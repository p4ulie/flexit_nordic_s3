"""Read all values from a Flexit Nordic unit over BACnet/IP (read-only)."""

import asyncio
import json
import os
import sys

from flexit_bacnet import FlexitBACnet

# ponytail: dumps every public property the library exposes; pick a subset if output gets noisy
FIELDS = sorted(
    n for n, v in vars(FlexitBACnet).items() if isinstance(v, property) and not n.startswith("_")
)


async def read(host: str, device_id: int) -> dict:
    unit = FlexitBACnet(host, device_id)
    await asyncio.wait_for(unit.update(), timeout=15)
    out = {}
    for name in FIELDS:
        try:
            out[name] = getattr(unit, name)
        except Exception as e:  # unit may not report every point
            out[name] = f"<{type(e).__name__}>"
    return out


def main() -> None:
    host = os.environ.get("FLEXIT_HOST", "10.3.252.2")
    device_id = int(os.environ.get("FLEXIT_DEVICE_ID", "2"))
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
