/**
 * Logo gear planetary (epicyclic) untuk Agent Learning Sistem - varian putih.
 *
 * Digambar inline sebagai SVG - bukan <img src="...svg"> - karena tiap roda
 * gigi harus berputar sendiri-sendiri dengan arah dan laju berbeda. SVG yang
 * dimuat lewat <img> terisolasi dan tidak bisa disentuh CSS dokumen induk.
 *
 * Susunan: ring gear **internal** (tepi luar mulus, gigi menghadap ke dalam)
 * yang diam, tiga planet krem yang mengorbit sambil berputar pada porosnya,
 * dan sun amber di pusat yang berputar berlawanan arah. Pola ini mengikuti GIF
 * referensi, di mana posisi poros planet terukur bergeser +30 derajat tiap 20
 * frame sementara sun bergerak ke arah sebaliknya.
 *
 * Gigi dibentuk dari lingkaran ber-stroke tebal dengan `stroke-dasharray`
 * seukuran pitch gigi - jauh lebih ringkas daripada path 200+ simpul.
 *
 * Bagian navy (lubang tengah ring dan celah antar gigi) digambar sebagai bentuk
 * opaque di atas krem, jadi logo ini mengandalkan cakram navy di belakangnya
 * dan tidak dirancang untuk latar transparan.
 */

const NAVY = '#14213D'
const CREAM = '#F4F1EA'
const GOLD = '#E0A040'
// Rangka carrier: navy yang dinaikkan terangnya supaya terbaca di atas cakram.
const ARM = '#2C3F63'

// Ketiga planet mengorbit pada r=59.5, di sudut -90, 30, dan 150 derajat.
const PLANETS = [
  { x: 128, y: 68.5 },
  { x: 179.53, y: 157.75 },
  { x: 76.47, y: 157.75 },
]

// Rangka carrier: segitiga yang menghubungkan ketiga poros planet. Bagian dekat
// planet tertutup roda giginya sendiri, jadi yang tampak hanya tengah tiap sisi.
const CARRIER_PATH = `M ${PLANETS[0].x} ${PLANETS[0].y} L ${PLANETS[1].x} ${PLANETS[1].y} L ${PLANETS[2].x} ${PLANETS[2].y} Z`

function PlanetGear() {
  return (
    <g>
      <circle r="34.6" fill="none" stroke={CREAM} strokeWidth="5.8" strokeDasharray="4.659 5.694" />
      <circle r="31.7" fill={CREAM} />
      <circle r="11" fill={NAVY} />
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

      {/* Ring gear internal - sengaja DIAM, jadi tidak diberi kelas animasi.
          Dibentuk dari cakram krem yang dilubangi, lalu celah antar gigi
          dikerok dengan blok navy sehingga giginya menghadap ke pusat. */}
      <g className="pgear__ring">
        <circle cx="128" cy="128" r="122" fill={CREAM} />
        <circle cx="128" cy="128" r="96" fill={NAVY} />
        <circle
          cx="128"
          cy="128"
          r="102"
          fill="none"
          stroke={NAVY}
          strokeWidth="12"
          strokeDasharray="6.779 5.546"
        />
      </g>

      {/* Carrier: membawa ketiga planet mengorbit pusat. */}
      <g className="pgear__carrier">
        <path d={CARRIER_PATH} fill="none" stroke={ARM} strokeWidth="16" strokeLinejoin="round" />
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
          r="23.5"
          fill="none"
          stroke={GOLD}
          strokeWidth="9"
          strokeDasharray="4.430 7.875"
        />
        <circle cx="128" cy="128" r="19" fill={GOLD} />
        <circle cx="128" cy="128" r="8" fill={NAVY} />
      </g>
    </svg>
  )
}
