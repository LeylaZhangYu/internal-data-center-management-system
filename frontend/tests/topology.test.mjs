import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/components/topology/model.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2020, target: ts.ScriptTarget.ES2020 } }).outputText
const { scopeGraph, tierIndex } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const data = {
  nodes: [
    { id: 1, data_center_id: 1, device_type: 'switch' },
    { id: 2, data_center_id: 2, device_type: 'server' },
    { id: 3, data_center_id: 2, device_type: 'storage' },
    { id: 4, data_center_id: null, device_type: 'other' },
    { id: 5, data_center_id: 1, device_type: 'pdu' },
  ],
  links: [{ id: 1, source: 1, target: 2 }, { id: 2, source: 2, target: 3 }, { id: 3, source: 1, target: 2 }],
}
test('all devices include isolated/unassigned nodes and parallel port links', () => {
  const graph = scopeGraph(data, 'all', null)
  assert.equal(graph.nodes.length, 5)
  assert.equal(graph.links.length, 3)
})
test('room scope retains direct external neighbors without traversing unrelated rooms', () => {
  const graph = scopeGraph(data, '1', null)
  assert.deepEqual(graph.nodes.map(n => n.id), [1, 2, 5])
  assert.deepEqual(graph.links.map(l => l.id), [1, 3])
  assert.deepEqual([...graph.local], [1, 5])
})
test('type filtering never leaves an edge without both visible endpoints', () => {
  const graph = scopeGraph(data, '1', tierIndex('switch'))
  assert.deepEqual(graph.nodes.map(n => n.id), [1])
  assert.deepEqual(graph.links, [])
})
test('unassigned and empty rooms have truthful empty connections', () => {
  assert.deepEqual(scopeGraph(data, 'unassigned', null).nodes.map(n => n.id), [4])
  assert.deepEqual(scopeGraph(data, 'unassigned', null).links, [])
  assert.deepEqual(scopeGraph(data, '999', null).nodes, [])
})
