#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-routines.py — the routine check's gate: a routine never asks the human anything.

    python3 tools/gate-routines.py            every case (python on Windows)
    python3 tools/gate-routines.py --keep     leave the worlds for inspection

HERMETIC: every world is made under the system temp folder (tempfile.mkdtemp) — a scratch HOME
holding the desktop app's task store in its real shape (Library/Application Support on macOS,
AppData/Roaming on Windows), a scratch hub, a scratch pulse state folder and the notifier's seam
(a script that records the texts it was handed). No real task store, no real notice, no real
scheduler, no network. The tools run from the copies beside this gate (a staged build) or the
hub's tools/.

  R1  WILL PROMPT     an enabled task with no permission mode is `!!` and `WILL PROMPT — N prompts
                      at the next boot`, and the fix is ONE sweep-list step naming every such task
                      with the Edit-form path; a disabled one is not counted; another account's
                      store is said, not counted; exit 1 while any prompts
  R2  THE CATCH-UP    the answer learned first-hand is in the sheet verbatim; a store in the
                      shape the app writes at a boot catch-up (the latest missed slot) says RUN; a
                      catch-up older than its own interval says SKIP; a catch-up whose regular fire
                      is due within 15 minutes is SKIP BY DEFAULT (a real catch-up,
                      08:17 for the 08:25 slot, replayed), `--near-minutes 0` switches that off and
                      `--near-minutes N` overrides it; weekly and twice-daily intervals come out
                      right; every command-running template's FIRST step is that check, the one bare
                      command with no flag on it
  R3  ONE ACTION      no template carries a compound command (`;` `&&` `||` `|` outside quotes, a
                      leading `cd` or `NAME=value`), every command-running one says so in words and
                      gives its scratch folder in words; the release reminder runs no command at all
  R4  AT BOOT         two UNSET tasks → ONE notice naming both; the same boot → none; a new boot →
                      one again; all Bypass → none (the marker still written); a notifier that fails
                      is tried at the next beat and decided after two; the staged pulse calls it on
                      its beat, after the postman, and passes its state folder
  R5  WINDOWS-TRUE    a cp1252 console prints the sweep step with no traceback (→ becomes ->); the
                      Windows store layout (APPDATA) is read; no path literal in the tool

Stdlib only, Python 3.9, OS-neutral. Exit 0 only when every check passes.
"""
import io
import json
import os
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent


def _older_sync_dirname():
    """The older layout's sync folder, by the one name the path resolver keeps
    (exo_paths.LEGACY_SYNC_DIRNAME), read from the resolver beside this gate and
    never typed here."""
    for cand in (HERE / "exo_paths.py", HERE.parent / "tools" / "exo_paths.py"):
        if cand.is_file():
            cached = sys.dont_write_bytecode
            try:
                sys.dont_write_bytecode = True
                spec = importlib.util.spec_from_file_location("exo_paths_names", str(cand))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.LEGACY_SYNC_DIRNAME
            finally:
                sys.dont_write_bytecode = cached
    sys.exit("%s: the path resolver (exo_paths.py) is not beside this gate; nothing was proved."
             % Path(__file__).name)


OLDER_SYNC = _older_sync_dirname()

PY = sys.executable or "python3"
FAILS, PASSES, CASE, WORLDS = [], [0], [""], []
EDIT = ("Claude app \u2192 Routines \u2192 the task \u2192 Edit \u2192 Permission mode = "
        "Bypass permissions \u2192 Save")
NOTIFY_SEAM = (
    "import io, json, os, sys\n"
    "rec = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notify-calls.jsonl')\n"
    "io.open(rec, 'a', encoding='utf-8').write(json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n')\n"
    "sys.exit(int(os.environ.get('EXO_NOTIFY_FAIL') or 0))\n")
COMMAND_TEMPLATES = ("build-runner.md", "lesson-miner-watcher.md", "memory-hygiene-watcher.md",
                     "session-hygiene-watcher.md")


def source(rel):
    """A staged file beside this gate's folder first (tools/x beside the gate, routines/ and
    design/ beside its parent), else the live hub's."""
    for base in (HERE.parent, ):
        p = base / rel
        if p.exists():
            return p
    try:
        rec = json.load(io.open(str(Path.home() / OLDER_SYNC / "machine.json"),
                                encoding="utf-8"))
        return Path(rec["roots"]["orchestrator"]) / rel
    except Exception:
        return HERE.parent / rel


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


def zulu(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def world(name, windows=False):
    base = Path(tempfile.mkdtemp(prefix="exo-gate-routines-%s-" % name))
    WORLDS.append(base)
    home, hub = base / "home", base / "hub"
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    # usage.py rides beside routine-check.py, as in the hub — its ONE login resolver names
    # the signed-in account's store
    for t in ("routine-check.py", "usage.py", "postman.py", "exo_registry.py", "exo_paths.py",
              "exo_common.py"):
        src = source("tools/" + t)
        if src.is_file():
            shutil.copy2(str(src), str(hub / "tools" / t))
    write(base / "notify.py", NOTIFY_SEAM)
    store_root = (home / "AppData" / "Roaming" if windows
                  else home / "Library" / "Application Support")
    w = {"base": base, "home": home, "hub": hub, "state": base / "pulse-state",
         "store": store_root / "Claude" / "claude-code-sessions" / "acct" / "org",
         "env": {"HOME": str(home), "USERPROFILE": str(home),
                 "APPDATA": str(home / "AppData" / "Roaming"), "EXO_NOTIFY": str(base / "notify.py"),
                 "EXO_NOTIFY_FAIL": None, "EXO_PULSE_STATE_DIR": None, "EXO_MACHINE_JSON": None,
                 "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}}
    return w


def task(tid, name, cron="0 8 * * *", mode="bypassPermissions", enabled=True, slot=None,
         spawned=None, skill=True, w=None):
    t = {"id": tid, "displayName": name, "cronExpression": cron, "enabled": enabled,
         "cwd": "hub"}
    if mode:
        t["permissionMode"] = mode
    if slot is not None:
        t["lastScheduledFor"] = zulu(slot)
    if spawned is not None:
        t["lastRunAt"] = zulu(spawned)
    if w is not None and skill:
        path = w["home"] / ".claude" / "scheduled-tasks" / tid / "SKILL.md"
        write(path, "---\nname: %s\nmodel: sonnet\n---\n\nbody\n" % tid)
        t["filePath"] = str(path)
    return t


def store(w, tasks, folder=None):
    target = folder or w["store"]
    write_json(target / "scheduled-tasks.json", {"scheduledTasks": tasks, "recordedSkips": {}})


def rc(w, *args, extra=None):
    env = dict(os.environ)
    for k, v in list(w["env"].items()) + list((extra or {}).items()):
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    p = subprocess.run([PY, str(w["hub"] / "tools" / "routine-check.py"), "--home", str(w["home"]),
                        "--hub", str(w["hub"]), "--codex-home", str(w["base"] / "codex")]
                       + list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=str(w["hub"]), timeout=60)
    return p.returncode, p.stdout.decode(env.get("PYTHONIOENCODING") or "utf-8", "replace")


def notices(w):
    path = w["base"] / "notify-calls.jsonl"
    if not path.is_file():
        return []
    return [json.loads(l) for l in io.open(str(path), encoding="utf-8").read().splitlines() if l.strip()]


# ── the cases ────────────────────────────────────────────────────────────────

def case_r1():
    start("R1", "WILL PROMPT, and the fix as ONE sweep-list step")
    w = world("r1")
    store(w, [task("gate-manual", "Gate manual task", mode=None, w=w),
              task("gate-second", "Gate second task", mode=None, w=w),
              task("gate-bypass", "Gate bypass task", w=w),
              task("gate-off", "Gate disabled task", mode=None, enabled=False, w=w)])
    code, out = rc(w)
    lines = out.splitlines()
    manual = [l for l in lines if l.startswith("!! Gate manual task")]
    check(bool(manual) and "WILL PROMPT" in manual[0], "the Manual task is `!!` and WILL PROMPT: %r"
          % (manual[0][:90] if manual else ""))
    check(any(l.startswith("-- Gate disabled task") and "never fires" in l for l in lines),
          "a disabled task with no mode is `--`, never fires, not counted")
    check("WILL PROMPT \u2014 2 prompts at the next boot" in out,
          "the count line: `WILL PROMPT — 2 prompts at the next boot`")
    steps = [l for l in lines if l.startswith("STEP: ")]
    check(len(steps) == 1, "ONE step, not one per task (%d)" % len(steps))
    check(bool(steps) and steps[0] == "STEP: 2 routines will ask permission: Gate manual task, "
          "Gate second task \u2014 " + EDIT,
          "the step carries the whole list and the Edit-form path: %r" % (steps[0] if steps else ""))
    check(code == 1 and "2 still prompting" in lines[-1], "exit 1 while any prompts; the tail says 2")
    # another account's store: said, not counted. which store is the signed-in one
    # is the app's own config (lastKnownAccountUuid), never the newest folder — so the world
    # names its signed-in account the way the app does
    write_json(w["store"].parent.parent.parent / "config.json", {"lastKnownAccountUuid": "acct"})
    other = w["store"].parent.parent / "acct2" / "org2"
    store(w, [task("gate-old", "Gate old-account task", mode=None, w=w)], folder=other)
    past = time.time() - 86400
    for f in other.iterdir():
        os.utime(str(f), (past, past))
    code, out = rc(w)
    check("another account's store" in out and "Gate old-account task" in out
          and "STEP: 2 routines" in out,
          "a second account's store (not the newest) is said in its own line and kept out of the step")
    store(w, [task("gate-bypass", "Gate bypass task", w=w)])
    shutil.rmtree(str(other.parent), ignore_errors=True)
    code, out = rc(w)
    check(code == 0 and "STEP:" not in out and "all run without prompts" in out,
          "all Bypass: no step, exit 0")


def case_r2():
    start("R2", "the catch-up, learned first-hand, and the first step that checks it")
    sheet = source("design/ROUTINES-NO-PROMPT-2026-09-12.md")
    text = io.open(str(sheet), encoding="utf-8").read() if sheet.is_file() else ""
    sec2 = text.split("## 2.", 1)[-1].split("## 3.", 1)[0]
    check("Missed fires at boot" in sec2 and "ONE run per task" in sec2
          and "missed: '2026-09-21T15:40:00.000Z'" in sec2 and "global_limit (active=3" in sec2,
          "§2 holds the answer and the app's own log line verbatim (%s)" % sheet)
    w = world("r2")
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    # the shape the app writes at a boot catch-up: the LATEST missed slot, spawned at launch
    slot = (now - timedelta(hours=20)).astimezone()
    cron = "%d %d * * *" % (slot.minute, slot.hour)
    store(w, [task("gate-daily", "Gate daily", cron=cron, slot=slot, spawned=now, w=w)])
    code, out = rc(w, "--catch-up", "gate-daily")
    check(out.startswith("RUN") and "interval 1440 min" in out,
          "a boot catch-up of the latest missed slot (20 h late, daily) is RUN: %s" % out.strip())
    # two missed fires, as an app that REPLAYED every slot would write the older one
    old = (now - timedelta(hours=44)).astimezone()
    store(w, [task("gate-daily", "Gate daily", cron=cron, slot=old, spawned=now, w=w)])
    code, out = rc(w, "--catch-up", "gate-daily")
    check(out.startswith("SKIP") and "older than its own interval" in out,
          "a catch-up two slots old (44 h, daily) is SKIP: %s" % out.strip())
    # THE NEAR RULE: ON at 15 minutes by default.
    # A real catch-up as the fixture: a daily routine (`25 8 * * *`) caught up at 08:17 for
    # Wednesday's 08:25 slot, eight minutes before Thursday's regular fire — pinned by --now, so
    # the answer never depends on the hour this gate runs at.
    wed = datetime(2026, 9, 23, 8, 25).astimezone()
    thu = datetime(2026, 9, 24, 8, 17).astimezone()
    store(w, [task("gate-miner", "Gate miner", cron="25 8 * * *", slot=wed, spawned=thu, w=w)])
    code, out = rc(w, "--catch-up", "gate-miner", "--now", zulu(thu))
    check(code == 0 and out.startswith("SKIP") and "next regular fire due in 8 min" in out,
          "the 09-24 lesson miner, 08:17 for the 08:25 slot, is SKIP with no flag at all: %s"
          % out.strip())
    code, out = rc(w, "--catch-up", "gate-miner", "--now", zulu(thu), "--near-minutes", "0")
    check(code == 0 and out.startswith("RUN") and "interval 1440 min" in out,
          "`--near-minutes 0` switches the rule off, and the same run is RUN: %s" % out.strip())
    code, out = rc(w, "--catch-up", "gate-miner", "--now", zulu(thu), "--near-minutes", "5")
    check(out.startswith("RUN"), "`--near-minutes 5` overrides it: 8 min away is outside 5: %s"
          % out.strip())
    # …and the same shape on the live clock: a catch-up whose regular fire is 8 min away
    nxt = (now + timedelta(minutes=8)).astimezone()
    cron2 = "%d %d * * *" % (nxt.minute, nxt.hour)
    prev = nxt - timedelta(days=1)
    store(w, [task("gate-miner", "Gate miner", cron=cron2, slot=prev, spawned=now, w=w)])
    code, out = rc(w, "--catch-up", "gate-miner")
    check(out.startswith("SKIP") and "next regular fire due in" in out,
          "on the live clock too, the default skips a catch-up 8 min before its regular fire: %s"
          % out.strip())
    code, out = rc(w, "--catch-up", "gate-miner", "--near-minutes", "60")
    check(out.startswith("SKIP") and "next regular fire due in" in out,
          "with --near-minutes 60 the catch-up 8 min before its regular fire is SKIP: %s" % out.strip())
    code, out = rc(w, "--catch-up", "gate-miner", "--near-minutes", "soon")
    check(code == 2 and "wants a number of minutes" in out,
          "a --near-minutes that is not a number is exit 2 and says so: %s" % out.strip()[:80])
    src = source("tools/routine-check.py")
    doc = io.open(str(src), encoding="utf-8").read() if src.is_file() else ""
    check("NEAR_MINUTES_DEFAULT = 15.0" in doc and "15 by default; 0 switches that off" in doc,
          "the tool says its own default where a reader looks (its usage text)")
    # intervals: weekly and twice-daily
    mon = datetime(2026, 9, 21, 8, 40).astimezone()
    store(w, [task("gate-weekly", "Gate weekly", cron="40 8 * * 1", slot=mon,
                   spawned=mon + timedelta(days=3), w=w)])
    # pinned to the spawn: with the near rule ON by default, the live clock early on a Monday morning would
    # otherwise put the next regular fire inside 15 minutes and turn this into a clock test
    code, out = rc(w, "--catch-up", "gate-weekly", "--now", zulu(mon + timedelta(days=3)))
    check(out.startswith("RUN") and "interval 10080 min" in out,
          "weekly: 3 days late is inside its 7-day interval: %s" % out.strip())
    eve = datetime(2026, 9, 20, 17, 0).astimezone()
    store(w, [task("gate-twice", "Gate twice", cron="0 9,17 * * *", slot=eve,
                   spawned=eve + timedelta(hours=17), w=w)])
    code, out = rc(w, "--catch-up", "gate-twice")
    check(out.startswith("SKIP") and "interval 960 min" in out,
          "twice daily: the 17:00 slot caught up 17 h later is past its 16 h gap: %s" % out.strip())
    code, out = rc(w, "--catch-up", "gate-nobody")
    check(out.startswith("RUN") and "no task" in out, "an unknown task id is RUN, and says why")
    for name in COMMAND_TEMPLATES:
        p = source("routines/" + name)
        body = io.open(str(p), encoding="utf-8").read() if p.is_file() else ""
        tid = name[:-3]
        proc = body.split("Procedure", 1)[-1]
        first = re.search(r"\n(\d+)\. (.*)", proc)
        check(bool(first) and first.group(1) == "0"
              and ("`python3 tools/routine-check.py --catch-up %s`" % tid) in first.group(2)
              and "SKIP" in first.group(2),
              "%s: its FIRST step is the catch-up check, one command" % name)
        check(bool(first) and "--near-minutes" not in first.group(2),
              "%s: …the bare command — the 15-minute rule is the tool's default, never a flag "
              "copied into four templates" % name)


def spans(text):
    """Every `…` code span of a template."""
    return re.findall(r"`([^`\n]+)`", text)


def compound(cmd):
    """Why one command span is a compound line, or ''. Quoted text is data, not shell, and a
    span that is not a command at all (`;` named in a sentence, a file name) is not judged."""
    if not re.match(r"\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S|[A-Za-z0-9_.~/\\-]+\s+\S)", cmd):
        return ""
    bare = re.sub(r'"[^"]*"|\'[^\']*\'', '""', cmd)
    if re.search(r";|&&|\|\||(?<![|])\|(?![|])", bare):
        return "joined with ; && || or |"
    head = bare.strip()
    if re.match(r"cd\s", head):
        return "starts with cd"
    if re.match(r"[A-Za-z_][A-Za-z0-9_]*=\S+\s+\S", head):
        return "starts with NAME=value"
    return ""


def case_r3():
    start("R3", "one action per command; the scratch folder in words")
    for name in COMMAND_TEMPLATES + ("release-countdown.md",):
        p = source("routines/" + name)
        body = io.open(str(p), encoding="utf-8").read() if p.is_file() else ""
        bad = [(c, compound(c)) for c in spans(body) if compound(c)]
        check(body and not bad, "%s: no compound command span %s" % (name, bad[:2]))
        check(not re.search(r"(?i)\brun\b[^.\n]{0,80}\bfrom ~/" + re.escape(OLDER_SYNC) + r"\b", body),
              "%s: no command told to run FROM another folder (a cd in disguise)" % name)
        if name in COMMAND_TEMPLATES:
            check("ONE ACTION PER COMMAND" in body and "scratchpad directory your session context names" in body,
                  "%s: the rule and the scratch folder are said in words" % name)
    p = source("routines/release-countdown.md")
    body = io.open(str(p), encoding="utf-8").read() if p.is_file() else ""
    check("do not run any command" in body.lower() and "--catch-up" not in body,
          "release-countdown runs no command at all (one Read), so it takes no catch-up step")
    check(compound(";") == "" and compound("&&") == ""
          and compound("python3 -c \"import json,pathlib;print(1)\"") == ""
          and compound("cd /c/Users/you/Exocortex; SC=1") != ""
          and compound("SC=/tmp/x python3 tools/a.py") != "",
          "the detector itself: quoted Python is data; a Windows shell's `cd …; SC=…` shape is caught")


def case_r4():
    start("R4", "at boot: ONE notice naming every routine that will ask, once per boot")
    w = world("r4")
    store(w, [task("gate-a", "Gate watcher one", mode=None, w=w),
              task("gate-b", "Gate watcher two", mode=None, w=w),
              task("gate-c", "Gate bypass", w=w)])
    st = str(w["state"])
    code, out = rc(w, "--boot-notice", "--boot-id", "1000000", "--state-dir", st, "--machine", "north")
    got = notices(w)
    check(code == 0 and len(got) == 1, "one notice (%d)" % len(got))
    check(bool(got) and got[0][-1] == "2 routines will ask permission: Gate watcher one, Gate watcher two "
          "\u2014 " + EDIT, "the notice names both and the Edit-form path: %r" % (got[0][-1] if got else ""))
    marker = w["state"] / "routines-boot-north.json"
    check(marker.is_file() and json.load(io.open(str(marker), encoding="utf-8")).get("decided"),
          "the boot is recorded in the machine-local state folder, never the hub")
    rc(w, "--boot-notice", "--boot-id", "1000060", "--state-dir", st, "--machine", "north")
    check(len(notices(w)) == 1, "the same boot (a minute's jitter in the reading) raises nothing more")
    rc(w, "--boot-notice", "--boot-id", "2000000", "--state-dir", st, "--machine", "north")
    check(len(notices(w)) == 2, "a new boot raises it once again")
    b = world("r4b")
    store(b, [task("gate-c", "Gate bypass", w=b)])
    code, out = rc(b, "--boot-notice", "--boot-id", "1000000", "--state-dir", str(b["state"]),
                   "--machine", "north")
    check(not notices(b) and "no notice" in out and (b["state"] / "routines-boot-north.json").is_file(),
          "all Bypass: silent, and the boot still recorded: %s" % out.strip())
    f = world("r4f")
    store(f, [task("gate-a", "Gate watcher one", mode=None, w=f)])
    args = ("--boot-notice", "--boot-id", "1000000", "--state-dir", str(f["state"]), "--machine", "north")
    code, out = rc(f, *args, extra={"EXO_NOTIFY_FAIL": "1"})
    check("tried again next beat" in out, "a failed notifier is tried again next beat: %s" % out.strip())
    code, out = rc(f, *args, extra={"EXO_NOTIFY_FAIL": "1"})
    check("failed twice" in out, "…and decided after two: %s" % out.strip()[:100])
    rc(f, *args)
    check(len(notices(f)) == 2, "…and never tried a third time that boot (%d)" % len(notices(f)))
    # the staged pulse calls it on its beat, after the postman, with its state folder
    pulse = source("tools/pulse.py")
    src = io.open(str(pulse), encoding="utf-8").read() if pulse.is_file() else ""
    beat = src.split("def beat(", 1)[-1]
    i_post, i_rout = beat.find("_postman(py, hub)"), beat.find("_routines_at_boot(py, hub)")
    check(0 < i_post < i_rout, "the pulse's beat calls the boot notice right after the postman")
    check('"--boot-notice", "--quiet"' in src and 'env["EXO_PULSE_STATE_DIR"]' in src,
          "…quietly, handing on its own state folder")
    # and it really runs from the pulse module, against a world
    loader_dir = str(source("tools/exo_registry.py").parent)     # read before HOME moves
    env_keep = dict(os.environ)
    try:
        for k, v in w["env"].items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        os.environ["EXO_PULSE_STATE_DIR"] = str(w["base"] / "pulse-state-2")
        import importlib.util
        sys.path.insert(0, str(pulse.parent))
        sys.path.append(loader_dir)                                    # the loader, if not staged
        spec = importlib.util.spec_from_file_location("gate_pulse", str(pulse))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        before = len(notices(w))
        lines = mod._routines_at_boot(PY, w["hub"])
        lines2 = mod._routines_at_boot(PY, w["hub"])
    finally:
        os.environ.clear()
        os.environ.update(env_keep)
    check(len(notices(w)) == before + 1 and any("notice raised" in l for l in lines),
          "the pulse's own function raises it once at a (real) boot reading: %s" % lines)
    check(lines2 == [], "…and its next beat says nothing at all")


def case_r5():
    start("R5", "Windows-true")
    w = world("r5", windows=True)
    store(w, [task("gate-a", "Gate watcher one", mode=None, w=w)])
    code, out = rc(w, extra={"PYTHONIOENCODING": "cp1252"})
    check("Traceback" not in out and "STEP: 1 routine will ask permission: Gate watcher one" in out,
          "the Windows store layout (APPDATA) is read, and a cp1252 console prints the step")
    check("Routines -> the task -> Edit" in out, "…its arrows fall back to ->")
    src = io.open(str(w["hub"] / "tools" / "routine-check.py"), encoding="utf-8").read()
    lits = [p for p in ("/tmp", "/Users/", "C:\\\\Users", "D:\\\\Projects") if p in src]
    check(not lits, "no path literal in the tool (%s)" % lits)


def main(argv):
    keep = "--keep" in argv
    print("gate-routines.py \u00B7 %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        for case in (case_r1, case_r2, case_r3, case_r4, case_r5):
            try:
                case()
            except Exception as exc:
                FAILS.append("%s: the case raised %r" % (CASE[0], exc))
                print("  [FAIL] the case raised %r" % (exc,))
    finally:
        if not keep:
            for base in WORLDS:
                shutil.rmtree(str(base), ignore_errors=True)
    total = PASSES[0] + len(FAILS)
    print("\n===== GATES =====")
    print("  %d checks \u00B7 %d passed \u00B7 %d failed" % (total, PASSES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL  %s" % f)
    if keep:
        print("  worlds kept: %s" % ", ".join(str(b) for b in WORLDS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
