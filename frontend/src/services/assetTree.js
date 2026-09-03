// Builds the sidebar's TreeNode[] purely from data already exposed by the
// backend today (/api/v2/modules + each domain's existing equipment-list
// endpoint). No new backend route: this is the frontend-only redesign
// described in desaindakhir.md's TreeNode concept, layered over the
// existing /api/* + /api/v2/* surface (docs/final.md Phase 25).
//
// v1 depth is root -> unit -> module -> equipment. "System" grouping from
// desaindakhir.md's fuller Plant/Unit/System/Equipment hierarchy is left out
// on purpose: none of today's equipment endpoints expose a queryable
// "system" field, so a 4th level would have to be invented client-side.
//
// @typedef {Object} TreeNode
// @property {string} id
// @property {string} name
// @property {'root'|'unit'|'module'|'equipment'} type
// @property {string} [icon]
// @property {string} [parentId]
// @property {TreeNode[]} [children]
// @property {{ moduleId?: string, equipmentId?: string, status?: string }} [metadata]

// api.js stays at src/api.js for now - existing pages import it from there
// and moving it is a mechanical rename left for the full cutover, not this slice.
import { apiUrl } from '../api';

// Which existing endpoint backs each engineering module's equipment list,
// and how to read equipment id/name/unit/status out of its response shape.
// Adding a module here is the only code change needed to grow a branch of
// the tree - equipment instances themselves are never hardcoded, they come
// from the live API response.
const DOMAIN_EQUIPMENT_SOURCES = {
  mcsa: {
    url: '/api/equipment',
    listKey: 'equipment',
    id: (row) => row.equipment,
    name: (row) => row.equipment,
    unit: (row) => row.unit,
    status: (row) => row.condition || row.status,
  },
  vibration: {
    url: '/api/vibration/equipment',
    listKey: 'equipment',
    id: (row) => row.asset_id || row.equipment,
    name: (row) => row.equipment,
    unit: (row) => row.unit,
    status: (row) => row.status,
  },
  dga: {
    url: '/api/dga/transformers',
    listKey: 'transformers',
    id: (row) => row.transformer_id,
    name: (row) => row.name,
    unit: (row) => row.unit,
    status: (row) => row.status,
  },
  tribology: {
    url: '/api/tribology/samples',
    listKey: 'samples',
    id: (row) => row.sample_id,
    name: (row) => row.equipment,
    unit: (row) => row.unit,
    status: (row) => row.status,
  },
  thermal: {
    url: '/api/thermal/inspections',
    listKey: 'inspections',
    id: (row) => row.id || row.equipment,
    name: (row) => row.equipment,
    unit: (row) => row.unit,
    status: (row) => row.status,
  },
};

const UNIT_ORDER = ['UNIT 1', 'UNIT 2', 'UNIT 3', 'UNIT COMMON'];

function unitSortIndex(unitName) {
  const idx = UNIT_ORDER.indexOf(String(unitName || '').toUpperCase());
  return idx === -1 ? UNIT_ORDER.length : idx;
}

async function fetchModuleList() {
  const res = await fetch(apiUrl('/api/v2/modules'));
  if (!res.ok) throw new Error(`Gagal memuat daftar module (${res.status})`);
  const data = await res.json();
  return data.modules || [];
}

async function fetchModuleEquipment(moduleId) {
  const source = DOMAIN_EQUIPMENT_SOURCES[moduleId];
  if (!source) return [];
  try {
    const res = await fetch(apiUrl(source.url));
    if (!res.ok) return [];
    const data = await res.json();
    const rows = data[source.listKey] || [];
    return rows
      .map((row) => ({
        id: source.id(row),
        name: source.name(row),
        unit: source.unit(row) || 'UNIT COMMON',
        status: source.status(row),
      }))
      .filter((eq) => eq.id);
  } catch {
    return [];
  }
}

/**
 * Assembles the full sidebar tree: one 'unit' branch per distinct unit seen
 * across all modules' equipment (derived from live data, not a hardcoded
 * array), each holding one 'module' child per registered engineering module,
 * each holding that module's equipment for that unit as leaves.
 * @returns {Promise<TreeNode[]>}
 */
export async function buildAssetTree() {
  const modules = await fetchModuleList();
  const equipmentByModule = await Promise.all(
    modules.map((m) => fetchModuleEquipment(m.id))
  );

  const unitsSeen = new Set();
  modules.forEach((_, i) => {
    equipmentByModule[i].forEach((eq) => unitsSeen.add(eq.unit));
  });
  if (unitsSeen.size === 0) UNIT_ORDER.forEach((u) => unitsSeen.add(u));

  const units = Array.from(unitsSeen).sort(
    (a, b) => unitSortIndex(a) - unitSortIndex(b) || a.localeCompare(b)
  );

  return units.map((unitName) => {
    const unitId = `unit:${unitName}`;
    const moduleNodes = modules.map((mod, i) => {
      const moduleId = `module:${unitName}:${mod.id}`;
      const equipmentInUnit = equipmentByModule[i].filter((eq) => eq.unit === unitName);
      return {
        id: moduleId,
        name: mod.name,
        type: 'module',
        parentId: unitId,
        metadata: { moduleId: mod.id },
        children: equipmentInUnit.map((eq) => ({
          id: `equipment:${mod.id}:${eq.id}`,
          name: eq.name,
          type: 'equipment',
          parentId: moduleId,
          metadata: { moduleId: mod.id, equipmentId: eq.id, status: eq.status },
        })),
      };
    });

    return {
      id: unitId,
      name: unitName,
      type: 'unit',
      parentId: 'root',
      children: moduleNodes,
    };
  });
}
