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
  Activity, AlertTriangle, BarChart2, Clock, Compass, Download,
  Flame, RefreshCw, Sliders, TrendingUp, Triangle, Zap,
} from 'lucide-react'
import {
  getDgaTransformerDetail,
  getDgaTransformers,
  getDomainMeasurements,
  getDomains,
  getMcsaEquipmentList,
  getMcsaSummary,
} from './api.js'

// ─── Constants ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'duval', label: 'DGA', icon: Triangle },
  { id: 'mcsa', label: 'MCSA & Motor', icon: Zap },
  { id: 'vibration', label: 'Parameter Vibrasi', icon: BarChart2 },
  { id: 'trend', label: 'Tren Kesehatan', icon: TrendingUp },
]


// Domain colors for trend chart lines
const DOMAIN_COLORS = {
  VIBRASI: '#3b82f6',
  DGA: '#f59e0b',
  TRIBOLOGY: '#10b981',
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
    color: '#1e40af', // Deep Royal Blue (top apex)
    textColor: '#ffffff',
    desc: 'Pelepasan muatan parsial / korona pada rongga bergas (void) atau gelembung minyak.',
    action: 'Lakukan pengujian akustik PD / UHF, periksa kadar gas H2 dan pertahankan sampling berkala.',
    labelPos: { x: 320, y: 56 },
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
    color: '#f472b6', // Soft Rose Pink (upper right)
    textColor: '#831843',
    desc: 'Gangguan termal suhu rendah (<300°C), pemanasan lokal pada konduktor atau sirkulasi minyak.',
    action: 'Periksa sistem pendingin (oil radiator & fan), pastikan pembebanan tidak melebihi kapasitas MVA.',
    labelPos: { x: 382, y: 135 },
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
    desc: 'Gangguan termal suhu menengah (300–700°C), kontak sambungan baut longgar atau kabel penghubung.',
    action: 'Lakukan thermovision pada bushing & sambungan eksternal, jadwalkan re-sampling DGA 1 bulan.',
    labelPos: { x: 465, y: 250 },
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
    desc: 'Gangguan termal suhu tinggi (>700°C), karbonisasi isolasi kertas, hotspot parah pada inti/belitan.',
    action: 'Kondisi Kritis! Pantau laju gas etilena (C2H4), rencanakan shutdown inspeksi internal & uji resistansi.',
    labelPos: { x: 465, y: 430 },
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
    color: '#2563eb', // Indigo Blue (central zigzag)
    textColor: '#ffffff',
    desc: 'Kombinasi gangguan termal dan pelepasan listrik (sparking/arcing lokal disertai panas tinggi).',
    action: 'Inspeksi switch kontak On-Load Tap Changer (OLTC) dan pantau rasio gas C2H2/C2H4.',
    labelPos: { x: 385, y: 330 },
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
    desc: 'Pelepasan busur api energi tinggi (Arcing) menembus minyak trafo, flashover antar lilitan.',
    action: 'Bahaya Tinggi! Asetilena (C2H2) terdeteksi. Segera verifikasi rele Buchholz dan siapkan uji offline.',
    labelPos: { x: 325, y: 420 },
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
    color: '#7dd3fc', // Sky Blue (left sector, exact IEC 60599 boundaries)
    textColor: '#0369a1',
    desc: 'Pelepasan percikan listrik energi rendah (Sparking), potensi elektroda mengambang atau pin isolator.',
    action: 'Lakukan pembersihan isolator, periksa pembumian netral (grounding), uji kadar air & BDV minyak.',
    labelPos: { x: 215, y: 310 },
    points: [
      [0, 0, 100],
      [0, 23, 77],
      [64, 23, 13],
      [87, 0, 13],
    ],
  },
]

// ─── Utility: ternary → SVG Cartesian (equilateral triangle) ─────────────────

const TRI_W = 640
const TRI_PAD_X = 75
const TRI_PAD_TOP = 65
const TRI_BASE = TRI_W - 2 * TRI_PAD_X // 490px
const TRI_H_EQUIL = (TRI_BASE * Math.sqrt(3)) / 2 // ~424.35px
const TRI_H = Math.round(TRI_PAD_TOP + TRI_H_EQUIL + 70) // ~559px

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

function detectDuvalZone(ch4, c2h4, c2h2) {
  const sum = (ch4 || 0) + (c2h4 || 0) + (c2h2 || 0)
  if (sum <= 0) return null
  const p_ch4 = (ch4 / sum) * 100
  const p_c2h4 = (c2h4 / sum) * 100
  const p_c2h2 = (c2h2 / sum) * 100

  if (p_ch4 >= 98) return DUVAL_ZONES.find((z) => z.id === 'PD')
  if (p_c2h2 < 4 && p_c2h4 < 20) return DUVAL_ZONES.find((z) => z.id === 'T1')
  if (p_c2h2 < 4 && p_c2h4 >= 20 && p_c2h4 < 50) return DUVAL_ZONES.find((z) => z.id === 'T2')
  if (p_c2h2 < 15 && p_c2h4 >= 50) return DUVAL_ZONES.find((z) => z.id === 'T3')
  if (p_c2h2 >= 4 && p_c2h2 < 29 && p_c2h4 >= 50) return DUVAL_ZONES.find((z) => z.id === 'DT')
  if (p_c2h2 >= 29) return DUVAL_ZONES.find((z) => z.id === 'D2')
  if (p_c2h2 >= 4 && p_c2h2 < 29) return DUVAL_ZONES.find((z) => z.id === 'D1')
  return DUVAL_ZONES.find((z) => z.id === 'T1')
}

// ─── Duval Triangle Component ─────────────────────────────────────────────────

function DuvalTriangle({ gases, transformerName, duvalDiag, history = [] }) {
  const [hoveredZone, setHoveredZone] = useState(null)
  const [selectedZone, setSelectedZone] = useState(null)
  const [hoveredPoint, setHoveredPoint] = useState(null)
  const [showGrid, setShowGrid] = useState(true)
  const [showProjections, setShowProjections] = useState(true)
  const [showHistory, setShowHistory] = useState(true)
  const svgRef = useRef(null)

  // Current gas readings
  const ch4raw  = Number(gases?.CH4 ?? 0)
  const c2h4raw = Number(gases?.C2H4 ?? 0)
  const c2h2raw = Number(gases?.C2H2 ?? 0)
  const gasSum  = ch4raw + c2h4raw + c2h2raw

  const pch4  = gasSum > 0 ? (ch4raw  / gasSum) * 100 : 0
  const pc2h4 = gasSum > 0 ? (c2h4raw / gasSum) * 100 : 0
  const pc2h2 = gasSum > 0 ? (c2h2raw / gasSum) * 100 : 0

  const activePoint = gasSum > 0 ? ternaryToSvg(pch4, pc2h4, pc2h2) : null
  const currentDetectedZone = gasSum > 0 ? detectDuvalZone(ch4raw, c2h4raw, c2h2raw) : null

  // Historical trajectory points
  const historyPoints = (history || [])
    .filter((h) => {
      const sum = Number(h.CH4 || 0) + Number(h.C2H4 || 0) + Number(h.C2H2 || 0)
      return sum > 0
    })
    .sort((a, b) => (a.date > b.date ? 1 : -1))
    .map((h, idx) => {
      const tot = Number(h.CH4 || 0) + Number(h.C2H4 || 0) + Number(h.C2H2 || 0)
      const pCH4 = (Number(h.CH4 || 0) / tot) * 100
      const pC2H4 = (Number(h.C2H4 || 0) / tot) * 100
      const pC2H2 = (Number(h.C2H2 || 0) / tot) * 100
      const pos = ternaryToSvg(pCH4, pC2H4, pC2H2)
      return { ...h, pos, pCH4, pC2H4, pC2H2, stepIndex: idx + 1 }
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

  // 3-Axis Projection coordinates for active data point
  const projCH4_left = activePoint ? ternaryToSvg(pch4, 0, 100 - pch4) : null
  const projCH4_right = activePoint ? ternaryToSvg(pch4, 100 - pch4, 0) : null
  const projC2H4_top = activePoint ? ternaryToSvg(100 - pc2h4, pc2h4, 0) : null
  const projC2H4_bot = activePoint ? ternaryToSvg(0, pc2h4, 100 - pc2h4) : null
  const projC2H2_top = activePoint ? ternaryToSvg(100 - pc2h2, 0, pc2h2) : null
  const projC2H2_bot = activePoint ? ternaryToSvg(0, 100 - pc2h2, pc2h2) : null

  function handleDownloadSvg() {
    if (!svgRef.current) return
    const svgData = new XMLSerializer().serializeToString(svgRef.current)
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Duval_Triangle_1_${(transformerName || 'DGA').replace(/\s+/g, '_')}.svg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const activeZoneInfo = DUVAL_ZONES.find((z) => z.id === (hoveredZone || selectedZone || currentDetectedZone?.id))

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title" style={{ flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Triangle size={18} className="text-amber-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Segitiga Duval 1 (IEC 60599 / IEEE C57.104)</span>
          {duvalDiag && duvalDiag !== '—' && (
            <span className="duval-diag-pill">{duvalDiag}</span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.78rem', flexWrap: 'wrap' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
            <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />
            <span>Grid Kisi</span>
          </label>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
            <input type="checkbox" checked={showProjections} onChange={(e) => setShowProjections(e.target.checked)} />
            <span>Garis Proyeksi 3-Sumbu</span>
          </label>
          {historyPoints.length > 1 && (
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
              <input type="checkbox" checked={showHistory} onChange={(e) => setShowHistory(e.target.checked)} />
              <span>Trajektori ({historyPoints.length} titik)</span>
            </label>
          )}
          <button
            type="button"
            className="duval-action-btn"
            onClick={handleDownloadSvg}
            title="Unduh diagram beresolusi tinggi (SVG)"
          >
            <Download size={13} />
            <span>Unduh SVG</span>
          </button>
        </div>
      </div>

      <div className="duval-interactive-wrap">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${TRI_W} ${TRI_H}`}
          className="duval-svg"
          role="img"
          aria-label={`Segitiga Duval untuk ${transformerName}`}
          style={{ width: '100%', height: 'auto', background: 'var(--surface)', borderRadius: 12 }}
        >
          <defs>
            <clipPath id="tri-main-clip">
              <polygon points={triPointsStr} />
            </clipPath>
            {/* Arrow marker for trajectory migration path */}
            <marker id="arrowhead" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
              <polygon points="0 0, 7 3.5, 0 7" fill="var(--ink)" />
            </marker>
            {/* Glow filter for active point */}
            <filter id="glow-target" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* 1. FAULT ZONE POLYGONS (100% full coverage, zero gaps, zero overlap) */}
          <g clipPath="url(#tri-main-clip)">
            {DUVAL_ZONES.map((zone) => {
              const isHov = (hoveredZone === zone.id) || (selectedZone === zone.id)
              return (
                <polygon
                  key={zone.id}
                  points={zonePolygonPoints(zone)}
                  fill={zone.color}
                  fillOpacity={isHov ? 0.98 : 0.84}
                  stroke="#ffffff"
                  strokeWidth={isHov ? 2 : 1.2}
                  strokeOpacity={isHov ? 1.0 : 0.75}
                  style={{ cursor: 'pointer', transition: 'fill-opacity 0.15s ease, stroke-width 0.15s ease' }}
                  onMouseEnter={() => setHoveredZone(zone.id)}
                  onMouseLeave={() => setHoveredZone(null)}
                  onClick={() => setSelectedZone(selectedZone === zone.id ? null : zone.id)}
                />
              )
            })}
          </g>

          {/* 2. OPTIONAL TERNARY GRID LINES */}
          {showGrid && (
            <g clipPath="url(#tri-main-clip)" opacity={0.35}>
              {gridLines.map((line, i) => (
                <line
                  key={i}
                  x1={line.x1} y1={line.y1}
                  x2={line.x2} y2={line.y2}
                  stroke="#ffffff"
                  strokeWidth={0.8}
                  strokeDasharray="3 3"
                />
              ))}
            </g>
          )}

          {/* 3. 3-AXIS PROJECTION GUIDELINES (White dashed lines from active point to all 3 axes) */}
          {showProjections && activePoint && (
            <g clipPath="url(#tri-main-clip)" style={{ pointerEvents: 'none' }}>
              {/* Horizontal %CH4 Projection */}
              <line
                x1={projCH4_left.x} y1={activePoint.y}
                x2={projCH4_right.x} y2={activePoint.y}
                stroke="#ffffff"
                strokeWidth={1.6}
                strokeDasharray="4 3"
                strokeOpacity={0.95}
              />
              {/* Parallel %C2H4 Projection */}
              <line
                x1={projC2H4_top.x} y1={projC2H4_top.y}
                x2={projC2H4_bot.x} y2={projC2H4_bot.y}
                stroke="#ffffff"
                strokeWidth={1.6}
                strokeDasharray="4 3"
                strokeOpacity={0.95}
              />
              {/* Parallel %C2H2 Projection */}
              <line
                x1={projC2H2_top.x} y1={projC2H2_top.y}
                x2={projC2H2_bot.x} y2={projC2H2_bot.y}
                stroke="#ffffff"
                strokeWidth={1.6}
                strokeDasharray="4 3"
                strokeOpacity={0.95}
              />
            </g>
          )}

          {/* 4. TRIANGLE OUTER BORDER */}
          <polygon
            points={triPointsStr}
            fill="none"
            stroke="var(--ink)"
            strokeWidth={2.6}
          />

          {/* 5. ZONE IDENTIFIER LABELS ON CHART */}
          {DUVAL_ZONES.map((zone) => {
            const isHov = (hoveredZone === zone.id) || (selectedZone === zone.id)
            return (
              <g key={`lbl-${zone.id}`} style={{ pointerEvents: 'none' }}>
                <text
                  x={zone.labelPos.x}
                  y={zone.labelPos.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  style={{
                    fontSize: zone.id === 'PD' ? 12 : (zone.id === 'T1' || zone.id === 'T2' ? 11 : 14),
                    fontWeight: 800,
                    fill: zone.textColor,
                    textShadow: zone.textColor === '#ffffff' ? '0 1px 3px rgba(0,0,0,0.65)' : '0 1px 2px rgba(255,255,255,0.7)',
                    transform: isHov ? 'scale(1.15)' : 'scale(1)',
                    transformOrigin: `${zone.labelPos.x}px ${zone.labelPos.y}px`,
                    transition: 'transform 0.15s ease',
                  }}
                >
                  {zone.id}
                </text>
              </g>
            )
          })}

          {/* 6. AXIS TICKS AND LABELS */}
          {/* LEFT AXIS: % CH4 (increases from bottom-left to top apex) */}
          {leftTicks.map(({ p, x, y }) => (
            <g key={`l-${p}`}>
              <line x1={x} y1={y} x2={x - 6} y2={y - 3.5} stroke="var(--muted)" strokeWidth={1.5} />
              <text x={x - 11} y={y + 3} textAnchor="end" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
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
              <line x1={x} y1={y} x2={x + 6} y2={y - 3.5} stroke="var(--muted)" strokeWidth={1.5} />
              <text x={x + 11} y={y + 3} textAnchor="start" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
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
              <line x1={x} y1={y} x2={x} y2={y + 6} stroke="var(--muted)" strokeWidth={1.5} />
              <text x={x} y={y + 17} textAnchor="middle" className="chart-tick-label" style={{ fontSize: 10, fontWeight: 600 }}>
                {p}
              </text>
            </g>
          ))}
          {/* Bottom edge title */}
          <text
            x={(V_C2H2.x + V_C2H4.x) / 2}
            y={V_C2H2.y + 38}
            textAnchor="middle"
            style={{ fontSize: 13, fontWeight: 700, fill: 'var(--ink)' }}
          >
            ← % C₂H₂
          </text>

          {/* Vertex 100% Labels */}
          <text x={V_CH4.x} y={V_CH4.y - 18} textAnchor="middle" style={{ fontSize: 11, fontWeight: 800, fill: 'var(--ink)' }}>
            100% CH₄
          </text>
          <text x={V_C2H4.x + 12} y={V_C2H4.y + 20} textAnchor="start" style={{ fontSize: 11, fontWeight: 800, fill: 'var(--ink)' }}>
            100% C₂H₄
          </text>
          <text x={V_C2H2.x - 12} y={V_C2H2.y + 20} textAnchor="end" style={{ fontSize: 11, fontWeight: 800, fill: 'var(--ink)' }}>
            100% C₂H₂
          </text>

          {/* Projection Axis Badges for active sample */}
          {showProjections && activePoint && (
            <g style={{ pointerEvents: 'none' }}>
              {/* %CH4 Left badge */}
              <circle cx={projCH4_left.x} cy={projCH4_left.y} r={3.5} fill="#f43f5e" />
              <text x={projCH4_left.x - 18} y={projCH4_left.y - 3} textAnchor="end" style={{ fontSize: 9.5, fontWeight: 800, fill: 'var(--critical)' }}>
                {pch4.toFixed(1)}%
              </text>
              {/* %C2H4 Right badge */}
              <circle cx={projC2H4_top.x} cy={projC2H4_top.y} r={3.5} fill="#f43f5e" />
              <text x={projC2H4_top.x + 18} y={projC2H4_top.y - 3} textAnchor="start" style={{ fontSize: 9.5, fontWeight: 800, fill: 'var(--critical)' }}>
                {pc2h4.toFixed(1)}%
              </text>
              {/* %C2H2 Bottom badge */}
              <circle cx={projC2H2_bot.x} cy={projC2H2_bot.y} r={3.5} fill="#f43f5e" />
              <text x={projC2H2_bot.x} y={projC2H2_bot.y + 25} textAnchor="middle" style={{ fontSize: 9.5, fontWeight: 800, fill: 'var(--critical)' }}>
                {pc2h2.toFixed(1)}%
              </text>
            </g>
          )}

          {/* 7. HISTORICAL TRAJECTORY LINE & POINTS */}
          {showHistory && historyPoints.length > 1 && (
            <g>
              {/* Trajectory migration polyline */}
              <polyline
                points={historyPoints.map((h) => `${h.pos.x.toFixed(1)},${h.pos.y.toFixed(1)}`).join(' ')}
                fill="none"
                stroke="#0f172a"
                strokeWidth={2}
                strokeDasharray="4 3"
                markerMid="url(#arrowhead)"
              />
              {/* Prior historical point nodes */}
              {historyPoints.slice(0, -1).map((h) => (
                <g
                  key={`hist-${h.stepIndex}`}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHoveredPoint(h)}
                  onMouseLeave={() => setHoveredPoint(null)}
                >
                  <circle
                    cx={h.pos.x} cy={h.pos.y}
                    r={5.5}
                    fill="#f59e0b"
                    stroke="#0f172a"
                    strokeWidth={1.8}
                  />
                  <text
                    x={h.pos.x} y={h.pos.y + 3}
                    textAnchor="middle"
                    style={{ fontSize: 7.5, fontWeight: 800, fill: 'var(--ink)' }}
                  >
                    {h.stepIndex}
                  </text>
                </g>
              ))}
            </g>
          )}

          {/* 8. LATEST DATA POINT — BULLSEYE TARGET MARKER */}
          {activePoint && (
            <g
              filter="url(#glow-target)"
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredPoint({
                date: 'Sampel Aktif',
                pCH4: pch4, pC2H4: pc2h4, pC2H2: pc2h2,
                CH4: ch4raw, C2H4: c2h4raw, C2H2: c2h2raw,
              })}
              onMouseLeave={() => setHoveredPoint(null)}
            >
              {/* Outer pulsing halo */}
              <circle cx={activePoint.x} cy={activePoint.y} r={18} fill="#f43f5e" fillOpacity={0.25} />
              {/* White ring */}
              <circle cx={activePoint.x} cy={activePoint.y} r={8.5} fill="#f43f5e" stroke="#ffffff" strokeWidth={2.4} />
              {/* Center bullseye dot */}
              <circle cx={activePoint.x} cy={activePoint.y} r={2.8} fill="#ffffff" />
            </g>
          )}

          {/* 9. FLOATING INTERACTIVE HOVER BOX */}
          {hoveredPoint && (
            <g style={{ pointerEvents: 'none' }}>
              <rect
                x={Math.min((hoveredPoint.pos ? hoveredPoint.pos.x + 12 : activePoint.x + 12), TRI_W - 180)}
                y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 70 : activePoint.y - 70), 12)}
                width={172}
                height={88}
                rx={7}
                fill="#0f172a"
                fillOpacity={0.94}
                stroke="#475569"
                strokeWidth={1}
              />
              <text
                x={Math.min((hoveredPoint.pos ? hoveredPoint.pos.x + 22 : activePoint.x + 22), TRI_W - 170)}
                y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 50 : activePoint.y - 50), 32)}
                fill="#ffffff"
                style={{ fontSize: 11, fontWeight: 700 }}
              >
                {hoveredPoint.date || 'Sampel DGA'} {hoveredPoint.stepIndex ? `(#${hoveredPoint.stepIndex})` : ''}
              </text>
              <text
                x={Math.min((hoveredPoint.pos ? hoveredPoint.pos.x + 22 : activePoint.x + 22), TRI_W - 170)}
                y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 34 : activePoint.y - 34), 48)}
                fill="#94a3b8"
                style={{ fontSize: 10 }}
              >
                %CH₄: {hoveredPoint.pCH4.toFixed(1)}% | {hoveredPoint.CH4 ?? ch4raw} ppm
              </text>
              <text
                x={Math.min((hoveredPoint.pos ? hoveredPoint.pos.x + 22 : activePoint.x + 22), TRI_W - 170)}
                y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 20 : activePoint.y - 20), 62)}
                fill="#94a3b8"
                style={{ fontSize: 10 }}
              >
                %C₂H₄: {hoveredPoint.pC2H4.toFixed(1)}% | {hoveredPoint.C2H4 ?? c2h4raw} ppm
              </text>
              <text
                x={Math.min((hoveredPoint.pos ? hoveredPoint.pos.x + 22 : activePoint.x + 22), TRI_W - 170)}
                y={Math.max((hoveredPoint.pos ? hoveredPoint.pos.y - 6 : activePoint.y - 6), 76)}
                fill="#94a3b8"
                style={{ fontSize: 10 }}
              >
                %C₂H₂: {hoveredPoint.pC2H2.toFixed(1)}% | {hoveredPoint.C2H2 ?? c2h2raw} ppm
              </text>
            </g>
          )}

          {/* No data overlay */}
          {gasSum === 0 && (
            <text x={TRI_W / 2} y={TRI_H / 2} className="duval-axis-label" textAnchor="middle" fill="var(--muted)" opacity={0.6}>
              (Pilih transformer dengan data gas aktif atau gunakan Simulator)
            </text>
          )}
        </svg>

        {/* Selected / Hovered Zone Details Card */}
        {activeZoneInfo && (
          <div className="duval-zone-info-card" style={{ borderLeftColor: activeZoneInfo.color }}>
            <div className="duval-zone-info-header">
              <span className="duval-zone-badge" style={{ background: activeZoneInfo.color, color: activeZoneInfo.textColor }}>
                {activeZoneInfo.id}
              </span>
              <strong>{activeZoneInfo.fullLabel}</strong>
            </div>
            <p className="duval-zone-desc">{activeZoneInfo.desc}</p>
            <div className="duval-zone-action">
              <Compass size={14} className="text-amber-500 shrink-0" />
              <span><strong>Rekomendasi CBM:</strong> {activeZoneInfo.action}</span>
            </div>
          </div>
        )}
      </div>

      {/* 10. LEGEND WITH ZONE HIGHLIGHTS */}
      <div className="duval-legend">
        {DUVAL_ZONES.map((zone) => (
          <span
            key={zone.id}
            className={`duval-legend-item ${(hoveredZone === zone.id || selectedZone === zone.id) ? 'duval-legend-item--active' : ''}`}
            onMouseEnter={() => setHoveredZone(zone.id)}
            onMouseLeave={() => setHoveredZone(null)}
            onClick={() => setSelectedZone(selectedZone === zone.id ? null : zone.id)}
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

// ─── Preset Gangguan DGA Riil untuk Simulator ─────────────────────────────────

const DUVAL_PRESETS = [
  {
    name: 'Hotspot T3 (>700°C)',
    zone: 'T3',
    gases: { CH4: 40, C2H4: 280, C2H2: 12, H2: 50, C2H6: 30, CO: 450, CO2: 2400 },
  },
  {
    name: 'Arcing D2 (High Energy)',
    zone: 'D2',
    gases: { CH4: 60, C2H4: 75, C2H2: 150, H2: 220, C2H6: 15, CO: 320, CO2: 1800 },
  },
  {
    name: 'Sparking D1 (Low Energy)',
    zone: 'D1',
    gases: { CH4: 25, C2H4: 15, C2H2: 85, H2: 95, C2H6: 10, CO: 210, CO2: 1500 },
  },
  {
    name: 'Partial Discharge (PD)',
    zone: 'PD',
    gases: { CH4: 260, C2H4: 2, C2H2: 1, H2: 480, C2H6: 25, CO: 160, CO2: 1400 },
  },
  {
    name: 'Thermal T1 (<300°C)',
    zone: 'T1',
    gases: { CH4: 190, C2H4: 18, C2H2: 2, H2: 45, C2H6: 40, CO: 380, CO2: 2900 },
  },
  {
    name: 'Thermal T2 (300-700°C)',
    zone: 'T2',
    gases: { CH4: 120, C2H4: 90, C2H2: 4, H2: 70, C2H6: 45, CO: 420, CO2: 2600 },
  },
  {
    name: 'Campuran DT (Arcing+Termal)',
    zone: 'DT',
    gases: { CH4: 95, C2H4: 135, C2H2: 40, H2: 140, C2H6: 25, CO: 350, CO2: 2200 },
  },
  {
    name: 'Degradasi Kertas Selulosa',
    zone: 'T1',
    gases: { CH4: 45, C2H4: 30, C2H2: 1, H2: 60, C2H6: 25, CO: 950, CO2: 6500 },
  },
  {
    name: 'Stray Gassing (Minyak Baru)',
    zone: 'S',
    gases: { CH4: 30, C2H4: 12, C2H2: 0.2, H2: 40, C2H6: 190, CO: 90, CO2: 850 },
  },
]

// ─── Duval Pentagon 1 Definition & Geometry (CIGRE TB 771) ───────────────────

const PENTAGON_ZONES = [
  { id: 'PD', label: 'PD', name: 'Partial Discharge', color: '#c084fc', textColor: '#581c87', desc: 'Pelepasan muatan parsial berdaya rendah pada rongga isolasi atau gelembung minyak.' },
  { id: 'D1', label: 'D1', name: 'Low Energy Discharge (Sparking)', color: '#7dd3fc', textColor: '#0369a1', desc: 'Pelepasan percikan listrik energi rendah, potensi elektroda mengambang.' },
  { id: 'D2', label: 'D2', name: 'High Energy Discharge (Arcing)', color: '#06b6d4', textColor: '#083344', desc: 'Busur api listrik energi tinggi menembus minyak trafo, flashover belitan.' },
  { id: 'T1', label: 'T1', name: 'Thermal Fault < 300°C', color: '#fbbf24', textColor: '#78350f', desc: 'Pemanasan setempat suhu rendah (< 300°C) pada minyak trafo.' },
  { id: 'T2', label: 'T2', name: 'Thermal Fault 300-700°C', color: '#f97316', textColor: '#7c2d12', desc: 'Overheating termal suhu menengah (300°C - 700°C) pada sambungan konduktor.' },
  { id: 'T3', label: 'T3', name: 'Thermal Fault > 700°C', color: '#ef4444', textColor: '#7f1d1d', desc: 'Suhu termal ekstrem di atas 700°C, pembentukan jelaga dan degradasi parah.' },
  { id: 'S',  label: 'S',  name: 'Stray Gassing / Oil < 200°C', color: '#34d399', textColor: '#064e3b', desc: 'Pelepasan gas alami (stray gassing) minyak mineral di bawah 200°C.' },
]

// Client-side math helpers for DGA evaluation (instant response in simulator)
function evalPentagonClient(gases) {
  const h2 = Math.max(0, Number(gases?.H2 || 0))
  const c2h6 = Math.max(0, Number(gases?.C2H6 || 0))
  const ch4 = Math.max(0, Number(gases?.CH4 || 0))
  const c2h4 = Math.max(0, Number(gases?.C2H4 || 0))
  const c2h2 = Math.max(0, Number(gases?.C2H2 || 0))
  const sum = h2 + c2h6 + ch4 + c2h4 + c2h2
  if (sum <= 0) return { x: 0, y: 0, zone: 'Normal', label: 'Normal (Gas Rendah)', percentages: { H2: 0, C2H6: 0, CH4: 0, C2H4: 0, C2H2: 0 } }

  const p_h2 = (h2 / sum) * 100
  const p_c2h6 = (c2h6 / sum) * 100
  const p_ch4 = (ch4 / sum) * 100
  const p_c2h4 = (c2h4 / sum) * 100
  const p_c2h2 = (c2h2 / sum) * 100

  const angles = [
    Math.PI / 2,         // H2 (90 deg)
    Math.PI * 0.1,       // C2H6 (18 deg)
    -Math.PI * 0.3,      // CH4 (-54 deg)
    -Math.PI * 0.7,      // C2H4 (-126 deg)
    Math.PI * 0.9,       // C2H2 (162 deg)
  ]
  const R = 40
  const x = ((p_h2 / 100) * R * Math.cos(angles[0])) +
            ((p_c2h6 / 100) * R * Math.cos(angles[1])) +
            ((p_ch4 / 100) * R * Math.cos(angles[2])) +
            ((p_c2h4 / 100) * R * Math.cos(angles[3])) +
            ((p_c2h2 / 100) * R * Math.cos(angles[4]))
  const y = ((p_h2 / 100) * R * Math.sin(angles[0])) +
            ((p_c2h6 / 100) * R * Math.sin(angles[1])) +
            ((p_ch4 / 100) * R * Math.sin(angles[2])) +
            ((p_c2h4 / 100) * R * Math.sin(angles[3])) +
            ((p_c2h2 / 100) * R * Math.sin(angles[4]))

  let zone = 'T1'
  let label = 'T1 (Thermal Fault < 300°C)'
  let desc = 'Gangguan termal suhu rendah pada minyak trafo.'

  if (p_h2 >= 75 || (y >= 18 && x >= -10 && x <= 14)) {
    zone = 'PD'; label = 'PD (Partial Discharge)'; desc = 'Pelepasan muatan parsial bertegangan tinggi di dalam rongga gas atau gelembung minyak.'
  } else if (p_c2h2 >= 35 || (x <= -12 && y <= 12 && y >= -16)) {
    zone = 'D2'; label = 'D2 (High Energy Discharge / Arcing)'; desc = 'Pelepasan busur api energi tinggi menembus minyak trafo, flashover belitan.'
  } else if (p_c2h2 >= 12 || (x <= -6 && y >= 0)) {
    zone = 'D1'; label = 'D1 (Low Energy Discharge / Sparking)'; desc = 'Pelepasan percikan listrik energi rendah (Sparking), potensi elektroda mengambang.'
  } else if (p_c2h4 >= 45 || (x <= 5 && y <= -15)) {
    zone = 'T3'; label = 'T3 (Thermal Fault > 700°C)'; desc = 'Gangguan termal suhu tinggi (> 700°C), overheating parah pada inti besi atau belitan.'
  } else if (p_c2h4 >= 20 || (y <= -8 && x >= -10)) {
    zone = 'T2'; label = 'T2 (Thermal Fault 300°C - 700°C)'; desc = 'Gangguan termal suhu menengah (300°C - 700°C) pada sambungan konduktor.'
  } else if (p_ch4 >= 35 || (x >= 12 && y <= 8)) {
    zone = 'T1'; label = 'T1 (Thermal Fault < 300°C)'; desc = 'Gangguan termal suhu rendah (< 300°C), titik panas terisolasi.'
  } else if (p_c2h6 >= 30 || (x >= -8 && x <= 12 && y >= -6 && y <= 14)) {
    zone = 'S'; label = 'S (Stray Gassing / Oil < 200°C)'; desc = 'Pelepasan gas alami (stray gassing) minyak mineral di bawah 200°C.'
  }

  return {
    x: Number(x.toFixed(2)),
    y: Number(y.toFixed(2)),
    zone,
    zone_label: label,
    zone_desc: desc,
    percentages: {
      H2: Number(p_h2.toFixed(1)),
      C2H6: Number(p_c2h6.toFixed(1)),
      CH4: Number(p_ch4.toFixed(1)),
      C2H4: Number(p_c2h4.toFixed(1)),
      C2H2: Number(p_c2h2.toFixed(1)),
    },
  }
}

function evalRogersClient(gases) {
  const h2 = Math.max(0, Number(gases?.H2 || 0))
  const ch4 = Math.max(0, Number(gases?.CH4 || 0))
  const c2h6 = Math.max(0, Number(gases?.C2H6 || 0))
  const c2h4 = Math.max(0, Number(gases?.C2H4 || 0))
  const c2h2 = Math.max(0, Number(gases?.C2H2 || 0))
  const co = Math.max(0, Number(gases?.CO || 0))
  const co2 = Math.max(0, Number(gases?.CO2 || 0))

  const r1 = c2h4 > 0 ? Number((c2h2 / c2h4).toFixed(3)) : (c2h2 === 0 ? 0 : 999)
  const r2 = h2 > 0 ? Number((ch4 / h2).toFixed(3)) : (ch4 === 0 ? 0 : 999)
  const r3 = c2h6 > 0 ? Number((c2h4 / c2h6).toFixed(3)) : (c2h4 === 0 ? 0 : 999)
  const co2_co = co > 0 ? Number((co2 / co).toFixed(2)) : 0

  const code_r1 = r1 < 0.1 ? 0 : (r1 <= 3.0 ? 1 : 2)
  const code_r2 = r2 < 0.1 ? 1 : (r2 <= 1.0 ? 0 : 2)
  const code_r3 = r3 < 1.0 ? 0 : (r3 <= 3.0 ? 1 : 2)
  const diag_code = `${code_r1}-${code_r2}-${code_r3}`

  let diagnosis = 'Normal Deterioration'
  let description = 'Degradasi normal isolasi minyak karena penuaan operasional normal.'
  let severity = 'NORMAL'

  if (r1 < 0.1 && r2 >= 0.1 && r2 <= 1.0 && r3 < 1.0) {
    diagnosis = 'Normal Deterioration'
    description = 'Degradasi normal isolasi minyak karena penuaan operasional normal.'
    severity = 'NORMAL'
  } else if (r1 < 0.1 && r2 < 0.1 && r3 < 1.0) {
    diagnosis = 'Partial Discharge (Corona)'
    description = 'Pelepasan muatan listrik parsial berdaya rendah di dalam rongga isolasi atau celah gas.'
    severity = 'WARNING'
  } else if (r1 >= 0.1 && r1 <= 3.0 && r2 >= 0.1 && r2 <= 1.0 && r3 > 3.0) {
    diagnosis = 'Continuous Sparking / Arcing'
    description = 'Pelepasan bunga api listrik terus-menerus ke elektroda mengambang atau kontak longgar.'
    severity = 'HIGH'
  } else if (r1 >= 1.0 && r2 >= 0.1 && r2 <= 1.0 && r3 >= 0.1 && r3 <= 3.0) {
    diagnosis = 'Arc with Power Follow-through'
    description = 'Busur listrik energi tinggi menembus dielektrik minyak trafo (Arcing).'
    severity = 'HIGH'
  } else if (r1 < 0.1 && r2 >= 0.1 && r2 <= 1.0 && r3 >= 1.0 && r3 <= 3.0) {
    diagnosis = 'Thermal Fault 150°C - 200°C'
    description = 'Overheating ringan pada minyak trafo atau konduktor lokal.'
    severity = 'PREWARNING'
  } else if (r1 < 0.1 && r2 > 1.0 && r3 >= 1.0 && r3 <= 3.0) {
    diagnosis = 'Thermal Fault 200°C - 300°C'
    description = 'Pemanasan setempat suhu menengah pada inti besi atau sambungan konduktor.'
    severity = 'WARNING'
  } else if (r1 < 0.1 && r2 > 1.0 && r3 >= 3.0) {
    diagnosis = 'Thermal Fault 300°C - 700°C'
    description = 'Pemanasan konduktor serius disertai degradasi minyak dan karbonisasi awal.'
    severity = 'WARNING'
  } else if (r1 < 0.1 && r2 >= 0.1 && r2 <= 1.0 && r3 >= 3.0) {
    diagnosis = 'Thermal Fault > 700°C'
    description = 'Suhu termal ekstrem melebihi 700°C, pembentukan jelaga dan degradasi parah.'
    severity = 'HIGH'
  } else if (r1 >= 0.1) {
    diagnosis = 'Electrical Discharge / Sparking'
    description = 'Terdeteksi pelepasan listrik aktif yang menghasilkan gas asetilena (C2H2).'
    severity = 'HIGH'
  }

  let paper_diag = 'Normal (Penuaan wajar)'
  if (co2_co >= 7 && co2_co <= 15) paper_diag = 'Normal (Penuaan wajar)'
  else if (co2_co < 3) paper_diag = 'Kritis (Degradasi / Pyrolysis isolasi kertas selulosa)'
  else if (co2_co < 7) paper_diag = 'Perhatian (Penuaan isolasi kertas dipercepat)'

  return {
    r1_c2h2_c2h4: r1,
    r2_ch4_h2: r2,
    r3_c2h4_c2h6: r3,
    co2_co_ratio: co2_co,
    diag_code,
    diagnosis,
    description,
    severity,
    paper_diagnosis: paper_diag,
  }
}

function evalKeyGasClient(gases) {
  const h2 = Math.max(0, Number(gases?.H2 || 0))
  const ch4 = Math.max(0, Number(gases?.CH4 || 0))
  const c2h6 = Math.max(0, Number(gases?.C2H6 || 0))
  const c2h4 = Math.max(0, Number(gases?.C2H4 || 0))
  const c2h2 = Math.max(0, Number(gases?.C2H2 || 0))
  const co = Math.max(0, Number(gases?.CO || 0))

  const total = h2 + ch4 + c2h6 + c2h4 + c2h2 + co
  if (total <= 0) {
    return {
      dominant_gas: '-',
      fault_type: 'Normal (Tidak Ada Gas Kunci)',
      primary_mechanism: 'Konsentrasi seluruh gas kunci berada pada tingkat latar belakang yang dapat diabaikan.',
      proportions: { H2: 0, CH4: 0, C2H6: 0, C2H4: 0, C2H2: 0, CO: 0 },
      scores: { thermal_oil: 0, thermal_cellulose: 0, corona_pd: 0, arcing: 0 },
    }
  }

  const p = {
    H2: Number(((h2 / total) * 100).toFixed(1)),
    CH4: Number(((ch4 / total) * 100).toFixed(1)),
    C2H6: Number(((c2h6 / total) * 100).toFixed(1)),
    C2H4: Number(((c2h4 / total) * 100).toFixed(1)),
    C2H2: Number(((c2h2 / total) * 100).toFixed(1)),
    CO: Number(((co / total) * 100).toFixed(1)),
  }

  const s_oil = Math.min(100, Math.max(0, (p.C2H4 * 1.3) + (p.CH4 * 0.4) + (p.C2H6 * 0.3) - (p.C2H2 * 1.5)))
  const s_cell = Math.min(100, Math.max(0, (p.CO * 1.05) - (p.C2H2 * 1.2)))
  const s_pd = Math.min(100, Math.max(0, (p.H2 * 1.15) + (p.CH4 * 0.2) - (p.C2H2 * 1.5)))
  const s_arc = Math.min(100, Math.max(0, (p.C2H2 * 1.8) + (p.H2 * 0.3)))

  const scores = {
    thermal_oil: Number(s_oil.toFixed(1)),
    thermal_cellulose: Number(s_cell.toFixed(1)),
    corona_pd: Number(s_pd.toFixed(1)),
    arcing: Number(s_arc.toFixed(1)),
  }

  const dominant_gas = Object.entries(p).sort((a, b) => b[1] - a[1])[0][0]

  let fault_type = 'Normal / Undifferentiated Mix'
  let mech = 'Distribusi gas kunci campuran pada tingkat operasional wajar.'

  const maxScoreKey = Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0]
  if (maxScoreKey === 'arcing' && p.C2H2 >= 3.0) {
    fault_type = 'Electrical Arcing (Flashover)'
    mech = `Gas kunci utama: Asetilena (${p.C2H2}%), mengindikasikan loncatan busur api listrik suhu tinggi menembus minyak trafo.`
  } else if (maxScoreKey === 'thermal_oil' && p.C2H4 >= 20.0) {
    fault_type = 'Thermal Oil Degradation'
    mech = `Gas kunci utama: Etilena (${p.C2H4}%), mengindikasikan overheating termal suhu tinggi pada minyak trafo.`
  } else if (maxScoreKey === 'thermal_cellulose' && p.CO >= 50.0) {
    fault_type = 'Thermal Cellulose / Paper Overheating'
    mech = `Gas kunci utama: Karbon Monoksida (${p.CO}%), mengindikasikan degradasi dan penuaan termal isolasi kertas selulosa.`
  } else if (maxScoreKey === 'corona_pd' && p.H2 >= 40.0) {
    fault_type = 'Electrical Corona / Partial Discharge'
    mech = `Gas kunci utama: Hidrogen (${p.H2}%), mengindikasikan pelepasan muatan parsial pada rongga udara atau gelembung minyak.`
  }

  return {
    dominant_gas,
    fault_type,
    primary_mechanism: mech,
    proportions: p,
    scores,
  }
}

function evalPredictionClient(history, currentGases) {
  const gasKeys = ['H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO', 'CO2']
  const currentTdcg = ['H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO'].reduce((acc, k) => acc + Number(currentGases?.[k] || 0), 0)

  let intervalDays = 90
  const rateDay = {}

  if (history && history.length >= 2) {
    const sorted = [...history].sort((a, b) => new Date(a.date) - new Date(b.date))
    const prev = sorted[sorted.length - 2]
    const curr = sorted[sorted.length - 1]
    const dCurr = new Date(curr.date)
    const dPrev = new Date(prev.date)
    const diff = Math.max(1, Math.round((dCurr - dPrev) / (1000 * 60 * 60 * 24)))
    intervalDays = diff

    gasKeys.forEach((k) => {
      const vCurr = Number(curr[k] ?? currentGases?.[k] ?? 0)
      const vPrev = Number(prev[k] ?? 0)
      rateDay[k] = Number(((vCurr - vPrev) / intervalDays).toFixed(3))
    })

    const tdcgCurr = Number(curr.tdcg ?? currentTdcg)
    const tdcgPrev = Number(prev.tdcg ?? tdcgCurr)
    rateDay.TDCG = Number(((tdcgCurr - tdcgPrev) / intervalDays).toFixed(3))
  } else {
    gasKeys.forEach((k) => { rateDay[k] = 0.01 })
    rateDay.TDCG = 0.05
  }

  const rateMonth = {}
  Object.keys(rateDay).forEach((k) => {
    rateMonth[k] = Number((rateDay[k] * 30).toFixed(2))
  })

  const forecast3m = {}
  const forecast6m = {}
  const forecast12m = {}

  gasKeys.forEach((k) => {
    const cur = Number(currentGases?.[k] || 0)
    const r = rateDay[k] || 0
    forecast3m[k] = Number(Math.max(0, cur + r * 90).toFixed(1))
    forecast6m[k] = Number(Math.max(0, cur + r * 180).toFixed(1))
    forecast12m[k] = Number(Math.max(0, cur + r * 365).toFixed(1))
  })

  const rTdcg = rateDay.TDCG || 0
  forecast3m.TDCG = Number(Math.max(0, currentTdcg + rTdcg * 90).toFixed(1))
  forecast6m.TDCG = Number(Math.max(0, currentTdcg + rTdcg * 180).toFixed(1))
  forecast12m.TDCG = Number(Math.max(0, currentTdcg + rTdcg * 365).toFixed(1))

  let rateStatus = 'STABLE'
  let rateDesc = 'Laju pembentukan gas stabil dalam batas operasional aman (< 10 ppm/hari).'
  let actionAdvice = 'Lanjutkan siklus pemeliharaan berkala 6 bulan sekali sesuai IEEE C57.104.'

  if (rTdcg > 30.0 || (rateDay.C2H2 || 0) > 0.5) {
    rateStatus = 'CRITICAL'
    rateDesc = 'Laju pembentukan gas sangat cepat (kritis). Risiko gangguan aktif berenergi tinggi.'
    actionAdvice = 'Lakukan re-sampling dalam kurun waktu 48 jam dan evaluasi penurunan pembebanan trafo.'
  } else if (rTdcg > 10.0 || (rateDay.C2H2 || 0) > 0.1 || (rateDay.H2 || 0) > 5.0) {
    rateStatus = 'ALERT'
    rateDesc = 'Laju pembentukan gas meningkat di atas batas toleransi IEEE C57.104.'
    actionAdvice = 'Tingkatkan frekuensi sampling menjadi 1 bulan sekali dan pantau tren kenaikan suhu.'
  } else if (rTdcg > 3.0) {
    rateStatus = 'PREWARNING'
    rateDesc = 'Kenaikan gas terdeteksi moderat seiring beban operasional.'
    actionAdvice = 'Lanjutkan pemantauan berkala 3 bulan sekali dan catat riwayat pembebanan puncak.'
  }

  let daysToWarn = null
  if (currentTdcg < 720 && rTdcg > 0.05) {
    daysToWarn = Math.round((720 - currentTdcg) / rTdcg)
  } else if (currentTdcg >= 720) {
    daysToWarn = 0
  }

  return {
    interval_days: intervalDays,
    rate_ppm_day: rateDay,
    rate_ppm_month: rateMonth,
    rate_status: rateStatus,
    rate_desc: rateDesc,
    action_advice: actionAdvice,
    days_to_warning: daysToWarn,
    forecast_3m: forecast3m,
    forecast_6m: forecast6m,
    forecast_12m: forecast12m,
  }
}

// ─── Component: Duval Pentagon 1 Visualizer (SVG) ────────────────────────────

function DuvalPentagon({ gases, transformerName, pentagonData, history }) {
  const [hoveredZone, setHoveredZone] = useState(null)
  const [showGrid, setShowGrid] = useState(true)
  const [showHistory, setShowHistory] = useState(true)

  const pentagon = pentagonData || evalPentagonClient(gases)
  const { x, y, zone, zone_label, zone_desc, percentages } = pentagon

  const cx = 270
  const cy = 230
  const R = 170

  // 5 Vertices on circle
  // H2 (90°), C2H6 (18°), CH4 (-54°), C2H4 (-126°), C2H2 (162°)
  const vertices = [
    { name: 'H₂', label: '100% H₂', angle: Math.PI / 2, x: cx, y: cy - R },
    { name: 'C₂H₆', label: '100% C₂H₆', angle: Math.PI * 0.1, x: cx + R * Math.cos(Math.PI * 0.1), y: cy - R * Math.sin(Math.PI * 0.1) },
    { name: 'CH₄', label: '100% CH₄', angle: -Math.PI * 0.3, x: cx + R * Math.cos(-Math.PI * 0.3), y: cy - R * Math.sin(-Math.PI * 0.3) },
    { name: 'C₂H₄', label: '100% C₂H₄', angle: -Math.PI * 0.7, x: cx + R * Math.cos(-Math.PI * 0.7), y: cy - R * Math.sin(-Math.PI * 0.7) },
    { name: 'C₂H₂', label: '100% C₂H₂', angle: Math.PI * 0.9, x: cx + R * Math.cos(Math.PI * 0.9), y: cy - R * Math.sin(Math.PI * 0.9) },
  ]

  const outerPointsStr = vertices.map((v) => `${v.x.toFixed(1)},${v.y.toFixed(1)}`).join(' ')

  // Concentric pentagon rings
  const rings = [0.25, 0.5, 0.75].map((scale) => {
    return vertices.map((v) => {
      const px = cx + (v.x - cx) * scale
      const py = cy + (v.y - cy) * scale
      return `${px.toFixed(1)},${py.toFixed(1)}`
    }).join(' ')
  })

  // Map coordinate to SVG
  // Radius R = 170 corresponds to r_max = 40
  const targetSvgX = cx + (x / 40) * R
  const targetSvgY = cy - (y / 40) * R

  // History points
  const historyPoints = (history || []).map((h) => {
    const hp = evalPentagonClient(h)
    return {
      date: h.date,
      x: cx + (hp.x / 40) * R,
      y: cy - (hp.y / 40) * R,
      zone: hp.zone,
    }
  })

  // Zone polygons in SVG
  const zonePolys = [
    { id: 'PD', points: '270,60 310,95 290,165 250,165 230,95', color: '#c084fc', textPos: { x: 270, y: 115 } },
    { id: 'D1', points: '230,95 250,165 200,205 108.3,177.5 155,115', color: '#7dd3fc', textPos: { x: 175, y: 155 } },
    { id: 'D2', points: '108.3,177.5 200,205 200,265 140,305 130,250', color: '#06b6d4', textPos: { x: 155, y: 235 } },
    { id: 'T3', points: '140,305 200,265 240,305 210,367.5 170.1,367.5', color: '#ef4444', textPos: { x: 195, y: 335 } },
    { id: 'T2', points: '240,305 295,305 340,265 369.9,367.5 320,367.5 210,367.5', color: '#f97316', textPos: { x: 285, y: 335 } },
    { id: 'T1', points: '340,265 340,205 431.7,177.5 369.9,367.5', color: '#fbbf24', textPos: { x: 370, y: 240 } },
    { id: 'S',  points: '250,165 290,165 340,205 340,265 295,305 240,305 200,265 200,205', color: '#34d399', textPos: { x: 270, y: 230 } },
  ]

  const activeZoneObj = PENTAGON_ZONES.find((z) => z.id === (hoveredZone || zone))

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title" style={{ flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Compass size={18} className="text-amber-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Pentagon Duval 1 (CIGRE TB 771) — {transformerName}</span>
          {zone_label && <span className="duval-diag-pill">{zone_label}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.78rem' }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
            <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />
            <span>Kisi Pentagon</span>
          </label>
          {historyPoints.length > 1 && (
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, cursor: 'pointer' }}>
              <input type="checkbox" checked={showHistory} onChange={(e) => setShowHistory(e.target.checked)} />
              <span>Riwayat ({historyPoints.length} titik)</span>
            </label>
          )}
        </div>
      </div>

      <div className="duval-interactive-wrap" style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
        {/* SVG Pentagon */}
        <div style={{ position: 'relative' }}>
          <svg
            viewBox="0 0 540 460"
            className="duval-svg"
            style={{ width: '100%', height: 'auto', background: 'var(--surface)', borderRadius: 12 }}
          >
            <defs>
              <clipPath id="pentagon-clip">
                <polygon points={outerPointsStr} />
              </clipPath>
              <filter id="glow-pentagon" x="-40%" y="-40%" width="180%" height="180%">
                <feGaussianBlur stdDeviation="3.5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* 1. FAULT ZONES */}
            <g clipPath="url(#pentagon-clip)">
              {zonePolys.map((zp) => {
                const isHov = hoveredZone === zp.id || zone === zp.id
                return (
                  <polygon
                    key={zp.id}
                    points={zp.points}
                    fill={zp.color}
                    fillOpacity={isHov ? 0.95 : 0.75}
                    stroke="#ffffff"
                    strokeWidth={isHov ? 2 : 1}
                    style={{ cursor: 'pointer', transition: 'fill-opacity 0.2s ease' }}
                    onMouseEnter={() => setHoveredZone(zp.id)}
                    onMouseLeave={() => setHoveredZone(null)}
                  />
                )
              })}
            </g>

            {/* 2. CONCENTRIC RINGS GRID */}
            {showGrid && (
              <g clipPath="url(#pentagon-clip)" opacity={0.4}>
                {rings.map((rStr, i) => (
                  <polygon key={i} points={rStr} fill="none" stroke="#ffffff" strokeWidth={1} strokeDasharray="3 3" />
                ))}
                {vertices.map((v) => (
                  <line key={v.name} x1={cx} y1={cy} x2={v.x} y2={v.y} stroke="#ffffff" strokeWidth={1} strokeDasharray="3 3" />
                ))}
              </g>
            )}

            {/* 3. PENTAGON OUTER BORDER */}
            <polygon points={outerPointsStr} fill="none" stroke="var(--ink)" strokeWidth={2} opacity={0.6} />

            {/* 4. ZONE LABELS */}
            {zonePolys.map((zp) => (
              <text
                key={`lbl-${zp.id}`}
                x={zp.textPos.x}
                y={zp.textPos.y}
                textAnchor="middle"
                dominantBaseline="central"
                style={{
                  fontSize: 13,
                  fontWeight: 800,
                  fill: '#ffffff',
                  textShadow: '0 1px 3px rgba(0,0,0,0.85)',
                  pointerEvents: 'none',
                }}
              >
                {zp.id}
              </text>
            ))}

            {/* 5. VERTEX LABELS */}
            <text x={vertices[0].x} y={vertices[0].y - 14} textAnchor="middle" style={{ fontSize: 12, fontWeight: 800, fill: 'var(--ink)' }}>
              100% H₂
            </text>
            <text x={vertices[1].x + 12} y={vertices[1].y - 4} textAnchor="start" style={{ fontSize: 12, fontWeight: 800, fill: 'var(--ink)' }}>
              100% C₂H₆
            </text>
            <text x={vertices[2].x + 12} y={vertices[2].y + 14} textAnchor="start" style={{ fontSize: 12, fontWeight: 800, fill: 'var(--ink)' }}>
              100% CH₄
            </text>
            <text x={vertices[3].x - 12} y={vertices[3].y + 14} textAnchor="end" style={{ fontSize: 12, fontWeight: 800, fill: 'var(--ink)' }}>
              100% C₂H₄
            </text>
            <text x={vertices[4].x - 12} y={vertices[4].y - 4} textAnchor="end" style={{ fontSize: 12, fontWeight: 800, fill: 'var(--ink)' }}>
              100% C₂H₂
            </text>

            {/* 6. TRAJECTORY MIGRATION PATH */}
            {showHistory && historyPoints.length > 1 && (
              <g opacity={0.75}>
                <polyline
                  points={historyPoints.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                  fill="none"
                  stroke="var(--ink)"
                  strokeWidth={2}
                  strokeDasharray="4 3"
                />
                {historyPoints.slice(0, -1).map((p, idx) => (
                  <circle key={idx} cx={p.x} cy={p.y} r={4.5} fill="#64748b" stroke="#ffffff" strokeWidth={1.5} />
                ))}
              </g>
            )}

            {/* 7. ACTIVE POINT TARGET */}
            <g>
              {/* Pulsing ring */}
              <circle cx={targetSvgX} cy={targetSvgY} r={14} fill="#f43f5e" fillOpacity={0.25} />
              <circle cx={targetSvgX} cy={targetSvgY} r={8} fill="#f43f5e" fillOpacity={0.65} filter="url(#glow-pentagon)" />
              <circle cx={targetSvgX} cy={targetSvgY} r={4.5} fill="#ffffff" stroke="#9f1239" strokeWidth={2} />
              {/* Coordinates label */}
              <text x={targetSvgX} y={targetSvgY - 14} textAnchor="middle" style={{ fontSize: 10.5, fontWeight: 800, fill: 'var(--ink)' }}>
                ({x.toFixed(1)}, {y.toFixed(1)})
              </text>
            </g>
          </svg>
        </div>

        {/* Details & Proportions Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ padding: 14, borderRadius: 10, background: 'var(--canvas)', border: '1px solid var(--border)' }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>Zona Duval Pentagon Terdeteksi:</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span style={{
                padding: '4px 10px',
                borderRadius: 6,
                fontWeight: 800,
                fontSize: '0.85rem',
                background: activeZoneObj?.color || '#3b82f6',
                color: '#ffffff',
              }}>
                {activeZoneObj?.id || zone}
              </span>
              <strong style={{ fontSize: '0.9rem', color: 'var(--ink)' }}>{activeZoneObj?.name || zone_label}</strong>
            </div>
            <p style={{ margin: '8px 0 0 0', fontSize: '0.78rem', color: 'var(--muted)', lineHeight: 1.4 }}>
              {activeZoneObj?.desc || zone_desc}
            </p>
          </div>

          <div style={{ padding: 14, borderRadius: 10, background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--ink)', display: 'block', marginBottom: 8 }}>
              Komposisi 5 Gas Terlarut:
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.76rem' }}>
              {[
                { gas: 'H₂ (Hidrogen)', pct: percentages?.H2, col: '#c084fc' },
                { gas: 'C₂H₆ (Etana)', pct: percentages?.C2H6, col: '#34d399' },
                { gas: 'CH₄ (Metana)', pct: percentages?.CH4, col: '#fbbf24' },
                { gas: 'C₂H₄ (Etilena)', pct: percentages?.C2H4, col: '#f97316' },
                { gas: 'C₂H₂ (Asetilena)', pct: percentages?.C2H2, col: '#06b6d4' },
              ].map((item) => (
                <div key={item.gas} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: item.col }} />
                    <span>{item.gas}</span>
                  </span>
                  <strong style={{ color: 'var(--ink)' }}>{Number(item.pct || 0).toFixed(1)}%</strong>
                </div>
              ))}
            </div>
          </div>

          <div style={{ padding: 12, borderRadius: 8, background: 'var(--attention-soft)', border: '1px solid color-mix(in srgb, var(--attention) 40%, transparent)', fontSize: '0.76rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--attention)', fontWeight: 700, marginBottom: 4 }}>
              <AlertTriangle size={14} />
              <span>Standar Duval Pentagon</span>
            </div>
            <p style={{ margin: 0, color: 'var(--ink)', lineHeight: 1.35 }}>
              Metode Duval Pentagon 1 memadukan lima gas hidrokarbon kunci dalam koordinat polar polarimetri untuk membedakan fenomena pelepasan termal versus lucutan listrik secara komprehensif.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Component: DGA Historical Gas Trend Chart & Table ───────────────────────

function DgaHistoryChart({ history, transformerName }) {
  const [activeGases, setActiveGases] = useState({
    H2: true,
    CH4: true,
    C2H6: false,
    C2H4: true,
    C2H2: true,
    CO: true,
    CO2: false,
    TDCG: true,
  })
  const [hoverPoint, setHoverPoint] = useState(null)

  const rows = history || []
  if (rows.length === 0) {
    return (
      <div className="chart-empty">
        <Clock size={32} />
        <strong>Belum Ada Riwayat Sampling DGA</strong>
        <span>Riwayat pengujian laboratorium akan terakumulasi otomatis seiring sampling berkala.</span>
      </div>
    )
  }

  const sorted = [...rows].sort((a, b) => new Date(a.date) - new Date(b.date))

  const gasColors = {
    H2: '#8b5cf6',
    CH4: '#3b82f6',
    C2H6: '#10b981',
    C2H4: '#ec4899',
    C2H2: '#06b6d4',
    CO: '#f59e0b',
    CO2: '#64748b',
    TDCG: '#ef4444',
  }

  // Determine max value for active gases
  let maxVal = 100
  sorted.forEach((r) => {
    Object.keys(activeGases).forEach((k) => {
      if (activeGases[k]) {
        const val = Number(r[k] ?? (k === 'TDCG' ? r.tdcg : 0))
        if (!Number.isNaN(val) && val > maxVal) maxVal = val
      }
    })
  })
  maxVal = Math.ceil(maxVal * 1.15)

  const W = 680
  const H = 280
  const padLeft = 60
  const padRight = 30
  const padTop = 30
  const padBottom = 50

  const nPoints = sorted.length
  const xStep = nPoints > 1 ? (W - padLeft - padRight) / (nPoints - 1) : 0

  function getX(idx) {
    return nPoints > 1 ? padLeft + idx * xStep : W / 2
  }

  function getY(val) {
    return padTop + (1 - val / maxVal) * (H - padTop - padBottom)
  }

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title" style={{ flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={18} className="text-blue-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Grafik Riwayat Konsentrasi Gas DGA — {transformerName}</span>
        </div>
        {/* Toggle gas buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {Object.keys(activeGases).map((gas) => (
            <button
              key={gas}
              type="button"
              onClick={() => setActiveGases({ ...activeGases, [gas]: !activeGases[gas] })}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 8px',
                borderRadius: 6,
                fontSize: '0.72rem',
                fontWeight: 700,
                background: activeGases[gas] ? `${gasColors[gas]}20` : 'var(--surface)',
                color: activeGases[gas] ? gasColors[gas] : 'var(--muted)',
                border: `1px solid ${activeGases[gas] ? gasColors[gas] : 'var(--border)'}`,
                cursor: 'pointer',
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: gasColors[gas] }} />
              <span>{gas}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Interactive SVG Chart */}
      <div style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', background: 'var(--surface)', borderRadius: 10 }}>
          {/* Horizontal Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const y = getY(maxVal * frac)
            const tickVal = Math.round(maxVal * frac)
            return (
              <g key={frac}>
                <line x1={padLeft} y1={y} x2={W - padRight} y2={y} stroke="var(--border)" strokeDasharray="3 3" strokeWidth={0.8} />
                <text x={padLeft - 8} y={y + 4} textAnchor="end" className="chart-tick-label" style={{ fontSize: 10, fill: 'var(--muted)' }}>
                  {tickVal}
                </text>
              </g>
            )
          })}

          {/* X Axis dates */}
          {sorted.map((r, idx) => {
            const x = getX(idx)
            return (
              <g key={r.date}>
                <line x1={x} y1={H - padBottom} x2={x} y2={H - padBottom + 5} stroke="var(--border)" strokeWidth={1} />
                <text
                  x={x}
                  y={H - padBottom + 18}
                  textAnchor="middle"
                  style={{ fontSize: 10, fill: 'var(--muted)', fontWeight: 600 }}
                >
                  {r.date}
                </text>
              </g>
            )
          })}

          {/* Gas Lines and Circles */}
          {Object.keys(activeGases).map((gas) => {
            if (!activeGases[gas]) return null
            const pointsStr = sorted.map((r, idx) => {
              const val = Number(r[gas] ?? (gas === 'TDCG' ? r.tdcg : 0))
              return `${getX(idx).toFixed(1)},${getY(val).toFixed(1)}`
            }).join(' ')

            return (
              <g key={`series-${gas}`}>
                <polyline
                  points={pointsStr}
                  fill="none"
                  stroke={gasColors[gas]}
                  strokeWidth={gas === 'TDCG' ? 2.5 : 1.8}
                  strokeDasharray={gas === 'TDCG' ? '5 3' : undefined}
                />
                {sorted.map((r, idx) => {
                  const val = Number(r[gas] ?? (gas === 'TDCG' ? r.tdcg : 0))
                  const px = getX(idx)
                  const py = getY(val)
                  return (
                    <circle
                      key={`pt-${gas}-${idx}`}
                      cx={px}
                      cy={py}
                      r={4}
                      fill={gasColors[gas]}
                      stroke="#ffffff"
                      strokeWidth={1.5}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setHoverPoint({ gas, val, date: r.date, x: px, y: py })}
                      onMouseLeave={() => setHoverPoint(null)}
                    />
                  )
                })}
              </g>
            )
          })}

          {/* Tooltip */}
          {hoverPoint && (
            <g style={{ pointerEvents: 'none' }}>
              <rect
                x={Math.min(W - 120, Math.max(padLeft, hoverPoint.x - 55))}
                y={hoverPoint.y - 36}
                width={110}
                height={28}
                rx={6}
                fill="var(--ink)"
                fillOpacity={0.92}
              />
              <text
                x={Math.min(W - 120, Math.max(padLeft, hoverPoint.x - 55)) + 55}
                y={hoverPoint.y - 18}
                textAnchor="middle"
                style={{ fontSize: 10.5, fontWeight: 700, fill: '#ffffff' }}
              >
                {hoverPoint.gas}: {hoverPoint.val.toFixed(1)} ppm
              </text>
            </g>
          )}

          {/* Y Axis title */}
          <text x={16} y={H / 2} textAnchor="middle" style={{ fontSize: 11, fontWeight: 700, fill: 'var(--muted)' }} transform={`rotate(-90, 16, ${H / 2})`}>
            Konsentrasi (ppm)
          </text>
        </svg>
      </div>

      {/* Sampling History Table */}
      <div style={{ marginTop: 16 }}>
        <strong style={{ fontSize: '0.85rem', color: 'var(--ink)', display: 'block', marginBottom: 8 }}>
          Tabel Riwayat Pengujian Laboratorium DGA
        </strong>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ fontSize: '0.78rem' }}>
            <thead>
              <tr>
                <th>Tanggal Uji</th>
                <th>TDCG (ppm)</th>
                <th>H₂</th>
                <th>CH₄</th>
                <th>C₂H₆</th>
                <th>C₂H₄</th>
                <th>C₂H₂</th>
                <th>CO</th>
                <th>CO₂</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.date}>
                  <td><strong>{r.date}</strong></td>
                  <td><strong style={{ color: 'var(--critical)' }}>{Number(r.tdcg ?? 0).toFixed(0)}</strong></td>
                  <td>{Number(r.H2 ?? 0).toFixed(1)}</td>
                  <td>{Number(r.CH4 ?? 0).toFixed(1)}</td>
                  <td>{Number(r.C2H6 ?? 0).toFixed(1)}</td>
                  <td>{Number(r.C2H4 ?? 0).toFixed(1)}</td>
                  <td><strong style={{ color: Number(r.C2H2 || 0) > 1 ? 'var(--critical)' : 'inherit' }}>{Number(r.C2H2 ?? 0).toFixed(1)}</strong></td>
                  <td>{Number(r.CO ?? 0).toFixed(0)}</td>
                  <td>{Number(r.CO2 ?? 0).toFixed(0)}</td>
                  <td>
                    <span className={`cbm-badge cbm-badge--${(r.status || '').toLowerCase().includes('normal') ? 'ok' : 'warn'}`} style={{ fontSize: '0.68rem', padding: '2px 6px' }}>
                      {r.status || 'NORMAL'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Component: Rogers Ratio & IEC 60599 Method ──────────────────────────────

function RogersRatioCard({ gases, rogersData }) {
  const rogers = rogersData || evalRogersClient(gases)
  const { r1_c2h2_c2h4, r2_ch4_h2, r3_c2h4_c2h6, co2_co_ratio, diag_code, diagnosis, description, severity, paper_diagnosis } = rogers

  const standardCases = [
    { code: '0-0-0', r1: '< 0.1', r2: '0.1 - 1.0', r3: '< 1.0', diag: 'Normal Deterioration', note: 'Degradasi wajar tanpa anomali aktif' },
    { code: '0-1-0', r1: '< 0.1', r2: '< 0.1', r3: '< 1.0', diag: 'Partial Discharge (Corona)', note: 'Pelepasan muatan listrik berdaya rendah' },
    { code: '1-0-2', r1: '0.1 - 3.0', r2: '0.1 - 1.0', r3: '> 3.0', diag: 'Continuous Sparking', note: 'Percikan bunga api ke elektroda mengambang' },
    { code: '1-0-1', r1: '0.1 - 3.0', r2: '0.1 - 1.0', r3: '0.1 - 3.0', diag: 'Arc with Power Follow-through', note: 'Busur api energi tinggi (Arcing)' },
    { code: '0-0-1', r1: '< 0.1', r2: '0.1 - 1.0', r3: '1.0 - 3.0', diag: 'Thermal Fault 150°C - 200°C', note: 'Overheating termal suhu rendah' },
    { code: '0-2-1', r1: '< 0.1', r2: '> 1.0', r3: '1.0 - 3.0', diag: 'Thermal Fault 200°C - 300°C', note: 'Overheating suhu menengah pada inti/kabel' },
    { code: '0-2-2', r1: '< 0.1', r2: '> 1.0', r3: '> 3.0', diag: 'Thermal Fault 300°C - 700°C', note: 'Pemanasan konduktor berat' },
    { code: '0-0-2', r1: '< 0.1', r2: '0.1 - 1.0', r3: '> 3.0', diag: 'Thermal Fault > 700°C', note: 'Suhu ekstrem, pembentukan jelaga/karbon' },
  ]

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChart2 size={18} className="text-cyan-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Metode Rasio Rogers & IEC 60599</span>
          <span className={`duval-diag-pill ${severity === 'HIGH' ? 'duval-diag-pill--danger' : ''}`}>{diagnosis}</span>
        </div>
      </div>

      {/* 4 Ratio Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 18 }}>
        <div className="cbm-gas-card" style={{ borderLeft: '4px solid #06b6d4' }}>
          <span className="cbm-gas-name">R1: C₂H₂ / C₂H₄</span>
          <strong className="cbm-gas-value">{r1_c2h2_c2h4.toFixed(3)}</strong>
          <span className="cbm-gas-unit">Rasio Gas Listrik</span>
        </div>
        <div className="cbm-gas-card" style={{ borderLeft: '4px solid #3b82f6' }}>
          <span className="cbm-gas-name">R2: CH₄ / H₂</span>
          <strong className="cbm-gas-value">{r2_ch4_h2.toFixed(3)}</strong>
          <span className="cbm-gas-unit">Rasio Korona/Termal</span>
        </div>
        <div className="cbm-gas-card" style={{ borderLeft: '4px solid #ec4899' }}>
          <span className="cbm-gas-name">R3: C₂H₄ / C₂H₆</span>
          <strong className="cbm-gas-value">{r3_c2h4_c2h6.toFixed(3)}</strong>
          <span className="cbm-gas-unit">Rasio Suhu Termal</span>
        </div>
        <div className="cbm-gas-card" style={{ borderLeft: '4px solid #f59e0b' }}>
          <span className="cbm-gas-name">CO₂ / CO (Kertas)</span>
          <strong className="cbm-gas-value">{co2_co_ratio.toFixed(2)}</strong>
          <span className="cbm-gas-unit">{paper_diagnosis}</span>
        </div>
      </div>

      {/* Active Code Callout */}
      <div style={{ padding: 14, borderRadius: 10, background: 'var(--canvas)', border: '1px solid var(--border)', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>Kode Rasio Rogers (R1-R2-R3):</span>
            <strong style={{ fontSize: '1.2rem', color: 'var(--action)', letterSpacing: 1 }}>[{diag_code}]</strong>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>Hasil Evaluasi:</span>
            <strong style={{ fontSize: '1rem', color: 'var(--ink)' }}>{diagnosis}</strong>
          </div>
        </div>
        <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: 'var(--ink)', lineHeight: 1.4 }}>
          {description}
        </p>
      </div>

      {/* IEC 60599 Matrix Table */}
      <div>
        <strong style={{ fontSize: '0.85rem', color: 'var(--ink)', display: 'block', marginBottom: 8 }}>
          Tabel Standar Klasifikasi Rasio IEC 60599
        </strong>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ fontSize: '0.78rem' }}>
            <thead>
              <tr>
                <th>Kode</th>
                <th>R1 (C₂H₂/C₂H₄)</th>
                <th>R2 (CH₄/H₂)</th>
                <th>R3 (C₂H₄/C₂H₆)</th>
                <th>Diagnosa IEC 60599</th>
                <th>Karakteristik Gangguan</th>
              </tr>
            </thead>
            <tbody>
              {standardCases.map((sc) => {
                const isActive = diag_code === sc.code
                return (
                  <tr key={sc.code} style={{ background: isActive ? 'color-mix(in srgb, var(--action) 12%, transparent)' : undefined }}>
                    <td>
                      <strong style={{ color: isActive ? 'var(--action)' : 'inherit' }}>
                        {sc.code} {isActive && '★'}
                      </strong>
                    </td>
                    <td>{sc.r1}</td>
                    <td>{sc.r2}</td>
                    <td>{sc.r3}</td>
                    <td><strong>{sc.diag}</strong></td>
                    <td style={{ color: 'var(--muted)' }}>{sc.note}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Component: Key Gas Method (IEEE C57.104) ────────────────────────────────

function KeyGasCard({ gases, keyGasData }) {
  const kg = keyGasData || evalKeyGasClient(gases)
  const { dominant_gas, fault_type, primary_mechanism, proportions, scores } = kg

  const keyGasPatterns = [
    {
      id: 'thermal_oil',
      name: 'Thermal Oil Degradation',
      keyGas: 'C₂H₄ (Etilena ~63%)',
      desc: 'Pemanasan minyak suhu tinggi menyebabkan pemecahan ikatan hidrokarbon menghasilkan etilena dominan.',
      score: scores?.thermal_oil || 0,
      color: '#ec4899',
    },
    {
      id: 'thermal_cellulose',
      name: 'Thermal Cellulose (Paper)',
      keyGas: 'CO (Karbon Monoksida ~92%)',
      desc: 'Pemanasan berlebih pada kertas/pressboard isolasi belitan melepaskan CO dan CO₂ dalam jumlah besar.',
      score: scores?.thermal_cellulose || 0,
      color: '#f59e0b',
    },
    {
      id: 'corona_pd',
      name: 'Corona / Partial Discharge',
      keyGas: 'H₂ (Hidrogen ~85%)',
      desc: 'Ionisasi medan listrik tinggi pada rongga gas menghasilkan ionisasi hidrogen dominan.',
      score: scores?.corona_pd || 0,
      color: '#8b5cf6',
    },
    {
      id: 'arcing',
      name: 'Electrical Arcing (Flashover)',
      keyGas: 'C₂H₂ (Asetilena ~50%)',
      desc: 'Pelepasan busur api listrik suhu sangat tinggi (> 3000°C) memicu sintesis asetilena secara masif.',
      score: scores?.arcing || 0,
      color: '#06b6d4',
    },
  ]

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Flame size={18} className="text-amber-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Metode Key Gas (IEEE C57.104)</span>
          <span className="duval-diag-pill">{fault_type}</span>
        </div>
      </div>

      {/* Stacked Proportions Bar */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.78rem' }}>
          <span style={{ fontWeight: 700, color: 'var(--ink)' }}>Distribusi Persentase 6 Gas Kunci Aktual:</span>
          <span style={{ color: 'var(--muted)' }}>Gas dominan: <strong style={{ color: 'var(--action)' }}>{dominant_gas} ({proportions?.[dominant_gas]}%)</strong></span>
        </div>

        <div style={{ display: 'flex', height: 26, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
          {[
            { key: 'H2', col: '#8b5cf6', label: 'H₂' },
            { key: 'CH4', col: '#3b82f6', label: 'CH₄' },
            { key: 'C2H6', col: '#10b981', label: 'C₂H₆' },
            { key: 'C2H4', col: '#ec4899', label: 'C₂H₄' },
            { key: 'C2H2', col: '#06b6d4', label: 'C₂H₂' },
            { key: 'CO', col: '#f59e0b', label: 'CO' },
          ].map((item) => {
            const pct = proportions?.[item.key] || 0
            if (pct <= 0) return null
            return (
              <div
                key={item.key}
                style={{
                  width: `${pct}%`,
                  background: item.col,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  fontSize: '0.68rem',
                  fontWeight: 800,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  padding: '0 4px',
                }}
                title={`${item.label}: ${pct}%`}
              >
                {pct > 5 ? `${item.label} ${pct}%` : ''}
              </div>
            )
          })}
        </div>
      </div>

      {/* Key Gas Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginBottom: 16 }}>
        {keyGasPatterns.map((pat) => {
          const isDominant = fault_type.toLowerCase().includes(pat.id.replace('_', ' ')) || fault_type.toLowerCase().includes(pat.name.toLowerCase().slice(0, 10))
          return (
            <div
              key={pat.id}
              style={{
                padding: 14,
                borderRadius: 10,
                background: isDominant ? 'color-mix(in srgb, var(--action) 8%, var(--surface))' : 'var(--surface)',
                border: `1.5px solid ${isDominant ? pat.color : 'var(--border)'}`,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--ink)' }}>{pat.name}</strong>
                  <span style={{ fontSize: '0.72rem', fontWeight: 800, color: pat.color }}>{pat.score}% Cocok</span>
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'block', marginBottom: 6 }}>
                  Kunci: <strong>{pat.keyGas}</strong>
                </span>
                <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--ink)', lineHeight: 1.35 }}>
                  {pat.desc}
                </p>
              </div>
              <div style={{ marginTop: 10, height: 6, borderRadius: 3, background: 'var(--border)', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, pat.score)}%`, height: '100%', background: pat.color }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Diagnostic explanation */}
      <div style={{ padding: 12, borderRadius: 8, background: 'var(--canvas)', border: '1px solid var(--border)', fontSize: '0.78rem' }}>
        <strong style={{ color: 'var(--ink)', display: 'block', marginBottom: 4 }}>Mekanisme Gangguan Teridentifikasi:</strong>
        <p style={{ margin: 0, color: 'var(--muted)', lineHeight: 1.4 }}>
          {primary_mechanism}
        </p>
      </div>
    </div>
  )
}

// ─── Component: Gas Prediction & Rate of Rise (IEEE C57.104) ─────────────────

function GasPredictionCard({ gases, history, predictionData }) {
  const pred = predictionData || evalPredictionClient(history, gases)
  const { interval_days, rate_ppm_day, rate_ppm_month, rate_status, rate_desc, action_advice, days_to_warning, forecast_3m, forecast_6m, forecast_12m } = pred

  const gasList = [
    { key: 'H2', name: 'Hidrogen (H₂)', alertRate: 5.0 },
    { key: 'CH4', name: 'Metana (CH₄)', alertRate: 2.0 },
    { key: 'C2H6', name: 'Etana (C₂H₆)', alertRate: 2.0 },
    { key: 'C2H4', name: 'Etilena (C₂H₄)', alertRate: 2.0 },
    { key: 'C2H2', name: 'Asetilena (C₂H₂)', alertRate: 0.1 },
    { key: 'CO', name: 'Karbon Monoksida (CO)', alertRate: 10.0 },
    { key: 'CO2', name: 'Karbon Dioksida (CO₂)', alertRate: 50.0 },
    { key: 'TDCG', name: 'Total Gas (TDCG)', alertRate: 10.0 },
  ]

  const statusColor = rate_status === 'CRITICAL' ? 'var(--critical)' : (rate_status === 'ALERT' ? 'var(--attention)' : (rate_status === 'PREWARNING' ? '#f59e0b' : 'var(--healthy)'))

  return (
    <div className="chart-container duval-workspace-card">
      <div className="chart-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={18} className="text-emerald-500" />
          <span style={{ fontWeight: 700, fontSize: '0.98rem' }}>Prediksi Laju Pembentukan Gas & Proyeksi Nilai Masa Depan</span>
          <span className={`duval-diag-pill ${rate_status === 'CRITICAL' ? 'duval-diag-pill--danger' : ''}`}>
            Laju: {rate_status}
          </span>
        </div>
      </div>

      {/* Status banner */}
      <div style={{ padding: 14, borderRadius: 10, background: 'var(--canvas)', border: `1.5px solid ${statusColor}`, marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <div>
            <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>
              Evaluasi Laju Pembentukan Gas (Interval: {interval_days} Hari):
            </span>
            <strong style={{ fontSize: '1rem', color: statusColor }}>{rate_desc}</strong>
          </div>
          {days_to_warning != null && (
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>Estimasi Capai Ambang Waspada (TDCG 720 ppm):</span>
              <strong style={{ fontSize: '1.05rem', color: days_to_warning < 60 ? 'var(--critical)' : 'var(--ink)' }}>
                {days_to_warning === 0 ? 'Sudah Melebihi Batas' : `${days_to_warning} Hari ke Depan`}
              </strong>
            </div>
          )}
        </div>
        <p style={{ margin: '8px 0 0 0', fontSize: '0.78rem', color: 'var(--ink)', lineHeight: 1.4 }}>
          <strong>Rekomendasi CBM:</strong> {action_advice}
        </p>
      </div>

      {/* Prediction Table */}
      <div>
        <strong style={{ fontSize: '0.85rem', color: 'var(--ink)', display: 'block', marginBottom: 8 }}>
          Proyeksi Konsentrasi Gas Sesuai Tren Laju Pembentukan (ppm)
        </strong>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table" style={{ fontSize: '0.78rem' }}>
            <thead>
              <tr>
                <th>Parameter Gas</th>
                <th>Saat Ini (ppm)</th>
                <th>Laju (ppm/hari)</th>
                <th>Laju (ppm/bulan)</th>
                <th>+3 Bulan (+90h)</th>
                <th>+6 Bulan (+180h)</th>
                <th>+12 Bulan (+365h)</th>
                <th>Batas Alert IEEE</th>
              </tr>
            </thead>
            <tbody>
              {gasList.map((g) => {
                const cur = Number(gases?.[g.key] ?? (g.key === 'TDCG' ? Object.keys(gases || {}).reduce((acc, k) => acc + (k !== 'CO2' && k !== 'H2O' ? Number(gases[k] || 0) : 0), 0) : 0))
                const rDay = Number(rate_ppm_day?.[g.key] || 0)
                const rMonth = Number(rate_ppm_month?.[g.key] || 0)
                const f3 = Number(forecast_3m?.[g.key] ?? cur)
                const f6 = Number(forecast_6m?.[g.key] ?? cur)
                const f12 = Number(forecast_12m?.[g.key] ?? cur)
                const isAlert = rDay >= g.alertRate

                return (
                  <tr key={g.key} style={{ background: isAlert ? 'color-mix(in srgb, var(--critical) 6%, transparent)' : undefined }}>
                    <td>
                      <strong style={{ color: g.key === 'TDCG' || g.key === 'C2H2' ? 'var(--critical)' : 'inherit' }}>
                        {g.name}
                      </strong>
                    </td>
                    <td><strong>{cur.toFixed(1)}</strong></td>
                    <td style={{ color: isAlert ? 'var(--critical)' : 'inherit', fontWeight: isAlert ? 700 : 400 }}>
                      {rDay > 0 ? `+${rDay.toFixed(3)}` : rDay.toFixed(3)}
                    </td>
                    <td>{rMonth > 0 ? `+${rMonth.toFixed(2)}` : rMonth.toFixed(2)}</td>
                    <td>{f3.toFixed(1)}</td>
                    <td>{f6.toFixed(1)}</td>
                    <td><strong style={{ color: f12 > cur * 1.5 ? 'var(--critical)' : 'inherit' }}>{f12.toFixed(1)}</strong></td>
                    <td style={{ color: 'var(--muted)' }}>&gt; {g.alertRate} ppm/hari</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Sub-Tab Items Configuration ─────────────────────────────────────────────

const DGA_SUBTABS = [
  { id: 'segitiga', label: 'Segitiga Duval 1', icon: Triangle },
  { id: 'pentagon', label: 'Pentagon Duval 1', icon: Compass },
  { id: 'trend', label: 'Grafik Riwayat Gas', icon: TrendingUp },
  { id: 'rogers', label: 'Rasio Rogers & IEC', icon: BarChart2 },
  { id: 'keygas', label: 'Metode Key Gas', icon: Flame },
  { id: 'prediction', label: 'Prediksi & Laju Gas', icon: Clock },
]

// ─── Duval / DGA Tab Workspace ────────────────────────────────────────────────

function DuvalTab() {
  const [mode, setMode] = useState('asset') // 'asset' | 'simulator'
  const [dgaSubTab, setDgaSubTab] = useState('segitiga')
  const [transformers, setTransformers] = useState([])
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState(null)
  const [status, setStatus] = useState('loading')

  // Simulator state with all 7 key gases
  const [simGases, setSimGases] = useState({
    CH4: 40,
    C2H4: 280,
    C2H2: 12,
    H2: 50,
    C2H6: 30,
    CO: 450,
    CO2: 2400,
  })

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

  // Active gases depending on mode
  const activeGases = mode === 'simulator' ? simGases : (detail?.gases ?? {})
  const activeName = mode === 'simulator' ? 'Simulasi Laboratorium DGA' : (detail?.name ?? selected)

  // Recalculate diagnosis for simulator or use detail diagnosis
  const detectedZone = detectDuvalZone(activeGases.CH4, activeGases.C2H4, activeGases.C2H2)
  const diagnosis = mode === 'simulator'
    ? (detectedZone ? `${detectedZone.id} (${detectedZone.fullLabel})` : 'Normal')
    : (detail?.duval_diag ?? detail?.diagnosis?.duval ?? (detectedZone ? `${detectedZone.id} (${detectedZone.fullLabel})` : '—'))

  const simTdcg = Number(activeGases.H2 || 0) + Number(activeGases.CH4 || 0) + Number(activeGases.C2H6 || 0) + Number(activeGases.C2H4 || 0) + Number(activeGases.C2H2 || 0) + Number(activeGases.CO || 0)
  const tdcg = mode === 'simulator' ? simTdcg : detail?.tdcg
  const statusLabel = mode === 'simulator'
    ? (simTdcg > 4630 ? 'CRITICAL' : (simTdcg > 1920 ? 'ALERT' : (simTdcg > 720 ? 'WARNING' : 'NORMAL')))
    : (detail?.status ?? '—')

  return (
    <div className="cbm-tab-content">
      {/* Mode Switcher */}
      <div className="duval-mode-switcher">
        <button
          type="button"
          className={`duval-mode-btn ${mode === 'asset' ? 'duval-mode-btn--active' : ''}`}
          onClick={() => setMode('asset')}
        >
          <Activity size={15} />
          <span>Data Trafo PLTU Terpasang</span>
        </button>
        <button
          type="button"
          className={`duval-mode-btn ${mode === 'simulator' ? 'duval-mode-btn--active' : ''}`}
          onClick={() => setMode('simulator')}
        >
          <Sliders size={15} />
          <span>Simulator & Uji Gas CBM</span>
        </button>
      </div>

      {mode === 'asset' ? (
        <div className="cbm-controls">
          <label htmlFor="transformer-select" className="cbm-control-label">Pilih Transformer</label>
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
              {tdcg != null && <span className="cbm-badge cbm-badge--neutral">TDCG: {Number(tdcg).toFixed(0)} ppm</span>}
              {diagnosis !== '—' && <span className="cbm-badge cbm-badge--info">Duval: {diagnosis}</span>}
            </div>
          )}
        </div>
      ) : (
        <div className="duval-simulator-panel">
          <div className="duval-simulator-header">
            <div>
              <strong style={{ fontSize: '0.92rem', color: 'var(--ink)' }}>Uji Cepat Gas Terlarut (Simulasi Laboratorium)</strong>
              <p style={{ margin: '3px 0 0 0', fontSize: '0.78rem', color: 'var(--muted)' }}>
                Geser nilai ppm gas untuk mengamati Segitiga Duval, Pentagon Duval, Rasio Rogers, Key Gas, dan Prediksi kenaikan seketika.
              </p>
            </div>
            <div className="cbm-badges">
              <span className={`cbm-badge cbm-badge--${statusLabel === 'NORMAL' ? 'ok' : 'warn'}`}>
                Status: {statusLabel}
              </span>
              <span className="cbm-badge cbm-badge--neutral">TDCG: {simTdcg.toFixed(0)} ppm</span>
              {detectedZone && <span className="cbm-badge cbm-badge--info">Zona: {detectedZone.id}</span>}
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div className="duval-preset-bar">
            <span className="duval-preset-title">Preset Gangguan:</span>
            {DUVAL_PRESETS.map((p) => (
              <button
                key={p.name}
                type="button"
                className="duval-preset-pill"
                onClick={() => setSimGases(p.gases)}
              >
                {p.name}
              </button>
            ))}
          </div>

          {/* Gas Sliders Grid (All 7 gases) */}
          <div className="duval-sliders-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            {[
              { key: 'CH4', label: 'Metana (CH₄)', max: 400, color: '#3b82f6', unit: 'ppm' },
              { key: 'C2H4', label: 'Etilena (C₂H₄)', max: 400, color: '#ec4899', unit: 'ppm' },
              { key: 'C2H2', label: 'Asetilena (C₂H₂)', max: 250, color: '#06b6d4', unit: 'ppm' },
              { key: 'H2', label: 'Hidrogen (H₂)', max: 600, color: '#8b5cf6', unit: 'ppm' },
              { key: 'C2H6', label: 'Etana (C₂H₆)', max: 300, color: '#10b981', unit: 'ppm' },
              { key: 'CO', label: 'Karbon Monoksida (CO)', max: 1200, color: '#f59e0b', unit: 'ppm' },
              { key: 'CO2', label: 'Karbon Dioksida (CO₂)', max: 8000, color: '#64748b', unit: 'ppm' },
            ].map((gas) => (
              <div key={gas.key} className="duval-slider-card">
                <div className="duval-slider-label">
                  <span>{gas.label}</span>
                  <strong style={{ color: gas.color }}>{simGases[gas.key]} {gas.unit}</strong>
                </div>
                <input
                  type="range"
                  min="0"
                  max={gas.max}
                  value={simGases[gas.key]}
                  onChange={(e) => setSimGases({ ...simGases, [gas.key]: Number(e.target.value) })}
                  className="duval-slider-input"
                  style={{ accentColor: gas.color }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {status === 'error' && mode === 'asset' && (
        <div className="notice notice--error">
          <strong>Data DGA tidak dapat dimuat.</strong>
          <span>Pastikan FastAPI berjalan di port 8000. Anda tetap dapat menggunakan Simulator & Uji Gas di atas.</span>
        </div>
      )}

      {/* DGA Sub-Navigation Tabs */}
      <div className="dga-subtab-bar" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '14px 0 6px 0' }}>
        {DGA_SUBTABS.map((tab) => {
          const Icon = tab.icon
          const isActive = dgaSubTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              className={`dga-subtab-btn ${isActive ? 'dga-subtab-btn--active' : ''}`}
              onClick={() => setDgaSubTab(tab.id)}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Active Sub-Tab View */}
      {dgaSubTab === 'segitiga' && (
        <DuvalTriangle
          gases={activeGases}
          transformerName={activeName}
          duvalDiag={diagnosis}
          history={mode === 'asset' ? detail?.history : []}
        />
      )}

      {dgaSubTab === 'pentagon' && (
        <DuvalPentagon
          gases={activeGases}
          transformerName={activeName}
          pentagonData={detail?.diagnosis?.pentagon}
          history={mode === 'asset' ? detail?.history : []}
        />
      )}

      {dgaSubTab === 'trend' && (
        <DgaHistoryChart
          history={mode === 'asset' ? detail?.history : []}
          transformerName={activeName}
        />
      )}

      {dgaSubTab === 'rogers' && (
        <RogersRatioCard
          gases={activeGases}
          rogersData={detail?.diagnosis?.rogers}
        />
      )}

      {dgaSubTab === 'keygas' && (
        <KeyGasCard
          gases={activeGases}
          keyGasData={detail?.diagnosis?.key_gas}
        />
      )}

      {dgaSubTab === 'prediction' && (
        <GasPredictionCard
          gases={activeGases}
          history={mode === 'asset' ? detail?.history : []}
          predictionData={detail?.prediction}
        />
      )}

      {/* Gas Concentration Cards (always visible for quick reference) */}
      <div className="cbm-gas-grid" style={{ marginTop: 16 }}>
        {['H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO', 'CO2'].map((gas) => {
          const val = activeGases[gas]
          return val != null ? (
            <div key={gas} className="cbm-gas-card">
              <span className="cbm-gas-name">{gas}</span>
              <strong className="cbm-gas-value">{Number(val).toFixed(1)}</strong>
              <span className="cbm-gas-unit">ppm</span>
            </div>
          ) : null
        })}
      </div>
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

function McsaTab() {
  const [summary, setSummary] = useState(null)
  const [equipment, setEquipment] = useState([])
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    const controller = new AbortController()
    setStatus('loading')
    Promise.all([
      getMcsaSummary(controller.signal),
      getMcsaEquipmentList({}, controller.signal),
    ])
      .then(([sumRes, eqRes]) => {
        setSummary(sumRes)
        setEquipment(eqRes.equipment || [])
        setStatus('ready')
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setStatus('error')
      })
    return () => controller.abort()
  }, [])

  const counts = summary?.counts || { Normal: 0, Alarm: 0, High: 0 }
  const attentionList = equipment.filter((e) => ['Alarm', 'High'].includes(e.status || e.condition))

  return (
    <div className="cbm-tab-content">
      {status === 'error' && (
        <div className="notice notice--error">
          <strong>Data MCSA tidak dapat dimuat.</strong>
          <span>Pastikan FastAPI berjalan pada port 8000 dan data MCSA tersedia.</span>
        </div>
      )}

      {status === 'loading' && (
        <div className="chart-loading"><RefreshCw size={20} className="spin" />Memuat data MCSA motor…</div>
      )}

      {status === 'ready' && (
        <>
          {/* Summary Strip */}
          <div className="cbm-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--ink)' }}>Kondisi Motor Current Signature (MCSA)</h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>Pemantauan kesehatan rotor bar & deviasi kelistrikan 93 motor PLTU Jeranjang</span>
              </div>
              <a href="/mcsa" className="button button--secondary" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', textDecoration: 'none' }}>
                <Zap size={15} color="#0891b2" />
                Buka Workspace MCSA Lengkap
              </a>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
              <div style={{ padding: '14px', borderRadius: '10px', background: 'var(--canvas)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--muted)', display: 'block' }}>Total Motor</span>
                <strong style={{ fontSize: '1.4rem', color: 'var(--ink)' }}>{summary?.total_equipment || equipment.length}</strong>
              </div>
              <div style={{ padding: '14px', borderRadius: '10px', background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--healthy)', display: 'block' }}>Normal</span>
                <strong style={{ fontSize: '1.4rem', color: 'var(--healthy)' }}>{counts.Normal}</strong>
              </div>
              <div style={{ padding: '14px', borderRadius: '10px', background: 'var(--attention-soft)', border: '1px solid color-mix(in srgb, var(--attention) 45%, transparent)' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--attention)', display: 'block' }}>Alarm (Waspada)</span>
                <strong style={{ fontSize: '1.4rem', color: 'var(--attention)' }}>{counts.Alarm}</strong>
              </div>
              <div style={{ padding: '14px', borderRadius: '10px', background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--critical)', display: 'block' }}>High / Kritis</span>
                <strong style={{ fontSize: '1.4rem', color: 'var(--critical)' }}>{counts.High}</strong>
              </div>
            </div>
          </div>

          {/* Attention Motors Table */}
          <div className="cbm-card" style={{ padding: '20px', marginTop: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <strong style={{ fontSize: '0.92rem', color: 'var(--ink)' }}>
                Daftar Motor dalam Perhatian (Status Alarm / High)
              </strong>
              <span style={{ fontSize: '0.76rem', color: 'var(--muted)' }}>
                {attentionList.length} motor memerlukan verifikasi
              </span>
            </div>

            {attentionList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--healthy)' }}>
                Seluruh motor berada dalam kondisi operasi normal.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table" style={{ fontSize: '0.8rem' }}>
                  <thead>
                    <tr>
                      <th>Motor Equipment</th>
                      <th>Unit</th>
                      <th>Tegangan</th>
                      <th>Kondisi</th>
                      <th>Rotor Bar</th>
                      <th>Tanggal Uji</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attentionList.slice(0, 10).map((m) => (
                      <tr key={m.equipment}>
                        <td><strong>{m.equipment}</strong></td>
                        <td>{m.unit}</td>
                        <td>{m.voltage}</td>
                        <td>
                          <span className={`status status--${m.status === 'High' ? 'critical' : 'attention'}`}>
                            <i />{m.status}
                          </span>
                        </td>
                        <td>{m.rotorbar_status || 'Normal'}</td>
                        <td>{m.last_date || '-'}</td>
                        <td>
                          <a href={`/mcsa?search=${encodeURIComponent(m.equipment)}`} style={{ color: 'var(--action)', textDecoration: 'none', fontWeight: 600 }}>
                            Lihat &rarr;
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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
          <p>Visualisasi interaktif kondisi aset — Duval Triangle, MCSA & Motor, Parameter Vibrasi, Tren Kesehatan.</p>
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
      {activeTab === 'mcsa' && <McsaTab />}
      {activeTab === 'vibration' && <VibrationTab />}
      {activeTab === 'trend' && <TrendTab />}
    </div>
  )
}

