#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-ideas.py — proof for tools/ideas.py, hermetic: nothing live is read or written.

    python3 tools/gate-ideas.py

A scratch hub (IDEAS.md absent) and a scratch projects root holding one Dummy
project whose STATUS.md carries a "## To do" heading are built in a temp dir;
every command runs with --hub and --projects pointed there, so the live
IDEAS.md, the live stamps and every real STATUS.md are out of reach of this
proof (gate-coordination.py's rule: a proof that can touch live state is not a
proof).

What it proves, in order:
  add → --count says "1 new · 1 total" · --list shows it as #1
  file #1 to Dummy → the To do line sits DIRECTLY under "## To do" and the idea
  line reads "filed → Dummy … · filed <today>", the hour, the words and the via
  unchanged · someday / drop / done rewrite ONLY the status word · a "!" idea is
  raised by --count --urgent · --sweep-reminders prints one line and exits 0 ·
  two adds number #1 then #2, and a filed line still counts as #1.

Stdlib only, OS-neutral. Exit 1 on any failed check.
"""
import io
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:                                   # cp1252 console: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HUB = Path(__file__).resolve().parent.parent
PY = sys.executable
SCRATCH = Path(tempfile.gettempdir()) / "exocortex-gate-ideas"
SCR_HUB, SCR_PROJ = SCRATCH / "hub", SCRATCH / "Projects"
TODAY = datetime.now().astimezone().strftime("%Y-%m-%d")
checks, fails = [], []

STATUS_SEED = """# Dummy

## Now

A scratch project the ideas gate files into.

## To do

- [ ] an item that was here before the gate ran

## Important

Nothing.
"""


def ok(name, cond, detail=""):
    checks.append(bool(cond))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, ("  — " + detail) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)


def run(*args, expect=0, label=None, must=(), must_not=(), quiet=False):
    """One ideas.py command against the scratch hub, its real output shown."""
    argv = [PY, str(HUB / "tools" / "ideas.py")] + list(args) + \
           ["--hub", str(SCR_HUB), "--projects", str(SCR_PROJ)]
    shown = " ".join(a if " " not in a else '"%s"' % a for a in args)
    print("\n$ ideas.py %s" % shown)
    p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    if not quiet:
        print(out.rstrip() or "(no output)")
    bad = []
    if expect is not None and p.returncode != expect:
        bad.append("exit %d, expected %d" % (p.returncode, expect))
    bad += ["missing %r" % m for m in must if m not in out]
    bad += ["must not contain %r" % m for m in must_not if m in out]
    if label:
        ok(label, not bad, "; ".join(bad))
    return out


def ideas_lines():
    try:
        return io.open(SCR_HUB / "IDEAS.md", encoding="utf-8").read().splitlines()
    except OSError:
        return []


def idea_line(n):
    """The nth idea line of the scratch file, or ''."""
    rows = [l for l in ideas_lines() if l.startswith("- 20")]
    return rows[n - 1] if 0 < n <= len(rows) else ""


def status_lines():
    return io.open(SCR_PROJ / "Dummy" / "STATUS.md", encoding="utf-8").read().splitlines()


def section(t):
    print("\n" + "=" * 8 + " " + t + " " + "=" * 8)


def fresh_scratch():
    if SCRATCH.exists():
        shutil.rmtree(str(SCRATCH))
    SCR_HUB.mkdir(parents=True)
    (SCR_PROJ / "Dummy").mkdir(parents=True)
    io.open(SCR_PROJ / "Dummy" / "STATUS.md", "w", encoding="utf-8", newline="\n").write(STATUS_SEED)
    print("   scratch hub: %s" % SCR_HUB)
    print("   scratch projects: %s (Dummy/STATUS.md seeded with a ## To do section)" % SCR_PROJ)
    ok("the scratch hub starts with no IDEAS.md", not (SCR_HUB / "IDEAS.md").exists())


def main(argv):
    if "--help" in argv:
        print(__doc__)
        return 0
    print("gate-ideas · hub %s · python %s" % (HUB, sys.version.split()[0]))
    fresh_scratch()

    section("A — capture answers in one line and writes the file")
    run("--add", "a wiki page per agent", "--via", "NORTH/GATE",
        label="add answers \"noted · #1 · Tuesday judges it\"", must=("noted · #1 · Tuesday judges it",))
    head = ideas_lines()[:6]
    ok("IDEAS.md was created with its six-line header",
       len(head) == 6 and head[0].startswith("# IDEAS") and all(l.startswith("#") for l in head),
       str(head[:2]))
    line1 = idea_line(1)
    print("   line 1: %s" % line1)
    ok("the line carries date, hour, status new, the words and the via",
       line1.startswith("- %s " % TODAY) and " · new · a wiki page per agent · via NORTH/GATE" in line1, line1)

    section("B — count and list see it")
    run("--count", label="--count says \"1 new · 1 total\"", must=("1 new · 1 total",))
    run("--list", label="--list (default --new) shows it as #1", must=("#1", "a wiki page per agent"))

    section("C — filing puts the To do line under ## To do and rewrites the status word")
    run("--file", "1", "--to", "Dummy", "--item", "draft the wiki page",
        label="file #1 → Dummy answers in one line", must=("filed · #1 → Dummy", "## To do"))
    body = status_lines()
    head_at = next((i for i, l in enumerate(body) if l.strip().lower() == "## to do"), -1)
    want = "- [ ] draft the wiki page (idea %s)" % TODAY
    print("   STATUS.md around the heading: %r" % body[head_at:head_at + 3])
    ok("the To do line sits DIRECTLY under \"## To do\"", head_at >= 0 and body[head_at + 1] == want,
       "%r" % (body[head_at + 1] if head_at >= 0 else None))
    ok("the item that was there before is still there",
       "- [ ] an item that was here before the gate ran" in body)
    filed = idea_line(1)
    print("   line 1 now: %s" % filed)
    ok("the idea line reads \"filed → Dummy\" and \"· filed %s\"" % TODAY,
       " · filed → Dummy · " in filed and filed.endswith("· filed %s" % TODAY), filed)
    ok("only the status word changed — hour, words and via are untouched",
       filed.startswith(line1.split(" · ")[0]) and "a wiki page per agent · via NORTH/GATE" in filed, filed)
    run("--count", label="a filed idea is no longer new: \"0 new · 1 total\"", must=("0 new · 1 total",))
    run("--list", label="--list says so plainly", must=("no new ideas",))
    run("--list", "--all", label="--list --all still shows it", must=("#1", "filed → Dummy"))

    section("D — someday / drop / done rewrite only the status word")
    for verb, word in (("--someday", "someday"), ("--drop", "dropped"), ("--done", "done")):
        run(verb, "1", label="%s rewrites #1 to %s" % (verb, word), must=("#1 · %s" % word,))
        got = idea_line(1)
        print("   line 1 now: %s" % got)
        ok("%s: status is \"%s\", the words and via are untouched, verb dated today" % (verb, word),
           " · %s · a wiki page per agent · via NORTH/GATE · %s %s" % (word, word, TODAY) in got, got)
    ok("the STATUS.md To do line is untouched by those rewrites", want in status_lines())

    section("E — an urgent idea is raised, and numbering keeps counting")
    run("--add", "! the transfer drive is nearly full", "--via", "NORTH/GATE",
        label="an urgent add answers \"raised for the next wake\"",
        must=("noted · #2 · raised for the next wake",))
    run("--count", "--urgent", label="--count --urgent prints the urgent new line",
        must=("1 new · 2 total", "! #2", "the transfer drive is nearly full"))
    run("--add", "a third thought", label="a third add is #3", must=("noted · #3",))
    run("--count", "--urgent", label="the third, not urgent, is not raised",
        must=("2 new · 3 total",), must_not=("#3",))
    ok("three lines on file, none deleted", len([l for l in ideas_lines() if l.startswith("- 20")]) == 3)

    section("F — the parked door and the plain errors")
    run("--sweep-reminders", label="the sweep stub prints one line and exits 0",
        expect=0, must=("sweep-reminders: parked (v2)",))
    ok("the sweep printed exactly one line",
       len([l for l in run("--sweep-reminders", quiet=True).strip().splitlines() if l.strip()]) == 1)
    run("--file", "9", "--to", "Dummy", "--item", "x", expect=1,
        label="filing an idea that does not exist: one sentence, exit 1", must=("no idea #9",))
    run("--file", "2", "--to", "Nowhere", "--item", "x", expect=1,
        label="filing to a project that is not there: one sentence, exit 1", must=("no STATUS.md for Nowhere",))
    ok("a refused filing left idea #2 new", " · new · " in idea_line(2))

    print("\n===== GATE =====")
    n_ok = sum(1 for c in checks if c)
    for f in fails:
        print("  FAIL  %s" % f)
    print("  scratch: %s (hermetic — the live IDEAS.md and every real STATUS.md were never opened)%s"
          % (SCRATCH, "" if "--keep" in argv else " — removed; --keep holds it"))
    print("GATE ideas: %d/%d %s" % (n_ok, len(checks), "PASS" if not fails else "FAIL"))
    print("%d checks · %d passed · %d failed" % (len(checks), n_ok, len(fails)))
    return 1 if fails else 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    shutil.rmtree(str(SCRATCH), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
