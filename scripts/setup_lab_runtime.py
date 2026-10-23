#!/usr/bin/env python3
"""Clone the lab action environment and install optional research dependencies safely."""
from __future__ import annotations

import argparse
import json
import shlex

from migrate_pet_final_to_lab import connect


REMOTE = r'''
import importlib.metadata as md
import json
from pathlib import Path
import subprocess
import sys

root = Path('/home/wyy/pet-final')
old = Path('/home/wyy/miniconda3/envs/pet')
new = root / '.runtime/pet'
logs = root / 'results/migration_lab'
logs.mkdir(parents=True, exist_ok=True)
action = sys.argv[1]
if action == 'clone':
    if not (new / 'bin/python').is_file():
        new.parent.mkdir(parents=True, exist_ok=True)
        command = ['/home/wyy/miniconda3/bin/conda', 'create', '-y', '-p', str(new), '--clone', str(old)]
        with (logs / 'runtime_clone.log').open('w') as log:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=1800)
        if result.returncode:
            raise RuntimeError('Conda clone failed; see runtime_clone.log')
    print(json.dumps({'python': str(new / 'bin/python'), 'ready': (new / 'bin/python').is_file()}))
elif action == 'install-aux':
    if not (new / 'bin/python').is_file():
        raise RuntimeError('Run clone first')
    constraints = logs / 'preserve_core.txt'
    versions = subprocess.check_output([str(new / 'bin/python'), '-m', 'pip', 'freeze'], text=True)
    core = ('torch', 'torchvision', 'mmcv', 'mmengine', 'mmaction2', 'numpy')
    selected = [line for line in versions.splitlines()
                if line.partition('==')[0].lower() in core and '==' in line]
    constraints.write_text('\n'.join(selected) + '\n')
    command = [str(new / 'bin/python'), '-m', 'pip', 'install', '-c', str(constraints),
               '-r', str(root / 'configs/company_auxiliary_requirements.txt')]
    with (logs / 'runtime_aux_install.log').open('w') as log:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT, timeout=3600)
    print(json.dumps({'exit_code': result.returncode, 'log': str(log),
                      'constraints': selected}))
    if result.returncode:
        sys.exit(result.returncode)
elif action == 'audit':
    if not (new / 'bin/python').is_file():
        raise RuntimeError('Cloned environment missing')
    code = """import importlib.metadata as m, json, torch
names=['torch','torchvision','mmcv','mmengine','mmaction2','numpy','ultralytics','rembg','onnxruntime','rknn-toolkit2','ruptures','hmmlearn','pytorch-tcn']
result={}
for name in names:
 try: result[name]=m.version(name)
 except m.PackageNotFoundError: result[name]=None
print(json.dumps({'versions':result,'cuda_available':torch.cuda.is_available()}))"""
    output = subprocess.check_output([str(new / 'bin/python'), '-c', code], text=True, timeout=120)
    print(output)
elif action == 'status':
    clone_log = logs / 'runtime_clone.log'
    aux_log = logs / 'runtime_aux_install.log'
    print(json.dumps({'clone_ready': (new / 'bin/python').is_file(),
                      'clone_tail': clone_log.read_text(errors='replace').splitlines()[-8:]
                      if clone_log.exists() else [],
                      'aux_tail': aux_log.read_text(errors='replace').splitlines()[-8:]
                      if aux_log.exists() else []}, ensure_ascii=False))
else:
    raise RuntimeError('Unsupported action')
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['clone', 'install-aux', 'audit', 'status'])
    args = parser.parse_args()
    client = connect()
    try:
        command = 'python3 -c ' + shlex.quote(REMOTE) + ' ' + shlex.quote(args.action)
        _, stdout, stderr = client.exec_command(command, timeout=3700)
        status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', 'replace')
        error = stderr.read().decode('utf-8', 'replace')
        if status:
            raise RuntimeError(f'{args.action} failed ({status}): {error[:2000]} {output[:1000]}')
        print(json.dumps(json.loads(output), ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
