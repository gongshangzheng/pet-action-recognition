# 项目进程管理

项目树（`tasks.json`）与看板（TaskBoard）是本项目唯一的任务记忆来源。

## 原则

- **单源 truth**：`management/docs/projects/pet-action-recognition/tasks.json` 同时驱动项目树页与看板页，改一处即可同步两处视图。
- **勤更新**：每次关键进展、状态变更、发现新任务或任务完成时，立即更新任务树与看板，避免项目记忆与实际进展脱节。
- **状态约定**：
  - `completed` → 已完成
  - `active` → 进行中
  - `planned` / `paused` / `blocked` → 待开始

## 常用操作

```bash
SD=.claude/skills/management/scripts

# 查看任务树
python3 $SD/list_tasks.py --slug pet-action-recognition

# 查看看板三桶
python3 $SD/list_tasks.py --slug pet-action-recognition --flat

# 新增任务
python3 $SD/add_task.py --slug pet-action-recognition --title "XX" --status active --assignee 姓名

# 更新状态（即跨段移动）
python3 $SD/update_task.py --slug pet-action-recognition --id tN --status completed
```

改完后启动服务即可在前端看板与项目树中看到最新状态。
