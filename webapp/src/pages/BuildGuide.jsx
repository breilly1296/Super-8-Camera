import { useState, useEffect, useMemo, useCallback } from 'react';
import ModelViewer from '../components/ModelViewer';
import buildSteps from '../data/build_steps.json';
import assemblyPositions from '../data/assembly_positions.json';

const TOTAL_STEPS = buildSteps.length;

export default function BuildGuide() {
  const [currentStep, setCurrentStep] = useState(0);

  const step = buildSteps[currentStep];

  // Collect all parts accumulated up to and including the current step
  const accumulatedModels = useMemo(() => {
    const models = [];
    for (let i = 0; i <= currentStep; i++) {
      for (const partName of buildSteps[i].parts) {
        const pos = assemblyPositions[partName];
        if (pos) {
          models.push({
            url: `/models/${partName}.stl`,
            position: pos.position,
            rotation: pos.rotation,
            color: pos.color,
            name: partName,
            displayName: pos.name,
          });
        }
      }
    }
    return models;
  }, [currentStep]);

  // Only the current step's parts should be highlighted
  const highlightParts = useMemo(() => {
    return step.parts.filter((p) => assemblyPositions[p]);
  }, [step]);

  const goNext = useCallback(() => {
    setCurrentStep((prev) => Math.min(prev + 1, TOTAL_STEPS - 1));
  }, []);

  const goPrev = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  }, []);

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'ArrowRight') {
        goNext();
      } else if (e.key === 'ArrowLeft') {
        goPrev();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrev]);

  const progressPercent = ((currentStep + 1) / TOTAL_STEPS) * 100;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl sm:text-4xl font-bold text-zinc-100 tracking-tight">
          Build Guide
        </h1>
        <p className="text-zinc-400 mt-2 font-mono text-sm">
          Step-by-step assembly &middot; 10 steps &middot; ~93 minutes total
        </p>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-zinc-300 font-medium">
            Step {currentStep + 1} of {TOTAL_STEPS}
          </span>
          <span className="text-zinc-500 font-mono">
            {Math.round(progressPercent)}% complete
          </span>
        </div>
        <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-amber-500 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {/* Step dots */}
        <div className="flex items-center gap-1 pt-1">
          {buildSteps.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentStep(i)}
              className={`h-1.5 rounded-full transition-all duration-200 ${
                i === currentStep
                  ? 'w-6 bg-amber-500'
                  : i < currentStep
                    ? 'w-3 bg-amber-500/40'
                    : 'w-3 bg-zinc-700'
              }`}
              aria-label={`Go to step ${i + 1}`}
            />
          ))}
        </div>
      </div>

      {/* 3D Viewer */}
      <div>
        <ModelViewer
          models={accumulatedModels}
          highlightParts={highlightParts}
          glowColor="#22d3ee"
          height="500px"
          className="w-full"
        />
        {step.parts.length > 0 && (
          <p className="text-xs text-cyan-400/70 font-mono mt-2">
            Highlighted in cyan: parts added in this step
          </p>
        )}
      </div>

      {/* Step content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main step info - takes 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          {/* Title and description */}
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
                <span className="text-amber-500 font-bold font-mono text-sm">
                  {step.step}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-xl font-bold text-zinc-100">
                  {step.title}
                </h2>
                <p className="text-zinc-400 mt-3 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          </div>

          {/* Tools and time */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
                Tools Needed
              </h3>
              <ul className="space-y-1.5">
                {step.tools.map((tool) => (
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

            <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
                Estimated Time
              </h3>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-amber-500 font-mono">
                  {step.estimatedMinutes}
                </span>
                <span className="text-zinc-400 text-sm">minutes</span>
              </div>
            </div>
          </div>

          {/* Tips and warnings */}
          {step.tips.length > 0 && (
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4">
              <h3 className="text-xs uppercase tracking-wider text-amber-500 font-mono mb-3">
                Tips &amp; Warnings
              </h3>
              <ul className="space-y-2">
                {step.tips.map((tip, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-zinc-300"
                  >
                    <span className="text-amber-500 flex-shrink-0 mt-0.5">
                      &bull;
                    </span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Sidebar - parts checklist */}
        <div className="space-y-4">
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
              Parts Needed for This Step
            </h3>
            {step.partNumbers.length > 0 ? (
              <ul className="space-y-2">
                {step.partNumbers.map((pn, i) => {
                  // Match part number to display name from parts in this step
                  const partKey = step.parts[i];
                  const displayName = partKey
                    ? assemblyPositions[partKey]?.name || partKey
                    : pn;
                  return (
                    <li
                      key={pn}
                      className="flex items-center gap-3 text-sm bg-zinc-900/50 rounded-md px-3 py-2"
                    >
                      <span className="w-4 h-4 rounded border border-zinc-600 flex-shrink-0" />
                      <div className="min-w-0">
                        <div className="text-zinc-200 truncate">
                          {displayName}
                        </div>
                        <div className="text-zinc-500 font-mono text-xs">
                          {pn}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-sm text-zinc-500 italic">
                No new parts needed &mdash; final check only.
              </p>
            )}
          </div>

          {/* Quick step summary */}
          <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4">
            <h3 className="text-xs uppercase tracking-wider text-zinc-500 font-mono mb-3">
              All Steps
            </h3>
            <ol className="space-y-1">
              {buildSteps.map((s, i) => (
                <li key={i}>
                  <button
                    onClick={() => setCurrentStep(i)}
                    className={`w-full text-left text-xs px-2 py-1.5 rounded transition-colors ${
                      i === currentStep
                        ? 'bg-amber-500/10 text-amber-400 font-medium'
                        : i < currentStep
                          ? 'text-zinc-500 hover:text-zinc-300'
                          : 'text-zinc-600 hover:text-zinc-400'
                    }`}
                  >
                    <span className="font-mono mr-2">
                      {i < currentStep ? '\u2713' : `${i + 1}.`}
                    </span>
                    {s.title}
                  </button>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
        <button
          onClick={goPrev}
          disabled={currentStep === 0}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all ${
            currentStep === 0
              ? 'bg-zinc-800/30 text-zinc-600 cursor-not-allowed'
              : 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-zinc-100'
          }`}
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
          Previous
        </button>

        <span className="text-xs text-zinc-600 font-mono hidden sm:block">
          Use arrow keys to navigate
        </span>

        <button
          onClick={goNext}
          disabled={currentStep === TOTAL_STEPS - 1}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all ${
            currentStep === TOTAL_STEPS - 1
              ? 'bg-zinc-800/30 text-zinc-600 cursor-not-allowed'
              : 'bg-amber-600 text-zinc-950 hover:bg-amber-500'
          }`}
        >
          Next
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
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
