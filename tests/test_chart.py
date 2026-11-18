import json
import re
import subprocess

import yaml

CHART = "helm/flexit-exporter"
REQUIRED = ["--set", "flexit.host=10.3.252.2", "--set", "flexit.deviceId=2"]
TOGGLES = [
    "--set", "serviceMonitor.enabled=true",
    "--set", "prometheusRule.enabled=true",
    "--set", "dashboard.enabled=true",
]


def template(*args):
    return subprocess.run(["helm", "template", "t", CHART, *args], capture_output=True, text=True)


def render(*args):
    out = template(*args)
    assert out.returncode == 0, out.stderr
    return {d["kind"]: d for d in yaml.safe_load_all(out.stdout) if d}


def test_requires_host():
    assert template("--set", "flexit.deviceId=2").returncode != 0
    assert template("--set", "flexit.host=x").returncode != 0


def test_defaults_render_only_workload():
    docs = render(*REQUIRED)
    assert set(docs) == {"Deployment", "Service"}
    pod = docs["Deployment"]["spec"]["template"]["spec"]
    # a Service named flexit-exporter injects FLEXIT_EXPORTER_PORT=tcp://..., which the exporter reads as its port
    assert pod["enableServiceLinks"] is False
    assert pod["securityContext"] == {
        "runAsNonRoot": True,
        "runAsUser": 65534,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    c = pod["containers"][0]
    app_version = yaml.safe_load(open(f"{CHART}/Chart.yaml"))["appVersion"]
    assert c["image"] == f"10.34.1.1:30095/flexit-exporter:{app_version}"
    assert {e["name"] for e in c["env"]} == {"FLEXIT_HOST", "FLEXIT_DEVICE_ID", "FLEXIT_INTERVAL"}
    assert c["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    assert c["readinessProbe"]["tcpSocket"]["port"] == "metrics"
    assert c["livenessProbe"]["httpGet"] == {"path": "/metrics", "port": "metrics"}
    assert docs["Service"]["spec"]["ports"][0]["name"] == "metrics"
    assert docs["Service"]["spec"]["ports"][0]["port"] == 9877


def test_all_toggles():
    docs = render(*REQUIRED, *TOGGLES)
    assert set(docs) == {"Deployment", "Service", "ServiceMonitor", "PrometheusRule", "ConfigMap"}

    ep = docs["ServiceMonitor"]["spec"]["endpoints"][0]
    assert (ep["port"], ep["path"], ep["interval"]) == ("metrics", "/metrics", "30s")

    rules = {r["alert"]: r for g in docs["PrometheusRule"]["spec"]["groups"] for r in g["rules"]}
    assert {n: (r["expr"], r["for"]) for n, r in rules.items()} == {
        "FlexitUnreachable": ("flexit_up == 0", "15m"),
        "FlexitStale": ("time() - flexit_last_success_timestamp_seconds > 600 and flexit_up == 1", "5m"),
        "FlexitFilterChange": ("flexit_air_filter_polluted == 1", "1h"),
        "FlexitSupplyAirCold": ("flexit_supply_air_temperature < 15", "30m"),
    }
    assert all(r["labels"]["severity"] == "warning" for r in rules.values())

    cm = docs["ConfigMap"]
    assert cm["metadata"]["labels"]["grafana_dashboard"] == "1"
    assert cm["metadata"]["annotations"]["grafana_folder"] == "Home"
    assert json.loads(cm["data"]["flexit.json"])["uid"] == "flexit"


def test_dashboard_with_empty_labels_and_annotations():
    # Helm merges a {} over the defaults, so only null really empties the maps; both must still parse.
    docs = render(*REQUIRED, "--set", "dashboard.enabled=true",
                  "--set-json", "dashboard.labels={}", "--set-json", "dashboard.annotations={}")
    assert docs["ConfigMap"]["metadata"]["labels"]["grafana_dashboard"] == "1"
    docs = render(*REQUIRED, "--set", "dashboard.enabled=true",
                  "--set-json", "dashboard.labels=null", "--set-json", "dashboard.annotations=null")
    meta = docs["ConfigMap"]["metadata"]
    assert "grafana_dashboard" not in meta["labels"]
    assert "annotations" not in meta


def test_dashboard_metrics_exist():
    from flexit_nordic.flexit import FIELDS

    known = {
        "flexit_up", "flexit_last_success_timestamp_seconds", "flexit_read_duration_seconds",
        "flexit_read_errors_total", "flexit_info",
    } | {f"flexit_{f}" for f in FIELDS}
    with open(f"{CHART}/dashboards/flexit.json") as f:
        dash = json.load(f)
    assert dash["uid"] == "flexit" and dash["editable"] is False
    panels = [p for p in dash["panels"] if p["type"] != "row"]
    assert len(panels) >= 15
    for p in panels:
        assert p["datasource"] == {"type": "prometheus", "uid": "prometheus"}
        for t in p["targets"]:
            assert t["datasource"]["uid"] == "prometheus"
            used = set(re.findall(r"flexit_[a-z_]+", t["expr"]))
            assert used and used <= known, used - known
