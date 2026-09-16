mtime 证实：docs-repo-inventory 的改动发生在 15:57–15:58（我创建 change 之前/期间，由并行会话完成），我全程未写入该目录。本任务仅新增 `openspec/changes/chore-toplevel-cleanup/` 下 4 个规划文件。

---

# 汇报

## Change
**`chore-toplevel-cleanup`** @ `openspec/changes/chore-toplevel-cleanup/`
- ✅ `openspec validate` → **"Change 'chore-toplevel-cleanup' is valid"**（exit 0）
- ✅ `openspec status` → **3/3 artifacts complete**（proposal [x] / specs [~] skipped via `skip_specs: true` / design [x] / tasks [x]）

## 逐文件处置结论摘要（证据已核实）

| 文件 | git 跟踪 | 核实证据 | 处置 |
|---|---|---|---|
| CanvasPlayer.vue | 是（d996aec 09-14 新增） | ≠ web 版（web 版多 NSpin/emits/status，超集）；无引用 | git rm，独立 commit |
| Live.vue | 是（d996aec） | ≠ web/src/views/Live.vue（web 版含源管理 modal 等）；无引用 | git rm，独立 commit |
| live.py | 是（d996aec） | ≠ server/routers/live.py（server 版多 sources CRUD，超集）；无引用 | git rm，独立 commit |
| live_stream.py | 是（d996aec） | ≠ scripts/live_stream.py（scripts 版 cv2+read_frame 更新）；无引用 | git rm，独立 commit |
| config.py | 是（d996aec） | **与 server/config.py 逐字节一致**；server 全用 `from server.config import` | git rm，独立 commit |
| package-lock.json | 是（75f0956） | 101B 空壳 `packages:{}`；根目录无 package.json；真 lock 在 web/（已 ignore） | git rm + .gitignore 补 `/package-lock.json` |
| remix_-派爪petra.zip | 否（7f61991 移除） | 27 条目 vs third-party/remix-petra/ 25 文件：同名组件、cats-reacting.mp4、乱码名吻合 → 内容一致 | 可删，**待用户确认**（不可恢复） |
| pet-videos.zip | 否（7f61991） | zip 双层嵌套含内嵌 .git+__MACOSX（407 条目）≠ third-party/pet-videos/ 平铺 277 文件 → **不一致** | **默认保留，待用户裁定** |
| data/papers.db.bak-seed | 否（`data/*.bak*` 已 ignore） | 现库 papers.db integrity ok、当日活跃；种子可由 extracted_papers.json 重建 | 可删，**待用户确认** |
| .playwright-mcp/ | 否（已 ignore，check-ignore 验证） | playwright MCP 可能正在使用 | 保留不动 |
| checkpoints/ | 否（`/checkpoints/` 已 ignore） | 空目录；权重在远程 | 保留不动 |
| 散落 .DS_Store | 否（已 ignore） | 根+8 个子目录共 15+ 处，纯 Finder 元数据 | 本地 find 删除，不入 commit |

**取证要点**：五个代码副本同秒时间戳（Sep 14 11:19）与 d996aec（09-14 11:17，A 状态批量添加、未动 web/server）吻合，确证为同一次 pet 服务器工作区误拷贝；`git log --all --find-object` 证实根副本内容从未出现在正式路径演化史中，但正式版本均为功能超集且内容永久留存于 git 历史（revert 可恢复）。另核实“web 静态服务泄露”不成立（server/main.py 无 StaticFiles 挂载、vite 以 web/ 为根）。

**未动任何仓库既有文件**：git status 仅新增我的 change 目录；docs-repo-inventory 的 M 标记系并行会话 15:57–15:58 所为（早于我写入时间），非本任务产物。