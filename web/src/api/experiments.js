import request from './request'

// 实验报告（management/experiments/，只读；生成走 experiment skill 脚本）
export const getExperiments = () => request.get('/management/experiments')
export const getExperimentDetail = (topic, slug) =>
  request.get(`/management/experiments/${topic}/${slug}`)
// 案例图按报告粒度服务（防穿越 + 白名单在后端）
export const getExperimentAssetUrl = (topic, slug, filename) =>
  `/api/management/experiments/${topic}/${slug}/assets/${encodeURIComponent(filename)}`
