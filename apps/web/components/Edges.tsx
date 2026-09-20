"use client";

import { useMemo } from "react";
import * as THREE from "three";

import type { SceneEdge, SceneNode } from "@/lib/types";

const STYLE: Record<string, { colour: string; opacity: number }> = {
  // A prerequisite is the only edge that gates anything, so it is the only
  // one drawn solidly.
  prerequisite: { colour: "#6f8fa6", opacity: 0.5 },
  related: { colour: "#4bd6b0", opacity: 0.22 },
  confused_with: { colour: "#e0776c", opacity: 0.3 },
};

export default function Edges({
  nodes,
  edges,
  highlightId,
}: {
  nodes: SceneNode[];
  edges: SceneEdge[];
  highlightId: string | null;
}) {
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const groups = useMemo(() => {
    const out: Record<string, { points: number[]; colour: string; opacity: number }> = {};
    for (const relation of Object.keys(STYLE)) {
      out[relation] = { points: [], ...STYLE[relation] };
    }
    for (const e of edges) {
      const a = byId.get(e.source);
      const b = byId.get(e.target);
      if (!a || !b) continue;
      const bucket = out[e.relation];
      if (!bucket) continue;
      bucket.points.push(
        a.position.x, a.position.y, a.position.z,
        b.position.x, b.position.y, b.position.z
      );
    }
    return out;
  }, [byId, edges]);

  // Edges touching the selected concept, drawn brightly on top so the
  // prerequisite chain is legible the moment you click something.
  const highlight = useMemo(() => {
    if (!highlightId) return null;
    const pts: number[] = [];
    for (const e of edges) {
      if (e.source !== highlightId && e.target !== highlightId) continue;
      const a = byId.get(e.source);
      const b = byId.get(e.target);
      if (!a || !b) continue;
      pts.push(
        a.position.x, a.position.y, a.position.z,
        b.position.x, b.position.y, b.position.z
      );
    }
    return pts.length ? new Float32Array(pts) : null;
  }, [byId, edges, highlightId]);

  return (
    <group>
      {Object.entries(groups).map(([relation, g]) =>
        g.points.length ? (
          <lineSegments key={relation} raycast={() => null}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[new Float32Array(g.points), 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial
              color={g.colour}
              transparent
              opacity={highlightId ? g.opacity * 0.35 : g.opacity}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </lineSegments>
        ) : null
      )}

      {highlight && (
        <lineSegments raycast={() => null}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[highlight, 3]} />
          </bufferGeometry>
          <lineBasicMaterial
            color="#9fe8ff"
            transparent
            opacity={0.9}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </lineSegments>
      )}
    </group>
  );
}
