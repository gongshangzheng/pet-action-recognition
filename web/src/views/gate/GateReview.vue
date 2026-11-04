<template>
  <div class="gate-review" :class="{ 'video-mode': isSingleView }">
    <header class="gr-head">
      <div class="gr-title">
        <h2>{{ selectedSet?.title || '门控核验' }}</h2>
        <span v-if="isCropComparison" class="gr-hint">三路视频均可独立播放，请分别打开并拖动到同一时刻比较。快捷键 P / F / U；空格播放/暂停原始视频，← → 翻页。</span>
        <span v-else-if="isVideo" class="gr-hint">两秒内任意时刻出现宠物即选有宠物，整个片段没有宠物才选无宠物；快捷键 F / A / U，空格播放/暂停，← → 翻页。</span>
        <span v-else-if="hideTeacher" class="gr-hint">只判断有没有宠物：有宠物 P / 无宠物 A；看不清可跳过待复核 U。← → 切换图片。</span>
        <span v-else class="gr-hint">模型预标仅供参考，请确认有无宠物；看不清可跳过。（快捷键 P / A / U，← → 切换图片）</span>
      </div>
      <div class="gr-controls">
        <n-select v-model:value="currentSet" :options="setOptions" size="small" style="width: 200px"
                  placeholder="选择标注批次" @update:value="changeFilter" />
        <n-select v-if="!isCropComparison" v-model:value="scenario" :options="scenarioOptions" size="small" style="width: 150px"
                  @update:value="changeFilter" />
        <n-switch v-model:value="onlyUnlabeled" size="small" @update:value="changeFilter">
          <template #checked>只看未标</template>
          <template #unchecked>全部</template>
        </n-switch>
        <template v-if="!isSingleView">
          <n-button size="small" @click="prevPage" :disabled="page <= 1">上一页</n-button>
          <span class="gr-page">{{ page }} / {{ maxPage }}</span>
          <n-button size="small" @click="nextPage" :disabled="page >= maxPage">下一页</n-button>
        </template>
      </div>
    </header>

    <n-progress v-if="stats" type="line" :percentage="progressPercent" :height="10" :show-indicator="false" />
    <div v-if="stats" class="gr-stats">
      <template v-if="isCropComparison">
        共 {{ stats.total }} 段 ｜ 已审核 {{ labeled }}（合格 {{ stats.counts.pass }} / 不合格
        {{ stats.counts.fail }} / 待复查 {{ stats.counts.uncertain }}）
      </template>
      <template v-else>
        共 {{ stats.total }} 帧 ｜ 已标 {{ labeled }}（present {{ stats.counts.present }} / absent
        {{ stats.counts.absent }} / uncertain {{ stats.counts.uncertain }}）
      </template>
    </div>

    <n-spin :show="loading">
      <div class="gr-grid">
        <figure v-for="(item, index) in items" :key="item.path" class="gr-card"
                :class="{ labeled: item.human_label, selected: index === cursor }"
                @click="cursor = index">
          <div class="gr-frame">
            <div v-if="isCropComparison" class="crop-compare">
              <figure v-for="arm in CROP_ARMS" :key="arm.key" class="crop-pane">
                <figcaption>
                  <strong>{{ arm.label }}</strong>
                  <span>{{ arm.note }}</span>
                </figcaption>
                <video
                  :ref="(element) => setCropVideo(arm.key, element)"
                  :src="videoUrl(currentSet, item.files?.[arm.key])"
                  controls
                  muted
                  playsinline
                  preload="auto"
                  @loadedmetadata="primeCropVideo"
                />
              </figure>
              <div class="crop-meta">
                <span>{{ item.review_id }} · {{ item.class_name }}</span>
                <span>{{ item.start_frame }}–{{ item.end_frame }}（{{ item.frame_count }} 帧）</span>
                <span>{{ item.video }}</span>
                <n-tag size="tiny" :bordered="false" :type="item.strict_available ? 'success' : 'warning'">
                  {{ item.strict_available ? '严格规则可用' : (item.unavailable_reason || '规则排除') }}
                </n-tag>
              </div>
            </div>
            <video v-else-if="isVideo" ref="videoRef" :src="videoUrl(currentSet, item.file)" controls preload="metadata" />
            <img v-else :src="frameUrl(currentSet, item.file)" :alt="item.path" loading="lazy" />
            <!-- 教师框叠加：按原始像素 → 百分比换算 -->
            <svg v-if="!hideTeacher" class="gr-box" viewBox="0 0 100 100" preserveAspectRatio="none">
              <rect v-if="item.box_cat" :x="pct(item.box_cat[0], item.width)" :y="pct(item.box_cat[1], item.height)"
                    :width="pct(item.box_cat[2] - item.box_cat[0], item.width)"
                    :height="pct(item.box_cat[3] - item.box_cat[1], item.height)"
                    class="box-cat" />
              <rect v-if="item.box_dog" :x="pct(item.box_dog[0], item.width)" :y="pct(item.box_dog[1], item.height)"
                    :width="pct(item.box_dog[2] - item.box_dog[0], item.width)"
                    :height="pct(item.box_dog[3] - item.box_dog[1], item.height)"
                    class="box-dog" />
            </svg>
            <div v-if="!hideTeacher" class="gr-badges">
              <span class="badge teacher">{{ teacherText(item.teacher_label) }}</span>
              <span class="badge cat">cat {{ (item.score_cat ?? 0).toFixed(2) }}</span>
              <span v-if="item.score_dog" class="badge dog">dog {{ item.score_dog.toFixed(2) }}</span>
              <span class="badge scenario">{{ item.scenario }} · {{ item.domain }}</span>
            </div>
            <div v-if="item.human_label" class="gr-human">{{ item.human_label }}</div>
          </div>
          <figcaption class="gr-actions">
            <template v-if="isCropComparison">
              <button class="btn present" :class="{ active: item.human_label === 'pass' }"
                      @click.stop="label(item, 'pass')">裁剪合格 P</button>
              <button class="btn absent" :class="{ active: item.human_label === 'fail' }"
                      @click.stop="label(item, 'fail')">裁剪不合格 F</button>
            </template>
            <template v-else>
              <button class="btn present" :class="{ active: item.human_label === 'present' }"
                      @click.stop="label(item, 'present')">有宠物 {{ isVideo ? 'F' : 'P' }}</button>
              <button class="btn absent" :class="{ active: item.human_label === 'absent' }"
                      @click.stop="label(item, 'absent')">无宠物 A</button>
            </template>
            <button class="btn uncertain" :class="{ active: item.human_label === 'uncertain' }"
                    @click.stop="label(item, 'uncertain')">{{ hideTeacher ? '跳过待复核 U' : '不确定 U' }}</button>
          </figcaption>
          <div v-if="isSingleView" class="gr-video-pager">
            <div class="gr-jump">
              <n-input-number v-model:value="jumpPageValue" :min="1" :max="maxPage" size="small"
                              placeholder="页码" @keydown.enter="jumpToPage" />
              <n-button size="small" @click="jumpToPage">跳转</n-button>
            </div>
            <n-button size="small" @click="prevPage" :disabled="page <= 1">上一页 ←</n-button>
            <span class="gr-page">{{ page }} / {{ maxPage }}</span>
            <n-button size="small" type="primary" @click="nextPage" :disabled="page >= maxPage">下一页 →</n-button>
          </div>
          <div v-if="isCropComparison" class="gr-flags" :class="{ disabled: !item.human_label }">
            <span class="gr-flags-label">问题：</span>
            <button v-for="flag in CROP_FLAGS" :key="flag.key" class="chip"
                    :class="{ on: hasFlag(item, flag.key) }" :disabled="!item.human_label"
                    @click.stop="toggleFlag(item, flag.key)">{{ flag.label }}</button>
          </div>
          <div v-else-if="!hideTeacher" class="gr-flags" :class="{ disabled: !item.human_label }">
            <span class="gr-flags-label">框问题：</span>
            <button v-for="flag in BOX_FLAGS" :key="flag.key" class="chip"
                    :class="{ on: hasFlag(item, flag.key) }" :disabled="!item.human_label"
                    @click.stop="toggleFlag(item, flag.key)">{{ flag.label }}</button>
          </div>
        </figure>
      </div>
      <n-empty v-if="!loading && !items.length" description="该筛选下没有帧" />
    </n-spin>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { NButton, NEmpty, NInputNumber, NProgress, NSelect, NSpin, NSwitch, NTag, useMessage } from 'naive-ui'
import { frameUrl, videoUrl, getStats, listItems, listSets, setLabel } from '../../api/gateReview'

const message = useMessage()
const sets = ref([])
const currentSet = ref('')
const scenario = ref('')
const onlyUnlabeled = ref(false)
const page = ref(1)
const jumpPageValue = ref(1)
const items = ref([])
const total = ref(0)
const stats = ref(null)
const loading = ref(false)
const cursor = ref(0)
const saving = ref(false)
const videoRef = ref(null)
let loadVersion = 0
const selectedSet = computed(() => sets.value.find((s) => s.name === currentSet.value))
const hideTeacher = computed(() => Boolean(selectedSet.value?.hide_teacher))
const isVideo = computed(() => selectedSet.value?.mode === 'video')
const isCropComparison = computed(() => selectedSet.value?.mode === 'crop_comparison')
const isSingleView = computed(() => isVideo.value || isCropComparison.value)
const pageSize = computed(() => (isSingleView.value ? 1 : 24))

const setOptions = computed(() => sets.value.map((s) => {
  const live = stats.value && s.name === currentSet.value ? labeled.value : s.labeled
  return { label: `${s.title || s.name}（${live}/${s.count}）`, value: s.name }
}))
const scenarioOptions = [
  { label: '全部场景', value: '' },
  { label: 'still 静止', value: 'still' },
  { label: 'small 小目标', value: 'small' },
  { label: 'occluded 灰带', value: 'occluded' },
  { label: 'out_of_frame 无检出', value: 'out_of_frame' },
  { label: 'day 白天', value: 'day' },
  { label: 'night 夜视', value: 'night' },
]
const maxPage = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const labeled = ref(0)
function syncLabeled() {
  if (!stats.value) { labeled.value = 0; return }
  const c = stats.value.counts
  labeled.value = isCropComparison.value
    ? (c.pass || 0) + (c.fail || 0) + (c.uncertain || 0)
    : (c.present || 0) + (c.absent || 0) + (c.uncertain || 0)
}
const progressPercent = computed(() => (stats.value ? Math.round((labeled.value / Math.max(1, stats.value.total)) * 100) : 0))

const pct = (value, dimension) => `${(value / dimension) * 100}`
const teacherText = (label) => ({ cat_present: '预标：有猫', other_animal_only: '预标：有狗', absent: '预标：未检出' }[label] || label)

async function loadSets() {
  sets.value = await listSets()
  const params = new URLSearchParams(window.location.search)
  const requestedSet = params.get('set')
  if (requestedSet && sets.value.some((s) => s.name === requestedSet)) currentSet.value = requestedSet
  if (!currentSet.value && sets.value.length) currentSet.value = sets.value[0].name
  const requestedScenario = params.get('scenario')
  if (scenarioOptions.some((option) => option.value === requestedScenario)) scenario.value = requestedScenario
  onlyUnlabeled.value = params.get('unlabeled') === '1'
  page.value = Math.max(1, Number(params.get('page')) || 1)
  jumpPageValue.value = page.value
  const current = sets.value.find((s) => s.name === currentSet.value)
  if (current && !stats.value) labeled.value = current.labeled
}

function changeFilter() {
  page.value = 1
  jumpPageValue.value = 1
  syncUrlState()
  reload()
}

function syncUrlState() {
  const params = new URLSearchParams()
  if (currentSet.value) params.set('set', currentSet.value)
  if (page.value > 1) params.set('page', String(page.value))
  if (scenario.value) params.set('scenario', scenario.value)
  if (onlyUnlabeled.value) params.set('unlabeled', '1')
  const query = params.toString()
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
}

async function reload() {
  if (!currentSet.value) return
  const batch = currentSet.value
  const version = ++loadVersion
  loading.value = true
  try {
    const data = await listItems(batch, {
      scenario: scenario.value || undefined,
      only_unlabeled: onlyUnlabeled.value,
      page: page.value,
      page_size: pageSize.value,
    })
    if (version !== loadVersion) return
    items.value = data.items.map((item) => ({ note: '', ...item }))
    total.value = data.total
    const loadedMaxPage = Math.max(1, Math.ceil(data.total / pageSize.value))
    if (page.value > loadedMaxPage) {
      page.value = loadedMaxPage
      jumpPageValue.value = loadedMaxPage
      syncUrlState()
      reload()
      return
    }
    syncUrlState()
    cursor.value = 0
    await nextTick()
    resetCropVideos()
    const updatedStats = await getStats(batch)
    if (version !== loadVersion) return
    stats.value = updatedStats
    syncLabeled()
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function label(item, value, note = item.note || '') {
  if (saving.value) return
  saving.value = true
  const batch = currentSet.value
  const version = loadVersion
  const previous = item.human_label
  try {
    await setLabel(batch, { path: item.path, human_label: value, note })
    if (batch !== currentSet.value) return
    item.human_label = value
    item.note = note
    // 以服务端统计为准（避免本地计数漂移），并把当前 set 的计数同步到下拉标签
    const updatedStats = await getStats(batch)
    if (batch !== currentSet.value) return
    stats.value = updatedStats
    syncLabeled()
    if (version === loadVersion && previous !== value && cursor.value < items.value.length - 1) cursor.value += 1
  } catch (error) {
    console.error('[gate-review] 标注保存失败', error)
    message.error(`保存失败：${error?.response?.data?.detail || error?.message || '未知错误'}（该帧可能已不在当前 review set 中，请刷新页面）`)
  } finally {
    saving.value = false
  }
}

const BOX_FLAGS = [
  { key: 'cat_wrong', label: 'cat 框错' },
  { key: 'dog_wrong', label: 'dog 框错' },
  { key: 'tight', label: '框偏小' },
  { key: 'loose', label: '框偏大' },
]

const CROP_ARMS = [
  { key: 'raw', label: '原始视频', note: '完整画面，等比缩放后居中' },
  { key: 'gdino', label: 'GroundingDINO 裁剪', note: '只使用检测跟踪框' },
  { key: 'gdino_motion', label: '像素运动辅助裁剪', note: '检测框加像素前景扩展' },
]

const CROP_FLAGS = [
  { key: 'body_cut', label: '身体切断' },
  { key: 'wrong_target', label: '裁错目标' },
  { key: 'target_jump', label: '跳猫/漂移' },
  { key: 'jitter', label: '裁剪抖动' },
  { key: 'gray_frames', label: '灰帧/无效帧' },
  { key: 'text_watermark', label: '水印/文字污染' },
  { key: 'multi_cat', label: '多猫歧义' },
  { key: 'dog_present', label: '有狗歧义' },
  { key: 'no_cat_detection', label: '未可靠检出猫' },
  { key: 'other', label: '其他' },
]

const cropVideos = new Map()
function setCropVideo(arm, element) {
  if (element) cropVideos.set(arm, element)
  else cropVideos.delete(arm)
}
function resetCropVideos() {
  for (const video of cropVideos.values()) {
    video.pause()
    video.currentTime = 0
  }
}
function primeCropVideo(event) {
  const video = event.currentTarget
  if (Number.isFinite(video.duration) && video.duration > 0) {
    video.currentTime = Math.min(0.04, video.duration / 2)
  }
}

const noteFlags = (note) => (note || '').split(';').map((v) => v.trim()).filter(Boolean)
const hasFlag = (item, key) => noteFlags(item.note).includes(key)

async function toggleFlag(item, key) {
  if (!item.human_label) return
  const flags = new Set(noteFlags(item.note))
  flags.has(key) ? flags.delete(key) : flags.add(key)
  await label(item, item.human_label, [...flags].sort().join(';'))
}

function nextPage() {
  if (page.value < maxPage.value) goToPage(page.value + 1)
}

function prevPage() {
  if (page.value > 1) goToPage(page.value - 1)
}

function goToPage(target) {
  const nextPageValue = Math.min(maxPage.value, Math.max(1, Number(target) || 1))
  jumpPageValue.value = nextPageValue
  if (nextPageValue === page.value) return
  page.value = nextPageValue
  syncUrlState()
  reload()
}

function jumpToPage() {
  goToPage(jumpPageValue.value)
}

function onKey(event) {
  if (event.target instanceof HTMLElement && (event.target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName))) return
  if (event.repeat || saving.value) return
  const key = event.key.toLowerCase()
  const item = items.value[cursor.value]
  if (!item) return
  if (isCropComparison.value) {
    if (key === 'p') label(item, 'pass')
    else if (key === 'f') label(item, 'fail')
    else if (key === 'u') label(item, 'uncertain')
    else if (key === ' ') {
      event.preventDefault()
      const raw = cropVideos.get('raw')
      if (!raw) return
      if (raw.paused || raw.ended) raw.play().catch(console.error)
      else raw.pause()
    } else if (key === 'arrowright') nextPage()
    else if (key === 'arrowleft') prevPage()
    return
  }
  if (key === (isVideo.value ? 'f' : 'p')) label(item, 'present')
  else if (key === 'a') label(item, 'absent')
  else if (key === 'u') label(item, 'uncertain')
  else if (key === ' ' && isVideo.value) {
    event.preventDefault()
    const video = Array.isArray(videoRef.value) ? videoRef.value[0] : videoRef.value
    if (!video) return
    if (video.paused || video.ended) video.play().catch(console.error)
    else video.pause()
  }
  else if (key === 'arrowright') isVideo.value ? nextPage() : cursor.value = Math.min(cursor.value + 1, items.value.length - 1)
  else if (key === 'arrowleft') isVideo.value ? prevPage() : cursor.value = Math.max(cursor.value - 1, 0)
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

  &.video-mode {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 12px 24px 20px;
    overflow: hidden;
  }
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

  .video-mode & {
    margin: 4px 0 8px;
  }
}

.video-mode {
  :deep(.n-spin-container),
  :deep(.n-spin-content) {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
  }
}

.gr-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;

  .video-mode & {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr;
    min-height: 0;
  }
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

  .video-mode & {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
}

.gr-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #111;

  .video-mode & {
    flex: 1;
    min-height: 0;
    aspect-ratio: auto;
    background: #000;
  }

  img, video {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }
}

.crop-compare {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  height: 100%;
  padding: 10px;
  background: #111;
  box-sizing: border-box;
}

.crop-pane {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  margin: 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  overflow: hidden;
  background: #000;

  figcaption {
    display: flex;
    flex-shrink: 0;
    justify-content: space-between;
    gap: 8px;
    padding: 7px 9px;
    color: rgba(255, 255, 255, 0.88);
    background: #1b1b1b;
    font-size: 12px;

    span {
      color: rgba(255, 255, 255, 0.52);
      font-size: 11px;
    }
  }

  video {
    flex: 1;
    min-height: 0;
    aspect-ratio: 1;
    object-fit: contain;
  }
}

.crop-meta {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  align-items: center;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;

  span:last-of-type {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

.gr-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
  padding: 0 8px 8px;
  font-size: 11px;
  color: var(--color-text-dim);

  &.disabled {
    opacity: 0.45;
  }

  .gr-flags-label {
    margin-right: 2px;
  }

  .chip {
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 10px;
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text-dim);
    cursor: pointer;

    &.on {
      background: #f0a020;
      border-color: #f0a020;
      color: #fff;
    }

    &:disabled {
      cursor: not-allowed;
    }
  }
}

.gr-actions {
  display: flex;
  gap: 6px;
  padding: 8px;

  .video-mode & {
    flex-shrink: 0;
    padding: 8px 0 0;
  }

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

.gr-video-pager {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
  padding: 8px 0 0;
}

@media (max-width: 720px) {
  .crop-compare {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .crop-pane video {
    min-height: 220px;
  }
}

.gr-jump {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-right: auto;

  :deep(.n-input-number) {
    width: 92px;
  }
}
</style>
