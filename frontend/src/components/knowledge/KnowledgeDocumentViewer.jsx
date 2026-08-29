import React from 'react';

export default function KnowledgeDocumentViewer({ selectedArticle }) {
  if (!selectedArticle) {
    return (
      <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-8 text-center text-muted text-xs">
        Pilih salah satu dokumen materi dari daftar di samping untuk membaca panduan teknis dan standar.
      </div>
    );
  }

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-5 flex flex-col gap-4">
      {/* Header Info */}
      <div className="flex justify-between items-start pb-3 border-b border-line">
        <div>
          <span className="text-[10px] uppercase font-bold text-cyan tracking-wider">
            {selectedArticle.domain || selectedArticle.category || 'CBM Standard'}
          </span>
          <h3 className="text-base font-bold text-textMain mt-0.5">
            {selectedArticle.title || selectedArticle.filename}
          </h3>
        </div>
        <span className="text-[10px] font-mono text-muted bg-panel px-2.5 py-1 rounded border border-line">
          {selectedArticle.filename}
        </span>
      </div>

      {/* Content Viewer */}
      <div className="p-4 bg-panel rounded-xl border border-line text-xs text-textMain leading-relaxed whitespace-pre-line max-h-[420px] overflow-y-auto font-sans">
        {selectedArticle.content || selectedArticle.text || 'Isi dokumen tidak tersedia.'}
      </div>

      {/* Citation / References Footer */}
      <div className="p-3 bg-panel2 rounded-xl border border-line flex items-center justify-between text-[11px] text-muted">
        <span>📖 Terintegrasi dengan Antigravity RAG Knowledge Base</span>
        <span className="text-cyan font-mono">PLTU Jeranjang O&amp;M</span>
      </div>
    </div>
  );
}
