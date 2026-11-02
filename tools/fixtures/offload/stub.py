#!/usr/bin/env python3
"""Canned headless events; never a model, network call, GUI, or repository command."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

def run(vendor):
    probe = os.environ.get('OFFLOAD_STUB_PROBES')
    if probe and ('--version' in sys.argv or sys.argv[1:] in (['auth', 'status'], ['login', 'status'])):
        with open(probe, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'vendor':vendor,'argv':sys.argv[1:]}) + '\n')
    if '--version' in sys.argv:
        print(vendor + '-fixture 1.0'); return 0
    if sys.argv[1:] in (['auth', 'status'], ['login', 'status']):
        logged = os.environ.get('OFFLOAD_STUB') != 'not-logged-in'
        print(json.dumps({'loggedIn': logged}))
        return 0 if logged else 1
    scenario = os.environ.get('OFFLOAD_STUB', 'done')
    data = json.loads((Path(__file__).parent / (scenario + '.json')).read_text(encoding='utf-8'))
    prompt = sys.argv[sys.argv.index('--') + 1]
    pointer = re.fullmatch(r'Read the file (.*?) in full and follow it as your brief;.*', prompt)
    if pointer:
        prompt = Path(pointer[1]).read_text(encoding='utf-8')
    report = re.search(r'^Hand back by writing (.*?) \(create or append', prompt, re.M)[1]
    prefix = re.search(r'^Its LAST line must be (.*?) — <one line of result>', prompt, re.M)[1]
    done = prefix + ' — OK'
    runid = os.environ['EXO_OFFLOAD_RUN']
    side = Path(os.environ['OFFLOAD_STUB_OUT']) / (runid + '.json')
    side.parent.mkdir(parents=True, exist_ok=True)
    echo = {'argv': sys.argv, 'env': {k: os.environ.get(k) for k in
            ['CHROME', 'BROWSER', 'EXO_OFFLOAD_RUN', 'CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT',
             'CLAUDE_CODE_SESSION_ID','CLAUDE_CODE_HOST_SESSION_ID','CLAUDE_CODE_CHILD_SESSION',
             'CLAUDE_CODE_MESSAGING_SOCKET','CLAUDE_CODE_MESSAGING_TOKEN','CLAUDE_CODE_FUTURE']},
            'prompt_head': prompt.splitlines()[:20], 'stdin_isatty':sys.stdin.isatty(),
            'stdin_readable':sys.stdin.readable(), 'stdin_devnull':os.path.samestat(os.fstat(0), os.stat(os.devnull)),
            'stdin': sys.stdin.read(), 'pid': os.getpid()}
    if data.get('sleep'):
        marker = 'offload-grandchild-' + runid
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)', marker], stdin=subprocess.DEVNULL)
        echo.update(grandchild=child.pid, marker=marker)
    side.write_text(json.dumps(echo), encoding='utf-8')
    if data.get('sleep'):
        if data.get('live_step'):
            if vendor == 'codex':
                event = {'type':'item.completed','item':{'type':'command_execution','command':data['live_step']}}
            else:
                name, _, argument = data['live_step'].partition(' ')
                event = {'type':'assistant','message':{'content':[{'type':'tool_use','name':name,
                         'input':{'file_path':argument,'ignored_second_argument':'not the displayed argument'}}]}}
            print(json.dumps(event), flush=True)
        print(json.dumps({'type':'thread.started', 'thread_id':'fixture-' + runid}), flush=True)
        time.sleep(600)
    time.sleep(data.get('delay', 0))
    mode = data.get('report')
    if data.get('scope_fallback') and 'Write' in sys.argv:
        mode = 'done'
        data['claude'][-1]['permission_denials'] = []
    if mode:
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        Path(report).write_text({'done': 'OK\n' + done + '\n', 'no-done':'unfinished\n', 'fail':'FAIL — fixture could not finish\n'}[mode], encoding='utf-8')
    for ev in data[vendor]:
        raw = json.dumps(ev).replace('DONE_LINE', done).replace('THREAD_ID', 'fixture-' + runid)
        raw = raw.replace('REPORT_PATH', json.dumps(report)[1:-1])
        print(raw, flush=True)
    if vendor == 'codex' and '-o' in sys.argv:
        Path(sys.argv[sys.argv.index('-o')+1]).write_text(done, encoding='utf-8')
    return data.get('exit', 0)
