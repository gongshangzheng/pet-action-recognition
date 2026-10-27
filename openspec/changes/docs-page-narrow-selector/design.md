# Design: docs-page-narrow-selector

## 根因

```scss
.doc-page { display: flex; gap: 24px; }   // 固定横向

@media (max-width: 1023px) {
  .doc-sidebar      { display: none; }     // 左栏让位给选择器
  .doc-mobile-select { display: block; }   // ← 但它仍是横向 flex 子项
}
```

`n-select` 根元素默认 `width: 100%`，在横向 flex 容器里表现为一个大宽度子项；正文 `.doc-article{flex:1}`
只能吃剩下的零头。宽屏没暴露该问题，因为那时 `.doc-mobile-select` 是 `display: none`。

## 方案：方向随断点切换（不改 DOM 结构）

DOM 保持「左栏 / 选择器 / 正文 / 右栏」四段不变（选择器本来就在正文之前），只让容器方向随断点变化：

| 视口 | 容器 | 选择器 | 左栏 | 右栏 TOC |
|---|---|---|---|---|
| <1024px | `column`，`gap: 12px`，`padding: 16px` | 显示，`width: 100%`，独占一行 | 隐藏 | 隐藏（<1280） |
| ≥1024px | `row`，`gap: 24px`，`padding: 20px 24px` | 隐藏 | 显示（可收起） | <1280 隐藏，≥1280 显示（可收起） |

- 选择器不再需要 `margin-bottom`（纵向 `gap` 已提供间距），避免窄屏下双重留白。
- 正文卡片内边距在 <640px 收紧到 16px：窄屏横向像素最稀缺，正文内容宽度优先。
- 下拉菜单不跟随触发器宽度（`consistent-menu-width: false`）：触发器整宽只是为了让选择器好点，
  弹层被拉成整屏宽会更丑。

## 不做

- 不做选择器吸顶（sticky）：滚动容器是布局层的 `.app-content`，吸顶需与滚动记忆/TOC 吸顶协调，收益小于风险；
  若后续确需，另开 change。
- 不把左栏改成抽屉：窄屏的既有方案（下拉选择器）已被规格接受，本次只修空间分配。
