import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import devices
import sync_devices


class DeviceMenuTests(unittest.TestCase):
    def test_combined_choice_cannot_mix_target_and_profile(self):
        catalog = json.loads((sync_devices.ROOT / 'configs/devices.json').read_text(encoding='utf-8'))
        for label, entry in catalog['devices'].items():
            self.assertEqual(devices.selected_device(label), (entry['target'], entry['profile']))
        with self.assertRaises(ValueError):
            devices.selected_device('invented router | x86/64 | nonexistent')

    def test_menu_keeps_same_profile_on_distinct_targets(self):
        rows = [dict(version='25.12.6', target=t, profile='generic', title="Generic 'EFI'")
                for t in ('x86/64', 'armsr/armv8')]
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(sync_devices.generate(rows + rows, Path(tmp)), 2)
            text = (Path(tmp) / '.github/workflows/build.yml').read_text(encoding='utf-8')
            self.assertIn('armsr/armv8 | generic', text)
            self.assertNotIn('      router_mode:', text)
            self.assertNotIn('      target:', text)

    def test_overlay_leaves_official_network_services_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = build.write_defaults(Path(tmp), '192.168.77.1', 'none').read_text()
            self.assertIn("network.lan.ipaddr='192.168.77.1'", text)
            for changed in ('dhcp.', '.gateway=', '.dns=', 'dnsmasq', 'eth0', 'eth1'):
                self.assertNotIn(changed, text)

    def test_access_does_not_claim_an_automatic_router_mode(self):
        info = dict(version='25.12.6', lan_ip='192.168.77.1', luci=True, docker=False,
                    proxy='none', package_manager='apk', firewall='nftables')
        text = build.access_notes(info)
        self.assertIn('保留官方设备 DHCP', text)
        self.assertNotIn('路由模式：', text)
        self.assertNotIn('上游网关：', text)
