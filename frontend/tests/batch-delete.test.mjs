import assert from 'node:assert/strict'
import { test } from 'node:test'
import { readFile } from 'node:fs/promises'
import { ref } from 'vue'
import ts from 'typescript'

const source = await readFile(new URL('../src/composables/useBatchDelete.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
function setup({ confirm = async () => {}, post = async () => ({ data: { message: '已删除' } }) } = {}) {
  const calls = [], messages = [], deleted = [], exports = {}
  let reloads = 0, cleared = 0, allowed = true
  const modules = {
    vue: { ref },
    'element-plus': { ElMessage: { success: value => messages.push(value), error: value => messages.push(value) }, ElMessageBox: { confirm } },
    '../api/client': { default: { post: async (...args) => { calls.push(args); return post(...args) } } },
  }
  new Function('require', 'exports', compiled)(name => modules[name], exports)
  const state = exports.useBatchDelete({ resource: 'racks', canDelete: () => allowed, reload: async () => { reloads++ }, onDeleted: ids => deleted.push(ids) })
  state.tableRef.value = { clearSelection() { cleared++ } }
  return { ...state, calls, messages, deleted, get reloads() { return reloads }, get cleared() { return cleared }, block: () => { allowed = false } }
}

test('cancel leaves records and selection untouched', async () => {
  const state = setup({ confirm: async () => { throw 'cancel' } })
  state.setSelection([{ id: 1, code: '机柜1' }])
  await state.deleteSelected()
  assert.equal(state.calls.length, 0)
  assert.equal(state.selectedRows.value.length, 1)
  assert.equal(state.deleting.value, false)
})

test('confirmation freezes selected IDs and prevents duplicate submissions', async () => {
  let confirm
  const state = setup({ confirm: () => new Promise(resolve => { confirm = resolve }) })
  state.setSelection([{ id: 1 }, { id: 2 }])
  const deleting = state.deleteSelected()
  assert.equal(state.deleting.value, true)
  state.setSelection([{ id: 3 }])
  await state.deleteSelected()
  assert.equal(state.calls.length, 0)
  confirm()
  await deleting
  assert.deepEqual(state.calls, [['/racks/batch-delete', { ids: [1, 2] }]])
  assert.deepEqual(state.deleted, [[1, 2]])
  assert.equal(state.selectedRows.value.length, 0)
  assert.equal(state.cleared, 1)
  assert.equal(state.reloads, 1)
})

test('a server failure refreshes results without retrying deletion or reporting success', async () => {
  const state = setup({ post: async () => { throw { response: { data: { detail: '部分机柜已不存在，未执行删除' } } } } })
  state.setSelection([{ id: 1 }])
  await state.deleteSelected()
  assert.equal(state.calls.length, 1)
  assert.equal(state.deleted.length, 0)
  assert.deepEqual(state.messages, ['部分机柜已不存在，未执行删除'])
  assert.equal(state.reloads, 1)
  assert.equal(state.deleting.value, false)
})

test('clearing selection on reload and disabling permission both prevent deletion', async () => {
  const state = setup()
  state.setSelection([{ id: 1 }])
  state.clearSelection()
  await state.deleteSelected()
  state.setSelection([{ id: 2 }])
  state.block()
  await state.deleteSelected()
  assert.equal(state.calls.length, 0)
})
