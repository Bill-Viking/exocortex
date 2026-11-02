#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-asked.py — proof for tools/asked.py, hermetic: nothing live is written.

    python3 tools/gate-asked.py [--keep]

A scratch hub and a scratch projects root are built under the system temp folder
and every case runs with --hub and --projects pointed there, so the live STATUS
files, IDEAS.md, the journal and the watchers are out of reach (the coordination
gate's rule: a proof that can touch live state is not a proof).

The fixtures carry, on purpose: dated asks on three days, an undated ask in a
repo whose line was committed on a fixed day, an undated ask in a folder that is
NOT a repo, a done item, two open items that ask nobody (one with a four-word
quote), an urgent ask, CAPS-titled items, a curly-quoted ruling and a
straight-quoted one, an idea "new" and an idea "someday", journal lines stamped
pending / PROMOTED / JOURNAL-ONLY / pending-then-decided, and two watcher
entries — one ruled and never filed (a filing word that stands BEFORE the
ruling, which must not count as filed) and one ruled and filed.

Cases, in order: A0 compile, --help, unknown flag · A1 the header
counts · A2 group order and oldest first · A3 the undated ask last and Alpha's
blamed date · A4 --project · A5 --days · A6 --everything · A7 --all · A8 --count
· A9 --json · A10 a project with no To do and a project with no STATUS · A11
nothing written — the whole scratch tree byte for byte, and the three live files
· A12 a read-only smoke run on this machine's real roots.

--keep leaves the scratch folder for inspection. Exit 1 on any failed check.
"""
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

try:                                   # cp1252 console: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HUB = Path(__file__).resolve().parent.parent
TOOL = HUB / "tools" / "asked.py"
PY = sys.executable
SCRATCH = Path(tempfile.gettempdir()) / "exocortex-gate-bq010"
SCR_HUB, SCR_PROJ = SCRATCH / "Exocortex", SCRATCH / "Projects"
# The gate's own registry: the owner its fixtures quote, and nobody else's. The
# scratch runs read it through EXO_REGISTRY_JSON, so the proof is the same on
# any machine, whatever that machine's own registry names; the smoke run on the
# real roots (A12) reads the machine's own registry, as the hub's wake does.
SCR_REGISTRY = SCRATCH / "registry.json"
FIXTURE_REGISTRY = {"version": 1, "owner": {"name": "Wren", "short": "wren", "aliases": []}}
TODAY = date.today()
# The fixtures were written on WRITTEN; every date in them is read as that many
# days before TODAY, so an ask is as old on every day this gate runs as it was
# the day it was written (the fixtures never age out of --days N).
WRITTEN = date(2026, 9, 12)
DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b(?: \((Mon|Tue|Wed|Thu|Fri|Sat|Sun)\))?")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def shift(text):
    """Every date in a fixture moved to the same distance before TODAY that it
    stood before WRITTEN — and a weekday written beside it moved with it."""
    def moved(m):
        then = TODAY - (WRITTEN - date.fromisoformat(m.group(1)))
        return then.isoformat() + ((" (%s)" % WEEKDAYS[then.weekday()]) if m.group(2) else "")
    return DATE.sub(moved, text)


ALPHA_DAY = shift("2026-08-26")        # the day Alpha's STATUS line was committed
checks, fails = [], []


def days(iso):
    return (TODAY - date.fromisoformat(iso)).days


# ── fixtures ──────────────────────────────────────────────────────────────

HUB_STATUS = """# STATUS — Exocortex (gate fixture)
<!-- scratch: nothing in this file is live -->

## Now

The asked gate reads this scratch hub.

## To do
- [ ] STYLE CATALOG follow-ups (Wren, 2026-08-24): the sky's constellations want their own page.
- [ ] ! DRIVE GUARD — PROTECTED PATHS (Wren, 2026-09-08 20:0x, re-taught at the button-up): the list every drive-writing tool must read before it writes.
- [ ] PEN CHECK 2026-09-05: the hub said "the pen is a claim, not a question" and the check should run itself.
- [ ] the ruling on the three proposals was “save all three of them, today” and nobody filed it (2026-09-11).
- [ ] MAIL WATCHER SELF-END: a watcher should end itself when its session retires — Wren asked for that in chat.
- [ ] a plain reminder to run the pulse on this machine once a week
- [ ] the tree page needs "one obvious next move" on every tile (2026-09-02)
- [x] SOMETHING DONE (Wren, 2026-08-20): a finished item never counts.

## Important

Nothing.
"""

ALPHA_STATUS = """# STATUS — Alpha

## Now

A scratch project, and a git repo.

## To do
- [ ] ALPHA NAMING: Wren still owes the name here, and this line carries no date at all.
- [ ] ALPHA DATED (Wren, 2026-09-01): a dated ask inside a repo needs no blame.
- [x] ALPHA DONE (Wren, 2026-08-30): finished.

## Important

Nothing.
"""

BETA_STATUS = """# STATUS — Beta

## Now

Beta has no To do heading at all, and this checkbox sits under ## Now:
- [ ] Wren asked for a Beta thing here, and this screen must not read it.

## Important

Nothing.
"""

IDEAS = """# IDEAS — the exocortex's Someday. Say "idea: …" in any session; Tuesday judges it.
# One line per idea, newest last. Lines are never deleted, so #<n> is stable.

- 2026-09-10 09:15 · new · a wiki page per agent · via SOUTH/GATE
- 2026-09-12 07:32 · someday · a Reminders door swept in by the pulse · via NORTH/GATE · someday 2026-09-12
- 2026-09-05 11:00 · filed → Alpha · the idea that already went to Alpha · via SOUTH/GATE · filed 2026-09-06
"""

TAUGHT = """<!-- gate fixture -->

# Taught

- 2026-08-31 · ANSWERABILITY LAW (proposed for promotion): an evidence surface must answer the question it is handed. [STAMP PENDING]
- 2026-09-10 · ROUTINES EXECUTE, NO PROMPTS (Wren, ~08:10): a routine should just run. [promotion: Wren's word pending]
- 2026-09-01 · PLAIN SPEECH (Wren): every explanation starts in everyday words. [PROMOTED to global CLAUDE.md 2026-09-01]
- 2026-09-02 · LANE LEDGER (a lane practice): the lane keeps its own ledger. [JOURNAL-ONLY]
- 2026-09-03 · MIXED STAMPS (Wren): the first stamp asks, the LAST one decides. [STAMP PENDING] [JOURNAL-ONLY]
"""

WATCHER = """# LESSON PROPOSALS — test fixture

## 2026-09-09 (Wed) — scheduled run

Three proposals this run.

- Proposal 1 — a lesson about openers (journal-only, recorded in the project memory's own block).
- Proposal 2 — a lesson about landings.
- Proposal 3 — a lesson about the drive.

**Wren's ruling, 2026-09-09 (live in chat, same run): "yes, save all three."**

## 2026-09-07 (Mon) — scheduled run

- Proposal A — a lesson about mail.

**Wren's ruling, 2026-09-07: "keep it."** Filed to dossier/TAUGHT.md the same hour.

## 2026-09-05 (Fri) — scheduled run

- Proposal B — nothing was ruled on this one, so it asks nobody anything.
"""


HUB_STATUS, ALPHA_STATUS, BETA_STATUS, IDEAS, TAUGHT, WATCHER = (
    shift(HUB_STATUS), shift(ALPHA_STATUS), shift(BETA_STATUS), shift(IDEAS), shift(TAUGHT),
    shift(WATCHER))


# ── plumbing ──────────────────────────────────────────────────────────────

def ok(name, cond, detail=""):
    checks.append(bool(cond))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + detail) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)


def run(*args, **kw):
    """One asked.py run against the scratch hub, its real output shown."""
    expect, label = kw.get("expect", 0), kw.get("label")
    must, must_not = kw.get("must", ()), kw.get("must_not", ())
    quiet, live = kw.get("quiet", False), kw.get("live", False)
    argv = [PY, str(TOOL)] + list(args)
    env = dict(os.environ)
    env.pop("EXO_REGISTRY_JSON", None)
    if not live:
        argv += ["--hub", str(SCR_HUB), "--projects", str(SCR_PROJ)]
        env["EXO_REGISTRY_JSON"] = str(SCR_REGISTRY)
    print("\n$ asked.py %s%s" % (" ".join(args), "   (the REAL roots)" if live else ""))
    started = time.time()
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    run.seconds, run.code = time.time() - started, proc.returncode
    if not quiet:
        print(out.rstrip() or "(no output)")
    bad = []
    if expect is not None and proc.returncode != expect:
        bad.append("exit %d, expected %d" % (proc.returncode, expect))
    bad += ["missing %r" % m for m in must if m not in out]
    bad += ["must not contain %r" % m for m in must_not if m in out]
    if "Traceback" in out:
        bad.append("it raised")
    if label:
        ok(label, not bad, "; ".join(bad))
    return out


def section(title):
    print("\n" + "=" * 8 + " " + title + " " + "=" * 8)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def sha(path):
    try:
        return hashlib.sha256(io.open(str(path), "rb").read()).hexdigest()[:16]
    except OSError:
        return "absent"


def tree_shas(root):
    """Every file under root, by path and content — the whole-tree fingerprint."""
    out = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root))] = sha(path)
    return out


def unlock(func, path, _exc):          # git keeps its objects read-only on Windows
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def remove_tree(root):
    if Path(root).exists():
        shutil.rmtree(str(root), onerror=unlock)


def git(repo, *args, **kw):
    cmd = ["git", "-C", str(repo), "-c", "user.name=Gate", "-c", "user.email=gate@example.invalid",
           "-c", "commit.gpgsign=false",
           "-c", "core.hooksPath=%s" % (SCRATCH / "nohooks")] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=kw.get("env"))


def lines_of(out):
    return [l for l in out.splitlines() if l.strip()]


def head_of(out):
    rows = lines_of(out)
    return rows[0] if rows else ""


def group_lines(out, title):
    """The item lines under one group heading — headings sit at column 0, items
    are indented by their age."""
    rows, taking = [], False
    for line in lines_of(out)[1:]:
        if not line.startswith(" "):
            taking = line.startswith(title)
            continue
        if taking:
            rows.append(line)
    return rows


def group_heads(out):
    return [l.split(" (")[0] for l in lines_of(out)[1:] if not l.startswith(" ")]


def without_stamp(header):
    """The header without its trailing "<machine> <date> <hour>" clause, so two
    runs a minute apart still compare equal."""
    return header.rsplit(" · ", 1)[0]


def live_hub():
    """The real hub folder, read (never written) so A11 can prove it."""
    try:
        with io.open(Path.home() / "orchestrator-sync" / "machine.json", encoding="utf-8") as fh:
            roots = (json.load(fh).get("roots") or {})
        return Path(roots.get("orchestrator") or HUB)
    except Exception:
        return HUB


def fresh_scratch():
    remove_tree(SCRATCH)
    (SCRATCH / "nohooks").mkdir(parents=True)
    write(SCR_REGISTRY, json.dumps(FIXTURE_REGISTRY, indent=2) + "\n")
    write(SCR_HUB / "STATUS.md", HUB_STATUS)
    write(SCR_HUB / "IDEAS.md", IDEAS)
    write(SCR_HUB / "dossier" / "TAUGHT.md", TAUGHT)
    write(SCR_HUB / "watchers" / "LESSON-PROPOSALS-test.md", WATCHER)
    write(SCR_PROJ / "Alpha" / "STATUS.md", ALPHA_STATUS)
    write(SCR_PROJ / "Beta" / "STATUS.md", BETA_STATUS)
    (SCR_PROJ / "Gamma").mkdir(parents=True, exist_ok=True)
    write(SCR_PROJ / "Gamma" / "README.md", "Gamma has no STATUS.md.\n")
    write(SCR_PROJ / "notes.txt", "a file in the projects root is not a project\n")
    print("   scratch hub:      %s" % SCR_HUB)
    print("   scratch projects: %s (Alpha = git repo · Beta = no To do · Gamma = no STATUS)" % SCR_PROJ)

    stamp = "%sT09:00:00-07:00" % ALPHA_DAY
    env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    made = git(SCR_PROJ / "Alpha", "init", "-q", "-b", "main")
    if made.returncode != 0:                                    # an older git has no -b
        made = git(SCR_PROJ / "Alpha", "init", "-q")
    git(SCR_PROJ / "Alpha", "add", "STATUS.md")
    done = git(SCR_PROJ / "Alpha", "commit", "-q", "-m", "fixture", env=env)
    ok("Alpha is a git repo whose STATUS line was committed on %s" % ALPHA_DAY,
       made.returncode == 0 and done.returncode == 0 and (SCR_PROJ / "Alpha" / ".git").exists(),
       ((made.stderr or "") + (done.stderr or "")).strip() or "is git on this machine?")


# ── the cases ─────────────────────────────────────────────────────────────

def main(argv):
    if "--help" in argv:
        print(__doc__)
        return 0
    keep = "--keep" in argv
    print("gate-asked · hub %s · python %s · today %s" % (HUB, sys.version.split()[0], TODAY))
    fresh_scratch()

    section("A0 — it compiles, it explains itself, it refuses what it does not know")
    # Compiled INTO the scratch folder: a proof for a read-only tool leaves no
    # byte of its own in the hub either.
    compiled = subprocess.run(
        [PY, "-c", "import py_compile, sys\n"
                   "prefix = sys.argv[1]\n"
                   "for i, f in enumerate(sys.argv[2:]):\n"
                   "    py_compile.compile(f, cfile=prefix + str(i) + '.pyc', doraise=True)\n",
         str(SCRATCH / "compiled"), str(TOOL), str(Path(__file__).resolve())],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok("both files compile", compiled.returncode == 0, (compiled.stderr or "").strip())
    run("--help", label="--help exits 0 and says what is NOT in v1",
        must=("INBOX lines", "openers", "NEVER writes"))
    run("--nonsense", expect=2, label="an unknown flag prints the usage and exits 2",
        must=("asked.py",))

    section("A1 — the header counts, exactly")
    before_tree = tree_shas(SCRATCH)     # the fingerprint A11 will check, taken
    out = run()                          # before the first asked.py run
    want = ("ASKED — 10 open · oldest %d d · 2 waiting on your word · 1 idea unjudged"
            " · 1 watcher ruling unfiled" % days(shift("2026-08-24")))
    got = head_of(out)
    ok("the header reads: %s" % want, got.startswith(want + " · "), got)
    ok("and ends with the machine and the minute it was read",
       re.search(r" · \S+ \d{4}-\d{2}-\d{2} \d{2}:\d{2}$", got) is not None, got)
    ok("a done item is never counted", "SOMETHING DONE" not in out)
    ok("an open item that asks nobody is not an ask", "a plain reminder to run the pulse" not in out)
    ok("a four-word quote is not an ask", "one obvious next move" not in out)
    ok("the default screen is one screen (40 lines or fewer)", len(lines_of(out)) <= 40,
       "%d lines" % len(lines_of(out)))

    section("A2 — group order, and oldest first inside each group")
    ok("the four groups stand in the brief's order",
       group_heads(out) == ["WAITING ON YOUR WORD", "IDEAS UNJUDGED", "OLDEST OPEN ASKS",
                            "WATCHER RULINGS NOT FILED"], str(group_heads(out)))
    asks = group_lines(out, "OLDEST OPEN ASKS")
    expected = ["STYLE CATALOG follow-ups", "ALPHA NAMING", "ALPHA DATED", "PEN CHECK",
                "DRIVE GUARD", "the ruling on the three proposals", "MAIL WATCHER SELF-END"]
    ok("seven asks, oldest first: %s" % " → ".join(expected),
       len(asks) == len(expected) and all(want in line for want, line in zip(expected, asks)),
       "\n      " + "\n      ".join(asks))
    ok("every ask line carries its project, its words and its file:line",
       all(re.search(r"· [^·]+ · [^·]*STATUS\.md:\d+$", line) for line in asks),
       "\n      " + "\n      ".join(asks))
    urgent = [l for l in asks if "▲" in l]
    ok("the one urgent ask carries the mark, and only it",
       len(urgent) == 1 and "DRIVE GUARD" in urgent[0], str(urgent))
    waiting = group_lines(out, "WAITING ON YOUR WORD")
    ok("the journal group holds the two pending stamps, oldest first",
       len(waiting) == 2 and "ANSWERABILITY LAW" in waiting[0]
       and "ROUTINES EXECUTE, NO PROMPTS" in waiting[1], str(waiting))
    ok("a line whose LAST stamp is decided is not waiting", "MIXED STAMPS" not in out)
    ok("PROMOTED and JOURNAL-ONLY lines are not waiting",
       "PLAIN SPEECH" not in out and "LANE LEDGER" not in out)
    ok("the ideas group shows the new idea alone",
       group_lines(out, "IDEAS UNJUDGED") and
       "a wiki page per agent" in group_lines(out, "IDEAS UNJUDGED")[0]
       and len(group_lines(out, "IDEAS UNJUDGED")) == 1)
    watchers = group_lines(out, "WATCHER RULINGS NOT FILED")
    ok("the entry ruled and never filed is named — the 2026-09-09 leak, "
       "though its \"recorded in\" sits before the ruling",
       len(watchers) == 1 and "LESSON-PROPOSALS-test" in watchers[0]
       and shift("2026-09-09 (Wed)") + " — scheduled run · ruled, not marked filed"
       in watchers[0],
       str(watchers))
    ok("the entry that WAS filed, and the entry nobody ruled, stay off the screen",
       shift("2026-09-07") not in out and shift("2026-09-05 (Fri)") not in out)

    section("A3 — the undated ask sorts last, and git supplies Alpha's date")
    undated = [l for l in asks if "MAIL WATCHER SELF-END" in l]
    ok("the undated ask prints \"?\" where its age would be",
       len(undated) == 1 and undated[0].startswith("    ?  "), str(undated))
    ok("and stands last in its group", bool(asks) and bool(undated) and asks[-1] is undated[0],
       asks[-1] if asks else "no ask was listed at all")
    blamed = [l for l in asks if "ALPHA NAMING" in l]
    ok("Alpha's undated line took the day it was committed (%s, %d d)"
       % (ALPHA_DAY, days(ALPHA_DAY)),
       len(blamed) == 1 and blamed[0].startswith("%5d d" % days(ALPHA_DAY)), str(blamed))

    section("A4 — one project at a time")
    out4 = run("--project", "alpha", label="--project alpha keeps only Alpha's asks",
               must=("ALPHA NAMING", "ALPHA DATED"),
               must_not=("STYLE CATALOG", "rule journal", "watcher", "IDEAS.md"))
    ok("its header counts only what it shows",
       head_of(out4).startswith("ASKED — 2 open · oldest %d d · " % days(ALPHA_DAY)), head_of(out4))

    section("A5 — only what is older than N days")
    out5 = run("--days", "10", label="--days 10 drops everything younger",
               must=("STYLE CATALOG", "ALPHA NAMING", "ALPHA DATED", "ANSWERABILITY LAW"),
               must_not=("PEN CHECK", "DRIVE GUARD", "a wiki page per agent",
                         "WATCHER RULINGS", "ROUTINES EXECUTE"))
    ok("an undated line is kept: its age is unknown, and hiding it would claim it is young",
       "MAIL WATCHER SELF-END" in out5)
    ok("the header counts the five that are left",
       head_of(out5).startswith("ASKED — 5 open · oldest %d d · 1 waiting on your word · "
                                % days(shift("2026-08-24"))), head_of(out5))

    section("A6 — every open item, ask or not")
    out6 = run("--everything", label="--everything adds the items that ask nobody",
               must=("a plain reminder to run the pulse", "one obvious next move",
                     "OLDEST OPEN ITEMS (9)"))
    ok("it still never counts a done item", "SOMETHING DONE" not in out6)
    ok("its header counts twelve open", head_of(out6).startswith("ASKED — 12 open · "), head_of(out6))

    section("A7 — every line, someday included")
    out7 = run("--all", label="--all shows the someday idea and names the group honestly",
               must=("IDEAS (incl. someday) (2)", "a Reminders door swept in by the pulse",
                     "a wiki page per agent"))
    ok("an idea already filed is never on this screen", "already went to Alpha" not in out7)
    ok("--all still says only one idea is unjudged",
       " · 1 idea unjudged · " in head_of(out7), head_of(out7))
    ok("--all shows every ask, with no \"showing\" note",
       len(group_lines(out7, "OLDEST OPEN ASKS")) == 7 and "showing" not in out7)

    section("A8 — the one line the hub says at wake")
    out8 = run("--count", label="--count prints the header and nothing else")
    ok("--count is exactly one line", len(lines_of(out8)) == 1, str(lines_of(out8)))
    ok("--count equals the default header",
       without_stamp(head_of(out8)) == without_stamp(head_of(out)),
       "%r vs %r" % (head_of(out8), head_of(out)))

    section("A9 — the bytes the tree page will read")
    out9 = run("--json", quiet=True, label="--json exits 0")
    try:
        data = json.loads(out9)
    except ValueError as exc:
        data = None
        ok("--json is valid JSON", False, str(exc))
    if data is not None:
        ok("--json is valid JSON", True)
        ok("it carries a header and the four groups",
           set(data) == {"header", "groups"} and
           set(data["groups"]) == {"waiting", "ideas", "asks", "watchers"}, str(list(data)))
        need = {"project", "lane", "urgent", "title", "date", "age_days", "where", "source"}
        rows = [r for g in data["groups"].values() for r in g]
        ok("every item carries the eight fields the brief names",
           bool(rows) and all(need <= set(r) for r in rows),
           str(sorted(need - set(rows[0]))) if rows else "no items")
        ok("the header line in the JSON is the header line on the screen",
           without_stamp(data["header"]["line"]) == without_stamp(head_of(out)))
        ok("the counts in the JSON are the counts in the header",
           (data["header"]["open"], data["header"]["waiting"], data["header"]["ideas_unjudged"],
            data["header"]["watcher_unfiled"]) == (10, 2, 1, 1), str(data["header"]))
        ok("--json is never truncated: all ten open rows are there",
           len(data["groups"]["waiting"]) + len(data["groups"]["ideas"])
           + len(data["groups"]["asks"]) == 10)
        ok("an undated item says so with a null age",
           any(r["age_days"] is None and "MAIL WATCHER" in r["title"] for r in rows))
        ok("every where reads <path>:<line>",
           all(re.search(r":\d+$", r["where"]) for r in rows))

    section("A10 — a project with no To do, and a project with no STATUS: silence")
    ok("Beta's checkbox under ## Now is not read", "Beta" not in out and "Beta" not in out6)
    ok("Gamma, having no STATUS.md, says nothing", "Gamma" not in out and "Gamma" not in out6)
    ok("a loose file in the projects root is not a project", "notes.txt" not in out6)
    ok("nothing was reported unread", "unread:" not in out and "unread:" not in out6)

    section("A11 — it wrote nothing: the scratch tree, and the live files")
    after_tree = tree_shas(SCRATCH)
    gone = sorted(set(before_tree) - set(after_tree))
    new = sorted(set(after_tree) - set(before_tree))
    changed = sorted(k for k in before_tree if k in after_tree and before_tree[k] != after_tree[k])
    ok("every one of the %d scratch files is byte for byte what it was" % len(before_tree),
       not changed and not gone, "changed %s gone %s" % (changed, gone))
    ok("and asked.py created no file of its own (not even a cache)", not new, str(new))
    hub = live_hub()
    watched = ("STATUS.md", "IDEAS.md", "dossier/TAUGHT.md")
    before_live = {name: sha(hub / name) for name in watched}

    section("A12 — a read-only smoke run on this machine's real roots")
    real = run(live=True, quiet=True)
    print("   " + head_of(real))
    ok("the real roots answer, exit 0", run.code == 0, real[:200])
    ok("in under five seconds (%0.2f s)" % run.seconds, run.seconds < 5.0)
    ok("with a header of its own", head_of(real).startswith("ASKED — "), head_of(real))
    after_live = {name: sha(hub / name) for name in watched}
    for name in watched:
        ok("live %s untouched by that run (%s)" % (name, before_live[name]),
           before_live[name] == after_live[name],
           "%s → %s (another session may have written it — check its mtime)"
           % (before_live[name], after_live[name]))

    print("\n===== GATE =====")
    n_ok = sum(1 for c in checks if c)
    for f in fails:
        print("  FAIL  %s" % f)
    print("  scratch: %s%s" % (SCRATCH, "" if keep else "  (removed; --keep holds it)"))
    print("  the live hub was read and never written: %s" % hub)
    if not keep:
        remove_tree(SCRATCH)
    if fails:
        print("GATE FAILED: %d/%d checks — asked.py is not proven." % (n_ok, len(checks)))
        print("%d checks · %d passed · %d failed" % (len(checks), n_ok, len(fails)))
        return 1
    print("GATE PASSED: %d/%d checks — asked.py mirrors the four sources, oldest first, "
          "and writes nothing." % (n_ok, len(checks)))
    print("%d checks · %d passed · %d failed" % (len(checks), n_ok, len(fails)))
    return 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    remove_tree(SCRATCH)


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
