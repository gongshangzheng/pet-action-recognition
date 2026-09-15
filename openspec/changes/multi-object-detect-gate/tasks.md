# Tasks: multi-object-detect-gate

> 总管 change：`pet-motion-latent-pipeline`。本 change 验收通过后进入 `batch-followcam-extraction`。
> 正式脚本 = `scripts/plf_multi_detect.py`（入版本管理；禁止 /tmp 临时脚本）。

- [x] 1.1 多 prompt 同帧检测实现：`scripts/plf_multi_detect.py`（默认 `cat. bed. table. sofa. shelf.`，`--prompt` 可调）；产物 = `<out>/multi_detect.mp4` + `multi_detect.json`
- [x] 1.2 074451 段实测：cat 1834/1859（98.7%）、table/sofa/shelf 全段检出、bed 0（画面无床）——五类版用户初评「效果不错」
- [x] 1.3 碗/摄像头文本检测实测并裁定撤下：bowl 2952 次误框、camera 4/1859 召回 → 静态小物体转总管 D9 路线（SAM 分割缓存 + 登记检索）
- [ ] 1.4 **用户验收**（`results/gate4/multi_detect.mp4`）：① 五类框质量 ② table 全帧检出是真是误 ③ 状态行 `cat on sofa/shelf/table` 切换准确性
- [ ] 1.5 验收通过后：检出统计 JSON 格式定稿（供 batch-followcam-extraction 消费），archive 本 change
