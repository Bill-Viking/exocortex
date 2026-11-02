#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""usage.py — the usage monitor: the exocortex watches the meter and stops itself.

No model and no network, ever. Every number carries its read time; a stale meter
says its age, never a remembered percent; an unreadable meter says 'not readable'.

    usage.py --write --vendor claude [--login EMAIL]   stdin: the get_usage JSON (a session's road)
    usage.py --write --vendor claude --scan [--budget-seconds S] [--all]
                                                       the newest get_usage result in this machine's
                                                       transcripts (no model: any session that called
                                                       get_usage left its reading in its own transcript);
                                                       the tail of each, none older than 7 days unless
                                                       --all; past S seconds (20) it stops with one line
    usage.py --write --vendor codex | grok             from the vendor's own store (the pulse's road)
    usage.py --beat                                    the pulse: all three roads + last_24h, when the
                                                       writer flag is on here (usage.py --install)
    usage.py --line  --vendor claude [--model ID] [--login EMAIL]
                                                       the turn-start line(s) of THAT login's meter;
                                                       below WARN the one state line — the
                                                       hook itself still says nothing below WARN
    usage.py --check --vendor claude [--model ID] [--login EMAIL]
                                                       exit 1 and one line under PAUSE or STOP, else exit 0
    usage.py --report [--since ISO | --hours N] [--vendor claude|codex|grok|all]
                      [--by session|model|hour] [--raw] [--session ID|WORDS] [--machine NAME]
                                                       what ran and what it cost, sums checkable by hand
    usage.py --status                                  every meter file here, its age and its windows
    usage.py --announce [--vendor claude] [--notify CMD]
                                                       the hub's wake: under a PAUSE, ONE desktop notice
                                                       (the question) and ONE <MACHINE>/all letter per
                                                       onset; at a WARN crossing ONE notice, no letter
                                                       (the hook does the same, once)
    usage.py --continue [--vendor claude] [--by "<session title>"] [--until ISO]
                                                       the owner said «continue»: a signed override past
                                                       the pause line until the window resets,
                                                       including past STOP (unattended flagship work still stops);
                                                       prints the dollars line FIRST, then the state line
    usage.py --manual on | off                         the manual pause, without editing JSON (one line)
    usage.py --install [--dry] | --uninstall [--dry]   the pulse's writer flag (machine-personal)
    usage.py --routine-step FILE... [--apply | --remove]
                                                       the routines' first step (optional belt: the
                                                       effort hook's scheduled-run block is the road)
    common: [--hub DIR] [--now ISO]

THE METER FILE — usage-<machine>-<vendor>-<login>.json in the hub folder (brain-synced,
machine-owned), written whole (temp file + rename) or not at all:
  {vendor, machine, login, login_source, account (the first eight hex of the account
   that owns the reading, when known), read_at, source, windows: [{label, percent, resets_at,
   kind, model}], spend, meter, accounting: {last_24h}, pause_announced_at, pause_announced_key,
   warn_announced_at, warn_announced_key, continue_expired: {key, lines, at},
   continue_expired_said_key, stop_window (the crossed flagship week, until reset),
   auto_pause_window (the window that crossed auto_pause_percent, until its reset),
   auto_announced_key / auto_announced_at, auto_lifted_window / auto_lifted_key}

THE SETTINGS — usage-settings.json in the hub folder, THE USER'S FILE (other tools keep their own
keys in it, untouched here). Missing = the defaults below, said once at the first read.
Two keys the tool itself writes, whole-file and in the file's own key order:
`overrides` — [{vendor, window_label, resets_at, until, by, at, percent_at, spend_at}], one per
window the owner said «continue» for, pruned by evaluate() once its `until` has come — and
`manual_pause_at`, stamped by `--manual on` so each manual pause is its own onset.

THE GATE ASKS. Under a PAUSE the turn-start line and the onset letter are a QUESTION
that names both answers — «continue» (work on until the reset; the extra-usage dollars, or that
extra usage is OFF and continuing spends nothing) or «button up» (the hub buttons up now) — and
the onset raises ONE desktop notice through the postman's notifier seam (`raise_note`, bounded,
fire-and-forget from a hook). The turn-start line alone ends with what a session does with
either word. An override is honoured through evaluate() alone: a PAUSE hit on an overridden
window is level `continued`, pause False, so every road that reads the verdict carries on
without a change of its own; a WARN on another window still rides its own line after it.

WARN, NEVER BLOCK. stop_percent defaults to 92 (per_vendor may override
it). The registry's flagship week and the crossed stop_window remain meter history
until reset. evaluate retains the stop verdict for unattended callers. On every
attended prompt effort.py instead carries ONE warning with percent, reset, login,
read age, cost words and the two choices, and admits the prompt. A person's first
whole-prompt «continue», «continue at my risk» or «take risks and continue» at or
past the flagship pause line records the signed override through edit_settings;
no command needs to be run by the session. --continue records past STOP too.
A stale provisional sign-in still says refresh. An applicable unexpired PAUSE
signature admits unattended work through the ordinary verdict. At flagship STOP,
unattended flagship or unknown-model work stops regardless of a signature.

AUTO-PAUSE. auto_pause_percent defaults to 97 (per_vendor may override it; null
turns the watch off). Plan windows only (5h, week, week-model) can latch it; spend
never does. A window without a reset cannot latch. store_meter keeps the crossed
auto_pause_window until reset, including after a lower or conflicting reading;
a newer reset releases it. ensure_auto still records the latch for the cheap
mind's button-up. A typed prompt gets AUTO-PAUSE as context and runs; unattended
frames, background work and the postman's button-up retain their pause roads.
The verdict always
carries the contract fields: auto_pause (bool), auto_key (`<label>|<resets_at>`), auto_window
({label, percent, kind, resets_at}), auto_resets (local ISO), auto_login, auto_line,
auto_lifted_key, auto_lifted_line, refresh_every (turns between refresh nags: refresh_turns_pause
= 2 at or above PAUSE, refresh_turns = 10 below) and refresh_line (set at pause, continued and
auto-pause only when the reading is 5 or more minutes old). The onset raises its own ONE
notice (title `Exocortex · auto-pause`, once per auto_announced_key) and NO letter — part B tells
the windows; a reset that lifts a latch raises one `AUTO-PAUSE lifted` notice (auto_lifted_key).

ONE LOGIN, ONE METER. A reading belongs to the login it was taken under, and every line
names that login and its read age. A reader reads ONLY its own login's file (newest_meter never
crosses logins): the hook passes the window's own login, every other caller (the postman, the
waiter, the wake) the login the app runs it under. A file older than stale_minutes, another
login's, `unknown`, or none at all says `refresh` in place of every percent:
    USAGE · <login> (<source>) · refresh (read 4 h ago by outlook) — call get_usage, then
    usage.py --write --vendor claude
and a fresh one, below WARN, says (to --line and the wake screen's receipts; one copy):
    USAGE · <login> (<source>) · Fable 9 % · all 6 % · read 3 min ago

THE LOGIN THE DESKTOP APP IS SIGNED IN AS. <home>/.claude.json is the TERMINAL CLI's
login, not the app's: the app may run every window as one account while that file names
another. ONE resolver, app_account(), says which login and where it read it, in this order:
  window   inside an app window of THIS home — its own CLAUDE_CODE_ACCOUNT_UUID and
           CLAUDE_CODE_USER_EMAIL, believed only when this home's app holds that account (a
           window's variables reach every child, a gate's world with another HOME included);
  app      the app's own config.json (macOS <home>/Library/Application Support/Claude, Windows
           %APPDATA%\\Claude) → lastKnownAccountUuid, the ONE key read, its email through the
           logins map — the account alone when nothing names it, never another account's email;
  cli      <home>/.claude.json oauthAccount (emailAddress, accountUuid — two non-secret fields),
           printed `(cli config — not the app's)` wherever it shows;
  unknown  nothing readable.
THE LOGINS MAP, logins-<machine>.json in the hub (brain-synced beside the meter files):
{"<account8>": {"login", "seen", "by": "window env"}} — written ONLY from a window's own variables,
never from .claude.json. A window's login (session_login) is its variables first, then its
transcript's bridge-session owner — unless that owner is the cli config's account while the app
is signed in as another: the bridge record is written under the terminal's login — then the
app's config, then the cli config, each named; a SCAN of another window's transcript is that
transcript's believable owner or `unknown`, never the scanning window's. Every line says the
source in one word, and a meter file's `login_source` opens with it. A PAUSE reaches only its
own login's windows and routines (reaches(): a reading that records its account, that account
alone). The scan walks newest-written first, the last TAIL_BYTES of each
transcript (once more at SCAN_TAIL_MAX when that held no result), none unwritten for 7 days
unless --all, stops at the first usable get_usage result and at --budget-seconds (20) with one
line — never a hang; on stderr a progress line every 30 s and one line per file over 50 MiB.

Paths come from the machine record through tools/exo_paths.py; the machine-personal state (the
transcript cursors, the pulse's writer flag) lives under <home>/.exocortex/usage, never synced.
Stdlib only. macOS and Windows. Output is plain text, <= 88 columns, no emoji.
"""
import io
import json
import os
import stat
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True

TOOL_VERSION = "0.1"
SETTINGS_FILE = "usage-settings.json"
METER_PREFIX = "usage-"
STATE_ENV = "EXO_USAGE_STATE_DIR"
WRITER_FLAG = "pulse-writer.on"

DEFAULTS = {
    "warn_percent": 80,
    "pause_percent": 90,
    "stop_percent": 92,
    "flagship_stop_policy": None,
    # ANY plan window at this percent pauses the login's windows until its reset, and
    # no «continue» lifts it (per_vendor may override it; null turns the watch off)
    "auto_pause_percent": 97,
    # None = follow pause_scope (a string, or a dict per window kind merged over it)
    "auto_pause_scope": None,
    "stale_minutes": 30,
    "refresh_turns": 10,
    # at or above PAUSE the refresh nag rides this often, so a 97 watch is never blind
    "refresh_turns_pause": 2,
    "per_vendor": {"anthropic": {}, "openai": {}, "grok": {"week_spend_limit_usd": None}},
    # A Fable-week PAUSE pauses the Fable windows and lets the cheap hands carry;
    # every other window's PAUSE pauses everything. The owner's `pause everything` = "all".
    "pause_scope": {"week-model": "model", "week": "all", "5h": "all", "month-spend": "all",
                    "week-spend": "all"},
    "manual_pause": False,
    "manual_pause_at": None,
    # the owner's «continue», one per window, honoured until the window resets
    "overrides": [],
    # the effort hook blocks a SCHEDULED run's prompt under a PAUSE that applies to its
    # model: the run ends before its first model call
    "block_routines": True,
    # list $ per 1M tokens, by model-id prefix — an ESTIMATE shown as such; a model with
    # no row shows no dollar. Seeded from the vendors' published list rates (Anthropic's
    # official table); the user's file may replace or extend it.
    "prices": {
        "claude-fable-":  {"input": 10.00, "cache_write": 12.50, "cache_read": 0.25, "output": 50.00},
        "claude-opus-5":  {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00},
        "claude-sonnet-5": {"input": 2.00, "cache_write": 2.50, "cache_read": 0.20, "output": 10.00},
        "claude-haiku-4": {"input": 1.00, "cache_write": 1.25, "cache_read": 0.10, "output": 5.00},
    },
}
VENDOR_FAMILY = {"claude": "anthropic", "codex": "openai", "grok": "grok"}
VENDOR_WORD = {"claude": "Claude", "codex": "Codex", "grok": "Grok"}
# Grok Build's own docs (~/.grok/docs/user-guide/17-sessions.md, `grok usage`):
# "`costUsdTicks` is 10^10 ticks per USD (divide by `1e10` for dollars)" — and the
# headless example beside it: 0.01268905 USD = 126890500 ticks.
GROK_TICKS_PER_USD = 1e10
TAIL_BYTES = 262144
FIRST_READ_CAP = 8 << 20          # a transcript seen for the first time: its last 8 MB
LINE_CAP = 16 << 20
ACCOUNT_HOURS = 24
ACCOUNT_REFRESH_S = 900           # last_24h is refreshed at most every 15 minutes

# THE GATE ASKS. Under a PAUSE the line is a question with both answers named;
# the owner answers in a window and the session carries the word — «continue» runs
# `usage.py --continue`, «button up» the standing button-up. A manual pause keeps its
# own line: «continue» never lifts it.
PAUSE_TAIL = "continue, or button up?"
BUTTON_UP_WORDS = "the hub buttons up now"
NO_FIGURE = "no extra-usage figure on this meter"
# A meter whose extra usage is switched off says what that means.
OFF_FIGURE = ("extra usage is OFF — past 100 percent this model stops until the reset; "
              "continuing spends nothing")
# The TURN-START line (never the notice, never the letter) ends
# with what a session does with either word.
SESSION_TAIL = ("a session hearing «continue» runs usage.py --continue --by \"<its title>\" and "
                "answers with its two lines; hearing «button up» it runs the button-up")
MANUAL_TAIL = "say «button up», or lift it: usage.py --manual off"
PING_TITLE = "Exocortex · usage gate"
AUTO_TITLE = "Exocortex · auto-pause"                 # the auto-pause notice's own title
REFRESH_HOW = {"claude": "call get_usage — the meter files itself from your transcript",
               "codex": "it is re-read from the rollouts at the Codex session's next turn on this machine",
               "grok": "the pulse re-reads usage.json"}
NO_METER_LINE = ("USAGE METER — none on this machine yet · call get_usage once; the meter files "
                 "itself from your transcript")
# what a refresh line tells a session to do, per vendor
REFRESH_DO = {"claude": "call get_usage, then usage.py --write --vendor claude",
              "codex": "it is re-read from the rollouts at the Codex session's next turn on this machine",
              "grok": "the pulse re-reads usage.json"}
UNKNOWN_LOGIN = "unknown"
ACCOUNT_CHARS = 8                 # an account uuid is kept as its first eight hex, never whole
ANNOUNCE_ACTION = "answer in your window: continue, or button up"
MANUAL_ACTION = "answer in your window: button up, or lift it: usage.py --manual off"

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


# ==========================================================================
# small plumbing
# ==========================================================================

def now_local(now=None):
    if now is not None:
        return now
    return datetime.now().astimezone()


def parse_iso(text):
    if not text:
        return None
    s = str(text).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return d


def iso(d):
    return d.astimezone().replace(microsecond=0).isoformat()


def read_json(path, default=None, cap=4 << 20):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.loads(fh.read(cap))
    except (OSError, ValueError):
        return default


def write_atomic(path, obj):
    """Whole or not at all: a temp file beside it, then a rename."""
    path = str(path)
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, path)


_RECORDS = {}


def paths_record(hub=None):
    """{hub, machine, roots} from the machine record, through the resolver — read once per
    process for the same hub and the same record (a hook asks more than once)."""
    key = (str(hub or ""), os.environ.get("EXO_MACHINE_JSON") or "",
           os.environ.get("HOME") or "", os.environ.get("USERPROFILE") or "")
    if key in _RECORDS:
        got = _RECORDS[key]
        return {"hub": got["hub"], "machine": got["machine"], "roots": dict(got["roots"])}
    rec = _paths_record(hub)
    _RECORDS[key] = rec
    return {"hub": rec["hub"], "machine": rec["machine"], "roots": dict(rec["roots"])}


def _paths_record(hub=None):
    here = os.path.dirname(os.path.abspath(__file__))
    rec = {"hub": hub or os.path.dirname(here), "machine": "", "roots": {}}
    try:
        if here not in sys.path:
            sys.path.insert(0, here)
        from exo_paths import paths as _paths
        p = _paths(tool_file=__file__)
        rec["machine"] = str(p.get("machine") or "").lower()
        rec["roots"] = dict(p.get("roots") or {})
        if not hub:
            rec["hub"] = str(rec["roots"].get("orchestrator") or p.get("hub") or rec["hub"])
    except Exception:
        pass
    if not rec["machine"]:
        rec["machine"] = "machine"
    return rec


def state_dir(roots):
    forced = os.environ.get(STATE_ENV, "").strip()
    if forced:
        return forced
    if roots.get("usage_state"):
        return str(roots["usage_state"])
    home = roots.get("home") or os.path.expanduser("~")
    return os.path.join(str(home), ".exocortex", "usage")


def safe_login(login):
    s = str(login or "default").strip().lower().replace("@", "-at-")
    out = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in s)
    return out.strip("-.") or "default"


def meter_name(machine, vendor, login):
    return "%s%s-%s-%s.json" % (METER_PREFIX, str(machine).lower(), vendor, safe_login(login))


def when_word(d, now=None):
    """`Sat 21:00`, or `21:00` when it is today — the local clock, the weekday
    computed from the date and never from memory."""
    if d is None:
        return "?"
    d = d.astimezone()
    n = now_local(now)
    if d.date() == n.date():
        return d.strftime("%H:%M")
    return d.strftime("%a %H:%M")


def minutes_between(a, b):
    return (b - a).total_seconds() / 60.0


# ==========================================================================
# the settings — the user's file
# ==========================================================================

_SAID = []


def load_settings(hub):
    """(cfg, missing). Our keys only, every default filled; any other key in the
    file is left exactly as it is by every road here."""
    cfg = json.loads(json.dumps(DEFAULTS))
    d = read_json(os.path.join(str(hub), SETTINGS_FILE), None)
    if not isinstance(d, dict):
        return cfg, True
    for key in ("warn_percent", "pause_percent", "stop_percent", "stale_minutes", "refresh_turns",
                "refresh_turns_pause"):
        try:
            if d.get(key) is not None:
                cfg[key] = float(d[key])
        except (TypeError, ValueError):
            pass
    if "auto_pause_percent" in d:                 # null is a setting — the watch is off
        if d["auto_pause_percent"] is None:
            cfg["auto_pause_percent"] = None
        else:
            try:
                cfg["auto_pause_percent"] = float(d["auto_pause_percent"])
            except (TypeError, ValueError):
                pass
    ascope = d.get("auto_pause_scope")
    if isinstance(ascope, str):
        cfg["auto_pause_scope"] = ascope
    elif isinstance(ascope, dict):
        cfg["auto_pause_scope"] = dict((str(k), str(v)) for k, v in ascope.items())
    if isinstance(d.get("per_vendor"), dict):
        for fam, over in d["per_vendor"].items():
            if isinstance(over, dict):
                cfg["per_vendor"].setdefault(str(fam), {}).update(over)
    scope = d.get("pause_scope")
    if isinstance(scope, str):
        cfg["pause_scope"] = scope
    elif isinstance(scope, dict):
        cfg["pause_scope"].update(dict((str(k), str(v)) for k, v in scope.items()))
    for key in ("manual_pause", "block_routines"):
        if key in d:
            cfg[key] = bool(d[key])
    if d.get("manual_pause_at"):
        cfg["manual_pause_at"] = str(d["manual_pause_at"])
    if isinstance(d.get("overrides"), list):
        cfg["overrides"] = [o for o in d["overrides"] if isinstance(o, dict)]
    if "flagship_stop_policy" in d:
        cfg["flagship_stop_policy"] = d["flagship_stop_policy"]
    if isinstance(d.get("prices"), dict):
        cfg["prices"].update(d["prices"])
    return cfg, False


def defaults_line(cfg):
    auto = cfg.get("auto_pause_percent")
    return ("usage-settings.json has no usage keys yet — defaults: WARN %g percent · PAUSE %g percent"
            " · STOP %g percent · AUTO-PAUSE %s · stale after %g min" % (
                cfg["warn_percent"], cfg["pause_percent"], cfg["stop_percent"],
                ("%g percent" % auto) if auto is not None else "off", cfg["stale_minutes"]))


def thresholds(cfg, vendor):
    over = (cfg.get("per_vendor") or {}).get(VENDOR_FAMILY.get(vendor, vendor)) or {}
    warn = over.get("warn_percent", cfg["warn_percent"])
    pause = over.get("pause_percent", cfg["pause_percent"])
    try:
        return float(warn), float(pause)
    except (TypeError, ValueError):
        return float(cfg["warn_percent"]), float(cfg["pause_percent"])


def scope_of(cfg, kind):
    scope = cfg.get("pause_scope")
    if isinstance(scope, str):
        return "all" if scope.strip().lower() == "all" else "model"
    return str((scope or {}).get(kind) or "all").strip().lower()


def applies(cfg, window, model):
    """Does this window's line reach a window running `model`? A model-scoped
    window reaches the windows on its own model; an UNKNOWN model is reached —
    a window whose model cannot be read is never assumed to be the cheap one."""
    if scope_of(cfg, window.get("kind") or "") != "model":
        return True
    family = str(window.get("model") or "").lower()
    if not family or not model:
        return True
    return family in str(model).lower()


def flagship_name(hub, vendor, model):
    """Resolve a product id, CLI word or persona through the registered flagship.

    Do not use mind_name(kind): a vendor-wide persona can also name its cheaper
    models. Only the row's own identifiers and aliases identify its flagship.
    """
    from exo_registry import registry, mind_alias, family_word
    reg = registry(hub)
    word = str(model or "").strip().lower().split("[", 1)[0]
    if not word:
        return ""
    tokens = {mind_alias(reg, word), mind_alias(reg, family_word(word, vendor))}
    for row in reg["minds"]:
        if row.get("kind") != vendor or row.get("tier") != "flagship":
            continue
        name = mind_alias(reg, row["name"])
        ids = [row.get("app_id"), row.get("cli"),
               (row.get("models") or {}).get("flagship")]
        if name in tokens or any(word == str(i).lower() for i in ids if i):
            return name
    return ""


def hard_stop(hub, vendor, data, cfg, n):
    """The unreset flagship week wins over manual pause, stale age and overrides.
    Reading this verdict writes nothing, including on a refused --continue.
    """
    over = (cfg.get("per_vendor") or {}).get(VENDOR_FAMILY.get(vendor, vendor)) or {}
    try:
        stop = float(over.get("stop_percent", cfg.get("stop_percent", 92)))
        if not 0 <= stop <= 100:
            stop = 92
    except (TypeError, ValueError):
        stop = 92
    hits = []
    latched = (data or {}).get("stop_window")
    windows = list((data or {}).get("windows") or [])
    if isinstance(latched, dict):
        windows.insert(0, latched)
    for w in windows:
        if not isinstance(w, dict) or w.get("kind") != "week-model":
            continue
        name = flagship_name(hub, vendor, w.get("model"))
        if not name and not w.get("model"):
            for word in str(w.get("label") or "").split():
                name = flagship_name(hub, vendor, word)
                if name:
                    break
        reset = parse_iso(w.get("resets_at"))
        if not name or (reset is not None and reset <= n):
            continue
        try:
            pct = float(w.get("percent"))
        except (TypeError, ValueError):
            continue
        if w is latched or pct >= stop:
            line = ("%s HARD STOP — %s percent of the week · resets %s · "
                    "no %s turn runs; cheaper windows carry on") % (
                        name, pct_word(pct), when_word(reset, n), name.capitalize())
            hits.append((pct, w, line, name))
    return max(hits, key=lambda h: h[0]) if hits else None


def confirm_policy(cfg, vendor):
    """An attributed opt-in to ask before crossing the flagship stop, or None."""
    p = cfg.get("flagship_stop_policy")
    if (not isinstance(p, dict) or p.get("mode") != "confirm" or
            ("vendor" in p and p["vendor"] != vendor) or
            not all(isinstance(p.get(k), str) and p[k].strip() for k in ("by", "reason")) or
            not isinstance(p.get("at"), str) or parse_iso(p["at"]) is None):
        return None
    return p


# --------------------------------------------------------------------------
# part A — the auto-pause watch: any plan window at auto_pause_percent
# --------------------------------------------------------------------------

REFRESH_MIN_AGE = 5.0                    # minutes: a reading younger than this needs no refresh nag
AUTO_KINDS = ("5h", "week", "week-model")     # plan percent windows only; never a spend window
AUTO_SLACK = timedelta(minutes=10)       # inclusive reset-window identity tolerance; never expiry grace


def auto_threshold(cfg, vendor):
    """auto_pause_percent for `vendor` (a per_vendor row may override it), or None = watch off."""
    over = (cfg.get("per_vendor") or {}).get(VENDOR_FAMILY.get(vendor, vendor)) or {}
    raw = over["auto_pause_percent"] if "auto_pause_percent" in over else cfg.get("auto_pause_percent", 97)
    if raw is None:
        return None
    try:
        got = float(raw)
    except (TypeError, ValueError):
        return 97.0
    return got if 0 <= got <= 100 else 97.0


def auto_scope_of(cfg, kind):
    """The auto watch's scope for a window kind: its own setting, else pause_scope's."""
    scope = cfg.get("auto_pause_scope")
    if scope is None:
        return scope_of(cfg, kind)
    if isinstance(scope, str):
        return "all" if scope.strip().lower() == "all" else "model"
    got = (scope or {}).get(kind)
    return str(got).strip().lower() if got else scope_of(cfg, kind)


def auto_applies(cfg, window, model):
    """applies() under the auto scope: a model-scoped window reaches its own model's windows;
    an unknown model is reached."""
    if auto_scope_of(cfg, window.get("kind") or "") != "model":
        return True
    family = str(window.get("model") or "").lower()
    if not family or not model:
        return True
    return family in str(model).lower()


def auto_key_of(w):
    return "%s|%s" % (w.get("label"), w.get("resets_at"))


def auto_latch_ended(latched, windows, n):
    """True when a latched window is over: its reset has come, or the meter now shows the same
    window with a different reset (rolled to a newer one, or a reading that puts it already past):
    the newest reading's word about the window's reset wins and clears the old latch."""
    reset = parse_iso((latched or {}).get("resets_at"))
    if reset is None or reset <= n:
        return True
    for w in windows or []:
        if isinstance(w, dict) and w.get("label") == latched.get("label"):
            other = parse_iso(w.get("resets_at"))
            if other is not None and abs(other - reset) > AUTO_SLACK:
                return True
    return False


def auto_find(data, cfg, vendor, model, n):
    """(window, percent) of the auto-pause window for a caller running `model`, or None. The
    latched window (live, not rolled) comes first, then the first window of the meter at or
    over auto_pause_percent whose reset has not come; a window with no reset time cannot be
    latched and is not watched."""
    thr = auto_threshold(cfg, vendor)
    if thr is None or not isinstance(data, dict):
        return None
    windows = [w for w in (data.get("windows") or []) if isinstance(w, dict)]
    latched = data.get("auto_pause_window")
    cands = []
    if isinstance(latched, dict) and latched.get("kind") in AUTO_KINDS and not auto_latch_ended(latched, windows, n):
        try:
            pct = float(latched.get("percent"))
        except (TypeError, ValueError):
            pct = thr
        for w in windows:                             # the same window read again, higher
            try:
                if (w.get("label") == latched.get("label")
                        and parse_iso(w.get("resets_at")) is not None
                        and same_reset(w.get("resets_at"), latched.get("resets_at"))):
                    pct = max(pct, float(w.get("percent")))
            except (TypeError, ValueError, AttributeError):
                pass
        cands.append((latched, pct))
    for w in windows:
        try:
            pct = float(w.get("percent"))
        except (TypeError, ValueError):
            continue
        reset = parse_iso(w.get("resets_at"))
        if w.get("kind") not in AUTO_KINDS or reset is None or reset <= n or pct < thr:
            continue
        cands.append((w, pct))
    for w, pct in cands:
        if auto_applies(cfg, w, model):
            return w, pct
    return None


def auto_lifted(data, cfg, vendor, n):
    """(key, label) of a latched auto-pause that ended and was not yet announced, or None."""
    if not isinstance(data, dict) or auto_threshold(cfg, vendor) is None:
        return None
    windows = [w for w in (data.get("windows") or []) if isinstance(w, dict)]
    cand = data.get("auto_pause_window")
    if not (isinstance(cand, dict) and auto_latch_ended(cand, windows, n)):
        cand = data.get("auto_lifted_window")
    if not isinstance(cand, dict):
        return None
    key = auto_key_of(cand)
    if data.get("auto_lifted_key") == key:
        return None
    return key, str(cand.get("label") or "")


def auto_line_of(w, pct, login, n, cfg):
    reset = parse_iso(w.get("resets_at"))
    who = "every window"
    if auto_scope_of(cfg, w.get("kind") or "") == "model" and w.get("model"):
        who = "every %s window" % str(w["model"]).capitalize()
    return "AUTO-PAUSE — %s %s percent (%s) · resets %s · %s of this login pauses · lifts at the reset" % (
        w.get("label"), pct_word(pct), login, when_word(reset, n), who)


def auto_store(old, body, cfg, vendor, n):
    """(latch, pending_lift) for the meter file about to be written. The latch is the old live
    one, else the first window of the new reading at or over the line; an old latch that ended
    leaves its window as `auto_lifted_window` until the lifted notice is marked."""
    thr = auto_threshold(cfg, vendor)
    if thr is None:
        return None, None
    windows = [w for w in (body.get("windows") or []) if isinstance(w, dict)]
    latch, lifted = None, None
    old_latch = (old or {}).get("auto_pause_window")
    if isinstance(old_latch, dict):
        if auto_latch_ended(old_latch, windows, n):
            lifted = old_latch
        else:
            latch = old_latch
    if latch is None:
        for w in windows:
            try:
                pct = float(w.get("percent"))
            except (TypeError, ValueError):
                continue
            reset = parse_iso(w.get("resets_at"))
            if w.get("kind") in AUTO_KINDS and reset is not None and reset > n and pct >= thr:
                latch = {"label": w.get("label"), "percent": pct, "kind": w.get("kind"),
                         "model": w.get("model") or "", "resets_at": w.get("resets_at")}
                break
    if lifted is None:
        pend = (old or {}).get("auto_lifted_window")
        if isinstance(pend, dict):
            lifted = pend
    if lifted is not None and body.get("auto_lifted_key") == auto_key_of(lifted):
        lifted = None
    return latch, lifted


def edit_settings(hub, change):
    """The user's file, edited whole: read it, let `change(dict)` set OUR keys,
    write it back (temp file + rename) in the file's own key order, so every other key —
    another tool's — rides through exactly as it was. A file that is there but is not a
    JSON object is NEVER written over. Returns 'written' | 'same' | 'unreadable'."""
    path = os.path.join(str(hub), SETTINGS_FILE)
    raw = {}
    if os.path.exists(path):
        got = read_json(path, None)
        if not isinstance(got, dict):
            return "unreadable"
        raw = got
    before = json.dumps(raw, sort_keys=True)
    change(raw)
    if json.dumps(raw, sort_keys=True) == before:
        return "same"
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(raw, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, path)
    return "written"


def same_reset(a, b):
    """Window identity within AUTO_SLACK, inclusive, comparing parsed instants.
    Two absent values match; malformed nonempty values do not. This is neither
    exact timestamp equality nor an extension of any stored signature expiry.
    """
    da, db = parse_iso(a), parse_iso(b)
    if da is None or db is None:
        return da is None and db is None and not a and not b
    return abs(da - db) <= AUTO_SLACK


def is_vendor(o, vendor):
    return str(o.get("vendor") or "claude").lower() == str(vendor).lower()


def override_for(overrides, vendor, window, now):
    """The unexpired override that answers `window` of `vendor`, or None: the same label
    AND the same reset — the next week is a new window, so a «continue» never carries
    past its own reset. An override whose `until` does not read is never honoured."""
    for o in overrides or []:
        if not isinstance(o, dict) or not is_vendor(o, vendor):
            continue
        if str(o.get("window_label") or "") != str(window.get("label") or ""):
            continue
        if not same_reset(o.get("resets_at"), window.get("resets_at")):
            continue
        until = parse_iso(o.get("until"))
        if until is not None and until > now:
            return o
    return None


def owner_word(hub):
    """How the lines name the person: the registry's owner name, else 'the owner' —
    nothing about one fleet is typed in here."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        from exo_registry import registry, owner_label
        return owner_label(registry(hub)) or "the owner"
    except Exception:
        return "the owner"


def money(value):
    """'10.45', '40' — a whole amount without its cents; None when it is not a number."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return ("%d" % int(round(f))) if abs(f - round(f)) < 0.005 else ("%.2f" % f)


def dollars(spend, short=False):
    """The extra-usage clause from the meter's own `spend` bytes, or '' when it carries no
    figure: `extra usage so far $10.45 of $40 this month` (short: `extra usage $10.45 of
    $40`). A vendor's own rolling spend (Grok's) says its own window, never 'this month'.
    A meter whose extra usage is switched OFF (`enabled: false`) says so, long or short:
    continuing spends nothing and the model stops at 100 percent."""
    if isinstance(spend, dict) and spend.get("enabled") is False:
        return OFF_FIGURE
    if not isinstance(spend, dict) or spend.get("spent") in (None, ""):
        return ""
    cur = str(spend.get("currency") or "").strip().upper()

    def amount(v):
        m = money(v)
        if m is None:
            return None
        return ("$%s" % m) if cur in ("", "USD") else ("%s %s" % (m, cur))
    spent = amount(spend.get("spent"))
    if spent is None:
        return ""
    limit = amount(spend.get("limit")) if spend.get("limit") not in (None, "") else None
    of = (" of %s" % limit) if limit else ""
    if spend.get("window"):
        return ("spend %s%s" if short else "spend so far %s%s, %s") % (
            (spent, of) if short else (spent, of, spend["window"]))
    return ("extra usage %s%s" % (spent, of)) if short else \
        ("extra usage so far %s%s this month" % (spent, of))


def question_words(spend, reset):
    """The question and both answers, in the owner's own two words."""
    carry = "work on until the reset" if reset is not None else "work on"
    return "%s · say «continue» (%s; %s) or «button up» (%s)" % (
        PAUSE_TAIL, carry, dollars(spend) or NO_FIGURE, BUTTON_UP_WORDS)


def age_words(age):
    if age is None:
        return "read ?"
    return "read just now" if age < 1 else "read %d min ago" % int(age)


def ago_words(age):
    """The read age for a refresh line: `3 min`, `4 h`, `2 d` — never a clock."""
    if age is None:
        return "?"
    if age < 1:
        return "just now"
    if age < 120:
        return "%d min ago" % int(age)
    if age < 48 * 60:
        return "%d h ago" % int(age // 60)
    return "%d d ago" % int(age // (24 * 60))


def reset_words(w, reset, n):
    if reset is None:
        return ""
    if w.get("kind") in ("week", "week-model"):
        return "the week resets %s" % when_word(reset, n)
    return "resets %s" % when_word(reset, n)


def who_word(by, width=28):
    """A session title on a band: its ACT/ARCH tag off, cut to `width`."""
    t = str(by or "").strip()
    for tag in ("ARCH \u2014 ", "ACT \u2014 ", "HARV \u2014 ", "ARCH - ", "ACT - "):
        if t.startswith(tag):
            t = t[len(tag):]
            break
    return cut(t, width) if t else "a session"


def pct_word(value):
    try:
        return "%d" % int(round(float(value)))
    except (TypeError, ValueError):
        return "?"


# ==========================================================================
# the meter files
# ==========================================================================

def classify(label):
    """(kind, model family) from the app's own label."""
    low = str(label or "").lower()
    if "5-hour" in low or "5 hour" in low or "5h" == low:
        return "5h", ""
    if low.startswith("weekly"):
        rest = low.split("·", 1)[1].strip() if "·" in low else low[6:].strip(" -:")
        if not rest or rest.startswith("all"):
            return "week", ""
        return "week-model", rest.split()[0]
    return "other", ""


def windows_from_get_usage(obj):
    """(windows, spend, plan) from the get_usage JSON — or ([], None, '') when
    this is not one."""
    if not isinstance(obj, dict):
        return [], None, ""
    plan = obj.get("plan") if isinstance(obj.get("plan"), dict) else obj
    wins = plan.get("windows") if isinstance(plan, dict) else None
    if not isinstance(wins, list):
        return [], None, ""
    out = []
    for w in wins:
        if not isinstance(w, dict):
            continue
        kind, fam = classify(w.get("label"))
        try:
            pct = float(w.get("percentUsed"))
        except (TypeError, ValueError):
            continue
        at = parse_iso(w.get("resetsAt"))
        out.append({"label": str(w.get("label") or kind), "percent": pct, "kind": kind,
                    "model": fam, "resets_at": iso(at) if at else None})
    spend = None
    extra = plan.get("extraUsage") if isinstance(plan, dict) else None
    if isinstance(extra, dict):
        spend = {"spent": extra.get("spent"), "limit": extra.get("monthlyLimit"),
                 "currency": extra.get("currency") or "", "enabled": extra.get("enabled")}
        try:
            pct = float(extra.get("percentUsed"))
            out.append({"label": "extra usage (month)", "percent": pct, "kind": "month-spend",
                        "model": "", "resets_at": None})
        except (TypeError, ValueError):
            pass
    return out, spend, str(plan.get("plan") or "") if isinstance(plan, dict) else ""


def meters(hub, machine=None, vendor=None):
    """[(path, data)] of every meter file in the hub, newest read first."""
    out = []
    try:
        names = os.listdir(str(hub))
    except OSError:
        return out
    for name in names:
        if not (name.startswith(METER_PREFIX) and name.endswith(".json")) or name == SETTINGS_FILE:
            continue
        data = read_json(os.path.join(str(hub), name), None, cap=1 << 20)
        if not isinstance(data, dict) or not data.get("vendor"):
            continue
        if machine and str(data.get("machine") or "").lower() != str(machine).lower():
            continue
        if vendor and data.get("vendor") != vendor:
            continue
        when = parse_iso(data.get("read_at"))
        out.append((when, os.path.join(str(hub), name), data))
    out.sort(key=lambda t: (t[0] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return [(p, d) for _w, p, d in out]


def same_login(a, b):
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def reaches(data, account):
    """A meter's lines — its PAUSE above all — reach a window or a routine of its
    OWN account only. A reading that records its account (`account`, first eight) reaches that
    account alone; one that records none is matched by its login (newest_meter), never across
    logins; an unread account is matched by login alone. The model half is applies()."""
    mine = account8((data or {}).get("account"))
    acct = account8(account)
    return not mine or not acct or mine == acct


def newest_meter(hub, machine, vendor, login=None, account=None):
    """The newest meter of `vendor` on `machine` — and, given a login, THAT login's newest
    and no other. `unknown` is nobody's login: it
    names a reading whose owner could not be read, so it is never returned for a login —
    but a reader whose ACCOUNT is known while no login names it yet (the app's
    config read, the logins map empty) reads the file that recorded that account. Given an
    account, a file that recorded ANOTHER account is never returned (reaches)."""
    got = meters(hub, machine, vendor)
    acct = account8(account)
    if login is not None:
        if same_login(login, UNKNOWN_LOGIN) or not str(login).strip():
            if not acct:
                return (None, None)
            got = [(p, d) for p, d in got if account8(d.get("account")) == acct
                   and not same_login(d.get("login"), UNKNOWN_LOGIN)]
        else:
            got = [(p, d) for p, d in got if same_login(d.get("login"), login)]
    if acct:
        got = [(p, d) for p, d in got if reaches(d, acct)]
    return got[0] if got else (None, None)


CARRIED = ("pause_announced_at", "pause_announced_key", "warn_announced_at", "warn_announced_key",
           "continue_expired", "continue_expired_said_key", "accounting",
           "auto_announced_key", "auto_announced_at", "auto_lifted_key")


def store_meter(hub, body, keep_newer=True, tail_conflict=False):
    """Write one meter file whole. A reading OLDER than the file already there
    is never written over it; the announce marks and the accounting ride along.
    Returns (path, 'written' | 'same' | 'older').
    tail_conflict replaces contradictory file latches only for a verified own-tail
    conflict; ordinary newer/lower readings retain the existing latch rules."""
    path = os.path.join(str(hub), meter_name(body["machine"], body["vendor"], body["login"]))
    old = read_json(path, None)
    if isinstance(old, dict):
        new_at, old_at = parse_iso(body.get("read_at")), parse_iso(old.get("read_at"))
        if keep_newer and new_at and old_at and new_at < old_at:
            return path, "older"
        for key in CARRIED:
            if key in old and key not in body:
                body[key] = old[key]
    cfg, _missing = load_settings(hub)
    n = now_local()
    # Only contradicted latch windows are superseded. Manual pause, overrides,
    # and every unrelated plan-window latch retain their existing policy.
    history = old
    if tail_conflict and isinstance(old, dict):
        def contradicted(window):
            return bool(tail_meter_conflict(body, dict(old, windows=[window])))
        history = dict(old)
        history["windows"] = [w for w in old.get("windows") or [] if not contradicted(w)]
        # R12: a tail conflict never deletes the plan pause latch. auto_store
        # retains it until the established reset/rollover rule releases it.
        for key in ("stop_window",):
            if isinstance(history.get(key), dict) and contradicted(history[key]):
                history.pop(key)
    # The existing meter is the durable record, not a second state store. A
    # lower read, a changed setting or a continue cannot clear a crossed week.
    stopped = hard_stop(hub, body["vendor"], history, cfg, n) if isinstance(history, dict) else None
    if stopped:
        # A crossed week latches until ITS reset — but a reading whose same-labelled
        # window carries a LATER reset says the week rolled (or the old latch was another
        # account's, filed here by the old resolver): the old latch is released, the new
        # reading judged on its own. A lower reading within the same-window tolerance
        # cannot clear it. The original latched reset stays fixed; wobble never renews it.
        _w = stopped[1] if isinstance(stopped[1], dict) else {}
        _same = [w for w in (body.get("windows") or []) if isinstance(w, dict)
                 and w.get("label") == _w.get("label")]
        _old_at, _new_at = parse_iso(_w.get("resets_at")), parse_iso((_same or [{}])[0].get("resets_at"))
        if (_old_at and _new_at and _new_at > _old_at
                and not same_reset(_w.get("resets_at"), (_same or [{}])[0].get("resets_at"))):
            stopped = None
    stopped = stopped or hard_stop(hub, body["vendor"], body, cfg, n)
    if stopped:
        body["stop_window"] = dict(stopped[1])
    else:
        body.pop("stop_window", None)
    # the auto-pause latch — the stop_window pattern. A crossed window stays until its
    # reset; a lower or older reading cannot clear it; one from a newer reset releases it.
    latch, lifted = auto_store(history if isinstance(history, dict) else None, body, cfg, body["vendor"], n)
    if latch:
        body["auto_pause_window"] = dict(latch)
    else:
        body.pop("auto_pause_window", None)
    if lifted:
        body["auto_lifted_window"] = dict(lifted)
    else:
        body.pop("auto_lifted_window", None)
    if isinstance(old, dict) and dict(old) == dict(body):
        return path, "same"
    write_atomic(path, body)
    return path, "written"


def base_body(machine, vendor, login, login_source, read_at, source):
    return {"vendor": vendor, "machine": str(machine).lower(), "login": str(login or "default"),
            "login_source": login_source, "read_at": iso(read_at), "source": source,
            "windows": [], "spend": None, "meter": "readable", "tool": "usage.py " + TOOL_VERSION}


# ==========================================================================
# THE LOGIN THE DESKTOP APP IS SIGNED IN AS: one resolver, the logins
# map, and a window's login
# ==========================================================================

ENV_ACCOUNT = "CLAUDE_CODE_ACCOUNT_UUID"      # the app sets these on every window it starts
ENV_EMAIL = "CLAUDE_CODE_USER_EMAIL"
ENV_SESSION = "CLAUDE_CODE_SESSION_ID"
APP_FOLDER = "Claude"
APP_CONFIG = "config.json"                    # the app's own; ONE key is read: lastKnownAccountUuid
APP_STORE = "claude-code-sessions"            # one folder per account the app has signed in as
LOGINS_PREFIX = "logins-"
LEARN_EVERY_S = 3600                          # a known pair's `seen` is refreshed at most hourly
SOURCE_WORDS = {"window": "window", "app": "app", "cli": "cli config — not the app's",
                "transcript": "transcript", "--login": "--login", "given": "given"}
_SOURCE_OF = {}                               # login → (word, account) session_login last read


def home_of(roots):
    return str((roots or {}).get("home") or os.path.expanduser("~"))


def _inside(path, folder):
    try:
        a = os.path.normcase(os.path.abspath(str(path)))
        b = os.path.normcase(os.path.abspath(str(folder)))
    except (TypeError, ValueError):
        return False
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def app_dirs(roots, env=None):
    """The desktop app's data folders under THIS home, in the order tried: macOS
    <home>/Library/Application Support/Claude; Windows %APPDATA%\\Claude — APPDATA taken only
    when it lies inside this home (a variable naming another home's folder, as in a gate's
    world, is that home's) — else <home>/AppData/Roaming/Claude, the Windows default; a machine
    record's own `appdata` root, when it names one, before both. The same folders
    tools/app_sessions.py and tools/routine-check.py read the app's stores from."""
    env = os.environ if env is None else env
    home = home_of(roots)
    found = [os.path.join(home, "Library", "Application Support", APP_FOLDER)]
    if (roots or {}).get("appdata"):               # a machine record that names it says so
        found.append(os.path.join(str(roots["appdata"]), APP_FOLDER))
    appdata = str(env.get("APPDATA") or "").strip()
    if appdata and _inside(appdata, home):
        found.append(os.path.join(appdata, APP_FOLDER))
    found.append(os.path.join(home, "AppData", "Roaming", APP_FOLDER))
    out, seen = [], set()
    for folder in found:
        key = os.path.normcase(os.path.abspath(folder))
        if key not in seen:
            seen.add(key)
            out.append(folder)
    return out


def account8(value):
    """An account id as it is kept: its first eight characters, lowercase; '' for nothing."""
    s = str(value or "").strip().lower()
    if not s or "/" in s or "\\" in s:
        return ""
    return s[:ACCOUNT_CHARS]


def app_config_account(roots, env=None):
    """(account8, path) the app's own config.json names — `lastKnownAccountUuid`, the ONE key
    read and nothing else of the file kept; ('', '') when no app config here names one."""
    for folder in app_dirs(roots, env):
        path = os.path.join(folder, APP_CONFIG)
        if not os.path.isfile(path):
            continue
        d = read_json(path, None, cap=1 << 20)
        acct = account8(d.get("lastKnownAccountUuid")) if isinstance(d, dict) else ""
        if acct:
            return acct, path
    return "", ""


def app_holds(roots, account, env=None):
    """Does the app on THIS home hold `account`? Its config names it, or its session store
    keeps a folder for it — the app makes one per account it signs in as, and every one of
    that account's windows has its record there."""
    acct = account8(account)
    if not acct:
        return False
    if app_config_account(roots, env)[0] == acct:
        return True
    for folder in app_dirs(roots, env):
        store = os.path.join(folder, APP_STORE)
        try:
            names = os.listdir(store)
        except OSError:
            continue
        if any(account8(n) == acct and os.path.isdir(os.path.join(store, n)) for n in names):
            return True
    return False


def cli_account(roots):
    """(email, account8) of the TERMINAL CLI's own login — two non-secret fields of
    <home>/.claude.json's oauthAccount (emailAddress, accountUuid); ('', '') when unread.
    NOT the desktop app's login (the app may run its windows as one account
    while this file names another). Nothing else of the file is read."""
    d = read_json(os.path.join(home_of(roots), ".claude.json"), None, cap=8 << 20)
    try:
        oa = (d or {}).get("oauthAccount") or {}
        return str(oa.get("emailAddress") or ""), account8(oa.get("accountUuid"))
    except AttributeError:
        return "", ""


def window_env(roots, env=None):
    """(email, account8) when this process runs inside a desktop-app window OF THIS HOME: the
    window's own variables (CLAUDE_CODE_ACCOUNT_UUID, CLAUDE_CODE_USER_EMAIL), believed only
    when this home's app holds that account (app_holds); ('', '') otherwise. A window's
    variables reach every child it starts — a gate's world with another HOME included — and an
    account this home's app does not hold is another home's, never this one's."""
    env = os.environ if env is None else env
    acct = account8(env.get(ENV_ACCOUNT))
    if not acct or not app_holds(roots, acct, env):
        return "", ""
    return str(env.get(ENV_EMAIL) or "").strip(), acct


def logins_name(machine):
    return "%s%s.json" % (LOGINS_PREFIX, str(machine or "machine").lower())


def logins_maps(hub):
    """[(path, map)] — every logins-<machine>.json in the hub (any machine's: an account's
    email is the same everywhere)."""
    out = []
    if not hub:
        return out
    try:
        names = sorted(os.listdir(str(hub)))
    except OSError:
        return out
    for name in names:
        if name.startswith(LOGINS_PREFIX) and name.endswith(".json"):
            d = read_json(os.path.join(str(hub), name), None, cap=1 << 20)
            if isinstance(d, dict):
                out.append((os.path.join(str(hub), name), d))
    return out


def learned(hub, acct=None, login=None):
    """The newest-seen row of any logins map for `acct` (or naming `login`):
    (account8, login, seen datetime or None, path) or None."""
    best = None
    for path, d in logins_maps(hub):
        for key, row in d.items():
            if not isinstance(row, dict) or not row.get("login"):
                continue
            if acct and account8(key) != acct:
                continue
            if login and not same_login(row.get("login"), login):
                continue
            seen = parse_iso(row.get("seen"))
            if best is None or (seen is not None and (best[2] is None or seen > best[2])):
                best = (account8(key), str(row["login"]), seen, path)
    return best


def learn_login(hub, acct, email, now=None):
    """Record `acct` → `email` in THIS machine's logins map — ONLY ever from a window's own
    variables (window_env), never from .claude.json — when no map knows the pair or it was last
    seen over an hour ago. Whole file or nothing; a map that is there but is not a JSON object
    is never written over. Returns the path written, else ''. Never raises."""
    try:
        acct = account8(acct)
        if not hub or not acct or not email or not os.path.isdir(str(hub)):
            return ""
        n = now_local(now)
        got = learned(hub, acct=acct)
        if got and same_login(got[1], email) and got[2] is not None \
                and abs((n - got[2]).total_seconds()) < LEARN_EVERY_S:
            return ""
        path = os.path.join(str(hub), logins_name(paths_record(str(hub))["machine"]))
        d = {}
        if os.path.exists(path):
            d = read_json(path, None, cap=1 << 20)
            if not isinstance(d, dict):
                return ""
        d[acct] = {"login": str(email), "seen": iso(n), "by": "window env"}
        write_atomic(path, d)
        return path
    except Exception:
        return ""


def email_of(hub, roots, acct):
    """(login, how) for an account's first eight: the logins map (what windows said), else
    .claude.json when it names that very account (a true pair, whoever is signed in where),
    else a meter file that recorded it; ('', why) when nothing here names it."""
    acct = account8(acct)
    if not acct:
        return "", "no account"
    got = learned(hub, acct=acct)
    if got:
        return got[1], "the logins map"
    email, mine = cli_account(roots)
    if email and mine == acct:
        return email, ".claude.json"
    for _p, d in (meters(hub, None, "claude") if hub else []):
        if account8(d.get("account")) == acct and d.get("login") \
                and not same_login(d.get("login"), UNKNOWN_LOGIN):
            return str(d["login"]), "a meter file's account"
    return "", ("account %s is named by no logins map, no .claude.json and no meter file here"
                % acct)


def account_of_login(hub, roots, login, env=None):
    """The account a login runs as, first eight, when something here pairs them: this window's
    own variables, the logins map, .claude.json; else ''."""
    email, acct = window_env(roots, env)
    if acct and same_login(email, login):
        return acct
    got = learned(hub, login=login)
    if got:
        return got[0]
    email, acct = cli_account(roots)
    return acct if acct and same_login(email, login) else ""


def app_account(roots, env=None, hub=None, window=True, learn=True):
    """THE ONE RESOLVER: (email, account8, source) of the login the DESKTOP APP
    runs this caller under, in this order:
      window   inside an app window of this home: its own variables (window_env) — and the
               logins map learns the pair (learn_login);
      app      the app's own config.json → lastKnownAccountUuid, its email through email_of —
               the account alone (email '') when nothing names it, NEVER another's email;
      cli      <home>/.claude.json — the TERMINAL's login, shown `(cli config — not the
               app's)` wherever it is printed, never as the app's;
      unknown  nothing readable.
    `hub` is where the logins map lives (default: the record's orchestrator root)."""
    hub = hub or (roots or {}).get("orchestrator") or ""
    if window:
        email, acct = window_env(roots, env)
        if acct:
            if email:
                if learn:
                    learn_login(hub, acct, email)
            else:
                email = email_of(hub, roots, acct)[0]
            return email, acct, "window"
    acct, _path = app_config_account(roots, env)
    if acct:
        return email_of(hub, roots, acct)[0], acct, "app"
    email, acct = cli_account(roots)
    if email or acct:
        return email, acct, "cli"
    return "", "", "unknown"


def claude_account(roots):
    """(email, account8) of the login the desktop app runs this caller under — a thin wrapper
    through app_account ( the window's variables, the app's config, the cli config);
    ('', '') when none reads. app_account also says WHICH road it took."""
    email, acct, _src = app_account(roots)
    return email, acct


def claude_login(roots):
    """The email of claude_account(); '' when unread."""
    return claude_account(roots)[0]


def source_word(how):
    """The one word a login's source opens with: window · app · cli · transcript · --login ·
    given · unknown; '' for words written before ."""
    s = str(how or "").strip()
    word = s.split(" — ", 1)[0].strip().split(" ", 1)[0] if s else ""
    return word if (word in SOURCE_WORDS or word == "unknown") else ""


def login_words(login, how, account=""):
    """`<login> (<source>)` — how every line names a login: `(cli config — not the
    app's)` for the terminal's; a login no map names yet whose account is known is `account
    <first eight> (<source>)`; an unknown login, or a source unread, is the login alone."""
    s = str(login or "").strip() or UNKNOWN_LOGIN
    word = source_word(how)
    if same_login(s, UNKNOWN_LOGIN) and account8(account) and word and word != "unknown":
        return "account %s (%s)" % (account8(account), SOURCE_WORDS.get(word, word))
    if same_login(s, UNKNOWN_LOGIN) or not word or word == "unknown":
        return s
    return "%s (%s)" % (s, SOURCE_WORDS.get(word, word))


def road_how(how, road):
    """A meter file's login_source: the source word first, then the road and its words —
    `window — this session`, `transcript — scan: transcript owner = .claude.json`."""
    word = source_word(how) or "unknown"
    rest = str(how or "").split(" — ", 1)[1].strip() if " — " in str(how or "") else ""
    return "%s — %s%s" % (word, road, (": " + rest) if rest else "")


def transcript_owner(path, cap=TAIL_BYTES):
    """The account that owns a transcript: the `ownerAccountUuid` the app writes on its
    bridge-session records (the newest in the tail, else the head), first eight hex; ''
    when the transcript names none. Bounded reads, never the whole file.
    The record may be written under the TERMINAL CLI's login while the app runs a window
    under another account; owner_believed() checks this distinction."""
    if not path:
        return ""
    try:
        size = os.path.getsize(str(path))
    except OSError:
        return ""
    found = ""
    for start in ((max(0, size - cap), 0) if size > cap else (0,)):
        try:
            with open(str(path), "rb") as fh:
                fh.seek(start)
                raw = fh.read(cap)
        except OSError:
            return ""
        for line in raw.split(b"\n"):
            if b"ownerAccountUuid" not in line:
                continue
            try:
                rec = json.loads(line.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("ownerAccountUuid"):
                found = account8(rec["ownerAccountUuid"])
        if found:
            return found
    return ""


def owner_believed(roots, owner, env=None):
    """(bool, why) — may a transcript's bridge-session owner stand for its window's login? Not
    when it is the cli config's account while the app is signed in as another: then the record
    names the terminal's login, never the app's."""
    # A window's bridge record names the account its process runs as.
    # get_usage inside the window reads THAT account's meter.
    # The app's config names its own sign-in, which can be another account.
    # Using the app account can therefore select the wrong meter.
    # The record identifies the window's account and takes precedence.
    # The output names the account source.
    _email, cli = cli_account(roots)
    app = app_config_account(roots, env)[0]
    if cli and owner == cli and app and app != owner:
        return True, ("its bridge record names %s, the cli config's account, while the app is "
                      "signed in as %s — the record wins (2026-10-27)" % (owner, app))
    return True, ""


def login_of_account(hub, roots, account):
    """(login, how) for an account's first eight, through email_of: the logins map, a
    .claude.json naming that account, a meter file that recorded it; else (unknown, why)."""
    if not account:
        return UNKNOWN_LOGIN, "the transcript names no owner"
    email, how = email_of(hub, roots, account)
    if email:
        return email, "transcript owner = %s" % how
    return UNKNOWN_LOGIN, how


def remember(login, how, account):
    """session_login's answer, kept for this process so a line that names the login later says
    its road (evaluate reads it); returns (login, how, account) unchanged."""
    if login and not same_login(login, UNKNOWN_LOGIN):
        _SOURCE_OF[str(login).strip().lower()] = (source_word(how), account8(account))
    return login, how, account


def session_login(roots, hub, transcript=None, session=None, fallback=True, env=None):
    """(login, how, account) of a window; `how` opens with its source word:
      window      the call runs inside that very window (no transcript or session asked, or the
                  one asked is this process's own CLAUDE_CODE_SESSION_ID) and its variables are
                  this home's app's (window_env) — the logins map learns the pair;
      transcript  the transcript's bridge-session owner, named through the logins map, a
                  .claude.json naming that account, or a meter file — unless it is the cli
                  config's account while the app is signed in as another (owner_believed);
      app / cli   when `fallback` (a window's own road: its hook fires under the app's login):
                  the resolver's later roads, the app's config before the cli config;
      unknown     a SCAN (`fallback` False) whose transcript names no believable owner — the
                  scanning window's own login never stands in for another window's.
    With no transcript: the session id's transcript when one is given."""
    env = os.environ if env is None else env
    if not transcript and session:
        transcript = find_transcript(roots, session)
    own = str(env.get(ENV_SESSION) or "").strip()
    asked = str(session or "").strip()
    if not asked and transcript:
        asked = os.path.basename(str(transcript))[:-6]
    owner = transcript_owner(transcript) if transcript else ""
    if not asked or (own and asked == own):
        email, acct = window_env(roots, env)
        if acct and email:
            learn_login(hub, acct, email)
        # The bridge record's owner is the account this window's process runs as
        # (what get_usage inside it reads); the window's variables name the app's sign-in,
        # which can be another account. The owner wins; the variables stand in only when the
        # transcript names no owner.
        if owner:
            login, how = login_of_account(hub, roots, owner)
            if login and not same_login(login, UNKNOWN_LOGIN):
                return remember(login, "transcript — " + how, owner)
        if acct:
            if not email:
                email = email_of(hub, roots, acct)[0]
            return remember(email or UNKNOWN_LOGIN, "window", acct)
    account = owner
    why = "the transcript names no owner"
    if account:
        ok, why = owner_believed(roots, account, env)
        if ok:
            login, how = login_of_account(hub, roots, account)
            return remember(login, "transcript — " + how, account)
    if transcript and not fallback:
        return UNKNOWN_LOGIN, "unknown — " + why, ""
    email, acct, src = app_account(roots, env, hub=hub, window=False)
    # ASSUMES: a desktop window's billing identity is its bridge owner or app sign-in.
    # Opposite: a home has only a terminal CLI config, naming a foreign account.
    # The CLI config alone is never evidence of the desktop window's account.
    if src == "cli" and env.get("CLAUDE_CODE_ENTRYPOINT") == "claude-desktop":
        return UNKNOWN_LOGIN, "unknown — desktop app sign-in unavailable; CLI config cannot identify a window", ""
    if email:
        return remember(email, src, acct)
    if acct:
        return UNKNOWN_LOGIN, ("unknown — the app is signed in as %s; no logins map here "
                               "names it yet" % acct), acct
    return UNKNOWN_LOGIN, "unknown — no login readable here", ""


def find_transcript(roots, sid):
    """A Claude session's transcript by its id, or ''."""
    base = os.path.join(str(roots.get("claude") or os.path.join(os.path.expanduser("~"), ".claude")),
                        "projects")
    sid = str(sid or "").strip()
    if not sid or "/" in sid or "\\" in sid:
        return ""
    try:
        folders = os.listdir(base)
    except OSError:
        return ""
    for folder in folders:
        path = os.path.join(base, folder, "%s.jsonl" % sid)
        if os.path.isfile(path):
            return path
    return ""


def app_login(roots):
    """The login every caller that is not a window reads for: the app's own login (through
    its config and the logins map), or unknown."""
    return claude_login(roots) or UNKNOWN_LOGIN


def short_login(login, against=()):
    """`you@example.com` → `example`: the word a person calls a login by (its domain's
    first label) — unless a login in `against` shares that word, and then the whole login;
    `unknown` is `an unnamed login`; any other login with no @ is itself."""
    s = str(login or "").strip()
    if not s or same_login(s, UNKNOWN_LOGIN):
        return "an unnamed login"
    if "@" not in s:
        return s

    def word(x):
        x = str(x or "").strip()
        return x.split("@", 1)[1].split(".", 1)[0].lower() if "@" in x else ""
    mine = word(s)
    if not mine or any(word(o) == mine and not same_login(o, s) for o in against):
        return s
    return mine


# ==========================================================================
# ROAD 1 — Claude: the get_usage JSON (stdin), or a transcript that holds one
# ==========================================================================

def get_usage_in_record(rec):
    """The get_usage JSON a transcript record carries as a tool result, or None."""
    if not isinstance(rec, dict) or rec.get("type") != "user":
        return None
    content = ((rec.get("message") or {}).get("content"))
    if not isinstance(content, list):
        return None
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_result":
            continue
        inner = item.get("content")
        texts = []
        if isinstance(inner, str):
            texts.append(inner)
        elif isinstance(inner, list):
            texts.extend(str(x.get("text") or "") for x in inner if isinstance(x, dict))
        for text in texts:
            if "percentUsed" not in text or "windows" not in text:
                continue
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            wins, _spend, _plan = windows_from_get_usage(obj)
            if wins:
                return obj
    return None


def claude_body_from(obj, roots, machine, read_at, source, login=None, how=None, account=""):
    """The reading is filed under the login it was TAKEN under — `login` with its
    `how` when the caller read it (the window, the transcript's owner, --login), else the
    login app_account() resolves,
    else unknown; never `default`, which named nobody. `login_source` opens with its one
    source word."""
    wins, spend, plan = windows_from_get_usage(obj)
    if not wins:
        return None
    if login:
        who, how = login, (how or "--login")
    else:
        who, account, how = app_account(roots)
    body = base_body(machine, "claude", who or UNKNOWN_LOGIN, how, read_at, source)
    if account:
        body["account"] = account8(account)
    body["windows"], body["spend"], body["plan"] = wins, spend, plan
    return body


def claude_files(roots, since_ts=0.0):
    """Every Claude transcript (main + subagents) touched since `since_ts`."""
    base = os.path.join(str(roots.get("claude") or os.path.join(os.path.expanduser("~"), ".claude")),
                        "projects")
    out = []
    try:
        folders = os.listdir(base)
    except OSError:
        return out
    for folder in folders:
        root = os.path.join(base, folder)
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            path = os.path.join(root, name)
            if name.endswith(".jsonl"):
                m = regular_mtime(path)
                if m is not None and m >= since_ts:
                    out.append((path, m, folder, name[:-6], False))
                continue
            sub = os.path.join(path, "subagents")
            if not os.path.isdir(sub):
                continue
            try:
                subs = os.listdir(sub)
            except OSError:
                continue
            for s in subs:
                if not s.endswith(".jsonl"):
                    continue
                sp = os.path.join(sub, s)
                m = regular_mtime(sp)
                if m is not None and m >= since_ts:
                    out.append((sp, m, folder, name, True))
    return out


def regular_mtime(path):
    """A transcript's mtime — None for anything that is not a regular file (a pipe or a
    device named *.jsonl would block the first read: ) or does not stat."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_mtime if stat.S_ISREG(st.st_mode) else None


def claude_title(roots, folder, sid):
    base = os.path.join(str(roots.get("claude") or ""), "projects", folder, sid, "custom-title.json")
    d = read_json(base, None, cap=65536)
    if isinstance(d, dict) and d.get("customTitle"):
        return str(d["customTitle"]).strip()
    return ""


def iter_lines(path, start=0, cap=None):
    """(offset after the line, raw bytes) for each complete line from `start`."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    if cap is not None and size - start > cap:
        start = size - cap
    try:
        fh = open(path, "rb")
    except OSError:
        return
    with fh:
        fh.seek(start)
        if start:
            fh.seek(start - 1)
            if fh.read(1) != b"\n":
                fh.readline()                     # skip the torn first line
        while True:
            raw = fh.readline(LINE_CAP)
            if not raw:
                break
            if not raw.endswith(b"\n"):
                break                             # a line still being written: next time
            yield fh.tell(), raw


SCAN_BUDGET_S = 20.0              # --scan's default --budget-seconds
SCAN_GRACE_S = 2.0                # past budget + grace a read that never returned ends the run
SCAN_TICK_ENV = "EXO_USAGE_SCAN_TICK"   # a gate's seam: virtual seconds added per transcript
SCAN_DAYS = 7                     # a transcript unwritten this long is not read without --all
SCAN_TAIL_MAX = 1 << 20           # when TAIL_BYTES held no result, the tail grows once to this
SCAN_BEAT_S = 30.0                # a progress line this often while the scan runs
SCAN_BIG_BYTES = 50 << 20         # a transcript over this gets its «skipping» line


def size_words(size):
    """`1.2 GB` / `60 MB` — a file's size in the one line a big transcript earns."""
    return "%.1f GB" % (size / float(1 << 30)) if size >= 1 << 30 else "%d MB" % (size >> 20)


def tail_result(path, sid, cap, since=None, until=None):
    """The newest get_usage result in the last `cap` bytes of a transcript, as the scan's
    (obj, timestamp, source, path) — or (None, None, None, None)."""
    best = (None, None, None, None)
    for _off, raw in iter_lines(path, 0, cap=cap):
        if b"percentUsed" not in raw or b"tool_result" not in raw:
            continue
        try:
            rec = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue
        obj = get_usage_in_record(rec)
        when = parse_iso(rec.get("timestamp")) if obj else None
        if (obj and when and (since is None or when >= since) and
                (until is None or when <= until) and (best[1] is None or when > best[1])):
            best = (obj, when, "get_usage in transcript %s" % sid, path)
    return best


def _epoch(x):
    """A file time as seconds since the epoch, from a number or a datetime; None when unreadable."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x.timestamp())
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def scan_claude_for_meter(roots, since_ts=0.0, files=None, budget=None, progress=None, out=None):
    """The newest get_usage result in any transcript touched since `since_ts`:
    (obj, timestamp, source, transcript path) or (None, None, None, None) — the path, so
    the reading is filed under the login that owns THAT transcript.
    Newest-written first, only the tail of each: the tail is TAIL_BYTES, grown
    once to SCAN_TAIL_MAX when it held no result. The walk keeps the NEWEST reading by
    its own timestamp and stops only when the next transcript was written BEFORE that reading
    (a reading is never newer than the file that holds it) — never at the first hit, because
    the newest-written transcript can hold an old reading (a quiet routine window) while a
    less-recently-written one holds the newest, and the hard stop reads the newest.
    With `budget` seconds the walk stops at the first transcript past it.
    `progress`, a dict, is kept current — {n, k, elapsed, stopped, best} — for the stop line and
    the watchdog. `out` (stderr) gets a flushed progress line every SCAN_BEAT_S and one line per
    transcript over SCAN_BIG_BYTES."""
    todo = sorted(files if files is not None else claude_files(roots, since_ts),
                  key=lambda f: f[1], reverse=True)
    prog = progress if progress is not None else {}
    prog.update(n=len(todo), k=0, elapsed=0.0, stopped=False, best=None)
    out = out or sys.stderr
    try:
        tick = max(0.0, float(os.environ.get(SCAN_TICK_ENV) or 0))
    except ValueError:
        tick = 0.0
    t0 = time.monotonic()
    beat = 0.0
    best = (None, None, None, None)

    def say(text):
        try:
            out.write(text + "\n")
            out.flush()
        except (OSError, ValueError):
            pass
    for i, (path, mtime, _folder, sid, _sub) in enumerate(todo):
        prog["elapsed"] = time.monotonic() - t0 + tick * i
        if budget is not None and prog["elapsed"] >= budget:
            prog["stopped"] = True
            break
        if best[1] is not None and _epoch(mtime) is not None and _epoch(mtime) < best[1].timestamp():
            break                 # written before the best reading — cannot hold a newer one
        if prog["elapsed"] - beat >= SCAN_BEAT_S:
            beat = prog["elapsed"]
            say("%d of %d files · newest first · %ds" % (i, len(todo), int(beat)))
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        if size > SCAN_BIG_BYTES:
            say("skipping %s: %s — read the tail only" % (os.path.basename(path), size_words(size)))
        found = tail_result(path, sid, TAIL_BYTES)
        if found[0] is None and size > TAIL_BYTES:
            found = tail_result(path, sid, SCAN_TAIL_MAX)
        if found[0] is not None and (best[1] is None or found[1] > best[1]):
            best = found                          # the newest reading so far, by its own time
        prog["k"] = i + 1
        prog["best"] = best
    prog["elapsed"] = time.monotonic() - t0 + tick * prog["k"]
    prog["best"] = best
    return best


def reading_words(best, n=None):
    """The scan's newest reading so far, in a few words: `07:13 in transcript 99320128 (Fable
    9% · all 6%)`, or `none`."""
    obj, when, _source, path = best if best else (None, None, None, None)
    if obj is None or when is None:
        return "none"
    wins, _spend, _plan = windows_from_get_usage(obj)
    pct = " · ".join("%s %s%%" % (short_name(w), pct_word(w.get("percent"))) for w in wins[:3])
    sid = os.path.basename(str(path or ""))[:-6][:8] or "?"
    return "%s in transcript %s%s" % (when_word(when, n), sid, (" (%s)" % pct) if pct else "")


def stop_line(prog, n=None, tail=""):
    """The scan's one line: `scan stopped at k of N after s s — newest reading so far: …`."""
    return "scan stopped at %d of %d after %.1f s — newest reading so far: %s%s" % (
        int(prog.get("k") or 0), int(prog.get("n") or 0), float(prog.get("elapsed") or 0.0),
        reading_words(prog.get("best"), n), tail)


def scan_watchdog(prog, seconds, out=None, end=None):
    """backstop: a read that never returns (a stalled disk, a file the system must
    fetch first) is past every cooperative check. At `seconds` this daemon timer prints the
    stop line from `prog` — nothing filed — and ends the process, exit 0. Returns the
    started timer; cancel() it when the scan returns."""
    out = out or sys.stdout
    end = end or os._exit
    started = time.monotonic()

    def fire():
        prog["elapsed"] = time.monotonic() - started
        try:
            out.write(stop_line(prog, tail=" · a read did not return; nothing filed") + "\n")
            out.flush()
        finally:
            end(0)
    timer = threading.Timer(seconds, fire)
    timer.daemon = True
    timer.start()
    return timer


def scanned_body(hub, roots, machine, obj, when, source, path):
    """A scanned reading's body, filed under the owner of the transcript it was found in
    — or `unknown` when that transcript names no owner (a scan never assumes the app's
    login: the transcript may be another login's, from before a switch)."""
    login, how, account = session_login(roots, hub, transcript=path, fallback=False)
    return claude_body_from(obj, roots, machine, when, source, login=login,
                            how=road_how(how, "scan"), account=account)


def tail_meter(hub, roots, machine, transcript):
    """Own-tail reading, without filing it. Bounded by TAIL_BYTES, newest timestamp wins."""
    if not transcript:
        return None
    # ASSUMES: first-hand usage remains usable for at most 24 h; future stamps are unread.
    n = now_local()
    obj, when, source, _path = tail_result(
        transcript, os.path.basename(str(transcript))[:-6], TAIL_BYTES,
        since=n - timedelta(hours=24), until=n)
    if obj is None:
        return None
    login, how, account = session_login(roots, hub, transcript=transcript, fallback=True)
    return claude_body_from(obj, roots, machine, when, source, login=login,
                            how=road_how(how, "this window"), account=account)


def tail_meter_conflict(tail, filed, now=None):
    """One metadata finding for the first disagreeing same-labelled window, else None.

    ASSUMES: a tail result is current evidence only within 24 hours, never future-dated.
    ASSUMES: an older tail is history; the newer file wins without a conflict.
    ASSUMES: same-account, same-reset progress can go down; a normal refresh is silent.
    Opposites: stale/future/older tails, two accounts, and a changed reset are gated.
    """
    import math
    if not tail or not filed:
        return None
    n = now_local(now)
    taken, file_at = parse_iso(tail.get("read_at")), parse_iso(filed.get("read_at"))
    if not taken or not file_at or not 0 <= (n - taken).total_seconds() <= 86400 or taken < file_at:
        return None
    ta, fa = account8(tail.get("account")), account8(filed.get("account"))
    same_owner = ta == fa if ta and fa else same_login(tail.get("login"), filed.get("login"))
    for tw in tail.get("windows") or []:
        if not isinstance(tw, dict) or not tw.get("label"):
            continue
        for fw in filed.get("windows") or []:
            if not isinstance(fw, dict) or fw.get("label") != tw["label"]:
                continue
            try:
                tp, fp = float(tw["percent"]), float(fw["percent"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(tp) or not math.isfinite(fp):
                continue
            reset_diff = not same_reset(tw.get("resets_at"), fw.get("resets_at"))
            if not reset_diff and (same_owner or abs(tp - fp) <= 5):
                continue
            return {"quantity": "usage", "label": tw["label"],
                    "reason": "reset differs" if reset_diff else "percent differs by more than 5",
                    "tail": {"login": tail.get("login"), "account": ta, "percent": tp,
                             "read_at": tail["read_at"], "resets_at": tw.get("resets_at")},
                    "file": {"login": filed.get("login"), "account": fa, "percent": fp,
                             "read_at": filed["read_at"], "resets_at": fw.get("resets_at")},
                    "winner": "this window"}
    return None


def conflict_line(conflict, now=None):
    n = now_local(now)
    tail, filed = conflict["tail"], conflict["file"]
    return ("CONFLICT — this window's own reading says %s percent (read %s), "
            "the meter for %s says %s (read %s) — the window's reading wins" %
            (pct_word(tail["percent"]), ago_words(minutes_between(parse_iso(tail["read_at"]), n)),
             filed.get("login") or UNKNOWN_LOGIN, pct_word(filed["percent"]),
             ago_words(minutes_between(parse_iso(filed["read_at"]), n))))


def meter_from_tail(hub, roots, machine, transcript, selected_meter=None, evidence=None):
    """File this window's own reading under session_login. Existing callers keep the path API.

    The hook supplies its pre-import verdict meter, so importing a fresh reading
    cannot erase the disagreement before it is compared. No other account's file
    is searched for a disagreement. Evidence contains metadata only.
    """
    body = tail_meter(hub, roots, machine, transcript)
    if body is None:
        return ""
    conflict = tail_meter_conflict(body, selected_meter)
    if evidence is not None and conflict:
        evidence.update(conflict)
    path, what = store_meter(hub, body, tail_conflict=bool(conflict))
    return path if what == "written" else ""


# ==========================================================================
# ROAD 2 — Codex: the newest token_count event's rate_limits
# ==========================================================================

def codex_rollouts(roots, since_ts=0.0):
    base = os.path.join(str(roots.get("codex") or os.path.join(os.path.expanduser("~"), ".codex")),
                        "sessions")
    out = []
    for folder, _dirs, names in os.walk(base):
        for name in names:
            if name.startswith("rollout-") and name.endswith(".jsonl"):
                p = os.path.join(folder, name)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                if m >= since_ts:
                    out.append((p, m))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def codex_window(block, label_word):
    if not isinstance(block, dict):
        return None
    try:
        pct = float(block.get("used_percent"))
    except (TypeError, ValueError):
        return None
    mins = block.get("window_minutes")
    kind = {10080: "week", 300: "5h"}.get(mins, "other")
    label = {"week": label_word, "5h": "%s 5-hour" % label_word}.get(
        kind, "%s %s-min" % (label_word, mins))
    at = None
    try:
        at = datetime.fromtimestamp(float(block.get("resets_at")), timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        pass
    return {"label": label, "percent": pct, "kind": kind, "model": "",
            "resets_at": iso(at) if at else None}


def codex_meter(roots, machine):
    """(body, note): the newest rate_limits across this machine's rollouts."""
    files = codex_rollouts(roots)
    if not files:
        return None, "codex: no rollouts on this machine — no meter written"
    best = None
    for path, _m in files[:6]:                     # the newest few; the meter is in the newest
        for _off, raw in iter_lines(path, 0, cap=TAIL_BYTES * 4):
            if b'"token_count"' not in raw or b'"rate_limits"' not in raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            pay = rec.get("payload") or {}
            rl = pay.get("rate_limits")
            when = parse_iso(rec.get("timestamp"))
            if not isinstance(rl, dict) or when is None:
                continue
            if best is None or when >= best[0]:
                best = (when, rl, os.path.basename(path))
        if best is not None:
            break
    if best is None:
        return None, "codex: no token_count event with rate_limits — no meter written"
    when, rl, name = best
    body = base_body(machine, "codex", "default", "default (the store's account holds secrets)",
                     when, "codex rollout %s" % name)
    wins = [w for w in (codex_window(rl.get("primary"), "Codex"),
                        codex_window(rl.get("secondary"), "Codex")) if w]
    body["windows"] = wins
    body["plan"] = str(rl.get("plan_type") or "")
    cr = rl.get("credits")
    if isinstance(cr, dict):
        body["spend"] = {"credits": cr.get("balance"), "has_credits": cr.get("has_credits"),
                         "unlimited": cr.get("unlimited")}
    if not wins:
        body["meter"] = "not readable — accounting only"
    return body, ""


# ==========================================================================
# ROAD 3 — Grok: accounting from usage.json (no plan meter in the store)
# ==========================================================================

def grok_usage_files(roots):
    base = os.path.join(str(roots.get("grok") or os.path.join(os.path.expanduser("~"), ".grok")),
                        "sessions")
    out = []
    for folder, _dirs, names in os.walk(base):
        if "usage.json" in names:
            out.append(os.path.join(folder, "usage.json"))
    return out


def grok_turns(roots, since, until=None):
    """[(ended, model, tokens dict, ticks, session id, cwd folder)] for every turn
    that ENDED inside [since, until)."""
    rows = []
    for path in grok_usage_files(roots):
        d = read_json(path, None, cap=8 << 20)
        if not isinstance(d, dict):
            continue
        sid = str(d.get("sessionId") or os.path.basename(os.path.dirname(path)))
        cwd = os.path.basename(os.path.dirname(os.path.dirname(path)))
        for t in d.get("turns") or []:
            if not isinstance(t, dict):
                continue
            ended = parse_iso(t.get("endedAt"))
            if ended is None or ended < since or (until is not None and ended >= until):
                continue
            usage = t.get("modelUsage") if isinstance(t.get("modelUsage"), dict) else {}
            if not usage:
                usage = {str(t.get("primaryModelId") or "grok"): t}
            for model, u in usage.items():
                if not isinstance(u, dict):
                    continue
                rows.append((ended, str(model), u, int(u.get("costUsdTicks") or 0), sid, cwd))
    return rows


def grok_meter(roots, machine, cfg, now=None):
    n = now_local(now)
    week = grok_turns(roots, n - timedelta(days=7))
    newest = max([r[0] for r in week], default=None)
    body = base_body(machine, "grok", "default", "default", newest or n,
                     "grok usage.json x%d" % len(grok_usage_files(roots)))
    ticks = sum(r[3] for r in week)
    usd = ticks / GROK_TICKS_PER_USD
    body["spend"] = {"spent": round(usd, 4), "currency": "USD", "window": "rolling 7 days",
                     "ticks": ticks, "scale": "1e10 ticks per USD (Grok Build docs, `grok usage`)"}
    limit = ((cfg.get("per_vendor") or {}).get("grok") or {}).get("week_spend_limit_usd")
    try:
        limit = float(limit) if limit is not None else None
    except (TypeError, ValueError):
        limit = None
    if limit and limit > 0:
        body["spend"]["limit"] = limit
        body["windows"] = [{"label": "Grok spend (7 days)", "percent": round(100.0 * usd / limit, 1),
                            "kind": "week-spend", "model": "", "resets_at": None}]
        body["meter"] = "readable — spend against your own weekly limit"
    else:
        body["meter"] = "not readable — accounting only"
    body["read_at"] = iso(n)          # the accounting is as of this read
    return body


# ==========================================================================
# THE VERDICT — the line, the pause
# ==========================================================================

def window_words(w, spend=None):
    kind, label = w.get("kind"), str(w.get("label") or "")
    pct = int(round(float(w.get("percent") or 0)))
    if kind == "week-model":
        return "%s %d percent of the week" % ((w.get("model") or label).capitalize(), pct)
    if kind == "week":
        return "%s %d percent of the week" % ("all models" if label.lower().startswith("weekly")
                                              else label, pct)
    if kind == "5h":
        return "%s %d percent" % ("5-hour window" if label.lower().startswith("5") else label, pct)
    if kind == "month-spend":
        extra = ""
        if isinstance(spend, dict) and spend.get("spent") is not None and spend.get("limit"):
            extra = " ($%s of $%s)" % (spend.get("spent"), spend.get("limit"))
        return "extra usage %d percent of the month%s" % (pct, extra)
    if kind == "week-spend":
        extra = ""
        if isinstance(spend, dict) and spend.get("limit"):
            extra = " ($%.2f of $%g)" % (float(spend.get("spent") or 0), float(spend["limit"]))
        return "%s %d percent%s" % (label, pct, extra)
    return "%s %d percent" % (label, pct)


def short_name(w):
    kind = w.get("kind")
    if kind == "week-model":
        return (w.get("model") or "model").capitalize()
    if kind == "week":
        return "all models" if str(w.get("label") or "").lower().startswith("weekly") else \
            str(w.get("label") or "week")
    if kind == "5h":
        return "5-hour window" if str(w.get("label") or "").startswith("5") else \
            str(w.get("label") or "5-hour")
    if kind == "month-spend":
        return "extra usage"
    return str(w.get("label") or kind)


def prune_overrides(hub, cfg, vendor, n, meter_path):
    """EXPIRY: an override of `vendor` whose `until` has come is taken out of
    the settings file — ONE whole-file write, and only when one expired — and its words
    are left in this machine's meter file for the next turn start to say ONCE
    (notes_once). Returns the overrides still honoured. Never raises."""
    live, gone = [], []
    for o in cfg.get("overrides") or []:
        until = parse_iso(o.get("until"))
        if is_vendor(o, vendor) and until is not None and until <= n:
            gone.append(o)
        else:
            live.append(o)
    if not gone:
        return live

    def change(raw):
        kept = []
        for o in raw.get("overrides") or []:
            if isinstance(o, dict) and is_vendor(o, vendor):
                until = parse_iso(o.get("until"))
                if until is not None and until <= n:
                    continue
            kept.append(o)
        raw["overrides"] = kept
    try:
        edit_settings(hub, change)
    except Exception:
        pass
    cfg["overrides"] = live
    try:
        data = read_json(meter_path, None) if meter_path else None
        if isinstance(data, dict):
            key = " + ".join(sorted("%s|%s|%s" % (o.get("window_label"), o.get("resets_at"), o.get("at"))
                                    for o in gone))
            data["continue_expired"] = {"key": key, "lines": [expiry_line(o, n) for o in gone],
                                        "at": iso(n)}
            write_atomic(meter_path, data)
    except Exception:
        pass
    return live


def expiry_line(o, n):
    at, until = parse_iso(o.get("at")), parse_iso(o.get("until"))
    reset = parse_iso(o.get("resets_at"))
    how = "with the reset" if until is not None and reset is not None and until == reset else \
        "at %s, as it was given" % when_word(until, n)
    return "USAGE — the continue of %s expired %s" % (when_word(at, n) if at else "?", how)


def notes_once(hub, verdict, now=None):
    """The turn start's once-only words — a «continue» that expired (R4) — returned ONCE:
    the said key is written into the meter file BEFORE they are returned, so two turn
    starts never both say them. [] when nothing is unsaid. Never raises."""
    try:
        path = verdict.get("meter")
        data = read_json(path, None) if path else None
        if not isinstance(data, dict):
            return []
        note = data.get("continue_expired")
        if not isinstance(note, dict) or not note.get("key"):
            return []
        if data.get("continue_expired_said_key") == note["key"]:
            return []
        data["continue_expired_said_key"] = note["key"]
        write_atomic(path, data)
        return [str(line) for line in (note.get("lines") or []) if line]
    except Exception:
        return []


def continued_line(hub, ov, w, spend, n, age, who, stale_words=""):
    """R4: the one line a window hears every turn while the owner's «continue» stands."""
    at = parse_iso(ov.get("at"))
    head = "USAGE — CONTINUED past the pause line (%s, %s, at %s percent)" % (
        owner_word(hub), when_word(at, n) if at else "?", pct_word(ov.get("percent_at")))
    if stale_words:
        return "%s · %s · %s%s" % (head, stale_words, dollars(spend, short=True) or NO_FIGURE, who)
    reset = parse_iso(w.get("resets_at"))
    reset_word = (", resets %s" % when_word(reset, n)) if reset else ""
    return "%s · %s%s · %s · %s%s" % (head, window_words(w, spend), reset_word,
                                        dollars(spend, short=True) or NO_FIGURE, age_words(age), who)


def refresh_line(vendor, login, why, src="", account=""):
    """the word `refresh` in place of every percent, the login named with its source
, why in parentheses, and what to do: `USAGE · <login> (app) · refresh (read
    4 h ago by outlook) — call get_usage, then usage.py --write --vendor claude`."""
    who = login_words(login, src, account) if vendor == "claude" else VENDOR_WORD.get(vendor, vendor)
    return "USAGE · %s · refresh (%s) — %s" % (who or UNKNOWN_LOGIN, why,
                                              REFRESH_DO.get(vendor, "read it again"))


def state_line(vendor, data, login, cfg, n, age, src=""):
    """the one line a fresh meter says below WARN (and the wake's receipts at any
    level): `USAGE · <login> (window) · Fable 9 % · all 6 % · read 3 min ago` — the week
    windows of the login's own file, the login's source in one word; a window
    that reset since the read says `refresh` for itself."""
    who = login_words(data.get("login") or login, src) if vendor == "claude" \
        else VENDOR_WORD.get(vendor, vendor)
    wins = [w for w in data.get("windows") or [] if isinstance(w, dict)]
    weekly = ([w for w in wins if w.get("kind") == "week-model"]
              + [w for w in wins if w.get("kind") == "week"])
    parts = []
    for w in (weekly or wins):
        name = "all" if w.get("kind") == "week" else short_name(w)
        reset = parse_iso(w.get("resets_at"))
        if reset is not None and reset <= n:
            parts.append("%s refresh (reset %s, after the read)" % (name, when_word(reset, n)))
            continue
        parts.append("%s %s %%" % (name, pct_word(w.get("percent"))))
    if not parts:
        parts.append(str(data.get("meter") or "no windows on this meter"))
    return "USAGE · %s · %s · %s" % (who or UNKNOWN_LOGIN, " · ".join(parts), age_words(age))


def no_meter_verdict(out, hub, machine, vendor, want, cfg, n):
    """No file for THIS login. Another login's newer reading never stands in: the
    line says `refresh` and names the freshest reading on this machine and whose it is.
    Level `stale` when another login's reading exists (the hook says it on the turn it
    goes so and every refresh_turns turns), else `none`."""
    others = [(p, d) for p, d in meters(hub, machine, vendor)
              if want is None or not same_login(d.get("login"), want)]
    if want is not None and same_login(want, UNKNOWN_LOGIN) and out.get("account"):
        why = "no logins map here names this account yet"
    elif want is not None and same_login(want, UNKNOWN_LOGIN):
        why = "the login this window runs under cannot be read here"
    elif want is not None:
        why = "no reading for this login on this machine yet"
    else:
        why = "no reading on this machine yet"
    if others:
        p, d = others[0]
        read = parse_iso(d.get("read_at"))
        age = minutes_between(read, n) if read else None
        whose = short_login(d.get("login"), [want] + [x.get("login") for _p, x in others]) \
            if vendor == "claude" else ""
        if want is not None and not same_login(want, UNKNOWN_LOGIN):
            why = "read %s by %s" % (ago_words(age), whose)
        else:
            why += "; the newest reading here is by %s, %s" % (whose or "another login", ago_words(age))
        out.update(level="stale", warned=False, foreign=p)
    out["lines"] = [refresh_line(vendor, want, why, out.get("login_source"), out.get("account"))]
    out["state_line"] = out["lines"][0]
    return out


def evaluate(hub, vendor, model=None, now=None, machine=None, cfg=None, login=None, prune=True,
             login_source=None):
    out = _evaluate(hub, vendor, model, now, machine, cfg, login, prune, login_source)
    # A cheaper window hears the stop, while its own existing gates still rule.
    if out.get("stop_line") and out["level"] != "stop" and not out.get("risk_confirmation"):
        out["lines"] = out["lines"] + [out["stop_line"]]
    # A5: how often the refresh nag rides — every refresh_turns_pause turns at or above
    # PAUSE (the only reason a 97 watch can be blind is a meter nobody refreshed), else
    # refresh_turns; effort.py reads the two fields and holds no number of its own.
    c = cfg if cfg is not None else load_settings(hub)[0]
    above = out.get("level") in ("pause", "stale-pause", "continued", "auto-pause")
    try:
        out["refresh_every"] = max(1, int(float(c.get("refresh_turns_pause" if above else "refresh_turns")
                                                or (2 if above else 10))))
    except (TypeError, ValueError):
        out["refresh_every"] = 2 if above else 10
    if (out.get("level") in ("pause", "continued", "auto-pause") and out.get("meter")
            and out.get("age_min") is not None and out["age_min"] >= REFRESH_MIN_AGE):
        out["refresh_line"] = refresh_line(vendor, out.get("login"), "read %s" % ago_words(out.get("age_min")),
                                           out.get("login_source"), out.get("account"))
    return out


def _evaluate(hub, vendor, model=None, now=None, machine=None, cfg=None, login=None, prune=True,
             login_source=None):
    """The verdict for a window running `model` on this machine:
    {level: none|ok|warn|pause|stop|auto-pause|stale|stale-pause|manual|continued, pause, lines,
     meter, read_at, age_min, hits, key, warn_key, question, meter_words, override, and 's
     auto_pause, auto_key, auto_window, auto_resets, auto_login, auto_line, auto_lifted_key,
     auto_lifted_line, refresh_every, refresh_line — always present, falsy when not applicable}.
    Never raises;
    remembers only a crossed STOP window until its weekly reset.

    A PAUSE hit whose window (label + reset) carries an unexpired override — the
    owner's «continue» — is level `continued`: pause False and one line, so the waiter
    arms, routines run and the attended road pushes with no change of their own. A hit on
    any other window still pauses; a manual pause stands above every override; and an
    override whose `until` has come is pruned here, once. `question` and `meter_words`
    are the notice's body and subtitle; `letter` is the onset letter's text (the PAUSE line
    without the session's clause); `warn_key` / `warn_line` are a WARN crossing's onset key
    and its line — at level `warn`, and beside a `continued` line when another window is at
    WARN.

    A Claude verdict reads ONE login's meter — `login` (the hook passes the window's
    own), else the login app_account() resolves (this window's variables, the app's config, the
    cli config), else `unknown` — and every line names it with its source in one word
    (`login_source`: given by the caller, else the road session_login took for that login in
    this process, else `given`). No file for that login (another login's newer file never
    stands in; a known account with no login yet reads the file that recorded it: a
    PAUSE reaches its own account's windows and routines only), a login that cannot be read,
    or a file older than stale_minutes says `refresh` in place of every percent;
    `state_line` is the one line --line and the wake screen print below WARN. `prune=False`
    is a READER's call (the wake screen, the night check): an expired «continue» is simply
    not honoured, and nothing is written."""
    n = now_local(now)
    if cfg is None:
        cfg, _missing = load_settings(hub)
    rec = None
    if machine is None:
        rec = paths_record(hub)
        machine = rec["machine"]
    want, src, acct = None, "", ""
    if vendor == "claude":
        want = str(login or "").strip()
        if want:
            known = _SOURCE_OF.get(want.lower()) or ("", "")
            src = login_source or known[0] or "given"
            acct = known[1] if not login_source or login_source == known[0] else ""
        else:
            rec = rec or paths_record(hub)
            email, acct, src = app_account(rec["roots"], hub=hub)
            want = email or UNKNOWN_LOGIN
    out = {"level": "none", "pause": False, "lines": [], "meter": None, "read_at": None,
           "age_min": None, "hits": [], "key": "", "vendor": vendor, "warn_key": "",
           "question": "", "meter_words": "", "override": None, "login": want or "",
           "state_line": "", "login_source": src, "account": acct,
           "auto_pause": False, "auto_key": None, "auto_window": None, "auto_resets": None,
           "auto_login": None, "auto_line": None, "auto_lifted_key": None,
           "auto_lifted_line": None, "refresh_every": 10, "refresh_line": None}
    path, data = newest_meter(hub, machine, vendor, login=want, account=acct or None)
    # An identity taken from the app's SIGN-IN —
    # source word «window» — is PROVISIONAL: a window's own record (its bridge owner) is not on
    # disk at its first prompt, and the sign-in can be another account than the one the window
    # bills. A provisional identity's meter older than stale_minutes says refresh and never
    # pauses, stops or asks for the choice; the verdict is re-made at the next turn from the
    # record. ASSUMES[first-prompt-identity-is-provisional]: the bridge record lands after the
    # first hook call.
    if data and src == "window":
        _read = parse_iso(data.get("read_at"))
        _age = minutes_between(_read, n) if _read else None
        if _age is None or _age > float(cfg["stale_minutes"]):
            words = ("read %s · the app's sign-in, provisional until this window's own record "
                     "lands" % ago_words(_age))
            line = refresh_line(vendor, data.get("login") or want, words, src)
            out.update(level="stale", stale=True, provisional=True, read_at=data.get("read_at"),
                       age_min=_age, meter=path, lines=[line], state_line=line)
            return out
    stopped = hard_stop(hub, vendor, data, cfg, n)
    policy = confirm_policy(cfg, vendor)
    confirm = bool(stopped and policy and
                   (model is None or flagship_name(hub, vendor, model) == stopped[3]))
    auto_data = data
    if confirm:
        # Only this flagship week changes policy. Shared-plan/other windows and
        # their latches retain their gates; the underlying meter is untouched.
        window = stopped[1]
        def same_flagship_week(w):
            return (isinstance(w, dict) and w.get("kind") == "week-model" and
                    w.get("label") == window.get("label") and
                    same_reset(w.get("resets_at"), window.get("resets_at")))
        auto_data = dict(data)
        auto_data["windows"] = [w for w in data.get("windows") or [] if not same_flagship_week(w)]
        if same_flagship_week(auto_data.get("auto_pause_window")):
            auto_data.pop("auto_pause_window", None)
    # the auto-pause watch reads the meter before anything else is decided, so its
    # fields are filled even when the hard stop wins the level
    auto = auto_find(auto_data, cfg, vendor, model, n) if auto_data else None
    if confirm and (auto or cfg.get("manual_pause")):
        out["risk_confirmation_blocked"] = True
    if data:
        lift = auto_lifted(data, cfg, vendor, n)
        if lift:
            out["auto_lifted_key"] = lift[0]
            out["auto_lifted_line"] = "AUTO-PAUSE lifted — %s reset" % lift[1]
    if auto:
        aw, apct = auto
        areset = parse_iso(aw.get("resets_at"))
        alogin = data.get("login") or want or UNKNOWN_LOGIN
        out.update(auto_pause=True, auto_key=auto_key_of(aw),
                   auto_window={"label": aw.get("label"), "percent": apct, "kind": aw.get("kind"),
                                "resets_at": aw.get("resets_at")},
                   auto_resets=iso(areset), auto_login=alogin,
                   auto_line=auto_line_of(aw, apct, alogin, n, cfg))
    if stopped:
        pct, window, line, name = stopped
        if not confirm:
            out["stop_line"] = line
        # Unknown models are never presumed cheap. pause_scope cannot widen STOP.
        if not confirm and (not model or flagship_name(hub, vendor, model) == name):
            out.update(level="stop", pause=True,
                       lines=[line] + ([out["auto_line"]] if auto else []), state_line=line,
                       meter=path, read_at=data.get("read_at"),
                       age_min=minutes_between(parse_iso(data.get("read_at")), n)
                       if parse_iso(data.get("read_at")) else None,
                       key="stop|%s|%s" % (window.get("label"), window.get("resets_at")),
                       hits=[{"level": "stop", "percent": pct, "window": window,
                              "continued": False}])
            return out
    if auto:
        # No «continue» reaches it: no override is read, nothing here asks a question.
        read_a = parse_iso(data.get("read_at"))
        out.update(level="auto-pause", pause=True, lines=[out["auto_line"]],
                   state_line=out["auto_line"], meter=path, read_at=data.get("read_at"),
                   age_min=minutes_between(read_a, n) if read_a else None,
                   key="auto|%s" % out["auto_key"],
                   hits=[{"level": "auto-pause", "percent": auto[1], "window": auto[0],
                          "continued": False}])
        return out
    if cfg.get("manual_pause"):
        at = cfg.get("manual_pause_at")
        out.update(level="manual", pause=True, key=("manual|%s" % at) if at else "manual",
                   meter_words="manual pause", question=MANUAL_TAIL,
                   lines=["USAGE PAUSE — manual pause is on (usage-settings.json) · %s" % MANUAL_TAIL])
        out["state_line"] = "USAGE · %s · manual pause is on — lift it: usage.py --manual off" % (
            login_words(want, src) if vendor == "claude" else VENDOR_WORD.get(vendor, vendor))
        return out
    if not data:
        return no_meter_verdict(out, hub, machine, vendor, want, cfg, n)
    if confirm:
        pct, window, _line, name = stopped
        policy_at = parse_iso(policy["at"])
        signed = [o for o in cfg.get("overrides") or [] if isinstance(o, dict) and
                  isinstance(o.get("by"), str) and o["by"].strip() and
                  parse_iso(o.get("at")) is not None and parse_iso(o["at"]) >= policy_at]
        ov = override_for(signed, vendor, window, n)
        _read_at = parse_iso(data.get("read_at"))
        _age = minutes_between(_read_at, n) if _read_at else None
        warning = flagship_warning(name, pct, window, want, src, _age, n, vendor)
        lines = [warning]
        if ov:
            lines.append("RISK ACKNOWLEDGED — by %s at %s; continuation lasts until %s." % (
                ov["by"], ov["at"], when_word(parse_iso(ov.get("until")), n)))
        out.update(risk_confirmation=True, risk_flagship=name, level="continued" if ov else "pause",
                   pause=not bool(ov), lines=lines, state_line=warning, override=ov,
                   meter=path, read_at=data.get("read_at"),
                   age_min=minutes_between(parse_iso(data.get("read_at")), n)
                   if parse_iso(data.get("read_at")) else None,
                   key="confirm|%s|%s" % (window.get("label"), window.get("resets_at")),
                   question="button up, or continue at my risk?", meter_words="%s percent" % pct_word(pct),
                   hits=[{"level": "pause", "percent": pct, "window": window, "continued": bool(ov)}])
        return out
    out["meter"] = path
    if prune:
        overrides = prune_overrides(hub, cfg, vendor, n, path)
    else:
        overrides = [o for o in cfg.get("overrides") or []
                     if not (is_vendor(o, vendor) and parse_iso(o.get("until")) is not None
                             and parse_iso(o.get("until")) <= n)]
    read = parse_iso(data.get("read_at"))
    out["read_at"] = data.get("read_at")
    age = minutes_between(read, n) if read else None
    out["age_min"] = age
    warn, pause = thresholds(cfg, vendor)
    spend = data.get("spend")
    hits = []
    for w in data.get("windows") or []:
        if stopped and w == stopped[1]:
            continue                       # only cheaper models reach this path
        try:
            pct = float(w.get("percent"))
        except (TypeError, ValueError):
            continue
        reset = parse_iso(w.get("resets_at"))
        if reset is not None and reset <= n:
            continue                              # that window has reset since the read
        if not applies(cfg, w, model):
            continue
        if pct >= pause:
            hits.append(("pause", pct, w))
        elif pct >= warn:
            hits.append(("warn", pct, w))
    hits.sort(key=lambda h: (h[0] != "pause", -h[1]))
    covered = {}
    for i, (lv, _p, w) in enumerate(hits):
        if lv == "pause":
            ov = override_for(overrides, vendor, w, n)
            if ov is not None:
                covered[i] = ov
    out["hits"] = [{"level": lv, "percent": p, "window": w, "continued": i in covered}
                   for i, (lv, p, w) in enumerate(hits)]
    open_pause = [h for i, h in enumerate(hits) if h[0] == "pause" and i not in covered]
    cont = [(hits[i], covered[i]) for i in sorted(covered)]
    if vendor == "claude":                                  # every line names its login,
        who = " · %s" % login_words(data.get("login") or want, src)   # and its source
    else:
        others = len(meters(hub, machine, vendor)) > 1
        who = (" · %s" % data.get("login")) if others and data.get("login") else ""
    stale = age is None or age > float(cfg["stale_minutes"])
    out["stale"] = stale
    read_word = age_words(age)                              # the read AGE, never a clock
    if stale:
        mins = int(age) if age is not None else 0
        if open_pause:
            w = open_pause[0][2]
            reset = parse_iso(w.get("resets_at"))
            question = question_words(spend, reset)
            words = "%s meter read %d min ago, last read at or over the pause line%s" % (
                short_name(w), mins, (", resets %s" % when_word(reset, n)) if reset else "")
            out.update(level="stale-pause", pause=True,
                       key="%s|%s" % (w.get("label"), w.get("resets_at")),
                       question=question, meter_words=words)
            out["letter"] = ("USAGE PAUSE — %s · refresh before you work (%s) · %s%s"
                             % (words, REFRESH_HOW.get(vendor, "read it again"), question, who))
            out["lines"] = ["%s · %s" % (out["letter"], SESSION_TAIL)]
        elif cont:
            (_lv, _p, w), ov = cont[0]
            out.update(level="continued", override=ov)
            out["lines"] = [continued_line(hub, ov, w, spend, n, age, who, stale_words=(
                "%s meter read %d min ago; refresh (%s)" % (short_name(w), mins,
                                                            REFRESH_HOW.get(vendor, "read it again"))))]
        else:
            out["level"] = "stale"
            out["warned"] = bool(hits)
            out["lines"] = [refresh_line(vendor, data.get("login") or want,
                                         "read %s" % ago_words(age), src)]
        out["state_line"] = refresh_line(vendor, data.get("login") or want,
                                         "read %s" % ago_words(age), src)
        return out
    out["state_line"] = state_line(vendor, data, want, cfg, n, age, src)
    if not hits:
        out["level"] = "ok"
        return out
    if open_pause:
        _lv, pct, w = open_pause[0]
        reset = parse_iso(w.get("resets_at"))
        question = question_words(spend, reset)
        meter_words = "%s %d percent" % (short_name(w), int(round(pct)))
        if reset is not None:
            meter_words += " · " + reset_words(w, reset, n)
        out.update(level="pause", pause=True, key="%s|%s" % (w.get("label"), w.get("resets_at")),
                   question=question, meter_words=meter_words)
        # The first ` · ` field stays `<meter> <N> percent`: the postman names the meter
        # that held a push by it (pause_meter), and mail.py's refusal quotes it.
        # The letter carries the question; the TURN-START line also tells the session what to
        # do with either word — the notice and the letter never do.
        out["letter"] = "USAGE PAUSE — %s · %s · %s%s" % (meter_words, question, age_words(age), who)
        out["lines"] = ["%s · %s" % (out["letter"], SESSION_TAIL)]
        return out
    warns = [h for h in hits if h[0] == "warn"]
    if warns:
        # A WARN rides on its own line — alone, or after a CONTINUED line when a «continue»
        # stands on another window (nothing is hidden) — and its
        # crossing is announced once either way (R2).
        _lv, _pct, ww = warns[0]
        reset = parse_iso(ww.get("resets_at"))
        reset_word = (", resets %s" % when_word(reset, n)) if reset else ""
        clause = ""
        if ww.get("kind") == "week-model":
            clause = " — step down where the stretch is mechanical"
        warn_line = "USAGE — %s%s · %s%s%s" % (window_words(ww, spend), reset_word, read_word,
                                               who, clause)
        out.update(warn_key="%s|%s" % (ww.get("label"), ww.get("resets_at")), warn_line=warn_line,
                   meter_words=window_words(ww, spend) + reset_word, question=warn_line)
    if cont:
        (_lv, _p, w), ov = cont[0]
        out.update(level="continued", override=ov)
        out["lines"] = [continued_line(hub, ov, w, spend, n, age, who)] + (
            [out["warn_line"]] if out.get("warn_line") else [])
        return out
    out["level"] = "warn"
    out["lines"] = [out["warn_line"]]
    return out


def pause_facts(hub, vendor="claude", now=None, machine=None, cfg=None):
    """What a pass copies into its holds rows: None when nothing is paused, else
    {all: bool, families: [..], line}. `all` = a PAUSE that reaches every model.
    A hit the owner's «continue» answers holds nothing."""
    if cfg is None:
        cfg, _m = load_settings(hub)
    v = evaluate(hub, vendor, model=None, now=now, machine=machine, cfg=cfg)
    if not v.get("pause"):
        return None
    auto = {"auto": bool(v.get("auto_pause")), "auto_line": v.get("auto_line"),
            "auto_key": v.get("auto_key"), "auto_login": v.get("auto_login")}
    if v["level"] == "manual":
        return dict({"all": True, "families": [], "line": v["lines"][0]}, **auto)
    fams, every = [], False
    for h in v["hits"]:
        if h["level"] not in ("pause", "auto-pause") or h.get("continued"):
            continue
        w = h["window"]
        scope = auto_scope_of(cfg, w.get("kind") or "") if h["level"] == "auto-pause" \
            else scope_of(cfg, w.get("kind") or "")
        if scope == "model" and w.get("model"):
            fams.append(str(w["model"]).lower())
        else:
            every = True
    if v.get("auto_pause") and v["level"] != "auto-pause":   # the stop level hid the auto hit
        aw = v.get("auto_window") or {}
        if auto_scope_of(cfg, aw.get("kind") or "") == "model" and aw.get("model"):
            fams.append(str(aw["model"]).lower())
        else:
            every = True
    return dict({"all": every or not fams, "families": sorted(set(fams)),
                 "line": (v["lines"] or [""])[0]}, **auto)


def pause_for_model(hub, model, vendor="claude", now=None):
    """The one call the waiter makes: the PAUSE line for a window on `model`, or ''."""
    try:
        v = evaluate(hub, vendor, model=model or None, now=now)
        return v["lines"][0] if v.get("pause") and v.get("lines") else ""
    except Exception:
        return ""


# ==========================================================================
# ANNOUNCE ONCE — one notice and one <MACHINE>/all letter per PAUSE onset;
# one notice, no letter, per WARN crossing
# ==========================================================================

def detached(args, hub):
    """Start a child and never wait on it: a hook's budget is five seconds.

    ASSUMES: the child outlives this call, and on Windows a live child's working directory
    (the hub) cannot be removed while it runs — WinError 32 on a test world's hub.
    So a harness that tears a world down waits, bounded, until the folder
    can go (test_usage_stop.py `remove_when_free`); the hook itself never waits (gate G-A1)."""
    import subprocess
    kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
          "stdin": subprocess.DEVNULL, "cwd": str(hub), "close_fds": True}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen(args, **kw)


def raise_now(subtitle, body, notify=None, title=None):
    """ONE desktop notice, now, through the postman's own notifier (`raise_note`): bounded
    by its NOTIFY_TIMEOUT, (how, why) back, never raises. `notify` — else EXO_NOTIFY in the
    environment — is the seam every gate uses; nothing else raises a real banner."""
    notify = notify or os.environ.get("EXO_NOTIFY") or None
    try:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "postman.py")
        if not os.path.isfile(path):
            return "none", "no postman.py beside usage.py"
        spec = importlib.util.spec_from_file_location("exo_postman_usage", path)
        pm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pm)
        return pm.raise_note(title or PING_TITLE, subtitle, body, notify=notify)
    except Exception as exc:
        return "", repr(exc)[:160]


def ping(hub, subtitle, body, wait=False, py=None, notify=None, title=None):
    """THE PING: one desktop notice on this machine. From a hook it is
    fire-and-forget — a detached `usage.py --ping` child, like the letter — so the
    notifier's ten seconds never reach a turn start. Returns 'pinged' or 'no ping: …'."""
    notify = notify or os.environ.get("EXO_NOTIFY") or None
    if wait:
        _how, why = raise_now(subtitle, body, notify, title=title)
        return "no ping: %s" % why if why else "pinged"
    args = [py or sys.executable or "python3", os.path.abspath(__file__), "--ping",
            "--subtitle", subtitle, "--body", body, "--hub", str(hub)]
    if title:
        args += ["--title", title]
    if notify:
        args += ["--notify", str(notify)]
    try:
        detached(args, hub)
        return "pinged"
    except Exception as exc:
        return "no ping: %r" % (exc,)


def announce(hub, verdict, machine, now=None, py=None, wait=False, notify=None):
    """Send ONE desktop notice and ONE broadcast letter per PAUSE onset — the question —
    and ONE notice, NO letter, per WARN crossing (information only). The onset
    key (the window and its reset, or 'manual') is written into the meter file (or the
    state dir for a manual pause) BEFORE the notice and the letter go, so two turn starts
    can never ask twice. Returns 'sent' | 'pinged' | 'already' | 'none' | 'failed: …'
    (with ` · no ping: …` when a waited-for notice failed)."""
    n = now_local(now)
    # an auto-pause onset raises its own ONE notice, keyed on auto_announced_key, and
    # NO letter (part B tells the windows). It is checked before the stop: both can be true.
    if verdict.get("auto_pause") and verdict.get("auto_key") and verdict.get("meter"):
        data = read_json(verdict["meter"], None)
        if not isinstance(data, dict):
            return "failed: the meter file could not be read"
        if data.get("auto_announced_key") != verdict["auto_key"]:
            data["auto_announced_key"] = verdict["auto_key"]
            data["auto_announced_at"] = iso(n)
            if not isinstance(data.get("auto_pause_window"), dict):   # belt: the latch is on file
                aw = verdict.get("auto_window") or {}
                data["auto_pause_window"] = {"label": aw.get("label"), "percent": aw.get("percent"),
                                             "kind": aw.get("kind"), "resets_at": aw.get("resets_at"),
                                             "model": (aw.get("model") or "")}
            write_atomic(verdict["meter"], data)
            return ping(hub, "%s %s percent" % ((verdict.get("auto_window") or {}).get("label"),
                                                  pct_word((verdict.get("auto_window") or {}).get("percent"))),
                        verdict["auto_line"], wait=wait, py=py, notify=notify, title=AUTO_TITLE)
        if verdict.get("level") == "auto-pause":
            return "already"
    if verdict.get("auto_lifted_key") and verdict.get("meter") and not verdict.get("auto_pause"):
        data = read_json(verdict["meter"], None)
        if not isinstance(data, dict):
            return "failed: the meter file could not be read"
        if data.get("auto_lifted_key") != verdict["auto_lifted_key"]:
            data["auto_lifted_key"] = verdict["auto_lifted_key"]
            data.pop("auto_lifted_window", None)
            data.pop("auto_pause_window", None) if isinstance(data.get("auto_pause_window"), dict) \
                and auto_key_of(data["auto_pause_window"]) == verdict["auto_lifted_key"] else None
            write_atomic(verdict["meter"], data)
            return ping(hub, "auto-pause lifted", verdict["auto_lifted_line"], wait=wait, py=py,
                        notify=notify, title=AUTO_TITLE)
    if verdict.get("level") == "stop":
        return "none"                     # STOP is not a question or a PAUSE onset
    if verdict.get("warn_key") and not verdict.get("pause") and verdict.get("meter"):
        key = verdict["warn_key"]
        data = read_json(verdict["meter"], None)
        if not isinstance(data, dict):
            return "failed: the meter file could not be read"
        if data.get("warn_announced_key") == key:
            return "already"
        data["warn_announced_key"] = key
        data["warn_announced_at"] = iso(n)
        write_atomic(verdict["meter"], data)
        return ping(hub, verdict.get("meter_words") or "",
                    verdict.get("warn_line") or (verdict.get("lines") or ["USAGE"])[0],
                    wait=wait, py=py, notify=notify)
    if not verdict.get("pause") or not verdict.get("key"):
        return "none"
    key = verdict["key"]
    rec = paths_record(hub)
    manual = verdict.get("level") == "manual"
    if manual or not verdict.get("meter"):
        mark_path = os.path.join(state_dir(rec["roots"]), "announced-%s.json" % verdict.get("vendor"))
        mark = read_json(mark_path, {}) or {}
        if mark.get("pause_announced_key") == key:
            return "already"
        write_atomic(mark_path, {"pause_announced_key": key, "pause_announced_at": iso(n)})
    else:
        data = read_json(verdict["meter"], None)
        if not isinstance(data, dict):
            return "failed: the meter file could not be read"
        if data.get("pause_announced_key") == key:
            return "already"
        data["pause_announced_key"] = key
        data["pause_announced_at"] = iso(n)
        write_atomic(verdict["meter"], data)
    text = verdict.get("letter") or (verdict.get("lines") or ["USAGE PAUSE"])[0]
    pinged = ping(hub, verdict.get("meter_words") or "", verdict.get("question") or text,
                  wait=wait, py=py, notify=notify)
    tail = "" if pinged == "pinged" else " · " + pinged
    mail = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mail.py")
    if not os.path.isfile(mail):
        return "failed: no mail.py beside usage.py" + tail
    import subprocess
    to = "%s/all" % str(machine).upper()
    args = [py or sys.executable or "python3", mail, "--send", to, "Exocortex", text,
            MANUAL_ACTION if manual else ANNOUNCE_ACTION, "--no-push", "--hub", str(hub)]
    try:
        if wait:
            proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=30, cwd=str(hub))
            return ("sent" if proc.returncode == 0 else "failed: mail.py exit %d" % proc.returncode) + tail
        # A HOOK NEVER WAITS ON THE LETTER: mail.py runs one postman pass after it
        # sends (up to ten seconds), and the hook's own budget is five. The onset
        # mark is already written, so a letter lost here is never sent twice —
        # and the PAUSE line still rides every turn start.
        detached(args, hub)
        return "sent" + tail
    except Exception as exc:
        return "failed: %r" % (exc,) + tail


# ==========================================================================
# THE ACCOUNTING
# ==========================================================================

def claude_rows(roots, since, until, raw=False):
    """One row per (file, request): {when, model, fresh, cwrite, cached, out,
    session, title, sub}. Deduplicated per requestId (the app writes one record
    per content block, each carrying the whole response's usage) unless raw."""
    rows = []
    for path, _m, folder, sid, sub in claude_files(roots, since.timestamp() - 60):
        seen = set()
        title = ""
        for _off, raw_line in iter_lines(path, 0):
            if b'"assistant"' not in raw_line or b'"usage"' not in raw_line:
                continue
            try:
                rec = json.loads(raw_line.decode("utf-8", "replace"))
            except ValueError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            u = msg.get("usage")
            if not isinstance(u, dict):
                continue
            when = parse_iso(rec.get("timestamp"))
            if when is None or when < since or when >= until:
                continue
            model = str(msg.get("model") or "")
            if not model or model.startswith("<"):
                continue
            key = rec.get("requestId") or msg.get("id") or rec.get("uuid")
            if not raw:
                if key in seen:
                    continue
                seen.add(key)
            if not title:
                title = claude_title(roots, folder, sid) or sid[:8]
            rows.append({"when": when, "model": model,
                         "fresh": int(u.get("input_tokens") or 0),
                         "cwrite": int(u.get("cache_creation_input_tokens") or 0),
                         "cached": int(u.get("cache_read_input_tokens") or 0),
                         "out": int(u.get("output_tokens") or 0),
                         "session": sid, "title": title, "sub": bool(sub), "ticks": 0})
    return rows


def codex_rows(roots, since, until):
    rows = []
    for path, m in codex_rollouts(roots, since.timestamp() - 60):
        prev = None                               # cumulative counters start at zero
        model = ""
        stem = os.path.basename(path)[:-6]
        for _off, raw_line in iter_lines(path, 0):
            if b'"turn_context"' in raw_line and b'"model"' in raw_line:
                try:
                    rec = json.loads(raw_line.decode("utf-8", "replace"))
                    model = str((rec.get("payload") or {}).get("model") or model)
                except ValueError:
                    pass
                continue
            if b'"token_count"' not in raw_line:
                continue
            try:
                rec = json.loads(raw_line.decode("utf-8", "replace"))
            except ValueError:
                continue
            info = ((rec.get("payload") or {}).get("info") or {})
            tot = info.get("total_token_usage") if isinstance(info, dict) else None
            if not isinstance(tot, dict):
                continue
            cur = dict((k, int(tot.get(k) or 0)) for k in
                       ("input_tokens", "cached_input_tokens", "output_tokens"))
            # the rollout's counter is cumulative from its first call: the first
            # event's growth is its whole total, every later one the difference
            delta = dict((k, cur[k] - (prev or {}).get(k, 0)) for k in cur)
            prev = cur
            when = parse_iso(rec.get("timestamp"))
            if when is None or when < since or when >= until:
                continue
            if sum(delta.values()) <= 0:
                continue
            rows.append({"when": when, "model": model or "codex",
                         "fresh": max(0, delta["input_tokens"] - delta["cached_input_tokens"]),
                         "cwrite": 0, "cached": delta["cached_input_tokens"],
                         "out": delta["output_tokens"], "session": stem,
                         "title": codex_title(roots, stem) or stem[-12:], "ticks": 0})
    return rows


def codex_title(roots, stem):
    tail = stem[-36:].lower()
    index = os.path.join(str(roots.get("codex") or ""), "session_index.jsonl")
    name = ""
    for _off, raw in iter_lines(index, 0, cap=512 * 1024):
        if tail.encode("ascii", "ignore") not in raw.lower():
            continue
        try:
            d = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue
        if isinstance(d, dict) and str(d.get("id") or "").lower() == tail and d.get("thread_name"):
            name = str(d["thread_name"])
    return name


def grok_title(roots, cwd, sid):
    """The session's own name from summary.json beside its usage.json (a manual
    /rename wins, else the generated title); '' when unread."""
    base = os.path.join(str(roots.get("grok") or os.path.join(os.path.expanduser("~"), ".grok")),
                        "sessions", cwd, sid, "summary.json")
    d = read_json(base, None, cap=1 << 20)
    if not isinstance(d, dict):
        return ""
    return str(d.get("title") or d.get("generated_title") or d.get("session_summary") or "").strip()


def grok_rows(roots, since, until):
    rows = []
    names = {}
    for ended, model, u, ticks, sid, cwd in grok_turns(roots, since, until):
        if sid not in names:
            names[sid] = grok_title(roots, cwd, sid) or sid[:12]
        inp = int(u.get("inputTokens") or 0)
        cached = int(u.get("cachedReadTokens") or 0)
        rows.append({"when": ended, "model": model, "fresh": max(0, inp - cached),
                     "cwrite": int(u.get("cacheCreationTokens") or 0), "cached": cached,
                     "out": int(u.get("outputTokens") or 0), "session": sid,
                     "title": names[sid], "ticks": ticks})
    return rows


def price_of(cfg, model):
    best = None
    for prefix, rate in (cfg.get("prices") or {}).items():
        if str(model).startswith(str(prefix)) and isinstance(rate, dict):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, rate)
    return best[1] if best else None


def cost_of(cfg, vendor, row):
    """(usd, how): exact for Grok (the vendor's own ticks), list-price estimate for
    a model with a price row, (None, '') otherwise."""
    if vendor == "grok":
        return row["ticks"] / GROK_TICKS_PER_USD, "exact"
    rate = price_of(cfg, row["model"])
    if not rate:
        return None, ""
    usd = (row["fresh"] * float(rate.get("input") or 0)
           + row["cwrite"] * float(rate.get("cache_write") or 0)
           + row["cached"] * float(rate.get("cache_read") or 0)
           + row["out"] * float(rate.get("output") or 0)) / 1e6
    return usd, "list"


def rollup(rows, by, cfg, vendor):
    groups = {}
    for r in rows:
        if by == "model":
            key = (r["model"],)
        elif by == "hour":
            key = (r["when"].astimezone().strftime("%Y-%m-%d %H:00"), r["model"])
        else:
            key = (session_label(r), r["model"])
        g = groups.setdefault(key, {"calls": 0, "fresh": 0, "cwrite": 0, "cached": 0, "out": 0,
                                    "usd": 0.0, "priced": True})
        g["calls"] += 1
        for k in ("fresh", "cwrite", "cached", "out"):
            g[k] += r[k]
        usd, _how = cost_of(cfg, vendor, r)
        if usd is None:
            g["priced"] = False
        else:
            g["usd"] += usd
    return groups


def session_label(r):
    """23 columns that tell sessions apart: the title without its ACT/ARCH tag,
    cut to 16, then the first six of the session's own id."""
    t = str(r.get("title") or "")
    for tag in ("ARCH \u2014 ", "ACT \u2014 ", "HARV \u2014 ", "ARCH - ", "ACT - "):
        if t.startswith(tag):
            t = t[len(tag):]
            break
    sid = str(r.get("session") or "")
    sid = sid[-12:] if sid.startswith("rollout-") else sid
    if r.get("sub"):                              # the session's subagents, on a row of their own
        return "%s +sub %s" % (cut(t, 11).ljust(11), sid[:6])
    return "%s %s" % (cut(t, 16).ljust(16), sid[:6])


def short_model(model):
    m = str(model)
    for p in ("claude-",):
        if m.startswith(p):
            m = m[len(p):]
    return m


def cut(text, width):
    text = str(text)
    return text if len(text) <= width else text[:width - 1] + "…"


def report_lines(vendor, rows, by, cfg, raw):
    groups = rollup(rows, by, cfg, vendor)
    lines = []
    head = {"session": "session", "model": "model", "hour": "hour (local)"}[by]
    lines.append("%-23s %-12s %6s %11s %13s %10s %7s"
                 % (head, "model" if by != "model" else "", "calls", "fresh in", "cached in",
                    "out", "$"))
    tot = {"calls": 0, "fresh": 0, "cwrite": 0, "cached": 0, "out": 0, "usd": 0.0, "priced": True}
    order = sorted(groups.items(), key=lambda kv: (-kv[1]["cached"] - kv[1]["fresh"], kv[0]))
    if by == "hour":
        order = sorted(groups.items(), key=lambda kv: kv[0])
    for key, g in order:
        name = key[0]
        model = short_model(key[1]) if len(key) > 1 else ""
        if by == "model":
            name, model = short_model(key[0]), ""
        usd = ("%7.2f" % g["usd"]) if g["priced"] else "%7s" % "-"
        lines.append("%-23s %-12s %6d %11s %13s %10s %s"
                     % (cut(name, 23), cut(model, 12), g["calls"], "{:,}".format(g["fresh"] + g["cwrite"]),
                        "{:,}".format(g["cached"]), "{:,}".format(g["out"]), usd))
        for k in ("calls", "fresh", "cwrite", "cached", "out"):
            tot[k] += g[k]
        tot["usd"] += g["usd"]
        tot["priced"] = tot["priced"] and g["priced"]
    lines.append("%-23s %-12s %6d %11s %13s %10s %s"
                 % ("TOTAL", "", tot["calls"], "{:,}".format(tot["fresh"] + tot["cwrite"]),
                    "{:,}".format(tot["cached"]), "{:,}".format(tot["out"]),
                    "%7.2f" % tot["usd"]))
    if not tot["priced"]:
        lines.append("  TOTAL $ leaves out the rows marked '-' (no price known for that model)")
    return lines, tot


def cmd_report(rec, cfg, argv):
    n = now_local(parse_iso(opt(argv, "--now")))
    since = parse_iso(opt(argv, "--since"))
    until = parse_iso(opt(argv, "--until")) or n
    if since is None:
        try:
            hours = float(opt(argv, "--hours") or 24)
        except ValueError:
            hours = 24.0
        since = until - timedelta(hours=hours)
    by = (opt(argv, "--by") or "session").lower()
    if by not in ("session", "model", "hour"):
        by = "session"
    want = (opt(argv, "--vendor") or "all").lower()
    raw = "--raw" in argv
    other = opt(argv, "--machine")
    only = (opt(argv, "--session") or "").lower()
    roots = rec["roots"]
    print("USAGE REPORT — %s · %s to %s (local) · by %s"
          % (rec["machine"].upper(), since.astimezone().strftime("%Y-%m-%d %H:%M"),
             until.astimezone().strftime("%Y-%m-%d %H:%M"), by))
    if raw:
        print("RAW: every record counted, no dedup (the app writes one per content block)")
    if other:
        return report_other(rec, other)
    print("fresh in = input + cache write · $ = list-price estimate (Grok: its own cost)")
    for vendor, fn in (("claude", lambda: claude_rows(roots, since, until, raw=raw)),
                       ("codex", lambda: codex_rows(roots, since, until)),
                       ("grok", lambda: grok_rows(roots, since, until))):
        if want not in ("all", vendor):
            continue
        rows = fn()
        if only:
            rows = [r for r in rows if str(r["session"]).lower().startswith(only)
                    or only in str(r["title"]).lower()]
        print("")
        print("%s%s" % (VENDOR_WORD[vendor].upper(),
                        {"claude": " (transcripts; one call = one requestId)" if not raw else
                         " (transcripts; RAW records)",
                         "codex": " (rollouts; each token_count's growth over the one before)",
                         "grok": " (usage.json turns)"}[vendor]))
        if not rows:
            print("  nothing in this window")
            continue
        lines, _tot = report_lines(vendor, rows, by, cfg, raw)
        for line in lines:
            print(line)
    return 0


def report_other(rec, machine):
    """Another machine's last 24 hours, from the meter files the brain carried."""
    found = [(p, d) for p, d in meters(rec["hub"], machine)]
    if not found:
        print("no meter file from %s in the hub — nothing its brain carried" % machine.upper())
        return 0
    for p, d in found:
        acc = ((d.get("accounting") or {}).get("last_24h") or {})
        print("")
        print("%s %s · accounting as of %s" % (machine.upper(), VENDOR_WORD.get(d.get("vendor"), "?"),
                                               acc.get("at") or "never"))
        for model, t in sorted((acc.get("tokens_by_model") or {}).items()):
            print("  %-20s calls %6d · fresh %13s · cached %15s · out %11s"
                  % (cut(short_model(model), 20), int((acc.get("calls_by_model") or {}).get(model, 0)),
                     "{:,}".format(t.get("fresh", 0)), "{:,}".format(t.get("cached", 0)),
                     "{:,}".format(t.get("out", 0))))
    return 0


def last_24h(rows, cfg, vendor, n):
    tok, calls, usd, priced = {}, {}, 0.0, True
    for r in rows:
        t = tok.setdefault(r["model"], {"fresh": 0, "cached": 0, "out": 0})
        t["fresh"] += r["fresh"] + r["cwrite"]
        t["cached"] += r["cached"]
        t["out"] += r["out"]
        calls[r["model"]] = calls.get(r["model"], 0) + 1
        c, _how = cost_of(cfg, vendor, r)
        if c is None:
            priced = False
        else:
            usd += c
    return {"at": iso(n), "hours": ACCOUNT_HOURS, "tokens_by_model": tok, "calls_by_model": calls,
            "est_spend": {"usd": round(usd, 2), "complete": priced,
                          "how": "exact (vendor ticks)" if vendor == "grok" else "list-price estimate"}}


# ==========================================================================
# the incremental tally the pulse keeps (Claude transcripts are the big walk)
# ==========================================================================

def tally_claude(roots, sdir, n, cfg):
    """last_24h for Claude by an INCREMENTAL walk: each transcript is read only
    past the offset the last beat left, its rows kept by hour in the state dir.
    Also returns the newest get_usage result seen in what was read."""
    path = os.path.join(sdir, "claude-cursor.json")
    state = read_json(path, {}) or {}
    files = state.get("files") or {}
    since = n - timedelta(hours=ACCOUNT_HOURS)
    horizon = (n - timedelta(hours=ACCOUNT_HOURS + 2)).timestamp()
    best = (None, None, None, None)
    live = set()
    for fpath, m, folder, sid, sub in claude_files(roots, horizon):
        live.add(fpath)
        cur = files.get(fpath) or {}
        try:
            size = os.path.getsize(fpath)
        except OSError:
            continue
        start = int(cur.get("offset") or 0)
        if start > size:
            cur, start = {}, 0                    # the file shrank: read it again
        if cur and start == size:
            continue
        seen = set(cur.get("seen") or [])
        hours = cur.get("hours") or {}
        first = not cur
        end = start
        for off, raw in iter_lines(fpath, start, cap=(FIRST_READ_CAP * 8 if first else None)):
            end = off
            if b"percentUsed" in raw and b"tool_result" in raw:
                try:
                    rec = json.loads(raw.decode("utf-8", "replace"))
                    obj = get_usage_in_record(rec)
                    when = parse_iso(rec.get("timestamp")) if obj else None
                    if obj and when and (best[1] is None or when > best[1]):
                        best = (obj, when, "get_usage in transcript %s" % sid, fpath)
                except ValueError:
                    pass
                continue
            if b'"assistant"' not in raw or b'"usage"' not in raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            u = msg.get("usage")
            model = str(msg.get("model") or "")
            when = parse_iso(rec.get("timestamp"))
            if not isinstance(u, dict) or not model or model.startswith("<") or when is None:
                continue
            key = str(rec.get("requestId") or msg.get("id") or rec.get("uuid"))
            if key in seen:
                continue
            seen.add(key)
            hk = when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
            b = hours.setdefault(hk, {}).setdefault(model, [0, 0, 0, 0, 0])
            b[0] += 1
            b[1] += int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0)
            b[2] += int(u.get("cache_read_input_tokens") or 0)
            b[3] += int(u.get("output_tokens") or 0)
            b[4] += int(round(1e6 * (cost_of(cfg, "claude", {
                "model": model, "fresh": int(u.get("input_tokens") or 0),
                "cwrite": int(u.get("cache_creation_input_tokens") or 0),
                "cached": int(u.get("cache_read_input_tokens") or 0),
                "out": int(u.get("output_tokens") or 0), "ticks": 0})[0] or 0)))
        cut_h = (n - timedelta(hours=ACCOUNT_HOURS + 1)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
        hours = dict((h, v) for h, v in hours.items() if h >= cut_h)
        files[fpath] = {"offset": end if end > start else start, "seen": sorted(seen)[-400:],
                        "hours": hours}
    files = dict((p, v) for p, v in files.items() if p in live)
    write_atomic(path, {"files": files, "at": iso(n)})
    tok, calls, usd = {}, {}, 0.0
    cut_h = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
    for f in files.values():
        for h, models in (f.get("hours") or {}).items():
            if h < cut_h:
                continue
            for model, b in models.items():
                t = tok.setdefault(model, {"fresh": 0, "cached": 0, "out": 0})
                t["fresh"] += b[1]
                t["cached"] += b[2]
                t["out"] += b[3]
                calls[model] = calls.get(model, 0) + b[0]
                usd += b[4] / 1e6
    acc = {"at": iso(n), "hours": ACCOUNT_HOURS, "tokens_by_model": tok, "calls_by_model": calls,
           "est_spend": {"usd": round(usd, 2), "complete": all(price_of(cfg, m) for m in tok),
                         "how": "list-price estimate (hour buckets, dedup per requestId)"}}
    return acc, best


# ==========================================================================
# the verbs
# ==========================================================================

def opt(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def cmd_write(rec, cfg, argv):
    vendor = (opt(argv, "--vendor") or "claude").lower()
    hub, roots, machine = rec["hub"], rec["roots"], rec["machine"]
    n = now_local(parse_iso(opt(argv, "--now")))
    if vendor == "claude":
        text = ""
        if "--scan" not in argv and not sys.stdin.isatty():
            try:
                text = sys.stdin.read(1 << 20)
            except Exception:
                text = ""
        given = opt(argv, "--login")
        prog = {}
        if text.strip():
            try:
                obj = json.loads(text)
            except ValueError:
                print("usage: stdin is not the get_usage JSON — nothing written")
                return 2
            if given:
                body = claude_body_from(obj, roots, machine, n, "get_usage", login=given,
                                        how="--login", account=account_of_login(hub, roots, given))
            else:
                # the calling session's own login: its window's own variables, else
                # its transcript's believable owner, else the app's config, else the cli config
                login, how, account = session_login(
                    roots, hub, session=os.environ.get(ENV_SESSION), fallback=True)
                body = claude_body_from(obj, roots, machine, n, "get_usage", login=login,
                                        how=road_how(how, "this session"), account=account)
            if body is None:
                print("usage: stdin carries no plan windows — nothing written")
                return 2
        else:
            # bounded — newest first, a tail of each, --budget-seconds, a watchdog
            try:
                budget = float(opt(argv, "--budget-seconds") or SCAN_BUDGET_S)
            except ValueError:
                print("usage: --budget-seconds wants a number of seconds — nothing written")
                return 2
            since = 0.0 if "--all" in argv else (n - timedelta(days=SCAN_DAYS)).timestamp()
            files = claude_files(roots, since)
            sys.stderr.write("scanning %d transcripts\n" % len(files))
            sys.stderr.flush()
            guard = scan_watchdog(prog, max(0.0, budget) + SCAN_GRACE_S)
            try:
                obj, when, source, tpath = scan_claude_for_meter(roots, files=files, budget=budget,
                                                                 progress=prog)
            finally:
                guard.cancel()
            if obj is None:
                if prog.get("stopped"):
                    print(stop_line(prog, n, tail=" · nothing filed"))
                    return 0
                print("usage: no get_usage result in this machine's transcripts — call get_usage "
                      "in a session first; nothing written")
                return 1
            if given:
                body = claude_body_from(obj, roots, machine, when, source, login=given,
                                        how="--login", account=account_of_login(hub, roots, given))
            else:
                body = scanned_body(hub, roots, machine, obj, when, source, tpath)
        path, what = store_meter(hub, body)
        filed = "%s %s · login %s" % (what, os.path.basename(path),
                                         login_words(body.get("login"), body.get("login_source")))
        if prog.get("stopped"):
            print(stop_line(prog, n, tail=" · " + filed))
            return 0
        print("usage: %s %s · %s%s" % (what, os.path.basename(path), summary(body, n),
                                       " · login %s" % login_words(body.get("login"),
                                                                   body.get("login_source"))))
        return 0
    if vendor == "codex":
        body, note = codex_meter(roots, machine)
        if body is None:
            print(note)
            return 0
        path, what = store_meter(hub, body)
        print("usage: %s %s · %s" % (what, os.path.basename(path), summary(body, n)))
        return 0
    if vendor == "grok":
        body = grok_meter(roots, machine, cfg, n)
        body["accounting"] = {"last_24h": last_24h(grok_rows(roots, n - timedelta(hours=24), n),
                                                   cfg, "grok", n)}
        path, what = store_meter(hub, body, keep_newer=False)
        print("usage: %s %s · %s" % (what, os.path.basename(path), summary(body, n)))
        return 0
    print("usage: --vendor is claude, codex or grok")
    return 2


def summary(body, n=None):
    if not body.get("windows"):
        sp = body.get("spend") or {}
        if body.get("vendor") == "grok":
            return "%s · $%.2f in 7 days" % (body.get("meter"), float(sp.get("spent") or 0))
        return str(body.get("meter"))
    return " · ".join("%s %g%%" % (short_name(w), float(w.get("percent") or 0))
                      for w in body["windows"]) + " · read %s" % when_word(parse_iso(body.get("read_at")), n)


def writer_on(roots):
    return os.path.isfile(os.path.join(state_dir(roots), WRITER_FLAG))


def cmd_beat(rec, cfg, argv):
    """The pulse's call. OFF until `usage.py --install` set the writer flag here."""
    hub, roots, machine = rec["hub"], rec["roots"], rec["machine"]
    if not writer_on(roots) and "--force" not in argv:
        print("usage: writer off on this machine (usage.py --install turns it on)")
        return 0
    n = now_local(parse_iso(opt(argv, "--now")))
    t0 = time.time()
    said = []
    sdir = state_dir(roots)
    # Claude: the incremental tally, which also sees any new get_usage result
    acc, best = None, (None, None, None, None)
    try:
        acc, best = tally_claude(roots, sdir, n, cfg)
    except Exception as exc:
        said.append("claude tally failed (%r)" % (exc,))
    try:
        if best[0] is not None:
            body = scanned_body(hub, roots, machine, best[0], best[1], best[2], best[3])
            if body is not None:
                path, what = store_meter(hub, body)
                said.append("claude %s (%s · %s)" % (what, summary(body, n), body.get("login")))
        if acc is not None:
            # this machine's tally rides the app's signed-in login's meter
            email, acct, _src = app_account(roots, hub=hub)
            path, data = newest_meter(hub, machine, "claude", login=email or UNKNOWN_LOGIN,
                                      account=acct or None)
            if data is not None:
                old = (data.get("accounting") or {}).get("last_24h") or {}
                at = parse_iso(old.get("at"))
                if at is None or (n - at).total_seconds() >= ACCOUNT_REFRESH_S:
                    data["accounting"] = {"last_24h": acc}
                    write_atomic(path, data)
                    said.append("claude last_24h")
    except Exception as exc:
        said.append("claude meter not written (%r)" % (exc,))
    try:
        body, note = codex_meter(roots, machine)
        if body is not None:
            _p, data = newest_meter(hub, machine, "codex")
            old = ((data or {}).get("accounting") or {}).get("last_24h") or {}
            at = parse_iso(old.get("at"))
            if at is None or (n - at).total_seconds() >= ACCOUNT_REFRESH_S:
                body["accounting"] = {"last_24h": last_24h(
                    codex_rows(roots, n - timedelta(hours=24), n), cfg, "codex", n)}
            path, what = store_meter(hub, body)
            said.append("codex %s" % what)
        elif note:
            said.append(note)
    except Exception as exc:
        said.append("codex failed (%r)" % (exc,))
    try:
        if grok_usage_files(roots):
            _p, data = newest_meter(hub, machine, "grok")
            old = ((data or {}).get("accounting") or {}).get("last_24h") or {}
            at = parse_iso(old.get("at"))
            if data is None or at is None or (n - at).total_seconds() >= ACCOUNT_REFRESH_S:
                body = grok_meter(roots, machine, cfg, n)
                body["accounting"] = {"last_24h": last_24h(grok_rows(roots, n - timedelta(hours=24), n),
                                                           cfg, "grok", n)}
                path, what = store_meter(hub, body, keep_newer=False)
                said.append("grok %s" % what)
    except Exception as exc:
        said.append("grok failed (%r)" % (exc,))
    print("usage: %s · %.1f s" % (" · ".join(said) or "nothing new", time.time() - t0))
    return 0


def cmd_line(rec, cfg, argv, check=False):
    vendor = (opt(argv, "--vendor") or "claude").lower()
    n = now_local(parse_iso(opt(argv, "--now")))
    v = evaluate(rec["hub"], vendor, model=opt(argv, "--model"), now=n, machine=rec["machine"], cfg=cfg,
                 login=opt(argv, "--login"), login_source="--login" if opt(argv, "--login") else None)
    for line in v["lines"]:
        if check and not v["pause"]:
            continue
        print(line)
    if check:
        return 1 if v["pause"] else 0
    if vendor == "claude" and not v["lines"] and v.get("state_line"):
        print(v["state_line"])                    # below WARN, the one state line
    return 0


def receipt_line(hub, vendor="claude", login=None, now=None):
    """The words the wake screen's receipts carry — the same state line --line
    prints (one copy): fresh numbers with the login and read age, or `refresh`. '' only
    when the tool cannot say anything at all. Never raises."""
    try:
        return evaluate(hub, vendor, now=now, login=login, prune=False).get("state_line") or ""
    except Exception:
        return ""


def find_title(roots, sid):
    """A Claude session's own title from its custom-title.json, found by its id; ''."""
    base = os.path.join(str(roots.get("claude") or os.path.join(os.path.expanduser("~"), ".claude")),
                        "projects")
    try:
        folders = os.listdir(base)
    except OSError:
        return ""
    for folder in folders:
        title = claude_title(roots, folder, sid)
        if title:
            return title
    return ""


def default_by(rec):
    """Who said «continue», when --by is not given: this session's own title, else its id."""
    sid = str(os.environ.get("CLAUDE_CODE_SESSION_ID") or "").strip()
    if not sid:
        return "a session with no name"
    return find_title(rec["roots"], sid) or "session %s" % sid[:8]


def state_words(v, data, n):
    """What the verdict says now, for a refusal: its line, else the meter in one line."""
    if v.get("lines"):
        return v["lines"][0]
    if not data:
        return "no usage meter on this machine yet"
    return "USAGE — %s" % summary(data, n)


def flagship_warning(name, pct, window, login, source, age, n, vendor="claude", refresh=False):
    """The one attended warning, also used by the confirm verdict."""
    age_words = ("read %d min ago" % age if age is not None and age < 120 else
                 "read %.0f h ago" % (age / 60.0) if age is not None else "read time unknown")
    return ("%s USAGE WARNING — %s · resets %s · %s · %s · "
            "long conversations can be expensive; past included usage, extra usage can incur "
            "substantial charges if enabled, otherwise the provider may refuse requests · "
            "say «button up» or «continue at my risk»") % (
                name, "refresh" if refresh else "%s percent of the week" % pct_word(pct),
                when_word(parse_iso(window.get("resets_at")), n),
                login_words(login, source) if vendor == "claude" else VENDOR_WORD.get(vendor, vendor),
                age_words)


def record_override(hub, vendor, hits, by, spend=None, now=None, until_arg=None):
    """Atomic, idempotent signed rows shared by the hook and --continue.
    No lock wait: contention is a failed receipt, never time spent waiting in the hook.
    ASSUMES: edit_settings's same-folder rename is atomic; the exclusive lock serializes
    writers of these rows. Opposite: a simultaneous choice must not duplicate a row.
    """
    n = now_local(now)
    spend_at = None
    if isinstance(spend, dict) and (spend.get("spent") not in (None, "") or spend.get("enabled") is False):
        spend_at = {k: spend[k] for k in ("spent", "limit", "currency", "enabled") if k in spend}
    rows = []
    for h in hits:
        w = h["window"]
        until = parse_iso(w.get("resets_at")) or until_arg
        if until is None:
            raise ValueError("window has no reset time; use --until <ISO>")
        if until <= n:
            raise ValueError("window reset is already past")
        rows.append({"vendor": vendor, "window_label": str(w.get("label") or ""),
                     "resets_at": w.get("resets_at"), "until": iso(until), "by": by,
                     "at": iso(n), "percent_at": float(h["percent"]), "spend_at": spend_at})
    lock = os.path.join(str(hub), ".usage-continue.lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    recorded = []
    try:
        def change(raw):
            kept = list(raw.get("overrides") or [])
            # Read the consuming policy INSIDE this atomic edit, never from the
            # caller's earlier snapshot. A real choice gets its real time only.
            policy = confirm_policy(raw, vendor)
            for row, h in zip(rows, hits):
                # Only the flagship STOP consumes the confirmation timestamp;
                # ordinary PAUSE keeps its established continuation contract.
                confirming = policy and hard_stop(hub, vendor, {"windows": [h["window"]]}, raw, n)
                policy_at = parse_iso(policy["at"]) if confirming else None
                if policy_at is not None and n < policy_at:
                    raise ValueError("choice predates confirmation policy; not recorded")
                valid = [o for o in kept if isinstance(o, dict)
                         and isinstance(o.get("by"), str) and o["by"].strip()
                         and parse_iso(o.get("at")) is not None
                         and (policy_at is None or parse_iso(o["at"]) >= policy_at)]
                old = override_for(valid, vendor, h["window"], n)
                if old:
                    recorded.append(old)
                    continue
                kept = [o for o in kept if not (isinstance(o, dict) and is_vendor(o, vendor)
                         and str(o.get("window_label") or "") == row["window_label"]
                         and same_reset(o.get("resets_at"), row["resets_at"]))]
                kept.append(row)
                recorded.append(row)
            raw["overrides"] = kept
        if edit_settings(hub, change) == "unreadable":
            raise ValueError("settings are not a JSON object")
    finally:
        os.unlink(lock)
    return recorded


def risk_receipt(row, now=None):
    n = now_local(now)
    row = row if isinstance(row, dict) else {}
    at, until = parse_iso(row.get("at")), parse_iso(row.get("until"))
    by = row.get("by")
    if at is None or until is None or until <= n or not isinstance(by, str) or not by.strip():
        return "RISK ACKNOWLEDGED — not recorded (invalid signature)"
    return "RISK ACKNOWLEDGED — recorded %s by %s; continuation lasts until %s" % (
        at.astimezone().strftime("%H:%M"), " ".join(by.split()), when_word(until, n))


def cmd_continue(rec, cfg, argv):
    """Record the owner's word even past STOP; dollars first, then receipts.
    Valid unexpired signatures are preserved, once per vendor/label/reset window."""
    vendor = (opt(argv, "--vendor") or "claude").lower()
    n = now_local(parse_iso(opt(argv, "--now")))
    hub = rec["hub"]
    until_text = opt(argv, "--until")
    until_arg = parse_iso(until_text) if until_text else None
    if until_text and until_arg is None:
        print("usage: --until is not an ISO time (%s) — nothing written" % until_text)
        return 2
    v = evaluate(hub, vendor, model=None, now=n, machine=rec["machine"], cfg=cfg,
                 login=opt(argv, "--login"), login_source="--login" if opt(argv, "--login") else None)
    _path, data = newest_meter(hub, rec["machine"], vendor,
                               login=(v.get("login") or None) if vendor == "claude" else None,
                               account=(v.get("account") or None) if vendor == "claude" else None)
    crossed = hard_stop(hub, vendor, data, cfg, n)
    # Preserve the manual/shared-plan CLI road; a crossed flagship stop never refuses.
    if not crossed and cfg.get("manual_pause"):
        print("manual pause is on (usage-settings.json) — «continue» never lifts it · %s" % MANUAL_TAIL)
        return 1
    if not crossed and v.get("auto_pause"):
        print("«continue» cannot stand past the auto-pause line — only the window's reset lifts it "
              "(%s)" % v.get("auto_resets"))
        return 1
    open_hits = ([{"level": "stop", "window": crossed[1], "percent": crossed[0]}] if crossed else
                 [h for h in v.get("hits") or [] if h["level"] == "pause"])
    if not open_hits:
        print("nothing to continue past — %s" % state_words(v, data, n))
        return 1
    by = (opt(argv, "--by") or "").strip() or default_by(rec)
    spend = (data or {}).get("spend")
    try:
        rows = record_override(hub, vendor, open_hits, by, spend, n, until_arg)
    except (OSError, ValueError) as exc:
        print("RISK ACKNOWLEDGED — not recorded (%s)" % " ".join(str(exc).split()))
        return 2
    print(dollars(spend) or NO_FIGURE)
    stale = v.get("level") == "stale-pause"
    for row, h in zip(rows, open_hits):
        words = window_words(h["window"], spend)
        if stale:
            words += " (last read %d min ago)" % int(v.get("age_min") or 0)
        print("CONTINUED past the pause line on %s's word · %s · until %s · by %s at %s"
              % (owner_word(hub), words, when_word(parse_iso(row["until"]), n), row["by"], when_word(parse_iso(row["at"]), n)))
    return 0


def cmd_manual(rec, argv):
    """R5: `--manual on|off` writes the flag (and, on, its stamp) so nobody edits JSON."""
    word = str(opt(argv, "--manual") or "").strip().lower()
    if word not in ("on", "off"):
        print("usage: usage.py --manual on | --manual off")
        return 2
    n = now_local(parse_iso(opt(argv, "--now")))

    def change(raw):
        if word == "on":
            if raw.get("manual_pause") is True and raw.get("manual_pause_at"):
                return
            raw["manual_pause"] = True
            raw["manual_pause_at"] = iso(n)
        else:
            if not raw.get("manual_pause") and "manual_pause_at" not in raw:
                return
            raw["manual_pause"] = False
            raw.pop("manual_pause_at", None)
    what = edit_settings(rec["hub"], change)
    if what == "unreadable":
        print("usage-settings.json is there but is not a JSON object — nothing written; fix it or "
              "move it aside")
        return 2
    if word == "on":
        print("manual pause is %s (usage-settings.json) · every window stops at its next turn start "
              "· lift it: usage.py --manual off" % ("ON" if what == "written" else "already on"))
    else:
        print("manual pause is %s (usage-settings.json) · the meters' own lines rule again"
              % ("OFF" if what == "written" else "already off"))
    return 0


def cmd_status(rec, cfg):
    n = now_local()
    found = meters(rec["hub"])
    if not found:
        print("usage: no meter file in %s yet" % rec["hub"])
    for p, d in found:
        read = parse_iso(d.get("read_at"))
        age = minutes_between(read, n) if read else None
        print("%s · %s · read %s (%s min ago) · %s"
              % (os.path.basename(p), d.get("source"), when_word(read, n),
                 "?" if age is None else int(age), summary(d, n)))
        latch = d.get("auto_pause_window")                      # A7: the latch, per file
        if isinstance(latch, dict) and not auto_latch_ended(latch, d.get("windows"), n):
            since = parse_iso(d.get("auto_announced_at"))
            print("    auto-pause since %s · lifts %s · %s %s percent" % (
                when_word(since, n) if since else "?", when_word(parse_iso(latch.get("resets_at")), n),
                latch.get("label"), pct_word(latch.get("percent"))))
    print("writer flag here: %s" % ("on" if writer_on(rec["roots"]) else "off"))
    return 0


def cmd_install(rec, argv, remove=False):
    dry = "--dry" in argv
    flag = os.path.join(state_dir(rec["roots"]), WRITER_FLAG)
    if remove:
        if os.path.isfile(flag):
            if not dry:
                os.unlink(flag)
            print("OK  the pulse's writer flag %s" % ("would be removed" if dry else "removed"))
        else:
            print("OK  the pulse's writer flag was not set here")
        print("    the meter files and usage-settings.json stay (data, harmless); the hook line")
        print("    goes with effort.py's rollback, or `\"USAGE\": false` in effort-rubric.json's switches")
        return 0
    if not dry:
        os.makedirs(os.path.dirname(flag), exist_ok=True)
        with io.open(flag, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("BQ-145: the pulse writes the usage meters on this machine. Remove with "
                     "usage.py --uninstall.\n")
    print("OK  the pulse's writer flag %s (%s)" % ("would be set" if dry else "set", flag))
    return 0


STEP_MARK = "BQ-145 usage check"


def step_text(model):
    m = (" --model %s" % model) if model else ""
    return ("0. %s — before anything else run `python3 tools/usage.py --check --vendor claude%s` "
            "from the hub folder (`python` on Windows). If it exits non-zero, say its one line as "
            "your final message and end the run: nothing else this run.\n" % (STEP_MARK, m))


def skill_model(text):
    """The model a routine's own frontmatter names, or ''."""
    if not text.startswith("---"):
        return ""
    for line in text.splitlines()[1:40]:
        if line.strip() == "---":
            break
        if line.lower().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return ""


NO_COMMAND_MARKS = ("Do not run any command",)


def cmd_routine_step(argv):
    apply_ = "--apply" in argv
    remove = "--remove" in argv
    files = [a for a in argv if not a.startswith("--") and a != "--routine-step"]
    files = [f for f in files if os.path.isfile(f)]
    if not files:
        print("usage: --routine-step needs one or more routine files")
        return 2
    rc = 0
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        has = STEP_MARK in text
        if remove:
            if not has:
                print("OK  %s — no step to remove" % f)
                continue
            lines = text.splitlines(True)
            kept = [l for l in lines if STEP_MARK not in l]
            if apply_:
                io.open(f, "w", encoding="utf-8", newline="").write("".join(kept))
            print("OK  %s — step %s" % (f, "removed" if apply_ else "would be removed"))
            continue
        if has:
            print("OK  %s — the step is already there" % f)
            continue
        if any(mark in text for mark in NO_COMMAND_MARKS):
            print("SKIP %s — this routine runs no command by its own design (a permission stall "
                  "would block its later fires); the effort hook's scheduled-run block covers it" % f)
            continue
        lines = text.splitlines(True)
        at = None
        for i, l in enumerate(lines):
            s = l.lstrip()
            if s[:2] in ("1.", "1)") or s.startswith("1. "):
                at = i
                break
        if at is None:
            print("STOP %s — no numbered first step found; left alone" % f)
            rc = 1
            continue
        lines.insert(at, step_text(skill_model(text)))
        if apply_:
            io.open(f, "w", encoding="utf-8", newline="").write("".join(lines))
        print("OK  %s — step %s" % (f, "added" if apply_ else "would be added"))
    return rc


# ==========================================================================
# the pictures — the tree's meter bands and the ledger's chip
# ==========================================================================

def _e(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


BAND_CSS = (
    ".ubands{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}"
    ".ub{display:flex;align-items:center;gap:8px;padding:5px 10px;border-radius:3px;"
    "border:1px solid rgba(127,140,160,.35);font:12px/1.3 ui-monospace,Menlo,Consolas,monospace;"
    "color:inherit;text-decoration:none;max-width:100%}"
    ".ub b{letter-spacing:.08em}.ub .bar{width:64px;height:6px;border-radius:3px;"
    "background:rgba(127,140,160,.25);overflow:hidden;flex:none}"
    ".ub .bar i{display:block;height:100%;background:#5b8fd4}"
    ".ub.warn{border-color:#FFB000}.ub.warn .bar i{background:#FFB000}"
    ".ub.pause{border-color:#e5484d}.ub.pause .bar i{background:#e5484d}"
    ".ub.stale{opacity:.6}.ub.stale .bar i{background:#8a8f98}"
    ".ub .t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    ".ub.ug{letter-spacing:.08em;white-space:nowrap}.ub.ug.asked{border-color:#FFB000;color:#FFB000}"
)


def band_state(data, cfg, n):
    """(css class, top window or None, words) for one meter file."""
    read = parse_iso(data.get("read_at"))
    age = minutes_between(read, n) if read else None
    vendor = data.get("vendor")
    warn, pause = thresholds(cfg, vendor)
    wins = []
    for w in data.get("windows") or []:
        reset = parse_iso(w.get("resets_at"))
        if reset is not None and reset <= n:
            continue
        try:
            wins.append((float(w.get("percent")), w))
        except (TypeError, ValueError):
            pass
    wins.sort(key=lambda t: -t[0])
    if not wins:
        acc = ((data.get("accounting") or {}).get("last_24h") or {})
        toks = sum(int(t.get("fresh", 0)) + int(t.get("cached", 0)) + int(t.get("out", 0))
                   for t in (acc.get("tokens_by_model") or {}).values())
        return ("ok", None, "%s · %s tokens in 24 h" % (data.get("meter") or "not readable", _num(toks)))
    if age is None or age > float(cfg["stale_minutes"]):
        return ("stale", wins[0][1], "read %d min ago — no percent until it is read again"
                % (int(age) if age is not None else 0))
    top = wins[0]
    cls = "pause" if top[0] >= pause else ("warn" if top[0] >= warn else "ok")
    words = " · ".join("%s %d%%" % (short_name(w), int(round(p))) for p, w in wins[:4])
    reset = parse_iso(top[1].get("resets_at"))
    if reset:
        words += " · resets %s" % when_word(reset, n)
    return (cls, top[1], words + " · read %s" % when_word(read, n))


def _num(v):
    v = float(v or 0)
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if v >= div:
            return "%.1f%s" % (v / div, unit)
    return "%d" % v


def gate_state(hub, path, data, cfg, n):
    """The gate's state word for one meter file, from real bytes — a tuple
    (css class, words, the words in full, the file the bytes are in) or None:
      CONTINUED until <reset> · <who>  an unexpired override answers one of its windows
      ASKED <when>                     its PAUSE onset is announced (pause_announced_key
                                       names a window still at or over the line, not yet
                                       reset) and no override answers it
    Reads only; never prunes and never writes."""
    vendor = data.get("vendor")
    wins = [w for w in data.get("windows") or [] if isinstance(w, dict)]
    for w in wins:
        ov = override_for(cfg.get("overrides"), vendor, w, n)
        if ov is None:
            continue
        until, at = parse_iso(ov.get("until")), parse_iso(ov.get("at"))
        words = "CONTINUED until %s · %s" % (when_word(until, n), who_word(ov.get("by")))
        full = ("continued past the pause line on %s's word, %s, at %s percent · %s · until %s · "
                "by %s · at the word: %s · from `overrides` in %s"
                % (owner_word(hub), when_word(at, n) if at else "?", pct_word(ov.get("percent_at")),
                   short_name(w), when_word(until, n), ov.get("by") or "a session",
                   dollars(ov.get("spend_at"), short=True) or NO_FIGURE, SETTINGS_FILE))
        return ("cont", words, full, SETTINGS_FILE)
    key = data.get("pause_announced_key")
    if not key:
        return None
    _warn, pause = thresholds(cfg, vendor)
    for w in wins:
        if "%s|%s" % (w.get("label"), w.get("resets_at")) != key:
            continue
        reset = parse_iso(w.get("resets_at"))
        try:
            pct = float(w.get("percent"))
        except (TypeError, ValueError):
            return None
        if (reset is not None and reset <= n) or pct < pause:
            return None
        at = parse_iso(data.get("pause_announced_at"))
        words = "ASKED %s" % when_word(at, n)
        full = ("asked %s: %s %d percent — %s · the answer is a word in any window: «continue» or "
                "«button up» · from pause_announced_at in %s"
                % (when_word(at, n), short_name(w), int(round(pct)), PAUSE_TAIL, os.path.basename(path)))
        return ("asked", words, full, os.path.basename(path))
    return None


def bands_html(hub, now=None):
    """One band per vendor per machine from the meter files' own bytes: label, a
    percent bar, the reset, the read time. Amber at WARN, red at PAUSE, grey with
    its age when stale, and Grok's 'not readable' in words. A band is a link to
    the file it was drawn from (Click-to-explain). '' when there is no meter."""
    n = now_local(now)
    cfg, _m = load_settings(hub)
    newest = {}
    for p, d in meters(hub):
        if d.get("vendor") == "claude" and same_login(d.get("login"), UNKNOWN_LOGIN):
            continue                              # nobody's reading is never a band
        key = (str(d.get("machine") or "").lower(), d.get("vendor"))
        if key not in newest:
            newest[key] = (p, d)
    if not newest:
        return ""
    out = ["<style>%s</style><div class=\"ubands\" aria-label=\"usage meters\">" % BAND_CSS]
    for (machine, vendor), (p, d) in sorted(newest.items()):
        cls, top, words = band_state(d, cfg, n)
        pct = 0 if top is None or cls == "stale" else max(0, min(100, float(top.get("percent") or 0)))
        tip = "%s · source %s · read_at %s" % (os.path.basename(p), d.get("source"), d.get("read_at"))
        gate = gate_state(hub, p, d, cfg, n)
        if gate is not None:
            tip += " · " + gate[2]
        out.append("<a class=\"ub %s\" href=\"%s\" title=\"%s\"><b>%s · %s</b>"
                   "<span class=\"bar\"><i style=\"width:%d%%\"></i></span><span class=\"t\">%s</span></a>"
                   % (cls, _e(os.path.basename(p)), _e(tip), _e(machine.upper()),
                      _e(VENDOR_WORD.get(vendor, vendor)), int(pct), _e(words)))
        if gate is not None:                      # R7: the gate's word beside its meter; a
            out.append("<a class=\"ub ug %s\" href=\"%s\" title=\"%s\">%s</a>"   # click opens its bytes
                       % (gate[0], _e(gate[3]), _e(gate[2]), _e(gate[1])))
    out.append("</div>")
    return "".join(out)


def chip_html(hub, machine=None, now=None):
    """The ledger page's chip: the last 24 h by model on this machine, from
    last_24h in the meter files — and the gate's word for each meter
    (ASKED / CONTINUED until) after them. '' when nothing is recorded."""
    if machine is None:
        machine = paths_record(hub)["machine"]
    n = now_local(now)
    cfg, _m = load_settings(hub)
    parts, gates, fulls = [], [], []
    for p, d in meters(hub, machine):
        acc = ((d.get("accounting") or {}).get("last_24h") or {})
        for model, t in sorted((acc.get("tokens_by_model") or {}).items(),
                               key=lambda kv: -(kv[1].get("fresh", 0) + kv[1].get("cached", 0))):
            parts.append("%s %s" % (short_model(model), _num(t.get("fresh", 0) + t.get("cached", 0)
                                                             + t.get("out", 0))))
        gate = gate_state(hub, p, d, cfg, n)
        if gate is not None:
            gates.append("%s %s" % (VENDOR_WORD.get(d.get("vendor"), d.get("vendor")), gate[1]))
            fulls.append(gate[2])
    if not parts and not gates:
        return ""
    title = "tokens by model, last 24 h, from the usage meter files"
    if fulls:
        title += " · " + " · ".join(fulls)
    words = (["last 24 h · " + " · ".join(parts[:6])] if parts else []) + gates
    return "<p class=\"cl\" title=\"%s\">usage · %s</p>" % (_e(title), _e(" · ".join(words)))


# ==========================================================================

def main(argv):
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if "--ping" in argv:                          # announce()'s detached child: one notice
        _how, why = raise_now(opt(argv, "--subtitle") or "", opt(argv, "--body") or "",
                              notify=opt(argv, "--notify"), title=opt(argv, "--title"))
        return 0 if not why else 1
    rec = paths_record(opt(argv, "--hub"))
    cfg, missing = load_settings(rec["hub"])
    if missing and "--status" in argv:
        print(defaults_line(cfg))                 # said once, where a person asked
    if "--write" in argv:
        return cmd_write(rec, cfg, argv)
    if "--beat" in argv:
        return cmd_beat(rec, cfg, argv)
    if "--check" in argv:
        return cmd_line(rec, cfg, argv, check=True)
    if "--line" in argv:
        return cmd_line(rec, cfg, argv)
    if "--announce" in argv:
        an = now_local(parse_iso(opt(argv, "--now")))
        v = evaluate(rec["hub"], (opt(argv, "--vendor") or "claude").lower(), cfg=cfg,
                     machine=rec["machine"], now=an)
        said = announce(rec["hub"], v, rec["machine"], now=an, wait=True, notify=opt(argv, "--notify"))
        print("usage: %s%s" % (said, (" · " + v["lines"][0]) if v.get("lines") else ""))
        return 0
    if "--continue" in argv:
        return cmd_continue(rec, cfg, argv)
    if "--manual" in argv:
        return cmd_manual(rec, argv)
    if "--report" in argv:
        return cmd_report(rec, cfg, argv)
    if "--status" in argv:
        return cmd_status(rec, cfg)
    if "--install" in argv:
        return cmd_install(rec, argv)
    if "--uninstall" in argv:
        return cmd_install(rec, argv, remove=True)
    if "--routine-step" in argv:
        return cmd_routine_step(argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
