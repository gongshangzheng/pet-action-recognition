import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue'),
        meta: { title: '首页' },
      },
      // 项目管理
      {
        path: 'management',
        redirect: '/management/team',
      },
      {
        path: 'management/team',
        name: 'TeamList',
        component: () => import('../views/management/TeamList.vue'),
        meta: { title: '团队成员', module: 'management' },
      },
      {
        path: 'management/team/:id',
        name: 'TeamDetail',
        component: () => import('../views/management/TeamDetail.vue'),
        meta: { title: '成员档案', module: 'management' },
      },
      {
        path: 'management/daily',
        name: 'DailyList',
        component: () => import('../views/management/DailyList.vue'),
        meta: { title: '日报', module: 'management' },
      },
      {
        path: 'management/daily/:date/:author',
        name: 'DailyDetail',
        component: () => import('../views/management/DailyDetail.vue'),
        meta: { title: '日报详情', module: 'management' },
      },
      {
        path: 'management/weekly',
        name: 'WeeklyList',
        component: () => import('../views/management/WeeklyList.vue'),
        meta: { title: '周报', module: 'management' },
      },
      {
        path: 'management/weekly/:year/:week/:author',
        name: 'WeeklyDetail',
        component: () => import('../views/management/WeeklyDetail.vue'),
        meta: { title: '周报详情', module: 'management' },
      },
      {
        path: 'management/monthly',
        name: 'MonthlyList',
        component: () => import('../views/management/MonthlyList.vue'),
        meta: { title: '月报', module: 'management' },
      },
      {
        path: 'management/monthly/:year/:month/:author',
        name: 'MonthlyDetail',
        component: () => import('../views/management/MonthlyDetail.vue'),
        meta: { title: '月报详情', module: 'management' },
      },
      {
        path: 'management/tasks',
        name: 'TaskBoard',
        component: () => import('../views/management/TaskBoard.vue'),
        meta: { title: '任务看板', module: 'management' },
      },
      {
        path: 'management/milestones',
        name: 'MilestoneTimeline',
        component: () => import('../views/management/MilestoneTimeline.vue'),
        meta: { title: '里程碑', module: 'management' },
      },
      {
        path: 'management/meetings',
        name: 'MeetingList',
        component: () => import('../views/management/MeetingList.vue'),
        meta: { title: '会议纪要', module: 'management' },
      },
      // 论文搜集
      {
        path: 'papers',
        redirect: '/papers/list',
      },
      {
        path: 'papers/list',
        name: 'PaperList',
        component: () => import('../views/papers/PaperList.vue'),
        meta: { title: '论文列表', module: 'papers' },
      },
      {
        path: 'papers/:id',
        name: 'PaperDetail',
        component: () => import('../views/papers/PaperDetail.vue'),
        meta: { title: '论文详情', module: 'papers' },
      },
      {
        path: 'papers/config',
        name: 'SourceConfig',
        component: () => import('../views/papers/SourceConfig.vue'),
        meta: { title: '数据源配置', module: 'papers' },
      },
      // 评测体系
      {
        path: 'evaluation',
        redirect: '/evaluation/results',
      },
      {
        path: 'evaluation/run',
        name: 'EvalRun',
        component: () => import('../views/evaluation/EvalRun.vue'),
        meta: { title: '评测运行', module: 'evaluation' },
      },
      {
        path: 'evaluation/results',
        name: 'EvalResults',
        component: () => import('../views/evaluation/EvalResults.vue'),
        meta: { title: '评测结果', module: 'evaluation' },
      },
      {
        path: 'evaluation/models',
        name: 'ModelManage',
        component: () => import('../views/evaluation/ModelManage.vue'),
        meta: { title: '模型管理', module: 'evaluation' },
      },
      {
        path: 'evaluation/datasets',
        name: 'DatasetManage',
        component: () => import('../views/evaluation/DatasetManage.vue'),
        meta: { title: '数据集管理', module: 'evaluation' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title
    ? `${to.meta.title} - 宠物动作识别研究平台`
    : '宠物动作识别研究平台'
  next()
})

export default router
