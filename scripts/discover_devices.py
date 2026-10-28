"""Export every published target/Profile; no invented device lists."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import urllib.error
from pathlib import Path

from build import official_catalog, resolve_release
from devices import ORIGIN, official_json, target_name


def discover(version, output, query=''):
    base = f'{ORIGIN}/releases/{version}/targets/'
    overview = official_json(f'{ORIGIN}/releases/{version}/.overview.json')
    if overview.get('release') != version or not isinstance(overview.get('profiles'), list):
        raise ValueError('官方 Firmware Selector 设备总览格式不符合预期')
    targets = sorted({target_name(item['target']) for item in overview['profiles']})

    def profiles(target):
        try:
            data = official_json(base + target + '/profiles.json')
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'官方设备元数据读取失败：{target} ({exc.code})') from exc
        if data.get('target') != target or data.get('version_number') != version:
            raise ValueError('设备目录与 Profile 元数据不一致')
        published = {item['id'] for item in overview['profiles'] if item['target'] == target}
        if not published.issubset(data['profiles']):
            raise ValueError('官方总览与目标设备清单不一致')
        rows = []
        for profile, info in data['profiles'].items():
            if profile not in published:
                continue
            title = '; '.join(' '.join(str(v) for v in t.values()) for t in info.get('titles', []))
            row = dict(version=version, target=target, profile=profile, architecture=data['arch_packages'],
                       title=title, source=base + target + '/profiles.json')
            if query.lower() in ' '.join(row.values()).lower():
                rows.append(row)
        return rows

    # Four concurrent read requests; any missing/broken target fails rather than silently dropping devices.
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = [row for group in pool.map(profiles, targets) for row in group]
    if not rows:
        raise ValueError('没有匹配设备；检查检索词及官方版本')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'devices.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'devices.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f'{version}: {len(targets)} target/subtargets; {len(rows)} matching device profiles')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='latest')
    parser.add_argument('--query', default='')
    parser.add_argument('--output', type=Path, default=Path('device-catalog'))
    args = parser.parse_args()
    discover(resolve_release(args.version, official_catalog()), args.output, args.query)
