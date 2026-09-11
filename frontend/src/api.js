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
  const [agents, modules] = await Promise.all([
    getJson('/api/v2/agents', signal),
    getJson('/api/v2/module-load-report', signal),
  ])
  return { agents: agents.agents ?? [], modules: modules.results ?? [] }
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
