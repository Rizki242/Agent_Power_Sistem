import React from 'react'
import { CircleAlert, Inbox, RotateCcw } from 'lucide-react'

/**
 * Satu tampilan seragam untuk status memuat / gagal / kosong.
 *
 * Sebelumnya tiap workspace menulis markup dan kalimatnya sendiri, sehingga
 * pesan kesalahan berbeda-beda dan konten "melompat" saat data tiba. Skeleton
 * di sini menahan ruang dengan bentuk yang menyerupai isi sebenarnya.
 */

function SkeletonRows({ rows = 6 }) {
  return (
    <div className="skeleton-table" aria-hidden="true">
      <div className="skeleton skeleton--head" />
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton skeleton--row" />
      ))}
    </div>
  )
}

function SkeletonCards({ cards = 4 }) {
  return (
    <div className="skeleton-cards" aria-hidden="true">
      {Array.from({ length: cards }).map((_, index) => (
        <div key={index} className="skeleton skeleton--card" />
      ))}
    </div>
  )
}

function SkeletonChart() {
  return <div className="skeleton skeleton--chart" aria-hidden="true" />
}

const SKELETONS = {
  table: SkeletonRows,
  cards: SkeletonCards,
  chart: SkeletonChart,
}

export default function AsyncState({
  status,
  error,
  onRetry,
  isEmpty = false,
  emptyTitle = 'Belum ada data',
  emptyHint = 'Data akan muncul setelah tersedia di sistem.',
  emptyIcon: EmptyIcon = Inbox,
  skeleton = 'table',
  loadingLabel = 'Memuat data...',
  children,
}) {
  if (status === 'loading') {
    const Skeleton = SKELETONS[skeleton] || SkeletonRows
    return (
      <div className="async-state async-state--loading" role="status" aria-live="polite">
        <span className="sr-only">{loadingLabel}</span>
        <Skeleton />
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="notice notice--error async-state__error" role="alert">
        <CircleAlert size={18} />
        <div>
          <strong>Data tidak dapat dimuat.</strong>
          <span>{error || 'Pastikan backend FastAPI berjalan di port 8000, lalu coba lagi.'}</span>
        </div>
        {onRetry ? (
          <button type="button" className="button button--secondary async-state__retry" onClick={onRetry}>
            <RotateCcw size={14} /> Coba lagi
          </button>
        ) : null}
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div className="empty-state">
        <EmptyIcon size={30} />
        <strong>{emptyTitle}</strong>
        <span>{emptyHint}</span>
      </div>
    )
  }

  return children
}
