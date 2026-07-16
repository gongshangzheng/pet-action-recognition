---
name: management
description: |
  项目管理模块操作指南。用于团队成员管理、日报/周报/月报、任务（看板+项目树）、里程碑、会议纪要等 CRUD 操作（脚本直接改文件，后端只读）。
  触发场景：(1) 添加/修改/删除团队成员，(2) 创建/更新/删除报表，(3) 管理任务(增删改查+改状态跨段移动)，(4) 创建/更新/删除会议纪要，(5) 了解项目结构
---

# 项目管理模块

本 skill 提供项目管理模块（`management/`）的完整操作指南，以及一套**自定位**的 CRUD 脚本，直接读写 `management/` 下的数据文件。

> **架构前提**：后端 `server/routers/management.py` 是**只读**的（解析数据文件暴露给前端）。所有"增删改"由本 skill 的脚本直接修改文件完成，再由只读 API 暴露。infraredComp 镜像本库。

> **任务数据单源**：任务（看板 + 项目树）的唯一来源是 **per-project `management/docs/projects/{slug}/tasks.json`**（层级树）。看板（TaskBoard）是它的**派生视图**——按 status 展平成 3 桶，按项目切换。`tasks.md` 已废弃删除。成员/报表/会议/里程碑仍是 markdown。

## 脚本一览（`.claude/skills/management/scripts/`）

脚本 **self-locating**（用 `parents[4]` 解析仓库根），同一份文件在上下游都能跑（两库 `tasks.json` schema 一致）。纯标准库，`python3` 直接运行。

| 实体 | 新增 | 修改 | 删除 | 查询 |
|------|------|------|------|------|
| 任务 task（tasks.json） | `add_task.py` | `update_task.py`（含改 status 跨段） | `delete_task.py` | `list_tasks.py` |
| 成员 member | `add_member.py` | `update_member.py` | `delete_member.py` | — |
| 会议 meeting | `create_meeting.py` | `update_meeting.py` | `delete_meeting.py` | — |
| 报表 report | `create_report.py` | `update_report.py` | `delete_report.py` | — |

## 项目结构

```text
management/
├── team/           # 团队成员
│   ├── README.md   # 成员列表表(姓名|英文标识|角色|入职日期) + 暂无占位
│   └── {id}.md     # 个人档案(基本信息表 + 技术栈 + 负责模块 + 备注)
├── daily/          # 日报  YYYY/MM/DD-{author}.md
├── weekly/         # 周报  YYYY/W{NN}-{author}.md
├── monthly/        # 月报  YYYY/{MM}-{author}.md
└── docs/
    ├── milestones.md # 里程碑
    ├── projects/   # 项目树 {slug}/README.md + tasks.json（任务单源）+ notes/
    └── meetings/   # 会议纪要 YYYY-MM-DD.md
```

启动服务（后端 8090 + 前端 3002）：`bash start_services.sh`。日志 `/tmp/<项目名>-backend.log`、`/tmp/<项目名>-frontend.log`。

只读 API（`GET /api/management/*`）：`team`、`daily`、`weekly`、`monthly`、`tasks`（`?slug=` 派生看板，缺省取首个项目）、`milestones`、`meetings`、`projects` 等。脚本改完文件，前端经 API 即可看到。

---

## 1. 任务 CRUD（per-project tasks.json）

任务数据**单源** = `management/docs/projects/{slug}/tasks.json`（层级树，与项目树页同源）。看板是派生视图：`server/parsers/tasks_parser.parse_tasks(slug)` 递归展平所有节点，按 status 映射进 3 桶：

- `completed` → completed
- `active` → in_progress
- `planned` / `paused` / `blocked` → pending

任务节点 schema：
```json
{
  "id": "t1-1", "title": "...", "status": "completed|active|planned|paused|blocked",
  "startDate": "2026-07-08", "endDate": "2026-07-10", "assignee": "张三",
  "description": "...", "notePath": "notes/01.md", "priority": "P1",
  "hidden": true,
  "progress": [ { "date": "2026-07-16", "note": "完成了 X" } ],
  "children": [ ... ]
}
```

字段说明补充：
- `hidden: true` — 项目树默认不展示此节点（前端眼睛图标可切换显示，节点以半透明斜体呈现）。子任务会随父任务一起隐藏。用法：`add_task.py --hidden` / `update_task.py --hidden` 或 `--no-hidden`。

```bash
SD=.claude/skills/management/scripts

# 新增根级任务（id 自动生成 tN）
python3 $SD/add_task.py --slug myproject --title "模块X开发" --status active \
  --assignee 张三 --start 2026-07-11 --end 2026-07-18 --description "备注" --note-path notes/x.md
# 新增子任务（挂到 t2 下，id 自动生成 t2-N）
python3 $SD/add_task.py --slug myproject --parent t2 --title "Y调研" --status planned --priority P1

# 修改字段（只改传了的；--status 即跨段移动，看板桶随之变）
python3 $SD/update_task.py --slug myproject --id t2-3 --status active --assignee 李四
# 改名 / 改日期
python3 $SD/update_task.py --slug myproject --id t2-3 --title "模块X v2" --end 2026-07-20
# 标记完成
python3 $SD/update_task.py --slug myproject --id t2-3 --status completed
# 追加进展记录（自动加日期，新条目在前）
python3 $SD/update_task.py --slug myproject --id t2-3 --progress "完成 API 对接，数据可正常加载"
# 完成 + 完成总结（一步到位）
python3 $SD/update_task.py --slug myproject --id t2-3 --status completed \
  --progress "[完成] 修复分页 bug——根因是 offset 未重置，已在 onMounted 中加 resetPage() 解决"

# 删除（递归删节点及其子树）
python3 $SD/delete_task.py --slug myproject --id t2-3

# 查询（树视图 / 展平看板桶 / 按 status 过滤 / 按 ID 精确定位）
python3 $SD/list_tasks.py --slug myproject              # 树视图
python3 $SD/list_tasks.py --slug myproject --flat       # 展平成 看板 三桶
python3 $SD/list_tasks.py --slug myproject --status active
python3 $SD/list_tasks.py --slug myproject --id t2-3    # 单个任务详情（含 progress）
```

`--status` 接受 canonical（completed/active/planned/paused/blocked）或别名（done/in_progress/ongoing/todo/pending）。

### 1.1 任务描述（description）写作规范

**反模式**：把所有信息塞进一行的 description 字段（标题、范围、交付物、约束都连在一起），导致看板/项目树悬浮卡只看到一行密密麻麻的字。

**正确做法**：description 字段允许 `\n` 换行（前端 `white-space: pre-line` 渲染）。按下面结构写，每段各司其职：

```
<一句话定位：做什么 + 为什么>                       ← 必填
                                                   ← 一个空行
• <要点 1：范围 / 交付物 / 约束>                    ← 2-4 条，可选
• <要点 2：关键依赖或验收标准>
• <要点 3：非目标 / 不在范围内>
```

**硬性规则**：
1. 首行必须是**单句定位**，≤ 40 汉字，回答"这个任务到底要做什么"。不要复述 title。
2. 要点段用 `• `（U+2022 + 空格）开头，每条独立成行；不要写 `- ` 或 `* `（会被当成 markdown 渲染错乱）。
3. 每条要点 ≤ 60 汉字；超过就拆成两条。
4. 整段 ≤ 6 行（含空行）。太长说明该拆子任务了，不要堆在 description 里。
5. **禁止**：HTML 标签、emoji、markdown 链接、`TODO:` 前缀、"详见 notePath" 这种占位废话。
6. 中文语境下英文专有名词首字母大写（PyTorch 不是 pytorch），且左右各留一个半角空格。
7. 如果任务已经挂了 `notePath`，description 仍要独立可读（用户不点进笔记也能看懂）。

**好例子**（tasks.json 中的 description 值）：
```json
"description": "为项目树页面包裹一层 Git 风格的分支线，让层级关系一眼可见。\n\n• 输入：任意深度 children 数组，输出递归分支线 + 悬浮卡\n• 首屏性能：500 节点内 < 100ms 渲染完成\n• 不在范围内：节点拖拽排序（放到 t9）"
```

**坏例子**：
```json
"description": "实现项目树页面的分支线渲染逻辑，用递归组件包裹每个 task node，支持任意深度，带 git 风格连接线，悬浮卡展示详情，要求性能达标（500节点<100ms），不包括拖拽排序功能，那个放到后面的 t9 里做。"
```

**调用专用 subagent（推荐）**：创建/修改任务时，若 description 需要新写或重写，主 agent 应派生一个 `general-purpose` subagent 专门产出描述文本，避免主上下文被写作过程污染。

- **提示词文件**：`.claude/agents/description-writer.md`（frontmatter 含 subagent 类型、输入/输出约定、完整规则）
- **调用方式**：
  1. 读取 `.claude/agents/description-writer.md` 正文
  2. 在末尾追加：`任务 title：<TITLE>\n上下文：<CONTEXT>`（占位符替换为实际值）
  3. 通过 `Agent` 工具派生 subagent（`subagent_type: general-purpose`）
  4. subagent 返回的字符串即 description 值，原样传给 `add_task.py --description "..."` 或 `update_task.py --description "..."`

> 写作规范的**人读版**（给主 agent / 人类 review 用）见上面的"硬性规则"。subagent 提示词是其**机器读版**，含更严格的输出格式约束（只输出字符串本身，不要前言后语）。两份要保持语义一致；修改规范时两处同步更新。

### 1.2 工作流公约（任务状态同步）

每完成一个用户请求，检查是否有对应的任务需要更新状态或进展。**铁律**：做了事就要记到任务树上，不要只做事不更新。

**开始工作时**（把任务从 planned → active）：
```bash
python3 $SD/update_task.py --slug <slug> --id <id> --status active
```

**推进过程中**（每完成一个有意义的步骤，追加一条 progress）：
```bash
python3 $SD/update_task.py --slug <slug> --id <id> --progress "完成了 X，下一步 Y"
```

**完成工作时**（status → completed + 完成总结一步到位）：
```bash
python3 $SD/update_task.py --slug <slug> --id <id> --status completed \
  --progress "[完成] <方法总结>"
```

**通过编号查找任务**（agent 快速定位任务详情）：
```bash
python3 $SD/list_tasks.py --slug <slug> --id <task-id>
```

**progress 格式规则**：
1. 进展记录：1-2 句话，不要复述代码变更，写"做了什么 + 下一步"。
2. 完成总结：以 `[完成]` 开头，侧重"怎么做 + 遇到什么问题 + 怎么解决"，不写"做了什么"（title 已经说了）。
3. 每条 note ≤ 120 汉字。太长说明该拆子任务了。
4. 不要写空泛的进展（"继续开发中"、"修了一些 bug"）。

---

## 2. 团队成员 CRUD

```bash
# 新增（自动去掉 README 的"暂无"占位行，并生成 {id}.md 档案）
python3 $SD/add_member.py --name 张三 --id zhangsan --role 算法工程师 \
  --join-date 2026-01-15 --research "大语言模型" --tech "Python,PyTorch,Transformers" --modules "论文,评测"

# 修改（按 --id 定位；--new-id 会改 id 并重命名档案文件）
python3 $SD/update_member.py --id zhangsan --role "高级算法工程师" --join-date 2026-01-15
python3 $SD/update_member.py --id zhangsan --name 张三丰 --new-id zhangsanfeng

# 删除（同时删 README 行 + 档案文件；--keep-profile 保留档案）
python3 $SD/delete_member.py --id zhangsan
python3 $SD/delete_member.py --id zhangsan --keep-profile
```

---

## 3. 报表 CRUD

文件路径：daily `YYYY/MM/DD-{author}.md`、weekly `YYYY/W{NN}-{author}.md`、monthly `YYYY/{MM}-{author}.md`。

```bash
# 创建
python3 $SD/create_report.py --type daily   --author zhangsan --date 2026-07-11
python3 $SD/create_report.py --type weekly  --author zhangsan --year 2026 --week 28
python3 $SD/create_report.py --type monthly --author zhangsan --year 2026 --month 07

# 更新（追加工作/计划条目，或重写备注）
python3 $SD/update_report.py --type daily --author zhangsan --date 2026-07-11 \
  --append-work "完成 X 模块" --append-plan "优化 Y" --note "ok"

# 删除
python3 $SD/delete_report.py --type daily   --author zhangsan --date 2026-07-11
python3 $SD/delete_report.py --type weekly  --author zhangsan --year 2026 --week 28
python3 $SD/delete_report.py --type monthly --author zhangsan --year 2026 --month 07
```

---

## 4. 会议纪要 CRUD

文件：`management/docs/meetings/YYYY-MM-DD.md`。

```bash
# 创建
python3 $SD/create_meeting.py --date 2026-07-11 \
  --participants "张三、李四" --recorder 张三 --topics "进度回顾,方案讨论" \
  --decision "确认 X 方案" --todo "张三:完成 X"

# 更新（换参会人/记录人，追加决议/待办）
python3 $SD/update_meeting.py --date 2026-07-11 --participants "张三、李四、王五" \
  --append-decision "追加决议" --append-todo "李四:调研 Y"

# 删除
python3 $SD/delete_meeting.py --date 2026-07-11
```

---

## 5. 里程碑 / 项目树

`milestones.md` 单表（名称|目标日期|状态|备注），暂无专用 CRUD 脚本，直接编辑 markdown 即可，只读 API `GET /api/management/milestones` 解析。

项目树 `docs/projects/{slug}/`：`README.md`（项目元信息 + 正文）+ **`tasks.json`（任务单源，CRUD 见 §1）** + `notes/`（任务笔记 markdown，task 节点 `notePath` 引用）。只读 API `GET /api/management/projects[/{slug}[/tasks|/notes/{path}]]` 解析。项目树页与看板页读同一份 `tasks.json`。

## 关键约定

- **只读后端**：management 后端只读数据文件；所有写操作走本 skill 脚本（直接改文件 + 原子写：tmp + os.replace）。
- **任务单源 tasks.json**：任务（看板+项目树）唯一来源是 per-project `tasks.json`。看板（`tasks_parser.parse_tasks(slug)`）递归展平 + 按 status 映射成 3 桶；项目树页直接读同一份树。改一处，两处同步。
- **跨段移动 = 改 status**：`update_task --status completed|active|planned|paused|blocked` 即把任务移到对应看板桶（无独立 move 概念）。
- **id 自动生成**：`add_task` 根级生成 `tN`（现有根级最大号 +1），子任务生成 `{parent}-N`，保证项目内不重复。
- **parser 兼容（markdown 实体）**：成员/会议/报表/里程碑仍是 markdown 表格；脚本的表格编辑器**保留表头**、按段实际列数生成行，与对应 parser（按表顺序 + 按表头名取列）兼容。空表保留（header+separator 无数据行也保留），保证位置映射不错位。
- **自定位**：脚本用 `parents[4]` 解析仓库根，从任意 cwd 运行均可；同一份文件在上下游通用。

## 常用命令

```bash
SD=.claude/skills/management/scripts
python3 $SD/list_tasks.py --slug myproject          # 看任务树
python3 $SD/list_tasks.py --slug myproject --flat   # 看展平看板桶
python3 $SD/add_task.py --slug myproject --title "X" --status active --assignee Y --start 2026-07-11 --end 2026-07-18
bash start_services.sh                             # 启动后端 8090 + 前端 3002
curl --noproxy '*' "http://localhost:8090/api/management/tasks?slug=myproject"   # 前端所见看板
tail -f /tmp/<项目名>-backend.log                  # 后端日志
```
