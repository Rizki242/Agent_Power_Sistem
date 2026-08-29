import React from 'react';

export default function FilterBar({
  search,
  onSearchChange,
  onSearchSubmit,
  searchPlaceholder = 'Cari equipment atau tag...',
  unitFilter,
  onUnitChange,
  unitOptions = ['ALL', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'COMMON', 'BOP'],
  statusFilter,
  onStatusChange,
  statusOptions = ['ALL', 'Normal', 'Alarm', 'High', 'Standby'],
  extraFilters = null,
  actions = null,
  accentColor = 'cyan'
}) {
  const focusBorderClass = accentColor === 'amber'
    ? 'focus:border-amber'
    : accentColor === 'green'
    ? 'focus:border-green'
    : accentColor === 'orange'
    ? 'focus:border-orange-400'
    : 'focus:border-cyan';

  return (
    <div className="border border-line rounded-2xl bg-card-gradient shadow-neon p-3.5 flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
      {/* Search Input Form */}
      <form onSubmit={(e) => { e.preventDefault(); onSearchSubmit && onSearchSubmit(e); }} className="flex-1">
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className={`w-full bg-panel2 border border-line rounded-lg pl-3 pr-8 py-1.5 text-xs text-textMain outline-none transition-colors ${focusBorderClass}`}
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-textMain text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </form>

      {/* Dropdown Filters & Actions */}
      <div className="flex items-center gap-2 flex-wrap justify-end">
        {unitFilter !== undefined && onUnitChange && (
          <select
            value={unitFilter}
            onChange={(e) => onUnitChange(e.target.value)}
            className={`bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-xs text-textMain outline-none ${focusBorderClass}`}
          >
            {unitOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt === 'ALL' ? 'Semua Unit' : opt}
              </option>
            ))}
          </select>
        )}

        {statusFilter !== undefined && onStatusChange && (
          <select
            value={statusFilter}
            onChange={(e) => onStatusChange(e.target.value)}
            className={`bg-panel2 border border-line rounded-lg px-2.5 py-1.5 text-xs text-textMain outline-none ${focusBorderClass}`}
          >
            {statusOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt === 'ALL' ? 'Semua Status' : opt}
              </option>
            ))}
          </select>
        )}

        {extraFilters}
        {actions}
      </div>
    </div>
  );
}
