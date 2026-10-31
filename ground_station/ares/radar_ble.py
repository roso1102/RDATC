"""Direct laptop BLE receiver. No firmware/threshold changes are performed."""

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import time
import uuid

from .radar_protocol import FrameDecoder, ack_result, authentication_frame, decode_report

NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"


async def discover_radars(timeout: float = 8.0) -> list[tuple]:
    from bleak import BleakScanner

    discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
    candidates = []
    for device, advertisement in discovered.values():
        name = advertisement.local_name or device.name or ""
        if "HLK-LD2410" in name.upper():
            candidates.append((device, {
                "name": name, "address": device.address, "rssi_dbm": advertisement.rssi,
            }))
    return candidates


async def find_radar(address: str, timeout: float = 8.0):
    """An explicitly selected address may advertise without a local name."""
    from bleak import BleakScanner

    return await asyncio.wait_for(
        BleakScanner.find_device_by_address(address, timeout=timeout), timeout=timeout + 5.0
    )


class RadarConnectionError(RuntimeError):
    pass


async def receive_reports(device, on_report, on_status, *, password="HiLink", stop=None,
                          client_factory=None, auth_timeout=5.0,
                          report_timeout=12.0):
    """Connect, authenticate, decode and deliver actual notifications.

    on_report/on_status are short synchronous callbacks on the asyncio loop.
    Only valid reports received after successful permission ACK are delivered.
    """
    stop = stop or asyncio.Event()
    if client_factory is None:
        from bleak import BleakClient
        client_factory = BleakClient
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=256)
    disconnected = asyncio.Event()
    decoder = FrameDecoder()
    dropped = 0
    sequence = 0
    connection_id = uuid.uuid4().hex

    def enqueue(data):
        nonlocal dropped
        try:
            queue.put_nowait(data)
        except asyncio.QueueFull:
            dropped += 1

    def notification(_, data):
        loop.call_soon_threadsafe(enqueue, bytes(data))

    on_status("CONNECTING", None)
    async with client_factory(device, disconnected_callback=lambda _: loop.call_soon_threadsafe(disconnected.set),
                              timeout=12.0) as client:
        notify = client.services.get_characteristic(NOTIFY_UUID)
        writer = client.services.get_characteristic(WRITE_UUID)
        if notify is None or writer is None:
            raise RadarConnectionError("Expected radar GATT characteristics were not found")
        if "notify" not in notify.properties or "write-without-response" not in writer.properties:
            raise RadarConnectionError("Radar GATT properties do not match the documented protocol")
        await client.start_notify(notify, notification)
        on_status("AUTHENTICATING", None)
        await client.write_gatt_char(writer, authentication_frame(password), response=False)
        auth_deadline = time.monotonic() + auth_timeout
        authenticated = False
        last_report = time.monotonic()
        while not stop.is_set():
            if disconnected.is_set() or not client.is_connected:
                raise RadarConnectionError("Radar Bluetooth disconnected")
            now = time.monotonic()
            if not authenticated and now >= auth_deadline:
                raise RadarConnectionError("Bluetooth permission acknowledgement timed out")
            if authenticated and now - last_report > report_timeout:
                raise RadarConnectionError("Radar report stream timed out")
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            for frame in decoder.feed(chunk):
                ack = ack_result(frame)
                if ack and ack[0] == 0x01A8:
                    if ack[1] != 0:
                        raise RadarConnectionError("Bluetooth permission rejected; check local password")
                    authenticated = True
                    last_report = time.monotonic()
                    on_status("CONNECTED_WAITING_FOR_REPORT", None)
                elif frame.kind == "report" and authenticated:
                    try:
                        record = decode_report(frame)
                    except ValueError:
                        decoder.rejected_frames += 1
                        continue
                    last_report = time.monotonic()
                    sequence += 1
                    record.update({
                        "source": "LIVE_EXTERNAL", "producer": "RADAR_BLE",
                        "valid": True, "hardware_sample_time_ms": None,
                        "received_at_utc": datetime.now(timezone.utc).isoformat(),
                        "received_monotonic_ms": round(time.monotonic() * 1000),
                        "sequence": sequence, "connection_id": connection_id,
                        "rejected_frames": decoder.rejected_frames,
                        "dropped_notifications": dropped,
                    })
                    on_report(record)
                    on_status("STREAMING", None)
        await client.stop_notify(notify)


async def cli(arguments):
    if arguments.action == "scan":
        candidates = await asyncio.wait_for(discover_radars(arguments.timeout), timeout=arguments.timeout + 5.0)
        print(json.dumps({"candidates": [info for _, info in candidates]}, indent=2))
        return
    if arguments.address:
        device = await find_radar(arguments.address, arguments.timeout)
        if device is None:
            raise RadarConnectionError("The selected radar address was not advertising during discovery")
    else:
        candidates = await asyncio.wait_for(discover_radars(arguments.timeout), timeout=arguments.timeout + 5.0)
        if len(candidates) != 1:
            raise RadarConnectionError("Select one matching radar address; scan did not identify a unique target")
        device = candidates[0][0]
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(arguments.duration, stop.set)
    try:
        await receive_reports(
            device,
            lambda record: print(json.dumps(record, sort_keys=True), flush=True),
            lambda state, error: print(json.dumps({"connection_state": state, "error": error}), flush=True),
            password=os.environ.get("ARES_RADAR_PASSWORD", "HiLink"), stop=stop,
        )
    finally:
        timer.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scan", "listen"])
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--address")
    parser.add_argument("--duration", type=float, default=15.0)
    arguments = parser.parse_args()
    if arguments.timeout <= 0 or arguments.duration <= 0:
        parser.error("timeouts must be positive")
    try:
        asyncio.run(cli(arguments))
    except Exception as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
