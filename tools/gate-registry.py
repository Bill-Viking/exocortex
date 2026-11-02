#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-registry.py — the proof that the owner's names left the code.

    python3 tools/gate-registry.py          from the hub folder (an installed hub)
    python3 tools/gate-registry.py --keep   keep the fixture worlds

TWO PLACES IT RUNS FROM, told apart by what is there, never by a path typed in:
  a BUILD folder   beside the build it proves — tools/, base/, templates/, sync/,
                   the owner's registry.fleet.json and the diffs — two folders
                   below the hub; every case runs
  an INSTALLED hub in the hub's own tools/ folder, beside the tools it proves;
                   the cases that need what only a build carries (the original
                   tools, the diffs) or what only the owner's machine carries
                   (their registry, their private word list) SKIP, each with
                   one line saying why

TWO CLAIMS, TWELVE CASES.

  With the FLEET registry installed, every tool's output is what it is today —
  proved by running the original tool and the registry copy on the same fixture and
  comparing the bytes (R2).
  With the SEED registry, the private word list finds nothing in the program
  tree or in anything the tools draw (R3, R9), and nothing is invented: no
  persona root, no colour token for a mind nobody has, no caption (R3, R7).

RULES THIS GATE KEEPS

  * Every fixture world is made under the SYSTEM TEMP folder — never under the
    hub — and is deleted at the end of every case and at the end of the run.
    (An older brain sync carries everything under the hub's scratch/ on every
    push, and a push can happen mid-run.)
  * The live hub is READ to build the fleet-equality fixture. Nothing writes it.
  * Every child carries a mark and a depth, is put in its own process group,
    and is ended with everything it started when it runs past its timeout. Each
    case ends with a survivors check.
  * Nothing this gate PRINTS carries a word from the private list: every hit is
    reported as its file and the word masked to its first letter and length,
    and every path is printed with the home folder folded to `~`.

Stdlib only, Python 3.9-compatible, macOS and Windows.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PY = sys.executable or "python3"

INNER = os.environ.get("EXO_GATE_REG_INNER") == "1"
DEPTH = int(os.environ.get("EXO_GATE_REG_DEPTH") or 0)
MAX_DEPTH = 2

if (HERE / "tools" / "exo_registry.py").is_file():
    LAYOUT = "build"                       # <hub>/scratch/<build>/gate-registry.py
    BUILD = HERE
    HUB = BUILD.parent.parent
    P3_TOOLS = BUILD / "tools"
    P3_ORCH = BUILD / "orchestrator.py"
    BASE_TOOLS = BUILD / "base" / "tools"
    BASE_ORCH = BUILD / "base" / "orchestrator.py"
    SYNC_DIR = BUILD / "sync"
    TEMPLATES = BUILD / "templates"
    RESOLVER = BUILD.parent / "bq045-p2a" / "exo_paths.py"
    OWNER_FILE = BUILD / "registry.fleet.json"
else:
    LAYOUT = "installed"                   # <hub>/tools/gate-registry.py
    BUILD = None
    HUB = HERE.parent
    P3_TOOLS = HERE
    P3_ORCH = HUB / "orchestrator.py"
    BASE_TOOLS = BASE_ORCH = None
    SYNC_DIR = HUB / "sync"
    TEMPLATES = HUB / "templates"
    RESOLVER = HERE / "exo_paths.py"
    OWNER_FILE = HUB / "registry.json"
SHIP_ROOT = BUILD or HUB                   # where the shipped files are measured
SEED_REGISTRY = TEMPLATES / "registry.json"
SCRUB_WORDS = HUB / "release" / "SCRUB-WORDS.txt"


def _owner_file():
    """The OWNER's own registry — registry.fleet.json beside a build, the hub's
    registry.json once installed — and only when it names an owner. The cases
    that prove the owner's own fleet read it at run time; on a machine whose
    registry names nobody it is None, and they SKIP."""
    try:
        data = json.loads(OWNER_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    owner = data.get("owner") if isinstance(data, dict) else None
    name = owner.get("name") if isinstance(owner, dict) else ""
    return OWNER_FILE if isinstance(name, str) and name.strip() else None


FLEET_REGISTRY = _owner_file()

# The gate's OWN registry: an owner, two machines, the minds with one persona —
# every name invented. The cases that need AN owner's registry (not THE owner's)
# use this one, so they prove the same thing on every machine.
FIXTURE_REGISTRY = {
    "version": 1,
    "note": "gate-registry's own fixture registry: every name in it is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "machines": {
        "north": {"label": "North", "mark": "\u25cf", "os": "macos",
                  "hue": {"light": "#2456a4", "dark": "#7fb0e8"}},
        "south": {"label": "South", "mark": "\u258e", "os": "windows",
                  "hue": {"light": "#9a6b3a", "dark": "#d4a373"}},
    },
    "minds": [
        {"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "show": True},
        {"name": "OPUS", "vendor": "Anthropic", "kind": "claude", "show": True},
        {"name": "NOBODY", "vendor": "OpenAI", "kind": "codex", "show": True},
    ],
    "mind_aliases": {"CODEX": "NOBODY", "GPT": "NOBODY"},
    "lanes": {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
              "hub_folders": ["Exocortex", "Old Hub"], "not_groups": [],
              "hub_key": "old hub"},
    "surface": {"caption": ""},
}
FIXTURE_OWNER = FIXTURE_REGISTRY["owner"]["name"]
FIXTURE_PERSONAS = ("NOBODY",)

BASE_ENV = dict(os.environ)
# A fixture never inherits this machine's own record or registry pointer: each
# world names its own through its HOME and its own files.
for _drop in ("EXO_REGISTRY_JSON", "EXO_MACHINE_JSON", "COLLECT_OPENERS_OUT",
              "COLLECT_OPENERS_ROOT"):
    BASE_ENV.pop(_drop, None)

checks, fails = [], []
SKIPS = []
CASE = "R0"
CHILDREN = 0
LAST_CHILD = None
CHILD_PROCS = []
WORLDS = []
ROOT = None


# ---------------------------------------------------------------------------
# saying what happened
# ---------------------------------------------------------------------------

REAL_HOME = str(Path(os.path.expanduser("~")).resolve())
REAL_HOME_RAW = os.path.expanduser("~")


def fold(text):
    """Accents folded, so a name under a diacritic is still that name."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def private_words():
    try:
        raw = SCRUB_WORDS.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [w.strip() for w in raw.splitlines() if w.strip() and not w.strip().startswith("#")]


WORDS = private_words()
PATTERNS = [(w, re.compile(r"(?<![0-9A-Za-z])" + re.escape(fold(w)) + r"(?![0-9A-Za-z])",
                           re.IGNORECASE)) for w in WORDS]


def masked(word):
    """A word this gate must REPORT without SAYING: its first letter and how
    long it is. A gate's output is read, pasted and committed, so the private
    list must not survive a single run of it."""
    word = str(word)
    return "%s\u2026 (%d)" % (word[:1], len(word))


def shown(text):
    """Anything this gate prints, with the home folder folded to `~` and every
    private word masked. On this machine every absolute path under the home
    folder carries the owner's name."""
    text = str(text)
    for home in (REAL_HOME, REAL_HOME_RAW):
        if home and home != "/":
            text = text.replace(home, "~")
    folded = fold(text)
    for word, pattern in PATTERNS:
        if pattern.search(folded):
            # Work on the folded copy so the position maths cannot slip.
            text = pattern.sub(masked(word), folded)
            folded = text
    return text


def say(text=""):
    try:
        sys.stdout.write(shown(text) + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(shown(text).encode("ascii", "replace").decode("ascii") + "\n")
    sys.stdout.flush()


def case(name, title):
    global CASE
    CASE = name
    say("")
    say("%s  %s" % (name, title))


def check(ok, what):
    checks.append(ok)
    if not ok:
        fails.append("%s  %s" % (CASE, what))
    say("  %s %s" % ("ok  " if ok else "FAIL", what))
    return ok


def skip(why):
    """A case this machine cannot answer, said in one line and counted."""
    SKIPS.append("%s  %s" % (CASE, why))
    say("  SKIP %s" % why)


# ---------------------------------------------------------------------------
# children: marked, bounded, and never left behind
# ---------------------------------------------------------------------------

def run_child(script, *args, **kw):
    """(exit code, output) from a tool run as a program."""
    global LAST_CHILD, CHILDREN
    env = dict(kw.pop("env", None) or BASE_ENV)
    env["EXO_GATE_REG_INNER"] = "1"
    env["EXO_GATE_REG_DEPTH"] = str(DEPTH + 1)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    timeout = kw.pop("timeout", 300)
    cwd = kw.pop("cwd", None)
    cmd = [PY, str(script)] + [str(a) for a in args]
    group = {}
    if os.name == "nt":
        group["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    elif DEPTH == 0:
        group["start_new_session"] = True
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=env, cwd=(str(cwd) if cwd else None), **group)
    LAST_CHILD = proc
    CHILD_PROCS.append(proc)
    CHILDREN += 1
    try:
        out, _err = proc.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        end_child(proc)
        out, _err = proc.communicate()
        out = (out or b"") + ("\ngate-registry: the child ran past %d s and was ended "
                              "with everything it started" % timeout).encode("utf-8")
    return proc.returncode, (out or b"").decode("utf-8", "replace").strip()


def end_child(proc):
    if os.name == "nt":
        subprocess.call(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif DEPTH == 0:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def survivors():
    """Every process still alive that THIS gate started — the child itself, and
    on POSIX anything left in the group the child was given.

    Counted from the gate's own list, never from a search of the machine: a
    shell pipeline around the gate puts its own processes in the same group,
    and a count of the group would call them strays."""
    left = []
    for proc in CHILD_PROCS:
        if proc.poll() is None:
            left.append("%d (still running)" % proc.pid)
            continue
        if os.name != "nt" and DEPTH == 0:
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                continue
            except OSError:
                continue
            left.append("%d (its group is not empty)" % proc.pid)
    return left


def no_strays():
    left = survivors()
    for one in left[:3]:
        say("      still alive: %s" % one)
    check(not left, "strays 0 (%d child process%s started so far)"
          % (CHILDREN, "" if CHILDREN == 1 else "es"))


# ---------------------------------------------------------------------------
# worlds — every one under the system temp folder, every one deleted
# ---------------------------------------------------------------------------

def world(name):
    """A fresh fixture world under the system temp folder. NEVER under the hub:
    the fleet's brain sync carries the hub's scratch/ on every push, and a push
    can happen while this gate is running."""
    global ROOT
    if ROOT is None:
        ROOT = Path(tempfile.mkdtemp(prefix="exo-gate-p3-"))
    w = ROOT / name
    if w.exists():
        shutil.rmtree(w, ignore_errors=True)
    w.mkdir(parents=True)
    WORLDS.append(w)
    return w


def drop(w, keep=False):
    if keep:
        return
    shutil.rmtree(str(w), ignore_errors=True)
    if w in WORLDS:
        WORLDS.remove(w)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def env_for(home, registry=None, **extra):
    env = dict(BASE_ENV)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # A fixture makes repositories of its own; git needs a name for them and
    # must never reach the person's own configuration for one.
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "exocortex gate"
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "gate@example.invalid"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    if registry is not None:
        env["EXO_REGISTRY_JSON"] = str(registry)
    # The fixture's own record, named outright when it wrote one: a tool that
    # reads the record through the resolver then reads the fixture's, even when
    # it runs in place beside a hub that keeps a record of its own.
    record = Path(home) / "orchestrator-sync" / "machine.json"
    if record.is_file():
        env["EXO_MACHINE_JSON"] = str(record)
    for key, value in extra.items():
        env[key] = str(value)
    return env


def machine_record(home, hub, name="north", roots=None):
    """A machine.json in a fake home's brain folder — the file every tool of
    this set finds by `~/orchestrator-sync/machine.json`."""
    rec = {"name": name, "os": "macos", "bootstrapped": True,
           "roots": dict(roots or {})}
    rec["roots"]["orchestrator"] = str(hub)
    rec["roots"].setdefault("projects", str(Path(home) / "Projects"))
    rec["roots"].setdefault("claude", str(Path(home) / ".claude"))
    rec["roots"].setdefault("codex", str(Path(home) / ".codex"))
    rec["roots"].setdefault("grok", str(Path(home) / ".grok"))
    rec["roots"].setdefault("home", str(home))
    write(Path(home) / "orchestrator-sync" / "machine.json",
          json.dumps(rec, indent=2, ensure_ascii=False))
    return rec


def load_registry_module():
    """The loader, imported from the build's own tools folder."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "exo_registry_under_test", str(P3_TOOLS / "exo_registry.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RG = load_registry_module() if (P3_TOOLS / "exo_registry.py").is_file() else None
_LOADED = {}


def load(which):
    """A registry FILE read as a record. The loader looks for `registry.json`
    beside a hub, so each file gets a folder of its own, once — and that folder
    is a WORLD like any other, deleted at the end of the run. One of them holds
    the owner's own registry, and it does not get to outlive the gate."""
    global ROOT
    key = str(which)
    if key not in _LOADED:
        if ROOT is None:
            ROOT = Path(tempfile.mkdtemp(prefix="exo-gate-p3-"))
        folder = Path(tempfile.mkdtemp(prefix="reg-", dir=str(ROOT)))
        shutil.copy(str(which), str(folder / "registry.json"))
        _LOADED[key] = (RG.registry(hub=folder), folder)
    return _LOADED[key][0]


def fleet():
    return load(FLEET_REGISTRY)


def fixture_file():
    """The gate's own registry, written once into the run's world root."""
    global ROOT
    if ROOT is None:
        ROOT = Path(tempfile.mkdtemp(prefix="exo-gate-p3-"))
    path = ROOT / "fixture-registry" / "registry.json"
    if not path.is_file():
        write(path, json.dumps(FIXTURE_REGISTRY, indent=2) + "\n")
    return path


def fixture():
    return load(fixture_file())


def persona_words():
    """The persona words a stranger's page must never carry: the owner's own,
    read from their registry at run time when this machine has it (a Codex- or
    Grok-side mind named apart from its family, and every alias target), and
    this gate's own invented one."""
    words = list(FIXTURE_PERSONAS)
    if FLEET_REGISTRY is not None:
        reg = fleet()
        for mind in reg.get("minds") or []:
            name = str(mind.get("name") or "").strip()
            if name and mind.get("kind") in ("codex", "grok") and \
                    name.upper() != str(mind.get("kind") or "").upper():
                words.append(name)
        words += [str(v) for v in (reg.get("mind_aliases") or {}).values()]
    return sorted(set(w.upper() for w in words if w))


def seed():
    return load(SEED_REGISTRY)


# ---------------------------------------------------------------------------
# R1 — the loader
# ---------------------------------------------------------------------------

def case_loader(keep):
    case("R1", "LOADER: defaults, problems, unknown keys, --check, a mutation")
    w = world("r1")
    missing = w / "not-here.json"
    reg = RG.registry(hub=w)
    check(all(k in reg for k in RG.RECORD_KEYS),
          "no file: every key of the record is present")
    check(reg["owner"] == {"name": "", "short": "", "aliases": []}
          and reg["machines"] == {} and reg["minds"] == []
          and reg["mind_aliases"] == {} and reg["lanes"]["aliases"] == {}
          and reg["surface"]["caption"] == "",
          "no file: every field is its default")
    check(reg["problems"] == [],
          "no file: NO problem — a person who has not written one is not a fault")

    bad = write(w / "broken" / "registry.json", "{ this is not json ")
    reg = RG.registry(hub=bad.parent)
    check(len(reg["problems"]) == 1, "malformed JSON: exactly one problem line")
    check(reg["problems"] and bad.name in reg["problems"][0]
          and ("JSON" in reg["problems"][0] or "json" in reg["problems"][0]),
          "malformed JSON: the line names the file and the parse error")
    check(reg["owner"]["name"] == "" and reg["minds"] == [],
          "malformed JSON: the defaults are used")

    typed = write(w / "typed" / "registry.json",
                  json.dumps({"owner": "a person", "minds": [], "lanes": {"aliases": []}}))
    reg = RG.registry(hub=typed.parent)
    check(reg["owner"] == {"name": "", "short": "", "aliases": []},
          "a wrong-typed field: that field's default")
    check(len(reg["problems"]) == 2,
          "a wrong-typed field: one problem line each (owner, lanes.aliases)")

    kept = write(w / "kept" / "registry.json",
                 json.dumps({"version": 1, "owner": {"name": "Q"},
                             "something_a_later_version_added": {"x": [1, 2]}}))
    reg = RG.registry(hub=kept.parent)
    check(reg.get("something_a_later_version_added") == {"x": [1, 2]},
          "an unknown key survives a round trip under its own name")
    check(reg["problems"] == [], "an unknown key is not a problem")

    code, out = run_child(P3_TOOLS / "exo_registry.py", "--check", "--hub", str(w))
    check(code == 0, "--check on a clean (absent) file exits 0")
    code2, out2 = run_child(P3_TOOLS / "exo_registry.py", "--check", "--hub", str(bad.parent))
    check(code2 == 2, "--check on a broken file exits 2")
    check("problem:" in out2, "--check on a broken file says what is wrong")
    code3, out3 = run_child(P3_TOOLS / "exo_registry.py", "--path", "--hub", str(w))
    check(code3 == 0 and out3.strip().endswith("registry.json"),
          "--path prints where the file is, or would be")

    # A MUTATION the gate must catch: one default taken out of the loader. The
    # address tokens are the promise "OWNER and HUMAN always mean the person",
    # and they are written down in exactly one place.
    src = (P3_TOOLS / "exo_registry.py").read_text(encoding="utf-8")
    mutated = src.replace('OWNER_TOKENS = ("OWNER", "HUMAN")',
                          'OWNER_TOKENS = ("OWNER",)', 1)
    check(mutated != src, "the mutation could be made (the default is in one place)")
    mfile = write(w / "mut" / "exo_registry.py", mutated)
    import importlib.util
    spec = importlib.util.spec_from_file_location("exo_registry_mutant", str(mfile))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hurt = False
    try:
        bad_reg = mod.registry(hub=w)
        hurt = ("HUMAN" not in mod.owner_tokens(bad_reg)
                or "human" not in mod.human_next_values(bad_reg))
    except Exception:
        hurt = True
    check(hurt, "a missing default is CAUGHT: the record loses a promise it makes")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R2 — fleet equality
# ---------------------------------------------------------------------------

# DATES, TIMES AND DURATIONS are masked everywhere: a clock moves between two
# runs however careful the fixture is, and a date or a duration in an output is
# always the clock's.
CLOCK = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:?\d{2}|Z)?)?"
    r"|\b\d{1,2}:\d{2}\b"
    r"|\b\d+(?:\.\d+)?\s*(?:s|ms|min|mins|minutes|h|hr|hrs|d|w|mo|y)\b")

# A BARE INTEGER IS NOT MASKED, because it might be the tool's own count. It is
# masked only on a line that the SAME side moves by itself between two
# back-to-back runs — A against A' — which is the only honest evidence that the
# number on that line belongs to the clock. Every other number is compared as
# it stands, so a count this build got wrong is a failure and not a blur.
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


# The note an opener gains when its `next:` word is one the registry does not
# know. Its END is fixed, so the sentence is found from there and walked back
# to its own `next:` — the opener's own words in the middle may carry quotes.
NOTE_END = "use owner, human or machine"
NOTE_MARK = "is not a word this registry knows"


def strip_note(line):
    out = line
    while True:
        at = out.find(NOTE_END)
        if at < 0:
            return out
        end = at + len(NOTE_END)
        start = out.rfind("next:", 0, end)
        if start < 0:
            return out
        if start > 0 and out[start - 1] == '"':
            start -= 1
        if end < len(out) and out[end] == '"':
            end += 1
        while start > 0 and out[start - 1] in ", ":
            start -= 1
        out = out[:start] + out[end:]
# These are renamed on purpose: an install flag is named after WHAT it
# installs, not after whose machine it is.
OLD_FLAG = re.compile(r"--install-[a-z0-9-]+")
NEW_FLAGS = ("--install-launchd", "--install-scheduler")


def renamed_flag(x, y):
    """True when two lines differ only by an install flag this build was
    ordered to rename."""
    if not OLD_FLAG.search(x) or not any(f in y for f in NEW_FLAGS):
        return False
    strip = lambda s: " ".join(OLD_FLAG.sub("<FLAG>", s).split())
    return strip(x) == strip(y)


# THE OWNER'S LETTER CHIP. The postman's chip on the tree's strip, `✉ N
# for you`, is drawn only while a letter for the owner is waiting, and its count
# moves as letters arrive and are read — it moves between two runs by itself,
# the way a clock does, and it is neither tool's doing. So its element, and the
# answer it registers in the marks table, are taken out of BOTH lines before
# they are compared; the rest of the line must still be equal, so a number
# wrong beside the chip still fails.
OWNER_CHIP = re.compile(
    r'<button class="cnt" type="button" style="color:var\(--amber-ink\)"'
    r'(?: data-mark="count:[a-z]+")?>\u2709 (?:\d+|#) for you</button>')
OWNER_MARK = re.compile(r'"count:[a-z]+": (?=\{"kind": "the notes waiting for you")')


def without_owner_chip(line):
    """The line with the owner's letter chip and its marks-table answer taken
    out. The answer is one JSON value, read to its own end — never a guess at
    where its brackets close."""
    line = OWNER_CHIP.sub("", line)
    found = OWNER_MARK.search(line)
    if found:
        try:
            _value, end = json.JSONDecoder().raw_decode(line, found.end())
        except ValueError:
            return line
        start = found.start()
        if line[end:end + 2] == ", ":
            end += 2
        elif line[start - 2:start] == ", ":
            start -= 2
        line = line[:start] + line[end:]
    return line


def owner_chip_only(x, y):
    """True when two lines differ only by the owner's letter chip."""
    if not (OWNER_CHIP.search(x) or OWNER_CHIP.search(y)
            or OWNER_MARK.search(x) or OWNER_MARK.search(y)):
        return False
    return without_owner_chip(x) == without_owner_chip(y)


def carries_private(line):
    folded = fold(line)
    return any(p.search(folded) for _w, p in PATTERNS)


def unstable_lines(a_text, a2_text, places=()):
    """The line numbers ONE side moves by itself between two runs. Their bare
    integers may be masked; nobody else's may."""
    if a_text is None or a2_text is None:
        return set()
    def prep(text):
        for place in places:
            text = text.replace(str(place[0]), str(place[1]))
        return [CLOCK.sub("#", l) for l in text.splitlines()]
    a, a2 = prep(a_text), prep(a2_text)
    return {i for i, (x, y) in enumerate(zip(a, a2)) if x != y}


def compare(name, a_text, b_text, owner_short, places=(), moving=frozenset(),
            quiet=False):
    """Byte equality after ONE clock expression and the fixture's own paths,
    with exactly TWO kinds of difference allowed and nothing else:

      1 A LINE THE SCRUB HAD TO TOUCH — the original carries a word from the
        private list, so this build was ORDERED to change it. That is the whole
        point of P3, and a line with no such word must not move.
      2 A RENAMED INSTALL FLAG — `--install-<machine>` became
        `--install-launchd` / `--install-scheduler`, named after what they
        install.
      3 THE UNKNOWN-`next:` NOTE — an opener whose `next:` value the registry
        does not know gains one note saying so (attention, never
        silence). Removing that sentence from the P3 side must give the
        original back, line for line.
      4 THE OWNER'S LETTER CHIP — `✉ N for you` and its answer, which come and
        go with the letters waiting, not with either tool. Taking the
        chip out of both lines must leave them equal.

    On a failure the first undeclared difference is printed, masked."""
    import difflib
    if a_text is None or b_text is None:
        return check(False, "%s: one side produced nothing" % name)

    def prep(text):
        for place in places:
            text = text.replace(str(place[0]), str(place[1]))
        out = []
        for i, line in enumerate(text.splitlines()):
            line = CLOCK.sub("#", line)
            if i in moving:                     # this side moves it by itself
                line = NUMBER.sub("#", line)
            out.append(line)
        return out

    a, b = prep(a_text), prep(b_text)
    counts = {"scrub": 0, "note": 0, "flag": 0, "chip": 0, "moving": len(moving)}
    bad = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for x, y in zip(a[i1:i2], b[j1:j2]):
                if carries_private(x):
                    counts["scrub"] += 1
                elif renamed_flag(x, y):
                    counts["flag"] += 1
                elif owner_chip_only(x, y):
                    counts["chip"] += 1
                elif NOTE_MARK in y and NOTE_MARK not in x and (
                        strip_note(y) == x or strip_note(y).rstrip() == x.rstrip()
                        or " ".join(strip_note(y).split()) == " ".join(x.split())):
                    counts["note"] += 1
                else:
                    bad.append((x, y))
            continue
        if tag == "insert":
            for y in b[j1:j2]:
                if NOTE_MARK in y:
                    counts["note"] += 1
                else:
                    bad.append(("(nothing)", y))
            continue
        for x in a[i1:i2]:
            bad.append((x, "(nothing)"))
        for y in b[j1:j2]:
            bad.append(("(nothing)", y))
    for x, y in (bad[:3] if not quiet else []):
        col = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), 0)
        say("      UNDECLARED difference, col %d:" % col)
        say("        original: %s" % x[max(0, col - 60):col + 140])
        say("        P3 copy : %s" % y[max(0, col - 60):col + 140])
    if quiet:
        return not bad
    chip = (" · %d owner's letter chip" % counts["chip"]) if counts["chip"] else ""
    return check(not bad, "%s: byte-identical apart from %d scrubbed · %d renamed flag "
                 "· %d note%s (%d line%s took the number mask, each proved by A vs A')"
                 % (name, counts["scrub"], counts["flag"], counts["note"], chip,
                    counts["moving"], "" if counts["moving"] == 1 else "s"))


def hub_copy(into, name):
    """A copy of the LIVE hub. The live hub is read, never written.

    ONE copy is taken and then CLONED for each side. The live hub moves while
    this runs — the heartbeat writes its pages, its stamps and its INBOX every
    few minutes — so two copies taken a minute apart are two different hubs,
    and the tools would be compared on different inputs — a board's six-week
    tick counts can differ for that reason alone.

    Both sides get a folder of the SAME name in different parents: the hub
    folder's own basename is the hub project's display name on every page."""
    dst = into / name / "hub"
    pristine = into / "pristine"
    if not pristine.exists():
        def ignore(d, names):
            out = [n for n in names
                   if n in ("scratch", "__pycache__", ".git") or n.endswith(".html")]
            if Path(d).name == "carry":
                out.extend(n for n in names if n == "backups")
            return out
        shutil.copytree(str(HUB), str(pristine), ignore=ignore, symlinks=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(pristine), str(dst), symlinks=True)
    return dst


def frozen_projects(into):
    """A projects root FROZEN for the length of this case: every project's
    STATUS.md and OPENER*.md, copied once and read by all three sides.

    The real projects root is written by whoever is working right now — an
    opener rewritten between two sides makes them differ for a reason that is
    neither tool's: a lane can move between the A run and the B run. Their
    `.git` folders are deliberately NOT
    copied: every side then reads 'not a repo' for every project, the same way,
    which is a fixture and not a lie."""
    dst = into / "projects"
    if dst.exists():
        return dst
    dst.mkdir(parents=True)
    real = json.loads((Path(REAL_HOME_RAW) / "orchestrator-sync" / "machine.json")
                      .read_text(encoding="utf-8"))
    src = Path((real.get("roots") or {}).get("projects") or (Path(REAL_HOME_RAW) / "Projects"))
    try:
        entries = sorted(src.iterdir())
    except OSError:
        return dst
    for entry in entries:
        try:
            if entry.name.startswith(".") or not entry.is_dir():
                continue
        except OSError:
            continue
        keep = [f for f in ("STATUS.md",) if (entry / f).is_file()]
        openers = sorted(entry.glob("OPENER*.md"))
        if not keep and not openers:
            continue
        (dst / entry.name).mkdir(parents=True, exist_ok=True)
        for name in keep:
            shutil.copy2(str(entry / name), str(dst / entry.name / name))
        for opener in openers:
            shutil.copy2(str(opener), str(dst / entry.name / opener.name))
    return dst


def side(w, label, tools_src, orch_src):
    """One side of the equality: a hub copy with ITS OWN tools/ and
    orchestrator.py, and a fake home whose machine.json points at it."""
    hub = hub_copy(w, label)
    shutil.rmtree(str(hub / "tools"), ignore_errors=True)
    shutil.copytree(str(tools_src), str(hub / "tools"))
    shutil.copy(str(orch_src), str(hub / "orchestrator.py"))
    home = w / ("home-" + label)
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    real = json.loads((Path(REAL_HOME_RAW) / "orchestrator-sync" / "machine.json")
                      .read_text(encoding="utf-8"))
    roots = dict(real.get("roots") or {})
    roots["orchestrator"] = str(hub)
    roots["projects"] = str(frozen_projects(w))
    machine_record(home, hub, name=real.get("name") or "north", roots=roots)
    return hub, home


def case_fleet_equality(keep):
    case("R2", "FLEET EQUALITY: the original tool and the P3 copy, same fixture")
    if BASE_TOOLS is None:
        skip("the tools as they stood before the registry sit beside a build (base/); an "
             "installed hub has only the tools it runs, so there is nothing to compare with")
        return
    if FLEET_REGISTRY is None:
        skip("the owner's own registry is not on this machine, so there is no fleet to "
             "prove equal")
        return
    if not (Path(REAL_HOME_RAW) / "orchestrator-sync" / "machine.json").is_file():
        check(False, "no machine record on this machine — the fixture cannot be built")
        return
    w = world("r2")
    a_hub, a_home = side(w, "a", BASE_TOOLS, BASE_ORCH)
    # A SECOND COPY OF THE SAME SIDE. Running the original tool twice is the
    # only honest way to learn which lines it moves by itself, and a bare
    # integer is masked ONLY on those.
    a2_hub, a2_home = side(w, "a2", BASE_TOOLS, BASE_ORCH)
    b_hub, b_home = side(w, "b", P3_TOOLS, P3_ORCH)
    shutil.copy(str(FLEET_REGISTRY), str(b_hub / "registry.json"))
    reg = RG.registry(hub=b_hub)
    owner_short = (reg["owner"]["short"] or "").strip().lower()
    check(not reg["problems"], "the fleet registry loads with no problem")

    a_env = env_for(a_home)
    a2_env = env_for(a2_home)
    b_env = env_for(b_home, registry=b_hub / "registry.json")
    # The fixture's OWN paths are not the tool's output: the two sides live in
    # two folders and the page prints where it stands.
    places = []
    for folder, mark in ((a_hub, "<HUB>"), (a2_hub, "<HUB>"), (b_hub, "<HUB>"),
                         (a_home, "<HOME>"), (a2_home, "<HOME>"), (b_home, "<HOME>")):
        places.append((str(Path(folder).resolve()), mark))
        places.append((str(folder), mark))

    for flag, label in (("--chat", "collect-openers --chat"),
                        ("--table", "collect-openers --table")):
        _c, a_out = run_child(a_hub / "tools" / "collect-openers.py", flag, env=a_env)
        _c, a2_out = run_child(a2_hub / "tools" / "collect-openers.py", flag, env=a2_env)
        _c, b_out = run_child(b_hub / "tools" / "collect-openers.py", flag, env=b_env)
        compare(label, a_out, b_out, owner_short, places,
                unstable_lines(a_out, a2_out, places))

    for hub, env in ((a_hub, a_env), (a2_hub, a2_env), (b_hub, b_env)):
        run_child(hub / "tools" / "collect-openers.py", "--write-tree", env=env)
    compare("collect-openers --write-tree (the TREE.md it writes)",
            read(a_hub / "TREE.md"), read(b_hub / "TREE.md"), owner_short, places,
            unstable_lines(read(a_hub / "TREE.md"), read(a2_hub / "TREE.md"), places))

    for hub, env in ((a_hub, a_env), (a2_hub, a2_env), (b_hub, b_env)):
        run_child(hub / "tools" / "collect-openers.py", "--html", env=env)
    compare("collect-openers --html (tree.html)",
            read(a_hub / "tree.html"), read(b_hub / "tree.html"), owner_short, places,
            unstable_lines(read(a_hub / "tree.html"), read(a2_hub / "tree.html"), places))

    for hub, env in ((a_hub, a_env), (a2_hub, a2_env), (b_hub, b_env)):
        run_child(hub / "orchestrator.py", env=env, timeout=420)
    compare("orchestrator.py (board.html)",
            read(a_hub / "board.html"), read(b_hub / "board.html"), owner_short, places,
            unstable_lines(read(a_hub / "board.html"), read(a2_hub / "board.html"), places))

    pairs = [
        (("who-is-live.py", ["--pen"]), "who-is-live.py --pen"),
        (("claim.py", ["--list"]), "claim.py --list"),
        (("asked.py", ["--count"]), "asked.py --count"),
        (("improvements.py", ["--count"]), "improvements.py --count"),
        (("ideas.py", ["--count"]), "ideas.py --count"),
        (("pulse.py", ["--help"]), "pulse.py --help"),
    ]
    for (tool, args), label in pairs:
        _c, a_out = run_child(a_hub / "tools" / tool, *args, env=a_env)
        _c, a2_out = run_child(a2_hub / "tools" / tool, *args, env=a2_env)
        _c, b_out = run_child(b_hub / "tools" / tool, *args, env=b_env)
        compare(label, a_out, b_out, owner_short, places,
                unstable_lines(a_out, a2_out, places))

    # mail.py --read on an address the fixture holds a letter for
    addr = "NORTH/gate-fixture"
    line = "- 2026-09-22 \u00b7 to: %s \u00b7 Exocortex \u00b7 a fixture letter \u00b7 no reply needed\n" % addr
    for hub in (a_hub, b_hub):
        with io.open(str(hub / "INBOX.md"), "a", encoding="utf-8") as handle:
            handle.write(line)
    with io.open(str(a2_hub / "INBOX.md"), "a", encoding="utf-8") as handle:
        handle.write(line)
    _c, a_out = run_child(a_hub / "tools" / "mail.py", "--read", addr, "--hub", str(a_hub), env=a_env)
    _c, a2_out = run_child(a2_hub / "tools" / "mail.py", "--read", addr, "--hub", str(a2_hub), env=a2_env)
    _c, b_out = run_child(b_hub / "tools" / "mail.py", "--read", addr, "--hub", str(b_hub), env=b_env)
    compare("mail.py --read <a fixture address>", a_out, b_out, owner_short, places,
            unstable_lines(a_out, a2_out, places))

    # i-am.py: the stamp JSON, minus its clock
    for hub, home, env in ((a_hub, a_home, a_env), (b_hub, b_home, b_env)):
        run_child(hub / "tools" / "i-am.py", "OPUS", "EXTRA",
                  "ACT \u2014 Gate/Fixture: the equality case", "--quiet", env=env)
    def stamp(hub):
        found = sorted(Path(hub).glob("live-*-opus.json"))
        if not found:
            return None
        try:
            d = json.loads(found[-1].read_text(encoding="utf-8"))
        except Exception:
            return None
        d.pop("when", None)
        for s in d.get("sessions") or []:
            s.pop("when", None)
        return json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False)
    compare("i-am.py <MIND> <EFFORT> \"<title>\" (the stamp, minus its `when`)",
            stamp(a_hub), stamp(b_hub), owner_short, places)

    # THE MUTATION. A number mask that swallowed every integer would make this
    # gate blind to the one thing it is for: a count this build got wrong. One
    # integer is bumped on a STABLE line of side B's board — a line A and A'
    # agree on, so the mask does not reach it — and R2 must FAIL on it.
    board_a, board_b = read(a_hub / "board.html"), read(b_hub / "board.html")
    board_a2 = read(a2_hub / "board.html")
    moving = unstable_lines(board_a, board_a2, places)
    hurt, at = None, None
    for index, raw in enumerate(( board_b or "").splitlines()):
        if index in moving or index >= len((board_a or "").splitlines()):
            continue
        if raw != (board_a or "").splitlines()[index]:
            continue
        found = re.search(r"\b(\d+)\b", raw)
        if not found:
            continue
        hurt, at = raw[:found.start(1)] + str(int(found.group(1)) + 7) + raw[found.end(1):], index
        break
    if hurt is None:
        check(False, "a stable line with a number could not be found to mutate")
    else:
        rows = (board_b or "").splitlines(True)
        rows[at] = hurt + ("\n" if rows[at].endswith("\n") else "")
        before = list(checks), list(fails)
        caught = not compare("THE MUTATION", board_a, "".join(rows),
                             owner_short, places, moving, quiet=True)
        checks[:], fails[:] = before                # the mutation's own check does not count
        check(caught, "a number this build got wrong on a stable line FAILS R2 "
                      "(line %d, one integer bumped by seven)" % (at + 1))

    # THE CHIP'S ALLOWANCE IS NARROW. On side A's own strip line — a
    # chip added forgiven; the same line with a count beside the chip bumped by
    # seven still FAILS. Built from the line itself, so it proves the same
    # thing whether or not a letter is waiting today.
    tree_a = read(a_hub / "tree.html") or ""
    strip = next((l for l in tree_a.splitlines() if '<div class="strip">' in l), None)
    first = re.search(r">(\d+) active</button>", strip or "")
    if strip is None or first is None:
        check(False, "side A's tree.html has no strip line with its active count")
    else:
        chip_el = ('<button class="cnt" type="button" style="color:var(--amber-ink)" '
                   'data-mark="count:owner">\u2709 3 for you</button>')
        with_chip = strip[:first.end()] + chip_el + strip[first.end():]
        bumped = (with_chip[:first.start(1)] + str(int(first.group(1)) + 7)
                  + with_chip[first.end(1):])
        before = list(checks), list(fails)
        forgiven = compare("THE CHIP", strip, with_chip, owner_short, quiet=True)
        caught = not compare("THE CHIP, A COUNT BESIDE IT", strip, bumped, owner_short,
                             quiet=True)
        checks[:], fails[:] = before
        check(forgiven and caught, "the owner's letter chip is forgiven and nothing beside "
              "it: a chip added to the strip passes, the same strip with its active count "
              "bumped by seven FAILS R2")

    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# a stranger's world — small on purpose
# ---------------------------------------------------------------------------

def stranger(w, name="alpha", registry=None, minds=(), openers=()):
    """A stranger's hub: a folder, a machine record, a project with an opener,
    and whatever the caller wants the pulse to have seen. NOT a program tree
    with a git repository — nothing here needs one, and a world that builds one
    takes a minute it does not have to."""
    home = w / "home"
    hub = home / "Exocortex"
    (hub).mkdir(parents=True, exist_ok=True)
    (home / "Projects").mkdir(parents=True, exist_ok=True)
    (home / ".claude" / "projects").mkdir(parents=True, exist_ok=True)
    machine_record(home, hub, name=name)
    write(hub / "STATUS.md", "## Now\nA stranger's first hour.\n\n## To do\n- [ ] one thing\n\n## Important\nnothing yet\n")
    write(hub / "INBOX.md", "# INBOX\n")
    write(hub / "IDEAS.md", "# IDEAS\n")
    write(hub / "claims.json", json.dumps({"claims": []}))
    write(hub / "dossier" / "TAUGHT.md", "# TAUGHT\n")
    write(hub / "design" / "BUILD-QUEUE.md", "# BUILD QUEUE\n")
    if registry is not None:
        shutil.copy(str(registry), str(hub / "registry.json"))
    for folder, body in openers:
        root = home / "Projects" / folder
        root.mkdir(parents=True, exist_ok=True)
        write(root / "STATUS.md", "## Now\nsomething\n\n## To do\n- [ ] a thing\n\n## Important\n-\n")
        write(root / "OPENER.md", body)
    if minds:
        import datetime
        now = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        write(hub / ("live-sessions-%s.json" % name),
              json.dumps({"machine": name, "when": now,
                          "live_minutes": 10, "sessions": list(minds)}, indent=2))
    return home, hub


def opener_text(lane, nxt, model="OPUS \u00b7 EXTRA"):
    return ("lane: %s\nwritten: 2026-09-22T09:00:00-07:00\nby: a session\n"
            "on: ALPHA\nhead: none\nstatus_updated: 2026-09-22T09:00:00-07:00\n"
            "where: a stranger's lane\nnext: %s\ndepends_on: nothing\n"
            "open_in: the project folder \u00b7 ACT \u2014 %s: go\nmodel: %s\n"
            "judgment: none\n---\nread the project status/memory first.\n"
            % (lane, nxt, lane, model))


def render_stranger_tree(w, registry, minds=(), openers=()):
    home, hub = stranger(w, registry=registry, minds=minds, openers=openers)
    env = env_for(home, registry=hub / "registry.json")
    code, out = run_child(P3_TOOLS / "collect-openers.py", "--html",
                          env=dict(env, COLLECT_OPENERS_OUT=str(w / "tree.html")))
    return home, hub, code, out, read(w / "tree.html")


# ---------------------------------------------------------------------------
# R3 — the stranger's page
# ---------------------------------------------------------------------------

def case_stranger(keep):
    case("R3", "STRANGER: no persona root, no persona token, no caption")
    w = world("r3")
    minds = [{"machine": "alpha", "kind": "codex", "mind": "", "model": "gpt-5.6",
              "id": "rollout-2026-09-22T09-00-00-aaaa", "minutes_ago": 3,
              "cwd": str(w), "dir": "Alpha", "in_hub": False}]
    openers = [("alpha-one", opener_text("Alpha/One", "owner")),
               ("alpha-two", opener_text("Alpha/Two", "machine")),
               ("alpha-three", opener_text("Alpha/Three", FIXTURE_REGISTRY["owner"]["short"]))]
    home, hub, code, out, page = render_stranger_tree(w, SEED_REGISTRY, minds, openers)
    check(code == 0 and page, "the page renders for a stranger")
    page = page or ""
    personas = persona_words()
    check(not any(("--m-%s" % p.lower()) in page for p in personas),
          "no colour token for a persona nobody here has")
    tokens = re.findall(r"--m-[a-z0-9-]+", page)
    check(not tokens, "no per-mind colour token at all (%d found)" % len(tokens))
    check(not any(re.search(r'data-root="mind"[^>]*data-mind="%s"' % re.escape(p), page)
                  for p in personas),
          "no root for a mind this person never had")
    check("CODEX" in page, "a codex transcript shows as CODEX \u2014 its own family's word")
    check("laid out as a cortex" not in page,
          "no caption line (the registry names none)")
    check("rewritten by every orchestrator.py run</p>" in page,
          "and no dangling separator where the caption would have been")

    env = env_for(home, registry=hub / "registry.json")
    code, table = run_child(P3_TOOLS / "collect-openers.py", "--table", env=env)
    check("Alpha/One" in table, "the lanes are listed")
    one = [l for l in table.splitlines() if l.startswith("Alpha/One")]
    two = [l for l in table.splitlines() if l.startswith("Alpha/Two")]
    three = [l for l in table.splitlines() if l.startswith("Alpha/Three")]
    check(bool(one) and "amber" in one[0], "`next: owner` grades amber")
    check(bool(two) and "amber" not in two[0], "`next: machine` does not")
    check(bool(three) and "amber" in three[0],
          "a word this registry does not know is counted as waiting on a person")
    code, card = run_child(P3_TOOLS / "collect-openers.py", "--expand", "Alpha/Three", env=env)
    check("is not a word this registry knows" in card,
          "\u2026and it is SAID on that lane, never silently")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R4 — the next: values
# ---------------------------------------------------------------------------

def case_next_values(keep):
    case("R4", "NEXT VALUES: machine, owner, human, the short word, the unknown")
    w = world("r4")
    reg = fixture()
    short = reg["owner"]["short"]
    rows = [
        ("machine", "machine", "machine", False, False),
        ("MACHINE", "machine", "machine", False, False),
        ("owner", "human", "human", False, False),
        ("Human", "human", "human", False, False),
        (short, "human", "human", False, True),
        (short.upper(), "human", "human", False, True),
        ("somebody-else", "human", "human", True, True),
    ]
    for value, want_fleet, want_seed, warn_fleet, warn_seed in rows:
        side_f, why_f = RG.next_side(fixture(), value)
        side_s, why_s = RG.next_side(seed(), value)
        check(side_f == want_fleet,
              "an owner's registry: `%s` \u2192 %s" % (value, want_fleet))
        check(bool(why_f) == warn_fleet,
              "an owner's registry: `%s` %s a problem line"
              % (value, "carries" if warn_fleet else "carries no"))
        check(side_s == want_seed, "seed registry: `%s` \u2192 %s" % (value, want_seed))
        check(bool(why_s) == warn_seed,
              "seed registry: `%s` %s a problem line"
              % (value, "carries" if warn_seed else "carries no"))
    check(RG.machine_next_values() == ["machine"], "the machine side is exactly `machine`")
    check(set(RG.human_next_values(seed())) == {"owner", "human"},
          "with no owner name the human side is exactly owner and human")
    drop(w, keep)


# ---------------------------------------------------------------------------
# R5 — the owner's mailbox
# ---------------------------------------------------------------------------

def case_owner_address(keep):
    case("R5", "OWNER ADDRESS: OWNER reaches the mailbox, the old word still does")
    w = world("r5")
    home, hub = stranger(w, registry=fixture_file())
    shutil.copytree(str(P3_TOOLS), str(hub / "tools"))
    env = env_for(home, registry=hub / "registry.json")
    mail = hub / "tools" / "mail.py"

    code, out = run_child(mail, "--send", "OWNER", "Exocortex",
                          "a letter for the person", "no reply needed",
                          "--no-push", "--hub", str(hub), env=env)
    check(code == 0, "mail.py --send OWNER \u2026 sends")
    code, out = run_child(mail, "--read", "OWNER", "--hub", str(hub), env=env)
    check("a letter for the person" in out, "--read OWNER finds it")

    reg = RG.registry(hub=hub)
    old = (reg["owner"]["short"] or "").upper()
    code, out_old = run_child(mail, "--read", old, "--hub", str(hub), env=env)
    check("a letter for the person" in out_old,
          "under an owner's registry the owner's own word finds the same letter")

    code, out = run_child(mail, "--ack", "OWNER", "--hub", str(hub), env=env)
    check(code == 0 and ("acked" in out or "nothing to ack" in out),
          "--ack OWNER answers (no note was waiting in this world: %s)"
          % out.splitlines()[0][:60] if out else "--ack OWNER answers")

    # A postman state file that carries ONLY the old key. The postman is loaded
    # in this process, so it is pointed at the world's own registry for the
    # length of the case, and never at the one this machine keeps.
    import importlib.util
    saved_registry = os.environ.get("EXO_REGISTRY_JSON")
    os.environ["EXO_REGISTRY_JSON"] = str(hub / "registry.json")
    spec = importlib.util.spec_from_file_location("pm_under_test", str(hub / "tools" / "postman.py"))
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    legacy_key = (reg["owner"]["short"] or "").lower()
    state = {"letters": {"pm-000000000001": {
        "state_kind": "for_%s" % legacy_key, "state": "waiting",
        legacy_key: {"raised": {"when": "2026-09-22T09:00:00-07:00"},
                     "push": {"state": "off"}}}}}
    entry = state["letters"]["pm-000000000001"]
    block = pm.owner_block(entry)
    check(block.get("raised", {}).get("when") == "2026-09-22T09:00:00-07:00",
          "a state file with only the old key is READ as if it were the new one")
    check("owner" in entry and legacy_key not in entry,
          "\u2026and after one read it carries the NEW key, with nothing lost")
    check(pm.state_is_for_owner("for_%s" % legacy_key) and pm.state_is_for_owner("for_owner"),
          "both spellings of the state word are understood")
    fresh = {}
    check(pm.owner_block(fresh) == {} and "owner" not in fresh,
          "a read never invents a block that was not there")
    check(pm.owner_block(fresh, create=True) == {} and "owner" in fresh,
          "\u2026and a write creates it under the new key only when asked")
    if saved_registry is None:
        os.environ.pop("EXO_REGISTRY_JSON", None)
    else:
        os.environ["EXO_REGISTRY_JSON"] = saved_registry
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R6 — asked and improvements
# ---------------------------------------------------------------------------

BUILD_QUEUE_FIXTURE = (
    "# BUILD QUEUE\n\n"
    "| id | lane | brief | gate | model | state | note |\n"
    "|---|---|---|---|---|---|---|\n"
    "| BQ-900 | Alpha/One | design/A-BRIEF.md | tools/gate-a.py | opus | listed | "
    "\u00abmake the widget blue\u00bb 2026-09-02 \u00b7 %s said \"make it blue\" |\n")


def case_asked(keep):
    case("R6", "ASKED / IMPROVEMENTS: the owner's word counts, or says why not")
    w = world("r6")
    name = fixture()["owner"]["name"]
    for label, registry, want_asks in (("owner", fixture_file(), True),
                                       ("seed", SEED_REGISTRY, False)):
        sub = w / label
        sub.mkdir(parents=True, exist_ok=True)
        home, hub = stranger(sub, registry=registry)
        shutil.copytree(str(P3_TOOLS), str(hub / "tools"))
        proj = home / "Projects" / "one"
        proj.mkdir(parents=True, exist_ok=True)
        write(proj / "STATUS.md",
              "## Now\nhere\n\n## To do\n"
              "- [ ] 2026-09-01 %s asked for the widget to be blue\n"
              "- [ ] 2026-09-02 tidy the shed\n\n## Important\n-\n" % name)
        write(hub / "design" / "BUILD-QUEUE.md", BUILD_QUEUE_FIXTURE % name)
        env = env_for(home, registry=hub / "registry.json")
        code, out = run_child(hub / "tools" / "asked.py", "--count",
                              "--hub", str(hub), "--projects", str(home / "Projects"), env=env)
        if want_asks:
            check("ASKED \u2014 1 open" in out or "ASKED \u2014 2 open" in out,
                  "an owner's registry: the owner's own word counts an ask (%s)"
                  % out.splitlines()[0][:70])
            check("no owner name in registry.json" not in out,
                  "an owner's registry: no reason line is printed")
        else:
            check("nothing open" in out or "ASKED \u2014 0" in out,
                  "seed registry: nothing counts as an ask (%s)" % out.splitlines()[0][:60])
            check("0 by name" in out and "no owner name in registry.json" in out,
                  "seed registry: and the tool says the honest number and why, in "
                  "one line (%s)" % (out.strip().splitlines()[-1][:80] if out else ""))
        code, out = run_child(hub / "tools" / "improvements.py", "--count",
                              "--hub", str(hub), env=env)
        check("1 listed" in out, "%s registry: the row is READ, quote or no quote (%s)"
              % (label, out.splitlines()[0][:70] if out else ""))
        run_child(hub / "tools" / "improvements.py", "--write", "--hub", str(hub), env=env)
        page = read(hub / "improvements.html") or ""
        # The quote stands twice when the owner's word is known: once as the
        # row's own words, once inside the note it came from. Once when it is
        # not: the note alone.
        check(page.count("make it blue") == (2 if want_asks else 1),
              "%s registry: the owner's quoted words are %s"
              % (label, "read off the row" if want_asks else "not invented"))
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R7 — the minds
# ---------------------------------------------------------------------------

def case_minds(keep):
    case("R7", "MINDS: names read off what is there, vendors off the id, hues distinct")
    w = world("r7")
    rows = [
        ("claude", "claude-fable-5-1", "FABLE", "Anthropic"),
        ("claude", "claude-sonnet-4-5", "SONNET", "Anthropic"),
        ("codex", "gpt-5.6", "CODEX", "OpenAI"),
        ("", "acme-9", "ACME", "Acme"),
    ]
    for kind, model, want_name, want_vendor in rows:
        got = RG.mind_name(seed(), kind, model)
        check(got == want_name, "%s \u2192 %s" % (model, want_name))
        check(RG.mind_vendor(seed(), got, model) == want_vendor,
              "%s \u2192 vendor %s" % (model, want_vendor))
    hues = [RG.mind_hue(seed(), "MIND%d" % i, i) for i in range(8)]
    check(len(set(hues)) == 8, "eight unlisted minds get eight distinct hues")
    check(all(h for h in hues), "and every one of them is a real colour")
    ninth = RG.mind_hue(seed(), "MIND8", 8)
    check(ninth == hues[0], "the ninth wraps the palette rather than failing")
    for bad in (None, "", 123, {"x": 1}):
        try:
            RG.mind_name(seed(), bad, bad)
            RG.mind_vendor(seed(), bad, bad)
            RG.mind_hue(seed(), bad, 0)
            ok = True
        except Exception:
            ok = False
        check(ok, "nothing raises on %r" % (bad,))

    minds = [{"machine": "alpha", "kind": "claude", "mind": "", "model": "claude-fable-5-1",
              "id": "aaaaaa", "minutes_ago": 1, "cwd": str(w), "dir": "A", "in_hub": False},
             {"machine": "alpha", "kind": "claude", "mind": "", "model": "claude-sonnet-4-5",
              "id": "bbbbbb", "minutes_ago": 2, "cwd": str(w), "dir": "B", "in_hub": False},
             {"machine": "alpha", "kind": "codex", "mind": "", "model": "gpt-5.6",
              "id": "rollout-cccccc", "minutes_ago": 3, "cwd": str(w), "dir": "C", "in_hub": False},
             {"machine": "alpha", "kind": "", "mind": "", "model": "acme-9",
              "id": "dddddd", "minutes_ago": 4, "cwd": str(w), "dir": "D", "in_hub": False}]
    _home, _hub, code, out, page = render_stranger_tree(w, SEED_REGISTRY, minds, [])
    page = page or ""
    check(code == 0, "the stranger's page renders with four minds it has never met")
    for want in ("FABLE", "SONNET", "CODEX", "ACME"):
        check(('data-mind="%s"' % want) in page, "the tree draws a root for %s" % want)
    check('>Acme<' in page or "Acme" in page, "and reads Acme off the id it came with")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R13 — the install flags
# ---------------------------------------------------------------------------

def case_install_flags(keep):
    case("R13", "INSTALL FLAGS: named after what they install, the old spelling kept")
    w = world("r13")
    # The owner's machines when their registry is here (the old spellings are
    # THEIR machines' names), this gate's own two machines otherwise.
    reg = fleet() if FLEET_REGISTRY is not None else fixture()
    machines = {kind: [n for n in RG.machine_names(reg)
                       if RG.machine_os(reg, n) in want]
                for kind, want in (("launchd", ("macos", "darwin")),
                                   ("scheduler", ("windows", "win32", "nt")))}
    kinds = (("launchd", "--install-launchd"), ("scheduler", "--install-scheduler"))
    if BASE_TOOLS is None or FLEET_REGISTRY is None:
        skip("the byte-for-byte half needs the tools as they stood before the registry and "
             "the owner's own registry (%s); the seed half below still runs"
             % ("an installed hub has no base/" if BASE_TOOLS is None
                else "this machine's registry names nobody"))
        kinds = ()
    else:
        home, hub = stranger(w, registry=FLEET_REGISTRY)
        shutil.copytree(str(P3_TOOLS), str(hub / "tools"))
        old_hub, old_home = w / "old" / "Exocortex", w / "old" / "home"
        old_hub.mkdir(parents=True)
        shutil.copytree(str(BASE_TOOLS), str(old_hub / "tools"))
        machine_record(old_home, old_hub, name=(machines["launchd"] or ["north"])[0])
        env = env_for(home, registry=hub / "registry.json")
        old_env = env_for(old_home)

    for kind, flag in kinds:
        named = machines[kind]
        check(len(named) == 1,
              "the registry names one %s machine (%d)" % (kind, len(named)))
        if not named:
            continue
        was = "--install-%s" % named[0].lower()
        _c, old_out = run_child(old_hub / "tools" / "pulse.py", was, env=old_env)
        _c, new_out = run_child(hub / "tools" / "pulse.py", flag, env=env)
        _c, alias_out = run_child(hub / "tools" / "pulse.py", was, env=env)
        # The scheduler form prints the hub with the OTHER separator, so both
        # spellings of each folder are folded or the two sides differ for the
        # fixture's reason and not the tool's.
        places = []
        for folder, mark in ((old_hub, "<HUB>"), (hub, "<HUB>"),
                             (old_home, "<HOME>"), (home, "<HOME>")):
            places.append((str(folder), mark))
            places.append((str(folder).replace("/", "\\"), mark))
        def fold_places(text):
            for a, b in places:
                text = (text or "").replace(a, b)
            return text
        check(fold_places(new_out) == fold_places(old_out),
              "`%s` prints what the old flag printed, byte for byte" % flag)
        check(fold_places(alias_out) == fold_places(old_out),
              "and the old spelling still does too (%s, one release only)"
              % masked(named[0]))

    # Under the seed nobody has that machine, so the old spelling is nobody's.
    seed_home, seed_hub = stranger(w / "seed", registry=SEED_REGISTRY, name="alpha")
    shutil.copytree(str(P3_TOOLS), str(seed_hub / "tools"))
    seed_env = env_for(seed_home, registry=seed_hub / "registry.json")
    for kind in ("launchd", "scheduler"):
        named = machines[kind]
        if not named:
            continue
        was = "--install-%s" % named[0].lower()
        code, out = run_child(seed_hub / "tools" / "pulse.py", was, env=seed_env)
        check("unknown flag" in out.lower() or "unknown" in out.lower() or code != 0,
              "seed registry: the old spelling is refused as an unknown flag "
              "(%s)" % (out.splitlines()[0][:70] if out else "no output"))
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R14 — the memory map's own names
# ---------------------------------------------------------------------------

def case_logical_names(keep):
    case("R14", "MEMORY NAMES: a name the map already carries is never renamed")
    w = world("r14")
    sync = SYNC_DIR / "sync.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("sync_under_test", str(sync))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        check(False, "sync.py could not be read as a module: %s" % exc)
        drop(w, keep)
        return

    # A PROGRAM TREE, nothing in the map yet: a root's own folder is named
    # after the root, and nobody's old folder name is invented.
    fresh = mod.logical_for("orchestrator", "")
    check(fresh == "ORCHESTRATOR",
          "a fresh hub-root memory folder is named ORCHESTRATOR (%s)" % fresh)
    check(mod.logical_for("projects", "") == "PROJECTS-ROOT"
          and mod.logical_for("home", "") == "HOME",
          "and the other roots are named the way they always were")
    check(mod.logical_for("projects", "Some Project") == "Some Project",
          "a project keeps its own folder name")

    # A LEGACY BRAIN whose map already carries the hub folder under a name of
    # its own: the map pins it BEFORE logical_for is ever asked, so the name
    # this build changed can never reach it.
    reg = fixture()
    old_name = RG.hub_key(reg, "")
    check(bool(old_name), "the registry records the name that map already uses")
    home = w / "home"
    hub = home / "Exocortex"
    claude = home / ".claude" / "projects"
    munged = "-" + str(hub).strip("/").replace("/", "-").replace(" ", "-")
    munged = re.sub(r"[^A-Za-z0-9]", "-", str(hub))
    (claude / munged / "memory").mkdir(parents=True)
    write(claude / munged / "memory" / "MEMORY.md", "# a memory\n")
    (home / "Projects").mkdir(parents=True)
    hub.mkdir(parents=True, exist_ok=True)
    pinned = {old_name: {"root": "orchestrator", "rel": "",
                         "munged": {"north": munged}}}
    machine = {"name": "north",
               "roots": {"orchestrator": str(hub), "projects": str(home / "Projects"),
                         "claude": str(home / ".claude"), "home": str(home)}}
    saved_home = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        found, _notes = mod.discover_memories(machine, pinned, None)
    except Exception as exc:
        found = {"(raised)": str(exc)}
    finally:
        if saved_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = saved_home
    check(old_name in found,
          "the map's own name for the hub folder is UNCHANGED after a walk "
          "(%s)" % ", ".join(masked(k) if carries_private(k) else k for k in found))
    check("ORCHESTRATOR" not in found,
          "and nothing renamed it to the fresh-folder name")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R8 — the lane words
# ---------------------------------------------------------------------------

ORIGINAL_TABLES = {
    # (the helper that answers it, the module-level name it used to live under)
    "families": ("lane_family", "FAMILY_PREFIXES"),
    "aliases": ("lane_folder", "ALIASES"),
    "groups": ("lane_group", "SKY_ALIASES"),
    "mentions": ("lane_mention", "aliases"),
    "hub": ("hub_words", "HUB_WORDS"),
}


def case_lane_words(keep):
    case("R8", "LANE WORDS: every word of the five tables still maps, and no table is left")
    if FLEET_REGISTRY is None:
        skip("the five tables are the OWNER's lane words, and this machine's registry "
             "names nobody; the half that proves no table is left in the code still runs")
        lane_tables_gone()
        return
    reg = fleet()
    aliases = RG.lane_aliases(reg)
    hub_words = RG.hub_words(reg)
    check(len(hub_words) == 5, "the five hub words are recorded (%d)" % len(hub_words))
    lanes = [(k, v) for k, v in aliases.items() if str(v).lower() != "hub"]
    check(len(lanes) == 11, "the eleven lane words are recorded (%d)" % len(lanes))
    bad = [k for k, v in lanes if RG.lane_folder(reg, k) != v]
    check(not bad, "every lane word maps to the folder it always did (%d wrong)" % len(bad))
    fams = RG.lane_families(reg)
    check(len(fams) == 8, "the eight family prefixes are recorded (%d)" % len(fams))
    bad = [k for k, v in fams.items() if RG.lane_family(reg, k) != v]
    check(not bad, "every family prefix still names its family (%d wrong)" % len(bad))
    check(RG.lane_family(reg, "not-a-family-name") == "not-a-family-name",
          "a name no prefix catches is its own family")
    groups = RG.lane_groups(reg)
    check(len(groups) == 20, "the twenty sky words are recorded (%d)" % len(groups))
    bad = [k for k, v in groups.items() if RG.lane_group(reg, k) != v]
    check(not bad, "every sky word still names its column (%d wrong)" % len(bad))
    ments = RG.lane_mentions(reg)
    check(len(ments) == 17, "the seventeen mention words are recorded (%d)" % len(ments))
    check(len(RG.not_lane_words(reg)) == 4, "the four not-a-lane words are recorded")
    check(len(RG.hub_folders(reg)) == 2, "both names this hub has had are recorded")
    lane_tables_gone()


def lane_tables_gone():
    """The tables themselves are gone from the code."""
    gone = {
        P3_TOOLS / "collect-openers.py": ["FAMILY_PREFIXES", "SKY_ALIASES", "SKY_NOT_LANES",
                                          "HUB_WORDS", "MIND_ORDER", "OPENAI_MINDS",
                                          "MIND_ALIAS", "VENDOR"],
        P3_ORCH: ["FAMILY_PREFIXES"],
        P3_TOOLS / "exo_common.py": ["MINDS"],
        P3_TOOLS / "i-am.py": ["MIND_ALIASES"],
    }
    for path, names in gone.items():
        text = read(path) or ""
        left = [n for n in names
                if re.search(r"(?<![A-Za-z0-9_])%s\s*=" % re.escape(n), text)]
        check(not left, "%s carries no such table any more (%s)"
              % (Path(path).name, ", ".join(left) or "none left"))


# ---------------------------------------------------------------------------
# R9 — the scrub
# ---------------------------------------------------------------------------

SHIPPED = [
    "tools/exo_registry.py", "tools/collect-openers.py", "tools/postman.py",
    "tools/mail.py", "tools/exo_common.py", "tools/i-am.py", "tools/claim.py",
    "tools/who-is-live.py", "tools/asked.py", "tools/improvements.py",
    "tools/ideas.py", "tools/pulse.py", "orchestrator.py",
    "sync/sync.py", "sync/install.py", "sync/carrier_preflight.py",
    "sync/add-root.py", "sync/manifest.base.json", "sync/install/jobs.json",
    "sync/install/templates/INSTALL-WATCHERS.md.tmpl",
    "sync/install/templates/sync_auto.py.tmpl",
    "sync/install/templates/launchd.plist.tmpl",
    "sync/install/templates/task.ps1.tmpl",
    "templates/registry.json", "templates/dot-gitignore",
    "templates/dot-gitattributes", "templates/installed.json",
]


def scrub_hits(paths):
    """[(file, the word MASKED, the line)] — whole word, case folded, accents
    folded. The word itself never leaves this function."""
    hits = []
    for path in paths:
        text = read(path)
        if text is None:
            continue
        text = fold(text)
        for word, pattern in PATTERNS:
            found = pattern.search(text)
            if found:
                hits.append((Path(path).name, masked(word),
                             text[:found.start()].count("\n") + 1))
    return hits


def case_scrub(keep):
    case("R9", "SCRUB: the private list finds nothing in anything that ships")
    if not SCRUB_WORDS.is_file() and FLEET_REGISTRY is None:
        skip("the private word list is the owner's own (release/SCRUB-WORDS.txt) and this "
             "machine has none, nor a registry naming an owner, so there is nothing to scrub for")
        return
    check(bool(WORDS), "the private list was read (%d words)" % len(WORDS))
    paths = [SHIP_ROOT / rel for rel in SHIPPED]
    absent = [Path(p).name for p in paths if not Path(p).is_file()]
    check(not absent, "every shipped file is here (%s)" % (", ".join(absent) or "all present"))
    hits = scrub_hits([p for p in paths if Path(p).is_file()])
    for name, word, line in hits[:12]:
        say("      %s:%d  %s" % (name, line, word))
    check(not hits, "0 hits across %d shipped files (%d found)"
          % (len(paths), len(hits)))
    # The fleet registry is the one file that carries them, on purpose.
    fleet_hits = scrub_hits([FLEET_REGISTRY]) if FLEET_REGISTRY is not None else []
    check(bool(fleet_hits),
          "the OWNER's registry carries them on purpose (%d distinct words)"
          % len({h[1] for h in fleet_hits}))
    owner_rel = (FLEET_REGISTRY.relative_to(SHIP_ROOT).as_posix()
                 if FLEET_REGISTRY is not None else "")
    check(FLEET_REGISTRY is not None and owner_rel not in SHIPPED,
          "\u2026and it is not in the shipped set")


# ---------------------------------------------------------------------------
# R10 — no new literals
# ---------------------------------------------------------------------------

# A real person's home folder. The placeholders an example is written with are
# not one: `/home/you/Projects/Some Project` is the documentation this build
# put there ON PURPOSE, and a rule that called it a leak would be measuring the
# wrong thing. The owner's own name is caught by the private-word check below.
PLACEHOLDERS = {"you", "user", "username", "someone", "me", "example"}
HOME_PATH = re.compile(r"(?:/Users/|/home/|C:\\\\Users\\\\|C:\\Users\\)([A-Za-z0-9_.-]+)")
LEGACY_DIR = "orchestrator-sync"


def real_home_paths(line):
    """The absolute home paths in a line that name a real person."""
    found = []
    for m in HOME_PATH.finditer(line):
        if m.group(1).lower() not in PLACEHOLDERS:
            found.append(m.group(0))
    if REAL_HOME and REAL_HOME in line:
        found.append("<the machine's own home>")
    return found


def added_lines(diff_text):
    return [l[1:] for l in (diff_text or "").splitlines()
            if l.startswith("+") and not l.startswith("+++")]


def case_no_new_literals(keep):
    case("R10", "NO NEW LITERALS: no home path, no legacy folder name, no private word")
    if BUILD is None:
        skip("the diffs a build cut sit beside the build; an installed hub has none to read")
        return
    diffs = sorted(BUILD.glob("*.diff"))
    check(bool(diffs), "there is a diff for every file that changed (%d)" % len(diffs))
    # collect-openers.py:57 is the resolver's `MACHINE_FILE` and is left alone,
    # so no ADDED line of its diff may carry the name either. The two gate
    # copies are not shipped (P7 owns the gates), and their own fixture names
    # stay as they are — their diffs are swept for added home paths and added
    # private words like every other, and for nothing else.
    allowed_legacy = {"collect-openers.py.diff"}
    not_shipped = {"gate-comms.py.diff", "gate-tree-answers.py.diff"}
    for d in diffs:
        text = read(d) or ""
        added = added_lines(text)
        homes = [l for l in added if real_home_paths(l)]
        check(not homes, "%s: no absolute home path added (%d)" % (d.name, len(homes)))
        legacy = [l for l in added if LEGACY_DIR in l]
        if d.name in allowed_legacy:
            check(not legacy, "%s: no legacy folder name ADDED (the one at :57 is not "
                              "an added line)" % d.name)
        else:
            check(not legacy, "%s: no legacy folder name added (%d)" % (d.name, len(legacy)))
        folded = fold("\n".join(added))
        words = [masked(w) for w, p in PATTERNS if p.search(folded)]
        if d.name in not_shipped:
            check(True, "%s: not a shipped file (P7 owns the gates); %d added "
                        "line%s carry a fixture name it keeps"
                  % (d.name, len(words), "" if len(words) == 1 else "s"))
        else:
            check(not words, "%s: no private word in an added line (%s)"
                  % (d.name, ", ".join(sorted(set(words))) or "none"))


# ---------------------------------------------------------------------------
# R11 — the registry crosses
# ---------------------------------------------------------------------------

def case_registry_crosses(keep):
    case("R11", "REGISTRY CROSSES: carried both ways, never on the never-sync list")
    w = world("r11")
    sync = SYNC_DIR / "sync.py"
    text = read(sync) or ""
    never = re.search(r"NEVER_SYNC\w*\s*=\s*\(([^)]*)\)", text)
    body = never.group(1) if never else ""
    check("registry.json" not in body,
          "registry.json is not on the executable never-sync list")
    check("registry.json" not in (read(SYNC_DIR / "manifest.base.json") or ""),
          "\u2026and the base manifest does not exclude it either")
    # The loader finds it beside the tools, with no resolver present — which is
    # how it arrives in a hub whose tools folder is <hub>/tools.
    hub = w / "hub"
    (hub / "tools").mkdir(parents=True)
    shutil.copy(str(P3_TOOLS / "exo_registry.py"), str(hub / "tools" / "exo_registry.py"))
    shutil.copy(str(fixture_file()), str(hub / "registry.json"))
    env = dict(BASE_ENV)
    env.pop("EXO_REGISTRY_JSON", None)
    code, out = run_child(hub / "tools" / "exo_registry.py", "--check", env=env)
    check(code == 0, "the loader finds <hub>/registry.json from beside the tools")
    check("(no file yet" not in out, "\u2026and reads it, rather than every default")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------
# R12 — the installer renders the owner
# ---------------------------------------------------------------------------

def install_world(w, registry):
    """A program tree the installer can run in: the sync package, the tools,
    the templates, and a home with nothing in it."""
    home = w / "home"
    hub = home / "Exocortex"
    (hub).mkdir(parents=True)
    (home / "Projects").mkdir(parents=True)
    shutil.copytree(str(SYNC_DIR), str(hub / "sync"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(str(P3_TOOLS), str(hub / "tools"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    # The path resolver: a program tree has one and the installer STOPs without it,
    # correctly (beside a build it is the build's; in an installed hub, the hub's own).
    resolver = RESOLVER
    if resolver.is_file():
        shutil.copy(str(resolver), str(hub / "tools" / "exo_paths.py"))
    shutil.copytree(str(TEMPLATES), str(hub / "templates"))
    shutil.copy(str(P3_ORCH), str(hub / "orchestrator.py"))
    if registry is not None:
        shutil.copy(str(registry), str(hub / "templates" / "registry.json"))
    return home, hub


def case_install(keep):
    case("R12", "INSTALL: the sheet names the owner, the seed walk lands the registry")
    w = world("r12")
    for label, registry, want_name in (("stranger", None, False),
                                       ("owner", fixture_file(), True)):
        sub = w / label
        sub.mkdir(parents=True)
        home, hub = install_world(sub, registry)
        env = env_for(home)
        env["EXO_INSTALL_NO_SCHEDULER"] = "1"
        code, out = run_child(hub / "sync" / "install.py", "--defaults", env=env, timeout=300)
        sheets = sorted((hub / "design").glob("INSTALL-WATCHERS-*.md"))
        if not sheets:
            check(False, "%s: the installer rendered a sheet (it said: %s)"
                  % (label, (out.splitlines() or [""])[-1][:90]))
            continue
        sheet = read(sheets[0]) or ""
        hits = scrub_hits([sheets[0]])
        if want_name:
            check(FIXTURE_OWNER in sheet, "%s: the owner's own name appears in the sheet"
                  % label)
        else:
            check(not hits and FIXTURE_OWNER not in sheet,
                  "%s: no private word anywhere in the sheet (%d)" % (label, len(hits)))
            check("the owner acts only at the PAUSEs" in sheet,
                  "stranger: `the owner` stands where a name would be")
        check("__OWNER__" not in sheet, "%s: every placeholder was rendered" % label)
        check(str(sheets[0]).startswith(str(hub / "design")),
              "%s: the sheet is brain-side, never in the program tree" % label)
        # the seed walk
        landed = hub / "registry.json"
        check(landed.is_file(), "%s: the seed walk landed registry.json at the hub root" % label)
        record = {}
        try:
            record = json.loads((hub / "installed.json").read_text(encoding="utf-8"))
        except Exception:
            record = {}
        seeded = record.get("seeded") or []
        check("registry.json" in seeded,
              "%s: and recorded it (%d seeded path%s)"
              % (label, len(seeded), "" if len(seeded) == 1 else "s"))
        check(any(s.startswith("routines/") for s in seeded)
              or not (hub / "templates" / "routines").is_dir(),
              "%s: the routine seeds still land by the same one rule" % label)
        check(not any(s.startswith("dot-") or s == "installed.json" for s in seeded),
              "%s: the dot-files and the record itself are not seeded" % label)

    # a pre-placed registry.json keeps its bytes
    sub = w / "preplaced"
    sub.mkdir(parents=True)
    home, hub = install_world(sub, fixture_file())
    mine = '{"version": 1, "owner": {"name": "Q"}}\n'
    write(hub / "registry.json", mine)
    env = env_for(home)
    env["EXO_INSTALL_NO_SCHEDULER"] = "1"
    run_child(hub / "sync" / "install.py", "--defaults", env=env, timeout=300)
    check(read(hub / "registry.json") == mine,
          "a registry.json already there keeps its bytes, exactly")
    no_strays()
    drop(w, keep)


# ---------------------------------------------------------------------------

CASES = [case_loader, case_fleet_equality, case_stranger, case_next_values,
         case_owner_address, case_asked, case_minds, case_lane_words,
         case_scrub, case_no_new_literals, case_registry_crosses, case_install,
         case_install_flags, case_logical_names]


def main(argv):
    if DEPTH > MAX_DEPTH:
        sys.stderr.write("gate-registry: depth %d is past the limit of %d — a gate has "
                         "started a gate\n" % (DEPTH, MAX_DEPTH))
        return 2
    keep = "--keep" in argv
    started = time.time()
    if LAYOUT == "installed" and not ((SYNC_DIR / "sync.py").is_file()
                                      and SEED_REGISTRY.is_file()):
        # An installed hub that is not a program tree (the older layout keeps
        # the sync package in the brain clone and ships no templates/) holds
        # neither the sync package nor the seed this gate proves.
        # The one line a runner reads as "cannot run on this layout": nothing
        # else is printed, and no check is counted.
        sys.stdout.write("gate-registry.py: skipped here \u2014 this hub is not a program tree: "
                         "no sync/sync.py and no templates/registry.json beside its tools, "
                         "and a program tree is what this gate proves\n")
        return 0
    if RG is None:
        check(False, "the loader this gate proves is installed beside it (%s)"
              % shown(P3_TOOLS / "exo_registry.py"))
        say("1 checks \u00b7 0 passed \u00b7 1 failed")
        return 1
    say("gate-registry \u2014 BQ-045 P3, the owner's names left the code")
    say("layout     %s \u2014 %s" % (LAYOUT, shown(HERE)))
    say("owner      %s" % ("the owner's own registry is here" if FLEET_REGISTRY is not None
                           else "no registry here names an owner"))
    say("worlds     the system temp folder, deleted at the end of every case")
    say("started    %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    for run_case in CASES:
        try:
            run_case(keep)
        except Exception as exc:
            import traceback
            check(False, "%s raised: %s" % (run_case.__name__, exc))
            say(shown(traceback.format_exc())[:2000])
    say("")
    if not keep and ROOT is not None:
        shutil.rmtree(str(ROOT), ignore_errors=True)
    left = [w for w in WORLDS if Path(w).exists()]
    check(keep or not left, "every fixture world is gone (%d left)" % len(left))
    strays = sorted(Path(tempfile.gettempdir()).glob("exo-gate-p3-*"))
    check(keep or not strays,
          "no folder of this gate's own making is left in the temp folder (%d)"
          % len(strays))
    check(keep or ROOT is None or not Path(ROOT).exists(),
          "and the world root itself is gone")
    no_strays()
    say("")
    say("children started: %d" % CHILDREN)
    say("elapsed: %.1f s" % (time.time() - started))
    for line in fails:
        say("FAILED  %s" % line)
    for line in SKIPS:
        say("SKIPPED %s" % line)
    say("%d checks \u00b7 %d passed \u00b7 %d failed%s"
        % (len(checks), sum(1 for c in checks if c), len(fails),
           (" \u00b7 %d skipped" % len(SKIPS)) if SKIPS else ""))
    return 0 if not fails else 1


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    if ROOT is not None:
        shutil.rmtree(str(ROOT), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
