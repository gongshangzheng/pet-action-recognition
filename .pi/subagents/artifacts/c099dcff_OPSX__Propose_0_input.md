# Task for OPSX: Propose

在 /Users/zhengxinyu/pet-action-recognition 创建一个 OpenSpec change（仅创建规划工件，绝对禁止移动/删除/修改任何仓库文件——这是纯规划任务）。主题：顶层散落文件清理。

背景：仓库根目录有一批散落/残留文件，用户要求立专项 change 说明如何清理。初步盘点（2026-09-16）发现以下可疑项，你必须逐一核实后再下处置结论：
- CanvasPlayer.vue（3.3KB，9-14 修改）——疑似 web 组件误放根目录；对比 web/src/components/ 是否已有同名/相似组件
- Live.vue（10.7KB，9-14）——对比 web/src/views/Live.vue
- live.py（7.5KB，9-14）——docstring 自称 Live 路由，对比 server/routers/live.py
- live_stream.py（6.2KB，9-14）——scripts/ 下也有 live_stream.py，对比两者
- config.py（3.9KB，9-14）——对比 server/config.py
- pet-videos.zip（14.8MB，只读权限 r--r--r--）——third-party/pet-videos/ 目录已存在（疑似同一内容的解压版，用 unzip -l 对比清单确认，不要解压）
- remix_-派爪petra.zip（15.3MB，只读权限）——third-party/remix-petra/ 同理
- package-lock.json（仅 101 字节，7-11）——根目录可疑空壳（真正的前端在 web/）
- .playwright-mcp/（Aug 10，59 项）——playwright MCP 临时产物目录
- checkpoints/（本地空目录）——权重实际在远程 pet 服务器
- data/papers.db.bak-seed（32KB，8-31）——数据库种子备份
- 散落 .DS_Store 若干

注意：上面 *.vue/*.py 五个文件时间戳同为 Sep 14 11:19，疑似同一次误拷贝到根目录。务必用 git ls-files / git log --oneline -- <file> 查每个文件是否被 git 跟踪及其提交历史，用 diff 对比与疑似正式位置文件的异同，给出证据。

操作步骤（openspec CLI）：
1. openspec new change "chore-toplevel-cleanup"（名字可微调但保持 kebab-case）
2. openspec status --change <name> --json 获取工件构建顺序
3. 逐个 openspec instructions <artifact> --change <name> --json，按返回的 template 写 proposal.md / design.md / tasks.md
4. 这是纯文件清理变更（无行为变更）：在 .openspec.yaml 中加 skip_specs: true（参考 openspec/changes/docs-repo-inventory/.openspec.yaml 的写法）

工件内容要求：
- proposal.md：Why（根目录污染、误导协作者与 AI、zip 占仓库体积、web 静态服务可能泄露）；What Changes 逐文件处置；Impact（涉及 git rm / .gitignore / 无代码行为变更）
- design.md：必须包含逐文件去留决策表，列：文件 → 核实证据（diff 结果/是否被 git 跟踪/提交历史）→ 处置（git rm 删除 | 未跟踪直接删 | 移动到正确位置 | 保留并补 .gitignore | 保留不动+理由）→ 风险与回滚方式。特别注意：① .playwright-mcp/ 可能正被 playwright MCP 工具使用，默认建议保留+确认 .gitignore 覆盖；② 两个 zip 若 third-party/ 解压版内容一致则可删，若有差异需标注待用户确认；③ papers.db.bak-seed 是种子备份，删除前确认 data/ 现库健康；④ 处置动作分独立 commit（chore: remove ...），可单点 revert
- tasks.md：按「1 逐文件核实取证 → 2 执行删除/移动（分 commit）→ 3 .gitignore 补充 → 4 验证（git status 干净、bash start_services.sh 服务仍正常、web 页面可打开）」分阶段写勾选框任务

完成后：openspec validate <name> 必须通过；openspec status 显示 3/3 artifacts complete。最终汇报：change 名称、逐文件处置结论摘要表、validate 结果。再次强调：只写规划工件，不动任何仓库文件。

## Acceptance Contract
Acceptance level: checked
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope

Required evidence: changed-files, tests-added, commands-run, residual-risks, no-staged-files

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
`criteriaSatisfied[].status` must be exactly one of: satisfied, not-satisfied, not-applicable.
`commandsRun[].result` must be exactly one of: passed, failed, not-run.
`manualNotes` and `notes` are optional strings; an empty string means no note and does not satisfy `manual-notes` evidence.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```