#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-usage.py — the usage monitor's gate.

    python3 tools/gate-usage.py           # every case (`python` on Windows)
    python3 tools/gate-usage.py --keep    # leave the scratch worlds for inspection

HERMETIC: every case builds its own world under the system temp folder — a scratch HOME whose
machine.json names a scratch hub, scratch vendor stores (.claude / .codex / .grok) and a scratch
POST DIR, and a stub sync.py that records the verb it was asked for. The tools under test are
copied into each world from beside this file (a build folder) or, failing that, from the hub's
own tools/. No real mail, meter, settings file, scheduler, stamp or push is written; no network.

  G1  rails — nothing outside the worlds was written (the live hub, settings.json's hook entries,
      the scheduled tasks, the three vendor stores, the machine-personal state), proved by the very
      content this gate writes (its fixture ids and its marker words)
  G2  thresholds — a meter at 79 prints nothing; 80 prints the WARN line with the fixture's reset
      and read time; 90 prints the PAUSE line; back at 79 nothing again; and a MUTANT usage.py that
      caches the last verdict is caught by that very check
  G3  stale — 31 min old prints its age and no percent; 29 min prints the percent
  G4  the waiter — under PAUSE `mail.py --wait` exits without arming and asks the question
      ('continue, or button up? (say either in your window)');
      below PAUSE it arms; a waiter already armed (the owner's --force) lets a letter wait
  G5  the routine step — `usage.py --check` exits non-zero under PAUSE and zero below; a fixture
      SKILL.md given the step ends at it (a stub runner's model counter stays 0); and the effort
      hook BLOCKS a scheduled run's prompt under a PAUSE that reaches its model
  G6  scope — a Fable-week PAUSE reaches a Fable window and not a Sonnet one; `pause_scope: all`
      reaches both; an all-models PAUSE reaches both; the postman's Stop hook stands down
  G7  the Codex road — three token_count events: the meter is the LAST one's rate_limits (percent,
      week, resets_at to local ISO); no rollouts: no file and one line; the pulse's writer flag
  G8  the Grok road — two usage.json files, one inside the window and one outside, sum to the
      inside one; `week_spend_limit_usd` makes a spend WARN fire at 80 percent of it
  G9  the accounting — a repeated requestId counts once; three sessions match the hand sum below;
      `--by hour` buckets by the local clock
  G10 announce-once — two PAUSE turn starts send ONE <MACHINE>/all letter
  G11 the tree — a meter at 85 draws an amber band with its read time; 91 red; stale grey with its
      age; Grok's band reads 'not readable — accounting only'
  G12 the open watch — a Sonnet window's `mail.py --watch`, armed below PAUSE with --every
      30, ends in ONE line, exit 0, within seconds of the all-models meter flipping to PAUSE, and the
      letter that asks is never printed; a Fable-week PAUSE leaves the same watch listening and it
      still carries a letter; a MUTANT watch that never re-reads keeps listening past the flip (the
      check has teeth); the cadence is mail.py's own minute, the gate's seam only shortens it

THE GATE ASKS:
  G-A1 a crossing of 90 raises ONE notice through the --notify seam (its title, its body the
       question) and sends ONE letter naming both words and the dollars; the turn-start line ends
       with what a session does with either word, the letter and the notice never do; a second
       turn start and the hub's --announce ask nothing more; the next reset asks again, once; a
       notifier that takes 6 s or fails never holds or stops the line and the letter
  G-A2 a crossing of 80 raises ONE notice, information only, and sends NO letter, never twice; the
       same window crossing 90 afterwards still asks — the WARN mark never stands in for the PAUSE
  G-A3 `--continue` under a PAUSE writes the override (every field), prints the dollars line FIRST;
       the next evaluate() is `continued`, pause False, the R4 line; --check exits 0; the waiter
       arms; a scheduled prompt blocked before the word is not blocked after it
  G-A4 `--continue` with no PAUSE hit: the refusal line, exit 1, the settings file byte for byte
  G-A5 an override whose `until` has come is pruned (the other keys kept) and its one line is said
       once — with the reset, and at an --until while the window is still over the line (PAUSE again)
  G-A6 a manual pause stands above an override (the R5 line, --check 1, `--continue` refused);
       `--manual on|off` round-trips without touching any other key; each manual onset asks once
  G-A7 a PAUSE on another window — all models, the 5-hour window, the next week of the same label —
       still pauses; the covered window alone holds nothing (pause_facts); a WARN on another window
       prints its own line after the CONTINUED line and its crossing raises one notice, no letter
  G-A8 the dollars clause, three ways — extra usage on (the figure), OFF (`enabled: false`: past
       100 percent the model stops, continuing spends nothing), no figure — in the question, the
       answer's first line and the CONTINUED line; a Codex meter's credits are no figure
  G-A9 the tree's band and the ledger's chip carry ASKED <when> and CONTINUED until <reset> · <who>
       from a fixture, as a word beside the meter and in its title; nothing otherwise; the rendered
       tree carries the word

ONE LOGIN, ONE METER. Terminal readers carry their CLI login in .claude.json.
Meter-bearing hook windows carry their own bridge owner and its logins map; an ownerless window
uses explicit app sign-in evidence only where the case calls for it. No window borrows a meter's
identity. G13 keeps the opposite case: no identity, one provisional refresh line, no meter verdict.
  U-a  two logins' files on one machine, the NEWER at PAUSE is the other login's → the line, the
       hook and --check read THIS login's file (its own numbers, no PAUSE, the login named); a
       MUTANT that picks the newest file across logins prints the other login's PAUSE (teeth)
  U-b  this login's file 4 h old → `refresh (read 4 h ago)`, no percent anywhere — from --line and
       from the hook's turn start
  U-c  a SCAN: a get_usage result in a transcript that names no owner is filed `login: unknown`
       (and read as another login's: the line says refresh); a transcript owned by the app's
       account is filed under the app's login with its account; a transcript owned by an account
       this machine does not know is `unknown` too, until a meter file names that account
  U-d  the hook passes the WINDOW's login: a window whose transcript an account a meter file
       names owns (not the app's) hears THAT login's PAUSE line, the login named in it; the app's
       own window hears its own login's numbers
  U-e  the wake screen's receipts carry the same words --line prints (one copy)

THE AUTO-PAUSE WATCH (the second half of the pause work). Any PLAN window (5-hour,
week, week-model) at auto_pause_percent (97) pauses the login's windows until its reset, and no «continue»
lifts it; the verdict carries the contract fields part B reads:
  AP1  a 5-hour window at 97: level auto-pause, auto_key, auto_line naming label, percent, login and the reset;
       --check exits 1; --line prints AUTO-PAUSE first; the fields are present and falsy below the line
  AP2  96 percent: an ordinary PAUSE, nothing new          AP3  an override does not lift it; --continue refuses
  AP4  the latch: 95 at the same reset stays paused; a newer reset or a past one releases it (auto_pause_window popped)
  AP5  the Fable week at 97 pauses Fable windows, not Sonnet ones; with the hard stop present the stop line is first
  AP6  null turns the watch off; a per_vendor row overrides the line       AP7  another login's meter does not reach
  AP8  announce: one notice at the crossing (title Exocortex · auto-pause), no letter, none twice, a 90 then 97 raises
       two, 97 then 90 nothing new, one `AUTO-PAUSE lifted` notice after the reset     AP9  pause_facts carries the fields
  AP10 the refresh nag every 2 turns at or above PAUSE and every 10 below, through effort.py's hook
  AP11 the hard stop and an auto-pause together: level stop, auto_pause True, both lines
  AP12 plan windows only: the extra-usage spend window never triggers it

Stdlib only, Python 3.9, OS-neutral (no path is typed; stdout is made safe for a cp1252 console).
Exit 0 only when every check passes.
"""
import datetime
import hashlib
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
from pathlib import Path

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

if os.environ.get("EXO_GATE_USAGE_DEPTH"):
    print("gate-usage: refusing to run inside its own child (depth mark set)")
    sys.exit(3)
os.environ["EXO_GATE_USAGE_DEPTH"] = "1"
os.environ.pop("EXO_MACHINE_JSON", None)       # the machine's own record never reaches a fixture
os.environ.pop("EXO_USAGE_STATE_DIR", None)

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

ROOT = Path(tempfile.gettempdir()) / ("exo-gate-usage-%d" % os.getpid())
PY = sys.executable or "python3"
MARK = "GATE-USAGE-145"                        # every fixture word carries it
FAILS, PASSES = [], [0]
CASE = {"id": ""}
TOOLS = ("hook_say.py", "usage.py", "effort.py", "mail.py", "postman.py", "exo_common.py", "exo_registry.py",
         "exo_paths.py", "collect-openers.py", "opener_carriers.py", "grok_sessions.py")
OPTIONAL = ("opener_carriers.py", "grok_sessions.py")
SID_F = "f1450000-aaaa-4bbb-8ccc-000000000f45"     # a Fable window
SID_S = "f1450000-aaaa-4bbb-8ccc-000000000545"     # a Sonnet window
SID_U = "f1450000-aaaa-4bbb-8ccc-00000000216a"     # a window whose transcript has an owner
SID_V = "f1450000-aaaa-4bbb-8ccc-00000000216b"     # a window whose transcript names none
LOGIN_W = "wren@example.test"                      # the app's own login in every world
ACCT_W = "a1b2c3d4-0000-4000-8000-00000000a216"    # its account (the app's .claude.json)
LOGIN_K = "kestrel@example.test"                   # another login on the same machine
ACCT_K = "b5c6d7e8-0000-4000-8000-00000000b216"
ACCT_X = "c9d0e1f2-0000-4000-8000-00000000c216"    # an account nothing on this machine names
# Terminal readers use the CLI config; hook windows use their own bridge owner.
# The source word remains part of the existing line contract.
CLI = " (cli config \u2014 not the app's)"
TRANSCRIPT = " (transcript)"
FABLE, SONNET = "claude-fable-5-1", "claude-sonnet-5"
TITLE_S = "ACT — Exocortex/Desk: %s the sonnet desk" % MARK
REGISTRY = {
    "version": 1, "note": "gate-usage's own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {"north": {"label": "North", "mark": "\u25cf", "os": "macos",
                           "hue": {"light": "#2456a4", "dark": "#7fb0e8"}},
                 "south": {"label": "South", "mark": "\u258e", "os": "windows",
                           "hue": {"light": "#9a6b3a", "dark": "#d4a373"}}},
    "minds": [{"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
              {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0f766e", "dark": "#2dd4bf"}},
              {"name": "NOBODY", "vendor": "OpenAI", "kind": "codex", "show": True,
               "hue": {"light": "#be185d", "dark": "#f0a0c0"}},
              {"name": "GROK", "vendor": "xAI", "kind": "grok", "show": False,
               "hue": {"light": "#4a6c00", "dark": "#9cc450"}}],
    "mind_aliases": {"CODEX": "NOBODY"},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Exocortex"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}
SYNC_STUB = ("import io, os, sys\n"
             "io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync-calls.log'),"
             " 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + '\\n')\n")
SPEND = {"spent": "10.45", "limit": "40.00", "currency": "USD", "enabled": True}
SPEND_OFF = {"spent": "10.45", "limit": "40.00", "currency": "USD", "enabled": False}
OFF = ("extra usage is OFF \u2014 past 100 percent this model stops until the reset; "
       "continuing spends nothing")
SESSION = ("a session hearing \u00abcontinue\u00bb runs usage.py --continue --by \"<its title>\" and "
           "answers with its two lines; hearing \u00abbutton up\u00bb it runs the button-up")
GATE_TITLE = "Exocortex \u00b7 usage gate"
QUESTION = ("continue, or button up? \u00b7 say \u00abcontinue\u00bb (work on until the reset; "
            "extra usage so far $10.45 of $40 this month) or \u00abbutton up\u00bb (the hub buttons up now)")
NOTIFY_STUB = ("import io, json, os, sys\n"
               "io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notify-calls.jsonl'),"
               " 'a', encoding='utf-8').write(json.dumps(sys.argv[1:]) + '\\n')\n")
# R2's bounds: a notifier that takes six seconds (past a hook's five), and one that fails
SLOW_STUB = ("import io, json, os, sys, time\n"
             "time.sleep(6)\n"
             "io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notify-calls.jsonl'),"
             " 'a', encoding='utf-8').write(json.dumps(sys.argv[1:]) + '\\n')\n")
FAIL_STUB = ("import sys\n"
             "sys.stderr.write('the notifier is broken\\n')\n"
             "sys.exit(1)\n")
WORLDS = []


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def start(cid, name):
    CASE["id"] = cid
    print("\n======== %s — %s ========" % (cid, name))


def check(cond, msg):
    if cond:
        PASSES[0] += 1
        print("  [PASS] %s" % msg)
    else:
        FAILS.append("%s: %s" % (CASE["id"], msg))
        print("  [FAIL] %s" % msg)
    return bool(cond)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def now():
    return datetime.datetime.now().astimezone()


def iso(d):
    return d.replace(microsecond=0).isoformat()


def zulu(d):
    return d.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def source_tool(name):
    here = HERE / name
    if here.is_file():
        return here
    try:
        with io.open(str(Path.home() / OLDER_SYNC / "machine.json"), encoding="utf-8") as fh:
            hub = (json.load(fh).get("roots") or {}).get("orchestrator")
        if hub and (Path(hub) / "tools" / name).is_file():
            return Path(hub) / "tools" / name
    except Exception:
        pass
    return HERE.parent / "tools" / name


def run(args, w=None, env=None, stdin=None, timeout=120, cwd=None):
    base = dict(os.environ)
    base.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0"})
    for k, v in dict((w or {}).get("env") or {}, **(env or {})).items():
        if v is None:
            base.pop(k, None)
        else:
            base[k] = str(v)
    try:
        p = subprocess.run([str(a) for a in args], input=stdin, cwd=str(cwd or (w or {}).get("hub") or HERE),
                           env=base, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                           universal_newlines=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def world(name, machine="north"):
    base = ROOT / name
    shutil.rmtree(str(base), ignore_errors=True)
    home, hub, post = base / "home", base / "hub", base / "post"
    for f in (home / OLDER_SYNC, hub / "tools", post, base / "out", base / "state",
              base / "effort", home / ".claude" / "projects", home / ".codex" / "sessions",
              home / ".grok" / "sessions", base / "projects"):
        f.mkdir(parents=True, exist_ok=True)
    for t in TOOLS:
        src = source_tool(t)
        if not src.is_file():
            if t in OPTIONAL:
                continue
            raise RuntimeError("the tool under test is missing: %s" % t)
        shutil.copy2(str(src), str(hub / "tools" / t))
    write_json(hub / "registry.json", REGISTRY)
    write(hub / "INBOX.md", "# INBOX\n\n")
    write_json(post / "installed.json", {"when": iso(now()), "vendors": ["claude"], "hub": str(hub)})
    write_json(home / OLDER_SYNC / "machine.json",
               {"name": machine, "os": platform.system(),
                "roots": {"orchestrator": str(hub), "projects": str(base / "projects"),
                          "claude": str(home / ".claude"), "codex": str(home / ".codex"),
                          "grok": str(home / ".grok"), "home": str(home), "post": str(post)}})
    write_json(home / OLDER_SYNC / "sync-manifest.json", {"machines": {"north": {}, "south": {}}})
    # The terminal CLI login is evidence for terminal readers only, never a desktop window.
    write_json(home / ".claude.json", {"oauthAccount": {"emailAddress": LOGIN_W, "accountUuid": ACCT_W}})
    write(home / OLDER_SYNC / "sync.py", SYNC_STUB)
    write(base / "notify.py", NOTIFY_STUB)
    w = {"base": base, "home": home, "hub": hub, "post": post, "machine": machine,
         "env": {"HOME": str(home), "USERPROFILE": str(home), "HOMEDRIVE": None, "HOMEPATH": None,
                 "EXO_MACHINE_JSON": str(home / OLDER_SYNC / "machine.json"),
                 "EXO_REGISTRY_JSON": str(hub / "registry.json"),
                 "EXO_USAGE_STATE_DIR": str(base / "state"),
                 "EXO_NOTIFY": str(base / "notify.py"),
                 "APPDATA": str(home / "AppData" / "Roaming"),
                 "CLAUDE_CONFIG_DIR": str(home / ".claude"),
                 "CLAUDE_CODE_SESSION_ID": None, "CLAUDE_CODE_HOST_SESSION_ID": None,
                 "CLAUDE_CODE_ENTRYPOINT": None,
                 "CLAUDE_CODE_ACCOUNT_UUID": None, "CLAUDE_CODE_USER_EMAIL": None,
                 "CLAUDE_EFFORT": None, "CLAUDE_CODE_EFFORT_LEVEL": None}}
    WORLDS.append(w)
    return w


def window(w, sid, model, title=None, project="-gate-hub", rows=(), owner=ACCT_W):
    folder = w["home"] / ".claude" / "projects" / project
    path = folder / ("%s.jsonl" % sid)
    body = [{"parentUuid": None, "isSidechain": False, "type": "user",
             "message": {"role": "user", "content": "go"}, "uuid": "u-1",
             "timestamp": zulu(now() - datetime.timedelta(minutes=5)), "sessionId": sid},
            {"parentUuid": "u-1", "isSidechain": False, "type": "assistant", "requestId": "req-w-1",
             "message": {"role": "assistant", "model": model, "id": "msg-w-1",
                         "content": [{"type": "text", "text": "done"}],
                         "usage": {"input_tokens": 4000, "cache_read_input_tokens": 4000,
                                   "cache_creation_input_tokens": 4000, "output_tokens": 10}},
             "uuid": "a-1", "timestamp": zulu(now() - datetime.timedelta(minutes=4)), "sessionId": sid}]
    # ASSUMES: a meter expectation belongs to this window's OWN account.
    # G13 falsifies that premise: no bridge, variables or app config, even at 90 percent.
    # Explicit owner rows keep their own account; scans may explicitly name no owner.
    if owner and not any(r.get("ownerAccountUuid") for r in rows):
        body.insert(0, owner_row(sid, owner))
        write_json(w["hub"] / ("logins-%s.json" % w["machine"]), {
            owner[:8]: {"login": LOGIN_W, "seen": iso(now()), "by": "fixture bridge owner"}})
    body.extend(rows)
    write(path, "\n".join(json.dumps(r, ensure_ascii=False) for r in body) + "\n")
    if title:
        write_json(folder / sid / "custom-title.json", {"customTitle": title})
    return path


def meter(w, windows, age_min=1.0, vendor="claude", login="wren@example.test", machine=None,
          spend=None, meter_word="readable", extra=None):
    read_at = now() - datetime.timedelta(minutes=age_min)
    safe = login.lower().replace("@", "-at-")
    body = {"vendor": vendor, "machine": machine or w["machine"], "login": login,
            "login_source": "--login", "read_at": iso(read_at), "source": "fixture %s" % MARK,
            "windows": windows, "spend": spend, "meter": meter_word}
    body.update(extra or {})
    path = w["hub"] / ("usage-%s-%s-%s.json" % (machine or w["machine"], vendor, safe))
    write_json(path, body)
    return path, read_at


def win(label, pct, kind, model="", reset_days=2.0, at=None):
    at = at if at is not None else now() + datetime.timedelta(days=reset_days)
    return {"label": label, "percent": pct, "kind": kind, "model": model, "resets_at": iso(at)}


def fable_week(pct, **kw):
    return win("Weekly \u00b7 Fable", pct, "week-model", "fable", **kw)


def all_week(pct, **kw):
    return win("Weekly \u00b7 all models", pct, "week", **kw)


def window_variables(w, sid):
    """An ownerless window's app sign-in, backed by its own world's app config."""
    write_json(w["home"] / "Library" / "Application Support" / "Claude" / "config.json",
               {"lastKnownAccountUuid": ACCT_W})
    return {"CLAUDE_CODE_ACCOUNT_UUID": ACCT_W, "CLAUDE_CODE_USER_EMAIL": LOGIN_W,
            "CLAUDE_CODE_SESSION_ID": sid}


def hook(w, sid, transcript, prompt="carry on %s" % MARK, event="UserPromptSubmit", env=None):
    ev = {"session_id": sid, "hook_event_name": event, "prompt": prompt,
          "transcript_path": str(transcript) if transcript else "", "cwd": str(w["hub"]),
          "entrypoint": "claude-desktop"}
    # Scheduled first prompts have no transcript yet: give those fixtures their own sign-in.
    own_env = window_variables(w, sid) if transcript is None else {}
    own_env.update(env or {})
    code, out = run([PY, w["hub"] / "tools" / "effort.py", "--hook", "--vendor", "claude",
                     "--hub", w["hub"], "--state-dir", w["base"] / "effort"], w,
                    env=own_env, stdin=json.dumps(ev))
    try:
        d = json.loads(out) if out.strip() else {}
    except ValueError:
        d = {"raw": out}
    ctx = ((d.get("hookSpecificOutput") or {}).get("additionalContext") or "")
    # The installed command hook emits policy rejections on stderr with exit 2.
    # run() merges stderr here: read THIS call's line on either supported output road.
    usage = [l for l in (out if code == 2 else ctx).splitlines() if l.startswith("USAGE")]
    return {"code": code, "out": out, "json": d, "usage": usage,
            "block": code == 2 or d.get("decision") == "block",
            "reason": out.strip() if code == 2 else d.get("reason") or ""}


def usage_cli(w, *args, stdin=None):
    return run([PY, w["hub"] / "tools" / "usage.py"] + list(args) + ["--hub", w["hub"]], w, stdin=stdin)


def settings(w, obj):
    write_json(w["hub"] / "usage-settings.json", obj)


def inbox_all_lines(w):
    try:
        text = io.open(str(w["hub"] / "INBOX.md"), encoding="utf-8").read()
    except OSError:
        return []
    return [l for l in text.splitlines() if "to: %s/all" % w["machine"].upper() in l]


def wait_for(fn, seconds=15.0):
    end = time.time() + seconds
    while time.time() < end:
        got = fn()
        if got:
            return got
        time.sleep(0.25)
    return fn()


def local_hm(d):
    """The tool's own word for a time: HH:MM today, else weekday + HH:MM."""
    d = d.astimezone()
    return d.strftime("%H:%M") if d.date() == now().date() else d.strftime("%a %H:%M")


# --------------------------------------------------------------------------
# G1 — rails (the fingerprint is taken before every case and compared after)
# --------------------------------------------------------------------------

def real_hub():
    try:
        with io.open(str(Path.home() / OLDER_SYNC / "machine.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return Path((d.get("roots") or {}).get("orchestrator") or HERE.parent), d.get("roots") or {}
    except Exception:
        return HERE.parent, {}


def sha(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def hook_entries(path):
    try:
        d = json.loads(io.open(str(path), encoding="utf-8").read())
    except (OSError, ValueError):
        return "unreadable"
    out = []
    for ev, rows in sorted((d.get("hooks") or {}).items()):
        for r in rows or []:
            for h in (r.get("hooks") or []):
                c = str(h.get("command") or "")
                if "effort.py" in c or "postman.py" in c or "usage.py" in c:
                    out.append((ev, c))
    return out


def fingerprint():
    hub, roots = real_hub()
    home = Path(roots.get("home") or Path.home())
    claude = Path(roots.get("claude") or home / ".claude")
    fp = {"hub": str(hub)}
    fp["hub_usage_files"] = sorted((p.name, sha(p)) for p in hub.glob("usage-*.json"))
    fp["hub_tools"] = sorted((p.name, sha(p)) for p in (hub / "tools").glob("*.py"))
    fp["hub_routines"] = sorted((p.name, sha(p)) for p in (hub / "routines").glob("*.md"))
    fp["settings_hooks"] = hook_entries(claude / "settings.json")
    fp["skills"] = sorted((str(p.relative_to(claude)), sha(p))
                          for p in (claude / "scheduled-tasks").glob("*/SKILL.md"))
    state = home / ".exocortex" / "usage"
    fp["usage_state"] = sorted(p.name for p in state.glob("*")) if state.is_dir() else None
    return fp


def marker_hits():
    """This gate's own content anywhere live: its fixture ids and its marker word."""
    hub, roots = real_hub()
    home = Path(roots.get("home") or Path.home())
    hits = []
    for sid in (SID_F, SID_S, SID_U, SID_V):
        for base in (Path(roots.get("claude") or home / ".claude") / "projects",):
            if base.is_dir():
                hits += [str(p) for p in base.glob("*/%s*" % sid)]
        eff = home / ".exocortex" / "effort" / "sessions" / ("%s.json" % sid)
        if eff.exists():
            hits.append(str(eff))
    for f in ("INBOX.md",):
        try:
            if MARK in io.open(str(hub / f), encoding="utf-8").read():
                hits.append(str(hub / f))
        except OSError:
            pass
    codex = Path(roots.get("codex") or home / ".codex") / "sessions"
    if codex.is_dir():
        hits += [str(p) for p in codex.rglob("*g145*")]
    grok = Path(roots.get("grok") or home / ".grok") / "sessions"
    if grok.is_dir():
        hits += [str(p) for p in grok.rglob("*g145*")]
    return hits


def case_g1(before, hits_before):
    start("G1", "rails: nothing outside the worlds was written")
    tmp = Path(tempfile.gettempdir()).resolve()
    hub, _roots = real_hub()
    check(str(ROOT.resolve()).startswith(str(tmp)), "the worlds sit under the system temp folder: %s" % ROOT)
    check(not str(ROOT.resolve()).startswith(str(hub.resolve())), "…and not under the live hub")
    after = fingerprint()
    for key in ("hub_usage_files", "hub_tools", "hub_routines", "settings_hooks", "skills", "usage_state"):
        check(before.get(key) == after.get(key), "live %s untouched (%s)" % (
            key.replace("_", " "), "%d entries" % len(after.get(key) or []) if isinstance(after.get(key), list)
            else after.get(key)))
        if key == "hub_usage_files" and before.get(key) != after.get(key):
            old, new = dict(before.get(key) or []), dict(after.get(key) or [])
            print("  G1 changed usage files: %s" % sorted(
                name for name in set(old) | set(new) if old.get(name) != new.get(name)))
    hits = [h for h in marker_hits() if h not in hits_before]
    check(not hits, "this gate's own fixture ids and marker word appear nowhere live: %s" % hits[:3])
    check(all(str(w["base"]).startswith(str(ROOT)) for w in WORLDS),
          "every world (%d) was made inside the gate's own root" % len(WORLDS))


# --------------------------------------------------------------------------
# G2 — thresholds, and the mutation that caches
# --------------------------------------------------------------------------

MUTANT = '''

# ---- MUTANT (gate-usage G2): a verdict remembered, never re-read ----
_real_evaluate = evaluate
def evaluate(hub, vendor, model=None, now=None, machine=None, cfg=None, **kw):
    cache = os.path.join(str(hub), "mutant-cache.json")
    got = read_json(cache, None)
    if isinstance(got, dict) and got.get("pause"):
        return got
    v = _real_evaluate(hub, vendor, model=model, now=now, machine=machine, cfg=cfg, **kw)
    write_atomic(cache, v)
    return v
'''


def g2_sequence(w, t):
    seen = {}
    for pct in (79, 80, 90, 79):
        _p, read_at = meter(w, [fable_week(pct)])
        seen.setdefault(pct, []).append((hook(w, SID_F, t), read_at))
    return seen


def case_g2():
    start("G2", "thresholds: 79 nothing · 80 WARN · 90 PAUSE · 79 nothing again")
    w = world("g2")
    t = window(w, SID_F, FABLE)
    seen = g2_sequence(w, t)
    h79, _ = seen[79][0]
    check(h79["code"] == 0 and not h79["usage"], "at 79 percent no USAGE line: %s" % h79["usage"])
    h80, at80 = seen[80][0]
    reset = now() + datetime.timedelta(days=2)
    want_reset = "resets %s" % local_hm(reset)
    line = (h80["usage"] or [""])[0]
    check(line.startswith("USAGE — Fable 80 percent of the week"), "at 80 the WARN line: %s" % line)
    check(want_reset in line and "read 1 min ago" in line and (" · %s" % LOGIN_W) in line,
          "…carrying the fixture's reset (%s), its read AGE and the login it belongs to (BQ-216; "
          "the read clock %s it said before)" % (want_reset, local_hm(at80)))
    h90, _ = seen[90][0]
    line = (h90["usage"] or [""])[0]
    check(line.startswith("USAGE PAUSE — Fable 90 percent") and "continue, or button up?" in line,
          "at 90 the PAUSE line — the question (BQ-179): %s" % line)
    h79b, _ = seen[79][1]
    check(not h79b["usage"], "back at 79 nothing — the verdict is read from the file every turn: %s"
          % h79b["usage"])
    # the mutation: the same check must go red against a tool that caches
    m = world("g2m")
    src = io.open(str(m["hub"] / "tools" / "usage.py"), encoding="utf-8").read()
    io.open(str(m["hub"] / "tools" / "usage.py"), "w", encoding="utf-8").write(src + MUTANT)
    tm = window(m, SID_F, FABLE)
    ms = g2_sequence(m, tm)
    caught = bool(ms[79][1][0]["usage"])
    check(caught, "a MUTANT that caches the last verdict prints PAUSE at 79 — the check above "
                  "would go red on it: %s" % ms[79][1][0]["usage"][:1])


# --------------------------------------------------------------------------
# G3 — stale
# --------------------------------------------------------------------------

def case_g3():
    start("G3", "stale: 31 min prints its age and no percent; 29 min prints the percent")
    w = world("g3")
    t = window(w, SID_F, FABLE)
    meter(w, [fable_week(85)], age_min=31)
    h = hook(w, SID_F, t)
    line = (h["usage"] or [""])[0]
    check("read 31 min ago" in line and "85" not in line,
          "31 min old: the age and no percent: %s" % line)
    meter(w, [fable_week(85)], age_min=29)
    h = hook(w, SID_F, t)
    line = (h["usage"] or [""])[0]
    check("Fable 85 percent" in line, "29 min old: the percent: %s" % line)
    meter(w, [fable_week(95)], age_min=45)
    h = hook(w, SID_F, t)
    line = (h["usage"] or [""])[0]
    check(line.startswith("USAGE PAUSE") and "45 min ago" in line and "95" not in line,
          "a stale reading over PAUSE HOLDS the pause (until a fresh read or its reset), "
          "without a remembered percent: %s" % line)
    meter(w, [fable_week(95, reset_days=-0.01)], age_min=45)
    h = hook(w, SID_F, t)
    check(not any(l.startswith("USAGE PAUSE") for l in h["usage"]),
          "…and lifts once its window has reset: %s" % h["usage"])


# ASSUMES: the backwards-account defect must never return: a meter file's
# login is NOT evidence of the account a window runs as. This is the opposite world.
def case_g13():
    start("G13", "no window identity: one provisional line and admission at 79, 80 and 90")
    w = world("g13")
    (w["home"] / ".claude.json").unlink()
    for pct in (79, 80, 90):
        sid = "f1450000-aaaa-4bbb-8ccc-0000000046%02d" % pct
        t = window(w, sid, FABLE, owner=None)
        meter(w, [fable_week(pct)])
        h = hook(w, sid, t)
        ctx = ((h["json"].get("hookSpecificOutput") or {}).get("additionalContext") or "")
        lines = h["usage"]
        check(h["code"] == 0 and not h["block"], "%s: unknown window admitted, exit 0" % pct)
        check(len(lines) == 1 and lines[0].startswith(
                  "USAGE · unknown · refresh (the login this window runs under cannot be read here")
              and lines[0].endswith("— call get_usage, then usage.py --write --vendor claude"),
              "%s: ONE provisional refresh line: %s" % (pct, lines))
        check(not PCT_RE.search(ctx) and not any(l.startswith(("USAGE —", "USAGE PAUSE",
                  "USAGE WARNING", "AUTO-PAUSE —")) or "HARD STOP" in l for l in ctx.splitlines()),
              "%s: no percent, WARN, PAUSE, STOP or auto-pause meter line" % pct)
        check(not notices(w) and not ap_notices(w) and not inbox_all_lines(w),
              "%s: no notice or pause letter from another login's meter" % pct)


# --------------------------------------------------------------------------
# G4 — the waiter
# --------------------------------------------------------------------------

def heartbeat(w):
    write_json(w["post"] / "heartbeat.json", {"when": iso(now()), "every": 60, "version": 1})


def waiter(w, sid, title, extra=()):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in dict(w["env"], CLAUDE_CODE_SESSION_ID=sid, CLAUDE_CODE_HOST_SESSION_ID="local_gate").items():
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    args = [PY, str(w["hub"] / "tools" / "mail.py"), "--wait", "NORTH/hub", "--hub", str(w["hub"]),
            "--title", title] + list(extra)
    return subprocess.Popen(args, cwd=str(w["hub"]), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8",
                            errors="replace")


def finish(proc, settle):
    time.sleep(settle)
    alive = proc.poll() is None
    if alive:
        proc.kill()
    out, _ = proc.communicate(timeout=15)
    return alive, out


def pending_letter(w, sid):
    line = "- %s · to: NORTH/hub · Exocortex · %s a question · answer it" % (
        datetime.date.today().isoformat(), MARK)
    write_json(w["post"] / "pending" / ("%s.json" % sid),
               {"session": sid, "updated": iso(now()),
                "items": [{"token": "pm-145145145145", "kind": "letter", "line": line,
                           "to": "NORTH/hub", "fyi": False, "wake": True}]})


def case_g4():
    start("G4", "the waiter: under PAUSE it refuses and asks the question; below PAUSE it arms")
    w = world("g4")
    heartbeat(w)
    window(w, SID_S, SONNET, title=TITLE_S)
    meter(w, [all_week(95)])
    began = time.time()
    proc = waiter(w, SID_S, TITLE_S)
    try:
        out, _ = proc.communicate(timeout=30)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        out, code = proc.communicate()[0], None
    check(code == 0 and "continue, or button up? (say either in your window) — under a usage PAUSE "
          "letters wait for a window's next turn start" in out and "USAGE PAUSE" in out
          and "retire" not in out,
          "under an all-models PAUSE a Sonnet window's --wait exits 0 asking the question (BQ-179): %s"
          % out.strip()[:160])
    check(time.time() - began < 25 and "waiting for" not in out, "…without arming (%.1f s)"
          % (time.time() - began))
    b = world("g4b")
    heartbeat(b)
    window(b, SID_S, SONNET, title=TITLE_S)
    meter(b, [all_week(50)])
    alive, out = finish(waiter(b, SID_S, TITLE_S), 4.0)
    check(alive and "waiting for NORTH/hub" in out, "below PAUSE it arms: %s" % out.strip()[:120])
    # an armed waiter under PAUSE: a letter that asks waits for the turn start
    c = world("g4c")
    heartbeat(c)
    window(c, SID_S, SONNET, title=TITLE_S)
    meter(c, [all_week(95)])
    proc = waiter(c, SID_S, TITLE_S, extra=["--force"])
    time.sleep(2.0)
    pending_letter(c, SID_S)
    alive, out = finish(proc, 6.0)
    check(alive and "FORCED" in out and "%s a question" % MARK not in out,
          "armed by the owner's --force under PAUSE, a letter that asks does NOT end the wait "
          "(it waits for the turn start): %s" % out.strip()[:160])
    check((c["post"] / "pending" / ("%s.json" % SID_S)).is_file(), "…and stays in the pending file")
    d = world("g4d")
    heartbeat(d)
    window(d, SID_S, SONNET, title=TITLE_S)
    meter(d, [all_week(50)])
    proc = waiter(d, SID_S, TITLE_S)
    time.sleep(2.0)
    pending_letter(d, SID_S)
    alive, out = finish(proc, 6.0)
    check(not alive and "%s a question" % MARK in out, "the control: below PAUSE the same letter ends the wait: %s"
          % out.strip()[-120:])


# --------------------------------------------------------------------------
# G5 — the routine step, and the hook's block
# --------------------------------------------------------------------------

SKILL = """---
name: gate-routine
description: %s a fixture routine
model: sonnet
---

You are a fixture routine.

Procedure:
1. Say hello.
2. Do the expensive thing.
""" % MARK

# A stub runner: it plays the model obeying the routine's numbered steps IN ORDER. A step
# whose text holds a `…` command runs that command; a step that says "if it exits non-zero …
# end" ends the run on a non-zero exit. Every other step is a "model line" and is counted.
RUNNER = r'''
import io, re, subprocess, sys
text = io.open(sys.argv[1], encoding="utf-8").read()
hub = sys.argv[2]
steps = [l for l in text.splitlines() if re.match(r"\s*\d+\.\s", l)]
model_lines = 0
for s in steps:
    m = re.search(r"`(python3? [^`]+)`", s)
    if m:
        cmd = m.group(1).split()
        cmd[0] = sys.executable
        cmd[1] = hub + "/" + cmd[1]
        code = subprocess.call(cmd + ["--hub", hub])
        if code != 0 and "exits non-zero" in s:
            break
        continue
    model_lines += 1
print("MODEL_LINES=%d" % model_lines)
'''


def case_g5():
    start("G5", "the routine step: --check's exit, a SKILL.md that ends at the step, the hook's block")
    w = world("g5")
    meter(w, [all_week(95)])
    code, out = usage_cli(w, "--check", "--vendor", "claude", "--model", "sonnet")
    check(code == 1 and "USAGE PAUSE" in out, "--check exits 1 under PAUSE and says the line: %s"
          % out.strip()[:120])
    meter(w, [all_week(50)])
    code, out = usage_cli(w, "--check", "--vendor", "claude", "--model", "sonnet")
    check(code == 0 and not out.strip(), "--check exits 0 and says nothing below PAUSE (%s)" % code)
    skill = w["base"] / "scheduled-tasks" / "gate-routine" / "SKILL.md"
    write(skill, SKILL)
    code, out = usage_cli(w, "--routine-step", str(skill), "--apply")
    text = io.open(str(skill), encoding="utf-8").read()
    steps = [l for l in text.splitlines() if re.match(r"\s*\d+\.\s", l)]
    check(code == 0 and steps and "BQ-145 usage check" in steps[0],
          "--routine-step --apply puts the step FIRST: %s" % (steps[0][:70] if steps else None))
    check("--model sonnet" in steps[0], "…naming the routine's own model from its frontmatter")
    write(w["base"] / "runner.py", RUNNER)
    meter(w, [all_week(95)])
    code, out = run([PY, w["base"] / "runner.py", skill, w["hub"]], w)
    check("MODEL_LINES=0" in out, "under PAUSE the stub run ends at the step: model counter 0 (%s)"
          % out.strip().splitlines()[-1:])
    meter(w, [all_week(50)])
    code, out = run([PY, w["base"] / "runner.py", skill, w["hub"]], w)
    check("MODEL_LINES=2" in out, "below PAUSE the run goes on to its two steps (%s)"
          % out.strip().splitlines()[-1:])
    code, _out = usage_cli(w, "--routine-step", str(skill), "--apply", "--remove")
    check("BQ-145" not in io.open(str(skill), encoding="utf-8").read(), "--remove takes the step out again")
    quiet = w["base"] / "scheduled-tasks" / "quiet" / "SKILL.md"
    write(quiet, SKILL.replace("You are a fixture routine.", "Do not run any command, ever."))
    code, out = usage_cli(w, "--routine-step", str(quiet), "--apply")
    check("SKIP" in out and "BQ-145" not in io.open(str(quiet), encoding="utf-8").read(),
          "a routine that runs no command by design is left alone and says why")
    # the hook: a SCHEDULED run's prompt is blocked before its first model call
    prompt = ('<scheduled-task name="gate-routine" file="%s">\nThis is an automated run of a '
              'scheduled task. %s</scheduled-task>' % (skill, MARK))
    meter(w, [all_week(95)])
    h = hook(w, "f1450000-aaaa-4bbb-8ccc-00000000r001", None, prompt=prompt)
    check(h["block"] and "USAGE PAUSE" in h["reason"] and "before its first model call" in h["reason"],
          "under PAUSE the effort hook BLOCKS the scheduled prompt: %s" % h["reason"][:120])
    meter(w, [fable_week(95)])
    h = hook(w, "f1450000-aaaa-4bbb-8ccc-00000000r002", None, prompt=prompt)
    check(not h["block"], "a Fable-week PAUSE does not block a Sonnet routine (its SKILL.md says sonnet)")
    meter(w, [all_week(50)])
    h = hook(w, "f1450000-aaaa-4bbb-8ccc-00000000r003", None, prompt=prompt)
    check(not h["block"] and h["code"] == 0, "below PAUSE the scheduled prompt goes through")


# --------------------------------------------------------------------------
# G6 — scope
# --------------------------------------------------------------------------

def case_g6():
    start("G6", "scope: a Fable-week PAUSE reaches Fable windows only; `all` and all-models reach both")
    w = world("g6")
    tf = window(w, SID_F, FABLE)
    ts = window(w, SID_S, SONNET)
    meter(w, [fable_week(93)])
    hf, hs = hook(w, SID_F, tf), hook(w, SID_S, ts)
    check(any(l.startswith("USAGE PAUSE — Fable 93") for l in hf["usage"]),
          "Fable-week 93: the Fable window hears PAUSE: %s" % hf["usage"][:1])
    check(not hs["usage"], "…the Sonnet window hears nothing: %s" % hs["usage"])
    settings(w, {"pause_scope": "all"})
    hf, hs = hook(w, SID_F, tf), hook(w, SID_S, ts)
    check(any(l.startswith("USAGE PAUSE") for l in hf["usage"]) and
          any(l.startswith("USAGE PAUSE") for l in hs["usage"]),
          "`pause_scope: all` (the word `pause everything`): both hear PAUSE")
    (w["hub"] / "usage-settings.json").unlink()
    meter(w, [all_week(91), fable_week(10)])
    hf, hs = hook(w, SID_F, tf), hook(w, SID_S, ts)
    check(any(l.startswith("USAGE PAUSE — all models 91") for l in hs["usage"]) and
          any(l.startswith("USAGE PAUSE") for l in hf["usage"]),
          "an all-models PAUSE reaches both: %s" % hs["usage"][:1])
    settings(w, {"manual_pause": True, "wait_refuse_models": ["claude-fable-"]})
    meter(w, [all_week(5)])
    hs = hook(w, SID_S, ts)
    check(any("manual pause" in l for l in hs["usage"]), "manual_pause: true stops at any percent")
    keep = json.loads(io.open(str(w["hub"] / "usage-settings.json"), encoding="utf-8").read())
    check(keep.get("wait_refuse_models") == ["claude-fable-"],
          "BQ-143's own key in the same file is read and never rewritten")
    (w["hub"] / "usage-settings.json").unlink()
    # the postman's Stop hook: no [arm] line for a window the PAUSE reaches
    sys.path.insert(0, str(w["hub"] / "tools"))
    code, out = run([PY, "-c", STOP_PROBE, str(w["hub"] / "tools"), str(w["post"]), str(ts)], w)
    check("ARM-SAID" in out and "NO-ARM" not in out.split("ARM-SAID")[0],
          "control: with no PAUSE the Stop hook asks the Sonnet window to arm (%s)" % out.strip()[:60])
    meter(w, [all_week(95)])
    code, out = run([PY, "-c", STOP_PROBE, str(w["hub"] / "tools"), str(w["post"]), str(ts)], w)
    check("NO-ARM" in out, "under an all-models PAUSE the postman's Stop hook summons nothing (%s)"
          % out.strip()[:80])
    meter(w, [fable_week(95)])
    code, out = run([PY, "-c", STOP_PROBE, str(w["hub"] / "tools"), str(w["post"]), str(ts)], w)
    check("ARM-SAID" in out, "…and a Fable-only PAUSE still lets a Sonnet window arm (%s)"
          % out.strip()[:60])
    sys.path.pop(0)


# The pass writes the holds row (claims -> holds); the Stop hook reads it. Driven in-process of a
# child so the probe reads the WORLD's record, never this machine's.
STOP_PROBE = r'''
import importlib.util, json, os, sys
tools, post, transcript = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("pm", os.path.join(tools, "postman.py"))
pm = importlib.util.module_from_spec(spec); spec.loader.exec_module(pm)
hub = os.path.dirname(tools)
sid = os.path.basename(transcript)[:-6]
try:
    os.unlink(os.path.join(post, "told", sid + ".json"))   # each probe is a first tell
except OSError:
    pass
claims = [{"arc": "Exocortex/Desk", "machine": "north", "session": sid, "title": "desk", "vendor": "claude"}]
pm.holds_reconcile(post, hub, claims, [], "north")
row = json.load(open(os.path.join(post, "holds", sid + ".json")))
said = pm._arm_tell(post, sid, "claude", {"transcript_path": transcript})
print(("ARM-SAID " if "[arm]" in (said or "") else "NO-ARM ") + json.dumps(row.get("usage_pause")))
'''


# --------------------------------------------------------------------------
# G7 — the Codex road
# --------------------------------------------------------------------------

def rollout(w, events):
    folder = w["home"] / ".codex" / "sessions" / "2026" / "09" / "24"
    path = folder / "rollout-2026-09-24T08-00-00-0199g145-0000-7000-8000-000000000145.jsonl"
    rows = [{"timestamp": zulu(now() - datetime.timedelta(minutes=30)), "type": "session_meta",
             "payload": {"id": "0199g145", "cwd": str(w["hub"])}},
            {"timestamp": zulu(now() - datetime.timedelta(minutes=30)), "type": "turn_context",
             "payload": {"model": "gpt-6-astra", "effort": "high"}}]
    rows.extend(events)
    write(path, "\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def token_event(minutes_ago, pct, reset_epoch, total):
    return {"timestamp": zulu(now() - datetime.timedelta(minutes=minutes_ago)), "type": "event_msg",
            "payload": {"type": "token_count",
                        "info": {"total_token_usage": {"input_tokens": total, "cached_input_tokens": total // 2,
                                                       "output_tokens": total // 100, "total_tokens": total}},
                        "rate_limits": {"primary": {"used_percent": pct, "window_minutes": 10080,
                                                    "resets_at": reset_epoch},
                                        "secondary": None, "plan_type": "pro"}}}


def case_g7():
    start("G7", "the Codex road: the LAST token_count's rate_limits; no rollouts, no file")
    w = world("g7")
    code, out = usage_cli(w, "--write", "--vendor", "codex")
    check("no rollouts" in out and not list(w["hub"].glob("usage-*-codex-*.json")),
          "no rollouts: one line and no file: %s" % out.strip()[:80])
    reset = int(time.time()) + 3 * 86400
    last_at = now() - datetime.timedelta(minutes=2)
    rollout(w, [token_event(20, 11.0, reset, 1000), token_event(10, 22.0, reset, 3000),
                token_event(2, 33.0, reset, 9000)])
    code, out = usage_cli(w, "--write", "--vendor", "codex")
    files = list(w["hub"].glob("usage-north-codex-*.json"))
    check(code == 0 and len(files) == 1, "one meter file: %s" % [f.name for f in files])
    d = json.loads(io.open(str(files[0]), encoding="utf-8").read()) if files else {}
    wins = d.get("windows") or [{}]
    want_reset = datetime.datetime.fromtimestamp(reset, datetime.timezone.utc).astimezone().replace(
        microsecond=0).isoformat()
    check(wins[0].get("percent") == 33.0 and wins[0].get("kind") == "week",
          "…its window is the LAST event's: %s percent, %s" % (wins[0].get("percent"), wins[0].get("kind")))
    check(wins[0].get("resets_at") == want_reset, "…resets_at in local ISO: %s" % wins[0].get("resets_at"))
    got_at = datetime.datetime.fromisoformat(str(d.get("read_at"))) if d.get("read_at") else None
    check(got_at is not None and abs((got_at - last_at).total_seconds()) < 90,
          "…read_at is the event's own time: %s" % d.get("read_at"))
    code, out = usage_cli(w, "--line", "--vendor", "codex")
    check(not out.strip(), "33 percent prints no Codex line")
    # the pulse's writer flag: --beat writes nothing until --install
    for f in w["hub"].glob("usage-*.json"):
        f.unlink()
    code, out = usage_cli(w, "--beat")
    check("writer off" in out and not list(w["hub"].glob("usage-*.json")),
          "--beat with no writer flag writes nothing and says so: %s" % out.strip()[:70])
    code, out = usage_cli(w, "--install")
    code, out = usage_cli(w, "--beat")
    check(list(w["hub"].glob("usage-north-codex-*.json")), "after --install the beat writes it: %s"
          % out.strip()[:90])
    code, out = usage_cli(w, "--uninstall")
    check(not (w["base"] / "state" / "pulse-writer.on").exists(), "--uninstall removes the writer flag")


# --------------------------------------------------------------------------
# G8 — the Grok road
# --------------------------------------------------------------------------

def grok_file(w, sid, ended, inp, cached, out, ticks):
    folder = w["home"] / ".grok" / "sessions" / "%2Fgate%2Fg145" / sid
    u = {"inputTokens": inp, "outputTokens": out, "cachedReadTokens": cached, "cacheCreationTokens": 0,
         "reasoningTokens": 0, "totalTokens": inp + out, "modelCalls": 3, "costUsdTicks": ticks}
    write_json(folder / "usage.json",
               {"sessionId": sid, "updatedAt": iso(ended), "session": dict(u, turnCount=1),
                "turns": [dict(u, turnNumber=1, endedAt=iso(ended), primaryModelId="grok-4.7-build",
                               modelUsage={"grok-4.7-build": u})]})


def case_g8():
    start("G8", "the Grok road: inside the window only; a spend limit makes a WARN")
    w = world("g8")
    grok_file(w, "g145-inside", now() - datetime.timedelta(hours=1), 1000, 400, 100, 5000000000)
    grok_file(w, "g145-outside", now() - datetime.timedelta(days=9), 777777, 7777, 7777, 99000000000)
    code, out = usage_cli(w, "--write", "--vendor", "grok")
    files = list(w["hub"].glob("usage-north-grok-*.json"))
    d = json.loads(io.open(str(files[0]), encoding="utf-8").read()) if files else {}
    acc = ((d.get("accounting") or {}).get("last_24h") or {})
    toks = (acc.get("tokens_by_model") or {}).get("grok-4.7-build") or {}
    check(toks == {"fresh": 600, "cached": 400, "out": 100},
          "the inside file's tokens alone (fresh = input - cached): %s" % toks)
    check(d.get("meter") == "not readable — accounting only", "meter: %s" % d.get("meter"))
    check(abs(float((d.get("spend") or {}).get("spent") or 0) - 0.5) < 1e-9,
          "7-day spend $0.50 from 5,000,000,000 ticks at the vendor's 1e10 per USD: %s"
          % (d.get("spend") or {}).get("spent"))
    code, out = usage_cli(w, "--line", "--vendor", "grok")
    check(not out.strip(), "no limit set: no Grok line")
    settings(w, {"per_vendor": {"grok": {"week_spend_limit_usd": 0.6}}})
    code, out = usage_cli(w, "--write", "--vendor", "grok")
    code, out = usage_cli(w, "--line", "--vendor", "grok")
    check("USAGE — Grok spend (7 days) 83 percent ($0.50 of $0.6)" in out,
          "limit $0.60: the spend WARN fires (83 percent): %s" % out.strip())
    settings(w, {"per_vendor": {"grok": {"week_spend_limit_usd": 0.63}}})
    code, out = usage_cli(w, "--write", "--vendor", "grok")
    code, out = usage_cli(w, "--line", "--vendor", "grok")
    check("79 percent" not in out and not out.strip(), "limit $0.63 (79 percent): no line — %s" % out.strip())


# --------------------------------------------------------------------------
# G9 — the accounting
# --------------------------------------------------------------------------

def rec(sid, req, model, when, inp, cw, cached, out, block="text"):
    return {"parentUuid": "x", "isSidechain": False, "type": "assistant", "requestId": req,
            "message": {"role": "assistant", "model": model, "id": "msg-" + req,
                        "content": [{"type": block}],
                        "usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                                  "cache_read_input_tokens": cached, "output_tokens": out}},
            "uuid": "u-%s-%s" % (req, block), "timestamp": zulu(when), "sessionId": sid}


# THE HAND SUM (three sessions, fresh in = input + cache write):
#   S1 Fable : r1 (two records — thinking + text — ONE request: in 100, cw 1000, cached 50000, out 200)
#              r2 (in 10, cw 0, cached 60000, out 300)          -> 2 calls · 1110 · 110000 · 500
#   S2 Sonnet: r3 (in 5, cw 500, cached 20000, out 50)          -> 1 call  ·  505 ·  20000 ·  50
#   S3 Fable : r4 (in 1, cached 1000, out 7) · r5 (in 2, cached 3000, out 8)
#                                                                -> 2 calls ·    3 ·   4000 ·  15
#   TOTAL                                                        -> 5 calls · 1618 · 134000 · 565
#   RAW (r1 counted twice): 6 calls · 2718 · 184000 · 765
def case_g9():
    start("G9", "the accounting: a repeated requestId once; the hand sum; --by hour on the local clock")
    w = world("g9")
    proj = w["home"] / ".claude" / "projects" / "-gate-acc"
    t1 = now() - datetime.timedelta(hours=3, minutes=10)
    t2 = now() - datetime.timedelta(hours=1, minutes=10)
    s1 = [rec("s1", "r1", FABLE, t1, 100, 1000, 50000, 200, "thinking"),
          rec("s1", "r1", FABLE, t1, 100, 1000, 50000, 200, "text"),
          rec("s1", "r2", FABLE, t2, 10, 0, 60000, 300)]
    s2 = [rec("s2", "r3", SONNET, t1, 5, 500, 20000, 50)]
    s3 = [rec("s3", "r4", FABLE, t2, 1, 0, 1000, 7), rec("s3", "r5", FABLE, t2, 2, 0, 3000, 8)]
    for sid, rows in (("g145s1", s1), ("g145s2", s2), ("g145s3", s3)):
        write(proj / ("%s.jsonl" % sid), "\n".join(json.dumps(r) for r in rows) + "\n")
        write_json(proj / sid / "custom-title.json", {"customTitle": "ACT — Gate/%s: %s" % (sid, MARK)})

    def total(out):
        m = re.search(r"^TOTAL\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", out, re.M)
        return tuple(int(x.replace(",", "")) for x in m.groups()) if m else None

    code, out = usage_cli(w, "--report", "--hours", "6", "--vendor", "claude")
    check(total(out) == (5, 1618, 134000, 565), "TOTAL matches the hand sum 5 · 1,618 · 134,000 · 565: %s"
          % (total(out),))
    check(all(len(l) <= 88 for l in out.splitlines()), "every line fits 88 columns")
    check(sum(1 for l in out.splitlines() if l.startswith("Gate/g145")) == 3, "one row per session")
    code, out = usage_cli(w, "--report", "--hours", "6", "--vendor", "claude", "--raw")
    check(total(out) == (6, 2718, 184000, 765), "--raw counts every record (r1 twice): %s" % (total(out),))
    code, out = usage_cli(w, "--report", "--hours", "6", "--vendor", "claude", "--by", "hour")
    h1 = t1.astimezone().strftime("%Y-%m-%d %H:00")
    h2 = t2.astimezone().strftime("%Y-%m-%d %H:00")
    rows = [l for l in out.splitlines() if l[:4].isdigit()]
    check(any(l.startswith(h1) for l in rows) and any(l.startswith(h2) for l in rows),
          "--by hour buckets by the LOCAL clock: %s and %s" % (h1, h2))
    code, out = usage_cli(w, "--report", "--hours", "2", "--vendor", "claude")
    check(total(out) == (3, 13, 64000, 315), "--hours 2 keeps only the later hour: %s" % (total(out),))


# --------------------------------------------------------------------------
# G10 — announce once
# --------------------------------------------------------------------------

def case_g10():
    start("G10", "announce-once: two PAUSE turn starts send ONE <MACHINE>/all letter")
    w = world("g10")
    t = window(w, SID_F, FABLE)
    meter(w, [fable_week(96)])
    first = hook(w, SID_F, t)
    got = wait_for(lambda: inbox_all_lines(w), 20.0)
    second = hook(w, SID_F, t)
    time.sleep(3.0)
    lines = inbox_all_lines(w)
    check(first["usage"] and second["usage"], "both turn starts print the PAUSE line")
    check(len(lines) == 1, "ONE letter to NORTH/all in the INBOX (%d): %s" % (len(lines), lines[:1]))
    check(lines and "USAGE PAUSE — Fable 96 percent" in lines[0], "…carrying the PAUSE line")
    d = json.loads(io.open(str(next(w["hub"].glob("usage-north-claude-*.json"))), encoding="utf-8").read())
    check(d.get("pause_announced_key") and d.get("pause_announced_at"),
          "the meter file carries pause_announced_at: %s" % d.get("pause_announced_at"))
    meter(w, [fable_week(96, reset_days=3.0)])          # a NEW onset (a later reset) — one more letter
    hook(w, SID_F, t)
    got = wait_for(lambda: len(inbox_all_lines(w)) >= 2, 20.0)
    check(len(inbox_all_lines(w)) == 2, "a new onset (the next week) sends one more: %d"
          % len(inbox_all_lines(w)))


# --------------------------------------------------------------------------
# G11 — the tree
# --------------------------------------------------------------------------

def render(w):
    out_path = w["base"] / "out" / "tree.html"
    env = {"COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_OUT": str(out_path),
           "COLLECT_OPENERS_VOLUMES": str(w["base"] / "vol"), "COLLECT_OPENERS_WORK": str(w["base"] / "work"),
           "COLLECT_OPENERS_ENGINE": str(w["home"] / OLDER_SYNC)}
    code, out = run([PY, w["hub"] / "tools" / "collect-openers.py", "--html"], w, env=env, timeout=600)
    if code != 0:
        return "", out
    return io.open(str(out_path), encoding="utf-8").read(), out


def band(html, machine, vendor):
    m = re.search(r'<a class="ub ([a-z]+)"[^>]*><b>%s · %s</b>.*?</a>' % (machine, vendor), html)
    return (m.group(1), m.group(0)) if m else (None, "")


def case_g11():
    start("G11", "the tree: amber at 85, red at 91, grey when stale, Grok in words")
    w = world("g11")
    _p, at = meter(w, [fable_week(85)])
    meter(w, [all_week(91)], machine="south", login="wren@example.test")
    meter(w, [win("Codex", 40.0, "week")], vendor="codex", login="default", age_min=90)
    meter(w, [], vendor="grok", login="default", meter_word="not readable — accounting only",
          extra={"accounting": {"last_24h": {"tokens_by_model": {"grok-4.7-build":
                                                                  {"fresh": 600, "cached": 400, "out": 100}}}}})
    html, out = render(w)
    check(bool(html), "the tree renders in the world (%s)" % out.strip()[-120:])
    cls, a = band(html, "NORTH", "Claude")
    check(cls == "warn" and ("read %s" % local_hm(at)) in a,
          "85 percent: an amber band with its read time: %s" % re.sub("<[^>]+>", " ", a)[:120])
    cls, a = band(html, "SOUTH", "Claude")
    check(cls == "pause", "91 percent: a red band (%s)" % cls)
    cls, a = band(html, "NORTH", "Codex")
    check(cls == "stale" and "read 90 min ago" in a, "90 min old: grey, with its age: %s"
          % re.sub("<[^>]+>", " ", a)[:120])
    cls, a = band(html, "NORTH", "Grok")
    check(cls is not None and "not readable — accounting only" in a,
          "Grok's band reads 'not readable — accounting only': %s" % re.sub("<[^>]+>", " ", a)[:120])
    check('href="usage-north-claude-' in html, "a band is a link to the file it was drawn from")


# --------------------------------------------------------------------------
# G12 — the open watch
# --------------------------------------------------------------------------

def watcher(w, sid, title, every, log, extra=(), recheck="1"):
    """`mail.py --watch` as a window arms it (Monitor road), its stdout into a file that is read
    while it runs — on any OS. EXO_USAGE_RECHECK_S is the seam that shortens mail.py's own minute
    so a flip is answered in a second; the watch is ended by the case, never left behind."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k, v in dict(w["env"], CLAUDE_CODE_SESSION_ID=sid, CLAUDE_CODE_HOST_SESSION_ID="local_gate",
                     EXO_USAGE_RECHECK_S=recheck).items():
        env.pop(k, None) if v is None else env.__setitem__(k, str(v))
    args = [PY, str(w["hub"] / "tools" / "mail.py"), "--watch", "NORTH/hub", "--hub", str(w["hub"]),
            "--title", title, "--every", str(every), "--no-pull"] + list(extra)
    handle = io.open(str(log), "w", encoding="utf-8")
    proc = subprocess.Popen(args, cwd=str(w["hub"]), env=env, stdout=handle,
                            stderr=subprocess.STDOUT)
    return proc, handle


def watch_stop(proc, handle):
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        handle.close()


def text_of(path):
    try:
        return io.open(str(path), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def ask_letter(w, words):
    line = "- %s · to: NORTH/hub · Exocortex · %s %s · answer it" % (
        datetime.date.today().isoformat(), MARK, words)
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return line


RECHECK_PROBE = r'''
import importlib.util, sys
spec = importlib.util.spec_from_file_location("m", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print("RECHECK=%s CONST=%s" % (mod.usage_recheck_s(), mod.USAGE_RECHECK_S))
'''


def case_g12():
    start("G12", "the open watch (BQ-173): a PAUSE reaches a --watch armed before it")
    w = world("g12")
    heartbeat(w)
    window(w, SID_S, SONNET, title=TITLE_S)
    meter(w, [all_week(50)])
    log = w["base"] / "out" / "watch-a.log"
    proc, handle = watcher(w, SID_S, TITLE_S, 30, log)
    try:
        armed = wait_for(lambda: "watching INBOX.md for to: NORTH/hub" in text_of(log), 15)
        check(armed and proc.poll() is None,
              "below PAUSE a Sonnet window's --watch arms and listens: %s" % text_of(log).strip()[:120])
        meter(w, [all_week(95)])
        ask_letter(w, "an ask sent during the pause")
        flipped = time.time()
        ended = wait_for(lambda: proc.poll() is not None, 15)
        took = time.time() - flipped
        out = text_of(log)
        check(ended and proc.returncode == 0 and took < 10,
              "the all-models meter flips to PAUSE and the watch ends, exit 0, %.1f s later — long "
              "before its next poll at 30 s: the meter is re-read on its own clock" % took)
        said = [l for l in out.splitlines() if "watch ended" in l]
        check(len(said) == 1 and said[0].startswith("USAGE PAUSE — all models 95 percent")
              and "letters now wait for this window's next turn start" in said[0],
              "…in ONE line that names the PAUSE: %s" % said)
        check("MAIL for" not in out and "an ask sent during the pause" not in out,
              "…and the letter that asks was never printed into the window")
    finally:
        watch_stop(proc, handle)
    b = world("g12b")
    heartbeat(b)
    window(b, SID_S, SONNET, title=TITLE_S)
    meter(b, [all_week(50)])
    logb = b["base"] / "out" / "watch-b.log"
    proc, handle = watcher(b, SID_S, TITLE_S, 2, logb)
    try:
        wait_for(lambda: "watching INBOX.md" in text_of(logb), 15)
        meter(b, [fable_week(95)])
        time.sleep(3.5)                            # three re-reads at the seam's one second
        check(proc.poll() is None and "watch ended" not in text_of(logb),
              "a Fable-week PAUSE leaves a Sonnet window's watch listening across three re-reads: %s"
              % text_of(logb).strip()[-120:])
        ask_letter(b, "an ask the sonnet watch still carries")
        got = wait_for(lambda: "MAIL for NORTH/hub" in text_of(logb), 15)
        check(got and "an ask the sonnet watch still carries" in text_of(logb),
              "…and it still prints a letter that asks")
    finally:
        watch_stop(proc, handle)
    # the teeth: a watch that never re-reads the meter keeps listening past the same flip
    m = world("g12m")
    heartbeat(m)
    window(m, SID_S, SONNET, title=TITLE_S)
    meter(m, [all_week(50)])
    src = io.open(str(m["hub"] / "tools" / "mail.py"), encoding="utf-8").read()
    mutant = src.replace("paused = usage_pause(hub, _WAIT_MODEL[0])", "paused = ''", 1)
    io.open(str(m["hub"] / "tools" / "mail.py"), "w", encoding="utf-8", newline="\n").write(mutant)
    logm = m["base"] / "out" / "watch-m.log"
    proc, handle = watcher(m, SID_S, TITLE_S, 30, logm)
    try:
        wait_for(lambda: "watching INBOX.md" in text_of(logm), 15)
        meter(m, [all_week(95)])
        time.sleep(4.0)
        check(mutant != src and proc.poll() is None,
              "a MUTANT --watch that never re-reads the meter is still listening 4 s after the flip "
              "— the check above would go red on it")
    finally:
        watch_stop(proc, handle)
    code, out = run([PY, "-c", RECHECK_PROBE, str(w["hub"] / "tools" / "mail.py")], w,
                    env={"EXO_USAGE_RECHECK_S": None})
    check("RECHECK=60" in out and "CONST=60" in out,
          "in service the cadence is mail.py's own minute, --wait's and --watch's alike: %s"
          % out.strip()[-60:])
    code, out = run([PY, "-c", RECHECK_PROBE, str(w["hub"] / "tools" / "mail.py")], w,
                    env={"EXO_USAGE_RECHECK_S": "0"})
    check("RECHECK=60" in out, "…and a seam that is not a positive number is the minute: %s"
          % out.strip()[-60:])


# --------------------------------------------------------------------------
# G-A1 … G-A9 — THE GATE ASKS
# --------------------------------------------------------------------------

EVAL_PROBE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("u", sys.argv[1])
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
v = u.evaluate(sys.argv[2], "claude", model=(sys.argv[3] if len(sys.argv) > 3 else None))
print(json.dumps({"level": v["level"], "pause": v["pause"], "lines": v["lines"],
                  "facts": u.pause_facts(sys.argv[2], "claude")}, ensure_ascii=False))
'''

PICTURE_PROBE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("u", sys.argv[1])
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
print(json.dumps({"bands": u.bands_html(sys.argv[2]), "chip": u.chip_html(sys.argv[2], machine="north")},
                 ensure_ascii=False))
'''


def probe(w, code_text, *extra):
    code, out = run([PY, "-c", code_text, w["hub"] / "tools" / "usage.py", w["hub"]] + list(extra), w)
    for line in reversed(out.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {"raw": out}


def notices(w):
    """The usage gate's own notices through the --notify seam: [title, subtitle, body] each.
    The postman's own notices (title 'Exocortex') are not this tool's and are left out."""
    try:
        text = io.open(str(w["base"] / "notify-calls.jsonl"), encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        try:
            got = json.loads(line)
        except ValueError:
            continue
        if isinstance(got, list) and got and got[0] == GATE_TITLE:
            out.append((got + ["", "", ""])[:3])
    return out


def settings_now(w):
    try:
        return json.loads(io.open(str(w["hub"] / "usage-settings.json"), encoding="utf-8").read())
    except (OSError, ValueError):
        return None


def meter_now(w, vendor="claude"):
    got = sorted(w["hub"].glob("usage-north-%s-*.json" % vendor))
    return json.loads(io.open(str(got[0]), encoding="utf-8").read()) if got else {}


def lines_of(out):
    return [l for l in out.strip().splitlines() if l.strip()]


def case_a1():
    start("G-A1", "the gate asks: a crossing of 90 raises ONE notice and ONE letter, both the question")
    w = world("a1")
    t = window(w, SID_F, FABLE)
    meter(w, [fable_week(91)], spend=SPEND)
    first = hook(w, SID_F, t)
    wait_for(lambda: notices(w) and inbox_all_lines(w), 20.0)
    time.sleep(1.0)
    ns, letters = notices(w), inbox_all_lines(w)
    check(len(ns) == 1, "ONE desktop notice through the --notify seam (%d)" % len(ns))
    title, sub, body = ns[0] if ns else ("", "", "")
    check(title == GATE_TITLE, "…titled %r: %r" % (GATE_TITLE, title))
    check(body == QUESTION, "…its body the question — both words and the dollars: %s" % body)
    check(sub.startswith("Fable 91 percent · the week resets "), "…its subtitle the meter and its reset: %s" % sub)
    check(len(letters) == 1, "ONE letter to NORTH/all (%d)" % len(letters))
    letter = letters[0] if letters else ""
    check(QUESTION in letter, "…whose text names both words and the dollars: %s" % letter[:170])
    check(letter.rstrip().endswith("· answer in your window: continue, or button up"),
          "…and whose action is the question: %s" % letter[-60:])
    line = (first["usage"] or [""])[0]
    check(line.startswith("USAGE PAUSE — Fable 91 percent · the week resets ")
          and (" · %s · read " % QUESTION) in line,
          "the turn-start line is the question: %s" % line)
    check(line.endswith(" · " + SESSION) and SESSION not in letter and SESSION not in body,
          "…and ends with what a session does with either word — the letter and the notice do not")
    second = hook(w, SID_F, t)
    code, out = usage_cli(w, "--announce", "--vendor", "claude")
    time.sleep(3.0)
    check(second["usage"][:1] and second["usage"][0].startswith("USAGE PAUSE — Fable 91 percent")
          and out.startswith("usage: already"),
          "twice-never: the next turn start still says the line, and the hub's --announce says "
          "'already': %s" % out.strip()[:60])
    check(len(notices(w)) == 1 and len(inbox_all_lines(w)) == 1,
          "…and nothing more is raised or sent (%d notice, %d letter)"
          % (len(notices(w)), len(inbox_all_lines(w))))
    meter(w, [fable_week(91, reset_days=3.0)], spend=SPEND)      # the next reset: a new key
    hook(w, SID_F, t)
    wait_for(lambda: len(notices(w)) >= 2 and len(inbox_all_lines(w)) >= 2, 20.0)
    time.sleep(2.0)
    check(len(notices(w)) == 2 and len(inbox_all_lines(w)) == 2,
          "a new key (the next reset) asks again, once: %d notices, %d letters"
          % (len(notices(w)), len(inbox_all_lines(w))))
    # R2's bounds: a notifier that takes its time never holds a turn start, and one that fails
    # never stops the line or the letter
    s = world("a1s")
    write(s["base"] / "notify.py", SLOW_STUB)
    ts = window(s, SID_F, FABLE)
    meter(s, [fable_week(91)], spend=SPEND)
    began = time.time()
    h = hook(s, SID_F, ts)
    took = time.time() - began
    check(h["usage"][:1] and h["usage"][0].startswith("USAGE PAUSE") and took < 4.0,
          "a notifier that takes 6 s: the turn start still says the line in %.1f s (the hook's budget "
          "is 5) — the notice is fire-and-forget" % took)
    check(wait_for(lambda: notices(s), 20.0) and len(notices(s)) == 1,
          "…and the notice still lands, once, after the turn start is done")
    f = world("a1f")
    write(f["base"] / "notify.py", FAIL_STUB)
    tf = window(f, SID_F, FABLE)
    meter(f, [fable_week(91)], spend=SPEND)
    h = hook(f, SID_F, tf)
    got = wait_for(lambda: inbox_all_lines(f), 20.0)
    check(h["code"] == 0 and h["usage"][:1] and h["usage"][0].startswith("USAGE PAUSE") and got,
          "a notifier that fails: the line is said and the letter still goes (%d)" % len(inbox_all_lines(f)))
    meter(f, [fable_week(91, reset_days=3.0)], spend=SPEND)
    code, out = usage_cli(f, "--announce", "--vendor", "claude")
    check(code == 0 and out.startswith("usage: sent · no ping: "),
          "…and the hub's --announce says so in its own line, exit 0: %s" % out.strip()[:70])


def case_a2():
    start("G-A2", "the WARN crossing: ONE notice, information only, NO letter, never twice")
    w = world("a2")
    t = window(w, SID_F, FABLE)
    reset = now() + datetime.timedelta(days=2)
    meter(w, [fable_week(82, at=reset)], spend=SPEND)
    h = hook(w, SID_F, t)
    wait_for(lambda: notices(w), 20.0)
    time.sleep(3.0)
    ns = notices(w)
    line = (h["usage"] or [""])[0]
    check(len(ns) == 1, "at 82 ONE notice through the --notify seam (%d)" % len(ns))
    check(ns and ns[0][2] == line and line.startswith("USAGE — Fable 82 percent of the week"),
          "…its body the WARN line itself: %s" % (ns[0][2] if ns else None))
    check(not inbox_all_lines(w), "…and NO letter: %s" % inbox_all_lines(w)[:1])
    d = meter_now(w)
    check(d.get("warn_announced_key") == "Weekly · Fable|%s" % iso(reset) and d.get("warn_announced_at")
          and not d.get("pause_announced_key"),
          "the meter file carries warn_announced_key/_at beside (not in place of) the pause keys: %s"
          % d.get("warn_announced_key"))
    hook(w, SID_F, t)
    code, out = usage_cli(w, "--announce", "--vendor", "claude")
    time.sleep(3.0)
    check(len(notices(w)) == 1 and not inbox_all_lines(w) and out.startswith("usage: already"),
          "twice-never: a second turn start and --announce raise nothing (%d; %s)"
          % (len(notices(w)), out.strip()[:40]))
    meter(w, [fable_week(91, at=reset)], spend=SPEND,
          extra={"warn_announced_key": d.get("warn_announced_key"),
                 "warn_announced_at": d.get("warn_announced_at")})
    hook(w, SID_F, t)
    wait_for(lambda: len(notices(w)) >= 2 and inbox_all_lines(w), 20.0)
    time.sleep(1.0)
    ns = notices(w)
    check(len(ns) == 2 and ns[1][2] == QUESTION and len(inbox_all_lines(w)) == 1,
          "the same window then crossing 90 still asks — one notice, one letter (%d, %d)"
          % (len(ns), len(inbox_all_lines(w))))


SKILL_S = SKILL                                 # model: sonnet — reached by an all-models PAUSE


def case_a3():
    start("G-A3", "«continue»: the override is written, the dollars first; every road carries on")
    w = world("a3")
    heartbeat(w)
    ts = window(w, SID_S, SONNET, title=TITLE_S)
    reset = now() + datetime.timedelta(days=2)
    meter(w, [all_week(91, at=reset)], spend=SPEND)
    skill = w["base"] / "scheduled-tasks" / "gate-routine" / "SKILL.md"
    write(skill, SKILL_S)
    prompt = ('<scheduled-task name="gate-routine" file="%s">\nThis is an automated run of a '
              'scheduled task. %s</scheduled-task>' % (skill, MARK))
    blocked = hook(w, "f1450000-aaaa-4bbb-8ccc-00000000a301", None, prompt=prompt)
    check(blocked["block"], "the control: before the word, the scheduled prompt is blocked")
    began = now()
    code, out = usage_cli(w, "--continue", "--vendor", "claude", "--by", TITLE_S)
    said = lines_of(out)
    check(code == 0 and said[:1] == ["extra usage so far $10.45 of $40 this month"],
          "--continue exits 0 and prints the dollars line FIRST: %s" % said[:1])
    want = ("CONTINUED past the pause line on Wren's word · all models 91 percent of the week · until %s "
            "· by %s at " % (local_hm(reset), TITLE_S))
    check(len(said) == 2 and said[1].startswith(want),
          "…then the state line: %s" % said[1:2])
    ov = (settings_now(w) or {}).get("overrides") or []
    o = ov[0] if ov else {}
    check(len(ov) == 1 and sorted(o) == sorted(["vendor", "window_label", "resets_at", "until", "by", "at",
                                                "percent_at", "spend_at"]),
          "ONE override with every field: %s" % sorted(o))
    at = datetime.datetime.fromisoformat(o["at"]) if o.get("at") else None
    check(o.get("vendor") == "claude" and o.get("window_label") == "Weekly · all models"
          and o.get("resets_at") == iso(reset) and o.get("until") == iso(reset.astimezone()) and o.get("by") == TITLE_S
          and o.get("percent_at") == 91 and at is not None and abs((at - began).total_seconds()) < 120
          and o.get("spend_at") == {"spent": "10.45", "limit": "40.00", "currency": "USD", "enabled": True},
          "…the window, its reset as `until`, who, when, the percent and the dollars at the word: %s"
          % json.dumps(o, ensure_ascii=False)[:200])
    v = probe(w, EVAL_PROBE)
    line = (v.get("lines") or [""])[0]
    check(v.get("level") == "continued" and v.get("pause") is False,
          "the next evaluate() is level `continued`, pause False: %s %s" % (v.get("level"), v.get("pause")))
    check(line.startswith("USAGE — CONTINUED past the pause line (Wren, %s, at 91 percent) · all models 91 "
                          "percent of the week, resets %s · extra usage $10.45 of $40 · read "
                          % (local_hm(at) if at else "?", local_hm(reset))),
          "…one line, R4's: %s" % line)
    check(v.get("facts") is None, "…and the postman's pause facts hold nothing (%s)" % v.get("facts"))
    code, out = usage_cli(w, "--check", "--vendor", "claude", "--model", "sonnet")
    check(code == 0 and not out.strip(), "--check exits 0 and says nothing (%s)" % code)
    h = hook(w, SID_S, ts)
    check(len(h["usage"]) == 1 and h["usage"][0].split(" · read ")[0] == line.split(" · read ")[0],
          "a Sonnet window's turn start hears the CONTINUED line: %s" % h["usage"])
    alive, out = finish(waiter(w, SID_S, TITLE_S), 4.0)
    check(alive and "waiting for NORTH/hub" in out, "the waiter arms: %s" % out.strip()[:100])
    h = hook(w, "f1450000-aaaa-4bbb-8ccc-00000000a302", None, prompt=prompt)
    check(not h["block"] and h["code"] == 0, "the same scheduled prompt is NOT blocked after the word")


def case_a4():
    start("G-A4", "«continue» with nothing to continue past: the refusal, exit 1, the file untouched")
    w = world("a4")
    settings(w, {"wait_refuse_models": ["claude-fable-"]})
    before = (w["hub"] / "usage-settings.json").read_bytes()
    meter(w, [all_week(85)], spend=SPEND)
    code, out = usage_cli(w, "--continue", "--vendor", "claude", "--by", TITLE_S)
    said = lines_of(out)
    check(code == 1 and len(said) == 1
          and said[0].startswith("nothing to continue past — USAGE — all models 85 percent of the week"),
          "at WARN: one line naming the WARN line, exit 1: %s" % said)
    meter(w, [all_week(40)], spend=SPEND)
    code, out = usage_cli(w, "--continue", "--vendor", "claude")
    said = lines_of(out)
    check(code == 1 and said[:1] and said[0].startswith("nothing to continue past — USAGE — all models 40%"),
          "below WARN: the meter in one line, exit 1: %s" % said)
    for f in w["hub"].glob("usage-*-claude-*.json"):
        f.unlink()
    code, out = usage_cli(w, "--continue", "--vendor", "claude")
    check(code == 1 and out.strip() == ("nothing to continue past — USAGE · %s%s · refresh (no "
                                        "reading for this login on this machine yet) — call "
                                        "get_usage, then usage.py --write --vendor claude"
                                        % (LOGIN_W, CLI)),
          "no meter: %s" % out.strip())
    check((w["hub"] / "usage-settings.json").read_bytes() == before,
          "usage-settings.json is byte for byte as it was (BQ-143's own key in it)")


def case_a5():
    start("G-A5", "expiry: an override past its `until` is pruned, and its one line said once")
    w = world("a5")
    t = window(w, SID_F, FABLE)
    old_reset = now() - datetime.timedelta(hours=1)
    given = now() - datetime.timedelta(days=2, hours=1)
    settings(w, {"wait_refuse_models": ["claude-fable-"],
                 "overrides": [{"vendor": "claude", "window_label": "Weekly · all models",
                                "resets_at": iso(old_reset), "until": iso(old_reset), "by": TITLE_S,
                                "at": iso(given), "percent_at": 91.0, "spend_at": None}]})
    meter(w, [all_week(12, reset_days=7.0)], spend=SPEND)          # the new week, after the reset
    h = hook(w, SID_F, t)
    want = "USAGE — the continue of %s expired with the reset" % local_hm(given)
    check(h["usage"] == [want], "the next turn start says it once: %s" % h["usage"])
    s = settings_now(w) or {}
    check(s.get("overrides") == [] and s.get("wait_refuse_models") == ["claude-fable-"],
          "…the override is pruned from the file and the other key kept: %s" % s)
    d = meter_now(w)
    check((d.get("continue_expired") or {}).get("key") and
          d.get("continue_expired_said_key") == (d.get("continue_expired") or {}).get("key"),
          "the meter file carries the note and its said key (twice-never)")
    h = hook(w, SID_F, t)
    check(not h["usage"], "…and the turn after says nothing: %s" % h["usage"])
    b = world("a5b")
    tb = window(b, SID_F, FABLE)
    reset = now() + datetime.timedelta(days=2)
    until = now() - datetime.timedelta(minutes=5)
    given = now() - datetime.timedelta(hours=3)
    settings(b, {"overrides": [{"vendor": "claude", "window_label": "Weekly \u00b7 all models",
                                "resets_at": iso(reset), "until": iso(until), "by": TITLE_S,
                                "at": iso(given), "percent_at": 91.0, "spend_at": None}]})
    meter(b, [all_week(93, at=reset)], spend=SPEND)
    h = hook(b, SID_F, tb)
    check(len(h["usage"]) == 2 and h["usage"][0] == "USAGE — the continue of %s expired at %s, as it was given"
          % (local_hm(given), local_hm(until))
          and h["usage"][1].startswith("USAGE PAUSE — all models 93 percent"),
          "an --until that has come while the window is still over the line: the expiry once, then "
          "the PAUSE again: %s" % h["usage"])
    code, out = usage_cli(b, "--check", "--vendor", "claude")
    check(code == 1 and (settings_now(b) or {}).get("overrides") == [],
          "…pause True again (--check exits 1) and the override is gone")
    h = hook(b, SID_F, tb)
    check(len(h["usage"]) == 1 and h["usage"][0].startswith("USAGE PAUSE"),
          "…the expiry is never said twice: %s" % h["usage"][:1])


MANUAL_LINE = ("USAGE PAUSE — manual pause is on (usage-settings.json) · say «button up», "
               "or lift it: usage.py --manual off")


def case_a6():
    start("G-A6", "a manual pause stands above every override; --manual on|off round-trips")
    w = world("a6")
    ts = window(w, SID_S, SONNET, title=TITLE_S)
    settings(w, {"wait_refuse_models": ["claude-fable-"]})
    meter(w, [all_week(91)], spend=SPEND)
    code, _out = usage_cli(w, "--continue", "--vendor", "claude", "--by", TITLE_S)
    check(code == 0, "an override is in force first")
    code, out = usage_cli(w, "--manual", "on")
    s = settings_now(w) or {}
    check(code == 0 and len(lines_of(out)) == 1 and out.startswith("manual pause is ON (usage-settings.json)"),
          "--manual on prints one line: %s" % out.strip())
    check(s.get("manual_pause") is True and s.get("manual_pause_at") and len(s.get("overrides") or []) == 1
          and s.get("wait_refuse_models") == ["claude-fable-"],
          "…sets the flag and its stamp, the override and the other key kept")
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(out.strip() == MANUAL_LINE, "the R5 line, over the override: %s" % out.strip())
    code, _out = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 1, "--check exits 1 under the manual pause")
    code, out = usage_cli(w, "--continue", "--vendor", "claude")
    check(code == 1 and "never lifts it" in out, "«continue» never lifts a manual pause: %s" % out.strip())
    h = hook(w, SID_S, ts)
    wait_for(lambda: notices(w) and inbox_all_lines(w), 20.0)
    time.sleep(1.0)
    ns = notices(w)
    check(h["usage"] == [MANUAL_LINE] and len(ns) == 1 and ns[0][1] == "manual pause"
          and len(inbox_all_lines(w)) == 1
          and inbox_all_lines(w)[0].rstrip().endswith("answer in your window: button up, or lift it: "
                                                      "usage.py --manual off"),
          "its onset asks once: one notice, one letter with its own answer (%d, %d)"
          % (len(ns), len(inbox_all_lines(w))))
    code, out = usage_cli(w, "--manual", "off")
    s = settings_now(w) or {}
    check(code == 0 and out.startswith("manual pause is OFF") and s.get("manual_pause") is False
          and "manual_pause_at" not in s and len(s.get("overrides") or []) == 1
          and s.get("wait_refuse_models") == ["claude-fable-"],
          "--manual off lifts it and keeps the rest: %s" % out.strip()[:60])
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(out.startswith("USAGE — CONTINUED past the pause line"), "…and the override rules again: %s"
          % out.strip()[:70])
    code, out = usage_cli(w, "--manual", "on", "--now", iso(now() + datetime.timedelta(minutes=1)))
    hook(w, SID_S, ts)
    wait_for(lambda: len(notices(w)) >= 2 and len(inbox_all_lines(w)) >= 2, 20.0)
    time.sleep(1.0)
    check(len(notices(w)) == 2 and len(inbox_all_lines(w)) == 2,
          "a second manual pause is its own onset: it asks once more (%d, %d)"
          % (len(notices(w)), len(inbox_all_lines(w))))
    code, out = usage_cli(w, "--manual", "maybe")
    check(code == 2, "a word that is not on/off: exit 2, nothing written")


def case_a7():
    start("G-A7", "a PAUSE on another window than the override's still pauses")
    w = world("a7")
    tf = window(w, SID_F, FABLE)
    reset = now() + datetime.timedelta(days=2)
    meter(w, [fable_week(92, at=reset), all_week(50, at=reset)], spend=SPEND)
    code, _out = usage_cli(w, "--continue", "--vendor", "claude", "--by", TITLE_S)
    v = probe(w, EVAL_PROBE)
    check(code == 0 and v.get("level") == "continued" and v.get("facts") is None,
          "the Fable week answered: continued, and the postman holds nothing (%s)" % v.get("level"))
    meter(w, [fable_week(93, at=reset), all_week(91, at=reset)], spend=SPEND)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(out.startswith("USAGE PAUSE — all models 91 percent"), "all models crosses 90: PAUSE: %s"
          % out.strip()[:60])
    code, _out = usage_cli(w, "--check", "--vendor", "claude", "--model", "fable")
    h = hook(w, SID_F, tf)
    v = probe(w, EVAL_PROBE)
    check(code == 1 and h["usage"][:1] and h["usage"][0].startswith("USAGE PAUSE — all models 91 percent")
          and (v.get("facts") or {}).get("all") is True,
          "…for the Fable window too, and the postman's facts say all (%s)" % v.get("facts"))
    meter(w, [fable_week(93, at=reset), win("5-hour limit", 95.0, "5h",
                                            at=now() + datetime.timedelta(hours=3))], spend=SPEND)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(out.startswith("USAGE PAUSE — 5-hour window 95 percent · resets "),
          "the 5-hour window crosses 90: PAUSE: %s" % out.strip()[:60])
    meter(w, [fable_week(95, at=reset + datetime.timedelta(days=7))], spend=SPEND)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(out.startswith("USAGE PAUSE — Fable 95 percent"),
          "the NEXT week of the same label is a new window: PAUSE: %s" % out.strip()[:60])
    # a WARN on ANOTHER window is never hidden by a «continue»
    x = world("a7w")
    tx = window(x, SID_F, FABLE)
    meter(x, [fable_week(92, at=reset), all_week(50, at=reset)], spend=SPEND)
    code, _out = usage_cli(x, "--continue", "--vendor", "claude", "--by", TITLE_S)
    meter(x, [fable_week(93, at=reset), all_week(85, at=reset)], spend=SPEND)
    h = hook(x, SID_F, tx)
    check(code == 0 and len(h["usage"]) == 2
          and h["usage"][0].startswith("USAGE — CONTINUED past the pause line")
          and h["usage"][1].startswith("USAGE — all models 85 percent of the week, resets %s · read "
                                       % local_hm(reset)),
          "Fable continued, all models at 85: the CONTINUED line, THEN the WARN line: %s" % h["usage"])
    wait_for(lambda: notices(x), 20.0)
    time.sleep(2.0)
    ns = notices(x)
    check(len(ns) == 1 and h["usage"][1:] and ns[0][2] == h["usage"][1] and not inbox_all_lines(x),
          "…and that crossing raises ONE notice, its WARN line, no letter (%d)" % len(ns))
    h = hook(x, SID_F, tx)
    code, out = usage_cli(x, "--line", "--vendor", "claude")
    time.sleep(2.0)
    check(len(h["usage"]) == 2 and len(lines_of(out)) == 2 and len(notices(x)) == 1,
          "the next turn: both lines again (the hook and --line), no second notice")


def case_a8():
    start("G-A8", "the dollars clause, three ways: extra usage on, OFF, no figure")
    for name, spend, long_words, short_words in (
            ("on", SPEND, "extra usage so far $10.45 of $40 this month", "extra usage $10.45 of $40"),
            ("off", SPEND_OFF, OFF, OFF),
            ("none", None, "no extra-usage figure on this meter", "no extra-usage figure on this meter")):
        x = world("a8" + name)
        meter(x, [all_week(91)], spend=spend)
        code, out = usage_cli(x, "--line", "--vendor", "claude")
        check("say «continue» (work on until the reset; %s) or «button up»" % long_words in out,
              "%s — the question: …%s" % (name, out.strip()[80:260]))
        code, out = usage_cli(x, "--continue", "--vendor", "claude", "--by", TITLE_S)
        check(code == 0 and lines_of(out)[:1] == [long_words],
              "%s — the answer's first line: %s" % (name, lines_of(out)[:1]))
        code, out = usage_cli(x, "--line", "--vendor", "claude")
        check(out.startswith("USAGE — CONTINUED") and (" · %s · read " % short_words) in out,
              "%s — the CONTINUED line: …%s" % (name, out.strip()[-130:]))
    w = world("a8")
    meter(w, [win("Codex", 95.0, "week")], vendor="codex", login="default",
          spend={"credits": 0, "has_credits": False, "unlimited": False})
    code, out = usage_cli(w, "--line", "--vendor", "codex")
    check(out.startswith("USAGE PAUSE — Codex 95 percent") and "no extra-usage figure on this meter" in out,
          "a Codex meter's credits are not an extra-usage figure: %s" % out.strip()[:120])


def case_a9():
    start("G-A9", "the tree and the ledger: ASKED / CONTINUED until beside the meter; nothing otherwise")
    w = world("a9")
    reset = now() + datetime.timedelta(days=2)
    asked = now() - datetime.timedelta(minutes=3)
    meter(w, [all_week(91, at=reset)], spend=SPEND,
          extra={"pause_announced_key": "Weekly · all models|%s" % iso(reset),
                 "pause_announced_at": iso(asked),
                 "accounting": {"last_24h": {"tokens_by_model": {SONNET: {"fresh": 10, "cached": 20,
                                                                          "out": 1}}}}})
    got = probe(w, PICTURE_PROBE)
    bands, chip = got.get("bands") or "", got.get("chip") or ""
    m = re.search(r'<a class="ub ug asked" href="([^"]+)" title="([^"]+)">([^<]+)</a>', bands)
    check(m is not None and m.group(3) == "ASKED %s" % local_hm(asked),
          "the band carries ASKED <when> beside it: %s" % (m.group(3) if m else re.sub("<[^>]+>", " ", bands)[-120:]))
    check(m is not None and m.group(1).startswith("usage-north-claude-") and "continue, or button up?" in m.group(2)
          and "pause_announced_at" in m.group(2),
          "…a link to the file its bytes are in, the question in its title")
    check("Claude ASKED %s" % local_hm(asked) in chip and "last 24 h" in chip,
          "the ledger's chip carries it after the 24 h: %s" % re.sub("<[^>]+>", "", chip))
    html, out = render(w)
    check('class="ub ug asked"' in html and ">ASKED %s<" % local_hm(asked) in html,
          "the rendered tree's masthead carries the word (%s)" % ("rendered" if html else out.strip()[-100:]))
    code, _out = usage_cli(w, "--continue", "--vendor", "claude", "--by", TITLE_S)
    got = probe(w, PICTURE_PROBE)
    bands, chip = got.get("bands") or "", got.get("chip") or ""
    m = re.search(r'<a class="ub ug cont" href="([^"]+)" title="([^"]+)">([^<]+)</a>', bands)
    check(code == 0 and m is not None and m.group(3).startswith("CONTINUED until %s · Exocortex/Desk: "
                                                                  % local_hm(reset))
          and m.group(1) == "usage-settings.json" and TITLE_S in m.group(2) and "ASKED" not in bands,
          "after «continue»: CONTINUED until <reset> · <who>, from usage-settings.json, the whole title "
          "in its hover: %s" % (m.group(3) if m else None))
    check("Claude CONTINUED until %s" % local_hm(reset) in chip, "…and on the ledger's chip")
    b = world("a9b")
    meter(b, [all_week(50, at=reset)], spend=SPEND,
          extra={"pause_announced_key": "Weekly · all models|%s" % iso(reset - datetime.timedelta(days=7)),
                 "pause_announced_at": iso(asked)})
    got = probe(b, PICTURE_PROBE)
    bands, chip = got.get("bands") or "", got.get("chip") or ""
    check(bands and 'class="ub ug' not in bands and "ASKED" not in chip and "CONTINUED" not in chip,
          "an old week's key and no override: no word on either (%s)" % re.sub("<[^>]+>", " ", bands)[-80:])


# --------------------------------------------------------------------------
# one login, one meter
# --------------------------------------------------------------------------

MUTANT_CROSS = """

# ---- MUTANT (gate-usage U-a): the newest meter file on the machine, whoever's it is ----
_real_newest_meter = newest_meter
def newest_meter(hub, machine, vendor, login=None, account=None):
    return _real_newest_meter(hub, machine, vendor)
"""

PCT_RE = re.compile(r"\d+\s*(%|percent)")


def owner_row(sid, account):
    """The record the app writes on a transcript that says which account owns it."""
    return {"type": "bridge-session", "sessionId": sid, "bridgeSessionId": "bridge-%s" % MARK,
            "ownerAccountUuid": account, "ownerOrganizationUuid": "org-%s" % MARK,
            "lastSequenceNum": 1}


def usage_row(sid, fable, allm, at=None, reset=None):
    """A get_usage tool result in the app's own shape, as a transcript carries it."""
    at = at or now() - datetime.timedelta(minutes=2)
    reset = reset or now() + datetime.timedelta(days=2)
    obj = {"plan": {"status": "ok", "plan": "Max", "windows": [
        {"label": "Weekly · all models", "percentUsed": allm, "resetsAt": zulu(reset)},
        {"label": "Weekly · Fable", "percentUsed": fable, "resetsAt": zulu(reset)}]}}
    return {"type": "user", "sessionId": sid, "timestamp": zulu(at), "uuid": "gu-%s" % MARK,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu-1",
                                                     "content": [{"type": "text",
                                                                  "text": json.dumps(obj)}]}]}}


def line_of(w, *extra):
    code, out = usage_cli(w, "--line", "--vendor", "claude", *extra)
    return code, [l for l in out.splitlines() if l.startswith("USAGE")]


def case_ua():
    start("U-a", "two logins on one machine: the newer, other login's PAUSE never stands in")
    w = world("ua")
    t = window(w, SID_F, FABLE, rows=[owner_row(SID_F, ACCT_W)])
    meter(w, [fable_week(12), all_week(8)], age_min=5)                      # this login's
    meter(w, [fable_week(96), all_week(94)], age_min=1, login=LOGIN_K,     # the other's, newer
          extra={"account": ACCT_K[:8]})
    code, lines = line_of(w)
    want = "USAGE · %s%s · Fable 12 %% · all 8 %% · read 5 min ago" % (LOGIN_W, CLI)
    check(code == 0 and lines == [want], "--line reads THIS login's file, names it and its read "
                                         "age: %s" % lines)
    h = hook(w, SID_F, t)
    check(h["code"] == 0 and not any(l.startswith("USAGE PAUSE") for l in h["usage"])
          and not any("96" in l for l in h["usage"]),
          "the hook hears no PAUSE from the other login's newer file: %s" % h["usage"])
    code, out = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 0, "--check exits 0: this login is at 12 percent (exit %d, %s)" % (code, out.strip()[:80]))
    code, lines = line_of(w, "--login", LOGIN_K)
    check(lines and lines[0].startswith("USAGE PAUSE — Fable 96 percent") and (" · %s" % LOGIN_K) in lines[0],
          "--login <the other> reads the other's file, and says whose it is: %s" % (lines[:1],))
    m = world("uam")
    src = io.open(str(m["hub"] / "tools" / "usage.py"), encoding="utf-8").read()
    io.open(str(m["hub"] / "tools" / "usage.py"), "w", encoding="utf-8").write(src + MUTANT_CROSS)
    meter(m, [fable_week(12), all_week(8)], age_min=5)
    meter(m, [fable_week(96), all_week(94)], age_min=1, login=LOGIN_K)
    tm = window(m, SID_F, FABLE, rows=[owner_row(SID_F, ACCT_W)])
    mh = hook(m, SID_F, tm)                  # the hook imports usage.py: the mutant is in force
    check(any(l.startswith("USAGE PAUSE — Fable 96") for l in mh["usage"]),
          "a MUTANT that takes the newest file across logins gives the hook the other login's "
          "PAUSE — the check above has teeth: %s" % mh["usage"][:1])


def case_ub():
    start("U-b", "a 4 h old reading: the word refresh, no percent anywhere")
    w = world("ub")
    t = window(w, SID_F, FABLE, rows=[owner_row(SID_F, ACCT_W)])
    meter(w, [fable_week(40), all_week(30)], age_min=240)
    code, lines = line_of(w)
    want = ("USAGE · %s%s · refresh (read 4 h ago) — call get_usage, then usage.py "
            "--write --vendor claude" % (LOGIN_W, CLI))
    check(code == 0 and lines == [want], "--line: %s" % lines)
    check(lines and not PCT_RE.search(lines[0]), "no percent in it")
    h = hook(w, SID_F, t)
    check(h["usage"] == [want.replace(CLI, TRANSCRIPT)],
          "the hook's turn start says the same words, its login read from its transcript: %s"
          % h["usage"])
    meter(w, [fable_week(40), all_week(30)], age_min=240, login=LOGIN_K)
    os.remove(str(w["hub"] / ("usage-north-claude-%s.json" % LOGIN_W.replace("@", "-at-"))))
    code, lines = line_of(w)
    want2 = ("USAGE · %s%s · refresh (read 4 h ago by %s) — call get_usage, then "
             "usage.py --write --vendor claude" % (LOGIN_W, CLI, LOGIN_K))
    check(lines == [want2] and not PCT_RE.search(lines[0]),
          "only ANOTHER login's reading on the machine: refresh, and whose it is (the whole login: "
          "both share the word `example`): %s" % lines)
    other = "osprey@elsewhere.test"
    meter(w, [fable_week(40), all_week(30)], age_min=30, login=other)
    code, lines = line_of(w)
    check(lines and "refresh (read 30 min ago by elsewhere)" in lines[0] and not PCT_RE.search(lines[0]),
          "a login on its own domain is called by that word, as a person would: %s" % lines)


def case_uc():
    start("U-c", "a scan files a reading under the login that owns its transcript — or unknown")
    w = world("uc")
    window(w, SID_V, SONNET, rows=[usage_row(SID_V, 33, 22)], owner=None)   # names no owner
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan")
    unknown = w["hub"] / "usage-north-claude-unknown.json"
    body = json.loads(io.open(str(unknown), encoding="utf-8").read()) if unknown.is_file() else {}
    check(code == 0 and body.get("login") == "unknown" and "names no owner" in str(body.get("login_source")),
          "no owner in the transcript: filed `login: unknown` (%s · %s)"
          % (body.get("login"), body.get("login_source")))
    mine = w["hub"] / ("usage-north-claude-%s.json" % LOGIN_W.replace("@", "-at-"))
    check(not mine.exists(), "…and NOT under the app's login: a scan never assumes it")
    code, lines = line_of(w)
    check(lines and "refresh" in lines[0] and not PCT_RE.search(lines[0]) and LOGIN_W in lines[0],
          "every reader takes `unknown` for another login's: the line says refresh: %s" % lines)
    bands = probe(w, PICTURE_PROBE).get("bands") or ""
    check("Claude" not in re.sub("<[^>]+>", " ", bands) and "33%" not in bands,
          "…and the tree never draws nobody's reading as this machine's band: %s"
          % re.sub("<[^>]+>", " ", bands)[-90:])
    window(w, SID_U, SONNET, rows=[owner_row(SID_U, ACCT_W),
                                   usage_row(SID_U, 41, 27, at=now() - datetime.timedelta(minutes=1))])
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan")
    body = json.loads(io.open(str(mine), encoding="utf-8").read()) if mine.is_file() else {}
    check(code == 0 and body.get("login") == LOGIN_W and body.get("account") == ACCT_W[:8]
          and "transcript owner = .claude.json" in str(body.get("login_source")),
          "a transcript the app's account owns: filed under the app's login, its account's first "
          "eight beside it (%s · %s · %s)" % (body.get("login"), body.get("account"), body.get("login_source")))
    code, lines = line_of(w)
    check(lines == ["USAGE · %s%s · Fable 41 %% · all 27 %% · read 1 min ago" % (LOGIN_W, CLI)],
          "…and the line reads it: %s" % lines)
    x = world("ucx")
    window(x, SID_U, SONNET, rows=[owner_row(SID_U, ACCT_X), usage_row(SID_U, 55, 44)])
    code, out = usage_cli(x, "--write", "--vendor", "claude", "--scan")
    got = sorted(p.name for p in x["hub"].glob("usage-north-claude-*.json"))
    check(got == ["usage-north-claude-unknown.json"],
          "an owner account nothing here names: `unknown` too, never the app's login: %s" % got)
    meter(x, [fable_week(10)], age_min=30, login=LOGIN_K, extra={"account": ACCT_X[:8]})
    code, out = usage_cli(x, "--write", "--vendor", "claude", "--scan")
    kfile = x["hub"] / ("usage-north-claude-%s.json" % LOGIN_K.replace("@", "-at-"))
    body = json.loads(io.open(str(kfile), encoding="utf-8").read()) if kfile.is_file() else {}
    check(body.get("login") == LOGIN_K and [w_.get("percent") for w_ in body.get("windows") or []] == [44.0, 55.0],
          "…until a meter file names that account: then it is that login's reading (%s)"
          % body.get("login_source"))


def case_ud():
    start("U-d", "the hook passes the WINDOW's login, and the line names it")
    w = world("ud")
    meter(w, [fable_week(20), all_week(15)], age_min=2)                    # the app's login
    meter(w, [fable_week(91), all_week(70)], age_min=2, login=LOGIN_K,
          extra={"account": ACCT_K[:8]})
    tk = window(w, SID_U, FABLE, rows=[owner_row(SID_U, ACCT_K)])
    h = hook(w, SID_U, tk)
    pause = [l for l in h["usage"] if l.startswith("USAGE PAUSE")]
    check(pause and pause[0].startswith("USAGE PAUSE — Fable 91 percent")
          and (" · %s%s · " % (LOGIN_K, TRANSCRIPT)) in pause[0],
          "a window another account owns hears ITS login's PAUSE, the login named: %s" % (pause[:1],))
    tw = window(w, SID_F, FABLE, rows=[owner_row(SID_F, ACCT_W)])
    h = hook(w, SID_F, tw)
    check(not h["usage"], "the app's own window, at 20 percent, hears nothing below WARN: %s" % h["usage"])
    meter(w, [fable_week(85), all_week(15)], age_min=2)
    h = hook(w, SID_F, tw)
    check(h["usage"] and h["usage"][0].startswith("USAGE — Fable 85 percent") and (" · %s" % LOGIN_W) in h["usage"][0],
          "…and at 85 its own WARN, its own login named: %s" % h["usage"][:1])
    tv = window(w, SID_V, FABLE, owner=None)                               # names no owner
    h = hook(w, SID_V, tv, env=window_variables(w, SID_V))
    check(h["usage"] and (" · %s" % LOGIN_W) in h["usage"][0],
          "a window whose transcript names no owner runs under the app's login: %s" % h["usage"][:1])


def case_ue():
    start("U-e", "the wake screen's receipts carry the same words (one copy)")
    w = world("ue")
    for name in ("wake-screen.py", "night-check.py", "app_sessions.py", "routine-check.py"):
        src = source_tool(name)
        if src.is_file():
            shutil.copy2(str(src), str(w["hub"] / "tools" / name))
    if not (w["hub"] / "tools" / "wake-screen.py").is_file():
        check(False, "tools/wake-screen.py is not beside this gate or in the hub — U-e cannot run; "
                     "named, never passed")
        return
    meter(w, [fable_week(9), all_week(6)], age_min=3)
    empty = w["base"] / "ps-empty.txt"
    write(empty, "")
    _code, lines = line_of(w)
    code, out = run([PY, w["hub"] / "tools" / "wake-screen.py"], w, env={"EXO_NIGHT_PS": str(empty)})
    first = out.splitlines()[0] if out.splitlines() else ""
    check(code == 0 and first.startswith("WAKE · ") and lines and (" · %s" % lines[0]) in first,
          "the receipts line carries --line's own words: %r" % first[-140:])
    meter(w, [fable_week(9), all_week(6)], age_min=240)
    _code, lines = line_of(w)
    code, out = run([PY, w["hub"] / "tools" / "wake-screen.py"], w, env={"EXO_NIGHT_PS": str(empty)})
    first = out.splitlines()[0] if out.splitlines() else ""
    check(lines and "refresh (read 4 h ago)" in lines[0] and lines[0] in first and not PCT_RE.search(first),
          "a stale reading: the same refresh words, and no percent on the receipts line: %r" % first[-140:])


# --------------------------------------------------------------------------
# `--write --scan` never hangs silently on a big transcript store
# --------------------------------------------------------------------------

HEARTBEAT_RE = re.compile(r"^(\d+) of (\d+) files · newest first · (\d+)s$", re.M)

# the same wrapper as scan-probe.py: usage.main() in-process, every open() and directory listing counted
OPEN_PROBE = r'''
import builtins, importlib.util, io, json, os, sys
opened, listed = [], []
_open, _os_open, _listdir, _scandir = builtins.open, os.open, os.listdir, os.scandir
def nm(f):
    try:
        return str(os.fspath(f))
    except TypeError:
        return None
def spy_open(file, *a, **k):
    if nm(file): opened.append(nm(file))
    return _open(file, *a, **k)
def spy_os_open(path, *a, **k):
    if nm(path): opened.append(nm(path))
    return _os_open(path, *a, **k)
def spy_listdir(path="."):
    if nm(path): listed.append(nm(path))
    return _listdir(path)
def spy_scandir(path="."):
    if nm(path): listed.append(nm(path))
    return _scandir(path)
spec = importlib.util.spec_from_file_location("u", sys.argv[1])
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
builtins.open = io.open = spy_open
os.open, os.listdir, os.scandir = spy_os_open, spy_listdir, spy_scandir
code = u.main(sys.argv[2:])
sys.stdout.flush()
print("PROBE " + json.dumps({"code": code, "opened": sorted(set(opened)), "listed": sorted(set(listed))}))
'''


def sized_transcript(w, sid, mib, rows, project="-gate-hub"):
    """A transcript of `mib` MiB of filler (no get_usage word in it) with `rows` at the END."""
    path = w["home"] / ".claude" / "projects" / project / ("%s.jsonl" % sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps({"type": "assistant", "note": "filler %s" % MARK, "pad": "x" * 900}) + "\n").encode()
    block = line * 1024
    with io.open(str(path), "wb") as fh:
        for _i in range((mib << 20) // len(block) + 1):
            fh.write(block)
        for r in rows:
            fh.write((json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def aged(path, minutes=0.0, days=0.0):
    t = time.time() - minutes * 60 - days * 86400
    os.utime(str(path), (t, t))
    return path


def scanned_meter(w):
    got = sorted(w["hub"].glob("usage-north-claude-*.json"))
    return json.loads(io.open(str(got[0]), encoding="utf-8").read()) if got else {}


def pcts(body):
    return sorted(float(x.get("percent") or 0) for x in body.get("windows") or [])


def case_u1():
    start("U1", "the scan reads the TAIL: a 60 MiB transcript with the result at its end, under 2 s")
    w = world("u1")
    big = sized_transcript(w, SID_V, 60, [usage_row(SID_V, 33, 22)])
    size = big.stat().st_size
    t0 = time.monotonic()
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan")
    secs = time.monotonic() - t0
    check(size >= 60 << 20, "the fixture is %d MiB of filler with the result on its last line" % (size >> 20))
    check(code == 0 and "usage: written" in out and pcts(scanned_meter(w)) == [22.0, 33.0],
          "the scan finds the result and files it (exit %s): %s" % (code, out.strip().splitlines()[-1:]))
    check(secs < 2.0, "…in %.2f s, under 2 s: the tail, never the whole file" % secs)
    skip = [l for l in out.splitlines() if l.startswith("skipping ")]
    check(skip == ["skipping %s.jsonl: 60 MB — read the tail only" % SID_V],
          "one line for the file over 50 MiB: %s" % skip)
    check(not HEARTBEAT_RE.search(out), "a fast scan prints no heartbeat line")
    w2 = world("u1b")
    window(w2, SID_V, SONNET, rows=[usage_row(SID_V, 33, 22)])
    code, out = usage_cli(w2, "--write", "--vendor", "claude", "--scan")
    check(code == 0 and "skipping" not in out, "a small transcript prints no skipping line")
    # a result older than the last 256 KiB but inside 1 MiB: the tail grows ONCE and finds it
    w3 = world("u1c")
    p = sized_transcript(w3, SID_V, 0, [usage_row(SID_V, 41, 27)])
    with io.open(str(p), "ab") as fh:
        fh.write((json.dumps({"type": "assistant", "pad": "y" * 900}) + "\n").encode() * 512)   # ~460 KiB after it
    code, out = usage_cli(w3, "--write", "--vendor", "claude", "--scan")
    check(code == 0 and pcts(scanned_meter(w3)) == [27.0, 41.0],
          "a result 450 KiB from the end: the tail grew once (256 KiB → 1 MiB) and found it")
    w4 = world("u1d")
    p = sized_transcript(w4, SID_V, 0, [usage_row(SID_V, 41, 27)])
    with io.open(str(p), "ab") as fh:
        fh.write((json.dumps({"type": "assistant", "pad": "y" * 900}) + "\n").encode() * 1400)  # ~1.2 MiB after it
    code, out = usage_cli(w4, "--write", "--vendor", "claude", "--scan")
    check(code == 1 and "no get_usage result" in out and not scanned_meter(w4),
          "a result 1.2 MiB from the end: past the single growth, not read (exit %s)" % code)


def case_u2():
    start("U2", "the budget stop prints what it found so far and exits 0")
    w = world("u2")
    window(w, SID_F, FABLE)                                                  # newest: no result
    window(w, SID_S, SONNET)                                                 # next: no result
    old = window(w, SID_V, SONNET, rows=[usage_row(SID_V, 33, 22)])          # oldest: the result
    aged(w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % SID_F), minutes=1)
    aged(w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % SID_S), minutes=2)
    aged(old, minutes=3)
    code, out = run([PY, w["hub"] / "tools" / "usage.py", "--write", "--vendor", "claude", "--scan",
                     "--budget-seconds", "20", "--hub", w["hub"]], w, env={"EXO_USAGE_SCAN_TICK": "15"})
    stop = [l for l in out.splitlines() if l.startswith("scan stopped at ")]
    check(code == 0 and len(stop) == 1, "exit 0 and ONE stop line (exit %s): %s" % (code, stop))
    check(stop and re.match(r"scan stopped at 2 of 3 after \d+\.\d s — newest reading so far: none"
                            r" · nothing filed$", stop[0]) is not None,
          "…it says where it stopped, what it had (none yet) and that nothing was filed: %s" % stop)
    check(not scanned_meter(w), "…and no meter file was written")
    code, out = run([PY, w["hub"] / "tools" / "usage.py", "--write", "--vendor", "claude", "--scan",
                     "--budget-seconds", "120", "--hub", w["hub"]], w, env={"EXO_USAGE_SCAN_TICK": "15"})
    check(code == 0 and "scan stopped" not in out and pcts(scanned_meter(w)) == [22.0, 33.0],
          "the same store with 120 s of budget reaches the result: the budget was what stopped it")


def case_u3():
    start("U3", "a transcript not modified in the last 7 days is skipped without --all")
    w = world("u3")
    p8 = window(w, SID_V, SONNET, rows=[usage_row(SID_V, 55, 44, at=now() - datetime.timedelta(days=8))])
    aged(p8, days=8)
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan")
    check(code == 1 and "no get_usage result" in out and not scanned_meter(w),
          "an 8-day-old transcript alone: not read, nothing written (exit %s)" % code)
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan", "--all")
    check(code == 0 and pcts(scanned_meter(w)) == [44.0, 55.0], "…with --all it is read (exit %s)" % code)
    w6 = world("u3b")
    p6 = window(w6, SID_V, SONNET, rows=[usage_row(SID_V, 31, 21, at=now() - datetime.timedelta(days=6))])
    aged(p6, days=6)
    code, out = usage_cli(w6, "--write", "--vendor", "claude", "--scan")
    check(code == 0 and pcts(scanned_meter(w6)) == [21.0, 31.0], "a 6-day-old transcript is read")


def case_u4():
    start("U4", "a flushed heartbeat line on a slow scan (35 s of synthetic delay per file)")
    w = world("u4")
    window(w, SID_F, FABLE)
    window(w, SID_S, SONNET)
    old = window(w, SID_V, SONNET, rows=[usage_row(SID_V, 33, 22)])
    aged(w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % SID_F), minutes=1)
    aged(w["home"] / ".claude" / "projects" / "-gate-hub" / ("%s.jsonl" % SID_S), minutes=2)
    aged(old, minutes=3)
    code, out = run([PY, w["hub"] / "tools" / "usage.py", "--write", "--vendor", "claude", "--scan",
                     "--budget-seconds", "300", "--hub", w["hub"]], w, env={"EXO_USAGE_SCAN_TICK": "35"})
    beats = HEARTBEAT_RE.findall(out)
    check(code == 0 and [(a, b) for a, b, _c in beats][:1] == [("1", "3")],
          "the heartbeat names files done of files total: %s" % beats)
    check([int(c) for _a, _b, c in beats] == [35, 70], "…at 35 s and again at 70 s, not at every file: %s" % beats)
    lines = out.splitlines()
    beat_at = [i for i, l in enumerate(lines) if HEARTBEAT_RE.match(l)]
    done_at = [i for i, l in enumerate(lines) if l.startswith("usage: written")]
    check(beat_at and done_at and max(beat_at) < done_at[0], "…and every heartbeat comes before the result line")


def case_u5():
    start("U5", "stdin --write touches no transcript and lists no store")
    w = world("u5")
    row = usage_row(SID_V, 33, 22)
    sized_transcript(w, SID_F, 60, [usage_row(SID_F, 90, 90)])
    window(w, SID_S, SONNET, rows=[usage_row(SID_S, 80, 80)])
    old = window(w, SID_U, SONNET, rows=[owner_row(SID_U, ACCT_W)])
    aged(old, days=9)
    stdin_json = row["message"]["content"][0]["content"][0]["text"]
    probe_args = ["--write", "--vendor", "claude", "--hub", w["hub"]]
    code, out = run([PY, "-c", OPEN_PROBE, w["hub"] / "tools" / "usage.py"] + probe_args, w, stdin=stdin_json)
    got = {}
    for l in reversed(out.strip().splitlines()):
        if l.startswith("PROBE "):
            got = json.loads(l[6:])
            break
    opened, listed = got.get("opened") or [], got.get("listed") or []
    store = str(w["home"] / ".claude" / "projects")
    in_store = [p for p in opened + listed if p.startswith(store) or p.endswith(".jsonl")]
    check(got.get("code") == 0 and pcts(scanned_meter(w)) == [22.0, 33.0],
          "the stdin write files its reading (exit %s): %s" % (got.get("code"), out.strip().splitlines()[:1]))
    check(not in_store, "no transcript opened, no folder of the store listed (%d paths opened, %d listed): %s"
          % (len(opened), len(listed), in_store))
    meters = [p for p in opened if os.path.basename(p).startswith("usage-north-claude-")]
    check(meters, "the spy sees the meter file opened: %s" % [os.path.basename(p) for p in meters])
    check("scanning" not in out and "skipping" not in out, "…and no scan line is printed")
    # the window's own session id: the login's owner lookup reads THAT one transcript, never a walk
    w2 = world("u5b")
    mine = window(w2, SID_V, SONNET, rows=[owner_row(SID_V, ACCT_W)])
    sized_transcript(w2, SID_F, 60, [usage_row(SID_F, 90, 90)])
    code, out = run([PY, "-c", OPEN_PROBE, w2["hub"] / "tools" / "usage.py"] + probe_args, w2, stdin=stdin_json,
                    env={"CLAUDE_CODE_SESSION_ID": SID_V})
    got = {}
    for l in reversed(out.strip().splitlines()):
        if l.startswith("PROBE "):
            got = json.loads(l[6:])
            break
    jl = [p for p in got.get("opened") or [] if p.endswith(".jsonl")]
    ls = got.get("listed") or []
    check(got.get("code") == 0 and set(os.path.basename(p) for p in jl) <= {"%s.jsonl" % SID_V},
          "NOT ZERO with CLAUDE_CODE_SESSION_ID set (the session's real road): only the session's own "
          "transcript is opened for its owner (BQ-261 D5), never another: %s; %d folder listing(s) "
          "to find it, none of the store's other files opened" % ([os.path.basename(p) for p in jl], len(ls)))


# --------------------------------------------------------------------------
# AP1 … AP12 — THE AUTO-PAUSE WATCH 
# --------------------------------------------------------------------------

AP_TITLE = "Exocortex · auto-pause"
AP_PROBE = r'''
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("u", sys.argv[1])
u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
model = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
v = u.evaluate(sys.argv[2], "claude", model=model, prune=False)
v = dict((k, v.get(k)) for k in (
    "level", "pause", "lines", "key", "hits", "stop_line", "auto_pause", "auto_key", "auto_window",
    "auto_resets", "auto_login", "auto_line", "auto_lifted_key", "auto_lifted_line",
    "refresh_every", "refresh_line"))
v["facts"] = u.pause_facts(sys.argv[2], "claude")
print(json.dumps(v, ensure_ascii=False, default=str))
'''
AP_METER = "usage-north-claude-wren-at-example.test.json"
AP_LABEL_5H = "5-hour limit"


def five_hour(pct, hours=3.0, **kw):
    kw.setdefault("at", now() + datetime.timedelta(hours=hours))
    return win(AP_LABEL_5H, pct, "5h", **kw)


def ap_v(w, model=None):
    return probe(w, AP_PROBE, model or "")


def ap_notices(w):
    """The auto-pause watch's own notices through the --notify seam: [title, subtitle, body]."""
    try:
        text = io.open(str(w["base"] / "notify-calls.jsonl"), encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        try:
            got = json.loads(line)
        except ValueError:
            continue
        if isinstance(got, list) and got and got[0] == AP_TITLE:
            out.append((got + ["", "", ""])[:3])
    return out


def ap_file(w):
    try:
        return json.loads(io.open(str(w["hub"] / AP_METER), encoding="utf-8").read())
    except (OSError, ValueError):
        return {}


def ap_edit(w, fn):
    d = ap_file(w)
    fn(d)
    write_json(w["hub"] / AP_METER, d)


def get_usage_json(pct, reset, label=AP_LABEL_5H):
    return json.dumps({"plan": {"windows": [{"label": label, "percentUsed": pct, "resetsAt": zulu(reset)}]}})


def flagship_registry(w):
    import copy
    reg = copy.deepcopy(REGISTRY)
    reg["minds"][0].update(tier="flagship", cli="fable", app_id=FABLE)
    write_json(w["hub"] / "registry.json", reg)


def case_ap1():
    start("AP1", "a 5-hour window at 97: level auto-pause, its key and line, --check 1, --line first")
    w = world("ap1")
    win5 = five_hour(97)
    meter(w, [win5, all_week(40)])
    v = ap_v(w)
    reset = datetime.datetime.fromisoformat(win5["resets_at"])
    check(v.get("level") == "auto-pause" and v.get("pause") is True and v.get("auto_pause") is True,
          "level auto-pause, pause True, auto_pause True: %s / %s" % (v.get("level"), v.get("auto_pause")))
    check(v.get("auto_key") == "%s|%s" % (AP_LABEL_5H, win5["resets_at"]),
          "auto_key is <label>|<resets_at>: %s" % v.get("auto_key"))
    line = v.get("auto_line") or ""
    check(line.startswith("AUTO-PAUSE — 5-hour limit 97 percent (%s) · resets %s · " % (
        LOGIN_W, local_hm(reset))) and line.endswith("every window of this login pauses · lifts at the reset"),
          "the line names the label, the percent, the login and the reset: %s" % line)
    aw = v.get("auto_window") or {}
    check(aw.get("label") == AP_LABEL_5H and aw.get("percent") == 97 and aw.get("kind") == "5h"
          and aw.get("resets_at") == win5["resets_at"] and v.get("auto_login") == LOGIN_W
          and v.get("auto_resets") == win5["resets_at"],
          "auto_window / auto_resets / auto_login carry the contract fields: %s" % aw)
    check(v.get("lines") == [line], "the verdict's one line is the auto line")
    code, out = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 1 and out.splitlines()[:1] == [line], "--check exits 1 and prints it: %s %s" % (code, out[:60]))
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(code == 0 and out.splitlines()[:1] == [line], "--line prints AUTO-PAUSE first: %s" % out[:60])
    w2 = world("ap1b")
    meter(w2, [five_hour(50), all_week(97)])
    v2 = ap_v(w2)
    check(v2.get("level") == "auto-pause" and (v2.get("auto_window") or {}).get("kind") == "week",
          "the all-models week at 97 pauses too (every plan kind is watched): %s" % v2.get("level"))
    w3 = world("ap1c")
    meter(w3, [five_hour(60), all_week(40)])
    v3 = ap_v(w3)
    check(v3.get("auto_pause") is False and v3.get("auto_key") is None and v3.get("auto_window") is None
          and v3.get("auto_resets") is None and v3.get("auto_login") is None and v3.get("auto_line") is None
          and v3.get("level") == "ok",
          "below the line the fields are present and falsy: %s" % v3.get("level"))


def case_ap2():
    start("AP2", "96 percent: nothing new — the ordinary PAUSE stands")
    w = world("ap2")
    meter(w, [five_hour(96)])
    v = ap_v(w)
    check(v.get("level") == "pause" and v.get("auto_pause") is False and v.get("auto_line") is None,
          "level pause, no auto fields: %s" % v.get("level"))
    check((v.get("lines") or [""])[0].startswith("USAGE PAUSE"), "the line is the ordinary PAUSE question")
    check(((v.get("facts") or {}).get("auto")) is False, "pause_facts says auto False")


def case_ap3():
    start("AP3", "an override does not lift it; --continue refuses with one line and writes nothing")
    w = world("ap3")
    win5 = five_hour(97)
    meter(w, [win5])
    reset = datetime.datetime.fromisoformat(win5["resets_at"])
    settings(w, {"manual_pause": False, "overrides": [{
        "vendor": "claude", "window_label": AP_LABEL_5H, "resets_at": win5["resets_at"],
        "until": iso(reset), "by": "fixture owner", "at": iso(now()), "percent_at": 91, "spend_at": None}]})
    v = ap_v(w)
    check(v.get("level") == "auto-pause" and v.get("pause") is True,
          "a «continue» stands on that window and the verdict is still auto-pause (never `continued`): %s"
          % v.get("level"))
    before = io.open(str(w["hub"] / "usage-settings.json"), encoding="utf-8").read()
    code, out = usage_cli(w, "--continue", "--by", "t")
    check(code == 1 and len(out.strip().splitlines()) == 1 and "cannot stand past the auto-pause line" in out,
          "--continue refuses in one line: %s" % out.strip()[:100])
    check(io.open(str(w["hub"] / "usage-settings.json"), encoding="utf-8").read() == before,
          "…and the settings file is byte for byte as it was")


def case_ap4():
    start("AP4", "the latch: a lower reading at the same reset stays paused; a rolled or past reset releases")
    w = world("ap4")
    reset = now() + datetime.timedelta(hours=3)
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--login", LOGIN_W, stdin=get_usage_json(97, reset))
    d = ap_file(w)
    check(code == 0 and (d.get("auto_pause_window") or {}).get("label") == AP_LABEL_5H,
          "the crossing is stored as auto_pause_window in the meter file: %s" % (d.get("auto_pause_window")))
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--login", LOGIN_W, stdin=get_usage_json(95, reset))
    d = ap_file(w)
    v = ap_v(w)
    check(d["windows"][0]["percent"] == 95 and d.get("auto_pause_window") and v.get("level") == "auto-pause"
          and v.get("auto_pause") is True,
          "written again at 95 with the same resets_at: still auto-pause, the latch carried (%s)" % v.get("level"))
    code, _o = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 1, "--check still exits 1 at 95 under the latch")
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--login", LOGIN_W,
                          stdin=get_usage_json(40, reset + datetime.timedelta(hours=5)))
    d = ap_file(w)
    v = ap_v(w)
    check("auto_pause_window" not in d and v.get("auto_pause") is False,
          "a reading from a NEWER reset (the window rolled) clears the old latch")
    w2 = world("ap4b")
    usage_cli(w2, "--write", "--vendor", "claude", "--login", LOGIN_W, stdin=get_usage_json(98, reset))
    past = now() - datetime.timedelta(minutes=1)
    code, out = usage_cli(w2, "--write", "--vendor", "claude", "--login", LOGIN_W, stdin=get_usage_json(30, past))
    d = ap_file(w2)
    v = ap_v(w2)
    check("auto_pause_window" not in d and v.get("auto_pause") is False,
          "written with a resets_at past now: released, auto_pause_window popped")
    check(bool(d.get("auto_lifted_window")) and bool(v.get("auto_lifted_key")),
          "…and the lift is remembered for its one notice (auto_lifted_key): %s" % v.get("auto_lifted_key"))


def case_ap5():
    start("AP5", "the Fable week at 97: a Fable window pauses, a Sonnet window does not (scope = pause_scope)")
    w = world("ap5")
    meter(w, [fable_week(97), all_week(40)])
    vf, vs = ap_v(w, FABLE), ap_v(w, SONNET)
    check(vf.get("level") == "auto-pause" and vf.get("auto_pause") is True,
          "a Fable window's verdict is auto-pause: %s" % vf.get("level"))
    check(vs.get("auto_pause") is False and vs.get("level") == "ok",
          "a Sonnet window's is not: %s / %s" % (vs.get("level"), vs.get("auto_pause")))
    check((vf.get("facts") or {}).get("families") == ["fable"] and (vf.get("facts") or {}).get("all") is False,
          "pause_facts: the Fable family only")
    line = vf.get("auto_line") or ""
    check("every Fable window of this login pauses" in line, "…and the line says so: %s" % line[-70:])
    w2 = world("ap5b")
    flagship_registry(w2)
    meter(w2, [fable_week(97), all_week(40)])
    vf2, vs2 = ap_v(w2, FABLE), ap_v(w2, SONNET)
    check(vf2.get("level") == "stop" and vf2.get("auto_pause") is True
          and "HARD STOP" in (vf2.get("lines") or [""])[0]
          and (vf2.get("lines") or ["", ""])[1].startswith("AUTO-PAUSE —"),
          "with the hard stop also present: level stop, the stop line first, the auto fields filled: %s"
          % vf2.get("lines"))
    check(vs2.get("auto_pause") is False and vs2.get("level") == "ok",
          "…and the Sonnet window still carries on (stop is information to it)")


def case_ap6():
    start("AP6", "auto_pause_percent null turns the watch off; a per_vendor row overrides the line")
    w = world("ap6")
    settings(w, {"auto_pause_percent": None})
    meter(w, [five_hour(99)])
    v = ap_v(w)
    check(v.get("level") == "pause" and v.get("auto_pause") is False
          and (v.get("lines") or [""])[0].startswith("USAGE PAUSE"),
          "null: 99 on the 5-hour window is an ordinary PAUSE: %s" % v.get("level"))
    w2 = world("ap6b")
    settings(w2, {"per_vendor": {"anthropic": {"auto_pause_percent": 99}}})
    meter(w2, [five_hour(98)])
    check(ap_v(w2).get("level") == "pause", "per_vendor 99: 98 is an ordinary PAUSE")
    meter(w2, [five_hour(99)])
    check(ap_v(w2).get("level") == "auto-pause", "…and 99 pauses")


def case_ap7():
    start("AP7", "another login's meter at 97 does not reach this login's verdict")
    w = world("ap7")
    meter(w, [five_hour(97)], login=LOGIN_K)
    meter(w, [five_hour(50)])
    v = ap_v(w)
    check(v.get("auto_pause") is False and v.get("level") == "ok",
          "this login reads its own file: %s / %s" % (v.get("level"), v.get("auto_pause")))


def case_ap8():
    start("AP8", "announce: one notice at the crossing, none twice, none for a 90 after a 97; a lifted notice once")
    w = world("ap8")
    win5 = five_hour(97)
    meter(w, [win5], spend=SPEND)
    code, out = usage_cli(w, "--announce", "--vendor", "claude")
    ns = ap_notices(w)
    check(len(ns) == 1 and ns[0][2].startswith("AUTO-PAUSE — 5-hour limit 97 percent")
          and ns[0][1].startswith("5-hour limit 97 percent"),
          "ONE notice titled %r, its body the line: %s" % (AP_TITLE, ns[:1]))
    check(not notices(w) and not inbox_all_lines(w), "…and no ordinary gate notice and NO letter")
    code, out = usage_cli(w, "--announce", "--vendor", "claude")
    check(out.startswith("usage: already") and len(ap_notices(w)) == 1, "the second evaluate raises nothing: %s" % out.strip()[:40])
    check(bool(ap_file(w).get("auto_pause_window")) and bool(ap_file(w).get("auto_announced_key")),
          "the latch and the onset key are on file")
    reset = datetime.datetime.fromisoformat(win5["resets_at"])
    after = iso(reset + datetime.timedelta(minutes=1))
    code, out = usage_cli(w, "--announce", "--vendor", "claude", "--now", after)
    ns = ap_notices(w)
    check(len(ns) == 2 and ns[1][2] == "AUTO-PAUSE lifted — 5-hour limit reset",
          "after the reset: ONE lifted notice: %s" % ns[1:])
    code, out = usage_cli(w, "--announce", "--vendor", "claude", "--now", after)
    check(len(ap_notices(w)) == 2, "…and only once")
    # 90 then 97 raise two notices; 97 then 90 again raises nothing new
    w2 = world("ap8b")
    meter(w2, [five_hour(91)], spend=SPEND)
    usage_cli(w2, "--announce", "--vendor", "claude")
    check(len(notices(w2)) == 1 and len(inbox_all_lines(w2)) == 1 and not ap_notices(w2),
          "a crossing of 90 raises the ordinary notice and letter")
    ap_edit(w2, lambda d: d["windows"][0].update(percent=97))
    usage_cli(w2, "--announce", "--vendor", "claude")
    check(len(notices(w2)) == 1 and len(ap_notices(w2)) == 1 and len(inbox_all_lines(w2)) == 1,
          "…then 97 raises its own notice (two in all) and no second letter")
    ap_edit(w2, lambda d: d["windows"][0].update(percent=91))
    code, out = usage_cli(w2, "--announce", "--vendor", "claude")
    check(out.startswith("usage: already") and len(notices(w2)) == 1 and len(ap_notices(w2)) == 1
          and len(inbox_all_lines(w2)) == 1,
          "…then 90 again (the latch stands) raises nothing new: %s" % out.strip()[:40])


def case_ap9():
    start("AP9", "pause_facts carries the auto fields")
    w = world("ap9")
    meter(w, [five_hour(97)])
    f = ap_v(w).get("facts") or {}
    check(f.get("auto") is True and (f.get("auto_line") or "").startswith("AUTO-PAUSE —")
          and f.get("auto_login") == LOGIN_W and (f.get("auto_key") or "").startswith(AP_LABEL_5H + "|")
          and f.get("all") is True and f.get("families") == [],
          "auto True, the line, the key, the login; every model is reached: %s" % f)
    w2 = world("ap9b")
    meter(w2, [five_hour(91)])
    f2 = ap_v(w2).get("facts") or {}
    check(f2.get("auto") is False and f2.get("auto_line") is None and f2.get("auto_key") is None
          and f2.get("auto_login") is None and (f2.get("line") or "").startswith("USAGE PAUSE"),
          "an ordinary PAUSE says auto False and the others None: %s" % f2)


def case_ap10():
    start("AP10", "the refresh nag rides every 2 turns at or above PAUSE, every 10 below (through the hook)")
    w = world("ap10")
    t = window(w, SID_F, FABLE)
    meter(w, [five_hour(91)], age_min=10)
    v = ap_v(w)
    check(v.get("refresh_every") == 2 and "refresh (read 10 min ago)" in (v.get("refresh_line") or ""),
          "the verdict carries refresh_every 2 and the refresh line for a 10-minute-old reading: %s"
          % v.get("refresh_every"))
    wf = world("ap10f")
    meter(wf, [five_hour(91)], age_min=1)
    check(ap_v(wf).get("refresh_line") is None, "…and no refresh line for a reading a minute old")
    got = []
    for _ in range(4):
        h = hook(w, SID_F, t)
        ctx = ((h["json"].get("hookSpecificOutput") or {}).get("additionalContext") or "")
        got.append(sum(1 for l in ctx.splitlines() if "refresh (read" in l))
    check(got == [1, 0, 1, 0], "PAUSE: the nag on turns 1 and 3 of four: %s" % got)
    w2 = world("ap10b")
    t2 = window(w2, SID_F, FABLE)
    meter(w2, [five_hour(50)], age_min=40)
    check(ap_v(w2).get("refresh_every") == 10, "below PAUSE the verdict says 10")
    got2 = []
    for _ in range(12):
        h = hook(w2, SID_F, t2)
        ctx = ((h["json"].get("hookSpecificOutput") or {}).get("additionalContext") or "")
        got2.append(sum(1 for l in ctx.splitlines() if "refresh (read" in l))
    check([i + 1 for i, c in enumerate(got2) if c] == [1, 11], "stale below PAUSE: the nag on turns 1 and 11 of twelve: %s" % got2)
    w3 = world("ap10c")
    t3 = window(w3, SID_F, FABLE)
    meter(w3, [five_hour(97)])
    h = hook(w3, SID_F, t3)
    ctx = ((h["json"].get("hookSpecificOutput") or {}).get("additionalContext") or "")
    check(any(l.startswith("AUTO-PAUSE —") for l in ctx.splitlines()) and h["code"] == 0,
          "the hook hands the AUTO-PAUSE line to the window: %s" % ctx[:50])


def case_ap11():
    start("AP11", "the hard stop and an auto-pause together: level stop, auto_pause True, both lines")
    w = world("ap11")
    flagship_registry(w)
    meter(w, [fable_week(93), five_hour(97)])
    v = ap_v(w)
    lines = v.get("lines") or []
    check(v.get("level") == "stop" and v.get("auto_pause") is True and len(lines) == 2
          and "HARD STOP" in lines[0] and lines[1].startswith("AUTO-PAUSE —"),
          "level stop, auto_pause True, the stop line then the auto line: %s" % lines)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    check(len(out.strip().splitlines()) == 2 and "HARD STOP" in out.splitlines()[0]
          and out.splitlines()[1].startswith("AUTO-PAUSE"), "--line prints both")
    code, out = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 1, "--check exits 1")


def case_ap12():
    start("AP12", "plan windows only: the extra-usage spend window never triggers it")
    w = world("ap12")
    spendw = {"label": "extra usage (month)", "percent": 99, "kind": "month-spend", "model": "",
              "resets_at": None}
    meter(w, [spendw, five_hour(50)], spend=SPEND)
    v = ap_v(w)
    check(v.get("auto_pause") is False and v.get("level") != "auto-pause",
          "extra usage at 99 with no reset time: no auto-pause (%s)" % v.get("level"))
    w2 = world("ap12b")
    spendw2 = dict(spendw, resets_at=iso(now() + datetime.timedelta(days=5)))
    meter(w2, [spendw2], spend=SPEND)
    v2 = ap_v(w2)
    check(v2.get("auto_pause") is False and v2.get("level") != "auto-pause",
          "…nor with a reset time on it (%s)" % v2.get("level"))
    code, out = usage_cli(w2, "--write", "--vendor", "claude", "--login", LOGIN_W,
                          stdin=json.dumps({"plan": {"windows": [], "extraUsage": {
                              "spent": "39", "monthlyLimit": "40", "percentUsed": 99, "currency": "USD"}}}))
    check("auto_pause_window" not in ap_file(w2), "…and a stored spend reading latches nothing")



# --------------------------------------------------------------------------

def main(argv):
    keep = "--keep" in argv
    ROOT.mkdir(parents=True, exist_ok=True)
    print("gate-usage · %s · worlds under %s" % (now().strftime("%Y-%m-%d %H:%M"), ROOT))
    print("  tools from: %s" % source_tool("usage.py").parent)
    before = fingerprint()
    hits_before = marker_hits()
    for case in (case_g2, case_g3, case_g13, case_g4, case_g5, case_g6, case_g7, case_g8, case_g9, case_g10,
                 case_g11, case_g12, case_a1, case_a2, case_a3, case_a4, case_a5, case_a6, case_a7,
                 case_a8, case_a9, case_ua, case_ub, case_uc, case_ud, case_ue,
                 case_u1, case_u2, case_u3, case_u4, case_u5,
                 case_ap1, case_ap2, case_ap3, case_ap4, case_ap5, case_ap6, case_ap7, case_ap8,
                 case_ap9, case_ap10, case_ap11, case_ap12):
        try:
            case()
        except Exception as exc:
            FAILS.append("%s: the case itself raised %r" % (CASE["id"], exc))
            print("  [FAIL] the case itself raised %r" % (exc,))
        if case is case_u1:
            old_fails = [f for f in FAILS if not f.startswith("U1:")]
    start("U6", "the existing cases stay green (G2–G12, A1–A9, U-a–U-e)")
    check(not old_fails, "no check of the existing cases failed (%s)" % (old_fails[:3] or "none"))
    time.sleep(2.0)                   # a detached letter from a PAUSE onset finishes inside its world
    try:
        case_g1(before, hits_before)
    except Exception as exc:
        FAILS.append("G1: the case itself raised %r" % (exc,))
    print("\n===== GATES =====")
    print("  %d checks · %d passed · %d failed" % (PASSES[0] + len(FAILS), PASSES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL  %s" % f)
    if keep:
        print("  scratch kept: %s" % ROOT)
    return 1 if FAILS else 0


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            shutil.rmtree(str(ROOT), ignore_errors=True)
    sys.exit(RESULT)
