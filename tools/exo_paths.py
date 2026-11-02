#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exo_paths.py — one answer to "where is everything".

A tool that needs the hub folder, the sync package, the brain clone or the
machine file asks this module instead of spelling a path of its own:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_paths import paths

    P = paths(tool_file=__file__)
    P["hub"], P["sync_dir"], P["brain"], P["machine_file"]

TWO LAYOUTS, and the module says which one it found.

  LEGACY        the hub folder holds the program and the notes together; the
                sync package and the machine file live inside the brain clone,
                in a folder of its own under the user's home.
  PROGRAM-TREE  the hub folder is a checkout of the program: the sync package
                is <hub>/sync, the machine file is <hub>/machine.json, and the
                brain clone lives wherever the record says.

WHAT IT PROMISES

  * Importing it does nothing at all: no file is written, nothing is printed,
    and neither the home folder nor the environment is read until a call.
  * paths() never raises over a missing or damaged record. What cannot be
    resolved comes back as None, and what looks wrong comes back as a plain
    sentence in `problems`. Pass strict=True to turn the first of those
    sentences into an ExoPathsStop instead.
  * It REPORTS. It does not decide what a caller should do about a problem.
  * The record is additive: later versions add keys and never remove or rename
    one. API carries the version, and need(n) stops in one plain line when the
    module present is older than a caller needs.
  * The home folder and the environment are read at CALL time, so two calls in
    one process can honestly give two answers.

FROM A SHELL, OR FROM ANOTHER LANGUAGE

    python3 exo_paths.py --check      one line; exit 0 when clean, 2 on a problem
    python3 exo_paths.py --json       the whole record, every path as text
    python3 exo_paths.py --json --tool-file <path>
    python3 exo_paths.py --check --hub <folder>

Standard library only, Python 3.9-compatible, macOS and Windows. It imports no
other module of its own program, so it can be the first piece to arrive.
"""
import io
import json
import os
import sys
from pathlib import Path

API = 1                       # the record's version — additive only, never renamed

# The one place the older layout's folder name is written down.
LEGACY_SYNC_DIRNAME = "orchestrator-sync"

MACHINE_FILE_NAME = "machine.json"
MACHINE_FILE_ENV = "EXO_MACHINE_JSON"
SYNC_ENTRY_NAME = "sync.py"
GIT_MARKER = ".git"                     # a folder in a clone, a small file in a worktree
LAYOUT_LEGACY = "legacy"
LAYOUT_PROGRAM = "program-tree"
LAYOUTS = (LAYOUT_LEGACY, LAYOUT_PROGRAM)

# Every key of the record, in the order it is returned. A later API adds to the
# end of this tuple; nothing is ever taken out of it.
RECORD_KEYS = ("api", "layout", "layout_source", "hub", "sync_dir", "brain",
               "machine_file", "machine", "roots", "bootstrapped", "hub_is_git",
               "partition", "templates_dir", "problems")

USAGE = """exo_paths.py — where the hub, the sync package, the brain clone and
the machine file are, on this machine, right now.

  python3 exo_paths.py --check      one line; exit 0 when clean, 2 on a problem
  python3 exo_paths.py --json       the whole record, every path as text

  --tool-file <path>   read the hub from a tool's own location (<hub>/tools/x.py)
  --hub <folder>       take this folder as the hub, whatever the record says
  --help               this text
"""


class ExoPathsStop(Exception):
    """One plain sentence, ready to print as it stands. No traceback needed."""


# ---------------------------------------------------------------------------
# small readers — none of them raises, and none of them writes
# ---------------------------------------------------------------------------

def _oneline(text):
    """Any message squeezed onto a single line, so one sentence stays one."""
    return " ".join(str(text).split())


def _path(value):
    """A written path as a Path, with a leading ~ expanded. None when the value
    is not a usable piece of text."""
    if isinstance(value, Path):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return Path(text).expanduser()
    except Exception:
        try:
            return Path(text)
        except Exception:
            return None


def _home():
    """The home folder, asked of the system every time it is wanted."""
    try:
        return Path.home()
    except Exception:
        return Path(os.path.expanduser("~"))


def _is_file(p):
    try:
        return p is not None and Path(p).is_file()
    except OSError:
        return False


def _is_dir(p):
    try:
        return p is not None and Path(p).is_dir()
    except OSError:
        return False


def _exists(p):
    try:
        return p is not None and Path(p).exists()
    except OSError:
        return False


def _read_record(path, problems):
    """(the record, was it readable) — the machine file parsed as a JSON object.

    A file that cannot be read, or that does not hold a JSON object, counts as
    an empty record and adds one sentence naming it. It is never an exception,
    and it never quietly turns into some other file's identity: the search
    stops at the file it found, so a damaged record is visible rather than
    replaced."""
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeError) as exc:
        problems.append("the machine file %s could not be read (%s), so this run has no "
                        "recorded identity; repair that file." % (path, _oneline(exc) or
                                                                  type(exc).__name__))
        return {}, False
    if not isinstance(data, dict):
        problems.append("the machine file %s does not hold a JSON object, so this run has no "
                        "recorded identity; repair that file." % path)
        return {}, False
    return data, True


# ---------------------------------------------------------------------------
# the record
# ---------------------------------------------------------------------------

def paths(tool_file=None, hub=None, strict=False):
    """Where everything is, as one dict. See RECORD_KEYS for every key.

    tool_file   the calling tool's own __file__; the hub is two levels above it
    hub         a folder to take as the hub, whatever the record says
    strict      raise ExoPathsStop(first problem) instead of reporting it
    """
    problems = []

    # 1 — where the hub probably is, before any record has been read.
    if hub is not None:
        hub_guess = _path(hub) or Path(str(hub))
    elif tool_file is not None:
        hub_guess = Path(str(tool_file)).resolve().parent.parent
    else:
        hub_guess = Path(__file__).resolve().parent.parent

    # 2 — the machine file: one named outright, then the hub's own, then the
    #     older layout's copy inside the brain clone.
    machine_file = None
    named = str(os.environ.get(MACHINE_FILE_ENV) or "").strip()
    if named:
        candidate = _path(named)
        if _is_file(candidate):
            machine_file = candidate
        else:
            problems.append("%s names %s, which is not a file; the search went on without "
                            "it." % (MACHINE_FILE_ENV, named))
    if machine_file is None and _is_file(hub_guess / MACHINE_FILE_NAME):
        machine_file = hub_guess / MACHINE_FILE_NAME
    if machine_file is None:
        older = _home() / LEGACY_SYNC_DIRNAME / MACHINE_FILE_NAME
        if _is_file(older):
            machine_file = older

    # 3 — the record itself.
    record, readable = ({}, False)
    if machine_file is not None:
        record, readable = _read_record(machine_file, problems)

    # 4 — the names the record carries.
    raw_roots = record.get("roots", None)
    roots = {}
    if isinstance(raw_roots, dict):
        roots = raw_roots
    elif raw_roots is not None:
        problems.append("the machine file %s records its folders, but not as a set of named "
                        "paths; none of them was used." % machine_file)
    machine = str(record.get("name", "") or "").strip().lower() or "unknown"

    def root(name):
        """One recorded folder, or None — and a sentence when it is unusable."""
        if name not in roots:
            return None
        chosen = _path(roots.get(name))
        if chosen is None:
            problems.append("the machine file %s records the %s folder, but not as a path; it "
                            "was ignored." % (machine_file, name))
        return chosen

    # 5 — the hub.
    if hub is not None:
        hub_dir = hub_guess
    else:
        hub_dir = root("orchestrator") or hub_guess

    # 6 — what the folders themselves say.
    has_sync_entry = _is_file(hub_dir / "sync" / SYNC_ENTRY_NAME)
    structure_says_program = has_sync_entry and _is_file(hub_dir / "tools" / "exo_paths.py")

    # 7 — the layout: the record first, then the structure, then the older shape.
    recorded = record.get("layout", None)
    layout, layout_source = None, None
    if isinstance(recorded, str) and recorded.strip() in LAYOUTS:
        layout, layout_source = recorded.strip(), "record"
    elif recorded is not None:
        problems.append("the machine file %s records the layout as %s, which is neither %s nor "
                        "%s; the folders were read instead."
                        % (machine_file, _oneline(repr(recorded)), LAYOUT_LEGACY, LAYOUT_PROGRAM))
    if layout is None:
        if structure_says_program:
            layout, layout_source = LAYOUT_PROGRAM, "structure"
        else:
            layout, layout_source = LAYOUT_LEGACY, "default"

    # A record and a folder tree that say different things are never reconciled
    # quietly: the record still wins, and the disagreement is reported.
    if layout_source == "record":
        if layout == LAYOUT_LEGACY and structure_says_program:
            problems.append("the machine file %s records the older layout, but %s holds "
                            "sync/%s beside tools/exo_paths.py, which is a program tree: one of "
                            "the two is wrong." % (machine_file, hub_dir, SYNC_ENTRY_NAME))
        elif layout == LAYOUT_PROGRAM and not has_sync_entry:
            problems.append("the machine file %s records a program tree, but there is no "
                            "sync/%s in %s: one of the two is wrong."
                            % (machine_file, SYNC_ENTRY_NAME, hub_dir))

    # 8 — the brain clone.
    brain = root("brain")
    if brain is None and layout == LAYOUT_LEGACY and machine_file is not None:
        folder = Path(machine_file).parent
        if _exists(folder / GIT_MARKER):
            brain = folder

    # 9 — the sync package: the folder that holds the sync entry point.
    sync_dir = root("sync")
    if sync_dir is None:
        if layout == LAYOUT_PROGRAM:
            sync_dir = hub_dir / "sync"
        else:
            beside = Path(machine_file).parent if machine_file is not None else None
            older = _home() / LEGACY_SYNC_DIRNAME
            if beside is not None and _is_file(beside / SYNC_ENTRY_NAME):
                sync_dir = beside
            elif _is_file(older / SYNC_ENTRY_NAME):
                sync_dir = older

    # 10 — the rest of the record.
    hub_is_git = _exists(hub_dir / GIT_MARKER)
    partition = record.get("partition", None)
    if partition is not None and not isinstance(partition, str):
        problems.append("the machine file %s records the partition as %s rather than as a word; "
                        "it was ignored." % (machine_file, _oneline(repr(partition))))
        partition = None
    templates_dir = hub_dir / "templates"
    if not _is_dir(templates_dir):
        templates_dir = None

    out = {
        "api": API,
        "layout": layout,
        "layout_source": layout_source,
        "hub": hub_dir,
        "sync_dir": sync_dir,
        "brain": brain,
        "machine_file": machine_file,
        "machine": machine,
        "roots": dict(roots),
        "bootstrapped": bool(readable),
        "hub_is_git": bool(hub_is_git),
        "partition": partition,
        "templates_dir": templates_dir,
        "problems": problems,
    }
    if strict and problems:
        raise ExoPathsStop(problems[0])
    return out


def need(api):
    """The version gate for a caller that needs a newer record than may be here.

    Stops in one plain line naming both numbers — never a traceback, never a
    missing key surprising the caller halfway through its run."""
    try:
        wanted = int(api)
    except (TypeError, ValueError):
        raise ExoPathsStop("this tool asked for path record %s, which is not a version number."
                           % _oneline(repr(api)))
    if API < wanted:
        raise ExoPathsStop("this tool needs path record %d; the one installed is %d — sync the "
                           "hub, then run it again." % (wanted, API))
    return API


# ---------------------------------------------------------------------------
# for a shell, and for tools written in another language
# ---------------------------------------------------------------------------

def as_text(record):
    """The record with every path as text — ready for json.dumps."""
    out = {}
    for key, value in record.items():
        out[key] = str(value) if isinstance(value, Path) else value
    return out


def _say(value):
    return str(value) if value is not None else "none"


def check_line(record):
    """(the one line a human reads, the exit code that goes with it)."""
    if record["problems"]:
        return "STOP: %s" % record["problems"][0], 2
    return ("OK: %s · hub %s · sync %s · brain %s"
            % (record["layout"], _say(record["hub"]), _say(record["sync_dir"]),
               _say(record["brain"]))), 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:                                   # a console that cannot spell "·" prints a dot
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    want_json = want_check = False
    tool_file = hub = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--help", "-h"):
            sys.stdout.write(USAGE)
            return 0
        if arg == "--json":
            want_json = True
        elif arg == "--check":
            want_check = True
        elif arg in ("--tool-file", "--hub"):
            i += 1
            if i >= len(argv):
                sys.stderr.write("exo_paths.py: %s needs a path after it.\n" % arg)
                return 2
            if arg == "--tool-file":
                tool_file = argv[i]
            else:
                hub = argv[i]
        else:
            sys.stderr.write("exo_paths.py: %s is not an option this tool knows.\n\n" % arg)
            sys.stderr.write(USAGE)
            return 2
        i += 1
    if not want_json and not want_check:
        want_check = True                  # a bare run answers the plain question
    record = paths(tool_file=tool_file, hub=hub)
    if want_json:
        sys.stdout.write(json.dumps(as_text(record), indent=2, ensure_ascii=False) + "\n")
    if want_check:
        line, code = check_line(record)
        sys.stdout.write(line + "\n")
        return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
