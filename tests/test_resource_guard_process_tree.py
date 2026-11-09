from pathlib import Path
import shutil
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".claude/skills/remote-ops/scripts/resource_guard.sh"


def _wait_for_pid_file(pid_file: Path, timeout_s: float = 10.0) -> str:
    """Wait until the writer has flushed the pid list.

    The guard only sees a root pid; if the test reads the file first it fails
    before the guard is invoked, which proves nothing about the guard.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pid_file.exists():
            content = pid_file.read_text().strip()
            if len(content.split()) == 2:
                return content
        time.sleep(0.02)
    raise AssertionError(f"writer did not write {pid_file} in {timeout_s}s")


def test_tree_pids_includes_grandchildren(tmp_path):
    pid_file = tmp_path / "pids"
    process = subprocess.Popen(
        ["bash", "-c", "sleep 30 & child=$!; sleep 30 & grandchild=$!; echo \"$child $grandchild\" > \"$1\"; wait", "bash", str(pid_file)]
    )
    try:
        children = [int(pid) for pid in _wait_for_pid_file(pid_file).split()]
        result = subprocess.run(
            ["bash", str(GUARD), "tree-pids", str(process.pid)],
            check=True,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        found = {int(pid) for pid in result.stdout.split()}
        assert {process.pid, *children} <= found
    finally:
        process.terminate()
        subprocess.run(["pkill", "-P", str(process.pid)], check=False)
        process.wait(timeout=5)


@pytest.mark.skipif(
    not Path("/proc/self/stat").exists(),
    reason="resource_guard parses /proc/<pid>/stat; needs Linux",
)
def test_cpu_accounting_survives_spaces_in_process_name(tmp_path):
    """A comm field containing spaces must not shift the utime/stime field offsets.

    The guard strips everything up to ") " before summing utime+stime. A process
    named "worker pool" only gets its CPU accounted correctly if that stripping
    happens; otherwise the tree never breaches the limit and the run is not killed.
    """
    burner = tmp_path / "worker pool"
    shutil.copy("/bin/sh", burner)
    log_file = tmp_path / "guard.log"

    result = subprocess.run(
        [
            "bash", str(GUARD), "run",
            "--max-cpu-pct", "20",
            "--interval", "1",
            "--timeout-s", "25",
            "--log", str(log_file),
            "--", str(burner), "-c", "while :; do :; done",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 4, (result.returncode, result.stdout, result.stderr)
    log = log_file.read_text()
    assert "CAP BREACH" in log
    assert "cpu" in log.lower()
