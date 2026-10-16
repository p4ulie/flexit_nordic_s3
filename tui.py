"""Curses TUI: basic view, Tab for the full list. Read-only."""

import asyncio
import curses
import time

from flexit import DEVICE_ID, HOST, read

REFRESH_S = 60  # same cadence as the HA integration
MODES = {1: "Off", 2: "Away", 3: "Home", 4: "High", 5: "Cooker hood", 6: "Fireplace", 7: "Temporary high"}

# (label, field, format)
BASIC = [
    ("Model", "model", "{}"),
    ("Serial", "serial_number", "{}"),
    ("Mode", "operation_mode", lambda v: MODES.get(v, v)),
    ("", None, None),
    ("Outside", "outside_air_temperature", "{:.1f} °C"),
    ("Supply", "supply_air_temperature", "{:.1f} °C"),
    ("Extract", "extract_air_temperature", "{:.1f} °C"),
    ("Exhaust", "exhaust_air_temperature", "{:.1f} °C"),
    ("Extract humidity", "extract_air_humidity", "{:.0f} %"),
    ("", None, None),
    ("Supply fan", "supply_air_fan_control_signal", "{} %"),
    ("Exhaust fan", "exhaust_air_fan_control_signal", "{} %"),
    ("HX efficiency", "heat_exchanger_efficiency", "{} %"),
    ("Electric heater", "electric_heater_power", "{:.2f} kW"),
    ("", None, None),
    ("Filter hours", "air_filter_operating_time", "{:.0f} h"),
    ("Filter interval", "air_filter_exchange_interval", "{:.0f} h"),
    ("Filter dirty", "air_filter_polluted", lambda v: "YES" if v else "no"),
]


def fmt(f, v):
    try:
        return f(v) if callable(f) else f.format(v)
    except (TypeError, ValueError):
        return str(v)


def lines(data, full):
    if full:
        w = max(map(len, data))
        return [f"{k:<{w}}  {v}" for k, v in data.items()]
    return [f"{label:<18}{fmt(f, data.get(k))}" if k else "" for label, k, f in BASIC]


def ui(scr):
    curses.curs_set(0)
    scr.timeout(1000)
    data, err, fetched, full, top = {}, None, 0.0, False, 0
    while True:
        if time.monotonic() - fetched >= REFRESH_S:
            scr.addstr(0, 0, "Reading…".ljust(curses.COLS - 1), curses.A_REVERSE)
            scr.refresh()
            try:
                data, err = asyncio.run(read(HOST, DEVICE_ID)), None
            except (TimeoutError, OSError) as e:
                err = f"No answer from {HOST}: {e!r}"
            fetched = time.monotonic()

        rows, cols = scr.getmaxyx()
        body = lines(data, full) if data else []
        top = max(0, min(top, len(body) - (rows - 3)))
        age = int(time.monotonic() - fetched)
        scr.erase()
        head = f" Flexit {HOST} · {'full' if full else 'basic'} · {age}s ago "
        scr.addnstr(0, 0, head.ljust(cols - 1), cols - 1, curses.A_REVERSE)
        if err:
            scr.addnstr(1, 0, err, cols - 1, curses.A_BOLD)
        for i, line in enumerate(body[top : top + rows - 3]):
            scr.addnstr(i + 2, 1, line, cols - 2)
        scr.addnstr(rows - 1, 0, " Tab basic/full · r refresh · ↑↓ scroll · q quit", cols - 1, curses.A_DIM)
        scr.refresh()

        key = scr.getch()
        if key in (ord("q"), 27):
            return
        if key == 9:
            full, top = not full, 0
        elif key == ord("r"):
            fetched = 0.0
        elif key in (curses.KEY_DOWN, ord("j")):
            top += 1
        elif key in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)


if __name__ == "__main__":
    curses.wrapper(ui)
