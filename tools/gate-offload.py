#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-offload.py — prove the hand-off without calling a mind.

Run from the hub, or any directory that is not tools. Every world lives under
system temp as exo-prove-offload-*. HOME, registry, model commands, mail, and
notices are isolated. No GUI is started by the hermetic gate. G4 builds a real
repository when git is on PATH, otherwise announces its porcelain seam.
--live alone enables G11 (including G11c) and G14.
--keep preserves the worlds. --only G7 is a diagnosis aid, never a full pass.
Print N/N, exit 0; on failure print the first failing case and exit 1.
"""
import ast
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BUILD = HERE.parent
FIX = HERE / ('fixtures-offload' if (HERE / 'fixtures-offload').is_dir() else 'fixtures/offload')
PY = sys.executable
WORLDS = []


def check(ok, why):
    if not ok:
        raise AssertionError(why)


def source(name):
    dirs = ([Path(os.environ['EXO_OFFLOAD_TOOL_DIR'])] if os.environ.get('EXO_OFFLOAD_TOOL_DIR') else [])
    for p in dirs + [HERE] + [p / 'tools' for p in HERE.parents]:
        if (p / name).is_file():
            return p / name
    raise AssertionError('missing dependency ' + name)


def apply_diff(text, patch):
    """Strict unified diff application in Python; no patch or git executable."""
    before, out, pos = text.splitlines(True), [], 0
    lines = patch.splitlines(True)
    i = 2
    while i < len(lines):
        m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', lines[i])
        check(m, 'unreadable diff header: ' + lines[i])
        start = int(m[1]) - 1
        out.extend(before[pos:start]); pos = start; i += 1
        while i < len(lines) and not lines[i].startswith('@@ '):
            line = lines[i]; i += 1
            if line.startswith((' ', '-')):
                check(pos < len(before) and before[pos] == line[1:], 'patch context drift at line %d' % (pos + 1))
                pos += 1
            if line.startswith((' ', '+')):
                out.append(line[1:])
    out.extend(before[pos:])
    return ''.join(out)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def wait_for(test, seconds=12):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = test()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError('bounded wait expired')


class World:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix='exo-prove-offload-'))
        WORLDS.append(self)
        self.hub = self.root / 'hub'; self.tools = self.hub / 'tools'
        self.home = self.root / 'home'; self.state = self.root / 'offload'
        self.work = self.root / 'work'; self.empty = self.root / 'empty-path'
        for p in (self.tools, self.home, self.work, self.empty, self.root / 'projects'):
            p.mkdir(parents=True, exist_ok=True)
        # Dependencies remain byte-for-byte copies, except the named patches.
        # Copy only the gate's runtime dependencies, never modify installed tools.
        # Candidate siblings win; integration dependencies remain the shipped ones.
        dependencies = ('exo_common.py', 'exo_paths.py', 'exo_registry.py',
                        'protector.py', 'pulse.py', 'wake-screen.py', 'collect-openers.py',
                        'usage.py', 'grok_sessions.py', 'exo_laws.py',
                        'opener_carriers.py', 'personal.py', 'postman.py', 'tail-session.py')
        for name in dependencies:
            shutil.copy2(str(source(name)), str(self.tools / name))
        for name in ['exo_common', 'protector', 'pulse', 'wake-screen', 'collect-openers']:
            # Round 3 builds on the reviewed round-2 candidates, even while the
            # hub's installation still contains 0.1. Keep these proof inputs
            # separate from the round-3 install payload.
            prior = BUILD / 'round2/patched' / (name + '.py')
            if prior.is_file():
                shutil.copy2(str(prior), str(self.tools / (name + '.py')))
            diff = BUILD / (name + '.patch2.py')
            if diff.is_file():
                dest = self.tools / (name + '.py')
                dest.write_text(apply_diff(dest.read_text(encoding='utf-8'), diff.read_text(encoding='utf-8')), encoding='utf-8')
            diff = BUILD / (name + '.patch3.py')
            if diff.is_file():
                dest = self.tools / (name + '.py')
                dest.write_text(apply_diff(dest.read_text(encoding='utf-8'), diff.read_text(encoding='utf-8')), encoding='utf-8')
        shutil.copy2(str(HERE / 'offload.py'), str(self.tools / 'offload.py'))
        shutil.copytree(str(FIX), str(self.tools / 'fixtures/offload'))
        self.reg = json.loads((FIX / 'registry.json').read_text(encoding='utf-8'))
        for row in self.reg['minds']:
            for oskind in ('macos', 'windows'):
                row['headless']['candidates'][oskind] = [str(self.tools / ('fixtures/offload/stub-' + row['kind'] + '.py'))]
        self.registry = self.hub / 'registry.json'; self.write_reg()
        self.machine = self.hub / 'machine.json'
        self.machine.write_text(json.dumps({'name':'north','machine':'north','roots':{
            'orchestrator':str(self.hub),'home':str(self.home),'projects':str(self.root/'projects'),
            'claude':str(self.home/'.claude'),'codex':str(self.home/'.codex'), 'grok':str(self.home/'.grok')}}),encoding='utf-8')
        local = self.home / 'orchestrator-sync'; local.mkdir()
        shutil.copy2(str(self.machine),str(local/'machine.json'))
        self.notice = self.root / 'notify.py'
        seam = "import json,os,sys\nfrom pathlib import Path\np=Path(os.environ['SEAM_FILE'])\nwith p.open('a',encoding='utf-8') as f: f.write(json.dumps(sys.argv[1:])+chr(10))\n"
        self.notice.write_text(seam.replace("['SEAM_FILE']", "['NOTICE_FILE']"), encoding='utf-8')
        (self.tools / 'mail.py').write_text(seam.replace("['SEAM_FILE']", "['MAIL_FILE']"),encoding='utf-8')
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(('EXO_', 'OFFLOAD_', 'PROTECTOR_', 'CODEX_', 'CLAUDE_CODE')) or key in ('ANTHROPIC_API_KEY','CLAUDECODE'):
                self.env.pop(key)
        self.env.update(HOME=str(self.home),USERPROFILE=str(self.home),PATH=str(self.empty),
                        EXO_MACHINE_JSON=str(self.machine),EXO_REGISTRY_JSON=str(self.registry),
                        EXO_OFFLOAD_STATE_DIR=str(self.state), EXO_OFFLOAD_NOTIFY=str(self.notice),
                        EXO_OFFLOAD_MAIL=str(self.tools/'mail.py'),EXO_PULSE_STATE_DIR=str(self.root/'pulse'),
                        EXO_POST_DIR=str(self.root/'post'),EXO_USAGE_STATE_DIR=str(self.root/'usage'),
                        OFFLOAD_STUB_OUT=str(self.root/'sidecars'),NOTICE_FILE=str(self.root/'notices.jsonl'),
                        MAIL_FILE=str(self.root/'mail.jsonl'),PYTHONDONTWRITEBYTECODE='1',
                        CHROME='/nonexistent',BROWSER='/nonexistent',COLLECT_OPENERS_OUT=str(self.root/'tree.html'),
                        CLAUDECODE='1',CLAUDE_CODE_ENTRYPOINT='fixture',CODEX_HOME=str(self.home/'.codex'),
                        OFFLOAD_STUB_PROBES=str(self.root/'probes.jsonl'))
        for key in ('SESSION_ID','HOST_SESSION_ID','CHILD_SESSION','MESSAGING_SOCKET','MESSAGING_TOKEN','FUTURE'):
            self.env['CLAUDE_CODE_'+key]='fixture-'+key
        # Hard refusal before subprocess creation: no repository or GUI command
        # can accidentally escape an imported surface's old convenience path.
        guard = self.root / 'guard'; guard.mkdir()
        (guard/'sitecustomize.py').write_text('''import os,sys

def audit(event,args):
    if event == 'subprocess.Popen':
        exe = os.path.basename(str(args[0])).lower()
        forbidden = ('open','osascript','chrome','google chrome','msedge','firefox')
        if exe in forbidden or (exe in ('git','git.exe') and not os.environ.get('OFFLOAD_GATE_GIT')):
            raise RuntimeError('gate forbids executable: '+exe)
sys.addaudithook(audit)
if len(sys.argv)>2 and sys.argv[1] in ('_execute','_watch'):
    import json
    from pathlib import Path
    p=Path(os.environ['OFFLOAD_STUB_OUT']);p.mkdir(parents=True,exist_ok=True)
    info={'isatty':sys.stdin.isatty(),'readable':sys.stdin.readable(),
          'devnull':os.path.samestat(os.fstat(0),os.stat(os.devnull)),'read':sys.stdin.read()}
    (p/(sys.argv[2]+sys.argv[1]+'.json')).write_text(json.dumps(info),encoding='utf-8')
''',encoding='utf-8')
        outer = os.environ.get('BQ364_AUDIT_GUARD')
        if outer:
            with (guard/'sitecustomize.py').open('a',encoding='utf-8') as f:
                f.write('\nexec(compile(open('+repr(outer)+').read(), '+repr(outer)+', "exec"))\n')
        self.env['PYTHONPATH']=str(guard)
        self.seq = 0

    def write_reg(self):
        self.registry.write_text(json.dumps(self.reg,indent=2),encoding='utf-8')

    def cmd(self, argv, scenario='done', timeout=25, extra=None, script='offload.py'):
        env=dict(self.env,OFFLOAD_STUB=scenario); env.update(extra or {})
        r=subprocess.run([PY,str(self.tools/script)] + list(argv),cwd=str(self.root),env=env,
                         stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         encoding='utf-8',timeout=timeout)
        return r.returncode,r.stdout

    def brief(self, header='', body='# Fixture job\nDo the small job.\n'):
        self.seq += 1
        p=self.work/('brief-%d.md'%self.seq)
        p.write_text((header+'\n---\n' if header else '')+body,encoding='utf-8')
        return p

    def run(self, scenario='done', args=(), header='', wait=True, mind='sonnet'):
        p=self.brief(header)
        argv=['run',str(p),'--to',mind,'--lane','NORTH/Test']+(['--wait'] if wait else [])+list(args)
        code,out=self.cmd(argv,scenario)
        rows=self.records(); return code,out, rows[-1] if rows else None

    def records(self):
        return sorted([json.loads(p.read_text(encoding='utf-8')) for p in (self.state/'runs').glob('*.json')],key=lambda r:(r['started'],r['id']))

    def get(self, ident):
        return json.loads((self.state/'runs'/(ident+'.json')).read_text(encoding='utf-8'))

    def side(self,r):
        return json.loads((self.root/'sidecars'/(r['id']+'.json')).read_text(encoding='utf-8'))

    def lines(self,name):
        p=self.root/name
        return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []

    def ledger(self):
        p=self.state/'offload-ledger.jsonl'
        return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []

    def code(self, code):
        p=self.root/'probe.py'; p.write_text(code,encoding='utf-8')
        env=dict(self.env,PYTHONPATH=str(self.tools)+os.pathsep+self.env['PYTHONPATH'])
        r=subprocess.run([PY,str(p)],cwd=str(self.root),env=env,stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',timeout=30)
        return r.returncode,r.stdout

    def cleanup(self):
        for r in self.records():
            if r.get('state') not in ('done','fail','timeout'):
                try:self.cmd(['kill',r['id']],timeout=15)
                except Exception:pass
        if '--keep' not in sys.argv:
            shutil.rmtree(str(self.root),ignore_errors=True)


def G0():
    w=World()
    for argv in ([],['--help']):
        code,out=w.cmd(argv); check(code==2 and 'python3 tools/offload.py run <job.md>' in out,'usage / exit 2')
    p=w.brief()
    code,out=w.cmd(['run',str(p),'--to','sonnet','--lane','NORTH/Test','--dry-run'])
    check(code==0,out)
    first, payload = out.split('\n',1)
    check(first=='dry-run · probed: CLI version, git status · ran: nothing','dry-run probe disclosure')
    d=json.loads(payload)
    check(all(k in d for k in ('argv','env_additions','prompt_head','contract')),'dry-run fields')
    check(not w.records() and not (w.root/'sidecars').exists() and not list(w.work.glob('*RUN*')),'dry run wrote or ran a job')
    # ASSUMES: on a posix host the prompt is the last argument. On Windows offload.py hands a
    # POINTER to the brief file by design (prompt_argument: the command line is bounded there),
    # so the last argument names the file and the prompt's own head still opens 'Never launch'.
    # The false case for the posix reading: a Windows prompt argument.
    if os.name == 'nt':
        check(d['argv'][-2]=='--' and d['argv'][-1].startswith('Read the file ')
              and d['prompt_head'][0].startswith('Never launch'),'prompt argument (pointer)')
    else:
        check(d['argv'][-2]=='--' and d['argv'][-1].startswith('Never launch'),'prompt argument')
    check([x['argv'] for x in w.lines('probes.jsonl')]==[['--version']],'dry-run probed sign-in')
    code,out=w.cmd(['run',str(p),'--to','sonnet','--dry-run'],scenario='not-logged-in')
    check(code==0,out)
    # ASSUMES: nothing about newline translation. brief_read keeps the file's bytes (a Windows
    # input file carries CRLF and the builder gets it as written), while Path.write_text/read_text
    # translate on Windows — so the probe compares against the bytes, not a text-mode read.
    # The false case for the posix reading: a Windows byte-preservation probe.
    code,out=w.code('''from pathlib import Path
import offload
p=Path('note.md');p.write_text('Note: body only\\nMore body.\\n')
_,body,header,title=offload.brief_read(p)
assert body==p.read_bytes().decode('utf-8') and header=={} and title=='note'
p.write_text('kind: reading\\n---\\nNo heading.\\n')
assert offload.brief_read(p)[2]=={'kind':'reading'}
p.write_text('Note: first\\n'+'text\\n'*29+'---\\nend')
assert offload.brief_read(p)[2]=={}
p.write_text('lane: NORTH/Test\\n'+'\\n'*27+'---\\nlast')
assert offload.brief_read(p)[2]=={'lane':'NORTH/Test'}
''');check(code==0,out)


def G1():
    w=World(); code,out,r=w.run(); check(code==0,out)
    check(r['how_found']=='candidate' and 'fixture 1.0' in r['version'],'candidate/version')
    code,out=w.code("import protector\nr=protector.runner_for('sonnet',protector.Opts())\nassert 'stub-claude.py' in r['argv'][0]\nprint('same finder')\n")
    check(code==0,out)
    path_hit=w.empty/('fixture-claude' + ('.cmd' if os.name=='nt' else ''))
    if os.name!='nt':
        path_hit.write_text('#!'+PY+'\nprint("PATH fixture 2.0")\n',encoding='utf-8');path_hit.chmod(0o755)
        code,out=w.code("import exo_common,os\np,v,h=exo_common.headless_command('SONNET','macos',os.environ)\nassert h=='PATH' and v=='PATH fixture 2.0'\nimport protector\nr=protector.runner_for('sonnet',protector.Opts())\nassert r['argv'][0]==p\n")
        check(code==0,out)
        path_hit.unlink()
    for row in w.reg['minds']:row['headless']['candidates']={'macos':[],'windows':[]}
    w.write_reg();code,out,_=w.run()
    check(code==2 and 'STOP:' in out and 'fixture install claude' in out,'missing CLI/install line')
    check(len(w.records())==1,'missing CLI launched job')

    w=World();code,out,_=w.run('not-logged-in')
    check(code==2 and out.startswith('STOP:') and 'not signed in' in out,out)
    check(not w.records() and not (w.root/'sidecars').exists(),'unsigned CLI launched a job')



def G2():
    for mind in ('sonnet','sol'):
        w=World();code,out,r=w.run('stdin',mind=mind); check(code==0,out)
        side=w.side(r);check(side['stdin']=='' and not side['stdin_isatty'] and side['stdin_readable'] and side['stdin_devnull'],'job stdin is not DEVNULL')
        for stage in ('_execute','_watch'):
            info=json.loads((w.root/'sidecars'/(r['id']+stage+'.json')).read_text())
            check(info=={'isatty':False,'readable':True,'devnull':True,'read':''},stage+' stdin is not DEVNULL')
        check(r['argv'][-1].startswith('Never launch') and r['argv'][-2]=='--','prompt is not argv')


def G3():
    for mind in ('sonnet','sol'):
        w=World();code,out,r=w.run(mind=mind);check(code==0,out)
        side=w.side(r)
        check(side['env']['CHROME']==side['env']['BROWSER']=='/nonexistent','browser environment')
        check(side['prompt_head'][0].startswith('Never launch a browser or GUI'),'first preamble rule')
        if mind=='sonnet':
            keys=[k for k in w.env if k.startswith('CLAUDE_CODE') or k=='CLAUDECODE']
            check(sorted(keys)==r['env_removed'] and all(side['env'][k] is None for k in keys),'nested Claude environment')


def G4():
    w=World()
    git = shutil.which('git')
    if git:
        w.env.update(PATH=os.environ.get('PATH',''), OFFLOAD_GATE_GIT=git,
                     GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(w.root/'no-git-config'))
        code,out=w.code('''from pathlib import Path
import subprocess,os,offload,exo_common
root=Path('repo');root.mkdir();root=root.resolve()
def git(*args):
 p=subprocess.run([os.environ['OFFLOAD_GATE_GIT'],*args],cwd=str(root),env=os.environ,
                  stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 assert p.returncode==0,p.stdout.decode()
git('init')
(root/'src').mkdir();(root/'src/part.py').write_text('before\\n')
git('add','src/part.py')
git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
    '-c','core.hooksPath='+str(root/'empty-hooks'),'-c','commit.gpgsign=false','commit','-m','fixture')
(root/'src/part.py').write_text('after\\n');(root/'scratch.txt').write_text('untracked\\n')
real=exo_common.run_bounded;calls=[]
def bounded(argv,**kw):
 if argv[0]=='git':
  assert argv==['git','--no-optional-locks','status','--porcelain','-z','--untracked-files=no']
  calls.append(argv)
 return real(argv,**kw)
exo_common.run_bounded=bounded
base=['--to','sonnet','--lane','NORTH/Test','--wait']
def run(n,header,extra=()):
 p=root/('case-%s.md'%n);p.write_text(header+'\\n---\\n# Dirty fixture\\nDo it.\\n')
 return offload.main(['run',str(p)]+base+list(extra))
assert run(1,'touches: src')==2
assert not offload.records()
assert run(2,'touches: elsewhere')==0
assert run(3,'lane: NORTH/Test')==2
assert run(4,'touches: src',['--despite-dirty'])==0
r=offload.records()[-1];assert r['despite_dirty'] and r['dirty_files']==['src/part.py']
(root/'src/part.py').write_text('before\\n')
assert run(5,'lane: NORTH/Test')==0
assert len(offload.records())==3 and len(calls)==5
''')
        check(code==0,out)
        print('G4 proof: real git init/commit; tracked + untracked; production porcelain -z',flush=True)
        return
    print('G4 proof: git absent from PATH; porcelain subprocess seam only',flush=True)
    # The subprocess seam proves exact argv and the decision on literal git
    # porcelain. No git command is executed in this builder's sandbox.
    code,out=w.code('''from pathlib import Path
import offload
root=Path('repo');root.mkdir();(root/'.git').mkdir()
(root/'src').mkdir();(root/'src/part.py').write_text('changed')
root=root.resolve(); calls=[]
def runner(argv,**kw):
    assert argv == ['git','--no-optional-locks','status','--porcelain','-z','--untracked-files=no']
    calls.append(argv)
    return 0, status
status=' M src/part.py\\0'
try:offload.tracked_changes(root,[root/'src'],runner=runner)
except offload.Stop as e:assert 'src/part.py' in str(e)
else:raise AssertionError('dirty touched file ran')
assert offload.tracked_changes(root,[root/'elsewhere'],runner=runner)==[]
try:offload.tracked_changes(root,[],runner=runner)
except offload.Stop:pass
else:raise AssertionError('any tracked dirty file ran')
assert offload.tracked_changes(root,[],True,runner)==['src/part.py']
status='?? scratch.txt\\0'
assert offload.tracked_changes(root,[],runner=runner)==[]
status='R  elsewhere/new name.py\\0src/old name.py\\0'
try:offload.tracked_changes(root,[root/'src'],runner=runner)
except offload.Stop as e:assert 'src/old name.py' in str(e)
else:raise AssertionError('rename source not checked')
print('porcelain subprocess seam: 6 decisions; no git process')
''')
    check(code==0,out)
    code,out=w.code("""import json
from pathlib import Path
import offload
root=Path('repo').resolve()
original=offload.tracked_changes
status=' M src/part.py\\0'
def runner(argv,**kw):return 0,status
offload.tracked_changes=lambda folder,touches,despite=False:original(folder,touches,despite,runner)
base=['--to','sonnet','--lane','NORTH/Test','--wait']
def run(n,header,extra=()):
 p=root/('case-%s.md'%n)
 p.write_text(header+'\\n---\\n# Dirty fixture\\nDo it.\\n')
 return offload.main(['run',str(p)]+base+list(extra))
assert run(1,'touches: src')==2
assert not offload.records()
assert run(2,'touches: elsewhere')==0
assert run(3,'lane: NORTH/Test')==2
status='?? scratch.txt\\0'
assert run(4,'lane: NORTH/Test')==0
status=' M src/part.py\\0'
assert run(5,'touches: src',['--despite-dirty'])==0
record=offload.records()[-1]
assert record['despite_dirty'] and record['dirty_files']==['src/part.py']
assert len(offload.records())==3
""")
    check(code==0,out)


def dead(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        h=kernel.OpenProcess(0x1000,False,int(pid))
        if not h:return ctypes.get_last_error()==87  # invalid pid; denied is not proof of death
        try:
            status=wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(h,ctypes.byref(status))) and status.value!=259
        finally:kernel.CloseHandle(h)
    try:os.kill(int(pid),0)
    except OSError:return True
    r=subprocess.run(['/bin/ps','-o','stat=','-p',str(pid)],stdout=subprocess.PIPE,encoding='utf-8',stdin=subprocess.DEVNULL)
    return not r.stdout.strip() or r.stdout.strip().startswith('Z')


def G5():
    w=World();code,out,r=w.run('sleep',['--timeout','3s']);check(code==4,out)
    check(r['state']=='timeout','timeout state')
    check('**⇠ BACK FROM ANTHROPIC**' in out and '«Fixture job» TIMED-OUT · ' in out, 'timeout return banner missing: '+out)
    side=w.side(r); wait_for(lambda:dead(side['pid']) and dead(side['grandchild']))
    check(len(w.lines('mail.jsonl'))==1,'exactly one timeout letter')
    notes=w.lines('notices.jsonl');check(len(notes)==2 and 'TIMEOUT' in notes[-1][0],'both timeout notices')
    check(len(w.ledger())==1 and w.ledger()[0]['token_status']=='tokens unknown','unknown tokens on timeout')
    code,out=w.code('''import os,errno,ctypes
import offload,exo_common
from unittest.mock import patch
assert exo_common.process_start_time(os.getpid()),'cannot read a native process birth stamp'
calls=[]
class Kernel:
 def GetExitCodeProcess(self,handle,p):p._obj.value=259;return 1
 def CloseHandle(self,handle):calls.append(handle)
with patch.object(os,'name','nt'),patch.object(os,'kill',side_effect=AssertionError('Windows signal used')):
 with patch.object(exo_common,'_windows_process',return_value=(Kernel(),123)):
  assert offload.alive(123)
assert calls==[123]
with patch.object(os,'name','posix'):
 with patch.object(os,'kill',side_effect=OSError(errno.EPERM,'denied')):assert offload.alive(123)
 with patch.object(os,'kill',side_effect=OSError(errno.ESRCH,'gone')):assert not offload.alive(123)
''');check(code==0,out)


def G6():
    w=World()
    for scenario,state,reason in [('done','done','DONE Fixture job'),('no-report','fail','no report'),('no-done','fail','no DONE line'),('stdout-only','fail','no DONE line'),('fail-line','fail','FAIL — fixture'),('nonzero','fail','exit 7'),('done-denied','done',' · 1 tool denials'),('done-error','done',' · cli error: fixture CLI error text'),('error-no-done','fail','CLI error: fixture CLI error text')]:
        code,out,r=w.run(scenario);check(code==(0 if state=='done' else 3),out)
        check(r['state']==state and reason in r['result'],scenario+': '+str(r))
        code,shown=w.cmd(['show',r['id']]);check(code==0 and r['result'] in shown,'show lost reason')
        if scenario=='stdout-only':
            check(r['done_prefix'] in Path(r['log']).read_text() and r['done_prefix'] not in Path(r['report']).read_text(),'stdout-only fixture is not the real case')
        if scenario in ('done-denied','done-error','error-no-done'):
            check(len(r['permission_denials'])==1 and r['is_error']==('error' in scenario),'CLI diagnostics not recorded')
    check((FIX/'stdout-only.json').read_bytes()!=(FIX/'no-done.json').read_bytes(),'contract fixtures duplicated')


def G7():
    w=World();code,out,r=w.run('usage');check(code==0,out)
    row=w.ledger()[0]
    # Independent arithmetic from the source table, not the tool's pricing API.
    tree=ast.parse(source('usage.py').read_text(encoding='utf-8'))
    defaults=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULTS' for t in n.targets))
    prices=ast.literal_eval(defaults)['prices']
    calc=lambda rate:sum(row['tokens'][k]*rate[k] for k in ('input','cache_write','cache_read','output'))/1e6
    check(abs(row['usd_at_list']-calc(prices['claude-sonnet-5']))<.005,'list dollars')
    check(abs(row['usd_at_flagship']-calc(prices['claude-fable-']))<.005,'flagship dollars')
    code,out,r=w.run('done',['--model','unpriced-fixture-model'],mind='sol');check(code==0,out)
    code,out=w.cmd(['ledger','--week']);check('no rate' in out and 'plan' in out,out)
    code,out,r=w.run('delay',wait=False);check(code==0,out)
    r=wait_for(lambda:(x if (x:=w.get(r['id'])).get('watcher_pid') else None))
    os.kill(r['watcher_pid'],signal.SIGKILL if os.name!='nt' else signal.SIGTERM)
    code,out=w.cmd(['_watch',r['id']]);check(code==0,out)
    code,out=w.cmd(['_watch',r['id']]);check(code==0,out)
    check(len([x for x in w.ledger() if x['run_id']==r['id']])==1,'recovery duplicated ledger')
    check(len(w.lines('mail.jsonl'))==3 and len(w.lines('notices.jsonl'))==6,'recovery duplicated external effects')

    code,out,r=w.run('no-usage',wait=False,mind='sol',args=['--model','unpriced-fixture-model'])
    check(code==0,out)
    folder=w.home/'.codex/sessions/2026/10/23';folder.mkdir(parents=True,exist_ok=True)
    ident='fixture-'+r['id']
    events=[{'type':'session_meta','payload':{'id':ident,'source':'exec','cwd':r['cwd'],'timestamp':r['started']}},
            {'type':'turn_context','payload':{'model':'unpriced-fixture-model'}},
            {'type':'event_msg','timestamp':r['started'],'payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':10000,'cached_input_tokens':2000,'output_tokens':1000,'reasoning_output_tokens':400}}}}]
    (folder/('rollout-'+ident+'.jsonl')).write_text('\n'.join(json.dumps(e) for e in events)+'\n',encoding='utf-8')
    code,out=w.cmd(['_watch',r['id']]);check(code==0,out)
    row=next(x for x in w.ledger() if x['run_id']==r['id'])
    check(row['tokens']['input']==8000 and row['tokens']['cache_read']==2000 and row['tokens']['output']==1000,'rollout fallback accounting')
    check(row['tokens']['reasoning'] is None,'reader did not expose reasoning; must remain unknown')

    code,out=w.code("""import protector,offload,json
from pathlib import Path
p=Path(protector.DEFAULT_STATE_DIR)
opts=protector.Opts(state_dir=str(p))
call={'time':offload.iso(),'run':'protector-compat','mind':'SONNET','model':'claude-sonnet-5-5','role':'bare','runner':'claude','cli_cost_usd':0.01,'usd':0.02,'fable_usd':0.10,'seconds':1,'tokens':{'input':1,'cache_write':2,'cache_read':3,'output':4}}
assert protector.ledger_append(opts,call)
row=json.loads((p/protector.LEDGER_FILE).read_text())
assert row['input']==1 and row['output']==4 and row['tokens_known'] and row['run']=='protector-compat'
assert 'run_id' not in row
""")
    check(code==0,out)
    code,out=w.cmd(['ledger','--all']);check(code==0 and 'SONNET' in out,out)




def live_fixture(w, scenario='sleep'):
    code,out,r=w.run(scenario,wait=False,mind='sol',args=['--timeout','20s','--model','unpriced-fixture-model'])
    check(code==0,out)
    r=wait_for(lambda:(x if (x:=w.get(r['id'])).get('thread_id') else None))
    # The rollout that the existing pulse already senses must collapse into the job.
    folder=w.home/'.codex/sessions/2026/10/23';folder.mkdir(parents=True)
    p=folder/('rollout-2026-10-23-'+r['thread_id']+'.jsonl')
    p.write_text(json.dumps({'type':'session_meta','payload':{'id':r['thread_id'],'cwd':r['cwd'],'source':'exec','timestamp':r['started']}})+'\n'+json.dumps({'type':'turn_context','payload':{'model':'unpriced-fixture-model'}})+'\n',encoding='utf-8')
    old=dict(r,id='old-job',run_id='old-job',state='done',ended='2001-01-01T00:00:00+00:00')
    (w.state/'runs/old-job.json').write_text(json.dumps(old),encoding='utf-8')
    code,out=w.cmd(['--sense','--hub',str(w.hub)],script='pulse.py');check(code==0,out)
    rows=json.loads((w.hub/'live-sessions-north.json').read_text(encoding='utf-8'))['sessions']
    check(len(rows)==1 and rows[0]['kind']=='job','pulse did not merge to exactly one job: '+str(rows))
    check(rows[0]['title']==r['title'] and 'last_step' in rows[0],'pulse lost job facts')
    return r,rows[0]


def G8():
    w=World();r,row=live_fixture(w,'long-step')
    for field in ('kind','mind','model','title','lane','minutes','last_step','state','run_id','log','report'):
        check(field in row,'§7.2 job row missing '+field)
        if field=='kind':check(row[field]=='job','job kind')
        elif field=='minutes':check(isinstance(row[field],(int,float)) and row[field]>=0,'job minutes')
        elif field!='last_step':check(row[field]==r[field],'§7.2 job field changed: '+field)
    full=json.loads((FIX/'long-step.json').read_text())['live_step']
    expected='Read …'+full[-66:]
    check(len(full)>240 and r['last_step']==full and w.get(r['id'])['last_step']==full,'record lost the full last step')
    check(row['last_step']==row['last_line']==expected and len(row['last_step'])==72,'job row did not preserve tool + argument tail at 72 characters')
    code,out=w.code('''import offload
for length in (0,1,71,72,73,240,900):
 step='Read '+('x'*max(0,length-5)) if length>=5 else 'x'*length
 got=offload.short_step(step)
 assert len(got)<=72 and offload.short_step(got)==got
 if length<=72:assert got==step
 else:assert got.startswith('Read …') and got.endswith('x'*20)
assert offload.short_step('Read\\n /path\\t/file')=='Read /path /file'
assert len(offload.short_step('X'*200))==72
# Claude uses the tool name and FIRST input value, never the second.
r=offload.get_record('latest')
event={'type':'assistant','message':{'content':[{'type':'tool_use','name':'Read','input':{'file_path':'/a/'+'x'*300+'/tail.py','second':'ignore-me'}}]}}
from pathlib import Path
import json
Path(r['log']).write_text(json.dumps(event)+'\\n')
offload.progress(r)
assert r['last_step']=='Read /a/'+'x'*300+'/tail.py'
assert offload.short_step(r['last_step']).startswith('Read …') and offload.short_step(r['last_step']).endswith('/tail.py')
''');check(code==0,out)
    w.cmd(['kill',r['id']])


def G9():
    w=World();r,row=live_fixture(w,'long-step')
    code,out=w.cmd([],script='wake-screen.py');check(code==0 and '⚙ SOL job · NORTH/Test · «Fixture job»' in out,out)
    check(row['last_step'] in out and r['last_step'] not in out,'wake screen lost trim')
    code,out=w.cmd(['--html'],script='collect-openers.py',timeout=45);check(code==0,out)
    page=(w.root/'tree.html').read_text(encoding='utf-8')
    check('⚙ SOL job · NORTH/Test · «Fixture job»' in page and row['show_uri'] in page,'tree line/click record missing')
    check(row['last_step'] in page and r['last_step'] not in page,'tree LIVE lost trim')
    show=Path(row['show']).read_text(encoding='utf-8')
    check('COMMAND' in show and 'Never launch a browser' in show,'local full record missing')
    synced=(w.hub/'live-sessions-north.json').read_text(encoding='utf-8')
    check('Never launch a browser' not in synced and 'Never launch a browser' not in page,'full brief leaked into synced metadata')
    check('var(--amber-ink)' in page,'no running amber style')
    w.cmd(['kill',r['id']])


def G10():
    w=World()
    for mind,args,header,expected in [
            ('sonnet',['--kind','judgment'],'',2),('fable',['--kind','judgment'],'',0),
            ('opus',['--kind','reading'],'',2),('fable',['--routine'],'',2),
            ('fable',['--routine'],'model-reason: explicit test exception',2),
            ('fable',['--routine','--kind','judgment'],'model-reason: no exception here',2),
            ('astra',['--routine','--kind','judgment'],'model-reason: no exception here',2),
            ('astra',[],'',0),('astra',['--routine'],'',2),('sol',['--kind','judgment'],'',2),
            ('fable',['--kind','judgment','--model','sonnet'],'',2),
            ('sonnet',['--kind','reading','--model','fable'],'',2)]:
        code,out,r=w.run(args=args,header=header,mind=mind);check(code==expected,out)
        if '--routine' in args and '--kind' not in args and mind in ('fable','astra'):
            check('a flagship cannot run a routine' in out and 'a reason does not lift it' in out,out)
        if '--kind' in args and 'judgment' in args and '--routine' in args:
            check('refused outright' in out,out)
    for row in w.reg['minds']:
        if row['name']=='ASTRA':
            row['name']='NOVA';row['models']['mechanical']=row['models']['flagship']
    w.write_reg()
    code,out,r=w.run(mind='nova');check(code==0 and 'WARN:' not in out,'renamed equal-default rule: '+out)
    for row in w.reg['minds']:
        if row['name']=='NOVA':row['models'].pop('flagship')
    w.write_reg()
    config=w.home/'.codex/config.toml';config.parent.mkdir(parents=True,exist_ok=True)
    config.write_text('model = "fixture-configured-model"\n',encoding='utf-8')
    code,out,r=w.run(mind='nova',args=['--reason','configured model proof'])
    check(code==0 and "fixture-configured-model (the CLI's configured model; mind model unset)" in out,out)
    check('-m' not in r['argv'],'unset must use CLI config')
    code,out=w.code("""import offload,exo_common
reg=exo_common._reg()
for vendor in ('claude','codex'):
 for kind in ('mechanical','reading','judgment'):
  a=offload.default_mind(reg,vendor,kind)
  b=offload.default_mind(dict(reg,minds=list(reversed(reg['minds']))),vendor,kind)
  assert a==b,'registry order changed default'
assert offload.default_mind(reg,'codex','mechanical')=='SONNET'
assert offload.default_mind(reg,'codex','mechanical','complex')=='OPUS'
assert offload.default_mind(reg,'codex','reading')=='HAIKU'
assert offload.default_mind(reg,'claude','reading')=='LUNA'
for vendor in ('grok','unknown',''):
 try:offload.default_mind(reg,vendor,'mechanical')
 except offload.Stop as e:assert "name --to: this caller's vendor is" in str(e)
 else:raise AssertionError(vendor)
# A former sentinel is now just an explicitly registered model id.
row=dict(next(m for m in reg['minds'] if m['name']=='SOL'),models={'mechanical':'UNSET-R1'})
assert offload.route(row,'mechanical',None,None,False,{})[1:3]==('UNSET-R1',False)
# Renamed tiers still route and price; no persona-name classifier.
row=dict(row,name='READER',cli='reader',kind='claude',tier='cheap',app_id='reader-id',models={})
assert offload.route(row,'reading',None,None,False,{})[0]=='reader-id'
row=dict(row,tier='mechanical')
try:offload.route(row,'reading',None,None,False,{})
except offload.Stop:pass
else:raise AssertionError('noncheap read')
""")
    check(code==0,out)


def G12():
    w=World();p=w.brief(body='# Scrub test\nA path /Users/you/file\n')
    args=['run',str(p),'--to','sonnet','--lane','NORTH/Test','--wait']
    code,out=w.cmd(args+['--work-bound']);check(code==2 and 'line 2' in out and 'personal filesystem path' in out,out)
    code,out=w.cmd(args+['--work-bound','--scrub-allow','/Users/']);check(code==0,out)
    check(w.records()[-1]['scrub_allow']==['/Users/'],'allow missing from record')
    code,out=w.cmd(args);check(code==0,out)
    code,out=w.code("import offload\nfor text in ['C:\\\\Users\\\\test','hóme machine','Códex','work-side','ITÁR']:\n try: offload.scrub(text,{},[])\n except offload.Stop: pass\n else: raise AssertionError(text)\n")
    check(code==0,out)
    # Personal path belongs to the tool, not the author's text. The literal
    # /Users component also exercises this on Linux/Windows fixture worlds.
    home_path=w.work/'Users'/'owner';home_path.mkdir(parents=True)
    p=home_path/'clean.md';p.write_text('report: ./report.md\n---\n# Clean brief\nRead this text.\n',encoding='utf-8')
    check('/Users/' in str(p).replace('\\','/'),'fixture lacks personal-path shape')
    code,out=w.cmd(['run',str(p),'--to','sonnet','--work-bound','--wait','--lane','NORTH/Test'])
    check(code==0,out)
    check(w.records()[-1]['scrub_allow']==[],'clean authored brief needed a path allowance')


def G13():
    # The sub-second model stub completes before any 30-second heartbeat.
    # Compare the literal last line and the state-derived exit code.
    w=World()
    for scenario,state,expected in [('done','DONE',0),('no-report','FAIL',3),('sleep','TIMEOUT',4)]:
        code,out,r=w.run(scenario,args=['--timeout','1s'] if scenario=='sleep' else [])
        check(code==expected,out)
        final='%s · %s · «%s» · %.1f min · %s' % (state,r['mind'],r['title'],r['minutes'],r['result'])
        check(out.splitlines()[-1]==final,'--wait did not end on its state line: '+out)
        check(sum(line.startswith(state+' · ') for line in out.splitlines())==1,'duplicate final state line')
        check(not any(re.match(r'^\d+:\d+ · ',line) for line in out.splitlines()),'fast fixture unexpectedly needed a heartbeat')
        if scenario!='sleep':
            receipt=json.loads((Path(r['prompt']).parent/'exit.json').read_text())
            began=__import__('datetime').datetime.fromisoformat(r['started'])
            ended=__import__('datetime').datetime.fromisoformat(receipt['ended'])
            check((ended-began).total_seconds()<1,'fast stub exceeded one second')
    code,out,r=w.run(args=['--json'])
    check(code==0 and json.loads(out.splitlines()[0])['id']==r['id'] and
          out.splitlines()[-1].startswith('DONE · SONNET · '),'--json --wait final state line')
    w=World();code,out,r=w.run('sleep',wait=False);check(code==0,out)
    code,out=w.cmd(['jobs']);check(r['id'] in out and '⚙ SONNET job' in out,out)
    code,out=w.cmd(['show','latest']);check(code==0,out)
    labels=['BRIEF ·','COMMAND ·','STATE ·','TURNS','HAND-BACK','LEDGER ·']
    positions=[out.index(x) for x in labels];check(positions==sorted(positions),'show section order')
    code,out=w.cmd(['kill',r['id']]);check(code==0 and 'killed by hand' in out,out)
    check('**⇠ BACK FROM ANTHROPIC**' in out and '«Fixture job» KILLED · ' in out, 'kill return banner missing: '+out)
    side=w.side(r);wait_for(lambda:dead(side['pid']) and dead(side['grandchild']))
    check(w.get(r['id'])['state']=='fail','manual kill state')
    wait_for(lambda:len(w.lines('mail.jsonl'))==1)
    check(len(w.ledger())==1 and len(w.lines('notices.jsonl'))==2,'manual kill finalization')
    code,out=w.cmd(['show','missing']);check(code==2 and out.startswith('STOP:'),'unknown run exit')
    code,out,r=w.run();check(code==0,out)
    code,out=w.code('''import os,offload
from unittest.mock import patch
from pathlib import Path
r=offload.get_record('latest');r['state']='running';r['deadline']='2001-01-01T00:00:00+00:00'
offload.atomic(offload.run_folder(r)/'kill.json',{'time':offload.iso()})
offload.save(r)
with patch.object(offload.module('exo_common'),'kill_tree',side_effect=AssertionError('finished job was killed')):
 assert offload.watch(r['id'])==0
assert offload.get_record(r['id'])['state']=='done','late watch overrode receipt'
for ident,manual in [('stale-deadline',False),('stale-manual',True),('unreadable-manual',True)]:
 stale=dict(r,id=ident,run_id=ident,state='running',ledger=None,pid=os.getpid(),pgid=os.getpid(),
            process_start='not-this-process',prompt=str(offload.state_dir()/'runs'/ident/'prompt.md'))
 for key in ('letter_attempted','end_notice_attempted'):stale.pop(key,None)
 if manual:stale['deadline']=offload.iso(__import__('time').time()+60)
 offload.save(stale)
 with patch.object(offload.module('exo_common'),'kill_tree',side_effect=AssertionError('unconfirmed pid was killed')):
  if ident=='unreadable-manual':
   with patch.object(offload.module('exo_common'),'process_start_time',return_value=None):
    assert offload.main(['kill',ident])==0
  elif manual:assert offload.main(['kill',ident])==0
  else:assert offload.watch(ident)==3
 got=offload.get_record(ident)
 assert got['state']=='fail' and got['result']=='kill skipped: pid not confirmed'
assert offload.alive(os.getpid()),'stale kill harmed the gate'
''');check(code==0,out)


def G15():
    w=World()
    code,out=w.code(r'''import offload,os,json
from pathlib import Path,PureWindowsPath
from unittest.mock import patch
p=Path('argv.md').resolve();p.write_text('# Argv proof\nDo it.\n')
source=Path('sources').resolve();source.mkdir()
reports=Path('reports').resolve();reports.mkdir()
report=reports/'report.md'
extra=Path('extra').resolve();extra.mkdir()
for mind in ('sonnet','sol'):
 for kind in ('mechanical','reading'):
  for api in ('','fixture-key'):
   target='luna' if mind=='sol' and kind=='reading' else mind
   with patch.dict(os.environ,{'ANTHROPIC_API_KEY':api}):
    a=offload.parser().parse_args(['run',str(p),'--to',target,'--kind',kind,'--in',str(source),
                                 '--report',str(report),'--add-dir',str(extra),'--dry-run'])
    r,prompt,env=offload.prepare(a)
   head=[__import__('sys').executable,r['resolved_path']]
   dirs=[str(extra),str(reports),str(p.parent)]
   tail=[]
   for d in dirs:tail+=['--add-dir',d]
   effort='medium' if kind=='reading' else 'high'
   if mind=='sol':
    cwd=str(reports) if kind=='reading' else str(source)
    expected=head+['exec','--json','--color','never','--skip-git-repo-check','-s','workspace-write','-C',cwd]+tail+[
     '-m','gpt-6-luna' if kind=='reading' else 'gpt-6.1-sol','-c','model_reasoning_effort='+effort,'-o',str(offload.run_folder(r)/'last-message.md'),'--',prompt]
    assert r['cwd']==cwd
   else:
    allowed=(['Read','Glob','Grep','Write('+offload.claude_path_rule(report)+')','Edit('+offload.claude_path_rule(report)+')']
             if kind=='reading' else ['Read','Edit','Write','Glob','Grep','Bash(python3 *)','Bash(python *)','Bash(git status*)','Bash(git diff*)'])
    expected=head+['-p','--model','sonnet','--effort',effort,'--output-format','stream-json','--verbose',
     '--bare' if api else '--safe-mode','--no-session-persistence','--max-budget-usd','5','--permission-mode','default',
     '--add-dir',str(source)]+tail+['--allowedTools']+allowed+['--',prompt]
    assert not any(t in str(allowed) for t in ('git add','git commit','git push','Bash(rm'))
    assert '--dangerously-skip-permissions' not in r['argv'] and 'acceptEdits' not in r['argv']
   assert r['argv']==expected,(r['argv'],expected)
   assert set(r['writable'])=={r['cwd'],*dirs}
   if kind=='reading':assert 'read your sources in '+str(source) in prompt
# Explicit read-only must name an existing added root that covers the report.
a=offload.parser().parse_args(['run',str(p),'--to','sol','--sandbox','read-only','--report',str(report),'--dry-run'])
try:offload.prepare(a)
except offload.Stop as e:assert 'hand-back' in str(e)
else:raise AssertionError('read-only silently accepted')
a.add_dir=[str(reports)];r,_,_=offload.prepare(a)
assert r['sandbox']=='read-only' and r['writable']==[str(reports)]
# Prompt limit counts bytes, and Windows always takes the pointer.
with patch.object(os,'name','posix'):
 assert offload.prompt_argument('x'*30000,'prompt.md')==('x'*30000,False)
 assert offload.prompt_argument('é'*15001,'prompt.md')[1]
with patch.object(os,'name','nt'):
 arg,ptr=offload.prompt_argument('short',PureWindowsPath('C:/reports/prompt.md'))
 assert ptr and '\n' not in arg and arg.endswith('launch no browser or GUI application.')
assert offload.claude_path_rule(PureWindowsPath('C:/reports/report.md'))=='//c/reports/report.md'
# Windows prefers a registered exe to a PATH cmd. Probe without executing either.
common=offload.module('exo_common')
cmd=Path('runner.cmd').resolve();cmd.write_text('fixture')
exe=Path('runner.exe').resolve();exe.write_text('fixture')
reg={'minds':[{'name':'NATIVE','kind':'claude','headless':{'exe':'runner','candidates':{'windows':[str(cmd),str(exe)]}}}]}
with patch.object(common,'_reg',return_value=reg),patch('shutil.which',return_value=str(cmd)):
 with patch.object(common,'run_bounded',return_value=(0,'native fixture')) as call:
  found,_,_=common.headless_command('NATIVE','windows',os.environ)
  assert found==str(exe)
  assert call.call_args[0][0]==[str(exe),'--version']
# Atomic replacement tolerates five sharing violations, with five 50ms waits.
real=offload.os.replace;attempts=[]
def flaky(a,b):
 attempts.append(1)
 if len(attempts)<=5:raise PermissionError('pulse reader')
 return real(a,b)
with patch.object(offload.os,'replace',side_effect=flaky),patch.object(offload.time,'sleep') as sleep:
 offload.atomic('atomic.json',{'ok':True})
 assert len(attempts)==6 and [c.args for c in sleep.call_args_list]==[(.05,)]*5
with patch.object(offload.os,'replace',side_effect=PermissionError('held')),patch.object(offload.time,'sleep') as sleep:
 try:offload.atomic('atomic.json',{'ok':False})
 except PermissionError:pass
 else:raise AssertionError('permanent replace failure hidden')
 assert sleep.call_count==5
assert json.loads(Path('atomic.json').read_text())=={'ok':True}
assert not list(Path('.').glob('atomic.json.*.tmp'))
assert str(offload.codex_root())!=str(Path('decoy').resolve())
with patch.dict(os.environ,{'CODEX_HOME':str(Path('decoy').resolve())}):
 assert str(offload.codex_root())==common.machine_paths(offload.__file__)['roots']['codex']
# Flagship ledger lookup also follows a renamed row and its app_id prefix.
protector=offload.module('protector')
reg={'minds':[{'name':'SUN','kind':'claude','tier':'flagship','app_id':'claude-opus-5-5'}]}
with patch.object(common,'_reg',return_value=reg):
 assert protector.fable_row()[1]==protector.price_of('claude-opus-5-5')
# The protector controls its own ledger filename and state directory.
import contextlib,io
ledger=Path('protector-state').resolve();ledger.mkdir()
(ledger/'renamed-ledger.jsonl').write_text(json.dumps({'mind':'ONLY-IN-PROTECTOR','runner':'claude','seconds':1})+'\n')
with patch.object(protector,'DEFAULT_STATE_DIR',str(ledger)),patch.object(protector,'LEDGER_FILE','renamed-ledger.jsonl'):
 out=io.StringIO()
 with contextlib.redirect_stdout(out):offload.ledger_print(offload.parser().parse_args(['ledger','--all']))
 assert 'ONLY-IN-PROTECTOR' in out.getvalue()
''')
    check(code==0,out)
    # Run real stubs with the pointer (not just an argv assertion).
    for mind in ('sonnet','sol'):
        p=w.brief(body='# Long brief\n'+('Some plain content. '*2000)+'\n')
        code,out=w.cmd(['run',str(p),'--to',mind,'--wait'])
        check(code==0,out)
        r=w.records()[-1]
        check(r['prompt_pointer'] and r['argv'][-1].startswith('Read the file '),'long prompt did not use pointer')
        check(Path(r['prompt']).stat().st_size>30000 and r['state']=='done','pointer lost full prompt or report')
        check(r['lane']=='NORTH/hub' and 'letter → NORTH/hub (no lane named)' in out,'unaddressed letter')
    # Reader hand-backs on both vendors, and only the permitted scoped fallback.
    for mind in ('sonnet','luna'):
        code,out,r=w.run(mind=mind,args=['--kind','reading','--report',str(w.root/'new-reports'/('read-'+mind+'.md'))])
        check(code==0 and r['state']=='done',out)
        check(r['sandbox']=='workspace-write','reader sandbox')
        if mind=='luna':check(r['cwd']==str(Path(r['report']).parent),'reader root is not report folder')
        else:check(r['write_scope']=='report','initial reading write scope')
    # A fast denial can retry during the start notice. Slow only that seam to
    # prove the parent never overwrites the executor's new scope/argv.
    w.notice.write_text('import time\ntime.sleep(.3)\n'+w.notice.read_text(),encoding='utf-8')
    code,out,r=w.run('scope-denied',args=['--kind','reading'])
    check(code==0 and r['write_scope']=='unscoped' and len(r.get('attempts',[]))==1,
          out+' code='+str(code)+' scope='+str(r.get('write_scope'))+' result='+r.get('result',''))
    check(r['argv'][r['argv'].index('--permission-mode')+1]=='default','fallback widened mode')
    check(float(r['argv'][r['argv'].index('--max-budget-usd')+1])<float(r['cap_usd']),'fallback reset budget cap')
    check(r['ledger']['tokens']['input']==16000 and abs(r['ledger']['cli_cost_usd']-.0842)<1e-9,'fallback usage/cost lost an attempt')
    check(' · 1 tool denials' in r['result'],'fallback hid initial denial')
    code,out,r=w.run('denied',args=['--kind','reading'])
    check(code==3 and r['write_scope']=='report' and not r.get('attempts'),'unrelated denial widened tools')


def G16():
    w=World()
    small='# Complexity fixture\nDo the small job.\n'
    big='# Complexity fixture\n'+('x'*4200)+'\n'
    cases=[
        ('reading',small,'',['--kind','reading'],'LUNA','gpt-6-luna','simple','size'),
        ('simple size',small,'touches: one.py',[],'SOL','gpt-6.1-sol','simple','size'),
        ('complex size',big,'',[],'ASTRA','gpt-6-astra','complex','size'),
        ('complex flag',small,'',['--complexity','complex'],'ASTRA','gpt-6-astra','complex','flag'),
        ('simple header',big,'complexity: simple',[],'SOL','gpt-6.1-sol','simple','header'),
    ]
    for label,body,header,args,mind,model,complexity,by in cases:
        p=w.brief(header,body)
        code,out=w.cmd(['run',str(p),'--lane','NORTH/Test','--wait']+args)
        check(code==0,label+': '+out)
        r=w.records()[-1]
        check(r['mind']==mind and r['argv'][r['argv'].index('-m')+1]==model,label+' argv/model')
        check(r['model']==model and r['complexity']==complexity and r['complexity_by']==by,label+' record')
        if by=='size':
            count=1 if header.startswith('touches:') else 0
            reason='%s by size (%s B · %d %s)' % (complexity,format(p.stat().st_size,','),count,'path' if count==1 else 'paths')
        else:
            reason=complexity+(' (--complexity)' if by=='flag' else ' (complexity: header)')
        if label=='reading':reason='reading → cheap reader · '+reason
        line=next(line for line in out.splitlines() if line.startswith('OFFLOAD '))
        check(' · '+mind+' '+model+' · '+reason+' · ' in line,label+' routing reason: '+line)
        check(r['effort']==('medium' if label=='reading' else 'high'),label+' effort')
    before=len(w.records());probes=len(w.lines('probes.jsonl'))
    p=w.brief(body=small)
    code,out=w.cmd(['run',str(p),'--to','luna','--kind','judgment','--wait'])
    check(code==2 and out.startswith('STOP: judgment needs a flagship') and len(out.splitlines())==1,'LUNA judgment refusal')
    check(len(w.records())==before and len(w.lines('probes.jsonl'))==probes,'forbidden mind invoked a CLI')

    # Boundaries, precedence, explicit minds, symmetry and routine safeguards.
    # Public prepare/argv is checked; these probes do not launch model jobs.
    code,out=w.code(r'''import offload,exo_common,os
from pathlib import Path
from unittest.mock import patch
p=Path('boundary.md').resolve()
def prepared(body,header='',args=()):
 p.write_bytes(((header+'\n---\n' if header else '')+body).encode('utf-8'))
 a=offload.parser().parse_args(['run',str(p),'--dry-run']+list(args))
 return offload.prepare(a)[0]
for length,expected in [(4095,'SOL'),(4096,'ASTRA')]:
 r=prepared('# Boundary\n'+'x'*(length-len('# Boundary\n')))
 assert r['mind']==expected and r['brief_bytes']==length and r['complexity_by']=='size'
r=prepared('# Bytes\n'+'é'*2050)
assert len(p.read_text())<4096 and r['mind']=='ASTRA' and r['brief_bytes']==p.stat().st_size
for touches,expected,count in [('a.py,b.py','SOL',2),('a.py\n - b.py\n - c.py','ASTRA',3),('','SOL',0)]:
 r=prepared('# Paths\n','touches: '+touches)
 assert r['mind']==expected and r['touches_count']==count
r=prepared('# Flag wins\n','complexity: complex',['--complexity','simple'])
assert r['mind']=='SOL' and r['complexity_by']=='flag'
r=prepared('# BOM\n'+'x'*(4094-len('# BOM\n')))
p.write_bytes(b'\xef\xbb\xbf'+p.read_bytes())
r=offload.prepare(offload.parser().parse_args(['run',str(p),'--dry-run']))[0]
assert r['mind']=='ASTRA' and r['brief_bytes']==4097
for args,header in [(['--complexity','medium'],''),([], 'complexity: medium')]:
 try:prepared('# Invalid\n',header,args)
 except offload.Stop as e:assert str(e)=='complexity must be simple or complex'
 else:raise AssertionError('invalid complexity accepted')
for target,model in [('astra','gpt-6-astra'),('sol','gpt-6.1-sol'),('luna','gpt-6-luna')]:
 for level in ('simple','complex'):
  r=prepared('# Named mind\n','to: astra',['--to',target,'--complexity',level])
  assert r['mind']==target.upper() and r['argv'][r['argv'].index('-m')+1]==model
  assert r['routing_reason'].endswith('mind named by --to')
r=prepared('# Named header\n','to: luna\ncomplexity: complex')
assert r['mind']=='LUNA' and r['routing_reason'].endswith('mind named by to: header')
r=prepared('# Alias\n',args=['--to','gpt'])
assert r['mind']=='ASTRA' and r['model']=='gpt-6-astra'
r=prepared('# Judgment\n',args=['--kind','judgment'])
assert r['mind']=='ASTRA' and r['model']=='gpt-6-astra' and r['routing_reason'].startswith('judgment → flagship')
r=prepared('# Routine\n',args=['--routine'])
assert r['mind']=='SOL' and r['effort']=='low'
for args in (['--routine','--complexity','complex'],['--routine','--to','astra']):
 try:prepared('# No flagship routine\n',args=args)
 except offload.Stop as e:assert 'a flagship cannot run a routine' in str(e)
 else:raise AssertionError('flagship routine without reason')
try:prepared('# Exception\n','model-reason: explicit test exception',['--routine','--complexity','complex'])
except offload.Stop as e:assert 'a flagship cannot run a routine' in str(e) and 'a reason does not lift it' in str(e)
else:raise AssertionError('flagship routine with reason')
for target in ('astra','fable'):
 try:prepared('# Routine judgment\n','model-reason: never enough',['--to',target,'--routine','--kind','judgment'])
 except offload.Stop as e:assert 'refused outright' in str(e)
 else:raise AssertionError('routine judgment ran')
with patch.object(exo_common,'session_identity',return_value={'vendor':'codex'}):
 for level,mind,model in [('simple','SONNET','sonnet'),('complex','OPUS','opus')]:
  r=prepared('# Reverse road\n',args=['--complexity',level])
  assert r['mind']==mind and r['argv'][r['argv'].index('--model')+1]==model
 r=prepared('# Reader\n',args=['--kind','reading'])
 assert r['mind']=='HAIKU'
 r=prepared('# Judgment\n',args=['--kind','judgment'])
 assert r['mind']=='FABLE'
# Names and order are data; renaming every mind leaves tier/kind choices intact.
reg=exo_common._reg()
for m in reg['minds']:m['name']='RENAMED-'+m['name']
reg['minds'].reverse()
with patch.object(exo_common,'_reg',return_value=reg):
 for vendor,kind,level,expected in [('claude','reading','simple','LUNA'),('claude','mechanical','simple','SOL'),('claude','mechanical','complex','ASTRA'),('codex','mechanical','simple','SONNET'),('codex','mechanical','complex','OPUS'),('codex','reading','simple','HAIKU')]:
  assert offload.default_mind(reg,vendor,kind,level)=='RENAMED-'+expected
''');check(code==0,out)


def live_world():
    w=World()
    # Explicit --live restores the caller's authentication and real CLIs;
    # records, work, mail and ledgers remain isolated in this temp world.
    real=source('exo_common.py').parent.parent/'registry.json'
    w.reg=json.loads(real.read_text(encoding='utf-8'))
    for merge in (BUILD/'round2/registry.patch2.json',BUILD/'registry.patch2.json',BUILD/'registry.patch3.json'):
        changes=json.loads(merge.read_text(encoding='utf-8')) if merge.exists() else {}
        for name,fields in changes.items():
            row=next((m for m in w.reg['minds'] if m['name']==name),None)
            if row is None:
                row={'name':name};w.reg['minds'].append(row)
            row.update(fields)
    w.write_reg()
    for key in ('HOME','USERPROFILE','PATH','CODEX_HOME','ANTHROPIC_API_KEY','PYTHONPATH'):
        if key in os.environ:w.env[key]=os.environ[key]
        else:w.env.pop(key,None)
    return w


def live_check(code,out,r,w):
    log=Path(r['log']).read_text(encoding='utf-8',errors='replace') if r else out
    if any(t in (log+out).lower() for t in ('not logged in','please run /login','authentication required','not signed in')):
        raise AssertionError('waits on the login — '+(r.get('result','') if r else out.strip()))
    check(code==0,out+' '+(r.get('result','') if r else ''))
    check(r['state']=='done' and r.get('version') and r.get('resolved_path'),'live finder/contract/record')
    check(len([x for x in w.ledger() if x['run_id']==r['id']])==1,'live ledger missing')


def live_result_text(w, label, code, out, r):
    """Preserve exact CLI bytes for a bounded prompt/denial diagnosis."""
    log=Path(r['log']).read_text(encoding='utf-8',errors='replace') if r else ''
    results=[]
    for line in log.splitlines():
        try:ev=json.loads(line)
        except ValueError:continue
        if isinstance(ev,dict) and ev.get('type')=='result':results.append(ev)
    (w.root/(label+'-result.txt')).write_text(out+'\n'+log,encoding='utf-8')
    if code==4 or (r and r['state']=='timeout'):
        print(label+' exact bounded CLI output:\n'+out+log,flush=True)
        raise AssertionError('waits on the hub — default mode -p timed out; no permission widening')
    if not results:
        print(label+' exact CLI output (no result object):\n'+out+log,flush=True)
    else:
        print(label+' result objects: '+json.dumps(results,ensure_ascii=False),flush=True)
    return results


def G11():
    w=live_world()
    print('G11 live: SONNET · up to $5 per permission attempt · default mode only; bounded at 2m',flush=True)
    body='# Permission probe\nUse only the Write tool to write OK and the required DONE line to the report. Do not use Bash, Edit or another tool. If Write is denied, report that denial.\n'
    p=w.brief(body=body)
    args=['run',str(p),'--to','sonnet','--lane','NORTH/Test','--timeout','2m','--wait']
    code,out=w.cmd(args,timeout=210);rows=w.records();r=rows[-1] if rows else None
    live_result_text(w,'G11a',code,out,r)
    live_check(code,out,r,w)
    check(Path(r['report']).is_file(),'G11a Write in list did not create file')
    p=w.brief(body=body)
    # Probe B removes both Write and Edit; Edit(path) can authorize Write too.
    probe="import sys\nsys.path.insert(0,"+repr(str(w.tools))+ ")\nimport offload\noriginal=offload.prepare\ndef prepare(a):\n r,p,e=original(a)\n at=r['argv'].index('--allowedTools')\n end=r['argv'].index('--',at)\n r['argv'][at+1:end]=['Read','Glob','Grep']\n return r,p,e\noffload.prepare=prepare\nraise SystemExit(offload.main("+repr(['run',str(p),'--to','sonnet','--lane','NORTH/Test','--timeout','2m','--wait'])+"))\n"
    path=w.root/'permissions-probe.py';path.write_text(probe,encoding='utf-8')
    cp=subprocess.run([PY,str(path)],cwd=str(w.root),env=w.env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',timeout=210)
    rows=w.records();r=rows[-1] if rows else None
    results=live_result_text(w,'G11b',cp.returncode,cp.stdout,r)
    check(r and cp.returncode==3 and r['state']=='fail' and not Path(r['report']).exists() and
          any(e.get('permission_denials') for e in results),
          'Write absent must report permission_denials and create no file; '+(r.get('result','') if r else cp.stdout))
    # C proves the production reading pair's absolute path anchor, including
    # a forbidden sibling. A recorded fallback is permitted only on report denial.
    outside=w.work/'outside-report.md'
    p=w.brief(body='# Scoped permission probe\nUse only Write. First try to write OUTSIDE to '+str(outside)+
              '. If denied, continue. Then write OK and the required DONE line to the report. Do not use Bash or another tool.\n')
    code,out=w.cmd(['run',str(p),'--to','sonnet','--kind','reading','--lane','NORTH/Test','--timeout','2m','--wait'],timeout=210)
    r=w.records()[-1]
    results=live_result_text(w,'G11c',code,out,r)
    live_check(code,out,r,w)
    if r['write_scope']=='report':
        check(not outside.exists(),'G11c path-scoped rules allowed an unrelated file')
        check(any(d.get('tool_name')=='Write' for e in results for d in e.get('permission_denials',[])),
              'G11c did not actually probe the outside-path denial')
        print('G11c PASS: report path writes; sibling denied; write_scope: report',flush=True)
    else:
        check(r['write_scope']=='unscoped' and r.get('attempts') and
              r.get('scope_fallback_reason')=='CLI denied the path-scoped report write',
              'G11c unscoped fallback lacks explicit report-denial evidence')
        print('G11c PASS: path rule denied report; authorized fallback wrote it; write_scope: unscoped',flush=True)


def G14():
    w=live_world()
    # G14 alone raises REAL desktop notices through the postman renderer.
    # No browser/login UI is opened; an unreadable login fails in one line.
    w.env.pop('EXO_OFFLOAD_NOTIFY',None)
    for mind in ('sonnet','astra'):
        print('G14 live: %s · %s · one one-word job' %
              (mind.upper(),'up to $5' if mind=='sonnet' else 'ChatGPT plan quota; registry mechanical model'),flush=True)
        p=w.brief(body=(FIX/'one-word.md').read_text(encoding='utf-8'))
        code,out=w.cmd(['run',str(p),'--to',mind,'--lane','NORTH/Test','--reason','one-word live acceptance proof',
                        '--timeout','2m','--wait'],timeout=210)
        rows=w.records();r=rows[-1] if rows else None
        live_check(code,out,r,w)
        check(r.get('start_notice_attempted') and r.get('end_notice_attempted') and
              not r.get('start_notice_error') and not r.get('end_notice_error'),'live desktop notice failed')


def B1():
    for mind, company, product in (('sol','OPENAI','CODEX'), ('astra','OPENAI','CODEX'),
                                   ('luna','OPENAI','CODEX'), ('sonnet','ANTHROPIC','CLAUDE')):
        w=World()
        code,out,r=w.run(mind=mind,args=['--reason','banner fixture'])
        check(code==0,out)
        deadline=datetime.fromisoformat(r['deadline']).astimezone().strftime('%H:%M')
        expected=('---\n**⇢ SENT TO %s** `%s · %s · BACKGROUND` — «Fixture job» · back by %s · '
                  '**nothing for you to do**\n---') % (company,mind.upper(),product,deadline)
        check(out.startswith(expected+'\nOFFLOAD '),out)


def B2():
    w=World(); brief=w.brief()
    # Capture the public JSON at the launch boundary and compare every original
    # key/value to the actual in-memory record, before the waiter mutates it.
    code,out=w.code('''import contextlib,io,json
import offload
capture=io.StringIO()
wait=offload.foreground_wait
def verify(record,env,quiet):
 assert quiet
 payload=json.loads(capture.getvalue().splitlines()[0])
 assert set(payload)==set(record)|{'banner_out'},set(payload)^set(record)
 assert payload.pop('banner_out')==offload.banner_out(record)
 assert payload==record,'an existing JSON key or value changed'
 return wait(record,env,quiet)
offload.foreground_wait=verify
with contextlib.redirect_stdout(capture):
 code=offload.main(['run',BRIEF,'--to','sol','--lane','NORTH/Test','--wait','--json'])
assert code==0,capture.getvalue()
print('launch JSON preserves every original field')
'''.replace('BRIEF',repr(str(brief))))
    check(code==0,out)


def B3():
    w=World(); code,out,r=w.run(mind='sol');check(code==0,out)
    text=w.lines('mail.jsonl')[0][-2]
    banner='\n'.join(text.splitlines()[:3])
    expected=('---\n**⇠ BACK FROM OPENAI** `SOL · %.1f min` — «Fixture job» DONE · %s · '
              'check owed here\n---') % (r['minutes'],r['result'][:80])
    check(banner==expected,text)
    tail='SOL job «Fixture job» DONE in %.1f min — report %s' % (r['minutes'],r['report'])
    check(text==expected+'\n'+tail and w.lines('mail.jsonl')[0][-1]=='read-report',text)
    check(expected+'\nDONE · SOL · ' in out,'foreground return banner missing or out of order: '+out)
    code,shown=w.cmd(['show',r['id']]);check(code==0 and shown.startswith(expected+'\nBRIEF · '),shown)
    code,out=w.code('''import offload
r=offload.get_record('latest')
r['result']='x'*100+'\\nmore'
banner=offload.banner_back(r)
assert ' · '+'x'*80+' · check owed here' in banner,banner
assert 'x'*81 not in banner and len(banner.splitlines())==3,banner
''');check(code==0,out)


def B4():
    w=World(); code,out,r=w.run('no-report',mind='sol');check(code==3,out)
    text=w.lines('mail.jsonl')[0][-2]
    check('**⇠ BACK FROM OPENAI**' in out and '«Fixture job» FAILED · ' in out,out)
    check(text.startswith('---\n**⇠ BACK FROM OPENAI**') and ' FAILED · ' in text,text)
    code,shown=w.cmd(['show',r['id']]);check(code==0 and ' FAILED · ' in shown.splitlines()[1],shown)
    code,out=w.code('''import offload
r=offload.get_record('latest')
r.update(state='timeout',result='TIMEOUT — deadline reached')
assert ' TIMED-OUT · ' in offload.banner_back(r)
r.update(state='fail',result='killed by hand')
assert ' KILLED · ' in offload.banner_back(r)
''');check(code==0,out)


def B5():
    w=World()
    next(row for row in w.reg['minds'] if row['name']=='SOL')['vendor']='unregistered company'
    w.write_reg()
    code,out,r=w.run(mind='sol');check(code==0,out)
    check(out.startswith('---\n**⇢ SENT TO SOL** `SOL · CODEX · BACKGROUND`'),out)
    check('**⇠ BACK FROM SOL**' in out,out)
    check(w.lines('mail.jsonl')[0][-2].startswith('---\n**⇠ BACK FROM SOL**'), 'fallback letter missing')


def main():
    if Path.cwd().name=='tools':
        print('STOP: run the gate from a folder not named tools');return 1
    cases=[('G'+str(n),globals()['G'+str(n)]) for n in range(17) if n not in (11,14)]
    cases += [('B'+str(n),globals()['B'+str(n)]) for n in range(1,6)]
    live='--live' in sys.argv
    if live:cases += [('G11',G11),('G14',G14)]
    only = sys.argv[sys.argv.index('--only')+1] if '--only' in sys.argv else None
    if only:
        cases=[x for x in cases if x[0]==only]
        if not cases:
            print('STOP: unknown or disabled case '+only);return 1
    passed=0
    hermetic=0
    live_passed=0
    total=len(cases) if only or live else len(cases)+2
    def count(reason=''):
        print('%d/%d%s · hermetic %d/%d · live %d/%d' % (passed,total,
              ' · '+reason if reason else '',hermetic,
              sum(n not in ('G11','G14') for n,_ in cases),live_passed,
              sum(n in ('G11','G14') for n,_ in cases) if only else 2),flush=True)
    try:
        for name,case in cases:
            try:case()
            except Exception as exc:
                print('%s FAIL: %s'%(name,exc),flush=True)
                reason=(name+' waits on the login') if 'waits on the login' in str(exc) else name+' failed: '+str(exc)
                count(reason);return 1
            passed+=1
            if name in ('G11','G14'):live_passed+=1
            else:hermetic+=1
            print(name+' PASS',flush=True)
        if not live:
            print('G11 skipped: live Claude permissions proof requires --live')
            print('G14 skipped: real vendor jobs require --live and signed-in CLIs')
        count('G14 waits on --live (login unprobed)' if not live else '')
        return 0
    finally:
        for w in WORLDS:w.cleanup()

if __name__=='__main__':
    raise SystemExit(main())
