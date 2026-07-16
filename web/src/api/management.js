import request from './request'

// 团队
export const getTeamList = () => request.get('/management/team')
export const getTeamMember = (id) => request.get(`/management/team/${id}`)

// 日报
export const getDailyList = (params) => request.get('/management/daily', { params })
export const getDailyDetail = (date, author) => request.get(`/management/daily/${date}/${author}`)

// 周报
export const getWeeklyList = (params) => request.get('/management/weekly', { params })
export const getWeeklyDetail = (year, week, author) => request.get(`/management/weekly/${year}/${week}/${author}`)

// 月报
export const getMonthlyList = (params) => request.get('/management/monthly', { params })
export const getMonthlyDetail = (year, month, author) => request.get(`/management/monthly/${year}/${month}/${author}`)

// 任务（看板：从 per-project tasks.json 派生，按项目切换）
export const getTasks = (slug) => request.get('/management/tasks', { params: { slug } })

// 里程碑
export const getMilestones = () => request.get('/management/milestones')

// 会议纪要
export const getMeetings = () => request.get('/management/meetings')
export const getMeetingDetail = (date) => request.get(`/management/meetings/${date}`)

// 项目树
export const getProjects = () => request.get('/management/projects')
export const getProjectDetail = (slug) => request.get(`/management/projects/${slug}`)
export const getProjectTasks = (slug) => request.get(`/management/projects/${slug}/tasks`)
export const getTaskNote = (slug, notePath) => request.get(`/management/projects/${slug}/notes/${notePath}`)
