const bilingual = (labels: Record<string, string>, value?: string) => {
  if (!value) return '-'
  return labels[value] ? `${labels[value]} (${value})` : value
}

export const deviceTypeLabel = (value?: string) => bilingual({ server: '通用服务器', gpu_server: 'GPU服务器', cpu_server: 'CPU服务器', management_node: '管理节点', switch: '交换机', storage: '存储', pdu: '配电单元', firewall: '防火墙', other: '其他' }, value)
export const deviceStatusLabel = (value?: string) => bilingual({ planned: '计划中', active: '运行中', standby: '待机', maintenance: '维护中', retired: '已退役', off_shelf: '已下架' }, value)
export const linkStatusLabel = (value?: string) => bilingual({ up: '正常', down: '断开', planned: '计划中' }, value)
export const orientationLabel = (value?: string) => bilingual({ north: '北向', south: '南向', east: '东向', west: '西向' }, value)
export const roleLabel = (value?: string) => bilingual({ admin: '管理员' }, value)
