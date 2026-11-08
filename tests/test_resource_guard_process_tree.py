from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".claude/skills/remote-ops/scripts/resource_guard.sh"


def test_tree_pids_includes_grandchildren(tmp_path):
    pid_file = tmp_path / "pids"
    process = subprocess.Popen(
        ["bash", "-c", "sleep 30 & child=$!; sleep 30 & grandchild=$!; echo \"$child $grandchild\" > \"$1\"; wait", "bash", str(pid_file)]
    )
    try:
        children = [int(pid) for pid in pid_file.read_text().split()]
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


def test_cpu_stat_parser_handles_spaces_in_process_name(tmp_path):
    stat_file = tmp_path / "stat"
    stat_file.write_text("123 (worker pool) S 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16\n")
    output = subprocess.check_output(
        [
            "bash",
            "-c",
            "sed 's/^.*) //' \"$1\" | awk '{print $12+$13}'",
            "bash",
            str(stat_file),
        ],
        text=True,
    ).strip()
    assert output == "27"
