import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import ts from 'typescript'
const source = await readFile(new URL('../src/utils/rackCode.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2020, target: ts.ScriptTarget.ES2020 } }).outputText
const { rackPrefix, rackSuffix } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
test('prefix preview waits for room and area selection', () => {
  assert.equal(rackPrefix(1, undefined), '')
  assert.equal(rackPrefix(1, 2), '1_2_')
})
test('editing strips only the actual room and area prefix, keeping leading zeroes', () => {
  assert.equal(rackSuffix('1_2_001', 1, 2), '001')
  assert.equal(rackSuffix('A01', 1, 2), 'A01')
  assert.equal(rackSuffix('123_4_001', 1, 2), '123_4_001')
  assert.equal(rackPrefix(3, 4) + rackSuffix('1_2_001', 1, 2), '3_4_001')
})
