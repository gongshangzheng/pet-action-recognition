#!/usr/bin/env python3
"""Finish the lab copy with existing checkpoints and public asset cache."""
from __future__ import annotations

import argparse
import json
import shlex

from migrate_pet_final_to_lab import connect


COPY_CHECKPOINTS = r'''
import hashlib
import json
from pathlib import Path
import shutil

source = Path('/home/wyy/pet-action-recognition/checkpoints')
target = Path('/home/wyy/pet-final/checkpoints')
if not source.is_dir() or not target.parent.is_dir():
    raise RuntimeError('Expected source or target project missing')
target.mkdir(exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

count = copied = total_bytes = 0
for file in sorted(source.rglob('*')):
    if not file.is_file() or file.is_symlink():
        continue
    relative = file.relative_to(source)
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(file, destination)
        copied += 1
    if destination.stat().st_size != file.stat().st_size or sha(destination) != sha(file):
        raise RuntimeError('Checkpoint differs: ' + str(relative))
    count += 1
    total_bytes += file.stat().st_size
report = {'source': str(source), 'target': str(target), 'files_verified': count,
          'files_copied': copied, 'bytes_verified': total_bytes}
output = Path('/home/wyy/pet-final/results/migration_lab/existing_checkpoints.json')
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
'''

START_ASSETS = r'''
import json
from pathlib import Path
import shutil
import subprocess

root = Path('/home/wyy/pet-final')
source = root / 'results/deployment/company_assets_20260930/manifest.json'
directory = root / 'results/migration_lab/public_assets'
directory.mkdir(parents=True, exist_ok=True)
manifest = directory / 'manifest.json'
if not manifest.exists():
    shutil.copy2(source, manifest)
elif manifest.read_bytes() != source.read_bytes():
    raise RuntimeError('Public asset manifest has changed')
log = directory / 'download.log'
pid = directory / 'download.pid'
if pid.exists():
    old = int(pid.read_text())
    if Path('/proc/' + str(old)).exists():
        raise RuntimeError('Public asset cache is already running')
command = ['/home/wyy/miniconda3/envs/pet/bin/python', str(root / 'scripts/cache_company_assets.py'),
           '--root', str(root), '--report-dir', 'results/migration_lab/public_assets',
           '--workers', '4', '--retry-failed']
with log.open('ab') as stream:
    process = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL,
                               stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
pid.write_text(str(process.pid) + '\n')
print(json.dumps({'pid': process.pid, 'log': str(log), 'manifest_entries':
                  len(json.loads(manifest.read_text())['assets'])}))
'''

ASSET_STATUS = r'''
import json
from pathlib import Path

directory = Path('/home/wyy/pet-final/results/migration_lab/public_assets')
status_file = directory / 'assets_status.json'
log = directory / 'download.log'
lines = log.read_text(errors='replace').splitlines() if log.exists() else []
status = json.loads(status_file.read_text()) if status_file.exists() else {}
print(json.dumps({'status': {key: status.get(key) for key in
                   ('verified', 'failed', 'total', 'bytes', 'discovery_errors')},
                  'finished': any('ASSET_CACHE_PASS_FINISHED' in line for line in lines[-20:]),
                  'log_tail': lines[-8:]}, ensure_ascii=False))
'''


def run(client, source: str, timeout: int) -> dict:
    _, stdout, stderr = client.exec_command('python3 -c ' + shlex.quote(source), timeout=timeout)
    code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', 'replace')
    error = stderr.read().decode('utf-8', 'replace')
    if code:
        raise RuntimeError(f'Remote action failed ({code}): {error[:2000]} {output[:1000]}')
    return json.loads(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['copy-checkpoints', 'start-assets', 'asset-status'])
    args = parser.parse_args()
    client = connect()
    try:
        source = {'copy-checkpoints': COPY_CHECKPOINTS, 'start-assets': START_ASSETS,
                  'asset-status': ASSET_STATUS}[args.action]
        print(json.dumps(run(client, source, 1800 if args.action == 'copy-checkpoints' else 120),
                         ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
