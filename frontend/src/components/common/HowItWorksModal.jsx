import React from 'react';

export default function HowItWorksModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-panel2 border border-cyan/40 rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 shadow-[0_0_50px_rgba(50,213,255,0.25)] flex flex-col gap-6 animate-fade-in relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-8 h-8 rounded-xl bg-panel border border-line text-muted hover:text-textMain hover:border-cyan transition-colors flex items-center justify-center text-sm font-bold"
        >
          ✕
        </button>

        {/* Header */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-cyan font-black">Panduan Pengoperasian</div>
          <h2 className="text-xl md:text-2xl font-bold text-textMain mt-1">
            Cara Kerja AI O&amp;M Reliability Command Center
          </h2>
          <p className="text-xs md:text-sm text-muted mt-1 leading-relaxed">
            Sistem ini menggabungkan kecerdasan buatan berbasis aturan standar industri (ISO, IEEE, ASTM) dan 8 AI Specialist Sub-Agents untuk memprediksi kerusakan peralatan pembangkit PLTU Jeranjang sebelum terjadi kegagalan (*Preventive to Predictive Maintenance*).
          </p>
        </div>

        {/* 4-Step Visual Workflow */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Step 1 */}
          <div className="p-4 rounded-2xl bg-panel border border-line relative overflow-hidden flex flex-col justify-between group hover:border-cyan transition-all shadow-neon">
            <div className="absolute top-0 right-0 w-12 h-12 bg-cyan/10 rounded-bl-3xl flex items-center justify-center text-xs font-black text-cyan">
              01
            </div>
            <div>
              <span className="text-2xl block mb-2">📋</span>
              <strong className="text-xs font-bold text-textMain block">Input &amp; Monitoring Data</strong>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                Data pengukuran berkala (MCSA arus 3-fasa, getaran 18 titik sensor, uji lab oli, gas DGA trafo, &amp; foto termal) dibaca dari database dan logbook.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-cyan font-mono">
              MCSA • Vib • Oli • DGA • IRT
            </div>
          </div>

          {/* Step 2 */}
          <div className="p-4 rounded-2xl bg-panel border border-line relative overflow-hidden flex flex-col justify-between group hover:border-cyan transition-all shadow-neon">
            <div className="absolute top-0 right-0 w-12 h-12 bg-purple/10 rounded-bl-3xl flex items-center justify-center text-xs font-black text-purple">
              02
            </div>
            <div>
              <span className="text-2xl block mb-2">🤖</span>
              <strong className="text-xs font-bold text-textMain block">Evaluasi 8 Sub-Agent AI</strong>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                8 Specialist Sub-Agents menganalisis data domain masing-masing secara independen berdasarkan batas baku mutu internasional.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-purple font-mono">
              ISO 10816 • IEEE 519 • C57.104
            </div>
          </div>

          {/* Step 3 */}
          <div className="p-4 rounded-2xl bg-panel border border-line relative overflow-hidden flex flex-col justify-between group hover:border-cyan transition-all shadow-neon">
            <div className="absolute top-0 right-0 w-12 h-12 bg-green/10 rounded-bl-3xl flex items-center justify-center text-xs font-black text-green">
              03
            </div>
            <div>
              <span className="text-2xl block mb-2">🔗</span>
              <strong className="text-xs font-bold text-textMain block">Multi-Modal Fusion &amp; RUL</strong>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                Reliability Fusion Engine mengkorelasikan seluruh temuan menjadi <strong>Health Index (0–100)</strong>, estimasi sisa umur operasi (RUL), dan analisis akar penyebab (RCA).
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-green font-mono">
              Health Index • RUL • 5x5 Risk
            </div>
          </div>

          {/* Step 4 */}
          <div className="p-4 rounded-2xl bg-panel border border-line relative overflow-hidden flex flex-col justify-between group hover:border-cyan transition-all shadow-neon">
            <div className="absolute top-0 right-0 w-12 h-12 bg-amber/10 rounded-bl-3xl flex items-center justify-center text-xs font-black text-amber">
              04
            </div>
            <div>
              <span className="text-2xl block mb-2">🛠️</span>
              <strong className="text-xs font-bold text-textMain block">Tindak Lanjut &amp; Work Order</strong>
              <p className="text-[11px] text-muted mt-1 leading-relaxed">
                Sistem menghasilkan rekomendasi tindakan korektif dan menerbitkan draft Work Order otomatis untuk Maximo / SAP CMMS.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-line/40 text-[10px] text-amber font-mono">
              Auto Maximo / SAP WO
            </div>
          </div>
        </div>

        {/* Interpretation Guide for Critical Values */}
        <div className="p-5 rounded-2xl bg-panel border border-line">
          <h3 className="text-xs font-bold text-textMain mb-3 uppercase tracking-wider flex items-center gap-2">
            <span>📊</span> Arti Skor &amp; Ambang Batas Parameter Pengujian
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="p-3 bg-panel2 rounded-xl border border-green/30">
              <span className="text-green font-bold block">🟢 Normal / Zone A (85–100)</span>
              <p className="text-[11px] text-muted mt-1">
                Peralatan prima. Getaran &lt; 2.8 mm/s, Sideband &lt; -54 dB, Oli bersih. Lanjutkan pemeliharaan rutin.
              </p>
            </div>
            <div className="p-3 bg-panel2 rounded-xl border border-blue/30">
              <span className="text-blue font-bold block">🔵 Watch / Zone B (70–84)</span>
              <p className="text-[11px] text-muted mt-1">
                Kondisi dapat diterima untuk operasi kontinu. Getaran 2.8–4.5 mm/s. Monitor tren getaran berkala.
              </p>
            </div>
            <div className="p-3 bg-panel2 rounded-xl border border-amber/30">
              <span className="text-amber font-bold block">🟡 Alarm / Warning (50–69)</span>
              <p className="text-[11px] text-muted mt-1">
                Perlu perhatian. Sideband -54 s/d -45 dB (Rotor Bar Level 2), Getaran 4.5–7.1 mm/s. Jadwalkan inspeksi.
              </p>
            </div>
            <div className="p-3 bg-panel2 rounded-xl border border-red/30">
              <span className="text-red font-bold block">🔴 Critical / Zone D (&lt; 50)</span>
              <p className="text-[11px] text-muted mt-1">
                Bahaya kerusakan fatal. Getaran &gt; 7.1 mm/s, Sideband &ge; -45 dB (Level 3-4). Mitigasi &amp; perbaikan segera!
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Shortcut Guide */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 bg-panel rounded-xl border border-line flex flex-col justify-between">
            <div>
              <strong className="text-xs text-cyan block font-bold">⚡ MCSA Workspace</strong>
              <p className="text-[11px] text-muted mt-1">
                Lihat arus 3-fasa, unbalance tegangan, spektrum rotor bar, daya aktif kW, dan spesifikasi nameplate motor.
              </p>
            </div>
          </div>
          <div className="p-3.5 bg-panel rounded-xl border border-line flex flex-col justify-between">
            <div>
              <strong className="text-xs text-blue block font-bold">🌀 Vibration Workspace</strong>
              <p className="text-[11px] text-muted mt-1">
                Lihat 18 titik sensor getaran (1V, 1H, 1A, dll.), RMS Max, ISO 10816 evaluasi, serta spesifikasi pompa &amp; fan.
              </p>
            </div>
          </div>
          <div className="p-3.5 bg-panel rounded-xl border border-line flex flex-col justify-between">
            <div>
              <strong className="text-xs text-purple block font-bold">🤖 Multi-Agent Fusion</strong>
              <p className="text-[11px] text-muted mt-1">
                Jalankan diagnosa kolaboratif 8 agen spesialis untuk menemukan akar masalah gabungan dan menerbitkan Work Order.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-line">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-cyan text-[#071018] font-bold text-xs hover:bg-cyan/90 transition-colors shadow-neon"
          >
            Mengerti, Masuk ke Dashboard →
          </button>
        </div>
      </div>
    </div>
  );
}
