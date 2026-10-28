"""Export every published target/Profile; no invented device lists."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path

from build import official_catalog, resolve_release
from devices import ORIGIN, directories, official_json


def discover(version, output, query=''):
    base = f'{ORIGIN}/releases/{version}/targets/'
    targets = []
    for family in directories(base):
        targets += [family + '/' + sub for sub in directories(base + family + '/')]

    def profiles(target):
        data = official_json(base + target + '/profiles.json')
        if data.get('target') != target or data.get('version_number') != version:
            raise ValueError('设备目录与 Profile 元数据不一致')
        rows = []
        for profile, info in data['profiles'].items():
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
