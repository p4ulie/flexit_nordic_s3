# flexit_nordic_s3

Read-only BACnet/IP reader for a Flexit Nordic S3 REL (uses `flexit-bacnet`).

```sh
mise install        # python 3.12 + uv, creates .venv
mise run install    # deps into .venv
mise run read       # table; `python flexit.py --json` for JSON
```

Unit address comes from `FLEXIT_HOST` / `FLEXIT_DEVICE_ID` in `mise.toml`
(from Flexit GO → More → Installer → Communication → BACnet settings).
Must run from the unit's LAN segment (UDP 47808).
