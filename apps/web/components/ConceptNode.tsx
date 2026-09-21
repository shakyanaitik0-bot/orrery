"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

import type { SceneNode } from "@/lib/types";

const MASTERED = new THREE.Color("#4bd6b0");
const LEARNING = new THREE.Color("#e0b341");
const OPEN = new THREE.Color("#5aa9c7");
const LOCKED = new THREE.Color("#6d8496");

/** Colour encodes state, not subject: the learner's own progress is the thing
 *  worth reading at a glance from across the map. */
function colourFor(node: SceneNode, threshold: number): THREE.Color {
  if (node.mastered) return MASTERED;
  if (node.locked) return LOCKED;
  if (node.mastery > 0) return LEARNING;
  return OPEN;
}

export default function ConceptNode({
  node,
  threshold,
  selected,
  onSelect,
}: {
  node: SceneNode;
  threshold: number;
  selected: boolean;
  onSelect: (node: SceneNode) => void;
}) {
  const mesh = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const colour = colourFor(node, threshold);
  // Size carries mastery: a well-known concept is a bigger body.
  const radius = 0.55 + node.mastery * 0.75;

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (mesh.current) {
      mesh.current.rotation.y = t * 0.15 + node.depth;
      const pulse = selected ? 1 + Math.sin(t * 3) * 0.06 : 1;
      mesh.current.scale.setScalar(pulse);
    }
    if (halo.current) {
      // Only concepts in progress breathe — it draws the eye to live work.
      const active = !node.locked && !node.mastered && node.mastery > 0;
      const base = active ? 1.35 + Math.sin(t * 1.6) * 0.09 : 1.3;
      halo.current.scale.setScalar(base);
    }
  });

  return (
    <group position={[node.position.x, node.position.y, node.position.z]}>
      <mesh
        ref={mesh}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(node);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <icosahedronGeometry args={[radius, node.locked ? 1 : 2]} />
        <meshStandardMaterial
          color={colour}
          emissive={colour}
          // Locked concepts stay clearly visible: you should be able to see
          // where the subject goes before you can get there.
          emissiveIntensity={node.locked ? 0.45 : 0.35 + node.mastery * 0.85}
          roughness={node.locked ? 0.6 : 0.25}
          metalness={node.locked ? 0.2 : 0.45}
          wireframe={node.locked}
          transparent
          opacity={node.locked ? 0.95 : 1}
        />
      </mesh>

      {/* Glow shell, sized by mastery. Locked concepts get a faint one too,
          so they read as present-but-unreachable rather than as empty space. */}
      <mesh ref={halo} raycast={() => null}>
        <sphereGeometry args={[radius, 24, 24]} />
        <meshBasicMaterial
          color={colour}
          transparent
          opacity={node.locked ? 0.05 : 0.06 + node.mastery * 0.08}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>

      {(hovered || selected) && (
        <Html
          center
          distanceFactor={22}
          position={[0, radius + 1.1, 0]}
          style={{ pointerEvents: "none" }}
          // drei defaults this to ~16.7 million, which floats the label over
          // any open modal. Keep labels below the modal layer instead.
          zIndexRange={[100, 0]}
        >
          <div className="node-label">
            <strong>{node.title}</strong>
            <span>
              {node.locked
                ? `Locked · ${node.blockedBy.length} prerequisite${
                    node.blockedBy.length === 1 ? "" : "s"
                  } left`
                : `${Math.round(node.mastery * 100)}% mastered`}
            </span>
          </div>
        </Html>
      )}
    </group>
  );
}
