import React from 'react';

export default function EmptyState({ icon = '🔍', title = 'Tidak ada data ditemukan', description = 'Coba ubah kata kunci pencarian atau filter unit/status.' }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center text-muted">
      <span className="text-2xl mb-2">{icon}</span>
      <h4 className="text-xs font-bold text-textMain">{title}</h4>
      <p className="text-[11px] text-muted max-w-xs mt-1">{description}</p>
    </div>
  );
}
