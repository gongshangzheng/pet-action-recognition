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
import shutil
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
    code = """import importlib.metadata as m, json, torch, importlib
names=['torch','torchvision','mmcv','mmengine','mmaction2','numpy','ultralytics','rembg','onnxruntime','rknn-toolkit2','ruptures','hmmlearn','pytorch-tcn']
result={}
for name in names:
 try: result[name]=m.version(name)
 except m.PackageNotFoundError: result[name]=None
imports={}
for name in ['mmaction','mmcv','mmengine','mmdet','decord','ultralytics','rembg','onnxruntime','rknn']:
 try:
  module=importlib.import_module(name)
  imports[name]=getattr(module,'__file__',None)
 except Exception as exc: imports[name]=type(exc).__name__+': '+str(exc)[:180]
print(json.dumps({'versions':result,'cuda_available':torch.cuda.is_available(),'imports':imports}))"""
    output = subprocess.check_output([str(new / 'bin/python'), '-c', code], text=True, timeout=120)
    check = subprocess.run([str(new / 'bin/python'), '-m', 'pip', 'check'], capture_output=True,
                           text=True, timeout=120)
    result = json.loads(output.splitlines()[-1])
    result['pip_check'] = {'exit_code': check.returncode, 'output': check.stdout.strip()[:3000]}
    print(json.dumps(result))
elif action == 'bind-project':
    if not (new / 'bin/python').is_file():
        raise RuntimeError('Cloned environment missing')
    command = [str(new / 'bin/python'), '-m', 'pip', 'install', '--no-deps',
               '-e', str(root / 'models/mmaction2')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    (logs / 'runtime_bind_mmaction.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('MMAction2 project binding failed; see runtime_bind_mmaction.log')
    print(json.dumps({'project': str(root / 'models/mmaction2'), 'bound': True}))
elif action == 'status':
    clone_log = logs / 'runtime_clone.log'
    aux_log = logs / 'runtime_aux_install.log'
    bind_log = logs / 'runtime_bind_mmaction.log'
    processes = subprocess.run(['ps', '-eo', 'pid,etime,stat,comm,args'], capture_output=True, text=True)
    clone_processes = [line.strip() for line in processes.stdout.splitlines()
                       if len(line.split(None, 4)) == 5 and
                       line.split(None, 4)[4].startswith('/home/wyy/miniconda3/bin/conda create')]
    size = subprocess.run(['du', '-sh', str(new)], capture_output=True, text=True)
    node = subprocess.run(['node', '--version'], capture_output=True, text=True) if shutil.which('node') else None
    npm = subprocess.run(['npm', '--version'], capture_output=True, text=True) if shutil.which('npm') else None
    print(json.dumps({'clone_ready': (new / 'bin/python').is_file(),
                      'node_version': node.stdout.strip() if node and node.returncode == 0 else None,
                      'npm_version': npm.stdout.strip() if npm and npm.returncode == 0 else None,
                      'web_node_modules': (root / 'web/node_modules').is_dir(),
                      'clone_processes': clone_processes[:5],
                      'clone_directory_size': size.stdout.strip() if size.returncode == 0 else None,
                      'clone_tail': clone_log.read_text(errors='replace').splitlines()[-8:]
                      if clone_log.exists() else [],
                      'aux_tail': aux_log.read_text(errors='replace').splitlines()[-8:]
                      if aux_log.exists() else [],
                      'bind_tail': bind_log.read_text(errors='replace').splitlines()[-12:]
                      if bind_log.exists() else []}, ensure_ascii=False))
elif action == 'fix-rich':
    command = [str(new / 'bin/python'), '-m', 'pip', 'install', 'rich~=13.4.2']
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    (logs / 'runtime_rich_fix.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Rich version adjustment failed; see runtime_rich_fix.log')
    print(json.dumps({'rich_adjusted': True}))
elif action == 'install-web':
    command = ['npm', 'ci', '--no-audit', '--no-fund']
    with (logs / 'web_npm_ci.log').open('w') as log:
        result = subprocess.run(command, cwd=root / 'web', stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    print(json.dumps({'exit_code': result.returncode, 'node_modules':
                      (root / 'web/node_modules').is_dir()}))
    if result.returncode:
        sys.exit(result.returncode)
else:
    raise RuntimeError('Unsupported action')
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['clone', 'install-aux', 'bind-project', 'audit',
                                           'status', 'fix-rich', 'install-web'])
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
