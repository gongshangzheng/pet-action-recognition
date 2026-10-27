# Tasks: docs-page-narrow-selector

- [ ] 1.1 `DocPage.vue` 根容器改为窄屏 `column` / 宽屏 `row`（断点 1024px），窄屏 `gap: 12px`、`padding: 16px`。
- [ ] 1.2 `.doc-mobile-select` 窄屏 `width: 100%`、去掉 `margin-bottom`；`n-select` 加 `:consistent-menu-width="false"`。
- [ ] 1.3 正文卡片内边距窄屏收紧（<640px 时 16px），保证正文字宽优先。
- [ ] 1.4 冒烟：390px / 768px / 1024px / 1440px 四档视口检查——选择器整宽独占一行、正文占满剩余宽度、宽屏三栏与两侧收起把手行为不变。（本机无可用无头浏览器，构建层已验证规则落地：`dist/assets/DocPage-*.css` 含窄屏 `flex-direction:column` 与 ≥1024px `row` 覆盖；**目视确认待用户**）
- [x] 1.5 `cd web && npm run build` 通过；构建产物包含新断点规则（`doc-page{flex-direction:column;gap:12px;padding:16px}` + `@media(min-width:1024px){flex-direction:row;gap:24px}`）。
- [x] 1.6 反哺上游 ProjFlow：`75e5284 [shared] fix(web): 文档页窄屏布局——选择器独占一行，正文整宽` 已推送 `upstream/main`（含同款 proposal/design/tasks/spec delta），本库以同内容落地。
