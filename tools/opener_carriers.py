#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opener_carriers.py — an opener rides three carriers; the freshest copy wins.

A session writes its handoff opener into the project folder when it closes. That
file is not the only copy: the hub copies every card into the brain's TREE.md at
button-up, and a lane that closed on the OTHER machine travels here inside a
transfer-drive payload's git bundle, landed or not. A hub that reads only the
folder can hand over a morning-old opener while the current one sits in a
payload's bundle on the mounted drive. This module reads the two carriers the
collector cannot see, so `tools/collect-openers.py` can compare every copy of
a lane's opener by its own `written:` line, hand over the newest, name the
carrier it came from, and say — loud — when the folder copy is behind.

    the folder      tools/collect-openers.py's own find_openers(); not this file's business
    the brain       read_brain(tree_path)      — the fenced `opener` blocks in TREE.md's cards
    the drive       read_drive(projects_root)  — every `*.bundle` in a `*-TX-*` payload folder
                                                 on every mounted volume that is not internal
    the winner      pick(folder, others)       — newest `written:`; ties → folder, brain, drive
    the lane's move lane_next_move(...)        — the LANE's own next step, not the project's first
    the model line  judgment_unwalked(...)     — a body that needs judgment under an OPUS/SONNET line

Nothing here writes into a project repo, onto a volume, or into the hub folder.
A bundle is read through a scratch clone of the local project (`git clone
--shared --no-checkout`, then `git fetch <bundle>` into that clone), so the
project's own refs are never touched and the drive is only ever read. Nothing
here raises: every failure becomes one note the collector prints, and the folder
copy stands.

COST. The collector runs on every pulse beat, so a volume that is not there
costs one listdir, and a bundle already read costs zero git calls: every bundle
is cached under the temp dir by (path, size, mtime) — failures cached too, so a
payload cut for the other machine is not re-verified every five minutes.

THE `HH:Mx` HABIT. Sessions write `written: YYYY-MM-DDT21:5x-07:00` when they
mean "about ten to ten". A trailing `x` in the minute or the second field is
read as `0` (`21:5x` → `21:50`) before the timestamps are compared; the value
printed to the human is always the line as the file actually says it.

Stdlib only, Python 3.9-compatible, OS-neutral: the projects root comes from the
collector (machine.json), the engine from the sync package the path resolver
finds (tools/exo_paths.py), the volumes from the engine's own first-hand volume
reader — never a hard-coded path or letter.
"""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# The resolver sits beside this file. The collector has already put this folder
# on the path; a gate that imports this module alone may not have.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_paths import paths            # noqa: E402  the one answer to "where is the engine"

# ── the opener contract, mirrored ─────────────────────────────────────────
# Mirrored from tools/collect-openers.py (whose file name carries a hyphen and
# cannot be imported) so this module stands alone for its gate. The gate checks
# the two tuples against the collector's source text, so a drift is caught.

HEADER_KEYS = ("lane", "written", "by", "on", "head", "status_updated",
               "where", "next", "depends_on", "open_in", "model")
OPTIONAL_KEYS = ("remaining", "due", "priority", "judgment")

HEADER_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")
SEPARATOR = "---"
OPENER_NAME = re.compile(r"^OPENER(?:-(.+))?\.md$")

# TREE.md's auto region, mirrored from the collector for the same reason.
AUTO_START = "<!-- tree:auto-start -->"
AUTO_END = "<!-- tree:auto-end -->"
CARD_HEAD = re.compile(r"^###\s+(.*)$")
LANE_COMMENT = re.compile(r"^<!--\s*tree\s+(.*?)-->\s*$")
ATTR = re.compile(r'([a-z_]+)="([^"]*)"')
FENCE = re.compile(r"^(`{3,})\s*([A-Za-z0-9_-]*)\s*$")
OPENER_COMMENT = re.compile(r"^<!--\s*opener\s+(.*?)-->\s*$")
OPENER_INFO = "opener"

# A payload folder on a volume root: `^[A-Z][A-Z0-9]*-TX-`, widened by one
# group so a dash-joined id (AB-GATE-TX-002) is seen too — every name the
# narrower pattern matches still matches, and nothing that is not a payload
# folder is ever opened.
PAYLOAD_DIR = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-TX-")

# The engine, for its first-hand volume reader: the sync package the path
# resolver finds — the older layout's own folder, or <hub>/sync in a program
# tree. None when this machine has none. Overridable for the gate.
ENGINE_DIR = (Path(os.environ["COLLECT_OPENERS_ENGINE"])
              if os.environ.get("COLLECT_OPENERS_ENGINE")
              else paths(tool_file=__file__)["sync_dir"])
VOLUMES_ENV = "COLLECT_OPENERS_VOLUMES"

# Where the bundle cache and the read-only scratch clones live. Never the hub
# folder, never a project, never the volume: this is scratch, and a machine that
# loses it only pays one git read per bundle again.
WORK_DIR = Path(os.environ.get("COLLECT_OPENERS_WORK")
                or (Path(tempfile.gettempdir()) / "exocortex-opener-carriers"))
CACHE_FILE = WORK_DIR / "cache.json"
CACHE_MAX = 200            # bundles remembered; the oldest are dropped
CLONE_TIMEOUT = 90
GIT_TIMEOUT = 30

# Counters the gate reads: a cached bundle must cost zero git calls.
GIT_CALLS = 0
CACHE_HITS = 0
CACHE_MISSES = 0

SOURCE_RANK = {"folder": 0, "brain": 1}     # anything else (drive:…) sorts last
OLDEST = -1.0e18                            # a candidate with no readable `written:`


def reset_stats():
    """Zero the counters (the gate calls this between runs)."""
    global GIT_CALLS, CACHE_HITS, CACHE_MISSES
    GIT_CALLS = CACHE_HITS = CACHE_MISSES = 0


def stats():
    return {"git_calls": GIT_CALLS, "cache_hits": CACHE_HITS,
            "cache_misses": CACHE_MISSES}


# ── text ──────────────────────────────────────────────────────────────────

def plain(text):
    text = str(text).replace("`", "").replace("**", "").replace("__", "")
    return " ".join(text.split())


def words(text, count):
    parts = plain(text).split()
    if len(parts) <= count:
        return " ".join(parts)
    return " ".join(parts[:count]) + "…"


def lane_key(text):
    """The one key two spellings of a lane agree on: lowercase, collapsed."""
    return " ".join(str(text or "").strip().lower().split())


def normalize_written(text):
    """`2026-09-10T21:5x-07:00` → `…T21:50-07:00`. A trailing `x` in the minute
    or second field is the sessions' own "about then" habit; it becomes 0."""
    return re.sub(r"(?<=:\d)[xX]", "0", str(text or ""))


def parse_iso(text):
    """ISO-8601 → aware datetime (local tz when naive), else None. Same rule as
    the collector's parse_iso; the collector passes its own in."""
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip().replace("Z", "+00:00")
    raw = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", raw)  #  -0700 → -07:00
    try:
        stamp = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return stamp.astimezone()
    return stamp


def written_ts(header, parse=None):
    """The comparable moment this opener says it was written, or None."""
    parse = parse or parse_iso
    try:
        stamp = parse(normalize_written((header or {}).get("written") or ""))
    except Exception:
        stamp = None
    if stamp is None:
        return None
    try:
        return stamp.timestamp()
    except Exception:
        return None


def written_words(candidate):
    """What the human is shown: the `written:` line as the file says it."""
    value = str(((candidate or {}).get("header") or {}).get("written") or "").strip()
    if not value:
        return "no written: line"
    if candidate.get("written_ts") is None:
        return "%s (unreadable)" % value
    return value


# ── one opener, parsed ────────────────────────────────────────────────────

def parse_text(text):
    """{header, body, raw, missing, unknown, problems} — the collector's own
    header contract (key: value lines, a bare `---`, then the body verbatim)."""
    out = {"header": {}, "body": "", "raw": text or "", "missing": [],
           "unknown": [], "problems": []}
    lines = str(text or "").splitlines()
    body_start = None
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped == SEPARATOR:
            body_start = index + 1
            break
        if not stripped:
            continue
        match = HEADER_LINE.match(stripped)
        if not match:
            out["problems"].append("header line not `key: value`: %s"
                                   % stripped[:40])
            continue
        key = match.group(1).strip().lower().replace("-", "_")
        value = match.group(2).strip()
        if key in HEADER_KEYS or key in OPTIONAL_KEYS:
            out["header"][key] = value
        else:
            out["unknown"].append(key)
    if body_start is None:
        out["header"] = {}
        out["body"] = str(text or "").strip("\n")
        out["problems"].append("no `---` separator — no header could be read")
    else:
        out["body"] = "\n".join(lines[body_start:]).strip("\n")
    out["missing"] = [key for key in HEADER_KEYS if not out["header"].get(key)]
    return out


def candidate(source, text, lane="", file="", project="", payload="",
              origin="", parse=None):
    """One carrier's copy of one opener, ready to be compared."""
    parsed = parse_text(text)
    header = parsed["header"]
    suffix = ""
    match = OPENER_NAME.match(str(file or ""))
    if match:
        suffix = (match.group(1) or "").strip()
    shown = plain(header.get("lane") or lane
                  or ("%s/%s" % (project, suffix) if (project and suffix)
                      else (project or "")))
    return {"source": source, "lane": shown, "file": str(file or ""),
            "project": str(project or ""), "payload": str(payload or ""),
            "suffix": suffix, "header": header, "body": parsed["body"],
            "raw": str(text or "").strip("\n"), "missing": parsed["missing"],
            "unknown": parsed["unknown"], "problems": parsed["problems"],
            "origin": str(origin or ""),
            "written_ts": written_ts(header, parse), "claimed": False}


def compose(header, body):
    """header + `---` + body, in the contract's own key order."""
    lines = []
    for key in tuple(HEADER_KEYS) + tuple(OPTIONAL_KEYS):
        if key in (header or {}):
            lines.append("%s: %s" % (key, header[key]))
    for key, value in sorted((header or {}).items()):
        if key not in HEADER_KEYS and key not in OPTIONAL_KEYS:
            lines.append("%s: %s" % (key, value))
    lines.append(SEPARATOR)
    lines.append(str(body or ""))
    return "\n".join(lines)


def opener_text(item):
    """The verbatim text to carry: the file as it was read, else composed."""
    raw = str((item or {}).get("raw") or "").strip("\n")
    if raw:
        return raw
    return compose((item or {}).get("header") or {},
                   (item or {}).get("body") or "").strip("\n")


def opener_block(item, fence_for=None, source="", written=""):
    """The card's machine-readable copy: one fenced `opener` block, verbatim.
    read_brain() parses exactly this back."""
    text = opener_text(item)
    fence = (fence_for or _fence_for)(text)
    head = "<!-- opener source=\"%s\" written=\"%s\" -->" % (
        _attr(source or (item or {}).get("source") or "folder"),
        _attr(written or ((item or {}).get("header") or {}).get("written") or ""))
    return [head, fence + OPENER_INFO] + text.split("\n") + [fence]


def _fence_for(body):
    longest = 0
    for run in re.findall(r"`+", body or ""):
        longest = max(longest, len(run))
    return "`" * max(3, longest + 1)


def _attr(text):
    return plain(text).replace('"', "'").replace("--", "-").replace(">", "›")


# ── carrier: the brain (TREE.md) ──────────────────────────────────────────

def read_brain(tree_path, parse=None):
    """{lane: candidate} — every opener TREE.md's cards carry verbatim. Two
    lanes of the same name in different projects both survive: the second is
    keyed `<project>::<lane>`.

    A TREE.md with no `opener` blocks (every file written before this build)
    yields {}: no error, no note. Only the auto region is read; the hub's own
    writing below `tree:auto-end` is never parsed."""
    out = {}
    try:
        text = io.open(str(tree_path), encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    if AUTO_START not in text or AUTO_END not in text:
        return out
    lines = text.split(AUTO_START, 1)[1].split(AUTO_END, 1)[0].split("\n")
    lane, attrs, origin = "", {}, {}
    at, total = 0, len(lines)
    while at < total:
        raw = lines[at]
        opened = FENCE.match(raw.rstrip())
        if opened:
            # Every fenced block is stepped over as a block, so a ``` inside the
            # card's pasteable prompt is never read as a fence of its own (that
            # prompt's own fence is the longer one — fence_for chose it).
            fence, info = opened.group(1), opened.group(2)
            held, at = [], at + 1
            while at < total and lines[at].rstrip() != fence:
                held.append(lines[at])
                at += 1
            at += 1
            if info == OPENER_INFO:
                item = candidate("brain", "\n".join(held),
                                 lane=attrs.get("lane") or lane,
                                 file=_file_attr(attrs),
                                 project=attrs.get("project") or "",
                                 origin=origin.get("source") or "",
                                 parse=parse)
                key = lane_key(item["lane"] or attrs.get("lane") or lane)
                # Two projects can run a lane of the same name (two `Style`
                # lanes on this machine today), so a clash keeps BOTH: the
                # second goes under `<project>::<lane>`. Nothing is dropped,
                # and candidates_for matches on project and file anyway.
                if key and key in out and not _same_project(
                        out[key].get("project"), item.get("project")):
                    key = "%s::%s" % (lane_key(item.get("project")), key)
                if key:
                    out[key] = item
            continue
        stripped = raw.strip()
        born = OPENER_COMMENT.match(stripped)
        if born:
            # the block's own line: the carrier THIS copy was written from, so a
            # drive payload is still named once the brain holds a copy of it
            origin = dict(ATTR.findall(born.group(1)))
            at += 1
            continue
        comment = LANE_COMMENT.match(stripped)
        if comment:
            attrs = dict(ATTR.findall(comment.group(1)))    # this card's facts
            at += 1
            continue
        head = CARD_HEAD.match(stripped)
        if head:
            lane = _unlock(head.group(1))
            at += 1
            continue
        at += 1
    return out


def _unlock(text):
    """The card heading without its gate mark."""
    return plain(str(text or "").lstrip("🔒 	"))


def _file_attr(attrs):
    value = str((attrs or {}).get("opener") or "").strip()
    return "" if value.lower() in ("", "none") else value


# ── carrier: the drive ────────────────────────────────────────────────────

def mounted_volumes(notes=None, projects_root=None):
    """[{'label', 'path'}] — every mounted volume that is not this machine's own.

    The engine's carrier_preflight.real_volumes() is the one first-hand reader
    of volumes (it finds a drive by LABEL, never by letter). When the engine is
    not there, this returns [] and says so once. COLLECT_OPENERS_VOLUMES — an
    os.pathsep-separated list of directories, each treated as a volume root
    whose label is its own folder name — overrides both, always."""
    forced = os.environ.get(VOLUMES_ENV, "").strip()
    if forced:
        out = []
        for piece in forced.split(os.pathsep):
            piece = piece.strip()
            if not piece:
                continue
            path = Path(piece)
            out.append({"label": path.name or str(path), "path": str(path)})
        return out
    if ENGINE_DIR is None:
        if notes is not None:
            notes.append("drive carriers: engine not found")
        return []
    engine = str(ENGINE_DIR)
    try:
        if engine not in sys.path:
            sys.path.append(engine)
        import carrier_preflight              # noqa: F401
        volumes = carrier_preflight.real_volumes() or []
    except Exception:
        if notes is not None:
            notes.append("drive carriers: engine not found")
        return []
    out = []
    for volume in volumes:
        try:
            path = (volume or {}).get("path")
            label = str((volume or {}).get("label") or "").strip()
        except Exception:
            continue
        if not path:
            continue                          # a volume with no mount point
        if _is_internal(path, projects_root):
            continue
        out.append({"label": label or Path(str(path)).name, "path": str(path)})
    return out


def _internal_anchors(projects_root=None):
    """The drives this machine keeps itself on: home, the hub, the projects
    root. Read from where this file and the user's home actually are — never a
    letter, never a name."""
    anchors = set()
    for path in (Path.home(), Path(__file__).resolve().parent.parent,
                 Path(os.environ.get("COLLECT_OPENERS_ROOT") or Path.home()),
                 Path(projects_root) if projects_root else Path.home()):
        try:
            anchors.add(str(Path(path).resolve().anchor).lower())
        except Exception:
            continue
    anchors.discard("")
    return anchors


def _is_internal(path, projects_root=None):
    try:
        anchor = str(Path(str(path)).resolve().anchor).lower()
    except Exception:
        return False
    return anchor in _internal_anchors(projects_root)


def payload_folders(volume_path):
    """Only `*-TX-*` folders on the volume ROOT. Nothing else is opened."""
    out = []
    try:
        for child in sorted(Path(volume_path).iterdir()):
            try:
                if child.is_dir() and PAYLOAD_DIR.match(child.name):
                    out.append(child)
            except OSError:
                continue
    except OSError:
        pass
    return out


def _project_names(projects_root):
    out = {}
    try:
        for child in sorted(Path(projects_root).iterdir()):
            try:
                if child.is_dir() and not child.name.startswith("."):
                    out[child.name.lower()] = child
            except OSError:
                continue
    except OSError:
        pass
    return out


def _payload_repo(folder, bundle_name):
    """The repo name PAYLOAD.json gives this bundle, or '' when it cannot say."""
    try:
        data = json.loads(io.open(str(Path(folder) / "PAYLOAD.json"),
                                  encoding="utf-8", errors="replace").read())
    except Exception:
        return ""
    parts = (data or {}).get("parts")
    if not isinstance(parts, list):
        return ""
    bundles = [p for p in parts
               if isinstance(p, dict) and p.get("kind") == "bundle" and p.get("repo")]
    for part in bundles:
        if str(part.get("file") or "").lower() == str(bundle_name).lower():
            return str(part["repo"])
    if len(bundles) == 1:
        return str(bundles[0]["repo"])
    return ""


def _guess_repo(bundle_name):
    """The bundle's own file name, before `-main.bundle` / `.bundle`."""
    name = str(bundle_name or "")
    for tail in ("-main.bundle", ".bundle"):
        if name.lower().endswith(tail):
            return name[: -len(tail)]
    return name


def _match_project(name, projects):
    """The project folder a bundle belongs to, or None.

    Its own name first; then the longest dash-joined prefix of it that IS a
    folder here. Every hand-cut payload on the live drive names its bundle for
    the cut rather than the repo — `alpha-47abe34..main.bundle`,
    `beta-prompts-south-<date>.bundle` — and those are alpha's and
    beta-prompts's openers (the shape of a real drive). A wrong
    match is not possible from a prefix that is not itself a folder name."""
    bits = str(name or "").split("-")
    while bits:
        found = projects.get("-".join(bits).strip().lower())
        if found is not None:
            return found
        bits.pop()
    return None


def _run(args, cwd=None, timeout=GIT_TIMEOUT):
    """(returncode, output). Counts the call. Never raises."""
    global GIT_CALLS
    GIT_CALLS += 1
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        proc = subprocess.run([str(a) for a in args],
                              cwd=str(cwd) if cwd else None, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, universal_newlines=True,
                              encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, "timed out after %ss" % timeout
    except Exception as exc:
        return 125, repr(exc)


def _scratch_clone(project_path):
    """A read-only window on the project's objects: `git clone --shared
    --no-checkout`, reused between runs, refreshed when it is reused. Returns
    (path, '') or (None, note). The project repo itself is never written."""
    project_path = Path(project_path)
    # The clone is named for the project AND for where that project is, so two
    # folders of the same name on one machine never share one scratch clone.
    stamp = hashlib.sha1(str(project_path).encode("utf-8", "replace")).hexdigest()[:8]
    scratch = WORK_DIR / "clones" / ("%s-%s" % (project_path.name, stamp))
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        (WORK_DIR / "clones").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return None, "scratch clone: %s" % exc
    if not (project_path / ".git").exists():
        return None, "%s is not a git repo here" % project_path.name
    if (scratch / "HEAD").exists() or (scratch / ".git").exists():
        code, out = _run(["git", "-C", str(scratch), "fetch", "--quiet",
                          "--no-tags", "origin",
                          "+refs/heads/*:refs/remotes/origin/*"],
                         timeout=CLONE_TIMEOUT)
        if code == 0:
            return scratch, ""
        # a clone left broken by an interrupted run: start it over
        _rmtree(scratch)
    code, out = _run(["git", "clone", "--shared", "--no-checkout", "--quiet",
                      str(project_path), str(scratch)], timeout=CLONE_TIMEOUT)
    if code != 0:
        return None, "scratch clone of %s failed: %s" % (
            project_path.name, " ".join(out.split())[:80])
    return scratch, ""


def _rmtree(path):
    try:
        import shutil
        shutil.rmtree(str(path), ignore_errors=True)
    except Exception:
        pass


def _cache():
    global _CACHE
    if _CACHE is None:
        data = None
        try:
            data = json.loads(io.open(str(CACHE_FILE), encoding="utf-8",
                                      errors="replace").read())
        except Exception:
            data = None
        if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
            data = {"version": 1, "entries": {}}
        _CACHE = data
    return _CACHE


_CACHE = None
_CACHE_DIRTY = False


def _cache_key(path):
    try:
        st = Path(path).stat()
        return "%s|%d|%d" % (str(Path(path)), st.st_size, int(st.st_mtime * 1000))
    except OSError:
        return ""


def _cache_save():
    global _CACHE_DIRTY
    if not _CACHE_DIRTY or _CACHE is None:
        return
    entries = _CACHE.get("entries") or {}
    if len(entries) > CACHE_MAX:
        keep = sorted(entries.items(),
                      key=lambda kv: (kv[1] or {}).get("seen") or 0,
                      reverse=True)[:CACHE_MAX]
        _CACHE["entries"] = dict(keep)
    try:
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        temp = CACHE_FILE.with_name(CACHE_FILE.name + ".%d.tmp" % os.getpid())
        io.open(str(temp), "w", encoding="utf-8", newline="\n").write(
            json.dumps(_CACHE, ensure_ascii=False, indent=1) + "\n")
        os.replace(str(temp), str(CACHE_FILE))
    except Exception:
        pass
    _CACHE_DIRTY = False


def bundle_openers(bundle_path, project_path, payload_id):
    """({name: text}, note) — every OPENER file in the bundle's tip tree.

    Incremental bundles cannot be read by an empty repo (memory
    `button-up-by-hand`, trap a), so the local project is the object store, used
    read-only through a scratch clone. A bundle whose base is not here — cut FOR
    the other machine, or this repo is behind — is skipped with one note. The
    answer is cached by (path, size, mtime): a second run costs no git call."""
    global CACHE_HITS, CACHE_MISSES, _CACHE_DIRTY
    key = _cache_key(bundle_path)
    cache = _cache()
    if key:
        hit = (cache.get("entries") or {}).get(key)
        if isinstance(hit, dict) and isinstance(hit.get("openers"), dict):
            CACHE_HITS += 1
            return dict(hit["openers"]), str(hit.get("note") or "")

    CACHE_MISSES += 1
    openers, note = {}, ""
    scratch, problem = _scratch_clone(project_path)
    if scratch is None:
        note = "bundle %s: %s" % (payload_id, problem)
    else:
        code, _out = _run(["git", "-C", str(scratch), "bundle", "verify",
                           str(bundle_path)])
        if code != 0:
            note = "bundle %s: base not in this repo" % payload_id
        else:
            code, out = _run(["git", "-C", str(scratch), "bundle",
                              "list-heads", str(bundle_path)])
            refs = []
            for line in (out or "").splitlines():
                bits = line.split(None, 1)
                if len(bits) == 2 and bits[1].strip().startswith("refs/"):
                    refs.append((bits[0].strip(), bits[1].strip()))
            ref = ""
            for wanted in ("refs/heads/main", "refs/heads/master"):
                for _sha, name in refs:
                    if name == wanted:
                        ref = name
                        break
                if ref:
                    break
            if not ref and refs:
                ref = refs[0][1]
            if not ref:
                note = "bundle %s: carries no branch this tool can read" % payload_id
            else:
                code, out = _run(["git", "-C", str(scratch), "fetch", "--quiet",
                                  "--no-tags", str(bundle_path),
                                  "+%s:refs/bundles/x" % ref],
                                 timeout=CLONE_TIMEOUT)
                if code != 0:
                    note = "bundle %s: could not be read (%s)" % (
                        payload_id, " ".join((out or "").split())[:60])
                else:
                    code, out = _run(["git", "-C", str(scratch), "ls-tree",
                                      "--name-only", "refs/bundles/x"])
                    names = [n.strip() for n in (out or "").splitlines()
                             if code == 0 and OPENER_NAME.match(n.strip())]
                    for name in names:
                        code, text = _run(["git", "-C", str(scratch), "show",
                                           "refs/bundles/x:%s" % name])
                        if code == 0:
                            openers[name] = text
    if key:
        cache.setdefault("entries", {})[key] = {
            "openers": openers, "note": note,
            "seen": int(datetime.now().timestamp()), "payload": payload_id}
        _CACHE_DIRTY = True
        _cache_save()
    return openers, note


def read_drive(projects_root, volumes=None, parse=None):
    """([candidate], [note]) — every opener riding a mounted payload's bundle."""
    notes, out = [], []
    try:
        found = (volumes if volumes is not None
                 else mounted_volumes(notes, projects_root))
    except Exception as exc:
        return out, ["drive carriers: %s" % exc]
    if not found:
        return out, notes
    projects = _project_names(projects_root)
    for volume in found:
        path = (volume or {}).get("path")
        if not path:
            continue
        for folder in payload_folders(path):
            payload_id = folder.name
            try:
                bundles = sorted(p for p in folder.iterdir()
                                 if p.is_file() and p.name.lower().endswith(".bundle"))
            except OSError:
                continue
            for bundle in bundles:
                repo = _payload_repo(folder, bundle.name) or _guess_repo(bundle.name)
                project = _match_project(repo, projects)
                if project is None:
                    notes.append("bundle %s: no project folder matches %r"
                                 % (payload_id, str(repo)[:40]))
                    continue
                try:
                    openers, note = bundle_openers(bundle, project, payload_id)
                except Exception as exc:
                    openers, note = {}, "bundle %s: %s" % (payload_id, exc)
                if note:
                    notes.append(note)
                for name in sorted(openers):
                    out.append(candidate("drive:%s" % payload_id, openers[name],
                                         file=name, project=project.name,
                                         payload=payload_id, parse=parse))
    return out, notes


# ── the index, built once per run ─────────────────────────────────────────

def index(tree_path, projects_root, parse=None, volumes=None):
    """{all, notes} — every opener the brain and the drive carry, ready to be
    matched to a lane. Never raises: a failure is a note and an empty list."""
    notes, all_of = [], []
    try:
        brain = read_brain(tree_path, parse=parse)
        for key in sorted(brain):
            all_of.append(brain[key])
    except Exception as exc:
        notes.append("brain carrier: %s" % exc)
    try:
        drive, drive_notes = read_drive(projects_root, volumes=volumes, parse=parse)
        all_of.extend(drive)
        notes.extend(drive_notes)
    except Exception as exc:
        notes.append("drive carriers: %s" % exc)
    return {"all": all_of, "notes": notes}


def _same_project(candidate_project, project):
    left = str(candidate_project or "").strip().lower()
    right = str(project or "").strip().lower()
    return bool(left) and left == right


def candidates_for(idx, project, suffix, header_lane, file_name):
    """Every carrier copy of THIS lane's opener, claimed so it is used once.

    Two rules, either is enough: the same opener FILE NAME inside the same
    project, or the same lane name. The first catches a lane whose folder copy
    has no `lane:` line; the second catches a card written before this build,
    which names its lane but not its project."""
    if not idx:
        return []
    wanted = set()
    if header_lane:
        wanted.add(lane_key(header_lane))
    if suffix:
        wanted.add(lane_key("%s/%s" % (project, suffix)))
    else:
        wanted.add(lane_key(project))
    wanted.discard("")
    out = []
    for item in idx.get("all") or []:
        if item.get("claimed"):
            continue
        same_file = (file_name and item.get("file")
                     and str(item["file"]).lower() == str(file_name).lower()
                     and _same_project(item.get("project"), project))
        # A lane name is not unique across projects (two folders both run a
        # `Style` lane), so a candidate that names its project must match it.
        same_lane = (lane_key(item.get("lane")) in wanted
                     and (not item.get("project")
                          or _same_project(item.get("project"), project)))
        if same_file or same_lane:
            item["claimed"] = True
            out.append(item)
    return out


def project_candidates(idx, project):
    """[[candidate, …], …] — ONE GROUP per lane whose opener has not landed in
    this project's folder: a lane that closed on the other machine and is still
    riding a carrier.

    Grouped by the opener's file name on purpose. A transfer drive holds every
    payload it was ever given — several can carry a copy of the same lane's
    openers — and that is ONE lane with several copies, not several lanes.
    """
    if not idx:
        return []
    groups, order = {}, []
    for item in idx.get("all") or []:
        if item.get("claimed"):
            continue
        if not _same_project(item.get("project"), project):
            continue
        item["claimed"] = True
        key = str(item.get("file") or "").lower() or lane_key(item.get("lane"))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)
    return [groups[key] for key in order]


def unclaimed(idx):
    """Carrier openers no project on this machine could claim. They are kept
    verbatim in TREE.md so a drive-only lane's opener is never dropped by a
    machine that does not have its folder."""
    return [item for item in (idx or {}).get("all") or []
            if not item.get("claimed")]


# ── the winner ────────────────────────────────────────────────────────────

def pick(folder, others, parse=None):
    """{winner, flag, candidates} — newest `written:` wins; ties → folder,
    then brain, then drive. `flag` is '' or the sentence that says, in full,
    which copy is newer than the folder's."""
    pool = [c for c in ([folder] if folder else []) + list(others or []) if c]
    if not pool:
        return {"winner": None, "flag": "", "candidates": []}
    for item in pool:
        if item.get("written_ts") is None and item.get("header"):
            item["written_ts"] = written_ts(item["header"], parse)
    ranked = sorted(
        pool,
        key=lambda c: (-(c.get("written_ts") if c.get("written_ts") is not None
                         else OLDEST),
                       SOURCE_RANK.get(str(c.get("source") or ""), 2),
                       str(c.get("source") or "")))
    winner = ranked[0]
    flag = ""
    if folder is not None and winner is not folder:
        flag = "folder copy written %s · %s copy written %s" % (
            written_words(folder), winner.get("source") or "carrier",
            written_words(winner))
    elif folder is None:
        flag = "no folder copy · %s copy written %s" % (
            winner.get("source") or "carrier", written_words(winner))
    return {"winner": winner, "flag": flag, "candidates": ranked}


def origin_payload(item):
    """The payload a copy first rode in on, when the carrier recorded it — a
    brain copy of a drive opener still knows which payload has to land."""
    origin = str((item or {}).get("origin") or "")
    return origin.split(":", 1)[1] if origin.startswith("drive:") else ""


def absent_head_note(head, source, payload=""):
    """A winner whose `head:` is not in this repo is a NOTE, not
    stale — the commit lands with the payload it rode in on."""
    short = str(head or "")[:12] or "?"
    if not payload and str(source or "").startswith("drive:"):
        payload = str(source).split(":", 1)[1]
    if payload:
        return "head %s not in this repo — lands with %s" % (short, payload)
    return "head %s not in this repo — carried in TREE.md" % short


# ── the lane's own next move ──────────────────────────────────────────────

NUMBERED = re.compile(r"^\s{0,6}(?:\(?\d{1,2}[.)]|\d{1,2}\s+[-–—])\s+(\S.*)$")
# Finished work, not a next move: a carryover opener's "what already happened"
# list is numbered too, and read in document order a lane's next move is a ✅ line.
DONE_STEP = re.compile(r"^(?:\u2705|\[x\]|DONE\b|done\b)", re.I)
NEXT_HEAD = re.compile(
    r"^[\s>*#_`\-·•]*(?:machine'?s?\s+next\s+move|machine\s+next"
    r"|next\s+move|next\s+steps?|next)\b\s*[:.\-—]?\s*(.*)$", re.I)


# `Machine's next move · in this order:` says nothing by itself: the move is the
# line under it. Same for a bare label (the CONNECTOR words below) and a leading
# `1.` — the reader wants the move, not the scaffolding around it.
CONNECTOR = re.compile(
    r"^(?:in this order|in order|as follows|this sitting|then|now|next)?"
    r"[\s:.,;·•—-]*$", re.I)
# `Machine's next move, in this order, ONE AT A TIME:` — the separator after
# "move" is a COMMA, which NEXT_HEAD's own class cannot eat, so the remainder
# starts at the comma and CONNECTOR (anchored, one phrase) never matches it.
# Two shapes are scaffolding whatever follows them: a remainder
# that STARTS with punctuation, and one whose words are connectors only.
LEAD_PUNCT = re.compile(r"^[,;:.·•—–\-/|)\]]")
SCAFFOLD_WORDS = re.compile(
    r"(?:in this order|in order|as follows|this sitting|one at a time"
    r"|one by one|first|then|now|next)", re.I)


def _is_scaffold(text):
    """True when nothing but connector words and punctuation is left — in any
    position, not only at the front."""
    rest = SCAFFOLD_WORDS.sub(" ", str(text or ""))
    return not re.search(r"[A-Za-z0-9]", rest)
MARKER = re.compile(r"^[\s>*_`·•:—-]*(?:[-*+]\s+|\(?\d{1,2}[.)]\s+)?")
PARENTHETICAL = re.compile(r"^\([^)]*\)\s*[:\-—]?\s*")


def _clean_move(text):
    """A move with its scaffolding off: bullets, `1.`, a leading aside, a
    connector. '' when nothing but scaffolding was there."""
    out = plain(text)
    for _ in range(3):
        before = out
        out = MARKER.sub("", out, count=1)
        out = PARENTHETICAL.sub("", out, count=1)
        out = out.strip(" *_`·•:—-")
        if out == before:
            break
    if CONNECTOR.match(out) or LEAD_PUNCT.match(out) or _is_scaffold(out):
        return ""
    return out


def opener_step(body):
    """The first move the opener itself names, in this order: what a
    `Machine's next move` / `NEXT` heading points at, then the first numbered
    step that is not already done. '' when the opener names no move.

    The heading comes FIRST on purpose. A carryover opener opens with a plain
    WHERE WE ARE block whose "what already happened" list is numbered, so
    reading document order alone would make every lane's `next:` a finished ✅
    line."""
    lines = str(body or "").split("\n")
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        head = NEXT_HEAD.match(stripped)
        if not head:
            continue
        rest = _clean_move(head.group(1))
        if rest:
            return words(rest, 12)
        for follow in lines[index + 1:]:
            if follow.strip():
                step = _clean_move(follow)
                if step:
                    return words(step, 12)
                continue        # that line was scaffolding too: read the next
            # a blank line between the heading and its move is fine
    for raw in lines:
        step = NUMBERED.match(raw)
        if step and not DONE_STEP.match(plain(step.group(1))):
            return words(step.group(1), 12)
    return ""


# ── whose to-do is it ─────────────────────

# A shared STATUS names a to-do's lane as its LEADING word, up to the first
# separator: `ALPHA-B2 - …`, `BETA - …`, `GAMMA: …`, `DELTA · …`,
# `KILO/ONE fix …`. A word anywhere else in the line is a mention, not an owner
# (a BETA line that mentions "the Alpha" is BETA's).
LANE_WORD = re.compile(r"^\s*([^\s:\-\u00b7]+)")


def lane_word(text):
    """The to-do's leading word, up to the first `-`, `:`, `·` or space; ''."""
    hit = LANE_WORD.match(plain(text or ""))
    return hit.group(1) if hit else ""


def word_key(text):
    """The one spelling two names of a lane agree on — wake-screen's lane_key:
    lowercase, and every run of space, `/`, `_`, `-` one `/`."""
    return re.sub(r"[\s/_\-]+", "/", str(text or "").strip().lower()).strip("/")


def names_lane(text, *tokens):
    """Does this to-do START with one of the lane's own names — the opener's
    suffix (`Door`), its header lane (`ALPHA/Door`)? A line with no lane word,
    or another lane's, is not this lane's."""
    word = word_key(lane_word(text))
    if not word:
        return False
    return any(word == word_key(t) for t in tokens if str(t or "").strip())


def lane_next_move(body, token, todos, project_move, cut=None, debracket=None, lane=None):
    """(move, where it came from) — the LANE's move, never the project's first
    open item when the lane can speak for itself.

    1  the opener body's own first step
    2  else the first open STATUS to-do that STARTS with this lane's name (the
       opener suffix `token`, or the header `lane` when given — names_lane),
       urgent first; a to-do that only mentions it is another lane's
    3  else the project's move, marked `(project)` so nobody reads it as the
       lane's own
    """
    step = opener_step(body)
    if step:
        return step, "opener"
    shorten = cut or (lambda text, limit: text[:limit])
    flat = debracket or (lambda text: text)
    token = str(token or "").strip()
    if token:
        matching = [t for t in (todos or [])
                    if names_lane(str(t.get("text") or ""), token, lane or "")]
        matching.sort(key=lambda t: not t.get("urgent"))
        if matching:
            return shorten(flat(matching[0]["text"]), 80), "lane-status"
        return "%s (project)" % project_move, "project"
    return project_move, "project"


# ── the model line that was never walked ──────────────────────────────────

JUDGMENT = re.compile(
    r"\b(rul(?:e|es|ed|ing|ings)|grad(?:e|es|ed|ing)|decid(?:e|es|ed|ing)"
    r"|design(?:|s|ed|ing)|diagnos(?:e|es|ed|ing)|revis(?:e|es|ed|ing))\b",
    re.I)
WALKED_MINDS = re.compile(r"\b(OPUS|SONNET)\b", re.I)


def judgment_unwalked(header, body):
    """The judgment verb found in the body, when the model line names OPUS or
    SONNET and the header carries no `judgment:` line at all. '' otherwise —
    a `judgment:` line, even `none`, means the line was walked."""
    header = header or {}
    if "judgment" in header:
        return ""
    if not WALKED_MINDS.search(str(header.get("model") or "")):
        return ""
    found = JUDGMENT.search(str(body or ""))
    return found.group(0) if found else ""


def judgment_sentence(verb):
    return ('model line not walked — the body says "%s" and the header has no '
            'judgment: line' % verb)


# ── cli (this module is a library; the flags are for a human checking it) ──

USAGE = """opener_carriers.py — the brain and the drive as opener carriers.

A library for tools/collect-openers.py. Run on its own it reports what the
carriers hold right now, which is the quickest way to see what the collector
will read:

  --brain [<TREE.md>]   the openers TREE.md carries (default: the hub's own)
  --drive               the openers a mounted *-TX-* payload's bundle carries
  --help

COLLECT_OPENERS_VOLUMES=<dir>[%s<dir>] treats each directory as a volume root.
COLLECT_OPENERS_ROOT=<dir> is the projects root a bundle's repo is matched in.
COLLECT_OPENERS_ENGINE=<dir> is where carrier_preflight.py lives.
COLLECT_OPENERS_WORK=<dir> is the scratch the bundle cache and clones live in.
""" % os.pathsep


def _hub():
    return Path(__file__).resolve().parent.parent


def main(argv):
    argv = list(argv)
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(USAGE)
        return 0
    known = ("--brain", "--drive")
    rest = [a for a in argv if a.startswith("-") and a not in known]
    if rest:
        sys.stdout.write(USAGE)
        return 2
    if not argv:
        argv = ["--brain", "--drive"]
    if "--brain" in argv:
        index_of = argv.index("--brain")
        after = argv[index_of + 1] if index_of + 1 < len(argv) else ""
        path = Path(after) if after and not after.startswith("-") else _hub() / "TREE.md"
        found = read_brain(path)
        sys.stdout.write("brain: %s — %d opener%s\n"
                         % (path, len(found), "" if len(found) == 1 else "s"))
        for key in sorted(found):
            item = found[key]
            sys.stdout.write("  %-28s %s · %s\n"
                             % (item["lane"][:28], item["file"] or "—",
                                written_words(item)))
    if "--drive" in argv:
        root = os.environ.get("COLLECT_OPENERS_ROOT") or str(Path.home() / "Projects")
        notes = []
        volumes = mounted_volumes(notes, root)
        sys.stdout.write("volumes: %s\n"
                         % (", ".join("%s (%s)" % (v["label"], v["path"])
                                      for v in volumes) or "none"))
        found, more = read_drive(root, volumes=volumes)
        notes.extend(more)
        for item in found:
            sys.stdout.write("  %-28s %s · %s · %s\n"
                             % (item["lane"][:28], item["file"],
                                item["source"], written_words(item)))
        for note in notes:
            sys.stdout.write("  note: %s\n" % note)
        sys.stdout.write("drive: %d opener%s · %d git call%s\n"
                         % (len(found), "" if len(found) == 1 else "s",
                            GIT_CALLS, "" if GIT_CALLS == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
