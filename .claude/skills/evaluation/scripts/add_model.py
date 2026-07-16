#!/usr/bin/env python3
"""添加模型脚本"""

import os
import sys
import json

MODELS_DIR = "evaluation/models"

def create_model(model_id, name, provider, model_type, endpoint, description="", parameters=None):
    """创建模型定义"""
    os.makedirs(MODELS_DIR, exist_ok=True)

    filename = f"{MODELS_DIR}/{model_id}.json"
    if os.path.exists(filename):
        print(f"文件已存在: {filename}")
        return False

    model = {
        "id": model_id,
        "name": name,
        "provider": provider,
        "type": model_type,
        "endpoint": endpoint,
        "description": description,
        "enabled": True
    }

    if parameters:
        model["parameters"] = parameters

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    print(f"✓ 已创建模型: {filename}")
    return True

def main():
    if len(sys.argv) < 5:
        print("用法:")
        print("  python3 add_model.py <模型ID> <模型名称> <提供商> <类型> <端点> [描述]")
        print("示例:")
        print("  python3 add_model.py gpt-4 GPT-4 OpenAI chat https://api.openai.com/v1/chat/completions")
        sys.exit(1)

    model_id = sys.argv[1]
    name = sys.argv[2]
    provider = sys.argv[3]
    model_type = sys.argv[4]
    endpoint = sys.argv[5]
    description = sys.argv[6] if len(sys.argv) > 6 else ""

    create_model(model_id, name, provider, model_type, endpoint, description)

if __name__ == "__main__":
    main()
