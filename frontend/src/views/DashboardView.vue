<template>
  <div class="dashboard">
    <div class="grid-4">
      <el-card class="metric-card"><div class="metric-label">机房数</div><h2 class="metric-value">{{ summary.data_center_count }}</h2></el-card>
      <el-card class="metric-card"><div class="metric-label">机柜数</div><h2 class="metric-value">{{ summary.rack_count }}</h2></el-card>
      <el-card class="metric-card"><div class="metric-label">设备数</div><h2 class="metric-value">{{ summary.device_count }}</h2></el-card>
      <el-card><div>平均机柜利用率</div><h2>{{ summary.average_rack_utilization }}%</h2></el-card>
    </div>
    <div class="dashboard-grid">
      <el-card>
        <template #header><strong>设备状态分布</strong></template>
        <el-table :data="distributionRows" size="small">
          <el-table-column prop="label" label="状态" />
          <el-table-column prop="value" label="数量" />
        </el-table>
      </el-card>
      <el-card>
        <template #header><strong>异常提醒</strong></template>
        <el-empty v-if="!summary.alerts?.length" description="暂无异常" />
        <el-timeline v-else>
          <el-timeline-item v-for="(item, index) in summary.alerts" :key="index" type="warning">{{ item }}</el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
    <el-card>
      <template #header><strong>近期设备变更</strong></template>
      <el-table :data="summary.recent_changes || []" size="small">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action" label="动作" width="120" />
        <el-table-column prop="message" label="内容" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import client from '../api/client'

const summary = reactive<any>({
  data_center_count: 0,
  rack_count: 0,
  device_count: 0,
  average_rack_utilization: 0,
  device_status_distribution: {},
  recent_changes: [],
  alerts: [],
})

const distributionRows = computed(() => Object.entries(summary.device_status_distribution || {}).map(([label, value]) => ({ label, value })))

const load = async () => {
  const { data } = await client.get('/overview')
  Object.assign(summary, data)
}

onMounted(load)
</script>
