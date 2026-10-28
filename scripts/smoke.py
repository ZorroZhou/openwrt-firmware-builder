"""Boot an ext4 BIOS image in an isolated, disposable QEMU snapshot (Linux CI)."""
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time
import zlib


def cross_check(info):
    # Board-specific kernels cannot all boot on QEMU virt. Never call this a board boot test.
    import devices
    from shutil import which
    cpu = devices.core_arch(info['arch_packages'])[0] if (info['proxy'] != 'none' or info['docker']) else None
    emulators = {'arm64': 'aarch64', 'armv5': 'arm', '386-softfloat': 'i386',
                 'mips-softfloat': 'mips', 'mipsle-softfloat': 'mipsel',
                 'mips64': 'mips64', 'mips64le': 'mips64el', 'riscv64': 'riscv64', 'ppc64le': 'ppc64le'}
    requested = []
    if info['proxy'] == 'openclash':
        requested.append((Path('work/files/etc/openclash/core/clash_meta'), '-v'))
    elif info['proxy'] == 'nikki':
        paths = [p for name in ('mihomo', 'mihomo-meta')
                 for p in Path('work/extracted').glob('*/build_dir/target-*/root-*/usr/bin/' + name)
                 if p.is_file() and not p.is_symlink()]
        if not paths:
            raise ValueError('没有找到可供目标架构执行检查的 Nikki 核心')
        requested.append((paths[0], '-v'))
    if info['docker']:
        paths = list(Path('work/extracted').glob('*/build_dir/target-*/root-*/usr/bin/dockerd'))
        if not paths:
            raise ValueError('没有找到 Docker daemon')
        requested.append((paths[0], '--version'))
    output = ['Validation scope: device image checks and cross-architecture userspace only; no board boot/DHCP/traffic test.']
    for binary, argument in requested:
        emulator = which('qemu-' + emulators.get(cpu, 'unsupported'))
        if not emulator:
            raise ValueError('目标架构缺少执行检查器，停止发布所选代理/容器组合')
        output.append(subprocess.check_output([emulator, str(binary.resolve()), argument],
                                             text=True, stderr=subprocess.STDOUT, timeout=90))
    Path('smoke.log').write_text('\n'.join(output))
    print('\n'.join(output))


def inflate_image(image, raw):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    with image.open('rb') as source, raw.open('wb') as dest:
        while chunk := source.read(64 * 1024):
            while chunk:
                dest.write(decoder.decompress(chunk, 1024 * 1024))
                if decoder.eof:
                    return  # Ignore the OpenWrt fwtool trailer, after verifying gzip CRC.
                chunk = decoder.unconsumed_tail
    raise ValueError('Incomplete gzip image')


def guest_checks(info):
    checks = ['test -s /etc/openwrt_release', 'test -d /sys/class/net/eth0']
    ip = info['lan_ip']
    if ip != 'official-default':
        if not re.fullmatch(r'[0-9.]+', ip):
            raise ValueError('Invalid test IP')
        checks.append(f'test "$(uci -q get network.lan.ipaddr)" = "{ip}"')
    policy = info.get('network_policy')
    if policy:
        checks.append('test "$(uci -q get dhcp.lan.ignore)" = ' + ('0' if policy['mode'] == 'main' else '1'))
        if policy['mode'] == 'bypass':
            checks += [f'test "$(uci -q get dhcp.lan.{s})" = disabled' for s in ('ra', 'dhcpv6', 'ndp')]
            checks.append(f'test "$(uci -q get network.lan.gateway)" = "{policy["gateway"]}"')
    if info.get('istore'):
        checks += ['test -x /bin/is-opkg', 'test -s /etc/apk/keys/istore.pem',
                   'test -s /etc/apk/repositories.d/istore.list']
    if info['docker']:
        checks += ['docker --version', 'test -x /etc/init.d/dockerd',
                   '/etc/init.d/dockerd start',
                   '(i=0; until docker info >/dev/null 2>&1; do i=$((i+1)); '
                   '[ "$i" -lt 30 ] || exit 1; sleep 2; done)']
    proxy = info['proxy']
    if proxy == 'openclash':
        checks += ['/etc/openclash/core/clash_meta -v',
                   'test "$(uci -q get openclash.config.enable)" = 0']
    elif proxy == 'nikki':
        checks += ['mihomo -v', 'test "$(uci -q get nikki.config.enabled)" = 0']
        repo = ('/etc/opkg/customfeeds.conf' if info['package_manager'] == 'opkg'
                else '/etc/apk/repositories.d/customfeeds.list')
        checks += [f'grep -q "https://nikkinikki.pages.dev/openwrt-" {repo}']
    elif proxy != 'none':
        raise ValueError('Invalid test proxy')
    if proxy != 'none':
        checks.append(f'! /etc/init.d/{proxy} enabled')
    # Encode markers so the terminal's echoed command cannot be mistaken for success.
    wait = ('#!/bin/sh\nwait_check() {\n echo "CHECK: $1"\n i=0\n'
            ' until sh -c "$1"; do\n  i=$((i+1))\n'
            '  [ "$i" -lt 45 ] || { echo "CHECK_FAILED: $1"; return 1; }\n'
            '  sleep 2\n done\n}\n'
            "fail() { printf '\\106\\127\\102\\137\\106\\101\\111\\114\\012'; poweroff; exit 1; }\n")
    # procd exposes the console before first-boot UCI defaults have completed.
    checks = ['wait_check \'' + check + '\' || fail' for check in checks]
    return (wait + '\n'.join(checks) + "\nprintf '\\106\\127\\102\\137\\117\\113\\012'\npoweroff\n")


def smoke(directory):
    info = json.loads((directory / 'build-info.json').read_text())
    target = info.get('target', 'x86-64')
    if target not in ('x86-64', 'x86/64', 'armsr/armv8') or info.get('profile', 'generic') != 'generic':
        cross_check(info)
        return
    image = directory / f"openwrt-{info['version']}-x86-64-generic-ext4-combined.img.gz"
    if target == 'armsr/armv8':
        image = directory / f"openwrt-{info['version']}-armsr-armv8-generic-ext4-combined-efi.img.gz"
    raw = Path('work/smoke.img')
    inflate_image(image, raw)
    command = ['qemu-system-x86_64', '-m', '768', '-smp', '2', '-nographic', '-no-reboot',
               '-drive', f'file={raw.resolve()},format=raw,if=virtio', '-snapshot',
               '-nic', 'user,model=virtio-net-pci,restrict=on',
               '-nic', 'user,model=virtio-net-pci,restrict=on']
    if target == 'armsr/armv8':
        command = ['qemu-system-aarch64', '-M', 'virt', '-cpu', 'cortex-a57', '-m', '1024', '-smp', '2',
                   '-bios', '/usr/share/qemu-efi-aarch64/QEMU_EFI.fd', '-nographic', '-no-reboot',
                   '-drive', f'file={raw.resolve()},format=raw,if=none,id=disk0',
                   '-device', 'virtio-blk-pci,drive=disk0', '-snapshot',
                   '-nic', 'user,model=virtio-net-pci,restrict=on',
                   '-nic', 'user,model=virtio-net-pci,restrict=on']
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline, tail, sent, success = time.monotonic() + 300, '', False, False
    try:
        with Path('smoke.log').open('wb') as log:
            while time.monotonic() < deadline:
                for key, _ in selector.select(timeout=1):
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        continue
                    log.write(chunk)
                    log.flush()
                    text = chunk.decode(errors='replace')
                    print(text, end='', flush=True)
                    tail = (tail + text)[-16384:]
                    if not sent and 'Please press Enter to activate this console' in tail:
                        process.stdin.write(b'\n')
                        process.stdin.flush()
                        tail = ''
                    if not sent and re.search(r'root@[^\r\n]+[#]', tail):
                        # BusyBox's interactive line editor truncates long commands.
                        # Use short heredoc lines and pace the emulated serial port.
                        script = "cat > /tmp/fwb-check.sh <<'FWB_SCRIPT'\n" + guest_checks(info)
                        script += 'FWB_SCRIPT\nsh /tmp/fwb-check.sh\n'
                        for line in script.splitlines(keepends=True):
                            process.stdin.write(line.encode())
                            process.stdin.flush()
                            time.sleep(0.05)
                        sent = True
                    if re.search(r'(?:^|[\r\n])FWB_OK[\r\n]', tail):
                        success = True
                    if re.search(r'(?:^|[\r\n])FWB_FAIL[\r\n]', tail):
                        raise RuntimeError('Guest feature checks failed')
                if success or process.poll() is not None:
                    break
            if not success:
                raise RuntimeError('No successful guest check marker within 300 seconds')
    finally:
        selector.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raw.unlink(missing_ok=True)
    print('\nQEMU boot and feature checks passed')


if __name__ == '__main__':
    try:
        smoke(Path('dist'))
    except Exception as exc:
        print('Boot test failed:', exc, file=sys.stderr)
        sys.exit(1)
