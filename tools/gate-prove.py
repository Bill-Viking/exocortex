#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-prove.py — proof for prove-install.py, the one command that proves an install.

    python3 tools/gate-prove.py            every case
    python3 tools/gate-prove.py --keep     leave the fixture world behind to look at

It NEVER runs the real gates through the runner. Its world, under the system
temp folder, holds a fixture tools/ with a copy of the runner whose set is
four tiny stand-in gates this proof writes itself:

    gate-green.py    prints a count line with nothing failed, exits 0
    gate-red.py      prints a count line with one failure, exits 1, and leaves
                     the world it made in its temporary folder behind
    gate-sleeper.py  makes a world, starts a child that sleeps, then sleeps past
                     its limit
    gate-skips.py    says in one line that it cannot run on this layout, exits 0

Every stand-in carries a depth mark (EXO_GATE_PROVE_DEPTH) and refuses to run
past 1, so nothing here can start a proof inside a proof. The copy of the runner
differs from the real one ONLY in its set; the real runner is the one read by
the source case and by --list.

The cases:
  P0  the copy under test is the real runner, but for its set
  P1  the table: four rows, the right verdicts and numbers, the footer
  P2  the exit is 1 when anything is red or stopped
  P3  the sleeper is ended inside its limit, with the child it started —
      survivors 0, found by who started whom, never by a command line; every
      world a stand-in made is gone — done, failed or ended at its limit — and
      each ran in a temporary folder of its own under the system temp folder
  P4  --only runs one gate; a skip alone exits 0
  P5  --list on the REAL hub names every gate of the set, present or missing,
      and runs none: the hub's tools/ reads the same before and after
  P6  the runner's source: no shell string, no pattern over gate names, and
      never the acknowledgment flag
  P7  a second fixture set of three — a gate that stops with no count line, one
      that counts nothing, one that says a skip line and fails: all three are
      stopped, never green, never skipped; the stopped
      gate's last line is shown with the person's words and the home folder
      masked, and nothing the runner printed carries a private word
  P8  the rails: a stand-in refuses past depth 1; the runner refuses inside a
      proof run; no world of this proof is left in the temp folder

Stdlib only, Python 3.9-compatible, macOS, Linux and Windows.
"""
import ast
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
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent            # <hub>/tools
HUB = HERE.parent
RUNNER = HERE / "prove-install.py"
PY = sys.executable
KEEP = "--keep" in sys.argv[1:]

DEPTH_MARK = "EXO_GATE_PROVE_DEPTH"
DEPTH = int(os.environ.get(DEPTH_MARK) or 0)
RUN_MARK = "EXO_PROVE_INSTALL_RUN"
WORLD_PREFIX = "exo-gate-p7-prove-"
SLEEPER_LIMIT = 3                                 # seconds the sleeper stand-in is given
SET_START = "# ── THE SET "
SET_END = "# ── END OF THE SET "

checks, fails = [], []
CASE = "P0"
OUTPUTS = []                                      # everything the runner printed, for P7
PIDS = []                                         # (pid, started) of every process this proof learned of


# ---------------------------------------------------------------------------
# saying what happened
# ---------------------------------------------------------------------------

def case(name, title):
    global CASE
    CASE = name
    print("\n── %s %s " % (name, title) + "─" * max(0, 60 - len(title)))


def ok(name, cond, detail=""):
    checks.append(bool(cond))
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", name,
                          ("  — " + " ".join(str(detail).split())[:300])
                          if (detail and not cond) else ""))
    if not cond:
        fails.append("%s · %s" % (CASE, name))


def note(text):
    print("  ..  %s" % text)


# ---------------------------------------------------------------------------
# the world
# ---------------------------------------------------------------------------

WORLD = None


def make_world():
    global WORLD
    WORLD = Path(tempfile.mkdtemp(prefix=WORLD_PREFIX)).resolve()
    return WORLD


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


STAND_IN_HEAD = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A stand-in gate, written by gate-prove.py. It proves nothing but the runner.
import os, subprocess, sys, time
from pathlib import Path
DEPTH = int(os.environ.get("EXO_GATE_PROVE_DEPTH") or 0)
if DEPTH > 1:
    sys.stderr.write("stand-in: depth %d is past 1, refusing to run\\n" % DEPTH)
    sys.exit(3)
MARKS = Path(__file__).resolve().parent.parent / "ran"
MARKS.mkdir(exist_ok=True)
(MARKS / (Path(__file__).stem + "-%d" % os.getpid())).write_text("ran", encoding="utf-8")


def make_world():
    """A world of this stand-in's own, where every gate makes one: the temp folder."""
    import tempfile
    w = Path(tempfile.mkdtemp(prefix="exo-standin-world-"))
    (w / "inside.txt").write_text("a fixture", encoding="utf-8")
    worlds = Path(__file__).resolve().parent.parent / "worlds"
    worlds.mkdir(exist_ok=True)
    (worlds / (Path(__file__).stem + "-%d" % os.getpid())).write_text(
        "%s\\n%s" % (w, tempfile.gettempdir()), encoding="utf-8")
    return w
'''

GREEN = STAND_IN_HEAD + '''
import shutil
shutil.rmtree(str(make_world()))           # a good gate removes its own world
print("the green stand-in: three things, all fine")
print("3 checks \\u00b7 3 passed \\u00b7 0 failed")
sys.exit(0)
'''

RED = STAND_IN_HEAD + '''
make_world()                               # a failing gate that forgets its world
print("the red stand-in: four things, one of them wrong")
print("  FAIL  the one wrong thing")
print("4 checks \\u00b7 3 passed \\u00b7 1 failed")
sys.exit(1)
'''

SLEEPER = STAND_IN_HEAD + '''
make_world()                               # a world, and then it is ended at its limit
env = dict(os.environ)
env["EXO_GATE_PROVE_DEPTH"] = str(DEPTH + 1)
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], env=env)
pids = Path(__file__).resolve().parent.parent / "pids"
pids.mkdir(exist_ok=True)
(pids / "sleeper").write_text("%d %d" % (os.getpid(), child.pid), encoding="utf-8")
print("the sleeper stand-in: it will not finish in time", flush=True)
time.sleep(120)
print("1 checks \\u00b7 1 passed \\u00b7 0 failed")
'''

STOPS = STAND_IN_HEAD + '''
home = os.path.expanduser("~")
sys.stderr.write("it stopped at Wren's desk on the North machine, in %s\\n"
                 % os.path.join(home, "somewhere"))
sys.exit(2)
'''

SKIPS = STAND_IN_HEAD + '''
print("gate-skips.py: skipped here \u2014 a stand-in with nothing to prove on this layout")
sys.exit(0)
'''

BADSKIP = STAND_IN_HEAD + '''
print("gate-badskip.py: skipped here \u2014 a skip line with a failing exit is not a skip")
sys.exit(2)
'''

EMPTY = STAND_IN_HEAD + '''
print("  SKIP  nothing here for this stand-in to prove")
print("0 checks \\u00b7 0 passed \\u00b7 0 failed \\u00b7 1 skipped")
sys.exit(0)
'''

FIXTURE_REGISTRY = {"version": 1, "owner": {"name": "Wren", "short": "wren", "aliases": []},
                    "machines": {"north": {"label": "North", "os": "macos"}}}


def runner_copy(tools, entries):
    """The real runner with its set replaced by `entries`, and nothing else."""
    text = io.open(str(RUNNER), encoding="utf-8").read()
    start, end = text.find(SET_START), text.find(SET_END)
    if start < 0 or end < 0 or end < start:
        raise RuntimeError("the runner's set is not between its two marker lines")
    end = text.index("\n", end) + 1
    block = SET_START + "(a fixture's own set) ─\nSET = (\n"
    for name, what, limit in entries:
        block += "    (%r, %r, %d),\n" % (name, what, limit)
    block += ")\n" + SET_END + "─\n"
    copy = text[:start] + block + text[end:]
    write(tools / "prove-install.py", copy)
    return text, copy, (start, end)


def build_fixture():
    """hub/tools with the runner copy and the four stand-ins; hub2/tools with a
    runner copy whose three gates stop, count nothing, or say a skip line and
    fail, beside a registry that names somebody."""
    w = make_world()
    tools = w / "hub" / "tools"
    for name, body in (("gate-green.py", GREEN), ("gate-red.py", RED),
                       ("gate-sleeper.py", SLEEPER), ("gate-skips.py", SKIPS)):
        write(tools / name, body)
    real, copy, span = runner_copy(tools, (("gate-green.py", "a stand-in that passes", 60),
                                           ("gate-red.py", "a stand-in that fails", 60),
                                           ("gate-sleeper.py", "a stand-in that sleeps",
                                            SLEEPER_LIMIT),
                                           ("gate-skips.py", "a stand-in that cannot run here",
                                            60)))
    tools2 = w / "hub2" / "tools"
    write(tools2 / "gate-stops.py", STOPS)
    write(tools2 / "gate-empty.py", EMPTY)
    write(tools2 / "gate-badskip.py", BADSKIP)
    runner_copy(tools2, (("gate-stops.py", "a stand-in that stops", 60),
                         ("gate-empty.py", "a stand-in that counts nothing", 60),
                         ("gate-badskip.py", "a skip line and a failing exit", 60)))
    write(w / "hub2" / "registry.json", json.dumps(FIXTURE_REGISTRY, indent=2) + "\n")
    return w, tools, tools2, real, copy, span


# ---------------------------------------------------------------------------
# processes: who started whom (the runner's own reading, asked independently)
# ---------------------------------------------------------------------------

def elapsed_seconds(text):
    days, _, rest = text.strip().rpartition("-")
    parts = [int(p) for p in rest.split(":") if p.isdigit()]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days.isdigit() else 0) * 86400 + parts[-3] * 3600 + parts[-2] * 60 + parts[-1]


def cim_epoch(value):
    if not value:
        return None
    m = re.search(r"Date\((-?\d+)\)", str(value))
    if m:
        return int(m.group(1)) / 1000.0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def process_rows():
    """(pid, parent, created) for every process on this machine."""
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate "
              "| ConvertTo-Json -Compress")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        text = r.stdout.decode("utf-8", "replace").strip()
        data = json.loads(text) if text else []
        if isinstance(data, dict):
            data = [data]
        rows = []
        for row in data:
            try:
                rows.append((int(row.get("ProcessId")), int(row.get("ParentProcessId") or 0),
                             cim_epoch(row.get("CreationDate"))))
            except (TypeError, ValueError):
                continue
        return rows
    r = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,etime="],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    now = time.time()
    rows = []
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                rows.append((int(parts[0]), int(parts[1]), now - elapsed_seconds(parts[2])))
            except ValueError:
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


def still_alive(pid, started):
    """Is this pid still the process we learned of? (alive, and not a reused
    pid: a process that began before ours did is not ours)."""
    for p, _pp, created in process_rows():
        if p == pid:
            return created is None or created >= started - 2
    return False


def end(pid):
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import signal
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# running the runner
# ---------------------------------------------------------------------------

def run_runner(script, *args, **kw):
    """(exit code, output, seconds, the survivors below it) for one run of a
    runner, with the stand-ins' depth mark at 1."""
    env = dict(os.environ)
    env.pop(RUN_MARK, None)
    env[DEPTH_MARK] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key, value in (kw.get("env") or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        group["start_new_session"] = True
    started = time.time()
    proc = subprocess.Popen([PY, str(script)] + list(args), cwd=str(Path(script).parent.parent),
                            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, **group)
    PIDS.append((proc.pid, started))
    try:
        out, _ = proc.communicate(timeout=kw.get("timeout", 300))
    except subprocess.TimeoutExpired:
        end(proc.pid)
        out, _ = proc.communicate()
    seconds = time.time() - started
    left = [pid for pid in descendants(process_rows(), proc.pid, os.getpid(), started)]
    for pid in left:
        end(pid)
    text = out.decode("utf-8", "replace")
    OUTPUTS.append(text)
    return proc.returncode, text, seconds, left


ROW = re.compile(r"^(gate-\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(green|red|stopped|skipped)")
FOOTER = re.compile(r"^(\d+) gates · (\d+) green · (\d+) red · (\d+) stopped · (\d+) skipped$")


def table(text):
    rows = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m:
            rows[m.group(1)] = m.groups()[1:]
    foot = [FOOTER.match(l.strip()).groups() for l in text.splitlines() if FOOTER.match(l.strip())]
    return rows, (foot[-1] if foot else None)


# ---------------------------------------------------------------------------
# private words
# ---------------------------------------------------------------------------

def fold(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def private_words():
    """This machine's private words (the owner's list and the hub's own
    registry names, exactly as the runner reads them) and the fixture's."""
    words = set()
    try:
        for line in io.open(str(HUB / "release" / "SCRUB-WORDS.txt"), encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(line)
    except OSError:
        pass
    try:
        reg = json.loads(io.open(str(HUB / "registry.json"), encoding="utf-8").read())
    except (OSError, ValueError):
        reg = {}
    owner = reg.get("owner") if isinstance(reg.get("owner"), dict) else {}
    for word in [owner.get("name"), owner.get("short")] + list(owner.get("aliases") or []):
        if isinstance(word, str):
            words.add(word)
    for name, block in (reg.get("machines") or {}).items():
        words.add(name)
        if isinstance(block, dict) and isinstance(block.get("label"), str):
            words.add(block["label"])
    words.update(str(v) for v in (reg.get("mind_aliases") or {}).values())
    words.update(("Wren", "North"))
    return sorted(w for w in (fold(w).strip() for w in words) if len(w) > 1)


def hits(text, words):
    folded = fold(text)
    found = []
    for w in words:
        if re.search(r"(?<![0-9A-Za-z])" + re.escape(w) + r"(?![0-9A-Za-z])", folded, re.I):
            found.append("%s… (%d)" % (w[:1], len(w)))
    return found


# ---------------------------------------------------------------------------
# the cases
# ---------------------------------------------------------------------------

def case_copy(real, copy, span):
    case("P0", "the copy under test is the real runner, but for its set")
    start, end = span
    ok("the real runner is beside this proof", RUNNER.is_file(), RUNNER)
    tail_real = real[real.index("\n", real.find(SET_END)) + 1:]
    ok("the copy is the real runner byte for byte before its set",
       copy.startswith(real[:start]))
    ok("and byte for byte after it", copy.endswith(tail_real))


def case_table(tools):
    case("P1", "the table: four rows, the right verdicts and numbers")
    code, out, seconds, left = run_runner(tools / "prove-install.py")
    print("\n".join("     | " + l for l in out.strip().splitlines()))
    rows, foot = table(out)
    ok("four rows, one per gate of the set", len(rows) == 4, sorted(rows))
    ok("the green stand-in: 3 checks · 3 passed · 0 failed · green",
       rows.get("gate-green.py", ())[:3] == ("3", "3", "0")
       and rows.get("gate-green.py", ())[-1] == "green", rows.get("gate-green.py"))
    ok("the red stand-in: 4 checks · 3 passed · 1 failed · red",
       rows.get("gate-red.py", ())[:3] == ("4", "3", "1")
       and rows.get("gate-red.py", ())[-1] == "red", rows.get("gate-red.py"))
    ok("the sleeper: no numbers, stopped",
       rows.get("gate-sleeper.py", ())[:3] == ("–", "–", "–")
       and rows.get("gate-sleeper.py", ())[-1] == "stopped", rows.get("gate-sleeper.py"))
    ok("the one that cannot run here: no numbers, skipped, with its own why",
       rows.get("gate-skips.py", ())[:3] == ("–", "–", "–")
       and rows.get("gate-skips.py", ())[-1] == "skipped"
       and "skipped · a stand-in with nothing to prove on this layout" in out,
       rows.get("gate-skips.py"))
    ok("the footer: 4 gates · 1 green · 1 red · 1 stopped · 1 skipped",
       foot == ("4", "1", "1", "1", "1"), foot)
    ok("the sleeper's line says it ran past its limit and was ended",
       ("gate-sleeper.py stopped: ran past its %d s" % SLEEPER_LIMIT) in out, out[-300:])
    ok("every gate's limit is said before it runs",
       ("sleeper %d s" % SLEEPER_LIMIT) in out.splitlines()[0], out.splitlines()[:1])
    return code, out, seconds, left


def case_exit(code):
    case("P2", "the exit is 1 when anything is red or stopped")
    ok("the runner exited 1", code == 1, code)


def case_sleeper(out, seconds, left, w):
    case("P3", "the sleeper is ended inside its limit, with the child it started")
    m = re.search(r"^gate-sleeper\.py\s+\S+\s+\S+\s+\S+\s+([\d.]+)\s", out, re.M)
    took = float(m.group(1)) if m else None
    ok("the sleeper's own run lasted its limit and not much more (%s s of %d)"
       % (took, SLEEPER_LIMIT), took is not None and SLEEPER_LIMIT <= took < SLEEPER_LIMIT + 10,
       took)
    ok("the whole run lasted well under the sleeper's own 120 s (%.1f s)" % seconds,
       seconds < 60, seconds)
    worlds = sorted((w / "hub" / "worlds").iterdir()) if (w / "hub" / "worlds").is_dir() else []
    told = dict((p.name.rsplit("-", 1)[0], p.read_text(encoding="utf-8").split("\n"))
                for p in worlds)
    ok("the green, red and sleeper stand-ins each made a world (%s)" % ", ".join(sorted(told)),
       sorted(told) == ["gate-green", "gate-red", "gate-sleeper"], sorted(told))
    real_temp = str(Path(tempfile.gettempdir()).resolve())
    ok("each ran in a temporary folder of its own, under the system temp folder",
       all(Path(t[1]).resolve().parent == Path(real_temp)
           and Path(t[1]).name.startswith("exo-prove-" + stand) for stand, t in told.items()),
       [t[1] for t in told.values()])
    ok("every world is gone — the one removed by its gate, the one a failing gate left, "
       "and the one whose gate was ended at its limit",
       told and not any(Path(t[0]).exists() for t in told.values()),
       [t[0] for t in told.values() if Path(t[0]).exists()])
    ok("and so is every temporary folder the runner gave out",
       told and not any(Path(t[1]).exists() for t in told.values()),
       [t[1] for t in told.values() if Path(t[1]).exists()])
    pids = (w / "hub" / "pids" / "sleeper")
    ok("the sleeper told this proof its pid and its child's", pids.is_file())
    if pids.is_file():
        sleeper, child = [int(x) for x in pids.read_text(encoding="utf-8").split()]
        started = [s for p, s in PIDS][-1]
        ok("the sleeper is gone", not still_alive(sleeper, started), sleeper)
        ok("and so is the child it started (found by its pid, not its command line)",
           not still_alive(child, started), child)
    ok("survivors below the runner, by lineage: 0", left == [], left)


def case_only(tools):
    case("P4", "--only runs one gate")
    code, out, _s, left = run_runner(tools / "prove-install.py", "--only", "gate-green.py")
    rows, foot = table(out)
    ok("one row, the one asked for", sorted(rows) == ["gate-green.py"], sorted(rows))
    ok("the footer counts one green gate", foot == ("1", "1", "0", "0", "0"), foot)
    ok("and the exit is 0", code == 0, code)
    code, out, _s, _l = run_runner(tools / "prove-install.py", "--only", "gate-skips.py")
    rows, foot = table(out)
    ok("a skip alone: one row, skipped, footer 1 gates · 0 green · 0 red · 0 stopped · "
       "1 skipped, and the exit stays 0",
       rows.get("gate-skips.py", ())[-1:] == ("skipped",) and foot == ("1", "0", "0", "0", "1")
       and code == 0, (rows, foot, code))
    code, out, _s, _l = run_runner(tools / "prove-install.py", "--only", "gate-nowhere.py")
    ok("a gate that is not in the set is refused in one line, exit 2",
       code == 2 and "not in the set" in out and len(out.strip().splitlines()) == 1, out)
    marks = sorted(p.name.rsplit("-", 1)[0] for p in (tools.parent / "ran").iterdir())
    ok("the stand-ins that ran are exactly the ones asked for (green twice, red, "
       "sleeper and skips once each, skips once more alone)",
       marks == ["gate-green", "gate-green", "gate-red", "gate-skips", "gate-skips",
                 "gate-sleeper"], marks)
    ok("survivors: 0", left == [], left)


def names_under(folder):
    try:
        return sorted((p.name, p.stat().st_size, p.stat().st_mtime) for p in folder.iterdir())
    except OSError:
        return []


def temp_names():
    """The names in the temp folder a gate's own world could take."""
    try:
        return sorted(p.name for p in Path(tempfile.gettempdir()).iterdir()
                      if p.name.startswith(("exo-", "exocortex-gate-")))
    except OSError:
        return []


def case_list():
    case("P5", "--list on the REAL hub names every gate of the set, and runs none")
    source = io.open(str(RUNNER), encoding="utf-8").read()
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SET"
                                                for t in node.targets):
            names = [e.elts[0].value for e in node.value.elts]
    ok("the real runner's set is read (%d gates)" % len(names), len(names) >= 3, names)
    before, temp_before = names_under(HERE), temp_names()
    code, out, seconds, left = run_runner(RUNNER, "--list", env={DEPTH_MARK: None})
    print("\n".join("     | " + l for l in out.strip().splitlines()))
    after, temp_after = names_under(HERE), temp_names()
    listed = [l.split()[0] for l in out.splitlines()[1:] if l.strip().startswith("gate-")]
    ok("every gate of the set is named, in the set's order", listed == names, listed)
    wrong = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts and parts[0] in names:
            here = (HERE / parts[0]).is_file()
            said = parts[1] if len(parts) > 1 else ""
            if here != (said == "present"):
                wrong.append(parts[0])
    ok("each is said present exactly when its file is here", not wrong, wrong)
    ok("the footer counts them", re.search(r"^%d gates · %d present · %d absent$" % (
        len(names), sum(1 for n in names if (HERE / n).is_file()),
        sum(1 for n in names if not (HERE / n).is_file())), out, re.M) is not None,
       out.splitlines()[-1:])
    ok("it exits 0", code == 0, code)
    ok("the hub's tools/ reads the same before and after, name, size and time",
       before == after, sorted(set(before) ^ set(after))[:4])
    ok("no world of any gate appeared in the temp folder while it ran",
       sorted(set(temp_after) - set(temp_before)) == [],
       sorted(set(temp_after) - set(temp_before)))
    ok("and it took a moment, not a gate's run (%.1f s)" % seconds, seconds < 15, seconds)
    ok("survivors: 0", left == [], left)


def case_source():
    case("P6", "the runner's source: no shell string, no pattern, no acknowledgment flag")
    source = io.open(str(RUNNER), encoding="utf-8").read()
    tree = ast.parse(source)
    shells, patterns, acks = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant)
                                              and kw.value.value is False):
                    shells.append(node.lineno)
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("glob", "rglob", "iglob", "fnmatch", "fnmatchcase", "filter"):
                patterns.append(node.lineno)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.strip() == "--" + "ack":
                acks.append(node.lineno)
    ok("no call is given a shell", not shells, shells)
    ok("no call looks for files by a pattern", not patterns, patterns)
    ok("the acknowledgment flag is never written in it", not acks, acks)
    imports = [a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
               for a in n.names] + [n.module for n in ast.walk(tree)
                                    if isinstance(n, ast.ImportFrom) and n.module]
    ok("it imports neither glob nor fnmatch", not ({"glob", "fnmatch"} & set(imports)), imports)
    entries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SET"
                                                for t in node.targets):
            entries = node.value.elts
    literal = all(isinstance(e, ast.Tuple) and isinstance(e.elts[0], ast.Constant)
                  and re.match(r"^gate-[a-z0-9-]+\.py$", e.elts[0].value) for e in entries)
    ok("the set is a written list of plain names (%d)" % len(entries),
       bool(entries) and literal)
    ok("its processes start in a group of their own on both families of machine",
       "start_new_session" in source and "CREATE_NEW_PROCESS_GROUP" in source)
    ok("the group is ended with killpg only on POSIX, and with taskkill /T on Windows",
       re.search(r'if os\.name == "nt":\s*\n\s*subprocess\.call\(\["taskkill", "/T", "/F"',
                 source) is not None and "os.killpg" in source)


def case_private(tools2):
    case("P7", "what the runner prints carries no private word")
    code, out, _s, left = run_runner(tools2 / "prove-install.py")
    print("\n".join("     | " + l for l in out.strip().splitlines()))
    rows, foot = table(out)
    ok("the gate that stops without a count line is stopped",
       rows.get("gate-stops.py", ())[-1:] == ("stopped",), rows.get("gate-stops.py"))
    ok("a gate that counted nothing is never green: it is stopped, and says why",
       rows.get("gate-empty.py", ())[-1:] == ("stopped",)
       and "gate-empty.py stopped: it proved nothing on this hub" in out,
       rows.get("gate-empty.py"))
    ok("a skip line with a failing exit is not a skip: it is stopped",
       rows.get("gate-badskip.py", ())[-1:] == ("stopped",), rows.get("gate-badskip.py"))
    ok("the footer: 3 gates · 0 green · 0 red · 3 stopped · 0 skipped",
       foot == ("3", "0", "0", "3", "0"), foot)
    ok("its last error line is shown under the table",
       "gate-stops.py stopped: it stopped at" in out, out[-300:])
    ok("with the person's name and machine masked, and the home folder as ~",
       "W…" in out and "N…" in out and "~" in out and "Wren" not in out
       and "North" not in out, out[-300:])
    words = private_words()
    found = sorted(set(sum((hits(text, words) for text in OUTPUTS), [])))
    ok("not one private word in anything the runner printed this run (%d words known)"
       % len(words), not found, found)
    ok("survivors: 0", left == [], left)


def case_rails(tools):
    case("P8", "the rails")
    env = dict(os.environ)
    env[DEPTH_MARK] = "2"
    r = subprocess.run([PY, str(tools / "gate-green.py")], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=60)
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    ok("a stand-in refuses past depth 1, with no count line",
       r.returncode == 3 and "checks" not in out and "refusing" in out, out)
    before = sorted(p.name for p in (tools.parent / "ran").iterdir())
    code, out, _s, left = run_runner(tools / "prove-install.py", env={RUN_MARK: "1"})
    after = sorted(p.name for p in (tools.parent / "ran").iterdir())
    ok("the runner refuses inside a proof run, in one line, exit 2",
       code == 2 and "already inside a proof run" in out
       and len(out.strip().splitlines()) == 1, out)
    ok("and no gate ran", before == after, sorted(set(after) - set(before)))
    ok("survivors: 0", left == [], left)


def main():
    if DEPTH >= 1:
        sys.stderr.write("gate-prove: this is already inside a proof (depth %d) — refusing to "
                         "start another\n" % DEPTH)
        return 3
    unknown = [a for a in sys.argv[1:] if a != "--keep"]
    if unknown:
        print("gate-prove: %s is not an option this gate knows." % unknown[0])
        return 2
    if not RUNNER.is_file():
        print("gate-prove: there is no prove-install.py beside this gate (%s)." % HERE)
        return 2
    temp_before = temp_names()
    started = time.time()
    print("gate-prove — proof for prove-install.py")
    print("  runner   %s" % RUNNER.name)
    print("  world    a folder of its own in the temp folder (%s…)" % WORLD_PREFIX)
    print("  python   %s" % sys.version.split()[0])
    w = None
    try:
        w, tools, tools2, real, copy, span = build_fixture()
        case_copy(real, copy, span)
        code, out, seconds, left = case_table(tools)
        case_exit(code)
        case_sleeper(out, seconds, left, w)
        case_only(tools)
        case_list()
        case_source()
        case_private(tools2)
        case_rails(tools)
    except Exception as exc:
        ok("the proof ran to its end", False, repr(exc))
    finally:
        if not KEEP and WORLD is not None:          # the world, however the run ended
            shutil.rmtree(str(WORLD), ignore_errors=True)
    case("P8", "the rails, closed")
    strays = [pid for pid, st in PIDS for pid in [pid] if still_alive(pid, st)]
    ok("no process this proof learned of is still alive", not strays, strays)
    left_worlds = sorted(n for n in temp_names() if n.startswith(WORLD_PREFIX)
                         and n not in temp_before)
    ok("no world of this proof is left in the temp folder",
       KEEP or not left_worlds, left_worlds)
    print("\n===== GATE =====")
    for name in fails:
        print("  FAIL  %s" % name)
    passed = sum(1 for c in checks if c)
    print("  %.1f s" % (time.time() - started))
    print("%d checks · %d passed · %d failed" % (len(checks), passed, len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
