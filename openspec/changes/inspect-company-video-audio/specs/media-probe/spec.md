# 音轨抽样规范

## Purpose

本能力在不解码、不转码、不下载原媒体的范围内读取已有视频的媒体属性，记录抽样策略与失败情况，避免将有限音轨样本的观察误写成全量数据结论。

## ADDED Requirements

### Requirement: Inspect existing files read-only
检查 SHALL 只读取媒体属性，不调用解码或转码、不写远程文件，
不下载公司视频或原标注。输入状态 SHALL 前后保持一致。

#### Scenario: Metadata inspection completes
- WHEN existing media is probed
- THEN input state remains unchanged and no remote files or decoded media are written.

### Requirement: Distinguish sample evidence from population claims
输出 SHALL 记录样本数量、策略、失败和音频流数量。
无法打开的样本 SHALL 视为检查失败，不计作无音频流。
抽样无音频流 SHALL 仅支持“所抽样本无音轨”，不宣称全量都没有。

#### Scenario: A sample cannot be opened
- WHEN a sampled file cannot be inspected
- THEN record an inspection failure rather than no audio, and limit conclusions to successfully inspected samples.
