// 实验报告内容拆分与媒体匹配工具。
//
// 正文是面向读者的文章（背景与目标 → … → 结论与下一步），「附录：配置与完整数据」在网页默认折叠。
// 本模块按 H2 标题把正文拆成 narrative + appendix，供 ExperimentsPage 分别渲染；
// 另提供「案例图是否已在正文中被引用」的判断，避免结构化案例区重复铺满同一张图。
export const REPORT_APPENDIX_HEADING = '附录：配置与完整数据'

// 正文媒体引用：`![说明](assets/<文件名>)`（图片）与 `![说明](media/<文件名>)`（视频）。
// 引用在**渲染期**映射到该报告的只读 API 路由（/api/management/experiments/<topic>/<slug>/…），
// 因此作者写清单登记的可读名（`<case-id>.<ext>`）、sha256 名或手工放进 assets/ 的可读名都能用，
// 不需要重新生成报告。只接受单段文件名 + 扩展名白名单，其余写法原样退回 <img>，不内联 HTML。
export const REPORT_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
export const REPORT_VIDEO_EXTS = ['.mp4', '.webm', '.mov']

const SINGLE_SEGMENT_RE = /^[^/\\\x00-\x1f\x7f?#%]+$/u
const REPORT_MEDIA_REF_RE = /^(?:\.\/)?(assets|media)\/(.+)$/u

function splitFileName(name) {
  const dot = name.lastIndexOf('.')
  if (dot <= 0) return null
  return { stem: name.slice(0, dot), ext: name.slice(dot).toLowerCase() }
}

// manifest.cases → 引用别名：`assets/<case-id>.<ext>` → `assets/<sha256>.<ext>`。
// 视频侧后端只放行清单登记的 sha256 文件名，别名让作者仍能写可读名。
export function buildReportFileAliases(cases) {
  const out = {}
  for (const c of Array.isArray(cases) ? cases : []) {
    const id = String(c?.id || '').trim()
    const src = String(c?.src || '').trim()
    if (!id || !src || !SINGLE_SEGMENT_RE.test(id)) continue
    const dir = src.startsWith('assets/') ? 'assets' : src.startsWith('media/') ? 'media' : ''
    if (!dir) continue
    const file = src.slice(dir.length + 1)
    if (!SINGLE_SEGMENT_RE.test(file)) continue
    const info = splitFileName(file)
    if (!info) continue
    out[`${dir}/${id}${info.ext}`] = `${dir}/${file}`
  }
  return out
}

// 解析正文媒体引用；不可解析（非 assets/media 前缀、扩展名不在白名单、非法文件名）→ null，调用方按普通图片处理。
// media：{ assetUrl(file), mediaUrl(file), fileAliases }，由页面按当前报告构造。
export function resolveReportMediaRef(src, media) {
  const raw = String(src ?? '').trim()
  if (!raw || !media) return null
  const m = REPORT_MEDIA_REF_RE.exec(raw)
  if (!m) return null
  const dir = m[1]
  const file = m[2]
  if (!SINGLE_SEGMENT_RE.test(file)) return null
  const aliased = media.fileAliases?.[`${dir}/${file}`]
  const target = typeof aliased === 'string' && aliased.startsWith(`${dir}/`)
    ? aliased.slice(dir.length + 1)
    : file
  const info = splitFileName(target)
  if (!info || !SINGLE_SEGMENT_RE.test(target)) return null
  if (dir === 'assets') {
    if (!REPORT_IMAGE_EXTS.includes(info.ext) || typeof media.assetUrl !== 'function') return null
    return { kind: 'image', url: media.assetUrl(target) }
  }
  if (!REPORT_VIDEO_EXTS.includes(info.ext) || typeof media.mediaUrl !== 'function') return null
  return { kind: 'video', url: media.mediaUrl(target) }
}

export function splitReportAppendix(markdown) {
  const normalized = String(markdown || '').replace(/\r\n?/g, '\n')
  const lines = normalized.split('\n')
  let fence = null // { marker, length }
  let appendixLine = -1

  const openingFence = line => {
    const m = line.match(/^ {0,3}(`{3,}|~{3,}).*$/)
    return m ? { marker: m[1][0], length: m[1].length } : null
  }
  const closesFence = (line, f) => {
    const m = line.match(/^ {0,3}(`{3,}|~{3,})[ \t]*$/)
    return !!m && m[1][0] === f.marker && m[1].length >= f.length
  }

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    if (fence) {
      if (closesFence(line, fence)) fence = null
      continue
    }
    const next = openingFence(line)
    if (next) { fence = next; continue }
    const h = line.match(/^##[ \t]+(.+?)[ \t]*$/)
    if (h && h[1].trim() === REPORT_APPENDIX_HEADING) appendixLine = i
  }

  if (appendixLine < 0) {
    return { narrative: normalized.trim(), appendix: '', hasAppendix: false }
  }
  return {
    narrative: lines.slice(0, appendixLine).join('\n').trim(),
    appendix: lines.slice(appendixLine + 1).join('\n').trim(),
    hasAppendix: true,
  }
}

// 简单判断正文里是否以 ![]() 引用过该 src（完整 markdown 解析依赖重，此处够用）。
// aliases（buildReportFileAliases 的结果）让「正文写可读名、清单记 sha256 名」也能算已引用，避免案例区重复铺满。
export function narrativeEmbedsAsset(narrative, src, aliases) {
  const target = String(src || '').trim()
  if (!target) return false
  const candidates = new Set([target])
  for (const [ref, value] of Object.entries(aliases || {})) {
    if (value === target) candidates.add(ref)
  }
  const text = String(narrative || '')
  const escape = (p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return [...candidates].some((candidate) =>
    new RegExp(`!\\[[^\\]]*\\]\\(\\s*${escape(candidate)}\\s*\\)`).test(text))
}
