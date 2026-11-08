# 证据

## 只读核查

当前 proposal 首次入 Git 为 2026-10-27，不等于最初构思日期。源侧只读连接/授权及附件输入尚缺；源端清点、附件哈希及差异报告未执行，不能用本地归档验证代替源侧核验。需用户确认可用源通道与授权。

## 2026-11-08：只读复核与待决处置

子代理核查本地文档和 Git 历史，未连接远端。原三项仍未完成：没有当前源端逐项比对、旧附件取回及哈希，也没有本 change 的差异报告。

- 旧源路径及时间见 `openspec/changes/archive/2026-10-27-recover-owned-cat-dataset/proposal.md` 和 `design.md`：视频 `/home/work/pet_analysis_wyy/dataset-wyy/`，标注 `/home/work/pet_analysis_wyy/annotation-wyy/merged_annotations.{csv,json}`；文档记录 2026-10-17 源目录存在、2026-10-21 用户报告大小，以及 2026-10-23 接收快照。恢复记录中的 5480/5480 SHA-256 一致是历史恢复副本记录，不是当前源端核验。
- `docs/company_video_paths.md` 记载 2026-10-10 旧服务器映射报告 `/home/work/analysis_code/results/datasets/company_video_paths_20261010T085713Z_d1e8d962/{path_mapping.csv,report.json}`；`docs/company_action_label_audit.md` 记载同日旧审计报告 `results/datasets/company_action_label_audit_20261010/report.json`。本机未读取到这些附件，不能补报其具体哈希或当前存在性。本机没有 `datasets/cat_raw/` 不代表 pet 没有数据，也不证明旧源下线。

**建议，待用户批准**：停止旧源核验计划，三项保留未完成、未验收；将已有来源、历史快照范围及未知项披露并入 `pet-pipeline` 原始数据卡。此建议尚未执行，数据卡披露不等于旧源当前一致性验收。


## 2026-11-08：用户确认处置

**2026-11-08 用户确认停止旧源核验计划**：保留 0/3 未完成、未验收；历史来源与未知项由 `pet-pipeline` 1.8 原始数据卡披露，披露不替代当前源端核验。
