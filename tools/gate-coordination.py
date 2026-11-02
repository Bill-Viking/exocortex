#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-coordination.py — the coordination gates (stamps, claims, the union merge), runnable on any machine.

    python3 tools/gate-coordination.py            # G1 · G2 · G3 · G5b, every command's real output shown
    python3 tools/gate-coordination.py --skip-g3  # without the sync-union rehearsal

Proves the three coordination mechanisms HERMETICALLY: every stamp and claim check
runs against a SCRATCH hub folder (i-am.py / claim.py / who-is-live.py --hub <scratch>), and every
stamp and claim here is --quiet, so a gate run never mails the other machine. Live
cross-machine stamps and claims never enter a proof — a proof that depends on who is live
elsewhere is not a proof. A live hub elsewhere is reproduced on purpose: a hub
claim AND a live hub stamp are planted from a machine named "elsewhere", and a job arc must still
be answered from its own claim (who-is-live --pen --arc is scoped to the arc asked).
  G1  session-keyed stamps   two sessions of one mind coexist; --off with a title leaves the other;
                             an old-shape stamp file still reads. G1b is the ONE LIVE TOUCH: the tree
                             page has no --hub, so two OPUS test stamps are written to the live hub,
                             orchestrator.py renders, the root count is read, and both are switched off
                             again before anything else runs (the residue is an off OPUS stamp, this
                             tool's normal close).
  G2  job claims             claim → HELD/STOP for an arriving session → release → OK; a planted hub
                             elsewhere never answers for button-up or for a --lane; sweep reaps by age,
                             --strict also reaps the unstamped. G2e: the MIND on a pen is
                             looked up by session identity, then by title, then recorded as `?` with one
                             plain line — never the newest stamp's mind (both recorded directions).
                             G2f: a claim on an arc the session ALREADY HOLDS records
                             session, host_session and vendor exactly as a first claim does, and the
                             holds cache the postman's hook reads follows every claim and release
  G3  append-only union      sync.py merges INBOX/TAUGHT/watchers both-sides edits by line union and
                             still refuses STATUS.md — in sync.py's own TEST MODE, git never runs
  G5b never-ask              a held hub arc (same machine, and elsewhere) makes an arriving hub session
                             print its READER ROLE line with no question in it
The runner stamps and claims ITSELF at its own ritual, never here. Stdlib only, OS-neutral.
Exit 1 on any failed check.
"""
import importlib.util, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

try:                                   # cp1252 console: never crash on an em-dash
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HUB = Path(__file__).resolve().parent.parent
PY = sys.executable
SCRATCH = Path(tempfile.gettempdir()) / "exocortex-gate-coordination"
fails, checks = [], []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, ("  — " + detail) if (detail and not cond) else ""))
    if not cond:
        fails.append(name)


def run(label, *args, expect=0, must=(), must_not=(), cwd=None, env=None, quiet=False):
    print("\n$ %s" % " ".join(a if " " not in a else '"%s"' % a for a in args))
    p = subprocess.run([PY] + list(args), cwd=str(cwd or HUB), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    out = (p.stdout or "") + (p.stderr or "")
    if not quiet:
        print(out.rstrip() or "(no output)")
    bad = []
    if expect is not None and p.returncode != expect:
        bad.append("exit %d, expected %d" % (p.returncode, expect))
    bad += ["missing %r" % m for m in must if m not in out]
    bad += ["must not contain %r" % m for m in must_not if m in out]
    ok(label, not bad, "; ".join(bad))
    return out


def section(t):
    print("\n" + "=" * 8 + " " + t + " " + "=" * 8)


def read_json(p, default):
    try:
        return json.loads(io.open(p, encoding="utf-8").read())
    except Exception:
        return default


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# the scratch hub — every stamp/claim check runs here, never in the live folder
# --------------------------------------------------------------------------

SCR = SCRATCH / "hub"
HUBARGS = ["--hub", str(SCR)]
def this_machine():
    """This machine's name, read the way i-am.py reads it when it names the stamp
    file — through the resolver beside the tools when it is installed, else the
    older layout's record — so G1b counts the rows of the file the stamps were
    really written to. "unknown" when neither names one."""
    if (HUB / "tools" / "exo_paths.py").is_file():
        try:
            sys.path.insert(0, str(HUB / "tools"))
            import exo_paths
            name = str(exo_paths.paths(tool_file=HUB / "tools" / "i-am.py").get("machine") or "")
            if name:
                return name.lower()
        except Exception:
            pass
        finally:
            if str(HUB / "tools") in sys.path:
                sys.path.remove(str(HUB / "tools"))
    return str(read_json(Path.home() / "orchestrator-sync" / "machine.json", {})
               .get("name", "")).lower() or "unknown"



ME = this_machine()


def owner_asks():
    """The phrases that would put a question to the owner: "ask the owner", and
    "ask <name>" for every word the hub's own registry.json names them by — read
    at run time, so no owner's name is written in this file."""
    phrases = ["ask the owner"]
    owner = read_json(HUB / "registry.json", {}).get("owner") or {}
    for word in [owner.get("name")] + list(owner.get("aliases") or []):
        if isinstance(word, str) and word.strip():
            phrases.append("ask %s" % word.strip())
    return tuple(phrases)


ASK_OWNER = owner_asks()
ELSEWHERE_TITLE = "ACT — Exocortex: hub (planted elsewhere)"


def copy_mail(hub):
    """mail.py into a scratch hub's tools/, with what it reads from its first line
    when it is here: the loader (the person's names) and the resolver (the
    machine record). A hub from before either has none to copy."""
    shutil.copy2(str(HUB / "tools" / "mail.py"), str(hub / "tools" / "mail.py"))
    for name in ("exo_registry.py", "exo_paths.py"):
        if (HUB / "tools" / name).is_file():
            shutil.copy2(str(HUB / "tools" / name), str(hub / "tools" / name))


def fresh_scratch_hub():
    if SCR.exists():
        shutil.rmtree(str(SCR))
    (SCR / "tools").mkdir(parents=True)
    copy_mail(SCR)                     # claim.py --take mails the holder from here
    io.open(SCR / "INBOX.md", "w", encoding="utf-8").write("# INBOX (gate scratch)\n\n")
    print("   scratch hub:", SCR)


def _recent():
    from datetime import datetime, timedelta
    return (datetime.now().astimezone() - timedelta(minutes=5)).replace(microsecond=0).isoformat()


def _stamp_age_h(when):
    """How old a stamp row is, in hours — or None when it carries no readable
    `when`. The tree's own measure of a live stamp."""
    from datetime import datetime
    try:
        d = datetime.fromisoformat(str(when or ""))
    except Exception:
        return None
    try:
        if d.tzinfo is None:
            d = d.astimezone()
        return (datetime.now().astimezone() - d).total_seconds() / 3600.0
    except Exception:
        return None


def plant_elsewhere():
    """A live hub on ANOTHER machine: a hub claim
    from a machine named 'elsewhere' plus that machine's live FABLE stamp carrying a hub title.
    Planted as bytes, never through the tools, so nothing here depends on who is live for real."""
    io.open(SCR / "live-elsewhere-fable.json", "w", encoding="utf-8").write(json.dumps(
        {"machine": "elsewhere", "mind": "FABLE", "when": _recent(),
         "sessions": [{"title": ELSEWHERE_TITLE, "effort": "EXTRA", "when": _recent()}]}))
    claims = read_json(SCR / "claims.json", [])
    claims = [c for c in claims if str(c.get("machine", "")).lower() != "elsewhere"]
    claims.append({"arc": "hub", "machine": "elsewhere", "mind": "FABLE", "title": ELSEWHERE_TITLE,
                   "since": _recent()})
    io.open(SCR / "claims.json", "w", encoding="utf-8").write(json.dumps(claims, ensure_ascii=False, indent=2) + "\n")
    print("   planted: hub claimed + FABLE hub stamp live on ELSEWHERE")


def unplant_elsewhere():
    (SCR / "live-elsewhere-fable.json").unlink()
    claims = [c for c in read_json(SCR / "claims.json", []) if str(c.get("machine", "")).lower() != "elsewhere"]
    io.open(SCR / "claims.json", "w", encoding="utf-8").write(json.dumps(claims, ensure_ascii=False, indent=2) + "\n")


# --------------------------------------------------------------------------
# G1 — stamps
# --------------------------------------------------------------------------

def g1():
    section("G1a — two sessions of one mind (OPUS test titles A and B), scratch hub")
    run("stamp A", "tools/i-am.py", "--quiet", "OPUS", "EXTRA", "GATE-A", *HUBARGS)
    run("stamp B — the file now holds two", "tools/i-am.py", "--quiet", "OPUS", "EXTRA", "GATE-B", *HUBARGS, must=("2",))
    out = run("table shows both rows", "tools/who-is-live.py", *HUBARGS, must=("GATE-A", "GATE-B"))
    rows = [l for l in out.splitlines() if "OPUS" in l and "LIVE" in l and "GATE-" in l]
    ok("exactly two live OPUS test rows", len(rows) == 2, "%d rows" % len(rows))
    ok("scratch table carries no live-folder session (hermetic)", "ACT —" not in out and "ACT -" not in out)

    section("G1b — the tree's root counts them (the ONE live touch: orchestrator.py has no --hub)")
    run("live: stamp A", "tools/i-am.py", "--quiet", "OPUS", "EXTRA", "GATE-A", quiet=True)
    run("live: stamp B", "tools/i-am.py", "--quiet", "OPUS", "EXTRA", "GATE-B", quiet=True)
    # COUNT THE ROWS THE PAGE COUNTS. The tree's `N stamped`
    # is rows YOUNGER THAN TWELVE HOURS by their own `when` (collect-openers'
    # own _is_live: not off, age <= 0.5 days); this counted every row in the
    # file, so one real hub's 71-hour OPUS row — a lane's session that never
    # stamped off — turned G1b red for a reason that is not the tool's.
    n = 0
    for f in HUB.glob("live-%s-opus.json" % ME):
        for x in (read_json(f, {}).get("sessions") or []):
            if not isinstance(x, dict) or x.get("off"):
                continue
            if _stamp_age_h(x.get("when")) is not None and _stamp_age_h(x.get("when")) <= 12.0:
                n += 1
    print("   live OPUS sessions on this machine right now: %d (the two test stamps included, "
          "rows older than 12 h counted out as the page counts them out)" % n)
    run("render the tree (orchestrator.py)", "orchestrator.py", expect=None, quiet=True)
    html = io.open(HUB / "tree.html", encoding="utf-8", errors="replace").read() if (HUB / "tree.html").is_file() else ""
    # One word per measure — i-am stamps read `N stamped` on the
    # page now, and `live` is the pulse's own count alone.
    hits = [l.strip()[:140] for l in html.splitlines() if ("%d stamped" % n) in l]
    for h in hits[:3]:
        print("   ", h)
    ok("tree.html carries '%d stamped'" % n, bool(hits))
    run("live: A off", "tools/i-am.py", "--quiet", "--off", "OPUS", "GATE-A", quiet=True)
    run("live: B off", "tools/i-am.py", "--quiet", "--off", "OPUS", "GATE-B", quiet=True)
    run("live folder: no GATE rows left after the tree check", "tools/who-is-live.py", must_not=("GATE-A", "GATE-B"), quiet=True)

    section("G1c — an old-shape stamp file still reads (who-is-live's own reader, on a scratch folder)")
    S = SCRATCH / "g1c"
    if S.exists():
        shutil.rmtree(str(S))
    S.mkdir(parents=True)
    io.open(S / "live-scratch-haiku.json", "w", encoding="utf-8").write(json.dumps(
        {"machine": "scratch", "mind": "HAIKU", "effort": "EXTRA", "session": "OLD SHAPE TEST",
         "when": "2099-01-01T00:00:00+00:00"}))
    io.open(S / "live-scratch-opus.json", "w", encoding="utf-8").write(json.dumps(
        {"machine": "scratch", "mind": "OPUS", "when": "2099-01-01T00:00:00+00:00",
         "sessions": [{"title": "NEW A", "effort": "EXTRA", "when": "2099-01-01T00:00:00+00:00"},
                      {"title": "NEW B", "effort": "EXTRA", "when": "2099-01-01T00:00:00+00:00"}]}))
    try:
        wil = load_module(HUB / "tools" / "who-is-live.py", "wil_gate")
        wil.HUB = S
        rows = wil.stamps()
        titles = sorted(r["title"] for r in rows)
        print("   rows read:", titles)
        ok("old single-object file reads as one row, new list file as two",
           titles == ["NEW A", "NEW B", "OLD SHAPE TEST"], str(titles))
    except Exception as exc:
        ok("who-is-live.py stamps() importable and reads both shapes", False, repr(exc))


# --------------------------------------------------------------------------
# G2 — claims
# --------------------------------------------------------------------------

def g2():
    section("G2a — GATE-A claims button-up; an arriving session checks the arc (scratch hub)")
    run("A claims", "tools/claim.py", "--quiet", "--claim", "button-up", "GATE-A", *HUBARGS)
    run("arriving session, bare: HELD ON THIS MACHINE naming A + READER ROLE, no question",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", *HUBARGS, expect=2,
        must=("HELD ON THIS MACHINE", "GATE-A", "rerun with --title", "READER ROLE"), must_not=("?", "should I") + ASK_OWNER)
    run("arriving session with its own title: STOP naming A + READER ROLE",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", "--title", "GATE-OTHER", *HUBARGS, expect=2,
        must=("STOP:", "GATE-A", "READER ROLE"), must_not=("?",))
    run("A itself with --title: OK + HELD (yours)",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", "--title", "GATE-A", *HUBARGS, expect=0,
        must=("OK", "HELD: the button-up arc is yours"))
    run("A re-claiming is a refresh", "tools/claim.py", "--quiet", "--claim", "button-up", "GATE-A", *HUBARGS, must=("HELD",))
    run("B claiming is refused, exit 1", "tools/claim.py", "--quiet", "--claim", "button-up", "GATE-B", *HUBARGS, expect=1, must=("GATE-A",))
    run("B --take without --reason is refused", "tools/claim.py", "--quiet", "--claim", "button-up", "GATE-B", "--take", *HUBARGS, expect=1)

    section("G2d — a live hub ELSEWHERE never answers for another arc (the 09:20 failure, reproduced)")
    plant_elsewhere()
    run("hub arc, bare: STOP naming ELSEWHERE (the cross-machine STOP path)",
        "tools/who-is-live.py", "--pen", *HUBARGS, expect=2, must=("STOP:", "ELSEWHERE", ELSEWHERE_TITLE, "READER ROLE"), must_not=("?",))
    run("button-up while A holds it: HELD naming A — not the elsewhere hub's STOP",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", *HUBARGS, expect=2,
        must=("HELD ON THIS MACHINE", "GATE-A"), must_not=("claimed on the ELSEWHERE",))
    run("A itself, button-up, --title: OK + HELD despite the live hub elsewhere",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", "--title", "GATE-A", *HUBARGS, expect=0,
        must=("OK", "HELD: the button-up arc is yours"), must_not=("STOP:", "claimed on the ELSEWHERE"))
    run("a lane (--lane Exocortex/Gate) is OK: the hub stamp elsewhere is not its lane's",
        "tools/who-is-live.py", "--pen", "--lane", "Exocortex/Gate", *HUBARGS, expect=0,
        must=("OK", "FREE: the Exocortex/Gate arc is unclaimed"), must_not=("STOP:",))

    section("G2b — release → OK, with the hub still held elsewhere")
    run("A releases", "tools/claim.py", "--quiet", "--release", "button-up", "GATE-A", *HUBARGS, must=("RELEASED",))
    run("arriving session: OK + the claim command, no question — the elsewhere hub stays silent",
        "tools/who-is-live.py", "--pen", "--arc", "button-up", *HUBARGS,
        expect=0, must=("OK", "claim.py --claim button-up"), must_not=("?", "STOP:", "claimed on the ELSEWHERE"))
    run("the hub arc itself is still STOPped by ELSEWHERE (scoping cut nothing it should keep)",
        "tools/who-is-live.py", "--pen", "--arc", "hub", *HUBARGS, expect=2, must=("STOP:", "ELSEWHERE"))
    unplant_elsewhere()
    run("unplanted: hub arc reads OK again", "tools/who-is-live.py", "--pen", *HUBARGS, expect=0, must=("OK",), must_not=("claimed on the ELSEWHERE",))

    section("G2c — sweep (scratch hub; the live claims.json is other lanes' state)")
    live_before = io.open(HUB / "claims.json", encoding="utf-8").read() if (HUB / "claims.json").is_file() else ""
    run("scratch: GATE-A (stamped) claims rename", "tools/claim.py", "--quiet", "--claim", "rename", "GATE-A", *HUBARGS, must=("CLAIMED",))
    run("scratch: GHOST (never stamped) claims landing:TEST with --mind", "tools/claim.py", "--quiet",
        "--claim", "landing:TEST", "GHOST", "--mind", "OPUS", *HUBARGS, must=("CLAIMED",))
    run("scratch: default sweep keeps everything younger than 12 h, the unstamped included",
        "tools/claim.py", "--quiet", "--sweep", *HUBARGS, must=("nothing to sweep",))
    run("scratch: --strict drops GHOST (no stamp), keeps GATE-A (stamped)",
        "tools/claim.py", "--quiet", "--sweep", "--strict", *HUBARGS, must=("GHOST", "--strict"), must_not=('"GATE-A"',))
    run("scratch: age sweep --hours 0 drops GATE-A too", "tools/claim.py", "--quiet", "--sweep", "--hours", "0", *HUBARGS,
        must=("older than", '"GATE-A"'))
    live_after = io.open(HUB / "claims.json", encoding="utf-8").read() if (HUB / "claims.json").is_file() else ""
    ok("LIVE claims.json untouched by the scratch sweeps", live_before == live_after)

    section("G2e — BQ-025: the MIND on a pen is looked up, never defaulted (both recorded directions)")
    g2e()

    section("G2f — BQ-048 R1: a refresh records the identity, and the holds cache follows a claim")
    g2f()

    section("G1d — --off with a title leaves the other session live (scratch hub)")
    run("A switches off — B survives", "tools/i-am.py", "--quiet", "--off", "OPUS", "GATE-A", *HUBARGS, must=("GATE-B",))
    run("table: B still there, A gone", "tools/who-is-live.py", *HUBARGS, must=("GATE-B",), must_not=("GATE-A",))


def g2e():
    """The mind on a pen is looked up, never defaulted.

    THE BUG, on the record in both directions: claim.py's mind_for() ended with
    `return rows[0][1] if rows else "?"` — the NEWEST stamp on this machine,
    whatever session it belonged to. A session whose own title was not stamped
    therefore recorded whichever mind had stamped most recently: FABLE written
    against an OPUS session, and OPUS against a FABLE one. A wrong mind on a pen
    is worse than no mind — the reader role names it, the tree draws it, and the
    mail is addressed by it.

    THE FIX: the session's own identity first, then the title, then "?" and one
    plain line. Never a silent default.

    These stamps carry no session id (the gate clears the environment that would
    give one), so this proves the TITLE path and the "?" path, which is exactly
    where the bug lived. The identity path is proved in gate-comms P4."""
    S = SCRATCH / "g2e"
    if S.exists():
        shutil.rmtree(str(S))
    (S / "tools").mkdir(parents=True)
    copy_mail(S)
    A = ["--hub", str(S)]
    env = dict(os.environ)
    for key in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_HOST_SESSION_ID"):
        env.pop(key, None)                 # a stamp with no session id: the title path
    run("stamp a FABLE session", "tools/i-am.py", "--quiet", "FABLE", "EXTRA",
        "GATE-FABLE", *A, env=env, quiet=True)
    run("stamp an OPUS session AFTER it — the newest stamp here is now OPUS",
        "tools/i-am.py", "--quiet", "OPUS", "EXTRA", "GATE-OPUS", *A, env=env, quiet=True)
    run("the FABLE session claims: FABLE, not the newest stamp's OPUS",
        "tools/claim.py", "--quiet", "--claim", "rename", "GATE-FABLE", *A, env=env,
        must=("CLAIMED", "FABLE"), must_not=("· OPUS ·",))
    run("re-stamp FABLE so the newest stamp here is FABLE again",
        "tools/i-am.py", "--quiet", "FABLE", "EXTRA", "GATE-FABLE-2", *A, env=env, quiet=True)
    run("the OPUS session claims: OPUS, not the newest stamp's FABLE",
        "tools/claim.py", "--quiet", "--claim", "button-up", "GATE-OPUS", *A, env=env,
        must=("CLAIMED", "OPUS"), must_not=("· FABLE ·",))
    run("a session NO stamp carries records `?` and says so — never a default",
        "tools/claim.py", "--quiet", "--claim", "landing:BQ025", "GATE-NEVER-STAMPED", *A,
        env=env, must=("CLAIMED", "?", "mind unknown"))
    rows = read_json(S / "claims.json", [])
    got = dict((c.get("arc"), c.get("mind")) for c in rows)
    ok("both directions and the unknown are on record: %s" % got,
       got.get("rename") == "FABLE" and got.get("button-up") == "OPUS"
       and got.get("landing:BQ025") == "?", str(got))


# --------------------------------------------------------------------------
# G5b — never ask
# --------------------------------------------------------------------------

def g2f():
    """A CLAIM ON AN ARC THE SESSION
    ALREADY HOLDS RECORDS ITS IDENTITY EXACTLY AS A FIRST CLAIM DOES.

    The gap this closes: a row written before the postman existed — or by an
    older tool — carried no `session`, and every refresh left it that way, so
    every letter to that lane read `holder known by title only — it has not run
    an exocortex tool since the postman was installed`. The refresh is the one
    moment a long-running session touches its own claim, and it is where the id
    belongs.

    And with it, the HOLDS CACHE: the moment a claim changes,
    POST DIR says which session holds which lane and what command would arm its
    waiter, so the hook never parses claims.json on its hot path. claims.json
    stays the truth; the cache is corrected by every pass."""
    S = SCRATCH / "g2f"
    if S.exists():
        shutil.rmtree(str(S))
    (S / "tools").mkdir(parents=True)
    copy_mail(S)
    A = ["--hub", str(S)]
    SID = "ffffffff-1111-2222-3333-ffffffffffff"
    env = dict(os.environ, CLAUDE_CODE_SESSION_ID=SID, CLAUDE_CODE_HOST_SESSION_ID="local_g2f")
    run("a session with an id claims a lane", "tools/claim.py", "--quiet", "--claim",
        "landing:R1", "GATE-R1", *A, env=env, must=("CLAIMED",))
    rows = read_json(S / "claims.json", [])
    ok("the first claim records the session: %s" % [r.get("session") for r in rows],
       bool(rows) and rows[0].get("session") == SID)
    post = S / ".post"
    hold = post / "holds" / ("%s.json" % SID)
    ok("the holds cache is written beside it (%s)" % hold.name, hold.is_file())
    body = read_json(hold, {})
    ok("…naming the lane, the address and the command that would arm a waiter: %s"
       % {k: body.get(k) for k in ("address", "arm")},
       bool(body.get("cmd")) and "--wait" in str(body.get("cmd")) and bool(body.get("address")))
    ok("…and POST DIR is the SCRATCH hub's own .post, never this machine's real one (R4)",
       post.is_dir() and not str(post).startswith(str(Path.home() / ".exocortex")))

    for r in rows:                             # a row as an older tool left it
        for key in ("session", "host_session", "vendor"):
            r.pop(key, None)
    io.open(S / "claims.json", "w", encoding="utf-8").write(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    shutil.rmtree(str(post / "holds"), ignore_errors=True)
    run("the same session claims again — a refresh", "tools/claim.py", "--quiet", "--claim",
        "landing:R1", "GATE-R1", *A, env=env, must=("HELD", "refreshed"))
    rows = read_json(S / "claims.json", [])
    got = dict((k, rows[0].get(k)) for k in ("session", "host_session", "vendor")) if rows else {}
    ok("A REFRESH RECORDS session, host_session AND vendor, exactly as a first claim does: %s"
       % got,
       got.get("session") == SID and got.get("vendor") == "claude"
       and got.get("host_session") == "local_g2f")
    ok("…and refreshes the holds cache with it", hold.is_file())
    run("the session releases the lane", "tools/claim.py", "--quiet", "--release",
        "landing:R1", "GATE-R1", *A, env=env, must=("RELEASED",))
    ok("a released lane takes its holds row with it — it asks for no waiter", not hold.is_file())
    run("a claim from a session with NO id in its environment still works, as before",
        "tools/claim.py", "--quiet", "--claim", "landing:R1b", "GATE-R1B", *A,
        env=dict((k, v) for k, v in os.environ.items()
                 if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_HOST_SESSION_ID")),
        must=("CLAIMED",))
    rows = read_json(S / "claims.json", [])
    ok("…and writes no holds row at all, because nothing is ever guessed",
       not list((post / "holds").glob("*.json")) if (post / "holds").is_dir() else True)


def g5b():
    section("G5b — a held hub arc → an arriving hub session prints its reader line, no question (scratch hub)")
    run("plant a same-machine holder", "tools/claim.py", "--quiet", "--claim", "hub", "GATE-HUB-HOLDER", "--mind", "OPUS", *HUBARGS, must=("CLAIMED",))
    run("arriving hub session (no --title): HELD ON THIS MACHINE, naming the title to rerun with + READER ROLE, no question mark",
        "tools/who-is-live.py", "--pen", *HUBARGS, expect=2,
        must=("HELD ON THIS MACHINE", "rerun with --title", "GATE-HUB-HOLDER", "READER ROLE"),
        must_not=("?", "should I", "do you want", "shall I") + ASK_OWNER)
    run("the holder itself, with --title, is not stopped by its own claim",
        "tools/who-is-live.py", "--pen", "--title", "GATE-HUB-HOLDER", *HUBARGS, expect=0, must=("OK", "HELD: the hub arc is yours"))
    run("a second hub-titled session trying to claim hub is refused, exit 1, no question",
        "tools/claim.py", "--quiet", "--claim", "hub", "ACT — Exocortex/Gate: a SECOND hub window", "--mind", "OPUS", *HUBARGS,
        expect=1, must=("STOP", "READER ROLE"), must_not=("?",))
    run("release the planted holder", "tools/claim.py", "--quiet", "--release", "hub", "GATE-HUB-HOLDER", *HUBARGS, must=("RELEASED",))
    plant_elsewhere()
    run("arriving hub session while the hub is held ELSEWHERE: STOP + READER ROLE, no question",
        "tools/who-is-live.py", "--pen", "--title", "ACT — Exocortex/Gate: arriving hub", *HUBARGS, expect=2,
        must=("STOP:", "ELSEWHERE", "READER ROLE"), must_not=("?", "should I") + ASK_OWNER)
    unplant_elsewhere()


def cleanup():
    section("cleanup of test residue")
    run("scratch: B switches off — the OPUS test list empties to an off stamp", "tools/i-am.py", "--quiet", "--off", "OPUS", "GATE-B", *HUBARGS)
    run("scratch: no GATE rows left", "tools/who-is-live.py", *HUBARGS, must_not=("GATE-A", "GATE-B"))
    run("scratch: no GATE claims left", "tools/claim.py", "--quiet", "--list", *HUBARGS, must_not=("GATE-",))
    run("LIVE folder: no GATE rows", "tools/who-is-live.py", must_not=("GATE-A", "GATE-B", "GATE-HUB", "ELSEWHERE"), quiet=True)
    run("LIVE folder: no GATE claims", "tools/claim.py", "--quiet", "--list", must_not=("GATE-", "elsewhere"), quiet=True)
    ok("LIVE folder: no planted elsewhere stamp", not (HUB / "live-elsewhere-fable.json").exists())


# --------------------------------------------------------------------------
# G3 — the union, in sync.py's own test mode on a scratch copy
# --------------------------------------------------------------------------

def g3():
    section("G3 — append-only union, scratch copy of the sync package (TEST MODE, git skipped)")
    SYNC, MANIFEST = sync_source()
    if SYNC is None:
        ok("the sync package was found (the older layout's folder, or this hub's sync/)", False,
           "neither %s nor %s holds sync.py with a manifest"
           % (Path.home() / "orchestrator-sync", HUB / "sync"))
        return
    print("   sync package: %s · manifest: %s" % (SYNC, MANIFEST.name))
    ROOT = SCRATCH / "g3"
    REPO, LIVE = ROOT / "repo", ROOT / "live"
    FAKE = LIVE / "fake" / "Exocortex"           # redirect() maps /fake/Exocortex (C:\fake\...) here
    FILES = ["INBOX.md", "STATUS.md", "dossier/TAUGHT.md", "watchers/LESSON-PROPOSALS-gate.md"]
    HEADER = {"INBOX.md": "# INBOX\n\n", "STATUS.md": "# STATUS\n\n## Now\n\n",
              "dossier/TAUGHT.md": "# TAUGHT\n\n", "watchers/LESSON-PROPOSALS-gate.md": "# LESSON PROPOSALS\n\n"}
    SEED = "- 2026-09-07 · to: SOUTH/hub · seed · a line both machines already had · none\n"

    def w(p, text):
        p.parent.mkdir(parents=True, exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="").write(text)

    def r(p):
        return io.open(p, encoding="utf-8", newline="").read()

    if ROOT.exists():
        shutil.rmtree(str(ROOT))
    (REPO / "orchestrator").mkdir(parents=True)
    FAKE.mkdir(parents=True)
    shutil.copy2(str(SYNC), str(REPO / "sync.py"))
    shutil.copy2(str(MANIFEST), str(REPO / "sync-manifest.json"))
    anchor = "C:\\fake" if os.name == "nt" else "/fake"
    sep = "\\" if os.name == "nt" else "/"
    w(REPO / "machine.json", json.dumps({
        "name": "gate", "os": "scratch", "bootstrapped": "2026-09-08T00:00:00Z",
        "roots": {"home": anchor, "orchestrator": anchor + sep + "Exocortex", "claude": anchor + sep + ".claude",
                  "codex": anchor + sep + ".codex", "projects": anchor + sep + "Projects"}}, indent=2))
    for rel in FILES:
        w(FAKE / rel, HEADER[rel] + SEED)
        w(REPO / "orchestrator" / rel, HEADER[rel] + SEED)
    # The scratch brain is a repository, as a real brain clone is: the sync
    # package tells the older layout by its own marks, and a clone is one of
    # them. TEST MODE still runs no git command against it.
    subprocess.run(["git", "init", "-q", str(REPO)], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    env = dict(os.environ, ORCHSYNC_TEST_ROOT=str(LIVE))

    first = run("1st pull — records the baseline state", "sync.py", "pull", cwd=REPO, env=env,
                must=("TEST MODE", "git: skipped"))

    stamped = SEED.rstrip("\n") + " · delivered: 2026-09-08T07:10-07:00 by NORTH hub\n"
    w(REPO / "orchestrator" / "INBOX.md", HEADER["INBOX.md"] + stamped)                 # repo: marked delivered
    w(FAKE / "INBOX.md", HEADER["INBOX.md"] + SEED + "- 2026-09-08 · to: NORTH/hub · exocortex · a line only this side wrote · none\n")
    for rel, a, b in (("dossier/TAUGHT.md", "- 2026-09-08 repo-side lesson\n", "- 2026-09-08 live-side lesson\n"),
                      ("watchers/LESSON-PROPOSALS-gate.md", "- 2026-09-08 repo-side proposal\n", "- 2026-09-08 live-side proposal\n")):
        w(REPO / "orchestrator" / rel, HEADER[rel] + SEED + a)
        w(FAKE / rel, HEADER[rel] + SEED + b)
    w(REPO / "orchestrator" / "STATUS.md", HEADER["STATUS.md"] + "repo edit\n")
    w(FAKE / "STATUS.md", HEADER["STATUS.md"] + "live edit\n")
    s_repo, s_live = r(REPO / "orchestrator" / "STATUS.md"), r(FAKE / "STATUS.md")

    out = run("2nd pull — both sides moved", "sync.py", "pull", cwd=REPO, env=env,
              must=("merged (append-only union)", "CONFLICT"))
    for rel in ("INBOX.md", "dossier/TAUGHT.md", "watchers/LESSON-PROPOSALS-gate.md"):
        live_txt, repo_txt = r(FAKE / rel), r(REPO / "orchestrator" / rel)
        ok("%s reported merged, not conflicted" % rel,
           ("merged (append-only union): orchestrator/%s" % rel) in out and
           not any(("orchestrator/%s" % rel) in l and "merged" not in l for l in out.splitlines()))
        ok("%s identical on both sides, header intact" % rel, live_txt == repo_txt and live_txt.startswith(HEADER[rel]))
    inbox = r(FAKE / "INBOX.md")
    ok("INBOX keeps the DELIVERED copy of the seed and drops the plain duplicate",
       "delivered: 2026-09-08T07:10-07:00 by NORTH hub" in inbox and inbox.count("· seed ·") == 1)
    ok("INBOX kept the live-only line", "a line only this side wrote" in inbox)
    for rel, a, b in (("dossier/TAUGHT.md", "repo-side lesson", "live-side lesson"),
                      ("watchers/LESSON-PROPOSALS-gate.md", "repo-side proposal", "live-side proposal")):
        txt = r(FAKE / rel)
        ok("%s has both lines, the other machine's first, seed once" % rel,
           a in txt and b in txt and txt.index(a) < txt.index(b) and txt.count("· seed ·") == 1)
    ok("STATUS.md still CONFLICTs and is untouched on both sides",
       "orchestrator/STATUS.md" in out and "merged (append-only union): orchestrator/STATUS.md" not in out
       and r(FAKE / "STATUS.md") == s_live and r(REPO / "orchestrator" / "STATUS.md") == s_repo)
    third = run("3rd pull — quiet: the union settled the state", "sync.py", "pull", cwd=REPO, env=env,
                must_not=("merged (append-only union)",), quiet=True)


def sync_source():
    """(sync.py, manifest) the way this machine's own sync is found: the older
    layout keeps both in its folder under the home; a program tree keeps sync.py
    in the hub's sync/ folder, and there the program's own manifest.base.json
    stands in for a brain that has no manifest of its own yet (the union rules
    under test — the append-only list — are in it). (None, None) when neither."""
    older = Path.home() / "orchestrator-sync"
    if (older / "sync.py").is_file() and (older / "sync-manifest.json").is_file():
        return older / "sync.py", older / "sync-manifest.json"
    program = HUB / "sync"
    if (program / "sync.py").is_file() and (program / "manifest.base.json").is_file():
        return program / "sync.py", program / "manifest.base.json"
    return None, None


def main(argv):
    if "--help" in argv:
        print(__doc__)
        return 0
    print("gate-coordination · hub %s · python %s" % (HUB, sys.version.split()[0]))
    fresh_scratch_hub()
    g1()
    g2()
    g5b()
    cleanup()
    if "--skip-g3" not in argv:
        g3()
    print("\n===== GATES =====")
    n_ok = sum(1 for _, good in checks if good)
    print("  %d checks · %d passed · %d failed" % (len(checks), n_ok, len(fails)))
    for f in fails:
        print("  FAIL  %s" % f)
    print("  scratch: %s (hermetic: every stamp/claim check ran in its hub/ subfolder; the one live touch, G1b, is switched off again)%s"
          % (SCRATCH, "" if "--keep" in argv else " — removed; --keep holds it"))
    return 1 if fails else 0


def remove_own_worlds():
    """Every world this gate made, removed — whatever way the run ended: done,
    failed or raised (a run ended from outside, at a runner's limit, is the
    runner's to clean: it gives each gate a temporary folder of its own)."""
    shutil.rmtree(str(SCRATCH), ignore_errors=True)


if __name__ == "__main__":
    try:
        RESULT = main(sys.argv[1:])
    finally:
        if "--keep" not in sys.argv[1:]:
            remove_own_worlds()
    sys.exit(RESULT)
