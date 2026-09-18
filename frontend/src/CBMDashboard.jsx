/**
 * Dashboard Condition Based Monitoring 
 *
 * 3 Tab utama:
 *   1. Segitiga Duval (DGA): ternary SVG plot CH4/C2H4/C2H2 dengan 7 zona fault
 *   2. Parameter Vibrasi: bar chart RMS/velocity per equipment dari domain measurements
 *   3. Tren Kesehatan: multi-line SVG time series health-index per domain
 *
 * Semua chart pure SVG — tidak butuh Recharts, Chart.js, atau D3.
 * Data dari /api/dga/* dan /api/v2/domain/* (domain_router.py + specialist_router.py).
 * Jika API tidak tersedia, setiap panel tampilkan empty-state — tidak crash.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart2, RefreshCw, TrendingUp, Triangle, Zap,
} from 'lucide-react'
import {
  getDgaTransformerDetail,
  getDgaTransformers,
  getDomainMeasurements,
  getDomains,
} from './api.js'

// ─── Constants ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'duval', label: 'Segitiga Duval', icon: Triangle },
  { id: 'vibration', label: 'Parameter Vibrasi', icon: BarChart2 },
  { id: 'trend', label: 'Tren Kesehatan', icon: TrendingUp },
]


// Domain colors for trend chart lines
const DOMAIN_COLORS = {
  VIBRASI: '#3b82f6',
  DGA: '#f59e0b',
  TRIBOLOGI: '#10b981',
  THERMAL: '#ef4444',
  PD: '#8b5cf6',
  MCSA: '#06b6d4',
}

// ─── Duval Triangle 1 — Correct Zone Boundaries (IEC 60599:2015 + Duval 2010) ─────
//
// Axes (% of three-gas sum CH4 + C2H4 + C2H2):
//   CH4  increases bottom → top-right  (right leg of equilateral triangle)
//   C2H4 increases right  → top-left   (left leg)
//   C2H2 increases top    → bottom     (base, left to right)
//
// Standard equilateral triangle orientation:
//   CH4  at BOTTOM-LEFT vertex  (100% CH4, 0% C2H4, 0% C2H2)
//   C2H4 at TOP vertex          (0% CH4, 100% C2H4, 0% C2H2)
//   C2H2 at BOTTOM-RIGHT vertex (0% CH4, 0% C2H4, 100% C2H2)
//
// Zone vertices are EXACT boundary percentages from IEC 60599 / Duval 2010 update.
// Each point is [ch4%, c2h4%, c2h2%] where the three always sum to 100.

// Key boundary lines:
//   %C2H2 = 4  vertical from left to right (separates thermal from discharge)
//   %C2H2 = 13 (D1 right boundary)
//   %C2H2 = 29 (D1/D2 boundary)
//   %C2H4 = 10 (T1/T2 boundary line)
//   %C2H4 = 50 (T2/T3 and DT boundary line)
//   %CH4  = 98 (PD boundary)
//
// All zone vertices listed counter-clockwise for consistent winding:

// ─── Duval Triangle 1 — Exact Standard IEC 60599 / IEEE C57.104 ─────────────
//
// Equilateral Triangle standard orientation (matching Duval 2010 / IEC 60599):
//   Top Apex:         100% CH4  (0% C2H4, 0% C2H2)
//   Bottom-Right:     100% C2H4 (0% CH4,  0% C2H2)
//   Bottom-Left:      100% C2H2 (0% CH4,  0% C2H4)
//
// Axes:
//   Left edge:   %CH4 increases from 0% at Bottom-Left to 100% at Top Apex (arrow ↑)
//   Right edge:  %C2H4 increases from 0% at Top Apex to 100% at Bottom-Right (arrow ↓)
//   Bottom edge: %C2H2 increases from 0% at Bottom-Right to 100% at Bottom-Left (arrow ←)
//
// Coordinates in polygons are [ %CH4, %C2H4, %C2H2 ] (sum always 100.0%).
// Polygons form a mathematically exact partition (zero overlap, zero gap).

const DUVAL_ZONES = [
  {
    id: 'PD',
    label: 'PD',
    fullLabel: 'Partial Discharge (Corona)',
    color: '#2563eb', // Royal Blue (top apex)
    textColor: '#ffffff',
    points: [
      [100, 0, 0],
      [98, 2, 0],
      [98, 0, 2],
    ],
  },
  {
    id: 'T1',
    label: 'T1',
    fullLabel: 'Thermal fault < 300°C',
    color: '#f472b6', // Light Pink / Rose (upper right)
    textColor: '#831843',
    points: [
      [98, 2, 0],
      [80, 20, 0],
      [76, 20, 4],
      [96, 0, 4],
      [98, 0, 2],
    ],
  },
  {
    id: 'T2',
    label: 'T2',
    fullLabel: 'Thermal fault 300–700°C',
    color: '#fb7185', // Coral / Salmon (middle right)
    textColor: '#881337',
    points: [
      [80, 20, 0],
      [50, 50, 0],
      [46, 50, 4],
      [76, 20, 4],
    ],
  },
  {
    id: 'T3',
    label: 'T3',
    fullLabel: 'Thermal fault > 700°C',
    color: '#be185d', // Deep Crimson / Magenta (bottom right)
    textColor: '#ffffff',
    points: [
      [50, 50, 0],
      [0, 100, 0],
      [0, 85, 15],
      [35, 50, 15],
    ],
  },
  {
    id: 'DT',
    label: 'DT',
    fullLabel: 'Electrical & thermal fault',
    color: '#1e40af', // Dark Navy Blue (central zigzag)
    textColor: '#ffffff',
    points: [
      [96, 0, 4],
      [46, 50, 4],
      [35, 50, 15],
      [0, 85, 15],
      [0, 71, 29],
      [31, 40, 29],
      [47, 40, 13],
      [87, 0, 13],
    ],
  },
  {
    id: 'D2',
    label: 'D2',
    fullLabel: 'Discharge of high energy (Arcing)',
    color: '#06b6d4', // Bright Cyan / Turquoise (middle bottom)
    textColor: '#083344',
    points: [
      [47, 40, 13],
      [31, 40, 29],
      [0, 71, 29],
      [0, 23, 77],
      [64, 23, 13],
    ],
  },
  {
    id: 'D1',
    label: 'D1',
    fullLabel: 'Discharge of low energy (Sparking)',
    color: '#7dd3fc', // Sky Blue (left sector)
    textColor: '#0369a1',
    points: [
      [98, 0, 2],
      [96, 0, 4],
      [87, 0, 13],
      [64, 23, 13],
      [0, 23, 77],
      [0, 0, 100],
    ],
  },
]

// ─── Utility: ternary → SVG Cartesian (equilateral triangle) ─────────────────

const TRI_W = 640
const TRI_PAD_X = 75
const TRI_PAD_TOP = 65
const TRI_BASE = TRI_W - 2 * TRI_PAD_X // 490px
const TRI_H_EQUIL = (TRI_BASE * Math.sqrt(3)) / 2 // ~424.35px
const TRI_H = Math.round(TRI_PAD_TOP + TRI_H_EQUIL + 65) // ~554px

// Three vertices of equilateral triangle in SVG space:
const V_CH4  = { x: TRI_W / 2,            y: TRI_PAD_TOP }                 // Top Apex: 100% CH4
const V_C2H4 = { x: TRI_W - TRI_PAD_X,    y: TRI_PAD_TOP + TRI_H_EQUIL }   // Bottom-Right: 100% C2H4
const V_C2H2 = { x: TRI_PAD_X,            y: TRI_PAD_TOP + TRI_H_EQUIL }   // Bottom-Left: 100% C2H2

function ternaryToSvg(pch4, pc2h4, pc2h2) {
  const total = (pch4 || 0) + (pc2h4 || 0) + (pc2h2 || 0) || 1
  const u = pch4 / total   // fraction CH4
  const v = pc2h4 / total  // fraction C2H4
  const w = pc2h2 / total  // fraction C2H2

  return {
    x: u * V_CH4.x + v * V_C2H4.x + w * V_C2H2.x,
    y: u * V_CH4.y + v * V_C2H4.y + w * V_C2H2.y,
  }
}

function zonePolygonPoints(zone) {
  return zone.points.map(([ch4, c2h4, c2h2]) => {
    const { x, y } = ternaryToSvg(ch4, c2h4, c2h2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

// ─── Duval Triangle Component ─────────────────────────────────────────────────

function DuvalTriangle({ gases, transformerName, duvalDiag, history = [] }) {
  const [hoveredZone, setHoveredZone] = useState(null)
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const [showGrid, setShowGrid] = useState(true)
  const [showHistory, setShowHistory] = useState(true)
  const svgRef = useRef(null)

  // Current gas readings
  const ch4raw  = gases?.CH4  ?? 0
  const c2h4raw = gases?.C2H4 ?? 0
  const c2h2raw = gases?.C2H2 ?? 0
  const gasSum  = ch4raw + c2h4raw + c2h2raw

  const pch4  = gasSum > 0 ? (ch4raw  / gasSum) * 100 : 0
  const pc2h4 = gasSum > 0 ? (c2h4raw / gasSum) * 100 : 0
  const pc2h2 = gasSum > 0 ? (c2h2raw / gasSum) * 100 : 0

  const activePoint = gasSum > 0 ? ternaryToSvg(pch4, pc2h4, pc2h2) : null

  // Historical trajectory points
  const historyPoints = (history || [])
    .filter((h) => {
      const sum = (h.CH4 || 0) + (h.C2H4 || 0) + (h.C2H2 || 0)
      return sum > 0
    })
    .sort((a, b) => (a.date > b.date ? 1 : -1))
    .map((h) => {
      const tot = (h.CH4 || 0) + (h.C2H4 || 0) + (h.C2H2 || 0)
      const pCH4 = ((h.CH4 || 0) / tot) * 100
      const pC2H4 = ((h.C2H4 || 0) / tot) * 100
      const pC2H2 = ((h.C2H2 || 0) / tot) * 100
      const pos = ternaryToSvg(pCH4, pC2H4, pC2H2)
      return { ...h, pos, pCH4, pC2H4, pC2H2 }
    })

  const triPointsStr = `${V_CH4.x},${V_CH4.y} ${V_C2H4.x},${V_C2H4.y} ${V_C2H2.x},${V_C2H2.y}`

  // Grid lines parallel to all three sides at 20%, 40%, 60%, 80%
  const gridLines = []
  for (const pct of [20, 40, 60, 80]) {
    // 1. Constant CH4 line (horizontal, parallel to base)
    const ch4_left = ternaryToSvg(pct, 0, 100 - pct)
    const ch4_right = ternaryToSvg(pct, 100 - pct, 0)
    gridLines.push({ x1: ch4_left.x, y1: ch4_left.y, x2: ch4_right.x, y2: ch4_right.y, axis: 'CH4' })

    // 2. Constant C2H4 line (parallel to left edge)
    const c2h4_bot = ternaryToSvg(0, pct, 100 - pct)
    const c2h4_right = ternaryToSvg(100 - pct, pct, 0)
    gridLines.push({ x1: c2h4_bot.x, y1: c2h4_bot.y, x2: c2h4_right.x, y2: c2h4_right.y, axis: 'C2H4' })

    // 3. Constant C2H2 line (parallel to right edge)
    const c2h2_bot = ternaryToSvg(0, 100 - pct, pct)
    const c2h2_left = ternaryToSvg(100 - pct, 0, pct)
    gridLines.push({ x1: c2h2_bot.x, y1: c2h2_bot.y, x2: c2h2_left.x, y2: c2h2_left.y, axis: 'C2H2' })
  }

  // Axis ticks calculation
  const leftTicks = [20, 40, 60, 80].map((p) => {
    const pt = ternaryToSvg(p, 0, 100 - p)
    return { p, x: pt.x, y: pt.y }
  })

  const rightTicks = [20, 40, 60, 80].map((p) => {
    const pt = ternaryToSvg(100 - p, p, 0)
    return { p, x: pt.x, y: pt.y }
  })

  const bottomTicks = [20, 40, 60, 80].map((p) => {
    const pt = ternaryToSvg(0, 100 - p, p)
    return { p, x: pt.x, y: pt.y }
  })

  return (
    <div className="chart-container">
      <div className="chart-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Triangle size={18} />
          <span style={{ fontWeight: 600 }}>Segitiga Duval 1 (IEC 60599 / IEEE C57.104)</span>
          {duvalDiag && duvalDiag !== '—' && (
            <span className="duval-diag-pill">{duvalDiag}</span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: '0.78rem' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
            <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />
            <span>Grid Kisi</span>
          </label>
          {historyPoints.length > 1 && (
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
              <input type="checkbox" checked={showHistory} onChange={(e) => setShowHistory(e.target.checked)} />
              <span>Tren Trajectory ({historyPoints.length} titik)</span>
            </label>
          )}
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${TRI_W} ${TRI_H}`}
        className="duval-svg"
        role="img"
        aria-label={`Segitiga Duval untuk ${transformerName}`}
        style={{ width: '100%', height: 'auto', background: 'var(--surface)', borderRadius: 10 }}
      >
        <defs>
          <clipPath id="tri-main-clip">
            <polygon points={triPointsStr} />
          </clipPath>
          {/* Arrow marker for history path */}
          <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
            <polygon points="0 0, 6 3, 0 6" fill="#475569" />
          </marker>
        </defs>

        {/* 1. FAULT ZONE POLYGONS (100% full coverage, no gaps) */}
        <g clipPath="url(#tri-main-clip)">
          {DUVAL_ZONES.map((zone) => {
            const isHov = hoveredZone === zone.id
            return (
              <polygon
                key={zone.id}
                points={zonePolygonPoints(zone)}
                fill={zone.color}
                fillOpacity={isHov ? 0.95 : 0.82}
                stroke="#ffffff"
                strokeWidth={1.2}
                strokeOpacity={0.8}
                style={{ cursor: 'pointer', transition: 'fill-opacity 0.15s ease' }}
                onMouseEnter={() => setHoveredZone(zone.id)}
                onMouseLeave={() => setHoveredZone(null)}
              />
            )
          })}
        </g>

        {/* 2. OPTIONAL GRID LINES */}
        {showGrid && (
          <g clipPath="url(#tri-main-clip)" opacity={0.4}>
            {gridLines.map((line, i) => (
              <line
                key={i}
                x1={line.x1} y1={line.y1}
                x2={line.x2} y2={line.y2}
                stroke="#ffffff"
                strokeWidth={0.7}
                strokeDasharray="3 3"
              />
            ))}
          </g>
        )}

        {/* 3. TRIANGLE OUTER BORDER */}
        <polygon
          points={triPointsStr}
          fill="none"
          stroke="#0f172a"
          strokeWidth={2.5}
        />

        {/* 4. ZONE IDENTIFIER LABELS ON CHART */}
        {/* PD at apex */}
        <text x={V_CH4.x} y={V_CH4.y - 12} textAnchor="middle" style={{ fontSize: 13, fontWeight: 800, fill: '#1e40af' }}>
          (PD)
        </text>
        {/* T1 beside right edge */}
        <text x={385} y={130} textAnchor="middle" style={{ fontSize: 11, fontWeight: 800, fill: '#831843' }}>
          (T1)
        </text>
        {/* T2 beside right edge */}
        <text x={470} y={245} textAnchor="middle" style={{ fontSize: 11, fontWeight: 800, fill: '#881337' }}>
          (T2)
        </text>
        {/* T3 inside zone */}
        <text x={470} y={425} textAnchor="middle" style={{ fontSize: 15, fontWeight: 800, fill: '#ffffff', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}>
          T3
        </text>
        {/* DT inside zigzag */}
        <text x={385} y={325} textAnchor="middle" style={{ fontSize: 14, fontWeight: 800, fill: '#ffffff', textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}>
          DT
        </text>
        {/* D2 inside cyan zone */}
        <text x={330} y={420} textAnchor="middle" style={{ fontSize: 15, fontWeight: 800, fill: '#083344' }}>
          D2
        </text>
        {/* D1 inside light blue zone */}
        <text x={220} y={290} textAnchor="middle" style={{ fontSize: 16, fontWeight: 800, fill: '#0369a1' }}>
          D1
        </text>

        {/* 5. AXIS TICKS AND LABELS */}
        {/* LEFT AXIS: % CH4 (increases from bottom-left to top apex) */}
        {leftTicks.map(({ p, x, y }) => (
          <g key={`l-${p}`}>
            {/* Tick mark pointing up-left */}
            <line x1={x} y1={y} x2={x - 6} y2={y - 3.5} stroke="#334155" strokeWidth={1.5} />
            <text x={x - 12} y={y + 3} textAnchor="end" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
              {p}
            </text>
          </g>
        ))}
        {/* Left edge title */}
        <text
          x={(V_CH4.x + V_C2H2.x) / 2 - 38}
          y={(V_CH4.y + V_C2H2.y) / 2}
          textAnchor="middle"
          style={{ fontSize: 13, fontWeight: 700, fill: 'var(--ink)' }}
          transform={`rotate(-60, ${(V_CH4.x + V_C2H2.x) / 2 - 38}, ${(V_CH4.y + V_C2H2.y) / 2})`}
        >
          % CH₄ →
        </text>

        {/* RIGHT AXIS: % C2H4 (increases from top apex to bottom-right) */}
        {rightTicks.map(({ p, x, y }) => (
          <g key={`r-${p}`}>
            <line x1={x} y1={y} x2={x + 6} y2={y - 3.5} stroke="#334155" strokeWidth={1.5} />
            <text x={x + 12} y={y + 3} textAnchor="start" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
              {p}
            </text>
          </g>
        ))}
        {/* Right edge title */}
        <text
          x={(V_CH4.x + V_C2H4.x) / 2 + 38}
          y={(V_CH4.y + V_C2H4.y) / 2}
          textAnchor="middle"
          style={{ fontSize: 13, fontWeight: 700, fill: 'var(--ink)' }}
          transform={`rotate(60, ${(V_CH4.x + V_C2H4.x) / 2 + 38}, ${(V_CH4.y + V_C2H4.y) / 2})`}
        >
          % C₂H₄ →
        </text>

        {/* BOTTOM AXIS: % C2H2 (increases from bottom-right to bottom-left) */}
        {bottomTicks.map(({ p, x, y }) => (
          <g key={`b-${p}`}>
            <line x1={x} y1={y} x2={x} y2={y + 6} stroke="#334155" strokeWidth={1.5} />
            <text x={x} y={y + 18} textAnchor="middle" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
              {p}
            </text>
          </g>
        ))}
        {/* Bottom edge title */}
        <text
          x={(V_C2H2.x + V_C2H4.x) / 2}
          y={V_C2H2.y + 36}
          textAnchor="middle"
          style={{ fontSize: 13, fontWeight: 700, fill: 'var(--ink)' }}
        >
          ← % C₂H₂
        </text>

        {/* Vertex 100% Labels */}
        <text x={V_CH4.x - 18} y={V_CH4.y - 12} textAnchor="end" style={{ fontSize: 11, fontWeight: 700, fill: 'var(--muted)' }}>
          100%
        </text>
        <text x={V_C2H4.x + 10} y={V_C2H4.y + 18} textAnchor="start" style={{ fontSize: 11, fontWeight: 700, fill: 'var(--muted)' }}>
          100% C₂H₄
        </text>
        <text x={V_C2H2.x - 10} y={V_C2H2.y + 18} textAnchor="end" style={{ fontSize: 11, fontWeight: 700, fill: 'var(--muted)' }}>
          100% C₂H₂
        </text>

        {/* 6. HISTORICAL TRAJECTORY LINE & POINTS (Image 1 & 2 feature) */}
        {showHistory && historyPoints.length > 1 && (
          <g>
            {/* Trajectory polyline */}
            <polyline
              points={historyPoints.map((h) => `${h.pos.x.toFixed(1)},${h.pos.y.toFixed(1)}`).join(' ')}
              fill="none"
              stroke="#0f172a"
              strokeWidth={1.8}
              strokeDasharray="4 2"
              markerMid="url(#arrowhead)"
            />
            {/* History point markers */}
            {historyPoints.slice(0, -1).map((h, i) => (
              <circle
                key={i}
                cx={h.pos.x} cy={h.pos.y}
                r={4}
                fill="#f59e0b"
                stroke="#0f172a"
                strokeWidth={1.5}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredPoint(h)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            ))}
          </g>
        )}

        {/* 7. LATEST DATA POINT — PROMINENT TARGET MARKER */}
        {activePoint && (
          <g style={{ cursor: 'pointer' }} onMouseEnter={() => setHoveredPoint({ date: 'Terbaru', pCH4: pch4, pC2H4: pc2h4, pC2H2: pc2h2, CH4: ch4raw, C2H4: c2h4raw, C2H2: c2h2raw })} onMouseLeave={() => setHoveredPoint(null)}>
            {/* Horizontal guide line (Image 2 style) */}
            <line
              x1={ternaryToSvg(pch4, 0, 100 - pch4).x}
              y1={activePoint.y}
              x2={ternaryToSvg(pch4, 100 - pch4, 0).x}
              y2={activePoint.y}
              stroke="#f43f5e"
              strokeWidth={1.2}
              strokeDasharray="4 3"
              opacity={0.85}
            />
            {/* Outer halo */}
            <circle cx={activePoint.x} cy={activePoint.y} r={16} fill="#f43f5e" fillOpacity={0.2} />
            {/* Inner ring */}
            <circle cx={activePoint.x} cy={activePoint.y} r={7.5} fill="#f43f5e" stroke="#ffffff" strokeWidth={2} />
            {/* Center dot */}
            <circle cx={activePoint.x} cy={activePoint.y} r={2.5} fill="#ffffff" />
          </g>
        )}

        {/* 8. FLOATING INTERACTIVE HOVER BOX */}
        {hoveredPoint && (
          <g>
            <rect
              x={Math.min(hoveredPoint.pos ? hoveredPoint.pos.x + 12 : activePoint.x + 12, TRI_W - 175)}
              y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 65 : activePoint.y - 65), 10)}
              width={165}
              height={85}
              rx={6}
              fill="#0f172a"
              fillOpacity={0.92}
              stroke="#475569"
              strokeWidth={1}
            />
            <text x={Math.min(hoveredPoint.pos ? hoveredPoint.pos.x + 20 : activePoint.x + 20, TRI_W - 165)} y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 45 : activePoint.y - 45), 30)} fill="#ffffff" style={{ fontSize: 11, fontWeight: 700 }}>
              {hoveredPoint.date || 'Sampel DGA'}
            </text>
            <text x={Math.min(hoveredPoint.pos ? hoveredPoint.pos.x + 20 : activePoint.x + 20, TRI_W - 165)} y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 30 : activePoint.y - 30), 45)} fill="#94a3b8" style={{ fontSize: 10 }}>
              %CH₄: {hoveredPoint.pCH4.toFixed(1)}% | {hoveredPoint.CH4 ?? ch4raw} ppm
            </text>
            <text x={Math.min(hoveredPoint.pos ? hoveredPoint.pos.x + 20 : activePoint.x + 20, TRI_W - 165)} y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 16 : activePoint.y - 16), 59)} fill="#94a3b8" style={{ fontSize: 10 }}>
              %C₂H₄: {hoveredPoint.pC2H4.toFixed(1)}% | {hoveredPoint.C2H4 ?? c2h4raw} ppm
            </text>
            <text x={Math.min(hoveredPoint.pos ? hoveredPoint.pos.x + 20 : activePoint.x + 20, TRI_W - 165)} y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 2 : activePoint.y - 2), 73)} fill="#94a3b8" style={{ fontSize: 10 }}>
              %C₂H₂: {hoveredPoint.pC2H2.toFixed(1)}% | {hoveredPoint.C2H2 ?? c2h2raw} ppm
            </text>
          </g>
        )}

        {/* No data overlay */}
        {gasSum === 0 && (
          <text x={TRI_W / 2} y={TRI_H / 2} className="duval-axis-label" textAnchor="middle" fill="var(--muted)" opacity={0.6}>
            (Pilih transformer dengan data gas aktif)
          </text>
        )}
      </svg>

      {/* 9. LEGEND WITH ZONE HIGHLIGHTS */}
      <div className="duval-legend">
        {DUVAL_ZONES.map((zone) => (
          <span
            key={zone.id}
            className={`duval-legend-item ${hoveredZone === zone.id ? 'duval-legend-item--active' : ''}`}
            onMouseEnter={() => setHoveredZone(zone.id)}
            onMouseLeave={() => setHoveredZone(null)}
            style={{ cursor: 'pointer' }}
          >
            <i style={{ background: zone.color, border: '1px solid rgba(0,0,0,0.15)' }} />
            <strong>{zone.id}</strong>
            <span>{zone.fullLabel}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

// ─── Duval Tab ────────────────────────────────────────────────────────────────

function DuvalTab() {
  const [transformers, setTransformers] = useState([])
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const controller = new AbortController()
    getDgaTransformers(controller.signal)
      .then((res) => {
        const list = res.transformers ?? []
        setTransformers(list)
        if (list.length > 0) setSelected(list[0].transformer_id)
        setStatus('ready')
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setStatus('error')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selected) return
    const controller = new AbortController()
    setDetail(null)
    getDgaTransformerDetail(selected, controller.signal)
      .then((res) => setDetail(res))
      .catch(() => {})
    return () => controller.abort()
  }, [selected])

  const gases = detail?.gases ?? {}
  const diagnosis = detail?.duval_diag ?? detail?.diagnosis?.duval ?? '—'
  const tdcg = detail?.tdcg
  const statusLabel = detail?.status ?? '—'

  return (
    <div className="cbm-tab-content">
      <div className="cbm-controls">
        <label htmlFor="transformer-select" className="cbm-control-label">Transformer</label>
        <select
          id="transformer-select"
          className="cbm-select"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          disabled={status !== 'ready'}
        >
          {transformers.map((t) => (
            <option key={t.transformer_id} value={t.transformer_id}>
              {t.name || t.transformer_id} ({t.unit})
            </option>
          ))}
        </select>

        {detail && (
          <div className="cbm-badges">
            <span className={`cbm-badge cbm-badge--${(statusLabel || '').toLowerCase().includes('normal') ? 'ok' : 'warn'}`}>
              {statusLabel}
            </span>
            {tdcg != null && <span className="cbm-badge cbm-badge--neutral">TDCG: {tdcg.toFixed(0)} ppm</span>}
            {diagnosis !== '—' && <span className="cbm-badge cbm-badge--info">Duval: {diagnosis}</span>}
          </div>
        )}
      </div>

      {status === 'error' && (
        <div className="notice notice--error">
          <strong>Data DGA tidak dapat dimuat.</strong>
          <span>Pastikan FastAPI berjalan di port 8000.</span>
        </div>
      )}

      <DuvalTriangle
        gases={gases}
        transformerName={detail?.name ?? selected}
        duvalDiag={diagnosis}
        history={detail?.history}
      />

      {detail && (
        <div className="cbm-gas-grid">
          {['H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO', 'CO2'].map((gas) => {
            const val = gases[gas]
            return val != null ? (
              <div key={gas} className="cbm-gas-card">
                <span className="cbm-gas-name">{gas}</span>
                <strong className="cbm-gas-value">{val.toFixed(1)}</strong>
                <span className="cbm-gas-unit">ppm</span>
              </div>
            ) : null
          })}
        </div>
      )}
    </div>
  )
}

// ─── Vibration Parameters Chart ────────────────────────────────────────────

function VibrationBarChart({ measurements, paramKey, label, unit, thresholds }) {
  if (!measurements.length) return null

  const values = measurements.map((m) => ({ equipment: m.equipment, val: parseFloat(m[paramKey] ?? 0) }))
    .filter((v) => !Number.isNaN(v.val) && v.val > 0)

  if (!values.length) return null

  const maxVal = Math.max(...values.map((v) => v.val), thresholds?.critical ?? 1)
  const W = 600
  const H = 240
  const padLeft = 60
  const padRight = 20
  const padTop = 20
  const padBottom = 60
  const barW = Math.max(20, Math.floor((W - padLeft - padRight) / values.length - 6))

  function barColor(val) {
    if (thresholds?.critical && val >= thresholds.critical) return '#ef4444'
    if (thresholds?.warning && val >= thresholds.warning) return '#f59e0b'
    return '#3b82f6'
  }

  function yPos(val) {
    return padTop + (1 - val / maxVal) * (H - padTop - padBottom)
  }

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ frac: f, val: (maxVal * f).toFixed(1) }))

  return (
    <div className="chart-container chart-container--bar">
      <div className="chart-title"><BarChart2 size={16} /><span>{label}</span></div>
      <svg viewBox={`0 0 ${W} ${H}`} className="bar-svg">
        {/* Grid + Y axis ticks */}
        {ticks.map(({ frac, val: tickVal }) => {
          const y = yPos(maxVal * frac)
          return (
            <g key={frac}>
              <line x1={padLeft} y1={y} x2={W - padRight} y2={y} stroke="var(--border)" strokeDasharray="4 4" strokeWidth={0.8} />
              <text x={padLeft - 6} y={y + 4} className="chart-tick-label" textAnchor="end">{tickVal}</text>
            </g>
          )
        })}

        {/* Threshold lines */}
        {thresholds?.warning && (
          <line x1={padLeft} y1={yPos(thresholds.warning)} x2={W - padRight} y2={yPos(thresholds.warning)}
            stroke="#f59e0b" strokeDasharray="6 3" strokeWidth={1.5} />
        )}
        {thresholds?.critical && (
          <line x1={padLeft} y1={yPos(thresholds.critical)} x2={W - padRight} y2={yPos(thresholds.critical)}
            stroke="#ef4444" strokeDasharray="6 3" strokeWidth={1.5} />
        )}

        {/* Bars */}
        {values.map(({ equipment, val }, i) => {
          const x = padLeft + i * ((W - padLeft - padRight) / values.length) + 4
          const y = yPos(val)
          const barH = H - padBottom - y
          return (
            <g key={equipment}>
              <rect x={x} y={y} width={barW} height={Math.max(barH, 2)} fill={barColor(val)} rx={3} fillOpacity={0.85} />
              <text x={x + barW / 2} y={H - padBottom + 14} className="chart-bar-label" textAnchor="middle">
                {equipment.length > 8 ? `${equipment.slice(0, 8)}…` : equipment}
              </text>
              <text x={x + barW / 2} y={y - 4} className="chart-bar-value" textAnchor="middle">{val.toFixed(2)}</text>
            </g>
          )
        })}

        {/* Y axis label */}
        <text x={14} y={H / 2} className="chart-axis-label" textAnchor="middle"
          transform={`rotate(-90, 14, ${H / 2})`}>{unit}</text>

        {/* X axis base line */}
        <line x1={padLeft} y1={H - padBottom} x2={W - padRight} y2={H - padBottom} stroke="var(--border)" strokeWidth={1} />
      </svg>
    </div>
  )
}

function VibrationTab() {
  const [measurements, setMeasurements] = useState([])
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const controller = new AbortController()
    getDomainMeasurements('VIBRASI', { limit: 200 }, controller.signal)
      .then((res) => {
        setMeasurements(res.measurements ?? [])
        setStatus('ready')
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setStatus('error')
      })
    return () => controller.abort()
  }, [])

  // Aggregate to latest per equipment
  const latest = {}
  for (const m of measurements) {
    if (!latest[m.equipment] || m.test_date > latest[m.equipment].test_date) {
      latest[m.equipment] = m
    }
  }
  const rows = Object.values(latest)

  return (
    <div className="cbm-tab-content">
      {status === 'error' && (
        <div className="notice notice--error">
          <strong>Data vibrasi tidak dapat dimuat.</strong>
          <span>Pastikan FastAPI berjalan dan domain VIBRASI sudah di-ingest.</span>
        </div>
      )}

      {status === 'loading' && (
        <div className="chart-loading"><RefreshCw size={20} className="spin" />Memuat data vibrasi…</div>
      )}

      {status === 'ready' && rows.length === 0 && (
        <div className="chart-empty">
          <Activity size={32} />
          <strong>Belum ada data vibrasi</strong>
          <span>Upload data melalui Streamlit atau halaman Data &rarr; domain VIBRASI.</span>
        </div>
      )}

      {rows.length > 0 && (
        <>
          <VibrationBarChart
            measurements={rows}
            paramKey="velocity_overall"
            label="Kecepatan Vibrasi Overall RMS"
            unit="mm/s"
            thresholds={{ warning: 4.5, critical: 11.2 }}
          />
          <VibrationBarChart
            measurements={rows}
            paramKey="displacement_pp"
            label="Displacement Peak-to-Peak"
            unit="µm"
            thresholds={{ warning: 100, critical: 200 }}
          />
          <VibrationBarChart
            measurements={rows}
            paramKey="acceleration_peak"
            label="Akselerasi Peak"
            unit="g"
            thresholds={{ warning: 2.0, critical: 5.0 }}
          />
        </>
      )}
    </div>
  )
}

// ─── Trend Chart ──────────────────────────────────────────────────────────────

function TrendSvg({ series, label }) {
  // series: [{domain, color, points: [{date, value}]}]
  const W = 700
  const H = 260
  const padLeft = 60
  const padRight = 20
  const padTop = 20
  const padBottom = 50

  const allPoints = series.flatMap((s) => s.points)
  if (!allPoints.length) return null

  const dates = allPoints.map((p) => p.date).sort()
  const minDate = new Date(dates[0]).getTime()
  const maxDate = new Date(dates.at(-1)).getTime()
  const dateRange = maxDate - minDate || 1

  const maxVal = 100 // health index 0–100

  function xPos(dateStr) {
    const t = new Date(dateStr).getTime()
    return padLeft + ((t - minDate) / dateRange) * (W - padLeft - padRight)
  }

  function yPos(val) {
    return padTop + (1 - val / maxVal) * (H - padTop - padBottom)
  }

  // X axis ticks — up to 6 evenly spaced dates
  const uniqueDates = [...new Set(dates)].sort()
  const tickStep = Math.max(1, Math.floor(uniqueDates.length / 6))
  const xTicks = uniqueDates.filter((_, i) => i % tickStep === 0 || i === uniqueDates.length - 1)

  // Y axis ticks: 0, 25, 50, 70 (warn), 75, 100
  const yTicks = [0, 25, 50, 75, 100]

  return (
    <div className="chart-container">
      <div className="chart-title"><TrendingUp size={16} /><span>{label}</span></div>
      <svg viewBox={`0 0 ${W} ${H}`} className="trend-svg">
        {/* Grid lines */}
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={padLeft} y1={yPos(v)} x2={W - padRight} y2={yPos(v)}
              stroke={v === 70 || v === 40 ? '#f59e0b' : 'var(--border)'}
              strokeDasharray={v === 70 || v === 40 ? '6 3' : '4 4'}
              strokeWidth={v === 70 || v === 40 ? 1.5 : 0.8}
              opacity={v === 70 || v === 40 ? 0.8 : 0.5}
            />
            <text x={padLeft - 6} y={yPos(v) + 4} className="chart-tick-label" textAnchor="end">{v}</text>
          </g>
        ))}

        {/* Threshold labels */}
        <text x={W - padRight} y={yPos(70) - 4} className="chart-threshold-label" textAnchor="end">Perhatian</text>
        <text x={W - padRight} y={yPos(40) - 4} className="chart-threshold-label chart-threshold-label--critical" textAnchor="end">Kritis</text>
        <line x1={padLeft} y1={yPos(40)} x2={W - padRight} y2={yPos(40)}
          stroke="#ef4444" strokeDasharray="6 3" strokeWidth={1.5} opacity={0.7} />

        {/* Series lines */}
        {series.map((s) => {
          if (!s.points.length) return null
          const sorted = [...s.points].sort((a, b) => a.date.localeCompare(b.date))
          const d = sorted.map((p, i) =>
            `${i === 0 ? 'M' : 'L'}${xPos(p.date).toFixed(1)},${yPos(p.value).toFixed(1)}`
          ).join(' ')
          return (
            <g key={s.domain}>
              <path d={d} fill="none" stroke={s.color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
              {sorted.map((p) => (
                <circle key={p.date} cx={xPos(p.date)} cy={yPos(p.value)} r={4}
                  fill={s.color} stroke="var(--surface)" strokeWidth={1.5} />
              ))}
            </g>
          )
        })}

        {/* X axis ticks */}
        {xTicks.map((d) => (
          <text key={d} x={xPos(d)} y={H - padBottom + 16} className="chart-tick-label" textAnchor="middle">
            {d.slice(0, 10)}
          </text>
        ))}

        {/* Axes */}
        <line x1={padLeft} y1={padTop} x2={padLeft} y2={H - padBottom} stroke="var(--border)" strokeWidth={1} />
        <line x1={padLeft} y1={H - padBottom} x2={W - padRight} y2={H - padBottom} stroke="var(--border)" strokeWidth={1} />

        {/* Y label */}
        <text x={14} y={H / 2} className="chart-axis-label" textAnchor="middle"
          transform={`rotate(-90, 14, ${H / 2})`}>Health Index</text>
      </svg>
    </div>
  )
}

function TrendTab() {
  const [domains, setDomains] = useState([])
  const [equipment, setEquipment] = useState('')
  const [series, setSeries] = useState([])
  const [allEquipment, setAllEquipment] = useState([])
  const [loadStatus, setLoadStatus] = useState('loading')

  // Load domain list
  useEffect(() => {
    const controller = new AbortController()
    getDomains(controller.signal)
      .then((res) => {
        setDomains((res.domains ?? []).map((d) => d.domain))
        setLoadStatus('ready')
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setLoadStatus('error')
      })
    return () => controller.abort()
  }, [])

  // Load measurements for each domain when equipment changes
  const loadTrends = useCallback((selectedEquipment, domainList) => {
    if (!domainList.length) return
    setSeries([])
    Promise.allSettled(
      domainList.map((domain) =>
        getDomainMeasurements(domain, { equipment: selectedEquipment || undefined, limit: 100 })
          .then((res) => ({ domain, measurements: res.measurements ?? [] }))
      )
    ).then((results) => {
      const newSeries = []
      for (const result of results) {
        if (result.status !== 'fulfilled') continue
        const { domain, measurements } = result.value
        // Extract health_index or derive from status
        const points = measurements
          .filter((m) => m.test_date)
          .map((m) => {
            const hi = parseFloat(m.health_index ?? m.indeks_kesehatan ?? m.health_score ?? 0)
            return { date: String(m.test_date).slice(0, 10), value: Number.isNaN(hi) ? 0 : Math.min(100, Math.max(0, hi)) }
          })
          .filter((p) => p.value > 0)
        if (points.length > 0) {
          newSeries.push({ domain, color: DOMAIN_COLORS[domain] ?? '#94a3b8', points })
        }
        // Collect equipment names
        for (const m of measurements) {
          if (m.equipment && !allEquipment.includes(m.equipment)) {
            setAllEquipment((prev) => prev.includes(m.equipment) ? prev : [...prev, m.equipment])
          }
        }
      }
      setSeries(newSeries)
    })
  }, [allEquipment])

  useEffect(() => {
    if (loadStatus === 'ready' && domains.length > 0) {
      loadTrends(equipment, domains)
    }
  }, [loadStatus, domains, equipment, loadTrends])

  return (
    <div className="cbm-tab-content">
      <div className="cbm-controls">
        <label htmlFor="trend-equipment-select" className="cbm-control-label">Filter Equipment</label>
        <select
          id="trend-equipment-select"
          className="cbm-select"
          value={equipment}
          onChange={(e) => setEquipment(e.target.value)}
        >
          <option value="">Semua equipment</option>
          {allEquipment.map((eq) => <option key={eq} value={eq}>{eq}</option>)}
        </select>

        {/* Domain color legend */}
        <div className="cbm-badges">
          {Object.entries(DOMAIN_COLORS).map(([domain, color]) => (
            <span key={domain} className="cbm-domain-pill" style={{ '--pill-color': color }}>
              {domain}
            </span>
          ))}
        </div>
      </div>

      {loadStatus === 'error' && (
        <div className="notice notice--error">
          <strong>Data domain tidak dapat dimuat.</strong>
          <span>Pastikan FastAPI berjalan di port 8000.</span>
        </div>
      )}

      {loadStatus === 'loading' && (
        <div className="chart-loading"><RefreshCw size={20} className="spin" />Memuat domain…</div>
      )}

      {loadStatus === 'ready' && series.length === 0 && (
        <div className="chart-empty">
          <TrendingUp size={32} />
          <strong>Belum ada data tren</strong>
          <span>Upload data per domain agar health index dapat ditampilkan di sini.</span>
        </div>
      )}

      {series.length > 0 && (
        <>
          <TrendSvg series={series} label="Health Index per Domain" />
          {/* Legend */}
          <div className="trend-legend">
            {series.map((s) => (
              <span key={s.domain} className="trend-legend-item">
                <i style={{ background: s.color }} />
                {s.domain}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Main CBMDashboard ────────────────────────────────────────────────────────

export default function CBMDashboard() {
  const [activeTab, setActiveTab] = useState('duval')

  return (
    <div className="page cbm-dashboard">
      <header className="page-header">
        <div>
          <h1>Dashboard CBM</h1>
          <p>Visualisasi interaktif kondisi aset — Duval Triangle, Parameter Vibrasi, Tren Kesehatan.</p>
        </div>
        <span className="status status--healthy"><i />Grafik interaktif</span>
      </header>

      {/* Safety notice */}
      <div className="cbm-safety-banner">
        <Zap size={16} />
        <span>Semua nilai berasal dari pengukuran nyata. Rule-based thresholds per IEC 60599, ISO 10816, dan standar domain.</span>
        <AlertTriangle size={16} className="cbm-safety-warn" />
      </div>

      {/* Tab navigation */}
      <nav className="cbm-tab-bar" aria-label="Tab dashboard CBM">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`cbm-tab ${activeTab === id ? 'cbm-tab--active' : ''}`}
            onClick={() => setActiveTab(id)}
            aria-current={activeTab === id ? 'page' : undefined}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}
      </nav>

      {/* Tab panels */}
      {activeTab === 'duval' && <DuvalTab />}
      {activeTab === 'vibration' && <VibrationTab />}
      {activeTab === 'trend' && <TrendTab />}
    </div>
  )
}

