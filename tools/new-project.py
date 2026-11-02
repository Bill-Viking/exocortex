#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new-project.py — one command makes a project the board and the tree can see.

    python3 tools/new-project.py <name>            macOS (python on Windows)
    python3 tools/new-project.py <name> --no-git   no repository
    python3 tools/new-project.py <name> --dry      say what it would do; change nothing
    python3 tools/new-project.py <name> --root <folder>
                                                   make it under this folder instead of
                                                   the projects root the record names

WHAT IT DOES, IN ORDER

  1 checks the name: a plain folder name on every machine — letters, digits,
    '-', '_' and '.', not starting with a dot, not ending with one, not one of
    the hub's own folder names and not a name Windows keeps for itself
  2 finds the projects root in this machine's record, through the path
    resolver (tools/exo_paths.py) — never a guess; --root overrides it
  3 writes STATUS.md in the one schema every tool reads (## Now · ## To do ·
    ## Important), and the project's first OPENER.md, so its tile is green
    with a prompt from the first minute. A folder that is already there gains
    those two files and nothing else — no repository — and an OPENER.md
    already in it is left as it is; a folder that already has a STATUS.md is
    already a project, and nothing changes
  4 makes a git repository with one commit of those two files, when git is on
    this machine's PATH and the folder is new and not already inside a
    repository — and says which of those roads it took
  5 redraws the board and the tree (orchestrator.py, this interpreter), and
    checks that the tree now lists the new folder
  6 prints the folder's full path alone on its own line, then the next move

Every refusal is one sentence and exit 1, with nothing changed. A second run
with the same name refuses, so running it twice is safe. Nothing it writes
names this machine's home folder or its owner. Standard library only, Python
3.9-compatible, macOS and Windows: paths are pathlib, commands are argument
lists, never a shell string.
"""
import datetime
import json
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:                                    # a cp1252 console never crashes on a dash
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

PROGRAM_NAME = "exocortex new-project"
TOOLS = Path(__file__).resolve().parent
PROGRAM = TOOLS.parent                  # the program tree this copy belongs to

sys.path.insert(0, str(TOOLS))
from exo_paths import paths             # noqa: E402  the one answer to "where is it"

# The hub's own folder names — the SAME tuple as sync/install.py's
# RESERVED_FOLDERS (the gate proves the two equal), carried here so this command
# works on a machine whose sync package predates the list.
RESERVED_FOLDERS = ("tools", "sync", "templates", "docs", "laws", "licenses",
                    "tests", "grok", "openai", ".github", "fonts")

NAME_OK = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")
# Names Windows will not make a folder with, whatever the case or extension.
WINDOWS_KEPT = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % i for i in range(1, 10)} \
    | {"LPT%d" % i for i in range(1, 10)}

# THE ONE SCHEMA, written once. The board (orchestrator.py read_status) and the
# tree (collect-openers.py read_status) both parse exactly these three
# headings; the Important sentence is the one the hub's own seed carries.
STATUS_TEMPLATE = """# STATUS — {name}

## Now

Created {date} with new-project.py; nothing has happened here yet — replace
this paragraph with where things stand.

## To do

- [ ] say in ## Now what this project is for

## Important

- The schema is fixed, and every project's STATUS.md uses it: `## Now` is one
  short paragraph of where things stand · `## To do` is `- [ ]` items, a
  leading `!` inside the item marks it urgent, and a finished item is ticked
  (`- [x]`) rather than deleted · `## Important` is the constraints, rulings
  and decisions that must survive this file being rewritten.
"""

# The project's first opener: header, `---`, the prompt (the opener file's
# contract the tree reads). `head: none` makes it a brain opener, current while
# STATUS.md is, whether or not the folder becomes a repository.
OPENER_TEMPLATE = """lane: {name}
written: {now}
by: new-project.py
on: {machine}
head: none (first opener, written by new-project.py)
status_updated: {now}
where: new project — nothing has happened yet
next: machine
depends_on: nothing
open_in: {folder} · a fresh session titled ACT — {name}: first session
model: any · default
judgment: none
---
read the project status/memory first.
Say what this project is for in STATUS.md ## Now, then take the first real step.
"""

USAGE = __doc__


class Refused(Exception):
    """One sentence, exit 1, nothing changed."""


def say(text=""):
    print(text)


def check_name(name, record):
    shown = name if name else "(empty)"
    if (not NAME_OK.match(name) or name.endswith(".") or name in (".", "..")):
        raise Refused('"%s" is not a plain folder name — use letters, digits, "-", "_" '
                      'and ".", not starting or ending with a dot; nothing changed.' % shown)
    if name.split(".")[0].upper() in WINDOWS_KEPT:
        raise Refused('"%s" is a name Windows keeps for itself, so the folder could not '
                      'cross to a Windows machine — pick another; nothing changed.' % name)
    if name.lower() in {r.lower() for r in RESERVED_FOLDERS}:
        raise Refused('"%s" is one of the hub\'s own folder names (%s) — pick another; '
                      'nothing changed.' % (name, ", ".join(RESERVED_FOLDERS)))


def projects_root(record, override):
    if override:
        return Path(override).expanduser()
    roots = record.get("roots") or {}
    value = roots.get("projects")
    if isinstance(value, str) and value.strip():
        return Path(value.strip()).expanduser()
    where = record.get("machine_file") or "no machine record was found"
    raise Refused("this machine's record (%s) names no projects folder — run the "
                  "installer, or pass --root <folder>; nothing changed." % where)


def machine_name(record):
    """This machine's name as its record writes it, or the resolver's word."""
    try:
        data = json.loads(Path(str(record.get("machine_file"))).read_text(encoding="utf-8"))
        name = str(data.get("name") or "").strip()
        if name:
            return name
    except (OSError, ValueError, TypeError):
        pass
    return str(record.get("machine") or "unknown")


def now_iso():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def git_top(folder, git):
    """The repository a folder is inside, or None. Asked of the nearest folder
    that exists, so a folder about to be made can be asked too."""
    probe = folder
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        done = subprocess.run([git, "-C", str(probe), "rev-parse", "--show-toplevel"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    top = (done.stdout or "").strip()
    return top if done.returncode == 0 and top else None


def last_line(text):
    lines = [l.strip() for l in str(text or "").splitlines() if l.strip()]
    return lines[-1] if lines else "no reason given"


def make_repo(folder, name, git):
    """(the road, in words). git init, STATUS.md added, one commit."""
    steps = ([git, "init", "-q", str(folder)],
             [git, "-C", str(folder), "add", "--", "STATUS.md", "OPENER.md"],
             [git, "-C", str(folder), "commit", "-q", "-m", "new project: %s" % name])
    for index, argv in enumerate(steps):
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=120)
        if done.returncode != 0:
            if index == 0:
                return "git could not make a repository here (%s)" % last_line(done.stdout)
            return ("a new repository; its first commit did not run (%s) — commit "
                    "STATUS.md and OPENER.md yourself" % last_line(done.stdout))
    return 'a new repository, first commit "new project: %s"' % name


def load_collector():
    """tools/collect-openers.py as a module, or None — the tree's own rule for
    which folders it lists, asked rather than copied."""
    path = TOOLS / "collect-openers.py"
    if not path.is_file():
        return None
    saved = sys.dont_write_bytecode
    sys.dont_write_bytecode = True          # no __pycache__ in the program tree
    try:
        spec = importlib.util.spec_from_file_location("collect_openers_np", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None
    finally:
        sys.dont_write_bytecode = saved


def redraw(folder, override_root):
    """(ok, the line to print). The board and the tree, redrawn by this same
    interpreter, then the tree's own enumeration asked whether it lists the new
    folder — a redraw is not done until the tile is really there."""
    board = PROGRAM / "orchestrator.py"
    if not board.is_file():
        return True, "this version draws no board — nothing to redraw"
    env = dict(os.environ)
    if override_root:
        env["ORCH_PROJECTS_ROOT"] = str(override_root)
    try:
        done = subprocess.run([sys.executable, str(board)], cwd=str(PROGRAM), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=900)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "the board could not be redrawn (%s)" % exc
    if done.returncode != 0:
        return False, ("the board did not redraw (exit %d: %s)"
                       % (done.returncode, last_line(done.stdout)))
    collector = load_collector()
    if collector is None:
        return True, "board redrawn; this version has no tree to check"
    try:
        found, listed_root, _machine = collector.project_roots()
    except Exception as exc:
        return False, "board redrawn; the tree's list could not be read (%s)" % exc
    target = folder.resolve()
    if any(Path(p).resolve() == target for _n, p, _h in found):
        return True, "board and tree redrawn — %s is on the tree" % folder.name
    return False, ("board and tree redrawn, but the tree lists projects from %s, not %s "
                   "— %s is not on it" % (listed_root, folder.parent, folder.name))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or "--help" in argv or "-h" in argv:
        sys.stdout.write(USAGE)
        return 0 if argv else 2
    dry = "--dry" in argv
    no_git = "--no-git" in argv
    override = None
    rest = []
    skip = False
    for index, arg in enumerate(argv):
        if skip:
            skip = False
            continue
        if arg == "--root":
            if index + 1 >= len(argv):
                say("new-project: --root needs a folder; nothing changed.")
                return 1
            override = argv[index + 1]
            skip = True
        elif arg in ("--dry", "--no-git"):
            continue
        elif arg.startswith("--"):
            say("new-project: %s is not a flag this tool knows; nothing changed." % arg)
            return 1
        else:
            rest.append(arg)
    if len(rest) != 1:
        say("new-project: give exactly one project name; nothing changed.")
        return 1
    name = rest[0]
    try:
        record = paths(tool_file=__file__)
        check_name(name, record)
        root = projects_root(record, override)
        folder = root / name
        if folder.exists() and not folder.is_dir():
            raise Refused("%s is a file, not a folder — nothing changed." % folder)
        status = folder / "STATUS.md"
        if status.exists():
            raise Refused("%s already has a STATUS.md — already a project; nothing changed."
                          % folder)
    except Refused as why:
        say("new-project: %s" % why)
        return 1

    existed = folder.is_dir()
    git = None if no_git else shutil.which("git")
    say("%s — %s%s" % (PROGRAM_NAME, name, "  (dry run: nothing is changed)" if dry else ""))
    text = STATUS_TEMPLATE.format(name=name, date=datetime.date.today().isoformat())

    if dry:
        if not root.is_dir():
            say("  would make   the projects root %s" % root)
        say("  would write  %s" % status)
        say("  would write  %s" % (folder / "OPENER.md") + ("  (one is already there; "
            "it would be left as it is)" if (folder / "OPENER.md").exists() else ""))
        if existed:
            say("  git          the folder is already here — it would gain these files alone")
        elif no_git:
            say("  git          skipped (--no-git)")
        elif git is None:
            say("  git          not on this machine's PATH — no repository would be made")
        else:
            top = git_top(folder, git)
            say("  git          " + ("inside the repository at %s — no new one would be made"
                                     % top if top else
                                     'would make a repository, first commit "new project: %s"'
                                     % name))
        say("  would redraw the board and the tree")
        return 0

    made_root = not root.is_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if made_root:
        say("  made         the projects root %s" % root)
    with open(str(status), "x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    # The opener is written AFTER STATUS.md, so its status_updated is never
    # older than the file it vouches for.
    opener = folder / "OPENER.md"
    if opener.exists():
        say("  wrote        STATUS.md; OPENER.md was already here and is left as it is")
    else:
        with open(str(opener), "x", encoding="utf-8", newline="\n") as handle:
            handle.write(OPENER_TEMPLATE.format(name=name, now=now_iso(),
                                                machine=machine_name(record),
                                                folder=folder))
        say("  wrote        STATUS.md and OPENER.md%s" % (
            "  (the folder was already here; it gained these two files alone)"
            if existed else ""))
    if existed:
        road = "the folder was already here — no repository was made"
    elif no_git:
        road = "skipped (--no-git)"
    elif git is None:
        road = "not on this machine's PATH — no repository was made"
    else:
        top = git_top(folder, git)
        road = (("inside the repository at %s — no new one was made" % top) if top
                else make_repo(folder, name, git))
    say("  git          %s" % road)
    ok, line = redraw(folder, root if override else None)
    say("  drawn        %s" % line)
    say(str(folder))
    say("Open a session in that folder.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
