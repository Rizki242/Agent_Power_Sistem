/**
 * Logo gear planetary (epicyclic) untuk chat Agent Learning Sistem.
 *
 * Digambar inline sebagai SVG - bukan <img src="...svg"> - karena tiap roda
 * gigi harus berputar sendiri-sendiri dengan arah dan laju berbeda. SVG yang
 * dimuat lewat <img> terisolasi dan tidak bisa disentuh CSS dokumen induk.
 *
 * Geometri dan palet diukur langsung dari GIF referensi (256x256, 80 frame):
 *   - cakram luar  r=124          #14213D
 *   - ring gear    52 gigi, r 100..110   #F4F1EA
 *   - 3 planet     21 gigi, r 33..39, mengorbit pada r=65.5 (terpisah 120 derajat)
 *   - sun          12 gigi, r 20..30     #E0A040
 *
 * Gigi dibentuk dari lingkaran ber-stroke tebal dengan `stroke-dasharray`
 * seukuran pitch gigi. Cara ini menghasilkan gigi persegi khas ikon flat
 * dengan beberapa baris, jauh lebih ringkas daripada path 200+ simpul.
 *
 * Arah putaran mengikuti perilaku GIF aslinya (diukur per frame): carrier dan
 * ring berputar searah jarum jam pada laju berbeda, sun berlawanan arah.
 */

const NAVY = '#14213D'
const CREAM = '#F4F1EA'
const SLATE = '#5D6A7C'
const LIGHT = '#CAD1D8'
const GOLD = '#E0A040'

// Posisi ketiga planet pada orbit r=65.5 di sudut -90, 30, dan 150 derajat.
const PLANETS = [
  { x: 128, y: 62.5 },
  { x: 184.72, y: 160.75 },
  { x: 71.28, y: 160.75 },
]

// Rangka carrier: segitiga yang menghubungkan ketiga poros planet. Di GIF asli
// bagian dekat planet tertutup roda giginya, jadi yang terlihat hanya tengah
// tiap sisi - efek yang sama muncul di sini karena planet digambar setelahnya.
const CARRIER_PATH = `M ${PLANETS[0].x} ${PLANETS[0].y} L ${PLANETS[1].x} ${PLANETS[1].y} L ${PLANETS[2].x} ${PLANETS[2].y} Z`

function PlanetGear() {
  return (
    <g>
      <circle r="36" fill="none" stroke={SLATE} strokeWidth="6" strokeDasharray="4.847 5.924" />
      <circle r="33" fill={SLATE} />
      <circle r="10" fill={CREAM} />
      <circle r="10" fill="none" stroke={LIGHT} strokeWidth="1.5" />
      <circle r="5" fill={NAVY} />
    </g>
  )
}

/**
 * @param {number} [size]  Lebar/tinggi render dalam piksel.
 * @param {boolean} [spinning]  Saat false seluruh animasi berhenti (logo diam).
 * @param {string} [className]  Kelas tambahan pada elemen <svg>.
 * @param {string} [title]  Label aksesibilitas; kosongkan untuk elemen dekoratif.
 * @param {object} [style]  Style inline, dipakai untuk memasang `--pg-dur`.
 */
export default function PlanetaryGear({
  size = 44,
  spinning = false,
  className = '',
  title = '',
  style,
}) {
  const decorative = !title

  return (
    <svg
      className={`pgear ${spinning ? 'pgear--spinning' : ''} ${className}`.trim()}
      width={size}
      height={size}
      style={style}
      viewBox="0 0 256 256"
      xmlns="http://www.w3.org/2000/svg"
      role={decorative ? 'presentation' : 'img'}
      aria-hidden={decorative ? 'true' : undefined}
      aria-label={decorative ? undefined : title}
    >
      {decorative ? null : <title>{title}</title>}

      <circle cx="128" cy="128" r="124" fill={NAVY} />

      {/* Ring gear: berputar paling lambat, searah carrier. */}
      <g className="pgear__ring">
        <circle
          cx="128"
          cy="128"
          r="105"
          fill="none"
          stroke={CREAM}
          strokeWidth="10"
          strokeDasharray="5.329 7.359"
        />
        <circle cx="128" cy="128" r="100" fill={CREAM} />
      </g>

      {/* Carrier: membawa ketiga planet mengorbit pusat. */}
      <g className="pgear__carrier">
        <path
          d={CARRIER_PATH}
          fill="none"
          stroke={LIGHT}
          strokeWidth="16"
          strokeLinejoin="round"
        />
        {PLANETS.map((p) => (
          <g key={`${p.x}-${p.y}`} transform={`translate(${p.x} ${p.y})`}>
            {/* Planet juga berputar pada porosnya sendiri, berlawanan carrier. */}
            <g className="pgear__planet">
              <PlanetGear />
            </g>
          </g>
        ))}
      </g>

      {/* Sun: berlawanan arah dengan carrier, seperti epicyclic sungguhan. */}
      <g className="pgear__sun">
        <circle
          cx="128"
          cy="128"
          r="25"
          fill="none"
          stroke={GOLD}
          strokeWidth="10"
          strokeDasharray="5.89 7.199"
        />
        <circle cx="128" cy="128" r="20" fill={GOLD} />
        <circle cx="128" cy="128" r="9" fill={CREAM} />
      </g>
    </svg>
  )
}
