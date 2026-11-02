"""Read exact-thread Codex dial evidence. Python 3.9+, stdlib, read-only.

A bounded header verifies identity; a 2 MiB tail grows once to 4 MiB only
when it contains no task_started. Locations in a truncated tail are byte
offsets, never invented absolute line numbers. No subprocess or network.
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

TAIL_BYTES = 2 * 1024 * 1024
HEADER_BYTES = 64 * 1024
FRESH_SECONDS = 30 * 60
SCHEMA_VERSION = "unknown — fill at install"
_UUID = re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
_LIFECYCLE = {"task_started", "task_complete", "turn_aborted"}
_EVENT_TYPES = _LIFECYCLE | {"agent_message", "agent_reasoning", "user_message",
                              "token_count", "context_compacted"}
_RECORD_TYPES = {"session_meta", "event_msg", "turn_context", "response_item", "compacted"}
_UNKNOWN_EVENT_TYPES = set()   # event types seen but not known; reported, never fatal
_UNKNOWN_RECORD_TYPES = set()  # record types seen but not known; reported, never fatal


def _identity(value):
    if not isinstance(value, str) or not _UUID.fullmatch(value):
        raise ValueError("invalid_thread_id")
    return str(uuid.UUID(value))


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _reject_non_json_constant(_value):
    raise ValueError("non_json_constant")


def _timestamp(value):
    try:
        stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp.timestamp() if stamp.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _decode(line):
    if not line.endswith(b"\n"):
        return None, "incomplete_trailing_line", None
    try:
        record = json.loads(line.decode("utf-8"), parse_constant=_reject_non_json_constant)
    except UnicodeDecodeError:
        return None, "invalid_utf8", None
    except (ValueError, RecursionError):
        return None, "malformed_json", None
    if not isinstance(record, dict):
        return None, "non_object_record", "record (expected object)"
    if not isinstance(record.get("payload"), dict):
        return None, "non_object_payload", "payload (expected object)"
    kind = record.get("type")
    if not isinstance(kind, str):
        return None, "unrecognized_record_type", "record.type: " + str(kind)
    if kind not in _RECORD_TYPES:
        # A record type this reader does not know (e.g. world_state) is ignored and
        # counted, never fatal — only the records the reading needs must parse.
        _UNKNOWN_RECORD_TYPES.add(kind)
        return record, None, None
    if kind == "event_msg" and not _nonempty(record["payload"].get("type")):
        return None, "missing_event_type", "event_msg.payload.type"
    if kind == "event_msg" and record["payload"]["type"] not in _EVENT_TYPES:
        # An event type this reader does not know (Codex adds them between releases,
        # e.g. item_completed) is NOT a schema failure: it is ignored and counted, so a
        # live rollout keeps reading. Only the records the reading needs must parse.
        _UNKNOWN_EVENT_TYPES.add(record["payload"]["type"])
        return record, None, None
    return record, None, None


def _context(record, location):
    payload = record["payload"]
    for key, reason in (("turn_id", "missing_context_turn_id"),
                        ("model", "missing_or_invalid_model"),
                        ("effort", "missing_or_invalid_effort")):
        if not _nonempty(payload.get(key)):
            return None, reason, "turn_context.payload." + key
    if _timestamp(record.get("timestamp")) is None:
        return None, "invalid_context_timestamp", "turn_context.timestamp"
    collaboration = payload.get("collaboration_mode")
    if collaboration is not None:
        if not isinstance(collaboration, dict):
            return None, "invalid_collaboration_mode", "turn_context.payload.collaboration_mode"
        settings = collaboration.get("settings")
        if settings is not None:
            if not isinstance(settings, dict):
                return None, "invalid_collaboration_settings", "collaboration_mode.settings"
            supporting = settings.get("reasoning_effort")
            if supporting is not None and supporting != payload["effort"]:
                return None, "effort_fields_disagree", None
    return {"turn_id": payload["turn_id"], "model": payload["model"],
            "effort": payload["effort"], "context_at": record["timestamp"],
            "source": location}, None, None


def _rows(raw, offset):
    """Discard only the partial first line; all subsequent damage is retained."""
    absolute_lines = offset == 0
    if offset:
        end = raw.find(b"\n")
        if end == -1:
            return []
        offset += end + 1
        raw = raw[end + 1:]
    rows = []
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        record, error, schema = _decode(line)
        location = {"context_byte": offset}
        if absolute_lines:
            location = {"context_line": number}
        rows.append((record, error, schema, location))
        offset += len(line)
    return rows


def _start(row):
    record = row[0]
    return (record is not None and record["type"] == "event_msg"
            and record["payload"].get("type") == "task_started")


def read_dial(thread_id=None, codex_home=None, transcript=None, environ=None, now=None):
    """Return JSON-ready evidence, including elapsed parse_ms on every path.

    Explicit IDs override selection, but conflicting environment IDs fail closed.
    now is an injectable epoch clock for fixtures. Old corruption is counted only
    within the bounded window, not claimed to be a scan of the entire history.
    """
    began = time.perf_counter()
    clock = time.time() if now is None else now
    env = os.environ if environ is None else environ
    result = {"state": "unknown", "thread_id": None, "age_seconds": None,
              "observed_at": datetime.datetime.fromtimestamp(
                  clock, datetime.timezone.utc).isoformat()}

    def finish():
        result["parse_ms"] = round((time.perf_counter() - began) * 1000, 3)
        if _UNKNOWN_EVENT_TYPES or _UNKNOWN_RECORD_TYPES:
            result["ignored_types"] = sorted(_UNKNOWN_RECORD_TYPES | {"event_msg:" + t for t in _UNKNOWN_EVENT_TYPES})
        return result

    def fail(reason, schema=None):
        result["state"] = "unknown"
        result["reason"] = reason
        if schema:
            result["schema"] = schema
        return finish()

    try:
        identities = [_identity(env[name]) for name in
                      ("CODEX_THREAD_ID", "CODEX_SESSION_ID") if env.get(name)]
        if len(set(identities)) > 1:
            return fail("conflicting_environment_identities")
        selected = _identity(thread_id) if thread_id is not None else (
            identities[0] if identities else None)
    except (ValueError, TypeError, AttributeError):
        return fail("invalid_thread_id")
    if selected is None:
        return fail("missing_thread_id")
    result["thread_id"] = selected

    try:
        if transcript is not None:
            path = Path(transcript)
        else:
            home = Path(codex_home if codex_home is not None else
                        env.get("CODEX_HOME") or Path.home() / ".codex")
            candidates = (home / "sessions").rglob("rollout-*-" + selected + ".jsonl")
            path = next(candidates, None)
            if path is None:
                return fail("transcript_not_found")
            if next(candidates, None) is not None:
                return fail("ambiguous_transcripts")
        result["source"] = {"path": str(path)}
        with path.open("rb") as handle:
            stat = os.fstat(handle.fileno())
            result["age_seconds"] = max(0, clock - stat.st_mtime)
            header = handle.readline(HEADER_BYTES + 1)
            if len(header) > HEADER_BYTES:
                return fail("session_header_exceeds_bound", "session_meta header")
            metadata, error, schema = _decode(header)
            if error:
                return fail(error, schema)
            if metadata["type"] != "session_meta":
                return fail("missing_session_identity", "session_meta")
            try:
                meta_id = _identity(metadata["payload"].get("id"))
            except (ValueError, TypeError, AttributeError):
                return fail("missing_or_invalid_session_identity", "session_meta.payload.id")
            if meta_id != selected:
                return fail("session_identity_mismatch")
            offset = max(0, stat.st_size - TAIL_BYTES)
            handle.seek(offset)
            raw = handle.read(stat.st_size - offset)
            rows = _rows(raw, offset)
            if not any(_start(row) for row in rows) and offset:
                expanded = max(0, offset - TAIL_BYTES)
                handle.seek(expanded)
                raw = handle.read(offset - expanded) + raw
                offset = expanded
                rows = _rows(raw, offset)
            result["tail_bytes"] = len(raw)
            result["tail_start_byte"] = offset
    except (OSError, ValueError, TypeError):
        return fail("transcript_unreadable")

    starts = [index for index, row in enumerate(rows) if _start(row)]
    if not starts:
        # Canary beats a generic missing-lifecycle error when the tail changed shape.
        for _, error, schema, _ in rows:
            if error:
                return fail(error, schema)
        return fail("task_start_outside_tail" if offset else "no_task_lifecycle",
                    None if offset else "event_msg.payload.type: task_started")
    first = starts[-1]
    ignored = sum(bool(row[1]) for row in rows[:first])
    if ignored:
        result["note"] = {"ignored_history_errors": ignored, "scope": "bounded tail before latest task_started"}
    # Preserve the overlap guard when an intact earlier lifecycle is visible.
    prior = [(i, r) for i, (r, error, _, _) in enumerate(rows[:first]) if not error and
             r["type"] == "event_msg" and r["payload"].get("type") in _LIFECYCLE]
    if prior and prior[-1][1]["payload"]["type"] == "task_started":
        # A damaged old completion cannot poison a later intact turn. An
        # uninterrupted, visible double start still fails the lifecycle guard.
        if not any(row[1] for row in rows[prior[-1][0] + 1:first]):
            return fail("lifecycle_start_while_active")

    active = None
    started_at = None
    ended_index = None
    latest_context = None
    context_index = None
    last_event = None
    for index in range(first, len(rows)):
        record, error, schema, location = rows[index]
        if error:
            return fail(error, schema)
        payload = record["payload"]
        if record["type"] == "event_msg" and payload.get("type") in _LIFECYCLE:
            event, turn = payload["type"], payload.get("turn_id")
            if not _nonempty(turn):
                return fail("missing_lifecycle_turn_id", "event_msg.payload.turn_id")
            if event == "task_started":
                active = turn
                started_at = _timestamp(record.get("timestamp"))
                if started_at is None:
                    return fail("invalid_task_timestamp", "task_started.timestamp")
                result["task_started_at"] = record["timestamp"]
                result["age_seconds"] = max(result["age_seconds"], clock - started_at, 0)
            else:
                if active != turn:
                    return fail("lifecycle_end_mismatch")
                active = None
                ended_index = index
            last_event = (event, turn)
        elif record["type"] == "turn_context":
            latest_context, error, schema = _context(record, dict(location, path=str(path)))
            if error:
                return fail(error, schema)
            context_index = index
        elif record["type"] == "session_meta":
            return fail("unexpected_session_meta", "session_meta inside turn")
    result["turn_id"] = last_event[1]
    if latest_context is None:
        old = [r for r, error, _, _ in rows[:first] if not error and r["type"] == "turn_context"]
        if old:
            return fail("context_precedes_task_start" if old[-1]["payload"].get("turn_id") == active
                        else "active_context_turn_mismatch")
        return fail("no_turn_context", "turn_context")
    if latest_context["turn_id"] != last_event[1]:
        return fail("active_context_turn_mismatch" if active else "ended_context_turn_mismatch")
    if not active and context_index >= ended_index:
        return fail("context_outside_completed_task")
    result["age_seconds"] = max(result["age_seconds"], clock - _timestamp(latest_context["context_at"]), 0)
    if active and clock - started_at <= FRESH_SECONDS and clock - stat.st_mtime <= FRESH_SECONDS:
        result.update(latest_context)
        result.update(state="current", reason="active_turn_context")
    else:
        result.update(state="last_observed", last_observed=latest_context,
                      reason="stale_active_turn" if active else last_event[0])
    return finish()


def safe_text(value):
    """One terminal-safe line, even if a private schema field contains controls."""
    return json.dumps(str(value), ensure_ascii=True)[1:-1]


def age_text(reading):
    age = reading.get("age_seconds")
    if age is None:
        return "age unknown"
    prefix = "read" if reading["state"] == "current" else "last seen"
    return "{} {} min ago".format(prefix, int(max(0, age) // 60))


def format_reading(reading):
    age = age_text(reading)
    if reading["state"] == "current":
        return "DIAL NOW — EFFORT {} · MODEL {} (Codex active turn) · {}".format(
            safe_text(reading["effort"].upper()), safe_text(reading["model"]), age)
    if reading["state"] == "last_observed":
        seen = reading["last_observed"]
        return "LAST SEEN {} · {} · {}".format(
            safe_text(seen["model"]), safe_text(seen["effort"].upper()), age)
    reason = ("unknown (schema: {})".format(safe_text(reading["schema"]))
              if reading.get("schema") else safe_text(reading["reason"]))
    return "UNKNOWN — {} · {}".format(reason, age)


def schema_version():
    try:
        with Path(__file__).with_name("SCHEMA-VERSION.txt").open(encoding="utf-8") as handle:
            version = handle.readline(256).strip()
        return version or SCHEMA_VERSION
    except OSError:
        return SCHEMA_VERSION


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread-id")
    parser.add_argument("--codex-home")
    parser.add_argument("--transcript")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--schema-check", action="store_true")
    args = parser.parse_args(argv)
    reading = read_dial(args.thread_id, args.codex_home, args.transcript)
    if args.json:
        print(json.dumps(reading, ensure_ascii=True, sort_keys=True))
    elif args.schema_check and reading["state"] != "unknown":
        print("schema OK on {} · {}".format(schema_version().replace("\r", "\\r").replace("\x1b", "\\x1b"), age_text(reading)))
        return 0
    else:
        print(format_reading(reading))
    return 0 if reading["state"] == "current" else 2


if __name__ == "__main__":
    sys.exit(main())
