#!/usr/bin/env python3
"""Aggregate read-only delivery checks for an article-note."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(label, command):
    print("==", label, "==")
    result = subprocess.run(command, text=True)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="article-note 交付前汇总检查")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--change", default="")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo = Path(args.repo_root).expanduser().resolve()
    skill_scripts = Path(__file__).resolve().parent
    workspace = Path(args.workspace).expanduser().resolve()
    note = Path(args.note).expanduser().resolve() if args.note else repo / "management" / "docs" / "notes" / (args.slug + ".md")
    failures = []
    failures.append(run("analysis", [sys.executable, str(skill_scripts / "validate-analysis.py"), "--workspace", str(workspace)]))
    failures.append(run("note", [sys.executable, str(skill_scripts / "validate-note.py"), "--note", str(note), "--docs-root", str(repo / "management" / "docs"), "--assets-root", str(repo / "management" / "docs" / "_assets")]))
    if args.change:
        failures.append(run("openspec", ["openspec", "validate", args.change]))
    if (repo / ".git").exists():
        result = subprocess.run(["git", "-C", str(repo), "diff", "--check"], text=True)
        print("== git diff --check ==")
        failures.append(result.returncode)
    print("delivery checks:", "FAILED" if any(failures) else "OK")
    return 1 if any(failures) else 0


if __name__ == "__main__":
    sys.exit(main())
