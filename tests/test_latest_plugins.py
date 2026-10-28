import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] / 'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class LatestReleaseTests(unittest.TestCase):
    def resolve(self, release, pattern=r'luci-app-openclash-[0-9.]+\.apk', redirect=False):
        with patch.object(b.urllib.request, 'urlopen') as fetch:
            response = fetch.return_value.__enter__.return_value
            response.url = ('https://unexpected.invalid' if redirect else
                            'https://api.github.com/repos/vernesong/OpenClash/releases/latest')
            response.read.return_value = json.dumps(release).encode()
            return b.latest_release_asset('vernesong/OpenClash', pattern)

    def fixture(self):
        return dict(tag_name='v0.49.001', draft=False, prerelease=False, assets=[dict(
            name='luci-app-openclash-0.49.001.apk', digest='sha256:' + 'a' * 64,
            browser_download_url='https://github.com/vernesong/OpenClash/releases/download/v0.49.001/luci-app-openclash-0.49.001.apk')])

    def test_latest_is_resolved_to_exact_tag_and_digest(self):
        result = self.resolve(self.fixture())
        self.assertEqual(result['release'], 'v0.49.001')
        self.assertEqual(result['sha256'], 'a' * 64)
        self.assertNotIn('/latest/', result['url'])
        self.assertEqual(result['version_policy'], 'latest-stable')

    def test_untrusted_or_incompatible_latest_fails_without_fallback(self):
        for change in ('draft', 'prerelease', 'missing', 'duplicate', 'digest', 'url', 'tag'):
            with self.subTest(change=change):
                release = self.fixture()
                if change in ('draft', 'prerelease'):
                    release[change] = True
                elif change == 'missing':
                    release['assets'] = []
                elif change == 'duplicate':
                    release['assets'] *= 2
                elif change == 'tag':
                    release['tag_name'] = 'v0.49.001-rc1'
                else:
                    release['assets'][0][change if change == 'digest' else 'browser_download_url'] = 'bad'
                with self.assertRaises(ValueError):
                    self.resolve(release)
        with self.assertRaises(ValueError):
            self.resolve(self.fixture(), redirect=True)
        with self.assertRaises(ValueError):
            self.resolve(self.fixture(), pattern=r'luci-app-openclash_[0-9.]+_all\.ipk')

    def test_only_known_upstream_repositories_are_allowed(self):
        with patch.object(b.urllib.request, 'urlopen') as fetch:
            with self.assertRaises(ValueError):
                b.latest_release_asset('unknown/project', '.*')
            fetch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
