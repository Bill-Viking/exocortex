#!/usr/bin/env python3
"""exocortex-sync — two-machine file sync for one person's second brain.

HOME SIDE ONLY. Never clone or run this on a work machine.

Python 3 standard library only. One file. Runs identically on macOS and
Windows: pathlib everywhere, no symlinks, no chmod, no shell=True, no
Unix-only calls.

Verbs
    status                     what has drifted, both directions, plus context
    pull                       git pull, then copy repo -> live where repo wins
    push                       copy live -> repo where live wins, commit, push
    push --prune-local         the same, after ONE commit that takes this
                               machine's own files out of the brain (below)
    sync                       pull then push (the normal verb)
    recover                    restore every live file the mirror holds and this
                               machine lacks (nothing is overwritten)
    bootstrap --machine NAME   first run on a machine: write machine.json, pull
    preflight                  check the carriers alone (exit 3 when one is missing)
    carriers --show|--drive …  edit this machine's carriers block in machine.json

Two layouts
    LEGACY        this file lives inside the brain clone, machine.json beside
                  it, and the hub folder is recorded in that file.
    PROGRAM-TREE  the hub folder is a checkout of the program: this file is
                  <hub>/sync/sync.py, the resolver is <hub>/tools/exo_paths.py,
                  machine.json is <hub>/machine.json and the brain clone lives
                  wherever the record says (default <home>/exocortex-brain).
    Either way this tool serves ONE repo: the brain. The shim at the top of
    this file works out which layout it is standing in before anything else
    runs, and the resolver answers every "where is it" question after that.

The partition (program-tree only, switched on by the record)
    In a program tree the hub folder holds the program and your own notes side
    by side, and git's own ignore rules say which is which: what git IGNORES is
    the brain and rides this sync; what git TRACKS is the program and rides
    git; anything untracked and un-ignored rides NEITHER and is reported by
    name until it is committed or moved. It is on only when machine.json
    records "partition": "git-ignore" — never inferred from a .git folder. A
    failed check stops the hub's entry alone, in one plain sentence; every
    other entry still syncs.

Never-sync — this machine's own files, in BOTH layouts
    A short executable list is applied to the hub folder's entry, on both walks,
    before anything is compared: machine.json, installed.json, scratch/, .git/,
    .claude/settings.local.json, .claude/*.lock, caches, the installer's lock
    and the pages each machine draws for itself by exact name. A path under it
    is never carried out, never carried in and never compared, so it is never
    reported as deleted on either side and never asks the human anything. With
    the partition on, the list is applied before git is asked. The manifest's
    own exclude list still rules what it names beyond the list. In the older
    layout the two identity names are read at the top of the hub folder only
    (HELD_BY_NAME, below).

    A path under the list that the brain still holds from before is named ONCE,
    by `status` ("in the brain by mistake"), and leaves the repo only at
    `push --prune-local`: one commit of its own (`git rm --cached`, the list in
    its message, a guard block in the brain's .gitignore so the leftover copies
    are never taken back in). It never runs by itself. History keeps every byte
    and nothing on this machine's disk is deleted.

    Two habits follow. A build's INSTALL CANDIDATE, the file another machine's
    hub installs from, is staged in harvest/<row-id>/ (which syncs) and the
    install letter names that path; a scratch/ path in an install letter is the
    builder's error, and the opener collector flags it. A tool's own RECORDS
    never live under scratch/: the hygiene receipts live in watchers/receipts/.

The brain privacy guard
    Before a push that has something to send, the tool resolves the address the
    push would actually reach and asks whether it is publicly readable. A
    public answer stops the push before any byte; an unanswerable one stops the
    push and lets the local sync finish, and the next beat asks again. No
    answer is ever reused for a later push. It is ENFORCING in a program tree
    and REPORT-ONLY in the older layout. Residual risk, stated plainly: a
    destination's visibility can change between the check and the transfer, and
    nothing on this side can close that window.

Carrier preflight
    Every pull first asks what the record says is owed by a carrier that is not the cloud (a
    transfer-drive payload in a drive ledger, a private git host) and checks each carrier
    first-hand — carrier_preflight.py, beside this file. One plain sentence when one is
    missing; the brain then syncs regardless. A missing or broken checker can never stop a
    pull.

Settling window
    A push carries only files whose last write is older than 60 seconds, so a
    file a builder or a watcher is halfway through writing waits one beat
    instead of crossing half-written (--settle N, ORCHSYNC_SETTLE; --settle 0
    carries everything, which is what button-up and the hub's close ritual
    pass). The signal files the fleet runs on - mail, claims, the stamps,
    ideas, the journal - never wait.

Push retry
    Two machines and a five-minute pulse push one branch, so a rejected push
    is an ordinary condition, not a failure: pull the newer tip under the
    commit and push again, up to three attempts (--retries N,
    ORCHSYNC_PUSH_RETRIES) with a random 1-4 s wait between them. If every
    attempt fails the commit stays safe locally and the machine says so twice:
    one `!` line here and one addressed INBOX line for this machine's hub.

Copy rule
    Per file, newest-mtime-wins on the very first encounter. After that a
    hash of both sides is remembered in .sync-state.json, and a file changed
    on BOTH sides since the last sync is flagged loudly and skipped. Nothing
    is ever deleted and nothing is ever resolved silently — but for the two
    owner cases , each said in one line: a signal file THIS machine
    owns and took down itself leaves the brain at the next pull or push
    (`taken down: <file> (this machine's own)`), and the other machine's copy
    of it is removed there only while it is unchanged since the last sync
    (`carried: <file> taken down by <owner>`); a copy that moved is reported
    and kept. More than OWNER_GONE_CAP of this machine's own files gone at
    once is read as a lost folder, never a takedown: nothing is deleted.

Machine-owned files 
    MACHINE_OWNED names every file one machine writes and the other only
    carries (the stamps, the mail state, the meters, the ledgers, carry/'s
    per-machine folders). On the owner, live wins — and when the brain's copy
    moved too, one line says `machine-owned <file> also changed in the brain —
    live kept`. On the carrier the brain's copy wins and is never pushed back —
    one line, `carried <file> is <owner>'s — the brain's copy kept`, when a copy
    edited here is put back. The owner is known by name: this machine's, or one
    the manifest's machines block records.

Memories
    ~/.claude/projects/<munged>/memory/ <-> claude-home/memories/<logical>/.
    Both directions work out the munged directory name by re-munging THIS
    machine's recorded roots, so push is the exact inverse of pull and the
    project folder itself need not exist here. A live memory dir that cannot
    be traced back to the projects root is this machine's own business: it is
    reported and left alone, never staged into the repo under a munged name.

Testing hook
    ORCHSYNC_TEST_ROOT=/some/dir  redirects every LIVE path under that dir,
    preserving its full structure (<home>/... -> $TEST/<home>/...).
    The repo side is untouched. Use it to exercise pull without writing over
    real files. Nothing else changes behaviour.

    push is refused while it is set. ORCHSYNC_ALLOW_LOCAL_PUSH=1 lifts that
    for one run, and ONLY when origin is a path on this disk: a rehearsal can
    exercise the whole push, and can never reach a host.

    EXO_PRIVACY_PROBE=/some/file.json answers the privacy guard from a file
    instead of the network: {"<resolved url>": "public|private|unknown"}. Unset
    is the real check. A gate never touches the network.

Transaction lock
    pull, push, sync, recover and bootstrap hold one checkout-local lock;
    sync holds it across BOTH halves. Busy exits 5 without dispatching a verb.
    ORCHSYNC_LOCK_WAIT sets the bounded wait (90 seconds by default).
    While held, ORCHSYNC_LOCK_HELD is this process's pid. A direct child that
    inherits its parent's pid there may re-enter without acquiring; the parent
    must wait for that child before leaving its transaction. Other values do
    not bypass the lock. The previous environment value is restored on exit.
    ORCHSYNC_LOCK_SLEEP pauses after acquisition ONLY with EXO_GATE_SYNC_LOCK=1
    (the disposable gate's mark); it has no effect in an ordinary run.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

# --------------------------------------------------------------------------
# the shim, and the seam it feeds
#
# The first thing this file does, because it cannot import a line of the
# program before it knows where the program is. Ten lines decide the layout;
# the resolver answers everything after that, and every name that used to hang
# off this file's own folder now hangs off the BRAIN the record names. In the
# older layout the brain IS this file's folder, so nothing moves.
#
# The fallback covers exactly ONE event: the resolver cannot
# be LOADED in a POSITIVELY identified older installation. Anything else that
# cannot be resolved is a STOP in one plain sentence — never a guess, and never
# a mirror of the whole hub.
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent

LAYOUT_LEGACY = "legacy"
LAYOUT_PROGRAM = "program-tree"
PARTITION_GIT = "git-ignore"
BRAIN_FOLDER_DEFAULT = "exocortex-brain"     # a new install's brain clone
USER_MANIFEST_NAMES = ("sync-manifest.json", "manifest.user.json")
BASE_MANIFEST_NAME = "manifest.base.json"


class SyncStop(Exception):
    """One plain sentence, ready to print as it stands. No traceback needed."""


def _plain_json(path):
    """A JSON object, read without help from anything below this line."""
    try:
        with open(str(path), "rb") as handle:
            data = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None


def _load_by_path(name, path):
    """A module loaded from a FILE. Never a package import: at this point in
    the run nothing of the program is on the import path yet."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _load_resolver():
    """(the resolver module or None, where it was looked for)."""
    beside = HERE.parent / "tools" / "exo_paths.py"
    if beside.is_file():                       # <hub>/sync/sync.py — a program tree
        return _load_by_path("exo_paths", beside), str(beside)
    record = _plain_json(HERE / "machine.json") or {}
    hub = (record.get("roots") or {}).get("orchestrator")
    if hub:                                    # the older layout: the hub is recorded
        tools = Path(str(hub)).expanduser() / "tools"
        if str(tools) not in sys.path:
            sys.path.insert(0, str(tools))
        module_file = tools / "exo_paths.py"
        if module_file.is_file():
            return _load_by_path("exo_paths", module_file), str(module_file)
        return None, str(module_file)
    return None, str(beside)


def _positively_legacy():
    """The older layout, identified POSITIVELY by all five of its own marks.

    Only this answer earns the fallback, and only this answer turns the
    partition off and lets the mirror carry the hub whole."""
    record = _plain_json(HERE / "machine.json")
    if record is None:
        return False                           # no machine file beside this one
    if not (HERE / ".git").exists():
        return False                           # not running inside the brain clone
    # Only a record that says PROGRAM TREE says otherwise. A record that says
    # "legacy" agrees with the folders, and a tool that read it as a
    # disagreement would stop the hub's own sync on a machine that is exactly
    # what it claims to be.
    if record.get("layout") == LAYOUT_PROGRAM or record.get("partition"):
        return False                           # a record says otherwise
    hub = (record.get("roots") or {}).get("orchestrator")
    if not hub:
        return False
    hub = Path(str(hub)).expanduser()
    if (hub / "sync" / "sync.py").is_file():
        return False                           # the hub carries a sync package
    if (hub / ".git").exists():
        return False                           # the hub is a git working tree
    return True


RESOLVER = None
RESOLVER_FILE = ""
RESOLVER_NOTE = None      # the one line the fallback prints, when it fires
STARTUP_STOP = None       # one plain sentence when this run must not proceed
LAYOUT = LAYOUT_LEGACY
HUB = None
BRAIN = HERE
SYNC_DIR = HERE
MACHINE_FILE = HERE / "machine.json"
MANIFEST_FILE = HERE / "sync-manifest.json"
BASE_MANIFEST_FILE = HERE / BASE_MANIFEST_NAME
REPO_ROOT = HERE          # the older name for the brain repo; kept on purpose


def _user_manifest(brain):
    """The user's own manifest in the brain: the name that is there, else the
    name a new one gets."""
    for name in USER_MANIFEST_NAMES:
        if (brain / name).is_file():
            return brain / name
    return brain / USER_MANIFEST_NAMES[0]


def _resolve():
    """Read the record once and set every path this file works from."""
    global RESOLVER, RESOLVER_FILE, RESOLVER_NOTE, STARTUP_STOP, LAYOUT, HUB
    global BRAIN, SYNC_DIR, MACHINE_FILE, MANIFEST_FILE, BASE_MANIFEST_FILE
    global REPO_ROOT
    RESOLVER_NOTE, STARTUP_STOP = None, None
    RESOLVER, RESOLVER_FILE = _load_resolver()
    if RESOLVER is None:
        if _positively_legacy():
            record = _plain_json(HERE / "machine.json") or {}
            LAYOUT = LAYOUT_LEGACY
            HUB = Path(str((record.get("roots") or {}).get("orchestrator")))
            BRAIN = SYNC_DIR = HERE
            MACHINE_FILE = HERE / "machine.json"
            MANIFEST_FILE = _user_manifest(HERE)
            BASE_MANIFEST_FILE = None
            REPO_ROOT = BRAIN
            RESOLVER_NOTE = ("the path resolver could not be loaded from %s, so this run used "
                             "this folder's own names — the brain sync is unaffected."
                             % (RESOLVER_FILE or "the hub"))
            return
        STARTUP_STOP = ("the path resolver could not be loaded from %s, and this is not a "
                        "plain older installation, so there is no safe answer to where the "
                        "brain is. Nothing was read or written. Run: %s %s --repair"
                        % (RESOLVER_FILE or "the hub's tools folder", py_word(),
                           (HERE / "install.py")))
        return
    record = RESOLVER.paths(tool_file=__file__)
    if record.get("problems"):
        STARTUP_STOP = record["problems"][0]
        return
    LAYOUT = record["layout"] or LAYOUT_LEGACY
    HUB = record["hub"]
    SYNC_DIR = HERE                 # carrier_preflight.py sits beside this file
    MACHINE_FILE = record["machine_file"] or (
        (HUB / "machine.json") if LAYOUT == LAYOUT_PROGRAM else HERE / "machine.json")
    brain = record["brain"]
    if brain is None:
        if LAYOUT == LAYOUT_PROGRAM:
            BRAIN = None
        else:
            BRAIN = HERE
    else:
        BRAIN = Path(brain)
    if BRAIN is not None:
        MANIFEST_FILE = _user_manifest(BRAIN)
        REPO_ROOT = BRAIN
    BASE_MANIFEST_FILE = (SYNC_DIR / BASE_MANIFEST_NAME
                          if LAYOUT == LAYOUT_PROGRAM else None)


def _brain_or_stop():
    """The brain folder, or one plain sentence saying why there is none."""
    if STARTUP_STOP:
        raise SyncStop(STARTUP_STOP)
    if BRAIN is None:
        raise SyncStop("this hub is a program tree but %s records no brain folder, so there "
                       "is nothing to sync with. Run: %s %s --repair"
                       % (MACHINE_FILE, py_word(), SYNC_DIR / "install.py"))
    return BRAIN


# What this program calls itself when it speaks. The folder the older layout
# keeps it in is NOT its name: that name is written down in exactly one place,
# the resolver, and a banner is not a path.
PROGRAM_NAME = "exocortex-sync"

ROOT_KEYS = ("orchestrator", "projects", "claude", "home")

# Never walked, whatever the manifest says. Build noise each machine makes for
# itself: a .pyc compiled here is worthless on the other machine, and a
# machine could otherwise stage orchestrator/__pycache__/*.pyc into the repo.
#
# `.git` joins the list BY BASENAME: a repository folder OR
# a gitdir file, at ANY depth. walk_tree tests the name before it descends, so
# the folder is PRUNED rather than walked object by object. A mirror that
# swallowed a nested repository would record it as a gitlink and the brain
# would quietly stop syncing. It changes nothing where no nested repository
# exists, which is why it applies in both layouts.
ALWAYS_EXCLUDE = ("__pycache__", "__pycache__/**", "*.pyc", ".git", ".git/**")

# The signals the fleet runs on: written atomically by a tool that pushes right
# after writing, so a half-written copy is not the risk - a late one is. These
# never wait for the settling window. fnmatch against the relative path with
# forward slashes; a pattern with a "/" matches at any depth (is_signal).
# post-*.json joined them with the postman: it says whether a letter has been read,
# and a sender is told "not read yet" at five minutes - a post file that waited
# out the settling window would make that sentence a lie on the other machine.
SIGNAL_FILES = (
    "INBOX.md",
    "IDEAS.md",
    "claims.json",
    "live-*.json",
    "live-sessions-*.json",
    "carriers-*.json",
    "drive-protect.json",
    "dossier/TAUGHT.md",
    "watchers/*-PROPOSALS-*.md",
    "issues-*.json",
    "issues-log-*.jsonl",
    "post-*.json",
    "usage-*-*-*.json",       # a usage meter — a PAUSE must reach the other machine now
)

# Files ONE machine writes and the other machine only carries: live is the
# truth by construction on the owner, so a repo copy that drifted from the
# record is never a conflict — the next push overwrites it. carrier_preflight.py
# rewrites carriers-<machine>.json on EVERY pull, before the compare, so its
# live side has "moved" on every beat; were the record to fall behind the
# repo copy the file would conflict forever. Every signal file a machine writes
# for itself belongs here. Matched against the path inside the hub's entry; a
# pattern with no "/" matches a top-level file only. {machine} is the owner's
# name. carry/projects.json is shared, not owned; carry/cache-*.json and *.log
# never sync at all (the manifest's excludes).
MACHINE_OWNED = (
    "carriers-{machine}.json",
    "usage-{machine}-*.json",                 # meters
    "ear-{machine}-*.json",
    "live-{machine}.json",
    "live-{machine}-*.json",
    "live-sessions-{machine}.json",
    "post-{machine}.json",
    "mail-marks-{machine}.json",
    "hygiene-archive-queue-{machine}.json",
    "hygiene-keep-{machine}.json",
    "landings-{machine}.json",
    "paths-ack-{machine}.json",
    "heads-{machine}.json",
    "logins-{machine}.json",
    "buttonup-state-{machine}.json",
    "buttonup-state-{machine}.prev.json",
    "guard-{machine}.json",
    "held-{machine}.json",
    "issues-{machine}.json",
    "issues-log-{machine}.jsonl",
    "roots-{machine}.json",
    "sync-verdict-{machine}.json",
    "carry/crossings/{machine}/**",
    "carry/state/*/{machine}/**",
    "carry/backups/{machine}/**",
)

# more of this machine's own files than this gone from the live side
# in ONE run reads as a lost folder (a wiped hub, a `git clean`), never as a
# takedown: none is taken down, each is decided by the ordinary rule (a call,
# or a pull when there is no record), and one line says so.
OWNER_GONE_CAP = 12

# Seconds a changed file must have been still before a push carries it: every
# push carries every changed file in the hub, and the pulse pushes every five
# minutes, so a file being written when the beat lands would otherwise cross
# half-written.
SETTLE_DEFAULT = 60

# Attempts at `git push` before a rejection is a real failure.
PUSH_RETRIES_DEFAULT = 3

# a failed push leaves its hub a letter only once the failure has outlived
# what usually heals it. The pulse pushes about every five minutes, and an ordinary
# bad minute — a DNS hiccup, an HTTP 408, a merge clash — is repaired by the very next
# beat (a day of three such failures was), so the letter waits for THREE failed beats
# running or HALF AN HOUR of failing, whichever comes first. The screen still says
# every failure at once. ORCHSYNC_PUSH_LETTER_AFTER / ORCHSYNC_PUSH_LETTER_MINUTES
# override the two, the way ORCHSYNC_PUSH_RETRIES overrides the attempts.
PUSH_LETTER_AFTER_DEFAULT = 3
PUSH_LETTER_MINUTES_DEFAULT = 30

# The tail a push that LANDS writes onto every failed-push letter it closes:
# ` · resolved: <ISO to the minute> by the push that landed`. Spelled here and once
# in tools/mail.py (its RESOLVED_MARK, whose comment names this one); the two files
# have no import between them, on purpose.
RESOLVED_MARK = " · resolved:"
RESOLVED_BY = "by the push that landed"

# Names Windows refuses. Reported by `status`, never silently mangled.
WIN_BAD_CHARS = set('<>:"|?*')
WIN_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def age_phrase(then):
    """Human age of a timezone-aware datetime."""
    if then is None:
        return "unknown"
    now = datetime.datetime.now(datetime.timezone.utc)
    if then.tzinfo is None:
        then = then.replace(tzinfo=datetime.timezone.utc)
    delta = now - then
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "in the future (clock skew)"
    if seconds < 90:
        return "%d seconds ago" % seconds
    minutes = seconds // 60
    if minutes < 90:
        return "%d minutes ago" % minutes
    hours = minutes // 60
    if hours < 48:
        return "%d hours ago" % hours
    return "%d days ago" % (hours // 24)


def read_json(path, default=None):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def read_text(path):
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()      # newline="": a file's own line endings survive the merge
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def sha256_of(path):
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 256)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def mtime_of(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def py_word():
    """`python` or `python3` - the word a human types on THIS machine.

    Read off the running interpreter, the way install.py chooses it, so a
    command printed for the reader is the command that works where they read it.
    """
    stem = Path(sys.executable or "").stem.lower()
    if stem.startswith("python3"):
        return "python3"
    if stem in ("python", "pythonw"):
        return "python"
    return "python" if os.name == "nt" else "python3"


def _env_int(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print("  i  %s=%r is not a number — using %d" % (name, raw, default))
        return default


def munge(text):
    """Claude Code's project-directory munge: every non-alphanumeric -> '-'.

    /home/you/Projects/Some Project -> -home-you-Projects-Some-Project
    C:\\Users\\You\\Projects\\Foo      -> C--Users-You-Projects-Foo
    """
    return re.sub(r"[^A-Za-z0-9]", "-", text)


def windows_unsafe(rel):
    """Return a reason string if this relative posix path cannot exist on
    Windows, else None."""
    for part in rel.split("/"):
        if not part:
            continue
        if any(char in WIN_BAD_CHARS for char in part):
            return "illegal character in %r" % part
        if part.endswith(" ") or part.endswith("."):
            return "trailing space/dot in %r" % part
        stem = part.split(".")[0].upper()
        if stem in WIN_RESERVED:
            return "reserved device name %r" % part
    return None


# The shim runs here, once, before any verb: every name below is read from
# what it sets. Nothing is written and nothing is printed by it.
_resolve()


# --------------------------------------------------------------------------
# machine identity and live-path resolution
# --------------------------------------------------------------------------

def test_root():
    value = os.environ.get("ORCHSYNC_TEST_ROOT", "").strip()
    return Path(value).resolve() if value else None


# --------------------------------------------------------------------------
# one transaction per checkout, including the state record and git mutations
# --------------------------------------------------------------------------

class SyncBusy(Exception):
    """The caller has not entered the transaction; nothing was synced."""


def transaction_lock_path():
    root = test_root()
    if root is not None:
        return root / ".exocortex-sync.lock"
    git_dir = REPO_ROOT / ".git"
    if git_dir.is_dir():
        return git_dir / "exocortex-sync.lock"
    # A program tree: the engine folder has no .git of its own (a stranger's
    # install). The lock sits beside the tool, never under a folder
    # that does not exist, so the first pull never dies on FileNotFoundError.
    return REPO_ROOT / ".exocortex-sync.lock"


def _pid_alive(pid):
    # Never send a signal to a process group from malformed lock metadata.
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return True
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.windll.kernel32
        op = kernel.OpenProcess
        op.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        op.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        try:
            handle = op(0x1000, False, pid)
        except PermissionError:
            return True
        if not handle:
            # ACCESS_DENIED is evidence of a holder, not permission to steal.
            return kernel.GetLastError() == 5
        close(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OverflowError):
        return True
    return True


def _lock_snapshot(path):
    """Read metadata and identity from the SAME open file, even across rename."""
    try:
        with path.open("rb") as handle:
            stat = os.fstat(handle.fileno())
            raw = handle.read()
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError):
            record = {}
        if not isinstance(record, dict):
            record = {}
        return record, stat
    except FileNotFoundError:
        return None


def _same_lock(path, stat):
    try:
        current = path.stat()
        return (current.st_dev, current.st_ino, current.st_mtime_ns,
                current.st_size) == (stat.st_dev, stat.st_ino, stat.st_mtime_ns,
                                     stat.st_size)
    except FileNotFoundError:
        return False


def _lock_age(record, stat):
    try:
        started = datetime.datetime.fromisoformat(record["started"].replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=datetime.timezone.utc)
        return max(0, time.time() - started.timestamp()), started.strftime("%H:%M:%S")
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        # A killed writer can leave an empty/partial line. Give a writer time
        # to finish; an unreadable orphan is reclaimable by the age limit.
        return max(0, time.time() - stat.st_mtime), "?"


# The gate may install a callback on an imported module. No hook is run by an
# ordinary invocation, even if a caller has assigned this module attribute.
_transaction_lock_test_hook = None


def _lock_hook(event, path, record):
    if os.environ.get("ORCHSYNC_LOCK_TEST_HOOK") and _transaction_lock_test_hook:
        _transaction_lock_test_hook(event, path, record)


def _lock_identity(record):
    return record.get("pid"), record.get("started")


def _create_lock_record(path, record):
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    # Close before dispatch: an expired Windows holder must permit rename.
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        try:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
        except BaseException:
            owned = os.fstat(handle.fileno())
            handle.close()
            if _same_lock(path, owned):
                path.unlink(missing_ok=True)
            raise


def _clear_stale_reclaim(marker):
    snapshot = _lock_snapshot(marker)
    if snapshot is None:
        return
    record, stat = snapshot
    age, _ = _lock_age(record, stat)
    pid = record.get("pid", "?")
    if (not _pid_alive(pid) or age > 60) and _same_lock(marker, stat):
        try:
            marker.unlink()
        except FileNotFoundError:
            return
        print("  lock: cleared a stale reclaim marker (pid %s)" % pid, flush=True)


def _reclaim_lock(path, marker, holder, record, age, dead):
    """Only the exclusive marker's creator may rename the judged holder."""
    claim = {"pid": os.getpid(), "started": datetime.datetime.now(
        datetime.timezone.utc).isoformat(),
        "stale_pid": holder.get("pid"), "stale_started": holder.get("started")}
    try:
        _create_lock_record(marker, claim)
    except FileExistsError:
        return False
    try:
        _lock_hook("reclaim_claimed", path, claim)
        current = _lock_snapshot(path)
        if current is None or _lock_identity(current[0]) != _lock_identity(holder):
            return False
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        stale = path.with_name("exocortex-sync.lock.stale-%s-%s" % (stamp, os.getpid()))
        if stale.exists():
            stale = path.with_name(stale.name + "-%s" % time.time_ns())
        try:
            path.rename(stale)
        except FileNotFoundError:
            return False
        reason = "not running" if dead else "past 30-minute limit"
        print("  lock: broke a stale lock (pid %s %s, held %d min)"
              % (holder.get("pid", "?"), reason, age // 60), flush=True)
        # Exclusive create still protects against an older sync implementation
        # that does not honour the marker during the rename/create gap.
        try:
            _create_lock_record(path, record)
        except FileExistsError:
            return False
        return True
    finally:
        current = _lock_snapshot(marker)
        if current is not None and _lock_identity(current[0]) == _lock_identity(claim):
            marker.unlink(missing_ok=True)


@contextmanager
def transaction_lock(verb):
    if os.environ.get("ORCHSYNC_LOCK_HELD") == str(os.getppid()):
        yield
        return
    try:
        wait = float(os.environ.get("ORCHSYNC_LOCK_WAIT", "90"))
        if not 0 <= wait < float("inf"):
            raise ValueError()
    except ValueError:
        raise SyncStop("ORCHSYNC_LOCK_WAIT must be a finite, non-negative number")
    path = transaction_lock_path()
    # A test world may not exist yet. Never manufacture a missing real .git.
    if test_root() is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
    began = time.monotonic()
    next_progress = 10
    marker = path.with_name(path.name + ".reclaim")
    machine = _plain_json(MACHINE_FILE) or {}
    while True:
        record = {"pid": os.getpid(), "machine": machine.get("name", "?"),
                  "verb": verb, "started": datetime.datetime.now(
                      datetime.timezone.utc).isoformat(), "hostname": platform.node()}
        _clear_stale_reclaim(marker)
        # Respect the marker even while the stale path is temporarily absent.
        claiming = _lock_snapshot(marker)
        if claiming is None:
            try:
                _create_lock_record(path, record)
                break
            except FileExistsError:
                pass
        snapshot = _lock_snapshot(path)
        if snapshot is not None:
            holder, stat = snapshot
            age, since = _lock_age(holder, stat)
            pid = holder.get("pid", "?")
            dead = not _pid_alive(pid)
            if claiming is None and (dead or age > 30 * 60):
                _lock_hook("stale_judged", path, holder)
                if _reclaim_lock(path, marker, holder, record, age, dead):
                    break
        elif claiming is not None:
            holder, stat = claiming
            age, since = _lock_age(holder, stat)
            pid = holder.get("pid", "?")
        else:
            continue
        elapsed = time.monotonic() - began
        held_verb = holder.get("verb", "reclaim" if claiming else "unknown")
        if elapsed >= wait:
            raise SyncBusy("sync: busy — %s held by pid %s for %d s; "
                           "nothing was copied or committed; run it again"
                           % (held_verb, pid, age))
        if elapsed >= next_progress:
            print("  lock: waiting for %s by pid %s since %s (%d s)"
                  % (held_verb, pid, since, elapsed), flush=True)
            next_progress += 10
        time.sleep(min(0.5, wait - elapsed))
    previous = os.environ.get("ORCHSYNC_LOCK_HELD")
    try:
        os.environ["ORCHSYNC_LOCK_HELD"] = str(os.getpid())
        _lock_hook("acquired", path, record)
        if os.environ.get("EXO_GATE_SYNC_LOCK") == "1":
            time.sleep(max(0, float(os.environ.get("ORCHSYNC_LOCK_SLEEP", "0"))))
        yield
    finally:
        if previous is None:
            os.environ.pop("ORCHSYNC_LOCK_HELD", None)
        else:
            os.environ["ORCHSYNC_LOCK_HELD"] = previous
        # An age-expired holder must not unlink its successor's lock. Compare
        # the published ownership record, including in-place replacements.
        _lock_hook("before_release", path, record)
        current = _lock_snapshot(path)
        if current is not None and _lock_identity(current[0]) == _lock_identity(record):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        elif current is not None:
            print("  lock: not mine at release (pid %s) — left in place"
                  % current[0].get("pid", "?"), flush=True)


def state_file():
    """Test runs keep their own bookkeeping so a rehearsal can never make the
    real files look out of date."""
    return REPO_ROOT / (".sync-state.test.json" if test_root()
                        else ".sync-state.json")


def redirect(path):
    """Apply ORCHSYNC_TEST_ROOT, if set, to an absolute live path."""
    root = test_root()
    if root is None:
        return path
    parts = path.parts
    if not parts:
        return path
    # parts[0] is the anchor ('/' on posix, 'C:\\' on Windows); drop it.
    tail = parts[1:] if path.is_absolute() else parts
    safe = [p.replace(":", "") for p in tail]
    return root.joinpath(*safe) if safe else root


def load_machine(required=True):
    if STARTUP_STOP:
        raise SyncStop(STARTUP_STOP)
    data = read_json(MACHINE_FILE)
    if data is None:
        if not required:
            return None
        die("no machine.json at %s — run:  %s sync.py bootstrap --machine <name>"
            % (MACHINE_FILE, py_word()))
    return data


def machine_roots(machine):
    return {key: Path(value) for key, value in machine["roots"].items()}


def live_path(machine, root_key, rel):
    base = Path(machine["roots"][root_key])
    path = base.joinpath(*[p for p in rel.split("/") if p]) if rel else base
    return redirect(path)


def die(message):
    sys.stderr.write("%s: %s\n" % (PROGRAM_NAME, message))
    sys.exit(2)


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------

# Where each merged entry came from, filled by load_manifest and printed by
# `status` when there is anything to say: base · user · both.
MANIFEST_ORIGIN = {}
MANIFEST_NOTES = []

# Two lists are EXTENDED by the user rather than replaced: adding one exclude
# of your own must not throw away the program's.
MANIFEST_EXTEND = ("exclude", "append_only")


def _merge_entry(base_entry, user_entry):
    """The program's entry with the user's on top: the user wins per field,
    except the two lists, which are the program's plus the user's."""
    merged = json.loads(json.dumps(base_entry))
    for key, value in user_entry.items():
        if key in MANIFEST_EXTEND and isinstance(value, list):
            have = list(merged.get(key) or [])
            merged[key] = have + [v for v in value if v not in have]
        else:
            merged[key] = value
    return merged


def merge_manifests(base, user):
    """base, then the user's on top, by entry id.

    The user may ADD entries and EXTEND an entry's exclude and append_only
    lists, and may override any other field of an entry. The user may NOT
    remove an entry the program ships: that is reported in one line and
    ignored, so an install can never lose the hub's own sync by editing a file.
    """
    origin, notes = {}, []
    merged = json.loads(json.dumps(base))
    entries = list(merged.get("entries") or [])
    index = dict((e.get("id"), i) for i, e in enumerate(entries) if e.get("id"))
    for eid in index:
        origin[eid] = "base"
    for entry in list((user or {}).get("entries") or []):
        eid = entry.get("id")
        if not eid:
            notes.append("an entry in %s has no id — it was ignored" % MANIFEST_FILE)
            continue
        if eid in index:
            entries[index[eid]] = _merge_entry(entries[index[eid]], entry)
            origin[eid] = "both"
        else:
            index[eid] = len(entries)
            entries.append(entry)
            origin[eid] = "user"
    merged["entries"] = entries
    for eid in list((user or {}).get("remove") or []):
        if eid in index:
            notes.append("%s asks to remove the entry %r, which the program ships: kept "
                         "(your manifest may add and extend, never remove)"
                         % (MANIFEST_FILE, eid))
    # The memories block: the program ships where it lives and what to skip;
    # the MAP itself is the user's, written by this tool and never by hand.
    mem = dict(merged.get("memories") or {})
    user_mem = dict((user or {}).get("memories") or {})
    for key, value in user_mem.items():
        if key in MANIFEST_EXTEND and isinstance(value, list):
            have = list(mem.get(key) or [])
            mem[key] = have + [v for v in value if v not in have]
        else:
            mem[key] = value
    merged["memories"] = mem
    if (user or {}).get("machines"):
        merged["machines"] = user["machines"]
    base_never = list(merged.get("never_synced") or [])
    merged["never_synced"] = base_never + [
        line for line in ((user or {}).get("never_synced") or [])
        if line not in base_never]
    return merged, origin, notes


def load_manifest():
    """The manifest this run works from.

    PROGRAM TREE: the program's own manifest.base.json, with the user's
    manifest in the brain merged over it. OLDER LAYOUT: the user's manifest
    alone, exactly as it has always been — the program ships no base file
    there, and nothing about that layout changes.
    """
    global MANIFEST_ORIGIN, MANIFEST_NOTES
    MANIFEST_ORIGIN, MANIFEST_NOTES = {}, []
    if STARTUP_STOP:
        raise SyncStop(STARTUP_STOP)
    base = None
    if BASE_MANIFEST_FILE is not None and Path(BASE_MANIFEST_FILE).is_file():
        base = read_json(Path(BASE_MANIFEST_FILE))
        if base is None:
            die("the program's %s could not be read at %s"
                % (BASE_MANIFEST_NAME, BASE_MANIFEST_FILE))
    data = read_json(MANIFEST_FILE)
    if base is None:
        if data is None:
            die("sync-manifest.json missing or unreadable at %s" % MANIFEST_FILE)
        MANIFEST_ORIGIN = dict((e.get("id"), "user")
                               for e in (data.get("entries") or []) if e.get("id"))
        return data
    merged, MANIFEST_ORIGIN, MANIFEST_NOTES = merge_manifests(base, data or {})
    return merged


def excluded(rel, patterns):
    base = rel.split("/")[-1]
    for pattern in patterns:
        if pattern.startswith("/"):
            # Anchored at the entry's own root: THIS path, never the same name
            # deeper down (HELD_BY_NAME). No manifest writes a leading slash, so
            # nothing that was matched before is matched differently now.
            if fnmatch.fnmatch(rel, pattern[1:]):
                return True
            continue
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
            continue
        if "/" in pattern:
            if fnmatch.fnmatch(rel, pattern):
                return True
            continue
        if fnmatch.fnmatch(base, pattern) or fnmatch.fnmatch(rel, pattern):
            return True
    return False


def walk_tree(root, patterns):
    """Relative posix paths of every file under root, excludes applied."""
    patterns = list(patterns) + list(ALWAYS_EXCLUDE)
    found = []
    if not root.is_dir():
        return found
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for entry in entries:
            rel = entry.relative_to(root).as_posix()
            if excluded(rel, patterns):
                continue
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                found.append(rel)
    return sorted(found)


# --------------------------------------------------------------------------
# the partition — three classes, switched on by the record
#
# BRAIN   what git ignores          rides this sync
# PROGRAM what git tracks           rides git
# PENDING untracked and un-ignored  rides NEITHER, and is named until it is
#                                   committed or moved
#
# Never a guess. git itself is the selector, its ignore sources are closed
# first, and a probe checks that its answers still mean what they meant. Any
# check that fails stops the HUB ENTRY alone, in one plain sentence with the
# owner and the next action; every other entry still syncs.
# --------------------------------------------------------------------------

# This machine's own files. Applied to the hub entry's BOTH walks before
# anything is compared, in BOTH layouts; with the
# partition on, before git is asked too. The pages each machine
# draws for itself are named exactly — never a broad *.html, which would take a
# page somebody wrote by hand.
NEVER_SYNC = (
    "machine.json",
    "installed.json",
    "scratch/**",
    ".git/**",
    ".claude/settings.local.json",
    ".claude/*.lock",
    "__pycache__/**",
    "*.pyc",
    # The installer's own lock, which lives inside the program's folder for the
    # length of one run: this machine's, transient, and nobody else's business.
    "sync/install/.lock",
    "board*.html",
    "tree.html",
    "improvements.html",
)

# HELD FOR THE HUB'S RULING. In the older
# layout the list above is NEW, and two of its names match by basename at any
# depth: the hub's notebook holds release/src/templates/installed.json, a
# template the brain has always carried. Until the hub rules, the older layout
# reads these two names at the TOP of the hub folder only, so the notebook's
# copies keep syncing exactly as before and --prune-local never removes them.
# The program tree's partition reads the list exactly as it always has.
HELD_BY_NAME = ("machine.json", "installed.json")

# What the hub entry applied this run, for `status`, `--prune-local` and the
# state record. Reset by build_units; empty when the hub's entry did not sync.
MACHINE_LOCAL = {}


def machine_local_patterns(partition_on):
    """The never-sync list as the hub entry applies it: the partition reads it
    as written; the older layout anchors the held names at the hub's top."""
    if partition_on:
        return tuple(NEVER_SYNC)
    return tuple(("/" + p) if p in HELD_BY_NAME else p for p in NEVER_SYNC)


CLASS_BRAIN = "brain"
CLASS_PROGRAM = "program"
CLASS_PENDING = "pending"
CLASS_NEVER = "never-sync"

# What git must still say, every time, or the whole answer is refused.
PROBE_BRAIN = ("STATUS.md", "INBOX.md")
PROBE_PROGRAM = ("sync/sync.py", "tools/exo_paths.py")

REPAIR_HINT = "re-run `%s sync/install.py --repair`"

# The last partition answer, for `status` to print. Reset by build_units.
PARTITION_REPORT = {}


class PartitionFailure(Exception):
    """One plain sentence. It stops the hub's entry, and nothing else."""


def _empty_excludes_file():
    """An empty file, so a global ignore list cannot colour git's answer.

    Same name every run and always empty, so two machines and two processes
    can share it without racing."""
    target = Path(tempfile.gettempdir()) / "exocortex-empty-excludes"
    try:
        if not target.is_file() or target.stat().st_size:
            # Written again whenever it is not empty: the promise is that this
            # file adds no rule, and a shared temporary folder is not a place
            # to take that on trust.
            with target.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write("")
    except OSError:
        return None
    return target


def hub_git(hub, args, stdin=None):
    """git, run in the hub, with the global ignore list neutralised for the
    call -> (code, stdout bytes, stderr text)."""
    cmd = ["git"]
    empty = _empty_excludes_file()
    if empty is not None:
        # Forward slashes on purpose: git reads a backslash in a configuration
        # value as an escape, and Windows paths are full of them.
        cmd += ["-c", "core.excludesFile=%s" % str(empty).replace("\\", "/")]
    cmd += ["-C", str(hub)] + [str(a) for a in args]
    proc = subprocess.run(cmd, input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout or b"",
            (proc.stderr or b"").decode("utf-8", "replace").strip())


def _nul_list(blob):
    return [part.decode("utf-8", "replace") for part in blob.split(b"\0") if part]


def check_ignore(hub, rels, no_index=False):
    """{rel: is it ignored} — git's own verdict on every path, in one call.

    Exit 0 (some were ignored) and exit 1 (none were) are both answers. Any
    other status is a failure, and a failure is NEVER read as "carry
    everything": it stops the hub's entry instead."""
    rels = list(rels)
    if not rels:
        return {}
    payload = b"".join(rel.encode("utf-8") + b"\0" for rel in rels)
    args = ["check-ignore", "--stdin", "-z"]
    if no_index:
        args.insert(1, "--no-index")
    code, out, err = hub_git(hub, args, stdin=payload)
    if code not in (0, 1):
        raise PartitionFailure(
            "git could not say which of this folder's files it ignores (%s), so the hub's "
            "sync stopped rather than guess: %s"
            % (("exit %d" % code), " ".join((err or "no message from git").split())[:160]))
    ignored = set(_nul_list(out))
    return dict((rel, rel in ignored) for rel in rels)


def tracked_paths(hub):
    code, out, err = hub_git(hub, ["ls-files", "-z"])
    if code != 0:
        raise PartitionFailure(
            "git could not list the files it tracks in this folder, so the hub's sync "
            "stopped rather than guess: %s"
            % " ".join((err or "no message from git").split())[:160])
    return set(_nul_list(out))


def partition_checks(hub, tracked):
    """Every ignore source closed and every promise checked. -> [sentences]."""
    problems = []
    py = py_word()

    # 1 — a file git tracks that a positive ignore rule also matches. The two
    #     disagree, so neither carrier is certain of it. --no-index is used to
    #     ASK this question; it is never the selector itself.
    if tracked:
        forced = [rel for rel, hit in
                  check_ignore(hub, sorted(tracked), no_index=True).items() if hit]
        for rel in sorted(forced)[:20]:
            problems.append(
                "%s is tracked by git AND matched by an ignore rule, so it is not clear "
                "which carrier owns it. Yours to settle: untrack it, or take the rule out. "
                "Then %s" % (rel, REPAIR_HINT % py))

    # 2 — the rule file itself: tracked, and the same bytes the program shipped.
    code, _out, _err = hub_git(hub, ["ls-files", "--error-unmatch", "-z", "--", ".gitignore"])
    if code != 0:
        problems.append(
            ".gitignore at the top of this folder is not tracked by git, and that one file "
            "is what says which of your files are yours. Yours to settle: %s"
            % (REPAIR_HINT % py))
    else:
        code, out, _err = hub_git(hub, ["status", "--porcelain", "-z", "--", ".gitignore"])
        if code == 0 and _nul_list(out):
            problems.append(
                ".gitignore at the top of this folder has been changed since the program "
                "shipped it, so the partition it describes is no longer the one that was "
                "reviewed. Yours to settle: commit the change, or restore it with "
                "`git checkout -- .gitignore`. Then %s" % (REPAIR_HINT % py))

    # 3 — the second ignore source, the one that lives inside .git and syncs
    #     with nothing: any active line in it is invisible to everyone else.
    code, out, _err = hub_git(hub, ["rev-parse", "--absolute-git-dir"])
    gitdir = out.decode("utf-8", "replace").strip() if code == 0 else ""
    if gitdir:
        exclude = Path(gitdir) / "info" / "exclude"
        text = read_text(exclude)
        active = [line.strip() for line in (text or "").splitlines()
                  if line.strip() and not line.strip().startswith("#")]
        if active:
            problems.append(
                "%s carries %d active ignore line(s) (%s), which change what belongs to "
                "whom on this machine only. Yours to settle: take them out, or put the rule "
                "in .gitignore where the other machine can see it. Then %s"
                % (exclude, len(active), ", ".join(active[:3]), REPAIR_HINT % py))

    # 4 — a nested rule file nobody reviewed: git reads it, and it can hide a
    #     program file from git without hiding it from anyone else.
    code, out, _err = hub_git(hub, ["ls-files", "-o", "--exclude-standard", "-z"])
    if code == 0:
        for rel in _nul_list(out):
            if rel.split("/")[-1] == ".gitignore":
                problems.append(
                    "%s is an ignore file inside the program's own folders and git has not "
                    "been told about it, so what it hides is known only here. Yours to "
                    "settle: commit it or remove it. Then %s" % (rel, REPAIR_HINT % py))

    # 5 — the probe: the answers still mean what they meant.
    probe = check_ignore(hub, list(PROBE_BRAIN) + list(PROBE_PROGRAM))
    wrong = [rel for rel in PROBE_BRAIN if not probe.get(rel)]
    wrong += [rel for rel in PROBE_PROGRAM if probe.get(rel)]
    if wrong:
        problems.append(
            "git's ignore rules no longer sort this folder the way the program expects "
            "(%s answered the wrong way), so the hub's sync stopped rather than carry the "
            "wrong files. Yours to settle: %s" % (", ".join(sorted(wrong)), REPAIR_HINT % py))
    return problems


def partition_classes(hub, rels, live_rels):
    """{rel: which carrier owns it} for every path of the hub's entry."""
    out = {}
    ask = []
    for rel in sorted(rels):
        if excluded(rel, NEVER_SYNC):
            # Both walks already pruned these before anything got here. The
            # test stays as the second line of defence: never-sync is applied
            # BEFORE the selector, wherever a path came from.
            out[rel] = CLASS_NEVER
        else:
            ask.append(rel)
    tracked = tracked_paths(hub)
    verdict = check_ignore(hub, ask)
    for rel in ask:
        if verdict.get(rel):
            out[rel] = CLASS_BRAIN
        elif rel in tracked or rel not in live_rels:
            # Tracked is the program's. A path that is only in the mirror and
            # is not ignored is a program copy the mirror is still holding: it
            # is the program's too, and taking it out of the mirror is its own
            # deliberate command, never a side effect of a sync.
            out[rel] = CLASS_PROGRAM
        else:
            out[rel] = CLASS_PENDING
    return out, tracked


def partition_mode(machine):
    """('on' | 'off' | a sentence that stops the hub's entry).

    A program tree REQUIRES a valid activation record: with
    none, the hub's entry stops and the brain is neither emptied nor mirrored
    whole. Only a POSITIVELY identified older installation carries the hub
    whole, and only it needs no record.
    """
    py = py_word()
    if LAYOUT == LAYOUT_PROGRAM:
        if (machine or {}).get("partition") != PARTITION_GIT:
            return ("%s does not say how this hub folder is divided between the program and "
                    "your own files, and this folder is a program tree, so the hub's sync "
                    "stopped rather than carry the wrong half. Yours to settle: %s"
                    % (MACHINE_FILE, REPAIR_HINT % py))
        return "on"
    if not _positively_legacy():
        return ("this installation is neither a plain older one nor a program tree with a "
                "partition on record, so which files belong to the brain is not settled and "
                "the hub's sync stopped. Yours to settle: %s" % (REPAIR_HINT % py))
    return "off"


def pending_warning(rel):
    """The standing line a file that rides neither carrier earns.

    Deny by default means every such file is inside one of the program's own
    folders, so the sentence can always name the way out."""
    folder = rel.split("/")[0] + "/" if "/" in rel else "the program's folders"
    return ("%s sits in the program's folder: it will not sync and an update may refuse "
            "to run — move it anywhere outside %s (the rest of this folder is yours), or "
            "commit it to the program." % (rel, folder))


def is_hub_entry(entry):
    """The one entry whose live folder IS the hub."""
    live = entry.get("live") or {}
    return live.get("root") == "orchestrator" and not (live.get("rel") or "")


# --------------------------------------------------------------------------
# memory discovery / un-munging
# --------------------------------------------------------------------------

def unmunge(munged, roots):
    """Resolve a ~/.claude/projects/<munged> name to (root_key, rel).

    Matches against this machine's recorded roots, most specific first, then
    walks the real filesystem so that real names (spaces, apostrophes, dots)
    come back intact. Returns (root_key, rel) or (None, None).
    """
    candidates = []
    for key in ROOT_KEYS:
        root = roots.get(key)
        if root is None:
            continue
        stem = munge(str(root))
        if munged == stem:
            candidates.append((key, ""))
            continue
        if munged.startswith(stem + "-"):
            remainder = munged[len(stem):]  # keeps the leading '-'
            for path in _descend(root, remainder):
                rel = path.relative_to(root).as_posix()
                candidates.append((key, rel))
    if not candidates:
        return None, None
    # Most specific root wins (ROOT_KEYS order), then the shallowest path.
    candidates.sort(key=lambda item: (ROOT_KEYS.index(item[0]),
                                      item[1].count("/"), item[1]))
    return candidates[0]


def _descend(current, remainder):
    """Every existing directory under `current` whose munged relative path
    equals `remainder` (which starts with '-')."""
    results = []
    if remainder == "":
        return [current]
    if not remainder.startswith("-"):
        return results
    rest = remainder[1:]
    try:
        entries = [e for e in current.iterdir() if e.is_dir()]
    except OSError:
        return results
    for entry in entries:
        stem = munge(entry.name)
        if not stem:
            continue
        if rest == stem:
            results.append(entry)
        elif rest.startswith(stem + "-"):
            results.extend(_descend(entry, rest[len(stem):]))
    return results


def unmunge_string(munged, roots):
    """Reverse a munged dir name against the projects root, by string only.

    unmunge() walks the real filesystem, so it can only resolve a project that
    exists here. A memory pulled for a project this machine has not cloned yet
    has no folder on disk — and the next push must not stage it back into the
    repo under its raw munged name. Pure string work
    keeps push the inverse of pull whether the folder is there or not.

    Deliberately the projects root ONLY: a home-rooted dir that unmunge()
    could not resolve (Desktop scratch, an orphan from a wrong-root bootstrap)
    is this machine's business and must never be invented into the repo.
    """
    root = roots.get("projects")
    if root is None:
        return None, None
    stem = munge(str(root))
    if munged == stem:
        return "projects", ""
    if munged.startswith(stem + "-"):
        rest = munged[len(stem) + 1:]
        if rest:
            # One level down: memories live in <projects>/<project>/. The real
            # folder name may hold spaces this cannot recover, which is why
            # known_munged() gets first refusal.
            return "projects", rest
    return None, None


def expected_munged(roots, root_key, rel):
    """The dir name THIS machine would use for a memory record — no disk."""
    if not root_key or rel is None:
        return None
    root = roots.get(root_key)
    if root is None:
        return None
    target = root.joinpath(*[p for p in rel.split("/") if p]) if rel else root
    return munge(str(target))


def known_munged(machine, memory_map, repo_memories):
    """{live dir name: (logical, root_key, rel)} for memories the repo knows.

    Built by re-munging this machine's roots, which is exactly how pull picks
    a live directory — so anything pull wrote, push reads back under the same
    logical name, spaces and all, without touching the filesystem.
    """
    roots = machine_roots(machine)
    index = {}
    for logical, record in (memory_map or {}).items():
        if not isinstance(record, dict):
            continue
        name = expected_munged(roots, record.get("root"), record.get("rel"))
        if name:
            # root/rel stay None: build_units keeps the manifest's own record.
            index.setdefault(name, (logical, None, None))
    projects = roots.get("projects")
    if projects is not None and repo_memories is not None \
            and repo_memories.is_dir():
        # A repo memory the map has not caught up with yet is still ours.
        for entry in sorted(repo_memories.iterdir(), key=lambda p: p.name):
            if entry.is_dir():
                index.setdefault(munge(str(projects / entry.name)),
                                 (entry.name, "projects", entry.name))
    return index


def logical_for(root_key, rel):
    """The name a NEWLY DISCOVERED memory folder takes in the repo's map.

    A folder the map already names keeps that name (discover_memories pins it
    from the map before this is asked), so nothing an existing brain already
    carries is renamed here. A root's own folder is named after the root."""
    if rel == "":
        return {"home": "HOME", "projects": "PROJECTS-ROOT",
                "claude": "CLAUDE-ROOT"}.get(root_key, root_key.upper())
    return rel.split("/")[-1]


def private_memory_lane(roots, root_key, rel):
    """The private lane a memory dir belongs to, or None. A lane the owner marked
    private (its STATUS `privacy: private`, or the registry) keeps its memory on its own
    machine: the dir is never staged, so the brain never carries it. The hub's exo_privacy.py
    answers; a hub without it marks nothing private.
    ASSUMES: a memory dir maps to the project folder it was made in. Opposite: an ordinary
    project's memory is staged as before (gate-privacy C10b)."""
    if not rel or root_key is None:
        return None
    base, hub = roots.get(root_key), roots.get("orchestrator")
    if base is None or hub is None:
        return None
    try:
        tools = str(Path(hub) / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from exo_privacy import private_lane_of
        return private_lane_of(cwd=str(Path(base) / rel), hub=str(hub))
    except Exception:
        return None


def discover_memories(machine, memory_map=None, repo_memories=None):
    """Scan ~/.claude/projects for dirs that HAVE a memory/ subdir.

    Returns ({logical: {"root":..., "rel":..., "munged": <dir name>}}, notes).

    A live dir is resolved in this order:
      1. the repo's own map, re-munged for this machine — the exact inverse of
         pull, so a pull followed by a push stages nothing;
      2. unmunge(), which walks the filesystem and recovers real folder names;
      3. a string un-munge under the projects root, for a project this machine
         has not cloned;
      4. otherwise it is machine-local and is left alone. It is NEVER staged
         into the repo under its raw munged name — that would duplicate
         every canonical memory on the other machine.
    """
    roots = machine_roots(machine)
    projects_dir = redirect(roots["claude"] / "projects")
    found = {}
    notes = []
    if not projects_dir.is_dir():
        return found, notes
    index = known_munged(machine, memory_map, repo_memories)
    # Dirs the repo already carries under a name of their own, from before
    # any of this: they keep syncing, they are simply not re-derived here.
    tracked = set()
    for record in (memory_map or {}).values():
        if isinstance(record, dict):
            tracked.add((record.get("munged") or {}).get(machine["name"]))
    rows = []
    for entry in sorted(projects_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if not (entry / "memory").is_dir():
            continue
        pinned = index.get(entry.name)
        if pinned is not None:
            logical, root_key, rel = pinned
            if private_memory_lane(roots, root_key, rel):
                notes.append("memory dir %r: a private lane's memory — kept on this machine, "
                             "never staged" % entry.name)
                continue
            rows.append((entry.name, root_key, rel, logical))
            continue
        root_key, rel = unmunge(entry.name, roots)
        if root_key is None:
            root_key, rel = unmunge_string(entry.name, roots)
        if private_memory_lane(roots, root_key, rel):
            notes.append("memory dir %r: a private lane's memory — kept on this machine, "
                         "never staged" % entry.name)
            continue
        if root_key is None:
            if entry.name in tracked:
                notes.append("memory dir %r: does not un-munge here — it goes "
                             "on syncing only because the repo already carries "
                             "it under that name" % entry.name)
            else:
                notes.append("memory dir %r: machine-local memory, left alone "
                             "(it does not un-munge under this machine's "
                             "projects root, so it is not staged into the repo)"
                             % entry.name)
            continue
        rows.append((entry.name, root_key, rel, None))
    names = {}
    for row in rows:
        name = row[3] if row[3] is not None else logical_for(row[1], row[2])
        names.setdefault(name, []).append(row)
    for name, group in names.items():
        for munged_name, root_key, rel, pinned in group:
            key = name
            # A name claimed by two live dirs is disambiguated — but a dir the
            # repo already owns keeps the name the repo gave it.
            if len(group) > 1 and pinned is None and root_key is not None:
                key = "%s--%s" % (root_key, rel.replace("/", "--") or "ROOT")
            found[key] = {
                "root": root_key,
                "rel": rel if root_key is not None else None,
                "munged": munged_name,
            }
    return found, notes


def memory_live_dir(machine, logical, record):
    """Where this logical memory lives on THIS machine, or None.

    root+rel wins over the recorded per-machine dir name: the roots are this
    machine's truth today, while a recorded name can be stale (one machine's
    first bootstrap wrote absolute names from another disk). The recorded
    name is the fallback for entries whose root could never be worked out.
    """
    roots = machine_roots(machine)
    name = expected_munged(roots, record.get("root"), record.get("rel"))
    if name is None:
        name = (record.get("munged") or {}).get(machine["name"])
    if name is None:
        return None
    return redirect(roots["claude"] / "projects" / name / "memory")


# --------------------------------------------------------------------------
# units: one syncable file, live side and repo side
# --------------------------------------------------------------------------

class Unit(object):
    def __init__(self, entry_id, repo_rel, live, report_only=False,
                 append_only=False, machine_owned=False, owner=""):
        self.entry_id = entry_id
        self.repo_rel = repo_rel
        self.repo = REPO_ROOT / Path(*repo_rel.split("/"))
        self.live = live
        self.report_only = report_only
        self.append_only = append_only
        self.machine_owned = machine_owned       # THIS machine writes it
        self.owner = owner                       # ANOTHER machine writes it (its name), else ""


def append_only_rel(rel, patterns):
    """Is this path inside its entry one of the files both machines only ever
    ADD lines to? Those are merged by line union instead of flagged as a
    conflict (the manifest's append_only list)."""
    if not patterns or not rel:
        return False
    rel = rel.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def machine_owned_rel(rel, machine_name):
    """Is this path inside its entry one of the files only THIS machine writes
    (MACHINE_OWNED)? Those never conflict: live wins, every time. A pattern
    with no "/" matches a top-level file only."""
    if not rel or not machine_name:
        return False
    rel = rel.replace("\\", "/")
    for pattern in MACHINE_OWNED:
        if "/" not in pattern and "/" in rel:
            continue
        if fnmatch.fnmatch(rel, pattern.replace("{machine}", machine_name)):
            return True
    return False


def owner_of_rel(rel, machine_name, machines):
    """The OTHER machine that writes this path , or "": the first name
    in `machines` — the machines the manifest records, never a guess from the
    file name — whose MACHINE_OWNED pattern matches. A path THIS machine owns is
    never another's: that test runs first, as it always has."""
    if not rel or machine_owned_rel(rel, machine_name):
        return ""
    for other in machines or ():
        if other and other != machine_name and machine_owned_rel(rel, other):
            return other
    return ""


def build_units(machine, manifest):
    """Every syncable file, plus a list of honest notes about what was
    skipped or could not be mapped."""
    global PARTITION_REPORT, MACHINE_LOCAL
    units = []
    notes = []
    claimed = set()
    name = machine["name"]
    # the machines a file's owner may be — the ones the manifest
    # records (each machine's push writes its own name there), never a name
    # read out of a file name.
    machines = sorted(m for m in (manifest.get("machines") or {}) if m and m != name)
    PARTITION_REPORT = {"mode": "off", "classes": {}, "problems": [],
                        "pending": [], "counts": {}}
    MACHINE_LOCAL = {}
    mode = partition_mode(machine)
    if mode not in ("on", "off"):
        PARTITION_REPORT["mode"] = "stopped"
        PARTITION_REPORT["problems"] = [mode]
    else:
        PARTITION_REPORT["mode"] = mode

    # Single files first, so that a per-machine artifact sitting inside a
    # synced tree (orchestrator/sessions-<machine>.json) is owned by its own entry
    # and never claimed a second time by the tree walk.
    ordered = [e for e in manifest["entries"] if e["kind"] == "file"]
    ordered += [e for e in manifest["entries"] if e["kind"] != "file"]

    for entry in ordered:
        patterns = entry.get("exclude", [])
        append_pats = entry.get("append_only", [])
        report_only = entry.get("mode") == "report-only"
        repo_base = entry["repo"].replace("{machine}", name)
        live_root = entry["live"]["root"]
        live_rel = entry["live"].get("rel", "")
        if live_root not in machine["roots"]:
            # A root this machine has not declared (e.g. "codex" on a machine
            # without Codex): skip the entry honestly instead of crashing.
            notes.append("entry %r: root %r is not in this machine's machine.json"
                         " — add it there to sync it" % (entry["id"], live_root))
            continue

        if entry["kind"] == "file":
            target = live_path(machine, live_root, live_rel)
            unit = Unit(entry["id"], repo_base, target, report_only,
                        append_only_rel(live_rel, append_pats),
                        machine_owned_rel(live_rel, name),
                        owner_of_rel(live_rel, name, machines))
            if not unit.live.exists() and not unit.repo.exists():
                if not entry.get("optional"):
                    notes.append("entry %r: absent on both sides (%s)"
                                 % (entry["id"], repo_base))
                continue
            units.append(unit)
            claimed.add(repo_base)
            continue

        if entry["kind"] == "tree":
            live_dir = live_path(machine, live_root, live_rel)
            repo_dir = REPO_ROOT / Path(*repo_base.split("/"))
            hub_entry = is_hub_entry(entry)
            divided = hub_entry and PARTITION_REPORT["mode"] != "off"
            if divided and PARTITION_REPORT["mode"] == "stopped":
                notes.append("the hub's own entry did not sync: %s"
                             % PARTITION_REPORT["problems"][0])
                continue
            if hub_entry:
                # This machine's own files, in BOTH layouts: pruned
                # from both walks, so never carried, never compared, and never
                # reported deleted on either side.
                local = machine_local_patterns(divided)
                patterns = list(patterns) + list(local)
                MACHINE_LOCAL = {"repo_base": repo_base, "patterns": local}
            live_rels = set(walk_tree(live_dir, patterns))
            rels = set(live_rels)
            rels |= set(walk_tree(repo_dir, patterns))
            if divided:
                try:
                    classes, _tracked = partition_classes(HUB, rels, live_rels)
                    problems = partition_checks(HUB, _tracked)
                except PartitionFailure as failure:
                    PARTITION_REPORT["mode"] = "stopped"
                    PARTITION_REPORT["problems"] = [str(failure)]
                    MACHINE_LOCAL = {}
                    notes.append("the hub's own entry did not sync: %s" % failure)
                    continue
                if problems:
                    MACHINE_LOCAL = {}
                    PARTITION_REPORT["mode"] = "stopped"
                    PARTITION_REPORT["problems"] = problems
                    notes.append("the hub's own entry did not sync: %s" % problems[0])
                    for extra in problems[1:]:
                        notes.append("the hub's own entry, also: %s" % extra)
                    continue
                PARTITION_REPORT["classes"] = classes
                PARTITION_REPORT["repo_base"] = repo_base
                PARTITION_REPORT["pending"] = sorted(
                    r for r, kind in classes.items() if kind == CLASS_PENDING)
                counts = {}
                for kind in classes.values():
                    counts[kind] = counts.get(kind, 0) + 1
                PARTITION_REPORT["counts"] = counts
                rels = set(r for r, kind in classes.items() if kind == CLASS_BRAIN)
                for rel in PARTITION_REPORT["pending"][:20]:
                    notes.append(pending_warning(rel))
            for rel in sorted(rels):
                repo_rel = repo_base + "/" + rel
                if repo_rel in claimed:
                    continue
                claimed.add(repo_rel)
                units.append(Unit(entry["id"], repo_rel,
                                  live_dir / Path(*rel.split("/")),
                                  report_only,
                                  append_only_rel(rel, append_pats),
                                  machine_owned_rel(rel, name),
                                  owner_of_rel(rel, name, machines)))
            continue

        notes.append("entry %r: unknown kind %r — skipped"
                     % (entry["id"], entry["kind"]))

    # memories
    mem = manifest.get("memories", {})
    repo_base = mem.get("repo_base", "claude-home/memories")
    patterns = mem.get("exclude", [])
    merged = dict(mem.get("map", {}))
    repo_memories = REPO_ROOT / Path(*repo_base.split("/"))
    discovered, mem_notes = discover_memories(machine, mem.get("map", {}),
                                              repo_memories)
    notes.extend(mem_notes)
    for logical, record in discovered.items():
        existing = merged.get(logical, {})
        munged = dict(existing.get("munged", {}))
        munged[name] = record["munged"]
        merged[logical] = {
            "root": record["root"] if record["root"] else existing.get("root"),
            "rel": record["rel"] if record["root"] else existing.get("rel"),
            "munged": munged,
        }
    if repo_memories.is_dir():
        for entry in sorted(repo_memories.iterdir(), key=lambda p: p.name):
            if entry.is_dir() and entry.name not in merged:
                merged[entry.name] = {"root": None, "rel": None, "munged": {}}

    for logical in sorted(merged):
        record = merged[logical]
        live_dir = memory_live_dir(machine, logical, record)
        repo_dir = repo_memories / logical
        if live_dir is None:
            if repo_dir.is_dir():
                notes.append("memory %r: no place for it on this machine "
                             "(project absent) — repo copy left alone" % logical)
            continue
        rels = set(walk_tree(live_dir, patterns))
        rels |= set(walk_tree(repo_dir, patterns))
        for rel in sorted(rels):
            units.append(Unit("memories",
                              "%s/%s/%s" % (repo_base, logical, rel),
                              live_dir / Path(*rel.split("/"))))

    return units, notes, merged


# --------------------------------------------------------------------------
# planning
# --------------------------------------------------------------------------

PULL = "pull"      # repo -> live
PUSH = "push"      # live -> repo
SAME = "same"
CONFLICT = "conflict"
UNION = "union"    # append-only file changed on both sides: merged line by line
LIVE_GONE = "live-deleted"
REPO_GONE = "repo-deleted"
REPORT = "report-only"
# the two deletions the engine makes itself, both a machine-owned
# file's owner's own write crossing the brain. Never LIVE_GONE / REPO_GONE, so
# the semantic engine's det_B1/B2 (which read those two) never see them.
OWNER_GONE = "owner-gone"        # this machine took its own file down: the repo copy goes
CARRIED_GONE = "carried-gone"    # the owner took it down: this machine's unchanged copy goes

DELIVERED = " · delivered:"


def _mark_cuts(line):
    """{mark: where its tail begins} for the two tails a line may carry — the
    delivery stamp and the resolved stamp — each matched at its LAST
    occurrence, so a line whose text mentions one still keys correctly."""
    cuts = {}
    for mark in (DELIVERED, RESOLVED_MARK):
        at = line.rfind(mark)
        if at >= 0:
            cuts[mark] = at
    return cuts


def union_key(line):
    """A line's identity, ignoring the mail law's two stamps: the same INBOX
    line is the same line whether or not either machine has marked it
    ` · delivered: <iso> by <session>` or ` · resolved: <iso> by the push
    that landed`. The line is cut at the EARLIEST of the two marks present."""
    cuts = _mark_cuts(line)
    if cuts:
        line = line[:min(cuts.values())]
    return line.rstrip()


def _tail_of(line, mark):
    """The one tail `mark` opens on this line ('' when it carries none): from the
    mark to the next mark after it, or to the end."""
    cuts = _mark_cuts(line)
    if mark not in cuts:
        return ""
    begin = cuts[mark]
    later = [at for at in cuts.values() if at > begin]
    return line[begin:min(later)] if later else line[begin:]


def stamped_union(line, theirs):
    """The one line two copies of a letter become when the other side carries a
    stamp this side lacks (the stamped side wins): this side's line when
    it carries every mark theirs does; theirs whole when this side carries none
    (the delivered road, exactly as before); else the key with BOTH tails, the
    delivered tail first and the resolved tail after it."""
    mine, other = _mark_cuts(line), _mark_cuts(theirs)
    if not [m for m in other if m not in mine]:
        return line
    if not mine:
        return theirs
    out = union_key(line)
    for mark in (DELIVERED, RESOLVED_MARK):
        out += _tail_of(line, mark) or _tail_of(theirs, mark)
    return out


def union_merge(live_text, repo_text):
    """Merge two append-only files by line union. -> (merged, n_from_repo).

    Live order is kept. A line the repo has stamped (delivered, or resolved)
    and live has not keeps the stamp. Repo-only item lines go in immediately before the first
    live-only item line, so the two machines' additions interleave in the
    order each machine wrote them rather than one burying the other. Blank
    lines and lines that are not ``- `` items are structure: live's are kept,
    the repo's are never inserted."""
    live_lines = live_text.split("\n")
    repo_lines = repo_text.split("\n")
    trailing = live_text.endswith("\n")
    if trailing:
        live_lines = live_lines[:-1]
    if repo_text.endswith("\n"):
        repo_lines = repo_lines[:-1]

    def is_item(line):
        return line.startswith("- ")

    repo_items = {}
    for line in repo_lines:
        if is_item(line):
            repo_items.setdefault(union_key(line), line)
    live_keys = set(union_key(l) for l in live_lines if is_item(l))

    extras = []
    seen = set()
    for line in repo_lines:
        key = union_key(line)
        if is_item(line) and key not in live_keys and key not in seen:
            seen.add(key)
            extras.append(line)

    merged = []
    placed = not extras
    for line in live_lines:
        if not placed and is_item(line) and union_key(line) not in repo_items:
            merged.extend(extras)      # in front of this machine's own new lines
            placed = True
        if is_item(line):
            theirs = repo_items.get(union_key(line))
            if theirs is not None:
                # the other machine stamped it (delivered, or resolved):
                # the stamped side wins, and an unstamped twin never comes back
                merged.append(stamped_union(line, theirs))
                continue
        merged.append(line)
    if not placed:
        merged.extend(extras)
    text = "\n".join(merged)
    if trailing:
        text += "\n"
    return text, len(extras)


class Action(object):
    def __init__(self, unit, kind, why):
        self.unit = unit
        self.kind = kind
        self.why = why
        self.merged_from_repo = 0
        self.say = ""            #  the one line a machine-owned resolution prints
        self.expect = None       # CARRIED_GONE: the bytes the copy must still be
        self.fallback = None     # OWNER_GONE: the ordinary rule's answer (OWNER_GONE_CAP)
        self.mass = 0            # >0: one of that many own files gone at once (a lost folder)


def unions(unit, live_hash, repo_hash):
    """Only an append-only file with both sides present is merged. A
    report-only unit never is: it is reported, never written."""
    return (unit.append_only and not unit.report_only
            and live_hash is not None and repo_hash is not None)


def ordinary(unit, live_hash, repo_hash, remembered):
    """The rule for every file nobody owns — exactly as it always was."""
    if remembered is None:
        if live_hash is not None and repo_hash is not None:
            live_m = mtime_of(unit.live) or 0
            repo_m = mtime_of(unit.repo) or 0
            if live_m >= repo_m:
                return Action(unit, PUSH, "no record yet; live mtime newer")
            return Action(unit, PULL, "no record yet; repo mtime newer")
        if live_hash is not None:
            return Action(unit, PUSH, "new on this machine")
        return Action(unit, PULL, "new from the other machine")

    live_moved = remembered.get("live") != live_hash
    repo_moved = remembered.get("repo") != repo_hash

    if live_moved and repo_moved:
        if unions(unit, live_hash, repo_hash):
            return Action(unit, UNION, "changed on BOTH sides — "
                                       "append-only, merged by line union")
        return Action(unit, CONFLICT, "changed on BOTH sides since the last sync")
    if live_moved:
        if live_hash is None:
            return Action(unit, LIVE_GONE, "deleted here, still in the repo")
        return Action(unit, PUSH, "changed here")
    if repo_moved:
        if repo_hash is None:
            return Action(unit, REPO_GONE, "deleted in the repo, still here")
        return Action(unit, PULL, "changed on the other machine")
    if unions(unit, live_hash, repo_hash):
        return Action(unit, UNION, "both sides differ but neither moved — "
                                   "append-only, merged by line union")
    return Action(unit, CONFLICT, "both sides differ but neither moved — "
                                  "an earlier conflict is still unresolved")


def owned_here(unit, live_hash, repo_hash, remembered):
    """on the OWNER: live wins while it is there (one line
    when the brain's copy moved too); gone here means taken down, so the repo
    copy goes — never pulled back, record or no record."""
    if live_hash is not None:
        action = Action(unit, PUSH, "machine-owned: this machine writes it, so live wins")
        if remembered is not None and repo_hash is not None \
                and remembered.get("repo") != repo_hash:
            action.say = ("machine-owned %s also changed in the brain — live kept"
                          % unit.repo_rel)
        return action
    action = Action(unit, OWNER_GONE, "this machine's own file, taken down here")
    action.fallback = ordinary(unit, live_hash, repo_hash, remembered)
    return action


def carried(unit, live_hash, repo_hash, remembered):
    """on the CARRIER of another machine's file, or None for
    the ordinary rule. The brain's copy is the owner's word: a copy edited
    here is put back (one line) and never pushed; a copy the owner took down
    goes while it is the remembered bytes, and is only reported once it moved.
    A copy gone HERE is the ordinary rule's — a call, never a deletion."""
    if live_hash is None:
        return None
    if repo_hash is None:
        if remembered is not None and remembered.get("repo") \
                and live_hash == remembered.get("repo"):
            action = Action(unit, CARRIED_GONE, "%s took it down; this copy is the one "
                                                "the last sync left" % unit.owner)
            action.expect = live_hash
            return action
        return None
    if remembered is not None and remembered.get("live") == live_hash:
        return None                       # only the brain moved: the ordinary pull
    action = Action(unit, PULL, "carried: %s writes it, so the brain's copy wins" % unit.owner)
    if remembered is not None:
        action.say = "carried %s is %s's — the brain's copy kept" % (unit.repo_rel, unit.owner)
    return action


def plan(units, state):
    actions = []
    takedowns = []
    for unit in units:
        live_hash = sha256_of(unit.live) if unit.live.is_file() else None
        repo_hash = sha256_of(unit.repo) if unit.repo.is_file() else None
        remembered = state.get("units", {}).get(unit.repo_rel)

        if live_hash is None and repo_hash is None:
            continue
        if live_hash == repo_hash:
            actions.append(Action(unit, SAME, "identical"))
            continue

        if unit.machine_owned:
            action = owned_here(unit, live_hash, repo_hash, remembered)
            if action.kind == OWNER_GONE:
                takedowns.append(action)
            actions.append(action)
            continue
        if getattr(unit, "owner", ""):
            action = carried(unit, live_hash, repo_hash, remembered)
            if action is not None:
                actions.append(action)
                continue
        actions.append(ordinary(unit, live_hash, repo_hash, remembered))

    # A lost folder is not a takedown (OWNER_GONE_CAP): past the cap, every
    # one of them takes the ordinary rule's answer instead, marked so the
    # report can say why in one line.
    if len(takedowns) > OWNER_GONE_CAP:
        swap = dict((id(a), a.fallback) for a in takedowns)
        for index, action in enumerate(actions):
            if id(action) in swap:
                actions[index] = swap[id(action)]
                actions[index].mass = len(takedowns)

    # A report-only entry is allowed to travel live -> repo (so the other
    # machine has something to compare against) but is NEVER written back
    # over a live file. Everything else about it is only ever reported.
    for action in actions:
        if action.unit.report_only and action.kind in (
                PULL, CONFLICT, REPO_GONE, LIVE_GONE, OWNER_GONE, CARRIED_GONE):
            action.kind = REPORT
    return actions


def apply_action(action, state):
    unit = action.unit
    if action.kind == PULL:
        unit.live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(unit.repo), str(unit.live))
    elif action.kind == PUSH:
        unit.repo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(unit.live), str(unit.repo))
    elif action.kind == UNION:
        live_text = read_text(unit.live)
        repo_text = read_text(unit.repo)
        if live_text is None or repo_text is None:
            return False
        merged, brought = union_merge(live_text, repo_text)
        action.merged_from_repo = brought
        write_text(unit.live, merged)
        write_text(unit.repo, merged)
    elif action.kind in (OWNER_GONE, CARRIED_GONE):
        return take_down(action, state)
    else:
        return False
    digest = sha256_of(unit.repo)
    state.setdefault("units", {})[unit.repo_rel] = {
        "live": digest, "repo": digest, "ts": now_iso()}
    return True


def take_down(action, state):
    """ the only two deletions this tool makes. Each is re-checked the
    moment before it happens (the plan may be seconds old): an owner's file
    that came back since is NOT taken down; a carried copy that moved since
    is NOT removed. The record goes with the file, so nothing is re-created
    from it. -> True when the file was removed."""
    unit = action.unit
    if action.kind == OWNER_GONE:
        if unit.live.exists():
            return False                  # the owner wrote it again: a push carries it
        target = unit.repo
    else:
        if action.expect is None or sha256_of(unit.live) != action.expect:
            return False                  # moved since the plan: reported next run, kept
        target = unit.live
    try:
        os.remove(str(target))
    except FileNotFoundError:
        pass
    except OSError:
        return False
    state.setdefault("units", {}).pop(unit.repo_rel, None)
    return True


def _apply_takedowns(buckets, state):
    """Apply both takedown kinds, one line each as it happens. -> the count."""
    done = 0
    for action in buckets.get(OWNER_GONE, []):
        if apply_action(action, state):
            done += 1
            print("  x  taken down: %s (this machine's own)" % action.unit.repo_rel)
    for action in buckets.get(CARRIED_GONE, []):
        if apply_action(action, state):
            done += 1
            print("  x  carried: %s taken down by %s" % (action.unit.repo_rel,
                                                         action.unit.owner))
    return done


def takedown_line(count, pending=False):
    """S3: the one summary line, after the pulled/pushed counts."""
    if not count:
        return ""
    return "  ~  %d signal file(s) taken down by their owner%s" % (
        count, " — the next pull or push carries it" if pending else "")


def mass_line(actions):
    """The one line a lost folder earns (OWNER_GONE_CAP), or ""."""
    mass = max([a.mass for a in actions] or [0])
    if not mass:
        return ""
    return ("  !  %d of this machine's own files are gone at once — read as a lost folder, "
            "not a takedown: nothing was deleted (sync.py recover puts back what the "
            "brain holds)" % mass)


def remember_same(actions, state):
    for action in actions:
        if action.kind == SAME:
            digest = sha256_of(action.unit.repo)
            if digest is not None:
                state.setdefault("units", {})[action.unit.repo_rel] = {
                    "live": digest, "repo": digest, "ts": now_iso()}


# --------------------------------------------------------------------------
# the settling window: what a push carries now, and what waits one beat
# --------------------------------------------------------------------------

def is_signal(rel, patterns=SIGNAL_FILES):
    """Is this relative path one of the signal files, which never wait?

    Matched against the path AND every tail of it, so `dossier/TAUGHT.md`
    catches `orchestrator/dossier/TAUGHT.md` too: sync.py carries both
    repo-relative and entry-relative paths, and a signal must never be held
    back because of a prefix.
    """
    rel = (rel or "").replace("\\", "/").strip("/")
    if not rel:
        return False
    parts = rel.split("/")
    tails = ["/".join(parts[i:]) for i in range(len(parts))]
    for pattern in patterns or ():
        for tail in tails:
            if fnmatch.fnmatch(tail, pattern):
                return True
    return False


def select_for_push(candidates, now, settle, signal_patterns=SIGNAL_FILES):
    """Split a push's changed files into (carry, waiting).

    `candidates` is [(rel, live mtime)] - what the push would copy. A file
    written less than `settle` seconds ago waits for the next push, so a
    half-saved file is never carried mid-edit. Four things never wait:
    a signal file, a file with no mtime (it is gone, and a deletion is never
    held back), a file whose mtime is in the future (clock skew must not park
    a file forever), and everything when `settle` is 0.
    """
    carry, waiting = [], []
    settle = max(0, int(settle or 0))
    for rel, mtime in candidates:
        age = None if mtime is None else (now - mtime)
        if settle and age is not None and 0 <= age < settle \
                and not is_signal(rel, signal_patterns):
            waiting.append(rel)
        else:
            carry.append(rel)
    return carry, waiting


def settling_line(waiting, settle, limit=8):
    """The one line a push prints about files that are waiting, or None."""
    if not waiting:
        return None
    names = ", ".join(waiting[:limit])
    if len(waiting) > limit:
        names += " +%d" % (len(waiting) - limit)
    return ("  settling: %d file(s) younger than %d s wait for the next push"
            " — %s" % (len(waiting), settle, names))


def settle_seconds(args=None):
    value = getattr(args, "settle", None)
    if value is None:
        value = _env_int("ORCHSYNC_SETTLE", SETTLE_DEFAULT)
    return max(0, int(value))


def push_retries(args=None):
    value = getattr(args, "retries", None)
    if value is None:
        value = _env_int("ORCHSYNC_PUSH_RETRIES", PUSH_RETRIES_DEFAULT)
    return max(1, int(value))


def push_letter_after():
    """Failed beats running before the hub gets a letter."""
    return max(1, int(_env_int("ORCHSYNC_PUSH_LETTER_AFTER", PUSH_LETTER_AFTER_DEFAULT)))


def push_letter_minutes():
    """Minutes of failing before the hub gets a letter, whatever the count."""
    return max(0, int(_env_int("ORCHSYNC_PUSH_LETTER_MINUTES", PUSH_LETTER_MINUTES_DEFAULT)))


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------

def git(*args, **kwargs):
    check = kwargs.pop("check", False)
    result = subprocess.run(
        ["git"] + list(args), cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True)
    if check and result.returncode != 0:
        die("git %s failed:\n%s" % (" ".join(args), result.stdout.strip()))
    return result.returncode, result.stdout.strip()


def git_has_commits():
    code, _ = git("rev-parse", "--verify", "HEAD")
    return code == 0


def git_branch():
    code, out = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if code == 0 and out:
        return out
    code, out = git("rev-parse", "--abbrev-ref", "HEAD")
    if code == 0 and out and out != "HEAD":
        return out
    return "main"


# Output git prints when someone else got there first. Nothing is lost: the
# commit just needs the newer tip under it.
REJECTED_MARKS = ("rejected", "cannot lock ref", "fetch first")


def _rejected(out):
    return any(mark in (out or "") for mark in REJECTED_MARKS)


# What git says when it is telling you something, as opposed to narrating.
GIT_SAYS = ("!", "error:", "fatal:", "remote:")


def _first_line(*outs):
    """The one line of git output worth putting in front of a human.

    `To ../origin.git` is the first line of a rejected push and says nothing;
    the line under it (`! [rejected] main -> main (fetch first)`) is the
    answer. So: the first line that is git speaking up, else the first line
    there is."""
    fallback = None
    for out in outs:
        for line in (out or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if fallback is None:
                fallback = line
            if line.startswith(GIT_SAYS) or _rejected(line):
                return line
    return fallback or "no output from git"


def _attempts(count):
    return "%d attempt%s" % (count, "" if count == 1 else "s")


def push_with_retry(git_fn, branch, *, retries=3, wait_fn=None, log=print,
                    on_fail=None):
    """`git push` that heals the ordinary collision by itself -> (code, out).

    Two machines and a five-minute pulse push the same branch, so a rejection
    is an operating condition: pull the newer tip under our commit (a merge,
    so the append-only files keep their union merge), wait a random 1-4 s so
    the two machines do not collide again on the same beat, and push again.
    Nothing is forced and nothing is lost - a rejected push leaves the commit
    exactly where it was, which is why a repeated attempt has no second effect.

    Every attempt rejected, or the merge-pull itself failing, is a real
    failure: one `!` line naming the reason, then `on_fail(reason)` for
    whoever wants to leave a letter about it. A failure git cannot fix by
    pulling (no network, no permission) is not retried at all.
    """
    retries = max(1, int(retries or 1))
    sleep = wait_fn if wait_fn is not None else time.sleep
    attempt, code, out = 0, 0, ""
    for attempt in range(1, retries + 1):
        code, out = git_fn("push", "-u", "origin", branch)
        for line in (out or "").splitlines():
            log("  git: %s" % line)
        if code == 0:
            if attempt > 1:
                log("  i  retry push ok (attempt %d)" % attempt)
            return code, out
        if not _rejected(out) or attempt == retries:
            break
        pause = random.uniform(1.0, 4.0)
        log("  i  push rejected (attempt %d/%d) — pulling, retrying in %.1f s"
            % (attempt, retries, pause))
        pull_code, pull_out = git_fn("pull", "--rebase=false", "--no-edit")
        for line in (pull_out or "").splitlines()[:3]:
            log("  git: %s" % line)
        if pull_code != 0:
            return _push_failed(log, on_fail, attempt,
                                _first_line(pull_out, out), pull_code or 1,
                                pull_out)
        sleep(pause)
    return _push_failed(log, on_fail, attempt, _first_line(out), code or 1, out)


def _push_failed(log, on_fail, attempt, reason, code, out):
    log("  !  push failed after %s — %s" % (_attempts(attempt), reason))
    if on_fail is not None:
        try:
            # A closure that wants to name the count in its letter reads it
            # here; the call itself stays on_fail(reason).
            on_fail.attempts = attempt
        except (AttributeError, TypeError):
            pass
        on_fail(reason)
    return code, out


def hub_letter_line(machine, what, reason):
    """The one addressed line hub_letter writes — spelled here and nowhere else."""
    name = str(machine.get("name") or "?")
    one_line = " ".join(str(reason).split()).replace("·", "-")[:200]
    return ("- %s · to: %s/hub · %s · %s: %s · run: %s sync.py push"
            % (datetime.date.today().isoformat(), name.upper(), PROGRAM_NAME,
               what, one_line or "no reason given", py_word()))


def hub_letter(machine, what, reason, log=print):
    """One addressed INBOX line for this machine's hub (mail law).

    The hub's watcher reads it on its next beat, and INBOX.md is a signal
    file, so the letter flies on the next push that does land. Never twice:
    an identical line already in the file is left alone, so a five-minute
    pulse cannot paper the INBOX with the same sentence.
    """
    name = str(machine.get("name") or "?")
    inbox = live_path(machine, "orchestrator", "INBOX.md")
    line = hub_letter_line(machine, what, reason)
    try:
        existing = read_text(inbox) or ""
        if line in existing.split("\n"):
            log("  i  the hub already has this letter today — not repeated")
            return True
        inbox.parent.mkdir(parents=True, exist_ok=True)
        with inbox.open("a", encoding="utf-8", newline="") as handle:
            handle.write(("" if not existing or existing.endswith("\n")
                          else "\n") + line + "\n")
    except OSError as exc:
        log("  i  could not leave the hub a letter about it (%s)" % exc)
        return False
    log("  i  told the hub: one INBOX line for %s/hub" % name.upper())
    return True


def push_fail_mail(machine, reason, attempts, log=print, since=None, tries=None):
    """The letter a push that could not be landed leaves behind. Given the span
    (`since`, the ISO of its first failed beat, and `tries`, its failed beats),
    the letter names the span instead of one beat's attempts."""
    return hub_letter(machine, push_fail_what(machine, attempts, since, tries),
                      reason, log=log)


def push_fail_what(machine, attempts, since=None, tries=None):
    if since is None:
        return "PUSH FAILED after %s on %s" % (_attempts(attempts), machine.get("name") or "?")
    return "PUSH FAILED since %s (%s) on %s" % (
        _local_hhmm(since), _tries(tries or 1), machine.get("name") or "?")


def _tries(count):
    return "%d tr%s" % (count, "y" if count == 1 else "ies")


def _local_hhmm(iso_text):
    when = parse_iso(iso_text)
    return when.astimezone().strftime("%H:%M") if when is not None else "?"


def _utc(now=None):
    if now is None:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    if now.tzinfo is None:
        now = now.astimezone()
    return now.astimezone(datetime.timezone.utc).replace(microsecond=0)


def _iso_z(when):
    return when.isoformat().replace("+00:00", "Z")


def _letter_token(line):
    """The token mail.py's token() gives this line: `pm-` + 12 hex of sha256 over the
    line, ends trimmed (a fresh letter carries no tail). sync.py imports nothing from
    the hub's tools; the gate (S1e) proves the two agree on the letter written."""
    return "pm-" + hashlib.sha256(str(line).strip().encode("utf-8")).hexdigest()[:12]


def note_push_failure(machine, state, reason, attempts, now=None, log=print):
    """A failed push is remembered as a SPAN in the sync state
    (`push_failures`: since · count · last_reason · letter), and the hub gets ONE
    letter about the span only when it has lasted PUSH_LETTER_AFTER failed beats or
    PUSH_LETTER_MINUTES, whichever comes first. A later failure in the same span
    writes nothing more. -> the span's letter token, or None while none is owed."""
    at = _utc(now)
    span = state.get("push_failures")
    if not isinstance(span, dict) or parse_iso(span.get("since")) is None:
        span = {"since": _iso_z(at), "count": 0, "last_reason": "", "letter": None}
    span["count"] = int(span.get("count") or 0) + 1
    span["last_reason"] = " ".join(str(reason or "").split())[:200]
    state["push_failures"] = span
    if span.get("letter"):
        return span["letter"]                      # this span's letter is written: never twice
    began = parse_iso(span["since"])
    lasted = (at - began).total_seconds() / 60.0 if began is not None else 0.0
    if span["count"] < push_letter_after() and lasted < push_letter_minutes():
        log("  i  the hub is not told yet: %s of this failure (a letter at %d, or after "
            "%d min)" % (_tries(span["count"]), push_letter_after(), push_letter_minutes()))
        return None
    what = push_fail_what(machine, attempts, span["since"], span["count"])
    line = hub_letter_line(machine, what, span["last_reason"] or reason)
    if hub_letter(machine, what, span["last_reason"] or reason, log=log):
        span["letter"] = _letter_token(line)
    return span.get("letter")


def is_failed_push_letter(line, machine):
    """A PUSH FAILED letter addressed to THIS machine's hub, still open (no resolved
    tail) — the letters a push that lands closes."""
    if not str(line).startswith("- ") or RESOLVED_MARK in line:
        return False
    fields = [f.strip() for f in union_key(line)[2:].split(" · ")]
    want = "to: %s/hub" % str(machine.get("name") or "?").lower()
    return (len(fields) >= 4 and fields[1].lower() == want
            and fields[3].startswith("PUSH FAILED"))


def stamp_resolved(machine, now=None, log=print):
    """Stamp every open failed-push letter to this machine's hub IN PLACE
    with ` · resolved: <ISO to the minute> by the push that landed` (after any
    delivered tail). The rewrite is compare-and-swap, the way mail.py's mark_delivered
    makes it: written beside, the file's own mode kept, replaced only when nothing
    appended meanwhile; three tries. -> how many letters were stamped."""
    inbox = live_path(machine, "orchestrator", "INBOX.md")
    when = (now or datetime.datetime.now()).astimezone().replace(second=0, microsecond=0)
    stamp = "%s %s %s" % (RESOLVED_MARK, when.isoformat(timespec="minutes"), RESOLVED_BY)
    for _ in range(3):
        try:
            before = inbox.stat()
        except OSError:
            return 0
        text = read_text(inbox) or ""
        lines = text.split("\n")
        hits = [i for i, l in enumerate(lines) if is_failed_push_letter(l, machine)]
        if not hits:
            return 0
        for i in hits:
            lines[i] = lines[i].rstrip() + stamp
        fd, tmp = tempfile.mkstemp(dir=str(inbox.parent), prefix=".INBOX", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(lines))
        try:
            os.chmod(tmp, before.st_mode & 0o7777)
        except OSError:
            pass
        try:
            after = inbox.stat()
        except OSError:
            after = None
        if after and (after.st_mtime_ns, after.st_size) == (before.st_mtime_ns, before.st_size):
            os.replace(tmp, str(inbox))
            return len(hits)
        try:
            os.unlink(tmp)
        except OSError:
            pass
    log("  i  the failed-push letters were not closed — INBOX.md changed under the stamp "
        "three times; the next push that lands closes them")
    return 0


def note_push_landed(machine, state, now=None, log=print):
    """A push LANDED: every open failed-push letter to this machine's hub
    is stamped resolved, and the span is forgotten. -> how many letters were closed."""
    closed = stamp_resolved(machine, now=now, log=log)
    if closed:
        log("  i  closed %d failed-push letter(s): the push landed" % closed)
    state.pop("push_failures", None)
    return closed


def push_and_mind(machine, state, git_fn, branch, retries, now=None, log=print,
                  wait_fn=None):
    """The push the tail makes, with its two duties around it: a failure is
    noted against its span (the letter waits for a real failure), and a push that
    lands closes every letter about failing. -> (code, out)."""
    def on_fail(reason):
        note_push_failure(machine, state, reason,
                          getattr(on_fail, "attempts", retries), now=now, log=log)

    kwargs = {"retries": retries, "on_fail": on_fail, "log": log}
    if wait_fn is not None:
        kwargs["wait_fn"] = wait_fn
    code, out = push_with_retry(git_fn, branch, **kwargs)
    if code == 0:
        note_push_landed(machine, state, now=now, log=log)
    return code, out


def privacy_stop_mail(machine, refusal, state=None, log=print):
    """The letter a push the guard STOPPED leaves behind.

    The same road a failed push takes, and one thing more: the letter is
    carried into the mirror in this same run. The push that would have carried
    it is the one that was stopped, and a machine told that its destination is
    public should not take that news to the grave."""
    if not hub_letter(machine, "BRAIN PUSH STOPPED by the privacy guard",
                      refusal, log=log):
        return False
    live = live_path(machine, "orchestrator", "INBOX.md")
    repo = REPO_ROOT / "orchestrator" / "INBOX.md"
    try:
        if live.is_file():
            repo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(live), str(repo))
            if state is not None:
                digest = sha256_of(repo)
                state.setdefault("units", {})["orchestrator/INBOX.md"] = {
                    "live": digest, "repo": digest, "ts": now_iso()}
    except OSError as exc:
        log("  i  the letter is in the hub's INBOX but did not reach the mirror (%s)"
            % exc)
    return True


def origin_url(git_fn=None):
    runner = git_fn or git
    code, out = runner("config", "--get", "remote.origin.url")
    return out.strip() if code == 0 else ""


def local_origin_path(url):
    """The filesystem path of a LOCAL origin, or None for anything remote.

    Local means a file:// URL or a plain path. Anything with another scheme,
    and anything scp-style (`user@host:path`), is a host - never local.
    """
    url = (url or "").strip()
    if not url:
        return None
    if url.lower().startswith("file://"):
        rest = url[7:]
        if len(rest) > 2 and rest[0] == "/" and rest[2] == ":":
            rest = rest[1:]          # file:///C:/x -> C:/x
        return rest or None
    if "://" in url:
        return None
    head = url.split(":", 1)[0]
    if ":" in url and not (len(head) == 1 and head.isalpha()):
        return None                  # host:path, but a drive letter is fine
    return url


def test_push_target():
    """Under ORCHSYNC_TEST_ROOT, the local origin a rehearsal may push to.

    None means the refusal stands. The flag alone is never enough: origin has
    to be a path on this disk, so no rehearsal can reach a host.
    """
    if os.environ.get("ORCHSYNC_ALLOW_LOCAL_PUSH", "").strip() != "1":
        return None
    return local_origin_path(origin_url())


# --------------------------------------------------------------------------
# the brain privacy guard
#
# A brain holds a life. Before a push that has something to send, the tool
# works out the address the push would ACTUALLY reach — after any rewriting —
# and needs a CURRENT answer that it is not publicly readable. An old answer
# authorizes nothing: a repository made public at 09:30 must not be pushed to
# at 10:00 on a verdict from 09:00. A beat with nothing to send asks nothing.
#
# Residual risk, stated rather than hidden: the destination's visibility can
# change between the check and the transfer. Nothing on this side closes that.
# --------------------------------------------------------------------------

PRIVATE = "private"
PUBLIC = "public"
UNKNOWN = "unknown"
PRIVACY_PROBE_ENV = "EXO_PRIVACY_PROBE"


def push_destination(git_fn=None):
    """The address a push would really reach, with any insteadOf applied."""
    runner = git_fn or git
    code, out = runner("remote", "get-url", "--push", "origin")
    if code != 0:
        return ""
    for line in (out or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def unpushed_commits(git_fn=None):
    """How many commits this machine is holding. 0 means: ask nothing."""
    runner = git_fn or git
    code, _out = runner("rev-parse", "--verify", "HEAD")
    if code != 0:
        return 0
    code, out = runner("rev-list", "--count", "@{u}..HEAD")
    if code == 0 and out.strip().isdigit():
        return int(out.strip())
    return 1              # no upstream yet: a first push has everything to send


def github_repo(url):
    """(owner, repo) when this address is a repository on the public host."""
    text = (url or "").strip()
    if text.endswith(".git"):
        text = text[:-4]
    host, path = "", ""
    if "://" in text:
        rest = text.split("://", 1)[1]
        host, _, path = rest.partition("/")
        if "@" in host:
            host = host.split("@", 1)[1]
    elif ":" in text and not text.startswith("/"):
        head, _, path = text.partition(":")
        host = head.split("@", 1)[1] if "@" in head else head
    if host.lower() not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in path.split("/") if p]
    return (parts[0], parts[1]) if len(parts) >= 2 else None


def _github_visibility(owner, repo, timeout=6.0):
    """(verdict, sentence) from the host's own answer. Authenticated when a
    token is here — a five-minute beat cannot reach that rate limit."""
    import urllib.error
    import urllib.request
    url = "https://api.github.com/repos/%s/%s" % (owner, repo)
    token = ""
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(name, "").strip()
        if token:
            break
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "exocortex-sync"})
    if token:
        request.add_header("Authorization", "Bearer %s" % token)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            body = json.loads(answer.read().decode("utf-8", "replace"))
        if answer.status == 200:
            if token and isinstance(body, dict) and "private" in body:
                return ((PRIVATE, "the host says it is private")
                        if body.get("private") else
                        (PUBLIC, "the host says it is public"))
            return PUBLIC, "anyone can read it without signing in"
        return UNKNOWN, "the host answered %s" % answer.status
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            return PRIVATE, "it cannot be read without signing in"
        return UNKNOWN, "the host answered %s" % exc.code
    except Exception as exc:
        return UNKNOWN, ("the host could not be asked (%s)"
                         % " ".join(str(exc).split())[:80])


def attestation_for(machine, url):
    return ((machine or {}).get("attestations") or {}).get(url)


def remember_attestation(machine, url, verdict):
    """Written against the EXACT address, so a changed address asks again."""
    data = read_json(MACHINE_FILE)
    if not isinstance(data, dict):
        return False
    data.setdefault("attestations", {})[url] = verdict
    write_json(MACHINE_FILE, data)
    machine.setdefault("attestations", {})[url] = verdict
    return True


def privacy_verdict(url, machine, ask=True):
    """(private | public | unknown, one plain sentence) for THIS push.

    Never remembered between pushes: the answer is made again every time there
    is something to send."""
    probe = os.environ.get(PRIVACY_PROBE_ENV, "").strip()
    if probe:
        table = read_json(Path(probe))
        if not isinstance(table, dict):
            return UNKNOWN, "the probe file %s could not be read" % probe
        word = str(table.get(url, table.get("*", UNKNOWN))).strip().lower()
        if word not in (PRIVATE, PUBLIC, UNKNOWN):
            word = UNKNOWN
        return word, "answered from the probe file"
    if not url:
        return UNKNOWN, "this repo has no push address"
    if local_origin_path(url):
        return PRIVATE, "it is a folder on this disk"
    named = github_repo(url)
    if named is not None:
        return _github_visibility(named[0], named[1])
    recorded = attestation_for(machine, url)
    if recorded in (PRIVATE, PUBLIC):
        return recorded, "you told this machine so, for this exact address"
    if ask and sys.stdin is not None and sys.stdin.isatty():
        print("  Your brain is about to be pushed to %s, and this machine cannot ask that"
              % url)
        print("  host whether anyone can read it. Is that address private?")
        try:
            answer = input("  private? [yes/no]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer in ("y", "yes"):
            remember_attestation(machine, url, PRIVATE)
            return PRIVATE, "you told this machine so, for this exact address"
        if answer in ("n", "no"):
            remember_attestation(machine, url, PUBLIC)
            return PUBLIC, "you told this machine so, for this exact address"
    return UNKNOWN, "nobody can say whether that address is readable by anyone"


def privacy_gate(machine, git_fn=None, log=print):
    """(may this push go, the one line about it).

    ENFORCING in a program tree. REPORT-ONLY in the older layout until it has
    run clean there — the line prints and the push goes on."""
    if unpushed_commits(git_fn) == 0:
        return True, None
    url = push_destination(git_fn)
    verdict, why = privacy_verdict(url, machine)
    log("  privacy: %s — %s (%s)" % (verdict, url or "no push address", why))
    if verdict == PRIVATE:
        return True, None
    if LAYOUT != LAYOUT_PROGRAM:
        log("  i  report-only in this layout: the push goes on.")
        return True, None
    if verdict == PUBLIC:
        return False, ("STOP: nothing was pushed. %s can be read by anyone, and your brain "
                       "is not for anyone. Everything on this machine is up to date. Point "
                       "origin at a private repository, then push again." % url)
    return False, ("STOP: nothing was pushed. This machine could not find out whether %s "
                   "can be read by anyone, and it will not send a brain it cannot vouch "
                   "for. Everything on this machine is up to date; the next beat asks "
                   "again." % (url or "the push address"))


def git_sync_commits():
    """[(sha, iso date, machine)] newest first, from `sync: <machine> ...`."""
    if not git_has_commits():
        return []
    code, out = git("log", "--format=%H\t%cI\t%s", "-n", "200")
    if code != 0:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        match = re.match(r"^sync:\s+(\S+)", parts[2])
        if match:
            rows.append((parts[0][:8], parts[1], match.group(1)))
    return rows


# --------------------------------------------------------------------------
# this machine's own files that the brain still holds
#
# The never-sync list applies in both layouts, not only with the partition
# on, so no builder's world under scratch/ rides the brain. What the brain
# already holds is named once by `status` and leaves by ONE commit,
# `push --prune-local`, which never runs by itself.
# --------------------------------------------------------------------------

PRUNE_GUARD_START = "# >>> BQ-101: this machine's own files never enter the brain >>>"
PRUNE_GUARD_END = "# <<< BQ-101 <<<"
PRUNE_CHUNK = 100          # paths per `git rm` call: far inside Windows' command line


def _git_bytes(args, stdin=None, env_extra=None):
    """git in the brain -> (code, stdout bytes, stderr text). stdout is kept
    apart from stderr: a list read with -z must never carry git's warnings."""
    env = None
    if env_extra:
        env = dict(os.environ)
        env.update(env_extra)
    proc = subprocess.run(["git"] + [str(a) for a in args], cwd=str(REPO_ROOT),
                          input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env)
    return (proc.returncode, proc.stdout or b"",
            (proc.stderr or b"").decode("utf-8", "replace").strip())


def machine_local_in_brain():
    """[repo paths] the brain still TRACKS that the list in force names as this
    machine's own. Git is asked, not the folder: a leftover copy the brain no
    longer tracks is not in the brain. Empty when the hub's entry did not sync
    this run, or when git cannot say."""
    base = MACHINE_LOCAL.get("repo_base")
    patterns = MACHINE_LOCAL.get("patterns")
    if not base or not patterns or not git_has_commits():
        return []
    code, out, _err = _git_bytes(["ls-files", "-z", "--", base],
                                 env_extra={"GIT_LITERAL_PATHSPECS": "1"})
    if code != 0:
        return []
    prefix = base + "/"
    return sorted(rel for rel in _nul_list(out)
                  if rel.startswith(prefix) and excluded(rel[len(prefix):], patterns))


def machine_local_groups(paths, depth=1):
    """[(folder/ or file, count)] under the hub's repo base, `depth` levels down."""
    base = MACHINE_LOCAL.get("repo_base") or ""
    counts = {}
    for rel in paths:
        inner = rel[len(base) + 1:] if base and rel.startswith(base + "/") else rel
        parts = inner.split("/")
        key = "/".join(parts[:depth]) + ("/" if len(parts) > depth else "")
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items())


def mistake_block(paths):
    """Said ONCE, by `status` alone: this machine's own files that the brain
    still holds from before the list applied to both layouts. Nothing is
    printed when there are none, so a clean brain reads exactly as before."""
    if not paths:
        return
    groups = machine_local_groups(paths)
    shown = " · ".join("%s %d" % (name, count) for name, count in groups[:8])
    if len(groups) > 8:
        shown += " · +%d more" % (len(groups) - 8)
    print("")
    print("IN THE BRAIN BY MISTAKE")
    print("  %d file(s) of this machine's own are still in the brain from before; they "
          "never sync now, and they leave at the next `sync.py push --prune-local` (one "
          "commit; history keeps every byte, nothing on disk is deleted):" % len(paths))
    print("      %s" % shown)


def guard_lines(base, patterns):
    """The brain's .gitignore lines for the list in force, under the hub's repo
    base — so `git add -A` never takes a leftover copy back in. The list's own
    reading is kept: a bare name matches at any depth, a leading slash only at
    the top, a folder pattern the whole folder."""
    lines = []
    for pattern in patterns:
        if pattern == ".git/**":
            continue                      # git never adds its own folder
        if pattern.startswith("/"):
            lines.append("/%s%s" % (base, pattern))
        elif pattern.endswith("/**"):
            lines.append("/%s/%s/" % (base, pattern[:-3]))
        elif "/" in pattern:
            head, _, name = pattern.rpartition("/")
            if any(c in name for c in "*?["):
                lines.append("/%s/%s/**/%s" % (base, head, name))
            else:
                lines.append("/%s/%s" % (base, pattern))
        else:
            lines.append("/%s/**/%s" % (base, pattern))
    return lines


def guarded_gitignore(text, lines):
    """The brain's .gitignore text with the guard block in place: replaced when
    present, added at the end otherwise. Its own line endings are kept."""
    eol = "\r\n" if "\r\n" in (text or "") else "\n"
    block = eol.join(
        [PRUNE_GUARD_START,
         "# Written by `sync.py push --prune-local`. sync.py never carries these",
         "# paths (its never-sync list, both layouts); this block keeps git from",
         "# taking the leftover copies back in. The list itself lives in sync.py."]
        + list(lines) + [PRUNE_GUARD_END])
    text = text or ""
    if PRUNE_GUARD_START in text and PRUNE_GUARD_END in text:
        head, _, rest = text.partition(PRUNE_GUARD_START)
        _, _, tail = rest.partition(PRUNE_GUARD_END)
        return head + block + tail
    if text and not text.endswith(("\n", "\r")):
        text += eol
    return text + (eol if text else "") + block + eol


def prune_local(machine):
    """`push --prune-local`: the ONE commit that takes this machine's own files
    out of the brain. Never runs by itself, and is a commit of its own:
    `git rm --cached` (so nothing on this machine's disk is deleted), the guard
    block in the brain's .gitignore, and the list in the message. A second run
    finds nothing and says so. -> 0, or 1 when it stopped before any change."""
    if not MACHINE_LOCAL.get("patterns"):
        print("  i  --prune-local: the hub's own entry did not sync this run, so nothing "
              "was pruned.")
        return 0
    paths = machine_local_in_brain()
    if not paths:
        print("  i  --prune-local: nothing of this machine's own is in the brain — "
              "nothing to prune.")
        return 0
    code, _out, _err = _git_bytes(["diff", "--cached", "--quiet"])
    if code != 0:
        print("  !  --prune-local stopped before any change: the brain already has staged "
              "changes, and the prune must be a commit of its own. Run a plain push "
              "first, then this again.")
        return 1
    gitignore = REPO_ROOT / ".gitignore"
    before = read_text(gitignore)
    if before is None and gitignore.exists():
        print("  !  --prune-local stopped before any change: the brain's .gitignore at %s "
              "could not be read, and the guard block goes into it." % gitignore)
        return 1

    def undo(why):
        _git_bytes(["reset", "-q"])       # the index was clean before: HEAD again
        if before is None:
            try:
                gitignore.unlink()
            except OSError:
                pass
        else:
            write_text(gitignore, before)
        print("  !  --prune-local stopped and put everything back: %s" % why)
        return 1

    literal = {"GIT_LITERAL_PATHSPECS": "1"}
    for start in range(0, len(paths), PRUNE_CHUNK):
        code, _out, err = _git_bytes(
            ["rm", "-r", "--cached", "--quiet", "--"] + paths[start:start + PRUNE_CHUNK],
            env_extra=literal)
        if code != 0:
            return undo("git could not untrack %s (%s)" % (
                paths[start], " ".join((err or "no message").split())[:160]))
    base = MACHINE_LOCAL["repo_base"]
    after = guarded_gitignore(before, guard_lines(base, MACHINE_LOCAL["patterns"]))
    if after != (before or ""):
        write_text(gitignore, after)
        code, _out, err = _git_bytes(["add", "--", ".gitignore"], env_extra=literal)
        if code != 0:
            return undo("git could not stage the .gitignore guard (%s)"
                        % " ".join((err or "no message").split())[:160])
    groups = machine_local_groups(paths, depth=2)
    subject = ("BQ-101: %d file(s) of %s's own leave the brain"
               % (len(paths), machine.get("name") or "this machine"))
    body = "\n".join(
        ["The never-sync list (sync.py) now applies in both layouts; these paths were",
         "still tracked from before. git rm --cached: history keeps every byte and",
         "nothing on this machine's disk was deleted. The other machine's next pull",
         "removes only its brain clone's copies, never a live hub file (sync.py never",
         "carries these paths). The brain's .gitignore carries the guard block.",
         "",
         "Removed, by folder (the exact list is this commit's own diff):"]
        + ["  %s/%s %d" % (base, name, count) for name, count in groups])
    code, out = git("commit", "-q", "-m", subject, "-m", body)
    if code != 0:
        return undo("the commit failed (%s)" % " ".join((out or "").split())[:160])
    _c, sha = git("rev-parse", "--short", "HEAD")
    shown = " · ".join("%s %d" % (name, count)
                       for name, count in machine_local_groups(paths)[:8])
    print("  -- pruned %d file(s) of this machine's own from the brain in one commit "
          "(%s): %s. History keeps every byte; nothing on disk was deleted."
          % (len(paths), sha.strip(), shown))
    return 0


def project_repo_report(machine):
    """Unpushed / unpushable ~/Projects/* repos. Courtesy only."""
    root = redirect(Path(machine["roots"]["projects"]))
    rows = []
    if not root.is_dir():
        return rows
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not (entry / ".git").exists():
            continue
        def run(*args):
            result = subprocess.run(
                ["git", "-C", str(entry)] + list(args),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
            return result.returncode, result.stdout.strip()
        code, upstream = run("rev-parse", "--abbrev-ref", "@{u}")
        _, branch = run("rev-parse", "--abbrev-ref", "HEAD")
        _, dirty = run("status", "--porcelain")
        ahead = 0
        has_upstream = code == 0
        if has_upstream:
            code2, count = run("rev-list", "--count", "@{u}..HEAD")
            if code2 == 0 and count.isdigit():
                ahead = int(count)
        dirty_files = len([l for l in dirty.splitlines() if l.strip()])
        if ahead or not has_upstream or dirty_files:
            rows.append({"name": entry.name, "branch": branch or "?",
                         "ahead": ahead, "upstream": has_upstream,
                         "dirty": dirty_files})
    return rows


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def group(actions):
    buckets = {}
    for action in actions:
        buckets.setdefault(action.kind, []).append(action)
    return buckets


def show_list(actions, limit, prefix="      "):
    for action in actions[:limit]:
        print("%s%s" % (prefix, action.unit.repo_rel))
    if len(actions) > limit:
        print("%s… and %d more" % (prefix, len(actions) - limit))


def report_drift(buckets, limit=12):
    pulls = buckets.get(PULL, [])
    pushes = buckets.get(PUSH, [])
    conflicts = buckets.get(CONFLICT, [])
    merges = buckets.get(UNION, [])
    live_gone = buckets.get(LIVE_GONE, [])
    repo_gone = buckets.get(REPO_GONE, [])
    same = buckets.get(SAME, [])
    taken = buckets.get(OWNER_GONE, []) + buckets.get(CARRIED_GONE, [])
    print("  repo -> live (pull): %d" % len(pulls))
    show_list(pulls, limit)
    print("  live -> repo (push): %d" % len(pushes))
    show_list(pushes, limit)
    if taken:                                   #  one line, never a call
        print(takedown_line(len(taken), pending=True))
        show_list(taken, limit)
    lost = mass_line([a for kind in buckets.values() for a in kind])
    if lost:
        print(lost)
    if merges:
        # status reports and never writes: the union runs on the next pull or push.
        print("  ~  append-only, changed on BOTH sides — merged line by line, "
              "not flagged: %d" % len(merges))
        for action in merges:
            print("      would merge (append-only union): %s" % action.unit.repo_rel)
    if conflicts:
        print("  !! CONFLICT — changed on BOTH sides, NOT touched: %d"
              % len(conflicts))
        for action in conflicts:
            print("      %s" % action.unit.repo_rel)
            print("        live: %s" % action.unit.live)
            print("        repo: %s" % action.unit.repo)
            print("        why : %s" % action.why)
        print("      resolve by hand (merge or pick a side), then re-run sync.")
    if live_gone:
        print("  !  deleted here but still in the repo — needs your call: %d"
              % len(live_gone))
        show_list(live_gone, limit)
        print("      nothing was deleted. Delete the repo copy too, or "
              "restore the file, then re-run sync.")
    if repo_gone:
        print("  !  deleted in the repo but still here — needs your call: %d"
              % len(repo_gone))
        show_list(repo_gone, limit)
        print("      nothing was deleted locally.")
    print("  already in sync: %d" % len(same))


def settings_report(actions):
    rows = [a for a in actions if a.unit.report_only]
    if not rows:
        print("  settings.reference.json: absent on both sides")
        return
    reports = [a for a in rows if a.kind == REPORT]
    if not reports:
        for action in rows:
            if action.kind == SAME:
                print("  settings.reference.json: identical to this machine's "
                      "~/.claude/settings.json")
            elif action.kind == PUSH:
                print("  settings.reference.json: will be refreshed from this "
                      "machine's ~/.claude/settings.json on the next push "
                      "(one-way, so the other machine has something to "
                      "compare against)")
            else:
                print("  settings.reference.json: %s" % action.kind)
        return
    for action in reports:
        unit = action.unit
        print("  DRIFT (report-only — never applied automatically)")
        print("    live: %s" % unit.live)
        print("    repo: %s" % unit.repo)
        live_lines = _lines(unit.live)
        repo_lines = _lines(unit.repo)
        only_live = [l for l in live_lines if l not in repo_lines]
        only_repo = [l for l in repo_lines if l not in live_lines]
        print("    %d line(s) only on this machine, %d only in the repo"
              % (len(only_live), len(only_repo)))
        for line in only_live[:6]:
            print("      + %s" % line.strip()[:100])
        for line in only_repo[:6]:
            print("      - %s" % line.strip()[:100])
        print("    permissions and paths are machine-specific: decide by hand.")


def _lines(path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------
# verbs
# --------------------------------------------------------------------------

def load_state():
    return read_json(state_file(), {"version": 1, "units": {}}) or \
        {"version": 1, "units": {}}


def prune_program_state(state):
    """A path the program owns must leave no trace in this tool's bookkeeping.

    The record of what was carried is a record of the BRAIN. Once the partition
    is on, a key for a file git tracks would outlive the file's move to the
    other carrier and would make a later sync argue about a file it does not
    own. -> the number of keys retired."""
    classes = PARTITION_REPORT.get("classes") or {}
    if not classes:
        return 0
    base = PARTITION_REPORT.get("repo_base") or "orchestrator"
    units = state.get("units") or {}
    gone = [base + "/" + rel for rel, kind in classes.items()
            if kind in (CLASS_PROGRAM, CLASS_PENDING, CLASS_NEVER)]
    dropped = 0
    for key in gone:
        if key in units:
            del units[key]
            dropped += 1
    return dropped


def prune_machine_local_state(state):
    """A path this machine keeps to itself leaves no key in the record either:
    the hub entry never builds a unit for it, so a key would only
    ever be a stale answer to a question no run asks. -> keys retired."""
    base = MACHINE_LOCAL.get("repo_base")
    patterns = MACHINE_LOCAL.get("patterns")
    if not base or not patterns:
        return 0
    units = state.get("units") or {}
    prefix = base + "/"
    gone = [key for key in units
            if key.startswith(prefix) and excluded(key[len(prefix):], patterns)]
    for key in gone:
        del units[key]
    return len(gone)


def save_state(state):
    prune_program_state(state)
    prune_machine_local_state(state)
    state["last_sync"] = now_iso()
    write_json(state_file(), state)


def refresh_manifest(machine, manifest, memory_map):
    """Record this machine's roots and its memory munging in the manifest.

    Other machines' records are merged, never dropped.
    """
    before = read_json(MANIFEST_FILE, {}) or {}
    # What the file said before this run changed anything. It has to be a COPY:
    # the merge below adopts `before` as the manifest and edits it in place, so
    # comparing the two at the end would be comparing one object with itself,
    # and nothing would ever be written. (That is exactly what happens in the
    # older layout today — the machines block and the memories map have not
    # been written since the file first existed. The fix is scoped to the
    # program-tree layout here because changing it is a behaviour change on a
    # running older installation, and that is a change of its own.)
    original = (json.loads(json.dumps(before)) if LAYOUT == LAYOUT_PROGRAM else before)
    # The file may have moved under us since this process read it (a pull
    # landed the other machine's edit, or a session edited it by hand while
    # we ran).  Merge THIS machine's records into the fresh copy and never
    # write the stale in-memory one back over it (else a hub's exclude-list
    # edit could be reverted by the next push from another session).
    if before:
        stale = manifest
        manifest = before
        if LAYOUT != LAYOUT_PROGRAM:
            for key, value in stale.items():
                if key not in manifest:
                    manifest[key] = value
        # In a program tree the file on disk is the USER's half and nothing
        # else. Filling its gaps from the merged manifest would copy the
        # program's own entries into it, and the next release's changes to
        # them would never be seen again.
    elif LAYOUT == LAYOUT_PROGRAM:
        # A program tree's user manifest is the user's half ONLY. Without this,
        # the first push would write the program's own entries into the brain,
        # and the next release's changes to them would never be seen again.
        manifest = {"description": "Your half of the manifest. The program ships the rest "
                                   "in sync/%s and reads it first; what is here is merged "
                                   "on top. Add entries and extend an entry's exclude and "
                                   "append_only lists; machines and memories.map are "
                                   "written by the tool." % BASE_MANIFEST_NAME,
                    "version": 1}
    manifest.setdefault("machines", {})[machine["name"]] = {
        "os": machine.get("os", ""),
        "roots": machine["roots"],
        "last_seen": now_iso(),
    }
    mem = manifest.setdefault("memories", {})
    mem.setdefault("repo_base", "claude-home/memories")
    mem["map"] = memory_map
    if _same_but_for_timestamp(original, manifest):
        # Nothing real changed. Leave the file alone rather than manufacture a
        # commit on every sync — a no-op sync should read as a no-op.
        return manifest
    write_json(MANIFEST_FILE, manifest)
    return manifest


def _same_but_for_timestamp(first, second):
    def stripped(data):
        copy = json.loads(json.dumps(data, sort_keys=True))
        for record in copy.get("machines", {}).values():
            if isinstance(record, dict):
                record.pop("last_seen", None)
        return copy
    return stripped(first) == stripped(second)


def layout_line():
    """The one line a run says about where it is standing, or None.

    An older installation working normally has nothing to say here, and says
    nothing: its output is what it has always been."""
    if RESOLVER_NOTE:
        return "  i  %s" % RESOLVER_NOTE
    if LAYOUT == LAYOUT_PROGRAM:
        return "  layout    : program tree · hub %s · brain %s" % (HUB, BRAIN)
    return None


def say_layout():
    line = layout_line()
    if line:
        print(line)


def partition_block():
    """What the partition did this run — printed only when there IS one."""
    report = PARTITION_REPORT or {}
    mode = report.get("mode", "off")
    if mode == "off":
        return
    print("")
    print("THE HUB FOLDER, DIVIDED")
    if mode == "stopped":
        print("  the hub's own entry did not sync. Every other entry did.")
        for sentence in report.get("problems", [])[:6]:
            print("  !  %s" % sentence)
        return
    counts = report.get("counts", {})
    print("  yours, carried by this sync : %d" % counts.get(CLASS_BRAIN, 0))
    print("  the program's, carried by git: %d" % counts.get(CLASS_PROGRAM, 0))
    print("  this machine's own (machine.json, installed.json, scratch/, the pages")
    print("  drawn here): never walked at all, in either direction")
    pending = report.get("pending", [])
    if pending:
        print("  !  %d file(s) ride NEITHER carrier — git neither tracks nor ignores them:"
              % len(pending))
        for rel in pending[:12]:
            print("      %s" % pending_warning(rel))
    else:
        print("  every file rides one carrier or the other.")


def manifest_block():
    """Where each entry came from — printed only when two files were merged."""
    if not MANIFEST_ORIGIN or set(MANIFEST_ORIGIN.values()) == {"user"}:
        return
    print("")
    print("THE MANIFEST (the program's, with yours on top)")
    for entry_id in sorted(MANIFEST_ORIGIN):
        print("  %-22s %s" % (entry_id, MANIFEST_ORIGIN[entry_id]))
    for note in MANIFEST_NOTES:
        print("  !  %s" % note)


def cmd_status(args):
    machine = load_machine()
    manifest = load_manifest()
    state = load_state()
    units, notes, memory_map = build_units(machine, manifest)
    actions = plan(units, state)
    buckets = group(actions)

    print("%s status" % PROGRAM_NAME)
    print("  machine   : %s (%s)" % (machine["name"], machine.get("os", "?")))
    print("  repo      : %s" % REPO_ROOT)
    say_layout()
    print("  time      : %s" % now_iso())
    if test_root():
        print("  TEST MODE : live side redirected under %s" % test_root())
    print("")

    print("GIT")
    _, porcelain = git("status", "--porcelain")
    dirty = len([l for l in porcelain.splitlines() if l.strip()])
    print("  branch %s, working tree %s"
          % (git_branch(), "clean" if dirty == 0 else "%d changed path(s)" % dirty))
    code, counts = git("rev-list", "--left-right", "--count", "@{u}...HEAD")
    if code == 0 and "\t" in counts:
        behind, ahead = counts.split("\t")[:2]
        print("  %s behind / %s ahead of origin" % (behind.strip(), ahead.strip()))
    else:
        print("  no upstream comparison available (nothing fetched yet?)")
    commits = git_sync_commits()
    mine = [c for c in commits if c[2] == machine["name"]]
    theirs = [c for c in commits if c[2] != machine["name"]]
    if mine:
        print("  this machine's last sync commit: %s (%s)"
              % (age_phrase(parse_iso(mine[0][1])), mine[0][0]))
    else:
        print("  this machine has not pushed a sync commit yet")
    if theirs:
        print("  other machine (%s) last sync commit: %s (%s)"
              % (theirs[0][2], age_phrase(parse_iso(theirs[0][1])), theirs[0][0]))
    else:
        print("  the other machine has not pushed a sync commit yet")
    print("")

    print("DRIFT (%d files under the manifest)" % len(units))
    report_drift(buckets)
    partition_block()
    mistake_block(machine_local_in_brain())
    manifest_block()
    print("")

    print("SETTINGS")
    settings_report(actions)
    print("")

    print("MEMORIES")
    resolved = [k for k, v in memory_map.items() if v.get("root")]
    unresolved = [k for k, v in memory_map.items() if not v.get("root")]
    print("  logical projects mapped: %d" % len(resolved))
    for logical in sorted(resolved):
        record = memory_map[logical]
        print("    %-28s %s/%s" % (logical, record["root"], record["rel"] or ""))
    if unresolved:
        print("  could not be un-munged to a real folder on this machine: %d"
              % len(unresolved))
        for logical in sorted(unresolved):
            print("    %-28s munged=%s" % (
                logical, memory_map[logical].get("munged", {})))
    print("")

    rows = project_repo_report(machine)
    print("PROJECT REPOS (~/Projects — NOT synced here, courtesy only)")
    if not rows:
        print("  nothing unpushed, unpushable or dirty")
    for row in rows:
        bits = []
        if row["ahead"]:
            bits.append("%d unpushed commit(s)" % row["ahead"])
        if not row["upstream"]:
            bits.append("no upstream branch")
        if row["dirty"]:
            bits.append("%d uncommitted path(s)" % row["dirty"])
        print("  %-46s %-24s %s" % (row["name"][:46], row["branch"][:24],
                                    ", ".join(bits)))
    print("")

    unsafe = [u for u in units if windows_unsafe(u.repo_rel)]
    print("PORTABILITY")
    if unsafe:
        print("  %d path(s) cannot exist on Windows — they will fail to check "
              "out on a Windows machine:" % len(unsafe))
        for unit in unsafe[:10]:
            print("      %s  (%s)" % (unit.repo_rel, windows_unsafe(unit.repo_rel)))
    else:
        print("  every synced path is legal on both macOS and Windows")
    print("")

    print("NOT SYNCED, BY DESIGN")
    for line in manifest.get("never_synced", []):
        print("  %s" % line)
    for note in notes:
        print("  note: %s" % note)
    return 0


def _preflight(machine, timeout=5.0):
    """The carriers, checked before the brain moves.

    Fail-safe by construction: a missing, broken or half-written carrier_preflight.py becomes
    one `carriers: skipped` line and the pull carries on. The brain never waits on the drive."""
    try:
        # Beside this file, in the sync package — never from the brain: in a
        # program tree the brain holds no code at all.
        if str(SYNC_DIR) not in sys.path:
            sys.path.insert(0, str(SYNC_DIR))
        import carrier_preflight
        return carrier_preflight.check_and_report(
            machine,
            live_path(machine, "orchestrator", ""),
            live_path(machine, "projects", ""),
            timeout=timeout)
    except Exception as exc:
        one_line = " ".join(("%s: %s" % (type(exc).__name__, exc)).split())[:200]
        print("  carriers: skipped — %s" % one_line)
        return None


def cmd_preflight(args):
    """The carrier check on its own — for a script that wants to gate on it."""
    machine = load_machine()
    print("%s preflight — machine %s" % (PROGRAM_NAME, machine["name"]))
    result = _preflight(machine, timeout=getattr(args, "timeout", 5.0) or 5.0)
    if result is None:
        return 0
    return 3 if result.get("missing") else 0


def cmd_carriers(args):
    """Edit (or show) this machine's `carriers` block. Nobody hand-edits JSON."""
    target = Path(args.file).resolve() if args.file else MACHINE_FILE
    data = read_json(target)
    if data is None:
        die("cannot read %s — run:  python sync.py bootstrap --machine <name>" % target)
    block = data.get("carriers")
    if not isinstance(block, dict):
        block = {}
    changed = False
    if args.drive:
        block["drive"] = {"label": args.drive.strip()}
        changed = True
    if args.forget_drive:
        block.pop("drive", None)
        changed = True
    if args.host:
        name, url = args.host[0], args.host[1]
        repos = [r.strip() for r in (args.repos or "").split(",") if r.strip()]
        hosts = [h for h in (block.get("hosts") or [])
                 if isinstance(h, dict) and h.get("name") != name]
        hosts.append({"name": name, "url": url, "repos": repos})
        block["hosts"] = hosts
        changed = True
    if args.forget_host:
        block["hosts"] = [h for h in (block.get("hosts") or [])
                          if isinstance(h, dict) and h.get("name") != args.forget_host]
        changed = True
    if changed:
        data["carriers"] = block
        write_json(target, data)
    print("%s carriers — %s%s" % (PROGRAM_NAME, target,
                                  " (written)" if changed else ""))
    if not block:
        print("  nothing declared. The drive is named by its LABEL, never a letter:")
        print('    python sync.py carriers --drive "<volume label>"')
    else:
        for line in json.dumps(block, indent=2, ensure_ascii=False,
                               sort_keys=True).splitlines():
            print("  %s" % line)
    return 0


def cmd_pull(args):
    machine = load_machine()
    manifest = load_manifest()
    print("%s pull — machine %s" % (PROGRAM_NAME, machine["name"]))
    say_layout()
    _preflight(machine)          # the carriers, before any git — the sentence lands first
    if test_root():
        print("  TEST MODE: live side redirected under %s" % test_root())
        print("  git: skipped (a rehearsal never touches the repo's history)")
        return _pull_copy(machine)
    branch = git_branch()
    code, _ = git("rev-parse", "--verify", "--quiet", "origin/%s" % branch)
    if code != 0:
        git("fetch", "origin")
        code, _ = git("rev-parse", "--verify", "--quiet", "origin/%s" % branch)
    if code != 0:
        print("  git: origin/%s does not exist yet — nothing to pull. "
              "(First push will create it.)" % branch)
    else:
        code, out = git("pull", "--rebase=false", "--no-edit")
        for line in out.splitlines():
            print("  git: %s" % line)
        if code != 0:
            print("  git pull did not succeed — copying nothing. Fix the repo "
                  "first (conflicts in git are yours to resolve).")
            return 1
    return _pull_copy(machine)


def _pull_copy(machine):
    manifest = load_manifest()
    state = load_state()
    units, notes, memory_map = build_units(machine, manifest)
    actions = plan(units, state)
    buckets = group(actions)
    copied = 0
    for action in buckets.get(PULL, []):
        apply_action(action, state)
        copied += 1
        print("  <- %s" % action.unit.repo_rel)
        if action.say:
            print("  ~  %s" % action.say)
    merged = _apply_unions(buckets, state)
    taken = _apply_takedowns(buckets, state)
    remember_same(actions, state)
    save_state(state)
    print("  pulled %d file(s) into the live folders." % copied)
    if merged:
        print("  ~  %d append-only file(s) merged by line union — nothing was lost." % merged)
    _tail(buckets, notes, taken)
    return 0


def _apply_unions(buckets, state):
    """Append-only files that moved on both sides: merged, written to BOTH
    sides, and remembered — so the next sync sees them identical."""
    merged = 0
    for action in buckets.get(UNION, []):
        if apply_action(action, state):
            merged += 1
            print("  merged (append-only union): %s +%d from the other machine"
                  % (action.unit.repo_rel, action.merged_from_repo))
    return merged


def cmd_push(args):
    machine = load_machine()
    local_push = None
    if test_root():
        local_push = test_push_target()
        if local_push is None:
            die("push is refused while ORCHSYNC_TEST_ROOT is set — a rehearsal "
                "must never write scratch files back into the repo. Unset it.")
    manifest = load_manifest()
    state = load_state()
    print("%s push — machine %s" % (PROGRAM_NAME, machine["name"]))
    say_layout()
    if local_push:
        print("  i  test push to local origin %s" % local_push)
    units, notes, memory_map = build_units(machine, manifest)
    if getattr(args, "prune_local", False):
        # a commit of its own, made before anything else is staged.
        if prune_local(machine) != 0:
            return 1
    actions = plan(units, state)
    buckets = group(actions)

    # The settling window. A file younger than --settle seconds is not copied,
    # not committed, and NOT recorded as synced - apply_action is what writes
    # the state record (the race fixed in ee7d698), so a waiting file is still
    # "changed here" on the next push and `status` still shows it as drift.
    settle = settle_seconds(args)
    pushes = buckets.get(PUSH, [])
    waiting = []
    if settle and pushes:
        carry, waiting = select_for_push(
            [(a.unit.repo_rel, mtime_of(a.unit.live)) for a in pushes],
            time.time(), settle)
        carried = set(carry)
        pushes = [a for a in pushes if a.unit.repo_rel in carried]

    copied = 0
    for action in pushes:
        apply_action(action, state)
        copied += 1
        print("  -> %s" % action.unit.repo_rel)
        if action.say:
            print("  ~  %s" % action.say)
    merged = _apply_unions(buckets, state)
    taken = _apply_takedowns(buckets, state)       #  before `git add -A` stages them
    remember_same(actions, state)
    refresh_manifest(machine, manifest, memory_map)
    save_state(state)
    print("  staged %d changed file(s) from the live folders." % copied)
    settled_note = settling_line(waiting, settle)
    if settled_note:
        print(settled_note)
    if merged:
        print("  ~  %d append-only file(s) merged by line union — nothing was lost." % merged)

    git("add", "-A")
    _, staged = git("diff", "--cached", "--name-only")
    if staged.strip():
        message = "sync: %s %s" % (machine["name"], now_iso())
        code, out = git("commit", "-m", message)
        for line in out.splitlines()[:4]:
            print("  git: %s" % line)
        if code != 0:
            print("  commit failed — nothing pushed.")
            return 1
    else:
        print("  nothing new to commit.")
    if not push_destination():
        # The local-only road (install.py's second honest road): there is no
        # destination at all, so nothing can go anywhere. Say it plainly rather
        # than let git print its own refusal on every beat.
        print("  i  this brain has no remote yet, so nothing was sent. Everything is "
              "committed here. When you have a private repository for it:")
        print("       git -C %s remote add origin <url>" % REPO_ROOT)
        _tail(buckets, notes, taken)
        return 0
    allowed, refusal = privacy_gate(machine)
    if not allowed:
        print("  %s" % refusal)
        # A stop nobody hears is a stop that happens again tomorrow: one line
        # for this machine's hub, the same road a failed push takes.
        privacy_stop_mail(machine, refusal, state)
        save_state(state)
        _tail(buckets, notes, taken)
        return 0
    retries = push_retries(args)
    # one INBOX line for this machine's hub once the failure is a real one
    # (never a red wall to read, never a letter about a beat the next beat repairs),
    # and every such letter closed by the push that lands.
    code, _ = push_and_mind(machine, state, git, git_branch(), retries)
    save_state(state)
    if code != 0:
        print("  push failed. The commit is safe locally; re-run after fixing.")
        return 1
    _tail(buckets, notes, taken)
    return 0


def _tail(buckets, notes, taken=0):
    conflicts = buckets.get(CONFLICT, [])
    live_gone = buckets.get(LIVE_GONE, [])
    repo_gone = buckets.get(REPO_GONE, [])
    if takedown_line(taken):                    #  one line, never a call
        print(takedown_line(taken))
    lost = mass_line([a for kind in buckets.values() for a in kind])
    if lost:
        print(lost)
    if conflicts:
        print("  !! %d CONFLICT(S) skipped — nothing was overwritten:"
              % len(conflicts))
        for action in conflicts:
            print("       %s" % action.unit.repo_rel)
    if live_gone or repo_gone:
        print("  !  %d deletion(s) need your call (nothing was deleted):"
              % (len(live_gone) + len(repo_gone)))
        for action in live_gone + repo_gone:
            print("       %s (%s)" % (action.unit.repo_rel, action.kind))
    if buckets.get(REPORT):
        print("  i  settings.reference.json differs from live settings.json "
              "(report-only, untouched).")
    for note in notes:
        print("  note: %s" % note)


def cmd_recover(args):
    """Put back every file the mirror holds and this machine has lost.

    Git treats the files it ignores as expendable, so losing them is an
    ORDINARY event here, not a disaster: one command brings the live brain
    back from the mirror. Nothing that is still here is touched, so a file you
    edited since the last sync survives this. A second run does nothing and
    says so."""
    machine = load_machine()
    manifest = load_manifest()
    state = load_state()
    print("%s recover — machine %s" % (PROGRAM_NAME, machine["name"]))
    say_layout()
    print("  from the mirror at %s" % REPO_ROOT)
    units, notes, _memory_map = build_units(machine, manifest)
    restored, kept = 0, 0
    for unit in units:
        if unit.report_only or not unit.repo.is_file():
            continue
        if unit.live.exists():
            kept += 1
            continue
        if getattr(args, "dry_run", False):
            print("  would restore %s" % unit.repo_rel)
            restored += 1
            continue
        unit.live.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(unit.repo), str(unit.live))
        digest = sha256_of(unit.repo)
        state.setdefault("units", {})[unit.repo_rel] = {
            "live": digest, "repo": digest, "ts": now_iso()}
        restored += 1
        print("  <- %s" % unit.repo_rel)
    if not getattr(args, "dry_run", False):
        save_state(state)
    if restored:
        print("  restored %d file(s); %d were already here and were not touched."
              % (restored, kept))
    else:
        print("  nothing was missing — every file the mirror holds is already here (%d)."
              % kept)
    for note in notes:
        print("  note: %s" % note)
    return 0


def cmd_sync(args):
    code = cmd_pull(args)
    if code != 0:
        return code
    print("")
    return cmd_push(args)


def cmd_bootstrap(args):
    name = args.machine.strip()
    if not name:
        die("--machine needs a short name, e.g. laptop or desktop")
    home = Path.home()
    roots = {
        "home": str(home),
        "claude": str(Path(args.claude_root) if args.claude_root
                      else home / ".claude"),
        "projects": str(Path(args.projects_root) if args.projects_root
                        else home / "Projects"),
        # Every machine's hub folder is ~/Exocortex by default. The
        # repo side is unaffected: a memory folder the map already names keeps
        # the name the map gave it.
        "orchestrator": str(Path(args.orchestrator_root) if args.orchestrator_root
                            else home / "Exocortex"),
    }
    machine = {
        "name": name,
        "os": "%s %s" % (platform.system(), platform.release()),
        "roots": roots,
        "bootstrapped": now_iso(),
    }
    # A program tree says so in its own record, and says where the brain is and
    # how the folder is divided. Nothing is ever inferred from a .git folder
    # later on: what is not written here is not true.
    # roots.brain is NOT one of ROOT_KEYS: it is where the mirror lives, never a
    # place live files are read from, and putting it in ROOT_KEYS would let the
    # memory un-munger resolve folders inside the brain clone.
    target = Path(args.machine_file) if getattr(args, "machine_file", None) else MACHINE_FILE
    if getattr(args, "layout", None) == LAYOUT_PROGRAM:
        roots["brain"] = str(Path(args.brain_root).expanduser() if args.brain_root
                             else home / BRAIN_FOLDER_DEFAULT)
        roots["sync"] = str(Path(roots["orchestrator"]) / "sync")
        machine["layout"] = LAYOUT_PROGRAM
        machine["partition"] = args.partition or PARTITION_GIT
        target = Path(roots["orchestrator"]) / "machine.json"
    elif getattr(args, "brain_root", None):
        roots["brain"] = str(Path(args.brain_root).expanduser())
    write_json(target, machine)
    print("%s bootstrap" % PROGRAM_NAME)
    print("  wrote %s" % target)
    for key in ROOT_KEYS:
        path = Path(roots[key])
        print("    %-13s %s%s" % (key, path, "" if path.exists()
                                  else "   (does not exist yet)"))
    if "brain" in roots:
        path = Path(roots["brain"])
        print("    %-13s %s%s" % ("brain", path, "" if path.exists()
                                  else "   (does not exist yet)"))
    print("  machine.json is gitignored — it is this machine's identity only.")
    print("")
    _resolve()                 # the record it just wrote is the record it works from
    if getattr(args, "no_pull", False):
        return 0
    return cmd_pull(args)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Two-machine sync for the exocortex's brain. "
                    "HOME SIDE ONLY.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="the brain privacy guard\n"
               "  Before a push that has something to send, this tool works out the address\n"
               "  the push would really reach and checks that it is not publicly readable. A\n"
               "  public answer stops the push before any byte; so does no answer at all, and\n"
               "  the next beat asks again. Either way the local sync finishes.\n"
               "  What it cannot cover: the moment AFTER the check. A destination made public\n"
               "  between the check and the transfer is a window nothing on this side closes.\n"
               "  `recover` puts back every live file the mirror holds and this machine has\n"
               "  lost; it overwrites nothing that is still here.\n")
    subs = parser.add_subparsers(dest="verb")
    subs.add_parser("status", help="what has drifted, both directions")
    subs.add_parser("pull", help="git pull, then repo -> live")
    rec = subs.add_parser("recover",
                          help="restore every live file the mirror holds and this "
                               "machine lacks (nothing is overwritten)")
    rec.add_argument("--dry-run", action="store_true",
                     help="name what would be restored and change nothing")
    for verb, helptext in (("push", "live -> repo, commit, push"),
                           ("sync", "pull then push (the normal verb)")):
        sub = subs.add_parser(verb, help=helptext)
        sub.add_argument("--settle", type=int, default=None, metavar="N",
                         help="seconds a changed file must have been still "
                              "before this push carries it (default %d, or "
                              "ORCHSYNC_SETTLE; 0 carries everything, which "
                              "is what button-up passes)" % SETTLE_DEFAULT)
        sub.add_argument("--retries", type=int, default=None, metavar="N",
                         help="attempts at `git push` when another writer got "
                              "there first (default %d, or "
                              "ORCHSYNC_PUSH_RETRIES)" % PUSH_RETRIES_DEFAULT)
        if verb == "push":
            sub.add_argument("--prune-local", action="store_true",
                             help="first, ONE commit that takes this machine's own "
                                  "files (the never-sync list: scratch/, the pages "
                                  "drawn here, ...) out of the brain: git rm --cached, "
                                  "so nothing on disk is deleted and history keeps "
                                  "every byte. Off by default; never runs by itself")
    pre = subs.add_parser("preflight",
                          help="check the carriers alone (exit 3 when one is missing)")
    pre.add_argument("--timeout", type=float, default=5.0,
                     help="seconds per private host (default 5, capped at 10)")
    car = subs.add_parser("carriers",
                          help="show or edit this machine's carriers block in machine.json")
    car.add_argument("--show", action="store_true", help="print the block (the default)")
    car.add_argument("--drive", metavar="LABEL", default=None,
                     help='the transfer drive\'s volume LABEL, e.g. --drive "Transfer"')
    car.add_argument("--forget-drive", action="store_true", help="clear the drive")
    car.add_argument("--host", nargs=2, metavar=("NAME", "URL"), default=None,
                     help="add or replace a private git host")
    car.add_argument("--repos", default=None, metavar="a,b",
                     help="the repos that sync through --host")
    car.add_argument("--forget-host", metavar="NAME", default=None, help="remove a host")
    car.add_argument("--file", default=None,
                     help="edit this machine.json instead of the real one (rehearsals)")
    boot = subs.add_parser("bootstrap", help="first run on a machine")
    boot.add_argument("--machine", required=True,
                      help="short machine name, e.g. laptop or desktop")
    boot.add_argument("--projects-root", default=None)
    boot.add_argument("--orchestrator-root", default=None,
                      help="the hub folder on this machine (default ~/Exocortex)")
    boot.add_argument("--claude-root", default=None)
    boot.add_argument("--brain-root", default=None,
                      help="where the brain clone lives (a program tree's default is "
                           "~/%s)" % BRAIN_FOLDER_DEFAULT)
    boot.add_argument("--layout", choices=(LAYOUT_LEGACY, LAYOUT_PROGRAM), default=None,
                      help="record which layout this machine is in; a program tree also "
                           "records how the hub folder is divided")
    boot.add_argument("--partition", default=None,
                      help="the division a program tree records (default %s)"
                           % PARTITION_GIT)
    boot.add_argument("--machine-file", default=None,
                      help="write this machine.json instead of the resolved one")
    boot.add_argument("--no-pull", action="store_true",
                      help="write the record and stop, without pulling")
    args = parser.parse_args(argv)
    if not args.verb:
        parser.print_help()
        return 1
    handlers = {"status": cmd_status, "pull": cmd_pull, "push": cmd_push,
                "sync": cmd_sync, "bootstrap": cmd_bootstrap,
                "recover": cmd_recover,
                "preflight": cmd_preflight, "carriers": cmd_carriers}
    try:
        if args.verb in {"pull", "push", "sync", "recover", "bootstrap"}:
            with transaction_lock(args.verb):
                return handlers[args.verb](args)
        return handlers[args.verb](args)
    except SyncBusy as busy:
        sys.stderr.write(str(busy) + "\n")
        return 5
    except SyncStop as stop:
        # One plain sentence, never a traceback: this tool is read by a person
        # at the end of a five-minute beat.
        sys.stderr.write("%s: %s\n" % (PROGRAM_NAME, stop))
        return 2


if __name__ == "__main__":
    sys.exit(main())
