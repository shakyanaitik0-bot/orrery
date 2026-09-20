"use client";

import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";

import ConceptNode from "./ConceptNode";
import Edges from "./Edges";
import type { Scene, SceneNode } from "@/lib/types";

function LayerFloors({
  layers,
  layerHeight,
  layerRadius,
}: {
  layers: number;
  layerHeight: number;
  layerRadius: number[];
}) {
  // One faint ring per prerequisite depth, sized to that layer's actual
  // spread, so the climb reads as structure rather than scattered points.
  return (
    <group>
      {Array.from({ length: layers }).map((_, i) => {
        const r = (layerRadius[i] ?? 7.4) * 1.25;
        return (
          <mesh
            key={i}
            rotation={[-Math.PI / 2, 0, 0]}
            position={[0, i * layerHeight - 0.9, 0]}
            raycast={() => null}
          >
            <ringGeometry args={[r, r + 0.12, 96]} />
            <meshBasicMaterial color="#2a3a46" transparent opacity={0.34} />
          </mesh>
        );
      })}
    </group>
  );
}

export default function KnowledgeMap({
  scene,
  selectedId,
  onSelect,
}: {
  scene: Scene;
  selectedId: string | null;
  onSelect: (node: SceneNode | null) => void;
}) {
  // Centre the graph vertically so orbiting feels balanced whatever its height.
  const midY = useMemo(() => {
    if (!scene.nodes.length) return 0;
    const ys = scene.nodes.map((n) => n.position.y);
    return (Math.min(...ys) + Math.max(...ys)) / 2;
  }, [scene.nodes]);

  // Tolerate an older API that does not send the layout hints: the map is
  // still drawable from node positions alone.
  const layerHeight = scene.layerHeight ?? 3;
  const layerRadius = scene.layerRadius ?? [];
  const height = (scene.layers || 1) * layerHeight;
  const widest = Math.max(8, ...(layerRadius.length ? layerRadius : [8]));
  // Pull back far enough that the whole climb is in frame on load, rather
  // than opening on a crop of the lower layers.
  const distance = Math.max(height * 1.45, widest * 3.8);

  return (
    <Canvas
      camera={{
        position: [distance * 0.58, midY + height * 0.1, distance * 0.58],
        fov: 45,
        near: 0.1,
        far: 600,
      }}
      dpr={[1, 2]}
      onPointerMissed={() => onSelect(null)}
    >
      <color attach="background" args={["#080d13"]} />
      <fog attach="fog" args={["#080d13", distance * 0.9, distance * 3.2]} />

      <ambientLight intensity={0.35} />
      <pointLight position={[18, midY + height * 0.7, 18]} intensity={1.6} color="#cfe9f5" />
      <pointLight position={[-20, midY - 14, -14]} intensity={0.7} color="#2f7d8c" />

      <Suspense fallback={null}>
        <Stars radius={150} depth={60} count={2600} factor={4} fade speed={0.4} />

        <group position={[0, -midY, 0]}>
          <LayerFloors
            layers={scene.layers}
            layerHeight={layerHeight}
            layerRadius={layerRadius}
          />
          <Edges nodes={scene.nodes} edges={scene.edges} highlightId={selectedId} />
          {scene.nodes.map((node) => (
            <ConceptNode
              key={node.id}
              node={node}
              threshold={scene.masteryThreshold}
              selected={selectedId === node.id}
              onSelect={onSelect}
            />
          ))}
        </group>
      </Suspense>

      <OrbitControls
        enablePan
        enableDamping
        dampingFactor={0.07}
        minDistance={8}
        maxDistance={Math.max(160, distance * 2.6)}
        autoRotate={!selectedId}
        autoRotateSpeed={0.35}
      />
    </Canvas>
  );
}
