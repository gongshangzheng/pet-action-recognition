import contextlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
REMOTE_OPS = ROOT / ".claude/skills/remote-ops/scripts"


@pytest.mark.parametrize("preflight_rc", [2, 3])
def test_remote_run_preserves_preflight_rejection_and_does_not_start_command(preflight_rc):
    fixtures_root = ROOT / "results/tests/remote-run-preflight-exit-code"
    fixtures_root.mkdir(parents=True, exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix=f"rc-{preflight_rc}-", dir=fixtures_root))
    try:
        bin_dir = fixture_dir / "bin"
        bin_dir.mkdir()
        (fixture_dir / "remote_run.sh").symlink_to(REMOTE_OPS / "remote_run.sh")
        (fixture_dir / "_remote_common.sh").symlink_to(REMOTE_OPS / "_remote_common.sh")
        marker = fixture_dir / "task-started"
        ssh_marker = fixture_dir / "ssh-called"

        preflight = fixture_dir / "preflight.sh"
        preflight.write_text(f"#!/bin/bash\nexit {preflight_rc}\n")
        preflight.chmod(0o755)

        ssh_stub = bin_dir / "ssh"
        ssh_stub.write_text(f"#!/bin/bash\nprintf called > {str(ssh_marker)!r}\nexit 0\n")
        ssh_stub.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
        result = subprocess.run(
            ["bash", str(fixture_dir / "remote_run.sh"), "--", "bash", "-c", f"touch {marker}"],
            cwd=fixture_dir,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
        )

        assert result.returncode == preflight_rc, result.stderr
        assert not marker.exists(), "preflight rejection must prevent the task command"
        assert not ssh_marker.exists(), "preflight rejection must prevent SSH"
        assert "预检未通过" in result.stderr
    finally:
        shutil.rmtree(fixture_dir)
        with contextlib.suppress(OSError):
            fixtures_root.rmdir()
