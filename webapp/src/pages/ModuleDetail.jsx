import { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import ModelViewer from '../components/ModelViewer';
import modules from '../data/modules.json';
import parts from '../data/parts.json';
import connectors from '../data/connectors.json';
import assemblyPositions from '../data/assembly_positions.json';

const REPAIR_LEVEL_COLORS = {
  1: 'text-green-400',
  2: 'text-amber-400',
  3: 'text-red-400',
};

const REPAIR_LEVEL_LABELS = {
  1: 'User',
  2: 'Technician',
  3: 'Factory',
};

export default function ModuleDetail() {
  const { id } = useParams();
  const mod = modules[id];

  // Build the list of parts belonging to this module
  const moduleParts = useMemo(() => {
    if (!mod) return [];
    return Object.values(parts).filter((p) => p.module === id);
  }, [mod, id]);

  // Build 3D models for parts in this module using assembly positions
  const models = useMemo(() => {
    if (!mod) return [];
    return mod.partsIncluded
      .filter((partName) => assemblyPositions[partName])
      .map((partName) => {
        const posData = assemblyPositions[partName];
        // Find the part data to get its material color
        const partData = moduleParts.find(
          (p) => p.stlFile === `${partName}.stl`
        );
        const color = partData
          ? partData.materialColor
          : posData.color || '#a0a0a8';

        return {
          url: `/models/${partName}.stl`,
          position: posData.position,
          rotation: posData.rotation || [0, 0, 0],
          color,
          name: partName,
          displayName: posData.name,
        };
      });
  }, [mod, moduleParts]);

  // Get connector details for this module
  const moduleConnectors = useMemo(() => {
    if (!mod) return [];
    return (mod.connectors || [])
      .map((connId) => connectors[connId])
      .filter(Boolean);
  }, [mod]);

  if (!mod) {
    return (
      <div className="px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-zinc-100 mb-4">
          Module Not Found
        </h1>
        <p className="text-zinc-400 mb-6">
          No module exists with ID "{id}".
        </p>
        <Link
          to="/modules"
          className="text-amber-500 hover:text-amber-400 font-mono transition-colors"
        >
          &larr; Back to Modules
        </Link>
      </div>
    );
  }

  return (
    <div className="px-4 py-8 space-y-10">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm font-mono text-zinc-500">
        <Link to="/modules" className="hover:text-amber-500 transition-colors">
          Modules
        </Link>
        <span>/</span>
        <span className="text-zinc-300">{mod.name}</span>
      </nav>

      {/* Module Header */}
      <header className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-zinc-800 border border-zinc-700 px-2 py-1 rounded text-zinc-400">
            {mod.moduleId}
          </span>
          <span className={`text-xs font-mono ${REPAIR_LEVEL_COLORS[mod.repairLevel]}`}>
            {mod.repairLevelName} Level
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-zinc-100">
          {mod.name}
        </h1>
        <p className="text-zinc-400 max-w-3xl leading-relaxed">
          {mod.description}
        </p>

        {/* Quick Stats */}
        <div className="flex flex-wrap gap-4 pt-2">
          <div className="bg-zinc-800/50 border border-zinc-700 rounded px-3 py-2 text-center">
            <div className="text-sm font-bold text-amber-500 font-mono">
              {mod.swapTimeDisplay}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase">Swap Time</div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded px-3 py-2 text-center">
            <div className="text-sm font-bold text-zinc-200 font-mono">
              {mod.interfaceType.replace('_', ' ')}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase">Interface</div>
          </div>
          <div className="bg-zinc-800/50 border border-zinc-700 rounded px-3 py-2 text-center">
            <div className="text-sm font-bold text-zinc-200 font-mono">
              {mod.partsIncluded.length}
            </div>
            <div className="text-[10px] text-zinc-500 uppercase">Parts</div>
          </div>
          {mod.toolsRequired.length > 0 && (
            <div className="bg-zinc-800/50 border border-zinc-700 rounded px-3 py-2">
              <div className="text-sm text-zinc-200 font-mono">
                {mod.toolsRequired.join(', ')}
              </div>
              <div className="text-[10px] text-zinc-500 uppercase">Tools Needed</div>
            </div>
          )}
        </div>
      </header>

      {/* 3D Model Viewer */}
      {models.length > 0 && (
        <section>
          <h2 className="text-xl font-bold text-zinc-100 mb-4">
            Module View
          </h2>
          <ModelViewer
            models={models}
            height="450px"
            className="w-full"
          />
        </section>
      )}

      {/* Parts Table */}
      <section>
        <h2 className="text-xl font-bold text-zinc-100 mb-4">
          Parts List
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-700 text-left">
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider">
                  Part #
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider">
                  Name
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider">
                  Material
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider text-center">
                  CNC/Printable
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider text-center">
                  Wear Item
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider text-right">
                  Replacement
                </th>
                <th className="py-3 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider text-right">
                  Cost
                </th>
                <th className="py-3 px-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {moduleParts.map((part) => (
                <tr
                  key={part.partNumber}
                  className="hover:bg-zinc-800/50 transition-colors"
                >
                  <td className="py-3 px-3 font-mono text-amber-500">
                    {part.partNumber}
                  </td>
                  <td className="py-3 px-3 text-zinc-200 font-medium">
                    {part.name}
                  </td>
                  <td className="py-3 px-3 text-zinc-400">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-3 h-3 rounded-full border border-zinc-600 flex-shrink-0"
                        style={{ backgroundColor: part.materialColor }}
                      />
                      {part.materialDisplay}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-center">
                    {part.isPrintable ? (
                      <span className="text-green-400 font-mono text-xs bg-green-400/10 px-2 py-0.5 rounded">
                        Printable
                      </span>
                    ) : (
                      <span className="text-zinc-500 font-mono text-xs bg-zinc-700/50 px-2 py-0.5 rounded">
                        CNC
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-center">
                    {part.isWearItem ? (
                      <span className="text-amber-400 font-mono text-xs">Yes</span>
                    ) : (
                      <span className="text-zinc-600 font-mono text-xs">No</span>
                    )}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-zinc-400">
                    {part.replacementInterval
                      ? `${part.replacementInterval.toLocaleString()} rolls`
                      : '\u2014'}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-zinc-200">
                    ${part.estimatedCost.toFixed(2)}
                  </td>
                  <td className="py-3 px-3 text-right">
                    <Link
                      to={`/store?sku=${part.partNumber}`}
                      className="text-xs text-amber-500 hover:text-amber-400 font-mono transition-colors whitespace-nowrap"
                    >
                      Order &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Connectors */}
      {moduleConnectors.length > 0 && (
        <section>
          <h2 className="text-xl font-bold text-zinc-100 mb-4">
            Connectors
          </h2>
          <div className="space-y-6">
            {moduleConnectors.map((conn) => (
              <div
                key={conn.id}
                className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-5"
              >
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="text-lg font-semibold text-zinc-100 font-mono">
                    {conn.id}
                  </h3>
                  <span className="text-xs text-zinc-400 bg-zinc-900 px-2 py-1 rounded font-mono">
                    {conn.family} {conn.pinCount}-pin
                  </span>
                  <span className="text-xs text-zinc-500">
                    {conn.from} &rarr; {conn.to}
                  </span>
                  <span className="text-xs text-zinc-500 font-mono ml-auto">
                    Max {conn.maxCurrentMa} mA
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-700 text-left">
                        <th className="py-2 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider w-16">
                          Pin
                        </th>
                        <th className="py-2 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider">
                          Signal
                        </th>
                        <th className="py-2 px-3 text-zinc-400 font-mono font-medium text-xs uppercase tracking-wider">
                          Wire Color
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800">
                      {conn.signals.map((signal, idx) => (
                        <tr key={idx} className="hover:bg-zinc-800/50 transition-colors">
                          <td className="py-2 px-3 font-mono text-amber-500 text-center">
                            {idx + 1}
                          </td>
                          <td className="py-2 px-3 font-mono text-zinc-200">
                            {signal}
                          </td>
                          <td className="py-2 px-3">
                            <div className="flex items-center gap-2">
                              <WireColorDot color={conn.wireColors[idx]} />
                              <span className="text-zinc-400 capitalize">
                                {conn.wireColors[idx]}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Repair Procedures */}
      <section>
        <h2 className="text-xl font-bold text-zinc-100 mb-4">
          Repair Procedures
        </h2>
        <div className="space-y-6">
          {moduleParts.map((part) => (
            <div
              key={part.partNumber}
              className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-5"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-zinc-100">
                    {part.name}
                  </h3>
                  <span className="text-xs font-mono text-zinc-500">
                    {part.partNumber}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-mono ${REPAIR_LEVEL_COLORS[part.repairLevel]}`}
                  >
                    {REPAIR_LEVEL_LABELS[part.repairLevel]}
                  </span>
                  <Link
                    to={`/store?sku=${part.partNumber}`}
                    className="text-xs bg-amber-600 hover:bg-amber-500 text-zinc-900 font-mono font-semibold px-3 py-1 rounded transition-colors"
                  >
                    Order this part
                  </Link>
                </div>
              </div>

              {/* Symptoms */}
              {part.symptoms && (
                <div className="mb-3">
                  <span className="text-xs text-zinc-500 uppercase tracking-wider">
                    Symptoms:
                  </span>
                  <span className="text-sm text-zinc-400 ml-2">
                    {part.symptoms}
                  </span>
                </div>
              )}

              {/* Procedure Steps */}
              <div className="space-y-2">
                {part.procedure.split('\n').map((step, idx) => {
                  const trimmed = step.trim();
                  if (!trimmed) return null;
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-3 text-sm text-zinc-300"
                    >
                      <span className="text-amber-500/70 font-mono text-xs mt-0.5 flex-shrink-0 w-5 text-right">
                        {idx + 1}.
                      </span>
                      <span>{trimmed.replace(/^\d+\.\s*/, '')}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Back Link */}
      <div className="pt-4 border-t border-zinc-800">
        <Link
          to="/modules"
          className="text-amber-500 hover:text-amber-400 font-mono text-sm transition-colors"
        >
          &larr; Back to all modules
        </Link>
      </div>
    </div>
  );
}

/* Small helper component for wire color dots */
function WireColorDot({ color }) {
  const CSS_COLORS = {
    red: '#ef4444',
    black: '#1c1c1c',
    orange: '#f97316',
    yellow: '#eab308',
    brown: '#92400e',
    blue: '#3b82f6',
    violet: '#8b5cf6',
    grey: '#9ca3af',
    white: '#f5f5f5',
    green: '#22c55e',
  };

  return (
    <span
      className="inline-block w-3 h-3 rounded-full border border-zinc-600 flex-shrink-0"
      style={{ backgroundColor: CSS_COLORS[color] || color }}
    />
  );
}
