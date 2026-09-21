"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import AuthGate from "@/components/AuthGate";
import Dashboard from "@/components/Dashboard";
import IngestPanel from "@/components/IngestPanel";
import QuizPanel from "@/components/QuizPanel";
import ReviewPanel from "@/components/ReviewPanel";
import TutorPanel from "@/components/TutorPanel";
import { clearStoredAccount, fetchProvider, fetchScene, listSubjects, restoreAccount } from "@/lib/api";
import type { Account } from "@/lib/api";
import type { Scene, SceneNode } from "@/lib/types";

// The canvas touches `window` on import, so it must not render on the server.
const KnowledgeMap = dynamic(() => import("@/components/KnowledgeMap"), {
  ssr: false,
  loading: () => <div className="boot">Loading the map…</div>,
});

export default function Page() {
  // `undefined` = still checking localStorage; `null` = no account yet.
  const [account, setAccount] = useState<Account | null | undefined>(undefined);
  // The dashboard is the landing screen; picking a subject opens its map.
  const [subjectSlug, setSubjectSlug] = useState<string | null>(null);
  const [subjects, setSubjects] = useState<{ slug: string; title: string }[]>([]);
  const [scene, setScene] = useState<Scene | null>(null);
  const [selected, setSelected] = useState<SceneNode | null>(null);
  const [provider, setProvider] = useState<string>("…");
  const [error, setError] = useState<string | null>(null);
  const [showIngest, setShowIngest] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [quizNode, setQuizNode] = useState<SceneNode | null>(null);

  // Restore a stored account on load, falling back to the auth gate.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let storedToken: string | null = null;
      try {
        storedToken = localStorage.getItem("orrery.sessionToken");
      } catch {
        /* private window or blocked storage */
      }
      if (storedToken) {
        const restored = await restoreAccount(storedToken);
        if (!cancelled) setAccount(restored);
      } else if (!cancelled) {
        setAccount(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadScene = useCallback((slug: string) => {
    fetchScene(slug)
      .then((s) => {
        setScene(s);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, []);

  // The subject list is used by the map's own picker; fetched once an
  // account exists, independent of which subject (if any) is open.
  useEffect(() => {
    if (!account) return;
    fetchProvider().then((p) => setProvider(p.provider));
    listSubjects().then(setSubjects);
  }, [account]);

  useEffect(() => {
    if (!account || !subjectSlug) return;
    loadScene(subjectSlug);
  }, [account, subjectSlug, loadScene]);

  const nodesById = useMemo(
    () => new Map((scene?.nodes ?? []).map((n) => [n.id, n])),
    [scene]
  );

  // A mastery change can unlock a downstream concept, so re-fetch the scene:
  // the server owns the gating rule, not the client.
  const handleMasteryChange = useCallback(
    async (conceptId: string, mastery: number) => {
      if (!account) return;
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
      if (!subjectSlug) return;
      try {
        const fresh = await fetchScene(subjectSlug);
        setScene(fresh);
        setSelected((s) => (s ? fresh.nodes.find((n) => n.id === s.id) ?? null : null));
      } catch {
        /* the optimistic update above still stands */
      }
    },
    [account, subjectSlug]
  );

  const handleIngested = useCallback(
    (slug: string) => {
      setShowIngest(false);
      setSelected(null);
      setSubjectSlug(slug);
      listSubjects().then(setSubjects);
    },
    []
  );

  const handleSwitchUser = useCallback(() => {
    clearStoredAccount();
    setAccount(null);
    setSubjectSlug(null);
    setScene(null);
    setSelected(null);
    setSubjects([]);
  }, []);

  if (account === undefined) return <div className="boot">Loading…</div>;

  if (account === null) {
    return <AuthGate onReady={(a) => setAccount(a)} />;
  }

  if (subjectSlug === null) {
    return (
      <>
        <Dashboard
          displayName={account.displayName}
          onOpenSubject={(slug) => {
            setSelected(null);
            setSubjectSlug(slug);
          }}
          onNewSubject={() => setShowIngest(true)}
          onSwitchUser={handleSwitchUser}
        />
        {showIngest && (
          <IngestPanel onCreated={handleIngested} onClose={() => setShowIngest(false)} />
        )}
      </>
    );
  }

  if (error) {
    return (
      <main className="boot boot-error">
        <div>
          <h1>The map could not load</h1>
          <p>{error}</p>
          <p className="hint">Start the API with <code>uvicorn main:app</code> on port 8000.</p>
          <button className="btn" onClick={() => { setSubjectSlug(null); setError(null); }}>
            ← Back to dashboard
          </button>
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
          <p className="hud-eyebrow">Orrery · {account.displayName}</p>
          <div className="subject-row">
            <button
              className="icon-btn"
              onClick={() => {
                setSubjectSlug(null);
                setSelected(null);
              }}
              aria-label="Back to dashboard"
              title="Back to dashboard"
            >
              ←
            </button>
            <select
              id="subject-picker"
              className="subject-picker"
              value={subjectSlug}
              onChange={(e) => {
                setSubjectSlug(e.target.value);
                setSelected(null);
              }}
            >
              {!subjects.some((s) => s.slug === subjectSlug) && (
                <option value={subjectSlug}>{scene.subject.title}</option>
              )}
              {subjects.map((s) => (
                <option key={s.slug} value={s.slug}>
                  {s.title}
                </option>
              ))}
            </select>
            <button className="btn btn-add" onClick={() => setShowIngest(true)}>
              + New subject
            </button>
            <button className="btn btn-review" onClick={() => setShowReview(true)}>
              Review
            </button>
            <button className="btn" onClick={handleSwitchUser}>
              Switch user
            </button>
          </div>
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
          nodesById={nodesById}
          onClose={() => setSelected(null)}
          onMasteryChange={handleMasteryChange}
          onQuiz={() => setQuizNode(selected)}
        />
      )}

      {quizNode && (
        <QuizPanel
          conceptId={quizNode.id}
          conceptTitle={quizNode.title}
          onClose={() => setQuizNode(null)}
          onMasteryChange={handleMasteryChange}
        />
      )}

      {showIngest && (
        <IngestPanel onCreated={handleIngested} onClose={() => setShowIngest(false)} />
      )}

      {showReview && (
        <ReviewPanel
          subjectSlug={subjectSlug}
          onClose={() => setShowReview(false)}
          onMasteryChange={handleMasteryChange}
        />
      )}
    </main>
  );
}
