#!/usr/bin/env python3
"""routine-check.py — one line per Claude desktop routine: mode · folder · stored approvals ·
skipped fires since the last run · last run. Reads the app's own task store, never writes it.

    python3 tools/routine-check.py            (python on Windows)
    python3 tools/routine-check.py --json
    python3 tools/routine-check.py --templates     the hub's routines/*.md, before any is registered
    python3 tools/routine-check.py --boot-notice   the pulse's first beat after a boot: ONE desktop notice
                                                   naming every routine that will ask permission, once per
                                                   boot (a marker in the machine-local state folder); silent
                                                   when every enabled routine reads Bypass
    python3 tools/routine-check.py --catch-up <task-id> [--near-minutes N]
                                                   a routine's FIRST step: prints `RUN …` or `SKIP …` — SKIP
                                                   when this run is a catch-up older than the task's own
                                                   interval, or a catch-up whose regular fire is due within
                                                   N minutes (15 by default; 0 switches that off) — the run
                                                   then ends on that line

WHAT THE APP DOES WITH A MISSED FIRE, as the app's own log shows it
(~/Library/Logs/Claude/main*.log, `[CCDScheduledTasks]`) and its task store: at launch it spawns ONE
catch-up run per task for the LATEST missed slot only (`missed: <slot>` in the log; the store's
`lastScheduledFor` keeps that slot and `lastRunAt` the spawn), never one per missed slot; at most
three routine runs at once (`global_limit (active=3, limit=3)`), the rest retried each minute. So a
boot costs at most one run per task — and in Manual mode each of those stops at its first command
that needs a click. A catch-up is therefore always YOUNGER than one interval; `--catch-up` still
checks, so a future app that replays every slot is caught, and it also skips a catch-up whose next
regular fire is due within 15 minutes, so the same work never runs twice a few minutes apart. The number
lives HERE, as the default, so every template's step 0 stays the one bare command the gate pins;
`--near-minutes N` changes it for one run and `--near-minutes 0` switches it off.

ROUTINES NEVER RUN ON FABLE (Opus when a routine needs
high inference, never Fable). Every Claude routine's model is read from its own
SKILL.md frontmatter (`model:`): a Fable id is a STOP; no model line is a STOP too, because the
routine then runs on the app's default model, which can be Fable; `opus` is OK only with a
`model-reason:` line beside it (WARN names the missing line); `sonnet` / `haiku` are OK.
THE OPENAI HALF: every Codex automation (~/.codex/automations/*/automation.toml) is read the same
way — `gpt-6-astra` is a STOP, and so is a missing model line, which inherits the default named in
~/.codex/config.toml (read first-hand, never assumed); the model usage-settings.json names under
`routine_models.openai` (default gpt-5.6-sol) is OK. A registration road runs `--templates` first
and never registers a routine it STOPs. Exit 1 on any STOP or any routine still prompting.

Why: a routine with no permission mode asks for permission on every run, and each "always allow"
is stored as one exact command that the next run never matches. The state should be visible
before anyone has to ask. Store locations are searched, not
assumed: macOS ~/Library/Application Support/Claude/claude-code-sessions/*/*/scheduled-tasks.json,
Windows %APPDATA%\\Claude\\claude-code-sessions\\*\\*\\scheduled-tasks.json.

THE ACTIVE STORE: the app keeps one store per account — claude-code-sessions/
<account>/<org>/ — and runs only the signed-in account's. Which account that is comes from the
ONE resolver, tools/usage.py app_account(): the window's own variables when this runs inside a
window, else the app's own config.json (lastKnownAccountUuid) — never the folder written most
recently , and never the terminal's .claude.json, which is not the
app's login. The first line says it: `store: <login> (app)`. When the account cannot be read,
the line says so and every store's unset tasks are counted — unknown is never shown as a guess.
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone


def _arg(flag, default=""):
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return default


HOME = _arg("--home") or os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA", os.path.join(HOME, "AppData", "Roaming")) if not _arg("--home") \
    else os.path.join(HOME, "AppData", "Roaming")
CANDIDATES = [
    os.path.join(HOME, "Library", "Application Support", "Claude", "claude-code-sessions", "*", "*", "scheduled-tasks.json"),
    os.path.join(APPDATA, "Claude", "claude-code-sessions", "*", "*", "scheduled-tasks.json"),
]
HUB = _arg("--hub") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEX = _arg("--codex-home") or os.path.join(HOME, ".codex")
ASTRA_PREFIXES = ("gpt-6-astra",)       # the OpenAI flagship the law keeps off routines
ROUTINE_OPENAI_DEFAULT = "gpt-5.6-sol"
NEAR_MINUTES_DEFAULT = 15.0             # --near-minutes' default


def find_store():
    hits = []
    for pat in CANDIDATES:
        hits.extend(glob.glob(pat))
    return sorted(set(hits))


def find_store_in(home=None, appdata=None):
    """The app's task stores under ANY home — the wake screen's and the gates' road; the
    module's own CANDIDATES stay what this run's --home made them."""
    home = home or os.path.expanduser("~")
    if appdata is None:
        appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    hits = []
    for pat in (os.path.join(home, "Library", "Application Support", "Claude", "claude-code-sessions",
                             "*", "*", "scheduled-tasks.json"),
                os.path.join(appdata, "Claude", "claude-code-sessions", "*", "*",
                             "scheduled-tasks.json")):
        hits.extend(glob.glob(pat))
    return sorted(set(hits))


def read_store(store):
    try:
        with open(store, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def unset_tasks(stores):
    """[{name, id, store}] — every ENABLED task whose record carries no permission mode, so its
    runs start in Manual and stop at the first command that needs a click. A disabled task never
    fires and is not counted. One entry per task name across the stores (a machine that has had
    two accounts keeps two stores; the same routine in both is one routine to fix)."""
    out, seen = [], set()
    for store in stores:
        for t in read_store(store).get("scheduledTasks") or []:
            if not isinstance(t, dict) or not t.get("enabled", True):
                continue
            if t.get("permissionMode"):
                continue
            name = str(t.get("displayName") or t.get("id") or "?")
            if name in seen:
                continue
            seen.add(name)
            out.append({"name": name, "id": t.get("id"), "store": store})
    return out


_USAGE = []


def load_usage():
    """usage.py beside this file — the ONE login resolver — or None; loaded once.
    usage.py sets its stdout to replace what a console cannot print: that is put back, so this
    tool's own ASCII fallback (→ becomes ->, _SafeOut) still speaks on a cp1252 console."""
    if _USAGE:
        return _USAGE[0]
    here = os.path.dirname(os.path.abspath(__file__))
    module = None
    for cand in (os.path.join(here, "usage.py"), os.path.join(HUB, "tools", "usage.py")):
        if os.path.isfile(cand):
            errors = getattr(sys.stdout, "errors", None)
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("rc_usage", cand)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception:
                module = None
            if errors and getattr(sys.stdout, "errors", None) != errors:
                try:
                    sys.stdout.reconfigure(errors=errors)
                except Exception:
                    pass
            break
    _USAGE.append(module)
    return module


_SIGNED = []


def signed_in():
    """(account8, login, source) of the account the desktop app is signed in as, by the
    window's own variables, else the app's config.json — source `window` or `app`. The cli
    config (.claude.json) is the TERMINAL's login and never names the app's store: then, and
    when nothing reads, ('', login-or-'', 'unknown'). Read once per run."""
    if _SIGNED:
        return _SIGNED[0]
    got = ("", "", "unknown")
    us = load_usage()
    if us is not None:
        try:
            email, acct, src = us.app_account({"home": HOME, "orchestrator": HUB}, hub=HUB)
            got = (acct, email, src) if src in ("window", "app") and acct else ("", email, "unknown")
        except Exception:
            pass
    _SIGNED.append(got)
    return got


def store_account(store):
    """The account a task store belongs to: claude-code-sessions/<account>/<org>/scheduled-
    tasks.json — its folder two levels up, first eight characters."""
    return os.path.basename(os.path.dirname(os.path.dirname(store))).strip().lower()[:8]


def active_store(stores, account=None):
    """The store of the account the app is signed in as NOW : the signed-in
    account's, by the ONE resolver (signed_in) — never the folder written most recently. None
    when that account keeps no store here, or when the account cannot be read and there is
    more than one store; the one store when there is only one and the account is unread. The
    app shows only the signed-in account's routines (hub memory account-switch-one-app), so
    another account's tasks never run here until it signs back in."""
    acct = str(account if account is not None else signed_in()[0] or "").strip().lower()[:8]
    if acct:
        for store in stores:
            if store_account(store) == acct:
                return store
        return None
    return stores[0] if len(stores) == 1 else None


def store_line():
    """The header : `store: <login> (app)` — the signed-in login and where it was read."""
    acct, login, src = signed_in()
    us = load_usage()
    if acct:
        who = (us.login_words(login, src) if us is not None and login else
               "account %s (%s)" % (acct, src))
        return "store: %s" % who
    if login:
        return ("store: unknown — only the cli config (%s, not the app's) names a login here; "
                "every store's unset tasks are counted" % login)
    return ("store: unknown — the app's signed-in account cannot be read here; every store's "
            "unset tasks are counted")


def prompting_split(rows, stores):
    """(prompting, elsewhere): unset task names in the signed-in account's store, and in any
    other account's. An unread account counts every store's (never a guess)."""
    acct = signed_in()[0]
    live = active_store(stores, acct)
    prompting, elsewhere = [], []
    for r in rows:
        if not r["unset"]:
            continue
        if live is not None:
            target = prompting if r["store"] == live else elsewhere
        else:
            target = elsewhere if acct else prompting
        if r["task"] not in target:
            target.append(r["task"])
    return prompting, elsewhere


EDIT_ROAD = "Claude app \u2192 Routines \u2192 the task \u2192 Edit \u2192 Permission mode = Bypass permissions \u2192 Save"


def sweep_step(names):
    """THE ONE STEP, with the whole list inside it (the Sweep-list rule)."""
    return "%d routine%s will ask permission: %s \u2014 %s" % (
        len(names), "" if len(names) == 1 else "s", ", ".join(names), EDIT_ROAD)


def frontmatter(path):
    """{key: value} of a SKILL.md / routine template's frontmatter — the first
    `---` block, read bounded; {} when there is none or the file is not there."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(65536)
    except OSError:
        return None
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines[:40]):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        return {}
    out = {}
    for line in lines[start + 1:start + 60]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            out[key.strip().lower()] = value.strip().strip('"').strip("'")
    return out


def claude_model_verdict(meta):
    """(flag, words) for one Claude routine's frontmatter: STOP · WARN · OK."""
    if meta is None:
        return "STOP", "its SKILL.md is not there — the model it runs on cannot be read"
    model = str(meta.get("model") or "").strip()
    low = model.lower()
    if not model:
        return "STOP", ("no `model:` line — it runs on the app's default model, which can be "
                        "Fable; write `model: sonnet`")
    if "fable" in low:
        return "STOP", "model %s — routines never run on Fable" % model
    if "opus" in low:
        reason = str(meta.get("model-reason") or "").strip()
        if reason:
            return "OK ", "model %s — reason: %s" % (model, reason)
        return "WARN", "model %s with no `model-reason:` line — say why it needs Opus" % model
    return "OK ", "model %s" % model


def usage_settings():
    try:
        with open(os.path.join(HUB, "usage-settings.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def toml_value(text, key):
    """One top-level `key = "value"` of a TOML file, without a TOML library (the
    tool is stdlib-only on Python 3.9); None when the key is not set."""
    hit = re.search(r'(?m)^\s*%s\s*=\s*"([^"]*)"' % re.escape(key), text)
    return hit.group(1) if hit else None


def codex_default():
    """(model or '', where) — the Codex app's own default, read first-hand from
    config.toml's `model =` line."""
    path = os.path.join(CODEX, "config.toml")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(262144)
    except OSError:
        return "", "%s is not there" % path
    return toml_value(text, "model") or "", path


def openai_rows():
    """One row per Codex automation: STOP for the Astra flagship or a missing model
    line (it inherits the default config.toml names, read here), OK for the model
    the settings name for routines, WARN for anything else."""
    want = str(((usage_settings().get("routine_models") or {}).get("openai"))
               or ROUTINE_OPENAI_DEFAULT)
    rows = []
    for path in sorted(glob.glob(os.path.join(CODEX, "automations", "*", "automation.toml"))):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read(262144)
        except OSError:
            continue
        name = toml_value(text, "name") or os.path.basename(os.path.dirname(path))
        status = toml_value(text, "status") or "?"
        model = toml_value(text, "model")
        if model is None:
            default, where = codex_default()
            label = ("the Astra default" if any(default.startswith(p) for p in ASTRA_PREFIXES)
                     else "the app's default")
            flag, words = "STOP", ("no model line — inherits %s (%s, from %s); write "
                                   "model = \"%s\"" % (label, default or "none named", where, want))
        elif any(model.startswith(p) for p in ASTRA_PREFIXES):
            flag, words = "STOP", "model %s — routines never run on Astra; write model = \"%s\"" % (model, want)
        elif model == want:
            flag, words = "OK ", "model %s" % model
        else:
            flag, words = "WARN", "model %s — not the routine model usage-settings.json names (%s)" % (model, want)
        rows.append({"task": name, "flag": flag.strip(), "words": words, "status": status,
                     "file": path, "vendor": "openai"})
    return rows


def template_rows():
    """The hub's routine templates (routines/*.md), judged BEFORE registration."""
    rows = []
    for path in sorted(glob.glob(os.path.join(HUB, "routines", "*.md"))):
        flag, words = claude_model_verdict(frontmatter(path))
        rows.append({"task": os.path.basename(path), "flag": flag.strip(), "words": words,
                     "file": path, "vendor": "claude"})
    return rows


def skill_path(task):
    """The SKILL.md a stored task runs: its own `filePath`, else the scheduled-tasks
    folder by its id."""
    path = task.get("filePath") or ""
    if path and os.path.isfile(path):
        return path
    return os.path.join(HOME, ".claude", "scheduled-tasks", str(task.get("id") or ""), "SKILL.md")


def iso_ms(ms):
    if not ms:
        return "never"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")



# ---------------------------------------------------------------------------
# THE BOOT NOTICE — once per boot, from the pulse's first beat
# ---------------------------------------------------------------------------

BOOT_SLACK_S = 300          # two readings of one boot's start agree within five minutes


def boot_time():
    """This machine's boot moment as epoch seconds, PROBED — never a clock guess: macOS
    `sysctl -n kern.boottime`, Windows GetTickCount64 (now minus the uptime), Linux
    /proc/stat's btime. None when none of them answers."""
    import subprocess
    import time as _t
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True,
                                 text=True, timeout=5).stdout
            hit = re.search(r"sec\s*=\s*(\d+)", out)
            if hit:
                return float(hit.group(1))
        elif os.name == "nt":
            import ctypes
            ms = ctypes.windll.kernel32.GetTickCount64
            ms.restype = ctypes.c_ulonglong
            return _t.time() - ms() / 1000.0
        else:
            with open("/proc/stat", encoding="ascii", errors="replace") as fh:
                for line in fh:
                    if line.startswith("btime"):
                        return float(line.split()[1])
    except Exception:
        pass
    return None


def state_dir():
    """The machine-local state folder the pulse keeps its own cursors in:
    EXO_PULSE_STATE_DIR, else <home>/.exocortex/pulse. Never the hub (it would sync)."""
    named = (_arg("--state-dir") or os.environ.get("EXO_PULSE_STATE_DIR") or "").strip()
    return named or os.path.join(HOME, ".exocortex", "pulse")


def machine_word():
    name = _arg("--machine")
    if name:
        return name
    for cand in (os.environ.get("EXO_MACHINE_JSON") or "",
                 os.path.join(HOME, "orchestrator-sync", "machine.json"),
                 os.path.join(HUB, "machine.json")):
        try:
            with open(cand, encoding="utf-8") as fh:
                n = str(json.load(fh).get("name") or "").strip().lower()
            if n:
                return n
        except (OSError, ValueError, AttributeError):
            continue
    return "this-machine"


def load_postman():
    """postman.py beside this file (its notifier: osascript on macOS, the toast on Windows,
    the --notify seam in every gate) — or None."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "postman.py"), os.path.join(HUB, "tools", "postman.py")):
        if os.path.isfile(cand):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("rc_postman", cand)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
            except Exception:
                return None
    return None


def boot_notice():
    """ONE notice per boot naming every routine that will ask permission; silent when all read
    Bypass. The marker is written only once the boot has been DECIDED — a notifier that failed
    is tried again at the next beat, twice at most. Exit 0 always: a beat never fails on it."""
    quiet = "--quiet" in sys.argv
    boot = _arg("--boot-id")
    boot = float(boot) if boot else boot_time()
    if boot is None:
        print("routines: the boot moment could not be read here — no boot notice")
        return 0
    folder = state_dir()
    marker = os.path.join(folder, "routines-boot-%s.json" % re.sub(r"[^a-z0-9_.-]", "-", machine_word()))
    try:
        with open(marker, encoding="utf-8") as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        prev = {}
    same = isinstance(prev, dict) and abs(float(prev.get("boot") or 0) - boot) <= BOOT_SLACK_S
    if same and prev.get("decided"):
        if not quiet:
            print("routines: already checked at this boot (%s) — %s"
                  % (prev.get("checked") or "?", prev.get("said") or "nothing said"))
        return 0
    tries = int(prev.get("tries") or 0) if same else 0
    stores = find_store()
    live = active_store(stores)
    names = [t["name"] for t in unset_tasks([live] if live else ([] if signed_in()[0] else stores))]
    body = {"boot": boot, "checked": datetime.now().astimezone().isoformat(timespec="seconds"),
            "unset": names, "tries": tries, "decided": True, "said": ""}
    if not names:
        body["said"] = "every enabled routine reads Bypass — no notice"
    else:
        text = sweep_step(names)
        pm = load_postman()
        notify = _arg("--notify") or os.environ.get("EXO_NOTIFY") or None
        how, why = ("", "postman.py is not beside this file — no notifier")
        if pm is not None:
            how, why = pm.raise_note("Exocortex", "routines", text, notify=notify)
        body["tries"] = tries + 1
        if how:
            body["said"] = "notice raised (%s): %s" % (how, text)
        elif body["tries"] < 2:
            body["decided"] = False
            body["said"] = "the notifier failed (%s) — tried again next beat" % why
        else:
            body["said"] = "the notifier failed twice (%s) — said here only: %s" % (why, text)
    try:
        os.makedirs(folder, exist_ok=True)
        tmp = marker + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(body, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, marker)
    except OSError as exc:
        body["said"] += " (the boot marker could not be written: %s)" % exc
    print("routines at boot: " + body["said"])
    return 0


# ---------------------------------------------------------------------------
# THE CATCH-UP CHECK — a routine's first step
# ---------------------------------------------------------------------------

def _cron_field(text, lo, hi):
    """The set of values one cron field allows, or None for `*` (anything)."""
    text = str(text).strip()
    if text == "*":
        return None
    out = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = max(1, int(step_s))
        if part in ("*", ""):
            a, b = lo, hi
        elif "-" in part:
            a, b = [int(x) for x in part.split("-", 1)]
        else:
            a = b = int(part)
        out.update(range(a, b + 1, step))
    if hi == 7:                         # day of week: 7 is Sunday, as 0 is
        out = set(0 if v == 7 else v for v in out)
    return out


def next_fire(cron, after):
    """The first minute strictly after `after` (a LOCAL naive datetime) that the five-field
    cron expression fires on; day-of-month and day-of-week are OR'ed when both are restricted,
    as cron does. None when nothing fires within 400 days."""
    from datetime import timedelta
    f = cron.split()
    if len(f) != 5:
        return None
    mins, hours = _cron_field(f[0], 0, 59), _cron_field(f[1], 0, 23)
    doms, months = _cron_field(f[2], 1, 31), _cron_field(f[3], 1, 12)
    dows = _cron_field(f[4], 0, 7)
    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    end = after + timedelta(days=400)
    while t <= end:
        if months is not None and t.month not in months:
            t = (t.replace(day=1, hour=0, minute=0) + timedelta(days=32)).replace(day=1)
            continue
        dow = (t.weekday() + 1) % 7
        if doms is not None and dows is not None:
            day_ok = t.day in doms or dow in dows
        else:
            day_ok = (doms is None or t.day in doms) and (dows is None or dow in dows)
        if not day_ok:
            t = t.replace(hour=0, minute=0) + timedelta(days=1)
            continue
        if hours is not None and t.hour not in hours:
            t = t.replace(minute=0) + timedelta(hours=1)
            continue
        if mins is not None and t.minute not in mins:
            t = t + timedelta(minutes=1)
            continue
        return t
    return None


def _utc(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def catch_up(task_id):
    """RUN or SKIP for this run of `task_id`, from the app's own task store: the store writes
    `lastScheduledFor` (the slot this run is for) and `lastRunAt` (when it was spawned) before
    the run's first step. SKIP when the run is a catch-up older than the task's own interval,
    and when it is a catch-up whose next regular fire is due within NEAR_MINUTES_DEFAULT (15)
    minutes — `--near-minutes N` changes that for one run, `--near-minutes 0` switches it off.
    Prints one line; exit 0 either way — the line is the answer; a --near-minutes that is not
    a number is exit 2 and says so."""
    said = _arg("--near-minutes")
    try:
        near = float(said) if said != "" else NEAR_MINUTES_DEFAULT
    except ValueError:
        print("--near-minutes wants a number of minutes (0 switches it off), not %r" % said)
        return 2
    now_arg = _arg("--now")
    now = _utc(now_arg) if now_arg else datetime.now(timezone.utc)
    best = None
    for store in find_store():
        for t in read_store(store).get("scheduledTasks") or []:
            if isinstance(t, dict) and t.get("id") == task_id:
                if best is None or str(t.get("lastRunAt") or "") > str(best.get("lastRunAt") or ""):
                    best = t
    if best is None:
        print("RUN — no task %s in the app's task store; nothing says this run is a catch-up" % task_id)
        return 0
    slot, spawned = _utc(best.get("lastScheduledFor")), _utc(best.get("lastRunAt"))
    cron = str(best.get("cronExpression") or "")
    if slot is None or spawned is None or not cron:
        print("RUN — the store does not record this run's slot; nothing says it is a catch-up")
        return 0
    local_slot = slot.astimezone().replace(tzinfo=None)
    after = next_fire(cron, local_slot)
    if after is None:
        print("RUN — the schedule %r has no next fire to measure an interval by" % cron)
        return 0
    interval = (after - local_slot).total_seconds()
    late = (spawned - slot).total_seconds()
    words = "slot %s, spawned %s, %d min late; interval %d min" % (
        local_slot.strftime("%a %H:%M"), spawned.astimezone().strftime("%a %H:%M"),
        late // 60, interval // 60)
    if late > interval:
        print("SKIP — a catch-up older than its own interval (%s): the next regular fire does "
              "this work" % words)
        return 0
    if near > 0 and late > 600:
        upcoming = next_fire(cron, now.astimezone().replace(tzinfo=None))
        if upcoming is not None:
            gap = (upcoming - now.astimezone().replace(tzinfo=None)).total_seconds() / 60.0
            if gap <= near:
                print("SKIP — a catch-up with the next regular fire due in %d min (%s)"
                      % (gap, words))
                return 0
    print("RUN — %s" % words)
    return 0

ASCII_FALLBACK = {"\u2192": "->", "\u2014": "--", "\u00b7": "-", "\u2026": "..."}


class _SafeOut:
    """stdout that never raises on a console whose code page lacks a mark (cp1252 has no →):
    the marks fall back to ASCII, anything else to '?'. A UTF-8 stdout is left untouched."""
    def __init__(self, raw):
        self.raw = raw

    def write(self, text):
        try:
            return self.raw.write(text)
        except UnicodeEncodeError:
            for mark, plain in ASCII_FALLBACK.items():
                text = text.replace(mark, plain)
            enc = getattr(self.raw, "encoding", None) or "ascii"
            return self.raw.write(text.encode(enc, "replace").decode(enc, "replace"))

    def flush(self):
        return self.raw.flush()

    def __getattr__(self, name):
        return getattr(self.raw, name)


def main():
    sys.stdout = _SafeOut(sys.stdout)
    want_json = "--json" in sys.argv
    if "--boot-notice" in sys.argv:
        return boot_notice()
    if "--catch-up" in sys.argv:
        task = _arg("--catch-up")
        if not task:
            print("--catch-up wants the task id (the SKILL folder's name)")
            return 2
        return catch_up(task)
    if "--templates" in sys.argv:
        rows = template_rows()
        for r in rows:
            print("%-4s %-28s %s" % (r["flag"], r["task"], r["words"]))
        stops = [r for r in rows if r["flag"] == "STOP"]
        print("%d template(s) · %s" % (len(rows), ("%d STOP — never register a STOP" % len(stops))
                                        if stops else "none runs on Fable"))
        return 1 if stops else 0
    stores = find_store()
    if not want_json:
        print(store_line())
    if not stores:
        print("STOP: no scheduled-tasks.json found under the app's data folder (is the Claude desktop app installed here?)")
        for r in openai_rows():
            print("%-4s %-28s %s  [codex · %s]" % (r["flag"], r["task"], r["words"], r["status"]))
        return 1
    rows = []
    for store in stores:
        with open(store, encoding="utf-8") as fh:
            data = json.load(fh)
        skips = data.get("recordedSkips", {})
        for t in data.get("scheduledTasks", []):
            tid = t.get("id")
            last_run = t.get("lastRunAt")
            last_run_ms = None
            if last_run:
                try:
                    last_run_ms = datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp() * 1000
                except ValueError:
                    last_run_ms = None
            task_skips = skips.get(tid, [])
            since = [s for s in task_skips if last_run_ms is None or s.get("at", 0) > last_run_ms]
            model_flag, model_words = claude_model_verdict(frontmatter(skill_path(t)))
            enabled = t.get("enabled", True)
            unset = not t.get("permissionMode")
            rows.append({
                "unset": bool(unset and enabled),
                "model_flag": model_flag.strip(),
                "model_words": model_words,
                "task": t.get("displayName") or tid,
                "id": tid,
                "mode": t.get("permissionMode") or ("UNSET (runs in Manual \u2014 WILL PROMPT)" if enabled
                                                    else "UNSET (disabled \u2014 never fires)"),
                "cwd": t.get("cwd") or "-",
                "model": t.get("model") or "-",
                "enabled": t.get("enabled", True),
                "approvals": len(t.get("approvedPermissions") or []),
                "skips_since_last_run": len(since),
                "skips_total": len(task_skips),
                "last_run": last_run or "never",
                "store": store,
            })
    codex = openai_rows()
    if want_json:
        acct, login, src = signed_in()
        print(json.dumps({"claude": rows, "openai": codex,
                          "store": {"account": acct, "login": login, "source": src,
                                    "active": active_store(stores, acct)}}, indent=2))
        return 0
    bad = 0
    stops = 0
    for r in rows:
        flag = "OK " if r["mode"] == "bypassPermissions" else ("!! " if r["unset"] else "-- ")
        if flag == "!! ":
            bad += 1
        print(f"{flag}{r['task']:<28} mode={r['mode']:<38} folder={r['cwd']}")
        print(f"    model={r['model']} · stored exact approvals={r['approvals']} · skipped fires since last run={r['skips_since_last_run']} (total {r['skips_total']}) · last run {r['last_run']}")
        if r["model_flag"] != "OK":
            stops += 1 if r["model_flag"] == "STOP" else 0
        print(f"    {r['model_flag']:<4} {r['model_words']}")
    for r in codex:
        if r["flag"] == "STOP":
            stops += 1
        print(f"{r['flag']:<4} {r['task']:<28} {r['words']}  [codex · {r['status']}]")
    prompting, elsewhere = prompting_split(rows, stores)
    if elsewhere:
        print("(another account's store, not signed in here \u2014 its tasks run only when it is: "
              "%d unset: %s)" % (len(elsewhere), ", ".join(elsewhere)))
    bad = len(prompting)
    if prompting:
        # the count and the fix as ONE sweep-list step. At the next boot the app runs
        # each of these once (its catch-up of the latest missed fire), and each run stops at its
        # first command that needs a click — at least one prompt per task, so N at the least.
        print("WILL PROMPT \u2014 %d prompt%s at the next boot (at least one per task: the app catches "
              "up each task's latest missed fire once, and a Manual run stops at its first command)"
              % (len(prompting), "" if len(prompting) == 1 else "s"))
        print("STEP: " + sweep_step(prompting))
    tail = f"{len(rows)} task(s) · {bad} still prompting" if bad else f"{len(rows)} task(s) · all run without prompts"
    tail += f" · {len(codex)} codex automation(s)"
    tail += f" · {stops} STOP — a routine that can run on Fable or Astra" if stops else " · none runs on Fable or Astra"
    print(tail)
    return 1 if (bad or stops) else 0


if __name__ == "__main__":
    sys.exit(main())
