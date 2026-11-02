#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claim.py — the pen made visible: which session holds which arc of work.

    python3 tools/claim.py --claim hub "ACT — Exocortex: hub"
    python3 tools/claim.py --release hub "ACT — Exocortex: hub"
    python3 tools/claim.py --list
    python3 tools/claim.py --claim-file PATH --session ID [--title TITLE]
    python3 tools/claim.py --release-file PATH --session ID
    python3 tools/claim.py --release-files --session ID
    python3 tools/claim.py --files
    python3 tools/claim.py --sweep-files
    # File state: ~/.exocortex/file-claims.json (never synced).
    # LIVE = transcript touched within 30 min; sweep = idle over 12 h.
    python3 tools/claim.py --sweep            # drops claims older than --hours (12)
    python3 tools/claim.py --sweep --strict   # …and claims whose holder has no live stamp
    (--hub <folder> points every verb at another hub folder — the gates run on a scratch copy)
    (--quiet takes or releases the pen without telling the other machine — gate runs)

Writes claims.json in the hub folder (synced with the brain): a list of
{"arc","machine","mind","title","since"}. An ARC is a short free-form token —
hub · button-up · rename · landing:AB-TX-008 · Project/Lane — compared without
regard to case. The MIND is not asked for: it is looked up from this machine's
own i-am.py stamps by session title.

A claim younger than --hours (12) held by another session refuses a second
claim: exit 1, the holder printed, and the reader role stated. --take with a
--reason overrides it and mails the holder (never silently). Lane claims remain a convention read at each ritual. The per-file
verbs below serialize their machine-local state with a short kernel lock;
they never lock the edited document itself.

The decision is never put to the owner — it is automatic: a session claims
the free arc, or takes the reader role, and says which in one line, so two
sessions (of one vendor or two) never run the same work at once.

TAKING A PEN ANNOUNCES ITSELF: --claim writes ONE
line to every OTHER machine's hub — "<MACHINE> <MIND> took the <arc> pen ·
\"<title>\"" — and --release writes the matching "released" line, through the
same tools/mail.py that carries a takeover letter. Refreshing a claim already
yours says nothing. A fleet of one machine sends nothing, --quiet sends nothing,
and a letter that fails never fails the claim.

Stdlib only, OS-neutral, no user paths: the machine's name and the hub folder
come from the machine record the path resolver finds (tools/exo_paths.py),
exactly as every other tool reads them. A machine whose record names no
machine claims nothing: a claim held on nobody is a claim nobody can answer.
"""
import argparse, io, json, subprocess, sys
sys.dont_write_bytecode = True
from datetime import datetime
from pathlib import Path

try:                                   # Windows consoles may be cp437: never crash on the plate's "·"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
# A staged candidate may use the hub's read-only dependencies; an installed
# copy and a gate world find those dependencies beside themselves first.
for _parent in Path(__file__).resolve().parents:
    _deps = _parent / "tools"
    if (_deps / "exo_paths.py").is_file():
        sys.path.append(str(_deps))
        break
from exo_paths import paths            # noqa: E402  the one answer to "where is the record"

try:                                   # WHICH SESSION holds this pen
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_common import session_identity, identity_or_nonce, load_postman
except Exception:                      # claim.py standing alone claims exactly as before
    def session_identity(env=None): return {}
    def identity_or_nonce(title="", arcs=(), hub=None): return {}, ""
    def load_postman(hub=None): return None


def refresh_holds(folder, name):
    """THE HOLDS CACHE: the moment a claim changes, say in
    POST DIR which session holds which lane, so the hook can ask an idle window
    to arm its own waiter WITHOUT parsing claims.json on its hot path.

    claims.json stays the truth — every pass reconciles the cache against it in
    both directions — and this only spares the hook a parse. No postman beside
    this file, or no POST DIR at all: nothing is written and nothing is said."""
    pm = load_postman(folder)
    if pm is None:
        return
    try:
        try:
            post = pm.post_dir(hub=str(folder))
        except TypeError:              # an older postman, before R4
            post = pm.post_dir()
        pm.holds_reconcile(post, folder, pm.read_claims(folder), pm.read_ears(folder), name)
    except Exception:
        pass


def machine():
    """(this machine's name, its recorded roots) from the machine record the
    path resolver finds — ("unknown", {}) when no record names a machine."""
    try:
        record = paths(tool_file=__file__)
        return record["machine"], dict(record["roots"])
    except Exception:
        return "unknown", {}


def unnamed_line():
    """The one sentence a claim on an unnamed machine gets, instead of a claim."""
    try:
        found = paths(tool_file=__file__)["machine_file"]
    except Exception:
        found = None
    where = ("the machine record %s names no machine" % found) if found else \
        "no machine record was found for this machine"
    return ("STOP: %s, so a claim made here would be held on nobody — run the installer, "
            "then claim again; nothing was claimed." % where)


def now_iso():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def parse_iso(text):
    t = str(text or "").strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(t)
    except Exception:
        return None
    return d.astimezone() if d.tzinfo is None else d


def age_h(since):
    d = parse_iso(since)
    if d is None:
        return float("inf")
    return (datetime.now().astimezone() - d).total_seconds() / 3600.0


# --------------------------------------------------------------------------
# stamps: where the mind comes from
# --------------------------------------------------------------------------

def stamp_sessions(d):
    """Every session in one i-am.py stamp, whichever shape it is in: the
    `sessions` list the current shape carries, or the single session an older
    file carries at its top level. An off stamp holds none."""
    if not isinstance(d, dict):
        return []
    raw = d.get("sessions")
    if isinstance(raw, list):
        return [{"title": str(s.get("title") or ""), "when": str(s.get("when") or ""),
                 "session": str(s.get("session") or "")}
                for s in raw if isinstance(s, dict)]
    if d.get("off"):
        return []
    return [{"title": str(d.get("session") or ""), "when": str(d.get("when") or ""),
             "session": ""}]


def stamp_rows(folder, only_machine=None):
    """(machine, mind, title, age in hours) for every stamped session in the
    hub folder, newest first. The whole folder, not just this machine: the
    stamps are synced, so a claim by the other machine can be checked here."""
    rows = []
    for f in sorted(folder.glob("live-*-*.json")):
        if f.name.startswith("live-sessions-"):
            continue                # the pulse's own file
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        if not isinstance(d, dict) or not d.get("mind"):
            continue
        mch = str(d.get("machine") or "").lower() or f.stem[5:].split("-")[0]
        if only_machine and mch != only_machine:
            continue
        for s in stamp_sessions(d):
            rows.append((mch, str(d.get("mind") or "").upper(), s["title"], age_h(s["when"]),
                         s.get("session") or ""))
    rows.sort(key=lambda r: r[3])
    return rows


def mind_for(folder, name, title):
    """The mind holding this session, looked up rather than asked for — BY SESSION
    IDENTITY FIRST, then by title, and NEVER by a silent default.

    The bug this closes, both directions on the record: the old last line fell
    back to `rows[0][1]`, the NEWEST stamp on this machine whatever session it
    belonged to.  So a session whose own title was not stamped recorded whichever
    mind had stamped most recently — FABLE written against an OPUS session, and
    OPUS against a FABLE one.  A wrong mind on a pen is worse than no mind: the
    reader role names it, the tree draws it, and the mail is addressed by it.

    Returns (mind, one line to say) — "?" and a sentence when nothing resolves."""
    rows = stamp_rows(folder, only_machine=name)
    me = str(session_identity().get("session") or "")
    if me:
        for _mch, mind, _ttl, _age, sid in rows:
            if sid and sid == me:
                return mind, ""
    want = str(title or "").strip().lower()
    for _mch, mind, ttl, _age, _sid in rows:
        if ttl.strip().lower() == want:
            return mind, ""
    return "?", ("  mind unknown — no stamp here carries this session or the title \"%s\", "
                 "so the pen is recorded as \"?\" (run tools/i-am.py <MIND> <EFFORT> "
                 "\"<title>\" and claim again to name it)" % title)


def live_holders(folder, hours):
    """(machine, title) of every session stamped live inside the window — what
    --sweep checks a claim against."""
    out = set()
    for mch, _mind, title, age, _sid in stamp_rows(folder):
        if age < hours and title.strip():
            out.add((mch, title.strip().lower()))
    return out


# --------------------------------------------------------------------------
# claims.json
# --------------------------------------------------------------------------

def read_claims(path):
    """A missing or malformed file is no claim at all — never a crash."""
    try:
        d = json.loads(io.open(path, encoding="utf-8").read())
    except Exception:
        return []
    if not isinstance(d, list):
        return []
    return [c for c in d if isinstance(c, dict) and c.get("arc")]


def write_claims(path, claims):
    """Sorted by arc then since, indented, with a trailing newline, so the
    brain sync sees stable bytes and not a reshuffle every write."""
    rows = sorted(claims, key=lambda c: (str(c.get("arc", "")).lower(), str(c.get("since", ""))))
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n")


def same_arc(claim, arc):
    return str(claim.get("arc", "")).strip().lower() == str(arc).strip().lower()


def is_holder(claim, name, title):
    return (str(claim.get("machine", "")).lower() == name
            and str(claim.get("title", "")).strip().lower() == str(title).strip().lower())


def describe(claim):
    return "%s · %s · %s · %.1f h ago · \"%s\"" % (
        claim.get("arc", ""), str(claim.get("machine") or "unknown").upper(),
        claim.get("mind") or "unknown", age_h(claim.get("since")), claim.get("title", ""))


# --------------------------------------------------------------------------
# the letter to the holder
# --------------------------------------------------------------------------

def lane_token(title):
    """The lane token of a ritual title: 'ACT — Project/Lane: purpose' ->
    'Project/Lane'. A title without both the dash and the colon has none."""
    t = str(title or "")
    if "—" not in t or ":" not in t:
        return ""
    return t.split("—", 1)[1].split(":", 1)[0].strip()


def holder_address(claim):
    """Where a letter to the holder goes: <MACHINE>/hub for the hub arc or a
    title with no lane in it, else <MACHINE>/<lane token>."""
    mch = str(claim.get("machine") or "unknown").upper()
    if same_arc(claim, "hub"):
        return "%s/hub" % mch
    token = lane_token(claim.get("title"))
    return "%s/%s" % (mch, token) if token else "%s/hub" % mch


def run_mail(folder, args, on_fail):
    """mail.py, run once. `folder` is the hub the letter lands in; the tool
    itself travels beside this file, so a scratch copy mails with its own copy
    and falls back to the hub's tools/ when it stands alone. Returns the output
    or None; never raises — a letter is never allowed to fail a claim."""
    tool = Path(__file__).resolve().parent / "mail.py"
    if not tool.is_file():
        tool = Path(folder) / "tools" / "mail.py"
    if not tool.is_file():
        print("  %s: %s is missing" % (on_fail, tool))
        return None
    try:
        r = subprocess.run([sys.executable, str(tool)] + [str(a) for a in args] + ["--hub", str(folder)],
                           capture_output=True, text=True)
    except Exception as exc:
        print("  %s: %s" % (on_fail, exc))
        return None
    if r.returncode != 0:
        print("  %s: mail.py exited %d" % (on_fail, r.returncode))
        for line in ((r.stderr or r.stdout) or "").strip().splitlines()[:3]:
            print("    %s" % line)
        return None
    return ((r.stdout or "") + (r.stderr or "")).strip()


def announce(folder, text, quiet=False):
    """One line to every other machine's hub. mail.py owns the fleet, the
    addresses and the push; this tool only says what happened."""
    if quiet:
        return
    out = run_mail(folder, ["--announce", text], "not announced")
    for line in ((out or "").splitlines() or ["mail.py said nothing"]):
        print("  %s" % line)


def pen_line(verb, machine_name, mind, arc, title):
    return "%s %s %s the %s pen · \"%s\"" % (str(machine_name).upper(), mind or "?", verb, arc, title)


def mail_holder(folder, claim, taker, reason):
    """One line into INBOX.md addressed to the holder. --no-push: the taking
    session pushes the brain on its own schedule. A letter that fails never
    fails the claim; it is reported and the claim stands."""
    mailpy = folder / "tools" / "mail.py"
    if not mailpy.is_file():
        print("  letter NOT sent: %s is missing — tell the holder by hand" % mailpy)
        return
    to = holder_address(claim)
    text = ("the %s arc was taken over by %s (%s) in \"%s\""
            % (claim.get("arc", ""), taker["machine"].upper(), taker["mind"], taker["title"]))
    action = "reason: %s — stop writing that arc's files, or reply by mail if this is wrong" % reason
    try:
        r = subprocess.run([sys.executable, str(mailpy), "--send", to, "Exocortex", text, action, "--no-push"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            print("  letter sent to %s (unpushed — it rides your next brain push)" % to)
        else:
            print("  letter NOT sent to %s: mail.py exited %d — tell the holder by hand"
                  % (to, r.returncode))
            for line in (r.stderr or "").strip().splitlines()[:3]:
                print("    %s" % line)
    except Exception as exc:
        print("  letter NOT sent to %s: %s — tell the holder by hand" % (to, exc))


# --------------------------------------------------------------------------
# verbs
# --------------------------------------------------------------------------

def reader_role_line():
    return ("READER ROLE: verify, consult, and report by mail to the holder "
            "(tools/mail.py --send %s ...). Write none of that arc's STATUS, openers or "
            "TREE.md from here. This decision is automatic and is never put to the owner.")


def cmd_claim(path, folder, name, arc, title, mind, take, reason, hours, quiet=False):
    claims = read_claims(path)
    mine = [c for c in claims if same_arc(c, arc) and is_holder(c, name, title)]
    if mine:
        # A REFRESH RECORDS THE IDENTITY EXACTLY AS A FIRST CLAIM
        # DOES. Without this, a session that claimed before the postman was
        # installed — or one whose row was written by an older tool — kept a
        # claim with no `session` on it however often it refreshed, and every
        # letter to that lane read `holder known by title only`.
        ident, id_line = identity_or_nonce(title=title, arcs=[str(arc).strip()], hub=folder)
        for c in mine:
            c["since"] = now_iso()
            if mind:
                c["mind"] = mind
            elif str(c.get("mind") or "?").strip() in ("", "?"):
                # A claim made BEFORE its stamp carried "?" for
                # its mind forever, however often it refreshed — resolve it now the
                # same way a first claim does (by session, then title; never a default).
                who, _said = mind_for(folder, name, title)
                if who and who != "?":
                    c["mind"] = who
            for k in ("session", "host_session", "vendor"):
                if ident.get(k):
                    c[k] = ident[k]
        write_claims(path, claims)
        print("HELD: %s is already yours — refreshed. %s" % (arc, describe(mine[0])))
        if id_line:
            print(id_line)
        refresh_holds(folder, name)
        return 0

    others = [c for c in claims if same_arc(c, arc) and not is_holder(c, name, title)]
    fresh = [c for c in others if age_h(c.get("since")) < hours]
    stale = [c for c in others if age_h(c.get("since")) >= hours]

    if fresh and not take:
        held = sorted(fresh, key=lambda c: age_h(c.get("since")))[0]
        print("STOP: %s is claimed — %s" % (arc, describe(held)))
        print(reader_role_line() % holder_address(held))
        return 1
    if take and not reason:
        print("STOP: --take needs --reason \"<why>\" — a takeover is recorded and mailed, never silent.")
        return 1

    said = ""
    if mind:
        who = mind
    else:
        who, said = mind_for(folder, name, title)
    entry = {"arc": str(arc).strip(), "machine": name, "mind": who,
             "title": str(title).strip(), "since": now_iso()}
    # WHICH SESSION holds it: the environment when the vendor says so,
    # else a printed nonce the postman binds from the transcript. Never a guess.
    ident, id_line = identity_or_nonce(title=title, arcs=[str(arc).strip()], hub=folder)
    for k in ("session", "host_session", "vendor"):
        if ident.get(k):
            entry[k] = ident[k]
    for c in stale:
        claims.remove(c)
        print("  dropped a stale claim (older than %g h): %s" % (hours, describe(c)))
    if fresh:
        for c in fresh:
            claims.remove(c)
            print("TAKEN: %s was held by %s" % (arc, describe(c)))
            mail_holder(folder, c, entry, reason)
    claims.append(entry)
    write_claims(path, claims)
    print("CLAIMED: %s" % describe(entry))
    if said:
        print(said)                    # a mind that could not be resolved is said, never defaulted
    if id_line:
        print(id_line)                 # the one added line, only where the vendor gives no id
    refresh_holds(folder, name)
    if not fresh:                      # a takeover's letter to the holder IS its announcement
        announce(folder, pen_line("took", name, who, entry["arc"], entry["title"]), quiet)
    return 0


def cmd_release(path, folder, name, arc, title, quiet=False):
    claims = read_claims(path)
    gone = [c for c in claims if same_arc(c, arc) and is_holder(c, name, title)]
    if not gone:
        print("NOTHING HELD: %s was not claimed by \"%s\" on %s — nothing to release."
              % (arc, title, name.upper()))
        return 0
    for c in gone:
        claims.remove(c)
        print("RELEASED: %s" % describe(c))
    write_claims(path, claims)
    refresh_holds(folder, name)        # a released lane stops asking for a waiter
    for c in gone:                     # the mind is the claim's own, not a fresh guess
        announce(folder, pen_line("released", name,
                                  c.get("mind") or mind_for(folder, name, title)[0],
                                  c.get("arc", arc), c.get("title", title)), quiet)
    return 0


def cmd_list(path, hours):
    claims = read_claims(path)
    if not claims:
        print("no claims on record (%s)" % path.name)
        return 0
    rows = sorted(claims, key=lambda c: (str(c.get("arc", "")).lower(), str(c.get("since", ""))))
    print("%-22s %-6s %-7s %8s  %s" % ("ARC", "WHERE", "MIND", "AGE", "TITLE"))
    for c in rows:
        h = age_h(c.get("since"))
        print("%-22s %-6s %-7s %6.1f h%s  %s" % (
            str(c.get("arc", ""))[:22], str(c.get("machine") or "?").upper()[:6],
            str(c.get("mind") or "?")[:7], h, " stale" if h >= hours else "      ",
            c.get("title", "")))
    return 0


def cmd_sweep(path, folder, hours, strict=False):
    """Age reaps: a claim older than --hours is dropped, and by default that is
    all. A holder with no stamp is a first-class case (a lane whose opener
    claims with --mind and stamps nothing), and a session that stamped and
    then died leaves its stamp LIVE, so absence proves little and would wipe
    live lanes' claims. --strict also
    drops claims whose holder shows no live stamp, for a fleet where every
    session stamps."""
    claims = read_claims(path)
    holders = live_holders(folder, hours)
    keep, dropped = [], []
    for c in claims:
        h = age_h(c.get("since"))
        key = (str(c.get("machine", "")).lower(), str(c.get("title", "")).strip().lower())
        if h >= hours:
            dropped.append((c, "older than %g h" % hours))
        elif strict and key not in holders:
            dropped.append((c, "its holder has no live stamp on record (--strict)"))
        else:
            keep.append(c)
    if not dropped:
        print("nothing to sweep — %d claim(s), every holder still live" % len(claims))
        return 0
    for c, why in dropped:
        print("SWEPT: %s — %s" % (describe(c), why))
    write_claims(path, keep)
    print("swept %d claim(s); %d left" % (len(dropped), len(keep)))
    return 0


# --------------------------------------------------------------------------
# Machine-local file claims. Lane verbs above are unchanged.
# --------------------------------------------------------------------------
import os
import re
import shlex
import signal
import tempfile
import time
from contextlib import contextmanager

FILE_LIVE_SECONDS = 30 * 60
FILE_SWEEP_SECONDS = 12 * 60 * 60


def file_context(hub=None, deadline=None):
    from exo_common import machine_paths
    record = machine_paths(tool_file=__file__)
    name = record['machine']
    if name == 'unknown':
        raise ValueError('machine record names no machine')
    roots = record['roots']
    return {'hub': Path(hub or record['hub']).resolve(),
            'machine': name, 'home': Path.home(),
            'transcripts': Path(roots.get('claude') or Path.home() / '.claude') / 'projects',
            'deadline': deadline or time.monotonic() + 0.80}


def file_budget(ctx):
    left = ctx['deadline'] - time.monotonic()
    if left <= 0:
        raise TimeoutError('file-claim deadline exceeded')
    return left


def file_log(ctx, line):
    folder = ctx['home'] / '.exocortex'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'file-claims.log').open('a', encoding='utf-8') as stream:
        stream.write(now_iso() + ' · ' + ' '.join(str(line).split()) + '\n')


def file_text(value, field):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('invalid ' + field)
    return value


def file_session(value):
    value = file_text(value, 'session')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', value):
        raise ValueError('invalid session id')
    return value


def file_path(value, cwd=None):
    value = file_text(value, 'file path')
    path = Path(value).expanduser()
    if not path.is_absolute():
        base = Path(file_text(str(cwd) if cwd is not None else None, 'cwd'))
        if not base.is_absolute():
            raise ValueError('cwd is not absolute')
        path = base / path
    # strict=False is necessary for Write creating a new file.
    return os.path.normcase(str(path.resolve()))


@contextmanager
def file_lock(ctx):
    """Kernel-owned lock survives crashes; short contention fails open."""
    folder = ctx['home'] / '.exocortex'
    folder.mkdir(parents=True, exist_ok=True)
    lock = (folder / 'file-claims.lock').open('a+b')
    acquired = False
    try:
        until = time.monotonic() + min(0.15, file_budget(ctx))
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                import errno
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= until:
                    raise TimeoutError('file-claim lock busy')
                time.sleep(0.005)
        yield folder / 'file-claims.json'
    finally:
        if acquired:
            if os.name == 'nt':
                import msvcrt
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def read_file_claims(path):
    """Never interpret corrupt ownership as a free file or overwrite it."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('file-claims state exceeds 4 MiB')
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get('claims'), list):
        raise ValueError('malformed file-claims state')
    seen = set()
    for row in data['claims']:
        if not isinstance(row, dict):
            raise ValueError('malformed file-claim row')
        for key in ('path', 'session', 'title', 'since', 'machine'):
            file_text(row.get(key), key)
        file_session(row['session'])
        if not Path(row['path']).is_absolute() or file_path(row['path']) != row['path']:
            raise ValueError('file claim path is not canonical')
        if parse_iso(row['since']) is None or row['path'] in seen:
            raise ValueError('invalid date or duplicate file claim')
        seen.add(row['path'])
    return data['claims']


def write_file_claims(path, rows):
    """Same-directory replace leaves either the old complete state or the new."""
    fd, temporary = tempfile.mkstemp(prefix='.file-claims-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'claims': sorted(rows, key=lambda r: r['path'])}, stream,
                      ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def file_title(ctx, session, explicit=None):
    if explicit is not None:
        return file_text(explicit, 'title')
    lane_path = ctx['hub'] / 'claims.json'
    data = json.loads(lane_path.read_text(encoding='utf-8'))
    if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
        raise ValueError('malformed lane claims')
    matches = [r for r in data if r.get('session') == session and
               str(r.get('machine', '')).lower() == ctx['machine'].lower()]
    matches.sort(key=lambda r: str(r.get('since', '')), reverse=True)
    return file_text(matches[0].get('title'), 'title') if matches else session[:8]


def file_age(ctx, session):
    """Search one directory level only; never trust a supplied transcript path.

    Holders can work in different projects. Multiple matches use the freshest
    transcript. Missing evidence is an error, not proof of idleness.
    """
    file_session(session)
    newest = None
    with os.scandir(ctx['transcripts']) as dirs:
        for entry in dirs:
            file_budget(ctx)
            if not entry.is_dir(follow_symlinks=False):
                continue
            candidate = Path(entry.path) / (session + '.jsonl')
            try:
                stamp = candidate.stat().st_mtime
            except FileNotFoundError:
                continue
            newest = stamp if newest is None else max(newest, stamp)
    if newest is None:
        raise FileNotFoundError('holder transcript missing: ' + session)
    return max(0.0, time.time() - newest)


def file_address(row):
    # Keep Project/Lane intact: mail.py canonicalizes '-' and '/' and the
    # existing lane-claim grammar already uses this complete token.
    token = lane_token(row['title'])
    if '/' not in token:
        token = 'hub'
    return row['machine'].upper() + '/' + token


def file_refusal(row, age, title):
    command = 'python3 tools/mail.py --send {} {} {} "say when free"'.format(
        shlex.quote(file_address(row)), shlex.quote(title),
        shlex.quote('FILE HOLD request: ' + row['path']))
    return ('HELD — %s is held by «%s» (live %d min ago) · ask it: %s'
            ' · or wait for its sha letter' % (row['path'], row['title'], age // 60, command))


def file_letter(ctx, row, text, title):
    """One local mail invocation; no push, bounded, no orphan postman on timeout."""
    mail = ctx['hub'] / 'tools' / 'mail.py'
    if not mail.is_file():
        raise FileNotFoundError('mail.py missing')
    args = [sys.executable, '-B', str(mail), '--send', file_address(row), title,
            text, 'no reply needed — FYI', '--no-push', '--hub', str(ctx['hub'])]
    proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=(os.name != 'nt'))
    try:
        code = proc.wait(timeout=max(0.01, min(0.35, file_budget(ctx) - 0.08)))
        if code:
            raise RuntimeError('mail.py exited %d' % code)
    finally:
        if proc.poll() is None:
            if os.name != 'nt':
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=0.10)


def claim_file(ctx, path, session, title=None, cwd=None):
    session = file_session(session)
    path = file_path(path, cwd)
    title = file_title(ctx, session, title)
    taken = None
    with file_lock(ctx) as state:
        rows = read_file_claims(state)
        if rows is None:
            file_log(ctx, 'WARN — file-claims state missing; initializing empty state')
            rows = []
        held = next((r for r in rows if r['path'] == path), None)
        if held and held['session'] == session:
            return 'mine', ''
        if held:
            age = file_age(ctx, held['session'])
            if age <= FILE_LIVE_SECONDS:
                line = file_refusal(held, age, title)
                file_log(ctx, line)
                return 'held', line
            taken = ('FILE TAKEN — %s, held by «%s» since %s, idle %d min; taken by «%s»'
                     % (path, held['title'], held['since'], age // 60, title))
        entry = {'path': path, 'session': session, 'title': title,
                 'since': now_iso(), 'machine': ctx['machine']}
        file_budget(ctx)
        write_file_claims(state, [r for r in rows if r['path'] != path] + [entry])
        if taken:
            file_log(ctx, taken)
            # Keep the lock through this one bounded send: concurrent retries
            # see the new holder and cannot send the takeover twice.
            file_letter(ctx, held, taken, title)
    return 'claimed', path


def file_cli(a):
    """CLI errors say STOP (exit 1); only the hook has the fail-open contract."""
    try:
        ctx = file_context(a.hub)
        if a.claim_file:
            status, line = claim_file(ctx, a.claim_file, a.session, a.title, os.getcwd())
            if status == 'held':
                print('STOP: ' + line)
                return 1
            print('CLAIMED: %s · %s' % (file_path(a.claim_file, os.getcwd()),
                                      file_title(ctx, a.session, a.title)))
            return 0
        if a.release_file or a.release_files:
            file_session(a.session)
        with file_lock(ctx) as state:
            rows = read_file_claims(state) or []
            if a.files:
                if not rows:
                    print('no file claims on record (file-claims.json)')
                for row in rows:
                    age = file_age(ctx, row['session'])
                    print('%s · %s · %s · %s' % (row['path'], row['title'], row['since'],
                          'live' if age <= FILE_LIVE_SECONDS else 'idle'))
                return 0
            selected = file_path(a.release_file, os.getcwd()) if a.release_file else None
            gone = []
            for row in rows:
                if a.sweep_files:
                    drop = file_age(ctx, row['session']) > FILE_SWEEP_SECONDS
                else:
                    drop = row['session'] == a.session and (selected is None or row['path'] == selected)
                if drop:
                    gone.append(row)
            if gone:
                write_file_claims(state, [r for r in rows if r not in gone])
            for row in gone:
                print('RELEASED: %s · %s' % (row['path'], row['title']))
            if not gone:
                print('RELEASED: 0 file claims')
            return 0
    except Exception as exc:
        print('STOP: file claims — ' + ' '.join(str(exc).split()))
        return 1


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--claim", nargs=2, metavar=("ARC", "TITLE"))
    ap.add_argument("--release", nargs=2, metavar=("ARC", "TITLE"))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--take", action="store_true")
    ap.add_argument("--reason", default=None)
    ap.add_argument("--mind", default=None)
    ap.add_argument("--hours", type=float, default=12)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--hub", default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--help", action="store_true")
    files = ap.add_mutually_exclusive_group()
    files.add_argument("--claim-file", metavar="PATH")
    files.add_argument("--release-file", metavar="PATH")
    files.add_argument("--release-files", action="store_true")
    files.add_argument("--files", action="store_true")
    files.add_argument("--sweep-files", action="store_true")
    ap.add_argument("--session", metavar="ID")
    ap.add_argument("--title", metavar="TITLE")
    a = ap.parse_args(argv)
    if a.claim_file or a.release_file or a.release_files or a.files or a.sweep_files:
        if a.claim or a.release or a.list or a.sweep or a.take:
            print("STOP: file and lane verbs cannot be mixed")
            return 1
        return file_cli(a)
    if a.help or not (a.claim or a.release or a.list or a.sweep):
        print(__doc__)
        return 0
    name, roots = machine()
    folder = Path(a.hub) if a.hub else Path(roots.get("orchestrator") or Path(__file__).resolve().parent.parent)
    path = folder / "claims.json"
    if a.claim and name == "unknown":
        print(unnamed_line())
        return 1
    if a.claim:
        return cmd_claim(path, folder, name, a.claim[0], a.claim[1],
                         (a.mind or "").strip().upper() or None, a.take, a.reason, a.hours,
                         quiet=a.quiet)
    if a.release:
        return cmd_release(path, folder, name, a.release[0], a.release[1], quiet=a.quiet)
    if a.list:
        return cmd_list(path, a.hours)
    return cmd_sweep(path, folder, a.hours, a.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
