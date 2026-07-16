---
name: projflow-management
description: |
  ProjFlow 项目管理模块操作指南。用于团队成员管理、日报/周报/月报、任务（看板+项目树）、里程碑、会议纪要等 CRUD 操作（脚本直接改文件，后端只读）。
  触发场景：(1) 添加/修改/删除团队成员，(2) 创建/更新/删除报表，(3) 管理任务(增删改查+改状态跨段移动)，(4) 创建/更新/删除会议纪要，(5) 了解项目结构
---

# ProjFlow 项目管理模块

本 skill 提供 ProjFlow 项目管理模块（`management/`）的完整操作指南，以及一套**自定位**的 CRUD 脚本，直接读写 `management/` 下的数据文件。

> **架构前提**：后端 `server/routers/management.py` 是**只读**的（解析数据文件暴露给前端）。所有"增删改"由本 skill 的脚本直接修改文件完成，再由只读 API 暴露。infraredComp 镜像本库。

> **任务数据单源**：任务（看板 + 项目树）的唯一来源是 **per-project `management/docs/projects/{slug}/tasks.json`**（层级树）。看板（TaskBoard）是它的**派生视图**——按 status 展平成 3 桶，按项目切换。`tasks.md` 已废弃删除。成员/报表/会议/里程碑仍是 markdown。

## 脚本一览（`.claude/skills/projflow-management/scripts/`）

脚本 **self-locating**（用 `parents[4]` 解析仓库根），同一份文件在 ProjFlow 与 infraredComp 都能跑（两库 `tasks.json` schema 一致）。纯标准库，`python3` 直接运行。

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

启动服务（后端 8090 + 前端 3002）：`bash start_services.sh`。日志 `/tmp/projflow-backend.log`、`/tmp/projflow-frontend.log`。

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
  "children": [ ... ]
}
```

```bash
SD=.claude/skills/projflow-management/scripts

# 新增根级任务（id 自动生成 tN）
python3 $SD/add_task.py --slug projflow --title "模块X开发" --status active \
  --assignee 张三 --start 2026-07-11 --end 2026-07-18 --description "备注" --note-path notes/x.md
# 新增子任务（挂到 t2 下，id 自动生成 t2-N）
python3 $SD/add_task.py --slug projflow --parent t2 --title "Y调研" --status planned --priority P1

# 修改字段（只改传了的；--status 即跨段移动，看板桶随之变）
python3 $SD/update_task.py --slug projflow --id t2-3 --status active --assignee 李四
# 改名 / 改日期
python3 $SD/update_task.py --slug projflow --id t2-3 --title "模块X v2" --end 2026-07-20
# 标记完成
python3 $SD/update_task.py --slug projflow --id t2-3 --status completed

# 删除（递归删节点及其子树）
python3 $SD/delete_task.py --slug projflow --id t2-3

# 查询（树视图 / 展平看板桶 / 按 status 过滤）
python3 $SD/list_tasks.py --slug projflow              # 树视图
python3 $SD/list_tasks.py --slug projflow --flat       # 展平成 看板 三桶
python3 $SD/list_tasks.py --slug projflow --status active
```

`--status` 接受 canonical（completed/active/planned/paused/blocked）或别名（done/in_progress/ongoing/todo/pending）。

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
- **自定位**：脚本用 `parents[4]` 解析仓库根，从任意 cwd 运行均可；同一份文件在 ProjFlow 与 infraredComp 通用。

## 常用命令

```bash
SD=.claude/skills/projflow-management/scripts
python3 $SD/list_tasks.py --slug projflow          # 看任务树
python3 $SD/list_tasks.py --slug projflow --flat   # 看展平看板桶
python3 $SD/add_task.py --slug projflow --title "X" --status active --assignee Y --start 2026-07-11 --end 2026-07-18
bash start_services.sh                             # 启动后端 8090 + 前端 3002
curl --noproxy '*' "http://localhost:8090/api/management/tasks?slug=projflow"   # 前端所见看板
tail -f /tmp/projflow-backend.log                  # 后端日志
```
