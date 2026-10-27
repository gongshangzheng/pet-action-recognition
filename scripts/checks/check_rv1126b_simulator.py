#!/usr/bin/env python3
"""Check one tiny RV1126B simulator path without retaining data or models."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile
import time
import traceback
import uuid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--timeout', type=int, default=240)
    args = parser.parse_args()
    root = args.root.resolve()
    initial_cwd = Path.cwd()
    sys.dont_write_bytecode = True
    ram_parent = Path('/dev/shm')
    if not ram_parent.is_dir() or not os.access(ram_parent, os.W_OK):
        raise RuntimeError('A writable RAM filesystem is required for this no-save check')
    workspace = tempfile.TemporaryDirectory(prefix='pet-rknn-', dir=ram_parent)
    ram = Path(workspace.name).resolve()
    link = root / '.runtime' / ('rknn-ram-' + uuid.uuid4().hex)
    link.symlink_to(ram, target_is_directory=True)
    for name, value in {
        'TMPDIR': str(link), 'TMP': str(link), 'TEMP': str(link),
        'MPLCONFIGDIR': str(link / 'matplotlib'), 'XDG_CACHE_HOME': str(link / 'cache'),
        'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_CACHE_DISABLE': '1',
        'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'YOLO_AUTOINSTALL': 'false',
    }.items():
        os.environ[name] = value
    # tempfile caches its selected default directory; force the RAM workspace.
    tempfile.tempdir = str(link)
    os.chdir(link)
    active = {'strict': True}

    def audit(event, values):
        if event == 'socket.connect' and values[0].family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError('Network connections are disabled')
        if not active['strict']:
            return
        if event == 'open' and not isinstance(values[0], int):
            filename, mode, flags = values
            write = (mode is not None and any(c in mode for c in 'wax+')) or (
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            path = Path(os.fsdecode(filename)).resolve()
            if write and path != ram and ram not in path.parents and str(path) != '/dev/null':
                raise RuntimeError(f'Writes outside the RAM workspace are disabled: {path}')

    sys.addaudithook(audit)
    stage = 'imports'
    toolkit = None
    passed = False
    started = time.monotonic()

    def deadline(signum, frame):
        raise TimeoutError(f'Simulator check exceeded {args.timeout} seconds')

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(args.timeout)

    def require(condition, message):
        if not condition:
            raise AssertionError(message)

    def success(name, value):
        require(value == 0, f'{name} returned {value}')
        print(f'PASS {name}', flush=True)

    print('SIMULATOR_CHECK_START target=rv1126b saved_results=False', flush=True)
    try:
        import numpy as np
        import onnx
        import onnxruntime as ort
        import torch
        from rknn.api import RKNN
        torch.set_num_threads(2)
        torch.set_num_interop_threads(2)
        torch.manual_seed(1729)
        model = torch.nn.Sequential(
            torch.nn.Conv2d(3, 4, 3, padding=1), torch.nn.ReLU(),
            torch.nn.AdaptiveAvgPool2d((1, 1)), torch.nn.Flatten(1),
        ).eval()
        samples = [torch.rand(1, 3, 32, 32), torch.zeros(1, 3, 32, 32)]
        with torch.inference_mode():
            references = [model(sample).numpy() for sample in samples]
        stage = 'onnx_export_and_ort'
        buffer = io.BytesIO()
        torch.onnx.export(model, samples[0], buffer, opset_version=12,
                          input_names=['image'], output_names=['scores'],
                          do_constant_folding=True)
        data = buffer.getvalue()
        onnx.checker.check_model(onnx.load_model_from_string(data))
        options = ort.SessionOptions()
        options.intra_op_num_threads = options.inter_op_num_threads = 2
        session = ort.InferenceSession(data, sess_options=options,
                                       providers=['CPUExecutionProvider'])
        for sample, reference in zip(samples, references):
            output = session.run(None, {'image': sample.numpy()})[0]
            require(np.allclose(output, reference, atol=1e-5, rtol=1e-4), 'ORT reference mismatch')
        del session
        print('PASS ONNX_checker_and_ORT', flush=True)
        # SDK requires a model pathname. This is an ephemeral tmpfs file,
        # never an exported/saved model on persistent storage.
        onnx_path = link / 'tiny.onnx'
        onnx_path.write_bytes(data)
        stage = 'rknn_construct'
        toolkit = RKNN(verbose=False, verbose_file=None)
        stage = 'rknn_config'
        success(stage, toolkit.config(target_platform='rv1126b', float_dtype='float16',
                                       mean_values=[[0, 0, 0]], std_values=[[1, 1, 1]]))
        stage = 'rknn_load_onnx'
        success(stage, toolkit.load_onnx(model=str(onnx_path)))
        stage = 'rknn_build_fp16'
        success(stage, toolkit.build(do_quantization=False))
        stage = 'simulator_init'
        success(stage, toolkit.init_runtime(target=None))
        outputs = []
        for index, (sample, reference) in enumerate(zip(samples, references)):
            stage = f'simulator_inference_{index}'
            result = toolkit.inference(inputs=[sample.numpy()], data_format=['nchw'])
            require(result is not None and len(result) == 1, 'Missing simulator output')
            output = np.asarray(result[0])
            require(output.shape == reference.shape, f'Output shape {output.shape} != {reference.shape}')
            require(np.isfinite(output).all(), 'Non-finite simulator output')
            error = np.abs(output.astype(np.float32) - reference)
            require(np.allclose(output, reference, atol=0.002, rtol=0.02), 'FP16 output exceeds tolerance')
            outputs.append(output.copy())
            print('PASS ' + stage + ' ' + json.dumps(dict(
                shape=list(output.shape), dtype=str(output.dtype),
                max_abs_error=float(error.max()), mean_abs_error=float(error.mean()),
                atol=0.002, rtol=0.02)), flush=True)
        require(not np.allclose(outputs[0], outputs[1], atol=1e-5, rtol=1e-5),
                'Different inputs unexpectedly returned identical outputs')
        print('PASS simulator_input_changes_output', flush=True)
        passed = True
    except Exception as exc:
        print(f'FAIL stage={stage} {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc(limit=7)
    finally:
        signal.alarm(0)
        if toolkit is not None:
            try:
                toolkit.release()
            except Exception as exc:
                passed = False
                print(f'FAIL release {type(exc).__name__}: {exc}', flush=True)
        os.chdir(initial_cwd)
        active['strict'] = False
        if link.is_symlink():
            link.unlink()
        workspace.cleanup()
        require(not link.exists() and not ram.exists(), 'RAM workspace cleanup failed')
        print('PASS RAM_workspace_removed saved_results=False', flush=True)
    print(f'SIMULATOR_CHECK_DONE passed={passed} elapsed={time.monotonic()-started:.3f}s '
          '(host check time; not board performance)', flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
