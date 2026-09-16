# shasum 留档证据（2026-09-16 清理前）

> 注：以下三项文件已按设计删除；本文件保留删除前的 sha256 留档备查。

## 删除的三项未跟踪文件

| 文件 | sha256（删除前） | size | 处置 | 来源 commit 留档依据 |
|---|---|---|---|---|
| `remix_-派爪petra.zip` | `daacb4fff19481a1a4526794923e2acd21914e02f1d5d8b504806b2aca6f08b0` | 15287763 字节 | 删除（与 third-party/remix-petra/ 内容一致） | 与解压版目录树对位 25 文件 |
| `pet-videos.zip` | `9920efd0502b295f49fab9360d0b2d4894017185c6ab17fb6849ec2fb1fb82fa` | 14807343 字节 | 删除（用户批复接受内容不一致风险） | 双层嵌套 + 完整 .git + __MACOSX，407 条目；与 third-party 平铺 277 文件不完全一致 |
| `data/papers.db.bak-seed` | `3da6dee725b60c1657df8fe025bf4d1f58e40cc0174100b7c2e2572ac15c4f8c` | 32768 字节 | 删除（现库 integrity ok，种子可由 extracted_papers.json 重建） | 2026-08-31 种子备份 |

## 现库健康检查（删除 bak-seed 前）

```
sqlite3 data/papers.db "PRAGMA integrity_check;" → ok
sqlite_master 表数 → 7
papers 行数 → 239
paper_categories 行数 → 519
```

## Gitignore 覆盖复核（删除前）

| 路径 | ignore 命中位置 | 状态 |
|---|---|---|
| `.playwright-mcp/` | `.gitignore:62` | ✓ 已 ignore |
| `.DS_Store` | `.gitignore:46` | ✓ 已 ignore |
| `/checkpoints/` | `.gitignore:27` | ✓ 已 ignore |
| `data/*.bak*` | `.gitignore:68` | ✓ 已 ignore（备份文件入库被阻止） |
| `/live/` | `.gitignore` 后增 | ✓ 已 ignore |