#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""offload.py 0.1.2 — hand a written job to another mind, then read its hand-back.

In plain words. You give this tool a written job and a mind's name. It checks the
folder, finds the command, and starts the job with its input closed. The job
has a deadline and cannot open a browser. A watcher keeps its place visible,
reads the report at the end, records the measured cost, and sends one letter.
A DONE printed only in the stream is not a delivered report.

The runner keeps an exit receipt independently of the watcher. A replacement
watcher can finish an interrupted watch without launching the model again.
No credentials are stored in the record. The prompt and argv stay local.
Stdlib only, Python 3.9, macOS and Windows.

Gate seams: EXO_REGISTRY_JSON is the shared registry override;
EXO_OFFLOAD_STATE_DIR, EXO_OFFLOAD_MAIL and EXO_OFFLOAD_NOTIFY isolate records
and external effects. EXO_OFFLOAD_TOOL_DIR supplies assembled dependencies
for a staged proof. Installed tools need none of these overrides.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
USAGE = '''python3 tools/offload.py run <job.md> [--to astra|sol|luna|sonnet|opus|haiku|fable] [--in <folder>] [--reason "<why>"]
        [--kind mechanical|judgment|reading] [--report <file>] [--done "<prefix>"] [--timeout 60m]
        [--complexity simple|complex]   # flag > complexity: header > size (<4096 bytes and <=2 touches)
        [--model <id>] [--effort <level>] [--sandbox read-only|workspace-write] [--add-dir <dir> ...]
        [--work-bound] [--lane <MACHINE>/<lane>] [--routine] [--despite-dirty] [--wait] [--dry-run] [--json]
python3 tools/offload.py show <run-id | latest> [--log]      # the job's head, the command, the turns, the hand-back, the ledger line
python3 tools/offload.py jobs                                # every run on this machine still running: id · mind · title · minutes · last step
python3 tools/offload.py kill <run-id>                       # kill_tree + FAIL (killed by hand) + the letter
python3 tools/offload.py ledger [--week] [--by mind|lane]    # totals from this machine's offload ledger
python3 tools/offload.py --help'''
ALLOWED = ['Read', 'Edit', 'Write', 'Glob', 'Grep', 'Bash(python3 *)',
           'Bash(python *)', 'Bash(git status*)', 'Bash(git diff*)']
TERMINAL = ('done', 'fail', 'timeout')
MODULES = {}


class Stop(Exception):
    """One plain refusal, exit 2, with the same sentence in the local log."""


def one(value):
    return ' '.join(str(value or '').split())


def iso(at=None):
    return datetime.fromtimestamp(time.time() if at is None else at, timezone.utc).isoformat()


def epoch(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return 0.0


def tool(name):
    # A build's explicit dependency directory; installed tools need no override.
    dirs = [HERE]
    if os.environ.get('EXO_OFFLOAD_TOOL_DIR'):
        dirs.insert(0, Path(os.environ['EXO_OFFLOAD_TOOL_DIR']))
    dirs += [p / 'tools' for p in HERE.parents]
    for folder in dirs:
        if (folder / name).is_file():
            return folder / name
    raise Stop('%s is not installed beside offload.py' % name)


def module(name):
    if name not in MODULES:
        path = tool(name + '.py')
        sys.path.insert(0, str(path.parent))
        if name in sys.modules:
            MODULES[name] = sys.modules[name]
        else:
            spec = importlib.util.spec_from_file_location(name, str(path))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            MODULES[name] = mod
    return MODULES[name]


def state_dir():
    return Path(os.environ.get('EXO_OFFLOAD_STATE_DIR') or Path.home() / '.exocortex/offload')


def read_json(path, fallback=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(6):
            try:
                os.replace(str(tmp), str(path))
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(.05)
    finally:
        if tmp.exists():
            tmp.unlink()


@contextlib.contextmanager
def locked(path):
    """An OS lock dies with its owner; a killed watcher cannot leave a stale lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                f.write(b'0'); f.flush()
            f.seek(0)
            while True:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(.05)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def record_path(ident):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', ident):
        raise Stop('unknown run id')
    return state_dir() / 'runs' / (ident + '.json')


def records():
    return sorted([r for p in (state_dir() / 'runs').glob('*.json')
                   for r in [read_json(p)] if isinstance(r, dict) and r.get('id')],
                  key=lambda r: (r.get('started', ''), r['id']))


def get_record(ident):
    if ident == 'latest':
        rows = records()
        if not rows:
            raise Stop('unknown run id: latest')
        return rows[-1]
    r = read_json(record_path(ident))
    if not isinstance(r, dict):
        raise Stop('unknown run id: ' + ident)
    return r


def save(r):
    atomic(record_path(r['id']), r)


def brief_read(path):
    try:
        data = path.read_bytes()
        if len(data) > 200 * 1024:
            raise Stop('the brief is over 200 KB')
        text = data.decode('utf-8-sig')
    except (OSError, UnicodeError) as exc:
        raise Stop('cannot read the UTF-8 brief: ' + one(exc))
    lines, header, body = text.splitlines(), {}, text
    if (lines and re.match(r'^[\w-]+:\s*.*$', lines[0]) and
            any(line.strip() == '---' for line in lines[1:30])):
        key = None
        for i, line in enumerate(lines):
            if line.strip() == '---':
                body = ''.join(text.splitlines(keepends=True)[i + 1:])
                break
            m = re.match(r'^([\w-]+):\s*(.*)$', line)
            if m:
                key = m[1].lower(); header[key] = m[2]
            elif key == 'touches' and line.strip():
                header[key] += ',' + line.strip().lstrip('- ').strip()
            elif line.strip():
                raise Stop('the brief header has an unreadable line: ' + one(line))
    title = next((l[2:].strip() for l in body.splitlines() if l.startswith('# ') and l[2:].strip()), path.stem)
    return text, body, header, title


def duration(value):
    m = re.fullmatch(r'(\d+(?:\.\d+)?)([smh]?)', str(value))
    if not m or float(m[1]) <= 0:
        raise Stop('timeout must be a positive number followed by s, m or h')
    return float(m[1]) * {'': 1, 's': 1, 'm': 60, 'h': 3600}[m[2]]


def resolve(path, base):
    p = Path(os.path.expandvars(os.path.expanduser(str(path))))
    return (p if p.is_absolute() else base / p).resolve()


def mind_row(want, reg):
    name = str(want).upper()
    name = {k.upper(): str(v).upper() for k, v in reg.get('mind_aliases', {}).items()}.get(name, name)
    row = next((m for m in reg.get('minds', []) if str(m.get('name')).upper() == name), None)
    if (not row or row.get('tier') not in ('cheap', 'mechanical', 'flagship') or
            row.get('kind') not in ('claude', 'codex') or
            (row.get('kind') == 'claude' and not row.get('cli'))):
        raise Stop('«%s» is not a headless target mind' % want)
    return row


def codex_root():
    roots = module('exo_common').machine_paths(__file__).get('roots') or {}
    return Path(roots['codex']) if 'codex' in roots else Path.home() / '.codex'


def configured_model():
    """The top-level configured model, without importing a TOML package on 3.9."""
    try:
        for line in (codex_root() / 'config.toml').read_text(encoding='utf-8').splitlines():
            if line.lstrip().startswith('['):
                break
            match = re.match(r'''^\s*model\s*=\s*(["'])(.*?)\1\s*(?:#.*)?$''', line)
            if match:
                return match[2]
    except OSError:
        pass
    return None


def claude_path_rule(path):
    value = str(path).replace('\\', '/')
    if re.match(r'^[A-Za-z]:/', value):
        value = '/' + value[0].lower() + value[2:]
    # Escape gitignore pattern characters: this rule names one literal file.
    value = re.sub(r'([*?\[\]])', r'\\\1', value)
    return '/' + value


def prompt_argument(prompt, path):
    pointer = os.name == 'nt' or len(prompt.encode('utf-8')) > 30000
    if pointer:
        return ('Read the file %s in full and follow it as your brief; its first rule binds before you read it: '
                'launch no browser or GUI application.' % path), True
    return prompt, False


def complexity_of(flag, header, brief_bytes):
    """The caller's word wins; size counts the entire UTF-8 file, not characters."""
    paths = [p.strip() for p in header.get('touches', '').split(',') if p.strip()]
    by = 'flag' if flag else 'header' if header.get('complexity') else 'size'
    value = flag or header.get('complexity') or ('simple' if brief_bytes < 4096 and len(paths) <= 2 else 'complex')
    if value not in ('simple', 'complex'):
        raise Stop('complexity must be simple or complex')
    if by == 'size':
        reason = '%s by size (%s B · %d %s)' % (value, format(brief_bytes, ','), len(paths),
                                               'path' if len(paths) == 1 else 'paths')
    else:
        reason = '%s (%s)' % (value, '--complexity' if by == 'flag' else 'complexity: header')
    return value, by, reason, len(paths)


def default_mind(reg, vendor, kind, complexity='simple'):
    if vendor not in ('claude', 'codex'):
        raise Stop("name --to: this caller's vendor is %s" % (vendor or 'unknown'))
    other = 'codex' if vendor == 'claude' else 'claude'
    candidates = [m for m in reg.get('minds', []) if m.get('kind') == other and
                  m.get('tier') in ('cheap', 'mechanical', 'flagship')]
    mechanical = ('flagship' if complexity == 'complex' else 'mechanical') if other == 'codex' else (
        'mechanical' if complexity == 'complex' else 'cheap')
    tier = {'reading': 'cheap', 'mechanical': mechanical, 'judgment': 'flagship'}[kind]
    choices = [m for m in candidates if m.get('tier') == tier]
    if not choices:
        raise Stop('name --to: no %s %s mind is registered' % (other, tier))
    # Two minds can share a tier but serve different kinds (reader / builder).
    preferred = [m for m in choices if kind in (m.get('offload_default_for') or [])]
    choices = preferred or choices
    # Stable across registry reordering; no persona word is a routing rule.
    return min(choices, key=lambda m: str(m['name']).casefold())['name']


def route(row, kind, model, reason, routine, header):
    tier = row['tier']
    models = row.get('models') or {}
    # --to names the mind, not a kind-specific model from its shared model map.
    selected = model or row.get('cli_model') or models.get(tier)
    unset = row['kind'] == 'codex' and not selected
    if row['kind'] == 'codex':
        actual = selected or configured_model() or 'CLI configured model (unreadable)'
        passed = selected
    else:
        passed = model or selected or row.get('cli')
        actual = model or selected or row.get('app_id') or passed
    # Recognize overrides by registered ids, not substrings of persona names.
    reg = module('exo_common')._reg()
    flagship_ids = {value for m in reg.get('minds', []) if m.get('tier') == 'flagship'
                    for value in (m.get('app_id'), m.get('cli'), m.get('cli_model'), (m.get('models') or {}).get('flagship')) if value}
    registered_tiers = {m.get('tier') for m in reg.get('minds', [])
                        if actual in (m.get('app_id'), m.get('cli'), m.get('cli_model'))}
    registered_tiers.update(t for m in reg.get('minds', []) for t, value in (m.get('models') or {}).items()
                            if value == actual and t in ('cheap', 'mechanical', 'flagship'))
    flagship = (actual in flagship_ids or passed in flagship_ids or
                (tier == 'flagship' and (not model or not registered_tiers)))
    # R2 authorizes the registered OpenAI flagship for complex builds and an
    # explicit flagship mind. Routine and kind guards below still apply.
    ruled_default = (not model and row['kind'] == 'codex' and tier == 'flagship' and
                     bool(models.get('flagship')) and actual == models['flagship'])
    warnings = []
    if routine and kind == 'judgment':
        raise Stop('judgment cannot run a routine — refused outright')
    if kind == 'judgment' and (tier != 'flagship' or not flagship or
                              (model and actual not in flagship_ids and passed not in flagship_ids)):
        raise Stop('judgment needs a flagship — the step-down law forbids this mind')
    if kind == 'reading' and (tier != 'cheap' or flagship or
                             (model and 'cheap' not in registered_tiers)):
        raise Stop('reading goes to a cheap reader — the Routine-model law')
    if unset and actual.endswith('(unreadable)') and (routine or kind == 'reading'):
        raise Stop("cannot verify the CLI's configured model for this reading or routine job")
    if routine and flagship:
        raise Stop('a flagship cannot run a routine — the Routine-model law; a reason does not lift it')
    if kind == 'mechanical' and flagship and not ruled_default:
        why = reason or (header.get('model-reason') if routine else '')
        if not why:
            raise Stop('a flagship for a mechanical job needs --reason')
        warnings.append('WARN: a flagship for a mechanical job — ' + one(why))
    return actual, passed, unset, flagship, warnings


def tracked_changes(folder, touches, despite=False, runner=None):
    """Porcelain -z keeps spaces, quotes, newlines and both sides of renames exact.
    The optional runner is an in-process gate seam; never an environment bypass.
    """
    root = next((p for p in [folder] + list(folder.parents) if (p / '.git').exists()), None)
    if root is None:
        return []
    call = runner or module('exo_common').run_bounded
    code, out = call(['git', '--no-optional-locks', 'status', '--porcelain', '-z', '--untracked-files=no'],
                     cwd=root, timeout=10, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    if code:
        raise Stop('cannot check tracked changes in %s: %s' % (folder, one(out)))
    # run_bounded strips whitespace at the boundaries; protect the leading XY
    # column by using its returned line's first status token length.
    changes, chunks = [], out.split('\0')
    i = 0
    while i < len(chunks):
        chunk = chunks[i]; i += 1
        if not chunk:
            continue
        if chunk.startswith('??'):
            continue
        if len(chunk) > 2 and chunk[2] == ' ':
            status, name = chunk[:2], chunk[3:]
        else:
            status, _, name = chunk.partition(' ')
        names = [name]
        if 'R' in status or 'C' in status:
            if i < len(chunks):
                names.append(chunks[i]); i += 1
        for name in names:
            changed = resolve(name, root)
            if not touches or any(changed == p or p in changed.parents or changed in p.parents for p in touches):
                changes.append(name)
    changes = sorted(set(changes))
    if changes and not despite:
        raise Stop('%d files are changed and uncommitted in %s (%s) — commit the build in flight first, or pass --despite-dirty' %
                   (len(changes), folder, ', '.join(one(n) for n in changes[:3])))
    return changes


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).casefold()


def scrub(text, reg, allow):
    classes = [
        ('personal filesystem path', ['/Users/', 'C:\\Users\\', '~/']),
        ('machine identity', ['home machine'] +
         [str(v.get('label') or k) for k, v in reg.get('machines', {}).items()]),
        ('mind or vendor', ['Claude', 'Codex', 'ChatGPT', 'GPT', 'Anthropic', 'OpenAI'] +
         [m['name'] for m in reg.get('minds', [])] + list(reg.get('mind_aliases', {}))),
        ('side word', ['work machine', 'work-side', 'at work', 'work repo', 'work clone',
                       'work mirror', 'work session', 'work computer', 'work brief', 'ferry', 'scan', 'screenshot', 'photo']),
        ('third-party mark', ['PROPRIETARY', 'EXPORT CONTROLLED', 'ITAR', 'EAR', 'CONFIDENTIAL'])]
    cleared = {folded(x) for x in allow}
    for n, line in enumerate(text.splitlines(), 1):
        s = folded(line)
        for category, words in classes:
            for word in words:
                w = folded(word)
                if not w or w in cleared:
                    continue
                pattern = re.escape(w) if category == 'personal filesystem path' else r'(?<!\w)' + re.escape(w) + r'(?!\w)'
                if re.search(pattern, s):
                    raise Stop('scrub — line %d: «%s» carries «%s» (%s)' % (n, one(line), word, category))


def prepare(a):
    brief = Path(a.brief).resolve()
    text, body, header, title = brief_read(brief)
    choose = lambda key, fallback=None: getattr(a, key.replace('-', '_'), None) or header.get(key) or fallback
    common, protector = module('exo_common'), module('protector')
    reg = common._reg()
    caller = common.session_identity()
    # The shared reader truthfully returns {} for a Codex shell. An explicit
    # CODEX_HOME marker is only a vendor hint; it is never a session id.
    vendor = caller.get('vendor') or ('codex' if os.environ.get('CODEX_HOME') or os.environ.get('CODEX_THREAD_ID') else '')
    kind = choose('kind', 'mechanical')
    if kind not in ('mechanical', 'reading', 'judgment'):
        raise Stop('kind must be mechanical, judgment or reading')
    brief_bytes = brief.stat().st_size
    complexity, complexity_by, complexity_reason, touches_count = complexity_of(a.complexity, header, brief_bytes)
    named = choose('to')
    want = named or default_mind(reg, vendor, kind, complexity)
    row = mind_row(want, reg)
    model, passed_model, unset, flagship, warnings = route(row, kind, a.model, a.reason, a.routine, header)
    routing_reason = complexity_reason
    if kind != 'mechanical':
        routing_reason = ('reading → cheap reader' if kind == 'reading' else 'judgment → flagship') + ' · ' + routing_reason
    if named:
        routing_reason += ' · mind named by ' + ('--to' if a.to else 'to: header')
    if not hasattr(common, 'headless_command'):
        raise Stop('install the BQ-364 exo_common finder patch before running a job')
    try:
        exe, version, found = common.headless_command(row['name'], 'windows' if os.name == 'nt' else 'macos', os.environ)
    except common.Stop as exc:
        raise Stop(str(exc))
    # A status probe reads sign-in; it never starts the interactive login road.
    # The documented commands are `claude auth status` and `codex login status`.
    removed = sorted(k for k in os.environ if row['kind'] == 'claude' and
                     (k.startswith('CLAUDE_CODE') or k == 'CLAUDECODE'))
    auth_checked = None
    if not a.dry_run:
        auth_env = dict(os.environ, CHROME='/nonexistent', BROWSER='/nonexistent',
                        PYTHONDONTWRITEBYTECODE='1')
        for key in removed:
            auth_env.pop(key, None)
        auth_head = [sys.executable, exe] if exe.lower().endswith('.py') else [exe]
        auth_args = ['auth', 'status'] if row['kind'] == 'claude' else ['login', 'status']
        code, auth = common.run_bounded(auth_head + auth_args, timeout=10, env=auth_env)
        signed = True
        try:
            status = json.loads(auth)
            if isinstance(status, dict) and status.get('loggedIn') is False:
                signed = False
        except ValueError:
            pass
        if code or not signed:
            raise Stop('%s CLI is not signed in or its status could not be read: %s' %
                       (row['name'], one(auth)[:180]))
        auth_checked = iso()
    folder = resolve(choose('in', str(brief.parent)), brief.parent)
    if not folder.is_dir():
        raise Stop('the job folder does not exist: ' + str(folder))
    touches = [resolve(p.strip(), folder) for p in header.get('touches', '').split(',') if p.strip()]
    changes = tracked_changes(folder, touches, a.despite_dirty)
    work_bound = a.work_bound or header.get('work-bound', '').lower() in ('yes', 'true', '1')
    if work_bound:
        scrub(body, reg, a.scrub_allow)
    report = resolve(choose('report', str(brief.with_name(brief.stem + '-REPORT.md'))), brief.parent)
    done = choose('done', 'DONE ' + ' '.join(title.split()[:4]))
    if '\n' in done or not done.strip():
        raise Stop('the DONE prefix must be one nonempty line')
    timeout = duration(choose('timeout', '60m'))
    started = time.time()
    ident = datetime.now().strftime('%Y%m%d-%H%M-') + row['name'].lower() + '-' + uuid.uuid4().hex[:4]
    run = state_dir() / 'runs' / ident
    sandbox = a.sandbox or 'workspace-write'
    extra = [resolve(d, folder) for d in (a.add_dir or [])]
    if any(not d.is_dir() for d in extra):
        raise Stop('an --add-dir folder does not exist')
    if sandbox == 'read-only' and not any(report.parent == d or d in report.parent.parents for d in extra):
        raise Stop('read-only has no place for the hand-back; --add-dir must cover the report folder')
    # The reader's root is the report folder. Source paths stay readable.
    cwd = report.parent if kind == 'reading' and row['kind'] == 'codex' else folder
    log = brief.with_name(brief.stem + '-RUN-' + ident + '.log')
    for dest in (report.parent, log.parent):
        if dest != folder and folder not in dest.parents and dest not in extra:
            extra.append(dest)
    writable = list(dict.fromkeys(([str(cwd)] if sandbox == 'workspace-write' else []) + [str(d) for d in extra]))
    preamble = (HERE / 'fixtures/offload/preamble.md').read_text(encoding='utf-8')
    if work_bound:
        # Only fixed words and authored body travel with the job's content.
        # Substitutions are tool-owned paths/contract values, not authored prose.
        scrub(re.sub(r'\{[a-z_]+\}', '', preamble), reg, a.scrub_allow)
    folder_rule = ('read your sources in %s' if kind == 'reading' else 'Work in %s') % folder
    prompt = preamble.format(report=report, done_prefix=done, sandbox=sandbox, folder_rule=folder_rule) + '\n' + body
    prompt_arg, pointer = prompt_argument(prompt, run / 'prompt.md')
    if exe.lower().endswith('.cmd') and not pointer:
        raise Stop('a .cmd runner requires the one-line prompt pointer')
    effort = a.effort or (row.get('cheap_effort') if a.routine else None) or ('medium' if kind == 'reading' else 'high')
    env_add = {'CHROME': '/nonexistent', 'BROWSER': '/nonexistent', 'EXO_OFFLOAD_RUN': ident,
               'NO_COLOR': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    env = dict(os.environ, **env_add)
    for key in removed:
        env.pop(key, None)
    head = [sys.executable, exe] if exe.lower().endswith('.py') else [exe]
    if row['kind'] == 'codex':
        argv = head + ['exec', '--json', '--color', 'never', '--skip-git-repo-check', '-s', sandbox, '-C', str(cwd)]
        for d in extra:
            argv += ['--add-dir', str(d)]
        if passed_model:
            argv += ['-m', passed_model]
        argv += ['-c', 'model_reasoning_effort=' + effort, '-o', str(run / 'last-message.md'), '--', prompt_arg]
        cap = None
        write_scope = 'workspace'
    else:
        cap = '5' if row['tier'] == 'cheap' else '15'
        # Claude's // form anchors an absolute path (a single / is project-relative).
        scoped_path = claude_path_rule(report)
        allowed = (['Read', 'Glob', 'Grep', 'Write(%s)' % scoped_path, 'Edit(%s)' % scoped_path]
                   if kind == 'reading' or sandbox == 'read-only' else ALLOWED)
        write_scope = 'report' if kind == 'reading' or sandbox == 'read-only' else 'workspace'
        argv = head + ['-p', '--model', passed_model, '--effort', effort, '--output-format', 'stream-json',
                       '--verbose', protector.claude_quiet_flag(env), '--no-session-persistence',
                       '--max-budget-usd', cap, '--permission-mode', 'default', '--add-dir', str(folder)]
        for d in extra:
            argv += ['--add-dir', str(d)]
        argv += ['--allowedTools'] + allowed + ['--', prompt_arg]
    lane = choose('lane') or caller.get('lane')
    lane_defaulted = False
    if not lane:
        machine = common.machine_paths(__file__).get('machine') or ''
        title_hint = caller.get('title') or os.environ.get('EXO_SESSION_TITLE', '')
        token = common.lane_token(title_hint) if title_hint else ''
        if not machine:
            raise Stop('machine.json does not name this machine for the hand-back address')
        lane_defaulted = not token
        lane = str(machine).upper() + '/' + (token or 'hub')
    caller.update(vendor=vendor or 'unknown', title=caller.get('title') or os.environ.get('EXO_SESSION_TITLE', ''), lane=lane)
    r = dict(id=ident, run_id=ident, started=iso(started), deadline=iso(started + timeout), timeout=timeout,
             caller=caller, lane=lane, mind=row['name'], vendor=row['kind'], model=model, model_id=model,
             effort=effort, kind=kind, tier=row['tier'], argv=argv, cwd=str(cwd), source_folder=str(folder),
             complexity=complexity, complexity_by=complexity_by, complexity_reason=complexity_reason,
             routing_reason=routing_reason, brief_bytes=brief_bytes, touches_count=touches_count,
             writable=writable, write_scope=write_scope, prompt_pointer=pointer, env_additions=env_add, env_removed=removed,
             brief=str(brief), brief_title=title, title=title, header=header, prompt=str(run / 'prompt.md'),
             log=str(log), report=str(report), done_prefix=done, lane_defaulted=lane_defaulted,
             resolved_path=exe, version=version, how_found=found, auth_checked=auth_checked, state='starting', pid=None, pgid=None,
             minutes=0, last_step='starting', log_bytes=0, despite_dirty=bool(a.despite_dirty), dirty_files=changes,
             scrub_allow=a.scrub_allow, work_bound=bool(work_bound), reason=a.reason or '', routine=a.routine,
             mechanical_unset=unset, unattended_flagship=flagship and row['kind'] == 'claude', cap_usd=cap,
             warnings=warnings, report_before=report_fingerprint(report), sandbox=sandbox)
    return r, prompt, env


def report_fingerprint(path):
    try:
        p = Path(path)
        return [p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()]
    except OSError:
        return None


def detached():
    if os.name == 'nt':
        return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS, 'close_fds': True}
    return {'start_new_session': True, 'close_fds': True}


def child_env(r):
    env = dict(os.environ, **r['env_additions'])
    removed = set(r['env_removed'])
    if r['vendor'] == 'claude':
        removed.update(k for k in env if k.startswith('CLAUDE_CODE') or k == 'CLAUDECODE')
    for key in removed:
        env.pop(key, None)
    return env


def run_folder(r):
    return Path(r['prompt']).parent


def execute(ident):
    """Own the actual child so its exit code survives a detached caller/watch."""
    r = get_record(ident)
    root = run_folder(r)
    try:
        for attempt in range(2):
            with open(r['log'], 'a', encoding='utf-8', newline='\n') as log:
                proc = subprocess.Popen(r['argv'], cwd=r['cwd'], env=child_env(r), stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, **detached())
                pid = {'pid': proc.pid, 'pgid': proc.pid, 'executor': os.getpid(),
                       'process_start': module('exo_common').process_start_time(proc.pid)}
                atomic(root / 'pid.json', pid)
                left = max(.01, epoch(r['deadline']) - time.time())
                try:
                    code = proc.wait(timeout=left)
                except subprocess.TimeoutExpired:
                    r.update(pid)
                    if not kill_job(r):
                        atomic(root / 'exit.json', {'code': 125, 'kill_skipped': True, 'ended': iso()})
                        return 0
                    code = proc.wait(timeout=10)
                    atomic(root / 'exit.json', {'code': code, 'timeout': True, 'ended': iso()})
                    return 0
            # Only an explicit denial of this report path demonstrates a path
            # rule the CLI did not honor. No retry on a hang, login or tool error.
            if attempt or not reading_scope_denied(r, code):
                break
            with locked(root / 'record.lock'):
                r = get_record(ident)
                if r['state'] in TERMINAL or time.time() >= epoch(r['deadline']) or (root / 'kill.json').exists():
                    break
                r.setdefault('attempts', []).append({'argv': r['argv'][:], 'write_scope': r['write_scope'], 'exit_code': code})
                result = next(e for e in reversed(list(events(r))) if e.get('type') == 'result')
                cost = result.get('total_cost_usd')
                if not isinstance(cost, (int, float)) or cost < 0 or cost >= float(r['cap_usd']):
                    r['scope_fallback_blocked'] = 'remaining CLI budget is unknown or exhausted'
                    r['attempts'].pop()
                    save(r)
                    break
                budget_at = r['argv'].index('--max-budget-usd') + 1
                r['argv'][budget_at] = str(round(float(r['cap_usd']) - cost, 8))
                at = r['argv'].index('--allowedTools') + 1
                end = r['argv'].index('--', at)
                r['argv'][at:end] = ['Read', 'Glob', 'Grep', 'Write', 'Edit']
                r['write_scope'] = 'unscoped'
                r['scope_fallback_reason'] = 'CLI denied the path-scoped report write'
                save(r)
        atomic(root / 'exit.json', {'code': code, 'ended': iso()})
    except Exception as exc:
        atomic(root / 'exit.json', {'code': 125, 'error': one(exc), 'ended': iso()})
    return 0


def alive(pid):
    return module('exo_common').pid_alive(pid)


def kill_job(r):
    receipt = read_json(run_folder(r) / 'pid.json', {}) or {}
    pid = receipt.get('pid') or r.get('pid')
    expected = receipt.get('process_start') if receipt.get('pid') else r.get('process_start')
    common = module('exo_common')
    if not pid or not expected or common.process_start_time(pid) != expected:
        r['kill_note'] = 'kill skipped: pid not confirmed'
        return False
    class Child:
        def __init__(self, value):
            self.pid = value
        def kill(self):
            # kill_tree's group/taskkill already acted; recheck before its
            # fallback signal, which could otherwise land on a recycled pid.
            if os.name != 'nt' and common.process_start_time(self.pid) == expected:
                os.kill(self.pid, signal.SIGKILL)
    common.kill_tree(Child(int(pid)))
    return True


def reading_scope_denied(r, code):
    if r['vendor'] != 'claude' or r['kind'] != 'reading' or r.get('write_scope') != 'report':
        return False
    if contract(r, code)[0] == 'done':
        return False
    result = next((e for e in reversed(list(events(r))) if e.get('type') == 'result'), {})
    for denial in result.get('permission_denials') or []:
        if not isinstance(denial, dict) or denial.get('tool_name') not in ('Write', 'Edit'):
            continue
        path = (denial.get('tool_input') or {}).get('file_path')
        if path and resolve(path, Path(r['cwd'])) == Path(r['report']):
            return True
    return False


def receipt_result(r, receipt):
    """The delivered contract wins over CLI diagnostics; keep both as facts."""
    r['exit_code'] = receipt['code']
    if receipt.get('kill_skipped'):
        r['state'], r['result'] = 'fail', 'kill skipped: pid not confirmed'
    elif receipt.get('timeout'):
        r['state'], r['result'] = 'timeout', 'TIMEOUT — deadline reached'
    else:
        r['state'], r['result'] = contract(r, receipt['code'])
        if receipt.get('error') and r['state'] != 'done':
            r['state'], r['result'] = 'fail', 'runner did not start: ' + receipt['error']
    denials, errors = [], []
    for ev in events(r):
        if ev.get('type') == 'result':
            denials.extend(ev.get('permission_denials') or [])
            if ev.get('is_error'):
                errors.append(one(ev.get('result') or ev.get('subtype') or 'unspecified CLI error'))
        elif ev.get('type') in ('error', 'turn.failed'):
            errors.append(one(ev.get('message') or (ev.get('error') or {}).get('message') or 'unspecified CLI error'))
    r['permission_denials'], r['is_error'], r['cli_error'] = denials, bool(errors), '; '.join(errors)
    if r['state'] not in ('done', 'timeout') and errors and not receipt.get('kill_skipped'):
        r['state'], r['result'] = 'fail', 'CLI error: ' + r['cli_error']
    if denials:
        r['result'] += ' · %d tool denials' % len(denials)
    if errors:
        r['result'] += ' · cli error: ' + r['cli_error']


def events(r, tail=False):
    try:
        with open(r['log'], 'rb') as f:
            if tail:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 512 * 1024))
                if size > 512 * 1024:
                    f.readline()  # never parse the fragment of a JSON event
            for line in f:
                try:
                    ev = json.loads(line.decode('utf-8', 'replace'))
                except ValueError:
                    continue
                if isinstance(ev, dict):
                    yield ev
    except OSError:
        return


def turns(r, tail=False):
    out = []
    for ev in events(r, tail=tail):
        item = ev.get('item') or {}
        if ev.get('type') == 'item.completed':
            if item.get('type') in ('agent_message', 'assistant_message'):
                out.append('message: ' + one(item.get('text')))
            elif item.get('type') in ('command_execution', 'command', 'file_change'):
                out.append('tool: ' + one(item.get('command') or item.get('changes') or item.get('type')))
        if ev.get('type') == 'assistant':
            for block in (ev.get('message') or {}).get('content') or []:
                if block.get('type') == 'text':
                    out.append('message: ' + one(block.get('text')))
                elif block.get('type') == 'tool_use':
                    args = block.get('input') or {}
                    out.append('tool: %s %s' % (block.get('name'), one(next(iter(args.values()), ''))))
    return out


def progress(r):
    steps = [x[6:] for x in turns(r, tail=True) if x.startswith('tool: ')]
    if steps:
        r['last_step'] = steps[-1]
    for ev in events(r, tail=True):
        if ev.get('type') == 'thread.started' and ev.get('thread_id'):
            r['thread_id'] = ev['thread_id']
    r['minutes'] = round(max(0, time.time() - epoch(r['started'])) / 60, 3)
    try:
        r['log_bytes'] = Path(r['log']).stat().st_size
    except OSError:
        r['log_bytes'] = 0


def contract(r, code):
    path = Path(r['report'])
    try:
        lines = [s for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
    except (OSError, UnicodeError):
        return 'fail', 'no report: ' + str(path)
    last = lines[-1] if lines else ''
    if last.startswith('FAIL'):
        return 'fail', last
    if last.startswith(r['done_prefix']):
        if report_fingerprint(path) == r.get('report_before'):
            return 'fail', 'report unchanged since this job started'
        return 'done', last
    if code:
        try:
            log = [x for x in Path(r['log']).read_text(encoding='utf-8', errors='replace').splitlines() if x.strip()]
        except OSError:
            log = []
        return 'fail', 'exit %s: %s' % (code, one(log[-1] if log else 'no error line'))
    return 'fail', 'no DONE line (last line: «%s»)' % one(last)


def tokens_and_cost(r):
    p = module('protector')
    evs = list(events(r, tail=True))
    text = '\n'.join(json.dumps(e) for e in evs)
    if r['vendor'] == 'codex':
        _text, tokens, _model, cost, _bad, _error = p.codex_shape(text)
        model = r['model']
        usage = next((e['usage'] for e in reversed(evs) if e.get('type') == 'turn.completed' and isinstance(e.get('usage'), dict)), {})
        if tokens is not None:
            tokens['reasoning'] = usage.get('reasoning_output_tokens')
        else:
            # Reuse the meter's cumulative-counter arithmetic; never a second
            # rollout token reader. Its current API does not expose reasoning.
            u = module('usage')
            roots = module('exo_common').machine_paths(__file__).get('roots') or {}
            roots = dict(roots, codex=str(codex_root()))
            since = datetime.fromtimestamp(epoch(r['started']) - 60, timezone.utc)
            thread_id = r.get('thread_id')
            if not thread_id:
                found = []
                for path, _mtime in u.codex_rollouts(roots, since.timestamp()):
                    if module('exo_common').codex_cwd(Path(path)) != r['cwd']:
                        continue
                    try:
                        with open(path, encoding='utf-8') as f:
                            first = json.loads(f.readline(65536))
                        meta = first.get('payload') or {}
                        began = epoch(meta.get('timestamp') or first.get('timestamp'))
                        if meta.get('source') == 'exec' and int(began // 60) == int(epoch(r['started']) // 60):
                            found.append(meta.get('id') or Path(path).stem[-36:])
                    except (OSError, ValueError):
                        continue
                if len(found) == 1:
                    thread_id = found[0]
                    r['thread_id'] = thread_id
            rows = u.codex_rows(roots, since, datetime.now(timezone.utc) + timedelta(seconds=1)) if thread_id else []
            rows = [x for x in rows if str(x['session']).endswith(thread_id)]
            if rows:
                tokens = {a: sum(x[b] for x in rows) for a, b in
                          [('input', 'fresh'), ('cache_write', 'cwrite'), ('cache_read', 'cached'), ('output', 'out')]}
                tokens['reasoning'] = None
                model = rows[-1]['model']
    else:
        # A path-rule fallback is a second paid CLI attempt under the same
        # deadline/cap. Count every result, not just the final success.
        results = [e for e in events(r) if e.get('type') == 'result']
        shaped = [p.claude_shape(obj) for obj in results]
        model = next((s[2] for s in reversed(shaped) if s[2]), r['model'])
        tokens = None
        if shaped and all(s[1] is not None for s in shaped):
            tokens = {k: sum(s[1][k] for s in shaped) for k in ('input', 'cache_write', 'cache_read', 'output')}
            reasoning = [(obj.get('usage') or {}).get('reasoning_output_tokens') for obj in results]
            tokens['reasoning'] = sum(reasoning) if all(isinstance(n, int) for n in reasoning) else None
        cost = sum(s[3] for s in shaped) if shaped and all(s[3] is not None for s in shaped) else None
    rate = p.price_of(model)
    return {'time': iso(), 'run_id': r['id'], 'vendor': r['vendor'], 'mind': r['mind'],
            'model_id': model, 'kind': r['kind'], 'lane': r['lane'], 'title': r['title'],
            'minutes': r['minutes'], 'state': r['state'], 'tokens': tokens,
            'token_status': 'known' if tokens is not None else 'tokens unknown',
            'cli_cost_usd': cost, 'usd_at_list': p.dollars(tokens, rate),
            'rate_status': 'list' if rate else 'no rate',
            'usd_at_flagship': p.dollars(tokens, p.fable_row()[1]),
            'report': r['report'], 'result': r['result']}


def ledger_once(row):
    path = state_dir() / 'offload-ledger.jsonl'
    with locked(state_dir() / 'ledger.lock'):
        old = ledger_rows(path)
        if any(x.get('run_id') == row['run_id'] for x in old):
            return next(x for x in old if x.get('run_id') == row['run_id'])
        # Repair only a crash-truncated final line; never lose complete rows.
        if path.exists():
            data = path.read_bytes()
            if data and not data.endswith(b'\n'):
                with path.open('r+b') as f:
                    f.truncate(data.rfind(b'\n') + 1)
        p = module('protector')
        opts = p.Opts(state_dir=str(state_dir()))
        if not p.ledger_append(opts, {}, row=row, filename=path.name, durable=True):
            raise Stop('the offload ledger could not be written')
    return row


def ledger_rows(path=None):
    try:
        lines = (path or state_dir() / 'offload-ledger.jsonl').read_text(encoding='utf-8').splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except ValueError:
            pass
    return out


def notice(r, start):
    title = 'Exocortex · %s job %s' % (r['mind'], 'started' if start else r['state'].upper())
    if start:
        body = '«%s» · %s · ends by %s' % (r['title'], r['lane'], datetime.fromtimestamp(epoch(r['deadline'])).strftime('%H:%M'))
    else:
        body = '«%s» · %.1f min · %s' % (r['title'], r['minutes'], r['result'][:60])
    pm = module('postman')
    argv, additions, flags, how = pm.notify_command(title, '', body, notify=os.environ.get('EXO_OFFLOAD_NOTIFY'))
    if not argv:
        return 'no notifier for this OS'
    # The renderer supplies Windows CREATE_NO_WINDOW; the subprocess rail has
    # stdin closed and a bounded wait, exactly as on the other platform.
    kw = {'creationflags': flags} if os.name == 'nt' and flags else {}
    try:
        proc = subprocess.Popen(argv, env=dict(os.environ, **additions), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        proc.wait(timeout=10)
        return '' if proc.returncode == 0 else 'notifier exit %s' % proc.returncode
    except Exception as exc:
        if 'proc' in locals():
            proc.kill()
        return one(exc)


def banner_identity(r):
    """Company and product belong to the job's registry row, not the caller."""
    try:
        row = mind_row(r['mind'], module('exo_common')._reg())
    except Exception:
        row = {}
    vendor = one(row.get('vendor')).upper()
    company = vendor if vendor in ('OPENAI', 'ANTHROPIC', 'XAI') else one(r['mind'])
    return company, one(row.get('kind') or r.get('vendor')).upper()


def banner_out(r):
    company, product = banner_identity(r)
    return ('---\n**⇢ SENT TO %s** `%s · %s · BACKGROUND` — «%s» · back by %s · '
            '**nothing for you to do**\n---') % (
                company, one(r['mind']), product, one(r['title']),
                datetime.fromtimestamp(epoch(r['deadline'])).strftime('%H:%M'))


def banner_back(r):
    company, _ = banner_identity(r)
    state = {'done': 'DONE', 'fail': 'FAILED', 'timeout': 'TIMED-OUT'}.get(r['state'], r['state'].upper())
    if r['state'] == 'fail' and r.get('result') == 'killed by hand':
        state = 'KILLED'
    return ('---\n**⇠ BACK FROM %s** `%s · %.1f min` — «%s» %s · %s · check owed here\n---') % (
        company, one(r['mind']), r['minutes'], one(r['title']), state, one(r.get('result'))[:80])


def finish(r):
    """Recoverable finalization; the ledger commit precedes external effects."""
    if not r.get('ledger'):
        try:
            row = tokens_and_cost(r)
        except Exception as exc:
            row = {k: r.get(k) for k in ('vendor', 'mind', 'model_id', 'kind', 'lane', 'title',
                                        'minutes', 'state', 'report', 'result')}
            row.update(time=iso(), run_id=r['id'], tokens=None, token_status='tokens unknown',
                       cli_cost_usd=None, usd_at_list=None, usd_at_flagship=None,
                       rate_status='unreadable', accounting_error=one(exc))
        r['ledger'] = ledger_once(row)
        save(r)
    if not r.get('letter_attempted'):
        r['letter_attempted'] = iso(); save(r)
        text = '%s job «%s» %s in %.1f min — report %s' % (r['mind'], r['title'], r['state'].upper(), r['minutes'], r['report'])
        text = banner_back(r) + '\n' + text
        mail = os.environ.get('EXO_OFFLOAD_MAIL') or str(tool('mail.py'))
        code, output = module('exo_common').run_bounded([sys.executable, mail, '--send', r['lane'], 'offload', text, 'read-report'], timeout=30)
        r['letter_status'] = 'sent' if code == 0 else 'failed: ' + one(output)
        save(r)
    if not r.get('end_notice_attempted'):
        r['end_notice_attempted'] = iso(); save(r)
        r['end_notice_error'] = notice(r, False); save(r)


def watch(ident, foreground=False):
    r = get_record(ident)
    next_beat = time.time() + 30
    next_refresh = 0
    try:
        while True:
            with locked(run_folder(r) / 'record.lock'):
                r = get_record(ident)
                r['watcher_pid'] = os.getpid()
                if r['state'] in TERMINAL:
                    finish(r)
                    return {'done': 0, 'fail': 3, 'timeout': 4}[r['state']]
                pid = read_json(run_folder(r) / 'pid.json', {})
                r.update({k: pid[k] for k in ('pid', 'pgid', 'executor', 'process_start') if k in pid})
                receipt = read_json(run_folder(r) / 'exit.json')
                manual = (run_folder(r) / 'kill.json').exists()
                refreshed = time.time() >= next_refresh or receipt or manual or time.time() >= epoch(r['deadline'])
                if refreshed:
                    progress(r)
                    next_refresh = time.time() + 30
                if receipt:
                    receipt_result(r, receipt)
                elif time.time() >= epoch(r['deadline']):
                    killed = kill_job(r)
                    r['state'], r['result'] = ('timeout', 'TIMEOUT — deadline reached') if killed else ('fail', r['kill_note'])
                elif manual:
                    killed = kill_job(r)
                    r['state'], r['result'] = 'fail', 'killed by hand' if killed else r['kill_note']
                elif not alive(r.get('executor')) and time.time() - epoch(r['started']) > 10:
                    killed = kill_job(r)
                    r['state'], r['result'] = 'fail', 'runner vanished without an exit receipt' if killed else r['kill_note']
                if r['state'] in TERMINAL:
                    r['ended'] = iso()
                if refreshed or r['state'] in TERMINAL:
                    save(r)
                if r['state'] in TERMINAL:
                    finish(r)
                    return {'done': 0, 'fail': 3, 'timeout': 4}[r['state']]
            if foreground and time.time() >= next_beat:
                seconds = int(time.time() - epoch(r['started']))
                print('%02d:%02d · %s · «%s» · last: %s' % (seconds // 60, seconds % 60, r['mind'], r['title'], short_step(r['last_step'])), flush=True)
                next_beat = time.time() + 30
            time.sleep(.2)
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            kill_job(r)
        with locked(run_folder(r) / 'record.lock'):
            r = get_record(ident)
            if r['state'] not in TERMINAL:
                killed = kill_job(r)
                r.update(state='fail', result='watcher failed: ' + one(exc) + ('' if killed else ' · ' + r['kill_note']), ended=iso())
            save(r)
        raise
    finally:
        # SIGKILL cannot execute finally; a new _watch replays the durable
        # record/exit receipt, then this same finalization, once per run id.
        with locked(run_folder(r) / 'record.lock'):
            r = get_record(ident)
            if r['state'] in TERMINAL:
                finish(r)


def start(a):
    if a.dry_run:
        print('dry-run · probed: CLI version, git status · ran: nothing', flush=True)
    r, prompt, env = prepare(a)
    if a.dry_run:
        print(json.dumps({'argv': r['argv'], 'env_additions': r['env_additions'], 'env_removed': r['env_removed'],
                          'prompt_head': prompt.splitlines()[:20], 'contract': {'report': r['report'], 'done_prefix': r['done_prefix']},
                          'warnings': r['warnings']}, ensure_ascii=False, indent=2))
        return 0
    root = run_folder(r)
    root.mkdir(parents=True)
    Path(r['report']).parent.mkdir(parents=True, exist_ok=True)
    Path(r['log']).parent.mkdir(parents=True, exist_ok=True)
    (root / 'prompt.md').write_text(prompt, encoding='utf-8')
    save(r)
    try:
        with (root / 'executor.log').open('a', encoding='utf-8') as log:
            proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_execute', r['id']],
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env, **detached())
        r['executor'] = proc.pid
        until = time.time() + 5
        while time.time() < until and not (root / 'pid.json').exists() and not (root / 'exit.json').exists():
            time.sleep(.02)
        pid = read_json(root / 'pid.json', {})
        if not pid:
            raise Stop('the runner did not start: ' + one(read_json(root / 'exit.json', {}).get('error', 'no start receipt')))
        # The executor can already have retried a very fast scoped denial.
        # Merge under the same lock, never overwrite its newer argv/scope with
        # this parent's prelaunch copy (also protects the notice receipt).
        with locked(root / 'record.lock'):
            r = get_record(r['id'])
            r.update(pid); r['state'] = 'running'
            r['start_notice_attempted'] = iso(); save(r)
            r['start_notice_error'] = notice(r, True); save(r)
        if not a.wait:
            with (root / 'watcher.log').open('a', encoding='utf-8') as log:
                watcher = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_watch', r['id']],
                                           env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **detached())
            r['watcher_pid'] = watcher.pid
            # Only the watcher mutates the record after its launch.
    except Exception as exc:
        kill_job(r)
        r.update(state='fail', result=one(exc), ended=iso()); save(r); finish(r)
        if not a.json:
            print(banner_back(r), flush=True)
        raise Stop(one(exc))
    if a.json:
        print(json.dumps(dict(r, banner_out=banner_out(r)), ensure_ascii=False), flush=True)
    else:
        for warning in r['warnings']:
            print(warning, flush=True)
        model_note = r['model'] + (" (the CLI's configured model; mind model unset)" if r['mechanical_unset'] else '')
        extra = (' · cap $' + r['cap_usd']) if r['cap_usd'] else ''
        extra += ' · unattended ' + r['mind'] if r['unattended_flagship'] else ''
        extra += ' · letter → ' + r['lane'] + (' (no lane named)' if r['lane_defaulted'] else '')
        print(banner_out(r), flush=True)
        print('OFFLOAD %s · %s %s · %s · «%s» · in %s · log %s · ends by %s (timeout)%s · say `offload.py show %s`' %
              (r['id'], r['mind'], model_note, r['routing_reason'], r['title'], r['cwd'], r['log'],
               datetime.fromtimestamp(epoch(r['deadline'])).strftime('%H:%M'), extra, r['id']), flush=True)
    return foreground_wait(r, env, a.json) if a.wait else 0


def foreground_wait(r, env, quiet):
    """The foreground road uses the shared bounded rail; a cheap thread prints
    progress while that rail waits. The detached executor still owns the job.
    """
    done = threading.Event()

    def beat():
        while not done.wait(30):
            current = get_record(r['id'])
            seconds = int(time.time() - epoch(r['started']))
            print('%02d:%02d · %s · «%s» · last: %s' %
                  (seconds // 60, seconds % 60, r['mind'], r['title'], short_step(current['last_step'])), flush=True)

    thread = threading.Thread(target=beat, daemon=True) if not quiet else None
    if thread:
        thread.start()
    try:
        code, output = module('exo_common').run_bounded(
            [sys.executable, str(Path(__file__).resolve()), '_watch', r['id']], cwd=r['cwd'],
            timeout=max(1, epoch(r['deadline']) - time.time()) + 90, env=env)
        if code not in (0, 3, 4):
            kill_job(r)
            current = get_record(r['id'])
            current.update(state='fail', result='watcher failed: ' + one(output), ended=iso())
            save(current); finish(current)
            return 3
        return code
    finally:
        done.set()
        if thread:
            thread.join()
        current = get_record(r['id'])
        if current['state'] in TERMINAL:
            print(banner_back(current), flush=True)
            print('%s · %s · «%s» · %.1f min · %s' %
                  (current['state'].upper(), current['mind'], one(current['title']),
                   current['minutes'], one(current['result'])), flush=True)


def short_step(step):
    """A one-line, 72-character view; keep the tool and the argument's tail."""
    text = one(step)
    if len(text) <= 72:
        return text
    tool_name, separator, argument = text.partition(' ')
    if separator and len(tool_name) < 70:
        return tool_name + ' …' + argument[-(70 - len(tool_name)):]
    # Unusual single tokens or tool names cannot consume the entire line.
    return text[:35] + '…' + text[-36:]


def job_line(r):
    line = '⚙ %s job · %s · «%s» · %.1f min · last: %s' % (r.get('mind', ''), r.get('lane', ''), r.get('title', ''), float(r.get('minutes') or 0), short_step(r.get('last_step', '')))
    return line + (' · ' + str(r.get('state', '')).upper() if r.get('state') != 'running' else '')


def show_text(r):
    lines = ([banner_back(r)] if r['state'] in TERMINAL else [])
    lines += ['BRIEF · ' + r['title'], json.dumps(r.get('header', {}), ensure_ascii=False),
             'COMMAND · ' + (subprocess.list2cmdline(r['argv']) if os.name == 'nt' else shlex.join(r['argv']))]
    ledger = r.get('ledger') or next((x for x in ledger_rows() if x.get('run_id') == r['id']), {})
    tokens = ledger.get('tokens')
    count = ('%s tokens' % sum(tokens.get(k) or 0 for k in ('input', 'cache_write', 'cache_read', 'output'))) if tokens is not None else 'tokens unknown'
    lines += ['STATE · %s in %.1f min · %s · %s · %s' % (r['state'].upper(), r['minutes'], count, r['model'], r.get('result', '')),
              'TURNS'] + turns(r) + ['HAND-BACK']
    try:
        lines += Path(r['report']).read_text(encoding='utf-8').splitlines()[-20:]
    except (OSError, UnicodeError):
        lines += ['no report']
    lines += ['LEDGER · ' + json.dumps(ledger, ensure_ascii=False)]
    return '\n'.join(lines)


def ledger_print(a):
    rows = ledger_rows()
    if a.all:
        protector = module('protector')
        for r in ledger_rows(Path(protector.DEFAULT_STATE_DIR) / protector.LEDGER_FILE):
            rows.append(dict(time=r.get('time'), mind=r.get('mind'), lane='protector', vendor=r.get('runner'),
                             minutes=(r.get('seconds') or 0) / 60, tokens={k: r.get(k) for k in ('input', 'cache_write', 'cache_read', 'output')} if r.get('tokens_known') else None,
                             usd_at_list=r.get('usd'), usd_at_flagship=r.get('fable_usd')))
    if a.week:
        now = datetime.now().astimezone()
        since = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        rows = [r for r in rows if epoch(r.get('time')) >= since]
    for key in sorted({str(r.get(a.by) or '?') for r in rows}):
        group = [r for r in rows if str(r.get(a.by) or '?') == key]
        known = all(r.get('tokens') is not None for r in group)
        count = sum(sum((r.get('tokens') or {}).get(k) or 0 for k in ('input', 'cache_write', 'cache_read', 'output')) for r in group)
        priced = all(r.get('usd_at_list') is not None for r in group)
        against = all(r.get('usd_at_flagship') is not None for r in group)
        usd = sum(r.get('usd_at_list') or 0 for r in group)
        flagship = sum(r.get('usd_at_flagship') or 0 for r in group)
        plan = 'plan · ' if any(r.get('vendor') == 'codex' for r in group) else ''
        print('%s · %d runs · %.1f min · %s · %s%s · flagship %s · difference %s' %
              (key, len(group), sum(r.get('minutes') or 0 for r in group), str(count) + ' tokens' if known else 'tokens unknown',
               plan, '$%.2f' % usd if priced else 'no rate / unpriced', '$%.2f' % flagship if against else 'unknown',
               '$%.2f' % (flagship - usd) if priced and against else 'unknown'))
    return 0


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop(message)


def parser():
    p = Parser(add_help=False)
    sub = p.add_subparsers(dest='command')
    run = sub.add_parser('run', add_help=False)
    run.add_argument('brief')
    for flag in ('to', 'in', 'reason', 'kind', 'complexity', 'report', 'done', 'timeout', 'model', 'effort', 'sandbox', 'lane'):
        run.add_argument('--' + flag)
    run.add_argument('--add-dir', action='append', default=[])
    run.add_argument('--scrub-allow', action='append', default=[])
    for flag in ('work-bound', 'routine', 'despite-dirty', 'wait', 'dry-run', 'json'):
        run.add_argument('--' + flag, action='store_true')
    show = sub.add_parser('show', add_help=False); show.add_argument('id'); show.add_argument('--log', action='store_true')
    sub.add_parser('jobs', add_help=False)
    for name in ('kill', '_watch', '_execute'):
        cmd = sub.add_parser(name, add_help=False); cmd.add_argument('id')
    ledger = sub.add_parser('ledger', add_help=False)
    ledger.add_argument('--week', action='store_true'); ledger.add_argument('--all', action='store_true')
    ledger.add_argument('--by', choices=('mind', 'lane'), default='mind')
    return p


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or '--help' in argv or '-h' in argv:
        print(USAGE); return 2
    try:
        a = parser().parse_args(argv)
        if a.command == 'run':
            if a.sandbox and a.sandbox not in ('read-only', 'workspace-write'):
                raise Stop('sandbox must be read-only or workspace-write')
            if a.effort and a.effort not in ('low', 'medium', 'high', 'xhigh', 'max'):
                raise Stop('effort must be low, medium, high, xhigh or max')
            return start(a)
        if a.command == '_execute':
            return execute(a.id)
        if a.command == '_watch':
            return watch(a.id)
        if a.command == 'show':
            r = get_record(a.id)
            print(Path(r['log']).read_text(encoding='utf-8', errors='replace') if a.log else show_text(r)); return 0
        if a.command == 'jobs':
            for r in records():
                if r['state'] in ('running', 'starting'):
                    r['minutes'] = (time.time() - epoch(r['started'])) / 60
                    print(r['id'] + ' · ' + job_line(r))
            return 0
        if a.command == 'kill':
            r = get_record(a.id)
            if r['state'] not in TERMINAL:
                atomic(run_folder(r) / 'kill.json', {'time': iso()})
                watch(r['id'])
            current = get_record(r['id'])
            if current['state'] in TERMINAL:
                print(banner_back(current), flush=True)
            print(current.get('result', '')); return 0
        if a.command == 'ledger':
            return ledger_print(a)
        raise Stop('unknown command')
    except Exception as exc:
        line = 'STOP: ' + one(exc)
        print(line)
        try:
            state_dir().mkdir(parents=True, exist_ok=True)
            with (state_dir() / 'offload.log').open('a', encoding='utf-8') as f:
                f.write(iso() + ' ' + line + '\n')
        except OSError:
            pass
        return 2


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, OSError):
            pass
    sys.exit(main())
