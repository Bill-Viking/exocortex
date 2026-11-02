#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish-heads.py — this machine says, for the others to read, where every project of its own stands.

    publish-heads.py [--hub <dir>] [--projects <dir>] [--dry] [--help]

Writes `heads-<machine>.json` in the hub folder, from this machine's own git. No model, no tokens,
nothing asked of anybody: the pulse calls it each beat beside publish-roots, and a beat where
nothing changed rewrites nothing, so the brain carries no churn.

Why it exists: without it, a button-up's plan can want a multi-gigabyte delta and whole-repo
bundles for projects the other machine has held for weeks. The arithmetic is right; the evidence
is not. The record of SEALED payloads cannot see hand-cut ones or
years of history, so a tool that infers what the other machine has will always guess low. The
engine law answers it: a tool states a fact about a carrier only from a probe, and the only honest
probe of another machine is that machine's own declaration, carried by the brain, exactly as
`roots-<machine>.json` already is.

The declaration (every value read first-hand, here):
  machine    the name in machine.json, lower case — the same word a payload's `to:` uses
  published  when this content was first written; unchanged content is not rewritten, so the stamp
             says how long this declaration has stood, not when the tool last ran
  projects   one entry per folder with a `.git` under the projects root, by its folder NAME (the
             name is the same on every machine, by law):
               branch          the checked-out branch, or the short sha when HEAD is detached
               head            the full 40-character sha of HEAD
               tracked_dirty   how many TRACKED files are modified (untracked files are never
                               counted: a fast-forward never touches them)

A reader (tools/buttonup.py) takes `head` as the newest thing this machine is KNOWN to hold for
that project: an ancestor of the reader's HEAD is the base its bundle starts from; equal means
there is nothing to bundle; neither means the two have diverged and nobody cuts until one lands.

Stdlib only, Python 3.9, OS-neutral. Every write is atomic (temp file, then replace), UTF-8, LF.
  0 = published or already standing · 1 = there is nothing to declare from · 2 = usage
"""
import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
HUB = HERE.parent
KNOWN_FLAGS = ("--hub", "--projects", "--dry", "--help", "-h")
VALUED_FLAGS = ("--hub", "--projects")
GIT_TIMEOUT = 60


def say(text=""):
    print(text)
    sys.stdout.flush()


def read_json(path):
    try:
        with io.open(str(path), encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def write_atomic(path, text):
    """Temp file then replace: a beat killed mid-write leaves the standing declaration whole."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / (".%s.publish-heads-%d" % (path.name, os.getpid()))
    with io.open(str(temp), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(str(temp), str(path))


def record_for(hub):
    """This machine's record: the hub's own machine.json when it has one (a gate's scratch
    identity — publish-roots.py's precedence, kept the same on purpose), else the real one."""
    if hub is not None:
        found = read_json(Path(hub) / "machine.json")
        if found is not None:
            return found
    return read_json(Path.home() / "orchestrator-sync" / "machine.json")


def git(repo, *args):
    try:
        proc = subprocess.run(["git", "-C", str(repo)] + [str(a) for a in args],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=GIT_TIMEOUT)
        return proc.returncode, (proc.stdout or "").strip()
    except Exception:
        return 1, ""


def stand_of(repo):
    """Where one project stands, or None when git cannot say (a repo mid-clone, a broken link)."""
    code, head = git(repo, "rev-parse", "HEAD")
    if code != 0 or len(head.split()[0] if head else "") != 40:
        return None
    head = head.split()[0]
    code, branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or not branch or branch == "HEAD":
        branch = head[:7]
    code, dirty = git(repo, "status", "--porcelain", "--untracked-files=no")
    count = len([l for l in dirty.splitlines() if l.strip()]) if code == 0 else 0
    return {"branch": branch, "head": head, "tracked_dirty": count}


def projects_root(record, override):
    if override:
        return Path(override)
    root = ((record or {}).get("roots") or {}).get("projects")
    return Path(root) if root else None


def declaration(record, root):
    """The whole published shape, in one place, so a reader can see it at a glance."""
    found = {}
    try:
        entries = sorted(Path(root).iterdir(), key=lambda p: p.name.lower())
    except OSError:
        entries = []
    for entry in entries:
        try:
            if entry.name.startswith(".") or not entry.is_dir() or not (entry / ".git").exists():
                continue
        except OSError:
            continue
        stand = stand_of(entry)
        if stand:
            found[entry.name] = stand
    return {"machine": str((record or {}).get("name") or "unknown").strip().lower(),
            "projects": found}


def same(a, b):
    """The declaration without its stamp: what makes a rewrite worth doing."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return {k: v for k, v in a.items() if k != "published"} == \
           {k: v for k, v in b.items() if k != "published"}


def publish(hub, root_override=None, dry=False):
    record = record_for(hub)
    if record is None:
        say("STOP: this machine has no machine.json to declare from — nothing published")
        return 1, None
    root = projects_root(record, root_override)
    if root is None or not root.is_dir():
        say("STOP: this machine's projects root is not there (%s) — nothing published" % (root or "none"))
        return 1, None
    body = declaration(record, root)
    path = Path(hub) / ("heads-%s.json" % body["machine"])
    standing = read_json(path)
    dirty = sum(1 for p in body["projects"].values() if p["tracked_dirty"])
    words = "%d project(s)%s" % (len(body["projects"]),
                                 (" · %d with modified tracked files" % dirty) if dirty else "")
    if same(standing, body):
        say("%s stands: %s" % (path.name, words))
        return 0, path
    body["published"] = datetime.now().astimezone().replace(microsecond=0).isoformat()
    if dry:
        say("%s would be %s: %s" % (path.name, "rewritten" if standing else "written", words))
        return 0, path
    write_atomic(path, json.dumps(body, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    say("%s %s: %s" % (path.name, "rewritten" if standing else "written", words))
    return 0, path


def main(argv):
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(__doc__)
        return 0
    hub, root = HUB, None
    rest = list(argv)
    for flag in VALUED_FLAGS:
        if flag in rest:
            index = rest.index(flag)
            if index + 1 >= len(rest):
                say("STOP: %s needs a folder" % flag)
                return 2
            value = rest[index + 1]
            if flag == "--hub":
                hub = Path(value)
            else:
                root = Path(value)
            del rest[index:index + 2]
    unknown = [a for a in rest if a.startswith("-") and a not in KNOWN_FLAGS]
    if unknown:
        say("unknown flag %s" % unknown[0])
        sys.stderr.write(__doc__)
        return 2
    if not Path(hub).is_dir():
        say("STOP: the hub folder %s is not there — nothing published" % hub)
        return 1
    code, _ = publish(Path(hub), root, dry="--dry" in rest)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
