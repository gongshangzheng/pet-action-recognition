// 文档取数来源切换层。
//
// - 本地开发（vite dev）：走 FastAPI，改 management/docs/ 刷新即见。
// - 生产构建（GitHub Pages 等无后端场景）：读构建期生成的 web/public/docs-data.json
//   （由 web/scripts/build-docs-data.mjs 产出，字段与后端文档接口一致）。
//
// 组件只依赖这里，不关心具体来源。
import {
  getDocList as apiDocList,
  getDocDetail as apiDocDetail,
} from './management'

const USE_STATIC = import.meta.env.PROD

// 正文按文档图片约定写绝对路径 /api/management/docs-assets/...；
// 静态托管没有该端点，读取静态数据时改写到产物内的 docs-assets/（随 BASE_URL 解析）。
// 源 Markdown 不改写 —— 它要同时满足 article-note 的校验与本地开发的后端端点。
const API_ASSET_PREFIX = '/api/management/docs-assets/'

function toStaticAssetUrls(content) {
  if (!content) return content
  return content.split(API_ASSET_PREFIX).join(`${import.meta.env.BASE_URL}docs-assets/`)
}

let staticCache = null

async function loadStaticData() {
  if (staticCache) return staticCache
  const url = `${import.meta.env.BASE_URL}docs-data.json`
  const response = await fetch(url, { cache: 'no-cache' })
  if (!response.ok) {
    throw new Error(`无法加载文档静态数据 ${url}（HTTP ${response.status}）`)
  }
  staticCache = await response.json()
  return staticCache
}

export async function getDocList() {
  if (!USE_STATIC) return apiDocList()
  const data = await loadStaticData()
  return data.docs || []
}

export async function getDocDetail(slug) {
  if (!USE_STATIC) return apiDocDetail(slug)
  const data = await loadStaticData()
  const doc = data.details?.[slug]
  // 与后端 404 行为一致：以错误结束，由调用方显示空态
  if (!doc) throw new Error(`Doc not found: ${slug}`)
  return { ...doc, content: toStaticAssetUrls(doc.content) }
}
