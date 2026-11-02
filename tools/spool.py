#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spool.py — the SPOOL road: hand a lane's prompts, start a window on the user's word,
dial every window.

    python3 tools/spool.py <lane> [<lane> ...] --ask   ASK — the one question first: START MODE (a window) or MANUAL MODE (the prompt)?
    python3 tools/spool.py <lane> [<lane> ...]    PROMPTS — one step per lane (the answer «prompt»)
    python3 tools/spool.py --all                  one step per active lane, ungated first
    python3 tools/spool.py <lane> --start         START — on the answer «window», or his word
    python3 tools/spool.py <lane> --successor --retiring "<title>"   SUCCESSOR — the next sitting,
                                                  started by the retiring window
    python3 tools/spool.py --dials                the dial pass over this machine's live windows
    python3 tools/spool.py --dials --plates-only  the postman's judge: plates only, never a walk
    common: [--json] [--login LOGIN] [--max-age MINUTES] [--project NAME] [--self SESSION_ID]

On Windows the same, as `python tools\\spool.py ...`.

THE STEP, in this order and nothing dense above it (the Both-doors, Run-here-mark and
Prompt-with-its-place laws): the ribbon · the SET line with the live meter · the terminal mark
and its one-shot launch line · the chat-box mark and the same sentence · the gate line when the
lane is gated · DONE WHEN · then the footer facts, one line each.

WHERE EVERYTHING COMES FROM — nothing about one fleet is written in this file (Universality):
  the roots         exo_paths.py: the machine record (projects, hub, this machine's name)
  the person        exo_registry.py: registry.json — the machines and their labels, the minds,
                    a mind's `cli` word and `app_id`, the `surfaces` marks. Where the registry
                    is silent the tool says so in one line and reads the model id the record
                    itself shows (the meter's own tally, the pulse's live sessions)
  the openers       collect-openers.py, imported and never copied: collect(), its FRESH / NOTE
                    / STALE verdict, its three carriers (opener_carriers.py), its ACT-title and
                    launch-sentence rules, its git helper
  the meter         usage.py, imported: this window's own login, that login's newest meter, the
                    warn line from the user's settings
  the dials         effort.py, imported: the user's rubric (effort-rubric.json — the judgment
                    row's minds in order, the level words), the transcript tail, the plates, the
                    judgment-verb reading
  no-remote         carry/projects.json — a project whose carrier is `drive` or `stays`
  the app's own id  app_sessions.py, imported when it is there: a window's `local_…` id from the
                    desktop app's session store ('' when the store does not name the window)

--dials --plates-only is the postman's JUDGE: each window is judged from the plate its
LAST reply ends with (effort.py tail_reply) and from nothing else — a window with no plate is
KEEP "no plate", never walked from its opener; a plate the rubric cannot read is KEEP "PLATE
UNREADABLE — <its first line>"; a stale or missing meter keeps every UP ("METER STALE — …") and
never blocks a DOWN. Every --json object carries `plate_uuid` (the reply record the plate was
read from), `local_id` and `plate` (the plate's own mind, level and clause).

--start prints: the reminder · a ⚠ line when the hub's own dial (read from its transcript, never
guessed) runs below a lane's walk, or one ⚠ line when that dial is unread · each lane's step and
its start object · the AFTER list (detach · the dial, never asked · group by project · record ·
say). Each --json object carries `starter` (the hub's mind, level, model, effort, read, below_walk).

THE TOOL WRITES NOTHING. Every verb reads. The hub session makes the app's calls (start,
detach, view, model, effort); the tool can make none of them.

Exit: 0 printed · 1 a STOP (one plain sentence with the move) · 2 a defect of its own.
Stdlib only, Python 3.9-compatible, macOS and Windows.
"""
import importlib.util
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

TOOL_VERSION = "0.3"
EXIT_OK, EXIT_STOP, EXIT_DEFECT = 0, 1, 2

MAX_AGE_MIN = 20            # a meter read longer ago than this is a STOP
MID_TURN_S = 60             # a transcript that moved this recently is mid-turn (--dials)
LIVE_MAX_MIN = 30           # a pulse file older than this says nothing about now (the
                            # collector's own half hour, read_live_sessions)
TITLE_MAX = 60              # the ACT-title ritual's cap
NAME_MAX = 24               # the app's session-name cap
TOOLS_ENV = "EXO_TOOLS_DIR"
SELF_ENV = "CLAUDE_CODE_SESSION_ID"
UNGATED = ("nothing", "none", "-")      # the collector's own words for an ungated lane
SENTENCE_HEAD = "read the project status/memory first."
PASTE_READY = "paste-ready:"
RULE = "---"

START_REMINDER = ("START — only on the user's explicit word («start them» · «open the windows "
                  "for me» · «1» / «window» / «session» to the spool question); without that "
                  "word, ask first (--ask), then hand the step.")
# On «spool» the session ASKS before it hands or starts: the user says whether they want the
# prompt or a new session started for them. The screen is a QUESTION screen: one sentence,
# numbered choices with the pick marked, one why line, «Say 1 or 2.»
ASK_HEAD = "SPOOL — %s · which way?"
ASK_LINES = (
    "1 · START MODE — a window started for you: titled, under its project, dial set   ← the pick",
    "2 · MANUAL MODE — the prompt to paste: both doors, you open the window yourself",
    "why: start mode costs you no window to open; manual mode when you want the words in your own hand",
    "Say 1 or 2.",
)
AFTER_LINES = (
    "AFTER 1 · detach_session <each new id> — at once, in the message right after the starts",
    "AFTER 2 · the dial, never asked: get_session <each new id>; where model or effort is not the "
    "walk's, set_session_model / set_session_effort to the walk's values (a cancelled card is "
    "retried once, right away)",
    "AFTER 3 · set_view group_by=project (once per sitting)",
    "AFTER 4 · record: one line in the hub STATUS ## Now naming the window, its dial and the "
    "reason",
    "AFTER 5 · say which windows opened, in one line, each under its project",
)
# The start tool cannot start a window above the starter's own model: the hub's own
# dial, read from the record, against each walk — one line per lane that starts below its walk,
# or one line when the hub's dial cannot be read. Silent when every walk is at or below the hub.
STARTER_BELOW = ("⚠ starting on %s · %s; the start tool cannot go above the starter — %s is set "
                 "to %s · %s at once (AFTER 2); its first turn, the reading, runs on %s")
STARTER_UNREAD = ("⚠ the starter's dial is unread (%s) — if this hub runs below a walk, each "
                  "window is set at AFTER 2 and its first turn runs on the hub's dial")
HUB_SWITCH = ("at a judgment step, message the hub for the switch rather than judging on a "
              "cheaper mind")

# The surfaces when the registry names none (these are the defaults). The NAME is
# built from the machine's own label, so nothing here spells a machine.
DEFAULT_TERMINAL = {"windows": ("⬛", "%s POWERSHELL", "powershell"),
                    "macos": ("\U0001f7e9", "%s TERMINAL", "zsh"),
                    "linux": ("\U0001f7e9", "%s TERMINAL", "bash")}
DEFAULT_CHAT_MARK = "\U0001f7e7"
APP_NAME = {"claude": "Claude Code", "codex": "Codex"}     # the vendors' own product names
NO_REMOTE_CARRIERS = ("drive", "stays", "upstream-readonly")

BACKTICK = re.compile(r"`([^`]+)`")
SHA = re.compile(r"(?<![0-9A-Za-z])([0-9a-f]{7,8})(?![0-9A-Za-z])")
LANDED = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)\s+LANDED OK\b")
FILE_EXT = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}/?$")
WIN_PATH = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]:\\[^·|`\"'()\n]*)")
POSIX_PATH = re.compile(r"(?:^|(?<=[\s`\"'(]))((?:~[\\/]|/)[^\s·|`\"'()][^·|`\"'()\n]*)")
CUT_WORDS = (" on the ", " on ", " (", " — ", " – ", " - ", " or ", ", ", "; ", " for ")
PROJECT_WORD = re.compile(r"^(?:project|folder|the project|the folder)\s+", re.I)
TITLE_HEAD = re.compile(r"^(ACT\s*[—–-]\s*[^:]+:\s*)(.*)$")
CLAUSE_SPLIT = re.compile(r"\s—\s|;")
QUOTE_END = re.compile(r"[\"`”']")


class Stop(Exception):
    """One plain sentence with the move. Printed as it stands; exit 1."""


class Defect(Exception):
    """The tool's own fault. One line; exit 2."""


# ═════════════════════════════════════════════════════════════════════════════
# the neighbours — found, imported, never copied
# ═════════════════════════════════════════════════════════════════════════════

def tools_dir():
    """The folder that holds exo_paths.py and its neighbours: beside this file (installed), else
    the folder EXO_TOOLS_DIR names, else the first `tools/` above this file (a staged copy)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isfile(os.path.join(here, "exo_paths.py")):
        return here
    named = os.environ.get(TOOLS_ENV, "").strip()
    if named and os.path.isfile(os.path.join(named, "exo_paths.py")):
        return os.path.abspath(named)
    cur = here
    for _ in range(8):
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cand = os.path.join(parent, "tools")
        if os.path.isfile(os.path.join(cand, "exo_paths.py")):
            return cand
        cur = parent
    return ""


class M(object):
    """The imported neighbours, held once per run."""
    tdir = ""
    paths = None
    rg = None
    usage = None
    effort = None
    co = None
    app = None          # app_sessions.py — optional: without it every local_id is ''


def load_tools():
    tdir = tools_dir()
    if not tdir:
        raise Defect("the tools spool.py reads (exo_paths.py and its neighbours) are not beside "
                     "it, not in %s and not above it — install it into the hub's tools folder"
                     % TOOLS_ENV)
    if tdir not in sys.path:
        sys.path.insert(0, tdir)
    try:
        import exo_paths
        import exo_registry
        import usage
        import effort
        path = os.path.join(tdir, "collect-openers.py")
        spec = importlib.util.spec_from_file_location("exo_collect_openers", path)
        if spec is None or spec.loader is None:
            raise ImportError("collect-openers.py is not in %s" % tdir)
        co = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(co)
    except Exception as exc:
        raise Defect("a neighbour could not be imported from %s (%s: %s)"
                     % (tdir, type(exc).__name__, " ".join(str(exc).split())))
    M.tdir, M.paths, M.rg, M.usage, M.effort, M.co = tdir, exo_paths, exo_registry, usage, \
        effort, co
    try:                                # the app's store reader: optional, never a defect
        import app_sessions
        M.app = app_sessions
    except Exception:
        M.app = None
    return M


# ═════════════════════════════════════════════════════════════════════════════
# the context: this machine, the person's names, the rubric
# ═════════════════════════════════════════════════════════════════════════════

class Ctx(object):
    pass


def _read_json(path):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.loads(fh.read(8 << 20))
    except (OSError, ValueError):
        return None


def context():
    rec = M.paths.paths(tool_file=os.path.join(M.tdir, "exo_paths.py"))
    if rec.get("problems"):
        raise Stop("the machine record has a problem: %s" % rec["problems"][0])
    if not rec.get("machine_file"):
        raise Stop("this machine has no machine record — bootstrap it, then spool again")
    c = Ctx()
    c.hub = os.path.abspath(str(rec["hub"]))
    c.machine = str(rec.get("machine") or "").lower()
    c.roots = dict((k, str(v)) for k, v in (rec.get("roots") or {}).items())
    c.projects = c.roots.get("projects") or ""
    c.machine_file = str(rec["machine_file"])
    c.reg = M.rg.registry(hub=c.hub)
    c.rubric, c.rubric_note = M.effort.load_rubric(c.hub)
    c.label = M.rg.machine_label(c.reg, c.machine)
    c.word = c.label.upper()
    c.os = machine_os(c)
    c.py = "python" if c.os == "windows" else "python3"
    c.sep = "\\" if c.os == "windows" else "/"
    c.notes = []
    # the collector reads the brain's TREE.md beside the hub this record names
    M.co.TREE_FILE = Path(c.hub) / "TREE.md"
    return c


def machine_os(c):
    """`macos` / `windows` / `linux` for THIS machine: the registry's word, else the machine
    record's own `os`, else the running system."""
    word = M.rg.machine_os(c.reg, c.machine)
    if word in ("macos", "windows", "linux"):
        return word
    rec = _read_json(c.machine_file) or {}
    said = str(rec.get("os") or "").lower()
    if said.startswith("darwin") or "macos" in said.split():
        return "macos"
    if said.startswith("windows") or said.startswith("win"):
        return "windows"
    if said.startswith("linux"):
        return "linux"
    if os.name == "nt":
        return "windows"
    return "macos" if sys.platform == "darwin" else "linux"


def tool_cmd(c, name):
    """`python3 tools/usage.py` / `python tools\\usage.py` — as the person types it in the hub."""
    return "%s tools%s%s" % (c.py, c.sep, name)


def hub_tool(c, name):
    """A hub tool by its absolute path, for a window that sits in another folder."""
    path = os.path.join(c.hub, "tools", name)
    return "%s %s" % (c.py, ('"%s"' % path) if " " in path else path)


# ═════════════════════════════════════════════════════════════════════════════
# the minds — the registry, then the rubric, then the record
# ═════════════════════════════════════════════════════════════════════════════

def mind_block(c, mind):
    want = str(mind or "").strip().upper()
    for entry in c.reg.get("minds") or []:
        if str(entry.get("name") or "").strip().upper() == want:
            return entry
    return {}


def known_mind(c, word):
    """The registry's mind a word means (aliases first), or '' when it names none."""
    token = M.rg.mind_alias(c.reg, str(word or "").strip().upper())
    return token if token and token in M.rg.mind_names(c.reg) else ""


def mind_kind(c, mind):
    return M.rg.mind_kind(c.reg, mind) or ""


def judgment_row(c):
    return M.effort.row_by_id(c.rubric, "judgment") or {}


def mechanical_row(c):
    return M.effort.row_by_id(c.rubric, "mechanical") or {}


def judgment_minds(c):
    """The judgment row's minds, in the user's own order, minus any the row refuses."""
    row = judgment_row(c)
    never = set(str(m).strip().upper() for m in (row.get("never") or []))
    out = []
    for m in row.get("minds") or []:
        name = known_mind(c, m) or str(m).strip().upper()
        if name and name not in never and name not in out:
            out.append(name)
    return out


def flagship(c):
    minds = judgment_minds(c)
    return minds[0] if minds else ""


def level_value(c, word):
    return M.effort.dial_value(c.rubric, str(word or "").strip().upper())


def level_word(c, value, family="anthropic"):
    return M.effort.dial_word(c.rubric, family, value).upper() if value else ""


def seen_model_ids(c, meter):
    """{model id: weight} the record itself shows: the meter's own tally of the last day, and
    the models of the live sessions on this machine."""
    out = {}
    acc = ((meter or {}).get("accounting") or {}).get("last_24h") or {}
    for mid, n in (acc.get("calls_by_model") or {}).items():
        try:
            out[str(mid)] = out.get(str(mid), 0) + int(n)
        except (TypeError, ValueError):
            out[str(mid)] = out.get(str(mid), 0)
    live = _read_json(os.path.join(c.hub, "live-sessions-%s.json" % c.machine)) or {}
    for sess in live.get("sessions") or []:
        mid = str(sess.get("model") or "")
        if mid:
            out[mid] = out.get(mid, 0)
    return out


def doors_of(c, mind, meter):
    """(cli word, app id, the one sentence that says the registry was silent, or '')."""
    block = mind_block(c, mind)
    cli = str(block.get("cli_long") or block.get("cli") or "").strip()   # the long-context word first
    app = str(block.get("app_id") or "").strip()
    if cli and app:
        return cli, app, ""
    seen = []
    for mid, weight in seen_model_ids(c, meter).items():
        if M.rg.family_word(mid, "claude") == mind:
            seen.append((weight, mid))
    seen.sort(reverse=True)
    rec_id = seen[0][1] if seen else ""
    missing = []
    if not cli:
        cli = M.rg.family_word(rec_id, "claude").lower() if rec_id else ""
        missing.append("CLI word")
    if not app:
        app = rec_id
        missing.append("app id")
    sentence = ("the registry names no %s for %s — the record's own: %s · %s"
                % (" or ".join(missing), mind, ("`%s`" % cli) if cli else "no CLI word",
                   app or "no app id seen, so the window starts on the caller's own model"))
    return cli, app, sentence


# ═════════════════════════════════════════════════════════════════════════════
# the live meter (usage.py's own readers)
# ═════════════════════════════════════════════════════════════════════════════

def refresh_move(c):
    return "refresh: get_usage, then %s --write" % tool_cmd(c, "usage.py")


def read_meter(c, login_arg, max_age):
    u = M.usage
    if login_arg:
        login = login_arg
    else:
        login, _how, _acc = u.session_login(c.roots, c.hub, session=os.environ.get(SELF_ENV),
                                            fallback=True)
    if not login or u.same_login(login, u.UNKNOWN_LOGIN):
        raise Stop("no login is readable for this window — name it with --login <login>, then "
                   "spool again")
    _path, data = u.newest_meter(c.hub, c.machine, "claude", login)
    if not data:
        raise Stop("no meter for %s on this machine — %s" % (login, refresh_move(c)))
    read_at = u.parse_iso(data.get("read_at"))
    now = datetime.now().astimezone()
    if read_at is None:
        raise Stop("the meter for %s carries no read time — %s" % (login, refresh_move(c)))
    age = (now - read_at).total_seconds() / 60.0
    if age > max_age:
        raise Stop("meter read %d min ago — %s" % (int(age), refresh_move(c)))
    cfg, _missing = u.load_settings(c.hub)
    warn, _pause = u.thresholds(cfg, "claude")
    top = flagship(c)
    floor_pct, all_pct = None, None
    for w in data.get("windows") or []:
        kind = str(w.get("kind") or "")
        if kind == "week" and all_pct is None:
            all_pct = _num(w.get("percent"))
        elif kind == "week-model" and top and \
                M.rg.mind_alias(c.reg, str(w.get("model") or "").upper()) == top:
            floor_pct = _num(w.get("percent"))
    others = [d.get("login") for _p, d in u.meters(c.hub, None, "claude")]
    return {"login": login, "short": u.short_login(login, against=others),
            "read_at": read_at, "when": u.when_word(read_at), "age_min": age,
            "warn": warn, "flagship": top, "flagship_pct": floor_pct, "all_pct": all_pct,
            "data": data}


def read_meter_soft(c, login_arg, max_age):
    """read_meter for the postman's judge (--plates-only): a stale, missing or unreadable meter
    is not a STOP — it keeps every UP ("METER STALE — …") and never blocks a DOWN."""
    try:
        return read_meter(c, login_arg, max_age)
    except Stop as exc:
        cfg, _missing = M.usage.load_settings(c.hub)
        warn, _pause = M.usage.thresholds(cfg, "claude")
        return {"login": login_arg or "", "short": "", "read_at": None, "when": "", "age_min": None,
                "warn": warn, "flagship": flagship(c), "flagship_pct": None, "all_pct": None,
                "data": None, "stale": str(exc)}


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(value):
    return "?" if value is None else "%d%%" % int(round(value))


def meter_words(c, meter):
    top = meter["flagship"].title() if meter["flagship"] else "the judgment mind"
    return "meter %s %s · all %s · %s · %s" % (top, _pct(meter["flagship_pct"]),
                                              _pct(meter["all_pct"]), meter["short"],
                                              meter["when"])


def under_warn(meter):
    return meter["flagship_pct"] is not None and meter["flagship_pct"] < meter["warn"]


# ═════════════════════════════════════════════════════════════════════════════
# the lanes (the collector's rows)
# ═════════════════════════════════════════════════════════════════════════════

def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _suffix(lane):
    return str(lane or "").rsplit("/", 1)[-1]


def match_lane(data, target, project=None):
    """The rows a lane word means: the collector's own match first; when it gives several,
    the one whose lane (or its part after the slash) is that word. Several rows of ONE lane
    carrying one opener into one folder are one lane."""
    rows = data["rows"]
    if project:
        rows = [r for r in rows if r["project"].lower() == project.lower()]
        if not rows:
            raise Stop("no project called %s on this machine — say the project as its folder "
                       "is named" % project)
    found, problem = M.co.match_rows({"rows": rows}, target)
    if problem and not found:
        key = _norm(target)
        found = [r for r in rows if key and (key == _norm(_suffix(r["lane"]))
                                             or key in _norm(r["lane"]))]
    if not found:
        known = sorted(set(r["lane"] for r in rows if r["active"]))
        words = [_norm(x) for x in re.split(r"[\s/]+", str(target)) if len(_norm(x)) >= 3]
        near = [k for k in known if any(x in _norm(k) for x in words)] or known
        raise Stop("no lane matches %s — say one of: %s" % (target, ", ".join(near[:12])
                                                           + (" …" if len(near) > 12 else "")))
    if len(set(r["lane"].lower() for r in found)) > 1:
        key = _norm(target)
        exact = [r for r in found if _norm(r["lane"]) == key or _norm(_suffix(r["lane"])) == key]
        if exact:
            found = exact
    lanes = sorted(set(r["lane"] for r in found))
    if len(lanes) > 1:
        raise Stop("%s names %d lanes: %s — say the one you mean"
                   % (target, len(lanes), ", ".join(lanes[:8])))
    first = found[0]
    others = [r for r in found[1:] if r["body"] != first["body"]]
    if others:
        raise Stop("%s rides %d projects with different openers (%s) — add --project <name>"
                   % (first["lane"], len(found), ", ".join(sorted(set(r["project"]
                                                                      for r in found)))))
    return first, sorted(set(r["project"] for r in found[1:]) - {first["project"]})


# ── the folder the window opens in: the opener's open_in, never a guess ─────

def _trim(text):
    t = str(text or "").strip()
    for word in CUT_WORDS:
        at = t.find(word)
        if at > 0:
            t = t[:at]
    return t.strip().rstrip(".,;:").strip()


def _foreign(c, path):
    """Another machine's spelling: a drive-letter path on a posix machine, a rooted posix path
    on Windows (a `~/` path is tried as written everywhere)."""
    if c.os == "windows":
        return path.startswith("/")
    return bool(re.match(r"^[A-Za-z]:\\", path))


def _base(path):
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1]


def open_in_folder(c, row):
    """(absolute folder, a note or '') — the folder the opener's `open_in:` names, verified on
    this machine. Another machine's path is read by its last folder name against this
    machine's projects root (or the hub, when it is the hub's own name), and said."""
    text = str((row.get("header") or {}).get("open_in") or "")
    native, foreign = [], []
    for m in POSIX_PATH.finditer(text):
        cand = _trim(m.group(1))
        if cand:
            (foreign if _foreign(c, cand) else native).append(cand)
    for m in WIN_PATH.finditer(text):
        cand = _trim(m.group(1))
        if cand:
            (foreign if _foreign(c, cand) else native).append(cand)
    seen_path = bool(native or foreign)
    for cand in native:
        full = os.path.abspath(os.path.expanduser(cand))
        if os.path.isdir(full):
            return full, ""
    hub_name = _base(c.hub)
    for cand in native + foreign:
        name = _base(cand)
        if not name:
            continue
        target = c.hub if name == hub_name else os.path.join(c.projects, name)
        if c.projects and os.path.isdir(target):
            return os.path.abspath(target), ("open_in names %s — this machine's %s"
                                             % (cand, os.path.abspath(target)))
    names = [s.strip() for s in BACKTICK.findall(text)]
    for seg in text.split("·"):
        seg = re.sub(r"^[A-Z]{2,}\s*[—–-]\s*", "", seg.strip())
        names.append(PROJECT_WORD.sub("", _trim(seg)))
    for name in names:
        name = name.strip().rstrip("/\\").strip()
        if not name or re.match(r"^ACT\s*[—\u2013-]", name) or "/" in name.strip("/") \
                or "\\" in name:
            continue
        for base in (c.projects, row["path"]):
            if not base:
                continue
            cand = os.path.join(base, name)
            if os.path.isdir(cand):
                return os.path.abspath(cand), ""
    if seen_path:
        shown = (native + foreign)[0]
        raise Stop("the folder %s that %s's opener names is not on this machine — clone or land "
                   "%s here first" % (shown, row["lane"], row["project"]))
    return os.path.abspath(row["path"]), "open_in names no folder — the opener's own folder"


# ── the sentence and the title ─────────────────────────────────────────────

def _ends(text):
    return text.rstrip().rstrip("`\"'*_ )").endswith((".", "!", "?"))


def _run_on(lines, i, first):
    """A hard-wrapped sentence: the line, then the lines under it until the text ends a
    sentence, a blank line comes, or a fence opens."""
    text = first
    j = i + 1
    while not _ends(text) and j < len(lines):
        nxt = lines[j].strip()
        if not nxt or nxt.startswith("```") or nxt.startswith("~~~"):
            break
        text = "%s %s" % (text, nxt)
        j += 1
    return text


def _ticked(rest):
    """`…` around a sentence, even when the sentence itself carries backticks: everything
    between the first and the LAST backtick of the text."""
    rest = rest.strip()
    if rest.startswith("`") and rest.count("`") >= 2:
        return rest[1:rest.rindex("`")]
    tick = BACKTICK.search(rest)
    return tick.group(1) if tick else rest


def body_sentence(body):
    """The opener body's own paste-ready line: the LAST line that starts `read the project
    status/memory first.` or carries `paste-ready:` (a hard-wrapped line read to the end of
    its sentence) — '' when it has none."""
    found = ""
    lines = str(body or "").splitlines()
    for i, raw in enumerate(lines):
        s = raw.strip().lstrip(">*_` \"'").rstrip()
        if s.lower().startswith(SENTENCE_HEAD):
            found = _run_on(lines, i, s).rstrip("`\"' *_")
            continue
        at = raw.lower().find(PASTE_READY)
        if at >= 0:
            rest = raw[at + len(PASTE_READY):].strip()
            if not rest:
                for k in range(i + 1, len(lines)):
                    t = lines[k].strip()
                    if t and not t.startswith("```") and not t.startswith("~~~"):
                        rest = _run_on(lines, k, t)
                        break
            elif not rest.startswith("`"):
                rest = _run_on(lines, i, rest)
            got = _ticked(rest).strip().strip("\"'").strip()
            if got:
                found = got
    return " ".join(found.split())


def lane_sentence(c, row, folder):
    own = body_sentence(row.get("body"))
    if own:
        return own, "the opener's own paste-ready line"
    opener = row.get("opener") or "the opener"
    if os.path.abspath(row["path"]) != os.path.abspath(folder) and row.get("opener"):
        opener_ref = os.path.join(row["path"], row["opener"])
        return ("%s Pick up %s on the %s: open %s and follow it."
                % (SENTENCE_HEAD, row["lane"], c.word, opener_ref)), \
            "the launch sentence, naming the opener by its path"
    return (M.co.LAUNCH_SENTENCE % (row["lane"], c.word, opener)), "the launch sentence"


# ── a captured lane opens the NEXT sitting ─────────────────────────────────

_SITTING_NO = re.compile(r"^\s*(?:ACT|ARCH)\s*[—–-]\s*[^:\n]+:\s*s(\d+)\b")


def captured_words(row):
    """(the NOTE line under the WHERE line, the sentence's prefix) for an opener the capture
    headed — its sitting ran and was captured from the outside — or ("", "") for any other."""
    cap = row.get("captured") or None
    if not cap:
        return "", ""
    date = cap.get("date") or "?"
    n, nxt = cap.get("sitting"), cap.get("next")
    if n is not None and nxt is not None:
        # which sitting this opener was WRITTEN FOR is read from the raw
        # header's open_in — row["open_in"] already says the NEXT sitting.
        raw_open_in = ((row.get("header") or {}).get("open_in") or row.get("open_in") or "")
        own = _SITTING_NO.match(M.co.lane_act_title({"open_in": str(raw_open_in),
                                                     "captured": None,
                                                     "lane": row.get("lane") or ""}))
        wrote_for = int(own.group(1)) if own else None
        if wrote_for is not None and wrote_for != n:
            note = ("NOTE — this opener was written for s%d; s%d ran after it and was captured %s; "
                    "its record is the HANDOFF CAPTURE block in STATUS; opening s%d"
                    % (wrote_for, n, date, nxt))
        else:
            note = ("NOTE — this opener was written for s%d, which ran and was captured %s; its "
                    "record is the HANDOFF CAPTURE block in STATUS; opening s%d" % (n, date, nxt))
        head = ("read the project status/memory first — including the HANDOFF CAPTURE block for "
                "s%d (captured %s); this is s%d. " % (n, date, nxt))
        return note, head
    title = cap.get("title") or "?"
    note = ("NOTE — this opener was written before the session \"%s\", which ran and was captured "
            "%s; its record is the HANDOFF CAPTURE block in STATUS; opening the next sitting"
            % (title, date))
    head = ("read the project status/memory first — including the HANDOFF CAPTURE block for the "
            "session \"%s\" (captured %s); this is the next sitting. " % (title, date))
    return note, head


def captured_sentence(head, sentence):
    """The prefix, then the opener's own sentence without its own `read the project
    status/memory first.` — the head says it once."""
    rest = str(sentence or "").strip()
    if rest.lower().startswith(SENTENCE_HEAD):
        rest = rest[len(SENTENCE_HEAD):].lstrip()
    return (head + rest).strip()


def full_title(row):
    title = M.co.lane_act_title(row)
    cut = QUOTE_END.search(title)
    if cut:
        title = title[:cut.start()]
    return " ".join(title.split()).rstrip(" ·,;")


def short_title(c, title):
    """(the title, shortened or not). Over 60 characters: keep `ACT — <Proj>/<Lane>: ` and the
    first clause up to ` — ` or `;`, add ` (<MACHINE>)`; a clause still too long is cut at its
    last whole word that fits."""
    if len(title) <= TITLE_MAX:
        return title, False
    tail = " (%s)" % c.word
    m = TITLE_HEAD.match(title)
    if not m:
        words, out = title.split(), ""
        for w in words:
            if len((out + " " + w).strip()) + len(tail) > TITLE_MAX:
                break
            out = (out + " " + w).strip()
        return out + tail, True
    head = m.group(1)
    clause = CLAUSE_SPLIT.split(m.group(2), 1)[0].strip()
    while clause and len(head + clause + tail) > TITLE_MAX:
        clause = clause.rsplit(" ", 1)[0] if " " in clause else ""
    return (head + clause).rstrip() + tail, True


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return (s[:NAME_MAX].rstrip("-")) or "lane"


# ── the gate ───────────────────────────────────────────────────────────────

def _path_like(span):
    s = span.strip()
    if not s or re.search(r"\s-{1,2}[A-Za-z]", s) or s.startswith("-"):
        return False
    return ("/" in s or "\\" in s or bool(FILE_EXT.search(s))) and not re.match(r"^[A-Za-z]:\\",
                                                                                 s)


def _git(root, args):
    return M.co.git(root, args)


def check_gate(c, row):
    """{value, gated, checks: [(ok|unverified, line)]} — or a Stop on a failed check."""
    value = (row.get("depends_on") or "nothing").strip() or "nothing"
    if value.lower() in UNGATED:
        return {"value": "nothing", "gated": False, "checks": []}
    checks, root = [], row["path"]
    for span in BACKTICK.findall(value):
        if not _path_like(span):
            continue
        p = os.path.expanduser(span.strip())
        full = p if os.path.isabs(p) else os.path.join(root, p)
        if os.path.exists(full):
            checks.append(("ok", "GATE OK — %s exists under %s" % (span.strip(), root)
                           if not os.path.isabs(p) else "GATE OK — %s exists" % span.strip()))
        else:
            raise Stop("GATE STOP — %s waits on %s, which is not here — land or make it, then "
                       "spool again" % (row["lane"], span.strip()))
    for sha in SHA.findall(value):
        if not (re.search(r"[0-9]", sha) and re.search(r"[a-f]", sha)):
            continue
        code, _out = _git(root, ["merge-base", "--is-ancestor", sha, "HEAD"])
        if code == 0:
            checks.append(("ok", "GATE OK — %s is in %s's history" % (sha, row["project"])))
        elif code == -1:
            checks.append(("unverified", "GATE UNVERIFIED — %s: the folder is not a git repo here "
                           "— the hub checks it by hand" % sha))
        else:
            raise Stop("GATE STOP — %s waits on %s, which is not in %s's history — pull or land "
                       "it, then spool again" % (row["lane"], sha, row["project"]))
    for pid in LANDED.findall(value):
        line = "%s LANDED OK" % pid
        hay = ""
        for name in ("STATUS.md", "landings-%s.json" % c.machine):
            try:
                with io.open(os.path.join(c.hub, name), encoding="utf-8",
                             errors="replace") as fh:
                    hay += fh.read(8 << 20)
            except OSError:
                pass
        if line in hay:
            checks.append(("ok", "GATE OK — %s is in the hub STATUS or this machine's landings"
                           % line))
        else:
            raise Stop("GATE STOP — %s waits on %s, which is in neither the hub STATUS nor this "
                       "machine's landings ledger — land %s first" % (row["lane"], line, pid))
    if not checks:
        checks.append(("unverified", "GATE UNVERIFIED — the hub checks it by hand: %s" % value))
    return {"value": value, "gated": True, "checks": checks}


# ── the walk (the Model-lines-are-walked and Judgment-steps laws) ──────────

def first_step(text):
    t = re.split(r"\s·\s|;|\s—\s", str(text or ""), 1)[0].strip()
    words = t.split()
    return " ".join(words[:12]) + ("…" if len(words) > 12 else "")


def walk(c, row, meter):
    """{mind, level (the user's word), value (the dial's), why, kind, judgment} — or a Stop."""
    header = row.get("header") or {}
    judgment = " ".join(str(header.get("judgment") or "").split())
    model_line = header.get("model") or ""
    _m, op_level = M.effort.split_model_line(model_line, c.rubric)
    op_mind = known_mind(c, M.co.mind_name(model_line))
    first = judgment.split()[0].strip(".,;:—-").lower() if judgment else ""
    is_judgment = bool(judgment) and first != "none"
    notes = []
    if is_judgment:
        minds = judgment_minds(c)
        if not minds:
            raise Stop("the rubric's judgment row names no mind — add its minds to "
                       "effort-rubric.json, then spool again")
        top, down = minds[0], (minds[1] if len(minds) > 1 else "")
        if under_warn(meter):
            mind = top
            why = first_step(judgment)
        elif down:
            mind = down
            reason = ("%s reads %s, at or past warn %d%%" % (top.title(),
                                                          _pct(meter["flagship_pct"]),
                                                          int(meter["warn"]))
                      if meter["flagship_pct"] is not None
                      else "the meter carries no %s week" % top.title())
            why = "%s — %s, so %s" % (first_step(judgment), reason, down.title())
        else:
            raise Stop("the stretch waits: %s reads %s (warn %d%%) and the rubric names no "
                       "step-down for judgment — say «continue» or name one"
                       % (top.title(), _pct(meter["flagship_pct"]), int(meter["warn"])))
        level = op_level if level_value(c, op_level) else ""
        if not level:
            level = str(judgment_row(c).get("level") or "").upper()
            notes.append("the opener names no level — the rubric's judgment level")
    else:
        if not op_mind:
            raise Stop("%s's model line names no mind the registry knows (%s) — walk it by hand "
                       "and say the mind" % (row["lane"], " ".join(model_line.split()[:6])
                                             or "empty"))
        mind = op_mind
        why = "mechanical"
        rest = judgment[len(first):].strip(" —-·,;") if judgment else ""
        if rest:
            why = "mechanical (%s)" % " ".join(rest.split()[:10])
        if not judgment:
            notes.append("no `judgment:` line — the opener's model line stands, unwalked")
        level = op_level if level_value(c, op_level) else ""
        if not level:
            level = str(mechanical_row(c).get("level") or "").upper()
            notes.append("the opener names no level — the rubric's mechanical level")
    value = level_value(c, level)
    if not value:
        raise Stop("no level the rubric knows for %s (%s) — say the level" % (row["lane"],
                                                                              level or "none"))
    kind = mind_kind(c, mind)
    return {"mind": mind, "level": level_word(c, value) or level, "value": value, "why": why,
            "kind": kind, "judgment": is_judgment, "notes": notes}


# ═════════════════════════════════════════════════════════════════════════════
# the step
# ═════════════════════════════════════════════════════════════════════════════

def surfaces(c, kind):
    """(terminal mark, terminal name, shell, chat mark, chat name) — the registry's
    `surfaces` when it names them, else the defaults built from this machine's label."""
    mark, name_fmt, shell = DEFAULT_TERMINAL.get(c.os, DEFAULT_TERMINAL["macos"])
    term_name = name_fmt % c.word
    app = APP_NAME.get(kind, kind.title() or "the app")
    chat_mark, chat_name = DEFAULT_CHAT_MARK, "%s CHAT BOX" % app.upper()
    s = c.reg.get("surfaces") if isinstance(c.reg.get("surfaces"), dict) else {}
    term = (s.get("terminal") or {}).get(c.machine) if isinstance(s.get("terminal"), dict) \
        else None
    if isinstance(term, dict):
        mark = str(term.get("mark") or mark)
        term_name = str(term.get("name") or term_name)
        shell = str(term.get("shell") or shell)
    chat = (s.get("chat") or {}).get(kind) if isinstance(s.get("chat"), dict) else None
    if isinstance(chat, dict):
        chat_mark = str(chat.get("mark") or chat_mark)
        chat_name = str(chat.get("name") or chat_name)
    return mark, term_name, shell, chat_mark, chat_name


def quote_zsh(text):
    if not re.search(r"[\"$`\\!]", text):
        return '"%s"' % text
    return "'%s'" % text.replace("'", "'\\''")


def quote_ps(text):
    return '"%s"' % text.replace("`", "``").replace("$", "`$").replace('"', '`"')


def cli_word(cli):
    """The model as the CLI takes it. High-context launch rule: a launch line
    names the mind's LONG-CONTEXT variant — the registry's `cli_long` word for that mind, which
    doors_of prefers over `cli` — quoted when it carries a bracket suffix; a standard window
    compacts mid-landing and loses the record."""
    w = str(cli or "").strip()
    if "[" in w and not w.startswith(('"', "'")):
        return '"%s"' % w
    return w


def launch_line(c, shell, folder, cli, sentence):
    cli = cli_word(cli)
    if shell == "powershell":
        return 'cd "%s"; claude --model %s %s' % (folder, cli, quote_ps(sentence))
    return 'cd "%s" && claude --model %s %s' % (folder, cli, quote_zsh(sentence))


def lane_facts(c, row, meter, also=()):
    """Everything one lane's step is made of — or a Stop."""
    fresh = row.get("fresh")
    lane = row["lane"]
    if fresh == "stale":
        note = (row.get("notes") or ["the opener could not be checked"])[0]
        raise Stop("STALE — %s: %s; not handed — open it with: %s" % (lane, note,
                                                                     SENTENCE_HEAD))
    if fresh not in ("fresh", "note") or not row.get("body"):
        raise Stop("NO OPENER — %s: no opener left; open it with: %s" % (lane, SENTENCE_HEAD))
    folder, folder_note = open_in_folder(c, row)
    if not os.path.isdir(folder):
        raise Stop("the folder %s is not on this machine — clone or land %s here first"
                   % (folder, row["project"]))
    gate = check_gate(c, row)
    w = walk(c, row, meter)
    if w["kind"] not in ("claude", "codex"):
        raise Stop("the walk names %s, a %s mind — this tool hands Claude and Codex doors only; "
                   "hand it by its own card: %s --expand \"%s\""
                   % (w["mind"], w["kind"] or "unknown", tool_cmd(c, "collect-openers.py"),
                      lane))
    sentence, sentence_from = lane_sentence(c, row, folder)
    captured_note, captured_head = captured_words(row)
    if captured_head:
        sentence = captured_sentence(captured_head, sentence)
        sentence_from += ", headed by the capture (BQ-335)"
    title = full_title(row)
    short, cut = short_title(c, title)
    facts = {"lane": lane, "project": row["project"], "folder": folder, "row": row,
             "folder_note": folder_note, "gate": gate, "walk": w, "sentence": sentence,
             "sentence_from": sentence_from, "title": short, "title_full": title,
             "title_cut": cut, "meter": meter, "also": list(also), "notes": [],
             "captured": row.get("captured") or None, "captured_note": captured_note}
    if row.get("source") not in ("folder", None, "none"):
        facts["notes"].append("⚠ STALE-BEHIND-CARRIER — the freshest copy rides %s (written %s); "
                              "the folder's copy is older or absent — land it before the window "
                              "opens" % (row.get("source"), row.get("written") or "not said"))
        gate["gated"] = True
        gate["checks"].append(("unverified", "GATE UNVERIFIED — the folder holds an older copy "
                               "than %s" % row.get("source")))
        if gate["value"] == "nothing":
            gate["value"] = "the %s copy lands in the folder" % row.get("source")
    if w["kind"] == "claude":
        cli, app, said = doors_of(c, w["mind"], meter.get("data"))
        if not cli:
            raise Stop("the registry names no CLI word for %s and the record shows no model id "
                       "for it — add `cli` to its block in registry.json" % w["mind"])
        facts["cli"], facts["app_id"] = cli, app or None
        if said:
            facts["notes"].append(said)
    else:
        facts["cli"], facts["app_id"] = "", None
    return facts


def step_lines(c, f):
    w, gate = f["walk"], f["gate"]
    kind = w["kind"]
    mark, term_name, shell, chat_mark, chat_name = surfaces(c, kind)
    app = APP_NAME.get(kind, kind.title())
    window = "NEW WINDOW" if kind == "claude" else "NEW THREAD"
    lock = "\U0001f512 " if gate["gated"] else ""
    model, level = w["mind"].title(), w["level"].title()
    out = ["▌ %s%s · %s · %s · folder %s · %s · %s"
           % (lock, c.word, app, window, f["folder"], model, level)]
    if f.get("captured_note"):
        out.append(f["captured_note"])           # under the WHERE line, one line
    out.append("\U0001f9e0 SET: %s · %s — %s (%s)" % (model, level, w["why"],
                                                    meter_words(c, f["meter"])))
    name = os.path.basename(f["folder"].rstrip("/\\")) or f["folder"]
    if kind == "claude":
        out.append("%s **%s** · NEW WINDOW · folder %s" % (mark, term_name, f["folder"]))
        out.append("```%s" % shell)
        out.append(launch_line(c, shell, f["folder"], f["cli"], f["sentence"]))
        out.append("```")
        out.append("%s **%s** · the project %s open in the app" % (chat_mark, chat_name, name))
    else:
        out.append("%s **%s** · a NEW thread with the project %s open in the app"
                   % (chat_mark, chat_name, name))
    out.append("```text")
    out.append(f["sentence"])
    out.append("```")
    if gate["gated"]:
        out.append("DO NOT OPEN BEFORE: %s" % gate["value"].upper())
    beside = (' · full title: "%s"' % f["title_full"]) if f["title_cut"] else ""
    out.append('✅ DONE WHEN: a %s titled "%s" answers with its WHERE WE ARE.%s'
               % ("window" if kind == "claude" else "thread", f["title"], beside))
    return out


def footer_lines(c, f):
    row = f["row"]
    out = []
    state = {"fresh": "FRESH", "note": "NOTE"}.get(row.get("fresh"), str(row.get("fresh")))
    line = "· opener %s · the %s copy · written %s · %s" % (
        row.get("opener") or "—", row.get("source") or "folder",
        row.get("written") or "not said", state)
    if row.get("fresh") == "note" and row.get("notes"):
        line += " — %s" % M.co.cut(row["notes"][0].split(": ", 1)[0], 120)
    out.append(line)
    for _ok, text in f["gate"]["checks"]:
        out.append("· %s" % text)
    if f["folder_note"]:
        out.append("· %s" % f["folder_note"])
    for note in f["walk"]["notes"] + f["notes"]:
        out.append("· %s" % note)
    if f["also"]:
        out.append("· the same lane rides %s too" % ", ".join(f["also"]))
    return out


def facts_json(c, f, starter=None):
    w, g = f["walk"], f["gate"]
    obj = {"lane": f["lane"], "project": f["project"], "folder": f["folder"],
            "title": f["title"], "title_full": f["title_full"], "sentence": f["sentence"],
            "door": w["kind"], "mind": w["mind"], "level": w["level"], "effort": w["value"],
            "cli": f["cli"] or None, "app_id": f["app_id"], "why": w["why"],
            "judgment": w["judgment"],
            "captured": f.get("captured"),
            "gate": {"value": g["value"], "gated": g["gated"],
                     "checks": [t for _o, t in g["checks"]]},
            "opener": {"file": f["row"].get("opener"), "source": f["row"].get("source"),
                       "fresh": f["row"].get("fresh"), "written": f["row"].get("written"),
                       "notes": f["row"].get("notes") or []},
            "meter": {"login": f["meter"]["login"], "read_at": f["meter"]["read_at"].isoformat(),
                      "flagship": f["meter"]["flagship"],
                      "flagship_percent": f["meter"]["flagship_pct"],
                      "all_percent": f["meter"]["all_pct"], "warn": f["meter"]["warn"]},
            "notes": f["walk"]["notes"] + f["notes"] + ([f["folder_note"]]
                                                        if f["folder_note"] else []),
            "stop": None}
    if starter is not None:
        obj["starter"] = dict((k, starter[k]) for k in ("mind", "level", "model", "effort",
                                                         "read"))
        obj["starter"]["below_walk"] = starter_below(c, starter, w)
    return obj


# ── START mode ─────────────────────────────────────────────────────────────

def no_remote(c, project):
    body = _read_json(os.path.join(c.hub, "carry", "projects.json")) or {}
    entries = {}
    if isinstance(body.get("projects"), dict):
        entries.update(body["projects"])
    entries.update(dict((k, v) for k, v in body.items() if isinstance(v, dict)
                        and k != "projects"))
    entry = entries.get(project) or {}
    carrier = str(entry.get("carrier") or "").strip().lower()
    return carrier if carrier in NO_REMOTE_CARRIERS else ""


def mail_token(lane):
    return _suffix(lane) or lane


def start_object(c, f, data):
    w, g, meter = f["walk"], f["gate"], f["meter"]
    lane, title = f["lane"], f["title"]
    if g["value"] == "nothing":
        gate_line = "Gate: nothing."
    else:
        gate_line = "Gate: %s — %s." % (g["value"], "; ".join(t for _o, t in g["checks"]))
    meter_line = ("Meter: %s %s · all %s · %s · read %s (warn %d%%)."
                  % (meter["flagship"].title() if meter["flagship"] else "judgment mind",
                     _pct(meter["flagship_pct"]), _pct(meter["all_pct"]), meter["login"],
                     meter["when"], int(meter["warn"])))
    machines = [c.machine] + [m for m in M.rg.machine_names(c.reg) if m.lower() != c.machine]
    token = mail_token(lane)
    boxes = ["%s/%s" % (m.upper(), token) for m in machines]
    ritual = ('Ritual: %s %s %s "%s" · %s --claim %s "%s" · mail %s, each read with %s --read '
              '<address> --mark "%s".'
              % (hub_tool(c, "i-am.py"), w["mind"], w["level"], title, hub_tool(c, "claim.py"),
                 lane, title, " and ".join(boxes), hub_tool(c, "mail.py"), title))
    dial = "Dial: %s · %s — %s; %s." % (w["mind"], w["level"], w["why"], HUB_SWITCH)
    parts = ["Lane %s in %s; its opener is %s (the %s copy, written %s, %s)."
             % (lane, f["folder"], f["row"].get("opener"), f["row"].get("source"),
                f["row"].get("written") or "not said", str(f["row"].get("fresh")).upper()),
             gate_line, meter_line, ritual, dial]
    carrier = no_remote(c, f["project"])
    if carrier:
        parts.append("Git: named-path git only, never push (%s's carrier is %s — no remote)."
                     % (f["project"], carrier))
    siblings = sorted(set(r["lane"] for r in data["rows"]
                          if r["path"] == f["row"]["path"] and r["lane"] != lane and r["opener"]
                          and r["active"]))
    if siblings:
        parts.append("Sibling lanes sharing this folder: %s." % ", ".join(siblings))
    return {"title": title, "cwd": f["folder"], "model": f["app_id"], "effort": w["value"],
            "prompt": f["sentence"], "background": " ".join(parts), "name": slug(lane)}


# ── SUCCESSOR mode (the context restart) ───────────────────────────────────
# A window whose context is about four fifths full writes its carryover, then starts its own
# successor: the lane's NEXT sitting, from the freshest opener, with the start object --start
# builds — and the retiring window's own moves around the start, in order, as the AFTER list.

SUCCESSOR_REMINDER = ("SUCCESSOR — the Context-restart law starts it: the carryover is written and "
                      "its opener FRESH first (the /restart skill, step 1); this window retires "
                      "when the AFTER list is done.")
SUCCESSOR_SENTENCE = ("Successor of «%s», started under the Context-restart law; the retiring "
                      "window's last-turn facts arrive by message.")
NEXT_MARK = " (next)"
SITTING_AT = re.compile(r"^(\s*(?:ACT|ARCH)\s*[—–-]\s*[^:\n]+:\s*s)(\d+)\b")
TITLE_PARTS = re.compile(r"^\s*(?:ACT|ARCH)\s*[—–-]\s*([^:\n]+):\s*(.*)$")


def sitting_of(title):
    m = SITTING_AT.match(str(title or ""))
    return int(m.group(2)) if m else None


def successor_title(opener_title, retiring):
    """(the successor's full title, its sitting or None, footer notes). The opener's own title
    with its sitting number moved on: past the retiring window's when the opener still names
    it or an older one; kept as written when the opener already names a later one
    (a carryover written for the next sitting is not counted twice). No number: ` (next)`."""
    own, ret = sitting_of(opener_title), sitting_of(retiring)
    if own is None:
        return (opener_title.rstrip() + NEXT_MARK, None,
                ["⚠ the opener's title carries no sitting number — the successor is titled "
                 "«…%s»; name its sitting by hand if the lane counts them" % NEXT_MARK])
    if ret is not None and own > ret:
        return opener_title, own, ["· the opener already names s%d, past the retiring s%d — "
                                   "kept as written" % (own, ret)]
    n = (ret if ret is not None and ret > own else own) + 1
    title = SITTING_AT.sub(lambda m: "%s%d" % (m.group(1), n), opener_title, count=1)
    notes = []
    if ret is not None and ret > own:
        notes.append("· the opener names s%d, behind the retiring s%d — the successor is s%d"
                     % (own, ret, n))
    return title, n, notes


def fit_title(c, full):
    """short_title, keeping the ` (next)` mark when the cut would drop it."""
    short, cut = short_title(c, full)
    if full.endswith(NEXT_MARK) and not short.endswith(NEXT_MARK):
        base, out = full[:-len(NEXT_MARK)], ""
        for word in base.split():
            if len((out + " " + word).strip()) + len(NEXT_MARK) > TITLE_MAX:
                break
            out = (out + " " + word).strip()
        short, cut = out + NEXT_MARK, True
    return short, cut


def arch_title(retiring, lane, today):
    """The retiring window's ARCH title: `ARCH — <Proj>/<Lane>: s<n> — <what it did> · <date>`."""
    m = TITLE_PARTS.match(str(retiring or ""))
    head = m.group(1).strip() if m else lane
    n = sitting_of(retiring)
    return "ARCH — %s: %s<what it did> · %s" % (head, ("s%d — " % n) if n is not None else "",
                                                today)


def successor_after(c, f, retiring, starter):
    mind = starter["mind"] if starter.get("read") else "<MIND>"
    release = '%s --release %s "%s"' % (hub_tool(c, "claim.py"), f["lane"], retiring)
    stamp = '%s --off %s "%s"' % (hub_tool(c, "i-am.py"), mind, retiring)
    retitle = arch_title(retiring, f["lane"], datetime.now().strftime("%Y-%m-%d"))
    lines = [
        "AFTER 1 · RELEASE · %s" % release,
        "AFTER 2 · STAMP OFF · %s" % stamp,
        "AFTER 3 · detach_session <the new id> — at once, in the message right after the start",
        "AFTER 4 · the dial, never asked: get_session <the new id>; where model or effort is not "
        "the walk's, set_session_model / set_session_effort to the walk's values (a cancelled "
        "card is retried once, right away)",
        'AFTER 5 · RETITLE · set_session_title self → "%s"' % retitle,
        "AFTER 6 · HAND-OFF · SendMessage to the successor: the last-turn facts (the shape in the "
        "/restart skill)",
        "AFTER 7 · set_view group_by=project (once per sitting)",
        "AFTER 8 · say, in one line: Context at <N>%%: carryover written, successor «%s» started "
        "under %s; this window retires." % (f["title"], f["project"]),
    ]
    notes = []
    if not starter.get("read"):
        notes.append("· this window's mind is unread (%s) — STAMP OFF takes the mind its own "
                     "stamp names" % (starter.get("why") or "no reading"))
    return lines, {"release": release, "stamp_off": stamp, "retitle": retitle}, notes


def run_successor(c, a):
    meter = read_meter(c, a["login"], a["max_age"])
    data = M.co.collect()
    row, others = match_lane(data, a["lanes"][0], a["project"] or None)
    f = lane_facts(c, row, meter, others)
    if f["walk"]["kind"] != "claude":
        raise Stop("the walk names %s, a %s mind — the app starts Claude windows only; hand %s's "
                   "door instead (spool.py \"%s\")" % (f["walk"]["mind"], f["walk"]["kind"],
                                                       f["lane"], f["lane"]))
    retiring = " ".join(a["retiring"].split())
    full, n, notes = successor_title(f["title_full"], retiring)
    short, cut = fit_title(c, full)
    f["title"], f["title_full"], f["title_cut"] = short, full, cut
    self_id = a["self"] if a["self"] is not None else os.environ.get(SELF_ENV, "")
    starter = starter_dial(c, self_id)
    start = start_object(c, f, data)
    start["background"] = "%s %s" % (start["background"], SUCCESSOR_SENTENCE % retiring)
    after, moves, more = successor_after(c, f, retiring, starter)
    obj = facts_json(c, f, starter)
    obj["start"] = start
    obj["successor"] = dict(moves, retiring=retiring, retiring_sitting=sitting_of(retiring),
                            sitting=n, title=short, title_full=full, after=after,
                            notes=notes + more)
    if a["json"]:
        say(json.dumps([obj], ensure_ascii=False, indent=1))
        return EXIT_OK
    say(SUCCESSOR_REMINDER)
    if not starter["read"]:
        say(STARTER_UNREAD % starter["why"])
    elif obj["starter"]["below_walk"]:
        w = f["walk"]
        say(STARTER_BELOW % (starter["mind"], starter["level"], f["lane"], w["mind"], w["level"],
                             starter["mind"]))
    for line in step_lines(c, f) + footer_lines(c, f) + notes + more:
        say(line)
    say(json.dumps(start, ensure_ascii=False))
    say(RULE)
    for line in after:
        say(line)
    return EXIT_OK


# ═════════════════════════════════════════════════════════════════════════════
# the dial pass (the engine half)
# ═════════════════════════════════════════════════════════════════════════════

def live_windows(c):
    path = os.path.join(c.hub, "live-sessions-%s.json" % c.machine)
    body = _read_json(path)
    if not isinstance(body, dict):
        raise Stop("no live-sessions file for this machine — run the pulse (%s), then --dials "
                   "again" % tool_cmd(c, "pulse.py"))
    when = M.usage.parse_iso(body.get("when"))
    age = ((datetime.now().astimezone() - when).total_seconds() / 60.0) if when else None
    if age is None or age > LIVE_MAX_MIN:
        raise Stop("the live-sessions file is %s old — run the pulse (%s), then --dials again"
                   % ("of unknown age" if age is None else "%d min" % int(age),
                      tool_cmd(c, "pulse.py")))
    return [s for s in body.get("sessions") or [] if isinstance(s, dict)]


def starter_dial(c, self_id):
    """The dial of the window that runs this tool — the hub — from the record, never a guess
    — its id, this machine's live-sessions file, its transcript's last reply. {mind,
    level, model, effort, read, why}; unread (read False, mind and level '') says why in `why`
    and is never a STOP — a start must still print."""
    out = {"mind": "", "level": "", "model": "", "effort": "", "read": False, "why": ""}

    def unread(reason):
        out["mind"], out["level"], out["why"] = "", "", reason
        return out
    sid = str(self_id or "").strip()
    if not sid:
        return unread("no session id")
    try:
        windows = live_windows(c)
    except Stop:
        path = os.path.join(c.hub, "live-sessions-%s.json" % c.machine)
        return unread("stale live-sessions file" if isinstance(_read_json(path), dict)
                      else "no live-sessions file")
    found = [s for s in windows if str(s.get("id") or "") == sid]
    if not found:
        return unread("this session is not in the live-sessions file")
    sess = found[0]
    kind = str(sess.get("kind") or "claude").lower()
    tpath = str(sess.get("transcript") or "")
    tail = M.effort.tail_reply(tpath) if tpath else {}
    model = str(tail.get("model") or "")
    value = str(tail.get("effort") or "").lower()
    out["model"], out["effort"] = model, value
    if not model:
        return unread("no reply yet")
    named, _fam, known = M.effort.mind_of_model(kind, model)
    mind = known_mind(c, named) if known else ""
    if not mind:
        return unread("the last reply's model %s names no mind the registry knows" % model)
    if not value:
        return unread("the last reply names no effort")
    family = M.effort.vendor_family(kind, model) or "anthropic"
    out["mind"], out["level"], out["read"] = mind, level_word(c, value, family), True
    return out


def starter_below(c, starter, w):
    """True when the walk outranks the starter: a mind the registry orders above the starter's
    (same family), or the same mind at a higher effort (the rubric's dial order)."""
    if not starter.get("read") or w.get("kind") != "claude" \
            or mind_kind(c, starter["mind"]) != "claude":
        return False
    if w["mind"] != starter["mind"]:
        return M.rg.mind_rank(c.reg, w["mind"]) < M.rg.mind_rank(c.reg, starter["mind"])
    order = [v for v, _word in M.effort.level_values(c.rubric.get("dials"))]

    def rank(value):
        value = str(value or "").lower()
        return order.index(value) if value in order else -1
    return rank(w["value"]) > rank(starter["effort"])


def _reply_text(rec):
    blocks = (rec.get("message") or {}).get("content") or []
    if isinstance(blocks, str):
        return blocks
    return "\n".join(str(b.get("text") or "") for b in blocks
                     if isinstance(b, dict) and b.get("type") == "text")


ARROW = re.compile(r"(?i)NEXT\s+(TURN|STRETCH)")
FIRST_LINE_MAX = 60


def plate_arrow(text):
    """The plate's first line — the `NEXT TURN|STRETCH` arrow in the reply's last lines, outside
    fenced blocks and block quotes (effort.py's own reading of where a plate lives) — with its
    markdown stripped and cut to 60 characters; '' when the reply carries no arrow. The LAST
    arrow is the plate's, as parse_ask reads it."""
    lines = str(text or "").splitlines()
    marked = M.effort._fence_and_quote(lines)
    low = max(0, len(lines) - M.effort.TAIL_LINES)
    found = ""
    for index in range(low, len(lines)):
        line, in_fence, in_quote = marked[index]
        if not in_fence and not in_quote and ARROW.search(line):
            found = " ".join(line.replace("*", " ").replace("`", " ").replace("_", " ").split())
    if len(found) > FIRST_LINE_MAX:
        found = found[:FIRST_LINE_MAX - 1].rstrip() + "…"
    return found


def read_plate(c, text, uuid):
    """The plate one reply ends with: {} when it carries no arrow; {unreadable, first_line,
    uuid} when the arrow has no trio the rubric can read (an unknown mind or level) — named,
    never skipped; else {mind, value, word, span, region, clause, first_line,
    uuid}."""
    first = plate_arrow(text)
    if not first:
        return {}
    ask = M.effort.parse_ask(text, c.rubric)
    mind = known_mind(c, ask.get("mind")) if ask and ask.get("mind") else ""
    if not mind or not ask.get("level"):
        return {"unreadable": True, "first_line": first, "uuid": uuid}
    region = "\n".join(str(text).splitlines()[-M.effort.TAIL_LINES:])
    return {"mind": mind, "value": ask["level"], "word": ask.get("word") or "",
            "span": ask.get("span") or "STRETCH", "region": region,
            "clause": plate_why(region), "first_line": first, "uuid": uuid}


def window_plate(c, records):
    """The newest ⇩/⇧ plate in the tail (read_plate's shape), or {}: the newest reply that
    carries an arrow decides — a readable plate, or a named unreadable one; an older reply's
    plate never stands in for it."""
    for rec in reversed(records):
        if not M.effort.is_reply_record(rec):
            continue
        plate = read_plate(c, _reply_text(rec), str(rec.get("uuid") or ""))
        if plate:
            return plate
    return {}


def app_ids(c):
    """{transcript stem: the app's local_… id} from the desktop app's store — {} without the
    reader or the store."""
    if M.app is None:
        return {}
    try:
        home = c.roots.get("home") or os.path.expanduser("~")
        recs = M.app.records(home, max_age_days=2.0)
        return dict((cli, str(r.get("local_id") or ""))
                    for cli, r in M.app.by_cli(recs).items())
    except Exception:
        return {}


def plate_why(region):
    """The plate's own clause: the words after its trio, else the line under it."""
    lines = [l.strip() for l in region.splitlines()]
    trio = re.compile(r"[A-Za-z0-9_.-]{2,20}\s*·\s*[A-Za-z0-9_.-]{2,20}\s*·\s*"
                      r"[A-Za-z0-9_.-]{2,20}`?")
    for i, line in enumerate(lines):
        m = trio.search(line)
        if m and re.search(r"(?i)NEXT\s+(TURN|STRETCH)", " ".join(lines[max(0, i - 2):i + 1])):
            rest = line[m.end():].strip(" `*_—-·")
            if not rest and i + 1 < len(lines):
                rest = lines[i + 1].strip(" `*_—-·")
            return " ".join(rest.split()[:14])
    return ""


def _rank(c, family, value):
    table = (c.rubric.get("dials") or {}).get(family) or {}
    keys = [str(k).lower() for k in table]
    return keys.index(str(value).lower()) if str(value).lower() in keys else -1


def dial_line(c, sess, data, meter, self_id, plates_only=False, ids=None):
    """(verdict, the one line, json facts). `data` is the collector's result, or a callable that
    collects on first use (the postman's judge collects only when an UP needs the opener's
    judgment line). `plates_only`: the plate the window's LAST reply ends with, and nothing else
    — never the opener's walk."""
    sid = str(sess.get("id") or "")
    title = " ".join(str(sess.get("title") or "").split()) or "(untitled %s)" % sid[:8]
    kind = str(sess.get("kind") or "claude").lower()
    tpath = str(sess.get("transcript") or "")
    tail = M.effort.tail_reply(tpath) if tpath else {}
    cur_model = str(tail.get("model") or sess.get("model") or "")
    family = M.effort.vendor_family(kind, cur_model) or "anthropic"
    cur_mind = ""
    if cur_model:
        named, _fam, known = M.effort.mind_of_model(kind, cur_model)
        cur_mind = known_mind(c, named) if known else ""
    cur_value = str(tail.get("effort") or "").lower()
    cur_word = level_word(c, cur_value, family) if cur_value else ""
    shown = "%s · %s" % (cur_mind or "unread", cur_word or "unread")
    out = {"id": sid, "title": title, "lane": "", "verdict": "KEEP", "mind": cur_mind,
           "effort_word": cur_word, "effort": cur_value or None, "model_id": None, "why": "",
           "plate_uuid": "", "local_id": (ids or {}).get(sid, ""), "plate": {}}

    def keep(reason):
        out["why"] = reason
        return "KEEP", 'KEEP "%s" · %s%s' % (title, shown, (" · " + reason) if reason else ""), out

    def rows():
        got = data() if callable(data) else data
        return got["rows"]

    if kind != "claude":
        return keep("another app's window — its own dial")
    lane = M.co.title_lane(title) if title.upper().startswith("ACT") else ""
    if not lane:
        return keep("not an ACT window")
    out["lane"] = lane
    if plates_only:
        plate = read_plate(c, tail.get("text") or "", str(tail.get("uuid") or ""))
    else:
        plate = window_plate(c, M.effort.tail_records(tpath) if tpath else [])
    if plate:
        out["plate_uuid"] = plate.get("uuid") or ""
        out["plate"] = {"first_line": plate.get("first_line") or ""}
    if plate.get("unreadable"):
        out["plate"]["readable"] = False
        return keep("PLATE UNREADABLE — %s" % plate["first_line"])
    if plates_only and not plate:
        return keep("no plate")
    row = None
    if not plates_only:
        found = [r for r in rows() if r["lane"].lower() == lane.lower()]
        row = found[0] if found else None
    target, why, ruling = None, "", False
    if plate:
        target = (plate["mind"], plate["value"])
        clause = plate.get("clause") or ""
        why = "its own plate (%s)%s" % ("⇧ NEXT TURN" if plate["span"] == "TURN"
                                        else "⇩ NEXT STRETCH",
                                        (": " + clause) if clause else "")
        ruling = bool(M.effort.judgment_verb(plate["region"]))
        out["plate"].update({"readable": True, "mind": plate["mind"], "effort": plate["value"],
                             "effort_word": level_word(c, plate["value"], family),
                             "span": plate["span"], "clause": clause})

    def judged_ruling(r):
        judged = " ".join(str((r.get("header") or {}).get("judgment") or "").split())
        jfirst = judged.split()[0].strip(".,;:—-").lower() if judged else ""
        return bool(judged and jfirst != "none")

    if row is not None:
        if judged_ruling(row):
            ruling = True
        if target is None:
            try:
                w = walk(c, row, meter)
            except Stop as exc:
                return keep("the opener cannot be walked: %s" % exc)
            if w["kind"] != "claude":
                return keep("the walk names %s, another app's mind — hand the lane by its door"
                            % w["mind"])
            target, why = (w["mind"], w["value"]), "the opener's walk: %s" % w["why"]
    if target is None:
        return keep("no plate and no opener for %s — nothing to walk" % lane)
    t_mind, t_value = target
    t_word = level_word(c, t_value, family)
    if mind_kind(c, t_mind) != "claude":
        return keep("%s names %s, another app's mind — hand the lane by its door"
                    % ("its plate" if plate else "the walk", t_mind))
    if t_mind == cur_mind and t_value == cur_value:
        return keep("")
    if sid and self_id and sid == self_id:
        return keep("SELF — the user's menu")
    try:
        moved = time.time() - os.path.getmtime(tpath) if tpath else None
    except OSError:
        moved = None
    if moved is not None and moved < MID_TURN_S:
        return keep("MID-TURN — next pass")
    top = flagship(c)
    mind_up = t_mind == top and cur_mind != top
    effort_up = _rank(c, family, t_value) > _rank(c, family, cur_value)
    if mind_up or effort_up:
        if meter.get("stale"):
            return keep("METER STALE — %s" % meter["stale"])
        pct = meter["flagship_pct"] if mind_up else meter["all_pct"]
        if pct is None or pct >= meter["warn"]:
            return keep("PAST WARN — %s reads %s, warn %d%%; the user's «continue» first"
                        % ((top.title() if mind_up else "all models"), _pct(pct),
                           int(meter["warn"])))
        if mind_up and not ruling and plates_only:
            # the opener's judgment line is a ruling too — read only now, when it decides
            found = [r for r in rows() if r["lane"].lower() == lane.lower()]
            ruling = bool(found) and judged_ruling(found[0])
        if mind_up and not ruling:
            return keep("UP to %s needs a ruling step — neither the plate nor the judgment line "
                        "names one" % top)
    out.update({"verdict": "SET", "mind": t_mind, "effort_word": t_word, "effort": t_value,
                "why": why})
    _cli, app, _said = doors_of(c, t_mind, meter.get("data"))
    # an effort-only change keeps the window's own model id when the record names no other
    out["model_id"] = app or (cur_model if t_mind == cur_mind and cur_model else None)
    return "SET", 'SET "%s" → %s · %s · %s' % (title, t_mind, t_word, why), out


# ═════════════════════════════════════════════════════════════════════════════
# the command line
# ═════════════════════════════════════════════════════════════════════════════

USAGE = __doc__.split("THE STEP,")[0].rstrip() + "\n"


def parse(argv):
    a = {"lanes": [], "all": False, "start": False, "dials": False, "json": False, "ask": False,
         "login": "", "max_age": MAX_AGE_MIN, "project": "", "self": None, "help": False,
         "plates_only": False}
    a["successor"], a["retiring"] = False, ""          # successor mode
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            a["help"] = True
        elif arg == "--all":
            a["all"] = True
        elif arg == "--start":
            a["start"] = True
        elif arg == "--ask":
            a["ask"] = True
        elif arg == "--dials":
            a["dials"] = True
        elif arg == "--json":
            a["json"] = True
        elif arg == "--plates-only":
            a["plates_only"] = True
        elif arg == "--successor":                       # successor mode
            a["successor"] = True
        elif arg == "--retiring":
            if i + 1 >= len(argv):
                raise Defect("--retiring needs the retiring window's title after it")
            i += 1
            a["retiring"] = argv[i]
        elif arg in ("--login", "--max-age", "--project", "--self"):
            if i + 1 >= len(argv):
                raise Defect("%s needs a value after it" % arg)
            i += 1
            if arg == "--max-age":
                try:
                    a["max_age"] = float(argv[i])
                except ValueError:
                    raise Defect("--max-age takes minutes, as a number")
            else:
                a[arg[2:].replace("-", "_")] = argv[i]
        elif arg.startswith("-"):
            raise Defect("%s is not an option this tool knows (--help lists them)" % arg)
        else:
            a["lanes"].append(arg)
        i += 1
    if not a["help"]:
        if a["successor"] and (a["all"] or a["dials"] or a["ask"] or len(a["lanes"]) != 1):
            raise Defect("--successor names one lane, and never rides with --all, --dials or "
                         "--ask")
        if a["successor"] and not a["retiring"].strip():
            raise Defect("--successor needs --retiring \"<this window's title>\"")
        if a["retiring"] and not a["successor"]:
            raise Defect("--retiring rides with --successor only")
        if a["dials"] and (a["lanes"] or a["all"] or a["start"]):
            raise Defect("--dials runs alone")
        if a["plates_only"] and not a["dials"]:
            raise Defect("--plates-only is a way of running --dials; say --dials with it")
        if a["start"] and a["all"]:
            raise Defect("--start names its lanes; it never runs over --all")
        if a["ask"] and (a["start"] or a["dials"]):
            raise Defect("--ask is the question before --start; it never rides with it or --dials")
        if not (a["dials"] or a["all"] or a["lanes"]):
            raise Defect("name a lane, or say --all or --dials (--help lists them)")
    return a


def say(text=""):
    sys.stdout.write(text + "\n")


def run_ask(c, a):
    """The one question on «spool»: a window started, or the prompt handed. No meter, no
    walk — only the lane names are checked, so a wrong name is a STOP here and not later."""
    data = M.co.collect()
    names = []
    if a["all"]:
        names = sorted({row["lane"] for row in data["rows"] if row["active"]})
    else:
        for target in a["lanes"]:
            row, _others = match_lane(data, target, a["project"] or None)
            names.append(row["lane"])
    if not names:
        raise Stop("no active lane to spool")
    if a["json"]:
        say(json.dumps({"ask": ASK_HEAD % " · ".join(names), "lanes": names,
                        "choices": {"1": "start", "2": "hand"},
                        "names": {"1": "START MODE", "2": "MANUAL MODE"}}, ensure_ascii=False))
        return EXIT_OK
    say(ASK_HEAD % " · ".join(names))
    for line in ASK_LINES:
        say(line)
    return EXIT_OK


def run_steps(c, a):
    if a["ask"]:
        return run_ask(c, a)
    if a.get("successor"):                       # successor mode
        return run_successor(c, a)
    meter = read_meter(c, a["login"], a["max_age"])
    data = M.co.collect()
    if a["all"]:
        chosen, seen = [], set()
        for row in data["rows"]:
            if not row["active"] or row["lane"].lower() in seen:
                continue
            seen.add(row["lane"].lower())
            others = sorted(set(r["project"] for r in data["rows"]
                                if r["lane"].lower() == row["lane"].lower() and r is not row))
            chosen.append((row, others))
    else:
        chosen = []
        for lane in a["lanes"]:
            try:
                chosen.append(match_lane(data, lane, a["project"] or None))
            except Stop as exc:
                chosen.append(({"lane": lane, "project": "", "gated": False}, exc))
    self_id = a["self"] if a["self"] is not None else os.environ.get(SELF_ENV, "")
    starter = starter_dial(c, self_id)
    done, stops, warns, started = [], 0, [], 0
    for row, others in chosen:
        if isinstance(others, Stop):
            stops += 1
            done.append((False, ["STOP — %s" % others],
                         {"lane": row["lane"], "project": "", "stop": str(others)}))
            continue
        try:
            f = lane_facts(c, row, meter, others)
        except Stop as exc:
            stops += 1
            done.append((bool(row.get("gated")), ["STOP — %s" % exc],
                         {"lane": row["lane"], "project": row["project"], "stop": str(exc)}))
            continue
        if a["start"] and f["walk"]["kind"] != "claude":
            stops += 1
            msg = ("the walk names %s, a %s mind — the app starts Claude windows only; hand %s's "
                   "door instead (spool.py \"%s\")" % (f["walk"]["mind"], f["walk"]["kind"],
                                                       f["lane"], f["lane"]))
            done.append((f["gate"]["gated"], ["STOP — %s" % msg],
                         {"lane": f["lane"], "project": f["project"], "stop": msg}))
            continue
        lines = step_lines(c, f) + footer_lines(c, f)
        obj = facts_json(c, f, starter)
        if a["start"]:
            start = start_object(c, f, data)
            lines.append(json.dumps(start, ensure_ascii=False))
            obj["start"] = start
            started += 1
            if obj["starter"]["below_walk"]:
                w = f["walk"]
                warns.append(STARTER_BELOW % (starter["mind"], starter["level"], f["lane"],
                                              w["mind"], w["level"], starter["mind"]))
        done.append((f["gate"]["gated"], lines, obj))
    if a["all"]:                       # independent lanes first, gated ones last (stable)
        done = [d for d in done if not d[0]] + [d for d in done if d[0]]
    blocks = [d[1] for d in done]
    objs = [d[2] for d in done]
    if a["json"]:
        say(json.dumps(objs, ensure_ascii=False, indent=1))
        return EXIT_STOP if stops else EXIT_OK
    if a["start"]:
        say(START_REMINDER)
        if started and not starter["read"]:
            say(STARTER_UNREAD % starter["why"])
        else:
            for line in warns:
                say(line)
    for n, lines in enumerate(blocks):
        if n:
            say(RULE)
        for line in lines:
            say(line)
    if a["start"] and stops < len(blocks):
        say(RULE)
        for line in AFTER_LINES:
            say(line)
    return EXIT_STOP if stops else EXIT_OK


def run_dials(c, a):
    plates_only = bool(a.get("plates_only"))
    if plates_only:                     # the postman's judge: a stale meter never blocks a DOWN
        meter = read_meter_soft(c, a["login"], a["max_age"])
    else:
        meter = read_meter(c, a["login"], a["max_age"])
    windows = live_windows(c)
    if plates_only:                     # the collector's scan only when an UP needs it
        held = []

        def data():
            if not held:
                held.append(M.co.collect())
            return held[0]
    else:
        data = M.co.collect()
    self_id = a["self"] if a["self"] is not None else os.environ.get(SELF_ENV, "")
    ids = app_ids(c)
    lines, objs = [], []
    for sess in windows:
        _verdict, line, obj = dial_line(c, sess, data, meter, self_id, plates_only, ids)
        lines.append(line)
        objs.append(obj)
    if a["json"]:
        say(json.dumps(objs, ensure_ascii=False, indent=1))
        return EXIT_OK
    if not lines:
        say("no live windows on this machine")
    for line in lines:
        say(line)
    return EXIT_OK


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        a = parse(argv)
        if a["help"]:
            say(USAGE)
            return EXIT_OK
        load_tools()
        c = context()
        if a["dials"]:
            return run_dials(c, a)
        return run_steps(c, a)
    except Stop as exc:
        if "--json" in argv:
            say(json.dumps({"stop": str(exc)}, ensure_ascii=False))
        else:
            say("STOP — %s" % exc)
        return EXIT_STOP
    except Defect as exc:
        sys.stderr.write("spool.py: %s\n" % exc)
        return EXIT_DEFECT
    except KeyboardInterrupt:
        return EXIT_DEFECT
    except Exception as exc:                       # the tool's own fault, said in one line
        sys.stderr.write("spool.py: defect — %s: %s\n" % (type(exc).__name__,
                                                          " ".join(str(exc).split())))
        return EXIT_DEFECT


if __name__ == "__main__":
    sys.exit(main())
