import React from 'react';

export default function TabNavigation({
  tabs,
  activeTab,
  onTabChange,
  accentColor = 'cyan',
  className = ''
}) {
  const activeColorClasses = {
    cyan: 'border-cyan text-cyan bg-cyan/10 font-bold',
    amber: 'border-amber text-amber bg-amber/10 font-bold',
    green: 'border-green text-green bg-green/10 font-bold',
    blue: 'border-blue text-blue bg-blue/10 font-bold',
    orange: 'border-orange-400 text-orange-400 bg-orange-500/10 font-bold'
  };

  const selectedClass = activeColorClasses[accentColor] || activeColorClasses.cyan;

  return (
    <div className={`flex gap-1.5 p-1 bg-panel2 rounded-xl border border-line overflow-x-auto ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs transition-all whitespace-nowrap flex items-center gap-1.5 ${
              isActive
                ? `border ${selectedClass}`
                : 'text-muted hover:text-textMain hover:bg-panel border border-transparent'
            }`}
          >
            {tab.icon && <span>{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${isActive ? 'bg-panel text-textMain' : 'bg-panel text-muted'}`}>
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
