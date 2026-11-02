#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exo_registry.py — one answer to "whose fleet is this".

A tool that needs the person's name, their machines' marks, the minds they
work with, the words they call their lanes by or the line under their tree
asks this module instead of holding a table of its own:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from exo_registry import registry, owner_words, machine_mark

    REG = registry()
    machine_mark(REG, "hawking")

THE FILE is `<hub>/registry.json`. The person edits it by hand; the brain sync
carries it to every machine, and every vendor's session reads the same one.
Two things are NOT in it because they are per machine and not per person: the
machine's own name and roots, and the transfer drive's label — those stay in
`machine.json`.

WHAT IT PROMISES

  * Importing it does nothing at all: no file is read, nothing is printed,
    nothing is written, until a call.
  * registry() never raises. No file at all is not a problem — it is a person
    who has not written one, and every default is filled. A file that cannot
    be read or parsed gives the defaults and ONE plain sentence in `problems`
    naming the file and what went wrong. A field of the wrong type gives that
    field's default and one sentence.
  * It REPORTS. It does not decide what a caller should do about a problem.
  * Every key of the record is present after a call, so no caller writes
    `.get(..., default)` and no caller carries a default of its own.
  * The record is ADDITIVE: a later version adds keys and never renames one.
    A key this version has never heard of survives a round trip under its own
    name, so a newer file read by an older tool is never trimmed.
  * Nothing is invented. With no owner name, tools say "the owner" and count
    nothing rather than guessing. With no minds listed, a mind's name is read
    off what the tools actually see — the model id, the transcript family —
    and never off a roster.

FROM A SHELL

    python3 exo_registry.py --check     the record as text; exit 0 clean, 2 on a problem
    python3 exo_registry.py --path      where the file is, or would be

Standard library only, Python 3.9-compatible, macOS and Windows.
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

API = 1                        # the record's version — additive only, never renamed

REGISTRY_FILE_NAME = "registry.json"
REGISTRY_FILE_ENV = "EXO_REGISTRY_JSON"

# Every key of the record, in the order it is returned. A later API adds to the
# end of this tuple; nothing is ever taken out of it.
RECORD_KEYS = ("api", "version", "note", "owner", "machines", "minds",
               "mind_aliases", "lanes", "surface", "file", "problems")

# ── the defaults: what a nameless registry means ───────────────────────────
# These are the STRANGER's defaults and they live in ONE place. No tool below
# this module carries a default of its own.

DEFAULT_OWNER = {"name": "", "short": "", "aliases": []}
DEFAULT_MACHINES = {}
DEFAULT_MINDS = []
DEFAULT_MIND_ALIASES = {}
# The lane words, by the KIND of thing each word points at. They are separate
# blocks because they genuinely point at different things: a project folder, a
# family, a column of the sky, another project by its display name. One block
# could not hold four answers for one word, and the drawn pages print all four.
LANE_MAPS = ("aliases", "families", "groups", "mentions")
LANE_LISTS = ("hub_folders", "not_groups")
DEFAULT_LANES = {"aliases": {}, "families": {}, "groups": {}, "mentions": {},
                 "hub_folders": [], "not_groups": [], "hub_key": ""}
DEFAULT_SURFACE = {"caption": ""}

# The address tokens that mean the human whatever their name is. A registry
# with no owner name still reaches this mailbox by either of these words.
OWNER_TOKENS = ("OWNER", "HUMAN")

# The one machine-side value of `next:`. Everything that is not a machine and
# not a known owner word is REPORTED and counted as the human's — attention,
# never silence.
MACHINE_NEXT = ("machine",)

# A machine with no mark of its own. Display only.
DEFAULT_MACHINE_MARK = "●"

# Vendors read off a model id's own prefix, so an id nobody has registered
# still names its house. An unknown prefix becomes itself, capitalized.
VENDOR_BY_PREFIX = (
    ("claude", "Anthropic"),
    ("gpt", "OpenAI"),
    ("codex", "OpenAI"),
    ("o", "OpenAI"),
    ("grok", "xAI"),
)

# Eight colours, handed out by order of first sight and stable within one
# drawing. A registry that names its own hues never reaches this list.
PALETTE = (
    {"light": "#0a6ba8", "dark": "#4fc1ff"},
    {"light": "#6f42ad", "dark": "#a78bfa"},
    {"light": "#0f766e", "dark": "#2dd4bf"},
    {"light": "#64748b", "dark": "#9fb3c8"},
    {"light": "#be185d", "dark": "#f0a0c0"},
    {"light": "#c2410c", "dark": "#ff9d7a"},
    {"light": "#7a5c00", "dark": "#d9b25c"},
    {"light": "#1f6f3f", "dark": "#5fd38a"},
)

USAGE = """exo_registry.py — the person's own names: who they are, what their
machines are called, which minds they work with, what they call their lanes.

  python3 exo_registry.py --check     the record as text; exit 0 clean, 2 on a problem
  python3 exo_registry.py --path      where the file is, or would be

The file is registry.json at the hub folder. Every field is optional; what is
missing is not guessed at — it is simply not said.
"""


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def _oneline(text):
    return " ".join(str(text).split())


def _hub_from_resolver(problems):
    """The hub through the resolver, when it is beside us. The registry works
    without it: a caller may always pass `hub=` itself."""
    here = Path(__file__).resolve().parent
    try:
        if not (here / "exo_paths.py").is_file():
            return None
        if str(here) not in sys.path:
            sys.path.insert(0, str(here))
        import exo_paths                                   # noqa: E402
        record = exo_paths.paths(tool_file=__file__)
        return record.get("hub")
    except Exception as exc:                               # never a crash
        problems.append("the resolver beside this module could not answer where "
                        "the hub is (%s); registry.json was looked for beside it"
                        % _oneline(exc))
        return None


def registry_path(hub=None):
    """Where the file is, or would be. `EXO_REGISTRY_JSON` names it outright —
    that is how a gate points a tool at a fixture."""
    named = os.environ.get(REGISTRY_FILE_ENV)
    if named:
        return Path(named)
    if hub:
        return Path(hub) / REGISTRY_FILE_NAME
    problems = []
    found = _hub_from_resolver(problems)
    if found:
        return Path(found) / REGISTRY_FILE_NAME
    return Path(__file__).resolve().parent.parent / REGISTRY_FILE_NAME


def _as_str(value):
    return value if isinstance(value, str) else ""


def _field(raw, key, default, want, problems, path):
    """One field, its default, and one plain sentence when it is the wrong
    shape. `want` is the type the field must be."""
    if key not in raw:
        return _copy(default)
    value = raw.get(key)
    if isinstance(value, want) and not isinstance(value, bool):
        return value
    problems.append("%s: `%s` should be %s, so its default is used instead"
                    % (path.name if hasattr(path, "name") else path, key,
                       _shape_word(want)))
    return _copy(default)


def _shape_word(want):
    if want is dict:
        return "a block of key: value lines"
    if want is list:
        return "a list"
    if want is str:
        return "a line of text"
    return "another shape"


def _copy(value):
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def registry(hub=None):
    """The person's own names, as one dict. See RECORD_KEYS for every key.

    Never raises. `problems` carries one plain sentence per thing that was
    wrong with the file; an empty list means the file was clean, or that there
    was no file at all — which is not a problem, only a person who has not
    written one yet."""
    problems = []
    path = registry_path(hub)

    raw = {}
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            problems.append("%s could not be read (%s), so the defaults are used"
                            % (path.name, _oneline(exc)))
            text = None
        if text is not None:
            try:
                loaded = json.loads(text)
            except Exception as exc:
                problems.append("%s is not valid JSON (%s), so the defaults are used"
                                % (path.name, _oneline(exc)))
                loaded = None
            if loaded is not None:
                if isinstance(loaded, dict):
                    raw = loaded
                else:
                    problems.append("%s should hold a block of key: value lines, "
                                    "so the defaults are used" % path.name)

    record = {"api": API}
    version = raw.get("version", 1)
    record["version"] = version if isinstance(version, int) and not isinstance(version, bool) else 1
    # `note` is for the person who edits the file. JSON has no comments, so it
    # may be one sentence or a list of them — a list reads as lines in an
    # editor, which is why the shipped seed writes one.
    note = raw.get("note", "")
    if isinstance(note, list):
        note = "\n".join(_as_str(n) for n in note)
    record["note"] = _as_str(note)

    owner = _field(raw, "owner", DEFAULT_OWNER, dict, problems, path)
    record["owner"] = {
        "name": _as_str(owner.get("name", "")).strip(),
        "short": _as_str(owner.get("short", "")).strip(),
        "aliases": [_as_str(a).strip() for a in owner.get("aliases", [])
                    if isinstance(a, str) and a.strip()]
        if isinstance(owner.get("aliases", []), list) else [],
    }
    for extra in owner:
        if extra not in record["owner"]:
            record["owner"][extra] = owner[extra]

    machines = _field(raw, "machines", DEFAULT_MACHINES, dict, problems, path)
    record["machines"] = {}
    for name, block in machines.items():
        if not isinstance(block, dict):
            problems.append("%s: the machine `%s` should hold a block of "
                            "key: value lines, so its defaults are used"
                            % (path.name, name))
            block = {}
        record["machines"][str(name)] = dict(block)

    minds = _field(raw, "minds", DEFAULT_MINDS, list, problems, path)
    record["minds"] = []
    for entry in minds:
        if not isinstance(entry, dict):
            problems.append("%s: every line of `minds` should hold a block of "
                            "key: value lines; one was skipped" % path.name)
            continue
        if not _as_str(entry.get("name", "")).strip():
            problems.append("%s: a mind with no `name` was skipped" % path.name)
            continue
        record["minds"].append(dict(entry))

    aliases = _field(raw, "mind_aliases", DEFAULT_MIND_ALIASES, dict, problems, path)
    record["mind_aliases"] = {str(k): _as_str(v) for k, v in aliases.items()}

    lanes = _field(raw, "lanes", DEFAULT_LANES, dict, problems, path)
    record["lanes"] = dict(lanes)
    for key in LANE_MAPS:
        block = lanes.get(key, {})
        if not isinstance(block, dict):
            problems.append("%s: `lanes.%s` should hold a block of key: value "
                            "lines, so nothing is mapped through it" % (path.name, key))
            block = {}
        record["lanes"][key] = {str(k): _as_str(v) for k, v in block.items()}
    record["lanes"]["hub_key"] = _as_str(lanes.get("hub_key", ""))
    for key in LANE_LISTS:
        block = lanes.get(key, [])
        if not isinstance(block, list):
            problems.append("%s: `lanes.%s` should hold a list, so it is read "
                            "as empty" % (path.name, key))
            block = []
        record["lanes"][key] = [_as_str(v) for v in block if isinstance(v, str)]

    surface = _field(raw, "surface", DEFAULT_SURFACE, dict, problems, path)
    record["surface"] = dict(surface)
    record["surface"]["caption"] = _as_str(surface.get("caption", ""))

    # Anything a later version wrote survives under its own name.
    for key in raw:
        if key not in record and key not in ("file", "problems", "api"):
            record[key] = raw[key]

    record["file"] = str(path)
    record["problems"] = problems
    return record


# ---------------------------------------------------------------------------
# the owner
# ---------------------------------------------------------------------------

def owner_words(reg):
    """Every word that means the person, for matching at word boundaries: the
    name and the aliases. EMPTY when no name is set — and a tool that counts
    by these words then counts nothing and says why, rather than counting the
    wrong thing."""
    words = []
    for word in [reg["owner"]["name"]] + list(reg["owner"]["aliases"]):
        word = str(word).strip()
        if word and word not in words:
            words.append(word)
    return words


def owner_label(reg, when_unset="the owner"):
    """How to NAME the person in prose. With no name set, the plain noun."""
    return reg["owner"]["name"] or when_unset


def owner_tokens(reg):
    """The upper-cased address tokens that reach the person's mailbox: OWNER
    and HUMAN always, plus the short word and every alias. `to: OWNER` works
    on a registry that names nobody, which is the point."""
    tokens = list(OWNER_TOKENS)
    for word in [reg["owner"]["short"]] + owner_words(reg):
        word = str(word).strip().upper()
        if word and word not in tokens:
            tokens.append(word)
    return tokens


def is_owner_token(reg, token):
    """True when this address means the person."""
    return str(token or "").strip().upper() in set(owner_tokens(reg))


def owner_key(reg):
    """The one lower-case key a state file writes the person's things under.
    It never carries a name: a state file outlives a change of name."""
    return "owner"


def human_next_values(reg):
    """The `next:` values that mean a human owes the next move — lower case,
    matched case-insensitively. `owner` and `human` always; the person's own
    short word and aliases when they set them."""
    values = ["owner", "human"]
    for word in [reg["owner"]["short"]] + owner_words(reg):
        word = str(word).strip().lower()
        if word and word not in values:
            values.append(word)
    return values


def machine_next_values():
    """The `next:` values that mean the machine owes the next move."""
    return list(MACHINE_NEXT)


def next_side(reg, value):
    """("human" | "machine", problem or "") for one opener's `next:` value.

    An unknown word is the human's AND carries a problem line: a lane waiting
    on somebody is never silently taken off the board."""
    word = str(value or "").strip().lower()
    if not word:
        return "", ""
    if word in machine_next_values():
        return "machine", ""
    if word in human_next_values(reg):
        return "human", ""
    return "human", ("next: %s is not a word this registry knows — counted as "
                     "waiting on a person; use owner, human or machine" % word)


# ---------------------------------------------------------------------------
# the machines
# ---------------------------------------------------------------------------

def _machine_block(reg, name):
    key = str(name or "").strip()
    machines = reg["machines"]
    if key in machines:
        return machines[key]
    for listed, block in machines.items():
        if str(listed).lower() == key.lower():
            return block
    return {}


def machine_label(reg, name):
    """What to CALL this machine on a surface. With nothing recorded, the name
    the machine calls itself, capitalized."""
    block = _machine_block(reg, name)
    label = _as_str(block.get("label", "")).strip()
    if label:
        return label
    name = str(name or "").strip()
    return name.title() if name else "this machine"


def machine_mark(reg, name):
    """The one glyph that stands for this machine. With nothing recorded, a
    neutral dot — never a guess at which machine it is."""
    block = _machine_block(reg, name)
    mark = _as_str(block.get("mark", "")).strip()
    return mark or DEFAULT_MACHINE_MARK


def machine_os(reg, name):
    """The operating system family this machine runs (`macos` / `windows` /
    `linux`), or "" when nothing says. A tool that must PRINT a command for
    another machine asks this; a tool that acts HERE asks the running system."""
    return _as_str(_machine_block(reg, name).get("os", "")).strip().lower()


def machine_hue(reg, name, scheme="light"):
    """This machine's colour, or "" when it has none. A surface that draws a
    colour token draws one only for a machine that HAS a colour."""
    return _hue_of(_machine_block(reg, name).get("hue"), scheme)


def machine_names(reg):
    """The machines the registry names, in the order it names them."""
    return list(reg["machines"].keys())


# ---------------------------------------------------------------------------
# the minds
# ---------------------------------------------------------------------------

def _fold(text):
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def _parts(model_id):
    return [p for p in re.split(r"[^0-9A-Za-z]+", _fold(model_id)) if p]


def _alpha(part):
    return part.isalpha()


def kind_word(kind):
    """The word a transcript family calls itself, upper-cased: `codex` →
    CODEX. It is derived from the kind and never from a roster, so a family
    nobody has registered still has a name."""
    return str(kind or "").strip().upper()


def family_word(model_id, kind=""):
    """The family word of a model id, upper-cased: the first purely alphabetic
    part AFTER the part that names the family, or after the first part when it
    does not appear. `claude-fable-5-1` → FABLE, `…-sonnet-…` → SONNET.

    Product names are read off the id. A persona is not a product name and is
    never read off anything — it comes from the registry or not at all."""
    parts = _parts(model_id)
    if not parts:
        return ""
    start = 1
    low = [p.lower() for p in parts]
    kind = str(kind or "").strip().lower()
    if kind and kind in low:
        start = low.index(kind) + 1
    for part in parts[start:]:
        if _alpha(part):
            return part.upper()
    return parts[0].upper() if _alpha(parts[0]) else ""


def mind_alias(reg, token):
    """A word a stamp, a model line or a transcript writes → the mind it
    means. An unknown word is itself: a stamp that says GPT stays GPT on a
    registry with no alias for it."""
    token = str(token or "").strip().upper()
    for written, means in reg["mind_aliases"].items():
        if str(written).strip().upper() == token and str(means).strip():
            return str(means).strip().upper()
    return token


def mind_names(reg):
    """The minds the registry lists, in the order it lists them."""
    return [str(m.get("name", "")).strip().upper() for m in reg["minds"]
            if str(m.get("name", "")).strip()]


def _mind_block(reg, name):
    name = str(name or "").strip().upper()
    for entry in reg["minds"]:
        if str(entry.get("name", "")).strip().upper() == name:
            return entry
    return {}


def mind_name(reg, kind="", model_id=""):
    """The NAME of the mind behind a session, from what the tools can see.

    kind `claude` → the family word of the model id (FABLE, OPUS, SONNET,
    HAIKU — product names, read off the id); any other kind → its own word
    upper-cased (CODEX, GROK). Then the registry's aliases have their say, so
    a person who calls their Codex desktop by a persona gets that persona and
    a person who has not named one gets CODEX.

    Never a crash, never a guess, never a silent drop."""
    kind = str(kind or "").strip().lower()
    if kind and kind != "claude":
        return mind_alias(reg, kind_word(kind))
    token = family_word(model_id, kind or "claude")
    if not token:
        token = kind_word(kind or "claude")
    return mind_alias(reg, token)


def mind_vendor(reg, name, model_id=""):
    """The word a surface prints for this mind's house. The registry first;
    then the model id's OWN prefix; then "" — and a caller that must print
    something prints its own dash, because "" is honest and "—" is a surface's
    choice."""
    resolved = mind_alias(reg, name)
    block = _mind_block(reg, resolved)
    if block:
        return _as_str(block.get("vendor", "")).strip()
    parts = _parts(model_id)
    if parts:
        prefix = parts[0].lower()
        for word, vendor in VENDOR_BY_PREFIX:
            if prefix == word:
                return vendor
        return parts[0].title()
    return ""


def mind_kind(reg, name):
    """The transcript family this mind belongs to (`claude` / `codex` /
    `grok` / …), or "" when nothing says."""
    resolved = mind_alias(reg, name)
    block = _mind_block(reg, resolved)
    if block:
        return _as_str(block.get("kind", "")).strip().lower()
    word = str(resolved or "").strip().lower()
    return word if word in ("claude", "codex", "grok") else ""


def minds_of_kind(reg, kind):
    """Every word that names a mind of this transcript family — the listed
    names AND the alias words that reach them. This is what a tool asks
    instead of holding a tuple of personas."""
    kind = str(kind or "").strip().lower()
    out = []
    for name in mind_names(reg):
        if mind_kind(reg, name) == kind and name not in out:
            out.append(name)
    for written in reg["mind_aliases"]:
        token = str(written).strip().upper()
        if token and mind_kind(reg, token) == kind and token not in out:
            out.append(token)
    return out


def mind_order(reg, seen=()):
    """The registry's own order, then everything else in order of first sight.

    A mind the registry has never heard of is never dropped and never sorted
    into somebody else's place — it simply follows."""
    order = mind_names(reg)
    for name in seen:
        name = str(name or "").strip().upper()
        if name and name not in order:
            order.append(name)
    return order


def mind_rank(reg, name, unlisted=9):
    """Where this mind sorts. A mind the registry does not list sorts last —
    one rank for all of them, so they keep their own order among themselves."""
    order = mind_names(reg)
    name = str(name or "").strip().upper()
    return order.index(name) if name in order else unlisted


def mind_shown(reg):
    """The minds a surface draws even when nothing of theirs is up: the ones
    the person marked `show`. A registry that marks none draws only what it
    actually sees — a stranger's tree has no root for a mind they never had."""
    return [str(m.get("name", "")).strip().upper() for m in reg["minds"]
            if m.get("show") and str(m.get("name", "")).strip()]


def _hue_of(value, scheme="light"):
    """A hue is one CSS colour, or a block naming one per scheme. "" means
    this thing has no colour, and a surface then draws no token for it."""
    scheme = str(scheme or "light").lower()
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return _as_str(value.get(scheme, "")).strip() or _as_str(value.get("light", "")).strip()
    return ""


def mind_hue(reg, name, index=None, scheme="light"):
    """This mind's colour. The registry's own when it names one; otherwise a
    palette colour by `index` — by order of first sight, stable within one
    drawing, distinct for the first eight and repeating after that. With
    neither, "".

    A mind the registry lists with no hue HAS no hue: the person left it
    uncoloured on purpose, and a surface draws no token for it."""
    resolved = mind_alias(reg, name)
    block = _mind_block(reg, resolved)
    if block:
        return _hue_of(block.get("hue"), scheme)
    if index is None:
        return ""
    return _hue_of(PALETTE[int(index) % len(PALETTE)], scheme)


def mind_drawn(reg):
    """The minds this registry gives a colour to, in its own order. These are
    the ones a surface can mint a token for; everything else is drawn in the
    colour it inherits."""
    return [name for name in mind_names(reg) if mind_hue(reg, name)]


# ---------------------------------------------------------------------------
# the lanes and the surface
# ---------------------------------------------------------------------------

def lane_aliases(reg):
    """The person's own lane words → the project folders they mean."""
    return dict(reg["lanes"]["aliases"])


def _lane_key(word):
    return re.sub(r"[^a-z0-9]+", " ", _fold(word).lower()).strip()


def lane_folder(reg, word, default=None):
    """The project folder a lane word means, or `default` when nothing says.

    Punctuation and case do not matter — `X99/`, `x99` and `X 99` are one
    word. The longest recorded word that the given text starts with wins, so
    a specific lane beats a family name."""
    text = _lane_key(word)
    if not text:
        return default
    best, found = "", default
    for alias, folder in reg["lanes"]["aliases"].items():
        key = _lane_key(alias)
        if not key:
            continue
        if text == key or text.startswith(key + " ") or _lane_key(word).startswith(key):
            if len(key) > len(best):
                best, found = key, folder
    return found


def lane_families(reg):
    """A name's opening words → the family it belongs to. Checked in the order
    the person wrote them, first match wins — the same rule the code used to
    carry as a list."""
    return dict(reg["lanes"]["families"])


def lane_family(reg, name, default=None):
    """The family a project belongs to: the first recorded prefix its name
    starts with, else its own name lowercased."""
    low = _fold(name).lower()
    for prefix, family in reg["lanes"]["families"].items():
        if low.startswith(str(prefix).lower()):
            return family
    return low if default is None else default


def lane_groups(reg):
    """A word → the column of the sky it belongs in."""
    return dict(reg["lanes"]["groups"])


def lane_group(reg, word, default=None):
    return reg["lanes"]["groups"].get(str(word), default)


def not_lane_words(reg):
    """Words that look like a lane and are not one — a root, a folder, a
    place. They are never resolved to a column."""
    return list(reg["lanes"]["not_groups"])


def lane_mentions(reg):
    """A word → the project it MENTIONS, by the display name the memories use.
    This is how a note that names another project draws a line to it."""
    return dict(reg["lanes"]["mentions"])


def lane_mention(reg, word, default=None):
    """The project a word MENTIONS, by the display name the memories use."""
    return reg["lanes"]["mentions"].get(str(word), default)


def hub_folders(reg):
    """The folder names that ARE this hub. A note addressed to one of them is
    a note to the hub itself, not to a project beside it."""
    return list(reg["lanes"]["hub_folders"])


def hub_key(reg, default=""):
    """The name the hub's OWN notes and memories are filed under. A folder that
    was renamed keeps its old name in the record that already carries it, so
    the person writes that name here and the tile still meets its stars."""
    found = _as_str(reg["lanes"].get("hub_key", "")).strip()
    return found or default


def hub_words(reg):
    """Every word that means the hub: the lane words recorded against `hub`,
    in the order they were written."""
    return [word for word, folder in reg["lanes"]["aliases"].items()
            if str(folder).strip().lower() == "hub"]


def caption(reg):
    """The one line under the tree's sky, or "" — and "" means NO line, not an
    empty one."""
    return reg["surface"]["caption"]


# ---------------------------------------------------------------------------
# from a shell
# ---------------------------------------------------------------------------

def as_text(reg):
    lines = []
    lines.append("file           %s%s" % (reg["file"], "" if Path(reg["file"]).is_file()
                                          else "   (no file yet — every default is used)"))
    lines.append("version        %s" % reg["version"])
    lines.append("owner          name %s · short %s · aliases %d"
                 % (reg["owner"]["name"] or "(none)", reg["owner"]["short"] or "(none)",
                    len(reg["owner"]["aliases"])))
    lines.append("machines       %s" % (", ".join("%s (%s %s)" % (n, machine_mark(reg, n),
                                                                  machine_label(reg, n))
                                                  for n in machine_names(reg)) or "(none)"))
    lines.append("minds          %s" % (", ".join("%s%s" % (n, (" · " + mind_vendor(reg, n))
                                                            if mind_vendor(reg, n) else "")
                                                  for n in mind_names(reg)) or "(none)"))
    lines.append("mind aliases   %d" % len(reg["mind_aliases"]))
    lines.append("lane words     %d" % len(reg["lanes"]["aliases"]))
    lines.append("caption        %s" % (caption(reg) or "(no line)"))
    return "\n".join(lines)


def check_line(reg):
    if reg["problems"]:
        return "registry: %d problem%s" % (len(reg["problems"]),
                                           "" if len(reg["problems"]) == 1 else "s")
    return "registry: clean"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    hub = None
    if "--hub" in argv:
        at = argv.index("--hub")
        hub = argv[at + 1] if at + 1 < len(argv) else None
        del argv[at:at + 2]
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(USAGE)
        return 0
    if "--path" in argv:
        sys.stdout.write("%s\n" % registry_path(hub))
        return 0
    if "--check" in argv or not argv:
        reg = registry(hub)
        sys.stdout.write("%s\n" % as_text(reg))
        for problem in reg["problems"]:
            sys.stdout.write("problem: %s\n" % problem)
        sys.stdout.write("%s\n" % check_line(reg))
        return 2 if reg["problems"] else 0
    sys.stdout.write(USAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
