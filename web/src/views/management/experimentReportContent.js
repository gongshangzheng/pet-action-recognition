// 实验报告内容拆分与媒体匹配工具。
//
// 正文是面向读者的文章（背景与目标 → … → 结论与下一步），「附录：配置与完整数据」在网页默认折叠。
// 本模块按 H2 标题把正文拆成 narrative + appendix，供 ExperimentsPage 分别渲染；
// 另提供「案例图是否已在正文中被引用」的判断，避免结构化案例区重复铺满同一张图。
export const REPORT_APPENDIX_HEADING = '附录：配置与完整数据'

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

// 简单判断正文里是否以 ![]() 引用过该 src（完整 markdown 解析依赖重，此处够用）
export function narrativeEmbedsAsset(narrative, src) {
  const target = String(src || '').trim()
  if (!target) return false
  return new RegExp(`!\\[[^\\]]*\\]\\(\\s*${target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\)`).test(String(narrative || ''))
}
