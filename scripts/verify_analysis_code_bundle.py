"""Verify deployed source files using only the Python 2.7/3 standard library."""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = os.path.realpath(args.root)
    with open(os.path.join(root, ".deployment", "source_manifest.json"), "rb") as stream:
        manifest = json.load(stream)
    failures = []
    for record in manifest["files"]:
        relative = record["path"]
        path = os.path.realpath(os.path.join(root, relative))
        if not path.startswith(root + os.sep) or not os.path.isfile(path):
            failures.append({"path": relative, "reason": "missing or outside root"})
            continue
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1048576), b""):
                digest.update(chunk)
        if os.path.getsize(path) != record["bytes"] or digest.hexdigest() != record["sha256"]:
            failures.append({"path": relative, "reason": "size or hash mismatch"})
    html_files = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".deployment"]
        html_files.extend(os.path.relpath(os.path.join(current, f), root)
                          for f in files if f.lower().endswith((".html", ".htm")))
    result = {"status": "passed" if not failures and not html_files else "failed",
              "verified_files": len(manifest["files"]), "failures": failures,
              "html_files": html_files, "source_revision": manifest["source_revision"],
              "root": root, "runtime_installed_or_tested": False}
    with open(os.path.join(root, ".deployment", "verification.json"), "w") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
