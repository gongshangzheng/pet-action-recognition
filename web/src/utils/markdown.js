export function slugify(text) {
  return text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\u4e00-\u9fff-]/g, '')
}

export function extractToc(body) {
  if (!body) return []
  const lines = body.split('\n')
  const items = []
  let inCodeBlock = false

  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock
      continue
    }
    if (inCodeBlock) continue

    const match = /^(#{2,3})\s+(.+)$/.exec(line)
    if (match) {
      items.push({
        level: match[1].length,
        text: match[2].trim(),
        slug: slugify(match[2].trim()),
      })
    }
  }
  return items
}
