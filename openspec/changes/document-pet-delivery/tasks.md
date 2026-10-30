## 1. 文档

- [x] 1.1 在 `AGENTS.md` 的「### Git 工作流」下新增「#### 交付到 pet」小节（push pet → 远程校验 commit；禁 rsync/scp；临时产物只进远程 `tmp/`；连接细节留在 `~/.ssh/config`）
- [x] 1.2 与「服务器/产物纪律（硬规则）」交叉引用，避免两处规则冲突或重复（第 3 条显式指向该节第 1、2 条）

## 2. 验证

- [x] 2.1 复查 `AGENTS.md` 中 `pet` 相关表述一致：remote 名 `pet`、目标 `pet:pet-action-recognition`、不出现硬编码 IP/密钥（`git remote -v` 核对）
- [x] 2.2 确认没有与既有「绝不在本地跑训练/测试/推理」条目矛盾

## 3. 交付

- [x] 3.1 提交 `docs: 补充交付到 pet 的 Git 规则` 并推送 `origin/main`
- [x] 3.2 若本次改动只涉及文档，按项目惯例不触发远程部署；推送后校验 `origin/main == HEAD`
