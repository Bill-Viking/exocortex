#!/usr/bin/env python3
"""install.py - one command installs, updates, repairs or rebuilds a machine.

    python3 install.py              macOS
    python  install.py              Windows

Run it from the program's sync folder. In a program tree that is
<hub>/sync/install.py; in the older layout it is the folder the brain clone
sits in. The hub folder does not have to exist yet.

  --defaults        no questions; sensible roots, and a brain of its own on
                    this disk (it says so, and says it is not backed up)
  --machine NAME    short machine name for a first bootstrap (default: hostname)
  --brain URL|PATH  JOIN an existing brain: clone it instead of making one
  --brain-remote U  make a NEW brain and push it to this address (it must be
                    private; the sync tool checks before it sends a byte)
  --dry-run         print every step as PRESENT / WOULD CREATE / WOULD REPAIR
                    and change nothing but this run's own lock file
  --only STEP       seeds | laws | heartbeat | watchers | tree   (repairs, one step)
  --update          THE SAFE UPDATER: fetch a verified ref, refuse to touch a
                    file of yours, fast-forward, re-run the idempotent steps
  --recover         THE ROAD BACK: put back every live file the mirror holds
                    and this machine has lost; nothing is overwritten
  --repair          re-check what an install wrote (the record, the rule file,
                    the seeds, the jobs) and mend what it can
  --ref REF         the ref --update follows (default: what the record names,
                    else origin/<this branch>)
  --uninstall       THE WAY OUT: remove exactly what installed.json says this
                    installer made — the heartbeat jobs, the rendered watcher
                    prompts and their landing sheet, <claude root>/exocortex-laws.md,
                    each shipped skill still byte-identical to the shipped copy —
                    and nothing else. The hub folder, the brain, every seed and
                    CLAUDE.md stay (the one line to take out of CLAUDE.md is
                    printed). Ends with a manifest: removed · left · not found.
                    With --dry-run it says what it would do and changes nothing.
  --help            this text

The machine's scheduler is the one thing here that is not confined to a folder,
so the heartbeat step writes every job file and registers it only when that is
plainly meant. It registers nothing, and says so in one sentence, when
EXO_INSTALL_NO_SCHEDULER=1 is set (a testing hook, the same shape as the sync
tool's own), or when this copy of the program is running from the system's
temporary folder — a job registered from there outlives the copy and points at
nothing. EXO_INSTALL_REAL_SCHEDULER=1 overrides the second of those.

The steps of an install, in order:

  1 machine.json    sync.py bootstrap writes it, or this verifies it
  2 the brain       JOIN an existing brain, or make one; then sync.py pull. A
                    failed pull is a STOP, never a half-brain, and success is
                    never reported without `git -C <brain> rev-parse HEAD`
  3 the seeds       the shipped routine and watcher templates copied into the
                    live folders WHEN ABSENT - a file of yours is never
                    overwritten - and each one recorded in installed.json. A
                    file marked as an EXAMPLE on its first line (another
                    person's pages, shipped to show the shape) is refused: an
                    example never lands in a live brain
  4 the laws        laws/LAWS.md rendered for this machine (its two tokens
                    filled) into <claude root>/exocortex-laws.md — the
                    program's file, never carried, re-rendered when the shipped
                    book changes. <hub>/dossier/LAWS.md, YOUR law book, is
                    written WHEN ABSENT as its two-line header and never again:
                    every rule you ratify is written there, never into the
                    engine's book. <claude root>/CLAUDE.md, WHEN ABSENT, is
                    written once as three lines of yours that load both; a
                    CLAUDE.md of yours is never edited, and one line says how
                    to load them. <codex root>/AGENTS.md, when the machine
                    records a Codex root and has none, is written once from
                    openai/AGENTS.md, naming the same two files. The shipped
                    skills are copied to <claude root>/skills/ when absent.
                    Every write recorded in installed.json
  5 the heartbeat   the jobs of install/jobs.json, rendered per OS: launchd
                    agents on macOS, scheduled tasks on Windows
  6 the watchers    every routine in <hub>/routines/ rendered for this machine,
                    the run files seeded, hygiene-settings.json seeded with the
                    built-in periods when the hub has none, and one landing
                    sheet written for the session that registers them in the app
  7 the tree        orchestrator.py, pulse.py, then tree.html is opened —
                    drawn but not opened when this copy runs from the system's
                    temporary folder (a rehearsal throws no window at anyone)

Three honest roads to a brain, and no fourth:
  JOIN            --brain <url or path>: clone it, and use what is there
  NEW, local only --defaults, or the answer to the question: a repository on
                  this disk. It is yours and it is NOT backed up anywhere.
  NEW, with a remote  --brain-remote <url>: made here, pushed there.

The way out, --uninstall, reads installed.json and removes only what it
records, each thing checked first: a job by the name jobs.json renders for it,
verified present, then unloaded (launchd) or unregistered (Task Scheduler) and
its file removed; a rendered prompt or the landing sheet only while it still
carries the bytes the installer wrote; a skill only while it matches the
shipped copy byte for byte. The scheduler wall above holds here too: from the
temporary folder, or with EXO_INSTALL_NO_SCHEDULER=1, nothing is asked of the
scheduler, and only a job file that was never handed to it is removed.
installed.json stays, marked `uninstalled`, as the record of what was removed.

Every step prints OK <what> or STOP: <why>, and the first STOP ends the run.
Idempotent: a second run is a repair. Nothing is ever re-registered while it
reads back identical, every write is atomic and read back, and the DONE line
prints only when every step's read-back passed. Nothing here ever commits,
rebases or merges anything but a fast-forward you asked for, and ownership of
a path never changes without you moving the file yourself.
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):          # cp1252 consoles, never a crash
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

ENGINE = Path(__file__).resolve().parent
INSTALL_DIR = ENGINE / "install"
TEMPLATES = INSTALL_DIR / "templates"
JOBS_FILE = INSTALL_DIR / "jobs.json"
LOCK_FILE = INSTALL_DIR / ".lock"
LOCK_STALE_SECONDS = 3600

LAYOUT_LEGACY = "legacy"
LAYOUT_PROGRAM = "program-tree"
PARTITION_GIT = "git-ignore"
BRAIN_FOLDER_DEFAULT = "exocortex-brain"
INSTALLED_NAME = "installed.json"

# The program's own folders, and the files it owns at the top level. A release
# may add paths only inside this set; anything else in the hub folder is the
# user's. Kept here so --repair can say which folder a file
# of the user's has landed in.
RESERVED_FOLDERS = ("tools", "sync", "templates", "docs", "laws", "licenses",
                    "tests", "grok", "openai", ".github", "fonts")
RESERVED_FILES = ("LICENSE", "NOTICE", "README.md", "CONTRIBUTING.md",
                  "CHANGELOG.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "VERSION",
                  ".gitignore", ".gitattributes", "orchestrator.py", "skin_v2.py",
                  "skin_v2_fonts.css", "evidence.py", "semantic-rules.json")


def load_by_path(name, path):
    """A module loaded from a FILE. Never a package import: the program is not
    on anyone's import path when this runs."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def plain_json(path):
    try:
        with open(str(path), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except (IOError, OSError, ValueError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def find_resolver():
    """The same ten lines sync.py carries: the program tree first, then the hub
    the machine file beside this one records."""
    beside = ENGINE.parent / "tools" / "exo_paths.py"
    if beside.is_file():
        return load_by_path("exo_paths", beside), str(beside)
    record = plain_json(ENGINE / "machine.json") or {}
    hub = (record.get("roots") or {}).get("orchestrator")
    if hub:
        module_file = Path(str(hub)).expanduser() / "tools" / "exo_paths.py"
        if module_file.is_file():
            return load_by_path("exo_paths", module_file), str(module_file)
        return None, str(module_file)
    return None, str(beside)


def find_registry():
    """The person's own names, loaded the same way the resolver is: by file
    path, from the hub's tools folder. Never a package import."""
    beside = ENGINE.parent / "tools" / "exo_registry.py"
    if beside.is_file():
        return load_by_path("exo_registry", beside), str(beside)
    record = plain_json(ENGINE / "machine.json") or {}
    hub = (record.get("roots") or {}).get("orchestrator")
    if hub:
        module_file = Path(str(hub)).expanduser() / "tools" / "exo_registry.py"
        if module_file.is_file():
            return load_by_path("exo_registry", module_file), str(module_file)
    return None, str(beside)


RESOLVER, RESOLVER_FILE = find_resolver()
PATHS = {}
if RESOLVER is not None:
    try:
        PATHS = RESOLVER.paths(tool_file=__file__)
    except Exception:
        PATHS = {}
LAYOUT = PATHS.get("layout") or (
    LAYOUT_PROGRAM if (ENGINE.parent / "tools" / "exo_paths.py").is_file()
    else LAYOUT_LEGACY)
PROGRAM_TREE = LAYOUT == LAYOUT_PROGRAM
# In a program tree the hub is the folder above the sync package, and the
# machine file lives in it. In the older layout both come from the record
# beside this file, exactly as they always have.
HUB_GUESS = Path(PATHS["hub"]) if PATHS.get("hub") else ENGINE.parent
MACHINE_FILE = (Path(PATHS["machine_file"]) if PATHS.get("machine_file")
                else ((HUB_GUESS / "machine.json") if PROGRAM_TREE
                      else ENGINE / "machine.json"))
SHIPPED_TEMPLATES = HUB_GUESS / "templates"

REGISTRY_MODULE, REGISTRY_FILE = find_registry()


def registry_record():
    """The person's names, or every default when this version ships without
    the loader. A missing registry is never a STOP: it is a person who has not
    written one, and the sheet then says `the owner`."""
    if REGISTRY_MODULE is None:
        return None
    try:
        return REGISTRY_MODULE.registry(hub=str(HUB_GUESS))
    except Exception:
        return None


def owner_name(when_unset="the owner"):
    record = registry_record()
    if record is None:
        return when_unset
    try:
        return REGISTRY_MODULE.owner_label(record, when_unset)
    except Exception:
        return when_unset

WINDOWS = os.name == "nt"
OSKEY = "windows" if WINDOWS else "macos"

# The scheduler is the one thing in this installer that is not confined to a
# folder. launchd and Task Scheduler belong to the MACHINE: a job registered
# from a copy of this program that is about to be deleted outlives the copy and
# points at nothing. So the heartbeat step writes every job file and hands it
# over only when it is sure that is meant.
#
#   EXO_INSTALL_NO_SCHEDULER=1   a testing hook, the same shape as the sync
#                                tool's own: write the files, register nothing.
#   running from a temporary folder: register nothing, and say so. A copy in
#                                the system's temporary folder is a rehearsal
#                                or a gate, not an installation.
#   EXO_INSTALL_REAL_SCHEDULER=1 overrides the second of those, for the one
#                                person who really did unpack there on purpose.
NO_SCHEDULER = bool(os.environ.get("EXO_INSTALL_NO_SCHEDULER", "").strip())
REAL_SCHEDULER = bool(os.environ.get("EXO_INSTALL_REAL_SCHEDULER", "").strip())


def temp_roots():
    """Every folder this machine calls temporary: the one this process was
    given (TMPDIR and its kin), and the system's own whatever TMPDIR says — a
    child pointed at a temp folder of its own is still running out of the
    system's scratch."""
    found = [tempfile.gettempdir()]
    if sys.platform == "darwin":
        found.append("/private/var/folders")    # where macOS keeps every user's own temp
    if os.name == "nt":
        for key in ("LOCALAPPDATA", "SystemRoot", "WINDIR"):
            if os.environ.get(key):
                found.append(os.path.join(os.environ[key], "Temp"))
    else:
        found += ["/tmp", "/var/tmp"]
    roots = []
    for folder in found:
        try:
            if folder:
                roots.append(Path(folder).resolve())
        except (OSError, ValueError):
            pass
    return roots


def in_temp_folder():
    """Is this copy of the installer running out of the system's scratch?"""
    try:
        here = Path(__file__).resolve().parent
    except (OSError, ValueError):
        return False
    return any(here == temp or temp in here.parents for temp in temp_roots())


def scheduler_held():
    """One plain sentence when the machine's scheduler is not to be touched,
    or None when it is."""
    if NO_SCHEDULER:
        return "EXO_INSTALL_NO_SCHEDULER is set"
    if in_temp_folder() and not REAL_SCHEDULER:
        return ("this copy of the program is running from the system's temporary folder, "
                "and a job registered here would outlive it and point at nothing — set "
                "EXO_INSTALL_REAL_SCHEDULER=1 if you really did install it there")
    return None

def page_open_held():
    """One plain sentence when the tree page is drawn but must not be opened,
    or None. A copy running from the system's temporary folder is a rehearsal
    or a gate: the page it draws is real, but a window thrown at whoever sits
    at this machine is not (the same reasoning as the scheduler's wall)."""
    if in_temp_folder():
        return ("this copy of the program is running from the system's temporary "
                "folder, so the page is drawn and not opened")
    return None

HYGIENE_SETTINGS = "hygiene-settings.json"      # the user's own sanitize periods
HYGIENE_DEFAULTS = {"grace_hours": 24, "ceiling": 12,
                    "routine_grace_hours": 0, "spoolup_quiet_hours": 6}

PRESENT = "PRESENT"
CREATED = "CREATED"
REPAIRED = "REPAIRED"
WOULD_CREATE = "WOULD CREATE"
WOULD_REPAIR = "WOULD REPAIR"
SKIPPED = "SKIPPED"

DONE_TEMPLATE = ("EXOCORTEX INSTALLED · %(machine)s · machine.json %(mj)s"
                 " · heartbeat %(hb)d/%(hbn)d · watchers %(w)d rendered,"
                 " paste printed · %(tree)s")


class Stop(Exception):
    """The first STOP ends the run."""


# ---------------------------------------------------------------- small tools

def say(text=""):
    print(text)


def mark(status, what, detail=""):
    line = "  %-12s %s" % (status, what)
    if detail:
        line += "  -- " + detail
    print(line)


def run(cmd, cwd=None):
    proc = subprocess.run([str(c) for c in cmd], cwd=(str(cwd) if cwd else None),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, encoding="utf-8",
                          errors="replace")
    return proc.returncode, proc.stdout or ""


def sha(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def read_text(path):
    try:
        with open(str(path), "rb") as handle:
            return handle.read().decode("utf-8")
    except (IOError, OSError):
        return None


def write_atomic(path, text, keep_prev=True):
    """Write beside the target, then replace it; keep the old copy as .prev on a
    repair; read the result back and hash it. Returns the sha of what is on
    disk, or raises Stop when the read-back does not match."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    old = None
    if path.exists():
        with open(str(path), "rb") as handle:
            old = handle.read()
    if old is not None and old != data and keep_prev:
        prev = path.with_name(path.name + ".prev")
        tmp_prev = path.with_name(path.name + ".prev.tmp-%d" % os.getpid())
        with open(str(tmp_prev), "wb") as handle:
            handle.write(old)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_prev), str(prev))
    tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
    with open(str(tmp), "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(tmp), str(path))
    with open(str(path), "rb") as handle:
        back = handle.read()
    if back != data:
        raise Stop("read-back of %s did not match what was written" % path)
    return sha(back)


def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def retire_prev(ctx, path):
    """The rollback copy a repair left behind is kept until the next successful
    run - this is that run, and this file came back good."""
    prev = Path(str(path) + ".prev")
    if ctx.dry or not prev.exists():
        return
    try:
        prev.unlink()
    except OSError:
        return
    ctx.note("CLEARED", "%s.prev" % Path(path).name,
             "the file reads good again; the rollback copy is retired")


# ------------------------------------------------------------------- the lock

class Lock(object):
    """One installer at a time in one engine folder (proof case 6)."""

    def __init__(self, path):
        self.path = Path(path)
        self.held = False

    def acquire(self):
        existing = read_text(self.path)
        if existing:
            try:
                info = json.loads(existing)
            except ValueError:
                info = {}
            started = info.get("started", "")
            age = None
            try:
                age = (datetime.datetime.now()
                       - datetime.datetime.fromisoformat(started)).total_seconds()
            except (ValueError, TypeError):
                age = None
            if age is not None and age < LOCK_STALE_SECONDS:
                raise Stop("another install.py holds %s (pid %s, since %s) - "
                           "wait for it, or delete the lock if that run is gone"
                           % (self.path, info.get("pid", "?"), started or "?"))
            say("  note         stale lock taken over (pid %s, since %s)"
                % (info.get("pid", "?"), started or "?"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(self.path, json.dumps(
            {"pid": os.getpid(), "started": now_iso()}) + "\n", keep_prev=False)
        self.held = True

    def release(self):
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass
            self.held = False


# --------------------------------------------------------------- the context

class Ctx(object):
    def __init__(self, args):
        self.args = args
        self.dry = args.dry_run
        self.report = []
        self.machine = None
        self.roots = {}
        self.python = sys.executable or ("python" if WINDOWS else "python3")
        self.pythonw = self.python
        if WINDOWS:
            cand = Path(self.python).with_name("pythonw.exe")
            if cand.exists():
                self.pythonw = str(cand)
        self.py_cmd = "python" if WINDOWS else "python3"
        self.sep = "\\" if WINDOWS else "/"
        self.heartbeat_present = 0
        self.heartbeat_total = 0
        self.wrapper_present = 0
        self.watchers_present = 0
        self.rendered = 0
        self.tree_opened = False
        self.tree_drawn = False
        self.ps_driver = None
        self.scratch = None

    # roots ------------------------------------------------------------------
    @property
    def hub(self):
        return Path(self.roots["orchestrator"])

    @property
    def home(self):
        return Path(self.roots["home"])

    @property
    def claude(self):
        return Path(self.roots["claude"])

    def note(self, status, what, detail=""):
        self.report.append((status, what, detail))
        mark(status, what, detail)

    @property
    def brain(self):
        """The brain clone: where the mirror of your own files lives. In the
        older layout that is the folder this file sits in."""
        recorded = self.roots.get("brain")
        if recorded:
            return Path(recorded)
        return ENGINE if not PROGRAM_TREE else (self.home / BRAIN_FOLDER_DEFAULT)

    def subs(self):
        return {
            "{hub}": str(self.hub),
            "{home}": str(self.home),
            "{claude}": str(self.claude),
            "{projects}": str(Path(self.roots.get("projects", ""))),
            "{syncdir}": str(ENGINE),
            "{brain}": str(self.brain),
            "{python}": self.python,
            "{pythonw}": self.pythonw,
            "{machine}": self.machine,
        }

    def fill(self, text):
        for key, value in self.subs().items():
            text = text.replace(key, value)
        return text


# ------------------------------------------------------- step 1: machine.json

def default_machine_name():
    name = (platform.node() or "machine").split(".")[0].strip().lower()
    return re.sub(r"[^a-z0-9-]+", "-", name) or "machine"


def ask(prompt, default):
    if not sys.stdin or not sys.stdin.isatty():
        return default
    try:
        answer = input("%s [%s]: " % (prompt, default)).strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return answer or default


def step_machine(ctx):
    say("1. machine.json")
    machine_file = MACHINE_FILE
    existing = read_text(machine_file)
    if existing:
        try:
            data = json.loads(existing)
        except ValueError:
            raise Stop("machine.json is not readable JSON: %s" % machine_file)
        roots = data.get("roots") or {}
        missing = [k for k in ("home", "claude", "projects", "orchestrator")
                   if not roots.get(k)]
        if missing:
            raise Stop("machine.json is missing roots: %s" % ", ".join(missing))
        ctx.machine = data.get("name") or default_machine_name()
        ctx.roots = dict(roots)
        if PROGRAM_TREE:
            repair_record(ctx, data, machine_file)
        ctx.note(PRESENT, "machine.json (%s)" % ctx.machine, str(machine_file))
        say("   OK machine.json")
        return

    home = Path.home()
    name = ctx.args.machine or default_machine_name()
    hub = HUB_GUESS if PROGRAM_TREE else home / "Exocortex"
    projects = home / "Projects"
    claude = home / ".claude"
    brain = home / BRAIN_FOLDER_DEFAULT
    if not ctx.args.defaults and not ctx.dry:
        name = ask("machine name", name)
        if not PROGRAM_TREE:
            hub = Path(ask("hub folder", str(hub)))
        projects = Path(ask("projects root", str(projects)))
        claude = Path(ask("claude root", str(claude)))
        if PROGRAM_TREE:
            brain = Path(ask("brain folder (your own files' repository)", str(brain)))
    ctx.machine = name
    ctx.roots = {"home": str(home), "claude": str(claude),
                 "projects": str(projects), "orchestrator": str(hub)}
    if PROGRAM_TREE:
        ctx.roots["brain"] = str(brain)
    if ctx.dry:
        ctx.note(WOULD_CREATE, "machine.json (%s)" % name, str(machine_file))
        say("   OK machine.json (dry run)")
        return
    argv = [ctx.python, str(ENGINE / "sync.py"), "bootstrap",
            "--machine", name,
            "--orchestrator-root", str(hub),
            "--projects-root", str(projects),
            "--claude-root", str(claude)]
    if PROGRAM_TREE:
        # The record says the layout and the division outright. Nothing later
        # infers either from the presence of a .git folder.
        argv += ["--layout", LAYOUT_PROGRAM, "--partition", PARTITION_GIT,
                 "--brain-root", str(brain), "--no-pull"]
    code, out = run(argv, cwd=ENGINE)
    for line in out.rstrip("\n").split("\n"):
        if line.strip():
            say("     " + line)
    if code != 0 or not machine_file.exists():
        raise Stop("sync.py bootstrap failed (exit %d)" % code)
    data = json.loads(read_text(machine_file))
    if PROGRAM_TREE:
        repair_record(ctx, data, machine_file)
    codex = Path(data["roots"]["home"]) / ".codex"
    if "codex" not in data["roots"] and codex.exists():
        data["roots"]["codex"] = str(codex)
        write_atomic(machine_file, json.dumps(data, indent=2) + "\n",
                     keep_prev=False)
        say("     added roots.codex %s" % codex)
    ctx.roots = dict(data["roots"])
    ctx.machine = data.get("name") or name
    ctx.note(CREATED, "machine.json (%s)" % ctx.machine, str(machine_file))
    say("   OK machine.json")


# --------------------------------------------- the record, and what it records

def repair_record(ctx, data, machine_file):
    """A program tree says what it is, in writing.

    The layout, the division of the hub folder and where the brain lives are
    RECORDED, never inferred later from a .git folder: a tree caught halfway
    through an install would otherwise be mirrored whole, and the program's own
    deny-by-default rule file would land inside the brain's repository.
    -> True when anything was written."""
    wanted = {
        "layout": LAYOUT_PROGRAM,
        "partition": PARTITION_GIT,
    }
    changed = [k for k, v in wanted.items() if data.get(k) != v]
    roots = data.setdefault("roots", {})
    if not roots.get("brain"):
        roots["brain"] = str(ctx.roots.get("brain")
                             or (Path(roots.get("home") or Path.home())
                                 / BRAIN_FOLDER_DEFAULT))
        changed.append("roots.brain")
    if roots.get("sync") != str(Path(roots["orchestrator"]) / "sync"):
        roots["sync"] = str(Path(roots["orchestrator"]) / "sync")
        changed.append("roots.sync")
    if not changed:
        return False
    data.update(wanted)
    if ctx.dry:
        ctx.note(WOULD_REPAIR, "machine.json records the layout",
                 ", ".join(changed))
        return False
    write_atomic(machine_file, json.dumps(data, indent=2, sort_keys=True) + "\n",
                 keep_prev=False)
    ctx.roots = dict(data["roots"])
    ctx.note(REPAIRED, "machine.json records the layout", ", ".join(changed))
    return True


# ---------------------------------------------------------- what was installed

def installed_file(ctx):
    return ctx.hub / INSTALLED_NAME


def read_installed(ctx):
    data = plain_json(installed_file(ctx))
    if data is None:
        template = plain_json(SHIPPED_TEMPLATES / INSTALLED_NAME)
        data = template if template is not None else {"version": 1, "seeded": []}
    data.setdefault("seeded", [])
    data.setdefault("jobs", [])
    return data


def write_installed(ctx, data):
    """This machine's own record of what the installer put here. It is on the
    never-sync list: it describes THIS disk and travels nowhere."""
    if ctx.dry:
        return
    data["machine"] = ctx.machine
    data["layout"] = LAYOUT
    data["installed"] = now_iso()
    version = read_text(ctx.hub / "VERSION")
    data["program_version"] = (version or "").strip()
    write_atomic(installed_file(ctx),
                 json.dumps(data, indent=2, sort_keys=True) + "\n", keep_prev=False)


# ------------------------------------------------------------ step 2: the brain

def git_in(path, *args):
    return run(["git", "-C", str(path)] + [str(a) for a in args])


def brain_has_head(brain):
    code, _out = git_in(brain, "rev-parse", "HEAD")
    return code == 0


# ASSUMES: git can name a committer on this machine. False on a fresh machine whose
# hostname carries no domain (Windows, most often: "unable to auto-detect email
# address ... (none)") and wherever user.useConfigOnly is set: the first commit of the
# hub or the brain fails there, and so would every commit sync.py makes later. So a
# repository this installer makes or adopts carries a LOCAL identity when git has
# none -- never a global one, never over one the person set.
IDENTITY_DOMAIN = "exocortex.invalid"


def ensure_git_identity(ctx, repo, what):
    """Give `repo` a local git identity when git cannot find one on this machine.
    Returns True when one was written, False when git already had one."""
    code, _out = git_in(repo, "var", "GIT_COMMITTER_IDENT")
    if code == 0:
        return False
    login = ""
    for key in ("USER", "LOGNAME", "USERNAME"):
        login = (os.environ.get(key) or "").strip()
        if login:
            break
    login = re.sub(r"[^A-Za-z0-9._-]", "", login) or "exocortex"
    name, email = login, "%s@%s" % (login, IDENTITY_DOMAIN)
    for key, value in (("user.name", name), ("user.email", email)):
        code, out = git_in(repo, "config", "--local", key, value)
        if code != 0:
            raise Stop("git has no identity on this machine, and %s could not be given "
                       "one: %s" % (what, out.strip()))
    ctx.note(CREATED, "git identity for %s" % what, "%s <%s>" % (name, email))
    say("   OK %s: git had no identity on this machine, so this repository carries a "
        "local one, %s <%s>. To use your own instead:" % (what, name, email))
    say("       git config --global user.name \"Your Name\"")
    say("       git config --global user.email you@example.com")
    return True


# What a brain repository keeps out of itself, written when one is made. Every
# line here describes THIS disk, so carrying it to another machine would make
# that machine read this one's bookkeeping as its own — and every file it had
# not pulled yet would look deleted. The name is built rather than written so
# that no file in this program's own source is called .gitignore.
BRAIN_IGNORE_NAME = ".git" + "ignore"
BRAIN_IGNORE = ("# Bookkeeping each machine keeps for itself. It describes ONE disk,\n"
                "# so it never travels to the other one.\n"
                ".sync-state*.json\n"
                "machine.json\n"
                "installed.json\n")


def make_brain(ctx, brain, remote=None):
    """A new brain repository on this disk, with its first commit in it."""
    brain.mkdir(parents=True, exist_ok=True)
    code, out = run(["git", "init", str(brain)])
    if code != 0:
        raise Stop("git init %s failed: %s" % (brain, out.strip()))
    ensure_git_identity(ctx, brain, "the brain")
    rules = brain / BRAIN_IGNORE_NAME
    if not rules.exists():
        write_atomic(rules, BRAIN_IGNORE, keep_prev=False)
    readme = brain / "README.md"
    if not readme.exists():
        write_atomic(readme,
                     "# Your brain\n\nThis repository is the private half of your exocortex:"
                     " your own notes,\nrecords and state, mirrored from the hub folder by"
                     " sync.py. Nothing in\nhere is the program, and none of it is meant to"
                     " be public.\n", keep_prev=False)
    git_in(brain, "add", "-A")
    code, out = git_in(brain, "commit", "-m", "brain: first commit")
    if code != 0 and not brain_has_head(brain):
        raise Stop("the brain's first commit failed: %s" % out.strip())
    if remote:
        code, out = git_in(brain, "remote", "add", "origin", remote)
        if code != 0:
            git_in(brain, "remote", "set-url", "origin", remote)
        ctx.note(CREATED, "brain remote", remote)
    return brain


def join_brain(ctx, brain, source):
    """JOIN: the brain already exists somewhere; this machine clones it."""
    if brain.exists() and any(brain.iterdir()):
        raise Stop("%s is not empty, so this machine will not clone a brain over it. "
                   "Move it aside, or point --brain at a folder that does not exist yet."
                   % brain)
    brain.parent.mkdir(parents=True, exist_ok=True)
    code, out = run(["git", "clone", str(source), str(brain)])
    if code != 0:
        raise Stop("cloning the brain from %s failed: %s" % (source, out.strip()))
    ensure_git_identity(ctx, brain, "the brain")
    return brain


# A program tree unpacked from an archive has no .git, and the brain step divides the
# hub through git: what git tracks is the program's, what the rule file ignores is
# yours. So the hub becomes a repository of its own first: the rule file in place,
# the program's files committed. Nothing of it is recorded, so the way out leaves it.
def hub_repository(ctx):
    if not PROGRAM_TREE:
        return
    if (ctx.hub / ".git").exists():
        if not ctx.dry:
            ensure_git_identity(ctx, ctx.hub, "the hub")
        return
    if ctx.dry:
        ctx.note(WOULD_CREATE, str(ctx.hub / ".git"), "the hub, a repository of its own")
        say("   OK hub (dry run): would become a repository of its own")
        return
    rule, shipped = ctx.hub / ".gitignore", SHIPPED_TEMPLATES / "dot-gitignore"
    if not rule.exists():
        if not shipped.is_file():
            raise Stop("the hub has no .git and no rule file to divide it by (.gitignore, "
                       "or templates/dot-gitignore), so nothing of it was committed")
        write_atomic(rule, read_text(shipped) or "", keep_prev=False)
    code, out = run(["git", "init", "-q", str(ctx.hub)])
    if code != 0:
        raise Stop("git init %s failed: %s" % (ctx.hub, out.strip()))
    ensure_git_identity(ctx, ctx.hub, "the hub")
    # ASSUMES: the held installer lock is transient machine state, never program
    # history. Keep the lock held, but exclude it from the first program commit.
    code, out = git_in(ctx.hub, "add", "-A", "--", ".",
                       ":(top,exclude)sync/install/.lock")
    if code != 0:
        raise Stop("git add in %s failed: %s" % (ctx.hub, out.strip()))
    code, out = git_in(ctx.hub, "commit", "-q", "-m", "the program, as unpacked")
    if code != 0 and not brain_has_head(ctx.hub):
        raise Stop("the hub's first commit failed: %s" % out.strip())
    ctx.note(CREATED, str(ctx.hub / ".git"), "the hub, a repository of its own")
    say("   OK hub: a repository of its own (the program's files committed; your own "
        "files stay yours, the brain carries them)")


def step_brain(ctx):
    say("2. the brain")
    hub_repository(ctx)
    brain = ctx.brain
    if ctx.dry:
        ctx.note(SKIPPED, "the brain", "dry run changes nothing")
        say("   OK brain (dry run)")
        return
    if PROGRAM_TREE:
        joined = getattr(ctx.args, "brain", None)
        remote = getattr(ctx.args, "brain_remote", None)
        if brain_has_head(brain):
            ctx.note(PRESENT, "the brain (%s)" % brain)
        elif joined:
            join_brain(ctx, brain, joined)
            ctx.note(CREATED, "the brain, joined from %s" % joined, str(brain))
        elif remote:
            make_brain(ctx, brain, remote=remote)
            ctx.note(CREATED, "the brain, new, with a remote", str(brain))
        else:
            make_brain(ctx, brain)
            ctx.note(CREATED, "the brain, new, on this disk alone", str(brain))
            say("     This brain lives here and NOWHERE else: it is not backed up.")
            say("     When you have a private repository for it, add it with:")
            say("       git -C %s remote add origin <url>" % brain)
        # Success is never reported without the repository answering for itself.
        if not brain_has_head(brain):
            raise Stop("%s is not a git repository with a commit in it, so there is no "
                       "brain to sync with. Nothing else was done." % brain)
    ensure_git_identity(ctx, brain, "the brain")
    code, out = run([ctx.python, str(ENGINE / "sync.py"), "pull"], cwd=ENGINE)
    tail = [l for l in out.rstrip("\n").split("\n") if l.strip()][-6:]
    for line in tail:
        say("     " + line)
    if code != 0:
        raise Stop("sync.py pull failed (exit %d) - never continue on a "
                   "half-brain" % code)
    ctx.note(PRESENT, "brain pulled", "sync.py pull")
    say("   OK brain (%s)" % brain)


# ------------------------------------------------------------- step 3: the seeds

# Two kinds of file under templates/ are not seeds. The dot-files are rendered
# by NAME, into names this build may not even write down; installed.json is the
# record of the seeding itself and would seed itself.
NOT_SEEDS = ("installed.json",)
NOT_SEED_PREFIX = "dot-"
NOT_SEED_FOLDER = "skills"


EXAMPLE_MARK = "EXAMPLE \u2014"


def is_example(path):
    """True when a file's first line marks it as an EXAMPLE — another person's
    pages, shipped to show the shape. The seed walk refuses it wherever it sits,
    so an example never lands in a live brain."""
    try:
        with open(str(path), "rb") as handle:
            first = handle.readline(400).decode("utf-8", "replace")
    except (IOError, OSError):
        return False
    return first.lstrip("\ufeff").startswith(EXAMPLE_MARK)


def is_seed(relative):
    """True when a file under templates/ is a seed — a file the installer may
    copy into the hub when the hub does not have it yet. The shipped skills are
    NOT seeds: a session reads them from <claude root>/skills/, where step 4
    puts them, and a copy in the hub would be read by nobody and carried by the
    brain twice."""
    parts = Path(relative).parts
    if not parts:
        return False
    if parts[0] == NOT_SEED_FOLDER:
        return False
    if parts[-1] in NOT_SEEDS:
        return False
    return not any(part.startswith(NOT_SEED_PREFIX) for part in parts)


def seed_pairs(ctx):
    """[(shipped template, where it goes live)] — EVERY file under templates/
    at the same relative path in the hub, except the dot-files (rendered by
    name), the install record itself and the skills (step 4 places them).

    The shipped copies live under templates/ and the live files are yours: no
    folder holds both. One rule, so a seed a
    later release adds needs no change here to arrive."""
    pairs = []
    source = SHIPPED_TEMPLATES
    if not source.is_dir():
        return pairs
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if not is_seed(relative):
            continue
        pairs.append((path, ctx.hub / relative))
    return pairs


def step_seeds(ctx):
    say("3. the seeds")
    if not PROGRAM_TREE:
        ctx.note(SKIPPED, "the seeds", "the older layout carries its own routines")
        say("   OK seeds (nothing to seed in this layout)")
        return
    if not SHIPPED_TEMPLATES.is_dir():
        ctx.note(SKIPPED, "the seeds", "this version ships no templates folder")
        say("   OK seeds (this version ships none)")
        return
    installed = read_installed(ctx)
    known = set(installed.get("seeded") or [])
    copied = 0
    for source, target in seed_pairs(ctx):
        rel = target.relative_to(ctx.hub).as_posix()
        if is_example(source):
            ctx.note(SKIPPED, rel, "refused: an EXAMPLE page never lands in a live brain")
            continue
        if target.exists():
            # A live file is NEVER overwritten, whether this installer wrote it
            # the first time or you did. Yours from the moment it exists.
            ctx.note(PRESENT, rel, "already here; left exactly as it is")
            continue
        if ctx.dry:
            ctx.note(WOULD_CREATE, rel, "seeded from templates/")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, read_text(source) or "", keep_prev=False)
        known.add(rel)
        copied += 1
        ctx.note(CREATED, rel, "seeded from templates/")
    installed["seeded"] = sorted(known)
    write_installed(ctx, installed)
    say("   OK seeds (%d copied, %d recorded)" % (copied, len(known)))


# ------------------------------------------------------------- step 4: the laws

# The program's own law book and skills, as shipped. The session reads its
# rules from <claude root>/CLAUDE.md and its skills from <claude root>/skills/,
# so this step is what puts them where they are read.
LAW_BOOK = HUB_GUESS / "laws" / "LAWS.md"
SHIPPED_SKILLS = SHIPPED_TEMPLATES / "skills"
# ONE road for the laws, on every machine: the rendering lives
# beside CLAUDE.md, under the claude root. The brain carries CLAUDE.md, skills/
# and the memories from that root and nothing else, so this file never leaves
# THIS machine and always carries this machine's own paths — and the one line
# that loads it, written home-relative, is right on every machine the brain
# carries CLAUDE.md to.
LAWS_BESIDE = "exocortex-laws.md"
CLAUDE_MD_TITLE = "# Your instructions — the lines below load the exocortex laws and yours"
# YOUR law book: in the hub, so the brain carries it to every machine. Written
# once as its header when absent (the seed walk's own copy when it ran first)
# and never again by this installer — every rule you ratify goes there.
USER_BOOK = ("dossier", "LAWS.md")
USER_BOOK_SEED = SHIPPED_TEMPLATES / "dossier" / "LAWS.md"
USER_BOOK_HEADER = (
    "# Your laws — the rules you ratified, in your own words\n"
    "<!-- exocortex:laws · every promotion writes here, never the engine's "
    "exocortex-laws.md. Edit freely: sessions read this file at every wake. -->\n")
# The other vendors read no `@` line: their rules file NAMES the same two files.
AGENTS_TEMPLATE = HUB_GUESS / "openai" / "AGENTS.md"
UNFILLED = re.compile(r"\{\{[^{}\n]*\}\}")


def quoted(part):
    """A command part as a shell reads it: quoted only when it has a space."""
    part = str(part)
    return '"%s"' % part if any(ch.isspace() for ch in part) else part


def sync_command(ctx):
    """The installed sync command, with the interpreter that runs it."""
    return "%s %s" % (quoted(ctx.python), quoted(ENGINE / "sync.py"))


def render_laws(ctx, text):
    """(the law book rendered for this machine, [tokens still unfilled]).
    The law book's own rule: an unresolved token means setup is incomplete, so
    a rendering with one left in it is never written."""
    for token, value in (("{{HUB}}", str(ctx.hub)), ("{{SYNC}}", sync_command(ctx))):
        text = text.replace(token, value)
    left = sorted(set(UNFILLED.findall(text)))
    if not left and "{{" in text:
        left = ["{{"]
    return text, left


def home_form(ctx, path):
    """`~/<rest>` for a path under the home root, else the path itself."""
    try:
        return "~/" + Path(path).relative_to(ctx.home).as_posix()
    except ValueError:
        return str(path)


def read_mine(path):
    """A file of the user's, for comparing only: bytes decoded leniently, so a
    file in another encoding is still read, never a crash. None when absent;
    Stop when it is there and cannot be read — it is never written over."""
    if not path.exists():
        return None
    try:
        with open(str(path), "rb") as handle:
            return handle.read().decode("utf-8", "replace")
    except (IOError, OSError) as exc:
        raise Stop("%s is there but could not be read (%s) — it was not touched, and "
                   "nothing was written" % (path, exc))


def step_laws(ctx):
    say("4. the laws")
    if not PROGRAM_TREE:
        ctx.note(SKIPPED, "the laws", "the older layout keeps its own CLAUDE.md")
        say("   OK laws (nothing to render in this layout)")
        return
    source = read_text(LAW_BOOK)
    if source is None:
        ctx.note(SKIPPED, "the laws", "this version ships no laws/LAWS.md")
        say("   OK laws (this version ships no law book)")
        return
    rendered, left = render_laws(ctx, source)
    if left:
        raise Stop("laws/LAWS.md carries %s, which this installer cannot fill — nothing "
                   "was written; the law book itself needs repair" % ", ".join(left))
    installed = read_installed(ctx)
    record = installed.get("laws") if isinstance(installed.get("laws"), dict) else {}
    shipped = sha(source)
    claude_md = ctx.claude / "CLAUDE.md"
    beside = ctx.claude / LAWS_BESIDE
    user_book = ctx.hub.joinpath(*USER_BOOK)
    load = "@" + home_form(ctx, beside)
    load_yours = "@" + home_form(ctx, user_book)
    mine = read_mine(claude_md)
    have = read_mine(beside)
    wrote = False
    laws = dict(record)

    # THE RENDERING — the program's file, this machine's paths. Written when
    # absent; rendered again when it is not this machine's rendering of the
    # book that ships now (the shipped book changed, or the hub moved).
    if have is None or have != rendered:
        why = ("the starter laws, rendered for this machine" if have is None
               else "rendered again: the shipped law book changed"
               if record.get("shipped_sha") and record.get("shipped_sha") != shipped
               else "rendered again for this machine")
        if ctx.dry:
            ctx.note(WOULD_CREATE if have is None else WOULD_REPAIR, str(beside), why)
        else:
            write_atomic(beside, rendered, keep_prev=False)
            laws.update({"to": str(beside), "shipped_sha": shipped, "rendered": now_iso(),
                         "rendered_sha": sha(rendered)})
            wrote = True
            ctx.note(CREATED if have is None else REPAIRED, str(beside), why)
    else:
        ctx.note(PRESENT, str(beside), "this machine's rendering of the shipped book")
        if record.get("shipped_sha") != shipped and not ctx.dry:
            laws.update({"to": str(beside), "shipped_sha": shipped,
                         "rendered": record.get("rendered") or now_iso()})
            wrote = True

    # YOUR law book — written once, as its header, when absent. Never again.
    if read_mine(user_book) is None:
        header = read_text(USER_BOOK_SEED) or USER_BOOK_HEADER
        if ctx.dry:
            ctx.note(WOULD_CREATE, str(user_book), "your law book: its two-line header")
        else:
            write_atomic(user_book, header, keep_prev=False)
            laws["user_book"] = {"path": str(user_book), "written": now_iso()}
            wrote = True
            ctx.note(CREATED, str(user_book), "your law book: its two-line header")
    else:
        ctx.note(PRESENT, str(user_book), "your law book; never edited by the installer")

    # CLAUDE.md — yours. When absent it is written ONCE, as three lines: a
    # title and the two imports. The token-filled text never rides the brain.
    if mine is None:
        if ctx.dry:
            ctx.note(WOULD_CREATE, str(claude_md), "three lines of yours: a title, `%s` and `%s`"
                     % (load, load_yours))
        else:
            write_atomic(claude_md, "%s\n%s\n%s\n" % (CLAUDE_MD_TITLE, load, load_yours),
                         keep_prev=False)
            laws["claude_md"] = {"path": str(claude_md), "written": now_iso()}
            wrote = True
            ctx.note(CREATED, str(claude_md), "three lines of yours: a title, `%s` and `%s`"
                     % (load, load_yours))
    else:
        ours = (laws.get("claude_md") or {}).get("path") == str(claude_md)
        ctx.note(PRESENT, str(claude_md),
                 ("yours since %s; never touched again"
                  % str(laws["claude_md"].get("written"))[:10]) if ours else "yours; not edited")
        if load not in mine and ("@" + str(beside)) not in mine:
            say("   your CLAUDE.md exists — the exocortex laws are rendered at %s; add the line "
                "`%s` to it to load them" % (beside, load))
        if load_yours not in mine and ("@" + str(user_book)) not in mine:
            say("   your CLAUDE.md exists — your own law book is %s; add the line `%s` to it "
                "to load it" % (user_book, load_yours))

    if step_agents(ctx, laws, beside, user_book):
        wrote = True

    if wrote:
        installed["laws"] = laws
    copied = step_skills(ctx, installed)
    if (wrote or copied) and not ctx.dry:
        write_installed(ctx, installed)
    say("   OK laws%s" % (" (dry run)" if ctx.dry else ""))


def render_agents(ctx, text, beside, user_book):
    """The shipped openai/AGENTS.md with its three tokens filled, and the tokens
    still unfilled."""
    for token, value in (("{{ENGINE_LAWS}}", home_form(ctx, beside)),
                         ("{{YOUR_LAWS}}", home_form(ctx, user_book)),
                         ("{{HUB}}", str(ctx.hub))):
        text = text.replace(token, value)
    left = sorted(set(UNFILLED.findall(text)))
    return text, left


def step_agents(ctx, laws, beside, user_book):
    """<codex root>/AGENTS.md — the Codex side's rules file, naming the SAME two
    law files CLAUDE.md loads. Written ONCE when the machine records a Codex
    root and the file is absent; a file of yours is never edited. -> wrote?"""
    root = ctx.roots.get("codex")
    template = read_text(AGENTS_TEMPLATE)
    # Only where Codex is actually installed: a recorded root whose folder is
    # not there is an app this machine does not have, and gets no folder made.
    if not root or template is None or not Path(root).is_dir():
        return False
    target = Path(root) / "AGENTS.md"
    rendered, left = render_agents(ctx, template, beside, user_book)
    if left:
        raise Stop("openai/AGENTS.md carries %s, which this installer cannot fill — nothing "
                   "was written" % ", ".join(left))
    have = read_mine(target)
    if have is not None:
        ctx.note(PRESENT, str(target), "yours; not edited")
        wanted = (home_form(ctx, beside), home_form(ctx, user_book))
        if not all(w in have for w in wanted):
            say("   your Codex AGENTS.md exists — name the two law files in it: %s and %s"
                % wanted)
        return False
    if ctx.dry:
        ctx.note(WOULD_CREATE, str(target), "the Codex rules file, naming the two law files")
        return False
    write_atomic(target, rendered, keep_prev=False)
    laws["agents_md"] = {"path": str(target), "written": now_iso()}
    ctx.note(CREATED, str(target), "the Codex rules file, naming the two law files")
    return True


def step_skills(ctx, installed):
    """Each shipped skill folder copied to <claude root>/skills/<name>/ WHEN
    ABSENT — a skill of yours by that name is never touched — and recorded.
    -> how many were copied."""
    if not SHIPPED_SKILLS.is_dir():
        return 0
    known = installed.get("skills") if isinstance(installed.get("skills"), dict) else {}
    copied = 0
    for folder in sorted(p for p in SHIPPED_SKILLS.iterdir() if p.is_dir()):
        target = ctx.claude / "skills" / folder.name
        label = str(target)
        if target.exists():
            ctx.note(PRESENT, label, "copied %s" % str(known[folder.name].get("copied"))[:10]
                     if isinstance(known.get(folder.name), dict)
                     else "yours; left exactly as it is")
            continue
        if ctx.dry:
            ctx.note(WOULD_CREATE, label, "copied from templates/skills/")
            continue
        staging = target.with_name(target.name + ".tmp-%d" % os.getpid())
        if staging.exists():
            shutil.rmtree(str(staging), ignore_errors=True)
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            dest = staging / path.relative_to(folder)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(str(path), "rb") as src, open(str(dest), "wb") as out:
                out.write(src.read())
                out.flush()
                os.fsync(out.fileno())
        os.replace(str(staging), str(target))
        known[folder.name] = {"to": str(target), "copied": now_iso()}
        copied += 1
        ctx.note(CREATED, label, "copied from templates/skills/")
    installed["skills"] = known
    return copied


# -------------------------------------------------------- step 3: the heartbeat

def xml_escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def task_xml(job, win, when):
    trig = win["trigger"]
    at = trig.get("at")
    if at:
        hour, minute = at.split(":")
        start = when.replace(hour=int(hour), minute=int(minute), second=0,
                             microsecond=0)
    else:
        start = when.replace(hour=0, minute=0, second=0, microsecond=0)
    boundary = start.strftime("%Y-%m-%dT%H:%M:%S")
    if trig["kind"] == "daily":
        trigger = ("  <CalendarTrigger>\n"
                   "    <StartBoundary>%s</StartBoundary>\n"
                   "    <Enabled>true</Enabled>\n"
                   "    <ScheduleByDay>\n"
                   "      <DaysInterval>1</DaysInterval>\n"
                   "    </ScheduleByDay>\n"
                   "  </CalendarTrigger>\n" % boundary)
    else:
        rep = "    <Repetition>\n      <Interval>%s</Interval>\n" % trig["interval"]
        if trig.get("duration"):
            rep += "      <Duration>%s</Duration>\n" % trig["duration"]
        rep += "      <StopAtDurationEnd>false</StopAtDurationEnd>\n    </Repetition>\n"
        tail = ("    <StartBoundary>%s</StartBoundary>\n"
                "    <Enabled>true</Enabled>\n"
                "  </TimeTrigger>\n") % boundary
        trigger = "  <TimeTrigger>\n" + rep + tail
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        "  <RegistrationInfo>\n"
        "    <Description>%s</Description>\n"
        "    <URI>\\%s</URI>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n%s  </Triggers>\n"
        "  <Principals>\n"
        '    <Principal id="Author">\n'
        "      <UserId>%%USERID%%</UserId>\n"
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <AllowHardTerminate>true</AllowHardTerminate>\n"
        "    <StartWhenAvailable>true</StartWhenAvailable>\n"
        "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
        "    <IdleSettings>\n"
        "      <StopOnIdleEnd>false</StopOnIdleEnd>\n"
        "      <RestartOnIdle>false</RestartOnIdle>\n"
        "    </IdleSettings>\n"
        "    <AllowStartOnDemand>true</AllowStartOnDemand>\n"
        "    <Enabled>true</Enabled>\n"
        "    <Hidden>false</Hidden>\n"
        "    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n"
        "    <WakeToRun>false</WakeToRun>\n"
        "    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>\n"
        "    <Priority>7</Priority>\n"
        "  </Settings>\n"
        '  <Actions Context="Author">\n'
        "    <Exec>\n"
        "      <Command>%s</Command>\n"
        "      <Arguments>%s</Arguments>\n"
        "      <WorkingDirectory>%s</WorkingDirectory>\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
        % (xml_escape("Exocortex: " + job["what"]),
           xml_escape(win["task_name"]),
           trigger,
           xml_escape(win["execute"]),
           xml_escape(win["arguments"]),
           xml_escape(win["workdir"])))


def load_jobs():
    text = read_text(JOBS_FILE)
    if text is None:
        raise Stop("no %s - the engine is incomplete" % JOBS_FILE)
    return json.loads(text)["jobs"]


def windows_spec(ctx, jobs, when):
    out = []
    for job in jobs:
        win = dict(job["windows"])
        for key in ("task_name", "execute", "arguments", "workdir"):
            win[key] = ctx.fill(win[key])
        spec = {"id": job["id"], "task_name": win["task_name"],
                "execute": win["execute"], "arguments": win["arguments"],
                "workdir": win["workdir"], "trigger": win["trigger"],
                "xml": task_xml(job, win, when)}
        out.append(spec)
    return out


def render_ps_driver(ctx, specs):
    tmpl = read_text(TEMPLATES / "task.ps1.tmpl")
    if tmpl is None:
        raise Stop("no %s" % (TEMPLATES / "task.ps1.tmpl"))
    blob = json.dumps({"jobs": specs}, indent=2, ensure_ascii=True)
    script = tmpl.replace("__SPEC_JSON__", blob)
    out_dir = Path(tempfile.gettempdir()) / ("exocortex-install-%s" % ctx.machine)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "exocortex-tasks.ps1"
    with open(str(target), "wb") as handle:                 # BOM: PS 5.1 reads it
        handle.write(b"\xef\xbb\xbf" + script.encode("utf-8"))
    return target


def ps(ctx, *argv):
    cmd = ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
           "-ExecutionPolicy", "Bypass", "-File", str(ctx.ps_driver)] + list(argv)
    return run(cmd)


def read_task(ctx, name):
    code, out = ps(ctx, "-Action", "read", "-TaskName", name)
    if code != 0:
        raise Stop("reading the task %r failed: %s" % (name, out.strip()))
    line = [l for l in out.strip().split("\n") if l.strip().startswith("{")]
    if not line:
        raise Stop("the task driver printed no JSON for %r: %s" % (name, out.strip()))
    return json.loads(line[-1])


EXPECTED_KIND = {"time": "MSFT_TaskTimeTrigger", "daily": "MSFT_TaskDailyTrigger"}


def task_diff(spec, state):
    if not state.get("found"):
        return ["not registered"]
    diffs = []
    for key in ("execute", "arguments", "workdir"):
        live = (state.get(key) or "").strip()
        want = spec[key].strip()
        if live != want:
            diffs.append("%s\n        live:   %s\n        wanted: %s"
                         % (key, live, want))
    trig = spec["trigger"]
    kind = EXPECTED_KIND[trig["kind"]]
    if (state.get("triggerKind") or "") != kind:
        diffs.append("trigger kind: live %s, wanted %s"
                     % (state.get("triggerKind") or "(none)", kind))
    if trig.get("at") and (state.get("startTimeOfDay") or "") != trig["at"]:
        diffs.append("start time: live %s, wanted %s"
                     % (state.get("startTimeOfDay") or "(none)", trig["at"]))
    if trig["kind"] == "time":
        if (state.get("interval") or "") != (trig.get("interval") or ""):
            diffs.append("repeat interval: live %s, wanted %s"
                         % (state.get("interval") or "(none)", trig.get("interval")))
        if (state.get("duration") or "") != (trig.get("duration") or ""):
            diffs.append("repeat duration: live %s, wanted %s"
                         % (state.get("duration") or "(none)",
                            trig.get("duration") or "(indefinite)"))
    else:
        if str(state.get("daysInterval") or "") not in ("1",):
            diffs.append("days interval: live %s, wanted 1"
                         % (state.get("daysInterval") or "(none)"))
    return diffs


def wrapper_item(ctx, job):
    """The machine-personal python wrapper a job may need (Windows sync)."""
    win = job.get(OSKEY, {})
    wrapper = win.get("wrapper")
    if not wrapper:
        return None
    tmpl = read_text(TEMPLATES / wrapper["template"])
    if tmpl is None:
        raise Stop("no %s" % (TEMPLATES / wrapper["template"]))
    text = (tmpl.replace("__PYTHON__", ctx.python)
                .replace("__SYNC_DIR__", str(ENGINE))
                .replace("__MACHINE_TITLE__", ctx.machine.capitalize()))
    return Path(ctx.fill(wrapper["path"])), text


def plist_for(ctx, job):
    mac = job["macos"]
    tmpl = read_text(TEMPLATES / "launchd.plist.tmpl")
    if tmpl is None:
        raise Stop("no %s" % (TEMPLATES / "launchd.plist.tmpl"))
    args = "".join("<string>%s</string>" % xml_escape(ctx.fill(a))
                   for a in mac["program"])
    sched = mac["schedule"]
    if sched["kind"] == "interval":
        block = "  <key>StartInterval</key><integer>%d</integer>\n" % sched["seconds"]
    else:
        # "calendar": one or more HH:MM times of day; one time renders as a
        # dict, several as an array of dicts (both are launchd's own forms)
        times = sched.get("times") or ["%02d:%02d" % (sched["hour"], sched["minute"])]
        dicts = ["<dict><key>Hour</key><integer>%d</integer>"
                 "<key>Minute</key><integer>%d</integer></dict>"
                 % tuple(int(x) for x in t.split(":")) for t in times]
        if len(dicts) == 1:
            block = "  <key>StartCalendarInterval</key>%s\n" % dicts[0]
        else:
            block = ("  <key>StartCalendarInterval</key><array>\n%s\n  </array>\n"
                     % "\n".join("    " + d for d in dicts))
    if sched.get("run_at_load"):
        block += "  <key>RunAtLoad</key><true/>\n"
    workdir = ""
    if mac.get("workdir"):
        workdir = ("  <key>WorkingDirectory</key><string>%s</string>\n"
                   % xml_escape(ctx.fill(mac["workdir"])))
    text = (tmpl.replace("__LABEL__", mac["label"])
                .replace("__PROGRAM_ARGS__", args)
                .replace("__SCHEDULE_BLOCK__", block)
                .replace("__WORKDIR_BLOCK__", workdir)
                .replace("__LOG__", ctx.fill(mac["log"])))
    target = Path(ctx.fill("{home}")) / "Library" / "LaunchAgents" / (
        mac["label"] + ".plist")
    return target, text


PYTHON3_PATH = re.compile(r"/[\w./+-]*python3(?:\.\d+)?\b")


def plist_norm(text):
    """A plist as launchd reads it: parsed, and with every python3 path that
    exists on this machine folded to one token - /usr/bin/python3 and the
    Command Line Tools python3 are the same interpreter to the job.  None
    when the text is not a plist at all."""
    try:
        data = plistlib.loads(text.encode("utf-8"))
    except Exception:
        return None

    def fold(value):
        if isinstance(value, str):
            return PYTHON3_PATH.sub(
                lambda m: "<python3>" if os.path.exists(m.group(0)) else m.group(0),
                value)
        if isinstance(value, list):
            return [fold(v) for v in value]
        if isinstance(value, dict):
            return {k: fold(v) for k, v in value.items()}
        return value
    return fold(data)


def plist_same(live, rendered):
    """PRESENT for a launchd agent = the live file MEANS the rendered one
    (label, program, working directory, schedule, logs) - never a byte
    compare, which fails on indentation and on which python3 shim a hand
    install picked."""
    if live is None:
        return False
    a, b = plist_norm(live), plist_norm(rendered)
    return a is not None and a == b


def step_heartbeat(ctx):
    say("5. the heartbeat")
    jobs = load_jobs()
    ctx.heartbeat_total = len(jobs)      # the three JOBS; a wrapper is a part
    ctx.wrapper_total = 0
    present = 0

    # the machine-personal wrappers first: a task that points at a wrapper is
    # only right when the wrapper is right.
    for job in jobs:
        item = wrapper_item(ctx, job)
        if not item:
            continue
        ctx.wrapper_total += 1
        path, text = item
        live = read_text(path)
        what = "%s wrapper (%s)" % (job["id"], path)
        if live == text:
            ctx.note(PRESENT, what)
            ctx.wrapper_present += 1
            retire_prev(ctx, path)
        elif live is None:
            if ctx.dry:
                ctx.note(WOULD_CREATE, what)
            else:
                write_atomic(path, text)
                ctx.note(CREATED, what)
                ctx.wrapper_present += 1
        else:
            if ctx.dry:
                ctx.note(WOULD_REPAIR, what, "text differs from the template")
            else:
                write_atomic(path, text)
                ctx.note(REPAIRED, what, "previous kept as .prev")
                ctx.wrapper_present += 1

    held = scheduler_held()
    record = heartbeat_record_start(ctx)
    if held:
        for job in jobs:
            if WINDOWS:
                spec = windows_spec(ctx, [job], datetime.datetime.now())[0]
                path, text = Path(ctx.fill(job["windows"]["task_name"])), spec["xml"]
                what = "%s (scheduled task)" % spec["task_name"]
            else:
                path, text = plist_for(ctx, job)
                what = "%s (%s)" % (job["macos"]["label"], path.name)
            if not WINDOWS and not ctx.dry:
                Path(ctx.fill(job["macos"]["log"])).parent.mkdir(parents=True,
                                                                 exist_ok=True)
                write_atomic(path, text)
            ctx.note(SKIPPED, what,
                     "written, NOT handed to this machine's scheduler: %s" % held)
            heartbeat_record_job(ctx, record, job, registered=False)
            present += 1
        ctx.heartbeat_present = present
        heartbeat_record_save(ctx, record)
        say("   OK heartbeat (%d/%d written, none registered)"
            % (present, ctx.heartbeat_total))
        return

    if WINDOWS:
        specs = windows_spec(ctx, jobs, datetime.datetime.now())
        ctx.ps_driver = render_ps_driver(ctx, specs)
        say("     driver: %s" % ctx.ps_driver)
        for spec in specs:
            state = read_task(ctx, spec["task_name"])
            diffs = task_diff(spec, state)
            what = "%s (scheduled task)" % spec["task_name"]
            job = [j for j in jobs if j["id"] == spec["id"]][0]
            if not diffs:
                ctx.note(PRESENT, what)
                heartbeat_record_job(ctx, record, job, registered=True)
                present += 1
                continue
            if ctx.dry:
                ctx.note(WOULD_CREATE if diffs == ["not registered"]
                         else WOULD_REPAIR, what, "; ".join(diffs))
                continue
            argv = ["-Action", "register", "-Job", spec["id"]]
            if state.get("found"):
                argv.append("-Force")
            code, out = ps(ctx, *argv)
            if code != 0:
                raise Stop("registering %s failed: %s"
                           % (spec["task_name"], out.strip()))
            state = read_task(ctx, spec["task_name"])       # read-back, not an echo
            after = task_diff(spec, state)
            if after:
                raise Stop("%s did not read back as registered: %s"
                           % (spec["task_name"], "; ".join(after)))
            ctx.note(CREATED if diffs == ["not registered"] else REPAIRED, what)
            heartbeat_record_job(ctx, record, job, registered=True)
            present += 1
    else:
        loaded = []
        for job in jobs:
            path, text = plist_for(ctx, job)
            live = read_text(path)
            what = "%s (%s)" % (job["macos"]["label"], path.name)
            if plist_same(live, text):
                ctx.note(PRESENT, what)
                heartbeat_record_job(ctx, record, job, registered=None)
                present += 1
                continue
            if ctx.dry:
                ctx.note(WOULD_CREATE if live is None else WOULD_REPAIR, what,
                         "" if live is None else "the live agent differs in meaning")
                continue
            # launchd never creates a missing log folder; it would fail silently
            Path(ctx.fill(job["macos"]["log"])).parent.mkdir(parents=True, exist_ok=True)
            write_atomic(path, text)
            code, out = run(["launchctl", "unload", str(path)])
            code, out = run(["launchctl", "load", str(path)])
            if code != 0:
                raise Stop("launchctl load %s failed: %s" % (path, out.strip()))
            back = read_text(path)
            if not plist_same(back, text):
                raise Stop("%s did not read back" % path)
            ctx.note(CREATED if live is None else REPAIRED, what)
            heartbeat_record_job(ctx, record, job, registered=True)
            present += 1
            loaded.append(job["macos"]["label"])
    ctx.heartbeat_present = present
    heartbeat_record_save(ctx, record)
    say("   OK heartbeat (%d/%d)" % (present, ctx.heartbeat_total))


# What the heartbeat step handed to this machine, written into installed.json so
# the way out (--uninstall) knows which job files were ever given to the
# scheduler. A job file written behind the scheduler wall is recorded as never
# registered; one found already in place keeps what an earlier run recorded, or
# None when no run recorded it. Program tree only, and never on a dry run.

def heartbeat_record_start(ctx):
    if not PROGRAM_TREE or ctx.dry:
        return None
    prior = read_installed(ctx).get("heartbeat")
    return {"prior": prior if isinstance(prior, dict) else {}, "jobs": {}}


def heartbeat_record_job(ctx, record, job, registered):
    if record is None:
        return
    before = record["prior"].get(job["id"]) if isinstance(record["prior"].get(job["id"]),
                                                            dict) else {}
    if registered is None:
        registered = before.get("registered")
    entry = {"registered": registered}
    if WINDOWS:
        entry["task"] = ctx.fill(job["windows"]["task_name"])
        item = wrapper_item(ctx, job)
        if item:
            entry["wrapper"] = str(item[0])
            entry["wrapper_sha"] = sha(item[1])
    else:
        path, _text = plist_for(ctx, job)
        entry["label"] = job["macos"]["label"]
        entry["file"] = str(path)
    record["jobs"][job["id"]] = entry


def heartbeat_record_save(ctx, record):
    if record is None or record["jobs"] == record["prior"]:
        return
    installed = read_installed(ctx)
    installed["heartbeat"] = record["jobs"]
    write_installed(ctx, installed)


# --------------------------------------------------------- step 4: the watchers

ROLE_PHRASE = re.compile(r"the hub folder \([^()]*machine\.json\)")
RUN_FILE = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)-[a-z]+\.md\b")
PATH_TAIL = re.compile(r"[/\\A-Za-z0-9_.\-*<>]*")
NAME_IN_COMMENT = re.compile(r"name\s*=\s*`([^`]+)`")


def parse_routine(text):
    """-> (preamble, frontmatter dict, key order, body)."""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        raise Stop("a routine template has no frontmatter")
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise Stop("a routine template has an unterminated frontmatter")
    preamble = "\n".join(lines[:start]).strip("\n")
    front = {}
    order = []
    for line in lines[start + 1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        front[key] = value.strip()
        order.append(key)
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return preamble, front, order, body


def windows_backslash_tails(text, roots):
    roots = sorted({r for r in roots if r}, key=len, reverse=True)
    out = []
    pos = 0
    while pos < len(text):
        best = None
        for root in roots:
            idx = text.find(root, pos)
            if idx != -1 and (best is None or idx < best[0]
                              or (idx == best[0] and len(root) > len(best[1]))):
                best = (idx, root)
        if best is None:
            out.append(text[pos:])
            break
        idx, root = best
        out.append(text[pos:idx])
        out.append(root)
        tail = PATH_TAIL.match(text, idx + len(root)).group(0)
        out.append(tail.replace("/", "\\"))
        pos = idx + len(root) + len(tail)
    return "".join(out)


def render_body(ctx, body):
    """The substitution contract a routine's body is rendered under: the hub's
    own path where the body names its role, and the machine's own name where a
    run file is named."""
    hub = str(ctx.hub)
    text = ROLE_PHRASE.sub(lambda m: hub, body)     # a function repl: no escapes
    text = RUN_FILE.sub(lambda m: "%s-%s.md" % (m.group(1), ctx.machine), text)
    if WINDOWS:
        # The older layout's folder name is written down in exactly one place,
        # the resolver; this render asks it rather than spelling it again.
        older = (getattr(RESOLVER, "LEGACY_SYNC_DIRNAME", None)
                 or (None if PROGRAM_TREE else ENGINE.name))
        if older:
            text = text.replace("~/" + older, str(ENGINE))
        text = text.replace("~/.claude", str(ctx.claude))
        text = text.replace("~/Exocortex", hub)
        text = re.sub(r"\bpython3\b", "python", text)
        text = text.replace("Run the real clock (date)",
                            "Run the real clock (Get-Date)")
        text = text.replace("`date`", "`Get-Date`")
        text = windows_backslash_tails(
            text, [hub, str(ctx.claude), str(ENGINE),
                   str(Path(ctx.roots.get("projects", "")))])
    return text


def routine_title(preamble, front, name):
    if front.get("title"):
        return front["title"]
    found = NAME_IN_COMMENT.search(preamble or "")
    if found:
        return found.group(1)
    words = name.replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def cron_words(cron):
    parts = (cron or "").split()
    if len(parts) != 5:
        return cron or "(no schedule in the template)"
    minute, hour, _dom, _mon, dow = parts
    times = []
    for h in hour.split(","):
        for m in minute.split(","):
            try:
                times.append("%02d:%02d" % (int(h), int(m)))
            except ValueError:
                return cron
    when = " and ".join(times)
    if dow == "*":
        return "daily " + when
    days = {"0": "Sundays", "1": "Mondays", "2": "Tuesdays", "3": "Wednesdays",
            "4": "Thursdays", "5": "Fridays", "6": "Saturdays", "7": "Sundays"}
    named = ", ".join(days.get(d, d) for d in dow.split(","))
    return "%s %s" % (named, when)


def other_machine(ctx):
    others = []
    for path in sorted(ctx.hub.glob("live-sessions-*.json")):
        token = path.stem[len("live-sessions-"):]
        if token and token != ctx.machine:
            others.append(token)
    return others[0] if len(others) == 1 else "<other-machine>"


def step_watchers(ctx):
    say("6. the watchers")
    registry = ctx.hub / "routines"
    if not registry.is_dir():
        if ctx.dry:
            # A first machine has no hub folder yet: step 2's brain pull brings
            # the registry. A dry run says so; it does not stop.
            ctx.note(WOULD_CREATE, "routines/ (the routine registry)",
                     "arrives with step 2's brain pull, at %s" % registry)
            say("   OK watchers (the registry arrives with the brain)")
            return
        if PROGRAM_TREE:
            # A fresh program tree has nothing to render until routines exist:
            # the seeds put the shipped ones there, and the rest are yours.
            ctx.note(SKIPPED, "routines/ (the routine registry)",
                     "no routines on this machine yet, at %s" % registry)
            say("   OK watchers (no routines on this machine yet)")
            return
        raise Stop("no routine registry at %s - the brain pull should have "
                   "brought it" % registry)
    rendered_dir = ctx.hub / "watchers" / "rendered" / ctx.machine
    rows = []
    seeds = set()
    present_tasks = 0
    made = {}                 # what this step wrote, by hub-relative path -> sha
    for path in sorted(registry.glob("*.md")):
        text = read_text(path)
        if text is None:
            raise Stop("cannot read %s" % path)
        preamble, front, _order, body = parse_routine(text)
        name = front.get("name") or path.stem
        schedule = front.get("schedule", "")
        extras = [(k, v) for k, v in front.items()
                  if k not in ("name", "description", "model", "title", "schedule")]
        comment = ("<!-- exocortex routine %s, rendered for %s by install.py"
                   " · schedule: %s%s · source routines/%s -->"
                   % (name, ctx.machine, schedule or "(none in the template)",
                      "".join(" · %s: %s" % kv for kv in extras),
                      path.name))
        out_body = render_body(ctx, body)
        # name · description · model only: the app keeps the cron elsewhere,
        # and a key the template does not carry is not invented here.
        head = ["---", "name: %s" % name]
        for key in ("description", "model"):
            if front.get(key):
                head.append("%s: %s" % (key, front[key]))
        head.append("---")
        rendered = "%s\n%s\n\n%s" % (comment, "\n".join(head), out_body)
        target = rendered_dir / ("%s.md" % name)
        live = read_text(target)
        what = "watchers/rendered/%s/%s.md" % (ctx.machine, name)
        if live == rendered:
            ctx.note(PRESENT, what)
            retire_prev(ctx, target)
            made[what] = sha(rendered)
        elif ctx.dry:
            ctx.note(WOULD_CREATE if live is None else WOULD_REPAIR, what)
        else:
            write_atomic(target, rendered)
            ctx.note(CREATED if live is None else REPAIRED, what)
            made[what] = sha(rendered)
        ctx.rendered += 1

        for found in RUN_FILE.finditer(out_body):
            if found.group(0).endswith("-%s.md" % ctx.machine):
                seeds.add(found.group(1))

        # the app registration: compare the rendered body with the live SKILL.md
        skill = ctx.claude / "scheduled-tasks" / name / "SKILL.md"
        live_skill = read_text(skill)
        label = "%s (registered in the app)" % name
        if live_skill is None:
            ctx.note(WOULD_CREATE, label, "the sheet's STEP 2 registers it")
        else:
            _p, lfront, _o, lbody = parse_routine(live_skill)
            same_body = lbody.replace("\r\n", "\n").rstrip("\n") == \
                out_body.replace("\r\n", "\n").rstrip("\n")
            same_front = all(lfront.get(k, "") == front.get(k, "")
                             for k in ("name", "description", "model"))
            if same_body and same_front:
                ctx.note(PRESENT, label)
                present_tasks += 1
            else:
                why = []
                if not same_body:
                    why.append("prompt body differs from the render")
                if not same_front:
                    why.append("frontmatter differs")
                ctx.note(WOULD_REPAIR, label,
                         "; ".join(why) + " - the sheet's STEP 1 updates it")

        rows.append({
            "id": name, "title": routine_title(preamble, front, name),
            "cron": schedule, "model": front.get("model", ""),
            "description": front.get("description", ""),
            "rendered": "watchers/rendered/%s/%s.md" % (ctx.machine, name),
        })

    # the run files: first line only, never overwritten
    for stem in sorted(seeds):
        run_file = ctx.hub / "watchers" / ("%s-%s.md" % (stem, ctx.machine))
        first = "# %s — %s\n" % (stem.replace("-", " "), ctx.machine)
        if run_file.exists():
            ctx.note(PRESENT, "watchers/%s" % run_file.name)
        elif ctx.dry:
            ctx.note(WOULD_CREATE, "watchers/%s" % run_file.name)
        else:
            write_atomic(run_file, first, keep_prev=False)
            ctx.note(CREATED, "watchers/%s" % run_file.name)

    seed_hygiene_settings(ctx)

    sheet_name = "INSTALL-WATCHERS-%s.md" % ctx.machine
    sheet_path = ctx.hub / "design" / sheet_name
    sheet = build_sheet(ctx, rows, sheet_name)
    live_sheet = read_text(sheet_path)
    # The sheet carries a "generated on" stamp. A stamp is not a change: a run
    # that would write the same page keeps the page it found (idempotence),
    # so a rerun repairs nothing and rewrites nothing.
    if live_sheet is not None and same_but_for_stamp(
            ctx, rows, sheet_name, live_sheet):
        ctx.note(PRESENT, "design/%s" % sheet_name)
        retire_prev(ctx, sheet_path)
        made["design/%s" % sheet_name] = sha(live_sheet)
    elif live_sheet == sheet:
        ctx.note(PRESENT, "design/%s" % sheet_name)
        retire_prev(ctx, sheet_path)
        made["design/%s" % sheet_name] = sha(sheet)
    elif ctx.dry:
        ctx.note(WOULD_CREATE if live_sheet is None else WOULD_REPAIR,
                 "design/%s" % sheet_name)
    else:
        write_atomic(sheet_path, sheet)
        ctx.note(CREATED if live_sheet is None else REPAIRED,
                 "design/%s" % sheet_name)
        made["design/%s" % sheet_name] = sha(sheet)
    if PROGRAM_TREE and not ctx.dry:
        # The way out removes only what this step wrote and only while it still
        # carries these bytes, so the record keeps each file's sha.
        installed = read_installed(ctx)
        if installed.get("watchers") != {"made": made}:
            installed["watchers"] = {"made": made}
            write_installed(ctx, installed)
    ctx.watchers_present = present_tasks
    say("")
    say("   The one step a session must do (a Claude app registers its")
    say("   scheduled tasks only through its own tool). Paste this into a")
    say("   Claude session whose folder is %s:" % ctx.hub)
    say("")
    say("     read the project status/memory first. Then read design/%s in "
        "this folder and do what it says." % sheet_name)
    say("")
    say("   OK watchers (%d rendered, %d already registered)"
        % (ctx.rendered, present_tasks))


def seed_hygiene_settings(ctx):
    """The hygiene watcher's four periods are the USER'S, and a fresh machine starts
    with the built-in ones written down where every vendor's watcher reads them. Seeded ONCE:
    a hub that already has the file keeps it exactly as it stands, because the number in it is
    the user's answer and this installer never overrules an answer."""
    path = ctx.hub / HYGIENE_SETTINGS
    text = json.dumps(HYGIENE_DEFAULTS, indent=1) + "\n"
    if path.exists():
        ctx.note(PRESENT, HYGIENE_SETTINGS)
        return
    if ctx.dry:
        ctx.note(WOULD_CREATE, HYGIENE_SETTINGS,
                 "the built-in periods, at %s" % path)
        return
    write_atomic(path, text, keep_prev=False)
    ctx.note(CREATED, HYGIENE_SETTINGS,
             "grace %s h, ceiling %s - change one with tools/hygiene-settings.py --set"
             % (HYGIENE_DEFAULTS["grace_hours"], HYGIENE_DEFAULTS["ceiling"]))


STAMP_SENTINEL = "\x00GENERATED\x00"


def same_but_for_stamp(ctx, rows, sheet_name, live):
    """True when the sheet on disk is what this run would write, apart from its
    'generated on' stamp - so nothing has to be rewritten."""
    probe = build_sheet(ctx, rows, sheet_name, stamp=STAMP_SENTINEL)
    if probe.count(STAMP_SENTINEL) != 1:
        return live == build_sheet(ctx, rows, sheet_name)
    head, tail = probe.split(STAMP_SENTINEL)
    return (len(live) >= len(head) + len(tail)
            and live.startswith(head) and live.endswith(tail))


def build_sheet(ctx, rows, sheet_name, stamp=None):
    tmpl = read_text(TEMPLATES / "INSTALL-WATCHERS.md.tmpl")
    if tmpl is None:
        raise Stop("no %s" % (TEMPLATES / "INSTALL-WATCHERS.md.tmpl"))
    header = ("| taskId | rendered prompt file | title | cron (local) | model |"
              " description |\n|---|---|---|---|---|---|\n")
    body = "".join(
        "| `%s` | `%s` | `%s` | `%s` | %s | %s |\n"
        % (r["id"], r["rendered"], r["title"],
           r["cron"] or "(none in the template - ask the lane)",
           r["model"] or "(none in the template)", r["description"])
        for r in rows)
    ids = ", ".join("`%s`" % r["id"] for r in rows)
    run_files = "".join(
        "- `watchers/%s`\n" % p.name
        for p in sorted((ctx.hub / "watchers").glob("*-%s.md" % ctx.machine)))
    done = ("ROUTINES REGISTERED · %s · %s · next runs <one date each>"
            % (ctx.machine, " · ".join(r["id"] for r in rows)))
    words = "; ".join("%s %s" % (r["id"], cron_words(r["cron"])) for r in rows)
    values = {
        "__GENERATED__": (stamp if stamp is not None
                          else "%s on the %s" % (now_iso(), ctx.machine)),
        "__OWNER__": owner_name(),
        "__MACHINE__": ctx.machine,
        "__MACHINE_UPPER__": ctx.machine.upper(),
        "__MACHINE_TITLE__": ctx.machine.capitalize(),
        "__HUB__": str(ctx.hub),
        "__SYNCDIR__": str(ENGINE),
        "__PY__": ctx.py_cmd,
        "__SHEET_NAME__": sheet_name,
        "__IDS_BACKTICKED__": ids,
        "__COUNT__": str(len(rows)),
        "__TABLE__": (header + body).rstrip("\n"),
        "__RENDERED_DIR__": str(ctx.hub / "watchers" / "rendered" / ctx.machine),
        "__RUN_FILES__": run_files or "- (none)\n",
        "__CLOCK__": ('Get-Date -Format "dddd yyyy-MM-dd HH:mm"' if WINDOWS
                      else "date"),
        "__WHOISLIVE__": "tools%swho-is-live.py --pen" % ctx.sep,
        "__MAILPATH__": "tools%smail.py" % ctx.sep,
        "__OTHER_HUB__": "%s/hub" % other_machine(ctx).upper(),
        "__CLAUDE_TASKS__": str(ctx.claude / "scheduled-tasks"),
        "__PATHSEP__": ctx.sep,
        "__DONE_LINE__": done,
        "__CRON_WORDS__": words,
    }
    for key, value in values.items():
        tmpl = tmpl.replace(key, value)
    return tmpl


# ------------------------------------------------------------ step 5: the tree

# A page tool that fails says why in its own words: step 7 shows those lines (at
# most WHY_LINES of them) above its STOP, so the cause is never off the screen.
TOOL_WHY = re.compile(r"failed|STOP|not written|not published|error", re.I)
WHY_LINES = 8


def step_tree(ctx):
    say("7. the tree")
    tree = ctx.hub / "tree.html"
    if ctx.dry:
        ctx.note(SKIPPED, "orchestrator.py", "dry run")
        ctx.note(SKIPPED, "tools/pulse.py", "dry run")
        ctx.note(SKIPPED, "open %s" % tree, "dry run")
        say("   OK tree (dry run)")
        return
    wanted = [ctx.hub / "orchestrator.py", ctx.hub / "tools" / "pulse.py"]
    absent = [s for s in wanted if not s.exists()]
    if absent and PROGRAM_TREE:
        # This version of the program does not ship the page-drawing tools yet.
        # That is a fact about the release, not a broken install: say it in one
        # line and finish, rather than stop an install that is otherwise done.
        for script in absent:
            ctx.note(SKIPPED, script.name, "this version of the program does not ship it")
        say("   OK tree (this version draws no pages yet)")
        return
    for script in wanted:
        if not script.exists():
            raise Stop("no %s - the hub folder is incomplete" % script)
        code, out = run([ctx.python, str(script)], cwd=ctx.hub)
        said = [l for l in out.rstrip("\n").split("\n") if l.strip()]
        if code != 0:
            # the tool's own words for WHY come first: every line that says it
            # failed, stopped, wrote or published nothing, or erred
            for line in [l for l in said[:-2] if TOOL_WHY.search(l)][:WHY_LINES]:
                say("     " + line)
        for line in said[-2:]:
            say("     " + line)
        if code != 0:
            raise Stop("%s failed (exit %d)" % (script.name, code))
        ctx.note("RAN", script.name)
    if not tree.exists():
        # THE PAGE TOOLS RAN AND SAID NOTHING WAS WRONG (a non-zero exit was a
        # STOP above), so there is simply nothing to draw yet: a hub
        # whose projects root is still empty draws no tree. That is a first
        # hour, not a broken install — the same answer as for a version
        # that ships no page tools.
        ctx.note(SKIPPED, "tree.html",
                 "nothing to draw yet - no project in the projects root")
        say("   OK tree (nothing to draw yet)")
        return
    held = page_open_held()
    if held:
        ctx.tree_drawn = True
        ctx.note(SKIPPED, "open %s" % tree, held)
        say("   OK tree (drawn, not opened)")
        return
    if WINDOWS:
        run(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
             "-Command", "Start-Process '%s'" % tree])
    else:
        run(["open", str(tree)])
    ctx.tree_opened = True
    ctx.note("OPENED", "tree.html", str(tree))
    say("   OK tree")


# ------------------------------------------------------- the safe updater

def hub_git(ctx, *args):
    return git_in(ctx.hub, *args)


def tracked_dirty(ctx):
    """The files git tracks that have been changed here. An update never runs
    over them: it would have to choose between your edit and the release."""
    code, out = hub_git(ctx, "status", "--porcelain", "--untracked-files=no")
    if code != 0:
        raise Stop("git could not say whether %s has uncommitted changes (%s)"
                   % (ctx.hub, out.strip()))
    return [l[3:].strip() for l in out.splitlines() if l.strip()]


def incoming_paths(ctx, ref):
    """Every path the incoming commits ADD. Renames count by their new name."""
    code, out = hub_git(ctx, "diff", "--name-status", "-z", "HEAD", ref)
    if code != 0:
        raise Stop("git could not compare this checkout with %s (%s)" % (ref, out.strip()))
    fields = [f for f in out.split("\0") if f != ""]
    added, i = [], 0
    while i < len(fields):
        status = fields[i]
        if status[:1] in ("R", "C") and i + 2 < len(fields):
            added.append(fields[i + 2])              # the name it arrives under
            i += 3
            continue
        if i + 1 < len(fields):
            if status[:1] == "A":
                added.append(fields[i + 1])
            i += 2
            continue
        break
    return added


def collisions(ctx, added, tracked):
    """Every incoming path that would land on something that is not the
    program's: a file of yours at that exact path, or a file where the release
    needs a folder, or a folder where it needs a file. Each one names itself,
    says whose it is, and changes nothing."""
    hits = []
    for rel in added:
        target = ctx.hub / Path(*rel.split("/"))
        if target.is_file() and rel not in tracked:
            hits.append("%s already exists here and git does not track it, so it is yours, "
                        "not the program's. Move it, then run the update again." % rel)
            continue
        if target.is_dir():
            hits.append("%s already exists here as a FOLDER and the update brings a file of "
                        "that name. Move the folder, then run the update again." % rel)
            continue
        walked = ""
        for part in rel.split("/")[:-1]:
            walked = (walked + "/" + part) if walked else part
            crumb = ctx.hub / Path(*walked.split("/"))
            if crumb.is_file():
                hits.append("the update brings %s, and %s already exists here as a FILE. "
                            "Move it, then run the update again." % (rel, walked))
                break
    return hits


def update_ref(ctx):
    named = getattr(ctx.args, "ref", None)
    if named:
        return named
    recorded = plain_json(MACHINE_FILE) or {}
    recorded = (recorded.get("update") or {}).get("ref")
    if recorded:
        return recorded
    code, out = hub_git(ctx, "rev-parse", "--abbrev-ref", "HEAD")
    branch = out.strip() if code == 0 and out.strip() and out.strip() != "HEAD" else "main"
    return "origin/%s" % branch


def road_update(ctx):
    """Fetch, refuse to touch anything of yours, fast-forward, settle in."""
    say("UPDATE")
    say("  hub %s" % ctx.hub)
    if not (ctx.hub / ".git").exists():
        raise Stop("%s is not a git checkout of the program, so there is nothing to update "
                   "here. This road is for an install made by cloning the program." % ctx.hub)
    ref = update_ref(ctx)
    say("  ref %s" % ref)
    dirty = tracked_dirty(ctx)
    if dirty:
        raise Stop("the program's own files have been changed here and not committed (%s). "
                   "An update would have to choose between your change and the release, and "
                   "it will not choose. Commit them or put them back, then run this again."
                   % ", ".join(dirty[:5]))
    code, out = hub_git(ctx, "fetch", "--quiet", "origin")
    if code != 0:
        raise Stop("fetching from origin failed: %s" % out.strip())
    code, _out = hub_git(ctx, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    if code != 0:
        raise Stop("there is no %s to update to. Name the one you mean with --ref." % ref)
    code, _out = hub_git(ctx, "merge-base", "--is-ancestor", "HEAD", ref)
    if code != 0:
        raise Stop("%s is not ahead of what is installed here: the two have gone different "
                   "ways. This road only ever fast-forwards, so it stopped and changed "
                   "nothing. A session that can read both sides settles it." % ref)
    code, out = hub_git(ctx, "ls-files", "-z")
    tracked = set(f for f in out.split("\0") if f)
    added = incoming_paths(ctx, ref)
    hits = collisions(ctx, added, tracked)
    if hits:
        say("")
        for line in hits[:10]:
            say("  !  %s" % line)
        raise Stop("the update would have landed on %d file(s) that are not the program's. "
                   "Nothing was changed." % len(hits))
    ctx.note(PRESENT, "%d incoming path(s) checked against your own files" % len(added))
    if ctx.dry:
        ctx.note(WOULD_REPAIR, "git merge --ff-only %s" % ref)
        say("   OK update (dry run)")
        return
    code, out = hub_git(ctx, "merge", "--ff-only", "--no-overwrite-ignore", ref)
    if code != 0:
        raise Stop("the fast-forward to %s did not run: %s" % (ref, out.strip()))
    for line in out.strip().splitlines()[:4]:
        say("     git: " + line)
    ctx.note(REPAIRED, "the program", "fast-forwarded to %s" % ref)
    say("   OK update")
    return "installed"


def quick_gates(ctx):
    """The cheap proofs an update runs before it says OK."""
    say("   checks")
    resolver = ctx.hub / "tools" / "exo_paths.py"
    if resolver.is_file():
        code, out = run([ctx.python, str(resolver), "--check"], cwd=ctx.hub)
        say("     " + (out.strip().splitlines() or ["no answer"])[-1])
        if code != 0:
            raise Stop("the path resolver does not agree with this machine's record after "
                       "the update. Nothing else was run.")
    code, out = run([ctx.python, str(ENGINE / "sync.py"), "status"], cwd=ENGINE)
    lines = [l for l in out.splitlines() if l.strip()]
    for line in lines:
        if line.strip().startswith("!") or "did not sync" in line:
            say("     " + line.strip())
    if code != 0:
        raise Stop("`sync.py status` does not run after the update (exit %d). The program is "
                   "installed; the sync is not healthy." % code)
    ctx.note(PRESENT, "the resolver and the sync tool both answer")


# ------------------------------------------------------------- the road back

def road_recover(ctx):
    """Git treats what it ignores as expendable. This is the road back."""
    say("RECOVER")
    say("  hub   %s" % ctx.hub)
    say("  brain %s" % ctx.brain)
    joined = getattr(ctx.args, "brain", None)
    if not brain_has_head(ctx.brain):
        if joined:
            join_brain(ctx, ctx.brain, joined)
            ctx.note(CREATED, "the brain, joined from %s" % joined, str(ctx.brain))
        else:
            raise Stop("there is no brain at %s to rebuild from. If it lives somewhere else, "
                       "name it: install.py --recover --brain <url or path>" % ctx.brain)
    code, out = run([ctx.python, str(ENGINE / "sync.py"), "recover"], cwd=ENGINE)
    for line in out.rstrip("\n").split("\n"):
        if line.strip():
            say("     " + line)
    if code != 0:
        raise Stop("sync.py recover failed (exit %d) - nothing was overwritten" % code)
    ctx.note(REPAIRED if "restored" in out else PRESENT, "the live brain",
             "rebuilt from the mirror")
    say("   OK recover")


# ---------------------------------------------------------------- the repair

def road_repair(ctx):
    """What an install wrote, checked again, and mended where it can."""
    say("REPAIR")
    data = plain_json(MACHINE_FILE)
    if data is None:
        raise Stop("there is no readable machine.json at %s. Run install.py without a flag "
                   "to make one." % MACHINE_FILE)
    if PROGRAM_TREE:
        if not repair_record(ctx, data, MACHINE_FILE):
            ctx.note(PRESENT, "machine.json records the layout",
                     "%s · %s" % (data.get("layout"), data.get("partition")))
        rule = ctx.hub / ".gitignore"
        code, out = hub_git(ctx, "ls-files", "--error-unmatch", "-z", "--", ".gitignore")
        if code != 0:
            shipped = SHIPPED_TEMPLATES / "dot-gitignore"
            if not rule.exists() and shipped.is_file() and not ctx.dry:
                write_atomic(rule, read_text(shipped) or "", keep_prev=False)
                ctx.note(CREATED, ".gitignore", "put back from templates/dot-gitignore")
            ctx.note(WOULD_REPAIR, ".gitignore",
                     "git does not track it. `git add .gitignore && git commit` it, or "
                     "check out the program's own copy.")
        else:
            code, out = hub_git(ctx, "status", "--porcelain", "-z", "--", ".gitignore")
            if code == 0 and [f for f in out.split("\0") if f]:
                if not rule.exists() and not ctx.dry:
                    hub_git(ctx, "checkout", "--", ".gitignore")
                    ctx.note(REPAIRED, ".gitignore", "restored from the program's own copy")
                else:
                    ctx.note(WOULD_REPAIR, ".gitignore",
                             "it differs from the program's copy: commit your change, or "
                             "`git checkout -- .gitignore`")
            else:
                ctx.note(PRESENT, ".gitignore", "tracked and unchanged")
    step_seeds(ctx)
    say("")
    step_laws(ctx)
    say("")
    step_heartbeat(ctx)
    say("")
    code, out = run([ctx.python, str(ENGINE / "sync.py"), "status"], cwd=ENGINE)
    for line in out.splitlines():
        if "did not sync" in line or line.strip().startswith("!"):
            say("   " + line.strip())
    ctx.note(PRESENT if code == 0 else WOULD_REPAIR, "the sync tool answers",
             "exit %d" % code)
    say("   OK repair")


# ------------------------------------------------------------- the way out

REMOVED = "REMOVED"
WOULD_REMOVE = "WOULD REMOVE"
LEFT = "LEFT"
NOT_FOUND = "NOT FOUND"


def read_record(ctx):
    """Who this machine is and where its folders are, READ from machine.json
    and never written: the way out neither bootstraps nor repairs a record.
    -> True when there is a readable record."""
    data = plain_json(MACHINE_FILE)
    roots = (data or {}).get("roots") or {}
    if not data or not roots.get("orchestrator"):
        return False
    ctx.machine = data.get("name") or default_machine_name()
    ctx.roots = dict(roots)
    ctx.roots.setdefault("home", str(Path.home()))
    ctx.roots.setdefault("claude", str(Path(ctx.roots["home"]) / ".claude"))
    return True


def file_sha(path):
    try:
        with open(str(path), "rb") as handle:
            return sha(handle.read())
    except (IOError, OSError):
        return None


def same_tree(left, right):
    """True when two folders hold the same files, byte for byte, and no other."""
    def files(root):
        out = {}
        for path in Path(root).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                out[path.relative_to(root).as_posix()] = file_sha(path)
        return out
    try:
        return files(left) == files(right)
    except OSError:
        return False


def remove_file(ctx, path):
    """One file, removed and checked gone. -> '' or why it is still there."""
    if ctx.dry:
        return ""
    try:
        Path(path).unlink()
    except OSError as exc:
        return "it could not be removed (%s)" % exc.__class__.__name__
    return "" if not Path(path).exists() else "it is still there after removal"


def remove_tree(ctx, path):
    if ctx.dry:
        return ""
    try:
        shutil.rmtree(str(path))
    except OSError as exc:
        return "it could not be removed (%s)" % exc.__class__.__name__
    return "" if not Path(path).exists() else "it is still there after removal"


def launchd_loaded(label):
    code, _out = run(["launchctl", "list", label])
    return code == 0


def uninstall_jobs(ctx, record, out):
    """The heartbeat's jobs, by the names jobs.json renders for them."""
    held = scheduler_held()
    ids = [str(j) for j in (record.get("jobs") or [])]
    beat = record.get("heartbeat") if isinstance(record.get("heartbeat"), dict) else {}
    for jid in beat:
        if jid not in ids:
            ids.append(jid)
    if not ids:
        return
    try:
        jobs = dict((j["id"], j) for j in load_jobs())
    except (Stop, ValueError, KeyError):
        jobs = {}
    if WINDOWS and not held and jobs:
        # the task driver, rendered into the temp folder as the install renders
        # it; reading a task through it changes nothing, so a dry run reads too
        ctx.ps_driver = render_ps_driver(ctx, windows_spec(ctx, list(jobs.values()),
                                                           datetime.datetime.now()))
    for jid in ids:
        job = jobs.get(jid)
        seen = beat.get(jid) if isinstance(beat.get(jid), dict) else {}
        registered = seen.get("registered")
        if job is None:
            out(LEFT, "job %s" % jid, "this version's install/jobs.json does not name it, so its "
                "scheduler name cannot be rendered")
            continue
        if WINDOWS:
            uninstall_task(ctx, job, registered, held, out, seen)
        else:
            uninstall_agent(ctx, job, registered, held, out)


def uninstall_agent(ctx, job, registered, held, out):
    path, _text = plist_for(ctx, job)
    label = job["macos"]["label"]
    what = "%s (%s)" % (label, path)
    there = path.exists()
    if held:
        if registered is False and there:
            why = remove_file(ctx, path)
            if why:
                out(LEFT, what, why)
            else:
                out(WOULD_REMOVE if ctx.dry else REMOVED, what,
                    "written by the installer and never handed to the scheduler")
        elif there:
            out(LEFT, what, "it is (or may be) loaded in this machine's scheduler, and the "
                "scheduler is not touched here: %s" % held)
        else:
            out(NOT_FOUND, what)
        return
    loaded = launchd_loaded(label)
    if not loaded and not there:
        out(NOT_FOUND, what)
        return
    if ctx.dry:
        out(WOULD_REMOVE, what, "unloaded, then its file removed" if loaded
            else "its file removed (it is not loaded)")
        return
    if loaded:
        if there:
            run(["launchctl", "unload", str(path)])
        else:
            run(["launchctl", "remove", label])
        if launchd_loaded(label):
            out(LEFT, what, "launchd still lists it after the unload")
            return
    why = remove_file(ctx, path) if there else ""
    if why:
        out(LEFT, what, "unloaded, but its file: %s" % why)
    else:
        out(REMOVED, what, "unloaded and its file removed" if loaded
            else "its file removed (it was not loaded)")


def uninstall_task(ctx, job, registered, held, out, seen=None):
    name = ctx.fill(job["windows"]["task_name"])
    what = "%s (scheduled task)" % name
    item = wrapper_item(ctx, job)
    kept = False
    if held:
        if registered is False:
            out(NOT_FOUND, what, "never registered")
        else:
            kept = True
            out(LEFT, what, "it is (or may be) registered with this machine's scheduler, and "
                "the scheduler is not touched here: %s" % held)
    else:
        state = read_task(ctx, name)
        if not state.get("found"):
            out(NOT_FOUND, what)
        elif ctx.dry:
            out(WOULD_REMOVE, what, "unregistered")
        else:
            code, text = ps(ctx, "-Action", "unregister", "-TaskName", name)
            if read_task(ctx, name).get("found"):
                kept = True
                out(LEFT, what, "the scheduler still has it: %s" % text.strip()[:160])
            else:
                out(REMOVED, what, "unregistered")
    if item:
        path, text = item
        wrap = "%s wrapper (%s)" % (job["id"], path)
        if not path.exists():
            out(NOT_FOUND, wrap)
        elif kept:
            out(LEFT, wrap, "the task that runs it is still registered")
        elif file_sha(path) not in (sha(text), (seen or {}).get("wrapper_sha")):
            out(LEFT, wrap, "it is not the installer's rendering any more — changed by hand?")
        else:
            why = remove_file(ctx, path)
            out(LEFT if why else (WOULD_REMOVE if ctx.dry else REMOVED), wrap,
                why or "the installer's rendering, unchanged")


def uninstall_watchers(ctx, record, out):
    """The rendered watcher prompts and the landing sheet — while they still
    carry the bytes the installer wrote."""
    made = (record.get("watchers") or {}).get("made") if isinstance(record.get("watchers"),
                                                                     dict) else None
    if not isinstance(made, dict):
        rendered = ctx.hub / "watchers" / "rendered" / ctx.machine
        if rendered.is_dir() and any(rendered.iterdir()):
            out(LEFT, "watchers/rendered/%s/" % ctx.machine,
                "the install that ran here recorded no rendered file, so none is removed")
        return
    rendered_dir = ctx.hub / "watchers" / "rendered" / ctx.machine
    sheet_name = "design/INSTALL-WATCHERS-%s.md" % ctx.machine
    for rel in sorted(made):
        ours = (rel.startswith("watchers/rendered/%s/" % ctx.machine) and rel.endswith(".md")
                and "/" not in rel[len("watchers/rendered/%s/" % ctx.machine):]) or rel == sheet_name
        path = ctx.hub / Path(*rel.split("/"))
        if not ours or ".." in rel.split("/"):
            out(LEFT, rel, "not a path this installer writes")
        elif not path.exists():
            out(NOT_FOUND, rel)
        elif file_sha(path) != made[rel]:
            out(LEFT, rel, "changed since the installer wrote it")
        else:
            why = remove_file(ctx, path)
            out(LEFT if why else (WOULD_REMOVE if ctx.dry else REMOVED), rel,
                why or "the installer's rendering, unchanged")
    if not ctx.dry and rendered_dir.is_dir():
        try:
            if not any(rendered_dir.iterdir()):
                rendered_dir.rmdir()
        except OSError:
            pass


def uninstall_laws(ctx, record, out):
    """<claude root>/exocortex-laws.md, the program's own rendering; CLAUDE.md is
    yours and is never touched — the one line to take out of it is printed."""
    laws = record.get("laws") if isinstance(record.get("laws"), dict) else {}
    beside = ctx.claude / LAWS_BESIDE
    load = "@" + home_form(ctx, beside)
    if laws:
        recorded = Path(str(laws.get("to") or ""))
        if str(recorded) != str(beside):
            out(LEFT, str(recorded), "not where this installer renders the laws")
        elif not beside.exists():
            out(NOT_FOUND, str(beside))
        else:
            live = file_sha(beside)
            ours = bool(live) and live == laws.get("rendered_sha")
            if not ours:
                source = read_text(LAW_BOOK)
                if source is not None:
                    text, left = render_laws(ctx, source)
                    ours = not left and live == sha(text)
            if not ours:
                out(LEFT, str(beside), "it is not the installer's rendering — changed by hand?")
            else:
                why = remove_file(ctx, beside)
                out(LEFT if why else (WOULD_REMOVE if ctx.dry else REMOVED), str(beside),
                    why or "the program's rendering of the law book")
    claude_md = ctx.claude / "CLAUDE.md"
    mine = read_mine(claude_md) if claude_md.exists() else None
    if mine is not None:
        loads = load in mine or ("@" + str(beside)) in mine
        out(LEFT, str(claude_md), ("yours — remove the line `%s` from it" % load) if loads
            else "yours; it does not load the laws")


def uninstall_skills(ctx, record, out):
    """Each shipped skill folder, only while it matches the shipped copy."""
    skills = record.get("skills") if isinstance(record.get("skills"), dict) else {}
    for name in sorted(skills):
        target = ctx.claude / "skills" / name
        seen = skills.get(name) if isinstance(skills.get(name), dict) else {}
        shipped = SHIPPED_SKILLS / name
        if str(seen.get("to") or target) != str(target) or not name or "/" in name or "\\" in name:
            out(LEFT, str(seen.get("to") or name), "not where this installer puts a skill")
        elif not target.exists():
            out(NOT_FOUND, str(target))
        elif not shipped.is_dir():
            out(LEFT, str(target), "this version ships no copy of it to compare with")
        elif not same_tree(target, shipped):
            out(LEFT, str(target), "it differs from the shipped copy — yours now")
        else:
            why = remove_tree(ctx, target)
            out(LEFT if why else (WOULD_REMOVE if ctx.dry else REMOVED), str(target),
                why or "byte-identical to the shipped copy")


def road_uninstall(ctx):
    """THE WAY OUT: exactly what installed.json says this installer made, each
    thing checked before it goes; nothing else. Prints the manifest."""
    say("UNINSTALL")
    if not read_record(ctx):
        say("  no readable machine record at %s, so this machine has no install to take "
            "out. Nothing was changed." % MACHINE_FILE)
        say("")
        say("EXOCORTEX UNINSTALL · nothing recorded · OK")
        return
    path = installed_file(ctx)
    record = plain_json(path)
    say("  hub    %s" % ctx.hub)
    say("  record %s" % path)
    say("")
    if record is None:
        say("  no installed.json here, so there is no record of anything this installer "
            "made. Nothing was changed.")
        say("")
        say("EXOCORTEX UNINSTALL · %s · nothing recorded · OK" % ctx.machine)
        return
    if record.get("uninstalled"):
        say("  the record says this machine was uninstalled on %s — checked again"
            % str(record.get("uninstalled"))[:19])
    rows = []

    def out(status, what, detail=""):
        rows.append((status, what, detail))
        mark(status, what, detail)

    uninstall_jobs(ctx, record, out)
    uninstall_watchers(ctx, record, out)
    uninstall_laws(ctx, record, out)
    uninstall_skills(ctx, record, out)
    seeded = [s for s in (record.get("seeded") or []) if isinstance(s, str)]
    if seeded:
        out(LEFT, "%d seed%s in the hub folder" % (len(seeded), "" if len(seeded) == 1 else "s"),
            "yours from the moment they exist")
    out(LEFT, "the hub folder %s" % ctx.hub, "your notes, projects' state and mail — never removed")
    if PROGRAM_TREE and ctx.brain.exists() and ctx.brain.resolve() != ctx.hub.resolve():
        out(LEFT, "the brain %s" % ctx.brain, "your own files' repository — never removed")
    if not ctx.dry:
        removed = [what for status, what, _d in rows if status == REMOVED]
        record["uninstalled"] = now_iso()
        record["removed"] = sorted(set(record.get("removed") or []) | set(removed))
        write_atomic(path, json.dumps(record, indent=2, sort_keys=True) + "\n", keep_prev=False)
    gone = sum(1 for s, _w, _d in rows if s in (REMOVED, WOULD_REMOVE))
    kept = sum(1 for s, _w, _d in rows if s == LEFT)
    absent = sum(1 for s, _w, _d in rows if s == NOT_FOUND)
    say("")
    say("  %s %d · left %d · not found %d" % ("would remove" if ctx.dry else "removed",
                                               gone, kept, absent))
    if not ctx.dry:
        say("  %s now says `uninstalled` — the record of what was removed" % path.name)
    say("")
    say("EXOCORTEX UNINSTALL · %s · OK%s" % (ctx.machine, " (dry run)" if ctx.dry else ""))


# ------------------------------------------------------------------- the main

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="install.py", add_help=False,
        description="one command installs an Exocortex machine")
    parser.add_argument("--defaults", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--machine", default=None)
    parser.add_argument("--brain", default=None)
    parser.add_argument("--brain-remote", default=None)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--repair", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--only", choices=("seeds", "laws", "heartbeat", "watchers",
                                           "tree"), default=None)
    parser.add_argument("--help", "-h", action="store_true", dest="help")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        sys.stdout.write(__doc__)
        return 2
    if args.help:
        sys.stdout.write(__doc__)
        return 0

    roads = [name for name in ("update", "recover", "repair", "uninstall")
             if getattr(args, name, False)]
    if len(roads) > 1:
        sys.stdout.write("install.py: one road at a time — %s were all asked for.\n"
                         % ", ".join("--" + r for r in roads))
        return 2
    road = roads[0] if roads else None
    if road == "uninstall" and args.only:
        sys.stdout.write("install.py: --uninstall takes no --only; it reads installed.json "
                         "and removes what that records.\n")
        return 2

    ctx = Ctx(args)
    lock = Lock(LOCK_FILE)
    started = time.time()
    banner = {"update": "EXOCORTEX UPDATE", "recover": "EXOCORTEX RECOVER",
              "repair": "EXOCORTEX REPAIR",
              "uninstall": "EXOCORTEX UNINSTALL"}.get(road, "EXOCORTEX INSTALL")
    say("%s%s" % (banner, "  (dry run - nothing is changed)" if ctx.dry else ""))
    say("  program %s" % ENGINE)
    if PROGRAM_TREE:
        say("  layout  program tree · hub %s" % HUB_GUESS)
    say("")
    try:
        lock.acquire()
        if road == "uninstall":
            # The way out reads the record and never writes one: no bootstrap,
            # no repair of machine.json on the way.
            road_uninstall(ctx)
            lock.release()
            return 0
        if road:
            # Every road starts from the record: who this machine is and where
            # its folders are. Nothing else is assumed.
            step_machine(ctx)
            say("")
            if road == "update":
                road_update(ctx)
                say("")
                if not ctx.dry:
                    step_seeds(ctx)
                    say("")
                    step_laws(ctx)
                    say("")
                    step_heartbeat(ctx)
                    say("")
                    quick_gates(ctx)
            elif road == "recover":
                road_recover(ctx)
            else:
                road_repair(ctx)
            say("")
            lock.release()
            counts = {}
            for status, _what, _detail in ctx.report:
                counts[status] = counts.get(status, 0) + 1
            say("  %s  (%.1fs)" % (" · ".join(
                "%s %d" % (k, counts[k]) for k in sorted(counts)),
                time.time() - started))
            say("")
            say("EXOCORTEX %s · %s · OK" % (road.upper(), ctx.machine))
            return 0
        step_machine(ctx)
        say("")
        if args.only is None:
            step_brain(ctx)
            say("")
        if args.only in (None, "seeds"):
            step_seeds(ctx)
            say("")
        if args.only in (None, "laws"):
            step_laws(ctx)
            say("")
        if args.only in (None, "heartbeat"):
            step_heartbeat(ctx)
            say("")
        if args.only in (None, "watchers"):
            step_watchers(ctx)
            say("")
        if args.only in (None, "tree"):
            step_tree(ctx)
            say("")
    except Stop as stop:
        say("")
        say("STOP: %s" % stop)
        return 1
    except KeyboardInterrupt:
        say("")
        say("STOP: interrupted")
        return 1
    finally:
        lock.release()

    counts = {}
    for status, _what, _detail in ctx.report:
        counts[status] = counts.get(status, 0) + 1
    say("  %s  (%.1fs)" % (" · ".join(
        "%s %d" % (k, counts[k]) for k in sorted(counts)), time.time() - started))
    tally = []
    if args.only in (None, "heartbeat"):
        tally.append("heartbeat %d/%d" % (ctx.heartbeat_present,
                                          ctx.heartbeat_total))
        if getattr(ctx, "wrapper_total", 0):
            tally.append("sync wrapper %d/%d" % (ctx.wrapper_present,
                                                ctx.wrapper_total))
    if args.only in (None, "watchers"):
        tally.append("routines registered %d/%d"
                     % (ctx.watchers_present, ctx.rendered))
        tally.append("rendered %d" % ctx.rendered)
    if tally:
        say("  " + " · ".join(tally))
    if args.only is None and not ctx.dry:
        installed = read_installed(ctx)
        installed["jobs"] = [job["id"] for job in load_jobs()]
        write_installed(ctx, installed)
        say("")
        say(DONE_TEMPLATE % {"machine": ctx.machine,
                             "mj": str(MACHINE_FILE),
                             "hb": ctx.heartbeat_present,
                             "hbn": ctx.heartbeat_total,
                             "w": ctx.rendered,
                             "tree": ("tree open" if ctx.tree_opened
                                      else "tree drawn, not opened" if ctx.tree_drawn
                                      else "no page to open in this version")})
        if PROGRAM_TREE:
            say("  brain %s · %s" % (ctx.brain, installed_file(ctx)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
