<template>
  <el-table :data="traces" stripe style="width: 100%">
    <el-table-column prop="type" label="类型" width="150">
      <template #default="{ row }">
        <el-tag>{{ row.type }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="投标方" width="200">
      <template #default="{ row }">
        {{ row.bidder_a }} ↔ {{ row.bidder_b }}
      </template>
    </el-table-column>
    <el-table-column prop="value" label="匹配值" width="180">
      <template #default="{ row }">
        <span class="value-cell">{{ row.value }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="weight" label="权重" width="80">
      <template #default="{ row }">
        <el-progress
          :percentage="row.weight * 100"
          :color="getWeightColor(row.weight)"
          :show-text="false"
        />
        <span class="weight-text">{{ row.weight.toFixed(2) }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="evidence" label="证据描述" />
  </el-table>
</template>

<script setup>
defineProps({
  traces: { type: Array, default: () => [] }
})

const getWeightColor = (weight) => {
  if (weight >= 0.85) return '#F56C6C'
  if (weight >= 0.7) return '#E6A23C'
  if (weight >= 0.5) return '#409EFF'
  return '#67C23A'
}
</script>

<style scoped>
.value-cell {
  font-family: monospace;
  font-size: 12px;
}

.weight-text {
  font-size: 12px;
  color: #606266;
}
</style>
