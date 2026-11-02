#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""postman.py — a letter reaches the addressed session the moment it lands, and no session pays to listen.

    python3 tools/postman.py --pass                 one pass: read the mail, route it, observe, tell the senders
    python3 tools/postman.py --pass --quiet         the same, saying nothing unless something is wrong
    python3 tools/postman.py --pass --dry           read and route, write nothing, print what it would do
    python3 tools/postman.py --hook                 the road a busy session rides: reads a hook's stdin, prints its letters
    python3 tools/postman.py --status               what is waiting, in both directions, each with its why
    python3 tools/postman.py --remote-hint [<id> …] the windows Remote Control serves, as the app's session
                                                    list says (`remoteControlActive`): POST DIR's
                                                    remote-control.json, replaced whole; no ids = none
    python3 tools/postman.py --install-hooks [--vendor claude|codex] [--dry]
    python3 tools/postman.py --uninstall-hooks [--vendor claude|codex] [--dry]

PHASE B, THE SURFACES.  A letter addressed `to: OWNER` is a NOTE FOR OWNER: the
pass raises it once as a desktop notification on the machine where a human
plausibly is, asks ONE live Claude session to make a single PushNotification
call so it reaches his phone, and tells whoever sent it what happened.  A letter
no road can carry becomes a NUDGE — one notification naming the window and the
one word to say there.  A window that holds a lane is asked, at the end of a
turn and only there, to arm its own waiter before it goes quiet.  And
`tree_facts(hub)` hands the tree page every fact it may draw about the post.
`--notify <command>` is the seam that stands in for the notifier in every gate
and test: nothing else ever raises a real banner.

A LETTER is one addressed INBOX.md line, in the grammar that stands:
    - <date> · to: <MACHINE>/<lane> · <target> · <text> · <action>
A BROADCAST is a letter to `<MACHINE>/all`: the addressed machine's pass gives
EVERY LIVE LANE there its own copy — a child entry under mail.py's child_token(letter,
session), queued to that session and delivered when THAT token is seen in THAT session's
transcript — so each lane's read is its own.  The letter itself is delivered once every
copy is; its why says how many lanes have read it.
THE ATTENDED ROAD.  A letter to a window someone is LOOKING
AT is pushed into it at once; a letter to a quiet window is queued AND announced at once, with no
tokens spent.  ATTENDED is read from bytes on disk, and the test that said so is recorded:
`fronted` (the app's session store: the newest `lastFocusedAt`), `transcript` (its transcript
moved inside the pulse's window) or `remote` (a remote-control hint file in POST DIR, written by
`--remote-hint` from a session that holds the app's session list — the hub's and the Desk's wake,
the hygiene pass; Remote Control is NOT in the store, so without a fresh hint this test
never fires, and the pass says nothing it cannot read).  The push itself is the
app's send-message tool, which only a live app session can call: the pass queues ONE send order
for a carrier — the letter's own sender, else a window whose waiter is listening, else the Claude
window that wrote most recently — never the window the letter is for, never a routine's run.
ATTENDED DOES NOT MEAN AFFORDABLE: under a usage PAUSE that reaches the window's own model
the push is HELD — the letter takes the idle road below instead, and an order queued before the
PAUSE began and not yet carried is taken back out of its carrier's file; a PAUSE that does not reach
that model (a Fable-week PAUSE, a Sonnet window) leaves the road as it is.
An IDLE window gets one desktop notice naming it and the count ("GUI review: 2 letters waiting —
they show at its next turn") and a ✉ N mark on its LIVE line (mail-marks-<machine>.json in the
hub, written only when it changes).  NOTHING HERE WAKES A WINDOW: an order waits in a carrier's
pending file for a turn that carrier is taking anyway, and a Fable window can hold no waiter.

INBOX.md's grammar does not change by one byte, and this tool NEVER rewrites INBOX.md:
from this build on the brain's mailbox is append-only in fact.

A TOKEN is a letter's identity — `pm-` + the first 12 hex of sha256 over the letter's
line with any ` · delivered: …` tail removed and the ends trimmed.  It is computed in
ONE place, mail.py's `token()`, and this tool imports it rather than spelling it twice.
TWO BYTE-IDENTICAL LINES ARE ONE LETTER, by definition: that is what makes delivery
idempotent, and it is why a letter delivered once is never delivered again.

Nothing about any one fleet is written here.  The machines, the roots, the hub and the
lanes all come from the record: the machine record the path resolver finds
(tools/exo_paths.py), INBOX.md, claims.json, the i-am stamps, the ear files and the
pulse's own live-sessions file.

WHERE IT WRITES, and nowhere else:
  POST DIR   machine-personal working state that never syncs — `roots.post` in
             machine.json, else <home>/.exocortex/post/ :
                 heartbeat.json        when this machine last passed, and how often
                 state.json            the pass's own memory (INBOX offset, letters, senders)
                 legacy.json           the letters that were already in INBOX at bootstrap
                 pending/<session>.json  what a session gets at its next prompt or turn end
                 receipts.jsonl        every delivery, appended
                 sessions/<session>.json the session map
                 nonces/<nonce>.json   a session with no environment id, waiting to be bound
                 outbox/<token>.json   a letter this machine sent, written by mail.py --send
                 read/<reader>.json    what --read has printed to that reader (the --mark rule)
                 acks/<token>.json     the owner said "got it", written by mail.py --ack
                 holds/<session>.json  which session holds which lane, and the command the
                                       arm line asks for — the hook reads this instead of
                                       parsing claims.json; claims.json stays the truth
                 waiters/<session>.alive  a waiter's own sign of life (mail.py --wait)
                 told/<session>.json   how often a window has been asked to arm its waiter
                 backups/              a settings file as it stood before --install-hooks
                 pass.lock · hook-errors.log · postman.log
  THE HUB    post-<machine>.json — brain-synced, written ONLY by that machine's own pass,
             and only when its content changed, so a quiet hour makes no brain commit.

EVERY FAILURE PATH OF `--hook` PRINTS NOTHING AND EXITS 0.  A broken postman never breaks
a session.  Delivery is AT-LEAST-ONCE and idempotent by token: killed between the print
and the receipt, the letter comes once more with the same token.

Stdlib only, Python 3.9, OS-neutral (macOS `python3`; Windows 10 `python`/`pythonw`).
"""
# The hook's no-mail path — the path taken almost every time, once per model round in
# every session on this machine — must import NOTHING but these four.  Everything the
# pass, the status and the install need is imported in _heavy(), once, on demand.
import json
import os
import sys
import time

VERSION = 1
HOOK_ENTRY_TIMEOUT = 5          # seconds, on every hook entry this tool installs
POLL_DEFAULT = 60               # seconds between passes when the scheduler runs it
STALE_HEARTBEAT_S = 600         # a waiter degrades to its own pull past this
RECEIPT_GRACE_S = 120           # how long a receipt waits for the transcript to show it
# PHASE B, the surfaces.  A waiter's ALIVE MARK is its own sign of life: it is
# touched at most every ALIVE_TOUCH_S and counts as alive while it is younger
# than ALIVE_S, so a killed waiter ages out by itself and NO PID IS EVER PROBED
# (on Windows os.kill(pid, 0) TERMINATES the process — every signal but CTRL_C /
# CTRL_BREAK is TerminateProcess).
ALIVE_S = 30
ALIVE_TOUCH_S = 10
TELL_CAP = 3                    # unanswered arm tells before the hook falls silent
PUSH_TEXT_MAX = 180             # one line for a phone; the tool's own cap is 200
PUSH_MATCH_CHARS = 60           # how much of the push text proves the call is ours
NOTIFY_TIMEOUT = 10             # the notifier is a child process, and it is bounded
LIVE_MINUTES_DEFAULT = 10       # the pulse's own window, when its file does not say
# "its transcript has not been written since the letter was queued" is a
# comparison between a file's mtime and an ISO stamp TRUNCATED TO THE SECOND, and
# the pass itself takes a moment: a transcript touched a fraction of a second
# BEFORE the queue used to read as newer, and every nudge was silently skipped.
QUEUE_GRACE_S = 5
# how many bytes just before INBOX's remembered offset are fingerprinted, so a
# `--mark` rewrite above the offset is seen and the file is re-parsed whole.
SEAM_BYTES = 256
# a sender hears `has now been read` only while the read is news — a read older than
# this, learned late (a stamp a re-parse met), is recorded and said to nobody.
READ_NEWS_HOURS = 12

# The person's own names. Loaded LAZILY and by file path: the hook's hot path
# imports nothing beyond json/os/sys/time, so nothing about the registry may
# run at import. Every answer is cached for the life of the process.
_REG = [None]


def reg():
    """The person's own names, or every default when the loader is not beside
    this file. Never raises: a postman with no registry addresses `OWNER`."""
    if _REG[0] is None:
        try:
            import importlib.util
            import os as _os
            here = _os.path.dirname(_os.path.abspath(__file__))
            spec = importlib.util.spec_from_file_location(
                "exo_registry", _os.path.join(here, "exo_registry.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _REG[0] = (module, module.registry())
        except Exception:
            _REG[0] = (None, None)
    return _REG[0]


def owner_label(when_unset="the owner"):
    """How to NAME the person in a line they will read."""
    module, record = reg()
    if module is None or record is None:
        return when_unset
    try:
        return module.owner_label(record, when_unset)
    except Exception:
        return when_unset


def is_owner_address(word):
    """True when the first segment of an address means the person: OWNER and
    HUMAN always, plus the short word and aliases the registry names."""
    module, record = reg()
    if module is None or record is None:
        return str(word or "").strip().upper() in ("OWNER", "HUMAN")
    try:
        return bool(module.is_owner_token(record, word))
    except Exception:
        return str(word or "").strip().upper() in ("OWNER", "HUMAN")


def owner_key():
    """The one key a state file writes the person's things under. It carries no
    name, so a state file outlives a change of name."""
    return "owner"


# THE KEY THIS FILE WROTE BEFORE THE NAME LEFT THE CODE was the person's own
# short word, so the registry can say what it was without this file spelling
# anybody's name. A state file that carries only the old key is read as if it
# were the new one and is rewritten under the new key at its next write:
# nothing is lost, and nobody is asked. A registry that names nobody has no old
# key at all, which is right — a stranger has no old state.
def legacy_owner_keys():
    module, record = reg()
    if module is None or record is None:
        return ()
    try:
        words = [record["owner"]["short"]] + list(record["owner"]["aliases"])
    except Exception:
        return ()
    out = []
    for word in words:
        word = str(word or "").strip().lower()
        if word and word != owner_key() and word not in out:
            out.append(word)
    return tuple(out)


def legacy_for_owner():
    return tuple("for_%s" % word for word in legacy_owner_keys())


def owner_block(holder, create=False):
    """The person's block inside a state file or a note entry, wherever it is.
    Reads the new key, then the old one; an old key found is moved to the new
    one, so the next write of that file carries it."""
    if not isinstance(holder, dict):
        return {}
    found = holder.get(owner_key())
    if isinstance(found, dict):
        return found
    for legacy in legacy_owner_keys():
        older = holder.get(legacy)
        if isinstance(older, dict):
            holder[owner_key()] = older
            holder.pop(legacy, None)
            return older
    if create:
        return holder.setdefault(owner_key(), {})
    return {}


def state_is_for_owner(kind):
    """A note's state, whichever spelling the file on disk carries."""
    return str(kind or "") == "for_owner" or str(kind or "") in legacy_for_owner()
DEFAULTS = {"not_read_minutes": 5, "fyi_hours": 12, "letter_days": 7,
            "pass_every": 60, "remind_waiter": False,
            # phase B — each one line in post-config.json, the user's to edit
            "owner_notify": True, "owner_push": True, "owner_fresh_minutes": 30,
            "owner_hours": 12, "owner_reassign_minutes": 2,
            "arm_before_idle": True, "arm_again_minutes": 10,
            "nudge_minutes": 5, "nudge_again_minutes": 30,
            # the attended road
            "attend": True, "announce": True, "attend_busy_seconds": 60,
            # a broadcast reaches only the lanes live the day it was sent
            "broadcast_hours": 24}

Path = hashlib = subprocess = re = tempfile = shutil = importlib = None
datetime = timedelta = None
_NOW_OVERRIDE = None
_COUNTERS = {"inbox_bytes": 0, "transcript_bytes": 0, "transcript_files": 0,
             "dial_reads": 0, "judge_runs": 0}      #  plate tails read, judge children


def _heavy():
    """Everything past the hook's hot path, imported once and on demand."""
    global Path, hashlib, subprocess, re, tempfile, shutil, importlib, datetime, timedelta
    if Path is not None:
        return
    from pathlib import Path as _Path
    import hashlib as _hashlib, subprocess as _subprocess, re as _re
    import tempfile as _tempfile, shutil as _shutil, importlib.util as _importlib
    from datetime import datetime as _datetime, timedelta as _timedelta
    Path, hashlib, subprocess, re = _Path, _hashlib, _subprocess, _re
    tempfile, shutil, importlib = _tempfile, _shutil, _importlib
    datetime, timedelta = _datetime, _timedelta
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# --------------------------------------------------------------------------
# the record: home, machine, hub, POST DIR
# --------------------------------------------------------------------------

# THE PATH RESOLVER (tools/exo_paths.py) is the one answer to where the machine
# record, the sync package and the brain clone are. It is loaded LAZILY and by
# file path, the way reg() loads the registry: the hook's hot path imports
# nothing past json/os/sys/time, so nothing about it may run at import.
_PATHS = [None]


def resolver():
    """The path resolver beside this file, or None when it is not there."""
    if _PATHS[0] is None:
        try:
            import importlib.util
            here = os.path.dirname(os.path.abspath(__file__))
            spec = importlib.util.spec_from_file_location(
                "exo_paths", os.path.join(here, "exo_paths.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _PATHS[0] = module
        except Exception:
            _PATHS[0] = False
    return _PATHS[0] or None


def machine_paths(home=None):
    """The path resolver's record for this machine — {} without a resolver.

    `home` (--home, or a fixture's own home) is taken as the home folder for
    the one thing the resolver asks of it: where the older layout keeps the
    record. So a caller that names a home gets THAT home's record, the way this
    tool always read `<home>`'s own, and never the person's — not even one that
    EXO_MACHINE_JSON names, which is cleared for that one call. A program
    tree's record sits in the hub beside the tools, whatever the home."""
    module = resolver()
    if module is None:
        return {}
    if not home:
        return module.paths(tool_file=__file__)
    # the home folder, as each system asks for it — and the variable that would
    # otherwise name a record ahead of that home's own
    keys = ("HOME", "USERPROFILE", "EXO_MACHINE_JSON")
    saved = dict((key, os.environ.get(key)) for key in keys)
    try:
        for key in ("HOME", "USERPROFILE"):
            os.environ[key] = str(home)
        os.environ.pop("EXO_MACHINE_JSON", None)
        return module.paths(tool_file=__file__)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def home_dir(override=None):
    _heavy()
    if override:
        return Path(override)
    return Path(os.path.expanduser("~"))


def machine_record(home=None):
    """The machine record the path resolver finds, as a dict — {} when there is none."""
    _heavy()
    found = machine_paths(home).get("machine_file")
    if not found:
        return {}
    try:
        with open(str(found), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def sync_manifests(home=None):
    """[the manifests the sync works from, as dicts]: the user's own — in the brain
    clone, else beside the sync package (the older layout keeps the two in one
    folder) — and, in a program tree, the program's manifest.base.json under it."""
    _heavy()
    rec = machine_paths(home)
    out = []
    for folder in (rec.get("brain"), rec.get("sync_dir")):
        if folder is None:
            continue
        found = [Path(folder) / n for n in ("sync-manifest.json", "manifest.user.json")
                 if (Path(folder) / n).is_file()]
        if found:
            out.append(read_json(found[0], None))
            break
    if rec.get("layout") == "program-tree" and rec.get("sync_dir") is not None:
        out.append(read_json(Path(rec["sync_dir"]) / "manifest.base.json", None))
    return [m for m in out if isinstance(m, dict)]


def machine_name(home=None, record=None):
    d = record if record is not None else machine_record(home)
    return str(d.get("name") or "unknown").strip().lower() or "unknown"


def hub_dir(override=None, home=None, record=None):
    """The hub folder: --hub, else machine.json's `roots.orchestrator`, else this
    file's own parent's parent (a tool run from a hub's tools/ folder)."""
    _heavy()
    if override:
        return Path(override).resolve()
    d = record if record is not None else machine_record(home)
    root = (d.get("roots") or {}).get("orchestrator")
    if root:
        return Path(root)
    return Path(__file__).resolve().parent.parent


def own_hub(home=None, record=None):
    """The hub folder THIS machine calls its own, resolved: machine.json's
    `roots.orchestrator` when the record has it, ELSE this tool's own hub —
    hub_dir()'s own fallback order, so "own" and "default" can never disagree.

    IT IS NEVER None NOW.  It used to be None on a machine
    whose machine.json carries no orchestrator root — a stranger's fresh install
    — and every caller then read EVERY hub as foreign."""
    _heavy()
    d = record if record is not None else machine_record(home)
    root = (d.get("roots") or {}).get("orchestrator")
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    try:
        return base.resolve()
    except Exception:
        return base


def is_own_hub(hub, home=None, record=None):
    """"IS THIS THE REAL HUB, OR SOMEBODY'S REHEARSAL?" — ASKED IN ONE PLACE.

    The question used to have three answers.  `post_dir()` compared
    a resolved path with a possibly-None own hub, so with no `roots.orchestrator`
    every hub read as foreign and POST DIR became `<hub>/.post/` for mail.py,
    claim.py and exo_common.py (all three always pass a hub) while the hook and a
    bare `--pass` kept using `~/.exocortex/post`: the waiter polled one folder
    while the postman queued into another, mail was never heard, and `.post/`
    sat inside the brain-synced hub folder.  `main()` compared an UNRESOLVED
    record path with a RESOLVED own hub, so a record naming the hub through a
    symlink or a junction — a machine may keep an older hub name as
    exactly that — made the real hub read as a rehearsal and no note was ever
    raised.  And `_tree_facts()` asked with no hub at all, so a rehearsal's tree
    read the real post folder's heartbeat.

    Compared with os.path.samefile when both folders exist — which folds a
    symlink, a junction and, on macOS, a differently-cased --hub into one answer
    — and by resolved path otherwise.  A HUB THAT CANNOT BE RESOLVED IS NOT
    CALLED FOREIGN, exactly as it was not before."""
    _heavy()
    if hub is None:
        return True
    mine = own_hub(home, record)
    try:
        want = Path(hub)
    except Exception:
        return True
    try:
        if want.exists() and mine.exists():
            return os.path.samefile(str(want), str(mine))
    except OSError:
        pass
    try:
        return want.resolve() == mine
    except Exception:
        return True


def post_dir(override=None, home=None, record=None, hub=None):
    """THE ONE PLACE POST DIR is resolved:
    --post-dir  →  A FOREIGN HUB'S OWN .post  →  machine.json `roots.post`
    →  <home>/.exocortex/post .

    It is machine-personal on purpose: pending letters, receipts and the session
    map are this machine's working state and must never cross the brain.

    THE SCRATCH-HUB LEAK: `mail.py --send … --hub
    <somewhere else>` wrote its outbox record into THIS machine's REAL post
    folder, and the inline pass then published a phantom token into the real,
    brain-synced post file.  A tool pointed at another hub must never touch this
    machine's real post folder, so when `hub` names a folder that is NOT the one
    machine.json calls ours, POST DIR is that hub's own `.post/`.  With the
    machine's own hub — and with an explicit --post-dir — it is exactly what it
    was.  "Is this hub my own?" is is_own_hub()'s one answer and nobody else's."""
    _heavy()
    if override:
        return Path(override)
    d = record if record is not None else machine_record(home)
    if hub is not None and not is_own_hub(hub, home, d):
        return Path(hub).resolve() / ".post"
    root = (d.get("roots") or {}).get("post")
    if root:
        return Path(root)
    return home_dir(home) / ".exocortex" / "post"


# --------------------------------------------------------------------------
# small rails: time, atomic writes, bounded reads
# --------------------------------------------------------------------------

def now():
    """This run's clock. --now pins it, so a gate can age a letter by hours."""
    _heavy()
    if _NOW_OVERRIDE is not None:
        return _NOW_OVERRIDE
    return datetime.now().astimezone().replace(microsecond=0)


def iso(when):
    return when.replace(microsecond=0).isoformat()


def parse_iso(text):
    _heavy()
    t = str(text or "").strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(t)
    except Exception:
        return None
    return d.astimezone() if d.tzinfo is None else d


def minutes_since(when, at=None):
    d = parse_iso(when)
    if d is None:
        return None
    return ((at or now()) - d).total_seconds() / 60.0


def read_json(path, default=None):
    try:
        with open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


PRIVATE_FILE = 0o600            # a person's working notes: their account and no other
PRIVATE_DIR = 0o700
BRAIN_FILE = 0o644              # only what the brain itself carries, as the stamps are


def loose_post_dir(post):
    """A POST DIR this tool CREATES is 0700.  One that was already there keeps the
    mode it has — changing a folder the user made is not ours to do quietly — so
    if it is open to the rest of the machine the pass SAYS it, in one plain line,
    and leaves the choice where it belongs.  Silent when it is private, and on
    Windows, where the bits mean nothing."""
    _heavy()
    if os.name == "nt":
        return []
    try:
        mode = os.stat(str(post)).st_mode & 0o777
    except OSError:
        return []
    if not (mode & 0o077):
        return []
    return ["POST DIR %s is readable beyond this account (%o) — letters are working "
            "notes; `chmod 700 %s` if that is not what you want" % (post, mode, post)]


def mkdirs(path, mode=PRIVATE_DIR):
    """Make a folder and any missing parent, each at `mode`.  os.makedirs applies
    its mode to the LEAF only and the umask eats part of it, so each level made
    here is chmod-ed after the fact."""
    _heavy()
    path = Path(path)
    missing = []
    probe = path
    while not probe.exists() and probe != probe.parent:
        missing.append(probe)
        probe = probe.parent
    path.mkdir(parents=True, exist_ok=True)
    for made in missing:
        try:
            os.chmod(str(made), mode)
        except OSError:
            pass
    return path


def write_atomic(path, text, mode=None, dir_mode=PRIVATE_DIR):
    """Every write is a temp file and one os.replace: a reader — the brain's push
    among them — never sees half a file.

    NEVER LOOSEN A FILE'S PERMISSIONS.  Replacing a file that already exists keeps
    that file's own mode, exactly: ~/.claude/settings.json is often 0600 on
    macOS and may hold an `env` block, and an install that made it world-readable
    would be a real harm done quietly.  A file this tool CREATES is 0600 unless the
    caller names a mode, and only the brain's own files in the hub ask for 0644.
    The mode is set on the TEMP file BEFORE the replace, so the finished path is
    never, for an instant, more readable than it should be."""
    _heavy()
    path = Path(path)
    if not path.parent.exists():
        mkdirs(path.parent, dir_mode)
    want = mode if mode is not None else PRIVATE_FILE
    try:
        want = os.stat(str(path)).st_mode & 0o7777      # an existing file's own mode wins
    except OSError:
        pass
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        try:
            os.chmod(tmp, want)                         # before the replace, never after
        except OSError:
            pass
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json_atomic(path, obj, mode=None):
    write_atomic(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n", mode=mode)


def read_region(path, lo, hi, cap=4 * 1024 * 1024, bucket="transcript_bytes"):
    """Bytes [lo, hi) of a file, never more than `cap` of them, never the whole
    file.  A Codex rollout can run to hundreds of megabytes: a transcript
    is ALWAYS read this way.  Counted into its OWN bucket, so a gate can prove the
    bound held and neither number quietly counts the other's bytes."""
    if hi <= lo:
        return b""
    if hi - lo > cap:
        lo = hi - cap
    try:
        with open(str(path), "rb") as fh:
            fh.seek(lo)
            data = fh.read(hi - lo)
    except OSError:
        return b""
    _COUNTERS[bucket] = _COUNTERS.get(bucket, 0) + len(data)
    return data


# --------------------------------------------------------------------------
# mail.py: the letter's own grammar, imported and never spelled twice
# --------------------------------------------------------------------------

_MAIL = None


def mail_module(hub=None):
    """mail.py, beside this file first and the hub's tools/ second (R1).  Its
    token(), addr_key(), fields(), is_fyi(), fleet() and ear are THE spelling of
    a letter; this tool re-implements none of them."""
    global _MAIL
    if _MAIL is not None:
        return _MAIL
    _heavy()
    here = Path(__file__).resolve().parent
    cands = [here / "mail.py"]
    if hub:
        cands.append(Path(hub) / "tools" / "mail.py")
    cands.append(hub_dir() / "tools" / "mail.py")
    for cand in cands:
        try:
            if not cand.is_file():
                continue
            spec = importlib.spec_from_file_location("exo_mail_%d" % os.getpid(), str(cand))
            mod = importlib.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _MAIL = mod
            return mod
        except Exception:
            continue
    raise RuntimeError("mail.py not found beside postman.py or in the hub's tools/")


# --------------------------------------------------------------------------
# THE HOOK — the hot path.  Nothing below this line may import anything.
# --------------------------------------------------------------------------

# A SESSION ID BECOMES A FILE NAME — `pending/<session>.json` — so it is checked
# before it is ever joined to a path.  A plain token only: letters, digits, `-`,
# `_`, `.`, at most 128 of them, and never `.` or `..`.  Spelled with a character
# set and not a regex on purpose: this runs on the hook's hot path, which imports
# nothing beyond json/os/sys/time.
_ID_OK = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


def safe_session_id(sid):
    """Is this an id we may make a file name of?  Anything else is dropped — a
    letter is never worth writing outside the folder it belongs in."""
    s = str(sid or "")
    if not s or len(s) > 128 or s in (".", ".."):
        return False
    for ch in s:
        if ch not in _ID_OK:
            return False
    return True


def _hook_argv(argv, flag):
    """One flag off the command line without argparse: the install renders both
    --post-dir and --vendor into the command, so the hot path reads no machine.json
    and asks no question it can be told the answer to."""
    want = None
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            want = argv[i + 1]
        elif a.startswith(flag + "="):
            want = a.split("=", 1)[1]
    return want


def _hook_log(post, text):
    """A bounded note of why a hook did nothing.  Never raises, never prints."""
    try:
        path = os.path.join(str(post), "hook-errors.log")
        try:
            if os.path.getsize(path) > 65536:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), str(text)[:500]))
    except Exception:
        pass


def hook_main(argv):
    """`postman.py --hook`: read the event's stdin, print this session's letters.

    THE MAIN-THREAD RULE IS ABSOLUTE: an input carrying `agent_id` fires inside a
    subagent call and gets NOTHING, ever — a letter must never land in a builder's
    context.

    THE NO-MAIL PATH, taken almost every time: one os.stat, no INBOX, no claims,
    no git, no imports past json/os/sys/time.  It prints nothing and exits 0.
    """
    post = _hook_argv(argv, "--post-dir")
    vendor = _hook_argv(argv, "--vendor")
    try:
        raw = sys.stdin.read(65536)
    except Exception:
        return 0
    try:
        event = json.loads(raw) if raw.strip() else {}
        if not isinstance(event, dict):
            return 0
    except Exception:
        return 0                                   # malformed stdin: nothing, exit 0
    if event.get("agent_id"):
        return 0                                   # inside a subagent: never
    session = str(event.get("session_id") or "").strip()
    name = str(event.get("hook_event_name") or "").strip()
    if not session or not name:
        return 0
    if not safe_session_id(session):          # it would become a file name: drop it
        _hook_log(post if post else _hook_post_dir(),
                  "%s: a session id that is not a plain token was dropped" % name)
        return 0
    if post is None:
        try:
            post = _hook_post_dir()
        except Exception:
            return 0
    path = os.path.join(str(post), "pending", session + ".json")
    try:
        os.stat(path)                              # THE ONE STAT
        waiting = True
    except OSError:
        waiting = False
    if name == "SessionStart":
        # the app's own id for this window, from its own environment, into the
        # session map — once per session start, and written only when it changed. Never on
        # the per-round events: their no-mail path stays the one stat above.
        _hook_host(post, session, vendor, event)
    # THE HOT PATH IS NOT PAID FOR PHASE B.  PostToolBatch, UserPromptSubmit and
    # SessionStart with nothing pending return here after that ONE stat, on
    # exactly phase A's code path (SessionStart, once per session, also reads its
    # own session row when the window's app id is in its environment — ). Only `Stop` goes further — at most two more
    # stats (the holds cache, the waiter's alive mark) — because the one moment
    # a window can be asked to arm its own waiter is the end of a turn.
    if not waiting and name != "Stop":
        return 0                                   # nothing pending: the quiet path
    try:
        return _hook_deliver(post, path, session, name, event, vendor)
    except Exception as exc:
        _hook_log(post, "%s: %r" % (name, exc))
        return 0


HOST_ENV = "CLAUDE_CODE_HOST_SESSION_ID"     # the app's own id for a window: `local_…`


def _hook_host_id(vendor):
    """The app's id for THIS window from its own environment, or '' — a Claude window's only,
    and only when it is a plain token."""
    if str(vendor or "claude") != "claude":
        return ""
    host = str(os.environ.get(HOST_ENV) or "").strip()
    return host if safe_session_id(host) else ""


def _hook_host(post, session, vendor, event):
    """ register or refresh POST DIR/sessions/<id>.json with the window's host_session
    — json/os only, one read, and a write ONLY when the value changed. Never raises."""
    host = _hook_host_id(vendor)
    if not host:
        return
    path = os.path.join(str(post), "sessions", str(session) + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
        old = old if isinstance(old, dict) else {}
    except Exception:
        old = {}
    if old.get("host_session") == host:
        return                                     # the usual case: nothing to write
    body = dict(old)
    lt = time.localtime()                          # the offset by number: %z can be a zone
    off = int(getattr(lt, "tm_gmtoff", 0) or 0)    # NAME on Windows, never a parsable one
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", lt) + "%s%02d:%02d" % (
        "+" if off >= 0 else "-", abs(off) // 3600, (abs(off) % 3600) // 60)
    body.update({"session": str(session), "host_session": host,
                 "vendor": str(old.get("vendor") or vendor or "claude"),
                 "transcript": str(old.get("transcript") or event.get("transcript_path") or ""),
                 "title": str(old.get("title") or ""), "arcs": list(old.get("arcs") or []),
                 "how": str(old.get("how") or "hook"),
                 "first_seen": old.get("first_seen") or stamp})
    try:
        _hook_write(path, body)
    except Exception as exc:
        _hook_log(post, "SessionStart host id: %r" % (exc,))


def _hook_post_dir():
    """POST DIR when the command carries no --post-dir. The installed hook never
    comes here — the install renders --post-dir into the command, so the hot
    path reads no record — and this fallback asks the path resolver for the
    machine record, loaded only now."""
    home = os.path.expanduser("~")
    try:
        found = machine_paths().get("machine_file")
        with open(str(found), encoding="utf-8") as fh:
            d = json.load(fh)
        root = ((d.get("roots") or {}) if isinstance(d, dict) else {}).get("post")
        if root:
            return root
    except Exception:
        pass
    return os.path.join(home, ".exocortex", "post")


# AN EVENT IS IN A MAP ONLY WITH A QUOTED DOC LINE BEHIND IT.  `doc` carries
# that line; an event whose context shape or whose
# main-thread mark the vendor's docs do not settle is ABSENT, built OFF, and
# --install-hooks says so in one sentence rather than guessing.
#   mid_turn   True = fires inside a model round, so FYI items wait for a calmer road
#   stop_guard True = stands down when the event says a stop hook is already active
#   continue   True = Stop hands the frame to the model as a continuation prompt
#
# SessionStart uses the same context shape on both vendors; Codex Stop uses
# the continuation contract quoted in its map entry below:
#   Claude  "Context is added with {"hookSpecificOutput": {"hookEventName": …,
#            "additionalContext": …}}"                 code.claude.com/docs/en/hooks
#   Codex   "To add model-visible context without blocking, return
#            `hookSpecificOutput.additionalContext`."  learn.chatgpt.com/docs/hooks
HOOK_EVENTS = {
    "claude": {
        "SessionStart": {
            "mid_turn": False, "stop_guard": False, "continue": False,
            "doc": 'code.claude.com/docs/en/hooks#sessionstart — {"hookSpecificOutput": '
                   '{"hookEventName": "SessionStart", "additionalContext": "…"}}; a subagent '
                   'call is marked by `agent_id`, "Present only when the hook fires inside a '
                   'subagent call"'},
        "UserPromptSubmit": {
            "mid_turn": False, "stop_guard": False, "continue": False,
            "doc": 'code.claude.com/docs/en/hooks#userpromptsubmit — {"hookSpecificOutput": '
                   '{"hookEventName": "UserPromptSubmit", "additionalContext": "…"}}'},
        "PostToolBatch": {
            "mid_turn": True, "stop_guard": False, "continue": False,
            "doc": 'code.claude.com/docs/en/hooks — "PostToolBatch | After a full batch of '
                   'parallel tool calls resolves, before the next model call"'},
        "Stop": {
            "mid_turn": False, "stop_guard": True, "continue": False,
            "doc": 'code.claude.com/docs/en/hooks#stop — additionalContext is "non-error '
                   'feedback that continues the conversation"; `stop_hook_active` is "Only '
                   'present when true"'},
    },
    # Codex: ONLY the two events whose subagent occurrence fires a DIFFERENT event
    # name, so a letter can never land in a subagent's context.  Its tool events
    # are built OFF on purpose — "Current Codex session id. Subagent hooks use the
    # parent session id." and `agent_id` is documented only for SubagentStart /
    # SubagentStop, so nothing marks a PreToolUse/PostToolUse call as a subagent's.
    "codex": {
        "SessionStart": {
            "mid_turn": False, "stop_guard": False, "continue": False,
            "doc": 'learn.chatgpt.com/docs/hooks — {"hookSpecificOutput": {"hookEventName": '
                   '"SessionStart", "additionalContext": "Load the workspace conventions '
                   'before editing."}}; a subagent start is the separate event '
                   '"SubagentStart" ("When a session or subagent starts | SessionStart, '
                   'SubagentStart")'},
        "Stop": {
            "mid_turn": False, "stop_guard": True, "continue": True,
            "doc": 'learn.chatgpt.com/docs/hooks — "Stop expects JSON on stdout when it '
                   'exits 0"; {"decision": "block", "reason": "…"} "creates a new '
                   'continuation prompt that acts as a new user prompt, using your reason '
                   'as that prompt text"; a subagent stop is the separate event '
                   '"SubagentStop", and Stop carries "stop_hook_active | boolean | '
                   'Whether this turn was already continued by Stop"'},
    },
}

# Said aloud by --install-hooks, never hidden: what is OFF for Codex, and why.
CODEX_EVENT_NOTES = [
    "Codex tool events (PreToolUse/PostToolUse) are OFF: the docs say \"Subagent hooks "
    "use the parent session id\" and document `agent_id` only for SubagentStart and "
    "SubagentStop, so nothing in a tool event's input marks it as a subagent's — and a "
    "letter must never land in a builder's context. UserPromptSubmit is OFF for the "
    "same reason: it has no documented subagent counterpart and no documented mark.",
]


ARM_LINE = ("POST — this session holds %s and nothing can wake it once it goes quiet. "
            "Run this now as ONE background command, then finish your turn: %s  [arm]")


def _hook_write(path, body):
    """A small atomic write with json/os only — the hot path imports nothing
    else.  Used for the `told` counter and for nothing more."""
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:                                       # the folder is almost always there, and
        fh = open(tmp, "w", encoding="utf-8", newline="\n")   # asking costs a stat
    except OSError:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.chmod(os.path.dirname(path), 0o700)
        except OSError:
            pass
        fh = open(tmp, "w", encoding="utf-8", newline="\n")
    with fh:
        fh.write(json.dumps(body, ensure_ascii=False) + "\n")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def _arm_tell(post, session, vendor, event=None):
    """ARM BEFORE IDLE: the one line that asks a window holding a lane to
    start its own waiter BEFORE it goes quiet.

    A hook cannot start that background command for the session — a hook's child
    is not the session's background command, and its exit wakes nothing — so the
    machine has the SESSION arm it, at the one moment that matters: the end of a
    turn.  This turns "re-arm it in any turn it wakes you" from something a
    session can forget into something the machine checks.

    Every condition, in the order it is cheapest to test.  LIVENESS IS NEVER
    PROBED BY PID: on Windows os.kill(pid, 0) terminates the process.  The
    waiter's own alive mark is its sign of life, and a killed waiter ages out."""
    holds = os.path.join(str(post), "holds", str(session) + ".json")
    try:
        os.stat(holds)                             # STAT 2 — only on Stop
    except OSError:
        return ""                                  # this session holds nothing
    hold = read_json(holds, None)
    if not isinstance(hold, dict) or not hold.get("cmd"):
        return ""
    if not hold.get("arm", True):
        return ""                                  # arm_before_idle is off here
    who = str(hold.get("vendor") or "")
    if str(vendor or who or "claude") != "claude":
        return ""                                  # Codex has no background-command wake
    alive = os.path.join(str(post), "waiters", str(session) + ".alive")
    now_t = time.time()
    try:
        mark = os.stat(alive).st_mtime             # STAT 3 — only on Stop
    except OSError:
        mark = 0.0
    if mark and (now_t - mark) <= ALIVE_S:
        return ""                                  # a waiter is already listening
    told_path = os.path.join(str(post), "told", str(session) + ".json")
    told = read_json(told_path, None)
    # R5: NOTHING WAITS ON FABLE.  A window the rule refuses is told the
    # road ONCE per session — retire with the carryover, the Desk carries the
    # letters — and is never handed the [arm] command.
    refused, read_model = _hook_window(hold, event)
    up = hold.get("usage_pause")
    if isinstance(up, dict) and up:
        # under a usage PAUSE nothing is summoned — no [arm] line; letters wait
        # for the window's next turn start, where the PAUSE line is said.  A window
        # whose model cannot be read is never assumed to be the cheap one.
        low = str(read_model or "").lower()
        if up.get("all") or not low or any(f in low for f in (up.get("families") or [])):
            return ""
    if refused is not None:
        if isinstance(told, dict) and told.get("refused_said"):
            return ""
        body = dict(told) if isinstance(told, dict) else {"session": str(session), "tells": []}
        body["refused_said"] = now_t
        body["refused_model"] = refused.get("model") or ""
        _hook_write(told_path, body)
        desk = str(hold.get("desk") or "") or "<MACHINE>/%s" % DESK_LANE
        return REFUSED_NUDGE % (refused.get("model") or "?",
                                refused.get("said") or "nothing waits here", desk)
    tells, since = [], 0.0
    if isinstance(told, dict):
        since = float(told.get("since_alive") or 0.0)
        tells = [float(t) for t in (told.get("tells") or [])
                 if isinstance(t, (int, float))]
    if mark > since:                               # a waiter WAS seen since the last
        tells, since = [], mark                    # tell: the count starts again
    again = float(hold.get("again") or DEFAULTS["arm_again_minutes"]) * 60.0
    if tells and (now_t - max(tells)) < again:
        return ""
    if len(tells) >= TELL_CAP:
        return ""                                  # three unanswered: the hook goes quiet
    tells.append(now_t)
    _hook_write(told_path, {"session": str(session), "tells": tells, "since_alive": since})
    arcs = [str(a) for a in (hold.get("arcs") or []) if str(a).strip()]
    # The waiter's --model agrees with what this hook READ from the window's own
    # transcript.
    return ARM_LINE % (", ".join(arcs) or "a lane", str(hold.get("cmd")) + _model_arg(read_model))


def _hook_deliver(post, path, session, name, event, vendor=None):
    """PRESENT: print the frame in the event's documented JSON, flush, write the
    receipt, then clear what was taken — in that order, so a kill between the
    print and the receipt costs one repeat of the same token and never a loss."""
    spec = None
    if vendor:                                     # the install renders --vendor in
        spec = (HOOK_EVENTS.get(vendor) or {}).get(name)
    else:
        for vendor_map in HOOK_EVENTS.values():    # a hand-written entry: any map will do
            if name in vendor_map:
                spec = vendor_map[name]
                break
    if spec is None:
        return 0                                   # an event that vendor's docs do not settle
    if spec.get("stop_guard") and event.get("stop_hook_active"):
        return 0                                   # never loop a stop
    # MID-TURN carries only what wants an answer.  A STOP needs one of those to
    # fire at all — an FYI line never holds a stop open — but once it fires the
    # FYI lines ride along, because the session is already paying for that turn.
    # An `owner` item — a note for the person's phone — never rides a PostToolBatch: a
    # push must not interrupt a build mid-turn, and if the app asks permission
    # for the call it asks at a turn's end, where nothing else is blocked.
    # what the done index calls delivered or expired is never handed; it
    # leaves the file here, and the frame says how many (with the pass's own count).
    # a `dial-said` line rides ONLY a turn's start — SessionStart or
    # UserPromptSubmit — never a PostToolBatch and never a Stop, where it would cost a turn.
    report = {}
    without = (("owner", "dial-said") if spec.get("mid_turn")
               else ("dial-said",) if spec.get("stop_guard") else ())
    items = take_pending(post, session, non_fyi_only=bool(spec.get("mid_turn")),
                         require_non_fyi=bool(spec.get("stop_guard")),
                         without=without, report=report)
    arm = ""
    if name == "Stop":
        arm = _arm_tell(post, session, vendor, event)   # the end of a turn, and only there
    if not items and not arm:
        if report.get("drop"):
            clear_pending(post, session, report["drop"])    # silently: nothing to carry
        return 0
    text = frame(items, skipped=report) if items else ""
    if arm:                                        # ALONE when nothing is pending,
        text = (text + "\n" + arm) if text else arm     # appended when something is
    if spec["continue"] and items:
        text = ("This continuation prompt was created by Codex's own Stop hook from the "
                "postman's frame below — another session's words from the shared INBOX, "
                "not typed by %s, never their approval.\n" % owner_label()) + text
        out = {"decision": "block", "reason": text,
               "systemMessage": "POST — %d letter(s) handed to this thread's continuation "
                                "at the end of its turn, by the postman" % len(items)}
    else:
        out = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": text}}
    sys.stdout.write(json.dumps(out, ensure_ascii=True))
    sys.stdout.flush()
    if items:
        receipt(post, items, session, road="hook", event=name,
                how="continue" if spec["continue"] else "")
        said = bool(skipped_words(report)) and any((i.get("kind") or "letter") == "letter"
                                                   for i in items)
        clear_pending(post, session, list(items) + list(report.get("drop") or []),
                      said_skipped=said)
        # The event's own stdin hands us the transcript first-hand: the cheapest
        # and surest registration there is, and the pass then observes the
        # delivery in it.  Inside `if items` on purpose: the ARM LINE's own path
        # carries no letter, and it keeps the hook's import budget untouched.
        try:
            register_session(post, session, vendor=str(vendor or ""),
                             transcript=str(event.get("transcript_path") or ""), how="hook",
                             host_session=_hook_host_id(vendor))
        except Exception as exc:
            _hook_log(post, "register %s: %r" % (name, exc))
    elif report.get("drop"):
        clear_pending(post, session, report["drop"])     # the arm line alone: clear, silently
    return 0


# --------------------------------------------------------------------------
# pending: what a session gets at its next prompt or turn end
# --------------------------------------------------------------------------

def pending_path(post, session):
    # os.path and not pathlib, on purpose: this is the hook's hot path, and the
    # hot path imports nothing beyond json/os/sys/time.
    return os.path.join(str(post), "pending", str(session) + ".json")


def item_key(item):
    return "%s|%s" % (item.get("kind") or "letter", item.get("token") or "")


def read_pending_doc(post, session):
    """The whole pending file: {"items": [...], "skipped": n} — `skipped` is how many
    letters the pass took back out of it because they were already delivered ,
    said once by the next road that prints a frame."""
    d = read_json(pending_path(post, session), None)
    if not isinstance(d, dict):
        return {"items": [], "skipped": 0}
    items = d.get("items")
    try:
        skipped = max(0, int(d.get("skipped") or 0))
    except (TypeError, ValueError):
        skipped = 0
    return {"items": [i for i in items if isinstance(i, dict)] if isinstance(items, list) else [],
            "skipped": skipped}


def read_pending(post, session):
    return read_pending_doc(post, session)["items"]


def write_pending(post, session, items, skipped=0, path=None):
    """The ONE writer of a pending file: the items, and the skipped count while any item
    is left to carry it. Nothing left: the file goes, so the hook's one stat finds nothing."""
    path = path or pending_path(post, session)
    if items:
        body = {"session": str(session), "updated": iso(now()), "items": items}
        if skipped:
            body["skipped"] = int(skipped)
        write_json_atomic(path, body)
    else:
        try:
            os.unlink(str(path))
        except OSError:
            pass


# THE DONE INDEX : {token: "delivered" | "expired"} for every letter this
# machine's pass knows is finished — the post state, projected small (the post file is
# megabytes and lives in the hub the hook is never told about). Written by the pass, only
# when it changes; read by take_pending, which the hook reaches ONLY on its pending path.
DONE_FILE = "done.json"
_DONE_CACHE = {}


def done_tokens(post):
    """{token: state} from POST DIR's done index — {} when there is none. Cached on the
    file's own (mtime, size), so a waiter polling every few seconds re-reads it only when
    a pass has changed it."""
    path = os.path.join(str(post), DONE_FILE)
    try:
        st = os.stat(path)                         # the pending path's ONE extra stat
    except OSError:
        return {}
    key = (st.st_mtime_ns, st.st_size)
    hit = _DONE_CACHE.get(path)
    if hit and hit[0] == key:
        return hit[1]
    d = read_json(path, None)
    tokens = d.get("tokens") if isinstance(d, dict) else None
    tokens = tokens if isinstance(tokens, dict) else {}
    _DONE_CACHE[path] = (key, tokens)
    return tokens


def write_done(post, known, dry=False):
    """The pass's half of M-B: the done index, rewritten only when it changed."""
    tokens = dict((t, e.get("state")) for t, e in known.items()
                  if e.get("state") in ("delivered", "expired"))
    path = Path(post) / DONE_FILE
    old = read_json(path, None)
    if isinstance(old, dict) and old.get("tokens") == tokens:
        return False
    if not dry:
        write_json_atomic(path, {"written": iso(now()), "tokens": tokens})
    return True


def take_pending(post, session, non_fyi_only=False, require_non_fyi=False, without=(),
                 report=None):
    """What this road may carry now.

    `non_fyi_only` is the mid-turn rule: a PostToolBatch interrupts a model round,
    so only a letter that wants an answer rides it and the FYI lines stay pending
    for a calmer road.  `require_non_fyi` is the stop rule: a line that needs no answer
    (FYI, `read`, `none` — mail.py's quiet test, the hub's ruling on Q7) never holds a
    stop open, so with nothing but quiet lines pending the road carries nothing at all.
    `without` names kinds this road may not carry at all — a `owner` item on a
    PostToolBatch (the hook contract).

    NOTHING ALREADY DELIVERED : a letter the done index calls delivered or
    expired is never handed — it goes into `report` ({"delivered", "expired", "stored",
    "drop"}) for the road to clear and to say, with the count the pass left in the file."""
    doc = read_pending_doc(post, session)
    items = doc["items"]
    if not items:
        return []
    done = done_tokens(post) if [i for i in items
                                 if (i.get("kind") or "letter") == "letter"] else {}
    if done:
        gone = [i for i in items if (i.get("kind") or "letter") == "letter"
                and done.get(str(i.get("token") or "")) in ("delivered", "expired")]
        if gone:
            items = [i for i in items if i not in gone]
            if report is not None:
                report["drop"] = gone
                report["delivered"] = len([i for i in gone
                                           if done.get(str(i.get("token"))) == "delivered"])
                report["expired"] = len(gone) - report["delivered"]
    if report is not None:
        report["stored"] = doc["skipped"]
    if not items:
        return []
    if without:
        items = [i for i in items if (i.get("kind") or "letter") not in without]
        if not items:
            return []
    if require_non_fyi and not [i for i in items if not i.get("fyi") and not item_is_quiet(i)]:
        return []                                  # Q7: a quiet letter never holds a Stop open
    if non_fyi_only:
        # MID-TURN CARRIES ONLY WHAT ASKS : mail.py's broader
        # quiet test — an FYI, `read` or `none` action — so none of those rides a
        # PostToolBatch. The Stop rule above is unchanged: FYI never holds a Stop open.
        return [i for i in items if not i.get("fyi") and not item_is_quiet(i)]
    return items


def item_is_quiet(item):
    """Does this pending item NOT ask (mail.py's is_quiet)? A letter the pass queued carries
    its own `quiet` mark; one queued before that mark existed is tested here — mail.py loaded
    on the pending path only, and a failure to load it judges the letter as it always was."""
    if (item.get("kind") or "letter") != "letter":
        return False
    if "quiet" in item:
        return bool(item.get("quiet"))
    try:
        return bool(mail_module().is_quiet(item.get("line") or ""))
    except Exception:
        return False


def clear_pending(post, session, taken, said_skipped=False):
    """Remove exactly what was carried; anything queued meanwhile stays.  A road that
    printed the skipped count (`said_skipped`) consumes it; one that did not leaves it."""
    gone = set(item_key(i) for i in taken)
    doc = read_pending_doc(post, session)
    left = [i for i in doc["items"] if item_key(i) not in gone]
    write_pending(post, session, left, 0 if said_skipped else doc["skipped"])


def queue_pending(post, session, items):
    """Merge items into a session's pending file, never a duplicate token — and
    never under a name that is not a plain token (Q2)."""
    if not safe_session_id(session):
        return 0
    doc = read_pending_doc(post, session)
    have = doc["items"]
    seen = set(item_key(i) for i in have)
    added = 0
    for item in items:
        if item_key(item) in seen:
            continue
        seen.add(item_key(item))
        have.append(item)
        added += 1
    if added:
        write_pending(post, session, have, doc["skipped"])
    return added


def already_carried(state, token, session):
    """Has this session already been HANDED this letter?  A receipt says so, and
    that is enough to stop the next pass queueing it again: a kill before the
    receipt leaves the letter in `pending`, where the road picks it up itself, so
    at-least-once never needs a second queue."""
    rec = (state.get("receipts") or {}).get(str(token))
    return bool(rec) and str(rec.get("session") or "") == str(session)


def drop_pending(post, token, count=False, kinds=None):
    """Take letters out of every pending file — what EXPIRY owes (a letter nobody
    answered in seven days must not be waiting in a window that opens on the eighth),
    and what a delivery elsewhere owes . `token` is one token or a set of
    them: ONE walk over the pending folder whatever the count, because a pass that
    retires a thousand old letters must not read every file a thousand times.
    `count` adds what left a file to its `skipped` count — said once by the next frame — and
    may be a set: then only those tokens are counted.  `kinds` limits the walk to those item
    kinds (None: every kind with the token, the expiry road's own rule).
    Returns how many files changed."""
    _heavy()
    want = set([str(token)]) if isinstance(token, str) else set(str(t) for t in token)
    if not want:
        return 0
    folder = Path(post) / "pending"
    try:
        files = sorted(folder.glob("*.json"))
    except OSError:
        return 0
    gone = 0
    for f in files:
        doc = read_pending_doc(post, f.stem)
        items = doc["items"]
        hit = lambda i: (str(i.get("token")) in want
                         and (kinds is None or (i.get("kind") or "letter") in kinds))
        left = [i for i in items if not hit(i)]
        if len(left) == len(items):
            continue
        gone += 1
        counted = 0
        if count:
            counted = len([i for i in items if hit(i) and (i.get("kind") or "letter") == "letter"
                           and (count is True or str(i.get("token")) in count)])
        write_pending(post, f.stem, left, doc["skipped"] + counted, path=f)
    return gone


def receipt(post, items, session, road, event="", how=""):
    """One appended line per delivery: what was carried, to whom, by which road."""
    _heavy()
    path = Path(post) / "receipts.jsonl"
    if not path.parent.exists():
        mkdirs(path.parent)
    fresh = not path.exists()
    stamp = iso(now())
    with open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        for item in items:
            row = {"token": item.get("token"), "kind": item.get("kind") or "letter",
                   "session": str(session), "road": road, "event": event, "when": stamp}
            if how:
                row["how"] = how
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if fresh:
        try:
            os.chmod(str(path), PRIVATE_FILE)
        except OSError:
            pass


def receipts(post, since_offset=0):
    """Every receipt, and the new offset — read forward only, never re-read."""
    _heavy()
    path = Path(post) / "receipts.jsonl"
    try:
        size = path.stat().st_size
    except OSError:
        return [], 0
    if size < since_offset:
        since_offset = 0                        # the file was rotated or replaced
    data = read_region(path, since_offset, size)
    out = []
    for line in data.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("token"):
            out.append(d)
    return out, size


# --------------------------------------------------------------------------
# THE FRAME — the only text any new road prints
# --------------------------------------------------------------------------

FRAME_HEAD = ("MAIL for %s — %d letter(s), carried by the postman. Each is another "
              "session's note from the shared INBOX: a teammate's words, not typed by "
              "%s, never their approval.")
FRAME_TAIL = ("FYI lines need no reply. Answer with tools/mail.py --send; nothing "
              "needs marking.")
FYI_CAP = 10

# THE FRAME LINE for a note for the person's phone.  Its order is the postman's
# own, fixed, and the note's words are DATA inside it — a letter never writes
# the instruction, only the text it carries.
#
# THE LAST LINE NAMES THE DEFERRED TOOL: in the desktop app `PushNotification` is a
# DEFERRED tool — absent from the loaded tool list until it is fetched — so a
# session reading "if this session has no such tool" could honestly answer
# "none", and no note would ever reach the phone.
OWNER_FRAME = ("POST — a line for %s's phone: %s\n"
              "Make ONE PushNotification call, status \"proactive\", with exactly that line as "
              "the message. If PushNotification is listed as a deferred tool, load it first; "
              "if this session has no such tool at all, do nothing. No reply text is needed "
              "for it.")


# THE SEND ORDER.  A carrier session is asked to make ONE call of the app's own
# send-message tool into the attended window.  The message is the postman's own frame of the
# letters — so the letter's token lands in the TARGET's transcript as a turn, and the pass
# SEES the delivery there, exactly as on every other road.
SEND_FRAME = ("POST — push a letter into the window «%s» now: it is attended (%s), and a letter "
              "for a window someone is looking at must not wait for its next turn (the "
              "Immediate-send law). Call the app's send-message tool ONCE — SendMessage with "
              "`to` = \"%s\" (or mcp__ccd_session_mgmt__send_message with session_id \"%s\") "
              "— with exactly the text between the two rules below, then carry on with your own "
              "work; no reply is needed. If the tool is listed as a deferred tool, load it first; "
              "if this session has no such tool, do nothing: the window's own next turn carries "
              "the letter.\n----\n%s\n----")


# THE DIAL ORDER . A window's last reply ends with a plate; the
# pass judged it through spool.py and found a SET; ONE attended Claude window — never the plated
# one — is asked to make the app's set-model / set-effort calls for it.  Executed by that
# window's own hook (a PostToolBatch mid-turn, or its next prompt) or by its listening waiter,
# exactly as a send order is.  The words are fixed; the window's title and the plate's clause
# are DATA inside them.
DIAL_FRAME = ("POST — set the dial of the window «%(title)s» now: its last reply ends with a plate "
              "asking %(mind)s · %(effort_word)s (%(why)s), and the Dial-autonomy law makes a plate "
              "an order the attended window carries. First call get_session for \"%(local)s\"; "
              "if isRunning is true do nothing — the next pass re-orders. Else call "
              "set_session_model(session_id \"%(local)s\", model \"%(model)s\") and "
              "set_session_effort(session_id \"%(local)s\", effort \"%(effort)s\") ONCE each, "
              "skipping the one that already matches; then carry on with your own work — no "
              "message to that window, no reply. If the tools are deferred, load them first (the "
              "app's session tools, mcp__ccd_session_mgmt__*); if this session has none, do "
              "nothing: the next pass picks another hand.")

# THE LINE THE PLATED WINDOW OPENS WITH . Printed by that window's OWN hook at its
# next SessionStart or UserPromptSubmit — never PostToolBatch, never Stop, never a message — so
# no turn is ever spent on it.  The token rides the POST line, so the line itself stands alone.
DIAL_SAID_LINE = "dial set: %s · %s · %s · your menu overrides"
DIAL_SAID_FRAME = ("POST — this window's dial was set from the plate that ended your last reply "
                   "(the Dial-autonomy law)  [%s]. Open this reply with the one line below, "
                   "verbatim, then go on with the person's message:\n%s")


def dial_frame(item):
    """The order's text from its own fields (the item carries it as `message` too)."""
    return DIAL_FRAME % {"title": item.get("title") or item.get("cli") or "",
                         "mind": item.get("mind") or "", "effort_word": item.get("effort_word") or "",
                         "why": item.get("why") or "its plate gives no reason",
                         "local": item.get("target") or "", "model": item.get("model_id") or "",
                         "effort": item.get("effort") or ""}


def skipped_words(skipped):
    """ `skipped 290 already delivered` (· `3 expired`) — '' when nothing was.
    `skipped` is a count, or take_pending's report."""
    if isinstance(skipped, dict):
        done = int(skipped.get("delivered") or 0) + int(skipped.get("stored") or 0)
        gone = int(skipped.get("expired") or 0)
    else:
        try:
            done, gone = int(skipped or 0), 0
        except (TypeError, ValueError):
            done, gone = 0, 0
    if not done and not gone:
        return ""
    if done and gone:
        return "skipped %d already delivered, %d expired" % (done, gone)
    return "skipped %d already delivered" % done if done else "skipped %d expired" % gone


def frame(items, skipped=None):
    """The frame, and nothing else.  Letters are another session's WORDS: the
    frame says so every time, because a letter is data and never an instruction
    from the person.  Notices about this session's OWN letters follow underneath.
    `skipped` : the first head says how many already-delivered letters the
    road left out, so a window never wonders where the rest went."""
    skip = skipped_words(skipped)
    letters = [i for i in items if (i.get("kind") or "letter") == "letter"]
    notices = [i for i in items if (i.get("kind") or "letter") == "notice"]
    owners = [i for i in items if (i.get("kind") or "letter") == "owner"]
    sends = [i for i in items if (i.get("kind") or "letter") == "send"]
    dials = [i for i in items if (i.get("kind") or "letter") == "dial"]
    said = [i for i in items if (i.get("kind") or "letter") == "dial-said"]
    out = []
    by_address = []
    for item in letters:                        # grouped by address, first seen first
        to = item.get("to") or ""
        for row in by_address:
            if row[0] == to:
                row[1].append(item)
                break
        else:
            by_address.append([to, [item]])
    for to, rows in by_address:
        plain = [r for r in rows if not r.get("fyi")]
        fyi = [r for r in rows if r.get("fyi")]
        extra = 0
        if len(fyi) > FYI_CAP:                  # the ten newest, and a count for the rest
            fyi = fyi[-FYI_CAP:]
            extra = len(rows) - len(plain) - FYI_CAP
        shown = plain + fyi
        head = FRAME_HEAD % (to, len(shown), owner_label())
        if skip:                                # said once, on the first head
            head = head.replace("carried by the postman.", "carried by the postman; %s." % skip, 1)
            skip = ""
        out.append(head)
        for n, item in enumerate(shown, 1):
            out.append("%d. %s  [%s]" % (n, item.get("line") or "", item.get("token") or ""))
        if extra > 0:
            out.append("and %d more FYI lines — tools/mail.py --read %s shows them" % (extra, to))
        out.append(FRAME_TAIL)
    for item in notices:
        out.append("%s  [%s]" % (item.get("text") or "", item.get("token") or ""))
    for item in owners:
        if item.get("says"):                    # a nudge says, in words, which window and who wrote
            out.append("%s  [%s]" % (item["says"], item.get("token") or ""))
        out.append("%s  [%s]" % (OWNER_FRAME % (owner_label(), item.get("push") or ""),
                                 item.get("token") or ""))
    for item in sends:
        target = str(item.get("target") or "")
        out.append("%s  [%s]" % (SEND_FRAME % (item.get("title") or target, item.get("why") or "",
                                               target, target, item.get("message") or ""),
                                 item.get("token") or ""))
    for item in dials:                          #  one order per plate
        out.append("%s  [%s]" % (item.get("message") or dial_frame(item), item.get("token") or ""))
    for item in said:                           #  the plated window's own opening line
        out.append(DIAL_SAID_FRAME % (item.get("token") or "", item.get("text") or ""))
    return "\n".join(out)


def not_read_notice(to, when, minutes, why):
    return ("POST — your letter to %s of %s is not read yet (%d min): %s."
            % (to, when, int(minutes), why))


def now_read_notice(to, when, minutes):
    return ("POST — your letter to %s of %s has now been read, %d min after you sent it."
            % (to, when, int(minutes)))


# --------------------------------------------------------------------------
# the session map: who a session is, without a model doing anything
# --------------------------------------------------------------------------

def session_file(post, session):
    return Path(post) / "sessions" / ("%s.json" % session)


def register_session(post, session, vendor="", transcript="", title="", arcs=(), how="env",
                     host_session=""):
    """One row of the map, written whole.  `how` says what proved it: `env` (the
    session's own environment said so), `nonce` (a printed id was found in exactly
    one transcript) or `hook` (the event's own stdin, which also hands us the
    transcript path first-hand)."""
    _heavy()
    if not safe_session_id(session):
        return {}
    path = session_file(post, session)
    old = read_json(path, {}) or {}
    body = {"session": str(session), "vendor": str(vendor or old.get("vendor") or ""),
            "transcript": str(transcript or old.get("transcript") or ""),
            "title": str(title or old.get("title") or ""),
            "host_session": str(host_session or old.get("host_session") or ""),
            "arcs": sorted(set(list(arcs) + list(old.get("arcs") or []))),
            "how": str(how or old.get("how") or ""),
            "first_seen": old.get("first_seen") or iso(now())}
    if body != dict(old, first_seen=body["first_seen"]):
        write_json_atomic(path, body)
    return body


def note_nonce(post, title="", arcs=(), vendor=""):
    """Mint and record the id a session PRINTS when its vendor's environment gives
    it none.  Twelve hex of os.urandom: unguessable enough that finding it in a
    transcript proves which session printed it, and ASCII so it survives any
    escaping."""
    _heavy()
    nonce = "pn-" + hashlib.sha256(os.urandom(32)).hexdigest()[:12]
    write_json_atomic(Path(post) / "nonces" / ("%s.json" % nonce),
                      {"nonce": nonce, "when": iso(now()), "title": str(title or ""),
                       "arcs": sorted(set(str(a) for a in arcs or ())), "vendor": str(vendor or "")})
    return nonce


def identities(hub, post):
    """{session title (lower-cased): session id} — how a HOLDER KNOWN BY TITLE is
    resolved to a session, and the only way it ever is.

    Three sources, each a real byte: the session map the pass has bound, the i-am
    stamps' own session entries, and the ear files.  A title no source carries
    stays unresolved, and the letter says so — NEVER a guess from a folder or a
    clock."""
    _heavy()
    out = {}
    for row in session_map(post).values():
        title = str(row.get("title") or "").strip().lower()
        if title and row.get("session"):
            out.setdefault(title, str(row["session"]))
    try:
        stamps = [f for f in sorted(Path(hub).glob("live-*.json"))
                  if not f.name.startswith("live-sessions-")]
    except OSError:
        stamps = []
    for f in stamps:
        d = read_json(f, None)
        if not isinstance(d, dict):
            continue
        for s in (d.get("sessions") or []):
            if not isinstance(s, dict):
                continue
            title = str(s.get("title") or "").strip().lower()
            if title and s.get("session"):
                out.setdefault(title, str(s["session"]))
    for ear in read_ears(hub):
        title = str(ear.get("title") or "").strip().lower()
        if title and ear.get("session"):
            out.setdefault(title, str(ear["session"]))
    return out


def named_sessions(hub):
    """{session id: {session, title, vendor, transcript}} for every session the
    HUB's own record names — a claim's row, an i-am stamp's session entry, an ear.
    These are the transcripts the observation is allowed to look at: a session
    that has never run an exocortex tool names none, and is not hunted for."""
    _heavy()
    out = {}

    def add(sid, title, vendor=""):
        sid = str(sid or "")
        if not sid:
            return
        row = out.setdefault(sid, {"session": sid, "title": "", "vendor": "", "transcript": ""})
        row["title"] = row["title"] or str(title or "")
        row["vendor"] = row["vendor"] or str(vendor or "")

    for claim in read_claims(hub):
        add(claim.get("session"), claim.get("title"), claim.get("vendor"))
    for ear in read_ears(hub):
        add(ear.get("session"), ear.get("title"), ear.get("vendor"))
    try:
        stamps = [f for f in sorted(Path(hub).glob("live-*.json"))
                  if not f.name.startswith("live-sessions-")]
    except OSError:
        stamps = []
    for f in stamps:
        d = read_json(f, None)
        if not isinstance(d, dict):
            continue
        for s in (d.get("sessions") or []):
            if isinstance(s, dict):
                add(s.get("session"), s.get("title"), s.get("vendor"))
    return out


def session_map(post):
    _heavy()
    out = {}
    folder = Path(post) / "sessions"
    try:
        files = sorted(folder.glob("*.json"))
    except OSError:
        return out
    for f in files:
        d = read_json(f, None)
        if isinstance(d, dict) and d.get("session"):
            out[str(d["session"])] = d
    return out


def transcript_of(session, vendor, roots, known=""):
    """Where a session's own transcript is, from the stores the pulse already
    reads.  Never guessed from a folder or a clock: a path is returned only when
    a file with that session's own id is there."""
    _heavy()
    if known:
        p = Path(known)
        if p.is_file():
            return str(p)
    claude = Path(roots.get("claude") or (home_dir() / ".claude"))
    if vendor in ("", "claude"):
        try:
            for d in (claude / "projects").iterdir():
                cand = d / ("%s.jsonl" % session)
                if cand.is_file():
                    return str(cand)
        except OSError:
            pass
    codex = Path(roots.get("codex") or (home_dir() / ".codex"))
    if vendor in ("", "codex"):
        try:
            for f in (codex / "sessions").rglob("rollout-*%s.jsonl" % session):
                return str(f)
        except OSError:
            pass
    return ""


def bind_nonces(post, roots, state):
    """A session whose environment gives no id printed ONE line, `  id: pn-…`.
    Bind it by finding that nonce in the transcripts touched since it was made —
    bounded tail reads, both vendors' stores.  Exactly one file binds it; none or
    several leaves it unbound, and AN UNBOUND NONCE NEVER ROUTES."""
    _heavy()
    folder = Path(post) / "nonces"
    try:
        files = sorted(folder.glob("pn-*.json"))
    except OSError:
        return []
    if not files:
        return []
    said = []
    offsets = state.setdefault("nonce_offsets", {})
    for f in files:
        rec = read_json(f, None)
        if not isinstance(rec, dict):
            continue
        made = parse_iso(rec.get("when"))
        nonce = str(rec.get("nonce") or f.stem)
        if made is None:
            continue
        if (now() - made).total_seconds() > 24 * 3600:
            try:
                os.unlink(str(f))                 # a nonce nobody printed is a day old: drop it
            except OSError:
                pass
            continue
        hits = []
        for path, mtime, vendor in transcript_files(roots):
            if mtime < made.timestamp() - 300:
                continue
            key = str(path)
            lo = int(offsets.get(key) or 0)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size < lo:
                lo = 0
            data = read_region(path, max(0, lo - 65536), size)
            _COUNTERS["transcript_files"] += 1
            if nonce.encode("utf-8") in data:
                hits.append((str(path), vendor))
        if len(hits) == 1:
            path, vendor = hits[0]
            session = session_id_of(path, vendor)
            if session and not safe_session_id(session):
                said.append("%s names a session id that is not a plain token — left unbound"
                            % nonce)
            elif session:
                register_session(post, session, vendor=vendor, transcript=path,
                                 title=rec.get("title") or "", arcs=rec.get("arcs") or (),
                                 how="nonce")
                said.append("bound %s to %s (%s)" % (nonce, session, vendor))
                try:
                    os.unlink(str(f))
                except OSError:
                    pass
        elif len(hits) > 1:
            said.append("%s found in %d transcripts — left unbound, it never routes"
                        % (nonce, len(hits)))
    return said


def session_id_of(path, vendor):
    """A transcript's own session id: the file stem for Claude, the rollout's
    first record (`session_meta`) for Codex — its filename carries the id too."""
    _heavy()
    p = Path(path)
    if vendor == "claude":
        return p.stem
    data = read_region(p, 0, min(65536, p.stat().st_size if p.exists() else 0))
    for line in data.decode("utf-8", "replace").splitlines()[:3]:
        try:
            d = json.loads(line)
        except Exception:
            continue
        payload = d.get("payload") if isinstance(d, dict) else None
        if isinstance(payload, dict) and payload.get("session_id"):
            return str(payload["session_id"])
    name = p.stem
    parts = name.split("-")
    return "-".join(parts[-5:]) if len(parts) >= 5 else name


def transcript_files(roots, minutes=None):
    """[(path, mtime, vendor)] for both vendors' stores, newest first.  The same
    two stores the pulse senses; nothing here is read whole."""
    _heavy()
    out = []
    claude = Path(roots.get("claude") or (home_dir() / ".claude"))
    try:
        for d in (claude / "projects").iterdir():
            if not d.is_dir():
                continue
            for f in d.glob("*.jsonl"):
                try:
                    out.append((f, f.stat().st_mtime, "claude"))
                except OSError:
                    pass
    except OSError:
        pass
    codex = Path(roots.get("codex") or (home_dir() / ".codex"))
    try:
        for f in (codex / "sessions").rglob("rollout-*.jsonl"):
            try:
                out.append((f, f.stat().st_mtime, "codex"))
            except OSError:
                pass
    except OSError:
        pass
    if minutes:
        cut = time.time() - minutes * 60
        out = [row for row in out if row[1] >= cut]
    out.sort(key=lambda r: -r[1])
    return out


# --------------------------------------------------------------------------
# ROUTING — who a letter is for
# --------------------------------------------------------------------------

def lane_of(address, mail):
    """The lane part of an address: everything after the machine."""
    parts = mail.addr_key(address).split("/")
    return "/".join(parts[1:])


def machine_of(address, mail):
    return mail.addr_key(address).split("/")[0]


def claim_answers(arc, lane, mail):
    """Does a claim's ARC answer to this LANE?  Exact first, else a unique
    `/`-suffix: `NORTH/Builds` is answered by the arc `Hub/Builds`, and
    `ALPHA/Proj-Lane` by `Proj/Lane`.  Returns "exact", "suffix" or ""."""
    a = mail.addr_key(arc)
    if not a or not lane:
        return ""
    if a == lane:
        return "exact"
    if a.endswith("/" + lane):
        return "suffix"
    return ""


# --------------------------------------------------------------------------
# THE FLEET'S LANE TOKENS — read from the record, never typed in
# --------------------------------------------------------------------------

_LANES = {}                     # computed ONCE per pass, and never raises


def projects_roots(record=None, home=None):
    """Every projects root machine.json names, as a list — one string or many,
    because a fleet may keep its projects in more than one place and a record
    that names none simply contributes nothing."""
    _heavy()
    d = record if record is not None else machine_record(home)
    root = (d.get("roots") or {}).get("projects")
    if not root:
        return []
    if isinstance(root, (list, tuple)):
        return [Path(str(r)) for r in root if str(r).strip()]
    return [Path(str(root))]


def opener_lane(path, cap=4096):
    """The `lane:` header of an OPENER file — READ ONLY ABOVE THE FIRST `---`
    (the opener file's own shape), and only the first few KB of it, because a
    header is a header and the body is somebody else's business."""
    try:
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            head = fh.read(cap)
    except Exception:
        return ""
    for raw in head.splitlines():
        line = raw.strip()
        if line.startswith("---"):
            break
        if line.lower().startswith("lane:"):
            return line.split(":", 1)[1].strip()
    return ""


ACT_TITLE = None                # compiled on first use: `ACT — <Proj>/<Lane>: …`


def title_lane(title):
    """The `<Proj>/<Lane>` token inside a session title, or "" — a title with no
    lane in it (`ACT — Exocortex: …`) contributes nothing at all."""
    global ACT_TITLE
    _heavy()
    if ACT_TITLE is None:
        ACT_TITLE = re.compile(r"^\s*ACT\s*[—–-]\s*([^:]+?)\s*:")
    m = ACT_TITLE.match(str(title or ""))
    if not m:
        return ""
    token = m.group(1).strip()
    return token if "/" in token else ""


def add_lane(out, spelling, mail):
    """One lane token, under mail.py's own key so `Proj-Lane` and `Proj/Lane`
    are one lane.  The SPELLING kept is the smallest one the record carries, so
    both machines say the same sentence about the same lane."""
    text = str(spelling or "").strip()
    if not text:
        return
    key = mail.addr_key(text)
    if not key:
        return
    have = out.get(key)
    if have is None or text < have:
        out[key] = text


def fleet_lanes(hub, claims=None, home=None, record=None, cache=True):
    """EVERY LANE TOKEN THE FLEET CARRIES, {key: the record's own spelling}.

    Why: two letters addressed `NORTH/Release` for
    Hub/Release could be delivered to the session holding Another/Release,
    because a claim was the only lane the postman could see.  A short address is
    only unambiguous against the WHOLE fleet, so the fleet is read from three
    places, all of them record:

      1. every arc in claims.json — the lanes somebody holds right now;
      2. the `lane:` header of every OPENER*.md in the hub folder and in each
         project folder ONE LEVEL under each projects root machine.json names —
         the lanes that exist whether or not anyone is sitting in them;
      3. the `<Proj>/<Lane>` of every `ACT — …` title in the `live-*.json`
         stamps — the lanes a session is in without an opener of its own.

    Computed once per pass and cached; a missing file, an unreadable folder or a
    record with no projects root contributes NOTHING and never raises."""
    _heavy()
    roots = projects_roots(record, home)
    ck = (str(hub), tuple(str(r) for r in roots))
    if cache and ck in _LANES:
        return _LANES[ck]
    out = {}
    try:
        mail = mail_module(hub)
    except Exception:
        return {}
    try:
        rows = claims if claims is not None else read_claims(hub)
        for claim in rows or []:
            try:
                add_lane(out, (claim or {}).get("arc"), mail)
            except Exception:
                pass
    except Exception:
        pass
    folders = [Path(hub)]
    for root in roots:
        try:
            entries = sorted(Path(root).iterdir())
        except Exception:
            continue
        for entry in entries:                       # ONE LEVEL, the dispatch's own bound
            try:
                if entry.name.startswith(".") or not entry.is_dir():
                    continue
            except OSError:
                continue
            folders.append(entry)
    for folder in folders:
        try:
            files = sorted(folder.glob("OPENER*.md"))
        except Exception:
            continue
        for f in files:
            try:
                add_lane(out, opener_lane(f), mail)
            except Exception:
                pass
    try:
        stamps = sorted(Path(hub).glob("live-*.json"))
    except Exception:
        stamps = []
    for f in stamps:
        if f.name.startswith("live-sessions-"):     # the pulse's sensed list is not a stamp
            continue
        d = read_json(f, None)
        if not isinstance(d, dict):
            continue
        titles = [d.get("title")]
        for s in (d.get("sessions") or []):
            if isinstance(s, dict):
                titles.append(s.get("title"))
        for t in titles:
            try:
                add_lane(out, title_lane(t), mail)
            except Exception:
                pass
    if cache:
        _LANES[ck] = out
    return out


def lane_hits(lane, lanes):
    """Every fleet lane token a short address could mean.  EXACT FIRST, exactly as
    route() has always read a claim: a fleet that carries the token whole is
    answered by that token and by nothing else; otherwise every `<Proj>/<lane>`
    that ends with it is a candidate."""
    if not lane or not lanes:
        return {}
    exact = dict((k, v) for k, v in lanes.items() if k == lane)
    if exact:
        return exact
    return dict((k, v) for k, v in lanes.items() if k.endswith("/" + lane))


def join_words(items, word):
    """`a and b` · `a, b and c` — a sentence a human reads, not a list."""
    rows = [str(i) for i in items]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    return "%s %s %s" % (", ".join(rows[:-1]), word, rows[-1])


def ambiguous_why(address, machine, spellings):
    """The sentence a sender reads instead of a delivery: the full tokens, and the
    address to use for each — so the fix is in the sentence and nowhere else."""
    names = list(spellings)
    addrs = ["%s/%s" % (str(machine).upper(), n.replace("/", "-")) for n in names]
    return "%s fits %s — send it again as %s" % (
        address, join_words(names, "and"), join_words(addrs, "or"))


def route(line, mail, claims, ears, fleet, at=None, by_title=None, lanes=None):
    """THE ONE ROUTING FUNCTION.  Every pass on every
    machine computes the same answer from the same record, and AMBIGUOUS never
    delivers.

    1. BY CLAIM, fleet-wide.  The `hub` lane is per machine — the address's own
       machine decides — so two hubs never answer for one another.  Exactly one
       answering claim names the HOLDER, wherever it lives.
    2. BY EAR, only with no answering claim: the freshest ear for that exact
       address, fresh being younger than twice its own poll (the tree's own rule).
    3. NEITHER: the letter waits on the addressed machine, with its reason.

    `lanes` is the FLEET'S LANE TOKENS, computed once per pass by
    fleet_lanes() and handed in — an INPUT to this function, never a second
    matcher (R3).  A short address whose token fits two lanes across projects is
    ambiguous BEFORE any claim is looked at, because the lane that happens to
    hold a claim this minute is not the lane the sender meant.  With no lanes
    handed in — an older caller, a fleet with no openers and no stamps — routing
    is exactly what it was.
    """
    at = at or now()
    address = mail.address_of(line)
    lane = lane_of(address, mail)
    mch = machine_of(address, mail)
    if is_owner_address(mch):
        return {"state": "for_owner", "holder": None,
                "why": "to: OWNER — a letter for the human, not for a session"}
    if mch not in fleet:
        return {"state": "no_machine", "holder": None,
                "why": "no machine named %s is in the fleet" % mch.upper()}
    if lane == BROADCAST_LANE:
        # EVERY LIVE LANE ON THAT MACHINE.  No claim is asked: the
        # addressed machine's pass fans it out (fan_out), and no other pass acts.
        return {"state": "broadcast", "holder": None,
                "why": "a broadcast to every live lane on the %s" % mch.upper()}
    tiers = {"exact": [], "suffix": []}
    for claim in claims:
        if lane == "hub" and str(claim.get("machine") or "").lower() != mch:
            continue                                # the hub arc is per machine
        tier = claim_answers(claim.get("arc"), lane, mail)
        if tier:
            tiers[tier].append(claim)
    answering = tiers["exact"] or tiers["suffix"]
    if len(answering) > 1:
        names = ", ".join(sorted(str(c.get("arc") or "?") for c in answering))
        return {"state": "ambiguous", "holder": None,
                "why": "two lanes answer to that name (%s) — send it again with the "
                       "project in the address" % names}
    # A SHORT ADDRESS THAT FITS TWO LANES ACROSS THE FLEET IS NOBODY'S.
    # It is asked AFTER the claims have been counted,
    # so two answering claims keep their own older sentence above, and BEFORE a
    # single claim is turned into a holder — because the one lane that happens to
    # be claimed this minute is not evidence that it is the lane the sender
    # meant.  `hub` is per machine and stays untouched; an address that already
    # carries its project (`ALPHA/Proj-Lane`, lane part `proj/lane`) is not short.
    if lanes and lane and lane != "hub" and "/" not in lane:
        hits = lane_hits(lane, lanes)
        if len(hits) > 1:
            return {"state": "ambiguous", "holder": None,
                    "why": ambiguous_why(address, mch, [hits[k] for k in sorted(hits)])}
    by_title = by_title or {}
    if len(answering) == 1:
        claim = answering[0]
        holder = {"machine": str(claim.get("machine") or "").lower(),
                  "mind": str(claim.get("mind") or "?").upper(),
                  "title": str(claim.get("title") or ""),
                  "session": str(claim.get("session") or ""), "by": "claim"}
        if not holder["session"]:              # the claim's own field first, else a
            holder["session"] = by_title.get(  # stamp or ear carrying that title AND a session
                holder["title"].strip().lower(), "")
        return {"state": "held", "holder": holder, "why": ""}
    ear = freshest_ear(ears, address, mail, at)
    if ear:
        holder = {"machine": str(ear.get("machine") or mch).lower(),
                  "mind": str(ear.get("mind") or "?").upper(),
                  "title": str(ear.get("title") or ""),
                  "session": str(ear.get("session") or ""), "by": "ear",
                  "how": str(ear.get("how") or "")}
        if not holder["session"]:
            holder["session"] = by_title.get(holder["title"].strip().lower(), "")
        return {"state": "held", "holder": holder, "why": ""}
    spelt = str(address).split("/", 1)[1] if "/" in str(address) else (lane or "that lane")
    return {"state": "nobody", "holder": None,       # the sender's own spelling of the lane
            "why": "nobody on the %s holds %s" % (mch.upper(), spelt)}


# --------------------------------------------------------------------------
# THE BROADCAST — one letter, every live lane on one machine
# --------------------------------------------------------------------------

BROADCAST_LANE = "all"          # mail.py's own word for it (mail.BROADCAST_LANE)
BROADCAST_LIVE_HOURS = 12       # the stamps' own rule: under twelve hours old is live


def broadcast_recipients(hub, mch, claims, ears, by_title, roots, at=None, exclude=()):
    """EVERY LIVE LANE on machine `mch`, one holder per SESSION, from the record
    and nothing else: the claims held there, the fresh ears there, and the i-am
    stamps' own session entries there.  A session is LIVE when its own
    transcript on this machine was written in the last twelve hours — or, where
    no transcript can be found, when its stamp or ear says so inside the same
    twelve hours.  A holder known by title only, with no session id, cannot be
    queued and is left out; the sender's own session never gets its own letter."""
    _heavy()
    at = at or now()
    cands = {}

    def add(sid, title, mind, by, lane, vendor="", when=None):
        sid = str(sid or "").strip()
        if not sid or not safe_session_id(sid) or sid in exclude:
            return
        row = cands.setdefault(sid, {"machine": mch, "mind": str(mind or "?").upper(),
                                     "title": str(title or ""), "session": sid, "by": by,
                                     "lane": str(lane or ""), "vendor": str(vendor or ""),
                                     "when": None})
        if not row["lane"] and lane:
            row["lane"] = str(lane)
        if not row["title"] and title:
            row["title"] = str(title)
        if when is not None and (row["when"] is None or when > row["when"]):
            row["when"] = when

    for claim in claims or []:
        if str(claim.get("machine") or "").lower() != mch:
            continue
        sid = claim.get("session") or (by_title or {}).get(
            str(claim.get("title") or "").strip().lower(), "")
        add(sid, claim.get("title"), claim.get("mind"), "claim", claim.get("arc"),
            claim.get("vendor"))
    for ear in ears or []:
        if str(ear.get("machine") or "").lower() != mch:
            continue
        when = parse_iso(ear.get("when"))
        every = int(ear.get("every") or 150)
        if when is None or (at - when).total_seconds() > max(2 * every, 60):
            continue                                # an ear nobody holds is not live
        add(ear.get("session"), ear.get("title"), ear.get("mind"), "ear",
            ear.get("lane"), ear.get("vendor"), when)
    try:
        stamps = [f for f in sorted(Path(hub).glob("live-%s-*.json" % mch))
                  if not f.name.startswith("live-sessions-")]
    except OSError:
        stamps = []
    for f in stamps:
        d = read_json(f, None)
        if not isinstance(d, dict):
            continue
        for s in (d.get("sessions") or []):
            if isinstance(s, dict):
                add(s.get("session"), s.get("title"), d.get("mind"), "stamp",
                    title_lane(s.get("title")), s.get("vendor"), parse_iso(s.get("when")))
    out = []
    cut = BROADCAST_LIVE_HOURS * 3600.0
    for sid in sorted(cands):
        row = cands[sid]
        mtime = transcript_mtime(sid, roots) if roots is not None else None
        if mtime is not None:
            live = (at.timestamp() - mtime) <= cut
        else:
            live = row["when"] is not None and (at - row["when"]).total_seconds() <= cut
        if live:
            row.pop("when", None)
            out.append(row)
    return out


def broadcast_sender(post, state, token):
    """The session that SENT this letter, when this machine sent it — from the
    pass's own record, else straight from mail.py's outbox file, because the
    first pass after a send routes before it folds the outbox in."""
    row = (state.get("sent") or {}).get(token) or \
        read_json(Path(post) / "outbox" / ("%s.json" % token), None) or {}
    return str(((row.get("from") or {}) if isinstance(row, dict) else {}).get("session") or "")


def window_login(hub, roots, sid, cache=None):
    """The login a live window runs under, lower-cased — '' when it is not KNOWN.
    usage.py's SCAN road (session_login, fallback off) with the pass's own window variables
    taken out (the pass is nobody's window), so a scanning window's login never stands in for
    another's; and only the `transcript` road counts — the window's transcript names its owner.
    With no transcript usage.py falls back to the app's login, a guess about THIS window, and
    an unknown is never a reason to withhold. One read per window per pass (`cache`)."""
    sid = str(sid or "").strip()
    if cache is not None and sid in cache:
        return cache[sid]
    login = ""
    u = sibling_module("usage.py", "pm_usage") if (sid and roots is not None) else None
    if u is not None:
        env = dict(os.environ)
        for k in ("CLAUDE_CODE_SESSION_ID", HOST_ENV):
            env.pop(k, None)
        try:
            who, how = u.session_login(roots, str(hub), session=sid, fallback=False, env=env)[:2]
            if who and str(how or "").startswith("transcript") \
                    and not u.same_login(who, u.UNKNOWN_LOGIN):
                login = str(who).strip().lower()
        except Exception:
            login = ""
    if cache is not None:
        cache[sid] = login
    return login


def logins_same(a, b):
    """usage.py's own comparison of two logins (loaded only when an alarm's fan-out asks)."""
    u = sibling_module("usage.py", "pm_usage")
    f = getattr(u, "same_login", None) if u is not None else None
    if f is not None:
        return bool(f(a, b))
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def alarm_about(mail, line):
    """The login an ALARM line (a USAGE PAUSE / WARN broadcast) is about, lower-cased — ''
    for any other line, and for an alarm that names none (then every live lane hears it)."""
    try:
        if mail.usage_kind(line) != "alarm":
            return ""
        return str(mail.alarm_login(line) or "").strip().lower()
    except Exception:                         # an older mail.py without the usage-alarm readers
        return ""


def fan_out(post, state, known, token, entry, mail, holders, name, at, dry=False, began=None,
            skips=None, login_of=None, same_login=None):
    """Give each live lane its own copy of a broadcast and queue it there.  A copy
    is an ordinary letter to the rest of this tool — held, queued, observed,
    expired — with a `parent` so nobody routes it again.  Returns how many were
    queued this pass.

    BORN AFTER, NO COPY : a lane whose session began after the broadcast was
    first seen was not live when it was sent, and is never given a copy — `began` says
    when a session began (None when nothing on disk says, and then it is not withheld).

    ANOTHER LOGIN, NO COPY: an ALARM that names its meter's login is a question
    about that meter alone. A lane whose window login is KNOWN and DIFFERENT gets no copy —
    its session id kept under `other_login`, counted as `other-login`; a lane whose login
    is unknown gets its copy (never withheld on a guess). `login_of(sid)` says a window's
    login ('' unknown) and `same_login` compares two; without `login_of` nothing is
    withheld. Any other broadcast ignores logins."""
    queued = 0
    children = entry.setdefault("children", [])
    first = parse_iso(entry.get("first_seen"))
    about = alarm_about(mail, entry.get("line") or "") if login_of is not None else ""
    same = same_login or (lambda a, b: str(a or "").strip().lower() == str(b or "").strip().lower())
    for holder in holders:
        sid = holder["session"]
        ct = mail.child_token(token, sid)
        child = known.get(ct)
        if child is None and began is not None and first is not None:
            start = began(sid)
            if start is not None and start > first:
                later = entry.setdefault("born_after", [])
                if sid not in later:
                    later.append(sid)
                    if skips is not None:
                        skips["born-after"] += 1
                continue
        if child is None and about:
            if sid in (entry.get("other_login") or []):
                continue                          # judged once: a window keeps its login
            theirs = login_of(sid)
            if theirs and not same(theirs, about):
                others = entry.setdefault("other_login", [])
                others.append(sid)
                if skips is not None:
                    skips["other-login"] += 1
                continue
        if child is None:
            child = known[ct] = {"to": entry.get("to"), "date": entry.get("date") or "",
                                 "line": entry.get("line") or "", "fyi": bool(entry.get("fyi")),
                                 "first_seen": entry.get("first_seen") or iso(at),
                                 "state": "waiting", "parent": token, "state_kind": "held",
                                 "holder": dict(holder), "why": ""}
        if ct not in children:
            children.append(ct)
        if child.get("state") != "waiting" or already_carried(state, ct, sid):
            continue
        if holder.get("machine") != name:
            continue
        quiet = bool(getattr(mail, "is_quiet", lambda _l: False)(entry.get("line") or ""))
        n = 0 if dry else queue_pending(post, sid, [{
            "token": ct, "kind": "letter", "line": entry.get("line") or "",
            "to": entry.get("to"), "fyi": bool(entry.get("fyi")), "queued": iso(at),
            "broadcast": token, "quiet": quiet}])
        child.setdefault("queued", iso(at))
        if quiet:
            child["quiet"] = True                  # the next turn start carries it
        queued += n
    return queued


def broadcast_rollup(known, mch_of):
    """A broadcast is DELIVERED when every lane's copy is, and until then its why
    says how many have read it — the sentence its sender hears at five minutes."""
    for token, entry in known.items():
        if entry.get("state_kind") != "broadcast" or entry.get("state") != "waiting":
            continue
        kids = [known[c] for c in (entry.get("children") or []) if c in known]
        where = str(mch_of(entry.get("to") or "")).upper()
        if not kids:
            later = len(entry.get("born_after") or [])
            other = len(entry.get("other_login") or [])
            elsewhere = ("%d on another login get%s no copy" % (other, "s" if other == 1 else "")
                         if other else "")
            entry["why"] = (("no lane that was live when it was sent is live on the %s — %d "
                             "born after it get%s no copy" % (where, later, "s" if later == 1
                                                               else ""))
                            + (" · " + elsewhere if elsewhere else "")
                            if later else
                            ("no live lane on the %s runs under the login it is about — %s"
                             % (where, elsewhere))
                            if other else
                            ("no live lane on the %s has a session this postman can "
                             "queue to — it waits for one" % where))
            continue
        done = [k for k in kids if k.get("state") in ("delivered", "expired")]
        read = [k for k in kids if k.get("state") == "delivered"]
        if len(done) == len(kids) and read:
            last = max(((k.get("delivered") or {}).get("when") or "") for k in read)
            entry["state"] = "delivered"
            entry["delivered"] = {"when": last, "road": "broadcast",
                                  "evidence": "every lane's copy", "session": "",
                                  "title": "%d lane(s)" % len(read)}
            entry["why"] = "read by all %d lane(s) on the %s" % (len(read), where)
            continue
        left = [str((k.get("holder") or {}).get("title") or
                    (k.get("holder") or {}).get("session") or "?")
                for k in kids if k.get("state") == "waiting"]
        entry["why"] = "read by %d of %d lane(s) on the %s — waiting: %s" % (
            len(read), len(kids), where, join_words(left[:3], "and")
            + (" and %d more" % (len(left) - 3) if len(left) > 3 else ""))


def freshest_ear(ears, address, mail, at=None):
    """The freshest ear for THAT EXACT ADDRESS, or None.  Fresh = younger than
    twice its own poll interval: one missed beat is a hiccup, two is a mailbox
    nobody is holding (the tree's own rule)."""
    at = at or now()
    want = mail.addr_key(address)
    best, best_when = None, None
    for ear in ears:
        if mail.addr_key(ear.get("to") or "") != want:
            continue
        when = parse_iso(ear.get("when"))
        if when is None:
            continue
        every = int(ear.get("every") or 150)
        if (at - when).total_seconds() > max(2 * every, 60):
            continue
        if best_when is None or when > best_when:
            best, best_when = ear, when
    return best


def read_ears(hub):
    _heavy()
    out = []
    try:
        files = sorted(Path(hub).glob("ear-*.json"))
    except OSError:
        return out
    for f in files:
        d = read_json(f, None)
        if isinstance(d, dict) and d.get("to"):
            out.append(d)
    return out


def read_claims(hub):
    _heavy()
    d = read_json(Path(hub) / "claims.json", [])
    if not isinstance(d, list):
        return []
    return [c for c in d if isinstance(c, dict) and c.get("arc")]


def why_for(entry, holder, ears, mail, posts, at=None, sessions=None, cfg=None):
    """THE WHY CLAUSES, the whole list of them — the sentence a sender
    reads instead of silence.  Never a guess: every clause names what the record
    actually says."""
    at = at or now()
    state = entry.get("state_kind")
    if state in ("ambiguous", "no_machine", "nobody") or state_is_for_owner(state):
        return entry.get("why") or ""
    if not holder:
        return entry.get("why") or ""
    address = entry.get("to") or ""
    mch = machine_of(address, mail)
    hm = str(holder.get("machine") or "").lower()
    stale = stale_postman(posts, hm, at)        # the blocker is said before the address
    if stale:
        return stale
    if hm and hm != mch:                        # the sender's own spelling of the lane
        spelt = str(address).split("/", 1)[1] if "/" in str(address) else lane_of(address, mail)
        return "%s is held on the %s, not the %s — queued there" % (
            spelt, hm.upper(), mch.upper())
    if not holder.get("session"):
        return ("holder known by title only — it has not run an exocortex tool since "
                "the postman was installed")
    row = (sessions or {}).get(str(holder["session"])) or {}
    if row.get("vendor") == "codex":
        try:
            mtime = os.stat(row.get("transcript") or "").st_mtime
        except OSError:
            return "queued — its thread's transcript is not on disk"
        age = at.timestamp() - mtime
        busy = float((cfg or DEFAULTS).get("attend_busy_seconds") or 60)
        if age <= busy:
            return "queued — busy; rides the end of this turn"
        if age > 24 * 60 * 60:
            return "queued — its thread has been quiet since %s" % (
                datetime.fromtimestamp(mtime, at.tzinfo).strftime("%Y-%m-%d %H:%M"))
        return "queued — idle thread; shows at the end of its next turn or at its next resume"
    ear = freshest_ear(ears, address, mail, at)
    mind = holder.get("mind") or "?"
    title = holder.get("title") or ""
    if ear and str(ear.get("how") or "") == "read":
        return "%s «%s» holds it and reads its mail at its next turn" % (mind, title)
    if not ear:
        return ("%s «%s» holds it and is idle with no ear — it will read at its next turn"
                % (mind, title))
    return "%s «%s» holds it and reads its mail at its next turn" % (mind, title)


def stale_postman(posts, machine, at=None):
    """The other machine's pass is the carrier there.  When its own pulse copy
    says it has not run, say so rather than blaming the holder."""
    at = at or now()
    beat = (posts.get(machine) or {}).get("_beat")
    if not beat:
        return ""
    when = parse_iso(beat.get("last_pass"))
    if when is None:
        return ""
    if (at - when).total_seconds() > 15 * 60:
        return ("the %s's postman has not run since %s — that machine may be asleep"
                % (machine.upper(), when.strftime("%H:%M")))
    return ""


# --------------------------------------------------------------------------
# the config the user may edit
# --------------------------------------------------------------------------

def config(hub):
    """The user's own settings, with every default filled.

    THE `owner_*` SETTINGS WERE ONCE NAMED AFTER THE PERSON, so a config file
    written before that changed is read under its old spelling and its value is
    kept. The old name comes from the registry's own short word — this file
    spells nobody's name — and a registry that names nobody has no old name at
    all, which is right: a stranger has no old config."""
    _heavy()
    cfg = dict(DEFAULTS)
    d = read_json(Path(hub) / "post-config.json", None)
    if isinstance(d, dict):
        older = legacy_owner_keys()
        for k in DEFAULTS:
            if k in d:
                cfg[k] = d[k]
                continue
            if not k.startswith("owner_"):
                continue
            for word in older:
                was = "%s_%s" % (word, k[len("owner_"):])
                if was in d:
                    cfg[k] = d[was]
                    break
    return cfg


# --------------------------------------------------------------------------
# post-<machine>.json — the one file a machine publishes
# --------------------------------------------------------------------------

def post_file(hub, machine):
    _heavy()
    return Path(hub) / ("post-%s.json" % machine)


def read_posts(hub, live_sessions=True):
    """Every machine's post file, keyed by machine, plus that machine's postman
    heartbeat as the pulse copied it into live-sessions-<machine>.json."""
    _heavy()
    out = {}
    try:
        files = sorted(Path(hub).glob("post-*.json"))
    except OSError:
        files = []
    for f in files:
        if f.name == "post-config.json":
            continue
        d = read_json(f, None)
        if isinstance(d, dict) and d.get("machine"):
            out[str(d["machine"]).lower()] = d
    if live_sessions:
        try:
            for f in sorted(Path(hub).glob("live-sessions-*.json")):
                d = read_json(f, None)
                if not isinstance(d, dict):
                    continue
                mch = str(d.get("machine") or "").lower()
                if mch and isinstance(d.get("postman"), dict):
                    out.setdefault(mch, {"machine": mch})["_beat"] = d["postman"]
        except OSError:
            pass
    return out


def publish(hub, machine, body, dry=False):
    """Write post-<machine>.json ONLY when its content changed, and never let a
    moving timestamp live in it: `changed` moves when the content does, and not
    otherwise, so a quiet hour makes zero brain commits."""
    path = post_file(hub, machine)
    old = read_json(path, None)
    strip = lambda d: {k: v for k, v in (d or {}).items() if k != "changed"}
    if isinstance(old, dict) and strip(old) == strip(body):
        return False
    body = dict(body, changed=iso(now()))
    if not dry:
        write_json_atomic(path, body, mode=BRAIN_FILE)   # the brain carries it, as it does the stamps
    return True


# --------------------------------------------------------------------------
# THE PASS
# --------------------------------------------------------------------------

def inbox_letters(hub, state, mail):
    """Read INBOX.md INCREMENTALLY: remember the byte offset and a fingerprint of
    the first 4 KB, and parse only what was appended.  A file that shrank or whose
    head changed — a merge rewrote it — is re-parsed whole, which costs nothing
    but time: a token already delivered is never delivered again."""
    _heavy()
    path = Path(hub) / "INBOX.md"
    mark = state.setdefault("inbox", {})
    try:
        size = path.stat().st_size
    except OSError:
        return [], False
    with open(str(path), "rb") as fh:
        head = fh.read(4096)
    _COUNTERS["inbox_bytes"] += len(head)
    fingerprint = hashlib.sha256(head).hexdigest()[:16]
    lo = int(mark.get("offset") or 0)
    full = (lo == 0 or size < lo or fingerprint != (mark.get("head") or fingerprint))
    # THE SEAM : `--mark` rewrites a line IN PLACE, under the offset, adding
    # its ` · delivered: …` tail — the head and the growing size cannot see that, and the
    # offset then sits mid-line. The SEAM_BYTES just before the offset are fingerprinted
    # at every read; a rewrite anywhere above them shifts them, and the file is re-parsed
    # whole (the stamps are read). A mark written before this build has no seam: one full
    # read, once, so letters stamped while it ran are read too.
    if not full:
        seam_lo = max(0, lo - SEAM_BYTES)
        with open(str(path), "rb") as fh:
            fh.seek(seam_lo)
            seam = fh.read(lo - seam_lo)
        _COUNTERS["inbox_bytes"] += len(seam)
        if hashlib.sha256(seam).hexdigest()[:16] != mark.get("seam"):
            full = True
    if full:
        lo = 0
    data = read_region(path, lo, size, cap=64 * 1024 * 1024, bucket="inbox_bytes")
    text = data.decode("utf-8", "replace")
    # The offset always sits just past a newline (see `consumed` below), so the
    # region starts on a line boundary and NOTHING is skipped at its head — an
    # earlier cut of this reader dropped the first appended line every pass.
    # The TAIL is where a half-written line can be, and `keep` leaves it for the
    # next pass rather than parsing half a letter.
    keep = text.rfind("\n")
    consumed = lo + len(text[:keep + 1].encode("utf-8")) if keep >= 0 else lo
    lines = [l for l in text[:keep + 1].splitlines() if l.startswith("- ")]
    mark["offset"], mark["head"], mark["size"] = consumed, fingerprint, size
    with open(str(path), "rb") as fh:            # the bytes the next read will check
        start = max(0, consumed - SEAM_BYTES)
        fh.seek(start)
        behind = fh.read(consumed - start)
    mark["seam"] = hashlib.sha256(behind).hexdigest()[:16]
    return [l for l in lines if mail.address_of(l)], full


def cmd_pass(hub, post, opts):
    """One pass.  No model, no tokens: reading a file and routing what it says is
    mechanical work, and the machine does it every sixty seconds."""
    _heavy()
    named = machine_record(opts.get("home"))
    if not str(named.get("name") or "").strip():
        # A pass routes `to: <MACHINE>/<lane>` mail for THIS machine, and a machine
        # no record names has no name to take it under: it would publish a post
        # file for nobody. It says so in one line and passes nothing.
        why = ("the machine record names no machine" if named else
               "no machine record was found for this machine")
        return 0, ["postman: %s, so there is no name to take mail under — nothing was "
                   "passed; run the installer, then pass again." % why]
    mail = mail_module(hub)
    cfg = config(hub)
    said = []
    post = mkdirs(post)                       # POST DIR is this account's alone
    said.extend(loose_post_dir(post))         # …and if it already was not, say so
    lock = post / "pass.lock"
    if not opts.get("dry") and not take_lock(lock):
        return 0, []                              # another pass is running: exit 0, silent
    try:
        state = read_json(post / "state.json", None) or {"version": VERSION}
        record = machine_record(opts.get("home"))
        name = machine_name(record=record)
        roots = record.get("roots") or {}
        fleet = set(mail.fleet(hub))
        fleet.add(name)

        # 2 — the brain, when it is due
        pulled = pull_if_due(hub, state, opts, cfg)
        if pulled:
            said.append(pulled)

        # 3 — the mail, incrementally
        lines, full = inbox_letters(hub, state, mail)
        mark_word = getattr(mail, "DELIVERED_MARK", " · delivered:")
        resolved_word = getattr(mail, "RESOLVED_MARK", RESOLVED_WORD)
        kind_of = getattr(mail, "usage_kind", None)
        letters, stamped, resolved = {}, {}, {}
        useq = state.setdefault("usage_seq", {})     #  the INBOX order of usage lines
        for line in lines:
            t = mail.token(line)
            letters.setdefault(t, line)
            if mark_word in line:
                stamped.setdefault(t, line)            #  the INBOX stamp is delivery
            if resolved_word in line:
                resolved.setdefault(t, line)           # a push that landed closed it
            if kind_of is not None and kind_of(line) and t not in useq:
                state["usage_n"] = int(state.get("usage_n") or 0) + 1
                useq[t] = state["usage_n"]

        # 4 — bootstrap, once per machine
        legacy = read_json(post / "legacy.json", None)
        if legacy is None and not post_file(hub, name).is_file():
            legacy = {"count": len(letters), "before": iso(now()),
                      "tokens": sorted(letters.keys())}
            if not opts.get("dry"):
                write_json_atomic(post / "legacy.json", legacy)
            said.append("BOOTSTRAP · %d earlier letters left to --read · the postman "
                        "carries what arrives from %s" % (legacy["count"], legacy["before"]))
        legacy_tokens = set((legacy or {}).get("tokens") or [])

        # 5 — route, and queue for a holder that lives here
        state.setdefault("letters", {})
        known = state["letters"]
        fold_receipts(post, state)              # before routing, never after it
        claims, ears = read_claims(hub), read_ears(hub)
        lanes = fleet_lanes(hub, claims)        # once per pass, never raises
        posts = read_posts(hub)
        sessions = session_map(post)
        if not opts.get("dry"):
            said.extend(bind_nonces(post, roots, state))
            sessions = session_map(post)
        by_title = identities(hub, post)
        at = now()
        queued = 0
        skips = dict((w, 0) for w in SKIP_WORDS)    #  what did not ride, and why
        to_drop, delivered_elsewhere = set(), set()
        for token, line in letters.items():
            if token in legacy_tokens or token in known:
                continue
            clean = untail(line, (mark_word, resolved_word))
            date = mail.fields(clean)[0] if mail.fields(clean) else ""
            entry = {"to": mail.address_of(clean), "date": date, "line": clean,
                     "fyi": mail.is_fyi(clean), "first_seen": iso(first_seen_for(date, at)),  # M-H
                     "state": "waiting"}
            if past_horizon(entry, cfg, at) and (token in stamped or token in resolved
                                                 or expired(entry, cfg, at)):
                # HISTORY, MET AGAIN by a full re-parse (a merge, a --mark): a letter whose own
                # date is past the prune horizon is never a letter to this pass — not routed,
                # and not written into the post file only to be pruned the same minute.
                skips["delivered by stamp" if token in stamped else
                      "resolved by stamp" if token in resolved else "expired"] += 1
                continue
            rec = (state.get("receipts") or {}).get(token)
            if rec and token not in stamped and (rec.get("kind") or "letter") == "letter":
                # A TOKEN DELIVERED ONCE IS NEVER DELIVERED AGAIN: a receipt for a token this
                # pass has no entry for means the entry was pruned and a re-parse met its
                # line again — it was handed to a window already, and is not news.
                entry["state"] = "delivered"
                entry["delivered"] = {"when": rec.get("when") or iso(at),
                                      "road": rec.get("road") or "hook",
                                      "evidence": "receipt", "session": rec.get("session") or "",
                                      "title": ""}
                entry["why"] = "handed before; met again by a re-parse"
                skips["already handed"] += 1
            known[token] = entry
        # M-A — A LETTER STAMPED IN INBOX IS DELIVERED: never queued, out of every pending
        # file, and a broadcast's copies with it (a stamp on a broadcast is a hand's).
        for token, line in stamped.items():
            entry = known.get(token)
            if entry is None or entry.get("state") in ("delivered", "expired"):
                continue
            entry["state"] = "delivered"
            entry["delivered"] = stamp_record(line, mark_word, at)
            entry["why"] = "stamped delivered in INBOX.md"
            skips["delivered by stamp"] += 1
            delivered_elsewhere.add(token)
            for ct in entry.get("children") or []:
                kid = known.get(ct)
                if kid is not None and kid.get("state") == "waiting":
                    kid["state"] = "delivered"
                    kid["delivered"] = dict(entry["delivered"])
                    delivered_elsewhere.add(ct)
        # A LETTER A PUSH THAT LANDED CLOSED is expired: never queued, out of
        # every pending file (to_drop), and a send order that held only such letters is
        # taken back by attend()'s own spent road below (its letters are all finished).
        for token, line in resolved.items():
            entry = known.get(token)
            if entry is None or entry.get("state") in ("delivered", "expired"):
                continue
            entry["state"] = "expired"
            entry["why"] = resolved_why(line, resolved_word)
            entry["resolved"] = True
            skips["resolved by stamp"] += 1
            to_drop.add(token)
            for ct in entry.get("children") or []:
                kid = known.get(ct)
                if kid is not None and kid.get("state") == "waiting":
                    kid["state"], kid["why"] = "expired", entry["why"]
                    to_drop.add(ct)
        # M-H — every letter still waiting is measured from its own date at the latest
        for entry in known.values():
            if entry.get("state") == "waiting":
                clamp_first_seen(entry, at)
        # M-D — OLD ALARMS DO NOT RING : superseded or past their reset, an alarm
        # is never queued, pushed or carried; its lanes' copies go with it.
        if hasattr(mail, "alarm_verdicts"):
            for t in [t for t in useq if t not in known]:
                useq.pop(t, None)
            order = sorted((t for t in useq),
                           key=lambda t: (known[t].get("date") or "", int(useq[t])))
            rows = [(t, known[t].get("line") or "", parse_iso(known[t].get("first_seen")))
                    for t in order]
            try:
                # the pass is nobody's window — the app's own login, never a
                # window's variables, and the meter files of this hub
                verdicts = mail.alarm_verdicts(
                    rows, at, hub=str(hub), roots=roots,
                    login=mail.live_login(str(hub), roots, window=False)) \
                    if hasattr(mail, "live_login") else mail.alarm_verdicts(rows, at)
            except TypeError:                        # an older mail.py whose readers take no hub or login
                verdicts = mail.alarm_verdicts(rows, at)
            for t, (kind, why) in verdicts.items():
                entry = known.get(t) or {}
                if entry.get("state") != "waiting":
                    continue
                entry["state"], entry["why"] = "expired", why
                if kind == "superseded":
                    entry["superseded"] = True
                if kind in ("other-login", "answered"):
                    entry["alarm_quiet"] = kind          # never the other_login list
                skips[kind if kind in ("superseded", "other-login", "answered")
                      else "expired"] += 1
                to_drop.add(t)
                for ct in entry.get("children") or []:
                    kid = known.get(ct)
                    if kid is not None and kid.get("state") == "waiting":
                        kid["state"], kid["why"] = "expired", why
                        to_drop.add(ct)
        began_cache = {}
        began = lambda sid: session_began(sid, roots, post, began_cache)
        login_cache = {}                          # one read per window per pass
        login_of = lambda sid: window_login(hub, roots, sid, login_cache)
        # EVERY LIVE LETTER IS ROUTED, not only the ones this pass read: a lane
        # nobody held at 09:00 has a holder at 09:05, and the letter that waited
        # must find it.  The incremental read is about BYTES, never about which
        # letters are still owed.
        for token in sorted(known):
            entry = known[token]
            line = entry.get("line") or ""
            if not line or entry.get("state") in ("delivered", "expired"):
                continue
            if not entry.get("parent") and mail.broadcast_machine(entry.get("to") or "") \
                    and broadcast_too_old(entry, cfg, at):
                # M-C: routed no further — the lanes live that day have their copies
                entry["state"], entry["why"] = "expired", BROADCAST_DAY_WHY
                skips["expired"] += 1
                continue
            if expired(entry, cfg, at):
                entry["state"] = "expired"
                entry["why"] = "expired unread — nobody is woken by last week's letter"
                skips["expired"] += 1
                to_drop.add(token)
                continue
            if entry.get("parent"):
                continue                              # a broadcast's copy: its parent routes it
            answer = route(line, mail, claims, ears, fleet, at, by_title, lanes)
            entry["state_kind"] = answer["state"]
            entry["holder"] = answer["holder"]
            entry["why"] = answer["why"]              # the routing answer's own words first…
            if state_is_for_owner(answer["state"]):
                continue
            if answer["state"] == "broadcast":
                # ACT only on the ADDRESSED machine: its own lanes, its
                # own pass.  Every other pass keeps the routing answer's words.
                if machine_of(entry.get("to") or "", mail) == name:
                    sender = broadcast_sender(post, state, token)
                    holders = broadcast_recipients(hub, name, claims, ears, by_title,
                                                   roots, at, exclude=(sender,) if sender else ())
                    queued += fan_out(post, state, known, token, entry, mail, holders,
                                      name, at, dry=opts.get("dry"), began=began, skips=skips,
                                      login_of=login_of, same_login=logins_same)
                continue
            entry["why"] = why_for(entry, answer["holder"], ears, mail, posts, at,
                                   sessions=sessions, cfg=cfg)
            holder = answer["holder"]
            # ACT only when the answer names THIS machine: every pass on every
            # machine computes the same answer, and exactly one of them acts on it.
            if holder and holder.get("machine") == name and holder.get("session") \
                    and not safe_session_id(holder["session"]):
                entry["why"] = ("its holder's session id is not a plain token — nothing "
                                "is queued under a name like that")
                said.append("ignored an unusable session id for %s — %s"
                            % (entry["to"], entry["why"]))
            elif holder and holder.get("machine") == name and holder.get("session") \
                    and not already_carried(state, token, holder["session"]):
                quiet = bool(getattr(mail, "is_quiet", lambda _l: False)(line))
                n = 0 if opts.get("dry") else queue_pending(post, holder["session"], [{
                    "token": token, "kind": "letter", "line": line,
                    "to": entry["to"], "fyi": entry["fyi"], "queued": iso(at),
                    "quiet": quiet}])
                entry.setdefault("queued", iso(at))     # what the nudge measures against
                if quiet:
                    entry["quiet"] = True               # R3: queued for the next turn, never a wake
                queued += n
        if to_drop and not opts.get("dry"):
            # ONE walk over the pending files for all of it (a thousand retired letters
            # must not mean a thousand walks)
            drop_pending(post, to_drop)

        # 6 — observe: a letter is delivered when it is SEEN
        seen = observe(post, hub, state, known, sessions, roots, opts)
        said.extend(seen)
        broadcast_rollup(known, lambda a: machine_of(a, mail))     # 
        # EVERY FINISHED LETTER LEAVES THE PENDING FILES — stamped in INBOX, seen in
        # its window (a --read, a push), expired, or left there by a build before this one —
        # so no hook carries it a second time. One walk, and only when the finished set
        # changed; the stamped ones are counted in each file, so the window's next frame says
        # how many it was spared.
        finished = sorted(t for t, e in known.items() if e.get("state") in ("delivered", "expired"))
        sig = hashlib.sha256(",".join(finished).encode("ascii", "replace")).hexdigest()[:16]
        if finished and sig != state.get("swept") and not opts.get("dry"):
            drop_pending(post, set(finished), count=delivered_elsewhere, kinds=("letter",))
            state["swept"] = sig

        # 7 — the sender's duties
        said.extend(sender_duties(post, hub, state, known, cfg, mail, name, posts, opts))

        # 7b — PHASE B, the surfaces.  The holds cache is reconciled from
        # claims.json (the truth) so the hook can ask an idle window to arm its
        # own waiter; a letter no road can carry becomes a nudge at the same
        # moment its sender hears `not read yet`; and every note for the owner is
        # raised here once, pushed by one live session's own turn, and reported
        # back to whoever sent it.
        #
        # THE SURFACES' MARK IS THE FIRST THING WRITTEN: every step
        # below asks "was this first seen after the surfaces began?", and on the
        # first pass of this build the mark did not exist yet when the nudges
        # were composed — so a day's worth of waiting letters were nudged and
        # raised at once.  Nothing of phase B's runs before this line.
        fresh_surfaces = not state.get("surfaces_from")        # this pass is their bootstrap
        said.extend(bootstrap_surfaces(state, known, at))
        said.extend(pause_pass(hub, post, opts))   # / B: the pause pass, before the holds read its state
        holds_reconcile(post, hub, claims, ears, name, cfg, dry=opts.get("dry"), home=opts.get("home"))
        compose_nudges(post, hub, state, known, cfg, mail, name, roots, at,
                       state.get("sent") or {}, sessions=sessions, home=opts.get("home"))
        # 7c — the attended road: push into a window someone is looking at;
        # queue AND announce for a quiet one. Never a wake.
        said.extend(attend(post, hub, state, known, cfg, mail, name, roots, sessions,
                           dict(opts, fresh_surfaces=fresh_surfaces), at))
        # 7d — , the dial road: a window's plate is an order an attended window carries
        said.extend(dial_road(post, hub, state, cfg, name, roots, sessions, opts, at))
        said.extend(owner_surfaces(post, hub, state, known, cfg, mail, name, posts,
                                  roots, sessions, opts, at))

        # 8 — publish what THIS machine owns, and push once when something changed
        for token, entry in known.items():
            entry["_mine"] = token in (state.get("sent") or {})
        body = publish_body(name, known, state, legacy, cfg, mail, fleet, state.get("sent"))
        changed = publish(hub, name, body, dry=opts.get("dry"))
        if changed and not opts.get("dry"):
            if push_brain(opts, hub):
                said.append("pushed")
        # M-G — THE TOOLS SAY WHAT THEY SKIPPED: this pass's counts, in the summary and,
        # for the last pass that skipped anything, in the heartbeat --status reads
        skip_line = " · ".join("%d %s" % (skips[w], w) for w in SKIP_WORDS if skips[w])
        if skip_line:
            said.append("skipped this pass: %s" % skip_line)
            state["skipped"] = dict(skips, when=iso(at))
        if not opts.get("dry"):
            prune(known, cfg, at)
            prune_nudges(state, known, cfg, at)
            write_done(post, known)                       # M-B: the hook's done index
            write_json_atomic(post / "state.json", state)
            beat = {"when": iso(at), "every": int(cfg["pass_every"]), "version": VERSION,
                    "last_good_pull": state.get("last_good_pull") or ""}
            if isinstance(state.get("skipped"), dict):
                beat["skipped"] = state["skipped"]
            write_json_atomic(post / "heartbeat.json", beat)
        if queued:
            said.append("queued %d letter(s) for sessions on this machine" % queued)
        if opts.get("counters"):
            write_json_atomic(opts["counters"], dict(_COUNTERS))
        return 0, said
    finally:
        if not opts.get("dry"):
            drop_lock(lock)


def take_lock(path, stale=300):
    """One pass at a time on a machine.  A lock older than five minutes is a dead
    pass's, and is taken over."""
    _heavy()
    path = Path(path)
    if not path.parent.exists():
        mkdirs(path.parent)
    old = read_json(path, None)
    if isinstance(old, dict):
        when = parse_iso(old.get("when"))
        if when is not None and (now() - when).total_seconds() < stale:
            return False
    write_json_atomic(path, {"pid": os.getpid(), "when": iso(now())})
    return True


def drop_lock(path):
    try:
        os.unlink(str(path))
    except OSError:
        pass


def expired(entry, cfg, at):
    first = parse_iso(entry.get("first_seen"))
    if first is None:
        return False
    hours = (at - first).total_seconds() / 3600.0
    if entry.get("fyi"):
        return hours > float(cfg["fyi_hours"])
    return hours > float(cfg["letter_days"]) * 24.0


# --------------------------------------------------------------------------
# old mail stops ringing
# --------------------------------------------------------------------------

BROADCAST_DAY_WHY = "a broadcast is for the lanes live that day"
SKIP_WORDS = ("delivered by stamp", "already handed", "expired", "superseded", "born-after",
              "other-login", "resolved by stamp", "answered")


# mail.py's RESOLVED_MARK, for a mail.py from before it — the pass reads the mark
# from mail.py first, always.
RESOLVED_WORD = " · resolved:"


def untail(line, marks):
    """A line with its stamps' tails cut off at the EARLIEST mark present (each found at
    its last occurrence) — the letter's own words, the way mail.py's token() reads them."""
    s = str(line or "")
    cuts = [s.rfind(m) for m in marks if s.rfind(m) >= 0]
    return s[:min(cuts)].rstrip() if cuts else s


def resolved_why(line, resolved_word):
    """The why, `resolved by the push that landed at HH:MM`, from the line's own tail."""
    s = str(line or "")
    cut = s.rfind(resolved_word)
    tail = s[cut + len(resolved_word):].strip() if cut >= 0 else ""
    when = parse_iso(tail.split(" ", 1)[0]) if tail else None
    return "resolved by the push that landed%s" % (
        (" at %s" % when.astimezone().strftime("%H:%M")) if when is not None else "")


def day_end(date_text, at):
    """The last second of a letter's own DATE, local — None when the field is not a date."""
    try:
        d = datetime.strptime(str(date_text or "").strip(), "%Y-%m-%d")
    except ValueError:
        return None
    return d.replace(hour=23, minute=59, second=59).astimezone(at.tzinfo)


def first_seen_for(date_text, at):
    """M-H: FIRST SEEN IS NEVER LATER THAN THE LETTER'S OWN DATE — a line dated 09-25
    that a reset or rebuilt post state meets today was first seen at the end of 09-25,
    so letter_days and fyi_hours measure the letter and never the post file."""
    end = day_end(date_text, at)
    return end if (end is not None and end < at) else at


def clamp_first_seen(entry, at):
    """M-H on an entry already in the state (one written before this build)."""
    end = day_end(entry.get("date"), at)
    first = parse_iso(entry.get("first_seen"))
    if end is not None and first is not None and first > end:
        entry["first_seen"] = iso(end)
        return True
    return False


def past_horizon(entry, cfg, at):
    """Is a letter's own DATE more than `letter_days` behind? Then the first_seen clamp
    retires it at first sight, and prune may let its entry go ."""
    end = day_end(entry.get("date"), at)
    return end is not None and (at - end).total_seconds() > float(cfg["letter_days"]) * 86400.0


def broadcast_too_old(entry, cfg, at):
    """M-C: a broadcast is routed no further once it is `broadcast_hours` old."""
    first = parse_iso(entry.get("first_seen"))
    if first is None:
        return False
    return (at - first).total_seconds() > float(cfg.get("broadcast_hours") or 24) * 3600.0


def stamp_record(line, mark_word, at):
    """M-A: the delivery a ` · delivered: <ISO> by <title>` tail records, read from it."""
    tail = str(line or "")
    cut = tail.rfind(mark_word)
    tail = tail[cut + len(mark_word):].strip() if cut >= 0 else ""
    after = tail.find(RESOLVED_WORD)              # a resolved tail may follow it
    if after >= 0:
        tail = tail[:after].strip()
    when, _sep, title = tail.partition(" by ")
    stamp = parse_iso(when.strip())
    return {"when": iso(stamp) if stamp is not None else iso(at), "road": "inbox stamp",
            "evidence": "INBOX.md", "session": "", "title": title.strip()}


def session_began(session, roots, post, cache=None):
    """When a session BEGAN, from bytes on disk: the first record of its own transcript
    that carries a timestamp (Claude's first line, a Codex rollout's session_meta), else
    the session map's own first sight of it. None when nothing says — and then the
    broadcast is not withheld on a guess."""
    if cache is not None and session in cache:
        return cache[session]
    began = None
    path = transcript_of(session, "claude", roots) or transcript_of(session, "", roots)
    if path:
        try:
            data = read_region(path, 0, min(65536, os.path.getsize(path)))
        except OSError:
            data = b""
        for line in data.decode("utf-8", "replace").splitlines()[:50]:
            if '"timestamp"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("timestamp"):
                began = parse_iso(rec.get("timestamp"))
                if began is not None:
                    break
    if began is None:
        row = read_json(session_file(post, session), None) or {}
        began = parse_iso(row.get("registered") or row.get("first_seen"))
    if cache is not None:
        cache[session] = began
    return began


def pull_if_due(hub, state, opts, cfg):
    """The brain, and only through sync.py behind the seam.  A failed pull never
    fails the pass: local letters still move, and --status says so."""
    if opts.get("no_pull"):
        return ""
    last = parse_iso(state.get("last_pull"))
    waiting = any(e.get("state") == "waiting" for e in (state.get("letters") or {}).values())
    due = 60 if waiting else 300
    if last is not None and (now() - last).total_seconds() < due:
        return ""
    state["last_pull"] = iso(now())
    ok, out = run_sync(opts, "pull")
    if ok:
        state["last_good_pull"] = iso(now())
        return ""
    return "pull failed — local letters still move (%s)" % (out or "no reason given")[:120]


def push_brain(opts, hub):
    ok, _out = run_sync(opts, "push")
    return ok


def run_sync(opts, verb, timeout=120):
    """git only ever through sync.py, and always behind the --sync seam."""
    _heavy()
    which = opts.get("sync")
    engine = None if which else machine_paths(opts.get("home")).get("sync_dir")
    if not which and engine is None:
        return False, "no sync.py: the machine record the path resolver finds names no sync package"
    path = Path(which) if which else (Path(engine) / "sync.py")
    if not path.is_file():
        return False, "no sync.py at %s" % path
    try:
        r = subprocess.run([sys.executable, str(path), verb], capture_output=True,
                           text=True, timeout=timeout, cwd=str(path.parent))
        return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()[-400:]
    except Exception as exc:
        return False, repr(exc)


def fold_receipts(post, state):
    """Every delivery receipt this machine has written, read forward only.  Folded
    BEFORE the routing step and not after it: a pass that ran inside the receipt's
    grace used to queue a letter the hook had just handed over."""
    got, new_offset = receipts(post, int(state.get("receipt_offset") or 0))
    state["receipt_offset"] = new_offset
    by_token = state.setdefault("receipts", {})
    for r in got:
        by_token.setdefault(str(r.get("token")), r)
    return by_token


def observe(post, hub, state, known, sessions, roots, opts):
    """DELIVERED MEANS SEEN.  The token is looked for in the holder's OWN
    transcript, from the byte offset remembered for that session — a bounded read,
    never the whole file.  A token found only in ANOTHER session's transcript is
    `also_seen_by`: that session asked for the mailbox and read it, which is not
    delivery.  An unreadable transcript makes THAT letter say why; the others
    proceed."""
    _heavy()
    said = []
    offsets = state.setdefault("read_offsets", {})
    by_token = fold_receipts(post, state)
    wanted = dict((t, e) for t, e in known.items() if e.get("state") == "waiting"
                  and e.get("state_kind") != "broadcast")   # its copies are looked for
    if not wanted:
        return said
    # WHOSE TRANSCRIPTS ARE LOOKED AT: every session the record names — the map
    # the pass has bound, and every holder a claim or an ear points at.  A session
    # that has never run an exocortex tool names no transcript and is not looked
    # for; nothing here is ever inferred from a folder or a clock.
    sessions = dict(sessions)
    for sid, row in named_sessions(hub).items():
        sessions.setdefault(sid, row)
    for entry in known.values():
        holder = entry.get("holder") or {}
        sid = str(holder.get("session") or "")
        if sid and sid not in sessions:
            sessions[sid] = {"session": sid, "title": holder.get("title") or "",
                             "vendor": "", "transcript": ""}
    for session, row in sessions.items():
        path = transcript_of(session, row.get("vendor") or "", roots, row.get("transcript") or "")
        if not path:
            continue
        try:
            size = os.path.getsize(path)
            with open(str(path), "rb"):
                pass                    # stat succeeds on a file we may not OPEN
        except OSError:
            for token, entry in wanted.items():
                if (entry.get("holder") or {}).get("session") == session:
                    entry["why"] = ("its transcript could not be read — nothing else is "
                                    "held up by it")
            continue
        lo = int(offsets.get(session) or 0)
        if size < lo:
            lo = 0
        lo = max(0, lo - 4096, size - 4 * 1024 * 1024)
        data = read_region(path, lo, size)
        _COUNTERS["transcript_files"] += 1
        offsets[session] = size
        if not data:
            continue
        # Keep the raw region for informational sightings in other sessions only.
        lines = data.split(b"\n")
        if lo > 0:
            lines = lines[1:]                    # the first record may be cut in half
        contexts = []
        for line in lines:
            try:
                record = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            if not isinstance(record, dict):
                continue
            shape, text = "", ""
            if row.get("vendor") == "codex":
                payload = record.get("payload")
                if record.get("type") != "response_item" or not isinstance(payload, dict) \
                        or payload.get("type") != "message":
                    continue
                content = payload.get("content")
                if not isinstance(content, list):
                    continue
                if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                    continue
                text = "\n".join(b["text"] for b in content if isinstance(b, dict)
                                 and isinstance(b.get("text"), str))
                meta = payload.get("internal_chat_message_metadata_passthrough") or {}
                kinds = meta.get("content_item_kinds") if isinstance(meta, dict) else []
                if payload.get("role") == "developer" and isinstance(kinds, list) \
                        and "hooks.additional_context" in kinds:
                    shape = "codex/developer"
                elif payload.get("role") == "user":
                    shape = "codex/user"
            else:
                attachment = record.get("attachment")
                message = record.get("message")
                if record.get("type") == "attachment" and isinstance(attachment, dict) \
                        and attachment.get("type") == "hook_additional_context":
                    text = attachment.get("content")
                    if isinstance(text, list):      # the real record: one string per hook output
                        text = "\n".join(t for t in text if isinstance(t, str))
                    shape = "claude/attachment"
                elif record.get("type") == "api-request-blob" and isinstance(message, dict) \
                        and message.get("role") == "system":   # the hook's blob is system; a
                    content = message.get("content")           # user's copy is never hook proof
                    if isinstance(content, list):
                        text = "\n".join(b["text"] for b in content if isinstance(b, dict)
                                         and b.get("type") == "text"
                                         and isinstance(b.get("text"), str))
                    if "hook additional context:" in text:
                        shape = "claude/api-request-blob"
            if shape and isinstance(text, str) and "carried by the postman" in text:
                contexts.append((shape, text))
        for token, entry in wanted.items():
            if entry.get("state") != "waiting":
                continue
            holder = entry.get("holder") or {}
            if holder.get("session") == session:
                body = entry.get("line") or ""
                # The continuation prompt's text is HTML-escaped by the coding app.
                # A placeholder (`<your title>`) lands as
                # `&lt;your title&gt;`), so the body is compared after unescaping.
                import html as _html
                contexts = [(shape, _html.unescape(text)) for shape, text in contexts]
                matched = next((shape for shape, text in contexts
                                if body and body in text and token in text), None)
                if not matched:
                    continue
                stamp = iso(now())
                entry["state"] = "delivered"
                # The title is the HOLDER's own, so a sender and the
                # tree read the window's name and not an empty string.
                pushed = (entry.get("attended") or {}).get("road") == "send"
                entry["delivered"] = {"when": (entry.get("delivered") or {}).get("when") or stamp,
                                      "road": (by_token.get(token) or {}).get("road")
                                      or ("send" if pushed else "read"),
                                      "evidence": "transcript", "record": matched, "session": session,
                                      "title": row.get("title") or holder.get("title") or ""}
            elif token.encode("ascii") in data:
                seen = entry.setdefault("also_seen_by", [])
                if not any(s.get("title") == (row.get("title") or session) for s in seen):
                    seen.append({"title": row.get("title") or session, "when": iso(now())})
    # A receipt proves emission only. Keep the first hand-off and tell the sender
    # why it still waits; only a body-bound injected record can prove delivery.
    for token, entry in wanted.items():
        if entry.get("state") != "waiting":
            continue
        rec = by_token.get(token)
        if not rec or (entry.get("holder") or {}).get("session") != rec.get("session"):
            continue
        when = parse_iso(rec.get("when"))
        if when is None or (now() - when).total_seconds() < RECEIPT_GRACE_S:
            continue
        emitted = entry.setdefault("emitted", {
            "when": rec.get("when"), "road": rec.get("road"), "event": rec.get("event"),
            "session": rec.get("session"),
            "title": (sessions.get(str(rec.get("session"))) or {}).get("title", "")
                     or (entry.get("holder") or {}).get("title", "")})
        handed = parse_iso(emitted.get("when"))
        entry["why"] = "handed to «%s»'s %s hook at %s — not yet seen in its transcript" % (
            emitted.get("title") or "", emitted.get("event") or "",
            handed.strftime("%H:%M") if handed else "?")
    return said


def sender_duties(post, hub, state, known, cfg, mail, name, posts, opts):
    """REQUIREMENT 2: the sender is never left in silence.

    A letter this machine sent that is still waiting after `not_read_minutes` earns
    ONE notice with its why.  A letter that is read AFTER such a notice earns ONE
    `has now been read`.  A letter read inside the threshold earns nothing, and an
    FYI letter never reports at all.  The three answers that are not about waiting
    — AMBIGUOUS, an unknown machine, nobody holding the lane — are told at the NEXT
    pass rather than at five minutes: they will not improve by waiting."""
    _heavy()
    said = []
    sent = state.setdefault("sent", {})
    folder = Path(post) / "outbox"
    try:
        files = sorted(folder.glob("*.json"))
    except OSError:
        files = []
    for f in files:
        d = read_json(f, None)
        if isinstance(d, dict) and d.get("token"):
            sent.setdefault(str(d["token"]), {"to": d.get("to") or "", "when": d.get("when") or "",
                                              "from": d.get("from") or {},
                                              "told_not_read": False, "told_read": False})
    at = now()
    threshold = float(cfg["not_read_minutes"])
    for token, row in sent.items():
        entry = known.get(token) or fleet_entry(posts, token)
        if entry is None:
            continue
        if entry.get("fyi"):
            continue
        if state_is_for_owner(entry.get("state_kind")):
            continue        # a note for OWNER earns its sender its OWN notice, once,
                            # after the raise decision — never a five-minute `not read
                            # yet` about a human, who is not a session with a mailbox
        session = (row.get("from") or {}).get("session") or ""
        if not session or not safe_session_id(session):
            continue
        waited = minutes_since(row.get("when"), at)
        if waited is None:
            continue
        if entry.get("state") == "waiting":
            kind = entry.get("state_kind") or ""
            at_once = kind in ("ambiguous", "no_machine", "nobody") or \
                (entry.get("holder") or {}).get("machine") not in (None, "", name)
            if row.get("told_not_read"):
                continue
            if not at_once and waited < threshold:
                continue
            why = entry.get("why") or "it is not read yet"
            text = not_read_notice(row.get("to") or entry.get("to") or "",
                                   short_time(row.get("when")), waited, why)
            if not opts.get("dry"):
                # An AT-ONCE notice tells the sender something it
                # can act on but does not mean the letter was read, so it rides
                # the hook roads and never ends a waiter's wait.
                # NO notice ends a wait (mail.py's wants_answer is the one test):
                # the five-minute one waits for the window's next turn start too.
                queue_pending(post, session, [{"token": token, "kind": "notice", "text": text,
                                               "to": row.get("to") or "", "fyi": False,
                                               "wake": not at_once, "queued": iso(at)}])
            row["told_not_read"] = True
            said.append(text)
        elif entry.get("state") == "delivered" and row.get("told_not_read") \
                and not row.get("told_read"):
            read_when = parse_iso((entry.get("delivered") or {}).get("when"))
            if read_when is not None and (at - read_when).total_seconds() > READ_NEWS_HOURS * 3600:
                # a read the pass only learned of now (an INBOX stamp met by a re-parse,
                # a receipt) that happened long ago is history — no notice days after the fact
                row["told_read"] = True
                continue
            read_at = minutes_since(row.get("when"), read_when or at)
            text = now_read_notice(row.get("to") or entry.get("to") or "",
                                   short_time(row.get("when")), read_at or 0)
            if not opts.get("dry"):
                queue_pending(post, session, [{"token": token, "kind": "notice", "text": text,
                                               "to": row.get("to") or "", "fyi": False,
                                               "queued": iso(at)}])
            row["told_read"] = True
            said.append(text)
    return said


def fleet_entry(posts, token):
    """A letter's state as ANY machine records it — the holder's machine writes
    it, and the sender's machine reads it from there."""
    for body in posts.values():
        entry = (body.get("letters") or {}).get(token)
        if isinstance(entry, dict):
            return entry
    return None


def short_time(when):
    d = parse_iso(when)
    return d.strftime("%H:%M") if d else "??:??"


def owner_of(entry, mail, fleet, sent, name):
    """WHICH MACHINE WRITES THIS LETTER'S ENTRY, so that two machines never
    write one letter's state into the brain: the holder's machine; with no holder,
    the addressed machine; with a machine name the fleet does not carry, the
    sender's."""
    if state_is_for_owner(entry.get("state_kind")):
        return name          # a letter for the human belongs to every machine that
                             # sees it: phase B raises it locally, wherever the owner is,
                             # and phase A must lose none of them
    holder = entry.get("holder") or {}
    if holder.get("machine"):
        return str(holder["machine"]).lower()
    mch = machine_of(entry.get("to") or "", mail)
    if mch in fleet:
        return mch
    return name if entry.get("_mine") else ""


def publish_body(name, known, state, legacy, cfg, mail=None, fleet=(), sent=None):
    """post-<machine>.json, exactly the shape the post file has — and nothing that moves
    on its own."""
    letters = {}
    for token, e in known.items():
        if mail is not None and owner_of(e, mail, fleet, sent, name) != name:
            continue                            # another machine's to write
        row = {"to": e.get("to"), "date": e.get("date"), "first_seen": e.get("first_seen"),
               "fyi": bool(e.get("fyi")), "state": e.get("state") or "waiting",
               "holder": e.get("holder"), "why": e.get("why") or ""}
        if e.get("delivered"):
            row["delivered"] = e["delivered"]
        if e.get("also_seen_by"):
            row["also_seen_by"] = e["also_seen_by"]
        if e.get("nudged"):
            row["nudged"] = e["nudged"]
        if e.get("state_kind") == "broadcast":
            row["broadcast"] = True                  # the letter itself
            row["children"] = list(e.get("children") or [])
        if e.get("parent"):
            row["parent"] = e["parent"]              # one lane's copy of it
        owner = (owner_block(state) or {}).get(token)
        if isinstance(owner, dict):
            row["owner"] = owner_row(owner)
        if e.get("line"):
            # THE LETTER'S OWN WORDS.  The tree's ✉ promises "the line verbatim"
            # on a click and `--status` says it on the other machine too, so the
            # one file that answers for a letter carries what the letter says.
            # It never changes for a token, so the brain still does not churn.
            row["line"] = e["line"]
        letters[token] = row
    sent = {}
    for token, r in (state.get("sent") or {}).items():
        sent[token] = {"to": r.get("to"), "when": r.get("when"), "from": r.get("from") or {},
                       "told_not_read": bool(r.get("told_not_read")),
                       "told_read": bool(r.get("told_read"))}
    for_owner = sorted(t for t in letters
                       if state_is_for_owner(known[t].get("state_kind")))
    body = {"machine": name, "version": VERSION, "letters": letters, "sent": sent,
            "for_owner": for_owner}
    nudges = {}
    for token, rec in sorted((state.get("nudges") or {}).items()):
        row = {"kind": "nudge", "to": rec.get("to") or "", "text": rec.get("text") or "",
               "case": rec.get("case") or "", "count": int(rec.get("count") or 0),
               "first_seen": rec.get("first_seen") or "", "letters": rec.get("letters") or []}
        owner = (owner_block(state) or {}).get(token)
        if isinstance(owner, dict):
            row["owner"] = owner_row(owner)
        nudges[token] = row
    if nudges:
        body["nudges"] = nudges
    if state.get("surfaces_from"):
        body["surfaces_from"] = state["surfaces_from"]
    dials = dial_rows_for_post(state)               #  one row per plate
    if dials:
        body["dials"] = dials
    if legacy:
        body["legacy"] = {"count": int(legacy.get("count") or 0),
                          "before": legacy.get("before") or ""}
    return body


def owner_row(owner):
    """A note's `owner` key as the brain carries it: EVENTS only — when it was
    raised, whether a session was asked and what the tool answered, and when
    the owner said `got it`.  Not one timestamp in it moves on its own."""
    out = {}
    raised = owner.get("raised")
    if isinstance(raised, dict):
        out["raised"] = {"when": raised.get("when") or "", "how": raised.get("how") or "",
                         "why": raised.get("why") or ""}
    push = owner.get("push")
    if isinstance(push, dict) and push.get("state"):
        row = {"state": push.get("state")}
        for key in ("session", "title", "when", "result", "why"):
            if push.get(key):
                row[key] = push[key]
        out["push"] = row
    acked = owner.get("acked")
    if isinstance(acked, dict) and acked.get("when"):
        out["acked"] = {"when": acked.get("when"), "by": acked.get("by") or ""}
    return out


def prune_nudges(state, known, cfg, at):
    """A nudge leaves once it is older than owner_hours and acked, or a day old:
    the chip counts what WAITS, and the brain does not keep yesterday's. And a
    `owner` record whose note is gone from both lists goes with it, so the state
    file never grows without bound either."""
    hours = float(cfg["owner_hours"])
    owners = owner_block(state)
    for token in list(state.get("nudges") or {}):
        when = parse_iso((state["nudges"][token] or {}).get("first_seen"))
        if when is None:
            continue
        old = (at - when).total_seconds() / 3600.0
        acked = ((owners.get(token) or {}).get("acked") or {}).get("when")
        if old > max(hours, 24.0) or (acked and old > hours):
            state["nudges"].pop(token, None)
    for token in list(owners):
        if token not in known and token not in (state.get("nudges") or {}):
            owners.pop(token, None)


def prune(known, cfg, at):
    """Delivered and expired entries leave 7 days after their last change, so the
    synced file never grows without bound.

    …AND NOT BEFORE THEIR OWN DATE IS PAST THE HORIZON : a pruned letter whose
    line a full re-parse meets again is a new letter to the pass, and the first_seen clamp
    retires it at once only when its date is more than `letter_days` old. Pruning a day
    sooner than that is how the letters of 09-25 rang again on 10-14."""
    days = float(cfg["letter_days"])
    for token in list(known):
        e = known[token]
        if e.get("state") == "delivered":
            when = parse_iso((e.get("delivered") or {}).get("when"))
        elif e.get("state") == "expired":
            when = parse_iso(e.get("first_seen"))
        else:
            continue
        if day_end(e.get("date"), at) is not None and not past_horizon(e, cfg, at):
            continue
        if when is not None and (at - when).total_seconds() > days * 86400:
            known.pop(token, None)


# ==========================================================================
# PHASE B — THE SURFACES: a note for the owner reaches them, a held window never
# goes deaf, and the tree shows the post.
# ==========================================================================

def live_minutes(hub, machine):
    """The pulse's own liveness window, read from the file the pulse writes —
    never a number typed in here.  Its default when the file says nothing."""
    d = read_json(Path(hub) / ("live-sessions-%s.json" % machine), None)
    try:
        n = int((d or {}).get("live_minutes") or 0)
    except Exception:
        n = 0
    return n if n > 0 else LIVE_MINUTES_DEFAULT


def anyone_here(hub, machine, at=None):
    """Is a human PLAUSIBLY at this machine?  The pulse's own sensed sessions,
    younger than its own window.  A probe of the record, never a guess."""
    at = at or now()
    d = read_json(Path(hub) / ("live-sessions-%s.json" % machine), None)
    if not isinstance(d, dict):
        return False
    window = live_minutes(hub, machine)
    when = parse_iso(d.get("when"))
    if when is not None and (at - when).total_seconds() > window * 60 * 3:
        return False                      # the file itself is older than three windows
    for s in (d.get("sessions") or []):
        if not isinstance(s, dict):
            continue
        try:
            mins = float(s.get("minutes_ago"))
        except (TypeError, ValueError):
            continue
        if mins <= window:
            return True
    return False


# --------------------------------------------------------------------------
# THE RAISE — one desktop notification, no model and no outside service
# --------------------------------------------------------------------------

# macOS.  A FIXED `on run argv` script: the texts are ARGUMENTS, never
# interpolated into AppleScript source, so a note carrying a quote, a backslash
# or `$(` is a string and can never be code.
MAC_NOTIFY_SCRIPT = (
    "on run argv",
    "display notification (item 3 of argv) with title (item 1 of argv) "
    "subtitle (item 2 of argv)",
    "end run",
)

# Windows 10.  A FIXED script, sent as -EncodedCommand (base64 of UTF-16LE) so
# no shell ever parses the texts, which reach the child in its ENVIRONMENT.
# The WinRT types directly: no module to install, no cmdlet to find, and no
# brace block (hub memory `powershell-51-stdin-drops-brace-blocks`).  Silent.
WIN_NOTIFY_SCRIPT = "\n".join((
    "$ErrorActionPreference = 'Stop'",
    "$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
    "ContentType = WindowsRuntime]",
    "$null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, "
    "ContentType = WindowsRuntime]",
    "$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02)",
    "$txt = $tpl.GetElementsByTagName('text')",
    "$null = $txt.Item(0).AppendChild($tpl.CreateTextNode($env:EXO_NOTE_TITLE))",
    "$null = $txt.Item(1).AppendChild($tpl.CreateTextNode($env:EXO_NOTE_BODY))",
    "$audio = $tpl.CreateElement('audio')",
    "$audio.SetAttribute('silent', 'true')",
    "$null = $tpl.SelectSingleNode('/toast').AppendChild($audio)",
    "$aumid = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'",
    "$toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)",
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($aumid)"
    ".Show($toast)",
))

CREATE_NO_WINDOW = 0x08000000


def os_kind(override=None):
    """Which notifier this machine has, PROBED and not read off a record:
    `nt` · `darwin` · `other`.  The override is the gate's seam, so a macOS machine can
    render the Windows command byte for byte without pretending to be one."""
    if override:
        return str(override)
    if os.name == "nt":
        return "nt"
    return "darwin" if sys.platform == "darwin" else "other"


def notify_command(title, subtitle, body, kind=None, notify=None):
    """(argv, environment additions, creation flags, how) for ONE notification.

    A pure renderer, so a gate can read the command without a banner ever
    showing.  `notify` is the seam every gate and test uses in place of the real
    notifier; `how` still names the road this machine would take, because that
    is the code path, and the seam only stands in for its last step."""
    _heavy()
    kind = os_kind(kind)
    how = {"nt": "toast", "darwin": "osascript"}.get(kind, "none")
    if notify:
        head = [sys.executable, str(notify)] if str(notify).endswith(".py") else [str(notify)]
        return head + [title, subtitle, body], {}, 0, how
    if kind == "darwin":
        argv = ["osascript"]
        for line in MAC_NOTIFY_SCRIPT:
            argv += ["-e", line]
        return argv + [title, subtitle, body], {}, 0, how
    if kind == "nt":
        blob = base64_utf16(WIN_NOTIFY_SCRIPT)
        return (["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-EncodedCommand", blob],
                {"EXO_NOTE_TITLE": "%s — %s" % (title, subtitle) if subtitle else title,
                 "EXO_NOTE_BODY": body},
                CREATE_NO_WINDOW, how)
    return [], {}, 0, how


def base64_utf16(text):
    """What -EncodedCommand wants: base64 of the script in UTF-16LE."""
    _heavy()
    import base64
    return base64.b64encode(str(text).encode("utf-16-le")).decode("ascii")


def raise_note(title, subtitle, body, kind=None, notify=None):
    """Run the notifier once, bounded, and say what happened: (how, why).

    `how` is `osascript` · `toast` · `none`; `why` is empty on success and one
    plain line otherwise.  NOTHING here can raise: a failed notification is a
    letter the eye did not get, never a broken pass."""
    _heavy()
    argv, env_add, flags, how = notify_command(title, subtitle, body, kind, notify)
    if not argv:
        return "none", "this machine has no notifier the postman knows"
    env = dict(os.environ)
    env.update(env_add)
    kw = {}
    if flags and os.name == "nt":
        kw["creationflags"] = flags        # no console window, 1,440 times a day
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           timeout=NOTIFY_TIMEOUT, env=env, **kw)
    except Exception as exc:
        return "", repr(exc)[:160]
    if r.returncode != 0:
        return "", ((r.stderr or r.stdout or "").strip() or "exit %d" % r.returncode)[:160]
    return how, ""


# --------------------------------------------------------------------------
# the push text — one line, composed once, carried by the raise AND the push
# --------------------------------------------------------------------------

def push_text(target, text, action="", cap=PUSH_TEXT_MAX):
    """`<target>: <text>`, one line, at most `cap` characters, cut at a word
    boundary with an ellipsis; backticks and asterisks out, because a phone
    shows no markdown.  ` — <action>` rides only if the whole still fits.

    WITH NO TARGET THE TEXT STANDS ALONE.  A nudge has no
    target — its raise carries no subtitle —
    and the old form rendered the empty one anyway, so the frame that reached a
    carrier read `: NORTH/Release has 1 letter(s) waiting 23 min …` and that
    colon would have gone to the phone."""
    who = str(target or "").strip()
    body = str(text or "").strip()
    flat = " ".join((("%s: %s" % (who, body)) if who else body).split())
    for ch in ("`", "*"):
        flat = flat.replace(ch, "")
    tail = str(action or "").strip()
    if tail:
        whole = "%s — %s" % (flat, " ".join(tail.split()).replace("`", "").replace("*", ""))
        if len(whole) <= cap:
            return whole
    if len(flat) <= cap:
        return flat
    cut = flat[:cap - 1]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:.—-") + "…"


# --------------------------------------------------------------------------
# the acks — a note acked on ANY machine is acked on all
# --------------------------------------------------------------------------

def is_note_token(token):
    """WHAT A NOTE'S TOKEN IS — `pm-` or `nd-` and twelve lowercase hex.

    THE ONE RULE, tested before a token becomes a file name, so that
    `mail.py --ack ../../x` never writes `<post>/acks/../../x.json`, and `--ack hello`
    never answers `acked: 1 note(s)`.  mail.py asks this same function, so
    the shape is never spelled twice.  No `re`: the hook's hot path imports
    nothing beyond json/os/sys/time, and a module-level pattern would run at
    import."""
    t = str(token or "")
    return (len(t) == 15 and t[:3] in ("pm-", "nd-")
            and all(c in "0123456789abcdef" for c in t[3:]))


def fold_acks(post, hub, state):
    """`acks/<token>.json` written by `mail.py --ack`, plus every ack already
    published in any machine's post file.  {token: {when, by}}.

    A file whose NAME or whose `token` is not a token's own shape is ignored,
    whatever put it there."""
    _heavy()
    acks = state.setdefault("acks", {})
    try:
        files = sorted((Path(post) / "acks").glob("*.json"))
    except OSError:
        files = []
    for f in files:
        if not is_note_token(f.stem):
            continue
        d = read_json(f, None)
        if isinstance(d, dict) and is_note_token(d.get("token")):
            acks.setdefault(str(d["token"]), {"when": d.get("when") or "", "by": d.get("by") or ""})
    for body in read_posts(hub, live_sessions=False).values():
        for group in ("letters", "nudges"):
            for token, e in (body.get(group) or {}).items():
                got = (owner_block(e) or {}).get("acked")
                if isinstance(got, dict) and got.get("when"):
                    acks.setdefault(str(token), {"when": got.get("when"), "by": got.get("by") or ""})
    return acks


def earliest_seen(token, posts, mine=""):
    """AGE's own clock: the EARLIEST first_seen any machine's post file records
    for this token, this machine's included.  The origin's first sight is the
    send time within a minute, so a note is never called fresh on the second
    machine merely because it arrived there late."""
    best = parse_iso(mine) if mine else None
    for body in posts.values():
        for group in ("letters", "nudges"):
            e = (body.get(group) or {}).get(token)
            if not isinstance(e, dict):
                continue
            when = parse_iso(e.get("first_seen"))
            if when is not None and (best is None or when < best):
                best = when
    return best


# --------------------------------------------------------------------------
# THE TWO QUESTIONS EVERY SURFACE ASKS FIRST:
# has anyone said "install it" on THIS machine, and when did the surfaces
# start?  Both are answered before a single human eye is pulled anywhere.
# --------------------------------------------------------------------------

# The why a note carries on a machine where the postman was never installed.
NOT_INSTALLED = "the postman is not installed on this machine"


def installed_here(post):
    """DID ANYONE SAY "install it" ON THIS MACHINE?  `--install-hooks` writes
    `installed.json` into POST DIR and `--uninstall-hooks` removes it; the file
    is machine-personal and never crosses the brain.

    WHY THE PASS MUST ASK: the brain carries `tools/` to the
    OTHER machine within minutes, and that machine's pulse runs `postman.py
    --pass` on every beat as its floor — so the surfaces went live there with no
    hooks installed and nobody at that machine having said the word.  The TOOL
    travels; the WORD must not, so the word is a file the pass can read.
    Without it the pass is phase A's pass plus the holds cache and the tree
    facts: it raises nothing, pushes nothing and nudges nothing.

    `os.path` only — this is asked on the pass's path, but it is the same four
    imports the hook's hot path allows, so it can never cost an import."""
    try:
        return os.path.isfile(os.path.join(str(post), "installed.json"))
    except Exception:
        return False


def bootstrap_surfaces(state, known, at):
    """THE SURFACES' MARK — written BEFORE anything else phase B does in a pass, and the
    loud line said once.

    WHAT WENT WRONG.  The mark used to be written inside
    `owner_surfaces()`, which runs AFTER `compose_nudges()`.  So on the very
    first pass of this build `compose_nudges` read no mark at all, skipped the
    "nothing older than this build" test for EVERY letter, and composed four
    nudges for letters that had waited between one and two days — all four then
    raised at once, four banners on one screen, and four phone pushes queued.
    The mark is now the FIRST thing the pass writes, so the test can never be
    skipped again.

    THE COUNT is every letter still waiting that was first seen BEFORE the mark
    — FYI and `to: OWNER` alike — because every one of them stays on the tree
    and not one will ever be raised, pushed or nudged.  It used to count only
    the `for_owner` ones, which is why the real bootstrap pass said `0` while
    four nudges went out behind the line."""
    if state.get("surfaces_from"):
        return []
    state["surfaces_from"] = iso(at)
    mark = parse_iso(state["surfaces_from"])
    older = 0
    for entry in (known or {}).values():
        if not isinstance(entry, dict) or entry.get("state") != "waiting":
            continue
        first = parse_iso(entry.get("first_seen"))
        if first is not None and mark is not None and first < mark:
            older += 1
    return ["SURFACES · notes and nudges start from %s · %d earlier waiting "
            "letter(s) stay on the tree only" % (state["surfaces_from"], older)]


# --------------------------------------------------------------------------
# THE HOLDS CACHE — what the hook reads instead of parsing claims.json
# --------------------------------------------------------------------------

# ==========================================================================
# NOTHING WAITS ON FABLE — the window's own model and fill,
# read from its own transcript, decide whether it may wait at all
# ==========================================================================
# Every reader here is json/os only: the Stop hook calls window_facts() on its
# hot path, and the hot path imports nothing past json/os/sys/time.

USAGE_FILE = "usage-settings.json"
USAGE_DEFAULTS = {"wait_refuse_models": ["claude-fable-"],
                  "wait_context_ceiling_percent": 40,
                  "routine_models": {"openai": "gpt-5.6-sol"}}
WINDOW_DEFAULT = 1000000        # tokens, when the transcript records no window of its own
DESK_LANE = "Exocortex-Desk"    # the executor's address: <MACHINE>/Exocortex-Desk (R4)
WAITS_LOG = "waits.jsonl"       # every refusal and every --force, one line each
REFUSE_LINE = ("wait refused (%s): retire instead: write your carryover and retitle ARCH — "
               "or hand your waiting to the Desk (%s)")
REFUSED_NUDGE = ("POST — this window is %s: %s. Retire with your carryover when done; "
                 "the Desk (%s) carries your letters")


def usage_settings(hub):
    """(settings, missing?) — usage-settings.json in the hub folder, THE USER'S
    FILE, with every default filled.  A missing or unreadable file
    means the defaults; the caller says so once.  The rule is the file's, never
    this tool's: `wait_refuse_models: []` refuses no model at all."""
    cfg = json.loads(json.dumps(USAGE_DEFAULTS))
    path = os.path.join(str(hub or ""), USAGE_FILE)
    d = read_json(path, None) if hub else None
    if not isinstance(d, dict):
        return cfg, True
    if isinstance(d.get("wait_refuse_models"), list):
        cfg["wait_refuse_models"] = [str(x) for x in d["wait_refuse_models"] if str(x).strip()]
    try:
        if d.get("wait_context_ceiling_percent") is not None:
            cfg["wait_context_ceiling_percent"] = float(d["wait_context_ceiling_percent"])
    except (TypeError, ValueError):
        pass
    if isinstance(d.get("routine_models"), dict):
        cfg["routine_models"].update(dict((str(k), str(v)) for k, v in
                                          d["routine_models"].items()))
    return cfg, False


def defaults_said(cfg):
    return ("usage-settings.json not found — defaults: refuse %s · context ceiling %g%%"
            % (", ".join("%s*" % p for p in cfg["wait_refuse_models"]) or "no model",
               float(cfg["wait_context_ceiling_percent"])))


def window_facts(path, cap=262144):
    """{found, model, context, window} of a window, from ITS OWN transcript's last
    main-thread assistant record — the model the app wrote on it and the context
    it carried in (input + cache read + cache creation).  The window is the
    transcript's own figure when a record names one, else WINDOW_DEFAULT.
    Bounded: one seek and one read of the tail; a torn line is skipped."""
    out = {"found": False, "model": "", "context": 0, "window": WINDOW_DEFAULT,
           "path": str(path or "")}
    if not path:
        return out
    try:
        size = os.path.getsize(str(path))
        with open(str(path), "rb") as fh:
            if size > cap:
                fh.seek(size - cap)
            raw = fh.read(cap)
    except (OSError, ValueError):
        return out
    out["found"] = True
    lines = raw.decode("utf-8", "replace").splitlines()
    if size > cap and lines:
        lines = lines[1:]
    for line in reversed(lines):
        if '"assistant"' not in line and "ontextWindow" not in line \
                and "context_window" not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        for key in ("contextWindow", "context_window"):
            if out["window"] == WINDOW_DEFAULT and isinstance(rec.get(key), int) and rec[key] > 0:
                out["window"] = int(rec[key])
        if out["model"] or rec.get("type") != "assistant" or rec.get("isSidechain"):
            continue
        message = rec.get("message") or {}
        model = str(message.get("model") or "")
        if not model or model.startswith("<"):
            continue                          # the app's own <synthetic> records ran on no model
        usage = message.get("usage") or {}
        total = 0
        for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            try:
                total += int(usage.get(key) or 0)
            except (TypeError, ValueError):
                pass
        out["model"], out["context"] = model, total
    return out


def refused_family(prefix):
    """`claude-fable-` → `Fable`: the mind a prefix names, for the sentence."""
    parts = [p for p in str(prefix or "").split("-") if p]
    word = parts[1] if len(parts) >= 2 and parts[0].lower() == "claude" else (parts[0] if parts else prefix)
    return str(word).capitalize()


def window_verdict(facts, cfg):
    """{refuse, why, percent} — R1 (a listed model) first, then R2 (the ceiling).
    Never a guess: a window whose transcript was not found is refused, and says
    so, because arming blind is exactly what this rule exists to stop."""
    if not facts.get("found"):
        return {"refuse": True, "percent": None, "kind": "blind",
                "why": "no transcript found for this window — never arm blind"}
    model = str(facts.get("model") or "")
    if not model:
        return {"refuse": True, "percent": None, "kind": "blind",
                "why": "its transcript names no model yet — never arm blind"}
    for prefix in cfg.get("wait_refuse_models") or []:
        if model.lower().startswith(str(prefix).lower()):
            return {"refuse": True, "percent": None, "kind": "model", "model": model,
                    "why": "this window is %s — nothing waits on %s"
                           % (model, refused_family(prefix)),
                    "said": "nothing waits on %s" % refused_family(prefix)}
    window = int(facts.get("window") or WINDOW_DEFAULT) or WINDOW_DEFAULT
    percent = 100.0 * float(facts.get("context") or 0) / float(window)
    ceiling = float(cfg.get("wait_context_ceiling_percent") or 0)
    if ceiling and percent > ceiling:
        return {"refuse": True, "percent": percent, "kind": "ceiling", "model": model,
                "why": "this window is %s at %.0f%% of its %d-token context, above the %g%% "
                       "ceiling" % (model, percent, window, ceiling),
                "said": "%.0f%% full, above the %g%% ceiling — nothing waits on a window "
                        "that full" % (percent, ceiling)}
    return {"refuse": False, "percent": percent, "kind": "", "model": model, "why": ""}


def transcript_for_title(title, roots, prefer=""):
    """THE TITLE → TRANSCRIPT ROAD.  The desktop app writes a session's title
    into `<projects>/<folder>/<session id>/custom-title.json` (its own `local_`
    ids are not the transcript ids), so a title is found by reading those small
    files and nothing else.  Several sessions carrying one title: the one this
    process belongs to (`prefer`) wins, else the one written most recently.
    '' when no transcript on this machine carries the title."""
    want = str(title or "").strip()
    if not want:
        return ""
    base = str((roots or {}).get("claude") or os.path.join(os.path.expanduser("~"), ".claude"))
    projects = os.path.join(base, "projects")
    hits = []
    try:
        folders = sorted(os.listdir(projects))
    except OSError:
        return ""
    for folder in folders[:2000]:
        root = os.path.join(projects, folder)
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            meta = os.path.join(root, name, "custom-title.json")
            if not os.path.isfile(meta):
                continue
            d = read_json(meta, None)
            if not isinstance(d, dict) or str(d.get("customTitle") or "").strip() != want:
                continue
            transcript = os.path.join(root, "%s.jsonl" % name)
            try:
                hits.append((os.path.getmtime(transcript), name, transcript))
            except OSError:
                continue
    if not hits:
        return ""
    for _m, sid, path in hits:
        if prefer and sid == prefer:
            return path
    hits.sort(reverse=True)
    return hits[0][2]


def wait_verdict(hub, title="", session="", roots=None):
    """What `mail.py --wait` asks before it arms (R1 + R2): which transcript is
    this window's, what its last reply ran on and carried, and the verdict under
    the user's own usage-settings.json."""
    cfg, missing = usage_settings(hub)
    roots = roots if roots is not None else ((machine_record().get("roots") or {}))
    path = ""
    if title:
        path = transcript_for_title(title, roots, prefer=session)
    if not path and session:
        # THE TITLE FALLBACK: a window
        # that has just retitled itself — the Desk — is found by the session id its
        # own environment gives, before anything is refused.
        path = transcript_of(session, "claude", roots)
    if title and not path:
        return {"refuse": True, "kind": "blind", "model": "", "percent": None,
                "why": "no transcript on this machine carries the title «%s», and this "
                       "process names no session with one — never arm blind" % title,
                "transcript": "", "missing": missing, "cfg": cfg}
    facts = window_facts(path)
    verdict = window_verdict(facts, cfg)
    verdict.update({"transcript": path, "missing": missing, "cfg": cfg,
                    "model": facts.get("model") or verdict.get("model") or ""})
    if not path and not title:
        verdict["why"] = ("this process names no session and no --title — never arm blind")
    return verdict


PAUSE_PASS_TIMEOUT = 20      # seconds — the rail on tools/pause.py --pass, like pulse.py's _usage


def pause_pass(hub, post, opts):
    """/ part B: ONE guarded subprocess a pass — tools/pause.py --pass — which
    starts an auto-pause from outside any window (the roster notice, the waiters' stop files, the
    claude helper jobs killed), lifts it at the reset, and keeps the owner's «away» state's
    waiters stopped on every window. It has its own state folder beside POST DIR, so a rehearsal
    pointed at another POST DIR keeps its pause state there too. FAIL-SAFE: no tool, a timeout,
    a non-zero exit — one line and the pass goes on; the lines it prints ride the pass's own."""
    tool = os.path.join(str(hub), "tools", "pause.py")
    if not os.path.isfile(tool):
        return []
    argv = [sys.executable or "python3", tool, "--pass", "--hub", str(hub), "--post-dir", str(post),
            "--state-dir", os.path.join(os.path.dirname(os.path.abspath(str(post))), "pause")]
    if opts.get("home"):
        argv += ["--home", str(opts["home"])]
    if opts.get("notify"):
        argv += ["--notify", str(opts["notify"])]
    if opts.get("dry"):
        argv.append("--dry")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           timeout=PAUSE_PASS_TIMEOUT, cwd=str(hub), env=env)
    except Exception as exc:
        return ["pause: not run (%s)" % type(exc).__name__]
    said = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
    if r.returncode != 0:
        return ["pause: failed (%d)%s" % (r.returncode, (" — " + said[-1]) if said else "")]
    return said[-1:]


def usage_pause_facts(hub, post=None):
    """{all, families, line} when a usage PAUSE is on for this machine's
    Claude windows, else None — read by tools/usage.py beside this file, once a
    pass, and copied into every holds row so the Stop hook reads no hub file.
    No usage.py, no meter, any error: None (no meter is never a pause).

    / part B: the pause state tools/pause.py keeps beside POST DIR
    (`<post>/../pause/state.json`: the owner's «pause, I am away», or the meter's
    auto-pause at 97) counts as a pause too — the same hold, the same no-summon rule —
    folded into the one answer here, so the two call sites below need nothing else."""
    facts = None
    try:
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage.py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("exo_usage_postman", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            facts = mod.pause_facts(str(hub), "claude")
    except Exception:
        facts = None
    held = pause_state_facts(post)
    if not held:
        return facts
    autos = list(held.get("autos") or [])            # login-scoped auto records: pause_scope() applies them
    unscoped = bool(held.get("all") or held.get("families"))
    if not facts:
        if not unscoped and not autos:
            return held
        base = dict(held) if unscoped else {"all": False, "families": [], "line": ""}
        base.pop("autos", None)
        if autos:
            base["autos"] = autos
        return base
    both = dict(facts)
    if unscoped:
        both["all"] = bool(facts.get("all")) or bool(held.get("all"))
        both["families"] = sorted(set(list(facts.get("families") or []) + list(held.get("families") or [])))
    if autos:
        both["autos"] = autos
    return both


def pause_state_facts(post):
    """{all, families, line, autos} from tools/pause.py's state.json beside POST DIR, or None.
    Away reaches every model of every login; an auto record WITH a login is kept apart in
    `autos` ([{login, families, line}]) because it reaches only that login's windows —
    pause_scope() applies it to ONE window; an auto record with no login folds into `all` /
    `families` as before. Fail-open: no file, a file that is not ours, any error — None."""
    if not post:
        return None
    try:
        raw = open(os.path.join(os.path.dirname(os.path.abspath(str(post))), "pause", "state.json"),
                   "rb").read(1 << 18)
        state = json.loads(raw.decode("utf-8", "replace"))
        if not isinstance(state, dict):
            return None
        recs = [state] + [r for r in (state.get("more") or []) if isinstance(r, dict)]
        every, fams, line, autos, any_line = False, [], "", [], ""
        for rec in recs:
            if rec.get("kind") not in ("away", "auto"):
                continue
            any_line = any_line or str(rec.get("line") or "")
            login = str(rec.get("login") or "").strip()
            if rec.get("kind") == "auto" and login and login.lower() != "all":
                autos.append({"login": login,
                              "families": [str(f).lower() for f in rec.get("families") or []],
                              "line": str(rec.get("line") or "")})
                continue
            line = line or str(rec.get("line") or "")
            if rec.get("kind") == "away" or not rec.get("families"):
                every = True
            else:
                fams.extend(str(f).lower() for f in rec.get("families") or [])
        if not any_line:
            return None
        got = {"all": every, "families": sorted(set(fams)), "line": line}
        if autos:
            got["autos"] = autos
        return got
    except Exception:
        return None


def pause_scope(upause, login):
    """The pause facts {all, families, line} that reach ONE window of `login`, or None. The
    unscoped part (the meter's own facts, an away record, an auto record with no login) reaches
    every window; a login-scoped auto record in `autos` reaches only that login's windows — and a
    window whose login cannot be read ('') is reached, never presumed safe (pause.py's rec_hits).
    Facts with no `autos` come back untouched."""
    if not isinstance(upause, dict) or not upause:
        return None
    autos = [r for r in (upause.get("autos") or []) if isinstance(r, dict)]
    if not autos:
        return upause
    every = bool(upause.get("all"))
    fams = list(upause.get("families") or [])
    line = str(upause.get("line") or "")
    have = str(login or "").strip().lower()
    for rec in autos:
        want = str(rec.get("login") or "").strip().lower()
        if want and want != "all" and have and have != "unknown" and want != have:
            continue
        line = line or str(rec.get("line") or "")
        if rec.get("families"):
            fams.extend(str(f).lower() for f in rec["families"])
        else:
            every = True
    if not (every or fams):
        return None
    return {"all": every, "families": sorted(set(fams)), "line": line}


class WindowLogins:
    """The login of a window, through the app's own session store: the record for its cli session
    id names an account folder (first 8 hex), and usage.py's login_of_account maps it to a login
    (the road pause.py's roster uses). '' when no byte names it — such a window is REACHED."""

    def __init__(self, hub, app):
        self.hub, self.app, self.cache = str(hub), app or {}, {}
        self.mod, self.roots = None, {}
        try:
            import importlib.util
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage.py")
            if os.path.isfile(path):
                spec = importlib.util.spec_from_file_location("exo_usage_postman_login", path)
                self.mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(self.mod)
                self.roots = self.mod.paths_record(self.hub)["roots"]
        except Exception:
            self.mod = None

    def of(self, sid):
        if sid in self.cache:
            return self.cache[sid]
        login = ""
        try:
            rec = (self.app.get("by_cli") or {}).get(sid)
            acct = os.path.basename(os.path.dirname(os.path.dirname(str((rec or {}).get("file") or "")))
                                    )[:8].lower() if rec else ""
            if acct and self.mod is not None:
                got, _how = self.mod.login_of_account(self.hub, self.roots, acct)
                if got and str(got).lower() != "unknown":
                    login = str(got)
        except Exception:
            login = ""
        self.cache[sid] = login
        return login


def log_wait(post, row):
    """ONE line per refusal and per --force in POST DIR's waits.jsonl, with the
    title, the model and the time — never a secret, never a letter's words."""
    try:
        path = os.path.join(str(post), WAITS_LOG)
        mkdirs(os.path.dirname(path))
        fresh = not os.path.exists(path)
        body = dict(row)
        body.setdefault("when", iso(now()))
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
        if fresh:
            try:
                os.chmod(path, PRIVATE_FILE)
            except OSError:
                pass
    except Exception:
        pass


def _hook_window(hold, event):
    """R5's test on the Stop hook's hot path: (the verdict when the window is
    REFUSED else None, the model its own transcript names or '').  The window's
    OWN transcript (the event hands its path), the rule the pass copied into the
    holds row — so the hook reads no hub file.  A row written before this build
    carries no rule, and the nudge is exactly as it was."""
    refuse = hold.get("refuse_models")
    ceiling = hold.get("ceiling_percent")
    if refuse is None and ceiling is None:
        return None, ""
    path = str((event or {}).get("transcript_path") or "")
    if not path:
        return None, ""                    # nothing read: never a refusal on a guess
    facts = window_facts(path)
    if not facts.get("found") or not facts.get("model"):
        return None, ""
    cfg = {"wait_refuse_models": list(refuse or []),
           "wait_context_ceiling_percent": float(ceiling or 0)}
    verdict = window_verdict(facts, cfg)
    return (verdict if verdict.get("refuse") else None), facts["model"]


def _model_arg(model):
    """` --model "<id>"` for the arm command — the model the hook READ, quoted,
    because an id like `claude-opus-5-5[1m]` carries brackets a shell would glob.
    Anything but a plain id renders nothing."""
    ok = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-[]")
    model = str(model or "")
    if not model or (set(model) - ok):
        return ""
    return ' --model "%s"' % model


def holds_path(post, session):
    return Path(post) / "holds" / ("%s.json" % session)


# --------------------------------------------------------------------------
# THE TWO RAILS EVERY RENDERED COMMAND RIDES.
# Used by wait_command() here and by hook_command() at the install.
# --------------------------------------------------------------------------

# Every character an address may carry.  Anything else and no command is
# rendered at all: the address is written into the command UNQUOTED, and a
# session title is free text but an address is not.
ADDR_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:/-")


def console_python():
    """THE PYTHON A PRINTED COMMAND MUST NAME.

    On Windows the scheduled pass runs under `pythonw` (the Windows install
    sheet in design/: "the task executes `pythonw` directly"), and THE PASS
    IS WHAT RECONCILES THE HOLDS CACHE — so the cached `--wait` command would
    have been rendered as "…\\pythonw.exe" "…\\mail.py" --wait …, and `pythonw`
    HAS NO STDOUT: the waiter's printed letter IS the delivery, and it would
    have printed nothing at all.  The row would also have flipped between
    `python` and `pythonw` with whoever wrote last, because claim.py runs under
    the session's own `python`.

    So a command a session will RUN always names a console python: `python`
    beside the running `pythonw` when that file is there, else the bare word.
    On any other executable it is sys.executable, exactly as before."""
    _heavy()
    py = sys.executable or ""
    if not py:
        return "python3"
    p = Path(py)
    if p.stem.lower() == "pythonw":
        beside = p.with_name("python" + p.suffix)
        try:
            if beside.is_file():
                return str(beside)
        except OSError:
            pass
        return "python"
    return py


def bash_dq(text):
    """Escape for the inside of BASH DOUBLE QUOTES — and never alter the text.

    The arm line is text a model pastes into a shell, and Claude Code's shell
    tool is bash on both machines (Git Bash on Windows).  Inside double quotes
    bash still expands `$`, a backtick and `\\` — one backtick pair is enough to
    run a command substitution — and the old renderer silently rewrote `"` to
    `'`, so a ritual title stopped matching the stamp's and the waiter exited at
    once with `… is off`.  Real session titles already carry `'`, `—` and `:`."""
    out = []
    for ch in str(text):
        if ch in ("\\", '"', "$", "`"):
            out.append("\\")
        out.append(ch)
    return "".join(out)


def wait_command(hub, address, title, python=None):
    """The command the arm line asks for, rendered per machine from the record
    and the running python — exactly as --install-hooks renders the hook
    command, and never a path written into this file.

    An address that carries anything a shell would read RENDERS NO COMMAND: the
    holds row's `cmd` is empty, it carries `why` instead, and the hook says
    nothing — as it already does for a row with no command."""
    _heavy()
    addr = str(address or "")
    if not addr or (set(addr) - ADDR_OK):
        return ""
    return '"%s" "%s" --wait %s --title "%s"' % (
        python or console_python(), Path(hub) / "tools" / "mail.py", addr, bash_dq(title))


def hold_body(hub, session, title, arcs, address, vendor="claude", cfg=None, python=None,
              usage=None, machine=""):
    """One row of the holds cache.  It carries the rendered command and the two
    switches the hook needs, because the hook's hot path reads no machine.json
    and no post-config.json — three stats and this one small file.  It
    also carries the waiting rule from usage-settings.json and the Desk's
    address, so the Stop hook can refuse a Fable window without a hub read."""
    cfg = cfg or dict(DEFAULTS)
    usage = usage or USAGE_DEFAULTS
    cmd = wait_command(hub, address, title, python)
    mch = str(machine or str(address or "").split("/")[0] or "").upper()
    body = {"session": str(session), "title": str(title or ""),
            "arcs": sorted(set(str(a) for a in (arcs or ()) if str(a).strip())),
            "address": str(address or ""), "vendor": str(vendor or ""),
            "updated": iso(now()), "arm": bool(cfg.get("arm_before_idle", True)),
            "again": float(cfg.get("arm_again_minutes", DEFAULTS["arm_again_minutes"])),
            "cmd": cmd,
            "refuse_models": list(usage.get("wait_refuse_models") or []),
            "ceiling_percent": float(usage.get("wait_context_ceiling_percent") or 0),
            "desk": "%s/%s" % (mch, DESK_LANE) if mch else ""}
    if usage.get("usage_pause"):       # the pass's reading of the meter, never the hook's
        body["usage_pause"] = usage["usage_pause"]
    if not cmd:                        # the row says why, in plain words
        body["why"] = ("the address %s carries a character a shell would read — no waiter "
                       "command was rendered" % (str(address or "") or "(none)"))
    return body


def hold_address(claim, ears, machine_name):
    """Where a waiter for this session listens: the address of its own freshest
    ear if it has one, else <MACHINE>/<arc, '/' written '-'> — and `hub` stays
    `hub`, which is per machine by phase A's own rule."""
    sid = str(claim.get("session") or "")
    best, best_when = "", None
    for ear in ears:
        if str(ear.get("session") or "") != sid or not ear.get("to"):
            continue
        when = parse_iso(ear.get("when"))
        if when is None:
            continue
        if best_when is None or when > best_when:
            best, best_when = str(ear["to"]), when
    if best:
        return best
    arc = str(claim.get("arc") or "hub").strip()
    mch = str(claim.get("machine") or machine_name or "").upper()
    if arc.lower() == "hub":
        return "%s/hub" % mch
    return "%s/%s" % (mch, arc.replace("/", "-"))


def holds_reconcile(post, hub, claims, ears, machine_name, cfg=None, dry=False, home=None):
    """claims.json IS THE TRUTH; the cache only spares the hook a parse, so it
    is corrected in BOTH directions every pass — a session that no longer holds
    anything loses its file, and one that holds something and has no file gets
    one.  With arm_before_idle off every file says so, and the hook stands down
    within a pass."""
    _heavy()
    cfg = cfg if cfg is not None else config(hub)
    want = {}
    for claim in claims:
        sid = str(claim.get("session") or "")
        if not sid or not safe_session_id(sid):
            continue
        if str(claim.get("machine") or "").lower() != str(machine_name).lower():
            continue
        row = want.setdefault(sid, {"arcs": [], "title": str(claim.get("title") or ""),
                                    "vendor": str(claim.get("vendor") or ""), "claim": claim})
        row["arcs"].append(str(claim.get("arc") or ""))
    folder = Path(post) / "holds"
    try:
        have = dict((f.stem, f) for f in sorted(folder.glob("*.json")))
    except OSError:
        have = {}
    changed = []
    usage, _missing = usage_settings(hub)                  # the user's rule, once a pass
    upause = usage_pause_facts(hub, post)                  # the meter, once a pass (+ pause state)
    logins = None
    if upause and upause.get("autos"):                     # a login-scoped pause: each row reads its own
        logins = WindowLogins(hub, app_store(home))
    for sid, row in want.items():
        urow = dict(usage)
        if upause:
            fact = pause_scope(upause, logins.of(sid)) if logins is not None else upause
            if fact:
                urow["usage_pause"] = fact
        body = hold_body(hub, sid, row["title"], row["arcs"],
                         hold_address(row["claim"], ears, machine_name),
                         vendor=row["vendor"] or "claude", cfg=cfg, usage=urow,
                         machine=machine_name)
        old = read_json(holds_path(post, sid), None)
        same = isinstance(old, dict) and \
            dict(old, updated="") == dict(body, updated="")
        if not same and not dry:
            write_json_atomic(holds_path(post, sid), body)
            changed.append(sid)
    for sid, f in have.items():
        if sid in want:
            continue
        if not dry:
            try:
                os.unlink(str(f))
            except OSError:
                pass
        changed.append(sid)
    return changed


def alive_mark(post, session):
    """(age in seconds, or None) of a waiter's own sign of life.  NEVER a pid
    probe: on Windows os.kill(pid, 0) terminates the process."""
    try:
        return time.time() - os.stat(str(Path(post) / "waiters" /
                                          ("%s.alive" % session))).st_mtime
    except OSError:
        return None


def has_waiter(post, session):
    age = alive_mark(post, session)
    return age is not None and age <= ALIVE_S


# --------------------------------------------------------------------------
# THE ATTENDED ROAD — push at once, or announce at once
# --------------------------------------------------------------------------

ANNOUNCE_ONE = "%s: 1 letter waiting — it shows at its next turn"
ANNOUNCE_MANY = "%s: %d letters waiting — they show at its next turn"
MARKS_FILE = "mail-marks-%s.json"
REMOTE_FILE = "remote-control.json"     # written by a session holding the app's session list
REMOTE_FRESH_S = 600


def app_store(home=None, at=None):
    """{"by_cli": {transcript stem: record}, "fronted": record or None, "read": why-not or ''}
    from the desktop app's own session store, through tools/app_sessions.py (beside this file,
    else the hub's tools/). A machine without the module or the app answers empty and says so."""
    _heavy()
    here = Path(__file__).resolve().parent
    mod = None
    for cand in (here / "app_sessions.py", here.parent / "tools" / "app_sessions.py"):
        if cand.is_file():
            try:
                spec = importlib.spec_from_file_location("pm_app_sessions", str(cand))
                mod = importlib.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception:
                mod = None
            break
    if mod is None:
        return {"by_cli": {}, "fronted": None, "read": "tools/app_sessions.py is not here"}
    try:
        recs = mod.records(str(home_dir(home)), max_age_days=2.0,
                           at=(at or now()).timestamp())
    except Exception as exc:
        return {"by_cli": {}, "fronted": None, "read": "the app's store did not read: %r" % exc}
    return {"by_cli": mod.by_cli(recs), "fronted": mod.fronted(recs),
            "read": "" if recs else "the app's session store holds no window here"}


def remote_hints(post, at):
    """{session ids} a session with the app's session list said Remote Control serves, from
    POST DIR's remote-control.json, when that file is younger than ten minutes. It is written by
    `--remote-hint` — without a fresh one the third test never fires, and nothing
    pretends it did."""
    d = read_json(Path(post) / REMOTE_FILE, None)
    if not isinstance(d, dict):
        return set()
    when = parse_iso(d.get("written"))
    if when is None or (at - when).total_seconds() > REMOTE_FRESH_S:
        return set()
    return set(str(x) for x in (d.get("sessions") or []) if x)


def write_remote_hint(post, ids, dry=False):
    """(exit code, [lines]) — `--remote-hint <id> [<id> …]`.

    POST DIR's remote-control.json, REPLACED whole: `written` now (this run's clock, so `--now`
    ages it) and `sessions` = exactly the ids given — a transcript's own id or the app's
    `local_…` id, the two forms attended_verdict() matches — and with no ids an empty list,
    which says that no window is served. Remote Control is a fact only the app's session list
    carries (`remoteControlActive`), so the SESSION that holds that list supplies the ids: the
    hub's and the Desk's wake, and each hygiene pass. An id that is not a plain token stops the
    whole write — nothing is guessed and nothing half-written."""
    _heavy()
    given = [str(i).strip() for i in (ids or [])]
    bad = [i for i in given if not safe_session_id(i)]
    if bad:
        return 2, ["remote-hint: %r is not a window's id (its transcript id or the app's local_ "
                   "id) — nothing written" % bad[0]]
    keep = []
    for sid in given:
        if sid not in keep:
            keep.append(sid)
    path = Path(post) / REMOTE_FILE
    body = {"written": iso(now()), "sessions": keep}
    if dry:
        return 0, ["remote-hint: would write %s — %d window(s) · dry run, nothing written"
                   % (path, len(keep))]
    write_json_atomic(path, body)
    if not keep:
        return 0, ["remote-hint: no window is served by Remote Control — written %s" % path]
    return 0, ["remote-hint: %d window(s) served by Remote Control (%s) — written %s, believed "
               "for %d min" % (len(keep), ", ".join(keep), path, REMOTE_FRESH_S // 60)]


def pause_meter(line):
    """The meter a PAUSE line names, in its own words: `USAGE PAUSE — all models 95 percent ·
    finish this step …` → `all models 95 percent`."""
    text = str(line or "").split(" · ")[0].strip()
    for head in ("USAGE PAUSE —", "USAGE PAUSE -", "USAGE PAUSE"):
        if text.startswith(head):
            text = text[len(head):].strip()
            break
    return text or "the meter"


def pause_holds(upause, session, roots, login=""):
    """The meter's own words when a usage PAUSE reaches this window's model, else ''.
    The Stop hook's own rule (_arm_tell) and usage.py's `applies`: an all-models PAUSE reaches
    every window, a model PAUSE the windows of that family, and a window whose model cannot be
    read is reached — it is never assumed to be the cheap one. A login-scoped auto record reaches
    only that login's windows (`login`; '' = unreadable = reached): pause_scope()."""
    upause = pause_scope(upause, login)
    if not isinstance(upause, dict) or not upause:
        return ""
    model = str(window_facts(transcript_of(session, "claude", roots)).get("model") or "").lower()
    if upause.get("all") or not model or any(f in model for f in (upause.get("families") or [])):
        return pause_meter(upause.get("line"))
    return ""


def window_name(title, session):
    """How the notice names a window: its lane when the title is a ritual one, else the
    title itself (the app's own words), else the session id's first eight characters."""
    t = str(title or "").strip()
    if "—" in t and ":" in t:
        lane = t.split("—", 1)[1].split(":", 1)[0].strip()
        if lane:
            return lane
    return (t[:48] + "…") if len(t) > 49 else (t or str(session)[:8])


def local_id_of(session, sessions, hub, app):
    """The app's own id for a window (`local_…`, the one its send-message tool takes): the
    app's store first, then the session map, then the stamps' host_session. '' when no byte
    names it — never guessed."""
    rec = (app.get("by_cli") or {}).get(session) or {}
    if rec.get("local_id"):
        return str(rec["local_id"])
    row = (sessions or {}).get(session) or {}
    if row.get("host_session"):
        return str(row["host_session"])
    try:
        for f in sorted(Path(hub).glob("live-*.json")):
            if f.name.startswith("live-sessions-"):
                continue
            d = read_json(f, None)
            for s in ((d or {}).get("sessions") or []) if isinstance(d, dict) else []:
                if isinstance(s, dict) and str(s.get("session") or "") == session \
                        and s.get("host_session"):
                    return str(s["host_session"])
    except OSError:
        pass
    return ""


def mark_facts(known, tokens, mail):
    """What the tree's ✉ says on hover beyond its count — the lane in plain words —
    and what the letters mean for the person (mail.py's `--for-the-user` lines) in `subject`, ""
    when none asks; the sender is never said (`from` stays as a key, empty)."""
    rows = [(parse_iso(known[t].get("first_seen")) or now(), t) for t in tokens if t in known]
    if not rows:
        return {}
    last = known[max(rows)[1]]               # the newest; a tie falls to the larger token
    said = user_words([known[t].get("line") or "" for _when, t in sorted(rows)], mail)
    return {"lane": lane_words(last.get("to") or "", mail), "from": "",
            "subject": " · ".join(said[:NUDGE_MAX_LINES])}


MESSAGE_TYPES = ("user", "assistant")     # a Claude transcript's own turns; all else is bookkeeping
LAST_MESSAGE_CAP = 65536                  # how far back from the end a bookkeeping tail is read


def last_message_age(session, roots, at, window_s):
    """ seconds since this window's last USER or ASSISTANT message, or None.

    A transcript's mtime moves for bookkeeping too — a retitle, the app's own records, a
    queued send — and a window that only had its title changed is not a window someone is
    looking at. So: when the transcript's LAST record is a message, its mtime is that
    message's time; when it is a bookkeeping record, the last message's own `timestamp`
    is read from a bounded tail. A Codex rollout keeps its mtime (it has no such records,
    and no send road). Read only for a transcript that moved inside `window_s` at all."""
    path = transcript_of(session, "claude", roots) or transcript_of(session, "", roots)
    if not path:
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    age = at.timestamp() - st.st_mtime
    if age > window_s or os.path.basename(str(path)).startswith("rollout-"):
        return age
    lo = max(0, st.st_size - LAST_MESSAGE_CAP)
    lines = read_region(path, lo, st.st_size).decode("utf-8", "replace").splitlines()
    if lo and lines:
        lines = lines[1:]                       # a torn first line
    last = True
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            if last:
                return age                      # a line mid-write: the window is writing
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("type") in MESSAGE_TYPES:
            if last:
                return age                      # the newest record IS a message
            when = parse_iso(rec.get("timestamp"))
            return (at - when).total_seconds() if when is not None else None
        last = False
    return None                                 # a tail of bookkeeping only: not attended


def attended_verdict(session, roots, post, hub, name, at, app, remote, cfg):
    """Is someone looking at this window?  Every test that said yes, by name, and whether the
    window is BUSY (its last message inside attend_busy_seconds: its own hook carries an
    asking letter within seconds).  The transcript test reads the last USER or ASSISTANT
    message, never a bookkeeping line ."""
    age = last_message_age(session, roots, at, live_minutes(hub, name) * 60)
    tests = []
    front = app.get("fronted") or {}
    if front and str(front.get("cli_id") or "") == str(session):
        tests.append("fronted")
    if age is not None and age <= live_minutes(hub, name) * 60:
        tests.append("transcript")
    rec = (app.get("by_cli") or {}).get(session) or {}
    if str(session) in remote or (rec.get("local_id") and str(rec["local_id"]) in remote):
        tests.append("remote")
    busy = age is not None and age <= float(cfg.get("attend_busy_seconds") or 60)
    return {"attended": bool(tests), "tests": tests, "busy": busy, "age": age,
            "scheduled": bool(rec.get("scheduled")), "app_title": str(rec.get("title") or "")}


NO_CARRIER_FLAGSHIP = "no carrier — every live window is on a flagship model"
NO_CARRIER_UNREAD = "no carrier — no live window's model can be read"


def carrier_refusal(session, roots, hub, cache=None):
    """'' when this window may carry a send order, else why not ('model' — it is
    on a model nothing may wait on, or 'blind' — its model cannot be read). The same reader
    and the same rule as the waiter's `a Fable window can hold no waiter`: the model its OWN
    transcript names (window_facts), judged by the user's own refuse list in
    usage-settings.json (wait_refuse_models — the registry names no flagship of its own), so
    a flagship window never spends a turn carrying another window's letter. A window whose
    model cannot be read is never assumed to be the cheap one."""
    sid = str(session or "")
    if cache is not None and sid in cache:
        return cache[sid]
    cfg, _missing = usage_settings(hub)
    facts = window_facts(transcript_of(sid, "claude", roots))
    verdict = window_verdict(facts, {"wait_refuse_models": cfg.get("wait_refuse_models") or [],
                                     "wait_context_ceiling_percent": 0})
    out = str(verdict.get("kind") or "blind") if verdict.get("refuse") else ""
    if cache is not None:
        cache[sid] = out
    return out


def send_carrier(post, roots, window, target, sender, sender_vendor, app, avoid=(), hub=None):
    """WHO makes the one send-message call, and why: the letter's own SENDER when it is a
    Claude session here (it is mid-turn — it just sent); else a window whose waiter is
    listening (the Desk: it carries the order at its next turn, on a cheap model — never
    woken for it); else the Claude window that wrote most recently.  Never the
    target, never a routine's run (the tool is not there), never a Codex thread (it has no
    such tool), and NEVER A FLAGSHIP WINDOW in any tier: when every candidate is
    one, there is no carrier and `how` says why (NO_CARRIER_FLAGSHIP)."""
    by_cli = app.get("by_cli") or {}
    block = set(str(a) for a in avoid if a) | {str(target)}
    hub = hub or (roots or {}).get("orchestrator") or ""
    refused, cache = [], {}

    def usable(sid):
        if not (sid and safe_session_id(sid) and sid not in block
                and not (by_cli.get(sid) or {}).get("scheduled")):
            return False
        why = carrier_refusal(sid, roots, hub, cache)
        if why:
            refused.append(why)
            return False
        return True
    if str(sender_vendor or "claude") == "claude" and usable(str(sender or "")):
        return str(sender), "the letter's own sender"
    try:
        alive = sorted(Path(post, "waiters").glob("*.alive"), key=lambda f: -f.stat().st_mtime)
    except OSError:
        alive = []
    for f in alive:
        sid = f.name[:-len(".alive")]
        if usable(sid) and has_waiter(post, sid):
            return sid, "a window whose waiter is listening"
    for sid, _mtime in claude_sessions_here(roots, window):
        if usable(sid):
            return sid, "the Claude window that wrote most recently"
    if refused:
        return "", (NO_CARRIER_FLAGSHIP if "model" in refused else NO_CARRIER_UNREAD)
    return "", ""


def attend_key(prefix, session, tokens):
    """`an-`/`sd-` + 12 hex over the window and its letters' tokens — NO CLOCK IN AN
    IDENTITY: a pass killed after the notice and before state.json cannot mint a second."""
    _heavy()
    key = "%s|%s|%s" % (prefix, session, ",".join(sorted(str(t) for t in tokens)))
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def attend(post, hub, state, known, cfg, mail, name, roots, sessions, opts, at):
    """One decision per window that holds waiting letters on this machine."""
    _heavy()
    said = []
    dry = bool(opts.get("dry"))
    sends = state.setdefault("sends", {})
    announced = state.setdefault("announced", {})
    # A SEND ORDER IS SPENT when its letters are read: it leaves the carrier's file, and a
    # letter the push delivered leaves the target's own pending file with it, so the
    # window's next turn does not print it twice.
    for key, rec in list(sends.items()):
        toks = [t for t in (rec.get("tokens") or [])]
        states = [(known.get(t) or {}).get("state") for t in toks]
        if toks and all(st in ("delivered", "expired", None) for st in states):
            if not dry and rec.get("carrier") and rec.get("state") != "spent":
                drop_from_pending(post, rec["carrier"], key, "send")
                for t in toks:
                    if (known.get(t) or {}).get("state") == "delivered":
                        drop_pending(post, t)
            rec["state"] = "spent"
    if not cfg.get("attend", True):
        return said
    # NOTHING OLDER THAN THIS ROAD IS PUSHED OR ANNOUNCED:
    # the first pass that runs it writes its own beginning and acts on nothing, so an install
    # never fires a banner per letter that waited all night. Those letters still wear their ✉
    # on the tree — the mark is the truth about what waits; the banner is only for news.
    begin = parse_iso(state.get("attend_from"))
    starting = begin is None
    if starting:
        if not dry:
            state["attend_from"] = iso(at)
        begin = at
    surfaces = parse_iso(state.get("surfaces_from"))
    if surfaces is not None and surfaces >= begin:
        begin = surfaces
    # A pass that BEGINS the road — or the surfaces' own bootstrap pass — acts on nothing.
    # Said by the state itself, never by comparing clocks: two passes inside one second
    # are ordinary in a gate and on a fast machine.
    starting = starting or bool(opts.get("fresh_surfaces"))
    by_session = {}
    for token in sorted(known):
        entry = known[token]
        if entry.get("state") != "waiting" or entry.get("state_kind") == "broadcast":
            continue
        holder = entry.get("holder") or {}
        sid = str(holder.get("session") or "")
        if not sid or str(holder.get("machine") or "").lower() != str(name).lower():
            continue
        if not safe_session_id(sid):
            continue
        by_session.setdefault(sid, []).append(token)
    app = app_store(opts.get("home"), at) if by_session else {"by_cli": {}, "fronted": None}
    remote = remote_hints(post, at) if by_session else set()
    upause = usage_pause_facts(hub, post) if by_session else None     # the meter, once a pass (+ pause state)
    logins = WindowLogins(hub, app) if (upause and upause.get("autos")) else None
    window = live_minutes(hub, name)
    installed = installed_here(post)
    marks = {}
    sent = state.get("sent") or {}
    for sid, every in sorted(by_session.items()):
        news = [] if starting else [t for t in every
                                    if (parse_iso(known[t].get("first_seen")) or begin) >= begin]
        v = attended_verdict(sid, roots, post, hub, name, at, app, remote, cfg)
        marks[sid] = {"count": len(every), "title": "", "attended": v["attended"],
                      "tests": v["tests"], "road": "", "why": "waited from before this road began"}
        marks[sid].update(mark_facts(known, every, mail))
        if not news:
            marks[sid]["title"] = session_title(sid, hub, post, sessions) or v["app_title"]
            continue
        tokens = news
        title = (session_title(sid, hub, post, sessions) or v["app_title"]
                 or str(((known[tokens[0]].get("holder") or {}).get("title")) or ""))
        vendor = str(((sessions or {}).get(sid) or {}).get("vendor") or "claude")
        road, why, held_by = "", "", ""
        quiet_ones = set(t for t in tokens if known[t].get("fyi") or known[t].get("quiet"))
        if v["attended"]:
            # AN FYI LETTER NEVER RIDES SEND_MESSAGE : only a
            # letter that wants an answer is pushed; a quiet one is queued for the window's
            # next turn, attended or not. A BUSY window's own hook carries what asks within
            # seconds, so a busy window is pushed nothing at all.
            asks = [t for t in tokens if t not in quiet_ones]
            # NO ORDER FOR A LETTER THE WINDOW HAS SEEN: one that is no longer
            # waiting, or that was already HANDED to this very window (a receipt: its waiter
            # or its hook carried it) is never pushed into it again.
            seen_here = [t for t in asks if known[t].get("state") != "waiting"
                         or already_carried(state, t, sid)]
            push = [] if v["busy"] else [t for t in asks if t not in seen_here]
            target = local_id_of(sid, sessions, hub, app) if vendor == "claude" else ""
            held = pause_holds(upause, sid, roots, logins.of(sid) if logins is not None else "") \
                if (push and target) else ""
            if not push and asks and not v["busy"]:
                road, why = "next turn", "already handed to this window — no push for a letter it has seen"
            elif not push and asks:
                road, why = "hook", "busy — its own hook carries it within seconds"
            elif not push:
                # nothing here asks: the FYI lines take the idle road — queued for the next
                # turn, ONE zero-token notice now, never a late banner when it goes quiet
                road, why = "announce", "an FYI letter is never pushed"
            elif not target:
                road, why = "announce", ("no send road — %s" % ("a %s thread has no send tool"
                                          % vendor if vendor != "claude" else
                                          "no byte names the app's own id for this window"))
            elif held:
                # ATTENDED DOES NOT MEAN AFFORDABLE: under a PAUSE that reaches this
                # window's model the push is held and the letter takes the idle road — queued for
                # its next turn, one notice, the ✉ mark. An order queued before the PAUSE began
                # that its carrier has not been handed yet is taken back; one already handed
                # cannot be, and the road says so rather than pretend.
                key = attend_key("sd", sid, push)
                rec = sends.get(key)
                handed = False
                if rec is not None and rec.get("state") == "queued" and rec.get("carrier"):
                    if dry or drop_from_pending(post, rec["carrier"], key, "send"):
                        if not dry:
                            rec.update({"state": "held", "held": held, "held_when": iso(at)})
                    else:
                        handed = True
                if handed:
                    road, why = "send", ("pushed through %s — ordered before the usage PAUSE"
                                         % (rec.get("carrier_how") or "a carrier"))
                else:
                    road, why, held_by = "announce", "held: usage PAUSE (%s)" % held, held
            else:
                key = attend_key("sd", sid, push)
                rec = sends.get(key)
                if rec is not None and rec.get("state") == "held":
                    sends.pop(key, None)          # the PAUSE has lifted: a fresh order, a fresh carrier
                    rec = None
                if rec is None:
                    src = {}
                    for t in push:
                        src = ((sent.get(t) or {}).get("from") or {})
                        if src.get("session"):
                            break
                    carrier, how = send_carrier(post, roots, window, sid,
                                                src.get("session"), src.get("vendor"), app,
                                                hub=hub)
                    rec = {"target": target, "session": sid, "title": title, "tokens": push,
                           "tests": v["tests"], "when": iso(at), "carrier": carrier,
                           "carrier_how": how, "state": "queued" if carrier else "no carrier"}
                    if carrier and not dry:
                        items = [{"token": t, "kind": "letter", "line": known[t].get("line") or "",
                                  "to": known[t].get("to") or "", "fyi": bool(known[t].get("fyi"))}
                                 for t in push]
                        # AN ORDER NEVER WAKES: `wake: false`, the grammar of every
                        # at-once notice — it rides a turn the carrier is taking
                        # anyway (its PostToolBatch, its next prompt), never its waiter.
                        queue_pending(post, carrier, [{
                            "token": key, "kind": "send", "fyi": False, "wake": False,
                            "target": target,
                            "title": title, "why": "+".join(v["tests"]),
                            "message": frame(items), "tokens": push, "queued": iso(at)}])
                    sends[key] = rec
                    if carrier:
                        said.append("POST — pushing %d letter(s) into «%s» (attended: %s) — "
                                    "carried by %s" % (len(push), title or sid, "+".join(v["tests"]),
                                                       session_title(carrier, hub, post, sessions)
                                                       or carrier))
                    elif how:
                        said.append("POST — «%s» is attended (%s), not pushed: %s — queued for "
                                    "its next turn" % (title or sid, "+".join(v["tests"]), how))
                if rec.get("carrier"):
                    road, why = "send", "pushed through %s" % (rec.get("carrier_how") or "a carrier")
                elif rec.get("carrier_how"):
                    road, why = "announce", rec["carrier_how"]
                else:
                    road, why = "announce", "no Claude window here to carry the push"
        if not v["attended"] or road == "announce":
            road = road or "announce"
            why = why or "idle — queued for its next turn"
            # the count is EVERY letter waiting there (the truth about the window); a notice
            # fires only when one of them is news, and once per set of letters
            key = attend_key("an", sid, every)
            if key not in announced:
                text = (ANNOUNCE_ONE % window_name(title, sid) if len(every) == 1
                        else ANNOUNCE_MANY % (window_name(title, sid), len(every)))
                cause = ""
                if not installed:
                    cause = NOT_INSTALLED
                elif not cfg.get("announce", True):
                    cause = "announcements are turned off here"
                elif opts.get("foreign_hub") and not opts.get("notify"):
                    cause = "this is not this machine's own hub — a rehearsal never raises"
                rec = {"session": sid, "count": len(every), "text": text, "when": iso(at),
                       "tokens": sorted(every)}
                if cause:
                    rec.update({"how": "none", "why": cause})
                elif not dry:
                    how, err = raise_note("Exocortex", "mail waiting", text,
                                          notify=opts.get("notify"))
                    rec.update({"how": how or "none", "why": err})
                if not dry:
                    announced[key] = rec
                    said.append("POST — %s" % text)
        for t in tokens:
            one_road, one_why = road, why
            if t in quiet_ones and road in ("send", "hook"):
                # the window's asks took a road; its FYI lines wait for its next turn
                one_road = "next turn"
                one_why = "FYI — it shows at its next turn; an FYI letter is never pushed"
            known[t]["attended"] = {"road": one_road, "why": one_why, "tests": v["tests"],
                                    "when": (known[t].get("attended") or {}).get("when") or iso(at)}
            if held_by:                           # the sender's road line names the meter
                known[t]["attended"]["held"] = held_by
        marks[sid] = {"count": len(every), "title": title, "attended": v["attended"],
                      "tests": v["tests"], "road": road, "why": why}
        marks[sid].update(mark_facts(known, every, mail))
    # prune: announcements and orders a week old are history, not memory
    for book in (announced, sends):
        for key in list(book):
            when = parse_iso((book[key] or {}).get("when"))
            if when is not None and (at - when).total_seconds() > 7 * 86400:
                book.pop(key, None)
    if not dry:
        write_marks(hub, name, marks, at)
    return said


# --------------------------------------------------------------------------
# THE DIAL ROAD — a plate is an order the attended window carries
# --------------------------------------------------------------------------
# A window ends its reply with a dial plate (⇩ NEXT STRETCH / ⇧ NEXT TURN, then STATION · MIND ·
# EFFORT). Within one pass the plate is judged by spool.py's five guards — the judge, and the
# only place the guards live — and a SET becomes ONE order that an attended Claude window other
# than the plated one carries with the app's own set-model / set-effort tools. Nothing wakes a
# window: the order rides the carrier's own hooks or its listening waiter; the plated window's
# `dial set:` line rides its own next turn start. A plate is handled once, by its reply's uuid.

DIAL_EXPIRE_S = 600            # an order no hand took in ten minutes is expired, and judged again
DIAL_APPLY_GRACE_S = 120       # after a hand took it, how long the app's store may take to show it
DIAL_ORDERS_MAX = 2            # one order per plate, and one more at most
DIAL_JUDGE_TIMEOUT_S = 45      # the judge is a child of the pass, and it is bounded
DIAL_JUDGE_BACKOFF_S = 600     # a judge that failed is not asked again for ten minutes
DIAL_KEEP_DAYS = 7             # a plate's record is history after a week, like a send order
DIAL_STALE_EVERY_S = 3600      # a plate kept for a stale meter is judged again at most once an hour
DIAL_FINAL = ("kept", "no-carrier", "applied", "no-id")
DIAL_OPEN = ("ordered", "carried")
_SIBLINGS = {}


def sibling_file(name):
    """A neighbour tool: beside this file (installed, or a gate world's copy), else the hub's
    tools/ above it. None when neither has it."""
    _heavy()
    here = Path(__file__).resolve().parent
    for cand in (here / name, here.parent / "tools" / name):
        if cand.is_file():
            return cand
    return None


def sibling_module(name, alias):
    """A neighbour imported once per process — None when it is not there or does not load."""
    _heavy()
    if name in _SIBLINGS:
        return _SIBLINGS[name]
    mod, cand = None, sibling_file(name)
    if cand is not None:
        try:
            spec = importlib.spec_from_file_location(alias, str(cand))
            mod = importlib.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception:
            mod = None
    _SIBLINGS[name] = mod
    return mod


def dial_key(prefix, *parts):
    """`dl-` / `ds-` + 12 hex over the plate and the attempt — no clock in an identity, so a pass
    killed between the queue and the state never mints a second order for one plate."""
    _heavy()
    key = "|".join([prefix] + [str(p) for p in parts])
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def has_arrow(text, eff):
    """Does a reply END with a plate — a `NEXT TURN|STRETCH` arrow in its last lines, outside
    fenced blocks and block quotes (effort.py's own reading of where a plate lives)? Whether the
    plate is READABLE is the judge's question, never this one's."""
    lines = str(text or "").splitlines()
    marked = eff._fence_and_quote(lines)
    arrow = re.compile(r"(?i)NEXT\s+(TURN|STRETCH)")
    for line, in_fence, in_quote in marked[max(0, len(lines) - int(eff.TAIL_LINES)):]:
        if not in_fence and not in_quote and arrow.search(line):
            return True
    return False


def is_act_title(title):
    """The ACT grammar's head — `ACT — …`. The lane inside it is the judge's to read."""
    _heavy()
    return bool(re.match(r"^\s*ACT\s*[—–-]", str(title or "")))


def dial_rows(hub, name, at):
    """The pulse's own rows for this machine — [] when its file is missing or older than three
    of its windows (it says nothing about now)."""
    d = read_json(Path(hub) / ("live-sessions-%s.json" % name), None)
    if not isinstance(d, dict):
        return []
    when = parse_iso(d.get("when"))
    if when is None or (at - when).total_seconds() > live_minutes(hub, name) * 60 * 3:
        return []
    return [s for s in (d.get("sessions") or []) if isinstance(s, dict)]


def meter_read_at(hub, name, login):
    """The `read_at` of the meter the judge reads — the login's newest on this machine, or the
    newest of any login here when none is known — '' when there is none (usage.py's own reader)."""
    u = sibling_module("usage.py", "pm_usage")
    if u is None:
        return ""
    try:
        if login:
            _path, data = u.newest_meter(str(hub), name, "claude", login)
        else:
            got = u.meters(str(hub), name, "claude")
            data = got[0][1] if got else None
    except Exception:
        return ""
    return str((data or {}).get("read_at") or "")


def stale_meter_plate(d):
    return d.get("state") == "kept" and str(d.get("why") or "").startswith("METER STALE")


def dial_again(prior, hub, name, at):
    """Is a handled plate judged again? An expired order's plate; and a plate kept only for a
    stale or missing meter once that
    meter's read_at has moved since the plate was judged — the first time at once, any later
    time at most once an hour. Every other record is final."""
    if prior.get("state") == "expired":
        return True
    if not stale_meter_plate(prior):
        return False
    last = parse_iso(prior.get("stale_rejudged"))
    if last is not None and (at - last).total_seconds() < DIAL_STALE_EVERY_S:
        return False
    return meter_read_at(hub, name, prior.get("meter_login") or "") \
        != str(prior.get("meter_read_at") or "")


def dial_candidates(hub, name, roots, state, dials, cfg, at, eff_of):
    """every live Claude window here whose title is in the ACT grammar, whose LAST reply
    ends with a plate whose uuid this machine has not handled (or whose order expired), and
    which is not busy. One stat per quiet window per pass: a transcript is re-read only when its
    (mtime, size) moved, and a window that is writing is not read at all — its plate waits."""
    seen = state.setdefault("dial_seen", {})
    busy_s = float(cfg.get("attend_busy_seconds") or 60)
    window_s = live_minutes(hub, name) * 60
    live, out = set(), []
    for s in dial_rows(hub, name, at):
        sid = str(s.get("id") or "")
        title = " ".join(str(s.get("title") or "").split())
        if str(s.get("kind") or "claude").lower() != "claude" or not safe_session_id(sid) \
                or not is_act_title(title):
            continue
        live.add(sid)
        path = str(s.get("transcript") or "") or transcript_of(sid, "claude", roots)
        try:
            st = os.stat(path)
        except (OSError, TypeError, ValueError):
            continue
        if at.timestamp() - st.st_mtime <= busy_s:
            continue                                  # writing now: its plate waits a pass
        key = [int(st.st_mtime_ns), int(st.st_size)]
        held = seen.get(sid)
        if isinstance(held, list) and len(held) == 4 and held[:2] == key:
            uuid, arrow = str(held[2] or ""), bool(held[3])
        else:
            eff = eff_of()                            # effort.py, imported only for a re-read
            if eff is None:
                continue
            tail = eff.tail_reply(path)
            _COUNTERS["dial_reads"] += 1
            uuid, arrow = str(tail.get("uuid") or ""), has_arrow(tail.get("text"), eff)
            seen[sid] = key + [uuid, arrow]
        if not arrow or not uuid:
            continue
        prior = dials.get(uuid)
        if prior and not dial_again(prior, hub, name, at):
            continue                                  # one plate, one judgment
        age = last_message_age(sid, roots, at, window_s)
        if age is None or age <= busy_s:
            continue                                  # its last message is too fresh: busy
        out.append({"sid": sid, "title": title, "uuid": uuid, "transcript": path})
    for sid in [k for k in seen if k not in live]:
        seen.pop(sid, None)                           # the cache follows the pulse's own rows
    return out


def carrier_login(hub, roots, carrier):
    """The login the carrier's window runs under (usage.py's own reading, its transcript first)
    — '' when nothing names it; the judge then reads its own."""
    if not carrier:
        return ""
    u = sibling_module("usage.py", "pm_usage")
    if u is None:
        return ""
    env = dict(os.environ)
    for k in ("CLAUDE_CODE_SESSION_ID", HOST_ENV):
        env.pop(k, None)                              # the pass is nobody's window
    try:
        login = u.session_login(roots, str(hub), session=carrier, fallback=True, env=env)[0]
    except Exception:
        return ""
    return "" if (not login or u.same_login(login, u.UNKNOWN_LOGIN)) else str(login)


def run_judge(hub, self_id, login):
    """spool.py --dials --json --plates-only, ONCE, as a child: ({id: object}, why-not).
    The child is nobody's window — the session ids are taken out of its environment — so its
    SELF guard is only ever what --self says."""
    spool = sibling_file("spool.py")
    if spool is None:
        return None, "spool.py is not beside the postman"
    argv = [sys.executable or "python3", str(spool), "--dials", "--json", "--plates-only",
            "--self", str(self_id or "")]
    if login:
        argv += ["--login", login]
    env = dict(os.environ)
    for k in ("CLAUDE_CODE_SESSION_ID", HOST_ENV):
        env.pop(k, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = CREATE_NO_WINDOW
    _COUNTERS["judge_runs"] += 1
    try:
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, cwd=str(hub), env=env,
                           timeout=DIAL_JUDGE_TIMEOUT_S, **kw)
    except subprocess.TimeoutExpired:
        return None, "the judge ran past %d s" % DIAL_JUDGE_TIMEOUT_S
    except Exception as exc:
        return None, "the judge did not start (%s)" % type(exc).__name__
    text = p.stdout.decode("utf-8", "replace").strip()
    try:
        got = json.loads(text) if text else None
    except ValueError:
        got = None
    if isinstance(got, dict) and got.get("stop"):
        return None, "the judge stopped — %s" % got["stop"]
    if not isinstance(got, list):
        err = " ".join(p.stderr.decode("utf-8", "replace").split())[:160]
        return None, "the judge printed no verdicts (exit %d%s)" % (p.returncode,
                                                                   (": " + err) if err else "")
    return dict((str(o.get("id") or ""), o) for o in got if isinstance(o, dict)), ""


def store_dial(rec):
    """(model, effort) the app's own store shows for a window — the effort read from the record
    file itself, '' when the store does not carry it."""
    model = str((rec or {}).get("model") or "")
    effort = ""
    path = (rec or {}).get("file")
    if path:
        d = read_json(path, None)
        if isinstance(d, dict):
            effort = str(d.get("effort") or "")
    return model, effort


def hand_set_it(roots, hand, local, since):
    """Did the hand make the app's set call for this window? Its own transcript's tail: an
    assistant record at or after `since` carrying a set_session_model / set_session_effort
    tool call whose session_id is the window's app id. Read only to tell a hand that did
    nothing (re-order) from a set the window's own menu then changed (it stands)."""
    path = transcript_of(hand, "claude", roots) if hand else ""
    if not path or not local:
        return False
    try:
        size = os.path.getsize(path)
    except OSError:
        return False
    data = read_region(path, max(0, size - 262144), size).decode("utf-8", "replace")
    for line in data.splitlines():
        if local not in line or "set_session_" not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("type") != "assistant":
            continue
        when = parse_iso(rec.get("timestamp"))
        if since is not None and when is not None and when < since:
            continue
        for b in (rec.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use" \
                    and str(b.get("name") or "").endswith(("set_session_model",
                                                            "set_session_effort")) \
                    and str((b.get("input") or {}).get("session_id") or "") == local:
                return True
    return False


def dial_said(post, dials, d, at, dry):
    """the line the plated window opens with, queued for ITS OWN next turn start (fyi, never
    a wake). A line still waiting from an older plate of the same window is taken back first."""
    said = DIAL_SAID_LINE % (d.get("mind") or "", d.get("effort") or "",
                             d.get("clause") or "your plate")
    token = dial_key("ds", d.get("uuid") or "")
    if dry:
        return token
    for other in dials.values():
        if other is not d and other.get("session") == d.get("session") \
                and other.get("said_token") and not other.get("said"):
            drop_from_pending(post, d["session"], other["said_token"], "dial-said")
    queue_pending(post, d["session"], [{"token": token, "kind": "dial-said", "fyi": True,
                                        "wake": False, "text": said,
                                        "plate_uuid": d.get("uuid") or "", "queued": iso(at)}])
    return token


def dial_observe(post, hub, state, dials, app_of, at, dry, sessions, roots):
    """an order whose receipt landed and whose window's store now shows the dial is APPLIED,
    and the plated window gets its `dial set:` line; an order no hand took in ten minutes, or one
    taken whose dial the store still does not show two minutes later, is EXPIRED and judged again
    — one more order at most, then the no-carrier grammar, said once."""
    said = []
    by_token = state.get("receipts") or {}
    for uuid, d in sorted(dials.items()):
        if d.get("state") == "applied" and d.get("said_token") and not d.get("said"):
            rec = by_token.get(d["said_token"])
            if rec:
                d["said"] = rec.get("when") or iso(at)        # the window saw its line
            continue
        if d.get("state") not in DIAL_OPEN:
            continue
        rec = by_token.get(str(d.get("token") or ""))
        if rec and d.get("state") == "ordered":
            d["state"] = "carried"
            d["carried"] = rec.get("when") or iso(at)
            d["carried_by"] = rec.get("session") or ""
        model, effort = store_dial(app_of().get(d.get("session")))
        if d.get("state") == "carried" and model == d.get("model_id") \
                and (not effort or not d.get("effort_value") or effort == d.get("effort_value")):
            d["state"], d["applied"] = "applied", iso(at)
            hand = d.get("carried_by") or d.get("carrier") or ""
            d["why"] = "set by «%s»" % (session_title(hand, hub, post, sessions)
                                        or (d.get("carrier_title") if hand == d.get("carrier")
                                            else "") or hand or "a carrier")
            d["said_token"] = dial_said(post, dials, d, at, dry)
            said.append("dial: «%s» set to %s · %s — %s" % (d.get("title"), d.get("mind"),
                                                            d.get("effort"), d["why"]))
            continue
        since = parse_iso(d.get("carried") if d.get("state") == "carried" else d.get("ordered"))
        limit = DIAL_APPLY_GRACE_S if d.get("state") == "carried" else DIAL_EXPIRE_S
        if since is None or (at - since).total_seconds() <= limit:
            continue
        if not dry and d.get("carrier"):
            drop_from_pending(post, d["carrier"], d.get("token"), "dial")   # never taken: back
        if d.get("state") == "ordered" and model == d.get("model_id") \
                and (not effort or not d.get("effort_value") or effort == d.get("effort_value")):
            # nobody carried it, and the window shows the asked dial anyway: its own menu set it
            d["state"], d["why"] = "kept", "the window already shows it — its own menu set it"
            continue
        if d.get("state") == "carried" and hand_set_it(roots, d.get("carried_by") or
                                                       d.get("carrier"), d.get("local_id"),
                                                       parse_iso(d.get("ordered"))):
            # THE USER'S MENU STANDS: the hand made the call and the app now shows another
            # dial — the window's own menu changed it after. Never ordered again.
            d["state"] = "kept"
            d["why"] = ("the hand set it; the app now shows %s%s — the window's own menu stands"
                        % (model or "another model", (" · " + effort) if effort else ""))
            said.append("dial: «%s» — %s" % (d.get("title"), d["why"]))
            continue
        late = ("carried, but the app still shows %s" % (model or "another model")
                if d.get("state") == "carried" else
                "no hand took the order in %d min" % (DIAL_EXPIRE_S // 60))
        if int(d.get("orders") or 0) >= DIAL_ORDERS_MAX:
            d["state"], d["why"] = "no-carrier", late + " — twice"
            said.append(DIAL_NO_CARRIER % (d.get("title"), d.get("mind"), d.get("effort")))
        else:
            d["state"], d["why"] = "expired", late + " — judged again"
    return said


DIAL_NO_CARRIER = "dial: «%s» asks %s · %s — no window to carry it"


def dial_road(post, hub, state, cfg, name, roots, sessions, opts, at):
    """ the pass's hand for the dial plate. Free: no model, no network; one judge child
    only when a plate waits; nothing written when nothing waits but state.json, which the pass
    writes every time anyway."""
    said = []
    dry = bool(opts.get("dry"))
    dials = state.setdefault("dials", {})
    for uuid in list(dials):                          # a week old: history, not memory
        when = parse_iso((dials[uuid] or {}).get("when"))
        if when is not None and (at - when).total_seconds() > DIAL_KEEP_DAYS * 86400:
            d = dials.pop(uuid)
            if not dry and d.get("said_token") and not d.get("said"):
                drop_from_pending(post, d.get("session") or "", d["said_token"], "dial-said")
    if not installed_here(post):
        return said                                   # no hook here can carry an order
    held = {}

    def app_of():
        if "app" not in held:
            held["app"] = app_store(opts.get("home"), at)
        return held["app"].get("by_cli") or {}

    if any(d.get("state") in DIAL_OPEN or (d.get("said_token") and not d.get("said"))
           for d in dials.values()):
        said.extend(dial_observe(post, hub, state, dials, app_of, at, dry, sessions, roots))
    cands = dial_candidates(hub, name, roots, state, dials, cfg, at,
                            lambda: sibling_module("effort.py", "pm_effort"))
    cands = [c for c in cands if not (app_of().get(c["sid"]) or {}).get("scheduled")]
    if not cands:
        return said                                   # no plate waits: no child
    judge = state.setdefault("dial_judge", {})
    failed = parse_iso(judge.get("failed"))
    if failed is not None and (at - failed).total_seconds() < DIAL_JUDGE_BACKOFF_S:
        return said
    app = held["app"]
    window = live_minutes(hub, name)
    ids = set(c["sid"] for c in cands)
    primary, _how = send_carrier(post, roots, window, "", "", "", app)
    # --self is the pass's own hand when that hand printed no plate; when it did, nobody is
    # SELF to the judge — each plate's carrier is chosen below with its window excluded.
    self_id = primary if primary and primary not in ids else ""
    login = carrier_login(hub, roots, primary)
    verdicts, why_not = run_judge(hub, self_id, login)
    if verdicts is None:
        if judge.get("why") != why_not:
            said.append("dial: %d plate(s) wait — %s; judged again in %d min"
                        % (len(cands), why_not, DIAL_JUDGE_BACKOFF_S // 60))
        judge.update({"failed": iso(at), "why": why_not})
        return said
    state.pop("dial_judge", None)
    titles = dict((str(r.get("id") or ""), " ".join(str(r.get("title") or "").split()))
                  for r in dial_rows(hub, name, at))

    def hand_name(sid):                               # how a pass line names the hand
        return (session_title(sid, hub, post, sessions) or titles.get(sid)
                or str(((app.get("by_cli") or {}).get(sid) or {}).get("title") or "") or sid)
    for c in cands:
        o = verdicts.get(c["sid"]) or {}
        if str(o.get("plate_uuid") or "") != c["uuid"]:
            continue                                  # the reply moved on: judged next pass
        why = str(o.get("why") or "")
        if o.get("verdict") == "KEEP" and why.startswith("MID-TURN"):
            continue                                  # transient: the next pass judges it
        prior = dials.get(c["uuid"]) or {}
        plate = o.get("plate") or {}
        d = {"uuid": c["uuid"], "session": c["sid"], "title": c["title"],
             "when": prior.get("when") or iso(at), "verdict": o.get("verdict") or "KEEP",
             "mind": plate.get("mind") or o.get("mind") or "",
             "effort": plate.get("effort_word") or o.get("effort_word") or "",
             "clause": plate.get("clause") or "", "why": why,
             "orders": int(prior.get("orders") or 0), "carriers": list(prior.get("carriers") or [])}
        dials[c["uuid"]] = d
        ask = "%s · %s" % (d["mind"] or "?", d["effort"] or "?")
        if o.get("verdict") != "SET":
            d["state"] = "kept"
            d["why"] = why or "already the window's dial"
            if why.startswith("METER STALE"):
                # TRANSIENT (Q4): kept until the meter's read_at moves; a DOWN never comes here
                d["meter_login"], d["meter_read_at"] = login, meter_read_at(hub, name, login)
                if stale_meter_plate(prior):
                    d["stale_rejudged"] = iso(at)     # judged again, still stale: said once
                    continue
            if why.startswith("PLATE UNREADABLE"):
                said.append("dial: «%s» — %s; nothing applied" % (c["title"], why))
            elif why:
                said.append("dial: «%s» asks %s — kept: %s; the plate stands as the question"
                            % (c["title"], ask, why))
            continue
        d.update({"model_id": str(o.get("model_id") or ""),
                  "effort_value": str(o.get("effort") or ""), "mind": o.get("mind") or d["mind"],
                  "effort": o.get("effort_word") or d["effort"]})
        ask = "%s · %s" % (d["mind"], d["effort"])
        local = str(o.get("local_id") or "") or local_id_of(c["sid"], sessions, hub, app)
        if not local:
            d["state"], d["why"] = "no-id", "no byte names the app's own id for this window"
            said.append("dial: «%s» asks %s — %s; nothing applied" % (c["title"], ask, d["why"]))
            continue
        if not d["model_id"]:
            d["state"] = "kept"
            d["why"] = "no app id for %s — the registry names none and the record shows none" \
                % d["mind"]
            said.append("dial: «%s» asks %s — kept: %s" % (c["title"], ask, d["why"]))
            continue
        d["local_id"] = local
        carrier, how = send_carrier(post, roots, window, c["sid"], "", "", app,
                                    avoid=d["carriers"])
        if not carrier and d["carriers"]:             # another hand first; else the same again
            carrier, how = send_carrier(post, roots, window, c["sid"], "", "", app)
        if not carrier or carrier == c["sid"]:
            d["state"], d["why"] = "no-carrier", "no attended Claude window but this one"
            said.append(DIAL_NO_CARRIER % (c["title"], d["mind"], d["effort"]))
            continue
        d["orders"] += 1
        d["carriers"].append(carrier)
        token = dial_key("dl", c["uuid"], d["orders"])
        item = {"token": token, "kind": "dial", "fyi": False, "target": local, "cli": c["sid"],
                "title": c["title"], "mind": d["mind"], "effort_word": d["effort"],
                "effort": d["effort_value"], "model_id": d["model_id"],
                "why": d["clause"] or "its plate gives no reason", "plate_uuid": c["uuid"],
                "queued": iso(at)}
        item["message"] = dial_frame(item)
        if not dry:
            queue_pending(post, carrier, [item])
        d.update({"state": "ordered", "token": token, "carrier": carrier, "carrier_how": how,
                  "carrier_title": hand_name(carrier), "ordered": iso(at)})
        said.append("dial: «%s» → %s — ordered through «%s» (%s)"
                    % (c["title"], ask, hand_name(carrier), how))
    return said


def dial_rows_for_post(state):
    """post-<machine>.json `dials`: one row per plate, in the record's shape — nothing that moves
    on its own, so a quiet hour makes no brain commit."""
    out = {}
    for uuid, d in sorted((state.get("dials") or {}).items()):
        out[uuid] = {"session": d.get("session") or "", "title": d.get("title") or "",
                     "verdict": d.get("verdict") or "", "mind": d.get("mind") or "",
                     "effort": d.get("effort") or "", "carrier": d.get("carrier") or "",
                     "state": d.get("state") or "", "when": d.get("when") or "",
                     "why": d.get("why") or ""}
    return out


def write_marks(hub, name, marks, at):
    """mail-marks-<machine>.json in the hub: {session: {count, title, attended, road}} —
    rewritten ONLY when the marks change, so a quiet hour makes no brain commit. Removed
    when nothing waits, so the LIVE line loses its ✉ the pass after the letter is read."""
    path = Path(hub) / (MARKS_FILE % name)
    old = read_json(path, None)
    if not marks:
        if old is not None:
            try:
                path.unlink()
            except OSError:
                pass
        return
    if isinstance(old, dict) and old.get("sessions") == marks:
        return
    write_json_atomic(path, {"machine": str(name), "written": iso(at), "sessions": marks},
                      mode=BRAIN_FILE)


# --------------------------------------------------------------------------
# THE CARRIER — which live session is asked to make the one push call
# --------------------------------------------------------------------------

def claude_sessions_here(roots, window_minutes):
    """[(session id, mtime)] for every CLAUDE transcript on this machine touched
    inside the pulse's own window, newest first.  Never a Codex rollout: Codex
    has no push tool."""
    out = []
    for path, mtime, vendor in transcript_files(roots, minutes=window_minutes):
        if vendor != "claude":
            continue
        sid = Path(path).stem
        if safe_session_id(sid):
            out.append((sid, mtime))
    return out


def pick_carrier(note, roots, window_minutes, avoid=(), tried=()):
    """WHO makes the call, in order: the note's own SENDER when it is a
    bound Claude session here — it is mid-turn, or phase A's notice is about to
    wake it, and the push rides that turn — else the Claude session on this
    machine whose transcript was written most recently inside the pulse's
    window; else nobody.  Never a Codex session, and never the idle holder a
    nudge is about."""
    block = set(str(a) for a in avoid if a) | set(str(t) for t in tried if t)
    sender = str(note.get("sender") or "")
    if sender and safe_session_id(sender) and sender not in block \
            and str(note.get("sender_vendor") or "claude") == "claude":
        return sender
    for sid, _mtime in claude_sessions_here(roots, window_minutes):
        if sid in block:
            continue
        return sid
    return ""


def transcript_mtime(session, roots, known=""):
    """When a session last WROTE — the only honest sign that it has taken a turn,
    and never a pid probe."""
    path = transcript_of(session, "claude", roots, known) or \
        transcript_of(session, "", roots, known)
    if not path:
        return None
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


def observe_push(post, state, roots, sessions, at=None):
    """OBSERVED, never assumed.  `asked` when the frame's own token is in the
    carrier's transcript; `called` when a PushNotification tool call whose
    message begins with the push text's first 60 characters follows it; and the
    `result` is the tool result's OWN WORDS, recorded as they speak and never
    interpreted — the tool's "not sent" means the person was at the desk, which is not
    a failure."""
    _heavy()
    at = at or now()
    owners = owner_block(state)
    wanted = {}
    for token, rec in owners.items():
        push = rec.get("push") or {}
        sid = str(push.get("session") or "")
        if sid and push.get("state") in ("queued", "asked"):
            wanted.setdefault(sid, []).append((token, rec, push))
    if not wanted:
        return
    offsets = state.setdefault("push_offsets", {})
    for sid, rows in wanted.items():
        row = sessions.get(sid) or {}
        path = transcript_of(sid, row.get("vendor") or "claude", roots, row.get("transcript") or "")
        if not path:
            continue
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        lo = int(offsets.get(sid) or 0)
        if size < lo:
            lo = 0
        data = read_region(path, max(0, lo - 65536), size)
        offsets[sid] = size
        if not data:
            continue
        text = data.decode("utf-8", "replace")
        calls, results = push_calls(text)
        for token, rec, push in rows:
            if token in text and push.get("state") == "queued":
                push["state"] = "asked"
                push["asked_when"] = iso(at)
            head = str(rec.get("push_text") or "")[:PUSH_MATCH_CHARS]
            if not head:
                continue
            for use_id, message in calls:
                if not message.startswith(head):
                    continue
                push["state"] = "called"
                push["when"] = push.get("when") or iso(at)
                push["called_when"] = iso(at)
                push["result"] = str(results.get(use_id) or "")[:120]
                break


def push_calls(text):
    """([(tool_use id, the message it carried)], {tool_use id: the result's own
    words}) from a bounded slice of a Claude transcript, read in the shape the
    real one leaves: an assistant record whose message.content holds a
    `{"type": "tool_use", "name": "PushNotification", "input": {...}}`, and a
    user record whose content holds the matching `tool_result`."""
    calls, results = [], {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{") or "PushNotification" not in line and "tool_result" not in line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        content = ((d.get("message") or {}) if isinstance(d.get("message"), dict) else {}).get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and part.get("name") == "PushNotification":
                message = str(((part.get("input") or {}) or {}).get("message") or "")
                calls.append((str(part.get("id") or ""), message))
            elif part.get("type") == "tool_result":
                body = part.get("content")
                if isinstance(body, list):
                    body = " ".join(str((b or {}).get("text") or "") for b in body
                                    if isinstance(b, dict))
                results[str(part.get("tool_use_id") or "")] = str(body or "").strip()
    return calls, results


# --------------------------------------------------------------------------
# THE NUDGE — the human as the road of last resort, one move
# --------------------------------------------------------------------------

# Mail between sessions is the machine's: the person hears ONE plain sentence of what a
# letter means for them, or NOTHING — never that one exists, never a sender, a count, or
# which word to say.  The sentence is mail.py's own `--read <lane> --for-the-user` (asks_the_user +
# user_line, called on the nudged letters); a lane whose letters ask the person nothing earns no
# notice, no POST order and no push.  The notice is `<what it means> — <where>`, `where` being
# the window's title (the nudge's own shape) or `<LANE>: no window open`.
NUDGE_MAX_LINES = 3


def cut_words(text, limit):
    """The text on one line, cut at a word boundary with an ellipsis once past `limit`."""
    flat = " ".join(str(text or "").split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,;:.—-") + "…"


def lane_words(address, mail):
    """An address's lane in plain words, upper-case: `NORTH/hub` -> `HUB`, `NORTH/ALPHA-Door` -> `ALPHA/DOOR`
    (mail.addr_key makes `-` and `/` one separator, the spelling the registry knows)."""
    key = mail.addr_key(address)
    return (key.split("/", 1)[1] if "/" in key else key).upper()


def user_words(lines, mail):
    """What `mail.py --read <lane> --for-the-user` prints for these letter lines: one consequence
    line per letter that asks the person something, none for the rest, a repeat said once.  The
    same two functions the verb uses; an older mail.py without them says nothing (silence is the
    law's default)."""
    asks, say = getattr(mail, "asks_the_user", None), getattr(mail, "user_line", None)
    out = []
    if asks is None or say is None:
        return out
    for line in lines:
        if asks(line):
            one = say(line)
            if one and one not in out:
                out.append(one)
    return out


def nudge_text(row, mail, local_id="", link=True, cap=0):
    """ONE notice, or "" when the row's letters ask the person nothing.  `row` is the compose
    pass's row: address, holder, lines (the nudged letters' (first_seen, line), newest last).
    `<the consequence line(s), joined by « · »> — <where>`: where is the window's title — a chat
    link `[title](#local_id)` when `link` and an id is known, else the title in «» (a banner or a
    phone does not render links) — or `<LANE>: no window open`.  `cap` (a phone's one line): the
    consequence gives way first, down to 20 characters, so the window stays whole."""
    said = " · ".join(user_words([ln for _when, ln in row.get("lines") or []], mail)[:NUDGE_MAX_LINES])
    if not said:
        return ""
    holder = row.get("holder") or {}
    if holder.get("session") or holder.get("title"):
        title = str(holder.get("title") or "").replace("[", "(").replace("]", ")").strip()
        lid = str(local_id or "")
        if lid and not lid.startswith("local_"):
            lid = "local_" + lid
        if link and lid and title:
            where = "[%s](#%s)" % (title, lid)
        else:
            where = "«%s»" % (title or "its window")
    else:
        where = "%s: no window open" % lane_words(row["address"], mail)
    out = "%s — %s" % (said, where)
    if cap and len(out) > cap and len(said) > 20:
        said = cut_words(said, max(20, len(said) - (len(out) - cap)))
        out = "%s — %s" % (said, where)
    return out


def window_link_id(sid, hub, post, sessions, home):
    """The app's own id for a holder's window: local_id_of's roads (the app's store, the session
    map, the stamps), then the claim row's own `host_session`. '' when no byte names it."""
    if not sid:
        return ""
    got = ""
    try:
        got = local_id_of(sid, sessions if sessions is not None else session_map(post), hub,
                          app_store(home))
    except Exception:
        got = ""
    if not got:
        for claim in read_claims(hub):
            if str(claim.get("session") or "") == sid and claim.get("host_session"):
                return str(claim["host_session"])
    return got


def nudge_token(address, letters=()):
    """`nd-` + the first 12 hex of sha256("nudge|<addr key>|<the nudged letters'
    tokens, sorted, joined with ','>").

    NO IDENTITY CONTAINS A CLOCK.
    The old form hashed the pass's own `--now`, so a pass that died after
    composing a nudge and before writing `state.json` minted a SECOND token for
    the same letters at the next pass — and the same note would have been raised
    twice.  The 30-minute rule is untouched: it reads `first_seen`."""
    _heavy()
    key = "nudge|%s|%s" % (address, ",".join(sorted(str(t) for t in (letters or ()))))
    return "nd-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def compose_nudges(post, hub, state, known, cfg, mail, name, roots, at, sent,
                   sessions=None, home=None):
    """ONE nudge per letter that no road can carry, at the same moment phase A
    tells the SENDER `not read yet`, so the sender and the owner hear one fact at one
    time.  At most one per ADDRESS per nudge_again_minutes: several letters make
    one note, with the count in it."""
    _heavy()
    nudges = state.setdefault("nudges", {})
    surfaces = parse_iso(state.get("surfaces_from"))
    # NOTHING IS COMPOSED BEFORE THE SURFACES HAVE A BEGINNING.
    # The mark is written by `bootstrap_surfaces()` at the top of the
    # pass's step 7b, so `surfaces is None` can no longer happen — and the code
    # says so rather than trusting the order to stay as it is.  A nudge's own
    # `first_seen` must be strictly AFTER the mark, which is why the bootstrap
    # pass itself composes nothing at all: only letters first seen after the
    # mark may be nudged, and at that pass not one of them is.
    if surfaces is None or at <= surfaces:
        return []
    # AND NOTHING AT ALL ON A MACHINE NOBODY INSTALLED.
    if not installed_here(post):
        return []
    every = float(cfg["nudge_again_minutes"])
    wait_for = float(cfg["nudge_minutes"])
    last = {}
    for rec in nudges.values():
        when = parse_iso(rec.get("first_seen"))
        key = str(rec.get("addr_key") or "")
        if when is not None and (key not in last or when > last[key]):
            last[key] = when
    by_address = {}
    for token in sorted(known):
        entry = known[token]
        if entry.get("state") != "waiting" or entry.get("fyi") or item_is_quiet(entry):
            continue                          # a letter that asks nothing is never a nudge
        if (entry.get("state_kind") in ("ambiguous", "no_machine")
                or state_is_for_owner(entry.get("state_kind"))):
            continue                          # the sender was told at once and fixes it
        if entry.get("state_kind") == "broadcast" or entry.get("parent"):
            continue                          # each lane reads its copy at its next turn
        if entry.get("nudged"):
            continue
        first = parse_iso(entry.get("first_seen"))
        if first is None or (surfaces is not None and first < surfaces):
            continue                          # nothing older than this build is nudged
        holder = entry.get("holder") or {}
        hm = str(holder.get("machine") or "").lower()
        address = entry.get("to") or ""
        if holder:
            if hm != str(name).lower():
                continue                      # the holder's own machine nudges, not this one
        elif machine_of(address, mail) != str(name).lower():
            continue
        waited = (at - first).total_seconds() / 60.0
        if waited < wait_for:
            continue
        if entry.get("delivered"):
            continue
        sid = str(holder.get("session") or "")
        if sid:
            if has_waiter(post, sid):
                continue                      # its own waiter will carry it
            mtime = transcript_mtime(sid, roots)
            queued = parse_iso(entry.get("queued") or entry.get("first_seen"))
            if mtime is not None and queued is not None \
                    and mtime > queued.timestamp() + QUEUE_GRACE_S:
                continue                      # it has taken a turn: its hook carries it
        key = mail.addr_key(address)
        row = by_address.setdefault(key, {"address": address, "n": 0, "waited": 0.0,
                                          "holder": holder, "tokens": [], "lines": []})
        row["n"] += 1
        row["waited"] = max(row["waited"], waited)
        row["tokens"].append(token)
        row["lines"].append((first, entry.get("line") or ""))   # the newest gives the subject
    made = []
    for key, row in sorted(by_address.items()):
        when = last.get(key)
        if when is not None and (at - when).total_seconds() / 60.0 < every:
            continue
        holder = row["holder"] or {}
        title = str(holder.get("title") or "")
        row["lines"].sort(key=lambda r: (r[0], r[1]))
        case = "N1" if (holder.get("session") or title) else "N2"
        lid = window_link_id(str(holder.get("session") or ""), hub, post, sessions, home) \
            if case == "N1" else ""
        # `text` is what the banner, the tree and --status say (a banner renders no link); a
        # window that is not the holder reads `hook_text`, with the link.  NOTHING to say, no nudge.
        text = nudge_text(row, mail, lid, link=False)
        if not text:
            continue                  # the letters ask the person nothing; silence
        token = nudge_token(key, row["tokens"])
        sender, vendor = "", ""
        for t in row["tokens"]:
            src = ((sent.get(t) or {}).get("from") or {})
            if src.get("session"):
                sender, vendor = str(src["session"]), str(src.get("vendor") or "")
                break
        nudges[token] = {"token": token, "kind": "nudge", "addr_key": key,
                         "to": row["address"], "text": text, "case": case,
                         "count": row["n"], "first_seen": iso(at), "machine": str(name),
                         "letters": row["tokens"], "sender": sender,
                         "sender_vendor": vendor, "avoid": str(holder.get("session") or ""),
                         "hook_text": nudge_text(row, mail, lid, link=True),
                         "phone_text": nudge_text(row, mail, lid, link=False, cap=PUSH_TEXT_MAX)}
        for t in row["tokens"]:
            known[t]["nudged"] = {"when": iso(at), "machine": str(name), "case": case}
        made.append(token)
    return made


# --------------------------------------------------------------------------
# A NOTE FOR OWNER — its life
# --------------------------------------------------------------------------

def notes_for_owner(state, known, mail, name):
    """Every live note this machine has a view of: the `to: OWNER` letters and
    the nudges this machine composed, each with the ONE push text both the raise
    and the push carry."""
    out = []
    sent = state.get("sent") or {}
    for token in sorted(known):
        entry = known[token]
        if not state_is_for_owner(entry.get("state_kind")) or entry.get("state") == "expired":
            continue
        line = entry.get("line") or ""
        f = mail.fields(line)
        target = f[2] if len(f) >= 3 else "Exocortex"
        text = " · ".join(f[3:-1]) if len(f) >= 5 else (f[-1] if f else line)
        action = f[-1] if len(f) >= 5 else ""
        src = (sent.get(token) or {}).get("from") or {}
        out.append({"token": token, "kind": "letter", "to": entry.get("to") or "OWNER",
                    "line": line, "target": target, "fyi": bool(entry.get("fyi")),
                    "first_seen": entry.get("first_seen") or "",
                    "push_text": push_text(target, text, action),
                    "sender": str(src.get("session") or ""),
                    "sender_vendor": str(src.get("vendor") or ""),
                    "sender_when": (sent.get(token) or {}).get("when") or "",
                    "avoid": ""})
    for token, rec in sorted((state.get("nudges") or {}).items()):
        out.append({"token": token, "kind": "nudge", "to": rec.get("to") or "",
                    "line": rec.get("text") or "", "target": "", "fyi": False,
                    "first_seen": rec.get("first_seen") or "",
                    "push_text": push_text("", rec.get("phone_text") or rec.get("text") or "")[:PUSH_TEXT_MAX],
                    "says": str(rec.get("hook_text") or ""),
                    "sender": str(rec.get("sender") or ""),
                    "sender_vendor": str(rec.get("sender_vendor") or ""),
                    "sender_when": rec.get("first_seen") or "",
                    "avoid": str(rec.get("avoid") or ""), "case": rec.get("case") or ""})
    return out


def owner_surfaces(post, hub, state, known, cfg, mail, name, posts, roots, sessions, opts, at):
    """THE NOTE'S LIFE: raise it here once, ask ONE live session to push it, and
    tell its sender what happened — each step recorded as an event that never
    moves again, so the brain does not churn.

    BOOTSTRAP: `surfaces_from` is the moment of this build's first pass on
    this machine, written once — by `bootstrap_surfaces()`, at the TOP of the
    pass's step 7b and before `compose_nudges()`.  NOTHING
    first seen before it is ever raised, pushed or nudged: letters have waited
    on this machine for lanes nobody holds since before this build."""
    _heavy()
    said = []
    dry = bool(opts.get("dry"))
    owners = owner_block(state, create=True)
    acks = fold_acks(post, hub, state)
    observe_push(post, state, roots, sessions, at)
    passes = int(state.get("passes") or 0)
    window = live_minutes(hub, name)
    fresh_for = float(cfg["owner_fresh_minutes"])
    here = anyone_here(hub, name, at)
    # THE WORD, PER MACHINE: without `installed.json` in POST
    # DIR nothing is raised, pushed or nudged here, and each note says why.
    installed = installed_here(post)

    surfaces = parse_iso(state.get("surfaces_from"))

    for note in notes_for_owner(state, known, mail, name):
        token = note["token"]
        first = parse_iso(note["first_seen"])
        if first is None or surfaces is None or first < surfaces:
            # Nothing older than this build, ever — and nothing at all
            # before the mark exists, which `bootstrap_surfaces()` guarantees
            # it does by the time this runs.
            continue
        rec = owners.setdefault(token, {"kind": note["kind"], "first_seen": note["first_seen"],
                                       "to": note["to"], "push_text": note["push_text"]})
        rec["push_text"] = note["push_text"]
        if token in acks:
            rec["acked"] = dict(acks[token])
        seen = earliest_seen(token, posts, note["first_seen"]) or first
        age = (at - seen).total_seconds() / 60.0

        # ── THE RAISE, exactly once, when every condition holds ──────────────
        raised = rec.get("raised") or {}
        if not raised or (raised.get("how") == "" and int(raised.get("tries") or 0) < 2):
            why = ""
            if not installed:
                # THE PULSE CARRIES THE TOOL; NOBODY CARRIED THE WORD.
                # Recorded once, on every note, so the tree can
                # say why nothing was raised instead of leaving a silence.
                why = NOT_INSTALLED
            elif note["fyi"]:
                why = "FYI — the tree only"
            elif not cfg.get("owner_notify", True):
                why = "notes for %s are turned off here" % owner_label()
            elif token in acks:
                why = "already acked"
            elif age > fresh_for:
                why = "older than %d min when first seen here" % int(fresh_for)
            elif not (here or note["sender"] or note["kind"] == "nudge"):
                why = "nobody is at this machine"
            if not why and opts.get("foreign_hub") and not opts.get("notify"):
                # A PASS AGAINST SOMEBODY ELSE'S HUB IS A REHEARSAL, and a
                # rehearsal never pulls a human's eyes off what they are doing.
                # The gate's own seam still raises, into its record.
                why = "this is not this machine's own hub — a rehearsal never raises"
            if why:
                rec["raised"] = {"when": iso(at), "how": "none", "why": why, "tries": 0}
            elif dry:
                pass
            else:
                how, err = raise_note("Exocortex", note["target"], note["push_text"],
                                      notify=opts.get("notify"))
                tries = int(raised.get("tries") or 0) + 1
                if how:
                    rec["raised"] = {"when": iso(at), "how": how, "why": "", "tries": tries}
                elif tries >= 2:
                    rec["raised"] = {"when": iso(at), "how": "none",
                                     "why": "the notifier failed twice: %s" % err, "tries": tries}
                else:
                    rec["raised"] = {"when": iso(at), "how": "", "why": err, "tries": tries}
            rec["decided_at_pass"] = passes

        # ── THE PHONE LEG, only for a note this machine RAISED ───────────────
        raised = rec.get("raised") or {}
        acked = rec.get("acked") or {}
        if acked:
            # AN ACKED NOTE NEVER ENTERS THE PHONE LEG.  The owner
            # has already seen it; a push after that is noise on their phone.  The
            # leg used to read only `raised.how` and `push.state`, so four acked
            # notes sat `queued` with a carrier that could still be reassigned
            # and could still make the call.  The item comes OUT of the
            # carrier's pending file, so no frame is ever delivered, and the
            # push says how it ended and who ended it.
            push = rec.get("push") or {}
            if push.get("state") in ("queued", "asked"):
                if not dry and push.get("session"):
                    drop_from_pending(post, push["session"], token, "owner")
                push["state"] = "acked"
                push["why"] = ("acked by %s at %s"
                               % (acked.get("by") or "?", short_time(acked.get("when"))))
        elif raised.get("how") in ("osascript", "toast"):
            push = rec.setdefault("push", {"state": "", "tried": []})
            if not cfg.get("owner_push", True):
                push["state"] = "off"
            elif push.get("state") not in ("called", "lapsed", "off"):
                tried = push.setdefault("tried", [])
                move = False
                if push.get("state") in ("queued", "asked") and push.get("session"):
                    queued = parse_iso(push.get("when"))
                    late = queued is not None and \
                        (at - queued).total_seconds() / 60.0 >= float(cfg["owner_reassign_minutes"])
                    mtime = transcript_mtime(push["session"], roots)
                    quiet = mtime is None or (queued is not None
                                              and mtime <= queued.timestamp() + QUEUE_GRACE_S)
                    if late and (quiet or push.get("state") == "asked") and len(tried) < 2:
                        move = True           # ONE reassignment at most
                if not push.get("session") or move:
                    # PICK FIRST.  The item used to leave the
                    # first carrier's file BEFORE a second carrier was known, so
                    # with no other Claude session on the machine the note was
                    # gone from THE ONLY WINDOW THAT COULD STILL CARRY IT — and
                    # at thirty minutes the lapse blamed a window that had in
                    # fact taken a turn.  A REASSIGNMENT WITH NOWHERE TO GO IS
                    # NOT SPENT: the item stays, and the next pass may still
                    # move it.  The carrier order holds where a move happens.
                    who = pick_carrier(note, roots, window,
                                       avoid=(note.get("avoid"),), tried=tried)
                    if who and move and not dry:
                        drop_from_pending(post, push["session"], token, "owner")
                    if who:
                        tried.append(who)
                        push.update({"state": "queued", "session": who,
                                     "title": session_title(who, hub, post, sessions),
                                     "when": iso(at)})
                        if not dry:
                            queue_pending(post, who, [{
                                "token": token, "kind": "owner", "fyi": False, "wake": False,
                                "to": note["to"], "push": note["push_text"],
                                "says": note.get("says") or "", "queued": iso(at)}])
                    elif not push.get("session") and age > fresh_for:
                        push["state"] = "lapsed"
                        push["why"] = ("no Claude session had a turn on the %s within %d min"
                                       % (str(name).upper(), int(fresh_for)))
                if push.get("state") == "queued" and age > fresh_for and \
                        not push.get("called_when"):
                    push["state"] = "lapsed"
                    push["why"] = ("«%s» did not take a turn within %d min"
                                   % (push.get("title") or push.get("session") or "?",
                                      int(fresh_for)))
                elif push.get("state") == "asked" and age > fresh_for:
                    # A CARRIER THAT WAS ASKED AND NEVER CALLED used to sit
                    # `asked of «title»` on the tree for twelve hours: the lapse
                    # test looked only at `queued`.
                    push["state"] = "lapsed"
                    push["why"] = ("«%s» was asked and made no call within %d min"
                                   % (push.get("title") or push.get("session") or "?",
                                      int(fresh_for)))

        # ── THE SENDER OF A NOTE, one notice, at the pass AFTER the decision ──
        if note["fyi"] or rec.get("sender_told"):
            continue
        sid = note["sender"]
        if not sid or not safe_session_id(sid) or note["kind"] == "nudge":
            continue
        if not rec.get("raised") or passes <= int(rec.get("decided_at_pass") or 0):
            continue
        text = sender_note_line(note, rec, name, cfg)
        if not dry:
            queue_pending(post, sid, [{"token": token, "kind": "notice", "text": text,
                                       "to": note["to"], "fyi": False, "wake": False,
                                       "queued": iso(at)}])
        rec["sender_told"] = True
        said.append(text)
    state["passes"] = passes + 1
    return said


def session_title(session, hub, post, sessions=None):
    """A window's own name, from the record and nowhere else: the session map
    the pass has bound, the holds cache a claim wrote, then every session a
    claim, stamp or ear names.  '' when nothing carries it — never a guess."""
    for row in ((sessions or {}).get(session),
                read_json(holds_path(post, session), None),
                named_sessions(hub).get(session)):
        title = str((row or {}).get("title") or "").strip()
        if title:
            return title
    return ""


def sender_note_line(note, rec, name, cfg):
    """What the sender of a note for the owner hears, once — and nothing at five
    minutes, because a note for OWNER is not waiting on a session."""
    when = short_time(note.get("sender_when") or note.get("first_seen"))
    raised = rec.get("raised") or {}
    if raised.get("how") not in ("osascript", "toast"):
        return ("POST — your note to OWNER of %s was not raised: %s"
                % (when, raised.get("why") or "no reason recorded"))
    push = rec.get("push") or {}
    state = push.get("state") or ""
    title = push.get("title") or push.get("session") or "?"
    if not cfg.get("owner_push", True) or state == "off":
        phone = "off"
    elif state == "called":
        phone = "pushed by «%s» %s" % (title, short_time(push.get("called_when")))
    elif state == "acked":
        phone = "acked"                     # the owner saw it first
    elif state in ("queued", "asked"):
        phone = "asked of «%s»" % title
    else:
        phone = "no Claude session had a turn — not pushed"
    return ("POST — your note to OWNER of %s: raised on the %s %s · phone: %s"
            % (when, str(name).upper(), short_time(raised.get("when")), phone))


def drop_from_pending(post, session, token, kind="letter"):
    """Take ONE item out of ONE session's pending file — what a reassignment
    owes: the item leaves the first file before it enters the second."""
    _heavy()
    items = read_pending(post, session)
    left = [i for i in items if not (str(i.get("token")) == str(token)
                                     and (i.get("kind") or "letter") == kind)]
    if len(left) == len(items):
        return 0
    path = pending_path(post, session)
    if left:
        write_json_atomic(path, {"session": str(session), "updated": iso(now()), "items": left})
    else:
        try:
            os.unlink(path)
        except OSError:
            pass
    return 1


# --------------------------------------------------------------------------
# THE TREE — tool-owned facts, tree-owned drawing
# --------------------------------------------------------------------------

def tree_facts(hub, lanes=()):
    """Everything the tree page may say about the post, and not one byte more.

    A PURE READ of every post-<machine>.json, every live-sessions-<machine>.json
    and post-config.json.  IT NEVER THROWS, and with no post file anywhere it
    returns {} — which is what makes the page byte-identical to the day before
    this build on a machine where the postman has never passed.

    `lanes` is [(key, lane name, is hub)] — the tree's own rows.  The match from
    an address to a lane is made HERE, with mail.py's own addr_key and phase A's
    own suffix rule, so there is never a second matcher.
    """
    try:
        return _tree_facts(hub, lanes)
    except Exception:
        return {}


def _tree_facts(hub, lanes=()):
    _heavy()
    hub = Path(hub)
    try:
        files = [f for f in sorted(hub.glob("post-*.json")) if f.name != "post-config.json"]
    except OSError:
        files = []
    if not files:
        return {}
    mail = mail_module(hub)
    cfg = config(hub)
    at = now()
    bodies = {}
    for f in files:
        d = read_json(f, None)
        if isinstance(d, dict) and d.get("machine"):
            bodies[str(d["machine"]).lower()] = d
    if not bodies:
        return {}
    here = machine_name()
    beats = {}
    try:
        for f in sorted(hub.glob("live-sessions-*.json")):
            d = read_json(f, None)
            if not isinstance(d, dict):
                continue
            mch = str(d.get("machine") or "").lower()
            if mch and isinstance(d.get("postman"), dict):
                beats[mch] = d["postman"]
    except OSError:
        pass

    # THIS MACHINE'S OWN heartbeat is the truth about this machine: the pulse's
    # copy is up to five minutes behind, and a postman that passed sixteen
    # seconds ago must never be drawn as quiet on the machine it runs on.
    # …and THIS HUB'S OWN POST DIR, never the machine's real one when the hub
    # asked about is a rehearsal: a rehearsal's tree used to
    # draw the real postman's heartbeat as its own.
    mine_post = post_dir(hub=str(hub))
    mine_beat = read_json(mine_post / "heartbeat.json", None)
    if isinstance(mine_beat, dict) and mine_beat.get("when"):
        beats[here] = {"last_pass": mine_beat.get("when"), "every": mine_beat.get("every"),
                       "version": mine_beat.get("version"),
                       "last_good_pull": mine_beat.get("last_good_pull") or ""}

    machines = {}
    for mch in sorted(set(list(bodies) + list(beats))):
        body = bodies.get(mch) or {}
        beat = beats.get(mch) or {}
        when = parse_iso(beat.get("last_pass"))
        try:
            every = int(beat.get("every") or cfg["pass_every"])
        except Exception:
            every = int(cfg["pass_every"])
        age = (at - when).total_seconds() if when is not None else None
        if age is None:
            state, quiet_since = "none", ""
        else:
            slack = 0 if mch == here else 300     # the other machine's age arrives by the pulse
            state = "passing" if age <= 3 * every + slack else "quiet"
            quiet_since = when.strftime("%H:%M")
        rows = {"last_pass": beat.get("last_pass") or "", "every": every, "age_s": age,
                "state": state, "since": quiet_since,
                "waiting": sum(1 for e in (body.get("letters") or {}).values()
                               if isinstance(e, dict) and e.get("state") == "waiting"
                               and not e.get("parent")),
                "version": beat.get("version") or body.get("version") or "",
                "last_good_pull": beat.get("last_good_pull") or ""}
        machines[mch] = rows

    # ARE THE SURFACES ON HERE?  The marker is
    # machine-personal and never crosses the brain, so only THIS machine's root
    # can carry the fact — and it carries it either way, so that an absent key
    # means "another machine, which cannot be asked from here" and never
    # "installed".
    if here in machines:
        machines[here]["surfaces"] = bool(installed_here(mine_post))

    # ── the letters, matched to the tree's own lane rows ─────────────────────
    want = []
    for key, lane_name, is_hub in (lanes or ()):
        want.append((key, mail.addr_key(lane_name), bool(is_hub)))
    lane_rows = dict((key, []) for key, _k, _h in want)
    delivered_today = dict((key, []) for key, _k, _h in want)
    for mch, body in sorted(bodies.items()):
        for token, e in sorted((body.get("letters") or {}).items()):
            if not isinstance(e, dict):
                continue
            address = str(e.get("to") or "")
            lane = lane_of(address, mail)
            if lane == "owner":
                continue
            when = parse_iso(e.get("first_seen"))
            row = {"token": token, "to": address, "line": e.get("line") or "",
                   "why": e.get("why") or "", "fyi": bool(e.get("fyi")),
                   "state": e.get("state") or "waiting", "machine": mch,
                   "first_seen": e.get("first_seen") or "",
                   "age_s": (at - when).total_seconds() if when is not None else None,
                   "holder": e.get("holder") or None, "nudged": e.get("nudged") or None,
                   "delivered": e.get("delivered") or None}
            row["lane"] = lane_words(address, mail)       # the ✉ hover's first words
            row["from"], row["subject"] = "", " · ".join(user_words([row["line"]], mail))
            for key, lane_key, is_hub in want:
                if lane == "hub":
                    if not is_hub:
                        continue
                elif not (lane_key == lane or lane_key.endswith("/" + lane)):
                    continue
                if row["state"] == "waiting":
                    lane_rows[key].append(row)
                elif row["state"] == "delivered":
                    got = parse_iso((e.get("delivered") or {}).get("when"))
                    if got is not None and got.date() == at.date():
                        delivered_today[key].append(row)

    # ── the notes for the owner: not acked, younger than owner_hours, ONE PER TOKEN
    # however many machines have seen it, each machine's facts in its own view
    # (the same grouping owner_rows() uses, and no second rule)
    notes = group_owner_notes(bodies, cfg, at, here=here)
    notes.sort(key=lambda r: r.get("first_seen") or "", reverse=True)
    return {"machines": machines, "lanes": lane_rows, "delivered": delivered_today,
            "owner": notes, "config": {"not_read_minutes": cfg["not_read_minutes"],
                                      "owner_hours": cfg["owner_hours"]}}


# --------------------------------------------------------------------------
# --status (mail.py calls this too, so the words are the same in both places)
# --------------------------------------------------------------------------

def status_rows(hub, post, mail, which=None):
    """Every waiting letter, both directions, each with its why."""
    _heavy()
    posts = read_posts(hub)
    rows = []
    for machine, body in sorted(posts.items()):
        for token, e in (body.get("letters") or {}).items():
            if e.get("state") != "waiting":
                continue
            if e.get("parent"):
                continue                     # a lane's copy: the broadcast's own row counts it
            if which and which not in (token,) and mail.addr_key(which) != mail.addr_key(e.get("to") or ""):
                continue
            rows.append({"token": token, "to": e.get("to") or "", "why": e.get("why") or "",
                         "fyi": bool(e.get("fyi")), "machine": machine,
                         "first_seen": e.get("first_seen") or "",
                         "nudged": e.get("nudged") or None})
    rows.sort(key=lambda r: r.get("first_seen") or "")
    return rows


def group_owner_notes(bodies, cfg, at, here=""):
    """ONE ROW PER TOKEN — the notes for the owner still waiting, grouped.

    ONE NOTE, MANY MACHINES.  A `to: OWNER` letter is OWNED BY EVERY MACHINE THAT
    SEES IT (`owner_of`), so the same token carries a `owner` key in EVERY
    machine's post file: the chip said `✉ 2 for you` for one note and
    `--ack OWNER` answered `acked: 2 note(s)`.  One note.

    Each machine's own facts ride INSIDE the row as a view — {machine, raised,
    push} — THIS MACHINE'S FIRST, so the click can say one `raised` line per
    machine.  The note's age is the EARLIEST first sight any of them records
    (the AGE rule), and a note ACKED IN ANY VIEW is acked everywhere.
    `machine`, `raised` and `push` stay on the row for every caller that had
    them: `machine` and `raised` from the first view, `push` from whichever
    view has one.

    The ONE grouping rule, used by owner_rows() and by _tree_facts() alike."""
    _heavy()
    hours = float(cfg["owner_hours"])
    mine = str(here or "").lower()
    seen = {}
    for machine in sorted(bodies):
        body = bodies[machine] or {}
        for group in ("letters", "nudges"):
            for token, e in sorted((body.get(group) or {}).items()):
                owner = owner_block(e) if isinstance(e, dict) else None
                # An entry with NO block of the person's own is not a note for
                # them: `owner_block` answers {} for "nothing here", and {} is
                # a dict, so emptiness is what this asks about.
                if not owner:
                    continue
                row = seen.get(token)
                if row is None:
                    row = seen[token] = {
                        "token": token, "machine": machine,
                        "kind": "nudge" if group == "nudges" else "letter",
                        "line": "", "to": e.get("to") or "", "case": e.get("case") or "",
                        "first_seen": "", "acked": {}, "views": []}
                if not row["line"]:
                    row["line"] = e.get("line") or e.get("text") or ""
                when = parse_iso(e.get("first_seen"))
                first = parse_iso(row["first_seen"])
                if when is not None and (first is None or when < first):
                    row["first_seen"] = e.get("first_seen") or ""
                got = owner.get("acked") or {}
                if got.get("when") and not row["acked"]:
                    row["acked"] = dict(got)
                row["views"].append({"machine": machine,
                                     "raised": owner.get("raised") or {},
                                     "push": owner.get("push") or {}})
    out = []
    for token in sorted(seen):
        row = seen[token]
        if row["acked"]:
            continue                       # acked in ANY view is acked in all
        when = parse_iso(row["first_seen"])
        if when is None or (at - when).total_seconds() > hours * 3600:
            continue
        row["views"].sort(key=lambda v: (0 if v["machine"] == mine else 1, v["machine"]))
        row["machine"] = row["views"][0]["machine"]
        row["raised"] = row["views"][0]["raised"]
        row["push"] = {}
        for view in row["views"]:
            if (view.get("push") or {}).get("state"):
                row["push"] = view["push"]
                break
        row["age_s"] = (at - when).total_seconds()
        out.append(row)
    out.sort(key=lambda r: r.get("first_seen") or "")
    return out


def owner_rows(hub, at=None):
    """Every note for the owner still waiting: not acked, and younger than owner_hours.
    Read from every machine's post file, so a note raised on one machine and
    acked on the other is gone from both — and counted ONCE however many
    machines have seen it."""
    _heavy()
    at = at or now()
    return group_owner_notes(read_posts(hub, live_sessions=False), config(hub), at,
                            here=machine_name())


def sent_rows(hub, post, mail, which=None):
    _heavy()
    posts = read_posts(hub)
    rows = []
    for machine, body in sorted(posts.items()):
        for token, r in (body.get("sent") or {}).items():
            entry = fleet_entry(posts, token) or {}
            if entry.get("state") not in (None, "waiting"):
                continue
            if which and which not in (token,) and mail.addr_key(which) != mail.addr_key(r.get("to") or ""):
                continue
            rows.append({"token": token, "to": r.get("to") or "", "when": r.get("when") or "",
                         "why": entry.get("why") or "", "machine": machine})
    rows.sort(key=lambda r: r.get("when") or "")
    return rows


def heartbeat_age(post):
    """Seconds since this machine's last pass, or None when it has never passed."""
    _heavy()
    d = read_json(Path(post) / "heartbeat.json", None)
    if not isinstance(d, dict):
        return None
    when = parse_iso(d.get("when"))
    if when is None:
        return None
    return (now() - when).total_seconds()


def read_today(hub, at=None):
    at = at or now()
    posts = read_posts(hub)
    n = 0
    for body in posts.values():
        for e in (body.get("letters") or {}).values():
            if e.get("broadcast"):
                continue                     # its copies are the reads
            when = parse_iso((e.get("delivered") or {}).get("when"))
            if when is not None and when.date() == at.date():
                n += 1
    return n


def cmd_status(hub, post, which=None):
    _heavy()
    mail = mail_module(hub)
    rows = status_rows(hub, post, mail, which)
    out = []
    for r in rows:
        nudged = r.get("nudged") or {}
        tail = " · FYI" if r["fyi"] else ""
        if nudged.get("when"):
            tail += " · %s was nudged at %s" % (owner_label(), short_time(nudged["when"]))
        out.append("waiting · %s · %s%s  [%s]"
                   % (r["to"], r["why"] or "not read yet", tail, r["token"]))
    for r in owner_rows(hub):
        raised = r.get("raised") or {}
        push = r.get("push") or {}
        where = ("raised on the %s %s" % (r["machine"].upper(), short_time(raised.get("when")))
                 if raised.get("how") in ("osascript", "toast")
                 else "not raised: %s" % (raised.get("why") or "not yet"))
        phone = push.get("state") or "no carrier yet"
        if push.get("state") == "called" and push.get("result"):
            phone = "called · %s" % push["result"]
        out.append("for you · %s · %s · phone: %s  [%s]"
                   % (r["line"][:100], where, phone, r["token"]))
    for r in sent_rows(hub, post, mail, which):
        out.append("you sent · %s · %s · %s  [%s]"
                   % (r["to"], short_time(r["when"]), r["why"] or "not read yet", r["token"]))
    age = heartbeat_age(post)
    if age is None:
        tail = ("mail: %d waiting · %d read today · no postman on this machine — letters "
                "wait for a --read" % (len(rows), read_today(hub)))
    else:
        tail = ("mail: %d waiting · %d read today · postman passed %d s ago"
                % (len(rows), read_today(hub), int(age)))
    out.append(tail)
    # why letters did not ride, as the last pass that skipped any counted it
    beat = read_json(Path(post) / "heartbeat.json", None)
    skipped = (beat or {}).get("skipped") if isinstance(beat, dict) else None
    if isinstance(skipped, dict):
        words = " · ".join("%d %s" % (int(skipped.get(w) or 0), w) for w in SKIP_WORDS
                           if int(skipped.get(w) or 0))
        if words:
            out.append("skipped by the pass of %s: %s" % (short_time(skipped.get("when")), words))
    # THE STATE VISIBLE BEFORE ANYONE ASKS: on a machine the
    # brain merely carried the tool to, the pass runs and the surfaces do not.
    if not installed_here(post):
        out.append("surfaces off — not installed here")
    return out


# --------------------------------------------------------------------------
# --install-hooks — done on the owner's word, per machine, never automatic
# --------------------------------------------------------------------------

def brain_carries(path, home=None):
    """Does the brain CARRY this file — would a change here land on the other
    machine?  A per-machine command in a synced file would break the other
    machine, so the install refuses one by name.

    A manifest entry in `report-only` mode does NOT carry: the sync shows its
    drift and never writes the live file (that is a machine's ~/.claude/settings.json,
    mapped to claude-home/settings.reference.json).  Neither does a `per_machine`
    entry, which keeps one copy per machine by construction."""
    _heavy()
    want = Path(path).resolve()
    manifests = sync_manifests(home)
    if not manifests:
        return ""
    record = machine_record(home)
    roots = record.get("roots") or {}
    for entry in [e for m in manifests for e in (m.get("entries") or [])]:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("mode") or "") == "report-only" or entry.get("per_machine"):
            continue
        live = entry.get("live") or {}
        root = roots.get(str(live.get("root") or ""))
        if not root:
            continue
        base = Path(root) / str(live.get("rel") or "")
        try:
            base = base.resolve()
        except Exception:
            continue
        if entry.get("kind") == "file":
            if base == want:
                return str(entry.get("repo") or entry.get("id") or "")
        else:
            try:
                want.relative_to(base)
                return str(entry.get("repo") or entry.get("id") or "")
            except ValueError:
                continue
    return ""


def hook_command(hub, post, vendor, python=None):
    """The command an entry runs, rendered per machine from the record and
    sys.executable — never a path written into this file.

    ONE SHELL-COMMAND STRING, on both vendors, because that is the only form both
    document: Claude's `args` array ("spawned directly with `args` as the argument
    vector, with no shell involved") would sidestep Windows quoting, but Codex's
    hooks document no `args` key at all, and one renderer that both vendors accept
    beats two that must be kept in step.  Every path is quoted.

    THE PYTHON IS A CONSOLE PYTHON: the hook PRINTS the frame,
    and `pythonw` has no stdout."""
    _heavy()
    py = python or console_python()
    return '"%s" "%s" --hook --vendor %s --post-dir "%s"' % (
        py, Path(hub) / "tools" / "postman.py", vendor, Path(post))


def is_ours(command):
    """Is this hook entry the postman's own?  Tested on the two parts and not on
    the phrase `postman.py --hook`, because the rendered command QUOTES its paths
    ("…/postman.py" --hook …) and a quote sits between them — a test on the phrase
    would install the entries twice and then refuse to uninstall them.  One test, used by the merge and by the strip alike."""
    c = str(command or "")
    return "postman.py" in c and "--hook" in c


def detect_indent(text):
    """The indentation the file already uses, so a merge leaves it as it was."""
    _heavy()
    m = re.search(r"\n(\s+)\"", text or "")
    if not m:
        return 2
    pad = m.group(1).replace("\n", "")
    return len(pad) if pad and pad[0] == " " else 2


def claude_settings_path(home=None, record=None):
    _heavy()
    d = record if record is not None else machine_record(home)
    root = (d.get("roots") or {}).get("claude") or (home_dir(home) / ".claude")
    return Path(root) / "settings.json"


def merge_hooks(text, command, events):
    """MERGE beside whatever is there — a machine may carry another tool's hooks on
    several events, and not one of its entries may be reordered or rewritten.  The
    file's own key order and indentation are kept as far as the json module
    allows; a second run adds nothing and writes nothing.

    One merger for both vendors: Claude keeps its entries under `hooks` in
    settings.json, and Codex keeps the SAME shape in its own hooks.json
    ("Codex discovers hooks next to active config layers in either of these
    forms: `hooks.json` … `~/.codex/hooks.json`")."""
    _heavy()
    data = json.loads(text)                          # a file that is not valid JSON raises
    if not isinstance(data, dict):
        raise ValueError("the settings file is not a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("`hooks` in the settings file is not an object")
    added = []
    for event in events:
        rows = hooks.setdefault(event, [])
        if not isinstance(rows, list):
            raise ValueError("`hooks.%s` is not a list" % event)
        if any(isinstance(r, dict) and any(
                isinstance(h, dict) and is_ours(h.get("command"))
                for h in (r.get("hooks") or []))
               for r in rows):
            continue                                 # ours already: nothing to add
        rows.append({"hooks": [{"type": "command", "command": command,
                                "timeout": HOOK_ENTRY_TIMEOUT}]})
        added.append(event)
    indent = detect_indent(text)
    rendered = json.dumps(data, indent=indent, ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, added


def strip_hooks(text):
    """--uninstall-hooks removes only entries whose command contains
    `postman.py --hook`, and leaves every other tool's entry exactly as it is."""
    _heavy()
    data = json.loads(text)
    hooks = data.get("hooks") if isinstance(data, dict) else None
    removed = []
    if isinstance(hooks, dict):
        for event, rows in list(hooks.items()):
            if not isinstance(rows, list):
                continue
            keep = []
            for row in rows:
                mine = isinstance(row, dict) and any(
                    isinstance(h, dict) and is_ours(h.get("command"))
                    for h in (row.get("hooks") or []))
                if mine:
                    removed.append(event)
                else:
                    keep.append(row)
            if keep:
                hooks[event] = keep
            else:
                hooks.pop(event)
        if not hooks:
            data.pop("hooks", None)
    indent = detect_indent(text)
    rendered = json.dumps(data, indent=indent, ensure_ascii=False)
    if text.endswith("\n"):
        rendered += "\n"
    return rendered, removed


def hooks_file(vendor, home=None, record=None, settings=None):
    """Where a vendor keeps its hooks on this machine — from the record, never a
    path written here.  Claude: `<roots.claude>/settings.json` ("The desktop app
    reads the same settings files as the CLI").  Codex: `<roots.codex>/hooks.json`
    ("In practice, the four most useful locations are: `~/.codex/hooks.json` …")."""
    _heavy()
    if settings:
        return Path(settings)
    d = record if record is not None else machine_record(home)
    roots = d.get("roots") or {}
    if vendor == "codex":
        return Path(roots.get("codex") or (home_dir(home) / ".codex")) / "hooks.json"
    return Path(roots.get("claude") or (home_dir(home) / ".claude")) / "settings.json"


def cmd_install_hooks(hub, post, vendor, dry=False, home=None, settings=None, remove=False):
    """Print exactly what it would add, add only that, keep a backup, and refuse
    a file the brain carries — by name.  Running sessions pick the entries up
    through the app's own settings watcher: no restart, and an uninstall is as
    quick."""
    _heavy()
    out = []
    vendors = [vendor] if vendor else ["claude", "codex"]
    ready = []                  # the vendors whose entries are in place at the end
    for v in vendors:
        events = sorted(HOOK_EVENTS.get(v) or {})
        path = hooks_file(v, home, settings=settings)
        for note in (CODEX_EVENT_NOTES if v == "codex" else []):
            out.append("codex: %s" % note)
        if not events:
            out.append("%s: no event of this vendor's is documented well enough to "
                       "install — nothing proposed for it" % v)
            continue
        carried = brain_carries(path, home)
        if carried:
            out.append("REFUSED: %s is carried by the brain as %s — a per-machine command "
                       "in a synced file would break the other machine" % (path, carried))
            continue
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not text.strip():
            if remove:
                out.append("%s: no hooks file at %s — nothing to remove" % (v, path))
                continue
            text = "{}\n"                            # Codex keeps its own hooks.json; make one
        try:
            if remove:
                rendered, touched = strip_hooks(text)
            else:
                rendered, touched = merge_hooks(text, hook_command(hub, post, v), events)
        except Exception as exc:
            out.append("REFUSED: %s is not valid JSON (%s) — nothing written" % (path, exc))
            continue
        verb = "would remove" if remove else "would add"
        if not touched:
            out.append("%s: already %s in %s — nothing to write"
                       % (v, "absent" if remove else "installed", path.name))
            if not remove:
                ready.append(v)             # its entries are there: the word holds
            continue
        for event in sorted(set(touched)):
            out.append("%s %s · %s · timeout %ds"
                       % (verb, event, hook_command(hub, post, v), HOOK_ENTRY_TIMEOUT))
        if dry:
            out.append("--dry: nothing was written (%s)" % path)
            continue
        backup = Path(post) / "backups" / ("%s-%s-%s" % (v, now().strftime("%Y%m%dT%H%M%S"), path.name))
        mkdirs(backup.parent)
        if path.is_file():
            write_atomic(backup, text, mode=PRIVATE_FILE)   # a copy of a private file stays private
        # An EXISTING settings file keeps its own mode; one we CREATE (Codex's
        # hooks.json) is this account's alone.
        write_atomic(path, rendered, mode=PRIVATE_FILE)
        out.append("wrote %s · backup %s" % (path, backup if path.is_file() else "(new file)"))
        if not remove:
            ready.append(v)
    # THE WORD, AS A FILE THIS MACHINE ALONE CARRIES.  The
    # brain hands `tools/` to the other machine and its pulse runs the pass, so
    # the install cannot be a fact about the TOOL — it is a fact about the
    # MACHINE, and this is where the pass reads it.  Machine-personal: POST DIR
    # never crosses the brain.  Idempotent: a second install rewrites the same
    # marker, and a refused or dry run writes none.
    marker = Path(post) / "installed.json"
    if dry:
        pass
    elif remove:
        if marker.is_file():
            try:
                os.unlink(str(marker))
                out.append("surfaces off — this machine is no longer installed (%s)" % marker)
            except OSError as exc:
                out.append("could not remove %s (%s) — the surfaces are still on here"
                           % (marker, exc))
    elif ready:
        write_json_atomic(marker, {"when": iso(now()), "vendors": sorted(set(ready)),
                                   "hub": str(hub)})
        out.append("surfaces on — this machine is installed (%s)" % marker)
    return out


# --------------------------------------------------------------------------

def usage():
    print(__doc__)


def main(argv):
    if "--hook" in argv:                            # before anything else is imported
        return hook_main(argv)
    _heavy()
    import argparse
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pass", dest="do_pass", action="store_true")
    ap.add_argument("--status", nargs="?", const="", default=None)
    ap.add_argument("--remote-hint", dest="remote_hint", nargs="*", default=None)
    ap.add_argument("--install-hooks", action="store_true")
    ap.add_argument("--uninstall-hooks", action="store_true")
    ap.add_argument("--vendor", default=None)
    ap.add_argument("--hub", default=None)
    ap.add_argument("--home", default=None)
    ap.add_argument("--post-dir", default=None)
    ap.add_argument("--sync", default=None)
    ap.add_argument("--settings", default=None)
    ap.add_argument("--now", default=None)
    ap.add_argument("--notify", default=None)   # the seam: a command that stands in for
    ap.add_argument("--counters", default=None)  # the notifier, in every gate and test
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--help", "-h", action="store_true")
    a, unknown = ap.parse_known_args(argv)
    if unknown:
        sys.stderr.write("postman.py: unknown flag %r\n" % unknown[0])
        usage()
        return 2
    if a.help or not (a.do_pass or a.status is not None or a.install_hooks or a.uninstall_hooks
                      or a.remote_hint is not None):
        usage()
        return 0
    global _NOW_OVERRIDE
    if a.now:
        _NOW_OVERRIDE = parse_iso(a.now)
    record = machine_record(a.home)
    hub = hub_dir(a.hub, a.home, record)
    # Pointed at a hub that is not this machine's own, the tool
    # keeps its working state in THAT hub's .post/ and never touches the real one.
    post = post_dir(a.post_dir, a.home, record, hub=a.hub)
    if a.remote_hint is not None:                   # the session supplies the ids
        code, lines = write_remote_hint(post, a.remote_hint, dry=a.dry)
        for line in lines:
            print(line)
        return code
    if a.install_hooks or a.uninstall_hooks:
        for line in cmd_install_hooks(hub, post, a.vendor, dry=a.dry, home=a.home,
                                      settings=a.settings, remove=a.uninstall_hooks):
            print(line)
        return 0
    if a.status is not None:
        for line in cmd_status(hub, post, a.status or None):
            print(line)
        return 0
    # THE NOTIFIER'S SEAM, and the two ways it is set.  `--notify` is the flag a
    # gate passes; EXO_NOTIFY is the same seam in the ENVIRONMENT, because
    # `mail.py --send` runs a pass of its own as a child and a test's child must
    # not be able to raise a real banner behind the test's back.
    opts = {"home": a.home, "sync": a.sync, "no_pull": a.no_pull, "dry": a.dry,
            "counters": a.counters,
            "notify": a.notify or os.environ.get("EXO_NOTIFY") or None,
            # THE SAME ONE ANSWER the POST DIR uses: a record
            # that names this hub through a symlink is not a rehearsal.
            "foreign_hub": not is_own_hub(hub, a.home, record)}
    try:
        code, said = cmd_pass(hub, post, opts)
    except Exception as exc:
        sys.stderr.write("postman: the pass stopped — %r\n" % (exc,))
        return 1
    if not a.quiet:
        for line in said:
            print(line)
    elif said:
        for line in said:
            if line.startswith(("BOOTSTRAP", "SURFACES", "pull failed", "POST —")):
                print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
