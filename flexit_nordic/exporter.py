"""Prometheus exporter: a background thread reads the unit, scrapes only format the last result."""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, CounterMetricFamily, GaugeMetricFamily

from .flexit import config, read

INFO = ("device_name", "model", "serial_number")
log = logging.getLogger("flexit_nordic.exporter")


@dataclass
class State:
    data: dict | None = None  # last successful read; kept out of /metrics while reads fail
    ok: bool = False
    last_success: float | None = None
    duration: float | None = None
    errors: int = 0


def poll_once(state: State, host: str, device_id: int, reader=read) -> None:
    start = time.monotonic()
    try:
        data = asyncio.run(reader(host, device_id))
    except Exception as e:  # timeout, unreachable, decode error: record it, keep polling
        state.duration = time.monotonic() - start
        state.errors += 1
        state.ok = False
        log.warning("read failed: %s: %s", type(e).__name__, e)
        return
    state.duration = time.monotonic() - start
    state.data = data
    state.last_success = time.time()
    state.ok = True


class FlexitCollector:
    def __init__(self, state: State):
        self.state = state

    def collect(self):
        s = self.state  # ponytail: no lock; a scrape racing a poll can mix two fields, harmless for gauges
        yield GaugeMetricFamily("flexit_up", "1 if the last BACnet read succeeded", value=float(s.ok))
        if s.last_success is not None:
            yield GaugeMetricFamily("flexit_last_success_timestamp_seconds", "Unix time of the last successful read", value=s.last_success)
        if s.duration is not None:
            yield GaugeMetricFamily("flexit_read_duration_seconds", "Duration of the last read", value=s.duration)
        yield CounterMetricFamily("flexit_read_errors", "Failed BACnet reads", value=s.errors)
        data = s.data
        if data is None or not s.ok:
            return
        info = GaugeMetricFamily("flexit_info", "Unit identity", labels=INFO)
        info.add_metric([str(data[k]) for k in INFO], 1)
        yield info
        for name, value in data.items():
            # bools become 0/1; strings (identity, unreadable points) and None are skipped
            if name not in INFO and isinstance(value, (int, float)):
                yield GaugeMetricFamily(f"flexit_{name}", name.replace("_", " "), value=float(value))


def main() -> None:
    host, device_id = config()  # fail fast on missing config, once
    interval = float(os.environ.get("FLEXIT_INTERVAL", "30"))
    port = int(os.environ.get("FLEXIT_EXPORTER_PORT", "9877"))
    state = State()
    REGISTRY.register(FlexitCollector(state))
    start_http_server(port)
    print(f"flexit exporter on :{port}/metrics → {host} device {device_id}, every {interval:g}s", flush=True)

    def loop():
        while True:
            poll_once(state, host, device_id)
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()
    threading.Event().wait()  # daemon thread dies with the main thread


if __name__ == "__main__":
    main()
