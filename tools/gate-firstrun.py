#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-firstrun.py — a stranger's first run DRAWS.

    python3 tools/gate-firstrun.py            every case, from the hub folder
    python3 tools/gate-firstrun.py --keep     keep the fixture worlds
    python3 tools/gate-firstrun.py --only N3  one case (or several, comma-separated)

TWO PLACES IT RUNS FROM, told apart by what is there:
  a BUILD folder   beside IMAGE.json, the build's own list of the program's files
                   (the dev tree, scratch), with the seeds and the law book read
                   from release/src — every case runs
  an INSTALLED hub in the hub's own tools/ folder: the program is the one THIS hub
                   is — every file its partition rule (templates/dot-gitignore)
                   names back in, its seeds under templates/, its law book under
                   laws/. N6 (two builds' copies side by side), N7's comparison with
                   the older collector and N10 (a build's files and diffs) need a
                   build and SKIP, each with one
                   line; a hub that is not a program tree says so in one line and
                   counts nothing.

THE CLAIM. On an empty machine the program draws its front door — the board and
the tree, with the hub as the one green tile carrying its first prompt — gives
ONE command that makes a project, keeps a truthful ledger and mailbox on an
empty brain, reads the shipped laws on the sky's horizon without anyone's name,
and puts the law book and the skills where a session reads them. On the owner's
fleet nothing moves but two declared values.

THE CASES:
  N1  RAILS           worlds in the temp folder only; the live hub's names unchanged
  N2  EMPTY MACHINE   orchestrator.py draws with no projects (root empty, root absent)
  N3  NEW PROJECT     new-project.py: made, parsed, on the tree; every refusal changes nothing
  N4  LEDGER          no queue is "0 listed · no queue file yet"; no absolute path written
  N5  MAIL            a first letter creates INBOX.md with the seed's header, byte for byte
  N6  FLEET           older copies vs newer copies on one copy of the live hub: laws equal, pages
                      equal but for two DECLARED values; SKIPPED on a machine with no owner
  N7  LAWS HORIZON    through the import: starter laws, dated personal laws, labels
  N8  THE LAWS STEP   exocortex-laws.md on every machine; CLAUDE.md three lines when absent;
                      a CLAUDE.md of yours untouched; re-render on a new book; dry; skills
  N9  NO SCHEDULER    a whole install in a world touches no scheduler and opens no window
  N10 SCRUB           no private word, no home path, no shell string; every diff applies

RULES THIS GATE KEEPS (the memory lessons it was written from):
  * Every fixture world lives under ONE root made here by
    tempfile.mkdtemp(prefix="exo-gate-firstrun-") in the SYSTEM temp folder —
    never under the hub, whose scratch/ the brain sync carries — and is removed
    at the end of its case; the root goes at the end of the run.
  * The live hub is READ (N6 copies it once) and never written; orchestrator.py
    is never run against it; no scheduler is ever reached; no mail is sent.
  * A live folder is never asserted absent: it is snapshotted and proved
    UNCHANGED, and only names this gate's own worlds could create are compared.
  * Every child carries a mark and a depth, runs in a process group of its own,
    is ended with everything it started past its timeout, and each case ends
    with a survivors check. The gate never runs itself.
  * Nothing it prints carries a private word or this machine's home folder.

Stdlib only, Python 3.9-compatible. macOS and Windows: pathlib, argument lists,
sys.executable; the process-group calls sit in POSIX branches.
"""
import ast
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
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
IMAGE_FILE = HERE / "IMAGE.json"
if IMAGE_FILE.is_file():
    LAYOUT = "build"                             # <hub>/scratch/<build>/gate-firstrun.py
    HUB = HERE.parent.parent
    SRC = HERE                                   # where the program's files are read
    REL = HUB / "release" / "src"                # the seeds and the law book
else:
    LAYOUT = "installed"                         # <hub>/tools/gate-firstrun.py
    HUB = HERE.parent
    SRC = HUB
    REL = HUB                                    # an install keeps them in templates/, laws/
SCRATCH = HUB / "scratch"
P3 = SCRATCH / "bq045-p3"
DEV_TREE = Path(os.path.expanduser("~")) / "exocortex-dev"
SCRUB_WORDS = HUB / "release" / "SCRUB-WORDS.txt"
PY = sys.executable or "python3"
PREFIX = "exo-gate-firstrun-"

MARK = "EXO_GATE_FIRSTRUN_INNER"
DEPTH_KEY = "EXO_GATE_FIRSTRUN_DEPTH"
DEPTH = int(os.environ.get(DEPTH_KEY) or 0)
if DEPTH >= 1 or os.environ.get(MARK) == "1":
    # A child of this gate is never this gate: refuse at once, before a world
    # is made (a gate that starts itself must never run away).
    sys.stdout.write("gate-firstrun: refused — started from inside its own run (depth %d)\n"
                     % DEPTH)
    sys.exit(3)

ARGS = sys.argv[1:]
KEEP = "--keep" in ARGS
ONLY = ""
for _i, _a in enumerate(ARGS):
    if _a == "--only" and _i + 1 < len(ARGS):
        ONLY = ARGS[_i + 1]
    elif _a.startswith("--only="):
        ONLY = _a.split("=", 1)[1]

BASE_ENV = dict(os.environ)
for _k in ("EXO_REGISTRY_JSON", "COLLECT_OPENERS_OUT", "COLLECT_OPENERS_ROOT",
           "EXO_MACHINE_JSON", "ORCH_PROJECTS_ROOT", "ORCH_TAUGHT_PATH", "EXO_PULSE",
           "EXO_INSTALL_REAL_SCHEDULER", "GITHUB_TOKEN", "GH_TOKEN"):
    BASE_ENV.pop(_k, None)

REAL_HOME = str(Path(os.path.expanduser("~")).resolve())
REAL_HOME_RAW = os.path.expanduser("~")
TEMP = str(Path(tempfile.gettempdir()).resolve())

# ONE root per run, in the system temp folder. Made before anything else so the
# rails below can prove where it is.
WORLDS = Path(tempfile.mkdtemp(prefix=PREFIX)).resolve()

checks, fails = [], []
SKIPS = []
CASE = "N1"
CHILDREN = 0
CHILD_PROCS = []
OUT = []


# ---------------------------------------------------------------------------
# saying what happened — masked, folded, one line at a time
# ---------------------------------------------------------------------------

def fold(text):
    """Accents folded, so a name under a diacritic is still that name."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def private_words():
    """The words this machine keeps private: the owner's list when it is here
    (release/SCRUB-WORDS.txt), else the names the hub's own registry.json
    carries. Empty when neither names anybody."""
    try:
        raw = SCRUB_WORDS.read_text(encoding="utf-8", errors="replace")
        words = [w.strip() for w in raw.splitlines()
                 if w.strip() and not w.strip().startswith("#")]
    except OSError:
        words = []
    if words:
        return words
    try:
        reg = json.loads((HUB / "registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        reg = {}
    owner = reg.get("owner") if isinstance(reg.get("owner"), dict) else {}
    found = [owner.get("name"), owner.get("short")] + list(owner.get("aliases") or [])
    for name, block in (reg.get("machines") or {}).items():
        found.append(name)
        if isinstance(block, dict):
            found.append(block.get("label"))
    found += list((reg.get("mind_aliases") or {}).values())
    return sorted(set(w.strip() for w in found if isinstance(w, str) and len(w.strip()) > 1))


WORDS = private_words()
PATTERNS = [(w, re.compile(r"(?<![0-9A-Za-z])" + re.escape(fold(w)) + r"(?![0-9A-Za-z])",
                           re.IGNORECASE)) for w in WORDS]


def masked(word):
    """A word the gate must REPORT without SAYING: first letter and length."""
    word = str(word)
    return "%s… (%d)" % (word[:1], len(word))


def shown(text):
    """What this gate prints: the world root as <world>, the temp folder as
    <temp>, the home folder as ~, and every private word masked."""
    text = str(text)
    for real, mark in ((str(WORLDS), "<world>"), (TEMP, "<temp>"),
                       (tempfile.gettempdir(), "<temp>"),
                       (REAL_HOME, "~"), (REAL_HOME_RAW, "~")):
        if real and real != "/":
            text = text.replace(real, mark)
    folded = fold(text)
    for word, pattern in PATTERNS:
        if pattern.search(folded):
            text = pattern.sub(masked(word), folded)
            folded = text
    return text


def say(text=""):
    line = shown(text)
    OUT.append(line)
    try:
        sys.stdout.write(line + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(line.encode("ascii", "replace").decode("ascii") + "\n")
    sys.stdout.flush()


def case(name, title):
    global CASE
    CASE = name
    say("")
    say("%s  %s" % (name, title))


def check(ok, what, detail=""):
    checks.append((CASE, what, bool(ok)))
    say("  %s %s" % ("ok  " if ok else "FAIL", what))
    if not ok:
        fails.append((CASE, what, detail))
        if detail not in ("", None):
            say("        %s" % " ".join(str(detail).split())[:500])
    return bool(ok)


def note(text):
    say("  ..   %s" % " ".join(str(text).split())[:400])


def skip(text):
    """What this machine cannot answer, said in one line and counted."""
    SKIPS.append("%s · %s" % (CASE, text))
    note("skipped: " + text)


def wanted(name):
    if not ONLY:
        return True
    return name.upper() in [w.strip().upper() for w in ONLY.split(",")]


# ---------------------------------------------------------------------------
# children: marked, bounded, grouped, never left behind
# ---------------------------------------------------------------------------

def run_child(argv, env=None, cwd=None, timeout=300):
    """(exit code, output) of one child. argv[0] is a script run by this same
    interpreter unless it is an executable name the caller means (git)."""
    global CHILDREN
    env = dict(env or BASE_ENV)
    env[MARK] = "1"
    env[DEPTH_KEY] = str(DEPTH + 1)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    first = str(argv[0])
    cmd = ([PY] if first.endswith(".py") else []) + [str(a) for a in argv]
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        group["start_new_session"] = True
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=env, cwd=(str(cwd) if cwd else None), **group)
    CHILD_PROCS.append(proc)
    CHILDREN += 1
    try:
        out, _err = proc.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        end_child(proc)
        out, _err = proc.communicate()
        out = (out or b"") + ("\ngate-firstrun: the child ran past %d s and was ended "
                              "with everything it started" % timeout).encode("utf-8")
    return proc.returncode, (out or b"").decode("utf-8", "replace").strip()


def end_child(proc):
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def survivors():
    """Every process still alive that THIS gate started: the child itself and,
    on POSIX, anything left in the group it was given. Counted from the gate's
    own list, never from a search of the machine."""
    left = []
    for proc in CHILD_PROCS:
        if proc.poll() is None:
            left.append("%d (still running)" % proc.pid)
            continue
        if os.name != "nt":
            try:
                os.killpg(proc.pid, 0)
            except OSError:
                continue
            left.append("%d (its group is not empty)" % proc.pid)
    return left


def case_ends(w=None):
    left = survivors()
    for one in left:
        pid = int(one.split()[0])
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            try:
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                pass
    check(not left, "strays 0 (%d child process%s started so far)"
          % (CHILDREN, "" if CHILDREN == 1 else "es"), left)
    if w is not None and not KEEP:
        shutil.rmtree(str(w), ignore_errors=True)
        check(not w.exists(), "this case's world is gone")


# ---------------------------------------------------------------------------
# files, snapshots
# ---------------------------------------------------------------------------

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


def sha_of(path):
    h = hashlib.sha256()
    with io.open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root):
    """{relative path: sha, or 'dir'} for everything under a folder — how a
    folder is proved exactly what it was."""
    root = Path(root)
    out = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if "/.git/" in "/" + rel + "/" and not rel.endswith("/.git"):
            continue
        try:
            out[rel] = "dir" if path.is_dir() else sha_of(path)
        except OSError:
            out[rel] = "unreadable"
    return out


def state_of_name(path):
    """A named path's state, for the live-name comparison: absent, a folder's
    listing, or a file's sha."""
    path = Path(path)
    try:
        if not path.exists():
            return "absent"
        if path.is_dir():
            return "dir:" + hashlib.sha256(json.dumps(snapshot(path), sort_keys=True)
                                           .encode("utf-8")).hexdigest()
        return "file:" + sha_of(path)
    except OSError as exc:
        return "unreadable:%s" % exc


# ---------------------------------------------------------------------------
# the fixture world — the image, the seeds, the law book, a stranger's record
# ---------------------------------------------------------------------------

def installed_image():
    """The image of the program THIS hub is: every file its own partition rule
    (templates/dot-gitignore, installed as .gitignore) names back in, read from
    the hub itself, and the two dot-files as renders. {} when the hub carries no
    such rule — it is not a program tree."""
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


IMAGE = json.loads(read(IMAGE_FILE) or "{}") if LAYOUT == "build" else installed_image()


def image_source(spec):
    """Where one line of the image reads from. Read-only, always."""
    if spec.startswith("dev:"):
        return DEV_TREE / spec[4:]
    if spec.startswith("scratch:"):
        return SCRATCH / spec[8:]
    return HUB / spec


def world(name):
    w = WORLDS / name
    if w.exists():
        shutil.rmtree(str(w), ignore_errors=True)
    (w / "home").mkdir(parents=True)
    return w


def fixture_env(home, hub=None, **extra):
    env = dict(BASE_ENV)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "exocortex gate"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "gate@example.invalid"
    env["ORCHSYNC_SETTLE"] = "0"
    # launchd and Task Scheduler are the MACHINE's, never a fixture's.
    env["EXO_INSTALL_NO_SCHEDULER"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if hub is not None:
        env["EXO_MACHINE_JSON"] = str(Path(hub) / "machine.json")
    for key, value in extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = str(value)
    return env


def git(cwd, *args, env=None):
    proc = subprocess.run(["git", "-c", "init.defaultBranch=main", "-C", str(cwd)]
                          + [str(a) for a in args], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=env or fixture_env(Path(cwd)),
                          universal_newlines=True, timeout=120)
    return proc.returncode, (proc.stdout or "").strip()


class Fx(object):
    def __init__(self, w, home, hub, env):
        self.w, self.home, self.hub, self.env = w, home, hub, env
        self.projects = home / "Projects"


def build_program(hub):
    """The program tree: the image file for file, the two renders, then the
    seeds and the law book and skills from release/src (read-only) — nothing
    the stranger would not have."""
    hub = Path(hub)
    for row in IMAGE["files"]:
        target = hub / Path(*row["to"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(image_source(row["from"])), str(target))
    for row in IMAGE["renders"]:
        shutil.copyfile(str(hub / Path(*row["from"].split("/"))),
                        str(hub / Path(*row["to"].split("/"))))
    for source in sorted((REL / "templates").rglob("*")):
        if source.is_file():
            target = hub / "templates" / source.relative_to(REL / "templates")
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(source), str(target))
    for source in sorted((REL / "laws").rglob("*")):
        if source.is_file():
            target = hub / "laws" / source.relative_to(REL / "laws")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(source), str(target))


def stranger(name, seeds=True, projects=True, commit=True):
    """A stranger's machine: a program tree committed as a checkout, a record
    in the hub's own machine.json only (the program-tree road — no older-layout
    folder anywhere), an empty projects root, and the seed walk run by the
    installer itself."""
    w = world(name)
    home = w / "home"
    hub = home / "Exocortex"
    build_program(hub)
    record = {"name": "north", "os": "gate fixture", "layout": "program-tree",
              "partition": "git-ignore",
              "roots": {"home": str(home), "claude": str(home / ".claude"),
                        "codex": str(home / ".codex"), "projects": str(home / "Projects"),
                        "orchestrator": str(hub)}}
    write(hub / "machine.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    if projects:
        (home / "Projects").mkdir(parents=True, exist_ok=True)
    env = fixture_env(home, hub)
    if commit:
        git(hub, "init", "-q", env=env)
        git(hub, "add", "-A", env=env)
        git(hub, "commit", "-q", "-m", "the program, at this version", env=env)
    fx = Fx(w, home, hub, env)
    if seeds:
        code, out = run_child([hub / "sync" / "install.py", "--defaults", "--machine",
                               "north", "--only", "seeds"], env=env, cwd=hub)
        if code != 0:
            note("the seed walk did not finish: %s" % out[-200:])
    return fx


def tool(fx, name):
    return fx.hub / "tools" / name


def collect_json(fx):
    code, out = run_child([tool(fx, "collect-openers.py"), "--json"], env=fx.env, cwd=fx.hub)
    try:
        return json.loads(out)
    except ValueError:
        return {"rows": [], "_error": out[-300:]}


def tiles(html):
    return len(re.findall(r'<div class="tile[ "]', html or ""))


# A project's FACE on the tree: a head in the crown (a project with work in the
# window) or a tile (the hub's own, a dormant project), read from the collector's
# own markup: the state word (`<span class="st">ready</span>` on a tile, `<span
# class="sx" title="ready …">ready</span>` on a head) and the one-click start,
# face_launch's `<a class="launch" …>▶ Launch</a>` or `▶ Open` (a head's carries
# data-g="▶"), or a head's fallback `<span class="pr" …>▶</span>`.
FACE = re.compile(r'<div class="(?:tile|ph)[ "]')
READY_FACE = re.compile(r'<span class="st">ready</span>'
                        r'|<span class="sx" title="ready[^"]*">ready</span>')
LAUNCH_FACE = re.compile(r'<a class="launch" href="[^"]+"(?: data-g="▶")? title="[^"]*">'
                         r'▶ (?:Launch|Open)</a>'
                         r'|<span class="pr" title="open the startup prompt">▶</span>')


def faces(html):
    return len(FACE.findall(html or ""))


def face_of(html, key):
    """One project's face, from its data-key to the end of its own element."""
    html = html or ""
    at = html.find('data-key="%s"' % key)
    return html[at:html.find("</div>", at)] if at >= 0 else ""


def face_ok(face):
    """The face reads ready and carries the ▶ start, both inside its own element —
    never a ▶ somewhere else on the page."""
    return bool(READY_FACE.search(face or "")) and bool(LAUNCH_FACE.search(face or ""))


def interpreter_word():
    name = Path(PY).name
    return name[:-4] if name.lower().endswith(".exe") else name


def load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class in_fixture(object):
    """Load a tool IN THIS PROCESS as if this machine were the fixture's: its
    home, its record, standing in its hub, its hub and tools first on the import
    path. Everything is put back afterwards — the environment, the folder, the
    path, and every module the load brought in, so no later case reuses one."""

    def __init__(self, fx):
        self.fx = fx

    def __enter__(self):
        self.saved = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE",
                                                     "EXO_MACHINE_JSON")}
        self.cwd = os.getcwd()
        self.before = set(sys.modules)
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(self.fx.home)
        os.environ["EXO_MACHINE_JSON"] = str(self.fx.hub / "machine.json")
        os.chdir(str(self.fx.hub))
        sys.path.insert(0, str(self.fx.hub))
        sys.path.insert(1, str(self.fx.hub / "tools"))
        return self

    def __exit__(self, *exc):
        for entry in (str(self.fx.hub), str(self.fx.hub / "tools")):
            while entry in sys.path:
                sys.path.remove(entry)
        for name in list(sys.modules):
            if name not in self.before:
                sys.modules.pop(name, None)
        os.chdir(self.cwd)
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return False


# ---------------------------------------------------------------------------
# N1 — rails
# ---------------------------------------------------------------------------

def live_projects_root():
    try:
        record = json.loads((Path(REAL_HOME_RAW) / "orchestrator-sync" / "machine.json")
                            .read_text(encoding="utf-8"))
        value = (record.get("roots") or {}).get("projects")
        if value:
            return Path(value)
    except (OSError, ValueError):
        pass
    return Path(REAL_HOME_RAW) / "Projects"


# The project names N3 makes in its worlds; the live projects root is compared
# on exactly these names and on nothing else.
N3_NAMES = ("alpha", "beta", "gamma", "gamma-kept", "delta", "epsilon", "existing",
            "drytest", "rooted", "Tools", "tools")


def live_names():
    """Every live path this gate's worlds could also create, with its state.
    Nothing else in the live hub is compared: the heartbeat and the owner's
    sessions write the rest of it while a gate runs."""
    names = {}
    for rel in ("installed.json", "laws"):
        names["hub:" + rel] = state_of_name(HUB / rel)
    for path in sorted(HUB.glob("paths-ack-*")):
        names["hub:" + path.name] = state_of_name(path)
    claude = Path(REAL_HOME_RAW) / ".claude"
    names["claude:exocortex-laws.md"] = state_of_name(claude / "exocortex-laws.md")
    names["claude:CLAUDE.md"] = state_of_name(claude / "CLAUDE.md")
    for skill in ("focus", "sweep-sessions", "sync"):
        names["claude:skills/" + skill] = state_of_name(claude / "skills" / skill)
    projects = live_projects_root()
    for name in N3_NAMES:
        names["projects:" + name] = state_of_name(projects / name)
    return names


LIVE_AT_START = {}


def other_roots():
    found = []
    try:
        for path in sorted(Path(TEMP).glob(PREFIX + "*")):
            if path.is_dir() and path.resolve() != WORLDS:
                found.append(path)
    except OSError:
        pass
    return found


def case_rails():
    case("N1", "RAILS: worlds in the temp folder only, the live hub's names unchanged")
    check(WORLDS.parent == Path(TEMP), "the world root is in the system temp folder",
          shown(WORLDS))
    check(HUB.resolve() not in WORLDS.parents and WORLDS != HUB.resolve(),
          "the world root is NOT under the hub, so no brain push can carry it")
    check(sorted(p.name for p in WORLDS.iterdir()) == [],
          "this run's root was made by this run and is empty")
    strays = other_roots()
    for path in strays:
        shutil.rmtree(str(path), ignore_errors=True)
    check(strays == [], "no root of an earlier run is left in the temp folder",
          "found and removed: %s" % [p.name for p in strays])
    if LAYOUT == "build":
        check(bool(IMAGE.get("files")) and IMAGE.get("version") == 3,
              "IMAGE.json is version 3 and names its files (%d)" % len(IMAGE.get("files") or []))
    else:
        check(bool(IMAGE.get("files")),
              "this hub's own program is readable as the image (%d files)"
              % len(IMAGE.get("files") or []))
    missing = [row["from"] for row in IMAGE.get("files") or []
               if not image_source(row["from"]).is_file()]
    check(missing == [], "every file the image names is there, read-only", missing)
    if LAYOUT == "build":
        check(DEV_TREE.is_dir(), "the dev tree is readable", shown(DEV_TREE))
    check((REL / "templates" / "STATUS.md").is_file() and (REL / "laws" / "LAWS.md").is_file(),
          "P4's seeds and P6's law book are where the brief says"
          if LAYOUT == "build" else
          "P4's seeds and P6's law book are where an install keeps them (templates/, laws/)")
    if LAYOUT == "installed" and not WORDS:
        skip("no private word is known on this machine — no release/SCRUB-WORDS.txt and a "
             "registry.json that names nobody — so the word checks have nothing to look for")
    else:
        check(bool(WORDS), "the private word list was read (%d words)" % len(WORDS))
    LIVE_AT_START.update(live_names())
    note("the live names compared at the end: %d (installed.json, laws/, paths-ack-*, "
         "the claude root's CLAUDE.md, exocortex-laws.md and three skills, and %d "
         "project names)" % (len(LIVE_AT_START), len(N3_NAMES)))


# ---------------------------------------------------------------------------
# N2 — an empty machine draws
# ---------------------------------------------------------------------------

def console_line(root):
    return ("No projects yet in %s — %s tools/new-project.py <name> makes one · "
            "board and tree drawn." % (root, interpreter_word()))


def case_empty():
    case("N2", "EMPTY MACHINE: the board and the tree draw with no projects")
    fx = stranger("n2")
    check((fx.hub / "OPENER.md").is_file() and (fx.hub / "STATUS.md").is_file(),
          "the seed walk landed the hub's STATUS.md and its first OPENER.md")
    installed = json.loads(read(fx.hub / "installed.json") or "{}")
    check("OPENER.md" in (installed.get("seeded") or []),
          "and recorded OPENER.md as a seed in installed.json")
    check(sorted(p.name for p in fx.projects.iterdir()) == [], "the projects root is empty")
    code, out = run_child([fx.hub / "orchestrator.py"], env=fx.env, cwd=fx.hub)
    check(code == 0, "orchestrator.py exits 0 on a machine with no projects", out[-300:])
    for name in ("board.html", "tree.html", "GETTING-GOING.md", "improvements.html"):
        check((fx.hub / name).is_file(), "it wrote %s" % name)
    check(console_line(fx.projects) in out, "it says the one move in the one console line",
          out[-300:])
    board = read(fx.hub / "board.html") or ""
    check("tools/new-project.py &lt;name&gt;" in board and interpreter_word() in board
          and str(fx.projects) in board,
          "the board carries the one-move line: the root, the interpreter, the command")
    check("hub folder&#x27;s own state file" in board or "hub folder's own state file" in board,
          "the board carries the hub's own ## Now paragraph as its one card")
    check("Everything else" not in board and "Focus" not in board,
          "and nothing else: no empty Focus, Active or Everything-else section")
    data = collect_json(fx)
    rows = data.get("rows") or []
    check(len(rows) == 1 and rows[0].get("is_hub"),
          "the tree has exactly ONE lane, the hub (%d)" % len(rows), data.get("_error", ""))
    row = rows[0] if rows else {}
    check(row.get("state") == "green", "its state is green (%s: %s)"
          % (row.get("state"), row.get("state_words")))
    check(row.get("fresh") == "fresh", "its seeded opener reads FRESH (%s %s)"
          % (row.get("fresh"), row.get("notes")))
    check(row.get("opener") == "OPENER.md" and bool(row.get("body")),
          "it carries the seeded opener and its prompt")
    check((row.get("written") or "") == "at install", "the row says written: at install")
    code, out = run_child([tool(fx, "collect-openers.py"), "--expand", "hub"], env=fx.env,
                          cwd=fx.hub)
    check(code == 0 and "source: folder · written at install" in out,
          "the card says `written at install` right above the prompt", out[-300:])
    check(row.get("on") == "north" and 'THIS MACHINE' not in (read(fx.hub / "tree.html") or "")
          and ">NORTH<" in (read(fx.hub / "tree.html") or ""),
          "`on: here` reads as this machine's own name from its record (%s), never "
          "\"THIS MACHINE\"" % row.get("on"))
    check(not (fx.hub / "skills").exists(), "the seed walk put no skills/ in the hub")
    check(row.get("model") == "any · default" and not re.search(r'data-mind="ANY"',
                                                                  read(fx.hub / "tree.html") or ""),
          "a model line of `any` draws no mind root")
    tree = read(fx.hub / "tree.html") or ""
    check(tiles(tree) == 1, "tree.html draws exactly one tile (%d)" % tiles(tree))
    check("▶ prompt" in tree, "the tile carries the ▶ prompt")
    at = tree.find('<div class="tile ')
    tile = tree[at:tree.find("</span></span></div>", at) + 20] if at >= 0 else ""
    check(bool(tile) and 'class="st">ready<' in tile and "stale" not in tile.lower()
          and "idle" not in tile.lower(),
          "the tile says ready, and no word on it says stale or idle")
    note("the tile's own age marks read: %s" % (re.findall(r'class="ages">([^<]*)<', tree)[:1]))

    # `status_updated: at install` is the opener file's own mtime, with one
    # install's window: a STATUS written by the same seed walk is not a change,
    # and one written later — the person's own first ## Now — is said so.
    opener_m = (fx.hub / "OPENER.md").stat().st_mtime
    os.utime(str(fx.hub / "STATUS.md"), (opener_m + 1, opener_m + 1))
    row = (collect_json(fx).get("rows") or [{}])[0]
    check(row.get("fresh") == "fresh", "a STATUS.md written a second after the seeded "
          "opener, by the same walk, keeps it FRESH (%s)" % row.get("fresh"))
    os.utime(str(fx.hub / "STATUS.md"), (opener_m + 3600, opener_m + 3600))
    row = (collect_json(fx).get("rows") or [{}])[0]
    check(row.get("fresh") == "note" and "STATUS changed since the opener" in
          (row.get("notes") or []) and row.get("state") == "green",
          "one written an hour later is a NOTE — said, still green (%s %s)"
          % (row.get("fresh"), row.get("state")))
    os.utime(str(fx.hub / "STATUS.md"), (opener_m, opener_m))

    # a hub that is not a repository at all: the fall has no weeks to draw
    fx3 = stranger("n2-norepo", commit=False)
    code, out = run_child([fx3.hub / "orchestrator.py"], env=fx3.env, cwd=fx3.hub)
    check(code == 0 and tiles(read(fx3.hub / "tree.html") or "") == 1,
          "a hub that is no repository (the fall has no weeks) still draws its one tile",
          out[-300:])
    case_ends(fx3.w)

    # the projects root ABSENT
    fx2 = stranger("n2-absent", projects=False)
    check(not fx2.projects.exists(), "a second world with NO projects root at all")
    code, out = run_child([fx2.hub / "orchestrator.py"], env=fx2.env, cwd=fx2.hub)
    check(code == 0 and console_line(fx2.projects) in out,
          "orchestrator.py exits 0 and says the one move there too", out[-300:])
    check((fx2.hub / "board.html").is_file() and (fx2.hub / "tree.html").is_file()
          and (fx2.hub / "GETTING-GOING.md").is_file(), "and draws the same three files")
    check(not fx2.projects.exists(), "drawing did not make the projects root")

    # the v2 skin prints its line and writes nothing new
    before = snapshot(fx.hub)
    code, out = run_child([fx.hub / "orchestrator.py", "--skin", "v2"], env=fx.env, cwd=fx.hub)
    check(code == 0 and "retired" in out, "--skin v2 prints its one line and exits 0",
          out[-200:])
    check(snapshot(fx.hub) == before, "and writes nothing")

    # the installer's own tree step: drawn, never opened from the temp folder
    marker = fx.w / "a-window-was-opened.txt"
    shims = opener_shims(fx.w / "shims", marker)
    env = dict(fx.env)
    env["PATH"] = str(fx.w / "shims") + os.pathsep + env.get("PATH", "")
    if shims:
        found = shutil.which(shims[0].split(".")[0], path=env["PATH"])
        check(found is not None and Path(found).parent == fx.w / "shims",
              "the stand-in for the page opener is the one PATH finds")
    code, out = run_child([fx.hub / "sync" / "install.py", "--defaults", "--machine",
                           "north", "--only", "tree"], env=env, cwd=fx.hub)
    check(code == 0 and "OK tree (drawn, not opened)" in out,
          "install.py's tree step draws the page and says it did not open it", out[-400:])
    check("temporary folder" in out, "   and says why, in one line")
    check(not marker.exists(), "   and nothing opened a window", read(marker))
    case_ends(fx.w)
    case_ends(fx2.w)


def opener_shims(folder, marker):
    """Stand-ins on PATH for what opens a page (and the scheduler, N9). Each
    writes a line to the marker if called and answers 0."""
    folder.mkdir(parents=True, exist_ok=True)
    made = []
    if os.name == "nt":
        for name in ("powershell.exe.bat", "powershell.bat", "schtasks.bat"):
            write(folder / name, "@echo %%* >> \"%s\"\r\n@exit /b 0\r\n" % marker)
            made.append(name)
    else:
        for name in ("open", "launchctl"):
            path = write(folder / name,
                         "#!/bin/sh\nprintf '%s %%s\\n' \"$*\" >> \"%s\"\nexit 0\n"
                         % (name, marker))
            os.chmod(str(path), 0o755)
            made.append(name)
    return made


# ---------------------------------------------------------------------------
# N3 — the new-project command
# ---------------------------------------------------------------------------

def case_new_project():
    case("N3", "NEW PROJECT: one command, a project the board and the tree can see")
    fx = stranger("n3")
    code, out = run_child([tool(fx, "new-project.py"), "alpha"], env=fx.env, cwd=fx.hub)
    folder = fx.projects / "alpha"
    check(code == 0, "new-project.py alpha exits 0", out[-400:])
    check(folder.is_dir() and (folder / "STATUS.md").is_file(),
          "it made the folder and its STATUS.md, under the root the record names")
    status_text = read(folder / "STATUS.md") or ""
    with in_fixture(fx):
        parsed = load(fx.hub / "orchestrator.py", "orch_n3").parse_status(
            status_text.splitlines())
    check(bool(parsed.get("now")) and len(parsed.get("todos") or []) == 1
          and bool(parsed.get("important")),
          "the board's own read_status parses its three sections (now · 1 to-do · important)")
    lines = out.splitlines()
    check(str(folder) in [l.strip() for l in lines] and str(folder) == lines[-2].strip(),
          "it prints the folder's full path ALONE on its own line")
    check(lines[-1].strip() == "Open a session in that folder.", "then the one next sentence")
    road = [l for l in lines if l.strip().startswith("git ")]
    note("the git road it printed: %s" % (road[0].strip()[3:].strip() if road else "none"))
    if shutil.which("git"):
        code_g, log = git(folder, "log", "--format=%s", env=fx.env)
        check('a new repository, first commit "new project: alpha"' in out
              and code_g == 0 and log == "new project: alpha",
              "git on PATH: the road printed is the road taken — one commit, its subject")
    else:
        check("not on this machine's PATH" in out, "no git on PATH: said so in one line")
    check("board and tree redrawn — alpha is on the tree" in out,
          "it redrew the board and the tree, and checked the tile is there")
    data = collect_json(fx)
    lanes = sorted(r.get("project") for r in data.get("rows") or [])
    check(len(data.get("rows") or []) == 2 and "alpha" in lanes,
          "the tree now has two tiles: the hub and alpha (%s)" % lanes)
    check(faces(read(fx.hub / "tree.html") or "") == 2, "tree.html draws the two tiles")
    check("alpha" in (read(fx.hub / "board.html") or ""), "the board names alpha")
    alpha = [r for r in data.get("rows") or [] if r.get("project") == "alpha"]
    arow = alpha[0] if alpha else {}
    check(arow.get("opener") == "OPENER.md" and arow.get("state") == "green"
          and arow.get("fresh") == "fresh" and "no opener written" not in
          (arow.get("state_words") or ""),
          "alpha's tile: its own first OPENER.md, green, FRESH — not amber (%s · %s · %s)"
          % (arow.get("state"), arow.get("fresh"), arow.get("state_words")))
    tree_now = read(fx.hub / "tree.html") or ""
    face = face_of(tree_now, "alpha")
    check(bool((arow.get("card") or {}).get("handed")) and bool(arow.get("body"))
          and face_ok(face),
          "   its tile reads ready and carries ▶, and its card hands over its own prompt")
    check(face_ok(face) and not face_ok(LAUNCH_FACE.sub("", face))
          and not face_ok(READY_FACE.sub("", face)),
          "   control: the same reading fails that face once its ▶ start, or its ready, is taken out")
    opener_text = read(folder / "OPENER.md") or ""
    header = dict(l.split(": ", 1) for l in opener_text.split("\n---\n")[0].splitlines()
                  if ": " in l)
    check(header.get("lane") == "alpha" and header.get("by") == "new-project.py"
          and header.get("on") == "north" and header.get("next") == "machine"
          and header.get("head", "").startswith("none")
          and header.get("open_in") == "%s · a fresh session titled ACT — alpha: first "
          "session" % folder and header.get("written") == header.get("status_updated"),
          "the opener's header carries real values: lane, by, on (the record's name), "
          "head none, open_in the folder and its ACT title")
    if shutil.which("git"):
        code_g, files = git(folder, "ls-files", env=fx.env)
        check(sorted(files.split()) == ["OPENER.md", "STATUS.md"],
              "   and the first commit holds STATUS.md and OPENER.md together")
    np_src = read(SRC / "tools" / "new-project.py") or ""
    inst_src = read(SRC / "sync" / "install.py") or ""

    def reserved_in(src):
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and any(getattr(x, "id", None) == "RESERVED_FOLDERS"
                                                    for x in node.targets):
                return tuple(ast.literal_eval(node.value))
        return None
    check(reserved_in(np_src) is not None and reserved_in(np_src) == reserved_in(inst_src),
          "new-project.py's RESERVED_FOLDERS equals install.py's, name for name (%d)"
          % len(reserved_in(np_src) or ()))
    check("install.py" not in re.sub(r"#.*|\"\"\"[\s\S]*?\"\"\"", "", np_src),
          "   and the tool reads no sync package to know them")
    home_hits = [p for p in (str(fx.home), REAL_HOME) if p in status_text]
    check(not home_hits and "/Users/" not in status_text and ":\\" not in status_text,
          "STATUS.md names no home folder")
    check(not [w for w, p in PATTERNS if p.search(fold(status_text))],
          "STATUS.md carries no private word")

    whole = snapshot(fx.home)
    code, out = run_child([tool(fx, "new-project.py"), "alpha"], env=fx.env, cwd=fx.hub)
    check(code == 1 and "already a project; nothing changed" in out,
          "a second run refuses: already a project", out[-200:])
    check(snapshot(fx.home) == whole, "   and the world is byte for byte what it was")
    for bad in ("../x", "a/b", ".hidden", "tools", "Tools", "", "x.", "CON", "a b"):
        code, out = run_child([tool(fx, "new-project.py"), bad], env=fx.env, cwd=fx.hub)
        check(code == 1 and out.count("\n") == 0 and "nothing changed" in out,
              "%r is refused in one sentence" % bad, out[-200:])
    check(snapshot(fx.home) == whole, "   and after every refusal the world is unchanged")

    existing = fx.projects / "existing"
    write(existing / "notes.txt", "a folder of the user's\n")
    code, out = run_child([tool(fx, "new-project.py"), "existing"], env=fx.env, cwd=fx.hub)
    check(code == 0 and "gained these two files alone" in out,
          "a folder already there WITHOUT a STATUS.md: it says so", out[-300:])
    check(sorted(p.name for p in existing.iterdir()) == ["OPENER.md", "STATUS.md", "notes.txt"],
          "   and gains STATUS.md and OPENER.md and nothing else — no repository",
          sorted(p.name for p in existing.iterdir()))
    kept = fx.projects / "gamma-kept"
    mine = write(kept / "OPENER.md", "lane: mine\n---\nmy own opener\n")
    code, out = run_child([tool(fx, "new-project.py"), "gamma-kept"], env=fx.env, cwd=fx.hub)
    check(code == 0 and read(mine) == "lane: mine\n---\nmy own opener\n"
          and "OPENER.md was already here and is left as it is" in out,
          "an OPENER.md already in the folder is left as it is, and said", out[-300:])
    write(fx.projects / "delta" / "STATUS.md", "# mine\n")
    delta = snapshot(fx.projects / "delta")
    code, out = run_child([tool(fx, "new-project.py"), "delta"], env=fx.env, cwd=fx.hub)
    check(code == 1 and "already a project" in out and snapshot(fx.projects / "delta") == delta,
          "a folder that already has a STATUS.md is refused, untouched")

    nogit = fx.w / "no-git-here"
    nogit.mkdir()
    env = dict(fx.env)
    env["PATH"] = str(nogit)
    code, out = run_child([tool(fx, "new-project.py"), "epsilon"], env=env, cwd=fx.hub)
    check(code == 0 and "not on this machine's PATH — no repository was made" in out
          and (fx.projects / "epsilon" / "STATUS.md").is_file()
          and sorted(p.name for p in (fx.projects / "epsilon").iterdir())
          == ["OPENER.md", "STATUS.md"],
          "no git on PATH: the project is made, and one plain line says so", out[-300:])
    code, out = run_child([tool(fx, "new-project.py"), "beta", "--no-git"], env=fx.env,
                          cwd=fx.hub)
    beta = fx.projects / "beta"
    check(code == 0 and (beta / "STATUS.md").is_file()
          and sorted(p.name for p in beta.iterdir()) == ["OPENER.md", "STATUS.md"]
          and "skipped (--no-git)" in out, "--no-git makes the project with no repository",
          out[-300:])

    whole = snapshot(fx.home)
    code, out = run_child([tool(fx, "new-project.py"), "drytest", "--dry"], env=fx.env,
                          cwd=fx.hub)
    check(code == 0 and "dry run" in out and "STATUS.md" in out and "OPENER.md" in out
          and out.count("would write") == 2,
          "--dry says what it would do, naming both files", out[-300:])
    check(snapshot(fx.home) == whole and not (fx.projects / "drytest").exists(),
          "   and writes nothing")

    elsewhere = fx.w / "elsewhere"
    code, out = run_child([tool(fx, "new-project.py"), "rooted", "--root", elsewhere],
                          env=fx.env, cwd=fx.hub)
    check((elsewhere / "rooted" / "STATUS.md").is_file()
          and "made         the projects root" in out,
          "--root makes the project (and the root) under the folder it names", out[-300:])
    check(code == 1 and "is not on it" in out,
          "   and says plainly the tree lists another root, so the tile is not there",
          out[-300:])

    # A stranger's projects root that does not exist yet is made on the first run.
    fx2 = stranger("n3-noroot", projects=False)
    code, out = run_child([tool(fx2, "new-project.py"), "gamma"], env=fx2.env, cwd=fx2.hub)
    check(code == 0 and (fx2.projects / "gamma" / "STATUS.md").is_file()
          and "made         the projects root" in out,
          "a projects root that is not there yet is made, and it says so", out[-300:])
    case_ends(fx.w)
    case_ends(fx2.w)


# ---------------------------------------------------------------------------
# N4 — the ledger on an empty brain
# ---------------------------------------------------------------------------

def case_ledger():
    case("N4", "LEDGER: truthful on an empty brain, and no absolute path written")
    fx = stranger("n4")
    queue = fx.hub / "design" / "BUILD-QUEUE.md"
    seeded = read(queue)
    queue.unlink()
    code, out = run_child([tool(fx, "improvements.py"), "--count"], env=fx.env, cwd=fx.hub)
    check(code == 0 and out.strip() == "improvements: 0 listed · no queue file yet",
          "no queue: --count says `0 listed · no queue file yet`, exit 0", out[-200:])
    code, out = run_child([tool(fx, "improvements.py"), "--write"], env=fx.env, cwd=fx.hub)
    page = read(fx.hub / "improvements.html") or ""
    check(code == 0 and "0 listed · no queue file yet" in page,
          "no queue: --write draws the page with that line", out[-200:])
    check("design/BUILD-QUEUE.md is not there yet" in page,
          "   and its footer says the file is not there yet")
    write(queue, seeded)
    code, out = run_child([tool(fx, "improvements.py"), "--count"], env=fx.env, cwd=fx.hub)
    check(code == 0 and out.startswith("improvements: 0 listed ·") and "no queue" not in out,
          "the seeded queue (zero rows): `0 listed`", out[-200:])
    code, out = run_child([tool(fx, "improvements.py"), "--write"], env=fx.env, cwd=fx.hub)
    page = read(fx.hub / "improvements.html") or ""
    state = read(fx.hub / "improvements-state.json") or ""
    for label, text in (("improvements.html", page), ("improvements-state.json", state)):
        check(str(fx.home) not in text and str(fx.home.resolve()) not in text,
              "%s carries no absolute path of the world's home" % label)
    check('"queue": "design/BUILD-QUEUE.md"' in state and "read from design/BUILD-QUEUE.md" in page,
          "both name the queue hub-relative")
    outside = fx.w / "elsewhere" / "Q.md"
    write(outside, seeded)
    code, out = run_child([tool(fx, "improvements.py"), "--write", "--queue", outside],
                          env=fx.env, cwd=fx.hub)
    state = json.loads(read(fx.hub / "improvements-state.json") or "{}")
    check(code == 0 and state.get("queue") == str(outside),
          "--queue outside the hub is written exactly as given")
    inside = fx.hub / "design" / "BUILD-QUEUE.md"
    code, out = run_child([tool(fx, "improvements.py"), "--write", "--queue", inside],
                          env=fx.env, cwd=fx.hub)
    state = json.loads(read(fx.hub / "improvements-state.json") or "{}")
    check(code == 0 and state.get("queue") == "design/BUILD-QUEUE.md",
          "--queue under the hub, given absolute, is written hub-relative")
    if os.name != "nt":
        queue.chmod(0)
        code, out = run_child([tool(fx, "improvements.py"), "--count"], env=fx.env, cwd=fx.hub)
        queue.chmod(0o644)
        check(code == 1 and "could not be read" in out,
              "a queue that is there but unreadable is NOT called empty", out[-200:])
    case_ends(fx.w)


# ---------------------------------------------------------------------------
# N5 — mail's first letter
# ---------------------------------------------------------------------------

def mail_seed_constant(path):
    tree = ast.parse(read(path) or "")
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "INBOX_SEED"
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def case_mail():
    case("N5", "MAIL: the first letter creates INBOX.md with the seed's header")
    fx = stranger("n5")
    seed = fx.hub / "templates" / "INBOX.md"
    inbox = fx.hub / "INBOX.md"
    inbox.unlink()
    check(not inbox.exists(), "a hub with no INBOX.md")
    code, out = run_child([tool(fx, "mail.py"), "--send", "NORTH/hub", "alpha",
                           "a first finding", "FYI", "--no-push"], env=fx.env, cwd=fx.hub)
    check(code == 0 and inbox.is_file(), "mail.py --send creates it", out[-300:])
    raw, head = inbox.read_bytes(), seed.read_bytes()
    check(raw.startswith(head), "its head is templates/INBOX.md byte for byte")
    tail = raw[len(head):].decode("utf-8")
    check(tail.count("\n") == 1 and tail.startswith("- ") and "to: NORTH/hub" in tail
          and tail.endswith("\n"), "the letter is the one line after it, and the last")
    with in_fixture(fx):
        seen = load(fx.hub / "orchestrator.py", "orch_n5").read_inbox()
    check(len(seen) == 1 and "a first finding" in seen[0]["text"],
          "the board's own reader lists the letter (%d)" % len(seen), seen)
    constant = mail_seed_constant(SRC / "tools" / "mail.py")
    check(constant is not None and constant.encode("utf-8") == (REL / "templates" / "INBOX.md")
          .read_bytes(), "mail.py's INBOX_SEED equals the shipped seed, byte for byte")
    code, out = run_child([tool(fx, "mail.py"), "--send", "NORTH/hub", "alpha",
                           "a second finding", "FYI", "--no-push"], env=fx.env, cwd=fx.hub)
    raw2 = inbox.read_bytes()
    check(raw2.startswith(raw) and raw2[len(raw):].decode("utf-8").count("\n") == 1,
          "a second letter appends one line and writes no second header")
    case_ends(fx.w)


# ---------------------------------------------------------------------------
# N6 — the fleet unchanged (the side-by-side method)
# ---------------------------------------------------------------------------

CLOCK = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:?\d{2}|Z)?)?"
    r"|\b\d{1,2}:\d{2}\b"
    r"|\b\d+(?:\.\d+)?\s*(?:s|ms|min|mins|minutes|h|hr|hrs|d|w|mo|y)\b")
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


def unstable_lines(a_text, a2_text, places=()):
    """The lines ONE side moves by itself between two runs (A against A')."""
    if a_text is None or a2_text is None:
        return set()

    def prep(text):
        for place in places:
            text = text.replace(place[0], place[1])
        return [CLOCK.sub("#", l) for l in text.splitlines()]
    a, a2 = prep(a_text), prep(a2_text)
    return {i for i, (x, y) in enumerate(zip(a, a2)) if x != y}


def differences(a_text, b_text, places=(), moving=frozenset()):
    """[(a line, b line)] after the clock mask, the fixture's own paths and the
    number mask on the lines A moves by itself — nothing else is forgiven."""
    import difflib

    def prep(text):
        for place in places:
            text = text.replace(place[0], place[1])
        out = []
        for i, line in enumerate(text.splitlines()):
            line = CLOCK.sub("#", line)
            if i in moving:
                line = NUMBER.sub("#", line)
            out.append(line)
        return out
    a, b = prep(a_text or ""), prep(b_text or "")
    bad = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        width = max(i2 - i1, j2 - j1)
        for k in range(width):
            x = a[i1 + k] if i1 + k < i2 else "(nothing)"
            y = b[j1 + k] if j1 + k < j2 else "(nothing)"
            bad.append((x, y))
    return bad


# THE DECLARED DIFFERENCE. A collector that carries the "none yet" answer — a zero count
# answers "none yet" (NONE_YET, through mark_entry's `when_empty`) — gives every
# ZERO count on the tree its answer: the count's button gains its data-mark and
# the marks table gains its entry, `"<mark>": {"kind": …, "bytes": [["so far",
# "none yet"]]}`. N6's frozen projects carry no git history, so its fall is
# empty — "0 in the fall" — and so are the notes drawn between the fall's
# columns: that ONE declared difference shows as two answers on a fleet.
# Expected answers = the zero counts that answer covers on side A's own page; a
# collector without it is declared NOTHING. Taking exactly those
# answers out of the B lines must give the A lines back.
S4_SIGN = 'NONE_YET = "none yet"'
S4_ZERO = re.compile(          # a zero count S4 answers, drawn with no answer (side A)
    r'<button class="cnt" type="button">(?:<span id="nfall">0</span> in the fall'
    r'|0 (?:active|notes in six weeks|prompts? on file)'
    r'|<b>0</b> (?:memories|constellations|links|skills|laws|journal lines|dossier pages))'
    r'</button>')
S4_ATTR = re.compile(          # its button's answer, on side B (0, or # under the mask)
    r' data-mark="((?:sky:)?count:[a-z]+)">(?=(?:<span id="nfall">|<b>)?[0#](?![\d.]))')
S4_ENTRY = re.compile(         # its entry in the marks table, on side B
    r'"((?:sky:)?count:[a-z]+)": \{"kind": "[^"\\]*", "bytes": \[\["so far", "none yet"\]\]\}')


def without_s4_answers(line):
    """(the line with every S4 answer taken out, the marks whose button lost
    its answer, the marks whose table entry was taken out)."""
    attrs = S4_ATTR.findall(line)
    line = S4_ATTR.sub(">", line)
    entries = []
    while True:
        found = S4_ENTRY.search(line)
        if not found:
            break
        entries.append(found.group(1))
        start, end = found.start(), found.end()
        if line[end:end + 2] == ", ":
            end += 2
        elif line[start - 2:start] == ", ":
            start -= 2
        line = line[:start] + line[end:]
    return line, attrs, entries


def s4_answered(x, y):
    """True when the B line differs from the A line only by S4 answers."""
    if x == y:
        return False
    rest, attrs, entries = without_s4_answers(y)
    return bool(attrs or entries) and rest == x


def hub_copy(into):
    """ONE copy of the live hub, read and never written: the heartbeat moves
    the live hub while a gate runs, so both sides are clones of this one."""
    pristine = into / "pristine"
    if not pristine.exists():
        def ignore(d, names):
            out = [n for n in names if n in ("scratch", "__pycache__", ".git")
                   or n.endswith(".html")]
            if Path(d).name == "carry":
                out.extend(n for n in names if n == "backups")
            return out
        shutil.copytree(str(HUB), str(pristine), ignore=ignore, symlinks=True)
    return pristine


def frozen_projects(into, real_projects):
    """Every project's STATUS.md and OPENER*.md, copied once."""
    dst = into / "projects"
    if dst.exists():
        return dst
    dst.mkdir(parents=True)
    try:
        entries = sorted(real_projects.iterdir())
    except OSError:
        return dst
    for entry in entries:
        try:
            if entry.name.startswith(".") or not entry.is_dir():
                continue
            files = [entry / "STATUS.md"] if (entry / "STATUS.md").is_file() else []
            files += sorted(entry.glob("OPENER*.md"))
        except OSError:
            continue
        for path in files:
            (dst / entry.name).mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(path), str(dst / entry.name / path.name))
    return dst


def side(w, label, pristine, tool_layers, orch_src, real_record, projects):
    hub = w / label / "hub"
    shutil.copytree(str(pristine), str(hub), symlinks=True)
    for layer in tool_layers:
        for path in sorted(Path(layer).glob("*.py")):
            shutil.copyfile(str(path), str(hub / "tools" / path.name))
    shutil.copyfile(str(orch_src), str(hub / "orchestrator.py"))
    home = w / ("home-" + label)
    roots = dict(real_record.get("roots") or {})
    roots["orchestrator"] = str(hub)
    roots["projects"] = str(projects)
    record = dict(real_record)
    record["roots"] = roots
    write(home / "orchestrator-sync" / "machine.json",
          json.dumps(record, indent=2, ensure_ascii=False))
    env = dict(BASE_ENV)
    env.update({"HOME": str(home), "USERPROFILE": str(home), "PYTHONDONTWRITEBYTECODE": "1",
                "EXO_REGISTRY_JSON": str(hub / "registry.json")})
    return hub, home, env


LAWDUMP = '''import importlib.util, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
path, claude, hub = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sys.path.insert(0, str(path.parent))
spec = importlib.util.spec_from_file_location("collector_dump", str(path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sky = module.brain_sky({"claude": claude, "orchestrator": hub})
print(json.dumps([[l["name"], l["date"]] for l in sky["laws"]]))
'''


def laws_of(w, collector, claude, hub, env):
    helper = write(w / "lawdump.py", LAWDUMP)
    code, out = run_child([helper, collector, claude, hub], env=env)
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def case_fleet():
    case("N6", "THE FLEET UNCHANGED: P3 copies against P5 copies on one copy of the live hub")
    if LAYOUT == "installed":
        skip("the P3 copies it compares with sit beside a build; an installed hub has only "
             "the tools it runs, so there is no P3 base here to compare with")
        return
    reg_mod = load(P3 / "tools" / "exo_registry.py", "exo_registry_n6")
    owner = (reg_mod.registry(hub=HUB).get("owner") or {}).get("name") or ""
    legacy = Path(REAL_HOME_RAW) / "orchestrator-sync" / "machine.json"
    if not owner or not legacy.is_file():
        skip("this machine's registry names no owner (or it has no machine record), so it "
             "is a stranger's machine and has no fleet to compare")
        return
    real_record = json.loads(legacy.read_text(encoding="utf-8"))
    real_claude = Path((real_record.get("roots") or {}).get("claude")
                       or Path(REAL_HOME_RAW) / ".claude")
    w = world("n6")
    pristine = hub_copy(w)
    projects = frozen_projects(w, live_projects_root())
    p3_tools, p5_tools = P3 / "tools", HERE / "tools"
    a_hub, a_home, a_env = side(w, "a", pristine, [p3_tools], P3 / "orchestrator.py",
                                real_record, projects)
    a2_hub, a2_home, a2_env = side(w, "a2", pristine, [p3_tools], P3 / "orchestrator.py",
                                   real_record, projects)
    b_hub, b_home, b_env = side(w, "b", pristine, [p3_tools, p5_tools], HERE / "orchestrator.py",
                                real_record, projects)
    # The fixture's OWN paths are not the tools' output: the sides live in
    # three folders, and a page prints where it stands — plainly, and inside
    # the launch links, percent-encoded. Both spellings fold to one mark.
    from urllib.parse import quote
    places = []
    for folder, mark in ((a_hub, "<HUB>"), (a2_hub, "<HUB>"), (b_hub, "<HUB>"),
                         (a_home, "<HOME>"), (a2_home, "<HOME>"), (b_home, "<HOME>")):
        for spelled in (str(Path(folder).resolve()), str(folder)):
            places.append((quote(spelled, safe=""), quote(mark, safe="")))
            places.append((spelled, mark))
    # THE RUN ORDER IS A, B, A'. The sky and the tiles carry values that move
    # with the clock (a memory's activation, a lane's age), so B is bracketed
    # between two runs of A: a line the clock moves while B runs is moved
    # between A and A' as well, and only such a line takes the number mask.
    order = ((a_hub, a_env), (b_hub, b_env), (a2_hub, a2_env))
    sides = ((a_hub, a_env), (a2_hub, a2_env), (b_hub, b_env))

    # THE LAWS, by name and date: the owner-clause road read exactly as before.
    got_a = laws_of(w, a_hub / "tools" / "collect-openers.py", real_claude, a_hub, a_env)
    got_b = laws_of(w, b_hub / "tools" / "collect-openers.py", real_claude, b_hub, b_env)
    owner_words = reg_mod.owner_words(reg_mod.registry(hub=HUB))
    key = 0
    for line in (read(real_claude / "CLAUDE.md") or "").splitlines():
        if line.startswith("**") and any(("(%s" % w_) in line for w_ in owner_words):
            key += 1
    check(got_a is not None and got_b is not None and got_a == got_b,
          "the laws list, name and date, is EQUAL (P3 %s · P5 %s)"
          % (len(got_a or []), len(got_b or [])))
    check(got_b is not None and len(got_b) == key,
          "   and it is the gate's own count of owner-clause heads (%d)" % key)
    imports = [l for l in (read(real_claude / "CLAUDE.md") or "").splitlines()
               if re.match(r"^\s*@\S+\s*$", l)]
    check(imports == [], "   the owner's CLAUDE.md names no `@` import (%d), so the import "
          "road adds nothing on the fleet" % len(imports))
    note("the live hub's own skills/ folder: %s — the S4 seed rule never reaches it "
         "(the older layout is not seeded)" % ("present" if (HUB / "skills").exists()
                                               else "none"))

    # THE PAGES AND THE PRINTS
    compared = []
    for flag in ("--chat", "--table"):
        outs = {str(h): run_child([h / "tools" / "collect-openers.py", flag], env=e,
                                  cwd=h)[1] for h, e in order}
        outs = [outs[str(h)] for h, _e in sides]
        compared.append(("collect-openers %s" % flag, outs[0], outs[2],
                         unstable_lines(outs[0], outs[1], places)))
    for h, e in order:
        run_child([h / "tools" / "collect-openers.py", "--write-tree"], env=e, cwd=h)
    t = [read(h / "TREE.md") for h, _e in sides]
    compared.append(("TREE.md (--write-tree)", t[0], t[2], unstable_lines(t[0], t[1], places)))
    for h, e in order:
        run_child([h / "tools" / "collect-openers.py", "--html"], env=e, cwd=h)
    t = [read(h / "tree.html") for h, _e in sides]
    compared.append(("tree.html (--html)", t[0], t[2], unstable_lines(t[0], t[1], places)))
    for h, e in order:
        run_child([h / "orchestrator.py"], env=e, cwd=h, timeout=600)
    b = [read(h / "board.html") for h, _e in sides]
    compared.append(("board.html (orchestrator.py)", b[0], b[2],
                     unstable_lines(b[0], b[1], places)))
    # S15: which S4 answers are expected here? Only from a collector that
    # carries S4, and only for the zero counts side A's own page draws.
    s4 = S4_SIGN in (read(b_hub / "tools" / "collect-openers.py") or "")
    for name, a_text, b_text, moving in compared:
        bad = differences(a_text, b_text, places, moving)
        declared = [(x, y) for x, y in bad if s4_answered(x, y)]
        bad = [(x, y) for x, y in bad if not s4_answered(x, y)]
        expected = (len(S4_ZERO.findall(a_text or ""))
                    if s4 and name.startswith("tree.html") else 0)
        attrs, entries = [], []
        for _x, y in declared:
            _rest, got_attrs, got_entries = without_s4_answers(y)
            attrs += got_attrs
            entries += got_entries
        for x, y in bad[:2]:
            note("UNDECLARED  P3: %s" % x[:160])
            note("            P5: %s" % y[:160])
        if expected or declared:
            note("DECLARED  %s: %d zero count%s on side A; answered on the page: %s; in the "
                 "marks table: %s" % (name, expected, "" if expected == 1 else "s",
                                      ", ".join(sorted(attrs)) or "none",
                                      ", ".join(sorted(entries)) or "none"))
        but = ((" but for ONE declared difference, its %d zero count%s answer \"none yet\" (S4)"
                % (expected, "" if expected == 1 else "s")) if expected else "")
        check(a_text is not None and b_text is not None and not bad
              and len(attrs) == expected and sorted(attrs) == sorted(entries),
              "%s: EQUAL%s (%d line%s took the number mask, each moved by A vs A')"
              % (name, but, len(moving), "" if len(moving) == 1 else "s"))

    # improvements: exactly one footer line, exactly one state value — declared
    for h, e in order:
        run_child([h / "tools" / "improvements.py", "--write", "--hub", h], env=e, cwd=h)
    pages = [read(h / "improvements.html") for h, _e in sides]
    bad = differences(pages[0], pages[2], places, unstable_lines(pages[0], pages[1], places))
    footer = [(x, y) for x, y in bad if "read from" in x and "read from design/BUILD-QUEUE.md" in y]
    check(len(bad) == 1 and len(footer) == 1,
          "improvements.html differs in exactly ONE line, the footer (%d difference%s)"
          % (len(bad), "" if len(bad) == 1 else "s"), bad[:2])
    states = []
    for h, _e in sides:
        try:
            states.append(json.loads(read(h / "improvements-state.json") or "{}"))
        except ValueError:
            states.append({})

    def masked_state(d):
        d = json.loads(CLOCK.sub("#", json.dumps(d, sort_keys=True)))
        return d
    sa, sb = masked_state(states[0]), masked_state(states[2])
    keys = sorted(k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k))
    check(keys == ["queue"] and sb.get("queue") == "design/BUILD-QUEUE.md",
          "improvements-state.json differs in exactly ONE value, `queue`, now hub-relative",
          keys)
    note("declared differences, counted: improvements.html 1 line · improvements-state.json "
         "1 value · every other output 0")

    # THE MUTATION: a number bumped on a stable line of B's board must FAIL.
    moving = unstable_lines(b[0], b[1], places)
    rows = (b[2] or "").splitlines(True)
    at = None
    for index, raw in enumerate(rows):
        if index in moving or index >= len((b[0] or "").splitlines()):
            continue
        if raw.rstrip("\n") != (b[0] or "").splitlines()[index]:
            continue
        if re.search(r"\b(\d+)\b", raw):
            at = index
            break
    if at is None:
        check(False, "a stable line with a number could be found to mutate")
    else:
        found = re.search(r"\b(\d+)\b", rows[at])
        rows[at] = rows[at][:found.start(1)] + str(int(found.group(1)) + 7) + rows[at][found.end(1):]
        check(bool(differences(b[0], "".join(rows), places, moving)),
              "a number wrong on a stable line of the board is CAUGHT (line %d)" % (at + 1))

    # the fleet's own hub opener is never overwritten by the seed walk
    live_opener = HUB / "OPENER.md"
    if live_opener.is_file():
        fx = stranger("n6-seedwalk", seeds=False)
        shutil.copyfile(str(live_opener), str(fx.hub / "OPENER.md"))
        before = sha_of(fx.hub / "OPENER.md")
        code, out = run_child([fx.hub / "sync" / "install.py", "--defaults", "--machine",
                               "north", "--only", "seeds"], env=fx.env, cwd=fx.hub)
        installed = json.loads(read(fx.hub / "installed.json") or "{}")
        check(code == 0 and sha_of(fx.hub / "OPENER.md") == before
              and "OPENER.md" not in (installed.get("seeded") or [])
              and "OPENER.md  -- already here; left exactly as it is" in out,
              "the fleet's own hub OPENER.md, in a hub the walk seeds, is left as it is "
              "and not recorded as a seed")
        case_ends(fx.w)
    installer = read(HERE / "sync" / "install.py") or ""
    check('ctx.note(SKIPPED, "the seeds", "the older layout carries its own routines")'
          in installer and 'ctx.note(SKIPPED, "the laws", "the older layout keeps its own '
          'CLAUDE.md")' in installer,
          "and the fleet's own layout (the older one) is never seeded, nor its laws rendered")
    case_ends(w)


# ---------------------------------------------------------------------------
# N7 — the law horizon, name-free
# ---------------------------------------------------------------------------

BOLD_HEAD = re.compile(r"^\*\*(.+?)\*\*")


def answer_key(text):
    """The gate's OWN reading of which lines are starter laws: a line opening
    with a bold head that ends in a period. Written here, never borrowed."""
    out = []
    for line in text.splitlines():
        found = BOLD_HEAD.match(line)
        if found and found.group(1).rstrip().endswith("."):
            out.append([found.group(1).strip()[:-1].strip(), ""])
    return out


IMPORT_LINE = "@~/.claude/exocortex-laws.md"
USER_IMPORT_LINE = "@~/Exocortex/dossier/LAWS.md"           # the person's own book
CLAUDE_TITLE = "# Your instructions — the lines below load the exocortex laws and yours"
ENTRY = "%s\n%s\n%s\n" % (CLAUDE_TITLE, IMPORT_LINE, USER_IMPORT_LINE)


def case_horizon():
    case("N7", "LAWS HORIZON: the starter laws read without anyone's name, through the import")
    fx = stranger("n7")
    code, out = run_child([fx.hub / "sync" / "install.py", "--defaults", "--machine", "north",
                           "--only", "laws"], env=fx.env, cwd=fx.hub)
    claude = fx.home / ".claude"
    claude_md, beside = claude / "CLAUDE.md", claude / "exocortex-laws.md"
    check(code == 0 and read(claude_md) == ENTRY
          and beside.is_file(), "the world's CLAUDE.md is the three-line file that imports "
          "the rendered law book and the person's own", out[-300:])
    expected = answer_key(read(beside) or "")
    check(len(expected) > 50, "the gate's own key counts %d starter laws in the "
          "rendering" % len(expected))
    extra = ("**Foo (ruled 2026-10-05).** A personal law, dated.\n"
             "**During**\n"
             "**Close** (arc done, or session getting long) — a section label.\n"
             "**Bar (ratified 2026-10-06).** Another, dated the other way.\n")
    write(claude_md, (read(claude_md) or "") + extra)
    got = laws_of(fx.w, tool(fx, "collect-openers.py"), claude, fx.hub, fx.env)
    want = expected + [["Foo", "2026-10-05"], ["Bar", "2026-10-06"]]
    check(got is not None and len(got) == len(want),
          "the collector's law count, THROUGH the import, is the key plus the two dated "
          "ones (%s of %d)" % (len(got or []), len(want)))
    check(got == want, "   every name and date right, in file order",
          [g for g in (got or []) if g not in want][:3])
    check(["Foo", "2026-10-05"] in (got or []), "   `(ruled 2026-10-05)` counts, with its date")
    check(["Bar", "2026-10-06"] in (got or []), "   `(ratified 2026-10-06)` counts, with its date")
    check(not [g for g in (got or []) if g[0] in ("During", "Close")],
          "   `**During**` and `**Close** (arc done…` add nothing")
    code, out = run_child([tool(fx, "collect-openers.py"), "--html"], env=fx.env, cwd=fx.hub)
    check("%d law ticks / %d laws" % (len(want), len(want)) in out,
          "the tree's own report draws them all as ticks (%d)" % len(want), out[-200:])
    if (P3 / "tools" / "collect-openers.py").is_file():
        p3 = laws_of(fx.w, P3 / "tools" / "collect-openers.py", claude, fx.hub, fx.env)
        check(p3 == [], "the P3 collector reads NONE of them here — the finding this closes (%s)"
              % (len(p3) if p3 is not None else "?"))
    else:
        skip("the P3 collector this half compares with sits beside a build; there is none here")

    # the import's three spellings, one level only, and a missing file skipped
    write(claude / "rel-laws.md", "**Relative one.** Named from the claude root.\n"
                                  "@~/.claude/deeper.md\n")
    write(claude / "deeper.md", "**Too deep.** An import's own import is never read.\n")
    absolute = write(fx.w / "abs-laws.md", "**Absolute one.** Named by its whole path.\n")
    write(claude_md, "%s\n@rel-laws.md\n@%s\n@~/.claude/not-there.md\n%s\n"
          % (CLAUDE_TITLE, absolute, IMPORT_LINE))
    got = laws_of(fx.w, tool(fx, "collect-openers.py"), claude, fx.hub, fx.env)
    names = [g[0] for g in (got or [])]
    check(got is not None and names[:2] == ["Relative one", "Absolute one"]
          and len(got) == len(expected) + 2,
          "a claude-root-relative and an absolute import are read, in their place")
    check("Too deep" not in names, "   an import's own `@` line is not followed (one level)")
    check(got is not None, "   a line naming a missing file is skipped, never a crash")
    if os.name != "nt":
        absolute.chmod(0)
        got = laws_of(fx.w, tool(fx, "collect-openers.py"), claude, fx.hub, fx.env)
        absolute.chmod(0o644)
        check(got is not None and "Absolute one" not in [g[0] for g in got],
              "   an unreadable imported file is skipped, never a crash")
    case_ends(fx.w)


# ---------------------------------------------------------------------------
# N8 — the laws step
# ---------------------------------------------------------------------------

def install(fx, *args, env=None):
    return run_child([fx.hub / "sync" / "install.py", "--defaults", "--machine", "north"]
                     + list(args), env=env or fx.env, cwd=fx.hub)


def case_laws_step():
    case("N8", "THE LAWS STEP: one road for the law book, and the skills, to the session")
    fx = stranger("n8")
    claude = fx.home / ".claude"
    beside = claude / "exocortex-laws.md"
    check(not (fx.hub / "skills").exists(),
          "the seed walk made no skills/ in the hub (S4: skills are not seeds)")
    code, out = install(fx, "--only", "laws")
    two = read(claude / "CLAUDE.md")
    check(code == 0 and two == ENTRY,
          "no CLAUDE.md: it is written as three lines of the person's — a title, "
          "`%s` and `%s`" % (IMPORT_LINE, USER_IMPORT_LINE), out[-300:])
    text = read(beside) or ""
    check(bool(text) and "{{" not in text,
          "the rendering is at the claude root's exocortex-laws.md, no unresolved {{")
    check("`%s` is the installed hub folder" % fx.hub in text,
          "{{HUB}} resolved to the world's hub")
    check(str(fx.hub / "sync" / "sync.py") in text and PY in text,
          "{{SYNC}} resolved to the installed sync command with its interpreter")
    record = json.loads(read(fx.hub / "installed.json") or "{}")
    laws = record.get("laws") or {}
    check(laws.get("to") == str(beside) and bool(laws.get("shipped_sha"))
          and bool(laws.get("rendered"))
          and (laws.get("claude_md") or {}).get("path") == str(claude / "CLAUDE.md")
          and bool((laws.get("claude_md") or {}).get("written")),
          "installed.json records both: the rendering (shipped sha, render time) and "
          "CLAUDE.md (written)")
    shipped = sorted(p.name for p in (fx.hub / "templates" / "skills").iterdir() if p.is_dir())
    for name in shipped:
        check((claude / "skills" / name / "SKILL.md").read_bytes()
              == (fx.hub / "templates" / "skills" / name / "SKILL.md").read_bytes(),
              "skill %s copied to the claude root's skills/, byte for byte" % name)
    check(sorted((record.get("skills") or {})) == shipped, "and each recorded")
    before = snapshot(fx.home)
    code, out = install(fx, "--only", "laws")
    check(code == 0 and "never touched again" in out and "CREATED" not in out
          and "REPAIRED" not in out, "run again: PRESENT, nothing created", out[-300:])
    check(snapshot(fx.home) == before, "   and every byte of the home folder is unchanged")
    with io.open(str(fx.hub / "laws" / "LAWS.md"), "a", encoding="utf-8") as fh:
        fh.write("\n**A new starter law.** Shipped by a later version.\n")
    code, out = install(fx, "--only", "laws")
    now = read(beside) or ""
    rec2 = (json.loads(read(fx.hub / "installed.json") or "{}").get("laws") or {})
    check(code == 0 and "rendered again: the shipped law book changed" in out
          and "**A new starter law.**" in now and read(claude / "CLAUDE.md") == two,
          "a newer shipped book: exocortex-laws.md is rendered again, CLAUDE.md byte for "
          "byte as it was", out[-300:])
    check(rec2.get("shipped_sha") and rec2.get("shipped_sha") != laws.get("shipped_sha"),
          "   and the record carries the new shipped sha")
    code, out = install(fx, "--repair")
    check(code == 0 and "4. the laws" in out and read(claude / "CLAUDE.md") == two,
          "the repair road runs the laws step too, and touches CLAUDE.md not at all",
          out[-300:])

    # a CLAUDE.md of the user's: untouched; the one line, once
    fx2 = stranger("n8-mine")
    mine = write(fx2.home / ".claude" / "CLAUDE.md", "# my own rules\n")
    mine_sha = sha_of(mine)
    write(fx2.home / ".claude" / "skills" / "focus" / "SKILL.md", "# my own focus skill\n")
    code, out = install(fx2, "--only", "laws")
    beside2 = fx2.home / ".claude" / "exocortex-laws.md"
    check(code == 0 and sha_of(mine) == mine_sha, "a CLAUDE.md of yours is untouched, byte "
          "for byte", out[-300:])
    check(beside2.is_file() and "{{" not in (read(beside2) or ""),
          "the rendering is at the same place as on every machine")
    check("add the line `%s` to it to load them" % IMPORT_LINE in out,
          "the one `@` line is printed, home-relative", out[-300:])
    check(read(fx2.home / ".claude" / "skills" / "focus" / "SKILL.md") == "# my own focus skill\n",
          "a skill of yours by a shipped name is never touched")
    check("add the line `%s` to it to load it" % USER_IMPORT_LINE in out,
          "   and the line that loads the person's own book", out[-300:])
    write(mine, "# my own rules\n%s\n%s\n" % (IMPORT_LINE, USER_IMPORT_LINE))
    code, out = install(fx2, "--only", "laws")
    check(code == 0 and "add the line" not in out,
          "once CLAUDE.md loads both, no line is printed again")

    # a CLAUDE.md the brain carried from another machine is the three-line file:
    # it already loads this machine's own rendering and the person's own book
    fx3 = stranger("n8-carried")
    carried = write(fx3.home / ".claude" / "CLAUDE.md", ENTRY)
    carried_sha = sha_of(carried)
    code, out = install(fx3, "--only", "laws")
    check(code == 0 and sha_of(carried) == carried_sha and "add the line" not in out
          and (fx3.home / ".claude" / "exocortex-laws.md").is_file()
          and str(fx3.hub) in (read(fx3.home / ".claude" / "exocortex-laws.md") or ""),
          "a CLAUDE.md carried from another machine: untouched, no line, and the "
          "rendering it loads names THIS machine's hub", out[-300:])

    # --dry writes nothing
    fx4 = stranger("n8-dry")
    before = snapshot(fx4.home)
    code, out = install(fx4, "--dry-run", "--only", "laws")
    after = snapshot(fx4.home)
    check(code == 0 and "WOULD CREATE" in out and {k: v for k, v in after.items()
                                                    if not k.endswith(".lock")}
          == {k: v for k, v in before.items() if not k.endswith(".lock")},
          "--dry-run --only laws says WOULD CREATE and writes nothing", out[-300:])

    # an unfillable token stops the step and writes nothing
    fx5 = stranger("n8-token")
    with io.open(str(fx5.hub / "laws" / "LAWS.md"), "a", encoding="utf-8") as fh:
        fh.write("\nRun `{{NOPE}}` first.\n")
    code, out = install(fx5, "--only", "laws")
    check(code == 1 and "{{NOPE}}" in out and "STOP" in out
          and not (fx5.home / ".claude" / "CLAUDE.md").exists()
          and not (fx5.home / ".claude" / "exocortex-laws.md").exists(),
          "a token the installer cannot fill is a STOP, and nothing is written", out[-300:])

    # THE TABLE, each row proved
    manifest = json.loads(read(fx.hub / "sync" / "manifest.base.json") or "{}")
    entries = {e.get("id"): e for e in manifest.get("entries") or []}
    seeded = json.loads(read(fx.hub / "installed.json") or "{}").get("seeded") or []
    check(not [s for s in seeded if s.startswith("skills/")] and not (fx.hub / "skills").exists(),
          "SEED: no skill is a seed any more — nothing under the hub's skills/, none recorded")
    check((entries.get("claude-md") or {}).get("live") == {"root": "claude", "rel": "CLAUDE.md"}
          and (entries.get("skills") or {}).get("live") == {"root": "claude", "rel": "skills"},
          "CARRIED: the brain carries the claude root's CLAUDE.md and skills/ between machines")
    under_claude = [e for e in entries.values() if (e.get("live") or {}).get("root") == "claude"]
    check(not [e for e in under_claude if (e.get("live") or {}).get("rel") in
               ("exocortex-laws.md", "")],
          "and nothing carries exocortex-laws.md: each machine renders its own")
    case_ends(fx.w)
    for other_fx in (fx2, fx3, fx4, fx5):
        case_ends(other_fx.w)


# ---------------------------------------------------------------------------
# N9 — a whole install: no scheduler, no window, nothing beside the real hub
# ---------------------------------------------------------------------------

JOB_WORD = "exocortex"


def scheduler_list():
    """The machine's scheduler, READ only: the lines naming this program's jobs."""
    try:
        if os.name == "nt":
            done = subprocess.run(["schtasks", "/Query", "/FO", "CSV", "/NH"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  universal_newlines=True, timeout=120)
        else:
            done = subprocess.run(["launchctl", "list"], stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, universal_newlines=True,
                                  timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    rows = [l.split()[-1] if os.name != "nt" else l.split(",")[0]
            for l in (done.stdout or "").splitlines() if JOB_WORD in l.lower()]
    return sorted(rows)


def case_no_scheduler():
    case("N9", "NO SCHEDULER: a whole install in a world reaches nothing of the machine's")
    fx = stranger("n9", seeds=False)
    jobs_before = scheduler_list()
    marker = fx.w / "the-machine-was-reached.txt"
    opener_shims(fx.w / "shims", marker)
    env = dict(fx.env)
    env["PATH"] = str(fx.w / "shims") + os.pathsep + env.get("PATH", "")
    code, out = install(fx, env=env)
    check(code == 0 and "EXOCORTEX INSTALLED" in out and "STOP:" not in out,
          "the whole install runs to its end", out[-500:])
    steps = [l.strip() for l in out.splitlines()
             if re.match(r"^\d\. (machine\.json|the [a-z]+)$", l.strip())]
    check(steps == ["1. machine.json", "2. the brain", "3. the seeds", "4. the laws",
                    "5. the heartbeat", "6. the watchers", "7. the tree"],
          "its seven steps, numbered once each, the laws fourth", steps)
    check("NOT handed to this machine's scheduler" in out or "registers nothing" in out.lower()
          or "EXO_INSTALL_NO_SCHEDULER is set" in out, "the heartbeat said it registered nothing")
    check("tree drawn, not opened" in out, "the DONE line says the tree was drawn, not opened")
    check(not marker.exists(), "no scheduler command and no page opener was called",
          read(marker))
    check((fx.home / ".claude" / "CLAUDE.md").is_file()
          and (fx.home / ".claude" / "exocortex-laws.md").is_file()
          and (fx.hub / "tree.html").is_file() and (fx.hub / "board.html").is_file(),
          "the laws (CLAUDE.md and its rendering), the tree and the board are there")
    before = snapshot(fx.home / ".claude")
    code, out = install(fx, env=env)
    check(code == 0 and snapshot(fx.home / ".claude") == before,
          "a second install is a repair: the claude root unchanged", out[-300:])
    jobs_after = scheduler_list()
    if jobs_before is None:
        note("the machine's job list could not be read here — the marker above is the proof")
    else:
        check(jobs_after == jobs_before, "the machine's own job list is unchanged (%d line%s)"
              % (len(jobs_before), "" if len(jobs_before) == 1 else "s"))
    now = live_names()
    moved = sorted(k for k in LIVE_AT_START if now.get(k) != LIVE_AT_START[k])
    check(not moved, "the live names this gate's worlds could create are unchanged", moved)
    case_ends(fx.w)


# ---------------------------------------------------------------------------
# N10 — scrub, shape, and every diff applies
# ---------------------------------------------------------------------------

P5_FILES = ("tools/collect-openers.py", "tools/improvements.py", "tools/mail.py",
            "tools/new-project.py", "orchestrator.py", "sync/install.py",
            "templates/OPENER.md", "IMAGE.json")
DIFFS = (("collect-openers.py.diff", "tools/collect-openers.py"),
         ("improvements.py.diff", "tools/improvements.py"),
         ("mail.py.diff", "tools/mail.py"),
         ("orchestrator.py.diff", "orchestrator.py"),
         ("install.py.diff", "sync/install.py"))
HOME_PATH = re.compile(r"(?<![\w.])/(?:Users|home)/([A-Za-z0-9_.\-]+)"
                       r"|[A-Za-z]:\\Users\\([A-Za-z0-9_.\-]+)")
# An example in a comment names a placeholder, not a person's home.
PLACEHOLDERS = {"you", "user", "username", "someone", "me", "example", "name"}


def real_home_path(text):
    """The first absolute home path in a text whose user is not a placeholder."""
    for found in HOME_PATH.finditer(text or ""):
        user = (found.group(1) or found.group(2) or "").lower()
        if user not in PLACEHOLDERS:
            return found
    return None
DOT_GIT = re.compile(r"\.git(?:ignore|attributes|modules|)\b")


def case_scrub():
    case("N10", "SCRUB: no private word, no home path, no shell string; every diff applies")
    if LAYOUT == "installed":
        skip("the build's own files and diffs, and the P3 copies the diffs apply to, sit "
             "beside a build; an installed hub has none of them")
        return
    for rel in P5_FILES:
        text = read(HERE / rel)
        check(text is not None, "%s is here" % rel)
        hits = [masked(w) for w, p in PATTERNS if p.search(fold(text or ""))]
        check(not hits, "%s: no private word (folded, at word boundaries)" % rel, hits)
        found = real_home_path(text)
        check(found is None, "%s: no absolute home path" % rel,
              "line %d" % ((text or "")[:found.start()].count("\n") + 1) if found else "")
        if rel.endswith(".py"):
            try:
                ast.parse(text or "", feature_version=(3, 9))
                parsed = True
            except SyntaxError as exc:
                parsed = exc
            check(parsed is True, "%s parses as Python 3.9" % rel, parsed)
            check("killpg" not in (text or "") and "shell=True" not in (text or ""),
                  "%s: no os.killpg, no shell=True" % rel)
    opener = read(HERE / "templates" / "OPENER.md") or ""
    check(DOT_GIT.search(opener) is None, "the seed the mirror carries names no dot-git file")
    tool_text = read(HERE / "tools" / "new-project.py") or ""
    check(not re.search(r"subprocess\.\w+\(\s*[\"']", tool_text)
          and not re.search(r"os\.system|os\.popen", tool_text),
          "new-project.py runs no string command — argument lists only")
    words_in_out = [masked(w) for w, p in PATTERNS if p.search(fold("\n".join(OUT)))]
    check(not words_in_out, "this gate's own output so far carries no private word")
    check(real_home_path("\n".join(OUT)) is None, "   and no absolute home path")
    patch = shutil.which("patch")
    if patch is None:
        note("patch is not on this machine's PATH — the diffs are checked by Release")
    for diff_name, rel in DIFFS:
        diff = HERE / diff_name
        if not diff.is_file():
            check(False, "%s is here" % diff_name)
            continue
        if patch is None:
            continue
        w = WORLDS / "n10-patch"
        w.mkdir(parents=True, exist_ok=True)
        base = w / Path(rel).name
        shutil.copyfile(str(P3 / rel), str(base))
        code, out = run_child([patch, "-s", "-o", str(w / "out"), str(base), str(diff)])
        same = (w / "out").is_file() and (w / "out").read_bytes() == (HERE / rel).read_bytes()
        check(code == 0 and same, "%s applied to the P3 copy gives the P5 copy, byte for byte"
              % diff_name, out[-200:])
        shutil.rmtree(str(w), ignore_errors=True)
    case_ends()


# ---------------------------------------------------------------------------

CASES = [("N1", case_rails), ("N2", case_empty), ("N3", case_new_project),
         ("N4", case_ledger), ("N5", case_mail), ("N6", case_fleet),
         ("N7", case_horizon), ("N8", case_laws_step), ("N9", case_no_scheduler),
         ("N10", case_scrub)]


def guarded(name, run):
    global CASE
    try:
        run()
    except Exception as exc:                        # a case that dies is a FAIL
        CASE = name
        check(False, "%s ran to its end" % name, "%s: %s" % (type(exc).__name__, exc))
        import traceback
        for line in traceback.format_exc().splitlines()[-6:]:
            say("        %s" % line)


def main():
    started = time.time()
    if LAYOUT == "installed" and not IMAGE.get("files"):
        # The one line a runner reads as "cannot run on this layout": nothing
        # else is printed, and no check is counted.
        shutil.rmtree(str(WORLDS), ignore_errors=True)
        sys.stdout.write("gate-firstrun.py: skipped here \u2014 this hub is not a program tree: "
                         "it carries no partition rule (templates/dot-gitignore), and a "
                         "stranger's program tree is what this gate builds from\n")
        return 0
    say("gate-firstrun — BQ-045 P5, a stranger's first run draws")
    say("layout     %s \u2014 %s" % (LAYOUT, HERE))
    say("worlds     %s (the system temp folder), removed at the end of every case" % WORLDS)
    say("started    %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    try:
        if not wanted("N1"):
            LIVE_AT_START.update(live_names())
        for name, run in CASES:
            if wanted(name):
                guarded(name, run)
    finally:
        if not KEEP:
            shutil.rmtree(str(WORLDS), ignore_errors=True)
    say("")
    left_worlds = ([p.name for p in WORLDS.iterdir()] if WORLDS.exists() else [])
    check(KEEP or not WORLDS.exists(), "every fixture world and the run's root are gone",
          left_worlds)
    check(KEEP or other_roots() == [], "nothing of this gate's making is left in the temp folder",
          [p.name for p in other_roots()])
    left = survivors()
    check(not left, "strays after the run: 0", left)
    passed = sum(1 for _c, _n, good in checks if good)
    if fails:
        say("")
        say("FAILED:")
        for case_name, what, detail in fails:
            say("  %s  %s" % (case_name, what))
    say("")
    say("children started: %d" % CHILDREN)
    say("finished %s · %.1f s" % (time.strftime("%Y-%m-%d %H:%M:%S"), time.time() - started))
    for line in SKIPS:
        say("SKIPPED  %s" % line)
    say("%d checks · %d passed · %d failed%s" % (len(checks), passed, len(checks) - passed,
                                                (" · %d skipped" % len(SKIPS)) if SKIPS else ""))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
