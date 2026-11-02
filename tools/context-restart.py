#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""context-restart.py — the machine half of the context-restart rule.

A window whose own context is about four fifths full writes its carryover, gives one line of
notice and starts its successor itself (the /restart skill). This hook is the part that
NOTICES: it reads the window's own transcript tail at a turn's start and at its end, and says
ONE line at the moment it is needed — never a wall, never a block, never a model call.

    python3 tools/context-restart.py --hook --vendor claude [--state-dir DIR] [--hub DIR]
    python3 tools/context-restart.py --read TRANSCRIPT [--state-dir DIR] [--all]
    python3 tools/context-restart.py --install-hooks   [--vendor claude] [--dry] [--state-dir DIR]
    python3 tools/context-restart.py --uninstall-hooks [--vendor claude] [--dry] [--state-dir DIR]
    python3 tools/context-restart.py --check
    common: [--home DIR] [--settings FILE] [--python PATH]

On Windows the same, as `python tools\\context-restart.py ...`.

THE READING. CONTEXT NOW is the last main-thread reply's usage: input_tokens +
cache_creation_input_tokens + cache_read_input_tokens — what the model saw on its last call.
THE WINDOW is `context.contextWindow` from the newest get_usage result in the tail, remembered
per session in the state dir once seen (so it outlives the tail). With none the window is UNREAD:
the hook never orders a restart on an assumption. From 70 percent of the smallest window a model
can have (200k) it prints one CONTEXT UNREAD line at each prompt — the tokens, what each possible
window makes of them, and the ask for one get_usage — and says nothing at Stop (a Stop line costs a
turn, and there is no crossing to catch on a guess); a context past 200k leaves 1M as the only
window. PERCENT = 100 x now / window, rounded half up.
ASSUMES: nothing about which window this model has. An unread window must not be judged:
a fresh 1M window can read 93 percent of an assumed 200k at its first Stop and be
told RESTART NOW at a fifth of its room.

THE LINES, at most one per event:
    under 70     nothing
    70 to 79     CONTEXT 7N% — ... — once per session, at a turn's start
    80 and up    RESTART NOW — context N% (now of window tokens) — ... — at EVERY turn's start

THE TWO EVENTS. UserPromptSubmit puts the line beside the prompt at once. Stop is different, and
the docs say how (code.claude.com/docs/en/hooks#stop): a Stop line "continues the conversation"
— the window acts on it AT ONCE, at the cost of a turn, and it is not held for the next prompt.
So the Stop hook speaks only to catch a crossing that happened INSIDE a turn: 80 or more at the
turn's end, no RESTART line said yet in this session, `stop_hook_active` not set. At most once
per session, so it can never loop. A scheduled run (its prompt opens `<scheduled-task`) and a
subagent (`agent_id`) hear nothing.

FAILURE IS SILENCE. No stdin, no transcript, malformed JSON, an unreadable state dir: exit 0,
print nothing, one line in <state-dir>/context-restart.log. A hook must never break a session.

WRITES, BY VERB. --hook and --read write their state dir and nothing else (sessions/<id>.json and
the log); --read with no --state-dir writes nothing. --install-hooks / --uninstall-hooks write the
vendor's settings file after backing it up into the state dir; --dry and --check write nothing
at all. A transcript is only ever read, and only its tail.

Stdlib only; --hook imports json, os and sys and nothing else. OS-neutral: `python3` on macOS,
`python` on Windows — never `pythonw`, which has no stdout, and a hook that cannot print
delivers nothing.
"""

import json
import os
import sys

sys.dont_write_bytecode = True

TOOL_VERSION = "0.1"

# ── bounds: every read in this file has one ───────────────────────────────
STDIN_CAP = 1 << 20              # 1 MB
TAIL_CAPS = (262144, 4 << 20)    # 256 KB of tail; 4 MB only when 256 KB holds no reply
SETTINGS_CAP = 4 << 20
STATE_CAP = 65536
LOG_CAP = 1 << 20                # the log rotates at 1 MB
HOOK_ENTRY_TIMEOUT = 5           # seconds, on every hook entry this tool installs

WARN_AT, RESTART_AT = 70, 80
ASSUMED_WINDOWS = (200000, 1000000)    # the windows a model can have, smallest first
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
UNATTENDED_MARK = "<scheduled-task"
LAW = "the Context-restart law"
LOG_NAME = "context-restart.log"
STATE_HOME = (".exocortex", "context-restart")

PRIVATE_DIR = 0o700
PRIVATE_FILE = 0o600

# The two events this hook answers, each with the doc line it stands on.
HOOK_EVENTS = {
    "claude": {
        "UserPromptSubmit": {
            "doc": 'code.claude.com/docs/en/hooks#userpromptsubmit — additionalContext is added '
                   'alongside the submitted prompt: the line reaches the window at once'},
        "Stop": {
            "doc": 'code.claude.com/docs/en/hooks#stop — additionalContext is "non-error '
                   'feedback that continues the conversation"; `stop_hook_active` is true "when '
                   'Claude Code is already continuing as a result of a stop hook" — so this hook '
                   'speaks at Stop only for a crossing inside a turn, once per session'},
    },
    "codex": {},
}

CODEX_OFF_NOTE = (
    "codex: the context hook is OFF until a probe proves that a Codex hook fires in the desktop "
    "app and that its added line reaches the model — nothing proposed for it")


# ══════════════════════════════════════════════════════════════════════════
# small rails — json/os/sys only, so the hot path pays for nothing else
# ══════════════════════════════════════════════════════════════════════════

def read_text(path, cap):
    try:
        with open(path, "rb") as fh:
            raw = fh.read(cap)
    except (OSError, ValueError):
        return ""
    return raw.decode("utf-8", "replace")


def read_json(path, default, cap=STATE_CAP):
    text = read_text(path, cap)
    if not text.strip():
        return default
    try:
        return json.loads(text)
    except ValueError:
        return default


def mkdirs(path, mode=PRIVATE_DIR):
    """Make a folder and every level this call creates, each with the mode; the folder the
    caller named is always given the mode (it is this tool's own)."""
    path = os.path.abspath(str(path))
    if not os.path.isdir(path):
        missing, probe = [], path
        while probe and not os.path.isdir(probe):
            missing.append(probe)
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        for made in reversed(missing):
            try:
                os.mkdir(made)
            except FileExistsError:
                continue
            except OSError:
                return os.path.isdir(path)
            try:
                os.chmod(made, mode)
            except OSError:
                pass
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return os.path.isdir(path)


def write_atomic(path, text, mode=PRIVATE_FILE):
    """A temp file and one os.replace, so a reader never sees half a file. An existing file
    keeps its own mode exactly — a settings file is never loosened."""
    parent = os.path.dirname(path) or "."
    if not os.path.isdir(parent):
        mkdirs(parent)
    want = mode
    try:
        want = os.stat(path).st_mode & 0o7777
    except OSError:
        pass
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, want)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        try:
            os.chmod(tmp, want)
        except OSError:
            pass
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def log_line(state_dir, text):
    """One bounded line, rotated at 1 MB. Never raises."""
    if not state_dir:
        return
    try:
        import time
        path = os.path.join(str(state_dir), LOG_NAME)
        mkdirs(os.path.dirname(path))
        try:
            if os.path.getsize(path) > LOG_CAP:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), " ".join(str(text).split())[:500]))
        try:
            os.chmod(path, PRIVATE_FILE)
        except OSError:
            pass
    except Exception:
        pass


def safe_token(value, cap=128):
    """A session id becomes a file name, so it must be a plain token."""
    text = str(value or "")
    if not text or len(text) > cap:
        return False
    ok = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    return all(ch in ok for ch in text) and ".." not in text


def home_dir(explicit=None):
    return str(explicit) if explicit else os.path.expanduser("~")


def hub_dir(explicit=None):
    """The hub folder: what --hub says, else this file's parent's parent."""
    if explicit:
        return str(explicit)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_state_dir(home=None):
    return os.path.join(home_dir(home), *STATE_HOME)


def argv_value(argv, flag):
    for index, item in enumerate(argv):
        if item == flag and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(flag + "="):
            return item.split("=", 1)[1]
    return ""


def tokens_word(n):
    """200000 → 200k · 1000000 → 1M."""
    if n >= 1000000 and n % 1000000 == 0:
        return "%dM" % (n // 1000000)
    if n >= 1000 and n % 1000 == 0:
        return "%dk" % (n // 1000)
    return str(n)


class Unreadable(Exception):
    """The transcript cannot be read as a transcript. Logged once, never printed."""


# ══════════════════════════════════════════════════════════════════════════
# the reading — the transcript's tail, never the whole file
# ══════════════════════════════════════════════════════════════════════════

def tail_lines(path, cap):
    """(raw lines of the last `cap` bytes, whether the file is longer than that). The window's
    first line is almost always half a record and is dropped when the file was cut."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > cap:
                fh.seek(size - cap)
            raw = fh.read(cap)
    except (OSError, ValueError) as exc:
        raise Unreadable("the transcript cannot be read (%s)" % type(exc).__name__)
    lines = raw.split(b"\n")
    cut = size > cap
    if cut and lines:
        lines = lines[1:]
    return lines, cut


def window_in_record(rec, session):
    """(contextWindow, timestamp) from a get_usage result this record carries, or None. Only
    the window's OWN context counts: a get_usage asked about another session says `session`
    with that session's id."""
    if rec.get("type") != "user":
        return None
    content = (rec.get("message") or {}).get("content")
    if not isinstance(content, list):
        return None
    found = None
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_result":
            continue
        inner = item.get("content")
        texts = []
        if isinstance(inner, str):
            texts.append(inner)
        elif isinstance(inner, list):
            texts.extend(str(x.get("text") or "") for x in inner if isinstance(x, dict))
        for text in texts:
            if "contextWindow" not in text:
                continue
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            ctx = obj.get("context") if isinstance(obj, dict) else None
            if not isinstance(ctx, dict):
                continue
            who = str(ctx.get("session") or "self")
            if who not in ("self", str(session or "")):
                continue
            try:
                window = int(ctx.get("contextWindow") or 0)
            except (TypeError, ValueError):
                continue
            if window > 0:
                found = (window, str(rec.get("timestamp") or ""))
    return found


def scan(lines, session):
    """{now, window, records, broken}: the LAST main-thread reply's usage sum and the NEWEST
    get_usage window in these lines. Only lines that can carry either are parsed."""
    out = {"now": None, "window": None, "records": 0, "broken": 0, "text": 0}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        out["text"] += 1
        if not raw.startswith(b"{"):
            continue
        out["records"] += 1
        has_usage = b'"usage"' in raw and b'"assistant"' in raw
        has_window = b"contextWindow" in raw
        if not (has_usage or has_window):
            continue
        try:
            rec = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            out["broken"] += 1
            continue
        if not isinstance(rec, dict):
            continue
        if has_usage and rec.get("type") == "assistant" and not rec.get("isSidechain"):
            message = rec.get("message") or {}
            model = str(message.get("model") or "") if isinstance(message, dict) else ""
            usage = message.get("usage") if isinstance(message, dict) else None
            if model and not model.startswith("<") and isinstance(usage, dict):
                try:
                    now = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
                except (TypeError, ValueError):
                    out["broken"] += 1
                    continue
                if now > 0:
                    out["now"] = now
        if has_window:
            got = window_in_record(rec, session)
            if got:
                out["window"] = got
    return out


def reading(path, session, state):
    """{now, window, assumed, percent} for a transcript — or None when it holds no reply usage
    yet (a fresh window: silent, and not a failure). Raises Unreadable on a file that is not a
    transcript, so the caller logs it."""
    got = None
    for cap in TAIL_CAPS:
        lines, cut = tail_lines(path, cap)
        got = scan(lines, session)
        if got["now"] is not None or not cut:
            break
    if got["now"] is None:
        if got["text"] and not got["records"]:
            raise Unreadable("no JSON record in the transcript's tail")
        if got["broken"]:
            raise Unreadable("%d record(s) in the tail do not parse, and no reply usage does"
                             % got["broken"])
        return None
    now = got["now"]
    window, assumed = 0, ""
    if got["window"]:
        window = got["window"][0]
        if state is not None and state.get("window") != window:
            state["window"], state["window_at"] = window, got["window"][1]
            state["_dirty"] = True
    elif state is not None and state.get("window"):
        try:
            window = int(state["window"])
        except (TypeError, ValueError):
            window = 0
    if window and now > window:
        window = 0                   # a window the context has outgrown is not this window's
    candidates = []
    if not window:
        candidates = [size for size in ASSUMED_WINDOWS if now <= size] or [ASSUMED_WINDOWS[-1]]
        window = candidates[0]
        assumed = tokens_word(window)
        if window != ASSUMED_WINDOWS[0]:
            assumed += " (context past %s)" % tokens_word(ASSUMED_WINDOWS[0])
    percent = (now * 100 + window // 2) // window
    return {"now": now, "window": window, "assumed": assumed, "percent": percent,
            "candidates": candidates}


def the_line(r):
    """The one line for a reading, or '' under 70 — and on an UNREAD window never an order."""
    if r["assumed"]:
        # ASSUMES: nothing about the window (see the head of this file). The percent here is of
        # the smallest window the context still fits, so the nudge starts where a 200k window
        # would be at 70; the line names every window the context could sit in.
        if r["percent"] < WARN_AT:
            return ""
        alts = " or ".join("%s (%d%%)" % (tokens_word(w), (r["now"] * 100 + w // 2) // w)
                           for w in (r.get("candidates") or [r["window"]]))
        past = (" (context past %s)" % tokens_word(ASSUMED_WINDOWS[0])
                if r["now"] > ASSUMED_WINDOWS[0] else "")
        return ("CONTEXT UNREAD — %s tokens; window assumed %s%s — call get_usage once; the hook "
                "judges from it and never orders a restart on an assumption (%s)"
                % ("{:,}".format(r["now"]), alts, past, LAW))
    tail = ""
    pct = r["percent"]
    if pct >= RESTART_AT:
        return ("RESTART NOW — context %d%% (%s of %s tokens) — write the carryover, give one line "
                "of notice, start the successor with /restart (%s)%s"
                % (pct, "{:,}".format(r["now"]), "{:,}".format(r["window"]), LAW, tail))
    if pct >= WARN_AT:
        return ("CONTEXT %d%% — plan the carryover; the restart line comes at %d (%s)%s"
                % (pct, RESTART_AT, LAW, tail))
    return ""


# ══════════════════════════════════════════════════════════════════════════
# per-session state
# ══════════════════════════════════════════════════════════════════════════

def state_file(state_dir, session):
    return os.path.join(str(state_dir), "sessions", "%s.json" % session)


def load_state(state_dir, session):
    data = read_json(state_file(state_dir, session), None) if state_dir and session else None
    if not isinstance(data, dict):
        data = {}
    data.setdefault("warned70", False)
    data.setdefault("restart_said", 0)
    data.setdefault("stop_said", False)
    data.setdefault("scheduled", False)
    data.setdefault("window", 0)
    data.setdefault("window_at", "")
    data["_dirty"] = False
    return data


def save_state(state_dir, session, state):
    if not (state_dir and session and state.get("_dirty")):
        return
    body = dict((k, v) for k, v in state.items() if not k.startswith("_"))
    path = state_file(state_dir, session)
    mkdirs(os.path.dirname(path))
    write_atomic(path, json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")


def decide(kind, r, state, stop_active=False):
    """The line this event says, '' for silence — and the state it moves.

    kind 'prompt' (UserPromptSubmit, --read): 80 and up every time; 70 to 79 once per session.
    kind 'stop': only a crossing inside a turn — 80 and up, no RESTART line said yet in this
    session, the Stop hook not already continuing — and then once, never again."""
    line = the_line(r)
    if not line:
        return ""
    if r["assumed"]:
        if kind == "stop":
            return ""                       # no crossing to catch on a guess; a Stop line costs a turn
        state["unread_said"] = int(state.get("unread_said") or 0) + 1
        state["_dirty"] = True
        return line
    if kind == "stop":
        if stop_active or state.get("scheduled") or r["percent"] < RESTART_AT:
            return ""
        if state.get("restart_said") or state.get("stop_said"):
            return ""
        state["stop_said"] = True
        state["restart_said"] = int(state.get("restart_said") or 0) + 1
        state["_dirty"] = True
        return line
    if r["percent"] >= RESTART_AT:
        state["restart_said"] = int(state.get("restart_said") or 0) + 1
        state["_dirty"] = True
        return line
    if state.get("warned70"):
        return ""
    state["warned70"] = True
    state["_dirty"] = True
    return line


# ══════════════════════════════════════════════════════════════════════════
# --hook
# ══════════════════════════════════════════════════════════════════════════

def claude_projects(home=None):
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home_dir(home), ".claude")
    return os.path.join(base, "projects")


def find_transcript(session, home=None):
    """A session's own transcript by its own id — one stat per project folder, never a read."""
    if not safe_token(session):
        return ""
    root = claude_projects(home)
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return ""
    for name in names[:2000]:
        candidate = os.path.join(root, name, "%s.jsonl" % session)
        if os.path.isfile(candidate):
            return candidate
    return ""


def hook_main(argv):
    """`--hook`: read the event's stdin, print at most one line as hook context, move the
    state. Every failure is silence and one log line."""
    state_dir = argv_value(argv, "--state-dir") or default_state_dir(argv_value(argv, "--home"))
    vendor = argv_value(argv, "--vendor") or "claude"
    try:
        raw = sys.stdin.read(STDIN_CAP)
    except Exception as exc:
        log_line(state_dir, "hook: stdin unreadable (%s)" % type(exc).__name__)
        return 0
    if not raw.strip():
        log_line(state_dir, "hook: no stdin")
        return 0
    try:
        event = json.loads(raw)
    except ValueError:
        log_line(state_dir, "hook: stdin is not JSON")
        return 0
    if not isinstance(event, dict):
        log_line(state_dir, "hook: stdin is not a JSON object")
        return 0
    if event.get("agent_id"):
        return 0                                   # inside a subagent: never
    name = str(event.get("hook_event_name") or "").strip()
    events = HOOK_EVENTS.get(vendor) or {}
    if name not in events:
        return 0
    session = str(event.get("session_id") or "").strip()
    try:
        own = safe_token(session)
        if not own:
            log_line(state_dir, "%s: a session id that is not a plain token — no state kept"
                     % name)
        state = load_state(state_dir, session if own else "")
        if name == "UserPromptSubmit":
            prompt = str(event.get("prompt") or "")
            if prompt.lstrip().startswith(UNATTENDED_MARK):
                if not state.get("scheduled"):
                    state["scheduled"] = True
                    state["_dirty"] = True
                    save_state(state_dir, session if own else "", state)
                return 0                           # a scheduled run never restarts
        transcript = str(event.get("transcript_path") or "") or \
            find_transcript(session, argv_value(argv, "--home") or None)
        if not transcript or not os.path.isfile(transcript):
            log_line(state_dir, "%s %s: no transcript" % (name, session[:36]))
            return 0
        try:
            r = reading(transcript, session, state)
        except Unreadable as exc:
            log_line(state_dir, "%s %s: %s" % (name, session[:36], exc))
            return 0
        if r is None:
            save_state(state_dir, session if own else "", state)
            return 0                               # no reply usage yet: nothing to say
        active = event.get("stop_hook_active") in (True, "true", "True", 1)
        line = decide("stop" if name == "Stop" else "prompt", r, state, stop_active=active)
        if line:
            out = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": line}}
            sys.stdout.write(json.dumps(out, ensure_ascii=True))
            sys.stdout.flush()
        save_state(state_dir, session if own else "", state)
        if line:
            log_line(state_dir, "%s %s %d%%%s" % (name, session[:36], r["percent"],
                                                  " assumed" if r["assumed"] else ""))
    except Exception as exc:
        log_line(state_dir, "%s: %r" % (name or "hook", exc))
        return 0
    return 0


# ══════════════════════════════════════════════════════════════════════════
# --read — the one-line readout for a given transcript
# ══════════════════════════════════════════════════════════════════════════

def read_main(path, state_dir="", show_all=False):
    """The line a turn's start would get, printed plain. With --state-dir the once-per-session
    rule applies and the state moves (the session id is the transcript's file name); without
    one nothing is written anywhere. --all prints the reading even under 70."""
    session = os.path.basename(str(path))
    if session.endswith(".jsonl"):
        session = session[:-6]
    own = safe_token(session)
    try:
        state = load_state(state_dir, session if own else "")
        if not os.path.isfile(path):
            log_line(state_dir, "read %s: no transcript" % path)
            return 0
        try:
            r = reading(path, session, state)
        except Unreadable as exc:
            log_line(state_dir, "read %s: %s" % (session[:36], exc))
            return 0
        if r is None:
            if show_all:
                print("context — no reply usage in %s yet" % os.path.basename(path))
            return 0
        line = decide("prompt", r, state)
        save_state(state_dir, session if own else "", state)
        if line:
            print(line)
        elif show_all:
            print("context %d%% (%s of %s tokens) · window %s" % (
                r["percent"], "{:,}".format(r["now"]), "{:,}".format(r["window"]),
                ("assumed " + r["assumed"]) if r["assumed"] else "from get_usage"))
    except Exception as exc:
        log_line(state_dir, "read: %r" % (exc,))
    return 0


# ══════════════════════════════════════════════════════════════════════════
# --install-hooks · --uninstall-hooks · --check — an attended act, per machine
# ══════════════════════════════════════════════════════════════════════════
# effort.py's road, written fresh here: back the settings file up first, keep its own mode, add
# only entries whose command is this tool's, remove only those, --dry writes nothing and prints
# the exact diff, and the command names the same CONSOLE python effort.py's own entries name.

def machine_record(home=None):
    return read_json(os.path.join(home_dir(home), "orchestrator-sync", "machine.json"),
                     {}, cap=65536)


def hooks_file(vendor, home=None, settings=None):
    if settings:
        return str(settings)
    data = machine_record(home)
    roots = (data.get("roots") or {}) if isinstance(data, dict) else {}
    if vendor == "codex":
        return os.path.join(str(roots.get("codex") or
                                os.path.join(home_dir(home), ".codex")), "hooks.json")
    return os.path.join(str(roots.get("claude") or
                            os.path.join(home_dir(home), ".claude")), "settings.json")


def brain_carries(path, home=None):
    """Does the brain carry this file? A per-machine command in a synced file would break the
    other machine, so the install refuses one by name."""
    manifest = read_json(os.path.join(home_dir(home), "orchestrator-sync",
                                      "sync-manifest.json"), None, cap=1 << 20)
    if not isinstance(manifest, dict):
        return ""
    roots = (machine_record(home).get("roots") or {})
    want = os.path.abspath(path)
    for entry in (manifest.get("entries") or []):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("mode") or "") == "report-only" or entry.get("per_machine"):
            continue
        live = entry.get("live") or {}
        root = roots.get(str(live.get("root") or ""))
        if not root:
            continue
        base = os.path.abspath(os.path.join(str(root), str(live.get("rel") or "")))
        if entry.get("kind") == "file":
            if base == want:
                return str(entry.get("repo") or entry.get("id") or "carried")
        elif want == base or want.startswith(base + os.sep):
            return str(entry.get("repo") or entry.get("id") or "carried")
    return ""


def console_python():
    py = sys.executable or ""
    if not py:
        return "python" if os.name == "nt" else "python3"
    stem = os.path.splitext(os.path.basename(py))[0].lower()
    if stem == "pythonw":
        beside = os.path.join(os.path.dirname(py), "python" + os.path.splitext(py)[1])
        return beside if os.path.isfile(beside) else "python"
    return py


def first_token(command):
    text = str(command or "").strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        return text[1:end] if end > 0 else ""
    return text.split()[0] if text.split() else ""


def sibling_python(text):
    """The interpreter effort.py's own hook entries name in this settings text, or '' — so both
    hooks run on the same python, which the machine already proved prints."""
    try:
        data = json.loads(text)
    except ValueError:
        return ""
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return ""
    for rows in hooks.values():
        for row in rows if isinstance(rows, list) else []:
            for entry in (row.get("hooks") or []) if isinstance(row, dict) else []:
                command = str(entry.get("command") or "") if isinstance(entry, dict) else ""
                if "effort.py" in command and "--hook" in command:
                    py = first_token(command)
                    stem = os.path.splitext(os.path.basename(py))[0].lower()
                    if py and stem.startswith("python") and stem != "pythonw":
                        return py
    return ""


def hook_command(hub, state_dir, vendor, python):
    return '"%s" "%s" --hook --vendor %s --state-dir "%s"' % (
        python, os.path.join(str(hub), "tools", "context-restart.py"), vendor, str(state_dir))


def is_ours(command):
    text = str(command or "")
    return "context-restart.py" in text and "--hook" in text


def detect_indent(text):
    import re
    match = re.search(r"\n(\s+)\"", text or "")
    if not match:
        return 2
    pad = match.group(1).replace("\n", "")
    return len(pad) if pad and pad[0] == " " else 2


def _ours_in(rows):
    return any(isinstance(r, dict) and any(isinstance(h, dict) and is_ours(h.get("command"))
                                           for h in (r.get("hooks") or []))
               for r in rows)


def merge_hooks(text, command, events):
    """Add beside whatever is there; another tool's entries are never reordered, rewritten or
    dropped. A second run adds nothing."""
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("the settings file is not a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("`hooks` in the settings file is not an object")
    added = []
    for event in events:
        rows = hooks.setdefault(event, [])
        if not isinstance(rows, list):
            raise ValueError("`hooks.%s` is not a list" % event)
        if _ours_in(rows):
            continue
        rows.append({"hooks": [{"type": "command", "command": command,
                                "timeout": HOOK_ENTRY_TIMEOUT}]})
        added.append(event)
    rendered = json.dumps(data, indent=detect_indent(text), ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, added


def strip_hooks(text):
    """Remove only this tool's entries; every other entry stays exactly as it is."""
    data = json.loads(text)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    removed = []
    if isinstance(hooks, dict):
        for event, rows in list(hooks.items()):
            if not isinstance(rows, list):
                continue
            keep = []
            for row in rows:
                if _ours_in([row]):
                    removed.append(event)
                else:
                    keep.append(row)
            if keep:
                hooks[event] = keep
            else:
                hooks.pop(event)
        if not hooks:
            data.pop("hooks", None)
    rendered = json.dumps(data, indent=detect_indent(text), ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, removed


def installed(path):
    """{event: command} of this tool's entries in a settings file."""
    data = read_json(path, None, cap=SETTINGS_CAP)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    out = {}
    if isinstance(hooks, dict):
        for event, rows in hooks.items():
            for row in rows if isinstance(rows, list) else []:
                for entry in (row.get("hooks") or []) if isinstance(row, dict) else []:
                    if isinstance(entry, dict) and is_ours(entry.get("command")):
                        out[event] = str(entry.get("command"))
    return out


def cmd_install(hub, state_dir, vendor, dry=False, home=None, settings=None, remove=False,
                python=None):
    """Print exactly what it would do, do only that, keep a backup, refuse a file the brain
    carries — by name."""
    import difflib
    out = []
    for name in ([vendor] if vendor else ["claude"]):
        events = sorted(HOOK_EVENTS.get(name) or {})
        path = hooks_file(name, home=home, settings=settings)
        if not events:
            out.append(CODEX_OFF_NOTE if name == "codex" else
                       "%s: no event of this vendor's is documented well enough to install — "
                       "nothing proposed for it" % name)
            continue
        carried = brain_carries(path, home)
        if carried:
            out.append("REFUSED: %s is carried by the brain as %s — a per-machine command in a "
                       "synced file would break the other machine" % (path, carried))
            continue
        text = read_text(path, SETTINGS_CAP) if os.path.isfile(path) else ""
        existed = bool(text.strip())
        if not existed:
            if remove:
                out.append("%s: no hooks file at %s — nothing to remove" % (name, path))
                continue
            text = "{}\n"
        py = python or sibling_python(text) or console_python()
        command = hook_command(hub, state_dir, name, py)
        if "pythonw" in command.lower():
            out.append("REFUSED: the python named is `pythonw`, which has no stdout — a hook "
                       "that cannot print delivers nothing")
            continue
        try:
            rendered, touched = (strip_hooks(text) if remove
                                 else merge_hooks(text, command, events))
        except Exception as exc:
            out.append("REFUSED: %s is not valid JSON (%s) — nothing written" % (path, exc))
            continue
        if not touched:
            out.append("%s: already %s in %s — nothing to write"
                       % (name, "absent" if remove else "installed", os.path.basename(path)))
            continue
        verb = "would remove" if remove else "would add"
        for event in sorted(set(touched)):
            out.append("%s %s · %s · timeout %ds" % (verb, event, command, HOOK_ENTRY_TIMEOUT))
            doc = (HOOK_EVENTS.get(name) or {}).get(event, {}).get("doc")
            if doc and not remove:
                out.append("    %s" % doc)
        if dry:
            for row in difflib.unified_diff(text.splitlines(), rendered.splitlines(),
                                            fromfile=path + " (now)",
                                            tofile=path + " (would be)", lineterm="", n=2):
                out.append("    " + row)
            out.append("--dry: nothing was written (%s)" % path)
            continue
        backup = ""
        if existed:
            import time
            backup = os.path.join(str(state_dir), "backups",
                                  "%s-%s-%s" % (name, time.strftime("%Y%m%dT%H%M%S"),
                                                os.path.basename(path)))
            mkdirs(os.path.dirname(backup))
            write_atomic(backup, text)
        write_atomic(path, rendered)
        out.append("wrote %s · backup %s" % (path, backup or "(new file)"))
    return out


def cmd_check(home=None, settings=None):
    """The hooks as installed, one line per event — or `not installed`. Exit 0 when both are
    in, 2 otherwise."""
    path = hooks_file("claude", home=home, settings=settings)
    found = installed(path)
    want = sorted(HOOK_EVENTS["claude"])
    if not found:
        print("not installed (%s)" % path)
        return 2
    for event in want:
        if event in found:
            print("%s · %s" % (event, found[event]))
        else:
            print("%s · not installed" % event)
    return 0 if all(e in found for e in want) else 2


# ══════════════════════════════════════════════════════════════════════════

def usage():
    print(__doc__.split("THE READING.")[0].rstrip())


def main(argv):
    if "--hook" in argv:                       # before anything heavier is imported
        return hook_main(argv)
    if "--read" in argv:
        path = argv_value(argv, "--read")
        if not path:
            usage()
            return 2
        return read_main(path, argv_value(argv, "--state-dir"), show_all="--all" in argv)
    home = argv_value(argv, "--home") or None
    settings = argv_value(argv, "--settings") or None
    if "--check" in argv:
        return cmd_check(home=home, settings=settings)
    install, remove = "--install-hooks" in argv, "--uninstall-hooks" in argv
    if install or remove:
        if install and remove:
            usage()
            return 2
        state_dir = argv_value(argv, "--state-dir") or default_state_dir(home)
        for line in cmd_install(hub_dir(argv_value(argv, "--hub") or None), state_dir,
                                argv_value(argv, "--vendor") or "claude", dry="--dry" in argv,
                                home=home, settings=settings, remove=remove,
                                python=argv_value(argv, "--python") or None):
            print(line)
        return 0
    usage()
    return 0 if ("--help" in argv or "-h" in argv) else 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
