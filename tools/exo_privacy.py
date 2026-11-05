#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exo_privacy.py — one answer to "is this lane private?".

Every carrier that copies a lane into a synced file (the pulse's
live-sessions-<machine>.json, the tree's TREE.md, INBOX.md, claims.json, the
stamps, the button-up capture's report) asks this module first, and a private
lane is carried as its NAME ONLY: a count of its live sessions, no title, no
typed line, no opener, no card, no letter body.

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_privacy import private_lane_of, public_title

    lane = private_lane_of(title=t, cwd=c, arc=a)     # the lane id, or None
    shown = public_title(t, cwd=c, arc=a)             # "<lane> (private)" or t

THE MARK IS THE USER'S. A lane is private only when the user says so, in
either of two places:

  * its own STATUS.md, under `## Important`, a line
        - privacy: private · names: <Word>, <Word>
    (`names:` is optional: the words its sessions' titles use for it, when they
    are not the folder's own name);
  * the brain's registry.json, a block
        "privacy": {"private": {"<lane id>": {"names": ["<Word>"]}},
                    "cloud_ok": ["<lane id>"]}
    which carries the lane's NAME only, so a machine that does not hold the
    lane's folder still honours the mark.

THE CLEARING WORD WINS. `privacy: cloud-ok` on the lane's STATUS line (logged
there by the session that heard the user say «put it on the cloud»), or the
lane listed under `privacy.cloud_ok`, makes the lane an ordinary lane again,
whatever else says private. Nothing else makes a lane private: a lane that
keeps no git remote is not private for that reason.

ASSUMES: a lane is private only by the user's mark (the STATUS line or the
  registry block). Opposite: a no-remote lane with no mark is carried as before
  (gate-privacy P2).
ASSUMES: the clearing word beats every private mark. Opposite: a lane marked
  private in the registry and cleared in its STATUS is carried (gate-privacy P3).
ASSUMES: a lane's folder is <projects root>/<lane id>, the root machine.json
  names — the same root every carrier walks. Opposite: a lane known only from
  the registry still matches by its name in a title or an arc (P4).
ASSUMES: a title names its lane in the ACT grammar `<TAG> — <Proj>[/<Lane>]: …`.
  Opposite: a title in no grammar is matched only by its cwd (P5).

WHAT IT PROMISES

  * Importing it does nothing: no file is read until a call.
  * It never raises. A file that cannot be read means "no mark there".
  * It answers from the record, read at call time (a short cache keyed by the
    files' mtimes), so a mark the user writes is honoured on the next call.

FROM A SHELL

    python3 exo_privacy.py --list            the private lanes this machine knows, by name
    python3 exo_privacy.py --check <word>    exit 0 when private, 1 when not

Standard library only, Python 3.9-compatible, macOS and Windows.
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

API = 1

PRIVATE = "private"
CLEARED = "cloud-ok"
PRIVATE_SUFFIX = " (private)"
# What a carrier writes in place of a private lane's words. One phrase, so a
# reader that meets it knows what it is and a scrub never mistakes it for text.
WITHHELD = "(private lane — kept on its own machine)"

_LINE = re.compile(r"^\s*(?:[-*]\s*)?privacy\s*:\s*(private|cloud[- ]?ok)\b(.*)$", re.I)
_NAMES = re.compile(r"names?\s*:\s*(.+)$", re.I)
_TITLE = re.compile(r"^\s*[A-Z?]{2,5}\s*[—–-]+\s*([^:]+?)\s*:")

_CACHE = {}


def _fold(text):
    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")


def key(word):
    """One spelling for a lane word: case, accents and punctuation do not matter."""
    return re.sub(r"[^a-z0-9]+", " ", _fold(word).lower()).strip()


def _here():
    return Path(__file__).resolve().parent


def _paths(hub=None):
    try:
        sys.path.insert(0, str(_here()))
        from exo_paths import paths
        return paths(tool_file=__file__, hub=hub)
    except Exception:
        return {}


def projects_root(hub=None, projects=None):
    if projects:
        return Path(projects)
    named = str(os.environ.get("EXO_PRIVACY_PROJECTS") or "").strip()
    if named:
        return Path(named)
    rec = _paths(hub)
    root = (rec.get("roots") or {}).get("projects") if rec else None
    return Path(root) if root else Path.home() / "Projects"


def hub_folder(hub=None):
    if hub:
        return Path(hub)
    rec = _paths(None)
    return Path(rec.get("hub")) if rec and rec.get("hub") else _here().parent


def _mtime(p):
    try:
        return os.stat(str(p)).st_mtime_ns
    except OSError:
        return 0


def _important(text):
    """The lines of a STATUS's `## Important` section."""
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip().lower().startswith("## important")
            continue
        if inside:
            out.append(line)
    return out


def status_mark(status_text):
    """(PRIVATE | CLEARED | None, [names]) from a STATUS's own text."""
    mark, names = None, []
    for line in _important(status_text or ""):
        m = _LINE.match(line)
        if not m:
            continue
        word = m.group(1).lower().replace(" ", "-")
        word = CLEARED if word.startswith("cloud") else PRIVATE
        if mark == CLEARED:
            continue                       # the clearing word, once said, stands
        mark = word
        nm = _NAMES.search(m.group(2) or "")
        if nm:
            names.extend(w.strip() for w in re.split(r"[,;]", nm.group(1)) if w.strip())
    return mark, names


def no_remote(status_text):
    """True when the lane's own STATUS says it keeps no remote / stays local —
    the spool's rule: such a lane is never worked from the hub folder."""
    for line in _important(status_text or ""):
        low = line.lower()
        if re.search(r"\bno[ -]remote\b|\blocal[ -]only\b|\bstays local\b|\bnever pushed\b", low):
            return True
    return False


def _registry_block(hub=None):
    try:
        sys.path.insert(0, str(_here()))
        from exo_registry import registry_path
        path = registry_path(hub)
    except Exception:
        path = hub_folder(hub) / "registry.json"
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}, path
    block = raw.get("privacy") if isinstance(raw, dict) else None
    return (block if isinstance(block, dict) else {}), path


def private_lanes(hub=None, projects=None):
    """{lane id: {"names": [keys], "folders": [paths], "source": "status"|"registry"}}
    — every lane the user marked private and did not clear. Never raises."""
    root = projects_root(hub, projects)
    block, reg_path = _registry_block(hub)
    try:
        listing = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:
        listing = []
    stamp = (str(root), str(reg_path), _mtime(reg_path), _mtime(root),
             tuple(_mtime(p / "STATUS.md") for p in listing))
    hit = _CACHE.get(stamp)
    if hit is not None:
        return hit
    found, cleared = {}, set()
    for lane in block.get("cloud_ok") or []:
        cleared.add(key(lane))
    reg_private = block.get("private") or {}
    if isinstance(reg_private, list):
        reg_private = dict((str(x), {}) for x in reg_private)
    for lane, spec in reg_private.items():
        names = [lane] + list((spec or {}).get("names") or []) if isinstance(spec, dict) else [lane]
        found[key(lane)] = {"lane": str(lane), "names": set(key(n) for n in names if key(n)),
                            "folders": [], "source": "registry"}
    for folder in listing:
        try:
            text = (folder / "STATUS.md").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        mark, names = status_mark(text)
        k = key(folder.name)
        if mark == CLEARED:
            cleared.add(k)
            continue
        if mark == PRIVATE or k in found:
            rec = found.setdefault(k, {"lane": folder.name, "names": set(), "folders": [],
                                       "source": "status"})
            rec["names"].update(key(n) for n in [folder.name] + names if key(n))
            rec["folders"].append(str(folder))
            lane_line = _opener_lane(folder)
            if lane_line:
                rec["names"].add(key(lane_line))
    out = dict((k, v) for k, v in found.items() if k not in cleared)
    for v in out.values():
        v["names"] = sorted(v["names"])
    _CACHE.clear()
    _CACHE[stamp] = out
    return out


def _opener_lane(folder):
    """The `lane:` header of the lane's own OPENER*.md, the word its cards use."""
    try:
        for p in sorted(Path(folder).glob("OPENER*.md")):
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[:20]:
                if line.startswith("lane:"):
                    return line.split(":", 1)[1].strip().split("/")[0]
    except OSError:
        pass
    return ""


def title_lane(title):
    """The project word a title names in the ACT grammar, or ''."""
    m = _TITLE.match(str(title or ""))
    return m.group(1).split("/")[0].strip() if m else ""


def _under(child, parent):
    try:                                   # real paths: /var and /private/var are one folder
        c = os.path.normcase(os.path.realpath(str(child)))
        p = os.path.normcase(os.path.realpath(str(parent)))
    except Exception:
        return False
    return c == p or c.startswith(p.rstrip("/\\") + os.sep)


def lane_of_word(word, hub=None, projects=None):
    """The private lane a word names (a lane id, an arc `Proj/Lane`, a title's
    project word), or None."""
    w = str(word or "").strip()
    if not w:
        return None
    lanes = private_lanes(hub, projects)
    for part in (w, w.split("/")[0]):
        k = key(part)
        if not k:
            continue
        for rec in lanes.values():
            if k in rec["names"]:
                return rec["lane"]
    return None


def lane_of_folder(path, hub=None, projects=None):
    if not path:
        return None
    for rec in private_lanes(hub, projects).values():
        for folder in rec["folders"]:
            if _under(path, folder):
                return rec["lane"]
        # a lane known only from the registry: the folder of its name, if here
        for name in [rec["lane"]]:
            if _under(path, projects_root(hub, projects) / name):
                return rec["lane"]
    return None


def private_lane_of(title="", cwd="", arc="", hub=None, projects=None):
    """The private lane a session, a claim or a letter belongs to, or None.
    Its cwd first (a real byte), then the arc, then the title's project word."""
    return (lane_of_folder(cwd, hub, projects)
            or lane_of_word(arc, hub, projects)
            or lane_of_word(title_lane(title), hub, projects))


def public_title(title, cwd="", arc="", hub=None, projects=None):
    """What a synced file may say for this title: the lane's name only when the
    lane is private, else the title unchanged."""
    lane = private_lane_of(title=title, cwd=cwd, arc=arc, hub=hub, projects=projects)
    return (lane + PRIVATE_SUFFIX) if lane else title


def is_private(word="", cwd="", hub=None, projects=None):
    return bool(private_lane_of(title=word, cwd=cwd, arc=word, hub=hub, projects=projects))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    hub = None
    if "--hub" in argv:
        i = argv.index("--hub")
        hub = argv[i + 1] if i + 1 < len(argv) else None
        del argv[i:i + 2]
    if argv[:1] == ["--list"]:
        lanes = private_lanes(hub)
        if not lanes:
            print("no private lanes marked")
        for rec in lanes.values():
            print("private: %s · from its %s" % (rec["lane"], rec["source"]))
        return 0
    if argv[:1] == ["--check"] and len(argv) > 1:
        lane = private_lane_of(title=argv[1], arc=argv[1], cwd=argv[1], hub=hub)
        print(("private: %s" % lane) if lane else "not private")
        return 0 if lane else 1
    print(__doc__.split("FROM A SHELL")[1].split("Standard library")[0].strip())
    return 2


if __name__ == "__main__":
    sys.exit(main())
