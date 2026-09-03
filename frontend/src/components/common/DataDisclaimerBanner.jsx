import React from 'react';

// React counterpart of src/components/theme.py's render_data_disclaimer_banner.
// Domains whose data is illustrative rather than sourced from real
// measurements (Partial Discharge today - see src/pd_data.py's module
// docstring) must show this, so the web UI never presents example figures as
// if they came from the plant.
export default function DataDisclaimerBanner({
  message = 'Data Contoh - Belum Terverifikasi dari Sumber Asli',
}) {
  return (
    <div
      role="note"
      className="flex items-start gap-2.5 rounded-xl border border-amber/40 bg-amber/10 px-3.5 py-2.5"
    >
      <span aria-hidden="true" className="text-sm leading-none mt-0.5">⚠️</span>
      <p className="text-[11px] leading-relaxed text-amber font-semibold m-0">{message}</p>
    </div>
  );
}
