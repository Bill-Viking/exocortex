#!/usr/bin/env python3
"""collect-openers.py — every lane's handoff opener, collected mechanically.

At a machine switch the hub must not POINT at opener files; it must HAND them
over. Every session writes an OPENER file into its own project root when it
closes; this tool finds them, checks each one against the repo it claims, ranks
the lanes, and prints either a short ranked landing list (--chat), the full card
plus the opener itself (--expand), a diagnostic table (--table), machine data
(--json), or the auto region of TREE.md (--write-tree).

THE HEADER CONTRACT — an OPENER file (`OPENER.md`, or `OPENER-<Lane>.md` when a
project runs several lanes) is `key: value` lines, then a line that is exactly
`---`, then the paste-ready opener verbatim:

    lane: Project/Lane                   # display name for this row
    written: 2026-09-05T07:25:00-07:00   # when the session wrote this file
    by: Lane session 11                  # which session wrote it
    on: LAPTOP                           # machine it was written on
    head: 5ffe67e                        # repo HEAD at the moment of writing
    status_updated: 2026-09-05T07:24:10-07:00   # >= STATUS.md's mtime
    where: mid-relay, three questions answered  # <= 12 words
    next: owner                          # owner | human | machine — whose move is it
    depends_on: nothing                  # nothing | the exact gate line
    open_in: LAPTOP                      # machine the NEXT session opens on
    model: FABLE · EXTRA                 # model + effort for that session
    ---
    Read the project status/memory first. ...

Every key is optional; a missing one is REPORTED, never guessed. Freshness is
computed from git and from STATUS.md's mtime, never taken on trust: an opener
whose `head` is not in HEAD's history is STALE and is not handed over.

Stdlib only, Python 3.9-compatible, OS-neutral: roots come from the machine
record the path resolver finds (tools/exo_paths.py). Nothing here writes into
a project — the only file it ever writes is TREE.md in the orchestrator
folder, under --write-tree and nowhere else.
"""

import hashlib
import io
import json
import os
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# ── roots ─────────────────────────────────────────────────────────────────
# This file lives in <orchestrator>/tools/, so its own parent is the one root
# that cannot be wrong. machine.json supplies the projects root (a machine may
# keep projects on another disk) and is trusted over any hard-coded path.

HUB_DIR = Path(__file__).resolve().parent.parent
TREE_FILE = HUB_DIR / "TREE.md"
AUTO_START = "<!-- tree:auto-start -->"
AUTO_END = "<!-- tree:auto-end -->"

ACTIVE_DAYS = 7   # a week: 14 would catch every repo the last handoff touched
DAY = 86400.0

# ── the fall: six ISO weeks, the current one at the top ──
FALL_WEEKS = 6
FALL_ROW = 56          # px per week row, mirrored in the CSS
# The week labels own 52 px at the fall's left and a head is never narrower
# than 96 px; both live in the CSS and the page's JS (.heads, LAB), because the
# crown wraps at the window's own width and nothing here counts columns.
SESSION_CACHE = "sessions-cache.json"   # machine-local by the sync manifest's
                                        # own `sessions-*.json` exclude

# The bounded transcript readers, shared with tools/pulse.py so a session is
# read the same way on both sides.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_common import read_model, mind_of, scan_cwd, codex_cwd, lane_token   # noqa: E402
import exo_registry as _rg                                        # noqa: E402
from exo_paths import paths                                       # noqa: E402

# The machine record, where the path resolver finds it (tools/exo_paths.py):
# the file EXO_MACHINE_JSON names, the hub's own machine.json in a program
# tree, the older layout's copy otherwise. With no record at all this names the
# file a program tree would hold — absent — so every read below falls back
# exactly as it always has. A gate may point it at a fixture record.
MACHINE_FILE = paths(tool_file=__file__)["machine_file"] or (HUB_DIR / "machine.json")

_REG = [None]


def reg():
    """The person's own names — who they are, what their machines and minds are
    called, what they call their lanes, the line under their sky. Read once per
    run. Nothing about a mind, a machine or a lane is written down in this file:
    a stranger's tree draws the minds and machines THEY have, and nobody
    else's."""
    if _REG[0] is None:
        _REG[0] = _rg.registry()
    return _REG[0]


def css_slug(name):
    """A CSS-safe token for a name: lower case, anything else a dash. The class
    and the custom property are minted from it together, so they always agree."""
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-") or "x"


def identity_css(reg_record):
    """{placeholder: the generated block} — the identity hues, the identity
    marks and the machine roots, all from the registry, in its own order.

    A mind or a machine the person has given NO colour gets no token and no
    class: it is drawn in the colour it inherits, which is what "nothing is
    invented" means on a page. A registry that names nobody mints nothing, so a
    stranger's page carries no persona token at all."""
    minds = _rg.mind_drawn(reg_record)
    machines = [m for m in _rg.machine_names(reg_record)
                if _rg.machine_hue(reg_record, m)]

    def hue_line(names, prefix, scheme, hue):
        out = "".join("--%s-%s:%s;" % (prefix, css_slug(n), hue(n, scheme)) for n in names)
        return out

    def chunked(items, per_line=4):
        rows = [items[i:i + per_line] for i in range(0, len(items), per_line)]
        return "".join("".join(row) + "\n" for row in rows)

    codex = ""
    for name in minds:
        if _rg.mind_kind(reg_record, name) == "codex":
            slug, vendor = css_slug(name), _rg.mind_vendor(reg_record, name)
            codex = ("/* the Codex side, in the %s hue the plates use (TREE-ART-SPEC \u00a75.1) */\n"
                     ".skyfield path.tick.codex{stroke:var(--m-%s);stroke-opacity:.9;stroke-width:1.4}\n"
                     ".skyfield path.skill.codex{fill:var(--m-%s);opacity:.9}\n"
                     ".skycap .key .cdx{color:var(--m-%s)}\n" % (vendor, slug, slug, slug))
            break
    return {
        "@@MIND_HUES_LIGHT@@": hue_line(
            minds, "m", "light", lambda n, s: _rg.mind_hue(reg_record, n, scheme=s)),
        "@@MIND_HUES_DARK@@": hue_line(
            minds, "m", "dark", lambda n, s: _rg.mind_hue(reg_record, n, scheme=s)),
        "@@MACHINE_HUES_LIGHT@@": hue_line(
            machines, "mc", "light", lambda n, s: _rg.machine_hue(reg_record, n, s)),
        "@@MACHINE_HUES_DARK@@": hue_line(
            machines, "mc", "dark", lambda n, s: _rg.machine_hue(reg_record, n, s)),
        "@@CODEX_SKY@@": codex,
        "@@MIND_CLASSES@@": chunked(
            [".m-%s{color:var(--m-%s)}" % (css_slug(n), css_slug(n)) for n in minds]),
        "@@MACHINE_CLASSES@@": chunked(
            [".mc-%s{color:var(--mc-%s)}" % (css_slug(n), css_slug(n)) for n in machines]),
        "@@MACHINE_ROOTS@@": "".join(
            ".root.machine.mc-%s{border-top:2px solid var(--mc-%s)}\n"
            % (css_slug(n), css_slug(n)) for n in machines),
    }


def base_scheme(reg_record):
    """The ids and the label of the page's OWN light and dark token sets. They
    are the person's to name — the page ships two style sets and calls them
    whatever their registry says, or `base` when it says nothing."""
    block = reg_record["surface"].get("base_scheme")
    block = block if isinstance(block, dict) else {}
    dark = str(block.get("dark_id") or "").strip() or "base-dark"
    light = str(block.get("light_id") or "").strip() or "base-light"
    label = str(block.get("label") or "").strip() or "base"
    return dark, light, label


def html_js(reg_record):
    """The page's script, with the scheme ids and the mind sort order minted
    for THIS person."""
    dark, light, _label = base_scheme(reg_record)
    text = HTML_JS
    text = text.replace("@@DARK_ID@@", dark).replace("@@LIGHT_ID@@", light)
    # A JS object literal, written the way a hand would write it: bare keys.
    # A mind's name is letters, digits, dots and dashes at most, so a name that
    # is not a bare identifier is quoted rather than mangled.
    order = mind_sort_index(reg_record)
    bare = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
    body = ",".join("%s:%d" % (k if bare.match(k) else json.dumps(k), v)
                    for k, v in order.items())
    return text.replace("@@MIND_SORT@@", "{%s}" % body)


def html_css(reg_record):
    """The page's stylesheet with every identity block minted for THIS person."""
    text = HTML_CSS
    for mark, block in identity_css(reg_record).items():
        text = text.replace(mark, block)
    return text


def mind_sort_index(reg_record):
    """{mind: its place} for the minds the page draws — the registry's own
    order. A mind not in it sorts after them all, and keeps its own order among
    the others. The page and its script share this one table."""
    return {name: index for index, name in enumerate(_rg.mind_drawn(reg_record))}
from grok_sessions import iter_sessions as grok_sessions, metadata as grok_metadata

# an opener rides three carriers — the project folder, the brain's
# TREE.md, and a mounted transfer-drive payload's bundle. opener_carriers reads
# the two this tool could not see. The import is guarded because a collector
# that cannot collect is worse than one that reads the folder alone: a missing
# or broken module leaves today's behaviour exactly as it was.
try:
    import opener_carriers as carriers          # noqa: E402
except Exception:                               # ImportError, or a broken file
    carriers = None
# The law book is a chain of files (exo_laws: the engine's book and the
# person's own), and the dossier's four pages are filled by a conversation
# (personal). Both guarded the same way: without them the sky draws exactly as
# it did — every law the person's, every dossier page a file that exists.
try:
    import exo_laws as _laws                    # noqa: E402
except Exception:
    _laws = None
try:
    import personal as _personal                # noqa: E402
except Exception:
    _personal = None

HEADER_KEYS = ("lane", "written", "by", "on", "head", "status_updated",
               "where", "next", "depends_on", "open_in", "model")
# Optional lines: the lane's own estimate of what is left
# and, when a real date exists, when it is due. Never invented by the hub.
# `judgment` is the opener file's own key (the steps that need judgment):
# read here so a walked model line survives a round trip through TREE.md and so
# the unwalked-model-line flag can tell "walked" from "never walked".
OPTIONAL_KEYS = ("remaining", "due", "priority", "judgment")
def family_of(name):
    """The family a project belongs to, so the map can draw kin lines. ONE
    table, the registry's own, shared with the board — two readers of one rule
    drift."""
    return _rg.lane_family(reg(), name)
HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")
SEPARATOR = "---"
OPENER_NAME = re.compile(r"^OPENER(?:-(.+))?\.md$")

# STATUS.md contract, mirrored from orchestrator.py (## Now / ## To do /
# ## Important, matched loosely). Kept here rather than imported so this tool
# stands alone on either machine and cannot import-cycle with the board.
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
STATUS_SECTIONS = {"now": "now", "todo": "todo", "todos": "todo",
                   "important": "important", "wherethingslive": "where"}
STATUS_TODO = re.compile(r"^\s*[-*+]\s*\[([ xX]?)\]\s*(.*)$")

GENERIC_OPENER = "read the project status/memory first"
DONE_WHEN = "its first reply is a plain WHERE WE ARE, then it stops"

# Windows consoles are not always UTF-8; the marks degrade rather than crash.
ASCII_FALLBACK = {"🟢": "[G]", "🟡": "[A]", "🔴": "[R]", "🔒": "[gate]",
                  "·": "-", "—": "--", "📍": "WHERE:", "📋": "DO:",
                  "✅": "DONE:", "≤": "<=", "…": "..."}


def machine_roots():
    """{name, projects, orchestrator, claude, codex} from machine.json, with
    safe fallbacks. `claude` and `codex` are where the session transcripts live
    — the fall's session dots read them; a machine with no
    Codex installed simply has none."""
    name = "this machine"
    found = {}
    try:
        with MACHINE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data.get("name"), str) and data["name"].strip():
            name = data["name"].strip()
        roots = data.get("roots") or {}
        # NOT "home": `_pretty_memory_dir` reads the roots it is given, and a
        # home root it never had before would rename memory folders under it —
        # the sky must stay exactly as pass 2 drew it.
        for key in ("projects", "orchestrator", "claude", "codex", "grok"):
            value = roots.get(key)
            if isinstance(value, str) and value.strip():
                found[key] = Path(value.strip())
    except (OSError, ValueError, AttributeError):
        pass
    return {"name": name,
            "projects": found.get("projects") or (Path.home() / "Projects"),
            "orchestrator": found.get("orchestrator") or HUB_DIR,
            "claude": found.get("claude") or (Path.home() / ".claude"),
            "codex": found.get("codex") or (Path.home() / ".codex"),
            "grok": found.get("grok") or (Path.home() / ".grok")}


def emit(text=""):
    """print() that survives a non-UTF-8 console instead of raising."""
    try:
        sys.stdout.write(text + "\n")
        return
    except UnicodeEncodeError:
        pass
    safe = text
    for mark, plain in ASCII_FALLBACK.items():
        safe = safe.replace(mark, plain)
    try:
        sys.stdout.write(safe + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(safe.encode("ascii", "replace").decode("ascii") + "\n")


# ── git, never raising ────────────────────────────────────────────────────

def git(root, args, timeout=15):
    """(returncode, stdout) for `git <args>` in root. (-1, "") when it cannot
    run at all — a missing binary, a non-git folder, a timeout. Never raises."""
    try:
        if not (Path(root) / ".git").exists():
            return (-1, "")
    except OSError:
        return (-1, "")
    try:
        proc = subprocess.run(["git"] + list(args), cwd=str(root),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, universal_newlines=True,
                              encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError, ValueError):
        return (-1, "")
    return (proc.returncode, proc.stdout or "")


def git_text(root, args):
    code, out = git(root, args)
    return out.strip() if code == 0 else ""


def remote_carrier(root):
    """(has_remote, 'origin · github.com' | 'no remote — drive lane')."""
    names = [n for n in git_text(root, ["remote"]).split() if n]
    if not names:
        return (False, "no remote — drive lane")
    name = "origin" if "origin" in names else names[0]
    url = git_text(root, ["remote", "get-url", name])
    host = ""
    if url:
        if "://" in url:
            rest = url.split("://", 1)[1]
            host = rest.split("/", 1)[0].split("@")[-1]
        elif ":" in url:
            host = url.split(":", 1)[0].split("@")[-1]
    return (True, "%s · %s" % (name, host) if host else name)


def git_facts(root):
    """Every git datum this tool ranks or reports on. Never raises."""
    facts = {"is_repo": (Path(root) / ".git").exists(),
             "head": "", "head_full": "", "branch": "", "dirty": 0,
             "ahead": 0, "has_remote": False, "carrier": "not a git repo",
             "last_commit": None, "last_work_commit": None, "first_commit": None, "last_subject": ""}
    if not facts["is_repo"]:
        return facts
    facts["first_commit"] = (git_text(root, ["log", "--reverse", "--format=%cI"]).splitlines() or [None])[0]
    facts["last_subject"] = plain(git_text(root, ["log", "-1", "--format=%s"]))
    facts["head"] = git_text(root, ["rev-parse", "--short", "HEAD"])
    facts["head_full"] = git_text(root, ["rev-parse", "HEAD"])
    facts["branch"] = git_text(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    # Tracked changes only: an untracked scratch file is not unfinished work.
    code, out = git(root, ["status", "--porcelain", "--untracked-files=no"])
    if code == 0:
        facts["dirty"] = len([line for line in out.splitlines() if line.strip()])
    upstream = git_text(root, ["rev-parse", "--abbrev-ref",
                               "--symbolic-full-name", "@{upstream}"])
    if upstream:
        count = git_text(root, ["rev-list", "--count", "@{upstream}..HEAD"])
        if count.isdigit():
            facts["ahead"] = int(count)
    facts["has_remote"], facts["carrier"] = remote_carrier(root)
    facts["last_commit"] = git_text(root, ["log", "-1", "--format=%cI"]) or None
    # A button-up commit is ritual, not work: it must not make a lane "active".
    facts["last_work_commit"] = git_text(root, ["log", "-1", "--format=%cI",
                                                "--invert-grep", "--grep=^button-up:"]) or facts["last_commit"]
    return facts


# ── text helpers ──────────────────────────────────────────────────────────

def plain(text):
    """Backticks and bold markers out, whitespace collapsed. File names stay intact."""
    text = str(text).replace("`", "").replace("**", "").replace("__", "")
    return " ".join(text.split())


BRACKETS = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")


def debracket(text):
    """Parenthetical asides out — STATUS paragraphs open with dated headers
    like "X LANDED (Saturday YYYY-MM-DD HH:MM, this session)"; the row wants X."""
    return " ".join(BRACKETS.sub("", str(text)).split())


def cut(text, limit):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"


def words(text, count):
    parts = plain(text).split()
    if len(parts) <= count:
        return " ".join(parts)
    return " ".join(parts[:count]) + "…"


def parse_iso(text):
    """ISO-8601 → aware datetime (local tz assumed when naive), else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip().replace("Z", "+00:00")
    # Python 3.9 refuses an offset without a colon (-0700); the
    # button-up writes one. Normalize before the parse.
    raw = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", raw)
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return stamp.astimezone()
    return stamp


def iso_of(timestamp):
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(
        timespec="seconds")


def day_of(iso_text):
    return iso_text[:10] if iso_text else "—"


# ── STATUS.md ─────────────────────────────────────────────────────────────

def section_key(heading):
    return STATUS_SECTIONS.get(re.sub(r"[^a-z0-9]", "", heading.lower()))


def read_status(root):
    """{now, now_first, todos, mtime, mtime_iso} or None. Never raises."""
    path = Path(root) / "STATUS.md"
    try:
        if not path.is_file():
            return None
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        mtime = path.stat().st_mtime
    except OSError:
        return None

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

    # No "To do" heading at all: take checkboxes wherever they sit (the board's
    # own fallback, so the two never disagree about what is open).
    todos = []
    for raw in sections.get("todo", lines):
        item = STATUS_TODO.match(raw)
        if not item or item.group(1).strip().lower() == "x":
            continue
        text = item.group(2).strip()
        urgent = text.startswith("!")
        if urgent:
            text = text[1:]
        text = plain(text)
        if text:
            todos.append({"text": text, "urgent": urgent})

    paragraph = []
    for raw in sections.get("now", []):
        stripped = raw.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    now = plain(" ".join(paragraph))
    first = now.split(". ", 1)[0] if now else ""
    return {"now": now, "now_first": first, "todos": todos, "mtime": mtime,
            "mtime_iso": iso_of(mtime)}


# ── openers ───────────────────────────────────────────────────────────────

def find_openers(root):
    """[(path, lane suffix or '')] — OPENER.md first, then OPENER-<Lane>.md."""
    found = []
    try:
        entries = sorted(Path(root).iterdir())
    except OSError:
        return found
    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        match = OPENER_NAME.match(entry.name)
        if match:
            found.append((entry, (match.group(1) or "").strip()))
    found.sort(key=lambda pair: (pair[1] != "", pair[1], pair[0].name))
    return found


def parse_opener(path):
    """{header, body, missing, problems} — never raises on a weird file."""
    out = {"header": {}, "body": "", "missing": [], "problems": [],
           "unknown": [], "raw": ""}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        out["problems"].append("unreadable: %s" % exc)
        out["missing"] = list(HEADER_KEYS)
        return out
    # The file verbatim: TREE.md carries this copy byte for byte, so an unknown
    # key a future law adds is never dropped on the way to the other machine.
    out["raw"] = text
    lines = text.splitlines()
    body_start = None
    for index, raw in enumerate(lines):
        if raw.strip() == SEPARATOR:
            body_start = index + 1
            break
        stripped = raw.strip()
        if not stripped:
            continue
        match = HEADER_LINE.match(stripped)
        if not match:
            out["problems"].append("header line not `key: value`: %s"
                                   % cut(stripped, 40))
            continue
        key = match.group(1).strip().lower().replace("-", "_")
        value = match.group(2).strip()
        if key in HEADER_KEYS or key in OPTIONAL_KEYS:
            out["header"][key] = value
        elif key == CAPTURED_KEY:
            # read from the raw text by captured_of(), the same for every
            # carrier's copy — known, so never listed as unknown.
            pass
        else:
            out["unknown"].append(key)
    if body_start is None:
        # The contract is header, `---`, body. Without the separator nothing can
        # be trusted as header, so nothing is read as header — and it is said.
        out["header"] = {}
        out["body"] = text.strip("\n")
        out["problems"].append("no `---` separator — no header could be read")
    else:
        out["body"] = "\n".join(lines[body_start:]).strip("\n")
    out["missing"] = [key for key in HEADER_KEYS if not out["header"].get(key)]  # optional keys never count as missing
    return out


BRAIN_HEADS = ("none", "n/a", "na")


# ── the head a capture puts on an opener its own sitting outran ──
# `tools/buttonup.py capture` never rewrites a lane's own opener; when the
# sitting it was written for has run and been captured from the outside, it
# adds ONE `captured:` header line (newest first, right after `by:`). Read from
# the RAW text so a carrier's copy is read the same as the folder's.
CAPTURED_KEY = "captured"
_CAP_SITTING = re.compile(r"\bs(\d+) \"")
_CAP_NEXT = re.compile(r"next sitting: s(\d+)\b")
_CAP_LAST = re.compile(r"\(last message ([^)]+)\)")
_CAP_TITLE = (re.compile(r"\bs\d+ \"(.*)\", ran and was captured"),
              re.compile(r"the session \"(.*)\" ran after this opener"))
_ACT_SITTING = re.compile(r"^(\s*(?:ACT|ARCH)\s*[—–-]\s*[^:\n]+:\s*s)(\d+)\b")
# the one copy of the pattern that finds the ACT title inside an `open_in:` text.
_ACT_TITLE = re.compile(r"(ACT\s*[—–-]\s*[^·|\n]+)")


def captured_of(raw):
    """{line, sitting, next, title, last, date} from an opener's newest
    `captured:` header line, or None when it carries none."""
    for line in str(raw or "").splitlines():
        if line.strip() == SEPARATOR:
            return None
        match = HEADER_LINE.match(line.strip())
        if not match or match.group(1).strip().lower() != CAPTURED_KEY:
            continue
        value = match.group(2).strip()
        sitting = _CAP_SITTING.search(value)
        nxt = _CAP_NEXT.search(value)
        lasts = _CAP_LAST.findall(value)
        title = ""
        for pattern in _CAP_TITLE:
            found = pattern.search(value)
            if found:
                title = found.group(1)
                break
        when = parse_iso(value.split("·")[0].strip())
        return {"line": value,
                "sitting": int(sitting.group(1)) if sitting else None,
                "next": int(nxt.group(1)) if nxt else None,
                "title": title,
                "last": lasts[-1].strip() if lasts else "",
                "date": when.date().isoformat() if when else ""}
    return None


def captured_note(captured):
    """The one note a headed opener carries on every surface."""
    if captured.get("sitting") is not None and captured.get("next") is not None:
        return ("captured: s%d ran and was captured %s; the next sitting is s%d"
                % (captured["sitting"], captured.get("date") or "?", captured["next"]))
    return ("captured: the session \"%s\" ran after this opener and was captured %s; "
            "the next sitting opens from it" % (captured.get("title") or "?",
                                                 captured.get("date") or "?"))

# THE INSTALLER'S OWN WORD for a header time nobody can know when the file is
# written: the hub's first opener is a SEED, copied once at
# install, so the file's own mtime IS the moment it was written. Only this exact
# word is read that way — any other value that is not a timestamp stays exactly
# what it was, so no opener anywhere else changes its meaning. The seed walk
# copies OPENER.md and STATUS.md a moment apart, so STATUS.md written inside
# one install's window is the same install, not a change since the opener.
INSTALL_WORD = "at install"
INSTALL_WINDOW = 120.0          # seconds: one install's seed walk, start to end


def install_stamp(value, path):
    """The opener file's own mtime (second resolution) when `value` is the
    installer's word, else None."""
    if str(value or "").strip().lower() != INSTALL_WORD or path is None:
        return None
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime).astimezone().replace(
            microsecond=0)
    except (OSError, ValueError, OverflowError):
        return None


# `on: here` (the hub's seeded first opener): the machine the
# file sits on, read as that machine's own name from its record. Only this
# exact word; every other `on:` value is shown exactly as written.
HERE_WORD = "here"
_HERE_NAME = []


def here_name():
    """This machine's own name, from the machine record the path resolver finds
    (MACHINE_FILE — the older layout's copy, or a program tree's
    <hub>/machine.json). '—' when no record names one."""
    if not _HERE_NAME:
        name = ""
        try:
            name = str(json.loads(MACHINE_FILE.read_text(encoding="utf-8"))
                       .get("name") or "").strip()
        except Exception:
            name = ""
        _HERE_NAME.append(name or "—")
    return _HERE_NAME[0]


def install_or_iso(value, opener_path):
    """(the moment a header time names, the slack a comparison against it
    allows). An ISO value is itself, with none; the installer's word is the
    opener file's own mtime, with one install's window."""
    stamp = parse_iso(value)
    if stamp is not None:
        return stamp, timedelta(0)
    stamp = install_stamp(value, opener_path)
    return stamp, (timedelta(seconds=INSTALL_WINDOW) if stamp is not None
                   else timedelta(0))


def head_says_brain(head):
    """Does this opener's header say it belongs to no commit at all?

    `head: none` and `head: n/a` are the two spellings, and a note after
    either of them ("none — brain lane") changes nothing. An opener that says
    so is a BRAIN opener: it lives beside a repository without belonging to
    it, so STATUS alone says whether it is current."""
    word = (head or "").strip().lower()
    if not word:
        return False
    first = word.replace("—", " ").replace("·", " ").replace(",", " ").split()[0]
    return first.strip("()[]") in BRAIN_HEADS


def freshness(root, header, problems, status, facts, source="folder",
              payload="", opener_path=None):
    """('fresh'|'note'|'stale', [notes]) — computed from git and mtimes only.

    FRESH  head is an ancestor of HEAD, EQUALS HEAD, and STATUS.md has not been
           written since `status_updated`.
    NOTE   head is an ancestor but HEAD moved on, or STATUS moved on. The opener
           is still handed over, carrying its note.
    STALE  head is not in HEAD's history, or the header could not be read. Not
           handed over: the hub falls back to the generic opener.

    `source` is the carrier the header came from. An opener that rode
    in on a carrier names a commit this repo has not landed yet — that is the
    payload waiting to be landed, not a stale opener, so it is a NOTE.
    """
    notes = []
    head = (header.get("head") or "").strip()
    # a sha may carry an aside after it ("d9f8cc55 (this machine's HEAD
    # before this carryover)"); git sees the first token only.
    head = head.split()[0] if head.split() else ""
    if problems:
        return ("stale", [problems[0]])
    if not facts["is_repo"] or head_says_brain(head):
        # No HEAD to check it against, so currency rests on STATUS alone, and
        # it is never STALE for that. Two ways to be in that position: the
        # folder is not a git repo (it syncs by file copy), or the opener says
        # in its own header that it is a BRAIN opener — `head: none` or
        # `head: n/a`. The second is what a hub that IS a git repo needs: its
        # openers sit beside the code but do not belong to the code's history.
        stamp, slack = install_or_iso(header.get("status_updated"), opener_path)
        if stamp is None:
            notes.append("no `status_updated` in the opener header")
        elif status is not None:
            written = datetime.fromtimestamp(status["mtime"]).astimezone().replace(
                microsecond=0)
            if written > stamp + slack:
                notes.append("STATUS changed since the opener")
        return ("note" if notes else "fresh", notes)
    if not head:
        return ("stale", ["no `head` in the opener header — "
                          "it cannot be checked against this repo"])
    code, _ = git(root, ["merge-base", "--is-ancestor", head, "HEAD"])
    if code != 0:
        if carriers is not None and source and source != "folder":
            return ("note", [carriers.absent_head_note(head, source, payload)])
        return ("stale", ["head %s is not in this HEAD's history"
                          % cut(head, 12)])
    resolved = git_text(root, ["rev-parse", head + "^{commit}"])
    if resolved and facts["head_full"] and resolved != facts["head_full"]:
        moved = git_text(root, ["rev-list", "--count", head + "..HEAD"])
        subjects = [line.strip() for line in
                    git_text(root, ["log", "--format=%s", head + "..HEAD"]
                             ).splitlines() if line.strip()][:3]
        notes.append("HEAD moved %s commit%s since the opener: %s"
                     % (moved or "?", "" if moved == "1" else "s",
                        "; ".join(subjects) or "no subjects"))
    stamp, slack = install_or_iso(header.get("status_updated"), opener_path)
    if stamp is None:
        notes.append("no `status_updated` in the opener header — "
                     "STATUS could have moved since")
    elif status is not None:
        # The mtime is floored to the second before the comparison: an ISO
        # stamp written with second resolution is itself floored, so a raw
        # comparison would call every same-second write a change.
        written = datetime.fromtimestamp(status["mtime"]).astimezone().replace(
            microsecond=0)
        if written > stamp + slack:
            notes.append("STATUS changed since the opener")
    return ("note" if notes else "fresh", notes)


# ── one row per lane ──────────────────────────────────────────────────────

def state_of(facts, status, openers, active, lane=None):
    """(color, [reasons]) by the one rule — nothing else feeds it.

    The red and amber tests are project-level facts (a dirty tree, an unpushed
    commit, an urgent to-do, a stale opener), so every lane of a project wears
    the same colour: the tree is dirty for all of them or for none of them.

    `lane` : the lane's own names — its opener suffix and its
    header lane — for ONE lane of a folder that holds several. Then the urgent
    test counts only the `!` to-dos that START with one of those names
    (opener_carriers.names_lane, the one rule): another lane's `!` is not this
    lane's attention, and a `!` that names no lane is the project's. None, the
    default, is the rule as it always was (any `!` in the folder).
    """
    red = []
    if facts["dirty"] > 0:
        red.append("%d dirty tracked file%s"
                   % (facts["dirty"], "" if facts["dirty"] == 1 else "s"))
    if facts["ahead"] > 0 and facts["has_remote"]:
        red.append("%d unpushed commit%s"
                   % (facts["ahead"], "" if facts["ahead"] == 1 else "s"))
    stale = [o for o in openers if o["fresh"] == "stale"]
    if stale:
        red.append("%d stale opener%s"
                   % (len(stale), "" if len(stale) == 1 else "s"))
    if red:
        return ("red", red)
    # Amber = attention, not breakage (an open urgent
    # item is amber; red is dirty, unpushed or stale only).
    amber = []
    # WHO OWES THE NEXT MOVE. `owner` and `human` always mean a person; so do
    # the person's own short word and any alias their registry names. A word
    # nobody knows is counted as a person AND reported on that opener —
    # attention, never silence.
    if any(_rg.next_side(reg(), (o["header"].get("next") or ""))[0] == "human"
           for o in openers):
        amber.append("waiting on you")
    owns = (lambda todo: True)
    if lane and carriers is not None and hasattr(carriers, "names_lane"):
        names = tuple(lane) if isinstance(lane, (list, tuple)) else (lane,)
        owns = (lambda todo: carriers.names_lane(todo["text"], *names))
    if status and any(todo["urgent"] and owns(todo) for todo in status["todos"]):
        amber.append("urgent item open")
    if active and not openers:
        amber.append("no opener written")
    if amber:
        return ("amber", amber)
    return ("green", ["ready to open"])


def _num(text):
    """'3 sittings' → 3.0; '40%' → 40.0; None when there is no number."""
    m = re.search(r"-?\d+(?:\.\d+)?", str(text or ""))
    return float(m.group(0)) if m else None


def _workdays(start, end):
    """Mon–Fri days from start to end (dates), never negative."""
    a, b = start.date(), end.date()
    if b <= a:
        return 0
    n, d = 0, a
    while d < b:
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _span(days):
    """A human span: 6 h · 4 d · 3 mo · 1.2 y. '—' when unknown."""
    if days is None:
        return "—"
    if days * 24 < 1:
        return "%d min" % max(1, int(days * 24 * 60))
    if days < 1:
        return "%d h" % int(days * 24)
    if days < 30:
        return "%d d" % int(days)
    if days < 365:
        return "%d mo" % int(round(days / 30.4))
    return "%.1f y" % (days / 365.0)


def _secs(seconds):
    """A short span in the unit a mailbox poll is measured in: 40 s · 3 min · 2 h.
    _span's finest grain is a minute, and "1 min" cannot tell a mailbox checked
    forty seconds ago from one checked two minutes ago."""
    if seconds is None:
        return "—"
    if seconds < 90:
        return "%d s" % int(seconds)
    return _span(seconds / DAY)


def next_move(status):
    """The one move this lane owes, from STATUS.md's open to-dos."""
    if status:
        for todo in status["todos"]:
            if todo["urgent"]:
                return cut(debracket(todo["text"]), 80)
        if status["todos"]:
            return cut(debracket(status["todos"][0]["text"]), 80)
    return GENERIC_OPENER


def build_card(row):
    """The card fields, once, for --expand, --write-tree and the board."""
    status = row["_status"]
    todos = list(status["todos"]) if status else []
    todos.sort(key=lambda todo: not todo["urgent"])
    actions = [todo for todo in todos][:6]
    now = cut(status["now"], 400) if status and status["now"] else ""
    last = []
    if status and status["mtime_iso"]:
        last.append("STATUS %s" % status["mtime_iso"])
    if row["last_commit"]:
        last.append("last commit %s" % row["last_commit"])
    return {
        # A `where` lifted from STATUS is the head of the paragraph printed
        # right after it, so the card shows it only when the opener SAID it.
        "where": row["where"] if row["where_from"] == "header" else "",
        "now": now,
        # A card is skimmed, not studied: a to-do that runs to a paragraph is
        # cut, and the ellipsis says STATUS.md holds the rest.
        "actions": [{"text": cut(t["text"], 240), "urgent": t["urgent"]}
                    for t in actions],
        "continues_on": row["continues_on"],
        "lives_at": row["path"],
        "carrier": row["carrier"],
        "last_recorded": " · ".join(last) or "nothing recorded",
        "depends_on": row["depends_on"],
        "notes": row["notes"],
        "handed": row["fresh"] in ("fresh", "note") and bool(row["body"]),
        "open_in": row["open_in"],
        "model": row["model"],
        "body": row["body"],
        "done_when": DONE_WHEN,
        "fallback": GENERIC_OPENER,
        # the card says which copy of the opener this is, and when it
        # was written, right above the prompt the hub hands over.
        "source": row.get("source") or "none",
        "written": row.get("written") or "",
        "behind_carrier": row.get("stale_behind_carrier") or "",
        # the capture's head, so the WHERE line can say which sitting ran.
        "captured": row.get("captured"),
    }


# ── the fall's own bytes: weeks, commits per week, sessions per week ───────

def _wkey(stamp):
    """The ISO week a datetime falls in, as '2026-W36' — the fall's row key."""
    cal = stamp.isocalendar()
    return "%04d-W%02d" % (cal[0], cal[1])


def _week_label(monday, newest):
    if newest:
        return "this week"
    return "%d %s" % (monday.day, monday.strftime("%b"))


_WEEKS_CACHE = None


def fall_weeks(n=FALL_WEEKS):
    """[{key, start, end, label, mon}] — the current ISO week first, then the
    n−1 before it. Local time throughout: a commit is in the week it was
    made in, not UTC's. Computed once per run."""
    global _WEEKS_CACHE
    if _WEEKS_CACHE is not None:
        return _WEEKS_CACHE
    now = datetime.now().astimezone()
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    weeks = []
    for i in range(n):
        start = monday - timedelta(weeks=i)
        end = start + timedelta(weeks=1)
        weeks.append({"key": _wkey(start), "label": _week_label(start, i == 0),
                      "start": start.timestamp(), "end": end.timestamp(),
                      "mon": start.date().isoformat()})
    _WEEKS_CACHE = weeks
    return weeks


def fall_window():
    """(weeks newest-first, window start timestamp, window start ISO date)."""
    weeks = fall_weeks()
    start = weeks[-1]["start"]
    return weeks, start, datetime.fromtimestamp(start).strftime("%Y-%m-%d")


WEEK_LOG_MAX = 8       # commits kept per week for the inspector


def week_commits(root, weeks, since):
    """({week key: commits}, {week key: [{h, s, d}]}) for one repo — ONE
    `git log --since` per project, bucketed by ISO week in local time.
    The second dict is what a stream segment answers a click with: the newest
    WEEK_LOG_MAX commits of that week, each `short sha · subject · date`
    (bounded). Both empty when there is no git."""
    out = dict((w["key"], 0) for w in weeks)
    log = dict((w["key"], []) for w in weeks)
    text = git_text(root, ["log", "--since=%s" % since,
                           "--format=%ct%x09%h%x09%s"])
    if not text:
        return out, log
    for line in text.splitlines():
        parts = line.rstrip("\n").split("\t", 2)
        if len(parts) < 2 or not parts[0].strip().isdigit():
            continue
        when = datetime.fromtimestamp(int(parts[0].strip())).astimezone()
        key = _wkey(when)
        if key not in out:
            continue
        out[key] += 1
        if len(log[key]) < WEEK_LOG_MAX:      # git log is newest first
            log[key].append({"h": parts[1].strip(),
                             "s": (parts[2] if len(parts) > 2 else "").strip(),
                             "d": when.strftime("%a %d %b %H:%M")})
    return out, log


def _session_files(roots):
    """[(path, kind, dir)] — every Claude Code transcript, Codex rollout, and primary Grok session on
    this machine. A machine with no ~/.codex simply contributes none."""
    found = []
    claude = Path(roots.get("claude") or (Path.home() / ".claude"))
    try:
        for d in (claude / "projects").iterdir():
            if not d.is_dir():
                continue
            try:
                for f in d.glob("*.jsonl"):
                    found.append((f, "claude", d.name))
            except OSError:
                continue
    except OSError:
        pass
    codex = Path(roots.get("codex") or (Path.home() / ".codex"))
    try:
        if (codex / "sessions").is_dir():
            for f in (codex / "sessions").rglob("rollout-*.jsonl"):
                found.append((f, "codex", f.parent.name))
    except OSError:
        pass
    for item in grok_sessions(roots.get("grok") or (Path.home() / ".grok")):
        if not item.get("is_subagent"):
            found.append((Path(item["path"]), "grok", item["cwd"]))
    return found


SESSION_REPORT = {}     # the last scan's counts, for a caller that reports them


def session_weeks(roots, weeks):
    """{cwd → {week key → [{mind, id, model}]}} — the sessions that ran in the
    window. One file is one session; it counts in every week it touched
    (created … last written). The mind comes from the SAME bounded read the
    pulse uses, and every read is cached by (path, mtime) in sessions-cache.json
    so a redraw costs nothing. Files outside the window are never opened."""
    hub = Path(roots.get("orchestrator") or HUB_DIR)
    window_start = weeks[-1]["start"]
    cache_path = hub / SESSION_CACHE
    cache = {}
    try:
        raw = json.loads(io.open(cache_path, encoding="utf-8").read())
        if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
            cache = raw["entries"]
    except Exception:
        cache = {}
    fresh, out = {}, {}
    read, hits = 0, 0
    for path, kind, folder in _session_files(roots):
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_mtime < window_start:
            continue                     # outside the window: never opened
        key = str(path)
        was = cache.get(key)
        if isinstance(was, dict) and abs(float(was.get("m") or 0) - st.st_mtime) < 0.001:
            entry = dict(was)
            hits += 1
        else:
            meta = grok_metadata(path) if kind == "grok" else {}
            model = meta.get("model", "") if kind == "grok" else read_model(path)
            entry = {"m": st.st_mtime, "kind": kind,
                     "cwd": (meta.get("cwd", "") if kind == "grok" else
                             codex_cwd(path) if kind == "codex" else scan_cwd(path)),
                     "model": model, "mind": mind_of(kind, model),
                     "id": meta.get("id", path.stem),
                     "b": float(meta.get("started_epoch") or getattr(st, "st_birthtime", None) or st.st_ctime)}
            read += 1
        entry["m"] = st.st_mtime
        fresh[key] = entry
        where = (entry.get("cwd") or "").rstrip("/\\") or folder
        started = min(float(entry.get("b") or st.st_mtime), st.st_mtime)
        # The weeks this session TOUCHED, and only those: the week it was last
        # written (its mtime) and the week it was created, when that is a
        # different week inside the window. The weeks between are not on record
        # — a file says when it began and when it was last written, nothing more
        # — so nothing is drawn for them (every mark is a real byte).
        for ts in (st.st_mtime, started):
            for w in weeks:
                if w["start"] <= ts < w["end"]:
                    seen = out.setdefault(where, {}).setdefault(w["key"], [])
                    if not any(s["id"] == str(entry.get("id") or path.stem)[-6:] for s in seen):
                        seen.append({"mind": entry.get("mind") or "CLAUDE",
                                     "id": str(entry.get("id") or path.stem)[-6:],
                                     "model": entry.get("model") or "",
                                     # what a session dot answers with
                                     "kind": entry.get("kind") or "claude",
                                     "when": datetime.fromtimestamp(st.st_mtime)
                                     .astimezone().strftime("%a %d %b %H:%M")})
                    break
    try:
        io.open(cache_path, "w", encoding="utf-8").write(
            json.dumps({"version": 1, "written": iso_of(datetime.now().timestamp()),
                        "entries": fresh}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    SESSION_REPORT.clear()
    SESSION_REPORT.update({"files": len(fresh), "read": read, "cached": hits,
                           "cwds": len(out)})
    return out


def opener_entry(root, name, suffix, file_name, parsed, folder, others,
                 status, facts):
    """One opener, after every carrier's copy of it has had its say.

    The newest `written:` wins; the entry remembers which carrier that was and,
    when it was not the project folder, the one sentence that says so."""
    chosen = {"winner": None, "flag": ""}
    if carriers is not None:
        chosen = carriers.pick(folder, others, parse=parse_iso)
    winner = chosen.get("winner")
    if winner is None:
        parsed = parsed or {"header": {}, "body": "", "raw": "", "problems": [],
                            "missing": list(HEADER_KEYS), "unknown": []}
        header, body = parsed["header"], parsed["body"]
        raw, problems = parsed.get("raw") or "", parsed["problems"]
        missing, unknown = parsed["missing"], parsed["unknown"]
        source, payload = "folder", ""
    else:
        header, body, raw = winner["header"], winner["body"], winner["raw"]
        problems, missing = winner["problems"], winner["missing"]
        unknown, source = winner["unknown"], winner["source"]
        # A brain copy of a drive opener still knows which payload must land.
        payload = winner.get("payload") or carriers.origin_payload(winner)
    # The installer's word reads the FOLDER copy's own mtime; a carrier's copy
    # has no file here to ask, so it keeps whatever its header says.
    here = (Path(root) / file_name) if (file_name and source == "folder") else None
    fresh, notes = freshness(root, header, problems, status, facts,
                             source=source, payload=payload, opener_path=here)
    notes = list(notes)
    captured = captured_of(raw)
    # opener_carriers.py parses a carrier's copy with its own mirrored key
    # list, which does not know `captured:` — known here, so never unknown.
    unknown = [key for key in (unknown or []) if key != CAPTURED_KEY]
    if captured is not None:
        # this opener's own sitting already ran — still
        # handed (the prompt is the lane's own), never as FRESH.
        notes.insert(0, captured_note(captured))
        if fresh == "fresh":
            fresh = "note"
    judged = carriers.judgment_unwalked(header, body) if carriers else ""
    if judged:
        notes.append(carriers.judgment_sentence(judged))
    lane = header.get("lane") or ("%s/%s" % (name, suffix) if suffix else name)
    return {"file": file_name, "lane": plain(lane), "fresh": fresh,
            "notes": notes, "header": header, "body": body, "raw": raw,
            "missing": missing, "problems": problems, "unknown": unknown,
            "source": source, "payload": payload, "suffix": suffix,
            "captured": captured,
            "carrier_flag": chosen.get("flag") or "",
            "judgment_unwalked": judged}


def scan_project(name, root, is_hub=False, carried=None):
    """Every row this project contributes. One per opener, else one for itself."""
    root = Path(root)
    facts = git_facts(root)
    status = read_status(root)
    # The fall's streams: one `git log --since` per project, bucketed by week.
    _weeks, _wstart, _since = fall_window()
    wcommits, wlog = week_commits(root, _weeks, _since)
    openers = []
    for path, suffix in find_openers(root):
        parsed = parse_opener(path)
        folder, others = None, []
        if carriers is not None:
            folder = carriers.candidate("folder", parsed.get("raw") or "",
                                        file=path.name, project=name,
                                        parse=parse_iso)
            # A seed's `written: at install` is the file's own mtime,
            # so the newest-copy-wins rule can still compare it.
            seeded = install_stamp(parsed["header"].get("written"), path)
            if seeded is not None and folder is not None \
                    and folder.get("written_ts") is None:
                folder["written_ts"] = seeded.timestamp()
            others = carriers.candidates_for(carried, name, suffix,
                                             parsed["header"].get("lane"),
                                             path.name)
        openers.append(opener_entry(root, name, suffix, path.name, parsed,
                                    folder, others, status, facts))
    # A lane whose opener has not landed here at all: it closed on the other
    # machine and its file is still riding a carrier. It is a lane of this
    # project all the same, so it gets its row, with the carrier named.
    if carriers is not None and carried:
        for group in carriers.project_candidates(carried, name):
            first = group[0]
            openers.append(opener_entry(root, name, first.get("suffix") or "",
                                        first.get("file") or "", None, None,
                                        group, status, facts))

    stamps = [parse_iso(facts["last_work_commit"] or facts["last_commit"])]
    if status:
        stamps.append(datetime.fromtimestamp(status["mtime"]).astimezone())
    stamps = [s for s in stamps if s is not None]
    touched = max(stamps) if stamps else None
    now = datetime.now().astimezone()
    fresh_days = (now - touched).total_seconds() / DAY if touched else None
    active = bool(openers) or (fresh_days is not None
                               and fresh_days <= ACTIVE_DAYS)
    color, reasons = state_of(facts, status, openers, active)
    project_move = next_move(status)
    # Age: first commit, else the folder's birth (creation) time.
    opened = parse_iso(facts.get("first_commit"))
    if opened is None:
        try:
            st = root.stat()
            born = getattr(st, "st_birthtime", None) or st.st_ctime
            opened = datetime.fromtimestamp(born).astimezone()
        except OSError:
            opened = None
    age_days = (now - opened).total_seconds() / DAY if opened else None
    idle_days = fresh_days
    open_items = list(status["todos"]) if status else []
    urgent_n = sum(1 for t in open_items if t["urgent"])
    plate = 2 * urgent_n + (len(open_items) - urgent_n)
    fallback_where = words(debracket(status["now_first"]), 12) if status else ""

    rows = []
    blanks = [{"file": None, "lane": name, "fresh": "none", "notes": [],
               "header": {}, "body": "", "raw": "", "missing": list(HEADER_KEYS),
               "problems": [], "unknown": [], "source": "none", "payload": "",
               "suffix": "", "carrier_flag": "", "judgment_unwalked": "",
               "captured": None}]
    for opener in (openers or blanks):
        header = opener["header"]
        # The move this LANE owes: its own opener's first step, else
        # a STATUS item that names it, else the project's — marked as such.
        move, move_from = project_move, "project"
        if carriers is not None:
            move, move_from = carriers.lane_next_move(
                opener["body"], opener.get("suffix") or "",
                (status["todos"] if status else []), project_move,
                cut=cut, debracket=debracket)
        depends = (header.get("depends_on") or "nothing").strip() or "nothing"
        gated = depends.lower() not in ("nothing", "none", "-")
        open_in = (header.get("open_in") or "").strip()
        # a headed opener's card says the NEXT sitting; the raw header
        # text stays in row["header"]["open_in"].
        open_in = open_in_said({"header": header, "open_in": open_in,
                                "captured": opener.get("captured"),
                                "lane": opener["lane"]}) if open_in else open_in
        header_where = plain(header.get("where") or "")
        remaining = _num(header.get("remaining"))
        due = parse_iso(header.get("due"))
        urgency = None
        if remaining is not None:
            if due is not None:
                left = max(1, _workdays(now, due))
                urgency = remaining / float(left)
            else:
                urgency = remaining
        weight = remaining if remaining is not None else float(plate)
        row = {
            "lane": opener["lane"],
            "project": name,
            "family": family_of(name),
            "opened": opened.isoformat(timespec="seconds") if opened else None,
            "age_days": age_days,
            "idle_days": idle_days,
            "age_txt": _span(age_days),
            "idle_txt": _span(idle_days),
            "open_items": len(open_items),
            "urgent_items": urgent_n,
            "remaining": remaining,
            "due": due.date().isoformat() if due else None,
            "urgency": urgency,
            "weight": weight,
            "is_hub": is_hub,
            "path": str(root),
            "opener": opener["file"],
            "fresh": opener["fresh"],
            # A `next:` word nobody knows is SAID on the lane and the lane is
            # still counted as waiting on a person — attention, never silence.
            # It is a note, not a staleness verdict: the opener is current, its
            # header simply uses a word this registry does not know.
            "notes": (list(opener["notes"]) + list(opener["problems"])
                      + [n for n in [_rg.next_side(reg(), header.get("next"))[1]] if n]),
            "missing": opener["missing"],
            "unknown": opener["unknown"],
            "header": header,
            "body": opener["body"],
            "state": color,
            "state_words": " · ".join(reasons[:2]),
            "state_reasons": reasons,
            "active": active,
            "touched": touched.isoformat(timespec="seconds") if touched else None,
            "touched_day": day_of(touched.isoformat()) if touched else "—",
            "touched_ts": touched.timestamp() if touched else -1.0,
            "on": (here_name() if (header.get("on") or "").strip().lower() == HERE_WORD
                   else (header.get("on") or "").strip() or "—"),
            "open_in": open_in or "—",
            "model": (header.get("model") or "").strip() or "—",
            "next_owner": (header.get("next") or "").strip().lower() or "none",
            "depends_on": depends,
            "gated": gated,
            "where": words(header_where or fallback_where, 12) or "—",
            "where_from": ("header" if header_where
                           else ("status" if fallback_where else "none")),
            "next_move": move,
            "next_move_from": move_from,
            # which carrier this opener came from, and the sentence that
            # says the folder's copy is behind it. False when it is not.
            "source": opener.get("source") or "none",
            "payload": opener.get("payload") or "",
            "stale_behind_carrier": opener.get("carrier_flag") or False,
            "judgment_unwalked": opener.get("judgment_unwalked") or "",
            # the capture's head — {line, sitting, next, title, last,
            # date} — or None when the opener's sitting has not been outrun.
            "captured": opener.get("captured"),
            "written": (header.get("written") or "").strip(),
            "_raw": opener.get("raw") or "",
            "continues_on": open_in if open_in else "either machine",
            "branch": facts["branch"],
            "head": facts["head"],
            "dirty": facts["dirty"],
            "ahead": facts["ahead"],
            "has_remote": facts["has_remote"],
            "carrier": facts["carrier"],
            "last_commit": facts["last_commit"],
            "last_subject": facts.get("last_subject", ""),
            "week_commits": dict(wcommits),
            # the inspector's own bytes; `_`-prefixed so --json stays lean
            "_week_log": dict(wlog),
            "commits_window": sum(wcommits.values()),
            "is_repo": facts["is_repo"],
            "status_mtime": status["mtime_iso"] if status else None,
            "_status": status,
        }
        row["card"] = build_card(row)
        rows.append(row)
    return rows


def project_roots():
    """[(display name, path, is_hub)] — the board's own enumeration rule, plus
    the orchestrator folder itself (skipped when a fixture root is forced)."""
    forced = os.environ.get("COLLECT_OPENERS_ROOT", "").strip()
    roots = machine_roots()
    projects_root = Path(forced) if forced else roots["projects"]
    found = []
    try:
        entries = sorted(projects_root.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        try:
            if entry.name.startswith(".") or not entry.is_dir():
                continue
        except OSError:
            continue
        found.append((entry.name, entry, False))
    if not forced:
        hub = roots["orchestrator"]
        try:
            if hub.is_dir():
                found.append((os.path.basename(str(hub).rstrip("/\\")) or "Exocortex", hub, True))
        except OSError:
            pass
    return found, projects_root, roots["name"]


LAST_CARRIED = []       # carrier openers no project here could claim


def carrier_index(projects_root):
    """Every opener the brain and the drive carry, read ONCE per run.
    Empty when opener_carriers is missing or could not read a carrier — the
    folder copies then stand, exactly as they did before this build."""
    if carriers is None:
        return {}
    try:
        return carriers.index(TREE_FILE, projects_root, parse=parse_iso)
    except Exception as exc:                  # a broken carrier is a note
        return {"all": [], "notes": ["carriers: %s" % exc]}


def collect():
    """The whole picture: ranked rows plus the flags nobody should miss."""
    global LAST_CARRIED
    found, projects_root, machine = project_roots()
    carried = carrier_index(projects_root)
    rows = []
    skipped = []
    for name, path, is_hub in found:
        try:
            rows.extend(scan_project(name, path, is_hub, carried))
        except Exception as exc:              # a weird folder is reported, not fatal
            skipped.append("%s: %s" % (name, exc))
    LAST_CARRIED = (carriers.unclaimed(carried)
                    if (carriers is not None and carried) else [])
    # Ranking: touched descending, active lanes first, paused after. Lane name
    # breaks ties so two runs never disagree.
    rows.sort(key=lambda row: row["lane"].lower())
    rows.sort(key=lambda row: (not row["active"], -row["touched_ts"]))
    flags = {
        # first because it is the loudest: a folder copy behind a
        # carrier copy is how a hub reads a stale opener as current.
        "behind_carrier": [{"lane": row["lane"], "source": row["source"],
                            "sentence": row["stale_behind_carrier"]}
                           for row in rows if row["stale_behind_carrier"]],
        "judgment_unwalked": [{"lane": row["lane"],
                               "verb": row["judgment_unwalked"]}
                              for row in rows if row["judgment_unwalked"]],
        "carrier_notes": list((carried or {}).get("notes") or []),
        "stale": [row["lane"] for row in rows if row["fresh"] == "stale"],
        "no_opener": [row["lane"] for row in rows
                      if row["active"] and not row["opener"]],
        "missing_keys": [{"lane": row["lane"], "keys": row["missing"]}
                         for row in rows if row["opener"] and row["missing"]],
        "skipped": skipped,
        # loud: an install letter that names a scratch/ path points the
        # other machine's hub at a file it does not have.
        "scratch_install": scratch_install_letters(inbox_text()),
    }
    return {"generated": datetime.now().astimezone().isoformat(timespec="seconds"),
            "machine": machine, "projects_root": str(projects_root),
            "rows": rows, "flags": flags,
            "carried": [{"lane": item.get("lane"), "source": item.get("source"),
                         "file": item.get("file"),
                         "written": (item.get("header") or {}).get("written") or ""}
                        for item in LAST_CARRIED]}


# ── output: --table ───────────────────────────────────────────────────────

def scratch_install_line(item):
    """One plain sentence for an install letter that names a scratch/ path."""
    return ("INSTALL-FROM-SCRATCH: INBOX.md:%d (%s%s) names %s — scratch/ never "
            "crosses the brain (BQ-101), so the other machine cannot install from it; "
            "stage the file in harvest/<row-id>/ and send the letter again with that path"
            % (item["lineno"], item["date"],
               (" · to: " + item["to"]) if item.get("to") else "", item["path"]))


def flags_line(flags):
    parts = []
    # the scratch-install flags lead: a letter that sends a hub to a path it does not have is a
    # failed install waiting to happen on the other machine.
    for item in flags.get("scratch_install") or []:
        parts.append(scratch_install_line(item))
    # the carrier flags lead, because a stale copy read as current is
    # the failure the whole build exists to prevent.
    for item in flags.get("behind_carrier") or []:
        parts.append("STALE-BEHIND-CARRIER: %s — %s"
                     % (item["lane"], item["sentence"]))
    if flags.get("judgment_unwalked"):
        parts.append("model line not walked: " + ", ".join(
            '%s ("%s")' % (item["lane"], item["verb"])
            for item in flags["judgment_unwalked"]))
    if flags.get("carrier_notes"):
        parts.append("carriers: " + "; ".join(flags["carrier_notes"][:4]))
    if flags["stale"]:
        parts.append("stale openers: " + ", ".join(flags["stale"]))
    if flags["no_opener"]:
        parts.append("active lanes with no opener: "
                     + ", ".join(flags["no_opener"]))
    if flags["missing_keys"]:
        parts.append("missing header keys: " + "; ".join(
            "%s[%s]" % (item["lane"], ",".join(item["keys"]))
            for item in flags["missing_keys"]))
    if flags["skipped"]:
        parts.append("skipped: " + "; ".join(flags["skipped"]))
    return "flags: " + (" · ".join(parts) if parts else "none")


def print_table(data):
    header = ["lane", "source", "state", "touched", "on", "fresh",
              "depends_on", "notes"]
    lines = [header]
    for row in data["rows"]:
        # the warning is the first thing on the line, never a footnote.
        behind = row.get("stale_behind_carrier")
        notes = list(row["notes"])
        if behind:
            notes.insert(0, "STALE-BEHIND-CARRIER · %s" % behind)
        lines.append([
            ("⚠ " if behind else "") + row["lane"]
            + ("" if row["active"] else " (paused)"),
            row.get("source") or "none",
            row["state"],
            row["touched_day"],
            row["on"],
            row["fresh"],
            cut(row["depends_on"], 28),
            cut("; ".join(notes) or row["state_words"], 60),
        ])
    widths = [max(len(line[i]) for line in lines) for i in range(len(header))]
    for index, line in enumerate(lines):
        emit(" · ".join(cell.ljust(widths[i]) for i, cell in enumerate(line)
                        ).rstrip())
        if index == 0:
            emit("-+-".join("-" * width for width in widths))
    emit("")
    emit(flags_line(data["flags"]))


# ── output: --chat ────────────────────────────────────────────────────────

DOTS = {"green": "🟢", "amber": "🟡", "red": "🔴"}


def chat_lines(data):
    out = []
    # said before any lane, so the hub meets it first.
    letters = (data.get("flags") or {}).get("scratch_install") or []
    for item in letters[:3]:
        out.append("⚠ " + scratch_install_line(item))
    if len(letters) > 3:
        out.append("⚠ INSTALL-FROM-SCRATCH: +%d more letter(s) — see --table"
                   % (len(letters) - 3))
    for row in data["rows"]:
        if not row["active"]:
            continue
        gate = "🔒 " if row["gated"] else ""
        # a folder copy behind a carrier copy is said BEFORE the lane,
        # so the eye meets it first and the hub cannot hand a stale opener.
        behind = ("⚠ STALE-BEHIND-CARRIER · "
                  if row.get("stale_behind_carrier") else "")
        out.append("%s%s %s%s — %s — next: %s"
                   % (behind, DOTS.get(row["state"], "🟡"), gate, row["lane"],
                      row["where"], row["next_move"]))
    paused = []
    for row in data["rows"]:
        if not row["active"] and row["project"] not in paused:
            paused.append(row["project"])
    out.append("")
    if len(paused) > 8:
        shown = ", ".join(paused[:8]) + " and %d more" % (len(paused) - 8)
    else:
        shown = ", ".join(paused) if paused else "none"
    out.append("Paused: " + shown)
    out.append("")
    out.append('Say a project\'s name to expand it, or "all".')
    return out


# ── output: --expand ──────────────────────────────────────────────────────

def fence_for(body):
    longest = 0
    for run in re.findall(r"`+", body or ""):
        longest = max(longest, len(run))
    return "`" * max(3, longest + 1)


def folder_plate(path):
    """The location plate under a 📍 WHERE line: the machine mark on its own
    line, then the absolute folder path ALONE in a fence (a project name
    alone is not a destination). The mark
    and the label come from the registry, keyed by the name machine.json
    records; a machine the registry does not name gets a neutral mark and its
    own name, never a crash."""
    try:
        name = (json.loads(MACHINE_FILE.read_text()).get("name") or "").strip()
    except Exception:
        name = ""
    mark = "%s %s" % (_rg.machine_mark(reg(), name), _rg.machine_label(reg(), name))
    return [mark, "```", str(path), "```"]


def card_lines(row):
    card = row["card"]
    out = ["### %s%s" % ("🔒 " if row["gated"] else "", row["lane"])]
    if card.get("behind_carrier"):
        # right under the lane name, in full words, before anything the
        # reader might act on.
        out.append("⚠ **STALE-BEHIND-CARRIER** — %s" % card["behind_carrier"])
    where = card["where"] if card["where"] != "—" else ""
    story = " — ".join([part for part in (where, card["now"]) if part])
    out.append("**WHERE YOU ARE.** " + (story or "nothing recorded"))
    out.append("")
    out.append("**NEXT ACTIONS.**")
    if card["actions"]:
        for action in card["actions"]:
            out.append("- [ ] %s%s" % ("! " if action["urgent"] else "",
                                       action["text"]))
    else:
        out.append("- [ ] %s" % GENERIC_OPENER)
    out.append("")
    out.append("**CONTINUES ON.** " + card["continues_on"])
    out.append("**LIVES AT.** %s — %s" % (card["lives_at"], card["carrier"]))
    out.append("**LAST RECORDED.** " + card["last_recorded"])
    out.append("**DEPENDS ON.** " + card["depends_on"])
    out.append("")
    for note in card["notes"]:
        out.append("⚠ %s" % note)
    if card["handed"]:
        fence = fence_for(card["body"])
        where_line = "📍 WHERE: %s · %s" % (card["open_in"], card["model"])
        where_note = captured_where_note(card.get("captured"))
        if where_note:
            where_line += "   " + where_note
        out.append(where_line)
        out.extend(folder_plate(card["lives_at"]))
        out.append("source: %s · written %s"
                   % (card.get("source") or "folder",
                      card.get("written") or "not said"))
        out.append("📋 DO:")
        out.append(fence)
        out.append(card["body"])
        out.append(fence)
        out.append("✅ DONE WHEN: %s" % card["done_when"])
    else:
        out.append("open with: %s" % GENERIC_OPENER)
        # The `## Now` paragraph belongs here by the spec, but WHERE YOU ARE
        # above already carries it whenever there is one — printing it twice in
        # ten lines helps nobody, so it prints only when the card had none.
        if card["now"] and not story:
            out.append("")
            out.append(card["now"])
    out.append("")
    return out


def match_rows(data, target):
    if target.strip().lower() == "all":
        return data["rows"], None
    key = plain(target).lower()
    exact = [row for row in data["rows"] if row["lane"].lower() == key]
    if exact:
        return exact, None
    same = [row for row in data["rows"] if row["project"].lower() == key]
    if same:
        return same, None
    near = [row for row in data["rows"] if key in row["lane"].lower()
            or key in row["project"].lower()]
    if len(near) >= 1:
        return near, None
    names = sorted({row["lane"] for row in data["rows"]})
    return [], "no lane matches %r. Known lanes: %s" % (target,
                                                        ", ".join(names))


# ── output: --write-tree ────────────────────────────────────────────────

def auto_region(data):
    stamp = data["generated"]
    lines = [AUTO_START, ""]
    lines.append("# TREE — %s · %s" % (data["machine"], stamp))
    lines.append("")
    lines.append("Rebuilt by `tools/collect-openers.py --write-tree`. "
                 "Everything below the end marker is the hub's own writing "
                 "and is never touched.")
    lines.append("")
    lines.append("## Landing")
    lines.append("")
    lines.extend(chat_lines(data))
    lines.append("")
    lines.append("## Cards")
    lines.append("")
    for row in data["rows"]:
        lines.append('<!-- tree lane="%s" state="%s" touched="%s" next="%s" '
                     'depends_on="%s" opener="%s" fresh="%s" project="%s" '
                     'source="%s" -->'
                     % (attr(row["lane"]), attr(row["state"]),
                        attr(row["touched"] or ""), attr(row["next_owner"]),
                        attr(row["depends_on"]), attr(row["opener"] or "none"),
                        attr(row["fresh"]), attr(row["project"]),
                        attr(row.get("source") or "none")))
        lines.extend(card_lines(row))
        lines.extend(opener_block_lines(row))
    carried = list(LAST_CARRIED)
    if carried:
        lines.append("## Carried openers")
        lines.append("")
        lines.append("Openers riding a carrier that no project on this machine "
                     "could place — kept verbatim so the machine that owns the "
                     "lane still finds its own handoff here.")
        lines.append("")
        for item in carried:
            lines.append('<!-- tree lane="%s" opener="%s" project="%s" '
                         'source="%s" carried="yes" -->'
                         % (attr(item.get("lane") or "?"),
                            attr(item.get("file") or "none"),
                            attr(item.get("project") or ""),
                            attr(item.get("source") or "")))
            lines.append("### %s" % plain(item.get("lane") or "?"))
            lines.append("**CARRIED.** %s · written %s"
                         % (item.get("source") or "carrier",
                            carriers.written_words(item)))
            lines.append("")
            lines.extend(carriers.opener_block(
                item, fence_for, source=item.get("source") or "",
                written=(item.get("header") or {}).get("written") or ""))
            lines.append("")
    lines.append(AUTO_END)
    return "\n".join(lines) + "\n"


def opener_block_lines(row):
    """The lane's opener verbatim inside its own card — the header
    lines, the `---` line and the body, in one fenced `opener` block. That block
    is what the OTHER machine's collector reads back when the project folder is
    not there or is behind; the prompt above it is the human's to paste."""
    if carriers is None or not row.get("opener"):
        return []
    item = {"raw": row.get("_raw") or "", "header": row.get("header") or {},
            "body": row.get("body") or ""}
    if not (item["raw"] or item["header"] or item["body"]):
        return []
    return [""] + carriers.opener_block(item, fence_for,
                                        source=row.get("source") or "folder",
                                        written=row.get("written") or "")


def attr(text):
    """Safe inside an HTML comment attribute: no quotes, no comment closer."""
    return plain(text).replace('"', "'").replace("--", "-").replace(">", "›")


def write_tree(data, path=None):
    """Replace the auto region of TREE.md; keep everything else verbatim."""
    target = Path(path) if path else TREE_FILE
    try:
        old = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        old = ""
    region = auto_region(data)
    if AUTO_START in old and AUTO_END in old:
        head, rest = old.split(AUTO_START, 1)
        _, tail = rest.split(AUTO_END, 1)
        new = head + region.rstrip("\n") + tail
    else:
        # First run: the markers go at the TOP; whatever the hub wrote stays
        # underneath, untouched.
        new = region + ("\n" + old.lstrip("\n") if old.strip() else "")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(new)
    return target


# ── json ──────────────────────────────────────────────────────────────────

def jsonable(data):
    out = dict(data)
    out["rows"] = []
    for row in data["rows"]:
        clean = {key: value for key, value in row.items()
                 if not key.startswith("_")}
        out["rows"].append(clean)
    return out


# ── cli ───────────────────────────────────────────────────────────────────

USAGE = """collect-openers.py — the lanes' handoff openers, collected.

  --table            (default) one diagnostic line per lane, then the flags
  --chat             the landing list for the hub's first reply
  --expand <name>    the full card + the opener itself; <name> may be "all"
  --write-tree     rebuild the auto region of TREE.md
  --html             write tree.html, the styled page
  --json             every row, for orchestrator.py
  --help

An opener rides three carriers: the project folder, the brain's TREE.md
and a mounted `*-TX-*` payload's git bundle. The newest `written:` wins, every
row names the carrier it came from, and a folder copy behind a carrier copy is
flagged STALE-BEHIND-CARRIER on every surface.

COLLECT_OPENERS_ROOT=<dir> points the scan at a fixture root and skips the
orchestrator folder. Roots otherwise come from the machine record the path
resolver finds (tools/exo_paths.py).
COLLECT_OPENERS_VOLUMES=<dir>[<sep><dir>] treats each directory as a mounted
volume root, instead of asking the engine which volumes this machine has.
"""



# ── output: --html (the styled page, a calm reading page) ──
# Tokens and layout are the style's own.
# Accent rule kept: the gradient appears only in the masthead rule, the section
# numerals and keywords; amber is ONE status chip. The three state dots
# are the only other colour on the page.

import html as _html

# The page's two faces, IBM Plex Sans and IBM Plex Mono, come from the hub
# folder's own skin_v2_fonts.css (woff2 embedded; SIL Open Font License 1.1,
# fonts/OFL.txt). Nothing on the page is fetched from the network: a missing
# file only means the system fonts in --sans and --mono stand in.
HTML_FONTS_FILE = "skin_v2_fonts.css"

HTML_CSS = """
:root{--ground:#f4f6fa;--panel:#ffffff;--faint:#eaeef4;--ink:#0f1319;--ink-2:#39414e;--dim:#5b6472;
--line:#dee3ec;--line-2:#c9d1dd;--acc-a:#0a6ba8;--acc-b:#6f42ad;--acc-soft:rgba(10,107,168,.09);--acc-line:rgba(10,107,168,.34);
--amber-ink:#7a4a00;--amber-bg:#fff3d6;--amber-line:#e3a326;--code-bg:#0f1319;--code-ink:#dfe5ee;--code-line:#2a323d;
--ok:#1e7a3c;--wait:#b7791f;--bad:#c0392b;
--t-ink:#0f1319;--t-dim:rgba(15,19,25,.58);--t-line:rgba(15,19,25,.16);
--t-ready-hot:linear-gradient(145deg,#cfe9d6,#a9d4b5);--t-ready:linear-gradient(145deg,#e1f0e5,#c9e3d1);
--t-wait-hot:linear-gradient(145deg,#f6e2b6,#ecc98a);--t-wait:linear-gradient(145deg,#faedd0,#f1ddae);
--t-bad-hot:linear-gradient(145deg,#f2c9c2,#e5a49a);--t-bad:linear-gradient(145deg,#f7dedb,#efc5bf);
--t-cool:#e9edf2;--cool-ink:#5b6472;
--shadow:0 1px 2px rgba(16,24,40,.05),0 8px 24px -18px rgba(16,24,40,.35);
--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
/* identity hues (TREE-ART-SPEC §5.1) — minds and machines. The schemes never
   re-key these: a mind keeps its colour whatever the page is wearing. */
@@MIND_HUES_LIGHT@@
@@MACHINE_HUES_LIGHT@@--np-field:#0a6ba8;}
:root[data-theme="dark"]{--ground:#090d12;--panel:#10161d;--faint:#141b23;--ink:#dfe6ee;--ink-2:#b7c1cc;--dim:#7f8b99;--line:#1f2831;--line-2:#2b3642;
--acc-a:#4fc1ff;--acc-b:#8fb4ff;--acc-soft:rgba(79,193,255,.09);--acc-line:rgba(79,193,255,.32);--amber-ink:#ffb000;--amber-bg:rgba(255,176,0,.10);--amber-line:rgba(255,176,0,.45);
--code-bg:#070a0e;--code-ink:#dfe5ee;--code-line:#1f2730;--ok:#5fd38a;--wait:#ffb000;--bad:#ff6b6b;
--t-ink:#e6edf3;--t-dim:rgba(218,228,233,.52);--t-line:rgba(205,214,219,.16);
--t-ready-hot:linear-gradient(145deg,rgba(51,82,67,.95),rgba(25,48,39,.92));--t-ready:linear-gradient(145deg,rgba(46,72,61,.82),rgba(23,45,37,.82));
--t-wait-hot:linear-gradient(145deg,rgba(116,94,41,.82),rgba(53,45,24,.78));--t-wait:linear-gradient(145deg,rgba(88,74,38,.7),rgba(44,38,22,.72));
--t-bad-hot:linear-gradient(145deg,rgba(87,49,51,.92),rgba(49,29,34,.9));--t-bad:linear-gradient(145deg,rgba(75,48,49,.84),rgba(43,29,33,.85));
--t-cool:#10151b;--cool-ink:#7f8b99;
--shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -22px rgba(0,0,0,.9);
@@MIND_HUES_DARK@@
@@MACHINE_HUES_DARK@@--np-field:#163a5c;}
/* colour schemes — the base is data-theme (light/dark tokens above); a scheme re-keys the tokens to a Style Catalog style */
:root[data-scheme="noir"]{--ground:#0a0e14;--panel:#0f1520;--faint:#121a26;--ink:#e9eff3;--ink-2:#c9d3db;--dim:rgba(170,188,200,.84);--line:rgba(255,176,32,.16);--line-2:rgba(255,176,32,.3);
--acc-a:#ffb000;--acc-b:#ff6a00;--acc-soft:rgba(255,176,0,.09);--acc-line:rgba(255,176,0,.36);--amber-ink:#ffb000;--amber-bg:rgba(255,176,0,.10);--amber-line:rgba(255,176,0,.45);
--code-bg:#070a0e;--code-ink:#e9eff3;--code-line:#1c2532;--ok:#2fd57b;--wait:#ffb000;--bad:#ff4d5e;--t-ink:#e9eff3;--t-dim:rgba(233,239,243,.55);--t-line:rgba(255,176,32,.2);
--t-ready-hot:linear-gradient(145deg,rgba(31,122,76,.55),rgba(18,26,38,.95));--t-ready:linear-gradient(145deg,rgba(31,122,76,.35),rgba(18,26,38,.95));
--t-wait-hot:linear-gradient(145deg,rgba(255,176,0,.32),rgba(18,26,38,.95));--t-wait:linear-gradient(145deg,rgba(255,176,0,.2),rgba(18,26,38,.95));
--t-bad-hot:linear-gradient(145deg,rgba(255,77,94,.4),rgba(18,26,38,.95));--t-bad:linear-gradient(145deg,rgba(255,77,94,.26),rgba(18,26,38,.95));--t-cool:#0f1520;--cool-ink:rgba(170,188,200,.7)}
:root[data-scheme="instrument"]{--ground:#05080c;--panel:#14161A;--faint:#0d1115;--ink:#D6E9FF;--ink-2:#A3AAB5;--dim:#7f8b99;--line:#1c2229;--line-2:#2a323c;
--acc-a:#7FB0E8;--acc-b:#63B36F;--acc-soft:rgba(127,176,232,.09);--acc-line:rgba(127,176,232,.34);--amber-ink:#F2B705;--amber-bg:rgba(242,183,5,.10);--amber-line:rgba(242,183,5,.45);
--code-bg:#05080c;--code-ink:#D6E9FF;--code-line:#1c2229;--ok:#63B36F;--wait:#E8930C;--bad:#ff6b6b;--t-ink:#D6E9FF;--t-dim:rgba(214,233,255,.5);--t-line:rgba(214,233,255,.14);
--t-ready-hot:linear-gradient(145deg,rgba(99,179,111,.45),rgba(20,22,26,.96));--t-ready:linear-gradient(145deg,rgba(99,179,111,.28),rgba(20,22,26,.96));
--t-wait-hot:linear-gradient(145deg,rgba(242,183,5,.35),rgba(20,22,26,.96));--t-wait:linear-gradient(145deg,rgba(242,183,5,.22),rgba(20,22,26,.96));
--t-bad-hot:linear-gradient(145deg,rgba(255,107,107,.4),rgba(20,22,26,.96));--t-bad:linear-gradient(145deg,rgba(255,107,107,.26),rgba(20,22,26,.96));--t-cool:#0d1115;--cool-ink:#7f8b99}
:root[data-scheme="cream"]{--ground:#f1eee5;--panel:#fffdf8;--faint:#e9e5d9;--ink:#11110f;--ink-2:#3d3a34;--dim:#77736a;--line:#ddd8ca;--line-2:#bdb7aa;
--acc-a:#ff3b22;--acc-b:#1E5AA8;--acc-soft:rgba(255,59,34,.08);--acc-line:rgba(255,59,34,.34);--amber-ink:#7a4a00;--amber-bg:#f6ecd2;--amber-line:#d99a2b;
--code-bg:#11110f;--code-ink:#f1eee5;--code-line:#3d3a34;--ok:#1e7a3c;--wait:#b7791f;--bad:#c0392b;--t-ink:#11110f;--t-dim:rgba(17,17,15,.58);--t-line:rgba(17,17,15,.16);
--t-ready-hot:linear-gradient(145deg,#d9e6cf,#bdd3ad);--t-ready:linear-gradient(145deg,#e7efdf,#d3e1c6);--t-wait-hot:linear-gradient(145deg,#f3e2bb,#e9cc90);--t-wait:linear-gradient(145deg,#f7ecd3,#eedcb3);
--t-bad-hot:linear-gradient(145deg,#f2cdc3,#e6ab9d);--t-bad:linear-gradient(145deg,#f6e0da,#eec9c1);--t-cool:#e9e5d9;--cool-ink:#77736a}
:root[data-scheme="print"]{--ground:#F2F1EC;--panel:#FFFFFF;--faint:#e8e7e1;--ink:#101012;--ink-2:#3a3a3e;--dim:#85847E;--line:rgba(16,16,18,.18);--line-2:rgba(16,16,18,.32);
--acc-a:#2456A4;--acc-b:#D0021B;--acc-soft:rgba(36,86,164,.08);--acc-line:rgba(36,86,164,.34);--amber-ink:#8a5200;--amber-bg:#fdf1d8;--amber-line:#E8930C;
--code-bg:#101012;--code-ink:#F2F1EC;--code-line:#3a3a3e;--ok:#1e7a3c;--wait:#E8930C;--bad:#D0021B;--t-ink:#101012;--t-dim:rgba(16,16,18,.58);--t-line:rgba(16,16,18,.18);
--t-ready-hot:linear-gradient(145deg,#d4e4dc,#b3cfc0);--t-ready:linear-gradient(145deg,#e3eee8,#cfe0d6);--t-wait-hot:linear-gradient(145deg,#f5e1bd,#ecca92);--t-wait:linear-gradient(145deg,#f9edd6,#f0dcb5);
--t-bad-hot:linear-gradient(145deg,#f3c9c4,#e7a49c);--t-bad:linear-gradient(145deg,#f7dedb,#efc5c0);--t-cool:#e8e7e1;--cool-ink:#85847E}

*,*::before,*::after{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.55;margin:0;overflow-x:hidden;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px 72px;position:relative}
p{margin:0}
.plate{padding:34px 0 0}
.plate .over{font-family:var(--mono);font-size:.66rem;letter-spacing:.22em;text-transform:uppercase;color:var(--dim);margin-bottom:14px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.rule{border:0;height:1px;background:var(--line-2);margin:10px 0 0}
.head{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-top:14px}
h1{font-family:var(--mono);font-weight:600;font-size:clamp(1.4rem,4.2vw,2.4rem);letter-spacing:.05em;line-height:1.05;margin:0;color:var(--ink)}
.dek{font-size:.98rem;color:var(--ink-2);max-width:44em;margin-top:8px}
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
/* LIVE: every live session by name, under the counts (BQ-121) */
.livestrip{margin:10px 0 2px;font-family:var(--mono);font-size:.66rem;color:var(--dim);min-width:0}
.livestrip .lsh{display:block;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}
.livestrip ul{list-style:none;margin:0;padding:0;display:grid;gap:3px}
.livestrip li{display:flex;align-items:baseline;gap:12px;min-width:0}
.livestrip .lsr{flex:0 1 auto;min-width:0;display:flex;align-items:baseline;overflow:hidden;white-space:nowrap;font:inherit;letter-spacing:.04em;color:inherit;background:none;border:0;padding:0;cursor:pointer;text-align:left}
.livestrip .lst{min-width:0;overflow:hidden;text-overflow:ellipsis;font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:0;color:var(--ink)}
.livestrip .lsm{flex:none}
.livestrip .lsr:hover .lst{color:var(--acc-a)}
.livestrip .lso{flex:none;font:inherit;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--amber-ink);background:none;border:0;padding:0;cursor:pointer}
.livestrip .lso:hover{text-decoration:underline}
@media (max-width:640px){.livestrip .lsr{flex-wrap:wrap;white-space:normal}.livestrip .lst{white-space:nowrap;max-width:100%}}
.chip{display:inline-block;padding:5px 11px;border-radius:3px;background:var(--amber-bg);border:1px solid var(--amber-line);color:var(--amber-ink);font-weight:600;letter-spacing:.13em}
.tbtn{font:inherit;letter-spacing:inherit;text-transform:inherit;color:var(--dim);background:none;border:1px solid var(--line-2);border-radius:3px;padding:4px 9px;cursor:pointer}
.tbtn:hover,.tbtn.on{color:var(--acc-a);border-color:var(--acc-line)}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:14px 0 10px;font-family:var(--mono);font-size:.68rem;letter-spacing:.04em;color:var(--ink-2);align-items:center}
.legend span,.legend button{display:inline-flex;align-items:center;gap:7px}
.legend button,.cnt{font:inherit;letter-spacing:inherit;text-transform:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
.legend button:hover,.cnt:hover{color:var(--acc-a)}
.cnt{border-bottom:1px dotted var(--line-2)}
.cnt:hover{border-bottom-color:var(--acc-line)}
.cnt b{color:var(--ink);font-weight:600}
button.chip{font:inherit;letter-spacing:.13em;cursor:pointer}
.legend .k{color:var(--ink);font-weight:600}
.sw{width:14px;height:10px;border-radius:2px;display:inline-block;border:1px solid var(--t-line)}
.sw.ready{background:var(--t-ready-hot)}.sw.wait{background:var(--t-wait-hot)}.sw.bad{background:var(--t-bad-hot)}.sw.cool{background:var(--t-cool)}
.heatmap{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-auto-rows:minmax(150px,auto);grid-auto-flow:dense;gap:14px;position:relative;z-index:1}
@media (max-width:1100px){.heatmap{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media (max-width:720px){.heatmap{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tile{min-width:0;position:relative;z-index:2;overflow:hidden;display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-end;padding:38px 16px 38px;border:1px solid var(--t-line);border-radius:10px;text-align:left;color:var(--t-ink);background:var(--t-cool);box-shadow:inset 0 1px rgba(255,255,255,.06),0 14px 36px -24px rgba(0,0,0,.5);cursor:pointer;transition:transform .16s ease,border-color .16s ease,filter .16s ease;font:inherit;width:100%}
.tile::before{content:"";position:absolute;inset:0;opacity:.7;pointer-events:none;background:radial-gradient(circle at 86% 12%,rgba(255,255,255,.08),transparent 40%)}
.tile:hover,.tile:focus-visible{transform:translateY(-2px);border-color:var(--acc-a);filter:brightness(1.06);outline:none;z-index:2}
.tile.hero{grid-column:span 2;grid-row:span 2}
.tile.wide{grid-column:span 2}
.tile.ready.hot{background:var(--t-ready-hot)}.tile.ready{background:var(--t-ready)}
.tile.wait.hot{background:var(--t-wait-hot)}.tile.wait{background:var(--t-wait)}
.tile.bad.hot{background:var(--t-bad-hot)}.tile.bad{background:var(--t-bad)}
.tile .grp{position:absolute;top:13px;left:16px;right:108px;color:var(--t-dim);font-family:var(--mono);font-size:.6rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .st{position:absolute;top:13px;right:15px;font-family:var(--mono);font-size:.6rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--t-ink);opacity:.85;white-space:nowrap}
.tile .st.gt{color:var(--amber-ink)}
.tile .nm{position:relative;font-family:var(--sans);font-weight:700;font-size:clamp(17px,1.7vw,24px);line-height:1;letter-spacing:-.03em;overflow-wrap:anywhere;text-wrap:balance}
.tile.hero .nm{font-size:clamp(28px,3.2vw,46px);letter-spacing:-.045em}
.tile .wh{position:relative;margin-top:7px;color:var(--t-dim);font-size:.76rem;line-height:1.35;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.tile.wide .wh{-webkit-line-clamp:2}
.tile.hero .wh{font-size:.92rem;-webkit-line-clamp:3;color:var(--t-ink);opacity:.8}
.tile .nx{position:relative;margin-top:9px;font-family:var(--mono);font-size:.68rem;line-height:1.4;color:var(--t-ink);opacity:.92;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.tile.wide .nx,.tile.hero .nx{-webkit-line-clamp:2}
.tile .nx b{font-weight:600;margin-right:7px;color:var(--acc-a)}
.tile .ban{position:absolute;top:36px;left:16px;right:16px;display:grid;gap:7px;z-index:1}
.tile .ban .bl{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:.78rem;line-height:1.35;color:var(--t-dim)}
.tile .ban .bl b{font-family:var(--mono);font-weight:600;font-size:.56rem;letter-spacing:.14em;text-transform:uppercase;color:var(--acc-a);margin-right:8px}
.tile .ban .bl i{font-style:normal;font-family:var(--mono);font-size:.62rem;opacity:.8}
.tile .ban .bl.next{color:var(--t-ink);font-family:var(--mono);font-size:.7rem}
.tile .ban .bl.live{color:var(--acc-a);font-family:var(--mono);font-size:.66rem}
.tile.hero .ban{top:40px}
.tile.big{padding-top:150px}.tile.hero{padding-top:170px}.hubbar .tile{padding-top:140px}
.tile .kin{display:block;font-family:var(--mono);font-size:.52rem;letter-spacing:.14em;text-transform:uppercase;color:var(--cool-ink);opacity:.8;margin-bottom:6px}
.coolmap .tile .kin{display:none}
.tile .est{position:relative;margin-top:6px;font-family:var(--mono);font-size:.64rem;letter-spacing:.06em;color:var(--t-ink);opacity:.8}
.tile .ft{position:absolute;left:16px;right:16px;bottom:11px;display:flex;justify-content:space-between;align-items:center;gap:10px;font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--t-dim);white-space:nowrap}
.tile .ft .ages{overflow:hidden;text-overflow:ellipsis}
.tile .ft .pr{color:var(--amber-ink);font-weight:600;flex:none}
.tile:hover .ft .pr{text-decoration:underline}
.coolband{margin-top:34px;padding-top:18px;border-top:1px dashed var(--line-2)}
/* ── the crown: one head per project column (TREE-FALL-SPEC §2) ─────────── */
/* the crown and the fall take the whole window; the crown WRAPS into rows at
   that width (BQ-120), so every head is on screen at any size and none is
   reachable only by widening the window. Every other section keeps the page's
   own 1240px measure. */
.crown,.fall{margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);padding-left:20px;padding-right:20px}
.crown{position:relative;z-index:2;margin-top:22px;pointer-events:none}
/* a family's bracket stands over its heads in every row they sit in; the page
   places it (one per row), on the ground colour so a nerve passes behind it */
.fambar{position:absolute;inset:0;pointer-events:none;z-index:3}
.fambar .fam{position:absolute;height:15px;pointer-events:auto;cursor:pointer;background:var(--ground);font-family:var(--mono);font-size:.52rem;line-height:1.2;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;border:1px solid var(--line-2);border-bottom:0;border-radius:6px 6px 0 0;padding:2px 5px 1px}
.fambar .fam[hidden]{display:none}
/* the crown: as many 96px-or-wider heads as the width holds, then the next row;
   the left 58px stay the week labels' column, as they are in the fall below */
/* the crown and the gaps between its heads let a click through to the line beneath (BQ-356) */
.heads{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:10px 6px;padding-left:58px;pointer-events:none}
.crown.fams .heads{row-gap:18px;padding-top:17px}
.ph{position:relative;z-index:2;pointer-events:auto;height:78px;min-width:0;overflow:hidden;display:flex;flex-direction:column;justify-content:space-between;gap:2px;padding:6px 9px 5px;border:1px solid var(--t-line);border-top:3px solid var(--t-line);border-radius:8px;background:var(--t-cool);color:var(--t-ink);text-align:left;font:inherit;cursor:pointer;box-shadow:inset 0 1px rgba(255,255,255,.06),0 10px 26px -22px rgba(0,0,0,.5);transition:transform .16s ease,border-color .16s ease,filter .16s ease}
.ph::before{content:"";position:absolute;inset:0;opacity:.7;pointer-events:none;background:radial-gradient(circle at 86% 12%,rgba(255,255,255,.08),transparent 40%)}
.ph:hover,.ph:focus-visible{transform:translateY(-2px);filter:brightness(1.06);border-color:var(--acc-a);outline:none}
.ph.ready{background:var(--t-ready);border-top-color:var(--ok)}.ph.ready.hot{background:var(--t-ready-hot)}
.ph.wait{background:var(--t-wait);border-top-color:var(--wait)}.ph.wait.hot{background:var(--t-wait-hot)}
.ph.bad{background:var(--t-bad);border-top-color:var(--bad)}.ph.bad.hot{background:var(--t-bad-hot)}
.ph > *{position:relative}
.ph .eb{display:flex;align-items:center;gap:5px;font-family:var(--mono);font-size:.5rem;letter-spacing:.02em;text-transform:uppercase;color:var(--t-dim);white-space:nowrap;overflow:hidden}
.ph .eb .mc{padding:0 4px;border:1px solid currentColor;border-radius:3px;font-size:.48rem;letter-spacing:.12em}
.ph .eb .lv{font-weight:600}
.ph .eb .sx{margin-left:auto;color:var(--t-ink);opacity:.85;font-weight:600}
.ph .eb .sx.gt{color:var(--amber-ink)}
.ph .nm{font-family:var(--sans);font-weight:700;font-size:.84rem;letter-spacing:-.02em;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ph .chips{display:flex;gap:4px;overflow:hidden}
.ph .lc{font-family:var(--mono);font-size:.5rem;letter-spacing:.08em;text-transform:uppercase;border:1px solid var(--t-line);border-radius:3px;padding:0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:.92}
.ph .lc.ready{border-color:var(--ok)}.ph .lc.wait{border-color:var(--wait)}.ph .lc.bad{border-color:var(--bad)}
.ph .lc:hover{background:rgba(127,127,127,.2)}
.ph .fo{display:flex;justify-content:space-between;align-items:baseline;gap:5px;font-family:var(--mono);font-size:.54rem;letter-spacing:0;color:var(--t-dim);white-space:nowrap;overflow:hidden}
.ph .fo .u{color:var(--amber-ink);font-weight:600}
.ph .fo .pr{color:var(--amber-ink);font-weight:600;flex:none}
.ph:hover .fo .pr{text-decoration:underline}
/* a flex/grid item ignores the browser's own [hidden] rule: say it here */
.ph[hidden],.tile[hidden],.coolmap .tile[hidden]{display:none!important}
/* ── the fall: six week rows, the time axis (§3.1) ──────────────────────── */
.fall{position:relative;z-index:0;display:grid;grid-auto-rows:56px}
.fall .wk{position:relative}
.fall .wk::before{content:"";position:absolute;left:0;right:0;top:0;height:1px;background:currentColor;opacity:.12}
.fall .wl{position:absolute;left:0;top:3px;width:50px;font-family:var(--mono);font-size:.5rem;letter-spacing:.02em;text-transform:uppercase;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fall .wk.now .wl{color:var(--amber-ink)}
svg.lines rect.stream{fill:var(--amber-ink);fill-opacity:.55;stroke:none;pointer-events:auto}
svg.lines rect.stream.none{fill-opacity:.2}
svg.lines circle.sdot{fill:currentColor;fill-opacity:.95;pointer-events:auto}
svg.lines text.xn{font-family:var(--mono);font-size:7px;fill:var(--dim);letter-spacing:.04em}
svg.lines path.arc{fill:none;stroke:var(--acc-b);stroke-opacity:.6;stroke-width:1.3;pointer-events:stroke}
svg.lines circle.aend{fill:var(--acc-b);fill-opacity:.85}
svg.lines circle.aend.out{fill:none;stroke:var(--acc-b);stroke-opacity:.7;stroke-width:1}
.coolh{display:flex;align-items:baseline;gap:14px;margin:0 0 10px;font-family:var(--mono);font-size:.64rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.coolh b{color:var(--ink);font-weight:600}
.coolmap{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:6px;position:relative}
.coolband{position:relative}
.coolmap .tile{min-height:0;padding:9px 11px 8px;border-radius:6px;justify-content:flex-start;background:var(--t-cool);color:var(--cool-ink);box-shadow:none;border-color:var(--line);filter:none}
.coolmap .tile::before{display:none}
.coolmap .tile:hover{border-color:var(--acc-line);transform:none;color:var(--ink)}
.coolmap .tile .nm{font-size:.76rem;font-weight:600;letter-spacing:0;color:inherit}
.coolmap .tile .nx,.coolmap .tile .grp,.coolmap .tile .est,.coolmap .tile .st,.coolmap .tile .ft .pr{display:none}
.coolmap .tile .wh{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:.58rem;line-height:1.3;margin-top:4px;color:inherit;opacity:.8}
.coolmap .tile .ft{position:static;margin-top:5px;font-size:.56rem;color:inherit;opacity:.75}
.plate{position:relative}
.skyband::before{content:"";position:absolute;inset:0;pointer-events:none;background:none;z-index:0}
.plate.sky .skyband::before{background:var(--sky-veil),var(--sky-image) center/cover no-repeat}
:root{--sky-veil:linear-gradient(180deg,rgba(244,246,250,.55),rgba(244,246,250,.92) 78%,var(--ground))}
:root[data-theme="dark"]{--sky-veil:linear-gradient(180deg,rgba(9,13,18,.35),rgba(9,13,18,.9) 78%,var(--ground))}
.plate > *{position:relative;z-index:1}
.plate .skyband{z-index:0}
/* the band is sized to the sky's own 1600×348 so `meet` never crops a label */
.skyband{position:relative;height:clamp(140px,20vw,284px);margin:6px -20px 0;overflow:hidden;border-radius:0 0 18px 18px}
.skyfield{position:absolute;left:0;right:0;top:0;width:100%;height:100%;z-index:1;pointer-events:none;color:var(--ink)}
.skyfield circle,.skyfield path.skill,.skyfield path.tick,.skyfield path.drop,.skyfield rect.dos{pointer-events:auto}
.skyfield circle{fill:currentColor}
.skyfield circle.today{fill:var(--amber-ink)}
.skyfield text{font-family:var(--mono);font-size:15px;letter-spacing:.08em;fill:currentColor;opacity:.8;text-transform:uppercase}
.skyfield text.sk{opacity:.85}
.skyfield path.skill{fill:currentColor;opacity:.55}
.skyfield rect.dos{fill:currentColor;opacity:.7}
.skyfield path.horizon{fill:none;stroke:currentColor;stroke-opacity:.18;stroke-width:1}
.skyfield path.link{fill:none;stroke:currentColor;stroke-opacity:.22;stroke-width:.7;pointer-events:auto}
.skyfield path.skill{fill:currentColor;opacity:.55}
.skyfield path.skill-line{fill:none;stroke:currentColor;stroke-opacity:.28;stroke-width:.9;pointer-events:auto}
.skyfield path.tick{stroke:currentColor;stroke-opacity:.35;stroke-width:1.2}
.skyfield path.tick.new{stroke:var(--amber-ink);stroke-opacity:.9;stroke-width:1.6}
.skyfield path.tick.eng{stroke-opacity:.16;stroke-width:1}
.skyfield rect.dos.empty{fill:none;stroke:currentColor;stroke-width:1;opacity:.5}
@@CODEX_SKY@@.skycap{font-family:var(--mono);font-size:.74rem;letter-spacing:.02em;line-height:1.5;color:var(--ink-2);margin:8px 0 0;max-width:86em}.skycap .key{color:var(--ink);opacity:.85}
.skycap b{color:var(--ink);font-weight:600}
svg.lines path.root.machine{stroke-width:3.2;stroke-opacity:.55}
svg.lines path.root.here{stroke-opacity:.95;stroke-width:4}
svg.lines path.root.mind{stroke-width:1.2;stroke-opacity:.35}
svg.lines path.root.live{stroke:var(--acc-a);stroke-opacity:.95;stroke-width:2.2}
svg.lines path.root.mind.live{stroke-dasharray:4 5;animation:flow 1.2s linear infinite}
.root.live{border-color:var(--acc-line);box-shadow:0 0 0 1px var(--acc-soft)}
.root .rv .lv{color:var(--acc-a);font-weight:600}
.root .rv .ear{color:var(--ink);font-weight:600}
.root .rv .gd{color:var(--ink);font-weight:600;cursor:pointer}
.hubbar{margin-top:0;position:relative;padding:22px 0 0}
.hubbar::before{content:"";position:absolute;left:50%;top:0;width:3px;height:22px;margin-left:-1px;background:var(--amber-ink);opacity:.6}
.hubbar .tile .grp::before{content:"● "}
.rootsec{position:relative;margin-top:0;padding-top:46px}
.rootsec::before{content:"";position:absolute;left:50%;top:0;width:3px;height:46px;margin-left:-1px;background:var(--amber-ink);opacity:.6}
.rootsec .rh{display:flex;align-items:baseline;gap:14px;margin:0 0 10px;font-family:var(--mono);font-size:.64rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.rootsec .rh b{color:var(--ink);font-weight:600}
.rootgrid{display:grid;gap:40px;position:relative}.rootrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.rootrow.machines{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}.rootrow .rl{grid-column:1/-1;font-family:var(--mono);font-size:.58rem;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);margin:0 0 -4px}
.root{position:relative;z-index:2;background:var(--faint);border:1px solid var(--line-2);border-radius:10px;padding:12px 13px 11px;min-width:0}
.root.here{border-color:var(--amber-line)}
.root .rk{font-family:var(--mono);font-size:.58rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.root .rn{display:block;font-family:var(--sans);font-weight:700;font-size:1.05rem;letter-spacing:-.02em;margin-top:2px;color:var(--ink)}
.root .rv{display:block;font-family:var(--mono);font-size:.64rem;letter-spacing:.06em;color:var(--ink-2);margin-top:5px;overflow-wrap:anywhere}
.root.dim{opacity:.55}
svg.lines path.root{stroke:var(--amber-ink);stroke-opacity:.45;stroke-width:1.6}
.dormant{margin-top:30px;padding-top:16px;border-top:1px dashed var(--line-2);position:relative}
@media (max-width:820px){.hubbar::before,.rootsec::before{left:18px}}
.hubbar .tile{min-height:0;padding:46px 18px 34px;border-radius:10px;border-color:var(--amber-line)}.hubbar .tile .ban{position:static;margin:0 0 12px}.hubbar .tile .est{position:static;display:block;margin:6px 0 0}
.hubbar .tile .nm{font-size:clamp(20px,2.2vw,30px)}
.hubbar .tile .grp::before{content:"● ";color:var(--amber-ink)}
svg.lines path.trunk{stroke:var(--amber-ink);stroke-opacity:.5;stroke-width:3}
.tile .grp .mail{color:var(--amber-ink);margin-left:8px}
.tile .grp .live{color:var(--acc-a);margin-left:8px;font-weight:600}
.hubbar .tile .grp .mail{font-size:.66rem}.tile .grp .mc{margin-left:8px;padding:1px 6px;border:1px solid var(--t-line);border-radius:3px;font-size:.54rem;letter-spacing:.14em;opacity:.9}
svg.lines path.gate{stroke:var(--acc-a);stroke-opacity:.7;stroke-width:1.6;stroke-dasharray:5 4}
svg.lines text{font-family:var(--mono);font-size:10px;fill:var(--amber-ink)}
@keyframes flow{to{stroke-dashoffset:-32}}
svg.lines{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;overflow:visible}
svg.lines path{fill:none;stroke:var(--acc-a);stroke-width:1.4;stroke-opacity:.42;stroke-linecap:round}
svg.lines circle{fill:var(--acc-a);fill-opacity:.7}
.lines.off{display:none}
.chart{margin-top:40px}
.chart h2{font-family:var(--mono);font-weight:600;font-size:.9rem;letter-spacing:.12em;text-transform:uppercase;margin:0 0 4px}
.chart .sub{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin-bottom:12px}
.chart .quiet{font-family:var(--mono);font-size:.7rem;letter-spacing:.08em;color:var(--dim);border:1px dashed var(--line-2);border-radius:8px;padding:14px 16px}
.chart svg{width:100%;height:auto;display:block;font-family:var(--mono)}
.chart .lab{fill:var(--ink);font-size:11px;font-weight:600}
.chart .val{fill:var(--dim);font-size:10px}
.chart .axis{stroke:var(--line-2);stroke-width:1}
.chart [data-mark]{cursor:pointer}
.chart .bar.ready{fill:var(--ok);fill-opacity:.7}.chart .bar.wait{fill:var(--wait);fill-opacity:.75}.chart .bar.bad{fill:var(--bad);fill-opacity:.7}.chart .bar.total{fill:var(--acc-a);fill-opacity:.55}
.chart .conn{stroke:var(--dim);stroke-width:1;stroke-dasharray:3 3;stroke-opacity:.7}
.detail{position:fixed;inset:0;background:var(--ground);overflow:auto;z-index:10}
.detail[hidden]{display:none}
.dpanel{max-width:1060px;margin:0 auto;padding:30px 20px 96px}
.dbar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-family:var(--mono);font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);border-bottom:1px solid var(--line);padding-bottom:14px}
.back,.jump{font:inherit;letter-spacing:inherit;text-transform:inherit;color:var(--acc-a);background:none;border:1px solid var(--acc-line);border-radius:3px;padding:6px 11px;cursor:pointer}
.back:hover,.jump:hover{background:var(--acc-soft)}
.jump{color:var(--amber-ink);border-color:var(--amber-line)}
.dbar .dst{display:inline-flex;align-items:center;gap:8px}
.dbar .dwhen{margin-left:auto}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;background:var(--wait);flex:none}
.dot.g{background:var(--ok)}.dot.r{background:var(--bad)}.dot.a{background:var(--wait)}
.dname{margin:28px 0 10px;font-family:var(--sans);font-weight:700;font-size:clamp(1.7rem,5vw,2.9rem);letter-spacing:-.03em;line-height:1.05}
.dwhere{font-size:clamp(1.05rem,2.4vw,1.25rem);color:var(--ink-2);max-width:40em;line-height:1.5}
.dsec{padding:44px 0 0}
.sec{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
.sec > *{min-width:0}
@media (min-width:900px){.sec{grid-template-columns:84px minmax(0,1fr);gap:0 32px}.sec > .body{grid-column:2}}
.smark{font-family:var(--mono);font-size:.95rem;font-weight:600;letter-spacing:.08em;color:var(--acc-a);background:linear-gradient(120deg,var(--acc-a),var(--acc-b));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;padding-top:.35rem}
h2{font-family:var(--mono);font-weight:600;font-size:clamp(1.12rem,3.2vw,1.44rem);letter-spacing:.05em;text-transform:uppercase;margin:0 0 6px}
.prose{max-width:66ch;font-size:1rem;color:var(--ink-2)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:20px}
.fact{background:var(--panel);border:1.5px solid var(--line-2);border-radius:8px;padding:12px 14px;min-width:0}
.fact .fl{font-family:var(--mono);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim)}
.fact .fv{display:block;margin-top:4px;font-size:.9rem;color:var(--ink);overflow-wrap:anywhere}
.fact .fv.m{font-family:var(--mono);font-size:.78rem}
.note{margin-top:14px;font-size:.9rem;color:var(--amber-ink)}
.steps{list-style:none;margin:0;padding:0;display:grid;gap:12px;counter-reset:s}
.steps li{display:grid;grid-template-columns:40px minmax(0,1fr);gap:16px;align-items:start;background:var(--panel);border:1.5px solid var(--line-2);border-radius:10px;padding:16px 18px;box-shadow:var(--shadow)}
.steps li > div{min-width:0}
.steps li::before{counter-increment:s;content:counter(s);font-family:var(--mono);font-size:.9rem;font-weight:600;color:var(--acc-a);border:1px solid var(--acc-line);border-radius:6px;text-align:center;padding:4px 0}
.steps li.u{border-left:4px solid var(--wait)}
.steps li.open{border-left:4px solid var(--acc-a)}
.steps .sh{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);display:block;margin-bottom:4px}
.steps .sh b{color:var(--acc-a);font-weight:600}
.steps .st{font-size:.95rem;color:var(--ink);overflow-wrap:anywhere;display:block}
.steps pre{margin:10px 0 0;background:var(--code-bg);border:1px solid var(--code-line);border-radius:8px;padding:16px;overflow-x:auto;max-width:100%;color:var(--code-ink);font-family:var(--mono);font-size:.78rem;line-height:1.62;white-space:pre-wrap;word-break:break-word}
.copy{margin-top:10px;font-family:var(--mono);font-size:.66rem;letter-spacing:.16em;text-transform:uppercase;color:var(--ink);background:var(--acc-soft);border:1px solid var(--acc-line);border-radius:3px;padding:6px 11px;cursor:pointer}
.copy:hover{background:var(--faint)}.copy.done{color:var(--acc-a)}
a.copy.launch{display:inline-block;margin-right:8px;text-decoration:none;color:var(--acc-a);border-color:var(--acc-a)}
.steps .tag{display:block;font-family:var(--mono);font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin-top:8px}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line)}
footer .fr{height:2px;border:0;margin:0 0 16px;background:linear-gradient(90deg,var(--acc-a),var(--acc-b));opacity:.7;border-radius:2px}
footer p{font-family:var(--mono);font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--dim);line-height:1.9}
/* ── the sky's axes and glyphs (TREE-ART-SPEC §4 v3) ───────────────────── */
.skyfield .s{fill:currentColor;pointer-events:auto}
.skyfield .s.today{fill:var(--amber-ink)}
.skyfield circle.ref{fill:none;stroke:currentColor;stroke-width:.9}
.skyfield circle.ref.today{stroke:var(--amber-ink);fill:none}
.skyfield circle.cent{fill:none;stroke:none;pointer-events:none}
/* the five bands: their names at the left edge — the axis, and nothing else
   (the dashed floors were tested and cut: they told the viewer nothing) */
.skyfield text.bl{font-size:13px;opacity:.75;letter-spacing:.1em}
/* LESSONS: one dot per dated journal line, and its drop into law */
.skyfield circle.jd{fill:currentColor;opacity:.5;pointer-events:auto}
.skyfield circle.jd.today{fill:var(--amber-ink);opacity:.95}
.skyfield path.drop{fill:none;stroke:currentColor;stroke-opacity:.25;stroke-width:.8;pointer-events:auto}
/* ── identity marks: small and quiet, never a fill (§5.2) ──────────────── */
@@MIND_CLASSES@@@@MACHINE_CLASSES@@.tile .grp .mc{border-color:currentColor}
.tile .grp .lv{margin-left:8px;font-weight:600;white-space:nowrap}
.tile .ban .bl.live .lv{margin-left:0;margin-right:10px}
@@MACHINE_ROOTS@@.root.mind.live{border-top:2px solid currentColor}
.root.mind.live .rv .lv{color:currentColor}
.legend .kk{font-weight:600;letter-spacing:.13em}
/* ── nerves: one per live session (§2) ────────────────────────────────── */
svg.lines path.nerve{stroke-width:1.4;stroke-opacity:.85;stroke-dasharray:6 10;animation:flow 3.2s linear infinite;pointer-events:stroke}
svg.lines path.nerve.glow{stroke-width:4;stroke-opacity:.18;stroke-dasharray:none;animation:none;pointer-events:none}
svg.lines path.nerve.still{animation:none}
svg.lines circle.nend{fill:currentColor;fill-opacity:.95}
svg.lines circle.halo{fill:none;stroke-width:1;stroke-opacity:.5;pointer-events:none}
svg.lines circle.halo.star{stroke-opacity:.35}
svg.lines circle.halo.none{pointer-events:all}
svg.lines path.stem{stroke:var(--amber-ink);stroke-opacity:.25;stroke-width:1;animation:none}
/* ── the collar: nameplate · ring · the hub's state (§3.1) ─────────────── */
.plate3{display:grid;grid-template-columns:minmax(0,1fr) 96px minmax(0,1fr);align-items:stretch;gap:0;min-height:150px}
.nameplate{display:flex;flex-direction:column;justify-content:center;gap:9px;padding:0 18px 0 0;min-width:0}
.npf{background:var(--np-field);border-radius:9px;padding:15px 18px;display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;box-shadow:var(--shadow)}
.npf .stn{font-family:var(--sans);font-weight:700;font-size:clamp(24px,2.8vw,38px);letter-spacing:.18em;line-height:1;color:#f2f7ff}
.npf .dsg{font-family:var(--mono);font-size:.66rem;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:#ffb000;display:grid;gap:4px}
.npbeat{font-family:var(--mono);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
.collarmid{position:relative;display:flex;align-items:center;justify-content:center}
.collarmid::before{content:"";position:absolute;left:50%;top:0;bottom:0;width:3px;margin-left:-1px;background:var(--amber-ink);opacity:.6}
.ring{position:relative;z-index:2;display:block;width:34px;height:34px;overflow:visible}
.ring circle{fill:var(--ground);stroke:var(--amber-ink);stroke-width:1.6;opacity:.5}
.ring.on circle{opacity:1;animation:breathe 2.4s ease-in-out infinite}
.ring text{font-family:var(--mono);font-size:11px;fill:var(--amber-ink);text-anchor:middle}
@keyframes breathe{0%,100%{opacity:.7}50%{opacity:1}}
.hubstate{padding-left:18px;display:flex;flex-direction:column;justify-content:center;min-width:0}
.hubstate .tile{width:100%}
/* ── the head reflows around the stem (§3.3) ───────────────────────────── */
.capwrap{display:block}
.head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;flex-wrap:wrap;margin-top:14px}
.head .hl{min-width:0;flex:1 1 460px}
.head .hrt{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px 10px}
.head .legend{margin:12px 0 0}
@media (max-width:820px){.head .hrt{justify-content:flex-start}.plate3{grid-template-columns:36px minmax(0,1fr);gap:12px}.nameplate{grid-column:2;grid-row:1;padding:0}.hubstate{grid-column:2;grid-row:2;padding:0}.collarmid{grid-column:1;grid-row:1/3}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
/* ── the inspector: one panel, one place, for every mark (BQ-011 §1) ────── */
/* placed by the script at the point that was clicked — never a fixed corner */
#inspector{position:fixed;left:0;top:0;width:380px;max-width:calc(100vw - 24px);max-height:70vh;overflow:auto;overflow:visible;z-index:11;
background:var(--panel);border:1px solid var(--line-2);border-left:3px solid var(--acc-a);border-radius:10px;box-shadow:var(--shadow);padding:13px 16px 16px;color:var(--ink)}
#inspector .iscroll{max-height:calc(70vh - 30px);overflow:auto}
/* the connector: a 1 px line from the panel's edge to the mark it answers for */
#inspector .icaret{position:absolute;width:15px;height:1px;background:var(--acc-line);pointer-events:none}
#inspector .icaret.left{right:100%}
#inspector .icaret.right{left:100%}
#inspector .icaret::after{content:"";position:absolute;top:-2px;width:5px;height:5px;border-radius:50%;background:var(--acc-a)}
#inspector .icaret.left::after{left:-2px}
#inspector .icaret.right::after{right:-2px}
#inspector[hidden]{display:none!important}
#inspector .ihead{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
#inspector .ikind{font-family:var(--sans);font-weight:700;font-size:.98rem;line-height:1.25;letter-spacing:-.01em;color:var(--ink)}
#inspector .ix{font:inherit;font-size:1.15rem;line-height:1;color:var(--dim);background:none;border:0;padding:0 2px;cursor:pointer;flex:none}
#inspector .ix:hover{color:var(--acc-a)}
#inspector .ibytes{display:grid;grid-template-columns:minmax(0,88px) minmax(0,1fr);gap:5px 12px;margin:12px 0 0;font-family:var(--mono);font-size:.7rem;line-height:1.5}
#inspector dt{color:var(--dim);font-size:.58rem;letter-spacing:.12em;text-transform:uppercase;padding-top:3px;overflow-wrap:anywhere}
#inspector dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere;white-space:pre-wrap}
/* the foot of a card: the machine facts, after what the thing is about (BQ-123) */
#inspector .ifoot{margin-top:10px;padding-top:8px;border-top:1px solid var(--line);font-size:.62rem;opacity:.85}
#inspector .ifoot dt{font-size:.52rem}
#inspector .iact{display:inline-block;margin-top:14px;font:inherit;font-family:var(--mono);font-size:.64rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--acc-a);background:var(--acc-soft);border:1px solid var(--acc-line);border-radius:3px;padding:7px 12px;cursor:pointer;text-decoration:none}
#inspector .iact:hover{background:var(--faint)}
#inspector .iact + .iact{margin-left:8px}
@media (max-width:820px){#inspector{max-height:56vh}#inspector .iscroll{max-height:calc(56vh - 30px)}}
/* the click targets: never smaller than the eye needs, never drawn (§1) */
svg.lines .hitl,.skyfield .hitl{fill:none;stroke:transparent;pointer-events:stroke;animation:none}
svg.lines .hita,.skyfield .hita{fill:none;stroke:none;pointer-events:all}
svg.lines [data-mark],.skyfield [data-mark],.skyfield text[data-mark]{cursor:pointer}
.skyfield text[data-mark],.skyfield path[data-mark],.skyfield rect[data-mark],.skyfield circle[data-mark]{pointer-events:auto}
svg.lines circle.halo{pointer-events:stroke}
.mk-flash{outline:2px solid var(--amber-line);outline-offset:2px}
svg.lines .mk-flash,.skyfield .mk-flash{stroke:var(--amber-ink);stroke-width:3;stroke-opacity:1;outline:none}
/* one-click start, on the face itself (BQ-011 §4) */
.tile .launch,.ph .launch{flex:none;display:inline-flex;align-items:center;min-height:22px;padding:3px 9px;border-radius:3px;
font-family:var(--mono);font-size:.6rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;text-decoration:none;cursor:pointer;
color:var(--t-ink);background:rgba(127,127,127,.14);border:1px solid var(--t-line)}
.tile .launch:hover,.ph .launch:hover{border-color:var(--acc-a);color:var(--acc-a)}
.tile .launch.done,.ph .launch.done{color:var(--acc-a)}
.ph .launch{font-size:.54rem;padding:2px 6px}
/* a head says its launch words where it has the room (BQ-120); a narrow one
   shows the glyph, and the words stay the link's name and its title */
.ph{container-type:inline-size}
.ph .launch[data-g]{font-size:0}
.ph .launch[data-g]::before{content:attr(data-g);font-size:.54rem}
@container (min-width:150px){.ph .launch[data-g]{font-size:.54rem}.ph .launch[data-g]::before{content:none}}
.ph .fo > span:first-child{overflow:hidden;text-overflow:ellipsis}
.coolmap .tile .launch{font-size:.54rem;padding:2px 6px}
"""

HTML_JS = r"""
(function(){
  var root=document.documentElement, key='tree-theme', skey='tree-scheme', lkey='tree-lines', nkey='tree-nerves';
  var SCHEMES={'@@DARK_ID@@':'dark','@@LIGHT_ID@@':'light','noir':'dark','instrument':'dark','cream':'light','print':'light'};
  var scheme=null; try{scheme=localStorage.getItem(skey); if(!scheme){var t=localStorage.getItem(key); scheme=t==='light'?'@@LIGHT_ID@@':null;}}catch(e){}
  if(!SCHEMES[scheme]) scheme='@@DARK_ID@@';
  function applyScheme(name){root.setAttribute('data-theme',SCHEMES[name]); root.setAttribute('data-scheme',name); try{localStorage.setItem(skey,name);}catch(e){}}
  applyScheme(scheme);
  var sb=document.getElementById('sbtn');
  if(sb){sb.value=scheme; sb.addEventListener('change',function(){applyScheme(SCHEMES[sb.value]?sb.value:'@@DARK_ID@@');});}
  var LANES=[]; try{LANES=JSON.parse(document.getElementById('lanes').textContent);}catch(e){}
  var STATE={green:'ready',amber:'waiting on you',red:'needs attention'};
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function fact(l,v,mono){return '<div class="fact"><span class="fl">'+esc(l)+'</span><span class="fv'+(mono?' m':'')+'">'+esc(v)+'</span></div>';}
  var detail=document.getElementById('detail'), panel=document.getElementById('dpanel');
  function open(i,toPrompt){
    var r=LANES[i]; if(!r) return;
    var h='<div class="dbar"><button class="back" type="button">&larr; all lanes</button>'
      +'<span class="dst"><span class="dot '+esc(r.dot)+'"></span>'+esc(STATE[r.state]||r.state)+(r.gated?' &middot; gated':'')+'</span>'
      +'<span>&#8987; open '+esc(r.age)+' &middot; &#9201; idle '+esc(r.idle)+'</span>'
      +'<button class="jump" type="button">&#9654; startup prompt</button>'
      +'<span class="dwhen">touched '+esc(r.touched)+'</span></div>';
    h+='<h1 class="dname">'+esc(r.lane)+'</h1><p class="dwhere">'+esc(r.where)+'</p>';
    h+='<section class="dsec"><div class="sec"><div class="smark">01</div><div class="body"><h2>Summary</h2>';
    h+='<p class="prose">'+esc(r.now||'Nothing recorded in STATUS yet.')+'</p><div class="facts">';
    h+=fact('State',(STATE[r.state]||r.state)+' — '+(r.reasons||'clean'));
    if(r.remaining!=null){h+=fact('Work left','≈ '+r.remaining+' sitting'+(r.remaining==1?'':'s')+(r.due?' · due '+r.due:''));}
    h+=fact('Continues on',r.continues_on)+fact('Lives at',r.lives_at,true)+fact('Carrier',r.carrier);
    h+=fact('Last recorded',r.last_recorded,true)+fact('Depends on',r.depends_on);
    if(r.why){h+=fact('Not in the fall',r.why);}
    h+='</div>';
    (r.notes||[]).forEach(function(n){h+='<p class="note">&#9888; '+esc(n)+'</p>';});
    h+='</div></div></section>';
    h+='<section class="dsec" id="todo"><div class="sec"><div class="smark">02</div><div class="body"><h2>What to do</h2><ol class="steps">';
    if(!r.actions.length){h+='<li><div><span class="sh">to do</span><span class="st">Nothing open in STATUS. Read it and decide the next move.</span></div></li>';}
    r.actions.forEach(function(a){h+='<li class="'+(a.urgent?'u':'')+'"><div><span class="sh">'+(a.urgent?'urgent':'to do')+'</span><span class="st">'+esc(a.text)+'</span></div></li>';});
    h+='<li class="open" id="prompt"><div><span class="sh"><b>start the session</b>'+(r.handed?' &middot; '+esc(r.open_in)+' &middot; '+esc(r.model):' &middot; no opener on file yet')+'</span>';
    h+='<span class="st">Open a fresh session pointed at <code>'+esc(r.folder)+'</code>'+(r.handed?' and paste this as its first message.':' and paste this.')+'</span>';
    h+='<pre id="op'+i+'">'+esc(r.body)+'</pre>';
    if(r.launch){h+='<a class="copy launch" href="'+esc(r.launch)+'" data-for="op'+i+'">&#9654; Launch session</a>';}
    h+='<button class="copy" type="button" data-for="op'+i+'">Copy startup prompt</button>';
    if(r.codex_note){h+='<span class="tag">'+esc(r.codex_note)+'</span>';}
    if(r.handed){h+='<span class="tag">&#10004; done when: '+esc(r.done_when)+'</span>';}
    h+='</div></li></ol></div></div></section>';
    panel.innerHTML=h; detail.hidden=false; document.body.style.overflow='hidden';
    if(location.hash!=='#lane='+i) history.replaceState(null,'','#lane='+i);
    if(toPrompt){var el=document.getElementById('prompt'); if(el) el.scrollIntoView({block:'start'});} else {detail.scrollTop=0;}
    panel.querySelector('.back').focus({preventScroll:true});
  }
  function close(){detail.hidden=true; document.body.style.overflow=''; history.replaceState(null,'',location.pathname);}
  // ── THE INSPECTOR (BQ-011 §1): one table, one panel, one listener ───────
  // Every mark on the page carries data-mark="<id>"; MARKS holds what that id
  // is, the real bytes behind it, and at most one action. Nothing here knows
  // what KIND of thing it is showing — that is the whole point.
  var MARKS={}; try{MARKS=JSON.parse(document.getElementById('marks').textContent);}catch(e){}
  var LISTS={}; try{LISTS=JSON.parse(document.getElementById('lists').textContent);}catch(e){}
  var insp=document.getElementById('inspector'), markOn='', markAt=null;
  // THE PANEL OPENS WHERE THE EYE IS (BQ-011b §1): beside the point that was
  // clicked, flipped to the side and the way up that fit, always inside the
  // window with a 12 px margin, and joined to its mark by a 1 px connector.
  function placeAt(x,y){
    if(!insp||insp.hidden) return;
    markAt={x:x,y:y};
    var W=window.innerWidth||1024, H=window.innerHeight||768, M=12, GAP=16;
    insp.style.left='0px'; insp.style.top='0px';
    var b=insp.getBoundingClientRect();
    var w=Math.ceil(b.width||380), h=Math.ceil(b.height||240);   // whole pixels, so the 12px margin really holds
    var right=(x+GAP+w+M<=W), left=right?(x+GAP):(x-GAP-w);
    if(left<M) left=M;
    if(left+w+M>W) left=Math.max(M,W-w-M);
    var top=y-14;
    if(top+h+M>H) top=y-h+14;                    // flip upward
    if(top<M) top=M;
    if(top+h+M>H) top=Math.max(M,H-h-M);
    insp.style.left=Math.round(left)+'px';
    insp.style.top=Math.round(top)+'px';
    var c=insp.querySelector('.icaret');
    if(c){
      // the connector is drawn only when it really reaches the mark: the panel
      // beside the point, and the point inside the panel's own span
      var near=Math.abs((right?left:left+w)-x)<40&&y>=top-2&&y<=top+h+2;
      c.className='icaret '+(right?'left':'right');
      c.style.top=Math.round(Math.max(8,Math.min(h-8,y-top)))+'px';
      c.style.display=near?'':'none';
    }
  }
  function anchorOf(id,ev){
    if(ev&&ev.clientX!=null&&(ev.clientX||ev.clientY)) return {x:ev.clientX,y:ev.clientY};
    var el=document.querySelector('[data-mark="'+q(id)+'"]');
    if(el){var b=el.getBoundingClientRect();
      if(b.width||b.height) return {x:b.left+b.width/2,y:b.top+b.height/2};}
    return {x:(window.innerWidth||1024)/2,y:(window.innerHeight||768)/3};
  }
  function flash(sel){
    if(!sel) return;
    var hit=document.querySelectorAll(sel);
    hit.forEach(function(el){el.classList.add('mk-flash');});
    setTimeout(function(){hit.forEach(function(el){el.classList.remove('mk-flash');});},2000);
  }
  function showMark(id,ev){
    var m=MARKS[id]; if(!m||!insp) return false;
    var h='<i class="icaret"></i><div class="ihead"><span class="ikind">'+esc(m.kind)+'</span>'
      +'<button class="ix" type="button" aria-label="close">&times;</button></div><div class="iscroll"><dl class="ibytes">';
    // BQ-150: a history first, time first, oldest at the top; the whole line on
    // hover, its source on a click (srcOf) — in the rows' own dt/dd, no new style
    var L=(typeof m.list==='string')?LISTS[m.list]:m.list;
    if(L&&L.items&&L.items.length){
      if(L.earlier) h+='<dt>'+esc(L.earlier+' earlier')+'</dt><dd></dd>';
      L.items.forEach(function(it,k){var nw=(k===L.items.length-1&&/ · now$/.test(it.at||''));
        h+='<dt>'+esc(it.at)+'</dt><dd tabindex="0"'+(nw?' data-now="1"':'')+' title="'+esc(it.full||it.w)
        +'" data-src="'+esc(it.src)+'">'+esc(it.w)+'</dd>';});
    }
    (m.bytes||[]).forEach(function(b){h+='<dt>'+esc(b[0])+'</dt><dd>'+esc(b[1])+'</dd>';});
    h+='</dl>';
    if(m.foot&&m.foot.length){h+='<dl class="ibytes ifoot">';
      m.foot.forEach(function(b){h+='<dt>'+esc(b[0])+'</dt><dd>'+esc(b[1])+'</dd>';}); h+='</dl>';}
    var a=m.action;
    if(a&&a.href){h+='<a class="iact" href="'+esc(a.href)+'">'+esc(a.label)+'</a>';}
    else if(a&&a.lane!=null){h+='<button class="iact" type="button" data-lane="'+(+a.lane)+'">'+esc(a.label)+'</button>';}
    else if(a&&a.copy!=null){h+='<button class="iact" type="button" data-copy="1">'+esc(a.label)+'</button>'
      +'<pre id="icopy" hidden>'+esc(a.copy)+'</pre>';}
    h+='</div>';
    insp.innerHTML=h; insp.hidden=false; markOn=id;
    var at=anchorOf(id,ev); placeAt(at.x,at.y);
    // BQ-150 (the hub's ruling): a history opens SCROLLED TO NOW — the newest
    // line in view at the foot of the panel, the older ones above it, reached
    // by scrolling up; a list that opens on old lines reads as old news
    var nwd=insp.querySelector('dd[data-now]'), scr=insp.querySelector('.iscroll');
    if(nwd&&scr){var gap=nwd.getBoundingClientRect().bottom-scr.getBoundingClientRect().bottom;
      if(gap>0) scr.scrollTop+=Math.ceil(gap);}
    try{sessionStorage.setItem('tree-mark',id);}catch(e){}
    if(m.highlight) flash(m.highlight);
    return true;
  }
  // a line of a history answers a click with where it came from — the
  // transcript and its line, or the INBOX line — and a second click folds it
  function srcOf(dd){
    var nx=dd.nextElementSibling;
    if(nx&&nx.hasAttribute('data-src-of')){var nd=nx.nextElementSibling; nx.remove();
      if(nd&&nd.hasAttribute('data-src-of')) nd.remove(); return;}
    dd.insertAdjacentHTML('afterend','<dt data-src-of="1">source</dt><dd data-src-of="1">'
      +esc(dd.getAttribute('data-src'))+'</dd>');
  }
  function hideMark(){if(!insp) return; insp.hidden=true; insp.innerHTML=''; markOn=''; markAt=null;
    try{sessionStorage.removeItem('tree-mark');}catch(e){}}
  function copyFrom(pre,btn){
    if(!pre) return;
    var was=btn.textContent;
    function ok(){btn.textContent='Copied';btn.classList.add('done');setTimeout(function(){btn.textContent=was;btn.classList.remove('done');},1600);}
    function fb(){var rg=document.createRange();rg.selectNodeContents(pre);var s=window.getSelection();s.removeAllRanges();s.addRange(rg);try{document.execCommand('copy');ok();}catch(e){}}
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(pre.textContent).then(ok,fb);}else{fb();}
  }
  document.addEventListener('click',function(e){
    if(insp&&!insp.hidden&&insp.contains(e.target)){          // the panel's own buttons
      var sd=e.target.closest('dd[data-src]'); if(sd){srcOf(sd);return;}
      var b=e.target.closest('button'); if(!b) return;
      if(b.classList.contains('ix')){hideMark();return;}
      if(b.hasAttribute('data-lane')){var i=+b.getAttribute('data-lane'); hideMark(); open(i,false); return;}
      if(b.hasAttribute('data-copy')){copyFrom(document.getElementById('icopy'),b); return;}
      return;
    }
    // ▶ open on a LIVE line goes to the lane that session works in (BQ-121)
    var lo=e.target.closest('.lso');
    if(lo){hideMark(); open(+lo.getAttribute('data-open'),false); return;}
    // the LIVE count is the strip's anchor: it brings the strip into view, and
    // its own answer lights the strip up
    var jp=e.target.closest('[data-jump]');
    if(jp){var tg=document.getElementById(jp.getAttribute('data-jump'));
      if(tg&&tg.scrollIntoView) tg.scrollIntoView({block:'nearest',behavior:'smooth'});}
    var el=e.target.closest('[data-mark]');
    if(el&&showMark(el.getAttribute('data-mark'),e)) return;
    if(insp&&!insp.hidden) hideMark();
  });
  // A head opens its project's first lane; a lane chip opens its own (§2.3/§2.4).
  document.querySelectorAll('.ph').forEach(function(t){
    t.addEventListener('click',function(e){
      var c=e.target.closest('.lc');
      if(c){e.stopPropagation(); open(+c.getAttribute('data-i'),false); return;}
      open(+t.getAttribute('data-i'), !!e.target.closest('.pr'));});
    t.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();open(+t.getAttribute('data-i'),false);}});
  });
  document.querySelectorAll('.tile').forEach(function(t){
    t.addEventListener('click',function(e){open(+t.getAttribute('data-i'), !!e.target.closest('.pr'));});
    t.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();open(+t.getAttribute('data-i'),false);}});
  });
  detail.addEventListener('click',function(e){
    // a.launch rides the same handler: it copies the opener AND follows its
    // href, so the new session opens with the paste already on the clipboard.
    var b=e.target.closest('button,a.launch'); if(!b) return;
    if(b.classList.contains('back')){close();return;}
    if(b.classList.contains('jump')){var el=document.getElementById('prompt'); if(el) el.scrollIntoView({block:'start',behavior:'smooth'});return;}
    if(b.classList.contains('copy')){
      var pre=document.getElementById(b.getAttribute('data-for')); if(!pre) return;
      var was=b.textContent;
      function ok(){b.textContent='Copied';b.classList.add('done');setTimeout(function(){b.textContent=was;b.classList.remove('done');},1600);}
      function fb(){var rg=document.createRange();rg.selectNodeContents(pre);var s=window.getSelection();s.removeAllRanges();s.addRange(rg);try{document.execCommand('copy');ok();}catch(e){}}
      if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(pre.textContent).then(ok,fb);}else{fb();}
    }
  });
  document.addEventListener('keydown',function(e){
    var sd=(e.key==='Enter'||e.key===' ')&&insp&&!insp.hidden&&document.activeElement;
    if(sd&&sd.matches&&sd.matches('dd[data-src]')&&insp.contains(sd)){e.preventDefault();srcOf(sd);return;}
    if(e.key!=='Escape') return;
    if(!detail.hidden){close();return;}
    if(insp&&!insp.hidden) hideMark();
  });
  // The launch link on a face starts the session; it must not ALSO open the
  // detail view underneath it (the .lc pattern above).
  document.querySelectorAll('.tile .launch,.ph .launch').forEach(function(a){
    a.addEventListener('click',function(e){
      e.stopPropagation();
      var i=a.getAttribute('data-copy-lane');
      if(i==null) return;                      // a real link: let it open
      e.preventDefault();
      var r=LANES[+i]; if(!r) return;
      var pre=document.createElement('pre');
      pre.textContent=r.body; pre.style.position='fixed'; pre.style.left='-9999px';
      document.body.appendChild(pre);
      copyFrom(pre,a);
      setTimeout(function(){if(pre.parentNode) pre.parentNode.removeChild(pre);},1500);
    });
  });
  // ── THE FALL (TREE-FALL-SPEC §3): weeks down, one stream per project ─────
  // Streams = that week's commits · dots = the sessions that ran · arcs = the
  // notes one project sent another that week · nerves = the live sessions.
  var FALL={weeks:[],cols:[],arcs:[],gates:[]};
  try{FALL=JSON.parse(document.getElementById('fall-data').textContent);}catch(e){}
  var svg=document.getElementById('lines'), wrap=document.querySelector('.wrap'), lb=document.getElementById('lbtn'), nb=document.getElementById('nbtn');
  var linesOn=true; try{linesOn=localStorage.getItem(lkey)!=='off';}catch(e){}
  var nervesOn=true; try{nervesOn=localStorage.getItem(nkey)!=='off';}catch(e){}
  var MORD=@@MIND_SORT@@;
  var LAB=52;                                // the week labels' margin
  function hue(m){return 'var(--m-'+String(m||'claude').toLowerCase()+', var(--acc-a))';}
  function box(el,W){var r=el.getBoundingClientRect();return {l:r.left-W.left,r:r.right-W.left,t:r.top-W.top,b:r.bottom-W.top,x:r.left-W.left+r.width/2,y:r.top-W.top+r.height/2,w:r.width,h:r.height};}
  function q(s){return String(s||'').replace(/["\\]/g,'');}
  function dm(id){return ' data-mark="'+q(id)+'"';}      // the one attribute (§1)
  function n1(v){return (Math.round(v*10)/10);}
  // THE CROWN WRAPS (BQ-120): the grid breaks the heads into rows at the
  // window's width, so every head is on the page at any size — nothing is
  // hidden and nothing is swapped. What is left to place by hand is each
  // family's bracket: one over every row its heads stand in, the first the
  // page's own and the rest its copies, redrawn on every resize.
  var heads=[].slice.call(document.querySelectorAll('.ph'));
  function layout(){
    var fb=document.querySelector('.fambar'); if(!fb) return;
    [].slice.call(fb.querySelectorAll('.fam.more')).forEach(function(f){f.parentNode.removeChild(f);});
    var FB=fb.getBoundingClientRect();
    [].slice.call(fb.querySelectorAll('.fam')).forEach(function(f){
      var from=+f.getAttribute('data-from'), n=+f.getAttribute('data-n'), segs=[], cur=null;
      for(var i=from;i<from+n&&i<heads.length;i++){
        var b=heads[i].getBoundingClientRect();
        if(!cur||Math.abs(b.top-cur.t)>2){cur={t:b.top,l:b.left,r:b.right}; segs.push(cur);}
        else{cur.l=Math.min(cur.l,b.left); cur.r=Math.max(cur.r,b.right);}
      }
      if(!segs.length){f.hidden=true; return;}
      segs.forEach(function(sg,k){
        var el=f;
        if(k>0){el=f.cloneNode(true); el.classList.add('more'); el.setAttribute('aria-hidden','true'); fb.appendChild(el);}
        el.style.left=Math.round(sg.l-FB.left)+'px'; el.style.width=Math.round(sg.r-sg.l)+'px';
        el.style.top=Math.round(sg.t-FB.top-16)+'px'; el.hidden=false;
      });
    });
  }
  function draw(){
    if(!svg||!wrap) return;
    layout();
    var W=wrap.getBoundingClientRect(); svg.setAttribute('viewBox','0 0 '+W.width+' '+W.height);
    var out='', nout='';
    var fall=document.getElementById('fall'); if(!fall){svg.innerHTML='';return;}
    var F=box(fall,W);
    var rows=[].slice.call(fall.querySelectorAll('.wk')).map(function(w){return box(w,W);});
    // the fall's own edges: never left of the week labels, never past its padding
    var wlEl=fall.querySelector('.wl');
    var fL=wlEl?(box(wlEl,W).r+8):(F.l+LAB+2), fR=F.r-24, fC=(fL+fR)/2;
    var ringEl=document.getElementById('ring'), plateEl=document.querySelector('.plate3');
    var R=ringEl?box(ringEl,W):null, P=plateEl?box(plateEl,W):null;
    var sx=R?R.x:(F.l+F.r)/2, rx=sx, ryT=R?R.t:F.b, ryB=R?R.b:F.b, ryC=R?R.y:F.b;
    var plateB=P?P.b:ryB, plateT=P?P.t:F.b;
    var laneY=(F.b+plateT)/2;                    // the 14px lane under the fall (§3.5)
    var band=document.querySelector('.skyband'); var skyB=band?box(band,W).b:0;
    // where each column stands, measured from its own head. When the crown
    // wraps, one grid column holds a head per row; each keeps a SLOT of its own
    // inside that column, side by side in row order (the top row's leftmost),
    // so every stream runs under its own head's span (BQ-120).
    var col=[], maxc=1, stack={};
    heads.forEach(function(h,i){var hb=box(h,W), k=Math.round(hb.l); (stack[k]=stack[k]||[]).push({i:i,hb:hb});});
    Object.keys(stack).forEach(function(k){
      var g=stack[k]; g.sort(function(a,b){return a.hb.t-b.hb.t;});
      var n=g.length, low=g[n-1].hb.b;
      g.forEach(function(e,r){
        var sw=e.hb.w/n, c=FALL.cols[e.i]||{};
        col[e.i]={x:e.hb.l+sw*(r+.5),b:e.hb.b,w:sw,c:c,low:low,gx:e.hb.l-3};
        FALL.weeks.forEach(function(wk){var m=(c.commits||{})[wk.key]||0; if(m>maxc) maxc=m;});
      });
    });
    function cx(i){return (i!=null&&col[i])?col[i].x:null;}
    // ── streams and session dots, row by row ────────────────────────────────
    col.forEach(function(cc,i){
      if(!cc) return;
      var c=cc.c, half=cc.w/2;
      rows.forEach(function(rb,wi){
        var wk=FALL.weeks[wi]; if(!wk) return;
        var n=(c.commits||{})[wk.key]||0;
        var w=c.repo?Math.min(1+13*Math.sqrt(n/maxc),Math.max(1,cc.w*.4)):1;   // a narrow slot keeps a narrow stream
        var ttl=c.repo?(c.name+' · week of '+wk.label+' · '+n+' commit'+(n==1?'':'s')):(c.name+' · no git history');
        var smk=dm('stream:'+i+':'+wk.key), stt='<title>'+esc(ttl)+'</title>';
        out+='<rect class="stream'+(n?'':' none')+'"'+smk+' x="'+n1(cc.x-w/2)+'" y="'+n1(rb.t)+'" width="'+n1(w)+'" height="'+n1(rb.h)+'">'+stt+'</rect>';
        out+='<rect class="hita"'+smk+' x="'+n1(cc.x-5)+'" y="'+n1(rb.t)+'" width="10" height="'+n1(rb.h)+'">'+stt+'</rect>';
        var ss=((c.sessions||{})[wk.key]||[]).slice();
        if(!ss.length) return;
        ss.sort(function(a,b){var ma=(MORD[a.mind]==null?9:MORD[a.mind]), mb=(MORD[b.mind]==null?9:MORD[b.mind]);
          return ma!==mb?ma-mb:(a.id<b.id?-1:(a.id>b.id?1:0));});
        var per={}; ss.forEach(function(s){(per[s.mind]=per[s.mind]||[]).push(s.id);});
        // a slot too narrow for a row of dots stacks them down its right side
        var shown=Math.min(6,ss.length), up=half<38, step=up?6:Math.max(5,Math.min(8,(half-12)/6)), dy=rb.t+14;
        for(var k=0;k<shown;k++){
          var s=ss[k], dx=up?(cc.x+Math.min(10,half-1)):(cc.x+10+step*k), dyk=up?(rb.t+8+step*k):dy, ids=per[s.mind]||[];
          var lab=s.mind+' · '+ids.length+' session'+(ids.length==1?'':'s')+' this week · …'+ids.join(' …');
          if(k===shown-1&&ss.length>shown) lab=ss.length+' sessions this week · '+lab;
          var dmk=dm('sdot:'+i+':'+wk.key+':'+k), dtt='<title>'+esc(lab)+'</title>';
          out+='<circle class="sdot"'+dmk+' style="fill:'+hue(s.mind)+'" cx="'+n1(dx)+'" cy="'+n1(dyk)+'" r="2.5">'+dtt+'</circle>';
          out+='<circle class="hita"'+dmk+' cx="'+n1(dx)+'" cy="'+n1(dyk)+'" r="4">'+dtt+'</circle>';
        }
        if(ss.length>shown){                     // the sixth dot carries the rest
          var lx=up?(cc.x+Math.min(10,half-1)+6):(cc.x+10+step*(shown-1)+6), ly=up?(rb.t+8+step*(shown-1)+2.5):(dy+2.5);
          var room=cc.x+half+(up?0:24);          // clear of the next stream
          if(lx+16<room) out+='<text class="xn"'+dm('sdot:'+i+':'+wk.key+':'+(shown-1))+' x="'+n1(lx)+'" y="'+n1(ly)+'">×'+ss.length+'</text>';
        }
      });
    });
    // ── arcs: one per (pair, week) — the notes that crossed (§3.4) ──────────
    var wIndex={}; FALL.weeks.forEach(function(w,i){wIndex[w.key]=i;});
    function arc(a,b,rb,cls,title,wide,mark){
      // the anchor line sits low in the row, the control point on the row rule:
      // a quadratic's own apex is then (y+2·ctl+y)/4 = 22 px up — inside this
      // row, never into the row above (§3.4)
      var y=rb.t+44, ctl=rb.t;
      var ax=cx(a), bx=cx(b), outer=false;
      if(ax==null&&bx==null) return;
      if(ax==null){ax=(bx<fC)?fL:fR; outer=true;}
      if(bx==null){bx=(ax<fC)?fL:fR; outer=true;}
      if(Math.abs(ax-bx)<1) return;
      var amk=mark?dm(mark):'', att='<title>'+esc(title)+'</title>';
      var dd='M'+n1(ax)+','+n1(y)+' Q'+n1((ax+bx)/2)+','+n1(ctl)+' '+n1(bx)+','+n1(y);
      out+='<path class="'+cls+'"'+amk+' style="stroke-width:'+(wide?2:1.3)+'" d="'+dd+'">'+att+'</path>';
      out+='<path class="hitl"'+amk+' style="stroke-width:11" d="'+dd+'">'+att+'</path>';
      out+='<circle class="aend'+(outer&&cx(b)==null?' out':'')+'"'+amk+' cx="'+n1(bx)+'" cy="'+n1(y)+'" r="'+(outer&&cx(b)==null?2.6:2.2)+'">'+att+'</circle>';
    }
    if(linesOn){
      (FALL.arcs||[]).forEach(function(a,ai){
        var wi=wIndex[a.w]; if(wi==null||!rows[wi]) return;
        var t=a.mon+' · '+a.an+' → '+a.bn+' · '+a.text;
        if(a.n>1) t=a.n+' notes · '+t;
        arc(a.a,a.b,rows[wi],'arc',t,a.n>1,'arc:'+ai);
      });
      (FALL.gates||[]).forEach(function(g,gi){
        if(!rows[0]) return; arc(g.a,g.b,rows[0],'gate',g.text,false,'gate:'+gi);
      });
    }
    // ── the roots: taproots from the ring out to each machine card ──────────
    var mach=[], mpos={}, mtop=null;
    document.querySelectorAll('.rootgrid .root.machine').forEach(function(rt){
      var b=box(rt,W); mach.push({el:rt,b:b,name:(rt.getAttribute('data-mch')||'').toUpperCase()});
      if(mtop===null||b.t<mtop) mtop=b.t;
    });
    var fanY=(mtop===null)?plateB+20:Math.max(plateB+8,Math.min(plateB+40,mtop-10));
    mach.forEach(function(m){
      mpos[m.name]=m.b;
      var k='root machine'+(m.el.classList.contains('here')?' here':'')+(m.el.classList.contains('live')?' live':'');
      var rmk=dm('root:'+m.name.toLowerCase()), rtt='<title>'+esc(m.name)+'</title>';
      var rd='M'+n1(rx)+','+n1(ryB)+' L'+n1(rx)+','+n1(plateB)
          +' C'+n1(rx)+','+n1(plateB+(m.b.t-plateB)*.55)+' '+n1(m.b.x)+','+n1(m.b.t-(m.b.t-plateB)*.45)
          +' '+n1(m.b.x)+','+n1(m.b.t);
      out+='<path class="'+k+'"'+rmk+' d="'+rd+'">'+rtt+'</path>';
      out+='<path class="hitl"'+rmk+' style="stroke-width:10" d="'+rd+'">'+rtt+'</path>';
    });
    // ── nerves: mind card → machine → ring → the lane → up its own column ───
    var list=nervesOn?nerveList():[], nerved={}, drawn=0;
    list.forEach(function(n,k){
      var s=n.s, mind=String(s.mind||'CLAUDE').toUpperCase(), c=hue(mind);
      var mb=mpos[String(s.machine||'').toUpperCase()]; if(!mb) return;
      nerved[mind]=1; drawn++;
      var mindEl=document.querySelector('.rootgrid .root.mind[data-mind="'+q(mind)+'"]');
      var mins=(s.minutes==null?0:+s.minutes);
      var dur=(mins<2)?'1.6s':'3.2s', fade=(mins>=8)?';opacity:.4':'';
      var ttxt=(s.about?s.about+' · ':'')+mind+' on '+(s.machine||'?')+' · '+n.project+' · '+mins+' min ago'+(s.model?' · '+s.model:'')+' · …'+(s.id||'');
      var t='<title>'+esc(ttxt)+'</title>', nmk=dm('nerve:'+n.i+':'+(s.id||''));
      var d='';
      if(mindEl){var mn=box(mindEl,W);   // a. the root leg, an S-curve in the empty gap
        d+='M'+n1(mn.x)+','+n1(mn.t)+' C'+n1(mn.x)+','+n1(mn.t-(mn.t-mb.b)*.55)
          +' '+n1(mb.x)+','+n1(mb.b+(mn.t-mb.b)*.55)+' '+n1(mb.x)+','+n1(mb.b)+' ';
      }
      // b. up into the fan zone, then the collar's empty column · c. the ring
      d+='M'+n1(mb.x)+','+n1(mb.t)+' L'+n1(mb.x)+','+n1(fanY)
        +' C'+n1(mb.x)+','+n1(fanY-(fanY-plateB)*.6)+' '+n1(rx)+','+n1(plateB+(fanY-plateB)*.45)
        +' '+n1(rx)+','+n1(plateB)
        +' L'+n1(rx)+','+n1(ryB)+' L'+n1(rx)+','+n1(ryT);
      // d. the lane under the fall, then straight up its own column (§3.5)
      var ci=(n.col==null?-1:n.col), cc=(ci>=0)?col[ci]:null;
      var off=laneOff(k), tipx, tipy, hub=n.hub&&!cc;
      if(cc){
        var nx=cc.x+off, r=8, sg=(nx>=rx)?1:-1, under=(cc.low>cc.b+1), top=under?(cc.low+6):cc.b;
        if(Math.abs(nx-rx)<2*r){ d+=' L'+n1(nx)+','+n1(laneY)+' L'+n1(nx)+','+n1(top); }
        else{ d+=' L'+n1(rx)+','+n1(laneY+r)+' Q'+n1(rx)+','+n1(laneY)+' '+n1(rx+sg*r)+','+n1(laneY)
                +' L'+n1(nx-sg*r)+','+n1(laneY)+' Q'+n1(nx)+','+n1(laneY)+' '+n1(nx)+','+n1(laneY-r)
                +' L'+n1(nx)+','+n1(top); }
        tipx=nx; tipy=cc.b;
        if(under){                         // heads stand below it in its column (BQ-120)
          d+=' L'+n1(cc.gx)+','+n1(top)+' L'+n1(cc.gx)+','+n1(cc.b-12);
          tipx=cc.gx; tipy=cc.b-12;         // it plugs in beside its head, in the gutter
        }
      }else if(hub){                       // the hub works at the collar itself
        var tl=document.querySelector('.hubstate .tile');
        var tb=tl?box(tl,W):null;
        if(tb){var bd='M'+n1(rx)+','+n1(ryC)+' L'+n1(tb.l)+','+n1(ryC);
          nout+='<path class="nerve glow" style="stroke:'+c+fade+'" d="'+bd+'"/>';
          nout+='<path class="nerve"'+nmk+' style="stroke:'+c+';animation-duration:'+dur+fade+'" d="'+bd+'">'+t+'</path>';
          nout+='<path class="hitl"'+nmk+' style="stroke-width:7" d="'+bd+'">'+t+'</path>';
          nout+='<circle class="nend"'+nmk+' style="fill:'+c+'" cx="'+n1(tb.l)+'" cy="'+n1(ryC)+'" r="2"/>';
          nout+='<circle class="hita"'+nmk+' cx="'+n1(tb.l)+'" cy="'+n1(ryC)+'" r="5">'+t+'</circle>';}
        tipx=null;
      }else{                               // no column in the fall: it stops in the lane and says where it works
        var ex=rx+off*3;
        d+=' L'+n1(ex)+','+n1(laneY);
        tipx=ex; tipy=laneY;
        t='<title>'+esc(ttxt+' · not in the fall')+'</title>';
      }
      nout+='<path class="nerve glow" style="stroke:'+c+fade+'" d="'+d+'"/>';
      nout+='<path class="nerve"'+nmk+' style="stroke:'+c+';animation-duration:'+dur+fade+'" d="'+d+'">'+t+'</path>';
      nout+='<path class="hitl"'+nmk+' style="stroke-width:7" d="'+d+'">'+t+'</path>';
      if(tipx!=null){nout+='<circle class="nend"'+nmk+' style="fill:'+c+'" cx="'+n1(tipx)+'" cy="'+n1(tipy)+'" r="2"/>';
        nout+='<circle class="hita"'+nmk+' cx="'+n1(tipx)+'" cy="'+n1(tipy)+'" r="5">'+t+'</circle>';}
      // the sky lights by colour from the same live data — no line through the head (§3.5)
      var cent=n.key?document.querySelector('.skyfield circle.cent[data-key="'+q(n.key)+'"]'):null;
      if(cent){var cb=box(cent,W);
        nout+='<circle class="halo"'+nmk+' style="stroke:'+c+'" cx="'+n1(cb.x)+'" cy="'+n1(cb.y)+'" r="'+n1(Math.max(3,cb.w/2))+'"><title>'+esc(n.project+' · '+mind)+'</title></circle>';
        var stars=document.querySelectorAll('.skyfield .s[data-key="'+q(n.key)+'"]');
        if(stars.length<=40){stars.forEach(function(st){var sbx=box(st,W);
          nout+='<circle class="halo star" style="stroke:'+c+'" cx="'+n1(sbx.x)+'" cy="'+n1(sbx.y)+'" r="'+n1(Math.max(sbx.w,sbx.h)/2+2.5)+'"/>';});}
      }
    });
    // A mind that stamped itself up but is working nowhere the pulse can see
    // keeps its quiet root: a stamp says "I am up", a nerve "I am working here".
    document.querySelectorAll('.rootgrid .root.mind.live').forEach(function(rt){
      var m=(rt.getAttribute('data-mind')||'').toUpperCase(); if(nerved[m]) return;
      var mn=box(rt,W), from=mpos[(rt.getAttribute('data-on')||'').toUpperCase()]||{x:rx,b:ryB};
      var mmk=dm('mind:'+m), mtt='<title>'+esc(m)+'</title>';
      var md='M'+n1(from.x)+','+n1(from.b)
          +' C'+n1(from.x)+','+n1(from.b+(mn.t-from.b)*.6)+' '+n1(mn.x)+','+n1(mn.t-(mn.t-from.b)*.4)
          +' '+n1(mn.x)+','+n1(mn.t);
      out+='<path class="root mind live"'+mmk+' d="'+md+'">'+mtt+'</path>';
      out+='<path class="hitl"'+mmk+' style="stroke-width:10" d="'+md+'">'+mtt+'</path>';
    });
    svg.innerHTML=out+nout;
    // a toggle says its own state, in words (BQ-011 §3)
    if(lb){lb.classList.toggle('on',linesOn); lb.setAttribute('aria-pressed',linesOn?'true':'false');
      lb.textContent='◠ '+(linesOn?'hide notes':'show notes');}
    if(nb){nb.classList.toggle('on',nervesOn); nb.setAttribute('aria-pressed',nervesOn?'true':'false');
      nb.textContent='● nerves '+(nervesOn?'on':'off');}
    var rn=document.getElementById('ringn'); if(rn) rn.textContent=drawn?String(drawn):'';
    if(ringEl) ringEl.classList.toggle('on',drawn>0);
    if(location.search.indexOf('check=1')>=0){skycheck();crosscheck();hitcheck();}
  }
  function nerveList(){
    // One entry per live session the pulse saw — the lanes JSON carries them,
    // each claimed by exactly one lane so a folder with two lanes never doubles.
    var list=[];
    for(var i=0;i<LANES.length;i++){
      var r=LANES[i], ss=r.sessions||[];
      for(var j=0;j<ss.length;j++) list.push({s:ss[j],i:i,col:(r.col==null?null:r.col),hub:!!r.hub,key:r.key||'',project:r.project||r.lane});
    }
    list.sort(function(a,b){                       // by mind, then short id: stable lanes
      var ma=(MORD[a.s.mind]==null?9:MORD[a.s.mind]), mb=(MORD[b.s.mind]==null?9:MORD[b.s.mind]);
      if(ma!==mb) return ma-mb;
      return a.s.id<b.s.id?-1:(a.s.id>b.s.id?1:0);
    });
    return list;
  }
  function laneOff(k){var mag=3*(Math.floor(k/2)+1); return (k%2===0)?mag:-mag;}
  function skycheck(){   // §4.4: every sky <text> against every other, on screen
    var els=[].slice.call(document.querySelectorAll('.skyfield text')), n=0, pairs=[];
    for(var i=0;i<els.length;i++){var a=els[i].getBBox();
      for(var j=i+1;j<els.length;j++){var b=els[j].getBBox();
        if(a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height){n++;pairs.push(els[i].textContent+' / '+els[j].textContent);}}}
    var el=document.getElementById('skycheck');
    var msg='SKYCHECK texts='+els.length+' overlaps='+n+(pairs.length?' :: '+pairs.join(' | '):'');
    if(el) el.textContent=msg;
    try{console.log(msg);}catch(e){}
  }
  function crosscheck(){ // §8 V6: does any drawn line pass over any words?
    var W=wrap.getBoundingClientRect();
    var texts=[];
    document.querySelectorAll('.ph .nm,.ph .eb,.ph .fo,.ph .lc,.fall .wl,.tile .nm,.tile .ft,.root .rn,.root .rv,.root .rk,.npf .stn,.npf .dsg,.skycap,.strip,.legend,svg.lines text').forEach(function(t){
      var b=t.getBoundingClientRect(); if(b.width<1||b.height<1) return;
      texts.push({l:b.left-W.left+1,t:b.top-W.top+1,r:b.right-W.left-1,b:b.bottom-W.top-1,s:(t.textContent||'').slice(0,26)});
    });
    // the invisible click targets are not marks the eye can see: V6 asks
    // whether a DRAWN line crosses words (BQ-011 §1 kept them out of it)
    var hits=[], paths=[].slice.call(svg.querySelectorAll('path,rect,circle')).filter(
      function(p){var k=p.getAttribute('class')||''; return k.indexOf('hitl')<0&&k.indexOf('hita')<0;});
    paths.forEach(function(p){
      var len=0, pts=[];
      if(p.tagName==='path'){ try{len=p.getTotalLength();}catch(e){len=0;}
        var n=Math.max(8,Math.min(240,Math.round(len/3)));
        for(var i=0;i<=n;i++){var q2=p.getPointAtLength(len*i/n); pts.push([q2.x,q2.y]);}
      }else{var b=p.getBBox(); pts.push([b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height],[b.x+b.width/2,b.y+b.height/2]);}
      for(var k=0;k<pts.length;k++){
        for(var j=0;j<texts.length;j++){var tb=texts[j];
          if(pts[k][0]>tb.l&&pts[k][0]<tb.r&&pts[k][1]>tb.t&&pts[k][1]<tb.b){
            hits.push((p.getAttribute('class')||p.tagName)+' over "'+tb.s+'" at '+Math.round(pts[k][0])+','+Math.round(pts[k][1])+' box '+Math.round(tb.l)+','+Math.round(tb.t)+'-'+Math.round(tb.r)+','+Math.round(tb.b)); return;}}
      }
    });
    var uniq=[]; hits.forEach(function(h){if(uniq.indexOf(h)<0)uniq.push(h);});
    var el=document.getElementById('crosscheck');
    var msg='CROSSCHECK marks='+paths.length+' texts='+texts.length+' crossings='+uniq.length+(uniq.length?' :: '+uniq.slice(0,12).join(' | '):'');
    if(el) el.textContent=msg;
    try{console.log(msg);}catch(e){}
  }
  function hitcheck(){  // BQ-356: does a click on every drawn mark reach an answer?
    // Along each drawn line (and at the middle of each dot or bar) the top
    // element under the pointer must be a mark. A point under a tile, a card or
    // words is hidden by design; a point under a see-through box is the bug.
    function solid(el){
      for(var e=el;e&&e!==document.body&&e!==document.documentElement;e=e.parentElement){
        if(e instanceof SVGElement) continue;
        var cs=getComputedStyle(e), bg=cs.backgroundColor;
        if(bg&&bg!=='transparent'&&!/rgba\([^)]*,\s*0\)$/.test(bg)) return true;
        if(parseFloat(cs.borderTopWidth)>0&&cs.borderTopStyle!=='none') return true;
        if(/^(SPAN|B|I|EM|A|BUTTON|H\d|P|LABEL)$/.test(e.tagName)) return true;
      }
      return false;
    }
    var sx=window.scrollX, sy=window.scrollY, n=0, pts=0, bad=[];
    var els=[].slice.call(document.querySelectorAll('svg.lines [data-mark],.chart svg [data-mark]')).filter(
      function(p){var k=p.getAttribute('class')||''; return k.indexOf('hitl')<0&&k.indexOf('hita')<0;});
    els.forEach(function(p){
      n++; var at=[];
      if(p.tagName==='path'){var len=0; try{len=p.getTotalLength();}catch(e){}
        for(var i=1;i<8;i++){var q2=p.getPointAtLength(len*i/8); at.push([q2.x,q2.y]);}}
      else{var b=p.getBBox(); at.push([b.x+b.width/2,b.y+b.height/2]);}
      at.forEach(function(xy){
        var pt=new DOMPoint(xy[0],xy[1]);
        window.scrollTo(0,0); var s0=pt.matrixTransform(p.getScreenCTM());
        window.scrollTo(0,Math.max(0,s0.y-window.innerHeight/2));
        var sc=pt.matrixTransform(p.getScreenCTM());
        if(sc.x<0||sc.x>=window.innerWidth||sc.y<0||sc.y>=window.innerHeight) return;
        pts++; var top=document.elementFromPoint(sc.x,sc.y);
        var host=top; while(host&&host.getAttribute&&!host.getAttribute('data-mark')) host=host.parentNode;
        var hid=host&&host.getAttribute?host.getAttribute('data-mark'):'';
        if(!top||(hid&&MARKS[hid])||solid(top)) return;
        var k=p.getAttribute('class')||p.tagName, by=top.tagName.toLowerCase()+'.'+String(top.getAttribute('class')||'').split(' ')[0];
        var line=k+' '+(p.getAttribute('data-mark')||'')+' under '+by;
        if(bad.indexOf(line)<0) bad.push(line);
      });
    });
    window.scrollTo(sx,sy);
    var el=document.getElementById('hitcheck');
    var msg='HITCHECK marks='+n+' points='+pts+' covered='+bad.length+(bad.length?' :: '+bad.slice(0,12).join(' | '):'');
    if(el) el.textContent=msg;
    try{console.log(msg);}catch(e){}
  }
  if(lb){lb.addEventListener('click',function(){linesOn=!linesOn; try{localStorage.setItem(lkey,linesOn?'on':'off');}catch(e){} draw();});}
  if(nb){nb.addEventListener('click',function(){nervesOn=!nervesOn; try{localStorage.setItem(nkey,nervesOn?'on':'off');}catch(e){} draw();});}
  window.addEventListener('resize',draw); window.addEventListener('load',draw); setTimeout(draw,60); setTimeout(draw,600);
  try{var sy=+sessionStorage.getItem('tree-scroll'); if(sy>0) window.scrollTo(0,sy);}catch(e){}
  var _st; window.addEventListener('scroll',function(){clearTimeout(_st); _st=setTimeout(function(){try{sessionStorage.setItem('tree-scroll',String(window.scrollY));}catch(e){}},200);});
  var m=/#lane=(\d+)/.exec(location.hash); if(m) open(+m[1],false);
  // the page reloads itself every five minutes: an open inspector comes back
  // on the same mark when that mark still exists, and closes when it does not
  try{var sm=sessionStorage.getItem('tree-mark'); if(sm&&!showMark(sm,null)) sessionStorage.removeItem('tree-mark');}catch(e){}
  // the window changed shape: keep the panel beside its own mark, inside it
  window.addEventListener('resize',function(){
    if(!insp||insp.hidden) return;
    var at=markOn?anchorOf(markOn,null):markAt;
    if(at) placeAt(at.x,at.y);
  });
})();
"""


def _e(text):
    return _html.escape(str(text), quote=True)


EMPTY_VALUES = ("—", "-", "--", "n/a", "N/A", "TODO", "?", "none recorded")


def _clean_rows(rows):
    clean = []
    for label, value in rows or ():
        text = "" if value is None else str(value).strip()
        if not text or text in EMPTY_VALUES:
            continue
        clean.append([str(label), text])
    return clean


# What a COUNT answers when it counts nothing yet. A count is drawn as a
# button whatever its number, and every mark answers a click: on an
# empty hub a zero says so, in plain words.
NONE_YET = "none yet"
NOT_TOLD = "you have not told me yet"      # an empty dossier page, on the sky


def mark_entry(store, mid, kind, rows, action=None, highlight=None, foot=None, when_empty=None,
               listing=None):
    """Register ONE answer — what this mark is, the real bytes behind it, at
    most one action — and return the `data-mark` attribute that points at it.

    A mark with no real bytes is not registered and gets no attribute: the page
    would rather draw nothing than answer with a placeholder.
    The one exception is a COUNT (`when_empty`): its zero is a real fact, and
    it answers with that fact — `when_empty`, e.g. "none yet".
    `foot` rows are real bytes too, drawn smaller under the rest (a live
    session's machine facts come after what it is about).
    `listing` is a history drawn above the rows (listing_of): one line
    per item, time first, its full words on hover and its source on click — or
    the key of one the page carries once for several marks (the `lists` blob)."""
    clean = _clean_rows(rows)
    if not clean and when_empty and kind:
        clean = [["so far", str(when_empty)]]
    if not kind or not clean:
        return ""
    entry = {"kind": str(kind), "bytes": clean}
    if isinstance(listing, str) and listing:
        entry["list"] = listing              # a key into the page's shared lists
    elif isinstance(listing, dict) and listing.get("items"):
        entry["list"] = listing
    tail = _clean_rows(foot)
    if tail:
        entry["foot"] = tail
    if action:
        entry["action"] = action
    if highlight:
        entry["highlight"] = highlight
    store[mid] = entry
    return " data-mark=\"%s\"" % _e(mid)


def marks_json(store):
    return json.dumps(store, ensure_ascii=False).replace("</", "<\\/")


def _heat(row, now_ts):
    """Recency bucket: h3 today · h2 within three days · h1 within the week · h0 cool."""
    if row["touched_ts"] < 0:
        return "h0"
    days = (now_ts - row["touched_ts"]) / DAY
    if days <= 1.0:
        return "h3"
    if days <= 3.0:
        return "h2"
    if days <= ACTIVE_DAYS:
        return "h1"
    return "h0"


# ── the launch link ────────────────────────────────
# claude-cli://open?cwd=…&q=… opens a NEW Claude session in a folder with the
# paste already in the box — the same scheme evidence.launch_url reads off the
# installed CLI. The q is the one-sentence paste of the hand-off law: a pointer
# at the lane's OWN opener file, never the opener's text.
CODEX_SESSION_WORDS = ("codex", "chatgpt")
LAUNCH_SENTENCE = ("read the project status/memory first. Pick up %s on the %s: "
                   "open %s in this folder and follow it.")


def is_grok_lane(row):
    # A subject such as "Hub/Grok" is not a choice of app. Respect an explicit
    # Codex destination and inspect the surface/model, never a lane-name match.
    if is_codex_lane(row):
        return False
    mind = mind_name(row.get("model"))
    where = " ".join(part for part in str(row.get("open_in") or "").split("·")
                     if not part.strip().startswith(("ACT ", "ARCH ")))
    return (mind == "GROK" or mind.startswith("GROK-")
            or bool(re.search(r"\bgrok\s+(?:build|cli|terminal|session|tui)\b", where, re.I)))


def is_codex_lane(row):
    """True when the opener itself says this lane opens on the OpenAI side: its
    `open_in` names a Codex or ChatGPT session, or its `model` field's MIND —
    the FIRST token, the one the plate spells (`GPT · XHIGH`, `GPT-5.6 ·
    MEDIUM`) — is a mind of the OpenAI side. The model field's PROSE is never
    searched: a lane on one side may name the other side's mind in its own
    reasoning, and a real opener (`OPUS · EXTRA — ... 38 edits ...`) does."""
    where = str(row.get("open_in") or "").lower()
    if any(word in where for word in CODEX_SESSION_WORDS):
        return True
    mind = mind_name(row.get("model"))          # the one rule
    return bool(mind) and any(mind.startswith(w)
                              for w in _rg.minds_of_kind(reg(), "codex"))


def lane_act_title(row):
    """The ACT title the opener's `open_in` names (the names-on-the-open_in
    law), or the grammar itself when the opener left it out."""
    found = _ACT_TITLE.search(str(row.get("open_in") or ""))
    if found:
        title = found.group(1).strip().strip("\"'`")
        # a headed opener opens the NEXT sitting, never a second copy
        # of the one that already ran and was captured.
        nxt = (row.get("captured") or {}).get("next")
        if nxt is not None:
            title = _ACT_SITTING.sub(lambda m: "%s%d" % (m.group(1), nxt), title, count=1)
        return title
    return "ACT — %s: …" % row["lane"]


def open_in_said(row):
    """The `open_in` text with its ACT title said as the NEXT sitting
    when the opener is headed (a capture's `captured:` line), so the one place
    a person copies the title from agrees with lane_act_title. Unchanged text
    otherwise; the raw header text is never touched."""
    header = row.get("header") or {}
    raw = str(header.get("open_in") if header.get("open_in") is not None
              else (row.get("open_in") or ""))
    raw = raw.strip()
    if not raw or raw == "\u2014" or row.get("captured") is None:
        return raw or "\u2014"
    found = _ACT_TITLE.search(raw)
    if not found:
        return raw
    group = found.group(1)
    old_title = group.strip().strip("\"'`")
    new_title = lane_act_title({"open_in": raw, "captured": row.get("captured"),
                                "lane": row.get("lane") or ""})
    if not old_title or old_title not in group:
        return raw
    return raw[:found.start(1)] + group.replace(old_title, new_title, 1) + raw[found.end(1):]


def captured_where_note(captured):
    """The parenthetical beside a headed card's WHERE line."""
    if not captured or captured.get("sitting") is None or captured.get("next") is None:
        return ""
    return "(s%d ran and was captured %s; this opens s%d)" % (
        captured["sitting"], captured.get("date") or "?", captured["next"])


def lane_launch(row, machine=""):
    """The launch URL for a Claude lane whose opener is on file, else ""."""
    if is_grok_lane(row) or is_codex_lane(row) or not row["card"]["handed"] or not row.get("opener"):
        return ""
    sentence = LAUNCH_SENTENCE % (row["lane"],
                                  (str(machine) or "this machine").upper(),
                                  row["opener"])
    query = urllib.parse.urlencode({"cwd": str(row["path"]), "q": sentence},
                                   quote_via=urllib.parse.quote)
    return "claude-cli://open?%s" % query


FRONT_DOOR = "read the project status/memory first."


def lane_front_door(row):
    """The Front-door link for a Claude lane with no opener on file: the same
    scheme, carrying the one sentence that opens any session."""
    if is_grok_lane(row) or is_codex_lane(row):
        return ""
    query = urllib.parse.urlencode({"cwd": str(row["path"]), "q": FRONT_DOOR},
                                   quote_via=urllib.parse.quote)
    return "claude-cli://open?%s" % query


def lane_codex_note(row):
    """Why a Codex lane has no launch button, and what to do instead. There is
    no codex:// scheme in the installed ChatGPT app."""
    if is_grok_lane(row):
        return "Grok Build: open this project folder in your terminal and run grok"
    if not is_codex_lane(row):
        return ""
    return ("no Codex launch link on file — paste into a new Codex thread titled %s"
            % lane_act_title(row))


def _lane_json(row, machine=""):
    card = row["card"]
    return {
        "lane": row["lane"], "project": row["project"], "state": row["state"],
        "dot": {"green": "g", "amber": "a", "red": "r"}.get(row["state"], "a"),
        "reasons": " · ".join(row["state_reasons"]) if row.get("state_reasons") else row["state_words"],
        "gated": row["gated"], "where": row["where"], "touched": row["touched_day"],
        "age": row["age_txt"], "idle": row["idle_txt"],
        "remaining": row["remaining"], "due": row["due"],
        "now": card["now"], "actions": card["actions"], "continues_on": card["continues_on"],
        "lives_at": card["lives_at"], "carrier": card["carrier"],
        "last_recorded": card["last_recorded"], "depends_on": card["depends_on"],
        "notes": card["notes"], "handed": card["handed"], "open_in": card["open_in"],
        "model": card["model"], "body": card["body"] if card["handed"] else card["fallback"],
        "done_when": card["done_when"],
        # what the launch row is built from: the folder a session opens in, the
        # opener file it is told to read, and the link (or the note in its place)
        "folder": row["path"], "opener_file": row.get("opener") or "",
        "launch": lane_launch(row, machine), "codex_note": lane_codex_note(row),
    }


def post_owner_notes(post_facts):
    """The notes waiting for the person, from this machine's postman pass.

    THE KEY WAS ONCE THE PERSON'S OWN SHORT WORD, so a pass written by a
    postman that has not been updated yet is still read. The old word comes
    from the registry — this file spells nobody's name."""
    found = (post_facts or {}).get("owner")
    if isinstance(found, list):
        return found
    for word in [reg()["owner"]["short"]] + list(reg()["owner"]["aliases"]):
        word = str(word or "").strip().lower()
        older = (post_facts or {}).get(word) if word else None
        if isinstance(older, list):
            return older
    return []


def tile_key(row):
    """The join between a tile and its constellation: the project FOLDER
    name, lowercased, hyphens → spaces — the same shape `_pretty_memory_dir`
    yields for a memory folder. The hub's own key is the registry's, because a
    hub folder that was renamed keeps its old name in the record its memories
    are already filed under."""
    if row.get("is_hub"):
        return _rg.hub_key(reg(), HUB_DIR.name.lower().replace("-", " ").strip())
    name = os.path.basename(str(row.get("path") or "").rstrip("/\\"))
    return name.lower().replace("-", " ").strip()


def live_dots(alive):
    """The live badge: one dot per live session in its mind's hue, with the
    mind's name; duplicates collapsed (● OPUS ×2). Never a fill.

    The hover names each session's model and, where the vendor records it, that
    session's own dial: `GROK on NORTH · grok-4.7 · high · 3 min ago`. A
    session whose dial nothing records reads exactly as it did before."""
    counts, order = {}, []
    for a in alive:
        m = str(a.get("mind") or "CLAUDE").upper()
        if m not in counts:
            counts[m] = 0
            order.append(m)
        counts[m] += 1
    order.sort(key=lambda m: (_rg.mind_rank(reg(), m), m))
    out = []
    for m in order:
        seen = [a for a in alive if str(a.get("mind") or "CLAUDE").upper() == m]
        title = "; ".join("%s on %s · %s%s · %s min ago"
                          % (m, a.get("machine") or "?", a.get("model") or "?",
                             (" · " + str(a["effort"])) if a.get("effort") else "",
                             a.get("minutes_ago"))
                          for a in seen)
        out.append('<span class="lv m-%s" title="%s">● %s%s</span>'
                   % (m.lower(), _e(title), _e(m), (" ×%d" % counts[m]) if counts[m] > 1 else ""))
    return "".join(out)


def _carrier_mark(row):
    c = (row.get("carrier") or "").lower()
    if "github" in c:
        return "◈ github"
    if "not a git" in c:
        return "⟳ sync"
    if "no remote" in c or "drive" in c:
        return "▣ drive"
    return "⌂ local"


def _chart(rows, tone, marks=None, index=None):
    """Work left, lane by lane: a bridge — each bar starts where the last
    ended, sorted by urgency, ending in the total. Static SVG, data-true.
    Quiet placeholder until a lane writes `remaining:` in its opener."""
    est = [r for r in rows if r["remaining"] is not None]
    if not est:
        return ("<div class=\"quiet\">No estimates yet. When a lane closes it writes "
                "<b>remaining: N sittings</b> (and <b>due: YYYY-MM-DD</b> when a date is real) "
                "in its opener file; the bridge appears here the moment the first one does.</div>")
    est.sort(key=lambda r: (-(r["urgency"] or 0), r["lane"]))
    total = sum(r["remaining"] for r in est) or 1.0
    W, LW, RH, PAD = 1000, 220, 26, 8
    H = PAD * 2 + RH * (len(est) + 1) + 24
    scale = (W - LW - 120) / total
    out = ["<svg viewBox=\"0 0 %d %d\" role=\"img\" aria-label=\"Work left by lane\">" % (W, H)]
    y, cum = PAD, 0.0
    for bi, r in enumerate(est):
        x0 = LW + cum * scale; w = max(2.0, r["remaining"] * scale)
        att = ""
        if marks is not None:
            lane_i = (index or {}).get(id(r))
            att = mark_entry(marks, "wl:%d" % bi, "a lane's own estimate of the work left",
                             [["lane", r["lane"]],
                              ["work left", "%g sitting%s" % (r["remaining"], "" if r["remaining"] == 1 else "s")],
                              ["due", r["due"] or ""],
                              ["urgency", ("%.2f sittings per workday left" % r["urgency"]) if r["urgency"] else ""],
                              ["where it comes from", "the lane's own `remaining:` line in its opener file"]],
                             action=({"label": "Open lane", "lane": lane_i} if lane_i is not None else None))
        out.append("<text class=\"lab\"%s x=\"%d\" y=\"%d\" text-anchor=\"end\">%s</text>" % (att, LW - 10, y + 17, _e(cut(r["lane"], 28))))
        out.append("<rect class=\"bar %s\"%s x=\"%.1f\" y=\"%d\" width=\"%.1f\" height=\"%d\" rx=\"3\"/>" % (tone.get(r["state"], "wait"), att, x0, y + 4, w, RH - 8))
        due = (" · due %s" % r["due"]) if r["due"] else ""
        # the value and the connector are the bar's own words: they answer as the bar
        out.append("<text class=\"val\"%s x=\"%.1f\" y=\"%d\">%g sitting%s%s</text>" % (att, x0 + w + 8, y + 17, r["remaining"], "" if r["remaining"] == 1 else "s", _e(due)))
        if cum > 0:
            cl = "x1=\"%.1f\" y1=\"%d\" x2=\"%.1f\" y2=\"%d\"" % (x0, y - RH + 4, x0, y + RH - 4)
            out.append("<line class=\"conn\"%s %s/>" % (att, cl))
            # a dashed hairline is hard to hit: an unseen 8 px target rides on it
            out.append("<line class=\"hitl\"%s style=\"stroke:transparent;stroke-width:8;pointer-events:stroke\" %s/>" % (att, cl))
        cum += r["remaining"]; y += RH
    tat = ""
    if marks is not None:
        tat = mark_entry(marks, "wl:total", "the work left across the fleet",
                         [["lanes with an estimate", "%d" % len(est)],
                          ["sittings left", "%g" % total],
                          ["soonest due", min([r["due"] for r in est if r["due"]] or [""]) or ""],
                          ["where it comes from", "each lane's own `remaining:` line, added up"]])
    out.append("<text class=\"lab\"%s x=\"%d\" y=\"%d\" text-anchor=\"end\">total</text>" % (tat, LW - 10, y + 17))
    out.append("<rect class=\"bar total\"%s x=\"%d\" y=\"%d\" width=\"%.1f\" height=\"%d\" rx=\"3\"/>" % (tat, LW, y + 4, total * scale, RH - 8))
    out.append("<text class=\"val\"%s x=\"%.1f\" y=\"%d\">%g sittings left across the fleet</text>" % (tat, LW + total * scale + 8, y + 17, total))
    out.append("<line class=\"axis\"%s x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\"/>" % (tat, LW, PAD, LW, y + RH))
    out.append("</svg>")
    return "".join(out)


def hub_words():
    """Every word an INBOX line uses for the hub itself — the lane words the
    person recorded against `hub`, in the order they wrote them."""
    return _rg.hub_words(reg())


def lane_aliases():
    """[(the word, the project it means)] — the person's own lane words, minus
    the ones that mean the hub, which `hub_words()` answers first."""
    return [(word, folder) for word, folder in _rg.lane_aliases(reg()).items()
            if str(folder).strip().lower() != "hub"]


def is_hub_folder(name):
    """True when a project name IS this hub — under any name it has had."""
    return str(name) in _rg.hub_folders(reg())


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _resolve(text, names):
    """A project name (or 'hub', or None) for one side of an INBOX line."""
    low = str(text).lower()
    if any(w in low for w in hub_words()):
        return "hub"
    best = None
    for name in sorted(names, key=len, reverse=True):
        if _norm(name) and _norm(name) in _norm(low):
            best = name
            break
    if best is None:
        for key, name in lane_aliases():
            if key in low and name in names:
                return "hub" if is_hub_folder(name) else name
    return best


def read_inbox(names, days=ACTIVE_DAYS):
    """[{date, src, tgts, text, line, lineno}] from the hub's INBOX.md, last
    `days` only. `line` is the whole INBOX line verbatim and `lineno` where it
    stands, so a note arc can answer a click with the note itself.
    Shapes seen: 'target ← source', 'source → target', 'source -> target',
    or a bare target. Never raises; an unreadable line is skipped."""
    roots = machine_roots()
    path = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent) / "INBOX.md"
    out = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    cutoff = datetime.now().astimezone() - timedelta(days=days)
    for number, raw in enumerate(text.splitlines(), 1):
        m = re.match(r"^- (\d{4}-\d{2}-\d{2})\s*(.*)$", raw.strip())
        if not m:
            continue
        stamp = parse_iso(m.group(1))
        if stamp is None or stamp < cutoff:
            continue
        rest = m.group(2).lstrip("·:- ").strip()
        head, _, finding = rest.partition(" · ")
        src, tgt = None, head
        if " ← " in head:
            tgt, src = [x.strip() for x in head.split(" ← ", 1)]
        elif " → " in head or " -> " in head:
            src, tgt = [x.strip() for x in re.split(r" → | -> ", head, 1)]
        elif ("→" in head or "->" in head):
            src, tgt = [x.strip() for x in re.split(r"→|->", head, 1)]
        tgts = [t for t in (_resolve(part, names) for part in re.split(r" \+ | AND | and |/(?=[A-Z])", tgt)) if t]
        source = _resolve(src, names) if src else None
        if not tgts:
            continue
        out.append({"date": m.group(1), "src": source, "tgts": list(dict.fromkeys(tgts)),
                    "text": cut(plain(finding or head), 140),
                    "line": raw.strip(), "lineno": number})
    return out


# ── an install letter never names scratch/ ─────────────────────────────────
# scratch/ is machine-local: the sync never
# carries it. A build's install candidate is staged in harvest/<row-id>/, which
# syncs, and the install letter names that path. A letter that says "install"
# and names a path under scratch/ is the builder's error: it points the other
# machine's hub at a file that machine does not have. Letters dated before
# SCRATCH_LOCAL_SINCE named a folder that still crossed, so they are history, not errors.
SCRATCH_LOCAL_SINCE = "2026-09-24"
SCRATCH_PATH = re.compile(r"(?<![A-Za-z0-9_-])scratch[\\/](?=[A-Za-z0-9_.-])")
INSTALL_VERB = re.compile(r"\binstall", re.I)
PATH_STOP = " \t`'\"()[]<>,;"


def inbox_text():
    """The hub's INBOX.md as text, or "" — never raises."""
    path = Path(machine_roots().get("orchestrator") or HUB_DIR) / "INBOX.md"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def scratch_install_letters(text, now=None, days=ACTIVE_DAYS, since=SCRATCH_LOCAL_SINCE):
    """[{lineno, date, to, path}] for every INBOX line dated on or after `since`
    and inside the last `days` that reads as an install letter (the word
    install) and names a path under scratch/. The path is the token around the
    first scratch/ it names. Never raises."""
    now = now or datetime.now().astimezone()
    floor = max((now - timedelta(days=days)).date().isoformat(), since)
    out = []
    for number, raw in enumerate((text or "").splitlines(), 1):
        m = re.match(r"^\s*- (\d{4}-\d{2}-\d{2})\b(.*)$", raw)
        if not m or m.group(1) < floor:
            continue
        body = m.group(2)
        hit = SCRATCH_PATH.search(body)
        if hit is None or INSTALL_VERB.search(body) is None:
            continue
        start, end = hit.start(), hit.end()
        while start > 0 and body[start - 1] not in PATH_STOP:
            start -= 1
        while end < len(body) and body[end] not in PATH_STOP:
            end += 1
        to = re.search(r"\bto:\s*([A-Za-z]+/[\w.-]+)", body)
        out.append({"lineno": number, "date": m.group(1),
                    "to": to.group(1) if to else "",
                    "path": body[start:end].rstrip(".:")})
    return out


def sync_roots():
    """Last sync per machine from the brain clone's own log — real bytes only.
    The brain is where the path resolver finds it; a machine with none has no
    log to read."""
    repo = paths(tool_file=__file__)["brain"]
    seen = {}
    if repo is not None and (Path(repo) / ".git").exists():
        for line in git_text(repo, ["log", "-6000", "--format=%cI|%s"]).splitlines():
            when, _, subject = line.partition("|")
            m = re.match(r"sync: (\w+)", subject)
            if m and m.group(1).lower() not in seen:
                seen[m.group(1).lower()] = parse_iso(when)
    return seen


def _pretty_memory_dir(name, roots):
    """'-home-you-Projects-Some-Project' → 'Some Project' (munged dir → a name)."""
    for key in ("projects", "orchestrator", "home"):
        root = str(roots.get(key) or "")
        if root:
            # Claude Code munges every non-alphanumeric character to a hyphen,
            # spaces included — "/home/you/Some Folder" becomes
            # "-home-you-Some-Folder". Munging only the separators missed the
            # hub, and its constellation lost its name (and with it the key a
            # nerve joins on).
            munged = re.sub(r"[^A-Za-z0-9]", "-", root)   # one dash per character, as Claude Code writes them (a Windows "D:\\Projects" becomes "D--Projects")
            if name.startswith(munged + "-"):
                return name[len(munged) + 1:].replace("-", " ")
            if name == munged:
                if key == "orchestrator":
                    # the folder's own name, so the hub's constellation key keeps
                    # matching its tile after the planned rename
                    return os.path.basename(str(root).rstrip("/\\")) or "Exocortex"
                return {"projects": "Projects", "home": "home"}[key]
    return name.strip("-").split("-")[-1] or name


def memory_uses():
    """{(normalised project, file name): [commit timestamps]} — every commit in
    the brain repo that touched a memory file is one USE. ONE git
    pass; a repo that isn't there simply yields nothing. The brain is where the
    path resolver finds it."""
    repo = paths(tool_file=__file__)["brain"]
    pair, byfile = {}, {}
    if repo is None or not (Path(repo) / ".git").exists():
        return pair, byfile
    text = git_text(repo, ["log", "--format=%ct", "--name-only", "--",
                           "claude-home/memories"])
    stamp = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d{9,12}$", line):
            stamp = int(line)
            continue
        if stamp is None or not line.startswith("claude-home/memories/"):
            continue
        parts = line.split("/")
        if len(parts) < 4 or parts[3] == "MEMORY.md":
            continue
        key = (_norm(parts[2]), parts[3])
        pair.setdefault(key, []).append(stamp)
        byfile.setdefault(parts[3], set()).add(key)
    return pair, byfile


def activation(use_days):
    """ACT-R base-level activation (Anderson & Schooler 1991):
    B = ln( Σ t_j^−0.5 ), t_j = days since each past use, floored at 0.02 of a
    day so a use minutes old cannot blow up. Retrieval probability follows
    P = 1/(1+e^(−B/0.4)); the star's opacity is 0.25 + 0.75·P."""
    import math
    total = 0.0
    for t in use_days:
        total += max(0.02, float(t)) ** -0.5
    if total <= 0:
        return -4.0, 0.0
    b = math.log(total)
    return b, 1.0 / (1.0 + math.exp(-b / 0.4))


def sky_aliases():
    """[(the word, the column it belongs in)] — the person's own, in order."""
    return list(_rg.lane_groups(reg()).items())


def sky_not_lanes():
    """Words that look like a lane and are not one: roots, folders, places."""
    return _rg.not_lane_words(reg())


def sky_lane(text, known, hub_project):
    """The column a journal line or a law belongs in: the lane its own
    words name, resolved through the alias table the fibers use; a line that
    names no lane goes to the hub's column — the hub is where general law is
    made. Longest project name first, so 'Some Project 2026' beats 'some project'."""
    low = " " + _norm(text) + " "
    for name in sorted(known, key=len, reverse=True):
        n = _norm(name)
        if len(n) >= 5 and n not in sky_not_lanes() and re.search(r"\b%s\b" % re.escape(n), low):
            return name
    for word, tag in sky_aliases():
        if not re.search(r"\b%s\b" % re.escape(word), low):
            continue
        for name in known:
            if tag in _norm(name):
                return name
    return hub_project


def _cap_words(text):
    """Capitalised words of five letters or more — the join between a journal
    line's leading title and a law's name."""
    return set(w.lower() for w in re.findall(r"\b[A-Z][A-Za-z'’-]{4,}\b", text or ""))


# An `@path` line imports a file into CLAUDE.md (the program's own law book is
# loaded this way). The sky reads the laws of every file such a
# line names, where the line stands — ONE level, never an import's imports.
LAW_IMPORT = re.compile(r"^\s*@(\S+)\s*$")


def law_lines(claude):
    """Every line the session's rules are made of: <claude root>/CLAUDE.md, with
    each file an `@` line names read in its place — `~/…` from the home folder,
    an absolute path as it is, anything else from the claude root. Read-only;
    a file that is missing or unreadable is skipped, never a crash."""
    for line, _whose in law_lines_tagged(claude):
        yield line


def law_lines_tagged(claude, hub=None):
    """(line, whose) for every line law_lines reads: `engine` for a line of the
    engine's own book (<claude root>/exocortex-laws.md), `yours` for every
    other — the person's book, and CLAUDE.md's own lines. The reading is
    exo_laws's; without it every line is the person's, as before the split."""
    if _laws is not None:
        for line, whose in _laws.tagged_lines(claude, hub, home=Path.home()):
            yield line, whose
        return
    for line in _law_lines_one_level(claude):
        yield line, "yours"


def _law_lines_one_level(claude):
    try:
        own = io.open(claude / "CLAUDE.md", encoding="utf-8", errors="replace").readlines()
    except OSError:
        return
    for line in own:
        named = LAW_IMPORT.match(line)
        if not named:
            yield line
            continue
        raw = named.group(1)
        if raw.startswith("~/") or raw.startswith("~\\"):
            target = Path.home() / raw[2:]
        elif Path(raw).is_absolute():
            target = Path(raw)
        else:
            target = claude / raw
        try:
            with io.open(target, encoding="utf-8", errors="replace") as fh:
                imported = fh.readlines()
        except (OSError, ValueError):
            continue
        for inner in imported:
            yield inner


# The name-free law marks, read off a line's BOLD HEAD only —
# the text between the opening `**` and the next `**`.
LAW_NAMEFREE_DATE = re.compile(r"\((?:ruled|ratified)\s+(\d{4}-\d{2}-\d{2})", re.I)


def starter_law(line):
    """{name, date, head} for a line starting `**` that is a law WITHOUT an
    owner clause, else None.

      `**Foo (ruled YYYY-MM-DD).** …`    a person's own law, dated
      `**Foo (ratified YYYY-MM-DD).** …` the same
      `**Foo.** …`                       a shipped starter law, undated

    A bold head that closes with neither (a section label such as `**During**`)
    is not a law. `head`, which the sky reads for a lane word, is the bold head
    itself."""
    close = line.find("**", 2)
    if close <= 2:
        return None
    bold = line[2:close]
    dated = LAW_NAMEFREE_DATE.search(bold)
    if dated:
        name = bold[:dated.start()].strip(" *—-:.")
        date = dated.group(1)
    elif bold.rstrip().endswith("."):
        name = bold.strip().rstrip(".").strip(" *—-:")
        date = ""
    else:
        return None
    if not name:
        return None
    return {"name": name, "date": date, "head": bold.strip()}


def brain_sky(roots):
    """What the exocortex holds: memories, skills, laws, journal, dossier."""
    claude = Path(roots.get("claude") or (Path.home() / ".claude"))
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    now = datetime.now().astimezone()
    use_pair, use_file = memory_uses()
    memories = []
    try:
        for d in sorted((claude / "projects").glob("*/memory")):
            for f in sorted(d.glob("*.md")):
                if f.name == "MEMORY.md":
                    continue
                try:
                    st = f.stat()
                except OSError:
                    continue
                try:
                    text = io.open(f, encoding="utf-8", errors="replace").read()
                except OSError:
                    text = ""
                # kind: the frontmatter's own `metadata: → type:` (user |
                # feedback | project | reference). Missing → project.
                kind = "project"
                mk = re.search(r"^\s+type:\s*([a-z]+)\s*$", text[:2000], re.M)
                if mk and mk.group(1) in ("user", "feedback", "project", "reference"):
                    kind = mk.group(1)
                # the file's own `description:` line — what a star answers with
                md = re.search(r"^description:\s*(.+?)\s*$", text[:4000], re.M)
                desc = cut(plain((md.group(1) if md else "").strip().strip('"')), 300)
                project = _pretty_memory_dir(d.parent.name, roots)
                # USES: every brain-repo commit that touched this file,
                # joined on (project, file name) — the repo's folders are the
                # projects' own basenames, the local dirs are munged paths, so
                # both sides are normalised; a name unique in the repo joins on
                # its own. The mtime is the latest use when it is newer than the
                # last commit; a file the repo has never seen has only its mtime.
                stamps = list(use_pair.get((_norm(project), f.name)) or [])
                if not stamps:
                    only = use_file.get(f.name) or set()
                    if len(only) == 1:
                        stamps = list(use_pair.get(next(iter(only))) or [])
                if not stamps or st.st_mtime > max(stamps) + 60:
                    stamps = stamps + [st.st_mtime]
                stamps.sort()
                days = [(now.timestamp() - s) / DAY for s in stamps]
                b, p = activation(days)
                memories.append({"project": project, "key": project.lower(), "name": f.stem,
                                 "kind": kind,
                                 "bytes": st.st_size, "age": (now.timestamp() - st.st_mtime) / DAY,
                                 "uses": len(stamps), "activation": round(b, 2), "p": round(p, 3),
                                 "first": datetime.fromtimestamp(stamps[0]).strftime("%b %d").replace(" 0", " "),
                                 "links": sorted(set(re.findall(r"\[\[([^\]|#]+)", text))),
                                 "desc": desc, "file": str(f),
                                 "text": text.lower()})
    except OSError:
        pass
    skills, skill_text = [], {}
    try:
        for sp in sorted(p for p in (claude / "skills").iterdir() if p.is_dir() and not p.name.startswith(".")):
            skills.append(sp.name)
            try:
                skill_text[sp.name] = io.open(sp / "SKILL.md", encoding="utf-8", errors="replace").read().lower()
            except OSError:
                skill_text[sp.name] = ""
    except OSError:
        pass
    laws = []
    # A ratified law opens `**Some law (<the owner>, <date>)`. The word that
    # means the owner is the registry's. A line with no owner clause is a law
    # too when its bold head says so without a name (starter_law, below):
    # `(ruled <date>` or `(ratified <date>` — a person's own dated law — or a
    # head that closes with a period, the shipped starter laws. ONE rule on
    # every machine; the owner-clause road is read first and exactly as before.
    # The lines are CLAUDE.md's own with each `@` import read in its place.
    _ow = _rg.owner_words(reg())
    _law_open = ["(%s" % w for w in _ow]
    _law_date = (re.compile(r"\((?:%s)[^)]*?(\d{4}-\d{2}-\d{2})"
                            % "|".join(re.escape(w) for w in _ow)) if _ow else None)
    try:
        for line, _whose in law_lines_tagged(claude, hub):
            _at = [line.index(o) for o in _law_open if o in line]
            if line.startswith("**") and _at:
                cut_at = min(_at)
                close = line.find("**", 2)
                name = line[2:(close if 0 < close < cut_at else cut_at)].strip(" *—-:")
                m = _law_date.search(line) if _law_date else None
                # the HEADER is where a law names its lane ("in the F&P lane",
                # "ratified in a project's lane"): the line through the end of
                # its own (<owner> …) clause, never the whole paragraph.
                tail = line.find(")", cut_at)
                laws.append({"name": name, "date": m.group(1) if m else "", "whose": _whose,
                             "head": line[:(tail + 1) if tail > 0 else min(len(line), cut_at + 160)]})
            elif line.startswith("**"):
                found = starter_law(line)
                if found is not None:
                    found["whose"] = _whose
                    laws.append(found)
    except OSError:
        pass
    # THE JOURNAL: every dated TAUGHT.md line is one episodic mark, with
    # its promotion stamp — the consolidation the drops draw.
    journal = []
    try:
        for raw in io.open(hub / "dossier" / "TAUGHT.md", encoding="utf-8", errors="replace"):
            if not raw.startswith("- 20"):
                continue
            m = re.match(r"^- (\d{4}-\d{2}-\d{2})\s*(.*)$", raw.rstrip())
            if not m:
                continue
            body = m.group(2).lstrip("—-–:· ").strip()
            pm = re.search(r"\[PROMOTED[^\]]*?(\d{4}-\d{2}-\d{2})", raw)
            age = (now - parse_iso(m.group(1))).total_seconds() / DAY if parse_iso(m.group(1)) else 0.0
            journal.append({"date": m.group(1), "title": cut(plain(body), 96),
                            "text": body, "lead": body[:110],
                            "promoted": pm.group(1) if pm else "",
                            "only": "JOURNAL-ONLY" in raw, "age": max(0.0, age)})
    except OSError:
        pass
    dossier, dossier_facts = [], {}
    # The four pages the first-run conversation fills are drawn whether they
    # exist or not: an absent or unanswered one says "you have not told me
    # yet", never a seed's text (the sky reads a page's state, not its words).
    if _personal is not None:
        for st in _personal.page_states(hub):
            dossier.append(st["page"])
            fact = {"bytes": 0, "age": None, "file": st["page"] + ".md",
                    "state": st["state"], "answered": st["answered"], "of": st["of"],
                    "last": st["last"]}
            try:
                pst = (hub / "dossier" / (st["page"] + ".md")).stat()
                fact["bytes"] = pst.st_size
                fact["age"] = (now.timestamp() - pst.st_mtime) / DAY
            except OSError:
                pass
            dossier_facts[st["page"]] = fact
    try:
        for p in sorted((hub / "dossier").glob("*.md")):
            if p.stem == "TAUGHT" or p.stem in dossier_facts:
                continue
            # the person's own law book lives beside the pages and is drawn on
            # the horizon, never as a page
            if _laws is not None and p.name == _laws.USER_BOOK[-1]:
                continue
            dossier.append(p.stem)
            try:
                st = p.stat()
                dossier_facts[p.stem] = {"bytes": st.st_size,
                                         "age": (now.timestamp() - st.st_mtime) / DAY,
                                         "file": p.name}
            except OSError:
                dossier_facts[p.stem] = {"bytes": 0, "age": None, "file": p.name}
    except OSError:
        pass
    # ── THE CODEX SIDE: the OpenAI half of the same
    # brain, drawn from real files only — the law stub it reads at every turn,
    # the rules file that lets it out of the sandbox, and every fleet skill it
    # has been given a symlink to. Root from machine.json (`codex`); a machine
    # with no Codex installed draws nothing and errors nothing.
    codex = []
    croot = Path(roots.get("codex") or (Path.home() / ".codex"))
    for rel in ("AGENTS.md", "rules/exocortex.rules"):
        f = croot / rel
        try:
            if f.is_file():
                codex.append({"kind": "law", "name": f.name, "path": str(f), "target": ""})
        except OSError:
            pass
    try:
        for sp in sorted((croot / "skills").iterdir()):
            # only the symlinks: `.system` is Codex's own, and a real folder
            # there is a Codex-side skill, not a link into the fleet.
            if sp.name.startswith(".") or not sp.is_symlink():
                continue
            target = os.path.realpath(str(sp))
            codex.append({"kind": "skill",
                          "name": os.path.basename(target.rstrip("/\\")) or sp.name,
                          "path": str(sp), "target": target})
    except OSError:
        pass
    # Relationships, all literal: a [[link]] to another memory's name; a memory
    # or a skill that names another project (display name, or a recorded alias).
    projects = sorted({m["project"] for m in memories})
    aliases = _rg.lane_mentions(reg())
    def mentions(text, own):
        hit = set()
        for proj in projects:
            key = proj.lower()
            if proj != own and len(key) >= 5 and key in text:
                hit.add(proj)
        for word, proj in aliases.items():
            if proj != own and proj in projects and word in text:
                hit.add(proj)
        return sorted(hit)
    by_stem = {}
    for m in memories:
        by_stem.setdefault(m["name"].lower(), []).append(m)
    edges = []
    for m in memories:
        for target in m["links"]:
            hits = by_stem.get(target.strip().lower(), [])
            same = [h for h in hits if h["project"] == m["project"]]
            for h in (same or hits)[:1]:
                if h is not m:
                    edges.append({"kind": "link", "a": (m["project"], m["name"]), "b": (h["project"], h["name"])})
        for proj in mentions(m["text"], m["project"]):
            edges.append({"kind": "mention", "a": (m["project"], m["name"]), "b": (proj, None)})
        m.pop("text", None)
    # The hub's own column: the orchestrator folder's basename, which is also
    # the display name its memories carry, so the rename survives.
    hub_project = os.path.basename(str(roots.get("orchestrator") or HUB_DIR).rstrip("/\\")) or "Exocortex"
    known = sorted({m["project"] for m in memories})
    for p in known:
        if _norm(p) == _norm(hub_project):
            hub_project = p
            break
    skill_lane = {}
    for sk in skills:
        named = mentions(skill_text.get(sk, ""), None)
        for proj in named:
            edges.append({"kind": "skill", "a": ("skill", sk), "b": (proj, None)})
        # a skill naming exactly one project stands in that column; one naming
        # several (focus reads every project) stands in the hub's.
        skill_lane[sk] = named[0] if len(named) == 1 else hub_project
    # LANES for the marks that are not files in a project folder: the journal's
    # lines and the laws name their lane in words, and the alias table the
    # fibers already use turns those words into a column.
    for j in journal:
        j["lane"] = sky_lane(j["text"], known, hub_project)
    for l in laws:
        l["lane"] = sky_lane(l["head"], known, hub_project)
        l.pop("head", None)
    told = [d for d in dossier if (dossier_facts.get(d) or {}).get("state", "yours") != "empty"]
    return {"memories": memories, "skills": skills, "skill_lane": skill_lane, "laws": laws,
            "journal": journal, "dossier": dossier, "dossier_facts": dossier_facts,
            "dossier_told": told,
            "edges": edges, "codex": codex, "hub_project": hub_project}


def _h(text, salt=""):
    return int.from_bytes(hashlib.sha256((text + "|" + salt).encode("utf-8")).digest()[:4], "big") / 4294967295.0


SKY_W, SKY_H = 1600, 348
SKY_TOP, SKY_BOT = 44, 258          # the band that holds stars and lines only
SKY_ROWS = (316, 334)               # the two label baselines, under the horizon (15px text)
SKY_CH = 10.6                       # measured width of one character at 15px mono with .08em tracking
SKY_AIR = 22.0                      # the air every label keeps around itself
# THE LADDER OF CONSOLIDATION: you · lessons · knowledge · skills · law.
SKY_BANDS = (("you", 44.0, 70.0), ("lessons", 74.0, 120.0),
             ("knowledge", 124.0, 226.0), ("skills", 230.0, 258.0))
SKY_LAW_EDGE, SKY_LAW_MID = 296.0, 288.0        # the horizon's shallow arc


def sky_law_y(x):
    """The law horizon: a shallow arc, 296 at the edges to 288 at the centre."""
    t = 2.0 * (float(x) / SKY_W) - 1.0
    return SKY_LAW_EDGE - (SKY_LAW_EDGE - SKY_LAW_MID) * (1.0 - t * t)


def sky_y(age_days, top, bot):
    """HEIGHT inside a band = RETRIEVAL STRENGTH: touched today sits at
    the band's top, a year at its floor, on a log10 scale."""
    import math
    age = max(0.0, float(age_days or 0.0))
    return min(bot, top + (bot - top) * math.log10(1.0 + age) / math.log10(366.0))


def sky_columns(counts):
    """COLUMN = project: kin together (the tree's own families), then by
    name; width ∝ 2+√n over x = 60 … W−20, never narrower than 64 px. n counts
    a project's marks in ALL five bands, not its memories alone."""
    import math
    order = sorted(counts, key=lambda p: (family_of(p), p.lower()))
    weights = [2.0 + math.sqrt(max(0, counts[p])) for p in order]
    total = sum(weights) or 1.0
    span = float((SKY_W - 20) - 60)
    widths = [max(64.0, span * w / total) for w in weights]
    over = sum(widths)
    if over > span:
        widths = [w * span / over for w in widths]
    cols, x = {}, 60.0
    for proj, width in zip(order, widths):
        cols[proj] = (x, width)
        x += width
    return order, cols


def _star_glyph(kind, x, y, r, cls, key, opacity, title, mark=""):
    """GLYPH = kind: project a filled circle · feedback a small diamond
    · user a four-point star · reference a hollow circle."""
    common = 'class="%s" data-key="%s" opacity="%.2f"%s' % (cls, key, opacity, mark)
    if kind == "feedback":
        s = r * 1.15
        return ('<rect %s x="%.1f" y="%.1f" width="%.1f" height="%.1f" transform="rotate(45 %.1f %.1f)">%s</rect>'
                % (common, x - s, y - s, 2 * s, 2 * s, x, y, title))
    if kind == "user":
        a, b = r * 1.9, r * 0.5
        d = ("M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1fZ"
             % (x, y - a, x + b, y - b, x + a, y, x + b, y + b,
                x, y + a, x - b, y + b, x - a, y, x - b, y - b))
        return '<path %s d="%s">%s</path>' % (common, d, title)
    if kind == "reference":
        return '<circle %s cx="%.1f" cy="%.1f" r="%.1f">%s</circle>' % (common.replace(cls, cls + " ref", 1), x, y, r + 0.4, title)
    return '<circle %s cx="%.1f" cy="%.1f" r="%.1f">%s</circle>' % (common, x, y, r, title)


def sky_overlaps(boxes):
    """Pairwise overlap count over the label boxes the layout itself measured —
    the same measure the SVG is built from, so the number is honest."""
    n = 0
    for i in range(len(boxes)):
        ax, ay, aw, ah, _ = boxes[i]
        for j in range(i + 1, len(boxes)):
            bx, by, bw, bh, _ = boxes[j]
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                n += 1
    return n


def sky_svg(brain):
    """The sky as SVG: every mark a real file, on the memory sciences' own axes.
    HEIGHT = the ladder of consolidation (you · lessons · knowledge ·
    skills · law) and, inside a band, how recently the thing was touched.
    BRIGHTNESS = ACT-R base-level activation, from the brain repo's own touch
    history. WIDTH = domain. Deterministic: the same bytes draw the same sky."""
    W, H = SKY_W, SKY_H
    import math
    out = ['<svg class="skyfield" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet" aria-label="The cortex: what the exocortex holds about you">' % (W, H)]
    boxes = []          # every <text> the sky draws, for the overlap check
    # every sky mark answers a click with its own file's bytes.
    smarks, hitpts = {}, []          # the answers · the point marks' hit areas

    def sm(mid, kind, rows, action=None):
        return mark_entry(smarks, mid, kind, rows, action=action)

    def hitpt(x, y, mid, title):
        hitpts.append((float(x), float(y), mid, title))
    hub_project = brain.get("hub_project") or "Exocortex"
    memories = brain["memories"]
    journal = brain.get("journal") or []
    laws = brain.get("laws") or []
    skills = list(brain.get("skills") or [])
    skill_lane = brain.get("skill_lane") or {}
    codex = list(brain.get("codex") or [])
    codex_laws = [c for c in codex if c.get("kind") == "law"]
    codex_skills = [c for c in codex if c.get("kind") == "skill"]

    # ── columns: every mark in every band counts toward its project's width ──
    counts = {}
    for m in memories:
        counts[m["project"]] = counts.get(m["project"], 0) + 1
    # the Codex marks stand in the hub's own column — they are the hub's files
    for extra in ([j.get("lane") for j in journal] + [l.get("lane") for l in laws]
                  + [skill_lane.get(s) for s in skills]
                  + [hub_project for _ in codex]):
        if extra:
            counts[extra] = counts.get(extra, 0) + 1
    if not counts:
        counts[hub_project] = 1
    order, cols = sky_columns(counts)

    def desc_of(f):
        """The memory's own `description:` line, or nothing — never a sentence
        the page made up about it."""
        return cut(str(f.get("desc") or ""), 240)

    def slot(proj, salt, name, top, bot, age):
        """A mark's place: its column's centre ± the seeded jitter, at the
        height its own age earns inside the band."""
        x0, width = cols.get(proj) or cols[order[0]]
        cx = x0 + width / 2.0
        x = cx + (_h(name, "e") * 2 - 1) * 0.38 * width
        y = sky_y(age, top, bot) + (_h(name, salt) * 2 - 1) * 4.0
        return (max(12.0, min(W - 12.0, x)), max(top - 3.0, min(bot + 3.0, y)))

    # ── the bands: named at the left edge, and nothing more ─────────────────
    n_user = sum(1 for m in memories if m.get("kind") == "user")
    n_know = sum(1 for m in memories if m.get("kind") in ("project", "reference"))
    n_less = sum(1 for m in memories if m.get("kind") == "feedback")
    BAND_SAYS = {
        "you": ("the dossier pages at the top centre, and the facts the memories keep about you",
                "%d dossier page%s · %d personal fact%s" % (len(brain.get("dossier_told", brain.get("dossier")) or []),
                "" if len(brain.get("dossier_told", brain.get("dossier")) or []) == 1 else "s", n_user, "" if n_user == 1 else "s")),
        "lessons": ("one dot per dated line of dossier/TAUGHT.md, and a drop to the law it became",
                    "%d journal line%s · %d lesson memor%s" % (len(journal), "" if len(journal) == 1 else "s",
                    n_less, "y" if n_less == 1 else "ies")),
        "knowledge": ("the project memories: higher means changed more recently, larger means a larger file",
                      "%d memor%s" % (n_know, "y" if n_know == 1 else "ies")),
        "skills": ("the skills installed beside the brain, each in the column its own file names",
                   "%d skill%s" % (len(skills), "" if len(skills) == 1 else "s")),
        "law": ("your ratified rules, one tick each on the horizon; the engine's own laws are the dim ticks",
                "%d of yours · %d of the engine's" % (
                    sum(1 for l in laws if l.get("whose", "yours") == "yours"),
                    sum(1 for l in laws if l.get("whose") == "engine"))),
    }

    def band_mark(label):
        says, count = BAND_SAYS.get(label, ("", ""))
        return sm("sky:band:" + label, "a row of the sky",
                  [["row", label], ["what it holds", says], ["on the page now", count],
                   ["colour", "amber means changed in the last day"],
                   ["height", "inside a row, higher means touched more recently"]])

    for label, top, bot in SKY_BANDS:
        out.append('<text class="bl"%s x="8" y="%.1f">%s</text>' % (band_mark(label), top + 9.0, _e(label)))
        boxes.append((8.0, top + 9.0 - 8.0, 4.8 * len(label) + 4, 10.0, label))
    out.append('<text class="bl"%s x="8" y="%.1f">law</text>' % (band_mark("law"), sky_law_y(8) - 5.0))
    boxes.append((8.0, sky_law_y(8) - 13.0, 4.8 * 3 + 4, 10.0, "law"))

    # ── KNOWLEDGE and YOU: the memory files ─────────────────────────────────
    pos, centroid, stars, labels, cents = {}, {}, [], [], []
    n_star = 0
    KIND_WORD = {"project": "a memory of this project", "reference": "a reference note",
                 "feedback": "a lesson from your feedback", "user": "a fact about you"}
    know_top, know_bot = SKY_BANDS[2][1], SKY_BANDS[2][2]
    you_top, you_bot = SKY_BANDS[0][1], SKY_BANDS[0][2]
    les_top, les_bot = SKY_BANDS[1][1], SKY_BANDS[1][2]
    groups = {}
    for m in memories:
        groups.setdefault(m["project"], []).append(m)
    users = sorted([m for m in memories if m.get("kind") == "user"], key=lambda m: (m["project"], m["name"]))
    user_row = {}
    for i, m in enumerate(users):        # YOU spreads evenly, not by age
        user_row[(m["project"], m["name"])] = you_top + (you_bot - you_top) * (i + 0.5) / max(1, len(users))
    for proj in order:
        files = groups.get(proj) or []
        if not files:
            continue
        key = files[0].get("key") or proj.lower()
        pts = []
        for f in files:
            kind = f.get("kind") or "project"
            if kind == "user":
                top, bot = you_top, you_bot
            elif kind == "feedback":
                top, bot = les_top, les_bot
            else:
                top, bot = know_top, know_bot
            x, y = slot(proj, "a", f["name"], top, bot, f["age"])
            if kind == "user":
                y = user_row[(proj, f["name"])]
            pos[(proj, f["name"])] = (x, y)
            if kind in ("project", "reference"):
                pts.append((x, y))
            r = 0.7 + min(2.6, math.log10(max(10, f["bytes"])) / 1.6)
            if kind == "feedback":
                r = min(r, 1.9)
            age = f["age"]
            p = float(f.get("p") or 0.0)
            need = "changed often" if p >= 0.7 else ("changed now and then" if p >= 0.4 else "quiet lately")
            uses = int(f.get("uses") or 1)
            title = ('<title>%s · %s · %s memory · %.1f KB · last touched %s ago · changed %d time%s since %s'
                     ' · activity %.2f (%s) · %d link%s</title>'
                     % (_e(proj), _e(f["name"]), _e(kind), f["bytes"] / 1024.0, _e(_span(age)),
                        uses, "" if uses == 1 else "s", _e(f.get("first") or "?"),
                        float(f.get("activation") or 0.0), need,
                        len(f["links"]), "" if len(f["links"]) == 1 else "s"))
            # BRIGHTNESS = activation; amber still owns "touched today".
            op = 0.25 + 0.75 * p
            n_star += 1
            mid = "sky:m%d" % n_star
            att = sm(mid, KIND_WORD.get(kind, "a memory"),
                     [["file", f["name"] + ".md"], ["project", proj],
                      ["what it is", desc_of(f)],
                      ["size", "%.1f KB" % (f["bytes"] / 1024.0)],
                      ["last change", "%s ago" % _span(age)],
                      ["changes", "%d since %s" % (uses, f.get("first") or "?")],
                      ["links to", ", ".join(f["links"])],
                      ["lives at", f.get("file") or ""]])
            if att:
                hitpt(x, y, mid, "%s · %s" % (proj, f["name"]))
            stars.append(_star_glyph(kind, x, y, r, "s today" if age <= 1 else "s", key,
                                     max(0.22, min(1.0, op)), title, att))
        if pts:
            ccx = sum(p[0] for p in pts) / len(pts); ccy = sum(p[1] for p in pts) / len(pts)
            centroid[proj] = (ccx, ccy)
            extent = max(math.hypot(p[0] - ccx, p[1] - ccy) for p in pts)
            # the invisible anchor a nerve's halo is drawn on
            cents.append('<circle class="cent" data-key="%s" data-n="%d" cx="%.1f" cy="%.1f" r="%.1f"></circle>'
                         % (_e(key), len(files), ccx, ccy, extent + 8.0))

    # ── LESSONS: the journal, one dot per dated line ────────────────────────
    jpos = []
    for ji, j in enumerate(journal):
        x, y = slot(j.get("lane") or hub_project, "j", j["date"] + j["title"], les_top, les_bot, j["age"])
        jpos.append((x, y, j))
        tail = (" · promoted " + j["promoted"]) if j["promoted"] else (" · journal only" if j.get("only") else "")
        mid = "sky:j%d" % ji
        att = sm(mid, "a line in your journal",
                 [["date", j["date"]], ["lane", j.get("lane") or ""],
                  ["what it says", j.get("text") or j["title"]],
                  ["became law", j["promoted"]],
                  ["kept in the journal", "yes — not promoted to law" if j.get("only") else ""],
                  ["file", "dossier/TAUGHT.md"]])
        if att:
            hitpt(x, y, mid, "journal %s · %s" % (j["date"], j["title"]))
        out.append('<circle class="jd%s"%s cx="%.1f" cy="%.1f" r="1.2"><title>journal %s · %s%s</title></circle>'
                   % (" today" if j["age"] <= 1 else "", att, x, y, _e(j["date"]), _e(j["title"]), _e(tail)))

    # ── LAW: the horizon, one tick per ratified law, spread inside its column ─
    # the horizon is the law band itself: it answers as the band's own label
    hd = "M0 %.0f Q %d %.0f %d %.0f" % (SKY_LAW_EDGE, W / 2, SKY_LAW_MID - (SKY_LAW_EDGE - SKY_LAW_MID), W, SKY_LAW_EDGE)
    out.append('<path class="horizon"%s d="%s"/>' % (band_mark("law"), hd))
    out.append('<path class="hitl"%s style="stroke-width:3" d="%s"><title>law</title></path>' % (band_mark("law"), hd))
    by_lane = {}
    for l in laws:
        by_lane.setdefault(l.get("lane") or hub_project, []).append(l)
    for c in codex_laws:                # the Codex side's own law stubs
        by_lane.setdefault(hub_project, []).append(
            {"name": "codex · " + c["name"], "date": "", "codex": True, "path": c["path"]})
    dated = sorted([l for l in laws if l["date"]], key=lambda l: l["date"])
    _cut = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    newest = set(id(l) for l in dated if str(l.get("date") or "") >= _cut
                 and l.get("whose", "yours") == "yours")   # amber = one of yours, dated in the last day, the same rule as every other mark
    lawpos = {}
    n_ticks = n_cx = 0
    for lane, group in by_lane.items():
        x0, width = cols.get(lane) or cols[order[0]]
        group = sorted(group, key=lambda l: (l["date"], l["name"]))
        for i, l in enumerate(group):
            x = x0 + width * (0.12 + 0.76 * (i + 0.5) / len(group))
            y = sky_law_y(x)
            lawpos[id(l)] = (x, y)
            if l.get("codex"):
                # a real file on the Codex side, not a ratified law: it is not
                # counted among the ticks the check line reports.
                n_cx += 1
                cid = "sky:cx%d" % n_cx
                cat = sm(cid, "a file on the OpenAI side",
                         [["file", l["name"]], ["lives at", l["path"]],
                          ["what it is", "a file the OpenAI side reads: its own law stub or rules"]])
                if cat:
                    hitpt(x, y - 4.5, cid, l["name"])
                out.append('<path class="tick codex"%s d="M%.1f %.1f v-9"><title>%s · %s</title></path>'
                           % (cat, x, y, _e(l["name"]), _e(l["path"])))
                continue
            n_ticks += 1
            mid = "sky:law%d" % n_ticks
            engine = l.get("whose") == "engine"
            att = sm(mid, "one of the engine's laws" if engine else "a law of yours",
                     [["name", l["name"]], ["ratified", l["date"]], ["lane", lane],
                      ["whose", "the engine's — how the exocortex works; shipped with the program"
                       if engine else "yours — a rule you ratified"],
                      ["file", "exocortex-laws.md, the engine's law book" if engine
                       else "your law book (dossier/LAWS.md) or your CLAUDE.md"]])
            if att:
                hitpt(x, y - 4.5, mid, "law · %s" % l["name"])
            out.append('<path class="tick%s"%s d="M%.1f %.1f v-%d"><title>%s · %s%s · %s</title></path>'
                       % (" eng" if engine else (" new" if id(l) in newest else ""), att, x, y,
                          5 if engine else 9, "engine law" if engine else "law", _e(l["name"]),
                          (" · %s %s" % (_rg.owner_label(reg()), l["date"])) if l["date"] else "", _e(lane)))

    # ── CONSOLIDATION: a promoted journal line drops to the horizon ───
    n_drops = 0
    for x, y, j in jpos:
        if not j["promoted"]:
            continue
        lane = j.get("lane") or hub_project
        hit, keys = None, _cap_words(j["lead"])
        for l in by_lane.get(lane, []):
            if l["date"] and l["date"] == j["date"] and (keys & _cap_words(l["name"])):
                hit = l
                break
        if hit is not None:
            ex, ey = lawpos[id(hit)]
            title = "journal %s → %s (inferred by date + keyword)" % (j["date"], hit["name"])
        else:
            ex, ey = x, sky_law_y(x)
            title = "promoted to law %s" % j["promoted"]
        n_drops += 1
        dd = "M%.1f %.1f L%.1f %.1f" % (x, y + 2, ex, ey - 9)
        att = sm("sky:drop%d" % n_drops, "a lesson that became law",
                 [["journal line", "%s · %s" % (j["date"], j["title"])],
                  ["became", hit["name"] if hit is not None else ("law, %s" % j["promoted"])],
                  ["how it was joined", "by date and keyword" if hit is not None else "by the promotion date in the line"]])
        out.append('<path class="drop"%s d="%s"><title>%s</title></path>' % (att, dd, _e(title)))
        out.append('<path class="hitl"%s style="stroke-width:3" d="%s"><title>%s</title></path>'
                   % (att, dd, _e(title)))

    # ── SKILLS: procedural memory, each in the column its file names ────────
    skill_pos = {}
    sk_top, sk_bot = SKY_BANDS[3][1], SKY_BANDS[3][2]
    sk_rows = (sk_top + 7.0, sk_top + 22.0)     # 15 apart: two label rows that clear
    sk_lanes = {}
    for sk in sorted(skills):
        sk_lanes.setdefault(skill_lane.get(sk) or hub_project, []).append(sk)
    for lane, group in sorted(sk_lanes.items()):
        x0, width = cols.get(lane) or cols[order[0]]
        cx = x0 + width / 2.0
        wid = [SKY_CH * len(s) + SKY_AIR for s in group]
        # the gap two neighbours on the SAME row need, measured, never guessed —
        # then opened out to fill the column, so the names have air around them
        gap = 30.0
        for i in range(len(group) - 2):
            gap = max(gap, ((wid[i] + wid[i + 2]) / 2.0) / 2.0 + 6.0)
        if len(group) > 1:
            gap = max(gap, 0.72 * width / (len(group) - 1))
        run = gap * (len(group) - 1)
        start = cx - run / 2.0
        for i, sk in enumerate(group):
            skill_pos[sk] = (max(20.0, min(W - 20.0, start + gap * i)), sk_rows[i % 2])

    # ── the lines: [[links]] (spreading activation) and skill → project ──────
    n_links = 0
    for e in brain.get("edges", []):
        if e["kind"] == "mention":
            continue            # a name mention is real but noisy; only explicit links draw
        a = pos.get(e["a"]) if e["kind"] != "skill" else skill_pos.get(e["a"][1])
        b = pos.get(e["b"]) if e["b"][1] else centroid.get(e["b"][0])
        if not a or not b:
            continue
        n_links += 1
        title = {"link": "%s · %s links to %s · %s" % (e["a"][0], e["a"][1], e["b"][0], e["b"][1]),
                 "skill": "skill %s works on %s" % (e["a"][1], e["b"][0])}[e["kind"]]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - abs(a[0] - b[0]) * 0.08
        att = sm("sky:link%d" % n_links,
                 "a link between two memories" if e["kind"] == "link" else "a skill that names a project",
                 ([["from", "%s · %s" % (e["a"][0], e["a"][1])],
                   ["to", "%s · %s" % (e["b"][0], e["b"][1])],
                   ["kind of link", "the first file's own [[link]] to the second"]]
                  if e["kind"] == "link" else
                  [["skill", e["a"][1]], ["names the project", e["b"][0]],
                   ["kind of link", "the skill's own SKILL.md names that project"]]))
        dd = "M%.0f %.0f Q %.0f %.0f %.0f %.0f" % (a[0], a[1], mx, my, b[0], b[1])
        out.append('<path class="%s"%s d="%s"><title>%s</title></path>'
                   % ("skill-line" if e["kind"] == "skill" else e["kind"], att, dd, _e(title)))
        out.append('<path class="hitl"%s style="stroke-width:3" d="%s"><title>%s</title></path>'
                   % (att, dd, _e(title)))
    out.extend(stars); out.extend(cents)
    brain["n_links"] = n_links
    brain["n_ticks"] = n_ticks
    brain["n_drops"] = n_drops
    brain["n_jdots"] = len(jpos)

    # ── the dossier: you, near the top centre ───────────────────────────────
    dos = brain["dossier"]
    if dos:
        gaps = [0.0]
        for i in range(1, len(dos)):
            gaps.append(max(46.0, (SKY_CH * len(dos[i - 1]) + SKY_CH * len(dos[i])) / 2 + SKY_AIR))
        run = sum(gaps)
        x = W / 2.0 - run / 2.0
        facts = brain.get("dossier_facts") or {}
        for i, name in enumerate(dos):
            x += gaps[i]
            fact = facts.get(name) or {}
            state = fact.get("state") or "yours"
            if state == "empty":
                told = NOT_TOLD
            elif state in ("partial", "full"):
                told = "%d of %d questions answered, in your words%s" % (
                    fact.get("answered") or 0, fact.get("of") or 0,
                    (" · last on %s" % fact["last"]) if fact.get("last") else "")
            elif state == "example":
                told = "an example page, not yours — take it out of dossier/"
            else:
                told = "kept by you, by hand"
            att = sm("sky:dos%d" % i, "a page of your dossier",
                     [["file", fact.get("file") or (name + ".md")],
                      ["what it holds", told],
                      ["size", "%.1f KB" % ((fact.get("bytes") or 0) / 1024.0) if fact.get("bytes") else ""],
                      ["last change", ("%s ago" % _span(fact["age"])) if fact.get("age") is not None else ""],
                      ["lives at", "dossier/ in the hub folder"]])
            if att:
                hitpt(x, 19, "sky:dos%d" % i, "dossier · %s" % name)
            out.append('<rect class="dos%s"%s x="%.1f" y="16" width="6" height="6" transform="rotate(45 %.1f 19)"><title>dossier · %s%s</title></rect>'
                       % (" empty" if state == "empty" else "", att, x - 3, x, _e(name),
                          (" · " + NOT_TOLD) if state == "empty" else ""))
            out.append('<text class="sk"%s x="%.1f" y="34" text-anchor="middle">%s</text>' % (att, x, _e(name.lower())))
            boxes.append((x - (SKY_CH * len(name)) / 2, 34 - 9.0, SKY_CH * len(name), 12.0, name))
    # skills draw over their lines, each with its name beneath it
    skill_named = {}
    for e in brain.get("edges") or []:
        if e.get("kind") == "skill":
            skill_named.setdefault(e["a"][1], []).append(e["b"][0])
    for si, sk in enumerate(sorted(skills)):
        x, y = skill_pos[sk]
        att = sm("sky:sk%d" % si, "a skill",
                 [["name", sk], ["names these projects", ", ".join(sorted(set(skill_named.get(sk) or [])))],
                  ["stands in the column of", skill_lane.get(sk) or hub_project],
                  ["file", "skills/%s/SKILL.md" % sk]])
        if att:
            hitpt(x, y - 3, "sky:sk%d" % si, "skill · %s" % sk)
        out.append('<path class="skill"%s d="M%.1f %.1f l2.2 5 5 2.2 -5 2.2 -2.2 5 -2.2 -5 -5 -2.2 5 -2.2z"><title>skill · %s · %s</title></path>'
                   % (att, x, y - 7, _e(sk), _e(skill_lane.get(sk) or hub_project)))
        out.append('<text class="sk"%s x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (att, x, y + 11, _e(sk)))
        boxes.append((x - (SKY_CH * len(sk)) / 2, y + 11 - 9.0, SKY_CH * len(sk), 12.0, sk))
    # THE CODEX SKILLS: the same skill, reached from the other side. It
    # stands in ITS OWN column — the fleet skill it resolves to — offset 11px
    # so the pair reads as two marks; rose says which side it belongs to. No
    # second label: the name is the one beneath it, and the legend says rose.
    for c in codex_skills:
        anchor = skill_pos.get(c["name"])
        if anchor is None:              # a link to something the fleet no longer has
            x0, width = cols.get(hub_project) or cols[order[0]]
            anchor = (x0 + width / 2.0, sk_rows[1])
        x = max(20.0, min(W - 20.0, anchor[0] + 11.0))
        cid = "sky:cxs%d" % codex_skills.index(c)
        att = sm(cid, "the same skill, reached from the OpenAI side",
                 [["name", c["name"]], ["the link", c["path"]], ["points at", c["target"]]])
        if att:
            hitpt(x, anchor[1] - 3, cid, "codex · %s" % c["name"])
        out.append('<path class="skill codex"%s d="M%.1f %.1f l2.2 5 5 2.2 -5 2.2 -2.2 5 -2.2 -5 -5 -2.2 5 -2.2z">'
                   '<title>codex · %s · %s → %s</title></path>'
                   % (att, x, anchor[1] - 7, _e(c["name"]), _e(c["path"]), _e(c["target"])))

    # ── the lands named on the ground: column labels under the horizon ──────
    named = sorted([(centroid[p][0], p, len(groups[p])) for p in order if p in centroid and len(groups[p]) >= 3])
    right = [-1e9, -1e9]
    for i, (ccx, proj, n) in enumerate(named):
        full = "%s · %d" % (proj, n)
        text = full
        w = SKY_CH * len(text) + SKY_AIR
        prefer = i % 2
        row = None
        for cand in (prefer, 1 - prefer):
            if ccx - w / 2 >= right[cand]:
                row = cand
                break
        if row is None:                       # both rows taken: shorten to the free width
            row = 0 if right[0] <= right[1] else 1
            room = (W - 6) - right[row]
            keep = int((room - SKY_AIR) / SKY_CH)
            if keep < 5:
                continue                      # no room for a readable label; the stars still hover
            text = full[:keep - 1] + "…"
            w = SKY_CH * len(text) + SKY_AIR
            x = right[row] + w / 2
        else:
            x = max(ccx, right[row] + w / 2)
            if x + w / 2 > W - 6:
                room = (W - 6) - right[row]
                keep = int((room - SKY_AIR) / SKY_CH)
                if keep < 5:
                    continue
                if keep < len(text):
                    text = full[:keep - 1] + "…"
                    w = SKY_CH * len(text) + SKY_AIR
                x = min(W - 6 - w / 2, max(x, right[row] + w / 2))
        right[row] = x + w / 2
        y = SKY_ROWS[row]
        att = sm("sky:cn%d" % i, "a project's memories",
                 [["project", proj], ["memories", "%d" % n],
                  ["where", "this constellation's own column of the sky"]])
        labels.append('<text class="cn"%s x="%.1f" y="%d" text-anchor="middle">%s<title>%s · %d memor%s</title></text>'
                      % (att, x, y, _e(text), _e(proj), n, "y" if n == 1 else "ies"))
        boxes.append((x - w / 2, y - 9.0, w, 12.0, text))
    out.extend(labels)
    # The click targets, last so they sit over the lines: each one as wide as
    # it can be without reaching its neighbour, so a click never answers with
    # the wrong file (the sky is the page's densest field).
    for i, (x, y, mid, title) in enumerate(hitpts):
        near = 1e9
        for j, other in enumerate(hitpts):
            if i == j:
                continue
            d = max(abs(x - other[0]), abs(y - other[1]))
            if d < near:
                near = d
        r = max(2.4, min(6.0, near / 2.0 - 0.4))
        out.append('<circle class="hita" data-mark="%s" cx="%.1f" cy="%.1f" r="%.1f"><title>%s</title></circle>'
                   % (_e(mid), x, y, r, _e(title)))
    out.append('</svg>')
    brain["sky_boxes"] = boxes
    brain["sky_overlaps"] = sky_overlaps(boxes)
    brain["marks"] = smarks
    return "".join(out)


def stamp_sessions(d):
    """The sessions in one stamp file, whichever shape it is in: the `sessions`
    list i-am.py writes now (two sessions of one mind on one
    machine used to wipe each other), or the single session an older file
    carries at its top level — a machine may still hold old files. An off
    stamp keeps one row of its own, so a mind never vanishes from the roots."""
    raw = d.get("sessions")
    if isinstance(raw, list):
        rows = [{"session": str(s.get("title") or ""), "effort": str(s.get("effort") or ""),
                 "when": str(s.get("when") or ""), "off": False}
                for s in raw if isinstance(s, dict)]
        if rows:
            return rows
        return [{"session": "", "effort": "", "when": str(d.get("when") or ""), "off": True}]
    return [{"session": str(d.get("session") or ""), "effort": str(d.get("effort") or ""),
             "when": str(d.get("when") or ""), "off": bool(d.get("off"))}]


def read_live(roots):
    """live-<machine>-<mind>.json files in the hub folder — one stamp per mind,
    plus the legacy one-per-machine live-<machine>.json: which minds are up
    where. Written by tools/i-am.py at a session's start; synced with the brain.

    Returns {machine: [session, ...]}, newest first — ONE DICT PER SESSION, so
    two sessions of one mind both show. Off stamps ride along marked `off`:
    they are never live, and count only for the "last mind" line."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    live = {}
    for f in sorted(hub.glob("live-*.json")):
        if f.name.startswith("live-sessions-"):
            continue                # the pulse's own file — read_live_sessions has it
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("mind"):
            continue                # no mind named: nothing to show on the roots
        mch = str(d.get("machine") or "").lower() or f.stem[5:].split("-")[0]
        for e in stamp_sessions(d):
            e["mind"] = d.get("mind")
            e["machine"] = d.get("machine") or mch
            when = parse_iso(e.get("when"))
            e["age"] = ((datetime.now().astimezone() - when).total_seconds() / DAY) if when else None
            live.setdefault(mch, []).append(e)
    for stamps in live.values():
        stamps.sort(key=lambda s: (s["age"] if s.get("age") is not None else 1e9))
    return live


def read_ears(roots):
    """ear-<machine>-<lane>.json in the hub folder — which mailboxes are actually
    being watched. Written by tools/mail.py --watch on every poll, so the file's
    own age is the proof: an ear is FRESH while it is younger than TWICE its own
    poll interval (one missed beat is a hiccup, two is a mailbox nobody holds).

    {machine: [ear, ...]}, the hub's ear first. A machine with no fresh hub ear
    is a machine no letter reaches on its own — the root says so in plain words."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    now = datetime.now().astimezone()
    ears = {}
    try:
        files = sorted(hub.glob("ear-*.json"))
    except OSError:
        files = []
    for f in files:
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        stem = f.stem[4:].split("-")
        mch = str(d.get("machine") or "").strip().lower() or (stem[0] if stem else "")
        lane = str(d.get("lane") or "").strip().lower() or "-".join(stem[1:]) or "hub"
        when = parse_iso(d.get("when"))
        age = (now - when).total_seconds() if when else None
        try:
            every = int(d.get("every") or 0)
        except Exception:
            every = 0
        if not mch:
            continue
        ears.setdefault(mch, []).append(
            {"machine": mch, "lane": lane, "title": str(d.get("title") or ""),
             "every": every, "age_s": age, "file": f.name,
             "fresh": bool(age is not None and every > 0 and 0 <= age <= 2 * every)})
    for rows in ears.values():
        rows.sort(key=lambda e: (e["lane"] != "hub", e["lane"]))
    return ears




# A model line is written for a human: `OPUS · EXTRA`, `GPT-5.6-MINI · MEDIUM`,
# and sometimes a whole sentence — `OPUS - XHIGH for diagnosis; HAIKU - medium
# for settled mechanical checks`. The MIND is the FIRST TOKEN of it and nothing
# more: a card named after a sentence is not a mind.
MIND_SEP = re.compile(r"\s*[\u00b7|;,/()\[\]:]\s*|\s+[-\u2013\u2014]\s+|\s+for\s+|\s{2,}", re.I)
MIND_TOKEN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]*$")
MIND_MAX = 16
# A model line that says any mind will do names none (the hub's seeded first
# opener says `model: any · default`): no root is drawn for it.
NO_MIND_WORDS = ("ANY",)


def known_mind_words():
    """Every word that NAMES a mind on this person's fleet: the minds they
    list, and the words they say mean one. Nothing is written down here — a
    fleet with no registry knows no mind by name and reads every model line at
    face value."""
    record = reg()
    return list(_rg.mind_names(record)) + list(record["mind_aliases"].keys())


def mind_name(m):
    """The MIND as the plate spells it: the first token of the model line,
    uppercased, letters/digits/dots/dashes only, at most 16 characters.

    A word the person has said means a mind of theirs becomes that mind (so
    one desktop's sessions can share one name); a Claude session
    with no model record yet is CLAUDE. A known mind named anywhere in that
    first chunk wins over an unknown token; an unknown token that is a single
    word still stands, because a mind this machine has never seen must still
    draw a root — but a sentence never does."""
    head = MIND_SEP.split(str(m or "").strip(), 1)[0].strip()
    words = head.split()
    token = re.sub(r"[^A-Za-z0-9.\-]", "", words[0]).upper() if words else ""
    known = known_mind_words()
    if token in known:
        return _rg.mind_alias(reg(), token)
    # the line may name a known mind without leading with it ("the OPUS lane")
    for name in known:
        if re.search(r"(?<![A-Z0-9.\-])%s(?![A-Z0-9.\-])" % re.escape(name), head.upper()):
            return _rg.mind_alias(reg(), name)
    token = token[:MIND_MAX]
    if token in NO_MIND_WORDS:
        return ""
    return token if MIND_TOKEN.match(token) else ""


def session_kind(sess):
    """claude | codex | grok for one pulse session, whichever pulse wrote the file:
    the new `kind` key, else the old `mind` (claude|codex), else the id shape."""
    kind = str(sess.get("kind") or "").lower()
    if kind in ("claude", "codex", "grok", "job"):
        return kind
    mind = str(sess.get("mind") or "").upper()
    by_registry = _rg.mind_kind(reg(), mind)
    if by_registry:
        return by_registry
    if str(sess.get("id") or "").startswith("rollout-"):
        return "codex"
    return "claude"


def session_mind(sess, kind):
    """The mind a nerve is drawn in. An older pulse file says only the
    transcript family — then the mind is what that family can be named without
    inventing anything: the registry's own word for it, or the family's."""
    mind = mind_name(sess.get("mind"))
    if mind in ("", _rg.kind_word("claude"), _rg.kind_word("codex")):
        return _rg.mind_name(reg(), kind, sess.get("model") or "")
    return mind


def _one_line(text, limit=0):
    """One line of words: whitespace collapsed, cut at `limit` when one is given."""
    s = " ".join(str(text or "").split())
    if limit and len(s) > limit:
        s = s[:limit - 1].rstrip() + "\u2026"
    return s


def _path_key(path):
    """A folder path as a comparable key: one separator, no trailing slash, case-folded."""
    return re.sub(r"[\\/]+", "/", str(path or "")).rstrip("/").lower()


def read_sync_verdicts(roots):
    """{machine: {words, line, read}} from sync-verdict-<machine>.json in the hub folder — the
    one-line sync verdict each machine's pulse writes every beat (tools/sync-verdict.py).
    The page carries the words; it never recomputes them. No file, no entry: the root reads
    exactly as it did before that build."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    out = {}
    try:
        files = sorted(hub.glob("sync-verdict-*.json"))
    except OSError:
        files = []
    for f in files:
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("line"):
            continue
        mch = str(d.get("machine") or f.stem[len("sync-verdict-"):]).strip().lower()
        out[mch] = {"words": str(d.get("words") or str(d["line"]).split(" · ")[0]),
                    "line": str(d["line"]), "read": parse_iso(d.get("read"))}
    return out


def read_live_sessions(roots):
    """{project path or dir name → [{machine, kind, mind, model, id, minutes_ago}]}
    from live-sessions-*.json (the pulse's own file). `mind` is the mind's own
    name (FABLE / OPUS / …), `kind` the vendor side, `id` the transcript
    stem's last six characters — the short id the hover shows.

    A row whose vendor records the session's own dial also carries `effort` (a
    Grok summary's `reasoning_effort`); a vendor that records none simply
    has no such key, and the hover then says nothing about a dial.

    Every row also carries what the session is ABOUT — `title`,
    `first_line`, `last_line`, '' where an older pulse wrote none — its `cwd`,
    whether it sits in the hub folder (`in_hub`, the pulse's own word, else
    worked out here), and `minutes_now`: its minutes since its last turn at the
    pulse's look PLUS the minutes since that look, so a line on the page never
    reads younger than the record allows."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    hub_key = _path_key(hub)
    out, stamps = {}, {}
    for f in sorted(hub.glob("live-sessions-*.json")):
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        when = parse_iso(d.get("when"))
        age_h = ((datetime.now().astimezone() - when).total_seconds() / 3600.0) if when else None
        stamps[str(d.get("machine", "")).lower()] = {"when": when, "age_h": age_h, "n": len(d.get("sessions", []))}
        if age_h is None or age_h > 0.5:
            continue            # a stale pulse file says nothing about now
        for sess in d.get("sessions", []):
            key = (sess.get("cwd") or "").rstrip("/") or sess.get("dir", "")
            kind = session_kind(sess)
            row = {"machine": str(d.get("machine", "")).upper(),
                   "kind": kind, "mind": session_mind(sess, kind),
                   "model": str(sess.get("model") or ""),
                   "id": str(sess.get("id") or "")[-6:],
                   "minutes_ago": sess.get("minutes_ago")}
            effort = str(sess.get("effort") or "").strip()
            if effort:                  # the session's own dial, never a guess
                row["effort"] = effort
            cwd = str(sess.get("cwd") or "")
            ckey = _path_key(cwd)
            in_hub = sess.get("in_hub")
            if not isinstance(in_hub, bool):
                in_hub = bool(ckey) and (ckey == hub_key or ckey.startswith(hub_key + "/"))
            try:
                ago = float(sess.get("minutes_ago"))
            except (TypeError, ValueError):
                ago = None
            row.update({"title": _one_line(sess.get("title")),
                        "first_line": _one_line(sess.get("first_line")),
                        "last_line": _one_line(sess.get("last_line")),
                        "cwd": cwd, "dir": str(sess.get("dir") or ""), "in_hub": in_hub,
                        "pulse_min": max(0.0, age_h * 60.0),
                        "minutes_now": (None if ago is None else ago + max(0.0, age_h * 60.0))})
            if kind == "job":
                ended = parse_iso(sess.get("ended"))
                if sess.get("state") != "running" and (ended is None or (datetime.now().astimezone() - ended).total_seconds() >= 600):
                    continue
                row.update({k: sess.get(k) for k in ("run_id", "lane", "minutes", "last_step", "state", "log", "report", "record", "show", "show_uri", "ended", "started")})
            row.update(session_history(sess))           # what it has been used for
            out.setdefault(key, []).append(row)
    return out, stamps


def minutes_words(mins):
    """How long ago, in whole minutes a person reads at a glance."""
    if mins is None:
        return ""
    try:
        m = int(round(float(mins)))
    except (TypeError, ValueError):
        return ""
    return "under a minute ago" if m < 1 else ("%d min ago" % m)


def title_lane(title):
    """`Proj/Lane` as a ritual title spells it (`ACT — Hub/Desk: …` gives
    `Hub/Desk`) — exo_common's lane token, in the title's own letters — or ''
    when the title names no lane (no slash, or words with spaces)."""
    tok = lane_token(title)
    if "/" not in tok or re.search(r"\s", tok):
        return ""
    t = str(title or "")
    at = t.lower().find(tok)
    return t[at:at + len(tok)] if at >= 0 else tok


# ── what a live link has been used for ────────────────────────────────────
# A live session's card is memory, not a snapshot: the pulse carries the last
# twenty turns a person typed in that window ({t, words, line}, read from the
# transcript by the pulse's own "a PERSON typed" test); the page only draws
# them. One line per turn, time first, trimmed to twelve words with the whole
# turn on hover and its source — the transcript and the line — on a click.
# Oldest at the top, the newest marked `now`; above twenty, one line `N
# earlier`. A one-turn window keeps its single ABOUT line, as before. A fall
# arc answers with the same shape over the INBOX letters between its pair.
LIST_KEEP = 20
LIST_WORDS = 12
LIST_FULL_CHARS = 500       # the hover's words, at most (the source line holds the rest)


def _first_words(text, count=LIST_WORDS):
    """The first `count` words of one line, an ellipsis when there were more."""
    parts = str(text or "").split()
    if len(parts) <= count:
        return " ".join(parts)
    return " ".join(parts[:count]) + "…"


def session_history(sess):
    """The history keys of one pulse row, checked: `turns` — [{t,
    words, line}] — `earlier`, `transcript`, and for a routine's run `routine`
    and `run_status`. A row from an older pulse has none of them, and its card
    reads ABOUT/NOW exactly as before."""
    out = {}
    turns = sess.get("turns")
    if isinstance(turns, list):
        clean = []
        for t in turns:
            if not isinstance(t, dict):
                continue
            said = _one_line(t.get("words"))
            if not said:
                continue
            try:
                line = max(0, int(t.get("line") or 0))
            except (TypeError, ValueError):
                line = 0
            clean.append({"t": str(t.get("t") or ""), "words": said, "line": line})
        out["turns"] = clean
    try:
        earlier = int(sess.get("earlier") or 0)
    except (TypeError, ValueError):
        earlier = 0
    if earlier > 0:
        out["earlier"] = earlier
    if sess.get("transcript"):
        out["transcript"] = str(sess["transcript"])
    if sess.get("routine") is not None:
        out["routine"] = _one_line(sess.get("routine"))
        out["run_status"] = _one_line(sess.get("run_status")) or "running"
    return out


def listing_of(items, earlier=0, now_mark=True):
    """A history for the inspector, oldest first: {"items": [{at, w, full?,
    src}], "earlier": N}. Each item comes as {when | at, words, full?, short?,
    src}: `at` is the time the line starts with (HH:MM on this machine's clock,
    with the day in front whenever the list leaves today or crosses a day), `w`
    the words trimmed to twelve, `full` the whole line for the hover when it is
    longer, `src` what a click answers with. The last LIST_KEEP are kept; the
    rest are counted in `earlier`."""
    items = [it for it in items if _one_line(it.get("words"))]
    keep = items[-LIST_KEEP:]
    earlier = max(0, int(earlier or 0)) + len(items) - len(keep)
    whens = [it["when"].astimezone() for it in keep if it.get("when") is not None]
    days = set(w.date() for w in whens)
    today = datetime.now().astimezone().date()
    mark_days = len(days) > 1 or any(d != today for d in days)
    out, prev_day = [], None
    for k, it in enumerate(keep):
        at = it.get("at")
        if at is None:
            at = ""
            if it.get("when") is not None:
                w = it["when"].astimezone()
                at = w.strftime("%H:%M")
                if mark_days and w.date() != prev_day:
                    at = "%s %s" % (w.strftime("%a"), at)
                prev_day = w.date()
        if now_mark and k == len(keep) - 1:
            at = ("%s · now" % at) if at else "now"
        full = _one_line(it.get("full") or it["words"], LIST_FULL_CHARS)
        short = _one_line(it.get("short")) or _first_words(_one_line(it["words"]))
        item = {"at": at, "w": short, "src": str(it.get("src") or "")}
        if full != short:
            item["full"] = full
        out.append(item)
    listing = {"items": out}
    if earlier > 0:
        listing["earlier"] = earlier
    return listing


def turn_listing(sess):
    """A live session's history as a listing (listing_of), or None when its
    card keeps the single ABOUT line: fewer than two turns and no routine.
    A routine's run is ONE line — its prompt's first line — never marked now."""
    turns = sess.get("turns") or []
    routine = sess.get("routine") is not None
    if not turns or (len(turns) < 2 and not routine):
        return None
    where = sess.get("transcript") or "the transcript"
    machine = sess.get("machine") or ""
    items = [{"when": parse_iso(t.get("t")), "words": t.get("words"),
              "src": "%s%s%s" % ((machine + " · ") if machine else "", where,
                                 (":%d" % t["line"]) if t.get("line") else "")}
             for t in turns]
    return listing_of(items, earlier=sess.get("earlier") or 0,
                      now_mark=not (routine and len(items) == 1))


def live_card(sess, project):
    """What a live session's card says, in the order a person needs it:
    the heading is its name — the title the app shows, else `<project> · a
    session` — then ABOUT (the first thing the person asked it), NOW (the latest,
    left out when it is the same), LAST ACTIVE; the machine facts sit in the foot.
    Returns (heading, rows, foot).

    When the session's history is a list (turn_listing: two or more
    turns, or a routine's run) the list IS the story and ABOUT/NOW are left
    out — ABOUT is its first line and NOW its last; a routine's card says its
    name and the run's status word instead."""
    heading = sess.get("title") or ("%s · a session" % (project or "a folder"))
    rows = []
    if turn_listing(sess) is None:
        if sess.get("first_line"):
            rows.append(["about", sess["first_line"]])
        if sess.get("last_line") and sess.get("last_line") != sess.get("first_line"):
            rows.append(["now", sess["last_line"]])
    elif sess.get("routine") is not None:
        rows.append(["routine", sess.get("routine") or "a scheduled task"])
        rows.append(["status", sess.get("run_status") or "running"])
    mins = sess.get("minutes_now")
    if mins is None:
        mins = sess.get("minutes_ago")
    rows.append(["last active", minutes_words(mins) or "at the pulse's last look"])
    seen = "the pulse, from the transcript it is writing"
    if sess.get("pulse_min") is not None:
        seen += " · looked %s" % (minutes_words(sess["pulse_min"]) or "just now")
    foot = [["mind", sess.get("mind") or "CLAUDE"], ["machine", sess.get("machine") or ""],
            ["model", sess.get("model") or ""],
            ["session id", "…%s" % (sess.get("id") or "?")],
            ["working in", sess.get("cwd") or sess.get("folder") or ""],
            ["seen by", seen]]
    return heading, rows, foot


SKY_REPORT = {}     # the last render's label check: {texts, overlaps}


def find_sky():
    """The user's own sky beside the page, if any: sky.svg / .png / .jpg / .jpeg / .webp."""
    roots = machine_roots()
    folder = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    for name in ("sky.svg", "sky.png", "sky.jpg", "sky.jpeg", "sky.webp"):
        if (folder / name).is_file():
            return name
    return None


def ideas_counts(roots):
    """(ideas on file, ideas still `new`) from IDEAS.md — the file itself, never
    a cached number (every count on the tree comes from the file).
    A hub with no IDEAS.md, or a line that is not an idea, counts nothing."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    total = new = 0
    try:
        for raw in io.open(hub / "IDEAS.md", encoding="utf-8", errors="replace"):
            m = re.match(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} · (.+?) · ", raw)
            if m:
                total += 1
                new += 1 if m.group(1).strip() == "new" else 0
    except OSError:
        pass
    return total, new


def ideas_lines(roots, limit=60):
    """[(status, when, first words)] from IDEAS.md — the file itself, never a
    cached number (the ideas count answers a click with these)."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    found = []
    try:
        for raw in io.open(hub / "IDEAS.md", encoding="utf-8", errors="replace"):
            m = re.match(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?) · (.*)$", raw.rstrip())
            if m:
                found.append((m.group(2).strip(), m.group(1), words(plain(m.group(3)), 16)))
    except OSError:
        pass
    return found[:limit]


def improvements_chip(roots):
    """Hook B: the improvements ledger's own chip for the counts strip,
    or "" — the ledger writes its own markup, the tree only carries it. Never
    raises: no ledger, no queue, no chip (the strip says nothing it cannot
    prove)."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "improvements", Path(__file__).resolve().parent / "improvements.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.chip_html(roots.get("orchestrator"))
    except Exception:
        return ""


def night_facts(roots):
    """ this machine's night check — {last, rows} for the collar's night line, from
    tools/night-check.py (the tool owns the facts, the tree carries them, as it carries the
    ledger's chip). Never raises: no tool beside this file, or any error, gives {} and the
    collar is exactly what it was before that build."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "exo_night_tree", Path(__file__).resolve().parent / "night-check.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        res = module.check(module.record([]), datetime.now().astimezone())
        rows = [[i.get("kind") or "", i.get("words") or ""] for i in res.get("items") or []]
        rows += [["cannot see", str(c).split(": ", 1)[-1]] for c in res.get("cannot_see") or []]
        rows.append(["read", "%s · tools/night-check.py, drawn with this page" % res.get("read")])
        return {"last": str(res.get("last") or ""), "rows": rows}
    except Exception:
        return {}


def usage_bands(roots):
    """The masthead's meter bands — one per vendor per machine, from
    the meter files' own bytes (tools/usage.py draws them; the tree only
    carries them, as it carries the ledger's chip). Never raises: no usage.py,
    no meter file, no band."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "exo_usage_tree", Path(__file__).resolve().parent / "usage.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.bands_html(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    except Exception:
        return ""


def postman_facts(roots, lanes=()):
    """The postman hook: the postman's own facts for this page — each
    machine's pass, the letters waiting for each lane, and the notes for the owner.

    Loaded the way `improvements_chip()` loads the ledger: THE TOOL OWNS THE
    FACTS AND THE TREE OWNS THE DRAWING. Never raises. No postman beside this
    file, or no post file anywhere in the hub, gives {} — and then every mark on
    this page is exactly the mark it was the day before that build."""
    try:
        import importlib.util
        here = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location("exo_postman_tree", here / "postman.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        facts = module.tree_facts(roots.get("orchestrator") or here.parent, lanes)
        return facts if isinstance(facts, dict) else {}
    except Exception:
        return {}


def guard_facts(roots):
    """Each machine's write guard, from the summary file the guard itself
    rewrites on every deny — `<hub>/guard-<machine>.json`:
    `{machine, when, today: N, last: [five {when, vendor, zone, target}]}`.

    {machine → {today, when, last}} for the machines whose count belongs to
    TODAY, and only those: `today` is the tally of the day `when` names, so a
    file whose last deny was yesterday says nothing about today and is left out
    — the chip would otherwise carry a number from another day. A hub with no
    guard file, a file that cannot be read, a count of zero: nothing, and the
    page draws nothing (Nothing-superfluous). The machine is the one the FILE
    NAME addresses (`guard-<machine>.json` is the guard's own contract), and a
    file whose inner `machine` contradicts its name is skipped rather than drawn
    on a root it may not belong to. Never raises."""
    hub = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    today = datetime.now().astimezone().date()
    out = {}
    try:
        files = sorted(hub.glob("guard-*.json"))
    except OSError:
        return out
    for f in files:
        name = f.stem[len("guard-"):].lower()
        if not name or name == "policy":        # guard-policy.json is the registry
            continue
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        said = str(d.get("machine") or "").strip().lower()
        if said and said != name:
            continue        # the name in the file contradicts the name on it: skip
        try:
            n = int(d.get("today") or 0)
        except (TypeError, ValueError):
            continue
        when = parse_iso(d.get("when"))
        if n <= 0 or when is None or when.date() != today:
            continue
        last = [r for r in (d.get("last") or []) if isinstance(r, dict)]
        out[name] = {"today": n, "when": d.get("when") or "", "last": last[-5:],
                     "file": f.name}
    return out


def _hhmm(when):
    d = parse_iso(when)
    return d.strftime("%H:%M") if d else ""


def mail_marks(roots):
    """{session id: mark} from every machine's mail-marks-<machine>.json in the hub
    (written by the postman's pass). {} when there is none — and then the LIVE list is byte for
    byte what it was before this build."""
    out = {}
    hub = Path(roots.get("orchestrator") or HUB_DIR)
    try:
        files = sorted(hub.glob("mail-marks-*.json"))
    except OSError:
        return out
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for sid, mark in ((d.get("sessions") or {}) if isinstance(d, dict) else {}).items():
            if isinstance(mark, dict) and int(mark.get("count") or 0) > 0:
                out[str(sid)] = mark
    return out


def mail_mark_words(mark):
    """What the ✉ says on hover: the count, and the road the postman took, in its own words."""
    n = int(mark.get("count") or 0)
    road = {"send": "pushed into the window", "hook": "its own next turn carries it",
            "announce": "queued for its next turn; a desktop notice said so"}.get(
        mark.get("road"), mark.get("road") or "")
    # the same first words as the postman's nudge — which lane, who wrote, what about
    said = ("%d note%s waiting for %s · from %s · «%s»" % (
        n, "" if n == 1 else "s", mark["lane"], mark.get("from") or "Exocortex",
        mark.get("subject") or "")) if mark.get("lane") else "%d letter%s waiting" % (n, "" if n == 1 else "s")
    return "%s — %s%s" % (said, road, (" (%s)" % mark["why"]) if mark.get("why") else "")


def html_page(data):
    """The cortex: the sky on top, then a row of project heads (the crown) and
    the FALL — six ISO weeks as rows, one stream per project whose width is that
    week's commits, session dots in their mind's hue, arcs for the notes that
    crossed between projects, nerves rising in their own column; then the
    collar, the roots, the band of what the fall does not show, the work-left
    bridge and the detail view (01 Summary · 02 What to do, then the prompt)."""
    roots = machine_roots()
    rows = data["rows"]
    # what the postman can say about the post. The match from
    # an address to one of these lanes is made inside the postman, with mail.py's
    # own addr_key and phase A's suffix rule — never a second matcher here.
    post_key = dict((id(r), "L%d" % i) for i, r in enumerate(rows))
    post_facts = postman_facts(roots, [(post_key[id(r)], r["lane"], bool(r["is_hub"]))
                                       for r in rows])
    post_lane = post_facts.get("lanes") or {}
    post_done = post_facts.get("delivered") or {}
    guard_by_machine = guard_facts(roots)       # today's refusals, per machine
    not_read_s = float((post_facts.get("config") or {}).get("not_read_minutes") or 5) * 60.0
    now = datetime.now().astimezone()
    now_ts = now.timestamp()
    # one table of answers, one id per mark. Every mark on the page
    # registers here, and the inspector is the only thing that reads it.
    marks = {}
    # a history is carried ONCE even when two marks answer with it (a
    # session's nerve and its LIVE line; the arcs of one pair, week by week)
    shared_lists, list_keys = {}, {}

    def mk(mid, kind, byte_rows, action=None, highlight=None, foot=None, when_empty=None,
           listing=None, share=None):
        if share is not None and isinstance(listing, dict):
            if listing.get("items"):
                key = list_keys.setdefault(share, "l%d" % len(list_keys))
                shared_lists.setdefault(key, listing)
                listing = key
            else:
                listing = None
        return mark_entry(marks, mid, kind, byte_rows, action=action, highlight=highlight,
                          foot=foot, when_empty=when_empty, listing=listing)

    def capped(byte_rows, limit=60):
        """A list the reader can take in: the first `limit`, then how many more."""
        rest = len(byte_rows) - limit
        if rest > 0:
            return byte_rows[:limit] + [["and", "%d more" % rest]]
        return byte_rows

    def post_mail(keys, mid):
        """(the ✉ mark, the count) for a face.

        WHEN ANY POST FILE EXISTS the count is the letters WAITING for that lane
        across every machine's post file, which is what the mark's own words
        promise; it is amber only while one of them wants an answer and has
        waited longer than not_read_minutes, and dim otherwise. The click
        answers with each letter verbatim, its why, its holder and when it was
        first seen — then today's delivered letters underneath.

        WITH NO POST FILE it returns ("", None), and the caller draws exactly
        the INBOX-note count it drew before this build."""
        if not post_facts:
            return "", None
        live, done, seen = [], [], set()
        for key in keys:
            for row in post_lane.get(key) or []:
                if row["token"] in seen:
                    continue
                seen.add(row["token"])
                live.append(row)
            for row in post_done.get(key) or []:
                done.append(row)
        if not live:
            return "", 0
        hot = any((not x["fyi"]) and (x.get("age_s") or 0) >= not_read_s for x in live)
        brows = []
        for x in sorted(live, key=lambda z: z.get("first_seen") or ""):
            brows.append(["letter", x.get("line") or x.get("to") or ""])
            brows.append(["why", x.get("why") or ""])
            holder = x.get("holder") or {}
            brows.append(["held by", ("%s «%s» on the %s"
                                      % (holder.get("mind") or "?", holder.get("title") or "",
                                         str(holder.get("machine") or "").upper()))
                          if holder else "nobody holds that lane"])
            brows.append(["first seen", x.get("first_seen") or ""])
            if x.get("nudged"):
                brows.append(["%s was nudged at" % _rg.owner_label(reg()), _hhmm((x["nudged"] or {}).get("when"))])
        for x in sorted(done, key=lambda z: (z.get("delivered") or {}).get("when") or ""):
            d = x.get("delivered") or {}
            brows.append(["delivered today", "%s · %s · %s · seen in the %s"
                          % (cut(plain(x.get("line") or x.get("to") or ""), 70),
                             d.get("road") or "?", _hhmm(d.get("when")),
                             d.get("evidence") or "?")])
        att = mk(mid, "the letters waiting for this lane", capped(brows, 80))
        # the hover opens with the same words as the nudge — the lane, who wrote the
        # newest letter, what about (the postman's own facts; an older postman gives the old title)
        last = max(live, key=lambda z: (z.get("first_seen") or "", z.get("token") or ""))
        said = ("%d note(s) waiting for %s · from %s · «%s»"
                % (len(live), last["lane"], last.get("from") or "Exocortex", last.get("subject") or "")
                ) if last.get("lane") else "%d letter(s) waiting for this lane" % len(live)
        return ("<span class=\"mail\"%s%s title=\"%s\">✉ %d</span>"
                % ("" if hot else " style=\"color:var(--dim)\"", att, _e(said), len(live))), len(live)

    hub_rows = [r for r in rows if r["is_hub"]]
    others = [r for r in rows if not r["is_hub"]]
    active = [r for r in others if r["active"]]
    with_opener = sum(1 for r in rows if r["active"] and r["opener"])
    owe_rows = [r for r in rows if r["active"] and not r["opener"]]
    owe = [r["lane"] for r in owe_rows]
    stale = data["flags"].get("stale", [])
    stamp = now.strftime("%A %Y-%m-%d %H:%M")
    if stale:
        chip = "%d stale opener%s" % (len(stale), "" if len(stale) == 1 else "s")
    elif owe:
        chip = "%d lane%s owe a startup prompt" % (len(owe), "" if len(owe) == 1 else "s")
    else:
        chip = "every startup prompt on file"
    machine = str(roots.get("name", "")).upper() or "THIS MACHINE"
    state_word = {"green": "ready", "amber": "waiting on you", "red": "attention"}
    tone = {"green": "ready", "amber": "wait", "red": "bad"}
    estimated = any(r["remaining"] is not None for r in rows if r["active"])

    # ── the fall's columns: one per project folder with activity inside the
    #    six-week window — families grouped, hottest family leftmost ───
    live_sessions, pulse_stamps = read_live_sessions(roots)
    weeks, window_start, since = fall_window()
    wkeys = [w["key"] for w in weeks]
    wlabel = dict((w["key"], w["label"]) for w in weeks)
    sessions_by_cwd = session_weeks(roots, weeks)

    projects, by_path = [], {}
    for r in others:
        path = str(r["path"]).rstrip("/\\")
        p = by_path.get(path)
        if p is None:
            p = {"path": path, "name": r["project"], "family": r["family"],
                 "rows": [], "rep": r, "repo": bool(r.get("is_repo")),
                 "commits": dict(r.get("week_commits") or {}),
                 "log": dict(r.get("_week_log") or {}),
                 "sessions": sessions_by_cwd.get(path, {}), "col": None, "why": ""}
            by_path[path] = p
            projects.append(p)
        p["rows"].append(r)
    for p in projects:
        p["n_commits"] = sum(p["commits"].values())
        p["n_sessions"] = sum(len(v) for v in p["sessions"].values())
        # ACTIVITY IN THE WINDOW is the fall's own bytes: commits, or sessions.
        p["in_window"] = bool(p["n_commits"] or p["n_sessions"])
        p["hot"] = max(row["touched_ts"] for row in p["rows"])
        p["active"] = any(row["active"] for row in p["rows"])
    fam_hot = {}
    for p in projects:
        fam_hot[p["family"]] = max(fam_hot.get(p["family"], -1e18), p["hot"])
    ranked = sorted([p for p in projects if p["in_window"]],
                    key=lambda p: (-fam_hot[p["family"]], p["family"], -p["hot"],
                                   p["name"].lower()))
    # EVERY PROJECT WITH WORK IN THE WINDOW IS A HEAD. The crown wraps
    # into rows at the window's own width (the CSS grid does it), so no head is
    # ever reachable only by widening the window — there is no cap, and no band
    # tile standing in for a head that did not fit.
    columns = ranked
    for i, p in enumerate(columns):
        p["col"] = i
    band = []
    rest = []
    for p in projects:
        if p["in_window"]:
            continue
        p["why"] = ("quiet for six weeks: no commit and no session since %s" % since
                    if p["active"] else "dormant · idle %s" % p["rep"]["idle_txt"])
        p["band_why"] = p["why"]
        rest.append(p)
    rest.sort(key=lambda p: (not p["active"], -p["hot"], p["name"].lower()))
    band.extend(rest)

    # Tile order = index order in the JSON: hub first, then the columns left to
    # right, then the band.
    ordered = list(hub_rows)
    seen_rows = set()
    for p in columns + band:
        if p["path"] in seen_rows:
            continue
        seen_rows.add(p["path"])
        ordered.extend(p["rows"])
    index = {id(r): i for i, r in enumerate(ordered)}
    col_of = dict((p["path"], p["col"]) for p in columns)
    why_of = dict((p["path"], p["why"]) for p in band if p.get("why"))
    # WHERE A LIVE SESSION BELONGS: in the hub folder its title's own
    # lane token names the project (`ACT — Hub/Desk: …` is Hub/Desk);
    # anywhere else the folder does — the deepest project folder that holds it,
    # named as its head names it. A session on the OTHER machine has a path this
    # machine does not, so there the folder's own name finds it (both machines
    # keep one folder name per project), and only when exactly one folder has it.
    lane_row_of = dict((str(r["lane"]).lower(), r) for r in ordered)
    folder_rows, _seen_folders, _per_folder = [], set(), {}
    for r in ordered:
        _k = _path_key(r["path"])
        _per_folder[_k] = _per_folder.get(_k, 0) + 1
        if _k and _k not in _seen_folders:
            _seen_folders.add(_k)
            folder_rows.append((_k, r))
    folder_rows.sort(key=lambda kr: -len(kr[0]))
    _by_name = {}
    for _k, r in folder_rows:
        _by_name.setdefault(_k.rsplit("/", 1)[-1], []).append(r)

    def folder_word(r):
        """A folder as its head names it: the lane for a one-lane folder, else the project."""
        return r["lane"] if _per_folder.get(_path_key(r["path"]), 0) == 1 else r["project"]

    def session_home(a):
        """(the project it works on, in words · the lane row its ▶ open goes to, or None)"""
        tok = title_lane(a.get("title"))
        ck = _path_key(a.get("cwd"))
        home = next((r for k, r in folder_rows if ck and (ck == k or ck.startswith(k + "/"))), None)
        leaf = ck.rsplit("/", 1)[-1] if ck else ""
        if home is None and leaf and len(_by_name.get(leaf) or []) == 1:
            home = _by_name[leaf][0]
        lane_row = lane_row_of.get(tok.lower()) if tok else None
        if a.get("in_hub") and tok:
            project = tok
        elif home is not None:
            project = folder_word(home)
        else:
            parts = [x for x in re.split(r"[\\/]+", str(a.get("cwd") or "")) if x]
            project = parts[-1] if parts else (a.get("dir") or "a folder")
        return project, (lane_row if lane_row is not None else home)

    # Every lane carries its column, its constellation key and — for the FIRST
    # row of a project, so two lanes in one folder never double a nerve — the
    # live sessions the pulse saw there. One nerve per session, no more.
    lane_objs, claimed, lane_live = [], set(), {}
    for r in ordered:
        obj = _lane_json(r, machine)
        obj["key"] = tile_key(r)
        path = str(r["path"]).rstrip("/\\")
        obj["col"] = col_of.get(path)
        obj["hub"] = bool(r["is_hub"])
        if why_of.get(path):
            obj["why"] = why_of[path]
        mine = []
        if path not in claimed:
            claimed.add(path)
            for a in live_sessions.get(path, []):
                s_ = {"machine": a.get("machine") or "", "mind": a.get("mind") or "CLAUDE",
                      "model": a.get("model") or "", "id": a.get("id") or "",
                      "minutes": a.get("minutes_ago")}
                about = a.get("title") or a.get("first_line")
                if about:           # the nerve's hover says what it is about first
                    s_["about"] = _one_line(about, 60)
                mine.append(s_)
                lane_live.setdefault(len(lane_objs), []).append(a)
        obj["sessions"] = mine
        lane_objs.append(obj)
    lanes_json = json.dumps(lane_objs, ensure_ascii=False).replace("</", "<\\/")
    n_nerves = sum(len(o.get("sessions") or []) for o in lane_objs)

    # ── arcs: the notes that crossed between projects, at their own week
    names = sorted({r["project"] for r in others})
    window_days = int((now_ts - window_start) / DAY) + 2
    col_by_name = dict((p["name"], p["col"]) for p in columns)
    HUB_NAME = "Exocortex hub"

    def side(name):
        if name == "hub":
            return (None, HUB_NAME)
        return (col_by_name.get(name), name)

    arcs = {}
    pair_letters = {}       # every letter between a pair in the fall's weeks
    for msg in read_inbox(names, days=window_days):
        when = parse_iso(msg["date"])
        if when is None:
            continue
        wk = _wkey(when)
        if wk not in wkeys:
            continue
        src = msg["src"] or "hub"
        for tgt in msg["tgts"]:
            if tgt == src:
                continue
            a, an = side(src)
            b, bn = side(tgt)
            if a is None and b is None:
                continue          # both ends outside the fall: nothing to draw
            entry = arcs.setdefault((an, bn, wk),
                                    {"a": a, "b": b, "an": an, "bn": bn, "w": wk,
                                     "mon": wlabel.get(wk, wk), "n": 0, "text": "",
                                     "lines": []})
            entry["n"] += 1
            pair_letters.setdefault(tuple(sorted((an, bn))), {})[(msg.get("lineno") or 0, an, bn)] = {
                "date": msg["date"], "lineno": msg.get("lineno") or 0, "an": an, "bn": bn,
                "line": msg.get("line") or "", "text": msg.get("text") or ""}
            entry["text"] = words(msg["text"], 12)      # the latest wins (file order)
            if len(entry["lines"]) < 8:                 # what the arc answers with
                entry["lines"].append({"lineno": msg.get("lineno") or 0,
                                       "line": msg.get("line") or "",
                                       "date": msg["date"]})
    # gates: a lane that must wait for another draws a dashed arc this week
    gates, seen_gate = [], set()
    for r in ordered:
        if not r["gated"]:
            continue
        b = col_of.get(str(r["path"]).rstrip("/\\"))
        if b is None:
            continue
        dep = _norm(r["depends_on"])
        for other in ordered:
            if other is r or other["project"] == r["project"]:
                continue
            if _norm(other["lane"]) and _norm(other["lane"]) in dep:
                a = col_of.get(str(other["path"]).rstrip("/\\"))
                if a is None or a == b or (a, b) in seen_gate:
                    continue
                seen_gate.add((a, b))
                gates.append({"a": a, "b": b, "text": "gate · %s waits on %s: %s"
                              % (r["lane"], other["lane"], r["depends_on"]),
                              "lane": r["lane"], "waits_on": other["lane"],
                              "line": r["depends_on"], "i": index[id(r)]})
    arc_list = sorted(arcs.values(), key=lambda e: (e["w"], e["an"], e["bn"]))
    fall_json = json.dumps({
        "weeks": [{"key": w["key"], "label": w["label"], "mon": w["mon"]} for w in weeks],
        "cols": [{"i": p["col"], "name": p["name"], "repo": p["repo"],
                  "commits": dict((k, v) for k, v in p["commits"].items() if k in wkeys),
                  "sessions": dict((k, [{"mind": s["mind"], "id": s["id"]} for s in v])
                                   for k, v in p["sessions"].items() if k in wkeys)}
                 for p in columns],
        "arcs": [dict((k, v) for k, v in e.items() if k != "lines") for e in arc_list],
        "gates": [dict((k, v) for k, v in g.items() if k in ("a", "b", "text")) for g in gates],
    }, ensure_ascii=False).replace("</", "<\\/")
    n_msgs = sum(e["n"] for e in arcs.values())

    # ── what every mark in the fall answers with ────────────────
    def week_span(w):
        a = datetime.fromtimestamp(w["start"])
        b = a + timedelta(days=6)
        return "%s – %s" % (a.strftime("%a %d %b").replace(" 0", " "),
                            b.strftime("%a %d %b").replace(" 0", " "))

    MORD = mind_sort_index(reg())
    SIDE = {"codex": "Codex (the OpenAI side)", "claude": "Claude Code", "grok": "Grok Build"}
    wk_commits = dict((w["key"], 0) for w in weeks)
    wk_sessions = dict((w["key"], 0) for w in weeks)
    wk_notes = dict((w["key"], 0) for w in weeks)
    for p in columns:
        i = p["col"]
        lane_i = index.get(id(p["rep"]))
        goto = {"label": "Open lane", "lane": lane_i} if lane_i is not None else None
        for w in weeks:
            n = p["commits"].get(w["key"], 0)
            wk_commits[w["key"]] += n
            log = (p.get("log") or {}).get(w["key"]) or []
            brow = [["project", p["name"]], ["week", week_span(w)]]
            if p["repo"]:
                brow.append(["commits", "%d" % n])
            else:
                brow.append(["git", "no git history in this folder"])
            for c in log:
                brow.append([c.get("h") or "?", "%s · %s" % (c.get("s") or "", c.get("d") or "")])
            if n > len(log):
                brow.append(["and", "%d more this week" % (n - len(log))])
            mk("stream:%d:%s" % (i, w["key"]),
               ("this week's commits on %s" if w is weeks[0] else "one week's commits on %s") % p["name"],
               brow, action=goto)
            ss = sorted(p["sessions"].get(w["key"]) or [],
                        key=lambda s: (MORD.get(str(s.get("mind") or "").upper(), 9), s.get("id") or ""))
            wk_sessions[w["key"]] += len(ss)
            shown = min(6, len(ss))
            for k in range(shown):
                s = ss[k]
                if k == shown - 1 and len(ss) > shown:
                    rest = ss[shown - 1:]
                    brow = [["week", week_span(w)], ["in", p["name"]],
                            ["sessions", "%d this week" % len(ss)]]
                    for extra in rest[:20]:
                        brow.append([str(extra.get("mind") or "CLAUDE"),
                                     "…%s · %s · last active %s" % (extra.get("id") or "?",
                                     SIDE.get(extra.get("kind") or "claude", "Claude Code"),
                                     extra.get("when") or "?")])
                    if len(rest) > 20:
                        brow.append(["and", "%d more" % (len(rest) - 20)])
                    mk("sdot:%d:%s:%d" % (i, w["key"], k), "the sessions this dot stands for",
                       brow, action=goto)
                else:
                    mk("sdot:%d:%s:%d" % (i, w["key"], k), "a session that ran this week",
                       [["mind", s.get("mind") or "CLAUDE"], ["machine", machine],
                        ["side", SIDE.get(s.get("kind") or "claude", "Claude Code")],
                        ["model", s.get("model") or ""],
                        ["session id", "…%s" % (s.get("id") or "?")],
                        ["last active", s.get("when") or ""],
                        ["worked in", p["name"]], ["week", week_span(w)]],
                       action=goto)
    for ai, e in enumerate(arc_list):
        wk_notes[e["w"]] = wk_notes.get(e["w"], 0) + e["n"]
        # the arc answers with the letters between its PAIR, both ways,
        # over the fall's weeks — time first, oldest at the top, the whole
        # INBOX line on hover and its line number on a click
        letters = sorted(pair_letters.get(tuple(sorted((e["an"], e["bn"]))), {}).values(),
                         key=lambda x: (x["date"], x["lineno"]))
        items = []
        for x in letters:
            day = parse_iso(x["date"])
            items.append({"at": day.strftime("%a %d %b") if day else x["date"],
                          "words": "%s → %s · %s" % (x["an"], x["bn"], x["text"]),
                          "short": "%s → %s · %s" % (x["an"], x["bn"], _first_words(x["text"])),
                          "full": x["line"], "src": "INBOX.md:%d" % x["lineno"]})
        brow = [["this arc", "%s → %s · week of %s · %d note%s"
                 % (e["an"], e["bn"], e["mon"], e["n"], "" if e["n"] == 1 else "s")]]
        mk("arc:%d" % ai, "the notes between %s and %s" % (e["an"], e["bn"]), brow,
           listing=listing_of(items, now_mark=False),
           share=("pair",) + tuple(sorted((e["an"], e["bn"]))))
    for gi, g in enumerate(gates):
        mk("gate:%d" % gi, "a lane waiting on another",
           [["the lane", g["lane"]], ["waits on", g["waits_on"]],
            ["the gate line", g["line"]],
            ["what it means", "its opener may not be handed over until that line is in hand"]],
           action={"label": "Open lane", "lane": g["i"]})
    for i, obj in enumerate(lane_objs):
        for a in lane_live.get(i) or []:
            _proj, _home = session_home(a)
            heading, brows, foot = live_card(dict(a, folder=obj.get("folder") or ""), _proj)
            mk("nerve:%d:%s" % (i, a.get("id") or ""), heading, brows, foot=foot,
               action={"label": "Open lane", "lane": i}, listing=turn_listing(a),
               share=("turns", a.get("machine") or "", a.get("transcript") or a.get("id") or ""))
    inbound = {}
    for e in arcs.values():
        inbound[e["bn"]] = inbound.get(e["bn"], 0) + e["n"]

    def face_launch(r, short=False):
        """The one-click start on a face. A Claude lane with an opener on
        file gets its own launch link; one without gets the front door; a Codex
        lane gets the paste, because there is no codex:// scheme to open.

        The head IS the project's face now that nothing stands in for it,
        so it carries the same words as a tile. A head is 96 px wide
        at its narrowest: there the CSS shows the glyph alone (`data-g`) and the
        words stay the link's own name and its title; a head with room for them
        shows them — the count beside it is real bytes and does not get clipped."""
        i = index[id(r)]
        if is_grok_lane(r) or is_codex_lane(r):
            return ("<button class=\"launch\" type=\"button\" data-copy-lane=\"%d\"%s title=\"%s\">Copy prompt</button>"
                    % (i, " data-g=\"⧉\"" if short else "",
                       _e("copy this lane's startup prompt · " + lane_codex_note(r))))
        g = " data-g=\"▶\"" if short else ""
        href = lane_launch(r, machine)
        if href:
            return ("<a class=\"launch\" href=\"%s\"%s title=\"launch a session in %s and hand it this lane\">▶ Launch</a>"
                    % (_e(href), g, _e(r["path"])))
        door = lane_front_door(r)
        if not door:
            return ""
        return ("<a class=\"launch\" href=\"%s\"%s title=\"open a session in %s with: %s\">▶ Open</a>"
                % (_e(door), g, _e(r["path"]), _e(FRONT_DOOR)))

    def tile(r, size="", cool=False, why="", col=None):
        heat = _heat(r, now_ts)
        hot = "hot" if heat in ("h3", "h2") else ""
        cls = " ".join(x for x in ("tile", "cool" if cool else tone.get(r["state"], "wait"), hot, size) if x)
        kin_mark = "<span class=\"kin\">%s · %s</span>" % (_e("dormant" if not r["active"] else "paused"), _e(_carrier_mark(r))) if cool else ""
        st = ("<span class=\"st gt\">🔒 %s</span>" if r["gated"] else "<span class=\"st\">%s</span>") % _e(state_word.get(r["state"], r["state"]))
        est = ""
        if r["remaining"] is not None:
            est = "<span class=\"est\">≈ %g sitting%s left%s</span>" % (r["remaining"], "" if r["remaining"] == 1 else "s", (" · due %s" % r["due"]) if r["due"] else "")
        n_in = inbound.get(HUB_NAME if r["is_hub"] else r["project"], 0)
        alive = live_sessions.get(str(r["path"]).rstrip("/\\"), [])
        mail, n_post = post_mail([post_key[id(r)]], "mail:%d" % index[id(r)])
        if n_post is None:      # no post file anywhere: the old count, byte for byte
            mail = ("<span class=\"mail\" title=\"%d note%s waiting in the INBOX\">✉ %d</span>" % (n_in, "" if n_in == 1 else "s", n_in)) if n_in else ""
        badge = live_dots(alive)
        mail += badge
        mchs = []
        for a in alive:
            if a.get("machine") and a["machine"] not in mchs:
                mchs.append(a["machine"])
        on = str(r.get("on") or "").strip().upper()
        chip_title = ("live on " + " + ".join(mchs)) if mchs else (("last worked on " + on + " (opener)") if on and on != "—" else "")
        if not mchs and on and on != "—":
            mchs = [on]
        mchip = "".join("<span class=\"mc mc-%s\" title=\"%s\">%s</span>" % (_e(m.lower()), _e(chip_title), _e(m)) for m in mchs)
        big = (not cool) and (size in ("big", "hero") or r["is_hub"])
        if big:
            last = r.get("last_subject") or (r["_status"]["now_first"] if r.get("_status") else "")
            ban = ("<span class=\"ban\">"
                   "<span class=\"bl\"><b>last</b>%s <i>· %s ago</i></span>"
                   "<span class=\"bl\"><b>focus</b>%s</span>"
                   "<span class=\"bl next\"><b>next</b>%s</span>%s</span>"
                   % (_e(words(debracket(last), 14)), _e(r["idle_txt"]), _e(r["where"]), _e(r["next_move"]),
                      ("<span class=\"bl live\"><b>live</b>%s</span>" % badge) if alive else ""))
            body = "%s<span class=\"nm\">%s</span>" % (ban, _e(r["lane"]))
        else:
            body = "<span class=\"nm\">%s</span><span class=\"wh\">%s</span><span class=\"nx\"><b>→</b>%s</span>" % (_e(r["lane"]), _e(why or r["where"]), _e(r["next_move"]))
        return ("<div class=\"%s\" role=\"button\" tabindex=\"0\" data-i=\"%d\" data-key=\"%s\" data-fam=\"%s\"%s>"
                "%s<span class=\"grp\">%s%s%s</span>%s%s%s"
                "<span class=\"ft\"><span class=\"ages\">⌛ %s · ⏱ %s</span>%s%s</span></div>"
                % (cls, index[id(r)], _e(tile_key(r)), _e(r["family"]),
                   ("" if col is None else " data-col=\"%d\"" % col),
                   kin_mark, _e(_carrier_mark(r)), mchip, mail, st, body, est,
                   _e(r["age_txt"]), _e(r["idle_txt"]), face_launch(r),
                   # a cool tile's CSS hid this mark; a mark nobody can see is
                   # not written at all (nothing superfluous)
                   "" if cool else "<span class=\"pr\">▶ prompt</span>"))

    def head(p):
        """One project head: the eyebrow, the name, its lanes as chips
        where a folder runs several, and the foot — open items and the prompt.
        The top border is the state; the body is the state's own tile ground."""
        r = p["rep"]
        heat = _heat(r, now_ts)
        cls = "ph %s%s" % (tone.get(r["state"], "wait"), " hot" if heat in ("h3", "h2") else "")
        alive = live_sessions.get(p["path"], [])
        mchs = []
        for a in alive:
            if a.get("machine") and a["machine"] not in mchs:
                mchs.append(a["machine"])
        on = str(r.get("on") or "").strip().upper()
        chip_title = ("live on " + " + ".join(mchs)) if mchs else (("last worked on " + on + " (opener)") if on and on != "—" else "")
        if not mchs and on and on != "—":
            mchs = [on]
        mchip = "".join("<span class=\"mc mc-%s\" title=\"%s\">%s</span>" % (_e(m.lower()), _e(chip_title), _e(m)) for m in mchs)
        n_in = inbound.get(p["name"], 0)
        mail, n_post = post_mail([post_key[id(x)] for x in p["rows"]],
                                 "mail:head:%d" % index[id(r)])
        if n_post is None:      # no post file anywhere: the old count, byte for byte
            mail = ("<span class=\"mail\" title=\"%d note%s waiting in the INBOX\">✉ %d</span>" % (n_in, "" if n_in == 1 else "s", n_in)) if n_in else ""
        short = {"green": "ready", "amber": "waiting", "red": "attention"}
        st = ("<span class=\"sx gt\" title=\"%s\">🔒 %s</span>" if r["gated"] else "<span class=\"sx\" title=\"%s\">%s</span>") % (
            _e("%s — %s" % (state_word.get(r["state"], r["state"]), r["state_words"])), _e(short.get(r["state"], r["state"])))
        many = len(p["rows"]) > 1
        name = p["name"] if many else r["lane"]
        chips = ""
        if many:
            chips = "<span class=\"chips\">%s</span>" % "".join(
                "<span class=\"lc %s\" data-i=\"%d\" title=\"%s — %s\">%s</span>"
                % (tone.get(x["state"], "wait"), index[id(x)], _e(x["lane"]), _e(state_word.get(x["state"], x["state"])),
                   _e(x["lane"].split("/")[-1]))
                for x in p["rows"])
        urgent = ("<span class=\"u\">!%d</span> " % r["urgent_items"]) if r["urgent_items"] else ""
        mark = _carrier_mark(r)
        title = "%s · %s · %d commit%s and %d session%s in six weeks" % (
            p["name"], state_word.get(r["state"], r["state"]),
            p["n_commits"], "" if p["n_commits"] == 1 else "s",
            p["n_sessions"], "" if p["n_sessions"] == 1 else "s")
        return ("<div class=\"%s\" role=\"button\" tabindex=\"0\" data-i=\"%d\" data-col=\"%d\" data-key=\"%s\" data-fam=\"%s\" title=\"%s\">"
                "<span class=\"eb\">%s%s%s%s</span>"
                "<span class=\"nm\">%s</span>%s"
                "<span class=\"fo\"><span>%s%d open</span>%s</span></div>"
                % (cls, index[id(r)], p["col"], _e(tile_key(r)), _e(p["family"]), _e(title),
                   ("<span title=\"%s\">%s</span>" % (_e(mark), _e(mark.split(" ")[0]))),
                   mchip, live_dots(alive), mail + st,
                   _e(name), chips, urgent, r["open_items"],
                   # the head is 78 px tall: ONE control, and it is the one that
                   # starts the session. The prompt itself is one click
                   # away inside the card, where a Codex lane's ▶ still points.
                   face_launch(r, short=True) or "<span class=\"pr\" title=\"open the startup prompt\">▶</span>"))

    out = []
    out.append("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">")
    out.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    # The page refreshes itself every five minutes whatever drew it:
    # a tree left open must never go stale behind the
    # heartbeat. Scroll-keep in HTML_JS is unconditional already.
    out.append("<meta http-equiv=\"refresh\" content=\"300\">")
    out.append("<title>Tree — Exocortex</title>")
    out.append("<link rel=\"stylesheet\" href=\"%s\">" % HTML_FONTS_FILE)
    sky = find_sky()
    out.append("<style>%s%s</style></head><body><div class=\"wrap\">" % (html_css(reg()), (":root{--sky-image:url(\"%s\")}" % sky) if sky else ""))
    out.append("<svg class=\"lines\" id=\"lines\" aria-hidden=\"true\"></svg>")
    brain = brain_sky(roots)
    LAST_BRAIN.clear(); LAST_BRAIN.update(brain)      # the reader bridge
    n_const = len({m["project"] for m in brain["memories"]})
    sky_markup = sky_svg(brain)
    marks.update(brain.get("marks") or {})       # the sky's own answers
    SKY_REPORT.clear()
    SKY_REPORT.update({"texts": len(brain.get("sky_boxes") or []),
                       "overlaps": brain.get("sky_overlaps", 0),
                       "journal": len(brain["journal"]), "jdots": brain.get("n_jdots", 0),
                       "laws": len(brain["laws"]), "ticks": brain.get("n_ticks", 0),
                       "promoted": sum(1 for j in brain["journal"] if j["promoted"]),
                       "drops": brain.get("n_drops", 0)})
    out.append("<header class=\"plate%s\"><div class=\"over\"><span>Cortex · what the exocortex holds about you · %s</span><span>%s</span></div>"
               "<div class=\"skyband\">%s</div>"
               % (" sky" if sky else "", _e(machine), _e(stamp), sky_markup))
    out.append(usage_bands(roots))                # the meters, dated, under the sky
    # The Sky rule allows ONE caption line of counts, and the decoding
    # sentences live in the inspector now: click a count for its
    # list, click a row label for what that row of the sky holds.
    _mem = sorted(brain["memories"], key=lambda m: m.get("age") or 0.0)
    _by_proj = {}
    for _m in brain["memories"]:
        _by_proj[_m["project"]] = _by_proj.get(_m["project"], 0) + 1
    _jrn = sorted(brain["journal"], key=lambda j: j["date"], reverse=True)
    _laws = sorted(brain["laws"], key=lambda l: l.get("date") or "", reverse=True)
    _sk_named = {}
    for _e2 in brain.get("edges") or []:
        if _e2.get("kind") == "skill":
            _sk_named.setdefault(_e2["a"][1], []).append(_e2["b"][0])
    _links = [e for e in (brain.get("edges") or []) if e.get("kind") == "link"]
    _dfacts = brain.get("dossier_facts") or {}
    cap = [
        ("memories", len(brain["memories"]), "sky:count:memories", "every memory the exocortex holds",
         capped([[m["project"], "%s · changed %s ago" % (m["name"], _span(m.get("age") or 0.0))] for m in _mem])),
        ("constellations", n_const, "sky:count:constellations", "the projects the memories group into",
         capped([[p, "%d memor%s" % (n, "y" if n == 1 else "ies")]
                 for p, n in sorted(_by_proj.items(), key=lambda kv: (-kv[1], kv[0]))])),
        ("links", brain.get("n_links", 0), "sky:count:links", "the links drawn between files",
         capped([["%s · %s" % (e["a"][0], e["a"][1]), "→ %s · %s" % (e["b"][0], e["b"][1])] for e in _links])),
        ("skills", len(brain["skills"]), "sky:count:skills", "the skills installed beside the brain",
         capped([[s, ", ".join(sorted(set(_sk_named.get(s) or []))) or "names no project"]
                 for s in sorted(brain["skills"])])),
        ("laws", len(brain["laws"]), "sky:count:laws", "your ratified rules, and the engine's own laws",
         capped([[l.get("date") or "undated", ("engine · " if l.get("whose") == "engine" else "yours · ") + l["name"]]
                 for l in _laws])),
        ("journal lines", len(brain["journal"]), "sky:count:journal", "the dated lines of dossier/TAUGHT.md",
         capped([[j["date"], j["title"]] for j in _jrn])),
        ("dossier pages", len(brain.get("dossier_told", brain["dossier"])), "sky:count:dossier",
         "the pages of your own dossier",
         capped([[d, NOT_TOLD if _dfacts.get(d, {}).get("state") == "empty" else
                  "%.1f KB · changed %s ago" % ((_dfacts.get(d, {}).get("bytes") or 0) / 1024.0,
                 _span(_dfacts.get(d, {}).get("age") or 0.0))] for d in brain["dossier"]])),
    ]
    out.append("<div class=\"capwrap\"><p class=\"skycap\">%s</p></div>"
               % " · ".join("<button class=\"cnt\" type=\"button\"%s><b>%d</b> %s</button>"
                            % (mk(mid, kind, brow, when_empty=NONE_YET), n, _e(label))
                            for label, n, mid, kind, brow in cap))
    out.append("<hr class=\"rule\">")
    out.append("<div class=\"head\"><div class=\"hl\">")
    n_ideas, n_new_ideas = ideas_counts(roots)
    here_name = str(roots.get("name", "")).lower()
    live_here = (pulse_stamps.get(here_name) or {}).get("n", 0)
    _act_rows = capped([[r["lane"], "%s · %s" % (state_word.get(r["state"], r["state"]), r["where"])]
                        for r in (hub_rows + active)])
    _fall_rows = capped([[p["name"], "%d commit%s and %d session%s in six weeks"
                          % (p["n_commits"], "" if p["n_commits"] == 1 else "s",
                             p["n_sessions"], "" if p["n_sessions"] == 1 else "s")] for p in columns])
    _note_rows = capped([["%s · %s → %s" % (e["mon"], e["an"], e["bn"]),
                          (e["lines"][0]["line"] if e["lines"] else e["text"])] for e in arc_list])
    _prompt_rows = capped([[r["lane"], "written %s · %s" % (r["written"] or "?", r["opener"])]
                           for r in rows if r["active"] and r["opener"]])
    # THE POSTMAN'S OWN CHIP: on the strip ONLY while a note
    # for the owner is waiting — not acked, and younger than owner_hours. An empty
    # inbox is not news, and a chip nobody needs is a mark with no job.
    owner_chip = ""
    _notes = post_owner_notes(post_facts)
    if _notes:
        _owner_rows = []
        for n in _notes:
            _owner_rows.append(["note" if n.get("kind") != "nudge" else "nudge",
                               n.get("line") or n.get("to") or ""])
            _owner_rows.append(["first seen", n.get("first_seen") or ""])
            # ONE NOTE, ONE RAISE LINE PER MACHINE THAT HAS A VIEW OF IT.
            # A `to: OWNER` letter is owned by every machine
            # that sees it, so the postman hands one row per token with each
            # machine's own facts inside it, this machine's first — never the
            # same note twice on the chip.
            for _v in (n.get("views") or [{"machine": n.get("machine"),
                                           "raised": n.get("raised") or {}}]):
                _raised = _v.get("raised") or {}
                _mch = str(_v.get("machine") or "").upper()
                _owner_rows.append(["raised",
                                   ("on the %s at %s" % (_mch, _hhmm(_raised.get("when"))))
                                   if _raised.get("how") in ("osascript", "toast")
                                   else ("%s: not raised — %s"
                                         % (_mch, _raised.get("why") or "not yet"))])
            _push = n.get("push") or {}
            if _push.get("state"):
                _owner_rows.append(["phone", {
                    "called": "pushed by «%s» — the tool said: %s"
                              % (_push.get("title") or _push.get("session") or "?",
                                 _push.get("result") or "(nothing recorded)"),
                    "asked": "asked of «%s»" % (_push.get("title") or "?"),
                    "queued": "waiting on a turn in «%s»" % (_push.get("title") or "?"),
                    "lapsed": _push.get("why") or "nobody took a turn in time",
                    "off": "notes to the phone are turned off here",
                }.get(_push.get("state"), _push.get("state"))])
        _owner_rows.append(["to clear these", "say “got it” in any session"])
        owner_chip = ("<button class=\"cnt\" type=\"button\" style=\"color:var(--amber-ink)\"%s>"
                     "✉ %d for you</button>"
                     % (mk("count:owner", "the notes waiting for you", capped(_owner_rows, 90)),
                        len(_notes)))
    out.append("<div class=\"strip\">"
               "<button class=\"cnt\" type=\"button\"%s>%d active</button>"
               "<button class=\"cnt\" type=\"button\"%s>%d in the fall</button>"
               "<button class=\"cnt\" type=\"button\"%s>%d notes in six weeks</button>"
               "<button class=\"cnt\" type=\"button\"%s>%d prompt%s on file</button>"
               "<button class=\"cnt\" type=\"button\"%s>%d live</button>%s%s</div>"
               % (mk("count:active", "the lanes counted here", _act_rows, when_empty=NONE_YET),
                  len(active) + len(hub_rows),
                  mk("count:fall", "the projects the fall shows", _fall_rows,
                     when_empty=NONE_YET), len(columns),
                  mk("count:notes", "the notes that crossed between projects in six weeks", _note_rows,
                     when_empty=NONE_YET), n_msgs,
                  mk("count:prompts", "the lanes whose startup prompt is on file", _prompt_rows,
                     when_empty=NONE_YET),
                  with_opener, "" if with_opener == 1 else "s",
                  # LIVE is the pulse's own count for this machine — the same
                  # number the nameplate and the machine root say, and
                  # the one place the page says "nothing is running".
                  mk("count:live", "the sessions the pulse sees on this machine",
                     [["pulse", ("%s ago" % _span((pulse_stamps.get(here_name) or {}).get("age_h", 0) / 24.0))
                       if (pulse_stamps.get(here_name) or {}).get("age_h") is not None else "no pulse yet"],
                      ["drawn as nerves", "%d" % n_nerves]]
                     + [[a.get("mind") or "CLAUDE",
                         "…%s · %s · %s" % (a.get("id") or "?", path,
                                            ("%g min ago" % a["minutes_ago"]) if a.get("minutes_ago") is not None else "just now")]
                        for path in sorted(live_sessions) for a in live_sessions[path]
                        if str(a.get("machine") or "").upper() == machine]
                     + [["every one, by name", "in the LIVE line just below"]],
                     # the count is the LIVE strip's anchor; the format
                     # string above stays byte-identical, gate-improvements pins it
                     highlight="#live") + " data-jump=\"live\"",
                  live_here,
                  # The ideas chip: on the strip only while there are ideas to
                  # read — an empty Someday is not news (Nothing-superfluous).
                  ("<button class=\"cnt\" type=\"button\"%s>✦ %d idea%s · %d new</button>"
                   % (mk("count:ideas", "the ideas waiting in the inbox",
                         [["%s · %s" % (st, when), text] for st, when, text in ideas_lines(roots)]
                         + [["file", "IDEAS.md at the hub root"],
                            ["how one gets here", "say \u201cidea: …\u201d in any session; Tuesday judges it"]]),
                      n_ideas, "" if n_ideas == 1 else "s", n_new_ideas)) if n_ideas else "",
                  owner_chip + improvements_chip(roots)))   # BQ-026 hook B: the ledger's chip
    # ── LIVE: every session the pulse sees, on every machine, by name.
    #    Most recent first; a line answers with the session's card, ▶ open goes
    #    to the lane it works in. Never a launch link: a live session already
    #    holds its lane, and a second one opened beside it would write over it.
    live_all = sorted((a for _rows in live_sessions.values() for a in _rows),
                      key=lambda a: (a.get("minutes_now") is None,
                                     a.get("minutes_now") or 0.0, a.get("id") or ""))
    _lines = []
    _marks = mail_marks(roots)                    # ✉ N on a window holding letters
    for _k, a in enumerate(live_all):
        if a.get("kind") == "job":
            try:
                from offload import job_line
            except ImportError:
                job_line = None     # no offload.py beside the collector: the job row is left out
            if job_line is None:
                continue
            _job_words = job_line(a)
            color = "var(--amber-ink)" if a.get("state") == "running" else "inherit"
            _lines.append('<li><a class="lsr" href="%s" style="color:%s" title="Full record on %s"><span class="lst">%s</span></a></li>' %
                          (_e(a.get("show_uri") or ""), color, _e(a.get("machine") or ""), _e(_job_words)))
            continue
        _proj, _home = session_home(a)
        _li = index.get(id(_home)) if _home is not None else None
        heading, brows, foot = live_card(a, _proj)
        _att = mk("live:%d" % _k, heading, brows, foot=foot,
                  action=({"label": "Open %s" % _home["lane"], "lane": _li}
                          if _li is not None else None), listing=turn_listing(a),
                  share=("turns", a.get("machine") or "", a.get("transcript") or a.get("id") or ""))
        _name = a.get("title") or a.get("first_line") or "a session"
        _facts = " · ".join(x for x in (_proj, a.get("machine") or "", a.get("mind") or "",
                                        minutes_words(a.get("minutes_now")
                                                      if a.get("minutes_now") is not None
                                                      else a.get("minutes_ago"))) if x)
        # say only what is known: its own lane (its title names it, or its folder
        # holds one lane), else the first lane of the folder it works in
        _sure = (title_lane(a.get("title")).lower() == str(_home["lane"]).lower()
                 or _per_folder.get(_path_key(_home["path"]), 0) == 1) if _home is not None else False
        _why = ("the lane this session works in" if _sure else
                "a lane of %s, the folder this session works in" % _home["project"]) if _home is not None else ""
        _open = ("<button class=\"lso\" type=\"button\" data-open=\"%d\" title=\"open the card of %s, "
                 "%s\">▶ open</button>" % (_li, _e(_home["lane"]), _e(_why))
                 if _li is not None else "")
        _mm = _marks.get(str(a.get("id") or ""))
        _env = (("<span class=\"lsm\" style=\"color:var(--amber-ink)\" title=\"%s\">&nbsp;✉ %d</span>"
                 % (_e(mail_mark_words(_mm)), int(_mm.get("count") or 0))) if _mm else "")
        _lines.append("<li><button class=\"lsr\" type=\"button\"%s title=\"%s\">"
                      "<span class=\"lst\">%s</span><span class=\"lsm\">&nbsp;· %s</span>%s</button>%s</li>"
                      % (_att, _e(_name), _e(_name), _e(_facts), _env, _open))
    if _lines:
        # the count above is this machine's; when the strip holds more than one
        # machine it says how many are where, so the two numbers agree on sight
        _on = []
        for a in live_all:
            _m = a.get("machine") or "?"
            if _m not in [x[0] for x in _on]:
                _on.append([_m, 0])
            next(x for x in _on if x[0] == _m)[1] += 1
        _on.sort(key=lambda x: (x[0] != machine, x[0]))
        _where = (" · " + " · ".join("%d on the %s" % (n, m) for m, n in _on)) if len(_on) > 1 else ""
        out.append("<div class=\"livestrip\" id=\"live\" aria-label=\"Every live session\">"
                   "<span class=\"lsh\">LIVE · %d%s</span><ul>%s</ul></div>"
                   % (len(_lines), _e(_where), "".join(_lines)))
    else:
        out.append("<div class=\"livestrip\" id=\"live\" aria-label=\"Every live session\">"
                   "<span class=\"lsh\">no live sessions</span></div>")
    # The legend is written once the roots below have said which machines and
    # which minds are real on this page (Universality: never a fixed table).
    legend_slot = len(out)
    out.append("")
    if stale:
        chip_kind = "the lanes whose startup prompt is out of date"
        chip_rows = [[lane, "its opener names a commit this repo no longer has — it is not handed over"]
                     for lane in stale]
        chip_first = next((r for r in rows if r["lane"] in stale), None)
    elif owe:
        chip_kind = "the lanes with no startup prompt on file"
        chip_rows = [[r["lane"], "no OPENER file in %s — its closing session writes one" % r["path"]]
                     for r in owe_rows]
        chip_first = owe_rows[0] if owe_rows else None
    else:
        chip_kind = "every active lane has a startup prompt on file"
        chip_rows = [[r["lane"], "written %s · %s" % (r["written"] or "?", r["opener"])]
                     for r in rows if r["active"] and r["opener"]]
        chip_first = None
    chip_att = mk("owe", chip_kind, capped(chip_rows),
                  action=({"label": "Open %s" % chip_first["lane"], "lane": index[id(chip_first)]}
                          if chip_first is not None else None))
    hrt = ["<div class=\"hrt\"><button class=\"chip\" type=\"button\"%s>%s</button>" % (chip_att, _e(chip))]
    if arc_list:
        hrt.append("<button class=\"tbtn\" id=\"lbtn\" type=\"button\" aria-pressed=\"true\""
                   " title=\"the note arcs between projects\">◠ hide notes</button>")
    if n_nerves:                  # nothing to toggle, nothing on the strip
        hrt.append("<button class=\"tbtn\" id=\"nbtn\" type=\"button\" aria-pressed=\"true\""
                   " title=\"the live sessions, rising up their own columns\">● nerves on</button>")
    _dk, _lt, _lb = base_scheme(reg())
    hrt.append("<select class=\"tbtn\" id=\"sbtn\" aria-label=\"colour scheme\"><option value=\"%s\">%s · dark</option><option value=\"%s\">%s · light</option><option value=\"noir\">05 Terminal Noir</option><option value=\"instrument\">04 Instrument Dark</option><option value=\"cream\">07 Cream Dossier</option><option value=\"print\">01 Print Board</option></select>"
               % (_e(_dk), _e(_lb), _e(_lt), _e(_lb)))
    hrt.append("</div></div></header>")
    out.append("".join(hrt))
    # ── the crown: one head per column, families bracketed. It WRAPS into
    #    rows at the window's width: the grid owns the columns, so no
    #    count is pinned here, and each family's bracket is placed over its
    #    heads by the page, one per row they stand in.
    _crown_at = len(out)
    out.append("<section class=\"crown\" aria-label=\"Projects in the fall\">")
    fams, i = [], 0
    while i < len(columns):
        j = i
        while j < len(columns) and columns[j]["family"] == columns[i]["family"]:
            j += 1
        if j - i >= 2:
            fams.append((i, j - i, columns[i]["family"]))
        i = j
    if fams:
        out[_crown_at] = "<section class=\"crown fams\" aria-label=\"Projects in the fall\">"
        out.append("<div class=\"fambar\">")
        for start, n, fam in fams:
            _fatt = mk("fam:%s" % fam, "a family of projects",
                       [["family", fam],
                        ["projects", ", ".join(p["name"] for p in columns[start:start + n])],
                        ["why they are together", "their folder names share this family's prefix"]])
            out.append("<span class=\"fam\"%s data-from=\"%d\" data-n=\"%d\" hidden>%s · %d</span>"
                       % (_fatt, start, n, _e(fam), n))
        out.append("</div>")
    out.append("<div class=\"heads\">%s</div>" % "".join(head(p) for p in columns))
    out.append("</section>")
    # ── the fall: six ISO weeks, this one at the top; the rest is drawn ─
    out.append("<section class=\"fall\" id=\"fall\" style=\"grid-auto-rows:%dpx\" aria-label=\"Six weeks of work\">" % FALL_ROW)
    for i, w in enumerate(weeks):
        att = mk("wk:%s" % w["key"], "a week",
                 [["week", week_span(w)], ["monday", w["mon"]],
                  ["commits", "%d across the fall" % wk_commits.get(w["key"], 0)],
                  ["sessions", "%d" % wk_sessions.get(w["key"], 0)],
                  ["notes", "%d" % wk_notes.get(w["key"], 0)]])
        out.append("<div class=\"wk%s\" data-wk=\"%s\"><span class=\"wl\"%s>%s</span></div>"
                   % (" now" if i == 0 else "", _e(w["key"]), att, _e(w["label"])))
    out.append("</section>")
    # Roots: the machines and the minds everything grows from. Real bytes:
    # each machine's last sync from the sync log (deep, so a quiet machine
    # stays); lanes per mind from openers; live = an i-am stamp under 12 h,
    # or — for the OpenAI mind — a Codex session the pulse saw this half hour.
    here = str(roots.get("name", "")).lower()
    synced = sync_roots()
    verdicts = read_sync_verdicts(roots)       #  each machine's one-line sync verdict
    night = night_facts(roots)                 #  this machine's night check, for the collar
    live = read_live(roots)
    ears = read_ears(roots)
    _mind_name = mind_name          # module-level: the plate's own spelling

    def _is_live(d):
        return (not d.get("off")) and d.get("age") is not None and d["age"] <= 0.5

    # TWO MEASURES, TWO WORDS. LIVE is what the pulse sees in the
    # transcripts right now; STAMPED is what a session wrote with tools/i-am.py
    # and has not switched off, up to twelve hours. No number on this page is
    # computed twice by two rules, and neither word ever names the other.
    MEASURES = ("live is what the pulse sees writing a transcript right now; "
                "stamped is what a session wrote with tools/i-am.py and has not switched off")

    def stamp_rows(mch):
        found = []
        for d in live.get(str(mch).lower(), []):
            if not _is_live(d):
                continue
            found.append([_mind_name(d.get("mind")) or "a mind",
                          "%s%s · stamped %s ago" % (d.get("session") or "no title recorded",
                                                     (" · " + str(d.get("effort")).upper()) if d.get("effort") else "",
                                                     _span(d["age"]) if d.get("age") is not None else "?")])
        return found

    def pulse_rows(mch):
        found = []
        for path in sorted(live_sessions):
            for a in live_sessions[path]:
                if str(a.get("machine") or "").upper() != str(mch).upper():
                    continue
                mins = a.get("minutes_ago")
                found.append([a.get("mind") or "CLAUDE",
                              "…%s · %s · %s · %s" % (a.get("id") or "?",
                                                      SIDE.get(a.get("kind") or "claude", "Claude Code"),
                                                      ("%g min ago" % mins) if mins is not None else "just now",
                                                      path)])
        return found

    def mind_stamp_rows(mdl):
        found = []
        for mch, stamps in sorted(live.items()):
            for d in stamps:
                if not _is_live(d) or _mind_name(d.get("mind")) != mdl:
                    continue
                found.append([str(d.get("machine") or mch).upper(),
                              "%s · stamped %s ago" % (d.get("session") or "no title recorded",
                                                       _span(d["age"]) if d.get("age") is not None else "?")])
        return found

    def mind_live_rows(mdl):
        found = []
        for path in sorted(live_sessions):
            for a in live_sessions[path]:
                if (a.get("mind") or "CLAUDE") != mdl:
                    continue
                mins = a.get("minutes_ago")
                found.append([str(a.get("machine") or "").upper(),
                              "…%s · %s · %s" % (a.get("id") or "?",
                                                 ("%g min ago" % mins) if mins is not None else "just now",
                                                 path)])
        return found

    live_minds = {}                     # {MIND: {machine, effort, age, how, n, titles}}
    for _stamps in live.values():
        for _d in _stamps:
            if not _is_live(_d):
                continue
            _m = _mind_name(_d.get("mind"))
            if not _m:
                continue
            # One row per SESSION: count them, and carry the
            # titles so the root says which two are up, not just that one is.
            if _m not in live_minds or (live_minds[_m].get("age") or 1e9) > _d["age"]:
                _was = live_minds.get(_m, {})
                live_minds[_m] = {"machine": str(_d.get("machine", "")).upper(), "effort": str(_d.get("effort", "")).upper(),
                                  "age": _d["age"], "how": "stamp",
                                  "n": _was.get("n", 0) + 1, "titles": _was.get("titles", [])}
            else:
                live_minds[_m]["n"] = live_minds[_m].get("n", 0) + 1
            _t = str(_d.get("session") or "").strip()
            if _t and _t not in live_minds[_m].setdefault("titles", []):
                live_minds[_m]["titles"].append(_t)
    pulse_seen = {}                     # {MACHINE: {"claude": n, "codex": n}} — the pulse's own sight
    pulse_minds = {}                    # {MACHINE: {MIND: n}} — which mind each sensed session runs
    for _sessions in live_sessions.values():
        for _a in _sessions:
            _mch = str(_a.get("machine", "")).upper()
            _v = str(_a.get("kind") or "claude").lower()
            pulse_seen.setdefault(_mch, {})
            pulse_seen[_mch][_v] = pulse_seen[_mch].get(_v, 0) + 1
            _mn = _mind_name(_a.get("mind"))
            if _mn and _mn != "—":
                pulse_minds.setdefault(_mch, {})
                pulse_minds[_mch][_mn] = pulse_minds[_mch].get(_mn, 0) + 1
    # A mind the pulse SEES working is up, stamp or no stamp: the "stamps only"
    # rule existed because the pulse could not tell minds apart, and that reason
    # died when it learned to read the model.
    for _mch in sorted(pulse_minds):
        for _mn, _n in sorted(pulse_minds[_mch].items()):
            if _mn not in live_minds:
                live_minds[_mn] = {"machine": _mch, "effort": "", "age": 0.0, "how": "pulse", "n": _n}
    for _mch, _seen in pulse_seen.items():
        _cx = _rg.mind_name(reg(), "codex", "")
        if _seen.get("codex") and _cx not in live_minds:   # an older file with no mind recorded
            live_minds[_cx] = {"machine": _mch, "effort": "", "age": 0.0, "how": "pulse", "n": _seen["codex"]}
    now_local = datetime.now().astimezone()
    machines = sorted(set(list(synced.keys()) + list(live.keys()) + [k.lower() for k in pulse_stamps if k]
                          + list(ears.keys()) + list(post_facts.get("machines") or {})
                          + ([here] if here else [])))
    minds, mind_lanes = {}, {}
    # A MODEL ID PER MIND, so a mind the registry has never heard of can still
    # have its house read off the id it came with, instead of a dash.
    mind_models = {}
    for _msess in live_sessions.values():
        for _s in _msess:
            _mmind = _mind_name(_s.get("mind"))
            if _mmind and _s.get("model") and _mmind not in mind_models:
                mind_models[_mmind] = str(_s.get("model"))
    for r in rows:
        mdl = _mind_name(r.get("model"))
        if r["opener"] and mdl and mdl != "—":
            minds[mdl] = minds.get(mdl, 0) + 1
            mind_lanes.setdefault(mdl, []).append(r["lane"])
    # The minds the person asked to see even when nothing of theirs is up,
    # then everything actually seen. A registry that marks none draws only what
    # is there — a stranger's tree has no root for a mind they never had.
    known_minds = list(_rg.mind_shown(reg()))
    for k in list(minds) + list(live_minds):
        if k not in known_minds:
            known_minds.append(k)


    # ── the collar: nameplate · ring · the hub's state ───────────────
    if hub_rows:
        desig = []
        for _m in sorted(live_minds, key=lambda k: (_rg.mind_rank(reg(), k), k)):
            _lv = live_minds[_m]
            if str(_lv.get("machine", "")).lower() != here:
                continue
            if _lv.get("how") == "pulse":
                desig.append("%s · %d live" % (_m, _lv.get("n", 1)))
            else:
                desig.append("%s · %s" % (_m, _lv.get("effort") or "LIVE"))
        if not desig:
            desig = ["no mind up"]
        _sync_here = synced.get(here)
        beat = "last sync %s ago" % (_span((now_local - _sync_here).total_seconds() / DAY) if _sync_here else "—")
        _vd_here = verdicts.get(here)
        if _vd_here:
            beat += " · %s" % _vd_here["words"]          # the verdict's first words
        _ps_here = pulse_stamps.get(here)
        if _ps_here and _ps_here.get("age_h") is not None:
            beat += " · pulse %s ago · %d live" % (_span(_ps_here["age_h"] / 24.0), _ps_here["n"])
        else:
            beat += " · no pulse yet"
        out.append("<section class=\"hubbar\" aria-label=\"The hub — the trunk's collar\"><div class=\"plate3\">")
        _pr, _sr = pulse_rows(machine), stamp_rows(here)
        _np = mk("nameplate", "this machine",
                 [["machine", machine], ["minds up", " · ".join(desig)],
                  ["last sync", ("%s ago" % _span((now_local - _sync_here).total_seconds() / DAY))
                   if _sync_here else "no sync recorded yet"],
                  ["pulse", ("%s ago" % _span(_ps_here["age_h"] / 24.0))
                   if (_ps_here and _ps_here.get("age_h") is not None) else "no pulse yet"],
                  ["live", "%d session%s the pulse sees" % ((_ps_here or {}).get("n", 0),
                                                            "" if (_ps_here or {}).get("n", 0) == 1 else "s")]]
                 + ([["sync", "%s · written %s — the beat rewrites it the moment it changes"
                      % (_vd_here["line"], _vd_here["read"].strftime("%a %H:%M")
                         if _vd_here["read"] else "at an unrecorded time")]]
                    if _vd_here else [])
                 + _pr
                 + [["stamped", "%d session%s stamped up here in the last 12 hours" % (len(_sr), "" if len(_sr) == 1 else "s")]]
                 + _sr + [["the two words", MEASURES]])
        # the night check's last line under the beat — the existing beat line's class,
        # no new class, colour or font; a click answers with the whole list.
        _night = ""
        if night.get("last"):
            _night = "<div class=\"npbeat\"%s>night · %s</div>" % (
                mk("night", "what can take a model turn while nobody is here",
                   [["the last line", night["last"]]] + night.get("rows", [])), _e(night["last"]))
        out.append("<div class=\"nameplate\"%s><div class=\"npf\"><span class=\"stn\">%s</span><span class=\"dsg\">%s</span></div>"
                   "<div class=\"npbeat\">%s</div>%s</div>"
                   % (_np, _e(machine), "".join("<span>%s</span>" % _e(d) for d in desig), _e(beat),
                      _night))
        _ring_rows = [["live", "%d session%s rising into the tree" % (n_nerves, "" if n_nerves == 1 else "s")]]
        for _o in lane_objs:
            for _s in _o.get("sessions") or []:
                _ring_rows.append([_s.get("mind") or "CLAUDE",
                                   "…%s on %s · %s" % (_s.get("id") or "?", _s.get("machine") or "?",
                                                       _o.get("lane") or "")])
        _ring_rows.append(["the word", MEASURES])
        out.append("<div class=\"collarmid\"><svg class=\"ring\" id=\"ring\"%s viewBox=\"0 0 34 34\" width=\"34\" height=\"34\">"
                   "<circle cx=\"17\" cy=\"17\" r=\"15.4\"/><text id=\"ringn\" x=\"17\" y=\"21\"></text></svg></div>"
                   % mk("ring", "the live sessions rising into the tree", _ring_rows))
        out.append("<div class=\"hubstate\">%s</div>" % tile(hub_rows[0]))
        out.append("</div></section>")
    out.append("<section class=\"rootsec\" aria-label=\"Roots — machines and minds\"><div class=\"rootgrid\">")
    out.append("<div class=\"rootrow machines\">")
    for mch in machines:
        last = synced.get(mch)
        ago = _span((now_local - last).total_seconds() / DAY) if last else "—"
        stamps = live.get(mch, [])
        up = [d for d in stamps if _is_live(d)]
        seen = pulse_seen.get(mch.upper(), {})
        ps = pulse_stamps.get(mch)
        pulse_fresh = bool(ps and ps.get("age_h") is not None and ps["age_h"] <= 0.5)
        is_live = bool(up) or (pulse_fresh and bool(seen))
        parts = []
        _up_minds = []                  # every mind up here by its own stamp, its sessions counted
        for d in up:
            _mn, _ef = _mind_name(d.get("mind")), str(d.get("effort", "")).upper() or "up"
            _row = None
            for _r in _up_minds:
                if _r[0] == _mn:
                    _row = _r
                    break
            if _row is None:
                _up_minds.append([_mn, _ef, 1, d.get("age")])
            else:
                _row[2] += 1
                if d.get("age") is not None and (_row[3] is None or d["age"] > _row[3]):
                    _row[3] = d["age"]
        for _mn, _ef, _cnt, _old in _up_minds:
            # i-am stamps: STAMPED, with the oldest of them, never "sessions"
            _tail = ""
            if _old is not None:
                _tail = " · %s %s" % ("oldest" if _cnt > 1 else "stamped", _span(_old))
            parts.append("<span class=\"lv\">● %s · %s · %d stamped%s</span>"
                         % (_e(_mn), _e(_ef), _cnt, _e(_tail)))
        if pulse_fresh:                  # every mind the pulse sees here, stamp or not
            _stamped = set(_mind_name(d.get("mind")) for d in up)
            _here_minds = pulse_minds.get(mch.upper(), {})
            for _mn in sorted(_here_minds, key=lambda k: (_rg.mind_rank(reg(), k), k)):
                if _mn in _stamped:
                    continue
                parts.append("<span class=\"lv\">● %s · %d live</span>" % (_e(_mn), _here_minds[_mn]))
            _cxm = _rg.mind_name(reg(), "codex", "")
            if not _here_minds and seen.get("codex") and _cxm not in _stamped:
                parts.append("<span class=\"lv\">● %s · %d live</span>" % (_e(_cxm), seen["codex"]))
        if not parts and stamps:        # nothing up: the newest stamp is the last mind
            lv = stamps[0]
            parts.append("last mind %s, %s ago" % (_e(_mind_name(lv.get("mind"))), _e(_span(lv["age"]) if lv.get("age") is not None else "—")))
        if ps and ps.get("age_h") is not None:
            who = " · ".join("%d %s" % (n, {"claude": "Claude", "codex": "Codex", "grok": "Grok"}.get(v, v)) for v, n in sorted(seen.items()) if n) if pulse_fresh else ""
            parts.append("pulse %s ago · %d live%s" % (_e(_span(ps["age_h"] / 24.0)), ps["n"], (" · " + who) if who else ""))
        elif not ps:
            parts.append("no pulse yet")
        # THE EAR: is anything on that machine watching its hub mail? A letter
        # reaches a live session only through a watch, so a root without a fresh
        # hub ear says so in the words a human would use.
        _mears = ears.get(mch, [])
        _hub_ear = next((e for e in _mears if e["lane"] == "hub"), None)
        if _hub_ear and _hub_ear["fresh"]:
            parts.append("<span class=\"ear\">◗ mailbox</span> · checked %s ago"
                         % _e(_secs(_hub_ear["age_s"])))
        else:
            parts.append("no mailbox")
        if _hub_ear and _hub_ear["fresh"]:
            _ear_rows = [["mailbox", "armed%s · checked %s ago · polls every %d s"
                          % ((" by \"%s\"" % _hub_ear["title"]) if _hub_ear["title"] else "",
                             _secs(_hub_ear["age_s"]), _hub_ear["every"])]]
        elif _hub_ear:
            _ear_rows = [["mailbox", "no mailbox — the last watch%s stopped answering %s ago, "
                                     "more than twice its %d s poll"
                          % ((" (\"%s\")" % _hub_ear["title"]) if _hub_ear["title"] else "",
                             _secs(_hub_ear["age_s"]), _hub_ear["every"])]]
        else:
            _ear_rows = [["mailbox", "no mailbox — nothing on that machine is watching its hub mail, "
                                     "so a letter waits there until someone reads it by hand"]]
        # THE POSTMAN, after the mailbox words. A machine
        # with no post file says nothing at all here, and the root is the root
        # it was before that build.
        _pm = (post_facts.get("machines") or {}).get(mch) or {}
        if _pm:
            if _pm.get("state") == "passing":
                parts.append("postman · passed %s ago" % _e(_secs(_pm.get("age_s"))))
            elif _pm.get("state") == "quiet":
                parts.append("postman quiet since %s" % _e(_pm.get("since") or "—"))
            else:
                parts.append("no postman")
            _ear_rows.append(["postman", {"passing": "passing",
                                          "quiet": "quiet since %s" % (_pm.get("since") or "—"),
                                          "none": "not running"}.get(_pm.get("state"), "")])
            if _pm.get("last_pass"):
                _ear_rows.append(["last pass", "%s ago · %s" % (_secs(_pm.get("age_s")),
                                                                _pm["last_pass"])])
            _ear_rows.append(["every", "%d s" % int(_pm.get("every") or 0)])
            if _pm.get("version"):
                _ear_rows.append(["postman version", str(_pm["version"])])
            if _pm.get("last_good_pull"):
                _ear_rows.append(["last good pull", str(_pm["last_good_pull"])])
            _ear_rows.append(["letters waiting there", "%d" % int(_pm.get("waiting") or 0)])
            # THE SURFACES, when they are OFF:
            # the pass runs on every machine the brain carries the tool to, and
            # raises nothing until somebody says "install it" THERE. The fact is
            # machine-personal, so tree_facts carries it for this machine only.
            if _pm.get("surfaces") is False:
                _ear_rows.append(["surfaces", "surfaces off — not installed here"])
            if _pm.get("state") in ("quiet", "none"):
                _ear_rows.append(["what that means",
                                  "letters for this machine wait for a read by hand"])
        for _e_row in _mears:
            if _e_row["lane"] == "hub":
                continue
            _ear_rows.append(["lane mailbox · %s" % _e_row["lane"],
                              "%s · checked %s ago · polls every %d s"
                              % ("armed" if _e_row["fresh"] else "stale", _secs(_e_row["age_s"]),
                                 _e_row["every"])])
        # THE GUARD: what the write guard turned down on this machine
        # TODAY, and nothing at all on a day it turned down nothing — the guard
        # decided at the moment, so this is a record, never a thing to act on.
        # The chip carries its own answer, so a click on it gives the log lines
        # rather than the machine's card.
        _gd = guard_by_machine.get(mch) or {}
        if _gd.get("today"):
            _gd_rows = [["refused today",
                         "%d write%s or command%s the guard turned down here"
                         % (_gd["today"], "" if _gd["today"] == 1 else "s",
                            "" if _gd["today"] == 1 else "s")]]
            _gd_lines = []
            for _r in reversed(_gd["last"]):
                _rw = parse_iso(_r.get("when"))
                _stamp = (_rw.strftime("%H:%M") if _rw and _rw.date() == now.date()
                          else (_rw.strftime("%a %H:%M") if _rw else "?"))
                _line = " · ".join(x for x in (str(_r.get("vendor") or ""),
                                               str(_r.get("zone") or ""),
                                               str(_r.get("target") or "")) if x)
                _gd_rows.append([_stamp, _line])
                _gd_lines.append("%s · %s" % (_stamp, _line))
            _gd_rows.append(["read from", _gd.get("file") or ""])
            _gatt = mk("guard:%s" % mch, "the write guard on this machine", _gd_rows)
            parts.append("<span class=\"gd\"%s title=\"%s\">⊘ %d refused today</span>"
                         % (_gatt, _e("\n".join(_gd_lines)), _gd["today"]))
        _mpr, _msr = pulse_rows(mch), stamp_rows(mch)
        _vd = verdicts.get(mch)
        _matt = mk("root:%s" % mch.lower(), "a machine",
                   [["machine", mch.upper()], ["this one", "yes — the page was drawn here" if mch == here else ""],
                    ["last sync", ("%s ago · %s" % (ago, last.strftime("%a %H:%M"))) if last else "no sync recorded yet"]]
                   + ([["sync", "%s · written %s — that machine's beat rewrites it the moment "
                        "it changes" % (_vd["line"], _vd["read"].strftime("%a %H:%M")
                                        if _vd["read"] else "at an unrecorded time")]]
                      if _vd else [])
                   + [
                    ["pulse", ("%s ago" % _span(ps["age_h"] / 24.0)) if (ps and ps.get("age_h") is not None) else "no pulse yet"],
                    ["live", "%d session%s the pulse sees" % ((ps or {}).get("n", 0), "" if (ps or {}).get("n", 0) == 1 else "s")]]
                   + _ear_rows
                   + _mpr
                   + [["stamped", "%d session%s stamped up in the last 12 hours" % (len(_msr), "" if len(_msr) == 1 else "s")]]
                   + _msr + [["the two words", MEASURES]])
        out.append("<div class=\"root machine mc-%s%s%s\"%s data-root=\"machine\" data-mch=\"%s\"><span class=\"rk\">machine%s</span><span class=\"rn\">%s</span>"
                   "<span class=\"rv\">last sync ⏱ %s ago%s</span><span class=\"rv\">%s</span></div>"
                   % (_e(mch.lower()), " here" if mch == here else "", " live" if is_live else "", _matt, _e(mch.upper()),
                      " · here" if mch == here else "",
                      _e(mch.upper()), _e(ago), ((" · " + last.strftime("%a %H:%M")) if last else "")
                      + ((" · " + _vd["words"]) if _vd else ""), "<br>".join(parts)))
    out.append("</div><div class=\"rootrow minds\">")
    for mdl in known_minds:
        n = minds.get(mdl, 0)
        vendor = _rg.mind_vendor(reg(), mdl, mind_models.get(mdl, "")) or "—"
        lv = live_minds.get(mdl)
        is_live = lv is not None
        if is_live:
            if lv.get("how") == "pulse":
                val = "<span class=\"lv\">● %d live on %s</span>" % (lv.get("n", 1), _e(lv["machine"]))
            else:
                _ns = lv.get("n", 1)    # session-keyed stamps: two sessions of one mind both count
                val = "<span class=\"lv\">● %d stamped on %s · %s</span>" % (
                    _ns, _e(lv["machine"]), _e(lv.get("effort") or "up"))
            if n:
                val += "<br>%d lane%s open on it" % (n, "" if n == 1 else "s")
        else:
            val = ("%d lane%s open on it" % (n, "" if n == 1 else "s")) if n else "no lane on it yet"
        _titles = (lv.get("titles") or []) if is_live else []
        _dsr, _dlr = mind_stamp_rows(mdl), mind_live_rows(mdl)
        _datt = mk("mind:%s" % mdl, "a mind",
                   [["mind", mdl], ["vendor", vendor],
                    ["lanes open on it", ", ".join(mind_lanes.get(mdl) or []) or "none"],
                    ["live", "%d session%s the pulse sees" % (len(_dlr), "" if len(_dlr) == 1 else "s")]]
                   + _dlr
                   + [["stamped", "%d session%s stamped up in the last 12 hours" % (len(_dsr), "" if len(_dsr) == 1 else "s")]]
                   + _dsr + [["the two words", MEASURES]])
        out.append("<div class=\"root mind m-%s%s%s\"%s data-root=\"mind\" data-mind=\"%s\"%s%s><span class=\"rk\">mind · %s</span><span class=\"rn\">%s</span><span class=\"rv\">%s</span></div>"
                   % (_e(mdl.lower()), "" if (n or is_live) else " dim", " live" if is_live else "", _datt, _e(mdl),
                      (" data-on=\"%s\"" % _e(lv["machine"])) if is_live else "",
                      (" title=\"%s\"" % _e(" · ".join(_titles))) if _titles else "", _e(vendor), _e(mdl), val))
    out.append("</div></div></section>")
    # ── the band at the foot: everything the fall does not show, with
    #    the one-line reason it is here ────────────────────────────────────────
    if band:
        n_quiet = sum(1 for p in band if (p.get("why") or "").startswith("quiet"))
        n_dorm = sum(1 for p in band if (p.get("why") or "").startswith("dormant"))
        out.append("<section class=\"dormant coolband\" aria-label=\"Not in the fall\"><div class=\"coolh\"><b>Not in the fall</b>"
                   "<span>%d projects · %d quiet for six weeks · %d dormant · click for the card</span>"
                   "</div><div class=\"coolmap\">"
                   % (len(band), n_quiet, n_dorm))
        for p in band:
            out.append(tile(p["rep"], cool=True, why=p["band_why"],
                            col=p["col"] if p["col"] is not None else None))
        out.append("</div></section>")
    out.append("<section class=\"chart\" aria-label=\"Work left\"><h2>Work left</h2>"
               "<div class=\"sub\">each lane's own estimate · sorted by urgency (work left against time left) · bars add up to the fleet total</div>%s</section>"
               % _chart([r for r in rows if r["active"]], tone, marks, index))
    # ── the legend: each key says what it means and how many are here;
    #    a key with nothing on the page is not drawn (Nothing-superfluous) ──
    page_so_far = "".join(out)

    def drawn(*tokens):
        """How many marks like this the page really carries — counted in its own
        bytes, so a legend key can never claim a number the page does not have."""
        return sum(page_so_far.count(token) for token in tokens)

    def legend_key(mid, glyph, word, kind, says, count, highlight, unit="marks like this on the page"):
        if not count:
            return ""        # nothing of that kind on the page: no key for it
        att = mk(mid, kind, [["what it means", says],
                             [unit, "%d" % count],
                             ["clicking this", "lights them up for two seconds"]],
                 highlight=highlight)
        if not att:
            return ""
        return "<button type=\"button\"%s>%s%s</button>" % (att, glyph, _e(word))

    _n_stream = sum(1 for p in columns for w in weeks if p["commits"].get(w["key"], 0))
    _sw = "<i class=\"sw %s\"></i>"
    _k = "<span class=\"k\">%s</span>"
    legend = [
        legend_key("legend:ready", _sw % "ready", "ready", "what this colour means",
                   "the next move on this lane is the machine's, or it is plainly written down",
                   drawn('class="ph ready', 'class="tile ready'), ".ph.ready,.tile.ready"),
        legend_key("legend:wait", _sw % "wait", "waiting on you", "what this colour means",
                   "the lane is clean but waits on a word from you, or carries an urgent open item",
                   drawn('class="ph wait', 'class="tile wait'), ".ph.wait,.tile.wait"),
        legend_key("legend:bad", _sw % "bad", "attention", "what this colour means",
                   "the repo is dirty or unpushed against its own law, or its startup prompt is stale",
                   drawn('class="ph bad', 'class="tile bad'), ".ph.bad,.tile.bad"),
        legend_key("legend:cool", _sw % "cool", "cool", "what this colour means",
                   "paused or dormant: the fall shows nothing for it in six weeks",
                   drawn('class="tile cool'), ".coolmap .tile"),
        legend_key("legend:launch", _k % "▶", "launch", "what this button does",
                   "opens a session in that folder with the one sentence that hands the lane over; "
                   "a Codex lane has no such link, so its mark (⧉) copies the paste instead",
                   drawn('class="launch"'), ".tile .launch,.ph .launch"),
        legend_key("legend:prompt", _k % "▶", "prompt", "what this mark does",
                   "opens the lane's card at its startup prompt, ready to copy",
                   drawn('class="pr"'), ".pr"),
        legend_key("legend:commits", _k % "▮", "commits", "what this mark means",
                   "the width of a stream is that week's commits in that project",
                   _n_stream, "svg.lines rect.stream", unit="drawn in the fall now"),
        legend_key("legend:note", _k % "◠", "note", "what this mark means",
                   "an arc is a note one project sent another, drawn at the week it was written",
                   len(arc_list), "svg.lines path.arc", unit="drawn in the fall now"),
        legend_key("legend:ages", _k % "⌛", "open · idle", "what these marks mean",
                   "how long the lane has been open, and how long since anything touched it",
                   drawn('class="ages"'), ".tile .ages"),
        legend_key("legend:mail", _k % "✉", "notes", "what this mark means",
                   "notes waiting in the INBOX for that project",
                   drawn('class="mail"'), ".mail"),
        legend_key("legend:gated", _k % "🔒", "gated", "what this mark means",
                   "the lane may not be opened until another lane prints its gate line",
                   drawn('class="st gt"', 'class="sx gt"'), ".st.gt,.sx.gt"),
        legend_key("legend:live", _k % "●", "live", "what this mark means",
                   "a session the pulse saw writing its transcript in the last ten minutes",
                   drawn('class="lv '), ".lv"),
        legend_key("legend:ear", _k % "◗", "mailbox", "what this mark means",
                   "a session on that machine is watching its hub mail, so a letter from here "
                   "reaches it without anyone carrying it; a machine without the mark says no mailbox",
                   drawn('class="ear"'), ".ear"),
        legend_key("legend:nerve", _k % "⌁", "nerve", "what this mark means",
                   "a live session, drawn rising from the roots up its own column",
                   n_nerves, "svg.lines path.nerve", unit="drawn in the fall now"),
        legend_key("legend:guard", _k % "⊘", "refused", "what this mark means",
                   "writes and commands the write guard turned down on that machine "
                   "today; the guard decided at the moment, so there is nothing here "
                   "to act on — click it for the lines",
                   drawn('class="gd"'), ".gd"),
    ]
    _mchips = "&nbsp;·&nbsp;".join("<span class=\"mc-%s\">%s</span>" % (_e(m.lower()), _e(m.upper()))
                                   for m in machines)
    _dchips = "&nbsp;·&nbsp;".join("<span class=\"m-%s\">%s</span>" % (_e(m.lower()), _e(m))
                                   for m in known_minds)
    if machines:
        legend.append("<span class=\"kk\"%s>%s</span>"
                      % (mk("legend:machines", "the machines, by colour",
                            [[m.upper(), ("last sync %s ago" % _span((now_local - synced[m]).total_seconds() / DAY))
                              if synced.get(m) else "no sync recorded yet"] for m in machines]),
                         _mchips))
    if known_minds:
        legend.append("<span class=\"kk\"%s>%s</span>"
                      % (mk("legend:minds", "the minds, by colour",
                            [[m, "%s · %d lane%s open on it" % (_rg.mind_vendor(reg(), m, mind_models.get(m, "")) or "—", minds.get(m, 0),
                                                                "" if minds.get(m, 0) == 1 else "s")]
                             for m in known_minds]),
                         _dchips))
    out[legend_slot] = "<div class=\"legend\">%s</div></div>" % "".join(x for x in legend if x)
    # The line under the page is the person's own, from the registry. Empty
    # means NO line — not an empty one, and not a dangling separator.
    _cap = _rg.caption(reg())
    out.append("<footer><hr class=\"fr\"><p>Generated %s · tools/collect-openers.py --html · rewritten by every orchestrator.py run%s</p>"
               "<p id=\"skycheck\" hidden></p><p id=\"crosscheck\" hidden></p><p id=\"hitcheck\" hidden></p></footer>"
               % (_e(stamp), (" · " + _html.escape(_cap, quote=False)) if _cap else ""))
    out.append("</div><aside id=\"inspector\" hidden aria-live=\"polite\" aria-label=\"what this mark is\"></aside>"
               "<div id=\"detail\" class=\"detail\" hidden><div class=\"dpanel\" id=\"dpanel\"></div></div>")
    out.append("<script type=\"application/json\" id=\"marks\">%s</script>" % marks_json(marks))
    out.append("<script type=\"application/json\" id=\"lists\">%s</script>" % marks_json(shared_lists))
    out.append("<script type=\"application/json\" id=\"lanes\">%s</script>" % lanes_json)
    out.append("<script type=\"application/json\" id=\"fall-data\">%s</script>" % fall_json)
    out.append("<script>%s</script></body></html>" % html_js(reg()))
    return "\n".join(out)


BRAIN_README = """# brain-index.json — what the exocortex holds, as data

Written beside tree.html by every collector run, from the same bytes the sky is drawn from. No memory TEXT: read the files themselves for words.

- memories[]: one per memory file. `project` is the folder's display name, `key` its lowercase form (the tile/constellation join), `name` the file stem.
- The file is `<claude root>/projects/<the project's absolute path with every non-alphanumeric character turned into a hyphen>/memory/<name>.md`.
- `kind` is the frontmatter `metadata: type:` (user | feedback | project | reference; missing reads as project). `bytes` is its size, `last_change` its mtime.
- `changes` is how many commits in the brain clone touched it (a change, not proof of use); `activity` a decayed change score in the ACT-R form, 0…1.
- `links` are the `[[names]]` it points at — other memories, by stem.
- journal[]: the dated lines of dossier/TAUGHT.md — `date`, the `lane` its own words name, `promoted` (the date it became law, or empty).
- laws[]: the ratified rules of the global CLAUDE.md — `name`, the owner's `date`, the `lane` its header names. skills[]: each skill and the `projects` its SKILL.md names.
- codex[]: the OpenAI side's own files under the machine's `codex` root — `kind` (law | skill), `name`, `path`, and for a skill the `target` its symlink resolves to.
- `machine` says which machine wrote this; both CLAUDE.md and the skills live under that machine's Claude home root.
"""


def write_brain_index(brain, roots, path=None):
    """brain-index.json beside the page:
    what the exocortex holds, for another program to read the brain by. Only what the
    sky already computed — no second pass, no memory text."""
    hub = Path(roots.get("orchestrator") or HUB_DIR)
    now = datetime.now().astimezone()
    memories = []
    for m in brain.get("memories") or []:
        last = now - timedelta(days=float(m.get("age") or 0.0))
        memories.append({"project": m["project"],
                         "key": m.get("key") or str(m["project"]).lower(),
                         "name": m["name"], "kind": m.get("kind") or "project",
                         "bytes": int(m.get("bytes") or 0),
                         "last_change": last.isoformat(timespec="seconds"),
                         "changes": int(m.get("uses") or 1),
                         "activity": float(m.get("p") or 0.0),
                         "links": list(m.get("links") or [])})
    skills = []
    for sk in brain.get("skills") or []:
        named = sorted({e["b"][0] for e in (brain.get("edges") or [])
                        if e.get("kind") == "skill" and e["a"][1] == sk})
        skills.append({"name": sk, "projects": named})
    payload = {"generated": now.isoformat(timespec="seconds"),
               "machine": str(roots.get("name") or "").lower(),
               "memories": memories,
               "journal": [{"date": j["date"], "lane": j.get("lane") or "",
                            "promoted": j.get("promoted") or ""}
                           for j in (brain.get("journal") or [])],
               "laws": [{"name": l["name"], "date": l.get("date") or "",
                         "lane": l.get("lane") or ""}
                        for l in (brain.get("laws") or [])],
               "skills": skills,
               "codex": [{"kind": c.get("kind") or "", "name": c.get("name") or "",
                          "path": c.get("path") or "", "target": c.get("target") or ""}
                         for c in (brain.get("codex") or [])]}
    target = Path(path) if path else (hub / "brain-index.json")
    try:
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
        # LF on every system: the README rides the brain (brain-index.json and the
        # page do not), and a CRLF copy from a Windows run read as a CONFLICT on
        # every pull there. io.open, not write_text: Python 3.9 has no
        # newline= on write_text.
        with io.open(str(target.parent / "brain-index.README.md"), "w", encoding="utf-8",
                     newline="\n") as handle:
            handle.write(BRAIN_README)
    except OSError:
        return None
    return target


LAST_BRAIN = {}     # the brain the last render read, for the bridge above


def write_html(data, path=None):
    """tree.html beside the board, in the hub folder. Returns the path.

    COLLECT_OPENERS_OUT=<file> sends the page — and the brain index beside it —
    somewhere else instead, so a build can render the REAL hub read-only
    without touching the live tree the heartbeat keeps. Unset, or
    empty, nothing changes."""
    roots = machine_roots()
    forced = os.environ.get("COLLECT_OPENERS_OUT", "").strip()
    beside = path is not None or bool(forced)
    if path is None:
        path = forced or (Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent) / "tree.html")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_page(data), encoding="utf-8")
    if LAST_BRAIN:
        write_brain_index(LAST_BRAIN, roots,
                          (path.parent / "brain-index.json") if beside else None)
    return path


def main(argv):
    argv = list(argv)
    if "--help" in argv or "-h" in argv:
        emit(USAGE)
        return 0
    mode, target = "table", None
    if "--chat" in argv:
        mode = "chat"
    if "--json" in argv:
        mode = "json"
    if "--write-tree" in argv:
        mode = "tree"
    if "--html" in argv:
        mode = "html"
    if "--expand" in argv:
        mode = "expand"
        index = argv.index("--expand")
        target = argv[index + 1] if index + 1 < len(argv) else "all"
    data = collect()
    if mode == "json":
        emit(json.dumps(jsonable(data), indent=2, ensure_ascii=False))
        return 0
    if mode == "chat":
        for line in chat_lines(data):
            emit(line)
        return 0
    if mode == "expand":
        rows, problem = match_rows(data, target or "all")
        if problem:
            emit(problem)
            return 1
        for row in rows:
            for line in card_lines(row):
                emit(line)
        return 0
    if mode == "html":
        path = write_html(data)
        emit("Wrote %s — %d active lanes, %d paused."
             % (path, sum(1 for row in data["rows"] if row["active"]),
                len({row["project"] for row in data["rows"] if not row["active"]})))
        emit("Sky labels: %d texts · %d overlapping pair%s (target 0)."
             % (SKY_REPORT.get("texts", 0), SKY_REPORT.get("overlaps", 0),
                "" if SKY_REPORT.get("overlaps", 0) == 1 else "s"))
        emit("Sky marks: %d journal dots / %d dated journal lines · %d law ticks / %d laws "
             "· %d drops / %d promoted lines."
             % (SKY_REPORT.get("jdots", 0), SKY_REPORT.get("journal", 0),
                SKY_REPORT.get("ticks", 0), SKY_REPORT.get("laws", 0),
                SKY_REPORT.get("drops", 0), SKY_REPORT.get("promoted", 0)))
        return 0
    if mode == "tree":
        path = write_tree(data)
        html_path = write_html(data)
        emit("Wrote %s (the styled page)." % html_path)
        active = sum(1 for row in data["rows"] if row["active"])
        emit("Wrote the auto region of %s — %d lanes (%d active), "
             "%d with an opener."
             % (path, len(data["rows"]), active,
                sum(1 for row in data["rows"] if row["opener"])))
        emit(flags_line(data["flags"]))
        return 0
    print_table(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
