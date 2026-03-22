<template>
  <div class="result-page">
    <header class="header">
      <div class="header-content">
        <div class="left">
          <el-button text @click="router.push('/')">
            ← 返回
          </el-button>
          <span class="project-name">{{ report?.project_name || '分析结果' }}</span>
        </div>
        <div class="actions">
          <el-button @click="download('html')">HTML</el-button>
          <el-button @click="download('json')">JSON</el-button>
        </div>
      </div>
    </header>

    <main v-if="report" class="main-content">
      <RiskCard
        :score="report.risk_score"
        :level="report.risk_level"
        :traces-count="report.traces.length"
        :high-risk-count="highRiskTraces.length"
      />

      <el-row :gutter="20" class="charts-row">
        <el-col :span="12">
          <el-card>
            <template #header>📊 投标方风险热力图</template>
            <div ref="heatmapRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>🔗 关联关系网络图</template>
            <div ref="networkRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-card class="traces-card">
        <template #header>
          <div class="traces-header">
            <span>📋 检测到的可疑痕迹</span>
            <el-select v-model="filter" placeholder="筛选类型" clearable size="small">
              <el-option label="全部" value="" />
              <el-option label="高风险" value="high" />
              <el-option label="编辑会话" value="rsid" />
            </el-select>
          </div>
        </template>
        <TraceTable :traces="filteredTraces" />
      </el-card>
    </main>

    <div v-else class="loading">
      <el-empty description="加载中..." />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import RiskCard from '@/components/RiskCard.vue'
import TraceTable from '@/components/TraceTable.vue'
import { getReportDetail, getDownloadUrl } from '@/api'

const route = useRoute()
const router = useRouter()

const report = ref(null)
const filter = ref('')
const heatmapRef = ref(null)
const networkRef = ref(null)

const highRiskTraces = computed(() => {
  return report.value?.traces.filter(t => t.weight >= 0.8) || []
})

const filteredTraces = computed(() => {
  if (!report.value) return []
  let traces = report.value.traces

  if (filter.value === 'high') {
    traces = traces.filter(t => t.weight >= 0.8)
  } else if (filter.value === 'rsid') {
    traces = traces.filter(t => t.type.includes('rsid'))
  }

  return traces
})

onMounted(async () => {
  const taskId = route.params.taskId

  try {
    report.value = await getReportDetail(taskId)
    nextTick(() => {
      renderCharts()
    })
  } catch (error) {
    ElMessage.error('加载报告失败: ' + error.message)
  }
})

const renderCharts = () => {
  renderHeatmap()
  renderNetwork()
}

const renderHeatmap = () => {
  if (!heatmapRef.value || !report.value) return

  const chart = echarts.init(heatmapRef.value)
  const bidders = report.value.bidders
  const data = report.value.heatmap_data

  chart.setOption({
    tooltip: {
      position: 'top'
    },
    grid: {
      top: 10,
      left: 80,
      right: 10,
      bottom: 60
    },
    xAxis: {
      type: 'category',
      data: bidders,
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: bidders,
      splitArea: { show: true }
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#fff7e6', '#ffd591', '#ff7a45', '#d4380d']
      }
    },
    series: [{
      type: 'heatmap',
      data: data.flatMap((row, i) =>
        row.map((val, j) => [i, j, val || '-'])
      ),
      label: {
        show: true
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  })
}

const renderNetwork = () => {
  if (!networkRef.value || !report.value) return

  const chart = echarts.init(networkRef.value)
  const nodes = report.value.network_nodes
  const edges = report.value.network_edges

  chart.setOption({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes.map(n => ({
        name: n.name,
        symbolSize: 50,
        itemStyle: {
          color: '#409eff'
        }
      })),
      links: edges.map(e => ({
        source: e.source,
        target: e.target,
        value: e.weight
      })),
      label: {
        show: true,
        position: 'bottom'
      },
      force: {
        repulsion: 200,
        edgeLength: 100
      },
      lineStyle: {
        width: 2,
        curveness: 0.1
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 4
        }
      }
    }]
  })
}

const download = (format) => {
  const url = getDownloadUrl(route.params.taskId, format)
  window.open(url, '_blank')
}
</script>

<style scoped>
.result-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.header {
  background: white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.project-name {
  font-size: 18px;
  font-weight: 500;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.charts-row {
  margin-bottom: 24px;
}

.chart-container {
  height: 300px;
}

.traces-card {
  margin-bottom: 24px;
}

.traces-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}
</style>
