---
name: evaluation
description: |
  评测体系模块操作指南。用于模型管理、数据集管理、评测配置、评测运行、结果对比等操作。
  触发场景：(1) 添加新模型，(2) 添加新数据集，(3) 配置评测任务，(4) 运行评测，(5) 查看/对比评测结果
---

# 评测体系模块

本 skill 提供评测体系模块的完整操作指南。

## 项目结构

```
evaluation/
├── models/      # 模型定义 JSON
├── datasets/    # 数据集定义 JSON
├── configs/     # 评测配置 JSON
├── scripts/     # 评测脚本
└── results/     # 评测结果 JSON
```

## 启动服务

```bash
# 后端 (8090)
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090
```

---

## 1. 模型管理

### 模型存储位置

```
evaluation/models/
```

### 添加新模型

在 `evaluation/models/` 目录下创建 JSON 文件：

```json
// evaluation/models/gpt-4.json
{
  "id": "gpt-4",
  "name": "GPT-4",
  "provider": "OpenAI",
  "type": "chat",
  "endpoint": "https://api.openai.com/v1/chat/completions",
  "parameters": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "description": "OpenAI GPT-4 model",
  "enabled": true
}
```

### 模型字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 模型唯一标识 |
| name | string | 模型名称 |
| provider | string | 提供商 (OpenAI, Anthropic, etc.) |
| type | string | 类型 (chat, completion) |
| endpoint | string | API 端点 URL |
| parameters | object | 默认参数 |
| description | string | 描述 |
| enabled | boolean | 是否启用 |

### 多个模型文件

```
evaluation/models/
├── gpt-4.json
├── gpt-3.5-turbo.json
├── claude-3-opus.json
└── llama-3-70b.json
```

---

## 2. 数据集管理

### 数据集存储位置

```
evaluation/datasets/
```

### 添加新数据集

在 `evaluation/datasets/` 目录下创建 JSON 文件：

```json
// evaluation/datasets/mmlu.json
{
  "id": "mmlu",
  "name": "MMLU",
  "description": "Massive Multitask Language Understanding",
  "task_type": "multiple_choice",
  "metrics": ["accuracy"],
  "num_samples": 14042,
  "source": "https://github.com/hendrycks/test",
  "categories": ["STEM", "Humanities", "Social Sciences", "Other"]
}
```

### 数据集字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 数据集唯一标识 |
| name | string | 数据集名称 |
| description | string | 描述 |
| task_type | string | 任务类型 (multiple_choice, qa, generation) |
| metrics | array | 评估指标 |
| num_samples | number | 样本数量 |
| source | string | 数据来源 |
| categories | array | 分类 |

### 常用数据集

```
evaluation/datasets/
├── mmlu.json
├── humaneval.json
├── mmb.json
├── ceval.json
└── agieval.json
```

---

## 3. 评测配置

### 配置存储位置

```
evaluation/configs/
```

### 创建评测配置

```json
// evaluation/configs/llm-benchmark.json
{
  "id": "llm-benchmark",
  "name": "LLM Benchmark",
  "description": "Comprehensive LLM evaluation",
  "models": ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"],
  "datasets": ["mmlu", "humaneval", "mmb"],
  "metrics": {
    "mmlu": "accuracy",
    "humaneval": "pass@1",
    "mmb": "accuracy"
  },
  "run_config": {
    "batch_size": 10,
    "max_concurrent": 5,
    "timeout": 300
  }
}
```

### 配置字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 配置唯一标识 |
| name | string | 配置名称 |
| models | array | 参与的模型 ID 列表 |
| datasets | array | 参与的数据集 ID 列表 |
| metrics | object | 数据集到指标的映射 |
| run_config | object | 运行参数 |

---

## 4. 运行评测

### API 端点

```bash
# 获取模型列表
GET /api/evaluation/models

# 获取数据集列表
GET /api/evaluation/datasets

# 获取评测配置
GET /api/evaluation/configs

# 获取评测结果
GET /api/evaluation/results

# 运行评测（如果实现了）
POST /api/evaluation/run
{
  "config_id": "llm-benchmark"
}
```

### 手动运行评测

创建评测脚本 `evaluation/scripts/run_benchmark.py`：

```python
#!/usr/bin/env python3
"""运行评测脚本示例"""

import json
import os
import time
from datetime import datetime

MODELS_DIR = "evaluation/models"
DATASETS_DIR = "evaluation/datasets"
RESULTS_DIR = "evaluation/results"

def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)

def save_result(config_id, model_id, dataset_id, metrics):
    """保存评测结果"""
    result_file = os.path.join(RESULTS_DIR, f"{config_id}_{model_id}_{dataset_id}.json")
    result = {
        "config_id": config_id,
        "model_id": model_id,
        "dataset_id": dataset_id,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Result saved: {result_file}")

def run_evaluation(config_id):
    """运行评测"""
    # 加载配置
    config_path = os.path.join("evaluation/configs", f"{config_id}.json")
    config = load_json(config_path)
    
    for model_id in config.get("models", []):
        for dataset_id in config.get("datasets", []):
            print(f"Running: {model_id} on {dataset_id}")
            # TODO: 实现实际的评测逻辑
            metrics = {"accuracy": 0.85}  # 示例结果
            save_result(config_id, model_id, dataset_id, metrics)
    
    print("Evaluation completed!")

if __name__ == "__main__":
    import sys
    config_id = sys.argv[1] if len(sys.argv) > 1 else "llm-benchmark"
    run_evaluation(config_id)
```

运行：
```bash
python3 evaluation/scripts/run_benchmark.py llm-benchmark
```

---

## 5. 评测结果

### 结果存储位置

```
evaluation/results/
```

### 结果格式

```json
// evaluation/results/llm-benchmark_gpt-4_mmlu.json
{
  "config_id": "llm-benchmark",
  "model_id": "gpt-4",
  "dataset_id": "mmlu",
  "metrics": {
    "accuracy": 0.86,
    "f1": 0.84
  },
  "timestamp": "2026-07-10T10:30:00",
  "details": {
    "total_samples": 14042,
    "correct": 12076,
    "time_taken": 120.5
  }
}
```

### 查看结果

```bash
# 列出所有结果
ls evaluation/results/

# 查看特定结果
cat evaluation/results/llm-benchmark_gpt-4_mmlu.json

# 批量查看
ls evaluation/results/ | while read f; do echo "=== $f ==="; cat "evaluation/results/$f"; done
```

---

## 6. 结果对比

### 对比脚本示例

```python
#!/usr/bin/env python3
"""结果对比脚本"""

import json
import os
from collections import defaultdict

RESULTS_DIR = "evaluation/results"

def load_results():
    results = {}
    for f in os.listdir(RESULTS_DIR):
        if f.endswith('.json'):
            with open(os.path.join(RESULTS_DIR, f)) as fp:
                results[f] = json.load(fp)
    return results

def compare_models(results, dataset_id):
    """对比不同模型在同一个数据集上的表现"""
    comparison = defaultdict(dict)
    
    for name, result in results.items():
        if result.get('dataset_id') == dataset_id:
            model_id = result['model_id']
            metrics = result.get('metrics', {})
            comparison[model_id] = metrics
    
    return comparison

if __name__ == "__main__":
    results = load_results()
    
    # 对比 MMLU 数据集
    print("=== MMLU Results ===")
    comparison = compare_models(results, "mmlu")
    for model, metrics in sorted(comparison.items(), 
                                 key=lambda x: x[1].get('accuracy', 0), 
                                 reverse=True):
        print(f"{model}: {metrics}")
```

---

## 7. 常用命令

```bash
# 启动服务
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8090

# 查看所有模型
curl http://localhost:8090/api/evaluation/models

# 查看所有数据集
curl http://localhost:8090/api/evaluation/datasets

# 查看所有评测结果
curl http://localhost:8090/api/evaluation/results
```
