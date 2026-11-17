import asyncio

from prometheus_client import CollectorRegistry, generate_latest

from flexit_nordic.exporter import FlexitCollector, State, poll_once

GOOD = {
    "supply_air_temperature": 22.5,
    "air_filter_polluted": True,
    "operation_mode": 3,
    "model": "S3",
    "device_name": "x",
    "serial_number": "1",
}


def render(state):
    registry = CollectorRegistry()
    registry.register(FlexitCollector(state))
    return generate_latest(registry).decode()


def ok(data):
    async def reader(host, device_id):
        return data

    return reader


async def boom(host, device_id):
    raise TimeoutError("no answer")


def test_before_first_read():
    out = render(State())
    assert "flexit_up 0.0" in out
    assert "flexit_supply_air_temperature" not in out


def test_good_read():
    state = State()
    poll_once(state, "h", 2, reader=ok(GOOD))
    out = render(state)
    assert "flexit_up 1.0" in out
    assert "flexit_supply_air_temperature 22.5" in out
    assert "flexit_air_filter_polluted 1.0" in out
    assert "flexit_operation_mode 3.0" in out
    assert 'flexit_info{device_name="x",model="S3",serial_number="1"} 1.0' in out
    assert "flexit_last_success_timestamp_seconds " in out
    assert "flexit_read_duration_seconds " in out


def test_good_read_without_identity_fields():
    state = State()
    poll_once(state, "h", 2, reader=ok({"supply_air_temperature": 22.5}))
    out = render(state)
    assert "flexit_up 1.0" in out
    assert "flexit_supply_air_temperature 22.5" in out


def test_failed_read_after_success(caplog):
    state = State()
    poll_once(state, "h", 2, reader=ok(GOOD))
    first = state.last_success
    poll_once(state, "h", 2, reader=boom)
    out = render(state)
    assert "flexit_up 0.0" in out
    assert "flexit_read_errors_total 1.0" in out
    line = next(l for l in out.splitlines() if l.startswith("flexit_last_success_timestamp_seconds "))
    assert float(line.split()[1]) == first  # exposition uses scientific notation, so compare numbers
    assert "flexit_supply_air_temperature" not in out
    assert "TimeoutError" in caplog.text


def test_strings_and_none_skipped():
    state = State()
    poll_once(state, "h", 2, reader=ok({"a": "<KeyError>", "b": None, "c": 1, **{k: GOOD[k] for k in ("model", "device_name", "serial_number")}}))
    out = render(state)
    assert "flexit_a " not in out and "flexit_b " not in out
    assert "flexit_c 1.0" in out
