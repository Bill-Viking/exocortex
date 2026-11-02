#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wake-screen.py — the first screen at a wake: where we left off.

    python3 tools/wake-screen.py            the WAKE SCREEN, for the hub's (and the Desk's) first reply
    python3 tools/wake-screen.py --json     the same facts, as data
    python3 tools/wake-screen.py --html     the same block as a dated strip for the top of tree.html
    python3 tools/wake-screen.py --limit N  how many lanes LAST WORKED shows (default 8)
    python3 tools/wake-screen.py --help     this text; nothing runs

WHAT IT PRINTS, in this order and nothing else:
  1  one receipts line   — the clock, this machine, the pulse's age and live count,
                           the USAGE words (tools/usage.py's own state line for THIS
                           window's login — `USAGE · <login> · Fable 9 % · all 6 % · read 3 min
                           ago`, or `refresh` in place of every percent; one copy, usage.py's),
                           and at its tail the ONE-LINE SYNC VERDICT — read from
                           sync-verdict-<machine>.json, which the pulse writes every beat; when that
                           file is missing or older than 15 minutes, tools/sync-verdict.py is asked
                           in place (read-only: the same code, never a second rule)
  2  LAST WORKED         — the eight lanes with the most recent LAST EXCHANGE, one line each in the
                           LIVE-list shape: state dot · lane · where we left off (<= 12 words) · the
                           open issue · next move · machine · when · ▶ OPEN (the window itself when
                           the app still holds it, else the lane's opener file). A stale opener is
                           flagged inline, first on its line. THE ISSUE IS THE LANE'S OWN: in a
                           folder with one opener, the project's first `!` item; in a folder with
                           several, the first `!` item whose text STARTS with the lane's own name
                           (its opener suffix or header lane — opener_carriers.names_lane), and a
                           `!` that names no lane is the project's, on no lane's line. The dot is
                           scoped the same way (collect-openers.state_of's `lane`).
  3  the hygiene line    — `N sessions to archive — say archive` from hygiene-archive-queue-<machine>.json,
                           counting only the items THIS window's login can archive: the app's own
                           store holds the session, under this login's account folder (the item's
                           `account` when it names one), and not already archived; an item the
                           store no longer holds is gone (silent at 0), and `N routines will ask permission — say routines` from the
                           app's own task store (silent at 0; companion on the same screen);
                           then `N ACT threads left in codex` (and `… in grok`) — counted
                           from the vendor's own store on this machine (Codex: the newest title per
                           thread in session_index.jsonl, for every rollout not in archived_sessions/;
                           Grok: each session's own title), never from an app's sidebar; and, for
                           each other machine whose last button-up counted any, the same line with
                           that machine's name and the time it was counted. Silent at 0.
                           Then `N repos with no carrier: … — say the word for each` and the
                           no-repo QUESTION, asked once: `N folders with no repo
                           — for each, say init · stays-here · ignore: <every folder>`, its hover
                           one `buttonup.py registry --set "<folder>" <word>` per folder; a folder
                           named once is said again only as `… and K more, ruled none` until a
                           word is recorded; a ruled `init` is owed until the repo exists. Silent
                           at 0.
                           Then, ALWAYS, the night check's last line:
                           `nothing can wake a Fable window tonight · …` or `CAN WAKE FABLE: … — <the
                           move>` — one line, read in place, writing nothing.
  4  the tree's plate    — the machine's mark on its own line, then the page's path alone in a fence

LAST EXCHANGE is the newest of three real bytes, and never a capture's write time:
  * the window's own last turn — the app's session store (`lastActivityAt`, tools/app_sessions.py)
    for every window whose ritual title names the lane, and the pulse's live-sessions files (every
    machine, every vendor) for a window seen in the last ten minutes;
  * the opener's `written:` — unless its `by:` says `captured by hub` (a capture ranks by the
    lane's last real turn, never by the moment the hub wrote its card);
  * STATUS.md's mtime — ONLY for a project with one lane: in a folder that holds several lanes the
    file is shared, so its mtime says the PROJECT moved, not which lane did.
A lane with none of the three is not ranked; it is not guessed.

Stdlib only, Python 3.9, macOS and Windows (cp1252-safe stdout). Every path from the machine
record the path resolver finds; git is asked only about the projects on the screen, in parallel,
so the screen stays under two seconds. It writes nothing — except `--inject <tree.html>`, the one
hook orchestrator.py calls after it draws the tree, which rewrites that one page's front-door strip,
and its own machine-local seen file, <home>/.exocortex/wake/no-repo-seen.json (never synced),
written only by the plain text run — the hub's first reply, where the no-repo question is asked.
"""
import html
import importlib.util
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMIT = 8
WHERE_WORDS = 12
STRIP_START = "<!-- front-door:start -->"
STRIP_END = "<!-- front-door:end -->"
CAPTURED = "captured by hub"
DOTS = {"green": "\U0001F7E2", "amber": "\U0001F7E1", "red": "\U0001F534", "none": "⚪"}
ASCII = {"\U0001F7E2": "[G]", "\U0001F7E1": "[A]", "\U0001F534": "[R]", "⚪": "[-]",
         "▶": ">", "·": "-", "—": "--", "…": "...", "✉": "mail",
         "⚠": "!", "●": "o", "▎": "|", "▌": "|", "≤": "<="}


# ── the tools this one stands on, beside it first and the hub's tools/ second ──

def _load(name, file_name):
    for cand in (HERE / file_name, HERE.parent / "tools" / file_name):
        if cand.is_file():
            spec = importlib.util.spec_from_file_location(name, str(cand))
            module = importlib.util.module_from_spec(spec)
            saved = sys.dont_write_bytecode
            errors = getattr(sys.stdout, "errors", None)
            sys.dont_write_bytecode = True
            try:
                spec.loader.exec_module(module)
            finally:
                sys.dont_write_bytecode = saved
                # a neighbour that reconfigures stdout at import (usage.py does) must not take
                # away emit()'s ASCII fallback on a cp1252 console
                if errors and getattr(sys.stdout, "errors", None) != errors:
                    try:
                        sys.stdout.reconfigure(errors=errors)
                    except Exception:
                        pass
            return module
    return None


sys.path.insert(0, str(HERE))
CO = _load("wake_collect_openers", "collect-openers.py")
AS = _load("wake_app_sessions", "app_sessions.py")
RC = _load("wake_routine_check", "routine-check.py")
BU = _load("wake_buttonup", "buttonup.py")          # the one reader of Codex's own store
GS = _load("wake_grok_sessions", "grok_sessions.py")
SV = _load("wake_sync_verdict", "sync-verdict.py")  # the one-line verdict's own reader
US = _load("wake_usage", "usage.py")                # the usage words, usage.py's one copy
NC = _load("wake_night_check", "night-check.py")    # the night check's last line
VERDICT_STALE_MIN = 15                              # three missed beats: the file is not "now"
SEEN_PARTS = (".exocortex", "wake", "no-repo-seen.json")   # machine-local, never synced
FOLDER_ASK = "init · stays-here · ignore"
SESSION_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,200}$")      # a store file name, never a path


def emit(text=""):
    """print() that survives a cp1252 console: marks fall back to ASCII, never a traceback."""
    try:
        sys.stdout.write(text + "\n")
        return
    except UnicodeEncodeError:
        pass
    safe = text
    for mark, plain in ASCII.items():
        safe = safe.replace(mark, plain)
    try:
        sys.stdout.write(safe + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(safe.encode("ascii", "replace").decode("ascii") + "\n")


def lane_key(text):
    """One spelling per lane: 'Exocortex hub', 'Exocortex/hub' and 'exocortex-hub' are one."""
    return re.sub(r"[\s/_\-]+", "/", str(text or "").strip().lower()).strip("/")


def title_lane(title):
    """The lane a ritual title names (`ACT — Garden/Docs: …` → `Garden/Docs`), or ''."""
    t = str(title or "")
    if "—" not in t or ":" not in t:
        return ""
    tok = t.split("—", 1)[1].split(":", 1)[0].strip()
    return tok if tok and len(tok) <= 60 else ""


def title_tag(title):
    head = str(title or "").split("—", 1)[0].strip().upper()
    return head if head in ("ACT", "ARCH", "HARV", "NEW", "DEL?") else ""


def read_json(path, default=None):
    """utf-8-sig: a file PowerShell wrote starts with a BOM, and a plain utf-8 read of it
    returns the default — an archive queue could count 0 that way."""
    try:
        with io.open(str(path), encoding="utf-8-sig") as fh:
            return json.load(fh)
    except Exception:
        return default


def parse_when(value):
    if CO is not None:
        stamp = CO.parse_iso(value)
        return stamp.timestamp() if stamp is not None else None
    return None


def ago(seconds):
    if seconds is None:
        return "?"
    s = max(0.0, seconds)
    if s < 90:
        return "just now"
    if s < 5400:
        return "%d min ago" % round(s / 60)
    if s < 129600:
        return "%d h ago" % round(s / 3600)
    return "%d d ago" % round(s / 86400)


def words(text, n):
    parts = str(text or "").split()
    return " ".join(parts[:n]) + ("…" if len(parts) > n else "")


# ── the record ────────────────────────────────────────────────────────────────

def machine_facts():
    """(name, roots dict of Paths, record) from the machine record the resolver finds."""
    roots = CO.machine_roots()
    record = read_json(CO.MACHINE_FILE, {}) or {}
    home = (record.get("roots") or {}).get("home") or os.path.expanduser("~")
    return str(roots["name"]).lower(), roots, record, home


def registry_bits(name):
    """(label, mark) for this machine from the person's registry — never a table written here."""
    try:
        rg = CO._rg
        record = CO.reg()
        return rg.machine_label(record, name) or name.upper(), rg.machine_mark(record, name) or ""
    except Exception:
        return name.upper(), ""


def machine_words():
    try:
        return [m.upper() for m in CO._rg.machine_names(CO.reg())]
    except Exception:
        return []



def live_jobs(hub, at):
    """The pulse's job rows, with the same thirty-minute freshness rail as the tree."""
    out = []
    for f in sorted(Path(hub).glob("live-sessions-*.json")):
        data = read_json(f, {}) or {}
        when = parse_when(data.get("when"))
        if not when or at - when > 1800:
            continue
        out.extend(s for s in data.get("sessions", []) if s.get("kind") == "job" and
                   (s.get("state") == "running" or (parse_when(s.get("ended")) and at - parse_when(s["ended"]) < 600)))
    return out


def job_words(job):
    from offload import job_line
    return job_line(job)


def live_turns(hub, at):
    """{lane key: (epoch, machine, title)} — every session the pulses see, every machine."""
    out = {}
    for f in sorted(Path(hub).glob("live-sessions-*.json")):
        d = read_json(f, None)
        if not isinstance(d, dict):
            continue
        mch = str(d.get("machine") or f.stem.split("-", 2)[-1]).upper()
        when = parse_when(d.get("when")) or at
        for s in d.get("sessions") or []:
            if not isinstance(s, dict):
                continue
            key = lane_key(title_lane(s.get("title")))
            if not key:
                continue
            try:
                t = when - float(s.get("minutes_ago") or 0.0) * 60.0
            except (TypeError, ValueError):
                continue
            if key not in out or t > out[key][0]:
                out[key] = (t, mch, s.get("title") or "")
    return out


def pulse_line(hub, name, at):
    d = read_json(Path(hub) / ("live-sessions-%s.json" % name), None)
    if not isinstance(d, dict):
        return "no pulse yet"
    when = parse_when(d.get("when"))
    live = len([s for s in (d.get("sessions") or []) if isinstance(s, dict)])
    return "pulse %s · %d live here" % (ago(at - when) if when else "?", live)


def letters_waiting(hub, name):
    d = read_json(Path(hub) / ("post-%s.json" % name), None)
    if not isinstance(d, dict):
        return None
    return sum(1 for e in (d.get("letters") or {}).values()
               if isinstance(e, dict) and e.get("state") == "waiting" and not e.get("parent"))


def account8(value):
    """An account id as it is kept: its first eight characters, lowercase (usage.py's form)."""
    if US is not None and hasattr(US, "account8"):
        return US.account8(value)
    s = str(value or "").strip().lower()
    return "" if (not s or "/" in s or "\\" in s) else s[:8]


def store_record(home, session_id):
    """(account8 of the folder the app keeps it under, archived?) — the app's own record of this
    window, from its session store (<store>/<account>/<org>/<sessionId>.json, the folders
    app_sessions.store_dirs names); None when the store holds no record of it: it is gone."""
    sid = str(session_id or "").strip()
    if AS is None or not SESSION_ID.match(sid) or sid in (".", ".."):
        return None
    name = sid if sid.endswith(".json") else sid + ".json"
    for folder in AS.store_dirs(home):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            rec = read_json(path, None)
            if not isinstance(rec, dict):
                return None
            return account8(os.path.basename(os.path.dirname(folder))), bool(rec.get("isArchived"))
    return None


def archive_count(hub, name, home=None, account=""):
    """How many queued sessions THIS window's login can archive now: the app's store holds the
    session, it is not archived, and it is this login's — the item's own `account` when it names
    one (archive-receipts.py --account, written by the watcher), else the account folder the store
    keeps it under. `account` '' (no login readable here): every live one, whoever's."""
    d = read_json(Path(hub) / ("hygiene-archive-queue-%s.json" % name), None)
    if not isinstance(d, dict):
        return 0
    if str(d.get("vendor") or "claude").strip().lower() != "claude":
        # the Codex twin's queue (its thread UUIDs): the Claude app's store cannot answer for it
        # and it names no login — counted whole, the rule as it was
        return len([i for i in (d.get("items") or []) if i])
    default = account8(d.get("account"))
    count = 0
    for item in d.get("items") or []:
        if not isinstance(item, dict):
            continue
        rec = store_record(home, item.get("sessionId") or item.get("session"))
        if rec is None or rec[1]:
            continue                      # gone from the store, or already archived
        owner = account8(item.get("account")) or default or rec[0]
        if account and owner != account8(account):
            continue                      # another login's window: not this one's to archive
        count += 1
    return count


def routines_unset(home):
    """[names] of ENABLED routines whose task carries no permission mode (they will prompt),
    read from the app's own task store by routine-check.py's reader; [] when none or unreadable."""
    if RC is None:
        return []
    try:
        stores = RC.find_store_in(home)
        live = RC.active_store(stores) if hasattr(RC, "active_store") else None
        return [t["name"] for t in RC.unset_tasks([live] if live else stores)]
    except Exception:
        return []


def codex_act_left(record, home):
    """(count, titles) of Codex threads titled ACT on THIS machine — the newest title per thread
    in Codex's own index, for every rollout still under sessions/ (an archived thread's rollout is
    in archived_sessions/). Read through buttonup.py's reader, the one copy; (0, []) without it."""
    if BU is None:
        return 0, []
    try:
        root = Path((record.get("roots") or {}).get("codex") or Path(home) / ".codex")
        index, _n = BU.codex_index(root)
        titles = sorted((index.get(ident) or {}).get("title") or ""
                        for ident in BU.codex_rollouts(root))
        act = [t for t in titles if BU.title_tag(t) == "ACT"]
        return len(act), act
    except Exception:
        return 0, []


def grok_title(item):
    """A Grok session's own name: a manual /rename (`title`) first, else the generated one."""
    try:
        with io.open(str(item.get("path") or ""), encoding="utf-8-sig") as fh:
            body = json.loads(fh.read(512 * 1024))
        return str(body.get("title") or body.get("generated_title") or
                   body.get("session_summary") or "").strip()
    except Exception:
        return str(item.get("title") or "").strip()


def grok_act_left(record, home):
    if GS is None:
        return 0, []
    try:
        root = Path((record.get("roots") or {}).get("grok") or Path(home) / ".grok")
        act = []
        for item in GS.iter_sessions(root):
            if item.get("is_subagent"):
                continue
            title = grok_title(item)
            if title_tag(title) == "ACT":
                act.append(title)
        return len(act), sorted(act)
    except Exception:
        return 0, []


def others_codex_left(hub, name):
    """[(MACHINE, count, when)] — the ACT count each OTHER machine's last button-up published in
    its book (buttonup-state-<machine>.json, brain-synced). The other machine's store cannot be
    read from here; its own count, with the time it was taken, can."""
    out = []
    for path in sorted(Path(hub).glob("buttonup-state-*.json")):
        mch = path.stem[len("buttonup-state-"):]
        if not mch or mch == name or mch.endswith(".prev"):
            continue
        body = read_json(path, None)
        facts = ((body or {}).get("report") or {}).get("codex_close") if isinstance(body, dict) else None
        if not isinstance(facts, dict):
            continue
        try:
            left = int(facts.get("act_left") or 0)
        except (TypeError, ValueError):
            continue
        if left > 0:
            out.append((mch.upper(), left, parse_when(facts.get("when"))))
    return out


def sync_verdict(hub, name, at):
    """The verdict the pulse wrote this beat (sync-verdict-<machine>.json), or — when that file
    is missing or older than VERDICT_STALE_MIN — the same tool asked in place, writing nothing.
    None when neither is here; the screen then says nothing about sync."""
    body = read_json(Path(hub) / ("sync-verdict-%s.json" % name), None)
    if isinstance(body, dict) and body.get("line"):
        when = parse_when(body.get("read"))
        if when is not None and (at - when) <= VERDICT_STALE_MIN * 60:
            return body
    if SV is None:
        return body if isinstance(body, dict) and body.get("line") else None
    try:
        return SV.result(Path(hub))
    except Exception:
        return body if isinstance(body, dict) and body.get("line") else None


def window_login(record, home, hub):
    """(login, how, account) of THIS window — usage.session_login, read ONCE per screen for
    the usage words and the archive count; None when usage.py is not here or it failed."""
    if US is None or not hasattr(US, "session_login"):
        return None
    try:
        roots = dict((record.get("roots") or {}))
        roots.setdefault("home", home)
        got = tuple(US.session_login(roots, str(hub),
                                     session=os.environ.get("CLAUDE_CODE_SESSION_ID"),
                                     fallback=True))
        return (got + ("", "", ""))[:3]
    except Exception:
        return None


def login_account(who):
    """The account the archive count is this login's by: the window's own, else the app's
    config — never the terminal cli's config, which can name another login."""
    if not who or not who[2]:
        return ""
    how = str(who[1] or "")
    word = US.source_word(how) if (US is not None and hasattr(US, "source_word")) else ""
    return "" if (word == "cli" or how.startswith("cli")) else account8(who[2])


def usage_words(record, home, hub, who=None):
    """the receipts' USAGE words — usage.py's own state line for THIS window's login
    (its transcript's owner, found by the id the environment gives, else the app's signed-in
    login); '' when usage.py is not here. Reads only."""
    if US is None or not hasattr(US, "receipt_line"):
        return ""
    try:
        if who is None:
            who = window_login(record, home, hub)
        if who is None:
            return ""
        return US.receipt_line(str(hub), "claude", login=who[0])
    except Exception:
        return ""


def night_facts():
    """(the night check's last line, its whole list) — read in place, writing nothing;
    a line that says so when the tool is not beside this one."""
    if NC is None:
        return "night check: tools/night-check.py is not here — nothing is ruled out", []
    try:
        res = NC.check(NC.record([]), datetime.now().astimezone())
        return res["last"], [i["words"] for i in res["items"]] + list(res["cannot_see"])
    except Exception as exc:
        return "night check: it could not finish (%r) — nothing is ruled out" % (exc,), []


def carrier_line(d):
    """`N repos with no carrier: …` — silent at 0. The folders are the no-repo
    question's (folder_lines), never this line's."""
    v = d.get("sync") or {}
    here = str(v.get("machine") or "").lower()
    repos = ["%s%s" % (n.get("name"), "" if str(n.get("on") or "").lower() == here
                       else " (%s)" % str(n.get("on") or "").upper())
             for n in v.get("no_carrier") or [] if isinstance(n, dict)]
    if not repos:
        return "", []
    return ("%d repo%s with no carrier: %s" % (len(repos), "" if len(repos) == 1 else "s",
                                               short_list(repos))), repos


def short_list(items, keep=4):
    return ", ".join(items[:keep]) + (" +%d" % (len(items) - keep) if len(items) > keep else "")


# ── the no-repo question, asked once ─────────────────────

def seen_path(home):
    return Path(home or os.path.expanduser("~")).joinpath(*SEEN_PARTS)


def no_repo_facts(v, home):
    """{ask, new, noted, owed}: the folders with no repo and no word (`ask`, split by whether
    this machine's seen file has named them before) and the folders ruled `init` whose repo is
    still owed. From the verdict's own no_repo list — never a second rule."""
    rows = [n for n in (v or {}).get("no_repo") or [] if isinstance(n, dict) and n.get("name")]
    ask = sorted((str(n["name"]) for n in rows if not n.get("word")), key=str.lower)
    owed = sorted((str(n["name"]) for n in rows if n.get("word") == "init"), key=str.lower)
    body = read_json(seen_path(home), None)
    seen = (body or {}).get("folders") if isinstance(body, dict) else None
    seen = seen if isinstance(seen, dict) else {}
    return {"ask": ask, "new": [f for f in ask if f not in seen],
            "noted": [f for f in ask if f in seen], "owed": owed}


def folder_command(folder, word="init|stays-here|ignore"):
    return '%s tools/buttonup.py registry --set "%s" %s' % (
        "python" if os.name == "nt" else "python3", folder, word)


def folder_lines(d):
    """[(line, hover)] — the question, with every folder it asks about, the first time each is
    seen; afterwards `… and K more, ruled none` until a word is recorded; then the owed ones."""
    f = d.get("folders") or {}
    out = []
    ask, new, noted, owed = f.get("ask") or [], f.get("new") or [], f.get("noted") or [], f.get("owed") or []
    if ask:
        head = "%d folder%s with no repo" % (len(ask), "" if len(ask) == 1 else "s")
        if new:
            named = ", ".join(new) + (" … and %d more, ruled none" % len(noted) if noted else "")
            line = "%s — for each, say %s: %s" % (head, FOLDER_ASK, named)
        else:
            line = "%s, ruled none — for each, say %s" % (head, FOLDER_ASK)
        out.append((line, "; ".join(folder_command(x) for x in ask)))
    if owed:
        out.append(("%d folder%s owe%s a repo (init said): %s"
                    % (len(owed), "" if len(owed) == 1 else "s", "s" if len(owed) == 1 else "",
                       ", ".join(owed)),
                    "the hub makes each a repo and seeds its carrier"))
    return out


def note_seen(home, folders, at=None):
    """The plain text run's one write: every folder the question named, `new` the first time
    and `noted` after; a folder that left the question (a word recorded) leaves the file.
    Machine-local, never synced; written whole (temp file, then replace); never raises."""
    try:
        ask = list((folders or {}).get("ask") or [])
        path = seen_path(home)
        body = read_json(path, None)
        old = (body or {}).get("folders") if isinstance(body, dict) else None
        old = old if isinstance(old, dict) else {}
        stamp = datetime.fromtimestamp(at or time.time()).astimezone().isoformat(timespec="seconds")
        now = {}
        for name in ask:
            was = old.get(name) if isinstance(old.get(name), dict) else None
            now[name] = ({"first": was.get("first") or stamp, "state": "noted"} if was
                         else {"first": stamp, "state": "new"})
        if now == old and isinstance(body, dict):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(".%s.%d.tmp" % (path.name, os.getpid()))
        with io.open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"written": stamp, "folders": now}, indent=1, ensure_ascii=False) + "\n")
        os.replace(str(tmp), str(path))
    except Exception:
        return


# ── the lanes ─────────────────────────────────────────────────────────────────

def gather(roots, home, at):
    """Every lane with an opener, and every ACT window whose lane has none — each with its
    last-exchange time and the evidence for it. Files only; no git."""
    found, projects_root, _m = CO.project_roots()
    carried = CO.carrier_index(projects_root)
    lanes, seen_real = {}, set()
    for name, path, is_hub in found:
        try:
            real = os.path.realpath(str(path))
        except OSError:
            real = str(path)
        if real in seen_real:
            continue                      # one folder under two names is one project
        seen_real.add(real)
        status = CO.read_status(path)
        openers = CO.find_openers(path)
        for opath, suffix in openers:
            parsed = CO.parse_opener(opath)
            header = parsed["header"]
            lane = CO.plain(header.get("lane") or ("%s/%s" % (name, suffix) if suffix else name))
            key = lane_key(lane)
            if key in lanes:
                continue
            by = str(header.get("by") or "")
            captured = CAPTURED in by.lower()
            ev = {}
            w = parse_when(header.get("written"))
            if w is not None and not captured:
                ev["opener"] = w
            if status is not None and len(openers) == 1:
                mt = status["mtime"]
                if not (captured and w is not None and abs(mt - w) < 900):
                    ev["status"] = mt          # a capture's own STATUS write is not an exchange
            lanes[key] = {"lane": lane, "project": name, "path": path, "is_hub": is_hub,
                          "suffix": suffix, "file": opath.name, "parsed": parsed,
                          "status": status, "captured": captured, "ev": ev,
                          "shared": len(openers) > 1,     # one STATUS, several lanes
                          "window": None, "window_machine": ""}
    return lanes, carried


def add_windows(lanes, hub, home, name, at):
    """The windows' own last turns: the app's store (this machine) and every pulse file."""
    recs = AS.records(home, max_age_days=21.0, at=at) if AS is not None else []
    here = name.upper()
    for r in recs:
        if r["scheduled"]:
            continue
        lane = title_lane(r["title"])
        key = lane_key(lane)
        if not key:
            continue
        row = lanes.get(key)
        if row is None:
            if title_tag(r["title"]) != "ACT" or r["archived"]:
                continue                  # only a LIVE window with no opener earns a line
            row = lanes[key] = {"lane": lane, "project": "", "path": None, "is_hub": False,
                                "suffix": "", "file": "", "parsed": None, "status": None,
                                "captured": False, "ev": {}, "window": None,
                                "window_machine": ""}
        if r["last_activity"] is not None:
            if r["last_activity"] > row["ev"].get("turn", 0):
                row["ev"]["turn"] = r["last_activity"]
                row["turn_machine"] = here
        if not r["archived"] and title_tag(r["title"]) in ("ACT", "NEW"):
            if row["window"] is None or (r["last_activity"] or 0) > (row["window"]["last_activity"] or 0):
                row["window"] = r
                row["window_machine"] = here
    for key, (t, mch, _title) in live_turns(hub, at).items():
        row = lanes.get(key)
        if row is not None and t > row["ev"].get("turn", 0):
            row["ev"]["turn"] = t
            row["turn_machine"] = mch
    for row in lanes.values():
        row["last"] = max(row["ev"].values()) if row["ev"] else None
        row["last_from"] = (max(row["ev"], key=row["ev"].get) if row["ev"] else "")


def light_facts(root):
    """Only the git facts the dot and the opener's freshness need — never the history walks."""
    facts = {"is_repo": (Path(root) / ".git").exists(), "head": "", "head_full": "",
             "branch": "", "dirty": 0, "ahead": 0, "has_remote": False}
    if not facts["is_repo"]:
        return facts
    facts["head_full"] = CO.git_text(root, ["rev-parse", "HEAD"])
    facts["head"] = facts["head_full"][:7]
    code, out = CO.git(root, ["status", "--porcelain", "--untracked-files=no"])
    if code == 0:
        facts["dirty"] = len([l for l in out.splitlines() if l.strip()])
    count = CO.git_text(root, ["rev-list", "--count", "@{upstream}..HEAD"])
    if count.isdigit():
        facts["ahead"] = int(count)
    facts["has_remote"] = bool(CO.git_text(root, ["remote"]).split())
    return facts


def machine_of(row, here):
    header = (row["parsed"] or {}).get("header") or {}
    text = " %s " % str(header.get("open_in") or "").upper()
    hits = [m for m in machine_words() if re.search(r"\b%s\b" % re.escape(m), text)]
    if len(hits) == 1:
        return hits[0]
    on = str(header.get("on") or "").strip().upper()
    if on == "HERE":
        return here
    if row.get("window") is not None:
        return row["window_machine"] or here
    return on or row.get("turn_machine") or here


def finish(row, facts, carried, here):
    """The line's words, from the collector's own rules — the dot, the freshness, the move."""
    status, parsed = row["status"], row["parsed"]
    out = {"lane": row["lane"], "project": row["project"], "last": row["last"],
           "last_from": row["last_from"], "machine": machine_of(row, here),
           "file": row["file"], "path": str(row["path"]) if row["path"] else "",
           "window": row["window"]["local_id"] if row.get("window") else "",
           "window_title": row["window"]["title"] if row.get("window") else "",
           "captured": row["captured"], "fresh": "none", "stale": "", "state": "none",
           "where": "", "issue": "", "next": ""}
    if parsed is None:
        out["where"] = words(title_rest(out["window_title"]), WHERE_WORDS) or "a live window, no opener yet"
        out["next"] = "its window holds the lane"
        return out
    folder, others = None, []
    if CO.carriers is not None:
        folder = CO.carriers.candidate("folder", parsed.get("raw") or "", file=row["file"],
                                       project=row["project"], parse=CO.parse_iso)
        others = CO.carriers.candidates_for(carried, row["project"], row["suffix"],
                                            parsed["header"].get("lane"), row["file"])
    entry = CO.opener_entry(row["path"], row["project"], row["suffix"], row["file"], parsed,
                            folder, others, status, facts)
    names = lane_names(row, entry)
    try:
        color, _reasons = CO.state_of(facts, status, [entry], True, lane=names)
    except TypeError:                 # a collector from before the lane scoping
        color, _reasons = CO.state_of(facts, status, [entry], True)
    out["state"] = color
    out["fresh"] = entry["fresh"]
    if entry["fresh"] == "stale":
        out["stale"] = "STALE OPENER — %s" % ((entry["notes"] or ["not in this repo's history"])[0])
    elif entry.get("carrier_flag"):
        out["stale"] = "STALE-BEHIND-CARRIER — %s" % entry["carrier_flag"]
    header = entry["header"]
    where = CO.plain(header.get("where") or "") or (CO.debracket(status["now_first"]) if status else "")
    out["where"] = words(where, WHERE_WORDS) or "—"
    move = CO.next_move(status)
    if CO.carriers is not None:
        todos = status["todos"] if status else []
        try:
            move, _from = CO.carriers.lane_next_move(entry["body"], row["suffix"] or "", todos,
                                                      move, cut=CO.cut, debracket=CO.debracket,
                                                      lane=row["lane"])
        except TypeError:             # an opener_carriers from before the lane word
            move, _from = CO.carriers.lane_next_move(entry["body"], row["suffix"] or "", todos,
                                                      move, cut=CO.cut, debracket=CO.debracket)
    out["next"] = words(move, 12)
    if status:
        urgent = [t for t in status["todos"] if t["urgent"]]
        if names:                     # several lanes share this STATUS: only this lane's own `!`
            owns = getattr(CO.carriers, "names_lane", None) if CO.carriers is not None else None
            urgent = [t for t in urgent if owns is not None and owns(t["text"], *names)]
        if urgent:
            issue = words(CO.debracket(urgent[0]["text"]), 10)
            # said once: when the next move IS the urgent item, the line does not repeat it
            if lane_key(issue[:30].rstrip("\u2026")) != lane_key(out["next"][:30].rstrip("\u2026")):
                out["issue"] = issue
    return out


def lane_names(row, entry):
    """The lane's own names — its opener suffix and its header lane — when the lane SHARES its
    folder's STATUS with other lanes; () for a folder with one opener, whose every `!` is the
    lane's (the rule as it always was)."""
    if not row.get("shared"):
        return ()
    lane = CO.plain((entry.get("header") or {}).get("lane") or row["lane"])
    return tuple(n for n in (row.get("suffix") or "", lane) if n)


def title_rest(title):
    t = str(title or "")
    return t.split(":", 1)[1].strip() if ":" in t else t


def screen(limit=LIMIT, at=None):
    """Every fact the screen prints, as one dict."""
    at = at if at is not None else time.time()
    name, roots, record, home = machine_facts()
    hub = roots["orchestrator"]
    lanes, carried = gather(roots, home, at)
    add_windows(lanes, hub, home, name, at)
    ranked = sorted((r for r in lanes.values() if r["last"] is not None),
                    key=lambda r: (-r["last"], r["lane"].lower()))[:limit]
    here = name.upper()
    repos = sorted({str(r["path"]) for r in ranked if r["path"] is not None})
    with ThreadPoolExecutor(max_workers=max(1, min(8, len(repos)))) as pool:
        facts = dict(zip(repos, pool.map(light_facts, repos)))
    blank = {"is_repo": False, "head": "", "head_full": "", "branch": "", "dirty": 0,
             "ahead": 0, "has_remote": False}
    rows = [finish(r, facts.get(str(r["path"]), blank), carried, here) for r in ranked]
    label, mark = registry_bits(name)
    night, night_list = night_facts()
    codex_left, codex_titles = codex_act_left(record, home)
    grok_left, grok_titles = grok_act_left(record, home)
    who = window_login(record, home, hub)          # once: the usage words and the archive count
    account = login_account(who)
    verdict = sync_verdict(hub, name, at)
    return {"generated": datetime.fromtimestamp(at).astimezone().isoformat(timespec="seconds"),
            "machine": here, "label": label, "mark": mark,
            "pulse": pulse_line(hub, name, at), "letters": letters_waiting(hub, name),
            "lanes_known": len(lanes), "rows": rows, "jobs": live_jobs(hub, at),
            "archive": archive_count(hub, name, home, account), "archive_account": account,
            "routines": routines_unset(home),
            "codex_left": codex_left, "codex_titles": codex_titles,
            "grok_left": grok_left, "grok_titles": grok_titles,
            "others_left": others_codex_left(hub, name),
            "sync": verdict, "folders": no_repo_facts(verdict, home), "home": home,
            "usage": usage_words(record, home, hub, who) if who is not None else "",
            "night": night, "night_list": night_list,
            "tree": str(Path(hub) / "tree.html"), "at": at}


# ── the two renderings ────────────────────────────────────────────────────────

def receipts(d):
    stamp = datetime.fromtimestamp(d["at"]).astimezone()
    parts = ["WAKE", stamp.strftime("%a %Y-%m-%d %H:%M"), d["machine"], d["pulse"]]
    # The letters count stays in the record (d["letters"]) and never rides the receipts line:
    # A count of mail hides its consequence; the body carries the useful result.
    # The hub reads its letters and the body carries the one consequence sentence, or nothing.
    parts.append("%d lanes read" % d["lanes_known"])
    if d.get("usage"):
        parts.append(d["usage"])                     # usage.py's own words, one copy
    if (d.get("sync") or {}).get("line"):
        parts.append(d["sync"]["line"])              # the verdict rides the receipts' tail
    return " · ".join(parts)


def second_line(d):
    """The verdict's SECOND line (what its ledger reader could not count), or '' — an
    older verdict body has no `line2`, and a clean record has an empty one."""
    return str((d.get("sync") or {}).get("line2") or "")


def line_parts(r, at):
    head = []
    if r["stale"]:
        head.append("⚠ " + r["stale"])
    body = [DOTS.get(r["state"], DOTS["none"]) + " " + r["lane"], r["where"]]
    if r["issue"]:
        body.append("! " + r["issue"])
    body.append("next: " + (r["next"] or "—"))
    body.append("%s · %s" % (r["machine"], ago(at - r["last"])))
    return head, body


def open_text(r, chat=True):
    if r["window"]:
        return "▶ [OPEN](#%s)" % r["window"] if chat else "▶ OPEN %s" % r["window"]
    if r["file"]:
        return "▶ OPEN %s" % r["file"]
    return "▶ OPEN"


def left_line(count, vendor, machine="", when=None):
    line = "%d ACT thread%s left in %s" % (count, "" if count == 1 else "s", vendor)
    if machine:
        line += " on the %s · counted at its button-up %s" % (
            machine, datetime.fromtimestamp(when).strftime("%a %H:%M") if when else "(time unread)")
    return line


def hygiene_lines(d):
    out = []
    if d["archive"]:
        out.append("%d session%s to archive — say archive"
                   % (d["archive"], "" if d["archive"] == 1 else "s"))
    if d["routines"]:
        out.append("%d routine%s will ask permission: %s — say routines"
                   % (len(d["routines"]), "" if len(d["routines"]) == 1 else "s",
                      ", ".join(d["routines"])))
    if d.get("codex_left"):
        out.append(left_line(d["codex_left"], "codex"))
    if d.get("grok_left"):
        out.append(left_line(d["grok_left"], "grok"))
    for machine, count, when in d.get("others_left") or []:
        out.append(left_line(count, "codex", machine, when))
    line, _all = carrier_line(d)
    if line:
        out.append(line + " — say the word for each")
    out.extend(line for line, _hover in folder_lines(d))
    return out


def hygiene_hovers(d):
    """{line: what it counts} — so every hygiene mark on the strip answers a hover with its titles."""
    out = {}
    if d.get("codex_left"):
        out[left_line(d["codex_left"], "codex")] = "; ".join(d.get("codex_titles") or [])
    if d.get("grok_left"):
        out[left_line(d["grok_left"], "grok")] = "; ".join(d.get("grok_titles") or [])
    line, every = carrier_line(d)
    if line:
        out[line + " — say the word for each"] = (
            "; ".join(every) + " · for each: `buttonup.py registry --set <name> github|drive|"
            "stays-here`")
    for line, hover in folder_lines(d):
        out[line] = hover
    return out


def text_lines(d):
    out = [receipts(d)]
    if second_line(d):
        out.append(second_line(d))                   # its own line, right under the receipts
    if d.get("jobs"):
        out.extend(["", "LIVE"])
        out.extend(job_words(j) for j in d["jobs"])
    out.extend(["", "LAST WORKED"])
    if not d["rows"]:
        out.append("nothing ranked yet — no lane has an opener, a window or a STATUS here")
    for r in d["rows"]:
        head, body = line_parts(r, d["at"])
        out.append(" — ".join(head + body) + " — " + open_text(r))
    extra = hygiene_lines(d)
    if d.get("night"):
        extra = extra + [d["night"]]                 # always, under the hygiene line
    if extra:
        out.append("")
        out.extend(extra)
    out.append("")
    out.append(d["mark"] + " " + d["label"] if d["mark"] else d["label"])
    out.append("```")
    out.append(d["tree"])
    out.append("```")
    return out


def html_strip(d):
    """The same block, dated, for the top of tree.html. Every line says where its words came
    from on hover — the opener file, the window, the queue — so no mark is without an answer."""
    e = html.escape
    stamp = datetime.fromtimestamp(d["at"]).astimezone().strftime("%a %Y-%m-%d %H:%M")
    items = []
    for r in d["rows"]:
        head, body = line_parts(r, d["at"])
        src = "; ".join(x for x in (
            ("opener %s in %s" % (r["file"], r["path"])) if r["file"] else "",
            ("window %s «%s»" % (r["window"], r["window_title"])) if r["window"] else "",
            "last exchange from %s" % {"turn": "the window's own last turn",
                                       "opener": "the opener's written: line",
                                       "status": "STATUS.md's mtime"}.get(r["last_from"], "?"))
            if x)
        items.append("<li title=\"%s\">%s%s <span class=\"fdo\">%s</span></li>"
                     % (e(src), ("<b class=\"fdw\">%s</b> — " % e(" ".join(head))) if head else "",
                        e(" — ".join(body)), e(open_text(r, chat=False))))
    for job in d.get("jobs", []):
        color = "var(--amber-ink,#ffb000)" if job.get("state") == "running" else "inherit"
        items.append('<li><a style="color:%s" href="%s" title="Full record on the job machine">%s</a></li>' %
                     (color, e(job.get("show_uri") or "", quote=True), e(job_words(job))))
    hovers = hygiene_hovers(d)
    lines = hygiene_lines(d)
    if d.get("night"):                               # the night line, its list on hover
        lines = lines + [d["night"]]
        hovers[d["night"]] = "; ".join(d.get("night_list") or []) + " · tools/night-check.py"
    extra = "".join("<li class=\"fdh\"%s>%s</li>"
                    % ((" title=\"%s\"" % e(hovers[x])) if hovers.get(x) else "", e(x))
                    for x in lines)
    second = ("<div class=\"fdr2\" title=\"tools/sync-verdict.py, line2\">%s</div>"
              % e(second_line(d))) if second_line(d) else ""      # the second line
    return ("%s\n<section class=\"frontdoor\" aria-label=\"Where we left off\" "
            "style=\"font:12px/1.5 ui-monospace,Menlo,Consolas,monospace;padding:8px 16px;"
            "border-bottom:1px solid rgba(128,128,128,.35)\">"
            "<div class=\"fdr\" title=\"tools/wake-screen.py, drawn %s\">%s</div>%s"
            "<div style=\"opacity:.7;margin-top:4px\">LAST WORKED · %s</div>"
            "<ol style=\"margin:2px 0 0 18px;padding:0\">%s%s</ol></section>\n%s"
            % (STRIP_START, e(d["generated"]), e(receipts(d)), second, e(stamp), "".join(items), extra,
               STRIP_END))


def inject(tree_path, limit=LIMIT):
    """The one hook orchestrator.py calls after drawing the tree: the strip replaces the
    previous one, right after <body>. A page without a <body> tag is left exactly as it was.
    Returns True when the page was rewritten. Never raises."""
    try:
        path = Path(tree_path)
        page = path.read_text(encoding="utf-8")
        page = re.sub(re.escape(STRIP_START) + r".*?" + re.escape(STRIP_END) + r"\n?", "",
                      page, flags=re.S)
        hit = re.search(r"<body[^>]*>", page)
        if hit is None:
            return False
        strip = html_strip(screen(limit))
        page = page[:hit.end()] + "\n" + strip + "\n" + page[hit.end():]
        path.write_text(page, encoding="utf-8")
        return True
    except Exception:
        return False


def main(argv):
    if "--help" in argv or "-h" in argv:
        emit(__doc__)
        return 0
    if CO is None:
        emit("wake-screen: tools/collect-openers.py is not beside this file or in the hub's "
             "tools/ — nothing to read the lanes with")
        return 1
    limit = LIMIT
    if "--limit" in argv:
        try:
            limit = max(1, int(argv[argv.index("--limit") + 1]))
        except (IndexError, ValueError):
            emit("wake-screen: --limit wants a number")
            return 2
    if "--inject" in argv:
        i = argv.index("--inject")
        target = argv[i + 1] if i + 1 < len(argv) else ""
        ok = inject(target, limit) if target else False
        emit("front-door strip %s" % ("written into %s" % target if ok else "not written"))
        return 0 if ok else 1
    d = screen(limit)
    if "--json" in argv:
        emit(json.dumps(d, indent=1, ensure_ascii=True, default=str))
        return 0
    if "--html" in argv:
        emit(html_strip(d))
        return 0
    for line in text_lines(d):
        emit(line)
    note_seen(d.get("home"), d.get("folders"), d.get("at"))   # the question was asked: once
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
