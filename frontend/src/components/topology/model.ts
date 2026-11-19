export interface SceneDevice {
  id: number; name: string; device_type: string; status: string
  asset_number: string | null; model: string | null; ip_address: string | null
  purpose: string | null; notes: string | null; data_center_id: number | null
  data_center_name: string | null; area_name: string | null; rack_code: string | null
  start_u: number | null; u_height: number; administrators: string[]
}
export interface SceneLink {
  id: number; source: number; target: number; source_port: string; target_port: string
  bandwidth: string | null; vlan: string | null; status: string; description: string | null
}
export interface SceneData {
  data_centers: { id: number; name: string }[]; nodes: SceneDevice[]; links: SceneLink[]
}
export const tiers = [
  { name: '安全设备', description: '防火墙', color: '#ff9566', types: ['firewall'] },
  { name: '网络交换', description: '交换机', color: '#62abff', types: ['switch'] },
  { name: '服务器计算', description: '通用 / CPU / GPU / 管理节点', color: '#4cd9b0', types: ['server', 'cpu_server', 'gpu_server', 'management_node'] },
  { name: '存储设备', description: '数据存储', color: '#bb92ff', types: ['storage'] },
  { name: '配套与其他', description: 'PDU / 其他设备', color: '#f4cf72', types: ['pdu', 'other'] },
]
export const tierIndex = (type: string) => {
  const index = tiers.findIndex(tier => tier.types.includes(type))
  return index < 0 ? tiers.length - 1 : index
}
export const linkColors: Record<string, string> = { up: '#53d9c2', down: '#ff7186', planned: '#e8bd66' }
export const linkLabels: Record<string, string> = { up: '正常', down: '中断', planned: '规划中' }
export const locationLabel = (node: SceneDevice) => [node.data_center_name, node.area_name, node.rack_code].filter(Boolean).join(' / ') || '未分配机柜'

// A room view retains directly connected external devices so cross-room links stay visible.
export function scopeGraph(data: SceneData, room: string, tier: number | null) {
  const local = new Set(data.nodes.filter(n => room === 'all' || (room === 'unassigned' ? n.data_center_id === null : String(n.data_center_id) === room)).map(n => n.id))
  const included = new Set(local)
  if (room !== 'all') data.links.forEach(link => {
    if (local.has(link.source)) included.add(link.target)
    if (local.has(link.target)) included.add(link.source)
  })
  const nodes = data.nodes.filter(n => included.has(n.id) && (tier === null || tierIndex(n.device_type) === tier))
  const ids = new Set(nodes.map(n => n.id))
  const links = data.links.filter(l => ids.has(l.source) && ids.has(l.target) && (room === 'all' || local.has(l.source) || local.has(l.target)))
  return { nodes, links, local }
}
