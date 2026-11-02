#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split-laws.py — one law book becomes two: the engine's and yours.

An exocortex whose rules still live in ONE CLAUDE.md is split, line by line,
by a TABLE that says where each line goes:

    engine   → <claude root>/exocortex-laws.md   how the exocortex works
    yours    → <hub>/dossier/LAWS.md              the rules the person ratified

and CLAUDE.md becomes three lines that load both. Every line of text lands in
exactly one of the two files; headings are structure and stand in each file
that holds a line under them; blank lines are layout. Nothing is ever written
in place: the three files are written into a folder you name, and the one who
installs them moves them.

    python3 tools/split-laws.py --units  [--claude-md FILE] [--json]
            every line of text with its fingerprint (the table's key)
    python3 tools/split-laws.py --check  --table TABLE.json [--claude-md FILE]
            every line placed? exit 0, or 2 naming each line the table misses
    python3 tools/split-laws.py --split  --table TABLE.json --out DIR
                                [--claude-md FILE] [--claude DIR] [--hub DIR] [--home DIR]
            write DIR/CLAUDE.md, DIR/exocortex-laws.md, DIR/LAWS.md; refuses
            when a line is unplaced, when DIR holds any of the three already, or
            when DIR is the claude root or the hub's dossier/
    python3 tools/split-laws.py --verify DIR [--claude-md FILE]
            the byte accounting: every line of the source present exactly once
            across the two books, nothing else but structure

The table's rows are {"fp": <fingerprint>, "to": "engine" | "yours", ...}; a
fingerprint is the first 16 hex of the line's sha256, so the table survives a
line moving and names a line that changed. Standard library only, Python
3.9-compatible, macOS and Windows.
"""
import collections
import hashlib
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import exo_laws                                          # noqa: E402

ENGINE_HEADER = ("<!-- exocortex-laws.md · the engine's law book: how the exocortex works. "
                 "Your own rules live in your law book (dossier/LAWS.md); a promotion never "
                 "writes here. -->\n")
TO_WORDS = {"engine": "engine", "yours": "yours", "owner": "yours"}


def fp(line):
    return hashlib.sha256(line.rstrip("\n").encode("utf-8")).hexdigest()[:16]


def read_lines(path):
    with io.open(str(path), encoding="utf-8", newline="") as fh:
        text = fh.read()
    return text.replace("\r\n", "\n").split("\n")


def is_heading(line):
    return line.startswith("#")


def level(line):
    return len(line) - len(line.lstrip("#"))


def units(lines):
    """[(line number, text)] — every line that is neither a heading nor blank."""
    return [(n, l) for n, l in enumerate(lines, 1) if l.strip() and not is_heading(l)]


def load_table(path):
    data = json.loads(io.open(str(path), encoding="utf-8").read())
    rows = data.get("rows") if isinstance(data, dict) else data
    out = {}
    for row in rows or []:
        to = TO_WORDS.get(str(row.get("to", "")).lower())
        if to and row.get("fp"):
            out[row["fp"]] = to
    return out


def placement(lines, table):
    """({line number: to}, [(n, text) unplaced])"""
    placed, missing = {}, []
    for n, text in units(lines):
        to = table.get(fp(text))
        if to is None:
            missing.append((n, text))
        else:
            placed[n] = to
    return placed, missing


def book(lines, placed, to):
    """The lines one book gets: its own text lines, each heading whose scope
    holds one of them, blank lines kept single and never at either end."""
    keep_heading = {}
    for i, line in enumerate(lines, 1):
        if not is_heading(line):
            continue
        lv = level(line)
        j = i + 1
        hit = False
        while j <= len(lines):
            other = lines[j - 1]
            if is_heading(other) and level(other) <= lv:
                break
            if placed.get(j) == to:
                hit = True
                break
            j += 1
        keep_heading[i] = hit
    out = []
    for i, line in enumerate(lines, 1):
        if is_heading(line):
            if keep_heading.get(i):
                if out and out[-1] != "":
                    out.append("")
                out.append(line)
            continue
        if not line.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        if placed.get(i) == to:
            out.append(line)
    while out and out[-1] == "":
        out.pop()
    while out and out[0] == "":
        out.pop(0)
    return out


def text_lines(text, drop=()):
    """The text lines of a written book: not blank, not a heading, not one of
    the book's own header lines."""
    drop = set(l.rstrip("\n") for l in drop)
    return [l for l in text.replace("\r\n", "\n").split("\n")
            if l.strip() and not is_heading(l) and l not in drop]


def verify(folder, source_lines):
    """[problems] — empty when the split accounts for every byte."""
    folder = Path(folder)
    problems = []
    got = {}
    for name in ("CLAUDE.md", exo_laws.ENGINE_BOOK, "LAWS.md"):
        try:
            got[name] = io.open(str(folder / name), encoding="utf-8").read()
        except OSError:
            problems.append("%s is missing from %s" % (name, folder))
    if problems:
        return problems
    src = [l for _n, l in units(source_lines)]
    eng = text_lines(got[exo_laws.ENGINE_BOOK], ENGINE_HEADER.splitlines())
    yours = text_lines(got["LAWS.md"], exo_laws.USER_BOOK_HEADER.splitlines())
    a, b = collections.Counter(src), collections.Counter(eng) + collections.Counter(yours)
    if a != b:
        lost = list((a - b).elements())
        extra = list((b - a).elements())
        problems.append("the two books differ from the source: %d line(s) lost, %d extra"
                        % (len(lost), len(extra)))
        for l in (lost + extra)[:5]:
            problems.append("   " + l[:120])
    both = set(eng) & set(yours)
    if both:
        problems.append("%d line(s) stand in BOTH books" % len(both))
    src_bytes = sum(len(l.encode("utf-8")) for l in src)
    out_bytes = sum(len(l.encode("utf-8")) for l in eng + yours)
    if src_bytes != out_bytes:
        problems.append("text bytes differ: source %d, books %d" % (src_bytes, out_bytes))
    entry = [l for l in got["CLAUDE.md"].split("\n") if l.strip()]
    imports = [l for l in entry if exo_laws.IMPORT.match(l)]
    if len(entry) != 3 or len(imports) != 2:
        problems.append("CLAUDE.md is not three lines (a title and two `@` lines): %d lines, "
                        "%d imports" % (len(entry), len(imports)))
    return problems


def _arg(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def _default_roots():
    try:
        from exo_paths import paths                       # noqa: E402
        record = paths(tool_file=__file__)
        roots = record.get("roots") or {}
        return (Path(roots.get("claude") or Path(os.path.expanduser("~")) / ".claude"),
                Path(record.get("hub") or HERE.parent))
    except Exception:
        return Path(os.path.expanduser("~")) / ".claude", HERE.parent


def say(line):
    try:
        sys.stdout.write(line + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(line.encode("ascii", "replace").decode("ascii") + "\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or "--help" in argv:
        sys.stdout.write(__doc__)
        return 0
    claude_default, hub_default = _default_roots()
    claude = Path(_arg(argv, "--claude") or claude_default)
    hub = Path(_arg(argv, "--hub") or hub_default)
    home = Path(_arg(argv, "--home") or os.path.expanduser("~"))
    source = Path(_arg(argv, "--claude-md") or (claude / "CLAUDE.md"))
    try:
        lines = read_lines(source)
    except OSError as exc:
        say("refused: %s cannot be read (%s)" % (source, exc))
        return 2
    if "--units" in argv:
        rows = [{"n": n, "fp": fp(t), "head": t[:90]} for n, t in units(lines)]
        if "--json" in argv:
            say(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                say("%4d %s %s" % (r["n"], r["fp"], r["head"]))
        return 0
    if "--verify" in argv:
        problems = verify(_arg(argv, "--verify"), lines)
        for p in problems:
            say("FAIL " + p)
        if not problems:
            say("OK the split accounts for every line: %d text lines, each in exactly one book"
                % len(units(lines)))
        return 2 if problems else 0
    table_file = _arg(argv, "--table")
    if not table_file:
        say("refused: --table TABLE.json is needed")
        return 2
    table = load_table(table_file)
    placed, missing = placement(lines, table)
    if "--check" in argv or missing:
        for n, text in missing:
            say("UNPLACED line %d %s  %s" % (n, fp(text), text[:100]))
        if missing:
            say("refused: %d line(s) the table does not place — nothing was written"
                % len(missing))
            return 2
        say("OK every line placed: %d engine · %d yours"
            % (sum(1 for v in placed.values() if v == "engine"),
               sum(1 for v in placed.values() if v == "yours")))
        if "--check" in argv:
            return 0
    if "--split" not in argv:
        sys.stdout.write(__doc__)
        return 2
    out = _arg(argv, "--out")
    if not out:
        say("refused: --out DIR is needed; the split is never written in place")
        return 2
    out = Path(out)
    for live in (claude, hub / "dossier"):
        if os.path.normcase(os.path.abspath(str(out))) == os.path.normcase(os.path.abspath(str(live))):
            say("refused: --out is a live folder (%s); the split is never written in place" % live)
            return 2
    names = ("CLAUDE.md", exo_laws.ENGINE_BOOK, "LAWS.md")
    there = [n for n in names if (out / n).exists()]
    if there:
        say("refused: %s already holds %s — nothing was written" % (out, ", ".join(there)))
        return 2
    out.mkdir(parents=True, exist_ok=True)
    engine = book(lines, placed, "engine")
    yours = book(lines, placed, "yours")
    files = {
        exo_laws.ENGINE_BOOK: ENGINE_HEADER + "\n" + "\n".join(engine) + "\n",
        "LAWS.md": exo_laws.USER_BOOK_HEADER + "\n" + "\n".join(yours) + "\n",
        "CLAUDE.md": exo_laws.entry_text(claude, hub, home),
    }
    for name in names:
        with io.open(str(out / name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(files[name])
    problems = verify(out, lines)
    for p in problems:
        say("FAIL " + p)
    if problems:
        return 2
    for name in names:
        data = (out / name).read_bytes()
        say("OK %-18s %6d bytes  sha256 %s" % (name, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
