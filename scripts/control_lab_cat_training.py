#!/usr/bin/env python3
"""Prepare, validate and monitor the cat interval baseline on the lab server."""
from __future__ import annotations

import argparse
import json
import shlex

from migrate_pet_final_to_lab import connect


REMOTE = r'''
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path('/home/wyy/pet-final')
python = root / '.runtime/pet/bin/python'
action = sys.argv[1]
smoke = action.startswith('smoke_')
verb = action[6:] if smoke else action
result = root / 'results/training' / ('cat_interval_smoke' if smoke else 'cat_interval_baseline')
result.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['PYTHONPATH'] = str(root) + os.pathsep + env.get('PYTHONPATH', '')
env['CUDA_VISIBLE_DEVICES'] = '1' if smoke else '0'
if verb in ('prepare', 'preflight', 'verify'):
    script = {'prepare': 'prepare_cat_interval_baseline.py',
              'preflight': 'check_cat_interval_baseline.py',
              'verify': 'verify_cat_interval_smoke.py'}[verb]
    command = [str(python), '-B', str(root / 'scripts' / script)]
    if verb == 'prepare':
        command += ['--root', str(root)]
    if smoke and verb != 'verify':
        command += ['--smoke']
    completed = subprocess.run(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=1200)
    if completed.returncode:
        raise RuntimeError(action + ' failed: ' + completed.stderr[-2500:] + completed.stdout[-1000:])
    print(completed.stdout.strip().splitlines()[-1])
elif verb == 'start':
    pid_path = result / 'job.pid'
    if pid_path.exists():
        old = int(pid_path.read_text())
        cmdline = Path('/proc/' + str(old) + '/cmdline')
        if cmdline.exists() and b'run_cat_interval_baseline.py' in cmdline.read_bytes():
            raise RuntimeError('Training job is already active')
    with (result / 'job.log').open('ab') as stream:
        command = [str(python), '-B', str(root / 'scripts/run_cat_interval_baseline.py')]
        if smoke:
            command += ['--smoke']
        proc = subprocess.Popen(command,
                                cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    pid_path.write_text(str(proc.pid) + '\n')
    print(json.dumps({'pid': proc.pid, 'result_dir': str(result)}))
elif verb == 'status':
    pid_path = result / 'job.pid'
    pid = int(pid_path.read_text()) if pid_path.exists() else None
    proc_path = Path('/proc/' + str(pid) + '/cmdline') if pid is not None else None
    active = bool(proc_path and proc_path.exists() and
                  b'run_cat_interval_baseline.py' in proc_path.read_bytes())
    status_path = result / 'run_status.json'
    state = json.loads(status_path.read_text()) if status_path.exists() else {}
    logs = {}
    for name in ('job', 'train', 'test'):
        path = result / (name + '.log')
        logs[name] = path.read_text(errors='replace').splitlines()[-6:] if path.exists() else []
    print(json.dumps({'active': active, 'pid': pid, 'state': state, 'log_tail': logs},
                     ensure_ascii=False))
else:
    raise RuntimeError('Unsupported action')
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'preflight', 'start', 'status',
                                           'smoke_prepare', 'smoke_preflight',
                                           'smoke_start', 'smoke_status', 'smoke_verify'])
    args = parser.parse_args()
    client = connect()
    try:
        command = 'python3 -c ' + shlex.quote(REMOTE) + ' ' + shlex.quote(args.action)
        _, stdout, stderr = client.exec_command(command, timeout=1300)
        code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', 'replace')
        err = stderr.read().decode('utf-8', 'replace')
        if code:
            raise RuntimeError(f'{args.action} failed ({code}): {err[:3500]} {out[:1000]}')
        print(json.dumps(json.loads(out.splitlines()[-1]), ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
