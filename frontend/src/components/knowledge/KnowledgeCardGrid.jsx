import React from 'react';
import { LoadingSpinner, EmptyState } from '../common';

export default function KnowledgeCardGrid({
  articles = [],
  loading,
  selectedArticle,
  onSelectArticle
}) {
  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs font-bold text-muted uppercase tracking-wider">
          Dokumen &amp; Standar CBM ({articles.length})
        </h3>
        <span className="text-[10px] text-cyan">SOP &amp; Engineering Rules</span>
      </div>

      <div className="overflow-y-auto max-h-[500px] space-y-2 pr-1">
        {loading ? (
          <LoadingSpinner message="Memuat materi pengetahuan CBM..." />
        ) : articles.length === 0 ? (
          <EmptyState title="Tidak ada materi ditemukan" description="Coba ubah kata kunci pencarian materi." />
        ) : (
          articles.map((item, idx) => {
            const isSelected = selectedArticle?.filename === item.filename || selectedArticle?.title === item.title;
            return (
              <div
                key={idx}
                onClick={() => onSelectArticle(item)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'border-cyan bg-cyan/10 shadow-[0_0_12px_rgba(45,212,191,0.15)]'
                    : 'border-line/70 bg-panel hover:border-cyan/50 hover:bg-panel2'
                }`}
              >
                <div className="flex justify-between items-start">
                  <strong className="text-xs text-textMain font-semibold block">{item.title || item.filename}</strong>
                  <span className="text-[9px] px-2 py-0.5 rounded bg-panel2 border border-line text-cyan font-mono">
                    {item.domain || item.category || 'Standard'}
                  </span>
                </div>
                <p className="text-[11px] text-muted line-clamp-2 mt-1.5 leading-relaxed">
                  {item.summary || item.snippet || item.content?.slice(0, 120) || 'Dokumen panduan engineering dan standar pemeliharaan prediktif.'}
                </p>
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-line/40 text-[10px] text-muted">
                  <span>📄 {item.filename}</span>
                  {item.score !== undefined && (
                    <span className="text-cyan font-bold">Relevansi: {Math.round(item.score * 100)}%</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
