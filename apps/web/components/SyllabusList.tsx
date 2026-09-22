"use client";

import type { Scene, SceneNode } from "@/lib/types";

/** The subject's concepts as an ordered, browsable course outline — the flat
 *  reading of the same graph the 3D map draws. Prerequisite depth becomes a
 *  stage, so a learner can see the whole path without navigating in 3D. */
export default function SyllabusList({
  scene,
  onSelect,
}: {
  scene: Scene;
  onSelect: (node: SceneNode) => void;
}) {
  const byTitle = new Map(scene.nodes.map((n) => [n.id, n.title]));

  const stages = new Map<number, SceneNode[]>();
  for (const node of scene.nodes) {
    const bucket = stages.get(node.depth);
    if (bucket) bucket.push(node);
    else stages.set(node.depth, [node]);
  }
  const ordered = [...stages.entries()].sort((a, b) => a[0] - b[0]);

  return (
    <div className="syllabus">
      {ordered.map(([depth, nodes]) => (
        <section key={depth} className="syllabus-stage">
          <h2 className="syllabus-stage-head">
            <span className="syllabus-stage-num">Stage {depth + 1}</span>
            {depth === 0 ? "Start here — no prerequisites" : `Builds on stage ${depth}`}
          </h2>

          <ul className="syllabus-rows">
            {nodes.map((node) => {
              const pct = Math.round(node.mastery * 100);
              const status = node.mastered
                ? "mastered"
                : node.locked
                ? "locked"
                : node.mastery > 0
                ? "learning"
                : "open";
              const label = node.mastered
                ? "Review"
                : node.locked
                ? "Locked"
                : node.mastery > 0
                ? "Continue"
                : "Start";

              return (
                <li key={node.id}>
                  <button
                    className={`syllabus-row is-${status}`}
                    onClick={() => onSelect(node)}
                    disabled={node.locked}
                  >
                    <span className={`dot d-${status === "open" ? "open" : status}`} />

                    <span className="syllabus-row-body">
                      <span className="syllabus-row-title">{node.title}</span>
                      {node.summary && (
                        <span className="syllabus-row-summary">{node.summary}</span>
                      )}
                      {node.locked && node.blockedBy.length > 0 && (
                        <span className="syllabus-row-blocked">
                          Needs:{" "}
                          {node.blockedBy
                            .map((id) => byTitle.get(id) ?? "another concept")
                            .join(", ")}
                        </span>
                      )}
                    </span>

                    <span className="syllabus-row-right">
                      <span className="syllabus-row-track">
                        <span
                          className="syllabus-row-fill"
                          style={{ width: `${pct}%`, background: scene.subject.accent }}
                        />
                      </span>
                      <span className="syllabus-row-pct">{pct}%</span>
                      <span className="syllabus-row-action">{label}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
