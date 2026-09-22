"use client";

import type { Scene, SceneNode } from "@/lib/types";

const BOX_W = 190;
const BOX_H = 64;
const COL_GAP = 90;
const ROW_GAP = 22;
const PAD = 40;

function statusOf(node: SceneNode): "mastered" | "learning" | "open" | "locked" {
  if (node.mastered) return "mastered";
  if (node.locked) return "locked";
  if (node.mastery > 0) return "learning";
  return "open";
}

/** A left-to-right flowchart of the same subject: one column per
 *  prerequisite stage, boxes connected by the actual prerequisite edges.
 *  Positions are derived purely from `depth` and list order, so no DOM
 *  measurement is needed to draw the connectors. */
export default function FlowchartView({
  scene,
  onSelect,
}: {
  scene: Scene;
  onSelect: (node: SceneNode) => void;
}) {
  const columns = new Map<number, SceneNode[]>();
  for (const node of scene.nodes) {
    const bucket = columns.get(node.depth);
    if (bucket) bucket.push(node);
    else columns.set(node.depth, [node]);
  }
  const depths = [...columns.keys()].sort((a, b) => a - b);

  const pos = new Map<string, { x: number; y: number }>();
  for (const d of depths) {
    columns.get(d)!.forEach((node, i) => {
      pos.set(node.id, {
        x: PAD + d * (BOX_W + COL_GAP),
        y: PAD + i * (BOX_H + ROW_GAP),
      });
    });
  }

  const maxRows = Math.max(1, ...depths.map((d) => columns.get(d)!.length));
  const width = PAD * 2 + depths.length * BOX_W + Math.max(0, depths.length - 1) * COL_GAP;
  const height = PAD * 2 + maxRows * BOX_H + Math.max(0, maxRows - 1) * ROW_GAP;

  const prereqEdges = scene.edges.filter((e) => e.relation === "prerequisite");

  return (
    <div className="flowchart">
      <div className="flowchart-canvas" style={{ width, height }}>
        <svg className="flowchart-svg" width={width} height={height}>
          <defs>
            <marker
              id="flow-arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--rule)" />
            </marker>
          </defs>
          {prereqEdges.map((e, i) => {
            const from = pos.get(e.source);
            const to = pos.get(e.target);
            if (!from || !to) return null;
            const x1 = from.x + BOX_W;
            const y1 = from.y + BOX_H / 2;
            const x2 = to.x;
            const y2 = to.y + BOX_H / 2;
            const midX = (x1 + x2) / 2;
            return (
              <path
                key={i}
                d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                stroke="var(--rule)"
                strokeWidth="1.5"
                fill="none"
                markerEnd="url(#flow-arrow)"
              />
            );
          })}
        </svg>

        {scene.nodes.map((node) => {
          const p = pos.get(node.id);
          if (!p) return null;
          const status = statusOf(node);
          const pct = Math.round(node.mastery * 100);
          return (
            <button
              key={node.id}
              className={`flow-box is-${status}`}
              style={{ left: p.x, top: p.y, width: BOX_W, height: BOX_H }}
              onClick={() => onSelect(node)}
              disabled={node.locked}
              title={node.locked ? `Locked — needs ${node.blockedBy.length} more concept(s)` : node.title}
            >
              <span className={`dot d-${status === "open" ? "open" : status}`} />
              <span className="flow-box-body">
                <span className="flow-box-title">{node.title}</span>
                <span className="flow-box-pct">{pct}%</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
