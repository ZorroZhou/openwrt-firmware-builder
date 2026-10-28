"""Generate the Actions version menu from official stable release metadata."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from build import VERSION_SOURCE, available_releases, official_catalog

ROOT = Path(__file__).resolve().parents[1]


def render_workflow(text, versions):
    block = ("      version:\n        description: '官网最新两代的全部正式小版本（刷新方法见 README）'\n"
             '        type: choice\n        required: true\n        options:\n'
             + ''.join(f"          - '{v}'\n" for v in versions)
             + f"        default: '{versions[0]}'\n")
    result, count = re.subn(r'^      version:\n.*?(?=^      device:)', lambda _: block,
                            text, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise ValueError('工作流 version 输入结构发生变化，拒绝覆盖')
    return result


def generate(catalog, output):
    versions = available_releases(catalog)
    workflow = render_workflow((ROOT / '.github/workflows/build.yml').read_text(encoding='utf-8'), versions)
    table = ('# 可选择的官方稳定版本\n\n'
             f'来源：[{VERSION_SOURCE}]({VERSION_SOURCE})。仅最新两个年号大版本，排除 RC/SNAPSHOT。\n\n'
             + '\n'.join(f'- `{v}`' for v in versions) + '\n\n'
             '菜单由官网数据生成；构建时仍实时验证版本范围和 ImageBuilder 文件。\n')
    files = {'.github/workflows/build.yml': workflow, 'docs/VERSIONS.md': table,
             'configs/versions.json': json.dumps(dict(source=VERSION_SOURCE,
                generated_at=datetime.now(timezone.utc).isoformat(), versions=versions), indent=2) + '\n'}
    for name, content in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8', newline='\n')
    return versions


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    args = parser.parse_args()
    versions = generate(official_catalog(), args.output_dir)
    print(f'已从官网生成 {len(versions)} 个稳定版本：' + ', '.join(versions))
