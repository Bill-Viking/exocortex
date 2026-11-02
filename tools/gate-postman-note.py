#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-postman-note.py — the postman's notice follows the lane-mail rule.

    python3 gate-postman-note.py            # every case

Lives BESIDE gate-comms.py (443 kB — too large to edit safely) and borrows its world builder, so
each case runs in the same hermetic scratch world gate-comms builds: a scratch HOME, a scratch hub,
a stub sync, a stub notifier, copies of postman.py / mail.py from beside this file.  No real mail,
no real push, no real banner.

  PN1  a lane with only FYI letters (and a machine-only one): no nudge, no banner, no POST order
       to a carrier, no push text — at the nudge minute and at twice it.
  PN2  a ruling letter to a lane whose window exists: ONE notice = the consequence line, « — »
       and the window's title; none of the banned words, no sender; the banner carries it with no
       subtitle; the carrier's POST order is `POST — a line for <owner>'s phone: <that notice>`.
  PN3  the same with no window: the consequence line + « — <LANE>: no window open ».
  PN4  grep: «is waiting», «say mail», «A note for the» (and N1/N2) appear nowhere in postman.py's
       notice text; the retired constants are gone.
"""
import importlib.util, io, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gate_comms_lib", str(HERE / "gate-comms.py"))
gc = importlib.util.module_from_spec(spec)
sys.modules["gate_comms_lib"] = gc
spec.loader.exec_module(gc)

SENDER = "ZEBRA-SENDER-7"
ASK = "Choose the header colour — say blue or green"
CONSEQUENCE = "Choose the header colour · say blue or green"
BANNED = re.compile(r"\b(notes?|letters?|mails?|waiting|is waiting|say mail)\b|A note for the|"
                    + SENDER, re.I)


def send(w, to, text, action):
    """A letter from a sender with a name no notice may carry (gc.letter always writes Exocortex)."""
    line = "- %s · to: %s · %s · %s · %s" % (gc.datetime.date.today().isoformat(), to, SENDER, text, action)
    with io.open(str(w["hub"] / "INBOX.md"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
    return line


def carrier_world(name, holder):
    """A bworld with SID_B live as the phone's carrier; `holder` also plants a window on NORTH/hub."""
    w = gc.bworld(name)
    gc.claude_transcript(w, gc.SID_B)
    gc.plant_live(w, [gc.SID_A, gc.SID_B])
    if holder:
        gc.plant_claim(w, "hub", "north", gc.HOLDER, session=gc.SID_A)
        gc.claude_transcript(w, gc.SID_A)
    return w


def passes(w, *minutes):
    gc.pmn(w, "--pass", "--no-pull")
    for m in minutes:
        gc.pmn(w, "--pass", "--no-pull", "--now", gc.later(minutes=m))


def banner_bodies(w):
    return [r["argv"] for r in gc.raises(w)]


def carrier_context(w):
    code, out, err = gc.hook(w, gc.SID_B, "UserPromptSubmit")
    return gc.context_of(out)


def case_pn1():
    gc.start("PN1", "a lane with only FYI letters: no notice, no POST order, no push text")
    w = carrier_world("pn1", holder=True)
    send(w, "NORTH/hub", "the nightly sync finished", "none — FYI")
    send(w, "NORTH/hub", "a heads-up nobody must answer", "no reply needed — FYI")
    send(w, "NORTH/hub", "rebuild chore for a machine", "rebuild the index")
    passes(w, 6, 45)
    rows = list((gc.state_of(w).get("nudges") or {}).values())
    gc.check(not rows and not gc.nudges_of(w), "no nudge is composed, at the nudge minute or at 45 min: %s" % rows)
    gc.check(not [r for r in (gc.state_of(w).get("owner") or {}).values() if r.get("kind") == "nudge"],
             "…and no push text is kept for one")
    # The idle-window ANNOUNCE road ("<window>: N letters waiting", subtitle "mail waiting") is a
    # different builder, outside this gate's scope; it fires here for the three letters and is NOT fixed.
    # It is named, not hidden: every other banner is a failure.
    announce = [a for a in banner_bodies(w) if re.search(r"\d+ letters? waiting", a[2])]
    for a in announce:
        print("  [INFO] NOT FIXED, out of scope — the ANNOUNCE road still says: %s" % a)
    other = [a for a in banner_bodies(w) if a not in announce]
    gc.check(not other, "no nudge banner was raised: %s" % other)
    ctx = carrier_context(w)
    gc.check("POST —" not in ctx and "PushNotification" not in ctx,
             "no POST order reaches the carrier: %r" % ctx[:80])
    gc.check(not [i for i in gc.pending_of(w, gc.SID_B) if i.get("kind") == "owner"],
             "…nor sits in its pending file")
    code, out = gc.pm(w, "--status", "--no-pull")
    gc.check(not BANNED.search("\n".join(l for l in out.splitlines() if "nudged" in l)),
             "--status has no nudge line to say")


def notice_checks(w, expect_where, label):
    rows = list((gc.state_of(w).get("nudges") or {}).values())
    gc.check(len(rows) == 1, "%s: exactly ONE nudge (%d)" % (label, len(rows)))
    if not rows:
        return
    text = rows[0].get("text", "")
    want = "%s — %s" % (CONSEQUENCE, expect_where)
    gc.check(text == want, "%s: the notice is the consequence line + where: %r (want %r)" % (label, text, want))
    gc.check(not BANNED.search(text),
             "%s: none of note / letter / mail / waiting / say mail, no sender, no «A note for the»: %s"
             % (label, BANNED.findall(text)))
    gc.check(rows[0].get("phone_text", "").startswith(CONSEQUENCE) and not BANNED.search(rows[0].get("phone_text", "")),
             "%s: the phone text is the same sentence: %r" % (label, rows[0].get("phone_text")))
    shown = [a for a in banner_bodies(w) if CONSEQUENCE in " ".join(a)]
    gc.check(len(shown) == 1 and shown[0][2] == text and shown[0][1] == "" and not BANNED.search(" ".join(shown[0][1:])),
             "%s: the desktop banner is raised once, body = the notice, no subtitle: %r"
             % (label, [a[1:] for a in shown]))
    ctx = carrier_context(w)
    who = gc.pm_module(w).owner_label()
    phone = [l for l in ctx.splitlines() if l.startswith("POST — a line for")]
    gc.check(len(phone) == 1 and phone[0].startswith("POST — a line for %s's phone: %s" % (who, rows[0]["phone_text"])),
             "%s: the POST order is `POST — a line for %s's phone: <that one notice>`: %s" % (label, who, phone))
    gc.check("a note for" not in ctx.lower() and "PushNotification" in ctx,
             "%s: …it still names the one PushNotification call, and says no «a note for»" % label)
    return rows[0]


def case_pn2():
    gc.start("PN2", "a ruling to a lane whose window exists: one notice = consequence + the window's title")
    w = carrier_world("pn2", holder=True)
    send(w, "NORTH/hub", "which header colour do you want", ASK)
    send(w, "NORTH/hub", "the nightly sync finished", "none — FYI")
    passes(w, 6)
    row = notice_checks(w, "«%s»" % gc.HOLDER, "window")
    gc.check(row and row.get("case") == "N1", "…the window case: %s" % (row or {}).get("case"))
    gc.check(row and row.get("hook_text", "").startswith(CONSEQUENCE + " — ") and "FYI" not in row.get("hook_text", "")
             and "nightly" not in row.get("hook_text", ""), "…the FYI beside it adds nothing: %r" % (row or {}).get("hook_text"))
    mod = gc.pm_module(w)
    gc.check(mod.mark_facts({"t": {"line": "- 2026-10-24 · to: NORTH/hub · %s · body · %s" % (SENDER, ASK),
                                   "to": "NORTH/hub", "first_seen": gc.later(minutes=-9)}},
                            ["t"], gc.load_mail(w)) == {"lane": "HUB", "from": "", "subject": CONSEQUENCE},
             "the tree's ✉ hover: the lane and the consequence, no sender")


def case_pn3():
    gc.start("PN3", "the same with no window: consequence + «<LANE>: no window open»")
    w = carrier_world("pn3", holder=False)
    send(w, "NORTH/Nowhere", "which header colour do you want", ASK)
    passes(w, 6)
    row = notice_checks(w, "NOWHERE: no window open", "no window")
    gc.check(row and row.get("case") == "N2", "…the no-window case: %s" % (row or {}).get("case"))


def case_pn4():
    gc.start("PN4", "grep: the old notice words are nowhere in postman.py's notice text")
    src = (HERE / "postman.py").read_text(encoding="utf-8")
    rows = src.splitlines()
    first_import = next(n for n, l in enumerate(rows, 1) if l.startswith("import "))
    for needle in ("is waiting", "say mail", "A note for the", "a note for %s's phone"):
        # the module's usage docstring (before the first import) and comment lines are not notice
        # text: `--status   what is waiting, in both directions` is a help line
        hits = [n for n, l in enumerate(rows, 1)
                if needle in l and n > first_import and not l.lstrip().startswith("#")]
        gc.check(not hits, "«%s» appears nowhere in postman.py's code or docstrings (lines %s)" % (needle, hits))
    gc.check(not re.search(r"^N[12] = ", src, re.M) and not re.search(r"\bshape = N[12]\b", src),
             "the N1 / N2 constants are gone and nothing reads them")
    gc.check("letter_words" not in src and "NUDGE_SENDER_MAX" not in src,
             "…and the sender/subject quoting helpers went with them")
    mod = gc.pm_module(gc.world("pn4"))
    gc.check(not hasattr(mod, "N1") and not hasattr(mod, "N2"), "the module has no N1 / N2")


def main():
    gc.ROOT.mkdir(parents=True, exist_ok=True)
    print("gate-postman-note.py · BQ-365B · scratch %s" % gc.ROOT)
    for case in (case_pn1, case_pn2, case_pn3, case_pn4):
        try:
            case()
        except Exception as exc:
            gc.FAILS.append("%s: the case itself raised %r" % (gc.CASE["id"], exc))
            print("  [FAIL] the case itself raised %r" % (exc,))
    print("\n===== GATE-POSTMAN-NOTE =====")
    print("  %d checks · %d passed · %d failed" % (gc.PASSES + len(gc.FAILS), gc.PASSES, len(gc.FAILS)))
    for f in gc.FAILS:
        print("  FAIL  %s" % f)
    gc.remove_own_worlds()
    return 1 if gc.FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
