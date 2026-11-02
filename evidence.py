#!/usr/bin/env python3
"""Evidence dating — the one recency law both board skins obey.

A project's date is the newest HARD-DATED work event it can show: a git author
stamp (`%at`, stored inside the commit object) or a Claude session stamp from
sessions.json. Folder mtimes and STATUS.md mtimes are NEVER consulted for
recency: a bulk copy or restore can leave most of them sitting on one day,
so neither can carry it. A project with no dated evidence is
*unranked* — never floored to zero and never ranked in among the dated ones.

Both `orchestrator.py` (skin v1, the print board) and `skin_v2.py` (the
instrument) import this module, so the two boards cannot drift apart about
which project you were last working in. Stdlib only; every function is
deterministic for a fixed repo state and clock, and none of them raise.
"""

from __future__ import annotations

import subprocess
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

DAY = 86400.0
WEEKS = 6                    # the six-week window both skins draw

# ── the launch scheme ─────────────────────────────────────────────────────
# claude-cli://open?cwd=<absolute path>&q=<prompt>. Neither USER-GUIDE.html nor
# CONTRACT.md documents it, so the format was read off the installed CLI:
# hostname must be "open", cwd must be absolute (<=4096 chars), q is the
# pre-filled prompt (<=5000 chars). The prompt is a FIXED string — no file
# content is ever pushed into a launch URL.
LAUNCH_PROMPT = ("Read STATUS.md (and the memory index if present) first, "
                 "then pick this project's thread back up.")


def launch_url(path) -> str:
    """claude-cli://open?cwd=…&q=… — a NEW session in that folder. There is no
    deep link into an existing session, only `claude --resume <id>`."""
    query = urllib.parse.urlencode({"cwd": str(path), "q": LAUNCH_PROMPT},
                                   quote_via=urllib.parse.quote)
    return f"claude-cli://open?{query}"


# ── git ───────────────────────────────────────────────────────────────────

def run_git(root: Path, args, timeout=10) -> str:
    """Run git in `root`; "" on any failure. Never raises, never blocks long."""
    if not (Path(root) / ".git").exists():
        return ""
    try:
        proc = subprocess.run(["git"] + list(args), cwd=str(root),
                              capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def git_head_and_commits(root: Path, count: int):
    """(head_author_ts, [(date, subject)]) from ONE git call.

    The head author stamp is the ranking datum: a date written into the commit
    object, which touching a file cannot forge. The (date, subject) pairs are
    what the board prints.
    """
    out = run_git(root, ["log", f"-{count}", "--format=%at%x09%ad%x09%s",
                         "--date=short"])
    head, commits = None, []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        stamp, date, subject = parts
        if head is None:
            try:
                head = int(stamp)
            except ValueError:
                head = None
        commits.append((date.strip(), subject.strip()))
    return head, commits


def git_window(root: Path, since_ts: float):
    """[(author_ts, subject)] for every commit authored since `since_ts`."""
    since = datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d")
    out = run_git(root, ["log", f"--since={since}", "--format=%at%x09%s"])
    commits = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        stamp, subject = line.split("\t", 1)
        try:
            commits.append((int(stamp), subject.strip()))
        except ValueError:
            continue
    return commits


# ── the law itself ────────────────────────────────────────────────────────

def evidence_of(head_ts, session_ts, now_ts):
    """The newest hard-dated work event → {ts, kind, date, edays}.

    `kind` is "commit", "session", or "none". `edays` is real days since that
    event, or None when the project has no dated evidence at all — the caller
    must leave such a project unranked rather than substituting an mtime.
    """
    dated = [(ts, kind) for ts, kind in
             ((head_ts, "commit"), (session_ts, "session")) if ts]
    if not dated:
        return {"ts": None, "kind": "none", "date": None, "edays": None}
    ts, kind = max(dated)
    return {
        "ts": ts,
        "kind": kind,
        "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
        "edays": max(0.0, (now_ts - ts) / DAY),
    }


# ── the six-week window ───────────────────────────────────────────────────

def week_start(when: datetime) -> datetime:
    """Monday 00:00 local of the week containing `when`."""
    day = when.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def week_windows(now: datetime, count: int = WEEKS):
    """[{index, iso, label, start, end}] newest first, `count` long."""
    this = week_start(now)
    out = []
    for i in range(count):
        start = this - timedelta(weeks=i)
        end = start + timedelta(weeks=1)
        iso_year, iso_week, _ = start.isocalendar()
        out.append({
            "index": i,
            "iso": f"{iso_year}-W{iso_week:02d}",
            "label": start.strftime("%d %b"),
            "start": start.timestamp(),
            "end": end.timestamp(),
        })
    return out


def week_activity(commit_stamps, session_stamps, weeks):
    """Per week (newest first): how many real commits and sessions landed in it.

    The only input is hard stamps, so an empty week is genuinely an empty week
    and not a gap in the evidence.
    """
    out = []
    for window in weeks:
        commits = sum(1 for ts in commit_stamps
                      if window["start"] <= ts < window["end"])
        sessions = sum(1 for ts in session_stamps
                       if window["start"] <= ts < window["end"])
        out.append({"iso": window["iso"], "label": window["label"],
                    "commits": commits, "sessions": sessions,
                    "hits": commits + sessions})
    return out
