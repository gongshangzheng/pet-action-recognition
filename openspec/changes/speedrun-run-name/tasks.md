# speedrun-run-name Tasks

## 后端

- [x] **T1** `server/routers/speedrun.py`
  - `/results` 读取时对缺 `run_name` 的记录补 `run_name="legacy"`（内存中，不回写）
  - `/results` 支持 `?run_name=` 过滤
  - `/run` 请求体接受可选 `run_name`，未传时生成 `{dataset}-{YYYYMMDD-HHmm}`，写入每条结果

## 前端

- [x] **T2** `web/src/views/training/SpeedRun.vue`
  - 筛选区新增「运行批次」下拉框（选项从 results 的 run_name 去重）
  - filteredResults / accuracy 等统计纳入 run_name 条件
- [x] **T3** `web/src/api/training.js`：`getSpeedrunResults` 支持 run_name 参数（如需要）

## 数据补标

- [x] **T4** 一次性脚本：为 pet 上 303 条 cats 结果（video 路径含 `quadruped_cats_v1`）写 `run_name="cats-v1-speedrun"`，rsync 回本地

## 验证

- [x] **T5** 重启 pet 后端，页面验证：批次筛选器出现 `cats-v1-speedrun` 和 `legacy`，选中后统计正确
