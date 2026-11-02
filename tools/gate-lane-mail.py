#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-lane-mail.py — the machine half of the lane-mail rule.

    python3 gate-lane-mail.py            # every case

Lives BESIDE gate-comms.py (443 kB — too large to edit safely) and borrows its world builder, so
each case runs in the same hermetic scratch world gate-comms builds: a scratch HOME, a scratch hub,
a stub sync, a copy of mail.py from beside this file. No real mail, no real push.

  LM1  `--read TO --for-the-user`: an INBOX with an FYI note, a ruling and a physical move prints
       TWO lines — each built from the ACTION field alone — and no sender, no body, no token, no
       count, and not the words «letter» or «mail». Plain `--read` on the same INBOX is unchanged.
  LM2  an INBOX with FYI / read / machine-only actions prints NOTHING at all, exit 0.
  LM3  `--wait`'s hand-back line carries the same path (deliver() driven with a stub postman).
  LM4  `--lint-reply`: five fixtures — three hits (exit 1, one line naming the phrase), two clean
       (exit 0, silent).
"""
import importlib.util, io, json, os, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gate_comms_lib", str(HERE / "gate-comms.py"))
gc = importlib.util.module_from_spec(spec)
sys.modules["gate_comms_lib"] = gc
spec.loader.exec_module(gc)

TO = "NORTH/hub"
BODY = "BODYMARKER-never-shown"
MAIL_WORDS = re.compile(r"\b(letters?|mails?)\b", re.I)


def mail_py(w, *args, **kw):
    return gc.mp(w, *args, **kw)


def case_lm1():
    gc.start("LM1", "--read TO --for-the-user: two asks, two plain lines, nothing else")
    w = gc.world("lm1")
    gc.letter(w, TO, "the nightly sync finished " + BODY, "none — FYI")
    gc.letter(w, TO, "which header colour do you want " + BODY,
              "Choose the header colour — say blue or green")
    gc.letter(w, TO, "the backup drive is not mounted " + BODY,
              "Plug the backup drive into the laptop — then the copy can finish")
    code, out = mail_py(w, "--read", TO, "--for-the-user")
    rows = [l for l in out.splitlines() if l.strip()]
    gc.check(code == 0, "exit 0")
    gc.check(len(rows) == 2, "prints exactly two lines: %r" % rows)
    gc.check("Choose the header colour · say blue or green" in rows,
             "the ruling reads `<what it means for you> · <the one move>`")
    gc.check("Plug the backup drive into the laptop · then the copy can finish" in rows,
             "the physical move reads the same way")
    gc.check(BODY not in out and "nightly" not in out and "header colour do you" not in out,
             "the body of a note is never printed")
    gc.check("Exocortex" not in out and "to:" not in out and TO not in out and "NORTH" not in out.upper(),
             "no sender, no address, no target")
    gc.check(not re.search(r"\d", out) and "pm-" not in out and "MAIL" not in out,
             "no count, no token, no `MAIL` frame")
    gc.check(not MAIL_WORDS.search(out), "not the word «letter» or «mail»")
    code2, out2 = mail_py(w, "--read", TO)
    gc.check(code2 == 0 and out2.count("MAIL:") == 3 and BODY in out2 and "[pm-" in out2,
             "plain --read on the same INBOX is unchanged: three MAIL lines with body and token")
    # the same read twice prints the same two lines: --for-the-user stamps nothing without --mark
    code3, out3 = mail_py(w, "--read", TO, "--for-the-user")
    gc.check(code3 == 0 and out3 == out, "a second read prints the same (nothing was stamped)")
    # --mark stamps, silently, and a later read is empty
    code4, out4 = mail_py(w, "--read", TO, "--for-the-user", "--mark", "gate lm1")
    gc.check(code4 == 0 and [l for l in out4.splitlines() if l.strip()] == rows,
             "with --mark it prints the same two lines and says nothing about the stamp")
    code5, out5 = mail_py(w, "--read", TO, "--for-the-user")
    gc.check(code5 == 0 and out5 == "", "…and once stamped, a read prints nothing at all: %r" % out5)


def case_lm2():
    gc.start("LM2", "--for-the-user with nothing that asks the person prints nothing, exit 0")
    w = gc.world("lm2")
    code, out = mail_py(w, "--read", TO, "--for-the-user")
    gc.check(code == 0 and out == "", "an empty INBOX: no output, exit 0: %r" % out)
    for body, action in (("sync done", "none — FYI"), ("a note", "read"), ("another", "fyi"),
                         ("machine one", "no reply needed — FYI"),
                         ("ack it", "reply with ack to the hub"), ("a chore", "rebuild the index")):
        gc.letter(w, TO, body, action)
    code, out = mail_py(w, "--read", TO, "--for-the-user")
    gc.check(code == 0 and out == "", "FYI, read, fyi, and machine-only actions: no output, exit 0: %r" % out)
    code, out = mail_py(w, "--read", TO)
    gc.check(code == 0 and out.count("MAIL:") == 6, "…while plain --read still lists all six")


class StubPm:
    def frame(self, take, skipped=None): return "FRAME"
    def receipt(self, *a, **k): pass
    def clear_pending(self, *a, **k): pass
    def skipped_words(self, skipped): return ""


def case_lm3():
    gc.start("LM3", "--wait's hand-back line carries the --for-the-user path")
    w = gc.world("lm3")
    mod_spec = importlib.util.spec_from_file_location("lm3_mail", str(w["hub"] / "tools" / "mail.py"))
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(w["home"])
    try:
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
        line = "- 2026-10-24 · to: NORTH/hub · Exocortex · body · Choose a colour — blue or green"
        item = {"kind": "letter", "line": line, "to": TO, "token": mod.token(line)}
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mod.deliver([item], StubPm(), Path("."), "sid", road="waiter")
        finally:
            sys.stdout = old
    finally:
        if old_home is None: os.environ.pop("HOME", None)
        else: os.environ["HOME"] = old_home
    first = next((l for l in buf.getvalue().splitlines() if "the wait ended on" in l), "")
    gc.check("--read %s --for-the-user" % TO in first, "the hand-back line names the path: %s" % first)
    gc.check("1 asking letter(s): " in first and "Choose a colour" in first and mod.token(line) in first,
             "…and keeps its old words (count, action, token) unchanged")


LINT_FIXTURES = (
    ("hit-1.txt", "Done — the header is blue.\n\nWorth your eye when you have a minute.\n", 1, "worth your eye"),
    ("hit-2.txt", "Two things changed.\nYou have letters waiting for you.\n", 1, "letters waiting"),
    ("hit-3.txt", "All set.\n\nPlease read the Mail from the other lane.\n", 1, "mail"),
    ("clean-1.txt", "The header is blue.\n\n```\nmail.py --read NORTH/hub --for-the-user\nletter letter mail\n```\n"
                    "\nNothing else needs you.\n", 0, None),
    ("clean-2.txt", "**Law: mail between sessions is the machine's, never the user's.**\n\n"
                    "Done — the header is blue and the drive is mounted.\n", 0, None),
)


def case_lm4():
    gc.start("LM4", "--lint-reply: five fixtures, three hits and two clean")
    w = gc.world("lm4")
    for name, text, want, phrase in LINT_FIXTURES:
        path = w["out"] / name
        gc.write(path, text)
        code, out = gc.run([gc.PY, str(w["hub"] / "tools" / "mail.py"), "--lint-reply", str(path)],
                           cwd=str(w["hub"]), env=w["env"])
        rows = [l for l in out.splitlines() if l.strip()]
        if want:
            gc.check(code == 1 and len(rows) == 1 and ("«%s»" % phrase) in rows[0].lower(),
                     "%s: exit 1, one line naming «%s»: %r" % (name, phrase, rows))
        else:
            gc.check(code == 0 and out == "", "%s: exit 0, silent: %r" % (name, out))
    code, out = gc.run([gc.PY, str(w["hub"] / "tools" / "mail.py"), "--lint-reply", str(w["out"] / "absent.txt")],
                       cwd=str(w["hub"]), env=w["env"])
    gc.check(code not in (0, 1) and len([l for l in out.splitlines() if l.strip()]) == 1,
             "a file that is not there: one line, an exit that is neither 0 nor 1 (%s)" % code)


def main():
    gc.ROOT.mkdir(parents=True, exist_ok=True)
    print("gate-lane-mail.py · BQ-365 · scratch %s" % gc.ROOT)
    for case in (case_lm1, case_lm2, case_lm3, case_lm4):
        try:
            case()
        except Exception as exc:
            gc.FAILS.append("%s: the case itself raised %r" % (gc.CASE["id"], exc))
            print("  [FAIL] the case itself raised %r" % (exc,))
    print("\n===== GATE-LANE-MAIL =====")
    print("  %d checks · %d passed · %d failed" % (gc.PASSES + len(gc.FAILS), gc.PASSES, len(gc.FAILS)))
    for f in gc.FAILS:
        print("  FAIL  %s" % f)
    gc.remove_own_worlds()
    return 1 if gc.FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
