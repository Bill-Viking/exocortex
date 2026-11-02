#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-context-restart.py — the proof of the context-restart rule's machine half.

    python3 gates/gate-context-restart.py [--tools DIR] [--hub-tools DIR] [--skip-spool-gate]
                                          [--keep] [--verbose]

Builds every fixture in the SYSTEM TEMP FOLDER (tempfile.mkdtemp, prefix
exo-prove-context-restart-) — transcripts it writes itself, a COPY of the settings file, a spool
fixture world from gate-spool.py's own builder — and checks, by name:

  (a) 50% of a get_usage-named 1,000,000 window → --read prints nothing
  (b) 81% → the RESTART NOW line with «81%»
  (c) 75% → the CONTEXT 75% line; a second read of the same session prints nothing
  (d) no get_usage, usage 170k → CONTEXT UNREAD naming both windows, never RESTART NOW
  (e) a malformed transcript → exit 0, nothing printed, one log line
  (f) an empty stdin to --hook → exit 0, nothing printed
  (g) --install-hooks --dry on a copied settings file → exactly two added hook lines; after the
      install a second dry run (and a second install) shows none; uninstall restores the file
  (h) spool.py --successor on an opener titled s12 → s13 and the RELEASE / RETITLE / HAND-OFF
      steps
  (i) gate-spool.py on the edited spool.py → no regression against the live spool.py
and the hook's own rules beside them: the Stop hook's once-only crossing, stop_hook_active, a
subagent and a scheduled run heard nothing, the remembered window, the 1M inference, a sidechain
reply ignored, the hot path's imports, the hook writing only its state dir, the /restart skill's
walk, and the Universality sweep (no live mind, machine, owner or login name in the sources).

The tools under test are found beside this file, else in ../tools (the build's install shape),
else where --tools says. The hub's own tools (gate-spool.py, exo_registry.py, usage.py) are
read, never written: the first `tools/` above this file that holds exo_paths.py, else --hub-tools.
Run it from a folder NOT named tools. Exit: 0 every check passed · 1 one failed · 2 cannot run.
Stdlib only, Python 3.9-compatible, macOS and Windows.
"""
import ast
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
VERBOSE = False
OUTPUTS = []


def check(name, ok, detail=""):
    detail = detail if isinstance(detail, str) else repr(detail)
    RESULTS.append((name, bool(ok), detail))
    if VERBOSE or not ok:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                           (" — " + detail[:400]) if detail and not ok else ""))


def sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def write(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def arg(argv, flag):
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return ""


def find_under_test(argv):
    named = arg(argv, "--tools")
    for cand in ([named] if named else []) + [HERE, os.path.join(os.path.dirname(HERE), "tools")]:
        if cand and os.path.isfile(os.path.join(cand, "context-restart.py")):
            return os.path.abspath(cand)
    return ""


def find_hub_tools(argv):
    named = arg(argv, "--hub-tools")
    if named and os.path.isfile(os.path.join(named, "exo_paths.py")):
        return os.path.abspath(named)
    if os.path.isfile(os.path.join(HERE, "exo_paths.py")):
        return HERE
    cur = HERE
    for _ in range(8):
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cand = os.path.join(parent, "tools")
        if os.path.isfile(os.path.join(cand, "exo_paths.py")):
            return cand
        cur = parent
    return ""


def skill_path(tools):
    """The staged skill (the build's install shape), else the installed one beside the vendor's
    own skills."""
    staged = os.path.join(os.path.dirname(tools), "skills", "restart", "SKILL.md")
    if os.path.isfile(staged):
        return staged
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "skills", "restart", "SKILL.md")


# ═════════════════════════════════════════════════════════════════════════════
# transcripts the gate writes itself
# ═════════════════════════════════════════════════════════════════════════════

def usage_result(window, session="self"):
    body = {"plan": {"windows": []},
            "context": {"session": session, "status": "ok", "tokensUsed": 1,
                        "contextWindow": window, "percentUsed": 1}}
    return {"type": "user", "timestamp": "2026-10-21T10:00:00.000Z",
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1",
                 "content": [{"type": "text", "text": json.dumps(body)}]}]}}


def reply(now, model="claude-gate-9-1", sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain, "uuid": "u%d" % now,
            "message": {"model": model, "role": "assistant",
                        "content": [{"type": "text", "text": "work"}],
                        "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1000,
                                  "cache_read_input_tokens": now - 1003, "output_tokens": 50}}}


def transcript(folder, sid, now=None, window=None, extra=None, sidechain_after=None):
    recs = [{"type": "user", "message": {"role": "user", "content": "go"}}]
    if window:
        recs.append(usage_result(window))
    if now is not None:
        recs.append(reply(now))
    if sidechain_after is not None:
        recs.append(reply(sidechain_after, sidechain=True))
    recs.extend(extra or [])
    path = os.path.join(folder, "%s.jsonl" % sid)
    write(path, "\n".join(json.dumps(r) for r in recs) + "\n")
    return path


def run(cmd, stdin=None, cwd=None, env=None, timeout=120):
    e = dict(os.environ)
    e.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    e.update(env or {})
    p = subprocess.run(cmd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=cwd, env=e, universal_newlines=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    OUTPUTS.append(p.stdout + p.stderr)
    return p.returncode, p.stdout, p.stderr


def log_count(state):
    path = os.path.join(state, "context-restart.log")
    try:
        with io.open(path, encoding="utf-8") as fh:
            return len([l for l in fh.read().splitlines() if l.strip()])
    except OSError:
        return 0


def tree(folder):
    out = {}
    for base, _dirs, files in os.walk(folder):
        for name in files:
            p = os.path.join(base, name)
            out[os.path.relpath(p, folder)] = sha(p)
    return out


# ═════════════════════════════════════════════════════════════════════════════
# (a)–(f) and the hook's own rules
# ═════════════════════════════════════════════════════════════════════════════

def reading_cases(tool, root):
    t = os.path.join(root, "transcripts")
    st = os.path.join(root, "state-read")
    py = sys.executable

    def read(path, state=st, more=()):
        return run([py, tool, "--read", path, "--state-dir", state] + list(more))

    code, out, err = read(transcript(t, "case-a", now=500000, window=1000000))
    check("(a) 50% of a get_usage 1,000,000 window → nothing", code == 0 and out == "",
          out + err)
    code, out, err = read(transcript(t, "case-b", now=810000, window=1000000))
    check("(b) 81% → the RESTART NOW line with «81%»",
          code == 0 and out.startswith("RESTART NOW — context 81% (810,000 of 1,000,000 tokens)")
          and "start the successor with /restart (the Context-restart law)" in out
          and "assumed" not in out and out.count("\n") == 1, out + err)
    path_c = transcript(t, "case-c", now=750000, window=1000000)
    code, out, err = read(path_c)
    check("(c) 75% → the CONTEXT 75% line",
          code == 0 and out.strip() == "CONTEXT 75% — plan the carryover; the restart line "
          "comes at 80 (the Context-restart law)", out + err)
    code, out, err = read(path_c)
    check("(c) a second read of the same session prints nothing (once per session)",
          code == 0 and out == "", out + err)
    code, out, err = read(transcript(t, "case-d", now=170000))
    # The opposite case of the hook's window ASSUMPTION: an unread window is never judged — four
    # fresh 1M windows can read 93% of an assumed 200k and be told RESTART NOW.
    check("(d) no get_usage, 170k → CONTEXT UNREAD naming both windows, never RESTART NOW",
          code == 0 and "CONTEXT UNREAD — 170,000 tokens; window assumed 200k (85%) or 1M (17%)" in out
          and "RESTART NOW" not in out and "never orders a restart on an assumption" in out, out)
    bad = os.path.join(t, "case-e.jsonl")
    write(bad, 'not a transcript at all\n{"type": "assistant", "message": {"usage": '
               '{"input_tokens": 5\n')
    before = log_count(st)
    code, out, err = read(bad)
    check("(e) a malformed transcript → exit 0, nothing printed, one log line",
          code == 0 and out == "" and err == "" and log_count(st) == before + 1,
          "exit %d · out %r · err %r · log %d→%d" % (code, out, err, before, log_count(st)))
    garbage = os.path.join(t, "case-e2.jsonl")
    write(garbage, "plain words\nno records here\n")
    before = log_count(st)
    code, out, err = read(garbage)
    check("(e) a file with no JSON record → exit 0, nothing printed, one log line",
          code == 0 and out == "" and log_count(st) == before + 1, out + err)

    hs = os.path.join(root, "state-hook")
    before = log_count(hs)
    code, out, err = run([py, tool, "--hook", "--vendor", "claude", "--state-dir", hs], stdin="")
    check("(f) an empty stdin to --hook → exit 0, nothing printed (one log line)",
          code == 0 and out == "" and err == "" and log_count(hs) == before + 1,
          "exit %d · %r · %r" % (code, out, err))
    code, out, err = run([py, tool, "--hook", "--vendor", "claude", "--state-dir", hs],
                         stdin="{not json")
    check("(f) malformed JSON on stdin → exit 0, nothing printed", code == 0 and out == "",
          out + err)

    # ── the hook's own rules ──
    def hook(event, path, sid, state=hs, **more):
        ev = {"session_id": sid, "transcript_path": path, "cwd": root, "hook_event_name": event}
        ev.update(more)
        code, out, err = run([py, tool, "--hook", "--vendor", "claude", "--state-dir", state],
                             stdin=json.dumps(ev))
        try:
            got = json.loads(out) if out.strip() else None
        except ValueError:
            got = "unparsed"
        return code, got, out + err

    p81 = transcript(t, "hook-81", now=810000, window=1000000)
    code, got, raw = hook("UserPromptSubmit", p81, "hook-81")
    ctx = ((got or {}).get("hookSpecificOutput") or {}) if isinstance(got, dict) else {}
    check("hook · UserPromptSubmit at 81% → one additionalContext line, its event named",
          code == 0 and ctx.get("hookEventName") == "UserPromptSubmit"
          and ctx.get("additionalContext", "").startswith("RESTART NOW — context 81%")
          and "\n" not in ctx.get("additionalContext", ""), raw)
    code, got2, raw = hook("UserPromptSubmit", p81, "hook-81")
    check("hook · at 80 and up the line rides EVERY turn's start", code == 0 and got2 == got, raw)
    code, got, raw = hook("Stop", p81, "hook-81")
    check("hook · Stop stays silent once a turn's start has said RESTART", code == 0
          and got is None, raw)

    pmid = transcript(t, "hook-mid", now=820000, window=1000000)
    code, got, raw = hook("Stop", pmid, "hook-mid", stop_hook_active=True)
    check("hook · Stop with stop_hook_active → silent (it can never loop)", code == 0
          and got is None, raw)
    code, got, raw = hook("Stop", pmid, "hook-mid")
    ctx = ((got or {}).get("hookSpecificOutput") or {}) if isinstance(got, dict) else {}
    check("hook · Stop catches a crossing inside a turn once, as Stop's additionalContext",
          code == 0 and ctx.get("hookEventName") == "Stop"
          and ctx.get("additionalContext", "").startswith("RESTART NOW — context 82%"), raw)
    code, got, raw = hook("Stop", pmid, "hook-mid")
    check("hook · a second Stop in the same session → silent", code == 0 and got is None, raw)
    p75 = transcript(t, "hook-75", now=750000, window=1000000)
    code, got, raw = hook("Stop", p75, "hook-75")
    check("hook · Stop at 70–79 → silent (a Stop line costs a turn)", code == 0 and got is None,
          raw)

    code, got, raw = hook("UserPromptSubmit", p81, "hook-agent", agent_id="a-1")
    check("hook · a subagent's event (agent_id) → silent", code == 0 and got is None, raw)
    psch = transcript(t, "hook-sched", now=900000, window=1000000)
    code, got, raw = hook("UserPromptSubmit", psch, "hook-sched",
                          prompt="<scheduled-task name=\"x\">run</scheduled-task>")
    code2, got2, raw2 = hook("Stop", psch, "hook-sched")
    check("hook · a scheduled run hears nothing, at its prompt or its Stop",
          code == 0 and got is None and code2 == 0 and got2 is None, raw + raw2)
    code, got, raw = hook("PreToolUse", p81, "hook-other")
    check("hook · an event it does not answer → silent", code == 0 and got is None, raw)
    code2, out2, _e = run([py, tool, "--hook", "--vendor", "codex", "--state-dir", hs],
                          stdin=json.dumps({"session_id": "c", "transcript_path": p81,
                                            "hook_event_name": "UserPromptSubmit"}))
    check("hook · vendor codex → silent (off until its probe)", code2 == 0 and out2 == "",
          out2)

    # the window, remembered once seen
    rem = os.path.join(t, "hook-rem.jsonl")
    transcript(t, "hook-rem", now=300000, window=1000000)
    code, got, raw = hook("UserPromptSubmit", rem, "hook-rem")
    check("hook · 30% of a named 1M window → silent", code == 0 and got is None, raw)
    transcript(t, "hook-rem", now=850000)                 # the get_usage left the tail
    code, got, raw = hook("UserPromptSubmit", rem, "hook-rem")
    ctx = ((got or {}).get("hookSpecificOutput") or {}) if isinstance(got, dict) else {}
    line = ctx.get("additionalContext", "")
    check("hook · the window is remembered per session once seen (no «assumed»)",
          line.startswith("RESTART NOW — context 85% (850,000 of 1,000,000 tokens)")
          and "assumed" not in line, raw)

    # An unread window: 185,137 tokens, no get_usage in the tail.
    unread = transcript(t, "hook-unread", now=185137)
    code, got, raw = hook("Stop", unread, "hook-unread")
    check("hook · Stop on an UNREAD window is silent (no turn spent on an assumption)",
          code == 0 and got is None, raw)
    code, got, raw = hook("UserPromptSubmit", unread, "hook-unread")
    ctx = ((got or {}).get("hookSpecificOutput") or {}) if isinstance(got, dict) else {}
    line = ctx.get("additionalContext", "")
    check("hook · a prompt on an UNREAD window gets CONTEXT UNREAD, never RESTART NOW",
          line.startswith("CONTEXT UNREAD — 185,137 tokens; window assumed 200k (93%) or 1M (19%)")
          and "RESTART NOW" not in line, raw)
    code, out, err = read(transcript(t, "case-1m", now=820000), more=["--all"])
    check("1M · a context past 200k with no window → UNREAD, 1M the only window left, said",
          "CONTEXT UNREAD — 820,000 tokens; window assumed 1M (82%) (context past 200k)" in out
          and "RESTART NOW" not in out, out)
    code, out, err = read(transcript(t, "case-side", now=500000, window=1000000,
                                     sidechain_after=950000))
    check("sidechain · a subagent's reply is not this window's context", code == 0 and out == "",
          out)
    other = transcript(t, "case-other", now=500000,
                       extra=[usage_result(2000, session="some-other-session")])
    code, out, err = read(other, more=["--all"])
    check("get_usage about ANOTHER session is not this window's", "assumed 1M" in out, out)
    st_fresh = os.path.join(root, "state-fresh")
    before = log_count(st_fresh)
    code, out, err = read(transcript(t, "case-fresh"), state=st_fresh)
    empty = os.path.join(t, "case-empty.jsonl")
    write(empty, "")
    code2, out2, _e = read(empty, state=st_fresh)
    check("a window with no reply usage yet → silent, and not logged as a failure",
          code == 0 and out == "" and code2 == 0 and out2 == "" and log_count(st_fresh) == before,
          out + out2)
    code, out, err = run([py, tool, "--read", os.path.join(t, "case-c.jsonl"), "--all"])
    check("--read with no state dir is a pure readout (prints, writes nothing)",
          code == 0 and out.startswith("CONTEXT 75%"), out)

    # the hook writes only its state dir
    snap = tree(t)
    hook("UserPromptSubmit", p81, "hook-write")
    hook("Stop", pmid, "hook-write2")
    read(path_c)
    check("writes · the hook and --read write only their state dir (transcripts untouched)",
          tree(t) == snap)
    names = sorted(os.listdir(os.path.join(hs, "sessions")))
    check("writes · one state file per session id, under sessions/",
          "hook-81.json" in names and all(n.endswith(".json") for n in names), str(names))

    # the hot path imports nothing but json, os and sys at module level
    mod = ast.parse(io.open(tool, encoding="utf-8").read())
    top = set()
    for node in mod.body:
        if isinstance(node, ast.Import):
            top.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            top.add(node.module or "")
    check("hot path · module-level imports are json, os and sys only", top == {"json", "os",
                                                                             "sys"}, str(top))
    t0 = time.time()
    hook("UserPromptSubmit", p81, "hook-speed")
    took = time.time() - t0
    check("hot path · one hook run under its 5 s timeout with room (%.2f s)" % took, took < 2.0)


# ═════════════════════════════════════════════════════════════════════════════
# (g) the installer, on a COPY of the settings file
# ═════════════════════════════════════════════════════════════════════════════

FIXTURE_SETTINGS = {
    "model": "gate",
    "hooks": {
        "UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 5, "command":
                                         '"/opt/gate/bin/python3" "/gate/hub/tools/effort.py" '
                                         '--hook --vendor claude --state-dir "/gate/st"'}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "/gate/other-hook.sh"}]}]}}


def effort_python(text):
    try:
        data = json.loads(text)
    except ValueError:
        return ""
    for rows in (data.get("hooks") or {}).values():
        for row in rows:
            for h in row.get("hooks") or []:
                cmd = str(h.get("command") or "")
                if "effort.py" in cmd and "--hook" in cmd:
                    return cmd[1:cmd.index('"', 1)] if cmd.startswith('"') else cmd.split()[0]
    return ""


def without_ours(data):
    hooks = data.get("hooks") or {}
    out = {}
    for event, rows in hooks.items():
        keep = [r for r in rows if not any("context-restart.py" in str(h.get("command"))
                                           for h in r.get("hooks") or [])]
        if keep:
            out[event] = keep
    data = dict(data)
    data["hooks"] = out
    return data


def install_cases(tool, root, hub):
    """The copy echoes the user's own settings in its diff, so these runs' output is kept out of
    the printed Universality sweep (it is the user's file, shown back to the user)."""
    mark = len(OUTPUTS)
    try:
        _install_cases(tool, root, hub)
    finally:
        del OUTPUTS[mark:]


def _install_cases(tool, root, hub):
    py = sys.executable
    live = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or
                        os.path.join(os.path.expanduser("~"), ".claude"), "settings.json")
    live_sha = sha(live)
    home = os.path.join(root, "home")
    os.makedirs(home)
    settings = os.path.join(root, "settings-copy.json")
    if os.path.isfile(live):
        shutil.copyfile(live, settings)
        source = "a copy of the live settings file"
        text = io.open(settings, encoding="utf-8").read()
        if "context-restart.py" in text:
            # the live file already carries this tool's entries (installed): the copy is made a
            # pre-install world, so the dry run has its two lines to add (an installed folder
            # would otherwise leave it nothing to add)
            try:
                stripped = without_ours(json.loads(text))
                write(settings, json.dumps(stripped, indent=2, ensure_ascii=False) + "\n")
                source = "a copy of the live settings file, this tool's own entries stripped"
            except ValueError:
                pass
    else:
        write(settings, json.dumps(FIXTURE_SETTINGS, indent=2) + "\n")
        source = "the gate's fixture settings"
    os.chmod(settings, 0o600)
    original = io.open(settings, encoding="utf-8").read()
    original_sha = sha(settings)
    state = os.path.join(root, "state-install")
    base = [py, tool, "--settings", settings, "--home", home, "--hub", hub,
            "--state-dir", state, "--vendor", "claude"]
    code, out, err = run(base + ["--install-hooks", "--dry"])
    would = [l for l in out.splitlines() if l.startswith("would add ")]
    added = [l for l in out.splitlines() if l.lstrip().startswith("+")
             and not l.lstrip().startswith("+++") and '"command":' in l]
    check("(g) --dry on %s → exactly two hook lines added (UserPromptSubmit, Stop)" % source,
          code == 0 and len(would) == 2 and would[0].startswith("would add Stop ·")
          and would[1].startswith("would add UserPromptSubmit ·") and len(added) == 2
          and all("context-restart.py" in l and "--hook" in l for l in added), out + err)
    check("(g) --dry wrote nothing (the file's bytes, no state dir)",
          sha(settings) == original_sha and not os.path.exists(state))
    want_py = effort_python(original)
    check("(g) the command names the interpreter effort.py's own entries name",
          (not want_py) or all(('"%s"' % want_py) in l for l in would), str(would)[:300])
    code, out, err = run(base + ["--install-hooks"])
    after = io.open(settings, encoding="utf-8").read()
    try:
        merged = json.loads(after)
    except ValueError:
        merged = {}
    rows = [(e, h.get("command")) for e, rs in (merged.get("hooks") or {}).items() for r in rs
            for h in r.get("hooks") or [] if "context-restart.py" in str(h.get("command"))]
    check("(g) the install adds the two entries and keeps every other entry as it was",
          code == 0 and sorted(e for e, _c in rows) == ["Stop", "UserPromptSubmit"]
          and without_ours(merged) == without_ours(json.loads(original)), out + err)
    # ASSUMES: posix mode bits. Windows keeps only the read-only bit (os.chmod honours S_IWRITE
    # alone, and st_mode reads 0o666 for a writable file), so there "kept its mode" means the
    # install left the file writable, as it found it. The false case for the posix reading is
    # a Windows run, which fails this check on a correct install.
    mode_kept = (os.access(settings, os.W_OK) if os.name == "nt"
                 else (os.stat(settings).st_mode & 0o777) == 0o600)
    check("(g) the install backed the file up into its own state dir and kept its mode",
          os.path.isdir(os.path.join(state, "backups")) and mode_kept, out)
    installed_sha = sha(settings)
    code, out, err = run(base + ["--install-hooks", "--dry"])
    check("(g) a second dry run after the install shows none",
          code == 0 and not any(l.startswith("would add") for l in out.splitlines())
          and "already installed" in out, out)
    code, out, err = run(base + ["--install-hooks"])
    check("(g) a second install changes nothing and says so",
          code == 0 and sha(settings) == installed_sha and "nothing to write" in out, out)
    code, out, err = run([py, tool, "--check", "--settings", settings, "--home", home])
    check("(g) --check names both entries, exit 0",
          code == 0 and "Stop · " in out and "UserPromptSubmit · " in out, out + err)
    code, out, err = run(base + ["--uninstall-hooks"])
    restored = io.open(settings, encoding="utf-8").read()
    check("(g) uninstall removes only its own entries (the JSON is the original's)",
          code == 0 and json.loads(restored) == json.loads(original), out + err)
    code, out, err = run([py, tool, "--check", "--settings", settings, "--home", home])
    check("(g) --check after uninstall → not installed, exit 2",
          code == 2 and out.startswith("not installed"), out)
    if os.path.isfile(live):
        check("(g) the live settings file was only read (its sha is unchanged)",
              sha(live) == live_sha)


# ═════════════════════════════════════════════════════════════════════════════
# (h) spool.py --successor, in gate-spool's own fixture world
# ═════════════════════════════════════════════════════════════════════════════

def load_gate_spool(hub_tools):
    path = os.path.join(hub_tools, "gate-spool.py")
    spec = importlib.util.spec_from_file_location("gate_spool_fixture", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def successor_cases(spool, hub_tools, root):
    gs = load_gate_spool(hub_tools)
    world = os.path.join(root, "spool-world")
    os.makedirs(world)
    w = gs.build_world(world)
    gs.meters(w, flag_pct=12)
    gs.live_sessions(w)
    head = gs.git(w.alpha, "rev-parse", "--short=8", "HEAD")

    def oi(title):
        return ("ORCA — %s · project `alpha` (reuse) · fresh Claude session titled `%s`"
                % (w.alpha, title))
    retiring = "ACT — Alpha/Next: s12 — carry the plan on"
    write(os.path.join(w.alpha, "OPENER-Next.md"),
          gs.opener("Alpha/Next", head, oi(retiring), "%s · HIGH" % gs.MID, judgment="none"))
    write(os.path.join(w.alpha, "OPENER-Ahead.md"),
          gs.opener("Alpha/Ahead", head, oi("ACT — Alpha/Ahead: s13 — the next stretch"),
                    "%s · HIGH" % gs.MID, judgment="none"))

    def sp(args, **kw):
        code, out, err = gs.run(w, spool, hub_tools, args, **kw)
        OUTPUTS.append(out + err)
        return code, out, err

    code, out, err = sp(["Alpha/Next", "--successor", "--retiring", retiring])
    ls = out.splitlines()
    check("(h) --successor exits 0, its reminder first", code == 0 and ls and
          ls[0].startswith("SUCCESSOR — the Context-restart law starts it"), (err or out)[:400])
    check("(h) the step's ribbon and DONE WHEN name the s13 title",
          len(ls) > 1 and ls[1].startswith("▌ ")
          and 'a window titled "ACT — Alpha/Next: s13 — carry the plan on"' in out, out[:600])
    objs = [json.loads(l) for l in ls if l.startswith("{")]
    obj = objs[0] if objs else {}
    check("(h) one start object with exactly the seven fields, titled s13",
          len(objs) == 1 and set(obj) == {"title", "cwd", "model", "effort", "prompt",
                                          "background", "name"}
          and obj["title"] == "ACT — Alpha/Next: s13 — carry the plan on", str(obj)[:300])
    bg = obj.get("background", "")
    check("(h) the background ends with the successor sentence and carries the s13 ritual",
          bg.endswith("Successor of «%s», started under the Context-restart law; the retiring "
                      "window's last-turn facts arrive by message." % retiring)
          and '--claim Alpha/Next "ACT — Alpha/Next: s13 — carry the plan on"' in bg, bg[-400:])
    check("(h) the prompt is the opener's own sentence",
          obj.get("prompt", "").startswith("read the project status/memory first. Pick up "
                                           "Alpha/Next"), obj.get("prompt", ""))
    after = [l for l in ls if l.startswith("AFTER ")]
    want = ["RELEASE", "STAMP OFF", "detach_session", "the dial, never asked", "RETITLE",
            "HAND-OFF", "set_view", "say, in one line"]
    order_ok = len(after) == len(want) and all(
        a.startswith("AFTER %d · %s" % (i + 1, k)) for i, (a, k) in enumerate(zip(after, want)))
    check("(h) the AFTER list: RELEASE · STAMP OFF before the detach; RETITLE · HAND-OFF after "
          "the dial", order_ok, "\n".join(after))
    rel = after[0] if after else ""
    check("(h) RELEASE names the lane's arc and the retiring title",
          "claim.py" in rel and '--release Alpha/Next "%s"' % retiring in rel, rel)
    stamp = after[1] if len(after) > 1 else ""
    check("(h) STAMP OFF names this window's own mind, read from the record",
          "i-am.py" in stamp and '--off %s "%s"' % (gs.MID, retiring) in stamp, stamp)
    today = datetime.now().strftime("%Y-%m-%d")
    retitle = after[4] if len(after) > 4 else ""
    check("(h) RETITLE → the ARCH title with the retiring sitting and today's date",
          retitle == 'AFTER 5 · RETITLE · set_session_title self → "ARCH — Alpha/Next: s12 — '
          '<what it did> · %s"' % today, retitle)
    check("(h) HAND-OFF points at the /restart skill's shape",
          len(after) > 5 and "SendMessage to the successor" in after[5]
          and "/restart skill" in after[5], after[5] if len(after) > 5 else "")
    check("(h) the say line names the successor and its project",
          after and "successor «ACT — Alpha/Next: s13 — carry the plan on» started under alpha"
          in after[-1], after[-1] if after else "")

    code, out, err = sp(["Alpha/Next", "--successor", "--retiring", retiring, "--json"])
    try:
        got = json.loads(out)[0]
    except (ValueError, IndexError, KeyError):
        got = {}
    suc = got.get("successor") or {}
    check("(h) --json carries the start object and the successor block (s12 → s13)",
          code == 0 and (got.get("start") or {}).get("title") == obj.get("title")
          and suc.get("retiring_sitting") == 12 and suc.get("sitting") == 13
          and len(suc.get("after") or []) == 8, out[:300])

    code, out, err = sp(["Alpha/Ahead", "--successor", "--retiring",
                         "ACT — Alpha/Ahead: s12 — the stretch before"])
    check("(h) an opener already naming s13 for a retiring s12 stays s13 (never counted twice)",
          code == 0 and 'a window titled "ACT — Alpha/Ahead: s13 — the next stretch"' in out
          and "already names s13" in out, out[:400])
    code, out, err = sp(["Alpha/Wordy", "--successor", "--retiring",
                         "ACT — Alpha/Wordy: the old one"])
    objs = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    check("(h) a title with no sitting number → «(next)» kept within 60, said on a ⚠ line",
          code == 0 and objs and objs[0]["title"].endswith(" (next)")
          and len(objs[0]["title"]) <= 60 and "⚠ the opener's title carries no sitting number"
          in out, (objs[0]["title"] if objs else out[:300]))
    code, out, err = sp(["Alpha/Next", "--successor"])
    check("(h) --successor without --retiring → exit 2, one line", code == 2
          and "--retiring" in err and out == "", err)
    code, out, err = sp(["Alpha/Next", "--retiring", retiring])
    check("(h) --retiring without --successor → exit 2", code == 2, err)
    code, out, err = sp(["Alpha/Next", "Alpha/Mech", "--successor", "--retiring", retiring])
    check("(h) --successor names one lane", code == 2 and "one lane" in err, err)
    code, out, err = sp(["Alpha/Next", "--start"])
    objs = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
    check("(h) --start on the same lane is unchanged (its own s12 title, no successor words)",
          code == 0 and objs and objs[0]["title"] == retiring
          and "Successor of" not in objs[0]["background"]
          and not any(l.startswith("AFTER 1 · RELEASE") for l in out.splitlines()), out[:300])


# ═════════════════════════════════════════════════════════════════════════════
# (i) the existing spool gate, on the edited copy and on the live tool
# ═════════════════════════════════════════════════════════════════════════════

def spool_gate(spool, hub_tools, root):
    gate = os.path.join(hub_tools, "gate-spool.py")
    live = os.path.join(hub_tools, "spool.py")
    got = {}
    mark = len(OUTPUTS)
    for label, path in (("copy", spool), ("live", live)):
        code, out, err = run([sys.executable, gate, "--tool", path], cwd=root, timeout=600)
        m = re.search(r"gate-spool: (\d+)/(\d+) PASS", out)
        fails = sorted(set(re.findall(r"^FAIL (.+?)(?: — |$)", out, re.M)))
        got[label] = (int(m.group(1)) if m else -1, int(m.group(2)) if m else -1, fails, code)
    del OUTPUTS[mark:]                     # gate-spool sweeps its own runs' output
    c, l = got["copy"], got["live"]
    print("    gate-spool on the edited copy: %d/%d · on the live spool.py: %d/%d%s"
          % (c[0], c[1], l[0], l[1], (" · live fails too: %s" % "; ".join(l[2])) if l[2] else ""))
    check("(i) gate-spool on the edited copy: no regression against the live spool.py "
          "(copy %d/%d · live %d/%d)" % (c[0], c[1], l[0], l[1]),
          c[0] >= 0 and l[0] >= 0 and c[1] == l[1] and c[0] >= l[0] and set(c[2]) <= set(l[2]),
          "copy fails: %s · live fails: %s" % (c[2], l[2]))
    return got


# ═════════════════════════════════════════════════════════════════════════════
# the /restart skill, and the Universality sweep
# ═════════════════════════════════════════════════════════════════════════════

def skill_cases(skill):
    text = io.open(skill, encoding="utf-8").read() if os.path.isfile(skill) else ""
    m = re.match(r"^---\nname: restart\ndescription: (.+?)\n---\n", text, re.S)
    check("skill · frontmatter: name restart and its description", bool(m)
          and "Context-restart law" in m.group(1) and "RESTART NOW" in m.group(1), skill)
    steps = re.findall(r"^## (\d) · ", text, re.M)
    check("skill · the walk, numbered 0 to 8", steps == [str(i) for i in range(9)], str(steps))
    for label, needle in (("the meter first-hand", "get_usage"),
                          ("the opener check", "collect-openers.py --expand"),
                          ("the successor road", "spool.py <lane> --successor --retiring"),
                          ("the start", "start_session"), ("the detach", "detach_session"),
                          ("the retitle", "set_session_title"), ("the hand-off", "SendMessage"),
                          ("the hand-off shape", "From «<retiring title>» (retired <HH:MM>):"),
                          ("the notice line", "Context at N%: carryover written, successor "
                                              "«<title>» started under <project>; this window "
                                              "retires."),
                          ("no pick-up plate", "pick-up plate is NOT handed")):
        check("skill · carries %s" % label, needle in text, needle)


def universality(hub_tools, sources, printed):
    sys.path.insert(0, hub_tools)
    import exo_registry as rg
    import usage as u
    hub = os.path.dirname(hub_tools)
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
    words = set()
    for n in names:
        words.update({n, n.upper(), n.lower(), n.title()})
    for _p, d in u.meters(hub, None, None):
        login = str(d.get("login") or "")
        if "@" in login:
            words.update({login, u.short_login(login)})
    words = sorted(x for x in words if len(x) >= 3)
    hits = []
    for src in sources:
        text = io.open(src, encoding="utf-8").read()
        for word in words:
            if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(word), text):
                hits.append("%s in %s" % (word, os.path.basename(src)))
    check("universality · no live mind, machine, owner or login name in the sources "
          "(%d words, %d files)" % (len(words), len(sources)), not hits and words,
          "; ".join(hits))
    leaked = [x for x in words
              if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(x), printed)]
    check("universality · the gate's runs print none of them", not leaked, ", ".join(leaked[:8]))


# ═════════════════════════════════════════════════════════════════════════════

def main(argv):
    global VERBOSE
    VERBOSE = "--verbose" in argv
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tools = find_under_test(argv)
    hub_tools = find_hub_tools(argv)
    if not tools or not hub_tools:
        print("gate-context-restart: cannot run — %s" % ("the tools under test are not found"
                                                         if not tools else
                                                         "the hub's tools are not found"))
        return 2
    if os.path.basename(os.getcwd()) == "tools":
        print("gate-context-restart: cannot run — run it from a folder not named tools")
        return 2
    tool = os.path.join(tools, "context-restart.py")
    spool = os.path.join(tools, "spool.py")
    skill = skill_path(tools)
    t0 = time.time()
    root = tempfile.mkdtemp(prefix="exo-prove-context-restart-")
    hub_before = {}
    for name in ("spool.py", "gate-spool.py", "exo_paths.py", "exo_registry.py", "usage.py",
                 "effort.py", "collect-openers.py"):
        hub_before[name] = sha(os.path.join(hub_tools, name))
    try:
        reading_cases(tool, root)
        install_cases(tool, root, os.path.dirname(hub_tools))
        successor_cases(spool, hub_tools, root)
        if "--skip-spool-gate" in argv:
            print("    (i) skipped on --skip-spool-gate")
        else:
            spool_gate(spool, hub_tools, root)
        skill_cases(skill)
        sources = [tool, os.path.abspath(__file__), spool] + ([skill] if os.path.isfile(skill)
                                                              else [])
        universality(hub_tools, sources, "\n".join(OUTPUTS))
        moved = [n for n, s in hub_before.items() if sha(os.path.join(hub_tools, n)) != s]
        check("read-only · the hub's own tools are unchanged by sha (%d files)" % len(hub_before),
              not moved, ", ".join(moved))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("gate-context-restart: cannot run — %s: %s" % (type(exc).__name__, exc))
        return 2
    finally:
        if "--keep" in argv:
            print("kept: %s" % root)
        else:
            shutil.rmtree(root, ignore_errors=True)
    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    print("gate-context-restart: %d/%d PASS · %.1f s · %s" % (passed, len(RESULTS),
                                                            time.time() - t0, tool))
    if passed != len(RESULTS):
        first = [n for n, ok, _d in RESULTS if not ok][0]
        print("first failing: %s" % first)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
