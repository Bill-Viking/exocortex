#!/usr/bin/env python3
"""effort.py — the effort recommender.

One rubric for every mind, the dial read by the machine, and a cue at the moment
of need.  No model, no tokens: every frame is computed from facts already on
disk — the hook's own input, the transcript's tail, the rubric file, the user's
own law book.

    python3 tools/effort.py --hook --vendor claude --state-dir DIR [--hub DIR]
    python3 tools/effort.py --dial [--transcript FILE] [--session ID]
    python3 tools/effort.py --replay TRANSCRIPT [TRANSCRIPT...] --state-dir TEMP
    python3 tools/effort.py --weigh OPENER.md | --weigh --kind JUDGMENT
    python3 tools/effort.py --rubric [--check]
    python3 tools/effort.py --status
    python3 tools/effort.py --install-hooks   [--vendor claude|codex] [--dry]
    python3 tools/effort.py --uninstall-hooks [--vendor claude|codex] [--dry]

WHAT IT DOES NOT DO.  It never turns a dial (the app refuses a session its own,
and turning another's is the user's ruling). Typed prompts run with usage warnings.
Unattended frames retain PAUSE controls (including applicable signed continuation)
and flagship STOP; blocked runs end before their first model call. It never writes
to the transcript, the INBOX, a claim, a stamp or any file of the postman's, and
never asks a model anything.  The session still weighs the coming stretch; this
only holds the weighing to one standard and puts the facts in front of it.

WRITES, BY VERB. --hook also writes one bounded metadata line per prompt to
scratch/usage-diag/<machine>.jsonl (newest 500 lines only). --hook writes its state dir —
its sessions/, its log, and wake/<session>.json, the law book as that
session woke to it — except the usage block, which through tools/usage.py
files a get_usage result found in the window's own tail as the meter file, and
marks a PAUSE onset in it when it sends the one <MACHINE>/all letter (and
the one desktop notice at a PAUSE onset and at a WARN crossing, the pruned
«continue» of a window that has reset, and the said mark of its one line).
A whole typed continuation choice writes its signed settings row atomically · --dial, --replay, --weigh, --rubric, --status and every
--dry write NOTHING AT ALL ·
--install-hooks writes the vendor's settings file, after backing it up into the
state dir.  It READS, and never writes, the law file, openers, transcripts and
the rubric.

FAILURE IS SILENCE.  Any exception, a missing or torn transcript, an
unreadable state dir, a malformed rubric: exit 0, print nothing, one line in
<state-dir>/effort.log.  A cue lost that way is simply re-derived at the next
prompt, because every frame is computed from current facts and never from a
queue.

NOTHING ABOUT ONE FLEET IS TYPED IN.  Minds come from the
record through the pulse's own mapper (exo_common.mind_of) and i-am.py's
canon_mind; the minds the law forbids for judgment and the mind it names as the
floor are read out of the user's own law paragraph at run time through the
semantic engine's C8 reading; levels, their words and the thresholds come from
effort-rubric.json, which is the user's to edit.  An unknown model id gets its
vendor from the id's own prefix and is shown raw.

THE HOT PATH.  `--hook` imports json, os and sys and nothing else until it knows
it has work: the rubric and the transcript tail are read only for an event this
tool answers, the mind mapper only when a frame needs a mind, and the semantic
engine only when the window's mind is one the law flags.  Everything heavier
(argparse, the installer, the opener reader) lives behind the verbs that use it.

Stdlib only.  OS-neutral: pathlib and os.path, `python3` on macOS, `python` on
Windows — never `pythonw`, which has no stdout, and a hook that cannot print
delivers nothing.
"""

import json
import os
import sys
import hook_say

CLI_ERROR = 2  # CLI validation only; hooks emit through hook_say.

# A sibling module must never leave a __pycache__ behind in the tools folder:
# this tool is a reader of its neighbours, not a writer.
sys.dont_write_bytecode = True

TOOL_VERSION = "0.1"

# ── bounds: every read in this file has one ───────────────────────────────
STDIN_CAP = 1 << 20          # 1 MB — a pasted prompt is large; a stream is not
TAIL_BYTES = 262144          # 256 KB of transcript tail
RUBRIC_CAP = 262144
LAW_CAP = 2 << 20
OPENER_CAP = 65536
SETTINGS_CAP = 4 << 20
LOG_CAP = 1 << 20            # the log rotates at 1 MB
WALK_CAP = 64 << 20          # the biggest transcript --replay will walk (P4)
CUED_CAP = 64                # tokens remembered per session
TAIL_LINES = 15              # the plate lives in the reply's last 15 lines
PLATE_GAP = 2                # how far under the arrow line the STATION line may sit
HOOK_ENTRY_TIMEOUT = 5       # seconds, on every hook entry this tool installs
SOFT_BUDGET_S = 2.0          # past this, the hook skips its heaviest read

PRIVATE_DIR = 0o700
PRIVATE_FILE = 0o600

# The two events this phase answers, each with the doc line it stands on.  An
# event is here only with a quoted line behind it; nothing is guessed.
HOOK_EVENTS = {
    "claude": {
        "UserPromptSubmit": {
            "doc": 'code.claude.com/docs/en/hooks#userpromptsubmit — "If a hook '
                   'returns `additionalContext`, Claude Code appends it to the '
                   'prompt before sending it to Claude, so the model can use the '
                   'added information to refine its response."'},
        "SessionStart": {
            "doc": 'code.claude.com/docs/en/hooks#sessionstart — "If a hook returns '
                   '`additionalContext`, Claude Code appends it to the first '
                   'assistant message as context"; this tool prints nothing on this '
                   'event and only learns the mind from it (BQ-058 §6), and takes the '
                   'law book\'s snapshot for this session (BQ-139)'},
    },
    # Codex: OFF until its probe passes.  Not a guess, not a silence.
    "codex": {},
}

CODEX_OFF_NOTE = (
    "codex: the effort hook is OFF until a probe proves three things — that Codex "
    "hooks fire in the desktop app, what carries its dial into a hook (a rollout "
    "records `effort` in its turn_context; a hook variable is unknown), and that an "
    "added line reaches the model. The rubric and --weigh are plain files and a plain "
    "command, so a Codex session uses them from its ONBOARD ritual today (BQ-058 §10).")

# Vendor families, for the dials table and for an unknown model id's prefix.
VENDOR_FAMILY = {"claude": "anthropic", "codex": "openai", "grok": "xai"}


# ══════════════════════════════════════════════════════════════════════════
# the seed rubric — the one table, every cell with its source
# ══════════════════════════════════════════════════════════════════════════
# THE FILE IS THE USER'S.  This is what the tool falls back to when the file is
# missing, malformed or refused, and what `effort-rubric.json` is cut from, so
# the two can never drift: the gate proves they are the same table.
SEED = {
    "version": 1,
    "about": ("The one table every mind weighs the coming work against (BQ-058 §5). "
              "Yours to edit. Cells marked in `seed` are the brief's proposal and are "
              "ruled only on the user's word (R1). JUDGMENT's signals are not in this "
              "file: they are the semantic engine's C8 verb pattern, read by import, "
              "and the minds the law forbids are read from the law paragraph at run "
              "time — a rubric may tighten the law, never loosen it. A row with a "
              "`ruled` date is one the user has ruled on: the cells named in "
              "`ruled_cells` are settled, and `seed` is what is still only proposed."),
    # Whose fleet this is: the one name a frame says out loud.  EMPTY IN THE
    # ENGINE, ALWAYS (nothing about one user's fleet is
    # written into the tool).  The shipped effort-rubric.json — the user's own
    # file, brain-synced — carries the name; the built-in seed, which is what a
    # missing or refused file falls back to, says "the user" and never a person.
    "user_name": "",
    "dials": {
        "anthropic": {"low": "LOW", "medium": "MEDIUM", "high": "HIGH",
                      "xhigh": "EXTRA", "max": "MAX"},
        "openai": {"xhigh": "EXTRA"},
        # xAI (Grok Build 1.0.40): the levels the app itself names — `/effort`
        # in the TUI offers low · medium · high · xhigh, and `--effort` /
        # `models.default_reasoning_effort` also take none · minimal · max, which
        # a session's own `reasoning_effort` can therefore report.  Grok's dial
        # says XHIGH where Anthropic's says EXTRA, so each vendor keeps its own
        # word and neither is translated into the other's.
        "xai": {"none": "NONE", "minimal": "MINIMAL", "low": "LOW",
                "medium": "MEDIUM", "high": "HIGH", "xhigh": "XHIGH",
                "max": "MAX"},
    },
    "flag_only_levels": ["max"],
    "kinds": [
        {"id": "synthesis", "name": "SYNTHESIS",
         "ask": "Must this answer be built from many sources held at once, and will "
                "others build on it? (a verdict · a cross-corpus audit · an "
                "architecture decision · a build brief · a whole prompt cut that ships)",
         "minds": ["FABLE", "ASTRA"], "mind_note": "FABLE, else ASTRA",
         "never": [], "never_law": False,
         "level": "MAX", "level_note": "",
         "flag": "flag FIRST, wait for the dial, the down plate after",
         "why": "an answer built across many sources at once, that others build on",
         "source": "law §3",
         "seed": [], "ruled": "2026-09-22",
         "ruled_cells": ["ask: a build brief", "ask: a whole prompt cut that ships"]},
        {"id": "judgment", "name": "JUDGMENT",
         "ask": "Do I still have to figure out what to do? (rule · grade · decide · "
                "design · diagnose · revise shipped text)",
         "minds": ["FABLE", "ASTRA"], "mind_note": "FABLE, else ASTRA",
         "never": ["HAIKU"], "never_law": True,
         "level": "EXTRA", "level_note": "",
         "flag": "plate only when the window differs",
         "why": "judgment steps down to the other judging mind, never to a cheaper one",
         "source": "law §2",
         "seed": [], "ruled": "2026-09-22",
         "ruled_cells": ["never: HAIKU (the rubric is tighter than the law here)"]},
        {"id": "build_that_ships", "name": "BUILD THAT SHIPS",
         "ask": "Am I about to author or edit something that ships, or that others "
                "build on?",
         "minds": [], "mind_note":
             "the judging mind states the effort check (bump · hold · step down) "
             "BEFORE the turn; a substantial build goes to a NAMED OPUS builder from a "
             "precise brief and the judging mind verifies",
         "never": [], "never_law": False,
         "level": "EXTRA",
         "level_note": "EXTRA held; MAX when this window authors the whole artifact itself",
         "flag": "the effort check, first",
         "why": "a mistake baked into a shipped artifact costs far more than the flag",
         "source": "law §3 build turns · law §1",
         "seed": []},
        {"id": "verify", "name": "VERIFY",
         "ask": "Am I checking a result against the record? (gate reruns, diff reads, "
                "adjudication)",
         "minds": [], "mind_note": "the mind that judged",
         "never": [], "never_law": False,
         "level": "", "level_note": "the standing level",
         "flag": "none unless flagged",
         "why": "verification stays at the standing level unless a turn is flagged",
         "source": "law §3",
         "seed": []},
        {"id": "mechanical", "name": "MECHANICAL",
         "ask": "Is the plan written down AND ruled — checked against the record, never "
                "assumed — and is what is left straightforward?",
         "minds": ["ASTRA", "OPUS", "SONNET"],
         "mind_note": "ASTRA by default; OPUS or SONNET",
         "never": [], "never_law": False,
         "level": "EXTRA",
         "level_note": "while the files ship, the saving comes from the cheaper MIND, "
                       "not a lower dial",
         "flag": "the down plate at the seam",
         "why": "the thinking is done; what is left is the cheaper mind's",
         "source": "law §2 session model by work kind · law §1 lanes default to Astra",
         "seed": ["level: EXTRA held while the files ship"]},
        {"id": "bookkeeping", "name": "BOOKKEEPING",
         "ask": "Is this a walk with nothing to decide and nothing that ships? (sweeps, "
                "archive walks, board refresh, renames already ruled)",
         "minds": ["SONNET"], "mind_note": "SONNET, or the cheapest mind that is up",
         "never": [], "never_law": False,
         "level": "HIGH",
         "level_note": "the law's standing default is EXTRA; this is the one step below it",
         "flag": "the down plate",
         "why": "nothing to decide and nothing that ships",
         "source": "ruled 2026-09-22",
         "seed": [], "ruled": "2026-09-22",
         "ruled_cells": ["level: HIGH", "the whole row"]},
        {"id": "bulk_read", "name": "BULK READ",
         "ask": "Is this reading, not deciding? (scans, screenshots, long documents, "
                "transcripts)",
         "minds": ["SONNET", "HAIKU"],
         "mind_note": "a NAMED reader subagent — SONNET; HAIKU for plain-text skims — "
                      "returning a digest with verbatim quotes",
         "never": [], "never_law": False,
         "level": "", "level_note": "the subagent's own (not settable per call)",
         "flag": "none; the model is named in the call",
         "why": "expensive reads belong to a cheap reader that returns a digest",
         "source": "law §1",
         "seed": []},
        {"id": "look_pass", "name": "LOOK PASS",
         "ask": "Is this the look — colour, type, aesthetics — from references?",
         "minds": ["ASTRA", "FABLE"],
         "mind_note": "ASTRA designs; FABLE specs the structure and reviews the build",
         "never": [], "never_law": False,
         "level": "EXTRA", "level_note": "",
         "flag": "",
         "why": "the expensive mind judges, the other vendor's mind styles",
         "source": "law §1 look passes go to Astra",
         "seed": []},
        {"id": "routine", "name": "ROUTINE",
         "ask": "Is this unattended, on a schedule?",
         "minds": ["SONNET"],
         "mind_note": "no model, or SONNET; never an unattended builder",
         "never": [], "never_law": False,
         "level": "MEDIUM", "level_note": "",
         "flag": "",
         "why": "unattended machinery stays model-free or cheap, and never builds",
         "source": "ruled 2026-09-22 · the Pulse law and the routine doctrine",
         "seed": [], "ruled": "2026-09-22",
         "ruled_cells": ["level: MEDIUM"]},
    ],
    "signals": {
        "synthesis": ["verdict", "cross-corpus", "architecture", "build brief",
                      "whole prompt", "audit", "adjudicate"],
        "build_that_ships": ["apply card", "prompt cut", "ships",
                             "bakes in", "landing sheet"],
        "verify": ["gate", "verify", "diff", "regression", "recheck"],
        "mechanical": ["walk", "apply the", "re-run", "mechanical", "type it in"],
        "bookkeeping": ["sweep", "archive", "board refresh", "rename", "tidy"],
        "bulk_read": ["scan", "screenshot", "transcript", "digest", "read every"],
        "look_pass": ["look pass", "colour", "color", "typography", "aesthetic",
                      "palette"],
        "routine": ["routine", "schedule", "unattended", "watcher"],
    },
    "thresholds": {"max_overstay_prompts": 2, "quota_watch_percent": 80},
    "switches": {"F1": True, "F2": True, "F3": True, "F4": True, "F5": True},
}


# ══════════════════════════════════════════════════════════════════════════
# small rails — json/os/sys only, so the hot path pays for nothing else
# ══════════════════════════════════════════════════════════════════════════

def read_text(path, cap):
    """A BOUNDED read.  '' when the file is missing, unreadable or empty — a file
    that is not there is never an exception in this tool."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(cap)
    except (OSError, ValueError):
        return ""
    return raw.decode("utf-8", "replace")


def read_json(path, default, cap=RUBRIC_CAP):
    text = read_text(path, cap)
    if not text.strip():
        return default
    try:
        return json.loads(text)
    except ValueError:
        return default


def mkdirs(path, mode=PRIVATE_DIR):
    """Make a directory and EVERY LEVEL THIS CALL CREATES, each with the mode.

    `os.makedirs` gives the mode to the leaf and the default umask to every
    parent it invents on the way — so a state dir created as the parent of
    `backups/` would come up 0755 where it must be 0700.
    The levels are made one at a time, shallowest-missing first, and each gets
    the mode.  An ANCESTOR that was already there keeps its own mode — it is not
    ours to change — while the folder the caller NAMED is ours either way, so its
    mode is asserted even when another hand made it (that is what keeps the state
    dir private after an install that created it some other way)."""
    path = os.path.abspath(str(path))
    if os.path.isdir(path):
        return _chmod_leaf(path, mode)           # the named folder is always ours
    missing, probe = [], path
    while probe and not os.path.isdir(probe):
        missing.append(probe)
        parent = os.path.dirname(probe)
        if parent == probe:                      # the root: nothing above it
            break
        probe = parent
    for made in reversed(missing):               # shallowest first
        try:
            os.mkdir(made)
        except FileExistsError:
            continue                             # another hand made it: not ours
        except OSError:
            return os.path.isdir(path)
        _chmod_leaf(made, mode)
    return os.path.isdir(path)


def _chmod_leaf(path, mode):
    """The folder a caller NAMED gets its mode whether this run made it or not —
    the state dir is this tool's own and must be 0700, and an install that
    made it some other way must not leave it readable.  Only levels ABOVE it that
    were already there are left as they are."""
    try:
        os.chmod(path, mode)
    except OSError:
        pass
    return True


def write_atomic(path, text, mode=PRIVATE_FILE):
    """A temp file and one os.replace, so a reader never sees half a file.

    NEVER LOOSEN A FILE'S PERMISSIONS: replacing a file that already exists keeps
    that file's own mode exactly (a settings file may be 0600 and may hold an env
    block, and an install that made it world-readable would be a real harm done
    quietly).  The mode is set on the TEMP file before the replace, so the
    finished path is never, for an instant, more readable than it should be.

    THE TEMP NAME CARRIES THE PID, NOT A RANDOM SUFFIX: `tempfile` costs fifteen
    milliseconds to import, and this write is on the hook's hot path.  Two runs of
    this tool in one session cannot share a pid, so the name is as unique as it
    needs to be, and a crash leaves one obvious file behind rather than a mystery."""
    parent = os.path.dirname(path) or "."
    if not os.path.isdir(parent):
        mkdirs(parent)
    want = mode
    try:
        want = os.stat(path).st_mode & 0o7777       # an existing file's own mode wins
    except OSError:
        pass
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, want)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        try:
            os.chmod(tmp, want)                     # before the replace, never after
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
    """One bounded line, rotated at 1 MB.  Never raises: a log that cannot be
    written is not a reason to disturb a prompt."""
    try:
        import time
        path = os.path.join(str(state_dir), "effort.log")
        mkdirs(os.path.dirname(path))
        try:
            if os.path.getsize(path) > LOG_CAP:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), str(text)[:500]))
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


def token(*parts):
    """A cue's identity: the frame, the session, and the facts the cue states.
    NO IDENTITY CONTAINS A CLOCK — the same facts tomorrow are the same cue, and
    a rerun says nothing twice."""
    import hashlib
    raw = "\x1f".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]


def here():
    return os.path.dirname(os.path.abspath(__file__))


def hub_dir(explicit=None):
    """The hub folder: what --hub says, else this file's parent's parent — which
    is right in both layouts, the hub's own tools/ and the brain mirror's."""
    if explicit:
        return str(explicit)
    return os.path.dirname(here())


def home_dir(explicit=None):
    return str(explicit) if explicit else os.path.expanduser("~")


# ══════════════════════════════════════════════════════════════════════════
# the rubric
# ══════════════════════════════════════════════════════════════════════════

def rubric_path(hub):
    return os.path.join(str(hub), "effort-rubric.json")


def load_rubric(hub, law=None):
    """(rubric, note) — the file when it is readable and not refused, the built-in
    seed otherwise.  `note` is the one line --status says; '' when the file is
    the one in use and nothing is wrong with it."""
    path = rubric_path(hub)
    if not os.path.isfile(path):
        return dict(SEED), "rubric: seed (no effort-rubric.json in %s)" % hub
    data = read_json(path, None)
    if not isinstance(data, dict):
        return dict(SEED), "rubric: seed (effort-rubric.json is not readable JSON)"
    bad = rubric_fault(data, law)
    if bad:
        return dict(SEED), "rubric: seed (refused: %s)" % bad
    return data, ""


def rubric_fault(data, law=None):
    """The ONE reason a rubric is refused, or '' when it stands.

    A RUBRIC MAY TIGHTEN THE LAW, NEVER LOOSEN IT: the judgment and synthesis rows
    may not admit a mind the law forbids, and a flag-only level may not be
    reachable without a flag.  The forbidden minds are the law's own, read at run
    time; when the law paragraph cannot be parsed the floor test is UNKNOWN and is
    never reported as passed — the caller says `law floor unreadable`."""
    if not isinstance(data.get("version"), int):
        return "no integer `version`"
    dials = data.get("dials")
    if not isinstance(dials, dict) or not dials:
        return "no `dials` table"
    for vendor, table in dials.items():
        if not isinstance(table, dict) or not table:
            return "`dials.%s` is not a table of level → word" % vendor
    flag_only = data.get("flag_only_levels")
    if not isinstance(flag_only, list):
        return "no `flag_only_levels` list"
    kinds = data.get("kinds")
    if not isinstance(kinds, list) or not kinds:
        return "no `kinds` rows"
    seen = set()
    for row in kinds:
        if not isinstance(row, dict):
            return "a row in `kinds` is not an object"
        rid = str(row.get("id") or "")
        if not rid:
            return "a row in `kinds` has no `id`"
        if rid in seen:
            return "two rows share the id `%s`" % rid
        seen.add(rid)
        for key in ("name", "ask", "level", "flag", "source"):
            if key not in row:
                return "row `%s` has no `%s`" % (rid, key)
        if not str(row.get("source") or "").strip():
            return "row `%s` names no source" % rid
        if not isinstance(row.get("minds"), list):
            return "row `%s` has no `minds` list" % rid
        # A flag-only level may not be reachable without a flag.
        words = [str(row.get("level") or "")] + [str(row.get("level_note") or "")]
        for value, word in level_values(dials):
            if value not in [str(x).lower() for x in flag_only]:
                continue
            if any(word and word in text for text in words):
                if not str(row.get("flag") or "").strip():
                    return ("row `%s` reaches %s with no flag — a flag-only level may "
                            "not be reachable without one" % (rid, word))
    thresholds = data.get("thresholds")
    if not isinstance(thresholds, dict):
        return "no `thresholds` table"
    if not isinstance(data.get("switches"), dict):
        return "no `switches` table"
    if law and law.get("flagged"):
        forbidden = set(m.upper() for m in law["flagged"])
        for row in kinds:
            rid = str(row.get("id") or "")
            if rid not in ("judgment", "synthesis"):
                continue
            admitted = set(str(m).upper() for m in (row.get("minds") or []))
            crossed = sorted(admitted & forbidden)
            if crossed:
                return ("row `%s` admits %s, which the law forbids for judgment work"
                        % (rid, ", ".join(crossed)))
    return ""


def level_values(dials):
    """[(machine value, the user's word)] over every vendor's dial table."""
    out = []
    for table in (dials or {}).values():
        if isinstance(table, dict):
            for value, word in table.items():
                out.append((str(value).lower(), str(word)))
    return out


def dial_word(rubric, family, value):
    """The user's word for a machine's level.  An unknown value is shown RAW —
    never mapped, never dropped, never a crash."""
    if not value:
        return ""
    table = (rubric.get("dials") or {}).get(family)
    if isinstance(table, dict):
        for key, word in table.items():
            if str(key).lower() == str(value).lower():
                return str(word)
    # Another vendor's table may still name it; the user's word wins over raw.
    for other, table in (rubric.get("dials") or {}).items():
        if isinstance(table, dict):
            for key, word in table.items():
                if str(key).lower() == str(value).lower():
                    return str(word)
    return str(value)


def dial_value(rubric, word):
    """The machine's value for a user's word (EXTRA → xhigh), '' when unknown."""
    if not word:
        return ""
    for value, name in level_values(rubric.get("dials")):
        if name.upper() == str(word).strip().upper():
            return value
    return ""


def cells_note(row):
    """What a row's cells are: RULED with the date the user ruled them, SEED
    while they are still this build's proposal, nothing when neither (P9)."""
    row = row or {}
    if row.get("ruled"):
        return "   [RULED %s: %s]" % (row["ruled"],
                                      "; ".join(row.get("ruled_cells") or []) or "the row")
    if row.get("seed"):
        return "   [SEED: %s]" % "; ".join(row["seed"])
    return ""


def row_by_id(rubric, rid):
    for row in (rubric.get("kinds") or []):
        if isinstance(row, dict) and str(row.get("id") or "") == rid:
            return row
    return {}


def row_by_name(rubric, name):
    want = str(name or "").strip().upper().replace(" ", "_")
    for row in (rubric.get("kinds") or []):
        if not isinstance(row, dict):
            continue
        if str(row.get("id") or "").upper() == want:
            return row
        if str(row.get("name") or "").upper().replace(" ", "_") == want:
            return row
    return {}


def user_name(rubric):
    """The name a frame says out loud, from the rubric — never from this file.
    Absent, empty or not a string: "the user" (P1)."""
    name = (rubric or {}).get("user_name")
    name = str(name).strip() if isinstance(name, (str, int)) else ""
    return name or "the user"


def switch_on(rubric, frame):
    table = rubric.get("switches")
    if not isinstance(table, dict):
        return True
    return bool(table.get(frame, True))


# ══════════════════════════════════════════════════════════════════════════
# the law's own floors, read through the semantic engine's C8 — by import
# ══════════════════════════════════════════════════════════════════════════

def law_path(home=None):
    """The user's own law book: the live file first, the brain's copy second."""
    home = home_dir(home)
    live = os.path.join(home, ".claude", "CLAUDE.md")
    if os.path.isfile(live):
        return live
    carried = os.path.join(home, "orchestrator-sync", "claude-home", "CLAUDE.md")
    if os.path.isfile(carried):
        return carried
    return live


def law_chain(path, home=None):
    """[path] — the law file and every file its `@` lines name, one level, in
    the order they stand: since the law book was split, CLAUDE.md is a short
    entry that loads the engine's book and the person's own. A file with no
    `@` line is its own whole chain, exactly as before the split. os only —
    this runs on the hook's hot path."""
    out = [path]
    try:
        with open(path, "rb") as fh:
            head = fh.read(65536).decode("utf-8", "replace")
    except OSError:
        return out
    base = os.path.dirname(path)
    for line in head.splitlines():
        s = line.strip()
        if len(s) < 2 or not s.startswith("@") or any(c.isspace() for c in s):
            continue
        raw = s[1:]
        if raw.startswith("~/") or raw.startswith("~\\"):
            target = os.path.join(home_dir(home), raw[2:])
        elif os.path.isabs(raw):
            target = raw
        else:
            target = os.path.join(base, raw)
        out.append(os.path.normpath(target))
    return out


def law_chain_key(path, home=None):
    """(key, newest mtime) over the whole chain; ("", 0.0) when the entry is
    not there. One file gives exactly law_key's own answer."""
    parts, newest = [], 0.0
    for n, one in enumerate(law_chain(path, home)):
        key, mtime = law_key(one)
        if n == 0 and not key:
            return "", 0.0
        parts.append(key or "absent")
        newest = max(newest, mtime)
    return "|".join(parts), newest


def law_chain_text(path, home=None):
    """The law book as a session reads it: the entry with each `@` line read in
    its place. One file gives exactly read_text's own answer."""
    chain = law_chain(path, home)
    text = read_text(path, LAW_CAP)
    if len(chain) == 1:
        return text
    targets = iter(chain[1:])
    out = []
    for line in text.splitlines(True):
        s = line.strip()
        if len(s) >= 2 and s.startswith("@") and not any(c.isspace() for c in s):
            target = next(targets, None)
            if target is not None:
                body = read_text(target, LAW_CAP)
                out.append(body if body.endswith("\n") or not body else body + "\n")
                continue
        out.append(line)
    return "".join(out)


class _LawCtx(object):
    """The smallest object the engine's own c8_minds() reads a law through.

    The engine's Context reads the brain, git and half the hub; C8 needs four
    things from it, and nothing else: the law's text, the line its paragraph sits
    on, a cache, and somewhere to record a miss.  So the READING is the engine's,
    imported and unchanged, and only the FILE is this tool's — no second copy of
    the pattern, and no engine run."""

    def __init__(self, text):
        self._cache = {}
        self.text = text
        self.missing = []

    def law_text(self):
        return self.text

    def law(self, title):
        needle = "**" + str(title)
        for n, line in enumerate(self.text.splitlines(), 1):
            if needle in line:
                return {"title": title, "source": "law", "line": n, "quote": line[:200]}
        return {"title": title, "source": None, "line": None, "quote": None}

    def _miss(self, what):
        if what not in self.missing:
            self.missing.append(what)


_MODULES = {}                     # one import per process, never per prompt


def sibling(name, module_name):
    """A neighbour module, imported by path (their names carry hyphens) and held
    for the life of the process.  Read and imported, never edited and never run:
    nothing here executes a tool's main()."""
    if module_name in _MODULES:
        return _MODULES[module_name]
    import importlib.util
    path = os.path.join(here(), name)
    module = None
    if os.path.isfile(path):
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
    _MODULES[module_name] = module
    return module


def engine_module():
    """The semantic engine, imported — never copied, never edited, never run.

    Importing it costs a sys.path insert and a stdout/stderr re-encode, and
    nothing else: it reads no file and starts no thread until something calls it.
    It is 250 KB of source, so the hook pays for it only when it must (see
    c8_pattern), and never twice in one process."""
    return sibling("semantic-engine.py", "exo_semantic_engine")


def engine_key():
    """The engine file's own fingerprint — what any cache of its bytes is keyed
    to, so a single edit to it invalidates every cached reading."""
    try:
        st = os.stat(os.path.join(here(), "semantic-engine.py"))
        return "%d-%d" % (st.st_size, st.st_mtime_ns)
    except OSError:
        return "none"


def c8_pattern(state_dir=None):
    """C8_VERB — the engine's own judgment-verb pattern, compiled from THE
    ENGINE'S OWN BYTES.

    THE PATTERN IS NEVER WRITTEN IN THIS FILE.  On a cold run the engine is
    imported and `C8_VERB.pattern` is taken from it; the pattern text is then
    cached in the state dir against the engine file's size and mtime, so the next
    prompt costs one stat instead of compiling 250 KB of source — and any edit to
    the engine, which necessarily moves its mtime, throws the cache away and the
    engine is read again.  A machine-made cache of the engine's own bytes cannot
    drift from it the way a hand-written copy would."""
    import re
    key = engine_key()
    held = _MODULES.get("c8pattern")
    if held and held[0] == key:
        return held[1]
    cache_file = os.path.join(str(state_dir), "c8.json") if state_dir else ""
    if cache_file:
        kept = read_json(cache_file, None, cap=65536)
        if isinstance(kept, dict) and kept.get("key") == key and kept.get("pattern"):
            try:
                rx = re.compile(kept["pattern"])
                _MODULES["c8pattern"] = (key, rx)
                return rx
            except re.error:
                pass
    engine = engine_module()
    if engine is None:
        return None
    rx = engine.C8_VERB
    _MODULES["c8pattern"] = (key, rx)
    if cache_file:
        try:
            write_atomic(cache_file, json.dumps(
                {"key": key, "pattern": rx.pattern,
                 "from": "semantic-engine.py C8_VERB"}, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return rx


def read_law(state_dir=None, home=None, cache=True):
    """{flagged, floor, path, readable, why} — the minds the law flags on a model
    line and the mind it names as the floor for a judgment step.

    Read from the law's own paragraph at run time.  The RESULT is cached in the
    state dir against the law file's own size and mtime and the engine's, so an
    unchanged law costs one stat instead of an import; any change to either file
    re-reads.  The cache holds the ANSWER, never the pattern."""
    path = law_path(home)
    key, _mtime = law_chain_key(path, home)
    if not key:
        return {"flagged": [], "floor": None, "path": path, "readable": False,
                "why": "the law file is not there"}
    try:
        est = os.stat(os.path.join(here(), "semantic-engine.py"))
        key += "/%d-%d" % (est.st_size, est.st_mtime_ns)
    except OSError:
        key += "/none"
    cache_file = os.path.join(str(state_dir), "law.json") if state_dir else ""
    if cache and cache_file:
        held = read_json(cache_file, None)
        if isinstance(held, dict) and held.get("key") == key:
            return {"flagged": list(held.get("flagged") or []),
                    "floor": held.get("floor"), "path": path,
                    "readable": bool(held.get("readable")),
                    "why": held.get("why") or ""}
    out = {"flagged": [], "floor": None, "path": path, "readable": False, "why": ""}
    try:
        engine = engine_module()
        if engine is None:
            out["why"] = "the semantic engine is not beside this tool"
        else:
            ctx = _LawCtx(law_chain_text(path, home))
            flagged, floor = engine.c8_minds(ctx)
            out["flagged"] = [str(m).upper() for m in (flagged or [])]
            out["floor"] = str(floor).upper() if floor else None
            out["readable"] = bool(out["flagged"])
            if not out["readable"]:
                out["why"] = (ctx.missing[0] if ctx.missing
                              else "the law paragraph no longer parses")
    except Exception as exc:
        out["why"] = "%r" % (exc,)
    if cache and cache_file:
        try:
            body = dict(out)
            body["key"] = key
            body.pop("path", None)
            write_atomic(cache_file, json.dumps(body, ensure_ascii=False) + "\n")
        except Exception:
            pass
    return out


def judgment_verb(text, state_dir=None):
    """The judgment verb a prompt carries, by the SEMANTIC ENGINE'S OWN pattern
    (C8_VERB with its noun guards).  '' when the prompt carries none.

    The pattern is not copied and not tightened here: frame 4's verdict IS C8's, so
    one reading of the law's six verbs serves the opener check and this cue
    alike, and a change to it changes both."""
    if not text:
        return ""
    rx = c8_pattern(state_dir)
    if rx is None:
        return ""
    hit = rx.search(str(text))
    return hit.group(0) if hit else ""


# ══════════════════════════════════════════════════════════════════════════
# minds — the pulse's own mapper, imported
# ══════════════════════════════════════════════════════════════════════════

def _tools_on_path():
    folder = here()
    if folder not in sys.path:
        sys.path.insert(0, folder)


def vendor_family(kind, model):
    """The vendor a model id belongs to, FROM THE ID'S OWN PREFIX — a plain string
    test, so the dial's word costs nothing on a prompt that needs no mind.  An id
    no table names still gets its vendor: its prefix is its vendor."""
    model = str(model or "")
    if "-" in model:
        prefix = model.split("-", 1)[0].lower()
        return {"claude": "anthropic", "gpt": "openai",
                "o": "openai", "grok": "xai"}.get(prefix, prefix)
    return VENDOR_FAMILY.get(kind, kind or "")


def mind_of_model(kind, model):
    """(mind, vendor family, known?) for a model id, the way the pulse maps it for
    the tree (exo_common.mind_of, which pulse.py imports as _mind_of), with
    i-am.py's canon_mind over it so a persona's aliases are the stamp's.

    AN UNKNOWN ID IS NEVER GUESSED: it gets its vendor from its own prefix and is
    shown raw: nothing about one fleet is typed in.

    CALLED ONLY WHEN A FRAME NEEDS A MIND (frame 4 once a verb is found, frame 5 once an
    opener is found): naming the mind means importing the pulse's reader, and
    that import is the most expensive thing on this path."""
    model = str(model or "")
    family = vendor_family(kind, model)
    if not model:
        return "", family, False
    try:
        _tools_on_path()
        import exo_common                       # plain import: no importlib.util
        import exo_registry
        common = exo_common
        mind = common.mind_of(kind, model)
        # canon_mind folds a vendor's personas (GPT/CODEX → ASTRA).  The pulse's
        # own names need no folding, so the alias table is opened only for a name
        # that is not one of them.
        if mind and mind not in getattr(common, "MINDS", ()):
            i_am = sibling("i-am.py", "exo_i_am")
            if i_am is not None:
                mind = i_am.canon_mind(mind)
        # The mapper reads a product name off ANY id
        # (zzz-9 -> ZZZ).  A mind is KNOWN only when the registry lists it; an
        # id it does not list is shown raw.  A registry that cannot be read
        # keeps the old behaviour (the except below handles an import failure
        # the same way as the mapper's).
        try:
            listed = exo_registry.mind_names(exo_registry.registry())
        except Exception:
            listed = None
        if listed and mind and str(mind).upper() not in listed:
            return model, family, False
    except Exception:
        return model, family, False
    # The mapper answers CLAUDE when a Claude transcript names no model it knows;
    # an id it cannot name is shown raw rather than called by a name it is not.
    if not mind or (mind == "CLAUDE" and "claude-" not in model.lower()):
        return model, family, False
    if mind == "CLAUDE":
        return model, family, False
    return mind, family, True


# ══════════════════════════════════════════════════════════════════════════
# the transcript's tail, and the ASK its last reply carries
# ══════════════════════════════════════════════════════════════════════════

UNATTENDED_MARKS = ("<scheduled-task", "<task-notification")


def unattended(prompt):
    """Is this prompt a SCHEDULED RUN's rather than a person's? (P2)

    A scheduled task's prompt is recorded exactly as a typed one — promptSource
    "sdk", origin "human" — and the hook's input carries no origin at all, so the
    app's own opening tag is the only mark there is.  The app writes it itself,
    and its next sentence says why this matters: "This is an automated run of a
    scheduled task. The user is not present to answer questions."  A cue with no
    reader is noise, so such a prompt is answered with silence — while the state
    still advances, so the next prompt a person types is read right.

    A TASK NOTIFICATION IS THE SAME CASE: a live capture
    shows the app injecting `<task-notification>…` through UserPromptSubmit
    exactly like a typed prompt — four of five captures were one — and nobody
    typed it either."""
    return str(prompt or "").lstrip().startswith(UNATTENDED_MARKS)


def facts_mind(facts):
    """The window's mind, resolved ONCE and only when a frame asks for it.  Most
    prompts never ask, and those prompts never pay for the reader."""
    if facts.get("_mind_done"):
        return facts.get("mind") or ""
    mind, family, known = mind_of_model(facts.get("kind") or "claude",
                                        facts.get("model"))
    facts["mind"], facts["mind_known"], facts["_mind_done"] = mind, known, True
    if facts.get("model"):
        facts["family"] = family
    return mind


def tail_reply(path, cap=TAIL_BYTES):
    """{text, uuid, model, effort} of the LAST main-thread reply in a transcript's
    last `cap` bytes — or an empty dict.

    Bounded by construction: a 5 MB transcript costs one seek and one 256 KB read.
    The first line of the window is almost always half a record and is dropped.
    A SUBAGENT'S RECORDS ARE SKIPPED (`isSidechain`): a builder's reply is not
    this window's last word.  A torn line is skipped, never raised."""
    out = {}
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > cap:
                fh.seek(size - cap)
            raw = fh.read(cap)
    except (OSError, ValueError):
        return out
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()
    if size > cap and lines:
        lines = lines[1:]
    for line in lines:
        if '"assistant"' not in line:
            continue
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        if rec.get("isSidechain"):
            continue
        message = rec.get("message") or {}
        blocks = message.get("content") or []
        body = ""
        if isinstance(blocks, list):
            body = "".join(b.get("text", "") for b in blocks
                           if isinstance(b, dict) and b.get("type") == "text")
        elif isinstance(blocks, str):
            body = blocks
        if not body.strip():
            continue
        out = {"text": body, "uuid": str(rec.get("uuid") or ""),
               "model": str(message.get("model") or ""),
               "effort": str(rec.get("effort") or ""),
               "timestamp": rec.get("timestamp")}
    return out


def _fence_and_quote(lines):
    """[(line, inside a fence?, a block quote?)] — a plate a reply DISCUSSES is
    not a plate a reply GIVES, and this is the whole difference."""
    out = []
    fence = False
    for line in lines:
        stripped = line.strip()
        opener = stripped.startswith("```") or stripped.startswith("~~~")
        if opener and not fence:
            out.append((line, True, False))
            fence = True
            continue
        if opener and fence:
            out.append((line, True, False))
            fence = False
            continue
        out.append((line, fence, stripped.startswith(">")))
    return out


def parse_ask(text, rubric):
    """The ASK a reply's bottom plate makes: {level, word, mind, span} or {}.

    THE LAST bottom plate in the final 15 lines, outside fenced blocks and block
    quotes — a line carrying `NEXT TURN` or `NEXT STRETCH` (bold or not), then
    `STATION · MIND · EFFORT` in a code span or plain.  The older Max flag —
    "this is a Max turn — flip effort up now" — is an ask of that level for a
    TURN.  Two plates: the last one wins."""
    if not text:
        return {}
    import re
    lines = str(text).splitlines()
    marked = _fence_and_quote(lines)
    low = max(0, len(lines) - TAIL_LINES)
    arrow = re.compile(r"(?i)NEXT\s+(TURN|STRETCH)")
    trio = re.compile(r"([A-Za-z0-9_.-]{2,20})\s*·\s*([A-Za-z0-9_.-]{2,20})\s*·\s*"
                      r"([A-Za-z0-9_.-]{2,20})")
    flag_old = re.compile(r"(?i)this is a (\w+) turn\b.{0,40}?flip\b.{0,30}?\bup\b")
    found = {}
    for index in range(low, len(lines)):
        line, in_fence, in_quote = marked[index]
        if in_fence or in_quote:
            continue
        hit = arrow.search(line)
        if hit:
            span = "TURN" if hit.group(1).upper() == "TURN" else "STRETCH"
            # the trio rides the same line, or the next line or two under it
            trio_hit = trio.search(line[hit.end():])
            step = 0
            while trio_hit is None and step < PLATE_GAP and index + step + 1 < len(lines):
                step += 1
                nxt, nxt_fence, nxt_quote = marked[index + step]
                if nxt_fence or nxt_quote:
                    break
                if arrow.search(nxt):
                    break
                trio_hit = trio.search(nxt)
            if trio_hit is None:
                continue
            word = trio_hit.group(3).strip().strip("`*_ ")
            value = dial_value(rubric, word)
            found = {"level": value, "word": word if not value
                     else dial_word(rubric, "anthropic", value),
                     "mind": trio_hit.group(2).strip().strip("`*_ "),
                     "span": span}
            continue
        old = flag_old.search(line)
        if old:
            word = old.group(1).strip()
            value = dial_value(rubric, word)
            found = {"level": value, "word": word if not value
                     else dial_word(rubric, "anthropic", value),
                     "mind": "", "span": "TURN"}
    return found


# ══════════════════════════════════════════════════════════════════════════
# per-session state
# ══════════════════════════════════════════════════════════════════════════

def state_file(state_dir, session):
    return os.path.join(str(state_dir), "sessions", "%s.json" % session)


def fresh_state():
    """A session the tool has never seen — the replay's whole memory, held in RAM
    so that a walk over the real record writes nothing anywhere."""
    return {"dial_last": "", "mind_last": "", "ask": {}, "max_run": 0,
            "max_runs": 0, "cued": [], "first_done": False, "f5_done": False,
            "source": "", "ran_last": "", "ran_uuid": "", "said_level_last": False,
            "opener_named": "", "title": "", "ask_turn_checked": False,
            "turn_spent": False}


def load_state(state_dir, session):
    data = read_json(state_file(state_dir, session), None)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("dial_last", "")
    data.setdefault("mind_last", "")
    data.setdefault("ask", {})
    data.setdefault("max_run", 0)
    data.setdefault("max_runs", 0)
    data.setdefault("cued", [])
    data.setdefault("first_done", False)
    data.setdefault("f5_done", False)
    for key, value in (("source", ""), ("ran_last", ""), ("ran_uuid", ""),
                       ("said_level_last", False), ("opener_named", ""),
                       ("title", ""), ("ask_turn_checked", False),
                       ("turn_spent", False)):
        data.setdefault(key, value)
    return data


def save_state(state_dir, session, state):
    path = state_file(state_dir, session)
    mkdirs(os.path.dirname(path))
    state["cued"] = list(state.get("cued") or [])[-CUED_CAP:]
    write_atomic(path, json.dumps(state, ensure_ascii=False, sort_keys=True) + "\n")


# ══════════════════════════════════════════════════════════════════════════
# the five frames — the tool's own fixed words
# ══════════════════════════════════════════════════════════════════════════

def f1_dial(state, facts, rubric):
    """Frame 1 — the level, never a remembered one.

    TWO VOCABULARIES.  On the LIVE road the words are the original ones: the
    dial as the app hands it, "dial reads" / "dial moved".  On the RAN road the
    only level there is to know is the one the LAST REPLY RAN AT, so the words
    say exactly that and never call it the dial — it is one reply behind, and a
    frame that pretended otherwise would be the untruthful surface the whole
    build exists to avoid."""
    new = facts.get("dial_word")
    if not new:
        return None                      # UNKNOWN is never shown as a level
    if facts.get("source") == "ran":
        return f1_ran(state, facts, rubric, new)
    old_value = state.get("dial_last") or ""
    if not state.get("first_done"):
        return ("F1", token("F1", facts["session"], "first", new),
                "EFFORT — dial reads %s. Your plate's third word is %s." % (new, new))
    if str(old_value).lower() == str(facts.get("dial") or "").lower():
        return None
    old = dial_word(rubric, facts["family"], old_value) or old_value
    asked = ""
    ask = state.get("ask") or {}
    if ask.get("level") and str(ask["level"]).lower() == str(facts.get("dial")).lower():
        asked = ", as you asked"
    return ("F1", token("F1", facts["session"], old, new, bool(asked)),
            "EFFORT — dial moved: %s → %s%s. Your plate's third word is %s."
            % (old, new, asked, new))


def f1_ran(state, facts, rubric, new):
    """Frame 1 on the RAN road: the first reply this window is known to have
    run, and every change between consecutive replies.  The token carries the
    reply's own uuid, so re-reading the same reply can never say it twice."""
    uuid = facts.get("reply_uuid") or ""
    if uuid and uuid == (state.get("ran_uuid") or ""):
        return None                      # the same reply as last prompt: nothing new
    old = state.get("ran_last") or ""
    if not old:
        return ("F1", token("F1", facts["session"], "ran-first", uuid, new),
                "EFFORT — your last reply ran at %s." % new)
    if str(old).lower() == str(facts.get("dial") or "").lower():
        return None                      # two replies at the same level: nothing to say
    old_word = dial_word(rubric, facts["family"], old) or old
    asked = ""
    ask = state.get("ask") or {}
    if ask.get("level") and str(ask["level"]).lower() == str(facts.get("dial")).lower():
        asked = ", as you asked"
    return ("F1", token("F1", facts["session"], "ran", uuid, old_word, new, bool(asked)),
            "EFFORT — your last reply ran at %s; the one before it ran at %s%s."
            % (new, old_word, asked))


def f2_asked(state, facts, rubric):
    """Frame 2, ASKED, NOT TURNED — both directions: a level asked for and not given,
    and a flip back asked for and not made."""
    ask = state.get("ask") or {}
    level = str(ask.get("level") or "")
    if not level or not facts.get("dial"):
        return None
    if facts.get("source") == "ran":
        return f2_ran(state, facts, rubric, ask, level)
    if level.lower() == str(facts["dial"]).lower():
        return None
    if ask.get("span") == "TURN" and int(ask.get("prompts") or 0) >= 1:
        return None                      # a TURN ask covers the next prompt only
    word = ask.get("word") or dial_word(rubric, facts["family"], level)
    return ("F2", token("F2", facts["session"], level, facts["dial"]),
            "EFFORT — your last plate asked for %s; the dial still reads %s. "
            "Say so in one line, then go on %s's word."
            % (word, facts["dial_word"], user_name(rubric)))


def f2_ran(state, facts, rubric, ask, level):
    """Frame 2 on the RAN road: ONE PROMPT LATER than on the live road, because
    the answer is in a reply that has not been written yet.

    The plate rides reply N.  The prompt after it draws reply N+1, and the level
    N+1 ran at is only readable at prompt N+2 — so the check waits for a reply
    NEWER than the one the plate rode, and the words say "your plate before
    last".  A TURN ask is checked once; a STRETCH ask is checked at every prompt
    until a reply runs at the level or a newer plate replaces it, and each (ask,
    level-it-ran-at) pair is said once."""
    uuid = facts.get("reply_uuid") or ""
    if not uuid or uuid == (ask.get("uuid") or ""):
        return None                      # still the plate's own reply: too early
    if level.lower() == str(facts["dial"]).lower():
        return None                      # it ran at the level asked for
    if ask.get("span") == "TURN" and state.get("ask_turn_checked"):
        return None                      # a TURN ask is asked about once
    word = ask.get("word") or dial_word(rubric, facts["family"], level)
    return ("F2", token("F2", facts["session"], "ran", level, facts["dial"]),
            "EFFORT — your plate before last asked for %s; your last reply still ran "
            "at %s. Say so in one line, then go on %s's word."
            % (word, facts["dial_word"], user_name(rubric)))


def f3_overstay(state, facts, rubric):
    """Frame 3, MAX OVERSTAY — a window left at a flag-only level through ordinary work
    says so by its second prompt."""
    run = int(state.get("max_run") or 0)
    threshold = int(((rubric.get("thresholds") or {}).get("max_overstay_prompts")) or 2)
    if run < threshold:
        return None
    level = facts["dial_word"]
    if facts.get("source") == "ran":
        # P12: what is counted is REPLIES that ran at the level, not prompts —
        # the only thing this road can see — and the words say so.
        return ("F3", token("F3", facts["session"], "ran", facts["dial"],
                            state.get("max_runs")),
                "EFFORT — your last %d replies ran at %s and no plate asked for it. "
                "%s is for synthesis turns (law §3). If this stretch is not one, end "
                "your reply with the ⇩ plate; if it is, say so in one line."
                % (run, level, level))
    return ("F3", token("F3", facts["session"], facts["dial"], state.get("max_runs")),
            "EFFORT — the dial has read %s for %d prompts and no plate asked for it. "
            "%s is for synthesis turns (law §3). If this stretch is not one, end your "
            "reply with the ⇩ plate; if it is, say so in one line." % (level, run, level))


def f4_forbidden(state, facts, rubric, law):
    """Frame 4, JUDGMENT ON A FORBIDDEN MIND — the law's own minds, the engine's own
    verb pattern.  When the law paragraph cannot be read, this frame never fires:
    an unreadable floor is UNKNOWN, and unknown never reads as passed."""
    if not law.get("readable") or not law.get("flagged"):
        return None
    # THE PROMPT IS TESTED BEFORE THE MIND IS NAMED: the verb test is one cached
    # pattern and a search; naming the mind means importing the pulse's reader.
    # Most prompts carry no judgment verb and pay for neither.
    verb = judgment_verb(facts.get("prompt"), facts.get("state_dir"))
    if not verb:
        return None
    mind = facts_mind(facts)
    if not mind or mind.upper() not in [m.upper() for m in law["flagged"]]:
        return None
    row = row_by_id(rubric, "judgment")
    minds = [str(m).upper() for m in (row.get("minds") or [])]
    floor = law.get("floor")
    if floor and floor.upper() in minds:            # the law's own floor leads
        minds = [floor.upper()] + [m for m in minds if m.upper() != floor.upper()]
    elif floor:
        minds = [floor.upper()] + minds
    goes = ", else ".join(minds) if minds else (floor or "the judging mind")
    return ("F4", token("F4", facts["session"], mind, verb.lower()),
            "EFFORT — this window's mind is %s and the prompt reads as judgment work "
            "(\"%s\"). Law: judgment goes to %s, never %s. Say so before working — or "
            "say in one line why this is not judgment."
            % (mind, verb, goes, mind.upper()))


def f5_opener(state, facts, rubric):
    """Frame 5, OPENED OFF THE OPENER — once per session, and only for a lane the prompt
    itself names.  A lane that is not known is never guessed at."""
    if state.get("f5_done"):
        return None
    # P13: at the first prompt of a session on the RAN road neither the mind nor
    # the level is knowable — there is no reply yet — so the opener the FIRST
    # prompt names is kept, and the answer is given at the next prompt, when the
    # first reply can be read.  A lane the prompt never named is still never
    # guessed at.
    opener = find_opener(facts.get("prompt"), facts.get("cwd")) \
        or str(state.get("opener_named") or "")
    if not opener or not os.path.isfile(opener):
        return None
    header = opener_header(opener)
    model_line = str(header.get("model") or "")
    if not model_line:
        return None
    mind_o, level_o = split_model_line(model_line, rubric)
    if not mind_o and not level_o:
        return None
    mind = facts_mind(facts)                    # named only now, for a known lane
    dial = facts.get("dial_word") or ""
    same_mind = (not mind_o) or (not mind) or mind_o.upper() == mind.upper()
    same_dial = (not level_o) or (not dial) or level_o.upper() == dial.upper()
    if same_mind and same_dial:
        return None
    judgment = str(header.get("judgment") or "").strip()
    said = ""
    if judgment:
        try:
            carriers = sibling("opener_carriers.py", "opener_carriers")
            said = ' (judgment: "%s")' % carriers.words(judgment, 12)
        except Exception:
            said = ' (judgment: "%s")' % " ".join(judgment.split()[:12])
    if facts.get("source") == "ran":
        return ("F5", token("F5", facts["session"], "ran", opener, mind_o, level_o,
                            mind, dial),
                "EFFORT — this lane's opener asks %s · %s%s; this window ran its "
                "first reply at %s · %s. Say so in your next reply."
                % (mind_o or "—", level_o or "—", said, mind or "—", dial or "—"))
    return ("F5", token("F5", facts["session"], opener, mind_o, level_o, mind, dial),
            "EFFORT — this lane's opener asks %s · %s%s; this window is %s · %s. "
            "Say so in your first reply."
            % (mind_o or "—", level_o or "—", said, mind or "—", dial or "—"))


def find_opener(prompt, cwd):
    """The OPENER file a prompt NAMES and that exists under cwd — never a guess,
    never a walk of the folder: the lane must be named to be checked."""
    if not prompt or not cwd:
        return ""
    import re
    names = re.findall(r"(?i)\b(OPENER(?:-[A-Za-z0-9_]+)?\.md)\b", str(prompt))
    for name in names:
        candidate = os.path.join(str(cwd), name)
        if os.path.isfile(candidate):
            return candidate
    return ""


def opener_header(path):
    """The opener's header, through the collector's OWN parser (the opener contract,
    opener_carriers.parse_text) — one reading of `key: value`, never a second."""
    text = read_text(path, OPENER_CAP)
    if not text:
        return {}
    try:
        carriers = sibling("opener_carriers.py", "opener_carriers")
        return carriers.parse_text(text).get("header") or {}
    except Exception:
        header = {}
        for line in text.splitlines():
            if line.strip() == "---":
                break
            if ":" in line:
                key, _, value = line.partition(":")
                header[key.strip().lower()] = value.strip()
        return header


def split_model_line(line, rubric):
    """`model: FABLE · EXTRA` → ("FABLE", "EXTRA").  Either half may be missing."""
    parts = [p.strip().strip("`*_") for p in str(line).replace("|", "·").split("·")]
    mind, level = "", ""
    for part in parts:
        if not part:
            continue
        word = part.split()[0].upper()
        if dial_value(rubric, word):
            level = word
        elif not mind:
            mind = word
    return mind, level


# ══════════════════════════════════════════════════════════════════════════
# THE TURN-START LINES — the dial, the plate, the law book
# ══════════════════════════════════════════════════════════════════════════
# THE BAR: the machine notices, the human never checks.  A session never has to
# remember to read its dial, and never learns a new law only because a person
# carried it.
#
# THE ROAD, PROVED BEFORE THIS WAS BUILT.  The app hands a hook no
# dial: its input carries no `effort` field and its environment no
# CLAUDE_EFFORT (captured live, then re-read in a second
# report from the installed hook's state files, every session of the day on the
# RAN or UNKNOWN road).  A session's OWN command does carry it.  So the hook
# prints the dial when its own process can read it (the LIVE road, any version
# that hands one), and otherwise prints the ONE command that reads it —
# `effort.py --dial`, run by the session as a child of its own, which prints the
# line from the process that holds the value.  NEVER A VALUE NOT READ THIS TURN.

DIAL_NOW = "DIAL NOW — EFFORT %s · MODEL %s"
DIAL_RUN = ("DIAL — run `%s` before you work: this hook cannot read the dial, "
            "so your plate carries what that command prints.")
PLATE_SAID = ("PLATE — your last reply's plate read `%s`; %s. Put the dial's own "
              "words on this reply's plate and say so in one line.")
LAW_SAID = ("LAW BOOK CHANGED at %s, after you woke — new or changed: %s%s. "
            "Read it in %s before you work.")
TOP_LINES = 6                  # the plate is the banner: the first lines of a reply
WAKE_DIR = "wake"              # <state-dir>/wake/<session>.json — the law book at wake
NOTICED_CAP = 20
LAW_NAME_CAP = 90


def dial_command():
    """The one command a session runs to read its dial, spelt for THIS machine:
    `python` on Windows and `python3` elsewhere (the law's own words), and this
    file's own absolute path, so it runs from any project folder.  A path with a
    space in it is quoted; nothing else about the machine is written in."""
    py = "python" if os.name == "nt" else "python3"
    path = os.path.abspath(__file__)
    if any(ch in path for ch in " \t'\"$`&;|()"):
        path = '"%s"' % path
    return "%s %s --dial" % (py, path)


def tail_records(path, cap=TAIL_BYTES):
    """Every whole record in a transcript's last `cap` bytes, in order — the same
    bounded window tail_reply() reads, parsed whole this time because a TURN is
    made of prompts, tool results and hook lines as well as replies.  A torn or
    unreadable line is skipped, never raised."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if size > cap:
                fh.seek(size - cap)
            raw = fh.read(cap)
    except (OSError, ValueError):
        return []
    lines = raw.decode("utf-8", "replace").splitlines()
    if size > cap and lines:
        lines = lines[1:]
    out = []
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def is_prompt_record(rec):
    """A TURN STARTS HERE: a main-thread `user` record that carries words — typed,
    pasted, or the app's own task notification — and is not a tool's result."""
    if rec.get("type") != "user" or rec.get("isSidechain") or rec.get("isMeta"):
        return False
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        kinds = [b.get("type") for b in content if isinstance(b, dict)]
        return "text" in kinds and "tool_result" not in kinds
    return False


def is_reply_record(rec):
    """A main-thread `assistant` record from a real model — a subagent's record
    is not this window's, and the app's own `<synthetic>` records ran on no
    model at all."""
    if rec.get("type") != "assistant" or rec.get("isSidechain"):
        return False
    model = str((rec.get("message") or {}).get("model") or "")
    return bool(model) and not model.startswith("<")


def last_turn(records):
    """{records, reply, prompt_at} of the turn that ends with the newest reply
    record — or None when the window holds no reply.  A window that holds no
    prompt at all is one long turn, and the whole window is its tail."""
    end = -1
    for index in range(len(records) - 1, -1, -1):
        if is_reply_record(records[index]):
            end = index
            break
    if end < 0:
        return None
    start = -1
    for index in range(end - 1, -1, -1):
        if is_prompt_record(records[index]):
            start = index
            break
    return {"records": records[start + 1:end + 1], "reply": records[end],
            "prompt_at": start}


def _strings(value, out, depth=0):
    """Every string inside a record, walked — a tool's output lives in
    `message.content[].content`, `toolUseResult.stdout` or a hook attachment's
    `content`, and the reader must not care which."""
    if depth > 8:
        return out
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _strings(item, out, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _strings(item, out, depth + 1)
    return out


def printed_dial(records, rubric):
    """The LAST `DIAL NOW — EFFORT <X> · MODEL <Y>` line a turn was handed by the
    dial tool itself, or None.  A reading is the dial tool's OWN PRINT and nothing
    else: a line at column 0 of the OUTPUT of a tool call whose own command ran
    `effort.py` with `--dial`, or of this hook's own line on the live road (a
    `hook_additional_context` attachment).  A line QUOTED in prose or in a code
    span, in a file a window read, in a letter's echo, or in an `api-request-blob`
    is never a reading, and neither is an assistant's own words; within one tool
    result the FIRST such line speaks (the tool prints it at its head), and across
    the turn the last one wins.  The level must be a word the rubric knows, so a
    line of source code that spells the format is not a reading either.  The model
    word rides the same reading — it is never read from anywhere else."""
    import re
    rx = re.compile(r"^DIAL NOW — EFFORT (\S+) · MODEL (\S+)", re.M)

    def first_reading(texts):
        for text in texts:
            if "DIAL NOW" not in text:
                continue
            for hit in rx.finditer(text):
                word = hit.group(1).strip("`*_.,;")
                if dial_value(rubric, word):
                    return {"word": word.upper(), "model": hit.group(2).strip("`*_.,;()")}
        return None

    ran_dial = set()        # ids of the turn's tool calls that ran `effort.py --dial`,
    found = None            # built as the turn is walked once; only their results can speak
    for rec in records:
        kind = rec.get("type")
        content = (rec.get("message") or {}).get("content")
        if kind == "assistant":
            for block in content if isinstance(content, list) else ():
                command = (block.get("input") or {}).get("command") \
                    if isinstance(block, dict) and block.get("type") == "tool_use" else None
                if isinstance(command, str) and "effort.py" in command and "--dial" in command:
                    ran_dial.add(block.get("id"))
        elif kind == "user" and isinstance(content, list):
            results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
            for block in results:
                if block.get("tool_use_id") not in ran_dial:
                    continue
                texts = _strings(block.get("content"), [])
                if len(results) == 1:                 # toolUseResult is that one call's own
                    texts += _strings(rec.get("toolUseResult"), [])
                found = first_reading(texts) or found
        elif kind == "attachment":
            attach = rec.get("attachment")
            if isinstance(attach, dict) and attach.get("type") == "hook_additional_context":
                found = first_reading(_strings(attach.get("content"), [])) or found
    return found


def find_plate(records, rubric):
    """The TOP plate of a turn — `STATION · MIND · EFFORT` in a code span in the
    first lines of a reply's text, outside fences and block quotes, whose third
    word is a level the rubric knows.  A bottom plate (a line under NEXT TURN /
    NEXT STRETCH) is an ask, never the plate, and is skipped with the lines
    that carry its trio.  The first one found is the plate."""
    import re
    span = re.compile(r"`([^`\n]{5,80})`")
    trio = re.compile(r"^\s*([A-Za-z0-9_.-]{2,20})\s*·\s*([A-Za-z0-9_.-]{2,20})"
                      r"\s*·\s*([A-Za-z0-9_.-]{2,20})\s*$")
    arrow = re.compile(r"(?i)NEXT\s+(TURN|STRETCH)")
    for rec in records:
        if not is_reply_record(rec):
            continue
        blocks = (rec.get("message") or {}).get("content") or []
        if isinstance(blocks, str):
            blocks = [{"type": "text", "text": blocks}]
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            lines = [l for l in str(block.get("text") or "").splitlines()]
            marked = _fence_and_quote(lines)
            shown, skip = 0, 0
            for line, in_fence, in_quote in marked:
                if not line.strip():
                    continue
                shown += 1
                if shown > TOP_LINES:
                    break
                if arrow.search(line):
                    skip = PLATE_GAP + 1          # the ask and the lines that carry it
                    continue
                if skip:
                    skip -= 1
                    continue
                if in_fence or in_quote:
                    continue
                for hit in span.finditer(line):
                    got = trio.match(hit.group(1))
                    if got and dial_value(rubric, got.group(3)):
                        return {"text": hit.group(1).strip(), "station": got.group(1),
                                "mind": got.group(2).upper(), "word": got.group(3).upper()}
    return None


def _same_mind(plate_mind, model):
    """Does a plate's MIND name this model?  The cheap test first — the id carries
    the mind's own word (claude-fable-5-1 is FABLE) — and the pulse's own mapper
    only when it does not, so the hot path pays for the import only on a
    disagreement worth confirming."""
    plate_mind = str(plate_mind or "").upper()
    model = str(model or "")
    if not plate_mind or not model:
        return True                                   # nothing to compare: no flag
    if plate_mind.lower() in model.lower():
        return True
    if model.upper() == plate_mind:
        return True
    mind, _family, known = mind_of_model("claude", model)
    if not known:
        return True                                   # an id nobody can name: no flag
    return str(mind).upper() == plate_mind


def plate_frame(state, facts, rubric):
    """G3 — THE PLATE THAT DISAGREES WITH THE DIAL, one line, once per reply.

    The last reply's top plate is held against the dial THAT TURN PRINTED — the
    `DIAL NOW` line it was handed — and, where it printed none, against what the
    reply's own record says it RAN at (the app writes `effort` and `model` on
    every assistant record).  Both are facts read from the transcript this turn;
    the words say which one spoke."""
    turn = facts.get("turn")
    if not turn:
        return None
    plate = find_plate(turn["records"], rubric)
    if not plate:
        return None
    reply = turn["reply"]
    uuid = str(reply.get("uuid") or "")
    dial = printed_dial(turn["records"], rubric)
    if dial:
        word = dial["word"]
        model = dial["model"] if dial["model"].lower() not in ("unread", "") else ""
        said = "the dial it printed read EFFORT %s · MODEL %s" % (word, dial["model"])
    else:
        ran = str(reply.get("effort") or "").strip()
        if not ran:
            return None                               # nothing read: nothing said
        family = vendor_family("claude", (reply.get("message") or {}).get("model"))
        word = dial_word(rubric, family, ran).upper()
        model = str((reply.get("message") or {}).get("model") or "")
        mind, _f, known = (mind_of_model("claude", model) if not
                           _same_mind(plate["mind"], model) else (plate["mind"], "", True))
        said = "that reply ran at %s on %s" % (word, mind if known else model)
    wrong_level = (dial_value(rubric, plate["word"]) or plate["word"].lower()) != \
        (dial_value(rubric, word) or word.lower())
    wrong_mind = not _same_mind(plate["mind"], model)
    if not (wrong_level or wrong_mind):
        return None
    return ("PLATE", token("PLATE", facts["session"], uuid, plate["text"], word),
            PLATE_SAID % (plate["text"], said))


def dial_line(facts, rubric):
    """THE DIAL LINE, first in the hook's words.  LIVE road: the level
    this hook's own process was handed, and the model with its own provenance.
    Otherwise: the command that
    reads it, never a level remembered or inferred."""
    if facts.get("source") == "live" and facts.get("dial_word"):
        model = str(facts.get("model") or "")
        if model:
            mind, _family, known = mind_of_model(facts.get("kind") or "claude", model)
            model_source = facts.get("model_source")
            when = {"event": "this hook's model", "app": "desktop session store"}.get(
                model_source, "as of the last reply")
            named = "%s (%s)" % (mind if known else model, when)
        else:
            named = "unread (no reply yet)"
        return DIAL_NOW % (str(facts["dial_word"]).upper(), named)
    return DIAL_RUN % dial_command()


# ── --dial: the line, from the process that holds the value ────────────────

def claude_projects(home=None):
    """Where Claude Code keeps its transcripts: CLAUDE_CONFIG_DIR when the user
    moved it, `<home>/.claude` otherwise."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home_dir(home), ".claude")
    return os.path.join(base, "projects")


def find_transcript(session, home=None):
    """A session's own transcript, by its own id — one stat per project folder,
    never a read, never a guess: '' when no file carries that name."""
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


def dial_reading(env=None, transcript="", session="", home=None, hub=None):
    """{effort, effort_from, model, model_from, line} — every value read NOW.

    EFFORT: this process's own CLAUDE_EFFORT (then CLAUDE_CODE_EFFORT_LEVEL), in
    the rubric's word.  Without one, this turn's own record when the turn has
    written one; the last reply's level is only ever said AS the last reply's.
    MODEL: the newest main-thread reply record — THIS turn's when it was written
    after the turn's prompt (the app writes a tool call's record before the tool
    runs), else said "as of the last reply"."""
    env = os.environ if env is None else env
    law = {"flagged": []}
    rubric, _note = load_rubric(hub_dir(hub), law)
    raw = str(env.get("CLAUDE_EFFORT") or env.get("CLAUDE_CODE_EFFORT_LEVEL") or "").strip()
    if not session:
        session = str(env.get("CLAUDE_CODE_SESSION_ID") or "").strip()
    if not transcript and session:
        transcript = find_transcript(session, home)
    records = tail_records(transcript) if transcript else []
    last_prompt, last_reply = -1, -1
    for index, rec in enumerate(records):
        if is_prompt_record(rec):
            last_prompt = index
        elif is_reply_record(rec):
            last_reply = index
    reply = records[last_reply] if last_reply >= 0 else {}
    this_turn = last_reply >= 0 and last_reply > last_prompt
    model = str((reply.get("message") or {}).get("model") or "")
    family = vendor_family("claude", model) or "anthropic"
    out = {"effort": "", "effort_from": "", "model": "", "model_from": "",
           "transcript": transcript}
    if raw:
        out["effort"], out["effort_from"] = dial_word(rubric, family, raw).upper(), "env"
    elif this_turn and str(reply.get("effort") or "").strip():
        out["effort"] = dial_word(rubric, family, str(reply["effort"]).strip()).upper()
        out["effort_from"] = "this turn's record"
    if model:
        mind, _f, known = mind_of_model("claude", model)
        out["model"] = mind if known else model
        out["model_from"] = "this turn" if this_turn else "the last reply"
    if out["effort"]:
        effort = out["effort"]
        if out["effort_from"] != "env":
            effort += " (from %s)" % out["effort_from"]
    else:
        ran = str(reply.get("effort") or "").strip()
        effort = "unread (this process carries no CLAUDE_EFFORT%s)" % (
            "; the last reply ran at %s" % dial_word(rubric, family, ran).upper()
            if ran else "")
    if out["model"]:
        named = out["model"] + ("" if out["model_from"] == "this turn"
                                else " (as of the last reply)")
    else:
        named = "unread (%s)" % ("no transcript for this session" if not transcript
                                 else "no reply in it yet")
    out["line"] = DIAL_NOW % (effort, named)
    return out


def cmd_dial(argv):
    """`effort.py --dial`: ONE line, read in this process, written nowhere.  It
    is the session's own command at the top of a turn (the Check-the-dial-first
    law), so the value comes from the process that holds it."""
    vendor = argv_value(argv, "--vendor") or "claude"
    if vendor == "codex":
        if not os.environ.get("CODEX_THREAD_ID"):
            print(CODEX_OFF_NOTE)
            return CLI_ERROR
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex_dial.py")
        try:
            spec = importlib.util.spec_from_file_location("codex_dial", path)
            reader = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(reader)
        except (OSError, ImportError, AttributeError):
            print("UNKNOWN — codex_reader_unavailable · age unknown")
            return CLI_ERROR
        forwarded = []
        for flag in ("--transcript", "--codex-home"):
            value = argv_value(argv, flag)
            if value:
                forwarded.extend((flag, value))
        for flag in ("--json", "--schema-check"):
            if flag in argv:
                forwarded.append(flag)
        if "--schema-check" in forwarded:
            # ASSUMES: normal dial reads may ignore new optional shapes; the explicit
            # schema canary must still name the FIRST unknown shape in file order.
            decode = reader._decode
            def canary(line):
                record, error, schema = decode(line)
                if record is not None and not error:
                    kind = record.get("type")
                    if kind not in reader._RECORD_TYPES:
                        return None, "unrecognized_record_type", "record.type: " + str(kind)
                    if kind == "event_msg" and record["payload"].get("type") not in reader._EVENT_TYPES:
                        return None, "unrecognized_event_type", "event_msg.payload.type: " + str(record["payload"].get("type"))
                return record, error, schema
            reader._decode = canary
        return reader.main(forwarded)
    if vendor != "claude":
        print("DIAL — %s: read the dial from the app's own composer; this command "
              "reads Claude Code's (CLAUDE_EFFORT)" % vendor)
        return 0
    try:
        got = dial_reading(transcript=argv_value(argv, "--transcript"),
                           session=argv_value(argv, "--session"),
                           home=argv_value(argv, "--home") or None,
                           hub=argv_value(argv, "--hub") or None)
        print(got["line"])
    except Exception as exc:                         # a reading that failed says so
        print("DIAL NOW — EFFORT unread · MODEL unread (%s)" % type(exc).__name__)
    return 0


# ── the law book: a snapshot at wake, a line when it changes ───────────────

def law_blocks(text):
    """[(key, name, hash)] for every paragraph of the law book, in file order.

    A paragraph is a run of lines between blank lines; a line that opens with a
    bold head (`**…**`, bare or as a list item) or a `#` heading starts a new
    one.  Its KEY is its head (or heading, or its first words when it has
    neither), so an amendment inside a rule reads as that rule CHANGED and a
    new rule reads as NEW; its NAME is the head up to its first ` (`."""
    import hashlib
    import re
    head_rx = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?\*\*(.+?)\*\*")
    blocks, para, seen = [], [], {}

    def flush():
        if not para:
            return
        first = para[0]
        hit = head_rx.match(first)
        if hit:
            head = " ".join(hit.group(1).split()).rstrip(":. ")
            kind, name = "H", head.split(" (", 1)[0].rstrip(":. ") or head
        elif first.lstrip().startswith("#"):
            head = first.strip().lstrip("#").strip()
            kind, name = "#", head
        else:
            head = " ".join(first.split())[:60]
            kind, name = "P", head
        key = "%s:%s" % (kind, head[:160])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = "%s#%d" % (key, seen[key])
        body = "\n".join(para)
        digest = hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()[:16]
        name = name if len(name) <= LAW_NAME_CAP else name[:LAW_NAME_CAP - 1] + "…"
        blocks.append((key, name, digest))
        del para[:]

    for line in str(text or "").splitlines():
        if not line.strip():
            flush()
            continue
        if para and (head_rx.match(line) or line.lstrip().startswith("#")):
            flush()
        para.append(line)
    flush()
    return blocks


def wake_file(state_dir, session):
    return os.path.join(str(state_dir), WAKE_DIR, "%s.json" % session)


def law_key(path):
    try:
        st = os.stat(path)
    except OSError:
        return "", 0.0
    return "%d-%d" % (st.st_size, st.st_mtime_ns), st.st_mtime


def snapshot_law(state_dir, session, home=None, why="wake"):
    """The law book AS THIS SESSION WOKE TO IT — written at every SessionStart
    (the app rebuilds a session's context from the file then), and at the first
    prompt of a session this hook never saw start.  One file per session id."""
    import time
    path = law_path(home)
    key, _mtime = law_chain_key(path, home)
    if not key:
        return None
    text = law_chain_text(path, home)
    body = {"session": session, "woke": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "woke_ts": time.time(), "how": why, "law": path, "law_key": key,
            "blocks": dict((k, h) for k, _n, h in law_blocks(text)), "noticed": []}
    write_atomic(wake_file(state_dir, session),
                 json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
    return body


def law_frame(state_dir, session, home=None):
    """(line or '', the snapshot to write after the line is printed, or None).

    THE FAST PATH IS ONE STAT AND ONE SMALL READ: an unchanged law book costs
    nothing more.  A changed one is read, its paragraphs held against the
    snapshot, and the FIRST new-or-changed head in file order is named — with a
    count of the rest.  A touch that changed no paragraph moves the snapshot's
    key and says nothing.  A session the hook never saw wake gets its snapshot
    now and no line: what it woke to is not knowable, and a guess would be a
    false alarm."""
    import time
    snap = read_json(wake_file(state_dir, session), None)
    if not isinstance(snap, dict) or not isinstance(snap.get("blocks"), dict):
        snapshot_law(state_dir, session, home, why="first prompt")
        return "", None
    path = law_path(home)
    key, mtime = law_chain_key(path, home)
    if not key or key == snap.get("law_key"):
        return "", None
    blocks = law_blocks(law_chain_text(path, home))
    old = snap.get("blocks") or {}
    fresh = [name for k, name, h in blocks if old.get(k) != h]
    snap = dict(snap)
    snap["law_key"] = key
    snap["blocks"] = dict((k, h) for k, _n, h in blocks)
    if not fresh:
        return "", snap
    woke = float(snap.get("woke_ts") or 0.0)
    when = mtime if mtime >= woke else time.time()
    more = " (and %d more)" % (len(fresh) - 1) if len(fresh) > 1 else ""
    display = path
    home_path = home_dir(home)
    if display.startswith(home_path + os.sep):
        display = "~" + display[len(home_path):]
    line = LAW_SAID % (time.strftime("%H:%M", time.localtime(when)), fresh[0], more, display)
    noticed = list(snap.get("noticed") or [])
    noticed.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "law_key": key,
                    "first": fresh[0], "count": len(fresh)})
    snap["noticed"] = noticed[-NOTICED_CAP:]
    return line, snap


# ══════════════════════════════════════════════════════════════════════════
# the hook
# ══════════════════════════════════════════════════════════════════════════

def evidence_time(value):
    """Epoch seconds, or None: an undated fact is never given an invented age."""
    import datetime
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value) / 1000 if value > 1e11 else float(value)
        stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.timestamp() if stamp.tzinfo else None
    except (TypeError, ValueError, AttributeError, OverflowError):
        return None


# ASSUMES: a prompt is a person's unless it carries the app's routine frame; the hook env cannot tell a person in a Terminal from a routine, so it is never the evidence. Opposite: a <scheduled-task prompt (R11-c).
def attendance_of(event):
    return hook_say.attendance(event)


def desktop_model_fact(event, wait=True, newer_than=None, deadline=None):
    """Read this exact window, with a monotonic 3 s deadline and 250 ms polling.

    ASSUMES: app persistence may lag the first hook. Opposite: no record ever lands.
    Each read uses app_sessions' read-only reader; no app, process, preference or focus guess.
    Conflicting identities remain unavailable, even when their model words agree.
    R7: newer_than asks for a newer write; an unchanged valid record is returned
    only at the deadline, marked refresh_timed_out for the admission note.
    """
    import re
    import time
    start = time.monotonic()
    # R8: readiness and freshness share the hook-start deadline.
    deadline = min(deadline, start + 3.0) if deadline is not None else start + 3.0
    if not wait:
        deadline = start
    result = {"value": "", "source": "none", "at": None, "age_seconds": None,
              "reason": "model unavailable", "readiness_ms": 0.0, "record": None}
    session = event.get("session_id")
    if not isinstance(session, str) or not session:
        return result
    reader = sibling("app_sessions.py", "exo_app_sessions")
    if reader is None:
        return result
    host = os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", "")
    entry = event.get("entrypoint") or event.get("CLAUDE_CODE_ENTRYPOINT") or os.environ.get(
        "CLAUDE_CODE_ENTRYPOINT")
    desktop_host = entry == "claude-desktop" and host
    if desktop_host and not re.fullmatch(r"local_[A-Za-z0-9_-]+", host):
        result["reason"] = "model unavailable: malformed host identity"
        return result
    event_at = evidence_time(event.get("timestamp"))
    while True:
        matching = []
        unchanged = None
        try:
            records = [r for r in reader.records(home=home_dir(), max_age_days=2.0)
                       if not r.get("archived")]
            cli = [r for r in records if r.get("cli_id") == session]
            matching = [r for r in records if r.get("local_id") == host] if desktop_host else cli
            conflict = (desktop_host and (
                any(r.get("cli_id") not in ("", session) for r in matching) or
                any(r.get("local_id") != host for r in cli)))
            models, candidates = set(), []
            for rec in matching:
                cwd, app_cwd = event.get("cwd"), rec.get("cwd")
                if (not isinstance(cwd, str) or not cwd or not isinstance(app_cwd, str)
                        or not app_cwd or os.path.normcase(os.path.realpath(cwd)) !=
                        os.path.normcase(os.path.realpath(app_cwd))):
                    conflict = True
                    break
                model = rec.get("model")
                if not isinstance(model, str) or not re.fullmatch(r"claude-[A-Za-z0-9][A-Za-z0-9._-]*", model):
                    conflict = True
                    break
                mtime = os.path.getmtime(rec["file"])
                models.add(model)
                candidates.append((mtime, model, rec))
            if candidates and not conflict and len(models) == 1:
                mtime, model, rec = max(candidates, key=lambda row: row[0])
                result["record"] = {"present": True, "model": model, "cli_id": rec.get("cli_id"),
                                    "mtime": mtime}
                # ASSUMES: a supplied live event timestamp bounds stale disk selections.
                # A record predating that boundary cannot establish this turn's model.
                if event_at is None or mtime >= event_at:
                    current = dict(result, value=model, source="app record", at=mtime,
                                   age_seconds=max(0, time.time() - mtime), reason="exact app record")
                    if newer_than is None or mtime > newer_than:
                        result = current
                        break
                    unchanged = current
            elif matching:
                result["record"] = {"present": True, "conflict": True}
                result["reason"] = "model unavailable: record identity, cwd or model conflict"
        except (OSError, ValueError, TypeError, AttributeError):
            result["reason"] = "model unavailable: unreadable store"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            if unchanged is not None:
                result = dict(unchanged, refresh_timed_out=True,
                              reason="no newer app record within 3 s")
            break
        time.sleep(min(0.25, remaining))
    result["readiness_ms"] = round((time.monotonic() - start) * 1000, 3)
    return result


def desktop_session_model(event):
    """Compatibility for callers needing only a value, without a readiness wait."""
    return desktop_model_fact(event, wait=False)["value"]


def hook_facts(event, vendor, rubric, state_dir, model_deadline=None):
    """Everything a frame may state, gathered once, every read bounded."""
    transcript = str(event.get("transcript_path") or "")
    reply = tail_reply(transcript) if transcript else {}
    # TWO ROADS, IN ORDER, AND THE TOOL SAYS WHICH IT TOOK.
    # LIVE first: the dial as the app hands it — the documented `effort.level`,
    # then the two environment names.  This desktop app (2.2553.1) hands a hook
    # none of them, so RAN is the road in practice; a version that supplies one
    # gets the frames in their original words, with no change here.
    # RAN second: the level the LAST REPLY ACTUALLY RAN AT, out of the transcript
    # tail already in hand.  It is one reply behind the prompt, and the frames'
    # words never pretend otherwise.
    dial = str(((event.get("effort") or {}) if isinstance(event.get("effort"), dict)
                else {}).get("level") or "")
    if not dial:
        dial = str(os.environ.get("CLAUDE_EFFORT") or "").strip()
    if not dial:
        dial = str(os.environ.get("CLAUDE_CODE_EFFORT_LEVEL") or "").strip()
    source = "live" if dial else ""
    if not dial:
        dial = str(reply.get("effort") or "").strip()
        source = "ran" if dial else "unknown"
    kind = "codex" if vendor == "codex" else "claude"
    import time
    model = event.get("model")
    model = model.strip() if isinstance(model, str) else ""
    model_source = "event" if model else ""
    model_at = evidence_time(event.get("timestamp")) if model else None
    model_fact = {"value": model, "source": "live event" if model else "none",
                  "at": model_at, "age_seconds": max(0, time.time() - model_at) if model_at else None,
                  "reason": "live event" if model else "model unavailable", "readiness_ms": 0.0,
                  "record": None}
    if model and vendor == "claude":
        # Snapshot record metadata for diagnostics even when the live event wins.
        model_fact["record"] = desktop_model_fact(event, wait=False).get("record")
    if not model and vendor == "claude":
        model_fact = desktop_model_fact(event, wait=event.get("hook_event_name") == "UserPromptSubmit",
                                        deadline=model_deadline)
        model = model_fact["value"]
        model_source = "app" if model else ""
    if not model:
        reply_at = evidence_time(reply.get("timestamp"))
        boundary = evidence_time(event.get("timestamp"))
        # A lagging reply cannot undo an explicit live boundary either.
        if boundary is None or (reply_at is not None and reply_at >= boundary):
            model = reply.get("model") or ""
        model_source = "reply" if model else "unknown"
        if model:
            model_fact.update(value=model, source="last reply", at=reply_at,
                              age_seconds=max(0, time.time() - reply_at) if reply_at else None,
                              reason="last assistant reply")
    family = vendor_family(kind, model)
    return {"session": str(event.get("session_id") or ""),
            "kind": kind,
            "prompt": str(event.get("prompt") or ""),
            "cwd": str(event.get("cwd") or ""),
            "transcript": transcript,
            "state_dir": str(state_dir or ""),
            "title": str(event.get("session_title") or ""),
            "dial": dial,
            "source": source,
            "family": family,
            "dial_word": dial_word(rubric, family, dial),
            "model": model,
            "model_source": model_source,
            "model_fact": model_fact,
            "model_deadline": model_deadline,
            "attendance": attendance_of(event),
            "desktop": (event.get("entrypoint") or event.get("CLAUDE_CODE_ENTRYPOINT")
                        or os.environ.get("CLAUDE_CODE_ENTRYPOINT")) == "claude-desktop",
            "event_name": event.get("hook_event_name"),
            "event_model_present": "model" in event,
            "event_timestamp": event.get("timestamp"),
            "host": os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", ""),
            "reply": reply.get("text") or "",
            "reply_uuid": reply.get("uuid") or ""}


def cues(state, facts, rubric, law):
    """The frames this prompt earns, in their fixed order and under their cap: frame 1
    always when it is true, and beside it AT MOST ONE of frames 5, 4, 2, 3 — in that
    order.  A frame that loses its place is simply not marked as said, so it is
    said with the next prompt if it is still true."""
    said = set(state.get("cued") or [])
    out = []
    first = f1_dial(state, facts, rubric) if switch_on(rubric, "F1") else None
    if first and first[1] not in said:
        out.append(first)
    others = []
    if switch_on(rubric, "F5"):
        others.append(f5_opener(state, facts, rubric))
    if switch_on(rubric, "F4"):
        others.append(f4_forbidden(state, facts, rubric, law))
    if switch_on(rubric, "F2"):
        others.append(f2_asked(state, facts, rubric))
    if switch_on(rubric, "F3"):
        others.append(f3_overstay(state, facts, rubric))
    # THE CAP IS OVER WHAT IS STILL UNSAID: a frame whose cue has already been
    # given holds nobody's place, or one true thing would silence another for the
    # whole sitting.
    for frame in others:
        if frame and frame[1] not in said:
            out.append(frame)
            break
    return out


def said_the_level(facts):
    """Did this prompt say the level's own word? — a WORD, not a substring (P3).
    One reading, used by the prompt road directly and carried one step by the
    reply road."""
    dial = str(facts.get("dial") or "").lower()
    if not dial:
        return False
    import re
    prompt = str(facts.get("prompt") or "")
    words = [w for w in (dial, str(facts.get("dial_word") or "")) if w]
    return any(re.search(r"(?i)(?<![\w-])%s(?![\w-])" % re.escape(w), prompt)
               for w in words)


def count_run(state, facts, rubric):
    """THE RUN COUNTED BEFORE THE FRAMES SEE IT, because the prompt now in hand is
    one of the prompts frame 3 is counting: a window left at a flag-only level says so
    ON the second ordinary prompt, not after it.

    A run is consecutive prompts read at a flag-only level that no ask and no word
    of the user's own covers.  It restarts the moment the dial leaves that level,
    and the run's NUMBER is part of frame 3's token, so one run earns one cue and a
    later run earns its own."""
    flag_only = [str(x).lower() for x in (rubric.get("flag_only_levels") or [])]
    dial = str(facts.get("dial") or "").lower()
    ask = state.get("ask") or {}
    covered = False
    if ask.get("level") and str(ask["level"]).lower() == dial:
        covered = ask.get("span") != "TURN" or int(ask.get("prompts") or 0) < 1
    said_by_user = said_the_level(facts)
    if facts.get("source") == "ran":
        # P12: the RAN road counts REPLIES, not prompts.  A reply is counted once
        # — when it is first seen — and the word that lets it off is the one in
        # the prompt that DREW it, which was the prompt before this one and is
        # carried in the state as `said_level_last`.
        uuid = facts.get("reply_uuid") or ""
        if not uuid or uuid == (state.get("ran_uuid") or ""):
            return state                 # no new reply: nothing to count
        said_by_user = bool(state.get("said_level_last"))
        # P17 — WHAT A TURN ASK COVERS ON THIS ROAD IS THE NEXT REPLY, not the
        # next prompt.  The prompt counter says "1" by the time that reply can be
        # read at all (it is first seen one prompt later), so the LIVE road's
        # `prompts < 1` let the asked-for reply through as unasked and frame 3 fired a
        # reply early on a count that was false.  Here the ask covers exactly the
        # first reply whose uuid differs from the plate's own, and that cover is
        # SPENT on it; a STRETCH ask covers every newer reply while it stands.
        covered = False
        if ask.get("level") and str(ask["level"]).lower() == dial:
            if ask.get("span") == "TURN":
                covered = (uuid != (ask.get("uuid") or "")
                           and not state.get("turn_spent"))
                if covered:
                    state["turn_spent"] = True      # one reply, once
            else:
                covered = True
        if dial and dial in flag_only and not covered and not said_by_user:
            if int(state.get("max_run") or 0) == 0:
                state["max_runs"] = int(state.get("max_runs") or 0) + 1
            state["max_run"] = int(state.get("max_run") or 0) + 1
        elif dial and dial not in flag_only:
            state["max_run"] = 0
        return state
    if dial and dial in flag_only and not covered and not said_by_user:
        if int(state.get("max_run") or 0) == 0:
            state["max_runs"] = int(state.get("max_runs") or 0) + 1
        state["max_run"] = int(state.get("max_run") or 0) + 1
    elif dial and dial not in flag_only:
        state["max_run"] = 0
    return state


def advance(state, facts, rubric, given):
    """The state after this prompt: what the level now reads, which mind is up,
    how far the last ask has travelled, and what has been said."""
    ask = state.get("ask") or {}
    if ask:
        ask = dict(ask)
        ask["prompts"] = int(ask.get("prompts") or 0) + 1
        state["ask"] = ask
    if facts.get("source"):
        state["source"] = facts["source"]
    if facts.get("title"):
        state["title"] = facts["title"]         # phase B's lane check will want it
    if facts.get("source") == "ran" and facts.get("reply_uuid"):
        if facts["reply_uuid"] != (state.get("ran_uuid") or ""):
            state["ran_last"] = facts.get("dial") or ""
            state["ran_uuid"] = facts["reply_uuid"]
    # THE WORD THE PROMPT SAID travels one step with it: on the RAN road the
    # reply this prompt draws is judged by what THIS prompt said (P12).
    state["said_level_last"] = bool(said_the_level(facts))
    named = find_opener(facts.get("prompt"), facts.get("cwd"))
    if named:
        state["opener_named"] = named           # frame 5 answers at the next prompt
    if facts.get("dial"):
        state["dial_last"] = facts["dial"]
    if facts.get("model"):
        state["model_last"] = facts["model"]    # the id is free; the NAME is not
    if facts.get("mind"):
        state["mind_last"] = facts["mind"]      # written when a frame named it
    for frame_id, tok, _text in given:
        state.setdefault("cued", []).append(tok)
        if frame_id == "F1":
            state["first_done"] = True
        if frame_id == "F5":
            state["f5_done"] = True
        if frame_id == "F2" and (state.get("ask") or {}).get("span") == "TURN":
            state["ask_turn_checked"] = True    # a TURN ask is asked about once
    return state


def read_ask(state, facts, rubric):
    """The ASK carried by the reply this prompt answers — recorded with that
    reply's uuid, so the same plate is never read as a new ask twice."""
    ask = state.get("ask") or {}
    uuid = facts.get("reply_uuid") or ""
    if uuid and ask.get("uuid") == uuid:
        return state
    found = parse_ask(facts.get("reply"), rubric)
    if found and uuid:
        found["uuid"] = uuid
        found["prompts"] = 0
        state["ask"] = found
        # TWO FLAGS, TWO MEANINGS, both belonging to the ask that is being
        # replaced: `ask_turn_checked` is "this ask has been asked about once"
        # (frame 2's), `turn_spent` is "this ask's one covered reply has been seen"
        # (the run counter's).  A new plate starts both clean, or an old plate
        # would silence a new one for the rest of the session.
        state["ask_turn_checked"] = False
        state["turn_spent"] = False
    return state


# ══════════════════════════════════════════════════════════════════════════
# No hook blocks a person's prompt or a reply; only a positively identified
# scheduled routine may be refused. Every other road carries a warning.
# THE USAGE LINE — one guarded block.  tools/usage.py owns the meter,
# the settings and the words; this hook only carries its line on the turn-start
# road the dial line opened.  Its switch is "USAGE" in the rubric's `switches` (absent
# = on); a missing usage.py is silence.  Nothing here reaches a network.
# ══════════════════════════════════════════════════════════════════════════

MODEL_WORDS = {"fable": "claude-fable-", "opus": "claude-opus-", "sonnet": "claude-sonnet-",
               "haiku": "claude-haiku-"}


def routine_model(prompt):
    """The model a scheduled run's OWN SKILL.md names (its frontmatter `model:`),
    read from the file its opening tag points at; '' when it names none — and an
    unnamed model is never assumed to be the cheap one."""
    import re
    m = re.match(r'\s*<scheduled-task\b[^>]*\bfile="([^"]+)"', str(prompt or ""))
    if not m:
        return ""
    try:
        with open(m.group(1), encoding="utf-8") as fh:
            head = fh.read(8192)
    except OSError:
        return ""
    if not head.startswith("---"):
        return ""
    for line in head.splitlines()[1:40]:
        if line.strip() == "---":
            break
        if line.lower().startswith("model:"):
            word = line.split(":", 1)[1].strip().lower()
            if word.startswith("claude-"):
                return word
            for key, prefix in MODEL_WORDS.items():
                if word.startswith(key):
                    return prefix
            return word
    return ""


BUTTON_UP_ONLY = "BUTTON UP ONLY — save work, write STATUS/opener, stop tasks and close sessions. No general work."


def closeout_prompt(prompt):
    import re
    choice = " ".join(str(prompt).strip().lower().split())
    choice = re.sub(r"([a-z])\1+", r"\1", choice)
    choice = " ".join(re.sub(r"[.,!?;:]", " ", choice).split())
    return choice in ("buton up", "please buton up", "buton up please", "buton up everything",
                      "please buton up everything", "buton up everything please")


def usage_diagnostic(hub, facts, block):
    """Metadata only. Retention: keep the newest 500 complete lines, drop older lines.

    One bounded file read and an atomic rewrite under a short, bounded lock also
    preserve overlapping windows' lines. No prompt, reply, environment or credentials.
    """
    import time
    mod = sibling("usage.py", "exo_usage")
    rec = mod.paths_record(hub) if mod else {"machine": "unknown"}
    machine = str(rec["machine"])
    if not safe_token(machine):
        machine = "unknown"
    folder = os.path.join(hub, "scratch", "usage-diag")
    mkdirs(folder)
    path = os.path.join(folder, machine + ".jsonl")
    lock = path + ".lock"
    deadline = time.monotonic() + 0.1
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise OSError("diagnostic lock busy")
            time.sleep(0.01)
    try:
        policy = dict(facts.get("policy") or {})
        refused = bool(block) and facts.get("event_name") != "Stop" and hook_say.may_refuse(facts, hook_say.settings_at(hub))
        policy.update(exit=2 if refused and facts.get("usage_stop") else 0,
                      rejected=refused,
                      reason="usage policy rejection" if refused else "admitted by usage policy")
        row = {"at": time.time(), "started_at": facts.get("started_at"), "identity": facts.get("identity") or {},
               "model": facts.get("model_fact") or {}, "attendance": facts.get("attendance"),
               "policy": policy, "session": str(facts.get("session") or "")[:160],
               "cwd": str(facts.get("cwd") or "")[:512], "event": facts.get("event_name"),
               "event_model_present": facts.get("event_model_present"),
               **({"conflict": facts["usage_conflict"]} if facts.get("usage_conflict") else {}),
               "host": str(facts.get("host") or "")[:160], "pid": os.getpid()}
        old = read_text(path, 1024 * 1024).splitlines()[-499:]
        write_atomic(path, "\n".join(old + [json.dumps(row, ensure_ascii=False, sort_keys=True)]) + "\n")
    finally:
        os.unlink(lock)


def usage_frame(state, facts, rubric, hub, state_dir):
    lines, block = _usage_frame_policy(state, facts, rubric, hub, state_dir)
    lines = list(facts.get("usage_prefix") or []) + lines
    if not block:
        lines = list(facts.get("selection_note") or []) + lines
    conflict = facts.get("usage_conflict")
    if conflict:
        mod = sibling("usage.py", "exo_usage")
        line = mod.conflict_line(conflict)
        if block:
            block = line + "\n" + block
        else:
            lines.insert(0, line)
    try:
        usage_diagnostic(hub, facts, block)
    except Exception as exc:
        log_line(state_dir, "USAGE diagnostic unavailable: %s" % type(exc).__name__)
    return lines, block


def _usage_frame_policy(state, facts, rubric, hub, state_dir):
    """(lines, block reason or None) for this prompt.  PAUSE, WARN and CONTINUED
    lines ride every turn; a stale meter's age line rides every turn while its last
    reading was over WARN, else on the turn it went stale and then every
    refresh_turns turns; no meter at all is said every refresh_turns turns.  A
    scheduled run under an unsigned PAUSE that reaches its model is BLOCKED
    (block_routines); an applicable unexpired signature continues it. Unattended
    flagship/unknown work at STOP remains blocked regardless of signatures.
    The PAUSE onset and the WARN crossing each raise their one notice
    through usage.py's announce(), and a «continue» that expired with its reset is
    said ONCE, at a turn a person typed — never spent on a run nobody reads.
    The verdict reads THIS window's login's meter — the login that owns its
    transcript, else the app's signed-in login — and the line names it; with no meter for
    that login the line says `refresh` and whose reading is the newest here."""
    mod = sibling("usage.py", "exo_usage")
    if mod is None:
        return ["USAGE meter unavailable — usage.py unreadable; prompt runs"], None
    rec = mod.paths_record(hub)
    cfg, _missing = mod.load_settings(rec["hub"])
    # ASSUMES: unattended work may consume an applicable PAUSE signature, but
    # cannot sign one or lift flagship STOP. Opposite: attended typed admission.

    prompt = str(facts.get("prompt") or "")
    scheduled = prompt.lstrip().startswith("<scheduled-task")
    login = None
    identity_how, identity_account = "none", ""
    if hasattr(mod, "session_login"):              # the window's own login
        try:
            login, identity_how, identity_account = mod.session_login(rec["roots"], rec["hub"],
                                      transcript=facts.get("transcript") or None,
                                      session=facts.get("session") or None, fallback=True,
                                      env=dict(os.environ, CLAUDE_CODE_ENTRYPOINT="claude-desktop")
                                      if facts.get("desktop") else None)
        except Exception as exc:
            log_line(state_dir, "USAGE login: %r" % (exc,))
    facts["identity"] = {"account": identity_account, "login": login,
                         "source": mod.source_word(identity_how)}
    model = routine_model(prompt) if scheduled else str(facts.get("model") or "")
    if scheduled:
        # R14: policy and diagnostics use the routine's declared selection;
        # an unrelated app record or old reply cannot replace that model.
        facts["model"] = model
        facts["model_source"] = "routine"
        facts["model_fact"] = dict(facts.get("model_fact") or {}, value=model,
                                   source="routine definition" if model else "none",
                                   at=None, age_seconds=None,
                                   reason="routine definition" if model else "routine model missing")
    if login:
        verdict = mod.evaluate(rec["hub"], "claude", model=model or None, cfg=cfg,
                               machine=rec["machine"], prune=not bool(facts.get("transcript")), login=login,
                               login_source="window" if facts.get("desktop")
                               and mod.source_word(identity_how) == "app" else None)
    else:
        verdict = mod.evaluate(rec["hub"], "claude", model=model or None, cfg=cfg,
                               machine=rec["machine"], prune=not bool(facts.get("transcript")))
    # Preserve exactly the verdict's selected file before own-tail import overwrites it.
    # ASSUMES: another login's unrelated file is not a reading of this window.
    # The replay gate also forces a wrongly selected foreign file (the 09:09 defect).
    if facts.get("transcript"):
        try:
            selected = mod.read_json(verdict["meter"], None) if verdict.get("meter") else None
            evidence = {}
            mod.meter_from_tail(rec["hub"], rec["roots"], rec["machine"], facts["transcript"],
                                selected_meter=selected, evidence=evidence)
            if evidence:
                facts["usage_conflict"] = evidence
                # Re-resolve from the window, never retain a file's mistaken login.
                login, identity_how, identity_account = mod.session_login(
                    rec["roots"], rec["hub"], transcript=facts["transcript"],
                    session=facts.get("session") or None, fallback=True)
                facts["identity"] = {"account": identity_account, "login": login,
                                     "source": mod.source_word(identity_how)}
            verdict = mod.evaluate(rec["hub"], "claude", model=model or None, cfg=cfg,
                                   machine=rec["machine"], login=login,
                                   login_source="window" if facts.get("desktop")
                                   and mod.source_word(identity_how) == "app" else None)
        except Exception as exc:
            log_line(state_dir, "USAGE tail: %r" % (exc,))
    # ASSUMES: app saves can exceed 3 s. R8 bounds the combined reads; R9
    # persists one residual admission per session/mtime. Opposite: repeated
    # prompts against the SAME unchanged cheap record must stop.
    # ASSUMES: an old cheap reply is useful only BELOW the stop line (R10);
    # absent/conflicting/delayed records with undated events are gated.
    # Only a cheap app-record selection at the flagship stop needs this newer-write
    # check. Live events, flagship records and below-stop meters never wait here.
    model_fact = facts.get("model_fact") or {}
    record = model_fact.get("record") or {}
    selection_note = []
    _path, data = mod.newest_meter(rec["hub"], rec["machine"], "claude",
                                  login=login, account=identity_account or None)
    stopped = mod.hard_stop(rec["hub"], "claude", data, cfg, mod.now_local())
    # R14: a routine's definition supplies its own policy model. R10 applies
    # only to an ATTENDED selection that actually fell back to an old reply.
    # ASSUMES: transcript provenance does not describe a scheduled definition;
    # opposite: a cheap routine at the flagship stop keeps its own plan pause.
    if (not scheduled and facts.get("desktop")
            and stopped and model_fact.get("source") == "last reply" and model and mod.flagship_name(
            rec["hub"], "claude", model) != stopped[3]):
        model = ""
        facts["model"] = ""
        facts["model_source"] = "unknown"
        model_fact.update(value="", source="none", reason="old cheap reply unvalidated at stop line")
        verdict = mod.evaluate(rec["hub"], "claude", model=None, cfg=cfg,
                               machine=rec["machine"], login=login,
                               login_source="window" if facts.get("desktop")
                               and mod.source_word(identity_how) == "app" else None)
    if model_fact.get("source") == "app record" and model and record.get("mtime") is not None:
        _path, data = mod.newest_meter(rec["hub"], rec["machine"], "claude",
                                      login=login, account=identity_account or None)
        stopped = mod.hard_stop(rec["hub"], "claude", data, cfg, mod.now_local())
        if stopped and mod.flagship_name(rec["hub"], "claude", model) != stopped[3]:
            event = {"session_id": facts["session"], "cwd": facts["cwd"],
                     "timestamp": facts.get("event_timestamp")}
            if facts.get("desktop"):
                event["entrypoint"] = "claude-desktop"
            fresh = desktop_model_fact(event, newer_than=record["mtime"],
                                       deadline=facts.get("model_deadline"))
            fresh["initial_readiness_ms"] = model_fact.get("readiness_ms", 0.0)
            fresh["refresh_ms"] = fresh["readiness_ms"]
            fresh["readiness_ms"] = round(fresh["readiness_ms"] + fresh["initial_readiness_ms"], 3)
            facts["model_fact"] = fresh
            model = fresh["value"]
            facts["model"] = model
            facts["model_source"] = "app" if model else "unknown"
            facts["family"] = vendor_family(facts["kind"], model)
            facts["dial_word"] = dial_word(rubric, facts["family"], facts.get("dial"))
            verdict = mod.evaluate(rec["hub"], "claude", model=model or None, cfg=cfg,
                                   machine=rec["machine"], login=login,
                                   login_source="window" if facts.get("desktop")
                                   and mod.source_word(identity_how) == "app" else None)
            if fresh.get("refresh_timed_out") and model and mod.flagship_name(
                    rec["hub"], "claude", model) != stopped[3]:
                latch = {"session": facts["session"], "record_mtime": fresh["record"]["mtime"]}
                # Exclusive creation makes concurrent hooks share the same admission.
                # ASSUMES: the state filesystem supports O_EXCL; an unavailable store
                # is conservative (unknown/flagship), never another residual turn.
                import hashlib
                marker_dir = os.path.join(str(state_dir), "usage-residual", facts["session"])
                marker = os.path.join(marker_dir, hashlib.sha256(
                    repr(latch["record_mtime"]).encode("ascii")).hexdigest() + ".json")
                admitted = False
                refusal = "unchanged record residual already admitted"
                try:
                    mkdirs(marker_dir)
                    fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    with os.fdopen(fd, "w", encoding="utf-8") as receipt:
                        receipt.write(json.dumps(latch) + "\n")
                    admitted = True
                except FileExistsError:
                    pass
                except OSError:
                    refusal = "residual admission state unavailable"
                state["usage_residual_admission"] = latch
                if not admitted:
                    facts["residual_exhausted"] = True
                    model = ""
                    facts["model"] = ""
                    facts["model_source"] = "unknown"
                    fresh.update(value="", source="none", reason=refusal)
                    verdict = mod.evaluate(rec["hub"], "claude", model=None, cfg=cfg,
                                           machine=rec["machine"], login=login,
                                           login_source="window" if facts.get("desktop")
                                           and mod.source_word(identity_how) == "app" else None)
                else:
                    # The exclusive marker is durable before the admission returns.
                    selection_note = ["admitted as %s — a switch to %s saved after this check warns on the next turn; "
                                      "a save slower than 3 s under load can admit ONE flagship turn; "
                                      "the warning rides every typed turn; the record is read again next turn" % (model, stopped[3])]
    if (verdict.get("risk_confirmation") and verdict.get("age_min") is not None
            and verdict["age_min"] > float(cfg["stale_minutes"])):
        import re
        verdict["lines"] = [re.sub(r"[0-9.]+ percent of the week", "refresh", line)
                            for line in verdict.get("lines") or []]
    facts["policy"] = {"level": verdict.get("level"), "pause": bool(verdict.get("pause")),
                       "login_source": verdict.get("login_source")}
    attended = facts.get("attendance") != "scheduled"
    provisional = attended and facts["identity"]["source"] in ("window", "app")
    # R9 still records model-readiness history; it cannot silence the provisional note.
    machine = facts.get("attendance") == "scheduled"
    unknown_note = (["model not yet readable — judged as the flagship this turn"]
                    if attended and not model else [])
    provisional_note = (["judged by the app's sign-in %s until this window's own record lands" %
                         (login or "unknown")] if provisional else [])
    facts["selection_note"] = selection_note
    prefix = unknown_note + provisional_note
    if attended and not verdict.get("lines"):
        missing = []
        if not login:
            missing.append("login unknown")
        if verdict.get("level") == "none":
            missing.append("meter unavailable")
        elif verdict.get("level") in ("stale", "stale-pause"):
            missing.append("meter stale")
        if missing:
            prefix.append("USAGE %s — refresh; prompt runs" % "; ".join(missing))
    closeout = closeout_prompt(prompt)
    # R11: invoke the existing once-per-onset notifier/letter road BEFORE any
    # manual rejection. Keep detached delivery: a slow notifier cannot spend the hook budget.
    if verdict.get("level") == "manual" or (provisional and cfg.get("manual_pause")):
        onset = verdict
        if verdict.get("level") != "manual":
            # Provisional stale identity can return before evaluate's manual branch;
            # the explicit manual rejection below still owes the same onset road.
            onset = dict(verdict, level="manual", pause=True,
                         key="manual|%s" % cfg["manual_pause_at"] if cfg.get("manual_pause_at") else "manual",
                         meter_words="manual pause", question=mod.MANUAL_TAIL,
                         lines=["USAGE PAUSE — manual pause is on (usage-settings.json) · " + mod.MANUAL_TAIL])
        said = mod.announce(rec["hub"], onset, rec["machine"])
        if said not in ("already", "none"):
            log_line(state_dir, "USAGE manual announce: %s" % said)
    # STOP is attendance-specific here; evaluate's CLI confirmation contract stands.
    if not attended and stopped and (not model or mod.flagship_name(rec["hub"], "claude", model) == stopped[3]):
        facts["usage_stop"] = True
        return [], stopped[2]
    # ASSUMES: a person who typed a prompt wants it to run; the gate's job is the one warning line. Opposite: a routine (R3).
    if attended:
        facts.pop("usage_stop", None)
        n = mod.now_local()
        lines = list(verdict.get("lines") or [])
        # stop_window remains history even after a newer reading falls below the line.
        # A provisional stale sign-in still says refresh instead of a percent.
        if stopped:
            pct, window, _hard_line, name = stopped
            age = verdict.get("age_min")
            stale = age is None or age > float(cfg["stale_minutes"])
            refresh = stale and (provisional or bool(verdict.get("risk_confirmation")))
            lines = [mod.flagship_warning(name, pct, window, login, verdict.get("login_source"),
                                         age, n, refresh=refresh)]
            if verdict.get("level") in ("auto-pause", "manual"):
                lines += [line for line in verdict.get("lines") or []
                          if " HARD STOP — " not in line and " USAGE WARNING — " not in line]
        if provisional and cfg.get("manual_pause") and verdict.get("level") != "manual":
            lines.append("USAGE PAUSE — manual pause is on (usage-settings.json) · " + mod.MANUAL_TAIL)
        choice = " ".join(prompt.strip().lower().split())
        # A whole typed choice signs only this login's flagship week at/above PAUSE.
        eligible = []
        if stopped:
            eligible = [{"window": stopped[1], "percent": stopped[0]}]
        else:
            _warn, pause = mod.thresholds(cfg, "claude")
            for w in (data or {}).get("windows") or []:
                reset = mod.parse_iso(w.get("resets_at"))
                try:
                    pct = float(w.get("percent"))
                except (TypeError, ValueError):
                    continue
                name = mod.flagship_name(rec["hub"], "claude", w.get("model"))
                if not name and not w.get("model"):
                    for word in str(w.get("label") or "").split():
                        name = mod.flagship_name(rec["hub"], "claude", word)
                        if name:
                            break
                if (w.get("kind") == "week-model" and name
                        and pct >= pause and (reset is None or reset > n)):
                    eligible.append({"window": w, "percent": pct})
        lines = [line.replace(mod.SESSION_TAIL,
                 "the hook records a typed «continue»; «button up» runs the standing button-up")
                 for line in lines]
        if choice in ("continue", "continue at my risk", "take risks and continue") and eligible:
            # Sign only after the genuine PAUSE onset has taken its existing
            # once-only notice/button-up road. STOP is warning-only, no onset.
            if (not stopped and verdict.get("pause")
                    and verdict.get("level") in ("pause", "stale-pause")
                    and switch_on(rubric, "USAGE")):
                said = mod.announce(rec["hub"], verdict, rec["machine"])
                if said not in ("already", "none"):
                    log_line(state_dir, "USAGE pause announce: %s" % said)
            try:
                rows = mod.record_override(rec["hub"], "claude", eligible,
                       facts.get("title") or state.get("title") or mod.find_title(rec["roots"], facts.get("session") or "")
                       or "typed in %s" % str(facts.get("session") or "unknown")[:8],
                       (data or {}).get("spend"), n)
                lines += [mod.risk_receipt(row, n) for row in rows]
            except Exception as exc:
                # No wait or retry: a failed receipt is context; the typed prompt still runs.
                reason = " ".join(str(exc).split())[:160] if isinstance(exc, ValueError) else type(exc).__name__
                lines.append("RISK ACKNOWLEDGED — not recorded (%s)" % reason)
        elif verdict.get("risk_confirmation") and verdict.get("override"):
            lines = [line for line in lines if not line.startswith("RISK ACKNOWLEDGED")]
            lines.append(mod.risk_receipt(verdict["override"], n))
        if (stopped or verdict.get("level") in ("manual", "auto-pause")
                or verdict.get("risk_confirmation") or verdict.get("risk_confirmation_blocked")
                or len(lines) > len(verdict.get("lines") or [])):
            if verdict.get("level") == "auto-pause":
                mod.announce(rec["hub"], verdict, rec["machine"])
            return prefix + lines, None
    if provisional and cfg.get("manual_pause"):
        manual_line = "USAGE PAUSE — manual pause is on (usage-settings.json) · " + mod.MANUAL_TAIL
        if closeout:
            return prefix + [manual_line, BUTTON_UP_ONLY], None
        facts["usage_stop"] = True
        return [], manual_line + "\n" + "\n".join(prefix)
    if verdict.get("level") == "stop":
        if provisional:
            warning = ("USAGE WARNING — login %s · read %s; this provisional app sign-in "
                       "reading is at or over the pause line. Choose: button up, or continue at my risk." %
                       (login or "unknown", mod.ago_words(verdict.get("age_min"))))
            return [warning] + prefix + ["CLOSEOUT OR CHOICE ONLY — No general work. Choose button up, or continue at my risk.",
                "button up saves work and closes sessions; continue at my risk requires the signed continuation for this login and reset."], None
        facts["usage_stop"] = True
        return [], "\n".join(list(verdict.get("lines") or [])[:1] + prefix)
    # R12: the plan-window latch is still policy after own-tail wins. A conflict
    # is printed by usage_frame beside these lines; it never admits general work.
    if verdict.get("level") == "auto-pause" and isinstance((data or {}).get("auto_pause_window"), dict):
        mod.announce(rec["hub"], verdict, rec["machine"])
        if closeout and not machine:
            return prefix + list(verdict.get("lines") or []) + [BUTTON_UP_ONLY], None
        facts["usage_stop"] = True
        return [], "\n".join(list(verdict.get("lines") or []) + prefix)
    if verdict.get("level") == "manual" or verdict.get("risk_confirmation_blocked"):
        if verdict.get("level") == "manual" and closeout and not machine:
            return prefix + list(verdict.get("lines") or []) + [BUTTON_UP_ONLY], None
        facts["usage_stop"] = True
        return [], "\n".join(list(verdict.get("lines") or []) + prefix)
    if verdict.get("risk_confirmation"):
        lines = list(verdict.get("lines") or [])
        name = mod.flagship_name(rec["hub"], "claude", model) if model else ""
        if not attended or (name and name != verdict.get("risk_flagship")):
            facts["usage_stop"] = True
            return [], lines[0] + " An attended user choice is required; this automated or unidentified turn is blocked."
    # Carry the conservative-model note below the pause line as well.
    facts["usage_prefix"] = prefix
    if not switch_on(rubric, "USAGE"):
        return ([verdict["stop_line"]] if verdict.get("stop_line") else []), None
    if (verdict.get("pause") or verdict.get("warn_key") or verdict.get("level") == "warn"
            or verdict.get("auto_lifted_key")):             # the auto-pause lifted notice
        said = mod.announce(rec["hub"], verdict, rec["machine"])
        if said not in ("already", "none"):
            log_line(state_dir, "USAGE announce %s: %s"
                     % (verdict.get("key") or verdict.get("warn_key"), said))
        if verdict.get("pause") and not attended and cfg.get("block_routines", True):
            return [], "%s — this scheduled run was stopped before its first model call (BQ-145)" \
                % (verdict.get("lines") or ["USAGE PAUSE"])[0]
    notes = []
    if not unattended(prompt) and hasattr(mod, "notes_once"):
        try:
            notes = list(mod.notes_once(rec["hub"], verdict) or [])
        except Exception as exc:
            log_line(state_dir, "USAGE notes: %r" % (exc,))
    turns = int(state.get("usage_turns") or 0) + 1
    state["usage_turns"] = turns
    # A5: the verdict carries how often the refresh nag rides (2 turns at or above PAUSE,
    # 10 below); this file holds no number of its own for it
    every = max(1, int(float(verdict.get("refresh_every") or cfg.get("refresh_turns") or 10)))
    level = verdict.get("level")
    before = state.get("usage_level_last")
    state["usage_level_last"] = level
    if verdict.get("stop_line"):
        return notes + list(verdict.get("lines") or []), None
    if level in ("pause", "stale-pause", "manual", "warn", "continued", "auto-pause"):
        state["usage_nag_at"] = turns
        lines = list(verdict.get("lines") or [])
        if level in ("pause", "continued", "auto-pause") and verdict.get("refresh_line"):
            last_r = int(state.get("usage_refresh_at") or 0)
            if not last_r or turns - last_r >= every:    # the 97 watch is never blind
                state["usage_refresh_at"] = turns
                lines.append(verdict["refresh_line"])
        return notes + lines, None
    if level == "stale":
        went = before != "stale"
        last = int(state.get("usage_nag_at") or 0)
        if verdict.get("warned") or went or turns - last >= every:
            state["usage_nag_at"] = turns
            return notes + list(verdict.get("lines") or []), None
        return notes, None
    if level == "none":
        last = int(state.get("usage_nag_at") or 0)
        if not last or turns - last >= every:
            state["usage_nag_at"] = turns
            return notes + (list(verdict.get("lines") or []) or [mod.NO_METER_LINE]), None
    return notes, None


def hook_main(argv):
    """`effort.py --hook`: read the event's stdin, print the cue, write the state.

    THE MAIN-THREAD RULE IS ABSOLUTE: an input carrying `agent_id` fires inside a
    subagent call and gets NOTHING, on every event — a cue must never land in a
    builder's context.  A SessionStart prints nothing at all; it is here only to
    learn the mind and the dial before the first prompt."""
    import time
    cfg = hook_say.settings_at(argv_value(argv, "--hub") or hub_dir(None))
    started = time.time()
    model_deadline = time.monotonic() + 3.0
    state_dir = argv_value(argv, "--state-dir")
    vendor = argv_value(argv, "--vendor") or "claude"
    hub = argv_value(argv, "--hub")
    try:
        raw = sys.stdin.read(STDIN_CAP)
    except Exception:
        return 0
    try:
        event = json.loads(raw) if raw.strip() else {}
        if not isinstance(event, dict):
            return 0
    except Exception:
        return 0
    if event.get("agent_id"):
        return 0                                   # inside a subagent: never
    name = str(event.get("hook_event_name") or "").strip()
    session = str(event.get("session_id") or "").strip()
    # A VENDOR WITH NO MAP OF ITS OWN IS SILENT (P5).  Codex's map is empty on
    # purpose — its hook is off until its probe passes, and the installer says so
    # — and an empty map must not borrow another vendor's events: a tool that
    # answers for a vendor it was told not to answer for is a lie on the surface.
    events = HOOK_EVENTS.get(vendor) or {}
    if not session or name not in events:
        return 0
    if not state_dir:
        return 0                                   # no state dir named: nothing to do
    if not safe_token(session):
        log_line(state_dir, "%s: a session id that is not a plain token was dropped" % name)
        return 0
    try:
        law = read_law(state_dir=state_dir)
        rubric, _note = load_rubric(hub_dir(hub), law)
        facts = hook_facts(event, vendor, rubric, state_dir, model_deadline=model_deadline)
        facts["started_at"] = started
        state = load_state(state_dir, session)
        if name == "SessionStart":
            # The one event where naming the mind IS the work: it happens once a
            # session, and the first prompt then finds the name already written.
            if facts.get("dial"):
                state["dial_last"] = facts["dial"]
            if facts.get("model"):
                state["model_last"] = facts["model"]
            if facts_mind(facts):
                state["mind_last"] = facts["mind"]
            save_state(state_dir, session, state)
            # THE LAW BOOK AS THIS SESSION WOKE TO IT: the app builds a
            # session's context from the file at every start, resume, clear and
            # compaction, so the snapshot is taken again at every one of them.
            if switch_on(rubric, "LAW"):
                try:
                    snapshot_law(state_dir, session, why=str(event.get("source") or "start"))
                except Exception as exc:
                    log_line(state_dir, "%s: law snapshot: %r" % (name, exc))
            return 0                               # SessionStart never speaks
        state = read_ask(state, facts, rubric)
        state = count_run(state, facts, rubric)
        if time.time() - started - float((facts.get("model_fact") or {}).get("readiness_ms") or 0) / 1000 > SOFT_BUDGET_S:
            log_line(state_dir, "%s: past the soft budget before the frames" % name)
            return hook_say.emit(name, ["USAGE unknown — hook budget exhausted before meter check; prompt runs"], facts=facts, settings=cfg)
        # A SCHEDULED RUN IS ANSWERED WITH SILENCE, AND THE STATE STILL MOVES
        # (P2): no frame is computed and no token is spent, but `advance` below
        # still records the dial, the model and the ask's travel, so the next
        # prompt a person types is read against the truth.
        quiet = facts.get("attendance") == "scheduled"
        # The usage line, and a scheduled run's block under a PAUSE.
        usage_lines, block = [], None
        try:
            usage_lines, block = usage_frame(state, facts, rubric, hub_dir(hub), state_dir)
        except Exception as exc:
            log_line(state_dir, "%s: usage: %r" % (name, exc))
            usage_lines = ["USAGE unknown — meter check failed (%s); prompt runs" % type(exc).__name__]
        if block:
            save_state(state_dir, session, state)
            return hook_say.emit(name, usage_lines, refusal=block, facts=facts, settings=cfg, hard=bool(facts.get("usage_stop")))
        if quiet:                                  # a run nobody typed hears only a PAUSE
            usage_lines = [l for l in usage_lines if l.startswith("USAGE PAUSE") or " HARD STOP — " in l
                           or l.startswith("AUTO-PAUSE —") or l.startswith("CONFLICT —")]
        given = [] if quiet else cues(state, facts, rubric, law)
        # THE TURN-START LINES, ahead of every frame: the
        # dial FIRST, then a plate that disagreed with it, then the law book.
        # The dial and the plate are about the person's dial and are silent on
        # a run nobody typed; the law line is the session's own rule book and
        # is said on any prompt.  Each has its own switch in the rubric.
        head, extra = [], []
        if not quiet and switch_on(rubric, "DIAL"):
            head.append(dial_line(facts, rubric))
        if not quiet and switch_on(rubric, "PLATE") and facts.get("transcript"):
            facts["turn"] = last_turn(tail_records(facts["transcript"]))
            plate = plate_frame(state, facts, rubric)
            if plate and plate[1] not in set(state.get("cued") or []):
                extra.append(plate)
        law_text, law_snap = "", None
        if switch_on(rubric, "LAW"):
            law_text, law_snap = law_frame(state_dir, session)
        conflicts = [line for line in usage_lines if line.startswith("CONFLICT —")]
        usage_lines = [line for line in usage_lines if not line.startswith("CONFLICT —")]
        lines = conflicts + head + usage_lines + [f[2] for f in extra] + ([law_text] if law_text else []) \
            + [frame[2] for frame in given]
        hook_say.emit(name, lines, facts=facts, settings=cfg)
        if law_snap is not None:                   # written AFTER the line is out:
            write_atomic(wake_file(state_dir, session),  # a kill between costs one
                         json.dumps(law_snap, ensure_ascii=False,  # repeat, never a loss
                                    sort_keys=True) + "\n")
        given = extra + given
        state = advance(state, facts, rubric, given)
        save_state(state_dir, session, state)
        for frame in given:
            log_line(state_dir, "CUE %s %s" % (frame[0], session))
        if law_text:
            log_line(state_dir, "CUE LAW %s" % session)
    except Exception as exc:
        log_line(state_dir, "%s: %r" % (name, exc))
        return hook_say.emit(name, ["HOOK unknown — %s failed (%s); prompt runs" % (name, type(exc).__name__)], settings=cfg)
    return 0


def argv_value(argv, flag):
    for index, item in enumerate(argv):
        if item == flag and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(flag + "="):
            return item.split("=", 1)[1]
    return ""


# ══════════════════════════════════════════════════════════════════════════
# --replay — read-only, writes nothing at all
# ══════════════════════════════════════════════════════════════════════════

def replay(paths, state_dir, hub=None, show_silent=False, first_words=12):
    """Walk saved transcripts prompt by prompt and print the cues that WOULD have
    been given.  IT WRITES NOTHING — not the state dir, not the log, not a cache:
    the state lives in memory for the length of the walk, which is what makes
    this safe to point at the real record.

    THE DIAL AT A PROMPT is the effort of the reply that prompt drew, because
    that is what the window was set to when the hook would have fired; a prompt
    with no reply after it is read at the dial that stood before it."""
    law = read_law(state_dir=None, cache=False)
    rubric, _note = load_rubric(hub_dir(hub), law)
    totals = {"prompts": 0, "cued": 0, "files": 0, "scheduled": 0}
    by_frame = {}
    hits = []
    machine = [0]
    skipped = []
    for path in paths:
        # A FILE TOO BIG TO WALK IS NAMED, NOT DROPPED (P4): the walk is bounded,
        # and a bound that hides what it left out is a lie by omission.
        try:
            if os.path.getsize(path) > WALK_CAP:
                skipped.append(path)
                continue
        except OSError:
            pass
        rows = walk_transcript(path, machine_prompts=machine)
        if not rows:
            continue
        totals["files"] += 1
        session = os.path.basename(path).rsplit(".", 1)[0]
        state = fresh_state()                     # in memory only: nothing is written
        for row in rows:
            # THE REPLAY WALKS THE ROAD THE HOOK ACTUALLY HAS: the level
            # the last reply ran at, one reply behind, exactly as the installed
            # hook reads it on this app version.
            facts = {"session": session, "prompt": row["prompt"], "cwd": row["cwd"],
                     "transcript": path, "dial": row["ran"], "kind": "claude",
                     "source": "ran" if row["ran"] else "unknown",
                     "family": row["family"], "model": row["model"],
                     "reply": row["reply"], "reply_uuid": row["reply_uuid"]}
            facts["dial_word"] = dial_word(rubric, facts["family"], facts["dial"])
            state = read_ask(state, facts, rubric)
            state = count_run(state, facts, rubric)
            # A scheduled run gets no cue and is counted apart (P2) — the state
            # still advances, exactly as it does at the hook.
            if unattended(row["prompt"]):
                totals["scheduled"] += 1
                state = advance(state, facts, rubric, [])
                continue
            given = cues(state, facts, rubric, law)
            totals["prompts"] += 1
            if given:
                totals["cued"] += 1
            for frame_id, _tok, text in given:
                by_frame[frame_id] = by_frame.get(frame_id, 0) + 1
                if frame_id in ("F3", "F4"):
                    hits.append((frame_id, os.path.basename(path), row["when"],
                                 " ".join(str(row["prompt"]).split()[:first_words]),
                                 text))
                print("%s %s %s" % (os.path.basename(path)[:8], row["when"][11:19], text))
            if show_silent and not given:
                print("%s %s (silent) %s" % (os.path.basename(path)[:8], row["when"][11:19],
                                             " ".join(row["prompt"].split()[:8])))
            state = advance(state, facts, rubric, given)
    silent = totals["prompts"] - totals["cued"]
    share = (100.0 * silent / totals["prompts"]) if totals["prompts"] else 100.0
    line = ("replay: %d files · %d prompts · silent %d (%.1f%%) · %s · %d app-injected "
            "prompts counted out · %d scheduled runs counted out"
            % (totals["files"], totals["prompts"], silent, share,
               " · ".join("%s %d" % (k, by_frame[k]) for k in sorted(by_frame)) or "no cues",
               machine[0], totals["scheduled"]))
    if skipped:
        line += " · %d file(s) over %d MB skipped" % (len(skipped), WALK_CAP >> 20)
    print(line)
    for path in skipped:
        print("  skipped (over %d MB): %s" % (WALK_CAP >> 20, path))
    for frame_id, where, when, words, _text in hits:
        print("  %s %s %s  %s" % (frame_id, where[:8], when[:19], words))
    return 0


def walk_transcript(path, cap=WALK_CAP, machine_prompts=None):
    """[{prompt, when, effort, model, reply, ...}] — one row per MAIN-THREAD
    prompt A PERSON TYPED, in order, with the reply before it and the effort of
    the reply after it.  Read-only and bounded; a torn line is skipped.

    `machine_prompts` is a one-cell list the caller passes to learn how many
    app-injected prompts were counted out."""
    rows = []
    machine_prompts = machine_prompts if machine_prompts is not None else [0]
    try:
        size = os.path.getsize(path)
    except OSError:
        return rows
    if size > cap:
        return rows
    last_reply = {"text": "", "uuid": "", "model": "", "effort": ""}
    pending = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(rec, dict) or rec.get("isSidechain"):
                    continue
                kind = rec.get("type")
                if kind == "assistant":
                    message = rec.get("message") or {}
                    blocks = message.get("content") or []
                    body = ""
                    if isinstance(blocks, list):
                        body = "".join(b.get("text", "") for b in blocks
                                       if isinstance(b, dict) and b.get("type") == "text")
                    if pending is not None:
                        pending["effort"] = str(rec.get("effort") or pending["effort"])
                        pending["model"] = str(message.get("model") or pending["model"])
                        rows.append(pending)
                        pending = None
                    if body.strip():
                        last_reply = {"text": body, "uuid": str(rec.get("uuid") or ""),
                                      "model": str(message.get("model") or ""),
                                      "effort": str(rec.get("effort") or ""),
               "timestamp": rec.get("timestamp")}
                    continue
                if kind != "user" or not rec.get("promptSource"):
                    continue
                # THE RECORD SAYS WHOSE PROMPT IT IS: a human's carries
                # origin.kind "human"; the app's own injections (a task
                # notification, a scheduled task's run) carry promptSource
                # "system" and their own origin kind.  A cue is for the person's
                # prompt, so the walk counts those apart.
                origin = rec.get("origin") if isinstance(rec.get("origin"), dict) else {}
                human = (str(origin.get("kind") or "") == "human"
                         or (not origin and str(rec.get("promptSource")) != "system"))
                if not human:
                    machine_prompts[0] += 1
                    continue
                content = (rec.get("message") or {}).get("content")
                if isinstance(content, list):
                    text = "".join(b.get("text", "") for b in content
                                   if isinstance(b, dict) and b.get("type") == "text")
                elif isinstance(content, str):
                    text = content
                else:
                    continue
                if not text.strip():
                    continue
                if pending is not None:
                    rows.append(pending)
                pending = {"prompt": text, "when": str(rec.get("timestamp") or ""),
                           "cwd": str(rec.get("cwd") or ""),
                           # `ran` is the level the reply BEFORE this prompt ran
                           # at — what a hook could read at that moment — and is
                           # never overwritten; `effort` is the level the reply
                           # this prompt DREW ran at, which no hook can see.
                           "ran": last_reply.get("effort") or "",
                           "effort": last_reply.get("effort") or "",
                           "model": last_reply.get("model") or "",
                           "reply": last_reply.get("text") or "",
                           "reply_uuid": last_reply.get("uuid") or ""}
    except (OSError, ValueError):
        return rows
    if pending is not None:
        rows.append(pending)
    for row in rows:
        row["family"] = vendor_family("claude", row.get("model"))
    return rows


# ══════════════════════════════════════════════════════════════════════════
# --rubric, --weigh, --status — every one of them writes nothing
# ══════════════════════════════════════════════════════════════════════════

def print_rubric(hub, check=False, home=None, state_dir=None):
    law = read_law(state_dir=None, home=home, cache=False)
    path = rubric_path(hub_dir(hub))
    data = read_json(path, None) if os.path.isfile(path) else None
    using_file = isinstance(data, dict)
    rubric = data if using_file else dict(SEED)
    fault = rubric_fault(rubric, law) if using_file else ""
    if check:
        if fault:
            print("REFUSED: %s" % fault)
            return 1
        if not law.get("readable"):
            print("law floor unreadable (%s) — the judgment floors could not be "
                  "checked, and nothing here reads as passed"
                  % (law.get("why") or "the paragraph no longer parses"))
            return 1
        print("rubric ok: %s · %d kinds · floors read from the law (%s; never %s)"
              % (os.path.basename(path) if using_file else "the built-in seed",
                 len(rubric.get("kinds") or []), law.get("floor") or "—",
                 ", ".join(law.get("flagged") or []) or "—"))
        return 0
    print("EFFORT RUBRIC — %s%s"
          % (path if using_file else "the built-in seed",
             "  (REFUSED: %s — the seed is in use)" % fault if fault else ""))
    print("the law's own floors: judgment goes to %s, never %s%s"
          % (law.get("floor") or "—", ", ".join(law.get("flagged") or []) or "—",
             "" if law.get("readable") else "   [law floor unreadable]"))
    road = newest_source(state_dir) if state_dir else ""
    print("the frames on this machine speak of: %s"
          % ("the dial, as the app hands it" if road == "live" else
             "the level your last reply RAN at — this app hands a hook no dial"
             if road == "ran" else
             "the dial where the app supplies one, else the level the last reply "
             "ran at (no session seen yet)"))
    print("")
    for row in (rubric.get("kinds") or []):
        if not isinstance(row, dict):
            continue
        never = list(row.get("never") or [])
        if row.get("never_law") and law.get("flagged"):
            never = never + ["%s (law)" % m for m in law["flagged"]]
        level = row.get("level") or "—"
        if row.get("level_note"):
            level = "%s — %s" % (level, row["level_note"]) if row.get("level") \
                else row["level_note"]
        print("%-18s %s" % (row.get("name") or row.get("id"), row.get("ask") or ""))
        print("%-18s mind: %s" % ("", row.get("mind_note")
                                  or ", ".join(row.get("minds") or []) or "—"))
        if never:
            print("%-18s never: %s" % ("", ", ".join(never)))
        print("%-18s dial: %s" % ("", level))
        print("%-18s flag: %s" % ("", row.get("flag") or "none"))
        print("%-18s source: %s%s" % ("", row.get("source") or "—", cells_note(row)))
        print("")
    print("flag-only levels: %s · overstay after %s prompts"
          % (", ".join(str(x) for x in (rubric.get("flag_only_levels") or [])) or "—",
             (rubric.get("thresholds") or {}).get("max_overstay_prompts")))
    print("modifiers (the law's own): ships to work or bakes in → the judging mind is "
          "the floor · quota short → judgment steps down to the other judging mind, "
          "never a cheaper one · unsure of the stakes → one question, never a guess "
          "downward · \"a wrong 'Opus' costs quality that ships, a wrong 'Fable' only "
          "costs quota.\"")
    return 0


def weigh(target, kind, hub, home=None):
    """--weigh: the evidence for a walk, printed and never written.

    IT NEVER COMPOSES THE SET LINE.  The law wants the model line walked in the
    handing session's own words; a line generated here would be a copy by another
    name, which is the very thing the law forbids."""
    law = read_law(state_dir=None, home=home, cache=False)
    rubric, note = load_rubric(hub_dir(hub), law)
    if note:
        print(note)
    if kind:
        row = row_by_name(rubric, kind)
        if not row:
            print("no kind `%s` in the rubric. Kinds: %s"
                  % (kind, ", ".join(str(r.get("name")) for r in rubric.get("kinds") or [])))
            return 1
        print_row(row, law)
        return 0
    if not target or not os.path.isfile(target):
        print("no opener at %s" % target)
        return CLI_ERROR
    header = opener_header(target)
    model_line = str(header.get("model") or "")
    judgment = str(header.get("judgment") or "")
    print("opener: %s" % target)
    print("  lane:      %s" % (header.get("lane") or "—"))
    print("  model:     %s" % (model_line or "— (no model line)"))
    print("  judgment:  %s" % (judgment or "— (no judgment line)"))
    mind_o, level_o = split_model_line(model_line, rubric)
    body = read_text(target, OPENER_CAP)
    verb = judgment_verb(judgment if judgment.strip().lower() not in ("", "none") else body)
    rows = touched_rows(rubric, judgment or body)
    print("  rows it touches: %s"
          % (", ".join(str(r.get("name")) for r in rows) or "none by signal"))
    print("  the law's floors: judgment goes to %s, never %s%s"
          % (law.get("floor") or "—", ", ".join(law.get("flagged") or []) or "—",
             "" if law.get("readable") else "   [law floor unreadable]"))
    disagreement = ""
    flagged = [m.upper() for m in (law.get("flagged") or [])]
    if judgment.strip() and judgment.strip().lower() != "none" and mind_o.upper() in flagged:
        disagreement = ("the header names judgment steps and the model line says %s, "
                        "which the law forbids for judgment" % mind_o.upper())
    elif not judgment.strip() and verb and mind_o.upper() in flagged:
        disagreement = ("the body says \"%s\" under a %s model line and there is no "
                        "judgment line" % (verb, mind_o.upper()))
    elif mind_o and law.get("floor") and rows and rows[0].get("id") == "synthesis" \
            and level_o and level_o.upper() != "MAX":
        disagreement = ("the work reads as synthesis and the opener asks %s" % level_o)
    print("  %s" % (disagreement or "they agree as far as this file can say"))
    if judgment.strip() and judgment.strip().lower() != "none":
        print("  the model line is the retiring session's guess: walk it in your own "
              "words (law §2). This tool does not write that line.")
    return 0


def touched_rows(rubric, text):
    """The rows a judgment line or a body touches: judgment by the engine's own
    verb pattern, the rest by the rubric's own signal words."""
    out = []
    low = str(text or "").lower()
    if judgment_verb(text):
        row = row_by_id(rubric, "judgment")
        if row:
            out.append(row)
    for rid, words in (rubric.get("signals") or {}).items():
        if not isinstance(words, list):
            continue
        if any(str(w).lower() in low for w in words):
            row = row_by_id(rubric, rid)
            if row and row not in out:
                out.append(row)
    return out


def print_row(row, law):
    never = list(row.get("never") or [])
    if row.get("never_law") and law.get("flagged"):
        never = never + ["%s (law)" % m for m in law["flagged"]]
    print("%s — %s" % (row.get("name"), row.get("ask")))
    print("  mind:   %s" % (row.get("mind_note") or ", ".join(row.get("minds") or [])))
    if never:
        print("  never:  %s" % ", ".join(never))
    print("  dial:   %s%s" % (row.get("level") or "—",
                              "  (%s)" % row["level_note"] if row.get("level_note") else ""))
    print("  flag:   %s" % (row.get("flag") or "none"))
    print("  why:    %s" % (row.get("why") or ""))
    print("  source: %s%s" % (row.get("source"), cells_note(row)))


def status(hub, state_dir, home=None, settings=None):
    """ONE line: the hooks, the rubric, the law, and this week's cues by frame."""
    law = read_law(state_dir=None, home=home, cache=False)
    rubric, note = load_rubric(hub_dir(hub), law)
    parts = []
    for vendor in ("claude", "codex"):
        events = HOOK_EVENTS.get(vendor) or {}
        path = hooks_file(vendor, home=home, settings=settings)
        have = installed_events(path)
        if not events:
            parts.append("hooks %s off (probe owed)" % vendor)
        else:
            parts.append("hooks %s %d/%d" % (vendor, len(have), len(events)))
    parts.append(note.replace("rubric: ", "rubric ") if note else "rubric ok")
    parts.append("law floor %s" % ("read (%s; never %s)"
                                   % (law.get("floor") or "—",
                                      ", ".join(law.get("flagged") or []) or "—")
                                   if law.get("readable") else "unreadable"))
    if not state_dir:
        # No --state-dir given: read the one the installed hook writes, from its
        # own command line -- never an empty cwd read as "nothing seen" (P18).
        state_dir = installed_state_dir(hooks_file("claude", home=home,
                                                   settings=settings))
    if state_dir:
        road = newest_source(state_dir)
        parts.append("dial source: %s" % (SOURCE_SAID.get(road, road) if road
                                          else "not seen yet"))
        counts = cue_counts(state_dir)
        parts.append("cues 7d: %s" % (" ".join("%s %d" % (k, counts[k])
                                               for k in sorted(counts)) or "none"))
    else:
        parts.append("state dir: none given and no hook installed -- "
                     "dial source and cues unread (give --state-dir)")
    print("effort: " + " · ".join(parts))
    return 0


SOURCE_SAID = {
    "live": "live",
    "ran": "ran (the app hands hooks no dial)",
    "unknown": "unknown (no reply to read yet)",
}


def newest_source(state_dir):
    """Which road the dial came by, in the newest session this machine has seen.
    '' when no session has run yet — never a guess (P15)."""
    folder = os.path.join(str(state_dir or ""), "sessions")
    best, when = "", -1.0
    try:
        names = os.listdir(folder)
    except OSError:
        return ""
    for name in names[:500]:                     # bounded, like every read here
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        try:
            age = os.stat(path).st_mtime
        except OSError:
            continue
        if age > when:
            held = read_json(path, None, cap=65536)
            if isinstance(held, dict) and held.get("source"):
                best, when = str(held["source"]), age
    return best


def cue_counts(state_dir, days=7):
    """This week's cues by frame, from the log the hook writes — bounded to the
    log's last 256 KB, because a count is not worth an unbounded read."""
    out = {}
    if not state_dir:
        return out
    import datetime
    path = os.path.join(str(state_dir), "effort.log")
    text = read_text(path, 262144)
    if not text:
        return out
    cut = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[1] != "CUE":
            continue
        if parts[0] < cut:
            continue
        out[parts[2]] = out.get(parts[2], 0) + 1
    return out


# ══════════════════════════════════════════════════════════════════════════
# --install-hooks — an attended act, on the user's word, per machine
# ══════════════════════════════════════════════════════════════════════════
# The postman's contract, mirrored and written fresh here (it is under another
# builder's rebuild and is not imported): back the settings file up first, keep
# its own mode, add only entries whose command is this tool's, remove only those,
# --dry writes nothing and prints the exact diff, and the command always names a
# CONSOLE python — never `pythonw`, which has no stdout, and a hook that cannot
# print delivers nothing.

def machine_record(home=None):
    return read_json(os.path.join(home_dir(home), "orchestrator-sync", "machine.json"),
                     {}, cap=65536)


def hooks_file(vendor, home=None, record=None, settings=None):
    """Where a vendor keeps its hooks on this machine — from the record, never a
    path written here."""
    if settings:
        return str(settings)
    data = record if record is not None else machine_record(home)
    roots = (data.get("roots") or {}) if isinstance(data, dict) else {}
    if vendor == "codex":
        return os.path.join(str(roots.get("codex") or
                                os.path.join(home_dir(home), ".codex")), "hooks.json")
    return os.path.join(str(roots.get("claude") or
                            os.path.join(home_dir(home), ".claude")), "settings.json")


def brain_carries(path, home=None):
    """Does the brain CARRY this file — would a change here land on the other
    machine?  A per-machine command in a synced file would break the other
    machine, so the install refuses one by name.  A `report-only` or per-machine
    entry does not carry."""
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
    """THE PYTHON A PRINTED COMMAND MUST NAME: a hook PRINTS its frame, and
    `pythonw` has no stdout, so a command that named it would deliver nothing."""
    py = sys.executable or ""
    if not py:
        return "python" if os.name == "nt" else "python3"
    stem = os.path.splitext(os.path.basename(py))[0].lower()
    if stem == "pythonw":
        beside = os.path.join(os.path.dirname(py), "python" +
                              os.path.splitext(py)[1])
        if os.path.isfile(beside):
            return beside
        return "python"
    return py


def hook_command(hub, state_dir, vendor, python=None):
    """The command an entry runs, rendered per machine from the record and the
    running python — never a path written into this file.  One shell-command
    string, the only form both vendors document; every path quoted."""
    return '"%s" "%s" --hook --vendor %s --state-dir "%s"' % (
        python or console_python(),
        os.path.join(str(hub), "tools", "effort.py"), vendor, str(state_dir))


def is_ours(command):
    """Is this entry ours?  Tested on the two parts and not on the phrase
    `effort.py --hook`, because the rendered command QUOTES its paths and a quote
    sits between them."""
    text = str(command or "")
    return "effort.py" in text and "--hook" in text


def detect_indent(text):
    import re
    match = re.search(r"\n(\s+)\"", text or "")
    if not match:
        return CLI_ERROR
    pad = match.group(1).replace("\n", "")
    return len(pad) if pad and pad[0] == " " else 2


def merge_hooks(text, command, events):
    """MERGE beside whatever is there: another tool's entries may not be
    reordered, rewritten or dropped.  A second run adds nothing and writes
    nothing."""
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
        if any(isinstance(r, dict) and any(isinstance(h, dict) and is_ours(h.get("command"))
                                           for h in (r.get("hooks") or []))
               for r in rows):
            continue
        rows.append({"hooks": [{"type": "command", "command": command,
                                "timeout": HOOK_ENTRY_TIMEOUT}]})
        added.append(event)
    indent = detect_indent(text)
    rendered = json.dumps(data, indent=indent, ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, added


def strip_hooks(text):
    """--uninstall-hooks removes only entries whose command is this tool's, and
    leaves every other tool's entry exactly as it is."""
    data = json.loads(text)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    removed = []
    if isinstance(hooks, dict):
        for event, rows in list(hooks.items()):
            if not isinstance(rows, list):
                continue
            keep = []
            for row in rows:
                mine = isinstance(row, dict) and any(
                    isinstance(h, dict) and is_ours(h.get("command"))
                    for h in (row.get("hooks") or []))
                if mine:
                    removed.append(event)
                else:
                    keep.append(row)
            if keep:
                hooks[event] = keep
            else:
                hooks.pop(event)
        if not hooks:
            data.pop("hooks", None)
    indent = detect_indent(text)
    rendered = json.dumps(data, indent=indent, ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, removed


def installed_events(path):
    """The events this tool's entries sit on in a settings file, for --status."""
    data = read_json(path, None, cap=SETTINGS_CAP)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    out = []
    if isinstance(hooks, dict):
        for event, rows in hooks.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict) and any(
                        isinstance(h, dict) and is_ours(h.get("command"))
                        for h in (row.get("hooks") or [])):
                    out.append(event)
    return sorted(set(out))


def installed_state_dir(path):
    """The state dir the installed hook writes, read from its own command in the
    settings file -- so `--status` with no --state-dir reads the real state and
    never an empty cwd."""
    import re
    data = read_json(path, None, cap=SETTINGS_CAP)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return ""
    for rows in hooks.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for entry in (row.get("hooks") or []):
                command = str(entry.get("command") or "") if isinstance(entry, dict) else ""
                if not is_ours(command):
                    continue
                match = re.search(r'--state-dir\s+(?:"([^"]*)"|\'([^\']*)\'|(\S+))',
                                  command)
                if match:
                    return match.group(1) or match.group(2) or match.group(3) or ""
    return ""


def cmd_install_hooks(hub, state_dir, vendor, dry=False, home=None, settings=None,
                      remove=False, python=None):
    """Print exactly what it would do, do only that, keep a backup, and refuse a
    file the brain carries — by name.  Running sessions pick the entries up
    through the app's own settings watcher: no restart, and an uninstall is as
    quick."""
    import difflib
    out = []
    vendors = [vendor] if vendor else ["claude", "codex"]
    for name in vendors:
        events = sorted(HOOK_EVENTS.get(name) or {})
        path = hooks_file(name, home=home, settings=settings)
        if not events:
            out.append(CODEX_OFF_NOTE if name == "codex" else
                       "%s: no event of this vendor's is documented well enough to "
                       "install — nothing proposed for it" % name)
            continue
        carried = brain_carries(path, home)
        if carried:
            out.append("REFUSED: %s is carried by the brain as %s — a per-machine "
                       "command in a synced file would break the other machine"
                       % (path, carried))
            continue
        text = read_text(path, SETTINGS_CAP) if os.path.isfile(path) else ""
        existed = bool(text.strip())
        if not existed:
            if remove:
                out.append("%s: no hooks file at %s — nothing to remove" % (name, path))
                continue
            text = "{}\n"
        command = hook_command(hub, state_dir, name, python=python)
        if "pythonw" in command.lower():
            out.append("REFUSED: the running python is `pythonw`, which has no stdout — "
                       "a hook that cannot print delivers nothing")
            continue
        try:
            if remove:
                rendered, touched = strip_hooks(text)
            else:
                rendered, touched = merge_hooks(text, command, events)
        except Exception as exc:
            out.append("REFUSED: %s is not valid JSON (%s) — nothing written"
                       % (path, exc))
            continue
        verb = "would remove" if remove else "would add"
        if not touched:
            out.append("%s: already %s in %s — nothing to write"
                       % (name, "absent" if remove else "installed",
                          os.path.basename(path)))
            continue
        for event in sorted(set(touched)):
            out.append("%s %s · %s · timeout %ds" % (verb, event, command,
                                                     HOOK_ENTRY_TIMEOUT))
            doc = (HOOK_EVENTS.get(name) or {}).get(event, {}).get("doc")
            if doc and not remove:
                out.append("    %s" % doc)
        if dry:
            for row in difflib.unified_diff(text.splitlines(), rendered.splitlines(),
                                            fromfile=path + " (now)",
                                            tofile=path + " (would be)", lineterm="",
                                            n=2):
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


# ══════════════════════════════════════════════════════════════════════════

def usage():
    print(__doc__ + "\nusage-settings.json hooks_refuse: unattended-only (default) | never (no prompt refusal).")


def main(argv):
    if "--hook" in argv:                       # before anything heavier is imported
        return hook_main(argv)
    if "--dial" in argv:                       # the session's own turn-start read
        return cmd_dial(argv)
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--replay", nargs="*", default=None)
    ap.add_argument("--weigh", nargs="?", const="", default=None)
    ap.add_argument("--kind", default="")
    ap.add_argument("--rubric", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--install-hooks", dest="install", action="store_true")
    ap.add_argument("--uninstall-hooks", dest="uninstall", action="store_true")
    ap.add_argument("--vendor", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--state-dir", dest="state_dir", default="")
    ap.add_argument("--hub", default="")
    ap.add_argument("--home", default="")
    ap.add_argument("--settings", default="")
    ap.add_argument("--python", default="")
    ap.add_argument("--silent-too", dest="silent_too", action="store_true")
    ap.add_argument("--help", "-h", dest="help", action="store_true",
                    help="usage-settings.json hooks_refuse: unattended-only (default) or never")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        usage()
        return CLI_ERROR
    if args.help:
        usage()
        return 0
    hub = args.hub or hub_dir(None)
    home = args.home or None
    if args.rubric:
        return print_rubric(hub, check=args.check, home=home,
                            state_dir=args.state_dir or None)
    if args.status:
        return status(hub, args.state_dir, home=home,
                      settings=args.settings or None)
    if args.weigh is not None or args.kind:
        return weigh(args.weigh or "", args.kind, hub, home=home)
    if args.replay is not None:
        if not args.state_dir:
            print("--replay needs --state-dir (a temp dir; it is never written to)")
            return CLI_ERROR
        return replay(args.replay, args.state_dir, hub=hub,
                      show_silent=args.silent_too)
    if args.install or args.uninstall:
        if not args.state_dir:
            print("--install-hooks needs --state-dir (the hook's own state dir)")
            return CLI_ERROR
        for line in cmd_install_hooks(hub, args.state_dir, args.vendor, dry=args.dry,
                                      home=home, settings=args.settings or None,
                                      remove=args.uninstall,
                                      python=args.python or None):
            print(line)
        return 0
    usage()
    return CLI_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
