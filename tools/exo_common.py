#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exo_common.py — the few readers and rails MORE THAN ONE tool needs.

The pulse (tools/pulse.py) senses live sessions; the tree page's collector
(tools/collect-openers.py) counts the sessions of the last six weeks for the
fall. Both must read a transcript the same way — bounded, never the whole file,
never raising — so the reader lives here once and both import it (never a
second copy of `_read_model`).

The pulse and the landing tool (tools/auto-land.py) must also BOUND a child
process the same way: `run_bounded` kills the whole process tree on a timeout,
because a plain timeout kills only the direct child and a grandchild holding the
pipes open hangs the beat (the engine's own carrier_preflight._run_bounded is
the same rule, and this is its hub-side twin so neither tool has to import the
engine to run a subprocess safely).

Stdlib only, Python 3.9-compatible, OS-neutral.
"""
import io
import errno
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exo_registry import registry, mind_name                          # noqa: E402

_REG = [None]


def _reg():
    """The person's own names, read once per process. A tool asks this instead
    of holding a roster; a registry that names nobody still answers."""
    if _REG[0] is None:
        _REG[0] = registry()
    return _REG[0]

MODEL_RE = re.compile(r'"model"\s*:\s*"([^"]{1,120})"')
CWD_RE = re.compile(r'"cwd"\s*:\s*"([^"]{1,400})"')
CHUNK = 65536          # 64 KB — a transcript is megabytes; never read it whole


def read_model(f):
    """The session's own model id, from a BOUNDED read (never the whole file).

    Claude Code writes `"model":"claude-fable-5-1"` on every assistant turn, so
    the LAST one in the final 64 KB is what the session is running now. A Codex
    rollout records it once, in the turn_context near the head, so when the tail
    says nothing the first 64 KB is read instead. '' when the file says nothing
    or cannot be read — one bad transcript never fails the beat."""
    try:
        size = f.stat().st_size
        with io.open(f, "rb") as fh:
            if size > CHUNK:
                fh.seek(size - CHUNK)
            found = MODEL_RE.findall(fh.read(CHUNK).decode("utf-8", "replace"))
        if found:
            return found[-1]
        if size > CHUNK:
            with io.open(f, "rb") as fh:
                found = MODEL_RE.findall(fh.read(CHUNK).decode("utf-8", "replace"))
            if found:
                return found[-1]
    except (OSError, ValueError, UnicodeError):
        pass
    return ""


def mind_of(kind, model):
    """The MIND the tree shows, from what this transcript actually says: the
    family word of the model id for a Claude transcript, the transcript
    family's own word for any other, and then whatever the registry calls
    that — a persona for somebody who has named one, the plain word for
    somebody who has not. The model id stays in the hover either way."""
    return mind_name(_reg(), kind, model)


def _unescape(raw):
    """A cwd lifted out of a JSON line by substring scan: JSON-unescape it when
    we can (Windows cwds arrive as 'C:\\\\Users\\\\you'), else keep it raw."""
    try:
        return json.loads('"' + raw + '"')
    except Exception:
        return raw


def scan_cwd(f, lines=40):
    """The substring scan: the first "cwd":"..." in the head of a transcript.
    Every readline is length-capped, so one pathological line cannot pull a
    megabyte into memory."""
    try:
        with io.open(f, encoding="utf-8", errors="replace") as fh:
            for _ in range(lines):
                line = fh.readline(CHUNK)
                if not line:
                    break
                if '"cwd"' in line:
                    try:                       # real JSON first (spaced or compact)
                        d = json.loads(line)
                        if isinstance(d, dict) and d.get("cwd"):
                            return str(d["cwd"])
                    except ValueError:
                        pass
                m = CWD_RE.search(line)
                if m:
                    return _unescape(m.group(1))
    except OSError:
        pass
    return ""


def codex_cwd(f):
    """A rollout's FIRST line is a session_meta record: payload.cwd. Parse it;
    fall back to the substring scan when the line will not parse."""
    try:
        with io.open(f, encoding="utf-8", errors="replace") as fh:
            first = fh.readline(CHUNK)
    except OSError:
        return ""
    try:
        d = json.loads(first)
        cwd = (d.get("payload") or {}).get("cwd")
        if cwd:
            return str(cwd)
    except Exception:
        pass
    m = CWD_RE.search(first or "")
    if m:
        return _unescape(m.group(1))
    return scan_cwd(f)


# --------------------------------------------------------------------------
# ritual titles: which lane a session belongs to
# --------------------------------------------------------------------------
# The pen check (tools/who-is-live.py) and the semantic engine's A-classes both
# ask the same question of a stamp: which lane is this session working in?  A
# substring test answers it wrong — a hub's token sits inside every one of its
# lanes' tokens, so every lane of a project used to read as that project's HUB,
# and the pen check raised false contests over it.
# One rule, one place, and neither a machine name nor a lane name is spelled
# here: the caller passes the machines the record knows.


def lane_token(title):
    """The lane token of a ritual title, lower-cased:

        'ACT — Hub/Machine: day 12'  ->  'hub/machine'

    the text between the first dash and the first colon.  A title with no dash
    is read from its start; a title with no colon gives all that is left."""
    t = str(title or "")
    if "—" in t:
        t = t.split("—", 1)[1]
    return t.split(":", 1)[0].strip().lower()


def is_hub_title(title, stem, machines=()):
    """Is this ritual title the HUB lane's own?

    Only three shapes count: '<stem>/<machine>' for a machine the record knows,
    '<stem> hub', and '<stem>' bare.  `stem` is the hub's own lane token without
    its trailing slash; `machines` are the names the record carries (machine.json
    and the brain's sync manifest), never a list written into code."""
    s = str(stem or "").strip().rstrip("/").lower()
    if not s:
        return False
    want = {s, "%s hub" % s}
    for m in machines or ():
        m = str(m).strip().lower()
        if m:
            want.add("%s/%s" % (s, m))
    return lane_token(title) in want


def is_lane(title, want, hub_stem=None, machines=()):
    """Does this ritual title belong to the lane asked for?

    The HUB lane — when `want` is the hub stem itself — matches only its own
    tokens (is_hub_title).  Every other lane matches by exact equality, so one
    lane's token answers for that lane and for nothing else."""
    w = str(want or "").strip().rstrip("/").lower()
    stem = str(hub_stem if hub_stem is not None else w).strip().rstrip("/").lower()
    if not w:
        return False
    if w == stem:
        return is_hub_title(title, stem, machines)
    return lane_token(title) == w


# --------------------------------------------------------------------------
# who is this session? — asked of the environment, never of a model
# --------------------------------------------------------------------------
# A tool running INSIDE a session can know which session it is in for nothing,
# when its vendor says so in the environment.  Claude Code documents two:
#   "CLAUDE_CODE_SESSION_ID  Current session ID … matches the `session_id` field
#    in the hook JSON input and is updated on /clear"   (code.claude.com/docs/en/env-vars)
# and CLAUDE_CODE_HOST_SESSION_ID, the desktop app's own `local_…` id.  Codex
# gives its shell tool no session id at all (its environment carries only
# CODEX_HOME), so there the answer is {} and the caller prints a
# nonce instead — never a guess from a folder or a clock.
#
# The session's messaging socket and its token are deliberately NOT read here:
# that door's contract is own-child only, and a secret on disk is not ours to keep.

# Grok Build: its shell carries GROK_SESSION_ID — the SAME id its
# PreToolUse stdin `session_id` carries — beside GROK_AGENT=1.  Grok is listed FIRST
# because a headless Grok launched from inside a Claude session INHERITS the Claude
# ids; the innermost agent wins, and GROK_AGENT=1 is the mark that Grok is the one
# running now (a Claude session launched from inside Grok is not a shape we run).
VENDOR_SESSION_ENV = (
    ("grok", "GROK_SESSION_ID", ""),
    ("claude", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_HOST_SESSION_ID"),
)
VENDOR_MARK_ENV = {"grok": "GROK_AGENT"}   # a vendor listed here counts only when its mark is set


def session_identity(env=None):
    """{vendor, session[, host_session]} from the environment, or {} — THE ONE
    PLACE.  {} is the honest answer for "this vendor does not say",
    and every caller treats it as such."""
    e = os.environ if env is None else env
    for vendor, key, host_key in VENDOR_SESSION_ENV:
        sid = str(e.get(key) or "").strip()
        if not sid:
            continue
        mark = VENDOR_MARK_ENV.get(vendor)
        if mark and not str(e.get(mark) or "").strip():
            continue
        out = {"vendor": vendor, "session": sid}
        host = str(e.get(host_key) or "").strip() if host_key else ""
        if host:
            out["host_session"] = host
        return out
    return {}


def load_postman(hub=None):
    """postman.py, beside this file first and the hub's tools/ second — or None.
    Nothing here ever raises: without a postman every caller keeps yesterday's
    behaviour exactly."""
    import importlib.util
    import os.path as _p
    here = _p.dirname(_p.abspath(__file__))
    cands = [_p.join(here, "postman.py")]
    if hub:
        cands.append(_p.join(str(hub), "tools", "postman.py"))
    for cand in cands:
        try:
            if not _p.isfile(cand):
                continue
            spec = importlib.util.spec_from_file_location("exo_postman_c%d" % os.getpid(), cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            continue
    return None


def identity_or_nonce(title="", arcs=(), hub=None):
    """(identity, the one line to print) — how a session says who it is.

    WITH an environment id the line is empty: nothing superfluous is printed.
    WITHOUT one — Codex today — a NONCE is minted and recorded, and the caller
    prints the single line `  id: pn-<12 hex>`.  The postman then binds that
    nonce by finding it in exactly one transcript; found in none or in several,
    it stays unbound, AND AN UNBOUND NONCE NEVER ROUTES."""
    who = session_identity()
    if who:
        return who, ""
    pm = load_postman(hub)
    if pm is None:
        return {}, ""
    try:
        # Pointed at a hub that is not this machine's own, the
        # nonce belongs in THAT hub's .post/ — a rehearsal must never write a
        # file into the real post folder. An older postman still answers.
        try:
            post = pm.post_dir(hub=str(hub)) if hub else pm.post_dir()
        except TypeError:
            post = pm.post_dir()
        nonce = pm.note_nonce(post, title=title, arcs=arcs)
    except Exception:
        return {}, ""
    return {"nonce": nonce}, "  id: %s" % nonce


# --------------------------------------------------------------------------
# a bounded child process — the tree dies, never only its head
# --------------------------------------------------------------------------

def kill_tree(proc):
    """Kill a child AND every descendant.

    A plain `subprocess.run(timeout=…)` kills only the direct child: on Windows
    `git` is Git\\cmd\\git.exe, a launcher whose grandchild can keep the pipes
    open and hang a run for many minutes. Same rule as the
    engine's carrier_preflight._kill_tree; nothing here ever raises."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def run_bounded(args, cwd=None, timeout=300, env=None):
    """(returncode, combined output) — 124 when the timeout fired, 125 when it would not start.

    The tree is killed BEFORE the pipes are drained, so a grandchild can never
    hold the caller open past `timeout`. Output is decoded as UTF-8 whatever the
    console locale is (a Windows cp437 console broke this once)."""
    kw = {} if os.name == "nt" else {"start_new_session": True}
    try:
        proc = subprocess.Popen([str(a) for a in args], cwd=str(cwd) if cwd else None, env=env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, **kw)
    except Exception as exc:
        return 125, repr(exc)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, (out or b"").decode("utf-8", "replace").strip()
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=10)
        except Exception:
            out = b""
        return 124, (out or b"").decode("utf-8", "replace").strip()
    except Exception as exc:
        kill_tree(proc)
        return 125, repr(exc)


class Stop(Exception):
    """A headless command cannot be found or read; one plain sentence, no launch."""


def machine_paths(tool_file=None):
    """Machine name and roots from the shared machine.json resolver."""
    from exo_paths import paths
    return paths(tool_file=tool_file or __file__)


def _windows_process(pid):
    """Read-only handle; pointer-sized signatures matter on 64-bit Windows."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    return kernel, kernel.OpenProcess(0x1000, False, pid)


def pid_alive(pid):
    """Non-destructive liveness. Never send any signal on Windows."""
    try:
        pid = int(pid)
        if pid <= 0:
            return False
    except (ValueError, TypeError):
        return False
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        try:
            kernel, handle = _windows_process(pid)
            if not handle:
                return False
            try:
                code = wintypes.DWORD()
                return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
            finally:
                kernel.CloseHandle(handle)
        except (OSError, AttributeError):
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError as exc:
        if exc.errno == errno.EPERM:
            return True
        if exc.errno == errno.ESRCH:
            return False
        return False


def process_start_time(pid):
    """An OS birth stamp for a recorded pid, or None when it cannot be read.

    No inference from liveness: an unreadable identity never authorizes a kill.
    Windows uses creation FILETIME; Linux uses boot id + start ticks; macOS
    uses proc_pidinfo's microsecond birth time (not ps's second-granularity date).
    """
    try:
        pid = int(pid)
        if pid <= 0:
            return None
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel, handle = _windows_process(pid)
            if not handle:
                return None
            try:
                kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
                kernel.GetProcessTimes.restype = wintypes.BOOL
                times = [wintypes.FILETIME() for _ in range(4)]
                if kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                    return 'win:%d' % ((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
            finally:
                kernel.CloseHandle(handle)
        elif sys.platform == 'darwin':
            import ctypes
            # proc_bsdinfo in libproc.h: 12 uint32s, comm[16], name[32],
            # 6 uint32s, then start_tvsec/start_tvusec (uint64 each).
            class BsdInfo(ctypes.Structure):
                _fields_ = [('ids', ctypes.c_uint32 * 12), ('comm', ctypes.c_char * 16),
                            ('name', ctypes.c_char * 32), ('misc', ctypes.c_uint32 * 6),
                            ('sec', ctypes.c_uint64), ('usec', ctypes.c_uint64)]
            lib = ctypes.CDLL('/usr/lib/libproc.dylib')
            lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
            lib.proc_pidinfo.restype = ctypes.c_int
            info = BsdInfo()
            if lib.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info)) == ctypes.sizeof(info):
                return 'mac:%d:%d' % (info.sec, info.usec)
        else:
            fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            return 'proc:%s:%s' % (boot, fields[19])
    except (OSError, ValueError, TypeError, AttributeError, IndexError):
        pass
    return None


def headless_command(mind_name, os_kind, env):
    """(path, version, how_found), PATH first, then this mind's registry candidates.

    The supplied environment is authoritative, including HOME and PATH in a
    hermetic gate. A Python candidate is the gate's ordinary script fixture.
    No shell command, installer, login, or GUI is ever started by the finder.
    """
    import shutil
    e = os.environ if env is None else env
    reg = _reg()
    name = str(mind_name).strip().upper()
    aliases = {str(k).upper(): str(v).upper() for k, v in reg.get("mind_aliases", {}).items()}
    name = aliases.get(name, name)
    row = next((m for m in reg.get("minds", []) if str(m.get("name", "")).upper() == name), {})
    cfg = row.get("headless") or {}
    kind = {"darwin": "macos", "nt": "windows", "win32": "windows"}.get(os_kind, os_kind)
    exe = str(cfg.get("exe") or row.get("kind") or "")
    if not exe or row.get("kind") not in ("claude", "codex"):
        raise Stop("no headless command is registered for «%s»" % mind_name)
    hit = shutil.which(exe, path=e.get("PATH", ""))
    candidates = [(hit, "PATH")] if hit else []
    if kind == 'windows' and not exe.lower().endswith('.exe'):
        native = shutil.which(os.path.splitext(exe)[0] + '.exe', path=e.get('PATH', ''))
        if native:
            candidates.insert(0, (native, 'PATH'))
    home = e.get("USERPROFILE") if kind == "windows" else e.get("HOME")
    for item in (cfg.get("candidates") or {}).get(kind, []):
        p = str(item)
        p = re.sub(r"%([^%]+)%", lambda m: str(e.get(m[1], m[0])), p)
        p = re.sub(r"\$(?:\{([^}]+)\}|([A-Za-z_][A-Za-z_0-9]*))", lambda m: str(e.get(m[1] or m[2], m[0])), p)
        if p == "~" or p.startswith("~/") or p.startswith("~\\"):
            p = str(home or os.path.expanduser("~")) + p[1:]
        p = os.path.expandvars(p)
        if os.path.isfile(p) and (kind == "windows" or p.endswith(".py") or os.access(p, os.X_OK)):
            candidates.append((os.path.abspath(p), "candidate"))
    if not candidates:
        install = (cfg.get("install") or {}).get(kind) or "UNREAD — fill at install"
        raise Stop("the runner «%s» is not on PATH and no candidate is registered — %s" % (exe, install))
    if kind == 'windows':
        candidates.sort(key=lambda item: not item[0].lower().endswith('.exe'))
    path, how = candidates[0]
    argv = [sys.executable, path] if path.lower().endswith(".py") else [path]
    code, out = run_bounded(argv + ["--version"], timeout=10, env=dict(e))
    if code:
        raise Stop("%s CLI version probe failed (exit %s): %s" % (name, code, " ".join(out.split())[:160]))
    return os.path.abspath(path), " ".join(out.split())[:200], how
