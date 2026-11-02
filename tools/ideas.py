#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ideas.py — the exocortex's Someday: catch a thought now, judge it later.

    python3 tools/ideas.py --add "a wiki page per agent"        capture (any session, any machine)
    python3 tools/ideas.py --add "! the drive is nearly full"   urgent: raised at the next hub wake
    python3 tools/ideas.py --list                               the new ones (--all for every line)
    python3 tools/ideas.py --file 3 --to <project> --item "draft the wiki page"
    python3 tools/ideas.py --someday 4 · --drop 5 · --done 6    the status word, rewritten
    python3 tools/ideas.py --count [--urgent]                   "N new · M total", for the wake line
    python3 tools/ideas.py --sweep-reminders                    parked (v2)
    (--hub <folder> and --projects <folder> point every verb elsewhere — the gate runs on a scratch copy)

One file, IDEAS.md at the hub root, synced with the brain to every machine and
vendor. One line per idea, newest last:

    - <YYYY-MM-DD HH:MM> · new · a wiki page per agent · via <MACHINE>/<MIND>

A line is NEVER deleted, so `#<n>` — its ordinal among the idea lines — is
stable for as long as the file lives. Filing, someday, drop and done rewrite
the status word and append `· <verb> <date>`; the idea's own words, its hour
and where it came from stay exactly as they were written.

Capture is not triage: --add answers in ONE line and asks nothing. The
judging happens later, in a planning session (the /focus skill, or "triage
ideas"), where --file appends the To do line to the project's own STATUS.md.

Stdlib only, Python 3.9-compatible, OS-neutral, no user paths: the hub folder
and the projects root come from the machine record the path resolver finds
(tools/exo_paths.py), exactly as every other tool reads them.
"""
import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_paths import paths                                           # noqa: E402

try:                       # a Windows console may be cp437: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# The six lines that explain the grammar to whoever opens the file — human or
# model, on either vendor. Written once, when the file is first created.
HEADER = [
    "# IDEAS — the exocortex's Someday. Say \"idea: …\" in any session; Tuesday judges it.",
    "# One line per idea, newest last. Lines are never deleted, so #<n> — the ordinal below — is stable.",
    "# - YYYY-MM-DD HH:MM · <status> · <the idea, verbatim> · via <MACHINE>/<mind>",
    "# Status is exactly one of: new · filed → <Proj>[/<Lane>] · someday · dropped · done.",
    "# Filing and the rest rewrite ONLY the status word and append ` · <verb> YYYY-MM-DD`.",
    "# A `!` first in the idea text means raise it at the next hub wake, not Tuesday.",
]

# - <when> · <status> · <text> · via <src>[ · <verb> <date>]
#   `status` is non-greedy, so it takes the one field after the hour and a text
#   carrying a "·" of its own still reads whole.
LINE = re.compile(
    r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.*) · via ([^·]+?)"
    r"(?: · ([a-z]+) (\d{4}-\d{2}-\d{2}))?\s*$")

VERB = {"filed": "filed", "someday": "someday", "dropped": "dropped", "done": "done"}
STALE_H = 12               # a stamp older than this says nothing about who is up now


# --------------------------------------------------------------------------
# where things are
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


def age_hours(when):
    try:
        d = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except Exception:
        return float("inf")
    if d.tzinfo is None:
        d = d.astimezone()
    return (datetime.now().astimezone() - d).total_seconds() / 3600.0


def live_mind(hub, name):
    """The MIND writing this line, READ from this machine's own i-am stamps
    (live-<machine>-<mind>.json, the same files who-is-live.py and claim.py
    read) — never guessed. The newest session stamped on this machine inside
    the last twelve hours wins; when nothing is stamped, the answer is the
    honest 'unknown'."""
    best, mind = float("inf"), ""
    for f in sorted(hub.glob("live-*-*.json")):
        if f.name.startswith("live-sessions-"):
            continue                                    # the pulse's own file
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("mind"):
            continue
        if str(d.get("machine") or "").lower() != str(name).lower():
            continue
        sessions = d.get("sessions")
        whens = ([str(s.get("when") or "") for s in sessions if isinstance(s, dict)]
                 if isinstance(sessions, list) else ([] if d.get("off") else [str(d.get("when") or "")]))
        for w in whens:
            h = age_hours(w)
            if h < best:
                best, mind = h, str(d["mind"]).upper()
    return mind if best < STALE_H else ""


def default_via(hub, name):
    mind = live_mind(hub, name)
    return "%s/%s" % (str(name).upper(), mind or "unknown")


# --------------------------------------------------------------------------
# the file
# --------------------------------------------------------------------------

def read_file(path):
    """(every line, the parsed ideas). A missing file is an empty one — the
    first --add creates it with its header."""
    try:
        text = io.open(path, encoding="utf-8").read()
    except OSError:
        text = ""
    lines = text.splitlines()
    ideas = []
    for i, raw in enumerate(lines):
        m = LINE.match(raw)
        if not m:
            continue
        ideas.append({"n": len(ideas) + 1, "row": i, "when": m.group(1), "status": m.group(2),
                      "text": m.group(3), "via": m.group(4).strip(),
                      "verb": m.group(5) or "", "verb_date": m.group(6) or ""})
    return lines, ideas


def write_file(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines).rstrip("\n") + "\n")


def ensure_header(lines):
    """The header, exactly once. A file that already carries it is left alone."""
    if lines and lines[0].startswith("# IDEAS"):
        return lines
    return list(HEADER) + [""] + lines


def render(idea):
    """One idea back into its line — the only place a line is composed."""
    tail = " · %s %s" % (idea["verb"], idea["verb_date"]) if idea["verb"] else ""
    return "- %s · %s · %s · via %s%s" % (idea["when"], idea["status"], idea["text"], idea["via"], tail)


def is_urgent(idea):
    return idea["text"].lstrip().startswith("!")


def is_new(idea):
    return idea["status"].strip() == "new"


def today():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def fail(sentence):
    print(sentence)
    return 1


def find(ideas, n):
    for idea in ideas:
        if idea["n"] == n:
            return idea
    return None


# --------------------------------------------------------------------------
# verbs
# --------------------------------------------------------------------------

def cmd_add(path, text, via):
    text = " ".join(str(text).split())               # one line, always
    if not text:
        return fail("nothing to note: --add needs the idea's own words.")
    if " · via " in text:
        return fail("that idea contains \" · via \", which is the file's own grammar — reword it.")
    lines, ideas = read_file(path)
    lines = ensure_header(lines)
    idea = {"when": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"), "status": "new",
            "text": text, "via": via, "verb": "", "verb_date": ""}
    lines.append(render(idea))
    write_file(path, lines)
    n = len(ideas) + 1
    print("noted · #%d · %s" % (n, "raised for the next wake" if is_urgent(idea) else "Tuesday judges it"))
    return 0


def cmd_list(path, which):
    _lines, ideas = read_file(path)
    rows = ideas if which == "all" else [i for i in ideas if is_new(i)]
    if not rows:
        print("no new ideas." if which != "all" else "no ideas yet — say \"idea: …\" in any session.")
        return 0
    for idea in rows:
        print("#%-3d %s · %s · %s · via %s%s"
              % (idea["n"], idea["when"], idea["status"], idea["text"], idea["via"],
                 (" · %s %s" % (idea["verb"], idea["verb_date"])) if idea["verb"] else ""))
    return 0


def status_path(hub, projects, to):
    """The STATUS.md a `--to <Proj>[/<Lane>]` names: the hub's own when the
    project is the hub folder itself, else <projects root>/<Proj>/STATUS.md."""
    proj = str(to).split("/", 1)[0].strip()
    if not proj:
        return None, "which project? --to needs a project name."
    if proj.lower() == hub.name.lower():
        return hub / "STATUS.md", ""
    return projects / proj / "STATUS.md", ""


def cmd_file(path, hub, projects, n, to, item):
    lines, ideas = read_file(path)
    idea = find(ideas, n)
    if idea is None:
        return fail("there is no idea #%d in %s." % (n, path))
    item = " ".join(str(item).split())
    if not item:
        return fail("--item needs the exact To do text to write into the project.")
    target, why = status_path(hub, projects, to)
    if why:
        return fail(why)
    if not target.is_file():
        return fail("no STATUS.md for %s at %s — nothing was filed." % (to, target))
    try:
        text = io.open(target, encoding="utf-8").read()
    except OSError as exc:
        return fail("could not read %s: %s" % (target, exc))
    body = text.splitlines()
    head = next((i for i, raw in enumerate(body) if raw.strip().lower() == "## to do"), -1)
    if head < 0:
        return fail("%s has no \"## To do\" heading — nothing was filed." % target)
    todo = "- [ ] %s (idea %s)" % (item, today())
    body.insert(head + 1, todo)
    try:
        io.open(target, "w", encoding="utf-8", newline="\n").write("\n".join(body).rstrip("\n") + "\n")
        # Own the outcome: the idea line is rewritten only once the To do line
        # is READ BACK from the project's own file.
        landed = todo in io.open(target, encoding="utf-8").read().splitlines()
    except OSError as exc:
        return fail("could not write %s: %s — the idea is still new." % (target, exc))
    if not landed:
        return fail("the To do line did not land in %s — the idea is still new." % target)
    idea["status"] = "filed → %s" % str(to).strip()
    idea["verb"], idea["verb_date"] = VERB["filed"], today()
    lines[idea["row"]] = render(idea)
    write_file(path, lines)
    print("filed · #%d → %s · \"%s\" is under \"## To do\" in %s" % (n, to, item, target))
    return 0


def cmd_status(path, n, word):
    lines, ideas = read_file(path)
    idea = find(ideas, n)
    if idea is None:
        return fail("there is no idea #%d in %s." % (n, path))
    idea["status"] = word
    idea["verb"], idea["verb_date"] = VERB[word], today()
    lines[idea["row"]] = render(idea)
    write_file(path, lines)
    print("#%d · %s · %s" % (n, word, idea["text"]))
    return 0


def cmd_count(path, urgent):
    _lines, ideas = read_file(path)
    new = [i for i in ideas if is_new(i)]
    print("%d new · %d total" % (len(new), len(ideas)))
    if urgent:
        for idea in [i for i in new if is_urgent(i)]:
            print("! #%d · %s · %s · via %s" % (idea["n"], idea["when"], idea["text"], idea["via"]))
    return 0


def cmd_sweep_reminders():
    print("sweep-reminders: parked (v2)")
    return 0


# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--add", metavar="TEXT")
    ap.add_argument("--via", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--file", type=int, metavar="N")
    ap.add_argument("--to", default=None)
    ap.add_argument("--item", default=None)
    ap.add_argument("--someday", type=int, metavar="N")
    ap.add_argument("--drop", type=int, metavar="N")
    ap.add_argument("--done", type=int, metavar="N")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--urgent", action="store_true")
    ap.add_argument("--sweep-reminders", dest="sweep", action="store_true")
    ap.add_argument("--hub", default=None)
    ap.add_argument("--projects", default=None)
    ap.add_argument("--help", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        print("that is not a verb ideas.py knows — run --help for the six it does.")
        return 1

    verbs = [a.add is not None, a.list, a.file is not None, a.someday is not None,
             a.drop is not None, a.done is not None, a.count, a.sweep]
    if a.help or not any(verbs):
        print(__doc__)
        return 0
    if sum(1 for v in verbs if v) > 1:
        return fail("one verb at a time — run --help for the six ideas.py knows.")

    name, roots = machine_facts()
    hub = hub_folder(a.hub, roots)
    path = hub / "IDEAS.md"

    if a.sweep:
        return cmd_sweep_reminders()
    if a.add is not None:
        return cmd_add(path, a.add, (a.via or "").strip() or default_via(hub, name))
    if a.list:
        return cmd_list(path, "all" if a.all else "new")
    if a.count:
        return cmd_count(path, a.urgent)
    if a.file is not None:
        if not a.to or not a.item:
            return fail("--file needs both --to <Proj> and --item \"<the To do text>\".")
        return cmd_file(path, hub, projects_root(a.projects, roots), a.file, a.to, a.item)
    for n, word in ((a.someday, "someday"), (a.drop, "dropped"), (a.done, "done")):
        if n is not None:
            return cmd_status(path, n, word)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
