"""Check installed action-recognition dependencies without executing any model."""
from __future__ import annotations

import argparse
import ast
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.relative_to(root)
    out.mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = os.pathsep.join([str(root), str(root / "models/mmaction2")])
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["MPLCONFIGDIR"] = str(root / ".runtime/cache/matplotlib")
    checks = []

    def check(name, action):
        try:
            detail = action()
            checks.append(dict(name=name, status="passed", detail=detail))
        except Exception:
            checks.append(dict(name=name, status="failed", error=traceback.format_exc()))
        print(name + ": " + checks[-1]["status"], flush=True)

    def command(argv, log_name):
        result = subprocess.run(argv, cwd=root, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=180)
        (out / log_name).write_text(result.stdout, encoding="utf-8")
        if result.returncode:
            raise RuntimeError("Command exited %s; see %s" % (result.returncode, log_name))
        return dict(returncode=result.returncode, log=log_name)

    def pip_check():
        result = subprocess.run([sys.executable, "-m", "pip", "check"], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        (out / "pip-check.txt").write_text(result.stdout, encoding="utf-8")
        if result.returncode == 0:
            return dict(returncode=0, log="pip-check.txt")
        expected = "decord 0.6.0 is not supported on this platform"
        wheel = importlib.metadata.distribution("decord").read_text("WHEEL") or ""
        if (result.returncode == 1 and result.stdout.strip() == expected
                and "Tag: cp36-cp36m-manylinux2010_x86_64" in wheel):
            import decord
            if decord.__version__ != "0.6.0":
                raise RuntimeError("Unexpected Decord version")
            return dict(returncode=1, log="pip-check.txt", warning=expected,
                        explanation="Official py3 wheel has an internal cp36 tag; ctypes/native library import passed. Video decoding was not executed.",
                        wheel_metadata=wheel, dependency_version_conflicts=False)
        raise RuntimeError("Unresolved dependency check: " + result.stdout)

    check("pip_check", pip_check)
    modules = ["torch", "torchvision", "numpy", "mmcv", "mmcv._ext", "mmcv.ops",
               "mmengine", "mmaction", "mmaction.apis", "mmdet", "mmdet.apis",
               "cv2", "decord", "av", "scipy", "sklearn", "pandas",
               "imageio_ffmpeg", "moviepy.editor", "pytorchvideo.transforms", "lmdb",
               "tensorboard", "fastapi",
               "scripts.train_model", "scripts.inference", "scripts.run_test",
               "scripts._infer", "configs.hooks.optimizer_checkpoint_hook"]
    for name in modules:
        check("import:" + name, lambda name=name: str(importlib.import_module(name).__file__))

    def cuda_visibility():
        import torch
        info = dict(available=torch.cuda.is_available(), count=torch.cuda.device_count(),
                    torch_cuda=torch.version.cuda, cudnn=torch.backends.cudnn.version(),
                    compiled_arches=torch.cuda.get_arch_list())
        if not info["available"] or not info["count"]:
            raise RuntimeError("No CUDA device visible: " + repr(info))
        return info

    check("cuda_discovery_no_computation", cuda_visibility)

    def ffmpeg_version():
        from imageio_ffmpeg import get_ffmpeg_exe
        return command([get_ffmpeg_exe(), "-version"], "ffmpeg-version.txt")

    check("ffmpeg_version", ffmpeg_version)

    def register_modules():
        from mmaction.utils import register_all_modules
        from mmdet.utils import register_all_modules as register_mmdet
        register_mmdet(init_default_scope=False)
        register_all_modules()
        return "Imported and registered classes only; no model was built."

    check("model_class_registration_no_build", register_modules)

    registry = []
    tree = ast.parse((root / "server/routers/training.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
                                               t.id == "_MMACTION2_REGISTRY" for t in node.targets):
            registry = ast.literal_eval(node.value)
            break

    def parse_config(path):
        from mmengine.config import Config
        cfg = Config.fromfile(str(path))
        def inspect_options(value):
            if isinstance(value, dict):
                if value.get("type") == "PytorchVideoWrapper":
                    transforms = importlib.import_module("pytorchvideo.transforms")
                    if not hasattr(transforms, value["op"]):
                        raise RuntimeError("Missing video augmentation: " + value["op"])
                for child in value.values():
                    inspect_options(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    inspect_options(child)
        inspect_options(cfg.to_dict())
        return dict(path=str(path.relative_to(root)), model_type=cfg.get("model", {}).get("type"),
                    has_train_dataloader="train_dataloader" in cfg,
                    has_test_dataloader="test_dataloader" in cfg,
                    dataset_and_checkpoint_existence_checked=False)

    seen = set()
    for item in registry:
        value = item.get("mmaction2_config")
        if not value:
            continue
        path = root / value
        if not path.is_file():
            path = root / "models/mmaction2" / value
        seen.add(path)
        check("config:" + item["id"], lambda path=path: parse_config(path))
    for path in sorted((root / "configs").glob("*.py")):
        if path not in seen:
            check("config:" + path.name, lambda path=path: parse_config(path))

    for relative in ["scripts/train_model.py", "scripts/inference.py", "scripts/run_test.py",
                     "models/mmaction2/tools/train.py", "models/mmaction2/tools/test.py"]:
        check("cli_help:" + relative,
              lambda relative=relative: command([sys.executable, str(root / relative), "--help"],
                                                relative.replace("/", "_") + ".help.txt"))

    warnings = [c["detail"]["warning"] for c in checks
                if isinstance(c.get("detail"), dict) and c["detail"].get("warning")]
    passed = all(c["status"] == "passed" for c in checks)
    status = ("passed_with_packaging_warning" if warnings else "passed") if passed else "failed"
    result = dict(status=status, warnings=warnings,
                  python=sys.version, executable=sys.executable, root=str(root), checks=checks,
                  model_built=False, training_executed=False, forward_executed=False,
                  evaluation_executed=False, dataset_processed=False,
                  weights_downloaded=False,
                  remaining=["Prepare company videos, annotations and class count",
                             "Prepare appropriate weights or an explicit from-scratch config",
                             "Validate actual train/forward/evaluation after user authorization"],
                  versions={d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
                            if d.metadata.get("Name")})
    (out / "runtime_audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("checks", "versions")}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
