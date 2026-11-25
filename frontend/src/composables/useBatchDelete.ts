import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance } from 'element-plus'
import client from '../api/client'

type SelectedRow = { id: number; code?: string; asset_number?: string; name?: string }

export function useBatchDelete(options: {
  resource: 'racks' | 'devices'
  canDelete: () => boolean
  reload: () => Promise<void>
  onDeleted: (ids: number[]) => void
}) {
  const tableRef = ref<TableInstance>()
  const selectedRows = ref<SelectedRow[]>([])
  const deleting = ref(false)
  const setSelection = (rows: SelectedRow[]) => { selectedRows.value = rows }
  const clearSelection = () => { tableRef.value?.clearSelection(); selectedRows.value = [] }
  const deleteSelected = async () => {
    if (deleting.value || !options.canDelete() || !selectedRows.value.length) return
    const selected = [...selectedRows.value]
    const ids = selected.map(row => row.id)
    const isRack = options.resource === 'racks'
    const label = isRack ? '机柜' : '设备'
    const names = selected.slice(0, 5).map(row => row.code || row.asset_number || row.name || `ID ${row.id}`).join('、')
    const impact = isRack ? '所选机柜内的全部设备及其端口、网络链路也会一并删除。' : '所选设备的端口、网络链路、上架记录和管理员关联也会一并删除，服务器管理员本人会保留。'
    deleting.value = true
    try {
      await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个${label}（${names}${ids.length > 5 ? '等' : ''}）吗？${impact}此操作不可恢复。`, '批量删除确认', {
        type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger',
      })
      const { data } = await client.post(`/${options.resource}/batch-delete`, { ids })
      ElMessage.success(data.message)
      clearSelection()
      options.onDeleted(ids)
      await options.reload()
    } catch (error: any) {
      if (error === 'cancel' || error === 'close') return
      ElMessage.error(error?.response?.data?.detail || '批量删除失败，请刷新列表确认结果后重试')
      // Refresh stale selections without automatically retrying a destructive request.
      await options.reload()
    } finally { deleting.value = false }
  }
  return { tableRef, selectedRows, deleting, setSelection, clearSelection, deleteSelected }
}
