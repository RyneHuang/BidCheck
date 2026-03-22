# Phase 5: Web 前端界面

## 概述

本阶段实现 Web 前端界面，提供可视化的围标检测操作体验。

## 技术栈

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "element-plus": "^2.5.0",
    "echarts": "^5.4.0",
    "axios": "^1.6.0",
    "pinia": "^2.1.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

## 项目结构

```
web/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   └── index.js
│   ├── stores/
│   │   └── analysis.js
│   ├── api/
│   │   └── index.js
│   ├── views/
│   │   ├── Home.vue
│   │   ├── Result.vue
│   │   └── History.vue
│   ├── components/
│   │   ├── FileUploader.vue
│   │   ├── RiskCard.vue
│   │   ├── TraceTable.vue
│   │   ├── HeatmapChart.vue
│   │   └── NetworkGraph.vue
│   └── styles/
│       └── main.css
└── public/
    └── favicon.ico
```

## API 封装

```javascript
// src/api/index.js

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
})

export async function createAnalysis(projectName, bidderFiles) {
  const formData = new FormData()

  // 添加投标方名称
  const bidderNames = bidderFiles.map(b => b.name)
  formData.append('bidder_names', JSON.stringify(bidderNames))
  formData.append('project_name', projectName)

  // 添加文件
  bidderFiles.forEach(bidder => {
    bidder.files.forEach(file => {
      formData.append('files', file)
    })
  })

  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })

  return response.data
}

export async function getTaskStatus(taskId) {
  const response = await api.get(`/status/${taskId}`)
  return response.data
}

export async function getReportDetail(taskId) {
  const response = await api.get(`/report/${taskId}`)
  return response.data
}

export function getDownloadUrl(taskId, format = 'html') {
  return `${API_BASE}/api/v1/download/${taskId}?format=${format}`
}

export async function pollTaskStatus(taskId, onProgress, interval = 2000) {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId)
        onProgress?.(status)

        if (status.status === 'completed') {
          resolve(status)
        } else if (status.status === 'failed') {
          reject(new Error(status.error || '分析失败'))
        } else {
          setTimeout(poll, interval)
        }
      } catch (error) {
        reject(error)
      }
    }
    poll()
  })
}
```

## 路由配置

```javascript
// src/router/index.js

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/result/:taskId',
    name: 'Result',
    component: () => import('../views/Result.vue')
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

## 主页面

```vue
<!-- src/views/Home.vue -->

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 头部 -->
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <span class="text-2xl">🔍</span>
          <h1 class="text-xl font-bold text-gray-800">围标检测系统</h1>
        </div>
        <el-button text @click="$router.push('/history')">
          <el-icon><Clock /></el-icon>
          历史记录
        </el-button>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="max-w-5xl mx-auto px-4 py-8">
      <!-- 说明卡片 -->
      <el-card class="mb-6" shadow="never">
        <div class="flex items-start gap-4">
          <span class="text-3xl">📋</span>
          <div>
            <h3 class="font-semibold text-gray-800 mb-2">使用说明</h3>
            <ol class="text-sm text-gray-600 space-y-1">
              <li>1. 输入项目名称</li>
              <li>2. 为每个投标方上传文件（支持 .docx, .xlsx, .pdf）</li>
              <li>3. 点击"开始分析"按钮</li>
              <li>4. 查看风险评分和可疑痕迹</li>
            </ol>
          </div>
        </div>
      </el-card>

      <!-- 上传区域 -->
      <el-card>
        <template #header>
          <div class="flex justify-between items-center">
            <span class="font-semibold">📁 上传投标文件</span>
            <el-tag type="info" size="small">支持 .docx .xlsx .pdf</el-tag>
          </div>
        </template>

        <!-- 项目名称 -->
        <div class="mb-6">
          <el-input
            v-model="projectName"
            placeholder="请输入项目名称"
            size="large"
          >
            <template #prepend>项目名称</template>
          </el-input>
        </div>

        <!-- 投标方文件 -->
        <div class="space-y-4">
          <div
            v-for="(bidder, index) in bidders"
            :key="index"
            class="border rounded-lg p-4 bg-gray-50"
          >
            <div class="flex justify-between items-center mb-3">
              <el-input
                v-model="bidder.name"
                placeholder="投标方名称"
                class="w-48"
              />
              <el-button
                v-if="bidders.length > 2"
                type="danger"
                text
                @click="removeBidder(index)"
              >
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>

            <FileUploader
              v-model="bidder.files"
              accept=".docx,.xlsx,.pdf"
              :max-size="50"
            />
          </div>
        </div>

        <!-- 添加投标方 -->
        <el-button
          type="primary"
          plain
          class="mt-4"
          @click="addBidder"
        >
          <el-icon><Plus /></el-icon>
          添加投标方
        </el-button>

        <!-- 开始分析 -->
        <div class="mt-6 flex justify-center">
          <el-button
            type="primary"
            size="large"
            :loading="analyzing"
            :disabled="!canAnalyze"
            @click="startAnalysis"
          >
            <el-icon v-if="!analyzing"><Search /></el-icon>
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

    // 轮询等待完成
    await pollTaskStatus(result.task_id, (status) => {
      console.log('Progress:', status.progress)
    })

    // 跳转到结果页
    router.push(`/result/${result.task_id}`)

  } catch (error) {
    ElMessage.error(error.message || '分析失败')
  } finally {
    analyzing.value = false
  }
}
</script>
```

## 文件上传组件

```vue
<!-- src/components/FileUploader.vue -->

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
      <div class="el-upload__text">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div>拖拽文件到此处，或 <em>点击上传</em></div>
        <div class="text-xs text-gray-400 mt-1">
          {{ accept }} 文件，单个最大 {{ maxSize }}MB
        </div>
      </div>
    </el-upload>

    <!-- 已上传文件列表 -->
    <div v-if="fileList.length" class="mt-3 space-y-2">
      <div
        v-for="file in fileList"
        :key="file.uid"
        class="flex items-center justify-between p-2 bg-white rounded border"
      >
        <div class="flex items-center gap-2">
          <el-icon><Document /></el-icon>
          <span class="text-sm">{{ file.name }}</span>
          <span class="text-xs text-gray-400">{{ formatSize(file.size) }}</span>
        </div>
        <el-button
          type="danger"
          text
          size="small"
          @click="removeFile(file)"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

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
  // 验证文件大小
  const validFiles = uploadFiles.filter(f => {
    const sizeMB = f.size / 1024 / 1024
    if (sizeMB > props.maxSize) {
      return false
    }
    return true
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
```

## 风险评分卡片

```vue
<!-- src/components/RiskCard.vue -->

<template>
  <div class="risk-card" :class="levelClass">
    <div class="score-section">
      <el-progress
        type="dashboard"
        :percentage="score"
        :color="scoreColor"
        :width="140"
        :stroke-width="12"
      >
        <template #default>
          <div class="score-content">
            <span class="score-number">{{ score.toFixed(1) }}</span>
            <span class="score-label">风险评分</span>
          </div>
        </template>
      </el-progress>
    </div>

    <div class="info-section">
      <h2 class="level-title">{{ levelText }}</h2>
      <p class="level-desc">{{ levelDesc }}</p>

      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-value">{{ tracesCount }}</span>
          <span class="stat-label">可疑痕迹</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ highRiskCount }}</span>
          <span class="stat-label">高风险项</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  level: { type: String, default: 'low' },
  tracesCount: { type: Number, default: 0 },
  highRiskCount: { type: Number, default: 0 }
})

const levelClass = computed(() => `level-${props.level}`)

const scoreColor = computed(() => {
  if (props.score >= 80) return '#F56C6C'
  if (props.score >= 60) return '#E6A23C'
  if (props.score >= 40) return '#409EFF'
  return '#67C23A'
})

const levelText = computed(() => {
  const map = {
    low: '✅ 低风险',
    medium: '⚠️ 中等风险',
    high: '🔶 高风险',
    critical: '🚨 极高风险'
  }
  return map[props.level] || '未知'
})

const levelDesc = computed(() => {
  if (props.score >= 80) return '存在高度可疑的围标迹象，建议重点审查'
  if (props.score >= 60) return '发现多项可疑痕迹，需要进一步核实'
  if (props.score >= 40) return '存在少量异常，建议关注'
  return '未发现明显异常'
})
</script>

<style scoped>
.risk-card {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 30px;
  border-radius: 16px;
  color: white;
}

.level-low {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}
.level-medium {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.level-high {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
.level-critical {
  background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
}

.score-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.score-number {
  font-size: 32px;
  font-weight: bold;
}

.score-label {
  font-size: 12px;
  opacity: 0.8;
}

.level-title {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 8px;
}

.level-desc {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 20px;
}

.stats-row {
  display: flex;
  gap: 30px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  display: block;
}

.stat-label {
  font-size: 12px;
  opacity: 0.8;
}
</style>
```

## 结果页面

```vue
<!-- src/views/Result.vue -->

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <el-button text @click="$router.push('/')">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <h1 class="text-lg font-semibold">{{ report?.projectName || '分析结果' }}</h1>
        </div>
        <div class="flex gap-2">
          <el-button @click="downloadReport('html')">
            <el-icon><Download /></el-icon>
            HTML
          </el-button>
          <el-button @click="downloadReport('json')">
            <el-icon><Document /></el-icon>
            JSON
          </el-button>
        </div>
      </div>
    </header>

    <main v-if="report" class="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <!-- 风险概览 -->
      <RiskCard
        :score="report.riskScore"
        :level="report.riskLevel"
        :traces-count="report.traces.length"
        :high-risk-count="highRiskTraces.length"
      />

      <!-- 可视化图表 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card>
            <template #header>📊 投标方风险热力图</template>
            <HeatmapChart :data="report.heatmapData" :labels="report.bidders" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>🔗 关联关系网络图</template>
            <NetworkGraph
              :nodes="report.networkNodes"
              :edges="report.networkEdges"
            />
          </el-card>
        </el-col>
      </el-row>

      <!-- 痕迹详情 -->
      <el-card>
        <template #header>
          <div class="flex justify-between items-center">
            <span>📋 检测到的可疑痕迹</span>
            <el-select v-model="filterType" placeholder="筛选类型" clearable size="small">
              <el-option label="全部" value="" />
              <el-option label="高风险" value="high" />
              <el-option label="编辑会话" value="rsid" />
              <el-option label="设备痕迹" value="device" />
            </el-select>
          </div>
        </template>

        <TraceTable :traces="filteredTraces" />
      </el-card>
    </main>

    <!-- 加载中 -->
    <div v-else class="flex items-center justify-center h-96">
      <el-empty description="加载中..." />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import RiskCard from '@/components/RiskCard.vue'
import HeatmapChart from '@/components/HeatmapChart.vue'
import NetworkGraph from '@/components/NetworkGraph.vue'
import TraceTable from '@/components/TraceTable.vue'
import { getReportDetail, getDownloadUrl } from '@/api'

const route = useRoute()
const report = ref(null)
const filterType = ref('')

const highRiskTraces = computed(() => {
  return report.value?.traces.filter(t => t.weight >= 0.8) || []
})

const filteredTraces = computed(() => {
  if (!report.value) return []

  let traces = report.value.traces

  if (filterType.value === 'high') {
    traces = traces.filter(t => t.weight >= 0.8)
  } else if (filterType.value === 'rsid') {
    traces = traces.filter(t => t.type.includes('rsid') || t.type.includes('revision'))
  } else if (filterType.value === 'device') {
    traces = traces.filter(t =>
      t.type.includes('printer') || t.type.includes('template') || t.type.includes('computer')
    )
  }

  return traces
})

onMounted(async () => {
  const taskId = route.params.taskId

  try {
    report.value = await getReportDetail(taskId)
  } catch (error) {
    ElMessage.error('加载报告失败: ' + error.message)
  }
})

const downloadReport = (format) => {
  const url = getDownloadUrl(route.params.taskId, format)
  window.open(url, '_blank')
}
</script>
```

## 验收标准

- [ ] 首页可正确显示上传表单
- [ ] 可添加/删除投标方
- [ ] 文件上传功能正常
- [ ] 分析后可跳转到结果页
- [ ] 风险评分卡片显示正确
- [ ] 热力图渲染正确
- [ ] 网络图渲染正确
- [ ] 痕迹表格可筛选
- [ ] 报告下载功能正常
- [ ] 响应式布局适配移动端
