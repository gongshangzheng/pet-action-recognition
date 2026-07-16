# third_party — 外部依赖（vendor 进仓库）

本目录存放 vendor 进仓库的外部依赖（非 git submodule，文件直接纳入本仓库版本控制）。

## mmaction2

- 来源：https://github.com/open-mmlab/mmaction2
- 版本：HEAD `a5a167dff2399e2d182a60332325f9c0d4663517`（shallow clone，2026-07-13 拉取）
- 目录：`third_party/mmaction2/`
- 许可：见 `third_party/mmaction2/LICENSE`（Apache-2.0）

### 为什么 vendor 而非 submodule
按项目决策「vendor 克隆进仓库」：文件直接进本仓库历史，不依赖 `git submodule update`，CI/协作者 clone 即得。代价是升级需手动重拉。

### 如何升级 mmaction2
```bash
# 重新 shallow clone 覆盖
rm -rf third_party/mmaction2
git clone --depth 1 --single-branch https://github.com/open-mmlab/mmaction2.git third_party/mmaction2
SHA=$(git -C third_party/mmaction2 rev-parse HEAD)
rm -rf third_party/mmaction2/.git
# 更新本文件的「版本」行 + LICENSE 行，然后：
git add third_party/mmaction2 third_party/README.md
git commit -m "chore: 升级 mmaction2 vendor ($SHA)"
```

### 如何使用
见 `.claude/skills/using-mmaction2/SKILL.md`（安装、训练、config 系统、适配我们的数据集与模型 registry）。
