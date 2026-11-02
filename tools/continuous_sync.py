#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""continuous_sync.py — THE CONTINUOUS SYNC: the projects level on both machines, every beat.

HALF A, THE GITHUB BEAT (this file). Each pulse beat, for every project the carry
registry (`carry/projects.json`) records as `carrier: github` and `confirmed: true` whose folder is
on this machine and that NO live session holds:

    fetch origin  ·  a clean branch that is behind catches up, fast-forward only  ·  a branch that is
    ahead and not behind pushes its already-committed commits  ·  and nothing else, ever.

It never commits, never merges, never rebases, never forces, never creates a remote or a branch on
the remote, never touches a `carrier: drive` project (half B, the home link, carries those), and
never touches a repo a live session holds. One line per repo it moved. A repo it cannot carry
safely is HELD — dirty tracked files with commits waiting, both sides moved, a remote that is not
the one the registry recorded, a tracked file over the 90 MB law, a git operation in progress —
with ONE line naming the owner and the next move, ONE letter to this machine's hub the first time
(never every beat), and a row in `held-<machine>.json` (brain-carried, so the tree on either
machine can say it on the lane's tile).

    python3 tools/continuous_sync.py --beat    [--hub DIR] [--projects DIR] [--dry] [--no-mail] [--json]
    python3 tools/continuous_sync.py --status  [--hub DIR]
    python3 tools/continuous_sync.py --help

WHAT HOLDS A REPO: a session in this machine's `live-sessions-<machine>.json` (the
pulse's own sense of the transcripts touched in the last ten minutes) whose folder is the repo, is
inside it, or contains it; and a claim in `claims.json` on THIS machine, younger than 12 hours,
whose arc is one of the repo's arcs (the registry's `arcs`, else its openers' lane prefixes, else
its folder name). A `button-up` or `rename` claim on this machine holds EVERY repo: the button-up
carries them itself. Git worktrees that share one repository are held together — a fetch in one
writes the others' refs. A live file older than LIVE_FILE_MINUTES holds every repo: the beat never
acts on a stale picture of who is working (run it from the pulse, which senses first).

THE RAILS. Every git call is bounded and tree-killed (exo_common.run_bounded); a credential prompt
can never hang it (GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never). The beat stops starting network
work after BEAT_BUDGET seconds and names what waits; a link that is slow or down is never retried
in the same beat: the rest wait for the next beat, said in one line. The order
rotates beat to beat, so no repo is always last.

ONE COPY OF THE PULL. `pull_ff` is the catch-all pull's own code: `buttonup.py arrive` calls it for
every repo it pulls (its first-beat case), and the beat calls it after its own fetch. The output
guide is the law's: level · caught-up · no-remote (expected on a drive-lane repo) · partial (the
link) · stop (git refused; its own words) — decided by the SHAs before and after, never by parsing
git's prose.

THE RECORD it writes: `held-<machine>.json` in the hub (rewritten only when what is held changes,
so the brain carries no churn) · its machine-personal state `~/.exocortex/csync/csync-<machine>.json`
(the rotation cursor and which HELD letters were already sent; never synced; losing it costs at
most one repeated letter) · letters through `tools/mail.py --send <MACHINE>/hub … --no-push` (the
beat's own brain push carries them).

THE SWITCH: on once installed; `EXO_REPO_BEAT=0` (one run) or `"repo_beat": false` in machine.json
(this machine) turns it off, and the beat then says so in one line.

SEAMS, for the gate and nothing else: `--hub`, `--projects` and `--state-dir` (or
EXO_CSYNC_STATE_DIR) point every read and write into a scratch world; EXO_CSYNC_MAIL_FILE makes a
letter a line appended to that file instead of a mail.py call; EXO_CSYNC_BUDGET overrides
BEAT_BUDGET and EXO_CSYNC_FETCH_TIMEOUT the fetch rail. The origin a fixture repo fetches from is a `file://` bare repository, so the gate
needs no network. Half B's `local` transport seam is documented in tools/homelink.py.

Stdlib only, Python 3.9, macOS and Windows: argument lists, never a shell; paths by pathlib; no
symlink, no chmod. Exit 0 = the beat ran (HELD is not a failure) · 1 = a repo errored this beat
(git refused a fetch or a push for a reason that is not the link) · 2 = usage.
"""
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TOOL_VERSION = "A.1"
LIVE_FILE_MINUTES = 15          # the pulse rewrites the live file every 5 min; older = unknown
CLAIM_HOURS = 12                # claim.py's own reaping age
BEAT_BUDGET = 150               # seconds of network work per beat; the pulse's rail is REPO_BEAT_TIMEOUT
FETCH_TIMEOUT = 60
PUSH_TIMEOUT = 120
LOCAL_TIMEOUT = 60
PULL_TIMEOUT_ATTENDED = 1800    # arrive's own rail for `git pull --ff-only`
BIG_FILE_MB = 90                # the button-up law's number: over this, flagged, never pushed
WHOLE_BEAT_ARCS = ("button-up", "rename")
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
SLOW_LINK = re.compile(r"TIMEOUT after|\b408\b|timed out|Operation too slow|RPC failed|"
                       r"unexpected disconnect|early EOF", re.I)
# The network itself, never the answer: an authentication or permission refusal also says
# "unable to access", so it is NOT here — it is a refusal, HELD with a letter, not a quiet beat.
OFFLINE = re.compile(r"Could not resolve host|Failed to connect|Couldn't connect to server|"
                     r"Network is unreachable|No route to host|Connection refused", re.I)
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge",
               "rebase-apply")
FETCH_TIMEOUT_ENV = "EXO_CSYNC_FETCH_TIMEOUT"
STATE_ENV = "EXO_CSYNC_STATE_DIR"
MAIL_FILE_ENV = "EXO_CSYNC_MAIL_FILE"
BUDGET_ENV = "EXO_CSYNC_BUDGET"
SWITCH_ENV = "EXO_REPO_BEAT"
KNOWN = ("--beat", "--status", "--hub", "--projects", "--state-dir", "--dry", "--no-mail",
         "--json", "--help", "-h")
VALUED = ("--hub", "--projects", "--state-dir")


def say(text=""):
    print(text)
    sys.stdout.flush()


def now_iso():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def parse_iso(text):
    s = str(text or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        when = datetime.fromisoformat(s)
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def age_seconds(text):
    when = parse_iso(text)
    if when is None:
        return None
    return (datetime.now(timezone.utc) - when).total_seconds()


def read_json(path, default=None):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def write_atomic(path, text):
    """Temp file beside it, then replace — a killed beat never leaves half a file."""
    path = Path(path)
    tmp = path.with_name(".%s.%d.tmp" % (path.name, os.getpid()))
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(str(tmp), str(path))


# --------------------------------------------------------------------------
# git — bounded, tree-killed, never prompting
# --------------------------------------------------------------------------

_RUNNER = [None]


def _runner():
    if _RUNNER[0] is None:
        try:
            from exo_common import run_bounded                          # noqa: E402
            _RUNNER[0] = run_bounded
        except Exception:
            import subprocess

            def fallback(args, cwd=None, timeout=300, env=None):
                try:
                    p = subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None,
                                       env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=timeout)
                    return p.returncode, (p.stdout or b"").decode("utf-8", "replace").strip()
                except subprocess.TimeoutExpired:
                    return 124, "TIMEOUT after %ss" % timeout
                except Exception as exc:
                    return 125, repr(exc)
            _RUNNER[0] = fallback
    return _RUNNER[0]


def git(repo, *args, timeout=LOCAL_TIMEOUT):
    env = dict(os.environ)
    env.update(GIT_ENV)
    return _runner()(["git", "-C", str(repo)] + [str(a) for a in args], timeout=timeout, env=env)


def git_line(repo, *args, timeout=LOCAL_TIMEOUT):
    code, out = git(repo, *args, timeout=timeout)
    return out.strip().splitlines()[0].strip() if (code == 0 and out.strip()) else ""


def is_repo(path):
    """A folder with `.git` — a directory, or the one-line file a worktree carries."""
    try:
        return (Path(path) / ".git").exists()
    except OSError:
        return False


def head_sha(repo):
    return git_line(repo, "rev-parse", "HEAD")


def current_branch(repo):
    """The checked-out branch, or '' when HEAD is detached."""
    return git_line(repo, "symbolic-ref", "--quiet", "--short", "HEAD")


def upstream_of(repo, branch):
    return git_line(repo, "rev-parse", "--abbrev-ref", "%s@{upstream}" % branch) if branch else ""


def remotes_of(repo):
    code, out = git(repo, "remote", "-v")
    found = {}
    if code == 0:
        for line in out.splitlines():
            bits = line.split()
            if len(bits) >= 2:
                found.setdefault(bits[0], bits[1])
    return found


def last_words(out, limit=140):
    lines = [l.strip() for l in str(out or "").splitlines() if l.strip()]
    return lines[-1][:limit] if lines else ""


def fetch_timeout():
    try:
        return float(os.environ.get(FETCH_TIMEOUT_ENV) or FETCH_TIMEOUT)
    except ValueError:
        return float(FETCH_TIMEOUT)


def is_slow(code, out):
    return code == 124 or bool(SLOW_LINK.search(str(out or "")))


# --------------------------------------------------------------------------
# THE ONE PULL — arrive's first-beat case and the beat's catch-up are this function
# --------------------------------------------------------------------------

def pull_ff(repo, fetched=False, dry=False, timeout=PULL_TIMEOUT_ATTENDED):
    """(state, what it said) for ONE repo, fast-forward only.

    `fetched=False` is arrive's road: `git pull --ff-only` (it fetches and lands). `fetched=True`
    is the beat's: the beat already fetched, so only `git merge --ff-only @{upstream}` runs.
    States: level · caught-up · no-remote · dry · partial (the link, deferred) · stop (git refused).
    Whether it moved is read from HEAD before and after, never from git's wording."""
    if not remotes_of(repo):
        return "no-remote", "no remote — expected on a drive-lane repo, not a failure"
    branch = current_branch(repo)
    upstream = upstream_of(repo, branch)
    if not upstream:
        return "no-remote", ("no tracking for %s — expected on a drive-lane repo, not a failure"
                             % (branch or "a detached HEAD"))
    if dry:
        return "dry", "would pull --ff-only"
    before = head_sha(repo)
    if fetched:
        code, out = git(repo, "merge", "--ff-only", "--no-edit", "@{upstream}", timeout=timeout)
    else:
        code, out = git(repo, "pull", "--ff-only", timeout=timeout)
    if code != 0:
        if is_slow(code, out):
            return "partial", "the link is slow (%s) — deferred to a fast line" % last_words(out)
        return "stop", (last_words(out) or "git pull refused")
    after = head_sha(repo)
    if after and after == before:
        return "level", "Already up to date"
    count = git_line(repo, "rev-list", "--count", "%s..%s" % (before, after)) if before else ""
    return "caught-up", "Fast-forward · %s..%s%s" % (before[:7], after[:7],
                                                      (" (%s commit%s)" % (count, "" if count == "1" else "s"))
                                                      if count else "")


# --------------------------------------------------------------------------
# the record: this machine, the registry, who is working where
# --------------------------------------------------------------------------

class World(object):
    """Every value from the record: machine.json (the hub's own first — a gate's scratch identity —
    then the path resolver's), the registry, the live file, the claims."""

    def __init__(self, hub=None, projects=None, state_dir=None):
        record, found = {}, None
        if hub is not None and (Path(hub) / "machine.json").is_file():
            found = Path(hub) / "machine.json"
        else:
            try:
                from exo_paths import paths                              # noqa: E402
                found = paths(hub=hub)["machine_file"] if hub is not None \
                    else paths(tool_file=__file__)["machine_file"]
            except Exception:
                found = None
        if found is not None:
            record = read_json(found, {}) or {}
        self.record = record if isinstance(record, dict) else {}
        self.name = str(self.record.get("name") or "unknown").lower()
        roots = self.record.get("roots") or {}
        self.hub = Path(hub) if hub else Path(roots.get("orchestrator") or HERE.parent)
        if projects:
            self.projects = Path(projects)
        else:
            self.projects = Path(roots["projects"]) if roots.get("projects") else None
        named = str(state_dir or os.environ.get(STATE_ENV) or "").strip()
        self.state_dir = Path(named) if named else Path.home() / ".exocortex" / "csync"

    def switch(self):
        """(on, why-off). On once installed; off by env for one run or by machine.json here."""
        v = str(os.environ.get(SWITCH_ENV, "")).strip().lower()
        if v in ("0", "false", "no", "off"):
            return False, "%s=%s" % (SWITCH_ENV, v)
        if self.record.get("repo_beat") is False:
            return False, '"repo_beat": false in machine.json'
        return True, ""


def registry(world):
    """{project name: entry} — both spellings buttonup.py reads (top level beside `github_owner`,
    or under `projects`)."""
    body = read_json(world.hub / "carry" / "projects.json", {})
    if not isinstance(body, dict):
        return {}
    out = {}
    nested = body.get("projects")
    if isinstance(nested, dict):
        out.update({k: v for k, v in nested.items() if isinstance(v, dict)})
    out.update({k: v for k, v in body.items() if isinstance(v, dict) and k != "projects"})
    return out


def carried_here(entry):
    """THE SAFETY DIRECTION — buttonup.may_push's own test: only a confirmed github entry."""
    return (str((entry or {}).get("carrier") or "").strip().lower() == "github"
            and (entry or {}).get("confirmed") is True)


def norm_path(p):
    return re.sub(r"[\\/]+", "/", str(p or "")).rstrip("/").lower()


def related(a, b):
    """Is one folder the other, or inside it — either separator, case-folded."""
    x, y = norm_path(a), norm_path(b)
    if not x or not y:
        return False
    return x == y or x.startswith(y + "/") or y.startswith(x + "/")


def norm_url(url):
    u = str(url or "").strip().rstrip("/")
    if u.lower().endswith(".git"):
        u = u[:-4]
    return u.lower()


def opener_prefixes(folder):
    """The arc prefixes a project's openers declare: `lane: Garden/Docs` → `Garden/`."""
    found = []
    try:
        names = sorted(p.name for p in Path(folder).iterdir())
    except OSError:
        return found
    for name in names:
        if not re.match(r"^OPENER(-.+)?\.md$", name):
            continue
        try:
            with io.open(str(Path(folder) / name), encoding="utf-8", errors="replace") as fh:
                head = fh.read(4096)
        except OSError:
            continue
        for line in head.splitlines():
            if line.strip().lower().startswith("lane:"):
                lane = line.split(":", 1)[1].strip()
                prefix = (lane.split("/", 1)[0] + "/") if "/" in lane else lane
                if prefix and prefix not in found:
                    found.append(prefix)
                break
    return found


def arcs_for(name, entry, folder):
    arcs = [str(a) for a in (entry or {}).get("arcs") or [] if str(a).strip()]
    return arcs or opener_prefixes(folder) or [name]


def arc_matches(arc, arcs):
    a = str(arc or "").strip().lower()
    for want in arcs:
        w = str(want).strip().lower()
        if not w:
            continue
        stem = w.rstrip("/")
        if a == stem or a.startswith(w) or (stem and a.startswith(stem + "/")):
            return True
    return False


def live_picture(world):
    """(live session rows, a reason the picture cannot be trusted or '')."""
    path = world.hub / ("live-sessions-%s.json" % world.name)
    body = read_json(path)
    if not isinstance(body, dict):
        return [], "this machine's live file (%s) is not there" % path.name
    age = age_seconds(body.get("when"))
    if age is None:
        return [], "this machine's live file carries no time"
    if age > LIVE_FILE_MINUTES * 60:
        return [], "this machine's live file is %d min old" % int(age // 60)
    rows = [s for s in body.get("sessions") or [] if isinstance(s, dict)]
    return rows, ""


def my_claims(world):
    body = read_json(world.hub / "claims.json", [])
    out = []
    for c in body if isinstance(body, list) else []:
        if not isinstance(c, dict) or str(c.get("machine") or "").lower() != world.name:
            continue
        age = age_seconds(c.get("since"))
        if age is None or age >= CLAIM_HOURS * 3600:
            continue
        out.append(c)
    return out


def holder_of(folder, arcs, rows, claims):
    """The one-line reason this folder is held, or ''."""
    for s in rows:
        cwd = s.get("cwd") or ""
        if cwd and related(cwd, folder):
            who = s.get("title") or s.get("mind") or s.get("kind") or "a session"
            return "a live session is working here (%s)" % str(who)[:60]
    for c in claims:
        if arc_matches(c.get("arc"), arcs):
            return "the %s claim is held (%s)" % (c.get("arc"), str(c.get("title") or "")[:60])
    return ""


# --------------------------------------------------------------------------
# one repo's facts, first-hand
# --------------------------------------------------------------------------

def common_dir(repo):
    """The repository a worktree belongs to — worktrees of one repo share refs and objects."""
    out = git_line(repo, "rev-parse", "--git-common-dir")
    if not out:
        return norm_path(Path(repo) / ".git")
    p = Path(out)
    if not p.is_absolute():
        p = Path(repo) / p
    try:
        p = p.resolve()
    except OSError:
        pass
    return norm_path(p)


def git_dir(repo):
    out = git_line(repo, "rev-parse", "--git-dir")
    if not out:
        return Path(repo) / ".git"
    p = Path(out)
    return p if p.is_absolute() else Path(repo) / p


LOCK_STALE_SECONDS = 600       # an editor's own git takes index.lock for a moment, all day


def in_progress(repo):
    """(the git operation left in progress here or '', is it only a FRESH index.lock?).
    A fresh lock is somebody's git at work right now: this beat passes the repo by, quietly.
    A lock older than LOCK_STALE_SECONDS, or a merge/rebase/cherry-pick left open, is HELD."""
    gd = git_dir(repo)
    for mark in IN_PROGRESS:
        if (gd / mark).exists():
            return mark, False
    lock = gd / "index.lock"
    try:
        age = time.time() - lock.stat().st_mtime
    except OSError:
        return "", False
    return "index.lock", age < LOCK_STALE_SECONDS


def dirty_tracked(repo):
    code, out = git(repo, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no")
    if code != 0:
        return -1
    return len([l for l in out.splitlines() if l.strip()])


def counts(repo, left, right):
    """(ahead, behind) of `left` against `right`, or (None, None)."""
    out = git_line(repo, "rev-list", "--left-right", "--count", "%s...%s" % (left, right))
    bits = out.split()
    if len(bits) == 2 and all(b.isdigit() for b in bits):
        return int(bits[0]), int(bits[1])
    return None, None


def big_tracked(repo, ref="HEAD", over_mb=None):
    """Files over the law's size in the tree of the commit about to be pushed — the button-up's
    own law (over 90 MB: FLAGGED, never pushed), read from the tree itself so a branch that is not
    checked out is judged by what it would send, not by the working tree."""
    code, out = git(repo, "ls-tree", "-r", "-l", "-z", ref)
    if code != 0:
        return []
    limit, found = (BIG_FILE_MB if over_mb is None else over_mb) * 1024 * 1024, []
    for row in [r for r in out.split("\0") if r]:
        meta, _tab, rel = row.partition("\t")
        bits = meta.split()
        if len(bits) == 4 and bits[1] == "blob" and bits[3].isdigit() and int(bits[3]) > limit:
            found.append((rel, int(bits[3])))
    return sorted(found, key=lambda pair: -pair[1])


def tracking_branches(repo):
    """[(local branch, its upstream)] for every local branch that tracks a branch of origin."""
    code, out = git(repo, "for-each-ref", "--format=%(refname:short)\t%(upstream:short)",
                    "refs/heads")
    rows = []
    if code == 0:
        for line in out.splitlines():
            if "\t" not in line:
                continue
            local, up = line.split("\t", 1)
            if up.strip().startswith("origin/"):
                rows.append((local.strip(), up.strip()))
    return rows


# --------------------------------------------------------------------------
# the beat
# --------------------------------------------------------------------------

class Beat(object):
    def __init__(self, world, dry=False, mail=True):
        self.w, self.dry, self.mail = world, dry, mail
        self.lines, self.held, self.errors, self.moved = [], [], [], []
        self.not_carried = []        # (project, why) — said on the summary line, never as noise
        self.counts = {"read": 0, "pulled": 0, "pushed": 0, "live": 0, "held": 0,
                       "deferred": 0, "level": 0, "not-here": 0, "untracked-branch": 0}
        try:
            self.budget = float(os.environ.get(BUDGET_ENV) or BEAT_BUDGET)
        except ValueError:
            self.budget = float(BEAT_BUDGET)
        self.t0 = time.time()
        self.link_down = ""          # once the link is slow or down, no more network this beat

    def out_of_time(self):
        return (time.time() - self.t0) >= self.budget

    def hold(self, project, kind, reason, owner, move, shas=""):
        self.held.append({"project": project, "kind": kind, "reason": reason, "owner": owner,
                          "next": move, "shas": shas})
        self.counts["held"] += 1

    def moved_line(self, text):
        self.moved.append(text)
        self.lines.append("  " + text)

    # ---- the network step, once per repository (worktrees share it) ----
    def fetch(self, repo):
        """(ok, why). Never retried inside the beat."""
        if self.dry:
            return True, "dry: no fetch"
        if self.link_down:
            return False, self.link_down
        if self.out_of_time():
            return False, "the beat's %d s were spent" % int(self.budget)
        code, out = git(repo, "fetch", "--quiet", "origin", timeout=fetch_timeout())
        if code == 0:
            return True, ""
        if is_slow(code, out):
            self.link_down = "the link is slow (%s)" % (last_words(out, 80) or "timed out")
            return False, self.link_down
        if OFFLINE.search(out or ""):
            said = [l.strip() for l in out.splitlines() if OFFLINE.search(l)]
            self.link_down = "the network is down (%s)" % (said[0][:80] if said else "no route")
            return False, self.link_down
        return None, last_words(out) or "git fetch refused"

    # ---- one repo ----
    def precheck(self, name, entry, repo):
        """True when this repo may be fetched and carried; else it is HELD or passed by, said.
        Runs BEFORE any network: a repo whose origin is not the recorded one is never fetched."""
        want = norm_url(entry.get("remote"))
        have = norm_url(remotes_of(repo).get("origin"))
        if not have:
            self.hold(name, "no-origin", "its carrier is github and it has no origin", "hub",
                      "run `buttonup.py remotes` — it creates one only for a confirmed entry")
            return False
        if want and have != want:
            self.hold(name, "remote-mismatch",
                      "origin is %s, the registry records %s" % (have, want), "hub",
                      "check carry/projects.json against the repo's origin; the beat fetches "
                      "and pushes only the recorded remote")
            return False
        busy, fresh_lock = in_progress(repo)
        if fresh_lock:
            self.not_carried.append((name, "git is at work here right now (index.lock)"))
            return False
        if busy:
            self.hold(name, "in-progress", "a git operation is in progress here (%s)" % busy,
                      name, "finish or abort it in a session in that lane (an index.lock left "
                      "with no git running is removed by hand)")
            return False
        return True

    def one(self, name, entry, repo, fetched_ok):
        branch = current_branch(repo)
        if not branch:
            self.not_carried.append((name, "a detached HEAD"))
            return
        upstream = upstream_of(repo, branch)
        if not upstream:
            self.counts["untracked-branch"] += 1
            self.not_carried.append((name, "%s tracks nothing on origin" % branch))
            return
        if not upstream.startswith("origin/"):
            self.not_carried.append((name, "%s tracks %s, not origin" % (branch, upstream)))
            return
        if fetched_ok is not True:
            return
        ahead, behind = counts(repo, "HEAD", upstream)
        if ahead is None:
            self.errors.append("%s: could not count against %s" % (name, upstream))
            self.lines.append("  %s · could not count against %s — nothing done" % (name, upstream))
            return
        here, there = head_sha(repo)[:7], git_line(repo, "rev-parse", upstream)[:7]
        if ahead and behind:
            self.hold(name, "diverged",
                      "both sides moved: here %s (+%d) · %s %s (+%d)" % (here, ahead, upstream,
                                                                         there, behind),
                      name, "merge or rebase in a session in that lane, then push — never a "
                      "force; the beat carries it from there", "%s %s" % (here, there))
            return
        if behind:
            dirty = dirty_tracked(repo)
            if dirty < 0:
                self.errors.append("%s: git status failed" % name)
                self.lines.append("  %s · git status failed — nothing done this beat" % name)
                return
            if dirty:
                self.hold(name, "dirty",
                          "%d tracked file(s) modified here and %s has %d new commit(s)"
                          % (dirty, upstream, behind), name,
                          "commit or set the changes aside in a session in that lane; the next "
                          "beat catches up", "%s %s" % (here, there))
                return
            state, said = pull_ff(repo, fetched=True, dry=self.dry, timeout=LOCAL_TIMEOUT)
            if state == "caught-up":
                if head_sha(repo) != git_line(repo, "rev-parse", upstream):
                    self.errors.append("%s: caught up but HEAD is not %s" % (name, upstream))
                    self.lines.append("  %s · pulled, but HEAD is not %s — read it by hand"
                                      % (name, upstream))
                    return
                self.counts["pulled"] += 1
                self.moved_line("%s · pulled %s" % (name, said))
            elif state == "dry":
                self.lines.append("  %s · would pull %d commit(s) from %s" % (name, behind, upstream))
            elif state == "level":
                self.counts["level"] += 1
            else:
                self.hold(name, "pull-refused", "git refused the fast-forward: %s" % said, name,
                          "read `git status` in a session in that lane", "%s %s" % (here, there))
            return
        if ahead:
            self.push(name, repo, branch, upstream, ahead)
            return
        self.counts["level"] += 1

    def push(self, name, repo, branch, upstream, ahead):
        big = big_tracked(repo, "HEAD")
        if big:
            rel, size = big[0]
            self.hold(name, "big-file", "%s is %d MB tracked — over the %d MB law, never pushed"
                      % (rel, size // (1024 * 1024), BIG_FILE_MB), "you",
                      "take the file out of the repo's history or out of the project; the beat "
                      "pushes once no tracked file is over the law")
            return
        remote_branch = upstream.split("/", 1)[1]
        if self.dry:
            self.lines.append("  %s · would push %d commit(s) to %s" % (name, ahead, upstream))
            return
        if self.link_down or self.out_of_time():
            self.counts["deferred"] += 1
            return
        before = head_sha(repo)
        code, out = git(repo, "push", "--quiet", "origin", "%s:%s" % (branch, remote_branch),
                        timeout=PUSH_TIMEOUT)
        if code == 0:
            if git_line(repo, "rev-parse", upstream) != before:
                self.errors.append("%s: pushed but %s is not HEAD" % (name, upstream))
                self.lines.append("  %s · pushed, but %s does not read HEAD — read it by hand"
                                  % (name, upstream))
                return
            self.counts["pushed"] += 1
            self.moved_line("%s · pushed %d commit(s) to %s · %s" % (name, ahead, upstream,
                                                                      before[:7]))
            return
        if is_slow(code, out) or OFFLINE.search(out or ""):
            self.link_down = "the link is slow (%s)" % (last_words(out, 80) or "timed out")
            self.counts["deferred"] += 1
            return
        if re.search(r"non-fast-forward|fetch first|rejected", out or "", re.I):
            self.lines.append("  %s · the remote moved during the beat — the next beat reads it "
                              "again" % name)
            return
        self.errors.append("%s: push refused: %s" % (name, last_words(out)))
        self.hold(name, "push-refused", "the push was refused: %s" % last_words(out), "hub",
                  "read the line above; push by hand in a session in that lane")

    def other_branches(self, name, repo, checked_out):
        """Branches that track origin, are not checked out in any worktree, are ahead and not
        behind: their committed work crosses too. Behind ones wait (a checkout is not ours)."""
        for local, up in tracking_branches(repo):
            if local in checked_out:
                continue
            ahead, behind = counts(repo, local, up)
            if not ahead or behind:
                if ahead and behind:
                    self.hold(name, "diverged", "branch %s and %s both moved (+%d / +%d)"
                              % (local, up, ahead, behind), name,
                              "merge or rebase that branch in a session in that lane — never a "
                              "force", "%s %s" % (git_line(repo, "rev-parse", local)[:7],
                                                  git_line(repo, "rev-parse", up)[:7]))
                continue
            big = big_tracked(repo, local)
            if big:
                self.hold(name, "big-file", "%s on branch %s is %d MB — over the %d MB law, never "
                          "pushed" % (big[0][0], local, big[0][1] // (1024 * 1024), BIG_FILE_MB),
                          "you", "take the file out of that branch; the beat pushes once no "
                          "file is over the law", git_line(repo, "rev-parse", local)[:7])
                continue
            if self.dry:
                self.lines.append("  %s · would push %d commit(s) of %s to %s"
                                  % (name, ahead, local, up))
                continue
            if self.link_down or self.out_of_time():
                self.counts["deferred"] += 1
                continue
            tip = git_line(repo, "rev-parse", local)
            code, out = git(repo, "push", "--quiet", "origin", "%s:%s" % (local, up.split("/", 1)[1]),
                            timeout=PUSH_TIMEOUT)
            if code == 0 and git_line(repo, "rev-parse", up) == tip:
                self.counts["pushed"] += 1
                self.moved_line("%s · pushed %d commit(s) of %s to %s · %s"
                                % (name, ahead, local, up, tip[:7]))
            elif is_slow(code, out) or OFFLINE.search(out or ""):
                self.link_down = "the link is slow (%s)" % (last_words(out, 80) or "timed out")
                self.counts["deferred"] += 1
            elif code != 0 and not re.search(r"non-fast-forward|fetch first|rejected", out or "", re.I):
                self.errors.append("%s: push of %s refused: %s" % (name, local, last_words(out)))

    def run(self):
        w = self.w
        on, why_off = w.switch()
        if not on:
            self.lines.append("repos: off (%s) — nothing carried" % why_off)
            return 0
        if w.projects is None or not w.projects.is_dir():
            self.lines.append("repos: this machine's record names no projects folder — nothing "
                              "to carry")
            return 0
        rows, stale = live_picture(w)
        claims = my_claims(w)
        whole = [c for c in claims if str(c.get("arc") or "").strip().lower() in WHOLE_BEAT_ARCS]
        reg = registry(w)
        entries = sorted(((n, e) for n, e in reg.items() if carried_here(e)), key=lambda p: p[0].lower())
        present = []
        for name, entry in entries:
            folder = w.projects / name
            if not is_repo(folder):
                self.counts["not-here"] += 1
                continue
            present.append((name, entry, folder))
        self.counts["read"] = len(present)
        if stale:
            self.counts["live"] = len(present)
            self.lines.append("repos: %d read · none touched — %s; the beat never acts on a stale "
                              "picture of who is working" % (len(present), stale))
            return 0
        if whole:
            self.counts["live"] = len(present)
            self.lines.append("repos: %d read · none touched — the %s claim holds every repo (%s)"
                              % (len(present), whole[0].get("arc"),
                                 str(whole[0].get("title") or "")[:60]))
            return 0
        # group worktrees of one repository; a group is held if any member is
        groups, order = {}, []
        for name, entry, folder in present:
            key = common_dir(folder)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append((name, entry, folder))
        state = self.load_state()
        cursor = int(state.get("cursor") or 0) % max(1, len(order)) if order else 0
        order = order[cursor:] + order[:cursor]
        state["cursor"] = (cursor + 1) % max(1, len(order)) if order else 0
        for key in order:
            members = groups[key]
            why = ""
            for name, entry, folder in members:
                why = holder_of(folder, arcs_for(name, entry, folder), rows, claims)
                if why:
                    break
            if why:
                self.counts["live"] += len(members)
                continue
            fit = [m for m in members if self.precheck(*m)]
            if not fit:
                continue
            ok, said = self.fetch(fit[0][2])
            if ok is None:
                for name, _e, _f in fit:
                    self.errors.append("%s: %s" % (name, said))
                    self.hold(name, "fetch-refused", "git fetch from origin was refused: %s" % said,
                              "hub", "read the line above in a session; credentials or the "
                              "remote itself")
                continue
            if ok is False:
                self.counts["deferred"] += len(fit)
                continue
            checked_out = set()
            for name, entry, folder in members:
                b = current_branch(folder)
                if b:
                    checked_out.add(b)
            for name, entry, folder in fit:
                self.one(name, entry, folder, ok)
            if len(fit) == len(members):
                self.other_branches(fit[0][0], fit[0][2], checked_out)
        rc = 1 if self.errors else 0
        self.finish(state)
        c = self.counts
        tail = []
        if self.link_down:
            tail.append(self.link_down + " — the rest wait for the next beat")
        elif c["deferred"]:
            tail.append("the beat's %d s were spent — the rest wait for the next beat"
                        % int(self.budget))
        summary = ("repos: %d read · %d pulled · %d pushed · %d live, not touched · %d held · "
                   "%d deferred%s%s%s" % (c["read"], c["pulled"], c["pushed"], c["live"], c["held"],
                                           c["deferred"],
                                           ((" · %d registered, not on this machine" % c["not-here"])
                                            if c["not-here"] else "")
                                           + ((" · not carried: %s" % "; ".join(
                                               "%s (%s)" % nc for nc in self.not_carried))
                                              if self.not_carried else ""),
                                           (" · " + "; ".join(tail)) if tail else "",
                                           " · dry run, nothing written" if self.dry else ""))
        self.lines.insert(0, summary)
        return rc

    # ---- state: machine-personal cursor + letters said; brain-carried held file ----
    def state_file(self):
        return self.w.state_dir / ("csync-%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "-", self.w.name))

    def load_state(self):
        body = read_json(self.state_file(), {})
        return body if isinstance(body, dict) else {}

    def held_key(self, h):
        """What makes a HELD item NEW: the project, the kind, and THIS side's sha — so the other
        side pushing again never re-letters a standing hold; work here that changes it does."""
        return "%s|%s|%s" % (h["project"], h["kind"], (str(h.get("shas") or "").split() or [""])[0])

    def finish(self, state):
        said = state.get("said") if isinstance(state.get("said"), dict) else {}
        keys_now = [self.held_key(h) for h in self.held]
        fresh = [h for h in self.held if self.held_key(h) not in said]
        for h in fresh:
            self.lines.append("  HELD %s · %s · owner: %s · next: %s"
                              % (h["project"], h["reason"], h["owner"], h["next"]))
        standing = sorted({h["project"] for h in self.held if self.held_key(h) in said})
        if standing:
            self.lines.append("  still held (said before, no new letter): %s" % ", ".join(standing))
        if self.dry:
            return
        kept = {}
        for k in keys_now:
            if k in said:
                kept[k] = said[k]
        for h in fresh:
            sent = self.send_letter(h)
            if sent:
                kept[self.held_key(h)] = now_iso()
            else:
                self.lines.append("    the letter for %s could not be sent — the next beat tries "
                                  "again" % h["project"])
        state["said"] = kept
        state["version"] = 1
        try:
            write_atomic(self.state_file(), json.dumps(state, indent=1, sort_keys=True) + "\n")
        except OSError as exc:
            self.lines.append("  state not kept — %s (the next beat may repeat a letter)" % exc)
        self.write_held(said)

    def send_letter(self, h):
        if not self.mail:
            return True
        text = "REPO HELD · %s · %s" % (h["project"], h["reason"])
        action = "%s (owner: %s)" % (h["next"], h["owner"])
        target = os.environ.get(MAIL_FILE_ENV, "").strip()
        if target:
            try:
                with io.open(target, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write("to: %s/hub · %s · %s · %s\n" % (self.w.name.upper(), h["project"],
                                                               text, action))
                return True
            except OSError:
                return False
        mailpy = self.w.hub / "tools" / "mail.py"
        if not mailpy.is_file():
            return False
        code, _out = _runner()([sys.executable or "python3", str(mailpy), "--send",
                                "%s/hub" % self.w.name.upper(), h["project"], text, action,
                                "--no-push", "--inbox", str(self.w.hub / "INBOX.md")],
                               cwd=str(self.w.hub), timeout=120,
                               env=dict(os.environ, PYTHONUTF8="1"))
        return code == 0

    def write_held(self, said):
        """held-<machine>.json — only when WHAT is held changed; `since` is kept per item."""
        path = self.w.hub / ("held-%s.json" % self.w.name)
        old = read_json(path, {}) or {}
        old_items = {self.held_key(i): i for i in (old.get("items") or []) if isinstance(i, dict)
                     and "project" in i and "kind" in i}
        items = []
        for h in sorted(self.held, key=lambda x: (x["project"].lower(), x["kind"])):
            prev = old_items.get(self.held_key(h))
            item = dict(h)
            item["since"] = (prev or {}).get("since") or now_iso()
            items.append(item)
        def core(lst):
            return [{k: v for k, v in i.items() if k != "since"} for i in lst]
        if old and core(old.get("items") or []) == core(items):
            return
        if not old and not items:
            return
        body = {"machine": self.w.name, "tool": "continuous_sync.py %s" % TOOL_VERSION,
                "about": "repos the continuous sync would not carry, with the owner and the "
                         "next move; rewritten only when this list changes",
                "written": now_iso(), "items": items}
        try:
            write_atomic(path, json.dumps(body, indent=1, ensure_ascii=False) + "\n")
        except OSError as exc:
            self.lines.append("  held file not written — %s" % exc)


def cmd_status(world):
    body = read_json(world.hub / ("held-%s.json" % world.name), {}) or {}
    items = body.get("items") or []
    on, why = world.switch()
    say("continuous sync (half A, github) on %s · %s" % (world.name.upper(),
                                                         "on" if on else "off (%s)" % why))
    if not items:
        say("nothing held")
        return 0
    for i in items:
        say("HELD %s · %s · owner: %s · next: %s · since %s"
            % (i.get("project"), i.get("reason"), i.get("owner"), i.get("next"), i.get("since")))
    return 0


def flag_value(args, name):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def main(argv):
    if "--help" in argv or "-h" in argv or not argv:
        sys.stdout.write(__doc__)
        return 0
    i = 0
    while i < len(argv):
        a = argv[i]
        if a not in KNOWN:
            sys.stderr.write("continuous_sync.py: unknown flag %r (see --help)\n" % a)
            return 2
        i += 2 if a in VALUED else 1
    world = World(hub=flag_value(argv, "--hub"), projects=flag_value(argv, "--projects"),
                  state_dir=flag_value(argv, "--state-dir"))
    if "--status" in argv:
        return cmd_status(world)
    if "--beat" not in argv:
        sys.stderr.write("continuous_sync.py: say --beat or --status\n")
        return 2
    beat = Beat(world, dry="--dry" in argv, mail="--no-mail" not in argv)
    rc = beat.run()
    for line in beat.lines:
        say(line)
    if "--json" in argv:
        say(json.dumps({"machine": world.name, "counts": beat.counts, "held": beat.held,
                        "moved": beat.moved, "errors": beat.errors, "dry": beat.dry},
                       ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
