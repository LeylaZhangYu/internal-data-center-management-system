<template>
  <div class="dashboard" v-loading="loading">
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button text @click="load">重新加载</el-button></el-alert>
    <div class="grid-4 dashboard-metrics">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <div class="metric-top"><span>{{ metric.label }}</span><el-icon><component :is="metric.icon" /></el-icon></div>
        <div class="metric-number">{{ metric.value }}<small>{{ metric.unit }}</small></div>
        <div class="metric-bottom"><span>{{ metric.caption }}</span><router-link :to="metric.path" :aria-label="`查看${metric.label}`">↗</router-link></div>
      </article>
    </div>
    <div class="dashboard-grid">
      <el-card class="distribution-card" shadow="never">
        <template #header><div class="panel-heading"><div><h2>设备状态分布</h2><p>按已录入设备状态统计</p></div><span class="panel-badge">{{ summary.device_count }} 台</span></div></template>
        <div v-if="distributionRows.length" class="distribution-layout">
          <div class="status-donut" :style="{ background: donutGradient }" role="img" :aria-label="distributionRows.map(row => `${row.label}：${row.value}台`).join('；')"><div><strong>{{ summary.device_count }}</strong><span>设备总数</span></div></div>
          <div class="status-list"><div v-for="row in distributionRows" :key="row.label" class="status-row"><i :style="{ background: row.color }" /><span>{{ row.label }}</span><strong>{{ row.value }}</strong><small>{{ row.percent }}%</small></div></div>
        </div>
        <el-empty v-else description="暂无设备，录入后即可查看状态分布" :image-size="72"><el-button plain @click="$router.push('/devices')">前往设备管理</el-button></el-empty>
      </el-card>
      <el-card class="alerts-card" shadow="never">
        <template #header><div class="panel-heading"><div><h2>异常提醒</h2><p>容量与设备信息检查</p></div><span class="panel-badge" :class="{ warning: summary.alerts?.length }">{{ summary.alerts?.length || 0 }} 项</span></div></template>
        <div v-if="!summary.alerts?.length" class="quiet-state"><span class="quiet-icon"><el-icon><CircleCheck /></el-icon></span><h3>当前暂无异常提醒</h3><p>平台将根据已录入的数据展示检查结果。</p></div>
        <div v-else class="alert-list"><div v-for="(item, index) in summary.alerts" :key="index" class="alert-row"><el-icon><Warning /></el-icon><span>{{ item }}</span></div></div>
      </el-card>
    </div>
    <el-card shadow="never">
      <template #header><div class="panel-heading"><div><h2>近期设备变更</h2><p>让关键操作有迹可循</p></div><router-link to="/logs" class="panel-link">查看全部记录 ↗</router-link></div></template>
      <el-table :data="summary.recent_changes || []" size="small" empty-text="暂无变更记录">
        <el-table-column prop="created_at" label="时间" width="190" show-overflow-tooltip />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action" label="动作" width="120" />
        <el-table-column prop="message" label="内容" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { OfficeBuilding, Coin, Monitor, DataAnalysis, CircleCheck, Warning } from '@element-plus/icons-vue'
import client from '../api/client'
import { deviceStatusLabel } from '../utils/labels'

const loading = ref(false), error = ref('')
const summary = reactive<any>({ data_center_count: 0, rack_count: 0, device_count: 0, average_rack_utilization: 0, device_status_distribution: {}, recent_changes: [], alerts: [] })
const metrics = computed(() => [
  { label: '机房总数', value: summary.data_center_count, unit: '处', caption: '已录入空间', path: '/datacenters', icon: OfficeBuilding },
  { label: '机柜总数', value: summary.rack_count, unit: '柜', caption: '集中管理机柜', path: '/racks', icon: Coin },
  { label: '设备总数', value: summary.device_count, unit: '台', caption: '已录入设备', path: '/devices', icon: Monitor },
  { label: '平均机柜利用率', value: summary.average_rack_utilization, unit: '%', caption: '机柜 U 位使用情况', path: '/visualization', icon: DataAnalysis },
])
const colors: Record<string, string> = { active: '#2e8d79', standby: '#7093b4', planned: '#a3b8af', maintenance: '#bc9458', retired: '#8e929b', off_shelf: '#c1cac7' }
const distributionRows = computed(() => {
  const entries = Object.entries(summary.device_status_distribution || {}).map(([key, value]) => ({ key, value: Number(value) }))
  const total = entries.reduce((sum, item) => sum + item.value, 0)
  return entries.filter(item => item.value > 0).map(item => ({ ...item, label: deviceStatusLabel(item.key), color: colors[item.key] || '#8e929b', percent: total ? Math.round(item.value / total * 100) : 0 }))
})
const donutGradient = computed(() => {
  const total = distributionRows.value.reduce((sum, row) => sum + row.value, 0)
  let offset = 0
  return total ? `conic-gradient(${distributionRows.value.map(row => { const start = offset; offset += row.value / total * 100; return `${row.color} ${start}% ${offset}%` }).join(',')})` : '#edf1ef'
})
const load = async () => {
  if (loading.value) return
  loading.value = true; error.value = ''
  try { const { data } = await client.get('/overview'); Object.assign(summary, data) }
  catch { error.value = '概览数据读取失败，请稍后重试。' }
  finally { loading.value = false }
}
onMounted(load)
</script>
