# Design: verify-cat-dataset-provenance

- **为什么拆出来**：这两项都依赖仓库外的连接（云电脑会话 / 源服务器可读通道），
  与 `recover-owned-cat-dataset` 中"本地归档副本已 100% 核验"的结论不同性质；混在一起会让归档状态失真。
- **源侧只读复查**：在可用连接内只读执行（`ls`/`du`/`stat` 级别），记录路径、目录层级、权限位、
  文件数与总字节；与本地 `datasets/cat_raw/manifests/verification.json` 中的清单逐项对齐，输出差异表。
  不写入源侧任何文件。
- **旧路径 provenance**：取回服务器绝对路径版标注与映射报告，存入 `datasets/cat_raw/manifests/provenance/`，
  记录来源路径、取回时间、SHA-256；取不到时在报告中登记为**缺失项**并标注原因。
- **产物位置**：报告写 `results/datasets/verify_cat_dataset_provenance.md`（不入 Git 之外的散落路径），
  清单与哈希写同目录 JSON。
- **验收**：报告列出复查表的逐项结论（一致 / 差异 / 缺失），缺失项有明确原因；不修改归档副本、不重跑恢复。
