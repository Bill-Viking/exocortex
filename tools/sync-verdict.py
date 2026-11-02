#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync-verdict.py — "are we synced?" answered in ONE line, from the pulse's own files.

    python3 tools/sync-verdict.py            the line (python on Windows)
    python3 tools/sync-verdict.py --long     the line, then one line per thing behind it
    python3 tools/sync-verdict.py --json     the same facts, as data
    python3 tools/sync-verdict.py --write    also write sync-verdict-<machine>.json in the hub
                                             (the pulse's beat does this; every surface reads it)
                                             — only when the verdict CHANGED, or its last write is
                                             REFRESH_MINUTES old: the brain carries a file only once
                                             it has been still for 60 s, and a file rewritten every
                                             beat would never cross to the other machine
    python3 tools/sync-verdict.py --help     this text; nothing runs

It answers four things in one place: the one-line verdict, no repo without a carrier, no
project folder that is not a repo, and the carrier word a ledger line names. A record can be
level while no surface says so, and a repo with no carrier can fall through every road with
nothing said; this line says both.

THE LINE is exactly one of these, under 120 characters, the same for the same record:

    synced · brain level · 29 repos level · read 08:12
    behind 3 h · the SOUTH's heads are from 20:35 · 2 repos differ: field-notes, garden-log
    owed: NB-TX-SL-013 on the drive to the SOUTH · GL-TX-008 waits in the SOUTH's outbox
    unknown · <what the files cannot say>

and, whenever it is not empty, the carrier part rides at its end, even after `synced`:

    no carrier: garden-log, Lab Notes

WHAT EACH WORD MAY CLAIM (nothing is inferred beyond the bytes):
  synced   every repo both machines declare has the SAME head in heads-<machine>.json; the other
           machine's picture is from a beat under 20 minutes old (its live-sessions file, written
           every beat, or its heads file's own stamp, whichever is newer); this machine's last
           brain pull (pulse-last-pull-<machine>.log) is under 20 minutes old, pulled, and skipped
           no conflict; and nothing is owed on any carrier. Anything the files cannot say is
           `unknown`, never `synced`.
  behind   the other machine's picture is older than 20 minutes (said as its age), or heads
           differ, or this machine's last pull failed or skipped a conflict. A repo on ONE machine
           only differs when nothing but a person can bring it across (a drive project, or a repo
           with no carrier); a confirmed github repo on one machine only is GitHub's to carry and
           `buttonup.py arrive` clones it — said in --long, never on the line. A repo the registry
           marks `stays` or `upstream-readonly` is carried by nobody, on purpose, and never
           counts as level or differing.
  owed     an OPEN drive-ledger line in the hub STATUS or a project STATUS, read through the
           engine's own reader (carrier_preflight.read_ledger — one copy of the grammar), in the
           words the record uses: `OWED TO THE <M>` is ON THE DRIVE, `waits in the <M>'s outbox`
           is in that machine's own outbox. A payload the destination's landings file marks
           landed is settled, not owed.
  unreadable  an OPEN line that carries a ledger phrase in its first words but
           names no payload id before it (a human note such as `DRIVE LEDGER - EVENING CUT OWED TO
           THE …`) is never counted as a payload. The one line does not change shape for it: it
           gets its OWN short SECOND line, `N ledger line(s) unreadable · <file>:<line>, …` (at
           most two named, then `+K`; the count alone if the names would overrun the width),
           printed under the line, carried in the JSON as `line2` and empty at zero — so what the
           reader could not count is named every time, never dropped to make the line fit. It needs an
           engine with read_ledger_full; an older engine reads as before.
  no carrier   a repo this machine's pulse sees (heads-<here>.json) whose carry/projects.json entry
           is missing, has no carrier, or is an UNCONFIRMED github entry (nothing pushes those),
           and whose own STATUS `## Important` rules neither no-remote nor `stays on <machine>`;
           a repo only the OTHER machine declares, whose registry entry says nothing, is named
           with that machine's name (its STATUS cannot be read from here); and a PROJECT FOLDER
           here (its own STATUS.md or OPENER*.md) that is not a repo and carries no ruled word
           (`init` still counts until the hub has made it a repo). The words are the human's:
           `buttonup.py registry --set <name> github|drive|stays-here` for a repo,
           `… init|stays-here|ignore` for a folder.

WHAT IT READS, and never more: heads-<m>.json, live-sessions-<m>.json and landings-<m>.json for
every machine the brain carries; held-<m>.json (the github beat's holds); this machine's
pulse-last-pull-<machine>.log; carry/projects.json; each project's STATUS.md; the projects root's
own listing; ~/.exocortex/csync/csync-<machine>.json (half A's own state — whether it has beaten
here). It runs NO git command and opens NO network connection: every fact about a repo is what the
pulse already published. It writes nothing unless `--write`, and then only its own json.

SEAMS, for the gate and nothing else: --hub DIR (a hub whose own machine.json names the machine),
--projects DIR, --engine DIR (where carrier_preflight.py is), --state-dir DIR (csync), --now ISO
(also EXO_NOW).

Stdlib only, Python 3.9, macOS and Windows. Exit 0 = a line was printed · 2 = usage.
"""
import datetime
import importlib.util
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TOOL_VERSION = "1"
REFRESH_MINUTES = 30                  # an unchanged verdict is rewritten at most this often
FRESH_MINUTES = 20                    # an older picture is not "now"
LINE_MAX = 119                        # "under 120 characters"
NOT_CARRIED = ("stays", "upstream-readonly")      # carried by nobody, on purpose
REPO_WORDS = ("github", "drive", "stays-here")
FOLDER_WORDS = ("init", "stays-here", "ignore")
CARRIER_ALIASES = {"stays-here": "stays", "stays_here": "stays", "stay": "stays", "stays": "stays",
                   "github": "github", "drive": "drive", "upstream-readonly": "upstream-readonly"}
FOLDER_ALIASES = {"init": "init", "stays-here": "stays", "stays_here": "stays", "stays": "stays",
                  "stay": "stays", "ignore": "ignore"}
NO_REMOTE_RULING = re.compile(r"\bno[- ]remote\b|\blocal[- ]only\b|\bnever[- ]push(?:ed)?\b", re.I)
KNOWN_FLAGS = ("--long", "--json", "--write", "--help", "-h", "--hub", "--projects", "--engine",
               "--state-dir", "--now")
VALUED = ("--hub", "--projects", "--engine", "--state-dir", "--now")


# --------------------------------------------------------------------------
# small readers — every one of them fails soft
# --------------------------------------------------------------------------

def read_json(path, default=None):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def read_text(path):
    try:
        with io.open(str(path), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def parse_iso(text):
    if not text:
        return None
    raw = str(text).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        when = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.astimezone()
    return when


def now_of(given=None):
    """The clock, with ONE seam (--now / EXO_NOW) so a gate can hold it still."""
    for text in (given, os.environ.get("EXO_NOW")):
        when = parse_iso(text)
        if when is not None:
            return when.astimezone()
    return datetime.datetime.now().astimezone()


def span(minutes):
    """How long, in the words a person uses: 12 min · 3 h · 2 days."""
    minutes = max(0.0, float(minutes))
    if minutes < 60:
        return "%d min" % max(1, int(minutes))
    if minutes < 48 * 60:
        return "%d h" % int(minutes / 60)
    return "%d days" % int(minutes / (24 * 60))


def clock(when, now):
    """A moment as the reader wants it: 20:35 today, Sun 22:15 this week, Sep 20 22:15 before."""
    if when is None:
        return "an unrecorded time"
    local = when.astimezone(now.tzinfo)
    if local.date() == now.date():
        return local.strftime("%H:%M")
    if abs((now.date() - local.date()).days) < 7:
        return local.strftime("%a %H:%M")
    return local.strftime("%b %d %H:%M")


def names(items, keep):
    """'a, b, c +2' — the first `keep` names, then the count of the rest."""
    items = list(items)
    if keep <= 0 or not items:
        return ""
    shown = items[:keep]
    rest = len(items) - len(shown)
    return ", ".join(shown) + (" +%d" % rest if rest else "")


def upper(name):
    return str(name or "").strip().upper()


# --------------------------------------------------------------------------
# the record: who am I, where is everything
# --------------------------------------------------------------------------

def record_for(hub):
    """This machine's record: the hub's own machine.json when it has one (a gate's scratch
    identity — publish-heads.py's precedence), else the record the path resolver finds."""
    if hub is not None:
        found = read_json(Path(hub) / "machine.json")
        if isinstance(found, dict):
            return found
    try:
        from exo_paths import paths                                 # noqa: E402
        machine_file = paths(tool_file=__file__)["machine_file"]
        found = read_json(machine_file) if machine_file else None
        if isinstance(found, dict):
            return found
    except Exception:
        pass
    found = read_json(Path.home() / "orchestrator-sync" / "machine.json")
    return found if isinstance(found, dict) else {}


def engine_dir(given=None):
    if given:
        return Path(given)
    try:
        from exo_paths import paths                                 # noqa: E402
        found = paths(tool_file=__file__)["sync_dir"]
        if found:
            return Path(found)
    except Exception:
        pass
    return Path.home() / "orchestrator-sync"


def load_engine(folder):
    """The engine's own carrier_preflight module — the one copy of the ledger's grammar. Loaded
    by path under a private name; None when it is not there or does not import."""
    target = Path(folder) / "carrier_preflight.py" if folder else None
    if target is None or not target.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("sync_verdict_carrier_preflight", str(target))
        module = importlib.util.module_from_spec(spec)
        saved = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = saved
        return module
    except Exception:
        return None


def machine_words(record, hub):
    """Every machine name the record knows: the registry's, this machine's, and every machine the
    brain carries a file for — so `stays on <machine>` is read for any fleet, never a typed list."""
    found = set()
    try:
        from exo_registry import registry, machine_names                # noqa: E402
        found.update(str(n).lower() for n in machine_names(registry(hub)))
    except Exception:
        pass
    found.add(str(record.get("name") or "").lower())
    for pattern in ("heads-*.json", "live-sessions-*.json", "roots-*.json"):
        for path in Path(hub).glob(pattern):
            found.add(path.stem.split("-", 2 if pattern.startswith("live") else 1)[-1].lower())
    return sorted(n for n in found if n)


# --------------------------------------------------------------------------
# the carrier rule — ONE copy, read by buttonup.py and the wake screen too
# --------------------------------------------------------------------------

def normal_carrier(word):
    return CARRIER_ALIASES.get(str(word or "").strip().lower(), str(word or "").strip().lower())


def registry_entries(hub):
    """{name: entry} from carry/projects.json — both spellings buttonup.load_registry reads."""
    body = read_json(Path(hub) / "carry" / "projects.json")
    if not isinstance(body, dict):
        return {}
    entries = {}
    nested = body.get("projects")
    if isinstance(nested, dict):
        entries.update({k: v for k, v in nested.items() if isinstance(v, dict)})
    entries.update({k: v for k, v in body.items() if isinstance(v, dict) and k != "projects"})
    return entries


def important_lines(status_text):
    """The lines of a STATUS's `## Important` section — the project's own binding rules."""
    out, inside = [], False
    for line in str(status_text or "").splitlines():
        if re.match(r"^##\s+Important\b", line.strip(), re.I):
            inside = True
            continue
        if inside and re.match(r"^#{1,2}\s", line.strip()):
            break
        if inside and line.strip():
            out.append(line.strip())
    return out


def important_ruling(status_text, machines):
    """('stays', line) | ('drive', line) | None — what a project's STATUS `## Important` rules
    about its carrier. `stays on <machine>` wins over a no-remote word: it is the narrower rule."""
    words = "|".join(re.escape(m) for m in sorted(set(machines or []), key=len, reverse=True)
                     if m and m != "this")
    stays = re.compile(r"\bstays on (?:the |this )?(?:%smachine)\b" % ((words + "|") if words else ""),
                       re.I)
    lines = important_lines(status_text)
    for line in lines:
        if stays.search(line):
            return "stays", " ".join(line.lstrip("-*[ ]x").split())[:110]
    for line in lines:
        if NO_REMOTE_RULING.search(line):
            return "drive", " ".join(line.lstrip("-*[ ]x").split())[:110]
    return None


def carrier_state(entry, status_text, machines):
    """{carrier, how, why} for one repo. `carrier` is '' when NOTHING carries it: no entry, an
    entry with no carrier, an unknown word, or an unconfirmed github entry (nothing pushes one) —
    unless the project's own STATUS `## Important` rules no-remote (the drive) or `stays on
    <machine>` (nobody). `how` says where the answer came from: registry · status · ''."""
    word = normal_carrier((entry or {}).get("carrier"))
    if word in ("drive", "stays", "upstream-readonly"):
        return {"carrier": word, "how": "registry", "why": ""}
    if word == "github":
        if (entry or {}).get("confirmed") is True:
            return {"carrier": "github", "how": "registry", "why": ""}
        why = "github, unconfirmed — nothing pushes it until the machine that holds it confirms"
    elif word:
        why = "carrier %r is not a word the registry knows" % word
    elif entry is None:
        why = "no entry in carry/projects.json"
    else:
        why = "its entry names no carrier"
    ruled = important_ruling(status_text, machines) if status_text is not None else None
    if ruled is not None:
        return {"carrier": ruled[0], "how": "status", "why": "its STATUS says: %s" % ruled[1]}
    return {"carrier": "", "how": "", "why": why}


def project_folders(projects_root):
    """[(name, path)] — every folder directly under the projects root that is NOT a repo and
    carries the record's own mark of a project: a STATUS.md or an OPENER*.md of its own."""
    out = []
    try:
        entries = sorted(Path(projects_root).iterdir(), key=lambda p: p.name.lower())
    except (OSError, TypeError):
        return out
    for entry in entries:
        try:
            if entry.name.startswith(".") or not entry.is_dir() or (entry / ".git").exists():
                continue
            marked = (entry / "STATUS.md").is_file() or any(
                p.is_file() for p in entry.glob("OPENER*.md"))
        except OSError:
            continue
        if marked:
            out.append((entry.name, entry))
    return out


def folder_state(name, entry, status_text, machines, entries):
    """{word, why, loose_by}: word '' = no ruling yet (counted), 'init' = ruled, the hub owes the
    repo (still counted), 'stays' / 'ignore' = ruled, silent. `loose_by` names the projects whose
    payloads already carry some of its files (a registry `loose` source)."""
    loose_by = []
    for other, value in sorted(entries.items(), key=lambda kv: kv[0].lower()):
        for rider in (value or {}).get("loose") or []:
            if isinstance(rider, dict) and str(rider.get("src") or "") == name:
                loose_by.append({"project": other, "files": list(rider.get("files") or [])})
    word = FOLDER_ALIASES.get(str((entry or {}).get("folder") or "").strip().lower(), "")
    if not word and normal_carrier((entry or {}).get("carrier")) == "stays":
        word = "stays"
    if word:
        return {"word": word, "why": "ruled %s in carry/projects.json" % word, "loose_by": loose_by}
    ruled = important_ruling(status_text, machines) if status_text is not None else None
    if ruled is not None and ruled[0] == "stays":
        return {"word": "stays", "why": "its STATUS says: %s" % ruled[1], "loose_by": loose_by}
    return {"word": "", "why": "a project folder with no repo and no ruled word",
            "loose_by": loose_by}


# --------------------------------------------------------------------------
# the facts
# --------------------------------------------------------------------------

def heads_of(hub, machine):
    body = read_json(Path(hub) / ("heads-%s.json" % machine))
    if isinstance(body, dict) and isinstance(body.get("projects"), dict):
        return body
    return None


def beat_of(hub, machine):
    body = read_json(Path(hub) / ("live-sessions-%s.json" % machine))
    return parse_iso((body or {}).get("when")) if isinstance(body, dict) else None


def landings_of(hub, machine):
    body = read_json(Path(hub) / ("landings-%s.json" % machine))
    found = (body or {}).get("landings") if isinstance(body, dict) else None
    return found if isinstance(found, dict) else {}


def brain_facts(hub, machine, now):
    """This machine's last brain pull, from the pulse's own verbatim report of it."""
    path = Path(hub) / ("pulse-last-pull-%s.log" % machine)
    text = read_text(path)
    if text is None:
        return {"state": "none", "when": None, "why": "no brain pull is recorded here"}
    first = text.splitlines()[0] if text.splitlines() else ""
    stamp = re.search(r"·\s*(\S+)\s*$", first)
    when = parse_iso(stamp.group(1)) if stamp else None
    out = {"when": when.isoformat() if when else None, "file": path.name}
    conflicts = re.search(r"(\d+)\s+CONFLICT", text)
    pulled = re.search(r"pulled (\d+) file\(s\)", text)
    if when is None:
        out.update(state="none", why="the last pull report carries no time")
    elif not pulled:
        out.update(state="failed", why="the last pull at %s did not finish" % clock(when, now))
    elif conflicts:
        n = int(conflicts.group(1))
        out.update(state="conflicts", why="%d conflict%s skipped at %s"
                   % (n, "" if n == 1 else "s", clock(when, now)))
    elif (now - when).total_seconds() / 60.0 > FRESH_MINUTES:
        out.update(state="stale", why="the last pull here was %s ago (%s)"
                   % (span((now - when).total_seconds() / 60.0), clock(when, now)))
    else:
        out.update(state="level", why="pulled at %s" % clock(when, now))
    return out


def owed_items(hub, projects_root, machine, engine, fallback_carriers, unreadable=None):
    """(open owed items, how they were read). Read through the ENGINE's own ledger reader and its
    own landed-marker, applied per destination; else the last pull's carriers file.

    When the engine has `read_ledger_full`, the lines it could not read as a payload (no
    payload id in their first words) are appended to `unreadable` — never counted as owed."""
    items, how = None, ""
    if engine is not None and hasattr(engine, "read_ledger"):
        try:
            if hasattr(engine, "read_ledger_full"):
                body = engine.read_ledger_full(str(hub), str(projects_root or hub), machine)
                items = list(body.get("owed") or [])
                if unreadable is not None:
                    unreadable.extend(dict(u) for u in body.get("unreadable") or []
                                      if isinstance(u, dict))
            else:
                items = engine.read_ledger(str(hub), str(projects_root or hub), machine)
            by_to = {}
            for item in items:
                by_to.setdefault(str(item.get("to") or "").lower(), []).append(item)
            for dest, group in by_to.items():
                if dest and hasattr(engine, "mark_landed"):
                    engine.mark_landed(group, str(hub), dest)
            how = "the ledger, read now%s" % ("" if hasattr(engine, "outbox_from_line") else
                                             " (this engine predates the outbox word)")
        except Exception:
            items = None
    if items is None:
        body = fallback_carriers if isinstance(fallback_carriers, dict) else {}
        items = [dict(o) for o in (body.get("owed") or []) if isinstance(o, dict)]
        how = "the last pull's carriers file (%s)" % (body.get("checked") or "never written")
    out = []
    for item in items:
        if item.get("landed") is not None:
            continue                                  # settled: landed, only the tick is owed
        item = dict(item)
        item.setdefault("carrier", "drive")
        item["label"] = payload_label(item.get("payload"))
        out.append(item)
    return out, how


def payload_label(text):
    """A payload in the record's own words, without a ledger line's scaffolding."""
    label = re.sub(r"^[!\s]*(?:DRIVE LEDGER\s*[-–—·:]*\s*)?", "", str(text or "")).strip()
    return label or str(text or "a payload")


def newer_side(repo, here, there, head_here, head_there, landings):
    """Which machine holds the newer head, from the landings files alone: a machine that once
    LANDED the other's head holds it in its history. '' when the files cannot say."""
    for pid, row in sorted((landings.get(there) or {}).items()):
        bundle = ((row or {}).get("receipts") or {}).get("bundle") if isinstance(row, dict) else None
        if isinstance(bundle, dict) and str(bundle.get("repo") or "") == repo \
                and str(bundle.get("head_after") or "") == head_here:
            return there, "the %s landed the %s's head in %s" % (upper(there), upper(here), pid)
    for pid, row in sorted((landings.get(here) or {}).items()):
        bundle = ((row or {}).get("receipts") or {}).get("bundle") if isinstance(row, dict) else None
        if isinstance(bundle, dict) and str(bundle.get("repo") or "") == repo \
                and str(bundle.get("head_after") or "") == head_there:
            return here, "the %s landed the %s's head in %s" % (upper(here), upper(there), pid)
    return "", ""


def gather(hub, projects_root=None, engine_path=None, state_dir=None, now=None):
    """Every fact the line is made from, as one dict. Reads only."""
    hub = Path(hub)
    now = now or now_of()
    record = record_for(hub)
    here = str(record.get("name") or "unknown").strip().lower()
    roots = record.get("roots") or {}
    projects_root = Path(projects_root) if projects_root else (
        Path(roots["projects"]) if roots.get("projects") else None)
    machines = machine_words(record, hub)
    entries = registry_entries(hub)
    engine = load_engine(engine_dir(engine_path))
    facts = {"machine": here, "read": now.replace(microsecond=0).isoformat(), "tool":
             "sync-verdict.py %s" % TOOL_VERSION, "fresh_minutes": FRESH_MINUTES,
             "brain": brain_facts(hub, here, now), "others": [], "level": [], "differ": [],
             "only_one_side": [], "not_carried": [], "modified": [], "same_head_elsewhere": [],
             "held": [], "owed": [], "owed_read": "", "unreadable": [], "no_carrier": [],
             "no_repo": [],
             "csync": {}, "unknown": ""}

    heads_here = heads_of(hub, here)
    others = []
    for path in sorted(hub.glob("heads-*.json")):
        name = path.stem[len("heads-"):].lower()
        if name and name != here:
            others.append(name)
    for path in sorted(hub.glob("live-sessions-*.json")):
        name = path.stem[len("live-sessions-"):].lower()
        if name and name != here and name not in others:
            others.append(name)

    status_cache = {}

    def status_of(name):
        if name not in status_cache:
            status_cache[name] = (read_text(projects_root / name / "STATUS.md")
                                  if projects_root is not None else None)
        return status_cache[name]

    def state_of(name, local):
        return carrier_state(entries.get(name), status_of(name) if local else None, machines)

    landings = {m: landings_of(hub, m) for m in [here] + others}

    # ---- the heads, machine by machine --------------------------------------------------------
    mine = (heads_here or {}).get("projects") or {}
    level_names, differ, only_one = set(), {}, []
    for other in others:
        body = heads_of(hub, other)
        beat = beat_of(hub, other)
        published = parse_iso((body or {}).get("published"))
        as_of = max([t for t in (beat, published) if t is not None], default=None)
        age = (now - as_of).total_seconds() / 60.0 if as_of else None
        facts["others"].append({
            "machine": other, "heads": body is not None,
            "beat": beat.isoformat() if beat else None,
            "published": published.isoformat() if published else None,
            "as_of": as_of.isoformat() if as_of else None,
            "age_min": round(age, 1) if age is not None else None,
            "fresh": age is not None and age <= FRESH_MINUTES})
        if body is None:
            continue
        theirs = body.get("projects") or {}
        for name in sorted(set(mine) | set(theirs), key=str.lower):
            a, b = mine.get(name), theirs.get(name)
            state = state_of(name, a is not None)
            if state["carrier"] in NOT_CARRIED:
                if name not in [n["name"] for n in facts["not_carried"]]:
                    facts["not_carried"].append({"name": name, "carrier": state["carrier"]})
                continue
            if isinstance(a, dict) and isinstance(b, dict):
                if a.get("head") and a.get("head") == b.get("head"):
                    level_names.add(name)
                    continue
                side, why = newer_side(name, here, other, str(a.get("head") or ""),
                                       str(b.get("head") or ""), landings)
                differ.setdefault(name, {
                    "name": name, "carrier": state["carrier"] or "none", "machine": other,
                    "here": {"branch": a.get("branch"), "head": a.get("head")},
                    "there": {"branch": b.get("branch"), "head": b.get("head")},
                    "newer": side, "newer_why": why or "the files cannot say",
                    "branches": "same" if a.get("branch") == b.get("branch") else "different"})
                continue
            holder = here if isinstance(a, dict) else other
            stand = a if isinstance(a, dict) else b
            row = {"name": name, "on": holder, "carrier": state["carrier"] or "none",
                   "branch": (stand or {}).get("branch"), "head": (stand or {}).get("head")}
            twin = [(m, n) for m, pool in ((here, mine), (other, theirs)) if m != holder
                    for n, s in pool.items() if isinstance(s, dict)
                    and s.get("head") and s.get("head") == row["head"]]
            if twin:
                facts["same_head_elsewhere"].append({"name": name, "on": holder,
                                                      "twin": twin[0][1], "twin_on": twin[0][0],
                                                      "head": row["head"]})
            if state["carrier"] == "github":
                only_one.append(row)                  # GitHub carries it; arrive clones it
            else:
                row["why"] = "only on the %s" % upper(holder)
                differ.setdefault(name, dict(row, machine=other, newer=holder,
                                             newer_why="only the %s has it" % upper(holder),
                                             branches=""))
    facts["level"] = sorted(level_names - set(differ), key=str.lower)
    rank = {"drive": 0, "none": 1, "github": 2}
    facts["differ"] = sorted(differ.values(), key=lambda d: (rank.get(d["carrier"], 1),
                                                             d["name"].lower()))
    facts["only_one_side"] = only_one
    for name, stand in sorted(mine.items(), key=lambda kv: kv[0].lower()):
        if isinstance(stand, dict) and stand.get("tracked_dirty"):
            facts["modified"].append({"name": name, "files": stand["tracked_dirty"], "on": here})

    # ---- what the github beat holds, both machines --------------------------------------------
    for m in [here] + others:
        body = read_json(hub / ("held-%s.json" % m), {}) or {}
        for item in body.get("items") or []:
            if isinstance(item, dict):
                facts["held"].append({"on": m, "project": item.get("project"),
                                      "reason": item.get("reason"), "owner": item.get("owner"),
                                      "next": item.get("next"), "since": item.get("since")})
    state_folder = Path(state_dir) if state_dir else Path(
        os.environ.get("EXO_CSYNC_STATE_DIR") or (Path.home() / ".exocortex" / "csync"))
    csync = read_json(state_folder / ("csync-%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "-", here)))
    if isinstance(csync, dict):
        facts["csync"] = {"beaten_here": True, "said": len(csync.get("said") or {})}
    else:
        facts["csync"] = {"beaten_here": False, "said": 0}

    # ---- what is owed on a carrier ------------------------------------------------------------
    carriers = read_json(hub / ("carriers-%s.json" % here), {})
    facts["owed"], facts["owed_read"] = owed_items(hub, projects_root, here, engine, carriers,
                                                   facts["unreadable"])

    # ---- no carrier: repos here, repos only there, folders here -------------------------------
    for name in sorted(mine, key=str.lower):
        state = state_of(name, True)
        if not state["carrier"]:
            facts["no_carrier"].append({"name": name, "on": here, "why": state["why"]})
    for other in others:
        theirs = (heads_of(hub, other) or {}).get("projects") or {}
        for name in sorted(theirs, key=str.lower):
            if name in mine:
                continue
            state = state_of(name, False)
            if not state["carrier"] and name not in [n["name"] for n in facts["no_carrier"]]:
                facts["no_carrier"].append({"name": name, "on": other, "why": state["why"]})
    if projects_root is not None:
        for name, path in project_folders(projects_root):
            st = folder_state(name, entries.get(name), read_text(path / "STATUS.md"), machines,
                              entries)
            if st["word"] in ("", "init"):
                facts["no_repo"].append({"name": name, "on": here, "word": st["word"],
                                         "why": st["why"], "loose_by": st["loose_by"]})

    # ---- what the files cannot say ------------------------------------------------------------
    if heads_here is None:
        facts["unknown"] = "the %s has not published its heads" % upper(here)
    elif not others:
        facts["unknown"] = "no other machine has published its heads"
    elif not any(o["heads"] for o in facts["others"]):
        facts["unknown"] = "no heads from the %s" % " or the ".join(upper(o) for o in others)
    return facts


# --------------------------------------------------------------------------
# the one line
# --------------------------------------------------------------------------

def owed_part(owed, keep):
    """'NB-TX-SL-013 +8 on the drive to the SOUTH · GL-TX-008 waits in the SOUTH's outbox' —
    grouped by carrier and place, in the order the record lists them."""
    groups, order = {}, []
    for item in owed:
        if item.get("carrier") == "outbox":
            key = ("outbox", upper(item.get("at")))
        else:
            key = ("drive", upper(item.get("to")))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item["label"])
    bits = []
    for kind, place in order:
        ids = groups[(kind, place)]
        said = names(ids, keep) if keep > 0 else "%d payload%s" % (len(ids), "" if len(ids) == 1 else "s")
        if kind == "outbox":
            verb = "waits" if (len(ids) == 1) else "wait"
            bits.append("%s %s in the %s's outbox" % (said, verb, place or "OTHER MACHINE"))
        else:
            bits.append("%s on the drive to the %s" % (said, place or "OTHER MACHINE"))
    return " · ".join(bits)


def second_line(facts):
    """The SECOND line — what the ledger holds that no reader can count, named by file and
    line (at most two, then `+K`): `3 ledger lines unreadable · STATUS.md:7, STATUS.md:8 +1`.
    Empty at zero. Under LINE_MAX too: the count alone when the names would overrun."""
    unreadable = facts.get("unreadable") or []
    if not unreadable:
        return ""
    n = len(unreadable)
    words = "%d ledger line%s unreadable" % (n, "" if n == 1 else "s")
    where = ["%s:%s" % (u.get("file") or "?", u.get("line") or "?") for u in unreadable]
    full = "%s \u00b7 %s" % (words, names(where, 2))
    return full if len(full) <= LINE_MAX else words


def carrier_names(facts):
    here = facts["machine"]
    found = []
    for item in facts["no_carrier"]:
        found.append(item["name"] if item["on"] == here else "%s (%s)" % (item["name"],
                                                                           upper(item["on"])))
    for item in facts["no_repo"]:
        found.append(item["name"])
    return found


def primary(facts, now):
    """(state, words, head text, [optional parts as keep -> text])."""
    stale = [o for o in facts["others"] if o["heads"] and not o["fresh"]]
    brain = facts["brain"]
    differ = [d["name"] for d in facts["differ"]]
    owed = facts["owed"]
    parts = []

    def differ_part(keep):
        if not differ:
            return ""
        n = len(differ)
        head = "%d repo%s differ%s" % (n, "" if n == 1 else "s", "" if n != 1 else "s")
        return head + (": " + names(differ, keep) if keep > 0 else "")

    def owed_optional(keep):
        return ("owed: " + owed_part(owed, keep)) if owed else ""

    def brain_optional(keep):
        return ("brain: " + brain["why"]) if brain["state"] in ("failed", "conflicts") else ""

    if facts["unknown"]:
        return ("unknown", "unknown", "unknown · " + facts["unknown"],
                [owed_optional])
    if stale:
        worst = max(stale, key=lambda o: o["age_min"] if o["age_min"] is not None else 1e9)
        age = worst["age_min"]
        when = parse_iso(worst["as_of"])
        words = "behind %s" % span(age) if age is not None else "behind"
        head = "%s · the %s's heads are from %s" % (words, upper(worst["machine"]), clock(when, now))
        return ("behind", words, head, [differ_part, brain_optional, owed_optional])
    if differ:
        fresh = [o for o in facts["others"] if o["heads"]]
        latest = parse_iso(fresh[0]["as_of"]) if fresh else None
        head = "behind · the %s's heads are from %s" % (upper(fresh[0]["machine"]) if fresh else
                                                        "OTHER MACHINE", clock(latest, now))
        return ("behind", "behind", head, [differ_part, brain_optional, owed_optional])
    if brain["state"] in ("failed", "conflicts"):
        return ("behind", "behind", "behind · brain: " + brain["why"],
                [owed_optional])
    if brain["state"] in ("none", "stale"):
        return ("unknown", "unknown", "unknown · " + brain["why"], [owed_optional])
    if owed:
        return ("owed", "owed", None, [])
    n = len(facts["level"])
    head = "synced · brain level · %d repo%s level · read %s" % (n, "" if n == 1 else "s",
                                                                  clock(now, now))
    return ("synced", "synced", head, [])


def verdict(facts, now=None):
    """(state, words, line) — the line always under LINE_MAX + 1 characters. Every part starts as
    its bare count; optional parts that still do not fit are dropped from the end; then each part
    in turn takes back its names — the head first, then the repos that differ, then the carrier
    names, then the owed payloads — for as long as the line stays under the limit."""
    now = now or now_of(facts.get("read"))
    state, words, head, optional = primary(facts, now)
    repos = [n for n in carrier_names(facts) if n not in [f["name"] for f in facts["no_repo"]]]
    folders = [f["name"] for f in facts["no_repo"]]
    everything = repos + folders

    def carrier_part(keep):
        if not everything:
            return ""
        if keep > 0:
            return "no carrier: " + names(everything, keep)
        bits = []
        if repos:
            bits.append("%d repo%s" % (len(repos), "" if len(repos) == 1 else "s"))
        if folders:
            bits.append("%d folder%s" % (len(folders), "" if len(folders) == 1 else "s"))
        return "no carrier: " + ", ".join(bits)

    def head_part(keep):
        if head is not None:
            return head
        return "owed: " + owed_part(facts["owed"], keep)

    # The unreadable clause does not ride this line — it has its own second line
    # (second_line). The head, the optional parts and the carrier names keep the places and the
    # drop order they have without it.
    parts = [head_part] + list(optional) + [carrier_part]
    keeps = [0] * len(parts)

    def build():
        return " · ".join(b for b in (p(k) for p, k in zip(parts, keeps)) if b)

    while len(build()) > LINE_MAX and len(parts) > 2:
        del parts[-2]                                  # the last optional part goes first
        del keeps[-2]
    # the head, the first optional part (the repos that differ), the carrier names, the rest
    order = [0] + ([1] if len(parts) > 2 else []) + [len(parts) - 1] + \
        [i for i in range(2, len(parts) - 1)]
    for index in order:
        for keep in (1, 2, 3):
            before = keeps[index]
            keeps[index] = keep
            if len(build()) > LINE_MAX:
                keeps[index] = before
                break
    line = build()
    if len(line) > LINE_MAX:                           # the last resort keeps the verdict word
        line = line[:LINE_MAX - 1].rstrip() + "\u2026"
    return state, words, line


def long_lines(facts):
    """One line per thing behind the verdict — the detail on demand."""
    now = now_of(facts.get("read"))
    here = facts["machine"]
    out = []
    b = facts["brain"]
    out.append("  brain       %s · %s" % (b["state"], b["why"]))
    for o in facts["others"]:
        out.append("  %-11s %s · last beat %s · heads published %s%s"
                   % (upper(o["machine"]), "fresh" if o["fresh"] else "NOT fresh",
                      clock(parse_iso(o["beat"]), now) if o["beat"] else "never",
                      clock(parse_iso(o["published"]), now) if o["published"] else "never",
                      (" · %s old" % span(o["age_min"])) if o["age_min"] is not None else ""))
    out.append("  level       %d repo%s" % (len(facts["level"]), "" if len(facts["level"]) == 1 else "s"))
    for d in facts["differ"]:
        if "here" in d:
            out.append("  differ      %s · %s %s %s · %s %s %s · newer: %s (%s)%s · %s"
                       % (d["name"], upper(here), d["here"]["branch"], str(d["here"]["head"] or "")[:7],
                          upper(d["machine"]), d["there"]["branch"], str(d["there"]["head"] or "")[:7],
                          upper(d["newer"]) or "unknown", d["newer_why"],
                          " · different branches checked out" if d["branches"] == "different" else "",
                          d["carrier"]))
        else:
            out.append("  differ      %s · %s · %s %s · %s"
                       % (d["name"], d["why"], d["branch"], str(d["head"] or "")[:7], d["carrier"]))
    for d in facts["only_one_side"]:
        out.append("  one side    %s · only on the %s · github carries it; `buttonup.py arrive` "
                   "clones it on the other machine" % (d["name"], upper(d["on"])))
    for t in facts["same_head_elsewhere"]:
        out.append("  same head   %s on the %s · the same head %s sits in %s on the %s"
                   % (t["name"], upper(t["on"]), str(t["head"])[:7], t["twin"], upper(t["twin_on"])))
    if facts["not_carried"]:
        out.append("  not carried %s" % ", ".join("%s (%s)" % (n["name"], n["carrier"])
                                                  for n in facts["not_carried"]))
    for m in facts["modified"]:
        out.append("  modified    %s · %d tracked file%s on the %s"
                   % (m["name"], m["files"], "" if m["files"] == 1 else "s", upper(m["on"])))
    for h in facts["held"]:
        out.append("  held        %s on the %s · %s · owner: %s · next: %s"
                   % (h["project"], upper(h["on"]), h["reason"], h["owner"], h["next"]))
    for o in facts["owed"]:
        where = ("in the %s's outbox" % upper(o.get("at"))) if o.get("carrier") == "outbox" else \
                "on the drive"
        out.append("  owed        %s · %s · to the %s · %s:%s"
                   % (o["label"], where, upper(o.get("to")) or "?", o.get("file"), o.get("line")))
    out.append("  owed read   %s" % facts["owed_read"])
    for u in facts.get("unreadable") or []:
        out.append("  unreadable  %s:%s · %s · %s" % (u.get("file"), u.get("line"), u.get("why"),
                                                      u.get("text")))
    for n in facts["no_carrier"]:
        out.append("  no carrier  %s (%s) · %s · say: github | drive | stays-here · "
                   "`buttonup.py registry --set \"%s\" <word>`" % (n["name"], upper(n["on"]), n["why"],
                                                                   n["name"]))
    for n in facts["no_repo"]:
        riders = "; ".join("its %s ride with %s" % (", ".join(r["files"]) or "files", r["project"])
                           for r in n["loose_by"])
        out.append("  no repo     %s%s · %s · say: init | stays-here | ignore · "
                   "`buttonup.py registry --set \"%s\" <word>`"
                   % (n["name"], " (ruled init: the hub makes the repo)" if n["word"] == "init" else "",
                      riders or "nothing carries its files", n["name"]))
    return out


def result(hub, projects_root=None, engine_path=None, state_dir=None, now=None):
    now = now or now_of()
    facts = gather(hub, projects_root, engine_path, state_dir, now)
    state, words, line = verdict(facts, now)
    facts.update({"state": state, "words": words, "line": line})
    facts["line2"] = second_line(facts)                # what the line could not count
    return facts


def core_of(facts):
    """What makes a rewrite worth doing: everything the reader sees, without the moment it was
    read. `synced … · read 08:12` and `… · read 08:17` are one verdict."""
    if not isinstance(facts, dict):
        return None
    line = re.sub(r" · read \d\d:\d\d", "", str(facts.get("line") or ""))
    return json.dumps({"state": facts.get("state"), "line": line,
                       "differ": [d.get("name") for d in facts.get("differ") or []],
                       "owed": [o.get("label") for o in facts.get("owed") or []],
                       "unreadable": ["%s:%s" % (u.get("file"), u.get("line"))
                                      for u in facts.get("unreadable") or []],
                       "no_carrier": [(n.get("name"), n.get("on")) for n in facts.get("no_carrier") or []],
                       "no_repo": [(n.get("name"), n.get("word")) for n in facts.get("no_repo") or []],
                       "brain": (facts.get("brain") or {}).get("state")}, sort_keys=True)


def should_write(path, facts, now):
    """(write?, why) — a changed verdict, a missing or unreadable file, or one REFRESH_MINUTES old."""
    old = read_json(path)
    if not isinstance(old, dict):
        return True, "written"
    if core_of(old) != core_of(facts):
        return True, "rewritten (the verdict changed)"
    if "line2" not in old:                            # a file an older tool wrote has no
        return True, "rewritten (an older tool wrote it)"   # second line; carry it now, not in 30 min
    when = parse_iso(old.get("read"))
    if when is None or (now - when).total_seconds() / 60.0 >= REFRESH_MINUTES:
        return True, "rewritten (%d-minute refresh)" % REFRESH_MINUTES
    return False, "stands (unchanged since %s)" % clock(when, now)


def write_atomic(path, text):
    path = Path(path)
    temp = path.parent / (".%s.sync-verdict-%d" % (path.name, os.getpid()))
    with io.open(str(temp), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(str(temp), str(path))


def flag_value(argv, name):
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def default_hub():
    try:
        from exo_paths import paths                                 # noqa: E402
        found = paths(tool_file=__file__)["hub"]
        if found:
            return Path(found)
    except Exception:
        pass
    return HERE.parent


def main(argv):
    # the console's encoding is set HERE, never at import: buttonup.py and the wake screen load
    # this file as a module, and a cp1252 console of theirs must keep its own fallback (W6)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(__doc__)
        return 0
    i = 0
    while i < len(argv):
        if argv[i] not in KNOWN_FLAGS:
            sys.stderr.write("sync-verdict.py: unknown flag %r (see --help)\n" % argv[i])
            return 2
        if argv[i] in VALUED:
            if i + 1 >= len(argv):
                sys.stderr.write("sync-verdict.py: %s needs a value\n" % argv[i])
                return 2
            i += 2
        else:
            i += 1
    hub = Path(flag_value(argv, "--hub")) if flag_value(argv, "--hub") else default_hub()
    now = now_of(flag_value(argv, "--now"))
    facts = result(hub, flag_value(argv, "--projects"), flag_value(argv, "--engine"),
                   flag_value(argv, "--state-dir"), now)
    if "--write" in argv:
        target = hub / ("sync-verdict-%s.json" % facts["machine"])
        write_it, _why = should_write(target, facts, now)
        if write_it:
            write_atomic(target, json.dumps(facts, indent=1, ensure_ascii=False, sort_keys=True,
                                            default=str) + "\n")
    if "--json" in argv:
        print(json.dumps(facts, indent=1, ensure_ascii=False, sort_keys=True, default=str))
        return 0
    print(facts["line"])
    if facts.get("line2"):
        print(facts["line2"])                          # its own short line, only when something was skipped
    if "--long" in argv:
        for line in long_lines(facts):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
