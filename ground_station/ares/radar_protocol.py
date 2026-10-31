"""Bounded stream framing for Seeed/HLK LD2410 reports and command ACKs.

Source: Seeed's 24GHz_mmWave_for_XIAO-Usermanual-V1.00, sections 2.1/2.3.
Transport callbacks need not align with protocol frames. No sensor confidence
or human identity is inferred here.
"""

from dataclasses import dataclass
import struct

REPORT_HEADER = bytes.fromhex("F4 F3 F2 F1")
REPORT_END = bytes.fromhex("F8 F7 F6 F5")
COMMAND_HEADER = bytes.fromhex("FD FC FB FA")
COMMAND_END = bytes.fromhex("04 03 02 01")
STATES = {0: "NONE", 1: "MOVING", 2: "STATIONARY", 3: "MOVING_AND_STATIONARY"}


@dataclass(frozen=True)
class Frame:
    kind: str
    payload: bytes
    raw: bytes


class FrameDecoder:
    def __init__(self, max_payload: int = 512):
        self.buffer = bytearray()
        self.max_payload = max_payload
        self.rejected_frames = 0

    def feed(self, data: bytes) -> list[Frame]:
        # BLE chunks are small, but bound memory even for malformed input.
        self.buffer.extend(data[-4096:])
        frames = []
        while True:
            candidates = [(self.buffer.find(header), kind, header, end) for kind, header, end in (
                ("report", REPORT_HEADER, REPORT_END), ("ack", COMMAND_HEADER, COMMAND_END)
            )]
            candidates = [item for item in candidates if item[0] >= 0]
            if not candidates:
                self.buffer[:] = self.buffer[-3:]
                break
            offset, kind, _, end = min(candidates, key=lambda item: item[0])
            del self.buffer[:offset]
            if len(self.buffer) < 6:
                break
            size = int.from_bytes(self.buffer[4:6], "little")
            if size < 2 or size > self.max_payload:
                del self.buffer[0]
                self.rejected_frames += 1
                continue
            total = size + 10
            if len(self.buffer) < total:
                break
            if self.buffer[total - 4:total] != end:
                del self.buffer[0]
                self.rejected_frames += 1
                continue
            raw = bytes(self.buffer[:total])
            del self.buffer[:total]
            frames.append(Frame(kind, raw[6:-4], raw))
        return frames


def command_frame(command: int, value: bytes = b"") -> bytes:
    body = struct.pack("<H", command) + value
    return COMMAND_HEADER + struct.pack("<H", len(body)) + body + COMMAND_END


def authentication_frame(password: str = "HiLink") -> bytes:
    encoded = password.encode("ascii")
    if len(encoded) != 6:
        raise ValueError("Radar Bluetooth password must contain six ASCII characters")
    # Build the declared length, rather than copying the manual's inconsistent
    # password example (which contains extra bytes after its six-byte value).
    return command_frame(0x00A8, encoded)


def ack_result(frame: Frame) -> tuple[int, int] | None:
    if frame.kind != "ack" or len(frame.payload) < 4:
        return None
    command, status = struct.unpack_from("<HH", frame.payload)
    return command, status


def decode_report(frame: Frame) -> dict:
    body = frame.payload
    if frame.kind != "report" or len(body) < 13:
        raise ValueError("Incomplete radar report")
    if body[0] not in (1, 2) or body[1] != 0xAA or body[-2:] != b"\x55\x00":
        raise ValueError("Invalid radar report markers/type")
    if body[0] == 2 and len(body) != 13:
        raise ValueError("Unexpected basic-report size")
    state = body[2]
    if state not in STATES:
        raise ValueError("Unknown target state")
    result = {
        "report_type": "ENGINEERING" if body[0] == 1 else "BASIC",
        "target_state": STATES[state],
        "presence": state != 0,
        "moving": bool(state & 1),
        "stationary": bool(state & 2),
        "moving_distance_cm": int.from_bytes(body[3:5], "little"),
        "moving_energy": body[5],
        "stationary_distance_cm": int.from_bytes(body[6:8], "little"),
        "stationary_energy": body[8],
        "detection_distance_cm": int.from_bytes(body[9:11], "little"),
        "energy_is_probability": False,
        "raw_packet_hex": frame.raw.hex(" "),
    }
    if body[0] == 1:
        if len(body) < 15:
            raise ValueError("Incomplete engineering report")
        moving_count, stationary_count = body[11] + 1, body[12] + 1
        end = 13 + moving_count + stationary_count
        if moving_count > 9 or stationary_count > 9 or end > len(body) - 2:
            raise ValueError("Invalid engineering range-gate lengths")
        result["moving_gate_energies"] = list(body[13:13 + moving_count])
        result["stationary_gate_energies"] = list(body[13 + moving_count:end])
    return result
