#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish-roots.py — this machine says, for the others to read, where its own roots are.

    publish-roots.py [--hub <dir>] [--dry] [--help]

Writes `roots-<machine>.json` in the hub folder, from the record and from what this machine can
see first-hand. No model, no tokens, nothing asked of anybody: the pulse calls it each beat, and
a beat where nothing changed rewrites nothing (the brain would carry the churn otherwise).

Why it exists: without it, every arriving path in a cut spec would be typed by hand on the
OTHER machine — one machine guessing where another keeps its projects, its ferry staging, its
python. A machine is the only honest source for its own paths, so it declares them here and
`cut-payload.py` reads the declaration instead of a human's memory (paths come from
configuration).

The declaration (every value from this machine):
  machine   the name in machine.json, lower case — the same word `to:` uses in a payload
  os        platform.system() read HERE, not the record's os string
  shell     bash | powershell — the shell a landing sheet for this machine must be written in
  python    python3 | python — how this machine spells the interpreter on a command line
  roots     machine.json's own roots, plus `ferry` resolved with auto-land's fallback
            (roots.ferry, else <home>/ferry-staging), so a reader never re-implements it
  drive     {label, mount_hint} — the label from machine.json's carriers; the hint is how THIS
            machine SPELLS a mounted volume: `/Volumes/<label>` on macOS, and on Windows the
            form `<letter>:\\`, never a letter, because the letter is found by label at run time
  published when this content was first written. Unchanged content is not rewritten, so the
            stamp says how long this declaration has stood, not when the tool last ran.

machine.json may override `shell` and `python` with those two words — a machine with an unusual
setup declares it once and every reader obeys (nothing about one fleet is
hard-coded here).

The record is the hub's own machine.json when the hub folder has one (a gate's scratch identity —
auto-land.py's precedence, kept the same on purpose), else the machine.json of the older layout's sync folder.

Exits 0 when the declaration stands (written or already current), 1 when this machine has no
record to declare from, 2 on a flag it does not know. Stdlib only, Python 3.9, OS-neutral.
"""
import io
import json
import os
import platform
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
HUB = HERE.parent
KNOWN_FLAGS = ("--hub", "--dry", "--help", "-h")
SHELLS = ("bash", "powershell")
PYTHONS = ("python3", "python")


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


def write_lf(path, text):
    """LF, UTF-8, no BOM — the one writer, as everywhere else in this lane."""
    with io.open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def record_for(hub):
    """This machine's record: the hub's own machine.json when it has one, else the real one."""
    if hub is not None:
        found = read_json(Path(hub) / "machine.json")
        if found is not None:
            return found
    return read_json(Path.home() / "orchestrator-sync" / "machine.json")


def windows_here():
    return os.name == "nt" or platform.system().lower().startswith("windows")


def shell_of(record):
    """The shell a sheet for this machine must be written in. The record may say it outright;
    otherwise this machine answers for itself — never the other machine's guess."""
    said = str(record.get("shell") or "").strip().lower()
    if said in SHELLS:
        return said
    return "powershell" if windows_here() else "bash"


def python_of(record, shell):
    said = str(record.get("python") or "").strip().lower()
    if said in PYTHONS:
        return said
    return "python" if shell == "powershell" else "python3"


def join_like(root, leaf):
    """Join the way THAT path is written: `C:\\Users\\you` keeps its backslashes, `/Users/you`
    its slashes. This machine's own separator is usually right — but a record may carry a path in
    the other machine's spelling, and a declaration nobody can read is worse than none."""
    root = str(root or "")
    sep = "\\" if ("\\" in root or re.match(r"^[A-Za-z]:", root)) else "/"
    return root.rstrip("/\\") + sep + str(leaf)


def roots_of(record):
    """machine.json's roots, with `ferry` resolved exactly as auto-land.py resolves it."""
    roots = dict(record.get("roots") or {})
    out = {}
    for name in sorted(roots):
        value = str(roots[name] or "").strip()
        if value:
            out[name] = value
    if not out.get("ferry"):
        home = out.get("home") or str(Path.home())
        out["ferry"] = join_like(home, "ferry-staging")
    return out


def drive_of(record, shell):
    """The label from the record, and how this machine spells a mounted volume.

    On Windows the mount is a LETTER the system hands out, and the letter is found by label at
    run time (`Get-Volume | Where-Object FileSystemLabel -eq '<label>'`) — so the hint is the
    FORM, and a reader that needs the real mount asks the machine, never this file."""
    label = str(((record.get("carriers") or {}).get("drive") or {}).get("label") or "").strip()
    if not label:
        return {"label": "", "mount_hint": ""}
    hint = "<letter>:\\" if shell == "powershell" else str(Path("/Volumes") / label)
    return {"label": label, "mount_hint": hint}


def declaration(record):
    """The whole published shape, in one place, so a reader can see it at a glance."""
    shell = shell_of(record)
    return {
        "machine": str(record.get("name") or "unknown").strip().lower(),
        "os": platform.system() or "unknown",
        "shell": shell,
        "python": python_of(record, shell),
        "roots": roots_of(record),
        "drive": drive_of(record, shell),
    }


def same(a, b):
    """The declaration without its stamp: what makes a rewrite worth doing."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return {k: v for k, v in a.items() if k != "published"} == \
           {k: v for k, v in b.items() if k != "published"}


def publish(hub, dry=False):
    record = record_for(hub)
    if record is None:
        say("STOP: this machine has no machine.json to declare from — nothing published")
        return 1, None
    body = declaration(record)
    path = Path(hub) / ("roots-%s.json" % body["machine"])
    standing = read_json(path)
    words = "%s · %s · %d root(s)%s" % (body["shell"], body["python"], len(body["roots"]),
                                        (' · drive "%s"' % body["drive"]["label"])
                                        if body["drive"]["label"] else " · no drive declared")
    if same(standing, body):
        say("%s stands: %s" % (path.name, words))
        return 0, path
    body["published"] = datetime.now().astimezone().replace(microsecond=0).isoformat()
    if dry:
        say(json.dumps(body, indent=1, ensure_ascii=False))
        say("%s would be %s: %s" % (path.name, "rewritten" if standing else "written", words))
        return 0, path
    write_lf(path, json.dumps(body, indent=1, ensure_ascii=False) + "\n")
    say("%s %s: %s" % (path.name, "rewritten" if standing else "written", words))
    return 0, path


def usage(stream=sys.stdout):
    stream.write(__doc__)


def main(argv):
    if "--help" in argv or "-h" in argv:
        usage()
        return 0
    hub = HUB
    rest = list(argv)
    if "--hub" in rest:
        i = rest.index("--hub")
        if i + 1 >= len(rest):
            say("STOP: --hub needs a folder")
            return 2
        hub = Path(rest[i + 1])
        del rest[i:i + 2]
    unknown = [a for a in rest if a.startswith("-") and a not in KNOWN_FLAGS]
    if unknown:
        say("unknown flag %s" % unknown[0])
        usage(sys.stderr)
        return 2
    if not Path(hub).is_dir():
        say("STOP: the hub folder %s is not there — nothing published" % hub)
        return 1
    code, _ = publish(Path(hub), dry="--dry" in rest)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
