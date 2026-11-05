#!/usr/bin/env python3
"""mail.py — mail between live sessions through the brain's INBOX.md. One file, both machines, both vendors.

The mail rule: a line meant for a LIVE session carries an address right after the date —
  - YYYY-MM-DD · to: <MACHINE>/<lane> · <target project> · <text> · <suggested action>
and the receiver appends ` · delivered: <ISO> by <session title>`.

  mail.py --send TO TARGET TEXT ACTION [--no-push]   append one addressed line, push the brain
  mail.py --read TO [--mark "<session title>"] [--title "<session title>"] [--all]
                                                      print undelivered lines for TO; --mark stamps them delivered (+push).
                                                      With --title it also refreshes the ear, which is how a Codex hub
                                                      (no Monitor tool) shows a mailbox: it reads at every turn start.
                                                      --all also lists what it hid — letters a later push closed,
                                                      old alarms — each with why, never as MAIL.
  mail.py --read TO --for-the-user [--mark "<session title>"] [--title "<session title>"]
                                                      THE LANE-MAIL LAW: reads exactly as --read does, but PRINTS
                                                      for the person, not the session — one plain line
                                                      `<what it means for you> · <the one move>` per letter whose ACTION asks
                                                      them for a ruling, a physical move or a word, built from the ACTION
                                                      alone (no sender, body, token, count or frame). FYI, read, none and every
                                                      machine-only action print nothing; an empty result prints nothing at all.
  mail.py --lint-reply FILE                           exit 1 with one line naming the phrase when a reply's text aims mail words
                                                      at the person («letter», «mail», «letters waiting», «worth your eye»,
                                                      «when you are next at», «check for mail»); fenced code and lines that
                                                      quote a law (start with `**`) are not read. Exit 0 otherwise, 2 if unreadable.
  mail.py --announce TEXT [--target T] [--action A] [--quiet]
                                                      ONE machine-made line to EVERY OTHER machine's hub — the fleet
                                                      comes from the record (machine.json, the brain's manifest, the
                                                      hub's own stamps), never from a name written here. A fleet of one
                                                      machine sends nothing. --quiet sends nothing and says nothing.
  mail.py --watch TO [--every 150] [--title "<session title>"] [--hub DIR] [--no-pull] [--model <id>] [--force]
                                                      THE FLOOR ROAD. `--wait` is the road a session arms; `--watch` is the
                                                      floor for a machine without the postman's hooks, armed with the app's
                                                      Monitor tool (Claude); Codex runs --read at turn start.
                                                      IT OBEYS THE SAME REFUSAL: before it loops it asks what --wait
                                                      asks — a Fable window, a window above the context ceiling, a window
                                                      whose model it cannot read, or no postman beside mail.py to read it —
                                                      and refuses in the same one line, exit 0, no ear (logged in the
                                                      postman's waits.jsonl, when there is a postman to keep it); --model
                                                      and --force are --wait's own. Allowed, it loops: pull the brain, print
                                                      `MAIL for` only for a NEW letter that ASKS; a QUIET letter (--wait's
                                                      own test) is counted in the ear's `quiet`, never printed, so it never
                                                      wakes the window. A letter dated before the watch was armed
                                                      is counted the same way, and named in ONE count line printed only
                                                      beside the next asking letter.
                                                      UNDER A USAGE PAUSE it re-reads the meter once a minute,
                                                      exactly as --wait does, whatever --every says: a PAUSE that reaches
                                                      its window's model ends the watch in one line, exit 0, and the
                                                      letters wait for the window's next turn start — so a watch armed
                                                      before the PAUSE ends within a minute of it.
                                                      --title ENDS THE WATCH ITSELF the moment no i-am stamp in the hub lists
                                                      that title, so a retired session is never woken by its own watcher.
                                                      Each poll refreshes ear-<machine>-<lane>.json in the hub folder, so
                                                      the tree can say which machines are listening and which are not.
  mail.py --wait TO [--title "<session title>"] [--max-hours 12] [--model <id>] [--force]
                                                      THE WAITER: an idle session arms this as a BACKGROUND command
                                                      and pays nothing while it is silent. It polls only its own pending file
                                                      (a local stat: no git, no INBOX parse) and EXITS the moment a letter
                                                      that ASKS this window for something is there, printing it — the app
                                                      re-invokes the session when a background command exits.
                                                      NOTHING WAITS ON FABLE: before it arms, it reads THIS
                                                      window's model and context from its own transcript (the one --title
                                                      names, else this process's session) and REFUSES in one line — exit 0,
                                                      no loop, logged — a model usage-settings.json lists in
                                                      wait_refuse_models (default claude-fable-*), a context above
                                                      wait_context_ceiling_percent (default 40), or a window whose transcript
                                                      it cannot find. --model is a hint that must AGREE with the transcript;
                                                      --force is the owner's own override, logged.
                                                      UNDER A USAGE PAUSE that reaches this window's
                                                      model it refuses too — and asks the question:
                                                      'continue, or button up?' — and a waiter
                                                      already armed lets every letter wait for the window's
                                                      next turn start. A QUIET letter (action FYI,
                                                      read, none, no reply needed, no reply, empty, `none —…`, `FYI…`) never
                                                      ends a wait: it stays queued for the window's next turn start.
  mail.py --status [ADDRESS | pm-token]               every waiting letter, both directions, each with its why.
  mail.py --ack OWNER | <token> [--title "<session title>"]
                                                      the owner said "got it": the note stops waiting, on EVERY machine.
                                                      Writes acks/<token>.json in POST DIR; INBOX.md is never rewritten.
TO is <MACHINE>/<lane>, case-insensitive, and '-' and '/' are the same separator (ALPHA/Proj-Lane is ALPHA/Proj/Lane).
THE BROADCAST ADDRESS: TO = <MACHINE>/all is every live lane on that machine. The postman carries ONE copy to
each lane's session under a token of that lane's own (child_token), so each lane's hook, waiter or --read prints it once
and each lane's read is its own; --read/--watch of any lane on that machine include it; --mark never stamps it (one
stamp would hide it from every other lane). `all` is therefore never a lane's own name.
Paths come from the machine record the path resolver finds (tools/exo_paths.py); no user names. A run pointed at another
hub folder with --hub never pushes the brain.

A LETTER'S TOKEN: `pm-` + the first 12 hex of sha256 over the line with any
` · delivered: …` tail (and any ` · resolved: …` tail) removed and the ends trimmed. TWO BYTE-IDENTICAL LINES ARE ONE
LETTER, by definition — which is what makes delivery idempotent: a token delivered once
is never delivered again. --read, --watch and the `sent:` line carry it as ` [pm-…]`, so
the postman SEES a delivery in the transcript and NOBODY MARKS ANYTHING. This tool never
rewrites INBOX.md except on --mark, which the postman makes unnecessary.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_registry import registry, is_owner_token, owner_label as _owner_label  # noqa: E402
from exo_paths import paths                                                     # noqa: E402

_REG = [None]


def _reg():
    """The person's own names, read once per run."""
    if _REG[0] is None:
        _REG[0] = registry()
    return _REG[0]


def owner_label(when_unset="the owner"):
    """How to NAME the person in a line they will read."""
    return _owner_label(_reg(), when_unset)


def is_owner_address(addr):
    """True when an address means the person and not a session: OWNER and HUMAN
    always, plus the short word and aliases the registry names."""
    return is_owner_token(_reg(), addr_key(addr).split("/")[0])


_PM = []


def pm_owner_block(entry):
    """The owner's block inside one note entry, whichever key the file on disk
    carries — the postman's own rule, asked of it so the shape is never spelled
    twice. Without a postman here, the current key alone. The module is loaded
    once: this is called once per note in a file that may hold hundreds."""
    if not _PM:
        _PM.append(postman())
    pm = _PM[0]
    try:
        return pm.owner_block(entry) if pm is not None else (entry.get("owner") or {})
    except Exception:
        return (entry.get("owner") or {}) if isinstance(entry, dict) else {}

HUB = Path(__file__).resolve().parent.parent
INBOX = HUB / "INBOX.md"
# The header a NEW INBOX.md starts with: byte for byte the shipped seed,
# templates/INBOX.md, which carries no letter (the gate proves the two equal,
# so neither can drift from the other silently).
INBOX_SEED = """<!-- Shipped with the program. This file was created once, when there was no
     INBOX.md — by the installer, or by the first letter sent — and neither will
     touch it again: from now on it is yours. An update does not overwrite it. -->

# INBOX — cross-project findings

Any session that discovers something relevant to a DIFFERENT project drops it
here instead of touching that project's files. One dated line per finding,
under `## Waiting`:

`- YYYY-MM-DD · <target project> · <finding> · <suggested action>`

MAIL: a line meant for a LIVE session carries an address right after the date —

`- YYYY-MM-DD · to: <MACHINE>/<lane> · <target project> · <finding or paste> · <suggested action>`

one line per message, where `<MACHINE>` is a machine's name as its own
`machine.json` records it and `<lane>` is the lane's short token (a session
that speaks for the hub folder itself uses `hub`). The engine is
`tools/mail.py` — `--send TO TARGET TEXT ACTION` · `--read TO [--mark "<title>"]`
· `--watch TO [--every 150]`. A session that wants mail arms the watcher at its
wake, so each new addressed line reaches it with no human in the path; the
receiver marks delivery with `--read TO --mark "<title>"`.

A line with no `to:` is not addressed to a live session: it waits here until
someone reads this file.

Nothing under the heading is deleted: the record stays whole. A line here has
no done-marker in this version — which is why the asks screen leaves this file
alone — so a finding is closed where it lands, in the `## To do` list of the
project it names.

## Waiting
"""
FYI = "no reply needed — FYI"          # the action every machine-made arrival line carries
FYI_NEEDLE = FYI.split("—")[0].strip().casefold()    # "no reply needed" — derived, never spelt twice
DELIVERED_MARK = " · delivered:"
# the tail a push that LANDS writes onto every failed-push letter it closes —
# ` · resolved: <ISO> by the push that landed`. Spelled here and once in the sync
# package's sync.py (its RESOLVED_MARK, whose comment names this one); the two files have
# no import between them, on purpose. A resolved letter is CLOSED: never shown by --read,
# never an ask, never a wake.
RESOLVED_MARK = " · resolved:"
TAIL_MARKS = (DELIVERED_MARK, RESOLVED_MARK)
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

try:                                   # the session's own id, when its vendor gives one
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_common import session_identity
except Exception:                      # mail.py standing alone still sends and reads
    def session_identity(env=None): return {}

def machine_json():
    """The machine record the path resolver finds, as a dict — {} when there is none."""
    try: return json.load(open(paths(tool_file=__file__)["machine_file"], encoding="utf-8"))
    except Exception: return {}

def fleet_manifest():
    """The sync manifest whose `machines` map names the fleet, where the sync
    package keeps it: in the brain clone, else beside the sync package (the
    older layout keeps the two in one folder). None when there is none."""
    try: record = paths(tool_file=__file__)
    except Exception: return None
    for folder in (record["brain"], record["sync_dir"]):
        for name in ("sync-manifest.json", "manifest.user.json"):
            if folder is not None and (Path(folder) / name).is_file():
                return Path(folder) / name
    return None

def machine():
    return str(machine_json().get("name") or "?").upper()

def sync_entry():
    """The sync package's entry point, where the path resolver finds it when it is
    wanted: the older layout's own folder, or <hub>/sync in a program tree. None
    when this machine has none — every road that would push then says so and
    sends nothing."""
    found = paths(tool_file=__file__)["sync_dir"]
    return (Path(found) / "sync.py") if found is not None else None

def sync(verb):
    entry = sync_entry()
    if entry is None or not entry.exists(): return False
    r = subprocess.run([sys.executable, str(entry), verb], capture_output=True, text=True)
    return r.returncode == 0

def lines():
    return INBOX.read_text(encoding="utf-8").split("\n") if INBOX.exists() else []

def addr_key(addr):
    """One address, compared the way a human writes it: case-blind, and '-' and '/'
    the same separator, so `ALPHA/Proj-Lane` and `ALPHA/Proj/Lane` are one lane
    (both spellings live in INBOX.md, and matching only the exact bytes would
    miss one). Repeated separators collapse."""
    out = []
    for ch in str(addr or "").strip().lower():
        if ch in "-/":
            if out and out[-1] == "/": continue
            out.append("/")
        else: out.append(ch)
    return "".join(out).strip("/")

def untailed(line):
    """The line with its stamps' tails cut off — ` · delivered: …` and
    ` · resolved: …` — at the EARLIEST of the marks present, each found at its LAST
    occurrence (so a text that mentions one is not cut there)."""
    s = str(line or "")
    cuts = [s.rfind(m) for m in TAIL_MARKS if s.rfind(m) >= 0]
    return s[:min(cuts)] if cuts else s

def is_resolved(line):
    """Has a push that landed closed this letter? (its resolved tail)"""
    return RESOLVED_MARK in str(line or "")

def fields(line):
    """A letter's fields, split on ' · ' EXACTLY as --read's own reader has always
    split them: date · to: · target · text… · action. The ACTION is the last field
    (the text itself may carry ' · '), and this is the one place that is spelled.
    A stamp's tail is never a field: the delivered and resolved tails are cut first,
    so neither can ever be read as the action."""
    l = untailed(line).rstrip()
    if not l.startswith("- "): return []
    return [x.strip() for x in l[2:].split(" · ")]

def address_of(line):
    """The ADDRESS FIELD — the one right after the date — or '' when the line
    carries none. Never a mention inside the text."""
    f = fields(line)
    if len(f) >= 2 and f[1].lower().startswith("to:"): return f[1][3:].strip()
    return ""

def is_fyi(line):
    """THE ONE FYI TEST: a letter whose ACTION, casefolded, contains
    `no reply needed`. An FYI letter never wakes anyone and never holds a stop
    open; it rides along with the next delivery."""
    f = fields(line)
    return bool(f) and FYI_NEEDLE in f[-1].casefold()

QUIET_ACTIONS = ("fyi", "read", "none", "no reply needed", "no reply", "")

def is_quiet(line):
    """THE WAITER'S TEST: does this letter ASK its window for
    something? A QUIET letter — action `FYI`, `read`, `none`, `no reply needed`,
    `no reply`, empty, or one that begins `none —` or `FYI` (case-blind), and
    every letter is_fyi() calls FYI — never ends a wait: it stays queued and the
    window reads it at its next turn start. Any other action is an ASK.
    A RESOLVED letter is quiet whatever its action: a push that landed has
    closed it, so it never ends a wait and never rides a hook as an ask."""
    if is_resolved(line):
        return True
    f = fields(line)
    if not f:
        return False
    action = " ".join(f[-1].split()).casefold() if len(f) >= 5 else ""
    if action in QUIET_ACTIONS or FYI_NEEDLE in action:
        return True
    return action.startswith("fyi") or action.startswith("none —") or action.startswith("none -")

def action_of(line):
    f = fields(line)
    return f[-1] if len(f) >= 5 else ""

def token(line):
    """A LETTER'S IDENTITY, and the only place it is computed: `pm-` plus
    the first 12 hex of sha256 over the line with any ` · delivered: …` tail — and
    any ` · resolved: …` tail, cut at the earliest of the two — removed and
    the ends trimmed, UTF-8. ASCII only, so it survives any transcript's escaping.
    TWO BYTE-IDENTICAL LINES ARE ONE LETTER, by definition — which is exactly what
    makes delivery idempotent; and a letter is the same letter before and after
    either stamp."""
    s = untailed(line)
    return "pm-" + hashlib.sha256(s.strip().encode("utf-8")).hexdigest()[:12]

BROADCAST_LANE = "all"                 # <MACHINE>/all — every live lane on that machine

def broadcast_machine(addr):
    """The machine a BROADCAST address names (`NORTH/all` → `north`), or '' when the
    address is anything else. The one place the broadcast spelling is read."""
    parts = addr_key(addr).split("/")
    return parts[0] if len(parts) == 2 and parts[0] and parts[1] == BROADCAST_LANE else ""

def child_token(parent, session):
    """ONE LANE'S COPY OF A BROADCAST: `pm-` + 12 hex of sha256 over the letter's
    own token and the receiving session's id. Computed here and nowhere else, so
    the postman that queues the copy and the --read that prints it name the same
    token — and the postman SEES that lane's read in that lane's transcript."""
    raw = "broadcast|%s|%s" % (str(parent), str(session))
    return "pm-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

def shown_token(line, to=None):
    """The token a reader is shown for a line: a broadcast read by a lane is that
    lane's own copy when this process knows its session; every other line is
    the letter's own token."""
    if broadcast_machine(address_of(line)) and not broadcast_machine(to or ""):
        sid = session_identity().get("session") or ""
        if sid:
            return child_token(token(line), sid)
    return token(line)

# ---------------------------------------------------------------------------
# OLD ALARMS DO NOT RING . A USAGE PAUSE / USAGE WARN broadcast is a question
# about ONE moment of the meter: it is SUPERSEDED by any later USAGE letter or IGNORE
# note for the same machine (and the same login, where both lines name one), and it
# EXPIRES at the reset its own line names. Computed HERE and nowhere else — the
# postman's pass, --read, --watch and --wait all ask these functions.
# ---------------------------------------------------------------------------
ALARM_FALLBACK_HOURS = 24              # a line whose reset cannot be read lives this long
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_RESET_RE = re.compile(r"\bresets\s+(?:(mon|tue|wed|thu|fri|sat|sun)[a-z]*\s+)?(\d{1,2}):(\d{2})\b",
                       re.IGNORECASE)
_LOGIN_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

def text_of(line):
    """A letter's TEXT — every field between the target and the action."""
    f = fields(line)
    if len(f) >= 5: return " · ".join(f[3:-1])
    return f[3] if len(f) == 4 else ""

def usage_kind(line):
    """'alarm' — a USAGE PAUSE / USAGE WARN broadcast ;
    'usage' — any other USAGE letter; 'ignore' — an IGNORE note about one; '' — the rest.
    Every non-empty kind addressed to a machine supersedes that machine's earlier alarms."""
    t = text_of(line).lstrip().upper()
    if not t: return ""
    if t.startswith(("USAGE PAUSE", "USAGE WARN", "USAGE —", "USAGE -")):
        return "alarm" if broadcast_machine(address_of(line)) else "usage"
    if t.startswith("USAGE"): return "usage"
    if t.startswith("IGNORE") and "USAGE" in t: return "ignore"
    return ""

def alarm_login(line):
    """The login an alarm line names (the meter's own account), lower-cased — '' for none."""
    m = _LOGIN_RE.search(text_of(line))
    return m.group(0).lower() if m else ""

def letter_day(line):
    """The letter's own DATE field as a date, or None when it is not YYYY-MM-DD."""
    f = fields(line)
    try: return datetime.date.fromisoformat(f[0]) if f else None
    except ValueError: return None

def alarm_expires(line, sent_at=None):
    """When an alarm stops ringing: the reset its line names — `the week resets Wed 10:00`
    is the next Wednesday 10:00 AFTER the letter's date (a reset on the letter's own day is
    written as a bare `10:00`, the way usage.py's when_word writes it), `resets 11:50` is
    11:50 on the letter's date — local time, aware. A line with no readable reset lives
    ALARM_FALLBACK_HOURS from when it was sent (`sent_at`, else the end of its date)."""
    day = letter_day(line)
    m = _RESET_RE.search(text_of(line))
    if day is not None and m:
        hh, mm = int(m.group(2)), int(m.group(3))
        if hh < 24 and mm < 60:
            target = day
            if m.group(1):
                want = _WEEKDAYS.index(m.group(1).lower()[:3])
                ahead = (want - day.weekday()) % 7 or 7
                target = day + datetime.timedelta(days=ahead)
            return datetime.datetime(target.year, target.month, target.day, hh, mm).astimezone()
    base = sent_at
    if base is None and day is not None:
        base = datetime.datetime(day.year, day.month, day.day, 23, 59, 59).astimezone()
    if base is None: return None
    return base + datetime.timedelta(hours=ALARM_FALLBACK_HOURS)

# `USAGE PAUSE — Fable 94 percent · …` / `USAGE WARN — …` / `USAGE — Fable 85 percent of the week`:
# the line the alarm is about (a bare `USAGE —` is usage.py's WARN line), the meter's own short
# name for the window it quotes (usage.short_name), and the percent it quoted.
_METER_RE = re.compile(r"^\s*USAGE(?:\s+(PAUSE|WARN))?\s*[—-]\s*([^·]+?)\s+(\d+(?:\.\d+)?)\s+percent\b",
                       re.IGNORECASE)

def live_login(hub=None, roots=None, window=True):
    """The login the desktop app runs THIS reader under, lower-cased — '' when it
    cannot be read. usage.py's own resolver (app_account): a window's own variables when the
    reader is a window (`window`), else the app's own config — never the terminal's config
    (a guess about the app), never `unknown`, and nothing is learned or written by asking."""
    u = usage_module()
    if u is None or roots is None:
        return ""
    try:
        email, _acct, src = u.app_account(roots, hub=str(hub or ""), window=window, learn=False)
    except Exception:
        return ""
    if src not in ("window", "app") or not str(email or "").strip() \
            or u.same_login(email, getattr(u, "UNKNOWN_LOGIN", "unknown")):
        return ""
    return str(email).strip().lower()

def alarm_answered(line, sent_at=None, hub=None):
    """('<n>', '<line word>') when the newest meter file for the login the alarm
    names reads the model it quotes UNDER the line the alarm is about (PAUSE → the pause line,
    WARN → the warn line, both from usage.py's own settings) — else None. A meter older than
    the alarm, an alarm naming no login or quoting no percent, or a model the meter does not
    show: None. Computed from bytes, never guessed."""
    u = usage_module()
    login = alarm_login(line)
    m = _METER_RE.match(text_of(line))
    if u is None or not hub or not login or not m:
        return None
    level, name = (m.group(1) or "WARN").upper(), " ".join(m.group(2).split()).lower()
    mch = addr_key(address_of(line)).split("/")[0]
    try:
        _path, data = u.newest_meter(str(hub), mch, "claude", login=login)
        if not data:
            return None
        cfg, _missing = u.load_settings(str(hub))
        warn, pause = u.thresholds(cfg, "claude")
        read = u.parse_iso(data.get("read_at"))
    except Exception:
        return None
    if read is None:
        return None
    floor = sent_at
    if floor is None:
        day = letter_day(line)
        floor = datetime.datetime(day.year, day.month, day.day).astimezone() if day else None
    if floor is None or read < floor:
        return None                    # a meter older than the alarm answers nothing
    limit, word = (pause, "pause") if level == "PAUSE" else (warn, "warn")
    for w in data.get("windows") or []:
        try:
            if str(u.short_name(w)).strip().lower() != name: continue
            pct = float(w.get("percent"))
        except (TypeError, ValueError, AttributeError):
            continue
        return ("%d" % int(round(pct)), word) if pct < float(limit) else None
    return None

def alarm_verdicts(rows, at=None, hub=None, roots=None, login=None):
    """{token: (kind, why)} for every ALARM in `rows` that no longer rings — kind is
    'superseded' or 'expired'. `rows` is [(token, line, sent_at or None)] for every USAGE /
    IGNORE line, OLDEST FIRST (INBOX order); a later row of any usage kind for the same
    machine supersedes an alarm, unless both lines name a login and the logins differ.

    Only when the caller passes what it has (`hub` / `roots`; `login` is the
    reader's own live login when the caller has read it already): 'other-login' — the alarm
    names a login and the reader's live app login is readable and is another — and
    'answered' — the newest meter for the alarm's own login reads the model it quotes under
    the line it was about. With neither passed it is exactly what it was."""
    at = at or datetime.datetime.now().astimezone()
    out = {}
    mine = None                            # the reader's live login, read once and only if asked
    for i, (tok, line, sent) in enumerate(rows):
        if usage_kind(line) != "alarm": continue
        mch = addr_key(address_of(line)).split("/")[0]
        about = alarm_login(line)
        for _t2, line2, _s2 in rows[i + 1:]:
            kind2 = usage_kind(line2)
            if not kind2 or addr_key(address_of(line2)).split("/")[0] != mch: continue
            other = alarm_login(line2)
            if about and other and other != about: continue
            out[tok] = ("superseded", "superseded by a later %s for the %s — an old alarm "
                        "does not ring" % ("IGNORE note" if kind2 == "ignore" else "USAGE letter",
                                           mch.upper()))
            break
        else:
            ends = alarm_expires(line, sent)
            if ends is not None and at >= ends:
                out[tok] = ("expired", "its reset has passed (%s) — an old alarm does not ring"
                            % ends.strftime("%a %Y-%m-%d %H:%M"))
        if tok in out or (hub is None and roots is None and login is None):
            continue
        if about and (roots is not None or login is not None):
            if mine is None:
                mine = (str(login).strip().lower() if login is not None
                        else live_login(hub, roots))
            u = usage_module()
            same = getattr(u, "same_login", None) if u is not None else None
            differs = (not same(mine, about)) if same is not None else (mine != about)
            if mine and differs:
                out[tok] = ("other-login", "a question about another login's meter (%s) — this "
                            "window is signed in as %s" % (about, mine))
                continue
        got = alarm_answered(line, sent, hub) if hub is not None else None
        if got:
            out[tok] = ("answered", "the meter it asked about now reads %s — under the %s line"
                        % got)
    return out

def quiet_alarms(all_lines, at=None, hub=None, roots=None, login=None):
    """{token: (kind, why)} over INBOX lines in file order — what --read and --watch hide.
    `hub` / `roots`: what the caller has, for the two verdicts that read the
    reader's live login and the meter; with none passed it behaves exactly as before."""
    rows = [(token(l), l, None) for l in all_lines if l.startswith("- ") and usage_kind(l)]
    return alarm_verdicts(rows, at, hub=hub, roots=roots, login=login) if rows else {}

def alarm_rang_out(line, at=None):
    """The one test a road holding no INBOX can make (the waiter): an alarm whose own reset
    has passed. Supersession needs INBOX order and is the pass's to judge."""
    if usage_kind(line) != "alarm": return False
    ends = alarm_expires(line)
    return ends is not None and (at or datetime.datetime.now().astimezone()) >= ends

def dated_before(line, day):
    """ is this letter's own date before `day` (an ISO date string)? A line whose
    date field cannot be read is never 'earlier' — it is judged as it always was."""
    d = letter_day(line)
    return d is not None and d.isoformat() < str(day)

def addressed(to, all_lines=None):
    """lines whose ADDRESS FIELD (the one right after the date) is to: TO — never a mention inside the text.

    THE PERSON HAS ONE MAILBOX whatever word reaches it: `OWNER`, `HUMAN` and
    any word their registry names are one address, so a letter sent under one
    of them is read under any of them.

    A LANE ALSO HEARS ITS MACHINE'S BROADCASTS: `NORTH/Proj-Lane`
    includes every `to: NORTH/all` line."""
    key = addr_key(to); out = []
    mine = is_owner_address(to)
    parts = key.split("/")
    hears = parts[0] if (len(parts) >= 2 and not mine and not broadcast_machine(to)) else ""
    for l in (lines() if all_lines is None else all_lines):
        if not l.startswith("- "): continue
        a = address_of(l)
        if not a: continue
        if addr_key(a) == key or (mine and is_owner_address(a)):
            out.append(l)
        elif hears and broadcast_machine(a) == hears:
            out.append(l)
    return out

def postman(hub=None):
    """postman.py, beside this file first and the hub's tools/ second — or None.
    WITHOUT IT NOTHING BREAKS: --status says there is no postman here, --wait
    degrades to its own watch, and --read is exactly what it was."""
    import importlib.util
    here = Path(__file__).resolve().parent
    for cand in (here / "postman.py", Path(hub or HUB) / "tools" / "postman.py"):
        try:
            if not cand.is_file(): continue
            spec = importlib.util.spec_from_file_location("exo_postman_%d" % os.getpid(), str(cand))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            return mod
        except Exception: continue
    return None

def pm_post(pm, hub=None):
    """POST DIR as this run's postman resolves it. Pointed at a hub that is not
    this machine's own, it is THAT hub's .post/ and never the real one — so a
    rehearsal can never leak a phantom letter into the brain. An older postman
    without the argument still answers."""
    try:
        return Path(pm.post_dir(hub=str(hub or HUB)))
    except TypeError:
        return Path(pm.post_dir())

def post_states(hub=None):
    """{token: state} from EVERY machine's post-<machine>.json — the fleet's own
    record of what has been delivered or has expired, and of every note for the
    owner they have said "got it" to. A hub with no post file at all gives {}, and then
    nothing is hidden from --read."""
    out = {}
    try: files = sorted(Path(hub or HUB).glob("post-*.json"))
    except OSError: return out
    for f in files:
        if f.name == "post-config.json": continue
        try: d = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if not isinstance(d, dict): continue
        for group in ("letters", "nudges"):
            for tok, e in (d.get(group) or {}).items():
                if not isinstance(e, dict): continue
                if e.get("state") in ("delivered", "expired"):
                    out[str(tok)] = e["state"]
                if (pm_owner_block(e).get("acked") or {}).get("when"):
                    out[str(tok)] = "acked"
    return out

def undelivered(to, hub=None):
    """What --read prints: no inline mark, and not already delivered or expired in
    any machine's post file.

    LEGACY LETTERS ARE NOT HIDDEN. The postman's own bootstrap line promises them —
    `<n> earlier letters left to --read` — so the letters that were in INBOX before
    the postman arrived stay exactly as readable as they were.

    OLD ALARMS ARE NOT : a USAGE PAUSE / WARN broadcast a later USAGE letter or
    IGNORE note superseded, or whose reset has passed, is not printed — nor one
    about another login's meter than the one this reader runs under, nor one the meter it
    quotes has since answered.

    CLOSED LETTERS ARE NOT: a letter a push that landed stamped resolved."""
    done = post_states(hub)
    every = lines()
    gone = quiet_alarms(every, hub=hub or HUB, roots=reader_roots())
    out = []
    for l in addressed(to, every):
        if "delivered:" in l: continue
        if is_resolved(l): continue
        if done.get(token(l)) is not None: continue
        if token(l) in gone: continue
        if broadcast_machine(address_of(l)) and done.get(shown_token(l, to)) is not None:
            continue                       # THIS lane's copy is read; the others' are theirs
        out.append(l)
    return out

def reader_roots():
    """The machine record's roots, for the readers that ask usage.py who this reader is
    — None when there is no record, and then nothing is judged by login."""
    roots = machine_json().get("roots")
    return roots if isinstance(roots, dict) and roots else None

CLOSED_SAY_DAYS = 7    # a closed letter older than a week is history: --read says it no more

def hidden_letters(to, hub=None):
    """What --read leaves out, with why — [(line, why)] for the letters to TO a
    push that landed has closed (never read before it closed — a letter delivered first is
    simply delivered — and dated inside the last CLOSED_SAY_DAYS), and for the old alarms
    quiet_alarms hides."""
    every = lines()
    gone = quiet_alarms(every, hub=hub or HUB, roots=reader_roots())
    done = post_states(hub)
    since = (datetime.date.today() - datetime.timedelta(days=CLOSED_SAY_DAYS)).isoformat()
    out = []
    for l in addressed(to, every):
        if DELIVERED_MARK in l or done.get(token(l)) in ("delivered", "acked"): continue
        if is_resolved(l):
            if not dated_before(l, since):
                out.append((l, "closed by a later push"))
        elif token(l) in gone:
            out.append((l, gone[token(l)][1]))
    return out

def compose(to, target, text, action):
    """The one place an addressed line is spelled — --send and --announce write
    the same grammar or the receiver's reader would have to know two."""
    for s in (to, target, text, action):
        if "\n" in str(s): sys.exit("mail: one line per message")
    return f"- {datetime.date.today().isoformat()} · to: {to} · {target} · {text} · {action}"

def append(line):
    """One line onto INBOX.md. A hub whose INBOX.md is not there yet gets the
    seed's header first (INBOX_SEED), so the letter lands under `## Waiting`,
    where the board's reader looks — never a bare line nobody's reader sees.
    Exclusive create: two senders at once cannot both write
    the header."""
    if not INBOX.exists():
        try:
            with open(INBOX, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(INBOX_SEED + line + "\n")
            return
        except FileExistsError:
            pass
    with open(INBOX, "a", encoding="utf-8") as fh: fh.write(line + "\n")

def outbox_record(line, to, hub=None):
    """What this machine sent, for the postman's SENDER DUTIES: the sender is
    never left in silence. Written into POST DIR, which never syncs. Without a
    postman beside this file there is nothing to write and nothing is lost."""
    pm = postman(hub)
    if pm is None: return None
    try:
        post = pm_post(pm, hub)
        who = session_identity()
        body = {"token": token(line), "to": str(to),
                "when": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
                "from": {"session": who.get("session", ""), "vendor": who.get("vendor", ""),
                         "host_session": who.get("host_session", ""), "title": os.environ.get("EXO_SESSION_TITLE", "")}}
        pm.write_json_atomic(Path(post) / "outbox" / ("%s.json" % body["token"]), body)
        return pm
    except Exception:
        return None

def nudge_postman(pm, hub=None):
    """One bounded pass right after the push, so a letter to a session on THIS
    machine is queued within the second instead of within the minute. A failure
    is ignored on purpose: the scheduler's pass and the pulse's pass both follow."""
    if pm is None: return
    tool = Path(__file__).resolve().parent / "postman.py"
    if not tool.is_file(): tool = Path(hub or HUB) / "tools" / "postman.py"
    if not tool.is_file(): return
    try:
        subprocess.run([sys.executable, str(tool), "--pass", "--no-pull", "--quiet",
                        "--hub", str(hub or HUB)], capture_output=True, text=True, timeout=10)
    except Exception:
        pass

def road_line(pm, line, hub=None):
    """What the pass that just ran did with this letter, in one line the sender can
    act on — '' when it was not routed to a window on this machine."""
    if pm is None: return ""
    try:
        state = json.loads((Path(pm_post(pm, hub)) / "state.json").read_text(encoding="utf-8"))
        entry = (state.get("letters") or {}).get(token(line)) or {}
    except Exception:
        return ""
    att = entry.get("attended") or {}
    title = (entry.get("holder") or {}).get("title") or (entry.get("holder") or {}).get("session") or "?"
    road = att.get("road")
    if road == "send":
        return "road: pushed into «%s» now — it is attended (%s); %s" % (
            title, "+".join(att.get("tests") or []) or "?", att.get("why") or "")
    if road == "hook":
        return "road: «%s» is busy — its own hook carries it within seconds" % title
    if road == "next turn":
        # an FYI letter never rides send_message, attended or not
        return "road: «%s» is attended (%s) — an FYI letter is never pushed; it shows at its next turn" % (
            title, "+".join(att.get("tests") or []) or "?")
    if road == "announce" and att.get("held"):
        # attended, and the meter held the push — said so, never "pushed"
        return ("road: not pushed into «%s» — held: usage PAUSE (%s); it is attended (%s), so it "
                "is queued for its next turn and a desktop notice said so" % (
                    title, att["held"], "+".join(att.get("tests") or []) or "?"))
    if road == "announce":
        return "road: «%s» — %s; queued for its next turn and a desktop notice said so" % (
            title, att.get("why") or "idle")
    return ""

# ── a private lane's letters stay on their machine ─────────────────
# A letter to or from a lane the user marked private crosses INBOX.md as its
# ADDRESS and the lane's NAME only; the whole letter is kept in a file of this
# machine that never syncs, and --read on this machine prints it in the stub's
# place. ASSUMES: the sender's lane is its cwd or its EXO_SESSION_TITLE; the
# receiver's lane is the address's lane part. Opposite: a letter between two
# ordinary lanes is written byte for byte as before (gate-privacy C4b).
try:
    from exo_privacy import (private_lane_of as _private_lane_of,          # noqa: E402
                             lane_of_word as _lane_of_word, WITHHELD as _WITHHELD)
except Exception:
    _private_lane_of = _lane_of_word = None
    _WITHHELD = ""

PRIVATE_TARGET = "private"
PRIVATE_MAIL_ENV = "EXO_PRIVATE_MAIL"


def private_mail_file():
    """~/.exocortex/private-mail/letters.jsonl, or the file EXO_PRIVATE_MAIL names."""
    named = str(os.environ.get(PRIVATE_MAIL_ENV) or "").strip()
    return Path(named) if named else Path.home() / ".exocortex" / "private-mail" / "letters.jsonl"


def private_lane_for(to, hub=None):
    """The private lane a letter is addressed to or sent from, or None. Never raises."""
    if _private_lane_of is None:
        return None
    try:
        part = str(to or "").split("/", 1)[1] if "/" in str(to or "") else ""
        for word in (part, part.split("-", 1)[0]):
            lane = _lane_of_word(word, hub=hub) if word else None
            if lane:
                return lane
        return _private_lane_of(title=os.environ.get("EXO_SESSION_TITLE", ""),
                                cwd=os.getcwd(), hub=hub)
    except Exception:
        return None


def withhold_letter(line, to, hub=None):
    """The line INBOX.md may carry for this letter: the line itself, or — for a
    private lane — a stub naming the address, the lane and the machine that
    keeps the whole letter."""
    lane = private_lane_for(to, hub)
    if not lane:
        return line
    here = str(machine_json().get("name") or "this machine").upper()
    ref = hashlib.sha256(line.encode("utf-8")).hexdigest()[:8]
    stub = compose(to, PRIVATE_TARGET,
                   "%s · %s · it waits on %s · ref %s" % (_WITHHELD, lane, here, ref),
                   "read it on %s with mail.py --read %s" % (here, to))
    store = private_mail_file()
    try:
        store.parent.mkdir(parents=True, exist_ok=True)
        with open(store, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"stub": token(stub), "line": line, "to": str(to), "lane": lane,
                                 "when": datetime.datetime.now().astimezone().replace(
                                     microsecond=0).isoformat()}, ensure_ascii=False) + "\n")
        try:
            os.chmod(str(store), 0o600)
        except OSError:
            pass
    except OSError as exc:
        # nowhere to keep it: the letter is NOT sent, never sent whole
        sys.exit("mail: a private lane's letter could not be kept on this machine (%s) — "
                 "nothing was written to INBOX.md" % exc)
    return stub


def private_letters():
    """{stub token: the whole line} from this machine's private file — {} when none."""
    out = {}
    try:
        with open(private_mail_file(), encoding="utf-8") as fh:
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get("stub") and rec.get("line"):
                    out[rec["stub"]] = rec["line"]
    except OSError:
        pass
    return out


def shown_line(line, kept=None):
    """What a reader on this machine prints for an INBOX line: the whole letter
    when it is a private stub this machine keeps, else the line itself."""
    if PRIVATE_TARGET not in line:
        return line
    kept = private_letters() if kept is None else kept
    return kept.get(token(line), line)


def send(to, target, text, action, push=True, hub=None):
    line = withhold_letter(compose(to, target, text, action), to, hub)
    append(line)
    print("sent:", line[:120] + ("…" if len(line) > 120 else ""), "[%s]" % token(line))
    pm = outbox_record(line, to, hub)
    if push: print("push:", "ok" if sync("push") else "FAILED — run sync.py push by hand")
    nudge_postman(pm, hub)
    said = road_line(pm, line, hub)            # the sender hears which road it took
    if said: print(said)

def say_hidden(to, hub=None, show=False):
    """ONE line for the letters about failed pushes a later push closed —
    `N letter(s) about failed pushes closed by a later push — not shown` — and, under
    --all, every hidden line with why it is hidden (never as MAIL: nothing hidden asks)."""
    try:
        hidden = hidden_letters(to, hub)
    except Exception:
        return
    closed = [l for l, why in hidden if is_resolved(l)]
    if closed and not show:
        print("%d letter(s) about failed pushes closed by a later push — not shown "
              "(--all shows them)" % len(closed))
    if show:
        for l, why in hidden:
            print("hidden (%s): %s [%s]" % (why, l, token(l)))

def read(to, mark=None, title=None, every=150, hub=None, show_all=False):
    if title:                              # a read BY A SESSION is a mailbox being held (Codex's ONBOARD)
        write_ear(hub or HUB, to, title, every, how="read")
    todo = undelivered(to, hub)
    notes = owner_notes(hub) if is_owner_address(to) else []
    say_hidden(to, hub, show=show_all)
    if not todo and not notes: print(f"no mail for {to}"); return
    for n in notes:                        # a nudge is a note for the owner with no INBOX line
        print("MAIL:", n.get("line") or "", "[%s]" % n.get("token"))
    if not todo: return
    earlier = read_record(hub, mark or title)
    fresh = [l for l in todo if shown_token(l, to) not in earlier]
    kept = private_letters()
    for l in todo: print("MAIL:", shown_line(l, kept), "[%s]" % shown_token(l, to))
    note_read(hub, mark or title, todo, to)
    if mark:
        if earlier and fresh:              # a mark must never sweep
            for l in fresh:                # letters that landed between the read and the mark
                print("NEW — read it; the next --mark takes it:", l, "[%s]" % shown_token(l, to))
        take = [l for l in todo if l not in fresh] if earlier else todo
        # A BROADCAST IS NEVER STAMPED: one stamp in INBOX.md would hide
        # it from every other lane. This lane's read is its own copy's token,
        # printed above and seen by the postman in this session's transcript.
        wide = [l for l in take if broadcast_machine(address_of(l))]
        take = [l for l in take if not broadcast_machine(address_of(l))]
        if not take:
            print("marked 0 delivered — %s" % ("a broadcast is read per lane and never stamped"
                                                 if wide else "every line here is new to this reader"))
            return
        mark_delivered(take, mark)

def mark_delivered(take, mark):
    """--mark, made safe: the rewrite is COMPARE-AND-SWAP. Five sessions append to
    INBOX.md on this machine right now, and the old rewrite could drop a line that
    landed while the new text was being built. Three tries, then it says plainly
    that nothing was stamped."""
    stamp = f" · delivered: {datetime.datetime.now().astimezone().isoformat(timespec='minutes')} by {mark}"
    take_set = set(take)
    for _ in range(3):
        try: before = INBOX.stat()
        except OSError: print("mark not taken — INBOX.md is not here"); return
        L = lines()
        text = "\n".join(l + stamp if l in take_set else l for l in L)
        fd, tmp = tempfile.mkstemp(dir=str(INBOX.parent), prefix=".INBOX", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh: fh.write(text)
        # INBOX.md KEEPS ITS OWN MODE. A rewrite is not an occasion to change who
        # may read a file, and mkstemp's 0600 is not the mailbox's mode either:
        # the temp file is set to what INBOX already is, before the replace.
        try: os.chmod(tmp, before.st_mode & 0o7777)
        except OSError: pass
        try: after = INBOX.stat()
        except OSError: after = None
        if after and (after.st_mtime_ns, after.st_size) == (before.st_mtime_ns, before.st_size):
            os.replace(tmp, str(INBOX))
            print(f"marked {len(take)} delivered ·", "push ok" if sync("push") else "push FAILED")
            return
        try: os.unlink(tmp)
        except OSError: pass
    print("mark not taken — INBOX.md changed under the mark three times; nothing was "
          "stamped (with the postman running nothing needs marking)")

def owner_notes(hub=None):
    """The NUDGES still waiting — notes the postman composed itself about a
    letter no road could carry. They are not INBOX lines, so --read OWNER reads
    them from the post files or nobody ever sees them."""
    pm = postman(hub)
    if pm is None: return []
    try:
        return [r for r in pm.owner_rows(Path(hub) if hub else HUB) if r.get("kind") == "nudge"]
    except Exception:
        return []

def read_slug(who):
    return re.sub(r"[^a-z0-9]+", "-", str(who or "").lower()).strip("-")[:60] or "unknown"

def read_record(hub, who):
    """The tokens an EARLIER --read already printed to this reader."""
    pm = postman(hub)
    if pm is None or not who: return set()
    try:
        d = json.load(open(pm_post(pm, hub) / "read" / ("%s.json" % read_slug(who)), encoding="utf-8"))
        return set(d.get("tokens") or [])
    except Exception:
        return set()

def note_read(hub, who, printed, to=None):
    pm = postman(hub)
    if pm is None or not who: return
    try:
        path = pm_post(pm, hub) / "read" / ("%s.json" % read_slug(who))
        have = read_record(hub, who)
        have.update(shown_token(l, to) for l in printed)
        pm.write_json_atomic(path, {"title": str(who), "tokens": sorted(have),
                                    "when": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()})
    except Exception:
        pass

# ---------------------------------------------------------------------------
# THE LANE-MAIL LAW: mail between sessions is the machine's, never
# the person's. The person hears ONE plain line of what a note means for them, or nothing.
# --for-the-user builds that line; --lint-reply checks a reply never aims mail words at them.
# ---------------------------------------------------------------------------

# Words in an ACTION that put a move on the PERSON (a ruling, a physical move, a word). An action
# with none of them is machine-only, and the person hears nothing: silence is the law's default.
USER_ASK = re.compile(
    r"\b(rule|ruling|decide|decision|approve|approval|authori[sz]e|choose|pick|yes or no|"
    r"go-ahead|go ahead|say|your|you|plug|unplug|press|tap|click|reboot|restart|power|insert|"
    r"carry|bring|sign in|log in|turn on|turn off|by hand)\b", re.I)
MAIL_WORD = re.compile(r"\b(letter|mail|e-?mail)(s?)\b", re.I)
SPLIT_ASK = re.compile(r"\s+[—–-]\s+|:\s+")

def asks_the_user(line):
    """Does this letter's ACTION ask something of the PERSON? Quiet actions (FYI, read, none…)
    never do; of the rest, only an action that names a move for them."""
    if is_quiet(line): return False
    a = " ".join(action_of(line).split())
    return bool(a) and bool(USER_ASK.search(a))

def user_line(line):
    """ONE plain line for the person, from the ACTION field alone — `<what it means for you> ·
    <the one move>`, split at the action's first dash or colon; an action with neither is its own
    one move and prints as it stands. The words «letter» and «mail» are never said to the person."""
    a = " ".join(action_of(line).split())
    parts = SPLIT_ASK.split(a, maxsplit=1)
    out = " · ".join(p.strip().rstrip(".") for p in parts if p.strip())
    return MAIL_WORD.sub(lambda m: "item" + m.group(2), out)

def read_for_the_user(to, mark=None, title=None, every=150, hub=None):
    """`--read TO --for-the-user`: the same reading as read() — same ear, same undelivered, same
    read record, same --mark — but it PRINTS for the person: one line per letter that asks them
    something, built from its action. No sender, no body, no token, no count, no frame; an
    empty result prints nothing at all. What --mark says about its stamp is swallowed."""
    import contextlib, io
    if title:
        write_ear(hub or HUB, to, title, every, how="read")
    todo = undelivered(to, hub)
    if not todo: return
    seen_lines = []
    for l in todo:
        if asks_the_user(l):
            s = user_line(l)
            if s and s not in seen_lines: seen_lines.append(s)
    earlier = read_record(hub, mark or title)
    fresh = [l for l in todo if shown_token(l, to) not in earlier]
    note_read(hub, mark or title, todo, to)
    for s in seen_lines: print(s)
    if mark:
        take = [l for l in todo if l not in fresh] if earlier else todo
        take = [l for l in take if not broadcast_machine(address_of(l))]
        if take:
            with contextlib.redirect_stdout(io.StringIO()):
                mark_delivered(take, mark)

# the phrases that aim mail words at the person, most specific first; a line is named by the first
# that matches. «letter» and «mail» match as whole words (and their plurals), never inside another.
LINT_PHRASES = (
    ("letters waiting", r"\bletters\s+waiting\b"),
    ("worth your eye", r"\bworth\s+your\s+eye\b"),
    ("when you are next at", r"\bwhen\s+you\s+are\s+next\s+at\b"),
    ("check for mail", r"\bcheck\s+for\s+mail\b"),
    ("letter", r"\bletters?\b"),
    ("mail", r"\bmails?\b"),
)

def lint_reply(path):
    """`--lint-reply FILE`: exit 1 with ONE line naming the first phrase that aims mail words at the
    person, 0 when the text is clean. Fenced code blocks are not read, and neither is a line that
    quotes a law (it starts with `**`). A file that cannot be read says so in one line: exit 2."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print("lint-reply: cannot read %s (%s)" % (path, exc.__class__.__name__)); return 2
    fenced = False
    for n, raw in enumerate(text.split("\n"), 1):
        s = raw.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fenced = not fenced; continue
        if fenced or s.startswith("**"): continue
        for name, rx in LINT_PHRASES:
            if re.search(rx, s, re.I):
                print("lint-reply: «%s» aimed at the user (line %d)" % (name, n)); return 1
    return 0

# ---------------------------------------------------------------------------
# the fleet: who else is out there
# ---------------------------------------------------------------------------

def fleet(hub=None):
    """Every machine the record knows, lower-cased. Three sources, all read, none
    written into this file (a third machine needs no edit):
    machine.json's own name, the machines the brain's sync manifest lists, and
    every machine that has left a stamp or a carrier file in the hub folder.
    A name the record does not carry is not in the fleet."""
    hub = Path(hub) if hub else HUB
    found = set()
    name = str(machine_json().get("name") or "").strip().lower()
    if name: found.add(name)
    try:
        d = json.load(open(fleet_manifest(), encoding="utf-8"))
        found.update(str(k).strip().lower() for k in (d.get("machines") or {}) if str(k).strip())
    except Exception: pass
    for pattern, cut in (("live-*-*.json", 5), ("carriers-*.json", 9), ("ear-*-*.json", 4)):
        try: files = sorted(hub.glob(pattern))
        except OSError: files = []
        for f in files:
            if f.name.startswith("live-sessions-"): continue
            stem = f.stem[cut:]
            first = stem.split("-")[0].strip().lower()
            if first: found.add(first)
    return sorted(m for m in found if m and m != "?")

def real_hub():
    """The hub folder machine.json names — the one whose INBOX.md is the brain's.
    A run pointed anywhere else is a rehearsal and never pushes."""
    root = (machine_json().get("roots") or {}).get("orchestrator")
    try: return Path(root).resolve() if root else None
    except Exception: return None

def announce(text, target="Exocortex", action=FYI, quiet=False):
    """ONE line to every OTHER machine's hub: a session woke, signed off, took a
    pen or released one. The fleet is discovered, the
    push is mail.py's own, and a fleet of one machine sends nothing at all."""
    if quiet: return 0
    here = str(machine_json().get("name") or "").strip().lower()
    others = [m for m in fleet(HUB) if m != here]
    if not others:
        print("announced to nobody — this fleet has one machine"); return 0
    tos = []
    for m in others:
        to = "%s/hub" % m.upper()
        append(compose(to, target, text, action))
        tos.append(to)
    if HUB != real_hub():
        tail = " · not pushed (this is not the brain's hub folder)"
    elif sync_entry() is None or not sync_entry().exists():
        tail = " · not pushed (no sync.py on this machine)"
    else:
        tail = " · pushed" if sync("push") else " · push FAILED — run sync.py push by hand"
    print("announced to %s%s" % (" · ".join(tos), tail))
    return 0

# ---------------------------------------------------------------------------
# the ear: which mailboxes are actually armed
# ---------------------------------------------------------------------------

def ear_path(hub, to):
    """ear-<machine>-<lane>.json beside the stamps. The name is the address
    itself, slugged, so ALPHA/Proj-Lane and ALPHA/Proj/Lane share one ear."""
    slug = re.sub(r"[^a-z0-9]+", "-", addr_key(to)).strip("-") or "unknown"
    return Path(hub) / ("ear-%s.json" % slug)

def write_ear(hub, to, title, every, how="watch", quiet=None):
    """Say, in the hub folder, that this mailbox is being watched — refreshed on
    every poll so the file's own age is the proof. Written whole through a temp
    file, because the brain's push may land mid-write. An ear that cannot be
    written never stops the watch.

    `quiet` (--watch only): how many QUIET letters this watch has
    counted and NOT printed since it armed — FYI mail that is waiting for the
    window's next --read, never a wake. Omitted by every other road."""
    key = addr_key(to).split("/")
    path = ear_path(hub, to)
    body = {"to": str(to), "machine": key[0] if key else "", "lane": "/".join(key[1:]),
            "when": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "title": str(title or ""), "every": int(every), "how": str(how)}
    if quiet is not None:
        body["quiet"] = int(quiet)
    who = session_identity()               # WHICH SESSION is holding this mailbox:
    for k in ("session", "host_session", "vendor"):   # the postman routes to a session, never to a title
        if who.get(k): body[k] = who[k]
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, str(path))
        try: os.chmod(str(path), 0o644)      # the stamps' own mode; mkstemp's 0600 is not a signal file's
        except OSError: pass
    except Exception as exc:
        print("ear not written (%s) — the watch runs on" % exc, flush=True)
        return None
    return path

def stamp_titles(hub):
    """Every session title the i-am stamps in `hub` say is live — or None when no stamp could be read.

    None is the honest answer for "I cannot tell" and never ends a watch. live-sessions-*.json is the
    pulse's own file (a different schema, no titles): skipped, so a field added there can never keep a
    retired session's watcher alive."""
    titles, read_any = set(), False
    try: files = [f for f in sorted(hub.glob("live-*.json")) if not f.name.startswith("live-sessions-")]
    except OSError: return None
    for f in files:
        try: data = json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        read_any = True
        for s in (data.get("sessions") or []):
            if isinstance(s, dict) and s.get("title"): titles.add(str(s["title"]).strip())
    return titles if read_any else None

def postman_fresh(pm, seconds, hub=None):
    """Has this machine's postman passed inside `seconds`? Then it has already
    pulled the brain, and a watcher pulling again only races it in one git repo.
    Unknown or stale answers False, so the watch keeps its own pull."""
    if pm is None: return False
    try:
        age = pm.heartbeat_age(pm_post(pm, hub))
        return age is not None and age < seconds
    except Exception:
        return False

def watch(to, every, title=None, hub=None, pull=True, force=False, model_hint=None):
    """THE FLOOR ROAD. It asks refuse_or_arm() exactly what --wait asks,
    before anything is armed: refused, it prints that one line and returns 0 —
    no ear, no loop, the refusal logged by the same call. Allowed, it prints
    `MAIL for` only for a letter that ASKS (is_quiet, --wait's own test); a
    quiet letter is counted into the ear's `quiet` and never printed, because
    every printed line wakes the window for a full turn.

    THE PAUSE REACHES THE ROAD THAT WAS ALREADY OPEN: refuse_or_arm()
    read the meter once, at arming. From then on it is read again at most once a
    minute — usage_pause(), --wait's own call at --wait's own cadence — between
    the polls, whatever --every says; under a PAUSE that reaches this window's
    model the watch prints one line and returns 0 instead of printing another
    letter into the window. A watch armed with --force past a PAUSE ends at the
    first re-read, the same way."""
    hub = Path(hub) if hub else HUB
    pm = postman(hub)
    refused = refuse_or_arm(to, title, hub, pm, force=force, model_hint=model_hint)
    if refused:
        print(refused, flush=True)                 # ONE line, exit 0, no loop, no ear
        return 0
    seen = set(addressed(to))                      # what is already in the file is not new mail
    quiet, held = 0, 0                             # quiet since arming (the ear's) · since the last print
    arm_day = datetime.date.today().isoformat()    # 
    earlier, earlier_told = [], set()
    ear = write_ear(hub, to, title, every, how="watch", quiet=quiet)   # armed now, not one poll from now
    print(f"watching {INBOX.name} for to: {to} · every {every}s · machine {machine()}"
          + (f" · ends when '{title}' is off" if title else "")
          + (f" · ear {ear.name}" if ear else ""), flush=True)
    said = False
    recheck = usage_recheck_s()
    last_pause = time.time()                       # refuse_or_arm() has just read the meter
    next_poll = last_pause + every
    while True:
        time.sleep(max(0.05, min(next_poll, last_pause + recheck) - time.time()))
        if time.time() - last_pause >= recheck:
            last_pause = time.time()               # the meter, at most once a minute
            paused = usage_pause(hub, _WAIT_MODEL[0])
            if paused:
                print("%s — watch ended: letters now wait for this window's next turn start"
                      % paused, flush=True)
                return 0
        if time.time() < next_poll:
            continue
        next_poll = time.time() + every
        if pull and not postman_fresh(pm, 180, hub): sync("pull")   # one puller per machine, not one per watcher
        asks = []
        for l in undelivered(to, hub):
            if l not in seen:
                seen.add(l)
                if dated_before(l, arm_day):       #  last week's mail a pull brought in is
                    quiet += 1                     # quiet — counted, never printed on its own
                    earlier.append({"token": token(l)})
                elif is_quiet(l): quiet += 1; held += 1
                else: asks.append(l)
        write_ear(hub, to, title, every, how="watch", quiet=quiet)  # the ear's age is the proof that this is still listening
        for l in asks:
            print(f"MAIL for {to}: {l}", "[%s]" % shown_token(l, to), flush=True)
        if asks and earlier:                       # ONE count line, and only beside an ask: on
            say_earlier(earlier, earlier_told, to) # --watch every printed line wakes the window
            earlier = []
        if asks and held:
            print("(+%d FYI letter%s waiting — read them at your next turn)"
                  % (held, "" if held == 1 else "s"), flush=True)
            held = 0
        if title:
            live = stamp_titles(hub)
            if live is None:
                if not said: said = True; print("i  stamps unreadable — watching on", flush=True)
            elif title.strip() not in live:
                print(f"watch ended: {title} is off", flush=True); return

# ---------------------------------------------------------------------------
# THE WAITER — an idle session, zero tokens while silent
# ---------------------------------------------------------------------------

def deliver(items, pm, post, session, road, skipped=None):
    """THE DELIVERY STEP, and the only one. Today it prints the frame and the
    waiter exits, because the app re-invokes a session when a background command
    exits. The day the session inbox socket's message format is published, THIS
    FUNCTION changes and nothing else does.

    The waiter hands over ONLY what ended the wait — the asks, and
    a note for the owner's phone riding along — and names them in its first
    line. A quiet letter and every notice stay in the pending file, and the
    window's next turn start prints them (the hook road, unchanged).

    An alarm whose own reset has passed is never carried by a waiter.
    Nor a letter a push that landed has closed (is_quiet says so for it), nor a
    send order — an order rides a turn its carrier is taking anyway, never a wake."""
    asks = wants_answer(items)
    carried = [i for i in items if (i.get("kind") or "letter") == "owner"
               or ((i.get("kind") or "letter") == "letter"
                   and not (i.get("fyi") or i.get("quiet") or is_quiet(i.get("line") or ""))
                   and not is_resolved(i.get("line") or "")
                   and not alarm_rang_out(i.get("line") or ""))]
    take = [i for i in items if i in asks or i in carried]
    named = "; ".join("%s · %s [%s]" % (i.get("to") or "", action_of(i.get("line") or "")
                                         or i.get("kind") or "", i.get("token") or "")
                      for i in asks)
    for_user = next((i.get("to") for i in asks if i.get("to")), "") or "<TO>"
    print("the wait ended on %d asking letter(s): %s · for the person, print: mail.py --read %s --for-the-user"
          % (len(asks), named, for_user), flush=True)
    try:
        print(pm.frame(take, skipped=skipped), flush=True)   #  says what it skipped
    except TypeError:
        print(pm.frame(take), flush=True)                    # a postman from before 
    pm.receipt(post, take, session, road=road)
    try:
        said = bool(pm.skipped_words(skipped)) and any(
            (i.get("kind") or "letter") == "letter" for i in take)
        pm.clear_pending(post, session, list(take) + list((skipped or {}).get("drop") or []),
                         said_skipped=said)
    except (TypeError, AttributeError):
        pm.clear_pending(post, session, take)

# THE ALIVE MARK: a waiter's own sign of life, so the hook
# can tell a window that is listening from one that has gone deaf WITHOUT EVER
# PROBING A PID — on Windows os.kill(pid, 0) terminates the process. It is
# touched at most every ALIVE_TOUCH_S, removed on every exit path, and a killed
# waiter simply ages out: an absent mark and a stale one mean the same thing.
ALIVE_TOUCH_S = 10

def alive_path(post, session):
    return Path(post) / "waiters" / ("%s.alive" % session)

def touch_alive(post, session):
    """Write the mark. Never raises: a mark that cannot be written costs an arm
    line the session does not need, never the wait."""
    try:
        path = alive_path(post, session)
        path.parent.mkdir(parents=True, exist_ok=True)
        try: os.chmod(str(path.parent), 0o700)
        except OSError: pass
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%s\n" % datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        try: os.chmod(str(path), 0o600)
        except OSError: pass
    except Exception:
        pass

def drop_alive(post, session):
    try: os.unlink(str(alive_path(post, session)))
    except OSError: pass
    except Exception: pass

# A WAITER THAT LIVED IS THE ANSWER TO EVERY TELL.
#
# The hook counts its unanswered arm tells in told/<session>.json and falls
# silent after three; the reset it had (`mark > since`) could only ever see a
# KILLED waiter's stale mark, because a waiter that DID ITS JOB and left removed
# the very mark that was the evidence the tell had been answered. So: Stop →
# tell #1 → the session arms → a letter arrives → the waiter delivers, exits and
# clears its mark → the woken turn forgets to re-arm → the next Stop found no
# mark, a tell younger than arm_again_minutes, and SAID NOTHING. The window held
# its lane deaf with no later Stop to catch it — the failure this rule
# exists to prevent.
#
# A waiter that lived at least ALIVE_LIVED_S clears the count on its way out.
# One that dies younger LEAVES it, and that is what still bounds the fast loop:
# a bad --title ends a wait in about 3 s with `wait ended: … is off`, that exit
# wakes the session, and its Stop must stay silent.
ALIVE_LIVED_S = 60

def drop_told(post, session):
    """Forget the hook's tell count. os/pathlib only, and it never raises: a
    count that cannot be cleared costs one silent Stop, never the delivery."""
    try: os.unlink(str(Path(post) / "told" / ("%s.json" % session)))
    except OSError: pass
    except Exception: pass

def wants_answer(items):
    """Which pending items END a wait. An item queued `wake: false` — an at-once
    notice, a notice about a note for the owner, a note for their phone — rides the
    hook roads and rides ALONG with any delivery, but never wakes a session by
    itself. An item with no `wake` key at all is an older item and
    reads exactly as it did.

    A LETTER wakes only when it ASKS — its own line is tested here,
    so a letter queued by an older postman is judged the same.
    NOTICES NEVER WAKE: the postman's
    `not read yet` / `has now been read` notices are FYI-class — they wait in the
    pending file and the window reads them at its next turn start.

    A SEND ORDER NEVER WAKES: an order to push a letter into an attended
    window rides only a turn its carrier is taking anyway — its hooks, its next prompt —
    so a window that is waiting is never woken (and never spends a turn) to carry it. The
    postman queues it `wake: false`; an order queued before that is judged by its kind
    here. A letter a push that landed has CLOSED (its resolved tail) never wakes either."""
    out = []
    for i in items:
        if i.get("fyi") or not i.get("wake", True):
            continue
        if (i.get("kind") or "letter") in ("notice", "send"):
            continue
        if (i.get("kind") or "letter") == "letter" and is_resolved(i.get("line") or ""):
            continue
        if (i.get("kind") or "letter") == "letter" and (i.get("quiet") or is_quiet(i.get("line") or "")):
            continue
        if (i.get("kind") or "letter") == "letter" and alarm_rang_out(i.get("line") or ""):
            continue                       #  an alarm past its reset never ends a wait
        out.append(i)
    return out

_USAGE = [None, False]          # tools/usage.py, loaded once per process (or None)
_WAIT_MODEL = [""]              # the model the waiter's own verdict read
USAGE_RECHECK_S = 60            # a listener re-reads the meter at most once a minute


def usage_recheck_s():
    """How often an armed --wait or --watch re-reads the usage meter: once a
    minute. EXO_USAGE_RECHECK_S is a gate's seam — a fixture flips a meter and
    must not sit through a minute to see the listener answer — and is unset in
    service; anything but a positive number is the minute."""
    try:
        said = float(os.environ.get("EXO_USAGE_RECHECK_S") or USAGE_RECHECK_S)
    except ValueError:
        return USAGE_RECHECK_S
    return said if said > 0 else USAGE_RECHECK_S


def usage_module():
    """tools/usage.py beside this file, loaded once per process — None when it is not
    there or does not load (the postman loads it the same way, as its sibling)."""
    if not _USAGE[1]:
        _USAGE[1] = True
        try:
            import importlib.util
            path = Path(__file__).resolve().parent / "usage.py"
            if path.is_file():
                spec = importlib.util.spec_from_file_location("exo_usage_mail", str(path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _USAGE[0] = mod
        except Exception:
            _USAGE[0] = None
    return _USAGE[0]


def usage_pause(hub, model):
    """The PAUSE line for a window on `model`, or '' — read from the
    meter file by tools/usage.py beside this file. No usage.py, an unreadable
    meter or any error: '' (no meter is never a pause)."""
    if usage_module() is None:
        return ""
    try:
        return _USAGE[0].pause_for_model(str(hub), model or None)
    except Exception:
        return ""

def refuse_or_arm(to, title, hub, pm, force=False, model_hint=None):
    """R1 + R2, asked BEFORE anything is armed: None to arm, else the
    ONE line the waiter prints instead. Every refusal and every --force is one
    line in the postman's waits.jsonl with the title, the model and the time."""
    who = session_identity()
    machine_word = machine()
    desk = "%s/%s" % (machine_word, getattr(pm, "DESK_LANE", "Exocortex-Desk")) if pm else \
        "%s/Exocortex-Desk" % machine_word
    if pm is None or not hasattr(pm, "wait_verdict"):
        verdict = {"refuse": True, "model": "", "why": "no postman beside mail.py to read this "
                   "window's model — never arm blind", "missing": False, "cfg": {}}
    else:
        verdict = pm.wait_verdict(hub, title=title or "", session=who.get("session") or "")
    model = str(verdict.get("model") or "")
    hint = str(model_hint or "").strip()
    if hint and not verdict.get("refuse") and model and hint.lower() not in model.lower():
        verdict = dict(verdict, refuse=True,
                       why="--model says %s but this window's transcript ran on %s" % (hint, model))
    _WAIT_MODEL[0] = model
    if not verdict.get("refuse"):
        paused = usage_pause(hub, model)       # nothing waits under a usage PAUSE
        if paused:
            verdict = dict(verdict, refuse=True, why=paused.split(" · ")[0], usage=True)
    row = {"title": str(title or ""), "session": who.get("session") or "", "model": model,
           "percent": verdict.get("percent"), "why": verdict.get("why") or "", "to": str(to)}
    if not verdict.get("refuse"):
        if verdict.get("missing") and pm is not None and hasattr(pm, "defaults_said"):
            print(pm.defaults_said(verdict.get("cfg") or {}), flush=True)
        return None
    post = pm_post(pm, hub) if pm is not None else None
    if force:
        row["verdict"] = "forced"
        if post is not None: pm.log_wait(post, row)
        print("wait FORCED past its refusal (%s) — logged" % row["why"], flush=True)
        return None
    row["verdict"] = "refused"
    if post is not None: pm.log_wait(post, row)
    if verdict.get("usage"):
        return ("wait refused (%s): continue, or button up? (say either in your window) — "
                "under a usage PAUSE letters wait for a window's next turn start" % row["why"])
    return (getattr(pm, "REFUSE_LINE", None) or "wait refused (%s): retire instead: write your "
            "carryover and retitle ARCH — or hand your waiting to the Desk (%s)") % (row["why"], desk)

def wait(to, title=None, max_hours=12.0, hub=None, poll=3.0, force=False, model_hint=None):
    """Poll only this session's own pending file — one local stat, no git and no
    INBOX parse — and EXIT the moment a letter that wants an answer is there.
    FYI lines alone never end it.

    WITHOUT A SESSION IDENTITY it never guesses which session it is: it says
    so in one line and behaves as a one-shot
    --watch for its address instead.

    WITH A STALE POSTMAN (no pass for ten minutes) it degrades to the postman-less
    road for its own address — its own bounded pull, its own read of INBOX —
    and still delivers. The old road is the floor, never the ceiling.

    IT ENDS ONLY ON TODAY'S MAIL : on both roads a letter whose own date is
    before the day the wait was armed is QUIET — counted in one line, `N earlier
    letters for <TO> — read them with --read`, left where it is, and it never ends
    the wait. A brain pull that brings last week's mail keeps the window's waiter alive."""
    hub = Path(hub) if hub else HUB
    pm = postman(hub)
    said = refuse_or_arm(to, title, hub, pm, force=force, model_hint=model_hint)
    if said:
        print(said, flush=True)                    # ONE line, exit 0, no loop
        return 0
    who = session_identity()
    session = who.get("session") or ""
    if pm is None or not session:
        print("wait: this session gives no id in its environment — waiting as a one-shot "
              "watch for %s instead (it ends at the first letter)" % to, flush=True)
        return wait_as_watch(to, title, max_hours, hub)
    post = pm_post(pm, hub)
    seen = set(addressed(to))                      # the snapshot is the mark — taken BEFORE the ear and the
    arm_day = datetime.date.today().isoformat()    # arm line, so a letter written after either is new by construction
    write_ear(hub, to, title, 60, how="wait")
    touch_alive(post, session)                     # armed now, not one poll from now
    print(f"waiting for {to} · this session · exits at the first letter that wants an answer"
          + (f" · ends when '{title}' is off" if title else "")
          + f" · at most {max_hours:g} h", flush=True)
    started = time.time(); last_ear = started; last_degraded = 0.0; last_alive = started
    paused, last_pause = "", 0.0
    earlier_told = set()                           # (arm_day, what counts as today's mail — set above)
    stop_mark = Path(post) / "waiters" / ("%s.stop" % session)
    try:
        while True:
            time.sleep(poll)
            if stop_mark.exists():                 # the pause-stop word (tools/pause.py) — end at once
                try: os.unlink(str(stop_mark))
                except OSError: pass
                print("wait ended: pause-stop", flush=True)
                return 0                           # the finally below drops the alive mark
            report = {}
            try:
                items = pm.take_pending(post, session, report=report)
            except TypeError:                  # a postman from before 
                try: items = pm.take_pending(post, session)
                except Exception: items = []
            except Exception:
                items = []
            old = [i for i in items if (i.get("kind") or "letter") == "letter"
                   and dated_before(i.get("line") or "", arm_day)]
            if old:
                items = [i for i in items if i not in old]
                say_earlier(old, earlier_told, to)
            if time.time() - last_pause >= usage_recheck_s():
                last_pause = time.time()       # the meter, read at most once a minute
                now_paused = usage_pause(hub, _WAIT_MODEL[0])
                if now_paused and not paused:
                    print("%s — letters now wait for this window's next turn start" % now_paused,
                          flush=True)
                paused = now_paused
            if paused:
                items = []                     # under PAUSE no letter summons: the turn start carries it
            if items and wants_answer(items):
                deliver(items, pm, post, session, road="waiter", skipped=report)
                return 0
            now_t = time.time()
            if now_t - last_alive >= ALIVE_TOUCH_S:
                touch_alive(post, session); last_alive = now_t
            if now_t - last_ear >= 60:                 # the ear, at most once a minute
                write_ear(hub, to, title, 60, how="wait"); last_ear = now_t
            age = None
            try: age = pm.heartbeat_age(post)
            except Exception: pass
            if (age is None or age > 600) and now_t - last_degraded >= FLOOR_EVERY_S:
                last_degraded = now_t                  # the floor: yesterday's road, for this address
                sync("pull")
                fresh = [l for l in undelivered(to, hub) if l not in seen]
                for l in fresh:
                    seen.add(l)
                old = [l for l in fresh if dated_before(l, arm_day)]   #  the pull's old mail
                if old:
                    fresh = [l for l in fresh if l not in old]
                    say_earlier([{"token": token(l)} for l in old], earlier_told, to)
                live = [l for l in fresh if not is_quiet(l)]
                if live:
                    print("the postman has not passed for a while — carrying these myself", flush=True)
                    for l in fresh: print(f"MAIL for {to}: {l}", "[%s]" % shown_token(l, to), flush=True)
                    return 0
            if title:
                live_titles = stamp_titles(hub)
                if live_titles is not None and title.strip() not in live_titles:
                    print(f"wait ended: {title} is off", flush=True); return 0
            if (now_t - started) / 3600.0 >= max_hours:
                print("wait ended after %g h — arm it again" % max_hours, flush=True); return 0
    finally:
        drop_alive(post, session)                  # EVERY exit path, delivery included
        if time.time() - started >= ALIVE_LIVED_S:
            drop_told(post, session)               # …and a waiter that LIVED answered the tell

FLOOR_EVERY_S = 150    # the floor road's own pull, at most this often (a gate's driver may lower it)

def say_earlier(old, told, to):
    """ ONE line for letters dated before the wait was armed — counted, never
    carried, never a wake. Each token is counted once, so a pull that brings the same old
    mail again says nothing."""
    new = [i for i in old if i.get("token") not in told]
    if not new: return
    told.update(i.get("token") for i in new)
    one = len(new) == 1
    print("%d earlier letter%s for %s — read %s with --read"
          % (len(new), "" if one else "s", to, "it" if one else "them"), flush=True)

def wait_as_watch(to, title, max_hours, hub):
    """No identity: one poll loop on this address alone, ending at the first
    letter that wants an answer. It never guesses a session."""
    started = time.time()
    seen = set(addressed(to))
    arm_day = datetime.date.today().isoformat()
    earlier_told = set()
    write_ear(hub, to, title, 150, how="wait")
    while True:
        time.sleep(15)
        sync("pull")
        write_ear(hub, to, title, 150, how="wait")
        fresh = [l for l in undelivered(to, hub) if l not in seen]
        for l in fresh: seen.add(l)
        old = [l for l in fresh if dated_before(l, arm_day)]           # 
        if old:
            fresh = [l for l in fresh if l not in old]
            say_earlier([{"token": token(l)} for l in old], earlier_told, to)
        if [l for l in fresh if not is_quiet(l)]:
            for l in fresh: print(f"MAIL for {to}: {l}", "[%s]" % shown_token(l, to), flush=True)
            return 0
        if title:
            live = stamp_titles(hub)
            if live is not None and title.strip() not in live:
                print(f"wait ended: {title} is off", flush=True); return 0
        if (time.time() - started) / 3600.0 >= max_hours:
            print("wait ended after %g h — arm it again" % max_hours, flush=True); return 0

# ---------------------------------------------------------------------------
# THE ACK — the owner said "got it", in any session, and the note stops waiting
# ---------------------------------------------------------------------------

def ack(which, title=None, hub=None):
    """`--ack OWNER` clears every note for the owner still waiting; `--ack <token>`
    clears one. A note acked on ANY machine is acked on all, because every
    machine's pass reads every machine's post file. INBOX.md is never rewritten
    for it — the mailbox stays append-only in fact."""
    hub = Path(hub) if hub else HUB
    pm = postman(hub)
    if pm is None:
        print("nothing to ack — no postman on this machine"); return 0
    try:
        rows = pm.owner_rows(hub)
    except Exception:
        rows = []
    waiting = [r["token"] for r in rows]
    want = str(which or "OWNER").strip()
    everyone = is_owner_token(_reg(), want) or want.upper() == "OWNER"
    # A SINGLE TOKEN IS CHECKED BEFORE IT BECOMES A FILE NAME: `--ack ../../x`
    # must never write <post>/acks/../../x.json, and `--ack hello` must never
    # answer `acked: 1 note(s)`. It must BE a token — the postman's own one
    # rule, `pm-` or `nd-` and twelve hex — and be one of the notes that are
    # waiting; anything else writes nothing and says so. `--ack OWNER` counts
    # DISTINCT tokens, one row per note however many machines have seen it.
    try:
        shaped = bool(pm.is_note_token(want))
    except Exception:
        shaped = False
    if everyone:
        tokens = list(waiting)
    elif shaped and want in waiting:
        tokens = [want]
    else:
        tokens = []
    if not tokens:
        print("nothing to ack"); return 0
    who = title or os.environ.get("EXO_SESSION_TITLE", "") or session_identity().get("session", "")
    post = pm_post(pm, hub)
    when = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    done = 0
    for tok in tokens:
        try:
            pm.write_json_atomic(Path(post) / "acks" / ("%s.json" % tok),
                                 {"token": tok, "when": when, "by": str(who)})
            done += 1
        except Exception as exc:
            print("not acked %s (%s)" % (tok, exc))
    if not done:
        print("nothing to ack"); return 0
    print("acked: %d note(s) for %s" % (done, owner_label()))
    return 0

def status(which=None, hub=None):
    """Every waiting letter, both directions, each with its why."""
    hub = Path(hub) if hub else HUB
    pm = postman(hub)
    if pm is None:
        todo = undelivered(which, hub) if which and "/" in str(which) else []
        for l in todo: print("waiting ·", l, "[%s]" % token(l))
        print("mail: %d waiting · 0 read today · no postman on this machine — letters "
              "wait for a --read" % len(todo))
        return 0
    for line in pm.cmd_status(hub, pm_post(pm, hub), which or None): print(line)
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--send", nargs=4, metavar=("TO", "TARGET", "TEXT", "ACTION")); ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--read"); ap.add_argument("--mark"); ap.add_argument("--watch"); ap.add_argument("--every", type=int, default=150)
    ap.add_argument("--announce"); ap.add_argument("--target", default="Exocortex"); ap.add_argument("--action", default=FYI)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--inbox"); ap.add_argument("--hub"); ap.add_argument("--title")
    ap.add_argument("--wait"); ap.add_argument("--max-hours", type=float, default=12.0)
    ap.add_argument("--model"); ap.add_argument("--force", action="store_true")   # a hint that must agree; the owner's override — --wait's and --watch's
    ap.add_argument("--status", nargs="?", const="", default=None)
    ap.add_argument("--ack", nargs="?", const="OWNER", default=None)
    ap.add_argument("--no-pull", action="store_true"); ap.add_argument("--help", action="store_true")
    ap.add_argument("--all", action="store_true")    # --read also lists what it hid, and why
    ap.add_argument("--for-the-user", action="store_true")   # --read prints for the person, not the session
    ap.add_argument("--lint-reply")                          # exit 1 if a reply aims mail words at the user
    a = ap.parse_args()
    if a.hub: HUB = Path(a.hub).resolve(); INBOX = HUB / "INBOX.md"
    if a.inbox: INBOX = Path(a.inbox)
    if a.help or not (a.send or a.read or a.watch or a.announce or a.wait or a.lint_reply
                      or a.status is not None or a.ack is not None):
        print(__doc__); sys.exit(0)
    if a.lint_reply: sys.exit(lint_reply(a.lint_reply))
    if a.for_the_user and not a.read:
        print("--for-the-user goes with --read TO"); sys.exit(2)
    if a.send: send(*a.send, push=not a.no_push, hub=HUB)
    elif a.read and a.for_the_user: read_for_the_user(a.read, a.mark, title=a.title, every=a.every, hub=HUB)
    elif a.read: read(a.read, a.mark, title=a.title, every=a.every, hub=HUB, show_all=a.all)
    elif a.announce: sys.exit(announce(a.announce, a.target, a.action, quiet=a.quiet))
    elif a.watch:
        # the floor road obeys --wait's refusal, with --wait's own two flags.
        sys.exit(watch(a.watch, a.every, title=a.title, hub=HUB, pull=not a.no_pull,
                       force=a.force, model_hint=a.model) or 0)
    elif a.wait:
        # the model is READ from this
        # window's own transcript (refuse_or_arm, inside wait()); --model is a hint that must agree with it,
        # and --force is the owner's own override, logged.
        sys.exit(wait(a.wait, title=a.title, max_hours=a.max_hours, hub=HUB,
                      force=a.force, model_hint=a.model))
    elif a.status is not None: sys.exit(status(a.status or None, hub=HUB))
    elif a.ack is not None: sys.exit(ack(a.ack, title=a.title, hub=HUB))
