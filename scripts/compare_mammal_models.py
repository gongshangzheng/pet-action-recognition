"""Evaluate existing AnimalKingdom-derived mammal checkpoints, without retraining.

Run on the project's remote MMAction2 environment. Outputs are isolated in --out.
Each model is evaluated in a subprocess so CUDA allocations cannot leak between
models. No network downloads or modification of existing experiment data.
"""
from __future__ import annotations

import argparse
import ast
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import traceback

LABELS = ['locomotion', 'jump', 'eating', 'drinking', 'grooming', 'still_rest', 'social_interaction']
DATASET = 'pet_action_mammal_v0'


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    tmp.replace(path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def discover(repo, out):
    candidates, by_model = [], {}
    for f in sorted((repo / 'checkpoints').glob('*/*best.json')):
        meta = json.loads(f.read_text())
        if meta.get('dataset') != DATASET:
            continue
        ckpt = f.with_suffix('.pth')
        wd = repo / 'results/training/work_dirs' / meta['run_id']
        configs = sorted(wd.glob('*.py'))
        item = dict(model_id=meta['model_id'], run_id=meta['run_id'],
                    checkpoint=str(ckpt), config=str(configs[0]) if len(configs) == 1 else None,
                    metadata=meta, usable=ckpt.is_file() and len(configs) == 1)
        candidates.append(item)
        if item['usable']:
            by_model.setdefault(item['model_id'], []).append(item)
    selected = []
    for mid, items in sorted(by_model.items()):
        def rank(x):
            value = x['metadata'].get('metrics', {}).get('top1_acc')
            return (float(value) if value is not None else -1, x['run_id'])
        item = copy.deepcopy(max(items, key=rank))
        item['checkpoint_sha256'] = sha256(item['checkpoint'])
        item['config_sha256'] = sha256(item['config'])
        selected.append(item)
    registered = []
    tree = ast.parse((repo / 'server/routers/training.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_MMACTION2_REGISTRY' for t in node.targets):
            registered = ast.literal_eval(node.value)
    eligible = {r['model_id'] for r in selected}
    exclusions = []
    for r in registered:
        if r['id'] in eligible:
            continue
        reason = 'No usable seven-class mammal fine-tuned checkpoint and saved config'
        if r.get('type') in ('detection', 'vlm'):
            reason = 'Different task or external VLM; outside RGB seven-class comparison'
        if r['id'] == 'videomae-v1' and 'videomae-base' in eligible:
            reason = 'Historical VideoMAE checkpoint is evaluated under its original ID videomae-base'
        exclusions.append(dict(model_id=r['id'], reason=reason))
    ds = repo / 'datasets' / DATASET
    artifacts = out / 'dataset'
    artifacts.mkdir(parents=True, exist_ok=True)
    for name in ['README.md', 'annotation/summary.json', 'annotation/class_distribution.csv',
                 'annotation/labels.txt', 'annotation/label_map_v0.csv',
                 'annotation/meta_public_mammal.csv', 'annotation/video_manifest.csv',
                 'annotation/train_public.txt', 'annotation/val_public.txt', 'annotation/test_public.txt']:
        shutil.copy2(ds / name, artifacts / Path(name).name)
    split_rows = {}
    for split in ['train', 'val', 'test']:
        split_rows[split] = [line.rsplit(maxsplit=1) for line in (ds / 'annotation' / f'{split}_public.txt').read_text().splitlines() if line.strip()]
    ids = {k: {x[0] for x in v} for k, v in split_rows.items()}
    overlap = {a + '_' + b: sorted(ids[a] & ids[b]) for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]}
    missing = [path for rows in split_rows.values() for path, _ in rows if not (ds / path).is_file()]
    import collections
    meta_rows = list(csv.DictReader((ds / 'annotation/meta_public_mammal.csv').open()))
    audit = dict(source_datasets=dict(collections.Counter(r['source_dataset'] for r in meta_rows)),
                 counts={k: len(v) for k, v in split_rows.items()}, split_path_overlap=overlap,
                 missing_files=missing, test_sha256=sha256(ds / 'annotation/test_public.txt'),
                 limitations=json.loads((ds / 'annotation/summary.json').read_text())['limitations'])
    manifest = dict(dataset=DATASET, labels=LABELS, selection='highest historical validation Top-1 among available best checkpoints',
                    selected=selected, candidates=candidates, exclusions=exclusions, dataset_audit=audit)
    write_json(out / 'manifest.json', manifest)
    if missing or any(overlap.values()):
        raise RuntimeError('Dataset audit failed; inspect manifest.json')
    return manifest


def stats(values):
    import numpy as np
    a = np.asarray(values, dtype=float)
    return dict(n=len(a), mean_ms=float(a.mean()), median_ms=float(np.median(a)),
                p95_ms=float(np.percentile(a, 95)), std_ms=float(a.std()),
                min_ms=float(a.min()), max_ms=float(a.max()))


def metrics_from_confusion(cm):
    import numpy as np
    cm = np.asarray(cm, dtype=np.int64)
    tp = cm.diagonal()
    support, predicted = cm.sum(axis=1), cm.sum(axis=0)
    precision = np.divide(tp, predicted, out=np.zeros(7), where=predicted != 0)
    recall = np.divide(tp, support, out=np.zeros(7), where=support != 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(7), where=(precision + recall) != 0)
    n = int(cm.sum())
    acc = float(tp.sum() / n) if n else 0.0
    z = 1.96
    den = 1 + z*z / n if n else 1
    center = (acc + z*z / (2*n)) / den if n else 0
    half = z * ((acc*(1-acc)/n + z*z/(4*n*n)) ** 0.5) / den if n else 0
    return dict(top1=acc, macro_precision=float(precision.mean()), macro_recall=float(recall.mean()),
                macro_f1=float(f1.mean()), weighted_f1=float((f1 * support).sum()/n) if n else 0,
                top1_wilson95=[max(0, center-half), min(1, center+half)],
                per_class=[dict(label=LABELS[i], support=int(support[i]), precision=float(precision[i]),
                                recall=float(recall[i]), f1=float(f1[i]), false_negative_rate=float(1-recall[i])) for i in range(7)])


def normalize_pipeline(original, recognizer_type):
    pipe = copy.deepcopy(original)
    for step in pipe:
        typ = step['type']
        if typ in ['ThreeCrop', 'TenCrop']:
            step['type'] = 'CenterCrop'
        if typ in ['SampleFrames', 'DenseSampleFrames', 'UniformSample']:
            step['test_mode'] = True
            if recognizer_type == 'Recognizer3D':
                step['num_clips'] = 1
            if 'twice_sample' in step:
                step['twice_sample'] = False
            if typ == 'DenseSampleFrames':
                step['num_sample_positions'] = 1
        if typ == 'DecordInit':
            step['num_threads'] = 1
    return pipe


def strip_initializers(value):
    if isinstance(value, dict):
        for k in list(value):
            if k in ('pretrained', 'init_cfg'):
                value[k] = None
            else:
                strip_initializers(value[k])
    elif isinstance(value, (list, tuple)):
        for v in value:
            strip_initializers(v)


def worker(args):
    repo, out = Path(args.repo), Path(args.out)
    sys.path[:0] = [str(repo / 'models/mmaction2'), str(repo)]
    os.chdir(repo)
    import numpy as np
    import torch
    from mmengine import Config
    from mmengine.dataset import Compose, pseudo_collate
    from mmengine.registry import init_default_scope
    from mmaction.registry import MODELS
    import mmaction.models  # noqa: F401
    import mmaction.datasets  # noqa: F401

    torch.set_num_threads(4)
    torch.cuda.set_device(torch.device(args.device))
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    random.seed(42); np.random.seed(42); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
    manifest = json.loads((out / 'manifest.json').read_text())
    item = next(x for x in manifest['selected'] if x['model_id'] == args.model)
    model_out = out / 'models' / args.model
    model_out.mkdir(parents=True, exist_ok=True)
    result = dict(model_id=args.model, status='running', run_id=item['run_id'],
                  checkpoint=item['checkpoint'], checkpoint_sha256=item['checkpoint_sha256'],
                  historical_training=item['metadata'], protocol='single_view_fp32_batch1',
                  source_script_sha256=sha256(__file__))
    write_json(model_out / 'result.json', result)
    try:
        cfg = Config.fromfile(item['config'])
        original_pipeline = cfg.get('test_pipeline')
        if original_pipeline is None:
            original_pipeline = cfg.test_dataloader.dataset.pipeline
        cfg.model.cls_head.num_classes = 7
        if cfg.model.cls_head.get('loss_cls', {}).get('num_classes') is not None:
            cfg.model.cls_head.loss_cls.num_classes = 7
        strip_initializers(cfg.model)
        pipeline = normalize_pipeline(original_pipeline, cfg.model.type)
        cfg.test_pipeline = pipeline
        cfg.dump(str(model_out / 'resolved_config.py'))
        write_json(model_out / 'protocol.json', dict(original_config=item['config'], original_pipeline=original_pipeline,
                   evaluation_pipeline=pipeline, model=cfg.model, seed=42, batch_size=1, precision='fp32',
                   tf32=False, warmup=args.warmup, repetitions=args.repetitions,
                   training=dict(train_cfg=cfg.get('train_cfg'), optim_wrapper=cfg.get('optim_wrapper'),
                                 train_batch_size=cfg.get('train_dataloader', {}).get('batch_size'), randomness=cfg.get('randomness'))))
        init_default_scope('mmaction')
        if cfg.model.cls_head.get('loss_cls', {}).get('type') == 'LabelSmoothLoss':
            # The saved config loses the import statement used by train_model.py.
            import configs.hooks.label_smooth_loss  # noqa: F401
            result['compatibility_notes'] = ['Registered the original project LabelSmoothLoss implementation']
        start = time.perf_counter()
        model = MODELS.build(cfg.model)
        checkpoint = torch.load(item['checkpoint'], map_location='cpu')
        state = checkpoint.get('state_dict', checkpoint)
        if state and all(k.startswith('module.') for k in state):
            state = {k[7:]: v for k, v in state.items()}
        if cfg.model.cls_head.type == 'TPNHead' and 'cls_head.new_cls.weight' in state:
            # TPN creates this Conv3d lazily during fcn_test; checkpoints saved after
            # validation contain it. Materialize the module and load every key.
            shape=state['cls_head.new_cls.weight'].shape
            if tuple(shape[2:]) != (1, 1, 1) or shape[0] != 7:
                raise RuntimeError('Unexpected TPN lazy classifier shape')
            model.cls_head.new_cls=torch.nn.Conv3d(shape[1],shape[0],1)
            result.setdefault('compatibility_notes',[]).append('Materialized original TPN lazy new_cls before strict loading; no weight keys discarded')
        model.load_state_dict(state, strict=True)
        del checkpoint, state
        model = model.to(args.device).float().eval()
        torch.cuda.synchronize()
        result.update(load_seconds=time.perf_counter()-start, strict_load=True,
                      parameters=sum(p.numel() for p in model.parameters()), checkpoint_bytes=Path(item['checkpoint']).stat().st_size,
                      backbone_type=cfg.model.backbone.type, architecture=cfg.model.backbone.get('arch'),
                      recognizer_type=cfg.model.type, device_name=torch.cuda.get_device_name(),
                      model_memory_allocated_mib=torch.cuda.memory_allocated()/2**20)
        compose = Compose(pipeline)
        ds = repo / 'datasets' / DATASET
        samples = [line.rsplit(maxsplit=1) for line in (ds/'annotation/test_public.txt').read_text().splitlines() if line.strip()]

        def prepare(relpath, target):
            data = compose(dict(filename=str(ds / relpath), label=int(target), start_index=0, modality='RGB'))
            return model.data_preprocessor(pseudo_collate([data]), training=False)

        class FullForward(torch.nn.Module):
            def __init__(self, recognizer):
                super().__init__(); self.recognizer = recognizer
            def forward(self, inputs):
                feats, kw = self.recognizer.extract_feat(inputs, test_mode=True)
                return self.recognizer.cls_head(feats, **kw)

        forward = FullForward(model).eval()
        with torch.inference_mode():
            prepared = prepare(*samples[0])
            inputs = prepared['inputs']
            result['input_shape'] = list(inputs.shape)
            result['benchmark_video'] = samples[0][0]
            torch.cuda.synchronize()
            t0 = time.perf_counter(); logits = forward(inputs); torch.cuda.synchronize()
            result['first_forward_ms'] = (time.perf_counter()-t0)*1000
            if logits.shape[-1] != 7 or not torch.isfinite(logits).all():
                raise RuntimeError('Invalid output shape or non-finite logits')
            result['logit_shape'] = list(logits.shape)
            del logits
            for _ in range(args.warmup):
                forward(inputs)
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            gpu_ms, host_ms = [], []
            for _ in range(args.repetitions):
                begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
                t0=time.perf_counter(); begin.record(); forward(inputs); end.record(); end.synchronize()
                host_ms.append((time.perf_counter()-t0)*1000); gpu_ms.append(begin.elapsed_time(end))
            result['forward_host'] = stats(host_ms)
            result['forward_cuda'] = stats(gpu_ms)
            result['forward_videos_per_second'] = 1000 / result['forward_host']['mean_ms']
            result['peak_forward_allocated_mib'] = torch.cuda.max_memory_allocated()/2**20
            result['peak_forward_reserved_mib'] = torch.cuda.max_memory_reserved()/2**20
            write_json(model_out/'forward_timings.json', dict(host_ms=host_ms, cuda_ms=gpu_ms))

            # Count the exact same full forward, including the classification head.
            try:
                from mmengine.analysis import FlopAnalyzer
                analysis = FlopAnalyzer(forward, (inputs,))
                total = analysis.total()
                result['flops'] = dict(total=total, gflops=total/1e9,
                    convention='One fused multiply-add = one FLOP; full backbone+neck+head for reported input',
                    unsupported_ops=dict(analysis.unsupported_ops()),
                    uncalled_modules=sorted(analysis.uncalled_modules()))
            except Exception as exc:
                result['flops'] = dict(error=str(exc))
            # Reset RNG after tracing, since TRN relation sampling is stochastic.
            random.seed(42); np.random.seed(42); torch.manual_seed(42)
            cm = np.zeros((7,7), dtype=np.int64)
            e2e, errors, predictions = [], [], []
            durations = {r['clip_path']: float(r['duration_sec']) for r in csv.DictReader((ds/'annotation/meta_public_mammal.csv').open())}
            torch.cuda.reset_peak_memory_stats()
            with (model_out/'predictions.jsonl').open('w', encoding='utf-8') as output:
                for index, (rel, target) in enumerate(samples):
                    try:
                        torch.cuda.synchronize(); t0=time.perf_counter()
                        batch = prepare(rel, target)
                        pred = model(**batch, mode='predict')[0].pred_score.detach().cpu().numpy()
                        torch.cuda.synchronize(); elapsed=(time.perf_counter()-t0)*1000
                        if pred.shape != (7,) or not np.isfinite(pred).all():
                            raise RuntimeError('Invalid class scores')
                        guess=int(pred.argmax()); cm[int(target),guess]+=1; e2e.append(elapsed)
                        record=dict(video=rel, target=int(target), prediction=guess, scores=pred.tolist(),
                                    correct=guess==int(target), e2e_ms=elapsed, duration_s=durations.get(rel))
                        predictions.append(record)
                        del batch
                    except Exception as exc:
                        record=dict(video=rel, target=int(target), error=str(exc)); errors.append(record)
                    output.write(json.dumps(record)+'\n'); output.flush()
                    if (index+1)%25==0:
                        print(f'{args.model} {index+1}/{len(samples)} errors={len(errors)}', flush=True)
            result.update(status='completed' if not errors else 'partial', total_samples=len(samples),
                          successful_samples=len(predictions), failed_samples=len(errors), errors=errors,
                          confusion_matrix=cm.tolist(), classification=metrics_from_confusion(cm),
                          e2e=stats(e2e) if e2e else None,
                          e2e_videos_per_second=1000*len(e2e)/sum(e2e) if e2e else None,
                          e2e_rtf=sum(e2e)/1000/sum(r['duration_s'] or 0 for r in predictions) if e2e else None,
                          peak_e2e_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
            write_json(model_out/'confusion_matrix.json',dict(labels=LABELS, rows='ground truth', columns='prediction', matrix=cm.tolist()))
            with (model_out/'per_class.csv').open('w',encoding='utf-8-sig',newline='') as f:
                rows=result['classification']['per_class']; writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        result['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    except Exception as exc:
        result.update(status='error', error=str(exc), traceback=traceback.format_exc())
        print(result['traceback'], flush=True)
    write_json(model_out/'result.json',result)
    print('MODEL_FINISHED',args.model,result['status'],flush=True)
    return 0 if result['status']=='completed' else 1


def summarize(out):
    manifest=json.loads((out/'manifest.json').read_text())
    rows=[]
    for item in manifest['selected']:
        f=out/'models'/item['model_id']/'result.json'
        r=json.loads(f.read_text()) if f.exists() else dict(model_id=item['model_id'],status='pending')
        rows.append(r)
    write_json(out/'comparison.json',rows)
    flat=[]
    for r in rows:
        c=r.get('classification',{}); host=r.get('forward_host',{}); gpu=r.get('forward_cuda',{}); e2e=r.get('e2e') or {}; fl=r.get('flops',{})
        flat.append(dict(model=r['model_id'],status=r['status'],top1=c.get('top1'),macro_f1=c.get('macro_f1'),
          macro_recall=c.get('macro_recall'),weighted_f1=c.get('weighted_f1'),n=r.get('successful_samples'),
          params_m=r.get('parameters',0)/1e6 if r.get('parameters') else None,gflops=fl.get('gflops'),
          unsupported_flop_ops=json.dumps(fl.get('unsupported_ops',{})),input_shape=str(r.get('input_shape','')),
          forward_mean_ms=host.get('mean_ms'),forward_p50_ms=host.get('median_ms'),forward_p95_ms=host.get('p95_ms'),
          cuda_mean_ms=gpu.get('mean_ms'),forward_videos_s=r.get('forward_videos_per_second'),
          e2e_mean_ms=e2e.get('mean_ms'),e2e_p95_ms=e2e.get('p95_ms'),e2e_videos_s=r.get('e2e_videos_per_second'),
          rtf=r.get('e2e_rtf'),checkpoint_mib=r.get('checkpoint_bytes',0)/2**20 if r.get('checkpoint_bytes') else None,
          error=r.get('error',''),run_id=r.get('run_id','')))
    if flat:
        with (out/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True); parser.add_argument('--out',required=True)
    parser.add_argument('--model'); parser.add_argument('--only'); parser.add_argument('--device',default='cuda:0')
    parser.add_argument('--warmup',type=int,default=20);parser.add_argument('--repetitions',type=int,default=100)
    parser.add_argument('--timeout',type=int,default=1800)
    args=parser.parse_args()
    if args.model: return worker(args)
    repo,out=Path(args.repo).resolve(),Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else discover(repo,out)
    sys.path[:0]=[str(repo/'models/mmaction2'),str(repo)]
    import importlib.metadata as metadata
    packages={}
    for name in ['torch','torchvision','mmcv','mmengine','mmaction2','numpy','decord']:
        try: packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError: packages[name]=None
    environment=dict(python=sys.version,packages=packages,script_sha256=sha256(__file__),
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv'],text=True),
        started_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), command=sys.argv)
    write_json(out/'environment.json',environment)
    only=set(args.only.split(',')) if args.only else None
    for item in manifest['selected']:
        mid=item['model_id']
        if only and mid not in only: continue
        dest=out/'models'/mid; dest.mkdir(parents=True,exist_ok=True)
        if (dest/'result.json').exists() and json.loads((dest/'result.json').read_text()).get('status')=='completed':
            continue
        gpu_index=args.device.split(':')[-1]
        # Wait for other GPU work instead of distorting timing or disrupting it.
        while True:
            used=int(subprocess.check_output(['nvidia-smi',f'--id={gpu_index}','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
            if used < 500: break
            print(f'WAIT_GPU memory_used={used}MiB',flush=True);time.sleep(15)
        cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'--repo',str(repo),'--out',str(out),
             '--model',mid,'--device',args.device,'--warmup',str(args.warmup),'--repetitions',str(args.repetitions)]
        env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONUNBUFFERED='1')
        print('MODEL_START',mid,flush=True)
        with (dest/'execution.log').open('w') as log:
            try:
                proc=subprocess.run(cmd,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
                rc=proc.returncode
            except subprocess.TimeoutExpired: rc=124
        if not (dest/'result.json').exists() or json.loads((dest/'result.json').read_text()).get('status')=='running':
            write_json(dest/'result.json',dict(model_id=mid,status='error',error=f'Worker exited {rc}; see execution.log'))
        summarize(out)
        print('MODEL_END',mid,'exit',rc,flush=True)
    summarize(out)
    write_json(out/'batch_status.json',dict(status='finished',finished_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    print('BATCH_FINISHED',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
