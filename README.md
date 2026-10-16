# flexit_nordic_s3

BACnet/IP reader + mode control for a Flexit Nordic S3 REL (uses `flexit-bacnet`).

```sh
mise install        # python 3.12 + uv, creates .venv
mise run install    # deps into .venv
mise run read       # table; `python flexit.py --json` for JSON
mise run tui        # screens: 1 Overview, 2 All values, 3 Control (mode / boost / fireplace)
```

Unit address comes from `FLEXIT_HOST` / `FLEXIT_DEVICE_ID` in `mise.toml`
(from Flexit GO → More → Installer → Communication → BACnet settings).
Must run from the unit's LAN segment (UDP 47808).
