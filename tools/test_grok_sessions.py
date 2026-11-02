import json
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.parse import quote

import grok_sessions


class GrokSessionsTests(unittest.TestCase):
    def make_session(self, base, cwd=r"C:\Users\You\Prøject", extra=None):
        sid = str(uuid.uuid4())
        session = Path(base) / ".grok" / "sessions" / quote(cwd, safe="") / sid
        session.mkdir(parents=True)
        payload = {
            "info": {"id": sid, "cwd": cwd},
            "generated_title": "A title",
            "created_at": "2026-09-16T10:11:12.123456789Z",
            "updated_at": "2026-09-16T10:12:13Z",
            "last_active_at": "2026-09-16T10:13:14.987654321Z",
            "current_model_id": "grok-test",
            "parent_session_id": "fork-source",
        }
        if extra:
            payload.update(extra)
        (session / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
        return session, sid, cwd

    def test_metadata_mapping_dates_and_primary_fork(self):
        with tempfile.TemporaryDirectory() as temp:
            session, sid, cwd = self.make_session(temp)
            events = [
                {"type": "turn_started", "session_relationship": "primary"},
                {"type": "turn_ended"},
            ]
            (session / "events.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
            )
            item = grok_sessions.metadata(session / "chat_history.jsonl")
            self.assertEqual(item["id"], sid)
            self.assertEqual(item["cwd"], cwd)
            self.assertEqual(item["title"], "A title")
            self.assertEqual(item["model"], "grok-test")
            self.assertEqual(item["updated_at"], "2026-09-16T10:12:13Z")
            self.assertAlmostEqual(item["started_epoch"], 1789553472.123456, places=5)
            self.assertEqual(item["relationship"], "primary")
            self.assertFalse(item["is_subagent"])
            self.assertEqual(item["parent_session_id"], "fork-source")
            self.assertEqual(item["status"], "idle")

    def test_fallback_bad_layout_malformed_and_oversized(self):
        with tempfile.TemporaryDirectory() as temp:
            session, sid, cwd = self.make_session(temp)
            (session / "summary.json").write_text(json.dumps({"info": {}}), encoding="utf-8")
            item = grok_sessions.metadata(session)
            self.assertEqual((item["id"], item["cwd"]), (sid, cwd))
            (session / "summary.json").write_text(
                json.dumps({"info": {"id": sid, "cwd": cwd}}),
                encoding="utf-8-sig",
            )
            self.assertEqual(grok_sessions.metadata(session)["id"], sid)
            stray = Path(temp) / "random"
            stray.mkdir()
            (stray / "summary.json").write_text(json.dumps({"info": {"id": "x"}}))
            self.assertEqual(grok_sessions.metadata(stray), {})
            self.assertEqual(grok_sessions.metadata(stray / "anything.json"), {})
            (session / "summary.json").write_text("{bad", encoding="utf-8")
            self.assertEqual(grok_sessions.metadata(session), {})
            (session / "summary.json").write_bytes(b" " * (512 * 1024 + 1))
            self.assertEqual(grok_sessions.metadata(session), {})

    def test_iter_sessions_keeps_forks_and_marks_only_relationship(self):
        with tempfile.TemporaryDirectory() as temp:
            primary, _, _ = self.make_session(temp, cwd="/tmp/one")
            child, _, _ = self.make_session(temp, cwd="/tmp/two")
            (primary / "events.jsonl").write_text(
                '{"type":"turn_ended","session_relationship":"primary"}\n'
            )
            (child / "events.jsonl").write_text(
                '{"type":"turn_ended","session_relationship":"subagent"}\n'
            )
            unknown, _, _ = self.make_session(temp, cwd="/tmp/three")
            (unknown / "events.jsonl").write_text(
                '{"type":"turn_ended","session_relationship":"fork"}\n'
            )
            items = list(grok_sessions.iter_sessions(Path(temp) / ".grok"))
            self.assertEqual(len(items), 3)
            self.assertEqual(sum(item["is_subagent"] for item in items), 1)
            self.assertEqual(list(grok_sessions.iter_sessions(Path(temp) / "absent")), [])

    def test_turn_types_partial_redaction_and_bom(self):
        with tempfile.TemporaryDirectory() as temp:
            session, _, _ = self.make_session(temp)
            rows = [
                {"type": "system", "content": [{"type": "text", "text": "system"}]},
                {"type": "reasoning", "content": [{"type": "text", "text": "hidden"}]},
                {"type": "tool_result", "content": [{"type": "text", "text": "tool"}]},
                {"type": "user", "timestamp": "t1", "content": [{"type": "text", "text": "hello sk-abcdef"}, {"type": "image", "text": "ignore"}]},
                {"type": "assistant", "ts": 2, "content": 'Bearer abc.def {"api_key":"open"}'},
                {"type": "user", "content": [{"type": "image", "url": "x"}]},
            ]
            history = session / "chat_history.jsonl"
            with history.open("wb") as handle:
                handle.write(b"\xef\xbb\xbf")
                for row in rows:
                    handle.write((json.dumps(row) + "\n").encode("utf-8"))
                handle.write(b'{"type":"user","content":')
            turns = list(grok_sessions.iter_turns(history, max_chars=80))
            self.assertEqual([turn[1] for turn in turns], ["user", "assistant"])
            self.assertEqual(turns[0], ("t1", "user", "hello [REDACTED]"))
            self.assertIn("Bearer [REDACTED]", turns[1][2])
            self.assertIn('"api_key":"[REDACTED]"', turns[1][2])

    def test_long_line_recovery_and_bounded_event_tail(self):
        with tempfile.TemporaryDirectory() as temp:
            session, _, _ = self.make_session(temp)
            history = session / "chat_history.jsonl"
            history.write_bytes(
                b"x" * (2 * 1024 * 1024 + 10)
                + b"\n"
                + b'{"type":"assistant","content":"recovered"}\n'
            )
            self.assertEqual(
                list(grok_sessions.iter_turns(session)), [(None, "assistant", "recovered")]
            )
            with (session / "events.jsonl").open("wb") as handle:
                handle.write(b"x" * (70 * 1024) + b"\n")
                handle.write(b'{"type":"turn_started","session_relationship":"primary"}\n')
            self.assertEqual(grok_sessions.metadata(session)["status"], "busy")


if __name__ == "__main__":
    unittest.main()
