# flexit_nordic_s3

BACnet/IP reader + mode control for a Flexit Nordic S3 REL (uses `flexit-bacnet`).

```sh
mise install        # python 3.12 + uv, creates .venv
mise run install    # deps into .venv
mise run read       # table; `python flexit.py --json` for JSON
mise run tui        # screens: 1 Overview, 2 All values, 3 Control (mode / boost / fireplace)
                    # refreshes every FLEXIT_REFRESH s (mise.toml, default 10) in the background
```

Unit address comes from `FLEXIT_HOST` / `FLEXIT_DEVICE_ID` in `mise.toml`
(from Flexit GO → More → Installer → Communication → BACnet settings).
Must run from the unit's LAN segment (UDP 47808).

## Prometheus exporter

`exporter.py` reads the unit on every scrape (via `flexit.read()`) and serves `:9877/metrics`:
`flexit_up`, `flexit_info{model,serial_number,…}`, and one gauge `flexit_<field>` per numeric value (bools as 0/1).

```sh
mise run exporter                                  # local
docker build -t flexit-exporter . && docker run -p 9877:9877 flexit-exporter
kubectl apply -f k8s/flexit-exporter.yaml          # set the image to your registry first
```

Layout: `flexit.py` = data access (shared), `tui.py` / `exporter.py` = consumers.
