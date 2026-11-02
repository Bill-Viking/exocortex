"""Bounded, read-only helpers for local Grok session records.

Only recognized Grok summary, event, and transcript files are read. Transcript
redaction covers a few obvious credential shapes; arbitrary private text must
still be treated as private.
"""

from __future__ import annotations

import datetime as _datetime
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Union
from urllib.parse import unquote

_SUMMARY_LIMIT = 512 * 1024
_EVENT_WINDOW = 64 * 1024
_TRANSCRIPT_LINE_LIMIT = 2 * 1024 * 1024
_TEXT_ROLES = frozenset(("user", "assistant"))
_TURN_EVENTS = frozenset(("turn_started", "turn_ended"))
PathLike = Union[str, os.PathLike]


def _as_path(value: PathLike) -> Optional[Path]:
    try:
        return Path(os.path.expanduser(os.fspath(value)))
    except (TypeError, ValueError, OSError):
        return None


def _summary_path(value: PathLike) -> Optional[Path]:
    path = _as_path(value)
    if path is None:
        return None
    try:
        if path.is_dir():
            return path / "summary.json"
    except OSError:
        return None
    if path.name == "summary.json":
        return path
    if path.name == "chat_history.jsonl":
        return path.with_name("summary.json")
    return None


def _history_path(value: Any) -> Optional[Path]:
    if isinstance(value, dict):
        candidate = value.get("transcript")
        if not isinstance(candidate, (str, os.PathLike)):
            return None
        path = _as_path(candidate)
        return path if path is not None and path.name == "chat_history.jsonl" else None
    path = _as_path(value)
    if path is None:
        return None
    try:
        if path.is_dir():
            return path / "chat_history.jsonl"
    except OSError:
        return None
    if path.name == "chat_history.jsonl":
        return path
    if path.name == "summary.json":
        return path.with_name("chat_history.jsonl")
    return None


def _read_json_object(path: Path, limit: int) -> Optional[Dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except (OSError, ValueError):
        return None
    if len(data) > limit:
        return None
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _canonical_parts(summary: Path) -> Optional[Tuple[str, str]]:
    session_dir = summary.parent
    encoded_dir = session_dir.parent
    sessions_dir = encoded_dir.parent
    if summary.name != "summary.json" or sessions_dir.name != "sessions":
        return None
    try:
        session_id = str(uuid.UUID(session_dir.name))
    except (ValueError, AttributeError):
        return None
    try:
        cwd = unquote(encoded_dir.name, encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return None
    return session_id, cwd


def _iso_epoch(value: Any) -> Optional[float]:
    """Parse ISO-8601, including nanosecond fractions and a trailing Z."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    match = re.match(r"^(.*?\.)(\d+)(Z|[+-]\d\d:\d\d)?$", text)
    if match:
        text = match.group(1) + match.group(2)[:6] + (match.group(3) or "")
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = _datetime.datetime.fromisoformat(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_datetime.timezone.utc)
    try:
        return parsed.timestamp()
    except (OSError, OverflowError, ValueError):
        return None


def _bounded_head(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(limit)
            return data[3:] if data.startswith(b"\xef\xbb\xbf") else data
    except OSError:
        return b""


def _bounded_tail(path: Path, limit: int) -> bytes:
    try:
        with path.open("rb") as handle:
            size = os.fstat(handle.fileno()).st_size
            offset = max(0, size - limit)
            handle.seek(offset)
            data = handle.read(limit)
    except (OSError, ValueError):
        return b""
    if offset and data:
        newline = data.find(b"\n")
        data = b"" if newline < 0 else data[newline + 1 :]
    elif data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data


def _event_rows(data: bytes) -> Iterator[Dict[str, Any]]:
    for raw_line in data.splitlines():
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict):
            yield value


def _event_state(events_path: Path, initial_relationship: Any) -> Tuple[Optional[str], str]:
    relationship = (
        initial_relationship
        if isinstance(initial_relationship, str) and initial_relationship
        else None
    )
    last_turn_event = None
    for row in _event_rows(_bounded_tail(events_path, _EVENT_WINDOW)):
        event_type = row.get("type")
        if event_type in _TURN_EVENTS:
            last_turn_event = event_type
        candidate = row.get("session_relationship")
        if isinstance(candidate, str) and candidate:
            relationship = candidate
    if relationship is None:
        for row in _event_rows(_bounded_head(events_path, _EVENT_WINDOW)):
            candidate = row.get("session_relationship")
            if isinstance(candidate, str) and candidate:
                relationship = candidate
                break
    if last_turn_event == "turn_started":
        status = "busy"
    elif last_turn_event == "turn_ended":
        status = "idle"
    else:
        status = "unknown"
    return relationship, status


def metadata(path: PathLike) -> Dict[str, Any]:
    """Return bounded session metadata, or an empty dict for bad inputs.

    Path may be summary.json, its session directory, or chat_history.jsonl.
    Busy/idle reflects only the last bounded event record, not a live process.
    """
    summary_path = _summary_path(path)
    if summary_path is None:
        return {}
    record = _read_json_object(summary_path, _SUMMARY_LIMIT)
    if record is None:
        return {}
    info = record.get("info")
    if not isinstance(info, dict):
        info = {}
    canonical = _canonical_parts(summary_path)
    session_id = info.get("id")
    if not isinstance(session_id, str) or not session_id.strip():
        session_id = canonical[0] if canonical is not None else None
    else:
        session_id = session_id.strip()
    cwd = info.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        cwd = canonical[1] if canonical is not None else None
    if session_id is None or cwd is None:
        return {}
    created_at = record.get("created_at")
    updated_at = record.get("updated_at") or record.get("last_active_at")
    if not isinstance(created_at, str):
        created_at = None
    if not isinstance(updated_at, str):
        updated_at = None
    relationship, status = _event_state(
        summary_path.with_name("events.jsonl"), record.get("session_relationship")
    )
    normalized_relationship = relationship.strip().lower() if relationship else ""
    is_subagent = normalized_relationship in {"subagent", "sub_agent", "sub-agent"}
    title = record.get("generated_title")
    if not isinstance(title, str):
        title = ""
    model = record.get("current_model_id")
    if not isinstance(model, str):
        model = ""
    # The session's own reasoning dial, as Grok Build records it beside the model
    # id (verified on this machine's ten summaries: a top-level
    # `reasoning_effort`, values `low` / `high`). `info.reasoning_effort` is read
    # as a second place only, for a record that carries it there. A summary that
    # names no dial leaves the key absent — never a default, never a guess.
    effort = record.get("reasoning_effort")
    if not isinstance(effort, str) or not effort.strip():
        effort = info.get("reasoning_effort")
    effort = effort.strip() if isinstance(effort, str) else ""
    parent = record.get("parent_session_id")
    if not isinstance(parent, str) or not parent:
        parent = None
    out = {
        "id": session_id,
        "cwd": cwd,
        "title": title,
        "model": model,
        "created_at": created_at,
        "updated_at": updated_at,
        "started_epoch": _iso_epoch(created_at),
        "updated_epoch": _iso_epoch(updated_at),
        "parent_session_id": parent,
        "relationship": relationship,
        "is_subagent": is_subagent,
        "status": status,
        "path": str(summary_path),
        "transcript": str(summary_path.with_name("chat_history.jsonl")),
    }
    if effort:
        out["effort"] = effort
    return out


def iter_sessions(root: PathLike) -> Iterator[Dict[str, Any]]:
    """Yield unique sessions below a .grok or sessions directory."""
    root_path = _as_path(root)
    if root_path is None:
        return
    sessions_path = root_path if root_path.name == "sessions" else root_path / "sessions"
    seen = set()
    try:
        cwd_entries = list(os.scandir(str(sessions_path)))
    except OSError:
        return
    for cwd_entry in cwd_entries:
        try:
            if not cwd_entry.is_dir(follow_symlinks=False):
                continue
            session_entries = list(os.scandir(cwd_entry.path))
        except OSError:
            continue
        for session_entry in session_entries:
            try:
                if not session_entry.is_dir(follow_symlinks=False):
                    continue
                uuid.UUID(session_entry.name)
            except (ValueError, AttributeError):
                continue
            except OSError:
                continue
            item = metadata(Path(session_entry.path) / "summary.json")
            session_id = item.get("id") if item else None
            if not session_id or session_id in seen:
                continue
            seen.add(session_id)
            yield item


_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_PREFIX_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])(?:xai|sk)-[A-Za-z0-9_-]{4,}")
_JSON_SECRET_RE = re.compile(
    r"""(?ix)(["'](?:api_key|access_token|refresh_token|password)["']\s*:\s*)
        (["'])(?:\\.|(?!\2).)*\2"""
)


def _redact(text: str) -> str:
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _PREFIX_TOKEN_RE.sub("[REDACTED]", text)
    return _JSON_SECRET_RE.sub(
        lambda match: match.group(1) + match.group(2) + "[REDACTED]" + match.group(2),
        text,
    )


def _snapshot_lines(path: Path) -> Iterator[bytes]:
    """Yield bounded lines from the size visible at open time.

    Oversized lines are discarded in bounded chunks. Appends after open wait
    for the next scan.
    """
    try:
        handle = path.open("rb")
    except OSError:
        return
    with handle:
        try:
            remaining = os.fstat(handle.fileno()).st_size
        except OSError:
            return
        at_file_head = True
        while remaining > 0:
            allowance = min(_TRANSCRIPT_LINE_LIMIT + 1, remaining)
            try:
                raw = handle.readline(allowance)
            except OSError:
                return
            if not raw:
                return
            remaining -= len(raw)
            if at_file_head:
                at_file_head = False
                if raw.startswith(b"\xef\xbb\xbf"):
                    raw = raw[3:]
            oversized = len(raw) > _TRANSCRIPT_LINE_LIMIT or (
                not raw.endswith(b"\n") and remaining > 0
            )
            if oversized:
                while remaining > 0 and not raw.endswith(b"\n"):
                    try:
                        raw = handle.readline(min(_TRANSCRIPT_LINE_LIMIT + 1, remaining))
                    except OSError:
                        return
                    if not raw:
                        return
                    remaining -= len(raw)
                continue
            yield raw


def _message_text(row: Dict[str, Any]) -> Optional[str]:
    content = row.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    parts = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts) if parts else None


def iter_turns(path: Any, max_chars: int = 12000) -> Iterator[Tuple[Any, str, str]]:
    """Yield (timestamp, role, text) for bounded user/assistant messages.

    Tool, system, and reasoning rows are skipped. Credential redaction covers
    common Bearer, xai-/sk-, and named JSON secret forms only; callers must
    still treat arbitrary conversation text as private.
    """
    history_path = _history_path(path)
    if history_path is None:
        return
    try:
        char_limit = int(max_chars)
    except (TypeError, ValueError, OverflowError):
        return
    if char_limit <= 0:
        return
    for raw_line in _snapshot_lines(history_path):
        try:
            row = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict):
            continue
        role = row.get("type")
        if role not in _TEXT_ROLES:
            continue
        text = _message_text(row)
        if text is None:
            continue
        timestamp = row.get("timestamp", row.get("ts"))
        if not isinstance(timestamp, (str, int, float)):
            timestamp = None
        yield timestamp, role, _redact(text)[:char_limit]
