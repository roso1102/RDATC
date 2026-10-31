import asyncio
import struct
import unittest

from ares.radar_ble import NOTIFY_UUID, RadarConnectionError, receive_reports
from ares.radar_protocol import FrameDecoder, authentication_frame, decode_report

# Manufacturer protocol examples; these are fixtures, not captured sensor data.
BASIC = bytes.fromhex("F4 F3 F2 F1 0D 00 02 AA 02 51 00 00 00 00 3B 00 00 55 00 F8 F7 F6 F5")
ENGINEERING = bytes.fromhex(
    "F4 F3 F2 F1 23 00 01 AA 03 1E 00 3C 00 00 39 00 00 08 08 "
    "3C 22 05 03 03 04 03 06 05 00 00 39 10 13 06 06 08 04 03 05 55 00 F8 F7 F6 F5"
)
AUTH_ACK = bytes.fromhex("FD FC FB FA 04 00 A8 01 00 00 04 03 02 01")


class RadarProtocolTests(unittest.TestCase):
    def test_basic_report_survives_arbitrary_notification_boundaries(self):
        decoder = FrameDecoder()
        frames = []
        for byte in BASIC:
            frames.extend(decoder.feed(bytes([byte])))
        self.assertEqual(len(frames), 1)
        result = decode_report(frames[0])
        self.assertEqual(result["target_state"], "STATIONARY")
        self.assertEqual(result["moving_distance_cm"], 81)
        self.assertEqual(result["stationary_energy"], 59)
        self.assertFalse(result["energy_is_probability"])

    def test_engineering_report_and_coalesced_ack(self):
        frames = FrameDecoder().feed(AUTH_ACK + ENGINEERING + BASIC)
        self.assertEqual([frame.kind for frame in frames], ["ack", "report", "report"])
        result = decode_report(frames[1])
        self.assertEqual(result["target_state"], "MOVING_AND_STATIONARY")
        self.assertEqual(result["moving_distance_cm"], 30)
        self.assertEqual(len(result["moving_gate_energies"]), 9)
        self.assertEqual(len(result["stationary_gate_energies"]), 9)

    def test_corrupt_frames_and_noise_resynchronise(self):
        bad = BASIC[:-1] + b"\x00"
        decoder = FrameDecoder()
        frames = decoder.feed(b"noise" + bad + b"\xf4\xf3\xf2\xf1\xff\xff" + BASIC)
        self.assertEqual([frame.raw for frame in frames], [BASIC])
        self.assertGreaterEqual(decoder.rejected_frames, 2)
        decoder.feed(b"x" * 100_000)
        self.assertLessEqual(len(decoder.buffer), 3)

    def test_authentication_length_is_computed_from_six_byte_password(self):
        frame = authentication_frame()
        self.assertEqual(int.from_bytes(frame[4:6], "little"), 8)
        self.assertEqual(len(frame), 18)
        self.assertEqual(frame[6:8], struct.pack("<H", 0x00A8))
        with self.assertRaises(ValueError):
            authentication_frame("bad")


class FakeCharacteristic:
    def __init__(self, properties):
        self.properties = properties


class FakeClient:
    def __init__(self, device, **kwargs):
        self.payload = device
        self.services = self
        self.is_connected = False
        self.written = []

    async def __aenter__(self):
        self.is_connected = True
        return self

    async def __aexit__(self, *args):
        self.is_connected = False

    def get_characteristic(self, uuid):
        return FakeCharacteristic(["notify"] if uuid == NOTIFY_UUID else ["write-without-response"])

    async def start_notify(self, _, callback):
        self.callback = callback

    async def write_gatt_char(self, _, payload, response):
        self.written.append(payload)
        self.callback(None, self.payload)

    async def stop_notify(self, _):
        pass


class RadarSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_report_is_delivered_before_successful_authentication(self):
        stop = asyncio.Event()
        reports = []

        def received(record):
            reports.append(record)
            stop.set()

        await receive_reports(BASIC + AUTH_ACK + BASIC, received, lambda *_: None,
                              stop=stop, client_factory=FakeClient)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["source"], "LIVE_EXTERNAL")
        self.assertIsNone(reports[0]["hardware_sample_time_ms"])

    async def test_rejected_auth_never_creates_live_evidence(self):
        rejected = AUTH_ACK[:8] + b"\x01\x00" + AUTH_ACK[10:]
        reports = []
        with self.assertRaises(RadarConnectionError):
            await receive_reports(rejected + BASIC, reports.append, lambda *_: None,
                                  client_factory=FakeClient, auth_timeout=0.1)
        self.assertEqual(reports, [])
