#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""carrier_preflight.py — the engine checks the carriers before the brain moves.

Before every brain pull — the pulse's beat, the scheduled sync, `sync.py pull`, `sync.py sync`,
`sync.py preflight`, and this file run on its own — the engine reads what the RECORD says is owed
by a carrier that is not the cloud (a transfer-drive payload in a drive ledger, a private git host
named in machine.json), checks each carrier FIRST-HAND, and prints ONE plain sentence when one is
missing. The brain then syncs regardless: the brain never waits on the drive.

    the record        open `- [ ]` lines carrying `OWED TO THE <NAME>` in the hub's STATUS.md and
                      every <projects root>/*/STATUS.md; the payload is the last `*-TX-nnn` token
                      before the phrase; a `- [x]` line is settled and is not owed
    the carrier word  every owed item says what holds it. `OWED TO THE <NAME>` is the
                      transfer DRIVE; `waits in the <NAME>'s outbox [for the <TO>]` is that
                      machine's own LOCAL OUTBOX — staged there, not on the drive yet. An outbox
                      item is said as `<payload> waits in the <NAME>'s outbox`, never as "land it"
                      and never as a reason to plug the drive in
    the registry      the `carriers` block of machine.json, written by `sync.py carriers`
    the drive         found by its LABEL, never a letter: the Win32 volume API on Windows,
                      /Volumes/<label> on macOS, the usual mount roots elsewhere. Probed on EVERY
                      run a label is declared: `state` (mounted/absent/no-letter/undeclared) says
                      whether the drive is here, `needed` whether anything is owed to it. Nothing
                      owed is not the same as nothing there
    the hosts         `git ls-remote --exit-code <url> HEAD` under a short timeout
    the sentence      one `!  plug in "<label>" — <payload> is owed to the <MACHINE>` line, in the
                      pull's own "needs your call" grammar, so pulse.py's flag parser carries it
    the bytes         <hub>/carriers-<machine>.json, written atomically — the tree's drive panel
                      reads it

Nothing here ever raises: an internal error becomes one `  carriers: skipped — …` line and the
pull continues. A broken checker must never stop the brain.

Standalone:
    python carrier_preflight.py --machine-json <file> --hub <dir> --projects <dir>
                                [--timeout N] [--json] [--no-state]
    exit 0 = nothing missing · exit 3 = a carrier is missing · exit 2 = bad arguments

Python 3 standard library only. Runs identically on macOS and Windows.
"""

import argparse
import datetime
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

WINDOWS = platform.system() == "Windows"

# The drive ledger's grammar.
#   `- [ ]` or `- [ ] !`, then anything, then `OWED TO THE <NAME>`.
BOX_RE = re.compile(r"^\s*-\s+\[(?P<box>[ xX])\]\s*(?P<rest>.*)$")
OWED_RE = re.compile(r"OWED TO THE ([A-Z][A-Z0-9]*)")
# a payload staged in a machine's OWN local outbox, not on the drive yet —
#   `- [ ] DRIVE LEDGER · LOCAL OUTBOX — AB-TX-008 waits in the SOUTH's outbox for the NORTH (…)`
OUTBOX_RE = re.compile(r"waits in the ([A-Z][A-Z0-9]*)['\u2019]s outbox(?:\s+for the ([A-Z][A-Z0-9]*))?")
# The phrase must sit this close to the start of the item text to be a ledger
# line at all (see owed_from_line).
LEDGER_PHRASE_WITHIN = 120
# A payload id: AB-TX-009, ABC-TX-027, AB-GATE-TX-002 — any dash-joined capitals before -TX-<n>.
PAYLOAD_RE = re.compile(r"(?<![A-Za-z0-9-])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-TX-(?:[A-Z]+-)?[0-9]+")  # a series segment (AB-TX-SL-004) is allowed

MAX_TIMEOUT = 10.0          # T defaults to 5 s per host, hard-capped at 10
STATE_PREFIX = "carriers-"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _now_local():
    """ISO-8601 local time with its offset — the reader compares it to their own clock."""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _one_line(exc):
    """An exception as ONE line, never a traceback."""
    text = "%s: %s" % (type(exc).__name__, exc)
    return " ".join(text.split())[:200]


def _secs(value):
    """5.0 -> '5', 2.5 -> '2.5' — a number a human reads."""
    return ("%g" % float(value))


def _python_word():
    """`python` on Windows, `python3` elsewhere — chosen the way install.py chooses it."""
    base = os.path.basename(sys.executable or "")
    return "python" if base.lower() in ("python", "python.exe") else "python3"


def _read_text(path):
    try:
        with open(str(path), "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def _read_json(path, default=None):
    try:
        with open(str(path), "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def _when(iso):
    """An ISO stamp as `YYYY-MM-DD HH:MM`, or the raw text when it will not parse."""
    if not iso:
        return "at an unrecorded time"
    text = str(iso).strip()
    cleaned = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.datetime.fromisoformat(cleaned).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


# --------------------------------------------------------------------------
# the record — what is owed by a carrier
# --------------------------------------------------------------------------

def status_files(hub, projects_root):
    """The hub's STATUS.md and every <projects root>/*/STATUS.md, each with its display name."""
    found = []
    hub = Path(hub)
    hub_status = hub / "STATUS.md"
    if hub_status.is_file():
        found.append((hub_status, "STATUS.md"))
    projects_root = Path(projects_root)
    try:
        children = sorted(p for p in projects_root.iterdir() if p.is_dir())
    except OSError:
        children = []
    for child in children:
        status = child / "STATUS.md"
        if status.is_file():
            found.append((status, "%s/STATUS.md" % child.name))
    return found


NO_ID_WHY = "no payload id in its first words"


class Unreadable(tuple):
    """What a ledger reader returns for a line that carries the ledger phrase but names no
    payload id before it. It unpacks exactly as a parsed line does — `(payload, to)` or
    `(payload, to, at)` — with `payload` None, and it carries `why`, so a caller can always tell
    it apart (`payload is None`, or `isinstance(item, Unreadable)`) and never mistakes a note's
    words for a payload's name."""
    why = NO_ID_WHY


def owed_from_line(rest):
    """(payload, to) for one open item's text, or None when it names no carrier."""
    match = OWED_RE.search(rest)
    if not match:
        return None
    # A LEDGER line carries the phrase in its first words ("! DRIVE LEDGER -
    # AB-TX-011 OWED TO THE NORTH (…"); a narrative item that merely mentions an
    # old debt ("… (was: OWED TO THE NORTH …") carries it hundreds of characters
    # in. On real ledgers every true line is under 40 and a false match is
    # well over 400, and a narrative line read as a ledger line would print a
    # stale payload sentence.
    if match.start() > LEDGER_PHRASE_WITHIN:
        return None
    before = rest[:match.start()]
    ids = PAYLOAD_RE.findall(before)
    if not ids:
        # a line with the phrase and no payload id in its first words is a human NOTE
        # ("DRIVE LEDGER - EVENING CUT OWED TO THE SOUTH …"), never a payload. Its words were once
        # taken as the payload's name, and the owed count grew a payload nobody cut.
        return Unreadable((None, match.group(1)))
    return ids[-1], match.group(1)


def outbox_from_line(rest):
    """(payload, to, at) for an open item that says a payload WAITS IN a machine's outbox, or
    None. `at` is the machine whose local outbox holds it; `to` is the machine it is for (the
    words after `for the`), '' when the line does not say. The phrase must sit in the item's
    first words, exactly as a drive line's must (LEDGER_PHRASE_WITHIN)."""
    match = OUTBOX_RE.search(rest)
    if not match or match.start() > LEDGER_PHRASE_WITHIN:
        return None
    ids = PAYLOAD_RE.findall(rest[:match.start()])
    if not ids:                                   # no id, no payload — the same rule
        return Unreadable((None, (match.group(2) or ""), match.group(1)))
    return ids[-1], (match.group(2) or ""), match.group(1)


def read_ledger(hub, projects_root, machine_name):
    """Every OPEN owed item in the record, in the order it was read — each with the CARRIER that
    holds it: `drive` for `OWED TO THE <NAME>`, `outbox` (and `at`, the machine whose outbox) for
    `waits in the <NAME>'s outbox`. When one line carries both phrases the earlier one names it.

    A `- [x]` line never counts — settled is settled. A line that names no payload id is never an
    owed item; `read_ledger_full` returns those as `unreadable`."""
    return read_ledger_full(hub, projects_root, machine_name)["owed"]


def read_ledger_full(hub, projects_root, machine_name):
    """{"owed": [... read_ledger's items ...], "unreadable": [{"file", "line", "text", "why"}]} —
    an OPEN line that carries a ledger phrase in its first words but no payload id before it is
    UNREADABLE: named by its file and line, never counted as a payload."""
    owed, unreadable = [], []
    mine = (machine_name or "").strip().lower()
    for path, display in status_files(hub, projects_root):
        text = _read_text(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            box = BOX_RE.match(line)
            if not box or box.group("box") != " ":
                continue
            rest = box.group("rest")
            item = owed_from_line(rest)
            waiting = outbox_from_line(rest)
            if waiting is not None and item is not None:
                if OUTBOX_RE.search(rest).start() < OWED_RE.search(rest).start():
                    item = None
                else:
                    waiting = None
            found = item if item is not None else waiting
            if found is not None and found[0] is None:
                unreadable.append({
                    "file": display,
                    "line": number,
                    "text": _short(rest),
                    "why": getattr(found, "why", NO_ID_WHY),
                })
                continue
            if item is not None:
                payload, to = item
                owed.append({
                    "payload": payload,
                    "to": to,
                    "carrier": "drive",
                    "direction": "to-me" if to.strip().lower() == mine else "from-me",
                    "file": display,
                    "line": number,
                })
            elif waiting is not None:
                payload, to, at = waiting
                if to:
                    direction = "to-me" if to.strip().lower() == mine else "from-me"
                else:                 # the line names no destination: whose outbox decides
                    direction = "from-me" if at.strip().lower() == mine else "to-me"
                owed.append({
                    "payload": payload,
                    "to": to,
                    "carrier": "outbox",
                    "at": at,
                    "direction": direction,
                    "file": display,
                    "line": number,
                })
    return {"owed": owed, "unreadable": unreadable}


def _short(text, limit=80):
    """One line of a ledger item, at most `limit` characters, for a reader to recognise it."""
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[:limit - 1].rstrip() + "\u2026"


def mark_landed(owed, hub, machine_name):
    """The landing ledger settles a to-me payload: the drive is not asked for.

    An absent or unreadable ledger changes nothing — the payload stays owed."""
    ledger = _read_json(Path(hub) / ("landings-%s.json" % machine_name), default=None)
    landings = (ledger or {}).get("landings") or {}
    if not isinstance(landings, dict):
        return owed
    for item in owed:
        entry = landings.get(item["payload"])
        if isinstance(entry, dict) and entry.get("state") == "landed":
            item["landed"] = entry.get("landed") or entry.get("seen") or ""
            item["landed_by"] = entry.get("by") or "auto-land"
    return owed


# --------------------------------------------------------------------------
# the probes — the drive by its label, the hosts by a short reach test
# --------------------------------------------------------------------------

def _windows_volumes():
    """Every volume this machine has: its label and its first path (None = no drive letter).

    restype and argtypes are set explicitly — a bare FindFirstVolumeW truncates the handle on
    64-bit Python and crashes. SetErrorMode keeps an empty card
    reader from raising a modal 'no disk in drive' box at us."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.FindFirstVolumeW.restype = wintypes.HANDLE
    k32.FindFirstVolumeW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
    k32.FindNextVolumeW.restype = wintypes.BOOL
    k32.FindNextVolumeW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD]
    k32.FindVolumeClose.restype = wintypes.BOOL
    k32.FindVolumeClose.argtypes = [wintypes.HANDLE]
    k32.GetVolumeInformationW.restype = wintypes.BOOL
    k32.GetVolumeInformationW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    k32.GetVolumePathNamesForVolumeNameW.restype = wintypes.BOOL
    k32.GetVolumePathNamesForVolumeNameW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k32.SetErrorMode.restype = wintypes.UINT
    k32.SetErrorMode.argtypes = [wintypes.UINT]

    SEM_FAILCRITICALERRORS, SEM_NOOPENFILEERRORBOX = 0x0001, 0x8000
    INVALID_HANDLE = ctypes.c_void_p(-1).value
    previous_mode = k32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX)
    volumes = []
    try:
        name = ctypes.create_unicode_buffer(300)
        handle = k32.FindFirstVolumeW(name, 300)
        if not handle or handle == INVALID_HANDLE:
            return volumes
        try:
            while True:
                volume = name.value
                label_buf = ctypes.create_unicode_buffer(261)
                fs_buf = ctypes.create_unicode_buffer(261)
                serial, max_component, flags = (wintypes.DWORD(), wintypes.DWORD(),
                                                wintypes.DWORD())
                got = k32.GetVolumeInformationW(
                    volume, label_buf, 261, ctypes.byref(serial),
                    ctypes.byref(max_component), ctypes.byref(flags), fs_buf, 261)
                label = label_buf.value.strip() if got else ""
                needed = wintypes.DWORD(0)
                path_buf = ctypes.create_unicode_buffer(2048)
                has_paths = k32.GetVolumePathNamesForVolumeNameW(
                    volume, path_buf, 2048, ctypes.byref(needed))
                paths = []
                if has_paths and needed.value:
                    raw = "".join(path_buf[:needed.value])
                    paths = [p for p in raw.split("\x00") if p]
                volumes.append({"label": label, "path": paths[0] if paths else None})
                if not k32.FindNextVolumeW(handle, name, 300):
                    break
        finally:
            k32.FindVolumeClose(handle)
    finally:
        k32.SetErrorMode(previous_mode)
    return volumes


def _posix_volumes():
    """The mount roots a labelled volume lands under on macOS and Linux."""
    roots = [Path("/Volumes")]
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    if user:
        roots += [Path("/media") / user, Path("/run/media") / user]
    roots += [Path("/media"), Path("/mnt")]
    volumes, seen = [], set()
    for root in roots:
        try:
            children = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            continue
        for child in children:
            key = (child.name, str(child))
            if key in seen:
                continue
            seen.add(key)
            try:
                mounted = os.path.ismount(str(child))
            except OSError:
                mounted = False
            if mounted:
                volumes.append({"label": child.name, "path": str(child)})
    return volumes


def real_volumes():
    """[{'label': str, 'path': str|None}, …] — this machine's volumes, first-hand."""
    return _windows_volumes() if WINDOWS else _posix_volumes()


def find_volume(label, volumes):
    """The volume carrying this LABEL, or None. Case-insensitive on Windows only."""
    wanted = (label or "").strip()
    if not wanted:
        return None
    for volume in volumes or []:
        have = (volume.get("label") or "").strip()
        if have == wanted or (WINDOWS and have.lower() == wanted.lower()):
            return volume
    return None


def _kill_tree(proc):
    """Kill a child AND every descendant. A plain timeout kills only the direct child: on Windows
    `git` from PowerShell or cmd is Git\\cmd\\git.exe, a launcher whose grandchild can keep the
    pipes open and hang a run for many minutes."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _run_bounded(args, timeout, env=None):
    """(returncode, combined output); 124 when the timeout fired. The tree dies BEFORE the pipes
    are drained, so a grandchild can never hold this beat open."""
    kw = {} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, **kw)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, (out or b"").decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out = b""
        return 124, (out or b"").decode("utf-8", "replace")


def real_reach(url, timeout=5.0):
    """(up, milliseconds, why) for one host, by the shortest honest question git can ask.

    Exit 0 = the host answered and HEAD resolves. Exit 2 is `--exit-code`'s "no matching refs":
    the host ANSWERED, it simply has no HEAD yet (a freshly initialised bare repo) — that is up.
    Anything else, or no answer at all, is down."""
    started = time.time()
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"          # never stop a beat at a password prompt
    env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")
    env.setdefault("GCM_INTERACTIVE", "never")
    try:
        code, out = _run_bounded(["git", "ls-remote", "--exit-code", url, "HEAD"],
                                 max(0.1, float(timeout)), env=env)
        elapsed = int((time.time() - started) * 1000)
        if code == 124:
            return False, elapsed, "did not answer within %s s" % _secs(timeout)
        if code in (0, 2):
            return True, elapsed, ""
        why = out.strip().splitlines()
        return False, elapsed, (why[0][:200] if why else "git exited %d" % code)
    except Exception as exc:                                  # git missing, url unusable, …
        return False, int((time.time() - started) * 1000), _one_line(exc)


# --------------------------------------------------------------------------
# the sentences
# --------------------------------------------------------------------------

def _joined(items):
    return ", ".join(items)


def format_lines(result):
    """Every stdout line the pull will print for this result, in order."""
    if result.get("error"):
        return ["  carriers: skipped — %s" % result["error"]]

    lines = []
    machine_upper = (result.get("machine") or "this machine").upper()
    drive = result.get("drive") or {}
    owed = result.get("owed") or []
    to_me = [o for o in owed if o.get("direction") == "to-me"]
    landed = [o for o in to_me if o.get("landed") is not None]
    waiting = [o for o in to_me if o.get("landed") is None and o.get("carrier", "drive") == "drive"]
    outboxed = [o for o in to_me if o.get("landed") is None and o.get("carrier") == "outbox"]
    ids = [o["payload"] for o in waiting]
    refs = ["%s:%d" % (o["file"], o["line"]) for o in waiting]
    verb = "is" if len(ids) == 1 else "are"
    label = drive.get("label")
    state = drive.get("state")

    if waiting:              # the drive's presence is recorded every run; it is SPOKEN about
                             # only when something is owed here — a quiet machine stays quiet
        if state == "absent":
            lines.append('  !  plug in "%s" — %s %s owed to the %s (%s)'
                         % (label, _joined(ids), verb, machine_upper, _joined(refs)))
        elif state == "no-letter":
            lines.append('  !  "%s" is connected but has no drive letter — open HFS+ for Windows '
                         'and click Mount · %s %s owed to the %s'
                         % (label, _joined(ids), verb, machine_upper))
        elif state == "undeclared":
            lines.append('  !  %s %s owed to the %s but machine.json names no drive — run: '
                         '%s sync.py carriers --drive "<label>"'
                         % (_joined(ids), verb, machine_upper, _python_word()))
        elif state == "mounted":
            lines.append('  carrier: "%s" is here — %s owed to the %s, land it'
                         % (label, _joined(ids), machine_upper))

    for item in outboxed:                     # staged in a machine's own outbox — the
                                              # drive is not asked for, nothing is to land yet
        lines.append("  carrier: %s waits in the %s's outbox (%s:%d)"
                     % (item["payload"], str(item.get("at") or "other machine").upper(),
                        item["file"], item["line"]))

    for item in landed:                       # settled by the landing ledger — quiet, and it names the tidy-up
        lines.append("  carrier: %s landed %s by %s — settle %s:%d"
                     % (item["payload"], _when(item.get("landed")),
                        item.get("landed_by") or "auto-land", item["file"], item["line"]))

    for host in result.get("hosts") or []:
        if host.get("state") != "down":
            continue
        repos = host.get("repos") or []
        if repos:
            through = "%s %s through it" % (_joined(repos), "syncs" if len(repos) == 1 else "sync")
        else:
            through = "it is a declared host"
        lines.append("  !  turn on %s — %s (%s %s)"
                     % (host.get("name") or "the host", through, host.get("url") or "",
                        host.get("why") or "did not answer"))

    if not lines:
        lines.append("  carriers: ok (nothing owed)")
    return lines


# --------------------------------------------------------------------------
# the check itself — never raises
# --------------------------------------------------------------------------

def _carriers_block(machine):
    """The machine's `carriers` block, with the test-mode override applied.

    ORCHSYNC_CARRIERS replaces the block ONLY while ORCHSYNC_TEST_ROOT is set (sync.py's
    rehearsal switch), so a rehearsal can describe any carrier without touching machine.json."""
    block = (machine or {}).get("carriers") or {}
    if os.environ.get("ORCHSYNC_TEST_ROOT", "").strip():
        override = os.environ.get("ORCHSYNC_CARRIERS", "").strip()
        if override:
            loaded = _read_json(Path(override), default=None)
            if isinstance(loaded, dict):
                block = loaded
    return block if isinstance(block, dict) else {}


def run(machine, hub, projects_root, timeout=5.0, probes=None):
    """Check every carrier the record says is owed. NEVER raises; the pull always continues."""
    machine = machine or {}
    name = str(machine.get("name") or "unknown")
    result = {
        "machine": name,
        "checked": _now_local(),
        "missing": False,
        "say": "",
        "lines": [],
        "drive": {"label": None, "state": "undeclared", "path": None, "needed": False},
        "hosts": [],
        "owed": [],
    }
    try:
        timeout = min(max(0.1, float(timeout or 5.0)), MAX_TIMEOUT)
        probes = probes or {}
        volumes_probe = probes.get("volumes") or real_volumes
        reach_probe = probes.get("reach") or real_reach

        block = _carriers_block(machine)
        declared = ((block.get("drive") or {}).get("label") or "").strip() or None
        hosts = [h for h in (block.get("hosts") or []) if isinstance(h, dict)]

        owed = mark_landed(read_ledger(hub, projects_root, name), hub, name)
        result["owed"] = owed
        waiting = [o for o in owed if o["direction"] == "to-me" and o.get("landed") is None
                   and o.get("carrier", "drive") == "drive"]      # an outbox item never asks for the drive

        # --- the drive, by its label ---------------------------------------
        # Check first-hand, the engine too: whenever a label is declared
        # the volume is PROBED on this run, whatever is owed. `state` says whether the drive is
        # HERE, `needed` whether anything wants it — one field never carries both facts again.
        # The sentence does not change: format_lines speaks about the drive only when something
        # is owed, so a quiet machine stays quiet while the record tells the truth.
        drive = {"label": declared, "state": "undeclared", "path": None, "needed": bool(waiting)}
        if declared is not None:
            volume = find_volume(declared, volumes_probe())
            if volume is None:
                drive["state"] = "absent"
            elif volume.get("path"):
                drive["state"] = "mounted"
                drive["path"] = volume["path"]
            else:
                drive["state"] = "no-letter"      # a volume mounted by a third-party
                                                  # driver can have no letter
        result["drive"] = drive

        # --- each host, by a short reach test -------------------------------
        for host in hosts:
            url = str(host.get("url") or "")
            up, elapsed, why = reach_probe(url, timeout)
            result["hosts"].append({
                "name": host.get("name") or url or "host",
                "url": url,
                "repos": list(host.get("repos") or []),
                "state": "up" if up else "down",
                "ms": int(elapsed),
                "why": why or "",
            })

        result["lines"] = format_lines(result)
    except Exception as exc:                       # a broken checker never stops the brain
        result["error"] = _one_line(exc)
        result["lines"] = format_lines(result)
        result["missing"] = False
        result["say"] = ""
        return result

    flags = [line for line in result["lines"] if line.strip().startswith("!")]
    result["missing"] = bool(flags)
    result["say"] = "\n".join(flags)
    return result


def write_state(result, hub):
    """<hub>/carriers-<machine>.json — temp file + os.replace, never a half-written file."""
    hub = Path(hub)
    target = hub / ("%s%s.json" % (STATE_PREFIX, result.get("machine") or "unknown"))
    # the temp name starts with a dot so a reader globbing carriers-*.json never sees it
    temp = hub / (".%s%s.json.tmp" % (STATE_PREFIX, result.get("machine") or "unknown"))
    try:
        hub.mkdir(parents=True, exist_ok=True)
        with open(str(temp), "w", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(str(temp), str(target))
    except Exception:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass
    return target


def check_and_report(machine, hub, projects_root, timeout=5.0, probes=None, out=None):
    """run + print the lines + write the state file. The one call every caller wants."""
    result = run(machine, hub, projects_root, timeout=timeout, probes=probes)
    stream = out or sys.stdout
    for line in result.get("lines") or []:
        try:
            stream.write(line + "\n")
        except Exception:
            pass
    write_state(result, hub)
    return result


# --------------------------------------------------------------------------
# standalone
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="carrier_preflight.py",
        description="Check the carriers the record says are owed — the drive by its label, "
                    "each private host by a short reach test. Exit 0 ok, 3 when one is missing.")
    parser.add_argument("--machine-json", required=True,
                        help="a machine.json (name, roots, carriers)")
    parser.add_argument("--hub", required=True, help="the hub folder to read and write state in")
    parser.add_argument("--projects", required=True, help="the projects root to read STATUS files in")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="seconds per host (default 5, capped at 10)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON instead")
    parser.add_argument("--no-state", action="store_true",
                        help="do not write carriers-<machine>.json")
    args = parser.parse_args(argv)

    machine = _read_json(Path(args.machine_json), default=None)
    if machine is None:
        sys.stderr.write("carrier_preflight: cannot read %s\n" % args.machine_json)
        return 2
    result = run(machine, Path(args.hub), Path(args.projects), timeout=args.timeout)
    if not args.no_state:
        write_state(result, Path(args.hub))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        for line in result.get("lines") or []:
            print(line)
    return 3 if result.get("missing") else 0


if __name__ == "__main__":
    sys.exit(main())
