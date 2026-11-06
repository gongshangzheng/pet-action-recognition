# 实验证据

### 2026-11-04：漏检时保持平滑裁剪（本地验证）

- 用户要求漏检时裁剪框平滑变化，禁止突然切到完整画面。检查发现不同物种锚点之间未补显示框，仍会触发整帧回退。
- 显示轨迹在不同物种锚点之间保持前框，同物种缺口使用 smoothstep 插值；所有显示帧使用系数 0.2 的指数平滑。有效与无效渲染分支共用显示轨迹，严格训练资格不变。
- 专项测试 34 passed、3 subtests passed，OpenSpec strict validation 与 diff 检查通过。修改尚未部署，现有远程审阅视频不包含本次平滑；平滑系数和视觉效果仍待小批验证。

### 2026-11-03：实验启动与资产核验（`gdino-crop-20261103a`）

- **skill 闸门**：已加载 `openspec-apply-change`、`experiment`、`remote-ops`、`training`、`testing`、`datasets`、`remote-server-discipline` 和 `remote-servers`。
- **批准范围**：用户指示开始推进远程实验。沿用 change 中的 A 原视频、B GroundingDINO 空间裁剪、C 相同检测缓存加像素运动校正三臂，七个类别、日期隔离划分、共同样本和测试前冻结规则不变。
- **远程路径**：`/home/wyy/pet-final-1` 不存在；`/home/wyy/pet-final-v1` 存在且是独立 Git worktree，`/home/wyy/pet-final` 是主工作树。旧报告所述共享数据、索引、权重和结果的链接关系成立。
- **资源预检**：2026-11-03 20:00（Asia/Shanghai）GPU 0 有 Python 进程占用约 14,842 MiB；GPU 1 为 0 MiB 且利用率 0%，load 5.72/24 核，可用内存约 113 GiB，根盘剩余约 68 GiB。实验固定使用 GPU 1，每次重活前重新预检。
- **数据**：`cat_raw` 为 2,737 个视频、9.4 GiB；源区间表哈希为 `80da23af3c6a6db4bac739fc2c1dc8714b8b5dc063b55abe7c9762932eeb04ff`。
- **索引**：train/val/test 为 1,664/604/442，哈希分别为 `073350c27fbda36c4a931fb0852f20a495023cfe7298e2350c677dfa9962751c`、`21b7bb44d8450d210bb9a73d9f951ec8e3a571ab97a79e379d5b487c6e2eb1d6`、`058c08bcd78554d70714533140d712c8e1db50c5398d199d711be61653d4096e`，与历史记录一致。
- **历史锚点**：旧七类 VideoMAEv2-B 最佳 checkpoint 为 epoch 12，SHA-256 `39a1baa176d66b85244dde40521b11d05ed84f5a4815d64038122454c0e518ae`；历史 val top-1/macro-F1 为 85.93%/70.97%，test 为 81.90%/67.66%。这些是既有测试集复验锚点，不是本轮结果。
- **目标有效性**：区间内出现无可靠猫检测、超过两个检测步长的缺口、多猫目标不明或狗时，保守排除并记录原因。像素低运动不用于判定无猫；当前检测结果也不能区分真实无猫与探测器漏检。
- **下一步**：实现低内存检测、B/C 同步渲染、共同索引、三臂训练与冻结评测；先做单视频烟测和用户可见的小批质检，不直接启动 20-epoch 全量训练。

### 2026-11-03：20 段 GroundingDINO 裁剪小批验证（`gdino-crop-20261103a`）

- **skill 闸门**：已加载 `experiment`、`remote-ops`、`remote-server-discipline` 和 `documentation`。
- **实验类型**：感知质量与正确性小批验证。A 原视频、B GroundingDINO 空间裁剪、C 同一检测缓存加像素运动辅助；本轮没有训练模型。
- **样本与冻结**：20 个训练集唯一视频区间，覆盖七类且包含短、长、夜间候选。抽样在检测前冻结，训练索引 SHA-256 为 `073350c27fbda36c4a931fb0852f20a495023cfe7298e2350c677dfa9962751c`。
- **实现提交**：`5e4c3ab` 实现配对实验与测试，`78d863f`、`a8b0784`、`0014200`、`b488f7d`、`c77748b` 修复索引、烟测、线程上限与背景处理问题，`8c85462` 冻结抽样和匿名 QC 图，`252352a` 将 QC 图改为流式组装以消除内存累积。最终远程 HEAD 与分支 HEAD 均为 `252352a`。
- **代码核验**：远程 26/26 pytest 通过；静态审计为 0 high、0 medium、0 low；渲染峰值约 199% CPU、1.38 GiB RSS，QC 拼图峰值约 201% CPU、235 MiB RSS。
- **媒体结果**：20/20 段完成 GroundingDINO 检测与 B/C 同步渲染，20/20 通过帧数、FPS、512×512 尺寸、源/输出哈希和轨迹长度审计。媒体链路通过不代表裁剪目标或构图可用。
- **目标有效性**：20 个预选区间只有 Q006 的 activity 区间满足严格单猫规则；其余 19 个中，多猫目标不明 5 个、狗在场 7 个、无可靠猫检测 7 个。共同索引在同源视频找到另一个相邻 eating 区间，共 2 个区间，但只有 Q006 属于本轮预选样本；同一视频、两个类别不足以训练七类模型。
- **帧诊断**：20 个源视频共 12,174 帧，其中 3,296 帧有效、8,878 帧无效，无效比例为 72.93%；731 帧触发像素运动辅助，占 6.00%。这些数字描述整段源视频，不是人工动作区间准确率或产品漏检率。
- **逐图预检**：Q001 的 B/C 在检查帧全为灰帧；Q003 三帧可看到猫但整区间仍因狗在场被判目标不明；Q006 是唯一严格可用预选样本，但源水印被放大；Q012 构图过紧并切掉身体；Q016 裁到猫和食盆但水印明显；Q020 主要框住笼子，前景大猫未稳定被扣住。用户最终逐例审核仍待完成，`review_form.csv` 保持空白。
- **失败边界**：`no_reliable_cat_detection` 同时包含真实无猫与探测器漏检，不能解释为已确认无猫。多猫或狗场景在缺少目标身份依据时只能排除。媒体审计无法发现身体切边、目标误裁和源水印放大。
- **结论上界**：当前只确认 GroundingDINO 裁剪和 B/C 媒体链路在小批上可运行，不能确认裁剪提高 VideoMAEv2 准确率。目标有效性和构图质量不足以扩到全量，也未启动训练或测试。
- **报告**：`management/experiments/cat-crop-classification/20261103-gdino-crop-20261103a/`，`status=partial`、`verdict=inconclusive`，生成器完整度检查为 0 项缺失。

### 2026-11-04：人工审阅页与三路媒体成品（`gdino-crop-20261103a`）

- **目的**：让用户在同一页面同步播放原始、GroundingDINO 和像素运动辅助三路视频，逐段记录合格、不合格或待复查，并可标记身体切断、裁错目标、跳猫/漂移、抖动、灰帧、水印、多猫、狗和未可靠检出猫等问题。
- **实现**：`0459d1f` 增加审阅集导出、三路播放器、报告页入口、视频接口与 pass/fail 标签；`186508b` 修复 pet Python 3.10 兼容；`6a05547` 修复新版 ffmpeg 的填充色参数；`1b87d79` 增加 60 个成品的帧数、尺寸、FPS、时长和哈希审计；`bb08317` 为变帧率源视频逐帧写入等间隔时间戳。
- **帧时间轴缺陷与修复**：首次审计发现 Q005 清单为 181 帧，原始导出版本因 VFR 时间戳被补帧到 198 帧，而 B/C 为 181 帧。根因是不能在抽样后用平均 FPS 强制输出；现改为按选中源帧生成等间隔时间戳并使用 passthrough，重导后三路均为 181 帧。Q005 若未修复会破坏同步与人工判断，因此这批初版作废。
- **测试**：远程相关测试最终为 29 passed、3 subtests passed；新增审阅集、接口和审计测试随后为 4 passed。前端 `npm run build` 通过，静态审计为 0 high、0 medium、0 low。
- **资源**：生成 20 段、60 个视频耗时约 26 秒；最终守卫峰值约 320% CPU、457 MiB RSS，GPU 未参与。第一次以 250% CPU 上限运行时被守卫终止，按项目默认 350% 上限、低优先级和看门狗重跑完成。
- **成品审计**：远程和本地均对 20/20 段、60/60 视频审计通过。三路均为 512×512，帧数等于区间标注，三路时长与 FPS 一致，清单路径无缺失或额外文件，SHA-256 已记录到 `audit.json`。来源抽样 SHA-256 为 `59f34896cbb682a4ccc117f088198bd8bd0f2b28f37c58446733042215dc4344`。
- **浏览器验收（初版）**：页面实际加载 20 段审阅集，Q001 的三路视频均完成加载且无媒体错误。并排首帧可见；从原始视频播放约 0.46 秒时，三路的 currentTime 分别为 0.4604、0.4481、0.4481 秒，说明原始视频能带起另外两路。该结果没有证明 B/C 能独立打开；用户随后反馈 B/C 没有可见播放控件。
- **样本覆盖**：abnormal 4、activity 4、eating 3、grooming 3、prolonged_stationary 2、drinking 2、toileting 2；按严格规则仅 1 段可用，其余不是质量合格证据。
- **产物**：本地 `results/gate/review/cat-crop-gdino-20261103a-sample20-v1/`；远程 `/home/wyy/pet-action-recognition/results/gate/review/cat-crop-gdino-20261103a-sample20-v1/`。报告详情页与侧栏均提供“裁剪人工审阅”入口。
- **当前结论**：工程链路、同步播放和三路媒体一致性已通过自动核验；人工裁剪质量、目标归属和“是否适合训练”仍未确认。`labels.csv` 尚未生成，任务 3.2 保持未完成，不能据此启动全量裁剪、VideoMAEv2 训练或准确率评测。

### 2026-11-04：三路播放器独立打开（`gdino-crop-20261103a`）

- **skill 闸门**：已加载 `experiment` 和 `web`。
- **用户反馈**：“只有原始视频能打开”。浏览器检查确认三路视频都完成了媒体加载，但初版只给 `raw` 设置了浏览器原生 `controls`；B/C 只能被原始视频的程序化同步带起，不能独立操作。
- **修复**：三路播放器都显示原生播放、暂停、静音、全屏和时间轴控件。三路互为播放源的事件同步曾造成播放器事件环并让浏览器无响应，该方案已删除；当前三路独立播放，人工拖动到同一时刻比较。
- **构建**：`npm run build` 通过，仅有既存的大 chunk 警告。
- **浏览器实测**：Q001 的三个 `<video>` 均为 `controls=true`、`readyState=4`、无媒体错误。GroundingDINO 和像素运动辅助两路都实际播放到 `4.27 s` 结束；点击各自时间轴后都回到约 `2.13 s`，页面没有卡死，浏览器控制台没有 error 或 warning。
- **失败边界**：Q001 的 B/C 仍是灰色无效帧，这是该区间多猫、目标归属不明导致的裁剪输出，不是播放器故障。媒体可播放不等于该段裁剪合格。
- **对旧结论的更正**：此前“同步机制工作”只证明原始视频可以程序化带动 B/C；修复后证明三路可以各自播放和定位。人工 A/F/U 结论仍未填写，任务 3.2 保持未完成。

### 2026-11-04：远端审阅服务与无效帧回退修复（`gdino-crop-20261103a`）

- **skill 闸门**：已加载 `experiment`、`web`、`remote-ops` 和 `remote-server-discipline`。
- **运行架构**：审阅后端在 pet 的 `/home/wyy/pet-action-recognition` 中运行，监听 `127.0.0.1:8788`；本地 Vite 只提供前端，本地 `127.0.0.1:8788` 是 SSH 隧道。浏览器按需从 pet 流式读取视频，本地仓库不再保存这套审阅视频。本地 `results/gate/review/cat-crop-gdino-20261103a-sample20-v1/` 已删除。
- **灰色根因**：GroundingDINO 并没有漏检 Q001。检测缓存每 10 帧稳定识别到两个猫框，最高置信度约 `0.47–0.61`。旧渲染器把“多猫导致训练目标不唯一”的严格资格规则直接用于画面生成，将全部无效帧写成固定 `BGR(114,114,114)`。因此灰色是渲染策略 bug，不是检测为空或播放器故障。
- **修复设计**：训练资格仍由 `camera_box` 和 `valid` 控制，多猫、有狗或无可靠检测继续排除，不污染训练索引；审阅显示增加独立 `display_box`。每个无效帧优先显示当前最高置信度猫框，完全无猫框时显示完整原画的黑边等比 letterbox，不再输出空白灰帧。
- **实现提交**：`20d6419` 增加显示框与回退渲染，`af71f03` 移除对系统 `ffprobe` 的依赖，`73440db` 复用 `imageio_ffmpeg` 的 bundled ffmpeg，`a619cd3` 修复脚本直接执行时的项目模块路径。
- **资源**：首轮 250% 和 350% 守卫分别采样到 `307%`、`492%`，均被正确终止且旧产物未被替换。把 OpenCV、Torch、FFmpeg 线程都限制为 1 后，Q001 烟测峰值约 `272% CPU / 1.87 GiB RSS`；其余 19 段约 595 秒完成，峰值约 `272% CPU / 1.94 GiB RSS`，未使用 GPU。
- **回退统计**：20 个源视频共 12,174 帧，严格无效帧 8,878。其中 2,938 帧使用最高置信度猫框显示，5,940 帧因没有猫框而显示完整原画。像素运动辅助校正仍为 731 帧。这里的数量描述完整源视频，不是审阅区间样本。
- **Q001 验证**：381 个完整源视频无效帧中，377 帧改用最高置信度猫框，4 帧使用原画 letterbox。抽查第 1、33、65 帧的 GroundingDINO 输出标准差分别为 `31.50`、`29.27`、`41.49`，不再是零方差灰帧。
- **媒体审计**：重新剪出 20 段、60 个审阅视频后，20/20 段的帧数、FPS、512×512 尺寸、时长、声明路径和 SHA-256 全部通过 OpenCV 媒体审计。审阅集选择 SHA-256 仍为 `59f34896cbb682a4ccc117f088198bd8bd0f2b28f37c58446733042215dc4344`。
- **浏览器验收**：页面恢复显示 20 段；Q001 三路均有原生控件且 `readyState=4`。B/C 首帧和中段均能看到猫和房间，B 拖到约 `2.075 s` 后播放至 `2.726 s`，C 从约 `2.104 s` 播放至 `2.755 s`，另外两路保持暂停。页面自身无 console、网络或媒体错误，三个 `video.error` 均为 `null`。
- **对旧结论的更正**：此前“Q001 的 B/C 灰帧是裁剪输出，不是播放器故障”只对旧渲染器成立，现已撤回该解释。新的正确表述是：旧代码主动写入了灰帧，属于可修复的渲染 bug；多猫仍是训练资格失败原因。
- **当前结论**：远端审阅服务、三路播放和媒体链路已恢复；灰色无效帧问题已修复。修复只改善可视化，不会让原本被严格规则排除的多猫片段进入训练，也不能据此判断裁剪构图已经合格。人工 A/F/U 审核仍未完成，VideoMAEv2 训练与准确率评测未启动。

### 2026-11-04：裁剪审阅合格快捷键改为 A（`gdino-crop-20261103a`）

- **用户决定**：裁剪合格的快捷键使用 `A`。裁剪审阅模式现为 `A` 合格、`F` 不合格、`U` 待复核，页面提示和按钮文字同步更新。普通图片与视频审阅的既有快捷键保持不变。

### 2026-11-04：第一阶段单宠物物种标注

- **用户决定**：第一阶段处理单一宠物目标。单猫记录为猫，单狗记录为狗并按该目标裁剪；多宠物场景暂不生成多目标子视频，后续另行研究 SORT 关联。
- **实现**：帧资格从“单猫且无狗”改为“宠物总数为 1”。每帧记录 `target_class`、`target_box` 和宠物计数；多宠物统一记为 `multi_pet_unsupported`，无检测记为 `no_reliable_pet_detection`。旧猫缓存仍可读作猫目标，避免历史数据直接失效。
- **安全**：检测缓存 schema 升级为 v2，渲染指纹包含单宠物策略，避免旧规则产物被当作新规则结果复用。已有输出与源或渲染参数不匹配时，脚本拒绝覆盖；已有数据集根目录非空时也拒绝覆盖。只有显式 `--force` 才允许重建。
- **路径**：准备脚本和抽样脚本移除了远程绝对路径默认值。运行时必须通过参数或 `CAT_ACTION_INDEX_ROOT`、`CAT_ACTION_VIDEO_ROOT`、`CAT_ACTION_TRAIN_INDEX` 提供路径。
- **测试**：全仓 Python 测试通过，68 个测试和 3 个 subtests；裁剪专项最终为 32 个测试和 3 个 subtests，覆盖单狗、跨物种插值阻断、多宠物、旧缓存兼容、路径必填和不匹配输出拒绝覆盖。

### 2026-11-04：单宠物规则 20 段复验（`sample20-v2`）

- **执行环境**：远程 HEAD 先后核验为 `3dea80e`、`5863b4a`、`9dc554f` 和 `e384bb3`；预检两块 GPU 空闲、load 约 1.1 到 2.6、可用内存约 119 GiB。GroundingDINO 使用 `plf` 环境；首次尝试 `pet` 环境因缺少 `transformers` 在模型加载前失败，未产生检测产物。
- **检测与渲染**：20/20 段检测缓存、40 个 B/C 全长输出和 60 个三路审阅短视频生成完成。检测峰值约 159% CPU、1.87 GiB RSS；渲染峰值约 161% CPU、1.04 GiB RSS；审阅集导出峰值约 118% CPU、581 MiB RSS。
- **媒体审计**：20 个源视频与 B/C 输出通过帧数、FPS、512×512、轨迹长度和 SHA-256 审计；三路审阅集 20/20 段、60/60 个媒体通过帧数、时长、FPS、路径清单和哈希审计。
- **区间资格**：这 20 个唯一视频共对应 31 个训练区间。预选 20 个区间中，1 个可用，13 个因多宠物不支持排除，6 个因无可靠宠物检测排除；可用样本仍为 Q006。同一批视频的全部 31 个区间中共 2 个可用，均为猫目标，类别仍只有 activity 和 eating。
- **物种统计**：1,226 个抽样检测状态中，389 个为单一猫、334 个为单一狗、428 个多宠物、75 个无可靠检测。整段 12,174 帧中 5,844 帧有效、6,330 帧无效；有效帧包含 389 个猫锚点、334 个狗锚点和 5,121 个插值帧。像素辅助触发 1,413 帧。
- **索引修复**：`sample20-v2` 和 `sample20-v3` 曾错误把全量 2,710 个区间写入小批 manifest，并标为 `training_ready=true`；两者保留为失败记录。修正后的 `sample20-v4` 只含 31 个候选区间，`source_rows=31`、`eligible_rows=2`、`training_ready=false`。
- **产物**：检测与渲染在远程 `results/cat_crop_classification/gdino-crop-20261103a/assets/sample20-v2/`；正确索引和汇总在 `quality/sample20-v2/` 与 `quality/sample20-v4/`；人工审阅集为 `results/gate/review/cat-crop-gdino-20261103a-sample20-v2/`。
- **当前边界**：新规则显著提高了整段有效帧比例，但没有改变预选区间可用率；单狗锚点较多，而预选动作区间内仍因缺口或多宠物不可用。人工 A/F/U 审核未完成，不能扩量或启动训练。

### 2026-11-04：复用 follow_cam 修复（待远程验证）

用户批准先更新 change 再运行。当前实现提取旧相机的 5 帧滑动平均与半余弦运动偏移阻尼，首尾改为端点填充。有效/无效帧共享显示轨迹，资格规则独立；删除临时 EMA 0.2 审阅模式。项目测试 `python3 -m pytest tests -q` 为 80 passed、3 subtests passed，OpenSpec strict 和 diff 检查通过，静态审计无匹配风险项。误执行未限定目录的 pytest 收集到第三方模型测试并在本机 torch 导入时退出，未执行 GPU 推理；后续只运行项目 tests。

远程预检两 GPU 无计算进程，load 0.30/24 cores、可用内存约 119 GiB、磁盘余量 70 GiB。新批复用 v3 检测缓存，保持源视频与检测参数不变；媒体质量尚未确认。

对旧结论的更正：Q004 的 146 是 v2 区间内训练无效帧数，不是完整画面回退数；v3 的 16 是整个源视频的回退帧数。二者分母和含义不同，撤回“146 降至 16”的改善结论。v3 审阅 availability 曾借用 v2 索引，本批必须重新生成匹配当前媒体的索引，不能沿用旧资格统计。

代码审阅指出超大框被窗口截断、索引可混入旧媒体两项 HIGH，现均已修复并补回归。最终项目测试为 85 passed、8 subtests passed；超大窗口采用补边保持目标与比例，索引生成核验源、检测、渲染和媒体哈希。视觉效果仍待远程重渲染与用户确认。

部署提交 `4895963`，二次审阅无 CRITICAL/HIGH。首个烟测 `.run/guard/run-20261104-175934.log` 因 CPU 469% 超过 350% 被守卫终止，保留失败记录；重试设置 `OPENCV_FFMPEG_THREADS=1`、OpenCV/守卫线程为 1，保持原资源上限。代码回退：`git revert 4895963`。

单段重试完成 405 帧，CPU 峰值 233%、RSS 约 1.35 GiB，守卫日志 `.run/guard/run-20261104-180052.log`。随后启动 20 段重渲染，使用同样线程限制与 350% CPU/3 GiB RSS 上限；本轮不训练。

重渲染期间共享机 GPU1 出现外部计算进程（约 6.5 GiB 显存），GPU0 保持空闲。本任务仅 CPU 媒体处理，不进行性能比较；共享窗口资源记录不作为性能证据，后续 CPU 索引/审计/审阅导出前重新预检主机与 GPU0。

### 2026-11-04：follow_cam 重渲染完成（sample20-followcam-v1）

20/20 源视频、40 个 B/C 输出完成，12,174 帧，整批守卫日志 `.run/guard/run-20261104-180203.log`，运行 671 秒（含首段缓存复用），RSS 最高约 1.37 GiB。共享资源窗口不作为吞吐证据。20 段媒体审计 passed；本批严格索引 source_rows=31、eligible_rows=2、training_ready=false。新旧源哈希、检测指纹、检测状态及逐帧资格全部相同；有效帧 6,154，预选区间合格 1/20，显示缺框 0。像素辅助触发数 1,059 对旧批 1,061，仅为触发诊断，不代表收益。

轨迹 summary 仅量化元数据中的基础显示框，不是历史 B 实际路径或 C 最终偏移路径，不能作视觉稳定性验收。60 个审阅短视频已在远程生成，availability 来自本批索引。远程产物：`results/cat_crop_classification/gdino-crop-20261103a/quality/sample20-followcam-v1/{crop_audit.json,camera_summary.json,dataset/}`；审阅集 `results/gate/review/cat-crop-gdino-20261103a-sample20-followcam-v1/`。视频未下载本地。用户视觉审阅仍待完成，不扩量、不训练。

审阅媒体审计 `audit.json` 为 passed、count=20，60 文件全部通过；远程 API 返回 total=20，Q004 gdino 单字节 Range 请求返回 HTTP 206、video/mp4。HEAD 返回 405 是接口不支持该方法，不是媒体缺失。项目回归最终 87 passed、8 subtests passed；新增只读诊断脚本经审阅批准。

### 2026-11-06：全量预处理完成，训练启动后暂停

- **全量阶段**：远程 `~/pet-action-recognition/.run/logs/full_preprocessing.log` 记录 `Full preprocessing finished successfully!`。2,144/2,144 个源视频完成检测，B/C 各生成 2,144 个视频。索引共有 2,710 个原始区间、214 个三臂共同可用区间，train/val/test 为 137/33/44；媒体路径解析与三臂 sample_id、标签、帧区间一致性已现场核验。类别稀疏，尤其 val 没有 toileting 样本，结论受限。
- **训练入口修复**：`scripts/run_cat_crop_experiment.py` 指向全量索引与 `full_run` 资产根，提交 `e460e05`、`8472b30`。真实 batch 三臂前向/反向 smoke 均通过，显存峰值约 11.2 GiB；该 smoke 没有导入验证评测 metric。
- **环境问题**：pet 主训练环境缺少 `scikit-learn`，A 臂首次在 metric 模块导入时失败，状态和错误保留在远程 `results/cat_crop_classification/gdino-crop-20261103a/raw/`。复用已有 `plf` 环境通过 metric 导入、训练栈版本和 CUDA 检查，没有修改共享环境。
- **部分训练**：A 臂在 `plf` 中从 epoch 4 checkpoint 恢复，最高写出 `raw/work/epoch_8.pth`。训练进程后已停止，GPU 回到 1 MiB 空闲；8 epoch 不代表训练完成。B/C 尚未开始。初次中止后 A 臂状态 json 仍标记 `training`，后续修复使其可识别现有 checkpoint 并恢复。
- **守卫异常**：首次资源守卫因没有覆盖派生 worker 而留下训练孤儿；已按 PID 精确清理。守卫 CPU 读数之后出现负值，追查发现树内进程退出时累计 jiffies 回落。对守卫所做的后续进程组与单调时钟修复仅完成 shell 静态检查，远程 CPU-only 演练验证计时与退出清理，但没有完成对真实 worker 生命周期下 CPU 采样的可靠性验证。当前训练暂停，不能把现有守卫认定为已通过。
- **部署状态**：训练 runner/守卫修复提交已推至实验分支，远程 HEAD 为 `55c9789f5c9b3db7b8261b5bcfeb53f7c86d654a`。后续本地守卫工作树另有未提交实验性改动；不得直接运行，须完成测试、提交、push、核验远端 HEAD 后再恢复。
- **下一步**：改用可验证的进程组/资源统计机制，补一个会创建并退出多个 worker 的 CPU-only 远程测试；测试需断言 CPU 百分比非负、elapsed 合理、超限时整组无残留。通过后按 GPU 资源预检和守卫从 epoch 8 恢复 A，再串行完成 B/C。保留所有失败日志和 checkpoint，不覆盖既有产物。

### 2026-11-06：撤回 epoch 8 可完整续训判断

远程只读检查发现 `raw/work/epoch_8.pth` 仅含 `meta`、`state_dict` 和 `message_hub`，没有优化器和学习率调度器状态。基础配置显式设置 `save_optimizer=False`、`save_param_scheduler=False`；此前从 epoch 4 和 epoch 6 续跑因而没有恢复完整训练状态，相关日志中学习率重新出现 warmup 值。epoch 8 只能保留为失败/诊断产物，不能作为三臂对照实验的有效断点。须在独立结果目录重新从预训练骨干开始 A 臂，并为三臂保存优化器与调度器状态；先修复和测试守卫与训练入口，不能覆盖已有失败产物。原有“从 epoch 8 恢复 A”计划撤回。

### 2026-11-04：小批质量人工质检确认通过

- **用户审阅结论**：用户已完成 `sample20-followcam-v1` 小批审阅，确认 20 段样本全部通过（无身体切断、目标跟踪连续稳定）。
- **任务状态推进**：勾选并通过 Task 3.2、3.3 与 6.5，解除全量处理前置阻塞。
- **下一阶段执行规划**：推进 Task 3.4（全量 GroundingDINO 检测与裁剪资产生成）。
  - 全量涉及 `cat_action_v1`（包含 train 1,664、val 604、test 442，共 2,710 个动作区间），去重后对应 2,144 个源视频。
  - 远程 pet 当前 2× RTX 4090 D 均处于空闲状态（显存占用 1 MiB，GPU 0%），`/home` 磁盘余量 11 TB，资源充裕。

### 2026-11-06：计划与事实对齐（计划修订，无新实验）

- **触发**：evidence 已记录全量预处理完成与 A 臂暂停，但 tasks.md 仍有已完成项未勾选，proposal 仍写“全量数据和训练评测待完成”，design 仍写“全量生成和训练尚未启动”，三处与事实冲突。
- **勾选依据**：3.4 由“全量阶段”条目支持，2,144/2,144 检测完成、B/C 各 2,144 个视频；3.5 由同条目的 2,710 个原始区间、214 个共同可用区间及 137/33/44 划分、sample_id 与帧区间一致性现场核验支持，类别保留数缺口的说明保留在该条目中；4.4 由“训练入口修复”条目的三臂前向/反向 smoke 与约 11.2 GiB 显存峰值支持。
- **4.4 的限定**：该 smoke 没有导入验证评测 metric，metric 导入是其后在 `plf` 环境中单独核验的；守卫 CPU 读数缺陷不影响显存读数，但显存峰值同样没有在真实 worker 生命周期下重复测量。
- **未勾选项保持未勾选**：1.4 的训练预算估算与随机种子未形成独立记录，2.3 与 2.7 的渲染回归测试、2.6 的逐帧时间戳核验、4.1 的解析配置核验、4.3 的无 GPU 测试均缺证据。不为了进度连续而勾选。
- **proposal 修订**：把“小批媒体准备完成、全量数据和训练评测待完成”改为当前事实，并写明 A 臂早前轮次作废与重启条件。
- **design 修订**：3.5 增加“三臂须保存优化器与调度器状态、只含 `state_dict` 的检查点只能作诊断产物、中断后在独立目录重启”的配方要求；Risks 增加“资源守卫可靠性是训练前提”，未通过 CPU 非负、elapsed 合理、超限整组无残留的 CPU-only 测试前不得启动或恢复训练。
- **待用户确认的结构改动**：新增第 7 节（守卫验证、检查点状态修复、A 臂重跑、B/C 串行）及并行标注。按任务规则，改 tasks.md 结构前须先说明并取得用户回复，故本次未写入。

### 2026-11-06：任务结构重组（用户选定方案 B）

- **批准**：用户选定方案 B，即拆开原 4.5 的三臂训练，并为守卫验证与检查点修复建立独立条目。改动前已说明内容与理由并取得回复。
- **新增**：4.5 资源守卫在真实 worker 生命周期下验证（可与 4.6 并行）；4.6 检查点保存优化器与调度器状态并补续训测试（可与 4.5 并行）；4.7 A 臂训练并含提交推送与远端 HEAD 核验（依赖 4.1、4.3、4.5、4.6）；4.8 B 臂（依赖 4.7）；4.9 C 臂（依赖 4.8）。
- **重编号**：原 4.6“仅按验证结果选择最佳 checkpoint”顺延为 4.10（依赖 4.9）。影响到的既有引用已同步：4.2 的“真实训练验收见 4.4、4.5”改为“4.4、4.7–4.9”；5.1 补“在 4.10 冻结选择后”前缀。
- **偏离说明**：方案 B 原写作“守卫与检查点修复放新第 7 节”，实际改放第 4 节的 4.5、4.6。原因是编号即执行顺序，第 4 节训练依赖第 7 节任务会使编号与实际顺序矛盾。如用户要求回到第 7 节，可再调整。
- **未勾选的保持未勾选**：4.1、4.3、4.5–4.10 均无证据；本次只做结构重组，不产生执行结果。
- **历史条目不回退**：1.1–3.7 与 6.1–6.5 的勾选状态保持原文，未因重排而改动。

### 2026-11-06：1.4 重新界定与 4.7 补充（用户批准）

- **为什么漏做**：2026-11-04 记录显示人工质检（3.2、3.3、6.5）勾选后直接推进 3.4 全量检测与裁剪，1.4 未关闭就被跨过。原因是 1.4 把源视频清单、索引冻结、训练 seed、预算估算合成一条，没有独立验收动作；旧 tasks 只有编号、没有前置关系，执行时按最急的任务推进。
- **1.4 改为回填冻结事实**：只记录全量批次源视频清单、三臂 train/val/test 索引与失败清单的 SHA-256，以及检测与编码的实际耗时和磁盘占用。索引内容已由 3.5 冻结并勾选，本项不重复冻结。
- **4.7 承担 seed 与训练预算**：条目文本增加记录数据划分 seed 与训练 seed、估算三臂训练时长与 checkpoint 磁盘占用，容量不足则停下报告。这样不改编号，也不新增条目。
- **对旧记录的更正**：本文件 2026-11-06“计划与事实对齐”条目中“1.4 的训练预算估算与随机种子未形成独立记录”一句，所指缺口现由 1.4（哈希与成本）与 4.7（seed 与训练预算）分别承担，原句描述的分工已过期，保留原文以备追溯。

### 2026-11-06：任务原子化拆分（用户回复“拆”）

- **批准**：用户确认按上一轮列举的 9 条复合任务拆分，并同意已完成条目保留原样、只记历史例外。
- **拆分结果**：1.4 拆为 1.4（哈希回填）与 1.5（耗时与磁盘成本）；2.3 拆为 2.3（锚点一致核验）与 2.8（渲染分支回归测试）；2.7 拆为 2.7（坐标恢复、空裁剪、帧号映射测试）与 2.9（场景回归测试）；4.1 明确只核验配置并把结论落盘；4.3 只保留无 GPU 测试与其运行结果，部署与版本核验移到 4.8；4.6 只做检查点保存实现，续训验证移到 4.7；原 4.7 拆为 4.8（提交推送与远端 HEAD 核验）、4.9（seed 与训练预算）、4.10（历史锚点复核）、4.11（A 臂）、4.12（B 臂）、4.13（C 臂）、4.14（验证选择）；5.5 拆为 5.5（源数据与旧产物未被修改）、5.6（资源释放核对）、5.7（严格校验与提交）。
- **重编号**：第 4 节由 10 条变为 14 条，第 5 节由 5 条变为 7 条。既有引用同步：4.2 的“真实训练验收见 4.4、4.7–4.9”改为“4.4、4.11–4.13”；5.1 的“在 4.10 冻结选择后”改为“在 4.14 冻结选择后”。
- **新增并行标注**：1.4 与 1.5、2.7 与 2.9、4.5 与 4.6、4.9 与 4.10 四对，其余按编号串行。
- **历史例外清单**：2.2、2.4、2.5、3.1、3.4、3.5、4.2、4.4 仍为复合条目，其勾选代表整组结果同时成立。按“保留已完成条目及其证据、不为重排而回退”的规则不补拆，此清单供后续审阅时识别。
- **未勾选的保持未勾选**：本次只做结构重组，未产生新的执行结果。1.1–1.3、2.1、2.2、2.4、2.5、3.1–3.7、4.2、4.4、6.1–6.5 的勾选状态与原文保持不变。

### 2026-11-06：1.4 冻结事实回填与 1.5 成本统计（远程只读）

- **方式**：在 pet `/home/wyy/pet-action-recognition`（HEAD `55c9789`）只读执行 `sha256sum`、`wc -l` 与对索引 JSON 的统计，未启动任何容器、训练或渲染。项目代码与数据未被修改。
- **源视频清单**：`results/cat_crop_classification/gdino-crop-20261103a/all_videos.txt`，2,144 行，SHA-256 `f4082a147b93d0c36913bab8413dceebffa04759c89dabc22b5a04861e6ed7a5`。
- **清单与索引 SHA-256**（`datasets/cat_crop_classification/gdino-v1-full/`）：
  - `manifest.json` `20db7ae253b445cf15234c313b9c189f749962c3226d9e1915842866c5a5ddb7`
  - `availability.json` `5ccb4bd781cffc11596a7da32780882bbba446ac11bb75043a93aee927cd9fdf`
  - `raw_train` `cb2ba613c7cf7a569de2d4865e46664a7d5133737f961fe6db838001f7afc50f`，`raw_val` `26effa5d66b3ea60c228d78c26c8e447ea73c0c7d9dc49b3da4a432d895d6249`，`raw_test` `f87085fd15c628687ae4c46f23c3d4b3212a4a52169bea390848cc9eb8337c3a`
  - `gdino_train` `c16520d47dffefff25bbf4fb389c5fbf6135aa28fdda65a77f7ef8245a4e1bf7`，`gdino_val` `835d31da47560f7a7201c79919f779ed98ffdd6c408bba3099fabf7f2dcb5552`，`gdino_test` `e5af18f67a5b426a88d34c2df343397c30b52f832cbac763de3fb3ac517f5a4a`
  - `gdino_motion_train` `553cbdb4d2c79650c1b16c12fd419e08954fae62ab2c31021371678a45844a6a`，`gdino_motion_val` `87263151cd5f75d7e5edd3cf199bf2c0ea74fac5ea83240421575ffbf5913c17`，`gdino_motion_test` `74cb3412e2839661a59c915a7f62ec7046500011e3d5abbb656c3d949d67956b`
- **失败清单**：来自 `availability.json` 的 2,710 行，可用 214；不可用 2,496，其中 `multi_pet_unsupported` 1,551、`no_reliable_pet_detection` 945。两类原因合并计 2,496，没有其他原因值。
- **索引自检**：三臂 train/val/test 行数均为 137/33/44，三臂类别计数相同（train：activity 58、prolonged_stationary 47、abnormal 9、drinking 8、eating 7、grooming 6、toileting 2）。
- **成本**：`.run/logs/full_preprocessing.log` 记录 2026-11-05 10:05:06 开始、2026-11-06 10:25:52 成功结束，墙钟 24 小时 20 分 46 秒。分段：检测在 16:17:41 中断后重跑，守卫记录最后一次检测 `rc=0 in 15473s`（4 小时 17 分 53 秒），20:35:34 结束；渲染 `rc=0 in 49699s`（13 小时 48 分 19 秒），次日 10:23:53 结束；清单与索引生成 119 秒。
- **磁盘**：`assets/full_run` 合计 6.8 GB，其中 `videos` 6.3 GB、`metadata` 364 MB、`detections` 116 MB；索引目录 1.4 MB。
- **限制**：24 小时 20 分包含首次检测被中断的时段，不是干净吞吐量；共享机并发窗口未排除，不能作为性能结论。`manifest.json` 的 `full_dataset_preprocessing` 为 `false`，但该批次实际覆盖全部 2,144 段索引视频，因此这个标志不能用来判断是否全量，判据应是 `all_videos.txt` 行数与 `source_rows`。

### 2026-11-06：2.3 核验 B/C 共用检测缓存与锚点（远程只读）

- **方法**：新增只读核对脚本 `scripts/checks/check_cat_crop_arm_consistency.py`（提交 `104d838`），在 pet HEAD `104d838` 上以 `plf` 环境运行，守卫上限 250% CPU / 4 GiB RSS，耗时约 5 秒，未使用 GPU。报告 `results/cat_crop_classification/gdino-crop-20261103a/quality/arm-consistency/arm_consistency_v2.json`。
- **共用检测缓存**：2,144 份渲染元数据的 `detection_fingerprint` 只有一个取值（变体数 0），指向同一 GroundingDINO 权重哈希 `1a2412ef…` 与同一配置；`render_fingerprint` 同样只有一个取值。B、C 不来自两次检测。
- **锚点行为**：`petlib/followcam.py` 的 `MotionOffsetSmoother.update` 在 `frame_index in (previous_anchor, next_anchor)` 时执行 `reset()` 并原样返回 base；`scripts/prepare_cat_crop_experiment.py` 的 `anchor_bounds` 用 `bisect_right`，锚点帧自身会作为 `previous_anchor` 命中，因此锚点帧不做像素外扩。
- **像素测量（3 段、每段逐帧对比两路视频）**：锚点帧差值中位数 1.9539 / 2.2208 / 2.2814，p90 ≤ 2.61；无效帧（两路按设计写同一裁剪）差值中位数 1.8644–2.2333，构成约 2.0 的编码噪声底；受像素辅助的帧 p90 为 14.55–16.87、最大 28.45–37.30，约为噪声底的 7 倍。锚点落在噪声底内，辅助帧明显高出，说明像素辅助没有污染锚点。
- **对旧结论的更正**：同一脚本首版把 `metadata.track[].camera_box` 与 `display_box` 相比，报出 110,163 处“锚点不一致”（提交 `9fc7b45` 的结果，报告 `arm_consistency.json`）。核对源码后确认 `camera_box` 记录的是训练资格框、`display_box` 可能带审阅平滑，两者本就不应相等；该数字测量的是字段约定而不是渲染结果，**结论撤回**。现行版本改为比较解码帧。
- **未证明的部分**：两路视频独立编码，帧间预测会带来约 1% 的均值差，因此不能从解码帧证明锚点裁剪“完全逐像素相同”。精确相等的证明需要比较编码前的裁剪帧，归入 2.8 的合成注入测试。
- **限制**：像素检查只覆盖 3 段、共 5,169 帧，不是全量 2,144 段；噪声底用无效帧代理，未单独测量同源同帧的两次编码差。

### 2026-11-06：2.6 逐帧时间映射核验（采样 40 段，待裁定策略）

- **方法**：新增 `scripts/checks/check_cat_crop_time_mapping.py`（提交 `5bd6243`），用 PyAV 读源视频与 B/C 两路的逐帧 PTS。在 pet HEAD `5bd6243`、`plf` 环境、守卫 250% CPU / 4 GiB 下运行 65 秒，未用 GPU。报告 `results/.../quality/arm-consistency/time_mapping_sample40_v2.json`。
- **索引映射**：40 段样本中，B、C 两路帧数与源视频逐一相等，无掉帧、无重复、无截断（mismatch 0）。
- **时间轴**：两路裁剪由恒定帧率管道写出，逐帧间距恒定（irregular 0）。源视频按累计漂移判定：39 段 `uniform`（漂移 ≤ 2 ms），1 段 `irregular`——`event_20260605_033052` 共 1,835 帧，累计漂移 1,007 ms（约 15 帧），说明源流存在可变帧率式的丢帧或补帧。
- **影响面**：该源视频在本批只有 2 个区间，且都已因 `multi_pet_unsupported` 不可用，因此当前 214 个可用区间中尚未发现受影响样本。这只是 40 段采样的观察，不能外推到 2,144 段。
- **为什么这仍然是个决策点**：训练采样按帧号进行（`RestrictFrameRange` 把区间换算成 `start_index` / `total_frames`，mmaction2 的 `SampleFrames` 在帧号空间取帧），所以 VFR 不会改变被采样的帧；它改变的是时间轴，会影响按秒计算的下游量（持续时间、2 秒窗口、跨模态对齐）和人工复核时的对时。design 3.2 原文要求“无法保持映射则明确拒绝”，需在两条路线之间裁定。
- **对旧判定的更正**：本脚本首版按“单个 PTS 间隔偏离中位数 ≤1 ms”判定，把 12 段采样中的 2 段误判为 VFR；第二版按“与主间隔的 tick 偏离 ≤1”判定，把 40 段全部误判为 VFR。两次都错在把时间基量化（15360 时间基下 1029/1029/1014 交替、平均 1024）当成帧率变化。现行版本改为与标称帧周期比较累计漂移，前两版结论均作废。
- **未完成**：全量 2,144 段的 VFR 比例未测；拒绝或接受 VFR 源区间的策略未定，2.6 保持未勾选。

### 2026-11-06：范围收窄为只训练 B（用户决定）

- **决定**：用户确认本轮只训练 B（GroundingDINO 裁剪），A（原视频）与 C（像素辅助）不训练。理由是本轮目标是让裁剪输入的分类链路端到端跑通，不需要归因裁剪相对原视频的收益。
- **代价**：本轮无法声称裁剪带来提升，报告结论只能写成“裁剪输入下的分类水平”。若要归因，需后续按同一冻结索引补训 A 与 C，已记入 design 的 Open Questions。
- **proposal**：训练范围由三臂改为 B 单臂，A/C 资产记为已生成但不训练。
- **spec**：`Paired reproducible classifier training` 改为 `Reproducible cropped-classifier training`（单臂，冻结索引与记录要求不变）；“Accuracy improves only on available crops” 改为单臂报告并明确不得声称提升；像素辅助的比较场景改为“仅生成、不训练”。
- **design**：3.1 改为单一训练臂并写明被否决的三臂方案与代价；3.4 改为像素辅助变体的当前定位；3.5 去掉三臂措辞；Risks 增加不能归因裁剪收益的限制；Open Questions 增加可变帧率策略与是否补训 A/C。
- **tasks 重编号**：删除原 4.12（A 后训练 B）、4.13（B 后训练 C）与原 5.2（A/B 与 B/C 配对比较）；原 4.11（训练 A 臂）改为 4.11（训练 B 臂），原 4.14（选择）改为 4.12；原 5.3–5.7 顺延为 5.2–5.6。引用同步：4.2 的“真实训练验收见 4.4、4.11–4.13”改为“4.4、4.11”。
- **判据补齐**：按新的任务规则，所有未完成条目在末尾补了完成判据；已完成条目保持原文，未回填判据也未重写。
- **未变**：索引、冻结批次、媒体产物与既有证据均未改动；B 的训练数据仍是 214 个可用区间（train/val/test 137/33/44）。

### 2026-11-06：删除随单臂范围失效的核验（用户决定）

- **决定**：只训练 B 之后，只有三臂对照或按秒解释才需要的核验不再做。删除原 2.6（全量逐帧时间映射）与原 2.8（B/C 锚点像素相等的合成回归），并把原 2.9 场景回归顺延为 2.7、原 2.7 单元测试顺延为 2.6。
- **保留**：帧号与区间边界的对应仍由索引与媒体审计覆盖；坐标恢复、空裁剪、缓存不匹配与多宠物等场景回归仍然决定 B 的裁剪是否正确，因此保留为 2.6、2.7。
- **design**：3.1 增加说明“B/C 锚点像素一致性与源视频时间轴漂移随单臂范围取消”，Open Questions 中的可变帧率条目删除，因为时间轴不再被本实验使用。
- **已完成条目**：2.3 的正文里“逐像素相等留待 2.8”改为“逐像素相等未做，该核验随单臂范围取消”，其余已完成条目未改动、未重编号。
- **未清理的代码**：`scripts/checks/check_cat_crop_time_mapping.py` 及其两份报告仍在仓库与远程产物中。它现在是范围外工具，删除它属于代码变更，未在本轮执行。

### 2026-11-06：2.6 收窄为两条实际缺口（用户确认）

- **核对既有覆盖**：`tests/test_cat_crop_experiment.py` 已覆盖补边与边界几何（`test_crop_square_pads_without_shifting_target_inward`、`test_edge_boxes_use_a_padded_square_window`、`test_square_crop_bounds_extend_past_frame_edges`）、逐帧渲染的帧数守恒，`tests/test_cat_crop_review_set.py` 已覆盖审阅导出的帧对齐。
- **缺口**：没有“空框或退化框必须报错”的用例；没有用已知标记做一次坐标往返的用例。
- **修订**：2.6 原条目“坐标恢复、空裁剪与帧号映射的单元测试”收窄为上述两条，措辞改为可直接判断的句子。编号与并行标注未变，2.7 未动。
- **未做**：没有删除 2.6。用户确认按收窄后的两条执行。

### 2026-11-06：2.6 两条裁剪测试通过

- **新增用例**（`tests/test_cat_crop_experiment.py`，提交见本条之后的 commit）：
  - `test_out_of_frame_and_degenerate_boxes_raise_instead_of_blank_output`：完全落在画面外的框 `[500,500,600,600]` 与零面积框 `[10,10,10,10]` 都必须抛 `ValueError`，不会输出灰帧或黑帧。
  - `test_known_marker_lands_at_the_converted_position`：在合成帧的 `[10,30)×[40,60)` 画白块，用 `[0,0,100,100]` 窗口按 1:1 裁剪时白块必须落在同一行列区间；`size=50` 缩放一半时白块中心必须落在 `(10,25)`。两处都检查白块外区域为背景值。
- **逐用例结果**：`python3 -m pytest tests/test_cat_crop_experiment.py -q -k "out_of_frame or known_marker"` → 2 passed。
- **全文件与全仓状态**：`tests/test_cat_crop_experiment.py` 为 51 passed、1 failed、8 subtests；`tests/` 全仓为 89 passed、3 failed、8 subtests。三个失败均与本条无关：`test_paired_index_rejects_different_samples` 的固件缺少 `source_index_root` 字段，HEAD 版本的 `validate_common_indexes` 已要求该字段，属既有失效用例；另两个 `tests/test_resource_guard_process_tree.py` 失败来自工作区中未提交的 `resource_guard.sh` 改动。
- **未修**：上述三个失败不在 2.6 范围，未修改；其中失效用例归入 4.3 的无 GPU 测试整理，守卫相关的两个失败属于 4.5 的守卫验证。

### 2026-11-06：待办任务改写成自足文字（用户要求）

- **问题**：原条目如“补齐坐标恢复、空裁剪与帧号映射等测试”，没有写明对象、输入与判据。我当时是按 `petlib/datasets/cat_crop.py` 的函数与现有测试名反推含义的，同一句换个人会写出不同范围。这属于任务文字缺陷，不是执行者的理解问题。
- **规则落点**：按用户指示写入 OpenSpec 补充扩展 `~/.pi/agent/extensions/openspec-house-rules/rules/authoring.md`，新增“任务文字必须自足”一节：四要素（对象、动作、判据、非目标）、禁用“等/相关/完善/处理一下”、判据须可被第三方核对。未写入 `.agents/skills/openspec-*`。
- **改写范围**：17 条未完成条目（2.7、4.1、4.3、4.5–4.12、5.1–5.6）改为自足文字，逐条补上对象（文件、函数、产物）、动作、判据与非目标。已完成条目与编号未动，无增删与重排。
- **2.7 语义变化**：由“补齐场景回归测试”改为“核对现有覆盖、只补缺口”。依据是六类场景已有 8 条通过用例（`pytest -k "no_pet or long_gap or multi_pets or single_dog or static_pet or cache_mismatch"` 全绿），不需要重写。
- **4.3 增加了已知失效用例**：`test_paired_index_rejects_different_samples` 的固件缺 `source_index_root`，现有代码要求该字段，属既有失效，归入 4.3 修复。

### 2026-11-06：2.7 六类场景覆盖核对

- **输入来源**：六类场景全部由测试当场构造的字典与数组驱动，不读任何视频。`classify_frame` 的输入是检测列表（`detection("cat", [...], 0.9)`），`build_frame_track` 的输入是锚点字典（`state([...])`），`motion_correct_box` 的输入是前景掩码数组与框。合成输入只证明规则逻辑，不证明真实检测分布；分布证据来自 `availability.json` 与 20 段人工审阅。
- **映射表**：
  - 无宠物 → `test_no_pet_is_detection_missing_not_confirmed_absence`：输入空检测列表，断言 `reasons == ["no_reliable_pet_detection"]` 且 `target_valid` 为假，不写“确认无宠物”。
  - 长缺口 → `test_long_detection_gap_keeps_display_crop`（40 帧缺口、`max_gap=20`：`camera_box` 为 None、`display_long_gap` 为真）与 `test_short_gap_interpolates_and_long_gap_does_not`（短缺口插值、长缺口无效）。
  - 多宠物 → `test_multi_pets_are_unsupported`（两猫与猫加狗都含 `multi_pet_unsupported`）＋本条新增 `test_multi_pet_frame_is_not_training_eligible`（断言 `pet_count == 2`、`target_valid` 为假、原因列表恰好一项）。
  - 单狗 → `test_single_dog_is_valid_and_labeled`（分类层 `target_class == "dog"`）＋本条新增 `test_single_dog_track_crops_with_the_dog_box`（轨道层 `camera_box` 等于狗框，证明按狗裁剪）。
  - 静止宠物 → `test_static_pet_keeps_box_and_motion_only_expands_after_two_hits`：空前景（宠物不动）时框不变、`corrected` 为假；静止不会被判成无宠物。
  - 缓存不匹配 → `test_cache_mismatch_is_rejected`：缓存记录旧 `source_sha256`，`load_reusable_detection` 对新哈希必须抛 `RuntimeError`。
- **补齐的两条缺口**：原有多宠物用例只断言原因字符串存在，没有断言“不可训练”；原有单狗用例只断言物种字段，没有断言裁剪框确实取狗框。新增两条补齐，未改动已有断言。
- **逐用例结果**：`python3 -m pytest tests -q -k "no_pet or long_gap or multi_pet or single_dog or static_pet or cache_mismatch"` → 10 passed。`tests/test_cat_crop_experiment.py` 为 53 passed、1 failed（既有失效用例 `test_paired_index_rejects_different_samples`，归 4.3）。

### 2026-11-06：训练目标改为只含猫、多宠物帧用猫框（用户要求）

- **决定一**：训练与评测只含猫目标，狗区间不进入。理由是用例数量不足以支撑，且会让验证集物种构成不稳定。实测 `availability.json`：可用 214 个区间中猫 207、狗 7（train 6、val 1、test 0）；剔除后为 207（train 131、val 32、test 44）。
- **决定二**：多宠物帧只要恰好一只猫就用猫框训练，狗不参与目标选择；两只及以上猫仍按 `multi_pet_unsupported` 排除。
- **实测影响（远程只读统计 1,551 个 `multi_pet_unsupported` 区间的 408,301 帧）**：猫狗都未检出 328,993 帧（80.6%）；恰好一只猫 54,371 帧（13.3%，其中 23,345 帧同时有狗）；两只及以上猫 5,884 帧（1.4%）。按“区间内每帧都必须有效”的现行规则，放宽多宠物策略后新增可训练区间为 **0**；主要障碍是漏检，不是多宠物策略。
- **因此**：决定二已写入 design 3.3 与 spec 的物种场景，但它在本轮不产生新样本；是否允许区间内存在部分无效帧（覆盖率阈值）列为 design 的 Open Questions，需另行裁定。
- **类别稀疏提示**：207 个区间中 toileting 训练样本仅 2 个，已在 design 的 Risks 写明必须逐类别报 support。
- **未改 tasks.md**：改为猫专用索引需要新增一条构建与冻结索引的任务，并同步 4.9、4.11、4.12、5.1、5.2 的样本数与分母。这属于 tasks 结构改动，等用户确认后再动。

### 2026-11-06：放弃多宠物放宽（用户决定）

- **决定**：用户判断多宠物放宽“也算了吧”，不予采用。回到严格规则：整帧宠物总数为 1 且是猫才有效；出现狗或多只宠物一律 `multi_pet_unsupported` 并排除。
- **依据**：上一条实测显示放宽新增可训练区间为 0，主要障碍是漏检（八成帧猫狗均未检出），收益为零却要改变资格定义与重新渲染，因此不划算。
- **design 修订**：3.3 恢复严格措辞，并保留实测数字作为不采用的依据；Open Questions 中“是否允许区间内存在部分无效帧”删除。
- **spec 修订**：物种场景恢复为“恰好一只宠物且是猫才有效；出现狗或多只宠物即排除，狗永不作为训练目标”。
- **对旧记录的更正**：上一条 evidence 写“决定二已写入 design 3.3 与 spec”，现已被本条取代，决定二不再成立。决定一（只训猫、剔除 7 个狗区间、可用 207）不变。

### 2026-11-06：新增猫专用索引任务并同步样本数（用户批准）

- **新增 3.8**：按 `target_class == "cat"` 重建并冻结训练索引，剔除 7 个狗区间，产出 207 个区间（train 131、val 32、test 44）。只重建索引，不重新检测、不重新渲染，因为 B 视频按 `display_box` 渲染，与资格审查无关。放在第 3 节末尾，不动 4.x 编号。
- **数字同步**：4.9 由 214 改为 207；4.11 的训练索引改为“3.8 冻结的 207 区间索引”；4.12 的训练集由 137 改为 131；5.2 的条件准确率分母由 214 改为 207，并要求注明 7 个狗区间按物种策略剔除。
- **分母核对**：2,710 = 207 猫可用 + 7 狗剔除 + 1,551 多宠物 + 945 无可靠检测，报告需能对上这四个数。
- **未变**：1.4 记录的 214 索引与哈希保留为三臂索引的历史记录，新索引与之并存，不覆盖。

### 2026-11-06：待办条目按“最小实现”规则压缩

- **触发**：用户认为当前任务太烦琐。对照 extension `rules/authoring.md` 的“最小实现、最小测试”与“一条任务一个可判定结果”，问题在于文字臃肿而不是条目过多：同一批数字在 4.9、4.11、4.12、5.2 反复出现，判据写成整段解释。
- **处理**：17 条待办条目压缩为“动作 + 判据”，每条不超过两句；重复数字只在产生或使用它的条目里保留一次；解释性从句移入 design。编号、并行标注、依赖关系与已完成条目均未改动（diff 为 17 增 17 删，无增删条目）。
- **未删除条目**：4.10、5.4、5.5 各自对应不同的证据（历史锚点、源数据未改、资源释放），删掉会降低可判定性，因此保留，仅压缩文字。若确认要合并，需按结构改动流程先说明再动。

### 2026-11-06：按“最小测试”收窄三条验证任务

- **4.3** 由“核对并补测试”改为只修失效用例（固件补 `source_index_root`），不新增测试。裁剪几何与六类场景已由 2.6、2.7 覆盖，重复写只会增加维护面。
- **4.5** 守卫验证改为一次 CPU-only 演练，三项断言看日志，不新增测试文件。
- **4.7** 由“补无 GPU 续训测试”改为一次 1 epoch 冒烟：检查点字段与恢复后的学习率，证据是字段清单，不写测试用例。理由是本轮不做多次续训，测试代码的收益低于一次核对。
- **未变**：2.6、2.7 已是“两条例句级用例 + 两条补断言”，符合最小测试；4.1、4.9、4.10、5.4、5.5 是核对类任务，本来不产出测试代码。

### 2026-11-06：3.8 猫专用索引冻结（远程只读重建）

- **实现**：`scripts/prepare_cat_crop_experiment.py` 新增 `--target-class`，在索引阶段按 `target_class` 过滤准入区间，并把过滤值与被剔除数量写入 manifest（提交 `7a1db27`）。不重新检测、不重新渲染。
- **运行**：pet HEAD `7a1db27`，`plf` 解释器，命令行与 2026-11-05 全量预处理第 3 阶段一致，另加 `--dataset-root datasets/cat_crop_classification/gdino-v1-cat --dataset-id gdino-v1-cat --target-class cat`。守卫上限 250% CPU / 6 GiB，201 秒完成，退出码 0，日志 `.run/logs/index_cat_20261106.log`；峰值 RSS 约 915 MB，未使用 GPU（执行期间 GPU0 有其他进程，与本任务无关）。
- **结果**：`source_rows` 2,710、`eligible_rows` 207、`excluded_by_target_class` 7、`training_ready` true、`target_class_filter` cat。三臂 train/val/test 均为 131/32/44，行数一致。
- **类别计数（train）**：activity 55、prolonged_stationary 47、drinking 8、eating 7、grooming 6、abnormal 6、toileting 2。**val**：activity 11、prolonged_stationary 7、eating 5、drinking 4、grooming 4、abnormal 1，无 toileting。toileting 全轮只有 2 个训练样本，类别级指标不可信，报告须逐类给 support。
- **哈希**：`manifest.json` `14284290c4711aeae21501d687dcf2445ab4ee2e79d82599b4ae930fe38ba6c6`；`availability.json` `6d6aa945829404b750e2399c306d4192e46fbc5517d0ba0c5497c21c859e1cae`；`raw_train` `97e68b09…`、`raw_val` `9ee3b6ad…`、`raw_test` `f87085fd…`；`gdino_train` `47cf983c…`、`gdino_val` `53d08736…`、`gdino_test` `e5af18f6…`；`gdino_motion_train` `b4cdd22e…`、`gdino_motion_val` `99082ff9…`、`gdino_motion_test` `74cb3412…`。
- **与旧索引并存**：1.4 记录的 214 区间索引 `gdino-v1-full` 未改动，保留为三臂索引的历史记录；本轮训练使用 `gdino-v1-cat`。

### 2026-11-06：4.1 B 臂配置解析核对（远程只读）

- **方法**：在 pet HEAD `7a1db27`、`plf` 环境用 `mmengine.config.Config.fromfile` 解析 `configs/cat_crop_videomaev2_gdino.py`，解析结果写到 `results/cat_crop_classification/gdino-crop-20261103a/gdino/config_resolved_4_1.json`（9,534 字节）。未改配置、未训练。
- **对照 design 3.5**：
  - 16 帧、间隔 4、单 clip：`SampleFrames(clip_len=16, frame_interval=4, num_clips=1)` ✓
  - 224 输入：训练 `Resize(-1,256)` → `RandomResizedCrop` → `Resize(224,224)`；验证 `Resize(-1,256)` → `CenterCrop` ✓
  - AdamW lr 5e-05、weight decay 0.05 ✓
  - 20 epoch：`EpochBasedTrainLoop(max_epochs=20, val_interval=1)` ✓
  - warmup 2：`LinearLR(start_factor=0.1, begin=0, end=2)` 后接 `CosineAnnealingLR(begin=2, end=20, eta_min=1e-06)` ✓
  - AMP：`optim_wrapper.type = AmpOptimWrapper` ✓（`train_cfg.amp` 未显式设置，由 wrapper 类型决定）
  - micro-batch 4 ✓
  - 七类：`cls_head.num_classes=7`，类别表与 design 一致 ✓
- **两处不一致**：
  - 梯度累积未设置（`accumulative_counts` 缺失），design 要求累积 4，即有效 batch 16，当前有效 batch 为 4。
  - `run_cat_crop_experiment.py` 的 `INDEX_ROOT` 仍指向 `datasets/cat_crop_classification/gdino-v1-full`（214 区间、含狗），而本轮训练应使用 3.8 的 `gdino-v1-cat`（207 区间）。
- **另确认**：`CheckpointHook` 同时为 `save_optimizer=False`、`save_param_scheduler=False`、`save_best=macro_f1`、`max_keep_ckpts=2`，对应 4.6 的修改目标。
- **计划缺口**：上述两处不一致没有对应任务。梯度累积属于训练运行参数，可并入 4.11；索引指向属于训练前置的代码修正，需要一条明确的归属。等用户确认后再改 tasks。

### 2026-11-06：4.1 两处缺口落入任务（用户确认）

- **4.6 扩为训练入口配置对齐**：除原有的两个 `save_*` 开关，增加把 `run_cat_crop_experiment.py` 的 `INDEX_ROOT` 指向 `gdino-v1-cat`。合并理由是三处修改共同构成“训练入口与 design 一致”这一个结果，证据同为解析后的配置与索引路径。
- **4.11 增加梯度累积**：训练参数写明 micro-batch 4 + 累积 4（有效 batch 16），判据增加“运行记录的解析配置显示有效 batch 16”。
- **未动**：编号、并行标注、依赖关系与其它条目均未改；proposal、spec、design 无需修订，因为 design 3.5 本来就要求有效 batch 16，缺的是实现而非计划。

### 2026-11-06：4.3 修复失效用例

- **改动**：`test_paired_index_rejects_different_samples` 的固件补齐 `validate_common_indexes` 现在需要的字段：`source_index_root`（三个 split 各一行源索引）、`source_video_root`、`source_rows`，并补 `availability.json`。断言未改，仍要求三臂 `sample_id` 不一致时抛 `ValueError`。
- **结果**：`python3 -m pytest tests/test_cat_crop_experiment.py -q` → **54 passed、8 subtests passed**（此前 1 failed）。
- **全仓状态**：`tests/` 为 92 passed、2 failed、8 subtests。两个失败是 `tests/test_resource_guard_process_tree.py`，来源是工作区里未提交的 `resource_guard.sh` 改动（+65/−11），不属于本条，归 4.5 的守卫演练处理。
- **未新增测试**：按最小测试只修固件，没有加用例。

### 2026-11-06：4.6 训练入口配置对齐

- **改动**（提交 `447ba4d`）：`configs/cat_action_v1_base.py` 的 `save_optimizer`、`save_param_scheduler` 由 `False` 改为 `True`；`scripts/run_cat_crop_experiment.py` 的 `INDEX_ROOT` 由 `gdino-v1-full` 改为 `gdino-v1-cat`。
- **核验**：pet HEAD `447ba4d`、`plf` 环境解析配置，`INDEX_ROOT` 为 `/home/wyy/pet-action-recognition/datasets/cat_crop_classification/gdino-v1-cat`，`save_optimizer=True`、`save_param_scheduler=True`、`save_best=macro_f1`；该索引 manifest 为 `dataset_id=gdino-v1-cat`、`eligible_rows=207`、`target_class_filter=cat`。
- **本地测试**：`tests/test_cat_crop_experiment.py` 54 passed、8 subtests。
- **判据措辞修正**：原条目写“旧检查点加载后含 `optimizer` 与 `param_scheduler` 字段”，这对旧检查点不可能成立；改为核对解析后的 `save_*` 与索引路径，检查点字段是否落地由 4.7 的冒烟验证。
- **影响面**：`save_best` 仍为 macro_f1，`max_keep_ckpts` 仍为 2，保存频率未改；检查点体积会因含优化器状态而增大，磁盘占用估算归 4.9。

### 2026-11-06：取消守卫演练，优先启动训练（用户决定）

- **删除原 4.5**（守卫 CPU-only 演练）。理由：守卫的改版仍在工作区未提交、两条单测未过，演练需要先部署再验证，而部署排在 4.8，形成循环依赖；用户要求先训练。
- **编号保留空位**：4.5 不再使用，其余编号不变，避免整段重排与引用改动。`openspec instructions apply` 的任务顺序与文件一致。
- **原 4.7 改为训练内联检查**：不再单独跑 1 epoch 冒烟，改为训练启动后检查第一个检查点是否含 `optimizer` 与 `param_scheduler`，缺则立即停止。这样省一轮训练，同时保住“别再一次白跑 8 个 epoch”的防线。
- **风险登记**：训练将使用 pet HEAD 上的旧版守卫（工作区改版未部署）。旧版曾留下孤儿进程，因此每轮结束必须手工核对进程与显存；本地 `tests/test_resource_guard_process_tree.py` 的两条失败不影响旧版守卫的既有行为。

### 2026-11-06：4.8 部署核验

- 本地与 pet 均位于 `a77aafb`，远端跟踪文件无改动（`git status --porcelain --untracked-files=no` 为 0）。本轮部署内容：配置对齐（`447ba4d`）、索引阶段 `--target-class`（`7a1db27`）、失效用例修复（`be71494`）、计划修订（至 `23d944b`）。
- 训练将使用 pet 上的旧版 `resource_guard.sh`；本地那份改版仍未提交、未部署。

### 2026-11-06：4.9 随机种子与预算

- **训练 seed**：0（design 3.5 指定）。**数据划分 seed**：无——划分来自冻结的 `cat_action_v1` 索引（按日期隔离），本轮不重新划分，因此不存在划分 seed。
- **待写参数**：`select_arms` 与 status 会记录 `seed=0`；训练入口 `scripts/run_cat_crop_experiment.py --stage train --arms gdino --epochs 20`，`artifact` 目录为 `results/cat_crop_classification/gdino-crop-20261103a/gdino/`。
- **吞吐测量**：同配方的上一轮（train 137，batch 4 + 累积 4）在 `raw/work` 留下 `epoch_7.pth` 与 `epoch_8.pth`，时间戳相差 39 秒，即约 **39 秒/epoch**。按 131 个训练样本、20 epoch 估算墙钟约 15–20 分钟（含每轮验证）。
- **磁盘估算**：上一轮 weights-only 检查点约 334 MiB；本轮打开 `save_optimizer` 与 `save_param_scheduler` 后单个检查点预计约 1 GB，`max_keep_ckpts=2` 加 best 共约 3–4 GB。仓库根盘此前余量 71 GB，不需要额外清理。
- **结论**：容量与时间均充足，不构成阻塞。
