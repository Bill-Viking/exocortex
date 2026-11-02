#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hygiene-settings.py — the user's own sanitize periods, written down where the sweep reads them.

    python3 tools/hygiene-settings.py --get [<key>]
    python3 tools/hygiene-settings.py --set <key> <value>

THE PERIOD IS A SETTING: the user picks their own sanitize time period, and that choice is
theirs to change at any time. The four numbers
the session-hygiene watcher runs on live in ONE brain-synced file at the hub root,
`hygiene-settings.json`, and THIS TOOL IS ITS ONLY WRITER:

    grace_hours          how long a closed (ARCH) session stays visible — the user's morning memory
    ceiling              how many visible sessions he accepts on the screen
    routine_grace_hours  how long a superseded routine run rests (0: it is a dead tile at once)
    spoolup_quiet_hours  how long an untitled sitting must be quiet before it is even looked at

`archive-receipts.py` reads the file whenever the matching flag is not given, so the number a pass
uses is the user's. When he says "grace 12 h" or "ceiling 20", the session he says it to runs one
line — `--set grace_hours 12` — and he is never asked to edit JSON.

The write is atomic (a temporary file beside the real one, then one replace), keeps the file's own
mode, keeps every other key exactly as it found it, and creates the file with the built-in defaults
when there is none. It prints ONE line and nothing else, and it never asks a question: an unknown
key or a value that is not a number at or above zero is refused in one line with exit 2.

Stdlib only, Python 3.9-compatible, OS-neutral (macOS `python3`, Windows `python`). No model, no
network. Writes one file, in one place, and only when something changed.
"""
import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SETTINGS_FILE = "hygiene-settings.json"
# key · the built-in default · whole numbers only — the same four `archive-receipts.py` reads.
KEYS = (
    ("grace_hours", 24, False),
    ("ceiling", 12, True),
    ("routine_grace_hours", 0, False),
    ("spoolup_quiet_hours", 6, False),
)
DEFAULTS = dict((k, v) for k, v, _w in KEYS)
ORDER = [k for k, _v, _w in KEYS]
WHOLE = dict((k, w) for k, _v, w in KEYS)


def hub_dir(override=""):
    """The hub: --hub, else the folder this tool's own `tools/` sits in."""
    if override:
        return Path(os.path.expanduser(override)).resolve()
    return Path(__file__).resolve().parent.parent


def plain(v):
    """A number said the way a person writes it: `12`, `1.5` — never `12.0`."""
    try:
        f = float(v)
    except Exception:
        return str(v)
    return ("%d" % int(round(f))) if abs(f - round(f)) < 1e-9 else ("%.10g" % f)


def number(raw):
    """(value, "") for a number at or above zero, else (None, the one-line reason)."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None, "is not a number"
    if isinstance(raw, str):
        try:
            raw = float(raw.strip())
        except Exception:
            return None, "is not a number"
    f = float(raw)
    if f != f or f in (float("inf"), float("-inf")):
        return None, "is not a number"
    if f < 0:
        return None, "is below zero"
    return f, ""


def store(key, value):
    """What goes in the file: a whole number where the key takes one, ints kept as ints."""
    f = float(value)
    if WHOLE.get(key) or abs(f - round(f)) < 1e-9:
        return int(round(f))
    return f


def read_file(path):
    """(rows, trouble) — the file as a dict, or the defaults and one line saying why not."""
    try:
        if not path.is_file():
            return {}, "no %s at the hub root" % SETTINGS_FILE
    except Exception as e:
        return {}, "cannot reach %s (%s)" % (SETTINGS_FILE, e.__class__.__name__)
    try:
        with io.open(str(path), "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception as e:
        return {}, "cannot read %s (%s)" % (SETTINGS_FILE, e.__class__.__name__)
    if not isinstance(data, dict):
        return {}, "%s is not a JSON object" % SETTINGS_FILE
    return data, ""


def in_force(data):
    """The values a run would actually use: the file's, and the built-in default for anything it
    does not answer — the same rule `archive-receipts.py` applies, said out loud here."""
    out = dict(DEFAULTS)
    notes = []
    for key in ORDER:
        if key not in data:
            continue
        v, why = number(data.get(key))
        if v is None:
            notes.append("%s %s %s" % (key, json.dumps(data.get(key), ensure_ascii=False), why))
            continue
        out[key] = store(key, v)
    return out, notes


def write_atomic(path, data):
    """One replace, never a half-written settings file, and the file's own mode kept."""
    rows = dict(data)                               # a key the user added by hand is not dropped
    ordered = dict((k, rows.pop(k)) for k in ORDER if k in rows)
    ordered.update(rows)
    text = json.dumps(ordered, ensure_ascii=False, indent=1) + "\n"
    mode = None
    try:
        if path.is_file():
            mode = os.stat(str(path)).st_mode & 0o7777
    except Exception:
        mode = None
    if mode is None:                    # a NEW file reads like its neighbours, not like a
        try:                            # temporary one: mkstemp makes 0600, the umask decides here
            um = os.umask(0)
            os.umask(um)
            mode = 0o666 & ~um
        except Exception:
            mode = 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".part", dir=str(path.parent))
    try:
        with io.open(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def main(argv):
    ap = argparse.ArgumentParser(add_help=True,
                                 description="the user's own periods for the hygiene sweep")
    ap.add_argument("--get", nargs="?", const="", default=None, metavar="KEY")
    ap.add_argument("--set", nargs=2, default=None, metavar=("KEY", "VALUE"))
    ap.add_argument("--hub", default="")
    a = ap.parse_args(argv)

    if (a.get is None) == (a.set is None):
        sys.stderr.write("say one of --get [<key>], --set <key> <value>\n")
        return 2
    path = hub_dir(a.hub) / SETTINGS_FILE
    data, trouble = read_file(path)

    if a.get is not None:
        if a.get and a.get not in DEFAULTS:
            sys.stderr.write("no such setting: %s — the four are %s\n" % (a.get, ", ".join(ORDER)))
            return 2
        values, notes = in_force(data)
        for key in ([a.get] if a.get else ORDER):
            print("%s %s" % (key, plain(values[key])))
        if trouble:                                 # the values in force are still the truth
            print("# %s — these are the built-in defaults" % trouble)
        for note in notes:                          # one line per key the file spoiled
            print("# %s — the built-in default used instead" % note)
        return 0

    key, raw = a.set[0], a.set[1]
    if key not in DEFAULTS:
        sys.stderr.write("no such setting: %s — the four are %s\n" % (key, ", ".join(ORDER)))
        return 2
    value, why = number(raw)
    if value is None:
        sys.stderr.write("%s %s — nothing written\n" % (json.dumps(raw, ensure_ascii=False), why))
        return 2
    if trouble and not trouble.startswith("no "):    # a file we cannot parse is never clobbered
        sys.stderr.write("%s — nothing written\n" % trouble)
        return 2
    rows = dict(data) if data else dict(DEFAULTS)
    for k in ORDER:                                  # a file missing a key gets its default beside
        rows.setdefault(k, DEFAULTS[k])
    was = rows.get(key)
    rows[key] = store(key, value)
    if was == rows[key] and not trouble:
        print("%s %s · unchanged in %s" % (key, plain(rows[key]), SETTINGS_FILE))
        return 0
    write_atomic(path, rows)
    print("%s %s · written %s" % (key, plain(rows[key]), SETTINGS_FILE))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
