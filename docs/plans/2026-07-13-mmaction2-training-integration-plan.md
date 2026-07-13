# 实施计划 — mmaction2 训练集成（steps 3–5）

> 接续 2026-07-13 完成的 step 1（拉取并适配上游训练脚手架，commit `8eae2be`）与 step 2（vendor mmaction2 + `using-mmaction2` skill，commits `9ea90e1` / `ce299d7`）。本文档覆盖剩余三步：模型 registry、数据集 loader、训练 run 接线 + web 展示。

## 现状基线

- `server/routers/training.py` 已是 pet-action 下游版：`DEFAULT_MODELS` 仅 2 条代表（tsn-resnet50 / slowfast-resnet101），`DEFAULT_DATASETS` 一条四足占位（`QUADRUPED_DATASET_NAME="quadruped_action"`，`status="pending_collection"`），`POST /run` 仍为模拟响应。
- `server/config.py` 已有 `QUADRUPED_DATASET_NAME` / `QUADRUPED_DATASET_DIR` / `TRAINING_*` / `CHECKPOINTS_DIR` 变量；`server/utils/file_utils.py` 已 port `safe_resolve`。
- `third_party/mmaction2/` 已 vendor（sha `a5a167d`）。
- web 训练 5 子页 + 路由 + 菜单已就位；`TrainResults.vue` 已按 `metrics.json` 契约画 loss 曲线 / 列 run（上游脚手架已接好，**无需改前端**）。

## 决策回放（来自本轮 brainstorm）

1. mmaction2 = vendor 进仓库（非 submodule、非 pip）。
2. 「每一个模型」= **按模型族注册一个代表 config**（非全量上百 config）。
3. 四足数据集 = 尚未收集，**先搭 loader 骨架 + 占位 annotation**，名称做成变量。
4. 本轮只做 1+2，再出本计划。

---

## Step 3 — 模型族 registry（按 configs/recognition 注册代表）

### 3.1 目标
把 `configs/recognition/` 下 19 个模型族各注册一个代表进训练 registry，前端「模型配置」页可列、可被 `POST /run` 选中触发训练。

### 3.2 设计：registry 从 `DEFAULT_MODELS` 抽出到独立模块
- 新建 `evaluation/models/registry.py` —— `MODEL_REGISTRY: list[dict]`，每条 shape：
  ```python
  {
    "id": "tsn-resnet50",
    "name": "TSN (ResNet-50)",
    "family": "TSN",
    "backbone": "resnet50",
    "mmaction2_config": "configs/recognition/tsn/tsn_imagenet-pretrained-r50_8xb32-1x1x3-100e_kinetics400-rgb.py",
    "pretrained_source": "mmaction2",
    "num_classes_default": 400,        # kinetics400；四足数据集到位后覆盖
    "trained_checkpoint": None,
    "description": "...",
  }
  ```
- `server/routers/training.py` 的 `DEFAULT_MODELS` 改为 `from evaluation.models.registry import MODEL_REGISTRY` 并在 `get_models` 返回；保持现有端点契约不变。

### 3.3 注册清单（19 族，每族挑 kinetics400-rgb 代表 config）
见 `using-mmaction2` skill §7 表格。逐族确认 config 文件存在后落 registry 条目：
TSN / TSM / I3D / C3D / SlowFast / SlowOnly / R(2+1)D / CSN / TIN / TRN / TPN / Tanet / TimeSformer / MViT / Swin / X3D / Uniformer / VideoMAE / VideoMAEv2。

> 不在 mmaction2 的模型（VideoMamba / SkeleTR / PMTNet / InternVideo2）单列 `external_models`（占位 + 来源 repo 链接），标记 `status: "out_of_scope"`，不在本轮集成。

### 3.4 数据集类别注入
- registry 条目带 `num_classes_default`；`POST /run` 时按选中 dataset 的实际 `num_classes` 覆盖 config（写临时 config 或用 `--cfg-options model.cls_head.num_classes=N`）。
- mmaction2 `tools/train.py` 支持 `--cfg-options`，无需改源码。

### 3.5 验证
- `python -c "from evaluation.models.registry import MODEL_REGISTRY; assert len(MODEL_REGISTRY)==19"`
- `GET /api/training/models` 返回 19 条；前端「模型配置」页可渲染。
- 抽 1 个族（TSN）用 kinetics400 tiny 子集（或 4 条样本）跑 `tools/train.py` 1 epoch 冒烟，确认 config 路径解析正确。

---

## Step 4 — 四足动物数据集 loader 骨架

### 4.1 目录结构（数据未到位，先建骨架 + 占位）
```
datasets/
└── quadruped_action/                      # = QUADRUPED_DATASET_NAME 变量值
    ├── README.md                           # 数据集说明、类别清单占位、采集规范
    ├── videos_train/  videos_val/  videos_test/   # 空目录（.gitkeep），数据到位放这里
    ├── quadruped_action_train_list.txt     # 占位空文件；mmaction2 VideoDataset ann_file
    ├── quadruped_action_val_list.txt
    ├── quadruped_action_test_list.txt
    └── label_map.txt                       # 类别 id↔name（待定，先放 TODO）
```
> 数据本体（视频/帧）不入 git（`.gitignore` 追加 `datasets/*/videos_*/` 与 `*.mp4` 等大文件），只提交结构 + 占位 list + README。

### 4.2 mmaction2 数据集 base config
- 新建 `evaluation/configs/dataset_quadruped.py`：`dataset_type='VideoDataset'`、`data_root`/`ann_file_*` 指向 `datasets/quadruped_action/`、`train/val/test_pipeline` 复用 kinetics 默认（按需调 `clip_len`/`input_size`）。`num_classes` 留占位变量 `num_classes = 0  # TODO: 数据集类别确定后填`。
- 每个模型族 config 可 `custom_imports` 或 `_base_` 继承此 dataset base —— 但更简洁的做法是 `POST /run` 时用 `--cfg-options` 注入 dataset 路径，避免为 19 族各写 dataset 覆盖。

### 4.3 `DEFAULT_DATASETS` 完善
- `training.py` 的四足条目补 `num_classes`(待定→0)、`ann_file`/`root_dir` 路径、`label_map` 引用，保持 `status="pending_collection"` 直到数据到位。

### 4.4 验证
- `datasets/quadruped_action/` 结构完整、占位 list 可被 `mmaction.datasets.VideoDataset` 实例化（空 list 不报错，仅样本数为 0）。
- `GET /api/training/datasets` 返回四足条目含正确路径变量展开。

---

## Step 5 — 训练 run 接线 + web 展示

### 5.1 `POST /run` 实接（替换模拟响应）
`server/routers/training.py` `run_training` 改为：
1. 解析 body：`model_id` / `dataset_id` / `config_id`（超参 preset）。
2. 在 registry 找 model → 拿 `mmaction2_config` 路径；拼 `--cfg-options`：`model.cls_head.num_classes=<dataset.num_classes>`、`train_dataloader.batch_size`、`optim_wrapper.optimizer.lr` 等（来自 config preset）。
3. `subprocess.Popen` 异步跑 `python third_party/mmaction2/tools/train.py <cfg> --work-dir results/training/runs/<run_id>`；立即返回 `status="pending"` + `run_id`。
4. 后台任务跑完后（用 lightweight 轮询/线程/独立 worker）：
   - 最新 `epoch_*.pth` → 软链/拷贝到 `results/training/checkpoints/<run_id>.pth`
   - 解析 `results/training/runs/<run_id>/vis_data/scalars.json` → `loss_series`（loss/epoch）+ 末值 `metrics`
   - 追加 run 到 `results/training/metrics.json`（见 skill §5 shape），status 标 `completed`/`failed`

### 5.2 异步执行选型（待定，建议）
- **方案 A（推荐）**：`POST /run` 写一个 `runs/<run_id>/run.sh` + nohup 后台拉起，立即返回；前端轮询 `GET /runs/{run_id}` 看 status。简单、可重启。
- **方案 B**：FastAPI BackgroundTask。但与 uvicorn worker 模型耦合，重启丢任务。
- 计划阶段定 A；实现时若需更健壮可换 RQ/celery（超出本轮）。

### 5.3 web 展示（已就绪，仅校验）
- `TrainResults.vue` 读 `metrics.json` → loss 曲线 + run 表。**无需改前端**。
- `TrainRun.vue` 选 model/dataset/config → `POST /run` → 跳结果页。检查其 POST 字段与 5.1 body 契约一致（model_id/dataset_id/config_id）。

### 5.4 验证
- 用 TSN + 四足占位（或 kinetics tiny 4 样本）触发一次 `POST /run`，确认：
  - `results/training/runs/<run_id>/` 生成 log + checkpoint
  - `results/training/metrics.json` 多出一条 run，`loss_series` 非空
  - 前端「训练结果」页显示该 run + loss 曲线
  - `GET /api/training/outputs/checkpoints/<run_id>.pth` 可下载（safe_resolve 守卫生效）

---

## 顺序与里程碑

1. **Step 4 先于 Step 3 完整落地**：模型 config 需要 dataset 路径与 num_classes，先把数据集骨架 + base config 建好。
2. Step 3 registry → 抽 1 族冒烟 → 全量 19 族。
3. Step 5 接线 → 单族冒烟 → web 端到端。

## 风险
- **num_classes 待定**：数据集类别未定前，`POST /run` 实跑会失败（num_classes=0）。冒烟用 kinetics400 tiny 子集验证流程，四足数据到位再切。
- **decord/macOS**：本地冒烟若 decord 不可用，改 PyAV 后端。
- **mmcv 版本**：`mim install "mmcv>=2.0.0"`，避免误装 mmcv-full。
- **vendor 升级**：改 `third_party/mmaction2/` 源码会被升级冲掉 —— 优先用 config 覆盖与 `evaluation/` 子类，源码改动记录在 `third_party/README.md`。
- **大文件入 git**：`datasets/*/videos_*` 与 `*.pth` checkpoint 必须在 `.gitignore`（checkpoint 已在 `results/training/checkpoints/` 但 `results/` 未整体 ignore —— 需补 `results/training/checkpoints/*.pth`、`results/training/runs/`）。

## 不做（YAGNI）
- 全量上百 config 注册（按族代表即可）。
- VideoMamba/SkeleTR/PMTNet/InternVideo2 集成（外部库，另开计划）。
- 分布式训练 UI（dist_train.sh 暂不在 web 暴露）。
- 训练超参 preset 的全量编辑器（先复用 `DEFAULT_CONFIGS`，前端已有脚手架）。
