import gzip
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SPEC = importlib.util.spec_from_file_location('builder', Path(__file__).resolve().parents[1] / 'scripts/build.py')
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class BuilderTests(unittest.TestCase):
    def test_inputs(self):
        for version in ('23.05.6', '24.10.6', '25.12.6', '最新大版本', 'previous', 'third'):
            for preset in b.PRESETS:
                b.validate(version, 'x86-64', 1024, preset)
        for version in ('25.12', 'SNAPSHOT', '25.12.0-rc1', '../25.12.6', '25.12.6;id'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                b.validate(version, 'x86-64', 1024, 'standard')
        for target, size, preset in [('arm', 1024, 'minimal'), ('x86-64', 1, 'minimal'), ('x86-64', 512, 'other')]:
            with self.assertRaises(ValueError):
                b.validate('25.12.6', target, size, preset)

    def test_manifest_selection(self):
        for extension in ('xz', 'zst'):
            name = f'openwrt-imagebuilder-25.12.6-x86-64.Linux-x86_64.tar.{extension}'
            line = 'a' * 64 + ' *' + name
            self.assertEqual(b.select_archive(line, '25.12.6'), (name, 'a' * 64))
            for text in ('', line + '\n' + line, line.replace('25.12.6', '24.10.6'), line.replace('x86-64', 'armsr-armv8')):
                with self.assertRaises(ValueError):
                    b.select_archive(text, '25.12.6')

    def test_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'archive'
            p.write_bytes(b'broken download')
            with self.assertRaises(ValueError):
                b.verify(p, '0' * 64)
            b.verify(p, b.sha256(p))

    def test_rootfs_setting_persists(self):
        config = 'CONFIG_USE_APK=y\nCONFIG_TARGET_ROOTFS_PARTSIZE=104\n'
        self.assertEqual(b.configure_rootfs(config, 1024),
                         'CONFIG_USE_APK=y\nCONFIG_TARGET_ROOTFS_PARTSIZE=1024\n')
        for text in ('', config + config):
            with self.assertRaises(ValueError):
                b.configure_rootfs(text, 512)

    def test_missing_release_fails_without_retry(self):
        error = urllib.error.HTTPError('https://downloads.openwrt.org/', 404, 'missing', {}, None)
        with patch.object(b.urllib.request, 'urlopen', side_effect=error) as fetch:
            with self.assertRaisesRegex(RuntimeError, '404'):
                b.download('https://downloads.openwrt.org/missing', Path('unused'))
            self.assertEqual(fetch.call_count, 1)

    def test_network_failure_propagates(self):
        with patch.object(b.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')) as fetch, patch.object(b.time, 'sleep'):
            with self.assertRaises(urllib.error.URLError):
                b.download('https://downloads.openwrt.org/', Path('unused'))
            self.assertEqual(fetch.call_count, 3)

    def test_make_failure_propagates(self):
        with patch.object(b.subprocess, 'run', side_effect=b.subprocess.CalledProcessError(2, 'make')):
            with self.assertRaises(b.subprocess.CalledProcessError):
                b.run(['make', 'image'])

    def test_disk_validation(self):
        # Small synthetic disk tests the parser without allocating a 256 MiB fixture.
        disk = bytearray(2 * 1024 * 1024)
        disk[510:512] = b'\x55\xaa'
        struct.pack_into('<II', disk, 446 + 16 + 8, 2048, 2048)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'test.img.gz'
            p.write_bytes(gzip.compress(disk) + b'fwtool metadata')
            b.check_image(p, 1)
            with self.assertRaises(ValueError):
                b.check_image(p, 2)
            p.write_bytes(gzip.compress(disk)[:-6])
            with self.assertRaises(ValueError):
                b.check_image(p, 1)

    def test_gpt_disk_validation(self):
        disk = bytearray(2 * 1024 * 1024)
        disk[510:512] = b'\x55\xaa'
        disk[450] = 0xee
        disk[512:520] = b'EFI PART'
        struct.pack_into('<Q', disk, 512 + 72, 2)
        struct.pack_into('<I', disk, 512 + 84, 128)
        struct.pack_into('<QQ', disk, 1024 + 128 + 32, 2048, 4095)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'efi.img.gz'
            p.write_bytes(gzip.compress(disk))
            b.check_image(p, 1)
            with self.assertRaises(ValueError):
                b.check_image(p, 2)
            disk[512:520] = b'INVALID!'
            p.write_bytes(gzip.compress(disk))
            with self.assertRaises(ValueError):
                b.check_image(p, 1)
            disk[510:512] = b'00'
            p.write_bytes(gzip.compress(disk))
            with self.assertRaises(ValueError):
                b.check_image(p, 1)

    def test_refuses_stale_output(self):
        with patch.object(b.Path, 'exists', return_value=True):
            with self.assertRaisesRegex(ValueError, '已存在'):
                b.build('25.12.6', 'x86-64', 1024, 'standard')

    def test_missing_image_and_manifest_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaisesRegex(ValueError, '镜像'):
                b.validate_outputs(output, '25.12.6', 512)
            for fs in ('ext4', 'squashfs'):
                for efi in ('', '-efi'):
                    (output / f'openwrt-25.12.6-x86-64-generic-{fs}-combined{efi}.img.gz').write_bytes(b'fixture')
            with patch.object(b, 'check_image'):
                with self.assertRaisesRegex(ValueError, 'manifest'):
                    b.validate_outputs(output, '25.12.6', 512)
                manifest = output / 'openwrt.manifest'
                manifest.write_bytes(b'')
                with self.assertRaisesRegex(ValueError, 'manifest'):
                    b.validate_outputs(output, '25.12.6', 512)
                manifest.write_text('base-files - test\n')
                images, manifests = b.validate_outputs(output, '25.12.6', 512)
                self.assertEqual((len(images), len(manifests)), (4, 1))


if __name__ == '__main__':
    unittest.main()
