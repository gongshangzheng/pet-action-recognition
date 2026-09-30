"""Assemble exactly the manifested local source from a base tar and local overlay.

Compatible with the existing Python 2.7 on the destination. No packages needed.
Archive paths are never extracted wholesale; each regular file is hash-checked.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import os
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = os.path.realpath(args.root)
    with tarfile.open(args.base, "r:gz") as base, tarfile.open(args.overlay, "r:gz") as overlay:
        manifest_bytes = overlay.extractfile(".deployment/source_manifest.json").read()
        manifest = json.loads(manifest_bytes)
        base_files = {}
        for member in base.getmembers():
            parts = member.name.split("/", 1)
            if member.isfile() and len(parts) == 2:
                base_files[parts[1]] = member
        overlay_files = {m.name: m for m in overlay.getmembers() if m.isfile()}
        installed = 0
        for record in manifest["files"]:
            name = record["path"]
            if name.startswith("/") or ".." in name.split("/") or "\\" in name:
                raise ValueError("Unsafe archive path: " + name)
            path = os.path.realpath(os.path.join(root, name))
            if not path.startswith(root + os.sep):
                raise ValueError("Path outside destination: " + name)
            if name in overlay_files:
                data = overlay.extractfile(overlay_files[name]).read()
            elif name in base_files:
                data = base.extractfile(base_files[name]).read()
            else:
                raise ValueError("Missing source: " + name)
            candidates = [data, data.replace(b"\r\n", b"\n"),
                          data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")]
            data = next((d for d in candidates if len(d) == record["bytes"]
                         and digest(d) == record["sha256"]), None)
            if data is None:
                raise ValueError("Source hash mismatch: " + name)
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            if os.path.exists(path):
                with open(path, "rb") as stream:
                    if digest(stream.read()) != record["sha256"]:
                        raise ValueError("Refusing to overwrite different existing file: " + name)
            else:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                     0o755 if name.endswith(".sh") else 0o644)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
            installed += 1
        manifest_path = os.path.join(root, ".deployment", "source_manifest.json")
        with open(manifest_path, "wb") as stream:
            stream.write(manifest_bytes)
    print(json.dumps({"installed_files": installed, "root": root,
                      "source_revision": manifest["source_revision"]}))


if __name__ == "__main__":
    main()
