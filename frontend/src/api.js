const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''
const authHeaders = API_KEY ? { 'X-API-Key': API_KEY } : {}

async function getJson(path, signal) {
  const response = await fetch(`${API_BASE}${path}`, { signal, headers: authHeaders })
  if (!response.ok) {
    throw new Error(`API merespons ${response.status}`)
  }
  return response.json()
}

async function sendJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...authHeaders, ...options.headers },
  })
  if (!response.ok) {
    throw new Error(`API merespons ${response.status}`)
  }
  return response.json()
}

export async function getWorkspaceOverview(signal) {
  const [agentsRes, modulesRes, automationsRes, learnedRes] = await Promise.allSettled([
    getJson('/api/v2/agents', signal),
    getJson('/api/v2/module-load-report', signal),
    getJson('/api/automations/runs', signal),
    getJson('/api/skills/learned-patterns', signal),
  ])

  const agents = agentsRes.status === 'fulfilled' ? (agentsRes.value.agents ?? []) : []
  const modules = modulesRes.status === 'fulfilled' ? (modulesRes.value.results ?? []) : []
  const runs = automationsRes.status === 'fulfilled' ? (automationsRes.value.runs ?? []) : []
  const patterns = learnedRes.status === 'fulfilled' ? (learnedRes.value.skills ?? []) : []

  return { agents, modules, runs, patterns }
}

export async function getDataWorkspace(signal) {
  const [assets, modules] = await Promise.all([
    getJson('/api/v2/assets', signal),
    getJson('/api/v2/module-load-report', signal),
  ])
  return { assets: assets.equipment ?? [], modules: modules.results ?? [] }
}

export async function getEquipmentModules(equipmentId, signal) {
  return getJson(`/api/v2/equipment/${encodeURIComponent(equipmentId)}/modules`, signal)
}

export async function setEquipmentModule(equipmentId, moduleId, enabled) {
  return sendJson(`/api/v2/equipment/${encodeURIComponent(equipmentId)}/modules/${encodeURIComponent(moduleId)}`, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  })
}

export async function getMaterials(signal) {
  const result = await getJson('/api/materi', signal)
  return result.materi ?? []
}

export async function searchMaterials(query, signal) {
  const response = await fetch(`${API_BASE}/api/materi/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders },
    body: JSON.stringify({ query }),
    signal,
  })
  if (!response.ok) throw new Error(`Pencarian merespons ${response.status}`)
  const result = await response.json()
  return result.results ?? []
}

export async function uploadMaterial({ file, title, tags, level }) {
  const body = new FormData()
  body.append('file', file)
  if (title.trim()) body.append('title', title.trim())
  if (tags.trim()) body.append('tags', tags.trim())
  body.append('level', level)
  const response = await fetch(`${API_BASE}/api/materi/upload`, { method: 'POST', body, headers: authHeaders })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `Upload merespons ${response.status}`)
  }
  return response.json()
}

export async function getMemoryWorkspace(signal) {
  const [materials, learned, harness] = await Promise.all([
    getJson('/api/materi', signal),
    getJson('/api/skills/learned-patterns', signal),
    getJson('/api/learning/harness-status', signal),
  ])
  return {
    knowledge: materials.materi ?? [],
    experiences: learned.skills ?? [],
    instructions: harness.components ?? [],
    cycles: harness.recent_cycles ?? [],
    harnessStatus: harness.status ?? 'UNKNOWN',
  }
}

export async function getAutomationWorkspace(signal) {
  const [workflows, runs] = await Promise.all([
    getJson('/api/automations/workflows', signal),
    getJson('/api/automations/runs', signal),
  ])
  return { workflows: workflows.workflows ?? [], runs: runs.runs ?? [] }
}

export function createAutomationWorkflow(payload) {
  return sendJson('/api/automations/workflows', { method: 'POST', body: JSON.stringify(payload) })
}

export function setAutomationEnabled(workflowId, enabled) {
  return sendJson(`/api/automations/workflows/${encodeURIComponent(workflowId)}`, { method: 'PATCH', body: JSON.stringify({ enabled }) })
}

export function runAutomation(workflowId) {
  return sendJson(`/api/automations/workflows/${encodeURIComponent(workflowId)}/run`, { method: 'POST' })
}

export function approveAutomationRun(runId, approvedBy) {
  return sendJson(`/api/automations/runs/${encodeURIComponent(runId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by: approvedBy }) })
}

export function retryAutomationRun(runId) {
  return sendJson(`/api/automations/runs/${encodeURIComponent(runId)}/retry`, { method: 'POST' })
}

export async function getAgentLab(signal) {
  const [status, benchmarks, harness, patterns] = await Promise.all([
    getJson('/api/agent/improvement-status', signal),
    getJson('/api/skills/benchmarks', signal),
    getJson('/api/learning/harness-status', signal),
    getJson('/api/skills/learned-patterns', signal),
  ])
  return { status, benchmarks, harness, patterns: patterns.skills ?? [] }
}

export function runImprovementCycle(maxIterations = 4) {
  return sendJson('/api/agent/self-improve', { method: 'POST', body: JSON.stringify({ max_iterations: maxIterations }) })
}

export function runHarnessEvaluation() {
  return sendJson('/api/learning/evaluate-harness', { method: 'POST' })
}

export function learnFromHistory() {
  return sendJson('/api/agent/learn-from-history', { method: 'POST' })
}

export function getSettingsOverview(signal) {
  return getJson('/api/settings/overview', signal)
}

export function saveAISettings(payload) {
  return sendJson('/api/settings/ai', { method: 'PUT', body: JSON.stringify(payload) })
}

export function testAIConnection() {
  return sendJson('/api/settings/test-ai', { method: 'POST' })
}

export async function sendChatMessage({ message, provider, model, apiKey, file, source = 'CHAT', sessionId = null, signal }) {
  if (file) {
    const body = new FormData()
    body.append('message', message || '')
    if (provider) body.append('provider', provider)
    if (model) body.append('model', model)
    if (apiKey) body.append('api_key', apiKey)
    if (source) body.append('source', source)
    if (sessionId) body.append('session_id', sessionId)
    body.append('file', file)
    const response = await fetch(`${API_BASE}/api/agent/chat`, {
      method: 'POST',
      body,
      headers: { ...authHeaders, 'X-Source': source },
      signal,
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `Chat merespons ${response.status}`)
    }
    return response.json()
  }

  return sendJson('/api/agent/chat', {
    method: 'POST',
    headers: { 'X-Source': source },
    body: JSON.stringify({
      message: message || '',
      provider: provider || 'gemini',
      model,
      api_key: apiKey,
      source,
      session_id: sessionId,
    }),
    signal,
  })
}

export async function getChatSessions(sessionType, signal) {
  const query = sessionType ? `?session_type=${encodeURIComponent(sessionType)}` : ''
  const res = await getJson(`/api/agent/chat/sessions${query}`, signal)
  return res.sessions ?? []
}

export async function createNewChatSession({ title, sessionType = 'chat' }) {
  return sendJson('/api/agent/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, session_type: sessionType }),
  })
}

export async function getChatSessionMessages(sessionId, signal) {
  const res = await getJson(`/api/agent/chat/sessions/${encodeURIComponent(sessionId)}`, signal)
  return res.messages ?? []
}

export async function deleteChatSession(sessionId) {
  return sendJson(`/api/agent/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
}

// ── CBM Dashboard API ──────────────────────────────────────────────────────

export function getDomains(signal) {
  return getJson('/api/v2/domain/domains', signal)
}

export function getDomainMeasurements(domain, { equipment, start, end, limit = 200 } = {}, signal) {
  const params = new URLSearchParams()
  if (equipment) params.set('equipment', equipment)
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  params.set('limit', String(limit))
  const qs = params.toString()
  return getJson(`/api/v2/domain/${encodeURIComponent(domain)}/measurements${qs ? `?${qs}` : ''}`, signal)
}

export function getDgaTransformers(signal) {
  return getJson('/api/dga/transformers', signal)
}

export function getDgaTransformerDetail(transformerId, signal) {
  return getJson(`/api/dga/transformers/${encodeURIComponent(transformerId)}`, signal)
}

export function getReliabilityHealth(equipmentId, signal) {
  return getJson(`/api/v2/reliability/${encodeURIComponent(equipmentId)}`, signal)
}

export function getAutomatedReportsSummary(signal) {
  return getJson('/api/reports/automated/summary', signal)
}

export function getWeeklyReportDownloadUrl(module, format = 'docx', week = 3) {
  return `${API_BASE}/api/reports/automated/download/weekly/${encodeURIComponent(module)}?format=${encodeURIComponent(format)}&week=${week}`
}

export function getMonthlyReportDownloadUrl(format = 'docx', year = 2026, month = 9) {
  return `${API_BASE}/api/reports/automated/download/monthly?format=${encodeURIComponent(format)}&year=${year}&month=${month}`
}

export function getMonthlyModuleReportDownloadUrl(module, format = 'docx', year = 2026, month = 9) {
  return `${API_BASE}/api/reports/automated/download/monthly/${encodeURIComponent(module)}?format=${encodeURIComponent(format)}&year=${year}&month=${month}`
}

export function getMeetingPptxDownloadUrl(year = 2026, month = 9) {
  return `${API_BASE}/api/reports/automated/download/meeting-pptx?year=${year}&month=${month}`
}

// ── Work Orders (CBM & Maintenance Dispatch) API ───────────────────────────

export function getWorkOrders({ equipment, domain, status } = {}, signal) {
  const params = new URLSearchParams()
  if (equipment) params.set('equipment', equipment)
  if (domain) params.set('domain', domain)
  if (status) params.set('status', status)
  const qs = params.toString()
  return getJson(`/api/workorders${qs ? `?${qs}` : ''}`, signal)
}

export function createNewWorkOrder(data) {
  return sendJson('/api/workorders', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function generateCbmWorkOrder(data) {
  return sendJson('/api/workorders/generate-cbm', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function approveWorkOrder({ woNumber, approvedBy, action = 'Approve' }) {
  return sendJson('/api/workorders/approve', {
    method: 'POST',
    body: JSON.stringify({
      wo_number: woNumber,
      approved_by: approvedBy,
      action,
    }),
  })
}

