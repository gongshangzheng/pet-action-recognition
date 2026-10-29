#!/usr/bin/env python3
"""Pre-run audit for code that is about to run on the remote machine.

Two halves, because a heuristic scan alone is not evidence:

* ``audit``  -- static scan for patterns that commonly turn into runaway memory
  (accumulating frames, whole-sequence loads, materialising expanded views,
  autograd graphs kept alive, unbounded loops, uncapped pools). Findings are
  heuristic: a report with no findings does not prove the code is safe.
* ``smoke``  -- run the command at a reduced scale under a hard RSS cap and
  measure peak RSS, then report growth per unit of scale. This is the part that
  actually demonstrates the code does not blow up; the audit only tells you
  where to look.

Usage:
    python3 code_audit.py audit scripts/bench/x.py [more.py ...] [--strict]
    python3 code_audit.py smoke --cap-mb 2000 --timeout-s 900 -- \
        python3 scripts/bench/x.py --frames {n} --out /tmp/smoke

Exit codes: 0 ok / 1 high-severity finding (audit) / 4 exceeded the RSS cap
            / 5 command failed / 2 usage error
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

AUDIO_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".wav", ".flac"}
ACCUMULATOR_HINTS = ("frame", "image", "img", "patch", "sample", "result", "rows", "record", "batch", "crop", "tensor")
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    severity: str
    message: str

    def as_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "rule": self.rule,
                "severity": self.severity, "message": self.message}


class Auditor(ast.NodeVisitor):
    """Walks one function body at a time so loop context is available."""

    def __init__(self, path: str, source: str) -> None:
        self.path = path
        self.source = source
        self.lines = source.splitlines()
        self.findings: list[Finding] = []
        self._loop_stack: list[ast.AST] = []
        self._func_stack: list[ast.AST] = []

    # ------------------------------------------------------------------ utils
    def add(self, node: ast.AST, rule: str, severity: str, message: str) -> None:
        self.findings.append(Finding(self.path, getattr(node, "lineno", 0), rule, severity, message))

    def _loop_body_has(self, predicate) -> bool:
        for loop in self._loop_stack:
            for child in ast.walk(loop):
                if predicate(child):
                    return True
        return False

    def _func_source(self) -> str:
        if not self._func_stack:
            return ""
        fn = self._func_stack[-1]
        start = getattr(fn, "lineno", 1) - 1
        end = getattr(fn, "end_lineno", len(self.lines)) or len(self.lines)
        return "\n".join(self.lines[start:end])

    @staticmethod
    def _name_of(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Call):
            return Auditor._name_of(node.func)
        return ""

    # -------------------------------------------------------------- visitors
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._func_stack.append(node)
        self.generic_visit(node)
        self._func_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_For(self, node: ast.For) -> None:
        self._loop_stack.append(node)
        self._check_iteration_over_sequence(node)
        self.generic_visit(node)
        self._loop_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        self._loop_stack.append(node)
        unconditional = isinstance(node.test, ast.Constant) and node.test.value is True
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
        has_limit = any(isinstance(n, ast.Compare) for n in ast.walk(node.test))
        if unconditional and not has_break and not has_limit:
            self.add(node, "C001", "high",
                     "`while True` without a break or a limit condition can accumulate memory forever")
        self.generic_visit(node)
        self._loop_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = self._name_of(node)
        in_loop = bool(self._loop_stack)

        if name == "append" and in_loop:
            self._check_append(node)
        if name in {"cat", "concatenate", "stack", "vstack", "hstack"} and in_loop:
            self.add(node, "C006", "high",
                     "grows a tensor/array by concatenation inside a loop; preallocate or stream to disk")
        if name in {"zeros", "ones", "empty", "full", "rand", "randn"} and node.args:
            self._check_large_allocation(node)
        if name == "contiguous" and isinstance(node.func, ast.Attribute):
            if self._name_of(node.func.value) == "expand":
                self.add(node, "C010", "medium",
                         "`.expand(...).contiguous()` materialises a full copy; check the shape product first")
        if name in {"load", "load_state_dict", "from_pretrained"} and in_loop:
            self.add(node, "C011", "medium",
                     "loads a checkpoint inside a loop; cache it outside unless the loop is over models")
        if name in {"Pool", "ThreadPool", "ThreadPoolExecutor", "ProcessPoolExecutor"}:
            has_size = any(k.arg in {"processes", "max_workers"} for k in node.keywords) or len(node.args) > 0
            if not has_size:
                self.add(node, "C012", "high",
                         "worker pool without an explicit size can fork one worker per core (or more)")
        if name in {"VideoCapture", "imread", "Image"} and in_loop:
            self.add(node, "C013", "low",
                     "media decode inside a loop; confirm frames are not retained and there is a frame limit")

        # forward pass without no_grad / inference_mode in the enclosing function
        if name in {"forward", "__call__", "predict", "infer"} or name in {"model", "net", "self"}:
            pass
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.generic_visit(node)

    # --------------------------------------------------------------- helpers
    def _check_append(self, node: ast.Call) -> None:
        if not node.args:
            return
        value = node.args[0]
        value_name = self._name_of(value)
        stored = isinstance(value, ast.Call) and self._name_of(value) in {"array", "asarray", "tensor", "imread", "cvtColor"}
        if value_name in ACCUMULATOR_HINTS or stored:
            has_limit = self._loop_has_limit()
            severity = "high" if not has_limit else "medium"
            note = "no frame/sample limit found in the loop" if not has_limit else "a limit exists; verify it is applied before the append"
            self.add(node, "C002", severity,
                     f"accumulates `{value_name or 'decoded value'}` across iterations ({note}); "
                     "stream to disk or cap the collection")

    def _loop_has_limit(self) -> bool:
        for loop in self._loop_stack:
            for child in ast.walk(loop):
                if isinstance(child, ast.Call) and self._name_of(child) in {"min", "islice", "range"}:
                    for a in list(child.args) + [k.value for k in child.keywords]:
                        if isinstance(a, ast.Constant) and isinstance(a.value, int) and a.value <= 100000:
                            if self._name_of(child) == "range" and a.value <= 10000:
                                return True
                    if self._name_of(child) in {"min", "islice"}:
                        return True
                # `if i >= limit: break` is the normal cap idiom; accept any break
                # guarded by a comparison, whatever the names involved.
                if isinstance(child, ast.If):
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(child))
                    has_compare = any(
                        isinstance(n, ast.Compare) for n in ast.walk(child.test)
                    )
                    if has_break and has_compare:
                        return True
        return False

    def _check_large_allocation(self, node: ast.Call) -> None:
        shape = None
        if isinstance(node.func, ast.Attribute) and node.args and isinstance(node.args[0], (ast.Tuple, ast.List)):
            shape = node.args[0]
        if shape is None:
            return
        product = 1
        symbolic = False
        for dim in shape.elts:
            if isinstance(dim, ast.Constant) and isinstance(dim.value, int):
                product *= max(dim.value, 1)
            elif isinstance(dim, ast.BinOp) and all(
                isinstance(x, ast.Constant) and isinstance(x.value, int) for x in (dim.left, dim.right)
            ):
                product *= max(int(dim.left.value) * int(dim.right.value), 1)  # type: ignore[attr-defined]
            else:
                symbolic = True
        # Small dtypes make the same element count harmless: 50M uint8 pixels is
        # 50 MB, while 50M float32 is 200 MB before intermediates.
        dtype_text = " ".join(ast.dump(k.value) for k in node.keywords if k.arg == "dtype")
        small_dtype = any(tag in dtype_text for tag in ("uint8", "int8", "bool"))
        limit = 500_000_000 if small_dtype else 50_000_000
        if product >= limit or (symbolic and product >= 1_000_000):
            self.add(node, "C003", "high",
                     f"allocates about {product:,} elements from literal dimensions"
                     + (" and symbolic dimensions" if symbolic else "")
                     + "; confirm this is bounded by an explicit frame/batch cap")
        elif symbolic:
            self.add(node, "C007", "medium",
                     "allocation sized by runtime values; check the caller caps frames/batch "
                     "before this is reached at full scale")

    def visit_Assign(self, node: ast.Assign) -> None:
        # list comprehension over a sequence without a cap is the other way to load everything
        value = node.value
        if isinstance(value, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and isinstance(value.generators[0].iter, ast.Call):
            call = value.generators[0].iter
            if self._name_of(call) in {"glob", "listdir", "walk", "iglob"}:
                self.add(node, "C004", "medium",
                         "comprehension over a filesystem listing builds every item at once; cap it or iterate lazily")
        self.generic_visit(node)

    def _check_iteration_over_sequence(self, node: ast.For) -> None:
        body_has_read = any(
            isinstance(n, ast.Call) and self._name_of(n) in {"imread", "read", "load", "open", "VideoCapture"}
            for n in ast.walk(node)
        )
        iter_name = self._name_of(node.iter)
        if body_has_read and iter_name in {"range", "enumerate", "iter"}:
            parent = self._name_of(node.iter.args[0]) if isinstance(node.iter, ast.Call) and node.iter.args else ""
            if parent in {"len", "self"}:
                self.add(node, "C005", "medium",
                         "iterates a full sequence while decoding media; add an explicit frame/segment cap")


def audit_file(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [Finding(str(path), exc.lineno or 0, "C000", "high", f"syntax error: {exc.msg}")]
    auditor = Auditor(str(path), source)

    # Function-level checks that need the whole body, not a single node.
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body_src = ast.get_source_segment(source, fn) or ""
        has_loop = any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(fn))
        forward = re.search(r"\b(model|net|pipeline|synthesis|encoder|policy)\s*\(", body_src) is not None
        guarded = ("no_grad" in body_src) or ("inference_mode" in body_src)
        if has_loop and forward and not guarded:
            auditor.add(fn, "C020", "high",
                        f"`{fn.name}` runs a forward pass inside a loop without torch.no_grad()/inference_mode; "
                        "the autograd graph accumulates per iteration")
        retains = re.search(r"\.append\(\s*(loss|out|output|logits|feat\w*)\s*\)", body_src)
        if retains and ".detach()" not in body_src and not guarded:
            auditor.add(fn, "C021", "high",
                        f"`{fn.name}` retains tensors with their autograd graph across iterations")
    auditor.visit(tree)
    return auditor.findings


def run_smoke(cmd: list[str], cap_mb: int, timeout_s: int, scales: tuple[int, int]) -> int:
    """Run the command twice at small scales and report peak RSS growth."""
    if "{n}" not in " ".join(cmd):
        print("smoke: command must contain {n} so the scale can be substituted", file=sys.stderr)
        return 2
    results = []
    for n in scales:
        argv = [part.replace("{n}", str(n)) for part in cmd]
        print(f"== smoke n={n}: {' '.join(argv)}")
        started = time.time()
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        peak_kb = 0
        deadline = started + timeout_s
        try:
            while proc.poll() is None:
                rss = _tree_rss_kb(proc.pid)
                peak_kb = max(peak_kb, rss)
                if peak_kb > cap_mb * 1024:
                    print(f"   exceeded cap: {peak_kb // 1024} MB > {cap_mb} MB -> terminating")
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
                if time.time() > deadline:
                    print(f"   timeout after {timeout_s}s -> terminating")
                    proc.terminate()
                    break
                time.sleep(0.1)
        finally:
            if proc.poll() is None:
                proc.terminate()
            try:
                out = proc.communicate(timeout=10)[0]
            except subprocess.TimeoutExpired:
                proc.kill()
                out = ""
        elapsed = time.time() - started
        results.append({"n": n, "peak_mb": peak_kb // 1024, "seconds": round(elapsed, 1), "rc": proc.returncode})
        print(f"   rc={proc.returncode} peak={peak_kb // 1024} MB elapsed={elapsed:.1f}s")
        if out:
            tail = "\n".join(out.strip().splitlines()[-5:])
            print("   output tail:\n" + "\n".join("     " + ln for ln in tail.splitlines()))
        if proc.returncode not in (0, None) and peak_kb > cap_mb * 1024:
            print(json.dumps({"smoke": results}, indent=2))
            return 4
        if proc.returncode not in (0,):
            print(json.dumps({"smoke": results}, indent=2))
            return 5

    if len(results) == 2:
        (a, b) = results
        per_unit = (b["peak_mb"] - a["peak_mb"]) / max(b["n"] - a["n"], 1)
        print(f"== growth: {per_unit:+.1f} MB per unit of scale "
              f"({a['n']} -> {b['n']}: {a['peak_mb']} -> {b['peak_mb']} MB)")
        if per_unit > 0:
            print(f"   at the target scale this extrapolates to roughly "
                  f"{b['peak_mb'] + per_unit * (max(b['n'], 1) * 100 - b['n']):,} MB at 100x — "
                  "check that against the machine's free memory")
    print(json.dumps({"smoke": results}, indent=2))
    return 0


def _tree_rss_kb(pid: int) -> int:
    """RSS of a process and its children (Linux /proc; falls back to ps)."""
    total = 0
    proc_root = Path("/proc")
    if proc_root.is_dir():
        parents = {}
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                stat = (entry / "stat").read_text()
            except OSError:
                continue
            parts = stat.rsplit(")", 1)[-1].split()
            parents[int(entry.name)] = int(parts[1]) if len(parts) > 1 else 0
        wanted = {pid}
        changed = True
        while changed:
            changed = False
            for child, parent in parents.items():
                if parent in wanted and child not in wanted:
                    wanted.add(child)
                    changed = True
        for candidate in wanted:
            try:
                status = (proc_root / str(candidate) / "status").read_text()
            except OSError:
                continue
            for line in status.splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1])
    else:
        ps = shutil.which("ps")
        if ps:
            out = subprocess.run([ps, "-o", "rss=", "-p", str(pid)], capture_output=True, text=True).stdout
            total = int(out.strip() or 0)
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="static scan for runaway-memory patterns")
    audit.add_argument("paths", nargs="+", type=Path)
    audit.add_argument("--strict", action="store_true", help="treat medium findings as failures too")
    audit.add_argument("--json", dest="json_path", type=Path)

    smoke = sub.add_parser("smoke", help="run at reduced scale under an RSS cap")
    smoke.add_argument("--cap-mb", type=int, default=2000)
    smoke.add_argument("--timeout-s", type=int, default=900)
    smoke.add_argument("--scales", type=int, nargs=2, default=(1, 2))
    smoke.add_argument("cmd", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)

    if args.command == "audit":
        findings: list[Finding] = []
        for path in args.paths:
            findings.extend(audit_file(path))
        findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.path, f.line))
        if not findings:
            print("audit: no matching patterns (absence of findings is not proof of safety)")
        for f in findings:
            print(f"{f.severity:6s} {f.path}:{f.line} {f.rule} {f.message}")
        high = [f for f in findings if f.severity == "high"]
        medium = [f for f in findings if f.severity == "medium"]
        print(f"\naudit: {len(high)} high, {len(medium)} medium, {len(findings) - len(high) - len(medium)} low")
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(json.dumps({"findings": [f.as_dict() for f in findings]}, indent=2))
        if high or (args.strict and medium):
            return 1
        return 0

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("smoke: no command given", file=sys.stderr)
        return 2
    return run_smoke(cmd, args.cap_mb, args.timeout_s, tuple(args.scales))


if __name__ == "__main__":
    raise SystemExit(main())
