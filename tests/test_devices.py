import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import devices
import build


class DeviceTests(unittest.TestCase):
    def test_profiles_are_selected_from_the_requested_official_target(self):
        data = dict(target='armsr/armv8', version_number='25.12.6', arch_packages='aarch64_generic',
                    profiles={'generic': {'images': [{'name': 'firmware.img.gz'}]}})
        with patch.object(devices, 'official_json', return_value=data) as request:
            self.assertEqual(devices.profile_data('25.12.6', 'armsr/armv8', 'generic')[0], data)
            self.assertIn('/25.12.6/targets/armsr/armv8/profiles.json', request.call_args.args[0])
            with self.assertRaises(ValueError):
                devices.profile_data('25.12.6', 'armsr/armv8', 'nonexistent')
            with self.assertRaises(ValueError):
                devices.profile_data('24.10.8', 'armsr/armv8', 'generic')
        for target in ('../x86/64', 'x86/64;id', 'http://example.com', 'arm'):
            with self.assertRaises(ValueError):
                devices.target_name(target)

    def test_cpu_isa_endianness_and_unknown_core_fail_closed(self):
        self.assertEqual(devices.core_arch('aarch64_cortex-a53'), ('arm64', 2, 1, 183))
        self.assertEqual(devices.core_arch('mips_24kc'), ('mips-softfloat', 1, 2, 8))
        self.assertEqual(devices.core_arch('mipsel_24kc'), ('mipsle-softfloat', 1, 1, 8))
        self.assertEqual(devices.core_arch('arm_cortex-a7_neon-vfpv4')[0], 'armv5')
        with self.assertRaises(ValueError):
            devices.core_arch('unknown_future_arch')
        with self.assertRaises(ValueError):
            devices.core_arch('arm_fa526')  # ARMv4 cannot execute a GOARM=5 core.

    def test_nondisk_and_untrusted_istore_combinations_are_rejected(self):
        fixed = {'images': [{'filesystem': 'squashfs', 'name': 'router-sysupgrade.bin'}]}
        data = {'arch_packages': 'mips_24kc', 'version_number': '25.12.6'}
        self.assertFalse(devices.feature_policy('ath79/generic', data, fixed, 0, False, 'none', False))
        for size, docker, store in ((512, False, False), (0, True, False), (0, False, True)):
            with self.assertRaises(ValueError):
                devices.feature_policy('ath79/generic', data, fixed, size, docker, 'none', store)
        data = {'arch_packages': 'x86_64', 'version_number': '24.10.8'}
        with self.assertRaisesRegex(ValueError, '签名'):
            devices.feature_policy('x86/64', data, fixed, 512, False, 'none', True)

    def test_device_image_names_and_checksums_not_x86_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            image = directory / 'device-sysupgrade.bin'
            image.write_bytes(b'synthetic device image')
            (directory / 'sha256sums').write_text(hashlib.sha256(image.read_bytes()).hexdigest() + ' *' + image.name + '\n')
            (directory / 'device.manifest').write_text('base-files - 1\n')
            selected = {'images': [{'name': image.name}]}
            self.assertEqual(devices.check_outputs(directory, selected)[0], [image])
            image.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                devices.check_outputs(directory, selected)
            with self.assertRaises(ValueError):
                devices.check_outputs(directory, {'images': [{'name': '../escape.bin'}]})

    def test_only_two_generations_and_no_third_alias(self):
        catalog = {'versions_list': ['25.12.6', '24.10.8', '23.05.6']}
        for version in ('23.05.6', 'third', '上两个大版本'):
            with self.assertRaises(ValueError):
                build.resolve_release(version, catalog)

    def test_catalog_uses_the_same_official_overview_as_firmware_selector(self):
        import discover_devices
        overview = dict(release='25.12.6', profiles=[dict(id='generic', target='armsr/armv8')])
        data = dict(version_number='25.12.6', target='armsr/armv8', arch_packages='aarch64_generic',
                    profiles={'generic': dict(titles=[{'title': 'Generic EFI'}])})
        def fetch(url):
            return overview if url.endswith('/.overview.json') else data
        with tempfile.TemporaryDirectory() as tmp, patch.object(discover_devices, 'official_json', side_effect=fetch):
            discover_devices.discover('25.12.6', Path(tmp))
            self.assertIn('Generic EFI', (Path(tmp) / 'devices.csv').read_text(encoding='utf-8-sig'))
            with self.assertRaises(ValueError):
                discover_devices.discover('25.12.6', Path(tmp), 'no such device')

    def test_initramfs_is_not_misrepresented_as_an_imagebuilder_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'sha256sums').write_text('')
            with self.assertRaisesRegex(ValueError, 'initramfs'):
                devices.check_outputs(directory, {'images': [{'filesystem': 'initramfs', 'name': 'kernel.bin'}]})
