#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-night.py — the night check's gate: the night check names what can wake a Fable window.

    python3 tools/gate-night.py            every case (`python` on Windows)
    python3 tools/gate-night.py --keep     leave the worlds for inspection

HERMETIC: every world is made by tempfile.mkdtemp(prefix="exo-prove-night-") under the system
temp folder — a HOME with the app's own stores in their real shapes (transcripts and their
custom-title.json, the session store's local_ records, the routine task store and the routines'
SKILL.md files, LaunchAgents), the postman's POST DIR (pending/, holds/, waiters/, waits.jsonl),
Codex automations, a machine record naming a scratch hub, and a PROCESS TABLE handed to the tool
through its one seam (EXO_NIGHT_PS). The tools run from a COPY inside the world; nothing of this
machine's own is read or written; no model, no network.

  N-a  one armed `mail.py --wait` on a Fable window (a fake process table, its shell wrapper
       beside it, a `forced` row in waits.jsonl), one pending SEND order into a Fable window
       whose carrier's waiter is armed, one Sonnet routine → all three named, the quiet line
       REFUSED, the last line `CAN WAKE FABLE: … — <the move>`, exit 2
  N-b  the clean world → the quiet line, word for word: `nothing can wake a Fable window tonight ·
       sonnet routine fires at 02:00 · read 22:14`, exit 0
  N-c  in-window timers are named as unseeable — in the text and in --json — in both worlds
  N-d  (gate-wake-screen W9) the wake screen prints the last line under the hygiene line
  N-e  --json round-trips: the same last line, the same items, the same exit; --line is the last
       line alone
  N-f  Windows: the process table read from a CIM/wmic CSV (a python.exe waiter on a Fable window
       is found by its command line, wmic's date read); tasklist's CSV, which shows no command
       line, never lets the quiet line be claimed
  N-g  the rules around the edges: a letter queued for a Fable window waits (quiet stands); a send
       order whose carrier shows no road is listed, not counted; a routine on Fable, or with no
       model line, firing tonight CAN wake; a routine on Fable firing after the night does not; a
       lane-holding live Fable window whose model wait_refuse_models does not refuse CAN; a
       process table that cannot be read never claims quiet
  N-h  the collar: the tree's collector carries the same last line and the whole list (its own
       night_facts reader), as one mark whose click answers with every row
  N-i  rails: the tool wrote nothing in its world (every file's bytes before and after); its
       source imports no network module and runs only the process and scheduler readers; every
       world sits under the system temp folder with the exo-prove-night- prefix

Stdlib only, Python 3.9, OS-neutral. Exit 0 only when every check passes.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PY = sys.executable or "python3"
TOOLS = ("night-check.py", "postman.py", "routine-check.py", "usage.py", "app_sessions.py",
         "exo_paths.py", "exo_registry.py", "mail.py", "exo_common.py")
OPTIONAL = ("exo_common.py", "mail.py")
TREE_TOOLS = ("collect-openers.py", "opener_carriers.py", "grok_sessions.py")
PREFIX = "exo-prove-night-"
MARK = "GATE-NIGHT-217"
FAILS, PASSES = [], [0]
CASE = [""]
WORLDS = []

# THE CLOCK IS FORCED: every world is read "at 22:14 tonight", so the words are fixed.
NOW = datetime.now().astimezone().replace(hour=22, minute=14, second=0, microsecond=0)
NOW_ISO = NOW.isoformat()

SID_HUB = "c0de0217-aaaa-4bbb-8ccc-00000000f001"      # a FABLE window: the hub
SID_LANE = "c0de0217-aaaa-4bbb-8ccc-00000000f002"     # a FABLE window: a lane, live
SID_DESK = "c0de0217-aaaa-4bbb-8ccc-00000000a003"     # a SONNET window: the Desk (carrier)
SID_OLD = "c0de0217-aaaa-4bbb-8ccc-00000000a004"      # an old window, idle, no waiter
T_HUB = "ACT \u2014 Gatehub/hub: %s the fable hub" % MARK
T_LANE = "ACT \u2014 Gatehub/Lane: %s a fable lane" % MARK
T_DESK = "ACT \u2014 Gatehub/Desk: %s the sonnet desk" % MARK
T_OLD = "ARCH \u2014 Gatehub/Old: %s an old window" % MARK
FABLE, SONNET = "claude-fable-5-1", "claude-sonnet-5"
REGISTRY = {
    "version": 1, "note": "gate-night's own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {"north": {"label": "North", "mark": "\u25cf", "os": "macos",
                           "hue": {"light": "#2456a4", "dark": "#7fb0e8"}}},
    "minds": [{"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
              {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0f766e", "dark": "#2dd4bf"}}],
    "mind_aliases": {},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["hub"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}


# ── plumbing ─────────────────────────────────────────────────────────────────

def start(cid, name):
    CASE[0] = cid
    print("\n======== %s — %s ========" % (cid, name))


def check(cond, msg):
    if cond:
        PASSES[0] += 1
        print("  [PASS] %s" % msg)
    else:
        FAILS.append("%s: %s" % (CASE[0], msg))
        print("  [FAIL] %s" % msg)
    return bool(cond)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(path), "w", encoding="utf-8", newline="\n").write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def iso(d):
    return d.replace(microsecond=0).isoformat()


def zulu(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def source_tool(name):
    """Beside this gate first (a staged build), else the hub's tools/ the record names."""
    here = HERE / name
    if here.is_file():
        return here
    try:
        rec = json.load(io.open(str(Path.home() / "orchestrator-sync" / "machine.json"), encoding="utf-8"))
        return Path(rec["roots"]["orchestrator"]) / "tools" / name
    except Exception:
        return HERE.parent / "tools" / name


def snapshot(root):
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            try:
                out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                out[str(p.relative_to(root))] = None
    return out


# ── the world ────────────────────────────────────────────────────────────────

def world(name, tree=False):
    # every tool under test is found BEFORE a world is made: a gate that stops leaves no world
    for t in TOOLS + (TREE_TOOLS if tree else ()):
        if not source_tool(t).is_file() and not (t in OPTIONAL or t in TREE_TOOLS[1:]):
            raise SystemExit("gate-night: %s not found beside the gate or in the hub" % t)
    base = Path(tempfile.mkdtemp(prefix=PREFIX + name + "-"))
    home, hub = base / "home", base / "hub"
    post = home / ".exocortex" / "post"
    for d in (hub / "tools", home / ".claude" / "projects", post / "pending", post / "holds",
              post / "waiters", home / ".codex" / "automations", home / "Library" / "LaunchAgents"):
        d.mkdir(parents=True, exist_ok=True)
    for t in TOOLS + (TREE_TOOLS if tree else ()):
        src = source_tool(t)
        if not src.is_file():
            if t in OPTIONAL or t in TREE_TOOLS[1:]:
                continue
            raise SystemExit("gate-night: %s not found beside the gate or in the hub" % t)
        shutil.copy2(str(src), str(hub / "tools" / t))
    write_json(hub / "registry.json", REGISTRY)
    machine = base / "machine.json"
    write_json(machine, {"name": "north", "os": "gate",
                         "roots": {"orchestrator": str(hub), "projects": str(base / "projects"),
                                   "home": str(home), "claude": str(home / ".claude"),
                                   "codex": str(home / ".codex"), "post": str(post)}})
    (base / "projects").mkdir(exist_ok=True)
    write_json(home / ".claude.json", {"oauthAccount": {"emailAddress": "wren@example.test",
                                                        "accountUuid": "a1b2c3d4-0217"}})
    store = home / "Library" / "Application Support" / "Claude" / "claude-code-sessions" / "acct" / "org"
    store.mkdir(parents=True, exist_ok=True)
    for job in ("pulse", "postman", "regen", "sync"):
        write(home / "Library" / "LaunchAgents" / ("com.exocortex.%s.plist" % job), "<plist/>\n")
    ps = base / "ps.txt"
    write(ps, "")
    w = {"base": base, "home": home, "hub": hub, "post": post, "store": store, "ps": ps,
         "env": {"HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home / "AppData" / "Roaming"),
                 "EXO_MACHINE_JSON": str(machine), "EXO_REGISTRY_JSON": str(hub / "registry.json"),
                 "EXO_NIGHT_PS": str(ps), "CLAUDE_CODE_SESSION_ID": None, "EXO_USAGE_STATE_DIR": str(base / "ustate"),
                 "COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_OUT": None, "PYTHONIOENCODING": "utf-8"}}
    WORLDS.append(w)
    window(w, SID_HUB, FABLE, T_HUB, 340000)
    window(w, SID_LANE, FABLE, T_LANE, 230000)
    window(w, SID_DESK, SONNET, T_DESK, 90000)
    window(w, SID_OLD, SONNET, T_OLD, 50000)
    for sid, title, model in ((SID_HUB, T_HUB, FABLE), (SID_LANE, T_LANE, FABLE), (SID_DESK, T_DESK, SONNET)):
        write_json(store / ("local_%s.json" % sid[-4:]), {
            "sessionId": "local_%s" % sid[-4:], "cliSessionId": sid, "title": title, "isArchived": False,
            "lastActivityAt": int((NOW - timedelta(minutes=30)).timestamp() * 1000),
            "lastFocusedAt": int((NOW - timedelta(minutes=30)).timestamp() * 1000), "model": model})
    routines(w, [("gate-sonnet-watcher", "Gate sonnet watcher", "0 2 * * *", "sonnet")])
    live(w, [])
    return w


def window(w, sid, model, title, context):
    folder = w["home"] / ".claude" / "projects" / "-gate-night"
    rows = [{"type": "user", "sessionId": sid, "uuid": "u1", "timestamp": zulu(NOW - timedelta(hours=1)),
             "message": {"role": "user", "content": "go %s" % MARK}},
            {"type": "assistant", "sessionId": sid, "uuid": "a1", "requestId": "r1",
             "timestamp": zulu(NOW - timedelta(minutes=59)),
             "message": {"role": "assistant", "model": model, "id": "m1",
                         "content": [{"type": "text", "text": "done"}],
                         "usage": {"input_tokens": 10, "cache_read_input_tokens": context - 10,
                                   "cache_creation_input_tokens": 0, "output_tokens": 5}}}]
    write(folder / ("%s.jsonl" % sid), "\n".join(json.dumps(r) for r in rows) + "\n")
    write_json(folder / sid / "custom-title.json", {"customTitle": title})


def routines(w, rows):
    tasks = []
    for tid, name, cron, model in rows:
        skill = w["home"] / ".claude" / "scheduled-tasks" / tid / "SKILL.md"
        front = ("model: %s\n" % model) if model else ""
        write(skill, "---\nname: %s\n%sdescription: %s fixture\n---\n1. do the thing\n" % (tid, front, MARK))
        tasks.append({"id": tid, "displayName": name, "cronExpression": cron, "enabled": True,
                      "filePath": str(skill), "permissionMode": "bypassPermissions"})
    write_json(w["store"] / "scheduled-tasks.json", {"scheduledTasks": tasks, "recordedSkips": {}})


def live(w, sessions):
    write_json(w["hub"] / "live-sessions-north.json",
               {"machine": "north", "when": iso(NOW - timedelta(minutes=1)), "live_minutes": 10,
                "sessions": sessions})


def live_row(sid, model, title):
    return {"id": sid, "kind": "claude", "model": model, "title": title, "minutes_ago": 0.5}


def ps_table(w, lines):
    write(w["ps"], "\n".join(lines) + ("\n" if lines else ""))


def waiter_lines(addr, title, pid, etime="58:00", model=None, force=False):
    py = "/Library/Developer/CommandLineTools/usr/bin/python3"
    tail = (" --model %s" % model if model else "") + (" --force" if force else "")
    cmd = "%s /x/hub/tools/mail.py --wait %s --title %s%s" % (py, addr, title, tail)
    shell = "/bin/zsh -c source /x/.zshrc && %s" % cmd
    return ["%6d %s %s" % (pid, etime, cmd), "%6d %s %s" % (pid - 1, etime, shell)]


def pending(w, sid, items):
    write_json(w["post"] / "pending" / ("%s.json" % sid), {"session": sid, "updated": iso(NOW), "items": items})


def send_item(target_sid, title, queued_min=20):
    return {"token": "sd-%s" % target_sid[-6:], "kind": "send", "fyi": False,
            "target": "local_%s" % target_sid[-4:], "title": title, "why": "fronted",
            "message": "MAIL for GATE — %s" % MARK, "tokens": ["pm-aaaaaaaaaaaa"],
            "queued": iso(NOW - timedelta(minutes=queued_min))}


def letter_item(n=1):
    return {"token": "pm-%012d" % n, "kind": "letter", "line": "- %s · to: NORTH/Lane · x · y · z" % MARK,
            "to": "NORTH/Lane", "fyi": False, "queued": iso(NOW - timedelta(minutes=40))}


def night(w, *args, extra=None):
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1"})
    for k, v in list(w["env"].items()) + list((extra or {}).items()):
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    p = subprocess.run([PY, str(w["hub"] / "tools" / "night-check.py"), "--now", NOW_ISO] + list(args),
                       cwd=str(w["hub"]), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def last(out):
    lines = [l for l in out.splitlines() if l.strip()]
    return lines[-1] if lines else ""


# ── the cases ────────────────────────────────────────────────────────────────

def armed_world(name):
    w = world(name)
    ps_table(w, waiter_lines("NORTH/hub", T_HUB, 4123, force=True)
             + waiter_lines("NORTH/Gatehub-Desk", T_DESK, 4200, etime="02:12:00", model="sonnet"))
    write(w["post"] / "waits.jsonl", json.dumps({"title": T_HUB, "session": SID_HUB, "model": FABLE,
                                                  "verdict": "forced", "why": "this window is %s" % FABLE,
                                                  "to": "NORTH/hub", "when": iso(NOW - timedelta(minutes=58))})
          + "\n")
    pending(w, SID_DESK, [send_item(SID_LANE, T_LANE)])
    return w


def case_na():
    start("N-a", "an armed waiter on Fable, a send order into Fable, a Sonnet routine: named, refused")
    w = armed_world("na")
    code, out = night(w)
    lines = out.splitlines()
    waiter = [l for l in lines if l.startswith("waiter") and "pid 4123" in l]
    check(len(waiter) == 1 and "mail.py --wait NORTH/hub" in waiter[0] and ("«%s»" % T_HUB) in waiter[0]
          and "that window is FABLE" in waiter[0] and "armed 21:16" in waiter[0]
          and "FORCED past its refusal 21:16 (waits.jsonl)" in waiter[0],
          "the waiter is named — its address, pid, armed time, window, model, and waits.jsonl's "
          "forced row: %s" % (waiter[0] if waiter else lines[:3]))
    check(not any("pid 4122" in l for l in lines), "its shell wrapper is not a second waiter")
    desk = [l for l in lines if "pid 4200" in l]
    check(len(desk) == 1 and "SONNET" in desk[0] and "never Fable" in desk[0],
          "the Desk's Sonnet waiter is listed as a Sonnet turn: %s" % (desk[0] if desk else ""))
    send = [l for l in lines if l.startswith("send")]
    check(len(send) == 1 and ("«%s»" % T_LANE) in send[0] and "FABLE" in send[0]
          and "context 23 %" in send[0] and "queued 21:54" in send[0] and ("«%s»" % T_DESK) in send[0]
          and "its waiter is armed" in send[0],
          "the send order is named — its Fable target by the app's own id, its context, when it was "
          "queued, its carrier and the carrier's road: %s" % (send[0] if send else ""))
    routine = [l for l in lines if l.startswith("routine")]
    check(len(routine) == 1 and re.search(r"Gate sonnet watcher · sonnet · next (\w{3} )?02:00", routine[0]),
          "the Sonnet routine is named with its model and next fire: %s" % (routine[0] if routine else ""))
    tail = last(out)
    check(code == 2 and tail.startswith("CAN WAKE FABLE: the waiter pid 4123 on «%s» — stop it: " % T_HUB)
          and "and 1 more above" in tail,
          "the quiet line is REFUSED: exit 2 and `CAN WAKE FABLE: <the waiter> — <the move>` "
          "(%d): %s" % (code, tail))
    check("nothing can wake" not in out, "the words 'nothing can wake' appear nowhere")


def case_nb():
    start("N-b", "the clean world: the quiet line, word for word")
    w = world("nb")
    code, out = night(w)
    tail = last(out)
    want = "nothing can wake a Fable window tonight · sonnet routine fires at 02:00 · read 22:14"
    check(code == 0 and tail == want, "exit 0 and: %s (%d)" % (tail, code))
    jobs = [l for l in out.splitlines() if l.startswith("jobs")]
    check(jobs == ["jobs     launchd com.exocortex.{postman,pulse,regen,sync} — no model, never a turn"],
          "the scheduler's jobs: no model, never a turn: %s" % jobs)
    meter = [l for l in out.splitlines() if l.startswith("meter")]
    check(len(meter) == 1 and "USAGE · wren@example.test · refresh" in meter[0],
          "the meter line is usage.py's own words (no reading in this world: refresh): %s" % meter)


def case_nc():
    start("N-c", "in-window timers are named as unseeable, in both worlds, text and --json")
    want = "cannot see: in-window timers (ScheduleWakeup, loop, cron) — they live inside the app"
    for w in (armed_world("nc1"), world("nc2")):
        _code, out = night(w)
        check(want in out.splitlines(), "%s: the text names them" % w["base"].name)
        _code, raw = night(w, "--json")
        try:
            d = json.loads(raw)
        except ValueError:
            d = {}
        check(want in (d.get("cannot_see") or []), "%s: --json names them" % w["base"].name)


def case_ne():
    start("N-e", "--json round-trips; --line is the last line alone")
    for w in (armed_world("ne1"), world("ne2")):
        code, out = night(w)
        jcode, raw = night(w, "--json")
        lcode, line = night(w, "--line")
        try:
            d = json.loads(raw)
        except ValueError:
            d = {}
        check(d.get("last") == last(out) and line.strip() == last(out),
              "%s: the same last line three ways: %s" % (w["base"].name, d.get("last")))
        words = [i.get("words") for i in d.get("items") or []]
        text = out.splitlines()
        check(words and all(any(t.endswith(x) for t in text) for x in words),
              "%s: every --json item is a line of the text (%d)" % (w["base"].name, len(words)))
        check(code == jcode == lcode == d.get("exit"), "%s: the same exit (%s)" % (w["base"].name, code))
        check(isinstance(d.get("can_wake"), list) and (d["can_wake"] != []) == (code == 2),
              "%s: can_wake lists exactly what refuses the quiet line" % w["base"].name)


def case_nf():
    start("N-f", "Windows: the process CSV; tasklist never claims quiet")
    w = world("nf")
    armed = NOW - timedelta(minutes=58)
    off = int(armed.utcoffset().total_seconds() // 60)
    wmic = "%s.123456%s%03d" % (armed.strftime("%Y%m%d%H%M%S"), "-" if off < 0 else "+", abs(off))
    csv = ('"ProcessId","CreationDate","CommandLine"\r\n'
           '"5120","%s","C:\\Windows\\system32\\svchost.exe -k netsvcs"\r\n'
           '"6400","%s","\\"C:\\Python39\\python.exe\\" C:\\hub\\tools\\mail.py '
           '--wait NORTH/hub --title \\"%s\\" --force"\r\n' % (armed.isoformat(), wmic, T_HUB))
    write(w["ps"], csv.replace('\\"', '""'))
    code, out = night(w)
    waiter = [l for l in out.splitlines() if l.startswith("waiter")]
    check(len(waiter) == 1 and "pid 6400" in waiter[0] and ("«%s»" % T_HUB) in waiter[0] and "FABLE" in waiter[0]
          and "armed 21:16" in waiter[0],
          "a python.exe waiter is found by its command line, its window's model read, wmic's date "
          "read: %s" % (waiter[0] if waiter else out[:200]))
    check(code == 2 and last(out).startswith("CAN WAKE FABLE: the waiter pid 6400"), "the quiet line refused (%d)" % code)
    write(w["ps"], '"Image Name","PID","Session Name","Session#","Mem Usage"\r\n'
                   '"svchost.exe","5120","Services","0","9,000 K"\r\n'
                   '"python.exe","6400","Console","1","22,000 K"\r\n')
    code, out = night(w)
    check(code == 2 and "1 python process whose command line this machine will not show" in last(out)
          and "PowerShell or wmic" in last(out),
          "tasklist shows no command line: the python process cannot be ruled out: %s" % last(out))
    wmic_csv = ("Node,CommandLine,CreationDate,ProcessId\r\n"
                "NORTH,C:\\Windows\\system32\\svchost.exe,%s,5120\r\n"
                "NORTH,C:\\Python39\\python.exe C:\\hub\\tools\\mail.py --wait NORTH/hub --title %s,%s,6500\r\n"
                % (wmic, T_HUB, wmic))
    Path(w["ps"]).write_bytes(wmic_csv.encode("utf-16"))
    code, out = night(w)
    waiter = [l for l in out.splitlines() if l.startswith("waiter")]
    check(code == 2 and len(waiter) == 1 and "pid 6500" in waiter[0] and ("«%s»" % T_HUB) in waiter[0]
          and "armed 21:16" in waiter[0],
          "wmic's own shape — UTF-16 into a pipe, its column order, its date — reads the same, the "
          "title's dash intact: %s" % (waiter[0] if waiter else last(out)))
    write(w["ps"], '"ProcessId","CreationDate","CommandLine"\r\n"5120","","C:\\Windows\\system32\\svchost.exe"\r\n')
    code, out = night(w)
    check(code == 0 and last(out).startswith("nothing can wake a Fable window tonight"),
          "a CSV with no waiter: quiet (%d): %s" % (code, last(out)))


def case_ng():
    start("N-g", "the rules at the edges")
    w = world("ng1")
    pending(w, SID_LANE, [letter_item(1), letter_item(2)])
    pending(w, SID_OLD, [letter_item(3), letter_item(4), letter_item(5)])
    live(w, [dict(live_row(SID_LANE, FABLE, T_LANE), transcript=str(
        w["home"] / ".claude" / "projects" / "-gate-night" / ("%s.jsonl" % SID_LANE)))])
    code, out = night(w)
    letters = [l for l in out.splitlines() if l.startswith("letters")]
    check(code == 0 and letters and ("pending → «%s» · FABLE · context 23 %% · 2 waiting" % T_LANE) in letters[0]
          and "a Fable window is never woken from idle; this waits for its next turn" in letters[0],
          "letters queued for a Fable window wait for its next turn — named, quiet stands (%d): %s"
          % (code, letters[:1]))
    check(any(l.endswith("3 more letters wait in 1 window's own file — each shows at that window's "
                         "next turn; none starts one") for l in letters),
          "letters for a window that is neither Fable-live nor holding a lane are counted, not named: %s"
          % letters[-1:])
    livel = [l for l in out.splitlines() if l.startswith("live")]
    check(livel and ("FABLE «%s» · live" % T_LANE) in livel[0] and "nothing waits on Fable" in livel[0],
          "the live Fable window is named with the rule that keeps it quiet: %s" % livel[:1])
    w = world("ng2")
    pending(w, SID_OLD, [send_item(SID_LANE, T_LANE)])
    code, out = night(w)
    send = [l for l in out.splitlines() if l.startswith("send")]
    check(code == 0 and send and "the carrier shows no road to a turn" in send[0],
          "a send order into Fable whose carrier shows no road: listed, not counted (%d): %s" % (code, send[:1]))
    live(w, [dict(live_row(SID_OLD, SONNET, T_OLD), transcript="")])
    code, out = night(w)
    check(code == 2 and "the send order into «%s»" % T_LANE in last(out) and "say «mail»" in last(out),
          "…the same order, its carrier LIVE: it can wake Fable, and the move is named: %s" % last(out))
    w = world("ng3")
    routines(w, [("gate-fable", "Gate fable routine", "0 3 * * *", "fable")])
    code, out = night(w)
    check(code == 2 and last(out).startswith("CAN WAKE FABLE: the routine «Gate fable routine» at 03:00 can run on Fable")
          and "model: sonnet" in last(out), "a routine on Fable firing tonight CAN (%d): %s" % (code, last(out)))
    routines(w, [("gate-bare", "Gate bare routine", "30 4 * * *", "")])
    code, out = night(w)
    check(code == 2 and "Gate bare routine" in last(out),
          "…and one with no model line (the app's default can be Fable): %s" % last(out))
    routines(w, [("gate-fable", "Gate fable routine", "0 15 * * *", "fable")])
    code, out = night(w)
    rline = [l for l in out.splitlines() if "Gate fable routine" in l]
    check(code == 0 and rline and "routines never run on Fable" in rline[0],
          "a Fable routine that fires after the night is listed with its fault, not counted (%d)" % code)
    w = world("ng4")
    write_json(w["hub"] / "usage-settings.json", {"wait_refuse_models": []})
    write_json(w["post"] / "holds" / ("%s.json" % SID_LANE),
               {"session": SID_LANE, "title": T_LANE, "arcs": ["Gatehub/Lane"], "arm": True})
    live(w, [dict(live_row(SID_LANE, FABLE, T_LANE), transcript=str(
        w["home"] / ".claude" / "projects" / "-gate-night" / ("%s.jsonl" % SID_LANE)))])
    code, out = night(w)
    check(code == 2 and "would arm a waiter" in last(out) and "wait_refuse_models" in last(out),
          "a lane-holding live Fable window whose model the refuse list does not name CAN: %s" % last(out))
    w = world("ng5")
    code, out = night(w, extra={"EXO_NIGHT_PS": str(w["base"] / "no-such-table.txt")})
    check(code == 2 and "the process table could not be read" in last(out),
          "a process table that cannot be read never claims quiet (%d): %s" % (code, last(out)))


PROBE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("co", sys.argv[1])
co = importlib.util.module_from_spec(spec); spec.loader.exec_module(co)
print(json.dumps(co.night_facts(co.machine_roots()), ensure_ascii=False))
'''


def case_nh():
    start("N-h", "the collar carries the same last line and the whole list")
    w = world("nh", tree=True)
    if not (w["hub"] / "tools" / "collect-openers.py").is_file():
        check(False, "collect-openers.py is not beside this gate — N-h cannot run; named, never passed")
        return
    ps_table(w, waiter_lines("NORTH/hub", T_HUB, 4123))
    probe = w["base"] / "probe.py"
    write(probe, PROBE)
    env = dict(os.environ)
    for k, v in w["env"].items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    p = subprocess.run([PY, str(probe), str(w["hub"] / "tools" / "collect-openers.py")], cwd=str(w["hub"]),
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    raw = p.stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        facts = json.loads(raw[-1]) if raw else {}
    except ValueError:
        facts = {}
    _c, jraw = night(w, "--json", extra={})
    try:
        d = json.loads(jraw)
    except ValueError:
        d = {}
    # the collector reads the clock itself, so its read time differs; the verdict must not
    fl = re.sub(r"read \d\d:\d\d", "read HH:MM", facts.get("last") or "")
    dl = re.sub(r"read \d\d:\d\d", "read HH:MM", d.get("last") or "")
    check(bool(fl) and fl == dl and fl.startswith("CAN WAKE FABLE: the waiter pid 4123"),
          "the collector's night line is the tool's own: %s" % (facts.get("last") or raw[-2:]))
    rows = facts.get("rows") or []
    kinds = [r[0] for r in rows]
    check("waiter" in kinds and "cannot see" in kinds and "routine" in kinds and "jobs" in kinds
          and rows[-1][0] == "read",
          "its answer carries every row of the list, the unseeable timers, and where it was read: %s" % kinds)
    # the page itself: the hub's own opener gives the collar its tile; rendered to a scratch path
    write(w["hub"] / "STATUS.md", "# STATUS\n\n## Now\n\nThe gate hub.\n\n## To do\n\n- [ ] a hub item\n")
    write(w["hub"] / "OPENER.md", "lane: Gatehub/hub\nwritten: %s\nby: the gate\non: NORTH\nhead: \n"
          "status_updated: %s\nwhere: the gate hub stands here\nnext: machine\ndepends_on: nothing\n"
          "open_in: NORTH · a fresh session · ACT — Gatehub/hub: the gate\nmodel: SONNET · HIGH\n---\n"
          "read the project status/memory first.\n\n1. the first step\n" % (iso(NOW), iso(NOW)))
    (w["base"] / "vol").mkdir(exist_ok=True)
    page = w["base"] / "out" / "tree.html"
    renv = dict(env, COLLECT_OPENERS_OUT=str(page), COLLECT_OPENERS_VOLUMES=str(w["base"] / "vol"),
                COLLECT_OPENERS_WORK=str(w["base"] / "work"), COLLECT_OPENERS_ENGINE=str(w["base"] / "engine"))
    renv.pop("COLLECT_OPENERS_ROOT", None)
    p = subprocess.run([PY, str(w["hub"] / "tools" / "collect-openers.py"), "--html"], cwd=str(w["hub"]),
                       env=renv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    html = io.open(str(page), encoding="utf-8").read() if page.is_file() else ""
    m = re.search(r'<div class="npbeat" data-mark="night">night · ([^<]+)</div>', html)
    check(m is not None and re.sub(r"read \d\d:\d\d", "read HH:MM", m.group(1).replace("&laquo;", "«")
                                     .replace("&raquo;", "»")).startswith("CAN WAKE FABLE: the waiter pid 4123"),
          "the rendered collar carries the night line in the beat line's own class (no new class, "
          "colour or font): %s" % (m.group(1)[:90] if m else ("no page: " + p.stdout.decode("utf-8", "replace")[-200:]
                                                               if not html else "no night line in the collar")))
    mm = re.search(r'"night": (\{"kind": "what can take a model turn while nobody is here", "bytes": \[.*?\]\]\})', html)
    try:
        entry = json.loads(mm.group(1)) if mm else {}
    except ValueError:
        entry = {}
    kinds = [r[0] for r in entry.get("bytes") or []]
    check(entry and kinds[0] == "the last line" and "waiter" in kinds and "cannot see" in kinds,
          "its click answers with the last line and the whole list, from the page's own answers: %s" % kinds)


def case_ni(before_hubs):
    start("N-i", "rails")
    w = armed_world("ni")
    snap = snapshot(w["base"])
    night(w)
    night(w, "--json")
    night(w, "--line")
    after = snapshot(w["base"])
    changed = sorted(k for k in set(snap) | set(after) if snap.get(k) != after.get(k))
    check(not changed, "the tool wrote nothing in its world (%d files, byte for byte): %s"
          % (len(after), changed[:3]))
    src = io.open(str(w["hub"] / "tools" / "night-check.py"), encoding="utf-8").read()
    bad = [m for m in ("urllib", "http.client", "socket", "requests", "smtplib", "anthropic")
           if re.search(r"^\s*(import|from)\s+%s" % re.escape(m), src, re.M)]
    check(not bad, "no network module is imported: %s" % bad)
    calls = set(re.findall(r'run\(\["([a-z]+)"', src))
    check(calls <= {"ps", "powershell", "wmic", "tasklist", "schtasks"},
          "it runs only the process and scheduler readers: %s" % sorted(calls))
    check(not re.search(r"os\.(remove|unlink|kill|replace|rename)|shutil\.|\.write_text|\.write_bytes|"
                        r"open\([^)]*,\s*[\"'][wax][bt+]*[\"']", src),
          "no write, no delete and no kill in its source")
    tmp = str(Path(tempfile.gettempdir()).resolve())
    check(all(str(x["base"].resolve()).startswith(tmp) and x["base"].name.startswith(PREFIX) for x in WORLDS),
          "every world (%d) sits under the system temp folder with the %s prefix" % (len(WORLDS), PREFIX))
    live_hub = None
    try:
        live_hub = json.load(io.open(str(Path.home() / "orchestrator-sync" / "machine.json"),
                                     encoding="utf-8"))["roots"]["orchestrator"]
    except Exception:
        pass
    if live_hub:
        check(all(not str(x["base"].resolve()).startswith(str(Path(live_hub).resolve())) for x in WORLDS),
              "…and none under the live hub")
    check(before_hubs == hub_marks(), "the live post folder and hub carry no fixture word of this gate")


def hub_marks():
    """This gate's marker word anywhere in the live post folder or the live hub's post files."""
    hits = []
    try:
        rec = json.load(io.open(str(Path.home() / "orchestrator-sync" / "machine.json"), encoding="utf-8"))
        roots = rec.get("roots") or {}
    except Exception:
        roots = {}
    post = Path(roots.get("post") or Path.home() / ".exocortex" / "post")
    for p in list((post / "pending").glob("*.json")) + list((post / "holds").glob("*.json")):
        try:
            if MARK in p.read_text(encoding="utf-8", errors="replace"):
                hits.append(str(p))
        except OSError:
            pass
    return hits


def main(argv):
    keep = "--keep" in argv
    print("gate-night.py · %s · the clock forced to %s" % (datetime.now().strftime("%Y-%m-%d %H:%M"), NOW_ISO))
    print("  tools from: %s" % source_tool("night-check.py").parent)
    before = hub_marks()
    try:
        for case in (case_na, case_nb, case_nc, case_ne, case_nf, case_ng, case_nh):
            try:
                case()
            except Exception as exc:
                FAILS.append("%s: the case raised %r" % (CASE[0], exc))
                print("  [FAIL] the case raised %r" % (exc,))
        try:
            case_ni(before)
        except Exception as exc:
            FAILS.append("N-i: the case raised %r" % (exc,))
            print("  [FAIL] the case raised %r" % (exc,))
    finally:
        if not keep:
            for w in WORLDS:
                shutil.rmtree(str(w["base"]), ignore_errors=True)
    print("\n  N-d is gate-wake-screen's W9 (the wake screen prints the last line)")
    print("\n===== GATES =====")
    print("  %d checks · %d passed · %d failed" % (PASSES[0] + len(FAILS), PASSES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL  %s" % f)
    if keep:
        print("  worlds kept: %s" % ", ".join(str(w["base"]) for w in WORLDS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
