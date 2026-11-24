import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/components/rack-scene/layout.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2020, target: ts.ScriptTarget.ES2020 } }).outputText
const { placeAreas, devicePlacement, rackHeight, unitHeight, isMounted, areaColors } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('areas with identical local origins are separated and keep relative rack spacing', () => {
  const areas = [
    { id: 1, name: 'A区', racks: [{ x_position: -2.2, y_position: 4 }, { x_position: 0, y_position: 8 }] },
    { id: 2, name: 'B区', racks: [{ x_position: -2.2, y_position: 4 }] },
  ]
  const original = JSON.stringify(areas)
  const [a, b] = placeAreas(areas)
  assert.ok(a.centerX + a.width / 2 < b.centerX - b.width / 2)
  const positions = a.area.racks.map(rack => ({ x: rack.x_position + a.offsetX, z: rack.y_position + a.offsetZ }))
  assert.ok(Math.abs(positions[1].x - positions[0].x - 2.2) < 1e-9)
  assert.equal(positions[1].z - positions[0].z, 4)
  assert.equal(JSON.stringify(areas), original)
})
test('1U devices on adjacent U slots do not overlap and the top device fits in 48U racks', () => {
  const lower = devicePlacement({ start_u: 1, u_height: 1 })
  const upper = devicePlacement({ start_u: 2, u_height: 1 })
  assert.ok(lower.y + lower.height / 2 < upper.y - upper.height / 2)
  assert.ok(Math.abs(upper.y - lower.y - unitHeight) < 1e-9)
  const top = devicePlacement({ start_u: 45, u_height: 4 })
  assert.ok(top.y + top.height / 2 < rackHeight({ total_u: 48 }) - .16)
  assert.ok(lower.y - lower.height / 2 > .16)
})
test('empty areas produce no invalid scene coordinates', () => {
  assert.deepEqual(placeAreas([]), [])
  assert.deepEqual(placeAreas([{ id: 1, name: '空区域', racks: [] }]), [])
})

test('off-shelf records with stale U slots are not mounted', () => {
  assert.equal(isMounted({ status: 'off_shelf', start_u: 1 }), false)
  assert.equal(isMounted({ status: 'active', start_u: null }), false)
  assert.equal(isMounted({ status: 'active', start_u: 0 }), false)
  assert.equal(isMounted({ status: 'active', start_u: 1 }), true)
})

test('empty areas do not shift scene colors away from the area legend', () => {
  const [placement] = placeAreas([
    { id: 1, name: 'empty', racks: [] },
    { id: 2, name: 'populated', racks: [{ x_position: 0, y_position: 0 }] },
  ])
  assert.equal(placement.color, areaColors[1])
})
