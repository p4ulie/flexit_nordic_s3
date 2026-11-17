# Flexit monitoring app — design

Date: 2026-11-17. Repo: `p4ulie/flexit_nordic_s3` (public). Consumer: `p4ulie/homenet_2.0` (RKE2 lab, ArgoCD).

## Intent

Monitor the Flexit Nordic S3 REL ventilation unit with its own small app, independent of Home Assistant: Prometheus
metrics, alerts and a Grafana dashboard that keep working when Home Assistant is down or rebuilt. The repo stays the
home of the BACnet tooling: the core reader and the TUI keep working as they do today; the monitoring app is added
next to them and uses the same core.

## Goals

- A Prometheus exporter, built as a container image, that reads the unit over BACnet/IP with `flexit_bacnet`.
- A Helm chart that installs the exporter and, when asked, its ServiceMonitor, PrometheusRule and Grafana dashboard.
- The repo tidied: one Python package, docs in `docs/`, the loose `k8s/` manifest replaced by the chart.
- homenet_2.0 deploys it through an ArgoCD Application pinned to a git tag of this repo.

## Non-goals

- **No writes.** The exporter never changes the unit (the TUI's Control screen still does, as today).
- **No BACnet objects beyond what `flexit_bacnet` exposes** (44 properties). The other objects in `docs/ENDPOINTS.md`
  (alarms, dampers, valves) are a possible later addition, not this work.
- **No CRDs in the chart.** ServiceMonitor and PrometheusRule CRDs belong to the cluster's prometheus-operator.
- No change to Home Assistant or its Flexit integration; both keep polling the unit (read-only BACnet traffic,
  harmless).
- No CI image build: images are built and pushed from the workstation (decided, see Approaches).

## Anti-goals

- A scrape that hangs or times out because the unit is slow. A down unit must read as `flexit_up 0`, never as a
  dead target.
- Stale values that look fresh.

## Approaches

**Image build and registry** — decided by the owner: **build locally, push to the lab registry
`10.34.1.1:30095`** (plain HTTP on TrueNAS; RKE2 already has a mirror entry for it, as the eve apps use it).
Considered: GitHub Actions to ghcr.io (no manual step, public image) — rejected in favour of the same flow as the
eve apps, nothing leaving the lab.

**When the exporter reads** — decided by the owner: **a background loop reads every `FLEXIT_INTERVAL` seconds
(default 30) and the scrape serves the last result.** Considered: read on each scrape (today's `exporter.py`) —
rejected because a read may take up to the library's 15 s timeout, longer than Prometheus' default 10 s scrape
timeout, and every extra scraper would add BACnet traffic.

## Repo layout (target)

```
flexit_nordic/
  __init__.py
  flexit.py        # core: read(host, device_id, action=None) -> dict, FIELDS, config()
  tui.py           # unchanged behaviour
  exporter.py      # the monitoring app
tests/             # pytest, no unit needed (fake FlexitBACnet)
deploy/helm/flexit-exporter/
  Chart.yaml       # version == appVersion == the release version
  values.yaml
  templates/       # deployment, service, servicemonitor, prometheusrule, dashboard configmap
  dashboards/flexit.json
docs/
  BACNET.md ENDPOINTS.md TAPHOME.md   # moved from the root, links fixed
  superpowers/specs/…
Dockerfile  .dockerignore  mise.toml  requirements.txt  README.md  .env.example
```

`k8s/flexit-exporter.yaml` is deleted (the chart replaces it). `requirements.txt` stays (no packaging needed;
the image copies the package). Entry points: `python -m flexit_nordic.flexit` (table / `--json`),
`python -m flexit_nordic.tui`, `python -m flexit_nordic.exporter`; mise tasks `read`, `tui`, `exporter` keep their
names.

**Core change:** `flexit.py` today reads `FLEXIT_HOST`/`FLEXIT_DEVICE_ID` and calls `sys.exit` at import time.
Move that into a `config()` function the three entry points call, so the package imports cleanly in tests.

## Exporter

- Env: `FLEXIT_HOST`, `FLEXIT_DEVICE_ID` (required, no defaults, as today), `FLEXIT_INTERVAL` (default 30),
  `FLEXIT_EXPORTER_PORT` (default 9877).
- A background thread runs `read()` every interval and stores the snapshot and the outcome. The custom collector
  only formats the stored state; a scrape never touches the network.
- Metrics:
  - `flexit_up` — 1 if the last read succeeded, else 0.
  - `flexit_last_success_timestamp_seconds` — unix time of the last successful read (staleness).
  - `flexit_read_duration_seconds` — duration of the last read.
  - `flexit_read_errors_total` — counter of failed reads.
  - `flexit_info{device_name, model, serial_number}` — 1.
  - `flexit_<property>` — every numeric property from `FIELDS` (bools as 0/1), values from the **last successful**
    read. While reads fail, they are **not exported** (anti-goal: stale values that look fresh); `flexit_up 0` and
    the timestamp say why.
  - `operation_mode` stays numeric (1 Off, 2 Away, 3 Home, 4 High, 5 Cooker hood, 6 Fireplace, 7 Temporary high —
    the TUI's `MODES`); the dashboard maps it to names.
- Logs one line per failed read (exception type and message), not per success.
- Before the first read finishes, `/metrics` serves `flexit_up 0` and `flexit_read_errors_total 0`;
  `flexit_last_success_timestamp_seconds` appears after the first successful read and `flexit_read_duration_seconds`
  after the first finished read.

## Image

`python:3.12-slim`, non-root (UID 65534), read-only root filesystem friendly, copies `flexit_nordic/` and
`requirements.txt`. Tag = release version, e.g. `10.34.1.1:30095/flexit-exporter:0.1.0`. mise task
`image:push` builds and pushes `${REGISTRY:-10.34.1.1:30095}/flexit-exporter:<version>`; the version comes from
`Chart.yaml` so there is one place to bump. The workstation's Docker must allow the HTTP registry (it already does
for the eve images).

## Helm chart `deploy/helm/flexit-exporter`

- `values.yaml`: `image.repository` (`10.34.1.1:30095/flexit-exporter`), `image.tag` (default: `appVersion`),
  `flexit.host` (required, chart fails to render without it), `flexit.deviceId` (required), `flexit.interval`,
  `resources` (requests cpu 10m / memory 32Mi, limit memory 96Mi), `serviceMonitor.enabled` (false),
  `serviceMonitor.interval` (30s), `prometheusRule.enabled` (false), `dashboard.enabled` (false),
  `dashboard.labels` (`grafana_dashboard: "1"`), `dashboard.annotations` (`grafana_folder: Home`).
- Deployment: 1 replica, security context as the current `k8s/` manifest (non-root, read-only root FS, no
  privilege escalation, drop ALL capabilities, seccomp RuntimeDefault — Pod Security `restricted`), readiness on
  the HTTP port, liveness on `/metrics`.
- Service on 9877, port name `metrics`.
- ServiceMonitor: selects the Service, path `/metrics`. No release label (the lab's Prometheus selects monitors in
  every namespace without labels).
- PrometheusRule, group `flexit`, all `severity: warning`:
  - `FlexitUnreachable` — `flexit_up == 0` for 15m.
  - `FlexitStale` — `time() - flexit_last_success_timestamp_seconds > 600` for 5m (the loop itself stalled).
  - `FlexitFilterChange` — `flexit_air_filter_polluted == 1` for 1h; summary says to reset the timer on the unit.
  - `FlexitSupplyAirCold` — `flexit_supply_air_temperature < 15` for 30m (it stayed above 19 °C through November
    2026 nights; below 15 °C the heater or heat recovery has failed).
- Dashboard ConfigMap from `dashboards/flexit.json` (`.Files.Get`), uid `flexit`, title `Home / Flexit ventilation`,
  datasource uid `prometheus`, not editable. Panels:
  - Now: mode (value-mapped), reachable, filter OK/CHANGE, filter hours / exchange interval, outside / supply /
    extract / exhaust temperatures, extract humidity, heat recovery %.
  - Air: the four temperatures over time; mode over time (state timeline).
  - Fans and heating: fan rpm, fan control signal %, heat exchanger efficiency and speed, heater power.
  - Exporter: last read age, read duration, read errors.

## Release flow

1. Bump `version` and `appVersion` in `Chart.yaml` (same value), commit, tag `v<version>`, push.
2. `mise run image:push`.
3. In homenet_2.0, set the Application's `targetRevision` to the tag (normal commit; this app is not one of the
   owner-gated eve releases).

## homenet_2.0 side (separate commit in that repo)

- `kubernetes/apps/flexit-exporter/application.yaml`: source `https://github.com/p4ulie/flexit_nordic_s3.git`,
  `path: deploy/helm/flexit-exporter`, `targetRevision: v0.1.0`, values from `kubernetes/apps/flexit-exporter/values.yaml`
  via `$values`, namespace `flexit` (created by ArgoCD), Pod Security `restricted`. Sync wave after
  kube-prometheus-stack and grafana, following the existing app waves.
- `values.yaml`: `flexit.host` / `flexit.deviceId` from `inventory/site.yaml` (`flexit-go`, `10.3.252.2`; device ID
  `2`), all three of `serviceMonitor`, `prometheusRule`, `dashboard` enabled.
- Network: pods reach the unit directly (proven from the Home Assistant pod, 2026-11-11); no policy needed outside
  the `public` namespaces.
- Register it the way homenet_2.0's `scripts/test_platform.py` and `docs/runbooks/monitoring.md` require for a new
  monitored app, and document it (a short `docs/runbooks/flexit.md` or a section in `home-assistant.md`).

## Testing

- Unit tests with a fake `FlexitBACnet` (monkeypatched): collector output for a good read, a failed read
  (`flexit_up 0`, no value gauges, error counter +1), before the first read, bools as 0/1, strings skipped.
- `helm lint` and `helm template` with all toggles on; `helm template` without `flexit.host` must fail.
- The dashboard JSON parses, and every panel query names a metric the exporter produces.
- Manual: `mise run exporter` against the real unit from a host on a route to VLAN 3, then `curl :9877/metrics`.

## Left to the builder

Exact panel geometry and colours; module internals of the exporter (thread vs asyncio task) as long as a scrape
never blocks on BACnet; test file structure; README wording.
