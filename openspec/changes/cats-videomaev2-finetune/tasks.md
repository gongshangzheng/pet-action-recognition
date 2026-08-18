# cats-videomaev2-finetune Tasks

## 1. Config 与注册

- [x] 1.1 新建 `configs/cats_videomaev2_base_16x4.py`：克隆 `configs/pet_mammal_videomaev2_base_16x4.py`，改 `num_classes=5`、数据集段指向 `datasets/cats`（annotation/{train,val,test}_public.txt，data_root=数据集根）、`train_cfg.max_epochs=25`、VisSamplesHook 的 dataset 参数对齐 cats
- [x] 1.2 `server/routers/training.py` `_MMACTION2_REGISTRY` 重新注册 `videomaev2-base`（id/name/family/backbone/pretrained_source/pretrained_url=K710 蒸馏 URL/mmaction2_config="configs/cats_videomaev2_base_16x4.py"/description 注明"自写 finetune config，勿用 --pretrained 模式"）
- [x] 1.3 本地验证：`python3 -c "from mmengine.config import Config; c=Config.fromfile('configs/cats_videomaev2_base_16x4.py'); assert c.model.cls_head.num_classes==5 and c.optim_wrapper.optimizer.lr==1e-4"` + `GET /api/training/models` 含新条目（隧道通 pet 后）

## 2. 训练执行（pet）

- [x] 2.1 rsync 代码到 pet + 重启 uvicorn；确认 `checkpoints/videomaev2-base/videomaev2-base_pretrained.pth` 存在、GPU 0 空闲
- [x] 2.2 触发训练：`POST /api/training/run`（model_id=videomaev2-base, dataset_id=quadruped_cats_v1, epochs=25, lr=1e-4, batch_size=2, num_clips_val=1, device=cuda:0），**不传 pretrained/load_from**（实际 device 传 cuda；另修两处暴露的 bug：train_model.py override 变量未传入 build_train_command、training.py _num_classes 未按 dataset_id 解析）
- [x] 2.3 监控前 2 个 epoch：loss 下降、无 shape/NaN/显存 OOM；异常则中止并修 config（epoch1=56.8% → epoch2=68.2% → epoch3=73.9% → epoch4=76.1% 峰值，后续过拟合回落；loss 1.59→0.0006 无 NaN；显存 6.1GB）

## 3. 验证与收尾

- [ ] 3.1 训练跑完：确认 `metrics.json` 该 run status=completed、val top1 记录在案；记录 best epoch 与耗时
- [ ] 3.2 结果对比：val top1 vs SlowOnly 67.05% / TSM 62.5% / TimeSformer 59.09%，写入 t12 任务 progress（结论：VideoMAEv2 路线保留/排除）
- [ ] 3.3 文档同步：training / using-mmaction2 skill 中"VideoMAE 不可训练"表述更新为"videomaev2-base 已恢复（自写 config，见 configs/cats_videomaev2_base_16x4.py）"
