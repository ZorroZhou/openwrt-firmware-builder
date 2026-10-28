import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
spec = importlib.util.spec_from_file_location('sync', ROOT / 'scripts/sync_versions.py')
sync = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'build': b}):
    spec.loader.exec_module(sync)


class MenuTests(unittest.TestCase):
    def test_all_minor_versions_of_only_two_majors_are_listed(self):
        catalog = dict(versions_list=['25.12.6', '25.12.0', '24.10.8', '24.10.0',
                                     '23.05.6', '23.05.0', '22.03.7', '26.01.0-rc1'])
        versions = b.available_releases(catalog)
        self.assertEqual(versions, ['25.12.6', '25.12.0', '24.10.8', '24.10.0'])
        with tempfile.TemporaryDirectory() as tmp:
            sync.generate(catalog, Path(tmp))
            text = (Path(tmp) / '.github/workflows/build.yml').read_text(encoding='utf-8')
            for version in versions:
                self.assertIn("- '" + version + "'", text)
            self.assertNotIn("- '22.03.7'", text)
            self.assertIn('      target:', text)
            self.assertIn("default: '25.12.6'", text)

    def test_menu_renderer_refuses_unknown_structure(self):
        with self.assertRaises(ValueError):
            sync.render_workflow('unrelated workflow', ['25.12.6'])


class FeedTests(unittest.TestCase):
    def fixture(self, root):
        builder, overlay = root / 'builder', root / 'overlay'
        (builder / 'keys').mkdir(parents=True)
        (builder / 'repositories.conf').write_text('official opkg\n')
        (builder / 'repositories').write_text('official apk\n')
        feed = json.loads((ROOT / 'configs/plugins.lock.json').read_text())['nikki']
        return builder, overlay, feed

    def test_signed_feeds_and_keys_are_preserved_for_upgrade(self):
        for manager, version, repo, key in (
                ('opkg', '24.10.8', 'etc/opkg/customfeeds.conf', 'etc/opkg/keys/0123456789abcdef'),
                ('apk', '25.12.6', 'etc/apk/repositories.d/customfeeds.list', 'etc/apk/keys/nikki.pem')):
            with self.subTest(manager=manager), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                builder, overlay, feed = self.fixture(root)
                def fetch(url, dest, **kwargs):
                    dest.write_bytes(b'public key fixture')
                with patch.object(b, 'download', side_effect=fetch), patch.object(b, 'verify') as verify, \
                     patch.object(b.subprocess, 'check_output', return_value='0123456789abcdef\n'):
                    records = b.prepare_nikki_feed(builder, root, overlay, version, manager, feed)
                verify.assert_called_once()
                self.assertTrue((overlay / key).is_file())
                text = (overlay / repo).read_text()
                self.assertIn('https://nikkinikki.pages.dev/openwrt-', text)
                self.assertNotIn('allow-untrusted', text)
                self.assertEqual(records[0]['installation'], 'signed-upstream-feed')
                host_repo = builder / ('repositories.conf' if manager == 'opkg' else 'repositories')
                self.assertTrue(host_repo.read_text().startswith('official'))

    def test_unexpected_key_fingerprint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder, overlay, feed = self.fixture(root)
            def fetch(url, dest, **kwargs):
                dest.write_bytes(b'key')
            with patch.object(b, 'download', side_effect=fetch), patch.object(b, 'verify'), \
                 patch.object(b.subprocess, 'check_output', return_value='../../bad'):
                with self.assertRaises(ValueError):
                    b.prepare_nikki_feed(builder, root, overlay, '24.10.8', 'opkg', feed)


if __name__ == '__main__':
    unittest.main()
