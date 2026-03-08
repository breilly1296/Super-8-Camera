import { Link } from 'react-router-dom';
import modules from '../data/modules.json';

const MODULE_ICONS = {
  'MOD-100': '🎞',
  'MOD-200': '⚙',
  'MOD-300': '🔧',
  'MOD-400': '📦',
  'MOD-500': '💻',
  'MOD-600': '🔋',
  'MOD-700': '👁',
};

const INTERFACE_LABELS = {
  THUMBSCREW: 'Thumbscrew',
  SNAP_FIT: 'Snap-Fit',
  JST: 'JST Connector',
  DOVETAIL: 'Dovetail',
};

export default function Modules() {
  const moduleList = Object.values(modules);

  return (
    <div className="px-4 py-8 space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Modules</h1>
        <p className="text-zinc-400 mt-2 max-w-2xl">
          The Super 8 Camera is built from 7 hot-swappable modules. Each module
          can be removed, repaired, or upgraded independently.
        </p>
      </div>

      {/* Module Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {moduleList.map((mod) => (
          <Link
            key={mod.moduleId}
            to={`/modules/${mod.moduleId}`}
            className="group bg-zinc-800/50 border border-zinc-700 rounded-lg p-6 hover:border-amber-500/50 hover:bg-zinc-800 transition-all flex flex-col"
          >
            {/* Icon and ID */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-4xl" role="img" aria-label={mod.name}>
                {MODULE_ICONS[mod.moduleId]}
              </span>
              <span className="text-xs font-mono text-zinc-600 bg-zinc-900 px-2 py-1 rounded">
                {mod.moduleId}
              </span>
            </div>

            {/* Name */}
            <h2 className="text-xl font-semibold text-zinc-100 group-hover:text-amber-500 transition-colors mb-2">
              {mod.name}
            </h2>

            {/* Description */}
            <p className="text-sm text-zinc-500 line-clamp-3 flex-1 mb-4">
              {mod.description}
            </p>

            {/* Stats Row */}
            <div className="grid grid-cols-3 gap-2 pt-4 border-t border-zinc-700/50">
              {/* Swap Time */}
              <div className="text-center">
                <div className="text-sm font-bold text-amber-500 font-mono">
                  {mod.swapTimeDisplay}
                </div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">
                  Swap
                </div>
              </div>

              {/* Repair Level */}
              <div className="text-center">
                <div className="text-sm font-bold text-zinc-200">
                  {mod.repairLevelName}
                </div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">
                  Level
                </div>
              </div>

              {/* Interface */}
              <div className="text-center">
                <div className="text-sm font-bold text-zinc-200 truncate">
                  {INTERFACE_LABELS[mod.interfaceType] || mod.interfaceType}
                </div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">
                  Interface
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
