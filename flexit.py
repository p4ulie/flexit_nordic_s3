"""Read all values from a Flexit Nordic unit over BACnet/IP (read-only)."""

import asyncio
import json
import logging
import os
import sys

from flexit_bacnet import FlexitBACnet

# flexit_bacnet's UDP protocol sets a result on the already-cancelled future after a timeout;
# asyncio logs that as a traceback (harmless, but it garbles the TUI)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# ponytail: dumps every public property the library exposes; pick a subset if output gets noisy
FIELDS = sorted(
    n for n, v in vars(FlexitBACnet).items() if isinstance(v, property) and not n.startswith("_")
)


async def read(host: str, device_id: int, action=None) -> dict:
    """Snapshot all values; if given, `await action(unit)` first (library re-reads after each write)."""
    unit = FlexitBACnet(host, device_id)
    await asyncio.wait_for(unit.update(), timeout=15)
    if action:
        await asyncio.wait_for(action(unit), timeout=15)
    out = {}
    for name in FIELDS:
        try:
            out[name] = getattr(unit, name)
        except Exception as e:  # unit may not report every point
            out[name] = f"<{type(e).__name__}>"
    return out


HOST = os.environ.get("FLEXIT_HOST", "10.3.252.2")
DEVICE_ID = int(os.environ.get("FLEXIT_DEVICE_ID", "2"))


def main() -> None:
    host, device_id = HOST, DEVICE_ID
    try:
        data = asyncio.run(read(host, device_id))
    except (TimeoutError, OSError) as e:
        sys.exit(f"No answer from {host} (device {device_id}): {e!r}. Run from the unit's LAN segment.")
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, default=str))
    else:
        width = max(map(len, data))
        for k, v in data.items():
            print(f"{k:<{width}}  {v}")


if __name__ == "__main__":
    main()
