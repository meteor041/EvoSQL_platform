<script setup>
import * as echarts from 'echarts'
import { computed, defineComponent, h, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'

const icons = {
  workbench: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  result: '<path d="M4 6h16M4 12h16M4 18h10"/>',
  sql: '<path d="M4 6c0-1.1 3.6-2 8-2s8 .9 8 2-3.6 2-8 2-8-.9-8-2z"/><path d="M4 6v6c0 1.1 3.6 2 8 2s8-.9 8-2V6"/><path d="M4 12v6c0 1.1 3.6 2 8 2s8-.9 8-2v-6"/>',
  trace: '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 6h8M6 8v8a2 2 0 0 0 2 2h8"/>',
  audit: '<path d="M9 12l2 2 4-4"/><path d="M12 3l8 4v6c0 4.4-3.4 7.6-8 8-4.6-.4-8-3.6-8-8V7l8-4z"/>',
  shield: '<path d="M12 3l8 4v6c0 4.4-3.4 7.6-8 8-4.6-.4-8-3.6-8-8V7l8-4z"/>',
  play: '<polygon points="6 4 20 12 6 20 6 4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="1.5"/><path d="M3 10h18M9 4v16"/>',
  filter: '<path d="M3 5h18M6 12h12M10 19h4"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  key: '<circle cx="7.5" cy="14.5" r="3.5"/><path d="M10 12l8-8M15 7l2 2M13 9l2 2"/>',
  star: '<path d="M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 16.9 6.6 19.8l1-6.1-4.4-4.3 6.1-.9L12 3z"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  warn: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9l-8 13.4A2 2 0 0 0 4 20.4h16a2 2 0 0 0 1.7-3.1L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.3 17l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7 4.3l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1A2 2 0 1 1 19.7 7l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  empty: '<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/>'
}

const IconSymbol = defineComponent({
  props: {
    name: { type: String, required: true },
    size: { type: Number, default: 16 }
  },
  setup(props) {
    return () =>
      h('svg', {
        class: 'icon-svg',
        width: props.size,
        height: props.size,
        viewBox: '0 0 24 24',
        fill: props.name === 'play' ? 'currentColor' : 'none',
        stroke: props.name === 'play' ? 'none' : 'currentColor',
        'stroke-width': 1.7,
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        innerHTML: icons[props.name] || icons.workbench
      })
  }
})

const chartEl = ref(null)
let chart = null
let chartHost = null
let resizeHandler = null
let llmNoticeTimer = null

const emptyLlmForm = () => ({
  displayName: '',
  provider: 'openrouter',
  model: '',
  baseUrl: 'https://openrouter.ai/api/v1/chat/completions',
  apiKey: '',
  temperature: 0.4,
  timeoutSeconds: 45,
  maxRetries: 2,
  scope: 'campus',
  notes: ''
})

const state = reactive({
  activeView: 'workbench',
  sessionId: 'S-2026-0508-A',
  domain: 'campus',
  llmMode: 'auto',
  question: '统计各学院当前学生人数',
  taskId: '',
  result: null,
  clarificationOptions: [],
  clarificationQuestion: '',
  auditLogs: [],
  auditTotal: 0,
  auditLimit: 12,
  auditOffset: 0,
  auditFilters: {
    domain: '',
    llmMode: '',
    status: '',
    resultSource: '',
    query: ''
  },
  loading: false,
  auditLoading: false,
  error: '',
  copiedSql: false,
  expandedCandidates: {},
  llmConfigs: [
    {
      id: 'mock-campus',
      displayName: '校园演示 Mock',
      provider: 'mock',
      model: 'campus-reference-qa',
      baseUrl: 'local://campus_qa',
      apiKeyMasked: 'not required',
      temperature: 0,
      timeoutSeconds: 2,
      maxRetries: 0,
      scope: 'campus',
      enabled: true,
      isDefault: true,
      notes: 'local reference set'
    },
    {
      id: 'openrouter-qwen',
      displayName: 'OpenRouter Qwen',
      provider: 'openrouter',
      model: 'qwen/qwen3.6-plus:free',
      baseUrl: 'https://openrouter.ai/api/v1/chat/completions',
      apiKeyMasked: 'env:OPENROUTER_API_KEY',
      temperature: 0.4,
      timeoutSeconds: 45,
      maxRetries: 2,
      scope: 'campus',
      enabled: false,
      isDefault: false,
      notes: 'qwen_openrouter'
    }
  ],
  llmForm: emptyLlmForm(),
  llmFormError: '',
  llmSavedNotice: ''
})

const exampleQuestions = [
  '统计各学院当前学生人数',
  '各专业平均成绩排名',
  '本月科研项目经费趋势',
  '近一年课程挂科率分布',
  '论文数量最高的教师 Top 5',
  '本学期选课人数最多的课程',
  '各学院师生比对比'
]

const navItems = [
  { id: 'workbench', label: '问数工作台', icon: 'workbench' },
  { id: 'result', label: '查询结果', icon: 'result' },
  { id: 'sql', label: 'SQL 证据', icon: 'sql' },
  { id: 'trace', label: '推理链路', icon: 'trace' },
  { id: 'safety', label: '安全检查', icon: 'shield' },
  { id: 'audit', label: '审计日志', icon: 'audit' }
]

const llmProviderOptions = [
  { value: 'openrouter', label: 'OpenRouter', defaultBaseUrl: 'https://openrouter.ai/api/v1/chat/completions' },
  { value: 'dashscope', label: 'DashScope', defaultBaseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions' },
  { value: 'openai-compatible', label: 'OpenAI Compatible', defaultBaseUrl: '' },
  { value: 'local', label: 'Local Endpoint', defaultBaseUrl: 'http://127.0.0.1:11434/v1/chat/completions' },
  { value: 'mock', label: 'Mock', defaultBaseUrl: 'local://campus_qa' }
]

const currentResultStatus = computed(() => state.result?.status || 'idle')
const resultRows = computed(() => state.result?.result_rows || [])
const resultColumns = computed(() => {
  if (!resultRows.value.length) return []
  return Object.keys(resultRows.value[0])
})
const chartSpec = computed(() => state.result?.chart_spec || {})
const activeCandidateRecords = computed(() => state.result?.candidate_records || [])
const attemptedCandidateRecords = computed(() => state.result?.attempted_candidate_records || [])
const hasSeparateAttemptChain = computed(() => state.result?.fallback_applied && attemptedCandidateRecords.value.length > 0)
const traceSteps = computed(() => normalizeTraceSteps(state.result?.trace_steps || []))
const safetyItems = computed(() => normalizeSafetyChecks(state.result?.safety_checks || []))
const safetyPassCount = computed(() => safetyItems.value.filter((item) => item.state === 'pass').length)
const auditPage = computed(() => Math.floor(state.auditOffset / state.auditLimit) + 1)
const auditPageCount = computed(() => Math.max(1, Math.ceil(state.auditTotal / state.auditLimit)))
const auditRangeText = computed(() => {
  if (!state.auditTotal) return '0 条记录'
  const start = state.auditOffset + 1
  const end = Math.min(state.auditOffset + state.auditLogs.length, state.auditTotal)
  return `${start}-${end} / ${state.auditTotal}`
})
const statusLabel = computed(() => {
  if (state.loading) return 'running'
  return currentResultStatus.value
})
const resultKpis = computed(() => [
  { label: '返回行数', value: String(resultRows.value.length), note: state.result ? 'rows' : '未执行' },
  { label: '命中表', value: String(state.result?.used_tables?.length || 0), note: 'schema linking' },
  { label: '候选 SQL', value: String(activeCandidateRecords.value.length + attemptedCandidateRecords.value.length), note: 'candidate chain' },
  { label: '安全通过', value: `${safetyPassCount.value}/${safetyItems.value.length || 0}`, note: 'safety guard' }
])
const hasChart = computed(() => {
  const type = chartSpec.value?.type
  return Boolean(type && type !== 'table' && resultRows.value.length)
})
const schemaLinking = computed(() => chartSpec.value?.schema_linking || null)
const highlightedFinalSql = computed(() => highlightSql(state.result?.final_sql || ''))
const enabledLlmCount = computed(() => state.llmConfigs.filter((item) => item.enabled).length)
const defaultLlm = computed(() => state.llmConfigs.find((item) => item.isDefault) || state.llmConfigs[0] || null)
const llmKpis = computed(() => [
  { label: '已配置', value: String(state.llmConfigs.length), note: 'providers' },
  { label: '已启用', value: String(enabledLlmCount.value), note: 'routing' },
  { label: '默认模型', value: defaultLlm.value?.displayName || 'n/a', note: defaultLlm.value?.provider || 'n/a' },
  { label: '作用域', value: String(new Set(state.llmConfigs.map((item) => item.scope)).size), note: 'domains' }
])

function domainLabel(value) {
  const labels = { campus: '校园综合库', bird: 'BIRD 数据集' }
  return labels[value] || value || 'n/a'
}

function modeLabel(value) {
  const labels = { auto: 'auto', qwen: 'qwen', mock: 'mock' }
  return labels[value] || value || 'n/a'
}

function providerLabel(value) {
  return llmProviderOptions.find((item) => item.value === value)?.label || value || 'n/a'
}

function maskSecret(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'not set'
  if (raw.length <= 8) return '••••'
  return `${raw.slice(0, 4)}••••${raw.slice(-4)}`
}

function applyProviderDefaults() {
  const provider = llmProviderOptions.find((item) => item.value === state.llmForm.provider)
  if (provider && (!state.llmForm.baseUrl || state.llmForm.baseUrl.startsWith('http') || state.llmForm.baseUrl.startsWith('local://'))) {
    state.llmForm.baseUrl = provider.defaultBaseUrl
  }
  if (state.llmForm.provider === 'mock') {
    state.llmForm.model = state.llmForm.model || 'campus-reference-qa'
    state.llmForm.apiKey = ''
    state.llmForm.temperature = 0
    state.llmForm.timeoutSeconds = 2
    state.llmForm.maxRetries = 0
  }
}

function resetLlmForm() {
  state.llmForm = emptyLlmForm()
  state.llmFormError = ''
}

function showLlmNotice(message) {
  state.llmSavedNotice = message
  if (llmNoticeTimer) clearTimeout(llmNoticeTimer)
  llmNoticeTimer = setTimeout(() => {
    state.llmSavedNotice = ''
  }, 1800)
}

function addLlmConfig() {
  state.llmFormError = ''
  const displayName = state.llmForm.displayName.trim()
  const model = state.llmForm.model.trim()
  const baseUrl = state.llmForm.baseUrl.trim()
  if (!displayName || !model) {
    state.llmFormError = '配置名称和模型 ID 不能为空。'
    return
  }
  if (state.llmForm.provider !== 'mock' && !baseUrl) {
    state.llmFormError = 'Base URL 不能为空。'
    return
  }
  const config = {
    id: `llm-${Date.now()}`,
    displayName,
    provider: state.llmForm.provider,
    model,
    baseUrl,
    apiKeyMasked: maskSecret(state.llmForm.apiKey),
    temperature: Number(state.llmForm.temperature),
    timeoutSeconds: Number(state.llmForm.timeoutSeconds),
    maxRetries: Number(state.llmForm.maxRetries),
    scope: state.llmForm.scope,
    enabled: true,
    isDefault: state.llmConfigs.length === 0,
    notes: state.llmForm.notes.trim()
  }
  state.llmConfigs.unshift(config)
  resetLlmForm()
  showLlmNotice('LLM 配置已新增。')
}

function setDefaultLlm(id) {
  state.llmConfigs.forEach((item) => {
    item.isDefault = item.id === id
    if (item.id === id) item.enabled = true
  })
  showLlmNotice('默认模型已更新。')
}

function toggleLlm(id) {
  const item = state.llmConfigs.find((config) => config.id === id)
  if (!item) return
  item.enabled = !item.enabled
  if (!item.enabled && item.isDefault) {
    item.isDefault = false
    const nextDefault = state.llmConfigs.find((config) => config.enabled)
    if (nextDefault) nextDefault.isDefault = true
  }
}

function removeLlm(id) {
  const removed = state.llmConfigs.find((item) => item.id === id)
  state.llmConfigs = state.llmConfigs.filter((item) => item.id !== id)
  if (removed?.isDefault) {
    const nextDefault = state.llmConfigs.find((item) => item.enabled) || state.llmConfigs[0]
    if (nextDefault) {
      nextDefault.isDefault = true
      nextDefault.enabled = true
    }
  }
}

function candidateStatusLabel(status) {
  const labels = {
    generated: 'generated',
    executed: 'executed',
    selected: 'selected',
    selected_blocked: 'selected blocked',
    blocked: 'blocked',
    failed: 'failed',
    execution_warning: 'warning',
    real_executed: 'real executed',
    real_selected: 'real selected',
    real_blocked: 'real blocked',
    real_failed: 'real failed',
    reference_executed: 'reference executed',
    reference_selected: 'reference selected'
  }
  return labels[status] || status || 'unknown'
}

function candidateStatusClass(status) {
  if (!status) return 'pending'
  if (status.includes('selected')) return 'selected'
  if (status.includes('blocked')) return 'blocked'
  if (status.includes('failed')) return 'failed'
  if (status.includes('executed')) return 'executed'
  if (status.includes('warning')) return 'fallback'
  return 'pending'
}

function resultStatusClass(status) {
  if (!status || status === 'idle') return 'pending'
  if (status === 'completed' || status === 'success') return 'success'
  if (status === 'blocked') return 'blocked'
  if (status === 'failed') return 'failed'
  if (status === 'clarification_required') return 'fallback'
  return 'info'
}

function normalizeTraceSteps(steps) {
  return steps.map((step, index) => {
    const strategy = step.strategy || step.title || `Step ${index + 1}`
    const summary = step.summary || step.detail || step.message || JSON.stringify(step)
    const stateValue = `${strategy} ${summary}`.toLowerCase()
    const stateName = stateValue.includes('fail') || stateValue.includes('error')
      ? 'fail'
      : stateValue.includes('warn') || stateValue.includes('blocked')
        ? 'warn'
        : 'done'
    return {
      key: `${index}-${strategy}`,
      title: strategy,
      detail: summary,
      iteration: step.iteration ?? index + 1,
      time: step.elapsed_ms ? `${step.elapsed_ms} ms` : '',
      state: stateName
    }
  })
}

function normalizeSafetyChecks(items) {
  return items.map((item, index) => {
    if (typeof item === 'string') {
      return { key: `${index}-${item}`, name: item, note: '已记录安全检查项', state: 'pass' }
    }
    const status = `${item.status || item.state || item.result || ''}`.toLowerCase()
    const stateName = status.includes('fail') || status.includes('block')
      ? 'fail'
      : status.includes('warn')
        ? 'warn'
        : 'pass'
    return {
      key: `${index}-${item.name || item.check || item.type || 'safety'}`,
      name: item.name || item.check || item.type || `安全检查 ${index + 1}`,
      note: item.note || item.message || item.reason || item.detail || JSON.stringify(item),
      state: stateName
    }
  })
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function highlightSql(sql) {
  const escaped = escapeHtml(sql || 'No SQL yet')
  return escaped
    .replace(/(--[^\n]*)/g, '<span class="tok-comment">$1</span>')
    .replace(/('[^']*')/g, '<span class="tok-str">$1</span>')
    .replace(/\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|LIMIT|AND|OR|AS|FILTER|COUNT|DISTINCT|DESC|ASC|INNER|LEFT|RIGHT|HAVING|CASE|WHEN|THEN|ELSE|END|WITH|UNION)\b/g, '<span class="tok-kw">$1</span>')
    .replace(/\b(\d+)\b/g, '<span class="tok-num">$1</span>')
}

async function readJsonResponse(res, fallbackMessage) {
  const text = await res.text()
  if (!text) {
    throw new Error(`${fallbackMessage}: empty response. 请确认后端服务已启动，且 Vite 代理端口指向 FastAPI。`)
  }
  try {
    return JSON.parse(text)
  } catch (error) {
    const preview = text.slice(0, 160).replace(/\s+/g, ' ')
    throw new Error(`${fallbackMessage}: non-JSON response (${res.status}). ${preview}`)
  }
}

function cellValue(row, column) {
  const value = row[column]
  if (value === null || value === undefined) return ''
  return value
}

function isNumericCell(row, column) {
  const value = row[column]
  return typeof value === 'number' || (typeof value === 'string' && value.trim() !== '' && !Number.isNaN(Number(value)))
}

function candidateKey(candidate, index, prefix) {
  return `${prefix}-${index}-${candidate.iteration || 'i'}-${candidate.rank || 'r'}-${candidate.sql || ''}`
}

function toggleCandidate(key) {
  state.expandedCandidates[key] = !state.expandedCandidates[key]
}

async function runQuery(question = state.question) {
  state.loading = true
  state.error = ''
  state.question = question
  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: state.sessionId,
        question: state.question,
        domain: state.domain,
        llm_mode: state.llmMode,
        user_id: 'demo-user',
        role: 'admin'
      })
    })
    const data = await readJsonResponse(res, 'Query failed')
    if (!res.ok) throw new Error(data.detail || 'Query failed')
    state.taskId = data.task_id
    state.clarificationQuestion = data.clarification_question || ''
    state.clarificationOptions = data.clarification_options || []
    await Promise.all([loadResult(), loadAuditLogs()])
  } catch (error) {
    state.error = error.message || String(error)
  } finally {
    state.loading = false
  }
}

async function loadResult() {
  if (!state.taskId) return
  const res = await fetch(`/api/query/${state.taskId}`)
  const data = await readJsonResponse(res, 'Load result failed')
  if (!res.ok) throw new Error(data.detail || 'Load result failed')
  state.result = data
}

async function followup(answer) {
  state.loading = true
  state.error = ''
  try {
    const res = await fetch(`/api/query/${state.taskId}/followup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer })
    })
    const data = await readJsonResponse(res, 'Follow-up failed')
    if (!res.ok) throw new Error(data.detail || 'Follow-up failed')
    state.taskId = data.task_id
    state.clarificationQuestion = ''
    state.clarificationOptions = []
    await Promise.all([loadResult(), loadAuditLogs()])
  } catch (error) {
    state.error = error.message || String(error)
  } finally {
    state.loading = false
  }
}

async function loadAuditLogs() {
  state.auditLoading = true
  try {
    const params = new URLSearchParams({
      limit: String(state.auditLimit),
      offset: String(state.auditOffset)
    })
    if (state.auditFilters.domain) params.set('domain', state.auditFilters.domain)
    if (state.auditFilters.llmMode) params.set('llm_mode', state.auditFilters.llmMode)
    if (state.auditFilters.status) params.set('status', state.auditFilters.status)
    if (state.auditFilters.resultSource) params.set('result_source', state.auditFilters.resultSource)
    if (state.auditFilters.query) params.set('query', state.auditFilters.query)

    const res = await fetch(`/api/audit/logs?${params.toString()}`)
    const data = await readJsonResponse(res, 'Load audit logs failed')
    if (!res.ok) throw new Error(data.detail || 'Load audit logs failed')
    state.auditLogs = data.items || []
    state.auditTotal = data.total || 0
  } catch (error) {
    state.error = error.message || String(error)
  } finally {
    state.auditLoading = false
  }
}

async function reloadAuditLogs() {
  state.error = ''
  try {
    const reloadRes = await fetch('/api/audit/reload', { method: 'POST' })
    const reloadData = await readJsonResponse(reloadRes, 'Reload audit logs failed')
    if (!reloadRes.ok) throw new Error(reloadData.detail || 'Reload audit logs failed')
    state.auditOffset = 0
    await loadAuditLogs()
  } catch (error) {
    state.error = error.message || String(error)
  }
}

function applyAuditFilters() {
  state.auditOffset = 0
  loadAuditLogs()
}

function goAuditPage(page) {
  const nextPage = Math.min(Math.max(page, 1), auditPageCount.value)
  state.auditOffset = (nextPage - 1) * state.auditLimit
  loadAuditLogs()
}

function clearQuestion() {
  state.question = ''
}

function copySql() {
  const sql = state.result?.final_sql || ''
  if (!sql) return
  navigator.clipboard?.writeText(sql)
  state.copiedSql = true
  setTimeout(() => {
    state.copiedSql = false
  }, 1500)
}

function disposeChart() {
  if (chart) {
    chart.dispose()
    chart = null
  }
  chartHost = null
}

function inferChartKeys() {
  const firstRow = resultRows.value[0] || {}
  const columns = resultColumns.value
  const xKey = chartSpec.value.x || columns.find((column) => !isNumericCell(firstRow, column)) || columns[0]
  const yKey = chartSpec.value.y || columns.find((column) => isNumericCell(firstRow, column) && column !== xKey) || columns[1]
  return { xKey, yKey }
}

function renderChart() {
  if (!hasChart.value || !chartEl.value) {
    disposeChart()
    return
  }
  const rows = resultRows.value
  const spec = chartSpec.value
  const type = spec.type || 'bar'
  const { xKey, yKey } = inferChartKeys()
  if (chartHost !== chartEl.value) {
    disposeChart()
    chartHost = chartEl.value
  }
  chart = chart || echarts.init(chartEl.value)

  const baseOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: type === 'pie' ? 'item' : 'axis',
      backgroundColor: '#0F172A',
      borderColor: '#0F172A',
      textStyle: { color: '#E2E8F0', fontSize: 12 }
    },
    color: ['#2563EB', '#0891B2', '#16A34A', '#D97706']
  }

  const option = type === 'pie'
    ? {
        ...baseOption,
        series: [{
          type: 'pie',
          radius: ['42%', '72%'],
          data: rows.map((row) => ({ name: row[xKey], value: Number(row[yKey]) || 0 })),
          label: { color: '#475569' }
        }]
      }
    : {
        ...baseOption,
        grid: { left: 48, right: 18, top: 28, bottom: 48, containLabel: true },
        xAxis: {
          type: 'category',
          data: rows.map((row) => row[xKey]),
          axisLine: { lineStyle: { color: '#E5E8EE' } },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 11, interval: 0, rotate: rows.length > 6 ? 28 : 0 }
        },
        yAxis: {
          type: 'value',
          axisLine: { show: false },
          axisLabel: { color: '#94A3B8', fontSize: 11 },
          splitLine: { lineStyle: { color: '#F1F4F8', type: 'dashed' } }
        },
        series: [{
          type,
          data: rows.map((row) => Number(row[yKey]) || 0),
          smooth: type === 'line',
          barWidth: type === 'bar' ? 22 : undefined,
          itemStyle: {
            borderRadius: type === 'bar' ? [4, 4, 0, 0] : 0,
            color: type === 'bar'
              ? {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 0,
                  y2: 1,
                  colorStops: [
                    { offset: 0, color: '#3B82F6' },
                    { offset: 1, color: '#0891B2' }
                  ]
                }
              : '#2563EB'
          },
          areaStyle: type === 'line' ? { color: 'rgba(37,99,235,0.12)' } : undefined
        }]
      }
  chart.setOption(option, true)
}

watch(
  () => [state.result, state.activeView],
  async () => {
    await nextTick()
    renderChart()
  },
  { deep: true }
)

resizeHandler = () => {
  if (chart) chart.resize()
}
window.addEventListener('resize', resizeHandler)

onBeforeUnmount(() => {
  disposeChart()
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

loadAuditLogs()
</script>

<template>
  <div class="shell">
    <header class="header shell-header">
      <div class="header-brand">
        <div class="brand-mark">EQ</div>
        <div>
          <div class="brand-title">校园智慧问数平台</div>
          <div class="brand-sub">Natural Language -&gt; Safe SQL</div>
        </div>
      </div>
      <div class="header-meta">
        <span class="meta-pill"><span class="label">Domain</span><span class="val">{{ domainLabel(state.domain) }}</span></span>
        <span class="meta-pill"><span class="label">LLM</span><span class="val">{{ modeLabel(state.llmMode) }}</span></span>
        <span class="meta-pill"><span class="dot"></span><span class="val">{{ statusLabel }}</span></span>
        <div class="header-user">
          <div class="avatar">管</div>
          <div class="user-meta">
            <div class="user-name">校园管理员</div>
            <div class="user-role">教务处 · 数据管理</div>
          </div>
        </div>
      </div>
    </header>

    <aside class="shell-sidebar">
      <nav class="sidebar">
        <div class="nav-group-label">主导航</div>
        <button
          v-for="item in navItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: state.activeView === item.id }"
          @click="state.activeView = item.id"
        >
          <span class="icon"><IconSymbol :name="item.icon" /></span>
          <span>{{ item.label }}</span>
          <span v-if="item.id === 'audit'" class="count">{{ state.auditTotal }}</span>
        </button>

        <div class="nav-group-label nav-system-label">系统</div>
        <button
          class="nav-item"
          type="button"
          :class="{ active: state.activeView === 'settings' }"
          @click="state.activeView = 'settings'"
        >
          <span class="icon"><IconSymbol name="cog" /></span>
          <span>模型设置</span>
          <span class="count">{{ state.llmConfigs.length }}</span>
        </button>
        <button class="nav-item" type="button">
          <span class="icon"><IconSymbol name="shield" /></span>
          <span>安全策略</span>
        </button>

        <div class="sidebar-footer">
          <div class="row"><span>Frontend</span><span class="v">Vite + Vue</span></div>
          <div class="row"><span>SQL Guard</span><span class="v">SELECT only</span></div>
          <div class="row"><span>Workspace</span><span class="v">Campus</span></div>
        </div>
      </nav>
    </aside>

    <main class="shell-main">
      <div class="page">
        <template v-if="state.activeView === 'workbench'">
          <div class="page-head">
            <div>
              <div class="page-title">问数工作台</div>
              <div class="page-sub">面向校园管理人员的自然语言问数、SQL 证据与审计工作台</div>
            </div>
            <div class="page-actions">
              <button class="btn" type="button" @click="reloadAuditLogs"><IconSymbol name="refresh" />刷新审计</button>
              <button class="btn" type="button" @click="state.activeView = 'settings'"><IconSymbol name="cog" />模型设置</button>
            </div>
          </div>

          <div class="stack">
            <div class="composer">
              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">发起问数</div>
                  <div class="panel-sub">POST /api/query</div>
                  <div class="panel-actions">
                    <span class="chip info"><span class="dot"></span>session active</span>
                  </div>
                </header>
                <div class="panel-body flush">
                  <div class="composer-meta">
                    <div class="meta-field">
                      <label class="field-label">Session</label>
                      <input v-model="state.sessionId" class="input" />
                    </div>
                    <div class="meta-field">
                      <label class="field-label">Domain</label>
                      <select v-model="state.domain" class="select">
                        <option value="campus">校园综合库</option>
                        <option value="bird">BIRD 数据集</option>
                      </select>
                    </div>
                    <div class="meta-field">
                      <label class="field-label">LLM Mode</label>
                      <select v-model="state.llmMode" class="select">
                        <option value="auto">auto</option>
                        <option value="qwen">qwen</option>
                        <option value="mock">mock</option>
                      </select>
                    </div>
                    <div class="meta-field">
                      <label class="field-label">权限角色</label>
                      <input class="input" value="admin" disabled />
                    </div>
                  </div>
                  <div class="composer-input">
                    <label class="field-label">自然语言问题</label>
                    <textarea
                      v-model="state.question"
                      class="textarea"
                      rows="4"
                      placeholder="例如：统计各学院当前学生人数"
                      @keydown.ctrl.enter.prevent="runQuery()"
                    ></textarea>
                  </div>
                  <div class="composer-bar">
                    <div class="composer-hints">
                      <span><span class="kbd">Ctrl</span> + <span class="kbd">Enter</span> 运行</span>
                      <span>建议字数 <= 80</span>
                    </div>
                    <button class="btn" type="button" @click="clearQuestion">清空</button>
                    <button class="btn primary" type="button" :disabled="state.loading || !state.question.trim()" @click="runQuery()">
                      <span v-if="state.loading" class="spinner"></span>
                      <IconSymbol v-else name="play" />
                      {{ state.loading ? '运行中...' : '运行查询' }}
                    </button>
                  </div>
                </div>
              </section>

              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">常用查询</div>
                  <div class="panel-sub">校园管理快捷入口</div>
                </header>
                <div class="panel-body flush">
                  <div class="demo-list">
                    <button v-for="(item, index) in exampleQuestions" :key="item" class="demo-item" type="button" @click="runQuery(item)">
                      <span class="num">{{ String(index + 1).padStart(2, '0') }}</span>
                      <span class="demo-text">{{ item }}</span>
                      <span class="arrow"><IconSymbol name="arrow" :size="14" /></span>
                    </button>
                  </div>
                </div>
              </section>
            </div>

            <div v-if="state.error" class="inline-error">
              <IconSymbol name="warn" :size="14" />
              <div><strong>操作失败</strong> · {{ state.error }}</div>
            </div>

            <section v-if="state.clarificationQuestion" class="panel">
              <header class="panel-head">
                <div class="panel-title">澄清追问</div>
                <div class="panel-sub">clarification required</div>
                <div class="panel-actions">
                  <span class="chip fallback"><span class="dot"></span>waiting</span>
                </div>
              </header>
              <div class="panel-body">
                <div class="clarify-question">{{ state.clarificationQuestion }}</div>
                <div class="clarify-actions">
                  <button v-for="item in state.clarificationOptions" :key="item" class="btn" type="button" @click="followup(item)">
                    {{ item }}
                  </button>
                </div>
              </div>
            </section>

            <div class="overview-grid">
              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">结果摘要</div>
                  <div class="panel-sub">{{ state.taskId || 'no task' }}</div>
                  <div class="panel-actions">
                    <span class="chip" :class="resultStatusClass(currentResultStatus)"><span class="dot"></span>{{ currentResultStatus }}</span>
                  </div>
                </header>
                <div class="panel-body">
                  <div class="summary-text">{{ state.result?.summary_text || '尚未执行查询。输入校园管理问题后，系统将在这里展示摘要、证据和数据表。' }}</div>
                  <div v-if="state.result?.fallback_reason" class="fallback-note">Fallback reason: {{ state.result.fallback_reason }}</div>
                  <div class="kpi-row">
                    <div v-for="item in resultKpis" :key="item.label" class="kpi">
                      <div class="kpi-label">{{ item.label }}</div>
                      <div class="kpi-value">{{ item.value }}</div>
                      <div class="kpi-delta flat">{{ item.note }}</div>
                    </div>
                  </div>
                </div>
              </section>

              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">数据来源</div>
                  <div class="panel-sub">schema linking</div>
                </header>
                <div class="panel-body">
                  <div class="sources-row">
                    <div class="sources-label">使用表</div>
                    <div class="sources-tags">
                      <span v-for="table in state.result?.used_tables || []" :key="table" class="tbl-tag">{{ table }}</span>
                      <span v-if="!state.result?.used_tables?.length" class="muted">暂无命中表</span>
                    </div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">结果来源</div>
                    <div class="source-line">{{ state.result?.result_source || 'n/a' }}</div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">执行模式</div>
                    <div class="source-line">{{ state.result?.execution_mode || 'n/a' }}</div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">命中字段</div>
                    <div class="sources-tags">
                      <span v-for="column in state.result?.used_columns || []" :key="column" class="tbl-tag">{{ column }}</span>
                      <span v-if="!state.result?.used_columns?.length" class="muted">暂无字段信息</span>
                    </div>
                  </div>
                </div>
              </section>
            </div>

            <div class="row-3-2">
              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">结果图表</div>
                  <div class="panel-sub">{{ chartSpec.type || 'auto' }}</div>
                </header>
                <div class="panel-body flush">
                  <div v-show="hasChart" ref="chartEl" class="chart-container"></div>
                  <div v-if="!hasChart" class="empty compact">
                    <div class="empty-icon"><IconSymbol name="empty" :size="28" /></div>
                    <div class="empty-title">暂无可视化图表</div>
                    <div class="empty-sub">返回结果包含图表配置时会自动渲染</div>
                  </div>
                </div>
              </section>

              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">Schema Linking</div>
                  <div class="panel-sub">字段映射</div>
                </header>
                <div class="panel-body">
                  <div v-if="schemaLinking" class="schema-summary">
                    <div class="sources-row">
                      <div class="sources-label">selected</div>
                      <div class="sources-tags">
                        <span v-for="table in schemaLinking.selected_tables || []" :key="table" class="tbl-tag">{{ table }}</span>
                      </div>
                    </div>
                    <div v-if="schemaLinking.heuristic_tables?.length" class="sources-row">
                      <div class="sources-label">heuristic</div>
                      <div class="sources-tags">
                        <span v-for="table in schemaLinking.heuristic_tables" :key="table" class="tbl-tag">{{ table }}</span>
                      </div>
                    </div>
                    <div v-if="schemaLinking.reasoning" class="schema-reasoning">{{ schemaLinking.reasoning }}</div>
                  </div>
                  <div v-else class="empty compact">
                    <div class="empty-icon"><IconSymbol name="table" :size="24" /></div>
                    <div class="empty-title">暂无 Schema Linking 信息</div>
                  </div>
                </div>
              </section>
            </div>

            <section class="panel">
              <header class="panel-head">
                <div class="panel-title">结果数据</div>
                <div class="panel-sub">{{ resultRows.length }} 行 · {{ resultColumns.length }} 列</div>
              </header>
              <div class="panel-body flush">
                <div v-if="resultRows.length" class="dtable-wrap">
                  <table class="dtable">
                    <thead>
                      <tr>
                        <th v-for="column in resultColumns" :key="column" :class="{ num: isNumericCell(resultRows[0], column) }">{{ column }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, rowIndex) in resultRows" :key="rowIndex">
                        <td v-for="column in resultColumns" :key="column" :class="{ num: isNumericCell(row, column), muted: column.toLowerCase().includes('id') }">
                          {{ cellValue(row, column) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="empty">
                  <div class="empty-icon"><IconSymbol name="empty" :size="28" /></div>
                  <div class="empty-title">暂无结果数据</div>
                  <div class="empty-sub">运行查询后将在这里展示明细表格</div>
                </div>
                <div class="dtable-foot">
                  <span>{{ resultRows.length }} rows</span>
                  <span class="foot-right">task {{ state.taskId || 'n/a' }}</span>
                </div>
              </div>
            </section>

            <section class="panel">
              <header class="panel-head">
                <div class="panel-title">SQL 证据 · 最终选用</div>
                <div class="panel-sub">final.sql</div>
                <div class="panel-actions">
                  <span class="chip selected"><span class="dot"></span>{{ state.result?.result_source || 'n/a' }}</span>
                  <button class="btn sm" type="button" @click="copySql"><IconSymbol name="copy" :size="14" />{{ state.copiedSql ? '已复制' : '复制' }}</button>
                </div>
              </header>
              <div class="panel-body">
                <div class="code">
                  <div class="code-head">
                    <span class="dot"></span><span class="dot dim"></span><span class="dot muted-dot"></span>
                    <span class="code-title">final.sql · SQLite Sandbox</span>
                    <span class="code-meta">{{ state.result?.status || 'idle' }}</span>
                  </div>
                  <div class="code-body">
                    <pre v-html="highlightedFinalSql"></pre>
                  </div>
                </div>
              </div>
            </section>

            <section v-if="hasSeparateAttemptChain" class="panel">
              <header class="panel-head">
                <div class="panel-title">Real Model Candidates Before Fallback</div>
                <div class="panel-sub">{{ attemptedCandidateRecords.length }} candidates</div>
              </header>
              <div class="panel-body">
                <div class="cand-list">
                  <article
                    v-for="(candidate, index) in attemptedCandidateRecords"
                    :key="candidateKey(candidate, index, 'attempt')"
                    class="cand"
                    :class="candidateStatusClass(candidate.status)"
                  >
                    <div class="cand-head">
                      <div class="cand-rank">#{{ candidate.rank || index + 1 }} · iter {{ candidate.iteration || '-' }}</div>
                      <div class="cand-title">{{ candidateStatusLabel(candidate.status) }}</div>
                      <div class="cand-meta">
                        <span class="cand-score">score {{ candidate.score ?? 'n/a' }}</span>
                        <span class="chip" :class="candidateStatusClass(candidate.status)"><span class="dot"></span>{{ candidateStatusLabel(candidate.status) }}</span>
                      </div>
                    </div>
                    <div class="cand-body">
                      <pre class="cand-preview" :class="{ expanded: state.expandedCandidates[candidateKey(candidate, index, 'attempt')] }">{{ candidate.sql }}</pre>
                      <div class="cand-kv">tables={{ (candidate.referenced_tables || []).join(', ') || 'n/a' }}</div>
                      <div class="cand-kv">columns={{ (candidate.referenced_columns || []).join(', ') || 'n/a' }}</div>
                      <div v-if="candidate.error" class="cand-error">{{ candidate.error }}</div>
                      <button class="btn sm cand-toggle" type="button" @click="toggleCandidate(candidateKey(candidate, index, 'attempt'))">
                        {{ state.expandedCandidates[candidateKey(candidate, index, 'attempt')] ? '收起 SQL' : '展开 SQL' }}
                      </button>
                    </div>
                  </article>
                </div>
              </div>
            </section>

            <section class="panel">
              <header class="panel-head">
                <div class="panel-title">候选 SQL 链路</div>
                <div class="panel-sub">{{ activeCandidateRecords.length }} candidates</div>
                <div class="panel-actions">
                  <span class="chip info"><span class="dot"></span>{{ state.result?.fallback_applied ? 'fallback chain' : 'active chain' }}</span>
                </div>
              </header>
              <div class="panel-body">
                <div v-if="activeCandidateRecords.length" class="cand-list">
                  <article
                    v-for="(candidate, index) in activeCandidateRecords"
                    :key="candidateKey(candidate, index, 'active')"
                    class="cand"
                    :class="candidateStatusClass(candidate.status)"
                  >
                    <div class="cand-head">
                      <div class="cand-rank">#{{ candidate.rank || index + 1 }} · iter {{ candidate.iteration || '-' }}</div>
                      <div class="cand-title">{{ candidate.selected ? '最终选用候选' : candidateStatusLabel(candidate.status) }}</div>
                      <div class="cand-meta">
                        <span class="cand-score">score {{ candidate.score ?? 'n/a' }}</span>
                        <span class="chip" :class="candidateStatusClass(candidate.status)"><span class="dot"></span>{{ candidateStatusLabel(candidate.status) }}</span>
                      </div>
                    </div>
                    <div class="cand-body">
                      <pre class="cand-preview" :class="{ expanded: state.expandedCandidates[candidateKey(candidate, index, 'active')] }">{{ candidate.sql }}</pre>
                      <div class="cand-kv">tables={{ (candidate.referenced_tables || []).join(', ') || 'n/a' }}</div>
                      <div class="cand-kv">columns={{ (candidate.referenced_columns || []).join(', ') || 'n/a' }}</div>
                      <div v-if="candidate.execution_signature" class="cand-kv">signature={{ candidate.execution_signature }}</div>
                      <div v-if="candidate.error" class="cand-error">{{ candidate.error }}</div>
                      <div v-if="candidate.execution_preview?.length" class="dtable-wrap candidate-preview-table">
                        <table class="dtable compact-table">
                          <thead>
                            <tr>
                              <th v-for="column in Object.keys(candidate.execution_preview[0])" :key="column">{{ column }}</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(row, rowIndex) in candidate.execution_preview" :key="rowIndex">
                              <td v-for="column in Object.keys(candidate.execution_preview[0])" :key="column">{{ row[column] }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <button class="btn sm cand-toggle" type="button" @click="toggleCandidate(candidateKey(candidate, index, 'active'))">
                        {{ state.expandedCandidates[candidateKey(candidate, index, 'active')] ? '收起 SQL' : '展开 SQL' }}
                      </button>
                    </div>
                  </article>
                </div>
                <div v-else class="empty compact">
                  <div class="empty-icon"><IconSymbol name="sql" :size="24" /></div>
                  <div class="empty-title">暂无候选 SQL</div>
                </div>
              </div>
            </section>

            <div class="row-2">
              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">推理链路 · Trace</div>
                  <div class="panel-sub">end-to-end</div>
                </header>
                <div class="panel-body">
                  <div v-if="traceSteps.length" class="trace-list">
                    <div v-for="(step, index) in traceSteps" :key="step.key" class="trace-step" :class="step.state">
                      <div class="trace-num">{{ index + 1 }}</div>
                      <div>
                        <div class="trace-title">{{ step.title }}</div>
                        <div class="trace-detail">{{ step.detail }}</div>
                      </div>
                      <div class="trace-time">{{ step.time }}</div>
                    </div>
                  </div>
                  <div v-else class="empty compact">
                    <div class="empty-icon"><IconSymbol name="trace" :size="24" /></div>
                    <div class="empty-title">暂无推理轨迹</div>
                  </div>
                </div>
              </section>

              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">安全检查</div>
                  <div class="panel-sub">safety guard</div>
                  <div class="panel-actions">
                    <span class="chip success"><span class="dot"></span>{{ safetyPassCount }}/{{ safetyItems.length }} pass</span>
                  </div>
                </header>
                <div class="panel-body">
                  <div v-if="safetyItems.length" class="safety-grid">
                    <div v-for="item in safetyItems" :key="item.key" class="safety-row">
                      <div class="safety-icon" :class="item.state">
                        <IconSymbol :name="item.state === 'pass' ? 'check' : item.state === 'warn' ? 'warn' : 'x'" :size="13" />
                      </div>
                      <div class="safety-text">
                        <div class="safety-name">{{ item.name }}</div>
                        <div class="safety-note">{{ item.note }}</div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="empty compact">
                    <div class="empty-icon"><IconSymbol name="shield" :size="24" /></div>
                    <div class="empty-title">暂无安全检查结果</div>
                  </div>
                </div>
              </section>
            </div>

            <section class="panel">
              <header class="panel-head">
                <div class="panel-title">审计日志</div>
                <div class="panel-sub">GET /api/audit/logs · {{ auditRangeText }}</div>
                <div class="panel-actions">
                  <span v-if="state.auditLoading" class="chip pending"><span class="dot"></span>loading</span>
                  <button class="btn sm" type="button" @click="reloadAuditLogs"><IconSymbol name="refresh" :size="14" />刷新</button>
                </div>
              </header>
              <div class="panel-body flush">
                <div class="audit-filters">
                  <div class="meta-field">
                    <label class="field-label">关键词</label>
                    <input v-model="state.auditFilters.query" class="input" placeholder="问题 / SQL / fallback" @keyup.enter="applyAuditFilters" />
                  </div>
                  <div class="meta-field">
                    <label class="field-label">Domain</label>
                    <select v-model="state.auditFilters.domain" class="select" @change="applyAuditFilters">
                      <option value="">全部</option>
                      <option value="campus">campus</option>
                      <option value="bird">bird</option>
                    </select>
                  </div>
                  <div class="meta-field">
                    <label class="field-label">Mode</label>
                    <select v-model="state.auditFilters.llmMode" class="select" @change="applyAuditFilters">
                      <option value="">全部</option>
                      <option value="qwen_openrouter">qwen_openrouter</option>
                      <option value="bird_reference">bird_reference</option>
                    </select>
                  </div>
                  <div class="meta-field">
                    <label class="field-label">Status</label>
                    <select v-model="state.auditFilters.status" class="select" @change="applyAuditFilters">
                      <option value="">全部</option>
                      <option value="completed">completed</option>
                      <option value="blocked">blocked</option>
                      <option value="failed">failed</option>
                      <option value="clarification_required">clarification_required</option>
                    </select>
                  </div>
                  <div class="meta-field">
                    <label class="field-label">Source</label>
                    <select v-model="state.auditFilters.resultSource" class="select" @change="applyAuditFilters">
                      <option value="">全部</option>
                      <option value="qwen">qwen</option>
                      <option value="bird_reference">bird_reference</option>
                    </select>
                  </div>
                  <button class="btn" type="button" @click="applyAuditFilters"><IconSymbol name="filter" />筛选</button>
                </div>
                <div class="audit-list">
                  <div v-if="!state.auditLogs.length" class="empty">
                    <div class="empty-icon"><IconSymbol name="empty" :size="28" /></div>
                    <div class="empty-title">没有匹配的审计记录</div>
                    <div class="empty-sub">尝试调整筛选条件或刷新日志</div>
                  </div>
                  <div v-for="item in state.auditLogs" :key="item.timestamp + item.task_id" class="audit-item">
                    <div class="audit-time">{{ item.timestamp }}</div>
                    <div class="audit-q" :title="item.question">
                      {{ item.question }}
                      <span class="meta">· candidates {{ item.candidate_count || 0 }}</span>
                    </div>
                    <div class="audit-user audit-user-cell">
                      <div class="avatar av">管</div>
                      <span class="name">{{ item.user_id || 'demo-user' }}</span>
                    </div>
                    <div class="audit-domain">{{ item.domain }}</div>
                    <div>
                      <span class="chip" :class="resultStatusClass(item.status)"><span class="dot"></span>{{ item.status }}</span>
                    </div>
                    <div class="audit-source">{{ item.result_source || 'n/a' }}</div>
                  </div>
                </div>
                <div class="audit-pager">
                  <div class="info">共 {{ state.auditTotal }} 条 · 每页 {{ state.auditLimit }} 条</div>
                  <div class="pager-spacer"></div>
                  <button class="pager-btn" type="button" :disabled="auditPage === 1" @click="goAuditPage(auditPage - 1)">Prev</button>
                  <button class="pager-btn active" type="button">{{ auditPage }}</button>
                  <button class="pager-btn" type="button" :disabled="auditPage >= auditPageCount" @click="goAuditPage(auditPage + 1)">Next</button>
                </div>
              </div>
            </section>
          </div>
        </template>

        <template v-else-if="state.activeView === 'result'">
          <div class="page-head">
            <div>
              <div class="page-title">查询结果</div>
              <div class="page-sub">最近一次查询的摘要、图表与明细数据</div>
            </div>
          </div>
          <div class="stack">
            <div class="overview-grid">
              <section class="panel">
                <header class="panel-head"><div class="panel-title">结果摘要</div><div class="panel-sub">{{ state.taskId || 'no task' }}</div></header>
                <div class="panel-body">
                  <div class="summary-text">{{ state.result?.summary_text || '尚未执行查询。' }}</div>
                  <div class="kpi-row">
                    <div v-for="item in resultKpis" :key="item.label" class="kpi">
                      <div class="kpi-label">{{ item.label }}</div>
                      <div class="kpi-value">{{ item.value }}</div>
                      <div class="kpi-delta flat">{{ item.note }}</div>
                    </div>
                  </div>
                </div>
              </section>
              <section class="panel">
                <header class="panel-head"><div class="panel-title">结果图表</div><div class="panel-sub">{{ chartSpec.type || 'auto' }}</div></header>
                <div class="panel-body flush">
                  <div v-show="hasChart" ref="chartEl" class="chart-container"></div>
                  <div v-if="!hasChart" class="empty compact"><div class="empty-title">暂无可视化图表</div></div>
                </div>
              </section>
            </div>
          </div>
        </template>

        <template v-else-if="state.activeView === 'sql'">
          <div class="page-head">
            <div>
              <div class="page-title">SQL 证据</div>
              <div class="page-sub">最终 SQL 与候选链路</div>
            </div>
          </div>
          <div class="stack">
            <section class="panel">
              <header class="panel-head"><div class="panel-title">最终 SQL</div><button class="btn sm panel-actions" type="button" @click="copySql"><IconSymbol name="copy" :size="14" />复制</button></header>
              <div class="panel-body"><div class="code"><div class="code-body"><pre v-html="highlightedFinalSql"></pre></div></div></div>
            </section>
          </div>
        </template>

        <template v-else-if="state.activeView === 'trace'">
          <div class="page-head">
            <div><div class="page-title">推理链路</div><div class="page-sub">end-to-end trace</div></div>
          </div>
          <section class="panel">
            <div class="panel-body">
              <div v-if="traceSteps.length" class="trace-list">
                <div v-for="(step, index) in traceSteps" :key="step.key" class="trace-step" :class="step.state">
                  <div class="trace-num">{{ index + 1 }}</div>
                  <div><div class="trace-title">{{ step.title }}</div><div class="trace-detail">{{ step.detail }}</div></div>
                  <div class="trace-time">{{ step.time }}</div>
                </div>
              </div>
              <div v-else class="empty"><div class="empty-title">暂无推理轨迹</div></div>
            </div>
          </section>
        </template>

        <template v-else-if="state.activeView === 'safety'">
          <div class="page-head">
            <div><div class="page-title">安全检查</div><div class="page-sub">SQL 白名单、沙箱执行、权限与注入检测</div></div>
          </div>
          <section class="panel">
            <div class="panel-body">
              <div v-if="safetyItems.length" class="safety-grid">
                <div v-for="item in safetyItems" :key="item.key" class="safety-row">
                  <div class="safety-icon" :class="item.state">
                    <IconSymbol :name="item.state === 'pass' ? 'check' : item.state === 'warn' ? 'warn' : 'x'" :size="13" />
                  </div>
                  <div class="safety-text"><div class="safety-name">{{ item.name }}</div><div class="safety-note">{{ item.note }}</div></div>
                </div>
              </div>
              <div v-else class="empty"><div class="empty-title">暂无安全检查结果</div></div>
            </div>
          </section>
        </template>

        <template v-else-if="state.activeView === 'audit'">
          <div class="page-head">
            <div><div class="page-title">审计日志</div><div class="page-sub">全部查询、状态、来源与候选链路快照</div></div>
            <button class="btn" type="button" @click="reloadAuditLogs"><IconSymbol name="refresh" />刷新</button>
          </div>
          <section class="panel">
            <div class="panel-body flush">
              <div class="audit-list">
                <div v-for="item in state.auditLogs" :key="item.timestamp + item.task_id" class="audit-item">
                  <div class="audit-time">{{ item.timestamp }}</div>
                  <div class="audit-q">{{ item.question }}</div>
                  <div class="audit-user audit-user-cell"><div class="avatar av">管</div><span class="name">{{ item.user_id || 'demo-user' }}</span></div>
                  <div class="audit-domain">{{ item.domain }}</div>
                  <div><span class="chip" :class="resultStatusClass(item.status)"><span class="dot"></span>{{ item.status }}</span></div>
                  <div class="audit-source">{{ item.result_source || 'n/a' }}</div>
                </div>
              </div>
            </div>
          </section>
        </template>

        <template v-else-if="state.activeView === 'settings'">
          <div class="page-head">
            <div>
              <div class="page-title">模型设置</div>
              <div class="page-sub">数据管理员维护 Text-to-SQL 可用 LLM 与默认路由</div>
            </div>
            <div class="page-actions">
              <span v-if="state.llmSavedNotice" class="chip success"><span class="dot"></span>{{ state.llmSavedNotice }}</span>
              <button class="btn" type="button" @click="resetLlmForm"><IconSymbol name="refresh" />重置表单</button>
            </div>
          </div>

          <div class="stack">
            <div class="kpi-row">
              <div v-for="item in llmKpis" :key="item.label" class="kpi">
                <div class="kpi-label">{{ item.label }}</div>
                <div class="kpi-value setting-kpi-value">{{ item.value }}</div>
                <div class="kpi-delta flat">{{ item.note }}</div>
              </div>
            </div>

            <div v-if="state.llmFormError" class="inline-error">
              <IconSymbol name="warn" :size="14" />
              <div><strong>配置未保存</strong> · {{ state.llmFormError }}</div>
            </div>

            <div class="settings-grid">
              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">新增 LLM</div>
                  <div class="panel-sub">provider / model / secret</div>
                  <div class="panel-actions">
                    <span class="chip info"><span class="dot"></span>admin only</span>
                  </div>
                </header>
                <div class="panel-body">
                  <div class="llm-form-grid">
                    <div class="meta-field span-2">
                      <label class="field-label">配置名称</label>
                      <input v-model="state.llmForm.displayName" class="input" placeholder="例如：Qwen Plus 校园问数" />
                    </div>
                    <div class="meta-field">
                      <label class="field-label">Provider</label>
                      <select v-model="state.llmForm.provider" class="select" @change="applyProviderDefaults">
                        <option v-for="item in llmProviderOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                      </select>
                    </div>
                    <div class="meta-field">
                      <label class="field-label">作用域</label>
                      <select v-model="state.llmForm.scope" class="select">
                        <option value="campus">campus</option>
                        <option value="bird">bird</option>
                        <option value="global">global</option>
                      </select>
                    </div>
                    <div class="meta-field span-2">
                      <label class="field-label">模型 ID</label>
                      <input v-model="state.llmForm.model" class="input" placeholder="例如：qwen/qwen3.6-plus:free" />
                    </div>
                    <div class="meta-field span-2">
                      <label class="field-label">Base URL</label>
                      <input v-model="state.llmForm.baseUrl" class="input" placeholder="https://.../chat/completions" />
                    </div>
                    <div class="meta-field span-2">
                      <label class="field-label">API Key</label>
                      <input v-model="state.llmForm.apiKey" class="input secret-input" type="password" placeholder="保存后仅显示遮罩" />
                    </div>
                    <div class="meta-field">
                      <label class="field-label">Temperature</label>
                      <input v-model.number="state.llmForm.temperature" class="input" type="number" min="0" max="2" step="0.1" />
                    </div>
                    <div class="meta-field">
                      <label class="field-label">Timeout(s)</label>
                      <input v-model.number="state.llmForm.timeoutSeconds" class="input" type="number" min="1" max="180" step="1" />
                    </div>
                    <div class="meta-field">
                      <label class="field-label">Retries</label>
                      <input v-model.number="state.llmForm.maxRetries" class="input" type="number" min="0" max="5" step="1" />
                    </div>
                    <div class="meta-field span-2">
                      <label class="field-label">备注</label>
                      <textarea v-model="state.llmForm.notes" class="textarea llm-notes" rows="3" placeholder="用途、配额、负责人或上线窗口"></textarea>
                    </div>
                  </div>
                  <div class="settings-actions">
                    <button class="btn" type="button" @click="resetLlmForm">清空</button>
                    <button class="btn primary" type="button" @click="addLlmConfig"><IconSymbol name="plus" />新增模型</button>
                  </div>
                </div>
              </section>

              <section class="panel">
                <header class="panel-head">
                  <div class="panel-title">默认路由</div>
                  <div class="panel-sub">{{ defaultLlm?.model || 'no model' }}</div>
                  <div class="panel-actions">
                    <span class="chip" :class="defaultLlm?.enabled ? 'success' : 'pending'"><span class="dot"></span>{{ defaultLlm?.enabled ? 'enabled' : 'disabled' }}</span>
                  </div>
                </header>
                <div class="panel-body">
                  <div v-if="defaultLlm" class="default-model">
                    <div class="default-icon"><IconSymbol name="star" :size="18" /></div>
                    <div>
                      <div class="default-title">{{ defaultLlm.displayName }}</div>
                      <div class="default-sub">{{ providerLabel(defaultLlm.provider) }} · {{ defaultLlm.scope }}</div>
                    </div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">model</div>
                    <div class="source-line">{{ defaultLlm?.model || 'n/a' }}</div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">base url</div>
                    <div class="source-line long">{{ defaultLlm?.baseUrl || 'n/a' }}</div>
                  </div>
                  <div class="sources-row">
                    <div class="sources-label">secret</div>
                    <div class="source-line">{{ defaultLlm?.apiKeyMasked || 'n/a' }}</div>
                  </div>
                  <div class="route-policy">
                    <div class="route-step"><span>1</span><strong>auto</strong><em>优先默认启用模型</em></div>
                    <div class="route-step"><span>2</span><strong>qwen</strong><em>强制真实模型</em></div>
                    <div class="route-step"><span>3</span><strong>mock</strong><em>本地演示兜底</em></div>
                  </div>
                </div>
              </section>
            </div>

            <section class="panel">
              <header class="panel-head">
                <div class="panel-title">LLM 配置列表</div>
                <div class="panel-sub">{{ state.llmConfigs.length }} models</div>
              </header>
              <div class="panel-body flush">
                <div class="llm-list">
                  <article v-for="item in state.llmConfigs" :key="item.id" class="llm-row" :class="{ disabled: !item.enabled, default: item.isDefault }">
                    <div class="llm-main">
                      <div class="llm-avatar"><IconSymbol :name="item.isDefault ? 'star' : 'key'" :size="16" /></div>
                      <div class="llm-title-wrap">
                        <div class="llm-title">
                          {{ item.displayName }}
                          <span v-if="item.isDefault" class="chip selected"><span class="dot"></span>default</span>
                        </div>
                        <div class="llm-sub">{{ providerLabel(item.provider) }} · {{ item.model }}</div>
                      </div>
                    </div>
                    <div class="llm-cell">
                      <div class="llm-label">scope</div>
                      <div class="llm-value">{{ item.scope }}</div>
                    </div>
                    <div class="llm-cell">
                      <div class="llm-label">runtime</div>
                      <div class="llm-value">{{ item.temperature }} temp · {{ item.timeoutSeconds }}s · {{ item.maxRetries }} retry</div>
                    </div>
                    <div class="llm-cell secret-cell">
                      <div class="llm-label">key</div>
                      <div class="llm-value">{{ item.apiKeyMasked }}</div>
                    </div>
                    <div class="llm-actions">
                      <button class="btn sm" type="button" :disabled="item.isDefault" @click="setDefaultLlm(item.id)">
                        <IconSymbol name="star" :size="13" />默认
                      </button>
                      <button class="btn sm" type="button" @click="toggleLlm(item.id)">
                        <IconSymbol :name="item.enabled ? 'x' : 'check'" :size="13" />{{ item.enabled ? '停用' : '启用' }}
                      </button>
                      <button class="btn sm danger" type="button" @click="removeLlm(item.id)">
                        <IconSymbol name="trash" :size="13" />删除
                      </button>
                    </div>
                  </article>
                </div>
              </div>
            </section>
          </div>
        </template>
      </div>
    </main>
  </div>
</template>
