import { useRef, useState } from 'react'
import { Camera } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from './Toast.jsx'

const AVATAR_MAX_SOURCE_BYTES = 8 * 1024 * 1024 // batas file asli yang dipilih pengguna
const AVATAR_TARGET_SIZE = 256 // sisi persegi hasil kompresi, cukup tajam untuk avatar kecil

// Mengubah file foto yang dipilih pengguna menjadi data URL JPEG persegi kecil,
// supaya tersimpan ringkas langsung di data pengguna tanpa perlu penyimpanan file terpisah.
function resizeImageToDataUrl(file, size = AVATAR_TARGET_SIZE) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const side = Math.min(img.naturalWidth, img.naturalHeight)
      const sx = (img.naturalWidth - side) / 2
      const sy = (img.naturalHeight - side) / 2
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size)
      resolve(canvas.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('Gagal membaca gambar. Pastikan file berupa foto yang valid.'))
    }
    img.src = objectUrl
  })
}

// Avatar bulat kecil untuk pill/ikon ringkas (mis. baris pengguna di sidebar) - hanya tampilan.
export function AvatarThumb({ avatar, initial, imgClassName = '' }) {
  return avatar ? <img src={avatar} alt="" className={imgClassName} /> : initial
}

// Avatar besar yang bisa diklik di header popover profil, dipakai untuk mengganti foto profil.
// Dibagikan antara menu profil sidebar utama (App.jsx) dan sidebar riwayat chat (ChatHistoryPanel.jsx)
// supaya logika resize/kompres & validasi upload tidak digandakan di dua tempat.
export function ProfileAvatarEditor({ avatar, initial, displayName }) {
  const { updateAvatar } = useAuth()
  const { notify } = useToast()
  const [isUploading, setIsUploading] = useState(false)
  const inputRef = useRef(null)

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = '' // agar memilih file yang sama lagi tetap memicu onChange
    if (!file) return
    if (!file.type.startsWith('image/')) {
      notify({ tone: 'error', message: 'Pilih file gambar (PNG, JPEG, atau WEBP).' })
      return
    }
    if (file.size > AVATAR_MAX_SOURCE_BYTES) {
      notify({ tone: 'error', message: 'Ukuran file terlalu besar. Maksimal 8 MB.' })
      return
    }
    setIsUploading(true)
    try {
      const dataUrl = await resizeImageToDataUrl(file)
      await updateAvatar(dataUrl)
      notify({ tone: 'success', message: 'Foto profil berhasil diperbarui.' })
    } catch (err) {
      notify({ tone: 'error', message: `Gagal memperbarui foto profil: ${err.message}` })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className="profile-popover-avatar"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        title="Ganti foto profil"
        aria-label="Ganti foto profil"
      >
        {avatar ? (
          <img src={avatar} alt={displayName} className="profile-popover-avatar-img" />
        ) : (
          <span className="profile-popover-avatar-fallback">{initial}</span>
        )}
        <span className="profile-popover-avatar-edit">
          <Camera size={13} />
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
    </>
  )
}
