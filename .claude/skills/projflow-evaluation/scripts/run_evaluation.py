#!/usr/bin/env python3
"""运行评测脚本"""

import os
import sys
import json
import time
from datetime import datetime

MODELS_DIR = "evaluation/models"
DATASETS_DIR = "evaluation/datasets"
CONFIGS_DIR = "evaluation/configs"
RESULTS_DIR = "evaluation/results"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_result(config_id, model_id, dataset_id, metrics, details=None):
    """保存评测结果"""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    timestamp = datetime.now().isoformat()
    result = {
        "config_id": config_id,
        "model_id": model_id,
        "dataset_id": dataset_id,
        "metrics": metrics,
        "timestamp": timestamp
    }

    if details:
        result["details"] = details

    filename = f"{RESULTS_DIR}/{config_id}_{model_id}_{dataset_id}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return filename

def run_evaluation(config_id):
    """运行评测"""
    # 加载配置
    config_path = f"{CONFIGS_DIR}/{config_id}.json"
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return

    config = load_json(config_path)
    print(f"开始评测: {config.get('name', config_id)}")

    models = config.get('models', [])
    datasets = config.get('datasets', [])
    metrics_config = config.get('metrics', {})

    total = len(models) * len(datasets)
    current = 0

    for model_id in models:
        # 加载模型
        model_path = f"{MODELS_DIR}/{model_id}.json"
        if not os.path.exists(model_path):
            print(f"模型不存在: {model_id}, 跳过")
            continue
        model = load_json(model_path)

        for dataset_id in datasets:
            current += 1
            print(f"[{current}/{total}] {model_id} on {dataset_id}...", end=" ")

            # 加载数据集
            dataset_path = f"{DATASETS_DIR}/{dataset_id}.json"
            if not os.path.exists(dataset_path):
                print(f"数据集不存在: {dataset_id}, 跳过")
                continue
            dataset = load_json(dataset_path)

            # TODO: 实现实际的评测逻辑
            # 这里模拟评测结果
            metrics = {
                "accuracy": 0.8 + (hash(model_id + dataset_id) % 20) / 100
            }

            # 保存结果
            filename = save_result(config_id, model_id, dataset_id, metrics, {
                "model": model.get('name'),
                "dataset": dataset.get('name')
            })
            print(f"✓ 结果保存到 {filename}")

    print(f"\n评测完成！")

def list_configs():
    """列出所有配置"""
    if not os.path.exists(CONFIGS_DIR):
        print("配置目录不存在")
        return

    files = [f for f in os.listdir(CONFIGS_DIR) if f.endswith('.json')]
    if not files:
        print("没有评测配置")
        return

    print("可用配置:")
    for f in files:
        config_id = f[:-5]
        try:
            config = load_json(f"{CONFIGS_DIR}/{f}")
            name = config.get('name', config_id)
            models = config.get('models', [])
            datasets = config.get('datasets', [])
            print(f"  - {config_id}: {name} ({len(models)} models, {len(datasets)} datasets)")
        except:
            print(f"  - {config_id}")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 run_evaluation.py <配置ID>     # 运行评测")
        print("  python3 run_evaluation.py --list       # 列出所有配置")
        print("示例:")
        print("  python3 run_evaluation.py llm-benchmark")
        print("  python3 run_evaluation.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_configs()
    else:
        config_id = sys.argv[1]
        run_evaluation(config_id)

if __name__ == "__main__":
    main()
