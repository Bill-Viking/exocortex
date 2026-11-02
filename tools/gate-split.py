#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-split.py — gate C: the stranger layout, proved from the program alone.

    python3 tools/gate-split.py            every case
    python3 tools/gate-split.py --keep     leave the fixture world behind to look at
    python3 tools/gate-split.py --only C6  one case (its id, or several, comma-separated)
    python3 scratch/<build>/gate-split.py --public-tree DIR  the actual exported tree

TWO PLACES IT RUNS FROM, told apart by what is there:
  a BUILD folder   beside IMAGE.json, the build's own list of the program's
                   files and where each is read from (the dev tree, scratch)
  an INSTALLED hub in the hub's own tools/ folder: the image is the program
                   THIS hub is — every file its own partition rule
                   (templates/dot-gitignore) names back in, read from the hub.
                   A hub with no such rule is not a program tree, and the gate
                   says so in one line. The cases that need the OLDER layout on
                   this machine (C13's equality) or the owner's private word
                   list (C10's scrub) SKIP, each with one line, where they are
                   not here.

Hermetic. Every fixture is a tree built from IMAGE.json into a temporary world
outside the hub, with its own HOME, and it is removed at the end. No case
touches the live hub, the live brain clone or the network: the privacy guard is
answered from a file (EXO_PRIVACY_PROBE) and every push goes to a bare
repository inside the same temporary world.

No fixture under a program-tree case has an older-layout folder in its HOME:
the gate asserts that before the case runs, so "the dev tree alone" is a fact
rather than a claim.

The cases:
  R    rails: fixtures outside the hub, the image is the whole tree
  C0   PUBLIC CLONE: actual export, missing-rule negative, shipped-rule positive
  C1   FRESH MACHINE: one command installs, and never overwrites a live file
  C2   PARTITION: every fixture lands in exactly one class; each violation
       stops the hub's entry by name while the other entries still sync
  C3   ACTIVATION BY RECORD: no record, no partition — and no mirror either
  C4   NEVER-SYNC: the machine-personal names cross in neither direction
  C5   STATE INVARIANT: no state key is a program path, after every road
  C6   UPDATE SAFETY: an update never lands on a file of yours
  C7   NO NESTED REPO: no .git path and no gitlink ever reaches the brain
  C8   RECOVERY: one command puts the live brain back; the second says so
  C9   PRIVACY GUARD: public stops the push, and no answer is ever reused
  C10  TWO STRANGER MACHINES: the second JOINs, and neither tree names a person
  C11  BRAIN OPENER: `head: none` is fresh in a git hub
  C12  MANIFESTS: the program's, with yours on top
  C13  THE SEAM: on an older fixture, this tool and the original agree exactly
  A6   SHIM FALLBACK: it fires in the one case it is for, and nowhere else

Every child this gate starts carries an inner mark and its depth, runs in its
own process group, and is ended with everything it started if it runs past its
timeout. Each case that starts children ends by checking that none survived and
that no fixture world was left behind.
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
import types
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ARGS = sys.argv[1:]
PUBLIC_TREE_ARG = None
for i, arg in enumerate(ARGS):
    if arg == "--public-tree" and i + 1 < len(ARGS):
        PUBLIC_TREE_ARG = ARGS[i + 1]
    elif arg.startswith("--public-tree="):
        PUBLIC_TREE_ARG = arg.split("=", 1)[1]
PUBLIC_TREE = Path(PUBLIC_TREE_ARG).expanduser().resolve() if PUBLIC_TREE_ARG else None
IMAGE_FILE = HERE / "IMAGE.json"
if IMAGE_FILE.is_file() or PUBLIC_TREE is not None:
    LAYOUT = "build"                         # <hub>/scratch/<build>/gate-split.py
    HUB = HERE.parent.parent
    BUILD_SYNC = HERE / "sync"
    RESOLVER = HUB / "scratch" / "bq045-p2a" / "exo_paths.py"
    COLLECTOR = HERE / "tools" / "collect-openers.py"
else:
    LAYOUT = "installed"                     # <hub>/tools/gate-split.py
    HUB = HERE.parent
    BUILD_SYNC = HUB / "sync"
    RESOLVER = HERE / "exo_paths.py"
    COLLECTOR = HERE / "collect-openers.py"
DEV_TREE = Path(os.path.expanduser("~")) / "exocortex-dev"
SCRATCH_ROOT = HUB / "scratch"
PY = sys.executable

ARGS = sys.argv[1:]
KEEP = "--keep" in ARGS
ONLY = ""
for i, arg in enumerate(ARGS):
    if arg == "--only" and i + 1 < len(ARGS):
        ONLY = ARGS[i + 1]
    elif arg.startswith("--only="):
        ONLY = arg.split("=", 1)[1]

INNER = bool(os.environ.get("EXO_GATE_SPLIT_INNER"))
DEPTH = int(os.environ.get("EXO_GATE_SPLIT_DEPTH") or 0)
MAX_DEPTH = 2
LAST_CHILD = None
CHILDREN = 0

# The older layout's folder name, written here on purpose: a gate works the old
# answers out for itself rather than asking the code it is proving.
OLDER_DIRNAME = "orchestrator-sync"

# What the tool under test calls itself when it speaks. Written
# here too, so the gate checks the name rather than asking the code for it.
PROGRAM_NAME = "exocortex-sync"

# The original tools, read-only, for the equality case.
ORIGINAL_SYNC = Path(os.path.expanduser("~")) / OLDER_DIRNAME / "sync.py"
ORIGINAL_INSTALL = Path(os.path.expanduser("~")) / OLDER_DIRNAME / "install.py"
ORIGINAL_PREFLIGHT = Path(os.path.expanduser("~")) / OLDER_DIRNAME / "carrier_preflight.py"
SCRUB_WORDS = HUB / "release" / "SCRUB-WORDS.txt"

BASE_ENV = dict(os.environ)

checks, fails = [], []
SKIPPED = []
CASES = {}
CASE = "R"


# ---------------------------------------------------------------------------
# saying what happened
# ---------------------------------------------------------------------------

REAL_HOME = str(Path(os.path.expanduser("~")).resolve())
REAL_HOME_RAW = os.path.expanduser("~")


def shown(text):
    """Anything this gate PRINTS, with the person's home folder folded to `~`.

    A gate's output is read, pasted and committed. The owner's name lives in
    every absolute path on their own machine, so no line of this gate carries
    one."""
    text = str(text)
    for home in (REAL_HOME, REAL_HOME_RAW):
        if home and home != "/":
            text = text.replace(home, "~")
    return text


def case(name, title):
    global CASE
    CASE = name
    CASES.setdefault(name, [0, 0])
    print("\n── %s %s " % (name, title) + "─" * max(0, 58 - len(title)))


def ok(name, cond, detail=""):
    checks.append(bool(cond))
    CASES.setdefault(CASE, [0, 0])[0 if cond else 1] += 1
    print(shown("  %s  %s%s" % ("ok  " if cond else "FAIL", name,
                                ("  — " + " ".join(str(detail).split())[:400])
                                if (detail and not cond) else "")))
    if not cond:
        fails.append("%s · %s" % (CASE, name))


def note(text):
    print(shown("  ..  %s" % " ".join(str(text).split())[:300]))


def skip(text):
    """What this machine cannot answer, said in one line and counted."""
    SKIPPED.append("%s · %s" % (CASE, text))
    note("skipped: " + text)


def wanted(name):
    if not ONLY:
        return True
    return name in [w.strip().upper() for w in ONLY.split(",")]


# ---------------------------------------------------------------------------
# the fixture world
# ---------------------------------------------------------------------------

SCRATCH = Path(tempfile.mkdtemp(prefix="exo-split-gate-")).resolve()


def world(name):
    w = SCRATCH / name
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


def snapshot(root):
    out = {}
    for base, dirs, files in os.walk(str(root)):
        dirs.sort()
        for f in sorted(files):
            p = Path(base, f)
            try:
                out[str(p.relative_to(root))] = sha256_of(p)
            except OSError:
                out[str(p.relative_to(root))] = "unreadable"
    return out


def fixture_env(home, **extra):
    env = dict(BASE_ENV)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "Exocortex Gate"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "gate@example.invalid"
    env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "2020-01-01T00:00:00+0000"
    env["ORCHSYNC_SETTLE"] = "0"          # a gate never waits out a settling window
    # launchd and Task Scheduler are the MACHINE's, not the fixture's: a gate
    # writes the job files and never hands one to them.
    env["EXO_INSTALL_NO_SCHEDULER"] = "1"
    # HOME does not isolate ps; use the night check's empty process-table seam.
    env["EXO_NIGHT_PS"] = os.devnull
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in ("EXO_MACHINE_JSON", "EXO_PRIVACY_PROBE", "ORCHSYNC_TEST_ROOT",
                 "GITHUB_TOKEN", "GH_TOKEN", "ORCHSYNC_ALLOW_LOCAL_PUSH"):
        env.pop(name, None)
    for key, value in extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = str(value)
    return env


class using_env(object):
    """This block runs as if the machine's home — and git's identity — were
    somewhere else. Everything is put back afterwards."""

    def __init__(self, home, **extra):
        self.values = fixture_env(home, **extra)
        self.touch = set(self.values) | {"EXO_MACHINE_JSON", "EXO_PRIVACY_PROBE",
                                         "ORCHSYNC_TEST_ROOT", "GITHUB_TOKEN",
                                         "GH_TOKEN", "ORCHSYNC_ALLOW_LOCAL_PUSH"}

    def __enter__(self):
        self.saved = dict((k, os.environ.get(k)) for k in self.touch)
        for key in self.touch:
            if key in self.values:
                os.environ[key] = self.values[key]
            else:
                os.environ.pop(key, None)
        return self

    def __exit__(self, *exc):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return False


def git(cwd, *args, **kw):
    """git in a fixture -> (code, text). Never the live hub, never the network."""
    env = kw.pop("env", None) or fixture_env(kw.pop("home", Path(cwd)))
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
# the image — every fixture tree is built from it, and from nothing else
# ---------------------------------------------------------------------------

def installed_image(root=None):
    """The image of the program THIS hub is: every file its own partition rule
    (templates/dot-gitignore, installed as .gitignore) names back in, read
    from the hub itself, and the two dot-files as renders. {} when the hub
    carries no such rule — it is not a program tree."""
    root = root or HUB
    rule = read(root / "templates" / "dot-gitignore")
    if not rule:
        return {}
    tops = sorted(set(line.strip()[2:].rstrip("/") for line in rule.splitlines()
                      if line.strip().startswith("!/")))
    files = []
    for top in tops:
        path = root / top
        if path.is_file():
            files.append(top)
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
                    files.append(f.relative_to(root).as_posix())
    return {"version": "installed",
            "files": [{"from": ("public:" if root == PUBLIC_TREE else "") + rel,
                       "to": rel} for rel in files],
            "renders": [{"from": "templates/dot-gitignore", "to": ".gitignore"},
                        {"from": "templates/dot-gitattributes", "to": ".gitattributes"}]}


IMAGE = (json.loads(read(IMAGE_FILE) or "{}") if IMAGE_FILE.is_file()
         else installed_image(PUBLIC_TREE or HUB))


def image_source(spec):
    """Where one line of the image reads from. Read-only, always."""
    if spec.startswith("public:"):
        return PUBLIC_TREE / spec[7:]
    if spec.startswith("dev:"):
        return DEV_TREE / spec[4:]
    if spec.startswith("scratch:"):
        return SCRATCH_ROOT / spec[8:]
    return HUB / spec


def image_file(to):
    """Where the image reads the file it lands at `to` from — None when the image
    names no such file."""
    for row in IMAGE.get("files") or []:
        if row["to"] == to:
            return image_source(row["from"])
    return None


if LAYOUT == "build" and IMAGE.get("files"):
    # A build folder need not carry the sync package, the resolver or the
    # collector itself: the image says where each is read from (a build that
    # carries them is read exactly as before).
    BUILD_SYNC = (image_file("sync/sync.py") or BUILD_SYNC / "sync.py").parent
    RESOLVER = image_file("tools/exo_paths.py") or RESOLVER
    COLLECTOR = image_file("tools/collect-openers.py") or COLLECTOR


def build_tree(hub, commit=True, env=None):
    """A program tree, exactly the image and nothing else, with a repository
    built at run time INSIDE the fixture world."""
    hub = Path(hub)
    for row in IMAGE["files"]:
        source = image_source(row["from"])
        target = hub / Path(*row["to"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
    for row in IMAGE["renders"]:
        shutil.copyfile(str(hub / Path(*row["from"].split("/"))),
                        str(hub / Path(*row["to"].split("/"))))
    env = env or fixture_env(hub.parent)
    if commit:
        git_init(hub, env=env)
        git(hub, "add", "-A", env=env)
        git(hub, "commit", "-q", "-m", "the program, at this version", env=env)
    return hub


def public_tree_files():
    """The actual export in build layout; the shipped program in installed layout.

    ASSUMES: the public tree contains its own root rule. This walk never renders
    it. The missing-rule clone below is the opposite case, before the first
    program commit, so installation cannot silently repair the public history.
    """
    root = PUBLIC_TREE if LAYOUT == "build" else HUB
    if root is None or not root.is_dir():
        raise ValueError("build layout needs --public-tree DIR (an actual export)")
    if (root / ".git").exists():
        code, listed = git(root, "ls-files", "-z")
        if code:
            raise ValueError("git could not list the exported program")
        rels = [r for r in listed.split("\0") if r]
    elif LAYOUT == "installed":
        rels = [row["to"] for row in IMAGE.get("files", [])]
    else:
        rels = [f.relative_to(root).as_posix() for f in root.rglob("*")
                if f.is_file() and ".git" not in f.relative_to(root).parts
                and "__pycache__" not in f.parts and f.suffix != ".pyc"]
    files = {}
    for rel in sorted(rels):
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError("the exported program is missing a regular file: " + rel)
        files[rel] = path
    return files


def build_public_clone(hub, env=None, missing_root_rule=False):
    """Copy the export unchanged, commit it in the fixture, then really clone it.

    No IMAGE renders, installer repairs, private tree or network are involved.
    The negative control drops ONLY the exported root rule before committing.
    """
    hub = Path(hub)
    env = env or fixture_env(hub.parent)
    origin = Path(tempfile.mkdtemp(prefix="public-origin-", dir=str(SCRATCH)))
    for rel, source in public_tree_files().items():
        if missing_root_rule and rel == ".gitignore":
            continue
        target = origin / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
    git_init(origin, env=env)
    for args in (("add", "-A"), ("commit", "-q", "-m", "the exported public program")):
        code, out = git(origin, *args, env=env)
        if code:
            raise ValueError("public fixture history could not be made: " + out)
    hub.parent.mkdir(parents=True, exist_ok=True)
    code, out = git(hub.parent, "clone", "-q", "--no-hardlinks", str(origin), str(hub), env=env)
    if code:
        raise ValueError("public fixture clone failed: " + out)
    return hub


def program_origin(w, hub, env):
    """A bare repository in the fixture world that the hub can fetch from."""
    bare = git_init(w / "program.git", env=env, bare=True)
    git(hub, "remote", "add", "origin", str(bare), env=env)
    git(hub, "push", "-q", "-u", "origin", "main", env=env)
    return bare


def stranger_home(w, machine="alpha", brain_bare=None, commit=True):
    """A home with a program tree in it and nothing of any older layout."""
    home = w / "home"
    hub = home / "Exocortex"
    env = fixture_env(home)
    build_tree(hub, commit=commit, env=env)
    write(home / ".claude" / "CLAUDE.md", "# the user's own rules\n")
    write(home / ".claude" / "skills" / "one" / "SKILL.md", "# a skill\n")
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    return home, hub, env


def no_older_folder(home):
    """The claim the whole gate rests on, checked rather than assumed."""
    return not (Path(home) / OLDER_DIRNAME).exists()


# ---------------------------------------------------------------------------
# children: marked, bounded, and never left behind
# ---------------------------------------------------------------------------

def run_child(script, *args, **kw):
    """(exit code, output) from a tool run as a program.

    Every child carries the inner mark and its depth, the outermost gate puts
    it in its own process group, and a child that runs past its timeout is
    ended with everything it started, so a runaway child cannot outlive the gate."""
    global LAST_CHILD, CHILDREN
    env = dict(kw.pop("env", None) or BASE_ENV)
    env["EXO_GATE_SPLIT_INNER"] = "1"
    env["EXO_GATE_SPLIT_DEPTH"] = str(DEPTH + 1)
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
        out = (out or b"") + ("\ngate-split: the child ran past %d s and was ended with "
                              "everything it started" % timeout).encode("utf-8")
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
                  "'*gate-split.py*' -and $_.ProcessId -ne %d } | "
                  "Select-Object -ExpandProperty ProcessId" % os.getpid())
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        else:
            r = subprocess.run(["pgrep", "-g", str(proc.pid)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return sorted(int(x) for x in r.stdout.decode("utf-8", "replace").split() if x.isdigit())


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
    return sorted(p.name for p in Path(tempfile.gettempdir()).glob("exo-split-gate-*"))


def stray_fixtures(before):
    left = [n for n in fixture_dirs() if n not in before]
    for name in left:
        shutil.rmtree(str(Path(tempfile.gettempdir()) / name), ignore_errors=True)
    return left


def spawned_case_ends(before):
    """The two lines every case that starts a child ends with."""
    left = sweep(LAST_CHILD)
    ok("no process from this case is still alive", left == [],
       "still running, now ended: %s" % left if left else "unknowable here")
    strays = stray_fixtures(before)
    ok("no fixture world was left behind", strays == [], strays)


# ---------------------------------------------------------------------------
# the tools under test, loaded in process where that is the honest way to ask
# ---------------------------------------------------------------------------

_LOADS = [0]


def load(path, name=None):
    import importlib.util
    _LOADS[0] += 1
    name = name or ("under_test_%d" % _LOADS[0])
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sync_of(hub, home, **env):
    """The hub's own sync tool, loaded with that machine's home in place."""
    with using_env(home, **env):
        return load(hub / "sync" / "sync.py")


def units_of(hub, home, **env):
    """(the module, its units, its notes) for one fixture, in process."""
    with using_env(home, **env):
        mod = load(hub / "sync" / "sync.py")
        machine = mod.load_machine()
        units, notes, _map = mod.build_units(machine, mod.load_manifest())
        return mod, units, notes


def machine_record(hub, home, name="alpha", brain=None, layout="program-tree",
                   partition="git-ignore", **extra):
    """This machine's identity, written where the layout keeps it."""
    record = {"name": name, "os": "gate fixture",
              "roots": {"home": str(home), "claude": str(Path(home) / ".claude"),
                        "projects": str(Path(home) / "Projects"),
                        "orchestrator": str(hub)}}
    if brain is not None:
        record["roots"]["brain"] = str(brain)
        record["roots"]["sync"] = str(Path(hub) / "sync")
    if layout:
        record["layout"] = layout
    if partition:
        record["partition"] = partition
    record.update(extra)
    write(Path(hub) / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def make_brain(path, env, remote=None):
    """A brain repository with one commit in it — the same shape install.py
    makes, including the rules that keep one machine's bookkeeping out of the
    other's (install.py's BRAIN_IGNORE)."""
    path = Path(path)
    git_init(path, env=env)
    write(path / (".git" + "ignore"), ".sync-state*.json\nmachine.json\ninstalled.json\n")
    write(path / "README.md", "# a brain\n")
    git(path, "add", "-A", env=env)
    git(path, "commit", "-q", "-m", "brain: first commit", env=env)
    if remote:
        git(path, "remote", "add", "origin", str(remote), env=env)
    return path


def stranger(name, machine="alpha", brain_remote=None):
    """A whole stranger machine: a program tree, a brain, and a record."""
    w = world(name)
    home, hub, env = stranger_home(w)
    # where a real install puts it, so a fixture asks the real question
    brain = make_brain(home / "exocortex-brain", env, remote=brain_remote)
    machine_record(hub, home, machine, brain)
    return types.SimpleNamespace(w=w, home=home, hub=hub, brain=brain, env=env)


def classes_of(fx, **env):
    """The partition's answer for one fixture, straight from the tool."""
    mod, units, notes = units_of(fx.hub, fx.home, **env)
    return mod, mod.PARTITION_REPORT, units, notes


def hub_units(units):
    return [u.repo_rel for u in units if u.repo_rel.startswith("orchestrator/")]


def other_units(units):
    return [u.repo_rel for u in units if not u.repo_rel.startswith("orchestrator/")]


# ---------------------------------------------------------------------------
# R — rails
# ---------------------------------------------------------------------------

def case_rails():
    case("R", "rails: fixtures outside the hub, the image is the whole tree")
    ok("the fixture world is outside the hub folder",
       not str(SCRATCH).startswith(str(HUB) + os.sep), SCRATCH)
    ok("the image is here and names every file of the tree",
       len(IMAGE.get("files") or []) >= 20, len(IMAGE.get("files") or []))
    missing = [row["from"] for row in IMAGE["files"]
               if not image_source(row["from"]).is_file()]
    ok("every source the image names exists, read-only", missing == [], missing)
    fx = stranger("rails")
    ok("a fixture home has no older-layout folder in it", no_older_folder(fx.home))
    tracked = git(fx.hub, "ls-files", env=fx.env)[1].splitlines()
    on_disk = sorted(p.relative_to(fx.hub).as_posix()
                     for p in fx.hub.rglob("*")
                     if p.is_file() and ".git/" not in p.as_posix()
                     and not p.name == "machine.json")
    ok("the tree holds exactly the image, rendered",
       sorted(tracked) == sorted(on_disk),
       set(on_disk) ^ set(tracked))
    named = [p.as_posix() for p in fx.hub.rglob("*")
             if p.name in (".gitmodules",) or (p.name == ".git" and p.parent != fx.hub)]
    ok("no repository metadata was placed anywhere but the fixture's own root",
       named == [], named)
    if LAYOUT == "build" and IMAGE_FILE.is_file():
        dot = image_file("templates/dot-gitignore") or (HERE / "templates" / "dot-gitignore")
        ok("the dot-files are stored under dot- names in the build",
           dot.is_file() and not (HERE / ".gitignore").exists()
           and not (dot.parent.parent / ".gitignore").exists())
    else:
        ok("the program carries its dot-files under dot- names (templates/)",
           (image_file("templates/dot-gitignore") or HUB / "templates/dot-gitignore").is_file()
           and (image_file("templates/dot-gitattributes") or HUB / "templates/dot-gitattributes").is_file())


def case_public_clone():
    case("C0", "PUBLIC CLONE: exported rule, never rendered before commit")
    before = fixture_dirs()
    files = public_tree_files()
    ok("the actual export ships its root rule and template byte-identically",
       ".gitignore" in files and "templates/dot-gitignore" in files
       and files[".gitignore"].read_bytes() == files["templates/dot-gitignore"].read_bytes())
    for missing in (True, False):
        label = "missing root rule" if missing else "shipped root rule"
        w = world("c0-missing" if missing else "c0-fixed")
        home, hub = w / "home", w / "home/Exocortex"
        env = fixture_env(home)
        build_public_clone(hub, env=env, missing_root_rule=missing)
        expected = {rel: sha256_of(source) for rel, source in files.items()
                    if not (missing and rel == ".gitignore")}
        actual = {f.relative_to(hub).as_posix(): sha256_of(f) for f in hub.rglob("*")
                  if f.is_file() and ".git" not in f.relative_to(hub).parts}
        tracked = git(hub, "ls-files", "-z", env=env)[1].split("\0")
        ok(label + ": clone tracks exactly the exported bytes, with no renders",
           actual == expected and set(filter(None, tracked)) == set(expected))
        head = git(hub, "rev-parse", "HEAD", env=env)[1]
        brain = make_brain(home / "exocortex-brain", env)
        kept = write(brain / "orchestrator/EXISTING.md", "existing brain content\n")
        previous = snapshot(brain / "orchestrator")
        write(home / ".claude/CLAUDE.md", "# the user's own rules\n")
        (home / "Projects").mkdir(exist_ok=True)
        code, out = run_child(hub / "sync/install.py", "--defaults", "--machine", "alpha",
                              env=env, cwd=hub)
        ok(label + ": install reached DONE", code == 0 and "EXOCORTEX INSTALLED" in out,
           out[-600:])
        fx = types.SimpleNamespace(hub=hub, home=home, brain=brain, env=env)
        mod, report, units, notes = classes_of(fx)
        refusal = [n for n in notes if "did not sync" in n or "entry, also:" in n]
        if missing:
            ok(label + ": partition stopped and named .gitignore",
               report.get("mode") == "stopped" and ".gitignore" in " ".join(refusal), refusal)
            ok(label + ": the hub entry carries no files", not hub_units(units))
            code, out = run_child(hub / "sync/sync.py", "push", env=env, cwd=hub)
            ok(label + ": exit zero cannot hide the refusal", "did not sync" in out, out[-400:])
            ok(label + ": existing brain content survives",
               snapshot(brain / "orchestrator") == previous)
            ok(label + ": installer did not invent a root rule", not (hub / ".gitignore").exists())
        else:
            ok(label + ": partition on with zero hub refusal notes",
               report.get("mode") == "on" and not refusal, refusal or report.get("problems"))
            ok(label + ": root rule equals its template",
               (hub / ".gitignore").read_bytes() == (hub / "templates/dot-gitignore").read_bytes())
            ok(label + ": root rule is tracked", ".gitignore" in git(hub, "ls-files", env=env)[1].splitlines())
            code, out = run_child(hub / "sync/sync.py", "push", env=env, cwd=hub)
            ok(label + ": explicit local sync has no hub refusal",
               code == 0 and "did not sync" not in out and "entry, also:" not in out, out[-400:])
            manifest = mod.load_manifest()
            entry = next(e for e in manifest["entries"] if mod.is_hub_entry(e))
            mirror = brain / entry["repo"].replace("{machine}", "alpha")
            for rel in ("INBOX.md", "STATUS.md"):
                ok(label + ": seeded " + rel + " reaches the manifest hub brain entry",
                   (hub / rel).is_file() and (mirror / rel).is_file()
                   and (hub / rel).read_bytes() == (mirror / rel).read_bytes())
            leaked = [r for r in files if (mirror / r).is_file()]
            ok(label + ": no program file reached that brain entry", not leaked, leaked[:3])
            ok(label + ": earlier brain content survived", kept.read_text() == "existing brain content\n")
        ok(label + ": install kept the public HEAD", git(hub, "rev-parse", "HEAD", env=env)[1] == head)
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C1 — a fresh machine
# ---------------------------------------------------------------------------

def case_fresh():
    case("C1", "FRESH MACHINE: one command, and no live file overwritten")
    before = fixture_dirs()
    w = world("c1")
    # ASSUMES: copy-in installation starts without a repository. A pre-committed
    # fixture misses transient files captured by the installer's initial add.
    home, hub, env = stranger_home(w, commit=False)
    ok("copy-in really starts without a repository", not (hub / ".git").exists())
    ok("no older-layout folder anywhere under this HOME", no_older_folder(home))
    mine = write(hub / "routines" / "sync-check.md",
                 "---\nname: sync-check\n---\n\nMY OWN VERSION.\n")
    mine_sha = sha256_of(mine)
    code, out = run_child(hub / "sync" / "install.py", "--defaults", "--machine", "alpha",
                          env=fixture_env(home), cwd=hub)
    ok("the install ran to its end", code == 0, out[-700:])
    tracked_code, tracked = git(hub, "ls-files", "-z", env=env)
    ok("the installer's transient lock never enters program history",
       tracked_code == 0 and "sync/install/.lock" not in tracked.split("\0"), tracked)
    ok("nothing in it stopped", "STOP:" not in out, [l for l in out.splitlines()
                                                     if "STOP:" in l])
    brain = home / "exocortex-brain"
    ok("it named the brain folder it made", str(brain) in out, out[-400:])
    ok("the brain is a repository with a commit in it",
       git(brain, "rev-parse", "HEAD", env=env)[0] == 0)
    record = json.loads(read(hub / "machine.json") or "{}")
    ok("machine.json records the layout", record.get("layout") == "program-tree",
       record.get("layout"))
    ok("machine.json records the partition", record.get("partition") == "git-ignore",
       record.get("partition"))
    ok("machine.json records where the brain is",
       Path(record.get("roots", {}).get("brain", "")) == brain,
       record.get("roots", {}).get("brain"))
    installed = json.loads(read(hub / "installed.json") or "{}")
    seeded = set(installed.get("seeded") or [])
    ok("the seeds it copied are recorded in installed.json",
       "watchers/SYNC-CHECK-run.md" in seeded, sorted(seeded))
    ok("the file that was already there was NOT recorded as seeded",
       "routines/sync-check.md" not in seeded, sorted(seeded))
    ok("and it kept its own bytes", sha256_of(mine) == mine_sha)
    ok("the shipped template is still under templates/, unmoved",
       (hub / "templates" / "routines" / "sync-check.md").is_file())
    # ASSUMES: the program tree carries its VERSION file and the installer wrote that
    # text into installed.json. The tree's own VERSION is the truth here, whatever it
    # says; a literal once sat in this check and failed the day VERSION moved on.
    tree_version = (read(hub / "VERSION") or "").strip()
    ok("installed.json names this machine and this version",
       bool(tree_version) and installed.get("machine") == "alpha"
       and installed.get("program_version") == tree_version,
       {"VERSION": tree_version or "(no VERSION file in the tree)",
        "program_version": installed.get("program_version"),
        "machine": installed.get("machine")})
    code, out = run_child(hub / "sync" / "sync.py", "push",
                          env=fixture_env(home), cwd=hub)
    ok("a first push runs on a brain that has no remote yet", code == 0, out[-400:])
    ok("   and says so in one plain line rather than failing",
       "no remote yet" in out, out[-300:])
    ok("the mirror inside the brain holds the user's files, not the program's",
       (brain / "orchestrator" / "routines" / "sync-check.md").is_file()
       and not (brain / "orchestrator" / "sync" / "sync.py").exists(),
       sorted(p.name for p in (brain / "orchestrator").glob("*"))
       if (brain / "orchestrator").is_dir() else "no mirror")
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C2 — the partition: every file in exactly one class, every violation by name
# ---------------------------------------------------------------------------

def plant_the_table(fx):
    """The Q1 table of the split's design review, as files on a disk."""
    write(fx.hub / "STATUS.md", "# the user's own state\n")
    write(fx.hub / "design" / "notes.md", "a note of the user's\n")
    write(fx.hub / "tools" / "my-note.md", "a note that landed in the program's folder\n")
    write(fx.hub / "tools" / "__pycache__" / "mod.pyc", "cache\n")
    write(fx.hub / "scratch" / "junk.md", "scratch\n")
    write(fx.hub / "tree.html", "<html>drawn here</html>\n")
    return ({
        "tools/routine-check.py": "program",      # tracked, from the image
        "sync/sync.py": "program",                # tracked, from the image
        "STATUS.md": "brain",                     # ignored: it is the user's
        "design/notes.md": "brain",
        "tools/my-note.md": "pending",            # untracked AND un-ignored
    }, [
        # never-sync: this machine's own. The list is applied to both walks
        # BEFORE the selector, so these are pruned and never classified at all.
        "machine.json", "scratch/junk.md", "tree.html",
        "tools/__pycache__/mod.pyc",
    ])


def case_partition():
    case("C2", "PARTITION: one class each, and every violation named")
    fx = stranger("c2-clean")
    table, never = plant_the_table(fx)
    mod, report, units, notes = classes_of(fx)
    ok("the partition is on", report["mode"] == "on", report["mode"])
    classes = report["classes"]
    for rel, want in sorted(table.items()):
        ok("%s rides %s" % (rel, want), classes.get(rel) == want,
           "it was called %r" % classes.get(rel))
    for rel in never:
        ok("%s is never walked at all" % rel,
           rel not in classes
           and ("orchestrator/" + rel) not in set(u.repo_rel for u in units),
           "it was called %r" % classes.get(rel))
    ok("a path that is on neither side is in no class at all",
       "docs/NOT-HERE.md" not in classes)
    ok("every path that WAS classified got exactly one class",
       all(v in ("brain", "program", "pending", "never-sync") for v in classes.values()),
       sorted(set(classes.values())))
    ok("caches never even reach the selector",
       not any("__pycache__" in rel for rel in classes),
       [r for r in classes if "__pycache__" in r][:3])
    carried = set(u.repo_rel for u in units)
    ok("only the brain's files became units",
       carried == set("orchestrator/" + r for r, k in classes.items() if k == "brain")
       | set(other_units(units)),
       sorted(carried - set("orchestrator/" + r for r, k in classes.items()
                            if k == "brain"))[:6])
    ok("the file that rides neither carrier is named in the notes",
       any("tools/my-note.md" in n for n in notes), notes[:3])
    ok("and the sentence tells the user what to do about it",
       any("move it anywhere outside tools/" in n for n in notes),
       [n for n in notes if "my-note" in n])

    # the global ignore list: neutralised, never allowed to colour the answer
    fx2 = stranger("c2-global")
    plant_the_table(fx2)
    write(fx2.home / "global-excludes", "sync/\ntools/\n")
    write(fx2.home / ".gitconfig",
          "[core]\n\texcludesFile = %s\n" % (fx2.home / "global-excludes"))
    _m, report2, units2, _n = classes_of(fx2)
    ok("a global ignore list does not change one answer",
       report2["mode"] == "on" and report2["classes"] == report["classes"],
       report2.get("problems") or
       {k: (report["classes"].get(k), report2["classes"].get(k))
        for k in report["classes"] if report["classes"].get(k) != report2["classes"].get(k)})

    for name, prepare, expect in (
            ("a file git tracks that an ignore rule also matches",
             lambda f: (write(f.hub / "notes.md", "forced\n"),
                        git(f.hub, "add", "-f", "notes.md", env=f.env),
                        git(f.hub, "commit", "-q", "-m", "forced", env=f.env)),
             "notes.md"),
            ("an active line in the repository's own exclude file",
             lambda f: write(f.hub / ".git" / "info" / "exclude",
                             "# comment\n\ntools/routine-check.py\n"),
             "info/exclude"),
            ("an ignore file inside a program folder that git has not been told about",
             lambda f: write(f.hub / "tools" / ".gitignore", "*.log\n"),
             "tools/.gitignore"),
            ("a rule file that has been edited since the program shipped it",
             lambda f: write(f.hub / ".gitignore",
                             (read(f.hub / ".gitignore") or "") + "\n!/design/\n"),
             ".gitignore"),
            ("a rule file git no longer tracks",
             lambda f: git(f.hub, "rm", "-q", "--cached", ".gitignore", env=f.env),
             ".gitignore"),
    ):
        fx3 = stranger("c2-" + re.sub(r"[^a-z]+", "-", name.lower())[:24])
        plant_the_table(fx3)
        prepare(fx3)
        _m, report3, units3, notes3 = classes_of(fx3)
        said = " ".join(report3.get("problems") or [])
        ok("STOP: %s" % name, report3["mode"] == "stopped", report3["mode"])
        ok("   and the sentence names it", expect in said, said[:200])
        ok("   the hub's entry carried nothing", hub_units(units3) == [],
           hub_units(units3)[:4])
        ok("   while the other entries still synced",
           "claude-home/CLAUDE.md" in other_units(units3), other_units(units3)[:6])
        ok("   and the user is told the next action",
           "install.py --repair" in said, said[:160])


# ---------------------------------------------------------------------------
# C3 — activation by record
# ---------------------------------------------------------------------------

def case_activation():
    case("C3", "ACTIVATION BY RECORD: no record, no partition, and no mirror")
    before = fixture_dirs()
    fx = stranger("c3-norecord")
    plant_the_table(fx)
    # the same tree, with the activation record taken out of the machine file
    record = json.loads(read(fx.hub / "machine.json"))
    record.pop("partition", None)
    record.pop("layout", None)
    write(fx.hub / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    write(fx.brain / "orchestrator" / "STATUS.md", "what the mirror already had\n")
    git(fx.brain, "add", "-A", env=fx.env)
    git(fx.brain, "commit", "-q", "-m", "the mirror before", env=fx.env)
    mirror_before = snapshot(fx.brain / "orchestrator")
    _m, report, units, notes = classes_of(fx)
    ok("a program tree with no record stops the hub's entry",
       report["mode"] == "stopped", report["mode"])
    ok("   and says which file should have said so",
       "machine.json" in " ".join(report["problems"]), report["problems"][:1])
    ok("   the brain was not mirrored whole", hub_units(units) == [],
       hub_units(units)[:4])
    ok("   the other entries still synced",
       "claude-home/CLAUDE.md" in other_units(units))
    code, out = run_child(fx.hub / "sync" / "sync.py", "push",
                          env=fixture_env(fx.home), cwd=fx.hub)
    ok("a whole push leaves the mirror byte for byte as it was",
       snapshot(fx.brain / "orchestrator") == mirror_before,
       set(snapshot(fx.brain / "orchestrator")) ^ set(mirror_before))
    ok("   and the push itself did not fail", code in (0, 1), out[-300:])
    ok("   it said in one plain sentence what stopped", "did not sync" in out,
       out[-300:])

    # no machine file at all: nothing is read, nothing is written
    fx2 = stranger("c3-nomachine")
    (fx2.hub / "machine.json").unlink()
    mirror_before2 = snapshot(fx2.brain)
    code, out = run_child(fx2.hub / "sync" / "sync.py", "push",
                          env=fixture_env(fx2.home), cwd=fx2.hub)
    ok("with no machine file at all the tool stops before it reads anything",
       code != 0 and "machine.json" in out, (code, out[-200:]))
    ok("   and the brain is untouched", snapshot(fx2.brain) == mirror_before2)

    # a rule file that is missing: a STOP, and again no mirror
    fx3 = stranger("c3-norule")
    plant_the_table(fx3)
    (fx3.hub / ".gitignore").unlink()
    _m, report3, units3, _n = classes_of(fx3)
    ok("a record with no rule file beside it stops the hub's entry",
       report3["mode"] == "stopped", report3["mode"])
    ok("   naming the rule file", ".gitignore" in " ".join(report3["problems"]),
       report3["problems"][:1])
    ok("   and the hub carried nothing", hub_units(units3) == [])
    # the next action those sentences name has to be one that works
    code, out = run_child(fx3.hub / "sync" / "install.py", "--repair",
                          env=fixture_env(fx3.home), cwd=fx3.hub)
    ok("the repair the STOP names runs to its end", code == 0, out[-500:])
    ok("   and puts the rule file back", (fx3.hub / ".gitignore").is_file())
    _m, report4, units4, _n = classes_of(fx3)
    ok("   after which the hub's entry syncs again", report4["mode"] == "on",
       report4.get("problems") or report4["mode"])
    ok("   and the user's files are on the brain's side again",
       "orchestrator/STATUS.md" in hub_units(units4), hub_units(units4)[:4])
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C4 — never-sync
# ---------------------------------------------------------------------------

def case_never_sync():
    case("C4", "NEVER-SYNC: the machine's own files cross in neither direction")
    fx = stranger("c4")
    personal = ["machine.json", "installed.json", "scratch/note.md", "board.html",
                "board-v2.html", "tree.html", "improvements.html",
                ".claude/settings.local.json", ".claude/run.lock"]
    for rel in personal:
        if rel != "machine.json":
            write(fx.hub / Path(*rel.split("/")), "this machine's own\n")
        # and the same name planted in the mirror, for the other direction
        write(fx.brain / "orchestrator" / Path(*rel.split("/")), "from elsewhere\n")
    write(fx.hub / "report.html", "<html>a page the user wrote</html>\n")
    _m, report, units, _n = classes_of(fx)
    carried = set(u.repo_rel for u in units)
    for rel in personal:
        ok("%s crosses in neither direction" % rel,
           ("orchestrator/" + rel) not in carried)
        ok("   and is not in any class but never-sync",
           report["classes"].get(rel, "never-sync") == "never-sync",
           report["classes"].get(rel))
    ok("a page that is NOT on the exact-name list does cross",
       "orchestrator/report.html" in carried,
       sorted(r for r in carried if r.endswith(".html")))


# ---------------------------------------------------------------------------
# C5 — the state invariant
# ---------------------------------------------------------------------------

def program_keys(fx, state):
    """Every state key that names something the program owns."""
    _m, report, _u, _n = classes_of(fx)
    classes = report.get("classes") or {}
    bad = []
    for key in (state.get("units") or {}):
        if not key.startswith("orchestrator/"):
            continue
        rel = key[len("orchestrator/"):]
        if classes.get(rel) in ("program", "pending", "never-sync"):
            bad.append(key)
    return bad


def case_state():
    case("C5", "STATE INVARIANT: no state key is ever a program path")
    before = fixture_dirs()
    bare = git_init(SCRATCH / "c5-remote.git", env=fixture_env(SCRATCH), bare=True)
    fx = stranger("c5", brain_remote=bare)
    plant_the_table(fx)
    env = fixture_env(fx.home, EXO_PRIVACY_PROBE=str(write(
        fx.w / "probe.json", json.dumps({"*": "private"}))))
    # a state file that already holds a program path, as a half-migrated one would
    write(fx.brain / ".sync-state.json", json.dumps(
        {"version": 1, "units": {"orchestrator/sync/sync.py": {"live": "x", "repo": "x"},
                                 "orchestrator/tools/my-note.md": {"live": "y", "repo": "y"}}}))
    for road in ("push", "pull", "push"):
        code, out = run_child(fx.hub / "sync" / "sync.py", road, env=env, cwd=fx.hub)
        ok("%s ran" % road, code == 0, out[-400:])
    state = json.loads(read(fx.brain / ".sync-state.json") or "{}")
    ok("after pull and push, no state key is a program path",
       program_keys(fx, state) == [], program_keys(fx, state))
    ok("the state it does keep is the brain's",
       any(k.startswith("orchestrator/STATUS.md") for k in state.get("units", {})),
       sorted(state.get("units", {}))[:6])
    code, out = run_child(fx.hub / "sync" / "install.py", "--recover",
                          env=env, cwd=fx.hub)
    ok("recover ran", code == 0, out[-400:])
    state = json.loads(read(fx.brain / ".sync-state.json") or "{}")
    ok("after recover, still no state key is a program path",
       program_keys(fx, state) == [], program_keys(fx, state))
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C6 — the safe updater
# ---------------------------------------------------------------------------

def updatable(name):
    """A fixture whose hub is a clone of a program origin, with one release
    waiting in it: the release adds docs/GUIDE.md, laws/BOOK.md and notes.md."""
    w = world(name)
    home = w / "home"
    hub = home / "Exocortex"
    env = fixture_env(home)
    build_tree(hub, env=env)
    write(home / ".claude" / "CLAUDE.md", "# the user's own rules\n")
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    bare = program_origin(w, hub, env)
    brain = make_brain(w / "brain", env)
    machine_record(hub, home, "alpha", brain)
    # the next release, made in its own clone and pushed to the same origin
    upstream = w / "upstream"
    subprocess.run(["git", "clone", "-q", str(bare), str(upstream)],
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=120)
    write(upstream / "docs" / "GUIDE.md", "the guide the release brings\n")
    write(upstream / "laws" / "BOOK.md", "the law book the release brings\n")
    write(upstream / "notes.md", "a file the release puts at the top level\n")
    git(upstream, "add", "-Af", env=env)
    git(upstream, "commit", "-q", "-m", "the next release", env=env)
    git(upstream, "push", "-q", "origin", "main", env=env)
    return types.SimpleNamespace(w=w, home=home, hub=hub, brain=brain, env=env,
                                 bare=bare, upstream=upstream)


def case_update():
    case("C6", "UPDATE SAFETY: an update never lands on a file of yours")
    before = fixture_dirs()

    # 1 — an untracked file of the user's at a path the release adds
    fx = updatable("c6-collide")
    mine = write(fx.hub / "docs" / "GUIDE.md", "MY OWN GUIDE\n")
    mine_sha = sha256_of(mine)
    head_before = git(fx.hub, "rev-parse", "HEAD", env=fx.env)[1]
    code, out = run_child(fx.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx.home), cwd=fx.hub)
    ok("it stops", code != 0 and "STOP:" in out, out[-500:])
    ok("   naming the file", "docs/GUIDE.md" in out, out[-500:])
    ok("   saying whose it is", "it is yours" in out, out[-500:])
    ok("   and changing nothing",
       sha256_of(mine) == mine_sha
       and git(fx.hub, "rev-parse", "HEAD", env=fx.env)[1] == head_before)

    # 2 — the same, for a file the program's own rules IGNORE
    fx2 = updatable("c6-ignored")
    private = write(fx2.hub / "notes.md", "a private note git ignores\n")
    private_sha = sha256_of(private)
    code, out = run_child(fx2.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx2.home), cwd=fx2.hub)
    ok("an IGNORED private note at an incoming path stops it too",
       code != 0 and "notes.md" in out, out[-500:])
    ok("   and the note still holds its own bytes",
       sha256_of(private) == private_sha)

    # 3 — a file where the release needs a folder: a folder the release brings
    # and this tree does not have yet (laws/ beside a build; an installed tree
    # that already carries laws/ meets the release's docs/ instead)
    tops = set(row["to"].split("/")[0] for row in IMAGE["files"])
    coming = next(name for name in ("laws", "docs") if name not in tops)
    fx3 = updatable("c6-filedir")
    write(fx3.hub / coming, "a file of mine where a folder is coming\n")
    code, out = run_child(fx3.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx3.home), cwd=fx3.hub)
    ok("a file standing where the release needs a folder stops it",
       code != 0 and coming in out, out[-500:])
    ok("   and says it is a FILE", "as a FILE" in out, out[-400:])

    # 4 — the program's own files changed here and not committed
    fx4 = updatable("c6-dirty")
    write(fx4.hub / "evidence.py", "# edited by hand, not committed\n")
    code, out = run_child(fx4.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx4.home), cwd=fx4.hub)
    ok("a dirty tracked file stops it", code != 0 and "evidence.py" in out, out[-400:])
    ok("   and it says it will not choose", "will not choose" in out, out[-400:])

    # 5 — the clean road
    fx5 = updatable("c6-clean")
    code, out = run_child(fx5.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx5.home), cwd=fx5.hub)
    ok("a clean update runs to its end", code == 0, out[-600:])
    ok("   it fast-forwarded", (fx5.hub / "docs" / "GUIDE.md").is_file())
    ok("   it re-ran the idempotent steps", "the seeds" in out and "heartbeat" in out,
       out[-600:])
    ok("   and it checked itself before saying OK", "checks" in out, out[-400:])
    ok("   it says OK", "EXOCORTEX UPDATE" in out and "OK" in out, out[-200:])
    merges = git(fx5.hub, "rev-list", "--merges", "--count", "HEAD", env=fx5.env)[1]
    ok("   and made no merge commit", merges == "0", merges)

    # 6 — a ref that is not ahead of this checkout
    fx6 = updatable("c6-diverged")
    write(fx6.hub / "evidence.py", "# a commit only this machine has\n")
    git(fx6.hub, "add", "-A", env=fx6.env)
    git(fx6.hub, "commit", "-q", "-m", "a local commit", env=fx6.env)
    head_before = git(fx6.hub, "rev-parse", "HEAD", env=fx6.env)[1]
    code, out = run_child(fx6.hub / "sync" / "install.py", "--update",
                          env=fixture_env(fx6.home), cwd=fx6.hub)
    ok("a ref that is not ahead stops it", code != 0 and "different ways" in out,
       out[-400:])
    ok("   with no merge commit anywhere",
       git(fx6.hub, "rev-parse", "HEAD", env=fx6.env)[1] == head_before
       and git(fx6.hub, "rev-list", "--merges", "--count", "HEAD", env=fx6.env)[1] == "0")
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C7 — no nested repository, ever
# ---------------------------------------------------------------------------

def case_nested():
    case("C7", "NO NESTED REPO: no .git path and no gitlink reaches the brain")
    before = fixture_dirs()
    bare = git_init(SCRATCH / "c7-remote.git", env=fixture_env(SCRATCH), bare=True)
    fx = stranger("c7", brain_remote=bare)
    # a real repository two folders down, in the user's own half
    inner = fx.hub / "design" / "a-project"
    write(inner / "notes.md", "the user's own notes inside a repository of their own\n")
    git_init(inner, env=fx.env)
    git(inner, "add", "-A", env=fx.env)
    git(inner, "commit", "-q", "-m", "inner", env=fx.env)
    # a gitdir FILE named .git, the shape a worktree leaves behind
    write(fx.hub / "carry" / "elsewhere" / ".git", "gitdir: /somewhere/else/.git\n")
    write(fx.hub / "carry" / "elsewhere" / "kept.md", "a file beside that marker\n")
    # and a repository inside the PROGRAM's own folders
    vendored = fx.hub / "tools" / "vendored"
    write(vendored / "thing.py", "# vendored\n")
    git_init(vendored, env=fx.env)
    git(vendored, "add", "-A", env=fx.env)
    git(vendored, "commit", "-q", "-m", "vendored", env=fx.env)

    env = fixture_env(fx.home, EXO_PRIVACY_PROBE=str(write(
        fx.w / "probe.json", json.dumps({"*": "private"}))))
    code, out = run_child(fx.hub / "sync" / "sync.py", "push", env=env, cwd=fx.hub)
    ok("the push ran", code == 0, out[-500:])
    tracked = git(fx.brain, "ls-files", "-s", env=fx.env)[1].splitlines()
    paths = [line.split("\t", 1)[-1] for line in tracked if line.strip()]
    ok("the brain repository holds no .git path at any depth",
       not any(".git" in p.split("/") for p in paths),
       [p for p in paths if ".git" in p.split("/")][:4])
    ok("and no gitlink", not any(line.startswith("160000") for line in tracked),
       [l for l in tracked if l.startswith("160000")][:3])
    ok("the marker FILE named .git did not cross either",
       not (fx.brain / "orchestrator" / "carry" / "elsewhere" / ".git").exists())
    ok("the file beside it did, because that half is the user's",
       (fx.brain / "orchestrator" / "carry" / "elsewhere" / "kept.md").is_file())
    ok("the repository inside the program's folders crossed nothing at all",
       not (fx.brain / "orchestrator" / "tools" / "vendored").exists(),
       sorted(p.name for p in (fx.brain / "orchestrator" / "tools").glob("*"))
       if (fx.brain / "orchestrator" / "tools").is_dir() else "no tools/ in the mirror")
    ok("the user's own notes inside their own repository did cross",
       (fx.brain / "orchestrator" / "design" / "a-project" / "notes.md").is_file())
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C8 — the road back
# ---------------------------------------------------------------------------

def case_recovery():
    case("C8", "RECOVERY: one command puts the live brain back")
    before = fixture_dirs()
    fx = stranger("c8")
    plant_the_table(fx)
    write(fx.hub / "dossier" / "who.md", "the user's own dossier\n")
    env = fixture_env(fx.home, EXO_PRIVACY_PROBE=str(write(
        fx.w / "probe.json", json.dumps({"*": "private"}))))
    code, out = run_child(fx.hub / "sync" / "sync.py", "push", env=env, cwd=fx.hub)
    ok("a first push filled the mirror", code == 0
       and (fx.brain / "orchestrator" / "STATUS.md").is_file(), out[-400:])

    # every file git ignores, gone — exactly what `git clean -xfd` would do
    kept = write(fx.hub / "design" / "notes.md", "EDITED SINCE THE LAST SYNC\n")
    kept_sha = sha256_of(kept)
    for rel in ("STATUS.md", "dossier/who.md", "routines", "watchers"):
        target = fx.hub / rel
        if target.is_dir():
            shutil.rmtree(str(target), ignore_errors=True)
        elif target.exists():
            target.unlink()
    (fx.hub / "machine.json").unlink()
    code, out = run_child(fx.hub / "sync" / "install.py", "--recover", "--defaults",
                          "--machine", "alpha", env=env, cwd=fx.hub)
    ok("recover ran to its end", code == 0, out[-600:])
    ok("   machine.json was written again", (fx.hub / "machine.json").is_file())
    ok("   the lost files came back", (fx.hub / "STATUS.md").is_file()
       and (fx.hub / "dossier" / "who.md").is_file())
    ok("   a file that was still here kept its own bytes",
       sha256_of(kept) == kept_sha)
    ok("   and nothing of the program's was restored over",
       (fx.hub / "sync" / "sync.py").is_file())
    code, out = run_child(fx.hub / "sync" / "install.py", "--recover",
                          env=env, cwd=fx.hub)
    ok("the second run is a no-op, and says so",
       code == 0 and "nothing was missing" in out, out[-400:])
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C9 — the privacy guard
# ---------------------------------------------------------------------------

def privacy_lines(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("privacy:")]


def case_privacy():
    case("C9", "PRIVACY GUARD: public stops it, and no answer is ever reused")
    before = fixture_dirs()
    bare = git_init(SCRATCH / "c9-remote.git", env=fixture_env(SCRATCH), bare=True)
    fx = stranger("c9", brain_remote=bare)
    plant_the_table(fx)
    probe = fx.w / "probe.json"
    url = str(bare)

    def push(verdict, extra=""):
        write(probe, json.dumps({url: verdict}))
        return run_child(fx.hub / "sync" / "sync.py", "push",
                         env=fixture_env(fx.home, EXO_PRIVACY_PROBE=str(probe)),
                         cwd=fx.hub)

    def letters():
        """The addressed lines about the guard, live side and mirror side."""
        live = read(fx.hub / "INBOX.md") or ""
        mirror = read(fx.brain / "orchestrator" / "INBOX.md") or ""
        mark = "BRAIN PUSH STOPPED by the privacy guard"
        return ([l for l in live.splitlines() if mark in l],
                [l for l in mirror.splitlines() if mark in l])

    code, out = push("public")
    refs = git(bare, "for-each-ref", env=fx.env)[1]
    ok("a public address stops the push before any byte", "STOP: nothing was pushed" in out,
       out[-500:])
    ok("   the remote received nothing at all", refs.strip() == "", refs[:200])
    ok("   and the local sync finished all the same",
       (fx.brain / "orchestrator" / "STATUS.md").is_file()
       and git(fx.brain, "log", "-1", "--format=%s", env=fx.env)[1].startswith("sync:"),
       out[-300:])
    ok("   it consulted the probe exactly once", len(privacy_lines(out)) == 1,
       privacy_lines(out))
    live_lines, mirror_lines = letters()
    ok("   it left the hub one addressed letter about it", len(live_lines) == 1,
       live_lines)
    ok("   which says the address and what to do",
       live_lines and "to: ALPHA/hub" in live_lines[0] and url in live_lines[0],
       live_lines[:1])
    ok("   and the letter reached the mirror, not only this folder",
       len(mirror_lines) == 1, mirror_lines)

    code, out = push("unknown")
    ok("an unanswerable address stops the push too", "STOP: nothing was pushed" in out,
       out[-400:])
    ok("   and says the next beat will ask again", "asks again" in out, out[-300:])
    ok("   the remote is still empty",
       git(bare, "for-each-ref", env=fx.env)[1].strip() == "")
    live_lines, _m = letters()
    ok("   a second stop, for a different reason, leaves a second letter",
       len(live_lines) == 2, live_lines)
    ok("   and neither of them was repeated",
       len(set(live_lines)) == len(live_lines), live_lines)

    before_private = letters()[0]
    code, out = push("private")
    ok("with a private answer the push goes", code == 0
       and git(bare, "for-each-ref", env=fx.env)[1].strip() != "", out[-400:])
    ok("   the earlier answers were not consulted: this push asked again",
       len(privacy_lines(out)) == 1 and "private" in (privacy_lines(out) or [""])[0],
       privacy_lines(out))
    ok("   and a push that goes leaves no letter behind",
       letters()[0] == before_private, letters()[0][len(before_private):])

    code, out = run_child(fx.hub / "sync" / "sync.py", "push",
                          env=fixture_env(fx.home,
                                          EXO_PRIVACY_PROBE=str(write(probe, "{}"))),
                          cwd=fx.hub)
    ok("a beat with nothing to send asks nothing at all",
       privacy_lines(out) == [], privacy_lines(out))

    # an address that is a folder on this disk is private by construction
    fx2 = stranger("c9-local", brain_remote=git_init(
        SCRATCH / "c9-local.git", env=fixture_env(SCRATCH), bare=True))
    write(fx2.hub / "STATUS.md", "something to send\n")
    code, out = run_child(fx2.hub / "sync" / "sync.py", "push",
                          env=fixture_env(fx2.home), cwd=fx2.hub)
    ok("a folder on this disk needs no probe and no network",
       code == 0 and any("folder on this disk" in l for l in privacy_lines(out)),
       privacy_lines(out) or out[-300:])
    spawned_case_ends(before)


def case_privacy_legacy(fx):
    """The older layout is REPORT-ONLY: the line prints, the push goes."""
    probe = write(fx.w / "probe.json", json.dumps({"*": "public"}))
    code, out = run_child(fx.legacy / "sync.py", "push",
                          env=fixture_env(fx.home, EXO_PRIVACY_PROBE=str(probe)),
                          cwd=fx.legacy)
    ok("in the older layout the guard is report-only: the line prints",
       any("public" in l for l in privacy_lines(out)), privacy_lines(out) or out[-300:])
    ok("   and the push goes on", code == 0 and "report-only" in out, out[-400:])
    ok("   the remote did receive it",
       git(fx.bare, "for-each-ref", env=fx.env)[1].strip() != "")


# ---------------------------------------------------------------------------
# C10 — two stranger machines
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
    """A word the gate has to REPORT without SAYING it: its first letter and
    how long it is. A gate's own output is read, pasted and committed, so the
    private list must not survive a single run of it."""
    word = str(word)
    return "%s\u2026 (%d)" % (word[:1], len(word))


def scrub_allow():
    """Exact, case-kept, bounded patterns, as in release/scrub.py load_allow."""
    lines = (read(SCRUB_WORDS.with_name("SCRUB-ALLOW.txt")) or "").splitlines()
    return [re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(line.strip())
                       + r"(?![A-Za-z0-9_-])")
            for line in lines if line.strip() and not line.strip().startswith("#")]


def scrub_hits(paths, words, allow=()):
    """[(file, the word MASKED, the line)] — whole-word, case folded, accents
    folded. The word itself never leaves this function."""
    patterns = [(w, re.compile(r"(?<![0-9A-Za-z])" + re.escape(fold(w))
                               + r"(?![0-9A-Za-z])", re.IGNORECASE)) for w in words]
    hits = []
    for path in paths:
        try:
            text = read(path) or ""
            # Cover exact allowed spans before folding; preserve line numbers.
            for pattern in allow:
                text = pattern.sub(lambda m: " " * len(m.group(0)), text)
            text = fold(text)
        except Exception:
            continue
        for word, pattern in patterns:
            found = pattern.search(text)
            if found:
                line = text[:found.start()].count("\n") + 1
                hits.append((Path(path).name, masked(word), line))
    return hits


def case_two_machines():
    case("C10", "TWO STRANGER MACHINES: the second JOINs, and nobody is named")
    before = fixture_dirs()
    bare = git_init(SCRATCH / "c10-remote.git", env=fixture_env(SCRATCH), bare=True)
    a = stranger("c10-a", machine="alpha", brain_remote=bare)
    write(a.hub / "STATUS.md", "the first machine's state\n")
    write(a.hub / "INBOX.md", "- a letter\n")
    env_a = fixture_env(a.home, EXO_PRIVACY_PROBE=str(write(
        a.w / "probe.json", json.dumps({"*": "private"}))))
    code, out = run_child(a.hub / "sync" / "sync.py", "push", env=env_a, cwd=a.hub)
    ok("the first machine pushed its brain", code == 0
       and git(bare, "for-each-ref", env=a.env)[1].strip() != "", out[-400:])

    # the second machine: a program tree, and one command that JOINs
    w = world("c10-b")
    home_b = w / "home"
    hub_b = home_b / "Exocortex"
    env_b = fixture_env(home_b)
    build_tree(hub_b, env=env_b)
    write(home_b / ".claude" / "CLAUDE.md", "# the user's own rules\n")
    project = home_b / "Projects" / "First Project"
    write(project / "README.md", "a project on the second machine\n")
    munged = re.sub(r"[^A-Za-z0-9]", "-", str(project))
    write(home_b / ".claude" / "projects" / munged / "memory" / "MEMORY.md",
          "# what the second machine remembers\n")
    ok("the second machine's home has no older-layout folder", no_older_folder(home_b))
    code, out = run_child(hub_b / "sync" / "install.py", "--defaults", "--machine", "beta",
                          "--brain", str(bare), env=env_b, cwd=hub_b)
    ok("one command joined it to the first machine's brain", code == 0, out[-700:])
    brain_b = home_b / "exocortex-brain"
    ok("   it has the first machine's commits",
       git(brain_b, "log", "--format=%s", env=env_b)[1].count("sync:") >= 1,
       git(brain_b, "log", "--format=%s", env=env_b)[1][:200])
    ok("   the first machine's files arrived", (hub_b / "STATUS.md").is_file())
    ok("   machine.json did not cross",
       not (brain_b / "orchestrator" / "machine.json").exists())
    record_b = json.loads(read(hub_b / "machine.json") or "{}")
    ok("   and the second machine kept its own name", record_b.get("name") == "beta",
       record_b.get("name"))
    code, out = run_child(hub_b / "sync" / "sync.py", "push",
                          env=fixture_env(home_b, EXO_PRIVACY_PROBE=str(write(
                              w / "probe.json", json.dumps({"*": "private"})))),
                          cwd=hub_b)
    ok("the second machine pushed", code == 0, out[-400:])
    manifest = json.loads(read(brain_b / "sync-manifest.json") or "{}")
    mapped = (manifest.get("memories") or {}).get("map") or {}
    ok("the memories map built itself for a user who had none",
       any((v.get("munged") or {}).get("beta") for v in mapped.values()),
       sorted(mapped))
    ok("   and it holds only this user's own projects",
       set(mapped) and all(k for k in mapped), sorted(mapped))
    ok("   the user's half of the manifest carries no program entry",
       not any(e.get("id") == "orchestrator" for e in manifest.get("entries") or []),
       [e.get("id") for e in manifest.get("entries") or []])

    words = scrub_words()
    if not words:
        skip("no private word is known on this machine — no release/SCRUB-WORDS.txt and a "
             "registry.json that names nobody — so the three scrub checks have nothing to "
             "look for")
        spawned_case_ends(before)
        return
    trees = []
    for hub in (a.hub, hub_b):
        trees += [p for p in hub.rglob("*")
                  if p.is_file() and ".git/" not in p.as_posix()]
    program = set()
    for row in IMAGE["files"]:
        program.add(row["to"])
    brain_side = [p for p in trees
                  if not any(p.as_posix().endswith("/" + rel) for rel in program)]
    program_side = [p for p in trees
                    if any(p.as_posix().endswith("/" + rel) for rel in program)]
    hits_brain = scrub_hits(brain_side, words)
    ok("the private word list finds nothing in what the install WROTE",
       hits_brain == [], hits_brain[:6])
    history = []
    for brain in (a.brain, brain_b):
        code, out = git(brain, "log", "--format=%H %s", env=env_b)
        blobs = git(brain, "rev-list", "--objects", "--all", env=env_b)[1]
        history.append(out + "\n" + blobs)
    hits_history = scrub_hits([write(w / ("history-%d.txt" % i), text)
                               for i, text in enumerate(history)], words)
    ok("and nothing in either brain repository's history",
       hits_history == [], hits_history[:6])
    hits_program = scrub_hits(sorted(set(program_side)), words, scrub_allow())
    ok("the shipped program files carry no owner word either",
       hits_program == [],
       "%d hit(s), e.g. %s" % (len(hits_program), hits_program[:4]))
    if hits_program:
        note("this is the P3/P4 debt the brief's own landing note names: the "
             "manifest promotes each file the day it passes the scrub.")
        by_file = {}
        for name, _mask, _line in hits_program:
            by_file[name] = by_file.get(name, 0) + 1
        for name in sorted(by_file):
            note("  %-34s %d word(s) of the list" % (name, by_file[name]))
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# C11 — a brain opener in a hub that is a git repository
# ---------------------------------------------------------------------------

def case_brain_opener():
    case("C11", "BRAIN OPENER: `head: none` is fresh in a git hub")
    w = world("c11")
    env = fixture_env(w / "home")
    repo = w / "hub"
    write(repo / "STATUS.md", "## Now\nsomething\n")
    git_init(repo, env=env)
    git(repo, "add", "-A", env=env)
    git(repo, "commit", "-q", "-m", "the hub, as a repository", env=env)
    head = git(repo, "rev-parse", "HEAD", env=env)[1]
    plain = w / "plain"
    write(plain / "STATUS.md", "## Now\nsomething\n")

    # The copy under test is loaded from THIS build. Its unchanged siblings
    # (exo_common, grok_sessions) are not part of this change, so they are
    # found where they live, read-only, by putting the hub's tools folder on
    # the import path for the length of the load and taking it off again.
    sys.path.insert(0, str(HUB / "tools"))
    try:
        collector = load(COLLECTOR, "collector_under_test")
    finally:
        sys.path.remove(str(HUB / "tools"))
    import datetime as dt

    def grade(root, head_value, status_behind=0):
        facts = collector.git_facts(root)
        mtime = os.path.getmtime(str(Path(root) / "STATUS.md"))
        stamp = dt.datetime.fromtimestamp(mtime - status_behind).astimezone().replace(
            microsecond=0).isoformat()
        header = {"head": head_value, "status_updated": stamp}
        return collector.freshness(Path(root), header, [], {"mtime": mtime}, facts)

    ok("the hub fixture really is a repository", collector.git_facts(repo)["is_repo"])
    for spelling in ("none", "n/a", "none — this lane keeps no commits", "N/A"):
        state, notes = grade(repo, spelling)
        ok("`head: %s` grades fresh when STATUS has not moved" % spelling,
           state == "fresh", (state, notes))
    state, notes = grade(repo, "none", status_behind=120)
    ok("`head: none` grades note when STATUS is newer", state == "note", (state, notes))
    ok("   and the note says why", any("STATUS changed" in n for n in notes), notes)
    state, notes = grade(repo, "0" * 40)
    ok("a head that is a sha this repo never had still grades stale",
       state == "stale", (state, notes))
    state, notes = grade(repo, head)
    ok("a real head still grades fresh", state == "fresh", (state, notes))
    state, notes = grade(plain, "none")
    ok("a hub that is not a repository grades as it always has",
       state == "fresh", (state, notes))
    state, notes = grade(repo, "")
    ok("an opener with no head at all is still stale in a repository",
       state == "stale", (state, notes))


# ---------------------------------------------------------------------------
# C12 — the manifests
# ---------------------------------------------------------------------------

def case_manifests():
    case("C12", "MANIFESTS: the program's, with yours on top")
    fx = stranger("c12")
    write(fx.brain / "sync-manifest.json", json.dumps({
        "version": 1,
        "entries": [
            {"id": "orchestrator", "exclude": ["my-own-pattern/**"],
             "append_only": ["LEDGER.md"]},
            {"id": "notes", "kind": "file", "live": {"root": "home", "rel": "NOTES.md"},
             "repo": "home/NOTES.md", "optional": True},
        ],
        "remove": ["skills"],
    }, indent=2) + "\n")
    write(fx.home / "NOTES.md", "a file of the user's own\n")
    with using_env(fx.home):
        mod = load(fx.hub / "sync" / "sync.py")
        merged = mod.load_manifest()
        origin = dict(mod.MANIFEST_ORIGIN)
        notes = list(mod.MANIFEST_NOTES)
        machine = mod.load_machine()
        units, _n, _m = mod.build_units(machine, merged)
    entries = dict((e["id"], e) for e in merged["entries"])
    ok("the program's entries are all there",
       {"orchestrator", "claude-md", "skills", "settings-reference"} <= set(entries),
       sorted(entries))
    ok("an entry the user added is there too", "notes" in entries, sorted(entries))
    ok("the user's exclude was ADDED to the program's, not put in its place",
       "my-own-pattern/**" in entries["orchestrator"]["exclude"]
       and "tree.html" in entries["orchestrator"]["exclude"],
       entries["orchestrator"]["exclude"])
    ok("so was the append-only list",
       set(["LEDGER.md", "INBOX.md"]) <= set(entries["orchestrator"]["append_only"]),
       entries["orchestrator"]["append_only"])
    ok("each entry says where it came from",
       origin.get("orchestrator") == "both" and origin.get("notes") == "user"
       and origin.get("claude-md") == "base", origin)
    ok("an entry the user tried to remove is kept", "skills" in entries)
    ok("   and the attempt is reported in one line",
       any("never remove" in n for n in notes), notes)
    ok("the user's own entry really does carry a file",
       "home/NOTES.md" in [u.repo_rel for u in units],
       [u.repo_rel for u in units][:8])


# ---------------------------------------------------------------------------
# C13 — the seam: the older layout, unchanged to the byte
# ---------------------------------------------------------------------------

MANIFEST_SMALL = {
    "description": "what crosses between two machines",
    "entries": [
        {"id": "orchestrator", "kind": "tree", "live": {"root": "orchestrator", "rel": ""},
         "repo": "orchestrator",
         "append_only": ["INBOX.md", "dossier/TAUGHT.md"],
         "exclude": ["board*.html", "tree.html", "*.log", ".DS_Store", ".git/**"]},
        {"id": "claude-md", "kind": "file", "live": {"root": "claude", "rel": "CLAUDE.md"},
         "repo": "claude-home/CLAUDE.md"},
        {"id": "skills", "kind": "tree", "live": {"root": "claude", "rel": "skills"},
         "repo": "claude-home/skills", "exclude": [".DS_Store", ".git/**"]},
    ],
    "machines": {},
    "memories": {"repo_base": "claude-home/memories", "exclude": [".DS_Store"], "map": {}},
    "never_synced": ["credentials of any kind"],
    "version": 1,
}


def legacy_world(name):
    """The older layout, as it really is: the tool inside the brain clone, the
    hub folder holding the program and the notes together, and no git in it."""
    w = world(name)
    home = w / "home"
    hub = home / "Exocortex"
    legacy = home / OLDER_DIRNAME
    env = fixture_env(home)
    write(hub / "STATUS.md", "## Now\nthe hub's own state\n")
    write(hub / "INBOX.md", "- a letter\n")
    write(hub / "design" / "a-design.md", "a design page\n")
    write(hub / "dossier" / "TAUGHT.md", "- a lesson\n")
    write(hub / "tools" / "a-tool.py", "print('a tool')\n")
    write(hub / "tree.html", "<html>drawn here</html>\n")
    shutil.copyfile(str(RESOLVER), str(write(hub / "tools" / "exo_paths.py", "")))
    write(home / ".claude" / "CLAUDE.md", "# the user's own rules\n")
    write(home / ".claude" / "skills" / "one" / "SKILL.md", "# a skill\n")
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    legacy.mkdir(parents=True, exist_ok=True)
    # The original tools are the OLDER layout's own, on a machine that has it;
    # a machine that never had it gives the fixture the program's own
    # companion (carrier_preflight.py) and no original to compare with (C13).
    if ORIGINAL_SYNC.is_file():
        shutil.copyfile(str(ORIGINAL_SYNC), str(legacy / "sync_original.py"))
    shutil.copyfile(str(BUILD_SYNC / "sync.py"), str(legacy / "sync.py"))
    shutil.copyfile(str(ORIGINAL_PREFLIGHT if ORIGINAL_PREFLIGHT.is_file()
                        else BUILD_SYNC / "carrier_preflight.py"),
                    str(legacy / "carrier_preflight.py"))
    if ORIGINAL_INSTALL.is_file():
        shutil.copyfile(str(ORIGINAL_INSTALL), str(legacy / "install_original.py"))
    shutil.copyfile(str(BUILD_SYNC / "install.py"), str(legacy / "install.py"))
    (legacy / "install").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(BUILD_SYNC / "install" / "jobs.json"),
                    str(legacy / "install" / "jobs.json"))
    (legacy / "install" / "templates").mkdir(parents=True, exist_ok=True)
    for tmpl in (BUILD_SYNC / "install" / "templates").glob("*.tmpl"):
        shutil.copyfile(str(tmpl), str(legacy / "install" / "templates" / tmpl.name))
    write(legacy / "machine.json", json.dumps({
        "name": "alpha", "os": "gate fixture",
        "roots": {"home": str(home), "claude": str(home / ".claude"),
                  "projects": str(home / "Projects"), "orchestrator": str(hub)},
        "bootstrapped": "2020-01-01T00:00:00Z"}, indent=2, sort_keys=True) + "\n")
    write(legacy / "sync-manifest.json",
          json.dumps(MANIFEST_SMALL, indent=2, sort_keys=True) + "\n")
    write(legacy / "orchestrator" / "STATUS.md", "## Now\nan older copy\n")
    write(legacy / "orchestrator" / "carried.md", "something only the mirror has\n")
    write(legacy / ".gitignore", "machine.json\n.sync-state*.json\n")
    git_init(legacy, env=env)
    git(legacy, "add", "-A", env=env)
    git(legacy, "commit", "-q", "-m", "the brain, before", env=env)
    bare = git_init(w / "origin.git", env=env, bare=True)
    git(legacy, "remote", "add", "origin", str(bare), env=env)
    git(legacy, "push", "-q", "-u", "origin", "main", env=env)
    return types.SimpleNamespace(w=w, home=home, hub=hub, legacy=legacy, env=env,
                                 bare=bare)


TIME_LINE = re.compile(r"^(\s*time\s*:).*$", re.M)
AGE = re.compile(r"\b\d+ (seconds|minutes|hours|days) ago\b")
SHA = re.compile(r"\b[0-9a-f]{8}\b")


def normalised(text):
    """The parts of a status page that are the SAME question asked twice: the
    clock it printed and the ages it worked out from the clock."""
    text = TIME_LINE.sub(r"\1 <when>", text)
    text = AGE.sub("<age>", text)
    return SHA.sub("<sha>", text)


def run_in(module_path, home, verb, args=None):
    """One verb of one tool, in process, with that machine's home in place."""
    args = args or types.SimpleNamespace(settle=0, retries=1)
    buffer = io.StringIO()
    with using_env(home):
        mod = load(module_path)
        with contextlib.redirect_stdout(buffer):
            code = getattr(mod, "cmd_" + verb)(args)
        result = {"code": code, "out": buffer.getvalue()}
        if verb == "status":
            machine = mod.load_machine()
            units, _n, _m = mod.build_units(machine, mod.load_manifest())
            actions = mod.plan(units, mod.load_state())
            result["plan"] = sorted((a.unit.repo_rel, a.kind) for a in actions)
            # the drift buckets, which is what the page is a picture OF
            result["buckets"] = dict(
                (kind, sorted(a.unit.repo_rel for a in rows))
                for kind, rows in mod.group(actions).items())
    return result


def render_jobs(module_path, home, hub, machine="alpha"):
    """Every job this installer would write, as text."""
    import datetime as dt
    with using_env(home):
        mod = load(module_path)
        args = types.SimpleNamespace(dry_run=False, defaults=True, machine=machine,
                                     only=None, help=False, brain=None,
                                     brain_remote=None, ref=None, update=False,
                                     recover=False, repair=False)
        ctx = mod.Ctx(args)
        ctx.machine = machine
        ctx.roots = {"home": str(home), "claude": str(Path(home) / ".claude"),
                     "projects": str(Path(home) / "Projects"),
                     "orchestrator": str(hub)}
        jobs = mod.load_jobs()
        out = []
        for job in jobs:
            target, text = mod.plist_for(ctx, job)
            out.append((Path(target).name, text))
        for spec in mod.windows_spec(ctx, jobs, dt.datetime(2020, 1, 1, 0, 0, 0)):
            out.append((spec["task_name"], spec["xml"]))
        return out, dict(ctx.subs())


def case_seam():
    case("C13", "THE SEAM: on an older fixture, both tools agree exactly")
    if not (ORIGINAL_SYNC.is_file() and ORIGINAL_INSTALL.is_file()):
        skip("this machine has no older layout (%s), so there is no original tool to "
             "compare the new one with" % (Path("~") / OLDER_DIRNAME))
        return
    fx = legacy_world("c13")
    backup = fx.w.parent / (fx.w.name + "-backup")
    shutil.copytree(str(fx.w), str(backup), symlinks=True)

    old = run_in(fx.legacy / "sync_original.py", fx.home, "status")
    old_push = run_in(fx.legacy / "sync_original.py", fx.home, "push")
    old_tree = git(fx.legacy, "ls-tree", "-r", "HEAD", env=fx.env)[1]

    shutil.rmtree(str(fx.w))
    shutil.copytree(str(backup), str(fx.w), symlinks=True)

    new = run_in(fx.legacy / "sync.py", fx.home, "status")
    new_push = run_in(fx.legacy / "sync.py", fx.home, "push")
    new_tree = git(fx.legacy, "ls-tree", "-r", "HEAD", env=fx.env)[1]

    # Equality is taken on the PLAN, the DRIFT BUCKETS and the commit contents
    # — never on the banner, which now carries the program's own name rather
    # than the older folder's. The page is checked all the same:
    # the only lines allowed to differ are the ones that print that name.
    a, b = normalised(old["out"]), normalised(new["out"])
    changed = [l for l in _diff(a, b) if l[:1] in "+-" and l[:3] not in ("---", "+++")]
    stray = [l for l in changed
             if OLDER_DIRNAME not in l and PROGRAM_NAME not in l]
    ok("the plan is the same, file for file and verb for verb",
       old["plan"] == new["plan"],
       sorted(set(old["plan"]) ^ set(new["plan"]))[:8])
    ok("the drift buckets are the same, bucket for bucket",
       old["buckets"] == new["buckets"],
       [k for k in set(old["buckets"]) | set(new["buckets"])
        if old["buckets"].get(k) != new["buckets"].get(k)])
    ok("the only lines of the page that differ are the ones naming the program",
       stray == [], stray[:6])
    ok("   and the name it prints now is its own",
       PROGRAM_NAME in new["out"] and OLDER_DIRNAME not in new["out"].split("\n")[0],
       new["out"].split("\n")[0])
    ok("both pushes succeeded", old_push["code"] == 0 and new_push["code"] == 0,
       (old_push["code"], new_push["code"]))
    ok("the commit carries the same files, with the same contents",
       old_tree == new_tree, "\n".join(_diff(old_tree, new_tree)[:8]))
    ok("the partition stayed off in the older layout",
       "THE HUB FOLDER, DIVIDED" not in new["out"])
    ok("and the tool said nothing extra about the layout",
       "layout    :" not in new["out"])

    # S1: a record that SAYS the older layout still is the older layout. A tool
    # that read that as a disagreement would stop the hub's own sync on a
    # machine that is exactly what it claims to be.
    shutil.rmtree(str(fx.w))
    shutil.copytree(str(backup), str(fx.w), symlinks=True)
    record = json.loads(read(fx.legacy / "machine.json"))
    record["layout"] = "legacy"
    write(fx.legacy / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    said = run_in(fx.legacy / "sync.py", fx.home, "status")
    ok("a record that says `layout: legacy` still carries the hub whole",
       said["plan"] == old["plan"],
       sorted(set(said["plan"]) ^ set(old["plan"]))[:8])
    ok("   the partition stayed off", "THE HUB FOLDER, DIVIDED" not in said["out"])
    ok("   and the hub's own entry carried its files",
       any(rel.startswith("orchestrator/") for rel, _kind in said["plan"]),
       said["plan"][:4])

    old_jobs, old_subs = render_jobs(fx.legacy / "install_original.py", fx.home, fx.hub)
    new_jobs, new_subs = render_jobs(fx.legacy / "install.py", fx.home, fx.hub)
    ok("every job renders byte for byte as the installed ones do",
       old_jobs == new_jobs,
       [name for (name, text), (n2, t2) in zip(old_jobs, new_jobs) if text != t2])
    ok("   and {syncdir} still means the folder the tool sits in",
       new_subs["{syncdir}"] == str(fx.legacy), new_subs["{syncdir}"])

    fx2 = stranger("c13-program")
    jobs2, subs2 = render_jobs(fx2.hub / "sync" / "install.py", fx2.home, fx2.hub)
    ok("in a program tree {syncdir} means <hub>/sync",
       subs2["{syncdir}"] == str(fx2.hub / "sync"), subs2["{syncdir}"])
    ok("and {brain} means the brain clone",
       subs2["{brain}"] == str(fx2.brain), subs2["{brain}"])
    ok("   so the jobs point into the program tree",
       any(str(fx2.hub / "sync") in text for _name, text in jobs2),
       [n for n, _t in jobs2])
    shutil.rmtree(str(backup), ignore_errors=True)
    return fx


def _diff(a, b):
    import difflib
    return [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(),
                                            "original", "under test", lineterm="", n=0)]


# ---------------------------------------------------------------------------
# C14 — the machine's scheduler is never reached from a temporary folder
# ---------------------------------------------------------------------------

def scheduler_shims(folder, marker):
    """Stand-ins on PATH for the commands that reach the machine's scheduler.

    Each one writes a line to the marker file if it is ever called, and answers
    0 so the installer would carry on believing it worked. If the guard fails,
    the marker is there to say so — and the real scheduler is not touched even
    then."""
    folder.mkdir(parents=True, exist_ok=True)
    made = []
    if os.name == "nt":
        # schtasks is the usual name for the scheduler; powershell is the door this
        # installer actually uses on Windows, so both are stood in for.
        for name in ("schtasks.bat", "powershell.bat", "powershell.exe.bat"):
            write(folder / name, "@echo %%* >> \"%s\"\r\n@exit /b 0\r\n" % marker)
            made.append(name)
    else:
        for name in ("launchctl",):
            path = write(folder / name,
                         "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"" + str(marker) + "\"\nexit 0\n")
            os.chmod(str(path), 0o755)
            made.append(name)
    return made


def case_temp_scheduler():
    case("C14", "THE SCHEDULER: never reached from a temporary folder")
    before = fixture_dirs()
    fx = stranger("c14")
    ok("the fixture really is under the system's temporary folder",
       str(fx.hub).startswith(str(Path(tempfile.gettempdir()).resolve())),
       (str(fx.hub), tempfile.gettempdir()))
    marker = fx.w / "the-scheduler-was-called.txt"
    shims = scheduler_shims(fx.w / "shims", marker)
    note("stood in for on PATH: %s" % ", ".join(shims))
    env = fixture_env(fx.home, EXO_INSTALL_NO_SCHEDULER=None)
    env["PATH"] = str(fx.w / "shims") + os.pathsep + env.get("PATH", "")
    ok("the testing hook is NOT set for this child",
       "EXO_INSTALL_NO_SCHEDULER" not in env)
    code, out = run_child(fx.hub / "sync" / "install.py", "--defaults",
                          "--machine", "alpha", env=env, cwd=fx.hub)
    ok("the install ran to its end", code == 0, out[-600:])
    ok("the heartbeat refused to register, and said why",
       "temporary folder" in out and "NOT handed to this machine's scheduler" in out,
       out[-600:])
    ok("   it named the way to mean it anyway",
       "EXO_INSTALL_REAL_SCHEDULER=1" in out, out[-400:])
    ok("   and nothing called the scheduler", not marker.exists(),
       read(marker) if marker.exists() else "")
    if os.name == "nt":
        note("the Windows half of this case is NOT RUN here: it needs a Windows machine.")
    else:
        agents = fx.home / "Library" / "LaunchAgents"
        written = sorted(p.name for p in agents.glob("*.plist")) if agents.is_dir() else []
        ok("the job files were still written, under the fixture's own home",
           len(written) == 4, written)
        ok("   and none of them is anywhere but the fixture",
           all(str(agents).startswith(str(fx.home)) for _ in written), str(agents))
    ok("the install still finished its other steps",
       (fx.hub / "installed.json").is_file() and "EXOCORTEX INSTALLED" in out,
       out[-300:])
    # The negative control. Without it "no marker" could mean the stand-ins
    # were never on PATH at all, and the case would prove nothing.
    if os.name == "nt":
        note("the negative control is NOT RUN on Windows: a batch file cannot "
             "stand in for a name given with its .exe, so it needs a Windows machine and "
             "a driver-level stand-in.")
    else:
        fx2 = stranger("c14-control")
        marker2 = fx2.w / "the-scheduler-was-called.txt"
        scheduler_shims(fx2.w / "shims", marker2)
        env2 = fixture_env(fx2.home, EXO_INSTALL_NO_SCHEDULER=None,
                           EXO_INSTALL_REAL_SCHEDULER="1")
        env2["PATH"] = str(fx2.w / "shims") + os.pathsep + env2.get("PATH", "")
        code, out2 = run_child(fx2.hub / "sync" / "install.py", "--defaults",
                               "--machine", "alpha", env=env2, cwd=fx2.hub)
        ok("with the override set, the installer DOES reach for the scheduler",
           marker2.is_file(), out2[-500:])
        ok("   so the stand-ins were live, and the guard is what stopped it",
           marker2.is_file() and not marker.exists())
        ok("   and even then it only ever reached the stand-in",
           "launchctl" in (read(marker2) or "") or (read(marker2) or "").strip() != "",
           read(marker2))
    spawned_case_ends(before)


# ---------------------------------------------------------------------------
# A6 — the shim's fallback: it fires in the one case it is for, and nowhere else
# ---------------------------------------------------------------------------

BROKEN = "def paths(  # a file that cannot be read as python\n"


def case_fallback():
    case("A6", "SHIM FALLBACK: one event, and never a guess anywhere else")
    before = fixture_dirs()
    fx = legacy_world("a6-legacy")
    write(fx.hub / "tools" / "exo_paths.py", BROKEN)
    code, out = run_child(fx.legacy / "sync.py", "status",
                          env=fixture_env(fx.home), cwd=fx.legacy)
    ok("an older installation keeps working when the resolver will not load",
       code == 0, out[-500:])
    ok("   and says so in one line",
       "the path resolver could not be loaded" in out, out[:400])
    ok("   the brain sync itself still ran", "DRIFT" in out, out[-300:])
    ok("   it is one line, not a wall",
       len([l for l in out.splitlines()
            if "resolver could not be loaded" in l]) == 1)

    record = json.loads(read(fx.legacy / "machine.json"))
    record["layout"] = "legacy"
    write(fx.legacy / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    code, out = run_child(fx.legacy / "sync.py", "status",
                          env=fixture_env(fx.home), cwd=fx.legacy)
    ok("a record that SAYS the older layout does not turn the fallback off",
       code == 0 and "the path resolver could not be loaded" in out,
       (code, out[-300:]))
    ok("   and the hub's own entry still synced", "DRIFT" in out, out[-300:])

    fxp = stranger("a6-program")
    write(fxp.hub / "tools" / "exo_paths.py", BROKEN)
    code, out = run_child(fxp.hub / "sync" / "sync.py", "status",
                          env=fixture_env(fxp.home), cwd=fxp.hub)
    ok("a program tree with the same failure STOPS", code != 0, (code, out[-300:]))
    ok("   in one plain sentence, with the next action",
       "no safe answer" in out and "--repair" in out, out[-400:])
    ok("   and it is one sentence, not a traceback",
       "Traceback" not in out and len(out.strip().splitlines()) == 1, out[-300:])

    # record against structure, both ways
    fxd = stranger("a6-disagree")
    record = json.loads(read(fxd.hub / "machine.json"))
    record["layout"] = "legacy"
    write(fxd.hub / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    code, out = run_child(fxd.hub / "sync" / "sync.py", "status",
                          env=fixture_env(fxd.home), cwd=fxd.hub)
    ok("a record that says one layout over a tree that is the other STOPS",
       code != 0 and "one of the two is wrong" in out, (code, out[-300:]))

    fxl = legacy_world("a6-disagree-legacy")
    record = json.loads(read(fxl.legacy / "machine.json"))
    record["layout"] = "program-tree"
    write(fxl.legacy / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    code, out = run_child(fxl.legacy / "sync.py", "status",
                          env=fixture_env(fxl.home), cwd=fxl.legacy)
    ok("and so does the same disagreement in the older layout",
       code != 0 and "one of the two is wrong" in out, (code, out[-300:]))
    ok("   with no fallback anywhere near it",
       "the path resolver could not be loaded" not in out, out[-300:])
    spawned_case_ends(before)


# ---------------------------------------------------------------------------

def guarded(run_case, *args):
    """One case never takes the run down."""
    try:
        return run_case(*args)
    except Exception as exc:
        ok("the case ran to its end", False, "%s stopped: %r" % (run_case.__name__, exc))
        import traceback
        for line in traceback.format_exc().splitlines()[-6:]:
            note(line)
        return None


CASE_LIST = (
    ("R", case_rails),
    ("C0", case_public_clone),
    ("C1", case_fresh),
    ("C2", case_partition),
    ("C3", case_activation),
    ("C4", case_never_sync),
    ("C5", case_state),
    ("C6", case_update),
    ("C7", case_nested),
    ("C8", case_recovery),
    ("C9", case_privacy),
    ("C10", case_two_machines),
    ("C11", case_brain_opener),
    ("C12", case_manifests),
    ("C13", case_seam),
    ("C14", case_temp_scheduler),
    ("A6", case_fallback),
)


def main():
    if any(a == "--public-tree" and (i + 1 == len(ARGS) or ARGS[i + 1].startswith("--"))
           or a == "--public-tree=" for i, a in enumerate(ARGS)):
        print("gate-split: --public-tree needs the exported tree's folder.")
        return 2
    if PUBLIC_TREE is not None and (not PUBLIC_TREE.is_dir() or not IMAGE.get("files")):
        print("gate-split: --public-tree does not name an exported program tree.")
        return 2
    if DEPTH > MAX_DEPTH:
        sys.stderr.write("gate-split: recursion — this run is %d gates deep and a gate "
                         "launches copies at most %d deep. Refusing to run.\n"
                         % (DEPTH, MAX_DEPTH))
        return 3
    unknown = [a for a in ARGS if a not in ("--keep", "--public-tree")
               and not a.startswith(("--only", "--public-tree="))
               and a not in (ONLY, PUBLIC_TREE_ARG)]
    if unknown:
        print("gate-split: %s is not an option this gate knows." % unknown[0])
        return 2
    if LAYOUT == "build" and IMAGE_FILE.is_file():
        for needed in (IMAGE_FILE, ORIGINAL_SYNC, ORIGINAL_INSTALL):
            if not Path(needed).is_file():
                print(shown("gate-split: %s is not here, and every case needs it." % needed))
                return 2
        if not DEV_TREE.is_dir():
            print(shown("gate-split: the dev tree is not at %s." % DEV_TREE))
            return 2
    elif not IMAGE.get("files"):
        # The one line a runner reads as "cannot run on this layout": nothing
        # else is printed, and no check is counted.
        print("gate-split.py: skipped here \u2014 this hub is not a program tree: it carries no "
              "partition rule (templates/dot-gitignore), and a program tree is what this "
              "gate proves")
        return 0

    print("gate-split — gate C: the stranger layout, from the program alone")
    if LAYOUT == "build":
        print(shown("  image    %s  (%d files)" % (IMAGE_FILE if IMAGE_FILE.is_file()
                    else PUBLIC_TREE, len(IMAGE["files"]))))
        if IMAGE_FILE.is_file():
            print(shown("  dev tree %s" % DEV_TREE))
    else:
        print(shown("  image    this hub's own program files, %s  (%d files)"
                    % (HUB, len(IMAGE["files"]))))
    print(shown("  fixtures %s" % SCRATCH))
    print(shown("  python   %s" % PY))

    started = time.time()
    for name, run_case in CASE_LIST:
        if wanted(name):
            guarded(run_case)

    print("\n===== GATE =====")
    for name in fails:
        print("  FAIL  %s" % name)
    passed = sum(1 for c in checks if c)
    print("  children started: %d" % CHILDREN)
    left = survivors(LAST_CHILD)
    print("  survivors after the last child: %s"
          % ("none" if left == [] else ("unknowable here" if left is None else left)))
    if KEEP:
        print(shown("  kept: %s" % SCRATCH))
    else:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    print("  %.1f s" % (time.time() - started))
    for line in SKIPPED:
        print(shown("  SKIP  %s" % line))
    print("%d checks · %d passed · %d failed%s" % (len(checks), passed, len(fails),
                                                  (" · %d skipped" % len(SKIPPED))
                                                  if SKIPPED else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        RESULT = main()
    finally:
        if not KEEP:
            shutil.rmtree(str(SCRATCH), ignore_errors=True)
    sys.exit(RESULT)
