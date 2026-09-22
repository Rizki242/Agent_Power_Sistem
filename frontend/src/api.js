const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const API_KEY = import.meta.env.VITE_API_KEY || ''

export function getAuthToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('pple_auth_token') || ''
  }
  return ''
}

export function setAuthToken(token) {
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('pple_auth_token', token)
    } else {
      localStorage.removeItem('pple_auth_token')
    }
  }
}

function getAuthHeaders(customHeaders = {}) {
  const headers = { ...customHeaders }
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY
  }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

const READ_TIMEOUT_MS = 20000
const WRITE_TIMEOUT_MS = 45000
// Chat melewati LLM + 6 specialist agent, jadi diberi anggaran waktu jauh lebih panjang.
const CHAT_TIMEOUT_MS = 180000

/**
 * Gabungkan signal pemanggil dengan batas waktu, supaya permintaan yang menggantung
 * tidak membuat UI menunggu selamanya (spinner tanpa akhir saat backend tidak sehat).
 */
function withTimeout(signal, timeoutMs) {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  const onAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onAbort, { once: true })
  }

  return {
    signal: controller.signal,
    didTimeout: () => timedOut,
    cleanup: () => {
      clearTimeout(timer)
      if (signal) signal.removeEventListener('abort', onAbort)
    },
  }
}

async function fetchWithTimeout(url, options = {}, timeoutMs = READ_TIMEOUT_MS) {
  const guard = withTimeout(options.signal, timeoutMs)
  try {
    return await fetch(url, { ...options, signal: guard.signal })
  } catch (error) {
    if (error.name === 'AbortError' && guard.didTimeout()) {
      throw new Error(`Permintaan melebihi batas waktu ${Math.round(timeoutMs / 1000)} detik`)
    }
    // Jika fetch gagal (koneksi ditolak / backend mati), berikan pesan diagnostik yang jelas
    const msg = error?.message || ''
    if (error instanceof TypeError || msg === 'Failed to fetch' || msg.includes('fetch') || msg.includes('NetworkError')) {
      throw new Error('Tidak dapat terhubung ke server backend FastAPI (port 8000). Pastikan server backend sudah berjalan (jalankan run_api.bat atau run_all.bat).')
    }
    throw error
  } finally {
    guard.cleanup()
  }
}

async function getJson(path, signal, customHeaders = {}) {
  const response = await fetchWithTimeout(`${API_BASE}${path}`, {
    signal,
    headers: getAuthHeaders(customHeaders),
  })
  if (!response.ok) {
    let errDetail = `API merespons ${response.status}`
    if (response.status === 502 || response.status === 504) {
      errDetail = 'Server backend FastAPI (port 8000) tidak dapat dihubungi. Pastikan backend aktif (jalankan run_api.bat).'
    } else {
      try {
        const errJson = await response.json()
        if (errJson && errJson.detail) {
          errDetail = errJson.detail
        }
      } catch {
        // ignore
      }
    }
    const err = new Error(errDetail)
    err.status = response.status
    throw err
  }
  return response.json()
}

async function sendJson(path, options = {}, timeoutMs = WRITE_TIMEOUT_MS) {
  const response = await fetchWithTimeout(
    `${API_BASE}${path}`,
    {
      ...options,
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(options.headers) },
    },
    timeoutMs
  )
  if (!response.ok) {
    let errDetail = `API merespons ${response.status}`
    if (response.status === 502 || response.status === 504) {
      errDetail = 'Server backend FastAPI (port 8000) tidak dapat dihubungi. Pastikan backend aktif (jalankan run_api.bat).'
    } else {
      try {
        const errJson = await response.json()
        if (errJson && errJson.detail) {
          errDetail = errJson.detail
        }
      } catch {
        // ignore
      }
    }
    const err = new Error(errDetail)
    err.status = response.status
    throw err
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

  const results = [agentsRes, modulesRes, automationsRes, learnedRes]
  const agents = agentsRes.status === 'fulfilled' ? (agentsRes.value.agents ?? []) : []
  const modules = modulesRes.status === 'fulfilled' ? (modulesRes.value.results ?? []) : []
  const runs = automationsRes.status === 'fulfilled' ? (automationsRes.value.runs ?? []) : []
  const patterns = learnedRes.status === 'fulfilled' ? (learnedRes.value.skills ?? []) : []

  // allSettled tidak pernah menolak, sehingga pemanggil harus diberi tahu berapa
  // sumber yang gagal - tanpa ini Beranda mengklaim "Sistem terhubung" walau
  // seluruh backend mati.
  const failed = results.filter((result) => result.status === 'rejected').length

  return { agents, modules, runs, patterns, failed, total: results.length }
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

export function scanOllamaModels(host) {
  return sendJson('/api/settings/ollama/scan', {
    method: 'POST',
    body: JSON.stringify({ host: host || undefined }),
  })
}

export async function sendChatMessage({ message, provider, model, apiKey, file, source = 'CHAT', sessionId = null, ollamaHost = null, signal }) {
  if (file) {
    const body = new FormData()
    body.append('message', message || '')
    if (provider) body.append('provider', provider)
    if (model) body.append('model', model)
    if (apiKey) body.append('api_key', apiKey)
    if (source) body.append('source', source)
    if (sessionId) body.append('session_id', sessionId)
    if (ollamaHost) body.append('ollama_host', ollamaHost)
    body.append('file', file)
    const response = await fetchWithTimeout(`${API_BASE}/api/agent/chat`, {
      method: 'POST',
      body,
      headers: { ...authHeaders, 'X-Source': source },
      signal,
    }, CHAT_TIMEOUT_MS)
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
      ollama_host: ollamaHost,
    }),
    signal,
  }, CHAT_TIMEOUT_MS)
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

export function getFleetReliability(signal) {
  return getJson('/api/reliability/fleet', signal)
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

// ── MCSA (Motor Current Signature Analysis) API ───────────────────────────

export function getMcsaSummary(signal) {
  return getJson('/api/summary', signal)
}

export function getMcsaEquipmentList({ unit, voltage, status, search } = {}, signal) {
  const params = new URLSearchParams()
  if (unit && unit !== 'all') params.set('unit', unit)
  if (voltage && voltage !== 'all') params.set('voltage', voltage)
  if (status && status !== 'all') params.set('status', status)
  if (search && search.trim()) params.set('search', search.trim())
  const qs = params.toString()
  return getJson(`/api/equipment${qs ? `?${qs}` : ''}`, signal)
}

export function getMcsaEquipmentDetail(equipmentName, signal) {
  return getJson(`/api/equipment/${encodeURIComponent(equipmentName)}`, signal)
}

export function calculateRotorBar(data) {
  return sendJson('/api/rotorbar/calculate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── Authentication & User Session API ──────────────────────────────

export function loginUser(username, password) {
  return sendJson('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function getCurrentUser(signal) {
  return getJson('/api/auth/me', signal)
}

export function logoutUser() {
  return sendJson('/api/auth/logout', {
    method: 'POST',
  })
}

export function changeUserPassword(oldPassword, newPassword) {
  return sendJson('/api/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
}



