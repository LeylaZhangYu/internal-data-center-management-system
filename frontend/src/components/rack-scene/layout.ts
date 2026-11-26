export interface RackDevice {
  id: number
  asset_number: string | null
  name: string
  model: string | null
  ip_address: string | null
  status: string
  start_u: number | null
  u_height: number
  administrators: string[]
  links: string[]
}
export interface RackLayout {
  id: number
  code: string
  category?: string
  x_position: number
  y_position: number
  orientation: string
  total_u: number
  utilization_rate: number
  device_count: number
  devices: RackDevice[]
}
export interface AreaLayout { id: number; name: string; racks: RackLayout[] }
export interface DataCenterLayout { id: number; name: string; areas: AreaLayout[] }
export const areaColors = ['#64adff', '#4dd5c0', '#ae99ff', '#e7b778', '#7fcddd']
export const rackCategoryStyle = (category?: string) => {
  switch (category) {
    case 'row_air_conditioner': return { kind: 'air-conditioner', label: '列间空调', accent: '#54c9dc' }
    case 'row_head_cabinet': return { kind: 'head-cabinet', label: '列头柜', accent: '#6cb7ff' }
    case 'power_distribution_cabinet': return { kind: 'power-cabinet', label: '配电柜', accent: '#e7aa58' }
    default: return { kind: 'rack', label: '机柜', accent: '#6888a5' }
  }
}
export const statusColors: Record<string, string> = {
  active: '#4edbb5', standby: '#69b2ff', maintenance: '#ffbc69', planned: '#af98ff', retired: '#8391a9', off_shelf: '#8391a9',
}
export const unitHeight = .105
export const rackHeight = (rack: RackLayout) => rack.total_u * unitHeight + .44
export function devicePlacement(device: RackDevice) {
  const height = device.u_height * unitHeight - .012
  return { height, y: .22 + ((device.start_u || 1) - 1) * unitHeight + device.u_height * unitHeight / 2 }
}
// Areas use local rack coordinates. Separate their display panels without changing the stored layout.
export function placeAreas(areas: AreaLayout[]) {
  let cursor = 0
  return areas.flatMap((area, index) => {
    if (!area.racks.length) return []
    const xs = area.racks.map(rack => rack.x_position), zs = area.racks.map(rack => rack.y_position)
    const minX = Math.min(...xs), maxX = Math.max(...xs), minZ = Math.min(...zs), maxZ = Math.max(...zs)
    const width = Math.max(5, maxX - minX + 4), depth = Math.max(5, maxZ - minZ + 4)
    const centerX = cursor + width / 2
    const offsetX = centerX - (minX + maxX) / 2, offsetZ = -(minZ + maxZ) / 2
    cursor += width + 2.5
    return [{ area, width, depth, centerX, offsetX, offsetZ, color: areaColors[index % areaColors.length] }]
  })
}

// A stale off-shelf record may still retain placement fields in older databases.
export const isMounted = (device: RackDevice) => device.status !== 'off_shelf'
  && device.start_u !== null && device.start_u > 0
