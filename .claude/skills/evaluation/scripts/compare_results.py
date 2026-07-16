#!/usr/bin/env python3
"""评测结果对比脚本"""

import os
import sys
import json
from collections import defaultdict

RESULTS_DIR = "evaluation/results"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_all():
    """对比所有评测结果"""
    if not os.path.exists(RESULTS_DIR):
        print(f"结果目录不存在: {RESULTS_DIR}")
        return

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
    if not files:
        print("没有评测结果")
        return

    # 按数据集分组
    by_dataset = defaultdict(lambda: defaultdict(dict))

    for f in files:
        result = load_json(os.path.join(RESULTS_DIR, f))
        model_id = result.get('model_id')
        dataset_id = result.get('dataset_id')
        metrics = result.get('metrics', {})

        by_dataset[dataset_id][model_id] = metrics

    # 打印对比结果
    print("=" * 60)
    print("评测结果对比")
    print("=" * 60)

    for dataset_id in sorted(by_dataset.keys()):
        print(f"\n## {dataset_id}")
        print("-" * 40)

        models = by_dataset[dataset_id]
        # 按第一个指标排序
        sorted_models = sorted(models.items(),
                            key=lambda x: list(x[1].values())[0] if x[1] else 0,
                            reverse=True)

        for rank, (model_id, metrics) in enumerate(sorted_models, 1):
            metric_str = " | ".join([f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}"
                                     for k, v in metrics.items()])
            print(f"{rank}. {model_id}: {metric_str}")

def compare_models(dataset_id):
    """对比指定数据集上的模型"""
    if not os.path.exists(RESULTS_DIR):
        print(f"结果目录不存在: {RESULTS_DIR}")
        return

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
    results = []

    for f in files:
        result = load_json(os.path.join(RESULTS_DIR, f))
        if result.get('dataset_id') == dataset_id:
            results.append(result)

    if not results:
        print(f"没有数据集 {dataset_id} 的评测结果")
        return

    print(f"\n## {dataset_id} 模型对比")
    print("-" * 40)

    sorted_results = sorted(results,
                          key=lambda x: list(x.get('metrics', {}).values())[0] if x.get('metrics') else 0,
                          reverse=True)

    for rank, result in enumerate(sorted_results, 1):
        model_id = result.get('model_id')
        metrics = result.get('metrics', {})
        metric_str = " | ".join([f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}"
                                 for k, v in metrics.items()])
        print(f"{rank}. {model_id}: {metric_str}")

def main():
    if len(sys.argv) < 2:
        compare_all()
    else:
        dataset_id = sys.argv[1]
        compare_models(dataset_id)

if __name__ == "__main__":
    main()
