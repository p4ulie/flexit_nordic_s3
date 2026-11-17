# flexit_nordic_s3

BACnet/IP reader + mode control for a Flexit Nordic S3 REL (uses `flexit-bacnet`).

```sh
mise install        # python 3.12 + uv, creates .venv
mise run install    # deps into .venv
mise run read       # table; `python -m flexit_nordic.flexit --json` for JSON
mise run tui        # screens: 1 Overview, 2 All values, 3 Control (mode / boost / fireplace)
                    # refreshes every FLEXIT_REFRESH s (mise.toml, default 10) in the background
```

Config: `cp .env.example .env` and set `FLEXIT_HOST` / `FLEXIT_DEVICE_ID` — mise loads `.env` (git-ignored).

## Connecting

The unit is controlled over **BACnet/IP**: UDP port 47808 on the local network. It doesn't use HTTP or the cloud.

- **No authentication.** BACnet/IP has no login, token or password. Anyone who can reach UDP 47808 on the unit can read and write it, so keep it on a trusted LAN or VLAN.
- **No HTTP API.** This means `curl` can't talk to the unit. Use the Python library below or a BACnet tool.
- **Same LAN segment.** Replies come back over UDP and discovery uses broadcast, so run the scripts from the unit's subnet. In Kubernetes, the pod needs a route to the unit.

How the protocol works (objects, command priority, packet bytes) is covered in [BACNET.md](docs/BACNET.md).
TapHome reads the temperatures and the operation mode over the same protocol: [TAPHOME.md](docs/TAPHOME.md).

### Finding the connection parameters

Get both values from the **Flexit GO** app, the same app that connects the unit to Flexit's cloud. Look under
**More → Installer → Communication → BACnet settings**:

| `.env` | Flexit GO field | Example |
|---|---|---|
| `FLEXIT_HOST` | IP address | `192.0.2.10` |
| `FLEXIT_DEVICE_ID` | Device ID (BACnet device instance) | `2` |

The library can also find the IP address. It sends the same Siemens discovery broadcast the Flexit GO app uses (not Who-Is; see [BACNET.md](docs/BACNET.md#discovery)).
It binds UDP 47808 locally, so stop any other BACnet client first:

```sh
python -c 'import asyncio, flexit_bacnet; print(asyncio.run(flexit_bacnet.discover()))'
```

Discovery returns only IP addresses. The Device ID still comes from the app.
Give the unit a DHCP reservation so the IP address doesn't change.

## Switching modes

A mode switch is a BACnet **WriteProperty** of `present-value`, sent with **priority 13** (why that matters: [BACNET.md](docs/BACNET.md#command-priority)).

| Action | BACnet object | Value |
|---|---|---|
| Comfort button on (required before Home/High/Stop) | `binary-value,50` | `1` (`0` = off, which falls back to Away) |
| Ventilation mode | `multi-state-value,42` | `1` Stop · `2` Away · `3` Home · `4` High |
| Boost: runtime, then trigger | `positive-integer-value,293`, then `multi-state-value,357` | minutes (1–360), then `2` |
| Stop a running boost (what the app's Stop button does) | `binary-value,15` | `NULL` at priority 13 (relinquish) |
| Fireplace: runtime, then trigger | `positive-integer-value,270`, then `multi-state-value,360` | minutes (1–360), then `2` |
| Read the current mode | `multi-state-value,361` (read-only) | `1` Off · `2` Away · `3` Home · `4` High · `5` Cooker hood · `6` Fireplace · `7` Temporary high |

All 653 BACnet objects are listed in [ENDPOINTS.md](docs/ENDPOINTS.md).

### Command line

`curl` can't speak BACnet. Use `bacwp` (write) and `bacrp` (read) from
[bacnet-stack](https://github.com/bacnet-stack/bacnet-stack) instead. On Arch, install it with `yay -S bacnet-stack`.
These examples are untested on this unit:

```sh
# bacwp <device-id> <object-type> <instance> <property> <priority> <index> <tag> <value>
# object types: 5 = binary-value, 19 = multi-state-value, 48 = positive-integer-value
# property 85 = present-value · priority 0 = none · index -1 = none · tags: 2 = unsigned, 9 = enumerated

# Home
bacwp 2 5 50 85 13 -1 9 1          # comfort button on
bacwp 2 19 42 85 13 -1 2 3         # ventilation mode 3 = Home

# High
bacwp 2 5 50 85 13 -1 9 1
bacwp 2 19 42 85 13 -1 2 4         # ventilation mode 4 = High

# Away
bacwp 2 19 42 85 13 -1 2 2         # ventilation mode 2 = Away

# High for 15 minutes
bacwp 2 48 293 85 0 -1 2 15        # boost runtime = 15 min
bacwp 2 19 357 85 0 -1 2 2         # trigger boost

# Stop the boost early
bacwp 2 5 15 85 13 -1 0 0          # Forced ventilation: NULL @ priority 13 (tag 0 = NULL)

bacrp 2 19 361 85                  # check: 2 Away · 3 Home · 4 High · 7 Temporary high
```

While a boost runs, the unit itself holds High in slot 7 of the ventilation mode, so **Home and Away writes are stored but have no effect**.
Stop the boost first. The unit then falls back to the last mode written at priority 13.

Replace the first `2` with your `FLEXIT_DEVICE_ID`.
`bacwp` finds the device with a Who-Is broadcast, so it has to run on the unit's broadcast segment.

## Prometheus exporter

`flexit_nordic/exporter.py` polls the unit in a background thread every `FLEXIT_INTERVAL` seconds (default 30) and serves
`:9877/metrics` (`FLEXIT_EXPORTER_PORT`). A scrape only formats the last result and never touches the network.

| Metric | Meaning |
|---|---|
| `flexit_up` | 1 if the last read succeeded, else 0 |
| `flexit_last_success_timestamp_seconds` | Unix time of the last successful read |
| `flexit_read_duration_seconds` | Duration of the last read |
| `flexit_read_errors_total` | Failed reads |
| `flexit_info{device_name,model,serial_number}` | Unit identity, always 1 |
| `flexit_<field>` | One gauge per numeric value (bools as 0/1) |

While reads fail, the `flexit_<field>` gauges and `flexit_info` are not exported, so a stale value never looks fresh.
`flexit_up 0` and the timestamp say why. Before the first read finishes, only `flexit_up 0` is served.
`flexit_operation_mode` is numeric (1 Off, 2 Away, 3 Home, 4 High, 5 Cooker hood, 6 Fireplace, 7 Temporary high).

```sh
mise run exporter                  # local
mise run image:build               # flexit-exporter:dev
docker run -p 9877:9877 --env-file .env flexit-exporter:dev
```

## Layout

- `flexit_nordic/flexit.py`: data access, shared. `python -m flexit_nordic.flexit` is the reader (`mise run read`).
- `flexit_nordic/tui.py`: the terminal UI (`mise run tui`).
- `flexit_nordic/exporter.py`: the exporter (`mise run exporter`).
- `deploy/helm/flexit-exporter/`: the Helm chart.
- `docs/`: protocol notes ([BACNET.md](docs/BACNET.md), [ENDPOINTS.md](docs/ENDPOINTS.md), [TAPHOME.md](docs/TAPHOME.md)).

## Helm chart

```sh
helm install flexit deploy/helm/flexit-exporter --set flexit.host=192.0.2.10 --set flexit.deviceId=2
```

| Value | Default | Meaning |
|---|---|---|
| `image.repository` | `10.34.1.1:30095/flexit-exporter` | Image to run |
| `image.tag` | `""` | Empty means the chart's `appVersion` |
| `flexit.host`, `flexit.deviceId` | none | Required |
| `flexit.interval` | `30` | Poll interval in seconds |
| `resources` | 10m CPU, 32Mi request, 96Mi limit | Pod resources |
| `serviceMonitor.enabled`, `.interval` | `false`, `30s` | Prometheus Operator scrape config |
| `prometheusRule.enabled` | `false` | Alerts: unreachable, stale, filter change, cold supply air |
| `dashboard.enabled`, `.labels`, `.annotations` | `false` | Grafana dashboard ConfigMap for the sidecar |

The chart installs no CRDs. The ServiceMonitor and PrometheusRule need prometheus-operator, the dashboard needs the Grafana sidecar.
The pod needs a route to the unit (see [Connecting](#connecting)).

## Release

1. Bump `version` and `appVersion` in `deploy/helm/flexit-exporter/Chart.yaml` (same value), commit, tag `v<version>`, push.
2. `mise run image:push` builds and pushes `${REGISTRY:-10.34.1.1:30095}/flexit-exporter:<version>`, with the version read from `Chart.yaml`.
3. Point the Argo CD Application at the tag.
