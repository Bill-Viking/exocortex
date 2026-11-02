#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exo_laws.py — one answer to "which files are the law book, and whose is each".

The law book is TWO files and one short entry file that loads them:

    <claude root>/CLAUDE.md             the entry: a title and two `@` lines
    <claude root>/exocortex-laws.md     the ENGINE's laws — how the exocortex
                                        works. Shipped with the program, rendered
                                        for this machine; a promotion never
                                        writes here.
    <hub>/dossier/LAWS.md               YOUR laws — the rules you ratified.
                                        Starts with a two-line header; every
                                        promotion writes here.

A session on the Claude side reads the entry and follows each `@` line. The
Codex and Grok sides read an AGENTS.md that names the same two files. This
module is the one place a tool asks which files those are and whose each is.

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import exo_laws

    for line, whose in exo_laws.tagged_lines(claude_root, hub):
        ...                                   # whose: "engine" | "yours"
    exo_laws.text(claude_root)                # the book as a session reads it
    exo_laws.chain(claude_root, hub)          # [{path, whose, exists, via}]

WHAT IT PROMISES
  * Importing it does nothing: no file is read until a call.
  * It never raises over a missing or unreadable file; such a file is reported
    in the chain as `exists: False` and contributes no lines.
  * `@` lines are followed ONE level deep, from the entry only — the same rule
    the tree's sky reads by. A line of the entry that is not an `@` line is the
    entry's own text and counts as YOURS: an entry file of one's own, written
    before the book was split, is still the person's.

FROM A SHELL
    python3 exo_laws.py --chain [--claude DIR] [--hub DIR]   the files, one a line
    python3 exo_laws.py --text  [--claude DIR]               the book as read

Standard library only, Python 3.9-compatible, macOS and Windows.
"""
import io
import os
import re
import sys
from pathlib import Path

API = 1

ENTRY = "CLAUDE.md"
ENGINE_BOOK = "exocortex-laws.md"            # beside CLAUDE.md, under the claude root
USER_BOOK = ("dossier", "LAWS.md")           # under the hub folder

IMPORT = re.compile(r"^\s*@(\S+)\s*$")

# The header an empty book of one's own starts with: two lines, nothing else.
USER_BOOK_HEADER = (
    "# Your laws — the rules you ratified, in your own words\n"
    "<!-- exocortex:laws · every promotion writes here, never the engine's "
    "exocortex-laws.md. Edit freely: sessions read this file at every wake. -->\n")

# The block an AGENTS.md (Codex, Grok) names its law files in: a heading line,
# then one `- <path>` line per file, in the order they are read.
AGENTS_BLOCK_HEAD = "## Law files — read both, in full, in this order"


def _home(home=None):
    if home:
        return Path(home)
    return Path(os.path.expanduser("~"))


def engine_book(claude_root):
    return Path(claude_root) / ENGINE_BOOK


def user_book(hub):
    return Path(hub).joinpath(*USER_BOOK)


def target_of(raw, claude_root, home=None):
    """Where an `@` line points: `~/…` from the home folder, an absolute path
    as it is, anything else from the claude root."""
    raw = str(raw)
    if raw.startswith("~/") or raw.startswith("~\\"):
        return _home(home) / raw[2:]
    if Path(raw).is_absolute():
        return Path(raw)
    return Path(claude_root) / raw


def _same(a, b):
    try:
        return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))
    except (OSError, ValueError):
        return False


def whose(path, claude_root, hub=None):
    """"engine" for the engine's book, "yours" for everything else a person
    wrote: their own book, the entry file, and any other file they import."""
    if _same(path, engine_book(claude_root)):
        return "engine"
    return "yours"


def _read_lines(path):
    try:
        with io.open(str(path), encoding="utf-8", errors="replace") as fh:
            return fh.readlines()
    except (OSError, ValueError):
        return None


def chain(claude_root, hub=None, home=None, entry=None):
    """[{path, whose, exists, via}] — the entry first, then every file its `@`
    lines name, in the order they stand. `via` is the `@` line's own text.
    `entry` reads another copy of the entry file (the brain's, say); its `@`
    lines still resolve from the claude root and the home folder."""
    claude_root = Path(claude_root)
    entry = Path(entry) if entry else claude_root / ENTRY
    own = _read_lines(entry)
    out = [{"path": str(entry), "whose": "yours", "exists": own is not None, "via": ""}]
    for line in own or []:
        named = IMPORT.match(line)
        if not named:
            continue
        target = target_of(named.group(1), claude_root, home)
        out.append({"path": str(target), "whose": whose(target, claude_root, hub),
                    "exists": _read_lines(target) is not None, "via": line.strip()})
    return out


def tagged_lines(claude_root, hub=None, home=None, entry=None):
    """(line, whose) for every line the session's rules are made of: the entry's
    own lines, with each file an `@` line names read in its place. A missing or
    unreadable file is skipped."""
    claude_root = Path(claude_root)
    own = _read_lines(Path(entry) if entry else claude_root / ENTRY)
    for line in own or []:
        named = IMPORT.match(line)
        if not named:
            yield line, "yours"
            continue
        target = target_of(named.group(1), claude_root, home)
        inner = _read_lines(target)
        if inner is None:
            continue
        tag = whose(target, claude_root, hub)
        for one in inner:
            yield one, tag


def text(claude_root, hub=None, home=None, entry=None):
    """The book as a session reads it: one string."""
    return "".join(line for line, _w in tagged_lines(claude_root, hub, home, entry))


def files(claude_root, home=None, entry=None):
    """[path] — the entry and every file it imports that exists: what a tool
    watches to know whether the law book changed."""
    return [Path(row["path"]) for row in chain(claude_root, None, home, entry) if row["exists"]]


def brain_rel(target, manifest, roots):
    """Where a live file is carried in the brain: its repo path by the sync
    manifest (a `file` entry's own path, or a path under a `tree` entry), or
    None when nothing carries it. `roots` is the machine record's roots."""
    target = os.path.normcase(os.path.abspath(str(target)))
    for entry in (manifest or {}).get("entries") or []:
        live = entry.get("live") or {}
        base = (roots or {}).get(live.get("root") or "")
        repo = entry.get("repo")
        if not base or not repo or "{machine}" in str(repo):
            continue
        where = os.path.normcase(os.path.abspath(os.path.join(str(base), live.get("rel") or "")))
        if entry.get("kind") == "file" and target == where:
            return str(repo)
        if entry.get("kind") == "tree" and (target + os.sep).startswith(where.rstrip(os.sep) + os.sep) \
                and target != where:
            rest = os.path.relpath(target, where).replace(os.sep, "/")
            return (str(repo).rstrip("/") + "/" + rest) if repo else rest
    return None


def entry_text(claude_root, hub, home=None, title=None):
    """The three-line entry file: a title and the two `@` lines, each written
    home-relative when the file sits under the home folder."""
    home = _home(home)
    lines = [title or "# Your instructions — the lines below load the exocortex laws and yours"]
    for path in (engine_book(claude_root), user_book(hub)):
        lines.append("@" + home_form(path, home))
    return "\n".join(lines) + "\n"


def home_form(path, home=None):
    """`~/<rest>` for a path under the home folder, else the path itself."""
    home = _home(home)
    for p, h in ((Path(path), home), (Path(os.path.realpath(str(path))),
                                      Path(os.path.realpath(str(home))))):
        try:
            return "~/" + p.relative_to(h).as_posix()
        except ValueError:
            continue
    return str(path)


def agents_files(agents_text, home=None):
    """The law files an AGENTS.md names in its law-files block, in order, as
    paths. [] when the file carries no such block."""
    out = []
    inside = False
    for raw in (agents_text or "").splitlines():
        line = raw.strip()
        if line == AGENTS_BLOCK_HEAD:
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("- "):
            item = line[2:].strip().strip("`")
            item = re.split(r"\s{2,}\(", item)[0].strip().strip("`")
            if item.startswith("~/") or item.startswith("~\\"):
                out.append(_home(home) / item[2:])
            else:
                out.append(Path(item))
            continue
        if line == "":
            if out:
                break
            continue
        break
    return out


def _arg(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    claude = Path(_arg(argv, "--claude") or (_home() / ".claude"))
    hub = _arg(argv, "--hub")
    if "--text" in argv:
        sys.stdout.write(text(claude, hub))
        return 0
    if "--chain" in argv or not argv:
        for row in chain(claude, hub):
            sys.stdout.write("%-6s %s %s\n" % (row["whose"], "ok  " if row["exists"] else "MISSING",
                                              row["path"]))
        return 0
    sys.stdout.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
