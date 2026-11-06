"""亮点抓取特征：画面亮度/对比度、宠物活动幅度、身体与面部面积占比和时长、行为识别信息。

核心计算只依赖 numpy + OpenCV；YOLO / MMAction2 在对应实现构造时懒加载。
设计见 openspec/changes/extract-highlight-features/design.md，字段见 docs/highlight_features.md。
"""
from petlib.highlights.aggregate import HighlightConfig
from petlib.highlights.report import SCHEMA, extract_highlights, write_outbox

__all__ = ["HighlightConfig", "SCHEMA", "extract_highlights", "write_outbox"]
