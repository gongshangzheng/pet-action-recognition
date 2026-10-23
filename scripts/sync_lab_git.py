#!/usr/bin/env python3
"""Inspect or safely copy post-migration code changes to the lab project."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

from migrate_pet_final_to_lab import LOCAL_REPORT, ROOT, TARGET, STAGING, connect, remote_run, upload, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'files'])
    args = parser.parse_args()
    client = connect()
    try:
        _, head, _ = remote_run(client, 'git -C ' + shlex.quote(TARGET) + ' rev-parse HEAD')
        _, changed, _ = remote_run(client, 'git -C ' + shlex.quote(TARGET)
                                   + ' diff --name-only')
        _, substantial, _ = remote_run(client, 'git -C ' + shlex.quote(TARGET)
                                       + ' diff --ignore-cr-at-eol --name-only')
        changes = changed.splitlines()
        substantive = substantial.splitlines()
        report = {'remote_head': head.strip(), 'local_head': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'remote_tracked_changes': len(changes), 'remote_substantive_changes': len(substantive),
            'changed_sample': changes[:30], 'substantive_sample': substantive[:30]}
        if args.action == 'files':
            source_manifest = json.loads((LOCAL_REPORT / 'manifest.json').read_text(encoding='utf-8'))
            original = {entry['path']: entry['sha256'] for entry in source_manifest['files']}
            updated = subprocess.check_output(['git', 'diff', '--name-only', head.strip(),
                                               'HEAD'], cwd=ROOT, text=True).splitlines()
            if not updated:
                raise RuntimeError('No post-migration changes to sync')
            sftp = client.open_sftp()
            try:
                for relative in updated:
                    local_file = ROOT / relative
                    if not local_file.is_file():
                        raise RuntimeError('Deleted or non-file update requires separate handling: ' + relative)
                    remote_file = TARGET + '/' + relative.replace('\\', '/')
                    status, current, _ = remote_run(client, 'test -f ' + shlex.quote(remote_file)
                                                    + ' && sha256sum ' + shlex.quote(remote_file), checked=False)
                    if status == 0:
                        if current.split()[0] == sha256_file(local_file):
                            continue
                        if relative not in original or current.split()[0] != original[relative]:
                            raise RuntimeError('Remote update path differs from original manifest: ' + relative)
                        replace = True
                    else:
                        replace = False
                    upload(sftp, local_file, remote_file, local_file.stat().st_size,
                           replace_pristine_clone_file=replace)
            finally:
                sftp.close()
            bundle = LOCAL_REPORT / 'final_history.bundle'
            subprocess.run(['git', 'bundle', 'create', str(bundle), '--all'], cwd=ROOT, check=True)
            digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            remote_bundle = STAGING + '/final_history_' + digest[:16] + '.bundle'
            sftp = client.open_sftp()
            try:
                upload(sftp, bundle, remote_bundle, bundle.stat().st_size)
            finally:
                sftp.close()
            remote_run(client, 'git -C ' + shlex.quote(TARGET) + ' fetch -q '
                       + shlex.quote(remote_bundle) + ' main:refs/heads/migration-final')
            _, branch, _ = remote_run(client, 'git -C ' + shlex.quote(TARGET)
                                      + ' rev-parse refs/heads/migration-final')
            if branch.strip() != report['local_head']:
                raise RuntimeError('Remote migration-final branch did not reach local HEAD')
            report.update(applied=True, files_updated=updated, migration_final_head=branch.strip(),
                          bundle_sha256=digest)
            output = LOCAL_REPORT / 'git_sync.json'
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
