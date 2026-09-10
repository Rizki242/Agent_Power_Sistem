import React from 'react';

/**
 * Reusable ErrorState component for displaying failed API requests with correlation IDs.
 */
export default function ErrorState({
  title = 'Terjadi Kesalahan',
  message = 'Gagal memuat data dari server.',
  correlationId = null,
  onRetry = null,
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center text-muted border border-red/20 bg-red/5 rounded-2xl">
      <span className="text-2xl mb-2" aria-hidden="true">⚠️</span>
      <h4 className="text-xs font-bold text-red">{title}</h4>
      <p className="text-[11px] text-muted max-w-sm mt-1">{message}</p>
      {correlationId && (
        <div className="mt-2 text-[10px] font-mono text-muted/80 bg-panel px-2.5 py-1 rounded-md border border-line">
          Request ID: {correlationId}
        </div>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 px-3 py-1.5 text-xs font-semibold bg-panel hover:bg-panel-2 border border-line rounded-lg text-textMain transition-colors"
        >
          Coba Lagi
        </button>
      )}
    </div>
  );
}
