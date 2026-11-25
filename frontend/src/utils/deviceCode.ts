type RackLocation = { data_center_id: number; area_id: number }

// Existing identifiers stay stable when moving a device or editing other fields.
export function deviceCodePreview(value: string | null | undefined, rack?: RackLocation, original?: string | null) {
  const code = (value || '').trim()
  if (!code || code === original || !rack) return code
  const suffix = code.replace(/^[0-9]+_[0-9]+_/, '').trim()
  return `${rack.data_center_id}_${rack.area_id}_${suffix}`
}
