#!/usr/bin/env node
// 构建期把 management/docs/ 编译为前端可读的静态数据（web/public/docs-data.json）。
//
// 为什么在这里生成：GitHub Pages 上只有静态文件，没有 FastAPI。文档页在生产构建里
// 改读这份数据；本地开发仍走后端 API（见 web/src/api/docs.js）。
//
// frontmatter 只支持本仓库实际用到的 YAML 子集（单行 key: value / 内联数组 / 数字）。
// 遇到不支持的写法直接报错退出，绝不静默产出缺字段的数据。

import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const WEB_DIR = resolve(__dirname, '..')
const REPO_ROOT = resolve(WEB_DIR, '..')
const DOCS_DIR = join(REPO_ROOT, 'management', 'docs')
const OUT_FILE = join(WEB_DIR, 'public', 'docs-data.json')

function fail(message) {
  console.error(`[build-docs-data] ${message}`)
  process.exit(1)
}

function walkMarkdown(dir) {
  const found = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) found.push(...walkMarkdown(full))
    else if (entry.isFile() && entry.name.endsWith('.md')) found.push(full)
  }
  return found
}

function unquote(value) {
  const s = value.trim()
  if (s.length >= 2) {
    const first = s[0]
    const last = s[s.length - 1]
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) return s.slice(1, -1)
  }
  return s
}

function parseScalar(raw) {
  const v = raw.trim()
  if (v === '') return ''
  if (v.startsWith('[') && v.endsWith(']')) {
    const inner = v.slice(1, -1).trim()
    if (!inner) return []
    return inner.split(',').map((item) => unquote(item))
  }
  if (/^-?\d+$/.test(v)) return Number(v)
  if (/^-?\d+\.\d+$/.test(v)) return Number(v)
  return unquote(v)
}

/** 返回 [meta, body]；body 的切法与后端 _parse_frontmatter 一致。 */
function parseFrontmatter(content, file) {
  if (!content.startsWith('---')) return [{}, content]
  const end = content.indexOf('---', 3)
  if (end < 0) fail(`${file}: frontmatter 起始 --- 之后没有结束 ---`)
  const head = content.slice(3, end).split('\n')
  const meta = {}
  head.forEach((line, index) => {
    if (!line.trim()) return
    if (/^\s*#/.test(line)) return
    if (/^\s/.test(line)) {
      fail(`${file}:${index + 2} frontmatter 不支持缩进/多行（仅支持单行 key: value）：${line}`)
    }
    const matched = line.match(/^([A-Za-z0-9_-]+):\s?(.*)$/)
    if (!matched) fail(`${file}:${index + 2} 无法解析的 frontmatter 行：${line}`)
    meta[matched[1]] = parseScalar(matched[2])
  })
  return [meta, content.slice(end + 3).trim()]
}

/** 与后端 get_docs() 一致：数字（含数字字符串）→ Number，其余 → Infinity（排最后）。 */
function idNumber(value) {
  if (value === null || value === undefined || value === '') return Infinity
  if (typeof value === 'number') return Number.isFinite(value) ? value : Infinity
  const text = String(value)
  return /^-?\d+(\.\d+)?$/.test(text) ? Number(text) : Infinity
}

function main() {
  if (!existsSync(DOCS_DIR)) fail(`找不到文档目录：${DOCS_DIR}`)
  const files = walkMarkdown(DOCS_DIR)
  if (!files.length) fail(`文档目录中没有 .md 文件：${DOCS_DIR}`)

  const docs = []
  const details = {}

  for (const file of files.sort()) {
    const raw = readFileSync(file, 'utf8')
    const [meta, body] = parseFrontmatter(raw, relative(REPO_ROOT, file))
    const slug = relative(DOCS_DIR, file).split(sep).join('/').replace(/\.md$/, '')

    const base = {
      slug,
      title: meta.title ?? slug,
      author: meta.author ?? '',
      date: meta.date === undefined || meta.date === null ? '' : String(meta.date),
      tags: Array.isArray(meta.tags) ? meta.tags : [],
      summary: meta.summary ?? '',
      id: meta.id ?? null,
    }

    let sidecar = {}
    const sidecarFile = file.replace(/\.md$/, '.json')
    if (existsSync(sidecarFile)) {
      try {
        sidecar = JSON.parse(readFileSync(sidecarFile, 'utf8') || '{}')
      } catch (error) {
        fail(`${relative(REPO_ROOT, sidecarFile)} 不是合法 JSON：${error.message}`)
      }
    }

    docs.push(base)
    details[slug] = { ...base, content: body, sidecar }
  }

  // 复刻后端两趟稳定排序：先 date 降序，再 id 数值升序（Infinity 最后）
  docs.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))
  docs.sort((a, b) => idNumber(a.id) - idNumber(b.id))

  const orderedDetails = {}
  for (const doc of docs) orderedDetails[doc.slug] = details[doc.slug]

  mkdirSync(dirname(OUT_FILE), { recursive: true })
  writeFileSync(
    OUT_FILE,
    JSON.stringify({ generatedAt: new Date().toISOString(), docs, details: orderedDetails }, null, 2) + '\n',
    'utf8',
  )

  console.log(`[build-docs-data] ${docs.length} 篇文档 → ${relative(REPO_ROOT, OUT_FILE)}`)
}

main()
