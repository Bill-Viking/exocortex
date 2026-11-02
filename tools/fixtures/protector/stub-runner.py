#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stub-runner.py — the gate's stand-in for a model.

It answers from the canned files in answers/ beside it, by the role marker on
the prompt's first line ([PROTECTOR:draft|check|revise|bare]) and by the mind
protector.py names in PROTECTOR_MODEL, for the scenario the gate names in
PROTECTOR_STUB. It prints the same JSON object `claude -p --output-format json`
prints, so protector.py reads the stub exactly as it reads the real CLI.

The checker's verdict is read off the draft it is shown, never off a counter:
a draft that carries the planted miss (1.71 a run) gets the failing grade, any
other draft the passing one — so a revise that fixes the number passes.

PROTECTOR_STUB_STATE (a folder) keeps one line per call in calls.jsonl, which
is how the gate counts calls and proves which minds were asked. Scenarios:

  pass · fail-once · fail-twice · malformed · vote-4of5 · vote-3of5
  sleep          sleeps 60 s after starting a grandchild that sleeps too
  not-logged-in  the CLI's own «Not logged in» answer, is_error true

Stdlib only, Python 3.9.
"""
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, "answers")
PLANTED = "1.71"                    # the planted miss: 2.49 - 0.78, a misread row

MODEL_IDS = {"sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5",
             "fable": "claude-fable-5-1", "codex": "gpt-6-astra",
             "haiku": "claude-haiku-4-5"}
# input, cache write, cache read, output — fixed per role so the gate can price them by hand
TOKENS = {"draft": (1200, 2400, 18000, 900), "check": (1500, 2600, 18000, 400),
          "revise": (1800, 2800, 18000, 900), "bare": (900, 2000, 15000, 300)}
CLI_COST = 0.0421                   # the stub CLI's own total_cost_usd, recorded as given


def role_of(prompt):
    first = prompt.lstrip().split("\n", 1)[0]
    if first.startswith("[PROTECTOR:") and "]" in first:
        return first[len("[PROTECTOR:"):first.index("]")]
    return "unknown"


def log_call(state, model, role, scenario):
    """This call's ordinal for (model, role), 1-based, and one line in calls.jsonl."""
    if not state:
        return 1
    os.makedirs(state, exist_ok=True)
    path = os.path.join(state, "calls.jsonl")
    seen = 0
    if os.path.isfile(path):
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("model") == model and row.get("role") == role:
                    seen += 1
    with io.open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"model": model, "role": role, "scenario": scenario,
                             "pid": os.getpid()}) + "\n")
    return seen + 1


def answer_file(scenario, role, model, n, prompt):
    starting = model in ("sonnet", "codex")      # the minds a run starts on carry the miss
    if role == "bare":
        return "bare-planted.md"
    if role == "check":
        if scenario == "malformed" and model == "opus":
            return "check-prose.md"
        return "check-fail.json" if PLANTED in prompt else "check-pass.md"
    if role == "draft":
        if scenario == "malformed" and model == "sonnet":
            return "draft-malformed.md"
        if scenario in ("fail-once", "fail-twice") and starting:
            return "draft-planted.md"
        if scenario == "vote-4of5" and model == "sonnet" and n == 3:
            return "draft-planted.md"
        if scenario == "vote-3of5" and model == "sonnet" and n in (2, 4):
            return "draft-planted.md"
        return "draft-right.md"
    if role == "revise":
        if scenario == "fail-twice" and starting:
            return "draft-planted.md"
        return "draft-right.md"
    return "check-prose.md"


def result_json(text, model, role, is_error=False):
    model_id = MODEL_IDS.get(model, "stub-unknown-1")
    t_in, t_cw, t_cr, t_out = TOKENS.get(role, (100, 0, 0, 100))
    return {"type": "result", "subtype": "error_during_execution" if is_error else "success",
            "is_error": is_error, "duration_ms": 5, "num_turns": 1, "result": text,
            "session_id": "stub", "total_cost_usd": 0 if is_error else CLI_COST,
            "usage": {"input_tokens": t_in, "cache_creation_input_tokens": t_cw,
                      "cache_read_input_tokens": t_cr, "output_tokens": t_out},
            "modelUsage": {} if is_error else {model_id: {
                "inputTokens": t_in, "outputTokens": t_out, "cacheReadInputTokens": t_cr,
                "cacheCreationInputTokens": t_cw, "costUSD": CLI_COST}}}


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    scenario = os.environ.get("PROTECTOR_STUB", "pass")
    model = os.environ.get("PROTECTOR_MODEL", "sonnet")
    state = os.environ.get("PROTECTOR_STUB_STATE", "")
    role = role_of(raw)
    n = log_call(state, model, role, scenario)
    if scenario == "sleep":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        if state:
            with io.open(os.path.join(state, "sleep-pids.json"), "w", encoding="utf-8") as fh:
                json.dump({"stub": os.getpid(), "grandchild": child.pid}, fh)
        time.sleep(60)
        return 0
    if scenario == "not-logged-in":
        print(json.dumps(result_json("Not logged in · Please run /login", model, role, True),
                         ensure_ascii=False))
        return 1
    name = answer_file(scenario, role, model, n, raw)
    with io.open(os.path.join(ANSWERS, name), encoding="utf-8") as fh:
        text = fh.read()
    sys.stdout.buffer.write(json.dumps(result_json(text, model, role),
                                       ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
