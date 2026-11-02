#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-paths.py — proof for exo_paths.py, the path resolver.

    python3 gate-paths.py              every case, including the live read-only one
    python3 gate-paths.py --no-live    skip the live case (a machine with no record)
    python3 gate-paths.py --keep       leave the fixture world behind to look at
    python3 gate-paths.py --ack        write the acknowledgment after a green run

Hermetic, apart from ONE case. Every fixture is built in a temporary world
outside the hub, with its own HOME, and is removed at the end. The live case
(P1) only READS this machine: it works out the older answers for itself, from
the older layout's own file, and requires the module to agree with them.

The cases:
  R   rails: the fixture world is outside the hub, and no repository metadata
      is ever created inside it
  P1  live equality with the older layout, read-only
  P2  a program tree with no older folder anywhere, before and after a record
  P3  an older-layout fixture: every key as the table says
  P4  a hub's own record beats the home one; a named file beats both
  P5  record and folders disagreeing, both ways: reported, never resolved
  P6  damage: empty, invalid, a list, no folders, odd values — no exception
  P7  the home folder is read at call time: two homes, two answers, one process
  P8  no side effects: the fixture tree is byte-identical afterwards
  P9  the older folder's name appears exactly once in the module's code
  P10 the record: every key every time, the version, and the version gate
  P11 a repository marker as a folder and as a file
  ACK the acknowledgment: refused by a copy outside tools/, written from tools/
  ACK2 a copy run FROM a folder named tools with --ack ends on its own, one
      nested run deep, and leaves no process and no fixture behind
  ACK3 the runaway shape re-made on purpose — a gate whose children carry no
      mark and whose refusal half runs itself — is stopped by the depth guard
  W1   the survivors walk finds a child's descendants by lineage only — never
      this gate, the shell that called it, a query whose text names the gate,
      or a reused pid (the Windows half of ACK2/ACK3)

A gate never launches itself deeper than MAX_DEPTH copies: every child carries
its depth, a child three deep refuses to run, and the outermost gate starts
each child in its own process group and kills the whole group on a timeout.
"""
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
import tokenize
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True             # nothing of ours leaves a cache behind
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

try:                                       # a console that cannot spell "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
MODULE = HERE / "exo_paths.py"
PY = sys.executable

ARGS = sys.argv[1:]
NO_LIVE = "--no-live" in ARGS
KEEP = "--keep" in ARGS
ACK = "--ack" in ARGS
INNER = bool(os.environ.get("EXO_GATE_PATHS_INNER"))
DEPTH = int(os.environ.get("EXO_GATE_PATHS_DEPTH") or 0)   # gates above this one
MAX_DEPTH = 2          # outer → a copy in a scratch tools/ → its refusal copy; never deeper
LAST_CHILD = None      # the last process cli() started, for the survivors check

# The older layout's folder name, written here on purpose: this gate must work
# the old answers out for itself, without asking the module under test (P1, P9).
OLDER_DIRNAME = "orchestrator-sync"

BASE_ENV = dict(os.environ)                # the real environment, kept for the live case
REAL_HOME = Path(os.path.expanduser("~")).resolve()

DUMMY_SYNC = "# stands in for the sync package's entry point\n"
GIT_NAMES = (".git", ".gitignore", ".gitattributes", ".gitmodules")

checks, fails = [], []
SKIPPED = []                               # the cases this machine had nothing to read for
HUB_TOP_AT_START = None                    # the hub's own repository names, as found
LIVE_RAN = False                           # the live case read this machine (P1)
CASES = {}
CASE = "R"
SEEN = []                                  # every record produced, for P10


# ---------------------------------------------------------------------------
# saying what happened
# ---------------------------------------------------------------------------

def case(name, title):
    global CASE
    CASE = name
    CASES.setdefault(name, [0, 0])
    print("\n── %s %s " % (name, title) + "─" * max(0, 60 - len(title)))


def ok(name, cond, detail=""):
    checks.append(bool(cond))
    CASES.setdefault(CASE, [0, 0])[0 if cond else 1] += 1
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", name,
                          ("  — " + " ".join(str(detail).split())) if (detail and not cond) else ""))
    if not cond:
        fails.append("%s · %s" % (CASE, name))


def note(text):
    print("  ..  %s" % text)


def skip(text):
    """A case this machine cannot answer, said in one line and counted."""
    SKIPPED.append("%s · %s" % (CASE, text))
    note("skipped: " + text)


def same(got, want):
    """Two paths are the same place (None matches None)."""
    if got is None or want is None:
        return got is None and want is None
    try:
        return Path(got).resolve() == Path(want).resolve()
    except OSError:
        return str(got) == str(want)


# ---------------------------------------------------------------------------
# the fixture world
# ---------------------------------------------------------------------------

SCRATCH = Path(tempfile.mkdtemp(prefix="exo-paths-gate-")).resolve()


def world(name):
    w = SCRATCH / name
    w.mkdir(parents=True, exist_ok=True)
    return w


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def record_file(path, **fields):
    return write(path, json.dumps(fields, indent=2, sort_keys=True) + "\n")


def program_tree(hub):
    """A hub that looks like a checkout of the program."""
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(MODULE), str(hub / "tools" / "exo_paths.py"))
    write(hub / "sync" / "sync.py", DUMMY_SYNC)
    return hub


def older_home(home, name="alpha", roots=None, git=True, sync=True, **extra):
    """A home with the older layout's folder in it: the record, the sync entry
    point and a repository marker, exactly as that layout has them."""
    folder = home / OLDER_DIRNAME
    folder.mkdir(parents=True, exist_ok=True)
    if sync:
        write(folder / "sync.py", DUMMY_SYNC)
    if git:
        (folder / ".git").mkdir(exist_ok=True)     # in the temporary world only
    record_file(folder / "machine.json", name=name, roots=(roots or {}), **extra)
    return folder


class using_home(object):
    """This block runs as if the machine's home were somewhere else."""

    KEYS = ("HOME", "USERPROFILE", "EXO_MACHINE_JSON")

    def __init__(self, home=None, machine_json=None):
        self.home, self.machine_json = home, machine_json

    def __enter__(self):
        self.saved = dict((k, os.environ.get(k)) for k in self.KEYS)
        if self.home is not None:
            os.environ["HOME"] = str(self.home)
            os.environ["USERPROFILE"] = str(self.home)
        if self.machine_json is None:
            os.environ.pop("EXO_MACHINE_JSON", None)
        else:
            os.environ["EXO_MACHINE_JSON"] = str(self.machine_json)
        return self

    def __exit__(self, *exc):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        return False


def sha256_of(path):
    h = hashlib.sha256()
    with io.open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root):
    """Every folder, file, size and content hash under a tree."""
    out = {}
    for base, dirs, files in os.walk(str(root)):
        dirs.sort()
        files.sort()
        for d in dirs:
            out[str(Path(base, d).relative_to(root)) + "/"] = ("dir",)
        for f in files:
            p = Path(base, f)
            try:
                out[str(p.relative_to(root))] = (p.stat().st_size, sha256_of(p))
            except OSError:
                out[str(p.relative_to(root))] = ("unreadable",)
    return out


def cli(*args, **kw):
    """(exit code, stdout, stderr) from a run of the module — or of a copy of
    this gate — as a program. Every child carries the INNER mark unless a case
    asks otherwise (a marked gate never runs the spawning cases) and its depth
    (a gate too deep refuses to run at all); the outermost gate starts each
    child in its own process group and ends the whole group on a timeout, so a
    runaway child cannot outlive the check that started it."""
    global LAST_CHILD
    script = kw.pop("script", MODULE)
    env = dict(kw.pop("env", None) or os.environ)
    if kw.pop("inner", True):
        env["EXO_GATE_PATHS_INNER"] = "1"      # every child carries the mark
    else:
        env.pop("EXO_GATE_PATHS_INNER", None)
    env["EXO_GATE_PATHS_DEPTH"] = str(DEPTH + 1)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    timeout = kw.pop("timeout", 120)
    cmd = [PY, str(script)] + [str(a) for a in args]
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    elif DEPTH == 0:
        group["start_new_session"] = True     # the child and all it starts share one group
    started = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **group)
    proc.exo_started = started               # the survivors walk keys on it (Windows)
    LAST_CHILD = proc
    try:
        out, err = proc.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        end_child(proc)
        out, err = proc.communicate()
        err = err + ("\ngate-paths: the child ran past %d s and was ended with everything "
                     "it started" % timeout).encode("utf-8")
    err = err.decode("utf-8", "replace").strip()
    if DEPTH > 0:                              # a refusal deep down is reported all the way up
        for line in err.splitlines():
            if line.startswith("gate-paths: recursion"):
                sys.stderr.write(line + "\n")
    return (proc.returncode, out.decode("utf-8", "replace").strip(), err)


def end_child(proc):
    """End a child of this gate. The outermost gate ends the child's whole
    process group; a nested gate ends only its direct child and leaves the
    sweep to the outermost gate's survivors check."""
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif DEPTH == 0:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)   # its own session: pgid == pid
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def cim_epoch(value):
    """A CIM CreationDate the way ConvertTo-Json writes it — '/Date(<ms>)/' on
    PowerShell 5, an ISO string on 7 — as epoch seconds; None when unreadable."""
    if not value:
        return None
    m = re.search(r"Date\((-?\d+)\)", str(value))
    if m:
        return int(m.group(1)) / 1000.0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def process_rows_nt():
    """Every process on this Windows machine as (pid, parent pid, created):
    the listing the survivors walk reads. Raises where the question could not
    be asked."""
    ps = ("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate "
          "| ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    text = r.stdout.decode("utf-8", "replace").strip()
    data = json.loads(text) if text else []
    if isinstance(data, dict):                 # one process comes back bare, not in a list
        data = [data]
    rows = []
    for row in data:
        try:
            rows.append((int(row.get("ProcessId")), int(row.get("ParentProcessId") or 0),
                         cim_epoch(row.get("CreationDate"))))
        except (TypeError, ValueError):
            continue
    return rows


def descendants(rows, root, own, started=None):
    """The processes under `root` in a (pid, parent, created) listing: its
    children, their children and so on — a dead root's children still name it
    as their parent. Never this process (`own`) or anything above it (the
    shell that called the gate, the app above that), and never a process that
    began before the root was started: that is a reused pid, not a child. A
    match is by lineage only, never by what a command line says — a query
    whose own text names the gate, or the shell that typed the command, is
    not a survivor."""
    parent = dict((pid, ppid) for pid, ppid, _ in rows)
    above = set([own])
    p = parent.get(own)
    while p and p not in above:
        above.add(p)
        p = parent.get(p)
    found, frontier = [], set([root])
    while frontier:
        nxt = set()
        for pid, ppid, created in rows:
            if ppid not in frontier or pid in found or pid == root or pid in above:
                continue
            if started is not None and created is not None and created < started - 2:
                continue
            found.append(pid)
            nxt.add(pid)
        frontier = nxt
    return sorted(found)


def survivors(proc):
    """Processes still alive from a child the outermost gate started: on POSIX
    the members of the child's own process group; on Windows the child's
    descendants by lineage (there is no group to ask), started no earlier than
    the child. None when the question could not be asked."""
    try:
        if os.name == "nt":
            return descendants(process_rows_nt(), proc.pid, os.getpid(),
                               getattr(proc, "exo_started", None))
        r = subprocess.run(["pgrep", "-g", str(proc.pid)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    return sorted(int(x) for x in r.stdout.decode("utf-8", "replace").split() if x.isdigit())


def sweep(proc):
    """Survivors of a child, ended; the list of what was found."""
    found = survivors(proc)
    if found:
        found = [pid for pid in found if pid != os.getpid()]   # never this gate
        if os.name == "nt":
            for pid in found:
                subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            for pid in found:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
    return found


def fixture_dirs():
    """The fixture worlds of every gate run on this machine right now."""
    return sorted(p.name for p in Path(tempfile.gettempdir()).glob("exo-paths-gate-*"))


def stray_fixtures(before):
    """Fixture worlds that appeared since `before` and were not removed: a
    child that was ended could not clean up. Removed here, and returned."""
    left = [n for n in fixture_dirs() if n not in before]
    for name in left:
        shutil.rmtree(str(Path(tempfile.gettempdir()) / name), ignore_errors=True)
    return left


def real_acks():
    return sorted(p.name for p in REAL_HUB.glob("paths-ack-*.json")) if REAL_HUB.is_dir() else []


def gate_copy(hub, text=None):
    """A copy of the module and of this gate in <hub>/tools/, or of a given
    text of the gate; the path of the copied gate."""
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(MODULE), str(hub / "tools" / "exo_paths.py"))
    target = hub / "tools" / "gate-paths.py"
    if text is None:
        shutil.copyfile(str(Path(__file__).resolve()), str(target))
    else:
        write(target, text)
    return target


# ---------------------------------------------------------------------------
# the module under test
# ---------------------------------------------------------------------------

def load_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("exo_paths_under_test", str(MODULE))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def res(**kw):
    """paths(), with every record kept for P10."""
    record = mod.paths(**kw)
    SEEN.append(record)
    return record


# ---------------------------------------------------------------------------
# R — rails
# ---------------------------------------------------------------------------

def case_rails():
    case("R", "rails: fixtures outside the hub, no repository metadata inside it")
    inside_gate = str(SCRATCH).startswith(str(HERE) + os.sep)
    inside_hub = str(SCRATCH).startswith(str(REAL_HUB) + os.sep)
    ok("the fixture world is outside the folder holding this gate", not inside_gate, SCRATCH)
    ok("the fixture world is outside the hub two levels above it", not inside_hub, SCRATCH)
    ok("the module under test is beside this gate", MODULE.is_file(), MODULE)
    ok("no repository metadata sits in this gate's own folder", not git_names_under(HERE),
       git_names_under(HERE))
    # The hub this gate runs under is SNAPSHOT here and proved unchanged at the
    # end of the run (case_rails_close): a program tree that is a checkout of
    # the program has repository names of its own, and a gate never asserts a
    # live folder absent — it proves it created nothing there.
    global HUB_TOP_AT_START
    HUB_TOP_AT_START = hub_git_names()


def hub_git_names():
    return sorted(p.name for p in REAL_HUB.iterdir() if p.name in GIT_NAMES) \
        if REAL_HUB.is_dir() else []


def case_rails_close():
    case("R", "rails, closed: the hub's own repository names are as this gate found them")
    top = hub_git_names()
    ok("none appeared at the top of the hub this gate runs under, and none went (%s)"
       % (", ".join(HUB_TOP_AT_START or []) or "it had none"),
       HUB_TOP_AT_START is not None and top == HUB_TOP_AT_START,
       "at the start %s · now %s" % (HUB_TOP_AT_START, top))


def git_names_under(root, limit=4000):
    found, seen = [], 0
    for base, dirs, files in os.walk(str(root)):
        seen += 1
        if seen > limit:
            break
        for name in list(dirs) + list(files):
            if name in GIT_NAMES:
                found.append(str(Path(base, name)))
    return found


# ---------------------------------------------------------------------------
# P1 — live equality with the older layout, read-only
# ---------------------------------------------------------------------------

def case_live():
    case("P1", "live equality with the older layout — read-only")
    if NO_LIVE:
        skip("--no-live was given, so this machine was not read.")
        return None
    older = REAL_HOME / OLDER_DIRNAME / "machine.json"
    if not older.is_file():
        skip("this machine has no record in the older layout's folder.")
        return None
    try:
        with io.open(str(older), encoding="utf-8") as fh:
            record = json.load(fh)
    except Exception as exc:
        ok("this machine's record reads as JSON", False, exc)
        return None
    roots = record.get("roots") or {}
    if roots.get("orchestrator"):
        old_hub = Path(str(roots["orchestrator"])).expanduser()
    elif (HERE.parent / "tools").is_dir() and HERE.name == "tools":
        old_hub = HERE.parent
    else:
        skip("the record names no hub folder, so there is nothing to compare with.")
        return None
    tool = old_hub / "tools" / "i-am.py"
    if not tool.is_file():
        skip("no installed tool to resolve from at %s." % tool)
        return None
    old_sync = REAL_HOME / OLDER_DIRNAME
    old_brain = old_sync if (old_sync / ".git").exists() else None
    old_name = str(record.get("name", "") or "").strip().lower() or "unknown"

    with using_home():                       # the real home, and no named file
        got = res(tool_file=tool)

    ok("the machine file is the one the older tools read", same(got["machine_file"], older))
    ok("the hub is the one the record names", same(got["hub"], old_hub),
       "%s vs %s" % (got["hub"], old_hub))
    ok("the sync package is the older layout's folder", same(got["sync_dir"], old_sync),
       got["sync_dir"])
    ok("the brain clone is that same folder", same(got["brain"], old_brain), got["brain"])
    ok("the layout reads as the older one", got["layout"] == "legacy", got["layout"])
    ok("and it was settled by default, not by a record", got["layout_source"] == "default",
       got["layout_source"])
    ok("the hub is not a repository", got["hub_is_git"] is False)
    ok("no partition is recorded", got["partition"] is None, got["partition"])
    ok("the machine name matches the record", got["machine"] == old_name, got["machine"])
    ok("this machine is bootstrapped", got["bootstrapped"] is True)
    ok("nothing is reported wrong on this machine", not got["problems"], got["problems"])
    return got


# ---------------------------------------------------------------------------
# P2 — a program tree, with no older folder anywhere
# ---------------------------------------------------------------------------

def case_program_tree():
    case("P2", "a program tree, no older folder present")
    w = world("p2")
    home = world("p2/home")
    hub = program_tree(w / "hub")
    tool = hub / "tools" / "exo_paths.py"

    with using_home(home):
        got = res(tool_file=tool)
    ok("the layout is a program tree", got["layout"] == "program-tree", got["layout"])
    ok("and the folders said so, not a record", got["layout_source"] == "structure",
       got["layout_source"])
    ok("the sync package is the hub's own sync folder", same(got["sync_dir"], hub / "sync"),
       got["sync_dir"])
    ok("no brain clone is known yet", got["brain"] is None, got["brain"])
    ok("no machine file was found", got["machine_file"] is None, got["machine_file"])
    ok("so this machine is not bootstrapped", got["bootstrapped"] is False)
    ok("the machine has no name yet", got["machine"] == "unknown", got["machine"])
    ok("the hub is the folder above the tool", same(got["hub"], hub), got["hub"])
    ok("no folders are recorded", got["roots"] == {}, got["roots"])
    ok("no templates folder is claimed", got["templates_dir"] is None, got["templates_dir"])
    ok("nothing is reported wrong", not got["problems"], got["problems"])

    brain = w / "brain"
    brain.mkdir(exist_ok=True)
    (hub / "templates").mkdir(exist_ok=True)
    record_file(hub / "machine.json", name="alpha", layout="program-tree", partition="v1",
                roots={"brain": str(brain)})
    with using_home(home):
        got = res(tool_file=tool)
    ok("with a record, the layout comes from the record",
       got["layout"] == "program-tree" and got["layout_source"] == "record", got["layout_source"])
    ok("the machine file is the hub's own", same(got["machine_file"], hub / "machine.json"))
    ok("the machine is named as recorded", got["machine"] == "alpha", got["machine"])
    ok("the brain clone is where the record says", same(got["brain"], brain), got["brain"])
    ok("the partition is the recorded word", got["partition"] == "v1", got["partition"])
    ok("the templates folder is found", same(got["templates_dir"], hub / "templates"),
       got["templates_dir"])
    ok("this machine is bootstrapped", got["bootstrapped"] is True)
    ok("nothing is reported wrong", not got["problems"], got["problems"])

    other = w / "elsewhere-sync"
    write(other / "sync.py", DUMMY_SYNC)
    record_file(hub / "machine.json", name="alpha", layout="program-tree",
                roots={"brain": str(brain), "sync": str(other), "orchestrator": str(hub)})
    with using_home(home):
        got = res(tool_file=tool)
    ok("a recorded sync folder wins over the layout's default", same(got["sync_dir"], other),
       got["sync_dir"])
    ok("and the recorded hub is used", same(got["hub"], hub), got["hub"])
    ok("still nothing reported wrong", not got["problems"], got["problems"])

    # What a tool that wants the answer has to write: two lines, and no more.
    consumer = write(hub / "tools" / "a-consumer.py",
                     "import sys\n"
                     "from pathlib import Path\n"
                     "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
                     "from exo_paths import paths, need\n"
                     "\n"
                     "need(1)\n"
                     "P = paths(tool_file=__file__)\n"
                     'print(P["hub"])\n'
                     'print(P["sync_dir"])\n')
    with using_home(home):
        code, out, err = cli(script=consumer)
    lines = out.splitlines()
    ok("a tool beside it picks it up in two lines and gets the same answer",
       code == 0 and len(lines) == 2 and same(lines[0], got["hub"])
       and same(lines[1], got["sync_dir"]), err or out[:160])


# ---------------------------------------------------------------------------
# P3 — the older layout as a fixture
# ---------------------------------------------------------------------------

def case_older_fixture():
    case("P3", "an older-layout fixture: every key as the table says")
    w = world("p3")
    home = world("p3/home")
    hub = w / "hub"
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    folder = older_home(home, name="alpha", roots={"orchestrator": str(hub)})

    with using_home(home):
        got = res(tool_file=hub / "tools" / "anything.py")
    ok("the machine file is the one inside the brain clone",
       same(got["machine_file"], folder / "machine.json"), got["machine_file"])
    ok("the hub is the folder the record names", same(got["hub"], hub), got["hub"])
    ok("the sync package is the brain clone", same(got["sync_dir"], folder), got["sync_dir"])
    ok("the brain clone is the folder holding the record", same(got["brain"], folder),
       got["brain"])
    ok("the layout is the older one, by default", got["layout"] == "legacy"
       and got["layout_source"] == "default", got["layout_source"])
    ok("the hub is not a repository", got["hub_is_git"] is False)
    ok("no partition, no templates", got["partition"] is None and got["templates_dir"] is None)
    ok("the machine is named as recorded", got["machine"] == "alpha", got["machine"])
    ok("it is bootstrapped, with nothing reported wrong",
       got["bootstrapped"] is True and not got["problems"], got["problems"])

    record_file(folder / "machine.json", name="alpha", layout="legacy",
                roots={"orchestrator": str(hub)})
    with using_home(home):
        got = res(tool_file=hub / "tools" / "anything.py")
    ok("a record naming the older layout agrees with the folders",
       got["layout"] == "legacy" and got["layout_source"] == "record" and not got["problems"],
       got["problems"])

    loose = w / "loose"
    (loose / "tools").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(MODULE), str(loose / "tools" / "exo_paths.py"))
    with using_home(home):
        code, out, err = cli("--json", script=loose / "tools" / "exo_paths.py")
    parsed = json.loads(out) if out.startswith("{") else {}
    ok("run with no arguments from another folder, the CLI answers", code == 0 and parsed,
       err or out[:200])
    ok("and the record's hub still wins over where the module sits",
       same(parsed.get("hub"), hub), parsed.get("hub"))
    ok("with the record found through the home folder",
       same(parsed.get("machine_file"), folder / "machine.json"), parsed.get("machine_file"))


# ---------------------------------------------------------------------------
# P4 — whose identity wins
# ---------------------------------------------------------------------------

def case_identity():
    case("P4", "a hub's own record beats the home one; a named file beats both")
    w = world("p4")
    home = world("p4/home")
    hub = w / "hub"
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    older_home(home, name="alpha", roots={})
    record_file(hub / "machine.json", name="beta", roots={})

    with using_home(home):
        got = res(tool_file=hub / "tools" / "anything.py")
    ok("the hub's own record is the one read", same(got["machine_file"], hub / "machine.json"),
       got["machine_file"])
    ok("so the machine is the hub's", got["machine"] == "beta", got["machine"])

    third_hub = w / "third-hub"
    third_hub.mkdir(exist_ok=True)
    named = record_file(w / "elsewhere" / "machine.json", name="gamma",
                        roots={"orchestrator": str(third_hub)})
    with using_home(home, machine_json=named):
        got = res(tool_file=hub / "tools" / "anything.py")
    ok("a named machine file beats both", same(got["machine_file"], named), got["machine_file"])
    ok("its name is the machine's", got["machine"] == "gamma", got["machine"])
    ok("and the hub it names is the hub", same(got["hub"], third_hub), got["hub"])

    with using_home(home, machine_json=w / "no-such-file.json"):
        got = res(tool_file=hub / "tools" / "anything.py")
    ok("a named file that is not there does not become another machine's record",
       same(got["machine_file"], hub / "machine.json"), got["machine_file"])
    ok("and it is said plainly", any("is not a file" in p for p in got["problems"]),
       got["problems"])


# ---------------------------------------------------------------------------
# P5 — record and folders disagreeing
# ---------------------------------------------------------------------------

def case_disagreement():
    case("P5", "record and folders disagreeing, both ways")
    w = world("p5")
    home = world("p5/home")

    hub = program_tree(w / "hub-a")
    record_file(hub / "machine.json", name="alpha", layout="legacy", roots={})
    tool = hub / "tools" / "exo_paths.py"
    with using_home(home):
        got = res(tool_file=tool)
    ok("a record saying the older layout on a program tree is reported",
       len(got["problems"]) == 1, got["problems"])
    ok("the record still wins, and says so",
       got["layout"] == "legacy" and got["layout_source"] == "record", got["layout_source"])
    ok("the sentence names the machine file and both shapes",
       got["problems"] and "machine.json" in got["problems"][0]
       and "program tree" in got["problems"][0], got["problems"])
    raised = None
    try:
        with using_home(home):
            mod.paths(tool_file=tool, strict=True)
    except mod.ExoPathsStop as exc:
        raised = str(exc)
    ok("strict raises the stop, with that same sentence", raised == (got["problems"][0]
       if got["problems"] else None), raised)
    with using_home(home):
        code, out, err = cli("--check", "--tool-file", tool)
    ok("--check prints one STOP line and exits 2",
       code == 2 and out.startswith("STOP: ") and len(out.splitlines()) == 1,
       "exit %d · %s" % (code, out))
    ok("the line carries the problem itself", out == "STOP: " + (got["problems"][0] if
       got["problems"] else ""), out)

    hub_b = w / "hub-b"
    (hub_b / "tools").mkdir(parents=True, exist_ok=True)
    record_file(hub_b / "machine.json", name="alpha", layout="program-tree", roots={})
    with using_home(home):
        got = res(tool_file=hub_b / "tools" / "anything.py")
    ok("a record saying program tree with no sync entry point is reported",
       len(got["problems"]) == 1, got["problems"])
    ok("the record still wins", got["layout"] == "program-tree"
       and got["layout_source"] == "record", got["layout_source"])
    ok("the sentence names the missing entry point",
       got["problems"] and "sync/sync.py" in got["problems"][0], got["problems"])
    raised = None
    try:
        with using_home(home):
            mod.paths(tool_file=hub_b / "tools" / "anything.py", strict=True)
    except mod.ExoPathsStop as exc:
        raised = str(exc)
    ok("strict raises here too", bool(raised), raised)
    with using_home(home):
        code, out, err = cli("--check", "--tool-file", hub_b / "tools" / "anything.py")
    ok("and --check exits 2 the same way", code == 2 and out.startswith("STOP: "),
       "exit %d · %s" % (code, out))

    hub_c = program_tree(w / "hub-c")
    record_file(hub_c / "machine.json", name="alpha", layout="program-tree", roots={})
    with using_home(home):
        got = res(tool_file=hub_c / "tools" / "exo_paths.py")
    ok("a record that agrees with the folders reports nothing", not got["problems"],
       got["problems"])


# ---------------------------------------------------------------------------
# P6 — damage
# ---------------------------------------------------------------------------

def case_damage():
    case("P6", "damage: never an exception, always a sentence or a sane default")
    w = world("p6")
    home = world("p6/home")
    hub = w / "hub"
    (hub / "tools").mkdir(parents=True, exist_ok=True)
    tool = hub / "tools" / "anything.py"
    mfile = hub / "machine.json"

    def resolve():
        with using_home(home):
            return res(tool_file=tool)

    for label, text in (("an empty file", ""),
                        ("invalid JSON", "{"),
                        ("a JSON list", "[1, 2, 3]"),
                        ("a bare number", "7"),
                        ("text that is not JSON at all", "the notes of a session\n")):
        write(mfile, text)
        try:
            got = resolve()
            raised = None
        except Exception as exc:
            got, raised = None, repr(exc)
        ok("%s: no exception" % label, raised is None, raised)
        if got is None:
            continue
        ok("%s: one sentence naming the file" % label,
           len(got["problems"]) == 1 and "machine.json" in got["problems"][0], got["problems"])
        ok("%s: not bootstrapped, and no name invented" % label,
           got["bootstrapped"] is False and got["machine"] == "unknown", got["machine"])
        ok("%s: the hub still resolves" % label, same(got["hub"], hub), got["hub"])
        ok("%s: the file it could not read is still named" % label,
           same(got["machine_file"], mfile), got["machine_file"])

    record_file(mfile, name="alpha")
    got = resolve()
    ok("a record with no folders: an empty set, and nothing reported",
       got["roots"] == {} and not got["problems"], got["problems"])
    ok("and it still counts as bootstrapped", got["bootstrapped"] is True)

    record_file(mfile, name="alpha", roots=["a", "b"])
    got = resolve()
    ok("folders recorded as a list: ignored, and said plainly",
       got["roots"] == {} and len(got["problems"]) == 1, got["problems"])

    record_file(mfile, name="alpha", roots={"orchestrator": 5})
    got = resolve()
    ok("a folder recorded as a number: ignored, and said plainly",
       len(got["problems"]) == 1 and same(got["hub"], hub), got["problems"])

    record_file(mfile, name="alpha", roots={}, layout="halfway")
    got = resolve()
    ok("an unknown layout word: the folders are read instead, and it is said",
       got["layout"] == "legacy" and got["layout_source"] == "default"
       and len(got["problems"]) == 1, got["problems"])

    record_file(mfile, name="alpha", roots={}, partition={"mode": "on"})
    got = resolve()
    ok("a partition that is not a word: ignored, and said plainly",
       got["partition"] is None and len(got["problems"]) == 1, got["problems"])

    record_file(mfile, name="  ALPHA  ", roots={})
    got = resolve()
    ok("a name with space and capitals is read plainly", got["machine"] == "alpha",
       got["machine"])

    write(mfile, "{")
    with using_home(home):
        code, out, err = cli("--json", "--tool-file", tool)
    parsed = json.loads(out) if out.startswith("{") else {}
    ok("--json over a damaged record still prints the record and exits 0",
       code == 0 and parsed.get("problems"), "exit %d · %s" % (code, out[:120]))
    ok("with every path as text", isinstance(parsed.get("hub"), str), type(parsed.get("hub")))

    write(hub / "templates", "a file where a folder would be\n")
    got = resolve()
    ok("a file named like the templates folder is not claimed as one",
       got["templates_dir"] is None, got["templates_dir"])


# ---------------------------------------------------------------------------
# P7 — the home folder is read at call time
# ---------------------------------------------------------------------------

def case_call_time():
    case("P7", "two homes, two answers, one process")
    w = world("p7")
    plain = w / "plainhub"
    (plain / "tools").mkdir(parents=True, exist_ok=True)
    tool = plain / "tools" / "anything.py"

    home_a, home_b = world("p7/a"), world("p7/b")
    hub_a, hub_b = w / "hub-a", w / "hub-b"
    hub_a.mkdir(exist_ok=True)
    hub_b.mkdir(exist_ok=True)
    folder_a = older_home(home_a, name="alpha", roots={"orchestrator": str(hub_a)})
    folder_b = older_home(home_b, name="beta", roots={"orchestrator": str(hub_b)})

    with using_home(home_a):
        first = res(tool_file=tool)
    with using_home(home_b):
        second = res(tool_file=tool)
    with using_home(home_a):
        third = res(tool_file=tool)

    ok("the first home answers with its own machine", first["machine"] == "alpha"
       and same(first["brain"], folder_a), first["machine"])
    ok("the second home answers with its own", second["machine"] == "beta"
       and same(second["brain"], folder_b), second["machine"])
    ok("and the first home answers the same way again", third["machine"] == "alpha"
       and same(third["hub"], hub_a), third["machine"])
    ok("nothing was cached between the calls", first["hub"] != second["hub"],
       "%s vs %s" % (first["hub"], second["hub"]))

    # The module was imported long before any of this, so a file named now can
    # only be honoured if the environment is read at call time.
    named = record_file(w / "named" / "machine.json", name="gamma", roots={})
    with using_home(home_a, machine_json=named):
        after = res(tool_file=tool)
    with using_home(home_a):
        back = res(tool_file=tool)
    ok("a file named after the module was imported is still honoured",
       after["machine"] == "gamma", after["machine"])
    ok("and dropping it goes back to the home's own record", back["machine"] == "alpha",
       back["machine"])


# ---------------------------------------------------------------------------
# P8 — no side effects
# ---------------------------------------------------------------------------

def cache_entries(folder):
    """The bytecode cache beside a module as it stands right now: name →
    (size, mtime) per entry; empty when there is no cache folder. Compared
    before and after a run — never asserted absent, since any machine that
    has run a tool from that folder already has one."""
    cache = Path(folder) / "__pycache__"
    if not cache.is_dir():
        return {}
    out = {}
    for p in cache.iterdir():
        try:
            st = p.stat()
            out[p.name] = (st.st_size, int(st.st_mtime))
        except OSError:
            out[p.name] = ("unreadable",)
    return out


def case_no_side_effects():
    case("P8", "no side effects: the tree is byte-identical afterwards")
    cache_before = cache_entries(MODULE.parent)
    w = world("p8")
    home = world("p8/home")
    hub = program_tree(w / "hub")
    older = older_home(home, name="alpha", roots={"orchestrator": str(hub)})
    record_file(hub / "machine.json", name="alpha", layout="program-tree", roots={})

    probe = write(SCRATCH / "probe.py",
                  "import importlib.util, sys\n"
                  "spec = importlib.util.spec_from_file_location('probe_target', sys.argv[1])\n"
                  "module = importlib.util.module_from_spec(spec)\n"
                  "spec.loader.exec_module(module)\n")

    before = snapshot(w)
    hub_before = set(p.name for p in REAL_HUB.iterdir()) if REAL_HUB.is_dir() else set()

    with using_home(home):
        code, out, err = cli(MODULE, script=probe)
    ok("importing the module alone prints nothing at all",
       code == 0 and out == "" and err == "", "exit %d · %s%s" % (code, out[:80], err[:80]))

    with using_home(home):
        for kw in ({}, {"tool_file": hub / "tools" / "exo_paths.py"}, {"hub": hub},
                   {"tool_file": older / "sync.py"}):
            res(**kw)
        cli("--json", "--tool-file", hub / "tools" / "exo_paths.py")
        cli("--check")
        cli("--json", script=hub / "tools" / "exo_paths.py")

    after = snapshot(w)
    added = sorted(set(after) - set(before))
    gone = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    ok("nothing was added to the fixture tree", not added, added[:6])
    ok("nothing was removed from it", not gone, gone[:6])
    ok("and not one byte changed", not changed, changed[:6])

    hub_after = set(p.name for p in REAL_HUB.iterdir()) if REAL_HUB.is_dir() else set()
    new_names = sorted(n for n in (hub_after - hub_before)
                       if n.startswith("paths-ack-") or n == "machine.json"
                       or n.startswith("exo_paths"))
    ok("no acknowledgment and no machine file appeared in the live hub", not new_names,
       new_names)

    code, out, err = cli("--check", "--hub", hub)
    cache_after = cache_entries(MODULE.parent)
    mine = lambda d: dict((k, v) for k, v in d.items() if k.startswith("exo_paths"))
    if cache_before:
        note("the module's folder already had a bytecode cache (%d entries) — compared, not "
             "asserted absent" % len(cache_before))
    ok("importing and running writes no bytecode cache for the module beside it",
       mine(cache_after) == mine(cache_before), "exit %d · %s" % (code, sorted(mine(cache_after))))
    ok("and creates no cache folder where there was none",
       bool(cache_before) or not cache_after, sorted(cache_after)[:6])
    ok("and none inside the fixture tree", not (hub / "tools" / "__pycache__").exists())
    ok("no repository metadata was created in this gate's own folder",
       not git_names_under(HERE), git_names_under(HERE))


# ---------------------------------------------------------------------------
# P9 — one literal
# ---------------------------------------------------------------------------

def case_one_literal():
    case("P9", "the older folder's name appears exactly once in the module's code")
    source = io.open(str(MODULE), encoding="utf-8").read()
    kept = []
    with io.open(str(MODULE), "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type != tokenize.COMMENT:
                kept.append(tok.string)
    code_text = "\n".join(kept)
    in_code = code_text.count(OLDER_DIRNAME)
    whole = source.count(OLDER_DIRNAME)
    ok("exactly once in the code, comments set aside", in_code == 1, "found %d" % in_code)
    ok("and not repeated in the comments either", whole == 1, "found %d in the whole file" % whole)
    ok("it is held in a named constant", getattr(mod, "LEGACY_SYNC_DIRNAME", None) == OLDER_DIRNAME,
       getattr(mod, "LEGACY_SYNC_DIRNAME", None))


# ---------------------------------------------------------------------------
# P10 — the record itself
# ---------------------------------------------------------------------------

PATH_KEYS = ("hub", "sync_dir", "brain", "machine_file", "templates_dir")


def case_record():
    case("P10", "the record: every key every time, the version, the version gate")
    missing, wrong = [], []
    for record in SEEN:
        for key in mod.RECORD_KEYS:
            if key not in record:
                missing.append(key)
        for key in PATH_KEYS:
            value = record.get(key)
            if not (value is None or isinstance(value, Path)):
                wrong.append("%s=%r" % (key, value))
        if not isinstance(record.get("roots"), dict):
            wrong.append("roots=%r" % record.get("roots"))
        if not isinstance(record.get("problems"), list):
            wrong.append("problems=%r" % record.get("problems"))
        if not all(isinstance(p, str) for p in record.get("problems", [])):
            wrong.append("a problem that is not a sentence")
        if record.get("layout") not in ("legacy", "program-tree"):
            wrong.append("layout=%r" % record.get("layout"))
        if record.get("layout_source") not in ("record", "structure", "default"):
            wrong.append("layout_source=%r" % record.get("layout_source"))
        for key in ("bootstrapped", "hub_is_git"):
            if not isinstance(record.get(key), bool):
                wrong.append("%s=%r" % (key, record.get(key)))
        if not isinstance(record.get("machine"), str) or not record.get("machine"):
            wrong.append("machine=%r" % record.get("machine"))
    ok("every case carried every key of the record (%d records)" % len(SEEN), not missing,
       sorted(set(missing)))
    ok("and every value is of the kind the contract promises", not wrong, sorted(set(wrong))[:6])
    ok("the hub is always a path, never None",
       all(isinstance(r.get("hub"), Path) for r in SEEN))
    ok("the version is the whole number 1", mod.API == 1 and isinstance(mod.API, int), mod.API)

    ok("a caller that needs this version passes", mod.need(1) == 1)
    raised = None
    try:
        mod.need(2)
    except mod.ExoPathsStop as exc:
        raised = str(exc)
    except Exception as exc:
        raised = "the wrong kind of error: %r" % exc
    ok("a caller that needs a newer one is stopped", isinstance(raised, str)
       and "2" in (raised or "") and "1" in (raised or ""), raised)
    ok("in one plain line, with no traceback needed",
       bool(raised) and len(raised.splitlines()) == 1 and raised.endswith("."), raised)


# ---------------------------------------------------------------------------
# P11 — the repository marker, as a folder and as a file
# ---------------------------------------------------------------------------

def case_marker():
    case("P11", "a repository marker as a folder and as a file")
    w = world("p11")
    home = world("p11/home")
    plain, folder_hub, file_hub = w / "plain", w / "folder-hub", w / "file-hub"
    for h in (plain, folder_hub, file_hub):
        (h / "tools").mkdir(parents=True, exist_ok=True)
    (folder_hub / ".git").mkdir(exist_ok=True)
    write(file_hub / ".git", "gitdir: ../elsewhere/repository\n")

    for label, hub, want in (("no marker", plain, False),
                             ("a marker folder", folder_hub, True),
                             ("a marker file", file_hub, True)):
        with using_home(home):
            got = res(tool_file=hub / "tools" / "anything.py")
        ok("%s: the hub reads as a repository = %s" % (label, want),
           got["hub_is_git"] is want, got["hub_is_git"])


# ---------------------------------------------------------------------------
# ACK — the acknowledgment
# ---------------------------------------------------------------------------

def ack_allowed():
    """Only an installed copy may write it: this gate sitting in the hub's
    tools folder, beside the module it is proving."""
    return HERE.name == "tools" and (HERE / "exo_paths.py").is_file()


def ack_hub():
    """The hub this installed copy belongs to: the folder holding tools/.
    Never the folder a record names — an acknowledgment says "the module works
    HERE", so it is written beside the copy that was proved."""
    return HERE.parent


def write_ack(hub, passed, total, green_cases):
    machine = mod.paths(tool_file=HERE / "gate-paths.py")["machine"]
    payload = {"machine": machine,
               "module": "tools/exo_paths.py",
               "sha256": sha256_of(MODULE),
               "api": mod.API,
               "cases_passed": sorted(green_cases),
               "checks": total,
               "passed": passed,
               "written": datetime.now().astimezone().replace(microsecond=0).isoformat()}
    handle, temporary = tempfile.mkstemp(prefix="paths-ack-", suffix=".tmp", dir=str(hub))
    with io.open(handle, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    target = Path(hub) / ("paths-ack-%s.json" % machine)
    os.replace(temporary, str(target))
    return target


def case_ack():
    case("ACK", "the acknowledgment: refused by a copy outside tools/, written from tools/")
    # The refusal is proved against a COPY of this gate in a folder not named
    # tools — never against this file. An installed copy is allowed to write,
    # and a child that is allowed to write runs the whole gate: that was the
    # runaway. The copy refuses at once wherever this gate itself is running.
    w = world("ack")
    copy = w / "copy"
    copy.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(MODULE), str(copy / "exo_paths.py"))
    refusal_copy = copy / "gate-paths.py"
    shutil.copyfile(str(Path(__file__).resolve()), str(refusal_copy))
    code, out, err = cli("--ack", "--no-live", script=refusal_copy)
    said = (out + " " + err).lower()
    ok("a copy outside tools/ refuses to write the acknowledgment",
       code == 2 and "acknowledgment" in said, "exit %d · %s" % (code, (out + err)[:160]))
    ok("and says where it is running from instead", str(copy) in (out + err), (out + err)[:160])

    if NO_LIVE or not LIVE_RAN:
        # The acknowledgment certifies the live case, and is written only after
        # it: a machine that could not run it (no record in the older layout's
        # folder) has nothing to acknowledge, and the writing half says so.
        skip("the writing half needs the live case, which %s."
             % ("was not asked for" if NO_LIVE else "this machine could not run"))
        return
    hub = w / "hub"
    gate_copy(hub)
    code, out, err = cli("--ack", script=hub / "tools" / "gate-paths.py", env=BASE_ENV)
    tail = out.strip().splitlines()[-1] if out.strip() else err[:160]
    ok("an installed copy runs green and writes it", code == 0, tail)
    machine = mod.paths(tool_file=HERE / "gate-paths.py")["machine"]
    target = hub / ("paths-ack-%s.json" % machine)
    ok("the acknowledgment is beside the hub, named for this machine", target.is_file(),
       sorted(p.name for p in hub.iterdir()))
    if not target.is_file():
        return
    payload = json.loads(io.open(str(target), encoding="utf-8").read())
    ok("it carries this machine, the module's fingerprint, the version and the count",
       payload.get("machine") == machine and payload.get("sha256") == sha256_of(MODULE)
       and payload.get("api") == mod.API and isinstance(payload.get("checks"), int),
       payload)
    ok("and the run it records was a whole one, the live case included",
       "P1" in (payload.get("cases_passed") or []), payload.get("cases_passed"))
    ok("no temporary file was left behind",
       not [p for p in hub.iterdir() if p.name.endswith(".tmp")],
       sorted(p.name for p in hub.iterdir()))


def case_from_tools():
    case("ACK2", "a copy run FROM a folder named tools with --ack: ends, one deep, nothing left")
    # This is the installed shape, the very command a person types in a hub's
    # tools folder, run inside a scratch hub: the copy is allowed to write, so
    # it runs every case of its own — its ACK proves the refusal against a
    # further copy and stops there. Only the outermost gate runs this case.
    hub = world("ack2") / "hub"
    gate = gate_copy(hub)
    before, acks = fixture_dirs(), real_acks()
    args = ["--ack"] + (["--no-live"] if NO_LIVE else [])
    started = time.monotonic()
    code, out, err = cli(*args, script=gate, env=BASE_ENV, inner=False)
    elapsed = time.monotonic() - started
    tail = out.strip().splitlines()[-1] if out.strip() else err[:160]
    ok("it ends on its own, green", code == 0, "exit %d · %s" % (code, tail))
    ok("well inside the timeout", 0 <= code and elapsed < 60, "%.1f s" % elapsed)
    ok("it ran its own acknowledgment case, refusal proved against a further copy",
       "a copy outside tools/ refuses to write the acknowledgment" in out, tail)
    ok("and did not run the spawning cases again — those are the outermost gate's alone",
       "── ACK2" not in out and "── ACK3" not in out, out[-200:])
    left = sweep(LAST_CHILD)
    ok("no process from that run is still alive",
       left == [], "still running, now ended: %s" % left if left else "unknowable here")
    strays = stray_fixtures(before)
    ok("no fixture world was left behind", strays == [], strays)
    if not NO_LIVE and LIVE_RAN:
        machine = mod.paths(tool_file=HERE / "gate-paths.py")["machine"]
        ok("it wrote its acknowledgment into ITS hub", (hub / ("paths-ack-%s.json" % machine)).is_file(),
           sorted(p.name for p in hub.iterdir()))
    elif not NO_LIVE:
        skip("the copy writes its acknowledgment only after the live case, which this "
             "machine could not run.")
    ok("and nothing beside the real hub", real_acks() == acks, real_acks())


def case_runaway():
    case("ACK3", "the runaway shape, re-made on purpose: a gate that launches itself is stopped")
    # Two lines of this gate put back the way they were: the children carry no
    # INNER mark, and the refusal half runs THIS file instead of a copy. In a
    # folder named tools that gate is allowed to write, so its refusal half
    # runs the whole gate again, which runs it again — the depth guard ends
    # it three gates deep, and nothing is left running or on disk.
    text = io.open(str(Path(__file__).resolve()), encoding="utf-8").read()
    mark = 'env["EXO_GATE_PATHS_INNER"] = "1"' + "      # every child carries the mark"
    target = "script=" + "refusal_copy"           # built in two pieces so this line is not a hit
    ok("the two lines the mutation puts back are present, once each",
       text.count(mark) == 1 and text.count(target) == 1, (text.count(mark), text.count(target)))
    mutated = (text.replace(mark, "pass                                    # MUTATED: no mark")
                   .replace(target, "script=Path(__file__).resolve()"))
    hub = world("ack3") / "hub"
    gate = gate_copy(hub, mutated)
    before, acks = fixture_dirs(), real_acks()
    started = time.monotonic()
    code, out, err = cli("--ack", "--no-live", script=gate, env=BASE_ENV, inner=False)
    elapsed = time.monotonic() - started
    ok("the mutated gate does not come back green", code != 0, "exit %d" % code)
    ok("it stops on its own, well inside the timeout", 0 <= code and elapsed < 60,
       "%.1f s · exit %d" % (elapsed, code))
    ok("the depth guard is what stopped it, three gates deep", "gate-paths: recursion" in err,
       err[-300:])
    ok("and its own acknowledgment case is the one that failed", "FAIL  ACK · " in out, out[-300:])
    left = sweep(LAST_CHILD)
    ok("no process from that run is still alive",
       left == [], "still running, now ended: %s" % left if left else "unknowable here")
    strays = stray_fixtures(before)
    ok("no fixture world was left behind", strays == [], strays)
    ok("nothing was written beside the real hub", real_acks() == acks, real_acks())


def case_tree_walk():
    case("W1", "the survivors walk: a child's descendants only — never this gate, its shell, a reused pid")
    # A listing shaped like the real one: the app, the shell that typed the
    # command, this gate, the child it started (ended), what the child left
    # running, the query that asked, a reused pid, a stranger.
    own, started = 500, 1000.0
    rows = [(100, 1, 10.0),        # the app
            (200, 100, 20.0),      # the calling shell — its command line names the gate
            (500, 200, 30.0),      # this gate
            (600, 500, 1001.0),    # the child the gate started; ended, its pid dead
            (610, 600, 1002.0),    # what it left running
            (611, 610, 1003.0),    # and what that left running
            (700, 500, 1005.0),    # the survivors query itself: the gate's child, not the root's
            (800, 600, 900.0),     # names the root as parent but began before it: a reused pid
            (900, 3, 1004.0)]      # a stranger's process
    got = descendants(rows, 600, own, started)
    ok("finds the child's children and their children", got == [610, 611], got)
    ok("never this gate, the shell that called it, or the app above that",
       not set(got) & set([100, 200, 500]), got)
    ok("never the process that asked the question", 700 not in got, got)
    ok("never a process that began before the child did", 800 not in got, got)
    ok("with no start time known, age excludes nothing — the honest side",
       descendants(rows, 600, own, None) == [610, 611, 800], descendants(rows, 600, own, None))
    ok("a self-parented row cannot loop the walk",
       descendants(rows + [(999, 999, 1006.0)], 600, own, started) == [610, 611], "looped")
    ok("a shell whose parent chain loops cannot loop it either",
       descendants([(100, 200, 1.0), (200, 100, 1.0), (500, 200, 2.0), (600, 500, 1001.0),
                    (610, 600, 1002.0)], 600, own, started) == [610], "looped")
    ok("CIM dates in both spellings read as seconds",
       cim_epoch("/Date(1695480000123)/") == 1695480000.123
       and abs(cim_epoch("2026-09-23T08:15:00-07:00")
               - datetime.fromisoformat("2026-09-23T08:15:00-07:00").timestamp()) < 1
       and cim_epoch("") is None
       and cim_epoch("yesterday") is None,
       (cim_epoch("/Date(1695480000123)/"), cim_epoch("2026-09-23T08:15:00-07:00")))


# ---------------------------------------------------------------------------

def guarded(run_case):
    """One case never takes the run down. A module that raises where it promised
    not to is a failure of that case, and the count line still gets printed."""
    try:
        return run_case()
    except Exception as exc:
        ok("the case ran to its end", False, "%s stopped: %r" % (run_case.__name__, exc))
        return None


def main():
    global mod, REAL_HUB
    if DEPTH > MAX_DEPTH:
        sys.stderr.write("gate-paths: recursion — this run is %d gates deep and a gate launches "
                         "copies at most %d deep. Refusing to run.\n" % (DEPTH, MAX_DEPTH))
        return 3
    unknown = [a for a in ARGS if a not in ("--no-live", "--keep", "--ack")]
    if unknown:
        print("gate-paths: %s is not an option this gate knows." % unknown[0])
        return 2
    if not MODULE.is_file():
        print("gate-paths: there is no exo_paths.py beside this gate (%s)." % HERE)
        return 2
    if ACK and not ack_allowed():
        print("gate-paths: the acknowledgment is written only by the copy installed in the "
              "hub's tools folder, beside the module it proves. This one is running from %s."
              % HERE)
        return 2

    try:
        mod = load_module()
    except Exception as exc:
        print("gate-paths: the module beside this gate could not be imported — %r" % exc)
        return 1
    try:
        with using_home():
            REAL_HUB = Path(mod.paths(tool_file=HERE / "gate-paths.py")["hub"])
    except Exception as exc:
        print("gate-paths: the module raised while answering about this machine — %r" % exc)
        REAL_HUB = HERE.parent
        checks.append(False)
        fails.append("R · the module answers about this machine without raising")

    print("gate-paths — proof for exo_paths.py")
    print("  module   %s" % MODULE)
    print("  sha256   %s" % sha256_of(MODULE))
    print("  fixtures %s" % SCRATCH)

    guarded(case_rails)
    live = guarded(case_live)
    global LIVE_RAN
    LIVE_RAN = live is not None
    for run_case in (case_program_tree, case_older_fixture, case_identity, case_disagreement,
                     case_damage, case_call_time, case_no_side_effects, case_one_literal,
                     case_record, case_marker, case_tree_walk):
        guarded(run_case)
    if not INNER:
        guarded(case_ack)
    if not INNER and DEPTH == 0:
        guarded(case_from_tools)
        guarded(case_runaway)
    guarded(case_rails_close)

    print("\n===== GATE =====")
    for name in fails:
        print("  FAIL  %s" % name)
    passed = sum(1 for c in checks if c)
    green_cases = [n for n, (good, bad) in CASES.items() if good and not bad]
    if live is None and not NO_LIVE:
        print("  the live case had nothing to read on this machine")
    if KEEP:
        print("  kept: %s" % SCRATCH)
    else:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    if ACK and not fails and live is not None:
        try:
            where = write_ack(ack_hub(), passed, len(checks), green_cases)
            print("  acknowledged: %s" % where)
        except Exception as exc:
            print("  the acknowledgment could not be written: %s" % exc)
            return 1
    for line in SKIPPED:
        print("  SKIP  %s" % line)
    print("%d checks · %d passed · %d failed%s" % (len(checks), passed, len(fails),
                                                  (" · %d skipped" % len(SKIPPED))
                                                  if SKIPPED else ""))
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        RESULT = main()
    finally:                               # an early answer leaves no world behind either
        if not KEEP:
            shutil.rmtree(str(SCRATCH), ignore_errors=True)
    sys.exit(RESULT)
