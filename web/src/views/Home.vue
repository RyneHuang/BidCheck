<template>
  <div class="home-page">
    <header class="header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-icon">🔍</span>
          <h1>围标检测系统</h1>
        </div>
      </div>
    </header>

    <main class="main-content">
      <el-card class="info-card" shadow="never">
        <div class="info-content">
          <span class="info-icon">📋</span>
          <div>
            <h3>使用说明</h3>
            <ol>
              <li>输入项目名称</li>
              <li>为每个投标方上传文件（支持 .docx, .xlsx, .pdf）</li>
              <li>点击"开始分析"按钮</li>
              <li>查看风险评分和可疑痕迹</li>
            </ol>
          </div>
        </div>
      </el-card>

      <el-card class="upload-card">
        <template #header>
          <div class="card-header">
            <span>📁 上传投标文件</span>
            <el-tag type="info" size="small">支持 .docx .xlsx .pdf</el-tag>
          </div>
        </template>

        <div class="project-input">
          <el-input v-model="projectName" placeholder="请输入项目名称" size="large">
            <template #prepend>项目名称</template>
          </el-input>
        </div>

        <div class="bidders-section">
          <div v-for="(bidder, index) in bidders" :key="index" class="bidder-block">
            <div class="bidder-header">
              <el-input v-model="bidder.name" placeholder="投标方名称" class="bidder-name" />
              <el-button v-if="bidders.length > 2" type="danger" text @click="removeBidder(index)">
                删除
              </el-button>
            </div>
            <FileUploader v-model="bidder.files" />
          </div>
        </div>

        <el-button type="primary" plain class="add-btn" @click="addBidder">
          + 添加投标方
        </el-button>

        <div class="action-bar">
          <el-button
            type="primary"
            size="large"
            :loading="analyzing"
            :disabled="!canAnalyze"
            @click="startAnalysis"
          >
            {{ analyzing ? '分析中...' : '开始分析' }}
          </el-button>
        </div>
      </el-card>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FileUploader from '@/components/FileUploader.vue'
import { createAnalysis, pollTaskStatus } from '@/api'

const router = useRouter()

const projectName = ref('')
const analyzing = ref(false)
const bidders = ref([
  { name: '投标方A', files: [] },
  { name: '投标方B', files: [] },
])

const canAnalyze = computed(() => {
  return projectName.value.trim() &&
    bidders.value.every(b => b.files.length > 0)
})

const addBidder = () => {
  const nextLetter = String.fromCharCode(65 + bidders.value.length)
  bidders.value.push({ name: `投标方${nextLetter}`, files: [] })
}

const removeBidder = (index) => {
  bidders.value.splice(index, 1)
}

const startAnalysis = async () => {
  if (!canAnalyze.value) {
    ElMessage.warning('请填写项目名称并上传文件')
    return
  }

  analyzing.value = true

  try {
    const result = await createAnalysis(projectName.value, bidders.value)
    ElMessage.success('分析任务已创建，正在处理...')

    await pollTaskStatus(result.task_id, (status) => {
      console.log('Progress:', status.progress)
    })

    router.push(`/result/${result.task_id}`)
  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 24px;
}

.logo h1 {
  font-size: 20px;
  color: #303133;
}

.main-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}

.info-card {
  margin-bottom: 24px;
}

.info-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.info-icon {
  font-size: 28px;
}

.info-content h3 {
  font-size: 16px;
  margin-bottom: 8px;
}

.info-content ol {
  font-size: 14px;
  color: #606266;
  padding-left: 20px;
}

.upload-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-input {
  margin-bottom: 24px;
}

.bidders-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bidder-block {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fafafa;
}

.bidder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.bidder-name {
  width: 200px;
}

.add-btn {
  margin-top: 16px;
}

.action-bar {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>
