#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""asked.py — what the owner asked for that is still open, oldest first. A mirror, not a door.

    python3 tools/asked.py                 the one screen, about forty lines
    python3 tools/asked.py --count         the header line alone, for the hub's wake
    python3 tools/asked.py --all           every line in every group
    python3 tools/asked.py --project <name>  one project (its folder name, any part of it)
    python3 tools/asked.py --days 14       only what is older than fourteen days
    python3 tools/asked.py --everything    every open STATUS item, ask or not
    python3 tools/asked.py --json          the whole set, for the tree page
    (--hub <folder> and --projects <folder> point it elsewhere — the gate uses a scratch copy)

It reads, and it NEVER writes — not a file, not a cache. Four kinds of file,
four groups:

  waiting on your word   dossier/TAUGHT.md lines whose last stamp still says pending
  ideas unjudged         IDEAS.md lines that say "new" (someday shows with --all)
  oldest open asks       every STATUS.md "## To do" line still open that ASKS:
                         its words name the owner, or a quoted phrase of five words or more
  watcher rulings        a watcher proposal entry you ruled, with no filing word after it

Every line carries its age in whole days, the project, the item's own words, and
the file and line it lives on — so it can be opened without asking anyone. An
undated line prints "?" and sorts last; an urgent item carries the mark.

Filing is not this tool's job: a lane files into its own STATUS, ideas.py files
an idea, a planning session judges. This screen only remembers.

Not in v1: INBOX lines (their grammar has no done-marker, so nothing there can
be called closed) and the lanes' openers (the tree page already carries those).

Three notes on how it reads, so nobody has to guess:
  - an item's AGE comes from the earliest date in its own opening (its first 160
    characters, where this record stamps when a thing was raised). A long item
    often TALKS about older dates; those are not its birth.
  - an item whose opening carries no date is asked of `git blame` — ONE call per
    file, each wanted line its own -L range, at most forty lines a run — and
    only when git cannot answer (no repo, the line not committed yet) is a date
    taken from deeper in the line. Nothing found at all prints "?".
  - a watcher entry counts as filed when a filing word ("filed", "recorded in",
    "written to") stands AT OR AFTER the ruling. A filing word earlier in the
    entry belongs to a proposal's own text, not to a receipt — reading it as a
    receipt would hide a ruling that was never filed, which this screen exists
    to show.

Stdlib only, Python 3.9-compatible, OS-neutral, no user paths: the hub folder and
the projects root come from the machine record the path resolver finds
(tools/exo_paths.py), exactly as every other tool reads them.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent))
from exo_registry import registry, owner_words                        # noqa: E402
from exo_paths import paths                                           # noqa: E402

_REG = [None]


def _reg():
    """The person's own names, read once per run."""
    if _REG[0] is None:
        _REG[0] = registry()
    return _REG[0]


def _owner_alt():
    """The owner's words as one regex alternation, or "" when the registry
    names nobody. Case-sensitive and at word boundaries, as the rule has always
    been: a name inside another word is not a name."""
    words = owner_words(_reg())
    return "|".join(re.escape(w) for w in words) if words else ""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:                       # a Windows console may be cp1252: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SHOW_ASKS = 12             # one screen: the rest waits behind --all
SHOW_OTHER = 8
BLAME_LINES = 40           # the cap, counted in lines asked of git
HEAD_CHARS = 160           # where an item stamps its own birth
TITLE_WIDTH = 60


# --------------------------------------------------------------------------
# where things are — machine.json is the one record (ideas.py's own reading)
# --------------------------------------------------------------------------

def machine_facts():
    """(machine name, roots) from the one record the path resolver finds.
    Unknown is said, never guessed."""
    try:
        with io.open(paths(tool_file=__file__)["machine_file"], encoding="utf-8") as fh:
            d = json.load(fh)
        return str(d.get("name", "")).strip() or "unknown", d.get("roots", {}) or {}
    except Exception:
        return "unknown", {}


def hub_folder(override, roots):
    if override:
        return Path(override).expanduser()
    return Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)


def projects_root(override, roots):
    if override:
        return Path(override).expanduser()
    return Path(roots.get("projects") or (Path.home() / "Projects"))


# --------------------------------------------------------------------------
# reading, dates, words
# --------------------------------------------------------------------------

def read_lines(path, unread):
    """The file's lines, or None. A file that is not there is simply absent — a
    source the fleet has not grown yet is not an error. A file that IS there and
    cannot be read is one honest line at the foot of the screen."""
    try:
        if not path.is_file():
            return None
    except OSError:
        return None
    try:
        return io.open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as exc:
        unread.append({"path": str(path), "why": exc.strerror or str(exc)})
        return None


DATE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")


def all_dates(text):
    """Every real date in the text, ISO. 2026-13-40 is not a date and is dropped;
    a date inside a timestamp (2026-09-10T09:03) still counts."""
    out = []
    for y, m, d in DATE.findall(text):
        try:
            out.append(date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            continue
    return out


def birth_date(text):
    """The ask's birth: the EARLIEST date in the item's OPENING — its first
    HEAD_CHARS characters, where this record stamps when a thing was raised.
    "" when its opening carries none: git's own record is asked next, and only
    then a date from deeper in the line (see collect_status).

    Not the earliest date anywhere in the line: on a STATUS line that runs to
    three thousand characters the earliest date is often a date the item TALKS
    about — an older release date quoted deep in its text — and reading that as
    its birth would make the screen call an item raised two weeks ago months
    old. A screen whose headline number is wrong is not a truthful
    interface, so the search is bounded to the item's own opening."""
    found = all_dates(text[:HEAD_CHARS])
    return min(found) if found else ""


def any_date(text):
    """The first date anywhere in the line — the last resort, for an item whose
    opening carries none and whose folder is not a repo to ask."""
    found = all_dates(text)
    return found[0] if found else ""


def leading_date(text):
    """The date a journal or idea line opens with — its own stamp, not a date it
    happens to mention."""
    m = re.match(r"^\s*[-*+]?\s*(\d{4}-\d{2}-\d{2})", text)
    if not m:
        return ""
    return (all_dates(m.group(1)) or [""])[0]


def age_of(iso, today):
    if not iso:
        return None
    try:
        return (today - date.fromisoformat(iso)).days
    except ValueError:
        return None


def plain(text):
    """Backticks and bold markers out, whitespace collapsed (collect-openers.py's
    own rule). File names and quotes stay intact."""
    text = str(text).replace("`", "").replace("**", "").replace("__", "")
    return " ".join(text.split())


QUOTED = (re.compile(r'"([^"\n]{2,600})"'),
          re.compile("“([^”\n]{2,600})”"))
_OWNER_RE = [None]


def owner_re():
    """A word that means the owner, whole and case-sensitive. None when the
    registry names nobody — and then no line is an ask by name."""
    if _OWNER_RE[0] is None:
        alt = _owner_alt()
        _OWNER_RE[0] = re.compile(r"\b(?:%s)\b" % alt) if alt else False
    return _OWNER_RE[0] or None


def ask_by_name(text):
    """True when this open item carries the owner's own name. It is HALF of
    what makes an item an ask; the other half is a quoted phrase, which needs
    no name. Counted apart so a registry that names nobody can say what it
    could not look for."""
    named = owner_re()
    return bool(named is not None and named.search(text))


def is_ask(text):
    """An open item is an ASK when the owner's name is in it, or when it quotes
    a phrase of five words or more — the shape of a ruling said out loud.
    Honest about its misses: --everything shows every open item,
    ask or not."""
    if ask_by_name(text):
        return True
    for rx in QUOTED:
        for quote in rx.findall(text):
            if len(quote.split()) >= 5:
                return True
    return False


# A date, an hour, a parenthetical aside or a lone dash at the very start is the
# record's own stamp, not the item's name: peeled off before the name is read.
LEAD = re.compile("^(?:\\d{4}-\\d{2}-\\d{2}|~?\\d{1,2}:\\d{1,2}\\w*"
                  "|\\((?:[^()]|\\([^()]*\\))*\\)|[·:;,—–-])\\s*")
LETTER = re.compile(r"[A-Za-z]")
CUTS = (" — ", " – ", " -- ", ":", "(")


def title_of(text, words=12, width=TITLE_WIDTH):
    """The item's CAPS name when it opens with one, else its first twelve words —
    the item's own words either way, never a summary."""
    whole = plain(text)
    body = whole
    for _ in range(5):
        peeled = LEAD.sub("", body, count=1)
        if peeled == body:
            break
        body = peeled
    cut = len(body)
    for mark in CUTS:
        at = body.find(mark)
        if 0 <= at < cut:
            cut = at
    head = body[:cut].split()
    while head and not LETTER.search(head[-1]):
        head.pop()                                   # a trailing date or hour is not a name
    caps = [w for w in head[:2] if LETTER.search(w) and w == w.upper()]
    chosen = head if (len(caps) == 2 and len(head) >= 2) else (body or whole).split()[:words]
    out = " ".join(chosen)
    if len(out) > width:
        out = out[:width].rsplit(" ", 1)[0] + "…"
    return out or whole[:width]


# --------------------------------------------------------------------------
# (A) the STATUS to-do lists
# --------------------------------------------------------------------------

# The board's own STATUS grammar, copied (not imported) so this tool stands
# alone on either machine — collect-openers.py's section_key, heading and item.
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
SECTIONS = {"now": "now", "todo": "todo", "todos": "todo",
            "important": "important", "wherethingslive": "where"}
TODO = re.compile(r"^\s*[-*+]\s*\[([ xX]?)\]\s*(.*)$")


def section_key(heading):
    return SECTIONS.get(re.sub(r"[^a-z0-9]", "", heading.lower()))


def open_todos(lines):
    """[(line number, text, urgent)] from the "## To do" section only. No
    fallback: a STATUS without that heading contributes nothing."""
    out, inside = [], False
    for n, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if stripped.startswith("<!--"):
            continue
        head = HEADING.match(stripped)
        if head:
            inside = section_key(head.group(1)) == "todo"
            continue
        if not inside:
            continue
        item = TODO.match(raw)
        if not item or item.group(1).strip().lower() == "x":
            continue
        text = item.group(2).strip()
        urgent = text.startswith("!")
        if urgent:
            text = text[1:].strip()
        text = plain(text)
        if text:
            out.append((n, text, urgent))
    return out


ZERO = "0" * 40
BLAME_HEAD = re.compile(r"^([0-9a-f]{40}) (\d+) (\d+)")


def author_day(epoch, tz):
    """The author's OWN day, in the offset git recorded it with."""
    try:
        tz = tz.strip()
        sign = -1 if tz.startswith("-") else 1
        off = timezone(sign * timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5])))
        return datetime.fromtimestamp(epoch, off).date().isoformat()
    except Exception:
        try:
            return datetime.fromtimestamp(epoch, timezone.utc).date().isoformat()
        except Exception:
            return ""


def blame_dates(repo, relpath, linenos):
    """{line number: YYYY-MM-DD} for undated lines, from ONE git blame carrying
    every wanted line as its own -L range. An uncommitted line (the all-zero
    sha) has no recorded birth and is left undated. Git missing, the file
    untracked, the repo empty: {} — nothing raises."""
    if not linenos:
        return {}
    args = ["git", "-C", str(repo), "blame", "--porcelain"]
    for n in linenos:
        args += ["-L", "%d,%d" % (n, n)]
    args += ["--", relpath]
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30)
    except Exception:
        return {}
    if proc.returncode != 0:
        return {}
    out, seen, sha, line, epoch = {}, {}, "", None, None
    for raw in (proc.stdout or "").splitlines():
        head = BLAME_HEAD.match(raw)
        if head:
            sha, line, epoch = head.group(1), int(head.group(3)), None
            if sha != ZERO and sha in seen:
                out[line] = seen[sha]
            continue
        if line is None:
            continue
        if raw.startswith("author-time "):
            try:
                epoch = int(raw.split(" ", 1)[1])
            except ValueError:
                epoch = None
        elif raw.startswith("author-tz ") and epoch is not None and sha != ZERO:
            day = author_day(epoch, raw.split(" ", 1)[1])
            if day:
                seen[sha] = day
                out[line] = day
    return out


def status_sources(hub, projects):
    """Every STATUS.md this machine can see: the hub's first, then one level of
    the projects root, in name order. A folder without one is skipped in
    silence; a file sitting in the projects root is not a project."""
    out = [(hub.name, hub / "STATUS.md", hub, "STATUS.md")]
    try:
        kids = sorted([p for p in projects.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    except OSError:
        kids = []
    for folder in kids:
        out.append((folder.name, folder / "STATUS.md", folder, "%s/STATUS.md" % folder.name))
    return out


def collect_status(hub, projects, everything, today, unread):
    """Group A. The age comes from the item's own opening; when the opening has
    no date the line's birth is asked of git (bounded by BLAME_LINES), and only
    if that cannot answer is a date taken from deeper in the line."""
    rows, dateless = [], []
    for project, path, folder, rel in status_sources(hub, projects):
        lines = read_lines(path, unread)
        if lines is None:
            continue
        is_repo = (folder / ".git").exists()
        for n, text, urgent in open_todos(lines):
            if not (everything or is_ask(text)):
                continue
            iso = birth_date(text)
            row = {"project": project, "lane": "", "urgent": urgent,
                   "title": title_of(text), "date": iso, "age_days": age_of(iso, today),
                   "where": "%s:%d" % (rel, n), "source": "status",
                   "by_name": ask_by_name(text)}
            rows.append(row)
            if not iso:
                dateless.append((folder if is_repo else None, n, row, text))

    wanted, spent = {}, 0
    for folder, n, row, _text in dateless:           # already in a settled order
        if folder is None or spent >= BLAME_LINES:
            continue
        wanted.setdefault(str(folder), []).append((n, row))
        spent += 1
    for folder, asked in wanted.items():
        found = blame_dates(Path(folder), "STATUS.md", [n for n, _row in asked])
        for n, row in asked:
            iso = found.get(n, "")
            if iso:
                row["date"], row["age_days"] = iso, age_of(iso, today)
    for _folder, _n, row, text in dateless:
        if not row["date"]:
            iso = any_date(text)
            if iso:
                row["date"], row["age_days"] = iso, age_of(iso, today)
    return rows


# --------------------------------------------------------------------------
# (B) the ideas file
# --------------------------------------------------------------------------

# ideas.py's own line grammar, copied so this tool stands alone.
IDEA = re.compile(
    "^- (\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}) · (.+?) · (.*) · via ([^·]+?)"
    "(?: · ([a-z]+) (\\d{4}-\\d{2}-\\d{2}))?\\s*$")


def collect_ideas(hub, keep_someday, today, unread):
    """Group B: an idea still saying "new" is unjudged. someday shows only with
    --all; filed, dropped and done have had their word and leave this screen."""
    lines = read_lines(hub / "IDEAS.md", unread)
    if lines is None:
        return []
    rows, n = [], 0
    for row, raw in enumerate(lines, 1):
        m = IDEA.match(raw)
        if not m:
            continue
        n += 1
        status = m.group(2).strip()
        if status != "new" and not (keep_someday and status == "someday"):
            continue
        iso = leading_date(raw)
        lane = status.split("/", 1)[1].strip() if (status.startswith("filed") and "/" in status) else ""
        rows.append({"project": hub.name, "lane": lane,
                     "urgent": m.group(3).lstrip().startswith("!"),
                     "title": plain(m.group(3)), "date": iso, "age_days": age_of(iso, today),
                     "where": "IDEAS.md:%d" % row, "source": "ideas",
                     "n": n, "status": status})
    return rows


# --------------------------------------------------------------------------
# (C) the rule journal — the exocortex's asks OF the owner
# --------------------------------------------------------------------------

STAMP = re.compile(r"\[([^\[\]]*)\]")
_WORD_PENDING = [None]


def word_pending_re():
    """`<owner>'s word pending` in the journal's own stamp. None when the
    registry names nobody, and then no journal line is waiting on a word."""
    if _WORD_PENDING[0] is None:
        alt = _owner_alt()
        _WORD_PENDING[0] = re.compile(
            "(?:%s)['’]s word pending" % alt, re.I) if alt else False
    return _WORD_PENDING[0] or None


def collect_taught(hub, today, unread):
    """Group C: a journal line whose LAST bracketed stamp still says pending — a
    rule waiting on the owner's promote-or-journal word. Only the owner can move
    these, so they stand at the top of the screen."""
    lines = read_lines(hub / "dossier" / "TAUGHT.md", unread)
    if lines is None:
        return []
    rows = []
    for row, raw in enumerate(lines, 1):
        if not raw.lstrip().startswith("- "):
            continue
        stamps = STAMP.findall(raw)
        last = stamps[-1] if stamps else ""
        _pending = word_pending_re()
        if not ("pending" in last.lower()
                or (_pending is not None and _pending.search(raw))):
            continue
        iso = leading_date(raw)
        rows.append({"project": hub.name, "lane": "", "urgent": False,
                     "title": title_of(raw.lstrip()[2:]), "date": iso,
                     "age_days": age_of(iso, today),
                     "where": "dossier/TAUGHT.md:%d" % row, "source": "taught",
                     "stamp": plain(last)})
    return rows


# --------------------------------------------------------------------------
# (D) watcher rulings that were never filed
# --------------------------------------------------------------------------

FILING = re.compile("filed|recorded in|written to", re.I)
_RULED = [None]


def ruled_re():
    """A watcher entry the owner RULED on. None when the registry names
    nobody, and then no entry reads as ruled."""
    if _RULED[0] is None:
        alt = _owner_alt()
        _RULED[0] = re.compile(
            "(?:%s)['’]s rul|(?:%s)\\s+ruled" % (alt, alt), re.I) if alt else False
    return _RULED[0] or None


def collect_watchers(hub, today, unread):
    """Group D: a proposal entry you RULED with no filing word standing at or
    after the ruling — a ruling that was given and never written down anywhere."""
    rows = []
    try:
        files = sorted((hub / "watchers").glob("*-PROPOSALS-*.md"), key=lambda p: p.name.lower())
    except OSError:
        files = []
    for path in files:
        lines = read_lines(path, unread)
        if lines is None:
            continue
        heads = [i for i, raw in enumerate(lines) if raw.startswith("## ")]
        for k, start in enumerate(heads):
            end = heads[k + 1] if k + 1 < len(heads) else len(lines)
            entry = lines[start:end]
            _ruled = ruled_re()
            ruling = (next((j for j, raw in enumerate(entry) if _ruled.search(raw)), None)
                      if _ruled is not None else None)
            if ruling is None:
                continue
            if any(FILING.search(raw) for raw in entry[ruling:]):
                continue
            heading = plain(lines[start][3:])
            iso = birth_date(heading) or birth_date("\n".join(entry))
            rows.append({"project": hub.name, "lane": "", "urgent": False,
                         "title": heading, "date": iso, "age_days": age_of(iso, today),
                         "where": "watchers/%s:%d" % (path.name, start + 1),
                         "source": "watcher", "watcher": path.stem})
    return rows


# --------------------------------------------------------------------------
# the screen
# --------------------------------------------------------------------------

def sort_key(row):
    """Oldest first; undated last; then project and place, so two runs of the
    same record print the same screen."""
    age = row["age_days"]
    return (0 if age is not None else 1, -(age or 0), row["project"].lower(), row["where"])


def age_cell(age):
    return "%5d d" % age if age is not None else "    ?  "


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def clip(text, width=TITLE_WIDTH):
    """One line stays one line. The full words live on in --json."""
    return text if len(text) <= width else text[:width].rsplit(" ", 1)[0] + "…"


def line_of(row):
    """One row, one line, in the item's own words."""
    src, age = row["source"], age_cell(row["age_days"])
    if src == "status":
        return "%s %s %s · %s · %s" % (age, "▲" if row["urgent"] else " ",
                                                 row["project"], row["title"], row["where"])
    if src == "ideas":
        word = "" if row.get("status") == "new" else "%s · " % row.get("status", "")
        return "%s · #%d · %s%s · %s" % (age, row.get("n", 0), word,
                                                        clip(row["title"]), row["where"])
    if src == "taught":
        return "%s · rule journal · %s · %s" % (age, row["title"], row["where"])
    return "%s · watcher %s · %s · ruled, not marked filed" % (
        age, row.get("watcher", ""), clip(row["title"]))


def header_line(counts, machine, when):
    """The one line the hub can say at wake. "open" counts the three groups that
    are still open — the waiting word, the unjudged ideas, the asks; a watcher
    ruling is a filing leak, not an ask, so it carries its own clause."""
    parts = ["ASKED — %d open" % counts["open"] if counts["open"] else "ASKED — nothing open"]
    if counts["oldest_days"] is not None:
        parts.append("oldest %d d" % counts["oldest_days"])
    if counts["waiting"]:
        parts.append("%d waiting on your word" % counts["waiting"])
    if counts["ideas_unjudged"]:
        parts.append(plural(counts["ideas_unjudged"], "idea") + " unjudged")
    if counts["watcher_unfiled"]:
        parts.append(plural(counts["watcher_unfiled"], "watcher ruling") + " unfiled")
    parts.append("%s %s" % (machine, when))
    line = " · ".join(parts)
    if not owner_words(_reg()):
        # Truthful, never silent, and never a number that means something else.
        line += ("\nasked: %d open · %d by name — no owner name in "
                 "registry.json; set owner.name to count asks by name"
                 % (counts["open"], counts.get("by_name", 0)))
    return line


def print_group(title, rows, cap, show_all):
    if not rows:
        return                                   # a group with nothing in it is absent
    shown = rows if (show_all or len(rows) <= cap) else rows[:cap]
    if len(shown) == len(rows):
        print("%s (%d)" % (title, len(rows)))
    else:
        print("%s (%d, showing %d — --all for every line)" % (title, len(rows), len(shown)))
    for row in shown:
        print(line_of(row))


def gather(hub, projects, opts, today):
    """The whole set, filtered, each group oldest first."""
    unread = []
    groups = {"waiting": collect_taught(hub, today, unread),
              "ideas": collect_ideas(hub, opts.all, today, unread),
              "asks": collect_status(hub, projects, opts.everything, today, unread),
              "watchers": collect_watchers(hub, today, unread)}
    for key in list(groups):
        rows = groups[key]
        if opts.project:
            needle = opts.project.strip().lower()
            rows = [r for r in rows if needle in r["project"].lower()]
        if opts.days is not None:
            # an undated line is kept: its age is unknown, and hiding it would
            # claim it is young.
            rows = [r for r in rows if r["age_days"] is None or r["age_days"] > opts.days]
        groups[key] = sorted(rows, key=sort_key)

    still_open = groups["waiting"] + groups["ideas"] + groups["asks"]
    ages = [r["age_days"] for r in still_open if r["age_days"] is not None]
    counts = {"open": len(still_open), "oldest_days": max(ages) if ages else None,
              "waiting": len(groups["waiting"]),
              "ideas_unjudged": len([r for r in groups["ideas"] if r.get("status") == "new"]),
              "watcher_unfiled": len(groups["watchers"]),
              # HOW MANY OF THE ASKS CARRY THE OWNER'S OWN NAME. `open` counts
              # the journal, the ideas and the asks together, so it can never
              # stand for this number and is never printed as if it did.
              "by_name": len([r for r in groups["asks"] if r.get("by_name")])}
    return groups, counts, unread


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--project", default=None)
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--everything", action="store_true")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--hub", default=None)
    ap.add_argument("--projects", default=None)
    ap.add_argument("--help", action="store_true")
    try:
        opts = ap.parse_args(argv)
    except SystemExit:
        print(__doc__)
        return 2
    if opts.help:
        print(__doc__)
        return 0

    machine, roots = machine_facts()
    hub = hub_folder(opts.hub, roots)
    projects = projects_root(opts.projects, roots)
    now = datetime.now().astimezone()
    groups, counts, unread = gather(hub, projects, opts, now.date())
    header = header_line(counts, machine, now.strftime("%Y-%m-%d %H:%M"))

    if opts.json:                                # never truncated: the tree's bytes
        head = dict(counts)
        head.update({"machine": machine, "when": now.strftime("%Y-%m-%d %H:%M"),
                     "hub": str(hub), "projects": str(projects), "line": header,
                     "unread": unread,
                     "filters": {"all": opts.all, "project": opts.project,
                                 "days": opts.days, "everything": opts.everything}})
        for rows in groups.values():
            for row in rows:
                row["line"] = line_of(row)
        print(json.dumps({"header": head, "groups": groups}, ensure_ascii=False, indent=2))
        return 0

    print(header)
    if opts.count:
        return 0
    print_group("WAITING ON YOUR WORD", groups["waiting"], SHOW_OTHER, opts.all)
    print_group("IDEAS (incl. someday)" if opts.all else "IDEAS UNJUDGED",
                groups["ideas"], SHOW_OTHER, opts.all)
    print_group("OLDEST OPEN ITEMS" if opts.everything else "OLDEST OPEN ASKS",
                groups["asks"], SHOW_ASKS, opts.all)
    print_group("WATCHER RULINGS NOT FILED", groups["watchers"], SHOW_OTHER, opts.all)
    if not counts["open"] and not groups["watchers"]:
        print("nothing open in the record this screen reads.")
    for miss in unread:
        print("unread: %s — %s" % (miss["path"], miss["why"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except BrokenPipeError:            # piped into head or more: the reader left, no error
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except Exception:
            pass
        sys.exit(0)
