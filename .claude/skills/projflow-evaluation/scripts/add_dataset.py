#!/usr/bin/env python3
"""添加数据集脚本"""

import os
import sys
import json

DATASETS_DIR = "evaluation/datasets"

def create_dataset(dataset_id, name, description, task_type, metrics, num_samples=0, source="", categories=None):
    """创建数据集定义"""
    os.makedirs(DATASETS_DIR, exist_ok=True)

    filename = f"{DATASETS_DIR}/{dataset_id}.json"
    if os.path.exists(filename):
        print(f"文件已存在: {filename}")
        return False

    dataset = {
        "id": dataset_id,
        "name": name,
        "description": description,
        "task_type": task_type,
        "metrics": metrics if isinstance(metrics, list) else [metrics],
        "num_samples": num_samples,
        "source": source
    }

    if categories:
        dataset["categories"] = categories if isinstance(categories, list) else [categories]

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"✓ 已创建数据集: {filename}")
    return True

def main():
    if len(sys.argv) < 5:
        print("用法:")
        print("  python3 add_dataset.py <数据集ID> <名称> <描述> <任务类型> <指标> [样本数]")
        print("示例:")
        print("  python3 add_dataset.py mmlu MMLU 'Massive Multitask Language Understanding' multiple_choice accuracy 14042")
        sys.exit(1)

    dataset_id = sys.argv[1]
    name = sys.argv[2]
    description = sys.argv[3]
    task_type = sys.argv[4]
    metrics = sys.argv[5]
    num_samples = int(sys.argv[6]) if len(sys.argv) > 6 else 0

    create_dataset(dataset_id, name, description, task_type, metrics, num_samples)

if __name__ == "__main__":
    main()
