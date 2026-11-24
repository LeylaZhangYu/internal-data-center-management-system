import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import * as THREE from 'three'
import ts from 'typescript'

const source = await readFile(new URL('../src/components/topology/geometry.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2020, target: ts.ScriptTarget.ES2020 } }).outputText
  .replace("from 'three'", `from '${new URL('../node_modules/three/build/three.module.js', import.meta.url).href}'`)
const { linkCurve, fittedView } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('same-device port links form a loop instead of doubling back on the same line', () => {
  const start = new THREE.Vector3(0, 12, 0)
  const curve = linkCurve(start, start, 0, true)
  assert.ok(curve.getPoint(0).distanceTo(start) < 1e-9)
  assert.ok(curve.getPoint(1).distanceTo(start) < 1e-9)
  assert.ok(curve.getPoint(.25).distanceTo(curve.getPoint(.75)) > 1)
  assert.ok(linkCurve(start, start, 1, true).getPoint(.5).distanceTo(curve.getPoint(.5)) > 1)
})

test('parallel and reverse links retain endpoints and distinct paths', () => {
  const a = new THREE.Vector3(-4, 12, 0), b = new THREE.Vector3(4, 12, 0)
  const first = linkCurve(a, b, 0, false), second = linkCurve(b, a, 1, false)
  assert.ok(second.getPoint(0).distanceTo(b) < 1e-9)
  assert.ok(second.getPoint(1).distanceTo(a) < 1e-9)
  assert.ok(first.getPoint(.5).distanceTo(second.getPoint(.5)) > 1)
})

test('camera frames large link arcs as well as nodes at wide and narrow aspect ratios', () => {
  const points = [new THREE.Vector3(-18, 0, -12), new THREE.Vector3(18, 40, 12)]
  for (let index = 0; index < 40; index++) points.push(...linkCurve(points[0], points[1], index, false).getPoints(40))
  const box = new THREE.Box3().setFromPoints(points)
  for (const aspect of [.35, 1, 2.5]) for (const top of [true, false]) {
    const { center, position, distance } = fittedView(box, 42, aspect, top)
    const camera = new THREE.PerspectiveCamera(42, aspect, .1, distance * 5)
    camera.position.copy(position); camera.lookAt(center); camera.updateMatrixWorld(true)
    for (const point of points) {
      const ndc = point.clone().project(camera)
      assert.ok(Math.abs(ndc.x) <= 1 && Math.abs(ndc.y) <= 1 && ndc.z < 1 && ndc.z > -1)
    }
  }
})
