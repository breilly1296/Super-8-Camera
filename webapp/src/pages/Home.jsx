import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import ModelViewer from '../components/ModelViewer';
import assemblyPositions from '../data/assembly_positions.json';
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

const stats = [
  { label: 'Total Parts', value: '27' },
  { label: 'Modules', value: '7' },
  { label: 'Weight', value: '~691g' },
  { label: 'Validation', value: '9/9' },
  { label: 'Kit Price', value: '$249' },
  { label: 'Assembled', value: '$599' },
];

export default function Home() {
  const allModels = useMemo(() => {
    return Object.entries(assemblyPositions).map(([key, data]) => ({
      url: `/models/${key}.stl`,
      position: data.position,
      rotation: data.rotation,
      color: data.color,
      name: key,
      displayName: data.name,
    }));
  }, []);

  const moduleList = Object.values(modules);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-16 px-4">
        <h1 className="text-5xl sm:text-6xl font-bold text-zinc-100 tracking-tight mb-4">
          Super 8 Camera
        </h1>
        <p className="text-lg sm:text-xl text-zinc-400 font-mono">
          Open Source &middot; Self-Repairable &middot; Framework for Film
        </p>
      </section>

      {/* Stats Grid */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 px-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 text-center"
          >
            <div className="text-2xl font-bold text-amber-500 font-mono">
              {stat.value}
            </div>
            <div className="text-xs text-zinc-400 mt-1 uppercase tracking-wider">
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      {/* 3D Model Viewer - Full Assembly */}
      <section className="px-4">
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">
          Full Assembly
        </h2>
        <ModelViewer
          models={allModels}
          height="600px"
          className="w-full"
        />
      </section>

      {/* Module Overview */}
      <section className="px-4">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-zinc-100">
            Modules
          </h2>
          <Link
            to="/modules"
            className="text-sm text-amber-500 hover:text-amber-400 font-mono transition-colors"
          >
            View all &rarr;
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {moduleList.map((mod) => (
            <Link
              key={mod.moduleId}
              to={`/modules/${mod.moduleId}`}
              className="group bg-zinc-800/50 border border-zinc-700 rounded-lg p-5 hover:border-amber-500/50 hover:bg-zinc-800 transition-all"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl" role="img" aria-label={mod.name}>
                  {MODULE_ICONS[mod.moduleId]}
                </span>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-zinc-100 group-hover:text-amber-500 transition-colors truncate">
                    {mod.name}
                  </h3>
                  <div className="flex items-center gap-3 mt-2 text-xs text-zinc-400 font-mono">
                    <span>{mod.swapTimeDisplay} swap</span>
                    <span className="text-zinc-600">|</span>
                    <span>{mod.repairLevelName}</span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-zinc-500 mt-3 line-clamp-2">
                {mod.description}
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
