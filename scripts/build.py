"""Official x86/64 ImageBuilder driver; Python 3.12+, Linux build host."""
import argparse
import gzip
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import zlib

PRESETS = {'minimal': '', 'standard': 'luci-ssl luci-i18n-base-zh-cn curl ca-bundle'}
SIZES = {256, 512, 1024, 2048, 4096}
VERSION_SOURCE = 'https://downloads.openwrt.org/.versions.json'
CHANNELS = {'最新大版本': 0, '上一大版本': 1, '上两个大版本': 2,
            'latest': 0, 'previous': 1, 'third': 2}


def validate(version, target, size, preset):
    if version not in CHANNELS and not re.fullmatch(r'[1-9][0-9]\.[0-9]{2}\.(0|[1-9][0-9]*)', version):
        raise ValueError('请选择最新/上一/上两个大版本；不接受 snapshot、RC 或下载 URL')
    if target != 'x86-64' or size not in SIZES or preset not in PRESETS:
        raise ValueError('不支持的 target、根分区大小或 preset')


def official_catalog():
    with urllib.request.urlopen(VERSION_SOURCE, timeout=60) as response:
        if response.url != VERSION_SOURCE:
            raise ValueError('官方版本数据重定向到非预期地址')
        return json.load(response)


def latest_three(catalog):
    versions = catalog.get('versions_list')
    if not isinstance(versions, list) or not all(isinstance(v, str) for v in versions):
        raise ValueError('官方版本数据格式不符合预期')
    releases = [v for v in versions if re.fullmatch(r'[1-9][0-9]\.[0-9]{2}\.[0-9]+', v)]
    ordered = sorted(set(releases), key=lambda v: tuple(map(int, v.split('.'))), reverse=True)
    chosen, majors = [], set()
    for version in ordered:
        major = version.split('.')[0]
        if major not in majors:
            chosen.append(version)
            majors.add(major)
        if len(chosen) == 3:
            return chosen
    raise ValueError('官网没有提供三个完整稳定大版本；停止构建，不猜测版本目录')


def resolve_release(selection, catalog):
    latest = latest_three(catalog)
    if selection in CHANNELS:
        return latest[CHANNELS[selection]]
    if (selection not in catalog['versions_list'] or
            selection.split('.')[0] not in {v.split('.')[0] for v in latest} or
            not re.fullmatch(r'[1-9][0-9]\.[0-9]{2}\.[0-9]+', selection)):
        raise ValueError('版本不在官网最新三个稳定大版本范围内')
    return selection


def plugin_support(version, proxy):
    if proxy == 'nikki':
        lock = json.loads((Path(__file__).resolve().parents[1] / 'configs/plugins.lock.json').read_text())
        branch = '.'.join(version.split('.')[:2])
        if branch not in lock['nikki']:
            raise ValueError(f'Nikki 没有锁定兼容 {branch} 的上游包；请选择 none 或 OpenClash，不混用其他版本包')


def detect_runtime(config):
    flags = set(config.splitlines())
    if 'CONFIG_USE_APK=y' in flags:
        manager = 'apk'
    elif 'CONFIG_PACKAGE_opkg=y' in flags:
        manager = 'opkg'
    else:
        raise ValueError('无法识别 ImageBuilder 包管理器')
    fw4, fw3 = 'CONFIG_PACKAGE_firewall4=y' in flags, 'CONFIG_PACKAGE_firewall=y' in flags
    if fw4 == fw3:
        raise ValueError('防火墙配置缺失或同时启用 fw3/fw4，停止构建')
    return manager, 'nftables' if fw4 else 'iptables'


def download(url, dest, github=False):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, dest.open('wb') as out:
                allowed = ({'github.com', 'release-assets.githubusercontent.com',
                            'objects.githubusercontent.com'} if github else {'downloads.openwrt.org'})
                parsed = urlparse(response.url)
                if parsed.scheme != 'https' or parsed.hostname not in allowed:
                    raise ValueError('下载重定向到了非预期地址')
                shutil.copyfileobj(response, out)
            return
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise RuntimeError(f'官方文件不可用（HTTP {exc.code}）：{url}') from exc
            if attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def select_archive(text, version):
    pattern = re.compile(r'openwrt-imagebuilder-' + re.escape(version)
                         + r'-x86-64\.Linux-x86_64\.tar\.(?:zst|xz)')
    matches = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]):
            name = parts[1].removeprefix('*')
            if pattern.fullmatch(name):
                matches.append((name, parts[0].lower()))
    if len(matches) != 1:
        raise ValueError('官方 sha256sums 中没有唯一匹配的 ImageBuilder；停止构建')
    return matches[0]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(path, expected):
    if sha256(path) != expected:
        raise ValueError(f'SHA256 不匹配：{path.name}')


def run(args, cwd=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def configure_rootfs(config, size):
    updated, count = re.subn(r'^CONFIG_TARGET_ROOTFS_PARTSIZE=[0-9]+$',
                            f'CONFIG_TARGET_ROOTFS_PARTSIZE={size}', config, flags=re.MULTILINE)
    if count != 1:
        raise ValueError('ImageBuilder 根分区配置不存在或重复')
    return updated


def extract(archive, workspace):
    # Decompress first so Python can enforce safe extraction for either format.
    unpacked = workspace / 'imagebuilder.tar'
    command = 'zstd' if archive.name.endswith('.zst') else 'xz'
    with unpacked.open('wb') as out:
        subprocess.run([command, '-dc', str(archive)], stdout=out, check=True)
    dest = workspace / 'extracted'
    dest.mkdir()
    host_links = []
    tools = {'ldconfig', 'egrep', 'file', 'grep', 'gzip', 'which', 'bash', 'awk',
             'getopt', 'rsync', 'python3', 'python', 'diff', 'gcc', 'wget', 'g++',
             'perl', 'git', 'xxd', 'unzip', 'seq', 'realpath', 'cp', 'stat', 'install'}

    def archive_filter(member, destination):
        parts = Path(member.name).parts
        if (member.issym() and member.linkname.startswith('/')
                and len(parts) == 5 and parts[1:4] == ('staging_dir', 'host', 'bin')
                and parts[4] in tools):
            host_links.append(parts[4])
            return None
        return tarfile.data_filter(member, destination)

    with tarfile.open(unpacked) as bundle:
        bundle.extractall(dest, filter=archive_filter)
    roots = list(dest.iterdir())
    if len(roots) != 1 or not (roots[0] / 'Makefile').is_file():
        raise ValueError('ImageBuilder 归档结构不符合预期')
    for tool in host_links:
        if tool in ('ldconfig', 'xxd'):
            target = roots[0] / 'scripts' / ('noop.sh' if tool == 'ldconfig' else 'xxdi.pl')
            if tool == 'ldconfig' and not target.is_file():
                target = shutil.which('true')
        else:
            target = shutil.which({'awk': 'gawk', 'python': 'python3'}.get(tool, tool))
        if not target:
            raise ValueError(f'缺少宿主工具：{tool}')
        (roots[0] / 'staging_dir/host/bin' / tool).symlink_to(Path(target).resolve())
    unpacked.unlink()
    return roots[0]


def check_image(path, size):
    # Verify gzip CRC and root partition size in BIOS MBR or EFI GPT.
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    header = b''
    total = 0
    with path.open('rb') as image:
        while chunk := image.read(64 * 1024):
            while chunk:
                raw = decoder.decompress(chunk, 1024 * 1024)
                header += raw[:max(0, 2048 - len(header))]
                total += len(raw)
                if decoder.eof:
                    break  # OpenWrt may append fwtool metadata after the gzip stream.
                chunk = decoder.unconsumed_tail
            if decoder.eof:
                break
    if not decoder.eof:
        raise ValueError(f'gzip 流不完整：{path.name}')
    if len(header) < 512 or header[510:512] != b'\x55\xaa':
        raise ValueError(f'镜像缺少有效 MBR：{path.name}')
    if header[450] == 0xee:
        if (len(header) < 1280 or header[512:520] != b'EFI PART'
                or struct.unpack_from('<Q', header, 512 + 72)[0] != 2
                or struct.unpack_from('<I', header, 512 + 84)[0] != 128):
            raise ValueError(f'GPT 格式不符合预期：{path.name}')
        start, end = struct.unpack_from('<QQ', header, 1024 + 128 + 32)
        sectors = end - start + 1
    else:
        start, sectors = struct.unpack_from('<II', header, 446 + 16 + 8)
    if sectors * 512 != size * 1024 * 1024 or total < (start + sectors) * 512:
        raise ValueError(f'根分区大小或磁盘镜像长度不符：{path.name}')


def validate_outputs(output, version, size):
    prefix = f'openwrt-{version}-x86-64-generic'
    images = [output / f'{prefix}-{fs}-combined{efi}.img.gz'
              for fs in ('ext4', 'squashfs') for efi in ('', '-efi')]
    for image in images:
        if not image.is_file() or image.stat().st_size == 0:
            raise ValueError(f'缺少预期镜像：{image.name}')
        check_image(image, size)
    manifests = list(output.glob('*.manifest'))
    if not manifests or any(p.stat().st_size == 0 for p in manifests):
        raise ValueError('缺少非空软件包 manifest')
    return images, manifests


def validate_features(lan_ip='', docker=False, proxy='none', extra_packages=''):
    if type(docker) is not bool or proxy not in ('none', 'openclash', 'nikki'):
        raise ValueError('Docker 或代理选项不合法')
    if lan_ip:
        try:
            ip = ipaddress.IPv4Address(lan_ip)
        except ipaddress.AddressValueError as exc:
            raise ValueError('管理 IPv4 格式错误；示例 192.168.31.100，不要填写端口、网址或 /24') from exc
        private = any(ip in ipaddress.IPv4Network(net) for net in
                      ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
        if not private or int(str(ip).split('.')[-1]) in (0, 255):
            raise ValueError('管理 IP 必须是私网 /24 网段的有效主机地址')
        if docker and ip in ipaddress.IPv4Network('172.17.0.0/16'):
            raise ValueError('管理 IP 与 Docker 默认 172.17.0.0/16 网段冲突，请换用其他私网网段')
    packages = extra_packages.split()
    if len(extra_packages) > 1024 or len(packages) > 64 or any(
            not re.fullmatch(r'[a-z0-9][a-z0-9+_.-]*', p) for p in packages):
        raise ValueError('自定义包只接受软件包名称（最多 64 个），不接受命令或移除包语法')


def package_selection(preset, docker, proxy, extra_packages, firewall='nftables'):
    packages = PRESETS[preset].split()
    if docker:
        packages += ['docker', 'dockerd', 'luci-app-dockerman', 'luci-i18n-dockerman-zh-cn']
    if docker or proxy != 'none' or any(p.startswith('luci') for p in extra_packages.split()):
        packages += ['luci-ssl', 'luci-i18n-base-zh-cn']
    if proxy != 'none':
        packages += ['-dnsmasq', 'dnsmasq-full', 'kmod-tun', 'kmod-inet-diag', 'ip-full']
        if firewall == 'nftables':
            packages += ['kmod-nft-tproxy']
        elif firewall == 'iptables' and proxy == 'openclash':
            packages += ['iptables-mod-tproxy', 'iptables-mod-extra', 'kmod-ipt-nat', 'ipset']
        else:
            raise ValueError('所选代理不支持当前防火墙后端')
        packages += (['luci-app-openclash', 'luci-compat'] if proxy == 'openclash'
                     else ['mihomo-meta', 'nikki', 'luci-app-nikki', 'luci-i18n-nikki-zh-cn'])
    return list(dict.fromkeys(packages + extra_packages.split()))


def write_defaults(overlay, lan_ip, proxy):
    defaults = overlay / 'etc/uci-defaults/99-firmware-builder'
    defaults.parent.mkdir(parents=True, exist_ok=True)
    lines = ['#!/bin/sh', 'set -e']
    if lan_ip:
        lines += ["uci -q get network.lan >/dev/null", "uci set network.lan.proto='static'",
                  f"uci set network.lan.ipaddr='{lan_ip}'", "uci set network.lan.netmask='255.255.255.0'",
                  'uci commit network']
    if proxy != 'none':
        lines += [f"uci set {proxy}.config.enabled='0'" if proxy == 'nikki'
                  else "uci set openclash.config.enable='0'", f'uci commit {proxy}',
                  f'/etc/init.d/{proxy} disable']
    lines += ['exit 0', '']
    defaults.write_text('\n'.join(lines))
    defaults.chmod(0o755)
    return defaults


def fetch_locked(entry, workspace):
    url, digest = entry['url'], entry['sha256']
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/releases/download/[^/]+/[^/]+', url):
        raise ValueError('插件锁文件必须使用固定 GitHub Release 地址')
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('插件锁文件 SHA256 不合法')
    path = workspace / url.rsplit('/', 1)[1]
    download(url, path, github=True)
    verify(path, digest)
    return path


def prepare_plugin(builder, workspace, overlay, version, proxy, manager):
    if proxy == 'none':
        return []
    lock = json.loads((Path(__file__).resolve().parents[1] / 'configs/plugins.lock.json').read_text())
    records, packages = [], []
    suffix = '.apk' if manager == 'apk' else '.ipk'
    if proxy == 'openclash':
        entry = lock[proxy][suffix[1:]]
        packages.append(fetch_locked(entry, workspace))
        records.append(entry)
        core_entry = lock[proxy]['core']
        core_archive = fetch_locked(core_entry, workspace)
        core = overlay / 'etc/openclash/core/clash_meta'
        core.parent.mkdir(parents=True)
        with gzip.open(core_archive, 'rb') as source, core.open('wb') as dest:
            shutil.copyfileobj(source, dest)
        if core.read_bytes()[:4] != b'\x7fELF':
            raise ValueError('OpenClash 核心不是 ELF 可执行文件')
        core.chmod(0o755)
        records.append(core_entry)
    else:
        entry = lock[proxy]['.'.join(version.split('.')[:2])]
        archive = fetch_locked(entry, workspace)
        records.append(entry)
        extracted = workspace / 'nikki-packages'
        with tarfile.open(archive) as bundle:
            bundle.extractall(extracted, filter='data')
        for name in ('mihomo-meta', 'nikki', 'luci-app-nikki', 'luci-i18n-nikki-zh-cn'):
            separator = '-' if manager == 'apk' else '_'
            candidates = list(extracted.glob(name + separator + '*' + suffix))
            if len(candidates) != 1:
                raise ValueError(f'Nikki 归档缺少唯一的 {name}{suffix}')
            packages.append(candidates[0])
    for package in packages:
        shutil.copy2(package, builder / 'packages' / package.name)
    if manager == 'apk':
        # Authenticate pinned downloads first, then sign only these local packages.
        # Official repository signature checking remains enabled.
        run(['make', '_check_keys'], builder)
        apk = builder / 'staging_dir/host/bin/apk'
        for package in packages:
            run([str(apk.resolve()), 'adbsign', '--allow-untrusted', '--sign-key',
                 str((builder / 'keys/local-private-key.pem').resolve()),
                 str((builder / 'packages' / package.name).resolve())], builder)
    return records


def verify_installed(manifests, required):
    names = {line.split()[0] for path in manifests for line in path.read_text().splitlines() if line.strip()}
    missing = set(required) - names
    if missing:
        raise ValueError('manifest 缺少请求的软件包：' + ', '.join(sorted(missing)))
    return names


def check_openclash_language(builder):
    translations = [p for base in ('build_dir', 'staging_dir')
                    for p in (builder / base).glob('target-*/root-*/usr/lib/lua/luci/i18n/openclash.*.lmo')]
    if not any(p.stat().st_size and any(language in p.name.lower().replace('_', '-')
               for language in ('zh-cn', 'zh-hans')) for p in translations):
        raise ValueError('OpenClash 缺少内置简体中文资源')


def access_notes(info):
    ip = info['lan_ip']
    web = f'https://{ip}/' if info['luci'] else '未预装 LuCI 网页管理界面（minimal 基础系统）'
    return (f"# OpenWrt {info['version']} 使用说明\n\n"
            f"- 目标：x86-64 / generic\n- 管理 IPv4：**{ip}**\n"
            f"- LAN 掩码：255.255.255.0（/24）\n- 网页管理：{web}\n"
            f"- SSH：`ssh root@{ip}`\n- 用户名：**root**\n"
            '- 初始密码：**未设置（空密码）**；全新刷写后首次登录请自行设置密码。\n'
            '- 本项目不预置共享密码，不在公开 Release 中保存个人密码。\n'
            '- 此说明适用于全新刷写/恢复出厂；保留旧配置升级时，地址和密码以旧配置为准。\n'
            f"- 软件包管理器：{info['package_manager']}\n- 防火墙：{info['firewall']}\n"
            f"- 简体中文：{'LuCI 及所选管理插件中文资源已包含' if info['luci'] else '无网页界面，不追加 LuCI 语言包'}\n"
            f"- Docker：{'已预装' if info['docker'] else '未选择'}\n"
            f"- 代理：{info['proxy']}（如已选择，首次启动保持关闭，导入自己的配置后再启用）\n\n"
            '先在隔离虚拟机验收。不要与现有路由器在同一网段同时提供 DHCP。\n')


def build(version, target, size, preset, lan_ip='', docker=False, proxy='none', extra_packages=''):
    validate(version, target, size, preset)
    validate_features(lan_ip, docker, proxy, extra_packages)
    if (docker or proxy != 'none') and size < 512:
        raise ValueError('启用 Docker 或代理插件时根分区至少 512 MiB')
    workspace, dist = Path('work'), Path('dist')
    if workspace.exists() or dist.exists():
        raise ValueError('work/ 或 dist/ 已存在；请使用干净工作目录，防止混入旧产物')
    requested = version
    catalog = official_catalog()
    version = resolve_release(requested, catalog)
    plugin_support(version, proxy)
    print(f'官方版本解析：{requested} -> {version}；最新三代：{latest_three(catalog)}', flush=True)
    lan_ip = lan_ip or '192.168.1.1'
    workspace.mkdir()
    workspace = workspace.resolve()
    overlay = workspace / 'files'
    defaults = write_defaults(overlay, lan_ip, proxy)
    base = f'https://downloads.openwrt.org/releases/{version}/targets/x86/64/'
    checksums = workspace / 'sha256sums'
    download(base + 'sha256sums', checksums)
    name, digest = select_archive(checksums.read_text(), version)
    archive = workspace / name
    download(base + name, archive)
    verify(archive, digest)
    builder = extract(archive, workspace)
    config = (builder / '.config').read_text()
    manager, firewall = detect_runtime(config)
    if proxy == 'nikki' and firewall != 'nftables':
        raise ValueError('Nikki 仅支持 fw4/nftables')
    # ImageBuilder clears MAKEFLAGS in recursive invocations: persist the setting.
    (builder / '.config').write_text(configure_rootfs(config, size))
    print(f'官方 ImageBuilder：{name}；包管理器：{manager}', flush=True)
    plugins = prepare_plugin(builder, workspace, overlay, version, proxy, manager)
    packages = package_selection(preset, docker, proxy, extra_packages, firewall)
    # Keep official repositories, signing keys and default device packages intact.
    run(['make', 'info'], builder)
    args = ['make', 'image', 'PROFILE=generic', 'PACKAGES=' + ' '.join(packages),
            f'FILES={overlay}']
    if proxy != 'none':
        args.append(f'DISABLED_SERVICES={proxy}')
    run(args, builder)
    output = builder / 'bin/targets/x86/64'
    images, manifests = validate_outputs(output, version, size)
    installed = verify_installed(manifests, [p for p in packages if not p.startswith('-')])
    verify_installed(manifests, ['firewall4' if firewall == 'nftables' else 'firewall'])
    if proxy == 'openclash':
        check_openclash_language(builder)
    # Publish only after all checks pass.
    dist.mkdir()
    for path in images + manifests:
        shutil.copy2(path, dist / path.name)
    metadata = dict(builder_version='2.1.0', version=version, version_requested=requested,
                    version_source=VERSION_SOURCE, target=target, profile='generic', rootfs_mib=size,
                    preset=preset, packages=packages, lan_ip=lan_ip, username='root', password_state='unset',
                    luci=('luci-ssl' in installed), docker=docker, proxy=proxy, plugins=plugins,
                    package_manager=manager, firewall=firewall,
                    imagebuilder_url=base + name, imagebuilder_sha256=digest,
                    github_sha=os.getenv('GITHUB_SHA'), run_id=os.getenv('GITHUB_RUN_ID'))
    (dist / 'build-info.json').write_text(json.dumps(metadata, indent=2) + '\n')
    shutil.copy2(checksums, dist / 'imagebuilder-sha256sums.txt')
    shutil.copy2(defaults, dist / 'uci-defaults.txt')
    (dist / 'official-versions.json').write_text(json.dumps(catalog, indent=2) + '\n')
    notes = access_notes(metadata)
    (dist / 'ACCESS.md').write_text(notes, encoding='utf-8')
    files = sorted(dist.iterdir())
    (dist / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in files))
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(notes)
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output_file:
            output_file.write(f'version={version}\n')
    print('产物检查通过：', ', '.join(p.name for p in images))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    values = (os.environ['OPENWRT_VERSION'], os.environ['OPENWRT_TARGET'],
              int(os.environ['ROOTFS_MB']), os.environ['PRESET'])
    docker_raw = os.getenv('DOCKER', 'false')
    if docker_raw not in ('true', 'false'):
        raise ValueError('DOCKER 必须为 true 或 false')
    features = (os.getenv('LAN_IP', '').strip(), docker_raw == 'true',
                os.getenv('PROXY', 'none'), os.getenv('EXTRA_PACKAGES', '').strip())
    validate(*values)
    validate_features(*features)
    if (features[1] or features[2] != 'none') and values[2] < 512:
        raise ValueError('启用 Docker 或代理插件时根分区至少 512 MiB')
    if not args.validate_only:
        build(*values, *features)
    else:
        resolved = resolve_release(values[0], official_catalog())
        plugin_support(resolved, features[2])
        print(f'参数校验通过，官网解析版本：{resolved}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'构建失败：{exc}', file=sys.stderr)
        sys.exit(1)
