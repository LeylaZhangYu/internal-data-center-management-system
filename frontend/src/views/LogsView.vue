<template>
  <div class="page-card">
    <el-table :data="rows">
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column prop="module" label="模块" width="120" />
      <el-table-column prop="action" label="操作" width="120" />
      <el-table-column prop="target_type" label="对象类型" width="120" />
      <el-table-column prop="target_id" label="对象ID" width="120" />
      <el-table-column prop="message" label="说明" />
    </el-table>
    <div style="margin-top:16px; display:flex; justify-content:flex-end">
      <el-pagination background layout="prev, pager, next, total" :total="total" v-model:current-page="page" :page-size="pageSize" @current-change="load" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import client from '../api/client'

const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const load = async () => {
  const { data } = await client.get('/logs', { params: { page: page.value, page_size: pageSize } })
  rows.value = data.items
  total.value = data.total
}
onMounted(load)
</script>
