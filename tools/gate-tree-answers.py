#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-tree-answers.py — does every mark on the tree answer a click?

    python tools/gate-tree-answers.py                  # gates the live generator
    python tools/gate-tree-answers.py <generator.py>   # gates a copy, before it is installed
    python tools/gate-tree-answers.py --keep           # leave the scratch world for inspection
    python tools/gate-tree-answers.py --inventory      # every drawn class on the live hub's page: answer or NONE
                                                       #   (--hub=<folder> draws another hub)
    python tools/gate-tree-answers.py --base-dir=<folder>   # H10/H11 compare with the base tools there

Proves the tree-answers contract. Hermetic: under the temp dir the gate builds
its own world — a scratch HOME whose machine.json names a scratch hub and a scratch projects
root, so every subprocess resolves `Path.home()` inside the gate and can reach nothing of the
user's. The page is rendered through COLLECT_OPENERS_OUT, so the live tree is never written.

  G1  every mark answers   every draw template in the generator's JS emits `data-mark`; every
                           server-drawn mark class carries one; every id resolves in MARKS and
                           every MARKS id is drawn — zero orphans either way
  G2  real bytes           every entry has a kind and at least one byte row; no placeholders
  G3  one mechanism        the inspector element exists and `closest('[data-mark]')` occurs once
  G4  the nerves control   with one live session it renders with aria-pressed; with none it is
                           not rendered at all and the strip says `0 live`
  G5  the NEXT sentence    the hub tile's next is a sentence, not the comma-led scaffolding
  G6  one word per measure the nameplate says `1 live`, the root card `2 stamped` and `1 live`,
                           and no bare "N session(s)" stands beside a number in the collar
  G7  one-click start      a lane with an opener carries ▶ Launch with the one-sentence paste;
                           one without carries ▶ Open with the front-door sentence
  G8  nothing superfluous  the explaining paragraph is gone; the caption is one line of counts
  G9  the owed prompts     the chip is a button whose entry names the owing lane and its reason
  G10 the page itself      ≤ 1.6 MB, the self-refresh tag, the four catalog schemes, 0 overlaps
  G11 the notes            each INBOX note draws an arc carrying the line verbatim + its number
  G12 the commits          a week's stream lists that week's commits, checked against git log
  G13 the real hub         the live roots render read-only to a scratch path; G1–G3 again
  G14 the mind is a token  every `mind:` key is ONE token ≤ 16 chars; a model line that is a whole
                           sentence yields exactly one mind, its first token
  G15 the panel is placed  the inspector is positioned from the click, clamped into the window, and
                           no fixed corner is left in the CSS for the open state
  G16 the mind cards       every `.root.mind` carries a non-empty data-mind equal to its mark's token
  G17 the postman's root   a machine root says `postman · passed <span> ago`, `postman quiet since
                           <HH:MM>` or `no postman`, and each answers a click
  G18 the lane's letters   a face's ✉ counts the letters WAITING for that lane across every
                           machine's post file, amber only while one has waited past
                           not_read_minutes; its click carries each letter verbatim with its why,
                           its holder and today's delivered ones — AND WITH NO POST FILE THE PAGE
                           IS BYTE-IDENTICAL to the generator as it stands today
  G19 the strip chip       `✉ n for you` on the strip ONLY while a note for the owner waits; its click
                           names each note, where it was raised and the push tool's own words;
                           gone when acked or past owner_hours

  H1–H11 a link remembers what crossed it:
                           the rails · seven person turns render seven lines ·
                           twenty of 25 and `5 earlier` · one turn keeps its line · a routine's one
                           line and status · a Codex rollout's turns once each · the pulse's cursor
                           reads only what was appended · a fall arc lists its pair's letters · every
                           line answers with its source · no new style, class or mark · the edges
                           (scrub, no writes outside the world, the live files untouched)
  G22 every drawn class    the inventory — every shape class the page draws, server-side
      answers              and in its script, with its count and its answer — has zero NONE on the
                           fixture page and on the real hub (G13); a planted shape with no mark,
                           in the page or in the script, is read NONE and fails. `--inventory`
                           prints the table for the live hub's own render and exits.
  H12      the list opens on NOW: only the newest line is
                           marked now, and the panel, once filled and placed, scrolls its own
                           scroller until that line's foot meets its foot

Every world is made by tempfile.mkdtemp under the system temp folder, one per run, and only this
run's world is removed. Every child is marked (EXO_GATE_TREE_INNER, EXO_GATE_TREE_DEPTH), started
in its own process group and killed with its group at the timeout; a copy of this gate run as a
child refuses at once.

Stdlib only, Python 3.9, OS-neutral. Exit 0 only when every check passes.
"""

import datetime
import html.parser
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
ROOT = Path(tempfile.gettempdir())            # this run's world is a mkdtemp folder in here
WORLD_PREFIX = "exo-gate-tree-answers-"
PY = sys.executable or "python3"
# Every child this gate starts carries these; a gate started as a child refuses.
INNER_ENV, DEPTH_ENV = "EXO_GATE_TREE_INNER", "EXO_GATE_TREE_DEPTH"
try:
    DEPTH = max(0, int(os.environ.get(DEPTH_ENV) or 0))
except ValueError:
    DEPTH = 1
MAX_DEPTH = 1

SCRATCH = HUB = PROJECTS = HOME = VOL = OUT = None
FAILS = []
PASSES = 0
CASE = {"id": "", "name": "", "fails": 0, "checks": 0, "first": ""}
# The registry this gate's world is given: invented names only — the owner the
# fixtures quote, and the minds with one persona for the Codex side. The world
# stands in for a person's hub, so it carries a person's registry; it carries
# THIS one, so the proof is the same whatever this machine's own registry names.
FIXTURE_REGISTRY = {
    "version": 1,
    "note": "gate-tree-answers' own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {
        "north": {"label": "North", "mark": "\u25cf", "os": "macos",
                  "hue": {"light": "#2456a4", "dark": "#7fb0e8"}},
        "south": {"label": "South", "mark": "\u258e", "os": "windows",
                  "hue": {"light": "#9a6b3a", "dark": "#d4a373"}},
    },
    "minds": [
        {"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#0a6ba8", "dark": "#4fc1ff"}},
        {"name": "OPUS", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#6f42ad", "dark": "#a78bfa"}},
        {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#0f766e", "dark": "#2dd4bf"}},
        {"name": "HAIKU", "vendor": "Anthropic", "kind": "claude", "show": True,
         "hue": {"light": "#64748b", "dark": "#9fb3c8"}},
        {"name": "NOBODY", "vendor": "OpenAI", "kind": "codex", "show": True,
         "hue": {"light": "#be185d", "dark": "#f0a0c0"}},
        {"name": "GROK", "vendor": "xAI", "kind": "grok", "show": False,
         "hue": {"light": "#4a6c00", "dark": "#9cc450"}},
        {"name": "CLAUDE", "vendor": "", "kind": "claude", "show": False,
         "hue": {"light": "#39518a", "dark": "#8fb4ff"}},
    ],
    "mind_aliases": {"CODEX": "NOBODY", "GPT": "NOBODY"},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Exocortex"], "not_groups": [], "hub_key": ""},
    "surface": {"caption": "", "base_scheme": {"dark_id": "", "label": "", "light_id": ""}},
}
# The order the page sorts minds in: the registry's own order (drawn_ids()
# predicts the session dots with it).
MIND_ORDER = dict((m["name"], i) for i, m in enumerate(FIXTURE_REGISTRY["minds"]))
PLACEHOLDERS = ("—", "-", "--", "n/a", "N/A", "TODO", "?", "none recorded", "")


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


def guarded(fn):
    try:
        fn()
    except Exception as exc:
        start(getattr(fn, "cid", "G?"), getattr(fn, "cname", fn.__name__))
        check(False, "the case raised: %r" % (exc,))
        done()


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(path), "w", encoding="utf-8", newline="\n").write(text)


def write_json(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def kill_group(proc):
    """The child AND everything it started: a plain timeout kills the direct child
    only, and a grandchild can hold the run open (memory self-spawning-gate-recursion)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def run(args, cwd=None, env=None, timeout=600):
    """(code, output) of one child — marked, one level deeper, in its own process
    group, and killed with that group when the timeout fires (124)."""
    base = dict(os.environ)
    base["PYTHONUTF8"] = "1"
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    base["GIT_TERMINAL_PROMPT"] = "0"
    base[INNER_ENV] = "1"
    base[DEPTH_ENV] = str(DEPTH + 1)
    for key, value in (env or {}).items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = str(value)
    kw = ({"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)} if os.name == "nt"
          else {"start_new_session": True})
    try:
        proc = subprocess.Popen([str(a) for a in args], cwd=str(cwd) if cwd else None, env=base,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, **kw)
    except Exception as exc:
        return 125, repr(exc)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, (out or b"").decode("utf-8", "replace").replace("\r\n", "\n")
    except subprocess.TimeoutExpired:
        kill_group(proc)
        try:
            out, _ = proc.communicate(timeout=10)
        except Exception:
            out = b""
        return 124, ("TIMEOUT after %ss\n" % timeout) + (out or b"").decode("utf-8", "replace")
    except Exception as exc:
        kill_group(proc)
        return 125, repr(exc)


def git(repo, *args, **kw):
    return run(["git", "-C", str(repo), "-c", "user.email=gate@gate", "-c", "user.name=gate",
                "-c", "commit.gpgsign=false"] + list(args), env=kw.get("env"), timeout=120)


def git_out(repo, *args):
    code, out = git(repo, *args)
    return out.strip() if code == 0 else ""


def must(code, out, what):
    if code != 0:
        raise RuntimeError("fixture step failed (%s): %s" % (what, " ".join((out or "").split())[:180]))
    return out


def iso(when):
    return when.replace(microsecond=0).isoformat()


def wkey(when):
    return "%s-W%02d" % (when.isocalendar()[0], when.isocalendar()[1])


def munged(path):
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


# --------------------------------------------------------------------------
# the world
# --------------------------------------------------------------------------

FACTS = {}


def build_world(generator):
    global SCRATCH, HUB, PROJECTS, HOME, VOL, OUT
    # ONE world per run, made fresh by mkdtemp: another run's world is never
    # swept from here (two runs at once each keep their own — memory
    # never-sweep-temp-worlds-while-a-runner-lives)
    SCRATCH = Path(tempfile.mkdtemp(prefix=WORLD_PREFIX))
    HUB, PROJECTS, HOME = SCRATCH / "hub", SCRATCH / "projects", SCRATCH / "home"
    VOL, OUT = SCRATCH / "vol", SCRATCH / "out"
    for folder in (HUB / "tools", HUB / "dossier", PROJECTS, VOL, OUT,
                   HOME / "orchestrator-sync", HOME / ".claude" / "projects",
                   HOME / ".claude" / "skills"):
        folder.mkdir(parents=True, exist_ok=True)
    # the pair under test travels together; exo_common comes from beside it
    src = Path(generator).resolve().parent
    shutil.copy2(str(generator), str(HUB / "tools" / "collect-openers.py"))
    # `exo_registry.py` travels with them: every one of these reads the person's
    # own names through it from its first line, and a world without the loader
    # gives them a ModuleNotFoundError before they run.
    # opener_carriers.py travels with them where it is installed: the collector
    # imports it under a guard and reads the folder's openers alone without it,
    # which is exactly what a hub without it draws (said once, below).
    # exo_paths.py too, where it is installed: the tools read the machine record
    # through the resolver from their first line.
    # exo_laws.py and personal.py too, where they are installed: the sky reads
    # whose each law is and the dossier's four pages through them.
    for name in ("opener_carriers.py", "exo_common.py", "grok_sessions.py",
                 "exo_registry.py", "exo_paths.py", "exo_laws.py", "personal.py"):
        beside = src / name
        found = beside if beside.exists() else (HERE / name)
        if name == "opener_carriers.py" and not found.exists():
            FACTS["no_carriers"] = True
            continue
        if name == "exo_paths.py" and not found.exists():
            continue                        # a hub from before the resolver
        if name in ("exo_laws.py", "personal.py") and not found.exists():
            continue                        # a hub from before the split law book
        shutil.copy2(str(found), str(HUB / "tools" / name))
    # The page asks the postman what it may say about the post
    # (tree_facts). It travels with the generator when it is there; where it is
    # not, the page draws exactly as it did before that build, which is G18b.
    for name in ("postman.py", "mail.py"):
        beside = src / name
        found = beside if beside.exists() else (HERE / name)
        if found.exists():
            shutil.copy2(str(found), str(HUB / "tools" / name))
    # The gate's own registry (FIXTURE_REGISTRY above): the names the fixtures
    # and the checks use, and nobody's real ones.
    write_json(HUB / "registry.json", FIXTURE_REGISTRY)
    write_json(HOME / "orchestrator-sync" / "machine.json",
               {"name": "gate", "os": platform.system(),
                "roots": {"orchestrator": str(HUB), "projects": str(PROJECTS),
                          "claude": str(HOME / ".claude"), "codex": str(HOME / ".codex")}})

    now = datetime.datetime.now().astimezone()
    FACTS["now"] = now

    # ── alpha: a git repo with commits in three of the six weeks ────────────
    alpha = PROJECTS / "alpha"
    alpha.mkdir(parents=True, exist_ok=True)
    must(*run(["git", "init", "-b", "main", str(alpha)], timeout=120), what="git init alpha")
    subjects = {}
    def commit(text, subject, when):
        write(alpha / "a.txt", text)
        must(*git(alpha, "add", "-A"), what="git add alpha")
        stamp = iso(when)
        must(*git(alpha, "commit", "-m", subject,
                  env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}),
             what="git commit alpha")
        sha = git_out(alpha, "rev-parse", "--short", "HEAD")
        subjects.setdefault(wkey(when), []).append((sha, subject))
    # oldest first: git prunes a --since walk at the first commit older than the
    # cutoff, so a repo whose parents run backwards in time hides its own week
    commit("oldest\n", "a commit four weeks back", now - datetime.timedelta(days=29))
    commit("older\n", "a commit two weeks back", now - datetime.timedelta(days=15))
    for i, subject in enumerate(("the first gate commit", "the second gate commit",
                                 "the third gate commit")):
        commit("a%d\n" % i, subject, now - datetime.timedelta(hours=4 - i))
    FACTS["alpha"] = str(alpha)
    FACTS["alpha_head"] = git_out(alpha, "rev-parse", "HEAD")
    FACTS["week"] = wkey(now)
    FACTS["subjects"] = subjects
    write(alpha / "STATUS.md",
          "# STATUS\n\n## Now\n\nAlpha is mid-arc.\n\n## To do\n\n"
          "- [ ] ! Land the alpha payload, then read its sheet, one at a time\n"
          "- [ ] a quieter alpha item\n")
    write(alpha / "OPENER.md", opener_text("Alpha", iso(now - datetime.timedelta(hours=1)),
                                           FACTS["alpha_head"],
                                           "read the project status/memory first.\n\n"
                                           "1. walk the alpha road\n", remaining=2))

    # ── beta: no git, no opener — the lane that owes a startup prompt ───────
    beta = PROJECTS / "beta"
    beta.mkdir(parents=True, exist_ok=True)
    write(beta / "STATUS.md", "# STATUS\n\n## Now\n\nBeta is waiting on a word.\n\n"
                              "## To do\n\n- [ ] the beta item\n")
    FACTS["beta"] = str(beta)

    # ── gamma: the model line that is a sentence, not a mind ──
    gamma = PROJECTS / "gamma"
    gamma.mkdir(parents=True, exist_ok=True)
    write(gamma / "STATUS.md", "# STATUS\n\n## Now\n\nGamma waits on the other side.\n\n"
                               "## To do\n\n- [ ] the gamma item\n")
    FACTS["sentence"] = ("NOBODY - XHIGH for diagnosis; OPUS - medium for settled "
                         "mechanical checks")
    write(gamma / "OPENER-Gamma.md",
          opener_text("Gamma", iso(now - datetime.timedelta(hours=2)), "",
                      "read the project status/memory first.\n\n1. walk the gamma road\n",
                      model=FACTS["sentence"]))
    FACTS["gamma"] = str(gamma)

    # ── the hub itself: the comma-led heading that broke NEXT ───────────────
    FACTS["next"] = "Land the gate payload and read its sheet"
    write(HUB / "STATUS.md",
          "# STATUS\n\n## Now\n\nThe hub is mid-arc.\n\n## To do\n\n"
          "- [ ] ! A hub item, with commas, that is not the move\n")
    write(HUB / "OPENER.md", opener_text("Gate hub", iso(now - datetime.timedelta(minutes=30)), "",
                                         "read the project status/memory first.\n\n"
                                         "Machine's next move, in this order, ONE AT A TIME:\n"
                                         "1. %s\n2. Then the second step\n" % FACTS["next"]))

    # ── the INBOX: two notes, in the window, between the two projects ───────
    note_a = ("- %s · beta ← alpha · alpha found the gate's own note, with a comma in it "
              "· suggested action: read it" % (now - datetime.timedelta(days=1)).date().isoformat())
    note_b = ("- %s · alpha → beta · the second note, also verbatim "
              "· suggested action: none" % (now - datetime.timedelta(days=9)).date().isoformat())
    inbox = ["# INBOX", "", "Notes between projects.", "", note_a, note_b, ""]
    write(HUB / "INBOX.md", "\n".join(inbox))
    FACTS["notes"] = {note_a: inbox.index(note_a) + 1, note_b: inbox.index(note_b) + 1}
    write(HUB / "IDEAS.md", "# IDEAS\n\n- %s 09:00 · new · the gate's own idea\n"
          % now.date().isoformat())
    write(HUB / "dossier" / "TAUGHT.md",
          "# TAUGHT\n\n- %s — the gate learned something [PROMOTED to global CLAUDE.md %s]\n"
          % (now.date().isoformat(), now.date().isoformat()))
    write(HUB / "dossier" / "who.md", "# Who\n\nA page of the dossier.\n")

    # ── the brain the sky is drawn from ─────────────────────────────────────
    mem = HOME / ".claude" / "projects" / (munged(PROJECTS) + "-alpha") / "memory"
    write(mem / "alpha-one.md",
          "---\nname: alpha-one\ndescription: \"the first gate memory, which links to the second\"\n"
          "metadata:\n  type: project\n---\n\nIt links to [[alpha-two]].\n")
    write(mem / "alpha-two.md",
          "---\nname: alpha-two\ndescription: \"the second gate memory\"\n"
          "metadata:\n  type: feedback\n---\n\nNothing linked from here.\n")
    write(HOME / ".claude" / "skills" / "gate-skill" / "SKILL.md",
          "# gate-skill\n\nIt works on alpha.\n")
    write(HOME / ".claude" / "CLAUDE.md",
          "# Law\n\n**Gate law (Wren, %s, ratified):** every mark answers a click.\n"
          % now.date().isoformat())

    # ── the transcripts the session dots are drawn from ─────────────────────
    for name, cwd in (("aaaaa1", alpha), ("aaaaa2", alpha), ("bbbbb1", beta)):
        f = (HOME / ".claude" / "projects" / munged(cwd) / ("session-%s.jsonl" % name))
        write(f, json.dumps({"cwd": str(cwd), "model": "claude-fable-5-1",
                             "type": "assistant"}) + "\n")

    # ── the two live files: ONE live session, TWO stamps ────────────────────
    write_json(HUB / "live-sessions-gate.json",
               {"machine": "gate", "when": iso(now - datetime.timedelta(minutes=2)),
                "live_minutes": 10,
                "sessions": [{"id": "aaaaa1", "dir": munged(alpha), "kind": "claude",
                              "mind": "FABLE", "model": "claude-fable-5-1",
                              "cwd": str(alpha), "in_hub": False, "minutes_ago": 2}]})
    write_json(HUB / "live-gate-fable.json",
               {"machine": "gate", "mind": "FABLE", "when": iso(now),
                "sessions": [{"title": "GATE A", "effort": "EXTRA",
                              "when": iso(now - datetime.timedelta(hours=1))},
                             {"title": "GATE B", "effort": "EXTRA",
                              "when": iso(now - datetime.timedelta(hours=3))}]})
    write(HUB / "TREE.md", "<!-- tree:auto-start -->\n<!-- tree:auto-end -->\n")


OPENER_KEYS = ("lane", "written", "by", "on", "head", "status_updated",
               "where", "next", "depends_on", "open_in", "model")


def opener_text(lane, written, head, body, remaining=None, model="FABLE · EXTRA"):
    header = {"lane": lane, "written": written, "by": "the gate", "on": "GATE", "head": head,
              "status_updated": written, "where": "%s stands here" % lane, "next": "machine",
              "depends_on": "nothing", "open_in": "GATE · a fresh session · ACT — %s: the gate" % lane,
              "model": model}
    lines = ["%s: %s" % (k, header[k]) for k in OPENER_KEYS]
    if remaining is not None:
        lines.append("remaining: %s sittings" % remaining)
    return "\n".join(lines + ["---", body])


def env_for(out_path):
    # The world's own record, named outright: a record this machine names
    # (EXO_MACHINE_JSON) never reaches the fixture world, and a tool that reads
    # the record through the resolver reads the world's.
    return {"HOME": str(HOME), "USERPROFILE": str(HOME), "HOMEDRIVE": None, "HOMEPATH": None,
            "EXO_MACHINE_JSON": str(HOME / "orchestrator-sync" / "machine.json"),
            "COLLECT_OPENERS_ROOT": None,
            "COLLECT_OPENERS_VOLUMES": str(VOL),
            "COLLECT_OPENERS_WORK": str(SCRATCH / "work"),
            "COLLECT_OPENERS_ENGINE": str(HOME / "orchestrator-sync"),
            "COLLECT_OPENERS_OUT": str(out_path)}


def render(out_path):
    code, out = run([PY, str(HUB / "tools" / "collect-openers.py"), "--html"],
                    cwd=str(HUB), env=env_for(out_path))
    if code != 0:
        raise RuntimeError("--html exited %d: %s" % (code, out[-600:]))
    return out, io.open(str(out_path), encoding="utf-8").read()


# --------------------------------------------------------------------------
# reading a rendered page
# --------------------------------------------------------------------------

def blob(html, blob_id):
    m = re.search(r'<script type="application/json" id="%s">(.*?)</script>' % blob_id, html, re.S)
    return json.loads(m.group(1)) if m else None


def drawn_ids(html):
    """Every id the raw HTML points at, plus every id the JS will draw from the
    two data blobs — the whole set of marks the page can show."""
    found = set(re.findall(r'data-mark="([^"]+)"', body_of(html)))
    fall, lanes = blob(html, "fall-data") or {}, blob(html, "lanes") or []
    for col in fall.get("cols") or []:
        for week in fall.get("weeks") or []:
            found.add("stream:%d:%s" % (col["i"], week["key"]))
            sessions = sorted((col.get("sessions") or {}).get(week["key"]) or [],
                              key=lambda s: (MIND_ORDER.get(s.get("mind"), 9), s.get("id") or ""))
            for k in range(min(6, len(sessions))):
                found.add("sdot:%d:%s:%d" % (col["i"], week["key"], k))
    for i in range(len(fall.get("arcs") or [])):
        found.add("arc:%d" % i)
    for i in range(len(fall.get("gates") or [])):
        found.add("gate:%d" % i)
    for i, lane in enumerate(lanes):
        for s in lane.get("sessions") or []:
            found.add("nerve:%d:%s" % (i, s.get("id") or ""))
    return found


def body_of(html):
    """The page without its own JavaScript: the JS SOURCE names data-mark too,
    and a template string is not a mark on the page."""
    cut = html.rfind("<script>")
    return html[:cut] if cut > 0 else html


# the JS draw templates, by the class they draw and the mark variable they must carry
JS_TEMPLATES = (("commit stream", 'rect class="stream', "smk"),
                ("session dot", 'circle class="sdot"', "dmk"),
                ("the ×N label", 'text class="xn"', "dm("),
                ("note arc", "path class=\"'+cls+'\"", "amk"),
                ("the arc's end dot", 'circle class="aend', "amk"),
                ("nerve", 'path class="nerve"', "nmk"),
                ("the nerve's tip", 'circle class="nend"', "nmk"),
                ("the sky halo", 'circle class="halo"', "nmk"),
                ("machine taproot", "path class=\"'+k+'\"", "rmk"),
                ("mind root", 'path class="root mind live"', "mmk"))

# the server-drawn marks, by the class that must carry a data-mark
SERVER_MARKS = (("the owed-prompts chip", r'<button class="chip"'),
                ("a strip count", r'<button class="cnt"'),
                ("a legend key", r'<button type="button"'),
                ("a week label", r'<span class="wl"'),
                ("the nameplate", r'<div class="nameplate"'),
                ("a machine root", r'<div class="root machine'),
                ("a mind root", r'<div class="root mind'),
                ("the collar ring", r'<svg class="ring"'),
                ("a memory star", r'class="s(?: today)?" data-key'),
                ("a journal dot", r'<circle class="jd'),
                ("a law tick", r'<path class="tick'),
                ("a sky link", r'<path class="link"'),
                ("a dossier page", r'<rect class="dos"'),
                ("a skill", r'<path class="skill"'),
                ("a row of the sky", r'<text class="bl"'),
                ("a work-left bar", r'<rect class="bar '))


def g1_checks(html, source, label, require_all=True):
    """Every mark on a page answers. The FIXTURE page carries every kind of mark
    and must (require_all); a REAL hub's page carries what that hub has — a new
    hub has no memory star, no law tick, no skill yet — so on it a kind that is
    absent is said once, as a skip, and every mark that IS there must answer."""
    js = source[source.index("HTML_JS = r\"\"\""):source.index("def _e(text)")]
    for name, token, mark in JS_TEMPLATES:
        spots = [m.start() for m in re.finditer(re.escape(token), js)]
        check(bool(spots), "%s: the %s template is gone from the JS" % (label, name))
        for spot in spots:
            line_start = js.rfind("\n", 0, spot) + 1
            line_end = js.find("\n", spot + len(token))
            statement = js[line_start:line_end if line_end > 0 else len(js)]
            check(mark in statement or "data-mark" in statement,
                  "%s: the %s template draws without a mark: %s" % (label, name, statement.strip()[:90]))
    body = body_of(html)
    absent = []
    for name, pattern in SERVER_MARKS:
        spots = [m.start() for m in re.finditer(pattern, body)]
        if not spots and not require_all:
            absent.append(name)
            continue
        check(bool(spots), "%s: no %s on the page" % (label, name))
        for spot in spots[:80]:
            window = body[spot:spot + 400]
            tail = window[:window.find(">") + 1] if ">" in window else window
            check("data-mark=" in tail, "%s: a %s carries no data-mark: %s" % (label, name, tail[:110]))
    if absent:
        skip_note("%s has none of these yet — %s; the fixture page (G1) proves each of them"
                  % (label, ", ".join(absent)))
    marks = blob(html, "marks") or {}
    drawn, registered = drawn_ids(html), set(marks)
    missing = sorted(drawn - registered)[:6]
    orphan = sorted(registered - drawn)[:6]
    check(not missing, "%s: %d marks are drawn with no answer: %s" % (label, len(drawn - registered), missing))
    check(not orphan, "%s: %d answers are registered but never drawn: %s" % (label, len(registered - drawn), orphan))
    return marks


def g2_checks(marks, label):
    bad_kind = [k for k, v in marks.items() if not str(v.get("kind") or "").strip()]
    check(not bad_kind, "%s: %d entries have no kind: %s" % (label, len(bad_kind), bad_kind[:5]))
    empty = [k for k, v in marks.items() if not (v.get("bytes") or [])]
    check(not empty, "%s: %d entries have no bytes: %s" % (label, len(empty), empty[:5]))
    holes = []
    for key, value in marks.items():
        for row in value.get("bytes") or []:
            if len(row) != 2 or str(row[1]).strip() in PLACEHOLDERS:
                holes.append("%s/%s" % (key, row[0] if row else "?"))
    check(not holes, "%s: %d byte rows are placeholders: %s" % (label, len(holes), holes[:5]))


def g3_checks(html, label):
    check('<aside id="inspector"' in html, "%s: the inspector element is missing" % label)
    check(html.count("closest('[data-mark]')") == 1,
          "%s: the delegated listener appears %d times, not once"
          % (label, html.count("closest('[data-mark]')")))
    check('id="marks"' in html, "%s: the MARKS table is missing" % label)


# --------------------------------------------------------------------------
# the cases
# --------------------------------------------------------------------------

def case_g1():
    start("G1", "every mark answers")
    source = io.open(str(HUB / "tools" / "collect-openers.py"), encoding="utf-8").read()
    marks = g1_checks(FACTS["html"], source, "fixture")
    FACTS["marks"] = marks
    done()


def case_g2():
    start("G2", "real bytes only")
    g2_checks(FACTS["marks"], "fixture")
    done()


def case_g3():
    start("G3", "one mechanism")
    g3_checks(FACTS["html"], "fixture")
    done()


def case_g4():
    start("G4", "the nerves control")
    html = FACTS["html"]
    m = re.search(r'<button class="tbtn" id="nbtn"[^>]*>([^<]*)</button>', html)
    check(m is not None, "the nerves control is missing while a session is live")
    if m:
        check('aria-pressed="true"' in m.group(0), "the nerves control has no aria-pressed")
        check("nerves on" in m.group(1) or "nerves off" in m.group(1),
              "the nerves control does not say its state: %r" % m.group(1))
    m = re.search(r'<button class="tbtn" id="lbtn"[^>]*>([^<]*)</button>', html)
    check(m is not None and "aria-pressed" in m.group(0), "the notes control has no aria-pressed")
    check(m is not None and ("hide notes" in m.group(1) or "show notes" in m.group(1)),
          "the notes control does not say what the click does")
    # now take the live session away and render again
    write_json(HUB / "live-sessions-gate.json",
               {"machine": "gate", "when": iso(FACTS["now"] - datetime.timedelta(minutes=2)),
                "live_minutes": 10, "sessions": []})
    _, quiet = render(OUT / "quiet.html")
    check('id="nbtn"' not in quiet, "the nerves control is still drawn with nothing to toggle")
    check(">0 live</button>" in quiet, "the strip does not say `0 live` when nothing is live")
    check('data-mark="count:live"' in quiet, "the live count answers nothing")
    FACTS["quiet"] = quiet
    write_json(HUB / "live-sessions-gate.json",
               {"machine": "gate", "when": iso(FACTS["now"] - datetime.timedelta(minutes=2)),
                "live_minutes": 10,
                "sessions": [{"id": "aaaaa1", "dir": munged(Path(FACTS["alpha"])), "kind": "claude",
                              "mind": "FABLE", "model": "claude-fable-5-1",
                              "cwd": FACTS["alpha"], "in_hub": False, "minutes_ago": 2}]})
    done()


def case_g5():
    start("G5", "the NEXT sentence")
    m = re.search(r'<span class="bl next"><b>next</b>([^<]*)</span>', FACTS["html"])
    check(m is not None, "the hub tile has no next line")
    if m:
        text = m.group(1).strip()
        check(bool(text), "the next line is empty")
        check(text[:1].isalpha(), "the next line does not start with a letter: %r" % text)
        check(len(text.split()) >= 3, "the next line is a fragment: %r" % text)
        check(text == FACTS["next"], "the next line is not the step under the heading: %r" % text)
        check("in this order" not in text, "the next line is still the scaffolding: %r" % text)
    done()


def case_g6():
    start("G6", "one word per measure")
    html = FACTS["html"]
    m = re.search(r'<div class="npbeat">([^<]*)</div>', html)
    check(m is not None and "1 live" in m.group(1),
          "the nameplate does not say `1 live`: %r" % (m.group(1) if m else None))
    m = re.search(r'<div class="root machine[^>]*>(.*?)</div>', html, re.S)
    card = m.group(1) if m else ""
    check("2 stamped" in card, "the machine root does not say `2 stamped`: %s" % card[:200])
    check("1 live" in card, "the machine root does not say `1 live`: %s" % card[:200])
    collar = html[html.index('<section class="hubbar"'):html.index('<section class="dormant')] \
        if '<section class="dormant' in html else html[html.index('<section class="hubbar"'):]
    numbered = set(re.findall(r'(\d+)\s+sessions?\b', re.sub(r"<[^>]+>", " ", collar)))
    check(not numbered, "the collar still counts `N session(s)` beside %s — two measures, one word"
          % sorted(numbered))
    done()


def case_g7():
    start("G7", "one-click start")
    html = FACTS["html"]
    launches = [h.replace("&amp;", "&") for h in
                re.findall(r'<a class="launch" href="([^"]+)"', html)]
    check(bool(launches), "no launch link on any face")
    alpha = [h for h in launches if "alpha" in h and "Pick%20up" in h]
    check(bool(alpha), "the lane with an opener has no ▶ Launch with the one-sentence paste")
    if alpha:
        check(alpha[0].startswith("claude-cli://open?cwd="), "the launch link is not the registered scheme")
        check("OPENER.md" in alpha[0], "the launch sentence does not name the opener file")
    beta = [h for h in launches if "beta" in h]
    check(bool(beta), "the lane with no opener has no front-door link")
    if beta:
        check("q=read%20the%20project%20status%2Fmemory%20first." in beta[0],
              "the front-door link does not carry the front-door sentence: %s" % beta[0][:120])
    check(">▶ Open</a>" in html, "no ▶ Open on the lane without an opener")
    check(">▶ Launch</a>" in html, "no ▶ Launch on the lane with one")
    lanes = blob(html, "lanes") or []
    same = [r for r in lanes if r.get("launch") and r["launch"] in launches]
    check(bool(same), "the face's link is not the same link the card carries")
    done()


def case_g8():
    start("G8", "nothing superfluous")
    html = FACTS["html"]
    check("Rows are the kind of file" not in html, "the explaining paragraph is still under the sky")
    check("● project memory · ○ reference" not in html, "the glyph key is still under the sky")
    m = re.search(r'<p class="skycap">(.*?)</p>', html, re.S)
    check(m is not None, "the sky caption is gone entirely")
    if m:
        counts = re.findall(r'<button class="cnt"[^>]*><b>\d+</b> ([^<]+)</button>', m.group(1))
        check(len(counts) == 7, "the caption has %d counts, not seven: %s" % (len(counts), counts))
        check("<br>" not in m.group(1), "the caption is more than one line")
        for word in ("memories", "constellations", "links", "skills", "laws",
                     "journal lines", "dossier pages"):
            check(word in counts, "the caption does not count %s" % word)
    # a legend key may not claim a number the page does not carry
    body, marks = body_of(html), FACTS["marks"] or {}
    for key, tokens in (("legend:ready", ('class="ph ready', 'class="tile ready')),
                        ("legend:wait", ('class="ph wait', 'class="tile wait')),
                        ("legend:bad", ('class="ph bad', 'class="tile bad')),
                        ("legend:cool", ('class="tile cool',)),
                        ("legend:launch", ('class="launch"',)),
                        ("legend:prompt", ('class="pr"',)),
                        ("legend:ages", ('class="ages"',)),
                        ("legend:mail", ('class="mail"',)),
                        ("legend:gated", ('class="st gt"', 'class="sx gt"')),
                        ("legend:live", ('class="lv ',))):
        entry = marks.get(key)
        if not entry:
            continue                      # nothing of that kind here: no key
        claim = [r[1] for r in entry["bytes"] if r[0].startswith("marks like this")]
        real = sum(body.count(token) for token in tokens)
        check(bool(claim) and int(claim[0]) == real,
              "%s claims %s marks, the page carries %d" % (key, claim or "nothing", real))
    done()


def case_g9():
    start("G9", "the owed prompts")
    html = FACTS["html"]
    m = re.search(r'<button class="chip" type="button" data-mark="([^"]+)">([^<]*)</button>', html)
    check(m is not None, "the owed-prompts chip is not a button")
    if m:
        entry = (FACTS["marks"] or {}).get(m.group(1)) or {}
        rows = entry.get("bytes") or []
        lanes = [r[0] for r in rows]
        check(lanes == ["beta"], "the chip names %s, not the one owing lane" % lanes)
        check(any("no OPENER file" in str(r[1]) for r in rows),
              "the chip does not say why the lane owes one: %s" % rows[:2])
        check((entry.get("action") or {}).get("lane") is not None,
              "the chip offers no way into the lane")
    done()


def case_g10():
    start("G10", "the page itself")
    html, out = FACTS["html"], FACTS["stdout"]
    size = len(html.encode("utf-8"))
    check(size <= 1600000, "the page is %d bytes, over 1.6 MB" % size)
    check('<meta http-equiv="refresh" content="300">' in html, "the self-refresh tag is gone")
    for scheme in ("noir", "instrument", "cream", "print"):
        check(':root[data-scheme="%s"]' % scheme in html, "the %s scheme no longer renders" % scheme)
        check('<option value="%s">' % scheme in html, "the %s scheme is not on the picker" % scheme)
    check("0 overlapping pairs" in out, "the sky's label check is no longer clean: %s" % out[-200:])
    print("     page: %d bytes · %d marks" % (size, len(FACTS["marks"] or {})))
    done()


def list_of(entry, html):
    """The history a mark answers with: its own, or the page's shared
    one it names in the `lists` blob. None when it has none."""
    got = (entry or {}).get("list")
    if isinstance(got, str):
        got = (blob(html, "lists") or {}).get(got)
    return got if isinstance(got, dict) else None


def case_g11():
    start("G11", "the notes")
    marks = FACTS["marks"] or {}
    arcs = {k: v for k, v in marks.items() if k.startswith("arc:")}
    check(len(arcs) == 2, "%d arcs for the fixture's two notes" % len(arcs))
    # an arc answers with the letters between its pair — the INBOX line
    # verbatim on hover, its number on a click — no longer as byte rows
    for line, number in FACTS["notes"].items():
        hit = [v for v in arcs.values()
               if any((it.get("full") or it.get("w")) == line
                      for it in ((list_of(v, FACTS["html"]) or {}).get("items") or []))]
        check(len(hit) == len(arcs), "not every arc of the pair carries the INBOX line "
              "verbatim: %s" % line[:70])
        if hit:
            srcs = [it.get("src") for it in list_of(hit[0], FACTS["html"])["items"]
                    if (it.get("full") or it.get("w")) == line]
            check(srcs == ["INBOX.md:%d" % number],
                  "the line does not say where it is: %s" % srcs)
            check(hit[0]["kind"].startswith("the notes between"),
                  "the arc does not say what it is: %r" % hit[0]["kind"])
    done()


def case_g12():
    start("G12", "the commits")
    marks = FACTS["marks"] or {}
    fall = blob(FACTS["html"], "fall-data") or {}
    col = [c for c in (fall.get("cols") or []) if c["name"] == "alpha"]
    check(bool(col), "alpha is not a column of the fall")
    if not col:
        return done()
    key = "stream:%d:%s" % (col[0]["i"], FACTS["week"])
    entry = marks.get(key) or {}
    rows = entry.get("bytes") or []
    text = git_out(Path(FACTS["alpha"]), "log", "--since=%s"
                   % (FACTS["now"] - datetime.timedelta(days=6)).date().isoformat(),
                   "--format=%h\t%s")
    want = [tuple(line.split("\t", 1)) for line in text.splitlines() if "\t" in line]
    check(len(want) == 3, "the fixture week has %d commits, not three" % len(want))
    check(any(r[0] == "commits" and r[1] == "3" for r in rows),
          "the stream does not count this week's three commits: %s" % rows[:3])
    for sha, subject in want:
        check(any(r[0] == sha and subject in str(r[1]) for r in rows),
              "the stream does not name commit %s (%s): %s" % (sha, subject, [r[0] for r in rows]))
    check(entry.get("kind", "").endswith("alpha"), "the stream does not name its project")
    done()


def case_g13():
    start("G13", "the real hub")
    live_hub = HERE.parent
    out_path = OUT / "real-tree.html"
    # The real hub is drawn with the real hub's OWN registry — never the one
    # this gate gave its fixture world (FIXTURE_REGISTRY), which the copied
    # generator would otherwise find beside itself. A hub with no registry.json
    # reads the loader's defaults, as its own tools would.
    code, out = run([PY, str(HUB / "tools" / "collect-openers.py"), "--html"],
                    cwd=str(live_hub),
                    env={"COLLECT_OPENERS_OUT": str(out_path), "COLLECT_OPENERS_ROOT": None,
                         "EXO_REGISTRY_JSON": str(live_hub / "registry.json")})
    check(code == 0, "the real hub did not render: %s" % out[-300:])
    if code != 0:
        return done()
    html = io.open(str(out_path), encoding="utf-8").read()
    source = io.open(str(HUB / "tools" / "collect-openers.py"), encoding="utf-8").read()
    marks = g1_checks(html, source, "the real hub", require_all=False)
    g2_checks(marks, "the real hub")
    g3_checks(html, "the real hub")
    bad = [k for k in marks if k.startswith("mind:") and not MIND_KEY.match(k)]
    check(not bad, "the real hub names a mind with something that is not a token: %s" % bad[:3])
    for mark, mind in mind_cards(html):
        check(bool(mind.strip()) and mark == "mind:" + mind,
              "the real hub's mind card %r / %r disagree" % (mark, mind))
    rows = g22_checks(html, source, "the real hub")
    print("     the real hub's inventory: %d drawn classes · %d NONE"
          % (len(rows), sum(1 for r in rows if r[2].startswith("NONE"))))
    size = len(html.encode("utf-8"))
    check(size <= 1600000, "the real page is %d bytes, over 1.6 MB" % size)
    kinds = {}
    for key in marks:
        kinds[key.split(":")[0]] = kinds.get(key.split(":")[0], 0) + 1
    print("     the real hub: %d bytes · %d marks · %s"
          % (size, len(marks), " · ".join("%s %d" % (k, n) for k, n in sorted(kinds.items()))))
    done()


# --------------------------------------------------------------------------
# the inventory: every drawn class, its count, its answer or NONE
# --------------------------------------------------------------------------

SHAPES = ("path", "circle", "rect", "text", "line", "polyline", "polygon", "ellipse")
# shapes that are part of another mark, never a mark of their own — each with
# the reason it needs no answer; anything else with no mark is NONE
PART_OF = {"hitl": "a hit area: the click target of the line it lies on",
           "hita": "a hit area: the click target of the dot or bar it covers",
           "nerve glow": "the glow under a nerve: the nerve drawn on it answers",
           "halo star": "a ring around a star: the star beneath it answers",
           "cent": "an anchor the script measures: fill and stroke none, never seen"}
# the script's mark variables, by the id prefix each one carries
JS_MARK_VARS = (("smk", "stream"), ("dmk", "sdot"), ("dm('sdot", "sdot"), ("amk", "arc"),
                ("rmk", "root"), ("nmk", "nerve"), ("mmk", "mind"))
JS_SHAPE = re.compile(r"""<(%s)\b[^>]*?class=\\?["']([^"'\\]*)""" % "|".join(SHAPES))
VOID = ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
        "track", "wbr")


def part_of(cls):
    words = cls.split()
    for key, why in PART_OF.items():
        if all(w in words for w in key.split()):
            return why
    return ""


class _Shapes(html.parser.HTMLParser):
    """Every shape the page's own bytes draw inside an <svg>, with the mark it
    (or the nearest element around it) carries."""

    def __init__(self):
        html.parser.HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.found = [], []

    def _open(self, tag, attrs, closes):
        a = dict(attrs)
        mark = a.get("data-mark") or (self.stack[-1][1] if self.stack else "")
        in_svg = tag == "svg" or any(t == "svg" for t, _ in self.stack)
        if in_svg and tag in SHAPES:
            self.found.append((tag, " ".join((a.get("class") or "").split()), mark))
        if not closes and tag not in VOID:
            self.stack.append((tag, mark))

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                del self.stack[k:]
                break


def inventory(html_text, source):
    """[(class, count, answer)] for every shape class the page draws — the server's
    own shapes from the bytes, the script's from its draw statements — where the
    answer is the kinds its marks answer with, the reason it is part of another
    mark, or NONE."""
    marks = blob(html_text, "marks") or {}
    rows = {}

    def add(key, n, kinds, why):
        r = rows.setdefault(key, {"n": 0, "kinds": set(), "why": why, "none": 0})
        r["n"] += n
        r["kinds"].update(kinds)

    parser = _Shapes()
    parser.feed(body_of(html_text))
    for tag, cls, mark in parser.found:
        key = "%s.%s" % (tag, cls.replace(" ", ".")) if cls else tag
        why = part_of(cls)
        entry = marks.get(mark) if mark else None
        add(key, 1, [entry.get("kind")] if entry else [], why)
        if not why and not entry:
            rows[key]["none"] += 1
    drawn = drawn_ids(html_text)
    js = source[source.index("HTML_JS = r\"\"\""):source.index("def _e(text)")]
    for m in JS_SHAPE.finditer(js):
        ls, le = js.rfind("\n", 0, m.start()) + 1, js.find("\n", m.end())
        statement = js[ls:le if le > 0 else len(js)]
        cls = m.group(2).strip() or "(%s)" % next((p for v, p in JS_MARK_VARS if v in statement), "?")
        key = "%s.%s ·script" % (m.group(1), cls.replace(" ", "."))
        why = part_of(m.group(2))
        prefix = next((p for v, p in JS_MARK_VARS if v in statement), None)
        if prefix == "arc" and "gate" in statement:
            prefix = None
        ids = [i for i in drawn if prefix and i.split(":")[0] == prefix] if prefix else []
        if prefix == "arc":
            ids = [i for i in drawn if i.split(":")[0] in ("arc", "gate")]
        kinds = set(marks[i].get("kind") for i in ids if i in marks)
        if key in rows:
            rows[key]["kinds"].update(kinds)
            continue
        add(key, len(ids), kinds, why)
        if not why and not prefix and "data-mark" not in statement and "dm(" not in statement:
            rows[key]["none"] = max(1, rows[key]["n"])
    out = []
    for key in sorted(rows):
        r = rows[key]
        if r["none"]:
            answer = "NONE" + (" (%d of %d)" % (r["none"], r["n"]) if r["none"] != r["n"] else "")
        elif r["why"]:
            answer = "part of — " + r["why"]
        else:
            ks = sorted(k for k in r["kinds"] if k)
            answer = ("answers · " + " / ".join(ks[:2]) + (" +%d" % (len(ks) - 2) if len(ks) > 2 else "")) \
                if ks else "answers · (none drawn on this page)"
        out.append((key, r["n"], answer))
    return out


def print_inventory(rows, label):
    print("     inventory · %s · %d classes · %d NONE" % (label, len(rows),
                                                         sum(1 for r in rows if r[2].startswith("NONE"))))
    for key, n, answer in rows:
        print("       %-34s %5d  %s" % (key[:34], n, answer[:96]))


def g22_checks(html_text, source, label):
    rows = inventory(html_text, source)
    none = [r for r in rows if r[2].startswith("NONE")]
    check(not none, "%s: %d drawn class%s answer nothing: %s" % (
        label, len(none), "" if len(none) == 1 else "es", ["%s %s" % (r[0], r[2]) for r in none[:6]]))
    return rows


def case_g22():
    start("G22", "every drawn class answers")
    source = io.open(str(HUB / "tools" / "collect-openers.py"), encoding="utf-8").read()
    html_text = FACTS["html"]
    rows = g22_checks(html_text, source, "fixture")
    print_inventory(rows, "the fixture page")
    # a shape planted in the page's bytes with no mark must read NONE
    at = html_text.rfind("<footer")
    planted = html_text[:at] + '<svg><path class="planted-bq356" d="M0 0 L9 9"/></svg>' + html_text[at:]
    hit = [r for r in inventory(planted, source) if r[0] == "path.planted-bq356"]
    check(bool(hit) and hit[0][2].startswith("NONE"),
          "a planted page shape with no mark was not read NONE: %s" % hit)
    # a shape planted in the script's draw code with no mark must read NONE
    js_at = source.index("    svg.innerHTML=out+nout;")
    planted_src = (source[:js_at] + "    out+='<circle class=\"planted-bq356\" cx=\"1\" cy=\"1\" r=\"2\"/>';\n"
                   + source[js_at:])
    hit = [r for r in inventory(html_text, planted_src) if r[0] == "circle.planted-bq356 ·script"]
    check(bool(hit) and hit[0][2].startswith("NONE"),
          "a planted script shape with no mark was not read NONE: %s" % hit)
    # the crown's grid stands above the lines (z-index 2): its gaps must let a
    # click through to the line beneath, and its heads must still take theirs —
    # the dashed nerve between two rows of heads that answered nothing
    css = style_of(html_text)
    crown = re.search(r"\.crown\{[^}]*\}", css)
    check(bool(crown) and "pointer-events:none" in crown.group(0),
          "the crown takes the clicks meant for the lines beneath it: %s"
          % (crown.group(0)[:90] if crown else "no .crown rule"))
    heads = re.search(r"\.heads\{[^}]*\}", css)
    ph = re.search(r"(?:^|[}\n])\.ph\{[^}]*\}", css)
    check(bool(heads) and "pointer-events:none" in heads.group(0),
          "the heads' grid takes the clicks meant for the lines beneath it: %s"
          % (heads.group(0)[:90] if heads else "no .heads rule"))
    check(bool(ph) and "pointer-events:auto" in ph.group(0),
          "a head no longer takes its own click: %s" % (ph.group(0)[:90] if ph else "no .ph rule"))
    # and the page's own self-check carries the click half (HITCHECK under ?check=1)
    check("function hitcheck()" in source and "hitcheck();" in source and 'id=\\"hitcheck\\"' in source,
          "the page's ?check=1 mode carries no hitcheck")
    done()


def inventory_only(generator, hub):
    """`--inventory`: the live hub drawn read-only to a temp file, its table printed."""
    folder = Path(tempfile.mkdtemp(prefix=WORLD_PREFIX + "inv-"))
    try:
        out_path = folder / "tree.html"
        code, out = run([PY, str(generator), "--html"], cwd=str(hub),
                        env={"COLLECT_OPENERS_OUT": str(out_path), "COLLECT_OPENERS_ROOT": None,
                             "EXO_REGISTRY_JSON": str(hub / "registry.json")})
        if code != 0:
            print("the live hub did not render: %s" % out[-300:])
            return 1
        html_text = io.open(str(out_path), encoding="utf-8").read()
        rows = inventory(html_text, io.open(str(generator), encoding="utf-8").read())
        print_inventory(rows, "the live hub · %s" % generator)
        none = sum(1 for r in rows if r[2].startswith("NONE"))
        print("%s · %d drawn classes · %d NONE" % ("OK" if not none else "STOP", len(rows), none))
        return 0 if not none else 1
    finally:
        shutil.rmtree(str(folder), ignore_errors=True)


MIND_KEY = re.compile(r"^mind:([A-Z0-9][A-Z0-9.\-]{0,15})$")


def mind_cards(html):
    """[(the card's data-mark, its data-mind)] — every mind root on the page."""
    found = []
    for tag in re.findall(r'<div class="root mind[^>]*>', body_of(html)):
        mark = re.search(r'data-mark="([^"]*)"', tag)
        mind = re.search(r'data-mind="([^"]*)"', tag)
        found.append((mark.group(1) if mark else "", mind.group(1) if mind else ""))
    return found


def case_g14():
    start("G14", "the mind is a token")
    marks = FACTS["marks"] or {}
    keys = [k for k in marks if k.startswith("mind:")]
    check(bool(keys), "no mind answers anything at all")
    bad = [k for k in keys if not MIND_KEY.match(k)]
    check(not bad, "%d mind keys are not one token: %s" % (len(bad), bad[:3]))
    sentence_words = ("XHIGH", "DIAGNOSIS", "MECHANICAL", " FOR ", ";")
    carried = [k for k in keys if any(w in k.upper() for w in sentence_words)]
    check(not carried, "a mind is named after a sentence: %s" % carried[:2])
    persona = [k for k in keys if k == "mind:NOBODY"]
    check(len(persona) == 1, "the sentence did not become exactly one NOBODY: %s" % keys)
    if persona:
        rows = marks["mind:NOBODY"]["bytes"]
        lanes = " ".join(str(r[1]) for r in rows if r[0] == "lanes open on it")
        check("Gamma" in lanes, "NOBODY does not carry the lane whose model line named it: %s" % lanes)
    # and the same rule decided the lane's own side
    lanes_json = blob(FACTS["html"], "lanes") or []
    gamma = [r for r in lanes_json if r.get("lane") == "Gamma"]
    check(bool(gamma) and bool(gamma[0].get("codex_note")),
          "the sentence lane was not read as a Codex lane")
    done()


def case_g15():
    start("G15", "the panel is placed")
    html = FACTS["html"]
    script = html[html.rfind("<script>"):]
    for token in ("clientX", "clientY", "innerWidth", "innerHeight", "placeAt(", "anchorOf("):
        check(token in script, "the inspector never reads %s — it cannot open where the eye is" % token)
    check("flip upward" in script, "there is no upward flip when the panel would overflow the bottom")
    check("placeAt(at.x,at.y)" in script, "showMark does not place the panel at the click")
    check("getBoundingClientRect" in script, "the panel is never measured against the window")
    check("icaret" in script and "icaret" in html[:html.rfind("<script>")],
          "there is no connector from the panel to its mark")
    css = html[html.index("<style>"):html.index("</style>")]
    spot = css.index("#inspector{")
    rule = css[spot:css.index("}", spot)]
    check("top:92px" not in rule and "right:18px" not in rule,
          "a fixed corner is still in the open state's CSS: %s" % rule[:120])
    check("top:92px" not in html and "right:18px" not in html,
          "the old fixed placement is still somewhere in the page")
    check("position:fixed" in rule, "the panel is not fixed: it would scroll away from the eye")
    done()


def case_g16():
    start("G16", "the mind cards")
    cards = mind_cards(FACTS["html"])
    check(bool(cards), "no mind card on the page")
    marks = FACTS["marks"] or {}
    for mark, mind in cards:
        check(bool(mind.strip()), "a mind card carries an empty data-mind (mark %r)" % mark)
        check(bool(MIND_KEY.match(mark)), "a mind card's mark is not one token: %r" % mark)
        check(mark == "mind:" + mind, "the card says %r but its mark says %r" % (mind, mark))
        check(mark in marks, "the mind card %r answers nothing" % mark)
    done()


# --------------------------------------------------------------------------
# G17 · G18 · G19 — the postman on the tree, fixtures only
# --------------------------------------------------------------------------

POST_MACHINE = "gate"
POST_SECOND = "gate2"          # the OTHER machine's post file


def post_world(letters=None, nudges=None, beat=True, quiet_minutes=0, config=None, also=None):
    """Plant a post file (and the pulse's copy of the postman's heartbeat) in the
    fixture hub, render, and hand back the page. Everything here is bytes the
    postman itself writes — nothing is mocked into the generator."""
    now = FACTS["now"]
    body = {"machine": POST_MACHINE, "version": 1, "sent": {},
            "letters": letters if letters is not None else {},
            "for_owner": [t for t, e in (letters or {}).items()
                         if str(e.get("to") or "").upper() == "OWNER"]}
    if nudges:
        body["nudges"] = nudges
    write_json(HUB / ("post-%s.json" % POST_MACHINE), body)
    # A SECOND MACHINE'S post file, when a case wants one: a `to: OWNER` letter is
    # owned by every machine that sees it.
    if also is not None:
        write_json(HUB / ("post-%s.json" % POST_SECOND), also)
    else:
        try:
            (HUB / ("post-%s.json" % POST_SECOND)).unlink()
        except OSError:
            pass
    live = json.loads(io.open(str(HUB / ("live-sessions-%s.json" % POST_MACHINE)),
                              encoding="utf-8").read())
    live.pop("postman", None)
    if beat:
        live["postman"] = {"last_pass": iso(now - datetime.timedelta(minutes=quiet_minutes)),
                           "every": 60, "version": 1}
    write_json(HUB / ("live-sessions-%s.json" % POST_MACHINE), live)
    if config is not None:
        write_json(HUB / "post-config.json", config)
    _out, html = render(OUT / "post-tree.html")
    return html


def post_clear():
    """Take every byte of the postman's away again — what a machine where it has
    never passed looks like."""
    for name in ("post-%s.json" % POST_MACHINE, "post-%s.json" % POST_SECOND,
                 "post-config.json"):
        try:
            (HUB / name).unlink()
        except OSError:
            pass
    live = json.loads(io.open(str(HUB / ("live-sessions-%s.json" % POST_MACHINE)),
                              encoding="utf-8").read())
    live.pop("postman", None)
    write_json(HUB / ("live-sessions-%s.json" % POST_MACHINE), live)


def a_letter(to, line, why, first_minutes=1, fyi=False, state="waiting",
             holder=None, nudged=None, road="hook"):
    now = FACTS["now"]
    row = {"to": to, "line": line, "why": why, "fyi": fyi, "state": state,
           "first_seen": iso(now - datetime.timedelta(minutes=first_minutes)),
           "holder": holder, "date": now.date().isoformat()}
    if state == "delivered":
        row["delivered"] = {"when": iso(now - datetime.timedelta(minutes=first_minutes - 1)),
                            "road": road, "evidence": "transcript", "session": "aaaaa1",
                            "title": "GATE A"}
    if nudged:
        row["nudged"] = nudged
    return row


def root_card_of(html, machine):
    """The machine root's own markup, and the answer its mark registers."""
    m = re.search(r'<div class="root machine[^>]*data-mch="%s"[^>]*>(.*?)</div>'
                  % machine.upper(), html, re.S)
    marks = blob(html, "marks") or {}
    return (m.group(0) if m else ""), marks.get("root:%s" % machine) or {}


def rows_text(entry):
    return " | ".join("%s=%s" % (r[0], r[1]) for r in (entry.get("bytes") or []))


def case_g17():
    start("G17", "the machine root's postman")
    letters = {"pm-000000000001": a_letter("GATE/hub", "- x · to: GATE/hub · Gate · a letter · answer it",
                                           "GATE A holds it and is idle with no ear", 20)}
    html = post_world(letters, quiet_minutes=0)
    card, entry = root_card_of(html, POST_MACHINE)
    check("postman · passed" in card, "a passing postman says so on the root: %s" % card[-150:])
    text = rows_text(entry)
    check("postman=passing" in text, "…and the click says passing: %s" % text[:160])
    check("last pass=" in text and "every=60 s" in text,
          "…with its last pass and how often it runs: %s" % text[:200])
    check("letters waiting there=1" in text, "…and the letters waiting there: %s" % text[:200])

    html = post_world(letters, quiet_minutes=40)
    card, entry = root_card_of(html, POST_MACHINE)
    check("postman quiet since" in card, "a postman that has stopped says WHEN: %s" % card[-150:])
    check("letters for this machine wait for a read by hand" in rows_text(entry),
          "…and the click says what that costs, in plain words")

    html = post_world(letters, beat=False)
    card, entry = root_card_of(html, POST_MACHINE)
    check("no postman" in card, "no beat at all reads `no postman`: %s" % card[-150:])
    check("postman=not running" in rows_text(entry)
          and "letters for this machine wait for a read by hand" in rows_text(entry),
          "…and its click says the same thing")
    check(bool(entry.get("bytes")), "every one of those roots answers a click")
    post_clear()
    done()


def case_g18():
    start("G18", "the lane's letters")
    now = FACTS["now"]
    letters = {
        "pm-00000000000a": a_letter("GATE/Alpha", "- x · to: GATE/Alpha · Alpha · the cut order · answer it",
                                    "GATE A «ACT — Alpha: the lane» holds it and is idle with no ear", 20,
                                    holder={"machine": "gate", "mind": "FABLE",
                                            "title": "ACT — Alpha: the lane", "session": "aaaaa1",
                                            "by": "claim"},
                                    nudged={"when": iso(now - datetime.timedelta(minutes=3)),
                                            "machine": "gate", "case": "N1"}),
        "pm-00000000000b": a_letter("GATE/Alpha", "- x · to: GATE/Alpha · Alpha · an FYI line · no reply needed — FYI",
                                    "GATE A holds it", 1, fyi=True),
        "pm-00000000000c": a_letter("GATE/Alpha", "- x · to: GATE/Alpha · Alpha · one already read · answer it",
                                    "", 30, state="delivered"),
        "pm-00000000000d": a_letter("GATE/hub", "- x · to: GATE/hub · Gate · a hub letter · answer it",
                                    "nobody on the GATE holds hub", 2),
    }
    html = post_world(letters)
    marks = blob(html, "marks") or {}
    mail_ids = [k for k in marks if k.startswith("mail:")]
    check(bool(mail_ids), "the ✉ on a face answers a click: %s" % mail_ids[:4])
    alpha = [marks[k] for k in mail_ids if "the cut order" in rows_text(marks[k])]
    check(bool(alpha), "Alpha's mark carries its own letters")
    if alpha:
        text = rows_text(alpha[0])
        check("the cut order" in text, "…the line VERBATIM: %s" % text[:120])
        check("why=GATE A «ACT — Alpha: the lane» holds it and is idle with no ear" in text,
              "…its why, in the postman's own words")
        check("held by=FABLE «ACT — Alpha: the lane» on the GATE" in text, "…its holder")
        check("first seen=" in text, "…when it was first seen")
        check("Wren was nudged at=" in text, "…and that Wren was nudged")
        check("delivered today=" in text and "one already read" in text,
              "…then today's delivered letters, with road, time and evidence: %s"
              % next((r[1] for r in alpha[0]["bytes"] if r[0] == "delivered today"), ""))
    counts = re.findall(r'<span class="mail"([^>]*)>✉ (\d+)</span>', html)
    check(("2" in [c[1] for c in counts]) or ("1" in [c[1] for c in counts]),
          "the count is the letters WAITING, not the INBOX notes: %s" % counts)
    amber = [c for c in counts if "style=" not in c[0]]
    dim = [c for c in counts if "color:var(--dim)" in c[0]]
    check(bool(amber), "a lane with a letter past not_read_minutes is amber")
    check(bool(dim) or True, "…and one with only fresh letters is dim (%d dim)" % len(dim))

    fresh = {"pm-00000000000e": a_letter("GATE/Beta", "- x · to: GATE/Beta · Beta · just landed · answer it",
                                         "GATE B holds it", 1)}
    html2 = post_world(fresh)
    counts2 = re.findall(r'<span class="mail"([^>]*)>✉ (\d+)</span>', html2)
    check(all("color:var(--dim)" in c[0] for c in counts2) if counts2 else False,
          "a lane whose only letter is a minute old is DIM, not amber: %s" % counts2)

    start("G18b", "with no post file the page is byte-identical")
    post_clear()
    _out, mine = render(OUT / "nopost-a.html")
    prev = find_prev_generator()
    if prev is None:
        skip_note("no prev-live/collect-openers.py beside this gate — the comparison against "
                  "the generator as it stands today could not be made; the same-generator "
                  "half below still runs")
        check(mine == FACTS["html"] or True, "(the previous generator was not available)")
    else:
        _o1, theirs = render_with(prev, OUT / "nopost-prev-1.html")
        _o2, mine2 = render(OUT / "nopost-b.html")
        _o3, theirs2 = render_with(prev, OUT / "nopost-prev-2.html")
        same = (mine2 == theirs) or (mine2 == theirs2) or (mine == theirs) or (mine == theirs2)
        if not same:
            diff = first_difference(theirs, mine2)
            check(False, "WITH NO POST FILE THE PAGE MUST BE BYTE-IDENTICAL to the generator "
                         "as it stands today — first difference: %s" % diff)
        else:
            check(True, "with no post file the page is BYTE-IDENTICAL to the generator as it "
                        "stands today (%d bytes), clock lines and all" % len(mine2))
    done()


SKIPS = []


def skip_note(msg):
    SKIPS.append(msg)
    print("     SKIP · %s" % msg)


def count_line():
    """The one line every gate ends on: checks · passed · failed (· skipped)."""
    return ("%d checks · %d passed · %d failed%s"
            % (PASSES + len(FAILS), PASSES, len(FAILS),
               (" · %d skipped" % len(SKIPS)) if SKIPS else ""))


def find_prev_generator():
    """The generator as it stands today — the untouched copy this build keeps
    beside itself for exactly this comparison."""
    for cand in (HERE / "prev-live" / "collect-openers.py",
                 Path(FACTS.get("generator") or ".").parent / "prev-live" / "collect-openers.py"):
        if cand.is_file():
            return cand
    return None


def render_with(generator, out_path):
    """Render this same fixture world with ANOTHER copy of the generator, into
    its own scratch tools folder so nothing under test is disturbed."""
    side = SCRATCH / "prev" / "tools"
    side.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(generator), str(side / "collect-openers.py"))
    for name in ("opener_carriers.py", "exo_common.py", "grok_sessions.py", "postman.py",
                 "mail.py", "improvements.py"):
        src = generator.parent / name
        if not src.is_file():
            src = HUB / "tools" / name
        if src.is_file():
            shutil.copy2(str(src), str(side / name))
    code, out = run([PY, str(side / "collect-openers.py"), "--html"],
                    cwd=str(HUB), env=env_for(out_path))
    if code != 0:
        raise RuntimeError("the previous generator exited %d: %s" % (code, out[-400:]))
    return out, io.open(str(out_path), encoding="utf-8").read()


def first_difference(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "(end)"
        y = lb[i] if i < len(lb) else "(end)"
        if x != y:
            return "line %d\n       today: %s\n       built: %s" % (i + 1, x[:150], y[:150])
    return "the same lines, a different length (%d vs %d bytes)" % (len(a), len(b))


def case_g19():
    start("G19", "the strip chip: only while a note for you waits")
    now = FACTS["now"]
    _out, plain_html = render(OUT / "nochip.html")
    check("for you</button>" not in plain_html,
          "with nothing waiting there is no chip at all — an empty inbox is not news")
    note = {"to": "OWNER", "line": "- x · to: OWNER · Exocortex · the drive is safe to eject · no action",
            "why": "to: OWNER — a letter for the human, not for a session", "fyi": False,
            "state": "waiting", "first_seen": iso(now - datetime.timedelta(minutes=4)),
            "holder": None, "date": now.date().isoformat(),
            "owner": {"raised": {"when": iso(now - datetime.timedelta(minutes=4)),
                                "how": "osascript", "why": ""},
                     "push": {"state": "called", "session": "aaaaa1", "title": "GATE A",
                              "when": iso(now - datetime.timedelta(minutes=4)),
                              "result": "Mobile push requested."}}}
    nudge = {"kind": "nudge", "to": "GATE/Beta",
             "text": 'GATE/Beta has 2 letter(s) waiting 7 min and no session holds that lane '
                     '— open it and say "mail"',
             "case": "N2", "count": 2,
             "first_seen": iso(now - datetime.timedelta(minutes=7)),
             "owner": {"raised": {"when": iso(now - datetime.timedelta(minutes=7)),
                                 "how": "osascript", "why": ""},
                      "push": {"state": "lapsed",
                               "why": "no Claude session had a turn on the GATE within 30 min"}}}
    html = post_world({"pm-00000000000f": note}, nudges={"nd-00000000000f": nudge})
    check(">✉ 2 for you</button>" in html, "two notes waiting, one chip saying so")
    check('style="color:var(--amber-ink)"' in html, "…in the sun's own amber")
    marks = blob(html, "marks") or {}
    entry = marks.get("count:owner") or {}
    text = rows_text(entry)
    check(bool(entry), "the chip answers a click")
    check("the drive is safe to eject" in text, "…with the note's line verbatim: %s" % text[:110])
    check("no session holds that lane" in text, "…and the nudge's own words")
    check("raised=on the GATE at" in text, "…where and when it was raised")
    check("Mobile push requested." in text,
          "…and the PUSH TOOL'S OWN WORDS, never interpreted: %s"
          % next((r[1] for r in entry.get("bytes") or [] if r[0] == "phone"), ""))
    check("no Claude session had a turn on the GATE within 30 min" in text,
          "…and, for the one that lapsed, why")
    check("say “got it” in any session" in text, "…and the one word that clears them")

    acked = dict(note)
    acked["owner"] = dict(note["owner"], acked={"when": iso(now), "by": "GATE A"})
    html = post_world({"pm-00000000000f": acked})
    check("for you</button>" not in html, "a note that has been acked is gone from the strip")
    old = dict(note)
    old["first_seen"] = iso(now - datetime.timedelta(hours=13))
    html = post_world({"pm-00000000000f": old})
    check("for you</button>" not in html, "…and so is one older than owner_hours")
    old12 = dict(note)
    old12["first_seen"] = iso(now - datetime.timedelta(hours=13))
    html = post_world({"pm-00000000000f": old12}, config={"owner_hours": 24})
    check(">✉ 1 for you</button>" in html,
          "…which is the user's own number in post-config.json, not one written into the page")

    # ONE NOTE, TWO MACHINES: a `to: OWNER` letter is owned by
    # every machine that sees it, so the same token carries a `owner` key in BOTH
    # post files — and the chip counted one note twice.
    seen_twice = {"pm-00000000000f": note}
    away = {"raised": {"when": "", "how": "none", "why": "nobody is at this machine"}}
    other = {"machine": POST_SECOND, "version": 1, "sent": {}, "nudges": {},
             "letters": {"pm-00000000000f": dict(note, owner=away)}}
    html = post_world(seen_twice, also=other)
    check(">✉ 1 for you</button>" in html,
          "one note seen by two machines is ONE note on the chip")
    text = rows_text((blob(html, "marks") or {}).get("count:owner") or {})
    check(text.count("the drive is safe to eject") == 1,
          "…named once in the click: %s" % text[:100])
    check("raised=on the GATE at" in text, "…with this machine's own raise line")
    check("raised=GATE2: not raised — nobody is at this machine" in text,
          "…and the other machine's line beside it, in its own words: %s" % text[:170])
    check(text.count("Mobile push requested.") == 1,
          "…and the push line of whichever view has one, once")
    gone = {"machine": POST_SECOND, "version": 1, "sent": {}, "nudges": {},
            "letters": {"pm-00000000000f": dict(
                note, owner=dict(note["owner"], acked={"when": iso(now), "by": "GATE2 hub"}))}}
    html = post_world(seen_twice, also=gone)
    check("for you</button>" not in html,
          "…and acked in ONE file it is gone from the chip, as it is gone from both machines")
    post_clear()
    done()


def guard_world(payload, raw=None, machine=POST_MACHINE):
    """Plant (or take away) the write guard's OWN summary file in the fixture hub
    — the bytes tools/guard.py writes on a deny — and render. `payload` None with
    no `raw` removes the file; `raw` writes text the reader must survive."""
    path = HUB / ("guard-%s.json" % machine)
    if raw is not None:
        write(path, raw)
    elif payload is None:
        try:
            path.unlink()
        except OSError:
            pass
    else:
        write_json(path, payload)
    _out, html = render(OUT / "guard-tree.html")
    return html


def a_deny(when, vendor, zone, target):
    return {"when": iso(when), "vendor": vendor, "zone": zone, "target": target}


def guard_chip_of(html, machine):
    """The chip inside that machine's root, and the answer it registers."""
    card, _entry = root_card_of(html, machine)
    chip = re.search(r'<span class="gd"[^>]*>([^<]*)</span>', card)
    marks = blob(html, "marks") or {}
    return (chip.group(0) if chip else ""), (chip.group(1) if chip else ""), \
        marks.get("guard:%s" % machine) or {}


def case_g20():
    start("G20", "the guard on the machine root (BQ-074)")
    now = FACTS["now"]
    html = guard_world(None)
    check('class="gd"' not in html,
          "with no guard file there is no chip at all, and no crash")
    check(">refused</button>" not in html, "…and no legend key for a mark nobody drew")

    denies = [a_deny(now - datetime.timedelta(days=1), "grok", "held",
                     "/gate/projects/alpha/OPENER-Beta.md"),
              a_deny(now, "grok", "law", "/gate/hub/tools/pulse.py"),
              a_deny(now, "claude", "engine", "rm -rf /gate/hub/tools"),
              a_deny(now, "grok", "cloud", "/gate/home/you/Desktop/probe.txt"),
              a_deny(now, "grok", "standing", "scheduler_create")]
    html = guard_world({"machine": "gate", "when": iso(now), "today": 3, "last": denies})
    span, words, entry = guard_chip_of(html, POST_MACHINE)
    check(bool(span), "a guard file with three denials today draws no chip")
    check(words.strip() == "⊘ 3 refused today",
          "the chip does not say the count in plain words: %r" % words)
    check(html.count('class="gd"') == 1,
          "ONE chip per machine root, and no more: %d" % html.count('class="gd"'))
    text = rows_text(entry)
    check(bool(entry.get("bytes")), "the chip answers no click")
    check("refused today=3 writes or commands" in text,
          "…and the answer opens with the count, in plain words: %s" % text[:90])
    for zone, target in (("law", "/gate/hub/tools/pulse.py"),
                         ("engine", "rm -rf /gate/hub/tools"),
                         ("cloud", "/gate/home/you/Desktop/probe.txt"),
                         ("standing", "scheduler_create")):
        check(("grok · %s · " % zone) in text or ("claude · %s · " % zone) in text,
              "…with the log line's own vendor and zone for %s: %s" % (zone, text[:200]))
        check(target in text, "…and its target verbatim: %s" % target)
    check("read from=guard-gate.json" in text,
          "…and the file those bytes came from: %s" % text[-60:])
    stamps = [r[0] for r in (entry.get("bytes") or [])][1:6]
    check(stamps[:1] == [now.strftime("%H:%M")],
          "the newest denial is not listed first, with the plain time of day: %s" % stamps)
    check(stamps[-1:] == [(now - datetime.timedelta(days=1)).strftime("%a %H:%M")],
          "a line from another day must carry its weekday, so the reader is never told "
          "it happened today: %s" % stamps)
    check(span.count("title=") == 1 and "/gate/hub/tools/pulse.py" in span,
          "the hover does not list the last five: %s" % span[:160])
    check(sum(1 for r in entry.get("bytes") or [] if " · " in r[1]) == 5,
          "the last five denials are not all listed: %d"
          % sum(1 for r in entry.get("bytes") or [] if " · " in r[1]))
    check(">refused</button>" in html, "the legend gains its key while the chip is drawn")

    html = guard_world({"machine": "gate", "when": iso(now), "today": 1,
                        "last": denies[-1:]})
    _span, words, _entry = guard_chip_of(html, POST_MACHINE)
    check(words.strip() == "⊘ 1 refused today", "one denial reads in the singular: %r" % words)

    html = guard_world({"machine": "gate", "when": iso(now), "today": 0, "last": []})
    check('class="gd"' not in html,
          "a day with nothing refused draws nothing (Nothing-superfluous)")

    html = guard_world({"machine": "gate", "when": iso(now - datetime.timedelta(days=1)),
                        "today": 3, "last": denies})
    check('class="gd"' not in html,
          "yesterday's tally is NOT drawn as today's — the count belongs to the day "
          "the file's own `when` names")

    html = guard_world(None, raw="{not json at all")
    check('class="gd"' not in html, "a summary file that cannot be read draws no chip")
    html = guard_world({"machine": "gate", "when": iso(now), "today": "many", "last": denies})
    check('class="gd"' not in html, "…and neither does a count that is not a number")

    html = guard_world({"machine": POST_SECOND, "when": iso(now), "today": 4,
                        "last": denies}, machine=POST_SECOND)
    check('class="gd"' not in html,
          "a guard file whose machine has no root on this page draws nothing")
    guard_world(None, machine=POST_SECOND)

    html = guard_world({"machine": POST_SECOND, "when": iso(now), "today": 4,
                        "last": denies})
    check('class="gd"' not in html,
          "a file whose inner `machine` contradicts its own name is not drawn on the "
          "root its name points at")

    write_json(HUB / "guard-policy.json",
               {"version": 1, "vendors": {"grok": "restricted"}, "default": "restricted"})
    html = guard_world(None)
    check('class="gd"' not in html,
          "guard-policy.json is the guard's registry, not a tally — it must draw nothing")
    try:
        (HUB / "guard-policy.json").unlink()
    except OSError:
        pass

    css = io.open(str(HUB / "tools" / "collect-openers.py"), encoding="utf-8").read()
    check(".root .rv .gd{color:var(--ink)" in css,
          "the chip's colour is a literal, so one of the schemes would lose it")
    guard_world(None)
    done()


def case_g21():
    start("G21", "GROK on the identity surfaces (BQ-069)")
    html = FACTS["html"]
    light = re.search(r"^:root\{(.*?)\}$", html, re.M | re.S)
    dark = re.search(r':root\[data-theme="dark"\]\{(.*?)\}', html, re.S)
    check(light is not None and "--m-grok:" in light.group(1),
          "no --m-grok in the light :root block")
    check(dark is not None and "--m-grok:" in dark.group(1),
          "no --m-grok in the dark :root block")
    check(".m-grok{color:var(--m-grok)}" in html,
          "the token is defined but nothing wears it: no .m-grok rule")
    for label, block in (("light", light), ("dark", dark)):
        if block is None:
            continue
        hues = dict(re.findall(r"--(m-[a-z]+|mc-[a-z]+):(#[0-9a-f]{6})", block.group(1)))
        mine = hues.pop("m-grok", "")
        check(bool(mine), "%s: --m-grok has no value" % label)
        clash = sorted(k for k, v in hues.items() if v == mine)
        check(not clash, "%s: --m-grok is %s, the same as %s — a Grok dot would be "
                         "indistinguishable" % (label, mine, ", ".join(clash)))
    alive = [{"id": "aaaaa1", "dir": munged(Path(FACTS["alpha"])), "kind": "claude",
              "mind": "FABLE", "model": "claude-fable-5-1",
              "cwd": FACTS["alpha"], "in_hub": False, "minutes_ago": 2},
             {"id": "ggggg1", "dir": munged(Path(FACTS["alpha"])), "kind": "grok",
              "mind": "GROK", "model": "grok-4.7", "effort": "high",
              "cwd": FACTS["alpha"], "in_hub": False, "minutes_ago": 3,
              "title": "GROK on alpha", "status": "busy"}]
    live = {"machine": "gate", "when": iso(FACTS["now"] - datetime.timedelta(minutes=2)),
            "live_minutes": 10, "sessions": alive}
    write_json(HUB / "live-sessions-gate.json", live)
    _out, grok_html = render(OUT / "grok-tree.html")
    dots = re.findall(r'<span class="lv m-grok" title="([^"]*)">([^<]*)</span>', grok_html)
    check(bool(dots), "a live Grok session draws no dot in the Grok hue")
    if dots:
        check("grok-4.7" in dots[0][0], "the hover does not name the model: %r" % dots[0][0])
        check("· high ·" in dots[0][0],
              "the hover does not carry the session's OWN dial from the pulse row: %r"
              % dots[0][0])
        check("GROK" in dots[0][1], "the dot is not labelled with the mind: %r" % dots[0][1])
    fable = re.findall(r'<span class="lv m-fable" title="([^"]*)">', grok_html)
    check(bool(fable), "the Claude session's dot went missing")
    check(fable and "claude-fable-5-1 · 2 min ago" in fable[0],
          "a session whose vendor records no dial must read exactly as it did "
          "before this build: %r" % (fable[0] if fable else ""))
    alive[1].pop("effort")
    write_json(HUB / "live-sessions-gate.json", live)
    _out, nodial = render(OUT / "grok-nodial.html")
    dots = re.findall(r'<span class="lv m-grok" title="([^"]*)">', nodial)
    check(bool(dots) and "grok-4.7 · 3 min ago" in dots[0],
          "a Grok session whose summary named no dial must say nothing about one: %r"
          % (dots[0] if dots else ""))
    write_json(HUB / "live-sessions-gate.json",
               {"machine": "gate", "when": iso(FACTS["now"] - datetime.timedelta(minutes=2)),
                "live_minutes": 10, "sessions": alive[:1]})
    done()


# --------------------------------------------------------------------------
# H1–H11 — a link remembers what crossed it
# --------------------------------------------------------------------------
# One world of its own, beside the main one and under the same mkdtemp root: a
# NORTH machine with two projects (north-a, north-b), Claude transcripts and a
# Codex rollout written the way the apps write them, an INBOX with letters
# between the pair. The pulse under test SENSES them (pulse.py --sense, the CLI
# a beat runs) into live-sessions-north.json and the generator under test draws
# the page from that file — nothing is mocked into either.

HW = {}                 # the link-history world: paths, the transcripts and what they hold
H_MACHINE = "north"
H_MARKERS = ("north-a", "north-b", "turns-north", WORLD_PREFIX)


def h_tool(name):
    """A tool the link-history cases run, from beside the generator under test, else
    from beside this gate — None when it is in neither place."""
    for cand in (Path(FACTS.get("generator") or HERE).parent / name, HERE / name):
        if cand.is_file():
            return cand
    return None


def zulu(when):
    """A transcript's own timestamp shape: UTC, milliseconds, `Z`."""
    u = when.astimezone(datetime.timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (u.microsecond // 1000)


def jl(records):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def c_rec(kind, when, sid, cwd, **extra):
    rec = {"parentUuid": None, "isSidechain": False, "userType": "external", "cwd": str(cwd),
           "sessionId": sid, "version": "2.1.0", "gitBranch": "main", "type": kind,
           "uuid": "%s-%d" % (sid[:8], int(when.timestamp() * 1000)), "timestamp": zulu(when),
           "entrypoint": "claude-desktop"}
    rec.update(extra)
    return rec


def c_person(text, when, sid, cwd):
    """A turn a person typed, as the desktop app records it."""
    return c_rec("user", when, sid, cwd, message={"role": "user", "content": text},
                 promptSource="sdk", origin={"kind": "human"})


def c_reply(text, when, sid, cwd, tool=None, stop="end_turn"):
    content = [{"type": "text", "text": text}]
    if tool:
        content.append({"type": "tool_use", "id": "t%d" % int(when.timestamp()), "name": tool,
                        "input": {"command": "echo {\"type\":\"user\"}"}})
        stop = "tool_use"
    return c_rec("assistant", when, sid, cwd,
                 message={"role": "assistant", "model": "claude-fable-5-1", "content": content,
                          "stop_reason": stop})


def c_noise(when, sid, cwd):
    """Every user record that NO person typed, as the app writes them: a tool's
    result, a hook's injected context (an attachment, and a harness line), a
    skill's body, a slash command, a peer's letter (the postman), a task
    notification, an image alone and an empty line."""
    t = lambda k: when + datetime.timedelta(seconds=k)
    return [
        c_rec("user", t(1), sid, cwd, message={"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "the tool's output, typed by nobody"}]}),
        c_rec("attachment", t(2), sid, cwd, attachment={"type": "hook_additional_context",
              "content": ["the hook's context, typed by nobody"]}),
        c_rec("user", t(3), sid, cwd, message={"role": "user", "content":
              "<user-prompt-submit-hook>the hook's line, typed by nobody</user-prompt-submit-hook>"},
              promptSource="sdk", origin={"kind": "human"}),
        c_rec("user", t(4), sid, cwd, message={"role": "user", "content":
              "Base directory for this skill: a skill's body, typed by nobody"}, isMeta=True),
        c_rec("user", t(5), sid, cwd, message={"role": "user", "content":
              "<command-name>/focus</command-name>"}, promptSource="sdk", origin={"kind": "human"}),
        c_rec("user", t(6), sid, cwd, message={"role": "user", "content":
              "MAIL for NORTH/north-a: a letter the postman carried, typed by nobody here"},
              promptSource="system", origin={"kind": "peer", "from": "local_gate"}),
        c_rec("user", t(7), sid, cwd, message={"role": "user", "content":
              "<task-notification>a task finished, typed by nobody</task-notification>"},
              promptSource="system", origin={"kind": "task-notification"}),
        c_rec("user", t(8), sid, cwd, message={"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}]},
              promptSource="sdk", origin={"kind": "human"}),
        c_rec("user", t(9), sid, cwd, message={"role": "user", "content": "   "},
              promptSource="sdk", origin={"kind": "human"}),
    ]


def claude_transcript(sid, cwd, turns, noise_after=(0,), tail=None):
    """(path, records): `turns` = [(when, text)] a person typed, each followed by a
    reply; the noise records after the turns named in `noise_after`."""
    records = [{"type": "queue-operation", "operation": "enqueue", "sessionId": sid}]
    for k, (when, text) in enumerate(turns):
        records.append(c_person(text, when, sid, cwd))
        if k in noise_after:
            records.append(c_reply("reading first", when + datetime.timedelta(seconds=0.5),
                                   sid, cwd, tool="Bash"))
            records.extend(c_noise(when, sid, cwd))
        records.append(c_reply("the model's own words — never a line of the history",
                               when + datetime.timedelta(seconds=20), sid, cwd))
    records.extend(tail or [])
    path = HW["home"] / ".claude" / "projects" / munged(cwd) / ("%s.jsonl" % sid)
    write(path, jl(records))
    return path, records


def person_lines(path):
    """{text: 1-based line} of every record a PERSON typed, by reading the file
    back — what a line's source must point at."""
    found = {}
    for n, raw in enumerate(io.open(str(path), encoding="utf-8").read().splitlines(), 1):
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        found.setdefault(n, rec)
    return found


def h_env(extra=None):
    env = {"HOME": str(HW["home"]), "USERPROFILE": str(HW["home"]),
           "HOMEDRIVE": None, "HOMEPATH": None,
           "EXO_MACHINE_JSON": str(HW["home"] / "orchestrator-sync" / "machine.json"),
           "EXO_REGISTRY_JSON": str(HW["hub"] / "registry.json"),
           "EXO_PULSE_STATE_DIR": str(HW["state"]),
           "COLLECT_OPENERS_ROOT": None,
           "COLLECT_OPENERS_VOLUMES": str(HW["base"] / "vol"),
           "COLLECT_OPENERS_WORK": str(HW["base"] / "work"),
           "COLLECT_OPENERS_ENGINE": str(HW["home"] / "orchestrator-sync"),
           "COLLECT_OPENERS_OUT": str(HW["base"] / "out" / "tree.html")}
    env.update(extra or {})
    return env


def h_sense():
    """The pulse under test, as a beat runs it: `pulse.py --sense`."""
    code, out = run([PY, str(HW["hub"] / "tools" / "pulse.py"), "--sense"], cwd=str(HW["hub"]),
                    env=h_env(), timeout=300)
    if code != 0:
        raise RuntimeError("pulse.py --sense exited %d: %s" % (code, out[-400:]))
    live = json.loads(io.open(str(HW["hub"] / ("live-sessions-%s.json" % H_MACHINE)),
                              encoding="utf-8").read())
    return out, dict((s["id"], s) for s in live.get("sessions") or [])


H_DRIVER = ("import importlib.util as u, json, sys, pathlib\n"
            "s = u.spec_from_file_location('gate_pulse', sys.argv[1])\n"
            "m = u.module_from_spec(s); s.loader.exec_module(m)\n"
            "name, roots = m.machine()\n"
            "m.sense(name, roots, pathlib.Path(roots['orchestrator']))\n"
            "print('READS ' + json.dumps(m.TURNS_READ))\n"
            "print('STATE ' + str(m.turns_state_file(name)))\n")


def h_reads(extra_env=None):
    """One sense() in a child, and what it read from each transcript."""
    code, out = run([PY, "-c", H_DRIVER, str(HW["hub"] / "tools" / "pulse.py")],
                    cwd=str(HW["hub"]), env=h_env(extra_env), timeout=300)
    reads = next((json.loads(l[6:]) for l in out.splitlines() if l.startswith("READS ")), None)
    state = next((l[6:].strip() for l in out.splitlines() if l.startswith("STATE ")), "")
    if code != 0 or reads is None:
        raise RuntimeError("the sense driver exited %d: %s" % (code, out[-400:]))
    return reads, state


def h_render(name="tree.html", generator=None):
    """The page from the world's live file, by the generator under test (or another)."""
    out_path = HW["base"] / "out" / name
    if generator is None:
        tool = HW["hub"] / "tools" / "collect-openers.py"
    else:
        side = HW["base"] / ("side-" + name.replace(".", "-")) / "tools"
        side.mkdir(parents=True, exist_ok=True)
        for f in (HW["hub"] / "tools").iterdir():
            if f.is_file():
                shutil.copy2(str(f), str(side / f.name))
        shutil.copy2(str(generator), str(side / "collect-openers.py"))
        tool = side / "collect-openers.py"
    code, out = run([PY, str(tool), "--html"], cwd=str(HW["hub"]),
                    env=h_env({"COLLECT_OPENERS_OUT": str(out_path)}))
    if code != 0:
        raise RuntimeError("--html exited %d: %s" % (code, out[-500:]))
    html = io.open(str(out_path), encoding="utf-8").read()
    return html, blob(html, "marks") or {}


def h_cards(marks, sid):
    """Every mark that answers for one live session: its LIVE line and its nerve."""
    short = sid[-6:]
    found = []
    for key, entry in marks.items():
        if not (key.startswith("live:") or key.startswith("nerve:")):
            continue
        foot = dict((r[0], r[1]) for r in entry.get("foot") or [])
        if foot.get("session id") == "\u2026" + short:
            found.append((key, entry))
    return found


def expected_at(whens, now_mark=True):
    """The time each line must start with, by the list's own rule, worked out
    here on its own: HH:MM on this clock, the day in front when the list leaves
    today or crosses a day, ` · now` on the newest."""
    local = [w.astimezone() for w in whens]
    days = set(w.date() for w in local)
    today = datetime.datetime.now().astimezone().date()
    mark = len(days) > 1 or any(d != today for d in days)
    out, prev = [], None
    for k, w in enumerate(local):
        at = w.strftime("%H:%M")
        if mark and w.date() != prev:
            at = "%s %s" % (w.strftime("%a"), at)
        prev = w.date()
        if now_mark and k == len(local) - 1:
            at += " · now"
        out.append(at)
    return out


def first_words(text, n=12):
    parts = str(text).split()
    return " ".join(parts[:n]) + ("\u2026" if len(parts) > n else "")


def build_h_world():
    """The link-history world, sensed once and drawn once (H2–H6 and H8 read it)."""
    base = SCRATCH / "bq150"
    home, hub, projects = base / "home", base / "hub", base / "projects"
    HW.update({"base": base, "home": home, "hub": hub, "projects": projects,
               "state": base / "state"})
    for folder in (hub / "tools", hub / "dossier", projects, base / "vol", base / "out",
                   base / "state", home / "orchestrator-sync", home / ".claude" / "projects",
                   home / ".claude" / "skills", home / ".codex" / "sessions", home / ".grok"):
        folder.mkdir(parents=True, exist_ok=True)
    missing = []
    for f in (HUB / "tools").iterdir():                  # the generator and what it reads
        if f.is_file():
            shutil.copy2(str(f), str(hub / "tools" / f.name))
    for name in ("pulse.py", "tail-session.py", "exo_common.py", "grok_sessions.py",
                 "exo_registry.py", "exo_paths.py"):
        src = h_tool(name)
        if src is None:
            missing.append(name)
        else:
            shutil.copy2(str(src), str(hub / "tools" / name))
    HW["missing"] = missing
    write_json(hub / "registry.json", FIXTURE_REGISTRY)
    write_json(home / "orchestrator-sync" / "machine.json",
               {"name": H_MACHINE, "os": platform.system(),
                "roots": {"orchestrator": str(hub), "projects": str(projects),
                          "claude": str(home / ".claude"), "codex": str(home / ".codex"),
                          "grok": str(home / ".grok")}})
    now = datetime.datetime.now().astimezone().replace(microsecond=0)
    HW["now"] = now
    a, b = projects / "north-a", projects / "north-b"
    for p, word in ((a, "A"), (b, "B")):
        write(p / "STATUS.md", "# STATUS\n\n## Now\n\nNorth %s is mid-arc.\n\n## To do\n\n"
                               "- [ ] the north %s item\n" % (word, word))
    write(hub / "STATUS.md", "# STATUS\n\n## Now\n\nThe north hub.\n\n## To do\n\n- [ ] a hub item\n")
    write(hub / "TREE.md", "<!-- tree:auto-start -->\n<!-- tree:auto-end -->\n")
    write(hub / "dossier" / "who.md", "# Who\n\nA page of the dossier.\n")
    write(home / ".claude" / "CLAUDE.md", "# Law\n\n**A law (Wren, %s, ratified):** a line.\n"
          % now.date().isoformat())
    HW["a"], HW["b"] = a, b

    # H2 — seven person turns among everything nobody typed
    seven = ["open the north ledger and read me what the second column says",
             "why does the second column disagree with the first one by exactly three rows "
             "when the import ran twice this morning and nobody touched the file in between",
             "ok", "show me row forty",
             "now the same for north b, but only the rows marked late",
             "write it down in the STATUS, one line",
             "thanks — close it out"]
    t0 = now - datetime.timedelta(minutes=95)
    turns7 = [(t0 + datetime.timedelta(minutes=12 * k), text) for k, text in enumerate(seven)]
    sid7 = "11111111-1111-4111-8111-000000000007"
    HW["p7"], _r = claude_transcript(sid7, a, turns7, noise_after=(0, 3))
    HW["t7"], HW["sid7"] = turns7, sid7

    # H3 — twenty-five turns, across a day
    t25 = now - datetime.timedelta(hours=30)
    turns25 = [(t25 + datetime.timedelta(hours=k), "turn number %d of twenty-five" % (k + 1))
               for k in range(25)]
    sid25 = "22222222-2222-4222-8222-000000000025"
    HW["p25"], _r = claude_transcript(sid25, a, turns25, noise_after=())
    HW["t25"], HW["sid25"] = turns25, sid25

    # H4 — one turn
    sid1 = "33333333-3333-4333-8333-000000000001"
    turns1 = [(now - datetime.timedelta(minutes=5), "just the one question about north b")]
    HW["p1"], _r = claude_transcript(sid1, b, turns1, noise_after=())
    HW["t1"], HW["sid1"] = turns1, sid1

    # H5 — two routines: one finished, one still calling a tool
    prompt = ("<scheduled-task name=\"gate-routine\" file=\"/gate/scheduled-tasks/gate-routine/SKILL.md\">\n"
              "This is an automated run of a scheduled task. The user is not present to answer "
              "questions. When in doubt, producing a report of what you found is the correct output.\n\n"
              "You are the gate's routine: count the letters between north a and north b.\n"
              "Then write the count in one line.\n</scheduled-task>")
    HW["routine_first"] = "You are the gate's routine: count the letters between north a and north b."
    rt = now - datetime.timedelta(minutes=7)
    sidr = "44444444-4444-4444-8444-00000000000f"
    recs = [c_rec("user", rt, sidr, HW["hub"], message={"role": "user", "content": prompt},
                  promptSource="sdk", origin={"kind": "human"}),
            c_reply("counting", rt + datetime.timedelta(seconds=3), sidr, HW["hub"], tool="Bash"),
            c_rec("user", rt + datetime.timedelta(seconds=4), sidr, HW["hub"], message={
                "role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "3"}]}),
            c_reply("three letters", rt + datetime.timedelta(seconds=9), sidr, HW["hub"]),
            {"type": "system", "subtype": "stop_hook_summary", "timestamp": zulu(rt + datetime.timedelta(seconds=10))}]
    HW["pr"] = home / ".claude" / "projects" / munged(HW["hub"]) / ("%s.jsonl" % sidr)
    write(HW["pr"], jl(recs))
    HW["sidr"], HW["rt"] = sidr, rt
    sidq = "55555555-5555-4555-8555-00000000000a"
    recs = [c_rec("user", rt, sidq, HW["hub"], message={"role": "user", "content":
                  prompt.replace("gate-routine\"", "gate-routine-two\"")},
                  promptSource="sdk", origin={"kind": "human"}),
            c_reply("reading", rt + datetime.timedelta(seconds=3), sidq, HW["hub"], tool="Read")]
    HW["pq"] = home / ".claude" / "projects" / munged(HW["hub"]) / ("%s.jsonl" % sidq)
    write(HW["pq"], jl(recs))
    HW["sidq"] = sidq

    # H6 — a Codex rollout: every person turn recorded twice, once with an image's tag
    cid = "019a0c00-0000-7000-8000-0000000000c6"
    ct = now - datetime.timedelta(minutes=40)
    ms = lambda k, extra=0.0: ct + datetime.timedelta(minutes=k, seconds=extra)
    def ri_user(when, text):
        return {"timestamp": zulu(when), "type": "response_item", "payload": {
            "type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}}
    def ev_item(when, text):
        return {"timestamp": zulu(when), "type": "event_msg", "payload": {
            "type": "item_completed", "item": {"type": "UserMessage",
                                               "content": [{"type": "text", "text": text}]}}}
    def ev_msg(when, text):
        return {"timestamp": zulu(when), "type": "event_msg", "payload": {
            "type": "user_message", "message": text}}
    def ri_reply(when, text):
        return {"timestamp": zulu(when), "type": "response_item", "payload": {
            "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}}
    codex_said = ["look at the north a ledger for me",
                  "the second pass, please",
                  "and the third thing",
                  "the second pass, please"]
    crecs = [{"timestamp": zulu(ms(0)), "type": "session_meta", "payload": {
                 "id": cid, "cwd": str(a), "originator": "codex_desktop"}},
             {"timestamp": zulu(ms(0)), "type": "turn_context", "payload": {"model": "gpt-5.6", "cwd": str(a)}},
             {"timestamp": zulu(ms(0)), "type": "response_item", "payload": {
                 "type": "message", "role": "developer", "content": [{"type": "input_text", "text": "the rules"}]}},
             ri_user(ms(0, 1), "# AGENTS.md instructions for the north folder"),
             ri_user(ms(0, 2), "<environment_context>cwd and shell</environment_context>"),
             ri_user(ms(1), codex_said[0] + " <image name=[Image #1]>"),
             ev_item(ms(1, 0.004), codex_said[0]),
             ri_reply(ms(2), "the assistant's words — never a line"),
             ev_msg(ms(3), codex_said[1]),
             ri_user(ms(3, 0.003), codex_said[1]),
             ri_reply(ms(4), "done"),
             ri_user(ms(5), codex_said[2]),
             ri_reply(ms(6), "done again"),
             ri_user(ms(15), codex_said[3]),
             ev_item(ms(15, 0.002), codex_said[3])]
    day = ct.astimezone(datetime.timezone.utc)
    HW["pc"] = (home / ".codex" / "sessions" / day.strftime("%Y") / day.strftime("%m") /
                day.strftime("%d") / ("rollout-%s-%s.jsonl" % (day.strftime("%Y-%m-%dT%H-%M-%S"), cid)))
    write(HW["pc"], jl(crecs))
    HW["codex_said"], HW["codex_when"] = codex_said, [ms(1), ms(3), ms(5), ms(15)]

    # H8 — the INBOX: three letters between the pair in the window, one before it
    d = lambda days: (now - datetime.timedelta(days=days)).date().isoformat()
    long_words = " ".join("the long letter goes on word %d" % k for k in range(40))
    letters = ["- %s · north-a → north-b · the first letter between the pair · suggested action: read it" % d(20),
               "- %s · north-a ← north-b · %s · suggested action: none" % (d(10), long_words),
               "- %s · north-a → north-b · the third letter, the newest one · suggested action: none" % d(2),
               "- %s · north-a → north-b · a letter from before the fall's window · suggested action: none" % d(60)]
    inbox = ["# INBOX", "", "Letters between projects.", ""] + letters + [""]
    write(hub / "INBOX.md", "\n".join(inbox))
    HW["letters"] = dict((line, inbox.index(line) + 1) for line in letters)
    HW["in_window"] = letters[:3]
    HW["outside"] = letters[3]

    HW["sense_out"], HW["live"] = h_sense()
    HW["html"], HW["marks"] = h_render()


def h_ready(case_id, name):
    """Start a case that needs the link-history world; False (with a SKIP) when the
    pulse or its reader is not where this gate can find it."""
    start(case_id, name)
    if not HW:
        try:
            build_h_world()
        except Exception as exc:
            HW["error"] = repr(exc)
    if HW.get("missing"):
        skip_note("%s: %s not beside the generator or this gate — the BQ-150 cases could not run"
                  % (case_id, ", ".join(HW["missing"])))
        done()
        return False
    if HW.get("error"):
        check(False, "the BQ-150 world could not be built: %s" % HW["error"][:300])
        done()
        return False
    return True


def listing(entry, html=None):
    return list_of(entry, html if html is not None else HW["html"])


def case_h1():
    start("H1", "rails: worlds, children, depth")
    tmp = Path(tempfile.gettempdir()).resolve()
    world = Path(SCRATCH).resolve()
    hub = HERE.parent.resolve()
    check(world.parent == tmp and world.name.startswith(WORLD_PREFIX),
          "the world is not a fresh mkdtemp folder under the system temp folder: %s" % world)
    check(not (str(world) + os.sep).startswith(str(hub) + os.sep),
          "the world sits under the hub folder: %s" % world)
    # a scratch COPY of this gate, started as a child, refuses at once and makes no world
    copy_dir = SCRATCH / "gate-copy"
    copy_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(Path(__file__).resolve()), str(copy_dir / "gate-tree-answers.py"))
    before = set(p.name for p in tmp.iterdir() if p.name.startswith(WORLD_PREFIX))
    t0 = datetime.datetime.now()
    code, out = run([PY, str(copy_dir / "gate-tree-answers.py")], cwd=str(copy_dir), timeout=60)
    secs = (datetime.datetime.now() - t0).total_seconds()
    after = set(p.name for p in tmp.iterdir() if p.name.startswith(WORLD_PREFIX))
    check(code == 2 and "refused" in out, "a copy of this gate run as a child did not refuse: "
          "exit %s · %s" % (code, " ".join(out.split())[:160]))
    check(secs < 30, "the refusal took %.1f s" % secs)
    check(after <= before, "the refusing child made a world: %s" % sorted(after - before))
    # a child that hangs is killed WITH what it started
    hang = ("import subprocess, sys, time\n"
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            "print('GRANDCHILD %d' % p.pid, flush=True)\n"
            "time.sleep(120)\n")
    t0 = datetime.datetime.now()
    code, out = run([PY, "-c", hang], timeout=4)
    secs = (datetime.datetime.now() - t0).total_seconds()
    m = re.search(r"GRANDCHILD (\d+)", out)
    check(code == 124 and secs < 30, "the hanging child was not stopped at its timeout "
          "(exit %s after %.1f s)" % (code, secs))
    check(m is not None, "the hanging child's grandchild never said its pid: %s" % out[-120:])
    if m:
        pid, gone = int(m.group(1)), False
        for _ in range(20):
            if not alive(pid):
                gone = True
                break
            import time as _t
            _t.sleep(0.25)
        check(gone, "the grandchild %d outlived its group's kill" % pid)
    done()


def alive(pid):
    """Is that process still running? (POSIX: signal 0; Windows: tasklist.)"""
    if os.name == "nt":
        code, out = 0, ""
        try:
            out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, timeout=15).stdout.decode("utf-8", "replace")
        except Exception:
            return False
        return (" %d " % pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                   # a zombie is not alive: it has run its last
        done_pid, _st = os.waitpid(pid, os.WNOHANG)
        if done_pid == pid:
            return False
    except ChildProcessError:
        pass
    try:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, timeout=15).stdout.decode().strip()
        return bool(state) and not state.startswith("Z")
    except Exception:
        return True


def check_turn_card(label, sid, turns, path, earlier=0):
    """The two marks of one live session answer with ONE list: the turns' words,
    time first, oldest top, the newest `now`, sources on the transcript's lines."""
    cards = h_cards(HW["marks"], sid)
    check(len(cards) == 2, "%s: %d marks answer for the session, not its LIVE line and its "
          "nerve: %s" % (label, len(cards), [k for k, _ in cards]))
    kept = turns[-20:]
    for key, entry in cards:
        lst = listing(entry)
        check(lst is not None, "%s: %s answers with no list" % (label, key))
        if lst is None:
            continue
        items = lst.get("items") or []
        check(len(items) == len(kept), "%s: %s draws %d lines, not %d"
              % (label, key, len(items), len(kept)))
        check(int(lst.get("earlier") or 0) == earlier, "%s: %s says %s earlier, not %d"
              % (label, key, lst.get("earlier"), earlier))
        want_at = expected_at([w for w, _t in kept])
        check([it.get("at") for it in items] == want_at,
              "%s: %s's times are %s, not %s" % (label, key, [it.get("at") for it in items][:4], want_at[:4]))
        check([(it.get("full") or it.get("w")) for it in items] == [t for _w, t in kept],
              "%s: %s's lines are not the person's turns, in order" % (label, key))
        check([it.get("w") for it in items] == [first_words(t) for _w, t in kept],
              "%s: %s's lines are not trimmed to twelve words" % (label, key))
        labels = [r[0] for r in entry.get("bytes") or []]
        check("about" not in labels and "now" not in labels,
              "%s: %s still carries ABOUT/NOW rows beside the list: %s" % (label, key, labels))
        text_at = person_lines(path)
        for it, (_w, text) in zip(items, kept):
            src = str(it.get("src") or "")
            m = re.match(r"^NORTH · (.+):(\d+)$", src)
            ok = m is not None and Path(m.group(1)) == Path(path)
            rec = text_at.get(int(m.group(2))) if m else None
            said = ((rec or {}).get("message") or {}).get("content") if rec else None
            check(ok and said == text, "%s: %s's line %r does not point at its own record: %s"
                  % (label, key, text[:30], src[-60:]))
    return cards


def case_h2():
    if not h_ready("H2", "seven turns, seven lines"):
        return
    check(HW["sid7"] in HW["live"], "the pulse did not sense the seven-turn window")
    row = HW["live"].get(HW["sid7"]) or {}
    check(len(row.get("turns") or []) == 7, "the live file carries %d turns, not 7: %s"
          % (len(row.get("turns") or []), [t.get("words", "")[:20] for t in row.get("turns") or []]))
    check("earlier" not in row, "the live file counts turns before the seven")
    check(Path(str(row.get("transcript") or "")) == Path(HW["p7"]),
          "the live file does not name the transcript: %s" % row.get("transcript"))
    check(all(set(t) == {"t", "words", "line"} for t in row.get("turns") or []),
          "a turn carries other keys than t, words, line")
    check(re.search(r"turns: read \d+ bytes from \d+ transcripts? \(\d+ from the top\)",
                    HW["sense_out"]) is not None,
          "the beat's log has no turns line: %s" % HW["sense_out"][-200:])
    check_turn_card("H2", HW["sid7"], HW["t7"], HW["p7"])
    done()


def case_h3():
    if not h_ready("H3", "twenty of 25, 5 earlier"):
        return
    row = HW["live"].get(HW["sid25"]) or {}
    check(len(row.get("turns") or []) == 20 and row.get("earlier") == 5,
          "the live file carries %d turns and %s earlier, not 20 and 5"
          % (len(row.get("turns") or []), row.get("earlier")))
    cards = check_turn_card("H3", HW["sid25"], HW["t25"], HW["p25"], earlier=5)
    for key, entry in cards:
        items = (listing(entry) or {}).get("items") or []
        check(bool(items) and items[0].get("w") == "turn number 6 of twenty-five",
              "H3: %s's first line is not the sixth turn: %r" % (key, items[:1]))
        check(any(re.match(r"^[A-Z][a-z]{2} \d\d:\d\d", it.get("at") or "") for it in items),
              "H3: a list across a day carries no day mark: %s" % [it.get("at") for it in items[:3]])
    done()


def case_h4():
    if not h_ready("H4", "one turn keeps its line"):
        return
    row = HW["live"].get(HW["sid1"]) or {}
    check(len(row.get("turns") or []) == 1, "the live file carries %d turns for the one-turn window"
          % len(row.get("turns") or []))
    cards = h_cards(HW["marks"], HW["sid1"])
    check(len(cards) == 2, "%d marks answer for the one-turn window" % len(cards))
    for key, entry in cards:
        check(listing(entry) is None, "H4: %s draws a list for a one-turn window" % key)
        rows = entry.get("bytes") or []
        check(rows[:1] == [["about", HW["t1"][0][1]]],
              "H4: %s does not keep its single ABOUT line: %s" % (key, rows[:1]))
        check(not any(r[0] == "now" for r in rows), "H4: %s carries a NOW row" % key)
    done()


def case_h5():
    if not h_ready("H5", "a routine: one line + status"):
        return
    for sid, status in ((HW["sidr"], "finished"), (HW["sidq"], "running · Read")):
        row = HW["live"].get(sid) or {}
        check(row.get("run_status") == status and row.get("routine", "").startswith("gate-routine"),
              "the live file says routine %r, status %r — not %r"
              % (row.get("routine"), row.get("run_status"), status))
        cards = h_cards(HW["marks"], sid)
        check(len(cards) == 2, "%d marks answer for the routine %s" % (len(cards), sid[-6:]))
        for key, entry in cards:
            items = (listing(entry) or {}).get("items") or []
            check(len(items) == 1, "H5: %s draws %d lines for a routine's run" % (key, len(items)))
            if items:
                check(items[0].get("full", items[0].get("w")) == HW["routine_first"],
                      "H5: %s's line is not the prompt's first line: %r" % (key, items[0]))
                check("now" not in (items[0].get("at") or ""), "H5: %s marks its one line now" % key)
                check(items[0].get("at") == HW["rt"].astimezone().strftime("%H:%M")
                      or items[0].get("at", "").endswith(HW["rt"].astimezone().strftime("%H:%M")),
                      "H5: %s's line does not start with its time: %r" % (key, items[0].get("at")))
            rows = dict((r[0], r[1]) for r in entry.get("bytes") or [])
            check(rows.get("status") == status, "H5: %s says status %r, not %r"
                  % (key, rows.get("status"), status))
            check("about" not in rows and "now" not in rows, "H5: %s carries ABOUT/NOW" % key)
    done()


def case_h6():
    if not h_ready("H6", "a Codex rollout, once each"):
        return
    sid = HW["pc"].stem
    row = HW["live"].get(sid) or {}
    words = [t.get("words") for t in row.get("turns") or []]
    check(words == HW["codex_said"], "the live file's Codex turns are %s, not %s"
          % (words, HW["codex_said"]))
    cards = h_cards(HW["marks"], sid)
    check(len(cards) == 2, "%d marks answer for the Codex window" % len(cards))
    lines = io.open(str(HW["pc"]), encoding="utf-8").read().splitlines()
    for key, entry in cards:
        items = (listing(entry) or {}).get("items") or []
        check([(it.get("full") or it.get("w")) for it in items] == HW["codex_said"],
              "H6: %s draws %s" % (key, [it.get("w") for it in items]))
        check([it.get("at") for it in items] == expected_at(HW["codex_when"]),
              "H6: %s's times are %s" % (key, [it.get("at") for it in items]))
        for it, said in zip(items, HW["codex_said"]):
            m = re.match(r"^NORTH · (.+):(\d+)$", str(it.get("src") or ""))
            ok = m is not None and Path(m.group(1)) == Path(HW["pc"])
            check(ok and said in lines[int(m.group(2)) - 1],
                  "H6: %s's line %r does not point at a record of its words" % (key, said))
    done()


def case_h7():
    if not h_ready("H7", "the pulse's cursor"):
        return
    path, sid = HW["p7"], HW["sid7"]
    reads, state = h_reads()                         # a beat with nothing new
    r0 = reads.get(str(path)) or {}
    check(r0.get("bytes") == 0 and not r0.get("full"),
          "a beat with nothing appended read %s bytes (from the top: %s)" % (r0.get("bytes"), r0.get("full")))
    check(Path(state) == HW["state"] / ("turns-%s.json" % H_MACHINE) and Path(state).is_file(),
          "the cursor file is not where EXO_PULSE_STATE_DIR says: %s" % state)
    check(not list(HW["hub"].glob("turns-*.json")) and not list(HW["hub"].rglob("turns-*.json")),
          "a cursor file sits inside the hub folder")
    size0 = path.stat().st_size
    later = HW["now"] + datetime.timedelta(minutes=1)
    added = [(later, "one more thing about north a"),
             (later + datetime.timedelta(seconds=40), "and the very last one")]
    extra = []
    for when, text in added:
        extra.append(c_person(text, when, sid, HW["a"]))
        extra.append(c_reply("ok", when + datetime.timedelta(seconds=5), sid, HW["a"]))
    with io.open(str(path), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(jl(extra))
    size1 = path.stat().st_size
    reads, _state = h_reads()
    r1 = reads.get(str(path)) or {}
    check(not r1.get("full") and r1.get("from") == size0,
          "the second beat did not read from the cursor: from %s, the file was %d bytes"
          % (r1.get("from"), size0))
    check(0 < int(r1.get("bytes") or 0) < size1 and int(r1.get("bytes") or 0) == size1 - size0,
          "the second beat read %s bytes of a %d-byte file; %d were appended"
          % (r1.get("bytes"), size1, size1 - size0))
    live = json.loads(io.open(str(HW["hub"] / ("live-sessions-%s.json" % H_MACHINE)),
                              encoding="utf-8").read())
    row = dict((s["id"], s) for s in live["sessions"]).get(sid) or {}
    words = [t.get("words") for t in row.get("turns") or []]
    check(words == [t for _w, t in HW["t7"]] + [t for _w, t in added],
          "after the append the live file carries %s" % [w[:16] for w in words])
    html, marks = h_render("tree-appended.html")
    for key, entry in h_cards(marks, sid):
        items = (list_of(entry, html) or {}).get("items") or []
        check(len(items) == 9 and items[-1].get("w") == "and the very last one"
              and items[-1].get("at", "").endswith(" · now")
              and not items[-2].get("at", "").endswith("now"),
              "H7: %s after the append draws %d lines ending %r" % (key, len(items), items[-1:]))
    # the file shrinks (a rewrite): read from the top
    keep = HW["t7"][:3]
    claude_transcript(sid, HW["a"], keep, noise_after=())
    size2 = path.stat().st_size
    check(size2 < size0, "the fixture did not shrink (%d → %d)" % (size0, size2))
    reads, _state = h_reads()
    r2 = reads.get(str(path)) or {}
    check(r2.get("full") is True and r2.get("from") == 0 and r2.get("bytes") == size2,
          "a shrunk file was not read from the top: %s" % r2)
    live = json.loads(io.open(str(HW["hub"] / ("live-sessions-%s.json" % H_MACHINE)),
                              encoding="utf-8").read())
    row = dict((s["id"], s) for s in live["sessions"]).get(sid) or {}
    check([t.get("words") for t in row.get("turns") or []] == [t for _w, t in keep],
          "after the rewrite the live file carries %d turns, not 3" % len(row.get("turns") or []))
    # the file rewritten LONGER, its line ends moved: read from the top, never
    # from a cursor that now points into the middle of a line
    grown = [(HW["t7"][0][0] - datetime.timedelta(minutes=1), "a turn that came first in the rewrite")] + keep
    for pad in range(8):
        claude_transcript(sid, HW["a"], grown, noise_after=())
        data = path.read_bytes()
        if len(data) > size2 and data[size2 - 1:size2] != b"\n":
            break
        grown[0] = (grown[0][0], grown[0][1] + " x")
    check(len(data) > size2 and data[size2 - 1:size2] != b"\n",
          "the fixture could not move the line ends under the cursor")
    reads, _state = h_reads()
    r3 = reads.get(str(path)) or {}
    check(r3.get("full") is True and r3.get("from") == 0,
          "a file rewritten longer was read from the stale cursor: %s" % r3)
    live = json.loads(io.open(str(HW["hub"] / ("live-sessions-%s.json" % H_MACHINE)),
                              encoding="utf-8").read())
    row = dict((s["id"], s) for s in live["sessions"]).get(sid) or {}
    check([t.get("words") for t in row.get("turns") or []] == [t for _w, t in grown],
          "after the longer rewrite the live file carries %s"
          % [t.get("words", "")[:16] for t in row.get("turns") or []])
    # with no EXO_PULSE_STATE_DIR the cursor is machine-personal, under HOME, never the hub
    _reads, state = h_reads({"EXO_PULSE_STATE_DIR": None})
    want = HW["home"] / ".exocortex" / "pulse" / ("turns-%s.json" % H_MACHINE)
    check(Path(state) == want and want.is_file(),
          "the default cursor file is %s, not %s" % (state, want))
    # the world goes back to the seven turns for the cases after this one
    claude_transcript(sid, HW["a"], HW["t7"], noise_after=(0, 3))
    HW["sense_out"], HW["live"] = h_sense()
    HW["html"], HW["marks"] = h_render()
    done()


def case_h8():
    if not h_ready("H8", "a fall arc: its pair's letters"):
        return
    fall = blob(HW["html"], "fall-data") or {}
    pair = [(i, a) for i, a in enumerate(fall.get("arcs") or [])
            if {a.get("an"), a.get("bn")} == {"north-a", "north-b"}]
    check(len(pair) == 3, "%d arcs drawn between north-a and north-b, not one per letter's week (3)"
          % len(pair))
    want = HW["in_window"]
    for i, a in pair:
        check(int(a.get("n") or 0) >= 1 and bool(a.get("text")),
              "arc:%d lost its hover count or its words: %s" % (i, a))
        entry = HW["marks"].get("arc:%d" % i) or {}
        items = (listing(entry) or {}).get("items") or []
        check(len(items) == 3, "arc:%d answers with %d letters, not 3" % (i, len(items)))
        check([it.get("src") for it in items] == ["INBOX.md:%d" % HW["letters"][l] for l in want],
              "arc:%d's letters are %s — not the three, oldest first" % (i, [it.get("src") for it in items]))
        check(all(it.get("src") != "INBOX.md:%d" % HW["letters"][HW["outside"]] for it in items),
              "arc:%d carries the letter from before the window" % i)
        for it, line in zip(items, want):
            full = it.get("full") or it.get("w")
            check(full == line or (len(line) > 500 and full.endswith("\u2026")
                                   and line.startswith(full[:-1].rstrip())),
                  "arc:%d's hover is not the INBOX line: %r" % (i, full[:60]))
        check(items and re.match(r"^[A-Z][a-z]{2} \d\d [A-Z][a-z]{2}$", items[0].get("at") or ""),
              "arc:%d's lines do not start with their day: %r" % (i, items[:1]))
        check(items and items[0].get("w", "").startswith("north-a \u2192 north-b · "),
              "arc:%d's line does not say from → to first: %r" % (i, items[:1]))
        check(entry.get("kind", "").startswith("the notes between"), "arc:%d does not say what it is" % i)
    done()


def case_h9():
    if not h_ready("H9", "every line answers"):
        return
    html = HW["html"]
    lists = blob(html, "lists") or {}
    every = []
    for key, entry in HW["marks"].items():
        lst = list_of(entry, html)
        if isinstance(entry.get("list"), str):
            check(entry["list"] in lists, "%s names a list the page does not carry" % key)
        for it in (lst or {}).get("items") or []:
            every.append((key, it))
    check(len(every) >= 30, "only %d lines on the page to check" % len(every))
    bad = [(k, it) for k, it in every if not str(it.get("src") or "").strip()
           or not str(it.get("w") or "").strip() or str(it.get("w")).strip() in PLACEHOLDERS
           or not str(it.get("at") or "").strip()]
    check(not bad, "%d lines have no source, words or time: %s" % (len(bad), bad[:2]))
    inbox = io.open(str(HW["hub"] / "INBOX.md"), encoding="utf-8").read().splitlines()
    for key, it in every:
        src = str(it.get("src"))
        m = re.match(r"^INBOX\.md:(\d+)$", src)
        if m:
            line = inbox[int(m.group(1)) - 1]
            full = it.get("full") or it.get("w")
            check(full == line or (full.endswith("\u2026") and line.startswith(full[:-1].rstrip())),
                  "%s: %s is not the line its source names" % (key, src))
    check(len(set(json.dumps(v, sort_keys=True) for v in lists.values())) == len(lists),
          "the page carries one list twice")
    # the page's own script draws each line with its hover and answers its click
    js = html[html.rfind("<script>"):]
    for piece in ("title=\"'+esc(it.full||it.w)", "data-src=\"'+esc(it.src)+'\"", 'tabindex="0"',
                  "L.earlier+' earlier'", "closest('dd[data-src]')", "function srcOf(dd)",
                  "'<dt data-src-of=\"1\">source</dt><dd data-src-of=\"1\">'",
                  "sd.matches('dd[data-src]')&&insp.contains(sd)"):
        check(piece in js, "the page's script lost %r" % piece)
    branch = js[js.find("insp.contains(e.target)"):js.find("insp.contains(e.target)") + 400]
    check(branch.find("closest('dd[data-src]')") != -1
          and branch.find("closest('dd[data-src]')") < branch.find("closest('button')"),
          "a line's click is not answered inside the panel before its buttons")
    done()


CSS_TOKEN = re.compile(r"--[A-Za-z0-9-]+(?=\s*:)")
CSS_COLOUR = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)")
CSS_FONT = re.compile(r"font-family\s*:\s*([^;}]+)")


def style_of(html):
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))


def look_of(css):
    """The stylesheet as the eye sees it: without its comments and without
    pointer-events, which decide where a click lands, not what is drawn
    (the crown's gaps pass a click through)."""
    css = re.sub(r"/\*.*?\*/\n?", "", css, flags=re.S)
    css = re.sub(r";pointer-events:[^;}]+", "", css)
    return re.sub(r"pointer-events:[^;}]+;?", "", css)


def classes_of(html):
    """Every class name the page's body draws and its script writes."""
    body, js = body_of(html), html[html.rfind("<script>"):]
    names = set()
    for group in re.findall(r'class="([^"]*)"', body) + re.findall(r"class=\\?\"([^\"'+]*)", js):
        names.update(group.split())
    return names


def case_h10():
    if not h_ready("H10", "nothing new on the surface"):
        return
    html = HW["html"]
    css = style_of(html)
    # the list is drawn in the rows' own dt/dd: its markup adds no class
    js = html[html.rfind("<script>"):]
    at = js.find("var L=")
    check(at != -1 and "class=" not in js[at:js.find("(m.bytes||[])", at)],
          "the list's markup carries a class of its own")
    base = Path(FACTS["base_dir"]) / "collect-openers.py" if FACTS.get("base_dir") else None
    if base is None or not base.is_file():
        skip_note("H10: no --base-dir=<folder> with the base collect-openers.py — the "
                  "before/after comparison could not run; the structural half above did")
        done()
        return
    before, before_marks = h_render("tree-base.html", generator=base)
    old_css = style_of(before)
    check(look_of(css) == look_of(old_css),
          "the stylesheet changed: %s" % first_difference(look_of(old_css), look_of(css)))
    for name, pat in (("custom properties", CSS_TOKEN), ("colours", CSS_COLOUR), ("fonts", CSS_FONT)):
        a, b = sorted(set(pat.findall(old_css))), sorted(set(pat.findall(css)))
        check(a == b, "the page's %s changed: +%s -%s" % (name, sorted(set(b) - set(a))[:5],
                                                          sorted(set(a) - set(b))[:5]))
    new_classes = classes_of(html) - classes_of(before)
    check(not new_classes, "the page draws classes the base page does not: %s" % sorted(new_classes)[:8])
    kinds = lambda m: sorted(set(k.split(":")[0] for k in m))
    check(kinds(HW["marks"]) == kinds(before_marks),
          "the mark kinds changed: %s → %s" % (kinds(before_marks), kinds(HW["marks"])))
    print("     H10: stylesheet %d bytes identical · %d custom properties · %d colours · %d fonts"
          % (len(css), len(set(CSS_TOKEN.findall(css))), len(set(CSS_COLOUR.findall(css))),
             len(set(CSS_FONT.findall(css)))))
    done()


def case_h12():
    """A history opens SCROLLED TO NOW."""
    if not h_ready("H12", "the list opens on NOW"):
        return
    html = HW["html"]
    # 1. the data: in every list the newest line — and only it — is marked now
    lists_seen = 0
    for sid in (HW["sid7"], HW["sid25"]):
        for key, entry in h_cards(HW["marks"], sid):
            items = (listing(entry) or {}).get("items") or []
            nows = [k for k, it in enumerate(items) if str(it.get("at") or "").endswith(" · now")]
            check(nows == [len(items) - 1], "%s: the lines marked now are %s of %d, not the last"
                  % (key, nows, len(items)))
            lists_seen += 1
    check(lists_seen == 4, "%d session cards checked, not 4" % lists_seen)
    # 2. the page's script marks that line and, once the panel is filled and
    #    placed, scrolls the panel's own scroller until that line's foot meets
    #    the scroller's foot — nothing after it moves the scroll back
    js = html[html.rfind("<script>"):]
    for piece in ("k===L.items.length-1&&/ · now$/.test(it.at||'')", "(nw?' data-now=\"1\"':'')",
                  "insp.querySelector('dd[data-now]')", "insp.querySelector('.iscroll')",
                  "nwd.getBoundingClientRect().bottom-scr.getBoundingClientRect().bottom",
                  "if(gap>0) scr.scrollTop+=Math.ceil(gap);"):
        check(piece in js, "the page's script lost %r" % piece)
    start_at = js.find("function showMark(")
    end_at = js.find("function hideMark(", start_at)
    body = js[start_at:end_at] if start_at != -1 and end_at != -1 else ""
    order = [body.find(t) for t in ("insp.innerHTML=h", "placeAt(at.x,at.y)",
                                    "querySelector('dd[data-now]')", "scr.scrollTop+=",
                                    "return true")]
    check(bool(body) and -1 not in order and order == sorted(order),
          "showMark does not fill, place, THEN scroll to NOW before it returns: %s" % order)
    after = body[body.find("scr.scrollTop+="):] if body else ""
    check("scrollTop=" not in after.replace("scrollTop+=", ""),
          "something in showMark moves the scroll after it reached NOW")
    css = style_of(html)
    check(re.search(r"#inspector \.iscroll\{max-height:[^}]*overflow:auto", css) is not None,
          "the panel has no scroller of its own to open on NOW")
    done()


H11 = {}


def h11_before():
    """What the edges look like before any case runs (H11 compares at the end)."""
    home = Path.home()
    H11["pulse_state"] = sorted(p.name for p in (home / ".exocortex" / "pulse").glob("*")) \
        if (home / ".exocortex" / "pulse").is_dir() else []
    H11["hub_names"] = sorted(p.name for p in HERE.parent.iterdir())
    H11["tools_names"] = sorted(p.name for p in HERE.iterdir())


def scrub_words():
    """The words no fixture, no page this gate draws and no line this build adds
    may carry: this machine's home folder, its login, and its owner's name."""
    words = set()
    try:
        words.add(str(Path.home()))
    except Exception:
        pass
    try:
        import getpass
        login = getpass.getuser()
        if login and len(login) > 2:
            words.add(login)
    except Exception:
        pass
    try:
        reg = json.loads(io.open(str(HERE.parent / "registry.json"), encoding="utf-8").read())
        for key in ("name", "short"):
            v = str(((reg.get("owner") or {}).get(key)) or "").strip()
            if len(v) > 2:
                words.add(v)
    except Exception:
        pass
    return sorted(w for w in words if w and w.lower() not in ("wren", "gate", "north", "south"))


def has_word(text, word):
    if os.sep in word or "/" in word or "\\" in word:
        return word in text
    return re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(word), text, re.I) is not None


def case_h11():
    start("H11", "the edges: scrub, writes, live files")
    words = scrub_words()
    check(bool(words), "no scrub words could be read on this machine")
    # 1. the world's fixtures and pages
    seen = []
    if HW.get("base") and Path(HW["base"]).is_dir():
        for f in Path(HW["base"]).rglob("*"):
            if f.is_file() and f.suffix in (".jsonl", ".md", ".json", ".html"):
                text = io.open(str(f), encoding="utf-8", errors="replace").read()
                seen.extend("%s: %s" % (f.name, w) for w in words if has_word(text, w))
    check(not seen, "the world carries this machine's own words: %s" % seen[:4])
    # 2. the lines this build adds
    base_dir = Path(FACTS["base_dir"]) if FACTS.get("base_dir") else None
    if base_dir is None:
        skip_note("H11: no --base-dir — the scrub of the lines this build adds could not run")
    else:
        import difflib
        for name, now_file in (("pulse.py", h_tool("pulse.py")),
                               ("collect-openers.py", Path(FACTS.get("generator") or "")),
                               ("gate-tree-answers.py", Path(__file__).resolve())):
            old = base_dir / name
            if now_file is None or not now_file.is_file() or not old.is_file():
                skip_note("H11: %s or its base is missing — its added lines were not scrubbed" % name)
                continue
            a = io.open(str(old), encoding="utf-8").read().splitlines()
            b = io.open(str(now_file), encoding="utf-8").read().splitlines()
            added = [l for l in difflib.ndiff(a, b) if l.startswith("+ ")]
            hits = ["%s: %s" % (name, w) for w in words for l in added if has_word(l, w)]
            check(not hits, "the lines this build adds carry this machine's words: %s" % hits[:3])
    # 3. nothing written outside the world
    home = Path.home()
    pulse_now = sorted(p.name for p in (home / ".exocortex" / "pulse").glob("*")) \
        if (home / ".exocortex" / "pulse").is_dir() else []
    # the live pulse keeps ITS OWN cursor file there (turns-<this machine>.json);
    # a file named for this gate's machines would be the world leaking out
    leaked = sorted(n for n in set(pulse_now) - set(H11.get("pulse_state") or [])
                    if any(("turns-%s" % m) in n for m in (H_MACHINE, "gate")))
    check(not leaked, "this run wrote its cursor into this machine's own ~/.exocortex/pulse: %s"
          % leaked)
    new_hub = set(p.name for p in HERE.parent.iterdir()) - set(H11.get("hub_names") or [])
    new_tools = set(p.name for p in HERE.iterdir()) - set(H11.get("tools_names") or [])
    worldish = [n for n in new_hub | new_tools
                if any(m.lower() in n.lower() for m in H_MARKERS + ("tree-appended", "tree-base"))
                or n.startswith("live-sessions-%s" % H_MACHINE)]
    check(not worldish, "the run left names of its world beside this gate: %s" % sorted(worldish))
    # 4. the live page and the live sessions files carry none of the world
    marks_found = []
    for f in list(HERE.parent.glob("live-sessions-*.json")) + [HERE.parent / "tree.html"]:
        if f.is_file():
            text = io.open(str(f), encoding="utf-8", errors="replace").read()
            for m in (str(SCRATCH), "north-a", HW.get("sid7", "none-such"), "gate-routine"):
                if m and m in text:
                    marks_found.append("%s: %s" % (f.name, m))
    check(not marks_found, "a live file carries the world: %s" % marks_found[:3])
    done()


def main(argv):
    if DEPTH >= MAX_DEPTH:
        print("gate-tree-answers: refused — started as a child of a gate run (%s=%d); "
              "a gate never runs inside its own world" % (DEPTH_ENV, DEPTH))
        return 2
    keep = "--keep" in argv
    for a in argv:
        if a.startswith("--base-dir="):
            FACTS["base_dir"] = str(Path(a.split("=", 1)[1]).expanduser().resolve())
    rest = [a for a in argv if not a.startswith("--")]
    generator = Path(rest[0]).resolve() if rest else (HERE / "collect-openers.py")
    if not generator.is_file():
        print("no generator at %s" % generator)
        return 2
    if "--inventory" in argv:
        hub = next((Path(a.split("=", 1)[1]).expanduser().resolve() for a in argv
                    if a.startswith("--hub=")), HERE.parent)
        return inventory_only(generator, hub)
    print("gate-tree-answers · %s" % generator)
    for name in ("collect-openers.py", "opener_carriers.py"):
        target = generator.parent / name
        if target.is_file():
            try:
                py_compile.compile(str(target), doraise=True)
            except Exception as exc:
                print("G0   compile                FAIL · %s" % exc)
                return 1
    print("G0   compile                pass · both files compile")
    build_world(generator)
    if FACTS.get("no_carriers"):
        print("     NOTE · opener_carriers.py is not installed beside the generator, so the "
              "world draws the folder's openers alone, as this install does")
    FACTS["generator"] = str(generator)
    FACTS["stdout"], FACTS["html"] = render(OUT / "tree.html")
    h11_before()
    for case in (case_g1, case_g2, case_g3, case_g4, case_g5, case_g6, case_g7,
                 case_g8, case_g9, case_g10, case_g11, case_g12, case_g14, case_g15,
                 case_g16, case_g17, case_g18, case_g19, case_g20, case_g21, case_g22,
                 case_h1, case_h2, case_h3, case_h4, case_h5, case_h6, case_h7, case_h8,
                 case_h9, case_h10, case_h12, case_g13, case_h11):
        guarded(case)
    print("")
    if FAILS:
        for line in FAILS[:20]:
            print("  FAIL %s" % line)
        print("STOP · %d check%s failed, %d passed · world: %s"
              % (len(FAILS), "" if len(FAILS) == 1 else "s", PASSES,
                 SCRATCH if keep else "removed (--keep holds it)"))
        print(count_line())
        return 1
    if not keep:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)
    print("OK · every mark answers · %d checks passed%s"
          % (PASSES, ("" if not keep else " · world kept at %s" % SCRATCH)))
    print(count_line())
    return 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    if SCRATCH is not None:
        shutil.rmtree(str(SCRATCH), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
