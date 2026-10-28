import importlib.util
from pathlib import Path
import unittest
import tempfile

spec = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] / 'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class CatalogTests(unittest.TestCase):
    catalog = dict(versions_list=['25.12.0', '25.12.6', '24.10.6', '24.10.8',
                                 '23.05.6', '22.03.7', '26.01.0-rc1', 'SNAPSHOT'])

    def test_official_latest_three_and_numeric_order(self):
        self.assertEqual(b.latest_three(self.catalog), ['25.12.6', '24.10.8', '23.05.6'])
        self.assertEqual(b.latest_three(dict(versions_list=self.catalog['versions_list'] + ['25.12.10']))[0], '25.12.10')
        for key, value in [('最新大版本', '25.12.6'), ('previous', '24.10.8'), ('third', '23.05.6')]:
            self.assertEqual(b.resolve_release(key, self.catalog), value)

    def test_next_major_rolls_window_without_guessing_directories(self):
        catalog = dict(versions_list=self.catalog['versions_list'] + ['26.01.0'])
        self.assertEqual(b.latest_three(catalog), ['26.01.0', '25.12.6', '24.10.8'])
        with self.assertRaises(ValueError):
            b.resolve_release('23.05.6', catalog)
        for version in ('22.03.7', '25.12.99', '26.01.0-rc1'):
            with self.assertRaises(ValueError):
                b.resolve_release(version, self.catalog)

    def test_malformed_or_incomplete_catalog_fails_closed(self):
        for catalog in ({}, {'versions_list': '25.12.6'}, {'versions_list': ['25.12.6', None]},
                        {'versions_list': ['25.12.6', '24.10.8']}):
            with self.assertRaises(ValueError):
                b.latest_three(catalog)

    def test_detects_package_manager_and_firewall_independently(self):
        self.assertEqual(b.detect_runtime('CONFIG_PACKAGE_opkg=y\nCONFIG_PACKAGE_firewall4=y'), ('opkg', 'nftables'))
        self.assertEqual(b.detect_runtime('CONFIG_USE_APK=y\nCONFIG_PACKAGE_firewall4=y'), ('apk', 'nftables'))
        self.assertEqual(b.detect_runtime('CONFIG_PACKAGE_opkg=y\nCONFIG_PACKAGE_firewall=y'), ('opkg', 'iptables'))
        for config in ('', 'CONFIG_USE_APK=y', 'CONFIG_PACKAGE_opkg=y\nCONFIG_PACKAGE_firewall=y\nCONFIG_PACKAGE_firewall4=y'):
            with self.assertRaises(ValueError):
                b.detect_runtime(config)

    def test_nikki_does_not_reuse_incompatible_version_packages(self):
        b.plugin_support('24.10.8', 'nikki')
        b.plugin_support('23.05.6', 'openclash')
        with self.assertRaisesRegex(ValueError, 'Nikki'):
            b.plugin_support('23.05.6', 'nikki')

    def test_docker_bridge_conflict_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Docker'):
            b.validate_features('172.17.1.1', docker=True)

    def test_access_notes_explain_address_credentials_and_upgrade(self):
        text = b.access_notes(dict(version='25.12.6', lan_ip='192.168.77.1', luci=True,
                                   package_manager='apk', firewall='nftables', docker=True, proxy='nikki'))
        for word in ('https://192.168.77.1/', '**root**', '空密码', '旧配置', 'nftables'):
            self.assertIn(word, text)

    def test_openclash_chinese_check_uses_actual_build_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                b.check_openclash_language(root)
            language = root / 'build_dir/target-x86_64_musl/root-x86/usr/lib/lua/luci/i18n/openclash.zh-cn.lmo'
            language.parent.mkdir(parents=True)
            language.write_bytes(b'translation fixture')
            b.check_openclash_language(root)
            language.write_bytes(b'')
            with self.assertRaises(ValueError):
                b.check_openclash_language(root)


if __name__ == '__main__':
    unittest.main()
