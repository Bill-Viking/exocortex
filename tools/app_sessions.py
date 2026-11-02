#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app_sessions.py — what the Claude desktop app's own session store says about its windows.

    python3 tools/app_sessions.py            one line per window touched in the last two days
    python3 tools/app_sessions.py --json     the same, as data

The desktop app keeps one small JSON record per window in its data folder:
    macOS    ~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/local_<id>.json
    Windows  %APPDATA%\\Claude\\claude-code-sessions\\<account>\\<org>\\local_<id>.json
Each record carries (read first-hand on macOS): `sessionId` (the app's own id,
`local_…` — the one the app's send-message tool takes), `cliSessionId` (the transcript's stem —
the id every exocortex tool and the pulse use), `title`, `isArchived`, `lastActivityAt` (ms, the
window's last real exchange), `lastFocusedAt` (ms, the last time the window was brought to the
front), `scheduledTaskId` (present on a routine's run), `model` and `cwd`.

THIS FILE ONLY READS. It never writes the store, never guesses a field the record does not
carry, and never raises: an unreadable record is skipped. Remote Control's `remoteControlActive`
is NOT in the store (the app's session list reports it; a tool cannot read that list) — so it is
not offered here, and every caller says so instead of pretending.

Stdlib only, Python 3.9, OS-neutral. Only records whose file changed inside `max_age_days` are
opened, so a store of four hundred windows costs a few dozen reads.
"""
import glob
import json
import os
import sys
import time

STORE_PARTS = ("Claude", "claude-code-sessions")


def store_dirs(home=None, appdata=None):
    """Every <account>/<org> folder of the app's session store on this machine."""
    home = home or os.path.expanduser("~")
    if appdata is None:
        appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    bases = [os.path.join(home, "Library", "Application Support", *STORE_PARTS),
             os.path.join(appdata, *STORE_PARTS)]
    out = []
    for base in bases:
        for d in sorted(glob.glob(os.path.join(base, "*", "*"))):
            if os.path.isdir(d) and d not in out:
                out.append(d)
    return out


def _ms(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v / 1000.0 if v > 1e11 else v


def records(home=None, max_age_days=2.0, at=None, appdata=None):
    """[{local_id, cli_id, title, archived, last_activity, last_focused, scheduled, model, cwd,
    file}] for every window record whose file changed inside max_age_days. Times are epoch
    seconds or None. Never raises."""
    at = at if at is not None else time.time()
    floor = at - float(max_age_days) * 86400.0
    out = []
    for d in store_dirs(home, appdata):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for name in names:
            if not (name.startswith("local_") and name.endswith(".json")):
                continue
            path = os.path.join(d, name)
            try:
                if os.path.getmtime(path) < floor:
                    continue
                with open(path, encoding="utf-8", errors="replace") as fh:
                    rec = json.load(fh)
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict):
                continue
            out.append({
                "local_id": str(rec.get("sessionId") or name[:-5]),
                "cli_id": str(rec.get("cliSessionId") or ""),
                "title": str(rec.get("title") or ""),
                "archived": bool(rec.get("isArchived")),
                "last_activity": _ms(rec.get("lastActivityAt")),
                "last_focused": _ms(rec.get("lastFocusedAt")),
                "scheduled": bool(rec.get("scheduledTaskId")),
                "model": str(rec.get("model") or ""),
                "cwd": str(rec.get("cwd") or ""),
                "file": path,
            })
    return out


def fronted(recs):
    """The window most recently brought to the front — the newest `lastFocusedAt` among the
    windows that are not archived and not a routine's run — or None. It says which window
    the app last FOCUSED; whether the app itself is in front of the desktop is not in the
    store and is not claimed."""
    best = None
    for r in recs:
        if r["archived"] or r["scheduled"] or r["last_focused"] is None:
            continue
        if best is None or r["last_focused"] > best["last_focused"]:
            best = r
    return best


def by_cli(recs):
    """{transcript stem: record} — the newest record wins when two name one transcript."""
    out = {}
    for r in recs:
        cid = r.get("cli_id")
        if not cid:
            continue
        old = out.get(cid)
        if old is None or (r["last_activity"] or 0) > (old["last_activity"] or 0):
            out[cid] = r
    return out


def main(argv):
    recs = records(max_age_days=2.0)
    front = fronted(recs)
    if "--json" in argv:
        sys.stdout.write(json.dumps({"records": recs,
                                     "fronted": front["local_id"] if front else None},
                                    indent=1) + "\n")
        return 0
    for r in sorted(recs, key=lambda r: -(r["last_activity"] or 0)):
        mark = "*" if front is not None and r is front else " "
        sys.stdout.write("%s %s  %s  %s\n" % (mark, r["local_id"], r["cli_id"][:8] or "-",
                                             (r["title"] or "(untitled)")[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
