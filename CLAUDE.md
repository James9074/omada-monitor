# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A PyQt6 **macOS desktop app** that monitors clients connected to a TP-Link
Omada controller and shows them in a sortable, searchable, dark-themed table.
It auto-refreshes on a timer, stores controller credentials encrypted locally,
and is packaged as a `.app` bundle via py2app.

## Environment

- Use the **project virtualenv at `./env`** (Python 3.11). It is the interpreter
  the build links against. The repo's `python3` on PATH may be older (3.9) and
  lacks the dependencies.
- Install deps: `env/bin/python -m pip install -r requirements.txt`
  (`requests` is required transitively by `omada.py`).

## Common commands

```sh
# Run against a real controller (auto-logins if creds are saved)
env/bin/python omada_monitor.py

# Run the full UI with sample data, no controller needed
env/bin/python omada_monitor.py --demo        # or OMADA_DEMO=1

# Tests
env/bin/python test_core_logic.py             # pure-logic, self-contained
env/bin/python test_omada_monitor.py          # imports the app; headless (offscreen)

# Build the macOS .app (alias mode -- README calls this "Production")
env/bin/python setup.py py2app -A
```

The `py2app -A` (alias) bundle symlinks its python to `./env/bin/python`, so it
**depends on `./env` staying in place** and is not portable. `setup.py` only
runs `clean_builds()` (wipes `build/`+`dist/`) when `py2app` is in `argv`.

## Layout

- `omada_monitor.py` — the whole app: `OmadaClientMonitor` (main window),
  `LoginDialog` (validated login), `CredentialManager` (Fernet, files written
  `0600`), `DataRefreshWorker` (`QThread` that fetches clients off the UI
  thread, with a silent re-login retry on session expiry), `MockOmada` +
  `DEMO_MODE` (sample data), and `DARK_STYLESHEET`.
- `omada.py` — a **borrowed** Omada REST API wrapper
  (ghaberek/omada-api). Prefer not to restructure it; only targeted bug fixes.
  Note it uses **tabs** for indentation (the rest of the project uses 4 spaces).
- `setup.py` — py2app config and bundle metadata (version, `LSMinimumSystemVersion`).
- `test_core_logic.py`, `test_omada_monitor.py` — see constraints below.
- Credentials live at `~/.omada-monitor/` (`key`, `credentials.enc`).
- Prefs (window geometry, sort, refresh interval) persist via `QSettings`
  under org `wlan1` / app `OmadaMonitor`.

## Test contracts (don't break these)

`test_omada_monitor.py` imports the real module and pins behavior. When editing,
keep:
- Public names: `CredentialManager`, `SortableIPItem`, `SortableTableItem`,
  `LoginDialog`, `OmadaClientMonitor`, `ValidationError`, `DataRefreshWorker`.
- `SortableIPItem` sort keys are **4-tuples** (`(-1,-1,-1,-1)` for invalid IPs).
- `format_time(30) == '30'` (no unit suffix on sub-minute values).
- `DataRefreshWorker(omada)` constructible with a **single arg** (the credential
  manager is an optional second arg used only for re-login).
- `OmadaClientMonitor.format_client_data(None, client)` works (static helpers
  are referenced via the class, not `self`).

`test_core_logic.py` tests *copies* of the helpers, so it won't catch drift in
the real code — keep the two in sync by hand if you change formatting behavior.

## Conventions

- 4-space indentation everywhere except the borrowed `omada.py` (tabs).
- Network I/O must stay off the GUI thread (use `DataRefreshWorker`); the Omada
  session is given a request timeout via `apply_session_timeout`.
- Run both test suites and (ideally) a `--demo` launch before building.
