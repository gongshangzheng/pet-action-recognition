#!/usr/bin/env python3
"""Small remote training checks. Data, losses and updated weights stay in RAM."""
from __future__ import annotations

import argparse
import collections
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import sys
import time
import traceback
import types
import urllib.parse
import zipfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data-root', type=Path, default=Path('/home/work/pet_analysis_wyy'))
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--steps', type=int, default=3, choices=(1, 2, 3))
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--only', help='Comma-separated check names; default: all')
    args = parser.parse_args()
    root, data_root = args.root.resolve(), args.data_root.resolve()
    os.chdir(root)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / 'models/mmaction2'))
    for key, value in {
        'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_CACHE_DISABLE': '1',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'YOLO_AUTOINSTALL': 'false', 'NUMBA_DISABLE_JIT': '1',
        'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2',
        'YOLO_CONFIG_DIR': str(root / '.runtime/cache/ultralytics'),
        'TORCH_HOME': str(root / '.runtime/cache/torch'),
        'HF_HOME': str(root / '.runtime/cache/huggingface'),
    }.items():
        os.environ[key] = value
    protected = [data_root] + [root / name for name in
        ('results', 'checkpoints', 'datasets', 'data', 'live', 'weights')]
    data_suffixes = {'.mp4', '.avi', '.jpg', '.jpeg', '.png', '.npy', '.npz',
                     '.pkl', '.pt', '.pth', '.onnx', '.rknn', '.csv', '.log'}

    def guarded(path):
        path = Path(os.fsdecode(path)).resolve()
        return path.suffix.lower() in data_suffixes or any(
            path == parent or parent in path.parents for parent in protected)

    def audit(event, values):
        if event == 'socket.connect' and values[0].family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError('Network connections are disabled')
        if event == 'open' and not isinstance(values[0], int):
            filename, mode, flags = values
            write = (mode is not None and any(c in mode for c in 'wax+')) or (
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if write and guarded(filename):
                raise RuntimeError(f'Data/result writes are disabled: {filename}')
        if event in ('os.remove', 'os.rmdir', 'os.rename', 'os.link', 'os.symlink'):
            for value in values[:2]:
                if isinstance(value, (str, bytes)) and guarded(value):
                    raise RuntimeError('Mutating existing data/model paths is disabled')

    sys.addaudithook(audit)
    import numpy as np
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(1729)
    np.random.seed(1729)
    if not args.device.startswith('cuda') or not torch.cuda.is_available():
        raise RuntimeError('An available remote CUDA GPU is required')
    torch.cuda.set_device(args.device)
    state, statuses = {}, []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)

    def finite(tensor):
        check(bool(torch.isfinite(tensor).all()), 'Non-finite loss/gradient')

    class AuditedSGD(torch.optim.SGD):
        def __init__(self, model, required_groups=()):
            self.named = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
            self.required_groups = required_groups
            self.last_stats = {}
            super().__init__([p for _, p in self.named], lr=1e-4, momentum=0.0)

        def step(self, closure=None):
            probes, nonzero = [], []
            for name, parameter in self.named:
                gradient = parameter.grad
                if gradient is not None:
                    finite(gradient)
                    if float(gradient.detach().abs().max()) > 0:
                        nonzero.append(name)
                flat = parameter.detach().reshape(-1)
                indices = torch.linspace(0, len(flat) - 1, min(32, len(flat)),
                                         device=flat.device).long()
                probes.append((parameter, indices, flat[indices].clone()))
            check(bool(nonzero), 'All gradients are absent/zero')
            for group in self.required_groups:
                check(any(name.startswith(group) for name in nonzero), f'No nonzero gradient in {group}')
            result = super().step(closure)
            changed = sum(not torch.equal(p.detach().reshape(-1)[idx], before)
                          for p, idx, before in probes)
            check(changed > 0, 'Optimizer did not change any sampled parameters')
            self.last_stats = dict(nonzero_gradient_tensors=len(nonzero),
                                   changed_parameter_tensors=changed, finite_gradients=True)
            return result

    def train_simple(model, loss_function, required_groups=()):
        model.train()
        optimizer = AuditedSGD(model, required_groups)
        losses, updates = [], []
        for step in range(args.steps):
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model)
            finite(loss)
            check(loss.ndim == 0, 'Training loss must be scalar')
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
            updates.append(dict(optimizer.last_stats))
            print(f'TRAIN_STEP {step + 1}/{args.steps} loss={losses[-1]:.6f} '
                  f'nonzero_grads={updates[-1]["nonzero_gradient_tensors"]} '
                  f'updated_params={updates[-1]["changed_parameter_tensors"]}', flush=True)
        optimizer.zero_grad(set_to_none=True)
        return dict(losses=losses, updates=updates, steps=args.steps, device=args.device)

    def deadline(signum, frame):
        raise TimeoutError(f'Check exceeded {args.timeout} seconds')

    signal.signal(signal.SIGALRM, deadline)

    def run(name, callback):
        print(f'BEGIN {name}', flush=True)
        signal.alarm(args.timeout)
        started = time.monotonic()
        try:
            details = callback()
            torch.cuda.synchronize()
            print('PASS ' + name + ' ' + json.dumps(details, ensure_ascii=False), flush=True)
            statuses.append((name, True))
        except Exception as exc:
            print(f'FAIL {name}: {type(exc).__name__}: {exc}', flush=True)
            traceback.print_exc(limit=6)
            statuses.append((name, False))
        finally:
            signal.alarm(0)
            gc.collect()
            torch.cuda.empty_cache()
            print(f'CHECK_SECONDS {name} {time.monotonic() - started:.3f}', flush=True)

    def sha256(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def prepare_action_data():
        import cv2
        import decord
        cv2.setNumThreads(2)
        annotation = data_root / 'annotation-wyy/merged_annotations.csv'
        originals = [annotation, data_root / 'annotation-wyy/merged_annotations.json']
        state['annotation_before'] = {p: sha256(p) for p in originals}
        with annotation.open(encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.DictReader(handle))
        labels = sorted({label for row in rows if row.get('behavior')
                         for item in json.loads(row['behavior'])
                         for label in item.get('timelinelabels', [])})
        check(len(labels) > 1, 'Insufficient action classes')
        label_map = {name: i for i, name in enumerate(labels)}
        video_dir = data_root / 'dataset-wyy'
        files = {p.name: p for p in video_dir.iterdir()
                 if p.is_file() and p.suffix.lower() == '.mp4' and not p.name.startswith('._')}
        by_label = collections.defaultdict(list)
        matched = 0
        for row in rows:
            name = urllib.parse.unquote(urllib.parse.urlsplit(row['video']).path).rsplit('/', 1)[-1]
            if name not in files:
                name = re.sub(r'^[0-9a-fA-F]{8}-', '', name)
            if name not in files:
                continue
            matched += 1
            for item in json.loads(row.get('behavior') or '[]'):
                # Skip simultaneous multiple labels; this check uses hard CE.
                names = item.get('timelinelabels', [])
                if len(names) != 1:
                    continue
                for span in item.get('ranges', []):
                    begin, end = span['start'], span['end']
                    if int(begin) == begin and int(end) == end and end - begin >= 15:
                        by_label[names[0]].append((files[name], int(begin), int(end)))
        records, summaries, selected_stats = [], [], {}
        for label in labels:
            for path, start, end in by_label[label][:12]:
                reader = None
                try:
                    reader = decord.VideoReader(str(path), num_threads=1)
                    check(1 <= start <= end <= len(reader), 'Annotated range exceeds video frames')
                    length = min(32, end - start + 1)
                    begin = (start - 1) + (end - start + 1 - length) // 2
                    frames = []
                    for index in range(begin, begin + length):
                        image = reader[index].asnumpy()
                        h, w = image.shape[:2]
                        scale = min(1.0, 256 / min(h, w))
                        frames.append(cv2.resize(image, (round(w * scale), round(h * scale))))
                    array = np.stack(frames)
                    records.append(dict(array=array, total_frames=length,
                                        avg_fps=float(reader.get_avg_fps()), label=label_map[label]))
                    summaries.append(dict(label=label, frame_count=length,
                                          fps=float(reader.get_avg_fps()),
                                          original_range=[start, end], decoded_range_zero_based=[begin, begin + length - 1]))
                    selected_stats[path] = (path.stat().st_size, path.stat().st_mtime_ns)
                    break
                except Exception as exc:
                    print(f'SKIP_SAMPLE label={label} reason={type(exc).__name__}', flush=True)
                finally:
                    if reader is not None:
                        del reader
            if len(records) >= 2:
                break
        check(len(records) == 2, 'Could not decode two valid annotated clips')
        check(len({r['label'] for r in records}) == 2, 'Need two different action labels')
        state.update(records=records, labels=labels, selected_stats=selected_stats)
        return dict(annotation_rows=len(rows), exactly_matched_rows=matched,
                    unmatched_rows=len(rows) - matched, real_videos=len(files),
                    classes=len(labels), test_label_map=label_map, selected=summaries,
                    annotation_files_modified=False)

    def action_training(model_id, config_name):
        from mmengine import Config
        from mmengine.dataset import pseudo_collate
        from mmengine.optim import OptimWrapper
        from mmengine.registry import init_default_scope
        from mmaction.apis import init_recognizer
        from mmaction.datasets.base import BaseActionDataset
        from torch.utils.data import DataLoader
        check('records' in state, 'Company data preparation failed')
        cfg = Config.fromfile(str(root / 'models/mmaction2/configs/recognition' / config_name))
        # Dataset construction precedes init_recognizer, so establish the
        # transform registry scope before Compose builds the training pipeline.
        init_default_scope(cfg.get('default_scope', 'mmaction'))
        classes = len(state['labels'])
        cfg.model.cls_head.num_classes = classes
        cfg.model.cls_head.topk = (1,)
        pipeline = []
        for transform in cfg.get('train_pipeline', cfg.test_pipeline):
            transform = dict(transform)
            if transform['type'].endswith('Init'):
                continue
            if transform['type'] == 'DecordDecode':
                transform = dict(type='ArrayDecode')
            elif transform['type'] == 'SampleFrames':
                transform['num_clips'] = 3 if model_id == 'tsn-resnet50' else 1
                transform['test_mode'] = False
                if model_id != 'tsn-resnet50':
                    transform['frame_interval'] = 1
            elif transform['type'] in ('TenCrop', 'ThreeCrop'):
                transform['type'] = 'CenterCrop'
            pipeline.append(transform)

        class InMemoryActionDataset(BaseActionDataset):
            def load_data_list(self):
                return state['records']
        dataset = InMemoryActionDataset(ann_file='', pipeline=pipeline,
            data_prefix=dict(video=''), num_classes=classes, serialize_data=False)
        loader = DataLoader(dataset, batch_size=2, num_workers=0, collate_fn=pseudo_collate)
        # init_recognizer disables the extra backbone URL; all loading is local.
        model = init_recognizer(cfg, checkpoint=None, device=args.device)
        checkpoint = torch.load(root / 'checkpoints' / model_id / f'{model_id}_pretrained.pth',
                                map_location='cpu')
        weights = checkpoint.get('state_dict', checkpoint)
        model_state = model.state_dict()
        output_prefix = 'cls_head.fc2.' if cfg.model.cls_head.type == 'X3DHead' else 'cls_head.fc_cls.'
        filtered = {k: v for k, v in weights.items() if k in model_state and v.shape == model_state[k].shape}
        dropped = [k for k in weights if k not in filtered]
        check(bool(filtered), 'No local pretrained weights matched')
        check(all(k.startswith(output_prefix) for k in dropped),
              f'Unexpected incompatible checkpoint keys: {dropped}')
        missing, unexpected = model.load_state_dict(filtered, strict=False)
        check(not unexpected and all(k.startswith(output_prefix) for k in missing),
              f'Unexpected missing keys: {missing}')
        model.train()
        optimizer = AuditedSGD(model, ('backbone.', 'cls_head.'))
        wrapper = OptimWrapper(optimizer=optimizer)
        losses, updates = [], []
        for step in range(args.steps):
            batch = next(iter(loader))
            metrics = model.train_step(batch, wrapper)
            finite(metrics['loss'])
            losses.append(float(metrics['loss'].detach()))
            updates.append(dict(optimizer.last_stats))
            print(f'TRAIN_STEP {step + 1}/{args.steps} loss={losses[-1]:.6f} '
                  f'nonzero_grads={updates[-1]["nonzero_gradient_tensors"]} '
                  f'updated_params={updates[-1]["changed_parameter_tensors"]}', flush=True)
        return dict(losses=losses, updates=updates, steps=args.steps, classes=classes,
                    device=args.device, input='real company annotated ranges',
                    api='BaseActionDataset/DataLoader/model.train_step/OptimWrapper',
                    weights='local K400, new 12-class output layer', skipped_output_keys=dropped)

    image = torch.rand(2, 3, 128, 128, device=args.device)
    image[:, :, 32:96, 40:88] = 0.8
    mask = torch.zeros(2, 128, 128, device=args.device)
    mask[:, 32:96, 40:88] = 1

    def yolo_training(filename):
        from ultralytics import YOLO
        from ultralytics.utils import DEFAULT_CFG_DICT
        model = YOLO(str(root / 'checkpoints/ultralytics' / filename)).model.to(args.device)
        options = dict(DEFAULT_CFG_DICT)
        options.update(model.args if isinstance(model.args, dict) else vars(model.args))
        options['overlap_mask'] = True
        model.args = types.SimpleNamespace(**options)
        for name, parameter in model.named_parameters():
            # Match the standard trainer: DFL's fixed projection stays frozen.
            parameter.requires_grad_(not name.endswith('dfl.conv.weight'))
        batch = dict(img=image, batch_idx=torch.tensor([0, 1], device=args.device),
                     cls=torch.tensor([[15.], [15.]], device=args.device),
                     bboxes=torch.tensor([[0.5, 0.5, 0.375, 0.5]] * 2, device=args.device))
        if filename.endswith('-seg.pt'):
            batch['masks'] = mask
        components = []
        def criterion(network):
            loss, items = network.loss(batch)
            finite(items)
            components.append(items.detach().cpu().tolist())
            if filename.endswith('-seg.pt'):
                check(float(items[1]) > 0, 'Mask loss path was not exercised')
            return loss.sum()
        result = train_simple(model, criterion, ('model.0.', f'model.{len(model.model)-1}.'))
        result.update(input='synthetic images/boxes/masks', weights='local COCO',
                      api='Ultralytics native model.loss', loss_components=components)
        return result

    def mobile_training():
        from torchvision.models import mobilenet_v3_small
        model = mobilenet_v3_small(weights=None)
        model.load_state_dict(torch.load(root / 'checkpoints/torchvision/mobilenet_v3_small-047dcff4.pth',
                                        map_location='cpu'), strict=True)
        model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 2)
        model.to(args.device)
        target = torch.tensor([0, 1], device=args.device)
        result = train_simple(model, lambda m: F.cross_entropy(m(image), target), ('features.', 'classifier.'))
        result.update(input='synthetic binary labels', weights='ImageNet backbone, new binary head')
        return result

    def lraspp_training():
        from torchvision.models.segmentation import lraspp_mobilenet_v3_large
        model = lraspp_mobilenet_v3_large(weights=None, weights_backbone=None)
        model.load_state_dict(torch.load(root / 'checkpoints/torchvision/lraspp_mobilenet_v3_large-d234d4ea.pth',
                                        map_location='cpu'), strict=True)
        model.to(args.device)
        target = (mask * 8).long()
        result = train_simple(model, lambda m: F.cross_entropy(m(image)['out'], target),
                              ('backbone.', 'classifier.'))
        result.update(input='synthetic VOC cat=8 masks', weights='local VOC pretrained')
        return result

    def u2netp_training():
        archives = list((root / 'third-party/offline/sources').glob('xuebinqin--U-2-Net-*.zip'))
        check(len(archives) == 1, 'Expected one cached U2-Net source archive')
        with zipfile.ZipFile(archives[0]) as archive:
            paths = [n for n in archive.namelist() if n.endswith('/model/u2net.py')]
            check(len(paths) == 1, 'Ambiguous U2-Net source path')
            source = archive.read(paths[0]).decode('utf-8')
        module = types.ModuleType('_company_check_u2net')
        sys.modules[module.__name__] = module
        exec(compile(source, paths[0], 'exec'), module.__dict__)
        model = module.U2NETP(3, 1)
        model.load_state_dict(torch.load(root / 'checkpoints/u2net-training/u2netp.pth',
                                        map_location='cpu'), strict=True)
        model.to(args.device)
        target = mask[:, None]
        def criterion(network):
            outputs = network(image)
            check(len(outputs) == 7, 'Expected seven supervised U2-Net outputs')
            return sum(F.binary_cross_entropy(output, target) for output in outputs)
        result = train_simple(model, criterion, ('stage1.', 'side1.'))
        result.update(input='synthetic binary masks', weights='local pretrained U2NETP.pth',
                      api='cached upstream PyTorch model, seven-output BCE')
        return result

    def tcn_training():
        from pytorch_tcn import TCN
        model = TCN(num_inputs=16, num_channels=[16, 5], kernel_size=3,
                    dropout=0.0, causal=True).to(args.device)
        features = torch.randn(2, 16, 24, device=args.device)
        target = torch.arange(24, device=args.device)[None].repeat(2, 1) // 8
        result = train_simple(model, lambda m: F.cross_entropy(m(features), target.long()))
        result.update(input='synthetic features and framewise labels', weights='random')
        return result

    def originals_unchanged():
        check('annotation_before' in state, 'Original annotation snapshot unavailable')
        for path, digest in state['annotation_before'].items():
            check(sha256(path) == digest, 'An original annotation file changed')
        for path, before in state.get('selected_stats', {}).items():
            check((path.stat().st_size, path.stat().st_mtime_ns) == before, 'A source video changed')
        return dict(annotation_sha256_unchanged=True, selected_video_size_mtime_unchanged=True,
                    saved_training_data=False, saved_checkpoints=False)

    callbacks = [
        ('company_data_loader', prepare_action_data),
        ('mmaction_tsn_train', lambda: action_training('tsn-resnet50',
          'tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py')),
        ('mmaction_x3d_s_train', lambda: action_training('x3d-xs', 'x3d/x3d_s_13x6x1_facebook-kinetics400-rgb.py')),
        ('yolo11n_detect_train', lambda: yolo_training('yolo11n.pt')),
        ('yolo11n_segment_train', lambda: yolo_training('yolo11n-seg.pt')),
        ('mobilenet_binary_train', mobile_training),
        ('lraspp_train', lraspp_training),
        ('u2netp_pytorch_train', u2netp_training),
        ('causal_tcn_train', tcn_training),
        ('originals_unchanged', originals_unchanged),
    ]
    selected = set(args.only.split(',')) if args.only else {name for name, _ in callbacks}
    unknown = selected - {name for name, _ in callbacks}
    check(not unknown, f'Unknown check names: {sorted(unknown)}')
    if selected & {'mmaction_tsn_train', 'mmaction_x3d_s_train'}:
        selected |= {'company_data_loader', 'originals_unchanged'}
    print('TRAINING_CHECK_START save_data=False network=False max_steps=3', flush=True)
    for name, callback in callbacks:
        if name in selected:
            run(name, callback)
    print('SKIP_TRAINING PELT/GrabCut/tracking_rules/rembg_ONNX/RKNN: no neural training in these paths', flush=True)
    passed = sum(ok for _, ok in statuses)
    print(f'TRAINING_CHECK_DONE passed={passed}/{len(statuses)} saved_data=False', flush=True)
    return 0 if passed == len(statuses) else 1


if __name__ == '__main__':
    raise SystemExit(main())
