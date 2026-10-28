"""Generate a combined device choice from the official catalog of both supported generations."""
import argparse
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def generate(rows, output):
    devices = {}
    for row in rows:
        key = (row['target'], row['profile'])
        title = ' '.join(row['title'].split()).replace('|', '/')[:100]
        devices.setdefault(key, f'{title} | {key[0]} | {key[1]}')
    if ('x86/64', 'generic') not in devices:
        raise ValueError('官方目录缺少默认 x86 设备，拒绝生成不完整菜单')
    choices = sorted(devices.values(), key=str.casefold)
    default = devices[('x86/64', 'generic')]
    block = ("      device:\n        description: '选择品牌/设备型号（自动匹配平台；构建前核对版本支持）'\n"
             '        type: choice\n        required: true\n        options:\n'
             + ''.join('          - ' + json.dumps(v, ensure_ascii=False) + '\n' for v in choices)
             + '        default: ' + json.dumps(default, ensure_ascii=False) + '\n')
    path = output / '.github/workflows/build.yml'
    source = path if path.exists() else ROOT / '.github/workflows/build.yml'
    text, count = re.subn(r'^      device:\n.*?(?=^      rootfs_mb:)', lambda _: block,
                         source.read_text(encoding='utf-8'), flags=re.M | re.S)
    if count != 1:
        raise ValueError('设备输入结构发生变化，拒绝覆盖')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')
    path = output / 'configs/devices.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(source='https://downloads.openwrt.org/releases/',
        versions=sorted({r['version'] for r in rows}),
        devices={label: dict(target=key[0], profile=key[1]) for key, label in devices.items()}),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(choices)


if __name__ == '__main__':
    from build import official_catalog, available_releases
    from discover_devices import discover
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    args = parser.parse_args()
    # Latest patch of each supported generation; older patch selections are checked live at build time.
    versions = {}
    for version in available_releases(official_catalog()):
        versions.setdefault(version.split('.')[0], version)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for version in versions.values():
            directory = Path(tmp) / version
            discover(version, directory)
            rows.extend(json.loads((directory / 'devices.json').read_text(encoding='utf-8')))
    print(f'Generated {generate(rows, args.output_dir)} device choices')
