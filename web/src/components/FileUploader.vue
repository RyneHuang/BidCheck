<template>
  <div class="file-uploader">
    <el-upload
      v-model:file-list="fileList"
      :auto-upload="false"
      :accept="accept"
      :limit="10"
      multiple
      drag
      @change="handleChange"
    >
      <div class="upload-area">
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div>拖拽文件到此处，或 <em>点击上传</em></div>
        <div class="upload-hint">
          {{ accept }} 文件，单个最大 {{ maxSize }}MB
        </div>
      </div>
    </el-upload>

    <div v-if="fileList.length" class="file-list">
      <div v-for="file in fileList" :key="file.uid" class="file-item">
        <div class="file-info">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
        </div>
        <el-button type="danger" text size="small" @click="removeFile(file)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { UploadFilled, Document, Close } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  accept: { type: String, default: '.docx,.xlsx,.pdf' },
  maxSize: { type: Number, default: 50 }
})

const emit = defineEmits(['update:modelValue'])

const fileList = ref([])

watch(() => props.modelValue, (val) => {
  if (val.length === 0) {
    fileList.value = []
  }
}, { deep: true })

const handleChange = (uploadFile, uploadFiles) => {
  const validFiles = uploadFiles.filter(f => {
    const sizeMB = f.size / 1024 / 1024
    return sizeMB <= props.maxSize
  })
  fileList.value = validFiles
  emit('update:modelValue', validFiles.map(f => f.raw))
}

const removeFile = (file) => {
  const index = fileList.value.findIndex(f => f.uid === file.uid)
  if (index > -1) {
    fileList.value.splice(index, 1)
    emit('update:modelValue', fileList.value.map(f => f.raw))
  }
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
}

.upload-area {
  padding: 20px;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #909399;
  margin-bottom: 10px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.file-list {
  margin-top: 12px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin-bottom: 8px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-size: 14px;
}

.file-size {
  font-size: 12px;
  color: #909399;
}
</style>
