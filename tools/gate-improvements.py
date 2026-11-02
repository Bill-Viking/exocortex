#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-improvements.py — proof for improvements.py and its two hooks.

    python3 gate-improvements.py            (from any folder)
    python3 gate-improvements.py --keep     leave the scratch world for inspection

Hermetic. Everything is built in a fresh temp world: a scratch HOME whose
machine.json names a scratch hub and a scratch projects root, queue fixtures
with one row per state plus the edge cases, and copies of the two patched tools.
Nothing live is written — the real hub is only READ, and only where the tool
itself reads it (does a brief file exist; what does the real queue say).

The order:
  A  each state derives correctly, DONE beating an old BUILDING note   (L1)
  B  the count line, exactly, with and without stopped / unreadable    (L2)
  C  the page: every row out once, no wall of text, dates, black hole  (L3 L4 L5)
  D  the state file: atomic, changed moves only on a real change       (L6)
  H  a note's «plain-words title» is the purpose, and only that (refinement 1)
  E  hook A: the board run survives a broken ledger                    (L7)
  F  hook B: one chip, right numbers, the tree otherwise untouched     (L8)
  G  a COPY of the real queue: every `| BQ-` line comes out            (L9)
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
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

try:                                   # a cp1252 console: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PY = sys.executable


def subjects():
    """The four files under test, found by EXISTENCE in either layout —
    never by a path typed into this file.

      scratch   all four beside the gate (scratch/bq026-build/)
      installed the gate, improvements.py and collect-openers.py in <hub>/tools,
                orchestrator.py at the hub root beside them

    Returns (layout word, improvements.py, collect-openers.py, orchestrator.py)."""
    tool, collector = HERE / "improvements.py", HERE / "collect-openers.py"
    if (HERE / "orchestrator.py").is_file():
        return "scratch", tool, collector, HERE / "orchestrator.py"
    if (HERE.parent / "orchestrator.py").is_file():
        return "installed", tool, collector, HERE.parent / "orchestrator.py"
    print("gate-improvements: no orchestrator.py beside the gate (%s) or above it (%s) "
          "— nothing to test." % (HERE, HERE.parent))
    raise SystemExit(2)


def engine_hub():
    """The hub whose ENGINE this gate borrows read-only: the sibling tool modules
    the collector imports, evidence.py, and the real queue section G copies. Read
    from the one record first (~/orchestrator-sync/machine.json), as every tool
    reads it; failing that, walked up from the gate. None when neither answers —
    said out loud, never guessed."""
    seen = []
    try:
        with io.open(str(Path.home() / "orchestrator-sync" / "machine.json"),
                     encoding="utf-8") as fh:
            recorded = (json.load(fh).get("roots") or {}).get("orchestrator")
        if recorded:
            seen.append(Path(recorded))
    except Exception:
        pass
    seen += [HERE.parent, HERE.parents[1] if len(HERE.parents) > 1 else HERE]
    for candidate in seen:
        if ((candidate / "tools" / "exo_common.py").is_file()
                and (candidate / "evidence.py").is_file()):
            return candidate
    return None


LAYOUT, TOOL, COLLECTOR, ORCH = subjects()
BUILD = HERE                                     # where the subjects were found
HUB = engine_hub()                               # the real hub, read-only
KEEP = "--keep" in sys.argv[1:]
VOID = {"meta", "br", "hr", "img", "input", "link", "source", "wbr"}

checks, fails = [], []
SCRATCH = Path(tempfile.mkdtemp(prefix="exocortex-gate-improvements-"))
# The gate's own registry: the owner whose words the fixtures quote, and nobody
# else's. The tool reads it through EXO_REGISTRY_JSON — in this process and in
# every child — so the proof is the same whatever this machine's registry names.
FIXTURE_REGISTRY = {"version": 1, "owner": {"name": "Wren", "short": "wren", "aliases": []}}
REGISTRY_FILE = SCRATCH / "registry.json"
TODAY = datetime.now().astimezone().date()


def ok(name, cond, detail=""):
    checks.append(bool(cond))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                           ("  — " + str(detail)) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)


def section(title):
    print("\n── %s " % title + "─" * max(0, 64 - len(title)))


def day(n):
    return (TODAY - timedelta(days=n)).isoformat()


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def run(args, env=None, cwd=None, timeout=300):
    base = dict(os.environ)
    for key, value in (env or {}).items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = str(value)
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=base,
                          cwd=str(cwd) if cwd else None, timeout=timeout)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def tool(*args, **kw):
    """improvements.py, always against the scratch hub."""
    return run([PY, str(TOOL)] + list(args), cwd=kw.get("cwd") or SCRATCH)


def load_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("improvements_under_test", str(TOOL))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# the fixtures
# --------------------------------------------------------------------------

HEAD = ("| id | arc | brief | gates | model | status | note |\n"
        "|---|---|---|---|---|---|---|\n")

ROWS = [
    # (id, status, note)  — file order is priority, exactly as the queue says
    ("BQ-900", "running GATE %sT09:00:00-07:00" % day(0),
     "Wren %s: \"start this one\" — the row the runner is on" % day(3)),
    ("BQ-901", "seeded",
     "BUILDING in the gate sitting since %s (the note says so, the status does not)" % day(1)),
    ("BQ-902", "ruled by ACT — Gate: the ruling %sT09:00:00-07:00" % day(5),
     "ruled %s · waiting on the runner" % day(5)),
    ("BQ-903", "seeded", "%s · its brief is on disk, so it is briefed" % day(4)),
    ("BQ-904", "seeded",
     "%s · the oldest thing still waiting — nobody has ruled it" % day(12)),
    ("BQ-905", "seeded", "no date anywhere in this note, so none is invented"),
    ("BQ-906", "stop: which machine owns this?", "%s · stopped on one question" % day(2)),
    ("BQ-907", "paused-cap", "%s · the run met the token cap" % day(2)),
    ("BQ-908", "done abc1234",
     "%s · BUILT · gate 12/12 · Wren \"that is what I need\"" % day(6)),
    ("BQ-909", "done HUB",
     "%s · built by the hub · BUILDING appears in this note too, and DONE still wins" % day(7)),
]
BRIEF_OF = {"BQ-903": "design/gate-on-disk.md"}
EVIL = ("%s · <script>alert(\"x\")</script> & `backticks` & <b>angle</b> \"quotes\" "
        "— the hostile note" % day(0))


def row_line(rid, status, note):
    brief = BRIEF_OF.get(rid, "design/%s-brief.md" % rid.lower())
    return "| %s | Gate/%s | %s | tools/gate-%s.py | opus | %s | %s |\n" % (
        rid, rid[-3:], brief, rid[-3:].lower(), status, note + " · exo: later")
    # every fixture row carries its EXO word : the fixtures are dated relative to today and
    # would otherwise cross the EXO snapshot date and gain an "exo unjudged" clause the exact-line checks do not expect


def fixture_full():
    """One row per state, plus the three rows the black-hole rule is for."""
    text = HEAD + "".join(row_line(*r) for r in ROWS)
    text += "| BQ-910 | Gate/910 | design/bq-910-brief.md | tools/gate-910.py | seeded | a row with one cell missing |\n"
    text += "| BQ-911 | Gate/911 | design/bq-911-brief.md | tools/gate-911.py | opus | seeded | the closing pipe is missing\n"
    text += row_line("BQ-912", "seeded", EVIL)
    return text


def fixture_plain():
    """The same list with nothing stopped and nothing broken."""
    keep = [r for r in ROWS if r[0] not in ("BQ-906", "BQ-907")]
    return HEAD + "".join(row_line(*r) for r in keep)


FULL_LINE = ("improvements: 13 listed · 2 done · 2 building · 2 briefed · 3 waiting · "
             "oldest waiting 12 d · 2 stopped · 2 UNREADABLE")
PLAIN_LINE = ("improvements: 8 listed · 2 done · 2 building · 2 briefed · 2 waiting · "
              "oldest waiting 12 d")
IDS = [r[0] for r in ROWS] + ["BQ-910", "BQ-911", "BQ-912"]


# --------------------------------------------------------------------------
# reading a rendered page
# --------------------------------------------------------------------------

class Texts(HTMLParser):
    """Every text node of the page, and whether it sits inside an expander."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.outside, self.inside = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        cls = (dict(attrs).get("class") or "").split()
        self.stack.append((tag, "exp" in cls, tag in ("script", "style")))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        text = data.strip()
        if not text or any(s[2] for s in self.stack):
            return
        (self.inside if any(s[1] for s in self.stack) else self.outside).append(text)


def texts_of(html):
    parser = Texts()
    parser.feed(html)
    return parser.outside, parser.inside


def groups_of(html):
    return re.findall(r'<h2 class="grp[^"]*"><span class="mk"></span>(.*?)<span', html)


def mask(html):
    """The one volatile mark on a tree page: the minute it was generated."""
    return re.sub(r"Generated [^·]+·", "Generated — ·", html)


# --------------------------------------------------------------------------
# A — the states
# --------------------------------------------------------------------------

def section_a(mod, qdir, root):
    section("A — each state derives from the queue (L1)")
    rows = {r["id"] or r["key"]: r for r in mod.read_rows(qdir / "full.md", root)}
    want = {"BQ-900": "BUILDING", "BQ-901": "BUILDING", "BQ-902": "BRIEFED",
            "BQ-903": "BRIEFED", "BQ-904": "WAITING", "BQ-905": "WAITING",
            "BQ-906": "STOPPED", "BQ-907": "STOPPED", "BQ-908": "DONE",
            "BQ-909": "DONE", "BQ-912": "WAITING"}
    why = {"BQ-900": "status `running`", "BQ-901": "the note carries BUILDING",
           "BQ-902": "status `ruled by`", "BQ-903": "its brief file is on disk",
           "BQ-904": "seeded, no brief", "BQ-905": "seeded, no brief",
           "BQ-906": "status `stop:`", "BQ-907": "status `paused-cap`",
           "BQ-908": "status `done <sha>`", "BQ-909": "status `done HUB`",
           "BQ-912": "seeded, no brief"}
    for rid in sorted(want):
        got = rows.get(rid, {}).get("state")
        ok("%s → %-8s (%s)" % (rid, want[rid], why[rid]), got == want[rid], "got %s" % got)
    ok("a DONE row whose note says BUILDING is still DONE",
       rows["BQ-909"]["state"] == "DONE" and "BUILDING" in rows["BQ-909"]["note"])
    ok("BQ-903 is BRIEFED only because the file is really there",
       (Path(root) / BRIEF_OF["BQ-903"]).is_file())
    ok("the two broken lines are UNREADABLE",
       [r["state"] for r in mod.read_rows(qdir / "full.md", root) if r["why"]] ==
       ["UNREADABLE", "UNREADABLE"])
    ok("proof on a done row = the sha plus the gate count",
       rows["BQ-908"]["proof"] == "abc1234 · gate 12/12", rows["BQ-908"]["proof"])
    ok("proof on a done-HUB row with no count = HUB",
       rows["BQ-909"]["proof"] == "HUB", rows["BQ-909"]["proof"])
    ok("heard = the first date in the note",
       rows["BQ-904"]["heard"] == day(12) and rows["BQ-904"]["age"] == 12)
    ok("Wren's words are taken whole, apostrophes and all",
       mod.said_of("Wren 2026-09-12 ('let's do as much as we can')")
       == "let's do as much as we can",
       mod.said_of("Wren 2026-09-12 ('let's do as much as we can')"))
    ok("purpose is the first clause, never the raw note",
       rows["BQ-904"]["purpose"] == "%s · the oldest thing still waiting" % day(12),
       rows["BQ-904"]["purpose"])
    long_note = "x" * 400
    ok("a note with no clause break is cut at 110 characters",
       len(mod.purpose_of(long_note)) <= 111 and mod.purpose_of(long_note).endswith("…"))


# --------------------------------------------------------------------------
# B — the count line
# --------------------------------------------------------------------------

def section_b(qdir, hub, root):
    section("B — the count line, exactly (L2)")
    code, out = tool("--count", "--queue", qdir / "full.md", "--hub", hub, "--root", root)
    ok("--count on the full fixture is exact", out.strip() == FULL_LINE, out.strip())
    ok("--count exits 0", code == 0, "exit %d" % code)
    code, out = tool("--count", "--queue", qdir / "plain.md", "--hub", hub, "--root", root)
    ok("no stopped and no unreadable: neither tail is printed",
       out.strip() == PLAIN_LINE, out.strip())
    write(qdir / "donly.md", HEAD + row_line("BQ-920", "done HUB", "%s · built" % day(1)))
    code, out = tool("--count", "--queue", qdir / "donly.md", "--hub", hub, "--root", root)
    ok("nothing waiting says so, and invents no age",
       out.strip() == ("improvements: 1 listed · 1 done · 0 building · 0 briefed · "
                       "0 waiting · oldest waiting none"), out.strip())
    write(qdir / "undated.md", HEAD + row_line("BQ-921", "seeded", "no date at all here"))
    code, out = tool("--count", "--queue", qdir / "undated.md", "--hub", hub, "--root", root)
    ok("a waiting row with no date is said, never dated",
       out.strip() == ("improvements: 1 listed · 0 done · 0 building · 0 briefed · "
                       "1 waiting · oldest waiting date not recorded"), out.strip())
    code, out = tool("--count", "--queue", SCRATCH / "nowhere.md", "--hub", hub)
    # A queue that is not there yet is the empty state of a new hub, not a
    # fault: the ledger says so in one line and exits 0 (an older ledger
    # called this a failure, exit 1).
    ok("a missing queue is one plain line, the empty state, exit 0",
       code == 0 and out.strip() == "improvements: 0 listed · no queue file yet", out.strip())
    code, out = tool("--help")
    ok("--help exits 0 and says what the verbs are",
       code == 0 and "--count" in out and "--write" in out and "--since" in out)


# --------------------------------------------------------------------------
# C — the page
# --------------------------------------------------------------------------

def section_c(hub, qdir, root):
    section("C — the page: every row comes out, once (L3 L4 L5)")
    code, out = tool("--write", "--queue", qdir / "full.md", "--hub", hub, "--root", root)
    ok("--write prints the same one line and exits 0",
       code == 0 and out.strip() == FULL_LINE, out.strip())
    page = io.open(str(hub / "improvements.html"), encoding="utf-8").read()
    missing = [i for i in IDS if page.count('id="r-%s"' % i) != 1]
    ok("every one of the 13 fixture rows is on the page exactly once",
       not missing, "not once: %s" % missing)
    outside, inside = texts_of(page)
    longest = max(outside, key=len) if outside else ""
    ok("no text node outside an expander is longer than 300 characters",
       len(longest) <= 300, "%d chars: %.80s…" % (len(longest), longest))
    ok("the full notes are inside the expanders", any(len(t) > 300 for t in inside) or
       any(EVIL[:30] in t for t in inside))
    ok("the groups are in the brief's order, and only the ones with rows",
       groups_of(page) == ["BUILDING NOW", "BRIEFED, NEXT", "WAITING", "STOPPED",
                           "UNREADABLE ROWS", "DONE"], groups_of(page))
    ok("the BUILDING group is the only amber marker",
       page.count('class="grp building"') == 1)
    ok("a row with no date says so, and shows no number (L4)",
       re.search(r'id="r-BQ-905".*?date not recorded', page, re.S) is not None)
    ok("a dated row shows the date and its age in days",
       re.search(r'id="r-BQ-904".*?heard %s · 12 d' % day(12), page, re.S) is not None)
    unread = page[page.index("UNREADABLE ROWS"):page.index(">DONE<")]
    lines = fixture_full().splitlines()
    n910 = 1 + next(i for i, l in enumerate(lines) if l.startswith("| BQ-910"))
    n911 = 1 + next(i for i, l in enumerate(lines) if l.startswith("| BQ-911"))
    ok("the malformed row is under UNREADABLE ROWS with its line number (L5)",
       ("line %d" % n910) in unread and "7 cells expected" in unread, unread[:200])
    ok("the broken-pipe row is there too, with its own line number",
       ("line %d" % n911) in unread
       and "does not open and close with a pipe" in unread, unread[:400])
    ok("a broken row keeps its id, so it is still the same row tomorrow",
       'id="r-BQ-911"' in page and ">BQ-911<" in unread)
    ok("both broken rows are counted in the 13 listed", FULL_LINE.startswith("improvements: 13 listed"))
    ok("the raw text of a broken row is kept, so nothing is lost",
       "the closing pipe is missing" in page)
    ok("done rows are struck through and carry their proof",
       page.count('class="row done"') == 2 and "proof · abc1234 · gate 12/12" in page)
    ok("Wren's words ride on the row that has them",
       "“that is what I need”" in page and "“start this one”" in page)
    ok("a hostile note cannot break the page open",
       "<script>alert" not in page and "&lt;script&gt;alert(&quot;x&quot;)" in page
       and "&amp;" in page)
    waiting = re.findall(r'id="r-(BQ-9\d\d)"', page[page.index(">WAITING<"):page.index(">STOPPED<")])
    ok("waiting is oldest heard first, the undated row last",
       waiting == ["BQ-904", "BQ-912", "BQ-905"], waiting)
    ok("the page is self-contained: no font, script or style is fetched",
       "http://" not in page and "https://" not in page and "<img" not in page
       and "src=" not in page and "<link" not in page)
    ok("the page re-reads itself and keeps the reader's place",
       'http-equiv="refresh" content="300"' in page and "sessionStorage" in page
       and page.count("try{") >= 3)
    ok("the page says which file it was read from",
       "full.md" in page.split("<footer>")[-1])
    ok("every row opens to its brief, its gate and its line in the queue",
       page.count("<dt>brief</dt>") == 11 and page.count("<dt>gate</dt>") == 11
       and page.count("<dt>line</dt>") == 13)
    # the black hole, closed: one id twice is two rows, not one
    write(qdir / "twice.md", HEAD + row_line("BQ-930", "seeded", "%s · the first" % day(1))
          + row_line("BQ-930", "done HUB", "%s · the same id again" % day(1)))
    code, out = tool("--write", "--queue", qdir / "twice.md", "--hub", hub / "twice",
                     "--root", root)
    twice = io.open(str(hub / "twice" / "improvements.html"), encoding="utf-8").read()
    ok("the same id twice comes out twice, the second called unreadable",
       out.strip().endswith("1 UNREADABLE") and "is already on line 3" in twice, out.strip())


# --------------------------------------------------------------------------
# D — the state file
# --------------------------------------------------------------------------

def section_d(hub, qdir, root):
    section("D — the state file: what changed, and when (L6)")
    state_file = hub / "improvements-state.json"
    first = json.loads(io.open(str(state_file), encoding="utf-8").read())
    ok("one entry per row, keyed by id", len(first["rows"]) == 13)
    ok("every entry carries first_seen and changed",
       all(e.get("first_seen") and e.get("changed") for e in first["rows"].values()))
    ok("no temp file is left behind (the write is atomic)",
       not list(Path(hub).glob("*.tmp-*")))
    time.sleep(1.1)                       # so a second stamp cannot read the same
    tool("--write", "--queue", qdir / "full.md", "--hub", hub, "--root", root)
    again = json.loads(io.open(str(state_file), encoding="utf-8").read())
    same = [k for k in first["rows"]
            if first["rows"][k]["changed"] != again["rows"][k]["changed"]]
    ok("a second write with nothing new leaves every `changed` untouched", not same, same)
    before = again["written"]
    flipped = fixture_full().replace("| BQ-904 | Gate/904 | design/bq-904-brief.md | tools/gate-904.py | opus | seeded |",
                                     "| BQ-904 | Gate/904 | design/bq-904-brief.md | tools/gate-904.py | opus | done zzz9999 |")
    ok("the flip fixture really differs", flipped != fixture_full())
    write(qdir / "full.md", flipped)
    time.sleep(1.1)
    code, out = tool("--write", "--queue", qdir / "full.md", "--hub", hub, "--root", root)
    third = json.loads(io.open(str(state_file), encoding="utf-8").read())
    moved = [k for k in again["rows"]
             if again["rows"][k]["changed"] != third["rows"][k]["changed"]]
    ok("a status flip moves that row's `changed`, and only that row's",
       moved == ["BQ-904"], moved)
    ok("the state file remembers what it was before",
       third["rows"]["BQ-904"]["prev"] == "WAITING"
       and third["rows"]["BQ-904"]["state"] == "DONE")
    ok("first_seen survives the flip",
       third["rows"]["BQ-904"]["first_seen"] == first["rows"]["BQ-904"]["first_seen"])
    ok("the count line followed the flip",
       out.strip().startswith("improvements: 13 listed · 3 done · 2 building · 2 briefed · 2 waiting"),
       out.strip())
    code, out = tool("--since", before, "--hub", hub, "--queue", qdir / "full.md", "--root", root)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    ok("--since reports the change in the brief's own shape",
       code == 0 and len(lines) == 1
       and re.match(r"^BQ-904 · WAITING → DONE · \d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", lines[0]),
       out.strip())
    code, out = tool("--since", "2090-01-01", "--hub", hub, "--queue", qdir / "full.md",
                     "--root", root)
    ok("nothing since a date in the future, said in one line",
       code == 0 and out.strip() == "no change since 2090-01-01", out.strip())
    code, out = tool("--since", "yesterday-ish", "--hub", hub, "--queue", qdir / "full.md",
                     "--root", root)
    ok("a date it cannot read is one plain line and exit 1",
       code == 1 and len(out.strip().splitlines()) == 1, out.strip())
    page = io.open(str(hub / "improvements.html"), encoding="utf-8").read()
    ok("the page is whole after every rewrite",
       page.rstrip().endswith("</html>") and page.count("<!DOCTYPE html>") == 1)
    write(qdir / "full.md", fixture_full())              # put the fixture back


# --------------------------------------------------------------------------
# the world the two hooks run in
# --------------------------------------------------------------------------

FACTS = {}

# Hook B, as it stands in the collector today — the gate can therefore take it
# back out and render the collector without it, in any layout and after any
# install. Hook B inserted the function, a slot at the end of the counts strip
# and the call that fills it; the owner's letter chip has since come to share
# that slot, written just before the ledger's (`<the owner chip> +
# improvements_chip(roots)`), so taking hook B out now leaves the slot to the
# owner's chip: two insertions come out, the function and the call. The
# function is taken out alone — the page's other helpers (the postman's facts,
# the guard's) have since come to stand between it and html_page.
HOOK_FUNC = re.compile(r"\ndef improvements_chip\(roots\):.*?\n(?=\n\ndef )", re.S)
# What of the ledger a collector without the hook must not carry: the call, and
# the ledger's own module. (A sibling's docstring may still NAME the chip.)
LEDGER_LEFT = re.compile(r"improvements_chip\(roots\)|\"improvements\"|improvements\.py")
HOOK_ARG = re.compile(r"(\w+_chip) \+ improvements_chip\(roots\)\)\)[ \t]*"
                      r"# BQ-026 hook B: the ledger's chip")


def unpatch(source):
    """(the collector without hook B, what was wrong). Each of the hook's
    insertions must be there exactly once, and nothing of the ledger may
    survive their removal — otherwise this is not the hook the gate knows."""
    problems = []
    if len(HOOK_FUNC.findall(source)) != 1:
        problems.append("the improvements_chip function is not there exactly once")
    out = HOOK_FUNC.sub("\n", source, count=1)
    if len(HOOK_ARG.findall(out)) != 1:
        problems.append("the call into the strip's last slot is not there exactly once")
    out = HOOK_ARG.sub(r"\1))", out, count=1)
    if LEDGER_LEFT.search(out):
        problems.append("the ledger is still named after the hook came out")
    return out, problems


def build_world(world):
    hub, projects, home = world / "hub", world / "projects", world / "home"
    for folder in (hub / "tools", hub / "design", hub / "dossier", projects / "alpha",
                   home / "orchestrator-sync", home / ".claude" / "projects",
                   world / "vol", world / "out"):
        folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(COLLECTOR), str(hub / "tools" / "collect-openers.py"))
    # The baseline is the collector with hook B taken back out — not a second file
    # on disk, which after an install is the patched one too (section F).
    base, problems = unpatch(io.open(str(COLLECTOR), encoding="utf-8").read())
    write(hub / "tools" / "collect-openers-orig.py", base)
    FACTS["unpatch"] = problems
    for name in ("opener_carriers.py", "exo_common.py", "grok_sessions.py"):
        if name == "opener_carriers.py" and not (HUB / "tools" / name).is_file():
            continue      # imported under a guard: without it the collector reads folders alone
        shutil.copy2(str(HUB / "tools" / name), str(hub / "tools" / name))
    # The loader the tools read the person's names through travels with them
    # (a world that copies the tools and not the loader cannot import them);
    # a hub from before the loader has none to copy.
    for loader in (HERE / "exo_registry.py", HUB / "tools" / "exo_registry.py"):
        if loader.is_file():
            shutil.copy2(str(loader), str(hub / "tools" / "exo_registry.py"))
            break
    # …and the path resolver, which the tools read the machine record through
    # from their first line; a hub from before the resolver has none.
    for resolver in (HERE / "exo_paths.py", HUB / "tools" / "exo_paths.py"):
        if resolver.is_file():
            shutil.copy2(str(resolver), str(hub / "tools" / "exo_paths.py"))
            break
    shutil.copy2(str(TOOL), str(hub / "tools" / "improvements.py"))
    shutil.copy2(str(ORCH), str(hub / "orchestrator.py"))
    shutil.copy2(str(HUB / "evidence.py"), str(hub / "evidence.py"))
    write(home / "orchestrator-sync" / "machine.json",
          json.dumps({"name": "gate", "os": "Gate",
                      "roots": {"orchestrator": str(hub), "projects": str(projects),
                                "claude": str(home / ".claude")}}, indent=1))
    write(hub / "design" / "BUILD-QUEUE.md", fixture_full())
    write(hub / "design" / BRIEF_OF["BQ-903"].split("/", 1)[1], "# a brief that exists\n")
    write(hub / "STATUS.md", "# STATUS\n\n## Now\n\nThe gate hub.\n\n## To do\n\n- [ ] a hub item\n")
    write(hub / "INBOX.md", "# INBOX\n\nNotes between projects.\n")
    write(projects / "alpha" / "STATUS.md",
          "# STATUS\n\n## Now\n\nAlpha is mid-arc.\n\n## To do\n\n- [ ] the alpha item\n")
    old = time.time() - 3 * 86400          # fixed ages, so two renders read the same
    for path in (hub / "STATUS.md", hub / "INBOX.md", projects / "alpha" / "STATUS.md"):
        os.utime(str(path), (old, old))
    return hub, projects, home


def world_env(world, out=None):
    home = world / "home"
    env = {"HOME": str(home), "USERPROFILE": str(home), "HOMEDRIVE": None, "HOMEPATH": None,
           # the world's own record, named outright (a record this machine names
           # never reaches the fixture; the resolver reads the world's)
           "EXO_MACHINE_JSON": str(home / "orchestrator-sync" / "machine.json"),
           "COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_VOLUMES": str(world / "vol"),
           "COLLECT_OPENERS_WORK": str(world / "work"),
           "COLLECT_OPENERS_ENGINE": str(home / "orchestrator-sync"),
           "ORCH_PROJECTS_ROOT": str(world / "projects"),
           "ORCH_TAUGHT_PATH": str(world / "hub" / "dossier" / "TAUGHT.md")}
    env["COLLECT_OPENERS_OUT"] = str(out) if out else None
    return env


# --------------------------------------------------------------------------
# E — hook A
# --------------------------------------------------------------------------

def section_e(world, hub):
    section("E — hook A: the ledger rides the board run, and never breaks it (L7)")
    board = hub / "orchestrator.py"
    code, out = run([PY, str(board)], env=world_env(world), cwd=world)
    ok("the board run finishes", code == 0, out[-400:])
    ok("it wrote the board, the tree and the ledger",
       (hub / "board.html").is_file() and (hub / "tree.html").is_file()
       and (hub / "improvements.html").is_file())
    line = [l for l in out.splitlines() if l.startswith("improvements: ")]
    ok("the run says one line about the ledger, in the tool's own words",
       len(line) == 1 and line[0].strip() == FULL_LINE, line)
    ok("the hook sits in main(), after the tree is written",
       re.search(r"write_html\(tree\).*write_improvements\(\)",
                 io.open(str(board), encoding="utf-8").read(), re.S) is not None)
    was = io.open(str(hub / "improvements.html"), encoding="utf-8").read()
    board_was = io.open(str(hub / "board.html"), encoding="utf-8").read()

    keep = io.open(str(hub / "tools" / "improvements.py"), encoding="utf-8").read()
    write(hub / "tools" / "improvements.py",
          "raise RuntimeError('the ledger is broken on purpose')\n")
    code, out = run([PY, str(board)], env=world_env(world), cwd=world)
    ok("a ledger that raises does not fail the board run", code == 0, out[-300:])
    bad = [l for l in out.splitlines() if l.startswith("Improvements: not written")]
    ok("it costs exactly one plain line", len(bad) == 1, bad)
    ok("the board was still written",
       io.open(str(hub / "board.html"), encoding="utf-8").read() != "" and
       (hub / "tree.html").is_file())
    ok("the ledger page is left exactly as it was",
       io.open(str(hub / "improvements.html"), encoding="utf-8").read() == was)

    os.remove(str(hub / "tools" / "improvements.py"))
    code, out = run([PY, str(board)], env=world_env(world), cwd=world)
    bad = [l for l in out.splitlines() if l.startswith("Improvements: not written")]
    ok("no ledger at all: still one line, still exit 0", code == 0 and len(bad) == 1,
       "exit %d · %s" % (code, bad))
    ok("and the board is written all the same",
       len(io.open(str(hub / "board.html"), encoding="utf-8").read()) > len(board_was) / 2)
    write(hub / "tools" / "improvements.py", keep)


# --------------------------------------------------------------------------
# F — hook B
# --------------------------------------------------------------------------

def section_f(world, hub, mod):
    section("F — hook B: one chip on the tree, and nothing else moved (L8)")
    out_dir = world / "out"
    patched = hub / "tools" / "collect-openers.py"
    baseline = hub / "tools" / "collect-openers-orig.py"
    code, log = run([PY, str(patched), "--html"], env=world_env(world, out_dir / "tree-chip.html"),
                    cwd=world)
    ok("the patched collector renders", code == 0, log[-400:])
    chip_page = io.open(str(out_dir / "tree-chip.html"), encoding="utf-8").read()
    chip = mod.chip_html(str(hub))
    ok("the chip is on the page exactly once", chip and chip_page.count(chip) == 1, chip)
    ok("it reads improvements <done>/<listed> and links to the page beside it",
       'href="improvements.html"' in chip and "improvements <b>2</b>/13 ▸" in chip, chip)
    ok("it sits in the counts strip, in the strip's own class, adding no CSS",
       re.search(r'<div class="strip">[^\0]*?%s' % re.escape(chip), chip_page) is not None
       and 'class="cnt" href=' in chip)
    ok("hook B is exactly reversible: its insertions, one each, nothing left behind",
       not FACTS.get("unpatch"), "; ".join(FACTS.get("unpatch") or []))

    code, log = run([PY, str(baseline), "--html"],
                    env=world_env(world, out_dir / "tree-plain.html"), cwd=world)
    ok("the collector without the hook renders the same world", code == 0, log[-400:])
    plain_page = io.open(str(out_dir / "tree-plain.html"), encoding="utf-8").read()
    ok("take the chip out and the tree is the unhooked tree, mark for mark",
       mask(chip_page.replace(chip, "", 1)) == mask(plain_page),
       "%d vs %d bytes" % (len(chip_page.replace(chip, "", 1)), len(plain_page)))

    shutil.move(str(hub / "design" / "BUILD-QUEUE.md"), str(world / "queue-away.md"))
    code, log = run([PY, str(patched), "--html"],
                    env=world_env(world, out_dir / "tree-none.html"), cwd=world)
    none_page = io.open(str(out_dir / "tree-none.html"), encoding="utf-8").read()
    ok("no queue, no chip — the strip never shows a placeholder",
       code == 0 and "improvements.html" not in none_page)
    ok("and that page is the unhooked page exactly", mask(none_page) == mask(plain_page),
       "%d vs %d bytes" % (len(none_page), len(plain_page)))
    shutil.move(str(world / "queue-away.md"), str(hub / "design" / "BUILD-QUEUE.md"))


# --------------------------------------------------------------------------
# G — the real queue, copied
# --------------------------------------------------------------------------

def section_g(hub, qdir):
    section("G — a COPY of the real queue: nothing falls in the hole (L9)")
    source = (HUB / "design" / "BUILD-QUEUE.md") if HUB else Path("no-hub")
    if not source.is_file():
        ok("the real queue is where the tool looks for it", False, str(source))
        return
    copy = write(qdir / "real-copy.md", io.open(str(source), encoding="utf-8").read())
    lines = [l for l in io.open(str(copy), encoding="utf-8").read().splitlines()
             if l.lstrip().startswith("| BQ-")]
    code, out = tool("--write", "--queue", copy, "--hub", hub / "real", "--root", HUB)
    got = re.match(r"improvements: (\d+) listed · (\d+) done · (\d+) building · "
                   r"(\d+) briefed · (\d+) waiting", out.strip())
    ok("the real queue reads without error", code == 0 and got is not None, out.strip())
    if not got:
        return
    listed = int(got.group(1))
    ok("N is exactly the number of `| BQ-` lines in the file (%d)" % len(lines),
       listed == len(lines), "listed %d" % listed)
    ok("not one of them is unreadable", "UNREADABLE" not in out, out.strip())
    parts = [int(got.group(i)) for i in range(2, 6)]
    stopped = re.search(r"· (\d+) stopped", out)
    ok("the states add up to the whole list",
       sum(parts) + (int(stopped.group(1)) if stopped else 0) == listed,
       "%s vs %d" % (parts, listed))
    page = io.open(str(hub / "real" / "improvements.html"), encoding="utf-8").read()
    ids = [re.match(r"\|\s*(BQ-\d+)", l.lstrip()).group(1) for l in lines]
    missing = [i for i in ids if page.count('id="r-%s"' % i) != 1]
    ok("every real row is on the page exactly once", not missing, missing)
    print("\n  the real queue, as the tool prints it:\n    %s" % out.strip())


# --------------------------------------------------------------------------
# H — the plain-words title a note may open with (refinement 1)
# --------------------------------------------------------------------------

TITLED = [
    ("BQ-940", "seeded",
     "«The tree's launch link opens the terminal, not the app» %s · the body carries "
     "the real date — and the first clause lives here" % day(10)),
    ("BQ-941", "seeded",
     "«Wren said \"not this one\" on 2026-01-01» %s · Wren \"this is the real quote\" "
     "— the body is where his words are" % day(3)),
    ("BQ-942", "seeded",
     "«A title with \"quotes\", an em dash — and Wren's own apostrophe» %s · the body" % day(1)),
    ("BQ-943", "seeded",
     "«an opening mark that never closes %s · the first clause — and the rest" % day(2)),
    ("BQ-944", "seeded",
     "«%s» %s · the body" % ("a title that runs on and on " * 8, day(4))),
    ("BQ-945", "done HUB",
     "«A done row with a title» %s · BUILT · gate 7/7" % day(5)),
]


def section_h(mod, qdir, hub, root):
    section("H — a note's plain-words title is the purpose (refinement 1)")
    write(qdir / "titled.md", HEAD + "".join(row_line(*r) for r in TITLED))
    rows = {r["id"]: r for r in mod.read_rows(qdir / "titled.md", root)}
    ok("a titled row shows its title, whole, as its purpose",
       rows["BQ-940"]["purpose"] == "The tree's launch link opens the terminal, not the app",
       rows["BQ-940"]["purpose"])
    ok("an untitled row still uses the first-clause rule",
       mod.read_rows(qdir / "full.md", root)[4]["purpose"]
       == "%s · the oldest thing still waiting" % day(12))
    ok("the date is read after the title, never inside it",
       rows["BQ-941"]["heard"] == day(3), rows["BQ-941"]["heard"])
    ok("Wren's words are read after the title, never inside it",
       rows["BQ-941"]["said"] == "this is the real quote", rows["BQ-941"]["said"])
    ok("an opening mark that never closes is not a title, and not an error",
       rows["BQ-943"]["state"] == "WAITING" and not rows["BQ-943"]["why"]
       and rows["BQ-943"]["purpose"] == "«an opening mark that never closes %s · the first clause" % day(2),
       rows["BQ-943"]["purpose"])
    ok("a title longer than 140 characters is cut at a whole word",
       len(rows["BQ-944"]["purpose"]) <= 141 and rows["BQ-944"]["purpose"].endswith("…"),
       "%d chars" % len(rows["BQ-944"]["purpose"]))
    ok("a done row's proof is still read, from the body",
       rows["BQ-945"]["proof"] == "HUB · gate 7/7", rows["BQ-945"]["proof"])
    code, out = tool("--write", "--queue", qdir / "titled.md", "--hub", hub / "titled",
                     "--root", root)
    page = io.open(str(hub / "titled" / "improvements.html"), encoding="utf-8").read()
    ok("all six titled rows come out, once each", code == 0
       and all(page.count('id="r-%s"' % r[0]) == 1 for r in TITLED), out.strip())
    ok("a title's quotes, em dash and apostrophe are escaped, not raw",
       "A title with &quot;quotes&quot;, an em dash — and Wren&#x27;s own apostrophe" in page,
       page[page.find("BQ-942"):][:300])
    outside, inside = texts_of(page)
    ok("no text node outside an expander grew past 300 characters",
       max((len(t) for t in outside), default=0) <= 300)
    ok("the expander still shows the whole note, title and all",
       any("«The tree's launch link" in t and "the body carries" in t for t in inside))


# --------------------------------------------------------------------------

def main():
    print("gate-improvements.py — BQ-026, the improvements ledger")
    print("  layout:  %s — improvements.py and collect-openers.py beside the gate "
          "(%s), orchestrator.py at %s" % (LAYOUT, HERE, ORCH.parent))
    print("  engine:  %s (read-only: the collector's sibling modules, evidence.py, "
          "the real queue)" % (HUB or "NOT FOUND — F and G cannot run"))
    print("  scratch: %s (hermetic; nothing live is written)" % SCRATCH)
    qdir, hub = SCRATCH / "queues", SCRATCH / "hub"
    root = SCRATCH / "root"
    (hub).mkdir(parents=True, exist_ok=True)
    write(root / BRIEF_OF["BQ-903"], "# a brief that exists\n")
    write(qdir / "full.md", fixture_full())
    write(qdir / "plain.md", fixture_plain())
    write(REGISTRY_FILE, json.dumps(FIXTURE_REGISTRY, indent=1) + "\n")
    os.environ["EXO_REGISTRY_JSON"] = str(REGISTRY_FILE)
    mod = load_tool()
    section_a(mod, qdir, root)
    section_b(qdir, hub, root)
    section_c(hub, qdir, root)
    section_d(hub, qdir, root)
    section_h(mod, qdir, hub, root)
    if HUB is None:
        section("E F G — the engine this gate borrows read-only")
        ok("the hub the record names is readable (machine.json roots.orchestrator)",
           False, "no folder with tools/exo_common.py and evidence.py above %s" % HERE)
    else:
        world = SCRATCH / "world"
        world_hub, _, _ = build_world(world)
        section_e(world, world_hub)
        section_f(world, world_hub, mod)
        section_g(hub, qdir)

    print("\n===== GATE =====")
    for name in fails:
        print("  FAIL  %s" % name)
    passed = sum(1 for c in checks if c)
    if KEEP:
        print("  kept: %s" % SCRATCH)
    else:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    print("%d checks · %d passed · %d failed" % (len(checks), passed, len(fails)))
    return 1 if fails else 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    shutil.rmtree(str(SCRATCH), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main()
    finally:
        if not KEEP:
            remove_own_worlds()
    sys.exit(RESULT)
