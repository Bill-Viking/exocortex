"""Disposable transcript tests; never read the user's production Codex data."""

import contextlib
import datetime
import importlib.util
import types
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import codex_dial as dial


THREAD = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
STAMP = "2026-10-24T12:00:00Z"


def record(kind, payload):
    return {"timestamp": STAMP, "type": kind, "payload": payload}


def meta(identity=THREAD):
    return record("session_meta", {"id": identity})


def event(kind="task_started", turn="turn-1"):
    return record("event_msg", {"type": kind, "turn_id": turn})


def context(turn="turn-1", model="gpt-6-astra", effort="xhigh"):
    return record("turn_context", {"turn_id": turn, "model": model, "effort": effort})


class DialTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.clock = dial._timestamp(STAMP) + 180
        clock_patch = mock.patch.object(dial.time, "time", return_value=self.clock)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.path = self.home / "sessions/2026/10/24" / ("rollout-2026-10-24-" + THREAD + ".jsonl")
        self.path.parent.mkdir(parents=True)
        self.env = {"CODEX_THREAD_ID": THREAD}

    def write(self, rows=None, path=None):
        target = path or self.path
        target.write_text("".join(json.dumps(row) + "\n" for row in (
            rows if rows is not None else [meta(), event(), context()])), encoding="utf-8")
        os.utime(target, (self.clock, self.clock))
        return target

    def read(self, **kwargs):
        return dial.read_dial(codex_home=self.home, environ=self.env, **kwargs)

    def assert_unknown(self, reading, reason=None):
        self.assertEqual(reading["state"], "unknown", reading)
        self.assertNotIn("effort", reading)
        self.assertNotIn("model", reading)
        if reason:
            self.assertEqual(reading["reason"], reason)

    def test_current_xhigh_first_turn_without_assistant_output(self):
        self.write()
        reading = self.read()
        self.assertEqual(reading["state"], "current")
        self.assertEqual(reading["effort"], "xhigh")
        self.assertEqual(reading["model"], "gpt-6-astra")
        self.assertEqual(reading["context_at"], STAMP)
        self.assertEqual(reading["source"], {"path": str(self.path), "context_line": 3})
        self.assertTrue(reading["observed_at"])

    def test_effort_and_model_change_across_turns(self):
        self.write([meta(), event(), context(), event("task_complete"),
                    event(turn="turn-2"), context("turn-2", "gpt-6-sol", "high")])
        reading = self.read()
        self.assertEqual((reading["state"], reading["turn_id"], reading["model"], reading["effort"]),
                         ("current", "turn-2", "gpt-6-sol", "high"))

    def test_new_turn_before_context_never_reuses_previous(self):
        self.write([meta(), event(), context(), event("task_complete"), event(turn="turn-2")])
        self.assert_unknown(self.read(), "active_context_turn_mismatch")

    def test_completed_and_aborted_are_only_historical(self):
        for end in ("task_complete", "turn_aborted"):
            with self.subTest(end=end):
                self.write([meta(), event(), context(), event(end)])
                reading = self.read()
                self.assertEqual(reading["state"], "last_observed")
                self.assertEqual(reading["reason"], end)
                self.assertNotIn("model", reading)
                self.assertNotIn("effort", reading)
                self.assertEqual(reading["last_observed"]["effort"], "xhigh")
                self.assertEqual(reading["last_observed"]["source"]["context_line"], 3)

    def test_wrong_thread_metadata_even_for_explicit_transcript(self):
        self.write([meta(OTHER), event(), context()])
        self.assert_unknown(self.read(transcript=self.path), "session_identity_mismatch")

    def test_different_thread_with_newer_file_is_ignored(self):
        self.write()
        newer = self.path.with_name("rollout-2099-01-01-" + OTHER + ".jsonl")
        self.write([meta(OTHER), event(), context(effort="low")], newer)
        os.utime(newer, (4102444800, 4102444800))
        self.assertEqual(self.read()["effort"], "xhigh")

    def test_missing_identity(self):
        self.write()
        self.assert_unknown(dial.read_dial(codex_home=self.home, environ={}), "missing_thread_id")
        self.write([event(), context()])
        self.assert_unknown(self.read(), "missing_session_identity")
        self.write([record("session_meta", {}), event(), context()])
        self.assert_unknown(self.read(), "missing_or_invalid_session_identity")

    def test_conflicting_env_ids_rejected_even_with_override(self):
        self.write()
        self.env["CODEX_SESSION_ID"] = OTHER
        self.assert_unknown(self.read(thread_id=THREAD), "conflicting_environment_identities")

    def test_invalid_ids(self):
        self.write()
        for bad in ("not-a-uuid", "../" + THREAD, THREAD.replace("-", ""), ""):
            with self.subTest(bad=bad):
                self.assert_unknown(self.read(thread_id=bad), "invalid_thread_id")
        self.env["CODEX_SESSION_ID"] = "bad"
        self.assert_unknown(self.read(), "invalid_thread_id")

    def test_session_id_fallback_and_matching_env_ids(self):
        self.write()
        self.env = {"CODEX_SESSION_ID": THREAD}
        self.assertEqual(self.read()["state"], "current")
        self.env["CODEX_THREAD_ID"] = THREAD.upper()
        self.assertEqual(self.read()["state"], "current")

    def test_explicit_id_overrides_environment_selection(self):
        self.write()
        self.env = {"CODEX_THREAD_ID": OTHER}
        self.assertEqual(self.read(thread_id=THREAD)["state"], "current")

    def test_home_precedence_and_no_environment_changes(self):
        self.write()
        self.env["CODEX_HOME"] = str(self.home / "missing")
        before = dict(self.env)
        self.assertEqual(self.read()["state"], "current")
        self.assertEqual(self.env, before)
        self.env["CODEX_HOME"] = str(self.home)
        self.assertEqual(dial.read_dial(environ=self.env)["state"], "current")
        with mock.patch.object(dial.Path, "home", return_value=self.home):
            # The fallback points at .codex underneath the mocked disposable home.
            self.assert_unknown(dial.read_dial(environ={"CODEX_THREAD_ID": THREAD}), "transcript_not_found")

    def test_missing_null_empty_or_nonstring_effort_unknown(self):
        for value in (None, "", " ", 0, False):
            with self.subTest(value=value):
                self.write([meta(), event(), context(effort=value)])
                self.assert_unknown(self.read(), "missing_or_invalid_effort")
        missing = context()
        del missing["payload"]["effort"]
        missing["payload"]["collaboration_mode"] = {"settings": {"reasoning_effort": "xhigh"}}
        self.write([meta(), event(), missing])
        self.assert_unknown(self.read(), "missing_or_invalid_effort")

    def test_literal_none_and_unfamiliar_efforts_preserved(self):
        for value in ("none", "ultra", "future-level-7"):
            with self.subTest(value=value):
                self.write([meta(), event(), context(effort=value)])
                self.assertEqual(self.read()["effort"], value)

    def test_supporting_effort_agrees_or_is_absent_or_null(self):
        for settings in ({}, {"reasoning_effort": None}, {"reasoning_effort": "xhigh"}):
            with self.subTest(settings=settings):
                ctx = context()
                ctx["payload"]["collaboration_mode"] = {"settings": settings}
                self.write([meta(), event(), ctx])
                self.assertEqual(self.read()["state"], "current")

    def test_disagreement_between_effort_fields(self):
        ctx = context()
        ctx["payload"]["collaboration_mode"] = {"settings": {"reasoning_effort": "high"}}
        self.write([meta(), event(), ctx])
        self.assert_unknown(self.read(), "effort_fields_disagree")

    def test_partial_and_malformed_lines_inside_active_span_are_unknown(self):
        for suffix, reason in ((b'{"type":', "incomplete_trailing_line"),
                               (b'{broken}\n', "malformed_json"),
                               (b'{"payload": {"bad": NaN}}\n', "malformed_json"),
                               (b'{}', "incomplete_trailing_line"),
                               (b'\xff\n', "invalid_utf8")):
            with self.subTest(suffix=suffix):
                self.write()
                self.path.write_bytes(self.path.read_bytes() + suffix)
                self.assert_unknown(self.read(), reason)

    def test_nonobject_records_and_payloads(self):
        for bad, reason in (([], "non_object_record"), (None, "non_object_record"),
                            ({"payload": []}, "non_object_payload"),
                            ({"payload": None}, "non_object_payload"),
                            ({}, "non_object_payload")):
            with self.subTest(bad=bad):
                self.write([meta(), event(), context(), bad])
                self.assert_unknown(self.read(), reason)

    def test_duplicate_candidates_ambiguous(self):
        self.write()
        self.write(path=self.path.with_name("rollout-another-" + THREAD + ".jsonl"))
        self.assert_unknown(self.read(), "ambiguous_transcripts")

    def test_bytes_unchanged_and_no_files_created(self):
        self.write()
        before = self.path.read_bytes()
        inventory = sorted(str(p) for p in self.home.rglob("*"))
        self.read()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(sorted(str(p) for p in self.home.rglob("*")), inventory)

    def test_no_context_or_context_for_wrong_current_task(self):
        self.write([meta(), event()])
        self.assert_unknown(self.read(), "no_turn_context")
        self.write([meta(), event(), context(turn="other-turn")])
        self.assert_unknown(self.read(), "active_context_turn_mismatch")

    def test_context_before_start_is_unknown(self):
        self.write([meta(), context(), event()])
        self.assert_unknown(self.read(), "context_precedes_task_start")

    def test_repeated_context_uses_latest_for_active_turn(self):
        self.write([meta(), event(), context(), context(model="gpt-6-sol", effort="medium")])
        reading = self.read()
        self.assertEqual((reading["model"], reading["effort"]), ("gpt-6-sol", "medium"))
        self.assertEqual(reading["source"]["context_line"], 4)

    def test_latest_null_effort_never_reuses_previous_context(self):
        self.write([meta(), event(), context(), context(effort=None)])
        self.assert_unknown(self.read(), "missing_or_invalid_effort")

    def test_unexpected_lifecycle_mismatches(self):
        cases = ([meta(), event(), context(), event("task_complete", "wrong")],
                 [meta(), event("task_complete")],
                 [meta(), event(), context(), event(turn="turn-2")],
                 [meta(), event(), context(), event("task_complete"), event("turn_aborted")])
        for rows in cases:
            with self.subTest(rows=rows):
                self.write(rows)
                self.assert_unknown(self.read())

    def test_missing_lifecycle_turn_id(self):
        self.write([meta(), record("event_msg", {"type": "task_started"}), context()])
        self.assert_unknown(self.read(), "missing_lifecycle_turn_id")

    def test_no_lifecycle_is_not_current(self):
        self.write([meta(), context()])
        self.assert_unknown(self.read(), "no_task_lifecycle")

    def test_historical_context_after_end_is_unknown(self):
        self.write([meta(), event(), context(), event("task_complete"), context()])
        self.assert_unknown(self.read(), "context_outside_completed_task")

    def test_missing_and_unreadable_file(self):
        self.assert_unknown(self.read(), "transcript_not_found")
        self.assert_unknown(self.read(transcript=self.path), "transcript_unreadable")
        self.write()
        with mock.patch.object(Path, "open", side_effect=PermissionError("sensitive text")):
            reading = self.read(transcript=self.path)
        self.assert_unknown(reading, "transcript_unreadable")
        self.assertNotIn("sensitive text", json.dumps(reading))

    def test_cli_current_json_and_uncertainty(self):
        self.write()
        arguments = ["--thread-id", THREAD, "--transcript", str(self.path)]
        with mock.patch.dict(os.environ, {}, clear=True):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = dial.main(arguments)
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), "DIAL NOW — EFFORT XHIGH · MODEL gpt-6-astra (Codex active turn) · read 3 min ago\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = dial.main(arguments + ["--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["effort"], "xhigh")
            self.write([meta(), event(), context(), event("task_complete")])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = dial.main(arguments)
            self.assertEqual(code, 2)
            self.assertEqual(len(output.getvalue().splitlines()), 1)
            self.assertIn("LAST SEEN gpt-6-astra · XHIGH · last seen 3 min ago", output.getvalue())

    def test_freshness_start_and_mtime_each_degrade_independently(self):
        for old_start, old_file in ((True, False), (False, True), (True, True)):
            with self.subTest(start=old_start, file=old_file):
                start = event()
                if old_start:
                    start["timestamp"] = datetime.datetime.fromtimestamp(
                        self.clock - 42 * 60, datetime.timezone.utc).isoformat()
                self.write([meta(), start, context()])
                if old_file:
                    os.utime(self.path, (self.clock - 42 * 60, self.clock - 42 * 60))
                reading = self.read()
                self.assertEqual(reading["state"], "last_observed")
                self.assertEqual(reading["age_seconds"], 42 * 60)
                self.assertNotIn("effort", reading)
                self.assertIn("last seen 42 min ago", dial.format_reading(reading))

    def test_freshness_exact_boundary(self):
        self.write()
        self.assertEqual(self.read(now=dial._timestamp(STAMP) + 1800)["state"], "current")
        self.assertEqual(self.read(now=dial._timestamp(STAMP) + 1800.001)["state"], "last_observed")

    def test_every_output_has_age_including_unknown_and_json(self):
        self.write()
        for reading in (self.read(), dial.read_dial(environ={}), self.read(now=self.clock + 3600)):
            self.assertIn("age_seconds", reading)
            self.assertIn("parse_ms", reading)
            self.assertRegex(dial.format_reading(reading), r"(?:min ago|age unknown)$")
            self.assertEqual(len(dial.format_reading(reading).splitlines()), 1)

    def test_old_malformed_lines_are_ignored_and_counted(self):
        self.write([meta(), event(), context(), event("task_complete")])
        with self.path.open("ab") as handle:
            handle.write(b'{broken}\n\xff\n')
            for row in (event(turn="turn-2"), context(turn="turn-2")):
                handle.write(json.dumps(row).encode() + b"\n")
        reading = self.read()
        self.assertEqual(reading["state"], "current", reading)
        self.assertEqual(reading["note"]["ignored_history_errors"], 2)

    def fill(self, size):
        filler = json.dumps(record("response_item", {"text": "x" * 8192})).encode() + b"\n"
        with self.path.open("ab") as handle:
            until = handle.tell() + size
            while handle.tell() < until:
                handle.write(filler)

    def test_tail_expands_once_when_start_is_in_previous_window(self):
        self.write()
        self.fill(3 * 1024 * 1024)
        reading = self.read()
        self.assertEqual(reading["state"], "current", reading)
        self.assertGreater(reading["tail_bytes"], dial.TAIL_BYTES)
        self.assertLessEqual(reading["tail_bytes"], 2 * dial.TAIL_BYTES)

    def test_tail_limit_never_reuses_context_when_start_outside_window(self):
        self.write()
        self.fill(5 * 1024 * 1024)
        reading = self.read()
        self.assert_unknown(reading, "task_start_outside_tail")
        self.assertEqual(reading["tail_bytes"], 2 * dial.TAIL_BYTES)

    def test_50_mib_fixture_under_200ms_and_bounded_io(self):
        self.write([meta()])
        self.fill(50 * 1024 * 1024)
        with self.path.open("ab") as handle:
            for row in (event(), context()):
                handle.write(json.dumps(row).encode() + b"\n")
        real_open = Path.open
        sizes = []
        class Reader:
            def __init__(self, wrapped): self.wrapped = wrapped
            def __enter__(self): return self
            def __exit__(self, *args): self.wrapped.close()
            def __getattr__(self, name): return getattr(self.wrapped, name)
            def read(self, size=-1):
                sizes.append(size)
                if size < 0: raise AssertionError("unbounded read")
                return self.wrapped.read(size)
            def readline(self, size=-1):
                sizes.append(size)
                if size < 0: raise AssertionError("unbounded header")
                return self.wrapped.readline(size)
        def opened(path, *args, **kwargs):
            return Reader(real_open(path, *args, **kwargs))
        with mock.patch.object(Path, "open", opened):
            reading = self.read()
        self.assertEqual(reading["state"], "current", reading)
        self.assertLess(reading["parse_ms"], 200, reading)
        self.assertLessEqual(sum(sizes), dial.HEADER_BYTES + 1 + 2 * dial.TAIL_BYTES)
        self.assertIn("context_byte", reading["source"])
        print("50 MiB fixture: parse_ms={:.3f} (< 200 ms); requested_bytes={}".format(
            reading["parse_ms"], sum(sizes)))

    def test_schema_canary_names_first_unknown_record_and_missing_key(self):
        self.write([meta(), event(), record("new_record_shape", {}), record("another", {})])
        reading = self.read()
        # unknown record types are ignored and counted, never a schema failure
        self.assertIn("new_record_shape", reading.get("ignored_types", []), reading)
        self.assertIn("another", reading.get("ignored_types", []), reading)
        self.write([meta(), event(), context(effort=None)])
        self.assertEqual(self.read()["schema"], "turn_context.payload.effort")

    def test_schema_check_success_and_failure_exit_codes(self):
        self.write()
        args = ["--schema-check", "--thread-id", THREAD, "--transcript", str(self.path)]
        with mock.patch.dict(os.environ, {}, clear=True):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = dial.main(args)
            self.assertEqual(code, 0)
            self.assertIn("schema OK on " + dial.schema_version(), out.getvalue())
            self.write([meta(), event(), context(effort=None)])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = dial.main(args)
            self.assertEqual(code, 2)
            self.assertIn("schema: turn_context.payload.effort", out.getvalue())

    def test_missing_or_invalid_timestamps_fail_schema_closed(self):
        for kind in ("start", "context"):
            for value in (None, "yesterday", "2026-10-24T12:00:00"):
                start, ctx = event(), context()
                (start if kind == "start" else ctx)["timestamp"] = value
                self.write([meta(), start, ctx])
                self.assert_unknown(self.read())
                self.assertIn("timestamp", self.read()["schema"])

    def test_output_escapes_terminal_controls(self):
        self.write([meta(), event(), context(model="gpt-6-sol\nFAKE", effort="hi\x1b[31m")])
        line = dial.format_reading(self.read())
        self.assertEqual(len(line.splitlines()), 1)
        self.assertNotIn("\x1b", line)

    def test_tail_identity_is_always_verified_in_header(self):
        self.write([meta(OTHER)])
        self.fill(3 * 1024 * 1024)
        with self.path.open("ab") as handle:
            for row in (event(), context()):
                handle.write(json.dumps(row).encode() + b"\n")
        self.assert_unknown(self.read(), "session_identity_mismatch")

    def test_no_start_schema_canary(self):
        self.write([meta(), record("renamed_task_started", {})])
        reading = self.read()
        # an unknown event type is ignored, never fatal; the reading then says what it
        # could not find — the task_started that never came
        self.assertEqual(reading["state"], "unknown", reading)
        self.assertIn("task_started", reading["schema"])

    def test_i_am_stamps_current_and_preserves_supplied_uncertain_labels(self):
        # Registry/path/identity are isolated stand-ins: hub siblings were not supplied.
        here = Path(__file__).resolve().parent
        root = here if (here / "i-am.py").exists() else here.parent
        registry = types.ModuleType("exo_registry")
        registry.registry = lambda: {}
        registry.mind_alias = lambda registry, name: name.upper()
        paths = types.ModuleType("exo_paths")
        paths.paths = lambda **kwargs: {"machine": "test", "roots": {"orchestrator": str(self.home)}}
        common = types.ModuleType("exo_common")
        common.identity_or_nonce = lambda **kwargs: ({}, "")
        common.mind_of = lambda vendor, model: {"gpt-6-astra": "ASTRA", "gpt-6-sol": "SOL"}.get(model, model)
        spec = importlib.util.spec_from_file_location("stamp_test", root / "i-am.py")
        stamp = importlib.util.module_from_spec(spec)
        with mock.patch.dict(__import__('sys').modules, {"exo_registry": registry, "exo_paths": paths,
                                                        "exo_common": common}):
            spec.loader.exec_module(stamp)
            for state in ("current", "last_observed", "unknown"):
                self.write([meta(), event(), context(model="gpt-6-sol", effort="medium")])
                if state == "last_observed":
                    os.utime(self.path, (self.clock - 3600, self.clock - 3600))
                if state == "unknown":
                    self.write([meta(), event(), context(effort=None)])
                real_load = importlib.util.spec_from_file_location
                def load(name, path):
                    dial_path = root / "package/codex_dial.py"
                    if not dial_path.exists():
                        dial_path = root / "codex_dial.py"
                    return real_load(name, dial_path if name == "codex_dial" else path)
                output = io.StringIO()
                with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.home), "CODEX_THREAD_ID": THREAD}, clear=True), \
                     mock.patch.object(importlib.util, "spec_from_file_location", side_effect=load), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(stamp.main(["ASTRA", "HIGH", state, "--quiet"]), 0)
                mind = "sol" if state == "current" else "astra"
                data = json.loads((self.home / ("live-test-" + mind + ".json")).read_text())
                entry = next(row for row in data["sessions"] if row["title"] == state)
                self.assertEqual(entry["effort"], "MEDIUM" if state == "current" else "HIGH")
                if state == "current":
                    self.assertEqual(entry["dial"]["turn_id"], "turn-1")
                    self.assertNotIn("stamped the label you gave", output.getvalue())
                else:
                    self.assertNotIn("dial", entry)
                    self.assertEqual(output.getvalue().count("stamped the label you gave"), 1)
                    self.assertIn("last seen", output.getvalue())

    def test_broken_old_completion_does_not_poison_new_turn(self):
        self.write([meta(), event(), context()])
        with self.path.open("ab") as handle:
            handle.write(b'{broken completion}\n')
            for row in (event(turn="turn-2"), context(turn="turn-2")):
                handle.write(json.dumps(row).encode() + b"\n")
        reading = self.read()
        self.assertEqual(reading["state"], "current", reading)
        self.assertEqual(reading["note"]["ignored_history_errors"], 1)

    def test_schema_canary_for_changed_lifecycle_shape(self):
        self.write([meta(), event(), context(), event("task_finished")])
        reading = self.read()
        # an unknown lifecycle-looking event is ignored and counted; the active turn reads
        self.assertEqual(reading["state"], "current", reading)
        self.assertIn("event_msg:task_finished", reading.get("ignored_types", []), reading)

    def test_schema_version_file_matches_canary(self):
        self.assertEqual(dial.schema_version(),
                         Path(dial.__file__).with_name("SCHEMA-VERSION.txt").read_text().strip())


if __name__ == "__main__":
    unittest.main()
