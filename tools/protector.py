#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""protector.py — the inference protector: a cheap mind reasons before it answers.

In plain words. A question goes to a cheap model with an order of work: PLAN
what is asked and which source decides each part, READ those sources before
any claim, DRAFT the answer with every number traced. Then a SEPARATE checker
call, in a fresh context that never sees the draft's reasoning, grades the
draft on six fixed lines and works every number out again. One revise is
allowed, and the checker runs again. The GRADE decides — never the model's
own confidence: SIGNED, or the question climbs one mind up the ladder and the
whole shape runs again there. At the ceiling with no signed answer, the best
answer goes out marked UNSIGNED, exit 4, and the hub gets one letter. Every
call is a line on the token ledger, so the saving is measured, never assumed.

    python3 tools/protector.py ask "<question>" [--sources f1 f2 ...] [--model sonnet]
        [--kind mechanical|judgment] [--ceiling opus] [--vote N --checkable]
        [--effort high] [--runner claude|codex|<cmd>] [--timeout 300]
        [--json] [--dry-run] [--against-fable] [--state-dir DIR]
    python3 tools/protector.py ledger [--week] [--state-dir DIR]
    python3 tools/protector.py --help

EXIT 0 signed (by any mind; the grade line names which) · 4 unsigned at the
ceiling · 2 STOP: a tool failure or a refusal, in one plain line.

WHERE IT CAN SIT: around a headless call (the claude CLI, the codex CLI, or any
command that reads a prompt on stdin and prints the answer). A session that IS
the model has no outside to wrap from; there the same shape rides as text.

THE GATE: tools/gate-protector.py (hermetic; --live calls real sonnet).
The ladders, the rubric and the grade's rules are the named constants below.
Stdlib only, Python 3.9, macOS and Windows.

IN-PROCESS USE (the gate's): bare_answer() and grade_text() run one bare call
and one checker call on any text, with the same runners, ledger and rubric.
"""
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True          # a run from a build folder never writes into the hub's tools/

TOOL_VERSION = "0.1.1"
HERE = Path(__file__).resolve().parent

# ── the shape ──────────────────────────────────────────────────────────────
MARK = "[PROTECTOR:%s]"                  # every prompt opens with its role's marker
ROLES = ("draft", "check", "revise", "bare")

# The six rubric lines (RULING R1): key, plain name, the test in one sentence.
RUBRIC = (
    ("read", "read before claim",
     "every claim about a source comes after that source was read; no «none», «empty» or "
     "«does not exist» without the look that could find it"),
    ("asked", "the question asked",
     "every part of the question is answered, and nothing that was not asked"),
    ("shown", "work shown",
     "every number, date, rule or name in the answer is traced to a step or a source line"),
    ("rederived", "re-derived",
     "every checkable claim was recomputed or looked up again by you, the checker, and "
     "MATCHES the draft; a mismatch is a fail, with both values named"),
    ("gaps", "gaps named",
     "what could not be read or is not known is said in words, never filled in"),
    ("one", "one answer",
     "one position and one ANSWER line; no hedging between two answers"),
)
MARKS = ("pass", "fail", "na")

# The ladders (RULING R2). Mechanical work climbs sonnet → opus → fable. Judgment
# work never runs on opus or sonnet (the step-down law): its first rung is the
# codex mind, whose NAME comes from the registry (an alias such as ASTRA), never
# from this file.
LADDERS = {
    "mechanical": ("sonnet", "opus", "fable"),
    "judgment": ("codex", "fable"),
}
AGAINST_RUNG = "fable"                  # --against-fable: the bare question, once, on this rung
RUNNER_KINDS = ("claude", "codex")      # the runners this tool knows by name
VOTE_AGREE = (2, 3)                     # a vote signs only when two thirds agree
VOTE_MAX = 9
NUMBER_TOLERANCE = 0.005                # numbers agree within half a percent
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EFFORT = "high"                 # thinking turned up on every call
DEFAULT_TIMEOUT = 300
HEARTBEAT_S = 30                        # a waiting window is never silent longer than this
CALL_CAP_USD = "2.00"                   # the claude CLI's --max-budget-usd, per call
SOURCES_CAP = 1000000                   # bytes of sources one prompt may carry

# The state dir effort.py's installed hook writes (as ~/.claude/settings.json names it):
# machine-local, never synced.
DEFAULT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".exocortex", "effort")
LEDGER_FILE = "protector-ledger.jsonl"
LOG_FILE = "protector.log"
LOG_CAP = 1 << 20

USAGE = """protector.py — a cheap mind plans, reads, drafts, is checked by a fresh
checker on six lines, revises once, and is graded; the grade signs the answer or
sends the question one mind up.

  protector.py ask "<question>" [--sources F ...] [--model sonnet]
      [--kind mechanical|judgment] [--ceiling MIND] [--vote N --checkable]
      [--effort low|medium|high|xhigh|max] [--runner claude|codex|<cmd>]
      [--timeout 300] [--json] [--dry-run] [--against-fable] [--state-dir DIR]
  protector.py ledger [--week] [--state-dir DIR]

  ladders     mechanical: sonnet → opus → fable · judgment: the codex mind → fable
  --ceiling   the highest mind the run may use (a routine passes opus)
  --vote N    N drafts, the majority is checked; needs --checkable (one number,
              yes/no or short string); under two thirds agreeing = one mind up
  --runner    default: each rung on its own CLI; a <cmd> reads the prompt on
              stdin, prints the answer (or the claude -p JSON) on stdout, and
              gets PROTECTOR_MODEL, PROTECTOR_ROLE, PROTECTOR_EFFORT
  --dry-run   print the prompts and the runner line; call nothing
  --against-fable   also run the bare question once on fable — it spends
              flagship quota — and print the measured comparison

  exit 0 signed · 4 unsigned at the ceiling · 2 STOP (one plain line)
  ledger: <state-dir>/protector-ledger.jsonl (default ~/.exocortex/effort)
"""

LEDGER_TAIL = "(estimate at list rates; a measured Fable run is --against-fable)"


class Stop(Exception):
    """One plain sentence, printed as `STOP: <it>`, exit 2."""


# ── small plumbing ─────────────────────────────────────────────────────────

def utf8_streams():
    for stream in (sys.stdout, sys.stderr):
        try:
            if (stream.encoding or "").lower().replace("-", "").replace("_", "") != "utf8":
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def oneline(text, cap=200):
    text = " ".join(str(text or "").split())
    return text if len(text) <= cap else text[:cap - 1] + "…"


def now_iso():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def find_tool(name):
    """A sibling tool: beside this file (the installed shape) first, then the
    nearest tools/ folder above it (a build folder inside the hub)."""
    for folder in [HERE] + [p / "tools" for p in HERE.parents]:
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


_COMMON = [None]


def common():
    """exo_common — run_bounded, kill_tree, the registry. Found, never assumed."""
    if _COMMON[0] is None:
        found = find_tool("exo_common.py")
        if not found:
            raise Stop("exo_common.py is not beside protector.py (nor in a tools/ folder above it)")
        if str(found.parent) not in sys.path:
            sys.path.insert(0, str(found.parent))
        import exo_common                                          # noqa: E402
        _COMMON[0] = exo_common
    return _COMMON[0]


def log_line(state_dir, text):
    """One bounded line in the tool's own log, rotated at 1 MB. Never raises."""
    try:
        os.makedirs(str(state_dir), exist_ok=True)
        path = os.path.join(str(state_dir), LOG_FILE)
        try:
            if os.path.getsize(path) > LOG_CAP:
                os.replace(path, path + ".1")
        except OSError:
            pass
        with io.open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("%s %s\n" % (now_iso(), oneline(text, 500)))
    except Exception:
        pass


class Opts(object):
    """What one run needs to know. In-process callers build one with keywords."""

    def __init__(self, **kw):
        self.runner = None
        self.effort = DEFAULT_EFFORT
        self.timeout = DEFAULT_TIMEOUT
        self.state_dir = DEFAULT_STATE_DIR
        self.quiet = True
        self.env = None
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.calls = []
        self.ledger_said = False
        self.__dict__.update(kw)


def progress(opts, text):
    """A flushed progress line on stderr (quiet under --json and in-process)."""
    if not opts.quiet:
        sys.stderr.write("protector: %s\n" % text)
        sys.stderr.flush()


# ── the minds: names from the registry, runners by family ──────────────────

def reg_minds():
    try:
        return common()._reg().get("minds") or []
    except Stop:
        raise
    except Exception:
        return []


def mind_block(name):
    for entry in reg_minds():
        if str(entry.get("name", "")).strip().lower() == str(name).strip().lower():
            return entry
    return {}


def mind_word(rung):
    """The name a person reads for a rung: the registry's, else the CLI's word."""
    kind = rung if rung in RUNNER_KINDS and rung != "claude" else "claude"
    try:
        name = common().mind_of(kind, "claude-%s" % rung if kind == "claude" else "")
    except Stop:
        raise
    except Exception:
        name = ""
    return (name or rung).lower()


def rung_kind(rung):
    kind = str(mind_block(mind_word(rung)).get("kind", "")).strip().lower()
    if kind in RUNNER_KINDS:
        return kind
    return rung if rung in RUNNER_KINDS else "claude"


def rung_model(rung):
    """The model word the CLI is given: the registry's `cli`, else the rung's own word
    (a codex rung with no `cli` gives none: the CLI's own default model)."""
    cli = str(mind_block(mind_word(rung)).get("cli", "")).strip()
    if cli:
        return cli
    return None if rung_kind(rung) == "codex" else rung


def claude_quiet_flag(env):
    """`--bare` reads ONLY ANTHROPIC_API_KEY (OAuth and the keychain are never read —
    `claude --help` says so), so a claude.ai login is refused under it with
    «Not logged in». With no API key the run takes `--safe-mode` instead: hooks,
    CLAUDE.md, skills and MCP off, auth as signed in. The exact command
    (with --bare) is kept for the API-key road."""
    return "--bare" if (env or {}).get("ANTHROPIC_API_KEY") else "--safe-mode"


def child_env(opts, extra=None):
    env = dict(os.environ)
    env.update(opts.env or {})
    env.update(extra or {})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def runner_for(rung, opts, check=True):
    """{kind, name, argv, cwd} for one rung. check=False (the dry run) never
    requires the CLI to be installed."""
    want = opts.runner or rung_kind(rung)
    env = child_env(opts)
    if want in RUNNER_KINDS:
        if want != rung_kind(rung):
            raise Stop("the %s runner cannot run the %s rung — leave --runner off and each "
                       "rung takes its own CLI" % (want, mind_word(rung)))
        if check:
            try:
                exe, _version, _how = common().headless_command(
                    mind_word(rung), "windows" if os.name == "nt" else "macos", env)
            except common().Stop as exc:
                raise Stop(str(exc))
        else:
            exe = shutil.which(want, path=env.get("PATH")) or want
        model = rung_model(rung)
        if want == "claude":
            argv = [exe, "-p", "--model", model, "--effort", opts.effort, "--output-format",
                    "json", claude_quiet_flag(env), "--no-session-persistence",
                    "--max-budget-usd", CALL_CAP_USD]
        else:
            effort = "xhigh" if opts.effort == "max" else opts.effort
            argv = [exe, "exec"] + (["--model", model] if model else []) + [
                "--json", "--skip-git-repo-check", "--sandbox", "read-only",
                "-c", "model_reasoning_effort=%s" % effort, "-"]
        return {"kind": want, "name": want, "argv": argv, "cwd": tempfile.gettempdir()}
    if os.path.isfile(want):
        tokens = [want]
    else:
        try:
            tokens = shlex.split(want, posix=(os.name != "nt"))
        except ValueError:
            raise Stop("the runner «%s» is not a command that can be read" % want)
    if not tokens:
        raise Stop("--runner is empty")
    if not os.path.isfile(tokens[0]):
        found = shutil.which(tokens[0], path=env.get("PATH"))
        if not found:
            if check:
                raise Stop("the runner «%s» is not on PATH" % tokens[0])
        else:
            tokens[0] = found
    if tokens[0].lower().endswith(".py"):
        tokens = [sys.executable or "python3"] + tokens
    script = tokens[1] if len(tokens) > 1 and tokens[0] == (sys.executable or "python3") else tokens[0]
    return {"kind": "cmd", "name": os.path.basename(script), "argv": tokens, "cwd": os.getcwd()}


def run_with_input(argv, text, timeout, env, cwd, beat=None):
    """(code, stdout, stderr): the prompt on stdin, the whole process tree killed
    on a timeout (exo_common.kill_tree, the run_bounded rule), 124 on a timeout,
    125 when it would not start. `beat` is called every HEARTBEAT_S while waiting."""
    kw = {} if os.name == "nt" else {"start_new_session": True}
    try:
        proc = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, **kw)
    except Exception as exc:
        return 125, "", repr(exc)
    data = text.encode("utf-8")
    deadline = time.time() + float(timeout)
    first = True
    while True:
        left = deadline - time.time()
        if left <= 0:
            common().kill_tree(proc)
            try:
                proc.communicate(timeout=10)
            except Exception:
                pass
            return 124, "", ""
        try:
            out, err = proc.communicate(input=data if first else None,
                                        timeout=min(HEARTBEAT_S, left))
            return (proc.returncode, (out or b"").decode("utf-8", "replace"),
                    (err or b"").decode("utf-8", "replace"))
        except subprocess.TimeoutExpired:
            first = False
            if beat and time.time() < deadline:
                beat()
        except Exception as exc:
            common().kill_tree(proc)
            return 125, "", repr(exc)


# ── reading what a runner printed ──────────────────────────────────────────

def first_json_object(text, want_key=None):
    """The first JSON object in a text (fences and prose around it allowed); with
    want_key, the first object that carries that key, else the first object."""
    decoder = json.JSONDecoder()
    fallback = None
    for i, ch in enumerate(text or ""):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text, i)
        except ValueError:
            continue
        if isinstance(obj, dict):
            if want_key is None or want_key in obj:
                return obj
            if fallback is None:
                fallback = obj
    return fallback


def tokens_of(usage):
    if not isinstance(usage, dict):
        return None
    try:
        return {"input": int(usage.get("input_tokens") or 0),
                "cache_write": int(usage.get("cache_creation_input_tokens") or 0),
                "cache_read": int(usage.get("cache_read_input_tokens") or 0),
                "output": int(usage.get("output_tokens") or 0)}
    except (TypeError, ValueError):
        return None


def claude_shape(obj):
    """(text, tokens, model id, cli cost, is_error) from a `claude -p` JSON object."""
    model_id = ""
    mu = obj.get("modelUsage")
    if isinstance(mu, dict) and mu:
        model_id = max(mu.keys(), key=lambda k: int((mu.get(k) or {}).get("outputTokens") or 0)
                       if isinstance(mu.get(k), dict) else 0)
    cost = obj.get("total_cost_usd")
    return (str(obj.get("result") or ""), tokens_of(obj.get("usage")), model_id,
            cost if isinstance(cost, (int, float)) else None, bool(obj.get("is_error")))


def codex_shape(out):
    """(text, tokens, model id, cost, is_error, error text) from `codex exec --json` events."""
    text, tokens, error = "", None, ""
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        kind = str(ev.get("type") or "")
        item = ev.get("item") if isinstance(ev.get("item"), dict) else {}
        if kind == "item.completed" and item.get("type") in ("agent_message", "assistant_message"):
            text = str(item.get("text") or text)
        elif kind == "turn.completed" and isinstance(ev.get("usage"), dict):
            u = ev["usage"]
            cached = int(u.get("cached_input_tokens") or 0)
            tokens = {"input": max(0, int(u.get("input_tokens") or 0) - cached),
                      "cache_write": 0, "cache_read": cached,
                      "output": int(u.get("output_tokens") or 0)}
        elif kind in ("error", "turn.failed"):
            error = oneline(ev.get("message") or (ev.get("error") or {}).get("message") or line)
    return text, tokens, "", None, bool(error and not text), error


def parse_runner(kind, code, out, err, login_hint=""):
    """{text, tokens, model_id, cli_cost} or a Stop. A CLI's own error is a tool
    failure (STOP), never a reasoning failure."""
    if kind == "codex":
        text, tokens, model_id, cost, is_error, error = codex_shape(out)
        if is_error or (code != 0 and not text):
            raise Stop("the codex CLI failed: %s" % oneline(error or err or out or "exit %d" % code))
        return {"text": text, "tokens": tokens, "model_id": model_id, "cli_cost": cost}
    obj = None
    stripped = (out or "").strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except ValueError:
            obj = None
    if not (isinstance(obj, dict) and "result" in obj) and kind == "claude":
        obj = first_json_object(stripped, "result")      # a warning line printed ahead of it
    if isinstance(obj, dict) and "result" in obj:
        text, tokens, model_id, cost, is_error = claude_shape(obj)
        if is_error:
            if "not logged in" in text.lower():
                raise Stop("the model's CLI answered «%s»%s" % (oneline(text, 80), login_hint))
            raise Stop("the model's CLI reported an error: %s" % oneline(text or obj.get("subtype")))
        return {"text": text, "tokens": tokens, "model_id": model_id, "cli_cost": cost}
    if kind == "claude":
        raise Stop("the claude CLI did not print its JSON (exit %d): %s"
                   % (code, oneline(err or out or "no output")))
    # <cmd>: the answer on stdout, usage from a trailing JSON line when one is printed
    lines = stripped.splitlines()
    tokens = None
    if lines and lines[-1].strip().startswith("{"):
        try:
            tail = json.loads(lines[-1])
            tokens = tokens_of(tail.get("usage") if isinstance(tail.get("usage"), dict) else tail)
            lines = lines[:-1]
        except ValueError:
            pass
    text = "\n".join(lines).strip()
    if code != 0 and not text:
        raise Stop("the runner exited %d: %s" % (code, oneline(err or "no output")))
    return {"text": text, "tokens": tokens, "model_id": "", "cli_cost": None}


# ── prices: usage.py's table, read from its text ───────────────────────────
# usage.py is NOT imported: importing it reconfigures sys.stdout and sets
# sys.dont_write_bytecode (module level). Its DEFAULTS["prices"]
# literal (~line 142) is read out of the file and evaluated as a literal — one
# table, never a second copy with silently different numbers.

_PRICES = [None]


def load_prices():
    """({prefix: {input, cache_write, cache_read, output}}, problem or '')."""
    if _PRICES[0] is None:
        import ast
        path = find_tool("usage.py")
        table, problem = {}, ""
        if not path:
            problem = "usage.py's price table was not found"
        else:
            try:
                text = path.read_text(encoding="utf-8")
                at = text.index('"prices":')
                start = text.index("{", at)
                depth, end = 0, None
                for i in range(start, len(text)):
                    if text[i] == "{":
                        depth += 1
                    elif text[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                block = re.sub(r"#[^\n]*", "", text[start:end])
                raw = ast.literal_eval(block)
                for prefix, rate in raw.items():
                    if isinstance(rate, dict):
                        table[str(prefix)] = dict((k, float(rate.get(k) or 0)) for k in
                                                  ("input", "cache_write", "cache_read", "output"))
            except Exception as exc:
                table, problem = {}, "usage.py's price table could not be read (%s)" % oneline(exc, 80)
        _PRICES[0] = (table, problem)
    return _PRICES[0]


def price_of(model_id):
    """The longest prefix row that the model id starts with (usage.py's price_of rule)."""
    table, _problem = load_prices()
    best = None
    for prefix, rate in table.items():
        if model_id and str(model_id).startswith(prefix):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, rate)
    return best[1] if best else None


def fable_row():
    """Compatibility API: price the registry's Claude flagship, whatever its name."""
    table, _problem = load_prices()
    rows = [m for m in common()._reg().get('minds', [])
            if m.get('kind') == 'claude' and m.get('tier') == 'flagship']
    for row in sorted(rows, key=lambda m: str(m.get('name', '')).casefold()):
        matches = [prefix for prefix in table if str(row.get('app_id') or '').startswith(prefix)]
        if matches:
            prefix = max(matches, key=len)
            return prefix, table[prefix]
    return None, None


def dollars(tokens, rate):
    if not tokens or not rate:
        return None
    return (tokens["input"] * rate["input"] + tokens["cache_write"] * rate["cache_write"]
            + tokens["cache_read"] * rate["cache_read"] + tokens["output"] * rate["output"]) / 1e6


# ── one call ───────────────────────────────────────────────────────────────

def call_model(rung, role, prompt, opts, step=""):
    """One runner call: bounded, ledgered, parsed. Returns the call record."""
    spec = runner_for(rung, opts)
    mind = mind_word(rung)
    model = rung_model(rung) or ""
    env = child_env(opts, {"PROTECTOR_MODEL": rung, "PROTECTOR_MIND": mind,
                           "PROTECTOR_ROLE": role, "PROTECTOR_EFFORT": opts.effort})
    login_hint = (" — --bare reads only ANTHROPIC_API_KEY, and the CLI's own sign-in is never "
                  "read under it" if "--bare" in spec["argv"]
                  else " — sign the CLI in: run `claude`, then /login, in a Terminal"
                  if spec["kind"] == "claude" else "")
    started = time.time()

    def beat():
        progress(opts, "%s · %s · still waiting · %d s" % (mind, role, time.time() - started))

    code, out, err = run_with_input(spec["argv"], prompt, opts.timeout, env, spec["cwd"], beat)
    seconds = round(time.time() - started, 1)
    if code == 124:
        raise Stop("the model did not answer in %s s" % ("%g" % float(opts.timeout)))
    if code == 125:
        raise Stop("the runner «%s» would not start: %s" % (spec["name"], oneline(err, 120)))
    got = parse_runner(spec["kind"], code, out, err, login_hint)
    block = mind_block(mind)
    model_id = got["model_id"] or str(block.get("app_id") or "") or (
        ("codex:%s" % (model or "default")) if spec["kind"] == "codex" else model)
    rate = price_of(model_id)
    fable = fable_row()[1]
    call = {"time": now_iso(), "run": opts.run_id, "mind": mind, "model": model_id,
            "role": role, "runner": spec["kind"], "tokens": got["tokens"],
            "cli_cost_usd": got["cli_cost"], "usd": dollars(got["tokens"], rate),
            "fable_usd": dollars(got["tokens"], fable), "seconds": seconds,
            "text": got["text"]}
    opts.calls.append(call)
    ledger_append(opts, call)
    progress(opts, "%s%s · %s · %.1f s" % (mind, (" · " + step) if step else "", role, seconds))
    return call


def ledger_append(opts, call, row=None, filename=None, durable=False):
    if row is None:
        row = dict((k, call[k]) for k in ("time", "run", "mind", "model", "role", "runner",
                                          "cli_cost_usd", "usd", "fable_usd", "seconds"))
        t = call["tokens"]
        row.update({"input": t["input"] if t else None, "cache_write": t["cache_write"] if t else None,
                    "cache_read": t["cache_read"] if t else None, "output": t["output"] if t else None,
                    "tokens_known": bool(t)})
    try:
        os.makedirs(str(opts.state_dir), exist_ok=True)
        with io.open(os.path.join(str(opts.state_dir), filename or LEDGER_FILE), "a", encoding="utf-8",
                     newline="\n") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            if durable:
                fh.flush()
                os.fsync(fh.fileno())
        return True
    except Exception as exc:
        if not opts.ledger_said:
            opts.ledger_said = True
            sys.stderr.write("protector: ledger NOT written (%s)\n" % oneline(exc, 120))
        log_line(opts.state_dir, "ledger not written: %r" % (exc,))

        return False


# ── the prompts ────────────────────────────────────────────────────────────

THINK = ("Think before you answer. Show the work the way a math teacher wants it: every "
         "step written down, nothing taken on faith.")


def sources_block(sources):
    if not sources:
        return ("THE SOURCES\n(none were given — whatever a part needs that you cannot read, "
                "say in GAPS; never fill it in)\n")
    parts = ["THE SOURCES — read every source that decides a part before any claim about it"]
    for i, (name, text) in enumerate(sources, 1):
        parts.append("=== source %d: %s ===\n%s\n=== end of source %d ===" % (i, name, text.rstrip(), i))
    return "\n".join(parts) + "\n"


SHAPE = """End your reply with exactly these three sections, in this order:
ANSWER: <one line: one position, no hedging between two answers>
WORK:
- <each number, date, rule or name in the answer, traced to a step or a source line>
GAPS: <what you could not read or do not know, in words; or "none">"""


def draft_prompt(question, sources):
    return "\n".join([
        MARK % "draft", THINK, "", "THE QUESTION", question.strip(), "", sources_block(sources),
        "ORDER OF WORK",
        "1. PLAN, in words: what the question asks, every part; which source decides each "
        "part; what is checkable (a number, a date, a rule, a yes/no) and what is judgment.",
        "2. READ: read every source that decides a part before any claim about it. Never say "
        "none, empty or does not exist without the look that could find it.",
        "3. DRAFT: the answer with its work shown.", "", SHAPE])


def rubric_text():
    return "\n".join("%s — %s: %s" % (key, name, test) for key, name, test in RUBRIC)


CHECK_OBJECT = ('{"lines": {"read": "pass|fail|na", "asked": "pass|fail|na", "shown": '
                '"pass|fail|na", "rederived": "pass|fail|na", "gaps": "pass|fail|na", "one": '
                '"pass|fail|na"}, "rederived": [{"claim": "...", "draft": "<the bare value>", "got": "<the bare value you got>", '
                '"match": true}], "findings": ["..."]}')


def check_prompt(question, sources, shaped):
    return "\n".join([
        MARK % "check",
        "You are the checker. You did not write the draft below, and you see only its answer "
        "and its work, never its reasoning. " + THINK, "",
        "THE QUESTION", question.strip(), "", sources_block(sources),
        "THE DRAFT UNDER CHECK", shaped.strip(), "",
        "THE SIX LINES — mark each pass, fail or na (na only when the line does not apply to "
        "this question):", rubric_text(), "",
        "For re-derived: recompute every arithmetic step, re-read every cell, look up every "
        "rule again YOURSELF, and list each checkable claim with the draft's value and the "
        "value you got. In each row, draft and got carry the BARE value only — a number, a "
        "date, a short string — never the working; your arithmetic and reasons go in "
        "findings.", "",
        "Answer with ONE JSON object and nothing else:", CHECK_OBJECT])


def revise_prompt(question, sources, draft, grade):
    found = []
    for item in grade.get("failed") or []:
        if item.get("draft") is not None:
            found.append("- %s failed: %s — your draft says %s, the checker got %s"
                         % (item["name"], item.get("claim") or "a claim", item["draft"], item["got"]))
        else:
            found.append("- %s failed" % item["name"])
    for line in grade.get("findings") or []:
        found.append("- %s" % oneline(line, 400))
    return "\n".join([
        MARK % "revise", THINK, "", "THE QUESTION", question.strip(), "", sources_block(sources),
        "YOUR DRAFT", draft["shaped"].strip(), "",
        "THE CHECKER'S FINDINGS", "\n".join(found) or "- (none named)", "",
        "Read again every source that decides a failed part; fix what is wrong and keep what "
        "is right. Revise once.", "", SHAPE])


def bare_prompt(question, sources):
    return "\n".join([MARK % "bare", question.strip(), "", sources_block(sources)])


# ── reading a draft and a grade ────────────────────────────────────────────

SECTION = r"^[ \t>*_#`-]*%s[*_ \t]*:[*_ \t]*(.*)$"
ANSWER_RE = re.compile(SECTION % "ANSWER", re.M | re.I)
WORK_RE = re.compile(SECTION % "WORK", re.M | re.I)
GAPS_RE = re.compile(SECTION % "GAPS", re.M | re.I)


def parse_draft(text):
    """{answer, work, gaps, shaped} from the LAST ANSWER: line on, or None when
    there is no ANSWER line (not in shape)."""
    found = list(ANSWER_RE.finditer(text or ""))
    if not found:
        return None
    m = found[-1]
    shaped = text[m.start():]
    answer = m.group(1).strip().strip("*_` ").strip()
    if not answer:
        rest = [ln.strip() for ln in text[m.end():].splitlines() if ln.strip()]
        if rest and not WORK_RE.match(rest[0]) and not GAPS_RE.match(rest[0]):
            answer = rest[0].strip("*_` ").strip()
    if not answer:
        return None
    w = WORK_RE.search(shaped)
    g = GAPS_RE.search(shaped)
    work = shaped[w.start():g.start() if g and g.start() > w.start() else len(shaped)] if w else ""
    gaps = shaped[g.start():] if g else ""
    return {"answer": answer, "work": work.strip(), "gaps": gaps.strip(), "shaped": shaped.strip()}


NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def numbers_in(text):
    clean = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text))
    return [float(x) for x in NUM_RE.findall(clean)]


def close(a, b):
    if a == b:
        return True
    return abs(a - b) <= NUMBER_TOLERANCE * max(abs(a), abs(b))


def norm_mark(value):
    v = str(value or "").strip().lower().replace("/", "").replace(" ", "")
    return v if v in MARKS else None


def mismatch(entry):
    """True when the checker's value and the draft's differ: the checker says so,
    or both carry a number and the numbers differ by more than half a percent."""
    said = entry.get("match")
    if said is False or str(said).strip().lower() in ("false", "no"):
        return True
    a, b = numbers_in(entry.get("draft", "")), numbers_in(entry.get("got", ""))
    if not (a and b):
        return False
    # The draft's value leads its field; the checker's value is the bare number it was
    # asked for — or, when it wrote its working into the field (a real model can:
    # «… = 45.78. … = 140.69. Difference 94.91.»), the result at the END of the line, or the
    # value at its start before an explanation. A match on either is a match.
    return not (close(a[0], b[-1]) or close(a[0], b[0]))


def judge(text):
    """The grade from a checker's answer — computed from its lines and its
    re-derived values, never from anyone's confidence. in_shape False when the
    answer is not the JSON object the checker was asked for."""
    obj = first_json_object(text, "lines")
    if not isinstance(obj, dict) or not isinstance(obj.get("lines"), dict):
        return {"in_shape": False, "why": "the checker did not answer with its JSON object"}
    lines = {}
    for key, _name, _test in RUBRIC:
        mark = norm_mark(obj["lines"].get(key))
        if mark is None:
            return {"in_shape": False, "why": "the checker left the line «%s» out" % key}
        lines[key] = mark
    entries = [e for e in (obj.get("rederived") or []) if isinstance(e, dict)] \
        if isinstance(obj.get("rederived"), list) else []
    misses = [e for e in entries if mismatch(e)]
    if misses:
        lines["rederived"] = "fail"
    applicable = [k for k, _n, _t in RUBRIC if lines[k] != "na"]
    if not applicable:
        return {"in_shape": False, "why": "the checker marked every line n/a"}
    failed = []
    for key, name, _test in RUBRIC:
        if lines[key] != "fail":
            continue
        item = {"key": key, "name": name, "claim": None, "draft": None, "got": None}
        if key == "rederived" and misses:
            item.update({"claim": str(misses[0].get("claim") or "").strip() or None,
                         "draft": str(misses[0].get("draft", "")).strip(),
                         "got": str(misses[0].get("got", "")).strip()})
        failed.append(item)
    findings = [str(f) for f in (obj.get("findings") or []) if str(f).strip()] \
        if isinstance(obj.get("findings"), list) else []
    return {"in_shape": True, "lines": lines, "failed": failed, "rederived": entries,
            "findings": findings, "applicable": len(applicable),
            "passed": len([k for k in applicable if lines[k] == "pass"])}


def escalate_detail(failed):
    """`re-derived failed (per-run saving: 1.71 vs 1.61)` — the escalate line's words."""
    out = []
    for f in failed:
        if f.get("draft") is not None:
            claim = ("%s: " % f["claim"]) if f.get("claim") else ""
            out.append("%s failed (%s%s vs %s)" % (f["name"], claim, f["draft"], f["got"]))
        else:
            out.append("%s failed" % f["name"])
    return ", ".join(out)


def unsigned_detail(failed):
    """`re-derived (1.71 vs 1.61)` — the UNSIGNED mark's words."""
    return ", ".join("%s (%s vs %s)" % (f["name"], f["draft"], f["got"])
                     if f.get("draft") is not None else f["name"] for f in failed)


def grade_summary(grade):
    """One reading of a single check: `signed 6/6` or `5/6 — re-derived failed (…)`."""
    if not grade.get("in_shape"):
        return "did not answer in shape (%s)" % grade.get("why", "")
    count = "%d/%d" % (grade["passed"], grade["applicable"])
    if not grade["failed"]:
        return "signed " + count
    return "%s — %s" % (count, escalate_detail(grade["failed"]))


# ── the vote ───────────────────────────────────────────────────────────────

def answer_key(line):
    """(numbers, words) of an ANSWER line: case and spacing folded, numbers as numbers."""
    clean = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(line).lower())
    nums = [float(x) for x in NUM_RE.findall(clean)]
    words = " ".join(re.sub(r"[^\w]+", " ", NUM_RE.sub(" ", clean)).split())
    return nums, words


def agree(a, b):
    (na, wa), (nb, wb) = answer_key(a), answer_key(b)
    return wa == wb and len(na) == len(nb) and all(close(x, y) for x, y in zip(na, nb))


def tally(drafts):
    """Groups of agreeing drafts, largest first (ties: the earliest). Drafts not in
    shape join no group."""
    groups = []
    for i, d in enumerate(drafts):
        if d is None:
            continue
        for g in groups:
            if agree(drafts[g[0]]["answer"], d["answer"]):
                g.append(i)
                break
        else:
            groups.append([i])
    groups.sort(key=lambda g: (-len(g), g[0]))
    return groups


# ── one mind: draft (× vote), check, revise once, check again ──────────────

def run_mind(rung, question, sources, opts, vote=1):
    """The shape on one mind. Returns {mind, signed, why, draft, grade, vote, revised}."""
    mind = mind_word(rung)
    out = {"mind": mind, "rung": rung, "signed": False, "why": "", "unsigned": "",
           "draft": None, "grade": None, "vote": None, "revised": False}
    planned = vote + 1
    drafts = []
    for i in range(vote):
        call = call_model(rung, "draft", draft_prompt(question, sources), opts,
                          "call %d of %d" % (i + 1, planned))
        drafts.append(parse_draft(call["text"]))
    if vote > 1:
        groups = tally(drafts)
        if not groups:
            out["why"] = "did not answer in shape (no draft has an ANSWER line)"
            out["unsigned"] = "did not answer in shape"
            return out
        size = len(groups[0])
        out["vote"] = "%d/%d" % (size, vote)
        if size * VOTE_AGREE[1] < VOTE_AGREE[0] * vote:
            out["draft"] = drafts[groups[0][0]]
            out["why"] = out["unsigned"] = "vote split %d/%d" % (size, vote)
            return out
        draft = drafts[groups[0][0]]
    else:
        draft = drafts[0]
    if draft is None:
        out["why"] = "did not answer in shape (the draft has no ANSWER line)"
        out["unsigned"] = "did not answer in shape"
        return out
    out["draft"] = draft
    step = vote + 1
    grade = judge(call_model(rung, "check", check_prompt(question, sources, draft["shaped"]), opts,
                             "call %d of %d" % (step, planned))["text"])
    out["grade"] = grade
    if not grade["in_shape"]:
        out["why"] = "did not answer in shape (%s)" % grade["why"]
        out["unsigned"] = "did not answer in shape"
        return out
    if not grade["failed"]:
        out["signed"] = True
        return out
    planned += 2
    revised = parse_draft(call_model(rung, "revise", revise_prompt(question, sources, draft, grade),
                                     opts, "call %d of %d" % (step + 1, planned))["text"])
    if revised is None:
        out["why"] = "did not answer in shape (the revise has no ANSWER line)"
        out["unsigned"] = "did not answer in shape"
        return out
    out["draft"], out["revised"] = revised, True
    grade = judge(call_model(rung, "check", check_prompt(question, sources, revised["shaped"]),
                             opts, "call %d of %d" % (step + 2, planned))["text"])
    out["grade"] = grade
    if not grade["in_shape"]:
        out["why"] = "did not answer in shape (%s)" % grade["why"]
        out["unsigned"] = "did not answer in shape"
    elif grade["failed"]:
        out["why"] = escalate_detail(grade["failed"])
        out["unsigned"] = unsigned_detail(grade["failed"])
    else:
        out["signed"] = True
    return out


# ── in-process: a bare answer, and the checker on any text (the gate's) ────

def bare_answer(question, sources, rung, opts):
    """One call with the bare question — no order of work, no shape."""
    return call_model(rung, "bare", bare_prompt(question, sources), opts)["text"]


def grade_text(question, sources, text, rung, opts):
    """The same checker, the same six lines, on any text (a bare answer)."""
    return judge(call_model(rung, "check", check_prompt(question, sources, text), opts)["text"])


# ── the ledger line ────────────────────────────────────────────────────────

def ledger_summary(calls):
    """{line, by_mind, usd, fable_usd, saved_usd} for the calls of one run."""
    order, by = [], {}
    for c in calls:
        if c["mind"] not in by:
            order.append(c["mind"])
            by[c["mind"]] = {"calls": 0, "usd": 0.0, "priced": True, "tokens_known": True}
        m = by[c["mind"]]
        m["calls"] += 1
        if not c["tokens"]:
            m["tokens_known"] = False
        if c["usd"] is None:
            m["priced"] = False
        else:
            m["usd"] += c["usd"]
    parts, total, why = [], 0.0, ""
    for name in order:
        m = by[name]
        if not m["tokens_known"]:
            parts.append("%s tokens unknown" % name)
            total, why = None, why or "%s's tokens are unknown" % name
        elif not m["priced"]:
            parts.append("%s no rate" % name)
            total, why = None, why or "%s has no rate" % name
        else:
            parts.append("%s $%.3f" % (name, m["usd"]))
            if total is not None:
                total += m["usd"]
    head = " + ".join(parts)
    if total is not None and len(order) > 1:
        head += " = $%.3f" % total
    prefix, _row = fable_row()
    fable_ok = prefix is not None and all(c["fable_usd"] is not None for c in calls)
    fable_total = sum(c["fable_usd"] for c in calls) if fable_ok else None
    word = prefix.split("-")[1].title() if prefix else "Fable"
    if fable_total is None:
        fable_part = "the same tokens at %s's rate: not computed" % word
        why = why or ("usage.py's table has no %s row" % word if prefix is None
                      else "some tokens are unknown")
    else:
        fable_part = "the same tokens at %s's rate $%.3f" % (word, fable_total)
    if total is not None and fable_total is not None:
        saved = fable_total - total
        saved_part = "saved $%.3f" % saved
    else:
        saved = None
        saved_part = "saved: not computed (%s)" % why
    problem = load_prices()[1]
    line = "LEDGER: %s · %s · %s %s%s" % (head or "no calls", fable_part, saved_part, LEDGER_TAIL,
                                          (" · %s" % problem) if problem else "")
    return {"line": line, "by_mind": by, "usd": total, "fable_usd": fable_total,
            "saved_usd": saved}


# ── the letter at the ceiling ──────────────────────────────────────────────

def send_letter(opts, mind, why, question):
    """One line to this machine's hub through mail.py --send. Never fails the run."""
    mail = find_tool("mail.py")
    if not mail:
        return "letter NOT sent: mail.py is not beside protector.py"
    machine = ""
    paths_tool = find_tool("exo_paths.py")
    if paths_tool:
        try:
            if str(paths_tool.parent) not in sys.path:
                sys.path.insert(0, str(paths_tool.parent))
            import exo_paths                                         # noqa: E402
            machine = str(exo_paths.paths(tool_file=str(mail)).get("machine") or "")
        except Exception as exc:
            log_line(opts.state_dir, "letter: the machine record did not answer: %r" % (exc,))
    if not machine:
        return "letter NOT sent: this machine's name is not in the record"
    to = "%s/hub" % machine.upper()
    text = ("protector: no signed answer at the ceiling (%s) — %s · question: %s"
            % (mind, why, oneline(question, 100)))
    action = ("decide what the unsigned answer is worth; run %s in %s"
              % (opts.run_id, os.path.join(str(opts.state_dir), LEDGER_FILE)))
    code, out = common().run_bounded([sys.executable or "python3", str(mail), "--send", to,
                                      mail.parent.parent.name, text, action],
                                     timeout=120, env=child_env(opts))
    if code == 0:
        return "letter sent to %s" % to
    log_line(opts.state_dir, "letter to %s: mail.py exited %d: %s" % (to, code, out))
    return "letter NOT sent to %s: mail.py exited %d" % (to, code)


# ── ask ────────────────────────────────────────────────────────────────────

def read_sources(paths):
    out, total = [], 0
    for p in paths:
        if not os.path.isfile(p):
            raise Stop("source not found: %s" % p)
        with io.open(p, "rb") as fh:
            data = fh.read(SOURCES_CAP + 1)
        total += len(data)
        if total > SOURCES_CAP:
            raise Stop("the sources pass %d bytes — more than one prompt should carry; give "
                       "the parts that decide the question" % SOURCES_CAP)
        out.append((os.path.basename(p), data.decode("utf-8", "replace")))
    return out


def rung_index(ladder, word):
    word = str(word or "").strip().lower()
    for i, rung in enumerate(ladder):
        if word in (rung, mind_word(rung)):
            return i
    return None


def plan_ladder(a):
    """(ladder, start index, ceiling index), or a refusal in one line."""
    ladder = LADDERS[a["kind"]]
    shown = " → ".join(mind_word(r) for r in ladder)
    start = 0
    if a.get("model"):
        start = rung_index(ladder, a["model"])
        if start is None:
            if a["kind"] == "judgment":
                raise Stop("judgment work never runs on %s — its ladder is %s (the step-down law)"
                           % (a["model"], shown))
            raise Stop("«%s» is not on the %s ladder (%s)" % (a["model"], a["kind"], shown))
    ceiling = len(ladder) - 1
    if a.get("ceiling"):
        ceiling = rung_index(ladder, a["ceiling"])
        if ceiling is None:
            raise Stop("a ceiling of %s is not on the %s ladder (%s)" % (a["ceiling"], a["kind"], shown))
        if ceiling < start:
            raise Stop("the ceiling %s is below the starting mind %s"
                       % (mind_word(ladder[ceiling]), mind_word(ladder[start])))
    return ladder, start, ceiling


def dry_run(a, opts, question, sources, ladder, start, ceiling):
    shown = " → ".join(mind_word(r) for r in ladder)
    vote = a["vote"]
    print("DRY RUN — nothing is called, nothing is written.")
    print("ladder: %s · %s work · starts on %s · ceiling %s"
          % (shown, a["kind"], mind_word(ladder[start]), mind_word(ladder[ceiling])))
    print("calls per mind: %d (%s check), %d with the one revise"
          % (vote + 1, "draft," if vote == 1 else "%d drafts, the majority's" % vote, vote + 3))
    for rung in ladder[start:ceiling + 1]:
        spec = runner_for(rung, opts, check=False)
        print("runner (%s): %s   (the prompt on stdin)" % (mind_word(rung), shlex.join(spec["argv"])))
    prompts = [draft_prompt(question, sources),
               check_prompt(question, sources, "<the draft's ANSWER, WORK and GAPS go here>")]
    if a["against_fable"]:
        prompts.append(bare_prompt(question, sources))
    for i, p in enumerate(prompts, 1):
        print("--- prompt %d of %d · %s ---" % (i, len(prompts), p.split("\n", 1)[0]))
        print(p)
    return 0


def against_fable(question, sources, opts, harness):
    progress(opts, "--against-fable: one bare call on %s — it spends flagship quota"
             % mind_word(AGAINST_RUNG))
    before = len(opts.calls)
    text = bare_answer(question, sources, AGAINST_RUNG, opts)
    call = opts.calls[before]
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if call["usd"] is not None and harness["usd"] is not None:
        line = ("LEDGER (measured): harness $%.3f · bare %s $%.3f · saved $%.3f"
                % (harness["usd"], call["mind"], call["usd"], call["usd"] - harness["usd"]))
    else:
        line = "LEDGER (measured): not computed (a call has no rate or no tokens)"
    return {"text": text, "first": first, "usd": call["usd"], "line": line}


def cmd_ask(a):
    opts = Opts(runner=a["runner"], effort=a["effort"], timeout=a["timeout"],
                state_dir=a["state_dir"], quiet=a["json"])
    question = a["question"]
    sources = read_sources(a["sources"])
    ladder, start, ceiling = plan_ladder(a)
    if a["dry_run"]:
        return dry_run(a, opts, question, sources, ladder, start, ceiling)
    for rung in ladder[start:ceiling + 1] + ((AGAINST_RUNG,) if a["against_fable"] else ()):
        runner_for(rung, opts)                          # a missing CLI stops before any call
    rounds, final, escalations = [], None, []
    for i in range(start, ceiling + 1):
        rung = ladder[i]
        result = run_mind(rung, question, sources, opts, a["vote"])
        rounds.append(result)
        final = result
        if result["signed"]:
            break
        if i < ceiling:
            line = "CHECK: escalate — %s · %s → %s" % (result["why"], result["mind"],
                                                      mind_word(ladder[i + 1]))
            escalations.append(line)
            if not a["json"]:
                print(line)
                sys.stdout.flush()
    best = next((r["draft"] for r in reversed(rounds) if r["draft"]), None)
    signed = bool(final and final["signed"])
    n_calls = len(opts.calls)
    if signed:
        g = final["grade"]
        climbed = [r["mind"] for r in rounds[:-1]]
        who = final["mind"] + (" (escalated from %s)" % " → ".join(climbed) if climbed else "")
        grade_line = "CHECK: signed %d/%d · %s%s · %d call%s" % (
            g["passed"], g["applicable"], who, (" · vote %s" % final["vote"]) if final["vote"] else "",
            n_calls, "" if n_calls == 1 else "s")
        code = 0
    else:
        grade_line = "CHECK: UNSIGNED — %s · %s at the ceiling · %d call%s" % (
            final["unsigned"] or final["why"], final["mind"], n_calls, "" if n_calls == 1 else "s")
        code = 4
    ledger = ledger_summary(opts.calls)
    extra = against_fable(question, sources, opts, ledger) if a["against_fable"] else None
    letter = send_letter(opts, final["mind"], final["unsigned"] or final["why"], question) \
        if not signed else None
    if a["json"]:
        obj = {"answer": best["answer"] if best else None,
               "work": best["work"] if best else None, "gaps": best["gaps"] if best else None,
               "grade": {"signed": signed,
                         "lines": (final["grade"] or {}).get("lines") if final else None,
                         "vote": final["vote"] if final else None, "mind": final["mind"],
                         "rounds": [{"mind": r["mind"], "signed": r["signed"], "why": r["why"],
                                     "revised": r["revised"], "vote": r["vote"]} for r in rounds],
                         "calls": n_calls, "line": grade_line, "escalations": escalations},
               "ledger": {"line": ledger["line"], "usd": ledger["usd"],
                          "fable_usd": ledger["fable_usd"], "saved_usd": ledger["saved_usd"],
                          "file": os.path.join(str(opts.state_dir), LEDGER_FILE), "run": opts.run_id},
               "calls": [{"role": c["role"], "mind": c["mind"], "model": c["model"],
                          "tokens": c["tokens"], "seconds": c["seconds"], "usd": c["usd"]}
                         for c in opts.calls],
               "against_fable": ({"first_line": extra["first"], "usd": extra["usd"],
                                  "line": extra["line"]} if extra else None),
               "letter": letter, "exit": code}
        print(json.dumps(obj, ensure_ascii=False, indent=1))
        return code
    if best:
        print(best["shaped"])
    else:
        print("ANSWER: (no answer in shape)")
    print(grade_line)
    print(ledger["line"])
    if extra:
        print("AGAINST FABLE (bare, one call): %s" % oneline(extra["first"], 160))
        print(extra["line"])
    if letter:
        print("LETTER: %s" % letter)
    return code


# ── ledger ─────────────────────────────────────────────────────────────────

def cmd_ledger(a):
    path = os.path.join(str(a["state_dir"]), LEDGER_FILE)
    since = datetime.now().astimezone() - timedelta(days=7) if a["week"] else None
    rows, bad = [], 0
    if os.path.isfile(path):
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    when = datetime.fromisoformat(str(row["time"]))
                    if when.tzinfo is None:
                        when = when.astimezone()
                except Exception:
                    bad += 1
                    continue
                if since is None or when >= since:
                    rows.append(row)
    span = "the last 7 days" if a["week"] else "all time"
    runs = len(set(r.get("run") for r in rows))
    print("LEDGER (%s · %s): %d call%s in %d run%s" % (span, path, len(rows),
                                                       "" if len(rows) == 1 else "s", runs,
                                                       "" if runs == 1 else "s"))
    order, by = [], {}
    for r in rows:
        mind = str(r.get("mind") or "?")
        if mind not in by:
            order.append(mind)
            by[mind] = {"calls": 0, "input": 0, "cache_write": 0, "cache_read": 0, "output": 0,
                        "usd": 0.0, "fable_usd": 0.0, "unknown": 0, "unpriced": 0}
        m = by[mind]
        m["calls"] += 1
        if not r.get("tokens_known"):
            m["unknown"] += 1
        else:
            for k in ("input", "cache_write", "cache_read", "output"):
                m[k] += int(r.get(k) or 0)
        if r.get("usd") is None:
            m["unpriced"] += 1
        else:
            m["usd"] += float(r["usd"])
        if r.get("fable_usd") is not None:
            m["fable_usd"] += float(r["fable_usd"])
    total, fable, complete = 0.0, 0.0, True
    for mind in order:
        m = by[mind]
        money = ("$%.3f" % m["usd"]) if not m["unpriced"] else (
            "no rate" if m["unpriced"] == m["calls"] else "$%.3f + %d call(s) with no rate"
            % (m["usd"], m["unpriced"]))
        print("  %-8s %3d call%s · in %s · cache-write %s · cache-read %s · out %s · %s%s"
              % (mind, m["calls"], " " if m["calls"] == 1 else "s", format(m["input"], ","),
                 format(m["cache_write"], ","), format(m["cache_read"], ","),
                 format(m["output"], ","), money,
                 (" · %d with tokens unknown" % m["unknown"]) if m["unknown"] else ""))
        total += m["usd"]
        fable += m["fable_usd"]
        if m["unpriced"] or m["unknown"]:
            complete = False
    if rows:
        tail = ("saved $%.3f" % (fable - total)) if complete else \
            "saved: not computed (a call has no rate or no tokens)"
        print("  total $%.3f · the same tokens at Fable's rate $%.3f · %s %s"
              % (total, fable, tail, LEDGER_TAIL))
    if bad:
        print("  %d line%s could not be read" % (bad, "" if bad == 1 else "s"))
    return 0


# ── the command line ───────────────────────────────────────────────────────

VALUE_FLAGS = {"--model": "model", "--kind": "kind", "--ceiling": "ceiling", "--vote": "vote",
               "--effort": "effort", "--runner": "runner", "--timeout": "timeout",
               "--state-dir": "state_dir"}
BOOL_FLAGS = {"--checkable": "checkable", "--json": "json", "--dry-run": "dry_run",
              "--against-fable": "against_fable", "--week": "week"}


def parse_args(argv):
    a = {"verb": argv[0], "question": None, "sources": [], "model": None, "kind": "mechanical",
         "ceiling": None, "vote": "1", "effort": DEFAULT_EFFORT, "runner": None,
         "timeout": str(DEFAULT_TIMEOUT), "state_dir": DEFAULT_STATE_DIR, "checkable": False,
         "json": False, "dry_run": False, "against_fable": False, "week": False}
    i, n = 1, len(argv)
    while i < n:
        tok = argv[i]
        if tok == "--sources":
            i += 1
            while i < n and not argv[i].startswith("--"):
                a["sources"].append(argv[i])
                i += 1
            if not a["sources"]:
                raise Stop("--sources needs at least one file")
            continue
        if tok in VALUE_FLAGS:
            if i + 1 >= n:
                raise Stop("%s needs a value" % tok)
            a[VALUE_FLAGS[tok]] = argv[i + 1]
            i += 2
            continue
        if tok in BOOL_FLAGS:
            a[BOOL_FLAGS[tok]] = True
            i += 1
            continue
        if tok.startswith("--"):
            raise Stop("unknown flag %s (protector.py --help)" % tok)
        if a["question"] is not None:
            raise Stop("one question at a time — put the whole question in quotes")
        a["question"] = tok
        i += 1
    return a


def check_args(a):
    if a["verb"] == "ledger":
        return a
    if not (a["question"] or "").strip():
        raise Stop("ask needs a question, in quotes")
    if a["kind"] not in LADDERS:
        raise Stop("--kind is mechanical or judgment, not %s" % a["kind"])
    if a["effort"] not in EFFORTS:
        raise Stop("--effort is one of %s, not %s" % (", ".join(EFFORTS), a["effort"]))
    try:
        a["vote"] = int(a["vote"])
    except ValueError:
        raise Stop("--vote needs a whole number, not %s" % a["vote"])
    if a["vote"] != 1 and not 2 <= a["vote"] <= VOTE_MAX:
        raise Stop("--vote takes 2 to %d drafts" % VOTE_MAX)
    if a["vote"] > 1 and not a["checkable"]:
        raise Stop("--vote needs --checkable: the answer must be one comparable thing "
                   "(a number, a yes/no, a short string)")
    try:
        a["timeout"] = float(a["timeout"])
        if a["timeout"] <= 0:
            raise ValueError
    except ValueError:
        raise Stop("--timeout needs a number of seconds above zero")
    if a["runner"] is not None and not a["runner"].strip():
        raise Stop("--runner is empty")
    return a


def main(argv=None):
    utf8_streams()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--help", "-h", "help") or argv[0] not in ("ask", "ledger"):
        if argv and argv[0] not in ("--help", "-h", "help"):
            print("STOP: unknown verb %s — ask or ledger (protector.py --help)" % argv[0])
            return 2
        print(USAGE)
        return 2
    state_dir = DEFAULT_STATE_DIR
    try:
        a = check_args(parse_args(argv))
        state_dir = a["state_dir"]
        return cmd_ledger(a) if a["verb"] == "ledger" else cmd_ask(a)
    except Stop as stop:
        print("STOP: %s" % stop)
        log_line(state_dir, "STOP: %s" % stop)
        return 2
    except KeyboardInterrupt:
        print("STOP: interrupted")
        return 2
    except Exception as exc:                                     # never a traceback
        import traceback
        print("STOP: protector failed: %s" % oneline(repr(exc), 160))
        log_line(state_dir, "failed: %s" % traceback.format_exc().replace("\n", " | "))
        return 2


if __name__ == "__main__":
    sys.exit(main())
