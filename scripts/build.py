"""Official x86/64 ImageBuilder driver; Python 3.12+, Linux build host."""
import argparse
import hashlib
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
import zlib

PRESETS = {'minimal': '', 'standard': 'luci-ssl curl ca-bundle'}
SIZES = {256, 512, 1024, 2048, 4096}


def validate(version, target, size, preset):
    if not re.fullmatch(r'(24\.10|25\.12)\.(0|[1-9][0-9]*)', version):
        raise ValueError('仅支持完整稳定版本号 24.10.N / 25.12.N；不接受 snapshot/RC/URL')
    if target != 'x86-64' or size not in SIZES or preset not in PRESETS:
        raise ValueError('不支持的 target、根分区大小或 preset')


def download(url, dest):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, dest.open('wb') as out:
                if not response.url.startswith('https://downloads.openwrt.org/'):
                    raise ValueError('下载重定向到了非官方地址')
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


def build(version, target, size, preset):
    validate(version, target, size, preset)
    workspace, dist = Path('work'), Path('dist')
    if workspace.exists() or dist.exists():
        raise ValueError('work/ 或 dist/ 已存在；请使用干净工作目录，防止混入旧产物')
    workspace.mkdir()
    base = f'https://downloads.openwrt.org/releases/{version}/targets/x86/64/'
    checksums = workspace / 'sha256sums'
    download(base + 'sha256sums', checksums)
    name, digest = select_archive(checksums.read_text(), version)
    archive = workspace / name
    download(base + name, archive)
    verify(archive, digest)
    builder = extract(archive, workspace)
    config = (builder / '.config').read_text()
    uses_apk = 'CONFIG_USE_APK=y' in config.splitlines()
    expected_apk = version.startswith('25.12.')
    if uses_apk != expected_apk:
        raise ValueError('ImageBuilder 包管理器与版本预期不符，需人工审查')
    manager = 'apk' if uses_apk else 'opkg'
    # ImageBuilder clears MAKEFLAGS in recursive invocations: persist the setting.
    (builder / '.config').write_text(configure_rootfs(config, size))
    print(f'官方 ImageBuilder：{name}；包管理器：{manager}', flush=True)
    # Keep official repositories, signing keys and default device packages intact.
    run(['make', 'info'], builder)
    run(['make', 'image', 'PROFILE=generic', f'PACKAGES={PRESETS[preset]}'], builder)
    output = builder / 'bin/targets/x86/64'
    images, manifests = validate_outputs(output, version, size)
    # Publish only after all checks pass.
    dist.mkdir()
    for path in images + manifests:
        shutil.copy2(path, dist / path.name)
    metadata = dict(version=version, target=target, profile='generic', rootfs_mib=size,
                    preset=preset, extra_packages=PRESETS[preset], package_manager=manager,
                    imagebuilder_url=base + name, imagebuilder_sha256=digest,
                    github_sha=os.getenv('GITHUB_SHA'), run_id=os.getenv('GITHUB_RUN_ID'))
    (dist / 'build-info.json').write_text(json.dumps(metadata, indent=2) + '\n')
    shutil.copy2(checksums, dist / 'imagebuilder-sha256sums.txt')
    files = sorted(dist.iterdir())
    (dist / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in files))
    print('产物检查通过：', ', '.join(p.name for p in images))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    values = (os.environ['OPENWRT_VERSION'], os.environ['OPENWRT_TARGET'],
              int(os.environ['ROOTFS_MB']), os.environ['PRESET'])
    validate(*values)
    if not args.validate_only:
        build(*values)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'构建失败：{exc}', file=sys.stderr)
        sys.exit(1)

