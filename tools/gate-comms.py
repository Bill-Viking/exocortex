#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-comms.py — the communication gates: mail, ears, the postman and its surfaces.

    python3 tools/gate-comms.py              # every case
    python3 tools/gate-comms.py --keep       # leave the scratch worlds for inspection

HERMETIC, all of it: every case builds its own world under the temp dir — a scratch HOME whose
machine.json names a scratch hub and a scratch fleet, and a stub sync.py that records the verb it
was asked for instead of touching a repo. No real mail is sent, no real brain is pushed, no live
stamp or claim is written, and the tree is rendered through COLLECT_OPENERS_OUT.

  C1  messages leave at once (item 1 — ALREADY BUILT, verify only)
      INBOX.md is one of sync.py's SIGNAL_FILES and a just-written INBOX.md is carried by a push
      with a 60 s settling window; `mail.py --send` asks the brain to push in the same breath;
      and the brain's own last INBOX commit lists INBOX.md among its files.
  C2  arrivals announce themselves (item 2)
      i-am.py and claim.py each write ONE line to every OTHER machine's hub, in the arrival lines' own
      words; a refresh says nothing; --quiet says nothing; a fleet of one machine sends nothing;
      a three-machine fleet writes one line per other machine and none to itself.
  C3  every hub arms its mailbox (item 3)
      mail.py --watch writes ear-<machine>-<lane>.json at arming and refreshes it on every poll
      (from a Sonnet window: a watch is refused on a window whose model it cannot read);
      the tree draws the mark for a fresh ear, and says `no mailbox` for a stale one and for a
      machine with no ear at all.
  C4  one lane, either spelling
      mail.py matches `NORTH/Alpha-One` and `NORTH/Alpha/One` as one lane, and they share one ear.

  BQ63A · BQ63B · BQ63C  three checks that used to go red for a reason that was not the
      tool's: a scratch brain whose newest INBOX commit is a MERGE, and C1's own
      read proved against it both ways, with a sweep of every gate that reads the brain's
      log · the LIVE ear check narrowed to the ear names this gate's own worlds could write,
      so a live session arming its waiter never reds it · the LIVE settings check moved off
      the file's size, which the app itself rewrites, onto the postman's own hook entries.
  BQ68  a short address that fits two lanes across projects is AMBIGUOUS: the
      fleet's lane tokens read from claims, openers and stamps; nobody is delivered to, even
      when one of them holds a claim; the sender is told at once with both full tokens and
      both addresses; `hub` untouched; --status and the tree say the same why.

  P1 … P16  THE POSTMAN (phase A): tokens ·
      bootstrap · routing · identity · the hook · the waiter · observation · the sender's
      duties · pass discipline · --mark · expiry · --install-hooks · the pulse · regressions ·
      P15 permissions (a file is never left more readable than it was; POST DIR is 0700 with
      0600 files; only the brain's own files are 0644) and P16 a session id, which becomes a
      file name, checked before it is one.
      Two machines, two scratch HOMEs, two hubs and a fake sync that copies between them;
      fixture transcripts in both vendors' real shapes; no network, no real mail, claim,
      stamp, push, settings file or scheduler.

  PB15 … PB25  THE POSTMAN'S SURFACES (phase B, its cases
      P15–P24): a note for Wren's life · AGE
      from the earliest first_seen · the phone leg, carrier order and all · arm before
      idle · the nudge · the ack · the sender of a note and R3's `wake` · R4, the
      scratch-hub leak · R1 and R2 · the Windows leg as far as a North can prove it · and
      tree_facts. They are numbered P15–P24 there; phase A already has a P15 and a P16,
      both green and untouched, so they are PB15…PB25 here and each says which it is.
      NO CHECK HERE EVER RAISES A REAL NOTIFICATION OR MAKES A REAL PUSH: the notifier's
      seam is on the flag AND in every world's environment, so even a pass a tool starts
      as a child of its own cannot reach the desktop.

  QW-G1 … QW-G11  NOTHING WAITS ON FABLE, AN FYI LETTER NEVER WAKES A WINDOW:
      rails · R1 the model read from the window's own
      transcript · R2 the context ceiling · --force · R3 the quiet letters · R4 the hygiene queue
      letter at the Desk · R5 the Stop hook's Desk line · the settings file · scrub · R7 routines
      (Claude and OpenAI). `--only QW` runs just these (and LIVE); `--skill <SKILL.md>` points G6 at
      a staged SKILL.md instead of the installed one.

  QW-W1 … QW-W4  THE FLOOR ROAD OBEYS THE SAME RULE: `mail.py --watch` asks --wait's own
      refuse_or_arm question before it loops · W1 a Fable window's watch is refused in one line, exit
      0, logged, no ear · W2 a Sonnet window's watch prints ONE `MAIL for` for an asking letter and
      swallows three FYI lines, counted in the ear's `quiet` · W3 --force arms a Fable window's watch,
      logged `forced` · W4 no postman beside mail.py: refused, never armed blind. Part of `--only QW`.

  FD1 … FD8  A QUIET WINDOW NEVER HIDES A LETTER: an ATTENDED
      window (the app's fronted one, a transcript that moved in ten minutes, a remote-control
      hint) is pushed at once by ONE send order a carrier's own turn makes — never the target,
      never a routine run; a busy window's own hook carries what asks and the push carries only
      the quiet lines; an IDLE window is queued AND announced at once — one desktop notice, the
      plain text, the count, a ✉ N mark on its LIVE line; a Fable window is never woken, and
      attended is the only exception; nothing older than the road itself is pushed or announced.
      `--only FD` runs just these (and LIVE).

  FD9  REMOTE CONTROL, WRITTEN BY THE TOOL: `postman.py --remote-hint <id> …` writes POST
      DIR's remote-control.json whole — `written` now, `sessions` exactly the ids given, the app's
      local_ id or the transcript's own id — and a fresh one makes a quiet window attended by
      `remote`; no ids writes an empty list and the window is idle again; a hint older than
      REMOTE_FRESH_S (written with --now) is not believed; an id that is not a plain token writes
      nothing, exit 2.
  FD10 · FD11  ATTENDED DOES NOT MEAN AFFORDABLE: under a usage PAUSE that reaches the
      window's model the attended road is HELD — no send order anywhere, the letter queued for its
      next turn, one zero-token notice, the ✉ mark, and `--send` says `not pushed into «…» — held:
      usage PAUSE (<meter>)`; a Fable-week PAUSE leaves a Sonnet window's push as it is and holds a
      Fable window's; an order queued before the PAUSE and not yet carried is taken back out of its
      carrier's file, one already handed is said as sent, and when the PAUSE lifts a fresh order
      goes out. Part of `--only FD`.

  BQ307-M1 … M10 · MH OLD MAIL STOPS RINGING ( extended,
      the contract): the INBOX stamp is delivery, seen through the
      seam even under the offset · a new window is handed 10 letters, not 300, and told it was
      spared 290 · a broadcast reaches only the lanes live that day · an alarm past its reset or
      superseded never rings · a waiter ends only on today's mail, both roads · an FYI letter
      never rides send_message, and a retitle is not a turn · a lane's own --read is its
      delivery · the no-mail hook is still one stat · first seen is never later than the
      letter's own date. Worlds in the system temp folder as exo-prove-comms-<pid>-<name>;
      `--only OM` runs just these (and LIVE). FD1 · FD2 · FD3 follow M-F: the FYI line is
      never pushed.

  BQ205-G1 · G2 · G3  A MACHINE'S BROADCAST STAYS ON ITS MACHINE, AND ON ITS LOGIN:
      a SOUTH lane's addressed / undelivered / --read never take NORTH/all
      or NORTH/<the same lane> · an alarm naming login A fans out to A's live lane and to a lane
      whose login is unknown (no owner on its transcript, or no transcript at all — the
      terminal's login never stands in), NOT to a lane whose transcript's owner is B, and the
      pass counts `1 other-login` · with no usage.py beside the postman nothing is withheld · a
      broadcast that is not an alarm ignores logins. `--only B205` runs just these (and LIVE).

  DL1 … DL10 THE DIAL PLATE IS AN ORDER THE POSTMAN CARRIES (,
      the contract): a ⇩ plate in a quiet ACT window becomes ONE
      dial order on one other attended Claude window, aimed at the app's own id · a ⇧ to the
      flagship past warn is kept, the plate stands · one plate, one order; a new reply's plate,
      a new one · a window with no plate is never walked · an unreadable plate is named once ·
      no other Claude window: no-carrier, no wake · a busy window waits a pass · applied → the
      window's own next prompt opens `dial set: …`, never a PostToolBatch or a Stop, and the
      no-mail hook is still one stat (SessionStart learns the app id once) · an order
      nobody takes expires and is judged again once · a routine's run or a Codex thread is
      never the hand. The pass runs the real judge, spool.py --dials --plates-only, as a child.
      Worlds in the system temp folder as exo-prove-comms-286-<pid>-<name>; `--only DL` runs
      just these (and LIVE).

  BQ337-C1 … C5  A LETTER ABOUT A FAILURE DIES WITH THE FAILURE:
      a resolved failed-push letter is hidden by --read (one line says so, --all shows it), never
      an ask, never carried by a waiter, expired by the pass with its send order taken back · an
      alarm about another login's meter than the app's, or one the meter has since answered, does
      not ring · a flagship window is never the carrier, and with only flagships live there is no
      order · an order never ends a wait, and rides the carrier's next turn · no order for a letter
      the window has been handed or has seen. `--only B337` runs just these (and LIVE).

Stdlib only, Python 3.9, OS-neutral. Exit 0 only when every check passes.
"""
import datetime
import importlib.util
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
# The machine's own record never reaches a fixture — not in a child, and not in
# this process either, where the postman and mail are loaded and asked about a
# world by its home: a record this machine names outright (EXO_MACHINE_JSON)
# would answer for every world instead. Each world names its own (w["env"]).
os.environ.pop("EXO_MACHINE_JSON", None)
HUB = HERE.parent
ROOT = Path(tempfile.gettempdir()) / "exocortex-gate-comms"
PY = sys.executable or "python3"
BRAIN = Path.home() / "orchestrator-sync"

FAILS, PASSES, SKIPS = [], 0, []
LOADS = []                       # timing checks over their ceiling on a machine over its CPU count — not judged
CPUS = os.cpu_count() or 1
TIMED_K = 5                      # a timing ceiling is K × this run's own interpreter start (measured: DONE.md)
_INTERP = []                     # the run's interpreter baseline, measured once, lazily
CASE = {"id": "", "name": ""}
WORLDS = []

# The tools this gate proves, and what each needs beside it to run from a copy.
# `exo_registry.py` is here because every one of the others reads the person's
# own names through it, from their first line: a world that copies the tools
# and not the loader gives them a ModuleNotFoundError before they run.
# `exo_paths.py` beside it for the same reason: the tools read the machine record,
# the sync package and the brain through the resolver, from their first line.
TOOLS = ("mail.py", "i-am.py", "claim.py", "postman.py", "exo_common.py",
         "exo_registry.py", "exo_paths.py", "app_sessions.py")
TREE_TOOLS = ("collect-openers.py", "opener_carriers.py", "exo_common.py", "grok_sessions.py")
# A tool the collector imports under a guard: an install without it draws the
# folder's openers alone, and a world built for such an install goes without.
OPTIONAL_TOOLS = ("opener_carriers.py", "exo_paths.py",   # the resolver: not on a hub from before it
                  "app_sessions.py")                        # the app's store reader: not on a hub from before it

# The registry every world's hub is given: invented names only. The owner the
# checks name, the two machines of the fleet the fixtures play (one macOS, one
# Windows), the minds with one persona for the Codex side, and nothing else.
FIXTURE_REGISTRY = {
    "version": 1,
    "note": "gate-comms' own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {
        "north": {"label": "North", "mark": "\u25cf", "os": "macos",
                  "hue": {"light": "#2456a4", "dark": "#7fb0e8"}},
        "south": {"label": "South", "mark": "\u258e", "os": "windows",
                  "hue": {"light": "#9a6b3a", "dark": "#d4a373"}},
    },
    "minds": [
        {"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
        {"name": "OPUS", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#6f42ad", "dark": "#a78bfa"}},
        {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#0f766e", "dark": "#2dd4bf"}},
        {"name": "HAIKU", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#64748b", "dark": "#9fb3c8"}},
        {"name": "NOBODY", "vendor": "OpenAI", "kind": "codex", "show": True,
         "hue": {"light": "#be185d", "dark": "#f0a0c0"}},
        {"name": "GROK", "vendor": "xAI", "kind": "grok", "show": False,
         "hue": {"light": "#4a6c00", "dark": "#9cc450"}},
        {"name": "CLAUDE", "vendor": "", "kind": "claude", "show": False,
         "hue": {"light": "#39518a", "dark": "#8fb4ff"}},
    ],
    "mind_aliases": {"CODEX": "NOBODY", "GPT": "NOBODY"},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Exocortex"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}


def real_hub():
    """The hub machine.json names — where a tool this gate needs but does not sit
    beside can still be found."""
    try:
        with io.open(str(Path.home() / "orchestrator-sync" / "machine.json"), encoding="utf-8") as fh:
            root = (json.load(fh).get("roots") or {}).get("orchestrator")
        return Path(root) if root else HUB
    except Exception:
        return HUB


def source_tool(name):
    """A tool's source, whichever LAYOUT this gate is running from: beside itself
    (a build folder) or inside a hub's tools/.  Three earlier builds failed here,
    so the gate resolves BY EXISTENCE and never by where it happens to sit."""
    here = HERE / name
    if here.is_file():
        return here
    return real_hub() / "tools" / name


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def start(case_id, name):
    global CASE
    CASE = {"id": case_id, "name": name}
    print("\n======== %s — %s ========" % (case_id, name))


def check(cond, msg):
    global PASSES
    if cond:
        PASSES += 1
        print("  [PASS] %s" % msg)
    else:
        FAILS.append("%s: %s" % (CASE["id"], msg))
        print("  [FAIL] %s" % msg)
    return bool(cond)


def skip(msg):
    SKIPS.append("%s: %s" % (CASE["id"], msg))
    print("  [SKIP] %s" % msg)


def load_now():
    """The 1-minute load average, or None where the platform has none (Windows)."""
    try:
        return float(os.getloadavg()[0])
    except (AttributeError, OSError):
        return None


def interp_ms():
    """THIS RUN'S interpreter start, in ms — the mean of 20 bare imports through the same
    subprocess road and env shape hook() uses. Measured once, where it is first needed, so a
    timing ceiling moves with the machine's own speed instead of an absolute number."""
    if not _INTERP:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        t0 = time.time()
        for _ in range(20):
            subprocess.run([PY, "-c", "import json, os, sys, re, io, datetime, pathlib"],
                           input="", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, env=env, timeout=60)
        _INTERP.append((time.time() - t0) / 20.0 * 1000)
        print("  i  interpreter baseline: %.0f ms mean" % _INTERP[0])
    return _INTERP[0]


def check_timed(ms, msg):
    """A timing check judged against this run's own interpreter, never an absolute number:
    ceiling = max(250 ms, K × the baseline). Over it on a machine whose load is over its CPU
    count, it is [LOAD] — not judged, counted, neither a pass nor a fail; over it on a machine
    that is not busy (or one that cannot say), it is a FAIL as before."""
    base = interp_ms()
    ceiling = max(250.0, TIMED_K * base)
    text = "%s · %.0f ms mean · interpreter %.0f · ceiling %.0f" % (msg, ms, base, ceiling)
    if ms < ceiling:
        return check(True, text)
    load = load_now()
    if load is not None and load > CPUS:
        LOADS.append("%s: %s" % (CASE["id"], text))
        print("  [LOAD] %s · load %.1f over %d CPUs — not judged" % (text, load, CPUS))
        return None
    return check(False, text)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(path), "w", encoding="utf-8", newline="\n").write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def run(args, cwd=None, env=None, timeout=300):
    base = dict(os.environ)
    base["PYTHONUTF8"] = "1"
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    base["GIT_TERMINAL_PROMPT"] = "0"
    for key, value in (env or {}).items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = str(value)
    try:
        proc = subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None, env=base,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                              universal_newlines=True, encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ss" % timeout
    except Exception as exc:
        return 125, repr(exc)


def iso(when):
    return when.replace(microsecond=0).isoformat()


# The stub brain: a sync.py that writes down the verb it was asked for and
# touches nothing. Every world gets one, so a push is proved without a push.
SYNC_STUB = (
    "import io, sys, os\n"
    "log = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync-calls.log')\n"
    "io.open(log, 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + '\\n')\n"
)

# THE NOTIFIER'S SEAM (phase B). It stands in for osascript and for the
# Windows toast, and it records the exact texts it was handed. EVERY world gets
# one, in the ENVIRONMENT as well as on the flag, because `mail.py --send` runs
# a pass of its own as a child: without EXO_NOTIFY that child could raise a real
# banner on the build machine behind the gate's back. NO CHECK IN THIS FILE EVER
# RAISES A REAL NOTIFICATION.
NOTIFY_SEAM = (
    "import io, json, os, sys\n"
    "rec = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notify-calls.jsonl')\n"
    "row = {'argv': sys.argv[1:],\n"
    "       'env': dict((k, v) for k, v in os.environ.items() if k.startswith('EXO_NOTE_'))}\n"
    "io.open(rec, 'a', encoding='utf-8').write(json.dumps(row, ensure_ascii=False) + '\\n')\n"
    "sys.exit(int(os.environ.get('EXO_NOTIFY_FAIL') or 0))\n"
)

# A driver that counts every os.stat the hook's own code path makes — the hot
# path's budget is a real seam and not a claim.
STAT_COUNTER = (
    "import importlib.util, os, sys\n"
    "spec = importlib.util.spec_from_file_location('pm', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "seen = [0]\n"
    "real = os.stat\n"
    "def counted(*a, **k):\n"
    "    seen[0] += 1\n"
    "    return real(*a, **k)\n"
    "os.stat = counted\n"
    "code = mod.hook_main(['--hook', '--vendor', 'claude', '--post-dir', sys.argv[2]])\n"
    "sys.stderr.write('STATS=%d\\n' % seen[0])\n"
    "sys.exit(code)\n"
)


# A driver that runs mail.py's OWN `wait()` with ONE named constant overridden
# in its own process — how long "a waiter that LIVED" means for this run.
# Nothing else is patched and the gate's own process is untouched,
# so the case proves the real exit path instead of the clock.
WAIT_DRIVER = (
    "import importlib.util, sys\n"
    "from pathlib import Path\n"
    "spec = importlib.util.spec_from_file_location('m', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "mod.ALIVE_LIVED_S = float(sys.argv[2])\n"
    "mod.HUB = Path(sys.argv[3])\n"
    "mod.INBOX = mod.HUB / 'INBOX.md'\n"
    "sys.exit(mod.wait(sys.argv[4], title=None, max_hours=float(sys.argv[5]),\n"
    "                  hub=sys.argv[3], poll=0.5))\n"
)

# A driver that renders the two commands under a FORCED sys.executable, in its
# own process — the South's `pythonw` cannot be stood up on a North any other way.
# It sets only the child's own interpreter path.
PY_RENDER = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('pm', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "sys.executable = sys.argv[2]\n"
    "print(json.dumps({'py': mod.console_python(),\n"
    "                  'wait': mod.wait_command(sys.argv[3], 'SOUTH/hub', sys.argv[5]),\n"
    "                  'hook': mod.hook_command(sys.argv[3], sys.argv[4], 'claude')}))\n"
)


# A PASS WITH NO SEAM AT ALL, on a machine whose notifier the postman does not
# know. It is the one SAFE way to read main()'s own `foreign_hub` decision: the
# rehearsal guard stands down whenever a seam is set (judgment call 6), and with
# `os_kind` → "other" raise_note renders an EMPTY argv and starts NO PROCESS,
# answering `none · this machine has no notifier the postman knows`. So the two
# outcomes — "a rehearsal never raises" and "no notifier here" — tell the flag
# apart without a banner ever being possible.
NO_NOTIFIER_PASS = (
    "import importlib.util, os, sys\n"
    "os.environ.pop('EXO_NOTIFY', None)\n"
    "spec = importlib.util.spec_from_file_location('pm', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "mod.os_kind = lambda override=None: 'other'\n"
    "sys.exit(mod.main(sys.argv[2:]))\n"
)

# tree_facts() as the PAGE GENERATOR calls it, in a process whose HOME is the
# world's — so `is_own_hub` answers from the world's machine.json and not from
# the machine the gate is running on.
TREE_FACTS = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('pm', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "print(json.dumps(mod.tree_facts(sys.argv[2])))\n"
)


def raises(w):
    """Every notification the seam was asked to raise, in order."""
    path = w["base"] / "notify-calls.jsonl"
    if not path.is_file():
        return []
    return [json.loads(l) for l in io.open(str(path), encoding="utf-8").read().splitlines()
            if l.strip()]


REGISTRY_FILE = ROOT / ("registry-%d.json" % os.getpid())


def fixture_registry_file():
    """The same registry, named outright for this process and its children: a
    tool loaded HERE (the postman, mail — asked about a world by its home) reads
    the registry through the resolver, and the resolver would answer from this
    machine's own record rather than the world's."""
    if not REGISTRY_FILE.is_file():
        write_json(REGISTRY_FILE, FIXTURE_REGISTRY)
    os.environ["EXO_REGISTRY_JSON"] = str(REGISTRY_FILE)
    return REGISTRY_FILE


def world(name, fleet=("north", "south"), machine="north", tree=False, base_dir=None):
    """A scratch world: HOME/orchestrator-sync/{machine.json, sync-manifest.json,
    sync.py stub} and a hub folder holding a copy of the tools under test.  `base_dir`
    names the world's folder outright ."""
    base = Path(base_dir) if base_dir else ROOT / ("%s-%d" % (name, os.getpid()))
    shutil.rmtree(str(base), ignore_errors=True)
    home, hub, projects, out = base / "home", base / "hub", base / "projects", base / "out"
    post = base / "post"
    for folder in (home / "orchestrator-sync", hub / "tools", projects, out, post):
        folder.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(post), 0o700)      # as the tool makes it in service, so a world
    except OSError:                     # the gate builds by hand is not a false alarm
        pass
    # A WORLD IS AN INSTALLED MACHINE.
    # `--install-hooks` writes `installed.json` into POST DIR, and without it a
    # pass raises nothing, pushes nothing and nudges nothing — so every case
    # that proves a surface needs the word to have been said here. The three
    # cases that prove the marker's absence remove it again, and PB15j proves the lifecycle.
    write_json(post / "installed.json",
               {"when": iso(datetime.datetime.now().astimezone()),
                "vendors": ["claude"], "hub": str(hub)})
    try:
        os.chmod(str(post / "installed.json"), 0o600)   # as the tool writes it
    except OSError:
        pass
    for tool in TOOLS + (TREE_TOOLS if tree else ()):
        source = source_tool(tool)
        if tool in OPTIONAL_TOOLS and not source.is_file():
            continue            # the collector reads the folder's openers alone without it
        shutil.copy2(str(source), str(hub / "tools" / tool))
    # The gate's own registry: every name its fixtures and checks use, and
    # nobody's real ones — the same proof on any machine, whatever that
    # machine's own registry names.
    write_json(hub / "registry.json", FIXTURE_REGISTRY)
    fixture_registry_file()
    write_json(home / "orchestrator-sync" / "machine.json",
               {"name": machine, "os": platform.system(),
                "roots": {"orchestrator": str(hub), "projects": str(projects),
                          "claude": str(home / ".claude"), "codex": str(home / ".codex"),
                          "post": str(post)}})
    write_json(home / "orchestrator-sync" / "sync-manifest.json",
               {"machines": dict((m, {}) for m in fleet)})
    write(home / "orchestrator-sync" / "sync.py", SYNC_STUB)
    write(base / "notify.py", NOTIFY_SEAM)
    write(base / "statcount.py", STAT_COUNTER)
    write(base / "waitdrv.py", WAIT_DRIVER)
    write(base / "pyrender.py", PY_RENDER)
    write(base / "treefacts.py", TREE_FACTS)
    write(base / "nonotify.py", NO_NOTIFIER_PASS)
    w = {"base": base, "home": home, "hub": hub, "projects": projects, "out": out,
         "post": post, "machine": machine, "notify": base / "notify.py",
         # The gate itself runs INSIDE a session whose environment names it. Cleared
         # here, always, or every stamp and claim in every world would record the
         # gate's own session id and no case could prove what happens without one.
         "env": {"HOME": str(home), "USERPROFILE": str(home),
                 "HOMEDRIVE": None, "HOMEPATH": None,
                 # the world's own record, named outright: a record this machine
                 # names (EXO_MACHINE_JSON) never reaches a fixture, and a tool that
                 # reads it through the resolver reads the world's
                 "EXO_MACHINE_JSON": str(home / "orchestrator-sync" / "machine.json"),
                 "CLAUDE_CODE_SESSION_ID": None, "CLAUDE_CODE_HOST_SESSION_ID": None,
                 # the notifier's seam, inherited by every child a tool starts
                 "EXO_NOTIFY": str(base / "notify.py"), "EXO_NOTIFY_FAIL": None}}
    WORLDS.append(w)
    return w


def tool(w, name, *args):
    return run([PY, str(w["hub"] / "tools" / name)] + list(args), cwd=str(w["hub"]), env=w["env"])


def inbox_lines(w):
    path = w["hub"] / "INBOX.md"
    if not path.is_file():
        return []
    return [l for l in io.open(str(path), encoding="utf-8").read().splitlines() if l.startswith("- ")]


def fields(line):
    """One INBOX line read the way its reader does: date · to · target · TEXT · action.
    The text itself carries "·" (the arrival lines do), so everything
    between the target and the last field is the text."""
    f = [x.strip() for x in line[2:].split(" · ")]
    while len(f) < 5:
        f.append("")
    return [f[0], f[1], f[2], " · ".join(f[3:-1]), f[-1]]


def load_mail(w):
    """mail.py from the world's own hub, imported for its readers."""
    spec = importlib.util.spec_from_file_location("gate_mail", str(w["hub"] / "tools" / "mail.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# C1 — messages leave the moment they are written (item 1: verify only)
# --------------------------------------------------------------------------

# A MERGE COMMIT MUST NEVER READ AS AN EMPTY CHANGE.  The two machines
# merge every day, so the newest commit that changed INBOX.md on this machine's
# own line is regularly a merge — and a merge's diff is OFF by default, so
# `--name-only` printed nothing and C1 went red for a reason that was not the
# tool's.  `--diff-merges=first-parent` gives a merge its first-parent diff, and
# `--first-parent` keeps the walk on this machine's own line so the commit
# selected is the one that really carried the change.  Measured on a real
# brain: the diff-merges flag ALONE picks the merge and still
# prints no name (red); the two together name `orchestrator/INBOX.md`.  BQ63A
# builds that shape from nothing and proves both readings.
MERGE_SAFE = ("--first-parent", "--diff-merges=first-parent")
# The one line in this file that reads the brain's log WITHOUT the flags, on
# purpose, so BQ63A can show what they are for.  The sweep below reads this file
# and must never count it as a defect, so it is marked — once, and the case
# checks that it is once.
CONTROL_MARK = "flagless on purpose (BQ63A control)"


def inbox_commit_names(repo, merge_safe=True, env=None):
    """THE ONE READ of the brain's newest commit touching INBOX.md — C1's, and
    the fixture's, so what the gate proves is what the gate runs.

    BOTH FORMS ARE SPELLED OUT WHOLE.  The sweep in BQ63A reads this very file,
    and a command assembled out of a constant and an `if` is a command it cannot
    judge: the flags would sit four lines away from the read, in a name.  The
    cost is one repeated line; the gain is that the scan sees what git sees."""
    if merge_safe:
        args = ["git", "-C", str(repo), "log", "-1", "--name-only",
                "--first-parent", "--diff-merges=first-parent",
                "--format=%h %cI", "--", "orchestrator/INBOX.md"]
    else:
        args = ["git", "-C", str(repo), "log", "-1", "--name-only",
                "--format=%h %cI", "--", "orchestrator/INBOX.md"]  # flagless on purpose (BQ63A control)
    return run(args, env=env, timeout=120)


def case_c1():
    start("C1", "messages leave the moment they are written (item 1 — verify only)")
    sync_py = BRAIN / "sync.py"
    if sync_py.is_file():
        spec = importlib.util.spec_from_file_location("gate_sync", str(sync_py))
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:
            mod = None
            skip("sync.py would not import (%r) — the signal check could not run" % exc)
        if mod is not None:
            check("INBOX.md" in tuple(getattr(mod, "SIGNAL_FILES", ())),
                  "INBOX.md is one of sync.py's SIGNAL_FILES")
            check(mod.is_signal("orchestrator/INBOX.md"),
                  "is_signal() says orchestrator/INBOX.md is a signal at any depth")
            now = time.time()
            carry, waiting = mod.select_for_push(
                [("orchestrator/INBOX.md", now), ("orchestrator/board.html", now)], now, 60)
            check("orchestrator/INBOX.md" in carry,
                  "a push with a 60 s settling window carries an INBOX.md written this second")
            check("orchestrator/board.html" in waiting,
                  "…while an ordinary file written this second waits, so the window is really on")
    else:
        skip("no sync.py at %s — the settling checks could not run" % sync_py)

    w = world("c1")
    code, out = tool(w, "mail.py", "--send", "SOUTH/hub", "Exocortex", "the gate's own letter",
                     "no reply needed — FYI")
    check(code == 0, "mail.py --send exited 0")
    check(len(inbox_lines(w)) == 1, "the letter is in INBOX.md the moment it is written")
    calls = w["home"] / "orchestrator-sync" / "sync-calls.log"
    called = io.open(str(calls), encoding="utf-8").read().split() if calls.is_file() else []
    check("push" in called, "--send asked the brain to push in the same breath (stub sync.py saw %r)"
          % (" ".join(called) or "nothing"))
    check("push: ok" in out, "…and said so in one line")

    if (BRAIN / ".git").is_dir():
        code, out = inbox_commit_names(BRAIN)
        check(code == 0 and "orchestrator/INBOX.md" in out,
              "the brain's last INBOX commit lists INBOX.md among its files: %s"
              % " ".join(out.split()[:2]))
    else:
        skip("no brain repo at %s — the git-log half of the owed case could not run" % BRAIN)


# --------------------------------------------------------------------------
# C2 — arrivals announce themselves (item 2)
# --------------------------------------------------------------------------

TITLE = "ACT — Exocortex/hub: the gate's own sitting"


def only_line(w, why):
    rows = inbox_lines(w)
    if not check(len(rows) == 1, "%s — exactly one line was written (found %d)" % (why, len(rows))):
        for r in rows:
            print("       %s" % r)
        return None
    return rows[0]


def case_c2():
    start("C2", "arrivals announce themselves (item 2)")
    w = world("c2")

    code, out = tool(w, "i-am.py", "FABLE", "EXTRA", TITLE)
    check(code == 0, "i-am.py exited 0")
    line = only_line(w, "a stamp")
    if line:
        f = fields(line)
        check(f[1] == "to: SOUTH/hub", "it is addressed to the OTHER machine's hub: %s" % f[1])
        check(re.match(r"^NORTH FABLE woke at \d\d:\d\d · \"%s\" · effort EXTRA$" % re.escape(TITLE), f[3]),
              "the line is the docket's own: %s" % f[3])
        check(f[4] == "no reply needed — FYI", "the action is `no reply needed — FYI`")
    check("announced to SOUTH/hub" in out, "i-am.py says in one line where the letter went")

    tool(w, "i-am.py", "FABLE", "EXTRA", TITLE)
    check(len(inbox_lines(w)) == 1, "re-stamping the same title says nothing — a refresh is not an arrival")

    code, out = tool(w, "claim.py", "--claim", "hub", TITLE)
    check(code == 0, "claim.py --claim exited 0")
    rows = inbox_lines(w)
    if check(len(rows) == 2, "taking the pen writes exactly one more line (found %d)" % len(rows)):
        f = fields(rows[1])
        check(f[1] == "to: SOUTH/hub", "addressed to the other machine's hub")
        check(f[3] == "NORTH FABLE took the hub pen · \"%s\"" % TITLE,
              "the line is the docket's own: %s" % f[3])

    code, _ = tool(w, "claim.py", "--release", "hub", TITLE)
    rows = inbox_lines(w)
    if check(code == 0 and len(rows) == 3, "releasing the pen writes one more line"):
        check(fields(rows[2])[3] == "NORTH FABLE released the hub pen · \"%s\"" % TITLE,
              "the matching released line: %s" % fields(rows[2])[3])

    code, _ = tool(w, "i-am.py", "--off", "FABLE", TITLE)
    rows = inbox_lines(w)
    if check(code == 0 and len(rows) == 4, "signing off writes one more line"):
        check(re.match(r"^NORTH FABLE signed off at \d\d:\d\d · \"%s\"$" % re.escape(TITLE),
                       fields(rows[3])[3]),
              "the matching signed-off line: %s" % fields(rows[3])[3])

    calls = w["home"] / "orchestrator-sync" / "sync-calls.log"
    check(calls.is_file() and calls.read_text(encoding="utf-8").split().count("push") == 4,
          "each of the four lines asked the brain to push, and none of them twice")

    # --quiet: the gate runs of every other tool must stay silent
    q = world("c2-quiet")
    tool(q, "i-am.py", "OPUS", "EXTRA", TITLE, "--quiet")
    tool(q, "claim.py", "--claim", "hub", TITLE, "--quiet")
    tool(q, "claim.py", "--release", "hub", TITLE, "--quiet")
    tool(q, "i-am.py", "--off", "OPUS", TITLE, "--quiet")
    check(not (q["hub"] / "INBOX.md").exists(),
          "--quiet writes no INBOX.md at all — a gate run tells nobody")
    check((q["hub"] / "live-north-opus.json").is_file() and (q["hub"] / "claims.json").is_file(),
          "…and the stamp and the claim were still written")

    # a fleet of one machine sends nothing
    s = world("c2-solo", fleet=("solo",), machine="solo")
    code, out = tool(s, "i-am.py", "FABLE", "EXTRA", TITLE)
    check(code == 0 and not (s["hub"] / "INBOX.md").exists(),
          "a fleet of one machine writes no line at all")
    check("announced to nobody — this fleet has one machine" in out,
          "…and says so in plain words")

    # three machines: one line each, none to itself
    t = world("c2-three", fleet=("north", "south", "elsewhere"), machine="north")
    tool(t, "i-am.py", "FABLE", "EXTRA", TITLE)
    rows = inbox_lines(t)
    tos = sorted(fields(r)[1] for r in rows)
    check(tos == sorted(["to: SOUTH/hub", "to: ELSEWHERE/hub"]),
          "a three-machine fleet writes one line per OTHER machine and none to itself: %s" % tos)


# --------------------------------------------------------------------------
# C3 — every hub arms its mailbox (item 3)
# --------------------------------------------------------------------------

def ear_path(w, to):
    """The world's ear file for an address — one spelling for watch_once and armed()."""
    return w["hub"] / ("ear-%s.json" % re.sub(r"[^a-z0-9]+", "-", to.lower()).strip("-"))


def armed(w, to, timeout=60.0):
    """THE ARM MARK. A waiter writes its ear only after it has taken its snapshot of the
    inbox (mail.py wait(): snapshot, ear, arm line), so the ear existing IS "armed" — a letter
    written after it is new mail by construction. Replaces a sleep that guessed how long an
    interpreter takes to start. Returns the seconds it took; None, said as a failed check, past
    `timeout`, so the case's later checks still run and say what they can."""
    began = time.time()
    path = ear_path(w, to)
    while time.time() - began < timeout:
        if path.is_file():
            return time.time() - began
        time.sleep(0.05)
    check(False, "the waiter never armed within %g s" % timeout)
    return None


def drop_ear(w, to):
    """Remove the ear a dead waiter left, so the next armed() reads THIS waiter's, not that one's."""
    try:
        ear_path(w, to).unlink()
    except OSError:
        pass


def watch_once(w, to, every, title, polls=1):
    """Arm a watch, let it poll once, stop it. Returns the ear's two `when`s.
    polls=0: stop it the moment its ear exists and return the ear twice — the
    tool's own fresh ear, written at arm with `every`, with no wait for a second poll.

    A watch asks --wait's refusal first, so it is armed from a WINDOW —
    a Sonnet transcript carrying the title, the session's id in its environment —
    exactly as every --wait fixture here already is. Without one it is refused
    (never armed blind), which is QW-W4's subject, not this case's."""
    qw_window(w, QW_SID_D, QW_SONNET, title=title)
    env = dict((k, v) for k, v in os.environ.items() if k not in w["env"])
    env.update((k, str(v)) for k, v in w["env"].items() if v is not None)
    env.update(as_session(QW_SID_D))
    proc = subprocess.Popen(
        [PY, str(w["hub"] / "tools" / "mail.py"), "--watch", to, "--every", str(every),
         "--title", title, "--no-pull"],
        cwd=str(w["hub"]), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    path = ear_path(w, to)
    first = None
    try:
        for _ in range(1200):                     # armed at once, not one poll from now (60 s: a loaded start)
            if path.is_file():
                try:
                    ear = json.loads(io.open(str(path), encoding="utf-8").read())
                except Exception:
                    ear = None
                if ear and ear.get("every") == every:     # THIS watch's ear, not a dead one's with the same name
                    first = ear
                    break
            time.sleep(0.05)
        second = first
        deadline = time.time() + every * 3 + 5 if polls else 0
        while time.time() < deadline:
            time.sleep(0.2)
            try:
                now = json.loads(io.open(str(path), encoding="utf-8").read())
            except Exception:
                continue
            if first and now.get("when") != first.get("when"):
                second = now
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    return first, second


def render(w, out_name="tree.html"):
    out_path = w["out"] / out_name
    env = dict(w["env"])
    env.update({"COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_OUT": str(out_path),
                "COLLECT_OPENERS_VOLUMES": str(w["base"] / "vol"),
                "COLLECT_OPENERS_WORK": str(w["base"] / "work"),
                "COLLECT_OPENERS_ENGINE": str(w["home"] / "orchestrator-sync")})
    code, out = run([PY, str(w["hub"] / "tools" / "collect-openers.py"), "--html"],
                    cwd=str(w["hub"]), env=env, timeout=600)
    if code != 0:
        raise RuntimeError("--html exited %d: %s" % (code, out[-800:]))
    return io.open(str(out_path), encoding="utf-8").read()


def root_card(html, machine):
    """The one machine root's own card: from the <div that carries its data-mch
    to that div's close."""
    spot = html.find('data-mch="%s"' % str(machine).upper())   # the card names its machine in caps
    if spot < 0:
        return ""
    start_at = html.rfind("<div", 0, spot)
    end_at = html.find("</div>", spot)
    return html[start_at:end_at + 6] if start_at >= 0 and end_at > 0 else ""


def case_c3():
    start("C3", "every hub arms its mailbox (item 3)")
    w = world("c3", tree=True)
    write(w["hub"] / "STATUS.md", "# STATUS\n\n## Now\n\nThe gate's hub.\n\n## To do\n\n- [ ] one item\n")
    write(w["hub"] / "TREE.md", "<!-- tree:auto-start -->\n<!-- tree:auto-end -->\n")

    first, second = watch_once(w, "NORTH/hub", 1, TITLE)
    # the 1-second watch above is judged stale 2 s after it dies — a render on a loaded
    # machine races that. Arm a real watch at the tree's own 150 s and stop it at its ear: a
    # fresh ear for 300 s, whatever the load, overwriting the 1-second one.
    watch_once(w, "NORTH/hub", 150, TITLE, polls=0)
    if check(bool(first), "the ear is written the moment the watch is armed, not one poll later"):
        check(first.get("title") == TITLE, "it carries the session's title: %r" % first.get("title"))
        check(first.get("every") == 1, "…the poll interval: %r" % first.get("every"))
        check(bool(first.get("when")), "…and when it last looked: %r" % first.get("when"))
        check(first.get("machine") == "north" and first.get("lane") == "hub",
              "the file is named for the machine and the lane it watches")
    check(bool(second) and second.get("when") != first.get("when"),
          "every poll refreshes it, so the file's own age is the proof it is still listening")

    # the Codex side has no Monitor: it reads at every turn start, and that read
    # is the same mailbox. A read by NO session claims nothing.
    r = world("c3-read")
    write(r["hub"] / "INBOX.md", "# INBOX\n")
    tool(r, "mail.py", "--read", "NORTH/hub")
    check(not list(r["hub"].glob("ear-*.json")),
          "a bare --read claims no mailbox — an ear is a session saying it is listening")
    tool(r, "mail.py", "--read", "NORTH/hub", "--title", TITLE)
    ear = r["hub"] / "ear-north-hub.json"
    if check(ear.is_file(), "a --read WITH a session title writes the same ear (the Codex hub's way)"):
        body = json.loads(io.open(str(ear), encoding="utf-8").read())
        check(body.get("how") == "read" and body.get("title") == TITLE,
              "…and the ear says how it is held: %r" % body.get("how"))

    # the other machine has no ear at all
    write_json(w["hub"] / "live-south-fable.json",
               {"machine": "south", "mind": "FABLE", "when": iso(datetime.datetime.now().astimezone()),
                "sessions": [{"title": "the other machine's session", "effort": "EXTRA",
                              "when": iso(datetime.datetime.now().astimezone())}]})
    html = render(w)
    north, south = root_card(html, "north"), root_card(html, "south")
    check("◗ mailbox" in north, "the tree draws the mark on a machine whose hub ear is fresh")
    check("no mailbox" not in north, "…and does not also call it no mailbox")
    check("no mailbox" in south and "◗ mailbox" not in south,
          "a machine with no ear at all says `no mailbox` in plain words")
    marks = re.search(r'<script type="application/json" id="marks">(.*?)</script>', html, re.S)
    entries = json.loads(marks.group(1)) if marks else {}
    north_rows = dict((r[0], r[1]) for r in (entries.get("root:north") or {}).get("bytes") or [])
    south_rows = dict((r[0], r[1]) for r in (entries.get("root:south") or {}).get("bytes") or [])
    check("armed" in north_rows.get("mailbox", ""), "clicking the root answers with the armed mailbox: %r"
          % north_rows.get("mailbox", ""))
    check("nothing on that machine is watching" in south_rows.get("mailbox", ""),
          "…and on the other machine says what is missing and why it matters")
    check("legend:ear" in entries, "the mark has a key in the legend that says what it means")

    # a stale ear: older than twice its own poll
    old = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=400)
    write_json(w["hub"] / "ear-north-hub.json",
               {"to": "NORTH/hub", "machine": "north", "lane": "hub", "when": iso(old),
                "title": TITLE, "every": 150})
    html = render(w, "tree-stale.html")
    north = root_card(html, "north")
    check("no mailbox" in north and "◗ mailbox" not in north,
          "an ear older than 2× its poll reads `no mailbox` — a mailbox nobody is holding")
    entries = json.loads(re.search(r'<script type="application/json" id="marks">(.*?)</script>',
                                   html, re.S).group(1))
    row = dict((r[0], r[1]) for r in (entries.get("root:north") or {}).get("bytes") or []).get("mailbox", "")
    check("stopped answering" in row, "…and the click says when it stopped answering: %r" % row)

    # just inside the window is still fresh
    write_json(w["hub"] / "ear-north-hub.json",
               {"to": "NORTH/hub", "machine": "north", "lane": "hub",
                "when": iso(datetime.datetime.now().astimezone() - datetime.timedelta(seconds=200)),
                "title": TITLE, "every": 150})
    html = render(w, "tree-fresh.html")
    check("◗ mailbox" in root_card(html, "north"),
          "an ear inside 2× its poll is still fresh — one missed beat is a hiccup, not a silence")


# --------------------------------------------------------------------------
# C4 — one lane, either spelling
# --------------------------------------------------------------------------

def case_c4():
    start("C4", "one lane, either spelling (punch list §4.5)")
    w = world("c4")
    write(w["hub"] / "INBOX.md",
          "# INBOX\n\n"
          "- 2026-09-17 · to: NORTH/Alpha-One · Alpha · the dash spelling · read it\n"
          "- 2026-09-17 · to: NORTH/Alpha/One · Alpha · the slash spelling · read it\n"
          "- 2026-09-17 · to: SOUTH/hub · Exocortex · another lane's letter · ignore it\n")
    for spelling in ("NORTH/Alpha/One", "north/alpha-one", "NORTH/Alpha-ONE"):
        code, out = tool(w, "mail.py", "--read", spelling)
        check(code == 0 and out.count("MAIL:") == 2,
              "`--read %s` finds both spellings of the one lane (found %d)"
              % (spelling, out.count("MAIL:")))
    code, out = tool(w, "mail.py", "--read", "SOUTH/hub")
    check(out.count("MAIL:") == 1, "…and still answers for one lane only, never another's")
    mail = load_mail(w)
    check(mail.ear_path(w["hub"], "NORTH/Alpha-One").name
          == mail.ear_path(w["hub"], "north/alpha/one").name == "ear-north-alpha-one.json",
          "both spellings share one ear file: %s" % mail.ear_path(w["hub"], "NORTH/Alpha-One").name)


# ==========================================================================
# BQ63 — three checks that went red for a reason that was not the tool's
# ==========================================================================

GIT_ID = ["-c", "user.name=exocortex gate", "-c", "user.email=gate@example.invalid",
          "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def merge_brain(base):
    """A SCRATCH BRAIN whose newest commit touching orchestrator/INBOX.md is a
    MERGE — the shape the sync's own conflict recovery makes on these two
    machines every day, built from nothing so the case never depends on what the
    real brain happens to look like this hour.

    Both sides change INBOX.md and the merge keeps BOTH lines, so the merge
    commit is TREESAME to neither parent: git cannot simplify it away, and the
    read that carries no merge flags therefore lands on a commit whose file list
    is empty.  That red, reproduced.

    Returns (repo, env) or (None, why) — a machine with no git says so and the
    case skips rather than failing for the absence of a tool."""
    code, out = run(["git", "--version"], timeout=60)
    if code != 0:
        return None, "git would not run here (%s)" % out.strip().splitlines()[:1]
    repo = Path(base) / "brain"
    home = Path(base) / "githome"
    (repo / "orchestrator").mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    # HOME is the world's, so not one line of the user's own git config is read
    # and not one byte of it is written.
    env = {"HOME": str(home), "USERPROFILE": str(home), "HOMEDRIVE": None, "HOMEPATH": None}
    inbox = repo / "orchestrator" / "INBOX.md"

    def g(*args):
        return run(["git", "-C", str(repo)] + GIT_ID + list(args), env=env, timeout=120)

    code, out = run(["git", "init", "-q", str(repo)], env=env, timeout=120)
    if code != 0:
        return None, "git init would not run (%s)" % out.strip()
    write(inbox, "# INBOX\n\n- 2026-09-20 · to: NORTH/hub · Exocortex · the first line · read it\n")
    g("add", "-A")
    g("commit", "-q", "-m", "first")
    g("branch", "-m", "main")                      # one branch name on every git
    g("checkout", "-q", "-b", "other-machine")
    write(inbox, "# INBOX\n\n- 2026-09-20 · to: NORTH/hub · Exocortex · the first line · read it\n"
                 "- 2026-09-21 · to: NORTH/hub · Exocortex · the SOUTH's line · read it\n")
    g("add", "-A")
    g("commit", "-q", "-m", "the other machine's letter")
    g("checkout", "-q", "main")
    write(inbox, "# INBOX\n\n- 2026-09-20 · to: NORTH/hub · Exocortex · the first line · read it\n"
                 "- 2026-09-21 · to: SOUTH/hub · Exocortex · this machine's line · read it\n")
    g("add", "-A")
    g("commit", "-q", "-m", "this machine's letter")
    g("merge", "--no-ff", "--no-commit", "other-machine")        # exits 1: a real conflict
    write(inbox, "# INBOX\n\n- 2026-09-20 · to: NORTH/hub · Exocortex · the first line · read it\n"
                 "- 2026-09-21 · to: SOUTH/hub · Exocortex · this machine's line · read it\n"
                 "- 2026-09-21 · to: NORTH/hub · Exocortex · the SOUTH's line · read it\n")
    g("add", "-A")
    code, out = g("commit", "-q", "-m", "sync: union merge")
    if code != 0:
        return None, "the merge commit would not be made (%s)" % out.strip()
    return repo, env


def case_bq63a():
    start("BQ63A", "a merge commit never reads as an empty change (BQ-063 A)")
    base = ROOT / ("bq63a-%d" % os.getpid())
    shutil.rmtree(str(base), ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    WORLDS.append({"base": base})                  # swept with every other world
    repo, env = merge_brain(base)
    if repo is None:
        skip("no merge fixture could be built: %s" % env)
    else:
        code, out = run(["git", "-C", str(repo), "log", "-1", "--format=%p", "--", "."],
                        env=env, timeout=120)
        check(code == 0 and len(out.split()) == 2,
              "the fixture's newest commit really is a MERGE — two parents: %s"
              % " ".join(out.split()))
        code, out = inbox_commit_names(repo, env=env)
        check(code == 0 and "orchestrator/INBOX.md" in out,
              "C1's own read lists INBOX.md among that merge's files: %s"
              % " ".join(out.split()[:2]))
        code, bare = inbox_commit_names(repo, merge_safe=False, env=env)
        check(code == 0 and "orchestrator/INBOX.md" not in bare,
              "…and the read WITHOUT the two flags lists no file at all — the red of "
              "2026-09-22 10:06, reproduced from nothing")
        check(out.split()[:1] == bare.split()[:1],
              "…on the very same commit, so the flags change the DIFF and never the walk")

    start("BQ63A-sweep", "every gate that reads the brain's log, and whether it is merge-safe")
    mine_src = io.open(str(Path(__file__)), encoding="utf-8").read().splitlines()
    check(all(f in "\n".join(mine_src) for f in MERGE_SAFE),
          "this gate's own brain-log read carries %s" % " ".join(MERGE_SAFE))
    marked = [n + 1 for n, l in enumerate(mine_src)
              if l.rstrip().endswith(CONTROL_MARK) and not l.lstrip().startswith("CONTROL_MARK")]
    check(len(marked) == 1,
          "exactly ONE line in this gate is marked a deliberate flagless control (line %s) — "
          "a second one would be a defect hiding behind the mark" % (marked or "none"))
    # THE GATE'S OWN FOLDER, never one resolved from the record (a reader of
    # the record would judge another copy).  The sweep used to read `real_hub()/tools`,
    # so in a scratch run it judged the INSTALLED gate instead of the built one —
    # green here, red the moment it was installed.  A tool proves its own shape.
    folder = Path(__file__).resolve().parent
    try:
        gates = sorted(folder.glob("gate-*.py"))
    except OSError:
        gates = []
    hits = log_name_reads(gates)
    print("       %d gate(s) swept in %s · %d log+name window(s) found · the scan is "
          "DELIBERATELY BROAD, so a window is a place for the lane to read; only a real "
          "read of the brain's log is judged" % (len(gates), folder, len(hits)))
    for hit in hits:
        print("       %s:%d  %s  %s  %s  %s"
              % (hit["file"], hit["line"], "merge-safe" if hit["safe"] else "NOT merge-safe",
                 "reads the brain" if hit["brain"] else "not the brain's log",
                 "JUDGED" if counted(hit) else "listed only (%s)" % why_not_counted(hit),
                 hit["what"]))
    mine = [h for h in hits if h["file"] == Path(__file__).name and counted(h)]
    check(bool(mine) and all(h["safe"] for h in mine),
          "this gate's own %d real read(s) of the brain's log carry both flags — every other "
          "window is listed above for the lane, never failed here" % len(mine))


BRAIN_WORDS = ("BRAIN", "orchestrator-sync", "INBOX.md")


def counted(hit):
    """A window this sweep will JUDGE: a real invocation of git, on the brain's own
    log, that is not the one line marked a deliberate control.  Everything else is
    listed for the lane and nothing more — a sweep that fails on its own prose, or
    on a fixture repo, is the very kind of untrue red these checks exist to close."""
    return bool(hit["git"] and hit["brain"] and not hit["control"])


def why_not_counted(hit):
    if not hit["git"]:
        return "no git call in it"
    if not hit["brain"]:
        return "not the brain's log"
    return "the marked control"


def code_view(path):
    """(the file's lines, the same lines with its COMMENTS and PROSE STRINGS
    blanked).  A prose string is one that is a statement all by itself — every
    docstring — so a paragraph ABOUT a git read is never mistaken for one, while
    a command's own arguments, which are strings inside an expression, are left
    exactly as they are.  A file that will not tokenize is scanned as it stands:
    never skipped, because a sweep that quietly drops a file proves nothing."""
    try:
        raw = io.open(str(path), encoding="utf-8", errors="replace").read()
    except OSError:
        return [], []
    lines = raw.splitlines()
    out = list(lines)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(raw).readline))
    except Exception:
        return lines, out
    skip_types = (tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT,
                  getattr(tokenize, "ENCODING", -1))
    sig = [i for i, t in enumerate(toks) if t[0] not in skip_types]
    blank = [t for t in toks if t[0] == tokenize.COMMENT]
    for n, i in enumerate(sig):
        t = toks[i]
        if t[0] != tokenize.STRING:
            continue
        before = toks[sig[n - 1]][0] if n else tokenize.NEWLINE
        after = toks[sig[n + 1]][0] if n + 1 < len(sig) else tokenize.NEWLINE
        if before == tokenize.NEWLINE and after == tokenize.NEWLINE:
            blank.append(t)                       # a string that is a whole statement
    for t in blank:
        (srow, scol), (erow, ecol) = t[2], t[3]
        for row in range(srow, erow + 1):
            idx = row - 1
            if idx < 0 or idx >= len(out):
                continue
            line = out[idx]
            a = min(scol if row == srow else 0, len(line))
            b = min(ecol if row == erow else len(line), len(line))
            out[idx] = line[:a] + " " * max(0, b - a) + line[b:]
    return lines, out


def log_name_reads(paths):
    """Every `git log … --name-only` / `--stat` WINDOW in these files, with the
    facts that decide whether it is judged: does it carry both merge-safe flags ·
    is it the BRAIN's log · is there a git call in it at all · is it the one
    marked control.  A read is one command expression, so the window is the five
    lines it may be split over.  The scan runs over the CODE view, so a docstring
    never counts; it stays deliberately broad, because a sweep that misses a real
    read is worse than one that names a fixture and says so."""
    out = []
    for path in paths:
        lines, code = code_view(path)
        for i, line in enumerate(code):
            if '"log"' not in line and "'log'" not in line and " log " not in line:
                continue
            window = "\n".join(code[i:i + 5])
            if "--name-only" not in window and "--stat" not in window:
                continue
            out.append({"file": Path(path).name, "line": i + 1,
                        "safe": all(f in window for f in MERGE_SAFE),
                        "brain": any(word in window for word in BRAIN_WORDS),
                        "git": '"git"' in window or "'git'" in window,
                        "control": CONTROL_MARK in "\n".join(lines[i:i + 5]),
                        "what": lines[i].strip()[:70]})
    return out


# THE EAR FILES THIS GATE'S OWN WORLDS COULD CREATE (BQ63B).  Every address a
# case hands to a verb that WRITES AN EAR — mail.py's --watch, --wait and --read
# (mail.py:243 writes one on a read too) and the gate's own plant_ear().  A
# letter's address is NOT here: sending one writes no ear.  BQ63B checks this
# list against the file itself, so a case added tomorrow cannot quietly narrow it.
EAR_ADDRESSES = ("NORTH/hub", "SOUTH/hub", "NORTH/lane-x", "OWNER",
                 "NORTH/Alpha/One", "NORTH/Alpha-One",     # the last two reach --read by variable
                 "SOUTH/Lane", "NORTH/Proj-Wren", "NORTH/Proj-Dee")   # BQ205-G1 · G2


def mail_source():
    """mail.py imported from wherever this gate's layout finds it — for ear_path
    and nothing else.  It reads no hub of its own."""
    spec = importlib.util.spec_from_file_location("gate_mail_src", str(source_tool("mail.py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def own_ear_names(hub):
    """The ear FILE NAMES this gate's own worlds could ever make in that hub —
    mail.py's own ear_path for each of the gate's own addresses, so the name is
    spelled by the tool and never by this file."""
    mail = mail_source()
    return sorted(set(mail.ear_path(hub, addr).name for addr in EAR_ADDRESSES))


def new_own_ears(before, after, own):
    """The ear files OF THIS GATE'S OWN MAKING that appeared during the run.

    BQ63B: the check used to compare EVERY ear name in the live hub, so a live
    session arming its own waiter (an ear file like ear-north-builds.json) made
    the gate red for something the gate had not done.  What this check has always
    MEANT is this: none of the names this gate could have written is new."""
    return sorted(n for n in own if n in after and n not in before)


def case_bq63b():
    start("BQ63B", "the live ear check watches only the names this gate could write (BQ-063 B)")
    w = world("bq63b")
    mail = load_mail(w)
    own = own_ear_names(w["hub"])
    check("ear-north-hub.json" in own and "ear-north-alpha-one.json" in own,
          "the watched names are mail.py's own spelling of this gate's addresses: %s"
          % ", ".join(own))
    before = {"ear-north-hub.json": 1}
    after = {"ear-north-hub.json": 1, "ear-north-builds.json": 1}
    check(new_own_ears(before, after, own) == [],
          "A LIVE SESSION ARMING ITS OWN WAITER (ear-north-builds.json) NEVER REDS THIS GATE")
    check(sorted(before) != sorted(after),
          "…although the whole-hub comparison this replaces would have gone red for it")
    leaked = dict(after)
    leaked["ear-north-lane-x.json"] = 1
    check(new_own_ears(before, leaked, own) == ["ear-north-lane-x.json"],
          "…and an ear THIS GATE could have written, appearing, is still caught by name")
    check(new_own_ears({"ear-north-hub.json": 1}, {"ear-north-hub.json": 2}, own) == [],
          "an ear that was there before and was merely refreshed is not an appearance")

    # THE LIST STAYS HONEST: every address this file hands to an ear-writing verb
    # is one of the names above, or this case says so by name.
    src = io.open(str(Path(__file__)), encoding="utf-8").read()
    found = set()
    for m in re.finditer(r"(?:plant_ear|watch_once|waiter|run_waiter)\([^\n)]*?\"([A-Za-z][^\"\n]*?/[^\"\n]*?)\""
                         r"|\"--(?:watch|wait|read)\"\s*,\s*\"([^\"\n]+)\"", src):
        found.add((m.group(1) or m.group(2)).strip())
    known = set(mail.addr_key(a) for a in EAR_ADDRESSES)
    stray = sorted(a for a in found if mail.addr_key(a) not in known)
    check(not stray, "every ear-writing address in this file is one of the watched names "
                     "(%d found, %d stray%s)"
                     % (len(found), len(stray), (": %s" % ", ".join(stray)) if stray else ""))


def postman_hooks(path):
    """THE POSTMAN'S OWN HOOK ENTRIES in a Claude settings file — (kind, entries),
    kind being "ok", "absent" or "unreadable".

    BQ63C: the LIVE check compared the FILE'S SIZE, and the app rewrites that
    file itself (a new permission rule does exactly that), so
    the gate went red for the app's work.  What the gate must never touch is not
    the file — it is the entries an install would write, so those are what is
    compared.  One entry is one line: event · matcher · timeout · command."""
    p = Path(path)
    if not p.is_file():
        return ("absent", [])
    try:
        d = json.loads(io.open(str(p), encoding="utf-8").read())
    except Exception as exc:
        return ("unreadable (%s)" % type(exc).__name__, [])
    if not isinstance(d, dict):
        return ("unreadable (not an object)", [])
    out = []
    for event, groups in sorted((d.get("hooks") or {}).items()):
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for entry in (group.get("hooks") or []):
                if not isinstance(entry, dict):
                    continue
                cmd = str(entry.get("command") or "")
                if "postman.py" in cmd:
                    out.append("%s · %s · %s · %s"
                               % (event, group.get("matcher") or "", entry.get("timeout"), cmd))
    return ("ok", sorted(out))


def case_bq63c():
    start("BQ63C", "the live settings check compares the postman's own entries (BQ-063 C)")
    w = world("bq63c")
    settings = w["home"] / ".claude" / "settings.json"
    foreign = {"matcher": None,
               "hooks": [{"type": "command", "command": "/opt/another-tool/hook.sh",
                          "timeout": 5}]}
    ours = {"hooks": [{"type": "command",
                       "command": '"/usr/bin/python3" "/hub/tools/postman.py" --hook',
                       "timeout": 5}]}
    body = {"model": "opus", "hooks": {"SessionStart": [foreign, ours],
                                       "UserPromptSubmit": [ours],
                                       "Notification": [foreign]}}
    write_json(settings, body)
    kind, before = postman_hooks(settings)
    check(kind == "ok" and len(before) == 2,
          "the postman's own entries are found beside another tool's: %d" % len(before))
    size_before = settings.stat().st_size

    # THE APP ITSELF REWRITES THAT FILE — a permission rule, a theme, a model.
    body["permissions"] = {"allow": ["Bash(python3 tools/pulse.py:*)"], "deny": []}
    body["theme"] = "dark"
    write_json(settings, body)
    kind, after = postman_hooks(settings)
    check(kind == "ok" and after == before,
          "the app rewriting the file leaves the postman's entries untouched — no red")
    check(settings.stat().st_size != size_before,
          "…while the SIZE this replaces moved by %d bytes, which is the false red"
          % (settings.stat().st_size - size_before))

    body["hooks"]["Stop"] = [ours]
    write_json(settings, body)
    kind, more = postman_hooks(settings)
    check(kind == "ok" and len(more) == 3 and more != before,
          "an entry ADDED to the postman's own hooks is caught: %d → %d"
          % (len(before), len(more)))
    del body["hooks"]["UserPromptSubmit"]
    write_json(settings, body)
    kind, fewer = postman_hooks(settings)
    check(kind == "ok" and len(fewer) == 2 and fewer != more,
          "…and so is one REMOVED: %d → %d" % (len(more), len(fewer)))

    write(settings, "{not json at all")
    kind, broken = postman_hooks(settings)
    check(kind.startswith("unreadable") and broken == [],
          "an unparseable settings file says so and claims nothing: %s" % kind)
    settings.unlink()
    kind, gone = postman_hooks(settings)
    check(kind == "absent" and gone == [],
          "an absent one says absent — the only state that passes on its own")
    check(postman_hooks(w["home"] / ".claude" / "never-written.json") == ("absent", []),
          "…and a path that never existed reads the same way, never an exception")


# ==========================================================================
# THE POSTMAN — phase A
# ==========================================================================

HOLDER = "ACT — Exocortex/hub: the holder"
OTHER = "ACT — Exocortex/hub: the second window"
SID_A = "aaaaaaaa-1111-2222-3333-aaaaaaaaaaaa"
SID_B = "bbbbbbbb-1111-2222-3333-bbbbbbbbbbbb"
TID_C = "01a0c0de-0000-7000-8000-cccccccccccc"          # a Codex thread id's real shape

# A sync.py that carries the brain between two scratch worlds by copying the
# signal files through a shared folder. No git, no network — and it records the
# verb, exactly as SYNC_STUB does, so C1's check still reads the same log.
FAKE_SYNC = (
    "import io, os, sys, glob, shutil\n"
    "here = os.path.dirname(os.path.abspath(__file__))\n"
    "io.open(os.path.join(here, 'sync-calls.log'), 'a', encoding='utf-8')"
    ".write(' '.join(sys.argv[1:]) + '\\n')\n"
    "hub, brain = %r, %r\n"
    "os.makedirs(brain, exist_ok=True)\n"
    "verb = sys.argv[1] if len(sys.argv) > 1 else ''\n"
    "pats = ('post-*.json', 'claims.json', 'ear-*.json', 'live-*.json', 'INBOX.md')\n"
    "src, dst = (hub, brain) if verb == 'push' else (brain, hub)\n"
    "for p in pats:\n"
    "    for f in glob.glob(os.path.join(src, p)):\n"
    "        shutil.copy2(f, os.path.join(dst, os.path.basename(f)))\n"
)


def pworld(name, machine="north", fleet=("north", "south"), brain=None, prime=True, base_dir=None):
    """A world with a postman in it.  PRIMED by default: one pass over an empty
    INBOX, so the bootstrap cut-off is already behind us and a letter written by a
    case is a letter that ARRIVED rather than one that was always there.  P2, the
    bootstrap case itself, is the one that asks for prime=False."""
    w = world(name, fleet=fleet, machine=machine, base_dir=base_dir)
    if brain:
        write(w["home"] / "orchestrator-sync" / "sync.py", FAKE_SYNC % (str(w["hub"]), str(brain)))
        w["brain"] = brain
    write(w["hub"] / "INBOX.md", "# INBOX\n\n")
    if prime:
        pm(w, "--pass", "--no-pull", "--quiet")
    return w


def pm(w, *args, **kw):
    """postman.py in that world, always through its own seams."""
    env = dict(w["env"])
    env.update(kw.get("env") or {})
    return run([PY, str(w["hub"] / "tools" / "postman.py")] + list(args)
               + ["--hub", str(w["hub"]), "--post-dir", str(w["post"])],
               cwd=str(w["hub"]), env=env, timeout=kw.get("timeout", 120))


def mp(w, *args, **kw):
    env = dict(w["env"])
    env.update(kw.get("env") or {})
    return run([PY, str(w["hub"] / "tools" / "mail.py")] + list(args) + ["--hub", str(w["hub"])],
               cwd=str(w["hub"]), env=env, timeout=kw.get("timeout", 120))


def as_session(sid, host="local_gate"):
    return {"CLAUDE_CODE_SESSION_ID": sid, "CLAUDE_CODE_HOST_SESSION_ID": host}


def letter(w, to, text, action="answer it", date=None):
    line = "- %s · to: %s · Exocortex · %s · %s" % (
        date or datetime.date.today().isoformat(), to, text, action)
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return line


# an ACTION that asks the PERSON something, and the one consequence
# line `mail.user_line` makes of it.  A notice is that line + the window's title, never the sender.
ASK_ACTION = "Choose the header colour — say blue or green"
ASK_LINE = "Choose the header colour · say blue or green"
RETIRED_WORDS = ("is waiting", "say mail", "A note for the", "mail waiting")


def tok(w, line):
    return load_mail(w).token(line)


def claude_transcript(w, sid, rows=(), project="-gate-hub"):
    """A Claude Code transcript in its REAL shape: one JSON object per line, the
    file named for the session, a tool result carrying `toolUseResult.stdout`, a
    hook's injected text in a `hook_additional_context` attachment."""
    path = w["home"] / ".claude" / "projects" / project / ("%s.jsonl" % sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [json.dumps({"parentUuid": None, "isSidechain": False, "type": "user",
                        "message": {"role": "user", "content": "go"},
                        "uuid": "u1", "timestamp": "2026-09-19T17:00:00.000Z",
                        "cwd": str(w["hub"]), "sessionId": sid, "version": "2.1.275"},
                       ensure_ascii=False)]
    if not path.is_file():
        # a fixture window has replied once, on a cheap model with a
        # small context, so `mail.py --wait` reads a real model from it and arms.
        body.append(json.dumps({"parentUuid": "u1", "isSidechain": False, "type": "assistant",
                                "message": {"role": "assistant", "model": "claude-sonnet-5",
                                            "content": [{"type": "text", "text": "ok"}],
                                            "usage": {"input_tokens": 4000,
                                                      "cache_read_input_tokens": 4000,
                                                      "cache_creation_input_tokens": 4000}},
                                "uuid": "a0", "timestamp": "2026-09-19T17:00:01.000Z",
                                "sessionId": sid}, ensure_ascii=False))
    for row in rows:
        body.append(json.dumps(row, ensure_ascii=False))
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(body) + "\n")
    return path


def title_file(w, sid, title, project="-gate-hub"):
    """The app's own title record for a window: `<projects>/<folder>/<sid>/custom-title.json`
    — the road `mail.py --wait --title` reads."""
    write_json(w["home"] / ".claude" / "projects" / project / sid / "custom-title.json",
               {"customTitle": title})


def claude_stdout(sid, text):
    return {"type": "user", "sessionId": sid, "cwd": "", "timestamp": "2026-09-19T17:01:00.000Z",
            "toolUseResult": {"stdout": text, "stderr": "", "interrupted": False,
                              "isImage": False, "noOutputExpected": False},
            "uuid": "u2"}


def claude_hook_context(sid, text):
    # postman.py observe(): only an injected, body-bound context proves delivery.
    return {"type": "attachment",
            "attachment": {"type": "hook_additional_context", "content": [text]},
            "sessionId": sid, "uuid": "u3", "timestamp": "2026-09-19T17:02:00.000Z"}


def letter_context(w, line, token=None):
    """The same body-and-token frame the real hook hands the target window."""
    return pm_module(w).frame([{"kind": "letter", "line": line,
                                "token": token or tok(w, line), "to": fields(line)[1][4:]}])


def codex_rollout(w, tid, stdouts=()):
    """A Codex rollout in its REAL shape: first record `session_meta` carrying
    `payload.session_id` and `payload.cwd`, then `event_msg` /
    `payload.item.type == "CommandExecution"` records carrying the command's own
    stdout — which is how a Codex thread's printed line is seen at all."""
    folder = w["home"] / ".codex" / "sessions" / "2026" / "09" / "19"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("rollout-2026-09-19T10-00-00-%s.jsonl" % tid)
    body = [json.dumps({"timestamp": "2026-09-19T17:00:00.000Z", "ordinal": 0,
                        "type": "session_meta",
                        "payload": {"session_id": tid, "id": tid, "cwd": str(w["hub"]),
                                    "originator": "codex_work_desktop",
                                    "cli_version": "0.155.0-alpha"}}, ensure_ascii=False)]
    for n, text in enumerate(stdouts, 1):
        body.append(json.dumps({"timestamp": "2026-09-19T17:0%d:00.000Z" % n, "ordinal": n,
                                "type": "event_msg",
                                "payload": {"type": "item_completed", "thread_id": tid,
                                            "turn_id": "t1",
                                            "item": {"type": "CommandExecution", "id": "exec-%d" % n,
                                                     "command": ["/bin/zsh", "-lc", "mail.py --read"],
                                                     "status": "completed", "stdout": text,
                                                     "stderr": "", "exit_code": 0}}},
                               ensure_ascii=False))
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(body) + "\n")
    return path


def plant_claim(w, arc, machine, title, mind="FABLE", session=None, since=None, host_session=None):
    claims = json.loads(io.open(str(w["hub"] / "claims.json"), encoding="utf-8").read()) \
        if (w["hub"] / "claims.json").is_file() else []
    row = {"arc": arc, "machine": machine, "mind": mind, "title": title,
           "since": since or iso(datetime.datetime.now().astimezone())}
    if session:
        row["session"] = session
        row["vendor"] = "claude"
        if host_session:
            row["host_session"] = host_session       # the app's own id, which the nudge links
    claims.append(row)
    write(w["hub"] / "claims.json", json.dumps(claims, ensure_ascii=False, indent=2) + "\n")
    return row


def plant_ear(w, to, title, session=None, every=150, how="watch", age_s=0):
    key = re.sub(r"[^a-z0-9]+", "-", to.lower()).strip("-")
    when = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=age_s)
    body = {"to": to, "machine": to.split("/")[0].lower(), "lane": to.split("/", 1)[1],
            "when": iso(when), "title": title, "every": every, "how": how}
    if session:
        body["session"] = session
        body["vendor"] = "claude"
    write_json(w["hub"] / ("ear-%s.json" % key), body)
    return body


def post_of(w, machine=None):
    return json.loads(io.open(str(w["hub"] / ("post-%s.json" % (machine or w["machine"]))),
                              encoding="utf-8").read())


def pending_of(w, sid):
    path = w["post"] / "pending" / ("%s.json" % sid)
    if not path.is_file():
        return []
    return json.loads(io.open(str(path), encoding="utf-8").read()).get("items") or []


def hook(w, sid, event, extra=None, vendor="claude", post=None):
    payload = {"session_id": sid, "hook_event_name": event, "cwd": str(w["hub"]),
               "transcript_path": ""}
    payload.update(extra or {})
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in w["env"].items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    proc = subprocess.run([PY, str(w["hub"] / "tools" / "postman.py"), "--hook",
                           "--vendor", vendor, "--post-dir", str(post or w["post"])],
                          input=json.dumps(payload), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


def pm_module(w):
    """The postman this world is running, loaded once per world — the gate asks
    IT what the person is called rather than spelling a name of its own."""
    import importlib.util as _iu
    key = str(w["hub"])
    if key not in _PM_MODULES:
        spec = _iu.spec_from_file_location("gate_pm_label_%d" % len(_PM_MODULES),
                                           str(w["hub"] / "tools" / "postman.py"))
        mod = _iu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PM_MODULES[key] = mod
    return _PM_MODULES[key]


_PM_MODULES = {}


def context_of(out):
    """The additionalContext a hook printed, or '' — parsed the way the vendor
    documents it, never by substring."""
    try:
        d = json.loads(out)
        return d["hookSpecificOutput"]["additionalContext"]
    except Exception:
        return ""


# --------------------------------------------------------------------------
# P1 — tokens
# --------------------------------------------------------------------------

def case_p1():
    start("P1", "a letter's token: one identity, the same on both machines")
    w = pworld("p1")
    mail = load_mail(w)
    line = "- 2026-09-19 · to: NORTH/hub · Exocortex · cut the payload · reply when done"
    t = mail.token(line)
    check(t.startswith("pm-") and len(t) == 15, "the token is `pm-` + 12 hex: %s" % t)
    check(all(c in "0123456789abcdef" for c in t[3:]),
          "…and ASCII only, so it survives any transcript's escaping")
    check(mail.token(line + " · delivered: 2026-09-19T08:00-07:00 by NORTH hub") == t,
          "an inline delivery mark does not change it — the stamped line is the same letter")
    check(mail.token("  " + line + "  ") == t, "…and neither does whitespace at the ends")
    d = pworld("p1-south", machine="south")
    check(load_mail(d).token(line) == t, "both machines compute the same token from the same line")
    check(mail.token(line + " ") == t and mail.token(line + "x") != t,
          "two byte-identical lines are one letter, and one changed byte is another")
    check(mail.is_fyi("- x · to: NORTH/hub · E · hi · no reply needed — FYI") is True
          and mail.is_fyi("- x · to: NORTH/hub · E · hi · Answer, NO REPLY NEEDED please") is True
          and mail.is_fyi(line) is False,
          "the FYI test is one function, on the ACTION field, casefolded")


# --------------------------------------------------------------------------
# P2 — bootstrap
# --------------------------------------------------------------------------

def case_p2():
    start("P2", "bootstrap: the letters already in INBOX are never delivered by the postman")
    w = pworld("p2", prime=False)
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    old = [letter(w, "NORTH/hub", "an unmarked line from the hand-marked weeks %d" % n)
           for n in range(3)]
    code, out = pm(w, "--pass", "--no-pull")
    check(code == 0, "the first pass exits 0")
    check("BOOTSTRAP · 3 earlier letters left to --read" in out,
          "it says so in ONE loud line: %s" % next((l for l in out.splitlines()
                                                    if "BOOTSTRAP" in l), "(none)"))
    check(not pending_of(w, SID_A), "not one of them is queued for the holder")
    body = post_of(w)
    check(body.get("legacy", {}).get("count") == 3 and body["legacy"].get("before"),
          "the post file carries a COUNT and the cut-off moment, never a list: %s"
          % body.get("legacy"))
    check(all(t not in body["letters"] for t in [tok(w, l) for l in old]),
          "…and no legacy letter is tracked as waiting")
    code, out = mp(w, "--read", "NORTH/hub")
    check(out.count("MAIL:") == 3,
          "they stay readable by --read, exactly as the bootstrap line promises (found %d)"
          % out.count("MAIL:"))
    new = letter(w, "NORTH/hub", "the first letter the postman carries")
    pm(w, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(w, SID_A)] == [tok(w, new)],
          "the letter that arrives AFTER the cut-off is carried, and only it")


# --------------------------------------------------------------------------
# P3 — routing
# --------------------------------------------------------------------------

def case_p3():
    start("P3", "routing: the claim holder gets it (the morning of 2026-09-19, replayed)")
    w = pworld("p3")
    # Two North sessions with NORTH/hub ears; ONE of them holds the claim.
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    plant_ear(w, "NORTH/hub", HOLDER, session=SID_A)
    plant_ear(w, "NORTH/hub", OTHER, session=SID_B)          # the freshest ear is the OTHER one
    claude_transcript(w, SID_A)
    claude_transcript(w, SID_B)
    one = letter(w, "NORTH/hub", "a cut order from the SOUTH")
    pm(w, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(w, SID_A)] == [tok(w, one)],
          "the CLAIM HOLDER is the one it is queued for")
    check(not pending_of(w, SID_B),
          "…and the second window, whose ear is fresher, gets nothing — an ear is not a claim")
    # the second window reads the mailbox it does not hold: seen, not delivered
    claude_transcript(w, SID_B, [claude_stdout(SID_B, "MAIL: %s [%s]" % (one, tok(w, one)))])
    pm(w, "--pass", "--no-pull")
    e = post_of(w)["letters"][tok(w, one)]
    check(e["state"] == "waiting", "a session that merely READS it has not been delivered to")
    check([s["title"] for s in e.get("also_seen_by") or []] == [OTHER],
          "…it is recorded under also_seen_by: %s" % (e.get("also_seen_by"),))

    start("P3b", "routing: suffix, ambiguity, the other machine, and hub per machine")
    x = pworld("p3b")
    plant_claim(x, "Exocortex/Builds", "north", "ACT — Exocortex/Builds: b", session=SID_A)
    claude_transcript(x, SID_A)
    lb = letter(x, "NORTH/Builds", "a letter by the lane's short name")
    pm(x, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(x, SID_A)] == [tok(x, lb)],
          "NORTH/Builds is answered by the arc Exocortex/Builds — the unique `/`-suffix")
    plant_claim(x, "Alpha/Builds", "north", "ACT — Alpha/Builds: b2", session=SID_B)
    claude_transcript(x, SID_B)
    la = letter(x, "NORTH/Builds", "which Builds?")
    code, out = pm(x, "--pass", "--no-pull")
    e = post_of(x)["letters"][tok(x, la)]
    check(e["state"] == "waiting" and "two lanes answer to that name" in e["why"],
          "two answering claims is AMBIGUOUS and nothing is delivered: %s" % e["why"])
    check("Alpha/Builds" in e["why"] and "Exocortex/Builds" in e["why"],
          "…and the why names both lanes so the sender can fix the address")
    check(not any(i["token"] == tok(x, la) for i in pending_of(x, SID_A) + pending_of(x, SID_B)),
          "AMBIGUOUS never delivers — to either of them")

    y = pworld("p3c")
    plant_claim(y, "Alpha/One", "south", "ACT — Alpha/One: on the South", session="south-1")
    lg = letter(y, "NORTH/Alpha-One", "addressed to the wrong machine")
    pm(y, "--pass", "--no-pull")
    check(not (y["hub"] / "post-north.json").is_file() or
          tok(y, lg) not in post_of(y).get("letters", {}),
          "the NORTH writes no entry for a letter whose holder lives on the SOUTH")
    mail = load_mail(y)
    import importlib.util as _iu
    spec = _iu.spec_from_file_location("gate_pm", str(y["hub"] / "tools" / "postman.py"))
    pmod = _iu.module_from_spec(spec)
    spec.loader.exec_module(pmod)
    answer = pmod.route(lg, mail, pmod.read_claims(y["hub"]), pmod.read_ears(y["hub"]),
                        set(["north", "south"]))
    check(answer["state"] == "held" and answer["holder"]["machine"] == "south",
          "…because the lane is really held on the SOUTH, and every machine routes it there")
    why = pmod.why_for({"to": "NORTH/Alpha-One", "state_kind": "held"}, answer["holder"],
                       [], mail, {})
    check(why == "Alpha-One is held on the SOUTH, not the NORTH — queued there",
          "the sender is told once, in the sender's own spelling: %s" % why)

    z = pworld("p3d")
    plant_claim(z, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(z, SID_A)
    lh = letter(z, "SOUTH/hub", "for the other machine's hub")
    pm(z, "--pass", "--no-pull")
    check(not pending_of(z, SID_A),
          "the hub arc is PER MACHINE: the North's hub claim never answers for SOUTH/hub")
    check(tok(z, lh) not in post_of(z).get("letters", {}),
          "…and the North writes no entry for it either — the SOUTH's pass owns that letter")

    v = pworld("p3e")
    claude_transcript(v, SID_B)
    plant_ear(v, "NORTH/hub", OTHER, session=SID_B, how="read")
    le = letter(v, "NORTH/hub", "no claim here, but a mailbox is armed")
    pm(v, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(v, SID_B)] == [tok(v, le)],
          "with no answering claim the freshest EAR names the session")
    plant_ear(v, "NORTH/lane-x", "a session that stopped answering", session=SID_B, every=150, age_s=400)
    lx = letter(v, "NORTH/lane-x", "its mailbox went quiet")
    pm(v, "--pass", "--no-pull")
    e = post_of(v)["letters"][tok(v, lx)]
    check(e["state"] == "waiting" and "nobody on the NORTH holds lane-x" in e["why"],
          "an ear older than twice its own poll names nobody: %s" % e["why"])

    u = pworld("p3f")
    lu = letter(u, "ELSEWHERE/hub", "a machine the record does not carry")
    pm(u, "--pass", "--no-pull")
    e = post_of(u)["letters"].get(tok(u, lu))
    check(e is None, "a letter to a machine outside the fleet is not the NORTH's to record")
    lowner = letter(u, "OWNER", "the drive is safe to eject", "none")
    pm(u, "--pass", "--no-pull")
    body = post_of(u)
    check(body["for_owner"] == [tok(u, lowner)],
          "a `to: OWNER` letter is listed under for_owner so phase B loses none")
    check(tok(u, lowner) in body["letters"],
          "…and its entry is really in the file the list points at")


# --------------------------------------------------------------------------
# P4 — identity
# --------------------------------------------------------------------------

def case_p4():
    start("P4", "the session map: a session says who it is, and never guesses")
    w = pworld("p4")
    env = as_session(SID_A)
    code, out = run([PY, str(w["hub"] / "tools" / "i-am.py"), "--quiet", "FABLE", "EXTRA",
                     HOLDER, "--hub", str(w["hub"])], cwd=str(w["hub"]),
                    env=dict(w["env"], **env))
    stamp = json.loads(io.open(str(w["hub"] / "live-north-fable.json"), encoding="utf-8").read())
    check(stamp["sessions"][0].get("session") == SID_A,
          "the stamp records the session id its environment gave: %r"
          % stamp["sessions"][0].get("session"))
    check("id: pn-" not in out, "…and prints NO nonce line, because nothing is missing")
    code, out = run([PY, str(w["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub",
                     HOLDER, "--hub", str(w["hub"])], cwd=str(w["hub"]), env=dict(w["env"], **env))
    claims = json.loads(io.open(str(w["hub"] / "claims.json"), encoding="utf-8").read())
    check(claims[0].get("session") == SID_A and claims[0].get("vendor") == "claude",
          "the claim records it too: %s" % {k: claims[0].get(k) for k in ("session", "vendor")})
    mp(w, "--read", "NORTH/hub", "--title", HOLDER, env=env)
    ear = json.loads(io.open(str(w["hub"] / "ear-north-hub.json"), encoding="utf-8").read())
    check(ear.get("session") == SID_A, "and so does the ear: %r" % ear.get("session"))

    # a second session of the same mind must not lose the first one's identity
    code, out = run([PY, str(w["hub"] / "tools" / "i-am.py"), "--quiet", "FABLE", "EXTRA",
                     OTHER, "--hub", str(w["hub"])], cwd=str(w["hub"]),
                    env=dict(w["env"], **as_session(SID_B)))
    stamp = json.loads(io.open(str(w["hub"] / "live-north-fable.json"), encoding="utf-8").read())
    got = dict((s["title"], s.get("session")) for s in stamp["sessions"])
    check(got.get(HOLDER) == SID_A and got.get(OTHER) == SID_B,
          "a re-stamp by another session keeps the first one's id: %s" % got)

    start("P4b", "no environment id: a nonce, bound from ONE transcript or not at all")
    n = pworld("p4b")
    code, out = run([PY, str(n["hub"] / "tools" / "claim.py"), "--quiet", "--claim",
                     "Alpha/One", "ACT — Alpha/One: an Nobody thread", "--mind", "NOBODY",
                     "--hub", str(n["hub"])], cwd=str(n["hub"]), env=n["env"])
    said = [l.strip() for l in out.splitlines() if l.strip().startswith("id: pn-")]
    check(len(said) == 1, "ONE added line, and only where the vendor gives no id: %r" % said)
    nonce = said[0].split()[-1] if said else ""
    claims = json.loads(io.open(str(n["hub"] / "claims.json"), encoding="utf-8").read())
    check(not claims[0].get("session"), "the claim carries no session id it does not have")
    letter(n, "NORTH/Alpha-One", "for the Nobody thread")
    pm(n, "--pass", "--no-pull")
    check(not any((n["post"] / "sessions").glob("*.json")),
          "an UNBOUND nonce never routes — nothing is queued for a session nobody has named")
    codex_rollout(n, TID_C, ["CLAIMED: Alpha/One …\n  id: %s\n" % nonce])
    code, out = pm(n, "--pass", "--no-pull")
    row = json.loads(io.open(str(n["post"] / "sessions" / ("%s.json" % TID_C)),
                             encoding="utf-8").read()) \
        if (n["post"] / "sessions" / ("%s.json" % TID_C)).is_file() else {}
    check(row.get("session") == TID_C and row.get("how") == "nonce",
          "found in exactly ONE rollout, it is bound: %s"
          % {k: row.get(k) for k in ("session", "vendor", "how")})
    check(row.get("vendor") == "codex", "…and the vendor comes from the store it was found in")

    c = pworld("p4c")
    code, out = run([PY, str(c["hub"] / "tools" / "i-am.py"), "--quiet", "OPUS", "EXTRA",
                     "ACT — Exocortex/x: no env id here", "--hub", str(c["hub"])],
                    cwd=str(c["hub"]), env=c["env"])
    nonce = next((l.strip().split()[-1] for l in out.splitlines()
                  if l.strip().startswith("id: pn-")), "")
    claude_transcript(c, SID_A, [claude_stdout(SID_A, "  id: %s" % nonce)])
    pm(c, "--pass", "--no-pull")
    check((c["post"] / "sessions" / ("%s.json" % SID_A)).is_file(),
          "a nonce is bound from a Claude-shaped transcript the same way")
    claude_transcript(c, SID_B, [claude_stdout(SID_B, "  id: %s" % nonce)])
    d2 = pworld("p4d")
    code, out = run([PY, str(d2["hub"] / "tools" / "i-am.py"), "--quiet", "OPUS", "EXTRA",
                     "ACT — Exocortex/x: doubled", "--hub", str(d2["hub"])],
                    cwd=str(d2["hub"]), env=d2["env"])
    nonce2 = next((l.strip().split()[-1] for l in out.splitlines()
                   if l.strip().startswith("id: pn-")), "")
    claude_transcript(d2, SID_A, [claude_stdout(SID_A, "  id: %s" % nonce2)])
    claude_transcript(d2, SID_B, [claude_stdout(SID_B, "  id: %s" % nonce2)])
    code, out = pm(d2, "--pass", "--no-pull")
    check("left unbound" in out and not list((d2["post"] / "sessions").glob("*.json")),
          "a nonce found in TWO transcripts binds nothing and says so: %s"
          % next((l for l in out.splitlines() if "unbound" in l), "(nothing)"))

    start("P4c", "BQ-025: the mind on a pen is looked up, never defaulted")
    m = pworld("p4e")
    run([PY, str(m["hub"] / "tools" / "i-am.py"), "--quiet", "OPUS", "EXTRA",
         "ACT — Exocortex/Builds: an OPUS builder", "--hub", str(m["hub"])],
        cwd=str(m["hub"]), env=dict(m["env"], **as_session(SID_B)))
    run([PY, str(m["hub"] / "tools" / "i-am.py"), "--quiet", "FABLE", "EXTRA",
         HOLDER, "--hub", str(m["hub"])], cwd=str(m["hub"]), env=dict(m["env"], **as_session(SID_A)))
    code, out = run([PY, str(m["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub",
                     HOLDER, "--hub", str(m["hub"])], cwd=str(m["hub"]),
                    env=dict(m["env"], **as_session(SID_A)))
    claims = json.loads(io.open(str(m["hub"] / "claims.json"), encoding="utf-8").read())
    check(claims[0]["mind"] == "FABLE",
          "a FABLE session beside a newer OPUS stamp records FABLE (it used to record OPUS)")
    code, out = run([PY, str(m["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "rename",
                     "ACT — Exocortex/Builds: an OPUS builder", "--hub", str(m["hub"])],
                    cwd=str(m["hub"]), env=dict(m["env"], **as_session(SID_B)))
    claims = json.loads(io.open(str(m["hub"] / "claims.json"), encoding="utf-8").read())
    got = dict((c["arc"], c["mind"]) for c in claims)
    check(got.get("rename") == "OPUS",
          "and an OPUS session beside a newer FABLE stamp records OPUS: %s" % got)
    code, out = run([PY, str(m["hub"] / "tools" / "claim.py"), "--quiet", "--claim",
                     "landing:TEST", "ACT — Nowhere/x: never stamped", "--hub", str(m["hub"])],
                    cwd=str(m["hub"]), env=m["env"])
    claims = json.loads(io.open(str(m["hub"] / "claims.json"), encoding="utf-8").read())
    got = dict((c["arc"], c["mind"]) for c in claims)
    check(got.get("landing:TEST") == "?",
          "a session no stamp carries records `?` — never the newest stamp's mind: %s" % got)
    check("mind unknown" in out, "…and says so in one line: %s"
          % next((l.strip() for l in out.splitlines() if "mind unknown" in l), "(nothing)"))


# --------------------------------------------------------------------------
# P5 — the hook
# --------------------------------------------------------------------------

def case_p5():
    start("P5", "the hook: the road a busy session rides, and the rules that bound it")
    w = pworld("p5")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)

    code, out, err = hook(w, "nobody-at-all", "UserPromptSubmit")
    check(code == 0 and out == "" and err == "",
          "THE NO-MAIL PATH prints nothing and exits 0")
    t0 = time.time()
    for _ in range(20):
        hook(w, "nobody-at-all", "UserPromptSubmit")
    span = (time.time() - t0) / 20.0 * 1000
    check_timed(span, "…and is cheap enough to run once a model round")

    for bad in ("", "not json at all", "[]", '{"hook_event_name":"Stop"}'):
        env = dict(os.environ)
        for k, v in w["env"].items():
            env.pop(k, None) if v is None else env.__setitem__(k, str(v))
        p = subprocess.run([PY, str(w["hub"] / "tools" / "postman.py"), "--hook",
                            "--post-dir", str(w["post"])], input=bad, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=60)
        check(p.returncode == 0 and not p.stdout,
              "malformed or empty stdin (%r) prints nothing and exits 0" % bad[:18])

    one = letter(w, "NORTH/hub", "a letter that wants an answer")
    fyi = letter(w, "NORTH/hub", "NORTH FABLE woke at 08:29", "no reply needed — FYI")
    pm(w, "--pass", "--no-pull")

    for event in sorted(load_postman(w).HOOK_EVENTS["claude"]):
        code, out, err = hook(w, SID_A, event, {"agent_id": "sub_7", "agent_type": "explore"})
        check(code == 0 and out == "",
              "THE MAIN-THREAD RULE: %s carrying agent_id gets nothing" % event)
    check(len(pending_of(w, SID_A)) == 2, "…and the letters are all still pending")

    code, out, err = hook(w, SID_A, "PostToolBatch")
    ctx = context_of(out)
    check(tok(w, one) in ctx, "PostToolBatch carries the letter that wants an answer")
    check(tok(w, fyi) not in ctx, "…and NOT the FYI line, mid-turn")
    check([i["token"] for i in pending_of(w, SID_A)] == [tok(w, fyi)],
          "the FYI line stays pending for a calmer road")
    check(json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PostToolBatch",
          "the frame is returned in the event's own documented JSON")
    check("carried by the postman" in ctx and "not typed by Wren" in ctx,
          "the frame says every time that a letter is another session's words")

    code, out, err = hook(w, SID_A, "Stop")
    # PHASE B: a Stop may now legitimately carry the ARM LINE for a window that
    # holds a lane and has no waiter, so this case asserts its own claim
    # exactly — the FYI LETTER is not carried — instead of an empty stdout.
    check(code == 0 and tok(w, fyi) not in context_of(out),
          "an FYI line alone never holds a stop open")
    two = letter(w, "NORTH/hub", "a second letter that wants an answer")
    pm(w, "--pass", "--no-pull")
    code, out, err = hook(w, SID_A, "Stop", {"stop_hook_active": True})
    check(code == 0 and out == "", "Stop stands down while stop_hook_active is true")
    code, out, err = hook(w, SID_A, "Stop")
    ctx = context_of(out)
    check(tok(w, two) in ctx and tok(w, fyi) in ctx,
          "…and with the guard down it carries the letter AND the FYI riding along")
    check(not pending_of(w, SID_A), "everything carried is cleared")

    rec = [json.loads(l) for l in io.open(str(w["post"] / "receipts.jsonl"),
                                          encoding="utf-8").read().splitlines() if l.strip()]
    check(all(r.get("road") == "hook" and r.get("session") == SID_A for r in rec)
          and set(r["event"] for r in rec) == set(["PostToolBatch", "Stop"]),
          "every delivery left a receipt naming its road and its event (%d)" % len(rec))

    start("P5b", "the hook: at-least-once — killed between the print and the receipt")
    k = pworld("p5b")
    plant_claim(k, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(k, SID_A)
    one = letter(k, "NORTH/hub", "the letter that must not be lost")
    pm(k, "--pass", "--no-pull")
    (k["post"] / "receipts.jsonl").mkdir()          # the receipt CANNOT be written: the kill
    code, out, err = hook(k, SID_A, "UserPromptSubmit")
    check(tok(k, one) in context_of(out), "the frame was printed before the failure")
    check([i["token"] for i in pending_of(k, SID_A)] == [tok(k, one)],
          "…and the letter is STILL pending: at-least-once, never at-most-once")
    (k["post"] / "receipts.jsonl").rmdir()
    code, out, err = hook(k, SID_A, "UserPromptSubmit")
    check(tok(k, one) in context_of(out),
          "it comes once more, with THE SAME TOKEN — which is what makes it idempotent")
    claude_transcript(k, SID_A, [claude_hook_context(SID_A, context_of(out))])
    pm(k, "--pass", "--no-pull")
    e = post_of(k)["letters"][tok(k, one)]
    check(e["state"] == "delivered" and e["delivered"]["evidence"] == "transcript",
          "and the observation closes it ONCE: %s" % e["delivered"])

    start("P5c", "the hook: an event a vendor's docs do not settle is absent from its map")
    pmod = load_postman(w)
    check("UserPromptSubmit" not in pmod.HOOK_EVENTS["codex"],
          "Codex's UserPromptSubmit is OFF — no documented subagent mark")
    check("PostToolUse" not in pmod.HOOK_EVENTS["codex"] and
          "PreToolUse" not in pmod.HOOK_EVENTS["codex"],
          "…and so are its tool events: \"Subagent hooks use the parent session id\"")
    check(all(v.get("doc") for m in pmod.HOOK_EVENTS.values() for v in m.values()),
          "every event in every map carries the doc line that backs it")
    c = pworld("p5d")
    plant_claim(c, "Alpha/One", "north", "ACT — Alpha/One: nobody", session=TID_C)
    codex_rollout(c, TID_C)
    lc = letter(c, "NORTH/Alpha-One", "a letter into an open Nobody thread")
    pm(c, "--pass", "--no-pull")
    code, out, err = hook(c, TID_C, "UserPromptSubmit", vendor="codex")
    check(code == 0 and out == "", "a Codex UserPromptSubmit hook carries nothing at all")
    code, out, err = hook(c, TID_C, "SessionStart", vendor="codex")
    check(tok(c, lc) in context_of(out), "its SessionStart does carry the letter")
    check(json.loads(out)["hookSpecificOutput"]["hookEventName"] == "SessionStart",
          "…in the JSON OpenAI's own docs spell")


def load_postman(w):
    import importlib.util as _iu
    spec = _iu.spec_from_file_location("gate_postman_%d" % id(w),
                                       str(w["hub"] / "tools" / "postman.py"))
    mod = _iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# P6 — the waiter
# --------------------------------------------------------------------------

def waiter(w, to, title=None, extra=(), env=None):
    sid = (env or {}).get("CLAUDE_CODE_SESSION_ID")
    if title and sid and not (w["home"] / ".claude" / "projects" / "-gate-hub" / sid /
                              "custom-title.json").is_file():
        title_file(w, sid, title)                  # a titled window, as the app records one
    env_all = dict(os.environ)
    env_all["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in dict(w["env"], **(env or {})).items():
        env_all.pop(k, None) if v is None else env_all.__setitem__(k, str(v))
    args = [PY, str(w["hub"] / "tools" / "mail.py"), "--wait", to, "--hub", str(w["hub"])]
    if title:
        args += ["--title", title]
    args += list(extra)
    return subprocess.Popen(args, cwd=str(w["hub"]), env=env_all, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True)


def case_p6():
    start("P6", "the waiter: an idle session, woken, at zero tokens while silent")
    w = pworld("p6")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    write_json(w["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})
    proc = waiter(w, "NORTH/hub", HOLDER, env=as_session(SID_A))
    try:
        fyi = letter(w, "NORTH/hub", "NORTH FABLE woke at 09:00", "no reply needed — FYI")
        pm(w, "--pass", "--no-pull")
        time.sleep(6)
        check(proc.poll() is None, "an FYI line alone never ends the wait")
        one = letter(w, "NORTH/hub", "a cut order")
        pm(w, "--pass", "--no-pull")
        try:
            out, _ = proc.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(proc.returncode == 0, "it exits 0 the moment a letter wants an answer")
        check(tok(w, one) in out and tok(w, fyi) not in out,
              "…printing the asking letter — the FYI line stays queued for the next turn "
              "start (BQ-143 R3; it used to ride along)")
        check([i.get("token") for i in pending_of(w, SID_A)] == [tok(w, fyi)],
              "and what it carried is cleared, the FYI line left in place")
        rec = io.open(str(w["post"] / "receipts.jsonl"), encoding="utf-8").read()
        check('"road": "waiter"' in rec, "the receipt names the road it came by")
        ear = json.loads(io.open(str(w["hub"] / "ear-north-hub.json"), encoding="utf-8").read())
        check(ear.get("how") == "wait" and ear.get("every") == 60 and ear.get("session") == SID_A,
              "the ear says a waiter holds this mailbox: %s"
              % {k: ear.get(k) for k in ("how", "every", "session")})
    finally:
        if proc.poll() is None:
            proc.kill()

    start("P6b", "the waiter: the title goes off, the hours run out, the postman goes stale")
    t = pworld("p6b")
    claude_transcript(t, SID_A)
    write_json(t["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})
    write_json(t["hub"] / "live-north-fable.json",
               {"machine": "north", "mind": "FABLE", "when": iso(datetime.datetime.now().astimezone()),
                "sessions": [{"title": HOLDER, "effort": "EXTRA",
                              "when": iso(datetime.datetime.now().astimezone()), "session": SID_A}]})
    proc = waiter(t, "NORTH/hub", HOLDER, env=as_session(SID_A))
    try:
        armed(t, "NORTH/hub")
        write_json(t["hub"] / "live-north-fable.json",
                   {"machine": "north", "mind": "FABLE", "off": True, "sessions": [],
                    "when": iso(datetime.datetime.now().astimezone())})
        out, _ = proc.communicate(timeout=25)
        check("wait ended: %s is off" % HOLDER in out,
              "a wait ends itself when its own title is stamped off")
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "a wait ends itself when its own title is stamped off (it did not)")
    finally:
        if proc.poll() is None:
            proc.kill()

    h = pworld("p6c")
    claude_transcript(h, SID_A)
    write_json(h["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})
    proc = waiter(h, "NORTH/hub", None, extra=["--max-hours", "0.0005"], env=as_session(SID_A))
    try:
        out, _ = proc.communicate(timeout=30)
        check("arm it again" in out,
              "at --max-hours it says `arm it again` rather than dying quietly: %s"
              % out.strip().splitlines()[-1:])
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "--max-hours ends the wait (it did not)")
    finally:
        if proc.poll() is None:
            proc.kill()

    s = pworld("p6d")
    claude_transcript(s, SID_A)
    write_json(s["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone() - datetime.timedelta(hours=2)),
                "every": 60, "version": 1})
    proc = waiter(s, "NORTH/hub", None, env=as_session(SID_A))
    try:
        armed(s, "NORTH/hub")                        # after its own snapshot of the file
        one = letter(s, "NORTH/hub", "nothing has passed for two hours")
        out, _ = proc.communicate(timeout=40)
        check(one in out, "a stale postman makes the waiter carry its own address itself")
        check("has not passed" in out, "…and say so plainly: %s"
              % next((l for l in out.splitlines() if "has not passed" in l), ""))
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "a stale heartbeat degrades to the 2026-09-06 road (it did not)")
    finally:
        if proc.poll() is None:
            proc.kill()

    start("P6c", "the waiter: with no session identity it never guesses one")
    g = pworld("p6e")
    proc = waiter(g, "NORTH/hub", None)
    try:
        out, _ = proc.communicate(timeout=40)
        check("never arm blind" in out and "Exocortex-Desk" in out,
              "BQ-143 R1 replaced the one-shot watch: no session and no title is refused, "
              "never armed blind: %s" % out.strip().splitlines()[0:1])
        check(proc.returncode == 0 and len([l for l in out.splitlines() if l.strip()]) == 1,
              "…in ONE line, exit 0")
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "with no identity and no title the waiter refuses (it waited)")
    finally:
        if proc.poll() is None:
            proc.kill()


# --------------------------------------------------------------------------
# P7 — observation
# --------------------------------------------------------------------------

def case_p7():
    start("P7", "observation: delivered means SEEN, and one bad transcript holds up nothing")
    w = pworld("p7")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    path = claude_transcript(w, SID_A)
    filler = json.dumps({"type": "assistant", "sessionId": SID_A,
                         "message": {"content": "x" * 900}}, ensure_ascii=False)
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        for _ in range(3000):
            fh.write(filler + "\n")                  # ~2.7 MB of history
    one = letter(w, "NORTH/hub", "read me")
    counters = w["base"] / "counters.json"
    pm(w, "--pass", "--no-pull", "--counters", str(counters))
    first = json.loads(io.open(str(counters), encoding="utf-8").read())
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(claude_hook_context(SID_A, letter_context(w, one)),
                            ensure_ascii=False) + "\n")
    pm(w, "--pass", "--no-pull", "--counters", str(counters))
    second = json.loads(io.open(str(counters), encoding="utf-8").read())
    size = path.stat().st_size
    check(second["transcript_bytes"] < size / 4,
          "the second pass read %d bytes of a %d-byte transcript — a tail, never the file"
          % (second["transcript_bytes"], size))
    e = post_of(w)["letters"][tok(w, one)]
    check(e["state"] == "delivered" and e["delivered"]["evidence"] == "transcript",
          "the token in the holder's OWN transcript is the delivery: %s" % e["delivered"])

    u = pworld("p7b")
    plant_claim(u, "hub", "north", HOLDER, session=SID_A)
    plant_claim(u, "Alpha/One", "north", "ACT — Alpha/One: g", session=SID_B)
    bad = claude_transcript(u, SID_A)
    claude_transcript(u, SID_B)
    la = letter(u, "NORTH/hub", "for the session whose transcript will not open")
    lb = letter(u, "NORTH/Alpha-One", "for the one that is fine")
    pm(u, "--pass", "--no-pull")
    os.chmod(str(bad), 0o000)
    try:
        code, out = pm(u, "--pass", "--no-pull")
        e = post_of(u)["letters"][tok(u, la)]
        check("transcript could not be read" in e["why"],
              "an unreadable transcript makes THAT letter say why: %s" % e["why"])
        check(post_of(u)["letters"][tok(u, lb)]["state"] == "waiting" and code == 0,
              "…and every other letter proceeds, the pass still exiting 0")
    finally:
        os.chmod(str(bad), 0o600)


# --------------------------------------------------------------------------
# P8 — the sender's duties
# --------------------------------------------------------------------------

def case_p8():
    start("P8", "the sender is never left in silence")
    w = pworld("p8")
    claude_transcript(w, SID_A)
    plant_claim(w, "hub", "north", HOLDER, session=SID_B)   # an idle holder with no ear
    claude_transcript(w, SID_B)
    env = as_session(SID_A)
    mp(w, "--send", "NORTH/hub", "Exocortex", "cut the payload", "reply when done",
       "--no-push", env=env)
    code, out = pm(w, "--pass", "--no-pull")
    check("not read yet" not in out, "a letter inside the five minutes earns nothing at all")
    later = iso(datetime.datetime.now().astimezone() + datetime.timedelta(minutes=7))
    code, out = pm(w, "--pass", "--no-pull", "--now", later)
    line = next((l for l in out.splitlines() if l.startswith("POST —")), "")
    check("is not read yet (7 min)" in line and "idle with no ear" in line,
          "past five minutes the sender is told ONCE, with the why: %s" % line)
    check(any(i["kind"] == "notice" for i in pending_of(w, SID_A)),
          "…and the notice is queued for the SENDING session, not printed into the void")
    code, out = pm(w, "--pass", "--no-pull", "--now", later)
    check("not read yet" not in out, "told once, and never again")

    letters_ = [i for i in pending_of(w, SID_A) if i["kind"] == "letter"]
    hook(w, SID_A, "UserPromptSubmit")                    # the sender reads its own notice
    sent_line = [l for l in io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read().splitlines()
                 if "cut the payload" in l][0]
    claude_transcript(w, SID_B, [claude_hook_context(SID_B, letter_context(w, sent_line))])
    code, out = pm(w, "--pass", "--no-pull", "--now", later)
    line = next((l for l in out.splitlines() if "has now been read" in l), "")
    check(line.startswith("POST — your letter to NORTH/hub of ") and "min after you sent it" in line,
          "a letter read after such a notice earns ONE `has now been read`: %s" % line)
    code, out = pm(w, "--pass", "--no-pull", "--now", later)
    check("has now been read" not in out, "…and only one")

    q = pworld("p8b")
    claude_transcript(q, SID_A)
    plant_claim(q, "hub", "north", HOLDER, session=SID_B)
    claude_transcript(q, SID_B)
    mp(q, "--send", "NORTH/hub", "Exocortex", "NORTH FABLE woke at 09:00",
       "no reply needed — FYI", "--no-push", env=as_session(SID_A))
    later = iso(datetime.datetime.now().astimezone() + datetime.timedelta(hours=1))
    code, out = pm(q, "--pass", "--no-pull", "--now", later)
    check("POST —" not in out, "an FYI letter never reports, however long it waits")

    a = pworld("p8c")
    claude_transcript(a, SID_A)
    mp(a, "--send", "NOWHERE/hub", "Exocortex", "into the dark", "answer", "--no-push",
       env=as_session(SID_A))
    pm(a, "--pass", "--no-pull")
    notices = [i["text"] for i in pending_of(a, SID_A) if i["kind"] == "notice"]
    check(any("no machine named NOWHERE is in the fleet" in n for n in notices),
          "an unknown machine is told at once, not at five minutes: %s" % (notices or "(none)"))

    s = pworld("p8d")
    claude_transcript(s, SID_A)
    plant_claim(s, "Alpha/One", "south", "ACT — Alpha/One: south", session="south-1")
    write_json(s["hub"] / "live-sessions-south.json",
               {"machine": "south", "when": iso(datetime.datetime.now().astimezone()),
                "sessions": [],
                "postman": {"last_pass": iso(datetime.datetime.now().astimezone()
                                             - datetime.timedelta(hours=3)), "every": 60}})
    mp(s, "--send", "NORTH/Alpha-One", "Alpha", "for the other machine", "answer", "--no-push",
       env=as_session(SID_A))
    pm(s, "--pass", "--no-pull")
    notices = [i["text"] for i in pending_of(s, SID_A) if i["kind"] == "notice"]
    check(any("postman has not run since" in n for n in notices),
          "a machine whose own pass has stopped is named, not blamed on the holder: %s"
          % (notices or "(none)"))


# --------------------------------------------------------------------------
# P9 — pass discipline
# --------------------------------------------------------------------------

def case_p9():
    start("P9", "the pass: quiet when there is nothing to say, and safe to rerun")
    w = pworld("p9")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    one = letter(w, "NORTH/hub", "one letter")
    pm(w, "--pass", "--no-pull")
    before = io.open(str(w["hub"] / "post-north.json"), encoding="utf-8").read()
    calls = w["home"] / "orchestrator-sync" / "sync-calls.log"
    pushes = io.open(str(calls), encoding="utf-8").read().count("push") if calls.is_file() else 0
    code, out = pm(w, "--pass", "--no-pull")
    after = io.open(str(w["hub"] / "post-north.json"), encoding="utf-8").read()
    now_pushes = io.open(str(calls), encoding="utf-8").read().count("push") if calls.is_file() else 0
    check(before == after, "a second pass with nothing new writes the post file not one byte")
    check(now_pushes == pushes, "…and asks the brain for no push at all")
    check(out.strip() == "", "…and says nothing")

    write_json(w["post"] / "pass.lock", {"pid": 1, "when": iso(datetime.datetime.now().astimezone())})
    two = letter(w, "NORTH/hub", "while another pass holds the lock")
    code, out = pm(w, "--pass", "--no-pull")
    check(code == 0 and out.strip() == "", "a second pass beside a live one exits 0, silent")
    check(not any(i["token"] == tok(w, two) for i in pending_of(w, SID_A)),
          "…and does no work")
    write_json(w["post"] / "pass.lock",
               {"pid": 1, "when": iso(datetime.datetime.now().astimezone()
                                      - datetime.timedelta(minutes=30))})
    pm(w, "--pass", "--no-pull")
    check(any(i["token"] == tok(w, two) for i in pending_of(w, SID_A)),
          "a lock left behind by a killed pass is taken over after five minutes")

    start("P9b", "the pass: INBOX read incrementally, and a merge that rewrites it")
    b = pworld("p9b")
    plant_claim(b, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(b, SID_A)
    with io.open(str(b["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        for n in range(6400):
            fh.write("- 2026-09-01 · to: NORTH/other · Exocortex · an old line number %04d "
                     "· no reply needed — FYI\n" % n)
    size = (b["hub"] / "INBOX.md").stat().st_size
    counters = b["base"] / "counters.json"
    pm(b, "--pass", "--no-pull", "--counters", str(counters))
    check(size > 500000, "the fixture INBOX is %d bytes, the size of the real one" % size)
    fresh = letter(b, "NORTH/hub", "one line appended to a 600 KB mailbox")
    pm(b, "--pass", "--no-pull", "--counters", str(counters))
    c = json.loads(io.open(str(counters), encoding="utf-8").read())
    check(c["inbox_bytes"] < 20000,
          "the second pass read %d bytes of it — only what was appended" % c["inbox_bytes"])
    check(any(i["token"] == tok(b, fresh) for i in pending_of(b, SID_A)),
          "…and still found the new letter")
    # a merge rewrites the file: the head changes, so it is re-parsed whole
    text = io.open(str(b["hub"] / "INBOX.md"), encoding="utf-8").read()
    write(b["hub"] / "INBOX.md", "# INBOX (merged by the other machine)\n\n" + text.split("\n", 2)[2])
    hook(b, SID_A, "UserPromptSubmit")
    pm(b, "--pass", "--no-pull", "--counters", str(counters))
    c2 = json.loads(io.open(str(counters), encoding="utf-8").read())
    check(c2["inbox_bytes"] > 400000, "a rewritten head makes ONE full re-parse (%d bytes)"
          % c2["inbox_bytes"])
    check(not pending_of(b, SID_A),
          "…and redelivers nothing: a token delivered once is never delivered again")


# --------------------------------------------------------------------------
# P10 — --mark
# --------------------------------------------------------------------------

def case_p10():
    start("P10", "--mark: the sweep of 2026-09-18, replayed")
    w = pworld("p10")
    first = letter(w, "NORTH/hub", "the line the reader actually saw")
    code, out = mp(w, "--read", "NORTH/hub", "--title", HOLDER)
    check(out.count("MAIL:") == 1 and tok(w, first) in out,
          "the read prints the letter, with its token")
    second = letter(w, "NORTH/hub", "a letter that landed between the read and the mark")
    code, out = mp(w, "--read", "NORTH/hub", "--mark", HOLDER)
    check("NEW — read it; the next --mark takes it" in out,
          "the newcomer is PRINTED, not marked: %s"
          % next((l for l in out.splitlines() if l.startswith("NEW")), ""))
    check("marked 1 delivered" in out, "…and exactly the one line the reader had seen is marked")
    text = io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read()
    check(" · delivered:" in [l for l in text.splitlines() if first in l][0],
          "the first letter carries its delivery stamp")
    check(" · delivered:" not in [l for l in text.splitlines() if second in l][0],
          "and the newcomer does not — it survives the mark")
    code, out = mp(w, "--read", "NORTH/hub", "--mark", HOLDER)
    check("marked 1 delivered" in out, "the next --mark takes it, exactly as the line promised")

    f = pworld("p10b")
    one = letter(f, "NORTH/hub", "no earlier read at all")
    code, out = mp(f, "--read", "NORTH/hub", "--mark", HOLDER)
    check("marked 1 delivered" in out and "NEW —" not in out,
          "with no earlier record it behaves as one-call --read --mark always did")


# --------------------------------------------------------------------------
# P11 — expiry
# --------------------------------------------------------------------------

def case_p11():
    start("P11", "expiry: nobody is woken by last week's letter")
    w = pworld("p11")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    fyi = letter(w, "NORTH/hub", "NORTH FABLE woke at 08:00", "no reply needed — FYI")
    real = letter(w, "NORTH/hub", "an order nobody answered")
    pm(w, "--pass", "--no-pull")
    hook(w, SID_A, "UserPromptSubmit")                  # take them out of pending
    later = iso(datetime.datetime.now().astimezone() + datetime.timedelta(hours=13))
    pm(w, "--pass", "--no-pull", "--now", later)
    body = post_of(w)["letters"]
    check(body[tok(w, fyi)]["state"] in ("expired", "delivered"),
          "an FYI letter is done with after twelve hours: %s" % body[tok(w, fyi)]["state"])
    x = pworld("p11b")
    plant_claim(x, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(x, SID_A)
    old = letter(x, "NORTH/hub", "an order from last week")
    fyi = letter(x, "NORTH/hub", "an old arrival line", "no reply needed — FYI")
    pm(x, "--pass", "--no-pull")
    check(len(pending_of(x, SID_A)) == 2, "both letters are waiting for the holder on day one")
    way_later = iso(datetime.datetime.now().astimezone() + datetime.timedelta(days=8))
    pm(x, "--pass", "--no-pull", "--now", way_later)
    body = post_of(x)["letters"]
    check(body[tok(x, old)]["state"] == "expired" and body[tok(x, fyi)]["state"] == "expired",
          "a letter older than seven days expires unread, and is never delivered")
    check(not pending_of(x, SID_A), "…and nothing was queued for anyone")


# --------------------------------------------------------------------------
# P12 — --install-hooks
# --------------------------------------------------------------------------

FOREIGN_SETTINGS = """{
  "permissions": {
    "allow": [
      "Bash(ls:*)"
    ]
  },
  "model": "opus[1m]",
  "hooks": {
    "Notification": [
      {
        "matcher": "idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "%s/.claude/ccnotifier-hook.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "%s/.claude/ccnotifier-hook.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "%s/.claude/ccnotifier-hook.sh"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "%s/.claude/ccnotifier-hook.sh"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "%s/.claude/ccnotifier-hook.sh"
          }
        ]
      }
    ]
  },
  "theme": "auto"
}
"""


def case_p12():
    start("P12", "--install-hooks: merged beside another tool's, idempotent, reversible")
    w = pworld("p12")
    target = w["home"] / ".claude" / "settings.json"
    write(target, FOREIGN_SETTINGS % ((str(w["home"]),) * 5))
    before = io.open(str(target), encoding="utf-8").read()
    code, out = pm(w, "--install-hooks", "--vendor", "claude", "--dry", "--settings", str(target))
    check(io.open(str(target), encoding="utf-8").read() == before, "--dry writes nothing at all")
    check(out.count("would add") == 4 and "timeout 5s" in out,
          "it prints exactly what it would add, each with its 5 s timeout (%d)"
          % out.count("would add"))
    code, out = pm(w, "--install-hooks", "--vendor", "claude", "--settings", str(target))
    one = io.open(str(target), encoding="utf-8").read()
    data = json.loads(one)
    ours = [(ev, h) for ev, rows in data["hooks"].items() for r in rows
            for h in r.get("hooks", []) if "postman.py" in h["command"]]
    theirs = [(ev, h) for ev, rows in data["hooks"].items() for r in rows
              for h in r.get("hooks", []) if "ccnotifier" in h["command"]]
    check(len(ours) == 4 and all(h.get("timeout") == 5 for _e, h in ours),
          "four entries went in, each with timeout 5")
    check(len(theirs) == 5, "…beside all five of the other tool's, not one of them touched")
    check(list(data) == list(json.loads(before)), "the file's own key order is kept")
    check(one.splitlines()[1].startswith("  \""), "…and its indentation")
    check(json.loads(before)["hooks"]["Notification"] == data["hooks"]["Notification"],
          "a foreign event's entries are byte-for-byte what they were")
    code, out = pm(w, "--install-hooks", "--vendor", "claude", "--settings", str(target))
    check(io.open(str(target), encoding="utf-8").read() == one and "already installed" in out,
          "a second run is idempotent: nothing added, nothing written")
    backups = sorted((w["post"] / "backups").glob("*.json"))
    check(backups and io.open(str(backups[0]), encoding="utf-8").read() == before,
          "the file as it stood is kept in POST DIR")
    code, out = pm(w, "--uninstall-hooks", "--vendor", "claude", "--settings", str(target))
    check(json.loads(io.open(str(target), encoding="utf-8").read()) == json.loads(before),
          "the uninstall removes only its own entries and leaves the file as it was")

    b = pworld("p12b")
    bad = b["home"] / ".claude" / "settings.json"
    write(bad, "{ this is not json ")
    code, out = pm(b, "--install-hooks", "--vendor", "claude", "--settings", str(bad))
    check("REFUSED" in out and "not valid JSON" in out,
          "a settings file that will not parse is refused in one sentence: %s"
          % next((l for l in out.splitlines() if "REFUSED" in l), ""))
    check(io.open(str(bad), encoding="utf-8").read() == "{ this is not json ",
          "…and nothing is written")

    c = pworld("p12c")
    carried = c["home"] / ".codex" / "AGENTS.md"
    carried.parent.mkdir(parents=True, exist_ok=True)
    write(carried, "# the brain carries this one\n")
    write_json(c["home"] / "orchestrator-sync" / "sync-manifest.json",
               {"machines": {"north": {}, "south": {}},
                "entries": [{"id": "codex-agents-md", "kind": "file",
                             "live": {"rel": "AGENTS.md", "root": "codex"},
                             "repo": "codex-home/AGENTS.md"},
                            {"id": "settings-reference", "kind": "file", "mode": "report-only",
                             "live": {"rel": "settings.json", "root": "claude"},
                             "repo": "claude-home/settings.reference.json"}]})
    code, out = pm(c, "--install-hooks", "--vendor", "codex", "--settings", str(carried))
    check("REFUSED" in out and "codex-home/AGENTS.md" in out,
          "a hooks file the brain CARRIES is refused by name: %s"
          % next((l for l in out.splitlines() if "REFUSED" in l), ""))
    check(io.open(str(carried), encoding="utf-8").read() == "# the brain carries this one\n",
          "…and is not written")
    settings = c["home"] / ".claude" / "settings.json"
    write(settings, FOREIGN_SETTINGS % ((str(c["home"]),) * 5))
    code, out = pm(c, "--install-hooks", "--vendor", "claude", "--dry", "--settings", str(settings))
    check("REFUSED" not in out and out.count("would add") == 4,
          "a report-only entry does NOT carry: the sync shows its drift and never writes it")

    d = pworld("p12d")
    hooks = d["home"] / ".codex" / "hooks.json"
    code, out = pm(d, "--install-hooks", "--vendor", "codex", "--settings", str(hooks))
    data = json.loads(io.open(str(hooks), encoding="utf-8").read())
    check(sorted(data["hooks"]) == ["SessionStart", "Stop"],
          "Codex gets its own hooks.json, with ONLY the events its docs settle: %s"
          % sorted(data["hooks"]))
    check("PreToolUse" in out and "parent session id" in out,
          "…and the reason the others are off is said aloud, never hidden")


# --------------------------------------------------------------------------
# P13 — the pulse
# --------------------------------------------------------------------------

def case_p13():
    start("P13", "the pulse: one failure-safe call a beat, and no churn in the brain")
    w = pworld("p13")
    for extra in ("pulse.py", "grok_sessions.py"):
        src = source_tool(extra)
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / "tools" / extra))
    if not (w["hub"] / "tools" / "pulse.py").is_file():
        skip("pulse.py is not beside this gate and not in the hub — the pulse case could not run")
        return
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    one = letter(w, "NORTH/hub", "carried by the beat, not by the job")
    code, out = run([PY, "-c",
                     "import importlib.util as u, sys;"
                     "s=u.spec_from_file_location('p', %r);m=u.module_from_spec(s);"
                     "s.loader.exec_module(m);"
                     "print('\\n'.join(m._postman(sys.executable, m.Path(%r))))"
                     % (str(w["hub"] / "tools" / "pulse.py"), str(w["hub"]))],
                    cwd=str(w["hub"]), env=w["env"])
    check(code == 0, "the pulse's call runs and the beat survives it")
    check(any(i["token"] == tok(w, one) for i in pending_of(w, SID_A)),
          "…and the letter moved without any scheduled job at all")
    os.replace(str(w["hub"] / "tools" / "postman.py"), str(w["hub"] / "tools" / "postman.off"))
    code, out = run([PY, "-c",
                     "import importlib.util as u, sys;"
                     "s=u.spec_from_file_location('p', %r);m=u.module_from_spec(s);"
                     "s.loader.exec_module(m);"
                     "print(repr(m._postman(sys.executable, m.Path(%r))));"
                     "print(repr(m._postman_beat(m.Path(%r))))"
                     % (str(w["hub"] / "tools" / "pulse.py"), str(w["hub"]), str(w["hub"]))],
                    cwd=str(w["hub"]), env=w["env"])
    check(code == 0 and "[]" in out, "no postman on this machine is silence, never a failed beat")
    os.replace(str(w["hub"] / "tools" / "postman.off"), str(w["hub"] / "tools" / "postman.py"))
    beat = json.loads(io.open(str(w["post"] / "heartbeat.json"), encoding="utf-8").read())
    check(beat.get("when") and beat.get("every") == 60,
          "the heartbeat is machine-personal and says when and how often: %s" % beat)
    check(not list(w["hub"].glob("heartbeat.json")),
          "…and never sits in the hub, where the brain would carry its moving timestamp")
    code, out = run([PY, "-c",
                     "import importlib.util as u;"
                     "s=u.spec_from_file_location('p', %r);m=u.module_from_spec(s);"
                     "s.loader.exec_module(m);"
                     "m.sense('north', {'claude': %r, 'codex': %r}, m.Path(%r))"
                     % (str(w["hub"] / "tools" / "pulse.py"), str(w["home"] / ".claude"),
                        str(w["home"] / ".codex"), str(w["hub"]))],
                    cwd=str(w["hub"]), env=w["env"])
    live = json.loads(io.open(str(w["hub"] / "live-sessions-north.json"), encoding="utf-8").read())
    check(code == 0 and (live.get("postman") or {}).get("last_pass") == beat["when"],
          "the pulse copies its age into a file it already writes each beat: %s"
          % live.get("postman"))


# --------------------------------------------------------------------------
# P14 — regressions, actually run
# --------------------------------------------------------------------------

def regression_world(name):
    """A scratch world complete enough for the OTHER gates to run in: their own
    tools, the hub's root-level modules, one scratch project and the two files the
    tree page reads. Everything comes from the record; nothing live is written."""
    w = world(name, tree=True)
    for extra in ("who-is-live.py", "gate-coordination.py", "gate-tree-answers.py",
                  "improvements.py", "asked.py", "ideas.py"):
        src = source_tool(extra)
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / "tools" / extra))
    for root_file in ("orchestrator.py", "evidence.py"):
        src = real_hub() / root_file
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / root_file))
    write(w["hub"] / "STATUS.md", "# STATUS\n\n## Now\n\nthe gate's own hub.\n\n"
                                  "## To do\n\n- [ ] one item\n")
    write(w["hub"] / "TREE.md", "<!-- tree:auto-start -->\n<!-- tree:auto-end -->\n")
    write(w["projects"] / "scratch-project" / "STATUS.md",
          "# STATUS\n\n## Now\n\nsomething for the tree to draw.\n\n## To do\n\n- [ ] one item\n")
    return w


# A gate's own count line: the one proof that it ran to its end.
COUNT_LINE = re.compile(r"\d+ checks · \d+ passed · \d+ failed")


def case_p14():
    start("P14", "regressions: the gates that touch these tools, rerun against the built files")
    src = source_tool("gate-coordination.py")
    if not src.is_file():
        skip("gate-coordination.py is neither beside this gate nor in the hub — NOT RUN")
    else:
        w = regression_world("p14-coord")
        code, out = run([PY, str(w["hub"] / "tools" / "gate-coordination.py"), "--skip-g3"],
                        cwd=str(w["hub"]), env=w["env"], timeout=900)
        counted = COUNT_LINE.search(out)
        tail = next((l.strip() for l in out.splitlines() if "checks ·" in l), out[-160:])
        # A child that dies on an import prints no FAIL at all: it passes only by
        # its own count line, which a gate that never ran cannot print.
        check(code == 0 and counted is not None,
              "gate-coordination.py passes with the new keys in the claims and "
              "stamps, and the BQ-025 cases in it: %s" % tail)

    src = source_tool("gate-tree-answers.py")
    if not src.is_file():
        skip("gate-tree-answers.py is neither beside this gate nor in the hub — NOT RUN")
        return
    w = regression_world("p14-tree")
    code, out = run([PY, str(w["hub"] / "tools" / "gate-tree-answers.py"),
                     str(w["hub"] / "tools" / "collect-openers.py")],
                    cwd=str(w["hub"]), env=w["env"], timeout=900)
    fails = [l.strip() for l in out.splitlines() if l.strip().startswith("FAIL ")]
    outside = [l for l in fails if "G13 the real hub" not in l]
    tail = next((l.strip() for l in out.splitlines() if "passed" in l), "")
    counted = COUNT_LINE.search(out)
    check(counted is not None and not outside,
          "gate-tree-answers.py: the ears and claims with the new keys still draw — "
          "%d failure(s) outside G13: %s" % (len(outside), outside[:2] or "none")
          if counted is not None else
          "gate-tree-answers.py ran to its count line — it printed none: %s" % out[-200:])
    if fails:
        skip("gate-tree-answers G13 'the real hub' wants this machine's own memories, "
             "journal, laws, sky, dossier and skills, which a scratch HOME does not "
             "have: %d checks in that one case could not run (%s)" % (len(fails), tail))
    check("gate-buttonup" not in out, "gate-buttonup.py was not touched by this build at all")


# --------------------------------------------------------------------------
# P15 — permissions: never loosen a file, never widen a folder
# --------------------------------------------------------------------------

def mode_of(path):
    return os.stat(str(path)).st_mode & 0o7777


def case_p15():
    start("P15", "permissions: a file this build writes is never more readable than it was")
    if os.name == "nt":
        skip("Windows has no POSIX mode bits — the permission assertions cannot run here, "
             "and are NOT claimed. The South proves the install another way (§11 L6).")
        return
    w = pworld("p15")
    target = w["home"] / ".claude" / "settings.json"
    write(target, FOREIGN_SETTINGS % ((str(w["home"]),) * 5))
    os.chmod(str(target), 0o600)                       # this North's real mode today
    before = io.open(str(target), encoding="utf-8").read()
    pm(w, "--install-hooks", "--vendor", "claude", "--settings", str(target))
    check(mode_of(target) == 0o600,
          "an EXISTING settings file keeps its own 0600 through the install (found %o)"
          % mode_of(target))
    backups = sorted((w["post"] / "backups").glob("*"))
    check(backups and all(mode_of(b) == 0o600 for b in backups),
          "…and the backup copy of it is 0600 too (%s)"
          % [oct(mode_of(b)) for b in backups])
    pm(w, "--uninstall-hooks", "--vendor", "claude", "--settings", str(target))
    check(mode_of(target) == 0o600, "and it is STILL 0600 after the uninstall (found %o)"
          % mode_of(target))
    check(io.open(str(target), encoding="utf-8").read() == before,
          "…with its content back to exactly what it was")

    odd = w["home"] / ".claude" / "settings-0640.json"
    write(odd, FOREIGN_SETTINGS % ((str(w["home"]),) * 5))
    os.chmod(str(odd), 0o640)
    pm(w, "--install-hooks", "--vendor", "claude", "--settings", str(odd))
    check(mode_of(odd) == 0o640,
          "a file the user has set to 0640 is left at 0640 — the FILE's mode wins, not ours")

    hooks = w["home"] / ".codex" / "hooks.json"
    pm(w, "--install-hooks", "--vendor", "codex", "--settings", str(hooks))
    check(hooks.is_file() and mode_of(hooks) == 0o600,
          "a hooks file this build CREATES is 0600 — this account's alone (found %s)"
          % (oct(mode_of(hooks)) if hooks.is_file() else "no file"))

    start("P15b", "permissions: POST DIR is private, and only brain files are 0644")
    x = pworld("p15b")
    plant_claim(x, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(x, SID_A)
    one = letter(x, "NORTH/hub", "a letter is a person's working note")
    shutil.rmtree(str(x["post"]), ignore_errors=True)   # let the pass make POST DIR itself
    pm(x, "--pass", "--no-pull")
    check(mode_of(x["post"]) == 0o700,
          "POST DIR is made 0700 — another account has no business in the mail (found %o)"
          % mode_of(x["post"]))
    subdirs = [d for d in sorted(x["post"].iterdir()) if d.is_dir()]
    check(subdirs and all(mode_of(d) == 0o700 for d in subdirs),
          "…and every folder inside it: %s"
          % [(d.name, oct(mode_of(d))) for d in subdirs])
    files = [f for f in sorted(x["post"].rglob("*")) if f.is_file()]
    loose = [(str(f.relative_to(x["post"])), oct(mode_of(f))) for f in files if mode_of(f) != 0o600]
    check(files and not loose,
          "every file inside POST DIR is 0600 (%d files, %d looser: %s)"
          % (len(files), len(loose), loose[:4]))
    hook(x, SID_A, "UserPromptSubmit")                  # the receipts file's first write
    rec = x["post"] / "receipts.jsonl"
    check(rec.is_file() and mode_of(rec) == 0o600,
          "the receipts a road appends to are 0600 from their first line (found %s)"
          % (oct(mode_of(rec)) if rec.is_file() else "no file"))
    post = x["hub"] / "post-north.json"
    check(post.is_file() and mode_of(post) == 0o644,
          "post-<machine>.json IS a brain file and stays 0644, as the stamps are (found %s)"
          % (oct(mode_of(post)) if post.is_file() else "no file"))
    os.chmod(str(x["post"]), 0o755)                    # a POST DIR the user already made open
    code, out = pm(x, "--pass", "--no-pull")
    check("is readable beyond this account (755)" in out,
          "a POST DIR that was ALREADY open is said, not silently changed: %s"
          % next((l for l in out.splitlines() if "readable beyond" in l), "(nothing)"))
    check(mode_of(x["post"]) == 0o755,
          "…and its mode is left exactly as the user set it — the choice stays theirs")
    os.chmod(str(x["post"]), 0o700)
    code, out = pm(x, "--pass", "--no-pull")
    check("readable beyond" not in out, "a private POST DIR says nothing at all about itself")

    start("P15c", "permissions: --mark leaves INBOX.md exactly as private as it found it")
    m = pworld("p15c")
    one = letter(m, "NORTH/hub", "a letter to mark")
    os.chmod(str(m["hub"] / "INBOX.md"), 0o600)
    mp(m, "--read", "NORTH/hub", "--title", HOLDER)
    letter(m, "NORTH/hub", "and one that lands after the read")
    mp(m, "--read", "NORTH/hub", "--mark", HOLDER)
    check(mode_of(m["hub"] / "INBOX.md") == 0o600,
          "a 0600 INBOX.md is still 0600 after a --mark rewrote it (found %o)"
          % mode_of(m["hub"] / "INBOX.md"))
    os.chmod(str(m["hub"] / "INBOX.md"), 0o644)
    letter(m, "NORTH/hub", "a third letter")
    mp(m, "--read", "NORTH/hub", "--mark", HOLDER)
    check(mode_of(m["hub"] / "INBOX.md") == 0o644,
          "…and a 0644 one is still 0644: the file's mode is the file's, never the tool's")


# --------------------------------------------------------------------------
# P16 — a session id becomes a file name
# --------------------------------------------------------------------------

BAD_IDS = ("../x", "/etc/passwd", "..", ".", "", "a/b", "x" * 300, "with space",
           "back\\slash", "null\x00byte")


def case_p16():
    start("P16", "a session id becomes a file name, so it is checked before it is one")
    w = pworld("p16")
    pmod = load_postman(w)
    for bad in BAD_IDS:
        check(not pmod.safe_session_id(bad), "refused as a file name: %r" % bad)
    for good in (SID_A, TID_C, "local_abc.123", "A" * 128):
        check(pmod.safe_session_id(good), "accepted, a plain token: %r" % good[:24])
    check(not pmod.safe_session_id("A" * 129), "…and 129 characters is one too many")

    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    one = letter(w, "NORTH/hub", "a letter for a real session")
    pm(w, "--pass", "--no-pull")
    before = sorted(p.name for p in (w["post"] / "pending").glob("*"))
    outside = sorted(p.name for p in w["post"].iterdir())

    for bad in ("../x", "/etc/passwd", "", "y" * 300):
        code, out, err = hook(w, bad, "UserPromptSubmit")
        check(code == 0 and out == "",
              "the hook carrying %r delivers nothing and exits 0" % (bad[:16] or "(empty)"))
    check(sorted(p.name for p in (w["post"] / "pending").glob("*")) == before,
          "…and not one file was made or taken in pending/")
    # hook-errors.log IS the designed output of a refusal (one bounded line); it is
    # the ONLY thing a bad id may leave behind.
    appeared = [n for n in sorted(p.name for p in w["post"].iterdir())
                if n not in outside and n != "hook-errors.log"]
    check(not appeared, "…and nothing but its own error log appeared in POST DIR: %s"
          % (appeared or "nothing"))
    check(not (w["base"] / "x").exists() and not (w["post"].parent / "x").exists(),
          "nothing was written outside POST DIR by `../x`")
    log = w["post"] / "hook-errors.log"
    check(log.is_file() and "not a plain token" in io.open(str(log), encoding="utf-8").read(),
          "the hook says why in its own bounded log, and nowhere else")

    start("P16b", "…and the pass refuses one too, in one plain line")
    x = pworld("p16b")
    plant_claim(x, "hub", "north", HOLDER, session="../../etc/whatever")
    lb = letter(x, "NORTH/hub", "addressed to a lane whose holder has an unusable id")
    code, out = pm(x, "--pass", "--no-pull")
    check("ignored an unusable session id for NORTH/hub" in out,
          "it says so in one line: %s"
          % next((l for l in out.splitlines() if "unusable" in l), "(nothing)"))
    check(not list((x["post"] / "pending").glob("*")) if (x["post"] / "pending").is_dir() else True,
          "…and queues nothing at all")
    e = post_of(x)["letters"][tok(x, lb)]
    check(e["state"] == "waiting" and "not a plain token" in e["why"],
          "the letter waits, and its why says what is wrong: %s" % e["why"])
    check(not (x["base"] / "etc").exists(), "nothing was written up and out of POST DIR")


# ==========================================================================
# PB15 … PB24 — THE POSTMAN'S SURFACES (phase B, cases P15–P24)
#
# Phase B numbers these P15…P24; phase A already carries a P15 (permissions)
# and a P16 (a session id becomes a file name), both green and untouched, so
# they are named PB15…PB24 here and each case says which phase B case it is.
# ==========================================================================

NASTY = 'a "quote" and a \'tick\' and a `back` and $(sub) and a \\slash and \U0001f642'
OWNER_NOTE = "the gate line printed: LANDED DM-TX-020"


def bworld(name, machine="north", fleet=("north", "south"), brain=None, prime=True, live=True,
           base_dir=None):
    """A world with a postman AND a plausible human at the machine: the pulse's
    own live-sessions file, which is what `anyone_here` reads."""
    w = pworld(name, machine=machine, fleet=fleet, brain=brain, prime=prime, base_dir=base_dir)
    if live:
        plant_live(w, [SID_A])
    return w


def plant_live(w, ids=(), minutes=1.0, window=10):
    write_json(w["hub"] / ("live-sessions-%s.json" % w["machine"]),
               {"machine": w["machine"], "when": iso(datetime.datetime.now().astimezone()),
                "live_minutes": window,
                "sessions": [{"id": sid, "dir": "-gate-hub", "kind": "claude", "mind": "FABLE",
                              "model": "claude-fable-5-1", "cwd": str(w["hub"]),
                              "in_hub": True, "minutes_ago": minutes} for sid in ids]})


def owner_of(w, token, machine=None):
    e = post_of(w, machine)["letters"].get(token) or {}
    return e.get("owner") or {}


def nudges_of(w, machine=None):
    return post_of(w, machine).get("nudges") or {}


def push_records(w, sid, message, result="Mobile push requested.", use_id="toolu_01GATE"):
    """The two records a REAL PushNotification call leaves in a Claude Code
    transcript, in the shape a real transcript carries them."""
    claude_transcript(w, sid, [
        {"type": "assistant", "sessionId": sid, "uuid": "p1",
         "timestamp": "2026-09-20T21:41:00.000Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "id": use_id, "name": "PushNotification",
              "input": {"message": message, "status": "proactive"},
              "caller": {"type": "direct"}}]}},
        {"type": "user", "sessionId": sid, "uuid": "p2", "isSidechain": False,
         "timestamp": "2026-09-20T21:41:01.000Z",
         "message": {"role": "user", "content": [
             {"tool_use_id": use_id, "type": "tool_result", "content": result}]}}])


def state_of(w):
    return json.loads(io.open(str(w["post"] / "state.json"), encoding="utf-8").read())


def write_state(w, body):
    write(w["post"] / "state.json", json.dumps(body, ensure_ascii=False, indent=1) + "\n")


def pmn(w, *args, **kw):
    """A pass with the notifier's seam on the flag as well as in the world's env."""
    return pm(w, *(list(args) + ["--notify", str(w["notify"])]), **kw)


def later(minutes=0, hours=0):
    return iso(datetime.datetime.now().astimezone()
               + datetime.timedelta(minutes=minutes, hours=hours))


def facts_via(w, hub=None):
    """`tree_facts()` as the PAGE GENERATOR calls it, in a process whose HOME is
    the world's — so every question it asks of the record (`is_own_hub`, POST
    DIR, the install marker) is answered from the world's own machine.json and
    never from the machine this gate happens to run on."""
    code, out = run([PY, str(w["base"] / "treefacts.py"),
                     str(w["hub"] / "tools" / "postman.py"), str(hub or w["hub"])],
                    cwd=str(w["hub"]), env=w["env"])
    try:
        return json.loads([l for l in out.splitlines() if l.strip().startswith("{")][-1])
    except Exception:
        return {"raw": out}


def install_marker(w, when=None):
    """The word said at this machine, in the shape `--install-hooks` writes."""
    write_json(w["post"] / "installed.json",
               {"when": when or iso(datetime.datetime.now().astimezone()),
                "vendors": ["claude"], "hub": str(w["hub"])})


def uninstall_marker(w):
    """…and a machine where nobody ever said it."""
    try:
        os.unlink(str(w["post"] / "installed.json"))
    except OSError:
        pass


def age_file(path, seconds):
    """A fixture file's own mtime, set back — how a window that has taken no
    turn since yesterday is stood up on a machine that booted this minute."""
    when = time.time() - float(seconds)
    os.utime(str(path), (when, when))


# --------------------------------------------------------------------------
# PB15 (phase B P15) — a note's life
# --------------------------------------------------------------------------

def case_pb15():
    start("PB15", "a note for Wren: raised here exactly once, and never for the wrong reason")
    w = bworld("pb15")
    pmod = load_postman(w)

    # the notifier is handed the texts as DATA — the script source holds none of them
    how, err = pmod.raise_note("Exocortex", "Alpha", NASTY + "\nsecond line",
                               notify=str(w["notify"]))
    check(how == "osascript" or how == "toast",
          "the raise goes by this machine's own notifier: %r %r" % (how, err))
    got = raises(w)
    check(len(got) == 1, "exactly one notification was raised (%d)" % len(got))
    if got:
        check(got[0]["argv"][2] == NASTY + "\nsecond line",
              "the body arrives BYTE-EXACT through the seam, quotes, backtick, $( , "
              "backslash, newline and emoji included")
        check(got[0]["argv"][0] == "Exocortex" and got[0]["argv"][1] == "Alpha",
              "…with the title `Exocortex` and the note's target as the subtitle")
    src = "\n".join(pmod.MAC_NOTIFY_SCRIPT) + pmod.WIN_NOTIFY_SCRIPT
    check(not any(bit in src for bit in ("quote", "\U0001f642", "$(sub)")),
          "and NOT ONE of those characters is in either script's source — the texts are "
          "arguments and an environment, never interpolated code")

    start("PB15b", "a note's life: the raise rule, condition by condition")
    x = bworld("pb15b")
    one = letter(x, "OWNER", OWNER_NOTE, "no action")
    fyi = letter(x, "OWNER", "NORTH FABLE woke at 09:00", "no reply needed — FYI")
    pmn(x, "--pass", "--no-pull")
    t_one, t_fyi = tok(x, one), tok(x, fyi)
    rec = owner_of(x, t_one)
    check((rec.get("raised") or {}).get("how") in ("osascript", "toast"),
          "a fresh non-FYI note is raised: %s" % (rec.get("raised") or {}))
    shown = [r for r in raises(x) if OWNER_NOTE in " ".join(r["argv"])]
    check(len(shown) == 1, "…once, through the seam (%d)" % len(shown))
    fr = owner_of(x, t_fyi)
    check((fr.get("raised") or {}).get("how") == "none"
          and "FYI" in (fr.get("raised") or {}).get("why", ""),
          "AN FYI NOTE NEVER RAISES: %s" % (fr.get("raised") or {}))
    check(not fr.get("push"), "…and never pushes: the tree alone")

    pmn(x, "--pass", "--no-pull", "--now", later(minutes=2))
    pmn(x, "--pass", "--no-pull", "--now", later(hours=2))
    shown = [r for r in raises(x) if OWNER_NOTE in " ".join(r["argv"])]
    check(len(shown) == 1,
          "a second pass a minute later and a third an hour later raise NOTHING more (%d)"
          % len(shown))

    start("PB15c", "a note's life: nobody here · older than 30 min · acked elsewhere · a failed raise")
    q = pworld("pb15c")                       # no live-sessions file: nobody is here
    qone = letter(q, "OWNER", "nobody is at this machine", "no action")
    pmn(q, "--pass", "--no-pull")
    r = (owner_of(q, tok(q, qone)).get("raised") or {})
    check(r.get("how") == "none" and r.get("why") == "nobody is at this machine",
          "nobody at this machine and not the origin: `%s`" % r.get("why"))
    check(not raises(q), "…and the notifier was never asked at all")

    o = bworld("pb15d")
    old = letter(o, "OWNER", "this one has been round the fleet", "no action")
    t_old = tok(o, old)
    write_json(o["hub"] / "post-south.json",
               {"machine": "south", "version": 1, "sent": {}, "for_owner": [t_old],
                "letters": {t_old: {"to": "OWNER", "state": "waiting", "fyi": False,
                                    "first_seen": later(minutes=-40)}}})
    pmn(o, "--pass", "--no-pull")
    r = (owner_of(o, t_old).get("raised") or {})
    check(r.get("how") == "none" and "older than 30 min" in (r.get("why") or ""),
          "a note the fleet first saw 40 min ago is never raised here: `%s`" % r.get("why"))

    a = bworld("pb15e")
    aone = letter(a, "OWNER", "acked on the other machine", "no action")
    t_a = tok(a, aone)
    write_json(a["hub"] / "post-south.json",
               {"machine": "south", "version": 1, "sent": {}, "for_owner": [t_a],
                "letters": {t_a: {"to": "OWNER", "state": "waiting", "fyi": False,
                                  "first_seen": iso(datetime.datetime.now().astimezone()),
                                  "owner": {"acked": {"when": later(minutes=-1), "by": "SOUTH hub"}}}}})
    pmn(a, "--pass", "--no-pull")
    r = (owner_of(a, t_a).get("raised") or {})
    check(r.get("how") == "none" and r.get("why") == "already acked",
          "a note acked on the OTHER machine is not raised here: `%s`" % r.get("why"))
    check(not [x for x in raises(a) if "acked on the other" in " ".join(x["argv"])],
          "…and the notifier was never asked")

    f = bworld("pb15f")
    fone = letter(f, "OWNER", "the notifier is broken today", "no action")
    for n in range(3):
        pmn(f, "--pass", "--no-pull", "--now", later(minutes=n), env={"EXO_NOTIFY_FAIL": "1"})
    tried = [x for x in raises(f) if "notifier is broken" in " ".join(x["argv"])]
    r = (owner_of(f, tok(f, fone)).get("raised") or {})
    check(len(tried) == 2,
          "a raise that fails is tried ONCE more at the next pass, and never again (%d tries)"
          % len(tried))
    check(r.get("how") == "none" and "failed twice" in (r.get("why") or ""),
          "…and the reason is on the record: `%s`" % r.get("why"))

    start("PB15g", "bootstrap: nothing older than this build is ever raised or nudged")
    b = bworld("pb15g")
    bone = letter(b, "OWNER", "this note predates the surfaces build", "no action")
    pm(b, "--pass", "--no-pull")               # phase A's pass: the letter is on record
    st = state_of(b)
    st.pop("surfaces_from", None)              # …and now phase B arrives, as it really will
    st.pop("owner", None)
    write_state(b, st)
    try:                                       # only what happens AFTER it is the case
        os.unlink(str(b["base"] / "notify-calls.jsonl"))
    except OSError:
        pass
    code, out = pmn(b, "--pass", "--no-pull", "--now", later(minutes=1))
    check("SURFACES · notes and nudges start from" in out,
          "the loud line, once: %s" % next((l for l in out.splitlines() if "SURFACES" in l), "(none)"))
    check(not owner_of(b, tok(b, bone)),
          "a note first seen BEFORE surfaces_from has no raise, no push and no nudge at all")
    check(not [r for r in raises(b) if "predates" in " ".join(r["argv"])],
          "…and the notifier was never asked about it")
    code, out = pmn(b, "--pass", "--no-pull", "--now", later(hours=1))
    check("SURFACES ·" not in out, "and the loud line is said ONCE, not every pass")

    start("PB15h", "THE BOOTSTRAP PASS ITSELF raises and nudges nothing, however long "
                   "the mail has waited (punch list 2 F11)")
    # WHAT HAPPENED ON THE NORTH AT 09:59:10. `surfaces_from` was written inside
    # owner_surfaces, which runs AFTER compose_nudges — so at the first pass the
    # nudge's "nothing older than this build" test read no mark, was skipped for
    # EVERY letter, and four nudges were composed for letters that had waited
    # between one and two days. All four were raised at once (four banners on
    # one screen) and four phone pushes were queued, while the SURFACES line
    # said `0`, because it counted only the `to: OWNER` ones.
    d = bworld("pb15h")
    plant_claim(d, "hub", "north", HOLDER, session=SID_A)
    tpath = claude_transcript(d, SID_A)
    held = letter(d, "NORTH/hub", "a cut order from yesterday")
    letter(d, "NORTH/Icebox", "the icebox lane's own letter")
    letter(d, "NORTH/Cutting", "the cutting lane's first")
    letter(d, "NORTH/Cutting", "and its second")
    letter(d, "NORTH/Fieldwork", "a field note nobody carried")
    oldnote = letter(d, "OWNER", "a note that waited all night", "no action")
    pm(d, "--pass", "--no-pull")                    # they are on the record, as phase A left them
    age_file(tpath, 48 * 3600)                      # its window has taken no turn since the day before
    st = state_of(d)
    yesterday = later(hours=-24)
    for e in (st.get("letters") or {}).values():    # …and the six have waited a day
        e["first_seen"] = yesterday
        e["queued"] = yesterday
        e.pop("nudged", None)
    st.pop("surfaces_from", None)                   # and NOW phase B arrives, as it really did
    st.pop("owner", None)
    st.pop("nudges", None)
    write_state(d, st)
    for pf in sorted((d["post"] / "pending").glob("*.json")):
        pbody = json.loads(io.open(str(pf), encoding="utf-8").read())
        pbody["items"] = [i for i in (pbody.get("items") or []) if i.get("kind") != "owner"]
        write_json(pf, pbody)                       # phase A knows no `owner` item at all
    try:
        os.unlink(str(d["base"] / "notify-calls.jsonl"))
    except OSError:
        pass
    fresh = letter(d, "NORTH/Fresh", "the first letter of the new era")
    # a default `answer it` letter asks nothing of the USER (the lane answers), so it earns
    # no notice; its sibling's ACTION asks the person and does.
    letter(d, "NORTH/Fresh2", "the new era's ruling", ASK_ACTION)
    code, out = pmn(d, "--pass", "--no-pull")
    line = next((l for l in out.splitlines() if l.startswith("SURFACES ·")), "")
    check("· 6 earlier waiting letter(s) stay on the tree only" in line,
          "the loud line counts EVERY letter that waited, `to: OWNER` and all: %s" % line)
    check(not (state_of(d).get("nudges") or {}),
          "THE BOOTSTRAP PASS COMPOSES NO NUDGE AT ALL (%d)"
          % len(state_of(d).get("nudges") or {}))
    check(not raises(d), "…the notifier was never asked, not once (%d)" % len(raises(d)))
    check(not (state_of(d).get("owner") or {}),
          "…no note for Wren was even recorded: %s" % sorted(state_of(d).get("owner") or {}))
    queued_owner = [f.name for f in sorted((d["post"] / "pending").glob("*.json"))
                   if any(i.get("kind") == "owner" for i in
                          (json.loads(io.open(str(f), encoding="utf-8").read()).get("items") or []))]
    check(not queued_owner, "…and no `owner` item was queued for anybody: %s" % queued_owner)
    check(not (post_of(d)["letters"][tok(d, held)].get("nudged")),
          "the day-old letter's own entry records no nudge either")
    check(not (post_of(d)["letters"][tok(d, oldnote)].get("owner")),
          "…and the day-old note for Wren carries no `owner` key")
    pmn(d, "--pass", "--no-pull", "--now", later(minutes=6))
    rows = list((state_of(d).get("nudges") or {}).values())
    check(len(rows) == 1, "six minutes on, ONE nudge — and only one (%d)" % len(rows))
    check(rows and rows[0].get("to") == "NORTH/Fresh2",
          "…for the ONE address whose letter arrived after the mark AND asks the person: %s"
          % [r.get("to") for r in rows])
    check(rows and rows[0].get("text") == "%s — FRESH2: no window open" % ASK_LINE,
          "…its notice is the consequence line + `<lane>: no window open`: %s"
          % [r.get("text") for r in rows])
    check(not [r for r in rows if r.get("to") == "NORTH/Fresh"],
          "…and the default `answer it` letter beside it earns NO nudge: silence")

    start("PB15i", "a machine the brain merely carried the tool to raises, pushes and "
                   "nudges NOTHING (punch list 2 F12)")
    # The brain carries tools/postman.py to the other machine within minutes and that
    # machine's PULSE runs `--pass` every beat as its floor, so phase B's
    # surfaces went live there minutes after this machine's install — no hooks
    # installed, nobody at that machine having said "install it". The tool
    # travels; the word is a file in POST DIR.
    n = bworld("pb15i")
    uninstall_marker(n)
    plant_claim(n, "hub", "north", HOLDER, session=SID_A)
    ntp = claude_transcript(n, SID_A)
    age_file(ntp, 600)
    note = letter(n, "OWNER", "a note on a machine nobody installed", "no action")
    letter(n, "NORTH/hub", "and a letter for its idle window")
    pmn(n, "--pass", "--no-pull")
    tn = tok(n, note)
    r = (owner_of(n, tn).get("raised") or {})
    check(r.get("how") == "none" and r.get("why") == "the postman is not installed on this machine",
          "the why is recorded on the note, in plain words: `%s`" % r.get("why"))
    check(not raises(n), "…the notifier was never asked at all")
    check(not (owner_of(n, tn).get("push")),
          "…no session was asked to push it: %s" % owner_of(n, tn).get("push"))
    check(not [i for i in pending_of(n, SID_A) if i.get("kind") == "owner"],
          "…and no `owner` item was queued")
    pmn(n, "--pass", "--no-pull", "--now", later(minutes=7))
    check(not (state_of(n).get("nudges") or {}), "no nudge is composed here either")
    check(read_hold(n, SID_A),
          "…while THE HOLDS CACHE IS STILL KEPT: arm-before-idle is phase A's floor plus "
          "the cache, and it stands on every machine")
    code, out = pm(n, "--status", "--no-pull")
    check("surfaces off — not installed here" in out,
          "--status says so in one line: %s"
          % next((l for l in out.splitlines() if "surfaces off" in l), "(nothing)"))
    facts = facts_via(n)
    check(((facts.get("machines") or {}).get("north") or {}).get("surfaces") is False,
          "…and the machine root's own facts carry it, so the click can answer: %s"
          % ((facts.get("machines") or {}).get("north") or {}).get("surfaces"))
    install_marker(n)                               # …and now the word IS said here
    said_note = letter(n, "OWNER", "and one sent after the word was said", "no action")
    pmn(n, "--pass", "--no-pull", "--now", later(minutes=8))
    r = (owner_of(n, tok(n, said_note)).get("raised") or {})
    check(r.get("how") in ("osascript", "toast"),
          "WITH THE MARKER the very same machine raises again, as today: %s" % r)
    facts = facts_via(n)
    check(((facts.get("machines") or {}).get("north") or {}).get("surfaces") is True,
          "…and the root says the surfaces are on")

    start("PB15j", "the word is a FILE: --install-hooks writes it, --dry does not, "
                   "--uninstall-hooks removes it")
    m = bworld("pb15j")
    uninstall_marker(m)
    marker = m["post"] / "installed.json"
    target = m["home"] / ".claude" / "settings.json"
    write(target, FOREIGN_SETTINGS % ((str(m["home"]),) * 5))
    code, out = pm(m, "--install-hooks", "--vendor", "claude", "--dry", "--settings", str(target))
    check(not marker.exists(), "--install-hooks --dry writes no marker at all")
    check("surfaces on" not in out, "…and does not say it did")
    code, out = pm(m, "--install-hooks", "--vendor", "claude", "--settings", str(target))
    check(marker.is_file(), "--install-hooks writes it")
    check("surfaces on — this machine is installed" in out,
          "…and says so in one line: %s"
          % next((l for l in out.splitlines() if "surfaces" in l), "(nothing)"))
    body = json.loads(io.open(str(marker), encoding="utf-8").read())
    check(sorted(body) == ["hub", "vendors", "when"] and body["vendors"] == ["claude"]
          and Path(body["hub"]).resolve() == m["hub"].resolve() and body["when"],
          "…carrying when, the vendor(s) and the hub, and nothing else: %s · %s"
          % (sorted(body), body.get("hub")))
    if os.name != "nt":
        check(mode_of(marker) == 0o600,
              "…at 0600, this account's alone (found %o)" % mode_of(marker))
    code, out = pm(m, "--install-hooks", "--vendor", "claude", "--settings", str(target))
    check(marker.is_file() and "already installed" in out,
          "a second install is idempotent and the marker stands — which is the one step "
          "this machine's verifier runs after the copy")
    code, out = pm(m, "--uninstall-hooks", "--vendor", "claude", "--dry", "--settings", str(target))
    check(marker.is_file(), "--uninstall-hooks --dry leaves it alone")
    code, out = pm(m, "--uninstall-hooks", "--vendor", "claude", "--settings", str(target))
    check(not marker.exists(), "--uninstall-hooks removes it")
    check("surfaces off — this machine is no longer installed" in out,
          "…and says that too: %s"
          % next((l for l in out.splitlines() if "surfaces" in l), "(nothing)"))
    b2 = bworld("pb15j2")
    uninstall_marker(b2)
    bad = b2["home"] / ".claude" / "settings.json"
    write(bad, "{ this is not json ")
    code, out = pm(b2, "--install-hooks", "--vendor", "claude", "--settings", str(bad))
    check("REFUSED" in out and not (b2["post"] / "installed.json").exists(),
          "AN INSTALL THAT WAS REFUSED WRITES NO MARKER — the word was never carried out")


# --------------------------------------------------------------------------
# PB16 (phase B P16) — AGE comes from the earliest first_seen across post files
# --------------------------------------------------------------------------

def case_pb16():
    start("PB16", "AGE is the EARLIEST first_seen any machine records, this one included")
    w = bworld("pb16")
    pmod = load_postman(w)
    posts = {"south": {"letters": {"pm-aaaaaaaaaaaa": {"first_seen": later(minutes=-40)}}},
             "north": {"letters": {"pm-aaaaaaaaaaaa": {"first_seen": later(minutes=-2)}}}}
    got = pmod.earliest_seen("pm-aaaaaaaaaaaa", posts, later(minutes=-2))
    check(got is not None and abs((datetime.datetime.now().astimezone() - got).total_seconds()
                                  / 60.0 - 40) < 2,
          "two machines, one token: the earliest sight wins (%s)" % got)
    got = pmod.earliest_seen("pm-nowhere00000", posts, later(minutes=-3))
    check(got is not None and abs((datetime.datetime.now().astimezone() - got).total_seconds()
                                  / 60.0 - 3) < 2,
          "a token no post file carries falls back to this machine's own sight (%s)" % got)
    nud = {"south": {"nudges": {"nd-aaaaaaaaaaaa": {"first_seen": later(minutes=-55)}}}}
    got = pmod.earliest_seen("nd-aaaaaaaaaaaa", nud, "")
    check(got is not None, "a NUDGE's own first sight counts the same way (%s)" % got)


# --------------------------------------------------------------------------
# PB17 (phase B P17) — the phone leg
# --------------------------------------------------------------------------

def case_pb17():
    start("PB17", "the phone: one live session's own turn carries the note, and it is OBSERVED")
    w = bworld("pb17")
    claude_transcript(w, SID_A)
    claude_transcript(w, SID_B)
    plant_live(w, [SID_A, SID_B])
    one = letter(w, "OWNER", OWNER_NOTE, "no action")
    t = tok(w, one)
    pmn(w, "--pass", "--no-pull")
    push = owner_of(w, t).get("push") or {}
    check(push.get("session") in (SID_A, SID_B),
          "a live Claude session on this machine is asked to carry it: %s" % push.get("session"))
    carrier = push.get("session")
    items = pending_of(w, carrier)
    owners = [i for i in items if i.get("kind") == "owner"]
    check(len(owners) == 1, "ONE pending item of kind `owner` (%d)" % len(owners))
    if owners:
        check(owners[0].get("wake") is False,
              "…queued `wake: false` — a note NEVER wakes a sleeping session")
        check(owners[0].get("push") == "Exocortex: %s — no action" % OWNER_NOTE,
              "…carrying the one push text the raise carried: %r" % owners[0].get("push"))

    code, out, err = hook(w, carrier, "PostToolBatch")
    check(context_of(out) == "" or "PushNotification" not in context_of(out),
          "a `owner` item is NOT delivered at PostToolBatch: a push never interrupts a build")
    check([i for i in pending_of(w, carrier) if i.get("kind") == "owner"],
          "…and it is still pending for a calmer road")
    for event in ("SessionStart", "UserPromptSubmit", "Stop"):
        code, out, err = hook(w, carrier, event, {"agent_id": "sub_9"})
        check(out == "", "THE MAIN-THREAD RULE holds for a owner item too: %s" % event)
    code, out, err = hook(w, carrier, "UserPromptSubmit")
    ctx = context_of(out)
    # The frame names the person, and who that is comes from the registry now:
    # the words are fixed, the name in them is the reader's own.
    _who = pm_module(w).owner_label()
    # the frame is a LINE for the phone, not a note, and no standing order.
    check(("POST — a line for %s's phone: " % _who) in ctx
          and "a note for" not in ctx and "a standing order" not in ctx,
          "the frame is the postman's own fixed words: %s" % ctx.splitlines()[:1])
    check("Make ONE PushNotification call, status \"proactive\", with exactly that line as "
          "the message." in ctx and "with exactly this message" not in ctx,
          "…naming the one call and its status")
    check(("POST — a line for %s's phone: Exocortex: %s — no action" % (_who, OWNER_NOTE)) in ctx,
          "…with the push text on the frame's own line")
    # THE LAST LINE NAMES THE DEFERRED TOOL: in the desktop
    # app PushNotification is DEFERRED — absent from the loaded tool list until
    # it is fetched — so "if this session has no such tool" could be answered
    # honestly with "none" and no note would ever reach the phone.
    check("If PushNotification is listed as a deferred tool, load it first; if this session "
          "has no such tool at all, do nothing. No reply text is needed for it." in ctx,
          "…and the way out, which first tells a session to LOAD a deferred tool")
    check(("[%s]" % t) in ctx, "…and the note's token, which is how `asked` is later SEEN")

    claude_transcript(w, carrier, [claude_hook_context(carrier, ctx)])
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    push = owner_of(w, t).get("push") or {}
    check(push.get("state") == "asked", "the frame in the carrier's transcript reads `asked`: %s" % push)
    push_records(w, carrier, "Exocortex: %s — no action" % OWNER_NOTE)
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=2))
    push = owner_of(w, t).get("push") or {}
    check(push.get("state") == "called", "the real call's own record reads `called`: %s" % push.get("state"))
    check(push.get("result") == "Mobile push requested.",
          "…and the result is the tool's OWN WORDS, never interpreted: %r" % push.get("result"))

    start("PB17b", "the phone: the carrier order, and never a Codex thread")
    s = bworld("pb17b")
    claude_transcript(s, SID_A)
    claude_transcript(s, SID_B)
    plant_live(s, [SID_A, SID_B])
    code, out = mp(s, "--send", "OWNER", "Exocortex", "sent by B itself", "no action",
                   "--no-push", env=as_session(SID_B))
    pmn(s, "--pass", "--no-pull")
    t = [tk for tk in post_of(s)["for_owner"]][0]
    push = owner_of(s, t).get("push") or {}
    check(push.get("session") == SID_B,
          "THE SENDER goes first when it is a bound Claude session here: %s" % push.get("session"))

    c = bworld("pb17c", live=False)
    codex_rollout(c, TID_C)
    plant_live(c, [])
    cone = letter(c, "OWNER", "only a Codex thread is up", "no action")
    write_json(c["hub"] / ("live-sessions-%s.json" % c["machine"]),
               {"machine": c["machine"], "when": iso(datetime.datetime.now().astimezone()),
                "live_minutes": 10,
                "sessions": [{"id": TID_C, "dir": "2026/09/19", "kind": "codex", "mind": "NOBODY",
                              "cwd": str(c["hub"]), "in_hub": True, "minutes_ago": 1}]})
    pmn(c, "--pass", "--no-pull")
    push = owner_of(c, tok(c, cone)).get("push") or {}
    check(push.get("session") in (None, ""),
          "A CODEX THREAD IS NEVER THE CARRIER — it has no push tool: %r" % push.get("session"))
    code, out = pmn(c, "--pass", "--no-pull", "--now", later(minutes=45))
    push = owner_of(c, tok(c, cone)).get("push") or {}
    check(push.get("state") == "lapsed"
          and "no Claude session had a turn on the NORTH within 30 min" in (push.get("why") or ""),
          "…and past 30 minutes it LAPSES, in plain words: %s" % push)

    start("PB17d", "the phone: ONE reassignment, and the item leaves the first file first")
    r = bworld("pb17d")
    claude_transcript(r, SID_A)
    claude_transcript(r, SID_B)
    plant_live(r, [SID_A, SID_B])
    rone = letter(r, "OWNER", "nobody answered the first time", "no action")
    t = tok(r, rone)
    pmn(r, "--pass", "--no-pull")
    first = (owner_of(r, t).get("push") or {}).get("session")
    check(bool(first), "a first carrier was picked: %s" % first)
    pmn(r, "--pass", "--no-pull", "--now", later(minutes=5))
    push = owner_of(r, t).get("push") or {}
    second = push.get("session")
    check(second and second != first,
          "a carrier with no model round in 2 min hands the item on: %s -> %s" % (first, second))
    check(not [i for i in pending_of(r, first) if i.get("kind") == "owner"],
          "…and the item left the FIRST pending file before it entered the second")
    check([i for i in pending_of(r, second) if i.get("kind") == "owner"],
          "…where it now is")
    tried = ((state_of(r)["owner"][t].get("push") or {}).get("tried") or [])
    check(len(tried) == 2, "ONE reassignment at most: %s" % tried)
    pmn(r, "--pass", "--no-pull", "--now", later(minutes=10))
    push = owner_of(r, t).get("push") or {}
    tried = ((state_of(r)["owner"][t].get("push") or {}).get("tried") or [])
    check(push.get("session") == second and len(tried) == 2,
          "…and it is never handed on a third time: %s" % tried)

    start("PB17g", "the phone: a reassignment with nowhere to go is never spent (punch list F5)")
    # The item used to leave the first carrier's file BEFORE a second was
    # known, so with ONE Claude session on the machine the note was gone from
    # the only window that could still carry it — and at thirty minutes the
    # lapse blamed a window that had in fact taken a turn.
    n1 = bworld("pb17g")
    claude_transcript(n1, SID_A)
    plant_live(n1, [SID_A])                        # ONE Claude session, and no other
    lone = letter(n1, "OWNER", "only one window is up on this machine", "no action")
    t1 = tok(n1, lone)
    pmn(n1, "--pass", "--no-pull")
    push = owner_of(n1, t1).get("push") or {}
    check(push.get("session") == SID_A, "the one live session is asked: %s" % push.get("session"))
    pmn(n1, "--pass", "--no-pull", "--now", later(minutes=3))
    push = owner_of(n1, t1).get("push") or {}
    check(push.get("session") == SID_A and push.get("state") == "queued",
          "quiet for 3 min with NOBODY ELSE, the item is not taken away: %s" % push)
    check([i for i in pending_of(n1, SID_A) if i.get("kind") == "owner"],
          "…it is still in the only pending file that can carry it")
    tried = ((state_of(n1)["owner"][t1].get("push") or {}).get("tried") or [])
    check(len(tried) == 1, "…and the one reassignment is NOT spent: %s" % tried)
    code, out, err = hook(n1, SID_A, "UserPromptSubmit")
    ctx = context_of(out)
    check("PushNotification" in ctx, "at 6 min the window takes a turn and gets the item")
    claude_transcript(n1, SID_A, [claude_hook_context(SID_A, ctx)])
    push_records(n1, SID_A, "Exocortex: only one window is up on this machine — no action")
    pmn(n1, "--pass", "--no-pull", "--now", later(minutes=6))
    push = owner_of(n1, t1).get("push") or {}
    check(push.get("state") == "called",
          "…and the push is `called`, by the window that was never robbed: %s" % push.get("state"))

    start("PB17h", "the phone: `asked` with no call lapses in its own words, and not before")
    n2 = bworld("pb17h")
    claude_transcript(n2, SID_A)
    plant_live(n2, [SID_A])
    dumb = letter(n2, "OWNER", "asked and never called", "no action")
    t2 = tok(n2, dumb)
    pmn(n2, "--pass", "--no-pull")
    code, out, err = hook(n2, SID_A, "UserPromptSubmit")
    claude_transcript(n2, SID_A, [claude_hook_context(SID_A, context_of(out))])
    pmn(n2, "--pass", "--no-pull", "--now", later(minutes=1))
    check((owner_of(n2, t2).get("push") or {}).get("state") == "asked",
          "the frame is in its transcript: %s" % (owner_of(n2, t2).get("push") or {}).get("state"))
    pmn(n2, "--pass", "--no-pull", "--now", later(minutes=29))
    check((owner_of(n2, t2).get("push") or {}).get("state") == "asked",
          "at 29 min it is still `asked` — never lapsed early")
    pmn(n2, "--pass", "--no-pull", "--now", later(minutes=31))
    push = owner_of(n2, t2).get("push") or {}
    check(push.get("state") == "lapsed",
          "…and past owner_fresh_minutes an `asked` carrier LAPSES: %s" % push.get("state"))
    check(push.get("why") == ("«%s» was asked and made no call within 30 min"
                              % (push.get("title") or push.get("session") or "?")),
          "…in its own wording, which never blames a window for not taking a turn: %s"
          % push.get("why"))

    start("PB17e", "the phone: turned off is said, not silently skipped")
    o = bworld("pb17e")
    write_json(o["hub"] / "post-config.json", {"owner_push": False})
    oone = letter(o, "OWNER", "the phone leg is off here", "no action")
    pmn(o, "--pass", "--no-pull")
    rec = owner_of(o, tok(o, oone))
    check((rec.get("raised") or {}).get("how") in ("osascript", "toast"),
          "the desktop raise still happens with the phone leg off")
    check((rec.get("push") or {}).get("state") == "off",
          "…and the push says `off`, not nothing: %s" % (rec.get("push") or {}))
    n = bworld("pb17f")
    write_json(n["hub"] / "post-config.json", {"owner_notify": False})
    none_ = letter(n, "OWNER", "notes are turned off here", "no action")
    pmn(n, "--pass", "--no-pull")
    rec = owner_of(n, tok(n, none_))
    check((rec.get("raised") or {}).get("why") == "notes for Wren are turned off here",
          "owner_notify false says so in plain words: %s" % (rec.get("raised") or {}))
    check(not raises(n), "…and the notifier is never asked")


# --------------------------------------------------------------------------
# PB18 (phase B P18) — arm before idle
# --------------------------------------------------------------------------

def case_pb18():
    start("PB18", "arm before idle: the machine has the session arm its own waiter")
    w = pworld("pb18")
    claude_transcript(w, SID_A)
    code, out = tool(w, "claim.py", "--quiet", "--claim", "hub", HOLDER, "--hub", str(w["hub"]),
                     "--mind", "FABLE")
    hold = w["post"] / "holds" / ("%s.json" % SID_A)
    check(code == 0 and not hold.is_file(),
          "a claim with no session id in the environment writes no holds row (nothing is guessed)")
    code, out = run([PY, str(w["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "landing:X",
                     OTHER, "--hub", str(w["hub"]), "--mind", "FABLE"],
                    cwd=str(w["hub"]), env=dict(w["env"], **as_session(SID_A)))
    hold_body = read_hold(w, SID_A)
    check(hold_body.get("session") == SID_A and hold_body.get("cmd"),
          "THE HOLDS CACHE is written the moment a claim changes: %s"
          % {k: hold_body.get(k) for k in ("session", "address", "arm")})
    check(hold_body.get("address", "").upper().startswith("NORTH/"),
          "…with the address a waiter would listen on: %s" % hold_body.get("address"))
    check("mail.py" in hold_body.get("cmd", "") and "--wait" in hold_body.get("cmd", ""),
          "…and the command the arm line asks for, rendered per machine: %s" % hold_body.get("cmd"))

    code, out, err = hook(w, SID_A, "Stop")
    ctx = context_of(out)
    check("POST — this session holds" in ctx and "[arm]" in ctx,
          "at Stop, with nothing pending, the hook asks it to arm: %s" % ctx[:120])
    check(hold_body.get("cmd") in ctx, "…with that exact command")
    check("as ONE background command" in ctx, "…said as one background command")
    for event in ("SessionStart", "UserPromptSubmit", "PostToolBatch"):
        code, out, err = hook(w, SID_A, event)
        check(out == "", "%s never carries the arm line — it belongs at a turn's end" % event)
    code, out, err = hook(w, SID_A, "Stop", {"stop_hook_active": True})
    check(out == "", "a second Stop in one turn is silent — the arm line rides the first")
    code, out, err = hook(w, SID_A, "Stop")
    check(out == "", "and it is not repeated inside arm_again_minutes")
    code, out, err = hook(w, SID_A, "Stop", {"agent_id": "sub_3"})
    check(out == "", "THE MAIN-THREAD RULE: a subagent is never asked to arm anything")

    start("PB18b", "arm before idle: three tells, then silence; and an alive mark stops it at once")
    told = w["post"] / "told" / ("%s.json" % SID_A)
    body = json.loads(io.open(str(told), encoding="utf-8").read())
    body["tells"] = [time.time() - 3600]
    write(told, json.dumps(body))
    code, out, err = hook(w, SID_A, "Stop")
    check("[arm]" in context_of(out), "an hour later it asks again (told #2)")
    body = json.loads(io.open(str(told), encoding="utf-8").read())
    body["tells"] = [t - 3600 for t in body["tells"]]
    write(told, json.dumps(body))
    code, out, err = hook(w, SID_A, "Stop")
    check("[arm]" in context_of(out), "and once more (told #3)")
    body = json.loads(io.open(str(told), encoding="utf-8").read())
    check(len(body.get("tells") or []) == 3, "three tells are on the record: %s" % len(body.get("tells") or []))
    body["tells"] = [t - 7200 for t in body["tells"]]
    write(told, json.dumps(body))
    code, out, err = hook(w, SID_A, "Stop")
    check(out == "", "AFTER THE THIRD UNANSWERED TELL THE HOOK IS SILENT — the nudge carries")
    alive = w["post"] / "waiters" / ("%s.alive" % SID_A)
    write(alive, iso(datetime.datetime.now().astimezone()))
    code, out, err = hook(w, SID_A, "Stop")
    check(out == "", "a session with a FRESH alive mark is never asked to arm")
    os.utime(str(alive), (time.time() - 120, time.time() - 120))
    code, out, err = hook(w, SID_A, "Stop")
    check("[arm]" in context_of(out),
          "a KILLED waiter ages out by itself — no pid was ever probed — and the count starts again")

    start("PB18c", "arm before idle: the switch, the vendor, and a released lane")
    o = pworld("pb18c")
    write_json(o["hub"] / "post-config.json", {"arm_before_idle": False})
    claude_transcript(o, SID_A)
    run([PY, str(o["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(o["hub"]), "--mind", "FABLE"],
        cwd=str(o["hub"]), env=dict(o["env"], **as_session(SID_A)))
    check(read_hold(o, SID_A).get("arm") is False,
          "arm_before_idle false is written into the holds row: %s" % read_hold(o, SID_A).get("arm"))
    code, out, err = hook(o, SID_A, "Stop")
    check(out == "", "…and the hook says nothing at all")
    code, out, err = hook(o, SID_A, "Stop", vendor="codex")
    check(out == "", "Codex is never asked to arm: no background-command wake exists there")

    v = pworld("pb18d")
    claude_transcript(v, SID_A)
    run([PY, str(v["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(v["hub"]), "--mind", "FABLE"],
        cwd=str(v["hub"]), env=dict(v["env"], **as_session(SID_A)))
    check(read_hold(v, SID_A).get("session") == SID_A, "the holds row is there")
    code, out, err = hook(v, SID_A, "Stop", vendor="codex")
    check(out == "", "a Codex hook on the same row carries nothing")
    run([PY, str(v["hub"] / "tools" / "claim.py"), "--quiet", "--release", "hub", HOLDER,
         "--hub", str(v["hub"])], cwd=str(v["hub"]), env=dict(v["env"], **as_session(SID_A)))
    check(not (v["post"] / "holds" / ("%s.json" % SID_A)).is_file(),
          "RELEASING the lane takes the row away — a lane nobody holds asks for no waiter")
    code, out, err = hook(v, SID_A, "Stop")
    check(out == "", "…and the hook is silent again")

    start("PB18e", "arm before idle: the pass corrects the cache in BOTH directions")
    p = pworld("pb18e")
    claude_transcript(p, SID_A)
    plant_claim(p, "hub", "north", HOLDER, session=SID_A)
    pm(p, "--pass", "--no-pull")
    check(read_hold(p, SID_A).get("session") == SID_A,
          "a claim with no cache row gets one at the next pass")
    write_json(p["post"] / "holds" / ("%s.json" % SID_B),
               {"session": SID_B, "title": "a window that let go", "arcs": ["ghost"],
                "address": "NORTH/ghost", "cmd": "x", "arm": True})
    pm(p, "--pass", "--no-pull", "--now", later(minutes=1))
    check(not (p["post"] / "holds" / ("%s.json" % SID_B)).is_file(),
          "…and a cache row no claim backs is taken away — claims.json is the truth")

    start("PB18f", "arm before idle: the rendered command RUNS, and the alive mark appears")
    if os.name == "nt":
        skip("the rendered command is a Windows command string here; PB24 proves its shape "
             "and the South runs it (§14 L8) — NOT RUN on this OS")
    else:
        import shlex
        g = pworld("pb18f")
        claude_transcript(g, SID_A)
        title_file(g, SID_A, HOLDER)
        run([PY, str(g["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
             "--hub", str(g["hub"]), "--mind", "FABLE"],
            cwd=str(g["hub"]), env=dict(g["env"], **as_session(SID_A)))
        write_json(g["post"] / "heartbeat.json",
                   {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})
        cmd = shlex.split(read_hold(g, SID_A).get("cmd") or "")
        env_all = dict(os.environ)
        env_all["PYTHONDONTWRITEBYTECODE"] = "1"
        for k, v in dict(g["env"], **as_session(SID_A)).items():
            env_all.pop(k, None) if v is None else env_all.__setitem__(k, str(v))
        proc = subprocess.Popen(cmd + ["--hub", str(g["hub"])], cwd=str(g["hub"]), env=env_all,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True)
        alive = g["post"] / "waiters" / ("%s.alive" % SID_A)
        try:
            for _ in range(80):
                if alive.is_file():
                    break
                time.sleep(0.1)
            check(alive.is_file(), "the command the arm line hands over RUNS and leaves its alive mark")
            check((g["hub"] / "ear-north-hub.json").is_file(), "…and the ear it arms")
            code, out, err = hook(g, SID_A, "Stop")
            check(out == "", "…so the hook stops asking at once")
            one = letter(g, "NORTH/hub", "and now a letter finds it")
            pm(g, "--pass", "--no-pull")
            out, _ = proc.communicate(timeout=30)
            check(tok(g, one) in out, "…and the waiter carries the letter, as phase A built it")
        except subprocess.TimeoutExpired:
            proc.kill()
            check(False, "the armed waiter delivered a letter (it did not)")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
            for _ in range(40):
                if not alive.is_file():
                    break
                time.sleep(0.1)
            check(not alive.is_file(), "and the mark is REMOVED on the way out, every exit path")

    start("PB18h", "arm before idle: A WAITER THAT LIVED IS THE ANSWER TO EVERY TELL (F2)")
    # The case the waiter's alive mark exists for: told at t0, the
    # session arms, a letter arrives, the waiter delivers and EXITS — removing
    # the alive mark that was the only evidence the tell had been answered — and
    # the next Stop found a tell younger than arm_again_minutes and SAID
    # NOTHING. The window held its lane deaf, with no later Stop to catch it.
    f2 = pworld("pb18h")
    claude_transcript(f2, SID_A)
    run([PY, str(f2["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(f2["hub"]), "--mind", "FABLE"],
        cwd=str(f2["hub"]), env=dict(f2["env"], **as_session(SID_A)))
    check(getattr(load_mail(f2), "ALIVE_LIVED_S", None) == 60,
          "`a waiter that LIVED` is 60 s, named in mail.py: %r"
          % getattr(load_mail(f2), "ALIVE_LIVED_S", None))
    code, out, err = hook(f2, SID_A, "Stop")
    check("[arm]" in context_of(out), "tell #1, at the first Stop")
    told = f2["post"] / "told" / ("%s.json" % SID_A)
    body = json.loads(io.open(str(told), encoding="utf-8").read())
    body["tells"] = [time.time() - 240]                    # told four minutes ago
    write(told, json.dumps(body))
    one = letter(f2, "NORTH/hub", "the letter the armed waiter carries away")
    pm(f2, "--pass", "--no-pull")
    check([i for i in pending_of(f2, SID_A) if i.get("token") == tok(f2, one)],
          "a letter is waiting in that session's own pending file")
    code, out = run_waiter(f2, SID_A, read_hold(f2, SID_A).get("address") or "NORTH/hub", 0)
    check(tok(f2, one) in out, "the waiter carries it and exits: %s" % out.strip()[-70:])
    check(not (f2["post"] / "waiters" / ("%s.alive" % SID_A)).is_file(),
          "…its alive mark is gone, exactly as it always was")
    check(not told.is_file(),
          "…AND SO IS THE TELL COUNT: a waiter that lived answered the tell")
    code, out, err = hook(f2, SID_A, "Stop")
    check("[arm]" in context_of(out),
          "so the Stop four minutes later ASKS AGAIN — the very Stop that went silent")
    code, out, err = hook(f2, SID_A, "Stop")
    check(out == "", "…and only once: the next Stop inside the window is silent again")

    start("PB18i", "arm before idle: a waiter that dies young leaves the count, and the cap holds")
    f3 = pworld("pb18i")
    claude_transcript(f3, SID_A)
    run([PY, str(f3["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(f3["hub"]), "--mind", "FABLE"],
        cwd=str(f3["hub"]), env=dict(f3["env"], **as_session(SID_A)))
    addr = read_hold(f3, SID_A).get("address") or "NORTH/hub"
    arms = []
    for i in range(5):                                     # five exits inside ten minutes
        code, out, err = hook(f3, SID_A, "Stop")
        arms.append("[arm]" in context_of(out))
        letter(f3, "NORTH/hub", "letter %d, carried at once" % i)
        pm(f3, "--pass", "--no-pull", "--now", later(minutes=i))
        run_waiter(f3, SID_A, addr, 1e9)                   # …each one dying far short of `lived`
    told = f3["post"] / "told" / ("%s.json" % SID_A)
    tells = (json.loads(io.open(str(told), encoding="utf-8").read()).get("tells") or []) \
        if told.is_file() else []
    check(arms[0] is True, "the first Stop tells")
    check(arms[1] is False, "…and the second Stop inside the window is SILENT")
    check(len(tells) <= 3, "five exits in ten minutes cost no more than TELL_CAP tells: %d"
          % len(tells))
    check(told.is_file(),
          "…because a waiter that dies young LEAVES the count — which is what still bounds "
          "the fast loop (a bad --title ends a wait in seconds)")

    start("PB18j", "the arm command is SHELL TEXT: the title survives bash byte-exact (F7)")
    u = pworld("pb18j2")
    claude_transcript(u, SID_A)
    plant_claim(u, "x;y", "north", HOLDER, session=SID_A)
    pm(u, "--pass", "--no-pull")
    row = read_hold(u, SID_A)
    check(row.get("address") == "NORTH/x;y",
          "an address carrying a character a shell would read: %s" % row.get("address"))
    check(row.get("cmd") == "", "…renders NO command at all — the address is never quoted")
    check("carries a character a shell would read" in (row.get("why") or ""),
          "…and the row says why, in plain words: %s" % row.get("why"))
    code, out, err = hook(u, SID_A, "Stop")
    check(out == "", "…and the hook says nothing, as it does for any row with no command")
    if os.name == "nt":
        skip("the arm line is bash text on both machines (Git Bash on the South); a Windows "
             "runner cannot run it here — NOT RUN on this OS")
    else:
        q = pworld("pb18j")
        pwn1, pwn2 = q["base"] / "PWNED-sub", q["base"] / "PWNED-tick"
        nasty_title = ('ACT — Exocortex/hub: a "quote" $(touch %s) `touch %s` '
                       "a'tick'; a \\slash and a *star" % (pwn1, pwn2))
        claude_transcript(q, SID_A)
        title_file(q, SID_A, nasty_title)
        run([PY, str(q["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", nasty_title,
             "--hub", str(q["hub"]), "--mind", "FABLE"],
            cwd=str(q["hub"]), env=dict(q["env"], **as_session(SID_A)))
        cmd = read_hold(q, SID_A).get("cmd") or ""
        check(read_hold(q, SID_A).get("title") == nasty_title,
              "the holds row keeps the title BYTE-EXACT, as claim.py was handed it")
        check('\\"quote\\"' in cmd and "\\$(touch" in cmd and "\\`touch" in cmd
              and "\\\\slash" in cmd,
              "…and the command escapes \" $ ` and \\ for bash double quotes, and alters "
              "nothing else: %s" % cmd[-90:])
        env_all = dict(os.environ)
        env_all["PYTHONDONTWRITEBYTECODE"] = "1"
        for k, v in dict(q["env"], **as_session(SID_A)).items():
            env_all.pop(k, None) if v is None else env_all.__setitem__(k, str(v))
        one = letter(q, "NORTH/hub", "a letter for the window with the awkward name")
        pm(q, "--pass", "--no-pull")
        proc = subprocess.Popen(["bash", "-c", '%s --hub "%s"' % (cmd, q["hub"])],
                                cwd=str(q["hub"]), env=env_all, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True)
        try:
            out, _ = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            out = "(TIMEOUT)"
        check(tok(q, one) in out,
              "THE COMMAND RUNS AS GIVEN UNDER BASH and carries the letter: %s" % out.strip()[-70:])
        ear = q["hub"] / "ear-north-hub.json"
        got = json.loads(io.open(str(ear), encoding="utf-8").read()).get("title") \
            if ear.is_file() else None
        check(got == nasty_title, "…and the ear carries the title BYTE-EXACT: %r" % got)
        check(not pwn1.exists() and not pwn2.exists(),
              "…and it touched NOTHING ELSE: neither $( ) nor the backtick pair ever ran")

    start("PB18g", "the hot path: one stat on the three untouched events, three at most on Stop")
    h = pworld("pb18g")
    claude_transcript(h, SID_A)
    run([PY, str(h["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(h["hub"]), "--mind", "FABLE"],
        cwd=str(h["hub"]), env=dict(h["env"], **as_session(SID_A)))
    for event in ("PostToolBatch", "UserPromptSubmit", "SessionStart"):
        n = stats_for(h, SID_A, event)
        check(n == 1, "%s with nothing pending: %s stat(s) — phase A's own path, untouched"
              % (event, n))
    n = stats_for(h, "nobody-at-all", "Stop")
    check(n is not None and n <= 3,
          "Stop, a session that holds nothing: %s stat(s) — the holds row is absent and it "
          "stops there" % n)
    write(h["post"] / "waiters" / ("%s.alive" % SID_A), iso(datetime.datetime.now().astimezone()))
    n = stats_for(h, SID_A, "Stop")
    check(n is not None and n <= 3,
          "Stop, a session holding a lane with its waiter alive: %s stat(s), at most three "
          "— pending, the holds row, the alive mark, and the decision is made" % n)
    os.unlink(str(h["post"] / "waiters" / ("%s.alive" % SID_A)))
    told = stats_for(h, SID_A, "Stop")
    check(told is not None,
          "…and the pass that actually TELLS costs %s, the one write included (measured, "
          "not budgeted: it happens at most three times per session per 10 min)" % told)
    spans = []
    for event in ("UserPromptSubmit", "Stop"):
        t0 = time.time()
        for _ in range(20):
            hook(h, "nobody-at-all", event)
        spans.append((event, (time.time() - t0) / 20.0 * 1000))
    for event, ms in spans:
        check_timed(ms, "…and it stays cheap enough to run every round: %s" % event)


def run_waiter(w, sid, address, lived, max_hours=0.02):
    """mail.py's OWN wait(), through the driver, with ALIVE_LIVED_S set to what
    this case needs "a waiter that lived" to mean."""
    return run([PY, str(w["base"] / "waitdrv.py"), str(w["hub"] / "tools" / "mail.py"),
                str(lived), str(w["hub"]), address, str(max_hours)],
               cwd=str(w["hub"]), env=dict(w["env"], **as_session(sid)), timeout=180)


def read_hold(w, sid):
    path = w["post"] / "holds" / ("%s.json" % sid)
    if not path.is_file():
        return {}
    return json.loads(io.open(str(path), encoding="utf-8").read())


def stats_for(w, sid, event):
    """How many os.stat calls the hook's own code path makes for this event."""
    payload = {"session_id": sid, "hook_event_name": event, "cwd": str(w["hub"]),
               "transcript_path": ""}
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in w["env"].items():
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    p = subprocess.run([PY, str(w["base"] / "statcount.py"),
                        str(w["hub"] / "tools" / "postman.py"), str(w["post"])],
                       input=json.dumps(payload), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=60)
    m = re.search(r"STATS=(\d+)", p.stderr or "")
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------
# PB19 (phase B P19) — the nudge
# --------------------------------------------------------------------------

def case_pb19():
    start("PB19", "the nudge: the human as the road of last resort, one move")
    w = bworld("pb19")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    one = letter(w, "NORTH/hub", "a cut order nobody can carry", ASK_ACTION)
    two = letter(w, "NORTH/hub", "and a second one", "plug in the drive — the backup waits on it")
    pmn(w, "--pass", "--no-pull")
    check(not nudges_of(w), "nothing is nudged at once — the letters have just landed")
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=6))
    nud = nudges_of(w)
    check(len(nud) == 1, "at nudge_minutes, ONE nudge for the address (%d)" % len(nud))
    row = list(nud.values())[0] if nud else {}
    check(row.get("case") == "N1", "its window is idle, so it is case N1: %s" % row.get("case"))
    # the notice is the consequence line(s) + the window's title.  No
    # sender, count, minutes or subject, no «say mail»; a banner renders no link, so the title is
    # in «» (no link in a banner).
    text = row.get("text", "")
    check(text == "%s · plug in the drive · the backup waits on it — «%s»" % (ASK_LINE, HOLDER),
          "several letters, ONE notice: the consequence lines + the holder's title in «»: %s" % text)
    check(not any(x in text for x in RETIRED_WORDS) and " from " not in text
          and "a cut order" not in text and "6 min" not in text and "and 1 more" not in text,
          "…never the sender, the subject, the minutes, «is waiting», «say mail» or «A note for the»: %s"
          % text)
    check("not this one" not in text and "NORTH/hub has" not in text,
          "…no address code opens it, and a banner never says `not this one`")
    shown = [r for r in raises(w) if ASK_LINE in " ".join(r["argv"])]
    check(len(shown) == 1, "it is raised like any notice for Wren, once (%d)" % len(shown))
    if shown:
        check(shown[0]["argv"][1] == "",
              "…with NO subtitle (not `mail waiting`): %r" % shown[0]["argv"][1])
        check(shown[0]["argv"][2] == text and "not this one" not in shown[0]["argv"][2],
              "…and the banner's own body is the notice: %r" % shown[0]["argv"][2][:80])
    e = post_of(w)["letters"][tok(w, one)]
    check((e.get("nudged") or {}).get("case") == "N1",
          "the letter's own entry records it: %s" % e.get("nudged"))
    code, out = pm(w, "--status", "--no-pull")
    check("Wren was nudged at" in out, "--status says so: %s"
          % next((l for l in out.splitlines() if "nudged" in l), "(nothing)"))
    three = letter(w, "NORTH/hub", "a third, ten minutes later", "press the green button — the door unlocks")
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=20))
    check(len(nudges_of(w)) == 1,
          "at most ONE nudge per address per nudge_again_minutes (%d)" % len(nudges_of(w)))
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=45))
    check(len(nudges_of(w)) == 2, "…and one more once that window has passed (%d)"
          % len(nudges_of(w)))

    start("PB19b", "the nudge: no window open, and every letter that must never earn one")
    n = bworld("pb19b")
    nobody = letter(n, "NORTH/Nowhere", "no session holds that lane", ASK_ACTION)
    pmn(n, "--pass", "--no-pull")
    pmn(n, "--pass", "--no-pull", "--now", later(minutes=6))
    rows = list(nudges_of(n).values())
    check(len(rows) == 1 and rows[0].get("case") == "N2",
          "a lane nobody holds is case N2: %s" % [r.get("case") for r in rows])
    check(bool(rows) and rows[0].get("text", "") == "%s — NOWHERE: no window open" % ASK_LINE,
          "…its notice is the consequence line + `<lane>: no window open`: %s"
          % [r.get("text") for r in rows])
    check(bool(rows) and not any(x in rows[0].get("text", "") for x in RETIRED_WORDS)
          and "Exocortex" not in rows[0].get("text", ""),
          "…and says no sender, no «is waiting», no «say mail»")
    # A letter that asks the person nothing (an FYI, or the default `answer it`) earns NO row at all:
    # assert the emptiness, never index into it.
    n2 = bworld("pb19b2")
    letter(n2, "NORTH/Nowhere", "no session holds that lane, and it asks nothing", "none — FYI")
    letter(n2, "NORTH/Nowhere", "and a default one the lane would answer")
    pmn(n2, "--pass", "--no-pull")
    pmn(n2, "--pass", "--no-pull", "--now", later(minutes=6))
    rows_fyi = list(nudges_of(n2).values())
    check(rows_fyi == [], "letters that ask the person nothing earn no row: %s" % rows_fyi)
    check(not raises(n2), "…and no banner")

    # A QUIET LETTER NEVER NUDGES.  `none — FYI; …` is quiet by mail.is_quiet (the waiter's
    # test) and NOT by is_fyi (the narrow needle), so the old pass raised a note a person was asked
    # to click for.  An `answer it` beside it still does — and the note is about that one alone.
    q1 = bworld("pb19q1")
    plant_claim(q1, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(q1, SID_A)
    quiet_line = letter(q1, "NORTH/hub", "a heads-up nobody must answer",
                        "none — FYI; tell the Archive lane")
    qmail = load_mail(q1)
    check(qmail.is_quiet(quiet_line) and not qmail.is_fyi(quiet_line),
          "the fixture's letter is quiet by is_quiet and NOT by is_fyi (the old gap)")
    pmn(q1, "--pass", "--no-pull")
    pmn(q1, "--pass", "--no-pull", "--now", later(minutes=6))
    pmn(q1, "--pass", "--no-pull", "--now", later(minutes=45))
    # (the idle-window ANNOUNCE road is a different road and not this check's: only a NUDGE's banner)
    check(not nudges_of(q1) and not [o for o in (state_of(q1).get("owner") or {}).values()
                                     if o.get("kind") == "nudge"],
          "QUIET-LETTER CHECK: an action `none — FYI; …` earns NO nudge, at nudge_minutes or at "
          "twice the wait: %s" % sorted(nudges_of(q1)))
    q2 = bworld("pb19q2")
    plant_claim(q2, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(q2, SID_A)
    letter(q2, "NORTH/hub", "a heads-up nobody must answer", "none — FYI; tell the Archive lane")
    letter(q2, "NORTH/hub", "a question that needs the answer", ASK_ACTION)
    pmn(q2, "--pass", "--no-pull")
    pmn(q2, "--pass", "--no-pull", "--now", later(minutes=6))
    rows2 = list(nudges_of(q2).values())
    check(len(rows2) == 1 and rows2[0].get("count") == 1
          and rows2[0].get("text", "") == "%s — «%s»" % (ASK_LINE, HOLDER)
          and "a heads-up" not in rows2[0].get("text", "") and "Archive" not in rows2[0].get("text", ""),
          "…while a letter that asks the person beside it does, and the notice is that letter's "
          "consequence line alone: %s" % [r.get("text") for r in rows2])

    f = bworld("pb19c")
    plant_claim(f, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(f, SID_A)
    letter(f, "NORTH/hub", "NORTH FABLE woke at 09:00", "no reply needed — FYI")
    letter(f, "NOWHERE/hub", "a machine the fleet does not carry", ASK_ACTION)
    plant_claim(f, "Alpha/One", "north", "ACT — Alpha/One: one", session=SID_B)
    plant_claim(f, "Beta/One", "north", "ACT — Beta/One: two", session=SID_B)
    letter(f, "NORTH/One", "two lanes answer to that name", ASK_ACTION)
    pmn(f, "--pass", "--no-pull", "--now", later(minutes=9))
    text = " ".join(r.get("text", "") for r in nudges_of(f).values())
    check(not nudges_of(f) and ASK_LINE not in text,
          "an FYI letter never nudges, and an asking letter to an unknown or ambiguous address "
          "does not either: %s" % sorted(nudges_of(f)))
    check("NOWHERE" not in text, "an unknown machine never nudges — the sender was told at once")
    check("ONE" not in text and "NORTH/One" not in text,
          "an ambiguous address never nudges, for the same reason")

    t = bworld("pb19d")
    plant_claim(t, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(t, SID_A)
    tone = letter(t, "NORTH/hub", "its window is busy, not idle")
    pmn(t, "--pass", "--no-pull", "--now", later(minutes=-10))   # the letter is queued
    claude_transcript(t, SID_A, [claude_stdout(SID_A, "the window took another turn")])
    pmn(t, "--pass", "--no-pull", "--now", later(minutes=8))     # …and it has since taken a turn
    check(not nudges_of(t),
          "A HOLDER WHOSE TRANSCRIPT WAS WRITTEN AFTER THE LETTER IS NEVER NUDGED — its own "
          "hook carries the letter at its next round")
    a = bworld("pb19d2")
    plant_claim(a, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(a, SID_A)
    letter(a, "NORTH/hub", "its waiter is listening for it")
    pmn(a, "--pass", "--no-pull")
    write(a["post"] / "waiters" / ("%s.alive" % SID_A), iso(datetime.datetime.now().astimezone()))
    pmn(a, "--pass", "--no-pull", "--now", later(minutes=12))
    check(not nudges_of(a), "…and neither is one whose waiter is listening")

    start("PB19e", "the nudge: the carrier is never the idle window the nudge is about")
    c = bworld("pb19e")
    plant_claim(c, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(c, SID_A)
    claude_transcript(c, SID_B)
    plant_live(c, [SID_A, SID_B])
    letter(c, "NORTH/hub", "the idle holder must not be asked to push", ASK_ACTION)
    pmn(c, "--pass", "--no-pull")
    pmn(c, "--pass", "--no-pull", "--now", later(minutes=7))
    rows = list(nudges_of(c).values())
    check(len(rows) == 1, "one nudge was composed (%d)" % len(rows))
    push = (rows[0].get("owner") or {}).get("push") or {} if rows else {}
    check(push.get("session") != SID_A,
          "the carrier is NOT the idle holder the nudge is about: %s" % push.get("session"))
    check(push.get("session") == SID_B, "…it is the other live session: %s" % push.get("session"))
    # the window that carries it is NOT the holder; its hook line is the consequence + the
    # holder's window — with the holder's app id on the claim, a link (one click); with none, the title
    code, out, err = hook(c, SID_B, "UserPromptSubmit")
    says = next((l for l in context_of(out).splitlines() if l.startswith(ASK_LINE)), "")
    check(says.startswith("%s — «%s»  [" % (ASK_LINE, HOLDER)),
          "THE HOOK ROAD, in the window that is not the holder: the consequence line, then the "
          "holder's window: %r" % says[:90])
    check("](#" not in says and not any(x in says for x in RETIRED_WORDS) and " from " not in says,
          "…with no app id known the window is the title in «», and no sender or mail words: %r"
          % says[-60:])
    c2 = bworld("pb19e2")
    plant_claim(c2, "hub", "north", HOLDER, session=SID_A, host_session="local_gateholder")
    claude_transcript(c2, SID_A)
    claude_transcript(c2, SID_B)
    plant_live(c2, [SID_A, SID_B])
    letter(c2, "NORTH/hub", "the holder's window has a link", ASK_ACTION)
    pmn(c2, "--pass", "--no-pull")
    pmn(c2, "--pass", "--no-pull", "--now", later(minutes=7))
    code, out, err = hook(c2, SID_B, "UserPromptSubmit")
    says2 = next((l for l in context_of(out).splitlines() if l.startswith(ASK_LINE)), "")
    check(says2.startswith("%s — [%s](#local_gateholder)  [" % (ASK_LINE, HOLDER))
          and not any(x in says2 for x in RETIRED_WORDS),
          "…and with the claim's host_session the window is ONE CLICK, [title](#local_…): %r"
          % says2[-90:])
    nd2 = list(nudges_of(c2).values())
    check(nd2 and nd2[0].get("text", "") == "%s — «%s»" % (ASK_LINE, HOLDER)
          and "](#" not in nd2[0].get("text", ""),
          "…while the banner's own text (and the toast) never carries a link")

    start("PB19f", "a nudge's token hashes its LETTERS, never a clock (punch list F8)")
    k = bworld("pb19f")
    plant_claim(k, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(k, SID_A)
    letter(k, "NORTH/hub", "the first of two the nudge gathers", ASK_ACTION)
    letter(k, "NORTH/hub", "and the second", "plug in the drive — the backup waits on it")
    pmn(k, "--pass", "--no-pull")
    pmn(k, "--pass", "--no-pull", "--now", later(minutes=6))
    first = sorted(state_of(k).get("nudges") or {})
    check(len(first) == 1, "one nudge was composed (%d)" % len(first))
    # A PASS THAT DIED AFTER COMPOSING: its state.json never reached disk, so the
    # next pass composes the same nudge from the same letters — and must mint the
    # SAME token, or the one note would be raised twice.
    body = state_of(k)
    body.pop("nudges", None)
    body.pop("owner", None)
    for e in (body.get("letters") or {}).values():
        e.pop("nudged", None)
    write_state(k, body)
    pmn(k, "--pass", "--no-pull", "--now", later(minutes=9))
    again = sorted(state_of(k).get("nudges") or {})
    check(again == first,
          "a pass that died after composing re-mints the SAME token at a different --now: "
          "%s then %s" % (first, again))
    kmod = load_postman(k)
    check(kmod.nudge_token("NORTH/hub", ["pm-bbbbbbbbbbbb", "pm-aaaaaaaaaaaa"])
          == kmod.nudge_token("NORTH/hub", ["pm-aaaaaaaaaaaa", "pm-bbbbbbbbbbbb"]),
          "…and the letters are sorted inside it, so their order cannot change it either")

    start("PB19g", "no nudge on a machine where nobody said `install it` (punch list 2 F12)")
    u = bworld("pb19g")
    uninstall_marker(u)
    plant_claim(u, "hub", "north", HOLDER, session=SID_A)
    age_file(claude_transcript(u, SID_A), 600)   # idle since before the letter was queued
    letter(u, "NORTH/hub", "a letter nobody will be nudged about", ASK_ACTION)
    pmn(u, "--pass", "--no-pull")
    pmn(u, "--pass", "--no-pull", "--now", later(minutes=6))
    check(not (state_of(u).get("nudges") or {}) and not nudges_of(u),
          "nothing is nudged, in the state or in the post file: %s"
          % sorted(state_of(u).get("nudges") or {}))
    check(not raises(u), "…and the notifier was never asked")
    install_marker(u)                            # the word, said at this machine
    pmn(u, "--pass", "--no-pull", "--now", later(minutes=12))
    rows = list((state_of(u).get("nudges") or {}).values())
    check(len(rows) == 1 and rows[0].get("to") == "NORTH/hub",
          "…and once the word is said the same world nudges, once: %s"
          % [r.get("to") for r in rows])

    start("PB19h", "a nudge's push text has no leading `: ` (punch list 2 F14)")
    # The frame that reached a carrier used to read `: NORTH/Release has 1
    # letter(s) waiting 23 min …`: `push_text()` rendered "<target>: <text>"
    # even with an empty target, and a NUDGE has no target — its raise carries
    # no subtitle at all now. That colon was on its way to Wren's phone.
    x = bworld("pb19h")
    claude_transcript(x, SID_A)
    plant_live(x, [SID_A])
    letter(x, "NORTH/Cutting", "a letter no road can carry", ASK_ACTION)
    pmn(x, "--pass", "--no-pull")
    pmn(x, "--pass", "--no-pull", "--now", later(minutes=6))
    nd = [(t, r) for t, r in sorted((state_of(x).get("owner") or {}).items())
          if r.get("kind") == "nudge"]
    check(len(nd) == 1, "one nudge is a notice for Wren (%d)" % len(nd))
    ptext = str((nd[0][1].get("push_text") if nd else "") or "")
    check(ptext == "%s — CUTTING: no window open" % ASK_LINE,
          "its push text is the consequence line + `<lane>: no window open`, with no colon "
          "before it: %r" % ptext[:60])
    shown = [r for r in raises(x) if ASK_LINE in " ".join(r["argv"])]
    check(shown and not shown[0]["argv"][2].startswith(": "),
          "the banner's body carries none either: %r"
          % (shown[0]["argv"][2][:40] if shown else "(no raise)"))
    check(shown and shown[0]["argv"][1] == "",
          "…and the subtitle is empty (BQ-365: no `mail waiting`): %r"
          % (shown[0]["argv"][1] if shown else "(no raise)"))
    code, out, err = hook(x, SID_A, "UserPromptSubmit")
    frame_line = next((l for l in context_of(out).splitlines() if l.startswith("POST — a line for")), "")
    check(frame_line and (": %s — CUTTING: no window open" % ASK_LINE) in frame_line
          and "a note for" not in frame_line.lower(),
          "and the frame the carrier reads carries the notice's own words, after its fixed frame: %r"
          % frame_line[:90])
    xmod = load_postman(x)
    check(xmod.push_text("Exocortex", "the gate line printed", "no action")
          == "Exocortex: the gate line printed — no action",
          "A LETTER'S push text is exactly what it always was: %r"
          % xmod.push_text("Exocortex", "the gate line printed", "no action"))


# --------------------------------------------------------------------------
# PB20 (phase B P20) — the ack
# --------------------------------------------------------------------------

def case_pb20():
    start("PB20", "`got it`: one word in any session, and the note stops waiting everywhere")
    w = bworld("pb20")
    one = letter(w, "OWNER", OWNER_NOTE, "no action")
    t = tok(w, one)
    before = io.open(str(w["hub"] / "INBOX.md"), "rb").read()
    pmn(w, "--pass", "--no-pull")
    pmod = load_postman(w)
    check(len(pmod.owner_rows(w["hub"])) == 1, "one note is waiting for Wren")
    code, out = mp(w, "--ack", t)
    check(code == 0 and "acked: 1 note(s) for Wren" in out, "--ack <token> says so: %s" % out.strip())
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    check((owner_of(w, t).get("acked") or {}).get("when"),
          "the pass folds it into the note's own entry: %s" % owner_of(w, t).get("acked"))
    check(not pmod.owner_rows(w["hub"]), "…and nothing is waiting any more")
    facts = pmod.tree_facts(w["hub"])
    check(not (facts.get("owner") or []), "tree_facts drops it too")
    code, out = mp(w, "--read", "OWNER")
    check(t not in out, "--read OWNER no longer lists it: %s" % out.strip()[:90])
    check(io.open(str(w["hub"] / "INBOX.md"), "rb").read() == before,
          "and INBOX.md is byte-identical — an ack never rewrites the mailbox")
    code, out = mp(w, "--ack", "OWNER")
    check("nothing to ack" in out, "with nothing waiting, --ack OWNER says `nothing to ack`")

    start("PB20b", "`got it`: OWNER clears them all, and an ack from the other machine counts")
    x = bworld("pb20b")
    a = letter(x, "OWNER", "the first note", "no action")
    b = letter(x, "OWNER", "the second note", "no action")
    pmn(x, "--pass", "--no-pull")
    code, out = mp(x, "--ack", "OWNER", "--title", HOLDER)
    check("acked: 2 note(s) for Wren" in out, "--ack OWNER clears every note waiting: %s" % out.strip())
    pmn(x, "--pass", "--no-pull", "--now", later(minutes=1))
    check((owner_of(x, tok(x, a)).get("acked") or {}).get("by") == HOLDER,
          "…recording who said it: %s" % owner_of(x, tok(x, a)).get("acked"))

    y = bworld("pb20c")
    c = letter(y, "OWNER", "acked from the other machine", "no action")
    t = tok(y, c)
    pmn(y, "--pass", "--no-pull")
    write_json(y["hub"] / "post-south.json",
               {"machine": "south", "version": 1, "sent": {}, "letters": {},
                "nudges": {t: {"kind": "nudge", "to": "OWNER", "text": "x",
                               "first_seen": iso(datetime.datetime.now().astimezone()),
                               "owner": {"acked": {"when": later(minutes=-1), "by": "SOUTH hub"}}}}})
    pmn(y, "--pass", "--no-pull", "--now", later(minutes=1))
    check((owner_of(y, t).get("acked") or {}).get("by") == "SOUTH hub",
          "a note acked on ANY machine is acked on all: %s" % owner_of(y, t).get("acked"))

    start("PB20d", "`--ack` checks a token BEFORE it becomes a file name (punch list F3)")
    # `--ack ../../x` wrote <post>/acks/../../x.json, and `--ack hello` answered
    # `acked: 1 note(s) for Wren` — unchecked text became a file name, and the
    # tool said "acked" to anything at all.
    z = bworld("pb20d")
    zone = letter(z, "OWNER", "a real note, so the good road is proved beside the bad", "no action")
    pmn(z, "--pass", "--no-pull")
    before = fingerprint(z["post"])
    outside = sorted(p.name for p in z["post"].parent.iterdir())
    for bad in ("../../x", "hello", "pm-000000000000", "pm-0000000000",
                "nd-zzzzzzzzzzzz", "PM-000000000000", "  "):
        code, out = mp(z, "--ack", bad)
        check(code == 0 and "nothing to ack" in out,
              "--ack %r → `nothing to ack`, exit 0: %s" % (bad, out.strip()))
    check(fingerprint(z["post"]) == before,
          "POST DIR is byte-identical: not one ack file was written")
    check(sorted(p.name for p in z["post"].parent.iterdir()) == outside,
          "…and nothing was written up and out of its parent either (`../../x`)")
    code, out = mp(z, "--ack", tok(z, zone))
    check("acked: 1 note(s) for Wren" in out,
          "…while the note's real token still acks: %s" % out.strip())
    write_json(z["post"] / "acks" / "sneaky.json",
               {"token": "../../x", "when": later(), "by": "nobody"})
    write_json(z["post"] / "acks" / "pm-000000000002.json",
               {"token": "hello", "when": later(), "by": "nobody"})
    pmn(z, "--pass", "--no-pull", "--now", later(minutes=1))
    check(sorted(state_of(z).get("acks") or {}) == [tok(z, zone)],
          "and the pass folds in ONLY the acks whose file name AND token are tokens: %s"
          % sorted(state_of(z).get("acks") or {}))

    start("PB20e", "ONE ROW PER TOKEN: a note two machines have seen is ONE note (F4)")
    # A `to: OWNER` letter is owned by EVERY machine that sees it, so once both
    # machines run this build the same token carries a `owner` key in both post
    # files: `tree_facts` gave two rows — `✉ 2 for you` — and `--ack OWNER` said
    # `acked: 2 note(s) for Wren`. One note.
    d = bworld("pb20e")
    dnote = letter(d, "OWNER", "the drive is safe to eject", "no action")
    td = tok(d, dnote)
    pmn(d, "--pass", "--no-pull")
    mine = post_of(d)["letters"][td]
    write_json(d["hub"] / "post-south.json",
               {"machine": "south", "version": 1, "sent": {}, "nudges": {},
                "letters": {td: dict(mine, owner={"raised": {"when": later(minutes=-2),
                                                            "how": "none",
                                                            "why": "nobody is at this machine"}})}})
    dmod = load_postman(d)
    rows = dmod.owner_rows(d["hub"])
    check(len(rows) == 1, "two post files, one token: ONE row (%d)" % len(rows))
    views = (rows[0].get("views") or []) if rows else []
    check([v["machine"] for v in views] == ["north", "south"],
          "…carrying one view per machine, THIS MACHINE'S FIRST: %s"
          % [v["machine"] for v in views])
    check(len(views) == 2
          and (views[0].get("raised") or {}).get("how") in ("osascript", "toast")
          and (views[1].get("raised") or {}).get("why") == "nobody is at this machine",
          "…each machine's own raise, in its own words: %s"
          % [(v["machine"], (v.get("raised") or {}).get("how")
              or (v.get("raised") or {}).get("why")) for v in views])
    check(len(dmod.tree_facts(d["hub"]).get("owner") or []) == 1,
          "tree_facts says ONE too (%d)" % len(dmod.tree_facts(d["hub"]).get("owner") or []))
    code, out = mp(d, "--ack", "OWNER")
    check("acked: 1 note(s) for Wren" in out,
          "…and `--ack OWNER` counts DISTINCT tokens: %s" % out.strip())
    check(len(list((d["post"] / "acks").glob("*.json"))) == 1,
          "…writing one ack file, not two")

    a2 = bworld("pb20e2")
    a2note = letter(a2, "OWNER", "acked on the other machine only", "no action")
    t2 = tok(a2, a2note)
    pmn(a2, "--pass", "--no-pull")
    mine2 = post_of(a2)["letters"][t2]
    write_json(a2["hub"] / "post-south.json",
               {"machine": "south", "version": 1, "sent": {}, "nudges": {},
                "letters": {t2: dict(mine2, owner={"raised": {"when": later(minutes=-2),
                                                             "how": "none", "why": "not here"},
                                                  "acked": {"when": later(minutes=-1),
                                                            "by": "SOUTH hub"}})}})
    a2mod = load_postman(a2)
    check(not a2mod.owner_rows(a2["hub"]),
          "a note acked in ONE view is acked in all — nothing is waiting")
    check(not (a2mod.tree_facts(a2["hub"]).get("owner") or []), "…and the chip is gone")

    start("PB20f", "AN ACKED NOTE NEVER RUNS THE PHONE LEG (punch list 2 F13)")
    # The phone leg tested `raised.how` and `push.state` and never `acked`: the
    # notes Wren had acked kept their `queued` push, could still be
    # moved to another window, and would have ended only by `lapsed` at thirty
    # minutes. An ack is Wren saying he has seen it.
    f = bworld("pb20f")
    claude_transcript(f, SID_A)
    plant_live(f, [SID_A])
    fone = letter(f, "OWNER", "the drive has finished writing", "no action")
    tf = tok(f, fone)
    pmn(f, "--pass", "--no-pull")
    push = owner_of(f, tf).get("push") or {}
    check(push.get("state") == "queued" and push.get("session") == SID_A,
          "it is raised, and the one live window is queued to push it: %s" % push.get("state"))
    check([i for i in pending_of(f, SID_A) if i.get("kind") == "owner"],
          "…the item is in that window's pending file")
    code, out = mp(f, "--ack", tf, "--title", HOLDER)
    check("acked: 1 note(s) for Wren" in out,
          "Wren says `got it` before the window takes its turn: %s" % out.strip())
    pmn(f, "--pass", "--no-pull", "--now", later(minutes=1))
    push = owner_of(f, tf).get("push") or {}
    check(push.get("state") == "acked", "the push reads `acked`: %s" % push.get("state"))
    check(str(push.get("why") or "").startswith("acked by %s at " % HOLDER),
          "…and says who ended it and when: %s" % push.get("why"))
    check(not [i for i in pending_of(f, SID_A) if i.get("kind") == "owner"],
          "THE ITEM IS GONE from the carrier's pending file")
    code, out, err = hook(f, SID_A, "UserPromptSubmit")
    check("PushNotification" not in context_of(out),
          "…so NO FRAME IS EVER DELIVERED: the window is never asked to make the call")
    pmn(f, "--pass", "--no-pull", "--now", later(minutes=31))
    push = owner_of(f, tf).get("push") or {}
    check(push.get("state") == "acked",
          "…and no later pass reassigns it or lapses it: %s" % push.get("state"))
    check(not raises(f) or len(raises(f)) == 1,
          "…and it was raised once and only once (%d)" % len(raises(f)))

    start("PB20g", "…and its sender is told `acked`, not `asked of «a window»`")
    s = bworld("pb20g")
    claude_transcript(s, SID_A)
    plant_live(s, [SID_A])
    mp(s, "--send", "OWNER", "Exocortex", "the payload is sealed", "no action", "--no-push",
       env=as_session(SID_A))
    ts = [tk for tk in post_of(s)["for_owner"]][0]
    mp(s, "--ack", ts, "--title", HOLDER)
    pmn(s, "--pass", "--no-pull", "--now", later(minutes=1))
    notices = [i for i in pending_of(s, SID_A) if i.get("kind") == "notice"]
    check(len(notices) == 1, "exactly one notice for the sender (%d)" % len(notices))
    text = notices[0]["text"] if notices else ""
    check("· phone: acked" in text, "…and its phone clause is `acked`: %s" % text)


# --------------------------------------------------------------------------
# PB21 (phase B P21) — the sender of a note, and R3
# --------------------------------------------------------------------------

def case_pb21():
    start("PB21", "the sender of a note for Wren hears once, and hears the truth")
    w = bworld("pb21")
    claude_transcript(w, SID_A)
    plant_live(w, [SID_A])
    code, out = mp(w, "--send", "OWNER", "Exocortex", OWNER_NOTE, "no action", "--no-push",
                   env=as_session(SID_A))
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    notices = [i for i in pending_of(w, SID_A) if i.get("kind") == "notice"]
    check(len(notices) == 1, "exactly one notice for the sender (%d)" % len(notices))
    text = notices[0]["text"] if notices else ""
    check(text.startswith("POST — your note to OWNER of "), "in its own form: %s" % text)
    check("raised on the NORTH" in text and "· phone:" in text,
          "…saying where it was raised and what the phone leg did: %s" % text)
    check(notices and notices[0].get("wake") is False,
          "…queued `wake: false`: it never wakes a sleeping window")
    check("is not read yet" not in text,
          "and NEVER phase A's five-minute `not read yet` — OWNER is not a session with a mailbox")
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=20))
    notices = [i for i in pending_of(w, SID_A) if i.get("kind") == "notice"]
    check(len(notices) == 1, "…and it is never said twice (%d)" % len(notices))

    n = bworld("pb21b", live=False)
    claude_transcript(n, SID_B)
    write_json(n["hub"] / "post-config.json", {"owner_notify": False})
    mp(n, "--send", "OWNER", "Exocortex", "a note nobody will raise", "no action", "--no-push",
       env=as_session(SID_B))
    pmn(n, "--pass", "--no-pull", "--now", later(minutes=1))
    texts = [i.get("text", "") for i in pending_of(n, SID_B) if i.get("kind") == "notice"]
    check(any(t.startswith("POST — your note to OWNER of ") and "was not raised:" in t
              for t in texts),
          "a note that was not raised says so, with the reason: %s" % texts)

    f = bworld("pb21c")
    claude_transcript(f, SID_A)
    mp(f, "--send", "OWNER", "Exocortex", "an FYI note", "no reply needed — FYI", "--no-push",
       env=as_session(SID_A))
    pmn(f, "--pass", "--no-pull", "--now", later(minutes=20))
    check(not [i for i in pending_of(f, SID_A) if i.get("kind") == "notice"],
          "an FYI note earns its sender nothing at all")

    start("PB21d", "R3: a `wake: false` item never ends a wait — and since BQ-143/144 no notice does")
    r = pworld("pb21d")
    claude_transcript(r, SID_A)
    write_json(r["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})
    write_json(r["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": "pm-000000000001", "kind": "notice", "fyi": False,
                           "wake": False, "to": "NORTH/hub", "queued": iso(datetime.datetime.now().astimezone()),
                           "text": "POST — nobody on the NORTH holds Nowhere."},
                          {"token": "pm-000000000002", "kind": "owner", "fyi": False,
                           "wake": False, "to": "OWNER", "push": "Exocortex: a note",
                           "queued": iso(datetime.datetime.now().astimezone())}]})
    proc = waiter(r, "NORTH/hub", None, env=as_session(SID_A))
    try:
        time.sleep(11)
        check(proc.poll() is None,
              "a pending file holding ONLY `wake: false` items leaves the waiter running")
        check((r["post"] / "waiters" / ("%s.alive" % SID_A)).is_file(),
              "…and its alive mark is there while it listens")
        write_json(r["post"] / "pending" / ("%s.json" % SID_A),
                   {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": [{"token": "pm-000000000003", "kind": "notice", "fyi": False,
                               "to": "NORTH/hub", "queued": iso(datetime.datetime.now().astimezone()),
                               "text": "POST — your letter to NORTH/hub of 09:00 is not read yet (5 min): idle."}]})
        time.sleep(6)
        check(proc.poll() is None,
              "…and an ordinary five-minute notice no longer ends it either (notices never wake, "
              "the hub's ruling on BQ-143/144 Part A)")
        check([i.get("token") for i in pending_of(r, SID_A)] == ["pm-000000000003"],
              "…it waits in the pending file for the window's next turn start")
        items = pending_of(r, SID_A) + [{
            "token": "pm-000000000004", "kind": "letter", "fyi": False, "to": "NORTH/hub",
            # dated TODAY: since a letter dated before the wait was armed never ends it
            "line": "- %s · to: NORTH/hub · Exocortex · the ask that ends it · answer it"
                    % datetime.date.today().isoformat(),
            "queued": iso(datetime.datetime.now().astimezone())}]
        write_json(r["post"] / "pending" / ("%s.json" % SID_A),
                   {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": items})
        out, _ = proc.communicate(timeout=30)
        check("pm-000000000004" in out and "pm-000000000003" not in out,
              "…an ASKING letter ends the wait the ordinary way, and the notice stays queued")
    except subprocess.TimeoutExpired:
        proc.kill()
        check(False, "the waiter answered (it hung)")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
    code, out, err = hook(r, SID_A, "UserPromptSubmit")
    check(not (r["post"] / "waiters" / ("%s.alive" % SID_A)).is_file(),
          "and the alive mark is gone the moment the waiter exits, whichever way it went")


# --------------------------------------------------------------------------
# PB22 (phase B P22) — R4, the scratch-hub leak
# --------------------------------------------------------------------------

def case_pb22():
    start("PB22", "R4: a tool pointed at another hub never touches this machine's real post folder")
    w = pworld("pb22")                        # w['post'] IS this machine's real POST DIR
    claude_transcript(w, SID_A)
    other = w["base"] / "elsewhere"
    (other / "tools").mkdir(parents=True, exist_ok=True)
    for name in TOOLS:
        shutil.copy2(str(w["hub"] / "tools" / name), str(other / "tools" / name))
    write(other / "INBOX.md", "# INBOX\n\n")
    before = fingerprint(w["post"])
    env = dict(w["env"], **as_session(SID_A))
    run([PY, str(other / "tools" / "mail.py"), "--send", "NORTH/hub", "Exocortex",
         "a letter written in a rehearsal", "answer it", "--no-push", "--hub", str(other)],
        cwd=str(other), env=env)
    run([PY, str(other / "tools" / "mail.py"), "--read", "NORTH/hub", "--title", HOLDER,
         "--hub", str(other)], cwd=str(other), env=env)
    run([PY, str(other / "tools" / "postman.py"), "--pass", "--no-pull", "--hub", str(other)],
        cwd=str(other), env=env)
    proc = subprocess.Popen([PY, str(other / "tools" / "mail.py"), "--wait", "NORTH/hub",
                             "--hub", str(other)], cwd=str(other),
                            env=dict(os.environ, **dict((k, str(v)) for k, v in env.items()
                                                        if v is not None)),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    time.sleep(6)
    proc.kill()
    proc.wait(timeout=10)
    after = fingerprint(w["post"])
    check(before == after,
          "a send, a read, a pass and a wait against a FOREIGN hub leave the real POST DIR "
          "byte-identical (%d files before, %d after)" % (len(before), len(after)))
    check((other / ".post").is_dir(), "…because the rehearsal kept its own state in <that hub>/.post/")
    check((other / ".post" / "outbox").is_dir() and list((other / ".post" / "outbox").glob("*.json")),
          "…outbox record included — the very file that leaked on 2026-09-20")
    check(not (w["hub"] / "post-north.json").is_file() or
          "rehearsal" not in io.open(str(w["hub"] / "post-north.json"), encoding="utf-8").read(),
          "…and no phantom token reached the real, brain-synced post file")
    if os.name != "nt":
        check((os.stat(str(other / ".post")).st_mode & 0o777) == 0o700,
              "the rehearsal's own POST DIR is 0700, like any other")

    start("PB22b", "R4: the machine's OWN hub behaves exactly as it did")
    m = pworld("pb22b")
    claude_transcript(m, SID_A)
    plant_claim(m, "hub", "north", HOLDER, session=SID_A)
    one = letter(m, "NORTH/hub", "a letter at home")
    run([PY, str(m["hub"] / "tools" / "postman.py"), "--pass", "--no-pull", "--hub", str(m["hub"])],
        cwd=str(m["hub"]), env=m["env"])
    check(any(i["token"] == tok(m, one) for i in pending_of(m, SID_A)),
          "--hub <this machine's own hub> still uses roots.post, exactly as before")
    check(not (m["hub"] / ".post").exists(), "…and makes no .post folder beside it")
    code, out = run([PY, str(m["hub"] / "tools" / "postman.py"), "--pass", "--no-pull",
                     "--hub", str(m["hub"]), "--post-dir", str(m["post"])],
                    cwd=str(m["hub"]), env=m["env"])
    check(code == 0, "and an explicit --post-dir still wins over everything")

    start("PB22c", "F1: with NO roots.orchestrator every road still finds ONE post folder")
    # A stranger's fresh install: machine.json names the machine and nothing
    # else. own_hub() was None, so post_dir() called EVERY hub foreign — mail.py,
    # claim.py and exo_common.py ALWAYS pass one — while the hook and a bare
    # --pass kept using <home>/.exocortex/post. The waiter polled
    # <hub>/.post/pending while the postman queued into the other folder: MAIL
    # WAS NEVER HEARD, and `.post/` sat inside the brain-synced hub folder.
    n = world("pb22c")
    write_json(n["home"] / "orchestrator-sync" / "machine.json", {"name": "north"})
    write(n["hub"] / "INBOX.md", "# INBOX\n\n")
    one_post = n["home"] / ".exocortex" / "post"
    nenv = dict(n["env"], **as_session(SID_A))
    claude_transcript(n, SID_A)
    run([PY, str(n["hub"] / "tools" / "postman.py"), "--pass", "--no-pull", "--quiet",
         "--hub", str(n["hub"])], cwd=str(n["hub"]), env=nenv)
    check((one_post / "state.json").is_file(),
          "`--pass --hub <that hub>` keeps its state in <home>/.exocortex/post")
    run([PY, str(n["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(n["hub"]), "--mind", "FABLE"], cwd=str(n["hub"]), env=nenv)
    check((one_post / "holds" / ("%s.json" % SID_A)).is_file(),
          "…and claim.py, which always passes a hub, writes its holds row into the SAME one")
    run([PY, str(n["hub"] / "tools" / "postman.py"), "--pass", "--no-pull", "--quiet"],
        cwd=str(n["hub"]), env=nenv)
    check((one_post / "heartbeat.json").is_file(),
          "…and so does a --pass with no --hub at all")
    henv = dict(os.environ)
    henv["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in nenv.items():
        henv.pop(k, None) if v is None else henv.__setitem__(k, str(v))
    proc = subprocess.run([PY, str(n["hub"] / "tools" / "postman.py"), "--hook",
                           "--vendor", "claude"],
                          input=json.dumps({"session_id": SID_A, "hook_event_name": "Stop",
                                            "cwd": str(n["hub"]), "transcript_path": ""}),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, env=henv, timeout=60)
    check("[arm]" in context_of(proc.stdout),
          "THE HOOK, carrying no --post-dir, reads that very holds row and asks it to arm")
    check((one_post / "told" / ("%s.json" % SID_A)).is_file(),
          "…and writes its tell count beside it")
    wproc = subprocess.Popen([PY, str(n["hub"] / "tools" / "mail.py"), "--wait", "NORTH/hub",
                              "--hub", str(n["hub"])], cwd=str(n["hub"]), env=henv,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
    alive = one_post / "waiters" / ("%s.alive" % SID_A)
    try:
        for _ in range(100):
            if alive.is_file():
                break
            time.sleep(0.1)
        check(alive.is_file(),
              "…and `mail.py --wait` listens in that same folder — ONE POST DIR, five roads")
    finally:
        wproc.kill()
        wproc.wait(timeout=10)
    check(not (n["hub"] / ".post").exists(),
          "NO .post/ APPEARS INSIDE THE BRAIN-SYNCED HUB FOLDER at all")

    start("PB22d", "F1: a record that names the hub through a symlink is not a rehearsal")
    if os.name == "nt":
        skip("a junction needs an elevated mklink on Windows; the macOS symlink proves the "
             "same one comparison — NOT RUN on this OS")
    else:
        s = pworld("pb22d")
        old = s["base"] / "the-old-hub-name"
        os.symlink(str(s["hub"]), str(old))
        rec = json.loads(io.open(str(s["home"] / "orchestrator-sync" / "machine.json"),
                                 encoding="utf-8").read())
        rec["roots"]["orchestrator"] = str(old)        # …exactly as both of Wren's machines do
        write_json(s["home"] / "orchestrator-sync" / "machine.json", rec)
        claude_transcript(s, SID_A)
        plant_live(s, [SID_A])
        one = letter(s, "OWNER", "a note on a hub the record reaches by its old name", "no action")
        # NO --hub, so the hub comes from the RECORD and is NOT resolved — which
        # is the shape the finding is about: main() compared that unresolved
        # path with a resolved own_hub() and called the real hub a rehearsal.
        # Read through the no-seam driver, the one road on which the flag is
        # visible and a real banner is still impossible.
        run([PY, str(s["base"] / "nonotify.py"), str(s["hub"] / "tools" / "postman.py"),
             "--pass", "--no-pull", "--post-dir", str(s["post"])],
            cwd=str(s["hub"]), env=s["env"])
        # A rehearsal records `how: none · why: …a rehearsal never raises · tries: 0`;
        # a REAL hub with no notifier records `how: none · why: "" · tries: 1`,
        # because raise_note was actually called and answered.
        got = ((owner_of(s, tok(s, one)) or {}).get("raised") or {})
        kept = (((state_of(s).get("owner") or {}).get(tok(s, one)) or {}).get("raised") or {})
        check(got.get("how") == "none" and not (got.get("why") or "")
              and int(kept.get("tries") or 0) == 1,
              "THE REAL HUB IS NEVER CALLED A REHEARSAL: the pass got all the way to the "
              "raise itself (tries=%s), and only the notifier was missing: %s"
              % (kept.get("tries"), got))
        check(not raises(s), "…and not one notifier process was started on that road")
        two = letter(s, "OWNER", "and one more, this time through the seam", "no action")
        pmn(s, "--pass", "--no-pull", "--now", later(minutes=1))
        check(((owner_of(s, tok(s, two)) or {}).get("raised") or {}).get("how")
              in ("osascript", "toast"),
              "…and with a seam in place a note on that hub IS raised: %s"
              % ((owner_of(s, tok(s, two)) or {}).get("raised") or {}))
        check([r for r in raises(s) if "one more" in " ".join(r["argv"])],
              "…reaching the notifier's seam, as case (b) asks")
        check(not (s["hub"] / ".post").exists() and not (old / ".post").exists(),
              "…and no .post/ was made beside either name")
        smod = load_postman(s)
        check(smod.is_own_hub(str(old), str(s["home"])) is True
              and smod.is_own_hub(str(s["hub"]), str(s["home"])) is True,
              "both names answer the ONE question the same way")
        check(smod.is_own_hub(str(s["base"] / "elsewhere"), str(s["home"])) is False,
              "…and a hub that really is somebody else's still reads foreign")


def fingerprint(folder):
    out = {}
    for f in sorted(Path(folder).rglob("*")):
        if f.is_file():
            out[str(f.relative_to(folder))] = f.stat().st_size
    return out


# --------------------------------------------------------------------------
# PB23 (phase B P23) — R1 and R2
# --------------------------------------------------------------------------

def case_pb23():
    start("PB23", "R1: a refresh records the identity exactly as a first claim does")
    w = pworld("pb23")
    env = dict(w["env"], **as_session(SID_A))
    run([PY, str(w["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub", HOLDER,
         "--hub", str(w["hub"]), "--mind", "FABLE"], cwd=str(w["hub"]), env=env)
    plant = json.loads(io.open(str(w["hub"] / "claims.json"), encoding="utf-8").read())
    for c in plant:
        for key in ("session", "host_session", "vendor"):
            c.pop(key, None)                  # a row written before the postman existed
    write(w["hub"] / "claims.json", json.dumps(plant, ensure_ascii=False, indent=2) + "\n")
    code, out = run([PY, str(w["hub"] / "tools" / "claim.py"), "--quiet", "--claim", "hub",
                     HOLDER, "--hub", str(w["hub"])], cwd=str(w["hub"]), env=env)
    row = json.loads(io.open(str(w["hub"] / "claims.json"), encoding="utf-8").read())[0]
    check("HELD:" in out and "refreshed" in out, "it is still a refresh, and says so")
    check(row.get("session") == SID_A and row.get("vendor") == "claude"
          and row.get("host_session") == "local_gate",
          "A REFRESH RECORDS session, host_session and vendor: %s"
          % {k: row.get(k) for k in ("session", "vendor", "host_session")})
    check(read_hold(w, SID_A).get("session") == SID_A, "…and the holds cache is refreshed with it")
    one = letter(w, "NORTH/hub", "a letter for a lane whose claim was refreshed")
    claude_transcript(w, SID_A)
    pm(w, "--pass", "--no-pull")
    check(any(i["token"] == tok(w, one) for i in pending_of(w, SID_A)),
          "…so a letter to that lane ROUTES, where before it read `holder known by title only`")

    start("PB23b", "R2: a delivery names the window that read it")
    d = pworld("pb23b")
    plant_claim(d, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(d, SID_A)
    one = letter(d, "NORTH/hub", "who read this?")
    pm(d, "--pass", "--no-pull")
    code, out, err = hook(d, SID_A, "UserPromptSubmit")
    claude_transcript(d, SID_A, [claude_hook_context(SID_A, context_of(out))])
    pm(d, "--pass", "--no-pull", "--now", later(minutes=1))
    got = post_of(d)["letters"][tok(d, one)].get("delivered") or {}
    check(got.get("title") == HOLDER,
          "delivered.title carries the HOLDER's own title: %r" % got.get("title"))


# --------------------------------------------------------------------------
# PB24 (phase B P24) — the Windows leg, as far as a North can prove it
# --------------------------------------------------------------------------

def case_pb24():
    start("PB24", "the Windows leg: -EncodedCommand, the texts in the environment, no window")
    import base64
    w = world("pb24", machine="south")
    write_json(w["home"] / "orchestrator-sync" / "machine.json",
               {"name": "south", "os": "Windows",
                "roots": {"orchestrator": str(w["hub"]), "projects": str(w["projects"]),
                          "claude": str(w["home"] / ".claude"), "codex": str(w["home"] / ".codex"),
                          "post": str(w["post"])}})
    pmod = load_postman(w)
    argv, env_add, flags, how = pmod.notify_command("Exocortex", "Alpha", NASTY, kind="nt")
    check(how == "toast", "the Windows road is the toast: %r" % how)
    check(argv[:4] == ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand"],
          "…run with -NoProfile -NonInteractive -EncodedCommand: %s" % argv[:4])
    check(len(argv) == 5, "…and nothing else on the command line: %d parts" % len(argv))
    decoded = base64.b64decode(argv[4]).decode("utf-16-le")
    check(decoded == pmod.WIN_NOTIFY_SCRIPT,
          "the blob decodes from UTF-16LE to the FIXED script, byte for byte")
    check(NASTY not in decoded and "Alpha" not in decoded and "Exocortex" not in decoded,
          "NOT ONE of the texts is in the script source — they are never interpolated")
    check(env_add == {"EXO_NOTE_TITLE": "Exocortex — Alpha", "EXO_NOTE_BODY": NASTY},
          "…they reach the child in its ENVIRONMENT: %s" % sorted(env_add))
    check(flags == pmod.CREATE_NO_WINDOW,
          "…the child is started with no window (0x%08x), 1,440 times a day" % flags)
    check("Windows.UI.Notifications" in decoded and "ToastText02" in decoded,
          "…built from the WinRT types themselves: no module, no cmdlet")
    check("silent" in decoded and "'true'" in decoded, "…and silent: no sound")
    check("{" not in decoded.replace("{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}", ""),
          "…with no brace block anywhere (hub memory powershell-51-stdin-drops-brace-blocks)")
    check("$env:EXO_NOTE_TITLE" in decoded and "$env:EXO_NOTE_BODY" in decoded,
          "…and it reads the texts from the environment and from nowhere else")

    argv, env_add, flags, how = pmod.notify_command("Exocortex", "Alpha", NASTY, kind="darwin")
    check(how == "osascript" and argv[0] == "osascript", "the macOS road is osascript")
    check(argv[2::2][:3] == list(pmod.MAC_NOTIFY_SCRIPT),
          "…running the FIXED `on run argv` script: %s" % argv[2::2][:1])
    check(argv[-3:] == ["Exocortex", "Alpha", NASTY],
          "…with the texts as ARGV and nowhere else")
    check(env_add == {} and flags == 0, "…no environment, no window flags")
    argv, _e, _f, how = pmod.notify_command("Exocortex", "Alpha", NASTY, kind="other")
    check(argv == [] and how == "none",
          "an operating system with no notifier the postman knows says `none`, never a guess")

    start("PB24b", "the South's `pythonw` cannot print: a rendered command names a console python")
    # The South's scheduled pass runs under `pythonw`, and THE PASS is what
    # reconciles the holds cache — so the cached --wait command would have been
    # "…\pythonw.exe" "…\mail.py" --wait …, and pythonw has no stdout: the
    # waiter's printed letter IS the delivery, and it would have printed nothing.
    def rendered(world_, exe):
        code, out = run([PY, str(world_["base"] / "pyrender.py"),
                         str(world_["hub"] / "tools" / "postman.py"), str(exe),
                         str(world_["hub"]), str(world_["post"]), HOLDER],
                        cwd=str(world_["hub"]), env=world_["env"])
        try:
            return json.loads([l for l in out.splitlines() if l.strip().startswith("{")][-1])
        except Exception:
            return {"raw": out}

    pyw = w["base"] / "pyhome"
    pyw.mkdir(parents=True, exist_ok=True)
    write(pyw / "pythonw.exe", "")
    write(pyw / "python.exe", "")
    got = rendered(w, pyw / "pythonw.exe")
    check(got.get("py") == str(pyw / "python.exe"),
          "under pythonw the console python beside it is used: %r" % got.get("py"))
    check(str(got.get("wait") or "").startswith('"%s"' % (pyw / "python.exe")),
          "…so the arm line's --wait command names it: %s" % str(got.get("wait"))[:70])
    check(str(got.get("hook") or "").startswith('"%s"' % (pyw / "python.exe")),
          "…and so does the hook command --install-hooks renders: %s" % str(got.get("hook"))[:70])
    check("pythonw" not in str(got.get("wait")) and "pythonw" not in str(got.get("hook")),
          "…and NEITHER names pythonw, which has no stdout at all")
    bare = w["base"] / "pyonly"
    bare.mkdir(parents=True, exist_ok=True)
    write(bare / "PythonW.exe", "")
    got = rendered(w, bare / "PythonW.exe")
    check(got.get("py") == "python",
          "with no console python beside it, the bare word — and the stem is matched in ANY "
          "case: %r" % got.get("py"))
    got = rendered(w, PY)
    check(got.get("py") == PY,
          "and any other interpreter is sys.executable, exactly as it was: %r" % got.get("py"))


# --------------------------------------------------------------------------
# PB25 — tree_facts: a pure read, and {} when there is no post file
# --------------------------------------------------------------------------

def case_pb25():
    start("PB25", "tree_facts: a pure read the tree can lean on, and {} when there is nothing")
    w = bworld("pb25")
    pmod = load_postman(w)
    empty = pworld("pb25-empty", prime=False)
    check(load_postman(empty).tree_facts(empty["hub"]) == {},
          "with no post file anywhere it is {} — and the page is the page it was")
    check(pmod.tree_facts("/no/such/hub/at/all") == {}, "a hub that is not there is {} too")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    one = letter(w, "NORTH/hub", "a letter for the tree to count")
    letter(w, "OWNER", OWNER_NOTE, "no action")
    pmn(w, "--pass", "--no-pull")
    before = fingerprint(w["post"])
    facts = pmod.tree_facts(w["hub"], [("H", "Exocortex/hub", True), ("G", "Alpha/One", False)])
    check(fingerprint(w["post"]) == before, "IT WRITES NOTHING: POST DIR is byte-identical after it")
    check(facts["machines"]["north"]["state"] in ("passing", "quiet", "none"),
          "each machine's postman has a state: %s" % facts["machines"]["north"])
    check(facts["machines"]["north"]["waiting"] >= 1, "…and the letters waiting there")
    check([r for r in facts["lanes"]["H"] if r["token"] == tok(w, one)],
          "the hub's letters answer to the hub row")
    check(not facts["lanes"]["G"], "…and to no other lane")
    check(not [r for r in facts["lanes"]["H"] if r["to"] == "OWNER"],
          "a note for OWNER is never counted as a lane's letter")
    check(len(facts["owner"]) == 1, "…it is a note for Wren: %d" % len(facts["owner"]))
    check(facts["owner"][0]["line"].endswith("no action"),
          "…carrying its own line verbatim: %s" % facts["owner"][0]["line"][-30:])
    g = pworld("pb25-suffix")
    plant_claim(g, "Alpha/One", "north", "ACT — Alpha/One: the lane", session=SID_B)
    gone = letter(g, "NORTH/Alpha-One", "one lane, either spelling")
    pm(g, "--pass", "--no-pull")
    facts = load_postman(g).tree_facts(g["hub"], [("H", "Exocortex/hub", True),
                                                  ("G", "Alpha/One", False)])
    check([r for r in facts["lanes"]["G"] if r["token"] == tok(g, gone)],
          "an address answers to a lane by phase A's own suffix rule, and by no second matcher")
    check(not facts["lanes"]["H"], "…and the hub row does not take it")

    start("PB25b", "tree_facts reads THIS HUB'S heartbeat, never the real machine's (F1)")
    # _tree_facts used to ask post_dir() with NO hub, so a rehearsal
    # hub's tree drew the REAL postman's heartbeat as its own. Read through the
    # driver, whose HOME is the world's, so the answer comes from the world's
    # machine.json and not from the machine this gate runs on.
    def facts_of(world_, hub):
        code, out = run([PY, str(world_["base"] / "treefacts.py"),
                         str(world_["hub"] / "tools" / "postman.py"), str(hub)],
                        cwd=str(world_["hub"]), env=world_["env"])
        try:
            return json.loads([l for l in out.splitlines() if l.strip().startswith("{")][-1])
        except Exception:
            return {"raw": out}

    h = bworld("pb25b")
    letter(h, "NORTH/hub", "a letter so the hub has a post file at all")
    pmn(h, "--pass", "--no-pull")
    check(((facts_of(h, h["hub"]).get("machines") or {}).get("north") or {}).get("state")
          == "passing",
          "on the machine's OWN hub the postman's own beat is read: passing")
    rehearsal = h["base"] / "rehearsal"
    rehearsal.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(h["hub"] / "post-north.json"), str(rehearsal / "post-north.json"))
    state = ((facts_of(h, rehearsal).get("machines") or {}).get("north") or {}).get("state")
    check(state == "none",
          "A REHEARSAL HUB READS ITS OWN post folder, which has never passed: %r" % state)
    check(not (h["hub"] / ".post").exists(),
          "…and a pure read made no .post/ anywhere")


# ==========================================================================
# BQ68 — a short address that fits two lanes across projects is ambiguous
# ==========================================================================

def plant_opener(w, project, lane, name="OPENER.md"):
    """A project folder ONE LEVEL under the world's projects root, carrying an
    opener whose header names its lane — the opener file's own shape, header
    lines above a `---` and the prompt below it."""
    path = w["projects"] / project / name
    write(path, "lane: %s\nwritten: %s\non: NORTH\nnext: owner\n"
                "depends_on: nothing\n---\nread the project status/memory first.\n"
                "lane: NOT-A-HEADER/Below\n"
          % (lane, iso(datetime.datetime.now().astimezone())))
    return path


def plant_stamp(w, mind, titles):
    """A live-<machine>-<mind>.json stamp, as i-am.py writes one."""
    when = iso(datetime.datetime.now().astimezone())
    write_json(w["hub"] / ("live-%s-%s.json" % (w["machine"], mind.lower())),
               {"machine": w["machine"], "mind": mind.upper(), "when": when,
                "sessions": [{"title": t, "when": when} for t in titles]})


AMBIGUOUS_WHY = ("NORTH/Release fits Exocortex/Release and Gamma/Release — send it again "
                 "as NORTH/Exocortex-Release or NORTH/Gamma-Release")


def case_bq68():
    start("BQ68", "a short address that fits two lanes is NOBODY'S (BQ-068, the 11:19 replayed)")
    # The failure: two letters addressed NORTH/Release for Hub/Release
    # were delivered to the session holding Gamma/Release — the only `…/Release`
    # claim at the time — and that session had to mail back that they were not its.
    w = pworld("bq68")
    plant_claim(w, "Gamma/Release", "north", "ACT — Gamma/Release: the claimed one",
                session=SID_A)
    claude_transcript(w, SID_A)
    claude_transcript(w, SID_B)                       # the sender
    plant_opener(w, "Exocortex-hub", "Exocortex/Release", name="OPENER-Release.md")
    lanes = load_postman(w).fleet_lanes(w["hub"], home=w["home"], cache=False)
    check(sorted(lanes) == ["exocortex/release", "gamma/release"],
          "the fleet's lane tokens are read from the claim AND the opener: %s"
          % ", ".join(sorted(lanes.values())))
    mp(w, "--send", "NORTH/Release", "Exocortex", "the P4 brief is ready", "answer it",
       "--no-push", env=as_session(SID_B))
    pm(w, "--pass", "--no-pull")
    line = [l for l in io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read().splitlines()
            if "the P4 brief" in l][0]
    e = post_of(w)["letters"][tok(w, line)]
    kind = (state_of(w)["letters"][tok(w, line)] or {}).get("state_kind")
    check(kind == "ambiguous" and e["state"] == "waiting",
          "the letter is AMBIGUOUS, not delivered: %s" % kind)
    check(e.get("holder") is None, "…held by nobody, though one of the two holds a claim")
    check(not pending_of(w, SID_A),
          "…and NOTHING is queued for the session that happens to hold a claim")
    check(e["why"] == AMBIGUOUS_WHY, "the why names both lanes and both addresses: %s" % e["why"])
    notices = [i["text"] for i in pending_of(w, SID_B) if i["kind"] == "notice"]
    check(any(AMBIGUOUS_WHY in n for n in notices),
          "THE SENDER IS TOLD AT ONCE, at the first pass and not at five minutes: %s"
          % (notices[:1] or "(none)"))
    check(any(n.startswith("POST — your letter to NORTH/Release of ") for n in notices),
          "…in the sender's own spelling of the address it wrote")

    start("BQ68b", "the same letter, addressed as the why says, is delivered")
    mp(w, "--send", "NORTH/Gamma-Release", "Exocortex", "the P4 brief, addressed in full",
       "answer it", "--no-push", env=as_session(SID_B))
    pm(w, "--pass", "--no-pull")
    full = [l for l in io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read().splitlines()
            if "addressed in full" in l][0]
    check([i["token"] for i in pending_of(w, SID_A) if i["kind"] == "letter"] == [tok(w, full)],
          "one of the two addresses the why offers delivers to the lane it names, and to no other")
    check((state_of(w)["letters"][tok(w, line)] or {}).get("state_kind") == "ambiguous"
          and post_of(w)["letters"][tok(w, line)]["why"] == AMBIGUOUS_WHY,
          "…while the short one is still ambiguous, and still nobody's")

    start("BQ68c", "a short token that fits exactly ONE fleet lane delivers, as it always did")
    x = pworld("bq68c")
    plant_claim(x, "Exocortex/Builds", "north", "ACT — Exocortex/Builds: b", session=SID_A)
    claude_transcript(x, SID_A)
    plant_opener(x, "Gamma", "Gamma/Release")      # another lane, another token
    lb = letter(x, "NORTH/Builds", "a letter by the lane's short name")
    pm(x, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(x, SID_A)] == [tok(x, lb)],
          "NORTH/Builds still reaches Exocortex/Builds by the unique `/`-suffix")

    start("BQ68d", "no openers and no stamps: routing is exactly what it was")
    y = pworld("bq68d")
    plant_claim(y, "Gamma/Release", "north", "ACT — Gamma/Release: the only record",
                session=SID_A)
    claude_transcript(y, SID_A)
    check(sorted(load_postman(y).fleet_lanes(y["hub"], home=y["home"], cache=False))
          == ["gamma/release"],
          "a fleet whose whole record is one claim carries one lane token")
    lr = letter(y, "NORTH/Release", "the day before the openers existed")
    pm(y, "--pass", "--no-pull")
    check([i["token"] for i in pending_of(y, SID_A)] == [tok(y, lr)],
          "…so the short address still delivers — nothing about yesterday changes")
    z = pworld("bq68e")
    mail = load_mail(z)
    pmod = load_postman(z)
    answer = pmod.route("- 2026-09-22 · to: NORTH/Release · Exocortex · x · answer it",
                        mail, [], [], set(["north", "south"]))
    check(answer["state"] == "nobody",
          "and route() called WITHOUT the fleet's lanes at all routes as it did before: %s"
          % answer["state"])

    start("BQ68e", "the lane tokens are read from all three records, and `hub` is untouched")
    v = pworld("bq68f")
    plant_claim(v, "Alpha/One", "north", "ACT — Alpha/One: g", session=SID_A)
    plant_opener(v, "Gamma", "Gamma/Release", name="OPENER-Release.md")
    plant_stamp(v, "NOBODY", ["ACT — BETA/Look: spatial study", "ACT — Exocortex: no lane here"])
    pmod = load_postman(v)
    lanes = pmod.fleet_lanes(v["hub"], home=v["home"], cache=False)
    check(sorted(lanes) == ["alpha/one", "beta/look", "gamma/release"],
          "claims, openers and stamps, and a title with no lane in it contributes nothing: %s"
          % ", ".join(sorted(lanes)))
    check(lanes.get("beta/look") == "BETA/Look",
          "…each in the record's OWN spelling, which is what the why quotes back")
    plant_opener(v, "Second", "Exocortex/One")
    lanes = pmod.fleet_lanes(v["hub"], home=v["home"], cache=False)
    hub_line = "- 2026-09-22 · to: NORTH/hub · Exocortex · a hub letter · answer it"
    plant_claim(v, "hub", "north", HOLDER, session=SID_B)
    answer = pmod.route(hub_line, load_mail(v), pmod.read_claims(v["hub"]),
                        pmod.read_ears(v["hub"]), set(["north", "south"]), lanes=lanes)
    check(answer["state"] == "held" and (answer["holder"] or {}).get("title") == HOLDER,
          "`hub` is per machine and this rule never touches it: %s" % answer["state"])
    short = "- 2026-09-22 · to: NORTH/One · Alpha · which One? · answer it"
    answer = pmod.route(short, load_mail(v), pmod.read_claims(v["hub"]),
                        pmod.read_ears(v["hub"]), set(["north", "south"]), lanes=lanes)
    check(answer["state"] == "ambiguous" and "Alpha/One" in answer["why"]
          and "Exocortex/One" in answer["why"],
          "a lane known only from an opener still makes a short address ambiguous: %s"
          % answer["why"])
    full = "- 2026-09-22 · to: NORTH/Alpha-One · Alpha · the full token · answer it"
    answer = pmod.route(full, load_mail(v), pmod.read_claims(v["hub"]),
                        pmod.read_ears(v["hub"]), set(["north", "south"]), lanes=lanes)
    check(answer["state"] == "held", "…and the full token is not short, so it routes as ever")
    check(pmod.fleet_lanes("/no/such/hub", home="/no/such/home", cache=False) == {}
          and pmod.opener_lane("/no/such/file") == "" and pmod.title_lane(None) == "",
          "a hub, a home and a file that are not there contribute nothing and raise nothing")

    start("BQ68f", "--status and the tree's ✉ say the same why, through state_kind")
    code, out = mp(w, "--status")
    row = next((l for l in out.splitlines() if l.startswith("waiting · NORTH/Release")), "")
    check(AMBIGUOUS_WHY in row, "--status carries the ambiguous why, not a second sentence: %s"
          % (row or "(no row)"))
    sent = next((l for l in out.splitlines() if l.startswith("you sent · NORTH/Release")), "")
    check(AMBIGUOUS_WHY in sent, "…and so does the sender's own side of it: %s"
          % (sent or "(no row)"))
    pmod = load_postman(w)
    before = fingerprint(w["post"])
    facts = pmod.tree_facts(w["hub"], [("E", "Exocortex/Release", False),
                                       ("R", "Gamma/Release", False)])
    rows = [r for r in facts["lanes"]["E"] if r["token"] == tok(w, line)]
    check(rows and rows[0]["why"] == AMBIGUOUS_WHY,
          "the tree's ✉ answers the click with the same words")
    check([r for r in facts["lanes"]["R"] if r["token"] == tok(w, line)],
          "…on BOTH lanes the address could have meant, because it is either one's to fix")
    check(fingerprint(w["post"]) == before, "and reading the tree wrote nothing")


# --------------------------------------------------------------------------
# LIVE — nothing of this machine's own was written
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# QW — NOTHING WAITS ON FABLE, AN FYI LETTER NEVER WAKES A WINDOW
#      (G1–G11)
# --------------------------------------------------------------------------
# Every world is the gate's own, under the system temp folder; the windows are
# fixture transcripts in the app's real shape (an assistant record carrying
# `message.model` and `message.usage`, the title in `<sid>/custom-title.json`).
# No real --send: letters are appended to the WORLD's INBOX, or sent by the
# world's own mail.py with --no-push into the world's own hub.

# THIS RUN'S OWN MARK : every QW fixture string
# carries this run's pid and start second, so the LIVE rail can never mistake a real letter's
# own words (a document named "…-RELEASE-GATE") for this gate's work.
GATE_QW = "GATE-QW-%d-%d" % (os.getpid(), int(time.time()))
QW_DESK = "ACT — Exocortex/Desk: %s the desk" % GATE_QW
QW_HUB = "ACT — Exocortex/hub: %s the fable hub" % GATE_QW
QW_SID_D = "dddddddd-1111-2222-3333-dddddddddddd"
QW_SID_F = "ffffffff-1111-2222-3333-ffffffffffff"
QW_FABLE = "claude-fable-5-1"
QW_SONNET = "claude-sonnet-5"
QW_REFUSE_TAIL = "retire instead: write your carryover and retitle ARCH — or hand your waiting to the Desk (NORTH/Exocortex-Desk)"


def qw_window(w, sid, model, context=12000, title=None, project="-gate-hub"):
    """A window in the app's real shape: one prompt, one assistant reply carrying
    the model it ran on and the context it carried in, and — when titled — the
    app's own `<sid>/custom-title.json` beside the transcript."""
    folder = w["home"] / ".claude" / "projects" / project
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("%s.jsonl" % sid)
    third = int(context) // 3
    rows = [{"parentUuid": None, "isSidechain": False, "type": "user",
             "message": {"role": "user", "content": "go"}, "uuid": "u-1",
             "timestamp": "2026-09-24T15:00:00.000Z", "sessionId": sid},
            {"parentUuid": "u-1", "isSidechain": False, "type": "assistant",
             "message": {"role": "assistant", "model": model,
                         "content": [{"type": "text", "text": "done"}],
                         "usage": {"input_tokens": int(context) - 2 * third,
                                   "cache_read_input_tokens": third,
                                   "cache_creation_input_tokens": third,
                                   "output_tokens": 10}},
             "effort": "high", "uuid": "a-1", "timestamp": "2026-09-24T15:00:05.000Z",
             "sessionId": sid}]
    write(path, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    if title:
        write_json(folder / sid / "custom-title.json", {"customTitle": title})
    return path


def qw_heartbeat(w):
    write_json(w["post"] / "heartbeat.json",
               {"when": iso(datetime.datetime.now().astimezone()), "every": 60, "version": 1})


def qw_waits(w):
    path = w["post"] / "waits.jsonl"
    if not path.is_file():
        return []
    return [json.loads(l) for l in io.open(str(path), encoding="utf-8").read().splitlines()
            if l.strip()]


def qw_wait_once(w, sid, title, extra=(), timeout=25):
    """A waiter that must NOT arm: (exit code, output, seconds it took)."""
    began = time.time()
    proc = waiter(w, "NORTH/hub", title, extra=extra, env=as_session(sid))
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate(timeout=10)
        return None, out, time.time() - began
    return proc.returncode, out, time.time() - began


def qw_armed(w, sid, title, extra=(), settle=4.0):
    """A waiter that MUST arm: (still running after `settle` s?, what it printed)."""
    proc = waiter(w, "NORTH/hub", title, extra=extra, env=as_session(sid))
    time.sleep(settle)
    alive = proc.poll() is None
    if proc.poll() is None:
        proc.kill()
    out, _ = proc.communicate(timeout=10)
    return alive, out


def case_qw1():
    start("QW-G1", "rails: the worlds are the gate's own, under the system temp folder")
    tmp = Path(tempfile.gettempdir()).resolve()
    root = ROOT.resolve()
    check(str(root).startswith(str(tmp)), "the scratch root sits under the system temp folder: %s" % root)
    hub = real_hub().resolve()
    check(not str(root).startswith(str(hub)) and not str(hub).startswith(str(root)),
          "…and not under (nor over) the live hub folder")
    check(not str(root).startswith(str(BRAIN.resolve())), "…and not under the brain")
    check(os.environ.get("EXO_GATE_COMMS_DEPTH") == "1",
          "every child this gate starts carries its depth mark (a gate-comms child refuses to run)")
    w = pworld("qw1")
    check(str(w["base"].resolve()).startswith(str(root)), "a QW world is made inside that root")
    check(w["env"].get("EXO_MACHINE_JSON", "").startswith(str(w["home"])),
          "…and its tools read the world's own machine record, never this machine's")


def case_qw2():
    start("QW-G2", "R1: nothing waits on Fable — the model is READ from the window's own transcript")
    w = pworld("qw2")
    qw_heartbeat(w)
    qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    code, out, took = qw_wait_once(w, QW_SID_F, QW_HUB)
    lines = [l for l in out.splitlines() if l.strip()]
    check(code == 0, "a Fable window's --wait exits 0 (exit %s)" % code)
    check(len(lines) == 1 and QW_REFUSE_TAIL in lines[0] and QW_FABLE in lines[0],
          "…in ONE line that names the model it read and the road: %s" % lines[:2])
    check(took < 20, "…and no loop: it was over in %.1f s" % took)
    rows = qw_waits(w)
    check(len(rows) == 1 and rows[0].get("verdict") == "refused" and rows[0].get("title") == QW_HUB
          and rows[0].get("model") == QW_FABLE and rows[0].get("when"),
          "one logged line with the title, the model and the time: %s"
          % [dict((k, r.get(k)) for k in ("verdict", "title", "model")) for r in rows])
    s = pworld("qw2s")
    qw_heartbeat(s)
    qw_window(s, QW_SID_D, QW_SONNET, title=QW_DESK)
    alive, out = qw_armed(s, QW_SID_D, QW_DESK)
    check(alive and "waiting for NORTH/hub" in out,
          "a Sonnet window arms, and says so: %s" % out.strip().splitlines()[:2])
    check("usage-settings.json not found — defaults" in out,
          "…and says once that usage-settings.json is missing, so the defaults rule")
    check(not qw_waits(s), "an armed wait writes no refusal line")
    b = pworld("qw2b")
    qw_heartbeat(b)
    qw_window(b, QW_SID_D, QW_SONNET, title="ACT — Exocortex/Desk: the title before a retitle")
    alive, out = qw_armed(b, QW_SID_D, QW_DESK)
    check(alive and "waiting for NORTH/hub" in out,
          "THE TITLE FALLBACK: no transcript carries the title yet (a Desk that just retitled "
          "itself), so the session's OWN transcript is read — Sonnet — and it arms")
    f = pworld("qw2f")
    qw_heartbeat(f)
    qw_window(f, QW_SID_F, QW_FABLE, title="ACT — Exocortex/hub: an older title")
    code, out, took = qw_wait_once(f, QW_SID_F, QW_HUB)
    check(code == 0 and QW_FABLE in out and QW_REFUSE_TAIL in out,
          "…and the fallback still refuses a Fable window by what its own transcript says")
    g = pworld("qw2g")
    qw_heartbeat(g)
    code, out, took = qw_wait_once(g, QW_SID_D, QW_DESK)
    check(code == 0 and "no transcript on this machine carries the title" in out
          and QW_REFUSE_TAIL in out and took < 20,
          "neither road finds a transcript: refused, never armed blind — %s" % out.strip()[:160])
    n = pworld("qw2n")
    qw_heartbeat(n)
    code, out, took = qw_wait_once(n, "", None, extra=())
    check(code == 0 and "never arm blind" in out,
          "no title and no session in the environment: refused, never armed blind — %s"
          % out.strip()[:140])
    h = pworld("qw2h")
    qw_heartbeat(h)
    qw_window(h, QW_SID_D, QW_SONNET, title=QW_DESK)
    code, out, took = qw_wait_once(h, QW_SID_D, QW_DESK, extra=["--model", "fable"])
    check(code == 0 and "--model says fable" in out and QW_SONNET in out,
          "--model is a hint that must AGREE with the transcript: %s" % out.strip()[:140])
    alive, out = qw_armed(h, QW_SID_D, QW_DESK, extra=["--model", "sonnet"])
    check(alive, "…and a hint that agrees arms")


def case_qw3():
    start("QW-G3", "R2: a context ceiling for every model — the window's own last reply, 40% by default")
    w = pworld("qw3")
    qw_heartbeat(w)
    qw_window(w, QW_SID_D, QW_SONNET, context=450000, title=QW_DESK)
    code, out, took = qw_wait_once(w, QW_SID_D, QW_DESK)
    check(code == 0 and "45%" in out and "40% ceiling" in out and QW_REFUSE_TAIL in out,
          "a Sonnet window at 45%% is refused, naming the percent: %s" % out.strip()[:170])
    rows = qw_waits(w)
    check(len(rows) == 1 and abs(float(rows[0].get("percent") or 0) - 45.0) < 0.01,
          "…logged with its percent")
    l = pworld("qw3l")
    qw_heartbeat(l)
    qw_window(l, QW_SID_D, QW_SONNET, context=300000, title=QW_DESK)
    alive, out = qw_armed(l, QW_SID_D, QW_DESK)
    check(alive, "…and the same window at 30% arms")


def case_qw4():
    start("QW-G4", "--force arms a Fable window, and the override is logged")
    w = pworld("qw4")
    qw_heartbeat(w)
    qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    alive, out = qw_armed(w, QW_SID_F, QW_HUB, extra=["--force"])
    check(alive and "FORCED" in out, "--force arms it, and says so: %s" % out.strip().splitlines()[:1])
    rows = qw_waits(w)
    check(len(rows) == 1 and rows[0].get("verdict") == "forced" and rows[0].get("title") == QW_HUB
          and rows[0].get("model") == QW_FABLE and rows[0].get("when"),
          "one logged line: forced, the title, the model, the time")


def case_qw5():
    start("QW-G5", "R3: an FYI letter never ends a wait; an asking letter does, and is named")
    w = pworld("qw5")
    qw_heartbeat(w)
    plant_claim(w, "hub", "north", QW_DESK, mind="SONNET", session=QW_SID_D)
    qw_window(w, QW_SID_D, QW_SONNET, title=QW_DESK)
    proc = waiter(w, "NORTH/hub", QW_DESK, env=as_session(QW_SID_D))
    try:
        armed(w, "NORTH/hub")
        quiet = [letter(w, "NORTH/hub", GATE_QW + " the pulse beat", "FYI"),
                 letter(w, "NORTH/hub", GATE_QW + " the ceiling block", "read"),
                 letter(w, "NORTH/hub", GATE_QW + " for the record", "none — nothing owed")]
        pm(w, "--pass", "--no-pull")
        time.sleep(6)
        check(proc.poll() is None, "three quiet letters (FYI · read · none — …) do not end the wait")
        items = pending_of(w, QW_SID_D)
        qt = set(tok(w, l) for l in quiet)
        check(set(i.get("token") for i in items) == qt and all(i.get("quiet") for i in items),
              "…they wait in the window's pending file, each marked quiet")
        st = json.loads(io.open(str(w["post"] / "state.json"), encoding="utf-8").read())
        check(all((st.get("letters") or {}).get(t, {}).get("quiet") and
                  (st.get("letters") or {}).get(t, {}).get("queued") for t in qt),
              "…and marked queued (and quiet) in the postman's own state")
        ask = letter(w, "NORTH/hub", GATE_QW + " archive queue: 2 · a, b", "archive the queue")
        pm(w, "--pass", "--no-pull")
        try:
            out, _ = proc.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(proc.returncode == 0, "one asking letter (`archive the queue`) ends it")
        first = next((l for l in out.splitlines() if "the wait ended on" in l), "")
        check("1 asking letter" in first and "archive the queue" in first and tok(w, ask) in first,
              "…and the waiter's line names it: %s" % first[:160])
        check(not [t for t in qt if t in out], "…and the quiet three do NOT ride that wake")
        left = set(i.get("token") for i in pending_of(w, SID_A if False else QW_SID_D))
        check(left == qt, "…they stay queued for the window's next turn start")
        code, hout, _err = hook(w, QW_SID_D, "UserPromptSubmit")
        ctx = context_of(hout)
        check(all(ctx.count(t) == 1 for t in qt), "the next turn start prints the quiet three, once each")
        code, hout, _err = hook(w, QW_SID_D, "UserPromptSubmit")
        check(not context_of(hout), "…and the turn after prints them no more")
        # NOTICES NEVER WAKE (the hub's ruling on Part A): a five-minute `not read yet`
        # joins the quiet ones; a letter that asks still ends the wait.
        drop_ear(w, "NORTH/hub")                      # the first waiter's ear is not this one's mark
        proc = waiter(w, "NORTH/hub", QW_DESK, env=as_session(QW_SID_D))
        armed(w, "NORTH/hub")
        write_json(w["post"] / "pending" / ("%s.json" % QW_SID_D),
                   {"session": QW_SID_D, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": [{"token": "pm-0000000000aa", "kind": "notice", "fyi": False,
                               "to": "NORTH/Proj", "queued": iso(datetime.datetime.now().astimezone()),
                               "text": "POST — your letter to NORTH/Proj of 09:00 is not read yet (5 min): idle."}]})
        time.sleep(6)
        check(proc.poll() is None, "a five-minute `not read yet` notice does not end a wait")
        ask2 = letter(w, "NORTH/hub", GATE_QW + " another ask", "reply when done")
        pm(w, "--pass", "--no-pull")
        out2, _ = proc.communicate(timeout=25)
        check(tok(w, ask2) in out2 and "pm-0000000000aa" not in out2,
              "…the next ask ends it, and the notice stays queued for the next turn start")
        check("pm-0000000000aa" in [i.get("token") for i in pending_of(w, QW_SID_D)],
              "…still in the pending file")
    finally:
        if proc.poll() is None:
            proc.kill()
    m = load_mail(w)
    rows = [("FYI", True), ("fyi — later", True), ("read", True), ("none", True),
            ("None — just so you know", True), ("no reply needed — FYI", True),
            ("no reply", True), ("", True), ("archive the queue", False), ("answer it", False),
            ("reply when done", False)]
    bad = [a for a, want in rows
           if m.is_quiet("- 2026-09-24 · to: NORTH/hub · E · text · %s" % a) is not want]
    check(not bad, "the quiet test, action by action (case-blind): %s" % (bad or "all as ruled"))


# --------------------------------------------------------------------------
# QW-W — THE FLOOR ROAD OBEYS THE SAME RULE
# --------------------------------------------------------------------------
# `mail.py --watch` loops forever and prints a line per letter, and every line it
# prints wakes the window for a full turn: the older door to the overnight burn.
# These worlds are QW's own (pworld, under the system temp folder, one name per
# check); every watch runs as a child with a timeout, or is ended by this gate.

def qw_watch_args(w, title, every=2, extra=()):
    args = [PY, str(w["hub"] / "tools" / "mail.py"), "--watch", "NORTH/hub",
            "--every", str(every), "--hub", str(w["hub"]), "--no-pull"]
    if title:
        args += ["--title", title]
    return args + list(extra)


def qw_watch_env(w, sid):
    """The world's environment over this process's own, with the window's id —
    the same shape waiter() gives a --wait (a key the world clears is dropped)."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    for k, v in dict(w["env"], **(as_session(sid) if sid else {})).items():
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    return env


def qw_watch_refused(w, sid, title, extra=(), timeout=25):
    """A watch that must NOT arm: (exit code, output, seconds). subprocess.run
    kills the child itself if it outlives the timeout."""
    began = time.time()
    code, out = run(qw_watch_args(w, title, extra=extra), cwd=w["hub"],
                    env=dict(w["env"], **(as_session(sid) if sid else {})), timeout=timeout)
    return code, out, time.time() - began


def qw_watch_start(w, sid, title, name, extra=(), every=2):
    """A watch that SHOULD arm, its output going to a file in the world (a file,
    not a pipe, so it is read while the child runs, on every OS)."""
    log = w["base"] / ("%s.log" % name)
    handle = io.open(str(log), "w", encoding="utf-8")
    proc = subprocess.Popen(qw_watch_args(w, title, every=every, extra=extra),
                            cwd=str(w["hub"]), env=qw_watch_env(w, sid),
                            stdout=handle, stderr=subprocess.STDOUT)
    return proc, handle, log


def qw_watch_stop(proc, handle):
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        try:
            handle.close()
        except Exception:
            pass


def qw_until(cond, seconds, step=0.2):
    """Poll `cond` until it is true or `seconds` pass; its last answer."""
    deadline = time.time() + seconds
    while True:
        got = cond()
        if got or time.time() >= deadline:
            return got
        time.sleep(step)


def qw_log(log):
    try:
        return io.open(str(log), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def qw_ear(w):
    path = w["hub"] / "ear-north-hub.json"
    try:
        return json.loads(io.open(str(path), encoding="utf-8").read())
    except (OSError, ValueError):
        return None


def case_qww1():
    start("QW-W1", "BQ-170: a Fable window's --watch is refused — one line, exit 0, logged, no ear")
    w = pworld("qww1")
    qw_heartbeat(w)
    qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    code, out, took = qw_watch_refused(w, QW_SID_F, QW_HUB)
    lines = [l for l in out.splitlines() if l.strip()]
    check(code == 0, "a Fable window's --watch exits 0 (exit %s)" % code)
    check(len(lines) == 1 and "refused" in lines[0] and QW_FABLE in lines[0]
          and QW_REFUSE_TAIL in lines[0],
          "…in ONE line — --wait's own words, naming the model it read: %s" % lines[:2])
    check(took < 20, "…and no loop: it was over in %.1f s" % took)
    rows = qw_waits(w)
    check(len(rows) == 1 and rows[0].get("verdict") == "refused" and rows[0].get("title") == QW_HUB
          and rows[0].get("model") == QW_FABLE and rows[0].get("to") == "NORTH/hub"
          and rows[0].get("when"),
          "one waits.jsonl line: refused, the title, the model, the address, the time: %s"
          % [dict((k, r.get(k)) for k in ("verdict", "title", "model", "to")) for r in rows])
    check(not list(w["hub"].glob("ear-*.json")),
          "no ear was written — a refused watch holds no mailbox")


def case_qww2():
    start("QW-W2", "BQ-170: a Sonnet window's --watch prints ONE `MAIL for` for an ask; three FYI "
          "lines are counted, never printed")
    w = pworld("qww2")
    qw_heartbeat(w)
    qw_window(w, QW_SID_D, QW_SONNET, title=QW_DESK)
    proc, handle, log = qw_watch_start(w, QW_SID_D, QW_DESK, "qww2-watch")
    try:
        armed = qw_until(lambda: qw_ear(w) is not None, 15)
        check(bool(armed) and proc.poll() is None,
              "a Sonnet window's watch arms and keeps running: %s"
              % qw_log(log).strip().splitlines()[:2])
        check((qw_ear(w) or {}).get("quiet") == 0, "the ear carries `quiet: 0` from the moment it arms")
        quiet = [letter(w, "NORTH/hub", GATE_QW + "-W the pulse beat", "FYI"),
                 letter(w, "NORTH/hub", GATE_QW + "-W the ceiling block", "read"),
                 letter(w, "NORTH/hub", GATE_QW + "-W for the record", "none — nothing owed")]
        counted = qw_until(lambda: (qw_ear(w) or {}).get("quiet") == 3, 15)
        check(bool(counted), "three quiet letters (FYI · read · none — …) are counted into the "
              "ear's `quiet`: %r" % (qw_ear(w) or {}).get("quiet"))
        time.sleep(2.5)                            # one more poll: nothing may print late
        check("MAIL for" not in qw_log(log),
              "…and not one `MAIL for` line was printed for them — nothing woke the window")
        ask = letter(w, "NORTH/hub", GATE_QW + "-W archive queue: 2 · a, b", "archive the queue")
        printed = qw_until(lambda: "MAIL for" in qw_log(log), 15)
        time.sleep(2.5)                            # one more poll, so a second line would show
        text = qw_log(log)
        mails = [l for l in text.splitlines() if l.startswith("MAIL for")]
        check(bool(printed) and len(mails) == 1 and tok(w, ask) in mails[0]
              and "archive the queue" in mails[0],
              "the one asking letter prints exactly ONE `MAIL for` line, its token on it: %s"
              % [m[:120] for m in mails])
        check(not [q for q in quiet if tok(w, q) in text],
              "the three FYI letters are never printed, not even beside the ask")
        check("(+3 FYI letters waiting — read them at your next turn)" in text,
              "…one trailing line says three FYI letters are waiting for the next turn")
        check((qw_ear(w) or {}).get("quiet") == 3, "the ear's `quiet` is still 3: %r"
              % (qw_ear(w) or {}).get("quiet"))
        check(proc.poll() is None, "the watch runs on after the ask (the floor road loops)")
        check(not qw_waits(w), "an armed watch writes no refusal line")
    finally:
        qw_watch_stop(proc, handle)


def case_qww3():
    start("QW-W3", "BQ-170: --watch --force arms a Fable window, and the override is logged")
    w = pworld("qww3")
    qw_heartbeat(w)
    qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    proc, handle, log = qw_watch_start(w, QW_SID_F, QW_HUB, "qww3-watch", extra=["--force"])
    try:
        armed = qw_until(lambda: qw_ear(w) is not None, 15)
        text = qw_log(log)
        check(bool(armed) and proc.poll() is None,
              "--force arms it: the ear is written and the watch keeps running")
        check("FORCED" in text and "watching INBOX.md for to: NORTH/hub" in text,
              "…and it says so: %s" % text.strip().splitlines()[:2])
        rows = qw_waits(w)
        check(len(rows) == 1 and rows[0].get("verdict") == "forced" and rows[0].get("title") == QW_HUB
              and rows[0].get("model") == QW_FABLE and rows[0].get("when"),
              "one waits.jsonl line: forced, the title, the model, the time: %s"
              % [dict((k, r.get(k)) for k in ("verdict", "title", "model")) for r in rows])
    finally:
        qw_watch_stop(proc, handle)


def case_qww4():
    start("QW-W4", "BQ-170: no postman beside mail.py — --watch is refused, never armed blind")
    w = pworld("qww4")
    qw_heartbeat(w)
    qw_window(w, QW_SID_D, QW_SONNET, title=QW_DESK)   # a window that WOULD arm: only the postman is missing
    (w["hub"] / "tools" / "postman.py").unlink()
    check(not (w["hub"] / "tools" / "postman.py").exists(),
          "the world's hub has no postman.py beside mail.py, nor in its tools/")
    code, out, took = qw_watch_refused(w, QW_SID_D, QW_DESK)
    lines = [l for l in out.splitlines() if l.strip()]
    check(code == 0 and took < 20, "--watch exits 0 at once (exit %s, %.1f s)" % (code, took))
    check(len(lines) == 1 and "refused" in lines[0] and "never arm blind" in lines[0]
          and "no postman beside mail.py" in lines[0],
          "…in ONE line with the `never arm blind` reason: %s" % lines[:2])
    check(not list(w["hub"].glob("ear-*.json")), "no ear was written")


def qw_text(path):
    try:
        return io.open(str(path), encoding="utf-8").read()
    except OSError:
        return None


def qw_duty(text, head):
    """The paragraph of a routine text that starts with `head`."""
    if text is None:
        return ""
    for block in re.split(r"\n\s*\n|\n(?=\d+[a-z]?\. )|\n(?=\*\*)", text):
        if head in block:
            return block
    return ""


def case_qw6():
    start("QW-G6", "R4: the hygiene queue letter goes to the Desk, with `archive the queue`, and no hub copy")
    hub = HERE.parent
    routine = qw_text(hub / "routines" / "session-hygiene-watcher.md")
    law = qw_text(hub / "watchers" / "session-hygiene-watcher.md")
    skill_path = Path(QW_ARGS.get("skill") or (Path.home() / ".claude" / "scheduled-tasks" /
                                                "session-hygiene-watcher" / "SKILL.md"))
    skill = qw_text(skill_path)
    for name, text, head in (("routines/session-hygiene-watcher.md", routine, "Duty 2c"),
                             ("SKILL.md (%s)" % skill_path, skill, "Duty 2c"),
                             ("watchers/session-hygiene-watcher.md", law, "THE QUEUE")):
        if text is None:
            skip("%s is not there — NOT RUN" % name)
            continue
        duty = qw_duty(text, head).replace("<MACHINE>", "NORTH")
        check("--send NORTH/Exocortex-Desk" in duty and '"archive the queue"' in duty,
              "%s: the queue letter is sent to NORTH/Exocortex-Desk with `archive the queue`" % name)
        sends = re.findall(r"--send (\S+)", duty)
        check(sends == ["NORTH/Exocortex-Desk"],
              "%s: …and that is the ONLY address the duty sends to (no hub copy): %s" % (name, sends))
    if routine is not None and skill is not None:
        # Duty 2c ONLY: the other duties of the same two files change for reasons
        # of their own, and that is not this gate's to judge.
        check(qw_duty(routine, "Duty 2c") == qw_duty(skill, "Duty 2c") != "",
              "the routine template and the installed SKILL.md say the same duty 2c")
    w = pworld("qw6")
    plant_claim(w, "Exocortex/Desk", "north", QW_DESK, mind="SONNET", session=QW_SID_D)
    plant_claim(w, "hub", "north", QW_HUB, mind="FABLE", session=QW_SID_F)
    code, out = mp(w, "--send", "NORTH/Exocortex-Desk", "NORTH/hygiene",
                   "archive queue: 2 · %s a, %s b" % (GATE_QW, GATE_QW), "archive the queue", "--no-push")
    pm(w, "--pass", "--no-pull")
    desk = [i.get("line") for i in pending_of(w, QW_SID_D)]
    hubp = pending_of(w, QW_SID_F)
    check(len(desk) == 1 and "archive the queue" in desk[0],
          "sent the way the routine says, it lands in the Desk's own pending file")
    check(not hubp, "…and nothing is queued for the Fable hub")


def case_qw7():
    start("QW-G7", "R5: the Stop hook on a Fable window prints the Desk line once and never [arm]")
    w = pworld("qw7")
    qw_heartbeat(w)
    plant_claim(w, "hub", "north", QW_HUB, mind="FABLE", session=QW_SID_F)
    path = qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    pm(w, "--pass", "--no-pull")
    hold = json.loads(io.open(str(w["post"] / "holds" / ("%s.json" % QW_SID_F)),
                              encoding="utf-8").read())
    check(hold.get("refuse_models") == ["claude-fable-"] and hold.get("desk") == "NORTH/Exocortex-Desk",
          "the pass copies the rule and the Desk's address into the holds row: %s"
          % dict((k, hold.get(k)) for k in ("refuse_models", "ceiling_percent", "desk")))
    code, out, _err = hook(w, QW_SID_F, "Stop", extra={"transcript_path": str(path)})
    ctx = context_of(out)
    check("this window is %s: nothing waits on Fable" % QW_FABLE in ctx
          and "the Desk (NORTH/Exocortex-Desk) carries your letters" in ctx,
          "a Fable window hears the Desk line: %s" % ctx[:170])
    check("[arm]" not in ctx and "--wait" not in ctx, "…and is never handed the [arm] command")
    code, out, _err = hook(w, QW_SID_F, "Stop", extra={"transcript_path": str(path)})
    check(not context_of(out), "…once per session: the next Stop says nothing")
    s = pworld("qw7s")
    qw_heartbeat(s)
    plant_claim(s, "hub", "north", QW_DESK, mind="SONNET", session=QW_SID_D)
    path = qw_window(s, QW_SID_D, QW_SONNET, title=QW_DESK)
    pm(s, "--pass", "--no-pull")
    code, out, _err = hook(s, QW_SID_D, "Stop", extra={"transcript_path": str(path)})
    ctx = context_of(out)
    check("[arm]" in ctx and '--model "%s"' % QW_SONNET in ctx,
          "a Sonnet window is handed [arm], its command carrying the model the hook READ: %s"
          % ctx[-150:])


def case_qw8():
    start("QW-G8", "the rule is the user's file: usage-settings.json with no refused model arms a Fable window")
    w = pworld("qw8")
    qw_heartbeat(w)
    qw_window(w, QW_SID_F, QW_FABLE, title=QW_HUB)
    write_json(w["hub"] / "usage-settings.json",
               {"wait_refuse_models": [], "wait_context_ceiling_percent": 40})
    alive, out = qw_armed(w, QW_SID_F, QW_HUB)
    check(alive and "waiting for NORTH/hub" in out, "wait_refuse_models: [] — the Fable fixture arms")
    check("not found" not in out, "…and no defaults line, because the file is there")
    c = pworld("qw8c")
    qw_heartbeat(c)
    qw_window(c, QW_SID_D, QW_SONNET, context=300000, title=QW_DESK)
    write_json(c["hub"] / "usage-settings.json", {"wait_context_ceiling_percent": 25})
    code, out, _took = qw_wait_once(c, QW_SID_D, QW_DESK)
    check(code == 0 and "30%" in out and "25% ceiling" in out,
          "the ceiling is the file's too: 25%% refuses a 30%% window — %s" % out.strip()[:120])


def qw_routine_world(name, skills, automations=None, config_model=None, settings=None,
                     templates=None):
    """A fixture machine for routine-check: the app's task store under a scratch
    home, each task's SKILL.md, the Codex automations and config.toml, and a
    fixture hub for usage-settings.json and routines/."""
    base = ROOT / ("%s-%d" % (name, os.getpid()))
    shutil.rmtree(str(base), ignore_errors=True)
    home, hub = base / "home", base / "hub"
    tasks = []
    for tid, front in skills:
        path = home / ".claude" / "scheduled-tasks" / tid / "SKILL.md"
        write(path, "---\nname: %s\ndescription: a gate routine\n%s---\n\nDo the gate's thing.\n"
              % (tid, "".join("%s: %s\n" % kv for kv in front)))
        tasks.append({"id": tid, "displayName": tid, "permissionMode": "bypassPermissions",
                      "cwd": str(hub), "filePath": str(path), "enabled": True})
    store = {"scheduledTasks": tasks, "recordedSkips": {}}
    write_json(home / "Library" / "Application Support" / "Claude" / "claude-code-sessions"
               / "acct" / "org" / "scheduled-tasks.json", store)
    write_json(home / "AppData" / "Roaming" / "Claude" / "claude-code-sessions"
               / "acct" / "org" / "scheduled-tasks.json", store)
    codex = home / ".codex"
    for aid, model in (automations or []):
        write(codex / "automations" / aid / "automation.toml",
              'version = 1\nid = "%s"\nkind = "cron"\nname = "%s"\nprompt = "a gate prompt"\n'
              'status = "ACTIVE"\n%s' % (aid, aid, ('model = "%s"\n' % model) if model else ""))
    if config_model is not None:
        write(codex / "config.toml", 'model = "%s"\nmodel_reasoning_effort = "xhigh"\n' % config_model)
    if settings is not None:
        write_json(hub / "usage-settings.json", settings)
    for tname, front in (templates or []):
        write(hub / "routines" / tname, "<!-- a template -->\n---\nname: %s\n%s---\n\nbody\n"
              % (tname, "".join("%s: %s\n" % kv for kv in front)))
    hub.mkdir(parents=True, exist_ok=True)
    WORLDS.append({"base": base})
    return {"base": base, "home": home, "hub": hub, "codex": codex}


def qw_check_routines(rw, *extra):
    return run([PY, str(source_tool("routine-check.py")), "--home", str(rw["home"]),
                "--hub", str(rw["hub"]), "--codex-home", str(rw["codex"])] + list(extra),
               env={"APPDATA": None})


def case_qw10():
    start("QW-G10", "R7: routines never run on Fable — routine-check.py reads each routine's own model")
    rw = qw_routine_world("qw10", [("gate-fable", [("model", "fable")]),
                                   ("gate-opus", [("model", "opus")]),
                                   ("gate-opus-why", [("model", "opus"),
                                                      ("model-reason", "a verdict across the fleet")]),
                                   ("gate-sonnet", [("model", "sonnet")]),
                                   ("gate-unset", [])])
    code, out = qw_check_routines(rw)
    lines = out.splitlines()

    def verdict(tid):
        for i, l in enumerate(lines):
            if l[3:].strip().startswith(tid + " ") or l.split()[1:2] == [tid]:
                return lines[i + 2].strip() if i + 2 < len(lines) else ""
        return ""
    check(verdict("gate-fable").startswith("STOP") and "never run on Fable" in verdict("gate-fable"),
          "model: fable → STOP: %s" % verdict("gate-fable"))
    check(verdict("gate-opus").startswith("WARN") and "model-reason:" in verdict("gate-opus"),
          "model: opus with no reason → WARN naming the missing line: %s" % verdict("gate-opus"))
    check(verdict("gate-opus-why").startswith("OK") and "a verdict across the fleet" in verdict("gate-opus-why"),
          "model: opus WITH a model-reason line → OK, with the reason: %s" % verdict("gate-opus-why"))
    check(verdict("gate-sonnet").startswith("OK"), "model: sonnet → OK: %s" % verdict("gate-sonnet"))
    check(verdict("gate-unset").startswith("STOP") and "app's default model" in verdict("gate-unset"),
          "no model line → STOP, saying it runs on the app's default: %s" % verdict("gate-unset"))
    check(code == 1 and "STOP" in lines[-1], "a STOP makes the exit 1 and the last line says so: %s"
          % lines[-1:])
    tw = qw_routine_world("qw10t", [], templates=[("a.md", [("model", "sonnet")]),
                                                  ("b.md", [("model", "claude-fable-5-1")])])
    code, out = qw_check_routines(tw, "--templates")
    check(code == 1 and "STOP b.md" in " ".join(out.split()) and "never register a STOP" in out,
          "--templates, the registration road: a Fable template is a STOP before it is ever registered")
    tw2 = qw_routine_world("qw10u", [], templates=[("a.md", [("model", "sonnet")])])
    code, out = qw_check_routines(tw2, "--templates")
    check(code == 0 and "none runs on Fable" in out, "…and an all-Sonnet set passes")


def case_qw11():
    start("QW-G11", "R7, the OpenAI half: an automation with no model line inherits the Astra default")
    rw = qw_routine_world("qw11", [("gate-sonnet", [("model", "sonnet")])],
                          automations=[("gate-bare", None), ("gate-sol", "gpt-5.6-sol"),
                                       ("gate-astra", "gpt-6-astra")],
                          config_model="gpt-6-astra")
    code, out = qw_check_routines(rw)
    row = lambda aid: next((l for l in out.splitlines() if "[codex" in l and (" %s " % aid) in l + " "), "")
    check(row("gate-bare").startswith("STOP") and "inherits the Astra default (gpt-6-astra" in row("gate-bare"),
          "no model line → STOP naming the default config.toml gives it: %s" % row("gate-bare")[:150])
    check(row("gate-sol").startswith("OK"), "model = gpt-5.6-sol → OK: %s" % row("gate-sol")[:90])
    check(row("gate-astra").startswith("STOP"), "model = gpt-6-astra → STOP: %s" % row("gate-astra")[:90])
    check(code == 1, "…and the exit is 1")
    sw = qw_routine_world("qw11s", [("gate-sonnet", [("model", "sonnet")])],
                          automations=[("gate-sol", "gpt-5.6-sol"), ("gate-mini", "gpt-5.6-mini")],
                          config_model="gpt-6-astra",
                          settings={"routine_models": {"openai": "gpt-5.6-mini"}})
    code, out = qw_check_routines(sw)
    row = lambda aid: next((l for l in out.splitlines() if "[codex" in l and (" %s " % aid) in l + " "), "")
    check(row("gate-mini").startswith("OK") and row("gate-sol").startswith("WARN"),
          "the routine model is the settings' own (routine_models.openai): %s | %s"
          % (row("gate-mini")[:60], row("gate-sol")[:80]))
    nw = qw_routine_world("qw11n", [("gate-sonnet", [("model", "sonnet")])],
                          automations=[("gate-bare", None)])
    code, out = qw_check_routines(nw)
    check("no model line — inherits the app's default (none named" in out,
          "with no config.toml, it says the default is not named — never assumed")


def qw_scrub_hits(path, registry=None, words=None):
    """Privacy classes, never matched text. Names come from the tested hub's
    registry and, when present, its private scrub list. Generic path, address
    and cloud-service checks remain active even on an unconfigured install.
    Optional data arguments let neutral fixtures prove the same classes."""
    text = qw_text(path) or ""
    hits = []
    for label, pattern in (("personal-path", r"/Us[e]rs/"),
                           ("personal-address", r"@(?:outl[o]ok|gm[a]il)"),
                           ("personal-cloud", r"icl[o]ud")):
        if re.search(pattern, text, re.I):
            hits.append(label)
    if registry is None:
        try:
            registry = json.loads((HUB / "registry.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            registry = {}
    owner = registry.get("owner") or {}
    names = [owner.get("name"), owner.get("short")] + list(owner.get("aliases") or [])
    if any(isinstance(name, str) and name.strip().casefold() not in
           ("", "owner", "you", "user") and re.search(
               r"(?<![0-9A-Za-z])" + re.escape(name.strip()) + r"(?![0-9A-Za-z])",
               text, re.I) for name in names):
        hits.append("owner-name")
    if words is None:
        try:
            words = (HUB / "release" / "SCRUB-WORDS.txt").read_text(encoding="utf-8").splitlines()
        except OSError:
            words = []
    for entry in words:
        entry = entry.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry.startswith("@name "):
            entry = entry[6:].strip()
        exact = entry.startswith("=")
        word = entry[1:].strip() if exact else entry
        if word and re.search(r"(?<![0-9A-Za-z])" + re.escape(word) +
                              r"(?![0-9A-Za-z])", text, 0 if exact else re.I):
            hits.append("private-word")
            break
    return hits


def case_qw9():
    start("QW-G9", "scrub: the shipped files carry no personal path, name or address")
    for name in ("mail.py", "postman.py", "routine-check.py", "gate-comms.py"):
        hits = qw_scrub_hits(source_tool(name))
        check(not hits, "%s: no personal path, name or address (%s)" % (name, hits or "clean"))
    tmp = Path(tempfile.gettempdir())
    strays = [p.name for p in tmp.iterdir()
              if p.name.startswith(("exocortex-gate-comms", "exo-gate-comms"))
              and p.resolve() != ROOT.resolve()]
    check(not strays, "no world of this gate's lies outside its own root: %s" % (strays or "none"))


QW_ARGS = {}



# --------------------------------------------------------------------------
# FD1 … FD8 — the attended road: push at once, or announce at once
# --------------------------------------------------------------------------

FD_TITLE = "GUI review"
FD_SID_C = "cccccccc-1111-2222-3333-cccccccccccc"


def fd_store(w, sid, local, title, focused_s_ago=3600, activity_s_ago=60, scheduled=False,
             archived=False):
    """One window record in the desktop app's REAL store shape (read first-hand on
    macOS): local_<id>.json under Library/Application Support/Claude/claude-code-sessions/."""
    now_ms = int(time.time() * 1000)
    rec = {"sessionId": local, "cliSessionId": sid, "title": title, "isArchived": archived,
           "lastActivityAt": now_ms - int(activity_s_ago * 1000),
           "lastFocusedAt": now_ms - int(focused_s_ago * 1000), "model": "claude-sonnet-5",
           "cwd": str(w["hub"])}
    if scheduled:
        rec["scheduledTaskId"] = "gate-routine"
    write_json(w["home"] / "Library" / "Application Support" / "Claude" / "claude-code-sessions"
               / "acct" / "org" / ("%s.json" % local), rec)


def fd_world(name, holder_title=FD_TITLE, holder_age_s=180, model=None, base_dir=None):
    """A primed world: the holder SID_A (its claim, its transcript aged `holder_age_s`, its app
    record `local_gatea`), and a sender SID_B — a live Claude window that writes letters."""
    w = bworld(name, live=False, base_dir=base_dir)
    plant_claim(w, "hub", "north", holder_title, session=SID_A,
                mind="FABLE" if model and "fable" in model else "SONNET")
    tpath = (qw_window(w, SID_A, model) if model else claude_transcript(w, SID_A))
    age_file(tpath, holder_age_s)
    bpath = claude_transcript(w, SID_B)
    fd_store(w, SID_A, "local_gatea", holder_title, focused_s_ago=3600)
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=30)
    w["tpath"], w["bpath"] = tpath, bpath
    try:
        os.unlink(str(w["base"] / "notify-calls.jsonl"))
    except OSError:
        pass
    return w


def fd_send(w, text, action="answer it", sender=SID_B):
    code, out = mp(w, "--send", "NORTH/hub", "Exocortex", text, action, "--no-push",
                   env=as_session(sender, "local_gateb"))
    lines = [l for l in inbox_lines(w) if text in l]
    return code, out, (lines[-1] if lines else "")


def fd_orders(w, sid):
    return [i for i in pending_of(w, sid) if i.get("kind") == "send"]


def fd_entry(w, token):
    return (state_of(w).get("letters") or {}).get(token) or {}


def fd_marks(w):
    path = w["hub"] / "mail-marks-north.json"
    return json.loads(io.open(str(path), encoding="utf-8").read()) if path.is_file() else None


def case_fd1():
    start("FD1", "ATTENDED by its transcript: pushed at once by ONE send order the sender's own turn carries")
    w = fd_world("fd1")
    code, out, ask = fd_send(w, "a letter that wants an answer")
    code2, out2, fyi = fd_send(w, "the build is green", "FYI — no reply needed")
    pmn(w, "--pass", "--no-pull")
    orders = fd_orders(w, SID_B)
    check(len(orders) >= 1 and all(o.get("target") == "local_gatea" for o in orders),
          "a send order waits in the SENDER's pending file, aimed at the app's own id for the "
          "window (local_gatea): %s" % [o.get("target") for o in orders])
    everything = " ".join(o.get("message") or "" for o in orders)
    check(tok(w, ask) in everything and tok(w, fyi) not in everything,
          "the order's message carries the ASKING letter with its token, and never the FYI "
          "one — an FYI letter never rides send_message (BQ-307 M-F)")
    check(not fd_orders(w, SID_A), "nothing is ever ordered from the window the letter is for")
    check("road: pushed into «%s» now — it is attended (transcript)" % FD_TITLE in out,
          "the sender hears the road in its own reply: %r"
          % [l for l in out.splitlines() if l.startswith("road:")])
    code, hout, _err = hook(w, SID_B, "PostToolBatch")
    ctx = context_of(hout)
    check("SendMessage" in ctx and '"local_gatea"' in ctx and tok(w, ask) in ctx,
          "the sender's very next hook (mid-turn) prints the order: the tool, the id, the letter")
    check("mcp__ccd_session_mgmt__send_message" in ctx and "load it first" in ctx,
          "…naming the older tool too, and how to load a deferred one")
    check(not raises(w), "an attended window gets NO desktop notice: %s" % raises(w))
    e = fd_entry(w, tok(w, ask))
    check((e.get("attended") or {}).get("road") == "send"
          and (e.get("attended") or {}).get("tests") == ["transcript"],
          "the letter records its road and the test that said attended: %s" % e.get("attended"))
    # The target's hook injects the pushed letter's body and token (postman.py observe).
    claude_transcript(w, SID_A, [claude_hook_context(SID_A, letter_context(w, ask))])
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    e = fd_entry(w, tok(w, ask))
    check(e.get("state") == "delivered" and (e.get("delivered") or {}).get("road") == "send",
          "SEEN in the target's own transcript: delivered, road `send`: %s" % e.get("delivered"))
    check(not fd_orders(w, SID_B), "…and the spent order leaves the carrier's pending file")
    check(not [i for i in pending_of(w, SID_A) if i.get("token") == tok(w, ask)]
          and [i for i in pending_of(w, SID_A) if i.get("token") == tok(w, fyi)],
          "…and the pushed letter leaves the target's own file, so its next turn does not print "
          "it twice; the FYI line waits there for that turn (BQ-307 M-F)")


def case_fd2():
    start("FD2", "ATTENDED because it is the app's FRONTED window, though its transcript is 40 min quiet")
    w = fd_world("fd2", holder_age_s=2400)
    fd_store(w, SID_A, "local_gatea", FD_TITLE, focused_s_ago=5)       # brought to the front
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=600)
    code, out, ask = fd_send(w, "look at the plate now", "no reply needed — FYI")
    pmn(w, "--pass", "--no-pull")
    e = fd_entry(w, tok(w, ask))
    check((e.get("attended") or {}).get("tests") == ["fronted"],
          "the test that said attended is `fronted`, read from lastFocusedAt: %s" % e.get("attended"))
    check(not fd_orders(w, SID_B) and not fd_orders(w, SID_A)
          and [i for i in pending_of(w, SID_A) if i.get("token") == tok(w, ask)]
          and (e.get("attended") or {}).get("road") == "announce"
          and [r["argv"][-1] for r in raises(w)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "an FYI line to the fronted window is NOT pushed (BQ-307 M-F): it takes the idle road — "
          "queued for its next turn, ONE zero-token notice: %s" % e.get("attended"))
    start("FD2b", "a routine's run is never a carrier (the send tool is not there in it)")
    v = fd_world("fd2b")
    fd_store(v, SID_B, "local_gateb", "Session hygiene watcher", scheduled=True)
    claude_transcript(v, FD_SID_C)
    fd_store(v, FD_SID_C, "local_gatec", "ACT — Exocortex/Desk: the desk", focused_s_ago=900)
    code, out, ask = fd_send(v, "carry this one", sender=SID_B)
    pmn(v, "--pass", "--no-pull")
    check(not fd_orders(v, SID_B) and len(fd_orders(v, FD_SID_C)) == 1,
          "the sender is a routine's run, so the order goes to the next Claude window instead")


def case_fd3():
    start("FD3", "BUSY (its transcript moved seconds ago): its own hook carries the ask; nothing is pushed (BQ-307 M-F)")
    w = fd_world("fd3", holder_age_s=5)
    code, out, ask = fd_send(w, "answer me mid-build")
    code, out, fyi = fd_send(w, "an aside", "FYI")
    age_file(w["tpath"], 5)
    pmn(w, "--pass", "--no-pull")
    orders = fd_orders(w, SID_B)
    check(not orders and not fd_orders(w, SID_A),
          "no send order at all — the FYI line is never pushed (BQ-307 M-F): %s"
          % [o.get("tokens") for o in orders])
    code, hout, _e = hook(w, SID_A, "PostToolBatch")
    check(tok(w, ask) in context_of(hout), "…and the window's own next hook carries the ask")


def case_fd4():
    start("FD4", "IDLE: queued for its next turn AND announced at once — one notice, the plain text, the count")
    w = fd_world("fd4", holder_age_s=2400)
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    code, out, one = fd_send(w, "the first", "answer it")
    code, out, two = fd_send(w, "the second", "FYI")
    pmn(w, "--pass", "--no-pull")
    texts = [r["argv"][-1] for r in raises(w)]
    check("GUI review: 2 letters waiting — they show at its next turn" in texts,
          "the notice says exactly `GUI review: 2 letters waiting — they show at its next turn`: %s" % texts)
    check(texts and texts[0] == "GUI review: 1 letter waiting — it shows at its next turn",
          "…and the send's own pass, one letter earlier, said the singular: %s" % texts[:1])
    check(not fd_orders(w, SID_B) and not fd_orders(w, SID_A), "an idle window is never pushed")
    check(len(pending_of(w, SID_A)) == 2, "both letters wait in its own pending file (BQ-143 stands)")
    before = len(raises(w))
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    check(len(raises(w)) == before, "a second pass with nothing new raises nothing more")
    marks = fd_marks(w)
    m = ((marks or {}).get("sessions") or {}).get(SID_A) or {}
    check(m.get("count") == 2 and m.get("road") == "announce" and m.get("title") == FD_TITLE,
          "mail-marks-north.json carries ✉ 2 for that window, its road and its name: %s" % m)
    check(m.get("lane") == "HUB" and not m.get("from")
          and not any(x in str(m.get("subject") or "") for x in ("Exocortex", "the first", "the second")),
          "…and the mark is a mark: the lane, and no sender or subject text (BQ-365; neither letter "
          "asks the person, so the hover's consequence is empty): %s"
          % {k: m.get(k) for k in ("lane", "from", "subject")})
    mtime = os.path.getmtime(str(w["hub"] / "mail-marks-north.json"))
    time.sleep(1.1)
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=2))
    check(os.path.getmtime(str(w["hub"] / "mail-marks-north.json")) == mtime,
          "…rewritten only when it changes: a quiet pass makes no brain write")
    for t in TREE_TOOLS:                              # this world draws the tree as well
        src = source_tool(t)
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / "tools" / t))
    plant_live(w, [SID_A], minutes=40.0)
    html = render(w)
    live = html[html.find('id="live"'):html.find('id="live"') + 6000]
    check("✉ 2" in live, "the tree's LIVE line for that window shows ✉ 2")
    # NOTE: the next two checks pin the TREE'S RENDERER as it stands (collect-openers.py is
    # not in this folder and was not touched); it still words `from <sender> · «subject»`.  The
    # postman's mark above carries neither.  Retiring that wording is the tree's own part.
    check("title=\"2 note(s) waiting for HUB · from Exocortex · «" in html,
          "…and the ✉ on the lane's face opens its hover with the nudge's own first words, the lane "
          "and who wrote (BQ-358): %s" % html[html.find("title=\"2 note"):][:100])
    co_spec = importlib.util.spec_from_file_location("co_fd4", str(w["hub"] / "tools" / "collect-openers.py"))
    co_mod = importlib.util.module_from_spec(co_spec)
    co_spec.loader.exec_module(co_mod)
    words = co_mod.mail_mark_words(dict(m, subject="the second"))
    check(words.startswith("2 notes waiting for HUB · from Exocortex · «the second» — ")
          and co_mod.mail_mark_words({"count": 1, "road": "hook"}).startswith("1 letter waiting — "),
          "…and the LIVE line's ✉ says the same words (a mark with no lane keeps the old ones): %s"
          % words[:90])
    os.unlink(str(w["hub"] / "mail-marks-north.json"))
    html2 = render(w, "tree2.html")
    live2 = html2[html2.find('id="live"'):html2.find('id="live"') + 6000]
    check("✉" not in live2.split("</ul>")[0],
          "…and with no marks file the LIVE line carries no ✉ at all")


def case_fd5():
    start("FD5", "A FABLE window is never WOKEN from idle; attended is the only exception")
    w = fd_world("fd5", holder_age_s=2400, model="claude-fable-5-1")
    code, out, ask = fd_send(w, "an ask for the fable hub")
    pmn(w, "--pass", "--no-pull")
    check(not fd_orders(w, SID_B) and not fd_orders(w, SID_A),
          "idle Fable window: no send order anywhere")
    check([r["argv"][-1] for r in raises(w)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "…one zero-token notice instead")
    code, wout, _took = qw_wait_once(w, SID_A, FD_TITLE)
    check("wait refused" in wout and not (w["post"] / "waiters" / ("%s.alive" % SID_A)).exists(),
          "…and the waiter still refuses the Fable window, so nothing can wake it (BQ-144): %s"
          % wout.strip()[:80])
    a = fd_world("fd5b", holder_age_s=2400, model="claude-fable-5-1")
    fd_store(a, SID_A, "local_gatea", FD_TITLE, focused_s_ago=3)
    fd_store(a, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=900)
    code, out, ask = fd_send(a, "an ask while the owner is looking at the fable hub")
    pmn(a, "--pass", "--no-pull")
    check(len(fd_orders(a, SID_B)) == 1,
          "the SAME Fable window, fronted: pushed — a turn where someone is watching is not wasted")


def case_fd6():
    start("FD6", "REMOTE CONTROL: honoured only from a fresh hint file; the store does not carry it")
    w = fd_world("fd6", holder_age_s=2400)
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    write_json(w["post"] / "remote-control.json",
               {"written": iso(datetime.datetime.now().astimezone()), "sessions": ["local_gatea"]})
    code, out, ask = fd_send(w, "for the phone that is driving this window")
    pmn(w, "--pass", "--no-pull")
    e = fd_entry(w, tok(w, ask))
    check((e.get("attended") or {}).get("tests") == ["remote"] and len(fd_orders(w, SID_B)) == 1,
          "a fresh hint naming the window's app id makes it attended by `remote`: %s" % e.get("attended"))
    x = fd_world("fd6b", holder_age_s=2400)
    fd_store(x, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    write_json(x["post"] / "remote-control.json",
               {"written": later(minutes=-30), "sessions": ["local_gatea"]})
    code, out, ask = fd_send(x, "an old hint says nothing")
    pmn(x, "--pass", "--no-pull")
    check((fd_entry(x, tok(x, ask)).get("attended") or {}).get("road") == "announce",
          "a hint thirty minutes old is not believed: idle, announced")


def case_fd7():
    start("FD7", "nothing older than the road is pushed or announced: an install is not a burst of banners")
    w = fd_world("fd7", holder_age_s=2400)
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    code, out, old = fd_send(w, "a letter from before the road")
    st = state_of(w)
    st.pop("attend_from", None)
    st.pop("announced", None)
    for e in (st.get("letters") or {}).values():
        e["first_seen"] = later(hours=-9)
        e.pop("attended", None)
    write_state(w, st)
    try:
        os.unlink(str(w["base"] / "notify-calls.jsonl"))
    except OSError:
        pass
    pmn(w, "--pass", "--no-pull")
    check(not raises(w) and state_of(w).get("attend_from"),
          "the first pass of the road writes its beginning and raises nothing: %s" % raises(w))
    m = (((fd_marks(w) or {}).get("sessions") or {}).get(SID_A) or {})
    check(m.get("count") == 1, "…while the old letter still wears its ✉ on the tree: %s" % m)
    code, out, new = fd_send(w, "the first letter after it")
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    texts = [r["argv"][-1] for r in raises(w)]
    check(texts == ["GUI review: 2 letters waiting — they show at its next turn"],
          "the first letter AFTER the beginning fires the notice, and its count is every letter "
          "waiting there, the old one too: %s" % texts)


def case_fd8():
    start("FD8", "the notice on Windows: the same text through the toast road, no shell ever parses it")
    w = fd_world("fd8")
    pmod = load_postman(w)
    argv, env_add, flags, how = pmod.notify_command("Exocortex", "mail waiting",
                                                   pmod.ANNOUNCE_MANY % ("GUI review", 2), kind="nt")
    check(how == "toast" and argv[0] == "powershell.exe" and "-EncodedCommand" in argv,
          "the Windows road is the toast, sent encoded")
    check(env_add.get("EXO_NOTE_BODY") == "GUI review: 2 letters waiting — they show at its next turn",
          "…and the text reaches it in the environment, verbatim")
    try:
        ("GUI review: 2 letters waiting — they show at its next turn").encode("cp1252")
        ok = True
    except UnicodeEncodeError:
        ok = False
    check(ok, "the notice text is cp1252-safe, so a Windows console can print it too")


def case_fd9():
    start("FD9", "REMOTE CONTROL, written by the tool (BQ-171): --remote-hint writes what the remote test reads")
    w = fd_world("fd9", holder_age_s=2400)
    fd_store(w, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    hint = w["post"] / "remote-control.json"
    code, out = pm(w, "--remote-hint", "local_gatea")
    body = json.loads(io.open(str(hint), encoding="utf-8").read()) if hint.is_file() else {}
    written = datetime.datetime.fromisoformat(body["written"]) if body.get("written") else None
    age = (datetime.datetime.now().astimezone() - written).total_seconds() if written else None
    check(code == 0 and body.get("sessions") == ["local_gatea"] and age is not None and abs(age) < 60,
          "`--remote-hint local_gatea` writes POST DIR's remote-control.json: `written` now, "
          "`sessions` the id given: %s" % body)
    check("1 window(s) served by Remote Control (local_gatea)" in out,
          "…and says so in one line: %s" % out.strip()[:140])
    if os.name != "nt":
        check((os.stat(str(hint)).st_mode & 0o777) == 0o600,
              "…private to this account, as every file in POST DIR is (%o)"
              % (os.stat(str(hint)).st_mode & 0o777))
    code, out, ask = fd_send(w, "for the window a phone is driving")
    e = fd_entry(w, tok(w, ask))
    check((e.get("attended") or {}).get("tests") == ["remote"] and len(fd_orders(w, SID_B)) == 1,
          "the hint the tool wrote makes the quiet window attended by `remote`, and it is pushed: %s"
          % e.get("attended"))
    x = fd_world("fd9b", holder_age_s=2400)
    fd_store(x, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    code, out = pm(x, "--remote-hint", SID_A, SID_A)
    body = json.loads(io.open(str(x["post"] / "remote-control.json"), encoding="utf-8").read())
    check(code == 0 and body.get("sessions") == [SID_A],
          "the transcript's own id is the other form it takes, and a repeat is kept once: %s"
          % body.get("sessions"))
    code, out, ask = fd_send(x, "the jsonl form reaches it too")
    check((fd_entry(x, tok(x, ask)).get("attended") or {}).get("tests") == ["remote"],
          "…and the remote test reads that form as well")
    y = fd_world("fd9c", holder_age_s=2400)
    fd_store(y, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    pm(y, "--remote-hint", "local_gatea")
    code, out = pm(y, "--remote-hint")
    body = json.loads(io.open(str(y["post"] / "remote-control.json"), encoding="utf-8").read())
    check(code == 0 and body.get("sessions") == [] and "no window is served" in out,
          "`--remote-hint` with no ids REPLACES the file with an empty list: %s · %s"
          % (body, out.strip()[:80]))
    code, out, ask = fd_send(y, "nobody is driving it now")
    check((fd_entry(y, tok(y, ask)).get("attended") or {}).get("road") == "announce"
          and not fd_orders(y, SID_B),
          "…and the window is idle again: announced, never pushed")
    z = fd_world("fd9d", holder_age_s=2400)
    fd_store(z, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=5)
    code, out = pm(z, "--remote-hint", "local_gatea", "--now", later(minutes=-30))
    code, out, ask = fd_send(z, "a hint written half an hour ago")
    check((fd_entry(z, tok(z, ask)).get("attended") or {}).get("road") == "announce",
          "a hint older than REMOTE_FRESH_S is not believed: idle, announced")
    before = io.open(str(z["post"] / "remote-control.json"), encoding="utf-8").read()
    code, out = pm(z, "--remote-hint", "local_gatea", "../x")
    check(code == 2 and "nothing written" in out
          and io.open(str(z["post"] / "remote-control.json"), encoding="utf-8").read() == before,
          "an id that is not a plain token writes nothing at all, exit 2: %s" % out.strip()[:100])
    routine = qw_text(HERE.parent / "routines" / "session-hygiene-watcher.md")
    if routine is None:
        skip("routines/session-hygiene-watcher.md is not beside this gate's folder — NOT RUN")
    else:
        step = qw_duty(routine, "THE REMOTE CONTROL HINT")
        check("remoteControlActive" in step and "`python3 tools/postman.py --remote-hint <id> <id> …`"
              in step and "`python3 tools/postman.py --remote-hint` with no id" in step,
              "the hygiene pass writes it from the one list that carries the fact (routine step 1b)")


def fd_meter(w, pct, kind="week", model=""):
    """A usage meter in the world's hub, in the shape `usage.py --write` files it, and usage.py
    beside the postman so the pass can read it (the FD worlds carry no meter otherwise)."""
    if not (w["hub"] / "tools" / "usage.py").is_file():
        shutil.copy2(str(source_tool("usage.py")), str(w["hub"] / "tools" / "usage.py"))
    now = datetime.datetime.now().astimezone()
    label = "Weekly \u00b7 all models" if kind == "week" else "Weekly \u00b7 %s" % model.capitalize()
    # a reader reads its OWN login's meter — the app's signed-in login in .claude.json —
    # and no other, so the world that holds a meter names that login too
    write_json(w["home"] / ".claude.json", {"oauthAccount": {"emailAddress": "wren@example.test",
                                                             "accountUuid": "a1b2c3d4-fd10"}})
    write_json(w["hub"] / "usage-north-claude-wren-at-example.test.json",
               {"vendor": "claude", "machine": "north", "login": "wren@example.test",
                "login_source": "--login", "read_at": iso(now - datetime.timedelta(minutes=1)),
                "source": "gate-comms FD10", "meter": "readable", "spend": None,
                "windows": [{"label": label, "percent": pct, "kind": kind, "model": model,
                             "resets_at": iso(now + datetime.timedelta(days=2))}]})


def road_of(out):
    return [l for l in out.splitlines() if l.startswith("road:")]


def case_fd10():
    start("FD10", "UNDER A USAGE PAUSE the attended road is held: queued, announced, never pushed")
    w = fd_world("fd10")
    fd_meter(w, 95)
    code, out, ask = fd_send(w, "an ask while the meter is paused")
    check(not fd_orders(w, SID_B) and not fd_orders(w, SID_A),
          "an all-models PAUSE: no send order in any pending file, though the window is attended")
    check([t for t in pending_of(w, SID_A) if t.get("token") == tok(w, ask)],
          "…the letter waits in the window's own pending file for its next turn")
    check([r["argv"][-1] for r in raises(w)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "…and ONE zero-token notice says so: %s" % [r["argv"][-1] for r in raises(w)])
    m = ((fd_marks(w) or {}).get("sessions") or {}).get(SID_A) or {}
    check(m.get("count") == 1 and m.get("road") == "announce" and m.get("attended") is True
          and m.get("why") == "held: usage PAUSE (all models 95 percent)",
          "the ✉ mark: attended, road announce, held by the meter it names: %s" % m)
    check(road_of(out) == ["road: not pushed into «%s» — held: usage PAUSE (all models 95 percent); "
                           "it is attended (transcript), so it is queued for its next turn and a "
                           "desktop notice said so" % FD_TITLE],
          "`--send` says it was NOT pushed and which meter held it: %s" % road_of(out))
    start("FD10b", "a Fable-week PAUSE does not reach a Sonnet window: its attended road is as it was")
    b = fd_world("fd10b")
    fd_meter(b, 95, kind="week-model", model="fable")
    code, out, ask = fd_send(b, "an ask for the sonnet window")
    check(len(fd_orders(b, SID_B)) == 1 and not raises(b),
          "pushed at once by one send order, and no banner: %s" % [o.get("target") for o in fd_orders(b, SID_B)])
    check(road_of(out) and road_of(out)[0].startswith("road: pushed into «%s» now — it is attended "
                                                      "(transcript)" % FD_TITLE),
          "…and `--send` says pushed: %s" % road_of(out))
    start("FD10c", "…and the same Fable-week PAUSE DOES reach a Fable window someone is looking at")
    c = fd_world("fd10c", holder_age_s=2400, model="claude-fable-5-1")
    fd_store(c, SID_A, "local_gatea", FD_TITLE, focused_s_ago=3)
    fd_store(c, SID_B, "local_gateb", "ACT — Exocortex/Sender: the sender", focused_s_ago=900)
    fd_meter(c, 95, kind="week-model", model="fable")
    code, out, ask = fd_send(c, "an ask for the fronted fable hub")
    check(not fd_orders(c, SID_B) and not fd_orders(c, SID_A)
          and [r["argv"][-1] for r in raises(c)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "fronted, but its own model is paused: held, one notice, no order anywhere")
    check(road_of(out) and "held: usage PAUSE (Fable 95 percent)" in road_of(out)[0]
          and "attended (fronted)" in road_of(out)[0],
          "…said with the meter that held it: %s" % road_of(out))


def case_fd11():
    start("FD11", "the PAUSE reaches an order already queued: taken back unless handed; lifted, a fresh one")
    w = fd_world("fd11")
    code, out, ask = fd_send(w, "an ask sent before the pause")
    key = [o.get("token") for o in fd_orders(w, SID_B)]
    check(len(key) == 1, "below PAUSE the order is queued in the sender's file: %s" % key)
    fd_meter(w, 95)
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    rec = (state_of(w).get("sends") or {}).get(key[0] if key else "") or {}
    check(not fd_orders(w, SID_B) and rec.get("state") == "held"
          and rec.get("held") == "all models 95 percent",
          "the PAUSE begins before the carrier's next turn: the order is TAKEN BACK and recorded "
          "held: %s" % {k: rec.get(k) for k in ("state", "held")})
    e = fd_entry(w, tok(w, ask))
    check((e.get("attended") or {}).get("road") == "announce"
          and (e.get("attended") or {}).get("held") == "all models 95 percent"
          and len(raises(w)) == 1,
          "…the letter takes the held road and ONE notice is raised: %s" % e.get("attended"))
    fd_meter(w, 50)
    pmn(w, "--pass", "--no-pull", "--now", later(minutes=2))
    orders = fd_orders(w, SID_B)
    e = fd_entry(w, tok(w, ask))
    check(len(orders) == 1 and orders[0].get("target") == "local_gatea"
          and (e.get("attended") or {}).get("road") == "send",
          "the PAUSE lifts and the window is still attended: a fresh order goes out: %s"
          % e.get("attended"))
    h = fd_world("fd11b")
    code, out, ask = fd_send(h, "an ask whose order is already handed")
    code, hout, _err = hook(h, SID_B, "PostToolBatch")
    check("SendMessage" in context_of(hout) and not fd_orders(h, SID_B),
          "the carrier's own hook has taken the order before the PAUSE")
    fd_meter(h, 95)
    pmn(h, "--pass", "--no-pull", "--now", later(minutes=1))
    e = fd_entry(h, tok(h, ask))
    check((e.get("attended") or {}).get("road") == "send"
          and "ordered before the usage PAUSE" in ((e.get("attended") or {}).get("why") or ""),
          "an order already handed cannot be taken back, and the road says so rather than "
          "pretend: %s" % e.get("attended"))


# ==========================================================================
# OLD MAIL STOPS RINGING — extended
# 
# ==========================================================================
# Every world here is the gate's own, in the system temp folder under the runner's own
# prefix (exo-prove-comms-<pid>-<name>), removed with the rest at the end of the run.

def om_base(name):
    return Path(tempfile.gettempdir()) / ("exo-prove-comms-%d-%s" % (os.getpid(), name))


def om_world(name, prime=True):
    return pworld(name, prime=prime, base_dir=om_base(name))


def om_day(days=0):
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def om_weekday(days):
    """The weekday `days` from today in usage.py's own English three letters — never the
    process locale's."""
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[
        (datetime.date.today() + datetime.timedelta(days=days)).weekday()]


def om_iso_z(when):
    return when.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def om_transcript(w, sid, began, model="claude-sonnet-5"):
    """A Claude window that BEGAN at `began` (its first record's own timestamp) and wrote
    a moment ago (the file's mtime is now)."""
    path = w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % sid)
    rows = [{"type": "user", "sessionId": sid, "uuid": "om-u1", "timestamp": om_iso_z(began),
             "message": {"role": "user", "content": "go"}},
            {"type": "assistant", "sessionId": sid, "uuid": "om-a1",
             "timestamp": om_iso_z(began + datetime.timedelta(seconds=5)),
             "message": {"role": "assistant", "model": model,
                         "content": [{"type": "text", "text": "ok"}],
                         "usage": {"input_tokens": 4000}}}]
    write(path, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    return path


def om_append(path, rec):
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def om_pause(w, date, meter, reset, login="wren@example.test", write_it=True):
    line = ("- %s · to: NORTH/all · Exocortex · USAGE PAUSE — %s · %s · continue, or button "
            "up? · say «continue» (work on until the reset) or «button up» (the hub buttons up "
            "now) · read 1 min ago · %s · answer in your window: continue, or button up"
            % (date, meter, reset, login))
    if write_it:
        with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
    return line


def om_stamp_line(w, line, by=HOLDER):
    """--mark's own rewrite, for one line: the tail appended IN PLACE."""
    path = w["hub"] / "INBOX.md"
    text = io.open(str(path), encoding="utf-8").read()
    stamp = " · delivered: %s by %s" % (iso(datetime.datetime.now().astimezone()), by)
    assert text.count(line + "\n") == 1
    write(path, text.replace(line + "\n", line + stamp + "\n"))


def om_tokens(items):
    return [i.get("token") for i in items]


def om_all_pending(w):
    out = {}
    for f in sorted((w["post"] / "pending").glob("*.json")):
        out[f.stem] = json.loads(io.open(str(f), encoding="utf-8").read())
    return out


def om_entry(w, token):
    return (state_of(w).get("letters") or {}).get(token) or {}


# A driver for mail.py's OWN wait() with the floor road's pull every second instead of
# every 150 s — the one constant it changes, in its own process (the WAIT_DRIVER pattern).
OM_FLOOR_DRIVER = (
    "import importlib.util, sys\n"
    "from pathlib import Path\n"
    "spec = importlib.util.spec_from_file_location('m', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "mod.FLOOR_EVERY_S = float(sys.argv[2])\n"
    "mod.HUB = Path(sys.argv[3])\n"
    "mod.INBOX = mod.HUB / 'INBOX.md'\n"
    "sys.exit(mod.wait(sys.argv[4], title=None, max_hours=float(sys.argv[5]),\n"
    "                  hub=sys.argv[3], poll=0.5))\n"
)

# A driver that records the PATH of every os.stat the hook's own code makes (M10).
OM_STAT_PATHS = (
    "import importlib.util, json, os, sys\n"
    "spec = importlib.util.spec_from_file_location('pm', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"
    "seen = []\n"
    "real = os.stat\n"
    "def counted(p, *a, **k):\n"
    "    seen.append(str(p))\n"
    "    return real(p, *a, **k)\n"
    "os.stat = counted\n"
    "code = mod.hook_main(['--hook', '--vendor', 'claude', '--post-dir', sys.argv[2]])\n"
    "sys.stderr.write('PATHS=%s\\n' % json.dumps(seen))\n"
    "sys.exit(code)\n"
)


def om_stat_paths(w, sid, event):
    write(w["base"] / "om-statpaths.py", OM_STAT_PATHS)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in w["env"].items():
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    p = subprocess.run([PY, str(w["base"] / "om-statpaths.py"),
                        str(w["hub"] / "tools" / "postman.py"), str(w["post"])],
                       input=json.dumps({"session_id": sid, "hook_event_name": event,
                                         "cwd": str(w["hub"]), "transcript_path": ""}),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                       env=env, timeout=60)
    m = re.search(r"PATHS=(\[.*\])", p.stderr or "")
    return (json.loads(m.group(1)) if m else None), p.stdout


def case_om1():
    start("BQ307-M1", "THE INBOX STAMP IS DELIVERY: a waiting letter stamped by --mark under the "
                      "offset is delivered, dropped, never queued again")
    w = om_world("om1")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        for n in range(80):                       # > 4 KB above the letter: the head never sees it
            fh.write("- %s · to: NORTH/other · Exocortex · a filler line %02d for the head · FYI\n"
                     % (om_day(), n))
    one = letter(w, "NORTH/hub", "the letter a --mark will stamp")
    pm(w, "--pass", "--no-pull")
    check(tok(w, one) in om_tokens(pending_of(w, SID_A)), "the letter is queued for its holder")
    mp(w, "--read", "NORTH/hub", "--title", HOLDER)
    two = letter(w, "NORTH/hub", "a later letter the mark must not touch")
    pm(w, "--pass", "--no-pull")
    head_before = (w["hub"] / "INBOX.md").read_bytes()[:4096]
    code, out = mp(w, "--read", "NORTH/hub", "--mark", HOLDER)
    text = io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read()
    check("marked 1 delivered" in out and " · delivered:" in [l for l in text.splitlines()
                                                              if one in l][0],
          "mail.py --mark stamped the first letter in INBOX.md, in place")
    check((w["hub"] / "INBOX.md").read_bytes()[:4096] == head_before,
          "…a rewrite the head fingerprint cannot see (the first 4 KB are byte-identical)")
    counters = w["base"] / "om1-counters.json"
    code, out = pm(w, "--pass", "--no-pull", "--counters", str(counters))
    e = om_entry(w, tok(w, one))
    check(e.get("state") == "delivered" and (e.get("delivered") or {}).get("road") == "inbox stamp"
          and (e.get("delivered") or {}).get("title") == HOLDER,
          "after ONE pass the letter is delivered, road `inbox stamp`, by the title the stamp "
          "names: %s" % e.get("delivered"))
    size = (w["hub"] / "INBOX.md").stat().st_size
    c = json.loads(io.open(str(counters), encoding="utf-8").read())
    check(c["inbox_bytes"] >= size, "the seam saw the rewrite: the file was re-parsed whole "
                                    "(%d of %d bytes)" % (c["inbox_bytes"], size))
    held = om_all_pending(w)
    check(not [s for s, d in held.items() if tok(w, one) in om_tokens(d.get("items") or [])],
          "it is in NO pending file now")
    check(tok(w, two) in om_tokens(pending_of(w, SID_A)), "…and the later letter still waits")
    check("skipped this pass: 1 delivered by stamp" in out,
          "the pass says what it skipped (M-G): %s" % [l for l in out.splitlines()
                                                       if l.startswith("skipped")])
    post = post_of(w)
    check(((post.get("letters") or {}).get(tok(w, one)) or {}).get("state") == "delivered",
          "post-north.json says delivered too, so every machine's --read agrees")
    pm(w, "--pass", "--no-pull")
    check(tok(w, one) not in om_tokens(pending_of(w, SID_A)), "a second pass queues it no more")
    code, sout = pm(w, "--status", "--no-pull")
    check("skipped by the pass of" in sout and "1 delivered by stamp" in sout,
          "--status names the last pass's skips: %s"
          % [l for l in sout.splitlines() if l.startswith("skipped")])
    three = letter(w, "NORTH/hub", "a letter that arrives already stamped")
    om_stamp_line(w, three)
    pm(w, "--pass", "--no-pull")
    check(om_entry(w, tok(w, three)).get("state") == "delivered"
          and tok(w, three) not in om_tokens(pending_of(w, SID_A)),
          "a letter that arrives already stamped is delivered at first sight and never queued")
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    ctx = context_of(hout)
    check(tok(w, two) in ctx and tok(w, one) not in ctx and tok(w, three) not in ctx,
          "the window's turn start carries the one letter left and neither stamped one")


def case_om2():
    start("BQ307-M2", "A NEW SESSION is handed 10 letters, not 300: the 290 stamped ones are "
                      "skipped, and the frame says so")
    w = om_world("om2")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    lines = []
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        for n in range(300):
            line = "- %s · to: NORTH/hub · Exocortex · letter number %03d for the hub · answer it" \
                   % (om_day(), n)
            fh.write(line + "\n")
            lines.append(line)
    pm(w, "--pass", "--no-pull")
    check(len(pending_of(w, SID_A)) == 300 and not (state_of(w).get("receipts") or {}),
          "the old road's picture: a new session with no receipts, 300 letters queued, none "
          "delivered")
    text = io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read()
    stamp = " · delivered: %s by an earlier hub window" % iso(datetime.datetime.now().astimezone())
    for line in lines[:290]:
        text = text.replace(line + "\n", line + stamp + "\n", 1)
    write(w["hub"] / "INBOX.md", text)
    pm(w, "--pass", "--no-pull")
    left = pending_of(w, SID_A)
    check(len(left) == 10, "after one pass the pending file holds 10 (%d)" % len(left))
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    ctx = context_of(hout)
    head = ctx.splitlines()[0] if ctx else ""
    carried = len(set(re.findall(r"\[(pm-[0-9a-f]{12})\]", ctx)))
    check(carried == 10, "the hook carries 10 letters (%d)" % carried)
    check("skipped 290 already delivered" in head,
          "the frame's head says `skipped 290 already delivered`: %s" % head[:160])
    check(not pending_of(w, SID_A) and not (w["post"] / "pending" / ("%s.json" % SID_A)).exists(),
          "…and the pending file is gone, so the next turn's one stat finds nothing")
    start("BQ307-M2b", "the hook's own rule: letters the post state calls delivered are never "
                       "handed, whoever left them in the file")
    items = [{"token": tok(w, l), "kind": "letter", "line": l, "to": "NORTH/hub", "fyi": False,
              "queued": iso(datetime.datetime.now().astimezone())} for l in lines]
    write_json(w["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": items})
    done = json.loads(io.open(str(w["post"] / "done.json"), encoding="utf-8").read())
    check(sum(1 for l in lines if (done.get("tokens") or {}).get(tok(w, l)) == "delivered") >= 290,
          "the pass's done index carries the 290 (and what the turn start just read)")
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    ctx = context_of(hout)
    carried = set(re.findall(r"\[(pm-[0-9a-f]{12})\]", ctx))
    delivered = set(t for t, s in (done.get("tokens") or {}).items() if s == "delivered")
    check(not (carried & delivered) and len(carried) == 300 - len(delivered & set(tok(w, l) for l in lines)),
          "a pending file refilled with all 300: the hook hands only what is not delivered "
          "(%d handed)" % len(carried))
    check("skipped %d already delivered" % len(delivered & set(tok(w, l) for l in lines)) in ctx,
          "…and its head counts the skipped: %s" % (ctx.splitlines()[0][:140] if ctx else ""))
    check(not (w["post"] / "pending" / ("%s.json" % SID_A)).exists(),
          "…and what it skipped leaves the file with what it carried")


def case_om3():
    start("BQ307-M3", "A BROADCAST first seen 20 days ago meets a window born today: no copy, "
                      "and the letter reads expired")
    w = om_world("om3")
    now = datetime.datetime.now().astimezone()
    line = letter(w, "NORTH/all", "a broadcast from twenty days ago", "run your ritual again",
                  date=om_day(-20))
    pm(w, "--pass", "--no-pull", "--now", later(hours=-20 * 24))   # seen then, no lane live
    sid = "dddddddd-1111-2222-3333-dddddddddddd"
    plant_claim(w, "Proj/Born", "north", "ACT — Proj/Born: born today", session=sid)
    om_transcript(w, sid, now - datetime.timedelta(hours=1))
    code, out = pm(w, "--pass", "--no-pull")
    mail = load_mail(w)
    child = mail.child_token(tok(w, line), sid)
    letters = post_of(w).get("letters") or {}      # published before prune lets it go
    e = letters.get(tok(w, line)) or {}
    check(child not in letters and child not in (state_of(w).get("letters") or {})
          and not pending_of(w, sid),
          "no copy is made for it and nothing is queued")
    check(e.get("state") == "expired" and e.get("why") == "a broadcast is for the lanes live that day",
          "the broadcast reads expired, `a broadcast is for the lanes live that day`: %s / %s"
          % (e.get("state"), e.get("why")))
    check(str(e.get("first_seen") or "").startswith(om_day(-20)),
          "…first seen on its own date, twenty days ago: %s" % e.get("first_seen"))


def case_om4():
    start("BQ307-M4", "A BROADCAST two hours old reaches the lane live since yesterday — and not "
                      "the one born after it")
    w = om_world("om4")
    now = datetime.datetime.now().astimezone()
    line = letter(w, "NORTH/all", "the meter moved, read this", "run your ritual again")
    pm(w, "--pass", "--no-pull", "--now", later(hours=-2))     # first seen two hours ago
    old_sid, new_sid = "eeeeeeee-1111-2222-3333-eeeeeeeeeeee", "ffffffff-1111-2222-3333-ffffffffffff"
    plant_claim(w, "Proj/Old", "north", "ACT — Proj/Old: live since yesterday", session=old_sid)
    plant_claim(w, "Proj/New", "north", "ACT — Proj/New: born an hour ago", session=new_sid)
    om_transcript(w, old_sid, now - datetime.timedelta(days=1))
    om_transcript(w, new_sid, now - datetime.timedelta(hours=1))
    code, out = pm(w, "--pass", "--no-pull")
    mail = load_mail(w)
    kid = mail.child_token(tok(w, line), old_sid)
    check(kid in om_tokens(pending_of(w, old_sid)), "the lane live since yesterday has its copy queued")
    check(not pending_of(w, new_sid)
          and mail.child_token(tok(w, line), new_sid) not in (state_of(w).get("letters") or {}),
          "the lane born an hour ago gets none")
    check("1 born-after" in out, "the pass counts it (M-G): %s"
          % [l for l in out.splitlines() if l.startswith("skipped")])
    e = om_entry(w, tok(w, line))
    check(e.get("state") == "waiting" and e.get("children") == [kid],
          "the broadcast itself still waits on its one lane: %s" % e.get("why"))


def case_om5():
    start("BQ307-M5", "A USAGE PAUSE whose reset has passed: expired, and --read, --wait and the "
                      "hooks all skip it")
    w = om_world("om5")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    qw_heartbeat(w)
    line = om_pause(w, om_day(-1), "Fable 92 percent", "resets 10:00")
    code, out = pm(w, "--pass", "--no-pull")
    e = om_entry(w, tok(w, line))
    check(e.get("state") == "expired" and "reset has passed" in (e.get("why") or ""),
          "the pass reads it expired at its own reset: %s" % e.get("why"))
    mail = load_mail(w)
    kid = mail.child_token(tok(w, line), SID_A)
    check(not pending_of(w, SID_A) and kid not in (state_of(w).get("letters") or {}),
          "no lane is given a copy")
    code, rout = mp(w, "--read", "NORTH/hub", env=as_session(SID_A))
    check("USAGE PAUSE" not in rout, "--read does not print it: %s" % rout.strip()[:80])
    check(tok(w, line) in mail.quiet_alarms([line]) and mail.alarm_rang_out(line),
          "…by mail.py's own rule too, with no post file to ask: %s"
          % (mail.quiet_alarms([line]).get(tok(w, line)),))
    # a copy an older pass had already queued: the hook skips it, the waiter never ends on it
    write_json(w["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": tok(w, line), "kind": "letter", "line": line,
                           "to": "NORTH/all", "fyi": False, "queued": later(hours=-20)}]})
    proc = waiter(w, "NORTH/hub", HOLDER, env=as_session(SID_A))
    try:
        time.sleep(6)
        check(proc.poll() is None, "a waiter does not end on it")
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=10)
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    check("USAGE PAUSE" not in context_of(hout) and not pending_of(w, SID_A),
          "the hook carries nothing and the file is cleared: %s" % context_of(hout)[:80])


def case_om6():
    start("BQ307-M6", "TWO USAGE PAUSE letters for one machine: the later supersedes the earlier")
    w = om_world("om6")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    reset = "the week resets %s 10:00" % om_weekday(2)
    first = om_pause(w, om_day(), "Fable 90 percent", reset)
    pm(w, "--pass", "--no-pull")
    mail = load_mail(w)
    kid1 = mail.child_token(tok(w, first), SID_A)
    check(kid1 in om_tokens(pending_of(w, SID_A)), "a live alarm reaches its lane")
    second = om_pause(w, om_day(), "Fable 95 percent", reset)
    code, out = pm(w, "--pass", "--no-pull")
    e = om_entry(w, tok(w, first))
    check(e.get("state") == "expired" and e.get("superseded") is True
          and "superseded" in (e.get("why") or ""),
          "the first is SUPERSEDED: %s" % e.get("why"))
    kid2 = mail.child_token(tok(w, second), SID_A)
    toks = om_tokens(pending_of(w, SID_A))
    check(kid1 not in toks and kid2 in toks,
          "its lane's copy leaves the pending file; the later one is queued: %s" % toks)
    check("1 superseded" in out, "the pass counts it: %s"
          % [l for l in out.splitlines() if l.startswith("skipped")])
    code, rout = mp(w, "--read", "NORTH/hub", env=as_session(SID_A))
    check("Fable 95 percent" in rout and "Fable 90 percent" not in rout,
          "--read prints the later alarm only")
    ignore = ("- %s · to: NORTH/all · NORTH/hub · IGNORE the earlier USAGE PAUSE letter: a live "
              "proof · FYI — no reply needed" % om_day())
    other = om_pause(w, om_day(), "Fable 90 percent", reset, login="kestrel@example.test",
                     write_it=False)
    rows = [(tok(w, l), l, None) for l in (first, second, ignore)]
    v = mail.alarm_verdicts(rows)
    check(v.get(tok(w, second), ("",))[0] == "superseded" and tok(w, ignore) not in v,
          "an IGNORE note supersedes the alarm before it, and is not itself an alarm")
    v2 = mail.alarm_verdicts([(tok(w, other), other, None), (tok(w, second), second, None)])
    check(tok(w, other) not in v2,
          "a later alarm for ANOTHER login does not supersede one that names its own")


def case_om7():
    start("BQ307-M7", "THE WAITER ENDS ONLY ON TODAY'S MAIL — the postman's road")
    w = om_world("om7")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    qw_heartbeat(w)
    proc = waiter(w, "NORTH/hub", HOLDER, env=as_session(SID_A))
    try:
        armed(w, "NORTH/hub")
        old = letter(w, "NORTH/hub", "an asking letter from three days ago", date=om_day(-3))
        pm(w, "--pass", "--no-pull")
        check(tok(w, old) in om_tokens(pending_of(w, SID_A)),
              "the old asking letter is queued for the window's turn start")
        time.sleep(7)
        check(proc.poll() is None, "…and the wait goes on")
        new = letter(w, "NORTH/hub", "an asking letter from today")
        pm(w, "--pass", "--no-pull")
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(proc.returncode == 0 and tok(w, new) in out and tok(w, old) not in out,
              "today's letter ends it, and only today's is carried")
        check(out.count("1 earlier letter for NORTH/hub — read it with --read") == 1,
              "the one count line, printed once: %s"
              % [l for l in out.splitlines() if "earlier" in l])
        check(tok(w, old) in om_tokens(pending_of(w, SID_A)),
              "the old letter is left where it was, for --read and the next turn start")
    finally:
        if proc.poll() is None:
            proc.kill()
    start("BQ307-M7b", "…and the floor's own pull: last week's mail never ends the wait")
    f = om_world("om7b")
    claude_transcript(f, SID_A)
    write_json(f["post"] / "heartbeat.json",
               {"when": later(hours=-2), "every": 60, "version": 1})      # a stale postman
    write(f["base"] / "om-floor.py", OM_FLOOR_DRIVER)
    env_all = dict(os.environ)
    env_all["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in dict(f["env"], **as_session(SID_A)).items():
        env_all.pop(k, None) if v is None else env_all.__setitem__(k, str(v))
    proc = subprocess.Popen([PY, str(f["base"] / "om-floor.py"), str(f["hub"] / "tools" / "mail.py"),
                             "1", str(f["hub"]), "NORTH/hub", "0.05"], cwd=str(f["hub"]),
                            env=env_all, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    try:
        armed(f, "NORTH/hub")
        old = letter(f, "NORTH/hub", "a pull brought this three-day-old ask", date=om_day(-3))
        time.sleep(4)
        check(proc.poll() is None, "a pull that brings a three-day-old ask does not end the wait")
        new = letter(f, "NORTH/hub", "and this one is today's")
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(new in out and old not in out, "the floor carries today's ask and not the old one")
        check(out.count("1 earlier letter for NORTH/hub — read it with --read") == 1,
              "…and counts the old one in one line, once: %s"
              % [l for l in out.splitlines() if "earlier" in l])
    finally:
        if proc.poll() is None:
            proc.kill()


def case_om8():
    start("BQ307-M8", "AN FYI LETTER NEVER RIDES SEND_MESSAGE, attended or not")
    w = fd_world("om8", base_dir=om_base("om8"))
    code, out, fyi = fd_send(w, "the build is green", "FYI — no reply needed")
    e = fd_entry(w, tok(w, fyi))
    check(not fd_orders(w, SID_B) and not fd_orders(w, SID_A),
          "an attended window (its transcript moved): no send order anywhere")
    check(tok(w, fyi) in om_tokens(pending_of(w, SID_A))
          and (e.get("attended") or {}).get("road") == "announce"
          and (e.get("attended") or {}).get("tests") == ["transcript"],
          "it takes the idle road — queued for its next turn — and the road says why: %s"
          % e.get("attended"))
    check([r["argv"][-1] for r in raises(w)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "…with ONE zero-token notice, as an idle window gets: %s" % [r["argv"][-1] for r in raises(w)])
    check([l for l in road_of(out) if "an FYI letter is never pushed" in l],
          "`--send` tells the sender: %s" % road_of(out))
    code, out2, both = fd_send(w, "an ask beside the FYI line")
    e = fd_entry(w, tok(w, fyi))
    msg = " ".join(o.get("message") or "" for o in fd_orders(w, SID_B))
    check(tok(w, both) in msg and tok(w, fyi) not in msg
          and (fd_entry(w, tok(w, both)).get("attended") or {}).get("road") == "send",
          "an ASK to the same window is pushed — and the push never carries the FYI line")
    start("BQ307-M8b", "A RETITLE is not a turn: a window whose only recent line is bookkeeping "
                       "is not attended")
    b = fd_world("om8b", holder_age_s=2400, base_dir=om_base("om8b"))
    om_append(b["tpath"], {"type": "custom-title", "customTitle": "a new name", "sessionId": SID_A})
    om_append(b["tpath"], {"type": "agent-name", "agentName": "a new name", "sessionId": SID_A})
    code, out, ask = fd_send(b, "an ask after a retitle")
    e = fd_entry(b, tok(b, ask))
    check(not fd_orders(b, SID_B) and (e.get("attended") or {}).get("road") == "announce"
          and (e.get("attended") or {}).get("tests") == [],
          "the transcript moved, by a retitle only: idle, announced, not pushed: %s" % e.get("attended"))
    c = fd_world("om8c", holder_age_s=2400, base_dir=om_base("om8c"))
    om_append(c["tpath"], {"type": "user", "sessionId": SID_A, "uuid": "om8c",
                           "timestamp": om_iso_z(datetime.datetime.now().astimezone()
                                                 - datetime.timedelta(minutes=3)),
                           "message": {"role": "user", "content": "a turn"}})
    age_file(c["tpath"], 180)                    # three minutes ago: attended, not busy
    code, out, ask = fd_send(c, "an ask after a real turn")
    e = fd_entry(c, tok(c, ask))
    check(len(fd_orders(c, SID_B)) == 1 and (e.get("attended") or {}).get("tests") == ["transcript"],
          "the control: a USER message three minutes ago is attended, and the ask is pushed: %s"
          % e.get("attended"))


def case_om9():
    start("BQ307-M9", "A LANE THAT --read A BROADCAST has read it: its copy is delivered and no "
                      "hook carries it again")
    w = om_world("om9")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    line = letter(w, "NORTH/all", "a broadcast every lane should see", "run your ritual again")
    pm(w, "--pass", "--no-pull")
    mail = load_mail(w)
    kid = mail.child_token(tok(w, line), SID_A)
    check(kid in om_tokens(pending_of(w, SID_A)), "the lane's copy is queued")
    code, rout = mp(w, "--read", "NORTH/hub", env=as_session(SID_A))
    check(kid in rout, "--read prints it under the lane's own copy's token")
    claude_transcript(w, SID_A, [claude_hook_context(SID_A, letter_context(w, line, kid))])
    pm(w, "--pass", "--no-pull")
    check(om_entry(w, kid).get("state") == "delivered", "the pass SEES it in that transcript: delivered")
    check(kid not in om_tokens(pending_of(w, SID_A)), "…and takes it out of the pending file")
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    check(kid not in context_of(hout), "the next turn start does not carry it")
    write_json(w["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": kid, "kind": "letter", "line": line, "to": "NORTH/all",
                           "fyi": False, "broadcast": tok(w, line)}]})
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    check(kid not in context_of(hout) and not pending_of(w, SID_A),
          "…nor does one a stale file still held: skipped and cleared, silently")


def case_om10():
    start("BQ307-M10", "THE NO-MAIL PATH: one stat, nothing printed — and the pending path adds "
                       "one stat of the done index, no more")
    w = om_world("om10")
    for event in ("UserPromptSubmit", "PostToolBatch"):
        n = stats_for(w, SID_A, event)
        code, hout, _e = hook(w, SID_A, event)
        check(n == 1 and code == 0 and hout == "",
              "%s with no pending file: exactly %s stat, nothing printed" % (event, n))
    paths, _out = om_stat_paths(w, SID_A, "UserPromptSubmit")
    check(paths is not None and len(paths) == 1 and paths[0].endswith(SID_A + ".json"),
          "…and that one stat is the session's own pending file: %s" % paths)
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    letter(w, "NORTH/hub", "one letter for the pending path")
    pm(w, "--pass", "--no-pull")
    paths, out = om_stat_paths(w, SID_A, "UserPromptSubmit")
    dones = [p for p in (paths or []) if p.endswith("done.json")]
    check(len(dones) == 1 and "one letter for the pending path" in out,
          "the pending path stats the done index once (%d) and carries the letter" % len(dones))


def case_omh():
    start("BQ307-MH", "FIRST SEEN IS NEVER LATER THAN THE LETTER'S OWN DATE: a rebuilt post "
                      "state cannot ring last week's mail")
    w = om_world("omh")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    line = letter(w, "NORTH/hub", "an ask dated nine days ago", date=om_day(-9))
    code, out = pm(w, "--pass", "--no-pull")
    e = om_entry(w, tok(w, line))
    check(e.get("state") in (None, "expired") and not pending_of(w, SID_A)
          and tok(w, line) not in (post_of(w).get("letters") or {})
          and "1 expired" in out,
          "met for the first time today (a rebuilt state, a full re-parse), a nine-day-old ask "
          "is history: never queued, never a post-file row, counted: %s"
          % [l for l in out.splitlines() if l.startswith("skipped")])
    st = state_of(w)                               # the 10-14 00:31 picture, as the old pass left it
    st["letters"][tok(w, line)] = {"to": "NORTH/hub", "date": om_day(-9), "line": line,
                                   "fyi": False, "state": "waiting",
                                   "first_seen": iso(datetime.datetime.now().astimezone())}
    write_state(w, st)
    write_json(w["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": tok(w, line), "kind": "letter", "line": line,
                           "to": "NORTH/hub", "fyi": False}]})
    pm(w, "--pass", "--no-pull")
    e = (post_of(w).get("letters") or {}).get(tok(w, line)) or {}
    check(e.get("state") == "expired" and str(e.get("first_seen") or "").startswith(om_day(-9))
          and not pending_of(w, SID_A),
          "a state that says `first seen today` for it is clamped to the letter's own date, "
          "expired, and taken out of the pending file: %s" % e.get("first_seen"))
    start("BQ307-MHb", "A TOKEN HANDED ONCE is not news when a re-parse meets its line again, "
                       "even for a new window")
    h = om_world("omhb")
    plant_claim(h, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(h, SID_A)
    one = letter(h, "NORTH/hub", "a letter the old window was handed")
    pm(h, "--pass", "--no-pull")
    code, hout, _e = hook(h, SID_A, "UserPromptSubmit")
    check(tok(h, one) in context_of(hout), "the old window's turn start carried it (a receipt)")
    st = state_of(h)
    st["letters"].pop(tok(h, one), None)           # pruned, as the old prune did at seven days
    write_state(h, st)
    write(h["hub"] / "claims.json", "[]\n")
    plant_claim(h, "hub", "north", OTHER, session=SID_B)    # a NEW window holds the lane now
    claude_transcript(h, SID_B)
    text = io.open(str(h["hub"] / "INBOX.md"), encoding="utf-8").read()
    write(h["hub"] / "INBOX.md", "# INBOX (merged by the other machine)\n\n" + text.split("\n", 2)[2])
    code, out = pm(h, "--pass", "--no-pull")
    e = om_entry(h, tok(h, one))
    check(e.get("state") == "delivered" and (e.get("delivered") or {}).get("evidence") == "receipt"
          and not pending_of(h, SID_B) and "1 already handed" in out,
          "the full re-parse meets it again: delivered by its receipt, never queued for the new "
          "window, counted: %s" % [l for l in out.splitlines() if l.startswith("skipped")])
    start("BQ307-MHc", "a read the pass learns of late is history: no `has now been read` days "
                       "after the fact — a fresh one is still said")
    for name, stamped_min, pass_min, said in (("omhc", 60, 14 * 60, False),
                                              ("omhd", 10, 20, True)):
        r = om_world(name)
        claude_transcript(r, SID_A)
        plant_claim(r, "hub", "north", HOLDER, session=SID_B)    # an idle holder, no ear
        claude_transcript(r, SID_B)
        mp(r, "--send", "NORTH/hub", "Exocortex", "a letter its sender waits on", "reply when done",
           "--no-push", env=as_session(SID_A))
        pm(r, "--pass", "--no-pull", "--now", later(minutes=7))       # the sender hears `not read`
        hook(r, SID_A, "UserPromptSubmit")                             # …and reads that notice
        line = [l for l in inbox_lines(r) if "a letter its sender waits on" in l][0]
        text = io.open(str(r["hub"] / "INBOX.md"), encoding="utf-8").read()
        write(r["hub"] / "INBOX.md", text.replace(
            line + "\n", line + " · delivered: %s by %s\n" % (later(minutes=stamped_min), HOLDER)))
        code, out = pm(r, "--pass", "--no-pull", "--now", later(minutes=pass_min))
        notes = [i.get("text") or "" for i in pending_of(r, SID_A) if i.get("kind") == "notice"]
        heard = [n for n in notes if "has now been read" in n]
        check(bool(heard) == said and ("has now been read" in out) == said,
              "stamped %d min after it was sent, learned %d min after: %s"
              % (stamped_min, pass_min, "the sender hears it" if said else
                 "recorded, said to nobody (%d notice)" % len(heard)))
    pmod = load_postman(w)
    pmod._heavy()
    at = datetime.datetime(2026, 10, 14, 9, 0).astimezone()
    known = {"pm-aaaaaaaaaaaa": {"state": "delivered", "date": "2026-10-07",
                                 "delivered": {"when": iso(datetime.datetime(2026, 10, 7, 8, 0).astimezone())}}}
    pmod.prune(known, dict(pmod.DEFAULTS), at)
    check("pm-aaaaaaaaaaaa" in known,
          "prune keeps a letter delivered 7 days ago while its own date is inside the horizon")
    pmod.prune(known, dict(pmod.DEFAULTS), datetime.datetime(2026, 10, 15, 0, 30).astimezone())
    check("pm-aaaaaaaaaaaa" not in known, "…and lets it go once a re-parse would retire it at once")


def case_omq2():
    start("BQ307-Q2", "MID-TURN CARRIES ONLY WHAT ASKS: no FYI, `read` or `none` letter rides a "
                      "PostToolBatch (the hub's ruling on Q2)")
    w = om_world("omq2")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    ask = letter(w, "NORTH/hub", "an ask mid-build", "answer it")
    quiet = [letter(w, "NORTH/hub", "a beat", "FYI"), letter(w, "NORTH/hub", "a record", "read"),
             letter(w, "NORTH/hub", "a note", "none — nothing owed")]
    pm(w, "--pass", "--no-pull")
    code, hout, _e = hook(w, SID_A, "PostToolBatch")
    ctx = context_of(hout)
    check(tok(w, ask) in ctx and not [q for q in quiet if tok(w, q) in ctx],
          "the PostToolBatch carries the ask and none of the three quiet letters")
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    ctx = context_of(hout)
    check(all(tok(w, q) in ctx for q in quiet), "…the next turn start carries all three")
    old = letter(w, "NORTH/hub", "a quiet letter an older pass queued", "read")
    write_json(w["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": tok(w, old), "kind": "letter", "line": old, "to": "NORTH/hub",
                           "fyi": False, "queued": iso(datetime.datetime.now().astimezone())}]})
    code, hout, _e = hook(w, SID_A, "PostToolBatch")
    check(hout == "" and tok(w, old) in om_tokens(pending_of(w, SID_A)),
          "an item queued before the `quiet` mark existed is judged by mail.py's own test: "
          "it waits for the turn start")


def case_omq7():
    start("BQ307-Q7", "A QUIET LETTER NEVER HOLDS A STOP OPEN: `read` and `none` letters alone "
                      "ride no Stop; with an ask pending they ride along (the hub's ruling on Q7)")
    w = om_world("omq7")
    plant_claim(w, "hub", "north", HOLDER, session=SID_A)
    claude_transcript(w, SID_A)
    quiet = [letter(w, "NORTH/hub", "a record", "read"),
             letter(w, "NORTH/hub", "a note", "none — nothing owed")]
    pm(w, "--pass", "--no-pull")
    code, hout, _e = hook(w, SID_A, "Stop")
    ctx = context_of(hout)
    check(not [q for q in quiet if tok(w, q) in ctx]
          and all(tok(w, q) in om_tokens(pending_of(w, SID_A)) for q in quiet),
          "two quiet letters alone: the Stop carries neither and both stay pending")
    ask = letter(w, "NORTH/hub", "an ask at the turn's end", "answer it")
    pm(w, "--pass", "--no-pull")
    code, hout, _e = hook(w, SID_A, "Stop")
    ctx = context_of(hout)
    check(tok(w, ask) in ctx and all(tok(w, q) in ctx for q in quiet),
          "with an ask pending the Stop carries it and the quiet letters ride along")


def case_omq4():
    start("BQ307-Q4", "--watch ENDS ONLY ON TODAY'S MAIL too: last week's ask is counted, never "
                      "printed alone (the hub's ruling on Q4)")
    w = om_world("omq4")
    qw_heartbeat(w)
    qw_window(w, QW_SID_D, QW_SONNET, title=QW_DESK)
    proc, handle, log = qw_watch_start(w, QW_SID_D, QW_DESK, "omq4-watch")
    try:
        qw_until(lambda: "watching" in qw_log(log), 15)
        old = letter(w, "NORTH/hub", "a three-day-old ask a pull brought in", "answer it",
                     date=om_day(-3))
        time.sleep(5)
        check("MAIL for" not in qw_log(log) and "earlier letter" not in qw_log(log),
              "the old ask prints nothing on its own — a printed line would wake the window")
        new = letter(w, "NORTH/hub", "today's ask", "answer it")
        got = qw_until(lambda: tok(w, new) in qw_log(log), 15)
        text = qw_log(log)
        check(got and tok(w, old) not in text, "today's ask is printed, the old one is not")
        check(text.count("1 earlier letter for NORTH/hub — read it with --read") == 1,
              "…with ONE count line beside it: %s" % [l for l in text.splitlines() if "earlier" in l])
        check(int((qw_ear(w) or {}).get("quiet") or 0) >= 1,
              "the ear counts the old ask among its quiet letters: %s" % (qw_ear(w) or {}).get("quiet"))
    finally:
        qw_watch_stop(proc, handle)


OM_CASES = (case_om1, case_om2, case_om3, case_om4, case_om5, case_om6, case_om7, case_om8,
            case_om9, case_om10, case_omh, case_omq2, case_omq4, case_omq7)


# ==========================================================================
# A MACHINE'S BROADCAST STAYS ON ITS MACHINE — AND ON ITS LOGIN
# (G1 · G2 · G3)
# ==========================================================================
# Worlds in the system temp folder under the runner's prefix (exo-prove-comms-<pid>-<name>),
# removed with the rest at the end of the run. Every name is the fixture's own.

B205_LOGIN_A = "wren@example.test"           # the login the alarm is about
B205_LOGIN_B = "kestrel@example.test"        # another login on the same machine
B205_ACCT_A = "a2050aaa-0000-4000-8000-0000000a2050"
B205_ACCT_B = "b2050bbb-0000-4000-8000-0000000b2050"
B205_SID_A = "a2050000-1111-2222-3333-aaaaaaaa2050"   # a window whose transcript's owner is A
B205_SID_B = "b2050000-1111-2222-3333-bbbbbbbb2050"   # …whose owner is B
B205_SID_C = "c2050000-1111-2222-3333-cccccccc2050"   # …whose transcript names no owner
B205_SID_D = "d2050000-1111-2222-3333-dddddddd2050"   # a live ear and no transcript at all


def b205_owner_row(sid, account):
    """The record the app writes on a transcript naming the account that owns it — the shape
    gate-usage.py's owner_row lays down, the one usage.py's session_login reads in a scan."""
    return {"type": "bridge-session", "sessionId": sid, "bridgeSessionId": "bridge-b205",
            "ownerAccountUuid": account, "ownerOrganizationUuid": "org-b205",
            "lastSequenceNum": 1}


def b205_world(name, with_usage=True):
    """A primed postman world whose hub carries usage.py beside the postman (unless asked
    not to) and a logins map naming both accounts — the way a window's own variables teach
    it (usage.py learn_login) — plus a terminal config naming B, so a road that fell back to
    it would read B for any window it could not see."""
    w = om_world(name)
    if with_usage:
        shutil.copy2(str(source_tool("usage.py")), str(w["hub"] / "tools" / "usage.py"))
    seen = iso(datetime.datetime.now().astimezone())
    write_json(w["hub"] / "logins-north.json",
               {B205_ACCT_A[:8]: {"login": B205_LOGIN_A, "seen": seen, "by": "window env"},
                B205_ACCT_B[:8]: {"login": B205_LOGIN_B, "seen": seen, "by": "window env"}})
    write_json(w["home"] / ".claude.json",
               {"oauthAccount": {"emailAddress": B205_LOGIN_B, "accountUuid": B205_ACCT_B}})
    began = datetime.datetime.now().astimezone() - datetime.timedelta(days=1)
    for sid, lane, acct in ((B205_SID_A, "Proj/Wren", B205_ACCT_A),
                            (B205_SID_B, "Proj/Kestrel", B205_ACCT_B),
                            (B205_SID_C, "Proj/Nobody", "")):
        plant_claim(w, lane, "north", "ACT — %s: a live lane" % lane, session=sid)
        path = om_transcript(w, sid, began)
        if acct:
            om_append(path, b205_owner_row(sid, acct))
    plant_ear(w, "NORTH/Proj-Dee", "ACT — Proj/Dee: an ear and no transcript", session=B205_SID_D)
    return w


def case_b205g1():
    start("BQ205-G1", "A LANE ON ONE MACHINE never takes another machine's broadcast or "
                      "its same-named lane's letters")
    w = om_world("b205g1")
    lines = [letter(w, "NORTH/all", "a broadcast for the north's lanes", "read it"),
             letter(w, "NORTH/Lane", "a letter for the north's Lane", "answer it"),
             letter(w, "SOUTH/all", "a broadcast for the south's lanes", "read it"),
             letter(w, "SOUTH/Lane", "a letter for the south's Lane", "answer it"),
             letter(w, "SOUTH/Other", "a letter for another south lane", "answer it")]
    n_all, n_lane, s_all, s_lane, s_other = lines
    mail = load_mail(w)
    every = inbox_lines(w)
    got = mail.addressed("SOUTH/Lane", every)
    check(got == [s_all, s_lane],
          "addressed(SOUTH/Lane) is its own letter and its own machine's broadcast, nothing "
          "else: %s" % [fields(l)[1] for l in got])
    check(n_all not in got and n_lane not in got,
          "…never NORTH/all, never NORTH/Lane (the same lane's name on the other machine)")
    got = mail.addressed("NORTH/Lane", every)
    check(got == [n_all, n_lane], "and the other way round: NORTH/Lane hears only the north's: %s"
          % [fields(l)[1] for l in got])
    left = mail.undelivered("SOUTH/Lane", w["hub"])
    check(left == [s_all, s_lane],
          "undelivered(SOUTH/Lane) — the waiter's floor road and --read's list — is the same "
          "two: %s" % [fields(l)[1] for l in left])
    code, out = mp(w, "--read", "SOUTH/Lane")
    check(code == 0 and "the south's Lane" in out and "the south's lanes" in out
          and "the north's" not in out and "another south lane" not in out,
          "mail.py --read SOUTH/Lane prints the south's two and neither north line: %s"
          % out.strip()[:120])


def case_b205g2():
    start("BQ205-G2", "AN ALARM ABOUT ONE LOGIN reaches that login's lanes and the unknown "
                      "ones — never a lane known to run under another")
    w = b205_world("b205g2")
    reset = "the week resets %s 10:00" % om_weekday(2)
    line = om_pause(w, om_day(), "Fable 92 percent", reset, login=B205_LOGIN_A)
    mail = load_mail(w)
    check(mail.usage_kind(line) == "alarm" and mail.alarm_login(line) == B205_LOGIN_A,
          "the fixture's line is an alarm that names login A (mail.py's own readers)")
    code, out = pm(w, "--pass", "--no-pull")
    kid = lambda sid: mail.child_token(tok(w, line), sid)
    check(kid(B205_SID_A) in om_tokens(pending_of(w, B205_SID_A)),
          "the lane whose transcript's owner is login A has its copy queued")
    check(not pending_of(w, B205_SID_B)
          and kid(B205_SID_B) not in (state_of(w).get("letters") or {}),
          "the lane whose transcript's owner is login B gets none, and no copy is made")
    check(kid(B205_SID_C) in om_tokens(pending_of(w, B205_SID_C)),
          "the lane whose transcript names no owner (login unknown) still gets its copy")
    check(kid(B205_SID_D) in om_tokens(pending_of(w, B205_SID_D)),
          "the lane with no transcript gets its copy: the terminal config's login (B) never "
          "stands in for a window the pass cannot see")
    skipped = [l for l in out.splitlines() if l.startswith("skipped")]
    check(skipped == ["skipped this pass: 1 other-login"],
          "the pass's summary counts it beside born-after, in the same words: %s" % skipped)
    e = om_entry(w, tok(w, line))
    check(e.get("other_login") == [B205_SID_B] and e.get("state") == "waiting"
          and sorted(e.get("children") or []) == sorted(kid(s) for s in
                                                        (B205_SID_A, B205_SID_C, B205_SID_D)),
          "the broadcast keeps the other login's session under other_login and three copies: "
          "%s" % e.get("other_login"))
    code, out = pm(w, "--pass", "--no-pull")
    check(not pending_of(w, B205_SID_B) and "other-login" not in out,
          "a second pass judges it no more and counts nothing new: %s"
          % [l for l in out.splitlines() if l.startswith("skipped")])
    code, sout = pm(w, "--status", "--no-pull")
    check("1 other-login" in sout,
          "--status names the skip the last pass that skipped anything made: %s"
          % [l for l in sout.splitlines() if l.startswith("skipped")])
    code, rout = mp(w, "--read", "NORTH/Proj-Wren", env=as_session(B205_SID_A))
    check("Fable 92 percent" in rout, "login A's lane reads the alarm with --read too")
    # no usage.py beside the postman: every login is unknown, and nothing is withheld
    n = b205_world("b205g2n", with_usage=False)
    nline = om_pause(n, om_day(), "Fable 92 percent", reset, login=B205_LOGIN_A)
    code, nout = pm(n, "--pass", "--no-pull")
    nmail = load_mail(n)
    check(nmail.child_token(tok(n, nline), B205_SID_B) in om_tokens(pending_of(n, B205_SID_B))
          and "other-login" not in nout,
          "the same world with no usage.py to read logins: login B's lane gets its copy — the "
          "skip above comes from the login read, never from a guess")


def case_b205g3():
    start("BQ205-G3", "A BROADCAST THAT IS NOT AN ALARM ignores logins: every live lane gets "
                      "its copy")
    w = b205_world("b205g3")
    line = letter(w, "NORTH/all", "the ritual changed — %s's lanes and everyone's" % B205_LOGIN_A,
                  "run your ritual again")
    mail = load_mail(w)
    check(mail.usage_kind(line) == "" and mail.alarm_login(line) == B205_LOGIN_A,
          "the fixture's line names login A in its text but is no alarm")
    code, out = pm(w, "--pass", "--no-pull")
    for sid, who in ((B205_SID_A, "login A's"), (B205_SID_B, "login B's"),
                     (B205_SID_C, "the unknown login's"), (B205_SID_D, "the no-transcript")):
        check(mail.child_token(tok(w, line), sid) in om_tokens(pending_of(w, sid)),
              "%s lane has its copy queued" % who)
    e = om_entry(w, tok(w, line))
    check(not e.get("other_login") and "other-login" not in out,
          "nothing is held back and nothing is counted: %s"
          % [l for l in out.splitlines() if l.startswith("skipped")])


B205_CASES = (case_b205g1, case_b205g2, case_b205g3)


# ==========================================================================
# A LETTER ABOUT A FAILURE DIES WITH THE FAILURE
# (C1 · C2 · C3 · C4 · C5)
# ==========================================================================
# Worlds in the system temp folder under the runner's prefix (exo-prove-comms-<pid>-<name>),
# removed with the rest at the end of the run. Every name is the fixture's own.

B337_SID_F = "f3370000-1111-2222-3333-ffffffff0337"     # a Fable window whose waiter listens
B337_LOGIN_A = "wren@example.test"                     # the login the alarm is about
B337_LOGIN_B = "kestrel@example.test"                  # the login the app is signed in as
B337_ACCT_A = "a3370aaa-0000-4000-8000-0000000a0337"
B337_ACCT_B = "b3370bbb-0000-4000-8000-0000000b0337"
B337_RESOLVED = " · resolved: %s by the push that landed"


def b337_failed(w, text="PUSH FAILED since 08:58 (3 tries) on north: fatal: unable to access"):
    """A failed-push letter in sync.py's own grammar, written into the world's INBOX."""
    line = ("- %s · to: NORTH/hub · exocortex-sync · %s · run: python3 sync.py push"
            % (om_day(), text))
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return line


def b337_resolve(w, line, when=None):
    """sync.py's own stamp, IN PLACE: the tail a push that landed writes."""
    when = (when or datetime.datetime.now().astimezone()).replace(second=0, microsecond=0)
    stamp = B337_RESOLVED % when.isoformat(timespec="minutes")
    path = w["hub"] / "INBOX.md"
    text = io.open(str(path), encoding="utf-8").read()
    assert text.count(line + "\n") == 1
    write(path, text.replace(line + "\n", line + stamp + "\n"))
    return line + stamp, when


def b337_alive(w, sid):
    write(w["post"] / "waiters" / ("%s.alive" % sid), iso(datetime.datetime.now().astimezone()))


def b337_sends(w):
    return state_of(w).get("sends") or {}


def b337_login_world(name, app_acct=None):
    """A primed postman world with usage.py beside the postman, a logins map naming both
    accounts, and — when `app_acct` is given — the desktop app's own config signed in as
    that account (both OS folders), so usage.py's app road reads it."""
    w = om_world(name)
    shutil.copy2(str(source_tool("usage.py")), str(w["hub"] / "tools" / "usage.py"))
    seen = iso(datetime.datetime.now().astimezone())
    write_json(w["hub"] / "logins-north.json",
               {B337_ACCT_A[:8]: {"login": B337_LOGIN_A, "seen": seen, "by": "window env"},
                B337_ACCT_B[:8]: {"login": B337_LOGIN_B, "seen": seen, "by": "window env"}})
    if app_acct:
        b337_app_login(w, app_acct)
    return w


def b337_app_login(w, acct):
    for folder in (w["home"] / "Library" / "Application Support" / "Claude",
                   w["home"] / "AppData" / "Roaming" / "Claude"):
        if acct:
            write_json(folder / "config.json", {"lastKnownAccountUuid": acct})
        else:
            try:
                os.unlink(str(folder / "config.json"))
            except OSError:
                pass


def b337_roots(w):
    return {"orchestrator": str(w["hub"]), "home": str(w["home"]),
            "claude": str(w["home"] / ".claude"), "projects": str(w["projects"]),
            "post": str(w["post"])}


def b337_meter(w, login, pct, read_at=None):
    now = datetime.datetime.now().astimezone()
    write_json(w["hub"] / ("usage-north-claude-%s.json" % login.replace("@", "-at-")),
               {"vendor": "claude", "machine": "north", "login": login, "login_source": "--login",
                "read_at": iso(read_at or now), "source": "gate-comms BQ-337",
                "meter": "readable", "spend": None,
                "windows": [{"label": "Weekly · Fable", "percent": pct, "kind": "week-model",
                             "model": "fable", "resets_at": iso(now + datetime.timedelta(days=3))}]})


def b337_no_window_env():
    return {"CLAUDE_CODE_ACCOUNT_UUID": None, "CLAUDE_CODE_USER_EMAIL": None}


def case_b337c1():
    start("BQ337-C1", "A RESOLVED LETTER IS CLOSED: --read hides it and says so, it never ends "
                      "a wait, the pass expires it and takes its order back")
    w = fd_world("b337c1", base_dir=om_base("b337c1"))
    line = b337_failed(w)
    mail = load_mail(w)
    t = mail.token(line)
    pmn(w, "--pass", "--no-pull")
    orders = fd_orders(w, SID_B)
    check(t in om_tokens(pending_of(w, SID_A)) and len(orders) == 1
          and orders[0].get("tokens") == [t],
          "before the stamp: the letter waits for the attended hub and ONE send order holds it "
          "alone: %s" % [o.get("tokens") for o in orders])
    key = orders[0].get("token") if orders else ""
    check(orders and orders[0].get("wake") is False,
          "…and the order is queued `wake: false` (C3): %s" % (orders[0] if orders else {}))
    stamped, when = b337_resolve(w, line)
    check(mail.token(stamped) == t and mail.is_resolved(stamped) and mail.is_quiet(stamped)
          and mail.fields(stamped)[-1] == "run: python3 sync.py push",
          "mail.py: the same token, resolved, quiet, and the tail never read as the action")
    code, rout = mp(w, "--read", "NORTH/hub", env=as_session(SID_A))
    check("PUSH FAILED" not in rout and t not in rout,
          "--read does not print it: %s" % rout.strip()[:120])
    check("1 letter(s) about failed pushes closed by a later push — not shown" in rout,
          "…and says the one hidden line: %s" % rout.strip()[:160])
    code, aout = mp(w, "--read", "NORTH/hub", "--all", env=as_session(SID_A))
    check(t in aout and "closed by a later push" in aout and "MAIL: %s" % stamped not in aout,
          "--all shows it with why, never as MAIL: %s" % aout.strip()[:160])
    item = {"token": t, "kind": "letter", "line": stamped, "to": "NORTH/hub", "fyi": False}
    check(mail.wants_answer([item]) == [], "wants_answer leaves a resolved letter out")
    # the waiter, its own process: the resolved letter alone never ends it; beside a real ask
    # it ends, and only the ask is carried
    v = fd_world("b337c1w", base_dir=om_base("b337c1w"))
    vline = b337_failed(v)
    vstamped, _w = b337_resolve(v, vline)
    vt = mail.token(vline)
    qw_heartbeat(v)
    write_json(v["post"] / "pending" / ("%s.json" % SID_A),
               {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                "items": [{"token": vt, "kind": "letter", "line": vstamped, "to": "NORTH/hub",
                           "fyi": False, "queued": iso(datetime.datetime.now().astimezone())}]})
    proc = waiter(v, "NORTH/hub", FD_TITLE, env=as_session(SID_A))
    try:
        time.sleep(6)
        check(proc.poll() is None, "a waiter holding only the resolved letter does not end")
        ask = letter(v, "NORTH/hub", "a real ask beside it")
        at = mail.token(ask)
        items = json.loads(io.open(str(v["post"] / "pending" / ("%s.json" % SID_A)),
                                   encoding="utf-8").read())["items"]
        items.append({"token": at, "kind": "letter", "line": ask, "to": "NORTH/hub",
                      "fyi": False, "queued": iso(datetime.datetime.now().astimezone())})
        write_json(v["post"] / "pending" / ("%s.json" % SID_A),
                   {"session": SID_A, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": items})
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(at in out and vt not in out,
              "the ask ends it; the waiter's carried list leaves the resolved one out: %s"
              % [l for l in out.splitlines() if "ended" in l])
    finally:
        if proc.poll() is None:
            proc.kill()
    code, out = pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    e = fd_entry(w, t)
    check(e.get("state") == "expired"
          and e.get("why") == "resolved by the push that landed at %s" % when.strftime("%H:%M"),
          "the pass reads it expired, `resolved by the push that landed at HH:MM`: %s / %s"
          % (e.get("state"), e.get("why")))
    check("1 resolved by stamp" in out,
          "…counts `resolved by stamp`: %s" % [l for l in out.splitlines() if l.startswith("skipped")])
    check(t not in om_tokens(pending_of(w, SID_A)),
          "…takes it out of the hub's own pending file")
    check(not fd_orders(w, SID_B) and (b337_sends(w).get(key) or {}).get("state") == "spent",
          "…and takes back the send order that held only it: %s"
          % (b337_sends(w).get(key) or {}).get("state"))


def case_b337c2():
    start("BQ337-C2", "AN ALARM ABOUT ANOTHER LOGIN'S METER, OR ONE THE METER HAS ANSWERED, "
                      "does not ring")
    reset = "the week resets %s 10:00" % om_weekday(2)
    w = b337_login_world("b337c2", app_acct=B337_ACCT_B)
    line = om_pause(w, om_day(), "Fable 94 percent", reset, login=B337_LOGIN_A)
    mail = load_mail(w)
    t = mail.token(line)
    roots = b337_roots(w)
    saved = dict((k, os.environ.get(k)) for k in ("CLAUDE_CODE_ACCOUNT_UUID", "CLAUDE_CODE_USER_EMAIL"))
    for k in saved:
        os.environ.pop(k, None)
    try:
        got = mail.quiet_alarms(inbox_lines(w), hub=w["hub"], roots=roots)
        check((got.get(t) or ("",))[0] == "other-login"
              and B337_LOGIN_A in got[t][1] and B337_LOGIN_B in got[t][1],
              "the app is signed in as B, the alarm is about A: `other-login`, naming both: %s"
              % (got.get(t),))
        check(t not in mail.quiet_alarms(inbox_lines(w)),
              "…and with nothing passed quiet_alarms is exactly what it was")
        code, rout = mp(w, "--read", "NORTH/hub", env=b337_no_window_env())
        check("USAGE PAUSE" not in rout, "--read for NORTH/hub hides it: %s" % rout.strip()[:100])
        code, out = pm(w, "--pass", "--no-pull", env=b337_no_window_env())
        e = om_entry(w, t)
        check(e.get("state") == "expired" and "another login's meter" in (e.get("why") or "")
              and "1 other-login" in out,
              "the pass expires it with the why, and counts it: %s / %s"
              % (e.get("why"), [l for l in out.splitlines() if l.startswith("skipped")]))
        n = b337_login_world("b337c2n")
        write_json(n["home"] / ".claude.json",            # the terminal's login: never the app's
                   {"oauthAccount": {"emailAddress": B337_LOGIN_B, "accountUuid": B337_ACCT_B}})
        nline = om_pause(n, om_day(), "Fable 94 percent", reset, login=B337_LOGIN_A)
        nmail = load_mail(n)
        check(nmail.token(nline) not in nmail.quiet_alarms(inbox_lines(n), hub=n["hub"],
                                                           roots=b337_roots(n)),
              "no app login readable (the terminal's config is never the app's): no verdict")
        code, rout = mp(n, "--read", "NORTH/hub", env=b337_no_window_env())
        check("Fable 94 percent" in rout, "…and --read prints it, as today: %s" % rout.strip()[:80])
        a = b337_login_world("b337c2a", app_acct=B337_ACCT_A)
        aline = om_pause(a, om_day(), "Fable 94 percent", reset, login=B337_LOGIN_A)
        amail = load_mail(a)
        at = amail.token(aline)
        b337_meter(a, B337_LOGIN_A, 40)
        got = amail.quiet_alarms(inbox_lines(a), hub=a["hub"], roots=b337_roots(a))
        check((got.get(at) or ("",))[0] == "answered"
              and got[at][1] == "the meter it asked about now reads 40 — under the pause line",
              "the alarm's own login (the app's too) now reads Fable 40: `answered`: %s"
              % (got.get(at),))
        b337_meter(a, B337_LOGIN_A, 95)
        got = amail.quiet_alarms(inbox_lines(a), hub=a["hub"], roots=b337_roots(a))
        check(at not in got, "…with the meter at 95: no verdict, it still rings: %s" % (got.get(at),))
        b337_meter(a, B337_LOGIN_A, 40, read_at=datetime.datetime.now().astimezone()
                   - datetime.timedelta(days=2))
        got = amail.quiet_alarms(inbox_lines(a), hub=a["hub"], roots=b337_roots(a))
        check(at not in got, "…and a reading older than the alarm answers nothing")
        b337_meter(a, B337_LOGIN_B, 10)
        try:
            os.unlink(str(a["hub"] / ("usage-north-claude-%s.json" % B337_LOGIN_A.replace("@", "-at-"))))
        except OSError:
            pass
        got = amail.quiet_alarms(inbox_lines(a), hub=a["hub"], roots=b337_roots(a))
        check(at not in got, "no meter file for the alarm's own login (another login's never "
                             "stands in): no verdict")
    finally:
        for k, val in saved.items():
            if val is not None:
                os.environ[k] = val


def case_b337c3():
    start("BQ337-C3", "A FLAGSHIP WINDOW IS NEVER THE CARRIER: the Sonnet window carries, and "
                      "with only a Fable window there is no order")
    w = fd_world("b337c3", base_dir=om_base("b337c3"))
    qw_window(w, B337_SID_F, QW_FABLE)
    b337_alive(w, B337_SID_F)
    line = b337_failed(w)
    mail = load_mail(w)
    t = mail.token(line)
    code, out = pmn(w, "--pass", "--no-pull")
    rec = [r for r in b337_sends(w).values() if t in (r.get("tokens") or [])]
    check(len(fd_orders(w, SID_B)) == 1 and not fd_orders(w, B337_SID_F),
          "the Fable window's waiter is listening, yet the order goes to the SONNET window")
    check(rec and rec[0].get("carrier") == SID_B
          and rec[0].get("carrier_how") == "the Claude window that wrote most recently",
          "…by the most-recent tier, the Fable one passed over: %s"
          % ({k: rec[0].get(k) for k in ("carrier", "carrier_how")} if rec else {}))
    o = fd_world("b337c3o", base_dir=om_base("b337c3o"))
    qw_window(o, SID_B, QW_FABLE)                     # the only other live window: Fable
    qw_window(o, B337_SID_F, QW_FABLE)
    b337_alive(o, B337_SID_F)
    oline = b337_failed(o)
    ot = mail.token(oline)
    code, out = pmn(o, "--pass", "--no-pull")
    e = fd_entry(o, ot)
    check(not fd_orders(o, SID_B) and not fd_orders(o, B337_SID_F) and not fd_orders(o, SID_A),
          "with only Fable windows live: no order in any pending file")
    check((e.get("attended") or {}).get("road") == "announce"
          and ot in om_tokens(pending_of(o, SID_A))
          and [r["argv"][-1] for r in raises(o)] == ["GUI review: 1 letter waiting — it shows at its next turn"],
          "…the letter takes the idle road: queued, ONE notice: %s" % e.get("attended"))
    check("no carrier — every live window is on a flagship model" in out
          and (e.get("attended") or {}).get("why") == "no carrier — every live window is on a flagship model",
          "…and the pass says why: %s" % [l for l in out.splitlines() if "carrier" in l])


def case_b337c4():
    start("BQ337-C4", "AN ORDER NEVER ENDS A WAIT: it rides the carrier's next turn")
    w = fd_world("b337c4", base_dir=om_base("b337c4"))
    qw_heartbeat(w)
    line = b337_failed(w)
    mail = load_mail(w)
    pmn(w, "--pass", "--no-pull")
    orders = fd_orders(w, SID_B)
    check(len(orders) == 1, "an order waits in the carrier's pending file")
    key = orders[0].get("token") if orders else ""
    proc = waiter(w, "NORTH/lane-x", "ACT — Proj/Desk: the desk", env=as_session(SID_B))
    try:
        time.sleep(6)
        check(proc.poll() is None, "the carrier's waiter does not end on the order")
        old = dict(orders[0]) if orders else {}
        old.pop("wake", None)                         # an order an older postman queued
        old["token"] = "sd-0337aaaaaaaa"
        items = json.loads(io.open(str(w["post"] / "pending" / ("%s.json" % SID_B)),
                                   encoding="utf-8").read())["items"] + [old]
        write_json(w["post"] / "pending" / ("%s.json" % SID_B),
                   {"session": SID_B, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": items})
        time.sleep(6)
        check(proc.poll() is None, "…nor on an order with no `wake` key (its kind is enough)")
        ask = letter(w, "NORTH/lane-x", "a real ask for the desk")
        items.append({"token": mail.token(ask), "kind": "letter", "line": ask,
                      "to": "NORTH/lane-x", "fyi": False,
                      "queued": iso(datetime.datetime.now().astimezone())})
        write_json(w["post"] / "pending" / ("%s.json" % SID_B),
                   {"session": SID_B, "updated": iso(datetime.datetime.now().astimezone()),
                    "items": items})
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=10)
        check(mail.token(ask) in out and key not in out and "SendMessage" not in out,
              "an ask ends it, and the order is not handed with it: %s"
              % [l for l in out.splitlines() if "ended" in l])
    finally:
        if proc.poll() is None:
            proc.kill()
    check(key in om_tokens(pending_of(w, SID_B)), "the order still waits in the carrier's file")
    code, hout, _e = hook(w, SID_B, "PostToolBatch")
    ctx = context_of(hout)
    check("SendMessage" in ctx and key in ctx,
          "…and the carrier's next turn (its PostToolBatch hook) carries it")


def case_b337c5():
    start("BQ337-C5", "NO ORDER FOR A LETTER THE WINDOW HAS SEEN: handed by its own road, or "
                      "delivered")
    w = fd_world("b337c5", holder_age_s=2400, base_dir=om_base("b337c5"))
    line = b337_failed(w)
    mail = load_mail(w)
    t = mail.token(line)
    pmn(w, "--pass", "--no-pull")
    check(not fd_orders(w, SID_B) and t in om_tokens(pending_of(w, SID_A)),
          "an idle hub: queued, no order")
    code, hout, _e = hook(w, SID_A, "UserPromptSubmit")
    check(t in context_of(hout), "the hub's own turn start hands it (a receipt, as the waiter's "
                                 "road leaves one)")
    age_file(w["tpath"], 120)                         # someone is looking at it now
    code, out = pmn(w, "--pass", "--no-pull", "--now", later(minutes=1))
    e = fd_entry(w, t)
    check(e.get("state") == "waiting" and not fd_orders(w, SID_B)
          and not [r for r in b337_sends(w).values() if t in (r.get("tokens") or [])],
          "attended now, the letter not yet seen in its transcript — but handed: NO order is "
          "minted: %s" % e.get("attended"))
    check((e.get("attended") or {}).get("road") == "next turn",
          "…its road says it was handed: %s" % e.get("attended"))
    d = fd_world("b337c5d", holder_age_s=2400, base_dir=om_base("b337c5d"))
    dline = b337_failed(d)
    dt = mail.token(dline)
    pmn(d, "--pass", "--no-pull")
    claude_transcript(d, SID_A, [claude_hook_context(SID_A, letter_context(d, dline, dt))])
    age_file(d["tpath"], 120)
    pmn(d, "--pass", "--no-pull", "--now", later(minutes=1))
    check(fd_entry(d, dt).get("state") == "delivered" and not fd_orders(d, SID_B),
          "a letter SEEN in the window's transcript is delivered, and no order is minted")


B337_CASES = (case_b337c1, case_b337c2, case_b337c3, case_b337c4, case_b337c5)


# ==========================================================================
# THE DIAL PLATE IS AN ORDER THE POSTMAN CARRIES — 
# 
# ==========================================================================
# Every world here is the gate's own, in the system temp folder under the runner's own prefix
# (exo-prove-comms-286-<pid>-<name>), removed with the rest at the end of the run. Each world's
# tools/ holds the postman and spool.py under test — source_tool(): beside this gate first, so a
# gate run from a stage tests the STAGE's bytes (DL1 proves it by sha) — and the judge's own
# neighbours, including effort.py's required hook_say.py import. The pass runs the judge
# (spool.py --dials --json --plates-only) as a real child.

DL_TOOLS = ("spool.py", "effort.py", "hook_say.py", "usage.py", "collect-openers.py", "opener_carriers.py",
            "grok_sessions.py", "exo_common.py")
DL_SID = "dddddddd-1111-2222-3333-dddddddddddd"        # the plated window
DL_HAND = SID_B                                        # an attended Claude window: the hand
DL_RUN = "eeeeeeee-1111-2222-3333-eeeeeeeeeeee"        # a routine's run
DL_TITLE = "ACT — Exocortex/Dials: the plated window"
DL_HAND_TITLE = "ACT — Exocortex/Desk: the hand"
DL_LOCAL, DL_HAND_LOCAL, DL_RUN_LOCAL = "local_dlplate", "local_dlhand", "local_dlrun"
DL_FABLE, DL_SONNET, DL_HAIKU = "claude-fable-5-1", "claude-sonnet-5-5", "claude-haiku-5-5"
DL_DOWN_WHY = "the mechanical rest"
DL_SAID = "dial set: SONNET · HIGH · %s · your menu overrides" % DL_DOWN_WHY
DL_RUBRIC = {
    "version": 1, "about": "gate-comms DL's rubric — the fixture registry's minds", "user_name": "",
    "dials": {"anthropic": {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "xhigh": "EXTRA",
                            "max": "MAX"}, "openai": {"xhigh": "EXTRA"}},
    "flag_only_levels": ["max"],
    "kinds": [
        {"id": "judgment", "name": "JUDGMENT", "ask": "decide?", "minds": ["FABLE", "NOBODY"],
         "never": ["HAIKU"], "level": "EXTRA", "flag": "plate", "source": "the gate"},
        {"id": "mechanical", "name": "MECHANICAL", "ask": "ruled?", "minds": ["SONNET", "HAIKU"],
         "never": [], "level": "HIGH", "flag": "plate", "source": "the gate"}],
    "thresholds": {}, "switches": {}}


def dl_base(name):
    return Path(tempfile.gettempdir()) / ("exo-prove-comms-286-%d-%s" % (os.getpid(), name))


def dl_plate(span, mind, level, why):
    arrow = "**⇧ NEXT TURN**" if span == "TURN" else "**⇩ NEXT STRETCH**"
    return "Done.\n\n---\n%s\n`NORTH · %s · %s` — %s\n\n---" % (arrow, mind, level, why)


DL_DOWN = dl_plate("STRETCH", "SONNET", "HIGH", DL_DOWN_WHY)


def dl_iso_z(age_s):
    return om_iso_z(datetime.datetime.now().astimezone() - datetime.timedelta(seconds=age_s))


def dl_reply(w, sid, uuid, text, model, effort, age_s, path=None):
    """One turn in a Claude transcript's REAL shape — a prompt, then the reply with its model,
    its top-level `effort` and its text — appended, the file's mtime set `age_s` back."""
    path = path or (w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % sid))
    path.parent.mkdir(parents=True, exist_ok=True)
    om_append(path, {"type": "user", "sessionId": sid, "uuid": uuid + "-u", "isSidechain": False,
                     "timestamp": dl_iso_z(age_s + 5),
                     "message": {"role": "user", "content": "go on"}})
    om_append(path, {"type": "assistant", "sessionId": sid, "uuid": uuid, "isSidechain": False,
                     "effort": effort, "timestamp": dl_iso_z(age_s),
                     "message": {"role": "assistant", "model": model,
                                 "content": [{"type": "text", "text": text}]}})
    age_file(path, age_s)
    return path


def dl_store(w, sid, local, title, model, effort, scheduled=False):
    """The desktop app's record for a window, in its REAL shape (model AND effort, as the store
    carries them), under both homes the reader knows — macOS's and Windows' %APPDATA%."""
    now_ms = int(time.time() * 1000)
    rec = {"sessionId": local, "cliSessionId": sid, "title": title, "isArchived": False,
           "lastActivityAt": now_ms - 60000, "lastFocusedAt": now_ms - 3600000, "model": model,
           "effort": effort, "cwd": str(w["hub"])}
    if scheduled:
        rec["scheduledTaskId"] = "gate-routine"
    for base in (w["home"] / "Library" / "Application Support",
                 w["home"] / "AppData" / "Roaming"):
        write_json(base / "Claude" / "claude-code-sessions" / "acct" / "org" / ("%s.json" % local),
                   rec)


def dl_meter(w, fable_pct=10, all_pct=20, minutes_ago=1):
    """The login's meter in the shape usage.py files it — the flagship's week, the all-models
    week, and the day's tally the judge reads model ids from — and the login it belongs to."""
    now = datetime.datetime.now().astimezone()
    write_json(w["home"] / ".claude.json", {"oauthAccount": {"emailAddress": "wren@example.test",
                                                             "accountUuid": "a1b2c3d4-dl286"}})
    # usage.py session_login(): CLI config alone cannot identify a desktop window.
    for base in (w["home"] / "Library" / "Application Support",
                 w["home"] / "AppData" / "Roaming"):
        write_json(base / "Claude" / "config.json", {"lastKnownAccountUuid": "a1b2c3d4-dl286"})
    write_json(w["hub"] / "usage-north-claude-wren-at-example.test.json",
               {"vendor": "claude", "machine": "north", "login": "wren@example.test",
                "login_source": "--login", "source": "gate-comms DL", "meter": "readable",
                "read_at": iso(now - datetime.timedelta(minutes=minutes_ago)), "spend": None,
                "windows": [{"label": "Weekly · all models", "percent": all_pct,
                             "kind": "week", "model": "",
                             "resets_at": iso(now + datetime.timedelta(days=2))},
                            {"label": "Weekly · Fable", "percent": fable_pct,
                             "kind": "week-model", "model": "fable",
                             "resets_at": iso(now + datetime.timedelta(days=2))}],
                "accounting": {"last_24h": {"calls_by_model": {DL_SONNET: 30, DL_FABLE: 10,
                                                               DL_HAIKU: 3}}}})


def dl_live(w, rows):
    write_json(w["hub"] / "live-sessions-north.json",
               {"machine": "north", "when": iso(datetime.datetime.now().astimezone()),
                "live_minutes": 10, "sessions": rows})


def dl_row(sid, title, model, path, kind="claude"):
    return {"id": sid, "kind": kind, "model": model, "title": title, "transcript": str(path),
            "cwd": "", "dir": "-gate-hub", "minutes_ago": 1.0}


def dl_world(name, plate=DL_DOWN, hand=True, model=DL_FABLE, effort="xhigh", age_s=180,
             fable_pct=10):
    """A primed postman world with the judge beside it: the PLATED window (its last reply ends
    with `plate`, aged `age_s`, its app record `local_dlplate`) and, unless `hand` is False, one
    other attended Claude window — the hand — that wrote two minutes ago."""
    w = pworld(name, base_dir=dl_base(name))
    for tool_name in DL_TOOLS:
        src = source_tool(tool_name)
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / "tools" / tool_name))
    write_json(w["hub"] / "effort-rubric.json", DL_RUBRIC)
    w["env"]["APPDATA"] = str(w["home"] / "AppData" / "Roaming")
    dl_meter(w, fable_pct=fable_pct)
    w["tp"] = dl_reply(w, DL_SID, "dl-r1", plate, model, effort, age_s)
    dl_store(w, DL_SID, DL_LOCAL, DL_TITLE, model, effort)
    rows = [dl_row(DL_SID, DL_TITLE, model, w["tp"])]
    if hand:
        w["hp"] = dl_reply(w, DL_HAND, "dl-h1", "Working on my own lane.", DL_SONNET, "medium", 120)
        dl_store(w, DL_HAND, DL_HAND_LOCAL, DL_HAND_TITLE, DL_SONNET, "medium")
        plant_claim(w, "Exocortex/Desk", "north", DL_HAND_TITLE, session=DL_HAND)
        rows.append(dl_row(DL_HAND, DL_HAND_TITLE, DL_SONNET, w["hp"]))
    w["rows"] = rows
    dl_live(w, rows)
    return w


def dl_pass(w, *extra):
    """(exit, printed, counters) of one pass, with the notifier's seam and the run's counters."""
    counters = w["base"] / "dl-counters.json"
    try:
        os.unlink(str(counters))
    except OSError:
        pass
    code, out = pmn(w, "--pass", "--no-pull", "--counters", str(counters), *extra)
    try:
        c = json.loads(io.open(str(counters), encoding="utf-8").read())
    except (OSError, ValueError):
        c = {}
    return code, out, c


def dl_items(w, sid, kind):
    return [i for i in pending_of(w, sid) if i.get("kind") == kind]


def dl_all_items(w):
    out = []
    for f in sorted((w["post"] / "pending").glob("*.json")):
        for i in json.loads(io.open(str(f), encoding="utf-8").read()).get("items") or []:
            out.append((f.stem, i))
    return out


def dl_dials(w):
    return state_of(w).get("dials") or {}


def dl_posted(w):
    path = w["hub"] / "post-north.json"
    if not path.is_file():
        return {}
    return json.loads(io.open(str(path), encoding="utf-8").read()).get("dials") or {}


def dl_lines(out):
    return [l for l in out.splitlines() if l.startswith("dial: ")]


def dl_sha(path):
    import hashlib as _hl
    return _hl.sha256(Path(path).read_bytes()).hexdigest()


def dl_backdate(w, uuid, field, minutes):
    """The world moves, never the clock: one timestamp of a plate's record set `minutes` back
    in the world's own state — how an order is made ten minutes old at any hour, midnight
    included, with no --now in sight."""
    body = state_of(w)
    rec = (body.get("dials") or {}).get(uuid) or {}
    rec[field] = iso(datetime.datetime.now().astimezone() - datetime.timedelta(minutes=minutes))
    write_state(w, body)


def dl_stats(w, sid, event, env_extra):
    """stats_for() with the window's OWN environment added (its app id): how many os.stat calls
    the hook makes, and what it printed."""
    payload = {"session_id": sid, "hook_event_name": event, "cwd": str(w["hub"]),
               "transcript_path": ""}
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in list(w["env"].items()) + list(env_extra.items()):
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    p = subprocess.run([PY, str(w["base"] / "statcount.py"),
                        str(w["hub"] / "tools" / "postman.py"), str(w["post"])],
                       input=json.dumps(payload), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=60)
    m = re.search(r"STATS=(\d+)", p.stderr or "")
    return (int(m.group(1)) if m else None), p.stdout


def case_dl1():
    start("DL1", "A ⇩ PLATE IN A QUIET WINDOW: one dial order on the one other attended window, "
                 "aimed at the plated window's app id")
    w = dl_world("dl1")
    staged = source_tool("postman.py").parent
    check(dl_sha(w["hub"] / "tools" / "postman.py") == dl_sha(source_tool("postman.py"))
          and dl_sha(w["hub"] / "tools" / "spool.py") == dl_sha(source_tool("spool.py")),
          "the world runs the bytes under test — postman.py and spool.py from %s (sha-equal)"
          % staged)
    code, out, cnt = dl_pass(w)
    orders = dl_items(w, DL_HAND, "dial")
    check(code == 0 and len(orders) == 1, "exactly one dial order, in the hand's own pending "
                                          "file: %d (exit %d)" % (len(orders), code))
    o = orders[0] if orders else {}
    check(o.get("target") == DL_LOCAL and o.get("cli") == DL_SID
          and o.get("model_id") == DL_SONNET and o.get("effort") == "high"
          and o.get("plate_uuid") == "dl-r1" and o.get("fyi") is False
          and str(o.get("token") or "").startswith("dl-"),
          "aimed at the app's own id, the asked model id and effort, the plate's uuid: %s"
          % dict((k, o.get(k)) for k in ("target", "model_id", "effort", "plate_uuid", "token")))
    check(cnt.get("judge_runs") == 1, "the judge ran once as a child: %s" % cnt.get("judge_runs"))
    check(not pending_of(w, DL_SID), "nothing is queued for the plated window itself — no wake, "
                                     "no message: %s" % pending_of(w, DL_SID))
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "ordered" and d.get("carrier") == DL_HAND and d.get("orders") == 1,
          "the post state: ordered, the hand, one order — keyed by the plate's uuid: %s"
          % dict((k, d.get(k)) for k in ("state", "carrier", "orders")))
    row = dl_posted(w).get("dl-r1") or {}
    check(row.get("state") == "ordered" and row.get("verdict") == "SET"
          and row.get("mind") == "SONNET" and row.get("effort") == "HIGH"
          and row.get("session") == DL_SID,
          "post-north.json carries it under `dials`: %s" % row)
    check(dl_lines(out) == ["dial: «%s» → SONNET · HIGH — ordered through «%s» (the Claude "
                            "window that wrote most recently)" % (DL_TITLE, DL_HAND_TITLE)],
          "the pass says it in one line: %s" % dl_lines(out))
    code, hout, _e = hook(w, DL_HAND, "PostToolBatch")
    ctx = context_of(hout)
    check(all(word in ctx for word in ("get_session", "set_session_model", "set_session_effort",
                                       "«%s»" % DL_TITLE, '"%s"' % DL_LOCAL, '"%s"' % DL_SONNET,
                                       'effort "high"', "isRunning", DL_DOWN_WHY,
                                       o.get("token") or "?")),
          "the hand's very next hook (mid-turn) prints the order: the three tools, the window's "
          "title, its app id, the model id and the effort: %s" % ctx[:160])
    check(not raises(w), "no desktop notice for a dial: %s" % raises(w))


def case_dl2():
    start("DL2", "A ⇧ TO THE FLAGSHIP AT 85 PERCENT: no order; kept PAST WARN; the plate stands")
    w = dl_world("dl2", plate=dl_plate("TURN", "FABLE", "EXTRA", "rule the merge order"),
                 model=DL_SONNET, effort="high", fable_pct=85)
    code, out, cnt = dl_pass(w)
    check(not dl_all_items(w), "no item in any pending file: %s" % dl_all_items(w))
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "kept" and str(d.get("why") or "").startswith("PAST WARN"),
          "the plate is recorded kept, PAST WARN: %s" % d.get("why"))
    lines = dl_lines(out)
    check(len(lines) == 1 and "asks FABLE · EXTRA — kept: PAST WARN" in lines[0]
          and lines[0].endswith("the plate stands as the question"),
          "the pass line says the plate stands: %s" % lines)
    code, out2, cnt2 = dl_pass(w)
    check(not dl_lines(out2) and cnt2.get("judge_runs") == 0,
          "…once: the next pass says nothing and asks no judge (%s)" % cnt2.get("judge_runs"))


def case_dl3():
    start("DL3", "ONE PLATE, ONE ORDER: the next pass adds nothing; a NEW reply's plate is a new "
                 "order")
    w = dl_world("dl3")
    dl_pass(w)
    first = dl_items(w, DL_HAND, "dial")
    code, out, cnt = dl_pass(w)
    again = dl_items(w, DL_HAND, "dial")
    check(len(first) == 1 and [i.get("token") for i in again] == [i.get("token") for i in first],
          "the same transcript, the next pass: still the one order (%d → %d)"
          % (len(first), len(again)))
    check(cnt.get("judge_runs") == 0 and cnt.get("dial_reads") == 0 and not dl_lines(out),
          "…no judge, no transcript re-read, no line (judge %s · reads %s)"
          % (cnt.get("judge_runs"), cnt.get("dial_reads")))
    dl_reply(w, DL_SID, "dl-r2", dl_plate("STRETCH", "HAIKU", "MEDIUM", "the small rest"),
             DL_FABLE, "xhigh", 150, path=w["tp"])
    code, out, cnt = dl_pass(w)
    now_items = dl_items(w, DL_HAND, "dial")
    second = [i for i in now_items if i.get("plate_uuid") == "dl-r2"]
    check(len(now_items) == 2 and len(second) == 1
          and second[0].get("token") != first[0].get("token")
          and second[0].get("model_id") == DL_HAIKU and second[0].get("effort") == "medium",
          "a new reply with a new plate: a new order, its own token: %s"
          % [(i.get("plate_uuid"), i.get("model_id")) for i in now_items])
    check(sorted(dl_dials(w)) == ["dl-r1", "dl-r2"],
          "one record per plate uuid: %s" % sorted(dl_dials(w)))


def case_dl4():
    start("DL4", "NO PLATE, A JUDGMENT OPENER: nothing — the postman never walks an opener")
    w = dl_world("dl4", plate="Done. The ruling is next, and it is the hub's to plate.")
    proj = w["projects"] / "dials"
    write(proj / "OPENER-Dials.md",
          "lane: Exocortex/Dials\nwritten: %s\nby: %s\non: NORTH\nhead: 0abc123\n"
          "status_updated: %s\nwhere: a fixture lane\nnext: machine\ndepends_on: nothing\n"
          "open_in: %s · fresh Claude session titled `%s`\njudgment: rule the merge order\n"
          "model: FABLE · EXTRA\n---\nread the project status/memory first.\n"
          % (iso(datetime.datetime.now().astimezone()), DL_TITLE,
             iso(datetime.datetime.now().astimezone()), proj, DL_TITLE))
    code, out, cnt = dl_pass(w)
    check(not dl_all_items(w) and not dl_dials(w) and not dl_lines(out),
          "no order, no record, no line: %s · %s" % (dl_all_items(w), dl_dials(w)))
    check(cnt.get("judge_runs") == 0 and cnt.get("dial_reads") == 2,
          "no judge child — one tail read per quiet ACT window (the plated one and the hand) "
          "showed no plate (judge %s · reads %s)"
          % (cnt.get("judge_runs"), cnt.get("dial_reads")))
    code, out, cnt = dl_pass(w)
    check(cnt.get("dial_reads") == 0 and cnt.get("judge_runs") == 0,
          "…and the next pass does not even re-read it: its transcript did not move (%s)"
          % cnt.get("dial_reads"))


def case_dl5():
    start("DL5", "AN ARROW WITH NO READABLE TRIO: kept PLATE UNREADABLE, named once, nothing "
                 "applied")
    w = dl_world("dl5", plate="Done.\n\n---\n**⇩ NEXT STRETCH**\nwhatever comes next\n\n---")
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "kept" and d.get("why") == "PLATE UNREADABLE — ⇩ NEXT STRETCH",
          "kept, with the plate's first line: %r" % d.get("why"))
    lines = dl_lines(out)
    check(lines == ["dial: «%s» — PLATE UNREADABLE — ⇩ NEXT STRETCH; nothing applied"
                    % DL_TITLE], "named in the pass line: %s" % lines)
    check(not dl_all_items(w), "nothing queued anywhere: %s" % dl_all_items(w))
    code, out2, _c = dl_pass(w)
    check(not dl_lines(out2), "…once: the next pass is silent about it: %s" % dl_lines(out2))


def case_dl6():
    start("DL6", "THE PLATED WINDOW IS THE ONLY CLAUDE WINDOW: no-carrier, nothing queued, no "
                 "wake")
    w = dl_world("dl6", hand=False)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "no-carrier", "the state is no-carrier: %s" % d)
    check(not dl_all_items(w), "nothing queued in any pending file — no dial, no send, no "
                               "notice: %s" % dl_all_items(w))
    check(dl_lines(out) == ["dial: «%s» asks SONNET · HIGH — no window to carry it" % DL_TITLE],
          "the pass says so: %s" % dl_lines(out))
    check(not raises(w), "no desktop notice of any kind: %s" % raises(w))
    code, out2, cnt2 = dl_pass(w)
    check(not dl_lines(out2) and cnt2.get("judge_runs") == 0,
          "…once: the plate stands as the question in its own reply (%s)" % dl_lines(out2))


def case_dl7():
    start("DL7", "A WINDOW WHOSE LAST MESSAGE IS 20 S OLD IS BUSY: not judged; 120 s later, judged")
    w = dl_world("dl7", age_s=20)
    code, out, cnt = dl_pass(w)
    check(cnt.get("judge_runs") == 0 and not dl_dials(w) and not dl_all_items(w),
          "20 s: no judge, no record, no order (judge %s)" % cnt.get("judge_runs"))
    age_file(w["tp"], 140)
    code, out, cnt = dl_pass(w)
    check(cnt.get("judge_runs") == 1 and (dl_dials(w).get("dl-r1") or {}).get("state") == "ordered"
          and len(dl_items(w, DL_HAND, "dial")) == 1,
          "140 s: judged and ordered (%s)" % (dl_dials(w).get("dl-r1") or {}).get("state"))


def case_dl8():
    start("DL8", "APPLIED: the receipt and the app's store → the plated window's own next turn "
                 "opens `dial set: …`, and only a turn's start carries it")
    w = dl_world("dl8")
    dl_pass(w)
    code, hout, _e = hook(w, DL_HAND, "PostToolBatch")          # the hand carries the order
    dl_store(w, DL_SID, DL_LOCAL, DL_TITLE, DL_SONNET, "high")    # …and the app shows the set
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "applied" and d.get("why") == "set by «%s»" % DL_HAND_TITLE,
          "the receipt and the store agree: applied, by the hand: %s"
          % dict((k, d.get(k)) for k in ("state", "why")))
    said = dl_items(w, DL_SID, "dial-said")
    check(len(said) == 1 and said[0].get("text") == DL_SAID and said[0].get("fyi") is True
          and said[0].get("wake") is False and said[0].get("plate_uuid") == "dl-r1",
          "one dial-said item queued for the plated window, fyi, never a wake: %s"
          % [i.get("text") for i in said])
    check(dl_lines(out) == ["dial: «%s» set to SONNET · HIGH — set by «%s»"
                            % (DL_TITLE, DL_HAND_TITLE)], "the pass says it: %s" % dl_lines(out))
    code, h1, _e = hook(w, DL_SID, "PostToolBatch")
    check(code == 0 and h1 == "" and dl_items(w, DL_SID, "dial-said"),
          "PostToolBatch prints nothing for it, and it stays pending: %r" % h1[:80])
    queue = pending_of(w, DL_SID) + [{"token": "dl8-ask", "kind": "letter", "fyi": False,
                                     "quiet": False, "to": "NORTH/Dials",
                                     "line": "- %s · to: NORTH/Dials · Exocortex · an ask that "
                                             "holds a Stop open · answer it"
                                             % datetime.date.today().isoformat()}]
    write_json(w["post"] / "pending" / ("%s.json" % DL_SID),
               {"session": DL_SID, "updated": iso(datetime.datetime.now().astimezone()),
                "items": queue})
    code, h2, _e = hook(w, DL_SID, "Stop")
    ctx2 = context_of(h2)
    check("an ask that holds a Stop open" in ctx2 and "dial set:" not in ctx2
          and dl_items(w, DL_SID, "dial-said"),
          "a Stop carries the asking letter beside it and never the dial line: %r" % ctx2[:120])
    code, h3, _e = hook(w, DL_SID, "UserPromptSubmit")
    ctx3 = context_of(h3)
    check(DL_SAID in ctx3.splitlines() and ctx3.splitlines()[0].startswith("POST — this "
                                                                           "window's dial was set"),
          "UserPromptSubmit prints it — the line alone on its own line, under the POST line: %r"
          % ctx3)
    check(not pending_of(w, DL_SID), "…and it is spent: %s" % pending_of(w, DL_SID))
    dl_pass(w)
    check((dl_dials(w).get("dl-r1") or {}).get("said"),
          "the pass records that the window was handed its line")
    start("DL8b", "THE NO-MAIL PATH IS STILL ONE STAT (M10, re-asserted) — and SessionStart "
                  "learns the window's app id once (D7)")
    for event in ("UserPromptSubmit", "PostToolBatch"):
        n = stats_for(w, DL_SID, event)
        code, hout, _e = hook(w, DL_SID, event)
        check(n == 1 and code == 0 and hout == "",
              "%s with no pending file: exactly %s stat, nothing printed" % (event, n))
    paths, _out = om_stat_paths(w, DL_SID, "UserPromptSubmit")
    check(paths is not None and len(paths) == 1 and paths[0].endswith(DL_SID + ".json"),
          "…and that one stat is the session's own pending file: %s" % paths)
    row = w["post"] / "sessions" / ("%s.json" % DL_SID)
    before = json.loads(io.open(str(row), encoding="utf-8").read()) if row.is_file() else {}
    host = {"CLAUDE_CODE_HOST_SESSION_ID": "local_dlplate_fromenv"}
    n, sout = dl_stats(w, DL_SID, "SessionStart", host)
    got = json.loads(io.open(str(row), encoding="utf-8").read()) if row.is_file() else {}
    check(n == 1 and sout == "" and got.get("host_session") == "local_dlplate_fromenv"
          and got.get("session") == DL_SID
          and all(got.get(k) == v for k, v in before.items() if k != "host_session"),
          "SessionStart with the app id in its environment: one stat, nothing printed, the id "
          "written into the session map, the rest of the row kept (%s · %s)"
          % (n, got.get("host_session")))
    mark = row.stat().st_mtime_ns
    time.sleep(0.05)
    n2, _o = dl_stats(w, DL_SID, "SessionStart", host)
    n3, _o = dl_stats(w, DL_SID, "UserPromptSubmit", host)
    check(n2 == 1 and n3 == 1 and row.stat().st_mtime_ns == mark,
          "…the same id again writes nothing, and a per-round event never touches the row "
          "(%s · %s stats)" % (n2, n3))
    check(pm_module(w).local_id_of(DL_SID, pm_module(w).session_map(w["post"]), w["hub"],
                                   {"by_cli": {}}) == "local_dlplate_fromenv",
          "local_id_of answers from the session map when the app's store does not")


def case_dl9():
    start("DL9", "AN ORDER NOBODY TAKES: expired at 10 min and judged again once; a second "
                 "expiry is the no-carrier line, once")
    w = dl_world("dl9")
    dl_pass(w)
    first = [i.get("token") for i in dl_items(w, DL_HAND, "dial")]
    dl_backdate(w, "dl-r1", "ordered", 11)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    now_tokens = [i.get("token") for i in dl_items(w, DL_HAND, "dial")]
    check(d.get("state") == "ordered" and d.get("orders") == 2 and len(now_tokens) == 1
          and now_tokens != first and cnt.get("judge_runs") == 1,
          "11 min, no receipt: the first order taken back, the plate judged again, ONE new "
          "order (%s · orders %s · %s → %s)" % (d.get("state"), d.get("orders"), first,
                                                now_tokens))
    dl_backdate(w, "dl-r1", "ordered", 11)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "no-carrier" and not dl_items(w, DL_HAND, "dial")
          and cnt.get("judge_runs") == 0,
          "a second expiry: no-carrier, nothing left in the hand's file, no third order (%s)"
          % d.get("state"))
    check(dl_lines(out) == ["dial: «%s» asks SONNET · HIGH — no window to carry it" % DL_TITLE],
          "…in the no-carrier grammar: %s" % dl_lines(out))
    code, out, cnt = dl_pass(w)
    check(not dl_lines(out) and not dl_all_items(w), "…said once: %s" % dl_lines(out))


def case_dl10():
    start("DL10", "A ROUTINE'S RUN AND A CODEX THREAD ARE NEVER THE HAND")
    w = dl_world("dl10", hand=False)
    run_path = dl_reply(w, DL_RUN, "dl-run1", dl_plate("STRETCH", "HAIKU", "LOW", "a routine"),
                        DL_SONNET, "medium", 90)
    dl_store(w, DL_RUN, DL_RUN_LOCAL, "ACT — Exocortex/Routine: a routine's run", DL_SONNET,
             "medium", scheduled=True)
    rollout = (w["home"] / ".codex" / "sessions" / "2026" / "10" / "14"
               / ("rollout-2026-10-14T22-00-00-%s.jsonl" % TID_C))
    write(rollout, json.dumps({"type": "session_meta", "payload": {"session_id": TID_C}}) + "\n")
    age_file(rollout, 10)
    dl_live(w, w["rows"] + [dl_row(DL_RUN, "ACT — Exocortex/Routine: a routine's run", DL_SONNET,
                                   run_path),
                            dl_row(TID_C, "ACT — Exocortex/Codex: a thread", "gpt-6", rollout,
                                   kind="codex")])
    code, out, cnt = dl_pass(w)
    check((dl_dials(w).get("dl-r1") or {}).get("state") == "no-carrier" and not dl_all_items(w),
          "a routine's run (newer) and a Codex thread (newest) only: no hand, no-carrier, "
          "nothing queued: %s" % dl_all_items(w))
    check("dl-run1" not in dl_dials(w), "…and the routine's own plate is never judged: %s"
          % sorted(dl_dials(w)))
    start("DL10b", "…and with an ordinary Claude window beside them, that window is the hand")
    v = dl_world("dl10b")
    run_path = dl_reply(v, DL_RUN, "dl-run1", "A routine wrote last.", DL_SONNET, "medium", 90)
    dl_store(v, DL_RUN, DL_RUN_LOCAL, "ACT — Exocortex/Routine: a routine's run", DL_SONNET,
             "medium", scheduled=True)
    age_file(v["hp"], 300)
    rollout = (v["home"] / ".codex" / "sessions" / "2026" / "10" / "14"
               / ("rollout-2026-10-14T22-00-00-%s.jsonl" % TID_C))
    write(rollout, json.dumps({"type": "session_meta", "payload": {"session_id": TID_C}}) + "\n")
    age_file(rollout, 10)
    code, out, cnt = dl_pass(v)
    check(len(dl_items(v, DL_HAND, "dial")) == 1 and not pending_of(v, DL_RUN)
          and not pending_of(v, TID_C),
          "the order sits with the ordinary window — never the routine's run, though it wrote "
          "later, never the Codex thread: %s" % [s for s, _i in dl_all_items(v)])


def case_dl9b():
    start("DL9b", "CARRIED BUT NOT SHOWN: a hand that did nothing is ordered again; a set the "
                  "window's own menu then changed STANDS — never ordered again")
    w = dl_world("dl9b")
    dl_pass(w)
    hook(w, DL_HAND, "PostToolBatch")                         # taken: a receipt, and no call made
    dl_pass(w)                                                 # …seen: carried
    dl_backdate(w, "dl-r1", "carried", 3)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "ordered" and d.get("orders") == 2
          and len(dl_items(w, DL_HAND, "dial")) == 1 and cnt.get("judge_runs") == 1,
          "taken, no set call in the hand's transcript, the store unchanged past the grace: "
          "judged again, one more order (%s · orders %s)" % (d.get("state"), d.get("orders")))
    v = dl_world("dl9c")
    dl_pass(v)
    hook(v, DL_HAND, "PostToolBatch")
    om_append(v["hp"], {"type": "assistant", "sessionId": DL_HAND, "uuid": "dl-h2",
                        "isSidechain": False, "timestamp": dl_iso_z(0),
                        "message": {"role": "assistant", "model": DL_SONNET, "content": [
                            {"type": "tool_use", "id": "toolu_dl9c",
                             "name": "mcp__ccd_session_mgmt__set_session_model",
                             "input": {"session_id": DL_LOCAL, "model": DL_SONNET}}]}})
    dl_store(v, DL_SID, DL_LOCAL, DL_TITLE, "claude-opus-5-5", "xhigh")   # the menu, after
    dl_pass(v)
    dl_backdate(v, "dl-r1", "carried", 3)
    code, out, cnt = dl_pass(v)
    d = dl_dials(v).get("dl-r1") or {}
    check(d.get("state") == "kept" and "the window's own menu stands" in str(d.get("why"))
          and not dl_items(v, DL_HAND, "dial") and not dl_items(v, DL_SID, "dial-said")
          and cnt.get("judge_runs") == 0,
          "the hand made the call and the app shows another model: kept, the menu stands — no "
          "second order, no dial line: %s" % d.get("why"))
    check(dl_lines(out) == ["dial: «%s» — %s" % (DL_TITLE, d.get("why"))],
          "…said once in the pass line: %s" % dl_lines(out))


def case_dl11():
    start("DL11", "METER STALE IS TRANSIENT (the hub's Q4): kept until the meter's read_at moves, "
                  "judged again then — at most once an hour — and a DOWN is never held by it")
    w = dl_world("dl11", plate=dl_plate("TURN", "SONNET", "EXTRA", "a harder stretch"),
                 model=DL_SONNET, effort="high")
    dl_meter(w, minutes_ago=45)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(d.get("state") == "kept" and str(d.get("why")).startswith("METER STALE — meter read 45")
          and not dl_all_items(w) and len(dl_lines(out)) == 1 and "kept: METER STALE" in out,
          "an UP under a 45-minute-old meter: kept, said once, nothing queued: %s" % d.get("why"))
    code, out, cnt = dl_pass(w)
    check(cnt.get("judge_runs") == 0 and not dl_lines(out),
          "the meter has not moved: not judged again (judge %s)" % cnt.get("judge_runs"))
    dl_meter(w, minutes_ago=44)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    check(cnt.get("judge_runs") == 1 and d.get("state") == "kept" and d.get("stale_rejudged")
          and not dl_lines(out),
          "its read_at moved (still stale): judged again at once, kept, not said twice (judge %s)"
          % cnt.get("judge_runs"))
    dl_meter(w, minutes_ago=43)
    code, out, cnt = dl_pass(w)
    check(cnt.get("judge_runs") == 0, "moved again inside the hour: not judged (judge %s)"
          % cnt.get("judge_runs"))
    dl_backdate(w, "dl-r1", "stale_rejudged", 61)
    dl_meter(w, minutes_ago=1)
    code, out, cnt = dl_pass(w)
    d = dl_dials(w).get("dl-r1") or {}
    orders = dl_items(w, DL_HAND, "dial")
    check(cnt.get("judge_runs") == 1 and d.get("state") == "ordered" and len(orders) == 1
          and orders[0].get("effort") == "xhigh" and orders[0].get("model_id") == DL_SONNET,
          "an hour on, a fresh meter under warn: judged, and the UP is ordered (%s · %s)"
          % (d.get("state"), [o.get("effort") for o in orders]))
    v = dl_world("dl11b")
    dl_meter(v, minutes_ago=45)
    code, out, cnt = dl_pass(v)
    check((dl_dials(v).get("dl-r1") or {}).get("state") == "ordered"
          and len(dl_items(v, DL_HAND, "dial")) == 1,
          "a ⇩ DOWN under the same stale meter is never held: ordered at once")


DL_CASES = (case_dl1, case_dl2, case_dl3, case_dl4, case_dl5, case_dl6, case_dl7, case_dl8,
            case_dl9, case_dl9b, case_dl10, case_dl11)


def live_fingerprint():
    hub = real_hub()
    marks = {}
    for name in ("claims.json", "INBOX.md", "post-north.json", "post-south.json",
                 "usage-settings.json"):
        f = hub / name
        marks[name] = f.stat().st_size if f.is_file() else None
    for f in sorted(hub.glob("ear-*.json")):
        marks[f.name] = f.stat().st_size
    # NOT THE SETTINGS FILE'S SIZE (BQ63C): the app rewrites that file itself.
    # What this gate must never touch is the postman's own hook entries in it.
    marks["~/.claude/settings.json"] = postman_hooks(Path.home() / ".claude" / "settings.json")
    codex_hooks = Path.home() / ".codex" / "hooks.json"
    marks["~/.codex/hooks.json"] = codex_hooks.stat().st_size if codex_hooks.is_file() else None
    return marks


def case_live(before):
    start("LIVE", "nothing live was written — proved by the very content this gate writes")
    after = live_fingerprint()
    hub = real_hub()
    # BQ63C — the POSTMAN'S OWN HOOK ENTRIES, never the file, which the app
    # itself rewrites.  Absent both times is the one state that passes without a
    # comparison; anything this gate cannot read, it says so and does not claim.
    was, is_now = before.get("~/.claude/settings.json"), after.get("~/.claude/settings.json")
    (was_kind, was_hooks) = was if isinstance(was, tuple) else ("unreadable (no mark)", [])
    (now_kind, now_hooks) = is_now if isinstance(is_now, tuple) else ("unreadable (no mark)", [])
    if was_kind == "absent" and now_kind == "absent":
        check(True, "~/.claude/settings.json is absent, before and after — the postman's own "
                    "hook entries could not have been touched")
    elif was_kind == "ok" and now_kind == "ok":
        check(was_hooks == now_hooks,
              "the postman's own hook entries in ~/.claude/settings.json are untouched "
              "(%d entries; the app's own rewrites of that file are not this gate's business)"
              % len(now_hooks))
    else:
        check(False, "~/.claude/settings.json could not be compared — %s before, %s after"
                     % (was_kind, now_kind))
    check(before.get("~/.codex/hooks.json") == after.get("~/.codex/hooks.json") is None
          or before.get("~/.codex/hooks.json") == after.get("~/.codex/hooks.json"),
          "~/.codex/hooks.json was not created by this run")
    # BQ63B — only the names this gate's OWN worlds could write.  A live
    # session arming its own waiter is not this gate's doing and never reds it.
    own = own_ear_names(hub)
    appeared = new_own_ears(before, after, own)
    check(not appeared,
          "no ear file of this gate's own making appeared in the live hub (%d names watched%s)"
          % (len(own), (": %s" % ", ".join(appeared)) if appeared else ""))
    text = io.open(str(hub / "claims.json"), encoding="utf-8").read() \
        if (hub / "claims.json").is_file() else ""
    check(HOLDER not in text and OTHER not in text and GATE_QW not in text,
          "not one of this gate's own titles is in the live claims")
    check(before.get("usage-settings.json") == after.get("usage-settings.json"),
          "the live usage-settings.json is exactly as this run found it (%s)"
          % ("absent" if after.get("usage-settings.json") is None else "present, untouched"))
    inbox = io.open(str(hub / "INBOX.md"), encoding="utf-8").read() \
        if (hub / "INBOX.md").is_file() else ""
    check("the gate's own letter" not in inbox and "cut the payload" not in inbox,
          "…and not one of its letters is in the live INBOX")
    # The postman is INSTALLED on this machine now and passes every minute, so its
    # own POST DIR is never empty and emptiness would be a false red. What this
    # case has always meant is asserted directly instead: NOT ONE BYTE OF THIS
    # GATE'S OWN WORK is anywhere in the live POST DIR.
    live_post = Path.home() / ".exocortex" / "post"
    text = ""
    for name in ("pending", "outbox", "holds", "waiters", "told", "acks", "nudges"):
        folder = live_post / name
        if not folder.is_dir():
            continue
        for f in sorted(folder.glob("*")):
            if f.is_file():
                text += f.name + "\n" + io.open(str(f), encoding="utf-8", errors="replace").read()
    for name in ("receipts.jsonl", "state.json", "hook-errors.log", "waits.jsonl"):
        f = live_post / name
        if f.is_file():
            text += io.open(str(f), encoding="utf-8", errors="replace").read()
    mine = (HOLDER, OTHER, SID_A, SID_B, TID_C, "the gate's own letter", "cut the payload",
            OWNER_NOTE, "a letter written in a rehearsal", "nobody can carry", GATE_QW)
    found = [m for m in mine if m in text]
    check(not found, "nothing was queued in this machine's own POST DIR%s"
          % (" (found: %s)" % ", ".join(found) if found else ""))


# --------------------------------------------------------------------------

def main(argv):
    keep = "--keep" in argv
    # THE GATE NEVER RUNS ITSELF (the self-spawning lesson): every child carries
    # the depth mark, and a gate-comms started under it refuses at once.
    if os.environ.get("EXO_GATE_COMMS_DEPTH"):
        print("gate-comms: refused — started under another gate-comms (depth %s); a gate "
              "never runs itself" % os.environ.get("EXO_GATE_COMMS_DEPTH"))
        return 1
    os.environ["EXO_GATE_COMMS_DEPTH"] = "1"
    only = ""
    for i, a in enumerate(argv):
        if a == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
        if a == "--skill" and i + 1 < len(argv):
            QW_ARGS["skill"] = argv[i + 1]
    ROOT.mkdir(parents=True, exist_ok=True)
    print("gate-comms.py · %s · scratch %s"
          % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), ROOT))
    print("  layout: %s" % ("beside its subjects (%s)" % HERE
                            if (HERE / "postman.py").is_file() else "a hub's tools/ (%s)" % HERE))
    load_start = load_now()
    print("  load: %s" % ("%.1f over %d CPUs" % (load_start, CPUS) if load_start is not None
                          else "unreadable"))
    live_before = live_fingerprint()
    qw = (case_qw1, case_qw2, case_qw3, case_qw4, case_qw5, case_qw6, case_qw7, case_qw8,
          case_qw10, case_qw11, case_qww1, case_qww2, case_qww3, case_qww4, case_qw9)
    everything = (case_c1, case_c2, case_c3, case_c4,
                 case_bq63a, case_bq63b, case_bq63c, case_bq68,
                 case_p1, case_p2, case_p3, case_p4, case_p5, case_p6, case_p7,
                 case_p8, case_p9, case_p10, case_p11, case_p12, case_p13,
                 case_p15, case_p16,
                 case_pb15, case_pb16, case_pb17, case_pb18, case_pb19, case_pb20,
                 case_pb21, case_pb22, case_pb23, case_pb24, case_pb25,
                 case_p14) + qw
    fd = (case_fd1, case_fd2, case_fd3, case_fd4, case_fd5, case_fd6, case_fd7, case_fd8,
          case_fd9, case_fd10, case_fd11)
    everything = everything + fd + OM_CASES + B205_CASES + DL_CASES + B337_CASES
    chosen = (qw if only.upper() == "QW" else fd if only.upper() == "FD"
              else fd + qw if only.upper() == "FDQW"
              else OM_CASES if only.upper() == "OM"
              else B205_CASES if only.upper() == "B205"
              else B337_CASES if only.upper() == "B337"
              else DL_CASES if only.upper() == "DL" else everything)
    for case in chosen + (lambda: case_live(live_before),):
        try:
            case()
        except Exception as exc:
            FAILS.append("%s: the case itself raised %r" % (CASE["id"], exc))
            print("  [FAIL] the case itself raised %r" % (exc,))
    print("\n===== GATES =====")
    total = PASSES + len(FAILS)
    print("  %d checks · %d passed · %d failed%s%s"
          % (total, PASSES, len(FAILS), (" · %d skipped" % len(SKIPS)) if SKIPS else "",
             (" · %d not judged (load)" % len(LOADS)) if LOADS else ""))
    for f in FAILS:
        print("  FAIL  %s" % f)
    for s in SKIPS:
        print("  SKIP  %s" % s)
    for l in LOADS:
        print("  LOAD  %s" % l)
    if keep:
        print("  scratch kept: %s" % ROOT)
    else:
        for w in WORLDS:
            shutil.rmtree(str(w["base"]), ignore_errors=True)
    load_end = load_now()
    if any(x is not None and x > CPUS for x in (load_start, load_end)):
        print("  load %s at start · %s at end · over %d CPUs: timing checks were judged against "
              "this run's own interpreter baseline"
              % tuple(["%.1f" % load_start if load_start is not None else "?",
                       "%.1f" % load_end if load_end is not None else "?", CPUS]))
    return 1 if FAILS else 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    for w in WORLDS:
        shutil.rmtree(str(w["base"]), ignore_errors=True)
    try:
        REGISTRY_FILE.unlink()
    except OSError:
        pass
    try:
        ROOT.rmdir()                       # the shared parent, once it is empty
    except OSError:
        pass


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
