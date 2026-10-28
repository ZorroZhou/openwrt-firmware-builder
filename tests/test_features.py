import hashlib
import importlib.util
import json
import os
import io
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b, release = load('build'), load('release')
smoke = load('smoke')


class FeatureTests(unittest.TestCase):
    def test_network_input_rejects_injection_and_invalid_hosts(self):
        for ip in ('192.168.31.100', '10.0.0.1', '172.16.5.1', ''):
            b.validate_features(ip)
        for ip in ('8.8.8.8', '127.0.0.1', '192.168.1.0', '192.168.1.255', '::1', "192.168.1.1';reboot", '192.168.1.1/24'):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                b.validate_features(ip)

    def test_package_input_is_data_only(self):
        b.validate_features(extra_packages='htop curl ca-bundle')
        for text in ('$(id)', 'curl;id', '-base-files', 'https://evil/package.ipk', 'htop\nreboot;', 'a ' * 65):
            with self.assertRaises(ValueError):
                b.validate_features(extra_packages=text)
        with self.assertRaises(ValueError):
            b.validate_features(proxy='openclash nikki')

    def test_feature_packages(self):
        packages = b.package_selection('standard', True, 'nikki', 'htop curl')
        self.assertIn('dockerd', packages)
        self.assertIn('mihomo-meta', packages)
        self.assertIn('-dnsmasq', packages)
        self.assertNotIn('luci-app-openclash', packages)
        self.assertEqual(packages.count('curl'), 1)
        self.assertEqual(b.package_selection('minimal', False, 'none', ''), [])

    def test_defaults_are_one_shot_and_proxy_stays_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = b.write_defaults(Path(tmp), '192.168.31.100', 'openclash')
            text = p.read_text()
            self.assertIn("network.lan.ipaddr='192.168.31.100'", text)
            self.assertIn("openclash.config.enable='0'", text)
            self.assertIn('/etc/init.d/openclash disable', text)
            self.assertNotIn('gateway', text)
            self.assertTrue(text.endswith('exit 0\n'))
            p = b.write_defaults(Path(tmp), '', 'none')
            self.assertNotIn('network.', p.read_text())

    def test_lock_entries_are_pinned_and_well_formed(self):
        lock = json.loads((Path(__file__).resolve().parents[1] / 'configs/plugins.lock.json').read_text())
        entries = list(lock['openclash'].values()) + list(lock['nikki'].values())
        for entry in entries:
            self.assertIn('/releases/download/v', entry['url'])
            self.assertNotIn('/latest/', entry['url'])
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')

    def test_installed_packages_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / 'packages.manifest'
            manifest.write_text('dockerd - 1\ncurl - 2\n')
            b.verify_installed([manifest], ['dockerd', 'curl'])
            with self.assertRaisesRegex(ValueError, 'nikki'):
                b.verify_installed([manifest], ['nikki'])

    def test_small_feature_image_is_rejected_before_download(self):
        with patch.object(b, 'download') as fetch:
            with self.assertRaisesRegex(ValueError, '512'):
                b.build('25.12.6', 'x86-64', 256, 'standard', docker=True)
            fetch.assert_not_called()

    def test_archive_cannot_write_outside_extraction_directory(self):
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode='w') as bundle:
            member = tarfile.TarInfo('../escaped')
            member.size = 1
            bundle.addfile(member, io.BytesIO(b'x'))
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            def decompress(args, stdout, check):
                stdout.write(payload.getvalue())
            with patch.object(b.subprocess, 'run', side_effect=decompress):
                with self.assertRaises(tarfile.FilterError):
                    b.extract(workspace / 'fixture.tar.zst', workspace)
            self.assertFalse((workspace / 'escaped').exists())

    def test_boot_test_checks_requested_features(self):
        commands = smoke.guest_checks(dict(lan_ip='192.168.77.1', docker=True, proxy='nikki'))
        self.assertIn('docker --version', commands)
        self.assertIn('mihomo -v', commands)
        self.assertNotIn('FWB_OK', commands)  # Prevent false success from terminal echo.
        with self.assertRaises(ValueError):
            smoke.guest_checks(dict(lan_ip='$(id)', docker=False, proxy='none'))


class ReleaseTests(unittest.TestCase):
    def fixture(self, directory):
        info = dict(version='25.12.6', rootfs_mib=512, preset='standard', docker=False,
                    proxy='none', github_sha='a' * 40)
        p = directory / 'build-info.json'
        p.write_text(json.dumps(info))
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        (directory / 'SHA256SUMS').write_text(f'{digest}  build-info.json\n')

    def test_corruption_and_extra_assets_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.fixture(directory)
            self.assertEqual(len(release.verified_files(directory)), 2)
            (directory / 'unexpected').write_bytes(b'x')
            with self.assertRaises(ValueError):
                release.verified_files(directory)
            (directory / 'unexpected').unlink()
            (directory / 'build-info.json').write_text('{}')
            with self.assertRaises(ValueError):
                release.verified_files(directory)

    def test_only_publish_after_every_upload(self):
        env = dict(GITHUB_REPOSITORY='test/repo', GH_TOKEN='test', GITHUB_SHA='a' * 40,
                   GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, env):
            directory = Path(tmp)
            self.fixture(directory)
            responses = [{'id': 7}, {'state': 'uploaded', 'size': (directory / 'build-info.json').stat().st_size},
                         {'state': 'uploaded', 'size': (directory / 'SHA256SUMS').stat().st_size},
                         {'html_url': 'https://github.com/test/repo/releases/tag/test'}]
            with patch.object(release, 'request', side_effect=responses) as call:
                release.publish(directory)
                self.assertTrue(json.loads(call.call_args_list[0].args[3])['draft'])
                self.assertEqual(call.call_args_list[-1].args[1], 'PATCH')
            with patch.object(release, 'request', side_effect=[{'id': 8}, RuntimeError('upload failed')]) as call:
                with self.assertRaises(RuntimeError):
                    release.publish(directory)
                self.assertEqual(call.call_count, 2)
                self.assertNotIn('PATCH', [x.args[1] for x in call.call_args_list])


if __name__ == '__main__':
    unittest.main()
