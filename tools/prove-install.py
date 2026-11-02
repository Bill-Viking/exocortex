#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prove-install.py — one command that proves this install.

    python3 tools/prove-install.py                  run every gate of the set, one table
    python3 tools/prove-install.py --only gate-paths.py
    python3 tools/prove-install.py --list           the set, and whether each file is here;
                                                    nothing is run
    python3 tools/prove-install.py --timeout 900    give every gate this many seconds

Every gate of the shipped set is run from this hub's own tools/ folder, each in
a process of its own, and ONE table says how each one went:

    gate · checks · passed · failed · seconds · verdict

A verdict is read from the gate's own count line (`N checks · N passed · N
failed`): green when nothing failed and the gate exited 0; red when something
failed; stopped when the gate printed no count line at all — it ran out of
time, or it ended before it could count — or counted nothing, and then the
last line it wrote to its error stream is shown under the table. A gate that
cannot run on this layout says so in ONE line, `<gate>: skipped here — <why>`,
exits 0 and counts nothing; it is skipped, and its why is shown. The footer
counts all four, and the exit is 1 when anything is red or stopped — never for
skips alone.

On Windows, the gates whose own harness is not yet Windows-true are NOT RUN:
one line above the table says how many and why, and each of their rows reads
`skipped · not yet Windows-true — <what>`; the program they prove was run on
Windows 10 by hand. EXO_PROVE_EVERYWHERE=1 runs them anyway — the measure for
making them true.

WHAT THE RUNNER NEVER DOES
  * It never looks for gates by a pattern. The set is the list below, written
    out name by name, so a gate that is not part of the shipped program is
    never run by this command, whatever else sits in tools/.
  * It never passes a gate a flag. Each gate runs as its author ships it.
  * It is not a gate itself: every gate starts as the outermost run, with no
    nesting mark of any gate's in its environment, in a process group of its
    own. A gate that runs past its limit is ended with everything it started,
    and whatever is still alive below it — found by who started whom, never by
    what a command line says — is ended too.
  * Each gate is given a temporary folder of its own (TMPDIR, TEMP and TMP
    point into it), made fresh under the system temp folder and removed when
    the gate ends — however it ends: done, failed, raised, or ended at its
    limit. Whatever a gate makes there cannot outlive its run.
  * It never starts inside another proof run (a gate that ran this command
    would run every gate again, without end); it refuses in one line.
  * What it prints carries no private word: the words this hub keeps private
    are masked, and the home folder is written as ~.

Standard library only, Python 3.9-compatible, macOS, Linux and Windows.
"""
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

try:                                       # a console that cannot spell "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent     # <hub>/tools
HUB = HERE.parent
PY = sys.executable

# ── THE SET ────────────────────────────────────────────────────────────────
# One entry per gate of the shipped program: the file, what it proves, and how
# many seconds it may run. A list, never a pattern — read from the program
# image's own names. The fourth field, when present, is what --list and the
# table say while that file is not in this folder.
SET = (
    ("gate-paths.py", "where the hub, the sync package and the machine file are", 600),
    ("gate-registry.py", "the person's own names, read from registry.json", 900),
    ("gate-split.py", "the program tree and the notes, kept apart", 1200),
    ("gate-seeds.py", "the first files a new brain is given", 900),
    ("gate-comms.py", "mail between sessions, and the postman", 1800),
    ("gate-tree-answers.py", "every mark on the tree page answers a click", 1200),
    ("gate-coordination.py", "stamps, claims and the union merge", 900),
    ("gate-opener-freshness.py", "the freshest opener wins on every carrier", 900),
    ("gate-asked.py", "what is waiting on the owner's word", 600),
    ("gate-ideas.py", "the ideas inbox", 600),
    ("gate-improvements.py", "the improvements ledger and its page", 900),
    ("gate-firstrun.py", "the first run on a clean machine", 900, "not yet built"),
)
# ── END OF THE SET ─────────────────────────────────────────────────────────

# ── NOT YET WINDOWS-TRUE ───────────────────────────────────────────────────
# Gates whose own harness knows only macOS and Linux today: a survivor query
# that matches its own PowerShell by command-line text, a cleanup that cannot
# remove the read-only objects git writes under .git, a child's output decoded
# with the console's code page, a Windows path planted unescaped in a fixture.
# The install, the heartbeat and the way out were run on Windows 10 by hand and
# held, so on Windows these gates are not run, and the table says so in one
# line, rather than printing a red that is the gate's and not the install's.
# Outside the set's markers on purpose: a fixture's own set keeps this map.
NOT_YET_WINDOWS = {
    "gate-registry.py": "its cleanup, and one lookup road",
    "gate-split.py": "its process query, and a fixture path",
    "gate-seeds.py": "its process query, and its cleanup",
    "gate-comms.py": "console decoding, and the hook install road",
    "gate-tree-answers.py": "the login in the temp path",
    "gate-improvements.py": "console decoding",
    "gate-firstrun.py": "its cleanup, and a PATH stand-in",
}
ON_WINDOWS = sys.platform.startswith("win")
EVERYWHERE = "EXO_PROVE_EVERYWHERE"
WINDOWS_LINE = ("Windows: %d of %d gates are not yet Windows-true and are not run here \u2014 "
                "their process queries, cleanup and console decoding know only macOS; the "
                "install, the heartbeat and the way out were proven on Windows 10 by hand. "
                "%s=1 runs them anyway.")

# Every gate's own nesting marks. The runner clears them all, so each gate it
# starts is the outermost run of that gate (depth 0, no inner mark).
GATE_MARKS = ("EXO_GATE_PATHS_INNER", "EXO_GATE_PATHS_DEPTH",
              "EXO_GATE_REG_INNER", "EXO_GATE_REG_DEPTH",
              "EXO_GATE_SPLIT_INNER", "EXO_GATE_SPLIT_DEPTH",
              "EXO_GATE_SEEDS_INNER", "EXO_GATE_SEEDS_DEPTH",
              "EXO_GATE_FIRSTRUN_INNER", "EXO_GATE_FIRSTRUN_DEPTH")
RUN_MARK = "EXO_PROVE_INSTALL_RUN"         # set for every gate this runner starts

COUNT = re.compile(r"(\d+) checks · (\d+) passed · (\d+) failed(?: · (\d+) skipped)?")
SKIP_LINE = re.compile(r"^(\S+): skipped here \u2014 (.+)$")
TEMP_PREFIX = "exo-prove-"                 # each gate's own temporary folder

USAGE = __doc__.split("WHAT THE RUNNER")[0].rstrip() + "\n"


# ---------------------------------------------------------------------------
# private words: what this hub keeps private is never printed
# ---------------------------------------------------------------------------

def fold(text):
    """Accents folded away, so a name dressed in a diacritic is still seen."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def private_words():
    """The words this hub keeps private: the owner's word list when the hub
    has one (release/SCRUB-WORDS.txt), and the names the person's own
    registry.json carries — their name, short word and aliases, their machines'
    names and labels, the persona words of their minds. Never raises."""
    words = set()
    listed = HUB / "release" / "SCRUB-WORDS.txt"
    try:
        for line in io.open(str(listed), encoding="utf-8", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(line)
    except OSError:
        pass
    try:
        with io.open(str(HUB / "registry.json"), encoding="utf-8") as fh:
            reg = json.load(fh)
    except (OSError, ValueError):
        reg = {}
    if isinstance(reg, dict):
        owner = reg.get("owner") if isinstance(reg.get("owner"), dict) else {}
        for key in ("name", "short"):
            if isinstance(owner.get(key), str):
                words.add(owner[key])
        for alias in owner.get("aliases") or []:
            if isinstance(alias, str):
                words.add(alias)
        machines = reg.get("machines") if isinstance(reg.get("machines"), dict) else {}
        for name, block in machines.items():
            words.add(str(name))
            if isinstance(block, dict) and isinstance(block.get("label"), str):
                words.add(block["label"])
        aliases = reg.get("mind_aliases") if isinstance(reg.get("mind_aliases"), dict) else {}
        for key, value in aliases.items():
            words.add(str(value))
    return sorted(w for w in (fold(w).strip() for w in words) if len(w) > 1)


def masker():
    """A function that masks every private word and the home folder in what it
    is given, line by line. A line is masked as it stands; a line that still
    holds a private word once its accents are folded is replaced by its folded,
    masked form, so a name written with a diacritic is caught too."""
    pats = [re.compile(r"(?<![0-9A-Za-z_])" + re.escape(w) + r"(?![0-9A-Za-z_])", re.IGNORECASE)
            for w in private_words()]
    homes = []
    for home in (os.path.expanduser("~"), str(Path(os.path.expanduser("~")).resolve())):
        for spelling in (home, fold(home)):
            if spelling and len(spelling) > 3 and spelling not in homes:
                homes.append(spelling)

    def plain(line):
        for home in homes:
            line = line.replace(home, "~")
        for pat in pats:
            line = pat.sub(lambda m: m.group(0)[:1] + "\u2026", line)
        return line

    def mask(text):
        out = []
        for line in str(text).split("\n"):
            line = plain(line)
            folded = fold(line)
            if any(pat.search(folded) for pat in pats):
                line = plain(folded)
            out.append(line)
        return "\n".join(out)
    return mask


# ---------------------------------------------------------------------------
# processes: who started whom
# ---------------------------------------------------------------------------

def elapsed_seconds(text):
    """`ps -o etime` as seconds: [[dd-]hh:]mm:ss."""
    days, _, rest = text.strip().rpartition("-")
    parts = [int(p) for p in rest.split(":") if p.isdigit()]
    while len(parts) < 3:
        parts.insert(0, 0)
    return (int(days) if days.isdigit() else 0) * 86400 + parts[-3] * 3600 + parts[-2] * 60 + parts[-1]


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


def process_rows():
    """Every process on this machine as (pid, parent pid, created, group);
    group is None on Windows. Raises where the question could not be asked."""
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
                             cim_epoch(row.get("CreationDate")), None))
            except (TypeError, ValueError):
                continue
        return rows
    r = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,pgid=,etime="],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    now = time.time()
    rows = []
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), now - elapsed_seconds(parts[3]), int(parts[2])))
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


def below(proc, started):
    """The pids alive below a child right now: its lineage, and on POSIX the
    members of its own process group (a group is inherited, never a name).
    None when the question could not be asked."""
    try:
        rows = process_rows()
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    own = os.getpid()
    found = set(descendants([(p, pp, c) for p, pp, c, _ in rows], proc.pid, own, started))
    if os.name != "nt":
        for pid, _, created, group in rows:
            if group == proc.pid and pid != proc.pid and pid != own:
                if created is None or created >= started - 2:
                    found.add(pid)
    return sorted(found)


def alive(pid):
    try:
        rows = process_rows()
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    return any(p == pid for p, _, _, _ in rows)


def end_group(proc):
    """End a child and everything it started: its process group on POSIX, its
    tree on Windows."""
    if os.name == "nt":
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)       # its own session: pgid == pid
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def end_pids(pids):
    for pid in pids:
        if pid == os.getpid():
            continue
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/PID", str(pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# one gate
# ---------------------------------------------------------------------------

def child_env(temp):
    env = dict(os.environ)
    for key in GATE_MARKS:
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env[RUN_MARK] = "1"
    for key in ("TMPDIR", "TEMP", "TMP"):      # the gate's own temporary folder
        env[key] = str(temp)
    return env


def remove_tree(path):
    """Remove a folder and everything in it, read-only files included."""
    def unlock(func, target, _exc):
        try:
            os.chmod(target, 0o700)
            func(target)
        except OSError:
            pass
    shutil.rmtree(str(path), onerror=unlock)


def run_gate(entry, limit):
    """(checks, passed, failed, skipped, seconds, verdict, note) for one gate."""
    name = entry[0]
    path = HERE / name
    if not path.is_file():
        note = entry[3] if len(entry) > 3 else "not installed"
        return (None, None, None, None, 0.0, "stopped", "%s — %s is not in %s" % (note, name, HERE))
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        group["start_new_session"] = True
    temp = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX + Path(name).stem + "-")).resolve()
    started = time.time()
    timed_out, strays = False, []
    try:
        proc = subprocess.Popen([PY, str(path)], cwd=str(HUB), env=child_env(temp),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, **group)
        try:
            out, err = proc.communicate(timeout=limit)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            timed_out = True
            lineage = below(proc, started) or []     # who is below it, taken BEFORE the end
            end_group(proc)
            try:
                out, err = proc.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                out, err = b"", b""
            left = [pid for pid in lineage if alive(pid)]
            strays = sorted(set(left) | set(below(proc, started) or []))
            end_pids(strays)
        else:
            strays = below(proc, started) or []      # a gate that left something running
            end_pids(strays)
    finally:
        remove_tree(temp)                            # however the gate ended
    seconds = time.time() - started
    out = out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")
    err = err.decode("utf-8", "replace") if isinstance(err, bytes) else (err or "")
    found = COUNT.findall(out)
    last_err = next((l.strip() for l in reversed(err.splitlines()) if l.strip()), "")
    strays_note = (" · %d process%s it left running %s ended" %
                   (len(strays), "" if len(strays) == 1 else "es",
                    "was" if len(strays) == 1 else "were")) if strays else ""
    if timed_out:
        return (None, None, None, None, seconds, "stopped",
                "ran past its %d s and was ended with everything it started%s"
                % (limit, strays_note))
    said = [l.strip() for l in out.splitlines() if l.strip()]
    skip = SKIP_LINE.match(said[0]) if len(said) == 1 else None
    if skip and skip.group(1) in (name, Path(name).stem) and proc.returncode == 0 \
            and not strays:
        return (0, 0, 0, 0, seconds, "skipped", skip.group(2))
    if not found:
        return (None, None, None, None, seconds, "stopped",
                (last_err or "it printed no count line (exit %s)" % proc.returncode) + strays_note)
    checks, passed, failed, skipped = found[-1]
    checks, passed, failed = int(checks), int(passed), int(failed)
    skipped = int(skipped) if skipped else 0
    if checks == 0:
        # A gate that counted nothing and did not say it cannot run here proved
        # nothing: it is not green, and it is not a skip.
        said = [l.strip() for l in out.splitlines()
                if "skipped:" in l or l.strip().startswith("SKIP")]
        return (checks, passed, failed, skipped, seconds, "stopped",
                "it proved nothing on this hub — " + (said[-1] if said else
                                                    "it counted no check at all"))
    if failed == 0 and proc.returncode == 0 and not strays:
        verdict = "green"
    else:
        verdict = "red"
    note = ""
    if failed == 0 and proc.returncode != 0:
        note = "nothing failed, yet it exited %s" % proc.returncode
    if strays:
        note = (note + strays_note) if note else strays_note.lstrip(" ·")
    return (checks, passed, failed, skipped, seconds, verdict, note)


# ---------------------------------------------------------------------------
# the table
# ---------------------------------------------------------------------------

def num(value):
    return "–" if value is None else str(value)


def row_line(name, checks, passed, failed, seconds, verdict, width):
    return "%-*s %7s %7s %7s %8s  %s" % (width, name, num(checks), num(passed), num(failed),
                                         "%.1f" % seconds if seconds else "–", verdict)


def head_line(width):
    return "%-*s %7s %7s %7s %8s  %s" % (width, "gate", "checks", "passed", "failed",
                                         "seconds", "verdict")


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(USAGE)
        return 0
    known = ("--list", "--only", "--timeout")
    args = list(argv)
    only, limit_all = None, None
    if "--only" in args:
        i = args.index("--only")
        if i + 1 >= len(args):
            print("prove-install: --only needs a gate's name, e.g. --only gate-paths.py")
            return 2
        only = args[i + 1]
        del args[i:i + 2]
    if "--timeout" in args:
        i = args.index("--timeout")
        try:
            limit_all = int(args[i + 1])
        except (IndexError, ValueError):
            print("prove-install: --timeout needs a number of seconds")
            return 2
        del args[i:i + 2]
    listing = "--list" in args
    args = [a for a in args if a != "--list"]
    if args:
        print("prove-install: %s is not something this command knows (it knows %s)."
              % (args[0], ", ".join(known)))
        return 2

    entries = list(SET)
    if only is not None:
        want = only if only.endswith(".py") else only + ".py"
        entries = [e for e in SET if e[0] == want]
        if not entries:
            print("prove-install: %s is not in the set; --list shows the set." % only)
            return 2

    mask = masker()
    width = max(len(e[0]) for e in entries) + 1
    held = {}
    if ON_WINDOWS and not os.environ.get(EVERYWHERE):
        held = dict((e[0], NOT_YET_WINDOWS[e[0]]) for e in entries if e[0] in NOT_YET_WINDOWS)

    if listing:
        print(mask("prove-install · the set, from %s · nothing is run" % HERE))
        for entry in entries:
            here = (HERE / entry[0]).is_file()
            state = "present" if here else (entry[3] if len(entry) > 3 else "absent")
            print(mask("  %-*s %-14s %s" % (width, entry[0], state, entry[1])))
        present = sum(1 for e in entries if (HERE / e[0]).is_file())
        print("%d gates · %d present · %d absent" % (len(entries), present, len(entries) - present))
        if held:
            print(mask(WINDOWS_LINE % (len(held), len(entries), EVERYWHERE)))
        return 0

    if os.environ.get(RUN_MARK):
        print("prove-install: this is already inside a proof run — a gate must never run the "
              "whole set again, so nothing was started.")
        return 2

    print(mask("prove-install · %d gate%s from %s · python %s · each gate's limit: %s"
               % (len(entries), "" if len(entries) == 1 else "s", HERE, sys.version.split()[0],
                  ("%d s" % limit_all) if limit_all else
                  ", ".join("%s %d s" % (e[0][5:-3], e[2]) for e in entries))))
    if held:
        print(mask(WINDOWS_LINE % (len(held), len(entries), EVERYWHERE)))
    print(head_line(width))
    tally = {"green": 0, "red": 0, "stopped": 0, "skipped": 0}
    notes = []
    for entry in entries:
        if entry[0] in held:
            tally["skipped"] += 1
            print(mask(row_line(entry[0], None, None, None, 0,
                                "skipped \u00b7 not yet Windows-true \u2014 " + held[entry[0]],
                                width)))
            sys.stdout.flush()
            continue
        limit = limit_all or entry[2]
        checks, passed, failed, skipped, seconds, verdict, note = run_gate(entry, limit)
        tally[verdict] += 1
        if verdict == "skipped":
            shown = "skipped \u00b7 " + note
            note = ""
            checks = passed = failed = None
        else:
            shown = verdict + (" · %d skipped" % skipped if skipped else "")
        print(mask(row_line(entry[0], checks, passed, failed, seconds, shown, width)))
        sys.stdout.flush()
        if note:
            notes.append("%s %s: %s" % (entry[0], verdict, note))
    print("%d gates · %d green · %d red · %d stopped · %d skipped"
          % (len(entries), tally["green"], tally["red"], tally["stopped"], tally["skipped"]))
    for line in notes:
        print(mask("  " + line))
    return 1 if (tally["red"] or tally["stopped"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
