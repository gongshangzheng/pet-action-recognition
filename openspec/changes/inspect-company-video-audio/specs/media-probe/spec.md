# 音轨抽样规范

### Requirement: Inspect existing files read-only
检查 SHALL 只读取媒体属性，不调用解码或转码、不写远程文件，
不下载公司视频或原标注。输入状态 SHALL 前后保持一致。

### Requirement: Distinguish sample evidence from population claims
输出 SHALL 记录样本数量、策略、失败和音频流数量。
无法打开的样本 SHALL 视为检查失败，不计作无音频流。
抽样无音频流 SHALL 仅支持“所抽样本无音轨”，不宣称全量都没有。
