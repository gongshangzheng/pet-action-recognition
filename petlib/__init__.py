"""petlib — 宠物视觉管线接口层。

分层原则：schemas/base/registry 零重依赖（任何环境可 import）；
具体实现（grounding_dino/byte_track/superanimal/...）在各自模块内懒加载重依赖。
切换实现 = 改 pipeline.yaml 配置，不改管线代码（design D6）。
"""

__version__ = "0.1.0"
