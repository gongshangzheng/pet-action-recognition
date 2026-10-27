"""Install/audit auxiliary dependencies in the existing environment; never run a model."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def versions():
    return {canonical(d.metadata["Name"]): d.version for d in metadata.distributions()
            if d.metadata.get("Name")}


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def native_snapshot():
    site = Path(metadata.distribution("torch").locate_file(""))
    patterns = {"cv2": "cv2/cv2*.so", "mmcv": "mmcv/_ext*.so",
                "torch": "torch/_C*.so", "numpy": "numpy/core/_multiarray_umath*.so"}
    result = {}
    for name, pattern in patterns.items():
        paths = list(site.glob(pattern))
        if len(paths) != 1:
            raise RuntimeError("Ambiguous native module: " + name)
        result[name] = dict(path=str(paths[0]), sha256=sha_file(paths[0]))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    root = args.root.resolve()
    if Path(sys.prefix).resolve() != (root / ".runtime/pet").resolve():
        raise RuntimeError("Use the existing .runtime/pet/bin/python")
    out = root / "results/deployment/company_auxiliary_20260930"
    wheels = root / ".runtime/cache/auxiliary-wheels"
    base_wheels = root / ".runtime/cache/wheels"
    out.mkdir(parents=True, exist_ok=True)
    wheels.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    env = os.environ.copy()
    env.update(PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple",
               PIP_CACHE_DIR=str(root / ".runtime/cache/pip"), PIP_DEFAULT_TIMEOUT="180",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONNOUSERSITE="1",
               TMPDIR=str(root / ".runtime/tmp"), YOLO_AUTOINSTALL="false",
               YOLO_CONFIG_DIR=str(root / ".runtime/cache/ultralytics"),
               U2NET_HOME=str(root / ".runtime/cache/rembg-models"),
               NUMBA_CACHE_DIR=str(root / ".runtime/cache/numba"),
               MPLCONFIGDIR=str(root / ".runtime/cache/matplotlib"),
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    env.pop("PIP_EXTRA_INDEX_URL", None)
    os.environ.update(env)
    pip = [sys.executable, "-m", "pip"]

    def run(argv, log_name=None, allow_failure=False):
        print("RUN " + " ".join(str(x) for x in argv), flush=True)
        if log_name:
            with (out / log_name).open("w", encoding="utf-8") as f:
                result = subprocess.run(argv, env=env, stdout=f, stderr=subprocess.STDOUT)
        else:
            result = subprocess.run(argv, env=env)
        if result.returncode and not allow_failure:
            raise RuntimeError("Command failed; see " + str(log_name or "install.log"))
        return result.returncode

    baseline_path = out / "before.json"
    if not baseline_path.exists():
        before = dict(versions=versions(), native=native_snapshot())
        matches = []
        for candidate in base_wheels.glob("opencv*.whl"):
            with zipfile.ZipFile(candidate) as z:
                for name in z.namelist():
                    if name.startswith("cv2/") and name.endswith(".so"):
                        if hashlib.sha256(z.read(name)).hexdigest() == before["native"]["cv2"]["sha256"]:
                            matches.append(str(candidate))
        if not matches:
            raise RuntimeError("Original OpenCV provider wheel is not cached")
        before["opencv_provider_wheel"] = matches[0]
        baseline_path.write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8")
    before = json.loads(baseline_path.read_text())
    constraints = out / "preserve-existing.txt"
    constraints.write_text("".join(name + "==" + version + "\n"
                                   for name, version in sorted(before["versions"].items())
                                   if name != "protobuf"), encoding="utf-8")

    if not args.audit_only:
        req = root / "configs/company_auxiliary_requirements.txt"
        plan = out / "install-plan.json"
        run(pip + ["install", "--dry-run", "--report", str(plan), "--only-binary=:all:",
                   "--retries", "12", "-c", str(constraints), "-r", str(req)])
        proposed = json.loads(plan.read_text())["install"]
        for item in proposed:
            name = canonical(item["metadata"]["name"])
            version = item["metadata"]["version"]
            previous = before["versions"].get(name)
            if previous and previous != version and not (name == "protobuf" and version == "4.25.4"):
                raise RuntimeError("Unapproved version change: " + name)
        pins = [item["metadata"]["name"] + "==" + item["metadata"]["version"] for item in proposed]
        if pins:
            run(pip + ["download", "--only-binary=:all:", "--no-deps", "--retries", "12",
                       "--resume-retries", "20", "-d", str(wheels)] + pins)
        try:
            run(pip + ["install", "--no-index", "--find-links", str(wheels),
                       "--find-links", str(base_wheels), "-c", str(constraints), "-r", str(req),
                       "--report", str(out / "installed.json")])
        finally:
            # Headless/core/contrib metadata share cv2; restore the exact original binary provider.
            if native_snapshot()["cv2"]["sha256"] != before["native"]["cv2"]["sha256"]:
                run(pip + ["install", "--no-index", "--no-deps", "--force-reinstall",
                           before["opencv_provider_wheel"]])

    checks = []
    after = dict(versions=versions(), native=native_snapshot())
    (out / "after.json").write_text(json.dumps(after, indent=2) + "\n", encoding="utf-8")
    changes = {name: dict(before=version, after=after["versions"].get(name))
               for name, version in before["versions"].items()
               if after["versions"].get(name) != version}
    unexpected = {name: change for name, change in changes.items()
                  if not (name == "protobuf" and change["after"] == "4.25.4")}
    checks.append(dict(name="existing_version_constraints", passed=not unexpected, detail=changes))
    checks.append(dict(name="native_module_hashes_unchanged", passed=after["native"] == before["native"]))

    modules = ["ultralytics", "ultralytics.nn.tasks", "torchvision.models.segmentation",
               "torchvision.models.mobilenetv3", "torchvision.models.shufflenetv2",
               "rembg", "pymatting", "numba", "albumentations", "timm",
               "pytorch_lightning", "torchmetrics", "ruptures", "hmmlearn",
               "pytorch_tcn", "h5py", "lap", "onnx", "onnxruntime",
               "onnxruntime.quantization", "onnxsim", "onnxoptimizer", "rknn.api"]
    for module in modules:
        code = "import importlib; m=importlib.import_module(" + repr(module) + "); print(m.__file__)"
        name = "import_" + module.replace(".", "_") + ".log"
        rc = run([sys.executable, "-c", code], name, allow_failure=True)
        checks.append(dict(name="import:" + module, passed=rc == 0, log=name))

    rknn_hits = []
    package_root = Path(metadata.distribution("rknn-toolkit2").locate_file("rknn"))
    for path in package_root.rglob("*"):
        if path.is_file() and path.suffix in (".py", ".so") and b"rv1126b" in path.read_bytes().lower():
            rknn_hits.append(str(path.relative_to(package_root)))
            break
    checks.append(dict(name="rknn_rv1126b_shipped_reference", passed=bool(rknn_hits), files=rknn_hits))
    core_out = out / "core_recheck"
    core_rc = run([sys.executable, str(root / "scripts/checks/audit_company_runtime.py"),
                   "--root", str(root), "--out", str(core_out)], "core_recheck.log", allow_failure=True)
    checks.append(dict(name="original_action_runtime_recheck", passed=core_rc == 0,
                       report="core_recheck/runtime_audit.json"))

    run(pip + ["freeze"], "pip-freeze.txt")
    run(pip + ["list", "--format=json"], "packages.json")
    with (out / "wheels.sha256").open("w", encoding="utf-8") as f:
        for path in sorted(wheels.glob("*.whl")):
            f.write(sha_file(path) + "  " + str(path) + "\n")
    result = dict(status="passed" if all(c["passed"] for c in checks) else "failed",
                  environment=str(Path(sys.prefix)), checks=checks, version_changes=changes,
                  added={n: v for n, v in after["versions"].items() if n not in before["versions"]},
                  model_constructed=False, training_executed=False, forward_executed=False,
                  weights_downloaded=False, dataset_processed=False, rknn_build_executed=False,
                  rknn_simulator_executed=False, board_speed_measured=False,
                  onnx_runtime_backend="CPU; does not replace existing torch CUDA",
                  known_core_warning="Decord 0.6.0 internal cp36 wheel tag; see core recheck report")
    (out / "auxiliary_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
    if result["status"] != "passed":
        raise SystemExit(1)
    print("AUXILIARY_DEPENDENCIES_DONE", flush=True)


if __name__ == "__main__":
    main()
