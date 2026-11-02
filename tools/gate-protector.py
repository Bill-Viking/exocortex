#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-protector.py — the inference protector's gate.

    python3 tools/gate-protector.py            G0–G8, hermetic; G9 skipped with its reason
    python3 tools/gate-protector.py --live     also G9: the fixture question on real sonnet
    python3 tools/gate-protector.py --keep     leave the temp worlds for inspection

HERMETIC, every case: a world of its own under the system temp folder
(tempfile.mkdtemp(prefix="exo-prove-protector-")) — a scratch HOME, a machine
record naming NORTH, a fixture registry, copies of protector.py and the hub
tools it reads (exo_common, exo_registry, exo_paths; usage.py for its price
table, read as text), and a stub mail.py that records the ceiling's letter in
the world instead of touching an INBOX. Every model is the stub runner
(fixtures/protector/stub-runner.py), which prints `claude -p`'s own JSON, so the
ledger path is the real one. No live call without --live.

  G0 usage and the dry run · G1 bare vs harnessed · G2 a planted failure that
  stays climbs · G3 a pass stays quiet · G4 the ceiling · G5 judgment's ladder ·
  G6 the vote · G7 the ledger, to the cent · G8 not in shape, and the STOPs ·
  G9 live (--live only)

The gate finds protector.py and the fixtures BESIDE ITSELF, and the hub tools
beside itself or in the nearest tools/ folder above — so it runs unchanged from
a build folder and from the hub's tools/. Run it from any folder.
Prints N/N and exits 0, else the first failing case and exits 1.
Stdlib only, Python 3.9, macOS and Windows.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

try:
    if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
PROTECTOR = HERE / "protector.py"
FIX = HERE / "fixtures" / "protector"
STUB = FIX / "stub-runner.py"
SOURCE = FIX / "sources-rates.md"
PY = sys.executable or "python3"

# The hub tools protector.py reads, copied into every world.
COPIED = ("exo_common.py", "exo_registry.py", "exo_paths.py", "usage.py")

# Invented names only, beside the minds' product words; the codex mind's alias is
# the one the tool's own words use (ASTRA). G5 proves the name comes from here.
FIXTURE_REGISTRY = {
    "version": 1,
    "note": "gate-protector's fixture registry: the owner is invented.",
    "owner": {"name": "Wren", "short": "wren", "aliases": []},
    "minds": [
        {"name": "FABLE", "vendor": "Anthropic", "kind": "claude", "cli": "fable",
         "app_id": "claude-fable-5-1", "tier": "flagship"},
        {"name": "OPUS", "vendor": "Anthropic", "kind": "claude", "cli": "opus",
         "app_id": "claude-opus-5-5"},
        {"name": "SONNET", "vendor": "Anthropic", "kind": "claude", "cli": "sonnet",
         "app_id": "claude-sonnet-5-5"},
        {"name": "ASTRA", "vendor": "OpenAI", "kind": "codex"},
    ],
    "mind_aliases": {"CODEX": "ASTRA", "GPT": "ASTRA"},
}

EXPECTED_SAVING = "1.61"
PLANTED = "1.71"
STUB_CLI_COST = 0.0421
CENT = 0.005

RESULTS = []          # (case id, ok, first failure)
CASE = {"id": "", "fails": []}
WORLDS = []
KEEP = "--keep" in sys.argv


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------

def source_tool(name):
    """A hub tool beside this gate (installed), else in the nearest tools/ above it
    (a build folder inside the hub), else in the hub the machine record names."""
    for folder in [HERE] + [p / "tools" for p in HERE.parents]:
        if (folder / name).is_file():
            return folder / name
    try:
        with io.open(str(Path.home() / "orchestrator-sync" / "machine.json"), encoding="utf-8") as fh:
            root = (json.load(fh).get("roots") or {}).get("orchestrator")
        if root and (Path(root) / "tools" / name).is_file():
            return Path(root) / "tools" / name
    except Exception:
        pass
    return None


def start(case_id, title):
    CASE["id"], CASE["fails"] = case_id, []
    print("\n======== %s — %s ========" % (case_id, title))


def check(cond, msg):
    if cond:
        print("  [PASS] %s" % msg)
    else:
        print("  [FAIL] %s" % msg)
        CASE["fails"].append(msg)
    return bool(cond)


def finish():
    ok = not CASE["fails"]
    RESULTS.append((CASE["id"], ok, CASE["fails"][0] if CASE["fails"] else ""))


def one_stop_line(out):
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    return len(lines) == 1 and lines[0].startswith("STOP:")


def read_prices():
    """usage.py's prices table, read here on the gate's own road (not protector's)."""
    import ast
    text = source_tool("usage.py").read_text(encoding="utf-8")
    m = re.search(r'"prices":\s*(\{.*?\n\s*\})', text, re.S)
    table = ast.literal_eval(re.sub(r"#[^\n]*", "", m.group(1)))
    return dict((k, dict((f, float(v)) for f, v in rate.items())) for k, rate in table.items())


def rate_for(prices, model_id):
    best = None
    for prefix, rate in prices.items():
        if model_id.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, rate)
    return best[1] if best else None


def priced(row, rate):
    return (row["input"] * rate["input"] + row["cache_write"] * rate["cache_write"]
            + row["cache_read"] * rate["cache_read"] + row["output"] * rate["output"]) / 1e6


def ledger_figures(out):
    """(total, at Fable's rate, saved) from the LEDGER line, or None."""
    m = re.search(r"LEDGER: (.*?) · the same tokens at \w+'s rate \$([0-9.]+) · saved \$([0-9.]+)", out)
    if not m:
        return None
    money = re.findall(r"\$([0-9.]+)", m.group(1))
    return (float(money[-1]) if money else None, float(m.group(2)), float(m.group(3)))


def alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True, text=True)
        return str(pid) in (r.stdout or "")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                       # a zombie is dead for this purpose
        r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
        return bool(r.stdout.strip()) and not r.stdout.strip().startswith("Z")
    except Exception:
        return True


QUESTION = (FIX / "question.md").read_text(encoding="utf-8").strip() if (FIX / "question.md").is_file() else ""


class World(object):
    """One case's world: hub/tools with copies, a stub mail.py, a registry, a HOME."""

    def __init__(self, registry=None):
        self.root = Path(tempfile.mkdtemp(prefix="exo-prove-protector-"))
        WORLDS.append(self.root)
        self.hub = self.root / "hub"
        self.tools = self.hub / "tools"
        self.tools.mkdir(parents=True)
        shutil.copy2(str(PROTECTOR), str(self.tools / "protector.py"))
        for name in COPIED:
            shutil.copy2(str(source_tool(name)), str(self.tools / name))
        shutil.copy2(str(FIX / "stub-mail.py"), str(self.tools / "mail.py"))
        self.registry = self.hub / "registry.json"
        self.registry.write_text(json.dumps(registry or FIXTURE_REGISTRY, indent=1), encoding="utf-8")
        self.home = self.root / "home"
        (self.home / "orchestrator-sync").mkdir(parents=True)
        self.machine = self.home / "orchestrator-sync" / "machine.json"
        self.machine.write_text(json.dumps({
            "name": "north", "os": "macos" if sys.platform == "darwin" else sys.platform,
            "roots": {"orchestrator": str(self.hub), "home": str(self.home)}}), encoding="utf-8")
        self.state = self.root / "state"
        self.stub = self.root / "stub"

    def env(self, scenario="pass", live=False, **extra):
        env = dict(os.environ)
        drop = ("EXO_MACHINE_JSON", "EXO_REGISTRY_JSON", "PROTECTOR_STUB", "PROTECTOR_STUB_STATE",
                "PROTECTOR_MODEL", "PROTECTOR_ROLE") + (() if live else ("ANTHROPIC_API_KEY",))
        for key in drop:                    # a live run keeps the person's own key, if they use one
            env.pop(key, None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["EXO_MACHINE_JSON"] = str(self.machine)
        if not live:                        # a live call needs the person's own HOME (its sign-in)
            env.update({"HOME": str(self.home), "USERPROFILE": str(self.home),
                        "EXO_REGISTRY_JSON": str(self.registry),
                        "PROTECTOR_STUB": scenario, "PROTECTOR_STUB_STATE": str(self.stub)})
        env.update(extra)
        return env

    def run(self, args, scenario="pass", env_extra=None, timeout=90, live=False):
        argv = [PY, str(self.tools / "protector.py")] + list(args)
        started = time.time()
        try:
            r = subprocess.run(argv, cwd=str(self.root), env=self.env(scenario, live, **(env_extra or {})),
                               capture_output=True, timeout=timeout)
            out = r.stdout.decode("utf-8", "replace")
            err = r.stderr.decode("utf-8", "replace")
            code = r.returncode
        except subprocess.TimeoutExpired:
            code, out, err = 99, "", "the gate's own timeout (%d s) fired" % timeout
        return code, out, err, time.time() - started

    def ask(self, *flags, **kw):
        runner = kw.pop("runner", str(STUB))
        args = ["ask", QUESTION, "--sources", str(SOURCE)]
        args += (["--runner", runner] if runner else []) + ["--state-dir", str(self.state)]
        return self.run(args + list(flags), **kw)

    def stub_calls(self):
        path = self.stub / "calls.jsonl"
        if not path.is_file():
            return []
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def letters(self):
        path = self.root / "mail-sent.jsonl"
        if not path.is_file():
            return []
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def ledger_rows(self):
        path = self.state / "protector-ledger.jsonl"
        if not path.is_file():
            return []
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def load_protector(self):
        """The world's copy of protector.py, imported in this process (bare + grade)."""
        os.environ["EXO_REGISTRY_JSON"] = str(self.registry)
        spec = importlib.util.spec_from_file_location("protector_world", str(self.tools / "protector.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def models_called(world, role=None):
    return [c["model"] for c in world.stub_calls() if role is None or c["role"] == role]


# --------------------------------------------------------------------------
# the cases
# --------------------------------------------------------------------------

def g0():
    start("G0", "usage, refusal of no args, and the dry run that calls nothing")
    w = World()
    code, out, _err, _s = w.run([])
    check(code == 2 and "protector.py ask" in out, "no args → the usage, exit 2 (got %d)" % code)
    code, out, _err, _s = w.run(["--help"])
    check(code == 2 and "protector.py ask" in out, "--help → the usage, exit 2 (got %d)" % code)
    code, out, _err, _s = w.ask("--dry-run")
    check(code == 0, "--dry-run exits 0 (got %d)" % code)
    check("--- prompt 1 of 2 · [PROTECTOR:draft] ---" in out and "\n[PROTECTOR:draft]\n" in out,
          "--dry-run prints the draft prompt with its role marker")
    check("--- prompt 2 of 2 · [PROTECTOR:check] ---" in out and "\n[PROTECTOR:check]\n" in out,
          "--dry-run prints the check prompt with its role marker")
    check("runner (sonnet):" in out and "stub-runner.py" in out, "--dry-run prints the runner line")
    check(not w.stub_calls(), "--dry-run made no call (the stub saw nothing)")
    check(not (w.state / "protector-ledger.jsonl").exists(), "--dry-run wrote no ledger line")
    want = ("claude -p --model sonnet --effort high --output-format json --safe-mode "
            "--no-session-persistence --max-budget-usd 2.00")
    code, out, _err, _s = w.ask("--dry-run", runner="claude")
    check(code == 0 and want in out,
          "the claude runner's line, no API key: `%s` (the CLI's own sign-in road)" % want)
    code, out, _err, _s = w.ask("--dry-run", runner="claude",
                                env_extra={"ANTHROPIC_API_KEY": "gate-dummy-never-called"})
    check(code == 0 and "--output-format json --bare --no-session-persistence" in out
          and "--safe-mode" not in out,
          "with ANTHROPIC_API_KEY set the line carries --bare, the brief's exact command")
    finish()


def g1():
    start("G1", "BARE vs HARNESSED (stub fail-once): the harness catches the planted miss")
    w = World()
    mod = w.load_protector()
    opts = mod.Opts(runner=str(STUB), state_dir=str(w.state), env=w.env("fail-once"), quiet=True)
    sources = mod.read_sources([str(SOURCE)])
    bare = mod.bare_answer(QUESTION, sources, "sonnet", opts)
    bare_grade = mod.grade_text(QUESTION, sources, bare, "sonnet", opts)
    check(PLANTED in bare, "the bare answer carries the planted miss (%s a run)" % PLANTED)
    miss = [f for f in bare_grade.get("failed") or [] if f["key"] == "rederived"]
    check(bare_grade.get("in_shape") and miss and miss[0]["draft"] == PLANTED
          and miss[0]["got"] == EXPECTED_SAVING,
          "the same checker grades the bare answer: re-derived fails, %s vs %s" % (PLANTED, EXPECTED_SAVING))
    before = len(w.stub_calls())
    code, out, err, _s = w.ask(scenario="fail-once")
    harness = w.stub_calls()[before:]
    check(code == 0, "the harnessed run exits 0 (got %d)" % code)
    check("CHECK: signed 6/6 · sonnet · 4 calls" in out, "harnessed → signed 6/6 · sonnet · 4 calls")
    check([c["role"] for c in harness] == ["draft", "check", "revise", "check"],
          "the calls: draft, check, revise, check (got %s)" % [c["role"] for c in harness])
    answer = next((ln for ln in out.splitlines() if ln.startswith("ANSWER:")), "")
    check(EXPECTED_SAVING in answer and PLANTED not in answer,
          "the signed ANSWER carries %s a run, not %s" % (EXPECTED_SAVING, PLANTED))
    check("escalate" not in out + err, "no escalation (the revise fixed it)")
    check(re.search(r"LEDGER: sonnet \$[0-9.]+ · the same tokens at Fable's rate \$[0-9.]+ · saved \$",
                    out) is not None, "the ledger prints with the Fable-rate line")
    grade_line = next((ln for ln in out.splitlines() if ln.startswith("CHECK:")), "")
    print("    side by side, the same six lines:")
    print("      BARE       %s" % mod.grade_summary(bare_grade))
    print("      HARNESSED  %s" % grade_line[len("CHECK: "):])
    finish()


def g2():
    start("G2", "A PLANTED FAILURE THAT STAYS (stub fail-twice): escalate, one mind up")
    w = World()
    code, out, _err, _s = w.ask(scenario="fail-twice")
    check(code == 0, "exit 0, signed by the next mind (got %d)" % code)
    check("CHECK: escalate — re-derived failed (per-run saving: 1.71 vs 1.61) · sonnet → opus" in out,
          "the escalate line names line 4 with both values, sonnet → opus")
    check("CHECK: signed 6/6 · opus (escalated from sonnet) · 6 calls" in out,
          "signed 6/6 · opus (escalated from sonnet) · 6 calls")
    called = models_called(w)
    check(called.count("sonnet") == 4 and called.count("opus") == 2 and "fable" not in called,
          "sonnet 4 calls (draft, check, revise, check), opus 2, fable none (got %s)" % called)
    finish()


def g3():
    start("G3", "A PASS stays quiet (stub pass)")
    w = World()
    code, out, err, _s = w.ask(scenario="pass")
    check(code == 0, "exit 0 (got %d)" % code)
    check("CHECK: signed 6/6 · sonnet · 2 calls" in out, "signed 6/6 · sonnet · 2 calls")
    check("escalate" not in out + err, "no escalation line, on either stream")
    check(len(w.stub_calls()) == 2, "two calls (got %d)" % len(w.stub_calls()))
    code, out, err, _s = w.ask("--json", scenario="pass")
    try:
        obj = json.loads(out)
    except ValueError:
        obj = {}
    g = obj.get("grade") or {}
    check(code == 0 and obj.get("exit") == 0 and g.get("signed") is True and g.get("mind") == "sonnet"
          and g.get("calls") == 2 and EXPECTED_SAVING in str(obj.get("answer"))
          and [c.get("role") for c in obj.get("calls") or []] == ["draft", "check"]
          and "LEDGER:" in str((obj.get("ledger") or {}).get("line")),
          "--json prints ONE object: answer, grade (signed, mind, calls), ledger, calls[]")
    check(not err.strip(), "--json is quiet on stderr (no progress lines)")
    finish()


def g4():
    start("G4", "THE CEILING (--ceiling sonnet, stub fail-twice): unsigned, exit 4, one letter")
    w = World()
    code, out, _err, _s = w.ask("--ceiling", "sonnet", scenario="fail-twice")
    check(code == 4, "exit 4 (got %d)" % code)
    check("CHECK: UNSIGNED — re-derived (1.71 vs 1.61)" in out, "UNSIGNED — re-derived (1.71 vs 1.61)")
    answer = next((ln for ln in out.splitlines() if ln.startswith("ANSWER:")), "")
    check(PLANTED in answer, "the best answer it has is printed, marked unsigned")
    check("opus" not in models_called(w), "never past the ceiling: no opus call")
    letters = w.letters()
    check(len(letters) == 1 and letters[0][:2] == ["--send", "NORTH/hub"],
          "ONE letter, to NORTH/hub, through the world's stub mail.py (got %s)"
          % [ln[:2] for ln in letters])
    check(letters and "re-derived (1.71 vs 1.61)" in letters[0][3] and "\n" not in letters[0][3],
          "the letter says why, in one line")
    check("LETTER: letter sent to NORTH/hub" in out, "the run says the letter went")
    finish()


def g5():
    start("G5", "JUDGMENT: the codex mind → fable, never opus or sonnet")
    w = World()
    code, out, _err, _s = w.ask("--kind", "judgment", scenario="fail-twice")
    check(code == 0, "exit 0 (got %d)" % code)
    check("CHECK: escalate — re-derived failed (per-run saving: 1.71 vs 1.61) · astra → fable" in out,
          "starts on astra (the registry's name for the codex mind), climbs to fable")
    check("CHECK: signed 6/6 · fable (escalated from astra)" in out, "signed by fable, escalated from astra")
    called = set(models_called(w))
    check(called == {"codex", "fable"}, "only the codex mind and fable were asked (got %s)" % sorted(called))
    for flags, what in ((["--model", "sonnet"], "--model sonnet"), (["--model", "opus"], "--model opus"),
                        (["--ceiling", "opus"], "--ceiling opus")):
        code, out, _err, _s = w.ask("--kind", "judgment", *flags)
        check(code == 2 and one_stop_line(out) and "astra → fable" in out,
              "--kind judgment %s → refused in one line, exit 2 (%s)" % (what, out.strip()[:90]))
    code, out, _err, _s = w.ask("--kind", "judgment", "--model", "astra", "--dry-run")
    check(code == 0 and "starts on astra" in out, "--model astra (the registry's word) is accepted")
    other = dict(FIXTURE_REGISTRY)
    other["minds"] = [m if m["name"] != "ASTRA" else dict(m, name="NOBODY") for m in FIXTURE_REGISTRY["minds"]]
    other["mind_aliases"] = {"CODEX": "NOBODY"}
    w2 = World(registry=other)
    code, out, _err, _s = w2.ask("--kind", "judgment", "--dry-run")
    check(code == 0 and "ladder: nobody → fable" in out,
          "a registry that names the codex mind NOBODY reads nobody → fable (no name in the tool)")
    finish()


def g6():
    start("G6", "THE VOTE: two thirds sign, a split climbs, no vote without --checkable")
    w = World()
    code, out, _err, _s = w.ask("--vote", "5", "--checkable", scenario="vote-4of5")
    check(code == 0 and "CHECK: signed 6/6 · sonnet · vote 4/5 · 6 calls" in out,
          "vote-4of5 → signed 6/6 · sonnet · vote 4/5 · 6 calls (exit %d)" % code)
    check(models_called(w, "draft").count("sonnet") == 5 and models_called(w, "check") == ["sonnet"],
          "five drafts, then the majority's draft checked once")
    w = World()
    code, out, _err, _s = w.ask("--vote", "5", "--checkable", scenario="vote-3of5")
    check("CHECK: escalate — vote split 3/5 · sonnet → opus" in out, "vote-3of5 → «vote split 3/5», escalate")
    check(code == 0 and "CHECK: signed 6/6 · opus (escalated from sonnet) · vote 5/5" in out,
          "opus votes 5/5 and signs (exit %d)" % code)
    check("sonnet" not in models_called(w, "check"), "a split vote is never checked: no sonnet check call")
    code, out, _err, _s = w.ask("--vote", "3")
    check(code == 2 and one_stop_line(out) and "--checkable" in out,
          "--vote 3 without --checkable → refused in one line, exit 2")
    finish()


def g7():
    start("G7", "THE LEDGER: tokens × usage.py's rows = the dollars, to the cent")
    prices = read_prices()
    fable = next(rate for prefix, rate in sorted(prices.items()) if prefix.startswith("claude-fable"))
    w = World()
    code, out, _err, _s = w.ask(scenario="fail-once")
    rows = w.ledger_rows()
    check(code == 0 and len(rows) == 4, "one ledger line per call (4; got %d)" % len(rows))
    exact = all(abs(r["usd"] - priced(r, rate_for(prices, r["model"]))) < 1e-9 for r in rows)
    check(exact, "each line's dollars = its tokens × the %s row" % (rows[0]["model"] if rows else "?"))
    check(all(r["cli_cost_usd"] == STUB_CLI_COST for r in rows), "the CLI's own total_cost_usd is kept as given")
    check(all(r["model"] == "claude-sonnet-5-5" and r["mind"] == "sonnet" for r in rows),
          "the model id comes from the CLI's modelUsage")
    figures = ledger_figures(out)
    total = sum(priced(r, rate_for(prices, r["model"])) for r in rows)
    at_fable = sum(priced(r, fable) for r in rows)
    check(figures and abs(figures[0] - total) < CENT, "the LEDGER line's $%s = %.4f, to the cent"
          % (figures[0] if figures else "?", total))
    check(figures and abs(figures[1] - at_fable) < CENT, "the Fable-rate line $%s = %.4f, to the cent"
          % (figures[1] if figures else "?", at_fable))
    check(figures and abs(figures[2] - (at_fable - total)) < CENT, "saved $%s = %.4f, to the cent"
          % (figures[2] if figures else "?", at_fable - total))
    w3 = World()
    code, out, err, _s = w3.ask("--against-fable", scenario="pass")
    bare = [c for c in w3.stub_calls() if c["role"] == "bare"]
    m = re.search(r"LEDGER \(measured\): harness \$([0-9.]+) · bare fable \$([0-9.]+) · saved \$(-?[0-9.]+)", out)
    check(code == 0 and len(bare) == 1 and bare[0]["model"] == "fable" and m
          and abs(float(m.group(3)) - (float(m.group(2)) - float(m.group(1)))) < CENT,
          "--against-fable: ONE bare call on fable, both ledgers on one measured line")
    check("flagship quota" in err, "--against-fable says it spends flagship quota before the call")
    w2 = World()
    code, out, _err, _s = w2.ask("--kind", "judgment", scenario="pass")
    check(code == 0 and "LEDGER: astra no rate" in out and "saved: not computed" in out,
          "a model id with no row (gpt-6-astra) prints `no rate`, never a dollar")
    old = {"time": (datetime.now().astimezone() - timedelta(days=10)).replace(microsecond=0).isoformat(),
           "run": "planted-old", "mind": "sonnet", "model": "claude-sonnet-5-5", "role": "draft",
           "runner": "cmd", "cli_cost_usd": None, "usd": 10.0, "fable_usd": 50.0, "seconds": 1,
           "input": 0, "cache_write": 0, "cache_read": 0, "output": 1000000, "tokens_known": True}
    with io.open(str(w.state / "protector-ledger.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(old) + "\n")
    code, out, _err, _s = w.run(["ledger", "--week", "--state-dir", str(w.state)])
    m = re.search(r"total \$([0-9.]+) · the same tokens at Fable's rate \$([0-9.]+)", out)
    check(code == 0 and m and abs(float(m.group(1)) - total) < CENT
          and abs(float(m.group(2)) - at_fable) < CENT,
          "ledger --week sums the world's jsonl ($%s) and leaves the 10-day-old line out"
          % (m.group(1) if m else "?"))
    code, out, _err, _s = w.run(["ledger", "--state-dir", str(w.state)])
    m = re.search(r"total \$([0-9.]+)", out)
    check(code == 0 and m and abs(float(m.group(1)) - (total + 10.0)) < CENT,
          "ledger with no --week takes every line ($%s)" % (m.group(1) if m else "?"))
    finish()


def g8():
    start("G8", "NOT IN SHAPE escalates, never a traceback; a tool failure is one STOP line")
    w = World()
    code, out, err, _s = w.ask(scenario="malformed")
    check("CHECK: escalate — did not answer in shape (the draft has no ANSWER line) · sonnet → opus" in out,
          "a draft with no ANSWER line → escalate «did not answer in shape»")
    check("CHECK: escalate — did not answer in shape (the checker did not answer with its JSON object)"
          " · opus → fable" in out, "a checker that answers in prose → escalate «did not answer in shape»")
    check(code == 0 and "CHECK: signed 6/6 · fable (escalated from sonnet → opus)" in out,
          "fable signs at the top (exit %d)" % code)
    check("Traceback" not in out + err, "no traceback anywhere")
    mod = w.load_protector()
    lines = dict((k, "pass") for k in ("read", "asked", "shown", "rederived", "gaps", "one"))
    said_pass = json.dumps({"lines": lines, "rederived": [
        {"claim": "per-run saving", "draft": "1.71", "got": "1.61", "match": True}]})
    graded = mod.judge(said_pass)
    check(graded.get("in_shape") and [f["key"] for f in graded["failed"]] == ["rederived"],
          "a checker that says pass while its own values differ (1.71 vs 1.61) is graded a fail")
    odd = dict(lines, one="maybe")
    check(mod.judge(json.dumps({"lines": odd})).get("in_shape") is False,
          "a line marked anything but pass, fail or n/a is not in shape")
    w = World()
    code, out, _err, _s = w.ask("--ceiling", "opus", scenario="malformed")
    check(code == 4 and "CHECK: UNSIGNED — did not answer in shape" in out,
          "at the ceiling: UNSIGNED — did not answer in shape, exit 4 (got %d)" % code)
    code, out, _err, _s = w.ask(runner="no-such-runner-bq351")
    check(code == 2 and one_stop_line(out) and "not on PATH" in out,
          "a runner that is not on PATH → one STOP line, exit 2 (%s)" % out.strip()[:80])
    bare_path = os.path.dirname(PY)
    if shutil.which("claude", path=bare_path) is None:
        hidden = json.loads(w.registry.read_text(encoding='utf-8'))
        for row in hidden['minds']:
            if row.get('kind') == 'claude':
                row['headless'] = {'exe': 'claude', 'candidates': {'macos': [], 'windows': []}}
        hidden_registry = w.hub / 'no-claude-candidates.json'
        hidden_registry.write_text(json.dumps(hidden), encoding='utf-8')
        code, out, _err, _s = w.ask(runner="claude", env_extra={"PATH": bare_path,
                                  "EXO_REGISTRY_JSON": str(hidden_registry)})
        expected = "the runner «claude» is not on PATH and no candidate is registered"
        check(code == 2 and one_stop_line(out) and expected in out,
              "the claude CLI not on PATH → STOP: " + expected)
    else:
        print("  [SKIP] the claude-not-on-PATH check: claude sits beside python here")
    code, out, _err, _s = w.ask(scenario="not-logged-in")
    check(code == 2 and one_stop_line(out) and "Not logged in" in out,
          "the CLI's «Not logged in» answer → one STOP line, exit 2, never an escalation")
    w = World()
    code, out, _err, secs = w.ask("--timeout", "2", scenario="sleep", timeout=60)
    check(code == 2 and one_stop_line(out) and "STOP: the model did not answer in 2 s" in out,
          "a runner past --timeout 2 → STOP: the model did not answer in 2 s, exit 2")
    check(secs < 15, "it stopped in %.1f s, not the stub's 60" % secs)
    pids = {}
    try:
        pids = json.loads((w.stub / "sleep-pids.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    for _ in range(30):
        if not any(alive(pids.get(k)) for k in ("stub", "grandchild")):
            break
        time.sleep(0.1)
    check(pids and not alive(pids.get("stub")) and not alive(pids.get("grandchild")),
          "no child left: the stub (%s) and its grandchild (%s) are gone"
          % (pids.get("stub"), pids.get("grandchild")))
    # a live miss: a real model wrote its working into «got», and a
    # true match (95 vs 94.91) read as a miss — the comparison reads the result at the end
    # of such a line, or the value at its start, and a claimed pass over differing values
    # is still a mismatch
    mod = w.load_protector()
    check(not mod.mismatch({"draft": "95", "match": True,
                            "got": "Sonnet 0.0033 + 23.52 + 16.175 + 6.08 = 45.78. Fable 0.0165 + "
                                   "29.4 + 80.875 + 30.4 = 140.69. Difference 94.91."}),
          "a got value that carries its working and ends in the result (94.91) matches the draft's 95")
    check(not mod.mismatch({"draft": "1.61 per run", "got": "1.61 (2.39 - 0.78)", "match": True}),
          "a bare value followed by its working matches")
    check(mod.mismatch({"draft": "1.61", "got": "the per-run saving is 1.71", "match": True}),
          "a pass claimed over 1.71 vs 1.61 is still a mismatch")
    check(mod.mismatch({"draft": "95", "got": "95", "match": False}),
          "the checker's own «match: false» stands even when the numbers agree")
    finish()


def g9():
    start("G9", "LIVE: the fixture question on real sonnet, bare and harnessed")
    print("  before the call: up to 6 calls on SONNET through the claude CLI — 1 bare, 1 check of")
    print("  it, 2 to 4 harnessed (--ceiling sonnet: it never climbs to a dearer mind), each capped")
    print("  at $2.00 by --max-budget-usd; they count against the plan's Sonnet window.")
    w = World()
    mod = w.load_protector()
    opts = mod.Opts(runner=None, state_dir=str(w.state), env=w.env(live=True), quiet=True,
                    timeout=600)
    sources = mod.read_sources([str(SOURCE)])
    try:
        bare = mod.bare_answer(QUESTION, sources, "sonnet", opts)
    except mod.Stop as stop:
        if "not logged in" in str(stop).lower():
            print("  G9 waits on the login: %s" % stop)
            RESULTS.append(("G9", None, "login"))
            return
        check(False, "the bare call: STOP: %s" % stop)
        finish()
        return
    bare_grade = mod.grade_text(QUESTION, sources, bare, "sonnet", opts)
    check(bare_grade.get("in_shape"), "the bare answer was graded by the six lines")
    code, out, err, _s = w.ask("--model", "sonnet", "--ceiling", "sonnet", runner=None, live=True,
                               timeout=2400)
    check(code in (0, 4), "the harnessed run ended signed or unsigned, never a STOP (exit %d%s)"
          % (code, (": " + out.strip()[:120]) if code == 2 else ""))
    grade_line = next((ln for ln in out.splitlines() if ln.startswith("CHECK: s")
                       or ln.startswith("CHECK: U")), "")
    check(bool(grade_line), "the harness printed its grade line")
    check(re.search(r"LEDGER: sonnet \$[0-9.]+", out) is not None, "the real ledger priced sonnet's tokens")
    print("    BARE       %s" % mod.grade_summary(bare_grade))
    print("    HARNESSED  %s" % grade_line[len("CHECK: "):])
    for line in out.splitlines():
        if line.startswith("LEDGER:"):
            print("    %s" % line)
    finish()


# --------------------------------------------------------------------------

def main():
    live = "--live" in sys.argv
    missing = [p for p in (PROTECTOR, STUB, SOURCE, FIX / "question.md", FIX / "stub-mail.py")
               if not p.is_file()] + [n for n in COPIED if source_tool(n) is None]
    if missing:
        print("gate-protector: STOP: not found beside the gate: %s" % ", ".join(str(m) for m in missing))
        return 1
    cases = [g0, g1, g2, g3, g4, g5, g6, g7, g8] + ([g9] if live else [])
    for case in cases:
        try:
            case()
        except Exception as exc:                       # a broken case is a failure, said plainly
            check(False, "the case itself broke: %r" % (exc,))
            finish()
    if not KEEP:
        for root in WORLDS:
            shutil.rmtree(str(root), ignore_errors=True)
    else:
        print("\nworlds kept: %s" % ", ".join(str(r) for r in WORLDS))
    hermetic = [r for r in RESULTS if r[0] != "G9"]
    passed = len([r for r in RESULTS if r[1]])
    total = len(RESULTS)
    first = next((r for r in RESULTS if r[1] is False), None)
    login = any(r[0] == "G9" and r[1] is None for r in RESULTS)
    print("")
    if first:
        print("gate-protector: %d/%d · first failure: %s — %s" % (passed, total, first[0], first[2]))
        return 1
    if login:
        print("gate-protector: %d/%d · G9 waits on the login" % (passed, total))
        return 1
    if not live:
        print("gate-protector: %d/%d · G9 skipped — it calls real sonnet; run with --live"
              % (passed, len(hermetic)))
    else:
        print("gate-protector: %d/%d" % (passed, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
