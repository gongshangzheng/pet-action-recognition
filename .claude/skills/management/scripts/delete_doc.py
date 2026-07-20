#!/usr/bin/env python3
"""Delete a wiki doc management/docs/{slug}.md.

Usage:
    python3 delete_doc.py --slug jwt-auth-guide
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mgmt_io


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="doc slug (filename without .md)")
    args = ap.parse_args()

    path = mgmt_io.doc_path(args.slug)
    if not path.exists():
        sys.exit(f"error: {mgmt_io.rel(path)} not found")
    path.unlink()
    print(f"✓ deleted doc {mgmt_io.rel(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
