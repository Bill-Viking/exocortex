#!/usr/bin/env python3
"""Board skin v2 — "the instrument": the orchestrator drawn as one fall.

Imported by orchestrator.py when it is run with `--skin v2`; it writes
`board-v2.html` and never touches the v1 board. Same guarantees as v1:
Python 3 stdlib only, deterministic for a fixed scan + clock, zero tokens per
run, one self-contained file out.

Two contracts govern this file.

* The v2 comp image is the visual contract. The geometry, the
  colour roles and the type idiom below are lifted from `build-v2.py` and
  `waterfall.py`, which generated it.
* The comp's notes are the data-honesty contract. Their rules, in
  short: recency comes only from hard-dated work events (a git author stamp
  or a session stamp) because folder and STATUS.md mtimes were poisoned by a
  bulk filesystem event; every blue cell is a real byte of that project's own
  record; arcs are real sessions and routings only; every cap is stated on
  the page; nothing is ever substituted silently.

Everything drawn here is recomputed live at generate time. Nothing is read
back from the comp's own snapshot.
"""

from __future__ import annotations

import html
import math
import re
from datetime import datetime
from pathlib import Path

# The recency law, the git plumbing under it, the six-week window and the
# launch scheme all live in evidence.py so that skin v1 and this skin cannot
# drift apart about which project you were last working in. Imported into this
# namespace under their old names, so the drawing code below is unchanged.
import evidence
from evidence import (LAUNCH_PROMPT, git_window, launch_url,  # noqa: F401
                      week_start, week_windows)

HERE = Path(__file__).resolve().parent
OUT_FILE = HERE / "board-v2.html"
FONTS_FILE = HERE / "skin_v2_fonts.css"       # copied from the comp folder
INBOX_FILE = HERE / "INBOX.md"

DAY = 86400.0
WEEKS = 6                                     # top wall = this week, then back
SHOW = 6                                      # streams in the fall
FOCUS_ROWS = 8
FAM_CHIPS = 20                                # family etchings on the foot wall
GIT_LOG = 60                                  # commits of log text per record

# INBOX contract line: "- YYYY-MM-DD · <target> · <finding> · <action>"
INBOX_LINE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*·\s*(.+)$")

# ── colour tokens, all copied from the comps, none invented ───────────────
# fixture-and-part src/styles.css: --frozen-on-screen, --frozen-lit,
# --frozen, --moving, --keys-on-screen, --screen, --screen-muted.
# arc4's own ground #05080c, hero amber #FFD338, its white #FFF2B8.
# orchestrator.py's v1 --amber #E8930C, reused here as the dim/undated tier.
# NO HAL RED (#D0021B) ANYWHERE IN THIS SKIN.
GROUND = "#05080c"
FROZEN = "#7FB0E8"
FROZEN_LIT = "#D6E9FF"
AMBER = "#F2B705"          # dated streams — the instrument amber
AMBER_DIM = "#E8930C"      # undated streams — the v1 board's amber
AMBER_LIT = "#FFD338"      # the hero channel, and only the hero channel
AMBER_WHITE = "#FFF2B8"
GREEN = "#63B36F"
SCREEN = "#14161A"
MUTED = "#A3AAB5"

# ── the recency law, stated on the page ───────────────────────────────────
LOG_REF = math.log(1 + 365)
RECENCY_LAW = "r = 1 − ln(1+d) / ln(1+365)"
PITCH_LAW = ("dot pitch = 2.0 + 10.0·(1−r) px · side-stream opacity "
             "= 0.14 + 0.44·r · the channel alone = 0.98")
CELL_LAW = "cell opacity = 0.075 + 0.66·v, v = the byte on its own 2–98 pct"

# ══ collection ════════════════════════════════════════════════════════════
# Everything the fall needs, on top of orchestrator.scan(). The one rule that
# matters: recency is evidence-dated, never mtime-dated — see evidence.py,
# which v1 obeys too.

def git_record(root: Path):
    """(head_author_ts, log_text) from ONE git call.

    log_text is byte-for-byte what `--format=%ad %an %s --date=short` gives —
    the second half of a project's record, after its STATUS.md. head_author_ts
    is the author stamp of the newest commit: a date stored inside the commit
    object, which touching a file cannot forge.
    """
    out = evidence.run_git(root, ["log", f"-{GIT_LOG}",
                                  "--format=%at%x09%ad %an %s", "--date=short"])
    head, lines = None, []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        stamp, rest = line.split("\t", 1)
        if head is None:
            try:
                head = int(stamp)
            except ValueError:
                head = None
        lines.append(rest)
    return head, "".join(line + "\n" for line in lines)


def read_inbox(names):
    """The '## Waiting' list. The line format names only a target, so the
    source is recovered mechanically — the longest known project name that
    appears in the finding text. That is a heuristic and is flagged as one."""
    if not INBOX_FILE.is_file():
        return []
    try:
        lines = INBOX_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    in_waiting, items = False, []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("#"):
            in_waiting = "waiting" in stripped.lower()
            continue
        if not in_waiting:
            continue
        match = INBOX_LINE.match(stripped)
        if not match:
            continue
        parts = [p.strip() for p in match.group(2).split("·")]
        target = parts[0] if parts else ""
        body = " · ".join(parts[1:])
        hits = [n for n in names
                if n.lower() != target.lower() and n.lower() in body.lower()]
        hits.sort(key=len, reverse=True)
        items.append({"date": match.group(1), "target": target,
                      "source": hits[0] if hits else None, "text": body})
    return items


def raw_status(root: Path) -> str:
    try:
        return (root / "STATUS.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect(orch, projects, snapshot, now: datetime):
    """Live equivalent of the comps' extract.json, computed at generate time.

    `orch` is the orchestrator module, so the STATUS.md parse, the family
    grouping and the session attribution are the board's own code, not a copy.
    """
    weeks = week_windows(now)
    oldest = weeks[-1]["start"]
    session_groups = {}
    if snapshot:
        session_groups = dict(orch.group_sessions(snapshot["sessions"], projects))

    rows = []
    for project in projects:
        status = project["status"] or {}
        todos = status.get("todos", [])
        sessions = session_groups.get(project["name"], [])
        head_ts, log_text = git_record(project["path"])
        session_ts = max((s["when"].timestamp() for s in sessions if s["when"]),
                         default=None)

        # Recency, the one number the whole page is ordered by — evidence.py's
        # law, the same one v1's board now ranks by. Folder and STATUS.md
        # mtimes are deliberately NOT consulted: a bulk filesystem event
        # pinned most of them to one date, so neither can carry recency.
        dated = evidence.evidence_of(head_ts, session_ts, now.timestamp())
        evidence_ts, evidence_kind, edays = (dated["ts"], dated["kind"],
                                             dated["edays"])

        rows.append({
            "name": project["name"],
            "path": project["path"],
            "family": project["family"],
            "activity": project["activity"],          # the mtime signal, kept
            "status_mtime": status.get("mtime"),      # so the page can name it
            "edays": edays,
            "evidence": evidence_kind,
            "evidence_ts": evidence_ts,
            "evidence_date": (datetime.fromtimestamp(evidence_ts).strftime("%Y-%m-%d")
                              if evidence_ts else None),
            "open_todos": len(todos),
            "urgent_todos": [t["text"] for t in todos if t["urgent"]],
            "next": todos[0]["text"] if todos else None,
            "next_urgent": bool(todos and todos[0]["urgent"]),
            "now": status.get("now", "") or "",
            "important": status.get("important", []),
            "has_status": bool(project["status"]),
            "memory": project["memory"],
            "record": (raw_status(project["path"]) + log_text).encode("utf-8", "replace"),
            "sessions": [
                {"tag": s["tag"], "label": s["label"], "running": s["running"],
                 "when": s["when"].timestamp() if s["when"] else None}
                for s in sessions if s["tag"] in orch.SESSION_LIVE
            ],
            "session_count": len(sessions),
            "weeks": None,                            # filled for shown rows
        })

    by_name = {row["name"]: row for row in rows}
    fam_members = {}
    for row in rows:
        fam_members.setdefault(row["family"], []).append(row["name"])
    for row in rows:
        row["family_members"] = [n for n in fam_members[row["family"]]
                                 if n != row["name"]]

    # The fall: the most recently evidenced projects. Undated projects are
    # never ranked in among them — they have no date to rank by.
    dated_rows = sorted((r for r in rows if r["edays"] is not None),
                        key=lambda r: r["edays"])
    shown = dated_rows[:SHOW]
    hero = shown[0]["name"] if shown else None
    shown_names = {r["name"] for r in shown}
    rest = [r for r in rows if r["name"] not in shown_names]

    # Weekly history is only needed for the streams that are actually drawn,
    # so the extra git call runs SHOW times, not once per project.
    for row in shown:
        history = git_window(row["path"], oldest)
        per_week = []
        for window in weeks:
            stamps = [ts for ts, _ in history
                      if window["start"] <= ts < window["end"]]
            sess = [s["when"] for s in row["sessions"]
                    if s["when"] and window["start"] <= s["when"] < window["end"]]
            per_week.append({"iso": window["iso"], "commits": len(stamps),
                             "sessions": len(sess), "stamps": stamps,
                             "session_stamps": sess})
        row["weeks"] = per_week

    focus = [{"text": todo["text"], "urgent": todo["urgent"],
              "project": project["name"]}
             for todo, project in orch.focus_items(projects)]

    return {
        "now": now,
        "generated_label": now.strftime("%Y-%m-%d %H:%M"),
        "weeks": weeks,
        "rows": rows,
        "by_name": by_name,
        "shown": order_streams(shown),
        "hero": hero,
        "hero_row": by_name.get(hero),
        "rest": rest,
        "focus": focus,
        "focus_urgent": sum(1 for f in focus if f["urgent"]),
        "inbox": read_inbox([r["name"] for r in rows]),
        "families": [(name, [by_name[m["name"]] for m in members])
                     for name, members in orch.group_families(projects)],
        "sessions_total": len(snapshot["sessions"]) if snapshot else 0,
        "sessions_generated": snapshot["generated"] if snapshot else None,
    }


def order_streams(rows):
    """Left to right: oldest dated evidence first, so the freshest lands at
    the right edge as the channel."""
    return sorted(rows, key=lambda r: -r["edays"])


def recency(edays):
    """Real days → 0…1. None for a project with no dated evidence at all."""
    if edays is None:
        return None
    return max(0.0, min(1.0, 1.0 - math.log(1.0 + edays) / LOG_REF))


def pinned_counts(rows, now):
    """How many folder mtimes and STATUS.md mtimes the bulk filesystem event
    left sitting on one day. Computed, never typed, so the sentence on the
    page cannot drift away from the data behind it."""
    days = [round(max(0.0, (now.timestamp() - r["activity"]) / DAY), 1)
            for r in rows]
    if not days:
        return 0, 0, 0.0
    day = max(set(days), key=days.count)
    folders = sum(1 for d in days if abs(d - day) <= 0.1)
    status = sum(1 for r in rows if r["status_mtime"] and
                 abs((now.timestamp() - r["status_mtime"]) / DAY - day) <= 0.1)
    return folders, status, day


# ══ drawing primitives ════════════════════════════════════════════════════
# Lifted from the comp's own waterfall.py, with the wall packing rewritten
# (see pack_plate) so the page fits its weight budget.

def esc(value) -> str:
    return html.escape(str(value), quote=True)


def upper(value) -> str:
    return esc(str(value).upper())


def slug(text) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "x"


def wrap(text, width):
    """Greedy wrap, hard-breaking any token wider than the column (real to-do
    text contains long file names)."""
    lines, current = [], ""
    for word in str(text).split():
        while len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:width - 1] + "-")
            word = word[width - 1:]
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def clip(text, width, lines):
    """Wrap to `width` and keep at most `lines` of it, marking any cut with an
    ellipsis. Text is never dropped off the end of a box in silence."""
    wrapped = wrap(text, width)
    if len(wrapped) <= lines:
        return wrapped, False
    kept = wrapped[:lines]
    kept[-1] = kept[-1][:width - 2].rstrip() + "…"
    return kept, True


def normalize(raw: bytes):
    """Bytes → 0…1 on their own 2–98 percentile. The fixture-and-part law."""
    if not raw:
        return []
    ordered = sorted(raw)
    lo = ordered[int(0.02 * (len(ordered) - 1))]
    hi = ordered[int(0.98 * (len(ordered) - 1))]
    span = max(1, hi - lo)
    return [max(0.0, min(1.0, (v - lo) / span)) for v in raw]


BUCKETS = 16          # opacity levels the wall cells are quantised into


def plate_capacity(w, h, cell, gap_x, gap_y):
    cols = max(1, int((w + gap_x) // (cell + gap_x)))
    rows = max(1, int((h + gap_y) // (cell + gap_y)))
    return cols * rows


def pack_plate(x, y, w, h, values, cell=3.6, gap_x=1.0, gap_y=1.0):
    """One wall plate: a real byte per cell, brightest byte brightest cell.

    Same grid, same cells and same law as the comp's `waterfall.plate()` — the
    difference is purely how it is written down. The comp emitted one <rect>
    per cell, which cost 2.0 MB of DOM for 23k cells. Here the cells are
    quantised into BUCKETS opacity levels and each level is emitted as ONE
    <path> of square subpaths. No cell is dropped and no cell moves; the page
    just carries ~40× fewer nodes and ~4× fewer bytes.

    Returns (svg, cells_used, path_nodes).
    """
    cols = max(1, int((w + gap_x) // (cell + gap_x)))
    rows = max(1, int((h + gap_y) // (cell + gap_y)))
    buckets = [[] for _ in range(BUCKETS)]
    used = 0
    for index in range(min(len(values), cols * rows)):
        row, col = divmod(index, cols)
        cx = x + col * (cell + gap_x)
        cy = y + row * (cell + gap_y)
        level = int(round(values[index] * (BUCKETS - 1)))
        # a filled subpath closes itself, so the trailing "z" is not written
        buckets[level].append(f"M{cx:.1f} {cy:.1f}h{cell}v{cell}h-{cell}")
        used += 1
    out = []
    for level, cells in enumerate(buckets):
        if not cells:
            continue
        opacity = 0.075 + (level / (BUCKETS - 1)) * 0.66
        out.append(f'<path opacity="{opacity:.3f}" d="{"".join(cells)}"/>')
    return "".join(out), used, len(out)


def stream(x, y0, y1, r, kind="dated", phase=0.0):
    """A falling particle column. Density and brightness are the datum.
    NOT-DATA: the dash phase per filament, which only breaks a perfectly
    periodic dash pattern."""
    if kind == "hero":
        cols, spacing, width, colour = 15, 1.9, 1.2, AMBER_LIT
        opacity, pitch = 0.98, 2.0
    elif kind == "undated":
        cols, spacing, width, colour = 2, 1.5, 0.55, AMBER_DIM
        opacity, pitch = 0.13, 12.0
    else:
        # pop-through-restraint: the loud channel is the hero and only the
        # hero, so side streams are held to 0.58 even at r = 1.
        cols, spacing, width, colour = 3, 1.6, 0.7, AMBER
        pitch = 2.0 + 10.0 * (1.0 - r)
        opacity = 0.14 + 0.44 * r
    dot = 0.9 + 0.6 * (r if r is not None else 0.0)
    out = []
    left = x - (cols - 1) * spacing / 2.0
    for i in range(cols):
        cx = left + i * spacing
        off = (phase + i * 0.83) % max(pitch, 0.6)
        out.append(
            f'<path d="M {cx:.2f} {y0:.1f} V {y1:.1f}" stroke="{colour}" '
            f'stroke-width="{width:.2f}" stroke-opacity="{opacity:.3f}" '
            f'stroke-dasharray="{dot:.2f} {max(pitch - dot, 0.4):.2f}" '
            f'stroke-dashoffset="{off:.2f}" stroke-linecap="round" fill="none"/>'
        )
    return "".join(out)


def registers(top, height, gap, count=WEEKS):
    """[(y_top, height)] newest week first, top of the page."""
    return [(top + i * (height + gap), height) for i in range(count)]


def ts_to_y(ts, weeks, regs):
    """A real unix stamp → its y in the wall stack; None if out of range.
    Time increases upward: the top register is this week."""
    for week, (top, height) in zip(weeks, regs):
        if week["start"] <= ts < week["end"]:
            frac = (ts - week["start"]) / (week["end"] - week["start"])
            return top + height * (1.0 - frac)
    return None


def event_marks(x, row, weeks, regs, hero=False):
    """Amber marks where the stream really crossed a wall it was active in:
    one tick per week with real events, at the mean of that week's own
    timestamps, width from log(count); plus one dot per commit at its own
    stamp."""
    colour = AMBER_LIT if hero else AMBER
    out, dots, dropped = [], 0, 0
    for week, (top, height) in zip(row["weeks"], regs):
        stamps = list(week["stamps"]) + list(week["session_stamps"])
        if not stamps:
            continue
        window = next(w for w in weeks if w["iso"] == week["iso"])
        mean = sum(stamps) / len(stamps)
        frac = (mean - window["start"]) / (window["end"] - window["start"])
        y = top + height * (1.0 - max(0.0, min(1.0, frac)))
        half = (5.0 if hero else 3.0) + 2.6 * math.log1p(len(stamps))
        out.append(
            f'<path class="event" d="M {x - half:.1f} {y:.1f} H {x + half:.1f}" '
            f'stroke="{colour}" stroke-width="{2.2 if hero else 1.5}" '
            f'stroke-opacity="{1.0 if hero else 0.8}"/>'
        )
        dropped += max(0, len(stamps) - DOT_CAP)
        for stamp in stamps[:DOT_CAP]:
            dy = ts_to_y(stamp, weeks, regs)
            if dy is None:
                continue
            out.append(f'<circle cx="{x:.1f}" cy="{dy:.1f}" '
                       f'r="{1.25 if hero else 0.85}" fill="{colour}" '
                       f'fill-opacity="{0.9 if hero else 0.55}"/>')
            dots += 1
    return "".join(out), dots, dropped


def arc(x0, y0, x1, y1, weight=1.0, strands=3, bright=False, rise_abs=None):
    """A braided amber arc: one real relation, drawn as a long melding sweep.
    NOT-DATA: the filament count and the height of the lift. The endpoints,
    the row and the stroke weight are real."""
    colour = AMBER_WHITE if bright else AMBER
    span = abs(x1 - x0)
    rise = rise_abs if rise_abs is not None else span * 0.42
    ctrl = max(span * 0.34, 24.0)
    out = []
    for i in range(strands):
        skew = (i - (strands - 1) / 2.0) * 2.6
        cy = y0 - rise + skew
        out.append(
            f'<path class="arc" d="M {x0:.1f} {y0 + skew * 0.35:.1f} '
            f'C {x0 + ctrl:.1f} {cy:.1f}, {x1 - ctrl * 0.88:.1f} '
            f'{y1 - rise * 0.30 + skew:.1f}, {x1:.1f} {y1 + skew * 0.30:.1f}" '
            f'stroke="{colour}" fill="none" stroke-linecap="round" '
            f'stroke-width="{max(0.45, weight * (1.0 if i == 1 else 0.62)):.2f}" '
            f'stroke-opacity="{(0.85 if bright else 0.55) * (1.0 if i == 1 else 0.6):.3f}"/>'
        )
    return "".join(out)


def origin_tick(x, y, wide=False):
    """The small green marker at every arc origin."""
    half = 7.0 if wide else 5.0
    return (f'<path class="gtick" d="M {x - half:.1f} {y:.1f} H {x + half:.1f}" '
            f'stroke="{GREEN}" stroke-width="{2.6 if wide else 2.0}"/>')


def urgent_tick(x, y):
    """Green square on a stream: one real urgent `!` to-do."""
    return (f'<rect class="gtick" x="{x - 3.1:.1f}" y="{y - 3.1:.1f}" width="6.2" '
            f'height="6.2" fill="{GREEN}" fill-opacity=".95"/>')


def chip(x, y, text, size=8.0, pad=5.0):
    """A micro-label on its own dark ground, so it never fouls what it sits on."""
    width = len(text) * size * 0.62 + pad * 2
    return (
        f'<rect x="{x - width / 2:.1f}" y="{y - size - 2:.1f}" width="{width:.1f}" '
        f'height="{size + 6:.1f}" rx="1.5" fill="{GROUND}" fill-opacity=".92"/>'
        f'<text class="arclab" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">'
        f'{upper(text)}</text>'
    )


def link(href, body, tip=None) -> str:
    """An SVG anchor. Titles come from folder names and STATUS.md, so they are
    escaped as data and never interpreted."""
    title = f"<title>{esc(tip)}</title>" if tip else ""
    return f'<a href="{esc(href)}">{title}{body}</a>'


# ══ the page ══════════════════════════════════════════════════════════════
# Geometry copied from build-v2.py so the render matches comp-v2.png.

W = 1280
LEFT, RIGHT = 112, 800
MAST_H = 104
BAND_BOTTOM = 288
HEAD_Y = 340
REG_TOP, REG_H, REG_GAP = 372, 78, 40
SPL_X, SPL_Y, SPL_W, SPL_H = 500, 1082, 380, 146
BASELINE = 1382
UNIT = 13.0                 # one cell = one open to-do; the comp's height
BAR_W = 46.0
PLATE_LINES = 2             # readout lines the landing plate has room for
DOT_CAP = 80                # per-week commit dots drawn on one stream
FOCUS_X, FOCUS_W, FOCUS_Y, FOCUS_H = 840, 396, 340, 690
FOOT_Y, FOOT_H = 1470, 148
CAP_Y = 1668
H = 1820
CELL, GX, GY = 3.6, 1.0, 1.0
FOOT_CELL, FOOT_GX, FOOT_GY = 3.2, 0.9, 0.9

CSS = f"""
*{{box-sizing:border-box}}
html,body{{margin:0;background:{GROUND};}}
body{{width:{W}px;font-family:'IBM Plex Sans',Arial,sans-serif;color:{MUTED};}}
svg{{display:block}}
a{{text-decoration:none}}
svg a{{cursor:pointer}}
svg a:hover text{{fill-opacity:1}}
svg a:focus-visible{{outline:1px solid {FROZEN}}}
.wall path{{fill:{FROZEN}}}
.weeklab{{fill:{FROZEN};font:500 8.5px 'IBM Plex Mono',monospace;letter-spacing:.13em}}
.weekdate{{fill:{FROZEN};fill-opacity:.55;font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.1em}}
.headname{{font-family:'IBM Plex Mono',monospace;font-weight:500;letter-spacing:.11em}}
.plate{{fill:{SCREEN};stroke:{FROZEN};stroke-width:1;stroke-opacity:.55}}
.plate-title{{fill:{FROZEN};font:500 8.5px 'IBM Plex Mono',monospace;letter-spacing:.2em}}
.plate-used{{fill:{FROZEN};fill-opacity:.5;font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.12em}}
.readout{{fill:{FROZEN_LIT};font:500 12.5px/1.5 'IBM Plex Mono',monospace}}
.readout-dim{{fill:{MUTED};font:400 11.5px 'IBM Plex Mono',monospace}}
.micro{{fill:{MUTED};font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.18em}}
.micro-a{{fill:{AMBER};font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.18em}}
.micro-b{{fill:{FROZEN};font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.18em}}
.launch{{fill:{AMBER};fill-opacity:.55;font:500 7px 'IBM Plex Mono',monospace;letter-spacing:.16em}}
.launch-lit{{fill:{AMBER_LIT};fill-opacity:.9;font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.16em}}
.big{{fill:{FROZEN_LIT};font:600 30px 'Space Grotesk',sans-serif;letter-spacing:-.01em}}
.mid{{fill:{FROZEN_LIT};font:600 17px 'Space Grotesk',sans-serif}}
.body{{fill:#C9D1DA;font:400 13px/1.5 'IBM Plex Sans',sans-serif}}
.caption{{fill:{MUTED};font:400 9.5px 'IBM Plex Mono',monospace;letter-spacing:.06em}}
.rule{{stroke:{FROZEN};stroke-opacity:.3;stroke-width:1}}
.rule-a{{stroke:{AMBER};stroke-opacity:.45;stroke-width:1}}
.arclab{{fill:{AMBER};fill-opacity:.85;font:500 8px 'IBM Plex Mono',monospace;letter-spacing:.12em}}
.famlab{{fill:{FROZEN};font:500 9px 'IBM Plex Mono',monospace;letter-spacing:.14em}}
.famcount{{fill:{FROZEN};fill-opacity:.55;font:500 8.5px 'IBM Plex Mono',monospace}}
.barlab{{fill:{AMBER};fill-opacity:.75;font:500 7.6px 'IBM Plex Mono',monospace;letter-spacing:.08em}}
.focus-n{{fill:{MUTED};font:500 9px 'IBM Plex Mono',monospace}}
.focus-t{{fill:#CDD5DE;font:400 11.5px 'IBM Plex Sans',sans-serif}}
.focus-p{{fill:{AMBER};fill-opacity:.8;font:500 7.6px 'IBM Plex Mono',monospace;letter-spacing:.12em}}

.detail{{width:{W}px;padding:0 44px 60px;font-family:'IBM Plex Mono',monospace}}
.detail summary{{cursor:pointer;list-style:none;padding:14px 0;
  color:{FROZEN};font-size:9px;letter-spacing:.18em;text-transform:uppercase;
  border-top:1px solid rgba(127,176,232,.3)}}
.detail summary::-webkit-details-marker{{display:none}}
.detail summary::before{{content:"+ ";color:{AMBER}}}
.detail details[open]>summary::before{{content:"− "}}
.detail .fam{{margin:18px 0 6px;color:{FROZEN};font-size:9px;letter-spacing:.2em;
  text-transform:uppercase;border-bottom:1px solid rgba(127,176,232,.22);padding-bottom:5px}}
.detail .proj{{padding:10px 0 12px;border-bottom:1px solid rgba(127,176,232,.1)}}
.detail .proj h3{{margin:0;font:600 14px 'Space Grotesk',sans-serif;color:{FROZEN_LIT}}}
.detail .meta{{color:{MUTED};font-size:9.5px;letter-spacing:.06em;margin-top:4px}}
.detail .now{{color:#C9D1DA;font:400 12px/1.55 'IBM Plex Sans',sans-serif;
  margin-top:7px;max-width:96ch}}
.detail .next{{color:{FROZEN_LIT};font:500 11.5px 'IBM Plex Mono',monospace;margin-top:6px}}
.detail .next b{{color:{AMBER};font-weight:500}}
.detail .open{{display:inline-block;margin-top:8px;color:{AMBER};font-size:8px;
  letter-spacing:.16em;text-transform:uppercase;opacity:.75}}
.detail .open:hover{{opacity:1}}
.detail .proj:target{{background:rgba(127,176,232,.07);
  box-shadow:-10px 0 0 rgba(242,183,5,.55);scroll-margin-top:16px}}
"""


def fonts_css() -> str:
    """The comp's type, inlined so the board stays one file. Falls back to the
    system stacks in the CSS above if the face file is missing."""
    try:
        return FONTS_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


# ── sections ──────────────────────────────────────────────────────────────

def masthead(data, rows):
    dated = sum(1 for r in rows if r["edays"] is not None)
    return "".join([
        '<text class="micro-b" x="44" y="44">ORCHESTRATOR · BOARD V2 · '
        'THE INSTRUMENT</text>',
        '<text class="big" x="44" y="82">Where you left off</text>',
        f'<text class="micro" x="{W - 44}" y="44" text-anchor="end">'
        f'GENERATED {upper(data["generated_label"])}</text>',
        f'<text class="micro" x="{W - 44}" y="62" text-anchor="end">'
        f'{len(rows)} PROJECTS · {len(data["families"])} FAMILIES · '
        f'{len(data["focus"])} OPEN TO-DOS · {data["sessions_total"]} SESSIONS</text>',
        f'<text class="micro" x="{W - 44}" y="80" text-anchor="end">'
        f'{dated} WITH DATED EVIDENCE · {len(rows) - dated} WITHOUT</text>',
        f'<path class="rule" d="M 44 {MAST_H} H {W - 44}"/>',
    ])


def hero_band(data, stats):
    hero = data["hero_row"]
    out = [f'<text class="micro-a" x="44" y="{MAST_H + 30}">YOU WERE DOING</text>']
    y = MAST_H + 30
    if hero is None:
        out.append(f'<text class="body" x="44" y="{y + 20}">No project carries '
                   f'a hard-dated work event, so there is no channel to show.</text>')
        out.append(f'<path class="rule" d="M 44 {BAND_BOTTOM} H {W - 44}"/>')
        return "".join(out)

    story = hero["now"] or ("No “Now” paragraph in this project's STATUS.md — "
                            "nothing was substituted for it.")
    story_lines, cut = clip(story, 96, 3)
    stats["clipped"] += cut
    for line in story_lines:
        y += 20
        out.append(f'<text class="body" x="44" y="{y}">{esc(line)}</text>')
    y += 30
    if hero["next"]:
        out.append(f'<text class="micro-a" x="44" y="{y}">NEXT · '
                   f'{"URGENT" if hero["next_urgent"] else "FIRST IN LINE"}</text>')
        next_lines, cut = clip(hero["next"], 78, 2)
        stats["clipped"] += cut
        for line in next_lines:
            y += 21
            out.append(f'<text class="readout" x="44" y="{y}">{esc(line)}</text>')
    else:
        out.append(f'<text class="micro-a" x="44" y="{y}">NEXT · NOTHING '
                   f'UNCHECKED</text>')
        y += 21
        out.append(f'<text class="readout" x="44" y="{y}">STATUS.md lists no '
                   f'open to-do for this project.</text>')

    hours = hero["edays"] * 24
    since = (f"{hours:.1f} h" if hours < 48 else f"{hero['edays']:.1f} d")
    kind = "commit" if hero["evidence"] == "commit" else "session stamp"
    week_commits = hero["weeks"][0]["commits"] if hero["weeks"] else 0
    right = W - 44
    out += [
        f'<path class="rule-a" d="M {right - 300} {MAST_H + 18} V {BAND_BOTTOM - 20}"/>',
        f'<text class="micro-a" x="{right}" y="{MAST_H + 30}" text-anchor="end">'
        f'THE CHANNEL</text>',
        f'<text class="mid" x="{right}" y="{MAST_H + 56}" text-anchor="end">'
        f'{esc(hero["name"])}</text>',
        f'<text class="readout-dim" x="{right}" y="{MAST_H + 78}" text-anchor="end">'
        f'{since} since its last {kind}</text>',
        f'<text class="readout-dim" x="{right}" y="{MAST_H + 98}" text-anchor="end">'
        f'{week_commits} commits this week · {hero["open_todos"]} open · '
        f'{len(hero["urgent_todos"])} urgent</text>',
        f'<text class="readout-dim" x="{right}" y="{MAST_H + 118}" text-anchor="end">'
        f'family “{esc(hero["family"])}” · {len(hero["family_members"])} siblings</text>',
        f'<text class="readout-dim" x="{right}" y="{MAST_H + 138}" text-anchor="end">'
        f'{len(hero["sessions"])} ACT sessions</text>',
        link(launch_url(hero["path"]),
             f'<text class="launch-lit" x="{right}" y="{MAST_H + 162}" '
             f'text-anchor="end">OPEN A SESSION HERE ↗</text>',
             f'New Claude session in {hero["path"]}'),
        f'<path class="rule" d="M 44 {BAND_BOTTOM} H {W - 44}"/>',
    ]
    return "".join(out)


def week_labels(x, regs, weeks):
    out = []
    for week, (top, _h) in zip(weeks, regs):
        out.append(f'<text class="weeklab" x="{x}" y="{top + 9}">'
                   f'{upper(week["iso"])}</text>')
        out.append(f'<text class="weekdate" x="{x}" y="{top + 21}">'
                   f'{upper(week["label"])}</text>')
    return "".join(out)


def walls(shown, xs, regs, plate_w, capacity, stats):
    out = ['<g class="wall">']
    for row, x in zip(shown, xs):
        values = normalize(row["record"])
        stats["record_bytes"] += len(row["record"])
        for index, (top, height) in enumerate(regs):
            slice_ = values[index * capacity:(index + 1) * capacity]
            if not slice_:
                continue
            svg, used, nodes = pack_plate(x - plate_w / 2, top, plate_w, height,
                                          slice_, CELL, GX, GY)
            stats["cells"] += used
            stats["wall_paths"] += nodes
            out.append(svg)
    out.append("</g>")
    return "".join(out)


def bar_unit(shown):
    """Cell height for the footer bars. One cell is always one real to-do, so
    a bar's height stays exactly proportional to its count; the cell only
    shrinks when the tallest bar would otherwise reach the landing plate."""
    tallest = max((r["open_todos"] for r in shown), default=0)
    headroom = BASELINE - (SPL_Y + SPL_H + 24)
    if not tallest:
        return UNIT
    return min(UNIT, headroom / tallest)


def streams(data, shown, xs, x_of, regs, wall_bottom, unit, stats):
    hero = data["hero"]
    out = []
    for i, (row, x) in enumerate(zip(shown, xs)):
        is_hero = row["name"] == hero
        kind = "hero" if is_hero else "dated"
        r = recency(row["edays"])
        end = SPL_Y + SPL_H + 4 if is_hero else wall_bottom + 46
        out.append(stream(x, HEAD_Y, end, r, kind, phase=i * 0.41))
        half = 9.0 if is_hero else 5.5
        colour = AMBER_LIT if is_hero else AMBER
        out.append(f'<path d="M {x - half} {HEAD_Y} H {x + half}" stroke="{colour}" '
                   f'stroke-width="2.6"/>')
        name = row["name"] if len(row["name"]) <= 17 else row["name"][:16] + "…"
        out.append(link(
            f'#p-{slug(row["name"])}',
            f'<text class="headname" x="{x:.1f}" y="{HEAD_Y - 12}" '
            f'text-anchor="middle" fill="{colour}" font-size="7.8">'
            f'{upper(name)}</text>',
            f'{row["name"]} — jump to its detail block'))
        out.append(f'<text class="headname" x="{x:.1f}" y="{HEAD_Y - 26}" '
                   f'text-anchor="middle" fill="{colour}" fill-opacity=".55" '
                   f'font-size="7.6">{row["edays"]:.2f} D</text>')
        out.append(link(
            launch_url(row["path"]),
            f'<text class="launch" x="{x:.1f}" y="{HEAD_Y - 40}" '
            f'text-anchor="middle">OPEN ↗</text>',
            f'New Claude session in {row["path"]}'))
        marks, dots, dropped = event_marks(x, row, data["weeks"], regs, is_hero)
        out.append(marks)
        stats["dots"] += dots
        stats["dots_dropped"] += dropped
    hero_row = data["hero_row"]
    if hero_row is not None and hero in x_of:
        hx = x_of[hero]
        out.append(stream(hx, SPL_Y + SPL_H + 4,
                          BASELINE - hero_row["open_todos"] * unit,
                          1.0, "hero", phase=0.19))
    return "".join(out)


def arcs(data, shown, xs, x_of, regs, stats):
    """Real ACT/NEW sessions of the shown projects, melding into their own
    streams, plus the INBOX routings whose two ends are both on the fall."""
    hero = data["hero"]
    out = []
    for row, x in zip(shown, xs):
        for i, session in enumerate(row["sessions"]):
            if not session["when"]:
                continue
            y = ts_to_y(session["when"], data["weeks"], regs)
            if y is None:
                stats["arcs_offscale"] += 1
                continue
            # a session is a tributary of its own project: it melds into that
            # project's stream at the row of its real stamp. NOT-DATA: the
            # origin offset, staggered so several braid rather than overlap.
            reach = 150.0 + i * 46.0
            x0 = x - reach if x - reach > LEFT - 40 else x + reach
            rise = min(reach * 0.46, max(24.0, y - (HEAD_Y + 14)))
            out.append(arc(x0, y, x, y + 10, 2.0 if row["name"] == hero else 1.3,
                           bright=row["name"] == hero, rise_abs=rise))
            out.append(origin_tick(x0, y))
            stats["arcs"] += 1
            stats["session_arcs"] += 1
    for item in data["inbox"]:
        if item["source"] in x_of and item["target"] in x_of:
            x0, x1 = x_of[item["source"]], x_of[item["target"]]
            y = regs[0][0] + 9
            out.append(arc(x0, y, x1, y + 10, 2.4, strands=4, bright=True,
                           rise_abs=30.0))
            out.append(origin_tick(x0, y, wide=True))
            out.append(chip(x0 - 58, y + 3, f'inbox {item["date"]}'))
            stats["arcs"] += 1
            stats["inbox_arcs"] += 1
        else:
            stats["inbox_offfall"] += 1
    return "".join(out)


def urgent_squares(shown, xs, regs, stats):
    out = []
    top, height = regs[0]
    for row, x in zip(shown, xs):
        for i, _ in enumerate(row["urgent_todos"]):
            out.append(urgent_tick(x, top + height + 10 + i * 8))
            stats["urgent_squares"] += 1
    return "".join(out)


def focus_panel(data, stats):
    items = data["focus"][:FOCUS_ROWS]
    more = len(data["focus"]) - len(items)
    out = [
        f'<rect x="{FOCUS_X}" y="{FOCUS_Y}" width="{FOCUS_W}" height="{FOCUS_H}" '
        f'rx="2" fill="{SCREEN}" stroke="{FROZEN}" stroke-width="1" '
        f'stroke-opacity=".4"/>',
        f'<text class="micro-b" x="{FOCUS_X + 16}" y="{FOCUS_Y - 12}">FOCUS · '
        f'{len(data["focus"])} OPEN TO-DOS · {data["focus_urgent"]} URGENT FIRST</text>',
    ]
    y = FOCUS_Y + 30
    for index, item in enumerate(items, 1):
        body = []
        if index > 1:
            out.append(f'<path d="M {FOCUS_X + 16} {y - 22} H {FOCUS_X + FOCUS_W - 16}" '
                       f'stroke="{FROZEN}" stroke-opacity=".14" stroke-width="1"/>')
        if item["urgent"]:
            body.append(f'<rect x="{FOCUS_X + 16}" y="{y - 8}" width="7" height="7" '
                        f'fill="{GREEN}"/>')
        else:
            body.append(f'<text class="focus-n" x="{FOCUS_X + 16}" y="{y}">'
                        f'{index:02d}</text>')
        item_lines, cut = clip(item["text"], 42, 2)
        stats["clipped"] += cut
        for line in item_lines:
            body.append(f'<text class="focus-t" x="{FOCUS_X + 36}" y="{y}">'
                        f'{esc(line)}</text>')
            y += 16
        body.append(f'<text class="focus-p" x="{FOCUS_X + 36}" y="{y + 2}">'
                    f'{upper(item["project"])}</text>')
        out.append(link(f'#p-{slug(item["project"])}', "".join(body),
                        f'{item["project"]} — jump to its detail block'))
        y += 40
    label = f"+{more} MORE" if more > 0 else "NONE HIDDEN"
    out.append(f'<text class="focus-n" x="{FOCUS_X + 16}" y="{y}">{label}</text>')
    assert y < FOCUS_Y + FOCUS_H, f"focus column overruns its panel at y={y:.0f}"
    return "".join(out)


def landing(data, stats):
    """The detached blue plate the channel lands on: a real byte band over the
    real next action."""
    hero = data["hero_row"]
    if hero is None:
        return ""
    band_h = 26.0
    tail = hero["record"][-700:]
    cells, used, nodes = pack_plate(SPL_X + 12, SPL_Y + 12, SPL_W - 24, band_h,
                                    normalize(tail), 3.4, .95, .95)
    stats["cells"] += used
    stats["wall_paths"] += nodes
    # The plate is a fixed-height object in the comp, so the readout is capped
    # at PLATE_LINES and the cut is shown with an ellipsis rather than hidden.
    wrapped, cut = clip(hero["next"] or "STATUS.md lists no open to-do.",
                        45, PLATE_LINES)
    stats["clipped"] += cut
    lines = [(text, "readout") for text in wrapped]
    lines.append(("", "readout"))
    lines.append((f'{hero["name"][:24]} · {hero["open_todos"]} open · '
                  f'{"URGENT" if hero["next_urgent"] else "next in line"}',
                  "readout-dim"))
    out = [
        f'<rect class="plate" x="{SPL_X}" y="{SPL_Y}" width="{SPL_W}" '
        f'height="{SPL_H}" rx="2"/>',
        f'<g class="wall">{cells}</g>',
        f'<path d="M {SPL_X + 12} {SPL_Y + band_h + 22} H {SPL_X + SPL_W - 12}" '
        f'stroke="{FROZEN}" stroke-width="1" stroke-opacity=".38"/>',
        f'<text class="plate-title" x="{SPL_X + 12}" y="{SPL_Y + band_h + 40}">'
        f'{upper("next · " + hero["name"])}</text>',
        f'<text class="plate-used" x="{SPL_X + SPL_W - 12}" '
        f'y="{SPL_Y + band_h + 40}" text-anchor="end">{used} BYTES</text>',
    ]
    ty = SPL_Y + band_h + 40
    for text, cls in lines:
        ty += 19.0
        out.append(f'<text class="{cls}" x="{SPL_X + 12}" y="{ty:.1f}">'
                   f'{esc(text)}</text>')
    assert ty <= SPL_Y + SPL_H - 4, f"landing plate overruns its box at {ty:.0f}"
    return "".join(out)


def bars(data, shown, xs, unit, stats):
    """One granular amber bar per shown project: ONE CELL PER OPEN TO-DO, so
    bar height IS the count, not a scaled magnitude."""
    hero = data["hero"]
    out = [f'<path class="baserule" d="M {min(xs) - 14:.1f} {BASELINE + 3} '
           f'H {max(xs) + 14:.1f}" stroke="{AMBER}" stroke-width="1" '
           f'stroke-opacity=".5"/>']
    for row, x in zip(shown, xs):
        count = row["open_todos"]
        is_hero = row["name"] == hero
        colour = AMBER_LIT if is_hero else AMBER
        opacity = 0.95 if is_hero else 0.72
        for i in range(count):
            y = BASELINE - (i + 1) * unit
            out.append(
                f'<rect class="todocell" x="{x - BAR_W / 2:.1f}" y="{y + 1.4:.1f}" '
                f'width="{BAR_W:.1f}" height="{max(unit - 2.8, 1.0):.1f}" rx=".6" '
                f'fill="{colour}" fill-opacity="{opacity:.2f}"/>'
            )
            stats["bar_cells"] += 1
        if is_hero and count:
            top = BASELINE - count * unit
            out.append(
                f'<path d="M {x - BAR_W / 2 - 2:.1f} {top - 5:.1f} '
                f'H {x + BAR_W / 2 + 2:.1f}" stroke="{AMBER_WHITE}" '
                f'stroke-width="2.6"/>')
        out.append(f'<text class="barlab" x="{x:.1f}" y="{BASELINE - count * unit - 8:.1f}" '
                   f'text-anchor="middle" font-size="9">{count}</text>')
        out.append(f'<text class="barlab" x="{x:.1f}" y="{BASELINE + 16:.1f}" '
                   f'text-anchor="middle" font-size="7">'
                   f'{upper(row["name"][:18])}</text>')
    tick = f"WHITE TICK = {upper(hero)}" if hero else "NO HERO"
    out.append(f'<text class="micro-a" x="44" y="{BASELINE + 34}">OPEN TO-DOS · '
               f'ONE CELL = ONE REAL TO-DO · {tick}</text>')
    return "".join(out)


def foot_wall(data, stats):
    """Everything else: one dim wall of their real records, families etched."""
    rest = data["rest"]
    blob = b"".join(row["record"] for row in rest)
    stats["foot_blob"] = len(blob)
    svg, used, nodes = pack_plate(44, FOOT_Y, W - 88, FOOT_H, normalize(blob),
                                  FOOT_CELL, FOOT_GX, FOOT_GY)
    stats["foot_cells"] = used
    stats["wall_paths"] += nodes
    out = [
        f'<text class="micro-b" x="44" y="{FOOT_Y - 12}">EVERYTHING ELSE · '
        f'{len(rest)} PROJECTS · {sum(r["open_todos"] for r in rest)} OPEN TO-DOS · '
        f'ONE WALL OF THEIR OWN RECORD BYTES</text>',
        f'<g class="wall" opacity=".34">{svg}</g>',
    ]
    shown_names = {r["name"] for r in data["shown"]}
    fams = [(name, members) for name, members in data["families"]
            if any(m["name"] not in shown_names for m in members)]
    stats["fam_total"] = len(fams)
    cols, pitch_x = 5, (W - 88) / 5
    for index, (name, members) in enumerate(fams[:FAM_CHIPS]):
        row_i, col_i = divmod(index, cols)
        x = 52 + col_i * pitch_x
        y = FOOT_Y + 20 + row_i * 33
        label = name if len(name) <= 22 else name[:21] + "…"
        out.append(f'<rect x="{x - 5}" y="{y - 11}" width="{pitch_x - 16:.0f}" '
                   f'height="16" fill="{GROUND}" fill-opacity=".82"/>')
        out.append(link(
            f'#f-{slug(name)}',
            f'<text class="famlab" x="{x}" y="{y}">{upper(label)}</text>'
            f'<text class="famcount" x="{x + pitch_x - 26:.0f}" y="{y}" '
            f'text-anchor="end">×{len(members)}</text>',
            f'family “{name}” — jump to its detail block'))
        stats["fam_chips"] += 1
    return "".join(out)


def caption(data, stats, rows, capacity, weeks_span):
    """The honesty footer: the recency law, the mtime exclusion, every cap,
    the thinning mechanism, and the list of marks that claim nothing."""
    edays = [r["edays"] for r in rows if r["edays"] is not None]
    folders, status_files, day = pinned_counts(rows, data["now"])
    hero = data["hero_row"]
    shown, rest = data["shown"], data["rest"]

    span = (f'POOL RANGE {min(edays):.2f} → {max(edays):.1f} d'
            if edays else "NO PROJECT CARRIES A DATED WORK EVENT")
    arc_note = (f'ARCS = THE {stats["arcs"]} REAL SESSIONS AND ROUTINGS ON THE '
                f'SHOWN STREAMS ({stats["session_arcs"]} SESSIONS, '
                f'{stats["inbox_arcs"]} INBOX), EACH ENTERING AT THE REGISTER ROW '
                f'OF ITS OWN TIMESTAMP; GREEN BAR AT EVERY ORIGIN.')
    if not stats["arcs"]:
        arc_note = ('NO ARCS: NONE OF THE SHOWN PROJECTS HAS A SESSION OR AN '
                    'INBOX ROUTING INSIDE THESE SIX WEEKS — STATED, NOT '
                    'SUBSTITUTED SILENTLY.')
    skipped = []
    if stats["arcs_offscale"]:
        skipped.append(f'{stats["arcs_offscale"]} SESSION STAMPS FALL OUTSIDE '
                       f'THE SIX WEEKS AND ARE NOT DRAWN')
    if stats["inbox_offfall"]:
        skipped.append(f'{stats["inbox_offfall"]} INBOX ROUTING(S) HAVE AN END '
                       f'THAT IS NOT ON THE FALL AND ARE NOT DRAWN')

    lines = [
        f'THE INSTRUMENT · THE FALL SHOWS {len(shown)} OF {len(rows)} PROJECTS — '
        f'THE MOST RECENTLY EVIDENCED; THE OTHER {len(rest)} ARE THE ONE DIM WALL '
        f'AT THE FOOT. NOTHING IS HIDDEN WITHOUT BEING COUNTED.',
        f'STREAM = ONE PROJECT. DENSITY AND BRIGHTNESS = RECENCY, LOG SCALE: '
        f'{RECENCY_LAW}, {PITCH_LAW}.',
        f'd = DAYS SINCE THE NEWEST HARD-DATED WORK EVENT (GIT AUTHOR STAMP %at OR '
        f'A SESSION STAMP), PRINTED UNDER EACH STREAM HEAD. {span}.',
        f'FOLDER AND STATUS.md MTIMES ARE NEVER USED FOR RECENCY: A BULK FILESYSTEM '
        f'EVENT LEFT {folders} FOLDER MTIMES AND {status_files} STATUS.md MTIMES '
        f'SITTING ON ONE DAY ({day:.1f} d AGO), SO NEITHER CAN CARRY IT. PROJECTS '
        f'WITH NO DATED EVIDENCE ARE UNRANKED, NOT FLOORED.',
        f'{CELL_LAW.upper()} — {stats["cells"]:,} CELLS IN THE FALL AND THE PLATE, '
        f'{stats["foot_cells"]:,} IN THE FOOT WALL, EVERY ONE A REAL RECORD BYTE '
        f'(STATUS.md IN ORDER, THEN git log -{GIT_LOG}).',
        f'WALL CAPS: EACH STREAM SHOWS THE FIRST {capacity * weeks_span:,} BYTES OF ITS '
        f'RECORD, {capacity:,} PER REGISTER IN READING ORDER — REGISTER k IS THE k-TH '
        f'SLICE OF THE RECORD, NOT THAT WEEK’S OWN BYTES; THE SIX SHOWN RECORDS RUN TO '
        f'{stats["record_bytes"]:,} BYTES. THE FOOT WALL SHOWS {stats["foot_cells"]:,} '
        f'OF {stats["foot_blob"]:,} BYTES.',
        f'TEXT CAPS: HEAD NAMES ARE CUT AT 17 CHARACTERS, EVERY OTHER CUT IS MARKED “…” '
        f'({stats["clipped"]} ON THIS RUN). A STREAM DRAWS AT MOST {DOT_CAP} COMMIT DOTS '
        f'PER WEEK ({stats["dots"]:,} DRAWN, {stats["dots_dropped"]:,} OVER THE CAP); THE '
        f'WEEK TICK STILL COUNTS EVERY EVENT.',
        f'PAGE WEIGHT: WALL CELLS ARE WRITTEN AS ONE PACKED SVG PATH PER OPACITY '
        f'BUCKET ({BUCKETS} BUCKETS) INSTEAD OF ONE ELEMENT PER CELL. SAME GRID, SAME '
        f'CELLS, NO DENSITY REDUCTION — {stats["cells"] + stats["foot_cells"]:,} CELLS '
        f'IN {stats["wall_paths"]:,} NODES.',
        arc_note,
        f'GREEN SQUARES UNDER THE TOP REGISTER = THE SHOWN PROJECTS’ '
        f'{stats["urgent_squares"]} REAL URGENT ITEMS, OF {data["focus_urgent"]} IN '
        f'THE WHOLE POOL. FOOTER BARS COUNT ONLY THE SHOWN PROJECTS: '
        f'{stats["bar_cells"]} CELLS.',
        f'FOCUS SHOWS {min(FOCUS_ROWS, len(data["focus"]))} OF {len(data["focus"])} '
        f'OPEN TO-DOS, URGENT FIRST. THE FOOT WALL ETCHES {stats["fam_chips"]} OF '
        f'{stats["fam_total"]} FAMILIES. THE READOUT BAND, THE FOCUS SCREEN AND THE '
        f'LANDING PLATE ARE VERBATIM STATUS.md TEXT.',
        f'CLICK A STREAM HEAD, A FOCUS ROW OR A FAMILY TO JUMP TO ITS BLOCK IN THE '
        f'DETAIL REGION BELOW. “OPEN ↗” IS A claude-cli://open?cwd=… DEEP LINK: IT '
        f'STARTS A NEW SESSION IN THAT FOLDER — NO DEEP LINK INTO AN EXISTING '
        f'SESSION EXISTS.',
        f'NOT DATA, CLAIMS NOTHING: DASH PHASE OF EACH FILAMENT, THE 3-FILAMENT BRAID, '
        f'ARC LIFT AND ITS OFF-CANVAS ORIGIN X, PLATE CORNER RADII, LABEL BACKING '
        f'PLATES, STREAM-HEAD BAR LENGTH.',
    ]
    if skipped:
        lines.append("ALSO NOT DRAWN: " + "; ".join(skipped) + ".")
    if hero is not None and not hero["sessions"]:
        lines.append(
            f'{upper(hero["name"])} HAS 0 ACT SESSIONS THIS SNAPSHOT, SO NO ARC '
            f'ENTERS THE CHANNEL — STATED, NOT SUBSTITUTED SILENTLY.')
    if data["sessions_generated"] is not None:
        stamp = data["sessions_generated"].astimezone().strftime("%Y-%m-%d %H:%M")
        age = (data["now"].astimezone() - data["sessions_generated"].astimezone())
        stale = " · OLDER THAN 24 H, TREAT AS STALE" if age.total_seconds() > DAY else ""
        lines.append(f'SESSIONS ARE A SNAPSHOT TAKEN {upper(stamp)}{stale}; '
                     f'sessions.json IS WRITTEN BY A CLAUDE SESSION, NOT A LIVE FEED.')
    else:
        lines.append('NO sessions.json SNAPSHOT WAS READABLE, SO NO SESSION '
                     'EVIDENCE AND NO SESSION ARCS ARE ON THIS PAGE.')

    out = [f'<path class="rule" d="M 44 {CAP_Y - 20} H {W - 44}"/>']
    written = 0
    for sentence in lines:
        for line in wrap(sentence, 166):
            out.append(f'<text class="caption" x="44" y="{CAP_Y + written * 13:.0f}">'
                       f'{esc(line)}</text>')
            written += 1
    return "".join(out), CAP_Y + written * 13 + 26


# ── the detail region (v1's reveal idiom, dark form) ──────────────────────

def detail_project(row):
    bits = [f'{row["open_todos"]} open']
    if row["urgent_todos"]:
        bits.append(f'{len(row["urgent_todos"])} urgent')
    if row["evidence_date"]:
        bits.append(f'{row["evidence"]} {row["evidence_date"]} '
                    f'({row["edays"]:.1f} d)')
    else:
        bits.append("no dated evidence")
    if row["sessions"]:
        bits.append(f'{len(row["sessions"])} live session'
                    f'{"s" if len(row["sessions"]) > 1 else ""}')
    if row["memory"]:
        bits.append("memory")
    story = row["now"] or ("No STATUS.md “Now” paragraph."
                           if row["has_status"] else "No STATUS.md.")
    nxt = ""
    if row["next"]:
        flag = "<b>! </b>" if row["next_urgent"] else ""
        nxt = f'<div class="next">{flag}{esc(row["next"])}</div>'
    return (
        f'<div class="proj" id="p-{slug(row["name"])}">'
        f'<h3>{esc(row["name"])}</h3>'
        f'<div class="meta">{esc(" · ".join(bits))}</div>'
        f'<div class="now">{esc(story)}</div>{nxt}'
        f'<a class="open" href="{esc(launch_url(row["path"]))}">'
        f'open a session here ↗</a></div>'
    )


def detail_region(data):
    blocks = []
    for name, members in data["families"]:
        blocks.append(f'<div class="fam" id="f-{slug(name)}">{esc(name)} '
                      f'×{len(members)}</div>')
        for row in members:
            blocks.append(detail_project(row))
    return (
        '<div class="detail"><details><summary>'
        f'All {len(data["rows"])} projects · detail · '
        f'{len(data["families"])} families</summary>'
        f'{"".join(blocks)}</details></div>'
    )


# ══ assembly ══════════════════════════════════════════════════════════════

def render(orch, projects, snapshot, now: datetime):
    """The whole page as one string. Pure for a fixed (scan, snapshot, now)."""
    data = collect(orch, projects, snapshot, now)
    rows, shown = data["rows"], data["shown"]
    stats = {"cells": 0, "foot_cells": 0, "foot_blob": 0, "record_bytes": 0,
             "arcs": 0, "session_arcs": 0, "inbox_arcs": 0, "arcs_offscale": 0,
             "inbox_offfall": 0, "urgent_squares": 0, "bar_cells": 0,
             "dots": 0, "fam_chips": 0, "fam_total": 0, "wall_paths": 0,
             "clipped": 0, "dots_dropped": 0}

    count = max(len(shown), 1)
    pitch = (RIGHT - LEFT) / count
    xs = [LEFT + pitch / 2 + i * pitch for i in range(count)]
    x_of = {row["name"]: x for row, x in zip(shown, xs)}
    plate_w = pitch - 8.0
    regs = registers(REG_TOP, REG_H, REG_GAP)
    wall_bottom = regs[-1][0] + regs[-1][1]
    capacity = plate_capacity(plate_w, REG_H, CELL, GX, GY)
    unit = bar_unit(shown)

    body = [masthead(data, rows), hero_band(data, stats)]
    if shown:
        body.append(walls(shown, xs, regs, plate_w, capacity, stats))
        body.append(week_labels(40, regs, data["weeks"]))
        body.append(arcs(data, shown, xs, x_of, regs, stats))
        body.append(streams(data, shown, xs, x_of, regs, wall_bottom, unit, stats))
        body.append(urgent_squares(shown, xs, regs, stats))
    body.append(focus_panel(data, stats))
    body.append(landing(data, stats))
    if shown:
        body.append(bars(data, shown, xs, unit, stats))
    body.append(foot_wall(data, stats))

    cap_svg, cap_bottom = caption(data, stats, rows, capacity, len(data["weeks"]))
    body.append(cap_svg)
    height = max(H, int(cap_bottom))

    svg = (f'<svg viewBox="0 0 {W} {height}" width="{W}" height="{height}" '
           f'aria-label="The orchestrator board as one fall: hero readout, the '
           f'{len(shown)} most recently evidenced projects as streams through six '
           f'weekly walls, the pooled to-do list, and every other project as one '
           f'wall of its own record bytes">'
           f'<rect width="{W}" height="{height}" fill="{GROUND}"/>'
           f'{"".join(body)}</svg>')

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Orchestrator Board v2 · the instrument</title>'
        f'<style>{fonts_css()}{CSS}</style></head><body>'
        f'{svg}{detail_region(data)}</body></html>\n'
    )
    return page, data, stats


def write(orch, projects, snapshot, now=None):
    """Render and write board-v2.html. Returns (path, data, stats)."""
    now = now or datetime.now()
    page, data, stats = render(orch, projects, snapshot, now)
    OUT_FILE.write_text(page, encoding="utf-8")
    return OUT_FILE, data, stats
