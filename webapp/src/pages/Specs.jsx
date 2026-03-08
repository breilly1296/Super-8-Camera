import { useState } from 'react';
import specs from '../data/specs.json';

const SPEC_GROUPS = ['film', 'lens', 'body', 'shutter', 'drivetrain', 'power', 'tolerances', 'pcb'];

function SpecTable({ group }) {
  const data = specs[group];
  if (!data || !data.specs) return null;
  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
      <h3 className="text-lg font-semibold text-zinc-100 px-5 py-3 border-b border-zinc-700 bg-zinc-800/80">
        {data.title}
      </h3>
      <table className="w-full text-sm">
        <tbody>
          {data.specs.map((spec, i) => (
            <tr
              key={spec.label}
              className={i % 2 === 0 ? 'bg-zinc-900/40' : 'bg-zinc-900/20'}
            >
              <td className="px-5 py-2.5 text-zinc-400 font-medium w-1/3 whitespace-nowrap">
                {spec.label}
              </td>
              <td className="px-5 py-2.5 text-zinc-100 font-mono text-xs">
                {spec.value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CamTimingDiagram() {
  const { phases } = specs.camTiming;
  const cx = 160;
  const cy = 160;
  const outerR = 130;
  const innerR = 80;
  const [hoveredPhase, setHoveredPhase] = useState(null);

  function degToRad(deg) {
    return ((deg - 90) * Math.PI) / 180;
  }

  function arcPath(startDeg, endDeg, rOuter, rInner) {
    const startOuter = {
      x: cx + rOuter * Math.cos(degToRad(startDeg)),
      y: cy + rOuter * Math.sin(degToRad(startDeg)),
    };
    const endOuter = {
      x: cx + rOuter * Math.cos(degToRad(endDeg)),
      y: cy + rOuter * Math.sin(degToRad(endDeg)),
    };
    const startInner = {
      x: cx + rInner * Math.cos(degToRad(endDeg)),
      y: cy + rInner * Math.sin(degToRad(endDeg)),
    };
    const endInner = {
      x: cx + rInner * Math.cos(degToRad(startDeg)),
      y: cy + rInner * Math.sin(degToRad(startDeg)),
    };
    const span = endDeg - startDeg;
    const largeArc = span > 180 ? 1 : 0;

    return [
      `M ${startOuter.x} ${startOuter.y}`,
      `A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
      `L ${startInner.x} ${startInner.y}`,
      `A ${rInner} ${rInner} 0 ${largeArc} 0 ${endInner.x} ${endInner.y}`,
      'Z',
    ].join(' ');
  }

  function labelPosition(startDeg, endDeg) {
    const midDeg = (startDeg + endDeg) / 2;
    const labelR = (outerR + innerR) / 2;
    return {
      x: cx + labelR * Math.cos(degToRad(midDeg)),
      y: cy + labelR * Math.sin(degToRad(midDeg)),
    };
  }

  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-5">
      <h3 className="text-lg font-semibold text-zinc-100 mb-4">
        {specs.camTiming.title}
      </h3>
      <div className="flex flex-col lg:flex-row items-start gap-6">
        <div className="flex-shrink-0">
          <svg width="320" height="320" viewBox="0 0 320 320" className="mx-auto">
            {/* Degree tick marks */}
            {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
              const tickOuter = {
                x: cx + (outerR + 12) * Math.cos(degToRad(deg)),
                y: cy + (outerR + 12) * Math.sin(degToRad(deg)),
              };
              const tickInner = {
                x: cx + (outerR + 2) * Math.cos(degToRad(deg)),
                y: cy + (outerR + 2) * Math.sin(degToRad(deg)),
              };
              const labelPos = {
                x: cx + (outerR + 22) * Math.cos(degToRad(deg)),
                y: cy + (outerR + 22) * Math.sin(degToRad(deg)),
              };
              return (
                <g key={deg}>
                  <line
                    x1={tickInner.x}
                    y1={tickInner.y}
                    x2={tickOuter.x}
                    y2={tickOuter.y}
                    stroke="#52525b"
                    strokeWidth="1"
                  />
                  <text
                    x={labelPos.x}
                    y={labelPos.y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="text-[9px] fill-zinc-500 font-mono"
                  >
                    {deg}°
                  </text>
                </g>
              );
            })}

            {/* Phase arc segments */}
            {phases.map((phase, i) => {
              const isHovered = hoveredPhase === i;
              return (
                <path
                  key={phase.name}
                  d={arcPath(phase.startDeg, phase.endDeg, outerR, innerR)}
                  fill={phase.color}
                  fillOpacity={isHovered ? 1 : 0.7}
                  stroke="#18181b"
                  strokeWidth="1.5"
                  className="transition-all duration-200 cursor-pointer"
                  onMouseEnter={() => setHoveredPhase(i)}
                  onMouseLeave={() => setHoveredPhase(null)}
                />
              );
            })}

            {/* Center label */}
            <circle cx={cx} cy={cy} r={innerR - 6} fill="#18181b" />
            <text
              x={cx}
              y={cy - 8}
              textAnchor="middle"
              className="text-xs fill-zinc-400 font-mono"
            >
              360°
            </text>
            <text
              x={cx}
              y={cy + 8}
              textAnchor="middle"
              className="text-[10px] fill-zinc-500"
            >
              cycle
            </text>

            {/* Phase degree labels on arcs (only for large enough segments) */}
            {phases.map((phase) => {
              const span = phase.endDeg - phase.startDeg;
              if (span < 20) return null;
              const pos = labelPosition(phase.startDeg, phase.endDeg);
              return (
                <text
                  key={`label-${phase.name}`}
                  x={pos.x}
                  y={pos.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="text-[9px] fill-zinc-950 font-bold pointer-events-none"
                >
                  {phase.startDeg}°-{phase.endDeg}°
                </text>
              );
            })}
          </svg>
        </div>

        {/* Legend + hover detail */}
        <div className="flex-1 min-w-0">
          <div className="space-y-2">
            {phases.map((phase, i) => {
              const span = phase.endDeg - phase.startDeg;
              const isHovered = hoveredPhase === i;
              return (
                <div
                  key={phase.name}
                  className={`flex items-start gap-3 px-3 py-2 rounded-md transition-colors cursor-pointer ${
                    isHovered ? 'bg-zinc-700/60' : 'hover:bg-zinc-800/60'
                  }`}
                  onMouseEnter={() => setHoveredPhase(i)}
                  onMouseLeave={() => setHoveredPhase(null)}
                >
                  <div
                    className="w-4 h-4 rounded-sm flex-shrink-0 mt-0.5"
                    style={{ backgroundColor: phase.color }}
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-zinc-100">
                      {phase.name}
                    </div>
                    <div className="text-xs text-zinc-400 font-mono">
                      {phase.startDeg}° &ndash; {phase.endDeg}° ({span}°)
                    </div>
                    {isHovered && (
                      <p className="text-xs text-zinc-400 mt-1">
                        {phase.description}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function ValidationResults() {
  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden">
      <h3 className="text-lg font-semibold text-zinc-100 px-5 py-3 border-b border-zinc-700 bg-zinc-800/80">
        Validation Results
      </h3>
      <div className="divide-y divide-zinc-800">
        {specs.validation.map((item) => (
          <div
            key={item.name}
            className="flex items-center gap-3 px-5 py-3 hover:bg-zinc-800/40 transition-colors"
          >
            <span
              className={
                item.status === 'pass'
                  ? 'badge-pass flex-shrink-0 w-6 h-6 rounded-full bg-green-600/20 border border-green-600/40 flex items-center justify-center text-green-400 text-sm'
                  : 'badge-fail flex-shrink-0 w-6 h-6 rounded-full bg-red-600/20 border border-red-600/40 flex items-center justify-center text-red-400 text-sm'
              }
            >
              {item.status === 'pass' ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-zinc-100">{item.name}</div>
              <div className="text-xs text-zinc-500">
                Required: {item.requirement}
              </div>
            </div>
            <span className="text-sm font-mono text-amber-400 flex-shrink-0">
              {item.value}
            </span>
          </div>
        ))}
      </div>
      <div className="px-5 py-3 border-t border-zinc-700 bg-zinc-800/60">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-green-400 font-bold">
            {specs.validation.filter((v) => v.status === 'pass').length}
          </span>
          <span className="text-zinc-400">passed</span>
          <span className="text-zinc-600 mx-1">/</span>
          <span className="text-zinc-400">{specs.validation.length} total</span>
        </div>
      </div>
    </div>
  );
}

function ToleranceStackup() {
  const { title, nominalMm, contributors } = specs.toleranceStackup;
  const totalTolerance = contributors.reduce((sum, c) => sum + c.tolerance, 0);
  const totalNominal = contributors.reduce((sum, c) => sum + c.nominal, 0);

  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-5">
      <h3 className="text-lg font-semibold text-zinc-100 mb-1">{title}</h3>
      <p className="text-sm text-zinc-400 font-mono mb-5">
        Nominal: {nominalMm} mm | Total stack: {totalNominal.toFixed(3)} mm | Worst-case tolerance: &plusmn;{totalTolerance.toFixed(3)} mm
      </p>

      {/* Stacked bar chart */}
      <div className="mb-6">
        <div className="flex rounded-md overflow-hidden h-10 border border-zinc-700">
          {contributors.map((c) => {
            const widthPercent = (c.nominal / totalNominal) * 100;
            return (
              <div
                key={c.name}
                className="relative group flex items-center justify-center overflow-hidden"
                style={{
                  width: `${widthPercent}%`,
                  backgroundColor: c.color,
                  minWidth: widthPercent > 3 ? undefined : '4px',
                }}
              >
                {widthPercent > 8 && (
                  <span className="text-[9px] font-mono text-zinc-100 font-bold truncate px-1">
                    {c.nominal}
                  </span>
                )}
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                  <div className="bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 shadow-lg whitespace-nowrap">
                    <div className="text-xs font-medium text-zinc-100">{c.name}</div>
                    <div className="text-[10px] text-zinc-400 font-mono mt-0.5">
                      {c.nominal} mm &plusmn; {c.tolerance} mm
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {/* Scale label */}
        <div className="flex justify-between mt-1 text-[10px] font-mono text-zinc-500">
          <span>0 mm</span>
          <span>{totalNominal.toFixed(3)} mm</span>
        </div>
      </div>

      {/* Detailed breakdown table */}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-zinc-500 uppercase tracking-wider">
            <th className="text-left px-3 py-2">Contributor</th>
            <th className="text-right px-3 py-2">Nominal</th>
            <th className="text-right px-3 py-2">Tolerance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {contributors.map((c) => (
            <tr key={c.name} className="hover:bg-zinc-800/40 transition-colors">
              <td className="px-3 py-2 text-zinc-300 flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: c.color }}
                />
                {c.name}
              </td>
              <td className="px-3 py-2 text-right font-mono text-zinc-100">
                {c.nominal.toFixed(3)} mm
              </td>
              <td className="px-3 py-2 text-right font-mono text-amber-400">
                &plusmn; {c.tolerance.toFixed(3)} mm
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-zinc-600">
            <td className="px-3 py-2 font-semibold text-zinc-100">Total</td>
            <td className="px-3 py-2 text-right font-mono font-bold text-zinc-100">
              {totalNominal.toFixed(3)} mm
            </td>
            <td className="px-3 py-2 text-right font-mono font-bold text-amber-400">
              &plusmn; {totalTolerance.toFixed(3)} mm
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export default function Specs() {
  return (
    <div className="space-y-10">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">Specifications</h1>
        <p className="text-zinc-400 mt-1">
          Complete engineering specifications, validation results, and tolerance analysis.
        </p>
      </div>

      {/* Spec tables grid */}
      <section>
        <h2 className="text-xl font-semibold text-zinc-100 mb-4">
          Component Specifications
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {SPEC_GROUPS.map((group) => (
            <SpecTable key={group} group={group} />
          ))}
        </div>
      </section>

      {/* Cam Timing */}
      <section>
        <h2 className="text-xl font-semibold text-zinc-100 mb-4">
          Cam Timing Diagram
        </h2>
        <CamTimingDiagram />
      </section>

      {/* Validation */}
      <section>
        <h2 className="text-xl font-semibold text-zinc-100 mb-4">
          Design Validation
        </h2>
        <ValidationResults />
      </section>

      {/* Tolerance Stack-up */}
      <section>
        <h2 className="text-xl font-semibold text-zinc-100 mb-4">
          Tolerance Stack-up Analysis
        </h2>
        <ToleranceStackup />
      </section>
    </div>
  );
}
