"""Prometheus exporter: reads the unit on every scrape via flexit.read()."""

import asyncio
import os
import time

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY, GaugeMetricFamily, InfoMetricFamily

from flexit import DEVICE_ID, HOST, read

PORT = int(os.environ.get("FLEXIT_EXPORTER_PORT", "9877"))
INFO = ("device_name", "model", "serial_number")


class FlexitCollector:
    # ponytail: one BACnet read per scrape (~1 s); cache if several Prometheis scrape it
    def collect(self):
        up = GaugeMetricFamily("flexit_up", "1 if the last BACnet read succeeded")
        start = time.monotonic()
        try:
            data = asyncio.run(read(HOST, DEVICE_ID))
        except Exception:  # timeout, unreachable, decode error: report down, keep serving
            up.add_metric([], 0)
            yield up
            return
        up.add_metric([], 1)
        yield up
        yield GaugeMetricFamily("flexit_scrape_duration_seconds", "BACnet read time", value=time.monotonic() - start)
        yield InfoMetricFamily("flexit", "Unit identity", value={k: str(data[k]) for k in INFO})
        for name, value in data.items():
            # bools become 0/1; strings (identity, unreadable points) are skipped
            if name not in INFO and isinstance(value, (int, float)):
                yield GaugeMetricFamily(f"flexit_{name}", name.replace("_", " "), value=float(value))


if __name__ == "__main__":
    REGISTRY.register(FlexitCollector())
    start_http_server(PORT)
    print(f"flexit exporter on :{PORT}/metrics → {HOST} device {DEVICE_ID}", flush=True)
    while True:
        time.sleep(3600)
