#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-login.py — the proof of the login reader: the
engine reads the login the DESKTOP APP is signed in as, says where it read it, never calls the
terminal's .claude.json "the app", and a PAUSE for one login never blocks another's window or
routine. And the scan that hung is bounded.

    python3 tools/gate-login.py           every case (`python` on Windows)
    python3 tools/gate-login.py --keep    leave the worlds for inspection

HERMETIC: every case builds its own world in the SYSTEM TEMP FOLDER (exo-prove-login-<pid>-…,
never under the hub: a mid-run brain push would carry it) — a scratch HOME holding the app's own
data folder in its real shape (macOS Library/Application Support/Claude, or a Windows-shaped
AppData/Roaming/Claude), a .claude.json naming the TERMINAL's login, a scratch hub with its
machine record and registry. Every child runs with the window variables of THIS process removed
unless the case sets its own. The tools under test are tools/usage.py and tools/routine-check.py
BESIDE this gate (a stage, or the hub's tools/ once installed); the tools they lean on
(exo_paths, exo_registry, exo_common, effort, postman, mail, wake-screen and its readers) are the
hub's own, found beside this gate or in the first tools/ above it — copied into each world,
never run in place. Nothing outside the worlds is written; G0 proves it.

  L1  a window's variables name B → (B's email, B, window); the logins map gains B, by "window env"
  L2  no window; the app's config names B; the map knows B → (B, app); --line says `(app)`
  L3  no window; the app's config names B; the map is empty; .claude.json names A → account B,
      login unknown, source app — NEVER A's email, in the resolver, --line or --check; a MUTANT
      that never reads the app's config gives A's email and A's PAUSE (teeth)
  L4  only .claude.json → (A, cli) and the printed line carries `(cli config — not the app's)`
  L5  a PAUSE recorded for A: a window whose variables say B is not paused (--check, the hook);
      one whose variables say A is, its login named `(window)`
  L6  a routine run (no window) with the app signed in as B and a PAUSE for A → not blocked (the
      routine step --check, the effort hook's scheduled-run block); the MUTANT is blocked (teeth)
  L7  --scan over 200 fixture transcripts with --budget-seconds 1 (the scan's time seam) → exit 0,
      ONE stdout line `scan stopped at k of 200 after s s — newest reading so far: …` naming the
      newest reading found so far, `scanning 200 transcripts` once on stderr; without the seam the
      same walk completes and files the newest reading of all; a reading only at the head of a
      transcript longer than TAIL_BYTES is never read; a named pipe among the transcripts is never
      opened (posix); the watchdog ends a read that never returns with the stop line, exit 0
  L8  the logins map is never written from .claude.json (--line, --check, --write, the hook), nor
      from a window's variables this home's app does not hold
  L9  a Windows-shaped home (APPDATA set, the config under it) resolves road (2); an APPDATA that
      names a folder outside this home is not read
  L10 routine-check on two stores with the app signed in as B → B's store is the active one even
      when A's folder is newer; the header says `store: <B> (app)`; a MUTANT that takes the newest
      folder counts A's tasks (teeth); with no account readable, every store is counted and said;
      a cp1252 console still gets the step's ASCII arrows
  L11 a window's variables that leaked into a world whose app does not hold that account are not
      `window` (why the neighbour gates' worlds stay theirs)
  L12 the transcript's bridge-session owner: the cli config's account while the app is signed in
      as B is never taken for the window (a scan files it `unknown`; the window's hook files B);
      an owner the app's own account matches is filed under it
  L13 every surface says the source: the PAUSE line and letter, a meter file's login_source, the
      wake screen's receipts (wake-screen.py unchanged), routine-check's header
  L14 secrets: of the app's config only lastKnownAccountUuid, of .claude.json only the two fields —
      their other bytes appear in no output and no written file

The gate never runs its own file. Stdlib only, Python 3.9, macOS and Windows.
Exit 0 only when every check passes.
"""
import datetime
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

sys.dont_write_bytecode = True
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

if os.environ.get("EXO_GATE_LOGIN_DEPTH"):
    print("gate-login: refusing to run inside its own child (depth mark set)")
    sys.exit(3)
os.environ["EXO_GATE_LOGIN_DEPTH"] = "1"

HERE = Path(__file__).resolve().parent
PY = sys.executable or "python3"
ROOT = Path(tempfile.mkdtemp(prefix="exo-prove-login-%d-" % os.getpid()))
MARK = "GATE-LOGIN-261"
FAILS, PASSES, CASE = [], [0], {"id": ""}

# the invented fleet — nobody's names
LOGIN_A = "heron@example.test"                       # the TERMINAL's login (.claude.json)
ACCT_A = "a0a0a0a0-1111-4111-8111-00000000261a"
LOGIN_B = "plover@example.test"                      # the APP's login
ACCT_B = "b0b0b0b0-2222-4222-8222-00000000261b"
ACCT_X = "c0c0c0c0-3333-4333-8333-00000000261c"      # an account this home's app does not hold
ORG = "0e0e0e0e-4444-4444-8444-00000000261d"
A8, B8, X8 = ACCT_A[:8], ACCT_B[:8], ACCT_X[:8]
SECRET_CFG = "GATE-LOGIN-261-APPCONFIG-NEVER-SHOWN"
SECRET_CLI = "GATE-LOGIN-261-CLITOKEN-NEVER-SHOWN"
CLI_WORDS = "(cli config — not the app's)"
SID_W = "26100000-aaaa-4bbb-8ccc-0000000261aa"       # a window
SID_R = "26100000-aaaa-4bbb-8ccc-0000000261bb"       # a routine run
SONNET, FABLE = "claude-sonnet-5", "claude-fable-5-1"
WINDOW_VARS = ("CLAUDE_CODE_ACCOUNT_UUID", "CLAUDE_CODE_USER_EMAIL", "CLAUDE_CODE_SESSION_ID",
               "CLAUDE_CODE_HOST_SESSION_ID", "CLAUDE_EFFORT", "CLAUDE_CODE_EFFORT_LEVEL",
               "EXO_MACHINE_JSON", "EXO_REGISTRY_JSON", "EXO_USAGE_STATE_DIR", "EXO_NOTIFY",
               "EXO_USAGE_SCAN_TICK", "APPDATA", "EXO_PULSE_STATE_DIR")
UNDER_TEST = ("usage.py", "routine-check.py")
LEANS_ON = ("exo_paths.py", "exo_registry.py", "exo_common.py", "effort.py", "postman.py", "mail.py",
            "collect-openers.py", "opener_carriers.py", "grok_sessions.py", "app_sessions.py",
            "wake-screen.py", "night-check.py")
OPTIONAL = ("opener_carriers.py", "grok_sessions.py", "collect-openers.py", "night-check.py")
REGISTRY = {
    "version": 1, "note": "gate-login's own fixture registry: every name in it is invented.",
    "owner": {"name": "Plover", "short": "plover", "aliases": []},
    "machines": {"north": {"label": "North", "mark": "●", "os": "macos",
                           "hue": {"light": "#2456a4", "dark": "#7fb0e8"}}},
    "minds": [{"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
              {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0f766e", "dark": "#2dd4bf"}}],
    "mind_aliases": {},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Exocortex"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}
SKILL = ("---\nname: gate-routine\ndescription: %s a fixture routine\nmodel: sonnet\n---\n\n"
         "You are a fixture routine.\n\nProcedure:\n1. Say hello.\n2. Do the thing.\n" % MARK)


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


def read_json(path):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def now():
    return datetime.datetime.now().astimezone()


def iso(d):
    return d.replace(microsecond=0).isoformat()


def zulu(d):
    return d.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def hub_tools():
    """The hub's tools/ — beside this gate when installed, else the first tools/ above it that
    holds exo_paths.py (a stage under harvest/)."""
    if (HERE / "exo_paths.py").is_file():
        return HERE
    cur = HERE
    for _ in range(8):
        parent = cur.parent
        if parent == cur:
            break
        if (parent / "tools" / "exo_paths.py").is_file():
            return parent / "tools"
        cur = parent
    return None


def tool_source(name):
    if name in UNDER_TEST:
        return HERE / name
    base = hub_tools()
    return (base / name) if base else HERE / name


def run(args, w, env=None, stdin=None, timeout=90, split=False):
    """A child in the world: THIS process's window variables removed, the world's own set."""
    base = dict(os.environ)
    for k in WINDOW_VARS:
        base.pop(k, None)
    base.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    for k, v in dict(w["env"], **(env or {})).items():
        if v is None:
            base.pop(k, None)
        else:
            base[k] = str(v)
    try:
        p = subprocess.run([str(a) for a in args], input=stdin, cwd=str(w["hub"]), env=base,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE if split else subprocess.STDOUT,
                           timeout=timeout, universal_newlines=True, encoding="utf-8",
                           errors="replace")
        if split:
            return p.returncode, p.stdout or "", p.stderr or ""
        return p.returncode, p.stdout or ""
    except subprocess.TimeoutExpired:
        return (124, "TIMEOUT", "TIMEOUT") if split else (124, "TIMEOUT")


def world(name, app="macos", config=None, stores=(), cli=(LOGIN_A, ACCT_A), logins=None):
    """A world: HOME with the app's data folder (`app`: macos | win | None), its config naming
    `config` (a full account id, or None for no config), a session-store folder per account in
    `stores`, a .claude.json naming `cli` (or None), a hub whose logins map holds `logins`."""
    base = ROOT / name
    home, hub = base / "home", base / "hub"
    for f in (home / "orchestrator-sync", hub / "tools", base / "state", base / "effort",
              home / ".claude" / "projects", base / "projects"):
        f.mkdir(parents=True, exist_ok=True)
    for t in UNDER_TEST + LEANS_ON:
        src = tool_source(t)
        if not src.is_file():
            if t in OPTIONAL:
                continue
            raise RuntimeError("a tool the gate needs is missing: %s" % src)
        shutil.copy2(str(src), str(hub / "tools" / t))
    write_json(hub / "registry.json", REGISTRY)
    write(hub / "INBOX.md", "# INBOX\n\n")
    roots = {"orchestrator": str(hub), "projects": str(base / "projects"),
             "claude": str(home / ".claude"), "home": str(home), "post": str(base / "post")}
    write_json(home / "orchestrator-sync" / "machine.json",
               {"name": "north", "os": platform.system(), "roots": roots})
    env = {"HOME": str(home), "USERPROFILE": str(home), "HOMEDRIVE": None, "HOMEPATH": None,
           "EXO_MACHINE_JSON": str(home / "orchestrator-sync" / "machine.json"),
           "EXO_REGISTRY_JSON": str(hub / "registry.json"),
           "EXO_USAGE_STATE_DIR": str(base / "state"), "EXO_NOTIFY": str(base / "notify.py")}
    write(base / "notify.py", "import sys\n")
    appdir = None
    if app == "macos":
        appdir = home / "Library" / "Application Support" / "Claude"
    elif app == "win":
        appdir = home / "AppData" / "Roaming" / "Claude"
        env["APPDATA"] = str(home / "AppData" / "Roaming")
    if appdir is not None:
        appdir.mkdir(parents=True, exist_ok=True)
        if config:
            write_json(appdir / "config.json", {"locale": "en-US", "gateNote": SECRET_CFG,
                                                "lastKnownAccountUuid": config,
                                                "oauthCache": {"token": SECRET_CFG}})
        for acct in stores:
            (appdir / "claude-code-sessions" / acct / ORG).mkdir(parents=True, exist_ok=True)
    if cli:
        write_json(home / ".claude.json", {"oauthAccount": {"emailAddress": cli[0],
                                                            "accountUuid": cli[1],
                                                            "organizationName": SECRET_CLI},
                                           "primaryApiKeyNote": SECRET_CLI})
    if logins:
        write_json(hub / "logins-north.json",
                   dict((a[:8], {"login": l, "seen": iso(now()), "by": "window env"})
                        for a, l in logins.items()))
    return {"base": base, "home": home, "hub": hub, "env": env, "appdir": appdir}


def window_vars(acct, email, sid=SID_W):
    return {"CLAUDE_CODE_ACCOUNT_UUID": acct, "CLAUDE_CODE_USER_EMAIL": email,
            "CLAUDE_CODE_SESSION_ID": sid}


PROBE_HEAD = (
    "import importlib.util, json, os, sys\n"
    "spec = importlib.util.spec_from_file_location('u', sys.argv[1])\n"
    "u = importlib.util.module_from_spec(spec); spec.loader.exec_module(u)\n"
    "hub = sys.argv[2]\n"
    "roots = u.paths_record(hub)['roots']\n"
    "R = {}\n")


def probe(w, code_text, env=None):
    path = w["base"] / ("probe-%d.py" % (len(list(w["base"].glob("probe-*.py"))) + 1))
    write(path, PROBE_HEAD + code_text + "\nprint('PROBE ' + json.dumps(R))\n")
    code, out = run([PY, path, w["hub"] / "tools" / "usage.py", w["hub"]], w, env=env)
    for line in reversed(out.splitlines()):
        if line.startswith("PROBE "):
            return json.loads(line[6:])
    return {"raw": out[-400:], "code": code}


def usage_cli(w, *args, env=None, stdin=None, split=False):
    return run([PY, w["hub"] / "tools" / "usage.py"] + list(args) + ["--hub", w["hub"]], w,
               env=env, stdin=stdin, split=split)


def usage_lines(out):
    return [l for l in out.splitlines() if l.startswith("USAGE")]


def meter(w, login, windows, account=None, age_min=1.0):
    body = {"vendor": "claude", "machine": "north", "login": login,
            "login_source": "--login", "read_at": iso(now() - datetime.timedelta(minutes=age_min)),
            "source": "fixture %s" % MARK, "windows": windows, "spend": None, "meter": "readable"}
    if account:
        body["account"] = account[:8]
    path = w["hub"] / ("usage-north-claude-%s.json" % login.lower().replace("@", "-at-"))
    write_json(path, body)
    return path


def win(label, pct, kind, model=""):
    return {"label": label, "percent": pct, "kind": kind, "model": model,
            "resets_at": iso(now() + datetime.timedelta(days=2))}


def all_week(pct):
    return win("Weekly · all models", pct, "week")


def fable_week(pct):
    return win("Weekly · Fable", pct, "week-model", "fable")


def transcript(w, sid, model=SONNET, rows=(), project="-gate-hub"):
    path = w["home"] / ".claude" / "projects" / project / ("%s.jsonl" % sid)
    body = [{"type": "user", "message": {"role": "user", "content": "go"}, "uuid": "u-1",
             "timestamp": zulu(now() - datetime.timedelta(minutes=5)), "sessionId": sid},
            {"type": "assistant", "requestId": "req-1", "uuid": "a-1", "sessionId": sid,
             "timestamp": zulu(now() - datetime.timedelta(minutes=4)),
             "message": {"role": "assistant", "model": model, "id": "msg-1",
                         "content": [{"type": "text", "text": "done"}],
                         "usage": {"input_tokens": 10, "output_tokens": 1}}}]
    body.extend(rows)
    write(path, "\n".join(json.dumps(r) for r in body) + "\n")
    return path


def owner_row(sid, acct):
    return {"type": "bridge-session", "sessionId": sid, "bridgeSessionId": "cse_%s" % MARK,
            "lastSequenceNum": 0, "ownerAccountUuid": acct, "ownerOrganizationUuid": ORG}


def usage_row(sid, fable, every, at=None):
    at = at or now() - datetime.timedelta(minutes=2)
    reset = now() + datetime.timedelta(days=3)
    obj = {"plan": {"plan": "max", "windows": [
        {"label": "Weekly · all models", "percentUsed": every, "resetsAt": zulu(reset)},
        {"label": "Weekly · Fable", "percentUsed": fable, "resetsAt": zulu(reset)}]}}
    return {"type": "user", "sessionId": sid, "timestamp": zulu(at), "uuid": "gu-%s" % MARK,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu-1",
                                                     "content": [{"type": "text",
                                                                  "text": json.dumps(obj)}]}]}}


def hook(w, sid, path, env=None, prompt="carry on %s" % MARK):
    ev = {"session_id": sid, "hook_event_name": "UserPromptSubmit", "prompt": prompt,
          "transcript_path": str(path) if path else "", "cwd": str(w["hub"])}
    code, out = run([PY, w["hub"] / "tools" / "effort.py", "--hook", "--vendor", "claude",
                     "--state-dir", w["base"] / "effort"], w, env=env, stdin=json.dumps(ev))
    try:
        d = json.loads(out) if out.strip() else {}
    except ValueError:
        d = {"raw": out}
    ctx = ((d.get("hookSpecificOutput") or {}).get("additionalContext") or "")
    return {"code": code, "out": out, "usage": [l for l in ctx.splitlines() if l.startswith("USAGE")],
            "block": d.get("decision") == "block", "reason": d.get("reason") or ""}


def maps(w):
    return sorted(p.name for p in w["hub"].glob("logins-*.json"))


def mutate(w, name, text):
    """A MUTANT: `text` goes in just above the file's `if __name__ == "__main__":` guard, so it
    is in force both when the file is imported and when it is run."""
    path = w["hub"] / "tools" / name
    with io.open(str(path), encoding="utf-8") as fh:
        src = fh.read()
    guard = '\nif __name__ == "__main__":'
    if guard not in src:
        raise RuntimeError("no main guard in %s — the mutant has nowhere to go" % name)
    at = src.rindex(guard)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src[:at] + text + "\n" + src[at:])


MUTANT_NO_APP = ("\n\ndef app_config_account(roots, env=None):   # MUTANT: the app's config unread\n"
                 "    return '', ''\n")
MUTANT_NEWEST = (
    "\n\ndef active_store(stores, account=None):   # MUTANT: the folder written most recently\n"
    "    best, when = None, -1.0\n"
    "    for store in stores:\n"
    "        folder = os.path.dirname(store)\n"
    "        try:\n"
    "            newest = max(os.path.getmtime(os.path.join(folder, n)) for n in os.listdir(folder))\n"
    "        except (OSError, ValueError):\n"
    "            continue\n"
    "        if newest > when:\n"
    "            best, when = store, newest\n"
    "    return best\n")


# --------------------------------------------------------------------------
# G0 — the rails: the live hub's login and meter files are untouched
# --------------------------------------------------------------------------

def live_hub():
    base = hub_tools()
    return base.parent if base else None


FIXTURE_WORDS = (MARK, LOGIN_A, LOGIN_B, "osprey@example.test", A8, B8, X8, ORG[:8],
                 SECRET_CFG, SECRET_CLI)


def live_hits():
    """[(file, word)] — every fixture word of this gate found in the live hub's login and meter
    files (read, never written; the pulse may rewrite them meanwhile, so the rail is their
    CONTENT, never their bytes or their absence)."""
    hub = live_hub()
    hits = []
    if hub is None:
        return hits
    for p in sorted(hub.iterdir()):
        if p.is_file() and (p.name.startswith("logins-") or p.name.startswith("usage-")):
            try:
                text = p.read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            hits.extend((p.name, word) for word in FIXTURE_WORDS if word in text)
    return hits


# --------------------------------------------------------------------------
# the cases
# --------------------------------------------------------------------------

def case_l1():
    start("L1", "a window's variables name B: (B's email, B, window), and the map learns B")
    w = world("l1", stores=(ACCT_B,))
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))", env=window_vars(ACCT_B, LOGIN_B))
    check(r.get("got") == [LOGIN_B, B8, "window"], "the resolver: %s" % r.get("got"))
    m = read_json(w["hub"] / "logins-north.json") or {}
    row = m.get(B8) or {}
    check(row.get("login") == LOGIN_B and row.get("by") == "window env" and row.get("seen"),
          "logins-north.json gained %s → %s, by window env: %s" % (B8, LOGIN_B, row))
    check(A8 not in m, "…and nothing for the cli config's account (%s)" % sorted(m))
    code, out = usage_cli(w, "--line", "--vendor", "claude", env=window_vars(ACCT_B, LOGIN_B))
    lines = usage_lines(out)
    check(code == 0 and lines and ("USAGE · %s (window) · " % LOGIN_B) in lines[0]
          and LOGIN_A not in out, "--line names B and says (window): %s" % lines[:1])


def case_l2():
    start("L2", "no window; the app's config names B; the map knows B → (B, app)")
    w = world("l2", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))")
    check(r.get("got") == [LOGIN_B, B8, "app"], "the resolver: %s" % r.get("got"))
    meter(w, LOGIN_B, [fable_week(12), all_week(8)], account=ACCT_B, age_min=5)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    want = "USAGE · %s (app) · Fable 12 %% · all 8 %% · read 5 min ago" % LOGIN_B
    check(code == 0 and usage_lines(out) == [want], "--line: %s" % usage_lines(out))


def case_l3():
    start("L3", "the app names B, the map is empty, .claude.json names A: account B, never A's email")
    w = world("l3", config=ACCT_B, stores=(ACCT_B,))
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))\n"
                 "R['login'] = u.app_login(roots)\n"
                 "R['claude_account'] = list(u.claude_account(roots))")
    check(r.get("got") == ["", B8, "app"], "the resolver: account B, login unknown, source app: %s"
          % r.get("got"))
    check(r.get("login") == "unknown" and r.get("claude_account") == ["", B8],
          "app_login is `unknown` and claude_account() — the wrapper — gives B with no email: %s %s"
          % (r.get("login"), r.get("claude_account")))
    meter(w, LOGIN_A, [all_week(95)], account=ACCT_A)            # the terminal's login at PAUSE
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    lines = usage_lines(out)
    check(LOGIN_A not in out and lines and lines[0].startswith(
          "USAGE \u00b7 account %s (app) \u00b7 refresh (no logins map here names this account yet"
          % B8), "--line never names A; it names account %s (app) and says refresh: %s"
          % (B8, lines[:1]))
    code, out = usage_cli(w, "--check", "--vendor", "claude")
    check(code == 0 and not out.strip(), "--check exits 0: A's PAUSE is not B's (%d, %r)"
          % (code, out.strip()[:80]))
    m = world("l3m", config=ACCT_B, stores=(ACCT_B,))
    mutate(m, "usage.py", MUTANT_NO_APP)
    meter(m, LOGIN_A, [all_week(95)], account=ACCT_A)
    code, out = usage_cli(m, "--check", "--vendor", "claude")
    check(code == 1 and LOGIN_A in out, "a MUTANT that never reads the app's config hears A's "
          "PAUSE as B's — the checks above have teeth: %d %s" % (code, out.strip()[:90]))


def case_l4():
    start("L4", "only .claude.json: (A, cli), printed `(cli config — not the app's)`")
    w = world("l4", app=None)
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))")
    check(r.get("got") == [LOGIN_A, A8, "cli"], "the resolver: %s" % r.get("got"))
    meter(w, LOGIN_A, [fable_week(30), all_week(20)], age_min=3)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    lines = usage_lines(out)
    check(lines and lines[0].startswith("USAGE · %s %s · Fable 30 %%" % (LOGIN_A, CLI_WORDS)),
          "the printed line: %s" % lines[:1])
    check("(app)" not in out and "(window)" not in out, "…and never calls it the app's")


def case_l5():
    start("L5", "a PAUSE for A: B's window is not paused, A's window is")
    w = world("l5", config=ACCT_B, stores=(ACCT_A, ACCT_B))
    meter(w, LOGIN_A, [all_week(95)], account=ACCT_A)
    meter(w, LOGIN_B, [all_week(20)], account=ACCT_B)
    t = transcript(w, SID_W)
    code, out = usage_cli(w, "--check", "--vendor", "claude", env=window_vars(ACCT_B, LOGIN_B))
    check(code == 0 and not out.strip(), "--check in B's window: exit 0, silent (%d %r)"
          % (code, out.strip()[:80]))
    code, out = usage_cli(w, "--check", "--vendor", "claude", env=window_vars(ACCT_A, LOGIN_A))
    check(code == 1 and out.startswith("USAGE PAUSE") and ("· %s (window) ·" % LOGIN_A) in out,
          "--check in A's window: exit 1, the PAUSE line naming A (window): %s" % out.strip()[:140])
    h = hook(w, SID_W, t, env=window_vars(ACCT_B, LOGIN_B))
    check(h["code"] == 0 and not any(l.startswith("USAGE PAUSE") for l in h["usage"]),
          "the effort hook in B's window hears no PAUSE: %s" % h["usage"])
    h = hook(w, SID_W, t, env=window_vars(ACCT_A, LOGIN_A))
    check(any(l.startswith("USAGE PAUSE") and ("%s (window)" % LOGIN_A) in l for l in h["usage"]),
          "…in A's window it hears A's PAUSE, A named (window): %s" % h["usage"][:1])


def case_l6():
    start("L6", "a routine run (no window), app signed in as B, a PAUSE for A: not blocked")
    skill = None
    for name, mutant in (("l6", False), ("l6m", True)):
        w = world(name, config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
        if mutant:
            mutate(w, "usage.py", MUTANT_NO_APP)
        meter(w, LOGIN_A, [all_week(95)], account=ACCT_A)        # .claude.json's login, at PAUSE
        skill = w["base"] / "scheduled-tasks" / "gate-routine" / "SKILL.md"
        write(skill, SKILL)
        prompt = ('<scheduled-task name="gate-routine" file="%s">\nThis is an automated run of a '
                  'scheduled task. %s</scheduled-task>' % (skill, MARK))
        code, out = usage_cli(w, "--check", "--vendor", "claude", "--model", "sonnet")
        h = hook(w, SID_R, None, prompt=prompt)
        if not mutant:
            check(code == 0 and not out.strip(), "the routine step `--check` exits 0 (%d %r)"
                  % (code, out.strip()[:80]))
            check(h["code"] == 0 and not h["block"], "the effort hook does not block the scheduled "
                  "run: %s" % (h["reason"][:100] or "not blocked"))
        else:
            check(code == 1 and h["block"] and LOGIN_A in h["reason"],
                  "a MUTANT that never reads the app's config BLOCKS it on A's PAUSE — the check "
                  "has teeth: %d · %s" % (code, h["reason"][:90]))


def scan_world(name):
    w = world(name, config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    base = now()
    for i in range(200):
        sid = "%08d-5ca0-4000-8000-000000000261" % (26100000 + i)
        at = base - datetime.timedelta(days=1, minutes=i)
        fable, every = 10 + i % 40, 5 + i % 30
        if i == 150:                                              # the newest reading of all,
            at, fable, every = base - datetime.timedelta(hours=1), 61, 37   # in an older file
        path = transcript(w, sid, rows=[usage_row(sid, fable, every, at=at)], project="-gate-scan")
        stamp = (base - datetime.timedelta(seconds=i)).timestamp()
        os.utime(str(path), (stamp, stamp))
    return w


def case_l7():
    start("L7", "--scan is bounded: --budget-seconds, a tail of each, one stop line, never a hang")
    w = scan_world("l7")
    code, out, err = usage_cli(w, "--write", "--vendor", "claude", "--scan", "--budget-seconds", "1",
                               env={"EXO_USAGE_SCAN_TICK": "0.01"}, split=True)
    lines = [l for l in out.splitlines() if l.strip()]
    hit = re.match(r"scan stopped at (\d+) of 200 after ([\d.]+) s — newest reading so far: "
                   r"(.*)$", lines[0]) if lines else None
    k = int(hit.group(1)) if hit else -1
    check(code == 0 and len(lines) == 1 and hit and 0 < k < 200,
          "exit 0 and ONE line, stopped part-way (k = %d): %r" % (k, lines[:2]))
    check(err.count("scanning 200 transcripts") == 1, "`scanning 200 transcripts` once on stderr: %r"
          % err.strip()[:80])
    said = hit.group(3) if hit else ""
    check(" in transcript 26100000 (" in said and "Fable 10%" in said and "all models 5%" in said
          and " \u00b7 written usage-north-claude-unknown.json \u00b7 login unknown" in said,
          "the newest reading found so far — the newest-written transcript's, not transcript 150's "
          "(unread) — and where it was filed: %r" % said)
    w2 = scan_world("l7b")
    t0 = time.time()
    code, out, err = usage_cli(w2, "--write", "--vendor", "claude", "--scan", "--budget-seconds", "20",
                               split=True)
    filed = read_json(w2["hub"] / "usage-north-claude-unknown.json") or {}
    pcts = sorted(x.get("percent") for x in filed.get("windows") or [])
    check(code == 0 and "stopped" not in out and out.startswith("usage: written")
          and pcts == [37.0, 61.0] and err.count("scanning 200 transcripts") == 1,
          "without the seam the walk completes and files the newest reading of all (transcript 150: "
          "Fable 61, all 37): %s · %s" % (out.strip()[:90], pcts))
    check(time.time() - t0 < 15, "…in %.1f s" % (time.time() - t0))
    # the tail cap: the tail is TAIL_BYTES, grown ONCE to SCAN_TAIL_MAX when it held no result — a
    # reading at the head of a transcript under 1 MiB is still found; one beyond that cap never is
    w3 = world("l7c", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    big_sid, huge_sid, small_sid = ("26100000-b16b-4000-8000-000000000001",
                                    "26100000-b16c-4000-8000-000000000003",
                                    "26100000-5a11-4000-8000-000000000002")

    def filler(sid, n):
        return [{"type": "user", "sessionId": sid, "uuid": "f-%d" % i, "timestamp":
                 zulu(now() - datetime.timedelta(minutes=30)), "message": {"role": "user",
                 "content": "x" * 2000}} for i in range(n)]
    big = transcript(w3, big_sid, rows=[usage_row(big_sid, 77, 66, at=now() - datetime.timedelta(
        minutes=40))] + filler(big_sid, 200), project="-gate-tail")
    huge = transcript(w3, huge_sid, rows=[usage_row(huge_sid, 88, 80, at=now() - datetime.timedelta(
        minutes=20))] + filler(huge_sid, 600), project="-gate-tail")
    transcript(w3, small_sid, rows=[usage_row(small_sid, 11, 9, at=now() - datetime.timedelta(
        hours=3))], project="-gate-tail")
    code, out = usage_cli(w3, "--write", "--vendor", "claude", "--scan")
    filed = read_json(w3["hub"] / "usage-north-claude-unknown.json") or {}
    pcts = sorted(x.get("percent") for x in filed.get("windows") or [])
    check(262144 < os.path.getsize(str(big)) < (1 << 20) < os.path.getsize(str(huge))
          and pcts == [66.0, 77.0],
          "the once-grown tail (SCAN_TAIL_MAX) finds the reading at the head of a %d-byte transcript "
          "and never the one at the head of a %d-byte transcript: filed %s (88/80 beyond the cap "
          "unread, the 3-hour-old small one older)" % (os.path.getsize(str(big)),
                                                       os.path.getsize(str(huge)), pcts))
    # a named pipe among the transcripts is never opened
    if hasattr(os, "mkfifo"):
        w4 = world("l7d", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
        transcript(w4, small_sid, rows=[usage_row(small_sid, 21, 19)], project="-gate-fifo")
        fifo = w4["home"] / ".claude" / "projects" / "-gate-fifo" / "26100000-f1f0-4000-8000-000000000003.jsonl"
        os.mkfifo(str(fifo))
        t0 = time.time()
        code, out, _err = usage_cli(w4, "--write", "--vendor", "claude", "--scan", "--budget-seconds",
                                    "5", split=True)
        check(code == 0 and out.startswith("usage: written") and time.time() - t0 < 4,
              "a named pipe called *.jsonl is never opened: the scan files the real reading in "
              "%.1f s: %s" % (time.time() - t0, out.strip()[:80]))
    else:
        print("  [n/a ] named pipes: this system has none (Windows) — not counted")
    # the watchdog: a read that never returns ends in the stop line, exit 0
    w5 = world("l7e", config=ACCT_B, stores=(ACCT_B,))
    path = w5["base"] / "watchdog-probe.py"
    write(path, PROBE_HEAD.replace("roots = u.paths_record(hub)['roots']\n", "") +
          "import threading, time\n"
          "prog = {'n': 3, 'k': 1, 'best': None}\n"
          "u.scan_watchdog(prog, 0.3)\n"
          "threading.Event().wait(20)\n"            # a read that never returns
          "print('NEVER REACHED')\n")
    t0 = time.time()
    code, out = run([PY, path, w5["hub"] / "tools" / "usage.py", w5["hub"]], w5, timeout=30)
    took = time.time() - t0
    check(code == 0 and "NEVER REACHED" not in out and re.search(
          r"^scan stopped at 1 of 3 after [\d.]+ s — newest reading so far: none · a read "
          r"did not return; nothing filed$", out.strip()) and took < 10,
          "a read that never returns: the watchdog's one line, exit 0, in %.1f s: %r"
          % (took, out.strip()[:120]))


def case_l8():
    start("L8", "the logins map is never written from .claude.json")
    w = world("l8", app=None)
    meter(w, LOGIN_A, [all_week(30)], account=ACCT_A)
    t = transcript(w, SID_W, rows=[usage_row(SID_W, 20, 10)])
    usage_cli(w, "--line", "--vendor", "claude")
    usage_cli(w, "--check", "--vendor", "claude")
    usage_cli(w, "--write", "--vendor", "claude", stdin=json.dumps(
        {"plan": {"windows": [{"label": "Weekly · all models", "percentUsed": 3,
                               "resetsAt": zulu(now() + datetime.timedelta(days=2))}]}}))
    hook(w, SID_W, t)
    check(maps(w) == [], "no window, only .claude.json: --line, --check, --write and the hook wrote "
                         "no logins map: %s" % maps(w))
    x = world("l8x", config=ACCT_B, stores=(ACCT_B,))
    usage_cli(x, "--line", "--vendor", "claude", env=window_vars(ACCT_X, "osprey@example.test"))
    probe(x, "R['got'] = list(u.app_account(roots, hub=hub))",
          env=window_vars(ACCT_X, "osprey@example.test"))
    check(maps(x) == [], "a window's variables this home's app does not hold write no map: %s" % maps(x))


def case_l9():
    start("L9", "a Windows-shaped home: APPDATA set, the config under it → road (2)")
    w = world("l9", app="win", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))\n"
                 "R['dirs'] = u.app_dirs(roots)")
    check(r.get("got") == [LOGIN_B, B8, "app"], "the resolver: %s" % r.get("got"))
    check(any(d.endswith(os.path.join("AppData", "Roaming", "Claude")) for d in r.get("dirs") or []),
          "…through <APPDATA>\\Claude: %s" % (r.get("dirs") or [])[-1:])
    other = w["base"] / "elsewhere" / "AppData" / "Roaming"
    write_json(other / "Claude" / "config.json", {"lastKnownAccountUuid": ACCT_X})
    shutil.rmtree(str(w["appdir"]))
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))", env={"APPDATA": str(other)})
    check(r.get("got") == [LOGIN_A, A8, "cli"],
          "an APPDATA naming a folder outside this home is not read (another home's): %s" % r.get("got"))


def rc(w, *args, env=None):
    return run([PY, w["hub"] / "tools" / "routine-check.py", "--home", w["home"], "--hub", w["hub"],
                "--codex-home", w["base"] / "codex"] + list(args), w, env=env)


def rc_world(name, config=ACCT_B, logins=None, mutant=False):
    w = world(name, config=config, stores=(ACCT_A, ACCT_B), logins=logins)
    for acct, task_id, label in ((ACCT_A, "gate-a", "Gate A-account task"),
                                 (ACCT_B, "gate-b", "Gate B-account task")):
        folder = w["appdir"] / "claude-code-sessions" / acct / ORG
        skill = w["home"] / ".claude" / "scheduled-tasks" / task_id / "SKILL.md"
        write(skill, SKILL)
        write_json(folder / "scheduled-tasks.json",
                   {"scheduledTasks": [{"id": task_id, "displayName": label, "cronExpression":
                                        "0 8 * * *", "enabled": True, "cwd": "hub",
                                        "filePath": str(skill)}], "recordedSkips": {}})
        stamp = time.time() - (86400 if acct == ACCT_B else 0)   # A's folder is the NEWER one
        for f in folder.iterdir():
            os.utime(str(f), (stamp, stamp))
    if mutant:
        mutate(w, "routine-check.py", MUTANT_NEWEST)
    return w


def case_l10():
    start("L10", "routine-check: the signed-in account's store, never the newest folder")
    w = rc_world("l10", logins={ACCT_B: LOGIN_B})
    code, out = rc(w)
    lines = out.splitlines()
    check(lines and lines[0] == "store: %s (app)" % LOGIN_B, "the header: %r" % (lines[:1],))
    check("STEP: 1 routine will ask permission: Gate B-account task" in out
          and "another account's store" in out and "Gate A-account task" in
          ([l for l in lines if "another account's store" in l] or [""])[0],
          "B's task is the one that will prompt; A's (the newer folder) is another account's")
    code, out = rc(w, env={"PYTHONIOENCODING": "cp1252"})
    check("Traceback" not in out and out.splitlines()[:1] == ["store: %s (app)" % LOGIN_B]
          and "Routines -> the task -> Edit" in out,
          "a cp1252 console: the header prints, and the step's arrows still fall back to -> with "
          "usage.py loaded beside it (its stdout setting is put back)")
    m = rc_world("l10m", logins={ACCT_B: LOGIN_B}, mutant=True)
    code, out = rc(m)
    check("STEP: 1 routine will ask permission: Gate A-account task" in out,
          "a MUTANT that takes the newest folder counts A's — the check has teeth")
    u = rc_world("l10u", config=None)
    code, out = rc(u)
    lines = out.splitlines()
    check(lines and lines[0].startswith("store: unknown — only the cli config (%s, not the app's)"
                                        % LOGIN_A)
          and "STEP: 2 routines will ask permission" in out,
          "no app config: the header says so and every store's unset task is counted: %r"
          % (lines[:1],))
    code, out = rc(w, "--json")
    d = json.loads(out) if out.strip().startswith("{") else {}
    st = d.get("store") or {}
    check(st.get("account") == B8 and st.get("source") == "app" and str(st.get("active") or "")
          .replace("\\", "/").find("/%s/" % ACCT_B) > 0, "--json carries the store: %s" % st)


def case_l11():
    start("L11", "a window's variables leaked into another home's world are not `window`")
    w = world("l11", config=None, stores=())
    r = probe(w, "R['got'] = list(u.app_account(roots, hub=hub))",
              env=window_vars(ACCT_X, "osprey@example.test"))
    check(r.get("got") == [LOGIN_A, A8, "cli"],
          "an account this home's app does not hold: the cli config, named as such: %s" % r.get("got"))
    w2 = world("l11b", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    r = probe(w2, "R['got'] = list(u.app_account(roots, hub=hub))",
              env=window_vars(ACCT_X, "osprey@example.test"))
    check(r.get("got") == [LOGIN_B, B8, "app"], "…and with the app's config here, the app's: %s"
          % r.get("got"))


def case_l12():
    start("L12", "a bridge owner that is the cli config's account never stands for the app's window")
    w = world("l12", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    sid = "26100000-b0b0-4000-8000-000000000012"
    t = transcript(w, sid, rows=[owner_row(sid, ACCT_A), usage_row(sid, 44, 33)])
    code, out = usage_cli(w, "--write", "--vendor", "claude", "--scan")
    got = sorted(p.name for p in w["hub"].glob("usage-north-claude-*.json"))
    body = read_json(w["hub"] / "usage-north-claude-unknown.json") or {}
    check(got == ["usage-north-claude-unknown.json"] and "cli config's account"
          in str(body.get("login_source")),
          "a scan of a window whose bridge record names A (the cli's) while the app is B: filed "
          "`unknown`, never A: %s · %s" % (got, body.get("login_source")))
    h = hook(w, sid, t, env=window_vars(ACCT_B, LOGIN_B, sid=sid))
    bfile = w["hub"] / ("usage-north-claude-%s.json" % LOGIN_B.replace("@", "-at-"))
    body = read_json(bfile) or {}
    check(body.get("login") == LOGIN_B and body.get("account") == B8
          and str(body.get("login_source")).startswith("window — this window"),
          "the same window's hook files its own reading under B, from its variables: %s · %s"
          % (body.get("login"), body.get("login_source")))
    x = world("l12b", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    sid2 = "26100000-b0b0-4000-8000-000000000013"
    transcript(x, sid2, rows=[owner_row(sid2, ACCT_B), usage_row(sid2, 55, 22)])
    code, out = usage_cli(x, "--write", "--vendor", "claude", "--scan")
    body = read_json(x["hub"] / ("usage-north-claude-%s.json" % LOGIN_B.replace("@", "-at-"))) or {}
    check(body.get("login") == LOGIN_B and str(body.get("login_source")).startswith(
          "transcript — scan: transcript owner = the logins map"),
          "a bridge owner that IS the app's account is filed under it: %s" % body.get("login_source"))


def case_l13():
    start("L13", "every surface says the source in one word")
    w = world("l13", config=ACCT_B, stores=(ACCT_B,), logins={ACCT_B: LOGIN_B})
    meter(w, LOGIN_B, [all_week(96)], account=ACCT_B)
    code, out = usage_cli(w, "--line", "--vendor", "claude")
    lines = usage_lines(out)
    check(lines and lines[0].startswith("USAGE PAUSE — all models 96 percent")
          and ("· %s (app) ·" % LOGIN_B) in lines[0],
          "the PAUSE line names the login and (app): %s" % lines[:1])
    r = probe(w, "v = u.evaluate(hub, 'claude')\nR['letter'] = v.get('letter')\n"
                 "R['src'] = v.get('login_source')")
    check(str(r.get("letter") or "").endswith("· %s (app)" % LOGIN_B) and r.get("src") == "app",
          "the PAUSE letter ends with the login and its source: %r" % str(r.get("letter"))[-60:])
    t = transcript(w, SID_W, rows=[usage_row(SID_W, 12, 9)])
    usage_cli(w, "--write", "--vendor", "claude", stdin=json.dumps(
        {"plan": {"windows": [{"label": "Weekly · all models", "percentUsed": 4,
                               "resetsAt": zulu(now() + datetime.timedelta(days=2))}]}}),
        env=window_vars(ACCT_B, LOGIN_B))
    body = read_json(w["hub"] / ("usage-north-claude-%s.json" % LOGIN_B.replace("@", "-at-"))) or {}
    check(body.get("login_source") == "window — this session" and body.get("account") == B8,
          "a meter file's login_source opens with the word: %r" % body.get("login_source"))
    # the wake screen: wake-screen.py as it stands, through usage.py's session_login
    if not (w["hub"] / "tools" / "wake-screen.py").is_file():
        check(False, "tools/wake-screen.py is not in the hub — the wake check cannot run; named, "
                     "never passed")
        return
    meter(w, LOGIN_B, [fable_week(9), all_week(6)], account=ACCT_B, age_min=3)
    empty = w["base"] / "ps-empty.txt"
    write(empty, "")
    for env, word in ((window_vars(ACCT_B, LOGIN_B), "window"), ({}, "app")):
        code, out = run([PY, w["hub"] / "tools" / "wake-screen.py"], w,
                        env=dict(env, EXO_NIGHT_PS=str(empty)))
        first = out.splitlines()[0] if out.splitlines() else ""
        check(first.startswith("WAKE · ") and ("USAGE · %s (%s) · Fable 9 %%" % (LOGIN_B, word))
              in first, "the wake screen's receipts say (%s): %r" % (word, first[-110:]))


def case_l14():
    start("L14", "secrets: one key of the app's config, two fields of .claude.json — nothing else")
    leaks = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.name in ("config.json", ".claude.json") or p.suffix == ".py":
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if SECRET_CFG.encode() in data or SECRET_CLI.encode() in data:
            leaks.append(str(p.relative_to(ROOT)))
    check(not leaks, "no file any case wrote carries a byte of either file beyond the fields read: %s"
          % leaks[:4])
    check(not any(SECRET_CFG in o or SECRET_CLI in o for o in OUTPUTS),
          "and no output printed one (%d outputs read)" % len(OUTPUTS))


OUTPUTS = []
_run = run


def run(args, w, env=None, stdin=None, timeout=90, split=False):   # noqa: F811 — every output kept
    got = _run(args, w, env=env, stdin=stdin, timeout=timeout, split=split)
    OUTPUTS.extend(x for x in got[1:] if isinstance(x, str))
    return got


# --------------------------------------------------------------------------

def main(argv):
    keep = "--keep" in argv
    print("gate-login · %s · worlds under %s" % (now().strftime("%Y-%m-%d %H:%M"), ROOT))
    print("  under test: %s · leaning on: %s" % (HERE, hub_tools()))
    if hub_tools() is None:
        print("  STOP: no tools/exo_paths.py beside this gate or above it — the gate cannot run")
        return 2
    before = live_hits()
    for case in (case_l1, case_l2, case_l3, case_l4, case_l5, case_l6, case_l7, case_l8, case_l9,
                 case_l10, case_l11, case_l12, case_l13, case_l14):
        try:
            case()
        except Exception as exc:
            FAILS.append("%s: the case itself raised %r" % (CASE["id"], exc))
            print("  [FAIL] the case itself raised %r" % (exc,))
    start("G0", "the rails: nothing of this gate reached the live hub")
    after = live_hits()
    check(not before and not after, "no fixture login, account or marker in the live hub's "
                                    "logins-*.json or usage-*.json, before or after: %s" % after[:4])
    stray = [p.name for p in HERE.iterdir() if p.name == "__pycache__"]
    check(not stray, "no __pycache__ beside the tools under test: %s" % stray)
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
