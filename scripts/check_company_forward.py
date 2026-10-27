#!/usr/bin/env python3
"""Bounded, offline forward checks; synthetic inputs and outputs stay in RAM.

Run on the company server only. No training, export, dataset, log or report.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time
import traceback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--timeout', type=int, default=180, help='Seconds per check')
    args = parser.parse_args()
    root = args.root.resolve()
    os.chdir(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / 'models/mmaction2'))
    for name, value in {
        'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_CACHE_DISABLE': '1',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'YOLO_AUTOINSTALL': 'false', 'NUMBA_DISABLE_JIT': '1',
        'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2',
        'OPENBLAS_NUM_THREADS': '2',
        'YOLO_CONFIG_DIR': str(root / '.runtime/cache/ultralytics'),
        'U2NET_HOME': str(root / '.runtime/cache/rembg-models'),
        'TORCH_HOME': str(root / '.runtime/cache/torch'),
        'HF_HOME': str(root / '.runtime/cache/huggingface'),
    }.items():
        os.environ[name] = value

    # Deny network access and writes to model/data/result paths. Third-party
    # import machinery may create temporary Python source, never test data.
    protected = [root / part for part in
                 ('results', 'checkpoints', 'datasets', 'data', 'live', 'weights')]
    data_suffixes = {'.mp4', '.avi', '.jpg', '.jpeg', '.png', '.npy', '.npz',
                     '.pkl', '.pt', '.pth', '.onnx', '.rknn', '.csv', '.log'}

    def audit(event, values):
        if event == 'socket.connect':
            if values[0].family in (socket.AF_INET, socket.AF_INET6):
                raise RuntimeError('Network connections are disabled in this check')
        if event != 'open' or isinstance(values[0], int):
            return
        filename, mode, flags = values
        write = (mode is not None and any(x in mode for x in 'wax+')) or (
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if write:
            path = Path(os.fsdecode(filename)).resolve()
            if path.suffix.lower() in data_suffixes or any(
                    path == p or p in path.parents for p in protected):
                raise RuntimeError(f'Data/result writes are disabled: {path}')

    sys.addaudithook(audit)
    import numpy as np
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(1729)
    np.random.seed(1729)
    if not args.device.startswith('cuda') or not torch.cuda.is_available():
        raise RuntimeError('This check requires an available remote CUDA GPU')
    torch.cuda.set_device(args.device)

    rng = np.random.default_rng(1729)
    frame = rng.integers(24, 160, size=(256, 256, 3), dtype=np.uint8)
    frame[72:184, 80:176] = [215, 185, 115]
    frames = np.repeat(frame[None], 96, axis=0)
    for i in range(len(frames)):
        frames[i, 90:130, (i % 48):((i % 48) + 40)] = [200, 85, 70]
    state = {}
    statuses = []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)

    def finite(value):
        if isinstance(value, torch.Tensor):
            check(bool(torch.isfinite(value).all()), 'Non-finite tensor output')
        else:
            check(bool(np.isfinite(value).all()), 'Non-finite array output')

    def timeout_handler(signum, current_frame):
        raise TimeoutError(f'Check exceeded {args.timeout} seconds')

    signal.signal(signal.SIGALRM, timeout_handler)

    def run(name, callback):
        print(f'BEGIN {name}', flush=True)
        started = time.monotonic()
        signal.alarm(args.timeout)
        try:
            with torch.inference_mode():
                details = callback()
            torch.cuda.synchronize()
            print('PASS ' + name + ' ' + json.dumps(details, ensure_ascii=False), flush=True)
            statuses.append((name, True))
        except Exception as exc:
            statuses.append((name, False))
            print(f'FAIL {name}: {type(exc).__name__}: {exc}', flush=True)
            traceback.print_exc(limit=6)
        finally:
            signal.alarm(0)
            print(f'CHECK_SECONDS {name} {time.monotonic() - started:.3f} '
                  '(initialization included; not a benchmark)', flush=True)
            gc.collect()
            torch.cuda.empty_cache()

    def action(model_id, config_name):
        from mmengine import Config
        from mmaction.apis import init_recognizer, inference_recognizer
        cfg = Config.fromfile(str(root / 'models/mmaction2/configs/recognition' / config_name))
        pipeline = []
        for transform in cfg.test_pipeline:
            transform = dict(transform)
            if transform['type'].endswith('Init'):
                continue
            if transform['type'] == 'DecordDecode':
                transform = dict(type='ArrayDecode')
            elif transform['type'] == 'SampleFrames':
                transform['num_clips'] = 3 if model_id == 'tsn-resnet50' else 1
            elif transform['type'] in ('TenCrop', 'ThreeCrop'):
                transform['type'] = 'CenterCrop'
            pipeline.append(transform)
        cfg.test_pipeline = pipeline
        checkpoint = root / 'checkpoints' / model_id / f'{model_id}_pretrained.pth'
        check(checkpoint.is_file(), f'Missing local checkpoint: {checkpoint}')
        model = init_recognizer(cfg, str(checkpoint), device=args.device)
        result = inference_recognizer(model, dict(
            array=frames, total_frames=len(frames), avg_fps=30,
            label=-1, start_index=0, modality='RGB'))
        score = result.pred_score.detach().cpu()
        finite(score)
        classes = int(cfg.model.cls_head.num_classes)
        check(tuple(score.shape) == (classes,), 'Wrong action score shape')
        check(bool((score >= 0).all()) and abs(float(score.sum()) - 1) < 1e-3,
              'Invalid action probabilities')
        return dict(shape=list(score.shape), device=args.device,
                    weights='local Kinetics-400 pretrained',
                    sum=float(score.sum()), pipeline='ArrayDecode, reduced views')

    def yolo(filename):
        from ultralytics import YOLO
        model = YOLO(str(root / 'checkpoints/ultralytics' / filename))
        check(model.names[15] == 'cat', 'COCO cat class mapping mismatch')
        # Ultralytics array inputs use BGR. The generated source is RGB.
        results = model.predict(source=frame[:, :, ::-1].copy(), imgsz=320,
                                device=args.device, classes=[15], conf=0.25,
                                save=False, save_txt=False, save_crop=False,
                                show=False, verbose=False, stream=False,
                                half=False, augment=False)
        check(len(results) == 1, 'Wrong YOLO batch size')
        result = results[0]
        boxes = result.boxes.data
        finite(boxes)
        check(tuple(boxes.shape[1:]) == (6,), 'Wrong detection shape')
        if len(boxes):
            check(bool((result.boxes.cls == 15).all()), 'Non-cat detections passed filter')
            xyxy = result.boxes.xyxy
            check(bool((xyxy[:, :2] <= xyxy[:, 2:]).all()), 'Invalid box coordinates')
            check(bool((xyxy >= 0).all()) and bool((xyxy <= 256).all()),
                  'Boxes exceed original image dimensions')
        if result.masks is not None:
            finite(result.masks.data)
        # Also validate dense model output: empty detections must not hide
        # NaNs or bypass segmentation head execution.
        tensor = torch.from_numpy(frame.copy()).permute(2, 0, 1).float()[None].to(args.device) / 255
        tensor = torch.nn.functional.interpolate(tensor, size=(320, 320), mode='bilinear', align_corners=False)
        raw = model.model(tensor)
        def validate(item):
            if isinstance(item, torch.Tensor):
                finite(item)
            elif isinstance(item, (tuple, list)):
                for child in item:
                    validate(child)
            elif isinstance(item, dict):
                for child in item.values():
                    validate(child)
        validate(raw)
        return dict(task=model.task, device=args.device, cat_id=15,
                    weights='local COCO pretrained', boxes=list(boxes.shape),
                    dense_output_finite=True, empty_detection_is_valid=True)

    def mobilenet():
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        from PIL import Image
        model = mobilenet_v3_small(weights=None).eval().to(args.device)
        weights = root / 'checkpoints/torchvision/mobilenet_v3_small-047dcff4.pth'
        model.load_state_dict(torch.load(weights, map_location='cpu'), strict=True)
        preprocess = MobileNet_V3_Small_Weights.DEFAULT.transforms()
        value = model(preprocess(Image.fromarray(frame))[None].to(args.device))
        finite(value)
        check(tuple(value.shape) == (1, 1000), 'Wrong classifier output')
        state['mobilenet'] = model
        state['preprocess'] = preprocess
        return dict(shape=list(value.shape), device=args.device,
                    weights='local ImageNet pretrained; not a binary cat classifier')

    def lraspp():
        from torchvision.models.segmentation import lraspp_mobilenet_v3_large
        from torchvision.models.segmentation import LRASPP_MobileNet_V3_Large_Weights
        from PIL import Image
        model = lraspp_mobilenet_v3_large(weights=None, weights_backbone=None).eval().to(args.device)
        checkpoint = root / 'checkpoints/torchvision/lraspp_mobilenet_v3_large-d234d4ea.pth'
        model.load_state_dict(torch.load(checkpoint, map_location='cpu'), strict=True)
        transform = LRASPP_MobileNet_V3_Large_Weights.DEFAULT.transforms(resize_size=256)
        tensor = transform(Image.fromarray(frame))[None].to(args.device)
        logits = model(tensor)['out']
        finite(logits)
        check(tuple(logits.shape) == (1, 21, 256, 256), 'Wrong LR-ASPP output')
        return dict(shape=list(logits.shape), device=args.device,
                    weights='local VOC 21-class pretrained', cat_id=8)

    def u2netp():
        import onnxruntime as ort
        from PIL import Image
        from rembg import remove
        from rembg.sessions.u2netp import U2netpSession
        checkpoint = root / '.runtime/cache/rembg-models/u2netp.onnx'
        check(checkpoint.is_file(), 'Missing local U2-NetP ONNX')
        class LocalSession(U2netpSession):
            @classmethod
            def download_models(cls, *unused_args, **unused_kwargs):
                return str(checkpoint)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 2
        session = LocalSession('u2netp', options, providers=['CPUExecutionProvider'])
        image = Image.fromarray(frame)
        raw = session.inner_session.run(None, session.normalize(
            image, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225), (320, 320)))
        for value in raw:
            finite(value)
        output = remove(image, session=session, alpha_matting=False)
        rgba = np.asarray(output)
        check(tuple(rgba.shape) == (256, 256, 4), 'Wrong rembg RGBA dimensions')
        finite(rgba)
        state['masked'] = (rgba[..., :3].astype(np.float32) *
                           (rgba[..., 3:4].astype(np.float32) / 255)).astype(np.uint8)
        return dict(shape=list(rgba.shape), device='CPUExecutionProvider',
                    weights='local U2-NetP pretrained', outputs=len(raw))

    def temporal():
        from pytorch_tcn import TCN
        model = TCN(num_inputs=1000, num_channels=[16, 5], kernel_size=3,
                    dropout=0.0, causal=True).eval().to(args.device)
        features = torch.randn(1, 1000, 12, device=args.device)
        before = model(features)
        altered = features.clone()
        altered[:, :, 8:] += 10
        after = model(altered)
        finite(before)
        finite(after)
        check(tuple(before.shape) == (1, 5, 12), 'Wrong TCN output')
        check(torch.allclose(before[:, :, :8], after[:, :, :8], atol=1e-5, rtol=1e-5),
              'Causal TCN used future features')
        state['tcn'] = model
        return dict(shape=list(before.shape), device=args.device,
                    weights='random; no learned action boundaries', causal_check=True)

    def pelt():
        import ruptures as rpt
        features = np.repeat(np.asarray([[0., 0.], [5., -3.], [-4., 4.]]), 20, axis=0)
        points = rpt.Pelt(model='l2', min_size=5, jump=1).fit(features).predict(pen=5)
        check(points == [20, 40, 60], f'Unexpected PELT boundaries: {points}')
        return dict(boundaries=points, device='CPU', method='non-model; synthetic change points')

    def combined():
        from PIL import Image
        check(all(key in state for key in ('masked', 'mobilenet', 'preprocess', 'tcn')),
              'Required independent module failed')
        tensor = state['preprocess'](Image.fromarray(state['masked']))[None].to(args.device)
        features = state['mobilenet'](tensor).softmax(dim=1)
        sequence = features.unsqueeze(-1).repeat(1, 1, 12)
        output = state['tcn'](sequence)
        finite(output)
        check(tuple(output.shape) == (1, 5, 12), 'Combined pipeline dimension mismatch')
        return dict(chain='U2-NetP actual mask -> MobileNetV3 -> random TCN',
                    shape=list(output.shape), production_pipeline=False)

    print('FORWARD_CHECK_START synthetic_only=True save_data=False network=False', flush=True)
    run('mmaction_tsn', lambda: action('tsn-resnet50',
        'tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py'))
    run('mmaction_x3d_s', lambda: action('x3d-xs', 'x3d/x3d_s_13x6x1_facebook-kinetics400-rgb.py'))
    run('yolo11n_detect', lambda: yolo('yolo11n.pt'))
    run('yolo11n_segment', lambda: yolo('yolo11n-seg.pt'))
    run('mobilenet_v3_small', mobilenet)
    run('lraspp', lraspp)
    run('rembg_u2netp', u2netp)
    run('causal_tcn', temporal)
    run('pelt', pelt)
    run('in_memory_combined', combined)
    passed = sum(ok for _, ok in statuses)
    print(f'FORWARD_CHECK_DONE passed={passed}/{len(statuses)} saved_data=False', flush=True)
    return 0 if passed == len(statuses) else 1


if __name__ == '__main__':
    raise SystemExit(main())
