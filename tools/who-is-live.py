#!/usr/bin/env python3
"""who-is-live.py — who holds a pen, from the brain's live stamps and claims. No model, no tokens.

Reads every live-<machine>-<mind>.json in the hub folder (written by tools/i-am.py on
each machine, carried by the brain sync) and prints machine · mind · LIVE/off · age · title —
ONE ROW PER SESSION, since a stamp carries a list of them.

  who-is-live.py          the table
  who-is-live.py --pen    the one-writer check for the HUB arc. It reads claims.json FIRST
                          (tools/claim.py — the pen made visible) and
                          then the stamps: exit 2 with a STOP: line when ANY other session,
                          either machine, either vendor, holds the arc or has a live hub stamp
                          (a session titled "… Exocortex/…", not off, younger than --hours,
                          default 12). A hub that writes STATUS/openers while another hub is
                          live clobbers it: a handoff on one machine could rewrite the hub's
                          carryover while another hub held the pen.
  who-is-live.py --pen --arc <token>    the same check for one arc: hub · button-up · landing:AB-TX-008.
                          The answer is SCOPED TO THE ARC ASKED: only the
                          hub arc (the default) also reads the hub STAMPS on the other machine; a
                          test arc or a job arc is answered from claims.json alone, so a live hub
                          elsewhere never answers a button-up question with the hub's STOP.
  who-is-live.py --hub <folder>         read stamps and claims from another hub folder — the gates
                          run hermetic against a scratch hub, never the live one
  who-is-live.py --pen --lane <token>   the stamp check for one lane AND the claim on the arc of that name: the
                          token between the dash and the colon of a ritual title, exact (Exocortex/<lane> never
                          counts as the hub)
  who-is-live.py --pen --title "<mine>"  exclude my own claim from the check, for a session that already claimed

The answer is a DECISION, never a question: held by another → the READER
ROLE line says what this session does instead; free → the exact claim command. Nothing here is
ever put to the owner.
"""
import argparse, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

# One rule for which lane a title belongs to, shared with the semantic engine
# (exo_common.lane_token / is_lane).  Running as a script puts this folder on
# the path; being imported by a gate does not, so it is put there either way.
_TOOLS = str(Path(__file__).resolve().parent)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
from exo_common import is_lane
from exo_paths import paths            # the one answer to "where is the record"

try:                                   # Windows consoles may be cp1252/cp437: never crash on a "—" or a "→"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HUB = Path(__file__).resolve().parent.parent
CLAIMS = HUB / "claims.json"
HUB_LANE = "Exocortex/"                # the default lane: this fleet's hub token

def here():
    """This machine's name, from the machine record the path resolver finds
    (tools/exo_paths.py); "?" when no record names one."""
    try:
        record = paths(tool_file=__file__)
        return record["machine"] if record["bootstrapped"] and record["machine"] != "unknown" else "?"
    except Exception: return "?"

def fleet_manifest():
    """The sync manifest whose `machines` map names the fleet, where the sync
    package keeps it: in the brain clone, else beside the sync package (the
    older layout keeps the two in one folder). None when there is none."""
    try: record = paths(tool_file=__file__)
    except Exception: return None
    for folder in (record["brain"], record["sync_dir"]):
        for name in ("sync-manifest.json", "manifest.user.json"):
            if folder is not None and (Path(folder) / name).is_file():
                return Path(folder) / name
    return None

def machines(rows):
    """Every machine name the record knows: the stamps' own `machine` field, this
    machine from machine.json, and the brain's manifest. The hub lane's tokens
    (`<stem>/<machine>`) are built from these, so a third machine needs no edit
    here — and no machine name is written into this file."""
    out = {here()}
    out.update(str(r.get("machine") or "").lower() for r in rows)
    try:
        d = json.load(open(fleet_manifest(), encoding="utf-8"))
        out.update(str(k).strip().lower() for k in (d.get("machines") or {}))
    except Exception: pass
    return {m for m in out if m and m != "?"}

def age_hours(when):
    try: return (datetime.now(timezone.utc) - datetime.fromisoformat(when)).total_seconds() / 3600
    except Exception: return float("inf")

def entries(o):
    """One row per SESSION in a stamp file, whichever shape it is in: the
    `sessions` list the current shape carries, or the single session an older
    file carries at its top level (a machine may still hold old files). An
    off stamp keeps its own single row, so the table never loses a mind."""
    raw = o.get("sessions")
    if isinstance(raw, list):
        rows = [{"title": str(s.get("title") or ""), "when": str(s.get("when") or ""), "off": False}
                for s in raw if isinstance(s, dict)]
        if rows: return rows
        return [{"title": "", "when": str(o.get("when") or ""), "off": True}]
    return [{"title": str(o.get("session") or ""), "when": str(o.get("when") or ""), "off": bool(o.get("off"))}]

def stamps():
    out = []
    for f in sorted(HUB.glob("live-*-*.json")):
        if f.name.startswith("live-sessions-"): continue
        try: o = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if not isinstance(o, dict): continue
        for e in entries(o):
            out.append({"machine": str(o.get("machine", "?")).lower(), "mind": o.get("mind", "?"), "off": e["off"],
                        "age_h": age_hours(e["when"]), "title": e["title"], "file": f.name})
    return out

def claims():
    """Every job claim on record (tools/claim.py). A missing or malformed file
    is no claim at all — the pen check must never crash on it."""
    try: d = json.load(open(CLAIMS, encoding="utf-8"))
    except Exception: return []
    if not isinstance(d, list): return []
    return [c for c in d if isinstance(c, dict) and c.get("arc")]

def claim_holder(arc, me, my_title, hours):
    """The live claim on this arc held by SOMEBODY ELSE — any machine, this one
    included (a second window on one machine is the case that started this)."""
    want = str(arc).strip().lower()
    mine = str(my_title or "").strip().lower()
    held = []
    for c in claims():
        if str(c.get("arc", "")).strip().lower() != want: continue
        if mine and str(c.get("machine", "")).lower() == me and str(c.get("title", "")).strip().lower() == mine: continue
        h = age_hours(str(c.get("since") or ""))
        if h < hours: held.append((h, c))
    if not held: return None
    held.sort(key=lambda r: r[0])
    return held[0][1], held[0][0]

def reader_role():
    return ("READER ROLE: verify, consult, and report by mail to the holder "
            "(tools/mail.py --send <MACHINE>/<lane> ...). Write none of that lane's STATUS, "
            "openers or TREE.md from here. This decision is automatic and is never put to the owner.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--pen", action="store_true"); ap.add_argument("--lane", default=None)
    ap.add_argument("--arc", default=None); ap.add_argument("--title", default=None)
    ap.add_argument("--hours", type=float, default=12); ap.add_argument("--help", action="store_true")
    ap.add_argument("--hub", default=None)
    a = ap.parse_args()
    if a.help: print(__doc__); sys.exit(0)
    if a.hub:                                     # a scratch hub for the gates; the live folder is other sessions' state
        HUB = Path(a.hub).resolve(); CLAIMS = HUB / "claims.json"
    lane = a.lane if a.lane is not None else HUB_LANE
    me = here(); rows = stamps()
    for r in rows:
        state = "off " if r["off"] else ("LIVE" if r["age_h"] < a.hours else "old ")
        mark = "here" if r["machine"] == me else "    "
        print(f"{r['machine'].upper():5} {r['mind']:7} {state} {r['age_h']:6.1f} h  {mark}  {r['title']}")
    if a.pen:
        arc = (a.arc if a.arc else (a.lane if a.lane else "hub")).strip()
        held = claim_holder(arc, me, a.title, a.hours)
        if held:                                  # the claim wins: it is the pen made visible
            c, h = held
            _ttl = c.get('title', '')
            if str(c.get("machine") or "").lower() == me and not a.title:
                # A same-machine holder may be the caller itself; only a title tells two sessions
                # apart, and the tool cannot read the caller's — so it says what it sees and what
                # each answer means (a hub must never be stopped by its own claim).
                print(f"HELD ON THIS MACHINE: the {arc} arc is claimed here — {c.get('mind') or 'unknown'} "
                      f"since {h:.1f} h ago: \"{_ttl}\".")
                print(f"IF THAT IS YOUR TITLE you hold the pen: rerun with --title \"{_ttl}\" and read OK. "
                      f"IF NOT: " + reader_role())
                sys.exit(2)
            print(f"STOP: the {arc} arc is claimed on the {str(c.get('machine') or 'unknown').upper()} — "
                  f"{c.get('mind') or 'unknown'} since {h:.1f} h ago: \"{_ttl}\".")
            print(reader_role())
            sys.exit(2)
        want = lane.strip().rstrip("/").lower()
        stem = HUB_LANE.strip().rstrip("/").lower()       # the HUB lane: only its own tokens
        known = machines(rows)                            # never Exocortex/<other lane>
        # The stamp check is scoped to the arc asked: it runs for the hub
        # arc (whose sessions stamp hub titles) and for a --lane (whose sessions stamp that token).
        # A job arc — button-up, rename, landing:<id> — has no title of its own, so its only pen is
        # the claim, already checked above; a live hub elsewhere must never answer for it.
        stamps_apply = a.lane is not None or arc.lower() == "hub"
        others = [r for r in rows if r["machine"] != me and not r["off"] and r["age_h"] < a.hours
                  and is_lane(r["title"], want, stem, known)] if stamps_apply else []
        if others:
            r = others[0]
            print(f"STOP: the {lane.rstrip('/')} pen is on the {r['machine'].upper()} — {r['mind']} live {r['age_h']:.1f} h ago: \"{r['title']}\". Do not write that lane's STATUS or openers from here.")
            print(reader_role())
            sys.exit(2)
        if stamps_apply:
            print(f"OK: no other machine holds a live {lane.rstrip('/')} stamp (younger than {a.hours:g} h)")
        else:
            print(f"OK: the {arc} arc is answered from its claim alone — no other session holds it (younger than {a.hours:g} h); hub stamps elsewhere do not speak for it")
        _py = "python" if os.name == "nt" else "python3"
        _title = a.title if a.title else "<your title>"
        mine = [c for c in claims()                # the arc is not free when it is already YOURS
                if str(c.get("arc", "")).strip().lower() == arc.lower()
                and str(c.get("machine", "")).lower() == me and a.title
                and str(c.get("title", "")).strip().lower() == a.title.strip().lower()]
        if mine:
            print(f"HELD: the {arc} arc is yours. Release it at close: {_py} tools/claim.py --release {arc} \"{_title}\"")
        elif me == "?":                           # claim.py refuses a claim held on nobody
            print(f"UNNAMED: the {arc} arc is unclaimed, but no machine record names this machine, "
                  f"so it cannot be claimed here — run the installer first.")
        else:
            print(f"FREE: the {arc} arc is unclaimed. Take it now: {_py} tools/claim.py --claim {arc} \"{_title}\"")
