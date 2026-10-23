#!/usr/bin/env python3
"""Inspect or fast-forward the migrated lab Git checkout from a local bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

from migrate_pet_final_to_lab import LOCAL_REPORT, ROOT, TARGET, STAGING, connect, remote_run, upload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'apply'])
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
        if args.action == 'apply':
            if substantial:
                raise RuntimeError('Remote worktree has substantive tracked changes; inspect first')
            # Restore only tracked files that differ by end-of-line whitespace. The original
            # migration manifest already verified their transferred content before this update.
            if changes:
                remote_run(client, 'git -C ' + shlex.quote(TARGET) + ' restore --worktree -- .')
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
                       + shlex.quote(remote_bundle) + ' main')
            remote_run(client, 'git -C ' + shlex.quote(TARGET) + ' merge --ff-only -q FETCH_HEAD')
            _, current, _ = remote_run(client, 'git -C ' + shlex.quote(TARGET) + ' rev-parse HEAD')
            if current.strip() != report['local_head']:
                raise RuntimeError('Remote Git HEAD did not reach local HEAD')
            report.update(applied=True, remote_head=current.strip(), bundle_sha256=digest)
            output = LOCAL_REPORT / 'git_sync.json'
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    main()
