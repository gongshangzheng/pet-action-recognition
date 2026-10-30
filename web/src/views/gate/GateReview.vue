<template>
  <div class="gate-review">
    <header class="gr-head">
      <div class="gr-title">
        <h2>门控核验</h2>
        <span class="gr-hint">教师判定与框已标出；你只需判断 <b>present / absent / uncertain</b>（快捷键 P / A / U，← → 翻页）</span>
      </div>
      <div class="gr-controls">
        <n-select v-model:value="currentSet" :options="setOptions" size="small" style="width: 200px"
                  placeholder="选择 review set" @update:value="reload" />
        <n-select v-model:value="scenario" :options="scenarioOptions" size="small" style="width: 150px"
                  @update:value="reload" />
        <n-switch v-model:value="onlyUnlabeled" size="small" @update:value="reload">
          <template #checked>只看未标</template>
          <template #unchecked>全部</template>
        </n-switch>
        <n-button size="small" @click="prevPage" :disabled="page <= 1">上一页</n-button>
        <span class="gr-page">{{ page }} / {{ maxPage }}</span>
        <n-button size="small" @click="nextPage" :disabled="page >= maxPage">下一页</n-button>
      </div>
    </header>

    <n-progress v-if="stats" type="line" :percentage="progressPercent" :height="10" :show-indicator="false" />
    <div v-if="stats" class="gr-stats">
      共 {{ stats.total }} 帧 ｜ 已标 {{ labeled }}（present {{ stats.counts.present }} / absent
      {{ stats.counts.absent }} / uncertain {{ stats.counts.uncertain }}）
    </div>

    <n-spin :show="loading">
      <div class="gr-grid">
        <figure v-for="(item, index) in items" :key="item.path" class="gr-card"
                :class="{ labeled: item.human_label, selected: index === cursor }"
                @click="cursor = index">
          <div class="gr-frame">
            <img :src="frameUrl(currentSet, item.file)" :alt="item.path" loading="lazy" />
            <!-- 教师框叠加：按原始像素 → 百分比换算 -->
            <svg class="gr-box" viewBox="0 0 100 100" preserveAspectRatio="none">
              <rect v-if="item.box_cat" :x="pct(item.box_cat[0], item.width)" :y="pct(item.box_cat[1], item.height)"
                    :width="pct(item.box_cat[2] - item.box_cat[0], item.width)"
                    :height="pct(item.box_cat[3] - item.box_cat[1], item.height)"
                    class="box-cat" />
              <rect v-if="item.box_dog" :x="pct(item.box_dog[0], item.width)" :y="pct(item.box_dog[1], item.height)"
                    :width="pct(item.box_dog[2] - item.box_dog[0], item.width)"
                    :height="pct(item.box_dog[3] - item.box_dog[1], item.height)"
                    class="box-dog" />
            </svg>
            <div class="gr-badges">
              <span class="badge teacher">{{ item.teacher_label }}</span>
              <span class="badge cat">cat {{ (item.score_cat ?? 0).toFixed(2) }}</span>
              <span v-if="item.score_dog" class="badge dog">dog {{ item.score_dog.toFixed(2) }}</span>
              <span class="badge scenario">{{ item.scenario }} · {{ item.domain }}</span>
            </div>
            <div v-if="item.human_label" class="gr-human">{{ item.human_label }}</div>
          </div>
          <figcaption class="gr-actions">
            <button class="btn present" :class="{ active: item.human_label === 'present' }"
                    @click.stop="label(item, 'present')">有宠物 P</button>
            <button class="btn absent" :class="{ active: item.human_label === 'absent' }"
                    @click.stop="label(item, 'absent')">无宠物 A</button>
            <button class="btn uncertain" :class="{ active: item.human_label === 'uncertain' }"
                    @click.stop="label(item, 'uncertain')">不确定 U</button>
          </figcaption>
        </figure>
      </div>
      <n-empty v-if="!loading && !items.length" description="该筛选下没有帧" />
    </n-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { NButton, NEmpty, NProgress, NSelect, NSpin, NSwitch } from 'naive-ui'
import { frameUrl, getStats, listItems, listSets, setLabel } from '../../api/gateReview'

const sets = ref([])
const currentSet = ref('')
const scenario = ref('')
const onlyUnlabeled = ref(false)
const page = ref(1)
const pageSize = 24
const items = ref([])
const total = ref(0)
const stats = ref(null)
const loading = ref(false)
const cursor = ref(0)

const setOptions = computed(() => sets.value.map((s) => ({
  label: `${s.name}（${s.labeled}/${s.count}）`, value: s.name,
})))
const scenarioOptions = [
  { label: '全部场景', value: '' },
  { label: 'still 静止', value: 'still' },
  { label: 'small 小目标', value: 'small' },
  { label: 'occluded 灰带', value: 'occluded' },
  { label: 'out_of_frame 无检出', value: 'out_of_frame' },
  { label: 'day 白天', value: 'day' },
  { label: 'night 夜视', value: 'night' },
]
const maxPage = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const labeled = computed(() => {
  if (!stats.value) return 0
  const c = stats.value.counts
  return c.present + c.absent + c.uncertain
})
const progressPercent = computed(() => (stats.value ? Math.round((labeled.value / Math.max(1, stats.value.total)) * 100) : 0))

const pct = (value, dimension) => `${(value / dimension) * 100}`

async function loadSets() {
  sets.value = await listSets()
  if (!currentSet.value && sets.value.length) currentSet.value = sets.value[0].name
}

async function reload() {
  if (!currentSet.value) return
  loading.value = true
  try {
    const data = await listItems(currentSet.value, {
      scenario: scenario.value || undefined,
      only_unlabeled: onlyUnlabeled.value,
      page: page.value,
      page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total
    cursor.value = 0
    stats.value = await getStats(currentSet.value)
  } finally {
    loading.value = false
  }
}

async function label(item, value) {
  const result = await setLabel(currentSet.value, { path: item.path, human_label: value })
  item.human_label = value
  if (stats.value) {
    stats.value.counts.unlabeled = Math.max(0, stats.value.counts.unlabeled - 1)
    stats.value.counts[value] = (stats.value.counts[value] || 0) + 1
  }
  if (result?.labeled !== undefined) labeled.value = result.labeled
  // 自动前进到下一张
  if (cursor.value < items.value.length - 1) cursor.value += 1
}

function nextPage() {
  if (page.value < maxPage.value) {
    page.value += 1
    reload()
  }
}

function prevPage() {
  if (page.value > 1) {
    page.value -= 1
    reload()
  }
}

function onKey(event) {
  const key = event.key.toLowerCase()
  const item = items.value[cursor.value]
  if (!item) return
  if (key === 'p') label(item, 'present')
  else if (key === 'a') label(item, 'absent')
  else if (key === 'u') label(item, 'uncertain')
  else if (key === 'arrowright' && cursor.value < items.value.length - 1) cursor.value += 1
  else if (key === 'arrowleft' && cursor.value > 0) cursor.value -= 1
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  await loadSets()
  await reload()
})

onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped lang="scss">
.gate-review {
  padding: 20px 24px;
}

.gr-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  h2 {
    margin: 0 0 4px;
    font-size: 18px;
  }
}

.gr-hint {
  font-size: 12px;
  color: var(--color-text-dim);
}

.gr-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.gr-page {
  font-size: 12px;
  color: var(--color-text-dim);
  min-width: 56px;
  text-align: center;
}

.gr-stats {
  margin: 6px 0 16px;
  font-size: 12px;
  color: var(--color-text-dim);
}

.gr-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.gr-card {
  margin: 0;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-card);

  &.selected {
    outline: 2px solid var(--color-primary);
  }

  &.labeled {
    border-color: var(--color-primary);
  }
}

.gr-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #111;

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }
}

.gr-box {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;

  .box-cat {
    fill: rgba(24, 160, 88, 0.18);
    stroke: #18a058;
    stroke-width: 0.6;
    vector-effect: non-scaling-stroke;
  }

  .box-dog {
    fill: rgba(208, 48, 80, 0.16);
    stroke: #d03050;
    stroke-width: 0.6;
    vector-effect: non-scaling-stroke;
  }
}

.gr-badges {
  position: absolute;
  top: 4px;
  left: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;

  .badge {
    font-size: 10px;
    line-height: 1.5;
    padding: 0 5px;
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.62);
    color: #fff;

    &.teacher {
      background: rgba(0, 0, 0, 0.8);
    }

    &.cat {
      background: rgba(24, 160, 88, 0.85);
    }

    &.dog {
      background: rgba(208, 48, 80, 0.85);
    }

    &.scenario {
      background: rgba(50, 50, 50, 0.75);
    }
  }
}

.gr-human {
  position: absolute;
  right: 4px;
  bottom: 4px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--color-primary);
  color: #fff;
}

.gr-actions {
  display: flex;
  gap: 6px;
  padding: 8px;

  .btn {
    flex: 1;
    font-size: 12px;
    padding: 5px 0;
    border-radius: 5px;
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text);
    cursor: pointer;

    &.present.active {
      background: #18a058;
      border-color: #18a058;
      color: #fff;
    }

    &.absent.active {
      background: #d03050;
      border-color: #d03050;
      color: #fff;
    }

    &.uncertain.active {
      background: #f0a020;
      border-color: #f0a020;
      color: #fff;
    }
  }
}
</style>
