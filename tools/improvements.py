#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""improvements.py — the improvements ledger: what Exocortex will update, and proof it got done.

    python3 tools/improvements.py --count            one line, for the hub's wake
    python3 tools/improvements.py --write            improvements.html + improvements-state.json
    python3 tools/improvements.py --since YYYY-MM-DD what changed state since then
    (--queue <file> and --hub <folder> point every verb elsewhere; --root <folder>
     is where a row's brief and gate paths are looked for — the gate runs on copies)

ONE list is read: design/BUILD-QUEUE.md in the hub folder. Nothing else is
parsed, and the queue is NEVER written — this tool only shows.

THE BLACK-HOLE RULE (the reason this exists): every `| BQ-` line in the queue
comes out the other side. A line this tool cannot read is not dropped and not
guessed at — it is listed under UNREADABLE ROWS with its line number and the
reason, and it is counted. What goes in comes out.

The state of a row is DERIVED from the queue, never hand-set:

    DONE      the status cell starts `done`
    STOPPED   the status cell starts `stop:` or `paused-cap`
    BUILDING  the status cell starts `running`, or the note carries the word BUILDING
    BRIEFED   the row's brief file exists on disk, or the status starts `ruled by`
    WAITING   everything else

first in that order, so a finished row is not called BUILDING by an old note.

A note may OPEN with a plain-words title between guillemets — `«What this row is
for» …the rest of the note` — and that title is the row's purpose, shown whole.
Everything else the tool reads out of a note (the date it was heard, the
owner's own words, a done row's gate count) is read AFTER the closing mark, so a quote or a
date inside a title is never mistaken for them. A note with no title, or a `«`
that never closes, falls back to the first-clause rule; neither is an error.

THE DOOR'S WORD : a note may carry `exo: <word>` — fits ·
fits-with-a-change · does-not-fit · later — optionally followed by
` — <what the Door calls it>`. A row heard on or after EXO_SNAPSHOT with no
such word, or with a word outside those four, is UNJUDGED: `--count` adds
` · exo unjudged N` (naming any word it could not accept) and the page shows a
dim `unjudged` chip on the row; a judged row wears its word as a chip.

Stdlib only, Python 3.9-compatible, OS-neutral, no user paths: the hub folder
comes from the machine record the path resolver finds (tools/exo_paths.py),
exactly as every other tool reads it. Every file this tool writes is written to a temp name and moved into place
(os.replace), so a page is never half-written when the heartbeat reads it.
"""
import io
import json
import os
import re
import sys
import html as _html
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
from datetime import datetime, date
from pathlib import Path

try:                       # a Windows console may be cp437: never crash on the "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

QUEUE_REL = os.path.join("design", "BUILD-QUEUE.md")
PAGE_NAME = "improvements.html"
STATE_NAME = "improvements-state.json"

ROW_START = "| BQ-"
ID_RE = re.compile(r"^BQ-\d+$")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
# A note may OPEN with a plain-words title between guillemets — the hub writes it
# in the owner's own vocabulary, and it is the row's purpose, whole. Everything
# the tool reads FROM the note (the date it was heard, their words, the gate
# count) is read after the closing mark, so a title can never be mistaken for them.
TITLE_RE = re.compile(r"^\s*«([^»]*)»")
GATE_RE = re.compile(r"gate[ -]?(\d+/\d+)", re.I)
COUNT_RE = re.compile(r"\b(\d+/\d+)\b")
# the Door's word on a row. EXO_SNAPSHOT is the day the Door's EXO spec
# (the inventory that judged every feature up to then) took its snapshot: a row
# heard before it was judged there, a row heard on or after it owes its own word.
EXO_SNAPSHOT = "2026-10-16"
EXO_WORDS = ("fits", "fits-with-a-change", "does-not-fit", "later")
EXO_RE = re.compile(r"(?<![\w-])exo:\s*([^\s.,;:|]+)(?:\s+—\s+([^;|]*))?", re.I)
EXO_DOOR_MAX = 12          # the Door's word is at most twelve words
# The owner's own words: the first quoted phrase AFTER a word that means them.
# A single quote inside a word (let's, we'll) is part of the phrase, never its
# end. With no owner name in the registry there is no such word, the pattern
# matches nothing, and a row with no quote is still a row.
QUOTED = (r"[^\"'“‘]{0,80}?"
          r"(?:\"([^\"]{3,})\"|“([^”]{3,})”"
          r"|'((?:[^']|(?<=\w)'(?=\w)){3,}?)'(?!\w))")
_SAID_RE = [None]


def said_re():
    """The quoted-phrase pattern, built from the registry's own owner words.
    None when the registry names nobody."""
    if _SAID_RE[0] is None:
        words = owner_words(_reg())
        _SAID_RE[0] = re.compile(
            r"\b(?:%s)\b" % "|".join(re.escape(w) for w in words) + QUOTED
        ) if words else False
    return _SAID_RE[0] or None

STATES = ("BUILDING", "BRIEFED", "WAITING", "STOPPED", "UNREADABLE", "DONE")
GROUPS = (("BUILDING", "BUILDING NOW"), ("BRIEFED", "BRIEFED, NEXT"),
          ("WAITING", "WAITING"), ("STOPPED", "STOPPED"),
          ("UNREADABLE", "UNREADABLE ROWS"), ("DONE", "DONE"))

PURPOSE_MAX = 110          # the note's first clause, never the raw note
TITLE_MAX = 140            # a title the hub wrote is shown whole, up to this
SAID_MAX = 160             # the quote on the row; the whole note is one click away


# --------------------------------------------------------------------------
# where things are
# --------------------------------------------------------------------------

def machine_roots():
    """The roots from the one record the path resolver finds. Unknown is said,
    never guessed."""
    try:
        with io.open(paths(tool_file=__file__)["machine_file"],
                     encoding="utf-8") as fh:
            return json.load(fh).get("roots", {}) or {}
    except Exception:
        return {}


def hub_folder(override=None, roots=None):
    if override:
        return Path(str(override)).expanduser()
    roots = machine_roots() if roots is None else roots
    return Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)


def queue_file(override=None, hub=None):
    if override:
        return Path(str(override)).expanduser()
    return Path(hub if hub is not None else hub_folder()) / QUEUE_REL


def queue_label(queue, hub):
    """How the page and the state file NAME the queue: hub-relative when it is
    inside the hub (`design/BUILD-QUEUE.md`), so what they write carries no
    machine's home folder; as given when the person pointed outside the hub on
    purpose — that path is theirs."""
    queue, hub = Path(str(queue)), Path(str(hub))
    try:
        return queue.resolve().relative_to(hub.resolve()).as_posix()
    except (ValueError, OSError, RuntimeError):
        return str(queue)


NO_QUEUE = "improvements: 0 listed · no queue file yet"


def now_local():
    return datetime.now().astimezone()


def iso_now():
    return now_local().replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# reading the one list
# --------------------------------------------------------------------------

def split_row(raw):
    """The cells of a markdown table row, or None when the pipes are broken."""
    line = raw.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    return [c.strip() for c in line[1:-1].split("|")]


def parse_queue(text):
    """Every `| BQ-` line of the queue, readable or not. Nothing is dropped.

    Returns a list of rows in file order (file order is priority). A row that
    could not be read carries state UNREADABLE and the reason why."""
    rows, seen = [], {}
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.lstrip().startswith(ROW_START):
            continue
        row = {"line": number, "raw": raw.strip(), "why": "", "id": "",
               "arc": "", "brief": "", "gates": "", "model": "",
               "status": "", "note": ""}
        cells = split_row(raw)
        # The id stands even when the rest of the row is broken, so a row that
        # breaks today is still the same row it was yesterday.
        if cells and ID_RE.match(cells[0]):
            row["id"] = cells[0]
        else:
            first = re.match(r"^\|\s*(BQ-\d+)\s*\|", raw.strip())
            row["id"] = first.group(1) if first else ""
        if cells is None:
            row["why"] = "the line does not open and close with a pipe"
        elif len(cells) != 7:
            row["why"] = ("7 cells expected (id, arc, brief, gates, model, "
                          "status, note), %d found" % len(cells))
        elif not row["id"]:
            row["why"] = "the id cell reads %r" % cells[0]
        elif not cells[5]:
            row["why"] = "the status cell is empty"
        else:
            for key, value in zip(("id", "arc", "brief", "gates", "model",
                                   "status", "note"), cells):
                row[key] = value
        key = row["id"] or ("line-%d" % number)
        if row["id"] and row["id"] in seen:
            row["why"] = ("%s; " % row["why"] if row["why"] else "") + \
                          "%s is already on line %d" % (row["id"], seen[row["id"]])
            key = "%s-line-%d" % (row["id"], number)
        elif row["id"]:
            seen[row["id"]] = number
        row["key"] = key
        rows.append(row)
    return rows


def heard_of(note):
    """The first YYYY-MM-DD in the note. A date is never invented."""
    found = DATE_RE.search(note or "")
    return found.group(1) if found else ""


def age_days(heard, today=None):
    try:
        then = date.fromisoformat(heard)
    except Exception:
        return None
    today = today or now_local().date()
    return (today - then).days


def title_of(note):
    """The plain-words title a note opens with, or "". A `«` that never closes
    is not a title — the note simply has none."""
    found = TITLE_RE.match(note or "")
    return " ".join(found.group(1).split()) if found else ""


def note_body(note):
    """The note after its title span: where the date, the owner's words and the
    gate count are read from. An untitled note is its own body."""
    found = TITLE_RE.match(note or "")
    return ((note or "")[found.end():] if found else (note or "")).strip()


def exo_match(note):
    """The `exo:` token in the note's body (past its title), or None."""
    return EXO_RE.search(note_body(note))


def exo_of(note):
    """The Door's judgment word the note carries, lowercased — one of EXO_WORDS
    when it is a word the ledger accepts — or None when the note carries none."""
    found = exo_match(note)
    return found.group(1).lower() if found else None


def exo_door_of(note):
    """What the Door calls the feature (the words after ` — `), up to the first
    sentence end, at most twelve words; "" when the note gives none."""
    found = exo_match(note)
    if not found or not found.group(2):
        return ""
    text = re.split(r"\.\s|\s·\s", found.group(2).strip(), 1)[0].strip().rstrip(".")
    return " ".join(text.split()[:EXO_DOOR_MAX])


def exo_owed(row):
    """True when a readable row heard on or after EXO_SNAPSHOT carries no word
    the ledger accepts: it is UNJUDGED for the Door. Earlier rows are exempt."""
    if row.get("state") == "UNREADABLE" or not row.get("heard"):
        return False
    return row["heard"] >= EXO_SNAPSHOT and row.get("exo") not in EXO_WORDS


def clip(text, limit):
    """`text` whole when it fits, else cut at the last whole word and an ellipsis."""
    if len(text) <= limit:
        return text
    out = text[:limit]
    if " " in out:
        out = out.rsplit(" ", 1)[0]
    return out.rstrip(" ·,;:-—") + "…"


def purpose_of(note):
    """What the row is FOR, in one line — never the raw note.

    The title the hub wrote, when the note opens with one (whole, up to 140
    characters); otherwise the note's FIRST CLAUSE: cut at the first ` — `, at
    the first `:` past 40 characters, or at 110 characters, whichever comes
    first. Either cut falls back to the last whole word, so no word is sliced."""
    title = title_of(note)
    if title:
        return clip(title, TITLE_MAX)
    text = " ".join((note or "").split())
    if not text:
        return ""
    ends = [len(text)]
    dash = text.find(" — ")
    if dash > 0:
        ends.append(dash)
    colon = text.find(":", 40)
    if colon > 0:
        ends.append(colon)
    ends.append(PURPOSE_MAX)
    end = min(ends)
    out = text[:end].rstrip(" ·,;:-—")
    if end == PURPOSE_MAX and len(text) > PURPOSE_MAX:
        if " " in out:
            out = out.rsplit(" ", 1)[0].rstrip(" ·,;:-—")
        out += "…"
    return out


def said_of(note):
    """The owner's own words, when the note carries them and the registry says
    which word means them."""
    pattern = said_re()
    found = pattern.search(note or "") if pattern else None
    if not found:
        return ""
    phrase = next((g for g in found.groups() if g), "")
    return clip(" ".join(phrase.split()), SAID_MAX)


def proof_of(status, note):
    """What a DONE row can show for itself: the sha (or HUB) the status names,
    and the first gate count the note carries, if any."""
    rest = status[4:].strip() if status.lower().startswith("done") else ""
    rest = rest.strip("·-— ").split(" ")[0] if rest else ""
    gate = GATE_RE.search(note or "") or COUNT_RE.search(note or "")
    parts = [p for p in (rest, ("gate %s" % gate.group(1)) if gate else "") if p]
    return " · ".join(parts)


def state_of(row, root):
    """The row's state, derived in a fixed order."""
    if row["why"]:
        return "UNREADABLE"
    status, note = row["status"], row["note"]
    low = status.lower()
    if low.startswith("done"):
        return "DONE"
    if low.startswith("stop:") or low.startswith("paused-cap"):
        return "STOPPED"
    if low.startswith("running") or re.search(r"\bBUILDING\b", note):
        return "BUILDING"
    if low.startswith("ruled by") or brief_exists(row, root):
        return "BRIEFED"
    return "WAITING"


def brief_exists(row, root):
    path = (row.get("brief") or "").strip()
    if not path or root is None:
        return False
    try:
        return (Path(root) / path).is_file()
    except Exception:
        return False


def read_rows(queue, root=None):
    """(rows with their derived state, the queue's own text). Raises OSError
    when the queue is not there — the caller says so in one plain line."""
    text = io.open(str(queue), encoding="utf-8").read()
    rows = parse_queue(text)
    today = now_local().date()
    for row in rows:
        body = note_body(row["note"])        # the note past its title span
        row["state"] = state_of(row, root)
        row["title"] = title_of(row["note"])
        row["heard"] = heard_of(body)
        row["age"] = age_days(row["heard"], today)
        row["purpose"] = purpose_of(row["note"]) or (row["raw"] if row["why"] else "")
        row["said"] = said_of(body)
        row["proof"] = proof_of(row["status"], body) if row["state"] == "DONE" else ""
        readable = row["state"] != "UNREADABLE"
        row["exo"] = (exo_of(row["note"]) or "") if readable else ""
        row["exo_door"] = exo_door_of(row["note"]) if readable else ""
        row["exo_owed"] = exo_owed(row)
    return rows


# --------------------------------------------------------------------------
# the count line — the one line a hub wake says
# --------------------------------------------------------------------------

def tally(rows):
    counts = {state: 0 for state in STATES}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    waiting = [r["age"] for r in rows if r["state"] == "WAITING" and r["age"] is not None]
    owed = [r for r in rows if r.get("exo_owed")]
    return {"listed": len(rows), "done": counts["DONE"], "building": counts["BUILDING"],
            "briefed": counts["BRIEFED"], "waiting": counts["WAITING"],
            "stopped": counts["STOPPED"], "unreadable": counts["UNREADABLE"],
            "oldest_waiting": max(waiting) if waiting else None,
            "waiting_dated": len(waiting),
            "exo_unjudged": len(owed),
            "exo_bad": [(r["id"], r["exo"]) for r in owed if r.get("exo")]}


def count_line(counts):
    if counts["oldest_waiting"] is not None:
        oldest = "%d d" % counts["oldest_waiting"]
    elif counts["waiting"]:
        oldest = "date not recorded"
    else:
        oldest = "none"
    line = ("improvements: %d listed · %d done · %d building · %d briefed · "
            "%d waiting · oldest waiting %s"
            % (counts["listed"], counts["done"], counts["building"],
               counts["briefed"], counts["waiting"], oldest))
    if counts["stopped"]:
        line += " · %d stopped" % counts["stopped"]
    if counts["unreadable"]:
        line += " · %d UNREADABLE" % counts["unreadable"]
    if counts.get("exo_unjudged"):               #  silent at 0
        line += " · exo unjudged %d" % counts["exo_unjudged"]
        if counts.get("exo_bad"):
            line += " (%s)" % "; ".join("%s says %s" % pair for pair in counts["exo_bad"])
    return line


# --------------------------------------------------------------------------
# the state file — what changed, and when
# --------------------------------------------------------------------------

def read_state(path):
    try:
        data = json.loads(io.open(str(path), encoding="utf-8").read())
    except Exception:
        return {}
    return data.get("rows", {}) if isinstance(data, dict) else {}


def write_atomic(path, text):
    path = Path(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-%d" % os.getpid())
    with io.open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(str(tmp), str(path))
    return path


def update_state(old, rows, stamp):
    """id → {state, prev, first_seen, changed}. `changed` moves ONLY when the
    state really moved, so a rewrite that says nothing new says nothing."""
    new = {}
    for row in rows:
        key = row["key"]
        was = old.get(key) if isinstance(old.get(key), dict) else {}
        state = row["state"]
        if was.get("state") == state:
            new[key] = {"state": state,
                        "prev": was.get("prev", ""),
                        "first_seen": was.get("first_seen") or stamp,
                        "changed": was.get("changed") or stamp}
        else:
            new[key] = {"state": state,
                        "prev": was.get("state", ""),
                        "first_seen": was.get("first_seen") or stamp,
                        "changed": stamp}
    for key, was in old.items():                 # a row that left the queue is kept,
        if key not in new and isinstance(was, dict):   # so its history is not lost
            entry = dict(was)
            if entry.get("state") != "GONE":
                entry = {"state": "GONE", "prev": was.get("state", ""),
                         "first_seen": was.get("first_seen") or stamp,
                         "changed": stamp}
            new[key] = entry
    return new


def state_json(rows_state, stamp, queue):
    return json.dumps({"written": stamp, "queue": str(queue), "rows": rows_state},
                      ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def parse_since(text):
    raw = str(text or "").strip().replace("Z", "+00:00")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        raw += "T00:00:00"
    try:
        when = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return when.astimezone() if when.tzinfo is None else when


def since_lines(rows_state, when):
    out = []
    for key in sorted(rows_state):
        entry = rows_state[key]
        if not isinstance(entry, dict) or not entry.get("prev"):
            continue
        changed = entry.get("changed") or ""
        try:
            stamp = datetime.fromisoformat(changed)
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.astimezone()
        if stamp < when:
            continue
        out.append((stamp, "%s · %s → %s · %s"
                    % (key, entry["prev"], entry["state"], changed[:16])))
    return [line for _, line in sorted(out, key=lambda p: p[0], reverse=True)]


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------

def _e(text):
    return _html.escape("" if text is None else str(text), quote=True)


CSS = """
:root{--ground:#090d12;--panel:#10161d;--faint:#141b23;--ink:#dfe6ee;--ink-2:#b7c1cc;
--dim:#7f8b99;--line:#1f2831;--line-2:#2b3642;--acc:#4fc1ff;--acc-line:rgba(79,193,255,.32);
--amber:#ffb000;--amber-bg:rgba(255,176,0,.10);--amber-line:rgba(255,176,0,.45);
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
--plate:Futura,"Futura PT","Century Gothic","Avenir Next",var(--sans)}
*,*::before,*::after{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:16px;
line-height:1.55;margin:0;overflow-x:hidden;-webkit-font-smoothing:antialiased}
.wrap{max-width:920px;margin:0 auto;padding:30px 20px 64px}
.np{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0;
font-family:var(--plate);font-size:clamp(1.3rem,4.6vw,1.9rem);letter-spacing:.18em;
text-transform:uppercase;color:var(--ink)}
.np i{font-style:normal;font-family:var(--mono);font-size:.6rem;letter-spacing:.22em;color:var(--dim)}
.cl{margin:10px 0 0;font-family:var(--mono);font-size:.78rem;letter-spacing:.04em;
color:var(--ink-2);overflow-wrap:anywhere}
.rule{border:0;height:1px;background:var(--line-2);margin:18px 0 0}
.grp{display:flex;align-items:center;gap:10px;margin:30px 0 8px;
font-family:var(--mono);font-size:.64rem;font-weight:600;letter-spacing:.2em;
text-transform:uppercase;color:var(--dim)}
.grp .mk{width:8px;height:8px;border-radius:2px;background:var(--line-2);flex:none}
.grp .n{margin-left:auto;color:var(--dim)}
.grp.building{color:var(--amber)}
.grp.building .mk{background:var(--amber);box-shadow:0 0 0 3px var(--amber-bg)}
.row{border:1px solid var(--line);border-radius:8px;background:var(--panel);margin:7px 0}
.row[open]{border-color:var(--line-2)}
.row>summary{list-style:none;cursor:pointer;padding:11px 14px;display:flex;
flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.row>summary::-webkit-details-marker{display:none}
.row>summary:hover .pu,.row>summary:focus-visible .pu{color:var(--acc)}
.row>summary:focus-visible{outline:1px solid var(--acc-line);outline-offset:-1px;border-radius:8px}
.cv{flex:none;color:var(--dim);font-size:.7rem;line-height:1.6;transition:transform .12s ease;transform-origin:50% 55%}
.row[open]>summary .cv{transform:rotate(90deg)}
.id{font-family:var(--mono);font-size:.74rem;font-weight:600;letter-spacing:.06em;color:var(--ink);flex:none}
.pu{flex:1 1 15em;min-width:0;color:var(--ink-2);overflow-wrap:anywhere}
.wh{font-family:var(--mono);font-size:.66rem;letter-spacing:.06em;color:var(--dim);
white-space:nowrap;margin-left:auto}
.said{flex:1 1 100%;color:var(--ink-2);font-size:.88rem;overflow-wrap:anywhere}
.pf{flex:1 1 100%;font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;color:var(--dim)}
.ex{flex:none;font-family:var(--mono);font-size:.6rem;letter-spacing:.08em;padding:1px 7px;
border:1px solid var(--acc-line);border-radius:999px;color:var(--acc);white-space:nowrap}
.ex.un{border-color:var(--line-2);color:var(--dim)}
.row.done>summary .id,.row.done>summary .pu{text-decoration:line-through;color:var(--dim)}
.row.done{background:transparent}
.row.bad{border-color:var(--line-2)}
.exp{border-top:1px solid var(--line);padding:12px 14px 14px;background:var(--faint);
border-radius:0 0 7px 7px}
.exp dl{display:grid;grid-template-columns:7.5em 1fr;gap:5px 14px;margin:0}
.exp dt{font-family:var(--mono);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;
color:var(--dim);padding-top:3px}
.exp dd{margin:0;color:var(--ink-2);font-size:.92rem;overflow-wrap:anywhere}
.exp dd.m{font-family:var(--mono);font-size:.74rem;color:var(--ink-2)}
.exp dd.gone{color:var(--dim)}
.empty{color:var(--dim);font-size:.95rem;margin:18px 0}
footer{margin-top:40px;color:var(--dim);font-family:var(--mono);font-size:.62rem;
letter-spacing:.08em;overflow-wrap:anywhere}
footer hr{border:0;height:1px;background:var(--line);margin:0 0 10px}
@media (max-width:560px){.wh{margin-left:0}.exp dl{grid-template-columns:1fr;gap:2px}
.exp dt{padding-top:8px}}
"""

JS = r"""
(function(){
  var K='improvements-open', S='improvements-scroll';
  var rows=[].slice.call(document.querySelectorAll('details.row'));
  var open={}; try{open=JSON.parse(sessionStorage.getItem(K)||'{}')||{};}catch(e){open={};}
  rows.forEach(function(r){ if(open[r.id]) r.open=true;
    r.addEventListener('toggle',function(){
      if(r.open){open[r.id]=1;} else {delete open[r.id];}
      try{sessionStorage.setItem(K,JSON.stringify(open));}catch(e){}
    });
  });
  try{var y=+sessionStorage.getItem(S); if(y>0) window.scrollTo(0,y);}catch(e){}
  var t; window.addEventListener('scroll',function(){clearTimeout(t);
    t=setTimeout(function(){try{sessionStorage.setItem(S,String(window.scrollY));}catch(e){}},200);});
})();
"""


def group_rows(rows, state_map):
    """The rows of each group, in the order the reader needs them."""
    out = {}
    order = {row["key"]: i for i, row in enumerate(rows)}
    for state, _ in GROUPS:
        group = [r for r in rows if r["state"] == state]
        if state == "WAITING":                       # oldest heard first; undated last
            group.sort(key=lambda r: (r["age"] is None,
                                      -(r["age"] or 0), order[r["key"]]))
        elif state == "UNREADABLE":
            group.sort(key=lambda r: r["line"])
        elif state == "DONE":                        # newest change first
            group.sort(key=lambda r: ((state_map.get(r["key"]) or {}).get("changed") or "",
                                      -order[r["key"]]), reverse=True)
        out[state] = group
    return out


def row_html(row, state_map):
    entry = state_map.get(row["key"]) or {}
    cls = "row" + (" done" if row["state"] == "DONE" else "") + \
          (" bad" if row["state"] == "UNREADABLE" else "")
    # the caret is the row's one affordance: it says this row opens (and, once
    # open, that it did) — the page's only piece of chrome.
    head = ["<span class=\"cv\" aria-hidden=\"true\">▸</span>"]
    if row["state"] == "UNREADABLE":
        head.append("<span class=\"id\">line %d</span>" % row["line"])
        head.append("<span class=\"pu\">could not be read — %s</span>" % _e(row["why"]))
        head.append("<span class=\"wh\">%s</span>" % _e(row["id"] or "no id"))
    else:
        head.append("<span class=\"id\">%s</span>" % _e(row["id"]))
        if row.get("exo_owed"):                      #  owes the Door its word
            head.append("<span class=\"ex un\" title=\"%s\">unjudged</span>"
                        % _e(("exo: %s is not a word the ledger accepts" % row["exo"])
                             if row.get("exo") else "no exo: word for the Door yet"))
        elif row.get("exo"):
            head.append("<span class=\"ex\" title=\"%s\">%s</span>"
                        % (_e(row.get("exo_door") or "the Door's word"), _e(row["exo"])))
        head.append("<span class=\"pu\">%s</span>" % _e(row["purpose"]))
        if row["heard"]:
            head.append("<span class=\"wh\">heard %s · %s</span>"
                        % (_e(row["heard"]),
                           ("%d d" % row["age"]) if row["age"] is not None else "—"))
        else:
            head.append("<span class=\"wh\">date not recorded</span>")
        if row["said"]:
            head.append("<span class=\"said\">“%s”</span>" % _e(row["said"]))
        if row["proof"]:
            head.append("<span class=\"pf\">proof · %s</span>" % _e(row["proof"]))
    facts = []
    if row["state"] == "UNREADABLE":
        facts.append(("the line", row["raw"], True))
        facts.append(("why", row["why"], False))
    else:
        facts.append(("note", row["note"], False))
        facts.append(("arc", row["arc"], False))
        facts.append(("brief", row["brief"], True))
        facts.append(("gate", row["gates"], True))
        facts.append(("status", row["status"], True))
        facts.append(("model", row["model"], True))
        if row.get("exo") or row.get("exo_owed"):
            facts.append(("exo", " — ".join(p for p in (
                row.get("exo") or "unjudged", row.get("exo_door")) if p), True))
    facts.append(("line", "%s:%d" % (QUEUE_REL.replace(os.sep, "/"), row["line"]), True))
    facts.append(("state", "%s%s" % (row["state"],
                                     (" · since %s" % entry["changed"][:16])
                                     if entry.get("changed") else ""), True))
    body = "".join("<dt>%s</dt><dd%s>%s</dd>"
                   % (_e(label), " class=\"m\"" if mono else "",
                      _e(value) if value else "<span class=\"gone\">not recorded</span>")
                   for label, value, mono in facts)
    return ("<details class=\"%s\" id=\"r-%s\"><summary>%s</summary>"
            "<div class=\"exp\"><dl>%s</dl></div></details>"
            % (cls, _e(row["key"]), "".join(head), body))


def usage_chip(hub):
    """The usage chip — the last 24 h by model, drawn by tools/usage.py
    from the meter files. '' when there is no usage.py or nothing recorded."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "exo_usage_ledger", os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.chip_html(str(hub))
    except Exception:
        return ""


def page_html(rows, counts, state_map, queue, stamp, line=None, extra=""):
    out = ["<!DOCTYPE html>", "<html lang=\"en\"><head><meta charset=\"utf-8\">",
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
           # the page is left open on a second screen: it re-reads itself every
           # five minutes, and keeps the reader's place and open rows
           "<meta http-equiv=\"refresh\" content=\"300\">",
           "<title>Improvements — Exocortex</title>",
           "<style>%s</style></head><body><div class=\"wrap\">" % CSS,
           "<p class=\"np\">IMPROVEMENTS <i>EXOCORTEX</i></p>",
           "<p class=\"cl\">%s</p>%s<hr class=\"rule\">" % (_e(line or count_line(counts)), extra)]
    grouped = group_rows(rows, state_map)
    for state, title in GROUPS:
        group = grouped.get(state) or []
        if not group:
            continue
        out.append("<h2 class=\"grp%s\"><span class=\"mk\"></span>%s<span class=\"n\">%d</span></h2>"
                   % (" building" if state == "BUILDING" else "", _e(title), len(group)))
        for row in group:
            out.append(row_html(row, state_map))
    if not rows:
        out.append("<p class=\"empty\">No rows in the queue yet.</p>")
    if line == NO_QUEUE:
        out.append("<footer><hr><p>%s · %s is not there yet · its first row appears here</p></footer>"
                   % (_e(stamp), _e(str(queue))))
    else:
        out.append("<footer><hr><p>%s · read from %s · every row of that file is on this page</p></footer>"
                   % (_e(stamp), _e(str(queue))))
    out.append("</div><script>%s</script></body></html>" % JS)
    return "\n".join(out)


# --------------------------------------------------------------------------
# the chip the tree page wears (hook B)
# --------------------------------------------------------------------------

def chip_html(hub=None, queue=None):
    """One chip for the tree's counts strip — `improvements <done>/<listed> ▸`,
    linking to the page beside it. Returns "" when there is nothing true to
    say: no queue, no rows, no chip (the strip never shows a placeholder)."""
    try:
        rows = read_rows(queue_file(queue, hub_folder(hub)), hub_folder(hub))
    except Exception:
        return ""
    if not rows:
        return ""
    counts = tally(rows)
    return ("<a class=\"cnt\" href=\"%s\" style=\"text-decoration:none\" "
            "title=\"%s\">improvements <b>%d</b>/%d ▸</a>"
            % (PAGE_NAME, _e(count_line(counts)), counts["done"], counts["listed"]))


# --------------------------------------------------------------------------
# the verbs
# --------------------------------------------------------------------------

USAGE = """improvements.py — the improvements ledger, read from design/BUILD-QUEUE.md

  --count                  one line: listed · done · building · briefed · waiting · oldest
                           (· exo unjudged N when a row owes the Door its word)
  --write                  improvements.html + improvements-state.json in the hub folder
  --since <ISO>            one line per row whose state changed since then
  --queue <file>           read this queue instead of <hub>/design/BUILD-QUEUE.md
  --hub <folder>           write the page and the state file here
  --root <folder>          look for a row's brief and gate files under here (default: the hub)

The queue is never written. Every `| BQ-` line comes out: one it cannot read is
listed under UNREADABLE ROWS with its line number."""


def opt(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def main(argv):
    argv = list(argv)
    if "--help" in argv or "-h" in argv or not argv:
        print(USAGE)
        return 0
    hub = hub_folder(opt(argv, "--hub"))
    queue = queue_file(opt(argv, "--queue"), hub)
    root = Path(str(opt(argv, "--root", hub))).expanduser()
    label = queue_label(queue, hub)
    line = None                 # the count line, when it is not count_line's
    try:
        rows = read_rows(queue, root)
    except OSError as exc:
        if queue.exists():      # there, and unreadable: that is not "empty"
            print("improvements: %s is there but could not be read (%s)."
                  % (label, exc.strerror or type(exc).__name__))
            return 1
        # NOT THERE YET is a fresh brain, not a fault: zero rows, said so.
        rows, line = [], NO_QUEUE
    counts = tally(rows)

    if "--since" in argv:
        raw = opt(argv, "--since", "")
        when = parse_since(raw)
        if when is None:
            print("improvements: --since wants a date like 2026-09-18 or "
                  "2026-09-18T15:02, not %r." % raw)
            return 1
        lines = since_lines(read_state(hub / STATE_NAME), when)
        print("\n".join(lines) if lines else "no change since %s" % raw)
        return 0

    if "--write" in argv:
        stamp = iso_now()
        state_map = update_state(read_state(hub / STATE_NAME), rows, stamp)
        write_atomic(hub / STATE_NAME, state_json(state_map, stamp, label))
        write_atomic(hub / PAGE_NAME, page_html(rows, counts, state_map, label, stamp,
                                                line, usage_chip(hub)))
        print(line or count_line(counts))
        return 0

    if "--count" in argv:
        print(line or count_line(counts))
        return 0

    print(USAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
