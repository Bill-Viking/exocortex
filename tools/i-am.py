#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i-am.py — a session says which mind is up on this machine, for the roots.

    python3 tools/i-am.py FABLE EXTRA "ACT — Exocortex: hub"
    python3 tools/i-am.py --off FABLE "ACT — Exocortex: hub"
    python3 tools/i-am.py --off FABLE        # every session of that mind here
    python3 tools/i-am.py --off              # switch off every live mind here
    python3 tools/i-am.py ... --hub <folder> # stamp into another hub folder (the gates' scratch hub)
    python3 tools/i-am.py ... --quiet        # stamp, and tell no other machine (gate runs)

Writes live-<machine>-<mind>.json in the hub folder (synced with the brain) —
ONE stamp per mind, so two minds up on the same machine (FABLE and GPT, say)
no longer overwrite each other. The stamp is KEYED BY SESSION:

    {"machine": "laptop", "mind": "OPUS", "when": "<iso>",
     "sessions": [{"title": "...", "effort": "EXTRA", "when": "<iso>"}, ...]}

because one stamp per mind was still one stamp too few: two sessions of the
same mind on the same machine wiped each other, and the survivor's --off then
switched the other one dark.
A run with a title adds or refreshes THAT session's entry and leaves the rest
alone; --off <MIND> "<title>" removes only that entry; bare --off <MIND>
clears them all, naming what it switched off. A stamp in the old
single-object shape is read everywhere as a one-entry list, so a machine
that still carries old files is read right.

The tree page reads every live-*.json: a session under 12 hours old counts as
live; older ones show as "last mind"; an emptied stamp is written off (never a
deletion, so the sync never asks). The legacy one-per-machine file
live-<machine>.json is rewritten as an off stamp on any run, and never
deleted. Run it at a session's start, right after the clock; run
--off <MIND> "<title>" at close. Stdlib only, OS-neutral. The machine's name
comes from the machine record the path resolver finds (tools/exo_paths.py); a
machine whose record names no machine stamps nothing and says so in one line.

ARRIVALS ANNOUNCE THEMSELVES. A stamp that is new
here writes ONE line to every OTHER machine's hub through tools/mail.py beside
this file — "<MACHINE> <MIND> woke at HH:MM · \"<title>\" · effort <EFFORT>" —
and --off writes the matching "signed off" line. Re-stamping a title that is
already up says nothing: a refresh is not an arrival. A fleet of one machine
sends nothing, --quiet sends nothing, and a letter that fails never fails the
stamp.
"""
import io, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_registry import registry, mind_alias                         # noqa: E402
from exo_paths import paths                                           # noqa: E402
try:                                   # a private lane's stamp carries its NAME only
    from exo_privacy import public_title                              # noqa: E402
except Exception:
    def public_title(title, **_kw):
        return title


def shown(title, hub=None):
    """The title a stamp may carry. ASSUMES: --off compares two shown titles,
    so a private window still switches itself off. Opposite: gate-privacy C6b."""
    try:
        return public_title(str(title or ""), cwd=os.getcwd(), hub=hub)
    except Exception:
        return title

_REG = [None]


def _reg():
    """The person's own names, read once per run."""
    if _REG[0] is None:
        _REG[0] = registry()
    return _REG[0]

try:                                   # WHICH SESSION this stamp belongs to
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_common import identity_or_nonce
except Exception:                      # i-am.py standing alone stamps exactly as before
    def identity_or_nonce(title="", arcs=(), hub=None): return {}, ""


def machine():
    """(this machine's name, its recorded roots) from the machine record the
    path resolver finds — ("unknown", {}) when no record names a machine."""
    try:
        record = paths(tool_file=__file__)
        return record["machine"], dict(record["roots"])
    except Exception:
        return "unknown", {}


def unnamed_line():
    """The one sentence a stamp on an unnamed machine gets, instead of a stamp."""
    try:
        found = paths(tool_file=__file__)["machine_file"]
    except Exception:
        found = None
    where = ("the machine record %s names no machine" % found) if found else \
        "no machine record was found for this machine"
    return ("i-am.py: %s, so a stamp written here would say nobody is up — run the "
            "installer, then stamp again; nothing was stamped." % where)


def now_iso():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def write_stamp(path, d):
    io.open(path, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    return path


def read_stamp(path):
    try:
        d = json.loads(io.open(path, encoding="utf-8").read())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def sessions_of(d):
    """Every session in a stamp, whichever shape it is in.

    The new shape carries a `sessions` list; a stamp in the older shape
    carried one session at the top level (`session`/`effort`/`when`) and is
    read here as a one-entry list, so an old file on either machine still
    counts. An off stamp holds no sessions."""
    if not isinstance(d, dict):
        return []
    raw = d.get("sessions")
    if isinstance(raw, list):
        out = []
        for s in raw:
            if isinstance(s, dict) and (s.get("title") or s.get("effort") or s.get("when")):
                # dict(s, …) and not a fresh three-key entry: a session's identity
                # keys (session / host_session / vendor) belong to that
                # session, and a re-stamp by ANOTHER session here must not drop them.
                out.append(dict(s, title=str(s.get("title") or ""),
                                effort=str(s.get("effort") or ""),
                                when=str(s.get("when") or "")))
        return out
    if d.get("off"):
        return []
    if not (d.get("session") or d.get("effort") or d.get("when")):
        return []                      # an empty or missing file holds no session (a first stamp into a fresh folder must not carry a phantom blank entry)
    return [{"title": str(d.get("session") or ""), "effort": str(d.get("effort") or ""),
             "when": str(d.get("when") or "")}]


def live_stamp(name, mind, sessions):
    """The file body for a mind with sessions up. The top-level `when` is the
    newest session's, so a reader that only knows the old shape still sees
    freshness."""
    newest = max([s.get("when") or "" for s in sessions] or [""])
    return {"machine": name, "mind": mind, "when": newest or now_iso(), "sessions": sessions}


def canon_mind(mind):
    """The mind a stamp MEANS. A word the person has given a mind of their own
    becomes that mind; a word nobody has claimed stays itself (so one
    desktop's sessions can share one name)."""
    return mind_alias(_reg(), mind)

def announce(folder, text, quiet=False):
    """One machine-made line to every other machine's hub, through the mail.py
    that travels beside this file (the gates run a copy, and a copy must mail
    with its own mail.py). The fleet, the addresses and the push are mail.py's —
    this tool only says what happened. Never raises: a letter that cannot be
    sent is reported in one line and the stamp still stands."""
    if quiet:
        return
    tool = Path(__file__).resolve().parent / "mail.py"
    if not tool.is_file():
        print("  not announced: %s is missing" % tool)
        return
    try:
        r = subprocess.run([sys.executable, str(tool), "--announce", text, "--hub", str(folder)],
                           capture_output=True, text=True)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        for line in (out.splitlines() or ["mail.py said nothing"]):
            print("  %s" % line)
    except Exception as exc:
        print("  not announced: %s" % exc)


def woke_line(name, mind, effort, title):
    return "%s %s woke at %s · \"%s\" · effort %s" % (
        name.upper(), mind, datetime.now().strftime("%H:%M"), title, str(effort).upper())


def off_line(name, mind, what):
    return "%s %s signed off at %s · %s" % (name.upper(), mind, datetime.now().strftime("%H:%M"), what)


def what_left(sessions):
    """What an --off line names: the one session's title in quotes, or how many
    left at once. A count is the truthful answer when several go together."""
    titled = [s.get("title", "").strip() for s in sessions if s.get("title", "").strip()]
    if len(sessions) == 1 and titled:
        return "\"%s\"" % titled[0]
    return "%d session%s" % (len(sessions), "" if len(sessions) == 1 else "s")


def mind_file(folder, name, mind):
    return folder / ("live-%s-%s.json" % (name, canon_mind(mind).lower()))


def retire_legacy(folder, name):
    """The old one-per-machine stamp becomes an off stamp on any run — its mind
    and its when kept. Never deleted: a deletion makes the sync ask the hub for
    a ruling every single close."""
    legacy = folder / ("live-%s.json" % name)
    if not legacy.is_file():
        return None
    d = read_stamp(legacy)
    if d.get("off"):
        return None
    out = {"machine": d.get("machine", name), "off": True}
    if d.get("mind"):
        out["mind"] = d["mind"]
    out["when"] = d.get("when") or now_iso()
    write_stamp(legacy, out)
    return legacy


def codex_stamp(mind, entry):
    """Use measured values only for a fresh active turn; retain the evidence."""
    import importlib.util
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(
            "codex_dial", Path(__file__).resolve().parent / "codex_dial.py")
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
    except (OSError, ImportError, AttributeError):
        return mind, "the reader saw UNKNOWN (codex_reader_unavailable), age unknown; stamped the label you gave"
    reading = reader.read_dial()
    if reading["state"] == "current":
        from exo_common import mind_of
        measured = canon_mind(mind_of("codex", reading["model"]))
        # Unknown model ids may be displayed, but never become path traversal.
        if measured and all(c.isalnum() or c in "-_." for c in measured) and ".." not in measured:
            entry["effort"] = reading["effort"].upper()
            entry["dial"] = reading
            return measured, ""
        reading = dict(reading, state="unknown", reason="model_not_stampable")
    seen = reader.format_reading(reading)
    return mind, "the reader saw {}; stamped the label you gave".format(seen)


def main(argv):
    try:                                   # Windows consoles may be cp437: never crash on the plate's "·"
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if "--help" in argv or "-h" in argv:   # asking what it does never writes a stamp
        print(__doc__); return 0
    name, roots = machine()
    if name == "unknown":
        print(unnamed_line())
        return 1
    folder = Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    if "--hub" in argv:                    # the gates stamp a scratch hub, never the live folder
        i = argv.index("--hub")
        if i + 1 >= len(argv):
            print("--hub needs a folder"); return 1
        folder = Path(argv[i + 1]).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        argv = argv[:i] + argv[i + 2:]
    legacy = retire_legacy(folder, name)
    if legacy is not None:
        print("%s: legacy %s rewritten as an off stamp (one stamp per mind now)" % (name.upper(), legacy.name))
    vendor = ""
    if "--vendor" in argv:
        index = argv.index("--vendor")
        if index + 1 >= len(argv) or argv[index + 1] not in ("codex", "claude", "grok"):
            print("--vendor needs codex, claude or grok"); return 1
        vendor = argv[index + 1]
        argv = argv[:index] + argv[index + 2:]
    quiet = "--quiet" in argv      # a gate run stamps without telling the other machine
    args = [a for a in argv if not a.startswith("--")]
    if "--off" in argv:
        if args:                       # --off FABLE ["<title>"]  (or  FABLE --off)
            mind = args[0].upper()
            title = shown(" ".join(args[1:]).strip(), hub=folder)
            target = mind_file(folder, name, mind)
            keep = sessions_of(read_stamp(target))
            if title:                  # one session leaves; the mind's others stay up
                left = [s for s in keep if s.get("title", "").strip() != title]
                if len(left) == len(keep) and keep:
                    print("%s: %s — no session titled \"%s\" is stamped here; nothing switched off"
                          % (name.upper(), mind, title))
                    return 0
                if left:
                    write_stamp(target, live_stamp(name, canon_mind(mind), left))
                    print("%s: %s off for \"%s\" — %d session%s still live: %s"
                          % (name.upper(), mind, title, len(left), "" if len(left) == 1 else "s",
                             " · ".join(s.get("title") or "(untitled)" for s in left)))
                    announce(folder, off_line(name, canon_mind(mind), '"%s"' % title), quiet)
                    return 0
            elif len(keep) > 1:        # bare --off <MIND> takes them all down at once
                print("%s: %s — switching off %d sessions: %s"
                      % (name.upper(), mind, len(keep),
                         " · ".join(s.get("title") or "(untitled)" for s in keep)))
            write_stamp(target, {"machine": name, "mind": canon_mind(mind), "off": True,
                                 "sessions": [], "when": now_iso()})
            print("%s: %s off — %s" % (name.upper(), mind, target))
            if keep:                   # nothing was up: nothing to tell the other machine
                announce(folder, off_line(name, canon_mind(mind), what_left(keep)), quiet)
            return 0
        done = []                      # --off alone: every live mind on this machine
        for f in sorted(folder.glob("live-%s-*.json" % name)):
            d = read_stamp(f)
            if d.get("off") or not d.get("mind"):
                continue
            mind = str(d["mind"]).upper()
            keep = sessions_of(d)
            write_stamp(f, {"machine": d.get("machine", name), "mind": canon_mind(mind), "off": True,
                            "sessions": [], "when": now_iso()})
            done.append((mind, f, keep))
        if not done:
            print("%s: nothing live to switch off" % name.upper())
        for mind, f, keep in done:
            if len(keep) > 1:
                print("%s: %s — switching off %d sessions: %s"
                      % (name.upper(), mind, len(keep),
                         " · ".join(s.get("title") or "(untitled)" for s in keep)))
            print("%s: %s off — %s" % (name.upper(), mind, f))
            if keep:
                announce(folder, off_line(name, canon_mind(mind), what_left(keep)), quiet)
        return 0
    if len(args) < 2:
        print(__doc__); return 1
    mind = canon_mind(args[0])
    entry = {"title": shown(" ".join(args[2:]), hub=folder) if len(args) > 2 else "",
             "effort": args[1].upper(), "when": now_iso()}
    ident, id_line = identity_or_nonce(title=entry["title"], hub=folder)
    for k in ("session", "host_session", "vendor"):
        if ident.get(k):
            entry[k] = ident[k]
    # Shared identity precedence stays in exo_common. An explicit vendor is
    # authoritative; otherwise use its identity, then an unclaimed Codex host.
    vendor = vendor or ident.get("vendor") or (
        "codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "")
    discrepancy = ""
    if vendor == "codex":
        mind, discrepancy = codex_stamp(mind, entry)
    target = mind_file(folder, name, mind)
    before = sessions_of(read_stamp(target))
    kept = [s for s in before
            if s.get("title", "").strip() != entry["title"].strip()]
    sessions = kept + [entry]          # same title = the same session, refreshed
    write_stamp(target, live_stamp(name, mind, sessions))
    if discrepancy:
        print(discrepancy)
    print("%s: %s · %s live — %s" % (name.upper(), mind, entry["effort"], target))
    print("%s: %d session%s live for %s" % (name.upper(), len(sessions),
                                            "" if len(sessions) == 1 else "s", mind))
    if id_line:
        print(id_line)                 # the one added line, only where the vendor gives no id
    if len(kept) == len(before):       # a title already up was refreshed, not an arrival
        announce(folder, woke_line(name, mind, entry["effort"], entry["title"]), quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
