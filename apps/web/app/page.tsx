"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import TutorPanel from "@/components/TutorPanel";
import { fetchProvider, fetchScene } from "@/lib/api";
import type { Scene, SceneNode } from "@/lib/types";

// The canvas touches `window` on import, so it must not render on the server.
const KnowledgeMap = dynamic(() => import("@/components/KnowledgeMap"), {
  ssr: false,
  loading: () => <div className="boot">Loading the map…</div>,
});

// Seeded demo learner. Real deployments read this from the auth session.
const USER_ID =
  process.env.NEXT_PUBLIC_DEMO_USER_ID ?? "178788d9-bf30-4c2e-8880-fc5a3e9a2179";

export default function Page() {
  const [scene, setScene] = useState<Scene | null>(null);
  const [selected, setSelected] = useState<SceneNode | null>(null);
  const [provider, setProvider] = useState<string>("…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchScene("algebra", USER_ID).then(setScene).catch((e) => setError(e.message));
    fetchProvider().then((p) => setProvider(p.provider));
  }, []);

  const nodesById = useMemo(
    () => new Map((scene?.nodes ?? []).map((n) => [n.id, n])),
    [scene]
  );

  // A mastery change can unlock a downstream concept, so re-fetch the scene:
  // the server owns the gating rule, not the client.
  const handleMasteryChange = useCallback(
    async (conceptId: string, mastery: number) => {
      setScene((prev) =>
        prev
          ? {
              ...prev,
              nodes: prev.nodes.map((n) =>
                n.id === conceptId ? { ...n, mastery, mastered: mastery >= prev.masteryThreshold } : n
              ),
            }
          : prev
      );
      try {
        const fresh = await fetchScene("algebra", USER_ID);
        setScene(fresh);
        setSelected((s) => (s ? fresh.nodes.find((n) => n.id === s.id) ?? null : null));
      } catch {
        /* the optimistic update above still stands */
      }
    },
    []
  );

  if (error) {
    return (
      <main className="boot boot-error">
        <div>
          <h1>The map could not load</h1>
          <p>{error}</p>
          <p className="hint">Start the API with <code>uvicorn main:app</code> on port 8000.</p>
        </div>
      </main>
    );
  }

  if (!scene) return <div className="boot">Loading the map…</div>;

  const mastered = scene.nodes.filter((n) => n.mastered).length;
  const open = scene.nodes.filter((n) => !n.locked && !n.mastered).length;
  const locked = scene.nodes.filter((n) => n.locked).length;

  return (
    <main className="stage">
      <KnowledgeMap scene={scene} selectedId={selected?.id ?? null} onSelect={setSelected} />

      <header className="hud hud-top">
        <div>
          <p className="hud-eyebrow">Orrery · knowledge map</p>
          <h1>{scene.subject.title}</h1>
        </div>
        <dl className="counts">
          <div>
            <dt>Mastered</dt>
            <dd className="c-mastered">{mastered}</dd>
          </div>
          <div>
            <dt>Open</dt>
            <dd className="c-open">{open}</dd>
          </div>
          <div>
            <dt>Locked</dt>
            <dd className="c-locked">{locked}</dd>
          </div>
        </dl>
      </header>

      <footer className="hud hud-bottom">
        <ul className="legend">
          <li><i className="dot d-mastered" />Mastered</li>
          <li><i className="dot d-learning" />In progress</li>
          <li><i className="dot d-open" />Available</li>
          <li><i className="dot d-locked" />Locked</li>
        </ul>
        <p className="hud-note">
          Height is prerequisite depth · size and glow are mastery · tutor on{" "}
          <strong>{provider}</strong>
        </p>
      </footer>

      {selected && (
        <TutorPanel
          node={selected}
          userId={USER_ID}
          nodesById={nodesById}
          onClose={() => setSelected(null)}
          onMasteryChange={handleMasteryChange}
        />
      )}
    </main>
  );
}
