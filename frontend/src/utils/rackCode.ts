export function rackPrefix(room?: number, area?: number) {
  return room && area ? `${room}_${area}_` : ''
}
export function rackSuffix(code: string, room: number, area: number) {
  const prefix = rackPrefix(room, area)
  return code.startsWith(prefix) ? code.slice(prefix.length) : code
}
