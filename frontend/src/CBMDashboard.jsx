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
  Activity, AlertTriangle, BarChart2, CheckCircle2, Compass, Download, Eye, HelpCircle, Info, Layers, RefreshCw, Sliders, TrendingUp, Triangle, Zap,
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
              <polygon points="0 0, 7 3.5, 0 7" fill="#0f172a" />
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
            stroke="#0f172a"
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
              <line x1={x} y1={y} x2={x - 6} y2={y - 3.5} stroke="#334155" strokeWidth={1.5} />
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
              <line x1={x} y1={y} x2={x + 6} y2={y - 3.5} stroke="#334155" strokeWidth={1.5} />
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
              <line x1={x} y1={y} x2={x} y2={y + 6} stroke="#334155" strokeWidth={1.5} />
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
              <text x={projCH4_left.x - 18} y={projCH4_left.y - 3} textAnchor="end" style={{ fontSize: 9.5, fontWeight: 800, fill: '#f43f5e' }}>
                {pch4.toFixed(1)}%
              </text>
              {/* %C2H4 Right badge */}
              <circle cx={projC2H4_top.x} cy={projC2H4_top.y} r={3.5} fill="#f43f5e" />
              <text x={projC2H4_top.x + 18} y={projC2H4_top.y - 3} textAnchor="start" style={{ fontSize: 9.5, fontWeight: 800, fill: '#f43f5e' }}>
                {pc2h4.toFixed(1)}%
              </text>
              {/* %C2H2 Bottom badge */}
              <circle cx={projC2H2_bot.x} cy={projC2H2_bot.y} r={3.5} fill="#f43f5e" />
              <text x={projC2H2_bot.x} y={projC2H2_bot.y + 25} textAnchor="middle" style={{ fontSize: 9.5, fontWeight: 800, fill: '#f43f5e' }}>
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
                    style={{ fontSize: 7.5, fontWeight: 800, fill: '#0f172a' }}
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
]

// ─── Duval Tab ────────────────────────────────────────────────────────────────

function DuvalTab() {
  const [mode, setMode] = useState('asset') // 'asset' | 'simulator'
  const [transformers, setTransformers] = useState([])
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState(null)
  const [status, setStatus] = useState('loading')

  // Simulator state
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
                Geser nilai ppm gas hidrokarbon untuk mengamati pergeseran koordinat dan deteksi zona kerusakan seketika.
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

          {/* Gas Sliders Grid */}
          <div className="duval-sliders-grid">
            {[
              { key: 'CH4', label: 'Metana (CH₄)', max: 400, color: '#3b82f6', unit: 'ppm' },
              { key: 'C2H4', label: 'Etilena (C₂H₄)', max: 400, color: '#ec4899', unit: 'ppm' },
              { key: 'C2H2', label: 'Asetilena (C₂H₂)', max: 250, color: '#06b6d4', unit: 'ppm' },
              { key: 'H2', label: 'Hidrogen (H₂)', max: 600, color: '#8b5cf6', unit: 'ppm' },
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

      {/* Main Duval Triangle Visualizer */}
      <DuvalTriangle
        gases={activeGases}
        transformerName={activeName}
        duvalDiag={diagnosis}
        history={mode === 'asset' ? detail?.history : []}
      />

      {/* Gas Concentration Cards */}
      <div className="cbm-gas-grid">
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

