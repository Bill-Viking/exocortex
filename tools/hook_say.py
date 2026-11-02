#!/usr/bin/env python3
"""usage-settings.json: hooks_refuse = unattended-only (default) | never disables every prompt refusal.

Only the app's scheduled-task frame proves an unattended run. Stop is always silent.
Stdlib only. All output errors fail open.
"""
import hashlib
import json
import os
from pathlib import Path
import sys


def settings_at(hub=None):
    try:
        path = Path(hub) if hub else Path(__file__).resolve().parent.parent
        with (path / "usage-settings.json").open(encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def attendance(event, human_text=""):
    prompt = str(human_text or (event or {}).get("prompt") or "").lstrip()
    if prompt.startswith("<scheduled-task"):
        return "scheduled"
    if prompt.startswith(("<task-notification", "<machine>", "<session-message",
                          "<cross-session-message", "<teammate-message")):
        return "machine frame"
    return "person-typed"


def may_refuse(facts, settings):
    try:
        switch = (settings or {}).get("hooks_refuse", "unattended-only")
        return switch != "never" and (facts or {}).get("attendance") == "scheduled"
    except Exception:
        return False


def emit(event_name, lines, refusal=None, facts=None, settings=None, hard=False):
    try:
        cfg = settings if settings is not None else settings_at()
        allowed = may_refuse(facts, cfg)  # owner's switch is read before event/output logic
        if event_name == "Stop":
            return 0
        if refusal and allowed:
            if hard:
                sys.stderr.write(str(refusal) + "\n")
                sys.stderr.flush()
                return 2
            output = {"decision": "block", "reason": str(refusal)}
        else:
            context = list(lines or [])
            if refusal:
                context.append(" ".join(str(refusal).split()))
            if not context:
                return 0
            output = {"hookSpecificOutput": {"hookEventName": event_name,
                      "additionalContext": "\n".join(context)}}
        sys.stdout.write(json.dumps(output, ensure_ascii=False))
        sys.stdout.flush()
    except Exception:
        pass
    return 0


# ASSUMES: session_id identifies a window; missing identity never shares findings.
# Opposite: the no-id and hostile-id cases in test_hook_say.py.
def finding_path(state_dir, session, owner):
    if not isinstance(session, str) or not session.strip():
        return None
    key = hashlib.sha256(session.encode("utf-8")).hexdigest()
    return Path(state_dir) / (owner + "-" + key + ".json")


def remember(state_dir, session, owner, reasons):
    try:
        path = finding_path(state_dir, session, owner)
        if path is None:
            return
        if not reasons:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(".%d.tmp" % os.getpid())
        try:
            pending.write_text(json.dumps(list(reasons), ensure_ascii=False), encoding="utf-8")
            os.replace(pending, path)
        finally:
            pending.unlink(missing_ok=True)
    except Exception:
        pass


def recall(state_dir, session, owner):
    try:
        path = finding_path(state_dir, session, owner)
        if path is None or path.stat().st_size > (1 << 20):
            return []
        reasons = json.loads(path.read_text(encoding="utf-8"))
        path.unlink()
        return [" ".join(x.split()) for x in reasons if isinstance(x, str)] if isinstance(reasons, list) else []
    except Exception:
        return []
