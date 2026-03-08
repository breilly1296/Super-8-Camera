import { Suspense, useRef, useState, useMemo } from 'react';
import { Canvas, useLoader, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Grid, Environment } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import * as THREE from 'three';

function STLModel({ url, position = [0, 0, 0], rotation = [0, 0, 0], color = '#a0a0a8', highlight = false, glowColor = '#22d3ee', name = '', onHover }) {
  const geometry = useLoader(STLLoader, url);
  const meshRef = useRef();
  const [hovered, setHovered] = useState(false);

  const displayColor = highlight ? glowColor : hovered ? '#e4e4e7' : color;
  const emissiveColor = highlight ? glowColor : hovered ? '#ffffff' : '#000000';
  const emissiveIntensity = highlight ? 0.3 : hovered ? 0.05 : 0;

  const centeredGeometry = useMemo(() => {
    const geo = geometry.clone();
    geo.computeBoundingBox();
    const center = new THREE.Vector3();
    geo.boundingBox.getCenter(center);
    geo.translate(-center.x, -center.y, -center.z);
    geo.computeVertexNormals();
    return geo;
  }, [geometry]);

  return (
    <mesh
      ref={meshRef}
      geometry={centeredGeometry}
      position={position}
      rotation={rotation.map(r => r * Math.PI / 180)}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover?.(name); }}
      onPointerOut={(e) => { e.stopPropagation(); setHovered(false); onHover?.(null); }}
    >
      <meshStandardMaterial
        color={displayColor}
        emissive={emissiveColor}
        emissiveIntensity={emissiveIntensity}
        metalness={0.6}
        roughness={0.35}
      />
    </mesh>
  );
}

function LoadingSpinner() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-zinc-600 border-t-amber-500 rounded-full animate-spin" />
        <span className="text-zinc-400 text-sm font-mono">Loading models...</span>
      </div>
    </Html>
  );
}

function Scene({ models, highlightParts = [], glowColor = '#22d3ee', onHover }) {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[50, 80, 50]} intensity={1.0} castShadow />
      <directionalLight position={[-30, 40, -20]} intensity={0.3} />
      <pointLight position={[0, 0, 50]} intensity={0.2} />

      <Suspense fallback={<LoadingSpinner />}>
        {models.map((model) => (
          <STLModel
            key={model.name}
            url={model.url}
            position={model.position || [0, 0, 0]}
            rotation={model.rotation || [0, 0, 0]}
            color={model.color || '#a0a0a8'}
            highlight={highlightParts.includes(model.name)}
            glowColor={glowColor}
            name={model.displayName || model.name}
            onHover={onHover}
          />
        ))}
      </Suspense>

      <Grid
        position={[0, 0, -45]}
        args={[200, 200]}
        cellSize={5}
        cellThickness={0.5}
        cellColor="#27272a"
        sectionSize={20}
        sectionThickness={1}
        sectionColor="#3f3f46"
        fadeDistance={150}
        fadeStrength={1}
        infiniteGrid
      />
    </>
  );
}

export default function ModelViewer({
  models = [],
  highlightParts = [],
  glowColor = '#22d3ee',
  height = '500px',
  className = '',
}) {
  const [hoveredPart, setHoveredPart] = useState(null);
  const controlsRef = useRef();

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  return (
    <div className={`relative bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden ${className}`} style={{ height }}>
      {/* Tooltip */}
      {hoveredPart && (
        <div className="absolute top-4 left-4 z-10 bg-zinc-800/90 backdrop-blur-sm border border-zinc-700 rounded-md px-3 py-1.5">
          <span className="text-sm font-mono text-zinc-200">{hoveredPart}</span>
        </div>
      )}

      {/* Controls */}
      <div className="absolute bottom-4 right-4 z-10 flex gap-2">
        <button
          onClick={resetCamera}
          className="bg-zinc-800/90 backdrop-blur-sm border border-zinc-700 rounded-md px-3 py-1.5 text-xs font-mono text-zinc-300 hover:bg-zinc-700 transition-colors"
        >
          Reset View
        </button>
      </div>

      {/* Hint */}
      <div className="absolute bottom-4 left-4 z-10 text-xs text-zinc-600 font-mono">
        Drag to rotate &middot; Scroll to zoom &middot; Right-drag to pan
      </div>

      <Canvas
        camera={{ position: [100, 80, 100], fov: 40, near: 0.1, far: 1000 }}
        className="canvas-container"
      >
        <Scene
          models={models}
          highlightParts={highlightParts}
          glowColor={glowColor}
          onHover={setHoveredPart}
        />
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.1}
          minDistance={20}
          maxDistance={400}
          target={[0, 0, 0]}
        />
      </Canvas>
    </div>
  );
}
