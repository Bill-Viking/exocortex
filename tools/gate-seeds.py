#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-seeds.py — every brain file a shipped tool opens has an empty shape.

    python3 tools/gate-seeds.py            every case
    python3 tools/gate-seeds.py --keep     leave the fixture world behind
    python3 tools/gate-seeds.py --only S3  one case (its id, or several, comma-separated)

TWO PLACES IT RUNS FROM, told apart by what is there:
  a BUILD folder   beside the seeds it proves (templates/ holding them), two
                   folders below the hub; the tree is the base image plus the registry layer
  an INSTALLED hub in the hub's own tools/ folder: the tree is the program THIS
                   hub is (every file its partition rule, templates/dot-gitignore,
                   names back in) and the seeds are the ones under its
                   templates/. The cases that need what only the owner's machine
                   carries (the private word list, the release's export
                   manifest) SKIP, each with one line.

Hermetic. Every fixture is a program tree built from the base IMAGE.json into a
world under ONE folder this run makes in the system temp directory, with its own
HOME; each case's world goes at the end of that case and the whole root goes at
the end of the run. NOTHING THIS GATE WRITES GOES UNDER THE HUB — the hub is
read and never written, because the fleet's own brain sync carries `scratch/`
and a world left standing mid-run would ride a push into a private repository.
No case touches the live hub, the live brain clone, the live
installer or the network.

The cases:
  R    rails: the seeds are what the report says, the worlds are ours alone
  S1   SCRUB: no private word, no absolute path, no dot-git literal, in any seed
  S2   THE WALK: the seed walk lands every seed once, records it, and never
       overwrites a live file; a second run copies nothing and says so
  S3   TRUTHFUL ON EMPTY: every tool that reads a seeded file runs to exit 0 on
       a fresh brain and says the true empty line
  S4   PARSE SHAPES: each seed parses through the parser its own tool uses
  S5   NOTHING PERSONAL BY NAME: no ledger, no live routine, is named SHIP

WHICH COPIES ARE TESTED. Beside a build, the registry layer may still be
changing in the folder next to this one. A gate that reads a workshop floor
mid-sweep is not a gate, so the road is chosen ONCE per run and printed: the
registry layer is used only when it has declared itself finished (its build
report exists) AND every file of its own deliverable list is there. Until then
the run uses the live tools, the base sync package and the twenty-line
stand-in copier that implements the seed walk's contract, and says so on its
first line.

Every child this gate starts carries an inner mark and its depth, runs in its
own process group, and is ended with everything it started if it runs past its
timeout. Each case that starts children ends by checking that none survived and
that no fixture world was left behind.

The helpers marked "(from gate-split.py)" are COPIED from
scratch/bq045-p2c/gate-split.py rather than imported: importing it would run its
module body, which makes a world of its own and would leave a second root for
this run to account for.
"""
import contextlib
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
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if HERE.name != "tools" and (HERE / "templates" / "INBOX.md").is_file():
    LAYOUT = "build"                              # <hub>/scratch/<build>/gate-seeds.py
    HUB = HERE.parent.parent
    SEED_ROOT = HERE / "templates"
else:
    LAYOUT = "installed"                          # <hub>/tools/gate-seeds.py
    HUB = HERE.parent
    SEED_ROOT = HUB / "templates"
SCRATCH_ROOT = HUB / "scratch"
P2C = SCRATCH_ROOT / "bq045-p2c"
P3 = SCRATCH_ROOT / "bq045-p3"
IMAGE_FILE = P2C / "IMAGE.json"
DEV_TREE = Path(os.path.expanduser("~")) / "exocortex-dev"

# THE WORLDS LIVE OUTSIDE THE HUB, in the system temp directory, and nowhere
# else. The fleet's brain sync carries `scratch/` on every push, so a fixture
# world standing under the hub for the three seconds this gate runs can be
# picked up by a push that happens to land in that window and carried into a
# private repository. One root per run, made here, emptied case by case, removed at the end.
WORLD_PREFIX = "exo-gate-p4-"
WORLDS = Path(tempfile.mkdtemp(prefix=WORLD_PREFIX)).resolve()


def under(root):
    """Every path under a folder, relative and sorted — for proving that a
    folder is exactly what it was."""
    try:
        return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*"))
    except OSError:
        return []


# What this build's own folder held before any case ran. The last screen proves
# it holds exactly that afterwards — the gate says "nothing under the hub" only
# because it looked.
HERE_AT_START = under(HERE)

SCRUB_WORDS = HUB / "release" / "SCRUB-WORDS.txt"
MANIFEST = HUB / "release" / "EXPORT-MANIFEST.json"
PY = sys.executable

ARGS = sys.argv[1:]
KEEP = "--keep" in ARGS
ONLY = ""
for i, arg in enumerate(ARGS):
    if arg == "--only" and i + 1 < len(ARGS):
        ONLY = ARGS[i + 1]
    elif arg.startswith("--only="):
        ONLY = arg.split("=", 1)[1]

DEPTH = int(os.environ.get("EXO_GATE_SEEDS_DEPTH") or 0)
LAST_CHILD = None
CHILDREN = 0

BASE_ENV = dict(os.environ)

checks, fails = [], []
SKIPPED = []
CASE = "R"


# ---------------------------------------------------------------------------
# which copies are tested — decided once, printed, and never re-asked
# ---------------------------------------------------------------------------

# The registry layer's own deliverable list, the files this gate would need.
P3_TOOLS = ("exo_registry.py", "collect-openers.py", "postman.py", "mail.py",
            "exo_common.py", "i-am.py", "claim.py", "who-is-live.py", "asked.py",
            "improvements.py", "ideas.py", "pulse.py")
P3_SYNC = ("sync.py", "install.py", "carrier_preflight.py")
P3_ROOT = ("orchestrator.py",)


def p3_missing():
    """What P3 still owes before its layer is a layer. [] means it is one."""
    owed = []
    if not (P3 / "BUILD-REPORT-P3.md").is_file():
        owed.append("BUILD-REPORT-P3.md (the build has not declared itself finished)")
    for name in P3_TOOLS:
        if not (P3 / "tools" / name).is_file():
            owed.append("tools/%s" % name)
    for name in P3_SYNC:
        if not (P3 / "sync" / name).is_file():
            owed.append("sync/%s" % name)
    for name in P3_ROOT:
        if not (P3 / name).is_file():
            owed.append(name)
    if not (P3 / "templates" / "registry.json").is_file():
        owed.append("templates/registry.json")
    return owed


if LAYOUT == "build":
    P3_OWED = p3_missing()
    P3_READY = not P3_OWED
    ROAD = "P3's layer" if P3_READY else "the live tools + P2c's sync + the stand-in copier"
    WALK = "P3's install.py" if P3_READY else "the stand-in copier (twenty lines, in this gate)"
else:
    P3_OWED = []                  # an installed hub IS the layer: its own tools, its own install
    P3_READY = True
    ROAD = "this hub's own program"
    WALK = "this hub's own install.py"

# The tools of the SEED column that the base image does not already carry — the
# v0.1 ship set is that image plus the registry layer, and NOTHING else goes into
# a fixture: a tool a stranger will not have must not be there to help.
TOOLS = ("improvements.py", "asked.py", "ideas.py", "mail.py", "claim.py",
         "who-is-live.py", "postman.py", "exo_common.py", "i-am.py", "pulse.py")
ROOT_TOOLS = ("orchestrator.py",)

# The seeds this build ships, by their path in the hub. Written here as the
# report writes them, and checked against the folder in R: a gate that reads its
# own answer off the thing it is proving proves nothing.
EXPECTED_SEEDS = (
    "INBOX.md",
    "STATUS.md",
    "design/BUILD-QUEUE.md",
    "dossier/TAUGHT.md",
    "dossier/INTERESTS.md",
    "dossier/LAWS.md",
    "dossier/PRINCIPLES.md",
    "dossier/PROFILE.md",
    "dossier/RHYTHMS.md",
    "guide-cards.json",
    "OPENER.md",           # the hub's own first opener
)
# Beside a build, the five are read from its templates/ and the opener from the
# release's own landed copy; in an installed hub every seed is under templates/.
BUILD_SEEDS_ELSEWHERE = {"OPENER.md": HUB / "release" / "src" / "templates" / "OPENER.md"}
# A seed whose own format decides its first line carries no opening note: an
# opener's first line is its header (`lane: …`), which the collector reads; an
# intake page's first line is personal.py's own mark (mark_line), which the
# first-run conversation reads and rewrites; and the law book's two-line header is
# exo_laws.py's own (USER_BOOK_HEADER), written by the installer's laws step.
_INTAKE = ("its first line is personal.py's own mark, which the first-run conversation "
           "reads and rewrites, so it carries no opening note")
NO_NOTE = {"OPENER.md": "an opener's first line is its header, so it carries no opening "
                        "note; the collector reads it as the hub's own opener",
           "dossier/INTERESTS.md": _INTAKE,
           "dossier/PRINCIPLES.md": _INTAKE,
           "dossier/PROFILE.md": _INTAKE,
           "dossier/RHYTHMS.md": _INTAKE,
           "dossier/LAWS.md": "its two-line header is exo_laws.py's own, written by the "
                              "installer's laws step, so it carries no opening note"}

# What the base image already ships under templates/, which the same walk must also land.
P2C_SEEDS = ("routines/sync-check.md", "watchers/SYNC-CHECK-run.md")

# Never copied by the walk: the dot-files are rendered by name, and the record is
# the installer's own.
NOT_SEEDS = ("dot-gitignore", "dot-gitattributes", "installed.json")

# What every seed's opening note must say, in its own words.
NOTE_MUST_SAY = ("shipped with the program", "once", "yours", "overwrite")


# ---------------------------------------------------------------------------
# saying what happened (from gate-split.py)
# ---------------------------------------------------------------------------

REAL_HOME = str(Path(os.path.expanduser("~")).resolve())
REAL_HOME_RAW = os.path.expanduser("~")


def shown(text):
    """Anything this gate PRINTS, with the machine folded out of it.

    A gate's output is read, pasted and committed, so no line of it carries a
    path that names this machine: the home folder folds to `~` (on this machine
    every absolute path under it carries the owner's name), and this
    run's world root folds to `<world>`, which also makes two runs of the gate
    identical apart from their clocks."""
    text = str(text)
    for real, mark in ((str(WORLDS), "<world>"),
                       (str(Path(tempfile.gettempdir()).resolve()), "<temp>"),
                       (tempfile.gettempdir(), "<temp>"),
                       (REAL_HOME, "~"), (REAL_HOME_RAW, "~")):
        if real and real != "/":
            text = text.replace(real, mark)
    return text


def case(name, title):
    global CASE
    CASE = name
    print("")
    print(shown("%s  %s" % (name, title)))
    print(shown("-" * 74))


def ok(name, cond, detail=""):
    checks.append((CASE, name, bool(cond)))
    if cond:
        print(shown("  ok    %s" % name))
    else:
        fails.append((CASE, name, detail))
        print(shown("  FAIL  %s" % name))
        if detail not in ("", None):
            print(shown("        %s" % str(detail)[:600]))


def note(text):
    print(shown("  ..    %s" % " ".join(str(text).split())[:400]))


def skip(text):
    """What this machine cannot answer, said in one line and counted."""
    SKIPPED.append("%s · %s" % (CASE, text))
    note("skipped: " + text)


def wanted(name):
    if not ONLY:
        return True
    return name in [w.strip().upper() for w in ONLY.split(",")]


# ---------------------------------------------------------------------------
# the fixture world (from gate-split.py, rooted in this build's own w/)
# ---------------------------------------------------------------------------

def world(name):
    w = WORLDS / name
    (w / "home").mkdir(parents=True, exist_ok=True)
    return w


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def read(path):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return None


def sha256_of(path):
    h = hashlib.sha256()
    with io.open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fixture_env(home, **extra):
    env = dict(BASE_ENV)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Exocortex Gate"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "gate@example.invalid"
    env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "2020-01-01T00:00:00+0000"
    env["ORCHSYNC_SETTLE"] = "0"
    # launchd and Task Scheduler are the MACHINE's, never a fixture's.
    env["EXO_INSTALL_NO_SCHEDULER"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in ("EXO_MACHINE_JSON", "EXO_PRIVACY_PROBE", "ORCHSYNC_TEST_ROOT",
                 "GITHUB_TOKEN", "GH_TOKEN", "ORCHSYNC_ALLOW_LOCAL_PUSH",
                 "ORCH_PROJECTS_ROOT", "ORCH_TAUGHT_PATH",
                 "EXO_INSTALL_REAL_SCHEDULER"):
        env.pop(name, None)
    for key, value in extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = str(value)
    return env


@contextlib.contextmanager
def in_fixture(fx):
    """Run this block as if the machine's home were the fixture's, standing in
    the fixture's hub, with the fixture's own hub first on the import path — a
    tool that imports a module from beside itself must find the FIXTURE's copy
    and never this machine's. Everything is put back afterwards."""
    saved = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
    cwd = os.getcwd()
    before = set(sys.modules)
    try:
        os.environ["HOME"] = str(fx.home)
        os.environ["USERPROFILE"] = str(fx.home)
        os.chdir(str(fx.hub))
        sys.path.insert(0, str(fx.hub))
        sys.path.insert(1, str(fx.hub / "tools"))
        yield
    finally:
        for entry in (str(fx.hub), str(fx.hub / "tools")):
            while entry in sys.path:
                sys.path.remove(entry)
        for name in list(sys.modules):
            if name not in before:
                sys.modules.pop(name, None)
        os.chdir(cwd)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def git(cwd, *args, **kw):
    env = kw.pop("env", None) or fixture_env(Path(cwd))
    proc = subprocess.run(["git", "-c", "init.defaultBranch=main", "-C", str(cwd)]
                          + [str(a) for a in args],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          env=env, universal_newlines=True, timeout=120)
    return proc.returncode, (proc.stdout or "").strip()


def git_init(path, env=None, bare=False):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    args = ["-c", "init.defaultBranch=main", "init", "-q"]
    if bare:
        args.append("--bare")
    subprocess.run(["git"] + args + [str(path)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   env=env or fixture_env(path.parent), timeout=120)
    return path


# ---------------------------------------------------------------------------
# the image — the fixture tree is the base image plus this build's seeds
# ---------------------------------------------------------------------------

def installed_image():
    """The image of the program THIS hub is: every file its own partition rule
    (templates/dot-gitignore, installed as .gitignore) names back in, read
    from the hub itself, and the two dot-files as renders. {} when the hub
    carries no such rule — it is not a program tree."""
    rule = read(HUB / "templates" / "dot-gitignore")
    if not rule:
        return {}
    tops = sorted(set(line.strip()[2:].rstrip("/") for line in rule.splitlines()
                      if line.strip().startswith("!/")))
    files = []
    for top in tops:
        if top in (".gitignore", ".gitattributes"):
            continue
        path = HUB / top
        if path.is_file():
            files.append(top)
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                    files.append(f.relative_to(HUB).as_posix())
    return {"version": "installed",
            "files": [{"from": rel, "to": rel} for rel in files],
            "renders": [{"from": "templates/dot-gitignore", "to": ".gitignore"},
                        {"from": "templates/dot-gitattributes", "to": ".gitattributes"}]}


IMAGE = (json.loads(read(IMAGE_FILE) or "{}") if LAYOUT == "build" else installed_image())

TOOL_SOURCE = {}      # path in the tree -> where this run read it from


def tool_source(name, root=False):
    """The file that ships, and where this run read it from. One road per run."""
    rel = name if root else ("tools/%s" % name)
    if LAYOUT == "installed":
        TOOL_SOURCE[rel] = "this hub"
        return HUB / (name if root else Path("tools") / name)
    if P3_READY:
        candidate = P3 / (name if root else Path("tools") / name)
        if candidate.is_file():
            TOOL_SOURCE[rel] = "P3"
            return candidate
    TOOL_SOURCE[rel] = "live"
    return HUB / (name if root else Path("tools") / name)


def image_source(spec):
    """Where one line of the base image reads from. Read-only, always."""
    if spec.startswith("dev:"):
        return DEV_TREE / spec[4:]
    if spec.startswith("scratch:"):
        return SCRATCH_ROOT / spec[8:]
    return HUB / spec


def build_tree(hub, commit=True, env=None):
    """A program tree: the base image, the tools of the SEED column, and THIS
    BUILD's seeds under templates/ at their hub-relative paths."""
    hub = Path(hub)
    for row in IMAGE["files"]:
        target = hub / Path(*row["to"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(image_source(row["from"])), str(target))
        TOOL_SOURCE.setdefault(row["to"], "P2c image")
    if P3_READY and LAYOUT == "build":   # the registry layer supersedes the base, whole
        for name in P3_SYNC:
            shutil.copyfile(str(P3 / "sync" / name), str(hub / "sync" / name))
            TOOL_SOURCE["sync/%s" % name] = "P3"
        shutil.copyfile(str(P3 / "tools" / "exo_registry.py"),
                        str(hub / "tools" / "exo_registry.py"))
        TOOL_SOURCE["tools/exo_registry.py"] = "P3"
        shutil.copyfile(str(P3 / "tools" / "collect-openers.py"),
                        str(hub / "tools" / "collect-openers.py"))
        TOOL_SOURCE["tools/collect-openers.py"] = "P3"
        (hub / "templates").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(P3 / "templates" / "registry.json"),
                        str(hub / "templates" / "registry.json"))
    for row in IMAGE["renders"]:
        shutil.copyfile(str(hub / Path(*row["from"].split("/"))),
                        str(hub / Path(*row["to"].split("/"))))
    for name in TOOLS:
        source = tool_source(name)
        if source.is_file():
            shutil.copyfile(str(source), str(hub / "tools" / name))
    for name in ROOT_TOOLS:
        source = tool_source(name, root=True)
        if source.is_file():
            shutil.copyfile(str(source), str(hub / name))
    for path in sorted(SEED_ROOT.rglob("*")):
        if path.is_file():
            target = hub / "templates" / path.relative_to(SEED_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(path), str(target))
    if LAYOUT == "build":
        for rel, source in BUILD_SEEDS_ELSEWHERE.items():
            if source.is_file():
                target = hub / "templates" / Path(*rel.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(source), str(target))
    env = env or fixture_env(hub.parent)
    if commit:
        git_init(hub, env=env)
        git(hub, "add", "-A", env=env)
        git(hub, "commit", "-q", "-m", "the program, at this version", env=env)
    return hub


def machine_record(hub, home, name="alpha", brain=None):
    record = {"name": name, "os": "gate fixture",
              "layout": "program-tree", "partition": "git-ignore",
              "roots": {"home": str(home), "claude": str(Path(home) / ".claude"),
                        "codex": str(Path(home) / ".codex"),
                        "projects": str(Path(home) / "Projects"),
                        "orchestrator": str(hub)}}
    if brain is not None:
        record["roots"]["brain"] = str(brain)
        record["roots"]["sync"] = str(Path(hub) / "sync")
    write(Path(hub) / "machine.json",
          json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


class Fixture(object):
    def __init__(self, w, home, hub, env, machine):
        self.w, self.home, self.hub = w, home, hub
        self.env, self.machine = env, machine


def stranger(name, machine="alpha", commit=True):
    """A whole stranger machine: a program tree, an empty brain, a record.

    A tool reads the machine record from one of two places depending on the
    layout it was written for, so a fixture writes both: the hub's own
    machine.json (the program tree) and the one an older layout keeps beside it.
    Neither carries a word of anyone's."""
    w = world(name)
    home = w / "home"
    hub = home / "Exocortex"
    env = fixture_env(home)
    build_tree(hub, commit=commit, env=env)
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    record = machine_record(hub, home, machine)
    legacy = home / "orchestrator-sync"
    legacy.mkdir(parents=True, exist_ok=True)
    write(legacy / "machine.json",
          json.dumps(record, indent=2, sort_keys=True) + "\n")
    return Fixture(w, home, hub, env, machine)


# ---------------------------------------------------------------------------
# children: marked, bounded, and never left behind (from gate-split.py)
# ---------------------------------------------------------------------------

def run_child(script, *args, **kw):
    """(exit code, output) from a tool run as a program."""
    global LAST_CHILD, CHILDREN
    env = dict(kw.pop("env", None) or BASE_ENV)
    env["EXO_GATE_SEEDS_INNER"] = "1"
    env["EXO_GATE_SEEDS_DEPTH"] = str(DEPTH + 1)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    timeout = kw.pop("timeout", 180)
    cwd = kw.pop("cwd", None)
    cmd = [PY, str(script)] + [str(a) for a in args]
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    elif DEPTH == 0:
        group["start_new_session"] = True
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=env, cwd=(str(cwd) if cwd else None), **group)
    LAST_CHILD = proc
    CHILDREN += 1
    try:
        out, _err = proc.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        end_child(proc)
        out, _err = proc.communicate()
        out = (out or b"") + ("\ngate-seeds: the child ran past %d s and was ended "
                              "with everything it started" % timeout).encode("utf-8")
    return proc.returncode, (out or b"").decode("utf-8", "replace").strip()


def end_child(proc):
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif DEPTH == 0:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def survivors(proc):
    """Processes still alive from a child this gate started, or None when the
    question cannot be asked here."""
    if proc is None:
        return []
    try:
        if os.name == "nt":
            ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "
                  "'*gate-seeds.py*' -and $_.ProcessId -ne %d } | "
                  "Select-Object -ExpandProperty ProcessId" % os.getpid())
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        else:
            r = subprocess.run(["pgrep", "-g", str(proc.pid)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return sorted(int(x) for x in r.stdout.decode("utf-8", "replace").split()
                  if x.isdigit())


def sweep(proc):
    found = survivors(proc)
    if found:
        import signal
        for pid in found:
            try:
                if os.name == "nt":
                    subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    return found


def fixture_dirs():
    """The worlds standing inside this run's own root, right now."""
    try:
        return sorted(p.name for p in WORLDS.iterdir() if p.is_dir())
    except OSError:
        return []


def other_roots():
    """Roots left behind by an EARLIER run of this gate that did not finish.

    A gate that leaves its own litter cannot tell the reader the machine is
    clean, so it names what it found and takes it away."""
    found = []
    try:
        for path in sorted(Path(tempfile.gettempdir()).glob(WORLD_PREFIX + "*")):
            if path.is_dir() and path.resolve() != WORLDS:
                found.append(path)
    except OSError:
        pass
    return found


def spawned_case_ends(name):
    """The two lines every case that starts a child ends with."""
    left = sweep(LAST_CHILD)
    ok("strays 0 — no process from this case is still alive", left == [],
       "still running, now ended: %s" % left if left else "unknowable here")
    if not KEEP:
        shutil.rmtree(str(WORLDS / name), ignore_errors=True)
    ok("this case's fixture world is gone",
       KEEP or not (WORLDS / name).exists(), "kept (--keep)" if KEEP else "")


def load(path, name=None):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        name or ("under_test_%d" % abs(hash(str(path)))), str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# the private list (from gate-split.py) — read at run time, never written down
# ---------------------------------------------------------------------------

def fold(text):
    """Accents folded, so a name under a diacritic is still that name."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def scrub_words():
    """The words this machine keeps private: the owner's list when it is here
    (release/SCRUB-WORDS.txt), else the names the hub's own registry.json
    carries — the person's name, short word and aliases, their machines' names
    and labels, their persona words. Empty when neither names anybody."""
    words = []
    for line in (read(SCRUB_WORDS) or "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    if words:
        return words
    try:
        reg = json.loads(read(HUB / "registry.json") or "{}")
    except ValueError:
        reg = {}
    owner = reg.get("owner") if isinstance(reg.get("owner"), dict) else {}
    found = [owner.get("name"), owner.get("short")] + list(owner.get("aliases") or [])
    for name, block in (reg.get("machines") or {}).items():
        found.append(name)
        if isinstance(block, dict):
            found.append(block.get("label"))
    found += list((reg.get("mind_aliases") or {}).values())
    return sorted(set(w.strip() for w in found if isinstance(w, str) and len(w.strip()) > 1))


def masked(word):
    """A word the gate has to REPORT without SAYING it: first letter, length."""
    word = str(word)
    return "%s… (%d)" % (word[:1], len(word))


def scrub_hits(paths, words):
    """[(file, the word MASKED, the line)] — whole-word, case and accents folded.
    The word itself never leaves this function."""
    patterns = [(w, re.compile(r"(?<![0-9A-Za-z])" + re.escape(fold(w))
                               + r"(?![0-9A-Za-z])", re.IGNORECASE)) for w in words]
    hits = []
    for path in paths:
        try:
            text = fold(read(path) or "")
        except Exception:
            continue
        for word, pattern in patterns:
            found = pattern.search(text)
            if found:
                line = text[:found.start()].count("\n") + 1
                hits.append((Path(path).name, masked(word), line))
    return hits


# ---------------------------------------------------------------------------
# the seed walk — the registry layer's install.py when it is finished, else the
# contract in twenty lines. Either way this is the one rule and nothing else.
# ---------------------------------------------------------------------------

def standin_seed_walk(hub):
    """The seed walk's contract, in twenty lines.

    EVERY file under templates/ except the dot-files (rendered by name) and
    installed.json (the record) pairs with <hub>/<same relative path>; copy when
    absent, never overwrite a live file, record every copy in installed.json."""
    hub = Path(hub)
    templates = hub / "templates"
    record_file = hub / "installed.json"
    record = json.loads(read(record_file) or "{}") or {}
    record.setdefault("version", 1)
    known = set(record.get("seeded") or [])
    copied = []
    for source in sorted(p for p in templates.rglob("*") if p.is_file()):
        rel = source.relative_to(templates).as_posix()
        if rel in NOT_SEEDS or Path(rel).name.startswith("dot-"):
            continue
        target = hub / Path(*rel.split("/"))
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
        known.add(rel)
        copied.append(rel)
    record["seeded"] = sorted(known)
    write(record_file, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return copied


def run_seed_walk(fx):
    """(what it copied this run, what it said). One road or the other, never the
    live installer and never the live hub."""
    if P3_READY:
        code, out = run_child(fx.hub / "sync" / "install.py", "--defaults",
                              "--machine", fx.machine, "--only", "seeds",
                              env=fixture_env(fx.home), cwd=fx.hub)
        new = [l for l in out.splitlines() if "seeded from templates" in l]
        return [l.split()[1] for l in new if len(l.split()) > 1], "%s (exit %s)" % (
            out.splitlines()[-1] if out.splitlines() else "", code)
    copied = standin_seed_walk(fx.hub)
    return copied, "the stand-in copied %d" % len(copied)


def shipped_walk(fx):
    """What the seed walk IN THE FIXTURE TREE lands, run as the installer's own
    step 3. This is the road a stranger's first install takes."""
    code, out = run_child(fx.hub / "sync" / "install.py", "--defaults", "--machine",
                          fx.machine, "--only", "seeds",
                          env=fixture_env(fx.home), cwd=fx.hub)
    record = json.loads(read(fx.hub / "installed.json") or "{}") or {}
    return code, out, sorted(record.get("seeded") or [])


# ---------------------------------------------------------------------------
# R — rails
# ---------------------------------------------------------------------------

# The program's OTHER templates — what an installed hub's templates/ holds
# beside the seeds this gate proves (the registry seed, the base image's two, the rendered
# dot-files' sources, the install record, the skills a release carries).
OTHER_TEMPLATES = set(P2C_SEEDS) | set(NOT_SEEDS) | {"registry.json"}


def seed_rel_paths():
    """Every seed this build ships, by its path in the hub — read from the
    folder, so the gate is never told an answer the folder does not hold. In an
    installed hub the folder is the program's templates/, and its OTHER
    templates are left out by name."""
    found = sorted(p.relative_to(SEED_ROOT).as_posix()
                   for p in SEED_ROOT.rglob("*") if p.is_file())
    if LAYOUT == "build":
        found = sorted(set(found) | set(rel for rel, source in BUILD_SEEDS_ELSEWHERE.items()
                                        if source.is_file()))
    if LAYOUT == "installed":
        found = [f for f in found
                 if f not in OTHER_TEMPLATES and not f.startswith("skills/")
                 and "__pycache__" not in f]
    return found


def seed_path(rel):
    """Where one seed is read from."""
    if LAYOUT == "build" and rel in BUILD_SEEDS_ELSEWHERE:
        return BUILD_SEEDS_ELSEWHERE[rel]
    return SEED_ROOT / Path(*rel.split("/"))


def case_rails():
    case("R", "rails: the seeds are what the report says, the worlds are ours")
    if LAYOUT == "build":
        ok("the private word list is where the brief says it is", SCRUB_WORDS.is_file(),
           shown(SCRUB_WORDS))
        ok("P2c's image is readable", bool(IMAGE.get("files")), IMAGE_FILE.name)
        ok("the dev tree is readable, read-only", DEV_TREE.is_dir(), shown(DEV_TREE))
    else:
        ok("this hub's own program is readable as the image",
           bool(IMAGE.get("files")), "%d files" % len(IMAGE.get("files") or []))
    found = seed_rel_paths()
    ok("the seeds on disk are exactly the seeds the report names",
       found == sorted(EXPECTED_SEEDS), found)
    ok("no seed is named for a dot-file or the install record",
       not [f for f in found if Path(f).name in NOT_SEEDS
            or Path(f).name.startswith("dot-")], found)
    ok("the world root is in the system temp directory",
       WORLDS.parent == Path(tempfile.gettempdir()).resolve(), shown(WORLDS))
    ok("the world root is NOT under the hub, so nothing this gate makes can "
       "ride a brain push", HUB.resolve() not in WORLDS.parents
       and WORLDS != HUB.resolve(), shown(WORLDS))
    ok("this run's root was made by this run and is empty", fixture_dirs() == [],
       fixture_dirs())
    strays = other_roots()
    for path in strays:
        shutil.rmtree(str(path), ignore_errors=True)
    ok("no root of an unfinished earlier run is left on this machine",
       strays == [], "found and removed: %s" % [p.name for p in strays])
    note("the road this run tests: %s" % ROAD)
    note("the seed walk under test: %s" % WALK)
    if P3_OWED:
        note("P3's layer is not used this run; it still owes: %s"
             % ", ".join(P3_OWED[:8]) + (" (+%d more)" % (len(P3_OWED) - 8)
                                         if len(P3_OWED) > 8 else ""))


# ---------------------------------------------------------------------------
# S1 — scrub
# ---------------------------------------------------------------------------

HOME_PATH = re.compile(r"(?<![\w.])/(?:Users|home)/[A-Za-z0-9_.\-]+")
WIN_PATH = re.compile(r"(?<![\w])[A-Za-z]:\\")
DOT_GIT = re.compile(r"\.git(?:ignore|attributes|modules|)\b")


def opening_note(path, text):
    """A seed's first-line comment: the HTML comment it opens with, or the JSON
    file's own `note` key."""
    if path.suffix == ".json":
        try:
            return str(json.loads(text).get("note") or "")
        except ValueError:
            return ""
    if not text.lstrip().startswith("<!--"):
        return ""
    end = text.find("-->")
    return text[:end] if end > 0 else ""


def case_scrub():
    case("S1", "SCRUB: no private word, no absolute path, no dot-git literal")
    words = scrub_words()
    rels = seed_rel_paths()
    seeds = [seed_path(rel) for rel in rels]
    if LAYOUT == "installed" and not words:
        skip("no private word is known on this machine — no release/SCRUB-WORDS.txt and a "
             "registry.json that names nobody — so the two word checks have nothing to "
             "look for; the path, dot-git and note checks below still run")
    else:
        ok("the private list was read and is not empty", len(words) > 0, len(words))
        hits = scrub_hits(seeds, words)
        ok("the private list, folded and at word boundaries, finds nothing in any seed",
           hits == [], ["%s %s line %d" % h for h in hits])
    for rel, path in zip(rels, seeds):
        text = read(path) or ""
        found = HOME_PATH.search(text) or WIN_PATH.search(text)
        ok("no absolute path in %s" % rel, found is None,
           "line %d" % (text[:found.start()].count("\n") + 1) if found else "")
        found = DOT_GIT.search(text)
        ok("no dot-git literal name in %s" % rel, found is None,
           "line %d" % (text[:found.start()].count("\n") + 1) if found else "")
        if rel in NO_NOTE:
            note("%s: no opening note is asked of it — %s" % (rel, NO_NOTE[rel]))
        else:
            said = opening_note(path, text).lower()
            missing = [w for w in NOTE_MUST_SAY if w not in said]
            ok("%s opens by saying it was shipped, copied once, is yours, and is "
               "never overwritten" % rel, not missing,
               "its opening note does not say: %s" % ", ".join(missing))
        if path.suffix == ".json":
            ok("%s is valid JSON" % rel, isinstance(json.loads(text), dict))


# ---------------------------------------------------------------------------
# S2 — the walk
# ---------------------------------------------------------------------------

def case_walk():
    case("S2", "THE WALK: every seed lands once, is recorded, and never "
               "overwrites a live file")
    fx = stranger("s2")
    note("the walk under test: %s" % WALK)

    # What the seed walk IN THE SHIPPED TREE does today. When the widened walk
    # has landed this IS the proof; until then it shows exactly what is still owed.
    code, out, shipped = shipped_walk(fx)
    ok("the installer's seed step runs to its end", code == 0, out[-400:])
    ok("it lands P2c's two seeds", set(P2C_SEEDS) <= set(shipped), shipped)
    landed = [s for s in EXPECTED_SEEDS if s in shipped]
    if P3_READY:
        ok("the shipped seed walk lands every seed this gate names (%d)" % len(EXPECTED_SEEDS),
           len(landed) == len(EXPECTED_SEEDS), shipped)
    else:
        ok("the shipped seed walk lands NONE of this build's seeds — the "
           "widening of seed_pairs to the whole templates tree is P3's "
           "(brief §3 L); this is what that change has to make true",
           landed == [], shipped)
    for rel in EXPECTED_SEEDS:                     # a clean slate for the road below
        target = fx.hub / Path(*rel.split("/"))
        if target.exists():
            target.unlink()
    record = json.loads(read(fx.hub / "installed.json") or "{}") or {}
    record["seeded"] = [s for s in (record.get("seeded") or [])
                        if s not in EXPECTED_SEEDS]
    write(fx.hub / "installed.json", json.dumps(record, indent=2, sort_keys=True) + "\n")

    # A live file of the user's, sitting where a seed would land, before the walk.
    mine = write(fx.hub / "INBOX.md", "- a line the user wrote first\n")
    mine_sha = sha256_of(mine)

    copied, said = run_seed_walk(fx)
    note(said)
    for rel in EXPECTED_SEEDS:
        target = fx.hub / Path(*rel.split("/"))
        ok("the walk put %s at its place in the hub" % rel, target.is_file(),
           shown(target))
    for rel in P2C_SEEDS:
        ok("the walk also kept P2c's %s in place" % rel,
           (fx.hub / Path(*rel.split("/"))).is_file(), rel)
    record = json.loads(read(fx.hub / "installed.json") or "{}") or {}
    seeded = set(record.get("seeded") or [])
    for rel in EXPECTED_SEEDS:
        if rel == "INBOX.md":                      # the user's own, not seeded
            continue
        ok("installed.json records %s as seeded" % rel, rel in seeded, sorted(seeded))
    ok("the file the user had already written kept its bytes",
       sha256_of(mine) == mine_sha, shown(mine))
    ok("and was NOT recorded as seeded", "INBOX.md" not in seeded, sorted(seeded))
    for name in NOT_SEEDS:
        if name == "installed.json":
            continue                               # the record itself lives there
        ok("the walk did not copy %s to the hub" % name,
           not (fx.hub / name).exists(), name)
    strays = [p.name for p in fx.hub.iterdir() if p.name.startswith("dot-")]
    ok("no file named for a dot-file reached the hub", strays == [], strays)
    ok("the shipped copies are still under templates/, unmoved",
       all((fx.hub / "templates" / Path(*rel.split("/"))).is_file()
           for rel in EXPECTED_SEEDS))

    landed_now = {rel: (fx.hub / Path(*rel.split("/")))
                  for rel in EXPECTED_SEEDS
                  if (fx.hub / Path(*rel.split("/"))).is_file()}
    before_second = {rel: sha256_of(p) for rel, p in landed_now.items()}
    copied2, said2 = run_seed_walk(fx)
    note(said2)
    ok("a second run copies nothing", copied2 == [], copied2)
    ok("and every seeded file still has the bytes of the first run",
       all(sha256_of(landed_now[rel]) == sha for rel, sha in before_second.items()))
    ok("and the record did not grow",
       set((json.loads(read(fx.hub / "installed.json") or "{}")
            or {}).get("seeded") or []) == seeded)

    # The one seed held out above, now on the road every other seed took: the
    # user's own file is gone, so the walk may place the shipped shape.
    (fx.hub / "INBOX.md").unlink()
    copied3, said3 = run_seed_walk(fx)
    note(said3)
    ok("with the user's own INBOX.md gone, the walk places the shipped shape",
       (fx.hub / "INBOX.md").is_file() and "INBOX.md" in copied3, copied3)
    ok("   and records it", "INBOX.md" in set(
        (json.loads(read(fx.hub / "installed.json") or "{}") or {}).get("seeded") or []))
    ok("   and what landed is the seed, byte for byte",
       sha256_of(fx.hub / "INBOX.md") == sha256_of(SEED_ROOT / "INBOX.md"))
    spawned_case_ends("s2")


# ---------------------------------------------------------------------------
# S3 — truthful on empty
# ---------------------------------------------------------------------------

def tool(fx, name):
    return fx.hub / "tools" / name


def case_truthful():
    case("S3", "TRUTHFUL ON EMPTY: every reader of a seeded file runs to exit 0 "
               "and says the true empty line")
    fx = stranger("s3")
    standin_seed_walk(fx.hub)          # the seeds in place, the brain otherwise fresh
    env = fixture_env(fx.home)
    note("the tools of this run: %s" % ", ".join(
        "%s=%s" % (k, v) for k, v in sorted(TOOL_SOURCE.items())
        if not k.startswith("sync/") and k != "VERSION"))

    code, out = run_child(tool(fx, "improvements.py"), "--count", env=env, cwd=fx.hub)
    ok("improvements.py --count exits 0", code == 0, out[-300:])
    ok("   and says 0 listed, not a path",
       "0 listed" in out and "no queue at" not in out, shown(out[:200]))
    code, out = run_child(tool(fx, "improvements.py"), "--write", env=env, cwd=fx.hub)
    ok("improvements.py --write exits 0", code == 0, out[-300:])
    ok("   and writes improvements.html", (fx.hub / "improvements.html").is_file())

    code, out = run_child(tool(fx, "asked.py"), "--count", env=env, cwd=fx.hub)
    ok("asked.py --count exits 0", code == 0, out[-300:])
    ok("   and says nothing is open",
       "nothing open" in out or re.search(r"\b0 open\b", out) is not None,
       shown(out[:200]))

    code, out = run_child(tool(fx, "ideas.py"), "--count", env=env, cwd=fx.hub)
    ok("ideas.py --count exits 0", code == 0, out[-300:])
    ok("   and says 0 new · 0 total", "0 new" in out and "0 total" in out,
       shown(out[:200]))
    code, out = run_child(tool(fx, "ideas.py"), "--list", env=env, cwd=fx.hub)
    ok("ideas.py --list exits 0", code == 0, out[-300:])
    ok("   and says there are none",
       "no new ideas" in out or "no ideas yet" in out, shown(out[:200]))

    code, out = run_child(tool(fx, "mail.py"), "--read", "ALPHA/hub",
                          env=env, cwd=fx.hub)
    ok("mail.py --read exits 0", code == 0, out[-300:])
    ok("   and says there is no mail", "no mail for" in out, shown(out[:200]))

    code, out = run_child(tool(fx, "claim.py"), "--list", env=env, cwd=fx.hub)
    ok("claim.py --list exits 0", code == 0, out[-300:])
    ok("   and says there are no claims", "no claims" in out, shown(out[:200]))

    code, out = run_child(tool(fx, "who-is-live.py"), "--pen", env=env, cwd=fx.hub)
    ok("who-is-live.py --pen exits 0", code == 0, out[-300:])
    ok("   and says OK", out.startswith("OK") or "\nOK" in out, shown(out[:200]))

    code, out = run_child(tool(fx, "collect-openers.py"), "--chat", env=env, cwd=fx.hub)
    ok("collect-openers.py --chat exits 0", code == 0, out[-400:])
    ok("   and does not crash", "Traceback" not in out, shown(out[-300:]))
    code, out = run_child(tool(fx, "collect-openers.py"), "--expand", "Exocortex",
                          env=env, cwd=fx.hub)
    ok("collect-openers.py --expand exits 0", code == 0, out[-400:])
    ok("   and the card with no opener file says to open with the generic line",
       "read the project status/memory first" in out, shown(out[-300:]))
    ok("   and it reads the seeded STATUS as where things stand",
       "WHERE YOU ARE" in out and "hub folder's own state file" in out,
       shown(out[:300]))

    # THE SEEDED FILE ITSELF, PROVED: the letter mail.py appends is SEEN by the
    # board's own reader. Without the seed's `## Waiting` heading it is dropped.
    code, out = run_child(tool(fx, "mail.py"), "--send", "ALPHA/hub", "Alpha",
                          "a finding for the hub", "FYI", "--no-push",
                          env=env, cwd=fx.hub)
    ok("mail.py --send exits 0", code == 0, out[-300:])
    with in_fixture(fx):
        seen = load(fx.hub / "orchestrator.py", "orch_inbox").read_inbox()
    ok("the board's own reader SEES the letter in the seeded INBOX.md",
       len(seen) == 1, seen)

    code, out = run_child(fx.hub / "orchestrator.py", env=env, cwd=fx.hub)
    ok("orchestrator.py exits 0 on a machine with no projects", code == 0, out[-400:])
    ok("   and writes board.html", (fx.hub / "board.html").is_file(),
       "FINDING FOR P5 — the board is never drawn on a machine with no projects. "
       "orchestrator.py:1962-1964 returns before writing anything when scan() is "
       "empty, and the hub's own seeded STATUS.md cannot help because scan() "
       "walks the projects root alone (orchestrator.py:458-462). It said: %s"
       % shown(out[-200:]))

    # The same run with ONE project, so the failure above is shown to be the
    # empty projects root and nothing the seeds did.
    write(fx.home / "Projects" / "example" / "STATUS.md",
          "# STATUS - example\n\n## Now\nA fixture project.\n\n## To do\n"
          "- [ ] a first item\n\n## Important\n- nothing yet\n")
    code, out = run_child(fx.hub / "orchestrator.py", env=env, cwd=fx.hub)
    ok("orchestrator.py with one project exits 0", code == 0, out[-400:])
    ok("   and writes board.html", (fx.hub / "board.html").is_file(), shown(out[-300:]))
    ok("   and the seeded journal gives the promotion check nothing to flag",
       "Unpromoted rulings: none" in out, shown(out[-500:]))
    ok("   and the ledger line it prints reads 0 listed", "0 listed" in out,
       shown(out[-500:]))
    ok("   and the seeded guide-cards drew the guide without a crash",
       (fx.hub / "GETTING-GOING.md").is_file() and "Guide:" in out,
       shown(out[-500:]))
    spawned_case_ends("s3")


# ---------------------------------------------------------------------------
# S4 — parse shapes
# ---------------------------------------------------------------------------

def row_starts(text):
    return [l for l in text.splitlines() if l.lstrip().startswith("| BQ-")]


def case_shapes():
    case("S4", "PARSE SHAPES: each seed parses through its own tool's parser")
    fx = stranger("s4")
    standin_seed_walk(fx.hub)

    # the queue, through improvements.py's own parser
    with in_fixture(fx):
        imp = load(tool(fx, "improvements.py"), "improvements_under_test")
    text = read(fx.hub / "design" / "BUILD-QUEUE.md") or ""
    rows = imp.parse_queue(text)
    ok("the BUILD-QUEUE seed parses to zero rows through parse_queue",
       rows == [], rows)
    line = imp.count_line(imp.tally(rows))
    ok("   and its own count line says 0 listed",
       line.startswith("improvements: 0 listed"), line)
    header = [l for l in text.splitlines() if l.startswith("| id |")]
    ok("   and it carries the header row", len(header) == 1, header)
    ok("   whose cells are the seven the parser names",
       imp.split_row(header[0]) == ["id", "arc", "brief", "gates", "model",
                                    "status", "note"],
       imp.split_row(header[0]) if header else None)
    ok("   and no line of it opens a row", row_starts(text) == [], row_starts(text))

    # guide-cards, as JSON with the keys the board reads by name
    with in_fixture(fx):
        orch = load(fx.hub / "orchestrator.py", "orch_shapes")
        guide = orch.load_guide()
    data = json.loads(read(fx.hub / "guide-cards.json") or "{}")
    ok("the board's own loader reads guide-cards.json as a dict with content",
       isinstance(guide, dict) and guide == data, type(guide).__name__)
    for key, kind in (("schema_version", str), ("description", str), ("note", str),
                      ("morning_ritual", list), ("house_rules", list),
                      ("cards", list), ("tails", list)):
        ok("guide-cards.json carries %s as %s" % (key, kind.__name__),
           isinstance(data.get(key), kind), type(data.get(key)).__name__)
    for key in ("morning_ritual", "house_rules", "cards", "tails"):
        ok("guide-cards.json ships %s empty" % key, data.get(key) == [], data.get(key))

    # INBOX: the line the board's reader keys on
    inbox = read(fx.hub / "INBOX.md") or ""
    heads = [l.strip() for l in inbox.splitlines() if l.strip().startswith("#")]
    ok("the INBOX seed carries a heading whose text is what read_inbox opens on",
       any("waiting" in h.lower() for h in heads), heads)
    ok("   and that heading is the LAST one, so an appended letter falls under it",
       bool(heads) and "waiting" in heads[-1].lower(), heads)
    tail = inbox.split(heads[-1], 1)[-1] if heads else inbox
    ok("   and it ships with no entry under that heading",
       not [l for l in tail.splitlines() if l.strip().startswith("- ")],
       tail[:200])
    ok("   and it shows both line forms the tools write",
       "<target project>" in inbox and "to: <MACHINE>/<lane>" in inbox)

    # TAUGHT: the shape the journal readers key on
    taught = read(fx.hub / "dossier" / "TAUGHT.md") or ""
    ok("the TAUGHT seed opens with the append-only note, then its own heading",
       taught.lstrip().startswith("<!--") and "\n# Taught" in taught,
       taught.splitlines()[:6])
    dated = re.compile(r"^(?:-\s*)?[0-9]{4}-[0-9]{2}-[0-9]{2}")
    flagged = [l for l in taught.splitlines() if dated.match(l.strip())]
    ok("   and carries no dated line, so the promotion check has nothing to flag",
       flagged == [], flagged)
    entries = [l for l in taught.splitlines() if l.lstrip().startswith("- ")]
    ok("   and no line of it reads as a journal entry to the asks screen",
       entries == [], entries)

    # STATUS: the three headings of the contract schema
    status = read(fx.hub / "STATUS.md") or ""
    parsed = orch.parse_status(status.splitlines())
    ok("the STATUS seed parses to the contract's three sections",
       bool(parsed.get("now")) and parsed.get("todos") == []
       and bool(parsed.get("important")),
       {k: v for k, v in parsed.items() if k in ("todos", "important")})
    ok("   and its To do list ships empty", parsed.get("todos") == [],
       parsed.get("todos"))
    ok("   and it claims no file that is not there", parsed.get("refs") in ([], set(), None)
       or not [r for r in parsed.get("refs") or [] if not (fx.hub / r).exists()],
       parsed.get("refs"))
    spawned_case_ends("s4")


# ---------------------------------------------------------------------------
# S5 — nothing personal by name
# ---------------------------------------------------------------------------

LEDGER = re.compile(r"watchers/[A-Za-z0-9_.\-]*-PROPOSALS-[A-Za-z0-9_.\-]*\.md$")
BUILD_LEDGER = re.compile(r"BUILD-LEDGER-[A-Za-z0-9_.\-]*\.md$")
LIVE_ROUTINE = re.compile(r"(?:^|[:/])routines/[A-Za-z0-9_.\-]+\.md$")


def case_manifest():
    case("S5", "NOTHING PERSONAL BY NAME: no ledger, no live routine, ships")
    if LAYOUT == "installed" and not MANIFEST.is_file():
        skip("the export manifest (release/EXPORT-MANIFEST.json) is the release pipeline's "
             "own, on the machine that cuts a release; this hub has none to judge")
        return
    ok("the export manifest is readable", MANIFEST.is_file(), shown(MANIFEST))
    data = json.loads(read(MANIFEST) or "{}")
    entries = data.get("entries") or []
    ok("it has entries to judge", len(entries) > 0, len(entries))
    ship = [e for e in entries if str(e.get("class", "")).lower() == "ship"]
    ledgers, routines = [], []
    for entry in ship:
        src = str(entry.get("src", ""))
        if LEDGER.search(src) or BUILD_LEDGER.search(src):
            ledgers.append(src)
        elif LIVE_ROUTINE.search(src) and "templates/" not in src:
            routines.append(src)
    ok("no watcher proposal ledger is named SHIP",
       not [s for s in ledgers if LEDGER.search(s)], ledgers)
    ok("no build ledger is named SHIP",
       not [s for s in ledgers if BUILD_LEDGER.search(s)], ledgers)
    ok("no live routine is named SHIP", routines == [], routines)
    note("%d entries · %d named SHIP today" % (len(entries), len(ship)))
    present = [e for e in entries
               if any(str(e.get("src", "")).endswith("templates/" + rel)
                      for rel in EXPECTED_SEEDS)]
    note("this build's seeds in the manifest today: %d — Release adds them as "
         "HOLD at landing and flips them with the P3 sync package (brief §7)"
         % len(present))


# ---------------------------------------------------------------------------

CASES = [("R", case_rails), ("S1", case_scrub), ("S2", case_walk),
         ("S3", case_truthful), ("S4", case_shapes), ("S5", case_manifest)]


def guarded(name, run):
    global CASE
    try:
        run()
    except Exception as exc:                       # a case that dies is a FAIL
        CASE = name
        ok("%s ran to its end" % name, False, "%s: %s" % (type(exc).__name__, exc))
        import traceback
        for line in traceback.format_exc().splitlines()[-6:]:
            print(shown("        %s" % line))


def main():
    started = time.time()
    if LAYOUT == "installed" and not IMAGE.get("files"):
        # The one line a runner reads as "cannot run on this layout": nothing
        # else is printed, and no check is counted.
        shutil.rmtree(str(WORLDS), ignore_errors=True)
        print("gate-seeds.py: skipped here \u2014 this hub is not a program tree: it carries no "
              "partition rule (templates/dot-gitignore), and a program tree is what this "
              "gate proves")
        return 0
    print(shown("gate-seeds.py — P4: the brain records the program ships as empty shapes"))
    print(shown("road: %s · walk: %s" % (ROAD, WALK)))
    print(shown("worlds: %s — a fresh folder in the system temp directory, "
                "outside the hub" % WORLDS))
    if KEEP:                      # only a --keep run needs the real path to look at
        print("        kept at %s" % WORLDS)
    print(shown("started %s" % time.strftime("%Y-%m-%d %H:%M:%S")))
    try:
        for name, run in CASES:
            if wanted(name):
                guarded(name, run)
    finally:
        if not KEEP:
            shutil.rmtree(str(WORLDS), ignore_errors=True)
    print("")
    if KEEP:
        worlds_left = "kept (--keep) at %s" % shown(WORLDS)
    elif WORLDS.exists():
        worlds_left = "%s STILL THERE at %s" % (fixture_dirs(), shown(WORLDS))
    else:
        worlds_left = "0 · the root is gone"
    print(shown("children started: %d · fixture worlds left: %s"
                % (CHILDREN, worlds_left)))
    here_now = under(HERE)
    added = [p for p in here_now if p not in HERE_AT_START]
    gone = [p for p in HERE_AT_START if p not in here_now]
    if LAYOUT == "installed":
        # An installed hub's tools/ is a live folder other things may write;
        # the gate proves only that nothing of ITS OWN making appeared there.
        mine = lambda p: (p.split(os.sep)[0].startswith(WORLD_PREFIX)
                          or p.split(os.sep)[0] in ("w", "home", "hub"))
        added = [p for p in added if mine(p)]
        gone = [p for p in gone if mine(p)]
    print(shown("under the hub: this build's folder is unchanged — %d paths in, "
                "%d out%s" % (len(added), len(gone),
                              "" if not (added or gone)
                              else "  <-- %s %s" % (added, gone))))
    if added or gone:
        checks.append(("R", "the gate wrote nothing under the hub", False))
        fails.append(("R", "the gate wrote nothing under the hub",
                      "added %s · gone %s" % (added, gone)))
    else:
        checks.append(("R", "the gate wrote nothing under the hub", True))
    passed = sum(1 for _c, _n, good in checks if good)
    left = sweep(LAST_CHILD)
    print(shown("strays after the run: %s" % ("0" if left == [] else left)))
    if fails:
        print("")
        print(shown("FAILED:"))
        for case_name, name, detail in fails:
            print(shown("  %s  %s" % (case_name, name)))
            if detail:
                print(shown("      %s" % str(detail)[:400]))
    print("")
    print(shown("finished %s · %.1fs" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                         time.time() - started)))
    for line in SKIPPED:
        print(shown("  SKIP  %s" % line))
    print(shown("%d checks · %d passed · %d failed%s"
                % (len(checks), passed, len(checks) - passed,
                   (" · %d skipped" % len(SKIPPED)) if SKIPPED else "")))
    return 0 if not fails else 1


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    shutil.rmtree(str(WORLDS), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main()
    finally:
        if not KEEP:
            remove_own_worlds()
    sys.exit(RESULT)
