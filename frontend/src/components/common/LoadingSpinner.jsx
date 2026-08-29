import React from 'react';

export default function LoadingSpinner({ message = 'Memuat data...', size = 'md' }) {
  const sizeClass = size === 'sm' ? 'w-4 h-4 border-2' : size === 'lg' ? 'w-8 h-8 border-3' : 'w-6 h-6 border-2';
  return (
    <div className="flex flex-col items-center justify-center p-8 gap-3 text-muted">
      <div className={`${sizeClass} border-cyan/30 border-t-cyan rounded-full animate-spin`}></div>
      {message && <span className="text-xs">{message}</span>}
    </div>
  );
}
