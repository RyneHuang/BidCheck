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
