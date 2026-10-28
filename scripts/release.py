"""Publish verified assets as a draft first; publish only after all uploads succeed."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request


def verified_files(directory):
    checksums = directory / 'SHA256SUMS'
    expected = {}
    for line in checksums.read_text().splitlines():
        digest, name = line.split('  ', 1)
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ValueError('Invalid checksum entry')
        if name in expected:
            raise ValueError('Duplicate checksum entry')
        expected[name] = digest
    actual = {p.name for p in directory.iterdir() if p.is_file() and p.name != 'SHA256SUMS'}
    if not expected or actual != set(expected):
        raise ValueError('Artifact file list does not match SHA256SUMS')
    for name, digest in expected.items():
        with (directory / name).open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != digest:
                raise ValueError('Artifact checksum mismatch: ' + name)
    return [directory / name for name in sorted(expected)] + [checksums]


def request(url, method, token, data, content_type='application/json'):
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': content_type}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def publish(directory):
    files = verified_files(directory)
    info = json.loads((directory / 'build-info.json').read_text())
    repo, token = os.environ['GITHUB_REPOSITORY'], os.environ['GH_TOKEN']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    if info['github_sha'] != os.environ['GITHUB_SHA']:
        raise ValueError('Artifact commit differs from publishing commit')
    run_id, attempt = os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_RUN_ATTEMPT']
    tag = f"firmware-{info['version']}-{run_id}-{attempt}"
    notes = (directory / 'ACCESS.md').read_text(encoding='utf-8')
    body = (f"OpenWrt {info['version']} / x86-64 / {info['rootfs_mib']} MiB\n\n"
            f"Preset: {info['preset']}; Docker: {info['docker']}; Proxy: {info['proxy']}\n\n"
            + notes + '\n\n'
            'Verify downloaded files using SHA256SUMS. Build checks do not replace boot testing.\n\n'
            f'https://github.com/{repo}/actions/runs/{run_id}')
    api = f'https://api.github.com/repos/{repo}/releases'
    release = request(api, 'POST', token, json.dumps(dict(tag_name=tag,
                      target_commitish=info['github_sha'], name=tag, body=body,
                      draft=True, prerelease=False)).encode())
    release_id = release['id']
    # Failure intentionally leaves a draft, never a public partial release.
    for path in files:
        url = f'https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name='
        asset = request(url + urllib.parse.quote(path.name), 'POST', token,
                        path.read_bytes(), 'application/octet-stream')
        if asset.get('state') != 'uploaded' or asset.get('size') != path.stat().st_size:
            raise ValueError('Release upload incomplete: ' + path.name)
    result = request(f'{api}/{release_id}', 'PATCH', token,
                     json.dumps(dict(draft=False, make_latest='false')).encode())
    print('Published:', result['html_url'])


if __name__ == '__main__':
    try:
        publish(Path('dist'))
    except Exception as exc:
        print('Release failed:', exc, file=sys.stderr)
        sys.exit(1)
