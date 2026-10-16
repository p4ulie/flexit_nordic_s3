"""Curses TUI: Overview / All values / Control screens."""

import asyncio
import curses
import time

from flexit import DEVICE_ID, HOST, read

REFRESH_S = 60  # same cadence as the HA integration
MODES = {1: "Off", 2: "Away", 3: "Home", 4: "High", 5: "Cooker hood", 6: "Fireplace", 7: "Temporary high"}
SCREENS = ["Overview", "All values", "Control"]

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


async def ventilation(unit, mode):
    # library: ventilation_mode is only honoured while the comfort button is active
    if mode != 2 and not unit.comfort_button:
        await unit.activate_comfort_button()
    await unit.set_ventilation_mode(mode)


# (label, asks for minutes, action(unit, minutes))
# ponytail: no Stop (unit off) entry on purpose; add with a stronger confirm if ever needed
ACTIONS = [
    ("Home", False, lambda u, m: ventilation(u, 3)),
    ("Away", False, lambda u, m: ventilation(u, 2)),
    ("High", False, lambda u, m: ventilation(u, 4)),
    ("Boost (temporary high)", True, lambda u, m: u.start_rapid_ventilation(m)),
    ("Fireplace", True, lambda u, m: u.start_fireplace_ventilation(m)),
]


# (section, field-name substrings); first match wins, unmatched land in "Other"
GROUPS = [
    ("Device", ("model", "serial", "device_name")),
    ("Filter", ("air_filter",)),
    ("Fan setpoints", ("fan_setpoint",)),
    ("Fans", ("fan",)),
    ("Modes", ("mode", "comfort", "cooker", "fireplace", "rapid", "setpoint_away", "setpoint_home")),
    ("Air", ("temperature", "humidity")),
    ("Heat exchanger", ("heat_exchanger",)),
    ("Heater", ("electric_heater",)),
]


def grouped(data):
    w = max(map(len, data), default=0)
    order = ["Device", "Modes", "Air", "Fans", "Fan setpoints", "Heat exchanger", "Heater", "Filter", "Other"]
    sections = {name: [] for name in order}
    for k, v in data.items():
        name = next((n for n, keys in GROUPS if any(s in k for s in keys)), "Other")
        sections[name].append(f"  {k:<{w}}  {v}")
    out = []
    for name, rows in sections.items():
        if rows:
            out += ([""] if out else []) + [name] + rows
    return out


def fmt(f, v):
    try:
        return f(v) if callable(f) else f.format(v)
    except (TypeError, ValueError):
        return str(v)


def body(screen, data, sel):
    if screen == 0:
        return [f"{label:<18}{fmt(f, data.get(k))}" if k else "" for label, k, f in BASIC]
    if screen == 1:
        return grouped(data)
    cur = f"Current mode: {MODES.get(data.get('operation_mode'), '?')}"
    return [cur, ""] + [("> " if i == sel else "  ") + a[0] for i, a in enumerate(ACTIONS)]


def ask(scr, prompt):
    rows, cols = scr.getmaxyx()
    scr.addnstr(rows - 1, 0, prompt.ljust(cols - 1), cols - 1, curses.A_BOLD)
    curses.echo()
    curses.curs_set(1)
    scr.timeout(-1)
    try:
        return scr.getstr(rows - 1, min(len(prompt), cols - 2), 6).decode().strip()
    finally:
        curses.noecho()
        curses.curs_set(0)
        scr.timeout(1000)


def ui(scr):
    curses.curs_set(0)
    scr.timeout(1000)
    data, msg, fetched = {}, "", 0.0
    screen, top, sel = 0, 0, 0

    def fetch(action=None, label="Reading…"):
        nonlocal data, msg, fetched
        scr.addnstr(0, 0, f" {label}".ljust(curses.COLS - 1), curses.COLS - 1, curses.A_REVERSE)
        scr.refresh()
        try:
            data = asyncio.run(read(HOST, DEVICE_ID, action))
            msg = ""
        except (TimeoutError, OSError) as e:
            msg = f"No answer from {HOST}: {e!r}"
        except Exception as e:  # write rejected by the unit / bad value
            msg = f"Failed: {e}"
        fetched = time.monotonic()

    while True:
        if time.monotonic() - fetched >= REFRESH_S:
            fetch()

        rows, cols = scr.getmaxyx()
        lines = body(screen, data, sel) if data else []
        top = max(0, min(top, len(lines) - (rows - 4)))
        scr.erase()
        x = 0
        for i, name in enumerate(SCREENS):
            tab = f" {i + 1} {name} "
            scr.addnstr(0, x, tab, max(0, cols - x - 1), curses.A_REVERSE if i == screen else curses.A_NORMAL)
            x += len(tab) + 1
        info = f"{HOST} · {int(time.monotonic() - fetched)}s ago"
        if x + len(info) < cols:
            scr.addstr(0, cols - len(info) - 1, info, curses.A_DIM)
        if msg:
            scr.addnstr(1, 0, msg, cols - 1, curses.A_BOLD)
        for i, line in enumerate(lines[top : top + rows - 4]):
            scr.addnstr(i + 2, 1, line, cols - 2, curses.A_BOLD if screen == 2 and line.startswith(">") else 0)
        keys = "1-3/Tab screen · ↑↓ " + ("select · Enter apply" if screen == 2 else "scroll") + " · r refresh · q quit"
        scr.addnstr(rows - 1, 0, " " + keys, cols - 1, curses.A_DIM)
        scr.refresh()

        key = scr.getch()
        if key in (ord("q"), 27):
            return
        if key == 9:
            screen, top = (screen + 1) % len(SCREENS), 0
        elif ord("1") <= key < ord("1") + len(SCREENS):
            screen, top = key - ord("1"), 0
        elif key == ord("r"):
            fetched = 0.0
        elif key in (curses.KEY_DOWN, ord("j")):
            if screen == 2:
                sel = min(sel + 1, len(ACTIONS) - 1)
            else:
                top += 1
        elif key in (curses.KEY_UP, ord("k")):
            if screen == 2:
                sel = max(sel - 1, 0)
            else:
                top = max(0, top - 1)
        elif key in (10, 13, curses.KEY_ENTER) and screen == 2:
            label, needs_minutes, action = ACTIONS[sel]
            minutes = 0
            if needs_minutes:
                raw = ask(scr, f" {label}: minutes (1-360, empty = cancel): ")
                if not raw.isdigit() or not 1 <= int(raw) <= 360:
                    msg = "Cancelled" if not raw else f"Invalid minutes: {raw}"
                    continue
                minutes = int(raw)
            what = f"{label} for {minutes} min" if minutes else label
            if ask(scr, f" Set {what}? [y/N] ").lower() != "y":
                msg = "Cancelled"
                continue
            fetch(lambda u: action(u, minutes), f"Setting {what}…")
            if not msg:
                msg = f"Done: {what} → mode now {MODES.get(data.get('operation_mode'), '?')}"


if __name__ == "__main__":
    curses.wrapper(ui)
