# Flexit Monitoring App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Prometheus exporter for the Flexit Nordic S3 unit, shipped as an image and a Helm chart with alerts and a Grafana dashboard, deployed to homenet_2.0 by ArgoCD.

**Architecture:** The repo becomes one package `flexit_nordic/` (core reader, TUI, exporter). The exporter reads the unit in a background thread every `FLEXIT_INTERVAL` s and serves the last result; a scrape never touches the network. The chart in `deploy/helm/flexit-exporter/` carries the Deployment, Service, ServiceMonitor, PrometheusRule and dashboard ConfigMap, each optional.

**Tech Stack:** Python 3.12, `flexit-bacnet` 2.2.3, `prometheus-client` 0.21.1, pytest, Docker, Helm 3.

**Spec:** `docs/superpowers/specs/2026-11-17-monitoring-app-design.md`

## Global Constraints

- The exporter is read-only: it never calls a write on the unit.
- No defaults for `FLEXIT_HOST` / `FLEXIT_DEVICE_ID`; missing or bad → exit with the existing message.
- `FLEXIT_INTERVAL` default 30, `FLEXIT_EXPORTER_PORT` default 9877.
- While the last read failed, no `flexit_<property>` value gauges are exported.
- One version number: `Chart.yaml` `version` == `appVersion` == image tag == git tag without `v`. First release `0.1.0`.
- Registry `10.34.1.1:30095`, image name `flexit-exporter`.
- The chart installs no CRDs; ServiceMonitor, PrometheusRule and dashboard default to off.
- Pod runs non-root (UID 65534), read-only root FS, no privilege escalation, all capabilities dropped, seccomp RuntimeDefault.
- Comments explain why, in full sentences, dry; keep the repo's existing `ponytail:` notes.

## Review Focus

- The unit unreachable at startup: `/metrics` must answer at once with `flexit_up 0`, and the process must not exit. → Task 2 test `test_before_first_read`.
- A read that raises mid-run after earlier successes: `flexit_up 0`, error counter +1, last-success timestamp unchanged, value gauges gone. → Task 2 test `test_failed_read_after_success`.
- A property the unit does not report (the core returns `"<ExcName>"` strings) or returns `None`: skipped, never a crash in the collector. → Task 2 test `test_strings_and_none_skipped`.
- `helm template` without `flexit.host`: must fail, not render a pod pointed at nothing. → Task 4 step.
- A dashboard query naming a metric the exporter does not produce (a typo shows as an empty panel nobody notices). → Task 5 test `test_dashboard_metrics_exist`.

---

### Task 1: Package the repo, move docs, keep the TUI working

**Files:**
- Move: `flexit.py`, `tui.py`, `exporter.py` → `flexit_nordic/` (add empty `flexit_nordic/__init__.py`)
- Move: `BACNET.md`, `ENDPOINTS.md`, `TAPHOME.md` → `docs/`; fix links in `README.md` and between them
- Delete: `k8s/flexit-exporter.yaml`
- Modify: `flexit_nordic/flexit.py`, `flexit_nordic/tui.py`, `mise.toml`, `.dockerignore`
- Create: `tests/test_flexit.py`, `requirements-dev.txt` (`pytest`)

**Interfaces:**
- Produces: `flexit_nordic.flexit.config() -> tuple[str, int]` (host, device_id; `sys.exit` with today's message when missing/bad), `read(host, device_id, action=None) -> dict` unchanged, `FIELDS` unchanged.

- [ ] **Step 1: Write the failing tests** in `tests/test_flexit.py`: `test_import_without_env` (with `FLEXIT_HOST`/`FLEXIT_DEVICE_ID` unset via `monkeypatch.delenv`, `import flexit_nordic.flexit` succeeds), `test_config_reads_env` (`config() == ("10.0.0.1", 2)`), `test_config_missing_exits` (`pytest.raises(SystemExit)`).
- [ ] **Step 2: Run** `uv run --with-requirements requirements.txt --with pytest pytest -q tests/` — expect FAIL (no package).
- [ ] **Step 3: Move files with `git mv`**, add `config()`, replace the import-time `HOST`/`DEVICE_ID` with `config()` calls in `main()` and in `tui.py`'s entry point; relative imports (`from .flexit import read, config`).
- [ ] **Step 4: Update `mise.toml`** tasks: `read` → `python -m flexit_nordic.flexit`, `tui` → `python -m flexit_nordic.tui`, `exporter` → `python -m flexit_nordic.exporter`, add `test` → the pytest command above; `install` also installs `requirements-dev.txt`. Add `tests/`, `docs/`, `deploy/` to `.dockerignore`.
- [ ] **Step 5: Run tests** — PASS. Run `python -m flexit_nordic.flexit --help` with no env → exits with the "Set FLEXIT_HOST…" message.
- [ ] **Step 6: Commit** `git commit -m "Package the reader, TUI and exporter; docs into docs/"`.

### Task 2: Exporter with a background read loop

**Files:**
- Rewrite: `flexit_nordic/exporter.py`
- Create: `tests/test_exporter.py`

**Interfaces:**
- Consumes: `read`, `config` from Task 1.
- Produces: `class State` (fields `data: dict | None`, `ok: bool`, `last_success: float | None`, `duration: float | None`, `errors: int`); `poll_once(state, host, device_id, reader=read) -> None` (one read, updates `state`, logs one line on failure); `class FlexitCollector(state)` with `collect()`; `main()` starts the HTTP server, then loops `poll_once` + `sleep(interval)` in a daemon thread.
- Metrics (exact names): `flexit_up`, `flexit_last_success_timestamp_seconds`, `flexit_read_duration_seconds`, `flexit_read_errors_total` (counter), `flexit_info{device_name,model,serial_number}`, `flexit_<property>` for every numeric/bool field of the last successful read (bool → 0/1; str and None skipped).

- [ ] **Step 1: Write the failing tests** with a fake async reader passed to `poll_once` and `prometheus_client.generate_latest` over a fresh `CollectorRegistry` holding `FlexitCollector(state)`:
  - `test_before_first_read`: output contains `flexit_up 0.0`, no `flexit_supply_air_temperature`.
  - `test_good_read`: fake returns `{"supply_air_temperature": 22.5, "air_filter_polluted": True, "operation_mode": 3, "model": "S3", "device_name": "x", "serial_number": "1"}` → `flexit_up 1.0`, `flexit_supply_air_temperature 22.5`, `flexit_air_filter_polluted 1.0`, `flexit_operation_mode 3.0`, `flexit_info{device_name="x",model="S3",serial_number="1"} 1.0`, `flexit_last_success_timestamp_seconds` present.
  - `test_failed_read_after_success`: good read, then a fake raising `TimeoutError` → `flexit_up 0.0`, `flexit_read_errors_total 1.0`, timestamp equals the first read's, no `flexit_supply_air_temperature`.
  - `test_strings_and_none_skipped`: field values `"<KeyError>"` and `None` produce no gauge and no exception.
- [ ] **Step 2: Run** `mise run test` — FAIL.
- [ ] **Step 3: Implement** in `exporter.py`; `FLEXIT_INTERVAL` from env (default 30). A plain `threading.Thread(daemon=True)` around `asyncio.run(read(...))`, as `tui.py`'s poller does. Keep the asyncio logger silenced (it lives in `flexit.py`).
- [ ] **Step 4: Run** `mise run test` — PASS.
- [ ] **Step 5: Manual check** (needs a route to VLAN 3; skip and say so if not reachable): `FLEXIT_HOST=10.3.252.2 FLEXIT_DEVICE_ID=2 mise run exporter`, then `curl -s :9877/metrics | grep -E 'flexit_(up|supply_air_temperature)'` → `flexit_up 1.0` and a temperature.
- [ ] **Step 6: Commit** `git commit -m "Exporter: read in the background, serve the last result"`.

### Task 3: Image and push task

**Files:**
- Modify: `Dockerfile`, `mise.toml`

- [ ] **Step 1: Dockerfile**: copy `flexit_nordic/` and `requirements.txt`; `CMD ["python", "-m", "flexit_nordic.exporter"]`; keep `USER 65534`, `PYTHONUNBUFFERED=1`, `EXPOSE 9877`; add `PYTHONDONTWRITEBYTECODE=1` (read-only root FS).
- [ ] **Step 2: mise task `image:push`**: version = `version:` line of `deploy/helm/flexit-exporter/Chart.yaml` (Task 4 creates it; until then the task is written but not run), `docker build -t ${REGISTRY:-10.34.1.1:30095}/flexit-exporter:$v . && docker push …`. Add `image:build` doing only the build, tagged `flexit-exporter:dev`.
- [ ] **Step 3: Verify** `mise run image:build` succeeds; `docker run --rm --read-only -e FLEXIT_HOST=192.0.2.10 -e FLEXIT_DEVICE_ID=2 -p 9877:9877 flexit-exporter:dev` and, from another shell, `curl -s :9877/metrics | grep flexit_up` → `flexit_up 0.0` (TEST-NET address, unreachable by design). Stop the container.
- [ ] **Step 4: Commit** `git commit -m "Image: run the packaged exporter; mise image tasks"`.

### Task 4: Helm chart

**Files:**
- Create: `deploy/helm/flexit-exporter/{Chart.yaml,values.yaml,.helmignore}`, `templates/{_helpers.tpl,deployment.yaml,service.yaml,servicemonitor.yaml,prometheusrule.yaml,dashboard.yaml}`
- Create: `tests/test_chart.py`

**Interfaces:**
- Produces: values keys exactly as the spec's "Helm chart" section (`image.repository`, `image.tag`, `flexit.host`, `flexit.deviceId`, `flexit.interval`, `resources`, `serviceMonitor.{enabled,interval}`, `prometheusRule.enabled`, `dashboard.{enabled,labels,annotations}`); Service port name `metrics`, port 9877; dashboard file path `deploy/helm/flexit-exporter/dashboards/flexit.json` (Task 5 fills it; Task 4 commits a minimal valid placeholder `{"uid":"flexit","title":"Home / Flexit ventilation","panels":[]}`).
- Chart.yaml: `apiVersion: v2`, `name: flexit-exporter`, `version: 0.1.0`, `appVersion: "0.1.0"`.

- [ ] **Step 1: Write the failing tests** in `tests/test_chart.py`, each shelling out to `helm template t deploy/helm/flexit-exporter …` and `yaml.safe_load_all`:
  - `test_requires_host`: without `--set flexit.host=…` → non-zero exit (`required` in the template).
  - `test_defaults_render_only_workload`: with host and deviceId set → kinds exactly `{Deployment, Service}`; container image `10.34.1.1:30095/flexit-exporter:0.1.0`; env `FLEXIT_HOST`, `FLEXIT_DEVICE_ID`, `FLEXIT_INTERVAL`; `securityContext` as the Global Constraints.
  - `test_all_toggles`: with all three enabled → also `ServiceMonitor` (port `metrics`, path `/metrics`, interval `30s`), `PrometheusRule` with alerts exactly `{FlexitUnreachable, FlexitStale, FlexitFilterChange, FlexitSupplyAirCold}` and expressions/`for` as in the spec, `ConfigMap` with label `grafana_dashboard: "1"`, annotation `grafana_folder: Home`, key `flexit.json` that parses as JSON.
- [ ] **Step 2: Run** `mise run test` (add `--with pyyaml` to the test task) — FAIL.
- [ ] **Step 3: Write the chart.** Probes: readiness TCP on `metrics`, liveness HTTP GET `/metrics`. No release labels on ServiceMonitor/PrometheusRule. Dashboard via `.Files.Get "dashboards/flexit.json"`.
- [ ] **Step 4: Run** `helm lint deploy/helm/flexit-exporter --set flexit.host=x --set flexit.deviceId=2` → 0 failures; `mise run test` → PASS.
- [ ] **Step 5: Commit** `git commit -m "Helm chart: exporter, ServiceMonitor, alerts, dashboard"`.

### Task 5: Grafana dashboard

**Files:**
- Replace: `deploy/helm/flexit-exporter/dashboards/flexit.json`
- Modify: `tests/test_chart.py`

- [ ] **Step 1: Write the failing test** `test_dashboard_metrics_exist`: every `flexit_[a-z_]+` name in any panel `expr` is in `{"flexit_up", "flexit_last_success_timestamp_seconds", "flexit_read_duration_seconds", "flexit_read_errors_total", "flexit_info"} | {f"flexit_{f}" for f in FIELDS}`; and at least 15 panels; uid `flexit`; `editable` false; every target's datasource uid `prometheus`.
- [ ] **Step 2: Run** — FAIL (placeholder has no panels).
- [ ] **Step 3: Write the dashboard** with the rows and panels listed in the spec's dashboard bullet. Mode mapping 1 Off, 2 Away, 3 Home, 4 High, 5 Cooker hood, 6 Fireplace, 7 Temporary high. Last read age = `time() - flexit_last_success_timestamp_seconds`.
- [ ] **Step 4: Run** `mise run test` — PASS.
- [ ] **Step 5: Commit** `git commit -m "Dashboard: Home / Flexit ventilation"`.

### Task 6: README and release 0.1.0

**Files:**
- Modify: `README.md`, `.env.example` (add `FLEXIT_INTERVAL=30`)

- [ ] **Step 1: README**: layout (package, chart, docs), the three entry points, the exporter's metrics and the stale-value rule, the release flow from the spec (bump Chart.yaml → tag `v<version>` → `mise run image:push`), the chart's values.
- [ ] **Step 2: Run** `mise run test` and `helm lint` — PASS.
- [ ] **Step 3: Commit** `git commit -m "README: monitoring app"`; tag `v0.1.0`.
- [ ] **Step 4: Owner step** (stop and hand over if the registry push is refused): `git push origin master --tags`, `mise run image:push`. Verify: `curl -s http://10.34.1.1:30095/v2/flexit-exporter/tags/list` lists `0.1.0`.

### Task 7: Deploy from homenet_2.0

Repo `~/Work/Personal/homenet_2.0`, its own worktree, its rules (`CLAUDE.md`: commit straight to `main`, `mise run check` before pushing, docs with every change, never a `kubectl` write).

**Files:**
- Create: `kubernetes/apps/flexit-exporter/application.yaml`, `kubernetes/apps/flexit-exporter/values.yaml`
- Modify: `scripts/test_platform.py` (`WAVES`, `MONITORED` or its equivalent for a chart with its own ServiceMonitor), `docs/runbooks/home-assistant.md` ("Flexit ventilation unit": the exporter, its dashboard and alerts) or a new `docs/runbooks/flexit.md`, `docs/runbooks/monitoring.md` (Home folder), then `mise run docs`.

- [ ] **Step 1: Application**: modelled on `kubernetes/apps/eve-universe/application.yaml` (multi-source, `$values`, `@branch@`): repo `https://github.com/p4ulie/flexit_nordic_s3.git`, `path: deploy/helm/flexit-exporter`, `targetRevision: v0.1.0`, namespace `flexit` with `CreateNamespace=true` and Pod Security `restricted` labels (`managedNamespaceMetadata`), sync wave after grafana (50), as the other apps; add `resources-finalizer.argocd.argoproj.io` so deleting the app removes the pod.
- [ ] **Step 2: values.yaml**: `flexit.host: 10.3.252.2`, `flexit.deviceId: 2` with a comment pointing at `inventory/site.yaml` `flexit-go`; all three toggles on.
- [ ] **Step 3: Register and test**: whatever `scripts/test_platform.py` requires for a new app (read `docs/runbooks/monitoring.md` "Adding an app"); `mise run check` → PASS.
- [ ] **Step 4: Commit and push** to `main` (`flexit-exporter: deploy 0.1.0 from flexit_nordic_s3`).
- [ ] **Step 5: Verify** (read-only): `kubectl -n flexit get pods` Running; Prometheus `flexit_up` = 1; Grafana folder Home shows "Home / Flexit ventilation" with data; `FlexitFilterChange` fires within the hour while the unit's filter alarm is on (it was on 2026-11-17).
