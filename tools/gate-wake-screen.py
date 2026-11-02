#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-wake-screen.py — the wake screen's gate: the first screen at a wake says where we left off.

    python3 tools/gate-wake-screen.py            every case (python on Windows)
    python3 tools/gate-wake-screen.py --keep     leave the world for inspection

HERMETIC: one world under the system temp folder (tempfile.mkdtemp) — a HOME with the app's
session store in its real shape, a machine record naming a scratch hub and a scratch projects
root, twelve lanes in real git repositories, the pulse's live file, the hygiene queue and the
routine task store. The tools run from a COPY inside that world; nothing of this machine's own is
read or written, and the live tree is never touched.

  W1  the shape          receipts line · LAST WORKED · one line per lane with dot, lane, where
                         (<= 12 words), the `!` issue, next, machine, when, ▶ OPEN · the hygiene
                         line · the plate (mark alone, then the path alone in a fence)
  W2  the hub's first reply is that screen — the tool takes no identity: the hub's and the
                         Desk's runs print byte-identical LAST WORKED blocks (W5 below is the
                         Desk's half); the ritual line itself is the hub's install move
  W3  the strip          --html is the same block, dated; --inject puts ONE strip right after
                         <body>, replaces it on a second run, leaves a page with no <body> alone;
                         the staged orchestrator.py calls it once, after the tree is drawn
  W4  twelve lanes       eight shown, ranked by last exchange; a captured lane ranks by its last
                         real turn and never by the capture's write; a shared STATUS in a
                         two-lane folder ranks neither lane; a stale opener is flagged inline
  W5  the Desk           the same screen from a window titled as the Desk
  W6  Windows-true       a cp1252 console prints it with no traceback; the Windows store path
                         (APPDATA) is read; no path literal in the tool; under two seconds
  W7  hygiene silence    0 in the queue and every routine in Bypass → neither line is printed;
                         3 in the queue and 2 routines unset → both lines, with the names
  W8  the sync verdict the receipts line ends with the one-line verdict;
                         `1 repo with no carrier: … · 1 folder with no repo: …` under the hygiene
                         line; both words said → the carrier line is silent and the tail says synced
  W9  the night line the night check's last line — word for word
                         what `night-check.py --line` says in the same world — sits under the
                         hygiene lines, just above the plate, ALWAYS (the hygiene lines at zero too);
                         a waiter the check cannot clear turns it into `CAN WAKE FABLE: …`; the strip
                         carries it with the whole list on hover; and the receipts carry
                         usage.py's own words for the app's login, before the sync verdict
  W10 the lane's own issue a STATUS two lanes share carries `! KILO/ONE …`,
                         `! KILO/TWO …` and a bare `! project …` line: each lane's line shows its
                         own, the bare one shows on neither, and each lane's dot is amber only for
                         its own `!`; lane_next_move's step 2 takes a to-do that STARTS with the
                         lane's name, never one that only mentions it
  W11 the archive count  a queue with items of two logins, one archived and one gone from the
                         store, counts only this login's live ones — the login from the app's
                         config, then from the window's own variables; an item's `account` field
                         is read when present; no login readable: every live one
  W12 a BOM'd queue      the queue file PowerShell writes (UTF-8 with a BOM) is read and counted
  W13 the no-repo ask    names init · stays-here · ignore and every folder; a folder ruled ignore or
                         stays-here is silent, init is owed; the seen file marks a folder `new`
                         once, then `noted`, and the line says `… and K more, ruled none`; only the
                         plain text run writes it
  W14 the clause         (G11) with the engine beside the hub and a ledger note that names
                         no payload, the receipts line's tail equals sync-verdict.py's own line,
                         ` · 1 ledger line unreadable (STATUS.md:8)` included, byte for byte

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
from datetime import datetime, timedelta
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
TOOLS = ("wake-screen.py", "app_sessions.py", "collect-openers.py", "opener_carriers.py",
         "exo_common.py", "exo_registry.py", "exo_paths.py", "routine-check.py",
         "grok_sessions.py", "sync-verdict.py", "night-check.py", "usage.py", "postman.py", "mail.py")
OPTIONAL = ("opener_carriers.py", "grok_sessions.py", "sync-verdict.py", "night-check.py", "usage.py",
            "postman.py", "mail.py")
FAILS, PASSES = [], [0]
CASE = [""]

REGISTRY = {
    "version": 1,
    "note": "gate-wake-screen's own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {
        "north": {"label": "North", "mark": "\u25cf", "os": "macos",
                  "hue": {"light": "#2456a4", "dark": "#7fb0e8"}},
        "south": {"label": "South", "mark": "\u258e", "os": "windows",
                  "hue": {"light": "#9a6b3a", "dark": "#d4a373"}},
    },
    "minds": [{"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
              {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
               "hue": {"light": "#0f766e", "dark": "#2dd4bf"}}],
    "mind_aliases": {},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Hubfolder"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}


def source_tool(name):
    """Beside this gate first (a staged build), else the hub's tools/ the record names."""
    here = HERE / name
    if here.is_file():
        return here
    try:
        rec = json.load(io.open(str(Path.home() / OLDER_SYNC / "machine.json"),
                                encoding="utf-8"))
        return Path(rec["roots"]["orchestrator"]) / "tools" / name
    except Exception:
        return HERE.parent / "tools" / name


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


def iso(ts):
    return datetime.fromtimestamp(ts).astimezone().replace(microsecond=0).isoformat()


def run(args, env, cwd=None, extra=None, timeout=60):
    base = dict(os.environ)
    base.update({"PYTHONDONTWRITEBYTECODE": "1", "GIT_TERMINAL_PROMPT": "0"})
    for k, v in list(env.items()) + list((extra or {}).items()):
        if v is None:
            base.pop(k, None)
        else:
            base[k] = str(v)
    t0 = time.time()
    p = subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None, env=base,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return p.returncode, p.stdout, time.time() - t0


def git(repo, *args, env=None):
    e = dict(os.environ)
    e.update({"GIT_AUTHOR_NAME": "gate", "GIT_AUTHOR_EMAIL": "gate@example.invalid",
              "GIT_COMMITTER_NAME": "gate", "GIT_COMMITTER_EMAIL": "gate@example.invalid",
              "GIT_TERMINAL_PROMPT": "0"})
    e.update(env or {})
    p = subprocess.run(["git"] + list(args), cwd=str(repo), env=e, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.stdout.strip()


def set_mtime(path, ts):
    os.utime(str(path), (ts, ts))


# ── the world ────────────────────────────────────────────────────────────────

NOW = time.time()
H = 3600.0

# (project folder, lane, hours since its LAST EXCHANGE, how that exchange is recorded)
#   opener  = the opener's `written:`       window = the app store's lastActivityAt
#   status  = STATUS.md mtime (one-lane folder only)
LANES = [
    ("alpha", "Alpha", 1.0, "opener"),
    ("bravo", "Bravo/Main", 2.0, "window"),
    ("charlie", "Charlie", 3.0, "status"),
    ("delta", "Delta", 4.0, "opener"),       # its opener is STALE (head not in history)
    ("echo", "Echo", 5.0, "captured"),       # captured 1 min ago; its real last turn 5 h ago
    ("foxtrot", "Foxtrot", 6.0, "opener"),
    ("golf", "Golf", 7.0, "opener"),
    ("hotel", "Hotel", 8.0, "opener"),
    ("india", "India", 9.0, "opener"),
    ("juliet", "Juliet", 10.0, "opener"),
    ("kilo", "Kilo/One", 20.0, "opener"),    # a two-lane folder whose STATUS was written just now
    ("kilo", "Kilo/Two", 21.0, "opener"),
]
EXPECT_ORDER = ["Alpha", "Bravo/Main", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]


def make_world():
    # A builder running a staged copy beside the landed gate names its own prefix, so a
    # neighbour's sweep or count of exo-gate-wake-* worlds never meets this run's.
    base = Path(tempfile.mkdtemp(prefix=os.environ.get("EXO_GATE_WAKE_PREFIX") or "exo-gate-wake-"))
    home, hub, projects = base / "home", base / "hub", base / "projects"
    for d in (home, hub / "tools", projects):
        d.mkdir(parents=True, exist_ok=True)
    beside, from_hub = [], []
    for t in TOOLS:
        src = source_tool(t)
        if not src.is_file():
            if t in OPTIONAL:
                continue
            raise SystemExit("gate-wake-screen: %s not found beside the gate or in the hub" % t)
        shutil.copy2(str(src), str(hub / "tools" / t))
        (beside if src.parent == HERE else from_hub).append(t)
    print("  tools beside the gate: %s" % (", ".join(beside) or "none"))
    print("  tools from the hub:    %s" % (", ".join(from_hub) or "none"))
    write_json(hub / "registry.json", REGISTRY)
    machine = base / "machine.json"
    write_json(machine, {"name": "north", "os": "gate",
                         "roots": {"orchestrator": str(hub), "projects": str(projects),
                                   "home": str(home), "claude": str(home / ".claude"),
                                   "codex": str(home / ".codex")}})
    store = home / "Library" / "Application Support" / "Claude" / "claude-code-sessions" / "acct" / "org"
    store.mkdir(parents=True, exist_ok=True)
    env = {"HOME": str(home), "USERPROFILE": str(home), "APPDATA": str(home / "AppData" / "Roaming"),
           "EXO_MACHINE_JSON": str(machine), "EXO_REGISTRY_JSON": str(hub / "registry.json"),
           "COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_OUT": None,
           "CLAUDE_CODE_SESSION_ID": None, "EXO_SESSION_TITLE": None, "PYTHONIOENCODING": "utf-8",
           # this window's own login never reaches the world (W11 names one when it wants one)
           "CLAUDE_CODE_ACCOUNT_UUID": None, "CLAUDE_CODE_USER_EMAIL": None,
           # the night check reads a process table the gate hands it, never this machine's
           "EXO_NIGHT_PS": str(base / "ps-empty.txt"), "EXO_USAGE_STATE_DIR": str(base / "ustate")}
    write(base / "ps-empty.txt", "")
    w = {"base": base, "home": home, "hub": hub, "projects": projects, "store": store,
         "env": env, "machine": machine}
    folders = {}
    for folder, lane, hours, how in LANES:
        repo = projects / folder
        if folder not in folders:
            repo.mkdir(parents=True, exist_ok=True)
            git(repo, "init", "-q")
            write(repo / "README.md", "gate project %s\n" % folder)
            status = ("# %s\n\n## Now\n%s stands where the gate put it. Second sentence.\n\n"
                      "## To do\n- [ ] ! fix the %s valve before anything else\n"
                      "- [ ] the %s next step\n" % (folder, folder, folder, folder))
            write(repo / "STATUS.md", status)
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "first")
            folders[folder] = git(repo, "rev-parse", "--short", "HEAD")
        head = folders[folder]
        suffix = lane.split("/", 1)[1] if "/" in lane and folder in ("kilo", "bravo") else ""
        name = "OPENER-%s.md" % suffix if folder == "kilo" else "OPENER.md"
        ts = NOW - hours * H
        by = "ACT \u2014 %s: gate sitting" % lane
        written = ts
        if how in ("window", "status"):
            written = NOW - 30 * H            # an old opener; the exchange is elsewhere
        if how == "captured":
            written = NOW - 60                 # the capture wrote it a minute ago
            by = "ACT \u2014 %s: gate sitting \u00B7 captured by hub" % lane
        if how == "opener" and folder != "kilo":
            written = ts
        header = {
            "lane": lane, "written": iso(written), "by": by, "on": "NORTH",
            "head": "deadbee" if folder == "delta" else head,
            "status_updated": iso(NOW + 60), "where": "%s where-words for the gate row" % lane,
            "next": "machine", "depends_on": "nothing",
            "open_in": "%s on the NORTH \u00B7 fresh session" % folder, "model": "SONNET \u00B7 HIGH",
            "judgment": "none"}
        body = ("read the project status/memory first.\n\n1. carry the %s parts to the bench\n"
                "2. then the rest\n" % lane)
        write(repo / name, "".join("%s: %s\n" % kv for kv in header.items()) + "---\n" + body)
        # STATUS mtimes: old, except where the case says otherwise
        st = repo / "STATUS.md"
        if folder == "kilo":
            set_mtime(st, NOW - 60)            # shared STATUS written just now: ranks NEITHER lane
        elif how == "status":
            set_mtime(st, ts)
        elif how == "captured":
            set_mtime(st, NOW - 60)            # the capture's own STATUS write
        else:
            set_mtime(st, NOW - 40 * H)
        if how in ("window", "captured"):
            lid = "local_gate%s" % folder
            write_json(store / ("%s.json" % lid), {
                "sessionId": lid, "cliSessionId": "cli-%s" % folder,
                "title": "%s \u2014 %s: gate window" % ("ACT" if how == "window" else "ARCH", lane),
                "isArchived": how != "window", "lastActivityAt": int(ts * 1000),
                "lastFocusedAt": int(ts * 1000), "model": "claude-sonnet-5", "cwd": str(repo)})
    write_json(hub / "live-sessions-north.json",
               {"machine": "north", "when": iso(NOW - 120), "live_minutes": 10, "sessions": []})
    write_json(hub / "post-north.json", {"machine": "north", "letters": {
        "pm-aaaaaaaaaaaa": {"state": "waiting", "to": "NORTH/Alpha"},
        "pm-bbbbbbbbbbbb": {"state": "delivered", "to": "NORTH/Alpha"}}})
    set_queue(w, 3)
    set_routines(w, unset=("Gate watcher one", "Gate watcher two"))
    return w


def store_window(folder, lid, title, archived=False):
    """One window's record in the app's store, in the real shape (app_sessions.py's notes)."""
    write_json(folder / ("%s.json" % lid), {
        "sessionId": lid, "cliSessionId": "cli-%s" % lid, "title": title,
        "isArchived": bool(archived), "lastActivityAt": int((NOW - 30 * H) * 1000),
        "lastFocusedAt": int((NOW - 30 * H) * 1000), "model": "claude-sonnet-5", "cwd": ""})


def set_queue(w, n):
    """The queue in its REAL shape — {sessionId, title, receipt, account} per item, the way the
    hygiene watcher writes it — each item a live ARCH window the app's store still holds."""
    items = []
    for i in range(n):
        lid = "local_gateq%d" % i
        store_window(w["store"], lid, "ARCH \u2014 Gate/Queued%d: closed" % i)
        items.append({"sessionId": lid, "title": "ARCH \u2014 Gate/Queued%d: closed" % i,
                      "receipt": "2 h quiet \u00b7 proof: a gate receipt", "account": "acct"})
    write_json(w["hub"] / "hygiene-archive-queue-north.json",
               {"written": iso(NOW), "vendor": "claude", "items": items})


def set_routines(w, unset=(), bypass=("Gate bypass task",)):
    tasks = []
    for name in unset:
        tasks.append({"id": name.lower().replace(" ", "-"), "displayName": name,
                      "cronExpression": "0 8 * * *", "enabled": True})
    for name in bypass:
        tasks.append({"id": name.lower().replace(" ", "-"), "displayName": name,
                      "cronExpression": "0 9 * * *", "enabled": True,
                      "permissionMode": "bypassPermissions"})
    tasks.append({"id": "gate-disabled", "displayName": "Gate disabled task",
                  "cronExpression": "0 9 * * *", "enabled": False})
    write_json(w["store"].parent / "org" / "scheduled-tasks.json",
               {"scheduledTasks": tasks, "recordedSkips": {}})


def screen(w, *args, extra=None):
    code, out, took = run([PY, str(w["hub"] / "tools" / "wake-screen.py")] + list(args),
                          w["env"], cwd=w["hub"], extra=extra)
    return code, out.decode("utf-8", "replace"), took


def lw_block(text):
    lines = text.splitlines()
    try:
        i = lines.index("LAST WORKED")
    except ValueError:
        return []
    out = []
    for line in lines[i + 1:]:
        if not line.strip():
            break
        out.append(line)
    return out


def lane_of_line(line):
    m = re.match(r"^(?:\u26A0 [^\u2014]*\u2014 [^\u2014]*\u2014 )?\S+ (\S+) \u2014", line)
    return m.group(1) if m else ""


# ── the cases ────────────────────────────────────────────────────────────────

def case_w1(w):
    start("W1", "the shape, from real bytes")
    code, out, _ = screen(w)
    check(code == 0, "exit 0 (%d)" % code)
    lines = out.splitlines()
    check(bool(lines) and lines[0].startswith("WAKE \u00B7 ") and " \u00B7 NORTH \u00B7 " in lines[0],
          "the first line is the receipts line: %r" % (lines[0] if lines else ""))
    check("letter" not in lines[0].lower(), "the receipts line carries no mail count to the person (the Lane-mail law): %r" % lines[0][:120])
    check("pulse 2 min ago" in lines[0], "the pulse's own age from live-sessions-north.json")
    block = lw_block(out)
    check(len(block) == 8, "LAST WORKED holds eight lines (%d)" % len(block))
    first = block[0] if block else ""
    check(first.startswith("\U0001F7E1 Alpha \u2014 Alpha where-words for the gate row"),
          "state dot · lane · where, from the opener's own where: line: %r" % first[:80])
    check("! fix the alpha valve before anything else" in first,
          "the open issue is the lane's own: in a folder with ONE opener, every `!` is the lane's, "
          "so it is the project's first `!` item, verbatim")
    check("next: carry the Alpha parts to the bench" in first and "NORTH \u00B7 60 min ago" in first,
          "the lane's own next move (its opener's first step), the machine the opener names, "
          "the last exchange's age")
    check(first.endswith("\u25B6 OPEN OPENER.md"), "▶ OPEN names the opener file when no window holds the lane")
    where = first.split(" \u2014 ")[1]
    check(len(where.split()) <= 12, "where is at most twelve words (%d)" % len(where.split()))
    bravo = [l for l in block if " Bravo/Main " in l]
    check(bool(bravo) and bravo[0].endswith("\u25B6 [OPEN](#local_gatebravo)"),
          "a lane whose window the app still holds opens THAT window: %r" % (bravo[0][-40:] if bravo else ""))
    check("3 sessions to archive \u2014 say archive" in out, "the hygiene line from the queue file")
    tail = lines[-4:]
    check(tail[0] == "\u25CF North" and tail[1] == "```" and tail[2] == str(w["hub"] / "tree.html")
          and tail[3] == "```", "the plate: the registry's mark alone, then the path alone in a fence: %r" % tail)


def case_w2_w5(w):
    start("W2 + W5", "the hub's first reply and the Desk's wake print the same screen")
    _c, hub_out, _t = screen(w, extra={"EXO_SESSION_TITLE": "ACT \u2014 Hubfolder/hub: gate",
                                       "CLAUDE_CODE_SESSION_ID": "cli-hub"})
    _c, desk_out, _t = screen(w, extra={"EXO_SESSION_TITLE": "ACT \u2014 Hubfolder/Desk: gate",
                                        "CLAUDE_CODE_SESSION_ID": "cli-desk"})
    check(lw_block(hub_out) and lw_block(hub_out) == lw_block(desk_out),
          "LAST WORKED is byte-identical from the hub's window and the Desk's")
    check(hub_out.splitlines()[-4:] == desk_out.splitlines()[-4:], "and so is the plate")


def case_w3(w):
    start("W3", "the dated strip on the tree page")
    code, out, _ = screen(w, "--html")
    check(code == 0 and "<!-- front-door:start -->" in out and "<!-- front-door:end -->" in out,
          "--html prints one marked strip")
    check("LAST WORKED \u00B7 " in out and re.search(r"LAST WORKED \u00B7 \w{3} \d{4}-\d\d-\d\d \d\d:\d\d", out),
          "the strip is dated")
    check(out.count("<li title=") == 8, "the same eight lanes, each line with its source on hover")
    check("3 sessions to archive" in out, "the hygiene line rides the strip too")
    page = w["base"] / "tree.html"
    write(page, "<!doctype html><html><head><title>t</title></head><body class=\"x\">\n<header>tree</header></body></html>\n")
    code1, _o, _t = screen(w, "--inject", str(page))
    code2, _o, _t = screen(w, "--inject", str(page))
    text = io.open(str(page), encoding="utf-8").read()
    check(code1 == 0 and code2 == 0, "--inject twice exits 0 both times")
    check(text.count("<!-- front-door:start -->") == 1, "one strip after two injections, never two")
    check(text.index("<body class=\"x\">") < text.index("front-door:start") < text.index("<header>tree"),
          "the strip sits right after <body>, before the page's own header")
    bare = w["base"] / "nobody.html"
    write(bare, "no body tag here\n")
    code3, _o, _t = screen(w, "--inject", str(bare))
    check(code3 == 1 and io.open(str(bare), encoding="utf-8").read() == "no body tag here\n",
          "a page with no <body> is left exactly as it was")
    orch = source_tool("orchestrator.py") if (HERE / "orchestrator.py").is_file() else HERE.parent / "orchestrator.py"
    src = io.open(str(orch), encoding="utf-8").read() if orch.is_file() else ""
    calls = [l for l in src.splitlines() if re.match(r"\s+front_door\(tree_path\)", l)]
    check(len(calls) == 1 and "wake-screen.py" in src and "--inject" in src,
          "the staged orchestrator.py calls the strip once, after the tree is drawn (%s)" % orch)


def case_w4(w):
    start("W4", "twelve lanes: eight shown, ranked by the last exchange")
    _c, out, _t = screen(w)
    block = lw_block(out)
    order = [lane_of_line(l) for l in block]
    check(order == EXPECT_ORDER, "the order is the last exchange's: %s" % order)
    check("Kilo/One" not in out and "Kilo/Two" not in out,
          "a STATUS shared by two lanes, written a minute ago, ranks neither lane (they sit at 20 h)")
    echo = [l for l in block if " Echo " in l]
    check(bool(echo) and "NORTH \u00B7 5 h ago" in echo[0],
          "the captured lane ranks by its last real turn (5 h), not the capture's write (1 min)")
    delta = [l for l in block if " Delta " in l]
    check(bool(delta) and delta[0].startswith("\u26A0 STALE OPENER"),
          "the stale opener is flagged inline, first on its line: %r" % (delta[0][:60] if delta else ""))
    check(bool(delta) and "\U0001F534 Delta" in delta[0], "and its dot is red, by the collector's own rule")
    charlie = [l for l in block if " Charlie " in l]
    check(bool(charlie) and "3 h ago" in charlie[0], "a one-lane folder ranks by its STATUS mtime")
    code, data, _t = screen(w, "--limit", "12")
    check(len(lw_block(data)) == 12, "--limit 12 shows all twelve")


def case_w6(w):
    start("W6", "Windows-true and fast")
    code, out, took = screen(w, extra={"PYTHONIOENCODING": "cp1252"})
    check(code == 0 and b"Traceback" not in out.encode("utf-8"), "a cp1252 console prints it, exit 0")
    check("[A] Alpha" in out and "> OPEN" in out, "the marks fall back to ASCII there")
    src = io.open(str(w["hub"] / "tools" / "wake-screen.py"), encoding="utf-8").read()
    src2 = io.open(str(w["hub"] / "tools" / "app_sessions.py"), encoding="utf-8").read()
    lits = [p for p in ("/tmp", "/Users/", "C:\\\\Users", "D:\\\\Projects") if p in src or p in src2]
    check(not lits, "no path literal in the tools (%s)" % lits)
    # the Windows store: the same record under %APPDATA%
    win = w["home"] / "AppData" / "Roaming" / "Claude" / "claude-code-sessions" / "a" / "o"
    write_json(win / "local_gatewin.json", {
        "sessionId": "local_gatewin", "cliSessionId": "cli-win", "title": "ACT \u2014 Zulu/Win: live",
        "isArchived": False, "lastActivityAt": int((NOW - 30) * 1000),
        "lastFocusedAt": int((NOW - 30) * 1000)})
    _c, out2, _t = screen(w)
    check("Zulu/Win" in out2 and "#local_gatewin" in out2,
          "a live window read from the Windows store layout earns a line of its own")
    (win / "local_gatewin.json").unlink()
    times = []
    for _ in range(3):
        _c, _o, took = screen(w)
        times.append(took)
    check(max(times) < 2.0, "under two seconds, three runs: %s" % ", ".join("%.2f s" % t for t in times))


def case_w7(w):
    start("W7", "the hygiene line is silent at zero")
    set_queue(w, 0)
    set_routines(w, unset=())
    _c, out, _t = screen(w)
    check("to archive" not in out and "will ask permission" not in out,
          "0 in the queue and every enabled routine in Bypass: neither line")
    set_queue(w, 3)
    set_routines(w, unset=("Gate watcher one", "Gate watcher two"))
    _c, out, _t = screen(w)
    rc_src = io.open(str(w["hub"] / "tools" / "routine-check.py"), encoding="utf-8").read()
    if "def unset_tasks(" in rc_src:
        check("2 routines will ask permission: Gate watcher one, Gate watcher two \u2014 say routines" in out,
              "two enabled routines with no mode: one line naming both (the disabled one is not "
              "counted) — read through BQ-148's routine-check")
    else:
        # the routine check's unset list not installed yet: the screen must say NOTHING about routines rather than a
        # wrong count; the named line is proved again once routine-check.py carries unset_tasks.
        check("will ask permission" not in out,
              "the routine-check here predates BQ-148 (no unset_tasks): the routines line stays "
              "silent, never wrong")


def case_w8(w):
    start("W8", "the sync verdict rides the receipts line; no repo without a carrier")
    if not (w["hub"] / "tools" / "sync-verdict.py").is_file():
        check(False, "tools/sync-verdict.py is not beside this gate — W8 cannot run (BQ-210 not "
                     "installed here); named, never passed")
        return
    hub = w["hub"]
    stamp = iso(NOW - 60)
    heads = {"machine": "north", "published": stamp, "projects": {
        "alpha": {"branch": "main", "head": "a" * 40, "tracked_dirty": 0},
        "bravo": {"branch": "main", "head": "b" * 40, "tracked_dirty": 0}}}
    write_json(hub / "heads-north.json", heads)
    write_json(hub / "heads-south.json", dict(heads, machine="south"))
    write_json(hub / "live-sessions-south.json",
               {"machine": "south", "when": iso(NOW - 180), "live_minutes": 10, "sessions": []})
    write(hub / "pulse-last-pull-north.log", "pulse pull north · %s\nexocortex-sync pull\n"
          "  pulled 0 file(s) into the live folders.\n" % iso(NOW - 60))
    write_json(hub / "carry" / "projects.json",
               {"github_owner": "Wren", "bravo": {"carrier": "github", "confirmed": True}})
    write(w["projects"] / "zulu-notes" / "STATUS.md", "# zulu\n\n## Now\nloose notes\n")
    code, out, _t = screen(w)
    first = out.splitlines()[0] if out.splitlines() else ""
    check(code == 0 and " \u00B7 behind \u00B7 " not in first and
          first.endswith(" \u00B7 no carrier: alpha, zulu-notes") and
          " \u00B7 synced \u00B7 brain level \u00B7 2 repos level" in first,
          "the receipts line's tail is the verdict, with the carrier names: %r" % first[-110:])
    check("1 repo with no carrier: alpha \u2014 say the word for each" in out
          and "1 folder with no repo \u2014 for each, say init \u00B7 stays-here \u00B7 ignore: "
              "zulu-notes" in out,
          "under the hygiene line: the repo with no carrier, and the folder with no repo as the "
          "question with its three words")
    write_json(hub / "carry" / "projects.json",
               {"github_owner": "Wren", "bravo": {"carrier": "github", "confirmed": True},
                "alpha": {"carrier": "drive", "confirmed": True},
                "zulu-notes": {"folder": "ignore"}})
    code, out, _t = screen(w)
    first = out.splitlines()[0] if out.splitlines() else ""
    check("with no carrier" not in out and "with no repo" not in out,
          "both words said: the carrier line is silent")
    check(re.search(r" \u00B7 synced \u00B7 brain level \u00B7 2 repos level \u00B7 read \d\d:\d\d$", first),
          "and the tail says synced: %r" % first[-70:])
    for name in ("heads-north.json", "heads-south.json", "live-sessions-south.json",
                 "pulse-last-pull-north.log"):
        (hub / name).unlink()


def engine_beside():
    """The engine's carrier_preflight.py a scratch install lays beside the hub, else the one
    beside this gate, else the machine's own — read, never written."""
    for cand in (HERE.parent.parent / "orchestrator-sync", HERE, Path.home() / "orchestrator-sync"):
        if (cand / "carrier_preflight.py").is_file():
            return cand / "carrier_preflight.py"
    return None


def case_w14(w):
    start("W14", "BQ-334/339 — the wake screen's sync line is the verdict's line; the unreadable note is the next line")
    if not (w["hub"] / "tools" / "sync-verdict.py").is_file():
        check(False, "tools/sync-verdict.py is not beside this gate — G11 cannot run; named, never "
                     "passed")
        return
    source = engine_beside()
    if source is None:
        check(False, "no carrier_preflight.py beside the hub or this gate — G11 cannot run; named, "
                     "never passed")
        return
    hub = w["hub"]
    engine = w["home"] / "orchestrator-sync"
    engine.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(engine / "carrier_preflight.py"))
    stamp = iso(NOW - 60)
    heads = {"machine": "north", "published": stamp, "projects": {
        "alpha": {"branch": "main", "head": "a" * 40, "tracked_dirty": 0},
        "bravo": {"branch": "main", "head": "b" * 40, "tracked_dirty": 0}}}
    made = [hub / "heads-north.json", hub / "heads-south.json", hub / "live-sessions-south.json",
            hub / "pulse-last-pull-north.log", hub / "STATUS.md"]
    had_status = (hub / "STATUS.md").is_file()
    old_status = (hub / "STATUS.md").read_bytes() if had_status else b""
    registry = hub / "carry" / "projects.json"
    old_registry = registry.read_bytes() if registry.is_file() else None
    try:
        write_json(hub / "heads-north.json", heads)
        write_json(hub / "heads-south.json", dict(heads, machine="south"))
        write_json(hub / "live-sessions-south.json",
                   {"machine": "south", "when": iso(NOW - 180), "live_minutes": 10, "sessions": []})
        write(hub / "pulse-last-pull-north.log", "pulse pull north · %s\nexocortex-sync pull\n"
              "  pulled 0 file(s) into the live folders.\n" % iso(NOW - 60))
        body = json.loads(old_registry.decode("utf-8")) if old_registry else {"github_owner": "Wren"}
        body.update({"alpha": {"carrier": "drive", "confirmed": True},
                     "bravo": {"carrier": "github", "confirmed": True},
                     "zulu-notes": {"folder": "ignore"}})
        write_json(registry, body)
        write(hub / "STATUS.md", "# STATUS\n\n## Now\nthe gate's hub\n\n## To do\n"
              "- [ ] DRIVE LEDGER - GW-TX-001 OWED TO THE SOUTH (alpha, North -> South, sealed)\n"
              "- [ ] ! DRIVE LEDGER - EVENING CUT OWED TO THE SOUTH (alpha): commits after "
              "GW-TX-001 are NOT on the drive\n")
        code, out, _t = run([PY, str(hub / "tools" / "sync-verdict.py"), "--json"], w["env"],
                            cwd=hub)
        try:
            facts = json.loads(out.decode("utf-8", "replace"))
        except ValueError:
            facts = {}
        line = str(facts.get("line") or "")
        line2 = str(facts.get("line2") or "")
        # the folders earlier cases left in this world ride after it as the carrier names
        check(code == 0 and (line == "owed: GW-TX-001 on the drive to the SOUTH" or
                             line.startswith("owed: GW-TX-001 on the drive to the SOUTH · no carrier: "))
              and "unreadable" not in line,
              "G11 the verdict, asked in the world, ends with the owed part and no clause: %r" % line)
        check(line2 == "1 ledger line unreadable \u00b7 STATUS.md:8",
              "G11 and its second line names the note: %r" % line2)
        code, out, _t = screen(w)
        lines = out.splitlines()
        first = lines[0] if lines else ""
        check(code == 0 and bool(line) and first.endswith(" \u00B7 " + line)
              and first[-len(line):].encode("utf-8") == line.encode("utf-8")
              and "unreadable" not in first,
              "G11 the receipts line's tail equals the verdict's line byte for byte, no clause: %r"
              % first[-120:])
        check(len(lines) > 1 and lines[1].encode("utf-8") == line2.encode("utf-8"),
              "G11 the NEXT line of the screen equals the verdict's line2 byte for byte: %r"
              % (lines[1] if len(lines) > 1 else None))
        check(" EVENING CUT" not in first, "G11 and never a payload named by the note's words")
        # the strip carries it too (--html is what --inject writes into tree.html)
        code, strip, _t = run([PY, str(hub / "tools" / "wake-screen.py"), "--html"], w["env"], cwd=hub)
        check(line2.encode("utf-8") in strip.replace(b"&middot;", "\u00b7".encode("utf-8")),
              "G11 and the front-door strip (--html, what --inject writes) carries the second line")
    finally:
        for path in made:
            if path.is_file():
                path.unlink()
        if had_status:
            (hub / "STATUS.md").write_bytes(old_status)
        if old_registry is None:
            if registry.is_file():
                registry.unlink()
        else:
            registry.write_bytes(old_registry)
        shutil.rmtree(str(engine), ignore_errors=True)


def night_line(w, extra=None):
    code, out, _t = run([PY, str(w["hub"] / "tools" / "night-check.py"), "--line"], w["env"],
                        cwd=w["hub"], extra=extra)
    return out.decode("utf-8", "replace").strip()


def case_w9(w):
    start("W9", "the night line under the hygiene lines, always; the usage words on the receipts")
    if not (w["hub"] / "tools" / "night-check.py").is_file():
        check(False, "tools/night-check.py is not beside this gate — W9 cannot run (BQ-217 not "
                     "installed here); named, never passed")
        return
    norm = lambda t: re.sub(r"read \d\d:\d\d", "read HH:MM", t)
    code, out, _t = screen(w)
    want = night_line(w)
    lines = out.splitlines()
    check(code == 0 and want and (want.startswith("nothing can wake a Fable window tonight")
                                  or want.startswith("CAN WAKE FABLE: ")),
          "the tool's own last line in this world: %s" % want)
    check(len(lines) >= 6 and norm(lines[-6]) == norm(want) and lines[-5] == "",
          "it is the last line above the plate: %r" % (lines[-6] if len(lines) >= 6 else lines))
    check("3 sessions to archive" in out and out.index("3 sessions to archive") < out.index(lines[-6]),
          "…under the hygiene lines")
    set_queue(w, 0)
    set_routines(w, unset=())
    code, out, _t = screen(w)
    lines = out.splitlines()
    check("to archive" not in out and len(lines) >= 6 and norm(lines[-6]) == norm(night_line(w)),
          "the hygiene lines at zero: the night line is still said: %r" % (lines[-6] if len(lines) >= 6 else ""))
    set_queue(w, 3)
    set_routines(w, unset=("Gate watcher one", "Gate watcher two"))
    table = w["base"] / "ps-waiter.txt"
    write(table, "  4123 58:00 /usr/bin/python3 /x/tools/mail.py --wait NORTH/hub --title ACT \u2014 "
                 "Nobody/hub: a window nobody can name\n")
    extra = {"EXO_NIGHT_PS": str(table)}
    code, out, _t = screen(w, extra=extra)
    want = night_line(w, extra)
    lines = out.splitlines()
    check(want.startswith("CAN WAKE FABLE: the waiter pid 4123") and len(lines) >= 6
          and norm(lines[-6]) == norm(want),
          "a waiter the check cannot clear: the screen says CAN WAKE FABLE and names it: %r"
          % (lines[-6] if len(lines) >= 6 else ""))
    code, html_out, _t = screen(w, "--html", extra=extra)
    check("CAN WAKE FABLE: the waiter pid 4123" in html_out and "tools/night-check.py" in html_out
          and "cannot see: in-window timers" in html_out,
          "the strip carries it, the whole list on hover")
    code, out, _t = screen(w)
    first = out.splitlines()[0] if out.splitlines() else ""
    check(" \u00B7 USAGE \u00B7 " in first and "refresh" in first,
          "(BQ-216) the receipts carry usage.py's words — no meter here, so `refresh`: %r" % first[-150:])


KILO_STATUS = ("# kilo\n\n## Now\nkilo stands where the gate put it. Second sentence.\n\n"
               "## To do\n- [ ] ! project-wide: the kilo bench is out of power\n%s"
               "- [ ] the kilo next step\n")
KILO_ONE = "- [ ] ! KILO/ONE - the first lane's own valve\n"
KILO_TWO = "- [ ] ! KILO/TWO - the second lane's own valve\n"


def set_kilo(w, lines):
    """kilo's shared STATUS, committed (a dirty tree would turn both dots red) and
    kept old, so no case's ranking moves."""
    repo = w["projects"] / "kilo"
    write(repo / "STATUS.md", KILO_STATUS % lines)
    git(repo, "add", "STATUS.md")
    git(repo, "commit", "-q", "-m", "the shared STATUS")
    set_mtime(repo / "STATUS.md", NOW - 60)


def lane_line(block, lane):
    got = [l for l in block if lane_of_line(l) == lane]
    return got[0] if got else ""


def lane_state(data, lane):
    try:
        rows = json.loads(data).get("rows") or []
    except ValueError:
        return "?"
    got = [r for r in rows if r.get("lane") == lane]
    return got[0].get("state") if got else "?"


def case_w10(w):
    start("W10", "a STATUS two lanes share: each lane's own `!`, the bare one on neither")
    set_kilo(w, KILO_TWO + KILO_ONE)
    _c, out, _t = screen(w, "--limit", "12")
    block = lw_block(out)
    one, two = lane_line(block, "Kilo/One"), lane_line(block, "Kilo/Two")
    check("! KILO/ONE - the first lane's own valve" in one and "KILO/TWO" not in one,
          "Kilo/One shows its own `!`: %r" % one[:140])
    check("! KILO/TWO - the second lane's own valve" in two and "KILO/ONE" not in two,
          "Kilo/Two shows its own `!`: %r" % two[:140])
    check(one and two and "project-wide" not in one + two,
          "the bare `!` names no lane: it is the project's, on neither lane's line")
    check(one.startswith("\U0001F7E1 Kilo/One") and two.startswith("\U0001F7E1 Kilo/Two"),
          "each lane's dot is amber for its own `!`")
    set_kilo(w, KILO_ONE)                     # the bare one and Kilo/One's, nothing of Two's
    _c, out, _t = screen(w, "--limit", "12")
    block = lw_block(out)
    one, two = lane_line(block, "Kilo/One"), lane_line(block, "Kilo/Two")
    check(one.startswith("\U0001F7E1 Kilo/One") and "! KILO/ONE" in one,
          "Kilo/One: amber, its own issue: %r" % one[:90])
    check(two.startswith("\U0001F7E2 Kilo/Two") and " ! " not in two,
          "Kilo/Two: green and no issue — the project's `!` and Kilo/One's are not its own: %r"
          % two[:90])
    _c, data, _t = screen(w, "--json", "--limit", "12")
    check(lane_state(data, "Kilo/One") == "amber" and lane_state(data, "Kilo/Two") == "green",
          "--json carries the same per-lane state (%s, %s)"
          % (lane_state(data, "Kilo/One"), lane_state(data, "Kilo/Two")))
    _c, out, _t = screen(w)
    first = [l for l in lw_block(out) if " Alpha " in l]
    check(bool(first) and "! fix the alpha valve" in first[0] and first[0].startswith("\U0001F7E1"),
          "a one-opener folder is unchanged: Alpha still wears its project's `!` and amber")
    probe = ("import importlib.util, json, sys\n"
             "spec = importlib.util.spec_from_file_location('oc', sys.argv[1])\n"
             "m = importlib.util.module_from_spec(spec); sys.path.insert(0, sys.argv[2])\n"
             "spec.loader.exec_module(m)\n"
             "todos = [{'text': 'ROGUEONE - the Door verdict is recorded', 'urgent': True},\n"
             "         {'text': 'DOOR-B2 - fix the door hinge', 'urgent': False}]\n"
             "print(json.dumps([m.lane_next_move('', 'Door', todos, 'the project move'),\n"
             "                  m.lane_next_move('', 'Door', todos[:1], 'the project move')]))\n")
    code, got, _t = run([PY, "-c", probe, str(w["hub"] / "tools" / "opener_carriers.py"),
                         str(w["hub"] / "tools")], w["env"], cwd=w["hub"])
    try:
        moves = json.loads(got.decode("utf-8", "replace").strip().splitlines()[-1])
    except (ValueError, IndexError):
        moves = []
    check(moves == [["DOOR-B2 - fix the door hinge", "lane-status"],
                    ["the project move (project)", "project"]],
          "lane_next_move step 2: the to-do that STARTS with the lane's name, never one that "
          "only mentions it: %r" % (moves,))
    repo = w["projects"] / "kilo"             # back to the world's own STATUS
    write(repo / "STATUS.md", "# kilo\n\n## Now\nkilo stands where the gate put it. Second "
          "sentence.\n\n## To do\n- [ ] ! fix the kilo valve before anything else\n"
          "- [ ] the kilo next step\n")
    git(repo, "add", "STATUS.md")
    git(repo, "commit", "-q", "-m", "back")
    set_mtime(repo / "STATUS.md", NOW - 60)


ACCT_THIS = "1111aaaa-0000-4000-8000-000000000001"     # invented: two logins of one app
ACCT_OTHER = "2222bbbb-0000-4000-8000-000000000002"


def case_w11(w):
    start("W11", "the archive count is this login's, and live")
    sessions = w["store"].parent.parent
    this, other = sessions / ACCT_THIS / "org-a", sessions / ACCT_OTHER / "org-b"
    rows = [("local_w11a", this, False, None),       # this login's, live
            ("local_w11b", this, False, ACCT_THIS),  # this login's, live, the field says so
            ("local_w11c", this, True, None),        # this login's, ALREADY archived
            ("local_w11d", other, False, None),      # the other login's, live
            ("local_w11e", None, False, ACCT_THIS),  # gone from the store
            ("local_w11f", this, False, ACCT_OTHER), # the field names the other login: read it
            ("local_w11g", other, False, None)]      # the other login's, live
    items = []
    for lid, folder, archived, acct in rows:
        if folder is not None:
            store_window(folder, lid, "ARCH — Gate/%s: closed" % lid, archived)
        item = {"sessionId": lid, "title": "ARCH — Gate/%s: closed" % lid,
                "receipt": "2 h quiet · proof: a gate receipt"}
        if acct:
            item["account"] = acct[:8]
        items.append(item)
    write_json(w["hub"] / "hygiene-archive-queue-north.json",
               {"written": iso(NOW), "vendor": "claude", "items": items})
    config = w["home"] / "Library" / "Application Support" / "Claude" / "config.json"
    write_json(config, {"lastKnownAccountUuid": ACCT_THIS})
    _c, out, _t = screen(w)
    check("2 sessions to archive — say archive" in out,
          "the app signed in as THIS login: its two live ones (not the archived one, not the gone "
          "one, not the one whose field names the other login, not the other login's)")
    _c, data, _t = screen(w, "--json")
    try:
        d = json.loads(data)
    except ValueError:
        d = {}
    check(d.get("archive") == 2 and d.get("archive_account") == ACCT_THIS[:8],
          "--json: archive 2 by account %s (%r, %r)" % (ACCT_THIS[:8], d.get("archive"),
                                                       d.get("archive_account")))
    _c, out, _t = screen(w, extra={"CLAUDE_CODE_ACCOUNT_UUID": ACCT_OTHER})
    check("3 sessions to archive — say archive" in out,
          "a window signed in as the OTHER login (its own variables, first): that login's three, "
          "the field-named one among them")
    config.unlink()
    _c, out, _t = screen(w)
    check("5 sessions to archive — say archive" in out,
          "no login readable here: every live one the store still holds, whoever's (5)")
    write_json(w["hub"] / "hygiene-archive-queue-north.json",
               {"written": iso(NOW), "vendor": "claude",
                "items": [i for i in items if i["sessionId"] in ("local_w11c", "local_w11e")]})
    _c, out, _t = screen(w)
    check("to archive" not in out, "only archived and gone items: the line is silent")
    write_json(w["hub"] / "hygiene-archive-queue-north.json",
               {"written": iso(NOW), "vendor": "codex", "items": [
                   {"sessionId": "019a0000-0000-7000-8000-00000000000%d" % i, "title": "ARCH \u2014 "
                    "Gate/Codex%d: closed" % i, "receipt": "gate receipt"} for i in range(2)]})
    _c, out, _t = screen(w)
    check("2 sessions to archive \u2014 say archive" in out,
          "the Codex twin's queue (vendor codex, thread UUIDs the Claude store never holds) is "
          "counted whole, as before")
    set_queue(w, 3)


def case_w12(w):
    start("W12", "a queue file with a BOM (PowerShell's UTF-8) is read and counted")
    set_queue(w, 3)
    path = w["hub"] / "hygiene-archive-queue-north.json"
    raw = path.read_bytes()
    path.write_bytes(b"\xef\xbb\xbf" + raw)
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            json.load(fh)
        plain_fails = False
    except ValueError:
        plain_fails = True
    check(plain_fails, "the BOM'd file is the case: a plain utf-8 read of it fails")
    _c, out, _t = screen(w)
    check("3 sessions to archive — say archive" in out, "read with utf-8-sig and counted: 3")
    set_queue(w, 3)


def seen_states(w):
    try:
        body = json.load(io.open(str(w["home"] / ".exocortex" / "wake" / "no-repo-seen.json"),
                                 encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dict((k, (v or {}).get("state")) for k, v in (body.get("folders") or {}).items())


def ask_line(out):
    got = [l for l in out.splitlines() if " with no repo" in l]
    return got[0] if got else ""


def case_w13(w):
    start("W13", "the no-repo line is a question, asked once")
    if not (w["hub"] / "tools" / "sync-verdict.py").is_file():
        check(False, "tools/sync-verdict.py is not beside this gate — W13 cannot run; named, "
                     "never passed")
        return
    reg = w["hub"] / "carry" / "projects.json"
    body = json.load(io.open(str(reg), encoding="utf-8")) if reg.is_file() else {}
    body.update({"fold-ignored": {"folder": "ignore"}, "fold-stays": {"folder": "stays"},
                 "fold-init": {"folder": "init"}})
    write_json(reg, body)
    for name in ("fold-ask-a", "fold-ignored", "fold-stays", "fold-init"):
        write(w["projects"] / name / "STATUS.md", "# %s\n\n## Now\nloose notes\n" % name)
    write(w["projects"] / "fold-ask-b" / "OPENER.md", "lane: fold-ask-b\n---\nread it\n")
    words = "init · stays-here · ignore"
    _c, out, _t = screen(w)
    check(ask_line(out) == "2 folders with no repo — for each, say %s: fold-ask-a, fold-ask-b"
          % words, "the question names the three words and every folder: %r" % ask_line(out))
    check("fold-ignored" not in out and "fold-stays" not in out,
          "a folder ruled ignore or stays-here is silent")
    check("1 folder owes a repo (init said): fold-init" in out, "a folder ruled init is owed, still counted")
    check(seen_states(w) == {"fold-ask-a": "new", "fold-ask-b": "new"},
          "the seen file marks both `new`: %r" % (seen_states(w),))
    before = (w["home"] / ".exocortex" / "wake" / "no-repo-seen.json").read_bytes()
    _c, html_out, _t = screen(w, "--html")
    _c, _j, _t = screen(w, "--json")
    check((w["home"] / ".exocortex" / "wake" / "no-repo-seen.json").read_bytes() == before,
          "--html and --json read the seen file and never write it")
    check("tools/buttonup.py registry --set &quot;fold-ask-a&quot; init|stays-here|ignore" in html_out
          and "registry --set &quot;fold-ask-b&quot;" in html_out,
          "the strip's hover carries one command per folder")
    _c, out, _t = screen(w)
    check(ask_line(out) == "2 folders with no repo, ruled none — for each, say %s" % words,
          "named once, then the short form: %r" % ask_line(out))
    check(seen_states(w) == {"fold-ask-a": "noted", "fold-ask-b": "noted"},
          "`new` once, then `noted`: %r" % (seen_states(w),))
    write(w["projects"] / "fold-ask-c" / "STATUS.md", "# c\n\n## Now\nnew notes\n")
    _c, out, _t = screen(w)
    check(ask_line(out) == "3 folders with no repo — for each, say %s: fold-ask-c … and 2 "
                           "more, ruled none" % words,
          "a new folder is named, the others counted: %r" % ask_line(out))
    check(seen_states(w) == {"fold-ask-a": "noted", "fold-ask-b": "noted", "fold-ask-c": "new"},
          "and the seen file marks only it `new`: %r" % (seen_states(w),))
    body["fold-ask-a"] = {"folder": "ignore"}
    write_json(reg, body)
    _c, out, _t = screen(w)
    check("fold-ask-a" not in out and ask_line(out).startswith("2 folders with no repo"),
          "a word recorded: never named again: %r" % ask_line(out))
    check("fold-ask-a" not in (seen_states(w) or {}), "and it leaves the seen file")


def main(argv):
    keep = "--keep" in argv
    print("gate-wake-screen.py \u00B7 %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    w = make_world()
    print("  world: %s" % w["base"])
    try:
        for case in (case_w1, case_w2_w5, case_w3, case_w4, case_w6, case_w7, case_w8, case_w9,
                     case_w10, case_w11, case_w12, case_w13, case_w14):
            try:
                case(w)
            except Exception as exc:
                FAILS.append("%s: the case raised %r" % (CASE[0], exc))
                print("  [FAIL] the case raised %r" % (exc,))
    finally:
        if not keep:
            shutil.rmtree(str(w["base"]), ignore_errors=True)
    total = PASSES[0] + len(FAILS)
    print("\n===== GATES =====")
    print("  %d checks \u00B7 %d passed \u00B7 %d failed" % (total, PASSES[0], len(FAILS)))
    for f in FAILS:
        print("  FAIL  %s" % f)
    if keep:
        print("  world kept: %s" % w["base"])
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
