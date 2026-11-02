#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pulse.py — the exocortex's heartbeat, one per machine. No model, no tokens.

Each beat: pull the brain · tally any drive that is here (tools/drive_guard.py:
a volume never seen before is inventoried, every folder protected, the hub
asked once) · sense which sessions are alive on this machine
(transcripts touched in the last LIVE_MINUTES — Claude Code transcripts, Codex rollouts AND
Grok session summaries, each record marked with its mind, whether it sits in the
hub folder, and what it is about: its title and the first and latest thing a
person typed; and what it has been used for: the last twenty turns a
person typed, read from a cursor so a beat reads only what was appended)
· write live-sessions-<machine>.json · run the usage meters
(tools/usage.py --beat: Codex's and Grok's from their stores, a Claude
session's get_usage from its transcript; off until `usage.py --install`) —
before the postman's pass, which reads them · carry the github projects
(tools/continuous_sync.py --beat: every confirmed github project
no live session holds is fetched, caught up fast-forward only and its committed
commits pushed; it reads the live file just written) · land a transfer-drive
payload that is addressed to this machine (tools/auto-land.py --beat; OFF until
the first real landing has run supervised — see the switch below) · say whether
the machines are synced (tools/sync-verdict.py --write: ONE line from the
files this beat just wrote, into sync-verdict-<machine>.json, which every surface
reads — the tree's machine roots, the wake screen, the /sync skill) · run the
semantic engine (tools/semantic-engine.py --run: reads the record, writes
issues-<machine>.json) · redraw the board and the tree (orchestrator.py) · push
what changed. A failed pull never pushes; a failed engine, landing or redraw
still does (the brain must flow); any failure makes the beat return 1.

The landing SWITCH (the hub's standing condition): the beat
lands nothing until `EXO_AUTO_LAND=1` is in the environment or `"auto_land":
true` sits in machine.json. While it is off the beat still SAYS, every beat, what
is on the drive and that the supervised first landing is owed.

The pull's report is kept verbatim in pulse-last-pull-<machine>.log beside the
hub (never synced) for the engine; a landing stopped at its rail leaves
pulse-land-<machine>.log there the same way.

    python3 tools/pulse.py                 # one beat (`python` where that is the word)
    python3 tools/pulse.py --every 5       # beat every 5 minutes until stopped
    python3 tools/pulse.py --sense         # only sense + write the live file, no sync
    python3 tools/pulse.py --install-launchd    # print the launchd plist + the two commands
    python3 tools/pulse.py --install-scheduler # print the Task Scheduler command
    python3 tools/pulse.py --help          # this text; nothing runs

Stdlib only. Roots, engine and brain from the path resolver. Never raises on a
missing piece: it says what it skipped and beats on.
"""
import io, json, os, re, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_registry import registry, machine_names, machine_os           # noqa: E402
from exo_paths import paths                                            # noqa: E402

_REG = [None]


def _reg():
    """The person's own names, read once per run."""
    if _REG[0] is None:
        _REG[0] = registry()
    return _REG[0]

LIVE_MINUTES = 10
ENGINE_TIMEOUT = 60           # the engine's own budget is 2 s warm; this is the rail, not the target
DRIVE_TIMEOUT = 60            # the drive guard's tally is milliseconds; this is the rail too
LAND_TIMEOUT = 600            # a payload of hundreds of MB hashes in seconds; this is the rail
LAND_STATUS_TIMEOUT = 60      # the switch-off report only reads PAYLOAD.json files
LAND_QUIET_SECONDS = 3600     # a timed-out landing says so once an hour, not once a beat
ROOTS_TIMEOUT = 30            # publishing this machine's own roots is a file write, not a probe
HEADS_TIMEOUT = 180           # publishing where every project stands is one git call per repo
POSTMAN_TIMEOUT = 60          # a pass reads INBOX's appended bytes and a few transcripts' tails
REPO_BEAT_TIMEOUT = 300       # the repo beat spends at most 150 s on the network; this is the rail
VERDICT_TIMEOUT = 30          # the verdict reads a few small files and every STATUS; milliseconds
# The install flags are named after WHAT they install, not after whose machine
# it is. For one release the older spellings still work: they were `--install-`
# plus a machine's own name, so they are rebuilt from the registry's machines
# and their recorded operating systems. Nothing prints them and nothing
# documents them; a registry that names no machine has no such alias at all.
INSTALL_LAUNCHD = "--install-launchd"
INSTALL_SCHEDULER = "--install-scheduler"
OS_LAUNCHD = ("macos", "darwin")
OS_SCHEDULER = ("windows", "win32", "nt")


def install_flags(kind):
    """Every spelling of one install flag: the named one, and the older
    `--install-<machine>` for each machine of that kind the registry names."""
    named = INSTALL_LAUNCHD if kind == "launchd" else INSTALL_SCHEDULER
    want = OS_LAUNCHD if kind == "launchd" else OS_SCHEDULER
    reg = _reg()
    olds = ["--install-%s" % name.lower() for name in machine_names(reg)
            if machine_os(reg, name) in want]
    return tuple([named] + olds)


def known_flags():
    return (("--every", "--sense", "--hub", "--help", "-h")
            + install_flags("launchd") + install_flags("scheduler"))


def _read_machine_json(path):
    """That file as a dict, or None when it is missing or does not parse."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def machine():
    """(this machine's name, its recorded roots) from the machine record the path
    resolver finds — ("unknown", {}) when there is none."""
    found = paths(tool_file=__file__)["machine_file"]
    d = _read_machine_json(found) if found is not None else None
    if d is None:
        return "unknown", {}
    return str(d.get("name", "")).lower() or "unknown", d.get("roots", {}) or {}


def record_here(hub):
    """This run's machine record: the hub's OWN machine.json when it has one (the gate's scratch
    identity — auto-land.py's same precedence), else the record the path resolver finds (the
    older layout's copy). The live hub folder carries no machine.json in the older layout, so a
    real beat there always reads the real one."""
    found = paths(hub=hub)["machine_file"] if hub is not None else paths(tool_file=__file__)["machine_file"]
    return (_read_machine_json(found) if found is not None else None) or {}


def brain_has_remote(brain):
    """True when the brain clone has an `origin` to pull from and push to — the
    engine's own test (sync.py's push_destination asks `git remote get-url --push
    origin`); False when it has none; None when that cannot be told here (no git,
    or not a repository), and then the engine is asked, as before."""
    if brain is None or not (Path(brain) / ".git").exists():
        return None
    code, _out = run(["git", "-C", str(brain), "remote", "get-url", "--push", "origin"],
                     timeout=30)
    if code in (124, 125):                    # the rail fired, or git would not start
        return None
    return code == 0


def engine_dirs(ask_remote=True):
    """(the sync package's folder, the brain clone, why the brain sync cannot run)
    as the path resolver finds them — a folder is None when this machine has none,
    and `why` is the plain reason whenever a pull or a push would have nothing to do
    ('' when both can run). The older layout keeps the two in one folder and its
    sync package reads that folder as the brain, so there the package's folder
    stands in for a brain the record does not name. A brain with NO REMOTE — the
    one a first install makes — is not a failure: there is simply nothing to pull
    from or push to yet. Nor is a brain folder the record names but that is
    not there yet — an install run `--only tree`, before its brain step — or
    one that is there but is not a repository yet (the engine's own push, run by
    the postman's pass, writes its mirror into the folder before any brain step
    has made it one)."""
    record = paths(tool_file=__file__)
    engine, brain = record["sync_dir"], record["brain"]
    if engine is not None and not (Path(engine) / "sync.py").exists():
        engine = None
    if brain is None and record["layout"] != "program-tree":
        brain = engine
    if record["machine_file"] is None:
        why = "no machine record was found for this machine"
    elif engine is None:
        why = "no sync package was found for this machine"
    elif brain is None:
        why = "this machine's record names no brain clone"
    elif not Path(brain).exists():
        why = "the brain folder is not there yet"
    elif not (Path(brain) / ".git").exists():
        why = "the brain folder is not a repository yet"
    elif ask_remote and brain_has_remote(brain) is False:
        why = "the brain has no remote yet"
    else:
        why = ""
    return engine, brain, why


def run(args, cwd=None, timeout=300, env=None):
    """Run a tool, bounded, and decode its output as UTF-8 whatever the console
    locale is (a Windows cp437 console must never break it).

    The rail is a TREE-kill (exo_common.run_bounded): a plain timeout kills only
    the direct child, and on Windows `git` is a launcher whose grandchild keeps
    the pipes open and can hang a run for many minutes.
    124 = the timeout fired; 125 = it would not start."""
    return run_bounded(args, cwd=cwd, timeout=timeout, env=env)


def basename_any(path):
    """Last segment of a path written with EITHER separator — a Windows cwd
    ('D:\\Projects\\Thing') reaches this file's log line as often as a POSIX one."""
    parts = [p for p in re.split(r"[\\/]+", str(path or "")) if p]
    return parts[-1] if parts else ""


def under(child, parent):
    """Is `child` inside `parent`?  Either separator, case-folded — the same
    test the semantic engine uses, so `in_hub` here means what it means there."""
    if not child or not parent:
        return False
    def norm(p):
        return re.sub(r"[\\/]+", "/", str(p)).rstrip("/").lower()
    c, p = norm(child), norm(parent)
    return c == p or c.startswith(p + "/")


def _age_min(f, now):
    try:
        return (now - f.stat().st_mtime) / 60.0
    except OSError:
        return None


# The bounded transcript readers live in tools/exo_common.py so the tree page's
# collector reads a session exactly as the pulse does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_common import (read_model as _read_model, mind_of as _mind_of,      # noqa: E402
                        scan_cwd as _scan_cwd, codex_cwd as _codex_cwd,
                        run_bounded)
from grok_sessions import iter_sessions as grok_sessions
try:                    # the same credential shapes the Grok reader already blanks
    from grok_sessions import _redact as _redact_secrets
except ImportError:     # an older grok_sessions: the words ride unredacted, as before
    def _redact_secrets(text):
        return text


# --------------------------------------------------------------------------
# what a live session is ABOUT
# --------------------------------------------------------------------------
# The tree's live card and its LIVE strip lead with the session's SUBJECT: the
# name the app shows for it, the first thing the person asked it, and the last.
# Everything here is a BOUNDED read of the transcript the pulse is already
# looking at — the head until the first human turn, then the tail in growing
# windows — and it never raises: a transcript it cannot read gives empty words
# and the beat goes on.

SUBJECT_CHARS = 120                  # each line the page shows, at most
SUBJECT_HEAD_LINES = 4000            # the first human turn is near the top; never past this
SUBJECT_LINE_CAP = 4 * 1024 * 1024   # a longer line (a pasted image) is skipped whole, never held
SUBJECT_WINDOWS = (256 * 1024, 2 * 1024 * 1024, 8 * 1024 * 1024)
TITLE_CHARS = 200
# Words a transcript records as a user turn that no person typed. A turn that
# starts with "<" is harness text (a slash command, a system reminder, a task
# notification, Codex's environment context) and is skipped by the same rule.
NOT_A_PERSON = ("[Request interrupted", "Caveat: The messages below",
                "This session is being continued", "# AGENTS.md instructions")
# The bytes a user turn or a title record must carry (compact or spaced JSON);
# "userType" on every assistant line does not match any of them.
RECORD_TOKENS = (b'"type":"user"', b'"type": "user"', b'"role":"user"', b'"role": "user"',
                 b'"user_message"', b'"UserMessage"', b'"custom-title"')
_TAIL = [None]          # tools/tail-session.py, loaded once: module, or False when absent


def _tail_session():
    """tools/tail-session.py beside this file — its `_texts` reads the words of
    a message the way the button-up's reader does, for either vendor. None when
    it is not here (a scratch world, an older install): the subject is then
    empty, never guessed."""
    if _TAIL[0] is None:
        _TAIL[0] = False
        try:
            import importlib.util
            cand = Path(__file__).resolve().parent / "tail-session.py"
            if cand.is_file():
                spec = importlib.util.spec_from_file_location("pulse_tail_session", str(cand))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if callable(getattr(mod, "_texts", None)):
                    _TAIL[0] = mod
        except Exception:
            _TAIL[0] = False
    return _TAIL[0] or None


def _one_line(text, limit=SUBJECT_CHARS):
    """Whitespace collapsed, credentials blanked, at most `limit` characters."""
    s = " ".join(str(text or "").split())
    try:
        s = " ".join(_redact_secrets(s).split())
    except Exception:
        pass
    if len(s) > limit:
        s = s[:limit - 1].rstrip() + "\u2026"
    return s


def _human_text(rec, texts):
    """The words a PERSON typed, from one transcript record — or ''.

    Claude Code: a `user` record that is not meta (a skill's body), not a
    compact summary, and whose `origin`, where the record carries one, is the
    human's (a peer session's message and a task notification are not). A
    tool_result carries no text block, so it reads as ''. Codex: a user
    `message`, or the `user_message` / `UserMessage` event of the same turn."""
    if not isinstance(rec, dict):
        return ""
    kind, text = rec.get("type"), ""
    if kind == "user":
        if rec.get("isMeta") or rec.get("isCompactSummary") or rec.get("isVisibleInTranscriptOnly"):
            return ""
        origin = rec.get("origin")
        if isinstance(origin, dict) and origin.get("kind") not in (None, "", "human"):
            return ""
        msg = rec.get("message")
        text = texts(msg.get("content")) if isinstance(msg, dict) else ""
    elif kind == "response_item":
        p = rec.get("payload") or {}
        if not isinstance(p, dict) or p.get("type") != "message" or p.get("role") != "user":
            return ""
        text = texts(p.get("content"))
    elif kind == "event_msg":
        p = rec.get("payload") or {}
        if not isinstance(p, dict):
            return ""
        if p.get("type") == "user_message":
            text = p.get("message") or ""
        elif p.get("type") == "item_completed" and isinstance(p.get("item"), dict) \
                and p["item"].get("type") == "UserMessage":
            text = texts(p["item"].get("content"))
        else:
            return ""
    else:
        return ""
    s = " ".join(str(text or "").split())
    if not s or s.startswith("<") or s.startswith(NOT_A_PERSON):
        return ""
    return s


# A session opened through the front door starts with the door, not its
# subject: the front-door sentence, or one door word (`go`, `hi`, `hub` — any
# single word of at most 12 characters). ABOUT skips it and takes the next
# thing the person typed, because the tree should show the SUBJECT the
# session is dealing with; with nothing after it, the door stays.
FRONT_DOOR_START = "read the project status/memory first"
DOOR_WORD_CHARS = 12


def _is_door(text):
    """Is this first turn the front door rather than the session's subject?"""
    s = " ".join(str(text or "").split())
    if s.lower().startswith(FRONT_DOOR_START):
        return True
    return bool(s) and " " not in s and len(s) <= DOOR_WORD_CHARS


def _maybe_record(raw):
    """One JSON line as a dict, but only when it can be a user turn or a title —
    the substring test first, so a megabyte of tool output is never parsed."""
    if not any(token in raw for token in RECORD_TOKENS):
        return None
    try:
        rec = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None
    return rec if isinstance(rec, dict) else None


def _head_lines(f):
    """Whole lines from the top, at most SUBJECT_HEAD_LINES; a line longer than
    SUBJECT_LINE_CAP is read through in pieces and dropped."""
    try:
        fh = io.open(f, "rb")
    except OSError:
        return
    with fh:
        for _ in range(SUBJECT_HEAD_LINES):
            raw = fh.readline(SUBJECT_LINE_CAP + 1)
            if not raw:
                return
            if len(raw) > SUBJECT_LINE_CAP and not raw.endswith(b"\n"):
                while raw and not raw.endswith(b"\n"):
                    raw = fh.readline(SUBJECT_LINE_CAP + 1)
                continue
            yield raw


def _tail_lines_of(f, size, window):
    """The whole lines of the file's last `window` bytes, oldest first."""
    start = max(0, size - window)
    with io.open(f, "rb") as fh:
        fh.seek(start)
        data = fh.read(window)
    lines = data.split(b"\n")
    return lines[1:] if start > 0 else lines


def subject_of(f):
    """(first_line, last_line, title_record) for one Claude transcript or Codex
    rollout: the first and the latest turn a PERSON typed, and the newest
    `custom-title` the transcript itself records. '' for anything not found.
    A first turn that is only the front door gives way to the next one."""
    mod = _tail_session()
    if mod is None:
        return "", "", ""
    texts = mod._texts
    first = last = title = door = ""
    try:
        for raw in _head_lines(f):
            rec = _maybe_record(raw)
            if rec is None:
                continue
            if rec.get("type") == "custom-title" and rec.get("customTitle"):
                title = str(rec["customTitle"])
                continue
            said = _human_text(rec, texts)
            if said:
                if not door and _is_door(said):
                    door = said             # the first turn is the door: look past it
                    continue
                first = said
                break
        first = first or door
        size = f.stat().st_size
        tail_title = ""
        for window in SUBJECT_WINDOWS:
            for raw in reversed(_tail_lines_of(f, size, window)):
                rec = _maybe_record(raw)
                if rec is None:
                    continue
                if rec.get("type") == "custom-title" and rec.get("customTitle"):
                    tail_title = tail_title or str(rec["customTitle"])
                    continue
                said = _human_text(rec, texts)
                if said:
                    last = said
                    break
            if last or window >= size:
                break
        title = tail_title or title
    except (OSError, ValueError, UnicodeError):
        pass
    return _one_line(first), _one_line(last), _one_line(title, TITLE_CHARS)


def claude_title(f):
    """The name the app shows for a Claude Code session: `customTitle` in
    custom-title.json, in the session's own folder beside its transcript
    (<dir>/<id>/custom-title.json). '' when it has none."""
    try:
        with io.open(f.parent / f.stem / "custom-title.json", encoding="utf-8") as fh:
            d = json.loads(fh.read(64 * 1024))
        return _one_line(d.get("customTitle") if isinstance(d, dict) else "", TITLE_CHARS)
    except (OSError, ValueError):
        return ""


UUID_TAIL = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.I)


def codex_title(codex, stem):
    """Codex's own name for a thread: the newest `thread_name` its
    session_index.jsonl holds for this rollout's id, read from the file's last
    512 KB (an index grows by appending). '' when none."""
    m = UUID_TAIL.search(str(stem or ""))
    if not m:
        return ""
    want = m.group(1).lower()
    index = Path(codex) / "session_index.jsonl"
    try:
        size = index.stat().st_size
        for raw in reversed(_tail_lines_of(index, size, 512 * 1024)):
            if want.encode("ascii") not in raw.lower():
                continue
            try:
                d = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(d, dict) and str(d.get("id") or "").lower() == want and d.get("thread_name"):
                return _one_line(d["thread_name"], TITLE_CHARS)
    except (OSError, ValueError):
        pass
    return ""


# --------------------------------------------------------------------------
# what a live session has been USED FOR
# --------------------------------------------------------------------------
# The card of a live link is memory, not a snapshot: one line per turn a PERSON
# typed in that window, with its time, oldest first — the same "a PERSON typed"
# test as the subject above (_human_text), never a second one. The model's
# replies are out. A routine's run (its first turn is the harness's
# <scheduled-task …> wrapper, which no person typed) shows ONE line — its
# prompt's first line — and the run's status word read from the transcript.
#
# INCREMENTAL: a transcript is read once from the top, then only what was
# appended since the last beat. The cursor (byte offset, line count, the last
# twenty turns and the count before them) is machine-personal state under
# ~/.exocortex/pulse/ — never in the hub folder, never synced; losing it costs
# one read from the top. A file that SHRANK, or was rewritten under the cursor
# (the byte before it is no longer a line's end), is read again from the top.

TURNS_KEEP = 20                      # the turns a live file carries per session
TURN_CHARS = 500                     # one turn's words, at most (the source line holds the rest)
TURN_LINE_CAP = 4 * 1024 * 1024      # a longer line (a pasted image) is read through, never held
TURNS_STATE_VERSION = 1
TURNS_FORGET_SECONDS = 2 * 86400     # a cursor not used for two days is dropped
TWIN_SECONDS = 2.0                   # Codex records one turn twice, milliseconds apart
TURNS_STATE_ENV = "EXO_PULSE_STATE_DIR"
ROUTINE_TAG = re.compile(r"^<scheduled-task\b([^>]*)>")
ROUTINE_NAME = re.compile(r'\bname="([^"]*)"')
ROUTINE_END = "</scheduled-task>"
# The harness's own paragraph at the top of every routine run; the routine's
# prompt starts after it.
ROUTINE_PREAMBLE = "This is an automated run of a scheduled task."
ASSISTANT_TOKENS = (b'"type":"assistant"', b'"type": "assistant"')
RUN_STOPPED = ("end_turn", "stop_sequence")
TURNS_READ = {}     # the last sense()'s reads, by transcript: {"bytes", "from", "size", "full"}
TURNS_STATE_ERROR = [None]      # why the last sense could not keep its cursors, or None


def turns_state_file(name):
    """This machine's cursor file: ~/.exocortex/pulse/turns-<machine>.json, or
    the folder EXO_PULSE_STATE_DIR names. Machine-personal, like the post."""
    named = str(os.environ.get(TURNS_STATE_ENV) or "").strip()
    folder = Path(named) if named else Path.home() / ".exocortex" / "pulse"
    return folder / ("turns-%s.json" % (re.sub(r"[^A-Za-z0-9_.-]", "-", str(name or "")) or "unknown"))


def _load_turn_state(path):
    """{transcript path: cursor} — empty when there is none or it does not read."""
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return {}
    if not isinstance(d, dict) or d.get("version") != TURNS_STATE_VERSION:
        return {}
    files = d.get("files")
    return files if isinstance(files, dict) else {}


def _save_turn_state(path, files):
    """Written whole and renamed into place; a failure is said, never raised."""
    path = Path(path)
    tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with io.open(str(tmp), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"version": TURNS_STATE_VERSION, "files": files},
                                ensure_ascii=False))
        os.replace(str(tmp), str(path))
        return None
    except Exception as exc:
        try:
            tmp.unlink()
        except Exception:
            pass
        return str(exc)


def _turn_when(stamp):
    """(local ISO with its offset, epoch seconds) from a record's timestamp —
    ('', None) when it has none or it does not parse."""
    s = str(stamp or "").strip()
    if not s:
        return "", None
    s = s[:-1] + "+00:00" if s.endswith("Z") else s
    m = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(\.\d+)?(.*)$", s)
    if m:                                   # Python 3.9 reads 3 or 6 fraction digits only
        s = m.group(1) + ((m.group(2) + "000000")[:7] if m.group(2) else "") + m.group(3)
    try:
        when = datetime.fromisoformat(s)
    except ValueError:
        return "", None
    if when.tzinfo is None:
        when = when.astimezone()
    return when.astimezone().replace(microsecond=0).isoformat(), when.timestamp()


def _routine_of(rec, texts):
    """(routine name, its prompt's first line) when this record is the opening
    turn of a routine's run — the <scheduled-task …> wrapper the harness writes
    — else None. The words are the prompt's own, never a paraphrase."""
    if rec.get("type") != "user":
        return None
    msg = rec.get("message")
    text = texts(msg.get("content")) if isinstance(msg, dict) else ""
    s = str(text or "").lstrip()
    m = ROUTINE_TAG.match(s)
    if not m:
        return None
    name = ROUTINE_NAME.search(m.group(1))
    body = s[m.end():].split(ROUTINE_END, 1)[0].strip()
    if body.startswith(ROUTINE_PREAMBLE):
        body = body.split("\n\n", 1)[1] if "\n\n" in body else ""
    first = next((l.strip() for l in body.splitlines() if l.strip()), "")
    return (name.group(1) if name else ""), first


def _run_status(raw):
    """The run's status word from ONE assistant record: `finished` when its turn
    ended, `running · <tool>` while it is calling one, `running` otherwise."""
    try:
        rec = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return ""
    msg = rec.get("message") if isinstance(rec, dict) else None
    if not isinstance(msg, dict):
        return ""
    tools = [b.get("name") for b in (msg.get("content") or [])
             if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name")]
    if msg.get("stop_reason") in RUN_STOPPED and not tools:
        return "finished"
    return ("running · %s" % tools[-1]) if tools else "running"


def _twin(prev, said, fam, epoch):
    """Is this turn the one just kept, recorded a second time? Codex writes every
    turn as a response_item AND an event, milliseconds apart; one of the two may
    carry an attachment's tag after the words. Never true for Claude."""
    if not prev or fam == "claude" or prev.get("fam") in (None, "claude", fam):
        return False
    if epoch is None or prev.get("ts") is None or abs(epoch - prev["ts"]) > TWIN_SECONDS:
        return False
    a, b = said[:TURN_CHARS], str(prev.get("text") or "")
    return a.startswith(b) or b.startswith(a)


def _fresh_cursor():
    return {"off": 0, "lines": 0, "size": 0, "n": 0, "turns": [], "routine": None,
            "run_status": "", "tail": None, "seen": 0}


def turns_of(f, prev=None):
    """(cursor, bytes read, read from the top?) for one transcript. The cursor
    carries the last TURNS_KEEP turns ({t, words, line}), `n` — every turn so
    far — and, for a routine's run, its name and status. Only the bytes
    appended since `prev` are read; a file shorter than the cursor, or one whose
    byte just before the cursor is no longer a line's end (it was rewritten),
    is read from the top. A line still being written (no newline yet) waits for
    the next beat. Never raises: a file it cannot read keeps the cursor it had."""
    mod = _tail_session()
    try:
        size = f.stat().st_size
    except OSError:
        return (prev or _fresh_cursor()), 0, False
    ok = isinstance(prev, dict) and isinstance(prev.get("turns"), list) \
        and isinstance(prev.get("off"), int) and 0 <= prev["off"] <= size
    if ok and prev["off"] > 0:          # the cursor always sits just after a newline
        try:
            with io.open(f, "rb") as fh:
                fh.seek(prev["off"] - 1)
                ok = fh.read(1) == b"\n"
        except OSError:
            ok = False
    cur = dict(prev, turns=list(prev["turns"])) if ok else _fresh_cursor()
    full = not ok
    cur["seen"] = time.time()
    if mod is None or (not full and cur["off"] == size):
        return cur, 0, full
    texts, start, got = mod._texts, cur["off"], 0
    last_assistant = None
    try:
        with io.open(f, "rb") as fh:
            fh.seek(start)
            pos = start
            while True:
                raw = fh.readline(TURN_LINE_CAP + 1)
                if not raw:
                    break
                got += len(raw)
                if not raw.endswith(b"\n"):
                    if len(raw) <= TURN_LINE_CAP:
                        break                       # still being written: next beat
                    ended = False                   # a giant line (a pasted image):
                    while True:                     # read through it, hold nothing
                        more = fh.readline(TURN_LINE_CAP + 1)
                        got += len(more)
                        if not more:
                            break
                        if more.endswith(b"\n"):
                            ended = True
                            break
                    if not ended:
                        break                       # its end is not written yet: next beat
                    pos = fh.tell()
                    cur["lines"] += 1
                    continue
                pos += len(raw)
                cur["lines"] += 1
                if cur["routine"] is not None and any(t in raw for t in ASSISTANT_TOKENS):
                    last_assistant = raw
                rec = _maybe_record(raw)
                if rec is None:
                    continue
                said = _human_text(rec, texts)
                if not said:
                    if cur["n"] == 0 and cur["routine"] is None:
                        found = _routine_of(rec, texts)
                        if found is not None:
                            iso_t, epoch = _turn_when(rec.get("timestamp"))
                            cur["routine"] = found[0]
                            cur["turns"].append({"t": iso_t, "words": _one_line(found[1], TURN_CHARS),
                                                 "line": cur["lines"]})
                            cur["n"] = 1
                            cur["run_status"] = "running"
                    continue
                iso_t, epoch = _turn_when(rec.get("timestamp"))
                kind = rec.get("type")
                fam = "codex-item" if kind == "response_item" else ("codex-event" if kind == "event_msg" else "claude")
                if _twin(cur.get("tail"), said, fam, epoch):
                    shorter = _one_line(said, TURN_CHARS)
                    if cur["turns"] and len(shorter) < len(cur["turns"][-1]["words"]):
                        cur["turns"][-1]["words"] = shorter     # the words without the tag
                    cur["tail"] = dict(cur["tail"], fam="twinned")
                    continue
                cur["turns"].append({"t": iso_t, "words": _one_line(said, TURN_CHARS), "line": cur["lines"]})
                cur["n"] += 1
                if len(cur["turns"]) > TURNS_KEEP:
                    del cur["turns"][:-TURNS_KEEP]
                cur["tail"] = {"ts": epoch, "fam": fam, "text": said[:TURN_CHARS]}
            cur["off"] = pos
    except (OSError, ValueError, UnicodeError):
        return (prev if ok else _fresh_cursor()), got, full
    cur["size"] = size
    if last_assistant is not None:
        cur["run_status"] = _run_status(last_assistant) or cur["run_status"]
    return cur, got, full


def turns_log_line():
    """One beat-log line: what the last sense read to keep the turns, and from where."""
    reads = list(TURNS_READ.values())
    total = sum(r["bytes"] for r in reads)
    tops = sum(1 for r in reads if r["full"])
    line = "  turns: read %d bytes from %d transcript%s (%d from the top)" % (
        total, len(reads), "" if len(reads) == 1 else "s", tops)
    if TURNS_STATE_ERROR[0]:
        line += " · cursors not kept — %s" % TURNS_STATE_ERROR[0]
    return line


def turns_fields(f, cur):
    """What a live-sessions row carries of a cursor: `turns` (the last twenty:
    {t, words, line}), `earlier` (how many came before them) when there are
    any, `transcript` (the file a bullet's line number is in), and for a
    routine's run `routine` (its name) and `run_status`."""
    turns = [{"t": x.get("t") or "", "words": x.get("words") or "", "line": x.get("line") or 0}
             for x in (cur.get("turns") or [])[-TURNS_KEEP:]]
    out = {"turns": turns, "transcript": str(f)}
    earlier = int(cur.get("n") or 0) - len(turns)
    if earlier > 0:
        out["earlier"] = earlier
    if cur.get("routine") is not None:
        out["routine"] = cur["routine"]
        out["run_status"] = cur.get("run_status") or "running"
    return out



def offload_rows(rows, hub, now):
    """Fold local offload records into the existing pulse rows, one job once.
    The synced row carries metadata only. Full show text stays beside the
    machine-local run, reached by its local file link; no brief file is synced.
    """
    try:
        import offload
    except ImportError:
        return rows                 # no offload.py beside the pulse: no job rows, the beat goes on
    for job in offload.records():
        state = job.get("state")
        ended = offload.epoch(job.get("ended"))
        if state != "running" and not (state in offload.TERMINAL and ended and 0 <= now - ended < 600):
            continue
        matches = []
        for r in rows:
            if r.get("kind") != "codex" or r.get("title"):
                continue
            if job.get("thread_id"):
                if str(r.get("id", "")).endswith(job["thread_id"]):
                    matches.append(r)
            elif str(r.get("cwd")) == job.get("cwd"):
                try:
                    with open(r.get("transcript", ""), encoding="utf-8") as f:
                        first = json.loads(f.readline())
                        meta = first.get("payload") or {}
                    began = offload.epoch(meta.get("timestamp") or first.get("timestamp"))
                    if meta.get("source") == "exec" and int(began // 60) == int(offload.epoch(job["started"]) // 60):
                        matches.append(r)
                except (OSError, ValueError):
                    pass
        # A cwd-only match is used only when unique; never swallow a neighbour.
        if job.get("thread_id") or len(matches) == 1:
            for match in matches:
                rows.remove(match)
        minutes = max(0, ((now if state == "running" else ended) - offload.epoch(job["started"])) / 60)
        show_file = offload.run_folder(job) / "show.txt"
        show_file.parent.mkdir(parents=True, exist_ok=True)
        show_file.write_text(offload.show_text(job) + "\n", encoding="utf-8")
        row = {"kind": "job", "id": job["id"], "run_id": job["id"],
               "mind": job["mind"], "model": job["model"], "title": job["title"],
               "lane": job["lane"], "minutes": round(minutes, 1), "last_step": offload.short_step(job.get("last_step", "")),
               "state": state, "ended": job.get("ended"), "started": job["started"],
               "log": job["log"], "report": job["report"],
               "cwd": job["cwd"], "in_hub": under(job["cwd"], hub),
               "minutes_ago": 0 if state == "running" else round((now - ended) / 60, 1),
               "first_line": job["title"], "last_line": offload.short_step(job.get("last_step", "")),
               "record": str(offload.record_path(job["id"])),
               "show": str(show_file), "show_uri": show_file.as_uri()}
        rows.append(row)
    return rows


def sense(name, roots, hub):
    """Live sessions on this machine, from transcripts on disk (a real byte):
    Claude Code transcripts (~/.claude/projects/<dir>/*.jsonl) and Codex
    rollouts (<codex>/sessions/**/rollout-*.jsonl), each record marked with the
    mind it belongs to and `in_hub` (its cwd under this machine's hub folder),
    so the other machine needs no root inference.

    Each record also says what the session is ABOUT: `title` (the
    name the app shows for it, '' when it has none), `first_line` and
    `last_line` (the first and the latest turn a person typed, one line of at
    most 120 characters each). A Grok row keeps its summary's own title; its
    turns stay on this machine, as the Grok reader's rule has it, so its two
    lines are ''.

    And what it has been USED FOR: `turns`, the last twenty turns a
    person typed ({t, words, line}), `earlier` when more came before them,
    `transcript` (the file the line numbers are in), and — for a routine's run
    — `routine` and `run_status`. Read incrementally from this machine's cursor
    file (turns_state_file); TURNS_READ says what each read cost."""
    now = time.time(); out = []
    state_file = turns_state_file(name)
    cursors = _load_turn_state(state_file)
    TURNS_READ.clear()

    def history(f):
        key = str(f)
        prev = cursors.get(key)
        start = prev.get("off") if isinstance(prev, dict) and isinstance(prev.get("off"), int) else 0
        cur, got, full = turns_of(f, prev)
        cursors[key] = cur
        TURNS_READ[key] = {"bytes": got, "from": 0 if full else start,
                           "size": cur.get("size") or 0, "full": full}
        return turns_fields(f, cur)

    claude = Path(roots.get("claude") or (Path.home() / ".claude"))
    try:
        for d in (claude / "projects").iterdir():
            if not d.is_dir():
                continue
            for f in d.glob("*.jsonl"):
                age_min = _age_min(f, now)
                if age_min is None or age_min > LIVE_MINUTES:
                    continue
                model = _read_model(f)
                cwd = _scan_cwd(f)
                first, last, said_title = subject_of(f)
                row = {"id": f.stem, "dir": d.name, "kind": "claude",
                       "mind": _mind_of("claude", model), "model": model,
                       "cwd": cwd, "in_hub": under(cwd, hub),
                       "title": claude_title(f) or said_title,
                       "first_line": first, "last_line": last,
                       "minutes_ago": round(age_min, 1)}
                row.update(history(f))
                out.append(row)
    except OSError:
        pass
    codex = Path(roots.get("codex") or (Path.home() / ".codex"))   # no "codex" root yet
    try:
        for f in (codex / "sessions").rglob("rollout-*.jsonl"):
            age_min = _age_min(f, now)
            if age_min is None or age_min > LIVE_MINUTES:
                continue
            try:
                where = f.parent.relative_to(codex).as_posix()
            except ValueError:
                where = f.parent.name
            model = _read_model(f)
            cwd = _codex_cwd(f)
            first, last, _said = subject_of(f)
            row = {"id": f.stem, "dir": where, "kind": "codex",
                   "mind": _mind_of("codex", model), "model": model,
                   "cwd": cwd, "in_hub": under(cwd, hub),
                   "title": codex_title(codex, f.stem),
                   "first_line": first, "last_line": last,
                   "minutes_ago": round(age_min, 1)}
            row.update(history(f))
            out.append(row)
    except OSError:
        pass
    # Grok summaries are metadata; its account files and transcript bodies stay local.
    grok_root = Path(roots.get("grok") or (Path.home() / ".grok"))
    for item in grok_sessions(grok_root):
        if item.get("is_subagent"):
            continue
        updated = item.get("updated_epoch") or 0
        age_min = max(0, (now - updated) / 60.0)
        if not updated or age_min > LIVE_MINUTES:
            continue
        cwd = item["cwd"]
        row = {"id": item["id"], "dir": Path(item["path"]).parent.parent.name,
               "kind": "grok", "mind": "GROK", "model": item["model"],
               "cwd": cwd, "in_hub": under(cwd, hub),
               "title": item["title"], "status": item["status"],
               "first_line": "", "last_line": "",
               "minutes_ago": round(age_min, 1)}
        # The session's own reasoning dial where the record names one,
        # so the tree's hover reads the real Grok dial instead of guessing at it.
        # No dial in the summary, no key on the row.
        if item.get("effort"):
            row["effort"] = item["effort"]
        out.append(row)
    out = offload_rows(out, hub, now)
    out.sort(key=lambda s: s["minutes_ago"])
    # the cursors of files seen in the last two days stay; the rest are dropped
    keep = dict((k, v) for k, v in cursors.items()
                if isinstance(v, dict) and now - float(v.get("seen") or 0) < TURNS_FORGET_SECONDS)
    TURNS_STATE_ERROR[0] = _save_turn_state(state_file, keep)
    payload = {"machine": name, "when": datetime.now().astimezone().replace(microsecond=0).isoformat(),
               "live_minutes": LIVE_MINUTES, "sessions": out}
    beat = _postman_beat(hub)
    if beat:
        payload["postman"] = beat
    io.open(hub / ("live-sessions-%s.json" % name), "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    return out


def _postman_beat(hub):
    """This machine's postman heartbeat, copied into a file the pulse already
    writes every beat. The heartbeat itself is machine-personal and
    never syncs; this copy is how the OTHER machine learns that a pass has stopped
    — at ZERO extra brain commits, because live-sessions-<machine>.json crosses
    every beat anyway. Fail-safe: no postman here simply means no key."""
    try:
        pm = _load_postman(hub)
        if pm is None:
            return None
        d = json.loads(io.open(Path(pm.post_dir()) / "heartbeat.json", encoding="utf-8").read())
        return {"last_pass": d.get("when"), "every": d.get("every")}
    except Exception:
        return None


def _load_postman(hub):
    """postman.py beside this file, else in the hub's tools/ — or None."""
    try:
        import importlib.util
        for cand in (Path(__file__).resolve().parent / "postman.py",
                     Path(hub) / "tools" / "postman.py"):
            if not cand.is_file():
                continue
            spec = importlib.util.spec_from_file_location("pulse_postman", str(cand))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _tail_lines(out, n=3):
    """The last few non-empty lines of a failed step's output, for the log."""
    return [l.strip() for l in out.splitlines() if l.strip()][-n:]


def _flag_lines(out):
    """sync.py's flag HEADERS and the indented file names under them — a
    deletion or a conflict names files, and those names must never be lost:

        !! 2 CONFLICT(S) skipped — nothing was overwritten:
             <file>
        !  1 deletion(s) need your call (nothing was deleted):
             <file> (kind)
    """
    keep, under_ = [], False
    for l in out.splitlines():
        s = l.strip()
        if not s:
            continue
        if s.startswith("!"):
            keep.append(s); under_ = True
        elif under_ and l.startswith("     "):
            keep.append("  " + s)          # its detail, kept under its header
        else:
            under_ = False
    return keep


def _keep_pull_report(hub, name, out):
    """The pull's stdout, verbatim, for the engine's B3 class;
    *.log never syncs. A failure to write it is said, never raised."""
    try:
        io.open(hub / ("pulse-last-pull-%s.log" % name), "w", encoding="utf-8").write(
            "pulse pull %s · %s\n%s\n" % (name, datetime.now().astimezone().replace(microsecond=0).isoformat(), out))
        return None
    except OSError as exc:
        return str(exc)


ENGINE_SUMMARY = re.compile(r"\d+ fixed · \d+ proposed · \d+ loud")


def _engine(py, hub):
    """One engine run between sense and redraw. Returns (ok, one log line):
    the engine's own summary line when it printed one, else its tail."""
    engine = hub / "tools" / "semantic-engine.py"
    if not engine.exists():
        return True, "engine: not present here — skipped"
    env = dict(os.environ, PYTHONUTF8="1")
    t0 = time.time()
    code, out = run([py, str(engine), "--run"], cwd=hub, timeout=ENGINE_TIMEOUT, env=env)
    secs = time.time() - t0
    summary = [l.strip() for l in out.splitlines() if ENGINE_SUMMARY.search(l)]
    if code == 0:
        # no summary line = the engine said something else (a lock held by another
        # run, a source missing): surface its own last line, never a bare "ok"
        said = summary[-1] if summary else (_tail_lines(out, 1) or ["ok"])[-1]
        return True, "engine: %s · %.1f s" % (said, secs)
    return False, "engine: failed (%s) · %.1f s — %s" % (code, secs, " | ".join(_tail_lines(out)))


def _drive_tally(py, hub, env=None):
    """The drive guard's tally, once a beat, right after the pull: a volume this machine
    has never seen is inventoried, every top-level folder protected, and the hub asked ONCE which
    are not sacred. Fail-safe like the engine step — a missing tool, a non-zero exit or a broken
    probe is ONE log line and the beat goes on. Returns the lines to add to the beat's log:
    usually none, because a tally with nothing new to say says nothing."""
    tool = hub / "tools" / "drive_guard.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    base = dict(env or os.environ)
    args = [py, str(tool), "--tally", "--hub", str(hub)]
    named = base.get("DRIVE_GUARD_VOLUMES_JSON", "").strip()      # the gate's seam, passed through
    if named:
        args += ["--volumes-json", named]
    code, out = run(args, cwd=hub, timeout=DRIVE_TIMEOUT, env=dict(base, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  drive guard: failed (%s)%s" % (code, (" — " + " | ".join(said[-2:])) if said else "")]
    return ["  " + l for l in said]


def _publish_roots(py, hub):
    """This machine's own roots, declared for the OTHER machine to read: where its
    projects and transfer-staging roots are, how it spells python, which shell its landing sheets must be
    written in. Cheap and idempotent — a beat that changes nothing rewrites nothing, so the brain
    carries no churn. Fail-safe like the engine and the tally: a missing tool, a non-zero exit or
    a broken record is ONE log line and the beat goes on."""
    tool = Path(hub) / "tools" / "publish-roots.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    code, out = run([py, str(tool), "--hub", str(hub)], cwd=hub, timeout=ROOTS_TIMEOUT,
                    env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  roots: not published (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  roots: " + l for l in said if " stands: " not in l]


def _publish_heads(py, hub):
    """Where every project of this machine stands, declared for the OTHER machine to read
    — its branch, its HEAD and whether its tracked tree is clean. The button-up on the other
    side reads it instead of inferring what this machine holds — an inference that cannot see
    hand-cut payloads and so asks for far more than is owed. Cheap and idempotent: a beat that changes nothing rewrites nothing. Fail-safe like the
    roots: a missing tool, a non-zero exit or a broken record is ONE log line and the beat goes on."""
    tool = Path(hub) / "tools" / "publish-heads.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    code, out = run([py, str(tool), "--hub", str(hub)], cwd=hub, timeout=HEADS_TIMEOUT,
                    env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  heads: not published (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  heads: " + l for l in said if " stands: " not in l]


USAGE_TIMEOUT = 60            # a warm beat reads what was appended in milliseconds; this is the rail


def _usage(py, hub):
    """THE USAGE METERS: Codex's meter from its rollouts, Grok's accounting from
    its usage.json files, any get_usage result a Claude session left in its transcript, and
    each vendor's last 24 hours — no model, no network. OFF on a machine until
    `usage.py --install` sets its writer flag; the tool says so itself. Fail-safe like the
    roots: a missing tool, a non-zero exit or a timeout is ONE log line and the beat goes on."""
    tool = Path(hub) / "tools" / "usage.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    code, out = run([py, str(tool), "--beat", "--hub", str(hub)], cwd=hub, timeout=USAGE_TIMEOUT,
                    env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  usage: not written (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  " + l for l in said[-1:]]


def _postman(py, hub):
    """One postman pass per beat — THE FLOOR under the 60 s scheduled job:
    without the job a letter still moves within five minutes, and with it
    this call costs nothing because the pass sees nothing new. Fail-safe exactly
    like the roots and the heads: a missing tool, a non-zero exit or a rail hit is
    ONE log line and the beat goes on."""
    tool = Path(hub) / "tools" / "postman.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    code, out = run([py, str(tool), "--pass", "--quiet", "--hub", str(hub)], cwd=hub,
                    timeout=POSTMAN_TIMEOUT, env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  postman: failed (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  postman: " + l for l in said]


ROUTINES_TIMEOUT = 30          # reading one task store and raising one notice


def _routines_at_boot(py, hub):
    """The first beat after a boot asks routine-check.py whether any routine will
    ask permission and, if one will, posts ONE desktop notice naming them all — once per boot
    (its marker lives in this machine's own state folder, beside the turn cursors), silent when
    every enabled routine reads Bypass. Every later beat of the same boot costs one small file
    read. Fail-safe like the postman: a missing tool, a non-zero exit or a rail hit is ONE log
    line and the beat goes on."""
    tool = Path(hub) / "tools" / "routine-check.py"
    if not tool.exists():
        return []
    env = dict(os.environ, PYTHONUTF8="1")
    folder = str(os.environ.get(TURNS_STATE_ENV) or "").strip()
    if folder:
        env["EXO_PULSE_STATE_DIR"] = folder
    code, out = run([py, str(tool), "--boot-notice", "--quiet"], cwd=hub,
                    timeout=ROUTINES_TIMEOUT, env=env)
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  routines: failed (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  " + l for l in said]


def _cloud_inbox(py, hub, roots, live):
    """One-way notes into the house; no window starts here.

    The regular repo beat has finished. Respect its live-session boundary,
    then pull ff-only, sort once, and push only after a successful sort.
    run() kills the process tree at the existing engine's timeout rail.
    """
    projects = roots.get("projects")
    if not projects:
        return False, ["  inbox: projects root is missing from the machine record"]
    inbox = Path(projects) / "exo-inbox"
    if not inbox.exists():
        return True, []
    if inbox.is_symlink():
        return False, ["  inbox: symlink refused"]
    for session in live:
        cwd = session.get("cwd") or session.get("dir")
        if cwd:
            try:
                Path(cwd).resolve().relative_to(inbox.resolve())
                return True, []                 # a live writer keeps its repo
            except (ValueError, OSError):
                pass
    tool = Path(hub) / "tools" / "inbox-sort.py"
    if not tool.is_file():
        return False, ["  inbox: sorter is not installed"]
    try:
        row = json.loads((Path(hub) / "carry" / "projects.json").read_text(
            encoding="utf-8")).get("exo-inbox", {})
        if row.get("carrier") != "github" or row.get("confirmed") is not True:
            return False, ["  inbox: its GitHub carrier is not confirmed"]
    except (OSError, ValueError):
        return False, ["  inbox: project registry could not be read"]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1")
    lines = []
    steps = [
        ("pull", ["git", "-C", str(inbox), "pull", "--ff-only"], 30),
        ("sort", [py, str(tool), "--inbox", str(inbox), "--once"], 120),
        ("push", ["git", "-C", str(inbox), "push"], 30),
    ]
    for verb, args, timeout in steps:
        code, out = run(args, cwd=hub, timeout=timeout, env=env)
        said = [line.strip() for line in (out or "").splitlines() if line.strip()]
        if verb == "sort":
            lines.extend("  " + line for line in said)
        if code:
            detail = (" — " + said[-1]) if said and verb != "sort" else ""
            lines.append("  inbox: %s failed (%s)%s; next beat retries" % (verb, code, detail))
            return False, lines
    return True, lines


def _repo_beat(py, hub):
    """The continuous sync's GitHub half, once a beat: every confirmed github
    project that no live session holds is fetched, caught up fast-forward only, and its
    already-committed commits pushed — never a commit, never a merge, never a force. The tool reads
    the live file this beat's sense() has just written, so it runs AFTER sense. Fail-safe like the
    postman: a missing tool is silence, a rail hit or a crash is ONE line and the beat goes on.
    Returns (ok, lines): ok is False when a repo errored or the tool did not finish."""
    tool = Path(hub) / "tools" / "continuous_sync.py"
    if not tool.exists():
        return True, []                             # not installed here — nothing to say
    code, out = run([py, str(tool), "--beat", "--hub", str(hub)], cwd=hub,
                    timeout=REPO_BEAT_TIMEOUT, env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.rstrip() for l in (out or "").splitlines() if l.strip()]
    if code == 124:
        return False, ["  repos: stopped at the %d s rail (the whole process tree) — the next beat "
                       "reads every repo again" % REPO_BEAT_TIMEOUT]
    if code not in (0, 1):
        return False, ["  repos: failed (%s)%s" % (code, (" — " + said[-1].strip()) if said else "")]
    return code == 0, ["  " + l for l in said]


PAYLOAD_ID_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-TX-[A-Za-z0-9-]+")


def _land_switch(hub):
    """Is auto-landing ON here?  OFF is the shipped state: the hub's standing condition is that
    the FIRST real landing runs with a session watching. Two ways to turn it
    on, both from the record: `EXO_AUTO_LAND=1` in the environment (one run, the gate's way) or
    `"auto_land": true` in machine.json (this machine, from the supervised landing on)."""
    if str(os.environ.get("EXO_AUTO_LAND", "")).strip().lower() in ("1", "true", "yes", "on"):
        return True, "EXO_AUTO_LAND"
    if record_here(hub).get("auto_land") is True:
        return True, "machine.json"
    return False, ""


def _land_letter(py, hub, name, text, action):
    """ONE letter to THIS machine's hub, through the hub's own tools/mail.py — the landing tool's
    own form and address. The pulse writes no INBOX line of its own; this is the letter a landing
    that was KILLED at the rail could not send for itself, and without it a timeout would be
    silent (own the outcome). True when it went out."""
    mailpy = Path(hub) / "tools" / "mail.py"
    if not mailpy.is_file():
        return False
    code, out = run([py, str(mailpy), "--send", "%s/hub" % str(name).upper(), "Exocortex",
                     text, action, "--no-push", "--inbox", str(Path(hub) / "INBOX.md")],
                    cwd=hub, timeout=120)
    return code == 0


def _land_timeout(py, hub, name, out):
    """A landing that ran past its rail was stopped, tree and all. Say it plainly, ONCE an hour:
    the marker is a *.log beside the pull's own report, which the brain never syncs."""
    said = PAYLOAD_ID_RE.findall(out or "")
    which = said[-1] if said else "a payload"
    mark = Path(hub) / ("pulse-land-%s.log" % name)
    try:
        quiet = (time.time() - mark.stat().st_mtime) < LAND_QUIET_SECONDS
    except OSError:
        quiet = False
    line = ("land: timed out after %d s — the landing of %s was stopped (the whole process tree); "
            "nothing more was written" % (LAND_TIMEOUT, which))
    if not quiet:
        sent = _land_letter(
            py, hub, name,
            "AUTO-LAND STOP · %s · the landing ran past its %d s rail on the %s and was stopped "
            "(the whole process tree) · nothing more was written" % (which, LAND_TIMEOUT, str(name).upper()),
            "read %s, then run `%s tools/auto-land.py --check %s` in the hub folder by hand — a "
            "landing this long means a very large payload or a hung git"
            % (mark.name, os.path.basename(sys.executable or "python3"), which))
        try:
            io.open(mark, "w", encoding="utf-8").write(
                "%s %s\n%s\n" % (datetime.now().astimezone().replace(microsecond=0).isoformat(),
                                   line, (out or "")[-4000:]))
        except OSError:
            pass
        line += " · letter sent" if sent else " · the letter could not be sent — tell the hub by hand"
    else:
        line += " · said within the hour already"
    return line


def _sync_verdict(py, hub):
    """THE ONE-LINE SYNC VERDICT, once a beat, after the landing and before the page is
    drawn: tools/sync-verdict.py reads the files this beat has just written (the heads, the pull's
    report, the ledger, the registry) and writes sync-verdict-<machine>.json — the one copy every
    surface reads, so the tree's machine root, the wake screen and the /sync skill say the same
    line and none of them recomputes it. It runs no git and opens no connection. Fail-safe like
    the postman: a missing tool is silence, a crash or a rail hit is ONE line and the beat goes
    on. Returns the lines to add to the beat's log: the verdict itself, which is the point."""
    tool = Path(hub) / "tools" / "sync-verdict.py"
    if not tool.exists():
        return []                                   # not installed here — nothing to say
    code, out = run([py, str(tool), "--write", "--hub", str(hub)], cwd=hub,
                    timeout=VERDICT_TIMEOUT, env=dict(os.environ, PYTHONUTF8="1"))
    said = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if code != 0:
        return ["  sync: not written (%s)%s" % (code, (" — " + said[-1]) if said else "")]
    return ["  sync: " + said[0]] if said else []


def _auto_land(py, hub, name):
    """One landing pass between sense and the engine. Returns (ok, one log line).

    The tool does the work (tools/auto-land.py --beat): it finds the drive by its label, lands
    only a payload sealed for THIS machine, fast-forward only, every fingerprint checked before a
    byte moves, and mails the hub its own gate line or its own STOP. This hook adds three things
    the tool cannot do for itself: the SWITCH (off until the first landing has run supervised),
    the RAIL (LAND_TIMEOUT, tree-killed) and the letter for a landing that was killed at it."""
    tool = Path(hub) / "tools" / "auto-land.py"
    if not tool.exists():
        return True, "land: not present here — skipped"
    env = dict(os.environ, PYTHONUTF8="1")
    on, _how = _land_switch(hub)
    if not on:
        code, out = run([py, str(tool), "--status", "--hub", str(hub)], cwd=hub,
                        timeout=LAND_STATUS_TIMEOUT, env=env)
        said = (_tail_lines(out, 1) or ["nothing to land"])[-1]
        return True, "land: off (supervised first landing owed) — %s" % said
    code, out = run([py, str(tool), "--beat", "--hub", str(hub)], cwd=hub,
                    timeout=LAND_TIMEOUT, env=env)
    if code == 124:
        return False, _land_timeout(py, hub, name, out)
    said = (_tail_lines(out, 1) or ["ok"])[-1]
    return code == 0, "land: %s" % said


def beat(name, roots, hub, sync_only_sense=False):
    py = sys.executable or "python3"
    sync_dir, brain, why = engine_dirs(ask_remote=not sync_only_sense)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # the date too: the log spans days, and a beat line without it reads as any day's
    lines = ["pulse %s · %s" % (name.upper(), stamp)]
    rc, pull_failed = 0, False
    if not sync_only_sense and sync_dir is not None and why:
        lines.append("  pull: skipped — %s; nothing to pull" % why)
    elif not sync_only_sense and sync_dir is not None:
        code, out = run([py, "sync.py", "pull"], cwd=sync_dir)
        flagged = [l for l in out.splitlines() if "CONFLICT" in l or "!!" in l or "differs" in l]
        lines.append("  pull: %s%s" % ("ok" if code == 0 else "failed", (" · " + " | ".join(flagged)) if flagged else ""))
        lines.extend("    %s" % l for l in _flag_lines(out))   # conflict / deletion file names
        if code != 0:
            rc, pull_failed = 1, True
            lines.extend("    %s" % l for l in _tail_lines(out))
        err = _keep_pull_report(hub, name, out)
        if err:
            lines.append("  pull report: not kept — %s" % err)
    if not sync_only_sense:
        lines.extend(_drive_tally(py, hub))     # first sight of a drive, asked once
        lines.extend(_publish_roots(py, hub))   # this machine says where its own roots are
        lines.extend(_publish_heads(py, hub))   # and where every project of its own stands
    live = sense(name, roots, hub)
    lines.append("  live sessions here: %d%s" % (len(live), (" · " + ", ".join(sorted({basename_any(s["cwd"]) or s["dir"] for s in live}))) if live else ""))
    lines.append(turns_log_line())              # what reading the windows' turns cost
    if sync_only_sense:
        print("\n".join(lines)); return 0
    lines.extend(_usage(py, hub))               # the meters, before the pass reads them
    lines.extend(_postman(py, hub))             # the mail moves before the page is drawn
    lines.extend(_routines_at_boot(py, hub))    # routines that will ask, once per boot
    ok, more = _repo_beat(py, hub)              # the github projects, level both ways
    lines.extend(more)
    if not ok:
        rc = 1                       # a repo's trouble is local: log it and beat on
    ok, more = _cloud_inbox(py, hub, roots, live)  # cloud notes arrive
    lines.extend(more)
    if not ok:
        rc = 1
    ok, line = _auto_land(py, hub, name)        # a drive payload lands before the engine reads the ledger
    lines.append("  " + line)
    if not ok:
        rc = 1                       # a failed landing is local: log it and beat on
    lines.extend(_sync_verdict(py, hub))        # one line, one file, before the page is drawn
    ok, line = _engine(py, hub)                                  # the engine reads, then the page draws what it found
    lines.append("  " + line)
    if not ok:
        rc = 1                       # the engine is local: log it and beat on
    code, out = run([py, "orchestrator.py"], cwd=hub, env=dict(os.environ, EXO_PULSE="1"))   # the flag that makes the page refresh itself
    lines.append("  redraw: %s" % ("ok" if code == 0 else "failed — " + out[-200:]))
    if code != 0:
        rc = 1                       # the redraw is local: log it and push anyway
    if pull_failed:
        lines.append("  push: skipped — the pull failed; never push over a failed pull")
        print("\n".join(lines))
        return 1
    if why:
        # THE SAME GUARD THE PULL ABOVE ALREADY HAS: the sync package and the
        # brain are where the path resolver finds them, and a machine with
        # neither — or a brain folder not made yet, or a brain with no remote
        # yet — pushes nothing. It used to raise FileNotFoundError, which an
        # installer reads as a STOP on a first install.
        lines.append("  push: skipped — %s; nothing to push from here" % why)
        print("\n".join(lines))
        return rc
    code, out = run([py, "sync.py", "push"], cwd=sync_dir)
    pushed = [l for l in out.splitlines()
              if not l.strip().startswith("!")          # a flag header gets its own line below
              and ("->" in l or "nothing" in l.lower() or "up to date" in l.lower())]
    lines.append("  push: %s%s" % ("ok" if code == 0 else "failed", (" · " + pushed[-1].strip()) if pushed else ""))
    lines.extend("    %s" % l for l in _flag_lines(out))
    if code != 0:
        rc = 1
        lines.extend("    %s" % l for l in _tail_lines(out))
    print("\n".join(lines))
    return rc


PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.exocortex.pulse</string>
  <key>ProgramArguments</key><array><string>%(py)s</string><string>%(hub)s/tools/pulse.py</string></array>
  <key>StartInterval</key><integer>%(secs)d</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>%(log)s</string>
  <key>StandardErrorPath</key><string>%(log)s</string>
</dict></plist>
"""


def usage(stream=sys.stdout):
    stream.write(__doc__)


def main(argv):
    # the help guard is a rail: --help and unknown flags never reach the beat —
    # a reader's --help must never run a pull, a redraw and a brain push.
    if "--help" in argv or "-h" in argv:
        usage(); return 0
    i = 0
    while i < len(argv):
        a = argv[i]
        if a not in known_flags():
            sys.stderr.write("pulse.py: unknown flag %r\n\n" % a); usage(sys.stderr); return 2
        i += 2 if a in ("--every", "--hub") else 1
    name, roots = machine()
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    if "--hub" in argv:
        at = argv.index("--hub")
        if at + 1 >= len(argv) or "--sense" not in argv:
            print("STOP: --hub needs a folder and --sense"); return 2
        hub = Path(argv[at + 1]).resolve()
        local = _read_machine_json(hub / "machine.json") or {}
        name = local.get("name") or local.get("machine") or name
        roots = dict(local.get("roots") or {}, orchestrator=str(hub))
    if any(flag in argv for flag in install_flags("launchd")):
        mins = 5
        log = str(Path.home() / "Library" / "Logs" / "exocortex-pulse.log")   # outside the synced hub folder
        plist = PLIST % {"py": sys.executable or "/usr/bin/python3", "hub": str(hub), "secs": mins * 60, "log": log}
        target = Path.home() / "Library" / "LaunchAgents" / "com.exocortex.pulse.plist"
        print("# 1. write the plist (every %d minutes):" % mins)
        print("cat > '%s' <<'EOF'\n%sEOF" % (target, plist))
        print("# 2. load it:\nlaunchctl unload '%s' 2>/dev/null; launchctl load '%s'" % (target, target))
        print("# 3. see it beat:\ntail -5 '%s'" % log)
        return 0
    if any(flag in argv for flag in install_flags("scheduler")):
        win = str(hub).replace("/", "\\")
        print('schtasks /Create /TN "Exocortex Pulse" /SC MINUTE /MO 5 /TR "cmd /c python \\"%s\\\\tools\\\\pulse.py\\" >> \\"%%USERPROFILE%%\\\\exocortex-pulse.log\\" 2>&1" /F' % win)
        print("# see it beat: Get-Content \"$env:USERPROFILE\\exocortex-pulse.log\" -Tail 5")
        return 0
    if "--sense" in argv:
        return beat(name, roots, hub, sync_only_sense=True)
    if "--every" in argv:
        i = argv.index("--every"); mins = float(argv[i + 1]) if i + 1 < len(argv) else 5.0
        while True:
            beat(name, roots, hub); sys.stdout.flush(); time.sleep(mins * 60)
    return beat(name, roots, hub)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
