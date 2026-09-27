"""
Unit tests for Ola BLE Protocol Parser
Tests live packet frames captured from physical scooter logs.
"""

import unittest
from app.bluetooth.protocol import OlaProtocol
from app.bluetooth.models import ScooterStatus

class TestOlaProtocol(unittest.TestCase):
    def setUp(self):
        self.protocol = OlaProtocol()
        self.status = ScooterStatus()

    def test_battery_soc_packet(self):
        # Type 8 is SOC packet with 78% battery
        # Framing: len, seq, ts (4 bytes), iv (2 bytes), type (8), data (0x4E = 78), eof
        pkt = bytes([0x0A, 0x01, 0x6A, 0xB9, 0x36, 0x31, 0x01, 0x02, 0x08, 0x4E, 0x00])
        res = self.protocol.parse_notification(pkt, self.status)
        self.assertEqual(res.battery_percent, 78)

    def test_range_packet(self):
        # Type 6 is Range packet with 82 km
        # Data: 0x00 0x52 = 82
        pkt = bytes([0x0B, 0x02, 0x6A, 0xB9, 0x36, 0x31, 0x01, 0x02, 0x06, 0x00, 0x52, 0x00])
        res = self.protocol.parse_notification(pkt, self.status)
        self.assertEqual(res.estimated_range_km, 82)

    def test_lock_state_packet(self):
        # Type 2 is Lock / Steering state: 1 = LOCKED, 2 = UNLOCKED
        pkt_locked = bytes([0x0A, 0x03, 0x6A, 0xB9, 0x36, 0x31, 0x01, 0x02, 0x02, 0x01, 0x00])
        res1 = self.protocol.parse_notification(pkt_locked, self.status)
        self.assertEqual(res1.lock_status, "LOCKED")

        pkt_unlocked = bytes([0x0A, 0x04, 0x6A, 0xB9, 0x36, 0x31, 0x01, 0x02, 0x02, 0x02, 0x00])
        res2 = self.protocol.parse_notification(pkt_unlocked, self.status)
        self.assertEqual(res2.lock_status, "UNLOCKED")

    def test_charging_state_packet(self):
        # Type 3 is Charging state: 1 = Charging
        pkt_charging = bytes([0x0A, 0x05, 0x6A, 0xB9, 0x36, 0x31, 0x01, 0x02, 0x03, 0x01, 0x00])
        res = self.protocol.parse_notification(pkt_charging, self.status)
        self.assertTrue(res.charging)

    def test_odometer_announcement_packet(self):
        # Packet 2 from nRF log: 0C 05 6A B9 36 31 01 02 71 01 01 09 CA ...
        # 0x09CA = 2506 -> 250.6 km
        pkt = bytes.fromhex("0C056AB93631010271010109CA00000000000000")
        res = self.protocol.parse_notification(pkt, self.status)
        self.assertEqual(res.odometer_km, 250.6)

if __name__ == "__main__":
    unittest.main()
