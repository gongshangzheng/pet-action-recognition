<template>
  <n-modal v-model:show="show" preset="dialog" :title="isEdit ? '编辑源' : '添加源'" style="width: 520px" :show-icon="false">
    <n-form :model="form" label-placement="left" label-width="100">
      <n-form-item label="名称">
        <n-input v-model:value="form.name" placeholder="如：客厅摄像头" />
      </n-form-item>
      <n-form-item label="alias">
        <n-input v-model:value="form.alias" placeholder="唯一别名，如 living-room" :disabled="isEdit" />
      </n-form-item>
      <n-form-item label="流地址">
        <n-input v-model:value="form.stream_url" placeholder="rtsp://... 或本地目录路径或 demo" />
      </n-form-item>
      <n-form-item label="存储路径">
        <n-input v-model:value="form.storage_path" placeholder="/home/wyy/.../videos 或本地目录绝对路径" />
      </n-form-item>
      <n-form-item label="启用">
        <n-switch v-model:value="form.is_active" />
      </n-form-item>
    </n-form>
    <template #action>
      <n-space>
        <n-button @click="show = false">取消</n-button>
        <n-button type="primary" :loading="saving" @click="save">{{ isEdit ? '保存' : '添加' }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSwitch, NButton, NSpace, useMessage } from 'naive-ui'
import { createSource, updateSource } from '../../api/live'

const props = defineProps({
  visible: { type: Boolean, default: false },
  source: { type: Object, default: null },  // null=新增, object=编辑
})
const emit = defineEmits(['update:visible', 'saved'])

const show = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const form = ref({ name: '', alias: '', stream_url: '', storage_path: '', is_active: true })
const msg = useMessage()

watch(() => props.visible, (v) => {
  show.value = v
  if (v) {
    if (props.source) {
      isEdit.value = true
      form.value = { ...props.source }
    } else {
      isEdit.value = false
      form.value = { name: '', alias: '', stream_url: '', storage_path: '', is_active: true }
    }
  }
})
watch(show, (v) => emit('update:visible', v))

async function save() {
  if (!form.value.name || !form.value.alias || !form.value.stream_url || !form.value.storage_path) {
    msg.warning('请填全字段')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateSource(form.value.id, {
        name: form.value.name, stream_url: form.value.stream_url,
        storage_path: form.value.storage_path, is_active: form.value.is_active,
      })
    } else {
      await createSource(form.value)
    }
    msg.success(isEdit.value ? '已保存' : '已添加')
    emit('saved')
    show.value = false
  } catch (e) {
    msg.error('保存失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>
