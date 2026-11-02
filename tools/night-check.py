#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""night-check.py — what can take a model turn while nobody is here.

    python3 tools/night-check.py            the list, then ONE plain last line  (`python` on Windows)
    python3 tools/night-check.py --json     the same, as data (the last line is `last`)
    python3 tools/night-check.py --line     the last line alone — the wake screen's and the tree's road
    common: [--hub DIR] [--home DIR] [--now ISO]

THE LAST LINE is one of two, and nothing else:
    nothing can wake a Fable window tonight · <what fires, and when> · read HH:MM          exit 0
    CAN WAKE FABLE: <the named thing> — <the move that disarms it>                        exit 2

WHAT IT READS — this machine's own record, never a model and never the network:
  waiters     every `mail.py --wait` / `--watch` in the process table (`ps` here; on Windows the
              process CSV — PowerShell's CIM, else wmic, else tasklist, which shows no command line
              and so cannot tell a waiter from any other python) — its window found by the title it
              was armed with, that window's model and context from its own transcript's tail; the
              postman's waits.jsonl says whether it was FORCED past its refusal. A waiter on a Fable
              window — or on a window whose model cannot be read — CAN WAKE FABLE.
  send orders every `send` item in the postman's pending/<carrier>.json: a push ordered while its
              window was attended, carried by ANOTHER window at that window's next turn — and the
              carried push starts a turn in its target. Into a Fable window, with a carrier that has
              a road to a turn the record shows (a waiter armed, or live in the pulse's window), it
              CAN WAKE FABLE; with a carrier that shows none it is listed, not counted.
  letters     a letter or notice queued in a window's OWN pending file waits for that window's next
              turn and starts none: a Fable window is never woken from idle.
  routines    the app's task store for the signed-in account (routine-check.py's own readers): each
              enabled routine, the model its SKILL.md names, its next fire; a routine that can run
              on Fable (a Fable model, or no model line — the app's default can be Fable) and fires
              inside the night CAN WAKE FABLE. Codex automations that are ACTIVE: model, next fire.
  live        each Fable window the pulse saw in its last minutes, with the rule that keeps it
              quiet (usage-settings' wait_refuse_models); a lane-holding Fable window whose model
              that list does NOT refuse would arm a waiter at its turn end — CAN WAKE FABLE.
  jobs        the scheduler's exocortex jobs (launchd here, Task Scheduler on Windows): no model,
              never a turn.
  meter       the usage line (tools/usage.py): the login, the week, the read age.
  cannot see  in-window timers (ScheduleWakeup, /loop, cron) live inside the app; always said.

THE NIGHT is the next 12 hours from the read. THE MOVE is named, never made: this tool kills
nothing, disarms nothing and writes nothing. THE ONE SEAM for a gate: EXO_NIGHT_PS names a file
holding a process table — `ps -axww -o pid=,etime=,command=` lines, or a Windows CSV whose header
names ProcessId and CommandLine (or tasklist's Image Name and PID) — read in place of this
machine's own.

Stdlib only, Python 3.9, macOS and Windows, cp1252-safe output, every path from the machine
record the path resolver finds.
"""
import csv
import glob
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
NIGHT_HOURS = 12
LIVE_MINUTES = 10                 # the pulse's own window, when its file does not say
ALIVE_S = 30                      # a waiter's alive mark is fresh this long (postman.ALIVE_S)
PS_ENV = "EXO_NIGHT_PS"
LETTER_LINES = 6                  # letters for Fable windows named one by one, then counted
TIMERS = "cannot see: in-window timers (ScheduleWakeup, loop, cron) — they live inside the app"
QUIET_HEAD = "nothing can wake a Fable window tonight"
CAN_HEAD = "CAN WAKE FABLE: "
ASCII = {"—": "--", "·": "-", "«": "<<", "»": ">>", "→": "->", "…": "..."}


# ── the tools this one stands on: beside it first, then the hub's tools/ ─────

_MODS = {}


def load(file_name, hub=None):
    key = file_name
    if key in _MODS:
        return _MODS[key]
    mod = None
    for folder in [HERE] + ([os.path.join(str(hub), "tools")] if hub else []):
        path = os.path.join(folder, file_name)
        if not os.path.isfile(path):
            continue
        try:
            if folder not in sys.path:
                sys.path.insert(0, folder)
            spec = importlib.util.spec_from_file_location(
                "night_" + re.sub(r"\W", "_", file_name), path)
            mod = importlib.util.module_from_spec(spec)
            errors = getattr(sys.stdout, "errors", None)
            try:
                spec.loader.exec_module(mod)
            finally:
                # a neighbour that reconfigures stdout at import (usage.py does) must leave
                # the importer's console as it was — the wake screen's ASCII fallback
                if errors and getattr(sys.stdout, "errors", None) != errors:
                    try:
                        sys.stdout.reconfigure(errors=errors)
                    except Exception:
                        pass
            break
        except Exception:
            mod = None
    _MODS[key] = mod
    return mod


def emit(text):
    try:
        sys.stdout.write(text + "\n")
        return
    except UnicodeEncodeError:
        pass
    for mark, plain in ASCII.items():
        text = text.replace(mark, plain)
    sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")


def argv_value(argv, name):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def parse_iso(text):
    if not text:
        return None
    s = str(text).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.astimezone()


def read_json(path, default=None, cap=4 << 20):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.loads(fh.read(cap))
    except (OSError, ValueError):
        return default


def hm(d, now):
    """`21:14` today, `Sun 21:14` within six days, `Mon 5 Oct 08:40` further — the weekday
    computed from the date, never from memory."""
    if d is None:
        return "?"
    d = d.astimezone()
    if d.date() == now.date():
        return d.strftime("%H:%M")
    if abs((d.date() - now.date()).days) <= 6:
        return d.strftime("%a %H:%M")
    return "%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b %H:%M"))


def night_hm(d, now):
    """HH:MM for a moment inside the night (12 hours ahead: the clock alone is unambiguous),
    else hm()'s words."""
    if d is not None and now <= d.astimezone() <= now + timedelta(hours=NIGHT_HOURS):
        return d.astimezone().strftime("%H:%M")
    return hm(d, now)


def ago(minutes):
    if minutes is None:
        return "?"
    if minutes < 1:
        return "just now"
    if minutes < 120:
        return "%d min ago" % int(minutes)
    if minutes < 48 * 60:
        return "%d h ago" % int(minutes // 60)
    return "%d d ago" % int(minutes // 1440)


def is_fable(model):
    return "fable" in str(model or "").lower()


def mind(model):
    """FABLE / SONNET / … from a model id; the id itself for a family this does not know."""
    low = str(model or "").lower()
    for word in ("fable", "opus", "sonnet", "haiku"):
        if word in low:
            return word.upper()
    return str(model) if model else "model unread"


# ── the record ───────────────────────────────────────────────────────────────

def record(argv):
    """{hub, machine, home, claude, codex, post, appdata, os} from the machine record the path
    resolver finds, with --hub / --home on top."""
    hub_arg, home_arg = argv_value(argv, "--hub"), argv_value(argv, "--home")
    found, roots = {}, {}
    ep = load("exo_paths.py")
    if ep is not None:
        try:
            found = ep.paths(tool_file=__file__, hub=hub_arg) if hub_arg else ep.paths(tool_file=__file__)
            mf = found.get("machine_file")
            if mf:
                roots = dict((read_json(mf, {}) or {}).get("roots") or {})
        except Exception:
            found, roots = {}, {}
    home = home_arg or roots.get("home") or os.path.expanduser("~")
    hub = hub_arg or roots.get("orchestrator") or (found.get("hub") and str(found["hub"])) \
        or os.path.dirname(HERE)
    machine = str(found.get("machine") or "").lower() or "machine"
    return {"hub": str(hub), "machine": machine, "home": str(home),
            "claude": str(roots.get("claude") or os.path.join(home, ".claude")),
            "codex": str(roots.get("codex") or os.path.join(home, ".codex")),
            "post": str(roots.get("post") or os.path.join(home, ".exocortex", "post")),
            "appdata": os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming"),
            "windows": os.name == "nt"}


# ── THE ONE SEAM: the process table ──────────────────────────────────────────

def etime_seconds(text):
    """ps's elapsed time — [[dd-]hh:]mm:ss — in seconds; None when it does not read."""
    try:
        days, rest = (text.split("-", 1) + [""])[:2] if "-" in text else ("0", text)
        parts = [int(p) for p in rest.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        return int(days) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
    except (ValueError, AttributeError):
        return None


def parse_ps(text, now):
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(\S+)\s+(.*\S)\s*$", line)
        if not m:
            continue
        secs = etime_seconds(m.group(2))
        started = (now - timedelta(seconds=secs)) if secs is not None else None
        rows.append({"pid": int(m.group(1)), "started": started, "cmd": m.group(3), "blind": False})
    return rows


def win_date(text):
    s = str(text or "").strip()
    d = parse_iso(s)
    if d is not None:
        return d
    m = re.match(r"(\d{14})\.\d+([+-]\d{3})$", s)             # wmic: 20260928091158.123456-420
    if m:
        try:
            base = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
            return base.replace(tzinfo=timezone(timedelta(minutes=int(m.group(2)))))
        except ValueError:
            return None
    return None


def parse_csv(text):
    """A Windows process CSV. By its header: ProcessId + CommandLine (+ CreationDate) is the
    CIM / wmic table; Image Name + PID is tasklist's, which carries NO command line."""
    body = "\n".join(l for l in text.splitlines() if l.strip())
    reader = csv.DictReader(io.StringIO(body))
    rows = []
    for raw in reader:
        row = dict((str(k or "").strip().lower(), v) for k, v in raw.items())
        if "commandline" in row or "processid" in row:
            try:
                pid = int(str(row.get("processid") or "").strip())
            except ValueError:
                continue
            rows.append({"pid": pid, "started": win_date(row.get("creationdate")),
                         "cmd": str(row.get("commandline") or ""), "blind": False})
        elif "image name" in row and "pid" in row:
            try:
                pid = int(str(row.get("pid") or "").strip())
            except ValueError:
                continue
            rows.append({"pid": pid, "started": None, "cmd": str(row.get("image name") or ""),
                         "blind": True})
    return rows


def parse_table(text, now):
    head = text.lstrip()[:400].lower()
    if head.startswith('"') or "processid" in head.split("\n", 1)[0] or \
            "image name" in head.split("\n", 1)[0]:
        return parse_csv(text)
    return parse_ps(text, now)


def decode(raw):
    """A child's bytes as text: UTF-16 when it says so (wmic writes UTF-16 into a pipe), else
    UTF-8, a mark it cannot read replaced rather than raised."""
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(raw) > 3 and raw[1:2] == b"\x00"):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def run(args, timeout=20):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout,
                           env=dict(os.environ, LC_ALL="C"))
        return p.returncode, decode(p.stdout or b"")
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, repr(exc)


WIN_PS = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
          "Get-CimInstance Win32_Process | Select-Object ProcessId,"
          "@{n='CreationDate';e={if($_.CreationDate){$_.CreationDate.ToString('o')}}},CommandLine"
          " | ConvertTo-Csv -NoTypeInformation")


def process_table(rec, now):
    """(rows, how, error). rows = [{pid, started, cmd, blind}]. The gate's seam first."""
    forced = str(os.environ.get(PS_ENV) or "").strip()
    if forced:
        try:
            with open(forced, "rb") as fh:
                text = decode(fh.read())            # the same decoding a real child's bytes get
        except OSError as exc:
            return [], "the file %s" % forced, "it could not be read (%s)" % exc
        return parse_table(text, now), "the file %s" % forced, ""
    if rec["windows"]:
        code, out = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", WIN_PS])
        if code == 0 and "ProcessId" in out:
            return parse_csv(out), "PowerShell's process table", ""
        code, out = run(["wmic", "process", "get", "ProcessId,CreationDate,CommandLine",
                         "/format:csv"])
        if code == 0 and "ProcessId" in out:
            return parse_csv(out), "wmic's process table", ""
        code, out = run(["tasklist", "/FO", "CSV"])
        if code == 0 and "PID" in out:
            return parse_csv(out), "tasklist (no command lines)", ""
        return [], "the process table", "neither PowerShell, wmic nor tasklist answered"
    code, out = run(["ps", "-axww", "-o", "pid=,etime=,command="])
    if code == 0 and out.strip():
        return parse_ps(out, now), "ps", ""
    return [], "ps", "ps did not answer (%s)" % (out.strip()[:80] or "exit %d" % code)


# ── the windows: transcripts, titles, the app's own ids ─────────────────────

class Windows(object):
    """Every Claude transcript on this machine, found once: id → path, title → ids, and the
    app's local_ ids → transcript ids from its own session store."""

    def __init__(self, rec, pm):
        self.rec, self.pm = rec, pm
        self._paths, self._titles, self._by_title, self._app = None, {}, None, None
        self._codex = None

    def _walk(self):
        if self._paths is not None:
            return
        self._paths = {}
        base = os.path.join(self.rec["claude"], "projects")
        try:
            folders = os.listdir(base)
        except OSError:
            folders = []
        for folder in folders:
            root = os.path.join(base, folder)
            try:
                names = os.listdir(root)
            except OSError:
                continue
            for name in names:
                if name.endswith(".jsonl"):
                    self._paths[name[:-6]] = os.path.join(root, name)

    def path(self, sid):
        self._walk()
        return self._paths.get(str(sid or ""), "")

    def title(self, sid):
        sid = str(sid or "")
        if sid in self._titles:
            return self._titles[sid]
        t = ""
        p = self.path(sid)
        if p:
            d = read_json(os.path.join(p[:-6], "custom-title.json"), None, cap=65536)
            if isinstance(d, dict):
                t = str(d.get("customTitle") or "").strip()
        self._titles[sid] = t
        return t

    def by_title(self, title):
        """The transcript a title names — the newest when several carry it; ''."""
        want = str(title or "").strip()
        if not want:
            return ""
        if self._by_title is None:
            self._walk()
            self._by_title = {}
            for sid, p in self._paths.items():
                d = read_json(os.path.join(p[:-6], "custom-title.json"), None, cap=65536)
                if not isinstance(d, dict) or not d.get("customTitle"):
                    continue
                t = str(d["customTitle"]).strip()
                self._titles[sid] = t
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    m = 0.0
                self._by_title.setdefault(t, []).append((m, sid, p))
        hits = sorted(self._by_title.get(want) or [], reverse=True)
        return hits[0][2] if hits else ""

    def app_target(self, local_id):
        """The transcript id behind an app `local_` id (the id a push names), from the app's
        own session store; ''."""
        if self._app is None:
            self._app = {}
            ap = load("app_sessions.py", self.rec["hub"])
            if ap is not None:
                try:
                    for r in ap.records(self.rec["home"], max_age_days=45.0,
                                        appdata=self.rec["appdata"]):
                        if r.get("local_id") and r.get("cli_id"):
                            self._app[str(r["local_id"])] = str(r["cli_id"])
                except Exception:
                    pass
        return self._app.get(str(local_id or ""), "")

    def codex_path(self, sid):
        if self._codex is None:
            self._codex = {}
            for p in glob.glob(os.path.join(self.rec["codex"], "sessions", "**", "rollout-*.jsonl"),
                               recursive=True):
                m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$", p)
                if m:
                    self._codex[m.group(1)] = p
        return self._codex.get(str(sid or ""), "")

    def facts(self, path):
        """{found, model, percent} of a window from its own transcript's tail (the postman's
        reader, the one copy)."""
        if not path:
            return {"found": False, "model": "", "percent": None}
        if self.pm is not None and hasattr(self.pm, "window_facts"):
            try:
                f = self.pm.window_facts(path)
                window = float(f.get("window") or 1000000) or 1000000.0
                pct = 100.0 * float(f.get("context") or 0) / window if f.get("model") else None
                if f.get("model"):
                    return {"found": True, "model": f["model"], "percent": pct}
            except Exception:
                pass
        # a Codex rollout (or a transcript the postman could not read): the model id alone
        try:
            with open(path, "rb") as fh:
                head = fh.read(65536).decode("utf-8", "replace")
            found = re.findall(r'"model"\s*:\s*"([^"]{1,120})"', head)
            return {"found": True, "model": found[-1] if found else "", "percent": None}
        except OSError:
            return {"found": False, "model": "", "percent": None}


def ctx_words(pct):
    return (" · context %d %%" % int(round(pct))) if pct is not None else ""


# ── the readers ──────────────────────────────────────────────────────────────

WAITER_RE = re.compile(r"(?:^|[\s\"'/\\])mail\.py[\"']?\s.*?--(wait|watch)\s+[\"']?([^\s\"']+)")


def is_python(cmd):
    """Is the process itself a python — its first word, quoted or not? (The app runs a
    background command inside a shell whose own line also names mail.py; only the python
    under it is the waiter.)"""
    s = str(cmd or "").strip()
    first = s[1:].split(s[0], 1)[0] if s[:1] in ("'", '"') else s.split(" ", 1)[0]
    base = re.split(r"[\\/]", first)[-1].lower()
    return "python" in base or base in ("py.exe", "py")


def waiter_args(cmd):
    """(road, address, title, model, forced) of a `mail.py --wait/--watch` command line, or None.
    ps joins argv with spaces, so a title runs to the next ` --flag`."""
    m = WAITER_RE.search(cmd)
    if not m:
        return None
    title = ""
    t = re.search(r"--title[=\s]+(.+?)(?=\s+--[a-z][a-z-]*(?:[\s=]|$)|\s*$)", cmd)
    if t:
        title = t.group(1).strip().strip("\"'")
    model = re.search(r"--model[=\s]+[\"']?([^\s\"']+)", cmd)
    return (m.group(1), m.group(2), title, model.group(1) if model else "",
            bool(re.search(r"\s--force(?:\s|$)", cmd)))


def forced_rows(post):
    """{title: the newest `forced` row} from the postman's waits.jsonl."""
    out = {}
    try:
        with io.open(os.path.join(post, "waits.jsonl"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("verdict") == "forced":
                    out[str(r.get("title") or "")] = r
    except OSError:
        pass
    return out


def holds(post):
    """{session id: holds row} — which window holds which lane (the postman's own file)."""
    out = {}
    for p in glob.glob(os.path.join(post, "holds", "*.json")):
        d = read_json(p, None)
        if isinstance(d, dict):
            out[str(d.get("session") or os.path.basename(p)[:-5])] = d
    return out


def alive_mark(post, sid, now_ts):
    try:
        return now_ts - os.path.getmtime(os.path.join(post, "waiters", "%s.alive" % sid)) <= ALIVE_S
    except OSError:
        return False


def live_windows(rec, now):
    """{session id: row} of the sessions the pulse saw inside its window, from
    live-sessions-<machine>.json (routine runs left out: they never carry and never idle)."""
    d = read_json(os.path.join(rec["hub"], "live-sessions-%s.json" % rec["machine"]), None)
    out = {}
    if not isinstance(d, dict):
        return out, None
    window = float(d.get("live_minutes") or LIVE_MINUTES)
    when = parse_iso(d.get("when"))
    for s in d.get("sessions") or []:
        if not isinstance(s, dict) or s.get("routine"):
            continue
        try:
            mins = float(s.get("minutes_ago") or 0.0)
        except (TypeError, ValueError):
            continue
        if when is not None:
            mins += (now - when).total_seconds() / 60.0
        if mins <= window:
            out[str(s.get("id") or "")] = dict(s, minutes=mins)
    return out, when


# ── the check ────────────────────────────────────────────────────────────────

def item(kind, words, wakes=False, move="", name=""):
    return {"kind": kind, "words": words, "wakes_fable": bool(wakes), "move": move, "name": name}


def kill_move(rec, pid):
    return ("stop it: taskkill /PID %d /T /F" % pid) if rec["windows"] else ("stop it: kill %d" % pid)


def check(rec, now):
    hub = rec["hub"]
    pm = load("postman.py", hub)
    rc = load("routine-check.py", hub)
    us = load("usage.py", hub)
    W = Windows(rec, pm)
    items, cannot = [], [TIMERS]
    now_ts = now.timestamp()
    refuse = ["claude-fable-"]
    if pm is not None and hasattr(pm, "usage_settings"):
        try:
            refuse = list(pm.usage_settings(hub)[0].get("wait_refuse_models") or [])
        except Exception:
            pass
    held = holds(rec["post"])
    live, _live_when = live_windows(rec, now)
    forced = forced_rows(rec["post"])

    # 1 · waiters and watches in the process table
    table, how, err = process_table(rec, now)
    waiter_titles, waiter_sids = set(), set()
    if err:
        items.append(item("ps", "process table · %s: %s" % (how, err), wakes=True,
                          move="run the check again, or look for mail.py --wait yourself",
                          name="the process table could not be read — a waiter cannot be ruled out"))
    blind = [r for r in table if r.get("blind") and "python" in r["cmd"].lower()]
    if blind:
        items.append(item("ps",
                          "process table · %s shows %d python process%s with no command line"
                          % (how, len(blind), "" if len(blind) == 1 else "es"), wakes=True,
                          move="run the check where PowerShell or wmic can read command lines",
                          name="%d python process%s whose command line%s this machine will not show"
                               % (len(blind), "" if len(blind) == 1 else "es",
                                  "" if len(blind) == 1 else "s")))
    seen_waiters = set()
    for r in sorted(table, key=lambda x: -x["pid"]):
        got = waiter_args(r["cmd"]) if not r.get("blind") and is_python(r["cmd"]) else None
        if not got:
            continue
        road, address, title, model_hint, force_flag = got
        if (road, address.lower(), title) in seen_waiters:
            continue
        seen_waiters.add((road, address.lower(), title))
        path = W.by_title(title) if title else ""
        sid = os.path.basename(path)[:-6] if path else ""
        if not sid:
            for s, h in held.items():
                if title and str(h.get("title") or "") == title:
                    sid, path = s, W.path(s)
                    break
        f = W.facts(path)
        model = f["model"]
        waiter_titles.add(title)
        if sid:
            waiter_sids.add(sid)
        armed = hm(r.get("started"), now)
        who = ("«%s»" % title) if title else "no --title (its window cannot be named)"
        fr = forced.get(title) if title else None
        head = "mail.py --%s %s · pid %d · armed %s by %s" % (road, address, r["pid"], armed, who)
        if not f["found"] or not model:
            items.append(item("waiter", "%s · its window's model cannot be read — never assumed "
                                        "to be the cheap one" % head, wakes=True,
                              move=kill_move(rec, r["pid"]),
                              name="the %s pid %d (its window's model cannot be read)"
                                   % ("waiter" if road == "wait" else "watch", r["pid"])))
        elif is_fable(model):
            why = ("FORCED past its refusal %s (waits.jsonl)" % hm(parse_iso(fr.get("when")), now)
                   if fr else ("armed with --force" if force_flag else
                               "the waiter refuses a Fable window, and this one is armed anyway"))
            items.append(item("waiter", "%s · that window is FABLE%s — %s"
                              % (head, ctx_words(f["percent"]), why), wakes=True,
                              move=kill_move(rec, r["pid"]),
                              name="the %s pid %d on «%s»" % ("waiter" if road == "wait" else "watch",
                                                             r["pid"], title or sid)))
        else:
            items.append(item("waiter", "%s · %s%s — a letter that asks wakes it (a %s turn, "
                                        "never Fable)" % (head, mind(model), ctx_words(f["percent"]),
                                                          mind(model))))

    # 2 · the postman's pending files: send orders, and letters that wait
    waiting_other, waiting_windows = 0, 0
    fable_letters = []
    for p in sorted(glob.glob(os.path.join(rec["post"], "pending", "*.json"))):
        d = read_json(p, None)
        if not isinstance(d, dict):
            continue
        sid = str(d.get("session") or os.path.basename(p)[:-5])
        entries = [i for i in (d.get("items") or []) if isinstance(i, dict)]
        sends, grouped = [], {}
        for i in entries:
            if i.get("kind") == "send":
                key = (str(i.get("target") or ""), str(i.get("title") or ""))
                if key not in grouped:
                    grouped[key] = dict(i, count=0)
                    sends.append(grouped[key])
                grouped[key]["count"] += 1
                if str(i.get("queued") or "") > str(grouped[key].get("queued") or ""):
                    grouped[key]["queued"] = i.get("queued")
        letters = [i for i in entries if i.get("kind") != "send"]
        for s in sends:
            target = str(s.get("target") or "")
            tsid = W.app_target(target) if target.startswith("local_") else ""
            tpath = W.path(tsid) if tsid else W.by_title(s.get("title"))
            f = W.facts(tpath)
            tname = str(s.get("title") or target or "?")
            carrier_title = W.title(sid) or sid[:8]
            road = ""
            if sid in waiter_sids or (W.title(sid) and W.title(sid) in waiter_titles):
                road = "its waiter is armed"
            elif alive_mark(rec["post"], sid, now_ts):
                road = "its waiter's alive mark is fresh"
            elif sid in live:
                road = "it is live (%s)" % ago(live[sid].get("minutes"))
            words = "%s → «%s» · %s%s · queued %s · carried by «%s»" % (
                "send order" if s["count"] == 1 else "%d send orders" % s["count"],
                tname, mind(f["model"]) if f["model"] else "model unread", ctx_words(f["percent"]),
                hm(parse_iso(s.get("queued")), now), carrier_title)
            if (is_fable(f["model"]) or not f["model"]) and road:
                items.append(item("send", "%s (%s) — carried, the push starts a turn in that %s "
                                          "window" % (words, road, "Fable" if f["model"] else
                                                      "unread-model"), wakes=True,
                                  move="say «mail» in «%s» now — its letters are read, and the order "
                                       "is spent at the next pass" % tname,
                                  name="the send order into «%s», carried by «%s»" % (tname, carrier_title)))
            elif is_fable(f["model"]) or not f["model"]:
                items.append(item("send", "%s — the carrier shows no road to a turn (no waiter, "
                                          "not live); it wakes that window only if the carrier "
                                          "takes one" % words))
            else:
                items.append(item("send", "%s — carried, it is a %s turn, never Fable"
                                  % (words, mind(f["model"]))))
        if not letters:
            continue
        path = W.path(sid) or W.codex_path(sid)
        f = W.facts(path)
        if is_fable(f["model"]) and (sid in live or sid in held):
            newest = max((parse_iso(i.get("queued")) for i in letters if parse_iso(i.get("queued"))),
                         default=None)
            fable_letters.append((item(
                "letters", "pending → «%s» · FABLE%s · %d waiting, newest queued %s — a Fable window "
                           "is never woken from idle; this waits for its next turn"
                % (W.title(sid) or sid[:8], ctx_words(f["percent"]), len(letters), hm(newest, now))),
                len(letters)))
        else:
            waiting_other += len(letters)
            waiting_windows += 1
    items.extend(i for i, _n in fable_letters[:LETTER_LINES])
    rest = fable_letters[LETTER_LINES:]
    if rest:
        waiting_other += sum(n for _i, n in rest)
        waiting_windows += len(rest)
    if waiting_other:
        items.append(item("letters", "%d %sletter%s wait%s in %d %s — each shows at that "
                                     "window's next turn; none starts one"
                          % (waiting_other, "more " if fable_letters else "",
                             "" if waiting_other == 1 else "s", "s" if waiting_other == 1 else "",
                             waiting_windows, "window's own file" if waiting_windows == 1
                             else "windows' own files")))

    # 3 · routines — the signed-in account's task store, and Codex automations
    fires = []
    night_end = now + timedelta(hours=NIGHT_HOURS)
    if rc is not None:
        try:
            stores = rc.find_store_in(rec["home"], rec["appdata"])
            active = rc.active_store(stores) if len(stores) > 1 else (stores[0] if stores else None)
        except Exception:
            stores, active = [], None
        for t in (rc.read_store(active).get("scheduledTasks") or []) if active else []:
            if not isinstance(t, dict) or not t.get("enabled", True):
                continue
            name = str(t.get("displayName") or t.get("id") or "?")
            meta = rc.frontmatter(t.get("filePath") or rc.skill_path(t))
            flag, words = rc.claude_model_verdict(meta)
            model = str((meta or {}).get("model") or "").strip()
            nxt = None
            try:
                nxt = rc.next_fire(str(t.get("cronExpression") or ""), now.replace(tzinfo=None))
            except Exception:
                nxt = None
            nxt_aware = nxt.astimezone() if nxt is not None else None
            when = ("next %s" % hm(nxt_aware, now)) if nxt_aware else "next fire unread"
            tonight = nxt_aware is not None and nxt_aware <= night_end
            if flag.strip() == "STOP":
                items.append(item("routine", "%s · %s · %s — %s" % (name, model or "no model line",
                                                                 when, words),
                                  wakes=tonight,
                                  move="write `model: sonnet` in %s (or disable «%s» in the app's "
                                       "Routines)" % (t.get("filePath") or rc.skill_path(t), name),
                                  name="the routine «%s» at %s can run on Fable" % (name, night_hm(nxt_aware, now))))
            else:
                items.append(item("routine", "%s · %s · %s" % (name, model or "?", when)))
            if tonight:
                fires.append((nxt_aware, mind(model).lower() if model else "unnamed-model"))
        others = [s for s in stores if s != active]
        if others:
            n_other = sum(len([t for t in (rc.read_store(s).get("scheduledTasks") or [])
                               if isinstance(t, dict) and t.get("enabled", True)]) for s in others)
            if n_other:
                items.append(item("routine", "another account's task store holds %d enabled "
                                             "routine%s — they fire only while it is signed in"
                                  % (n_other, "" if n_other == 1 else "s")))
    else:
        cannot.append("cannot see: the routines (routine-check.py is not beside this tool)")
    for path in sorted(glob.glob(os.path.join(rec["codex"], "automations", "*", "automation.toml"))):
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read(262144)
        except OSError:
            continue
        val = (lambda k: (re.search(r'(?m)^\s*%s\s*=\s*"([^"]*)"' % k, text) or [None, ""])[1])
        if val("status").upper() != "ACTIVE":
            continue
        nxt = rrule_next(val("rrule"), now)
        tonight = nxt is not None and nxt <= night_end
        model = val("model") or "the Codex default"
        items.append(item("routine", "%s · codex %s · %s" % (val("name") or os.path.basename(
            os.path.dirname(path)), model, ("next %s" % hm(nxt, now)) if nxt else "next fire unread")))
        if tonight:
            fires.append((nxt, "codex %s" % model))

    # 4 · live Fable windows, with the rule that keeps each one quiet
    refused = any(str(p).lower().startswith("claude-fable") or "fable" in str(p).lower()
                  for p in refuse)
    for sid, s in sorted(live.items(), key=lambda kv: kv[1].get("minutes") or 0):
        model = str(s.get("model") or "")
        if not is_fable(model):
            continue
        f = W.facts(s.get("transcript") or W.path(sid))
        lane = ", ".join((held.get(sid) or {}).get("arcs") or [])
        title = str(s.get("title") or W.title(sid) or sid[:8])
        head = "FABLE «%s» · live %s%s%s" % (title, ago(s.get("minutes")), ctx_words(f["percent"]),
                                              (" · holds %s" % lane) if lane else "")
        if lane and not refused and (held.get(sid) or {}).get("arm"):
            items.append(item("live", "%s — usage-settings' wait_refuse_models does not refuse Fable, "
                                      "so its turn end arms a waiter" % head, wakes=True,
                              move="put claude-fable- back in wait_refuse_models "
                                   "(usage-settings.json), or retire «%s»" % title,
                              name="the live Fable window «%s» would arm a waiter" % title))
        else:
            items.append(item("live", "%s — nothing waits on Fable (the waiter refuses it); it takes "
                                      "a turn only when you type" % head))

    # 5 · the scheduler's jobs — no model, never a turn
    jobs = scheduler_jobs(rec)
    if jobs:
        items.append(item("jobs", "%s — no model, never a turn" % jobs))

    # 6 · the meter
    if us is not None and hasattr(us, "receipt_line"):
        try:
            line = us.receipt_line(hub, "claude")
            if line:
                items.append(item("meter", line))
        except Exception:
            pass

    wakes = [i for i in items if i["wakes_fable"]]
    read = now.strftime("%H:%M")
    if wakes:
        first = wakes[0]
        last = "%s%s — %s%s" % (CAN_HEAD, first["name"] or first["words"], first["move"],
                                (" · and %d more above" % (len(wakes) - 1)) if len(wakes) > 1 else "")
    else:
        last = " · ".join([QUIET_HEAD] + fires_words(fires, now, items) + ["read %s" % read])
    return {"machine": rec["machine"].upper(), "read": now.replace(microsecond=0).isoformat(),
            "process_table": how, "items": items, "cannot_see": cannot,
            "can_wake": [i["name"] for i in wakes], "last": last, "exit": 2 if wakes else 0}


def fires_words(fires, now, items):
    """`sonnet routines fire at 08:00, 08:25 · codex gpt-5.6-sol at 06:00` — what will take a
    turn tonight, by model; `no routine fires in the next 12 h` when nothing does."""
    out = []
    groups = {}
    for when, word in sorted(fires):
        groups.setdefault(word, []).append(when)
    for word, whens in sorted(groups.items(), key=lambda kv: kv[1][0]):
        times = [night_hm(w, now) for w in whens]
        shown = ", ".join(times[:4]) + (" +%d" % (len(times) - 4) if len(times) > 4 else "")
        if word.startswith("codex"):
            out.append("%s at %s" % (word, shown))
        else:
            out.append("%s routine%s fire%s at %s" % (word, "s" if len(times) > 1 else "",
                                                     "" if len(times) > 1 else "s", shown))
    if not out:
        out.append("no routine fires in the next %d h" % NIGHT_HOURS)
    waiters = [i for i in items if i["kind"] == "waiter" and not i["wakes_fable"]]
    if waiters:
        out.append("%d waiter%s armed on a non-Fable window" % (len(waiters),
                                                                 "" if len(waiters) == 1 else "s"))
    return out


def rrule_next(rule, now):
    """The next fire of a Codex automation's RRULE (FREQ=DAILY|WEEKLY|HOURLY with BYDAY,
    BYHOUR, BYMINUTE), in local time; None when it does not read."""
    parts = dict(p.split("=", 1) for p in str(rule or "").split(";") if "=" in p)
    freq = parts.get("FREQ", "").upper()
    try:
        hours = [int(h) for h in parts["BYHOUR"].split(",")] if "BYHOUR" in parts else None
        minutes = [int(m) for m in parts["BYMINUTE"].split(",")] if "BYMINUTE" in parts else [0]
    except ValueError:
        return None
    days = None
    if "BYDAY" in parts:
        names = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        days = set(names.index(d[-2:]) for d in parts["BYDAY"].split(",") if d[-2:] in names)
    if freq not in ("DAILY", "WEEKLY", "HOURLY") or (freq != "HOURLY" and hours is None):
        return None                           # a daily rule with no hour fires at a time unread
    t = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(60 * 24 * 8):
        if (days is None or t.weekday() in days) and (hours is None or t.hour in hours) \
                and t.minute in minutes:
            return t
        t += timedelta(minutes=1)
    return None


def scheduler_jobs(rec):
    """`launchd com.exocortex.{postman,pulse,regen,sync}` — the machine scheduler's exocortex
    jobs by name (launchd's LaunchAgents here, Task Scheduler on Windows), or ''."""
    if not rec["windows"]:
        folder = os.path.join(rec["home"], "Library", "LaunchAgents")
        try:
            names = sorted(n[:-6] for n in os.listdir(folder)
                           if n.endswith(".plist") and "exocortex" in n.lower())
        except OSError:
            names = []
        what = "launchd"
    else:
        code, out = run(["schtasks", "/Query", "/FO", "CSV", "/NH"], timeout=20)
        names = sorted(set(row[0].strip("\\") for row in csv.reader(io.StringIO(out))
                           if row and "exocortex" in row[0].lower())) if code == 0 else []
        what = "Task Scheduler"
    if not names:
        return ""
    if len(names) == 1:
        return "%s %s" % (what, names[0])
    prefix = os.path.commonprefix(names)
    prefix = prefix[:prefix.rfind(".") + 1] if "." in prefix else ""
    return "%s %s{%s}" % (what, prefix, ",".join(n[len(prefix):] for n in names))


# ── output ───────────────────────────────────────────────────────────────────

def text_lines(res, now):
    out = ["NIGHT CHECK — %s · %s" % (res["machine"], now.strftime("%a %H:%M"))]
    for i in res["items"]:
        out.append("%-8s %s" % (i["kind"] if len(i["kind"]) <= 8 else i["kind"][:8], i["words"]))
    out.extend(res["cannot_see"])
    out.append(res["last"])
    return out


def main(argv):
    # emit() falls back to ASCII on a console that cannot print a mark; importing this file
    # (the wake screen, the tree) changes nothing about the importer's console
    if "--help" in argv or "-h" in argv:
        emit(__doc__)
        return 0
    now = parse_iso(argv_value(argv, "--now")) or datetime.now().astimezone()
    rec = record(argv)
    try:
        res = check(rec, now)
    except Exception as exc:                  # the tool never claims quiet when it broke
        res = {"machine": rec["machine"].upper(), "read": now.isoformat(), "items": [],
               "cannot_see": [TIMERS], "can_wake": ["the night check itself"],
               "last": "%sthe night check could not finish (%r) — nothing is ruled out; run it "
                       "again" % (CAN_HEAD, exc), "exit": 2, "process_table": ""}
    if "--json" in argv:
        emit(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True))
    elif "--line" in argv:
        emit(res["last"])
    else:
        for line in text_lines(res, now):
            emit(line)
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
