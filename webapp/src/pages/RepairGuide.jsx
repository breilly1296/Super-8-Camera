import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import ModelViewer from '../components/ModelViewer';
import repairs from '../data/repairs.json';
import assemblyPositions from '../data/assembly_positions.json';
import modules from '../data/modules.json';

const DIFFICULTY_STYLES = {
  Easy: 'bg-green-500/10 text-green-400 border-green-500/30',
  Moderate: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  Advanced: 'bg-red-500/10 text-red-400 border-red-500/30',
};

const DIFFICULTY_DOT = {
  Easy: 'bg-green-400',
  Moderate: 'bg-amber-400',
  Advanced: 'bg-red-400',
};

function DifficultyBadge({ label }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${DIFFICULTY_STYLES[label] || DIFFICULTY_STYLES.Moderate}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${DIFFICULTY_DOT[label] || DIFFICULTY_DOT.Moderate}`}
      />
      {label}
    </span>
  );
}

function RepairCard({ repair, onClick }) {
  const mod = modules[repair.affectedModule];
  const moduleName = mod ? mod.name : repair.affectedModule;

  return (
    <button
      onClick={() => onClick(repair)}
      className="w-full text-left bg-zinc-800/50 border border-zinc-700 rounded-lg p-5 hover:border-amber-500/50 hover:bg-zinc-800 transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-lg font-semibold text-zinc-100 group-hover:text-amber-500 transition-colors">
          {repair.symptom}
        </h3>
        <DifficultyBadge label={repair.difficultyLabel} />
      </div>

      <div className="flex items-center gap-3 mt-3 text-xs text-zinc-400 font-mono">
        <span>{moduleName}</span>
        <span className="text-zinc-600">|</span>
        <span>~{repair.estimatedMinutes} min</span>
      </div>

      <p className="text-sm text-zinc-500 mt-3 line-clamp-2">
        {repair.description}
      </p>
    </button>
  );
}

function RepairDetail({ repair, onBack }) {
  const mod = modules[repair.affectedModule];
  const moduleName = mod ? mod.name : repair.affectedModule;

  // Build models from the module's parts (if module exists), otherwise
  // show just the highlighted part as a single model
  const modelsForViewer = useMemo(() => {
    const partsToShow = mod ? mod.partsIncluded : [repair.highlightPart];
    return partsToShow
      .filter((partKey) => assemblyPositions[partKey])
      .map((partKey) => {
        const pos = assemblyPositions[partKey];
        return {
          url: `/models/${partKey}.stl`,
          position: pos.position,
          rotation: pos.rotation,
          color: pos.color,
          name: partKey,
          displayName: pos.name,
        };
      });
  }, [mod, repair.highlightPart]);

  const highlightParts = [repair.highlightPart];

  // Find SKU from the first affected part for the "Order Replacement" link
  const primarySku = repair.affectedParts?.[0] || '';

  return (
    <div className="space-y-8">
      {/* Back button and header */}
      <div>
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors mb-4"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to all repairs
        </button>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-100">
              {repair.symptom}
            </h2>
            <div className="flex items-center gap-3 mt-2 text-sm text-zinc-400 font-mono">
              <span>{moduleName} module</span>
              <span className="text-zinc-600">|</span>
              <span>~{repair.estimatedMinutes} min</span>
            </div>
          </div>
          <DifficultyBadge label={repair.difficultyLabel} />
        </div>

        <p className="text-zinc-400 mt-4 leading-relaxed">
          {repair.description}
        </p>
      </div>

      {/* 3D viewer showing affected module */}
      <div>
        <ModelViewer
          models={modelsForViewer}
          highlightParts={highlightParts}
          glowColor="#ef4444"
          height="400px"
          className="w-full"
        />
        <p className="text-xs text-red-400/70 font-mono mt-2">
          Highlighted in red:{' '}
          {assemblyPositions[repair.highlightPart]?.name ||
            repair.highlightPart}
        </p>
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Procedure - takes 2 cols */}
        <div className="lg:col-span-2">
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-4">
              Repair Procedure
            </h3>
            <ol className="space-y-3">
              {repair.steps.map((stepText, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-300">
                    {i + 1}
                  </span>
                  <span className="text-sm text-zinc-300 leading-relaxed pt-0.5">
                    {stepText}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Tools */}
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
              Tools Required
            </h3>
            <ul className="space-y-1.5">
              {repair.tools.map((tool) => (
                <li
                  key={tool}
                  className="flex items-center gap-2 text-sm text-zinc-300"
                >
                  <span className="w-1 h-1 rounded-full bg-zinc-500 flex-shrink-0" />
                  {tool}
                </li>
              ))}
            </ul>
          </div>

          {/* Parts needed */}
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
              Parts Needed
            </h3>
            <ul className="space-y-2">
              {repair.partsNeeded.map((part) => (
                <li
                  key={part}
                  className="text-sm text-zinc-300 bg-zinc-900/50 rounded-md px-3 py-2"
                >
                  {part}
                </li>
              ))}
            </ul>
          </div>

          {/* Order replacement button */}
          {primarySku && (
            <Link
              to={`/store?sku=${primarySku}`}
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-amber-600 hover:bg-amber-500 text-zinc-950 font-medium text-sm rounded-lg transition-colors"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z"
                />
              </svg>
              Order Replacement
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function RepairGuide() {
  const [selectedRepair, setSelectedRepair] = useState(null);

  if (selectedRepair) {
    return (
      <RepairDetail
        repair={selectedRepair}
        onBack={() => setSelectedRepair(null)}
      />
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl sm:text-4xl font-bold text-zinc-100 tracking-tight">
          Repair Guide
        </h1>
        <p className="text-zinc-400 mt-2 font-mono text-sm">
          {repairs.length} common issues &middot; Diagnose &amp; fix
        </p>
      </div>

      {/* Difficulty legend */}
      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span>Difficulty:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-400" />
          <span>Easy</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-400" />
          <span>Moderate</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          <span>Advanced</span>
        </div>
      </div>

      {/* Repair cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {repairs.map((repair) => (
          <RepairCard
            key={repair.id}
            repair={repair}
            onClick={setSelectedRepair}
          />
        ))}
      </div>
    </div>
  );
}
