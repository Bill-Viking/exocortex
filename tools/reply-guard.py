#!/usr/bin/env python3
"""reply-guard.py — Stop silently saves reply findings for the same session's next prompt.
--only launch,lost selects the installed checks. --state-dir DIR holds pending findings.
UserPromptSubmit carries one REPLY GUARD context line and clears it. Every error allows.
--scan FILE is read-only; --self-test verifies checks and the delayed context road.
"""
import json
import hook_say
from pathlib import Path
import re
import sys

VERSION = "0.2.0"
WORDS_MAX = 220
FENCES_MAX = 2
FENCE = re.compile(r"```[^\n]*\n.*?```", re.S)
POINTER = re.compile(
    r"\b(above|below|earlier in this (?:turn|message)|in my (?:last|previous) message)\b", re.I)
BARE_LAUNCH = re.compile(r"""claude\s+--model\s+["']?(sonnet|opus)["']?(?!\[1m\])(?=\s|$|["'])""", re.I)
NOT_HUMAN = ("The user hasn't heard from you", "<system-reminder>", "[Request interrupted")


def _norm(text):
    return " ".join(text.split())


def turns(path):
    """The turns of a transcript: {"human": text, "texts": [assistant text blocks, in order]}.
    A turn starts at a real human message (never a tool result, never a harness reminder)."""
    out = []
    cur = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            kind = e.get("type")
            content = (e.get("message") or {}).get("content")
            if kind == "user":
                text = ""
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    blocks = [b for b in content if isinstance(b, dict)]
                    if any(b.get("type") == "tool_result" for b in blocks):
                        continue
                    text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                if not text.strip() or text.lstrip().startswith(NOT_HUMAN):
                    continue
                if cur:
                    out.append(cur)
                cur = {"human": text, "texts": []}
            elif kind == "assistant" and cur is not None and isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                        cur["texts"].append(b["text"])
    if cur:
        out.append(cur)
    return out


def check(texts, only=None):
    """The reasons to block, for a turn's assistant text blocks in order; [] = allow.
    only: a set of check names that may block ({"launch"}, {"launch", "lost"}); None = all."""
    if not texts:
        return []
    final = texts[-1]
    earlier = texts[:-1]
    reasons = []
    on = (lambda name: only is None or name in only)
    for m in BARE_LAUNCH.finditer(final):
        reasons.append("the launch line says 'claude --model %s' without the long-context suffix - "
                       "write --model \"%s[1m]\" (quoted) on every launch line, and say Sonnet 1M / "
                       "Opus 1M on the SET line; a standard window compacts mid-landing and loses "
                       "the record (High-context launch rule, 2026-10-17)" % (m.group(1), m.group(1)))
        break
    final_fences = [_norm(f) for f in FENCE.findall(final)]
    lost = [f for e in earlier for f in FENCE.findall(e) if _norm(f) not in final_fences]
    if lost and on("lost"):
        first = _norm(lost[0])[:70]
        reasons.append("a paste you wrote BEFORE a tool call is not in your final message - the app "
                       "hides that text and the person never saw it; put the whole thing (its mark, "
                       "the block, the done-when line) in this final message: " + first + "...")
    if only is not None and not (only - {"launch", "lost"}):
        return reasons
    prose = FENCE.sub(" ", final)
    m = POINTER.search(prose)
    if m:
        reasons.append("the final message says '%s' - never point outside this message; put the "
                       "thing here, whole" % m.group(0))
    words = len(re.findall(r"\S+", prose))
    if words > WORDS_MAX:
        reasons.append("the final message's prose is %d words (limit %d) - the picture, the one "
                       "move, the one paste; the rest goes to STATUS" % (words, WORDS_MAX))
    if len(final_fences) > FENCES_MAX:
        reasons.append("%d fenced blocks in the final message (limit %d) - one move per reply"
                       % (len(final_fences), FENCES_MAX))
    return reasons


def scan(path):
    ts = turns(path)
    blocked = 0
    for i, t in enumerate(ts, 1):
        r = check(t["texts"])
        if r:
            blocked += 1
            print("turn %d - BLOCK - after: %s" % (i, _norm(t["human"])[:70]))
            for x in r:
                print("    " + x[:160])
    print("%d turns, %d would have been blocked" % (len(ts), blocked))
    return 0


def self_test():
    ok = True
    passed = 0
    cases = [
        (["here is the paste:\n```text\nread it\n```\n", "done, see above"],
         ["not in your final message", "says 'above'"]),
        (["fine, one move:\n```text\nread it\n```\nthat is all"], []),
        (["x " * 300], ["words"]),
        (["```a\n1\n```\n```b\n2\n```\n```c\n3\n```"], ["3 fenced blocks"]),
        ([], []),
        (['```powershell\ncd C:\\x; claude --model sonnet "go"\n```'], ["long-context suffix"]),
        (['```powershell\ncd C:\\x; claude --model "sonnet[1m]" "go"\n```'], []),
        (['cd ~/x && claude --model fable "go"'], []),
    ]
    for texts, want in cases:
        got = check(texts)
        good = len(got) == len(want) and all(any(w in g for g in got) for w in want)
        ok = ok and good
        passed += int(good)
        print(("OK   " if good else "FAIL ") + repr(want))
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory(prefix="bq493-guard-") as directory:
        path = Path(directory) / "turn.jsonl"
        for label, texts in (("launch", ['claude --model sonnet "go"']),
                             ("lost", ['```text\nwhole paste\n```', 'ready'])):
            rows = [{"type": "user", "message": {"content": "go"}}]
            rows += [{"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}} for t in texts]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            event = {"hook_event_name": "Stop", "session_id": "guard-self-test", "transcript_path": str(path)}
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = hook(event, directory, {"launch", "lost"})
            saved_path = hook_say.finding_path(directory, event['session_id'], 'guard')
            saved = json.loads(saved_path.read_text()) if saved_path.is_file() else []
            expected = check(texts, {"launch", "lost"})
            good = code == 0 and out.getvalue() == "" and saved == expected and bool(saved)
            with contextlib.redirect_stdout(out):
                code = hook(dict(event, hook_event_name="UserPromptSubmit"), directory)
            context = json.loads(out.getvalue() or '{}').get('hookSpecificOutput', {}).get('additionalContext', '')
            good = good and code == 0 and context == ("REPLY GUARD · last reply · " + " · ".join(expected))[:499] and not saved_path.exists()
            ok = ok and good
            passed += int(good)
            print(("OK   " if good else "FAIL ") + label + " saved / next prompt / cleared")
    print("reply-guard self-test: %d/10" % passed)
    return 0 if ok else 1


def hook(data, state_dir, only=None):
    if not isinstance(data, dict) or "agent_id" in data:
        return 0
    name = data.get("hook_event_name") or "Stop"
    sid = data.get("session_id")
    if name == "UserPromptSubmit":
        reasons = hook_say.recall(state_dir, sid, "guard")
        line = ("REPLY GUARD · last reply · " + " · ".join(reasons))[:499] if reasons else ""
        return hook_say.emit(name, [line] if line else [])
    if name != "Stop" or data.get("stop_hook_active"):
        return 0
    path = data.get("transcript_path")
    if not path:
        return 0
    ts = turns(path)
    if ts:
        reasons = check(ts[-1]["texts"], only=only)
        hook_say.remember(state_dir, sid, "guard", reasons)
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "--scan" and len(argv) >= 3:
        return scan(argv[2])
    if len(argv) >= 2 and argv[1] == "--self-test":
        return self_test()
    only = None
    if "--only" in argv and argv.index("--only") + 1 < len(argv):
        only = set(w.strip() for w in argv[argv.index("--only") + 1].split(",") if w.strip())
    try:
        data = json.loads(sys.stdin.read(1 << 20) or "{}")
        state_dir = str(Path(__file__).resolve().parent.parent / ".reply-router")
        if "--state-dir" in argv:
            state_dir = argv[argv.index("--state-dir") + 1]
        return hook(data, state_dir, only)
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
