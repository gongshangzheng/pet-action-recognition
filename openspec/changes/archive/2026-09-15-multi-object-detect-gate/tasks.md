# Tasks: multi-object-detect-gate

> 总管 change：`pet-motion-latent-pipeline`。本 change 验收通过后进入 `batch-followcam-extraction`。
> 正式脚本 = `scripts/plf_multi_detect.py`（入版本管理；禁止 /tmp 临时脚本）。

- [x] 1.1 多 prompt 同帧检测实现：`scripts/plf_multi_detect.py`（默认 `cat. bed. table. sofa. shelf.`，`--prompt` 可调）；产物 = `<out>/multi_detect.mp4` + `multi_detect.json`
- [x] 1.2 074451 段实测：cat 1834/1859（98.7%）、table/sofa/shelf 全段检出、bed 0（画面无床）——五类版用户初评「效果不错」
- [x] 1.3 碗/摄像头文本检测实测并裁定撤下：bowl 2952 次误框、camera 4/1859 召回 → 静态小物体转总管 D9 路线（SAM 分割缓存 + 登记检索）
- [x] 1.4 **用户验收通过（2026-09-14）**：五类版效果用户认可（「检测效果还是不错的」）；碗/摄像头撤下裁定同步确认；状态行逻辑随验收视频交付
- [x] 1.5 检出统计 JSON 格式定稿（`multi_detect.json`：video/frames/threshold/prompt/det_counts），供 batch-followcam-extraction 消费
