# Tasks: verify-cat-dataset-provenance

> 前置：可用连接（云电脑会话或源服务器可读通道）。无连接时本 change 保持未开工，不得以推断代替取证。

- [ ] 在云电脑内或可用连接中**只读**复查源文件、目录、权限和当前实际数量，与本地 `verification.json` 清单对齐差异并记录。
- [ ] 在可用时恢复旧路径版标注/映射报告作为 provenance 附件，保存来源路径、时间与 SHA-256；并在报告中记录缺失项及原因。
- [ ] 产出复查报告 `results/datasets/verify_cat_dataset_provenance.md`（逐项一致 / 差异 / 缺失），不修改归档副本。
