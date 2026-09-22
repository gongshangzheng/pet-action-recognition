// ============================================================
// 站点图标（favicon）形状集合
//
// 浏览器标签页图标读不到 CSS 变量，因此由 JS 按当前强调色 + 明暗模式
// 生成 SVG 并写入 <link rel="icon"> 的 data URL。
//
// 设计：32×32 圆角方块（底色 = 强调色）+ 前景形状（取底色的可读对比色）。
// 不用「透明底 + 彩色形状」——深色强调色（如枪灰）在深色标签栏上会看不见。
// ============================================================
import { readableOn } from './theme'

export const DEFAULT_FAVICON = 'bolt'

// 每个形状是 (color) => svg 片段；几何路径在 16px 下仍可辨识。
const MARKS = {
  bolt: (c) => `<path fill="${c}" d="M18 3.5 8 17.5h6.5l-1 11L24 14h-6.5l.5-10.5Z"/>`,
  flow: (c) => `<path fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M6 16h4.5l3-8 4.5 16 3-8H26"/>`,
  grid: (c) => `<g fill="${c}"><rect x="6" y="6" width="8.4" height="8.4" rx="2"/><rect x="17.6" y="6" width="8.4" height="8.4" rx="2"/><rect x="6" y="17.6" width="8.4" height="8.4" rx="2"/><rect x="17.6" y="17.6" width="8.4" height="8.4" rx="2"/></g>`,
  layers: (c) => `<g fill="${c}"><rect x="6" y="8" width="20" height="4" rx="2"/><rect x="6" y="14" width="20" height="4" rx="2"/><rect x="6" y="20" width="13" height="4" rx="2"/></g>`,
  hex: (c) => `<path fill="${c}" d="M16 3.6 26.6 9.8v12.4L16 28.4 5.4 22.2V9.8Z"/>`,
  spark: (c) => `<path fill="${c}" d="M16 3.6 19.2 12.8 28.4 16 19.2 19.2 16 28.4 12.8 19.2 3.6 16 12.8 12.8Z"/>`,
}

// 供 UI 遍历；label 用于 hover 提示
export const FAVICONS = [
  { key: 'bolt', label: '闪电' },
  { key: 'flow', label: '脉冲' },
  { key: 'grid', label: '网格' },
  { key: 'layers', label: '层级' },
  { key: 'hex', label: '六边形' },
  { key: 'spark', label: '星芒' },
]

export function isFaviconKey(key) {
  return FAVICONS.some((f) => f.key === key)
}

/** 生成完整 SVG 字符串；预览（v-html）与真图标（data URL）共用。 */
export function faviconSvg(key, bgColor) {
  const shape = MARKS[key] || MARKS[DEFAULT_FAVICON]
  const mark = readableOn(bgColor)
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">` +
    `<rect width="32" height="32" rx="7" fill="${bgColor}"/>` +
    `${shape(mark)}` +
    `</svg>`
  )
}

/** 供 <link rel="icon"> 使用的 data URL。 */
export function faviconDataUrl(key, bgColor) {
  return 'data:image/svg+xml,' + encodeURIComponent(faviconSvg(key, bgColor))
}
