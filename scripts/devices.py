"""Official device metadata, conservative feature matching and network policy."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import urllib.request

ORIGIN = 'https://downloads.openwrt.org'


def official_json(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        if response.url != url:
            raise ValueError('Official metadata redirected unexpectedly')
        return json.load(response)


def target_name(value):
    value = 'x86/64' if value == 'x86-64' else value
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*', value):
        raise ValueError('目标必须为官方 target/subtarget，例如 x86/64 或 armsr/armv8')
    return value


def profile_data(version, target, profile):
    target = target_name(target)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.+-]*', profile):
        raise ValueError('设备 Profile 格式错误')
    url = f'{ORIGIN}/releases/{version}/targets/{target}/profiles.json'
    data = official_json(url)
    if data.get('target') != target or data.get('version_number') != version:
        raise ValueError('官方设备元数据与请求版本/平台不符')
    if profile not in data.get('profiles', {}):
        raise ValueError('所选设备 Profile 不存在于此版本/平台；运行 Discover official devices 查找')
    if not re.fullmatch(r'[a-zA-Z0-9_+-]+', data.get('arch_packages', '')):
        raise ValueError('官方软件包架构元数据不合法')
    selected = data['profiles'][profile]
    if not selected.get('images'):
        raise ValueError('此 Profile 没有官方发布镜像，不能假设可刷写')
    if all(i.get('filesystem') == 'initramfs' for i in selected['images']):
        raise ValueError('仅有 initramfs 的设备需要源码构建，不适用 ImageBuilder 拼装')
    return data, selected


def core_arch(arch):
    # Lowest common ISA variants; unknown architectures fail, never fall back to amd64.
    if arch == 'x86_64':
        return 'amd64-v1', 2, 1, 62
    if arch.startswith('aarch64_'):
        return 'arm64', 2, 1, 183
    if arch.startswith('arm_cortex-a') or arch in ('arm_arm1176jzf-s_vfp', 'arm_arm926ej-s', 'arm_xscale'):
        return 'armv5', 1, 1, 40
    if arch.startswith('i386_'):
        return '386-softfloat', 1, 1, 3
    for prefix, result in (
        ('mips64el_', ('mips64le', 2, 1, 8)), ('mips64_', ('mips64', 2, 2, 8)),
        ('mipsel_', ('mipsle-softfloat', 1, 1, 8)), ('mips_', ('mips-softfloat', 1, 2, 8)),
        ('riscv64_', ('riscv64', 2, 1, 243)), ('powerpc64le_', ('ppc64le', 2, 1, 21))):
        if arch.startswith(prefix):
            return result
    raise ValueError(f'没有经过映射的 Mihomo 核心架构：{arch}；请选择不安装代理')


def is_disk(target, profile):
    return target == 'x86/64' or any(
        i.get('filesystem') == 'ext4' and any(s in i.get('name', '') for s in ('combined', 'sdcard'))
        for i in profile['images'])


def feature_policy(target, data, profile, size, docker, proxy, istore):
    arch = data['arch_packages']
    disk = is_disk(target, profile)
    if size and not disk:
        raise ValueError('固定闪存设备不能套用磁盘根分区大小；请选择 auto')
    if docker and (not disk or not (arch == 'x86_64' or arch.startswith('aarch64_'))):
        raise ValueError('Docker 目前仅开放官方 ext4 磁盘镜像的 x86_64/arm64 平台；固定闪存/其他架构不混装')
    if (docker or proxy != 'none' or istore) and disk and (size or 1024) < 512:
        raise ValueError('管理插件/容器的磁盘根分区至少 512 MiB')
    if proxy == 'openclash':
        core_arch(arch)
    if istore and not (arch == 'x86_64' or arch.startswith('aarch64_')):
        raise ValueError('iStore 上游仅支持 x86_64/arm64')
    if istore and version_manager(data['version_number']) != 'apk':
        raise ValueError('iStore 的 opkg 包装器会剥除其临时源的签名检查；本项目目前仅集成 APK 签名源，不降低校验')
    return disk


def version_manager(version):
    # Only for early iStore policy. Actual manager is always checked from ImageBuilder.
    return 'apk' if version.startswith('25.12.') else 'unknown'


def network_policy(mode, address, gateway='', dns=''):
    if mode not in ('main', 'bypass'):
        raise ValueError('路由模式必须为 main 或 bypass')
    ip = ipaddress.IPv4Address(address)
    subnet = ipaddress.IPv4Network(f'{ip}/24', strict=False)
    if mode == 'main' and (gateway or dns):
        raise ValueError('上游网关/DNS 输入仅用于旁路由模式，主路由保留官方 WAN 配置')
    servers = dns.split()
    if mode == 'bypass':
        if not gateway or not servers:
            raise ValueError('旁路由必须填写上游网关和 DNS，不猜测主路由地址')
        gw = ipaddress.IPv4Address(gateway)
        if gw not in subnet or gw == ip or gw in (subnet.network_address, subnet.broadcast_address):
            raise ValueError('上游网关必须是相同 /24 网段中另一个有效主机地址')
        if len(servers) > 3:
            raise ValueError('最多填写三个 DNS IPv4，以空格分隔')
        for server in servers:
            value = ipaddress.IPv4Address(server)
            if value == ip or value.is_multicast or value.is_unspecified or value.is_loopback or value.is_reserved:
                raise ValueError('DNS 地址不可为自身、回环、多播或保留地址')
    return dict(mode=mode, dhcpv4=('enabled' if mode == 'main' else 'disabled'),
                ipv6_lan=('official-defaults' if mode == 'main' else 'RA/DHCPv6/NDP disabled'),
                gateway=gateway, dns=servers)


def network_commands(policy):
    commands = ['uci -q get dhcp.lan >/dev/null']
    commands += ["uci set dhcp.lan.ignore='" + ('0' if policy['mode'] == 'main' else '1') + "'"]
    if policy['mode'] == 'bypass':
        commands += [f"uci set dhcp.lan.{service}='disabled'" for service in ('ra', 'dhcpv6', 'ndp')]
        commands += [f"uci set network.lan.gateway='{policy['gateway']}'",
                     'uci -q delete network.lan.dns || true']
        commands += [f"uci add_list network.lan.dns='{server}'" for server in policy['dns']]
    return commands + ['uci commit network', 'uci commit dhcp']


def check_outputs(output, selected):
    # Device-specific image types and names come from the selected official Profile.
    sums = output / 'sha256sums'
    if not sums.is_file():
        raise ValueError('ImageBuilder 未生成 sha256sums')
    expected = {}
    for line in sums.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            expected[parts[1].lstrip('*')] = parts[0]
    images = []
    for info in selected['images']:
        # ImageBuilder reuses the released kernel; it does not rebuild initramfs kernels.
        if info.get('filesystem') == 'initramfs':
            continue
        name = info['name']
        if Path(name).name != name or not re.fullmatch(r'[a-zA-Z0-9_.+-]+', name):
            raise ValueError('镜像文件名不合法')
        path = output / name
        if not path.is_file() or path.stat().st_size == 0 or name not in expected:
            raise ValueError(f'缺少设备预期镜像（可能超出闪存容量）：{name}')
        with path.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != expected[name]:
                raise ValueError('ImageBuilder 镜像校验不符：' + name)
        images.append(path)
    if not images:
        raise ValueError('此设备仅提供 initramfs，需要源码构建，不能假装 ImageBuilder 已生成可刷写镜像')
    manifests = list(output.glob('*.manifest'))
    if not manifests or any(not p.stat().st_size for p in manifests):
        raise ValueError('缺少软件包清单')
    return images, manifests


