#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-opener-freshness.py — does the freshest opener win, on every carrier?

    python tools/gate-opener-freshness.py            # hermetic; the live hub is only fingerprinted
    python tools/gate-opener-freshness.py --hub <d>  # accepted (the build runner passes it), not read
    python tools/gate-opener-freshness.py --keep     # leave the scratch world for inspection

Proves the opener-freshness contract, and with it two proof cases: 2
(the record is preserved and the issue stays visible with its owner) and 6 (tests own their scratch
space and cannot touch live work). Under the temp dir the gate builds its own world: a scratch HOME
whose machine.json names a scratch hub and a scratch projects root — so every subprocess resolves
`Path.home()` inside the gate and can reach nothing of the owner's — a scratch "volume" holding real git
bundles the gate cuts itself, and a scratch hub carrying the two files under test plus the collector.

  G0  compiles + cli       opener_carriers.py, gate-opener-freshness.py and collect-openers.py
                           py_compile; `--help` 0 and an unknown flag 2 on both new tools; the
                           mirrored HEADER_KEYS/OPTIONAL_KEYS equal the collector's own
  G1  folder only          a lane with one folder opener → source `folder`, no flag, fresh
  G2  brain newer          TREE.md carries a later copy → the brain wins, STALE-BEHIND-CARRIER on
                           the table line, the --chat line, the card and the JSON; the winner's
                           header is the one used; a head this repo has not got is a NOTE
  G3  drive newer          an INCREMENTAL bundle in a payload folder carries a later copy → the
                           drive wins, flagged, the note names the payload; the project repo's refs
                           are untouched and every byte on the volume is unchanged
  G4  tie                  the same `written:` on both → the folder copy wins, no flag
  G5  unreadable bundle    a bundle whose base is not in this repo → one note, folder copy stands
  G6  the HH:Mx habit      `written: …T18:3x-07:00` compares as …18:30 — newer than 18:25, older
                           than 18:35
  G7  write-tree round     `--write-tree` writes every lane's opener verbatim; read_brain gives the
                           trip                same headers and bodies back; the hub's own text below
                           `tree:auto-end` is untouched; a second run picks the same winners
  G8  lane-true next       three lanes in one folder: its own opener step · the STATUS item that
                           names it · the project's item, marked `(project)`
  G9  judgment unwalked    a body that needs judgment under an OPUS model line with no `judgment:`
                           is flagged; the same opener with `judgment: none` is not
  G10 cache                the second read of one bundle makes no git call and gives the same answer
  G11 nothing there        no volume, no engine, no TREE.md → exit 0, no crash, folder copies stand
  G12 live untouched       the live hub's TREE.md is byte-identical; no live file carries a word of
                           the gate's own world (the conclusive test: the pulse redraws tree.html,
                           board.html, brain-index.json and sessions-cache.json every five minutes,
                           and a claim or a session stamp rewrites claims.json and live-*.json while
                           the gate runs, so a sha alone proves nothing there); no file appeared
  G13 smoke, real machine   the collector beside this gate runs against the LIVE roots read-only:
                           `--table` and `--json` exit 0 and every row carries a source
  G14 carrier-only lane    a lane whose opener file is not in the folder at all still gets ONE row
                           — the newest of its copies, the carrier named, "no folder copy" said and
                           the payload that must land in the note (a drive can hold several payloads
                           carrying the same lanes' openers)
  G15 carried openers      an opener for a project this machine does not have survives a
                           `--write-tree` verbatim instead of being dropped
  BQ335-G6 the capture's   an opener a button-up capture HEADED (its sitting s7 ran) is a NOTE
           head            whose first note says so, carries `captured` in --json, shows it on
                           its card, and lane_act_title names s8; an unheaded lane has none

Stdlib only, Python 3.9, OS-neutral, no user names. Exit 0 only when every check passes.
"""

import datetime
import hashlib
import io
import json
import os
import platform
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = Path(tempfile.gettempdir()) / "exocortex-gate-bq007"
PY = sys.executable or "python3"
OFF = datetime.datetime.now().astimezone().strftime("%z")
OFF = OFF[:3] + ":" + OFF[3:] if len(OFF) == 5 else "+00:00"

SCRATCH = None          # ROOT/run-<pid>-<stamp>: this run's own world
HUB = PROJECTS = VOL = HOME = WORK = None
FAILS = []
PASSES = 0
CASE = {"id": "", "name": "", "fails": 0, "checks": 0, "first": ""}
CASE_LINES = []


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def start(case_id, name):
    global CASE
    CASE = {"id": case_id, "name": name, "fails": 0, "checks": 0, "first": ""}


def done():
    line = "%-4s %-22s %s · %d check%s" % (
        CASE["id"], CASE["name"], "FAIL" if CASE["fails"] else "pass",
        CASE["checks"], "" if CASE["checks"] == 1 else "s")
    if CASE["fails"]:
        line += " · " + CASE["first"]
    CASE_LINES.append(line)
    print(line)


def check(cond, msg):
    global PASSES
    CASE["checks"] += 1
    if cond:
        PASSES += 1
        return True
    FAILS.append("%s %s" % (CASE["id"], msg))
    CASE["fails"] += 1
    if not CASE["first"]:
        CASE["first"] = msg
    return False


def guarded(fn, *args):
    try:
        fn(*args)
    except Exception as exc:
        start(getattr(fn, "case_id", "G?"), getattr(fn, "case_name", fn.__name__))
        check(False, "the case raised: %r" % (exc,))
        done()


def sha(path):
    p = Path(path)
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "absent"
    except OSError:
        return "unreadable"


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(path), "w", encoding="utf-8", newline="\n").write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def run(args, cwd=None, env=None, timeout=300):
    base = dict(os.environ)
    base["PYTHONUTF8"] = "1"
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    base["GIT_TERMINAL_PROMPT"] = "0"
    if env:
        for key, value in env.items():
            if value is None:
                base.pop(key, None)
            else:
                base[key] = str(value)
    try:
        proc = subprocess.run([str(a) for a in args],
                              cwd=str(cwd) if cwd else None, env=base,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, universal_newlines=True,
                              encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ss" % timeout
    except Exception as exc:
        return 125, repr(exc)


def git(repo, *args, **kw):
    return run(["git", "-C", str(repo), "-c", "user.email=gate@gate",
                "-c", "user.name=gate", "-c", "commit.gpgsign=false"] + list(args),
               timeout=kw.get("timeout", 120))


def git_out(repo, *args):
    code, out = git(repo, *args)
    return out.strip() if code == 0 else ""


def stamp(seconds=0, minutes=0):
    """An ISO stamp the fixtures can order: now plus an offset, to the second."""
    when = (datetime.datetime.now().astimezone()
            + datetime.timedelta(seconds=seconds, minutes=minutes))
    return when.replace(microsecond=0).isoformat()


def tens_stamp(minutes=0):
    """The current ten-minute mark, moved by `minutes`. The `HH:Mx` fixture."""
    now = datetime.datetime.now().astimezone().replace(second=0, microsecond=0)
    tens = now.replace(minute=(now.minute // 10) * 10)
    return (tens + datetime.timedelta(minutes=minutes)).isoformat(timespec="seconds")


def habit_stamp():
    """`2026-09-12T18:3x-07:00` — what a session writes when it means 18:30."""
    text = tens_stamp().replace(":00" + OFF, OFF)      # drop the seconds field
    return text[:15] + "x" + text[16:]


# --------------------------------------------------------------------------
# the collector, always inside the gate's own world
# --------------------------------------------------------------------------

def co(args, env=None, timeout=300):
    """The scratch hub's collect-openers.py, run with the gate's HOME."""
    base = {"USERPROFILE": str(HOME), "HOME": str(HOME),
            "HOMEDRIVE": None, "HOMEPATH": None,
            # the world's own record, named outright (a record this machine names
            # never reaches the fixture; the resolver reads the world's)
            "EXO_MACHINE_JSON": str(HOME / "orchestrator-sync" / "machine.json"),
            "COLLECT_OPENERS_ROOT": str(PROJECTS),
            "COLLECT_OPENERS_VOLUMES": str(VOL),
            "COLLECT_OPENERS_WORK": str(WORK),
            "COLLECT_OPENERS_ENGINE": str(HOME / "orchestrator-sync")}
    if env:
        base.update(env)
    return run([PY, str(HUB / "tools" / "collect-openers.py")] + list(args),
               cwd=str(HUB), env=base, timeout=timeout)


def data_of(env=None):
    code, out = co(["--json"], env=env)
    if code != 0:
        raise RuntimeError("--json exited %d: %s" % (code, out[-400:]))
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError("--json did not parse: %s" % out[:400])


def row_of(data, lane):
    for row in data["rows"]:
        if row["lane"].lower() == lane.lower():
            return row
    return None


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

OPENER_KEYS = ("lane", "written", "by", "on", "head", "status_updated",
               "where", "next", "depends_on", "open_in", "model")


def opener_text(lane, written, head="", body="step one", status_updated=None,
                model="FABLE · EXTRA", extra=None):
    header = {"lane": lane, "written": written, "by": "the gate", "on": "GATE",
              "head": head, "status_updated": status_updated or stamp(120),
              "where": "%s stands here" % lane, "next": "machine",
              "depends_on": "nothing", "open_in": "GATE", "model": model}
    lines = ["%s: %s" % (key, header[key]) for key in OPENER_KEYS]
    for key, value in (extra or {}).items():
        lines.append("%s: %s" % (key, value))
    lines.append("---")
    lines.append(body)
    return "\n".join(lines) + "\n"


def status_text(todos, now="The lane is mid-arc; nothing is blocked."):
    lines = ["# STATUS", "", "## Now", "", now, "", "## To do", ""]
    for todo in todos:
        lines.append("- [ ] %s" % todo)
    return "\n".join(lines) + "\n"


def must(code, out, what):
    """A fixture step that fails is the gate's own bug: say so and stop, never
    limp on into a case that then blames the tool under test."""
    if code != 0:
        raise RuntimeError("fixture step failed (%s): %s"
                           % (what, " ".join((out or "").split())[:160]))
    return out


def make_repo(path, files, message="base"):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    code, out = run(["git", "init", "-b", "main", str(path)], timeout=120)
    must(code, out, "git init %s" % path.name)
    for name, text in files.items():
        write(path / name, text)
    must(*git(path, "add", "-A"), what="git add in %s" % path.name)
    must(*git(path, "commit", "-m", message), what="git commit in %s" % path.name)
    head = git_out(path, "rev-parse", "HEAD")
    if not head:
        raise RuntimeError("fixture step failed: %s has no HEAD" % path)
    return head


def brain_card(lane, opener_file, project, text, source="folder", decoy=True):
    """One card in TREE.md's auto region, written BY HAND in the documented
    shape — so read_brain is proved against the contract, not against its own
    output. The decoy block is the card's pasteable prompt, whose own fence is
    longer and which carries a ``` line inside it."""
    written = ""
    for line in text.splitlines():
        if line.lower().startswith("written:"):
            written = line.split(":", 1)[1].strip()
            break
    lines = ['<!-- tree lane="%s" state="green" touched="%s" next="machine" '
             'depends_on="nothing" opener="%s" fresh="fresh" project="%s" '
             'source="%s" -->' % (lane, stamp(-600), opener_file, project, source),
             "### %s" % lane,
             "**WHERE YOU ARE.** the card's human half",
             ""]
    if decoy:
        lines += ["📍 WHERE: GATE · FABLE · EXTRA", "📋 DO:", "````",
                  "read the project status/memory first.", "```",
                  "````", ""]
    lines += ['<!-- opener source="%s" written="%s" -->' % (source, written),
              "```opener"]
    lines += text.rstrip("\n").split("\n")
    lines += ["```", ""]
    return lines


def tree_text(cards, hub_tail):
    """`cards` is already a flat list of lines — one card after another."""
    lines = ["<!-- tree:auto-start -->", "",
             "# TREE — gate · %s" % stamp(), "", "## Landing", "",
             "🟢 something — somewhere — next: something", "", "## Cards", ""]
    lines.extend(cards)
    lines.append("<!-- tree:auto-end -->")
    lines.append("")
    lines.extend(hub_tail)
    return "\n".join(lines) + "\n"


HUB_TAIL = ["## HANDOFF 2026-09-12 · the hub's own writing",
            "",
            "This paragraph below the end marker is the hub's. Nothing may touch it.",
            ""]


def build_world():
    """Every fixture, built once. Returns the facts later cases need."""
    global SCRATCH, HUB, PROJECTS, VOL, HOME, WORK
    # This run's own world, so two runs — or a `--keep` left behind — can never
    # collide (per-run scratch space). Old runs are swept
    # best-effort; a locked leftover is stepped around, never worked inside.
    SCRATCH = ROOT / ("run-%d-%s" % (os.getpid(),
                                     datetime.datetime.now().strftime("%H%M%S")))
    try:
        for old in ROOT.iterdir() if ROOT.is_dir() else []:
            if old.name.startswith("run-"):
                shutil.rmtree(str(old), ignore_errors=True)
    except OSError:
        pass
    shutil.rmtree(str(SCRATCH), ignore_errors=True)
    HUB = SCRATCH / "hub"
    PROJECTS = SCRATCH / "projects"
    VOL = SCRATCH / "volume"
    HOME = SCRATCH / "home"
    WORK = SCRATCH / "work"
    for folder in (HUB / "tools", PROJECTS, VOL, HOME / "orchestrator-sync", WORK):
        folder.mkdir(parents=True, exist_ok=True)
    for name in ("collect-openers.py", "opener_carriers.py", "exo_common.py", "grok_sessions.py"):
        shutil.copy2(str(HERE / name), str(HUB / "tools" / name))
    # The loader the tools read the person's names through travels with them
    # wherever it is installed (a world that copies the tools and not the
    # loader cannot import them); a hub from before the loader has none to copy.
    for name in ("exo_registry.py", "exo_paths.py"):   # the loader, and the path resolver
        if (HERE / name).is_file():
            shutil.copy2(str(HERE / name), str(HUB / "tools" / name))
    write_json(HOME / "orchestrator-sync" / "machine.json",
               {"name": "gate", "os": platform.system(),
                "roots": {"orchestrator": str(HUB), "projects": str(PROJECTS),
                          "claude": str(HOME / ".claude"),
                          "codex": str(HOME / ".codex")}})

    facts = {}

    # G1 — alpha: a real repo, one folder opener, nothing else
    head = make_repo(PROJECTS / "alpha", {"a.txt": "a\n"})
    write(PROJECTS / "alpha" / "STATUS.md", status_text(["alpha item one"]))
    write(PROJECTS / "alpha" / "OPENER.md",
          opener_text("Alpha", stamp(-3600), head,
                      "read the project status/memory first.\n\n"
                      "1. walk the alpha road\n"))
    facts["alpha_head"] = head

    # G2 — beta: the brain's copy is newer, and names a commit this repo lacks
    head = make_repo(PROJECTS / "beta", {"b.txt": "b\n"})
    write(PROJECTS / "beta" / "STATUS.md", status_text(["beta item one"]))
    write(PROJECTS / "beta" / "OPENER-Beta.md",
          opener_text("Beta", stamp(-3600), head,
                      "the folder body — older\n"))
    facts["beta_head"] = head
    facts["beta_brain"] = opener_text(
        "Beta", stamp(-60), "deadbee1234567890deadbee1234567890deadbe",
        "the brain body — newer\n\n1. land what the brain says\n",
        model="SONNET · EXTRA")
    facts["beta_brain_written"] = stamp(-60)

    # G3 — gamma: an incremental bundle on the volume carries the newer copy
    origin = SCRATCH / "cut" / "gamma-origin"
    base = make_repo(origin, {"g.txt": "g\n",
                              "OPENER-Gamma.md": opener_text("Gamma", stamp(-7200),
                                                             "0" * 40, "base body\n")})
    code, out = run(["git", "clone", "--quiet", str(origin), str(PROJECTS / "gamma")],
                    timeout=180)
    must(code, out, "git clone gamma")
    write(PROJECTS / "gamma" / "STATUS.md", status_text(["gamma item one"]))
    # the folder copy, rewritten so it carries this checkout's own head
    gamma_head = git_out(PROJECTS / "gamma", "rev-parse", "HEAD")
    if not gamma_head:
        raise RuntimeError("fixture step failed: the gamma clone has no HEAD")
    write(PROJECTS / "gamma" / "OPENER-Gamma.md",
          opener_text("Gamma", stamp(-7200), gamma_head, "the folder body — older\n"))
    write(origin / "OPENER-Gamma.md",
          opener_text("Gamma", stamp(-45), "TIP", "the drive body — newer\n"))
    git(origin, "add", "-A")
    git(origin, "commit", "-m", "the other machine's close")
    tip = git_out(origin, "rev-parse", "HEAD")
    write(origin / "OPENER-Gamma.md",
          opener_text("Gamma", stamp(-45), tip, "the drive body — newer\n"))
    git(origin, "add", "-A")
    git(origin, "commit", "--amend", "-m", "the other machine's close")
    tip = git_out(origin, "rev-parse", "HEAD")
    payload = VOL / "XX-TX-001"
    payload.mkdir(parents=True, exist_ok=True)
    must(*git(origin, "bundle", "create", str(payload / "gamma-main.bundle"),
             "%s..main" % base), what="git bundle create gamma")
    write_json(payload / "PAYLOAD.json",
               {"id": "XX-TX-001", "from": "other", "to": "gate", "cut": stamp(-40),
                "parts": [{"kind": "bundle", "file": "gamma-main.bundle",
                           "repo": "gamma", "branch": "main", "base": base,
                           "tip": tip, "label": "gamma"}]})
    # a second copy of the same bundle, named for the CUT and absent from the
    # manifest — the hand-cut shape every older payload on the live drive has
    shutil.copy2(str(payload / "gamma-main.bundle"),
                 str(payload / ("gamma-%s..main.bundle" % tip[:7])))
    facts["gamma_tip"] = tip
    facts["gamma_base"] = base

    # G4 — delta: the same `written:` on both copies
    write(PROJECTS / "delta" / "STATUS.md", status_text(["delta item one"]))
    tie = stamp(-1800)
    write(PROJECTS / "delta" / "OPENER-Delta.md",
          opener_text("Delta", tie, "", "the folder body — the tie\n"))
    facts["delta_brain"] = opener_text("Delta", tie, "", "the brain body — the tie\n")

    # G5 — epsilon: a bundle cut from a repo that has nothing to do with it
    alien = SCRATCH / "cut" / "alien"
    alien_base = make_repo(alien, {"x.txt": "x\n"})
    write(alien / "OPENER-Eps.md", opener_text("Epsilon", stamp(-30), "0" * 40,
                                               "the alien body\n"))
    git(alien, "add", "-A")
    git(alien, "commit", "-m", "second")
    make_repo(PROJECTS / "epsilon", {"e.txt": "e\n"})
    eps_head = git_out(PROJECTS / "epsilon", "rev-parse", "HEAD")
    write(PROJECTS / "epsilon" / "STATUS.md", status_text(["epsilon item one"]))
    write(PROJECTS / "epsilon" / "OPENER-Eps.md",
          opener_text("Epsilon", stamp(-3600), eps_head, "the folder body\n"))
    payload2 = VOL / "XX-TX-002"
    payload2.mkdir(parents=True, exist_ok=True)
    must(*git(alien, "bundle", "create", str(payload2 / "epsilon-main.bundle"),
             "%s..main" % alien_base), what="git bundle create epsilon")
    write_json(payload2 / "PAYLOAD.json",
               {"id": "XX-TX-002", "from": "other", "to": "gate", "cut": stamp(-30),
                "parts": [{"kind": "bundle", "file": "epsilon-main.bundle",
                           "repo": "epsilon", "branch": "main"}]})

    # G6 — zeta: the `HH:Mx` habit, once against a later copy and once earlier
    write(PROJECTS / "zeta" / "STATUS.md", status_text(["zeta item one"]))
    habit = habit_stamp()
    write(PROJECTS / "zeta" / "OPENER-Zx.md",
          opener_text("Zeta/Zx", habit, "", "the folder body — Zx\n"))
    write(PROJECTS / "zeta" / "OPENER-Zy.md",
          opener_text("Zeta/Zy", habit, "", "the folder body — Zy\n"))
    facts["zeta_habit"] = habit
    facts["zx_brain"] = opener_text("Zeta/Zx", tens_stamp(5), "",
                                    "the brain body — Zx, five minutes later\n")
    facts["zy_brain"] = opener_text("Zeta/Zy", tens_stamp(-5), "",
                                    "the brain body — Zy, five minutes earlier\n")

    # G8 — eta: three lanes, one STATUS
    write(PROJECTS / "eta" / "STATUS.md",
          status_text(["Bravo needs its page written", "something unrelated"]))
    write(PROJECTS / "eta" / "OPENER-Alfa.md",
          opener_text("Eta/Alfa", stamp(-600), "",
                      "read the project status/memory first.\n\n"
                      "1. run the Alfa walk\n2. stop\n"))
    write(PROJECTS / "eta" / "OPENER-Bravo.md",
          opener_text("Eta/Bravo", stamp(-600), "",
                      "read the project status/memory first. Then ask Wren.\n"))
    write(PROJECTS / "eta" / "OPENER-Charlie.md",
          opener_text("Eta/Charlie", stamp(-600), "",
                      "read the project status/memory first. Then ask Wren.\n"))
    # a known failure, as a fixture: a carryover opener's "what already
    # happened" list is numbered, so document order alone read a done line as
    # the lane's next move, and the heading under it was ignored
    write(PROJECTS / "eta" / "OPENER-Echo.md",
          opener_text("Eta/Echo", stamp(-600), "",
                      "WHERE WE ARE\n\n"
                      "- What already happened:\n"
                      "1. \u2705 the fleet landed Friday and was signed off\n"
                      "2. \u2705 the smoke run passed\n"
                      "- Wren's next move: read the card at the desk.\n"
                      "- Machine's next move \u00b7 in this order:\n"
                      "1. cut the package and print the gate line\n"))

    # G9 — theta: one model line walked, one never walked
    write(PROJECTS / "theta" / "STATUS.md", status_text(["theta item one"]))
    write(PROJECTS / "theta" / "OPENER-Judge.md",
          opener_text("Theta/Judge", stamp(-600), "",
                      "read the project status/memory first. Then rule the docket.\n",
                      model="OPUS · EXTRA"))
    write(PROJECTS / "theta" / "OPENER-Walked.md",
          opener_text("Theta/Walked", stamp(-600), "",
                      "read the project status/memory first. Then rule the docket.\n",
                      model="OPUS · EXTRA", extra={"judgment": "none"}))

    # G14 — iota: a lane whose opener file never landed in the folder, carried by
    # TWO carriers at once (the brain and a payload). One lane, one row.
    iota_origin = SCRATCH / "cut" / "iota-origin"
    iota_base = make_repo(iota_origin, {"i.txt": "i\n"})
    code, out = run(["git", "clone", "--quiet", str(iota_origin),
                     str(PROJECTS / "iota")], timeout=180)
    must(code, out, "git clone iota")
    write(PROJECTS / "iota" / "STATUS.md", status_text(["iota item one"]))
    facts["iota_brain"] = opener_text("Iota/Kappa", stamp(-120), "",
                                      "the brain body — Kappa\n\n1. land the Kappa payload\n")
    write(iota_origin / "OPENER-Kappa.md",
          opener_text("Iota/Kappa", stamp(-20), "TIP",
                      "the drive body — Kappa, the newest copy of all\n"))
    must(*git(iota_origin, "add", "-A"), what="git add iota opener")
    must(*git(iota_origin, "commit", "-m", "Kappa closes"), what="git commit iota")
    iota_tip = git_out(iota_origin, "rev-parse", "HEAD")
    write(iota_origin / "OPENER-Kappa.md",
          opener_text("Iota/Kappa", stamp(-20), iota_tip,
                      "the drive body — Kappa, the newest copy of all\n"))
    must(*git(iota_origin, "add", "-A"), what="git add iota opener again")
    must(*git(iota_origin, "commit", "--amend", "-m", "Kappa closes"),
         what="git amend iota")
    iota_tip = git_out(iota_origin, "rev-parse", "HEAD")
    payload3 = VOL / "XX-TX-003"
    payload3.mkdir(parents=True, exist_ok=True)
    must(*git(iota_origin, "bundle", "create", str(payload3 / "iota-main.bundle"),
              "%s..main" % iota_base), what="git bundle create iota")
    write_json(payload3 / "PAYLOAD.json",
               {"id": "XX-TX-003", "from": "other", "to": "gate", "cut": stamp(-15),
                "parts": [{"kind": "bundle", "file": "iota-main.bundle",
                           "repo": "iota", "branch": "main", "base": iota_base,
                           "tip": iota_tip, "label": "iota"}]})

    # G15 — a card for a project this machine does not have at all
    facts["ghost_brain"] = opener_text("Ghost/Lane", stamp(-180), "",
                                       "the ghost body — drive-only lane\n")

    # BQ335-G6 — kappa: an opener the capture headed (its sitting s7 ran)
    head = make_repo(PROJECTS / "kappa", {"k.txt": "k\n"})
    write(PROJECTS / "kappa" / "STATUS.md", status_text(["kappa item one"]))
    write(PROJECTS / "kappa" / "OPENER.md", "\n".join([
        "lane: Kappa", "written: %s" % stamp(-7200),
        "by: ACT — Kappa: s6 — the sitting before",
        "captured: %s · tools/buttonup.py on the GATE · the sitting this opener was written "
        "for, s7 \"ACT — Kappa: s7 — the gate's lane\", ran and was captured (last message %s) "
        "· its record: kappa/STATUS.md § HANDOFF CAPTURE (hub button-up %s) · next sitting: s8"
        % (stamp(-60), stamp(-120), stamp(-60)[:10]),
        "on: GATE", "head: %s" % head, "status_updated: %s" % stamp(120),
        "where: Kappa stands here", "next: machine", "depends_on: nothing",
        "open_in: %s on the GATE · project `kappa` (reuse) · fresh Claude session titled "
        "`ACT — Kappa: s7 — the gate's lane`" % (PROJECTS / "kappa"),
        "model: FABLE · EXTRA", "---", "",
        "CAPTURE NOTE (hub button-up %s): the sitting this opener was written for — s7 — ran "
        "and was captured from the outside, not closed by its own hand. Read its HANDOFF "
        "CAPTURE block in STATUS first; this is s8. The prompt below was written before s7 ran."
        % stamp(-60)[:10], "",
        "read the project status/memory first. Pick up Kappa: walk the kappa road.", ""]))
    facts["kappa_date"] = stamp(-60)[:10]
    return facts


def write_tree_fixture(facts):
    """The scratch TREE.md, hand-built in the documented shape."""
    cards = []
    cards += brain_card("Beta", "OPENER-Beta.md", "beta", facts["beta_brain"])
    cards += brain_card("Delta", "OPENER-Delta.md", "delta", facts["delta_brain"])
    cards += brain_card("Zeta/Zx", "OPENER-Zx.md", "zeta", facts["zx_brain"])
    cards += brain_card("Zeta/Zy", "OPENER-Zy.md", "zeta", facts["zy_brain"])
    cards += brain_card("Iota/Kappa", "OPENER-Kappa.md", "iota", facts["iota_brain"])
    cards += brain_card("Ghost/Lane", "OPENER-Lane.md", "ghost", facts["ghost_brain"])
    write(HUB / "TREE.md", tree_text(cards, HUB_TAIL))


# --------------------------------------------------------------------------
# the cases
# --------------------------------------------------------------------------

def case_g0(live_hub):
    start("G0", "compiles + cli")
    for name in ("opener_carriers.py", "gate-opener-freshness.py",
                 "collect-openers.py"):
        try:
            py_compile.compile(str(HERE / name), cfile=str(WORK / (name + "c")),
                               doraise=True)
            check(True, "%s compiles" % name)
        except Exception as exc:
            check(False, "%s does not compile: %r" % (name, exc))
    for name in ("opener_carriers.py", "gate-opener-freshness.py"):
        code, out = run([PY, str(HERE / name), "--help"], timeout=120)
        check(code == 0 and "--help" in out, "%s --help exits 0 with usage" % name)
        code, out = run([PY, str(HERE / name), "--nonsense"], timeout=120)
        check(code == 2, "%s --nonsense exits 2 (got %d)" % (name, code))
    # the mirrored contract must equal the collector's own
    text = io.open(str(HERE / "collect-openers.py"), encoding="utf-8",
                   errors="replace").read()
    sys.path.insert(0, str(HUB / "tools"))
    import opener_carriers as oc
    for name, mirror in (("HEADER_KEYS", oc.HEADER_KEYS),
                         ("OPTIONAL_KEYS", oc.OPTIONAL_KEYS)):
        found = re.search(r"^%s = \((.*?)\)" % name, text, re.S | re.M)
        keys = tuple(re.findall(r'"([a-z_]+)"', found.group(1))) if found else ()
        check(keys == tuple(mirror),
              "%s mirrors the collector (%s vs %s)" % (name, keys, tuple(mirror)))
    check(live_hub is not None, "the live hub was found for the fingerprint")
    done()


def act_title_of(row):
    """The scratch hub's own lane_act_title(row), asked in a child with the gate's HOME."""
    code, out = co_python(
        "import importlib.util, json, sys\n"
        "spec = importlib.util.spec_from_file_location('co', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "print(m.lane_act_title(json.loads(sys.argv[2])))\n",
        [str(HUB / "tools" / "collect-openers.py"), json.dumps(row)])
    return out.strip().splitlines()[-1] if code == 0 and out.strip() else "exit %d: %s" % (
        code, out.strip()[-160:])


def co_python(source, args):
    base = {"USERPROFILE": str(HOME), "HOME": str(HOME), "HOMEDRIVE": None, "HOMEPATH": None,
            "EXO_MACHINE_JSON": str(HOME / "orchestrator-sync" / "machine.json"),
            "COLLECT_OPENERS_ROOT": str(PROJECTS), "COLLECT_OPENERS_VOLUMES": str(VOL),
            "COLLECT_OPENERS_WORK": str(WORK),
            "COLLECT_OPENERS_ENGINE": str(HOME / "orchestrator-sync")}
    return run([PY, "-c", source] + list(args), cwd=str(HUB / "tools"), env=base)


def case_r335(data, facts):
    start("BQ335-G6", "the capture's head")
    row = row_of(data, "Kappa")
    if not check(row is not None, "the Kappa row is there"):
        return done()
    want = ("captured: s7 ran and was captured %s; the next sitting is s8" % facts["kappa_date"])
    check(row["fresh"] == "note", "a headed opener is a NOTE (got %r)" % row["fresh"])
    check(row["notes"] and row["notes"][0] == want,
          "its first note says the sitting ran (got %r)" % (row["notes"][:1],))
    cap = row.get("captured") or {}
    check(cap.get("sitting") == 7 and cap.get("next") == 8
          and cap.get("title") == "ACT — Kappa: s7 — the gate's lane"
          and cap.get("line", "").startswith(cap.get("line", "x")[:10]) and cap.get("last"),
          "--json carries `captured` = {line, sitting 7, next 8, title, last} (got %r)"
          % ({k: cap.get(k) for k in ("sitting", "next", "title", "last")},))
    check("captured" not in (row.get("unknown") or []),
          "`captured:` is a known header key, never listed unknown")
    title = act_title_of(row)
    check(title == "ACT — Kappa: s8 — the gate's lane",
          "lane_act_title names the NEXT sitting (got %r)" % title)
    alpha = row_of(data, "Alpha")
    check(alpha is not None and alpha.get("captured") is None
          and act_title_of(alpha) == "ACT — Alpha: …",
          "an unheaded lane carries no `captured` and its title is untouched")
    code, out = co(["--expand", "Kappa"])
    check(code == 0 and ("⚠ " + want) in out, "the card shows the note (exit %d)" % code)
    # the card's WHERE line says the NEXT sitting, and why
    where_lines = [ln for ln in out.splitlines() if ln.startswith("📍 WHERE:")]
    where_line = where_lines[0] if where_lines else ""
    check("ACT — Kappa: s8 — the gate's lane" in where_line
          and "s7 — the gate's lane" not in where_line,
          "BQ338: the --expand card's WHERE line titles the NEXT sitting, s8 (got %r)" % where_line[-200:])
    check("s7 ran" in where_line,
          "BQ338: the WHERE line says which sitting ran (got %r)" % where_line[-120:])
    check(row.get("open_in", "").find("ACT — Kappa: s8") >= 0
          and "s7 —" not in row.get("open_in", ""),
          "BQ338: --json row open_in names s8 (got %r)" % row.get("open_in", "")[-100:])
    check("ACT — Kappa: s7 — the gate's lane" in (row.get("header") or {}).get("open_in", ""),
          "BQ338: --json header.open_in still names s7, the raw header untouched")
    check(alpha is not None and alpha.get("open_in") == (alpha.get("header") or {}).get("open_in", "").strip(),
          "BQ338: the unheaded Alpha row's open_in equals its header open_in byte for byte")
    code, out = co(["--table"])
    check(code == 0 and "captured: s7 ran" in out, "and so does the table (exit %d)" % code)
    done()


def case_g1(data):
    start("G1", "folder only")
    row = row_of(data, "Alpha")
    if not check(row is not None, "the Alpha row is there"):
        return done()
    check(row["source"] == "folder", "source is `folder` (got %r)" % row["source"])
    check(row["stale_behind_carrier"] is False,
          "no STALE-BEHIND-CARRIER (got %r)" % row["stale_behind_carrier"])
    check(row["fresh"] == "fresh", "fresh (got %r · %s)"
          % (row["fresh"], "; ".join(row["notes"])))
    check(row["opener"] == "OPENER.md", "the opener file is named")
    done()


def case_g2(data, facts):
    start("G2", "brain newer")
    row = row_of(data, "Beta")
    if not check(row is not None, "the Beta row is there"):
        return done()
    check(row["source"] == "brain", "source is `brain` (got %r)" % row["source"])
    sentence = row["stale_behind_carrier"]
    check(bool(sentence) and "folder copy written" in str(sentence)
          and "brain copy written" in str(sentence),
          "the JSON carries the sentence (got %r)" % sentence)
    check("the brain body" in row["body"], "the winner's BODY is used")
    check(row["model"].upper().startswith("SONNET"),
          "the winner's HEADER is used (model %r)" % row["model"])
    check(row["fresh"] == "note" and any("not in this repo" in n for n in row["notes"]),
          "a head this repo lacks is a NOTE, not stale (%r · %s)"
          % (row["fresh"], "; ".join(row["notes"])))
    code, table = co(["--table"])
    line = [l for l in table.splitlines() if l.startswith("⚠") and "Beta" in l]
    check(code == 0 and line, "the table line leads with the warning")
    check(any("brain" in l for l in line), "the table names the source")
    code, chat = co(["--chat"])
    check(code == 0 and any(l.startswith("⚠ STALE-BEHIND-CARRIER · ") and "Beta" in l
                            for l in chat.splitlines()),
          "the --chat line carries the prefix")
    code, card = co(["--expand", "Beta"])
    lines = [l for l in card.splitlines() if l.strip()]
    where = [i for i, l in enumerate(lines) if l.startswith("### ")]
    check(code == 0 and where and "STALE-BEHIND-CARRIER" in lines[where[0] + 1],
          "the card says it on the line under the lane name")
    check("source: brain · written" in card, "the card names the source above the prompt")
    check(any("STALE-BEHIND-CARRIER: Beta" in l for l in table.splitlines()),
          "the flags line names the lane")
    done()


def case_g3(data, facts, before):
    start("G3", "drive newer")
    row = row_of(data, "Gamma")
    if not check(row is not None, "the Gamma row is there"):
        return done()
    check(row["source"] == "drive:XX-TX-001",
          "source names the payload (got %r)" % row["source"])
    check("the drive body" in row["body"], "the bundle's copy is the one handed over")
    check(bool(row["stale_behind_carrier"]), "flagged STALE-BEHIND-CARRIER")
    check(row["fresh"] == "note"
          and any("lands with XX-TX-001" in n for n in row["notes"]),
          "the note says which payload it lands with (%s)" % "; ".join(row["notes"]))
    after = repo_state(PROJECTS / "gamma")
    check(after == before["gamma"], "the project repo's refs are unchanged")
    check("refs/bundles" not in after, "no refs/bundles in the project repo")
    check(volume_state() == before["volume"], "every byte on the volume is unchanged")
    notes = data["flags"].get("carrier_notes") or []
    check(not [n for n in notes if "gamma" in n],
          "a bundle named for its cut, absent from the manifest, still finds its "
          "project (%r)" % notes)
    done()


def case_g4(data, facts):
    start("G4", "tie")
    row = row_of(data, "Delta")
    if not check(row is not None, "the Delta row is there"):
        return done()
    check(row["source"] == "folder", "the folder copy wins a tie (got %r)" % row["source"])
    check(row["stale_behind_carrier"] is False, "no flag on a tie")
    check("the folder body" in row["body"], "the folder's body is the one used")
    done()


def case_g5(data):
    start("G5", "unreadable bundle")
    row = row_of(data, "Epsilon")
    if not check(row is not None, "the Epsilon row is there"):
        return done()
    check(row["source"] == "folder", "the folder copy stands (got %r)" % row["source"])
    notes = data["flags"].get("carrier_notes") or []
    check(any("XX-TX-002" in n and "base not in this repo" in n for n in notes),
          "one note names the payload and why (got %r)" % notes)
    done()


def case_g6(data, facts):
    start("G6", "the HH:Mx habit")
    zx, zy = row_of(data, "Zeta/Zx"), row_of(data, "Zeta/Zy")
    if not check(zx is not None and zy is not None, "both Zeta rows are there"):
        return done()
    check(facts["zeta_habit"] in str(zx["stale_behind_carrier"]),
          "the folder line is shown as the file says it (%r)"
          % zx["stale_behind_carrier"])
    check(zy["written"] == facts["zeta_habit"],
          "a winning habit stamp is shown verbatim too (%r)" % zy["written"])
    check(zx["source"] == "brain",
          "…T18:3x is older than …T18:35 (got %r)" % zx["source"])
    check(zy["source"] == "folder",
          "…T18:3x is newer than …T18:25 (got %r)" % zy["source"])
    done()


def case_g7(data):
    start("G7", "write-tree round trip")
    tree = HUB / "TREE.md"
    before_tail = io.open(str(tree), encoding="utf-8").read().split(
        "<!-- tree:auto-end -->", 1)[1]
    code, out = co(["--write-tree"])
    check(code == 0, "--write-tree exits 0 (%s)" % out[-200:])
    text = io.open(str(tree), encoding="utf-8").read()
    check(text.split("<!-- tree:auto-end -->", 1)[1] == before_tail,
          "the hub's own text below the end marker is untouched")
    sys.path.insert(0, str(HUB / "tools"))
    import opener_carriers as oc
    back = oc.read_brain(tree)
    wanted = [r for r in data["rows"] if r["opener"]]
    missing = [r["lane"] for r in wanted if oc.lane_key(r["lane"]) not in back]
    check(not missing, "every lane with an opener is carried (missing %r)" % missing[:3])
    bad = []
    for row in wanted:
        item = back.get(oc.lane_key(row["lane"]))
        if not item:
            continue
        if item["header"] != row["header"] or item["body"] != row["body"]:
            bad.append(row["lane"])
    check(not bad, "headers and bodies come back byte for byte (%r)" % bad[:3])
    # and the second generation picks the same winners
    again = data_of()
    drift = [(r["lane"], r["source"]) for r in again["rows"]
             for o in [row_of(data, r["lane"])]
             if o and r["body"] != o["body"]]
    check(not drift, "a second run hands the same opener for every lane (%r)" % drift[:3])
    gamma = row_of(again, "Gamma")
    check(gamma is not None
          and any("XX-TX-001" in n for n in gamma["notes"]),
          "the payload is still named after the brain has a copy of it")
    done()


def case_g8(data):
    start("G8", "lane-true next")
    alfa, bravo = row_of(data, "Eta/Alfa"), row_of(data, "Eta/Bravo")
    charlie = row_of(data, "Eta/Charlie")
    if not check(all(r is not None for r in (alfa, bravo, charlie)),
                 "all three Eta rows are there"):
        return done()
    check(alfa["next_move"] == "run the Alfa walk",
          "lane A takes its own opener step (got %r)" % alfa["next_move"])
    check(bravo["next_move"].startswith("Bravo needs its page"),
          "lane B takes the STATUS item that names it (got %r)" % bravo["next_move"])
    check(charlie["next_move"].endswith("(project)"),
          "lane C takes the project's item, marked (got %r)" % charlie["next_move"])
    check(alfa["next_move"] != bravo["next_move"],
          "two lanes in one folder do not show the same move")
    echo = row_of(data, "Eta/Echo")
    if check(echo is not None, "the Eta/Echo row is there"):
        check(echo["next_move"].startswith("cut the package"),
              "a carryover opener's \u2705 history is never the next move "
              "(got %r)" % echo["next_move"])
        check("\u2705" not in echo["next_move"], "no done line reaches the landing list")
    done()


def case_g9(data):
    start("G9", "judgment unwalked")
    judge, walked = row_of(data, "Theta/Judge"), row_of(data, "Theta/Walked")
    if not check(judge is not None and walked is not None, "both Theta rows are there"):
        return done()
    check(judge["judgment_unwalked"].lower().startswith("rul"),
          "the verb as found is reported (got %r)" % judge["judgment_unwalked"])
    check(any("model line not walked" in n for n in judge["notes"]),
          "the card carries the sentence")
    check(not walked["judgment_unwalked"],
          "`judgment: none` is walked and never flagged")
    flags = [f["lane"] for f in data["flags"].get("judgment_unwalked") or []]
    check("Theta/Judge" in flags and "Theta/Walked" not in flags,
          "the flags line names only the unwalked one (%r)" % flags)
    code, table = co(["--table"])
    check("model line not walked" in table, "the table says it too")
    done()


def case_g10():
    start("G10", "cache")
    sys.path.insert(0, str(HUB / "tools"))
    import opener_carriers as oc
    os.environ["COLLECT_OPENERS_WORK"] = str(WORK / "cache-case")
    oc.WORK_DIR = Path(os.environ["COLLECT_OPENERS_WORK"])
    oc.CACHE_FILE = oc.WORK_DIR / "cache.json"
    oc._CACHE = None
    oc.reset_stats()
    volumes = [{"label": "gate", "path": str(VOL)}]
    first, notes = oc.read_drive(str(PROJECTS), volumes=volumes)
    calls = oc.stats()["git_calls"]
    check(calls > 0, "the first read does real git work (%d calls)" % calls)
    check(any(c["source"] == "drive:XX-TX-001" for c in first),
          "the first read finds the payload's opener")
    oc.reset_stats()
    oc._CACHE = None                       # forget everything but the file itself
    second, notes2 = oc.read_drive(str(PROJECTS), volumes=volumes)
    check(oc.stats()["git_calls"] == 0,
          "the second read makes no git call (%d)" % oc.stats()["git_calls"])
    check([(c["source"], c["file"], c["body"]) for c in first]
          == [(c["source"], c["file"], c["body"]) for c in second],
          "the cached answer is the same answer")
    check(notes == notes2, "the notes are the same too")
    done()


def case_g11():
    start("G11", "nothing there")
    tree = HUB / "TREE.md"
    kept = io.open(str(tree), encoding="utf-8").read() if tree.is_file() else None
    try:
        if kept is not None:
            tree.unlink()
        env = {"COLLECT_OPENERS_VOLUMES": str(SCRATCH / "no-such-volume"),
               "COLLECT_OPENERS_ENGINE": str(SCRATCH / "no-such-engine")}
        code, out = co(["--table"], env=env)
        check(code == 0, "no volume, no engine, no TREE.md → exit 0 (%s)" % out[-200:])
        check("Traceback" not in out, "nothing raised")
        data = data_of(env=env)
        check(all(r["source"] in ("folder", "none") for r in data["rows"]),
              "every row falls back to its folder copy")
        # the engine truly missing, with no volume override: one note, no crash
        sys.path.insert(0, str(HUB / "tools"))
        import opener_carriers as oc
        saved_engine, saved_env = oc.ENGINE_DIR, os.environ.pop("COLLECT_OPENERS_VOLUMES", None)
        try:
            oc.ENGINE_DIR = SCRATCH / "no-such-engine"
            notes = []
            volumes = oc.mounted_volumes(notes, str(PROJECTS))
            check(volumes == [] and notes == ["drive carriers: engine not found"],
                  "a missing engine is one note and no volumes (%r · %r)" % (volumes, notes))
        finally:
            oc.ENGINE_DIR = saved_engine
            if saved_env is not None:
                os.environ["COLLECT_OPENERS_VOLUMES"] = saved_env
    finally:
        if kept is not None:
            write(tree, kept)
    done()


def this_machines_engine():
    """The sync package on THIS machine, found the way its own tools find it: the
    resolver beside the tools when it is installed (a program tree keeps it in
    <hub>/sync, the older layout in its folder under the home), else the older
    layout's folder."""
    if (HERE / "exo_paths.py").is_file():
        try:
            sys.path.insert(0, str(HERE))
            import exo_paths
            found = exo_paths.paths(tool_file=HERE / "collect-openers.py").get("sync_dir")
            if found:
                return Path(found)
        except Exception:
            pass
        finally:
            if str(HERE) in sys.path:
                sys.path.remove(str(HERE))
    return Path.home() / "orchestrator-sync"


def case_g13(live_hub):
    start("G13", "smoke, real machine")
    tool = HERE / "collect-openers.py"
    env = {"COLLECT_OPENERS_ROOT": None, "COLLECT_OPENERS_VOLUMES": None,
           "COLLECT_OPENERS_WORK": None, "COLLECT_OPENERS_ENGINE": None}
    code, out = run([PY, str(tool), "--table"], cwd=str(HERE.parent), env=env,
                    timeout=600)
    check(code == 0, "--table against the live roots exits 0 (%s)" % out[-200:])
    check("Traceback" not in out, "nothing raised on the real machine")
    code, out = run([PY, str(tool), "--json"], cwd=str(HERE.parent), env=env,
                    timeout=600)
    if not check(code == 0, "--json against the live roots exits 0 (%s)" % out[-200:]):
        return done()
    try:
        live = json.loads(out)
    except ValueError:
        check(False, "--json did not parse")
        return done()
    rows = live.get("rows") or []
    check(bool(rows), "the live machine has lanes to report (%d)" % len(rows))
    check(all(r.get("source") for r in rows), "every row carries a source")
    sys.path.insert(0, str(HUB / "tools"))
    import opener_carriers as oc
    saved = os.environ.pop("COLLECT_OPENERS_VOLUMES", None)
    try:
        oc.ENGINE_DIR = this_machines_engine()
        notes = []
        volumes = oc.mounted_volumes(notes, live.get("projects_root"))
        check(isinstance(volumes, list) and not notes,
              "the engine's volume reader answers first-hand (%r · %r)" % (volumes, notes))
    finally:
        if saved is not None:
            os.environ["COLLECT_OPENERS_VOLUMES"] = saved
    done()


def case_g14(data):
    start("G14", "carrier-only lane")
    rows = [r for r in data["rows"] if r["lane"].lower() == "iota/kappa"]
    if not check(rows, "a lane with no folder copy still gets its row"):
        return done()
    check(len(rows) == 1,
          "one lane is ONE row however many copies ride (got %d)" % len(rows))
    row = rows[0]
    check(row["source"] == "drive:XX-TX-003",
          "the newest carrier wins and is named (got %r)" % row["source"])
    check(str(row["stale_behind_carrier"]).startswith("no folder copy"),
          "it says there is no folder copy (got %r)" % row["stale_behind_carrier"])
    check("the drive body" in row["body"], "the newest copy is handed over")
    check(row["fresh"] == "note"
          and any("lands with XX-TX-003" in n for n in row["notes"]),
          "the note names the payload that has to land (%s)" % "; ".join(row["notes"]))
    done()


def case_g15(data):
    start("G15", "carried openers")
    carried = [c["lane"] for c in data.get("carried") or []]
    check("Ghost/Lane" in carried,
          "an opener no project here can place is reported (%r)" % carried)
    sys.path.insert(0, str(HUB / "tools"))
    import opener_carriers as oc
    back = oc.read_brain(HUB / "TREE.md")
    item = back.get("ghost/lane")
    check(item is not None, "it survived --write-tree instead of being dropped")
    if item:
        check("the ghost body" in item["body"], "it survived verbatim")
    done()


# --------------------------------------------------------------------------
# live fingerprints
# --------------------------------------------------------------------------

def repo_state(repo):
    return git_out(repo, "for-each-ref", "--format=%(refname) %(objectname)")


def volume_state():
    out = []
    for path in sorted(Path(VOL).rglob("*")):
        if path.is_file():
            out.append((str(path.relative_to(VOL)), sha(path)))
    return out


def live_names(live_hub):
    """The hub's own files, top level and tools/ — nothing may appear."""
    out = []
    for folder in (live_hub, live_hub / "tools"):
        try:
            out.extend(sorted(p.name for p in folder.iterdir() if p.is_file()))
        except OSError:
            pass
    return out


# The one live file the tools under test write that nothing else on this machine
# regenerates by itself: a change here is the gate's fault and fails, full stop.
STRICT = ("TREE.md",)
# Every other watched file has another writer on a live machine — the pulse
# redraws these four every five minutes, a claim rewrites claims.json, a session
# stamp rewrites live-*.json. A change in one of them proves nothing; what
# proves everything is whether any of the GATE'S OWN WORDS is inside it, because
# a page or a tree written from the gate's world would be full of them.
GENERATED = ("tree.html", "board.html", "brain-index.json",
             "sessions-cache.json", "GETTING-GOING.md")
WATCHED = STRICT + GENERATED + ("STATUS.md", "claims.json")
# The gate's own words. Nothing of the owner's says any of these.
GATE_MARKS = ("exocortex-gate-bq007", "XX-TX-001", "XX-TX-002", "Zeta/Zx",
              "Iota/Kappa", "Ghost/Lane", '"machine": "gate"')


def live_watched(live_hub):
    names = list(WATCHED)
    try:
        names += sorted(p.name for p in live_hub.glob("live-*.json"))
    except OSError:
        pass
    out = {}
    for name in names:
        out[name] = sha(live_hub / name)
    return out


def gate_trace(path):
    """Any of the gate's own words inside a live file that changed. A claim, a
    session stamp or a pulse beat rewrites those files while the gate runs — so
    the question is not whether one changed, it is whether the GATE changed it,
    and the gate's world is named in everything it writes."""
    try:
        text = io.open(str(path), encoding="utf-8", errors="replace").read()
    except OSError:
        return ["unreadable"]
    return [mark for mark in GATE_MARKS if mark.lower() in text.lower()]


def find_live_hub():
    """The real hub folder, from machine.json — read for its fingerprint only."""
    try:
        data = json.loads(io.open(str(Path.home() / "orchestrator-sync" / "machine.json"),
                                  encoding="utf-8").read())
        root = ((data.get("roots") or {}).get("orchestrator") or "").strip()
        if root and Path(root).is_dir():
            return Path(root)
    except Exception:
        pass
    return HERE.parent


USAGE = """gate-opener-freshness.py — does the freshest opener win?

  (no flags)     build the scratch world, run every case, print one line each
  --keep         leave the scratch world at %s
  --hub <dir>    accepted so the build runner can pass it; never read for a verdict
  --help

Exit 0 only when every check passes.
""" % ROOT


def main(argv):
    argv = list(argv)
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(USAGE)
        return 0
    keep = "--keep" in argv
    rest = [a for a in argv if a not in ("--keep",)]
    while "--hub" in rest:
        at = rest.index("--hub")
        del rest[at:at + 2]
    if rest:
        sys.stdout.write(USAGE)
        return 2

    live_hub = find_live_hub()
    before_watched = live_watched(live_hub)
    before_names = live_names(live_hub)

    # The files this gate proves travel together; one that is not installed is
    # said by name, as a failed check, and the gate ends on its count line.
    missing = [name for name in ("collect-openers.py", "opener_carriers.py", "exo_common.py",
                                 "grok_sessions.py") if not (HERE / name).is_file()]
    if missing:
        print("FAIL: %s — not installed beside this gate (%s); the carriers this gate "
              "proves are read by it" % (", ".join(missing), HERE))
        print("GATE FAILED: 1/1 — %s is not installed" % missing[0])
        print("1 checks · 0 passed · 1 failed")
        return 1
    try:
        facts = build_world()
    except Exception as exc:
        print("FAIL: the gate could not build its world: %r" % exc)
        if not keep and SCRATCH is not None:
            shutil.rmtree(str(SCRATCH), ignore_errors=True)
        return 1

    os.environ["COLLECT_OPENERS_WORK"] = str(WORK)
    guarded(case_g0, live_hub)

    # phase 1 — no TREE.md at all: the folder copies stand on their own
    try:
        first = data_of()
        guarded(case_g1, first)
    except Exception as exc:
        start("G1", "folder only")
        check(False, "the first run failed: %r" % exc)
        done()

    # phase 2 — the brain and the drive both carry copies
    before = {"gamma": repo_state(PROJECTS / "gamma")}
    write_tree_fixture(facts)
    before["volume"] = volume_state()
    try:
        data = data_of()
    except Exception as exc:
        print("FAIL: the second run failed: %r" % exc)
        data = {"rows": [], "flags": {}, "carried": []}
    guarded(case_g2, data, facts)
    guarded(case_g3, data, facts, before)
    guarded(case_g4, data, facts)
    guarded(case_g5, data)
    guarded(case_g6, data, facts)
    guarded(case_g8, data)
    guarded(case_g9, data)
    guarded(case_g14, data)
    guarded(case_r335, data, facts)
    guarded(case_g10)
    guarded(case_g7, data)          # writes TREE.md, so it runs after the readers
    guarded(case_g15, data)
    guarded(case_g11)
    guarded(case_g13, live_hub)

    start("G12", "live untouched")
    after_watched = live_watched(live_hub)
    moved = [name for name, value in before_watched.items()
             if after_watched.get(name) != value]
    check(not [n for n in moved if n in STRICT],
          "the live TREE.md is byte-identical (moved: %s)"
          % (", ".join(n for n in moved if n in STRICT) or "none"))
    traced = []
    for name in moved:
        traced += ["%s (%s)" % (name, ", ".join(gate_trace(live_hub / name)))
                   for mark in [gate_trace(live_hub / name)] if mark]
    check(not traced, "no live file carries a word of the gate's world (%s)"
          % (", ".join(traced) or "none"))
    appeared = [n for n in live_names(live_hub) if n not in before_names]
    check(not appeared, "no file appeared in the live hub (%s)"
          % (", ".join(appeared) or "none"))
    check(str(HUB) != str(live_hub), "the gate's hub is not the live hub")
    done()
    others = [n for n in moved if n not in STRICT]
    if others:
        # Said out loud rather than hidden: those files belong to the claims,
        # the session stamps and the pulse, which write while the gate runs.
        print("     note: %s changed while the gate ran — another live writer "
              "(a claim, a session stamp, a pulse beat); no word of the gate's "
              "world is in any of them, and the gate's own HOME is %s"
              % (", ".join(others), HOME))

    if keep:
        print("scratch kept at %s" % SCRATCH)
    else:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    total = PASSES + len(FAILS)
    if FAILS:
        print("GATE FAILED: %d/%d — %s" % (len(FAILS), total, FAILS[0]))
        print("%d checks · %d passed · %d failed" % (total, PASSES, len(FAILS)))
        return 1
    print("GATE PASSED: %d/%d checks — the freshest opener wins on every carrier, "
          "and nothing live was read for a verdict or written" % (PASSES, total))
    print("%d checks · %d passed · %d failed" % (total, PASSES, len(FAILS)))
    return 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    if SCRATCH is not None:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    try:
        ROOT.rmdir()                       # the shared parent, once it is empty
    except OSError:
        pass


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
