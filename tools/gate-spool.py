#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-spool.py — the proof of tools/spool.py.

    python3 tools/gate-spool.py [--tool PATH] [--keep] [--verbose]

Builds a whole fixture world in the SYSTEM TEMP FOLDER (never under the hub: a mid-run brain
push would carry it) — a machine record for a posix machine and one for a Windows machine, a
registry whose minds, machines, owner and login are all invented, the user's rubric, the meter
files, git projects with openers, a hub STATUS and landings ledger, a carrier registry, and a
live-sessions file with transcripts — then runs spool.py against it as a subprocess, with
every finder pointed at the fixture (EXO_MACHINE_JSON, EXO_REGISTRY_JSON, COLLECT_OPENERS_ROOT,
COLLECT_OPENERS_VOLUMES, COLLECT_OPENERS_WORK, HOME), and checks what it prints.

THE ASSERTIONS, each named: the ribbon is the first line · every fence has its mark line
directly above it and its tag matches the shell · both doors, one sentence · the title rule ·
the walk (judgment under warn → the flagship; judgment past warn → the step-down, never a
mechanical mind; none → the opener's own mind, never above) · the stale-meter STOP wording ·
each gate outcome · the --start JSON, the starter's ⚠ line and its AFTER list · the five
--dials guards · --all's order · the exit codes · the tool writes nothing (nor its tools, by
sha) · the Universality sweep (the live registry's
names never appear in the source, and a run with the invented registry never prints them).

The tool under test is the spool.py beside this file unless --tool names another. The tools it
imports are the hub's own (found beside it, or in the first `tools/` above it).
Exit: 0 every assertion passed · 1 one failed · 2 the gate could not run.
Stdlib only, Python 3.9-compatible, macOS and Windows.
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
import time
from datetime import datetime, timedelta

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
VERBOSE = False

# ── the invented fleet: nobody's names ─────────────────────────────────────
POSIX_M, WIN_M = "orca", "lynx"
LOGIN = "pat@example.test"
SELF_ID = "gate-self-0001"
FLAG, STEP, MID, LOW, CODEX, GROKISH = "KESTREL", "HERON", "WREN", "FINCH", "HERON", "LOON"
MARKS = ("\U0001f7e9", "\u2b1b", "\U0001f7e7", "\U0001f7e6", "\U0001f7ea")


def tools_dir():
    if os.path.isfile(os.path.join(HERE, "exo_paths.py")):
        return HERE
    named = os.environ.get("EXO_TOOLS_DIR", "").strip()
    if named and os.path.isfile(os.path.join(named, "exo_paths.py")):
        return os.path.abspath(named)
    cur = HERE
    for _ in range(8):
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        if os.path.isfile(os.path.join(parent, "tools", "exo_paths.py")):
            return os.path.join(parent, "tools")
        cur = parent
    return ""


def check(name, ok, detail=""):
    detail = detail if isinstance(detail, str) else repr(detail)
    RESULTS.append((name, bool(ok), detail))
    if VERBOSE or not ok:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok
                           else ""))


def iso(d):
    return d.replace(microsecond=0).isoformat()


def now():
    return datetime.now().astimezone()


def write(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def git(cwd, *args):
    base = ["git", "-c", "user.name=gate", "-c", "user.email=gate@example.test",
            "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]
    p = subprocess.run(base + list(args), cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        raise RuntimeError("git %s failed in %s: %s" % (" ".join(args), cwd, p.stderr.strip()))
    return p.stdout.strip()


# ═════════════════════════════════════════════════════════════════════════════
# the fixture world
# ═════════════════════════════════════════════════════════════════════════════

class World(object):
    pass


def opener(lane, head, open_in, model, judgment=None, depends="nothing", body=None,
           status_updated=None):
    lines = ["lane: %s" % lane, "written: %s" % iso(now()), "by: ACT — %s: s0 (ORCA)" % lane,
             "on: ORCA", "head: %s" % head,
             "status_updated: %s" % (status_updated or iso(now() + timedelta(hours=1))),
             "where: a fixture lane", "next: machine", "depends_on: %s" % depends,
             "open_in: %s" % open_in]
    if judgment is not None:
        lines.append("judgment: %s" % judgment)
    lines.append("model: %s" % model)
    lines.append("---")
    lines.append(body if body is not None else
                 "read the project status/memory first. Pick up %s on the ORCA: open the "
                 "opener in this folder and follow it." % lane)
    return "\n".join(lines) + "\n"


def build_world(root):
    w = World()
    w.root = root
    w.home = os.path.join(root, "home")
    w.hub = os.path.join(root, "hub")
    w.projects = os.path.join(root, "projects")
    w.volumes = os.path.join(root, "volumes")
    w.work = os.path.join(root, "work")
    for d in (w.home, w.hub, w.projects, w.volumes, w.work,
              os.path.join(w.home, ".claude", "projects", "-fixture")):
        os.makedirs(d)
    write_json(os.path.join(w.home, ".claude.json"),
               {"oauthAccount": {"emailAddress": LOGIN,
                                 "accountUuid": "0a1b2c3d-0000-4000-8000-000000000000"}})
    for name, os_word in ((POSIX_M, "Darwin 99.0"), (WIN_M, "Windows 10")):
        write_json(os.path.join(root, "%s.json" % name),
                   {"name": name, "os": os_word,
                    "roots": {"orchestrator": w.hub, "projects": w.projects, "home": w.home,
                              "claude": os.path.join(w.home, ".claude")}})
    write_json(os.path.join(w.hub, "registry.json"), {
        "version": 1, "note": "the gate's invented fleet",
        "owner": {"name": "Pat", "short": "pat", "aliases": []},
        "machines": {POSIX_M: {"label": "Orca", "mark": "o", "os": "macos"},
                     WIN_M: {"label": "Lynx", "mark": "l", "os": "windows"}},
        "minds": [
            {"name": FLAG, "vendor": "Anthropic", "kind": "claude", "cli": "kestrel",
             "app_id": "claude-kestrel-9-1"},
            {"name": MID, "vendor": "Anthropic", "kind": "claude", "cli": "wren",
             "app_id": "claude-wren-9-5"},
            {"name": LOW, "vendor": "Anthropic", "kind": "claude"},
            {"name": STEP, "vendor": "OpenAI", "kind": "codex"},
            {"name": GROKISH, "vendor": "xAI", "kind": "grok"}],
        "mind_aliases": {"GPTX": STEP}})
    write_json(os.path.join(w.hub, "effort-rubric.json"), {
        "version": 1, "about": "the gate's rubric", "user_name": "",
        "dials": {"anthropic": {"low": "LOW", "medium": "MEDIUM", "high": "HIGH",
                                "xhigh": "EXTRA", "max": "MAX"},
                  "openai": {"xhigh": "EXTRA"}},
        "flag_only_levels": ["max"],
        "kinds": [
            {"id": "judgment", "name": "JUDGMENT", "ask": "decide?", "minds": [FLAG, STEP],
             "never": [LOW], "level": "EXTRA", "flag": "plate", "source": "the gate"},
            {"id": "mechanical", "name": "MECHANICAL", "ask": "ruled?", "minds": [MID, LOW],
             "never": [], "level": "HIGH", "flag": "plate", "source": "the gate"}],
        "thresholds": {}, "switches": {}})
    write(os.path.join(w.hub, "STATUS.md"),
          "# Hub\n\n## Now\nZX-TX-001 LANDED OK · HEAD 1a2b3c4\n\n## To do\n- [ ] nothing\n")
    write_json(os.path.join(w.hub, "landings-%s.json" % POSIX_M),
               {"machine": POSIX_M, "landings": {"ZX-TX-002": {
                   "gate": "ZX-TX-002 LANDED OK · HEAD 5e6f7a8"}}})
    write_json(os.path.join(w.hub, "carry", "projects.json"),
               {"delta": {"carrier": "drive", "confirmed": True}})

    # alpha — one folder, many lanes
    a = os.path.join(w.projects, "alpha")
    os.makedirs(os.path.join(a, "docs"))
    git(a, "init", "-q")
    write(os.path.join(a, "STATUS.md"), "# alpha\n\n## Now\nfixture.\n\n## To do\n- [ ] a step\n")
    write(os.path.join(a, "docs", "plan.md"), "the plan\n")
    git(a, "add", "-A")
    git(a, "commit", "-q", "-m", "first")
    w.first_sha = git(a, "rev-parse", "--short=8", "HEAD")
    n = 0
    while not (re.search(r"[0-9]", w.first_sha) and re.search(r"[a-f]", w.first_sha)) and n < 40:
        n += 1                          # a sha the gate's reader takes holds a digit and a letter
        write(os.path.join(a, "pad.txt"), "%d\n" % n)
        git(a, "add", "-A")
        git(a, "commit", "-q", "-m", "pad %d" % n)
        w.first_sha = git(a, "rev-parse", "--short=8", "HEAD")
    write(os.path.join(a, "notes.txt"), "two\n")
    git(a, "add", "-A")
    git(a, "commit", "-q", "-m", "second")
    head = git(a, "rev-parse", "--short=8", "HEAD")
    w.alpha = a

    def oi(title):
        return ("ORCA — %s · project `alpha` (reuse) · fresh Claude session titled `%s`"
                % (a, title))
    w.titles = {
        "Judge": "ACT — Alpha/Judge: s1 — rule the plan",
        "Mech": "ACT — Alpha/Mech: s2 — build the ruled thing",
        "Long": ("ACT — Alpha/Long: s9 — a very long purpose that runs well past the sixty "
                 "character cap; and more"),
        "Wordy": "ACT — Alpha/Wordy: a clause with many words that keeps going and going past it",
    }
    files = {
        "Judge": opener("Alpha/Judge", head, oi(w.titles["Judge"]), "%s · EXTRA" % MID,
                        judgment="rule the plan · grade the draft"),
        "Mech": opener("Alpha/Mech", head, oi(w.titles["Mech"]), "%s · HIGH" % MID,
                       judgment="none — the build is ruled",
                       body="Some words first.\n\nNo paste-ready line here."),
        "Long": opener("Alpha/Long", head, oi(w.titles["Long"]), "%s · MEDIUM" % LOW,
                       judgment="none"),
        "Wordy": opener("Alpha/Wordy", head, oi(w.titles["Wordy"]), "%s · HIGH" % MID,
                        judgment="none"),
        "Codex": opener("Alpha/Codex", head, "%s · fresh Codex session" % a, "GPTX · EXTRA",
                        judgment="none"),
        "Grok": opener("Alpha/Grok", head, "%s · fresh session" % a, "%s · HIGH" % GROKISH,
                       judgment="none"),
        "Gpath": opener("Alpha/Gpath", head, oi("ACT — Alpha/Gpath: s1"), "%s · HIGH" % MID,
                        judgment="none", depends="`docs/plan.md` is written"),
        "Gmiss": opener("Alpha/Gmiss", head, oi("ACT — Alpha/Gmiss: s1"), "%s · HIGH" % MID,
                        judgment="none", depends="`docs/missing.md` is written"),
        "Gsha": opener("Alpha/Gsha", head, oi("ACT — Alpha/Gsha: s1"), "%s · HIGH" % MID,
                       judgment="none", depends="commit %s is in" % w.first_sha),
        "Gbad": opener("Alpha/Gbad", head, oi("ACT — Alpha/Gbad: s1"), "%s · HIGH" % MID,
                       judgment="none", depends="commit deadbe7f is in"),
        "Gland": opener("Alpha/Gland", head, oi("ACT — Alpha/Gland: s1"), "%s · HIGH" % MID,
                        judgment="none", depends="ZX-TX-001 LANDED OK"),
        "Gledger": opener("Alpha/Gledger", head, oi("ACT — Alpha/Gledger: s1"),
                          "%s · HIGH" % MID, judgment="none", depends="ZX-TX-002 LANDED OK"),
        "Gnoland": opener("Alpha/Gnoland", head, oi("ACT — Alpha/Gnoland: s1"),
                          "%s · HIGH" % MID, judgment="none", depends="ZX-TX-009 LANDED OK"),
        "Gprose": opener("Alpha/Gprose", head, oi("ACT — Alpha/Gprose: s1"), "%s · HIGH" % MID,
                         judgment="none", depends="the other lane's word"),
    }
    for suffix, text in files.items():
        write(os.path.join(a, "OPENER-%s.md" % suffix), text)

    # beta — HEAD moved on since the opener: NOTE
    b = os.path.join(w.projects, "beta")
    os.makedirs(b)
    git(b, "init", "-q")
    write(os.path.join(b, "STATUS.md"), "# beta\n\n## Now\nfixture.\n")
    git(b, "add", "-A")
    git(b, "commit", "-q", "-m", "one")
    old = git(b, "rev-parse", "--short=8", "HEAD")
    write(os.path.join(b, "x.txt"), "x\n")
    git(b, "add", "-A")
    git(b, "commit", "-q", "-m", "two")
    write(os.path.join(b, "OPENER.md"),
          opener("Beta/Main", old, "%s · fresh Claude session titled `ACT — Beta/Main: s3`" % b,
                 "%s · HIGH" % MID, judgment="none"))
    # gamma — the opener names a commit this repo never had: STALE
    g = os.path.join(w.projects, "gamma")
    os.makedirs(g)
    git(g, "init", "-q")
    write(os.path.join(g, "STATUS.md"), "# gamma\n\n## Now\nfixture.\n")
    git(g, "add", "-A")
    git(g, "commit", "-q", "-m", "one")
    write(os.path.join(g, "OPENER.md"),
          opener("Gamma/Main", "0f0f0f0", "%s · fresh Claude session" % g, "%s · HIGH" % MID,
                 judgment="none"))
    # delta — a no-remote (drive) project, a judgment lane
    d = os.path.join(w.projects, "delta")
    os.makedirs(d)
    git(d, "init", "-q")
    write(os.path.join(d, "STATUS.md"), "# delta\n\n## Now\nfixture.\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "one")
    dh = git(d, "rev-parse", "--short=8", "HEAD")
    write(os.path.join(d, "OPENER.md"),
          opener("Delta/Main", dh, "%s · fresh Claude session titled `ACT — Delta/Main: s1`" % d,
                 "%s · EXTRA" % MID, judgment="decide the merge order"))
    return w


def meter(w, machine, flag_pct=12, all_pct=30, minutes_ago=5, with_flag=True):
    windows = [{"kind": "week", "label": "Weekly · all models", "model": "", "percent": all_pct,
                "resets_at": None}]
    if with_flag:
        windows.append({"kind": "week-model", "label": "Weekly · Kestrel", "model": "kestrel",
                        "percent": flag_pct, "resets_at": None})
    write_json(os.path.join(w.hub, "usage-%s-claude-pat-at-example.test.json" % machine), {
        "vendor": "claude", "machine": machine, "login": LOGIN, "login_source": "the gate",
        "read_at": iso(now() - timedelta(minutes=minutes_ago)), "source": "the gate",
        "windows": windows, "meter": "readable",
        "accounting": {"last_24h": {"calls_by_model": {"claude-finch-9-0": 40,
                                                       "claude-kestrel-9-1": 10}}}})


def meters(w, **kw):
    meter(w, POSIX_M, **kw)
    meter(w, WIN_M, **kw)


def transcript(w, sid, model, effort, text, mid_turn=False):
    path = os.path.join(w.home, ".claude", "projects", "-fixture", "%s.jsonl" % sid)
    recs = [{"type": "user", "message": {"role": "user", "content": "go"}},
            {"type": "assistant", "uuid": "u-%s" % sid, "effort": effort,
             "message": {"model": model, "content": [{"type": "text", "text": text}]}}]
    write(path, "\n".join(json.dumps(r) for r in recs) + "\n")
    if not mid_turn:
        old = time.time() - 600
        os.utime(path, (old, old))
    return path


def plate(span, mind, level, why):
    arrow = "**\u21e7 NEXT TURN**" if span == "TURN" else "**\u21e9 NEXT STRETCH**"
    return "The work.\n\n---\n%s\n`ORCA · %s · %s` — %s\n\n---\n" % (arrow, mind, level, why)


def live_sessions(w):
    s = []

    def add(sid, title, model, effort, text, kind="claude", mid_turn=False):
        p = transcript(w, sid, model, effort, text, mid_turn)
        s.append({"id": sid, "kind": kind, "model": model, "title": title, "transcript": p,
                  "cwd": w.alpha, "minutes_ago": 1.0})
    add("w-up", "ACT — Alpha/Judge: s1 — rule the plan", "claude-wren-9-5", "xhigh", "Done.")
    add("w-plate-up", "ACT — Alpha/Mech: s2 — build", "claude-wren-9-5", "high",
        plate("TURN", FLAG, "EXTRA", "rule the merge order"))
    add("w-norule", "ACT — Alpha/Long: s9", "claude-wren-9-5", "high",
        plate("TURN", FLAG, "HIGH", "tidy the list"))
    add("w-down", "ACT — Beta/Main: s3", "claude-kestrel-9-1", "xhigh",
        plate("STRETCH", LOW, "HIGH", "the mechanical rest"))
    add("w-mid", "ACT — Delta/Main: s1", "claude-wren-9-5", "high", "Working.", mid_turn=True)
    add(SELF_ID, "ACT — Alpha/Judge: the hub itself", "claude-wren-9-5", "high", "Here.")
    add("w-arch", "ARCH — Alpha/Judge: done", "claude-wren-9-5", "high", "Bye.")
    add("w-codex", "ACT — Alpha/Codex: s1", "codex-x9", "xhigh", "Hi.", kind="codex")
    write_json(os.path.join(w.hub, "live-sessions-%s.json" % POSIX_M),
               {"machine": POSIX_M, "when": iso(now()), "live_minutes": 10, "sessions": s})


# ═════════════════════════════════════════════════════════════════════════════
# running the tool
# ═════════════════════════════════════════════════════════════════════════════

def env_for(w, machine, tdir, self_id=SELF_ID):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("COLLECT_OPENERS_") or key in ("EXO_MACHINE_JSON",
                                                          "EXO_REGISTRY_JSON"):
            env.pop(key)
    env.update({"EXO_MACHINE_JSON": os.path.join(w.root, "%s.json" % machine),
                "EXO_REGISTRY_JSON": os.path.join(w.hub, "registry.json"),
                "COLLECT_OPENERS_ROOT": w.projects, "COLLECT_OPENERS_VOLUMES": w.volumes,
                "COLLECT_OPENERS_WORK": w.work, "EXO_TOOLS_DIR": tdir, "HOME": w.home,
                "USERPROFILE": w.home, "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8", "CLAUDE_CODE_SESSION_ID": self_id,
                "GIT_CONFIG_NOSYSTEM": "1"})
    env.pop("CLAUDE_CONFIG_DIR", None)
    # ASSUMES: the fixture's login is the fixture's own. A gate run from inside a desktop
    # window inherits that window's identity (entrypoint, account, email) — usage.py then
    # refuses the fixture's CLI-only config as a desktop window's login. Opposite: the
    # parent's variables are dropped here, so the world's .claude.json is the only road.
    for key in ("CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_ACCOUNT_UUID", "CLAUDE_CODE_USER_EMAIL"):
        env.pop(key, None)
    return env


ALL_OUT = []


def run(w, tool, tdir, args, machine=POSIX_M, self_id=SELF_ID, extra=None):
    env = env_for(w, machine, tdir, self_id)
    env.update(extra or {})
    p = subprocess.run([sys.executable, tool] + list(args), env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=w.root,
                       universal_newlines=True, encoding="utf-8", errors="replace")
    ALL_OUT.append(p.stdout + p.stderr)
    return p.returncode, p.stdout, p.stderr


def lines_of(out):
    return out.rstrip("\n").split("\n") if out.strip() else []


def fences(lines):
    """[(index of the opening fence, its tag, the body lines)]"""
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            tag = lines[i][3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append((i, tag, lines[i + 1:j]))
            i = j + 1
        else:
            i += 1
    return out


def unquote(text):
    """The sentence inside a launch line's last argument, whichever shell quoted it."""
    m = re.search(r'claude --model \S+ (.*)$', text)
    if not m:
        return None
    arg = m.group(1)
    if arg.startswith('"') and arg.endswith('"'):
        inner = arg[1:-1]
        return inner.replace('`"', '"').replace("`$", "$").replace("``", "`")
    if arg.startswith("'") and arg.endswith("'"):
        return arg[1:-1].replace("'\\''", "'")
    return None


def check_step(name, out, shell, kind="claude"):
    """The shape every step must have."""
    ls = lines_of(out)
    check("%s · the ribbon is the first line" % name, ls and ls[0].startswith("\u258c"),
          ls[0] if ls else "no output")
    fs = fences(ls)
    good = bool(fs)
    tags = []
    for idx, tag, _body in fs:
        above = ls[idx - 1] if idx > 0 else ""
        if not (above[:1] in "".join(MARKS) and "**" in above):
            good = False
        tags.append(tag)
    check("%s · every fence has its mark line directly above it" % name, good,
          " | ".join(ls[i - 1][:40] for i, _t, _b in fs))
    if kind == "claude":
        check("%s · the fence tags match the shell" % name, tags == [shell, "text"], str(tags))
        launch = fs[0][2][0] if fs and fs[0][2] else ""
        chat = fs[1][2][0] if len(fs) > 1 and fs[1][2] else ""
        check("%s · both doors carry one sentence" % name,
              launch and chat and unquote(launch) == chat, "%r vs %r" % (launch[-60:], chat[-60:]))
    else:
        check("%s · the Codex door is one chat fence" % name, tags == ["text"], str(tags))
    return ls


def ribbon_words(ls):
    return ls[0] if ls else ""


# ═════════════════════════════════════════════════════════════════════════════
# the assertions
# ═════════════════════════════════════════════════════════════════════════════

def proofs(w, tool, tdir):
    sentence_judge = ("read the project status/memory first. Pick up Alpha/Judge on the ORCA: "
                      "open the opener in this folder and follow it.")
    # ── the step and the walk, posix machine, under warn ──
    meters(w, flag_pct=12)
    code, out, err = run(w, tool, tdir, ["Alpha/Judge"])
    check("judge · exit 0", code == 0, err.strip()[:200] or out[:200])
    ls = check_step("judge (posix)", out, "zsh")
    check("walk · judgment under warn → the flagship", "· Kestrel · Extra" in ribbon_words(ls)
          and "claude --model kestrel " in out, ribbon_words(ls))
    check("step · the terminal mark is the posix default from the machine's label",
          "\U0001f7e9 **ORCA TERMINAL** · NEW WINDOW · folder %s" % w.alpha in out)
    check("step · the chat-box mark", "\U0001f7e7 **CLAUDE CODE CHAT BOX** · the project alpha"
          in out)
    check("step · the SET line quotes the meter",
          re.search(r"\U0001f9e0 SET: Kestrel · Extra — rule the plan \(meter Kestrel 12% · all 30%"
                    r" · example · (?:\w{3} )?\d\d:\d\d\)", out) is not None,
          [l for l in ls if "SET:" in l][:1])
    check("step · the body's own sentence is the paste", sentence_judge in out)
    check("step · DONE WHEN names the title", '\u2705 DONE WHEN: a window titled "ACT — Alpha/Judge:'
          ' s1 — rule the plan" answers with its WHERE WE ARE.' in out)
    check("step · no gate, no lock", "\U0001f512" not in out and "DO NOT OPEN BEFORE" not in out)

    # ── past warn: the step-down, a Codex door, never a mechanical mind ──
    meters(w, flag_pct=85)
    code, out, err = run(w, tool, tdir, ["Alpha/Judge"])
    ls = check_step("judge past warn", out, "", kind="codex")
    check("walk · judgment past warn → the step-down's door",
          code == 0 and "· Codex · NEW THREAD ·" in ribbon_words(ls) and "· Heron · Extra"
          in ribbon_words(ls), ribbon_words(ls))
    check("walk · past warn never names a mechanical mind",
          all(m.title() not in ls[0] + ls[1] for m in (MID, LOW)), ls[:2])
    check("walk · past warn says why", "at or past warn 80%" in out)
    meters(w, flag_pct=12, with_flag=False)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge"])
    check("walk · no flagship week on the meter → the step-down, said",
          "· Heron · Extra" in out and "the meter carries no Kestrel week" in out, out[:300])

    # ── judgment none: the opener's own mind, never above ──
    for pct in (12, 85):
        meters(w, flag_pct=pct)
        code, out, _e = run(w, tool, tdir, ["Alpha/Mech"])
        ls = lines_of(out)
        check("walk · none → the opener's mind (flagship %d%%)" % pct,
              code == 0 and ls and "· Wren · High" in ls[0] and "Kestrel" not in ls[0],
              ls[0] if ls else out)
    check("step · no paste-ready line → the launch sentence",
          "read the project status/memory first. Pick up Alpha/Mech on the ORCA: open "
          "OPENER-Mech.md in this folder and follow it." in out, out[-400:])

    posix_out = out
    # ── the Windows machine ──
    meters(w, flag_pct=12)
    code, out, err = run(w, tool, tdir, ["Alpha/Mech"], machine=WIN_M)
    ls = check_step("mech (windows)", out, "powershell")
    check("windows · the mark and the PowerShell launch line",
          "\u2b1b **LYNX POWERSHELL** · NEW WINDOW" in out and re.search(
              r'^cd "[^"]+alpha"; claude --model wren "read the project', out, re.M) is not None,
          out[:500])
    # ASSUMES: the gate's world is spelled in the HOST's own path form, so it is foreign to the
    # fixture machine of the other os — LYNX (Windows) on a posix host, ORCA (posix) on a Windows
    # host, where spool reads a drive-letter path as LYNX's own folder and rightly says no note.
    # The translation is proven on whichever run is foreign here; the false case for the posix
    # reading is a Windows run of this check.
    foreign_out = posix_out if os.name == "nt" else out
    check("windows · another machine's path is translated and said",
          "this machine's %s" % w.alpha in foreign_out)

    # ── the title rule ──
    code, out, _e = run(w, tool, tdir, ["Alpha/Long"])
    m = re.search(r'a window titled "([^"]+)"', out)
    t = m.group(1) if m else ""
    check("title · over 60 → ACT head + first clause + machine",
          t == "ACT — Alpha/Long: s9 (ORCA)" and len(t) <= 60, t)
    check("title · the full title beside it",
          'full title: "%s"' % w.titles["Long"] in out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Wordy"])
    m = re.search(r'a window titled "([^"]+)"', out)
    t = m.group(1) if m else ""
    check("title · a long first clause is cut at a whole word",
          t.startswith("ACT — Alpha/Wordy: a clause with") and t.endswith(" (ORCA)")
          and len(t) <= 60, "%r (%d)" % (t, len(t)))
    # ── the registry silent on a mind's doors ──
    code, out, _e = run(w, tool, tdir, ["Alpha/Long"])
    check("registry silent · said in one line, the record's own id",
          "the registry names no CLI word or app id for FINCH — the record's own: `finch` · "
          "claude-finch-9-0" in out and "claude --model finch " in out, out[-300:])
    # ── the Codex door for an aliased mind ──
    code, out, _e = run(w, tool, tdir, ["Alpha/Codex"])
    check_step("codex lane", out, "", kind="codex")
    check("codex · an alias resolves to the registry's mind", "· Heron · Extra" in out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Grok"])
    check("grok · a mind with no door is a STOP", code == 1 and out.startswith("STOP — "))

    # ── the gate outcomes ──
    code, out, _e = run(w, tool, tdir, ["Alpha/Gpath"])
    check("gate · a path present → OK, locked, the line in caps",
          code == 0 and out.startswith("\u258c \U0001f512 ") and "GATE OK — docs/plan.md exists"
          in out and "DO NOT OPEN BEFORE: `DOCS/PLAN.MD` IS WRITTEN" in out, out[:200])
    dn = lines_of(out)
    at = [i for i, l in enumerate(dn) if l.startswith("DO NOT OPEN BEFORE")]
    check("gate · the gate line sits on the line above DONE WHEN",
          at and dn[at[0] + 1].startswith("\u2705 DONE WHEN"))
    code, out, _e = run(w, tool, tdir, ["Alpha/Gmiss"])
    check("gate · a path absent → STOP", code == 1 and out.startswith("STOP — GATE STOP")
          and "docs/missing.md" in out and len(lines_of(out)) == 1, out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Gsha"])
    check("gate · a sha in history → OK", code == 0 and "GATE OK — %s is in alpha's history"
          % w.first_sha in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Gbad"])
    check("gate · a sha not in history → STOP", code == 1 and "deadbe7f" in out
          and out.startswith("STOP — GATE STOP"), out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Gland"])
    check("gate · a LANDED line in the hub STATUS → OK", code == 0 and
          "GATE OK — ZX-TX-001 LANDED OK" in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Gledger"])
    check("gate · a LANDED line in the landings ledger → OK", code == 0 and
          "GATE OK — ZX-TX-002 LANDED OK" in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Gnoland"])
    check("gate · a LANDED line nowhere → STOP", code == 1 and "ZX-TX-009" in out, out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Gprose"])
    check("gate · anything else → UNVERIFIED, the step still prints, locked",
          code == 0 and out.startswith("\u258c \U0001f512 ") and
          "GATE UNVERIFIED — the hub checks it by hand: the other lane's word" in out, out[:200])

    # ── freshness, exactly the collector's ──
    code, out, _e = run(w, tool, tdir, ["Beta/Main"])
    check("opener · NOTE is handed with its note", code == 0 and "· NOTE — HEAD moved 1 commit"
          in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Gamma/Main"])
    check("opener · STALE is a one-line STOP with the fallback",
          code == 1 and len(lines_of(out)) == 1 and out.startswith("STOP — STALE — Gamma/Main")
          and "read the project status/memory first." in out, out)

    # ── the stale meter ──
    meters(w, flag_pct=12, minutes_ago=45)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge"])
    check("meter · stale → the one STOP sentence",
          code == 1 and re.match(r"^STOP — meter read 4\d min ago — refresh: get_usage, then "
                                 r"python3 tools/usage\.py --write\n$", out) is not None, out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge"], machine=WIN_M)
    check("meter · stale on Windows names python and the backslash",
          code == 1 and "then python tools\\usage.py --write" in out, out)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge", "--max-age", "60"])
    check("meter · --max-age widens the window", code == 0, out[:120])
    meters(w, flag_pct=12)

    # ── --ask (the question before a hand or a start) ──
    code, out, err = run(w, tool, tdir, ["Delta/Main", "--ask"])
    ls = lines_of(out)
    check("ask · exit 0", code == 0, err[:200] or out[:200])
    check("ask · the first line names the lane and asks which way",
          ls and ls[0] == "SPOOL — Delta/Main · which way?", ls[0] if ls else "")
    check("ask · choice 1 is the started window, marked as the pick",
          len(ls) > 1 and ls[1].startswith("1 · START MODE — a window started for you") and "← the pick" in ls[1])
    check("ask · choice 2 is the prompt to paste",
          len(ls) > 2 and ls[2].startswith("2 · MANUAL MODE — the prompt to paste"))
    check("ask · one why line, then «Say 1 or 2.» last",
          len(ls) == 5 and ls[3].startswith("why: ") and "start mode" in ls[3]
          and "manual mode" in ls[3] and ls[4] == "Say 1 or 2.", str(ls))
    check("ask · no ribbon, no launch line, no JSON — a question only",
          not any(l.startswith(("\u258c", "```", "{")) for l in ls))
    code, out, _e = run(w, tool, tdir, ["Delta/Main", "--ask", "--json"])
    try:
        aobj = json.loads(out.strip())
    except ValueError:
        aobj = {}
    check("ask · --json carries the lanes and the two choices",
          aobj.get("lanes") == ["Delta/Main"] and aobj.get("choices") == {"1": "start", "2": "hand"},
          out[:200])
    check("ask · --json names the two modes (START MODE, MANUAL MODE)",
          aobj.get("names") == {"1": "START MODE", "2": "MANUAL MODE"}, out[:200])
    code, out, _e = run(w, tool, tdir, ["Delta/Main", "--ask", "--start"])
    check("ask · --ask with --start is a defect (exit 2)", code == 2, out[:120])
    code, out, _e = run(w, tool, tdir, ["Nobody/Here", "--ask"])
    check("ask · an unknown lane is a STOP here, not later", code == 1 and out.startswith("STOP — "),
          out[:120])

    # ── --start ──
    live_sessions(w)                    # the hub (SELF_ID) answers on WREN · high
    code, out, err = run(w, tool, tdir, ["Delta/Main", "--start"])
    ls = lines_of(out)
    check("start · exit 0", code == 0, err[:200] or out[:200])
    check("start · the reminder is the first line", ls and ls[0].startswith(
        "START — only on the user's explicit word"))
    # G1 BELOW: the hub on WREN · HIGH starts a KESTREL · EXTRA walk
    second = ls[1] if len(ls) > 1 else ""
    check("start · G1 the ⚠ line is the second line, the hub's dial below the walk",
          second.startswith("\u26a0 starting on %s · HIGH" % MID)
          and "Delta/Main is set to %s · EXTRA at once (AFTER 2)" % FLAG in second
          and second.endswith("runs on %s" % MID), second)
    check("start · G1 one ⚠ line only", sum(1 for l in ls if l.startswith("\u26a0")) == 1,
          str([l for l in ls if l.startswith("\u26a0")]))
    code, jout, _e = run(w, tool, tdir, ["Delta/Main", "--start", "--json"])
    try:
        st = json.loads(jout)[0].get("starter") or {}
    except (ValueError, IndexError, AttributeError):
        st = {}
    check("start · G1 --json starter: read, the hub's mind, below the walk",
          st.get("read") is True and st.get("mind") == MID and st.get("level") == "HIGH"
          and st.get("model") == "claude-wren-9-5" and st.get("effort") == "high"
          and st.get("below_walk") is True, st)
    obj = None
    for l in ls:
        if l.startswith("{"):
            try:
                obj = json.loads(l)
            except ValueError:
                obj = None
    check("start · one JSON object with exactly the seven fields", obj is not None and
          set(obj) == {"title", "cwd", "model", "effort", "prompt", "background", "name"},
          str(sorted(obj)) if obj else "no JSON line")
    if obj:
        bg = obj["background"]
        check("start · model is the registry's app id, effort the dial's value",
              obj["model"] == "claude-kestrel-9-1" and obj["effort"] == "xhigh", str(obj)[:200])
        chat = [b for _i, t, b in fences(ls) if t == "text"]
        check("start · the prompt is the step's sentence", chat and obj["prompt"] == chat[0][0])
        check("start · the name is a lane slug", re.match(r"^[a-z0-9-]{1,24}$", obj["name"])
              is not None and obj["name"] == "delta-main", obj["name"])
        check("start · cwd is the folder", obj["cwd"] == os.path.join(w.projects, "delta"))
        for label, needle in (("gate", "Gate: nothing."), ("meter", "Meter: Kestrel 12%"),
                              ("login", LOGIN), ("stamp", "i-am.py\" KESTREL EXTRA"
                                                 if " " in w.hub else "i-am.py KESTREL EXTRA"),
                              ("claim", "--claim Delta/Main"),
                              ("mail, both machines", "ORCA/Main and LYNX/Main"),
                              ("the hub-switch clause", "message the hub for the switch rather "
                                                        "than judging on a cheaper mind"),
                              ("no-remote", "named-path git only, never push")):
            check("start · background carries the %s" % label, needle in bg, bg[:300])
    after = [l for l in ls if l.startswith("AFTER ")]
    check("start · the AFTER list, in order", after == [
        "AFTER 1 · detach_session <each new id> — at once, in the message right after the starts",
        "AFTER 2 · the dial, never asked: get_session <each new id>; where model or effort is "
        "not the walk's, set_session_model / set_session_effort to the walk's values (a "
        "cancelled card is retried once, right away)",
        "AFTER 3 · set_view group_by=project (once per sitting)",
        "AFTER 4 · record: one line in the hub STATUS ## Now naming the window, its dial and "
        "the reason",
        "AFTER 5 · say which windows opened, in one line, each under its project"], str(after))
    # G2 NOT BELOW: the hub on the walk's own dial — no ⚠ line
    hub_t = [s_ for s_ in json.loads(io.open(os.path.join(w.hub, "live-sessions-%s.json"
                                                          % POSIX_M), encoding="utf-8").read())
             ["sessions"] if s_["id"] == SELF_ID][0]["transcript"]
    before_t = sha_of(hub_t)
    transcript(w, SELF_ID, "claude-kestrel-9-1", "xhigh", "Here.")
    code, out2, _e = run(w, tool, tdir, ["Delta/Main", "--start"])
    code_j, jout, _e = run(w, tool, tdir, ["Delta/Main", "--start", "--json"])
    transcript(w, SELF_ID, "claude-wren-9-5", "high", "Here.")
    try:
        st = json.loads(jout)[0].get("starter") or {}
    except (ValueError, IndexError, AttributeError):
        st = {}
    check("start · G2 the hub at the walk's dial → no ⚠ line, the start still prints",
          code == 0 and not any(l.startswith("\u26a0") for l in lines_of(out2))
          and any(l.startswith("{") for l in lines_of(out2)), out2[:300])
    check("start · G2 --json starter: read, not below the walk",
          code_j == 0 and st.get("read") is True and st.get("mind") == FLAG
          and st.get("below_walk") is False, st)
    check("start · G2 the hub's transcript is put back", sha_of(hub_t) == before_t)
    # G3 UNREAD: a session id the live-sessions file does not hold
    code, out3, err3 = run(w, tool, tdir, ["Delta/Main", "--start"], self_id="gate-nobody-0009")
    l3 = lines_of(out3)
    warn3 = [l for l in l3 if l.startswith("\u26a0")]
    check("start · G3 an unread hub dial → exit 0, one ⚠ line naming why, the start prints",
          code == 0 and len(warn3) == 1 and l3[1:2] == warn3 and "unread" in warn3[0]
          and ("no session id" in warn3[0] or "not in the live-sessions file" in warn3[0])
          and any(l.startswith("{") for l in l3), (err3 or out3)[:300])
    code, jout, _e = run(w, tool, tdir, ["Delta/Main", "--start", "--json"],
                         self_id="gate-nobody-0009")
    try:
        st = json.loads(jout)[0].get("starter") or {}
    except (ValueError, IndexError, AttributeError):
        st = {}
    check("start · G3 --json starter: unread, no mind, not below",
          st.get("read") is False and st.get("mind") == "" and st.get("level") == ""
          and st.get("below_walk") is False, st)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge", "--start"])
    obj = [json.loads(l) for l in lines_of(out) if l.startswith("{")]
    check("start · siblings in the folder are named",
          obj and "Sibling lanes sharing this folder: Alpha/Codex" in obj[0]["background"])
    meters(w, flag_pct=85)
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge", "--start"])
    check("start · a Codex walk is a STOP (the app starts Claude windows only)",
          code == 1 and "STOP — the walk names HERON" in out and "{" not in out, out[:300])
    meters(w, flag_pct=12)

    # ── an opener the capture headed opens the NEXT sitting ──
    captured_proofs(w, tool, tdir)

    # ── --json ──
    code, out, _e = run(w, tool, tdir, ["Alpha/Judge", "--json"])
    try:
        got = json.loads(out)
    except ValueError:
        got = None
    check("json · one object per lane", isinstance(got, list) and len(got) == 1 and
          got[0]["mind"] == FLAG and got[0]["door"] == "claude" and got[0]["effort"] == "xhigh",
          out[:200])

    # ── --all: ranked, ungated first, gated last, one rule between blocks ──
    code, out, _e = run(w, tool, tdir, ["--all"])
    ls = lines_of(out)
    ribbons = [l for l in ls if l.startswith("\u258c")]
    locks = [("\U0001f512" in r) for r in ribbons]
    check("all · ungated first, gated last", ribbons and locks == sorted(locks) and any(locks)
          and not all(locks), str(locks))
    blocks = 1 + sum(1 for l in ls if l == "---")
    starts = sum(1 for l in ls if l.startswith("\u258c") or l.startswith("STOP — "))
    check("all · one block per active lane, a rule between", blocks == starts and blocks == 17,
          "%d rules+1 · %d blocks" % (blocks, starts))
    check("all · a STOP anywhere → exit 1", code == 1)

    # ── --dials: the five guards ──
    live_sessions(w)
    code, out, err = run(w, tool, tdir, ["--dials"])
    ls = lines_of(out)

    def line_for(title_start):
        hits = [l for l in ls if l.split('"')[1:2] and l.split('"')[1].startswith(title_start)]
        return hits[0] if hits else ""
    check("dials · exit 0, one line per window", code == 0 and len(ls) == 8,
          (err or out)[:300])
    l = line_for("ACT — Alpha/Judge: s1")
    check("dials · UP to the flagship under warn with a ruling → SET",
          l.startswith('SET "ACT — Alpha/Judge: s1') and "→ KESTREL · EXTRA" in l, l)
    l = line_for("ACT — Alpha/Mech")
    check("dials · a plate's UP with a ruling under warn → SET",
          l.startswith("SET ") and "→ KESTREL · EXTRA" in l and "its own plate" in l, l)
    l = line_for("ACT — Alpha/Long")
    check("dials · UP with no ruling → KEEP", l.startswith("KEEP ") and "needs a ruling" in l, l)
    l = line_for("ACT — Beta/Main")
    check("dials · DOWN always → SET", l.startswith("SET ") and "→ FINCH · HIGH" in l, l)
    l = line_for("ACT — Delta/Main")
    check("dials · a window that moved in the last 60 s → MID-TURN",
          l.startswith("KEEP ") and "MID-TURN — next pass" in l, l)
    l = line_for("ACT — Alpha/Judge: the hub")
    check("dials · this window → SELF", l.startswith("KEEP ") and "SELF — the user's menu" in l, l)
    l = line_for("ARCH — Alpha/Judge")
    check("dials · a window with no ACT title is kept", l.startswith("KEEP ")
          and "not an ACT window" in l, l)
    l = line_for("ACT — Alpha/Codex")
    check("dials · another vendor's window is kept", l.startswith("KEEP ")
          and "another app's window" in l, l)
    meters(w, flag_pct=85, all_pct=85)
    code, out, _e = run(w, tool, tdir, ["--dials"])
    ls = lines_of(out)
    l = line_for("ACT — Alpha/Mech")
    check("dials · never past warn → KEEP", l.startswith("KEEP ") and "PAST WARN" in l, l)
    l = line_for("ACT — Beta/Main")
    check("dials · DOWN still applies past warn", l.startswith("SET ") and "→ FINCH" in l, l)
    meters(w, flag_pct=12)
    plates_only(w, tool, tdir)

    # ── exit codes and defects ──
    code, out, err = run(w, tool, tdir, ["--bogus"])
    check("exit · an unknown option is the tool's defect → 2", code == 2 and out == ""
          and "--bogus" in err, err)
    code, out, err = run(w, tool, tdir, ["no-such-lane-anywhere"])
    check("exit · an unknown lane is a STOP → 1", code == 1 and out.startswith("STOP — no lane"),
          out)
    lone = os.path.join(w.root, "lone")
    os.makedirs(lone)
    shutil.copy2(tool, os.path.join(lone, "spool.py"))
    code, out, err = run(w, os.path.join(lone, "spool.py"), "", ["Alpha/Judge"])
    check("exit · no neighbours to import → 2, one line", code == 2 and len(lines_of(err)) == 1,
          err)


def remote_proofs(w, tool, tdir):
    """A pick over Remote Control: nothing asked, nothing started, the step handed for
    the lane's HOME machine; a no-remote lane is never worked from the hub folder."""
    meters(w, flag_pct=12)
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech", "--start", "--remote", "on"])
    ls = lines_of(out)
    check("RC1 a start picked over Remote Control is refused, and says so first",
          code == 1 and ls and ls[0].startswith("START REFUSED — Alpha/Mech"), out[:300])
    check("RC1b the refusal hands the step instead: the ribbon, the launch line, the chat box",
          any(l.startswith("\u258c ") for l in ls) and any(l.startswith("cd \"") and " claude " in l
                                                           for l in ls)
          and any("CHAT BOX" in l for l in ls), out[:400])
    check("RC1c no start object and no AFTER list (nothing to start)",
          '"detach"' not in out and "START — only on the user's explicit word" not in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech", "--ask", "--remote", "on"])
    check("RC2 --ask over Remote Control asks nothing: no START MODE, the step for the home machine",
          code == 0 and "START MODE" not in out and "came over Remote Control" in out
          and "\u258c ORCA" in out, out[:400])
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech", "--start"])
    check("RC3 a typed pick (no --remote) starts as before",
          code == 0 and "START — only on the user's explicit word" in out
          and "START REFUSED" not in out, out[:300])
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech", "--ask", "--remote", "on"], machine=WIN_M)
    ls = lines_of(out)
    tags = [t for _i, t, _b in fences(ls)]
    check("RC4 asked on another machine, the step is the HOME machine's: its label, its shell, "
          "its recorded folder", "\u258c ORCA" in out and "zsh" in tags
          and any(l.startswith('cd "%s" && claude' % w.alpha) for l in ls), out[:500])
    code, out, _e = run(w, tool, tdir, ["Delta/Main"])
    check("RC5 a no-remote lane's step says it is never worked from the hub folder",
          "never worked from the hub folder" in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech"])
    check("RC5b a lane with a remote carries no such line", "never worked from the hub folder"
          not in out, out[-300:])
    code, out, _e = run(w, tool, tdir, ["Alpha/Mech", "--remote", "maybe"])
    check("RC6 --remote takes on or off only (a defect, exit 2)", code == 2)


def captured_proofs(w, tool, tdir):
    """G7/G8 — a lane whose opener a button-up capture HEADED (its sitting s7 ran and was
    captured) is handed as s8: the NOTE line under the WHERE line, the s8 title, the prefixed
    sentence, the same in --start and --json. Its project lives only for these runs."""
    e = os.path.join(w.projects, "epsilon")
    os.makedirs(e)
    git(e, "init", "-q")
    write(os.path.join(e, "STATUS.md"), "# epsilon\n\n## Now\nfixture.\n")
    git(e, "add", "-A")
    git(e, "commit", "-q", "-m", "one")
    eh = git(e, "rev-parse", "--short=8", "HEAD")
    when = now()
    day = iso(when)[:10]
    title = "ACT — Eps/Main: s7 — the next stretch of work"
    head_line = ('captured: %s · tools/buttonup.py on the ORCA · the sitting this opener was '
                 'written for, s7 "%s", ran and was captured (last message %s) · its record: '
                 'epsilon/STATUS.md § HANDOFF CAPTURE (hub button-up %s) · next sitting: s8'
                 % (iso(when), title, iso(when - timedelta(minutes=40)), day))
    text = opener("Eps/Main", eh, "%s · fresh Claude session titled `%s`" % (e, title),
                  "%s · HIGH" % MID, judgment="none",
                  body="CAPTURE NOTE (hub button-up %s): the sitting this opener was written for "
                       "— s7 — ran and was captured from the outside, not closed by its own hand. "
                       "Read its HANDOFF CAPTURE block in STATUS first; this is s8. The prompt "
                       "below was written before s7 ran.\n\nread the project status/memory "
                       "first. Pick up Eps/Main on the ORCA: open the opener in this folder and "
                       "follow it." % day)
    text = text.replace("\non: ORCA\n", "\n%s\non: ORCA\n" % head_line, 1)
    write(os.path.join(e, "OPENER.md"), text)
    note = ("NOTE — this opener was written for s7, which ran and was captured %s; its record is "
            "the HANDOFF CAPTURE block in STATUS; opening s8" % day)
    sentence = ("read the project status/memory first — including the HANDOFF CAPTURE block for "
                "s7 (captured %s); this is s8. Pick up Eps/Main on the ORCA: open the opener in "
                "this folder and follow it." % day)
    title8 = "ACT — Eps/Main: s8 — the next stretch of work"
    try:
        code, out, err = run(w, tool, tdir, ["Eps/Main"])
        ls = check_step("captured (posix)", out, "zsh")
        check("captured · G7 exit 0", code == 0, err[:200] or out[:200])
        check("captured · G7 the NOTE line sits directly under the WHERE line",
              len(ls) > 1 and ls[1] == note, ls[1] if len(ls) > 1 else "")
        print("    spool NOTE line: %s" % (ls[1] if len(ls) > 1 else ""))
        chat = [b for _i, t, b in fences(ls) if t == "text"]
        check("captured · G7 the sentence is prefixed, its own head said once",
              chat and chat[0] and chat[0][0] == sentence
              and chat[0][0].count("read the project status/memory first") == 1,
              chat[0][0] if chat and chat[0] else "")
        check("captured · G7 the window is titled for s8",
              ('a window titled "%s"' % title8) in out, [l for l in ls if "DONE WHEN" in l][:1])
        code, out, _e = run(w, tool, tdir, ["Eps/Main", "--start"])
        obj = [json.loads(l) for l in lines_of(out) if l.startswith("{")]
        check("captured · G7 --start's title is s8 and its prompt the prefixed sentence",
              code == 0 and obj and obj[0]["title"] == title8 and obj[0]["prompt"] == sentence,
              (obj[0]["title"], obj[0]["prompt"][:120]) if obj else out[:200])
        code, out, _e = run(w, tool, tdir, ["Eps/Main", "--json"])
        try:
            got = json.loads(out)[0]
        except (ValueError, IndexError, KeyError):
            got = {}
        cap = got.get("captured") or {}
        check("captured · G7 --json carries `captured` (s7 → s8) and the s8 title",
              cap.get("sitting") == 7 and cap.get("next") == 8 and got.get("title") == title8
              and got.get("sentence") == sentence, str(cap)[:200])
        # G8 — an unheaded lane is exactly as it was
        code, out, _e = run(w, tool, tdir, ["Delta/Main"])
        ls = lines_of(out)
        chat = [b for _i, t, b in fences(ls) if t == "text"]
        check("captured · G8 an unheaded lane: no NOTE line, its own sentence, its own title",
              code == 0 and not any(l.startswith("NOTE — this opener") for l in ls)
              and ls[1:2] and ls[1].startswith("\U0001f9e0 SET:")
              and chat and chat[0][0].startswith("read the project status/memory first. Pick up "
                                                 "Delta/Main")
              and 'a window titled "ACT — Delta/Main: s1"' in out, out[:300])
        code, out, _e = run(w, tool, tdir, ["Delta/Main", "--json"])
        try:
            got = json.loads(out)[0]
        except (ValueError, IndexError, KeyError):
            got = {"captured": "unread"}
        check("captured · G8 its --json carries `captured: null`",
              "captured" in got and got["captured"] is None, str(got.get("captured")))
    finally:
        shutil.rmtree(e, ignore_errors=True)


def app_record(w, sid, local):
    """One window in the desktop app's own store, in its real shape, under both homes the
    reader knows (macOS's, and Windows' %APPDATA% — pointed into the fixture by `extra`)."""
    rec = {"sessionId": local, "cliSessionId": sid, "title": "fixture", "isArchived": False,
           "lastActivityAt": int(time.time() * 1000) - 60000, "lastFocusedAt": 0,
           "model": "claude-kestrel-9-1", "effort": "xhigh", "cwd": w.alpha}
    for base in (os.path.join(w.home, "Library", "Application Support"),
                 os.path.join(w.home, "AppData", "Roaming")):
        write_json(os.path.join(base, "Claude", "claude-code-sessions", "acct", "org",
                                "%s.json" % local), rec)


def plates_only(w, tool, tdir):
    """--dials --plates-only is the postman's judge — plates only, never a walk; the
    unreadable plate is a named KEEP in both modes; every --json object carries plate_uuid and
    local_id; a stale meter keeps an UP and never blocks a DOWN."""
    extra = {"APPDATA": os.path.join(w.home, "AppData", "Roaming")}
    live_sessions(w)
    app_record(w, "w-down", "local_gate_down")
    live = os.path.join(w.hub, "live-sessions-%s.json" % POSIX_M)
    body = json.loads(io.open(live, encoding="utf-8").read())
    for sid, title, text in (
            ("w-unread", "ACT — Alpha/Wordy: s4", "Done.\n\n---\n**\u21e9 NEXT STRETCH**\n"
                                                 "whatever comes next\n\n---\n"),
            ("w-unknown", "ACT — Alpha/Gpath: s2", plate("STRETCH", "ZEBRA", "HIGH", "a mind "
                                                         "nobody named"))):
        path = transcript(w, sid, "claude-wren-9-5", "high", text)
        body["sessions"].append({"id": sid, "kind": "claude", "model": "claude-wren-9-5",
                                 "title": title, "transcript": path, "cwd": w.alpha,
                                 "minutes_ago": 1.0})
    write_json(live, body)

    def objs(args):
        code, out, err = run(w, tool, tdir, args, extra=extra)
        try:
            got = json.loads(out)
        except ValueError:
            got = None
        return code, (dict((o["id"], o) for o in got) if isinstance(got, list) else {}), \
            (err or out)[:300]

    code, po, why = objs(["--dials", "--json", "--plates-only"])
    check("plates-only · exit 0, one object per live window", code == 0 and len(po) == 10, why)
    o = po.get("w-up") or {}
    check("plates-only · a plate-less window with a judgment opener is KEEP \"no plate\" — never "
          "the opener's walk", o.get("verdict") == "KEEP" and o.get("why") == "no plate", o)
    o = po.get("w-down") or {}
    check("plates-only · a plate's DOWN still SETs", o.get("verdict") == "SET"
          and o.get("mind") == LOW and o.get("effort") == "high", o)
    o = po.get("w-unread") or {}
    check("plates-only · an arrow with no trio is a named KEEP",
          o.get("verdict") == "KEEP" and o.get("why") == "PLATE UNREADABLE — \u21e9 NEXT STRETCH"
          and o.get("plate_uuid") == "u-w-unread", o)
    o = po.get("w-unknown") or {}
    check("plates-only · a trio whose mind the registry does not know is a named KEEP",
          o.get("verdict") == "KEEP" and str(o.get("why")).startswith("PLATE UNREADABLE — "), o)
    code, dj, why = objs(["--dials", "--json"])
    o = dj.get("w-down") or {}
    check("json · every object carries plate_uuid and local_id (the app's store)",
          code == 0 and all("plate_uuid" in x and "local_id" in x for x in dj.values())
          and o.get("plate_uuid") == "u-w-down" and o.get("local_id") == "local_gate_down"
          and (dj.get("w-up") or {}).get("plate_uuid") == ""
          and (dj.get("w-up") or {}).get("local_id") == "", o)
    o = dj.get("w-up") or {}
    check("json · …and the hand's own road still walks a plate-less window's opener",
          o.get("verdict") == "SET" and str(o.get("why")).startswith("the opener's walk"), o)
    o = dj.get("w-unread") or {}
    check("dials · the unreadable plate is a named KEEP by hand too, never the opener's walk",
          o.get("verdict") == "KEEP" and o.get("why") == "PLATE UNREADABLE — \u21e9 NEXT STRETCH",
          o)
    code, out, _e = run(w, tool, tdir, ["--dials"], extra=extra)
    line = [l for l in lines_of(out) if '"ACT — Alpha/Wordy: s4"' in l]
    check("dials · the text line names it", line and line[0].startswith("KEEP ")
          and line[0].endswith("PLATE UNREADABLE — \u21e9 NEXT STRETCH"), line)
    meters(w, flag_pct=12, minutes_ago=45)
    code, po, why = objs(["--dials", "--json", "--plates-only"])
    o = po.get("w-plate-up") or {}
    check("plates-only · a stale meter keeps an UP: METER STALE",
          code == 0 and o.get("verdict") == "KEEP" and str(o.get("why")).startswith(
              "METER STALE — meter read 45 min ago — refresh: "), o or why)
    o = po.get("w-down") or {}
    check("plates-only · …and never blocks a DOWN", o.get("verdict") == "SET", o)
    code, out, _e = run(w, tool, tdir, ["--dials"], extra=extra)
    check("dials · by hand a stale meter is still the STOP it was", code == 1
          and out.startswith("STOP — meter read 45 min ago"), out[:120])
    code, out, err = run(w, tool, tdir, ["Alpha/Judge", "--plates-only"], extra=extra)
    check("exit · --plates-only without --dials is a defect → 2", code == 2 and "--plates-only"
          in err, err)
    meters(w, flag_pct=12)
    live_sessions(w)


def sha_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def tools_snapshot(tdir):
    """G4: every file in the tools folder the run imports, by sha — the run changes none."""
    out = {}
    for folder, dirs, files in os.walk(tdir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            p = os.path.join(folder, f)
            out[p] = sha_of(p)
    return out


def snapshot(w):
    """Every file outside .git, with its size and mtime: the tool must change none."""
    out = {}
    for base in (w.hub, w.projects, w.home):
        for folder, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in files:
                p = os.path.join(folder, f)
                st = os.stat(p)
                out[p] = (st.st_size, st.st_mtime_ns)
    return out


def universality(w, tool, tdir):
    """The live registry's names never appear in the source; the invented run never prints
    them. The names are READ here, at run time — this file spells none of them."""
    sys.path.insert(0, tdir)
    import exo_registry as rg
    import usage as u
    hub = os.path.dirname(tdir)
    saved = os.environ.pop("EXO_REGISTRY_JSON", None)
    try:
        reg = rg.registry(hub=hub)
    finally:
        if saved is not None:
            os.environ["EXO_REGISTRY_JSON"] = saved
    kinds = set(str(m.get("kind") or "").lower() for m in reg["minds"])
    names = set()
    for m in rg.mind_names(reg) + [k.upper() for k in reg["mind_aliases"]]:
        if m.lower() not in kinds:
            names.add(m)
    for m in rg.machine_names(reg):
        names.add(m)
        names.add(rg.machine_label(reg, m))
    for word in [reg["owner"]["name"], reg["owner"]["short"]] + list(reg["owner"]["aliases"]):
        if str(word).strip():
            names.add(str(word).strip())
    logins = set()
    for _p, d in u.meters(hub, None, None):
        login = str(d.get("login") or "")
        if "@" in login:
            logins.add(login)
            logins.add(u.short_login(login))
    words = set()
    for n in names:
        words.update({n, n.upper(), n.lower(), n.title()})
    words.update(logins)
    words = sorted(w_ for w_ in words if len(w_) >= 3)
    sources = [tool, os.path.abspath(__file__)]
    skills = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(tool))), "skills",
                           "spool", "SKILL.md")]                       # the staged copy
    try:
        import exo_paths
        claude = (exo_paths.paths(tool_file=os.path.join(tdir, "exo_paths.py")).get("roots")
                  or {}).get("claude")
        if claude:
            skills.append(os.path.join(str(claude), "skills", "spool", "SKILL.md"))
    except Exception:
        pass
    for skill in skills:
        if os.path.isfile(skill) and skill not in sources:
            sources.append(skill)
    hits = []
    for src in sources:
        text = io.open(src, encoding="utf-8").read()
        for word in words:
            if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(word), text):
                hits.append("%s in %s" % (word, os.path.basename(src)))
    check("universality · no live mind, machine, owner or login name in the source (%d words, "
          "%d files)" % (len(words), len(sources)), not hits and len(words) > 0, "; ".join(hits))
    printed = "\n".join(ALL_OUT)
    leaked = [word for word in words
              if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(word), printed)]
    check("universality · a run with the invented registry prints none of them",
          not leaked and FLAG in printed and "ORCA" in printed, ", ".join(leaked[:8]))


def main(argv):
    global VERBOSE
    keep = "--keep" in argv
    VERBOSE = "--verbose" in argv
    tool = os.path.join(HERE, "spool.py")
    if "--tool" in argv:
        tool = os.path.abspath(argv[argv.index("--tool") + 1])
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tdir = tools_dir()
    if not tdir or not os.path.isfile(tool):
        print("gate-spool: cannot run — %s" % ("the hub's tools are not found"
                                               if not tdir else "%s is not there" % tool))
        return 2
    t0 = time.time()
    root = tempfile.mkdtemp(prefix="exo-gate-spool-")
    try:
        w = build_world(root)
        before = snapshot(w)
        tools_before = tools_snapshot(tdir)
        proofs(w, tool, tdir)
        remote_proofs(w, tool, tdir)
        # the gate's own writes (meters, live sessions) happen between runs; the last run's
        # world is re-read after one more quiet run, so only the tool's writes could differ
        meters(w, flag_pct=12)
        live_sessions(w)
        mid = snapshot(w)
        run(w, tool, tdir, ["--all"])
        run(w, tool, tdir, ["Delta/Main", "--start"])
        run(w, tool, tdir, ["--dials"])
        after = snapshot(w)
        changed = sorted(p for p in set(mid) | set(after) if mid.get(p) != after.get(p))
        check("read-only · the tool wrote nothing in the hub, the projects or the home",
              not changed, "; ".join(changed[:5]))
        check("read-only · the fixture was built before the first run", bool(before))
        universality(w, tool, tdir)
        tools_after = tools_snapshot(tdir)
        moved = sorted(p for p in set(tools_before) | set(tools_after)
                       if tools_before.get(p) != tools_after.get(p))
        check("read-only · G4 the tools the run imports are unchanged by sha (%d files)"
              % len(tools_before), bool(tools_before) and not moved, "; ".join(moved[:5]))
    except Exception as exc:
        print("gate-spool: cannot run — %s: %s" % (type(exc).__name__, exc))
        return 2
    finally:
        if keep:
            print("kept: %s" % root)
        else:
            shutil.rmtree(root, ignore_errors=True)
    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    print("gate-spool: %d/%d PASS · %.1f s · %s" % (passed, len(RESULTS), time.time() - t0,
                                                  os.path.relpath(tool, os.path.dirname(tdir))))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
