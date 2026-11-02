#!/usr/bin/env python3
"""tail-session.py — the last exchanges of a session transcript. No model, no tokens.

Reads Grok session summaries/directories, Claude Code transcripts (~/.claude/projects/<dir>/*.jsonl) and Codex rollouts
(~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl); the format is detected per line.
A handoff's "reader" step is this script, on either vendor and either OS.

usage:
  tail-session.py FILE [FILE ...] [--turns N] [--chars N]
      the last N user/assistant turns of each file (default 6 turns, 2500 chars each)
  tail-session.py --scan DIR [--days D] [--limit N]
      every transcript under DIR touched in the last D days (default 2), newest first:
      touched · size · project folder (cwd) · path · the first user line — so a session can be told
      apart by content and grouped by project without any app's list (the disk is the complete inventory)
"""
import argparse, json, os, sys, time
from pathlib import Path
from grok_sessions import iter_sessions as grok_sessions, iter_turns as grok_turns, metadata as grok_metadata

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

def _texts(content):
    if isinstance(content, str): return content
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get("type") in ("text", "input_text", "output_text") and b.get("text"):
            out.append(b["text"])
    return "\n".join(out)

def turns(path):
    """yield (timestamp, role, text) for the human-readable user/assistant turns, either format."""
    if Path(path).is_dir() or Path(path).name in ("summary.json", "chat_history.jsonl"):
        yield from grok_turns(path)
        return
    last = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try: o = json.loads(line)
            except Exception: continue
            t = o.get("type"); ts = o.get("timestamp", "")
            role = txt = None
            if t in ("user", "assistant"):                                   # Claude Code
                role, txt = t, _texts(o.get("message", {}).get("content"))
            elif t == "response_item":                                       # Codex rollout
                p = o.get("payload", {}); pt = p.get("type")
                if pt == "message" and p.get("role") in ("user", "assistant"):
                    role, txt = p["role"], _texts(p.get("content"))
                elif pt == "agent_message":
                    role, txt = "assistant", (_texts(p.get("content")) or p.get("text") or "")
            elif t == "event_msg" and o.get("payload", {}).get("type") == "item_completed":
                it = o["payload"].get("item", {})
                if it.get("type") == "UserMessage":
                    role, txt = "user", _texts(it.get("content"))
            if not role or not txt or not txt.strip(): continue
            s = txt.strip()
            if s.startswith("<") and s[:40].lower().startswith(("<app-context", "<environment_context", "<system-reminder", "<permission")):
                continue                                                     # harness context, not a person
            if last and last[1] == role and last[2] == s: continue           # duplicate record of one turn
            last = (ts, role, s); yield last

def tail(path, n, chars):
    allt = list(turns(path)); sel = allt[-n:] if n else allt
    try: size = os.path.getsize(path)
    except OSError: size = 0
    print(f"=== {path}\n    {len(allt)} turns · {size/1e6:.1f} MB · last {allt[-1][0] if allt else 'n/a'}")
    for ts, role, s in sel:
        body = s if len(s) <= chars else s[:chars] + f" …[+{len(s)-chars} chars]"
        print(f"\n--- [{ts}] {role.upper()}\n{body}")
    print()

def cwd_of(path):
    """the project folder a transcript was opened in: Codex session_meta.cwd, or Claude's per-line cwd."""
    if Path(path).is_dir() or Path(path).name in ("summary.json", "chat_history.jsonl"):
        return grok_metadata(path).get("cwd", "")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > 200: break
                try: o = json.loads(line)
                except Exception: continue
                if o.get("type") == "session_meta": return o.get("payload", {}).get("cwd", "") or ""
                if o.get("cwd"): return o["cwd"]
    except OSError: pass
    return ""

def scan(root, days, limit):
    cutoff = time.time() - days * 86400; rows = []
    for f in Path(root).rglob("*.jsonl"):
        if (f.parent / "summary.json").is_file() or f.name in ("events.jsonl", "updates.jsonl", "chat_history.jsonl", "prompt_history.jsonl"):
            continue  # All Grok sidecars, including future ones, belong to the summary below.
        try: m = f.stat().st_mtime
        except OSError: continue
        if m < cutoff: continue
        first = next((s for ts, role, s in turns(f) if role == "user"), "")
        rows.append((m, f.stat().st_size, str(f), first.replace("\n", " ")[:140], cwd_of(f)))
    for item in grok_sessions(root):
        if item.get("is_subagent") or not item.get("updated_epoch") or item["updated_epoch"] < cutoff:
            continue
        f = Path(item["path"])
        try:
            size = f.stat().st_size
        except OSError:
            continue
        first = item["title"] or next((s for ts, role, s in grok_turns(f) if role == "user"), "")
        rows.append((item["updated_epoch"], size, str(f), first.replace("\n", " ")[:140], item["cwd"]))
    rows.sort(reverse=True)
    for m, size, p, first, cwd in rows[:limit]:
        print(f"{time.strftime('%m-%d %H:%M', time.localtime(m))}  {size/1e6:5.1f} MB  {cwd or '?'}\n    {p}\n    first: {first}")
    if not rows: print(f"no transcripts under {root} touched in the last {days} day(s)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("files", nargs="*"); ap.add_argument("--turns", type=int, default=6); ap.add_argument("--chars", type=int, default=2500)
    ap.add_argument("--scan"); ap.add_argument("--days", type=float, default=2); ap.add_argument("--limit", type=int, default=40); ap.add_argument("--help", action="store_true")
    a = ap.parse_args()
    if a.help or (not a.files and not a.scan): print(__doc__); sys.exit(0)
    if a.scan: scan(os.path.expanduser(a.scan), a.days, a.limit)
    for f in a.files: tail(os.path.expanduser(f), a.turns, a.chars)
