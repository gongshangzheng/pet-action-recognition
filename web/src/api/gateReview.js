import request from './request'

// 门控人工核验（review set 由 scripts/prepare_gate_review_set.py 生成）
export const listSets = () => request.get('/gate-review/sets')
export const listItems = (set, params) => request.get(`/gate-review/sets/${set}/items`, { params })
export const getStats = (set) => request.get(`/gate-review/sets/${set}/stats`)
export const setLabel = (set, payload) => request.post(`/gate-review/sets/${set}/label`, payload)

// 帧图片直连 URL（不走 axios，交给 <img> 加载）
export const frameUrl = (set, path) =>
  `/api/gate-review/sets/${encodeURIComponent(set)}/frame?path=${encodeURIComponent(path)}`
