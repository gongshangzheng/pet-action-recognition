<template>
  <div class="page-container">
    <n-card title="数据源配置" size="small">
      <template #header-extra>
        <n-button type="primary" size="small" @click="showAdd = true">添加数据源</n-button>
      </template>
      <n-spin :show="loading">
        <n-table v-if="sources.length" :bordered="false" :single-line="false" size="small" striped>
          <thead>
            <tr><th>名称</th><th>类型</th><th>API 地址</th><th>状态</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in sources" :key="s.id">
              <td>{{ s.name }}</td>
              <td>{{ s.type }}</td>
              <td>{{ s.api_url || '-' }}</td>
              <td><n-tag :type="s.enabled ? 'success' : 'default'" size="small">{{ s.enabled ? '已启用' : '已禁用' }}</n-tag></td>
              <td>
                <n-switch v-model:value="s.enabled" size="small" @update:value="toggleSource(s)" />
              </td>
            </tr>
          </tbody>
        </n-table>
        <EmptyState v-else description="暂无数据源配置，可点击右上角添加" />
      </n-spin>
    </n-card>

    <n-modal v-model:show="showAdd" preset="card" title="添加数据源" style="width: 500px">
      <n-form label-placement="left" :label-width="80">
        <n-form-item label="名称"><n-input v-model:value="newSource.name" /></n-form-item>
        <n-form-item label="类型"><n-input v-model:value="newSource.type" /></n-form-item>
        <n-form-item label="API 地址"><n-input v-model:value="newSource.api_url" /></n-form-item>
        <n-form-item label="启用"><n-switch v-model:value="newSource.enabled" /></n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAdd = false">取消</n-button>
          <n-button type="primary" @click="showAdd = false">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NTable, NTag, NButton, NSwitch, NModal, NForm, NFormItem, NInput, NSpace, useMessage } from 'naive-ui'
import EmptyState from '../../components/common/EmptyState.vue'
import { getPaperSources, updatePaperSource } from '../../api/papers'

const message = useMessage()
const loading = ref(false)
const sources = ref([])
const showAdd = ref(false)
const newSource = ref({ name: '', type: '', api_url: '', enabled: true })

async function toggleSource(s) {
  try {
    await updatePaperSource(s.id, { enabled: s.enabled })
    message.success(`${s.name} 已${s.enabled ? '启用' : '禁用'}`)
  } catch { message.error('操作失败') }
}

onMounted(async () => {
  loading.value = true
  try { sources.value = await getPaperSources() } catch { sources.value = [] }
  loading.value = false
})
</script>
