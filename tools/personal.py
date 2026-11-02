#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""personal.py — the exocortex gets to know its person, and keeps their laws.

TWO JOBS, one file.

1. THE FIRST-RUN CONVERSATION. Four pages in the hub's dossier/ folder hold
   what the person has said about themselves, word for word:

       PROFILE      who you are, what you do, your machines and their names
       RHYTHMS      when you work, when you do not want to be disturbed
       PRINCIPLES   how you want to be spoken to, what annoys you, what is
                    never done without asking
       INTERESTS    what you are working on, what you care about

   While a page is absent, or still carries the conversation's mark on its first
   line, the first wake of the day asks ONE question, in that order. The session
   says the question in the words printed here and passes the answer back
   unchanged; the answer is written under the question's heading, with the date,
   exactly as given. `skip` passes a question, `later` stops until the next day,
   `enough` stops the conversation for good (`--resume` starts it again). A page
   without the mark is kept by hand and is never asked about.

       python3 tools/personal.py --wake [--by MIND]     the day's first question, or nothing
       python3 tools/personal.py --answer "<words>"     write the answer, print the next
       python3 tools/personal.py --answer -             the answer read from standard input
       python3 tools/personal.py --answer-file FILE     the answer read from a UTF-8 file
       python3 tools/personal.py --skip | --later | --enough | --resume
       python3 tools/personal.py --status [--json]

   Answering with the single word skip, later or enough does the same as the
   flag, so a session that passes every answer through unchanged is right.

2. YOUR LAW BOOK. A rule the person ratifies is written to THEIR book,
   dossier/LAWS.md — never to the engine's exocortex-laws.md — and the journal
   line it came from is stamped.

       python3 tools/personal.py --promote "<the rule, one paragraph>" --name "<its name>"
                                 [--taught "<words of the journal line>"]
       python3 tools/personal.py --journal-only --taught "<words of the journal line>"

   Common flags: --hub DIR (default: the hub the resolver finds) · --json.
   EXO_PERSONAL_TODAY=YYYY-MM-DD fixes the date (a testing hook).

Every line printed for the person starts `say:` or `ask:`; a session says those
lines in those words and waits. Exit 0 = done (including "nothing to ask"),
2 = a refusal with one plain line saying why.

Standard library only, Python 3.9-compatible, macOS and Windows.
"""
import datetime
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):         # a Windows console is cp1252
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

try:
    import exo_laws                                     # noqa: E402
except ImportError:                                     # pragma: no cover
    exo_laws = None

API = 1

# ---------------------------------------------------------------- the pages

PAGES = ("PROFILE", "RHYTHMS", "PRINCIPLES", "INTERESTS")
TITLES = {
    "PROFILE": "Profile — who you are",
    "RHYTHMS": "Rhythms — when you work",
    "PRINCIPLES": "Principles — how you want to be worked with",
    "INTERESTS": "Interests — what you are working on and care about",
}
QUESTIONS = (
    ("profile-who", "PROFILE", "Who are you, in a sentence or two?"),
    ("profile-work", "PROFILE", "What do you do — your work, and the kind of work you will bring here?"),
    ("profile-machines", "PROFILE", "Which machines will you use this on, and what do you call each one?"),
    ("rhythms-when", "RHYTHMS", "When do you usually work?"),
    ("rhythms-quiet", "RHYTHMS", "When do you not want to be disturbed?"),
    ("principles-voice", "PRINCIPLES", "How do you want me to speak to you?"),
    ("principles-annoys", "PRINCIPLES", "What annoys you in how an assistant works?"),
    ("principles-ask-first", "PRINCIPLES", "What should I never do without asking you first?"),
    ("interests-now", "INTERESTS", "What are you working on right now?"),
    ("interests-care", "INTERESTS", "What do you care about, beyond the work in front of you?"),
)
QUESTION = dict((q[0], q) for q in QUESTIONS)

MARK = "<!-- exocortex:intake"
EXAMPLE_MARK = "EXAMPLE —"
NOT_YET = "you have not told me yet"
ANSWER_HEAD = re.compile(r"^(\d{4}-\d{2}-\d{2}), in your words:\s*$")
STATE_NAME = "intake.json"
COMMAND_WORDS = ("skip", "later", "enough")

INTRO = ("I'm Exocortex: one notebook shared by every session you open, on every "
         "machine and with every assistant you use. I will remember what you tell me "
         "here, word for word, on four short pages that are yours to read and change.")
HINT = "(answer in your own words — or say skip, later or enough)"


def mark_line(page):
    return ("%s page=%s · the first-run conversation writes your answers here, word "
            "for word, with the date. Edit freely. Delete this line to keep the page by "
            "hand: the conversation will not ask about it again. -->" % (MARK, page))


def empty_page(page):
    """The page before any answer — exactly the shipped seed."""
    out = [mark_line(page), "# " + TITLES[page], ""]
    for qid, where, text in QUESTIONS:
        if where != page:
            continue
        out += ["## " + text, "", NOT_YET, ""]
    return "\n".join(out).rstrip("\n") + "\n"


# ---------------------------------------------------------------- small tools

def today():
    fixed = (os.environ.get("EXO_PERSONAL_TODAY") or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", fixed):
        return fixed
    return datetime.date.today().isoformat()


def now_iso():
    fixed = (os.environ.get("EXO_PERSONAL_TODAY") or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", fixed):
        return fixed + "T12:00:00"
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def read(path):
    try:
        with io.open(str(path), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def write_atomic(path, text):
    """Written whole or not at all: a temp file beside it, then a rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    try:
        with io.open(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Refuse(Exception):
    """One plain line saying why nothing was written."""


def resolve_hub(given=None):
    if given:
        return Path(given)
    try:
        from exo_paths import paths                     # noqa: E402
        record = paths(tool_file=__file__)
        if record.get("hub"):
            return Path(record["hub"])
    except Exception:
        pass
    return HERE.parent


def resolve_claude(hub):
    """The claude root from the machine record, for the engine-book guard."""
    try:
        from exo_paths import paths                     # noqa: E402
        record = paths(tool_file=__file__, hub=str(hub))
        roots = record.get("roots") or {}
        if roots.get("claude"):
            return Path(roots["claude"])
    except Exception:
        pass
    return Path(os.path.expanduser("~")) / ".claude"


# ---------------------------------------------------------------- reading pages

def page_path(hub, page):
    return Path(hub) / "dossier" / (page + ".md")


def parse_page(text):
    """{heading text: [answer dicts]} for a page in the conversation's shape.
    An answer dict is {date, words}."""
    sections, current = {}, None
    lines = (text or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            i += 1
            continue
        head = ANSWER_HEAD.match(line)
        if head and current is not None:
            j = i + 1
            while j < len(lines) and lines[j] == "":
                j += 1
            quoted = []
            while j < len(lines) and lines[j].startswith(">"):
                body = lines[j][1:]
                quoted.append(body[1:] if body.startswith(" ") else body)
                j += 1
            sections[current].append({"date": head.group(1), "words": "\n".join(quoted)})
            i = j
            continue
        i += 1
    return sections


def page_state(hub, page):
    """{state, answered, of, last, file}. state: `empty` (absent, or marked with
    no answer) · `partial` · `full` (every question answered) · `yours` (kept by
    hand: no mark) · `example` (a marked example page — never a person's)."""
    path = page_path(hub, page)
    text = read(path)
    asked = [q for q in QUESTIONS if q[1] == page]
    out = {"page": page, "file": "dossier/%s.md" % page, "of": len(asked),
           "answered": 0, "last": "", "exists": text is not None}
    if text is None:
        out["state"] = "empty"
        return out
    first = text.split("\n", 1)[0]
    if first.startswith(EXAMPLE_MARK):
        out["state"] = "example"
        return out
    if not first.startswith(MARK):
        out["state"] = "yours"
        out["answered"] = out["of"]
        return out
    sections = parse_page(text)
    dates = []
    for _qid, _page, words in asked:
        got = sections.get(words) or []
        if got:
            out["answered"] += 1
            dates += [a["date"] for a in got]
    out["last"] = max(dates) if dates else ""
    out["state"] = ("empty" if out["answered"] == 0 else
                    "full" if out["answered"] == out["of"] else "partial")
    return out


def page_states(hub):
    return [page_state(hub, page) for page in PAGES]


def answered(hub, qid):
    """The answer written for one question, or None."""
    _qid, page, words = QUESTION[qid]
    text = read(page_path(hub, page))
    if text is None or not text.split("\n", 1)[0].startswith(MARK):
        return None
    got = parse_page(text).get(words) or []
    return got[-1] if got else None


def managed(hub, page):
    """True while the conversation may write this page: absent, or marked."""
    text = read(page_path(hub, page))
    return text is None or text.split("\n", 1)[0].startswith(MARK)


# ---------------------------------------------------------------- writing pages

def with_answer(text, page, words, date, answer):
    """The page with one answer written under its question's heading, in place
    of the `not yet` line when it is still there."""
    if text is None:
        text = empty_page(page)
    lines = text.rstrip("\n").split("\n")
    block = ["%s, in your words:" % date, ""] + [("> " + l) if l else ">" for l in answer.split("\n")]
    heading = "## " + words
    try:
        at = lines.index(heading)
    except ValueError:
        return "\n".join(lines + ["", heading, ""] + block) + "\n"
    end = at + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    section = lines[at + 1:end]
    body = [l for l in section if l.strip() != NOT_YET]
    while body and body[-1] == "":
        body.pop()
    while body and body[0] == "":
        body.pop(0)
    new = [""] + (body + [""] if body else []) + block + [""]
    lines = lines[:at + 1] + new + lines[end:]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the state

def state_path(hub):
    return Path(hub) / "dossier" / STATE_NAME


def load_state(hub):
    raw = read(state_path(hub))
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("opened", "")
    data.setdefault("current", None)
    data.setdefault("skipped", [])
    data.setdefault("enough", "")
    data.setdefault("log", [])
    return data


def save_state(hub, data):
    data["log"] = list(data.get("log") or [])[-200:]
    write_atomic(state_path(hub), json.dumps(data, indent=2, sort_keys=True) + "\n")


def log(data, qid, did, by=""):
    data.setdefault("log", []).append({"at": now_iso(), "q": qid or "", "did": did, "by": by or ""})


def open_questions(hub, data):
    """The questions still to ask, in order: on a page the conversation may
    write, not answered, not skipped."""
    out = []
    skipped = set(data.get("skipped") or [])
    for qid, page, _words in QUESTIONS:
        if not managed(hub, page):
            continue
        if qid in skipped:
            continue
        if answered(hub, qid) is not None:
            continue
        out.append(qid)
    return out


def ever_answered(hub):
    return any(answered(hub, qid) is not None for qid, _p, _w in QUESTIONS)


# ---------------------------------------------------------------- the conversation

def result(ask=None, say=(), why="", done=False, n=None, of=None):
    return {"ask": ask, "question": (QUESTION[ask][2] if ask else None),
            "say": list(say), "why": why, "done": done,
            "number": n, "of": of}


def numbered(hub, data, qid):
    left = open_questions(hub, data)
    total = len([q for q in QUESTIONS if managed(hub, q[1])])
    before = total - len(left)
    return before + 1, total


def wake(hub, by=""):
    """The day's first question, or nothing. Writes the state only when a
    question is asked."""
    data = load_state(hub)
    if data.get("enough"):
        return result(why="you said enough on %s; --resume starts again" % data["enough"])
    left = open_questions(hub, data)
    if not left:
        return result(why="nothing left to ask", done=True)
    if data.get("opened") == today():
        return result(why="already asked today (%s); the next question comes at the "
                          "first wake of another day" % data["opened"])
    first_time = not ever_answered(hub) and not data.get("log")
    qid = left[0]
    data["opened"] = today()
    data["current"] = qid
    log(data, qid, "asked", by)
    save_state(hub, data)
    n, of = numbered(hub, data, qid)
    if first_time:
        say = [INTRO]
    else:
        say = ["Picking up where we left off: %d question%s to go."
               % (len(left), "" if len(left) == 1 else "s")]
    return result(ask=qid, say=say, n=n, of=of)


def _waiting(data):
    qid = data.get("current")
    if not qid or qid not in QUESTION:
        raise Refuse("no question is waiting — the conversation opens at a wake "
                     "(personal.py --wake)")
    if data.get("opened") != today():
        raise Refuse("the question asked on %s is no longer open — it will be asked "
                     "again at the next wake" % (data.get("opened") or "an earlier day"))
    return qid


def _next(hub, data, by, said):
    left = open_questions(hub, data)
    if not left:
        data["current"] = None
        save_state(hub, data)
        return result(say=said + ["That was the last question. Your four pages are in "
                                  "dossier/ — read or change them any time."], done=True)
    qid = left[0]
    data["current"] = qid
    log(data, qid, "asked", by)
    save_state(hub, data)
    n, of = numbered(hub, data, qid)
    return result(ask=qid, say=said, n=n, of=of)


def answer(hub, words, by=""):
    command = (words or "").strip().strip(".!").lower()
    if command in COMMAND_WORDS:
        return {"skip": skip, "later": later, "enough": enough}[command](hub, by)
    data = load_state(hub)
    qid = _waiting(data)
    text = (words or "").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text.strip():
        raise Refuse("an empty answer is not written — say skip to pass this question")
    _qid, page, question = QUESTION[qid]
    if not managed(hub, page):
        raise Refuse("dossier/%s.md is kept by hand (it has no conversation mark) — "
                     "nothing was written" % page)
    path = page_path(hub, page)
    write_atomic(path, with_answer(read(path), page, question, today(), text))
    got = answered(hub, qid)
    if got is None or got["words"] != text:
        raise Refuse("the answer did not read back word for word from %s" % path.name)
    log(data, qid, "answered", by)
    return _next(hub, data, by, ["Noted, in your words, on your %s page."
                                 % page.lower()])


def skip(hub, by=""):
    data = load_state(hub)
    qid = _waiting(data)
    if qid not in data["skipped"]:
        data["skipped"].append(qid)
    log(data, qid, "skip", by)
    return _next(hub, data, by, ["Skipped — I will not ask that one again."])


def later(hub, by=""):
    data = load_state(hub)
    qid = _waiting(data)
    data["current"] = None
    log(data, qid, "later", by)
    save_state(hub, data)
    return result(say=["All right — I will pick this up at the first wake of another day."],
                  why="later")


def enough(hub, by=""):
    data = load_state(hub)
    qid = data.get("current")
    data["current"] = None
    data["enough"] = today()
    log(data, qid, "enough", by)
    save_state(hub, data)
    return result(say=["All right — I will not ask again. What you told me stays on your "
                       "pages. To start again later: personal.py --resume."], why="enough")


def resume(hub, by=""):
    data = load_state(hub)
    data["enough"] = ""
    data["opened"] = ""
    log(data, None, "resume", by)
    save_state(hub, data)
    return result(say=["The conversation will start again at the next wake."], why="resume")


def status(hub):
    data = load_state(hub)
    return {"pages": page_states(hub), "open": open_questions(hub, data),
            "skipped": list(data.get("skipped") or []), "enough": data.get("enough") or "",
            "opened": data.get("opened") or "", "current": data.get("current")}


# ---------------------------------------------------------------- the law book

def _stamp_taught(hub, match, stamp):
    """(new text, the line stamped) for the LAST unstamped dated journal line
    containing `match`. Refuse when there is none."""
    path = Path(hub) / "dossier" / "TAUGHT.md"
    text = read(path)
    if text is None:
        raise Refuse("there is no dossier/TAUGHT.md to stamp — nothing was written")
    lines = text.split("\n")
    at = None
    for i, line in enumerate(lines):
        if not line.startswith("- 20"):
            continue
        if match not in line:
            continue
        if "[PROMOTED" in line or "[JOURNAL-ONLY]" in line:
            continue
        at = i
    if at is None:
        raise Refuse("no unstamped journal line in dossier/TAUGHT.md contains those words "
                     "— nothing was written")
    lines[at] = lines[at].rstrip() + " " + stamp
    return "\n".join(lines), lines[at], path


def _same_file(a, b):
    """True when two paths are one file — by their real paths, so a link from
    one to the other counts, and by identity when both exist."""
    try:
        if os.path.exists(str(a)) and os.path.exists(str(b)) and os.path.samefile(str(a), str(b)):
            return True
    except OSError:
        pass
    norm = lambda p: os.path.normcase(os.path.realpath(os.path.abspath(str(p))))
    return norm(a) == norm(b)


def promote(hub, rule, name, taught=None, claude=None):
    rule = (rule or "").strip()
    name = (name or "").strip()
    if not rule or not name:
        raise Refuse("a promotion needs the rule and its name — nothing was written")
    if "\n" in rule or "\r" in rule:
        raise Refuse("a rule is one paragraph, one line — nothing was written")
    if "**" in name or "\n" in name or "(" in name:
        raise Refuse("a rule's name is plain words, no `**` and no brackets — nothing "
                     "was written")
    book = exo_laws.user_book(hub) if exo_laws else Path(hub) / "dossier" / "LAWS.md"
    engine = (exo_laws.engine_book(claude or resolve_claude(hub)) if exo_laws else None)
    if engine is not None and _same_file(book, engine):
        raise Refuse("your law book and the engine's are the same file here — a promotion "
                     "never writes the engine's book; nothing was written")
    stamped = None
    if taught:
        new_taught, stamped, taught_path = _stamp_taught(
            hub, taught, "[PROMOTED to your law book %s]" % today())
    law = "**%s (ruled %s).** %s" % (name, today(), rule)
    current = read(book)
    if current is None:
        current = (exo_laws.USER_BOOK_HEADER if exo_laws else "# Your laws\n")
    body = current.rstrip("\n") + "\n\n" + law + "\n"
    write_atomic(book, body)
    if stamped is not None:
        write_atomic(taught_path, new_taught)
    return {"wrote": str(book), "law": law, "stamped": stamped}


def journal_only(hub, taught):
    if not taught:
        raise Refuse("--journal-only needs --taught \"<words of the journal line>\"")
    new_taught, stamped, taught_path = _stamp_taught(hub, taught, "[JOURNAL-ONLY]")
    write_atomic(taught_path, new_taught)
    return {"stamped": stamped}


# ---------------------------------------------------------------- the command line

def _arg(argv, name, default=None):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def _utf8(raw):
    """Bytes as the person's words: UTF-8 with any byte-order mark dropped —
    never the console's own code page, which would change an accent."""
    if isinstance(raw, str):
        return raw
    text = (raw or b"").decode("utf-8", "replace")
    return text[1:] if text.startswith("\ufeff") else text


def _print(line):
    try:
        sys.stdout.write(line + "\n")
    except UnicodeEncodeError:
        sys.stdout.write(line.encode("ascii", "replace").decode("ascii") + "\n")


def show(res, as_json):
    if as_json:
        _print(json.dumps(res, sort_keys=True, ensure_ascii=False))
        return
    for line in res.get("say") or []:
        _print("say: " + line)
    if res.get("ask"):
        _print("ask: " + res["question"])
        _print("     " + HINT + "   [question %s of %s]" % (res.get("number"), res.get("of")))
    elif not res.get("say"):
        _print("nothing to ask — " + (res.get("why") or "done"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or "--help" in argv or "-h" in argv:
        sys.stdout.write(__doc__)
        return 0
    as_json = "--json" in argv
    hub = resolve_hub(_arg(argv, "--hub"))
    by = _arg(argv, "--by", "") or ""
    try:
        if "--wake" in argv:
            show(wake(hub, by), as_json)
        elif "--answer-file" in argv:
            path = _arg(argv, "--answer-file")
            raw = None
            try:
                with open(str(path), "rb") as fh:
                    raw = fh.read()
            except (OSError, TypeError):
                raise Refuse("--answer-file needs a file that can be read — nothing was written")
            show(answer(hub, _utf8(raw), by), as_json)
        elif "--answer" in argv:
            given = _arg(argv, "--answer")
            if given is None:
                raise Refuse("--answer needs the words, or - to read them from standard input")
            if given == "-":
                given = _utf8(sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer")
                              else sys.stdin.read())
            show(answer(hub, given, by), as_json)
        elif "--skip" in argv:
            show(skip(hub, by), as_json)
        elif "--later" in argv:
            show(later(hub, by), as_json)
        elif "--enough" in argv:
            show(enough(hub, by), as_json)
        elif "--resume" in argv:
            show(resume(hub, by), as_json)
        elif "--status" in argv:
            st = status(hub)
            if as_json:
                _print(json.dumps(st, sort_keys=True))
            else:
                for p in st["pages"]:
                    _print("%-10s %-8s %d of %d answered%s" % (
                        p["page"], p["state"], p["answered"], p["of"],
                        (" · last %s" % p["last"]) if p["last"] else ""))
                _print("open: %d · skipped: %d · %s" % (
                    len(st["open"]), len(st["skipped"]),
                    ("stopped (enough, %s)" % st["enough"]) if st["enough"]
                    else ("asked today" if st["opened"] == today() else "not asked today")))
        elif "--promote" in argv:
            got = promote(hub, _arg(argv, "--promote"), _arg(argv, "--name"),
                          _arg(argv, "--taught"),
                          Path(_arg(argv, "--claude")) if _arg(argv, "--claude") else None)
            if as_json:
                _print(json.dumps(got, sort_keys=True, ensure_ascii=False))
            else:
                _print("OK promoted into %s" % got["wrote"])
                _print("   " + got["law"][:160])
                _print("   journal line stamped" if got["stamped"]
                       else "   no journal line named (--taught) — none stamped")
        elif "--journal-only" in argv:
            got = journal_only(hub, _arg(argv, "--taught"))
            _print(json.dumps(got, ensure_ascii=False) if as_json
                   else "OK journal-only: " + got["stamped"][:160])
        else:
            sys.stdout.write(__doc__)
            return 2
    except Refuse as why:
        _print(("refused: %s" % why) if not as_json
               else json.dumps({"refused": str(why)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
