#!/usr/bin/env python3
"""Scan ~/Projects and emit a self-contained board.html from existing exhaust:
git log, STATUS.md, HANDOFF.md, Claude memory dirs, sessions.json. Stdlib only.

Recency: every ranking on this board — the hero, the active rows, the
family order, the staleness comparisons — comes from evidence.py, i.e. from
the newest git author stamp or Claude session stamp a project can show. File
and folder mtimes are read (v2 still names them) but NEVER ranked: a bulk
copy or restore can pin most of them to one day, and a hero ranked by them
drifts to whatever a shader cache last wrote.
"""

import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from exo_registry import registry, lane_family, hub_folders             # noqa: E402
from exo_paths import paths, LEGACY_SYNC_DIRNAME                        # noqa: E402
try:                                                                    # private lanes
    from exo_privacy import private_lane_of                             # noqa: E402
except Exception:                                                       # an older hub: nothing is private
    def private_lane_of(**_kw):
        return None

_REG_CACHE = [None]


def _reg():
    """The person's own names, read once per run."""
    if _REG_CACHE[0] is None:
        _REG_CACHE[0] = registry()
    return _REG_CACHE[0]

import evidence

def hub_paths() -> dict:
    """The path resolver's record (tools/exo_paths.py), asked with this file's
    own folder as the hub: where the machine record, the sync package and the
    brain clone are. Read at call time, as the resolver promises."""
    return paths(hub=Path(__file__).resolve().parent)


def record_file() -> Path:
    """The machine record the path resolver finds: the file EXO_MACHINE_JSON
    names, a program tree's <hub>/machine.json, or the older layout's copy.
    Raises OSError when this machine has no record, as a missing file does."""
    found = hub_paths()["machine_file"]
    if found is None:
        raise FileNotFoundError("no machine record was found for this machine")
    return Path(found)


def projects_dir() -> Path:
    """Where this machine keeps its projects.

    Each machine's real roots are recorded in its own machine record
    (gitignored, machine-local), which the resolver finds. A machine may keep
    its projects on another disk, so ~/Projects is wrong there. If the record
    is missing, malformed, or has no projects root, fall back to ~/Projects —
    the behaviour this board has always had.

    ORCH_PROJECTS_ROOT overrides everything: the test harness points it at a
    forged root so checks can be proven against known repo states.
    """
    forced = os.environ.get("ORCH_PROJECTS_ROOT", "").strip()
    if forced:
        return Path(forced)
    try:
        with record_file().open("r", encoding="utf-8") as handle:
            roots = json.load(handle).get("roots") or {}
        recorded = roots.get("projects")
        if isinstance(recorded, str) and recorded.strip():
            return Path(recorded)
    except (OSError, ValueError, AttributeError):
        pass
    return Path.home() / "Projects"


PROJECTS_DIR = projects_dir()
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
HERE = Path(__file__).resolve().parent
OUT_FILE = HERE / "board.html"
SESSIONS_FILE = HERE / "sessions.json"
INBOX_FILE = HERE / "INBOX.md"
GUIDE_CARDS = HERE / "guide-cards.json"      # curated half — synced
GUIDE_FILE = HERE / "GETTING-GOING.md"       # generated half — machine-local


def taught_path() -> Path:
    """The dossier journal the promotion check reads.

    ORCH_TAUGHT_PATH overrides it, mirroring ORCH_PROJECTS_ROOT above: the
    test harness points it at a forged journal so the check can be proven.
    """
    forced = os.environ.get("ORCH_TAUGHT_PATH", "").strip()
    if forced:
        return Path(forced)
    return HERE / "dossier" / "TAUGHT.md"


TAUGHT_FILE = taught_path()

PRUNE_DIRS = {".git", "node_modules", "dist", ".wrangler", "__pycache__"}
PRUNE_FILES = {".DS_Store"}
MAX_DEPTH = 3
DAY = 86400
GIT_COMMITS = 3           # commits printed on the hero card

# Sort key for anything ranked: the evidence stamp, undated last. Never mtime.
EVIDENCE_KEY = lambda project: project["evidence"]["ts"] or -1  # noqa: E731


NEXT_HEADING = re.compile(r"\b(next|to-?do|open|pending)\b", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}\s+(.*)$")

# STATUS.md contract: "## Now" / "## To do" / "## Important", matched loosely.
# "## Where things live" (CONTRACT v1.1) declares artifacts that are known to
# live elsewhere — another branch, a drive, gitignored — so the portability
# check below can tell a declared absence from an unwritten one.
STATUS_SECTIONS = {"now": "now", "todo": "todo", "todos": "todo",
                   "important": "important", "wherethingslive": "where"}
STATUS_TODO = re.compile(r"^\s*[-*+]\s*\[([ xX]?)\]\s*(.*)$")
STATUS_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
FOCUS_ROWS = 8

# Session titles follow "TAG — Proj: purpose". Untagged sessions read as NEW.
SESSION_SEP = " — "
SESSION_TAGS = ("ACT", "ARCH", "HARV", "DEL?")
SESSION_LIVE = ("ACT", "NEW")  # the only tags that earn a row of their own
SESSION_REST = (("ARCH", "ready to archive"), ("HARV", "needs harvest"),
                ("DEL?", "awaiting ruling"))
UNFILED = "Unfiled"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ── scanning ──────────────────────────────────────────────────────────────

def last_activity(root: Path) -> float:
    """Newest mtime under root, walking at most MAX_DEPTH levels deep.

    NOT a ranking signal on this board — see the module docstring. It is kept
    because skin v2 names it on its honesty caption, and because it is the
    scan's stable enumeration order.
    """
    newest = 0.0
    try:
        newest = root.stat().st_mtime
    except OSError:
        pass
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth >= MAX_DEPTH:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for name in filenames:
            if name in PRUNE_FILES:
                continue
            try:
                mtime = os.stat(os.path.join(dirpath, name)).st_mtime
            except OSError:
                continue
            if mtime > newest:
                newest = mtime
    return newest


def clean_markdown(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # keep the HTML valid
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_]+", "", text)
    text = re.sub(r"^\s*[>\-+]\s*", "", text)
    return " ".join(text.split())


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def handoff_summary(lines, limit=180) -> str:
    """First non-heading paragraph, flattened (cut at `limit`; None: whole)."""
    para = []
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or set(stripped) <= set("-=*_"):
            if para:
                break
            continue
        if stripped.startswith("#"):
            if para:
                break
            continue
        para.append(stripped)
    text = clean_markdown(" ".join(para))
    return truncate(text, limit) if limit else text


def handoff_next(lines):
    """First bullet or sentence under the first next/todo/open/pending heading."""
    for i, raw in enumerate(lines):
        match = HEADING.match(raw.strip())
        if not match or not NEXT_HEADING.search(match.group(1)):
            continue
        for follow in lines[i + 1:]:
            stripped = follow.strip()
            if not stripped or set(stripped) <= set("-=*_"):
                continue
            if stripped.startswith("#"):
                break
            text = clean_markdown(stripped)
            if text:
                return truncate(text, 200)
        break
    return None


def read_handoff(root: Path):
    path = root / "HANDOFF.md"
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return {
        "mtime": mtime,
        "summary": handoff_summary(lines),
        "next": handoff_next(lines),
    }


def section_key(heading: str):
    """'To do' / 'TO-DO:' / '## Important' → canonical section name, else None."""
    return STATUS_SECTIONS.get(re.sub(r"[^a-z0-9]", "", heading.lower()))


# A file reference is a backtick-quoted, spaceless token that looks like a file
# or repo path. Spaceless on purpose: `python sync.py pull` is a command, not a
# file claim. Absolute paths and URLs are skipped — they name things outside
# this checkout, which the check below could only ever half-verify.
FILE_REF = re.compile(r"`([^`\s]+)`")
FILE_EXT = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")


def file_refs(lines):
    """Every checkable file/path token named in the given raw lines."""
    refs = set()
    for raw in lines:
        for token in FILE_REF.findall(raw):
            token = token.strip().rstrip(".,;:").replace("\\", "/")
            if not token or "://" in token or "*" in token:
                continue
            if any(ch in token for ch in '<>="'):
                continue        # placeholders and code fragments, not paths
            if token.startswith(("-", "~", "/")) or re.match(r"^[A-Za-z]:", token):
                continue
            if token.startswith(".") and not token.startswith("../"):
                continue        # bare extensions like `.txt`; ../sibling stays
            if "/." in token:
                continue        # `PLAYBOOK.md/.html` shorthand, not a path
            if "/" in token or FILE_EXT.search(token):
                refs.add(token.rstrip("/"))
    return refs


def parse_status(lines):
    """STATUS.md → {now, todos, important}. Never raises on a weird file."""
    sections, current = {}, None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("<!--"):
            continue
        heading = HEADING.match(stripped)
        if heading:
            current = section_key(heading.group(1))
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw)

    # No "To do" heading at all: take checkboxes wherever they happen to sit.
    todos, open_raw = [], []
    for raw in sections.get("todo", lines):
        item = STATUS_TODO.match(raw)
        if not item or item.group(1).strip().lower() == "x":
            continue
        open_raw.append(raw)
        text = item.group(2).strip()
        urgent = text.startswith("!")
        if urgent:
            text = text[1:]
        text = clean_markdown(text)
        if text:
            todos.append({"text": truncate(text, 150), "urgent": urgent})

    important = []
    for raw in sections.get("important", []):
        bullet = STATUS_BULLET.match(raw)
        if not bullet:
            continue
        text = clean_markdown(bullet.group(1))
        if text:
            important.append(truncate(text, 140))

    where_lines = []
    for raw in sections.get("where", []):
        bullet = STATUS_BULLET.match(raw)
        if not bullet:
            continue
        text = plain_text(bullet.group(1))
        if text:
            where_lines.append(truncate(text, 160))

    now_lines = [clean_markdown(line) for line in sections.get("now", [])]
    # Only LIVE content makes file claims: Now, unchecked to-dos, Important.
    # Checked items are history — a file they name may be legitimately gone.
    active = list(sections.get("now", [])) + open_raw + \
        list(sections.get("important", []))
    return {"now": handoff_summary(now_lines), "todos": todos,
            "important": important, "refs": file_refs(active),
            "declared": file_refs(sections.get("where", [])),
            "where": where_lines[:6]}


def read_status(root: Path):
    path = root / "STATUS.md"
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        mtime = path.stat().st_mtime
    except OSError:
        return None
    status = parse_status(lines)
    status["mtime"] = mtime
    return status


def munge(path: Path) -> str:
    """~/.claude/projects dir name: '/', ' ' and '.' each become '-'."""
    name = str(path.resolve())
    for char in ("/", " ", "."):
        name = name.replace(char, "-")
    return name


def has_memory(root: Path) -> bool:
    return (CLAUDE_PROJECTS / munge(root) / "memory").is_dir()


def is_stale(handoff, evidence_ts) -> bool:
    """Real dated work happened more than a day after the handoff was written.

    The comparison is against the evidence stamp, not a folder mtime: a bulk
    touch must never be able to declare a handoff stale.
    """
    if not handoff or not evidence_ts:
        return False
    return evidence_ts - handoff["mtime"] > DAY


def status_is_stale(status, evidence_ts) -> bool:
    """The project moved on more than a day after STATUS.md was last written."""
    if not status or not evidence_ts:
        return False
    return evidence_ts - status["mtime"] > DAY


def portability(root: Path, status):
    """What only THIS machine can see — the checks behind the board's
    Portability section: the portability rule as machinery, so a file that
    lives only on a side branch or only on this disk is said, not assumed.

    Deterministic, per project: (1) files STATUS.md's live sections name that
    this checkout lacks — unless declared under "## Where things live";
    (2) checked-out branch differs from the default; (3) a project with no
    STATUS.md whose STATUS.md exists on a remote branch; (4) uncommitted or
    unpushed work, i.e. bytes the other machine cannot pull. Empty list =
    nothing to say. Never raises.
    """
    warns = []
    refs = status["refs"] if status else set()
    declared = status["declared"] if status else set()
    exempt = declared | {Path(item).name for item in declared}
    for ref in sorted(refs):
        if ref in exempt or Path(ref).name in exempt:
            continue
        try:
            if not (root / ref).exists():
                warns.append(f"STATUS names {ref} — not in this checkout")
        except (OSError, ValueError):
            continue
    if not (root / ".git").exists():
        return warns

    current = evidence.run_git(root, ["branch", "--show-current"]).strip()
    head = evidence.run_git(
        root, ["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()
    default = head.rsplit("/", 1)[-1] if head else ""
    if current and default and current != default:
        warns.append(f"on branch {current} — default is {default}")
    elif current and not default and current not in ("main", "master"):
        warns.append(f"on branch {current}")

    if status is None:
        remote_refs = evidence.run_git(
            root, ["for-each-ref", "refs/remotes",
                   "--format=%(refname:short)"]).split()
        for ref in remote_refs:
            if ref.endswith("/HEAD") or "/" not in ref:
                continue
            if evidence.run_git(root, ["ls-tree", "--name-only", ref,
                                       "STATUS.md"]).strip():
                warns.append(f"STATUS.md exists on {ref}, "
                             "not in this checkout")
                break

    dirty = [line for line in
             evidence.run_git(root, ["status", "--porcelain"]).splitlines()
             if line.strip()]
    if dirty:
        plural = "s" if len(dirty) != 1 else ""
        warns.append(f"{len(dirty)} uncommitted path{plural}")
    ahead = evidence.run_git(
        root, ["rev-list", "--count", "@{upstream}..HEAD"]).strip()
    if ahead.isdigit() and int(ahead) > 0:
        plural = "s" if ahead != "1" else ""
        warns.append(f"{ahead} unpushed commit{plural}")
    return warns


# dossier/TAUGHT.md is a dated journal, one lesson per line. The promotion
# rule: a rule-shaped line dated from the cutoff on must say where
# it went — "[PROMOTED to <where> <date>]" or "[JOURNAL-ONLY]". A promoted
# rule is written to the person's own book,
# dossier/LAWS.md, by tools/personal.py --promote, which stamps the line itself.
# Earlier lines were written before the law and are never flagged. ISO dates
# compare as strings, so the cutoff needs no parsing.
PROMOTION_DAY = "2026-08-31"
TAUGHT_DATED = re.compile(
    r"^(?:-\s*)?([0-9]{4}-[0-9]{2}-[0-9]{2})\s*[—–:]?\s*(.*)$")
TAUGHT_RULE = re.compile(r"\b(rule|law|ratified|ruling)\b", re.IGNORECASE)
TAUGHT_STAMPS = ("[PROMOTED", "[JOURNAL-ONLY", "[WITHDRAWN")   # prefixes: the long forms "[JOURNAL-ONLY — why]" count
PROMOTION_ASK = ("ask the owner: promote to their law book or journal-only — "
                 "tools/personal.py --promote or --journal-only writes it and stamps "
                 "the TAUGHT line")


def unpromoted_rulings():
    """Rule-shaped TAUGHT.md lines dated on or after the promotion law that
    carry neither stamp → [{date, text}], in file order. No journal, or no
    such line, means nothing to say. Never raises."""
    try:
        lines = TAUGHT_FILE.read_text(encoding="utf-8",
                                      errors="replace").splitlines()
    except OSError:
        return []
    flagged = []
    for raw in lines:
        match = TAUGHT_DATED.match(raw.strip())
        if not match:
            continue
        date, text = match.groups()
        if date < PROMOTION_DAY or not TAUGHT_RULE.search(raw):
            continue
        if any(stamp in raw for stamp in TAUGHT_STAMPS):
            continue
        flagged.append({"date": date, "text": plain_text(text)})
    return flagged


def family_of(name: str) -> str:
    """The family a project belongs to — the registry's own `lanes.families`,
    read in the order the person wrote it, first match wins. A name no prefix
    catches is its own family. ONE table, shared with the tree's collector."""
    return lane_family(_reg(), name)


def scan():
    projects, errors = [], []
    if not PROJECTS_DIR.is_dir():
        return projects, errors
    for entry in sorted(PROJECTS_DIR.iterdir()):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        # a lane the user marked private is not on the board.
        # ASSUMES: the mark is the lane's own STATUS line or the registry, read
        # by exo_privacy. Opposite: a cleared lane is drawn (gate-privacy C3b).
        try:
            if private_lane_of(cwd=str(entry), arc=entry.name):
                continue
        except Exception:
            pass
        try:
            # One git call gives both the head author stamp (the ranking datum)
            # and the commit lines the hero card prints.
            head_ts, commits = evidence.git_head_and_commits(entry, GIT_COMMITS)
            status = read_status(entry)
            projects.append({
                "name": entry.name,
                "path": entry,
                "activity": last_activity(entry),
                "head_ts": head_ts,
                "commits": commits,
                "handoff": read_handoff(entry),
                "status": status,
                "portability": portability(entry, status),
                "memory": has_memory(entry),
                "family": family_of(entry.name),
                "sessions": [],       # filled by rank()
                "act": 0,             # filled by rank()
                "weeks": None,        # filled lazily, only for rows with ticks
            })
        except OSError as exc:
            errors.append(f"{entry.name}: {exc}")
    # Enumeration order only — and skin v2's input contract, which is why it is
    # still the mtime. Nothing on the v1 board is ordered by it; rank() below
    # re-orders the list by evidence before anything is rendered.
    projects.sort(key=lambda p: p["activity"], reverse=True)
    return projects, errors


def rank(projects, snapshot, now_ts):
    """Date every project by evidence and return the list newest-first.

    THE ranking step, and the only one. A project's date is the newest git
    author stamp or Claude session stamp it can show (evidence.py). Projects
    with neither keep `ts = None`, sort to the end, and the board leaves them
    unranked — they appear only in Everything else, marked as undated.
    """
    groups = dict(group_sessions(snapshot["sessions"], projects)) if snapshot else {}
    for project in projects:
        sessions = groups.get(project["name"], [])
        session_ts = max((s["when"].timestamp() for s in sessions if s["when"]),
                         default=None)
        project["sessions"] = sessions
        project["act"] = sum(1 for s in sessions if s["tag"] == "ACT")
        project["evidence"] = evidence.evidence_of(project["head_ts"],
                                                   session_ts, now_ts)
        stamp = project["evidence"]["ts"]
        project["stale"] = is_stale(project["handoff"], stamp)
        project["status_stale"] = status_is_stale(project["status"], stamp)
    ranked = sorted(projects, key=lambda p: p["name"])   # deterministic ties
    ranked.sort(key=EVIDENCE_KEY, reverse=True)
    return ranked


def group_families(projects, key=None):
    """[(family, [members in the given order])] ordered by their best member.

    `key` defaults to the mtime, which is skin v2's enumeration contract; v1
    passes EVIDENCE_KEY, the ranking signal. Members keep the caller's order,
    so a list handed in newest-first stays newest-first.
    """
    if key is None:
        key = lambda project: project["activity"]  # noqa: E731
    families = {}
    for project in projects:
        families.setdefault(project["family"], []).append(project)
    return sorted(families.items(),
                  key=lambda kv: max(key(member) for member in kv[1]),
                  reverse=True)


def attach_weeks(project, weeks):
    """Six weeks of hard evidence for one project: commits from git, sessions
    from the snapshot. Computed lazily, so the extra git call runs once per row
    that actually draws ticks — a handful — and not once per project."""
    if project["weeks"] is None:
        stamps = [stamp for stamp, _ in
                  evidence.git_window(project["path"], weeks[-1]["start"])]
        seen = [s["when"].timestamp() for s in project["sessions"] if s["when"]]
        project["weeks"] = evidence.week_activity(stamps, seen, weeks)
    return project["weeks"]


def focus_items(projects):
    """Every unchecked to-do as (todo, project): urgent first, then recency."""
    urgent, normal = [], []
    for project in projects:  # newest-first, so each group stays in recency order
        if not project["status"]:
            continue
        for todo in project["status"]["todos"]:
            (urgent if todo["urgent"] else normal).append((todo, project))
    return urgent + normal


# ── sessions ──────────────────────────────────────────────────────────────

def parse_iso(text):
    """ISO-8601 → aware UTC datetime, or None. Tolerates 'Z' and naive stamps."""
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=timezone.utc)
    return stamp


def split_tag(title: str):
    """'ACT — Proj: purpose' → ('ACT', 'Proj: purpose'); untagged → ('NEW', title)."""
    head, sep, rest = title.partition(SESSION_SEP)
    if sep and head.strip() in SESSION_TAGS:
        return head.strip(), rest.strip()
    return "NEW", title.strip()


def read_sessions():
    """sessions.json → {generated, sessions} or None. Never raises, never fails loud."""
    try:
        raw = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("sessions"), list):
        return None
    sessions = []
    for entry in raw["sessions"]:
        if not isinstance(entry, dict):
            continue
        try:                                     # a private lane's window is not on the board
            if private_lane_of(title=str(entry.get("title") or ""), cwd=str(entry.get("cwd") or "")):
                continue
        except Exception:
            pass
        # Titles are data written elsewhere: they get escaped, never interpreted.
        tag, label = split_tag(str(entry.get("title") or ""))
        sessions.append({
            "tag": tag,
            "label": label,
            "cwd": str(entry.get("cwd") or ""),
            "when": parse_iso(entry.get("lastActivityAt")),
            "running": bool(entry.get("isRunning")),
        })
    if not sessions:
        return None
    return {"generated": parse_iso(raw.get("generated")), "sessions": sessions}


def session_project(path, roots) -> str:
    """Longest project-path prefix wins, so a worktree lands on its own project."""
    if path is None:
        return UNFILED
    for root, name in roots:  # roots arrive longest-first
        if path == root or root in path.parents:
            return name
    return UNFILED


def group_sessions(sessions, projects):
    """[(project, [sessions newest-first])] by newest session, Unfiled last."""
    roots = []
    for project in projects:
        try:
            roots.append((project["path"].resolve(), project["name"]))
        except OSError:
            continue
    try:
        # the exocortex's own folder lives outside ~/Projects on purpose;
        # claim its sessions so they don't land in Unfiled
        roots.append((Path(__file__).resolve().parent, "Exocortex"))
    except OSError:
        pass
    roots.sort(key=lambda pair: len(str(pair[0])), reverse=True)

    groups = {}
    for session in sessions:
        try:
            path = Path(session["cwd"]).resolve() if session["cwd"] else None
        except (OSError, ValueError):
            path = None
        groups.setdefault(session_project(path, roots), []).append(session)

    ordered = []
    for name, items in groups.items():
        items.sort(key=lambda s: s["when"] or EPOCH, reverse=True)
        ordered.append((name, items, items[0]["when"] or EPOCH))
    ordered.sort(key=lambda g: (g[0] == UNFILED, -g[2].timestamp()))
    return [(name, items) for name, items, _ in ordered]


# ── the getting-going guide ───────────────────────────────────────────────
# GETTING-GOING.md is the restart playbook rebuilt from live data at every
# regen (it replaces a hand-written restart playbook, which stays as the
# shape reference where it exists). The split that
# makes it trustworthy: curated judgment (openers, tiers, lane rules) comes
# from guide-cards.json and SHOWS ITS DATE; every line marked "live" was read
# from disk seconds ago and cannot be stale. The output names THIS machine's
# paths, so it is excluded from sync on purpose (see sync-manifest.json).

INBOX_DOT = re.compile(
    r"^-\s*([0-9]{4}-[0-9]{2}-[0-9]{2})[^·→]*·\s*([^·]+?)\s*·\s*(.+)$")
INBOX_ARROW = re.compile(
    r"^-\s*([0-9]{4}-[0-9]{2}-[0-9]{2})[^→]*→\s*([^:]+):\s*(.+)$")
META_PROJECT = "@orchestrator"    # guide-cards "project" value for this folder
# What INBOX lines call this folder. A folder may have been renamed and both
# names still be in use, so the registry lists every one of them and they all
# attach to the meta card.
META_MATCH = tuple(hub_folders(_reg()) or [HERE.name])


def plain_text(text: str) -> str:
    """Backticks out, whitespace collapsed — and nothing else. INBOX findings
    and Where-things-live entries name literal files (`wave_gate.py`,
    `some_handoff_documents`), so the markdown cleaner's underscore and
    asterisk stripping would mangle exactly the names that matter."""
    return " ".join(text.replace("`", "").split())


def read_inbox():
    """INBOX.md '## Waiting' lines → [{date, target, text}]. Lines that fit
    neither the `date · target · finding` nor the `date … → Target: finding`
    shape are skipped quietly — the guide is a reader, never a linter."""
    try:
        lines = INBOX_FILE.read_text(encoding="utf-8",
                                     errors="replace").splitlines()
    except OSError:
        return []
    items, waiting = [], False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("#"):
            waiting = "waiting" in stripped.lower()
            continue
        if not waiting or not stripped.startswith("-"):
            continue
        match = INBOX_DOT.match(stripped) or INBOX_ARROW.match(stripped)
        if not match:
            continue
        date, target, text = match.groups()
        items.append({"date": date, "target": " ".join(target.split()),
                      "text": plain_text(text)})
    return items


def norm_name(text: str) -> str:
    return " ".join(str(text).split()).casefold()


def inbox_for(name, inbox):
    """INBOX items whose target names this project (exact, or the target
    starts with the project name — 'some-project (and any…)' still lands)."""
    key = norm_name(name)
    out = []
    for item in inbox:
        target = norm_name(item["target"])
        if target == key or target.startswith(key + " "):
            out.append(item)
    return out


def load_guide():
    """guide-cards.json → dict; {} when absent/broken (auto-cards only)."""
    try:
        data = json.loads(GUIDE_CARDS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def machine_name() -> str:
    """This machine's name as its record writes it — the record the path
    resolver finds — or "this machine" when no record names one."""
    try:
        with record_file().open("r", encoding="utf-8") as handle:
            name = json.load(handle).get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except (OSError, ValueError, AttributeError):
        pass
    return "this machine"


# ── the session count on the machine's root of the tree ───────────────
# The hygiene watcher already owns watchers/HYGIENE-PROPOSALS-<machine>.md
# and writes its newest run entry at the top. Its FIRST line is THE COUNT
# LINE — `visible N · ceiling M · archived k · grace 2 h · claude <when>`.
# This reads that one line and nothing else: no new file, no new writer,
# and a file that has never been run says so instead of guessing.
HYGIENE_ENTRIES = 14          # the watcher keeps the last 14; we read no further
HYGIENE_COUNT_RE = re.compile(
    r"visible\s+(\d+)\s*·\s*ceiling\s+(\d+)\s*·\s*archived\s+(\d+)", re.I)
HYGIENE_ENTRY_RE = re.compile(r"^##\s+", re.M)


def hygiene_count(hub, machine):
    """The newest run entry's count line → {visible, ceiling, archived, when,
    over} for one machine, or None when the file has no count line.

    Tolerant by design: a missing file, an entry the watcher wrote before this
    build landed, a hand-edited entry, a line with extra words — each simply
    does not answer, and the caller says `no run yet`. Bounded: at most the
    first HYGIENE_ENTRIES entries are looked at, so a file that has grown past
    its trim is still cheap to read."""
    try:
        path = Path(hub) / "watchers" / f"HYGIENE-PROPOSALS-{machine}.md"
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError, TypeError):
        return None
    parts = HYGIENE_ENTRY_RE.split(text)[1:][:HYGIENE_ENTRIES]
    for entry in parts:                       # newest first, as the file is
        head, _, body = entry.partition("\n")
        when = None
        stamp = re.search(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})", head)
        if stamp:
            try:
                when = datetime.strptime(stamp.group(1).replace("T", " "),
                                         "%Y-%m-%d %H:%M")
            except ValueError:
                when = None
        for line in body.splitlines()[:40]:   # the count line is the first
            found = HYGIENE_COUNT_RE.search(line)
            if not found:
                if line.strip():
                    break                     # an entry without one: the next
                continue
            visible, ceiling, archived = (int(found.group(i)) for i in (1, 2, 3))
            return {"visible": visible, "ceiling": ceiling,
                    "archived": archived, "when": when,
                    "over": max(0, visible - ceiling)}
    return None


def hygiene_root_line(hub, machine, now=None):
    """The one string the tree draws on that machine's root — never a page, so
    the gate can ask for it without drawing anything: `sessions: 9 visible ·
    ceiling 12 · 1 h ago`, or `sessions: no run yet`."""
    got = hygiene_count(hub, machine)
    if not got:
        return "sessions: no run yet"
    line = f"sessions: {got['visible']} visible · ceiling {got['ceiling']}"
    when = got.get("when")
    if when is not None:
        hours = ((now or datetime.now()) - when).total_seconds() / 3600.0
        if hours < 1.5:
            line += " · just now" if hours < 0.5 else " · 1 h ago"
        elif hours < 48:
            line += f" · {int(round(hours))} h ago"
        else:
            line += f" · {int(round(hours / 24.0))} d ago"
    return line


def guide_next(project):
    """The live next action: first urgent unchecked to-do, else the first."""
    if not project["status"]:
        if project.get("portability"):
            return "no STATUS.md in this checkout — see the flags below"
        return "no STATUS.md in this checkout"
    todos = project["status"]["todos"]
    for todo in todos:
        if todo["urgent"]:
            return "(urgent) " + todo["text"]
    if todos:
        return todos[0]["text"]
    return "STATUS.md lists no open to-dos — add one when you leave"


def render_guide(projects, now):
    """(markdown text, {curated, auto, away}) for GETTING-GOING.md."""
    guide = load_guide()
    inbox = read_inbox()
    by_name = {p["name"]: p for p in projects}
    order = {p["name"]: i for i, p in enumerate(projects)}
    lines = []

    def emit_live(project, match_name):
        """The lines no hand-written playbook can carry: read from disk now."""
        if project is not None:
            lines.append(f"▶ NEXT (live): {guide_next(project)}")
            status = project.get("status")
            for entry in (status or {}).get("where", []):
                lines.append(f"🗺 lives: {entry}")
            flags = project.get("portability", [])
            for flag in flags[:4]:
                lines.append(f"⚠ live: {flag}")
            if len(flags) > 4:
                lines.append(f"⚠ live: +{len(flags) - 4} more on the board")
            if project.get("status_stale"):
                lines.append("⚠ live: STATUS.md is older than the newest "
                             "work — trust the repo over the file")
            stamp = project.get("evidence") or {}
            if stamp.get("ts"):
                lines.append(f"· last {stamp['kind']} {stamp['date']}")
        names = match_name if isinstance(match_name, tuple) else (match_name,)
        matched, seen = [], set()
        for name in names:
            for item in inbox_for(name, inbox):
                key = (item["date"], item["text"])
                if key not in seen:
                    seen.add(key)
                    matched.append(item)
        for item in matched[:3]:
            lines.append(f"📨 INBOX {item['date']}: "
                         f"{truncate(item['text'], 150)}")

    def emit_card(card):
        target = card.get("project", "")
        if target == META_PROJECT:
            status = read_status(HERE)
            project = {"status": status,
                       "portability": portability(HERE, status),
                       "evidence": {"ts": None}, "path": HERE}
            match_name = META_MATCH
        else:
            project = by_name.get(target)
            match_name = target
        path = project["path"] if project else "(not on this machine)"
        mark = card.get("mark")
        title = card.get("name", target)
        head = f"{mark}  ·  {title}" if mark else title
        lines.append(f"## {head}    *(curated {card.get('curated', 'undated')})*")
        tier = card.get("tier", "tier by the rule of thumb")
        note = card.get("tier_note")
        lines.append(f"📍 WHERE: `{path}` · **{tier}**"
                     + (f" — {note}" if note else ""))
        if card.get("opener"):
            lines.append(f"📋 DO: `{card['opener']}`")
        if card.get("done_when"):
            lines.append(f"✅ DONE WHEN: {card['done_when']}")
        for caution in card.get("cautions", []):
            lines.append(f"⚠ {caution}")
        emit_live(project, match_name)
        lines.append("")

    # curated cards, board order (newest evidence first; the meta card last)
    here_cards, away_cards = [], []
    for seed, card in enumerate(guide.get("cards", [])):
        if not isinstance(card, dict):
            continue
        target = card.get("project", "")
        if target == META_PROJECT or target in by_name:
            here_cards.append((order.get(target, len(order) + 1), seed, card))
        else:
            away_cards.append(card)
    here_cards = [card for _, _, card in sorted(here_cards, key=lambda t: t[:2])]

    carded = {c.get("project") for c in guide.get("cards", [])
              if isinstance(c, dict)}
    auto = [p for p in projects if p["name"] not in carded]

    stamp = "%s, %d %s" % (now.strftime("%A"), now.day,
                           now.strftime("%B %Y · %H:%M"))
    lines.append(f"# GETTING-GOING — Exocortex · {machine_name()} · {stamp}")
    lines.append("")
    lines.append("Rebuilt from live STATUS/INBOX/git data at every board "
                 "regen — lines marked *live* cannot be stale. Curated "
                 "openers show their date; if one looks old, say so to the "
                 "session you open with it.")
    lines.append("")
    for title, key in (("Morning ritual", "morning_ritual"),
                       ("House rules", "house_rules")):
        entries = guide.get(key, [])
        if entries:
            lines.append(f"## {title}")
            for i, entry in enumerate(entries, 1):
                prefix = f"{i}. " if key == "morning_ritual" else "- "
                lines.append(f"{prefix}{entry}")
            lines.append("")
    lines.append("---")
    lines.append("")
    for card in here_cards:
        emit_card(card)
    if auto:
        lines.append("## Uncarded projects — generic restart")
        lines.append("Opener for any of these: `read the project "
                     "status/memory first — report state and propose the "
                     "next action, wait for my go.` Tier by the rule of "
                     "thumb. Add a card to guide-cards.json when one earns "
                     "a real opener.")
        lines.append("")
        for project in auto:
            lines.append(f"### {project['name']}")
            lines.append(f"📍 WHERE: `{project['path']}`")
            emit_live(project, project["name"])
            lines.append("")
    if away_cards:
        lines.append("## Curated, but not on this machine")
        for card in away_cards:
            lines.append(f"- **{card.get('name', '?')}** — project folder "
                         f"`{card.get('project', '?')}` is absent here "
                         f"(curated {card.get('curated', 'undated')})")
        lines.append("")
    for tail in guide.get("tails", []):
        if not isinstance(tail, dict):
            continue
        lines.append(f"## {tail.get('label', 'Notes')}")
        for item in tail.get("items", []):
            lines.append(f"- {item}")
        lines.append("")
    rulings = unpromoted_rulings()
    if rulings:
        lines.append("## Unpromoted rulings — dossier/TAUGHT.md")
        lines.append(f"Rule-shaped journal lines dated {PROMOTION_DAY} or later "
                     f"with no promotion stamp — {PROMOTION_ASK}.")
        for ruling in rulings:
            lines.append(f"- ⚠ live: {ruling['date']} — "
                         f"{truncate(ruling['text'], 90)}")
        lines.append("")
    known = ({norm_name(p["name"]) for p in projects}
             | {norm_name(name) for name in META_MATCH})
    stray = [i for i in inbox
             if not any(norm_name(i["target"]) == k
                        or norm_name(i["target"]).startswith(k + " ")
                        for k in known)]
    if stray:
        targets = ", ".join(sorted({i["target"] for i in stray}))
        lines.append(f"📨 INBOX items for projects not on this machine: "
                     f"{len(stray)} ({targets}) — see INBOX.md")
        lines.append("")
    lines.append("*The generic card for anything unlisted: folder → tier by "
                 "the rule of thumb → `read the project status/memory "
                 "first` → let it propose → you pick → close out loud.*")
    lines.append("")
    text = "\n".join(lines)
    return text, {"curated": len(here_cards), "auto": len(auto),
                  "away": len(away_cards)}


def write_guide(projects, now):
    text, stats = render_guide(projects, now)
    with GUIDE_FILE.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return stats


# ── rendering ─────────────────────────────────────────────────────────────

def esc(text) -> str:
    return html.escape(str(text), quote=True)


def fmt_ago(timestamp: float) -> str:
    delta = datetime.now() - datetime.fromtimestamp(timestamp)
    days = delta.days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def render_ticks(project, weeks):
    """Six weeks as six small squares, oldest left — the one thing borrowed
    from the v2 waterfall, translated to print.

    Filled ink = that ISO week holds a real commit or session stamp for this
    project; outlined = it does not; the current week goes instrument amber
    when it is live. A few pixels, readable at a glance, no other claim.
    """
    cells = attach_weeks(project, weeks)             # newest week first
    boxes, legend = [], []
    for index, cell in enumerate(reversed(cells)):   # draw oldest → newest
        current = index == len(cells) - 1
        cls = ("on now" if current else "on") if cell["hits"] else ""
        boxes.append(f'<i class="{cls}"></i>' if cls else "<i></i>")
        legend.append(f'{cell["iso"]} {cell["commits"]}c {cell["sessions"]}s')
    title = "Six weeks, oldest left · " + " · ".join(legend)
    return (f'<span class="ticks" title="{esc(title)}">{"".join(boxes)}</span>')


def render_when(project, blank="no dated evidence"):
    """The evidence date, or the quiet mark for a project that has none."""
    stamp = project["evidence"]
    if not stamp["ts"]:
        return (f'<span class="mono mut when nodate" title="No git author stamp '
                f'and no session stamp — unranked">{esc(blank)}</span>')
    return (f'<span class="mono mut when" title="Newest {esc(stamp["kind"])} '
            f'stamp">{esc(stamp["date"])}</span>')


def render_open(project):
    """claude-cli://open deep link — a NEW session in that folder, carrying the
    same fixed prompt v2 uses. Console blue, underlined, no glow."""
    return (f'<a class="open" href="{esc(evidence.launch_url(project["path"]))}"'
            f' title="Start a Claude session in {esc(project["path"])}">Open ↗</a>')


def hero_stats(project, weeks):
    """One compact mono line under the hero summary: the evidence and its age,
    this week's output, the queue, the family, the live sessions. At most one
    emphasis, and only when it is earned — the laws block stays the loud one."""
    stamp = project["evidence"]
    cells = attach_weeks(project, weeks)
    todos = project["status"]["todos"] if project["status"] else []
    urgent = sum(1 for todo in todos if todo["urgent"])
    act = project["act"]
    if stamp["ts"]:
        hours = stamp["edays"] * 24
        if hours < 1:            # "0 h since last commit" reads as broken
            age = f"{max(1, round(hours * 60))} min"
        elif hours < 48:
            age = f"{hours:.0f} h"
        else:
            age = f"{stamp['edays']:.0f} d"
        first = f'{age} since last {stamp["kind"]}'
    else:
        first = "no dated evidence"
    parts = [esc(first), esc(f'{cells[0]["commits"]} commits this week'),
             esc(f"{len(todos)} open")]
    if urgent:
        parts.append(f'<span class="amber">{urgent} urgent</span>')
    parts += [esc(f'family {truncate(project["family"], 18)}'),
              esc(f'{act} ACT session{"" if act == 1 else "s"}')]
    return f'        <div class="mono mut stats">{" · ".join(parts)}</div>\n'


def row_state(project):
    """STATUS.md is the canonical signal; handoffs only speak when it is absent."""
    if project["status"]:
        if project["status_stale"]:
            return ("s-stale", "Status stale")
        return ("s-fresh", "Status fresh")
    if not project["handoff"]:
        return ("s-none", "No handoff")
    if project["stale"]:
        return ("s-stale", "Handoff stale")
    return ("s-fresh", "Handoff fresh")


def hero_badges(project):
    badges = [("b-ink", "Git")] if project["commits"] else []
    if project["status"]:
        badges.append(("b-amber", "Status stale") if project["status_stale"]
                      else ("b-blue", "Status fresh"))
    elif not project["handoff"]:
        badges.append(("b-mut", "No handoff"))
    else:
        badges.append(("b-amber", "Handoff stale") if project["stale"]
                      else ("b-blue", "Handoff fresh"))
    if project["memory"]:
        badges.append(("b-blue", "Memory"))
    return "".join(f'<span class="badge {c}">{esc(t)}</span>' for c, t in badges)


def hero_story(project):
    if project["status"] and project["status"]["now"]:
        return project["status"]["now"]
    if project["handoff"] and project["handoff"]["summary"]:
        return project["handoff"]["summary"]
    if project["commits"]:
        return "Last commit: " + project["commits"][0][1]
    # The old fallback said "folder activity only"; folder mtimes no longer
    # mean anything on this board, so it must not imply that they do.
    return "No STATUS.md, no HANDOFF.md and no commits — nothing on record."


def hero_next(project):
    todos = project["status"]["todos"] if project["status"] else []
    for todo in todos:
        if todo["urgent"]:
            return todo["text"]
    if todos:
        return todos[0]["text"]
    if project["status"] and not project["handoff"]:
        # The badge already says STATUS is fresh; asking for a HANDOFF would jar.
        return "STATUS.md lists no open to-dos — add one when you leave."
    if project["handoff"]:
        if project["handoff"]["next"]:
            return project["handoff"]["next"]
        # Saying "write a HANDOFF" would contradict the badge above it.
        return "HANDOFF.md records no next step — add one when you leave."
    return "Write a HANDOFF.md next time you leave this project."


NO_HERO = """    <div class="hero">
      <div class="eyebrow blue">Nothing dated</div>
      <h2>No project to pick up</h2>
      <p>No project carries a git author stamp or a Claude session stamp, so
      none of them can be ranked. Nothing was substituted from a file mtime.</p>
    </div>
    <div class="laws">
      <div class="eyebrow" style="opacity:.85">Next</div>
      <h2>Commit something, or refresh sessions.json.</h2>
    </div>
"""


def render_hero(project, weeks):
    if project is None:
        return NO_HERO
    commits = ""
    if project["commits"]:
        rows = "".join(
            f'<div class="commit"><span class="mono">{esc(date)}</span>'
            f'<span>{esc(subject)}</span></div>'
            for date, subject in project["commits"]
        )
        commits = (
            '<div class="commits"><div class="eyebrow mut">Recent commits</div>'
            f"{rows}</div>"
        )
    keys = ""
    if project["status"] and project["status"]["important"]:
        items = "".join(
            f"<li>{esc(item)}</li>" for item in project["status"]["important"][:3]
        )
        keys = (
            '<div class="story"><div class="eyebrow mut">Important</div>'
            f"<ul>{items}</ul></div>"
        )
    stamp = project["evidence"]
    return f"""    <div class="hero">
      <div class="eyebrow blue">Most recent · {esc(fmt_ago(stamp['ts']))}</div>
      <h2>{esc(project['name'])}</h2>
      <div class="heroline">
        <span class="mono mut">Last {esc(stamp['kind'])} {esc(stamp['date'])}</span>
        {render_ticks(project, weeks)}
        {render_open(project)}
      </div>
      <div class="badges">{hero_badges(project)}</div>
      <div class="story">
        <div class="eyebrow mut">You were doing</div>
        <p>{esc(hero_story(project))}</p>
{hero_stats(project, weeks)}      </div>
{keys}{commits}    </div>
    <div class="laws">
      <div class="eyebrow" style="opacity:.85">Next</div>
      <h2>{esc(hero_next(project))}</h2>
    </div>
"""


def render_row(project, weeks=None, variants=0):
    """One project line. `weeks` draws the six-week ticks — passed for the
    active rows, withheld in Everything else so the reveal stays quiet (and so
    the per-row git call stays off the long tail)."""
    cls, label = row_state(project)
    extra = (
        f'<span class="variants">+{variants} variants</span>' if variants else ""
    )
    ticks = render_ticks(project, weeks) if weeks else ""
    return f"""      <div class="row">
        <span class="nm">{esc(project['name'])}</span>{extra}{ticks}
        {render_when(project)}
        <span class="stat {cls}">{esc(label)}</span>
        {render_open(project)}
      </div>
"""


def render_focus_row(index, todo, project):
    # Urgent items take over the number column with a red "!" — same slot, same size.
    # ".mark" is the masthead logo — the number column is ".step".
    mark = "!" if todo["urgent"] else f"{index:02d}"
    cls = "step urgent" if todo["urgent"] else "step"
    return f"""      <div class="row">
        <span class="{cls}">{mark}</span>
        <span class="task">{esc(todo['text'])}</span>
        <span class="eyebrow mut proj">{esc(project['name'])}</span>
        {render_when(project, blank="—")}
      </div>
"""


def render_focus(items):
    if not items:
        return (
            '    <div class="rows">\n'
            '      <div class="row"><span class="task mut">Nothing queued — add a '
            "STATUS.md with a To do list to any project and it lands here."
            "</span></div>\n    </div>\n"
        )
    shown = items[:FOCUS_ROWS]
    rows = "".join(
        render_focus_row(i, todo, project)
        for i, (todo, project) in enumerate(shown, 1)
    )
    more = ""
    if len(items) > len(shown):
        more = ('      <div class="row"><span class="eyebrow mut">'
                f'+{len(items) - len(shown)} more</span></div>\n')
    return f'    <div class="rows">\n{rows}{more}    </div>\n'


def fmt_age(when, now) -> str:
    """Age against build time: '14m' / '3h' / '2d'; '—' when the stamp is junk."""
    if when is None:
        return "—"
    seconds = max((now - when).total_seconds(), 0)
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < DAY:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // DAY)}d"


def render_session_row(session, now):
    chip = "c-act" if session["tag"] == "ACT" else "c-new"
    dot = '<span class="live"></span>' if session["running"] else ""
    label = session["label"] or "Untitled session"
    return f"""          <div class="row">
            <span class="chip {chip}">{esc(session['tag'])}</span>
            <span class="task">{dot}{esc(label)}</span>
            <span class="mono mut age">{esc(fmt_age(session['when'], now))}</span>
          </div>
"""


def render_session_rest(items):
    """One quiet line for the dormant tags — silent when a tag has no members."""
    counts = {}
    for session in items:
        counts[session["tag"]] = counts.get(session["tag"], 0) + 1
    parts = [f"· {counts[tag]} {tag} {phrase}"
             for tag, phrase in SESSION_REST if counts.get(tag)]
    if not parts:
        return ""
    return ('          <div class="row rest"><span class="mono mut">'
            f'{esc(" ".join(parts))}</span></div>\n')


def render_session_group(name, items, now):
    rows = "".join(render_session_row(session, now) for session in items
                   if session["tag"] in SESSION_LIVE)
    rest = render_session_rest(items)
    if not rows and not rest:
        return ""
    return (
        '      <div class="fam">\n'
        f'        <div class="famhead"><span class="eyebrow">{esc(name)}</span>'
        f'<span class="mono mut">×{len(items)}</span></div>\n'
        f'        <div class="rows">\n{rows}{rest}        </div>\n'
        "      </div>\n"
    )


def session_eyebrow(generated, now) -> str:
    stamp = generated.astimezone().strftime("%Y-%m-%d %H:%M") if generated else "unknown"
    text = esc(f"Snapshot {stamp} · Refresh via orchestrator session")
    if generated and (now - generated).total_seconds() > DAY:
        text += ' · <span class="amber">Stale</span>'
    return text


def render_sessions(snapshot, projects, number, now):
    """The whole section, or "" when there is no usable snapshot to show."""
    if not snapshot:
        return ""
    blocks = "".join(
        render_session_group(name, items, now)
        for name, items in group_sessions(snapshot["sessions"], projects)
    )
    if not blocks:
        return ""
    return f"""
  <section>
    <div class="rulehead"><span class="bignum">{number}</span><h2>Sessions</h2>
    <span class="eyebrow mut">Where to jump in</span></div>
    <div class="eyebrow mut snapline">{session_eyebrow(snapshot['generated'], now)}</div>
    <div class="sessions">
{blocks}    </div>
  </section>
"""


def codex_install_check():
    """INSTALL Surface 0 as machinery: a reminder the exocortex gives when the
    user installs it. A Codex install on
    this machine that cannot yet pull or push the brain shows in Portability
    until it is fixed: its sandbox needs the sync folder and the hub folder as
    writable roots and network on, and its global AGENTS.md must carry the
    exocortex rules (delivered by sync once machine.json has a codex root).
    Says nothing on a machine without Codex. Textual checks, never raises.

    The folders it checks are where the path resolver finds them: the older
    layout's one folder that holds both the sync package and the brain (the
    "sync folder"); in a program tree the hub (its sync package is inside it)
    and the brain clone, wherever the record puts it."""
    codex = Path.home() / ".codex"
    if not codex.is_dir():
        return []
    warns = []
    record = hub_paths()
    engine, brain = record["sync_dir"], record["brain"]
    older_layout = record["layout"] != "program-tree"
    hub = str(HERE)
    places = []
    if older_layout:
        if (engine or brain) is not None:
            places.append(("sync folder", str(engine or brain)))
    elif engine is not None and not _inside(engine, HERE):
        places.append(("sync folder", str(engine)))
    places.append(("hub folder", hub))
    if not older_layout and brain is not None and not _inside(brain, HERE):
        places.append(("brain folder", str(brain)))
    try:
        cfg = codex / "config.toml"
        text = cfg.read_text(encoding="utf-8") if cfg.exists() else ""
    except OSError:
        text = ""
    sect = re.search(r"^\[sandbox_workspace_write\]\s*$(.*?)(?=^\[|\Z)",
                     text, re.M | re.S)
    if not sect:
        warns.append("config.toml has no [sandbox_workspace_write] — "
                     "Codex cannot pull/push the brain (INSTALL Surface 0)")
    else:
        body = sect.group(1)
        # network_access is NOT required: the brain sync runs outside the
        # sandbox by the allow rule (network stays off).
        roots = re.search(r"^\s*writable_roots\s*=\s*\[(.*?)\]", body,
                          re.M | re.S)
        roots_txt = roots.group(1) if roots else ""
        for label, path in places:
            if path not in roots_txt:
                warns.append(f"{label} not in sandbox writable_roots "
                             "(INSTALL Surface 0)")
        # Codex keeps memory like Claude — every project
        # memory folder must be a writable root (new folders appear when a
        # Claude session writes a project's first memory).
        try:
            mem_dirs = sorted(d for d in (Path.home() / ".claude" / "projects").glob("*/memory") if d.is_dir())
        except OSError:
            mem_dirs = []
        missing = [d for d in mem_dirs if str(d) not in roots_txt]
        if missing:
            warns.append(f"{len(missing)} project memory folder(s) not in Codex's "
                         f"writable_roots — Codex cannot write memory there "
                         f"(first: {missing[0].parent.name}; INSTALL Surface 0)")
    try:
        rules = codex / "rules" / "exocortex.rules"
        rtext = rules.read_text(encoding="utf-8") if rules.exists() else ""
    except OSError:
        rtext = ""
    # The allow rule must name THIS machine's sync package — the engine the
    # resolver finds, by its full path or its home-relative form — and its entry
    # point. On the older layout the fleet's rules were written with the older
    # folder's name, and that still counts there.
    names_engine = engine is not None and _mentions(rtext, Path(engine) / "sync.py")
    names_older = older_layout and LEGACY_SYNC_DIRNAME in rtext
    if not (names_engine or names_older) or "sync.py" not in rtext:
        warns.append("no allow rule for the brain sync in ~/.codex/rules/"
                     "exocortex.rules — Codex keeps .git read-only in its "
                     "sandbox, so pull/push fail (INSTALL Surface 0)")
    try:
        agents = codex / "AGENTS.md"
        atext = agents.read_text(encoding="utf-8") if agents.exists() else ""
    except OSError:
        atext = ""
    if "Exocortex" not in atext:
        warns.append("~/.codex/AGENTS.md lacks the exocortex rules — add "
                     "roots.codex to machine.json, then sync pull "
                     "(INSTALL Surface 0)")
    return warns


def _inside(path, folder) -> bool:
    """Is `path` the folder itself or somewhere under it?"""
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except (ValueError, OSError):
        return False


def _mentions(text, path) -> bool:
    """Does a rules file name this path — as written, with forward slashes, with
    the doubled backslashes a quoted Windows string carries, or home-relative
    (~/...)? A textual check, like every check in codex_install_check."""
    raw = str(path)
    forms = {raw, raw.replace("\\", "/"), raw.replace("\\", "\\\\")}
    try:
        rel = Path(path).resolve().relative_to(Path.home().resolve())
        forms.add("~/" + rel.as_posix())
    except (ValueError, OSError):
        pass
    return any(form and form in text for form in forms)


def render_portability(projects, number):
    """The whole section, or "" when every artifact is reachable. Amber row
    per flagged project — a warning about reachability, never an error."""
    flagged = [p for p in projects if p["portability"]]
    if not flagged:
        return ""
    rows = ""
    for project in flagged:
        shown = project["portability"][:4]
        hidden = len(project["portability"]) - len(shown)
        text = " · ".join(shown) + (f" · +{hidden} more" if hidden else "")
        rows += f"""      <div class="row">
        <span class="nm">{esc(project['name'])}</span>
        <span class="task amber">{esc(text)}</span>
        {render_open(project)}
      </div>
"""
    return f"""
  <section>
    <div class="rulehead"><span class="bignum">{number}</span><h2>Portability</h2>
    <span class="eyebrow mut">What this checkout can't see</span></div>
    <div class="eyebrow mut snapline">Nothing is lost — these artifacts exist,
    just not where this machine is looking. Declared locations
    ("Where things live" in STATUS.md) are never flagged.</div>
    <div class="rows">
{rows}    </div>
  </section>
"""


def render_unpromoted(rulings, number):
    """The whole section, or "" when every recent ruling names where it went.
    Amber row per unstamped line — an open question, never an error."""
    if not rulings:
        return ""
    rows = ""
    for ruling in rulings:
        rows += f"""      <div class="row">
        <span class="nm">{esc(ruling['date'])}</span>
        <span class="task amber">{esc(truncate(ruling['text'], 90))}</span>
        <span class="eyebrow mut proj">{esc(PROMOTION_ASK)}</span>
      </div>
"""
    return f"""
  <section>
    <div class="rulehead"><span class="bignum">{number}</span><h2>Unpromoted rulings</h2>
    <span class="eyebrow mut">Rules still only in the journal</span></div>
    <div class="eyebrow mut snapline">TAUGHT.md lines dated {PROMOTION_DAY} or
    later that read as rules but carry no promotion stamp. Nothing is wrong —
    they simply have not been ruled on yet.</div>
    <div class="rows">
{rows}    </div>
  </section>
"""


def render_active(families, weeks):
    rows = "".join(
        render_row(members[0], weeks, len(members) - 1) for _, members in families
    )
    if not rows:
        return ('    <div class="rows">\n      <div class="row"><span class="task '
                'mut">Only one project carries dated evidence — everything else '
                'is below.</span></div>\n    </div>\n')
    return f'    <div class="rows">\n{rows}    </div>\n'


def render_family(label, members):
    rows = "".join(render_row(member) for member in members)
    return (
        '      <div class="fam">\n'
        f'        <div class="famhead"><span class="eyebrow">{esc(label)}</span>'
        f'<span class="mono mut">×{len(members)}</span></div>\n'
        f'        <div class="rows">\n{rows}        </div>\n'
        "      </div>\n"
    )


def render_all(families, hidden_count):
    # One-project families would just repeat their own name as a heading,
    # so they share a single "one-offs" block at the end.
    blocks, singles = [], []
    for name, members in families:
        if len(members) == 1:
            singles.append(members[0])
        else:
            blocks.append(render_family(name, members))
    if singles:
        blocks.append(render_family("One-off projects", singles))
    return (
        '    <details>\n'
        f'      <summary><span class="eyebrow">All projects · '
        f'{hidden_count} more</span></summary>\n'
        f'      <div class="allbody">\n{"".join(blocks)}      </div>\n'
        "    </details>\n"
    )


# ── 00 tree ────────────────────────────────────────────────────────────
# tools/collect-openers.py is the ONE place that reads a lane's OPENER file,
# checks it against the repo it claims, and ranks the lanes. This board renders
# what that tool returns and computes none of it again: two readers of one rule
# drift, and the tree screen is the thing read at a machine switch.

COLLECTOR = HERE / "tools" / "collect-openers.py"
WAKE_SCREEN = HERE / "tools" / "wake-screen.py"
PROGRAM_NAME = "Exocortex"          # the program's own name, for what it draws
DOT_CLASS = {"green": "d-green", "amber": "d-amber", "red": "d-red"}


def front_door(tree_path):
    """The WAKE SCREEN's dated strip at the top of the page just drawn — the same
    block the hub's first reply prints (tools/wake-screen.py --inject). Never raises: a page
    without its strip is still the whole tree."""
    try:
        if tree_path is not None and WAKE_SCREEN.is_file():
            import subprocess
            subprocess.run([sys.executable, str(WAKE_SCREEN), "--inject", str(tree_path)],
                           capture_output=True, text=True, timeout=20)
    except Exception:
        pass


def load_collector():
    """tools/collect-openers.py as a module, or None. Never raises: a board
    that cannot collect openers still prints every other section."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("collect_openers",
                                                      str(COLLECTOR))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        saved = sys.dont_write_bytecode
        sys.dont_write_bytecode = True      # no __pycache__ in the hub folder
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = saved
        return module
    except Exception:                       # a broken tool is a missing section
        return None


def write_improvements():
    """Hook A: the improvements ledger rides every board run, so the page
    that opens is never older than the board. It runs in its own process and
    never fails this run — one plain line is all a failure costs."""
    import subprocess
    try:
        done = subprocess.run([sys.executable, str(HERE / "tools" / "improvements.py"),
                               "--write", "--hub", str(HERE)],
                              capture_output=True, text=True, timeout=120)
        out = (done.stdout or "").strip().splitlines()
        if done.returncode == 0:
            print(out[-1] if out else "Improvements: written.")
            return
        why = ((done.stderr or "").strip().splitlines() or out or
               ["exit %d" % done.returncode])[-1]
    except Exception as exc:                # a missing or broken tool is one line
        why = "%s: %s" % (type(exc).__name__, exc)
    print("Improvements: not written (%s) - improvements.html is unchanged." % why)


def tree_data():
    """The collector's ranked rows and flags, or None when it cannot run."""
    module = load_collector()
    if module is None:
        return None
    try:
        return module.collect()
    except Exception:
        return None


def tree_flags(flags):
    """The one red line under the section head: stale openers and silent lanes,
    and an install letter that names a scratch/ path."""
    parts = []
    letters = flags.get("scratch_install") or []
    if letters:
        parts.append("%d install letter(s) name a scratch/ path, which never crosses "
                     "the brain — first: INBOX.md:%d, %s"
                     % (len(letters), letters[0]["lineno"], esc(letters[0]["path"])))
    if flags.get("stale"):
        parts.append("stale openers: " + esc(", ".join(flags["stale"])))
    silent = flags.get("no_opener") or []
    if silent:
        shown = ", ".join(silent[:4])
        if len(silent) > 4:
            shown += f", +{len(silent) - 4} more"
        parts.append(f"{len(silent)} active lane(s) wrote no opener: "
                     + esc(shown))
    if not parts:
        return ('    <div class="eyebrow mut snapline">Every active lane left '
                'an opener, and every opener matches the repo it claims.</div>\n')
    return f'    <div class="eyebrow flags">{" · ".join(parts)}</div>\n'


def render_tree_card(row, slot):
    """The whole card: where you are, next actions, and the opener itself."""
    card = row["card"]
    where = card["where"] if card["where"] != "—" else ""
    story = " — ".join([part for part in (where, card["now"]) if part])
    actions = "".join(
        f'<li>{"! " if item["urgent"] else ""}{esc(item["text"])}</li>'
        for item in card["actions"]
    ) or f'<li>{esc(card["fallback"])}</li>'
    warns = "".join(f'<div class="warn">⚠ {esc(note)}</div>'
                    for note in card["notes"])
    if card["handed"]:
        opener = (
            f'      <div class="eyebrow mut">📍 Where: {esc(card["open_in"])} · '
            f'{esc(card["model"])}</div>\n'
            f'      <div class="eyebrow mut">📋 Do — paste this:</div>\n'
            f'      <pre class="mono" id="{esc(slot)}">{esc(card["body"])}</pre>\n'
            f'      <button class="copy" type="button" data-for="{esc(slot)}">'
            'Copy opener</button>\n'
            f'      <div class="eyebrow mut done">✅ Done when: '
            f'{esc(card["done_when"])}</div>\n'
        )
    else:
        opener = (f'      <div class="eyebrow mut">📋 Open with:</div>\n'
                  f'      <pre class="mono" id="{esc(slot)}">'
                  f'{esc(card["fallback"])}</pre>\n'
                  f'      <button class="copy" type="button" '
                  f'data-for="{esc(slot)}">Copy opener</button>\n')
    return f"""      <div class="card">
        <dl>
          <dt>Where you are</dt><dd>{esc(story or "nothing recorded")}</dd>
          <dt>Next actions</dt><dd><ul>{actions}</ul></dd>
          <dt>Continues on</dt><dd>{esc(card["continues_on"])}</dd>
          <dt>Lives at</dt><dd><span class="mono">{esc(card["lives_at"])}</span>
            — {esc(card["carrier"])}</dd>
          <dt>Last recorded</dt><dd class="mono">{esc(card["last_recorded"])}</dd>
          <dt>Depends on</dt><dd>{esc(card["depends_on"])}</dd>
          <dt>State</dt><dd>{esc(row["state"])} — {esc(row["state_words"] or "clean")}</dd>
        </dl>
{warns}{opener}      </div>
"""


def render_tree_row(row, index):
    """One ranked lane: dot, name, state words + next move, touched, gate."""
    slot = f"op{index:02d}"
    gate = '<span class="gate" title="Gated">🔒</span>' if row["gated"] else ""
    dot = DOT_CLASS.get(row["state"], "d-amber")
    # Same words as the chat form: where it stands, then the one move. The
    # colour's reason lives in the card.
    line = f'{row["where"]} — next: {row["next_move"]}'
    return f"""      <details>
        <summary class="row">
          <span class="dot {dot}" title="{esc(row["state"])}"></span>
          <span class="nm">{esc(row["lane"])}</span>{gate}
          <span class="task">{esc(line)}</span>
          <span class="mono mut when">{esc(row["touched_day"])}</span>
        </summary>
{render_tree_card(row, slot)}      </details>
"""


def render_tree_paused(rows):
    """The lanes nothing has touched in a fortnight, named but out of the way."""
    if not rows:
        return ""
    items = "".join(
        f'      <div class="row"><span class="nm">{esc(row["lane"])}</span>'
        f'<span class="mono mut when">{esc(row["touched_day"])}</span></div>\n'
        for row in rows
    )
    return (
        '    <details class="paused">\n'
        f'      <summary><span class="eyebrow">Paused · {len(rows)} lanes '
        'untouched for a fortnight</span></summary>\n'
        f'      <div class="rows">\n{items}      </div>\n'
        '    </details>\n'
    )


def render_tree(data):
    """Section 00 — the ranked landing list. Always present, even when the
    collector cannot run: a silent section would read as "nothing to pick up"."""
    head = ('  <section>\n'
            '    <div class="rulehead"><span class="bignum">00</span>'
            '<h2>Tree</h2>\n'
            '<a class="eyebrow mut" href="tree.html" style="margin-left:auto;text-decoration:none">open the styled page →</a>\n'
            '    <span class="eyebrow mut">Start here on this machine</span>'
            '</div>\n')
    if not data:
        return (head + '    <div class="eyebrow flags">tools/collect-openers.py '
                'could not be run — no opener was collected. Every other '
                'section is unaffected.</div>\n  </section>\n')
    active = [row for row in data["rows"] if row["active"]]
    paused = [row for row in data["rows"] if not row["active"]]
    if active:
        rows = "".join(render_tree_row(row, i)
                       for i, row in enumerate(active, 1))
        body = f'    <div class="rows pick">\n{rows}    </div>\n'
    else:
        body = ('    <div class="rows"><div class="row"><span class="task mut">'
                'No active lane — every project has been quiet for a '
                'fortnight.</span></div></div>\n')
    return (head + tree_flags(data["flags"]) + body
            + render_tree_paused(paused) + '  </section>\n')


SCRIPT = """<script>
document.addEventListener("click", function (event) {
  var target = event.target;
  if (!target || !target.closest) { return; }
  var button = target.closest(".copy");
  if (!button) { return; }
  var pre = document.getElementById(button.getAttribute("data-for"));
  if (!pre) { return; }
  var label = button.getAttribute("data-label") || button.textContent;
  button.setAttribute("data-label", label);
  var said = function (word) {
    button.textContent = word;
    window.setTimeout(function () { button.textContent = label; }, 1400);
  };
  var select = function () {
    var range = document.createRange();
    range.selectNodeContents(pre);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    said("Selected — press copy");
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(pre.textContent).then(function () {
      said("Copied");
    }, select);
  } else {
    select();
  }
});
</script>
"""


CSS = """  :root{
    --paper:#F2F1EC; --card:#FFFFFF; --ink:#101012; --red:#D0021B;
    --blue:#2456A4; --amber:#E8930C; --green:#1E7A3C; --mut:#85847E;
    --rule:#101012;
    --hair:rgba(16,16,18,.18);
    --disp:Futura,"Avenir Next","Century Gothic","Trebuchet MS",sans-serif;
    --mono:Menlo,Consolas,"Liberation Mono",monospace;
  }
  html{background:var(--paper);}
  body{margin:0; background:var(--paper); color:var(--ink); font-size:16px; line-height:1.55;
    font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased;}
  .wrap{max-width:880px; margin:0 auto; padding:0 28px 96px;}
  h1,h2,h3{font-family:var(--disp); font-weight:700; letter-spacing:-.01em;}
  h1{font-size:clamp(42px,9vw,84px); line-height:.95; margin:0;}
  h2{font-size:clamp(25px,4vw,36px); line-height:1.06; margin:0;} p{margin:.5em 0; max-width:62ch;}
  .eyebrow{font-family:var(--disp); font-weight:700; font-size:12px; text-transform:uppercase;
    letter-spacing:.18em;} .mut{color:var(--mut);} .blue{color:var(--blue);}
  .amber{color:var(--amber);}
  .mono{font-family:var(--mono); font-size:13px; font-variant-numeric:tabular-nums;}

  .cover{padding:60px 0 30px; border-bottom:6px solid var(--rule);}
  .mark{display:block; margin-bottom:34px;}
  .cover .eyebrow{color:var(--red);} .cover h1{margin-top:14px;}
  .cover .sub{font-size:19px; margin-top:18px;}

  section{padding:44px 0 8px;}
  .rulehead{display:flex; align-items:baseline; gap:16px; margin-bottom:24px;
    border-bottom:6px solid var(--rule); padding-bottom:10px;}
  .rulehead h2{text-transform:uppercase; letter-spacing:.08em;}
  .bignum{font-family:var(--disp); font-weight:700; line-height:1; color:var(--red);
    font-size:clamp(38px,6vw,62px);}

  .hero{background:var(--card); border:3px solid var(--rule); padding:26px 28px 24px;}
  .hero h2{font-size:clamp(30px,5.6vw,48px); margin:10px 0 6px;}
  .heroline{display:flex; align-items:center; gap:8px 16px; flex-wrap:wrap; margin-top:4px;}
  .heroline .open{margin-left:auto;} .badges{margin-top:16px;}
  .stats{display:block; margin-top:12px; font-size:12.5px;}

  /* six-week ticks: one square per ISO week, oldest left. Filled = that week
     holds a real commit or session; the current week goes amber when live. */
  .ticks{display:inline-flex; gap:3px; flex:0 0 auto; align-self:center;}
  .ticks i{width:9px; height:9px; border:2px solid rgba(16,16,18,.26);}
  .ticks i.on{background:var(--ink); border-color:var(--ink);}
  .ticks i.now{background:var(--amber); border-color:var(--amber);}

  /* claude-cli://open deep link. Console blue, print-flat, never loud. */
  .open{font-family:var(--disp); font-weight:700; font-size:11.5px; letter-spacing:.14em;
    text-transform:uppercase; color:var(--blue); text-decoration:none; flex:0 0 auto;
    white-space:nowrap; border-bottom:2px solid var(--blue); align-self:center;}
  .open:hover{background:var(--blue); color:#fff;}
  .hero .open{border:2px solid var(--blue); padding:3px 9px;}
  .badge{display:inline-block; font-family:var(--disp); font-weight:700; font-size:11.5px;
    letter-spacing:.14em; text-transform:uppercase; padding:4px 10px; margin:0 6px 6px 0; color:#fff;}
  .b-blue{background:var(--blue);} .b-amber{background:var(--amber); color:var(--ink);}
  .b-ink{background:var(--ink);} .b-mut{background:var(--mut);}
  .story,.commits{margin-top:18px; border-top:2px solid var(--hair); padding-top:14px;}
  .story p{margin-top:6px;}
  .story ul{margin:6px 0 0; padding-left:20px;} .story li{margin:3px 0; max-width:62ch;}
  .commit{display:flex; flex-wrap:wrap; gap:6px 14px; padding:4px 0; font-size:14.5px;}
  .commit .mono{color:var(--mut); flex:0 0 auto;}

  .laws{background:var(--red); color:#fff; padding:28px 30px; margin-top:14px;}
  .laws h2{color:#fff; margin-top:10px;}

  .rows{background:var(--card); border:3px solid var(--rule); padding:2px 20px;}
  .row{display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 16px; padding:15px 0;
    border-bottom:2px solid var(--hair);}
  .row:last-child{border-bottom:none;}
  .row .nm{font-family:var(--disp); font-weight:700; font-size:19px; flex:1 1 240px;}
  .variants,.stat{font-family:var(--disp); font-weight:700; font-size:11.5px;
    letter-spacing:.14em; text-transform:uppercase; flex:0 0 auto;}
  .variants{color:var(--mut);} .stat{min-width:104px;}
  .s-fresh{color:var(--blue);} .s-stale{color:var(--amber);} .s-none{color:var(--mut);}
  .when{flex:0 0 auto; min-width:88px;} .nodate{font-size:12px; min-width:0;}

  .step{font-family:var(--disp); font-weight:700; font-size:19px; color:var(--mut);
    flex:0 0 26px; font-variant-numeric:tabular-nums;}
  .step.urgent{color:var(--red);}
  .task{flex:1 1 300px;} .row .proj{flex:0 0 auto;}

  .snapline{display:block; margin:-8px 0 18px;}
  .chip{font-family:var(--disp); font-weight:700; font-size:11.5px; letter-spacing:.14em;
    text-transform:uppercase; flex:0 0 auto; min-width:48px; text-align:center; padding:3px 9px;}
  .c-act{background:var(--blue); color:#fff;}
  .c-new{background:var(--card); color:var(--ink); border:2px solid var(--ink); padding:1px 7px;}
  .live{display:inline-block; width:8px; height:8px; border-radius:50%;
    background:var(--red); margin-right:9px; vertical-align:middle;}
  .age{flex:0 0 auto; min-width:38px; text-align:right;}
  .sessions .fam:last-child{margin-bottom:0;}

  details{border-top:2px solid var(--hair);} .allbody{padding-bottom:8px;}
  summary{cursor:pointer; padding:16px 0; color:var(--mut); list-style:none;}
  summary::-webkit-details-marker{display:none;}
  summary::before{content:"+ "; color:var(--red);} summary:hover{color:var(--ink);}
  details[open] summary::before{content:"− ";}
  .fam{margin-bottom:20px;}
  .famhead{display:flex; align-items:baseline; gap:12px; padding-bottom:8px;
    border-bottom:3px solid var(--rule);}
  .famhead .eyebrow{letter-spacing:.22em;} .fam .rows{border-top:none;}

  /* 00 TREE: one ranked row per lane, click it for the whole card and the
     opener itself. Same rows, same rules, same palette as every section above
     — the only new ink is the green dot, and the dot is the whole signal. */
  .flags{display:block; margin:-8px 0 18px; color:var(--red);}
  .pick details{border-top:none; border-bottom:2px solid var(--hair);}
  .pick details:last-child{border-bottom:none;}
  .pick summary{padding:15px 0; color:var(--ink); list-style:none;}
  .pick summary::before{flex:0 0 auto; align-self:center;}
  .pick summary.row{border-bottom:none;}
  .pick summary:hover .nm{color:var(--red);}
  .dot{display:inline-block; width:11px; height:11px; border-radius:50%;
    flex:0 0 auto; align-self:center;}
  .d-green{background:var(--green);} .d-amber{background:var(--amber);}
  .d-red{background:var(--red);}
  .pick .nm{flex:0 1 auto;} .gate{flex:0 0 auto; align-self:center;}
  .card{padding:0 0 20px 26px;}
  .card dl{margin:0;}
  .card dt{font-family:var(--disp); font-weight:700; font-size:11.5px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--mut);
    margin-top:12px;}
  .card dd{margin:2px 0 0; max-width:62ch;}
  .card ul{margin:2px 0 0; padding-left:20px;} .card li{margin:3px 0;}
  .card .warn{color:var(--amber); margin-top:12px; max-width:62ch;}
  .card .eyebrow{display:block; margin-top:14px;}
  .card .done{margin-top:10px;}
  .card pre.mono{background:var(--paper); border:2px solid var(--hair);
    padding:12px 14px; margin:6px 0 0; overflow-x:auto; white-space:pre-wrap;
    word-break:break-word; line-height:1.5;}
  .copy{font-family:var(--disp); font-weight:700; font-size:11.5px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--blue);
    background:none; border:2px solid var(--blue); padding:3px 9px;
    margin-top:10px; cursor:pointer;}
  .copy:hover{background:var(--blue); color:#fff;}
  .paused .rows{border-top:none;}

  .note{display:block; margin:44px 0 0; font-size:12px;}
  .foot{margin-top:14px; border-top:6px solid var(--rule); padding-top:18px; display:flex;
    justify-content:space-between; gap:20px; flex-wrap:wrap;} .foot .eyebrow{color:var(--mut);}

  @media (max-width:560px){
    .wrap{padding:0 18px 72px;}
    .row{flex-direction:column; gap:4px;} .row .nm{flex:1 1 auto;}
    .row .open,.heroline .open,.ticks{margin-left:0; align-self:flex-start;}
    .stats{font-size:12px;}
    .hero{padding:20px 18px;} .laws{padding:22px 18px;} .rows{padding:2px 14px;}
  }
"""

MARK = """  <svg class="mark" width="136" height="56" viewBox="0 0 136 56" role="img"
       aria-label="Exocortex mark: monolith and eye">
    <rect x="0" y="0" width="22" height="56" fill="var(--ink)"/>
    <circle cx="66" cy="28" r="16" fill="var(--ink)"/>
    <circle cx="66" cy="28" r="7" fill="var(--red)"/>
    <rect x="102" y="26" width="34" height="4" fill="var(--blue)"/>
  </svg>
"""


def render(projects, snapshot=None, tree=None):
    now = datetime.now()
    # no %-d: that strftime extension is macOS/Linux-only and crashes on Windows
    stamp = "%s, %d %s" % (now.strftime("%A"), now.day,
                           now.strftime("%B %Y · %H:%M"))
    weeks = evidence.week_windows(now)
    # Only projects with dated evidence can be ranked, so only they can be the
    # hero or take an Active row. The undated ones are still all listed and
    # counted below, marked for what they are.
    dated = [project for project in projects if project["evidence"]["ts"]]
    hero = dated[0] if dated else None
    families = group_families(projects, EVIDENCE_KEY)
    active = [family for family in group_families(dated, EVIDENCE_KEY)
              if hero is None or family[0] != hero["family"]][:5]
    hidden = max(len(projects) - (1 if hero else 0) - len(active), 0)
    fam_count = len(families)
    focus = focus_items(projects)
    # PORTABILITY, UNPROMOTED RULINGS and SESSIONS are optional; when one is
    # absent the run closes
    # up again so the numbering never shows a gap. Numbers are handed out in
    # page order: hero 01, focus 02, then whoever shows up.
    number = 2

    def next_number():
        nonlocal number
        number += 1
        return f"{number:02d}"

    codex_warns = codex_install_check()
    if codex_warns:
        print("Codex on this machine: " + " · ".join(codex_warns))
    port_rows = list(projects) + ([{"name": "Codex on this machine",
                                    "portability": codex_warns, "path": HERE}]
                                  if codex_warns else [])
    port = render_portability(port_rows, next_number())
    if not port:
        number -= 1
    unpromoted = render_unpromoted(unpromoted_rulings(), next_number())
    if not unpromoted:
        number -= 1
    sessions = render_sessions(snapshot, projects, next_number(),
                               datetime.now(timezone.utc))
    if not sessions:
        number -= 1
    n_active, n_all = next_number(), next_number()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Exocortex Board</title>
<style>
{CSS}</style>
</head>
<body>
<div class="wrap">

  <header class="cover">
{MARK}    <div class="eyebrow">Exocortex · {esc(stamp)}</div>
    <h1>Project<br>Board</h1>
    <p class="sub">{len(projects)} projects · {fam_count} families ·
    one place to pick the thread back up.</p>
  </header>

{render_tree(tree)}
  <section>
    <div class="rulehead"><span class="bignum">01</span><h2>Where you left off</h2></div>
{render_hero(hero, weeks)}  </section>

  <section>
    <div class="rulehead"><span class="bignum">02</span><h2>Focus</h2>
    <span class="eyebrow mut">What needs doing</span></div>
{render_focus(focus)}  </section>
{port}{unpromoted}{sessions}
  <section>
    <div class="rulehead"><span class="bignum">{n_active}</span><h2>Active</h2></div>
{render_active(active, weeks)}  </section>

  <section>
    <div class="rulehead"><span class="bignum">{n_all}</span><h2>Everything else</h2></div>
{render_all(families, hidden)}  </section>

  <span class="mono mut note">Ranked by newest git author stamp or session
  stamp — never by file mtimes. {len(dated)} of {len(projects)} projects are dated.</span>
  <div class="foot">
    <span class="eyebrow">Generated from ~/Projects · no manual entry</span>
    <span class="eyebrow">{esc(now.strftime('%Y-%m-%d %H:%M'))}</span>
  </div>

</div>
{SCRIPT}</body>
</html>
"""


def parse_skin(argv):
    """--skin <name>, default v1. Anything else is refused rather than guessed."""
    skin = "v1"
    if "--skin" in argv:
        index = argv.index("--skin")
        skin = argv[index + 1] if index + 1 < len(argv) else ""
    if skin == "v2":
        # RETIRED (nothing superfluous, everything has a function — the byte-wall
        # skin's cells said nothing a viewer could read). The tree page
        # (tree.html) is the second surface now. A no-op so scheduled runs stay quiet.
        print("skin v2 is retired (2026-09-05) — nothing written; see design/v2-comps/board-v2-retired-2026-09-05.html and tree.html")
        raise SystemExit(0)
    if skin != "v1":
        raise SystemExit(f"unknown skin {skin!r} — expected v1")
    return skin


def parse_open(argv):
    """--open: show the tree page once the run has written it (the hub OPENS
    the page instead of naming a path). Never under
    EXO_PULSE: the heartbeat draws the page every five minutes and must not
    throw a window at whoever is sitting there."""
    return "--open" in argv and not os.environ.get("EXO_PULSE")


def show(path):
    """Open a written file with whatever this machine uses. True when it went."""
    try:
        if sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))          # noqa: B606 - Windows' own opener
        else:
            import webbrowser
            webbrowser.open(Path(path).resolve().as_uri())
        return True
    except Exception:                        # a page that will not open is not
        return False                         # a board that failed to write


def main_v2(projects, snapshot):
    """The second skin: the waterfall instrument. Lives in skin_v2.py so the
    v1 board above cannot be disturbed by it."""
    import skin_v2

    path, data, stats = skin_v2.write(sys.modules[__name__], projects, snapshot)
    hero = data["hero_row"]
    print(f"Fall: {len(data['shown'])} of {len(data['rows'])} projects "
          f"({', '.join(r['name'] for r in data['shown'])}).")
    if hero:
        print(f"Channel: {hero['name']} · {hero['edays']:.3f} d via "
              f"{hero['evidence']} · {hero['open_todos']} open "
              f"({len(hero['urgent_todos'])} urgent) · {len(hero['sessions'])} "
              f"live sessions.")
    else:
        print("Channel: none — no project carries a hard-dated work event.")
    print(f"Cells: {stats['cells']:,} in the fall + {stats['foot_cells']:,} in "
          f"the foot wall, in {stats['wall_paths']:,} packed paths.")
    print(f"Arcs: {stats['arcs']} ({stats['session_arcs']} sessions, "
          f"{stats['inbox_arcs']} inbox) · {stats['urgent_squares']} urgent "
          f"squares · {stats['bar_cells']} footer cells.")
    print(f"Wrote {path} ({path.stat().st_size:,} bytes)")


def interpreter_word() -> str:
    """The interpreter this machine runs, as a person types it: the name of
    sys.executable, without a Windows `.exe` (python3 on macOS, python on
    Windows) — never a word written down here."""
    name = Path(sys.executable or "").name
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name or ("python" if os.name == "nt" else "python3")


def new_project_command() -> str:
    """The one move a machine with no projects has: the command that makes one."""
    return f"{interpreter_word()} tools/new-project.py <name>"


def whole_now(root: Path) -> str:
    """The whole `## Now` paragraph of a folder's STATUS.md, flattened and
    never cut: on a first run it is the one card, and it says what to do."""
    try:
        lines = (root / "STATUS.md").read_text(encoding="utf-8",
                                               errors="replace").splitlines()
    except OSError:
        return ""
    now_lines, current = [], None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("<!--"):
            continue
        heading = HEADING.match(stripped)
        if heading:
            current = section_key(heading.group(1))
            continue
        if current == "now":
            now_lines.append(raw)
    return handoff_summary(now_lines, limit=None)


def render_first_run(tree):
    """The board of a machine with NO projects yet: one plain
    line naming the one move, the tree, and the hub's own `## Now` as the one
    card. Nothing else is drawn, because there is nothing else to say."""
    now = datetime.now()
    stamp = "%s, %d %s" % (now.strftime("%A"), now.day,
                           now.strftime("%B %Y · %H:%M"))
    story = whole_now(HERE)
    if not story:
        story = ("There is no STATUS.md with a ## Now paragraph in this folder "
                 "yet, so there is nothing to say here.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(PROGRAM_NAME)} Board</title>
<style>
{CSS}</style>
</head>
<body>
<div class="wrap">

  <header class="cover">
{MARK}    <div class="eyebrow">{esc(PROGRAM_NAME)} · {esc(stamp)}</div>
    <h1>Project<br>Board</h1>
    <p class="sub">No projects yet in <span class="mono">{esc(PROJECTS_DIR)}</span> —
    <span class="mono">{esc(new_project_command())}</span> makes one.</p>
  </header>

{render_tree(tree)}
  <section>
    <div class="rulehead"><span class="bignum">01</span><h2>The hub</h2></div>
    <div class="hero">
      <div class="eyebrow blue">Where things stand</div>
      <h2>{esc(HERE.name)}</h2>
      <div class="story"><p>{esc(story)}</p></div>
    </div>
  </section>

  <div class="foot">
    <span class="eyebrow">Generated from {esc(PROJECTS_DIR)} · no manual entry</span>
    <span class="eyebrow">{esc(now.strftime('%Y-%m-%d %H:%M'))}</span>
  </div>

</div>
{SCRIPT}</body>
</html>
"""


def main_first_run(wants_open, errors):
    """A machine with no projects still DRAWS: the board, the tree with the hub as its one tile, the guide and
    the ledger page — then one line saying the one move. Exit 0."""
    tree = tree_data()
    OUT_FILE.write_text(render_first_run(tree), encoding="utf-8")
    tree_path = None
    if tree is not None:
        try:
            tree_path = load_collector().write_html(tree)
        except Exception:
            tree_path = None
    write_guide([], datetime.now())
    for message in errors:
        print(f"skipped {message}")
    drawn = ("board and tree drawn" if tree_path is not None else
             "board drawn; the tree could not be drawn "
             "(tools/collect-openers.py could not be run)")
    print(f"No projects yet in {PROJECTS_DIR} — {new_project_command()} "
          f"makes one · {drawn}.")
    write_improvements()                     # hook A: the ledger page
    if wants_open:
        if tree_path is not None and show(tree_path):
            print(f"opened {Path(tree_path).name}")
        else:
            print("--open: no tree page to open (the collector could not run)")


def main():
    skin = parse_skin(sys.argv[1:])
    wants_open = parse_open(sys.argv[1:])
    projects, errors = scan()
    if not projects:
        if skin == "v2":
            # The v2 skin is unchanged: with no projects it says so and draws
            # nothing (parse_skin has already retired it before this line).
            print(f"No projects found in {PROJECTS_DIR}")
            return
        main_first_run(wants_open, errors)
        return
    snapshot = read_sessions()
    if skin == "v2":
        # v2 takes the scan list untouched — its own collect() dates it.
        main_v2(projects, snapshot)
        for message in errors:
            print(f"skipped {message}")
        return
    projects = rank(projects, snapshot, datetime.now().timestamp())
    families = group_families(projects, EVIDENCE_KEY)
    tree = tree_data()
    tree_path = None
    OUT_FILE.write_text(render(projects, snapshot, tree), encoding="utf-8")
    if tree is not None:
        # The styled tree page (catalogue style 06) rides every board run,
        # so "Orchestrator Board.command" leaves both surfaces current.
        try:
            tree_path = load_collector().write_html(tree)
        except Exception:
            pass
        front_door(tree_path)                # the wake screen's strip, dated
    guide_stats = write_guide(projects, datetime.now())
    focus = focus_items(projects)
    with_status = sum(1 for p in projects if p["status"])
    dated = [p for p in projects if p["evidence"]["ts"]]
    print(f"Scanned {len(projects)} projects in {len(families)} families.")
    if tree is None:
        print("Tree: tools/collect-openers.py could not be run - the "
              "section says so on the board.")
    else:
        rows = tree["rows"]
        active = [row for row in rows if row["active"]]
        with_opener = [row for row in rows if row["opener"]]
        colours = {colour: sum(1 for row in active if row["state"] == colour)
                   for colour in ("green", "amber", "red")}
        print(f"Tree: {len(active)} active lanes "
              f"({colours['red']} red, {colours['amber']} amber, "
              f"{colours['green']} green) - {len(with_opener)} carry an "
              f"OPENER file; {len(rows) - len(active)} paused.")
        flags = tree["flags"]
        for letter in (flags.get("scratch_install") or [])[:3]:
            # loud, and first — the other machine cannot install from it.
            print("  ! install letter INBOX.md:%d (%s) names %s — scratch/ never crosses "
                  "the brain; stage it in harvest/<row-id>/ and send the letter again"
                  % (letter["lineno"], letter["date"], letter["path"]))
        if flags["stale"]:
            print("  stale openers: " + ", ".join(flags["stale"]))
        if flags["no_opener"]:
            silent = flags["no_opener"]
            shown = ", ".join(silent[:4])
            if len(silent) > 4:
                shown += f", +{len(silent) - 4} more"
            print(f"  {len(silent)} active lane(s) wrote no opener: {shown}")
        for message in flags["skipped"]:
            print(f"  skipped {message}")
    print(f"STATUS.md in {with_status} projects · {len(focus)} open to-dos "
          f"({sum(1 for t, _ in focus if t['urgent'])} urgent).")
    if snapshot:
        groups = group_sessions(snapshot["sessions"], projects)
        live = sum(1 for s in snapshot["sessions"] if s["tag"] in SESSION_LIVE)
        print(f"Sessions: {len(snapshot['sessions'])} in {len(groups)} groups "
              f"· {live} live rows.")
    else:
        print("No sessions.json — SESSIONS section skipped.")
    flagged = [p for p in projects if p["portability"]]
    if flagged:
        print(f"Portability: {len(flagged)} project(s) flagged - "
              "nothing is lost, just not visible from this checkout.")
        for project in flagged:
            shown = project["portability"][:3]
            line = "; ".join(shown).replace("—", "-")
            hidden = len(project["portability"]) - len(shown)
            if hidden:
                line += f"; +{hidden} more (the board lists 4)"
            print(f"  {project['name']}: {line}")
    else:
        print("Portability: everything STATUS names is reachable "
              "from this checkout.")
    rulings = unpromoted_rulings()
    if rulings:
        print(f"Unpromoted rulings: {len(rulings)} TAUGHT line(s) dated "
              f"{PROMOTION_DAY}+ read as rules but carry no stamp - "
              "promote to the law book (tools/personal.py --promote) "
              "or mark journal-only.")
        for ruling in rulings:
            line = truncate(ruling["text"], 90).replace("—", "-")
            print(f"  {ruling['date']}: {line}")
    else:
        print("Unpromoted rulings: none - every recent TAUGHT rule says "
              "where it went.")
    print(f"Dated evidence: {len(dated)} of {len(projects)} projects; "
          f"the other {len(projects) - len(dated)} are unranked.")
    if dated:
        stamp = dated[0]["evidence"]
        print(f"Hero: {dated[0]['name']} — {stamp['kind']} {stamp['date']} "
              f"({stamp['edays'] * 24:.1f} h ago).")
    else:
        print("Hero: none — no project carries a dated work event.")
    for message in errors:
        print(f"skipped {message}")
    print(f"Guide: {guide_stats['curated']} curated + {guide_stats['auto']} "
          f"auto cards ({guide_stats['away']} curated for elsewhere) -> "
          f"{GUIDE_FILE.name}")
    write_improvements()                     # hook A: the ledger page
    print(f"Wrote {OUT_FILE} ({OUT_FILE.stat().st_size:,} bytes)")
    if wants_open:
        if tree_path is not None and show(tree_path):
            print(f"opened {Path(tree_path).name}")
        else:
            print("--open: no tree page to open (the collector could not run)")


if __name__ == "__main__":
    main()
