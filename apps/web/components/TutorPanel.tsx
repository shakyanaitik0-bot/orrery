"use client";

import { useEffect, useRef, useState } from "react";

import { askTutor, submitAnswer } from "@/lib/api";
import type { SceneNode } from "@/lib/types";

interface Turn {
  role: "user" | "tutor";
  content: string;
}

export default function TutorPanel({
  node,
  nodesById,
  onClose,
  onMasteryChange,
  onQuiz,
}: {
  node: SceneNode;
  nodesById: Map<string, SceneNode>;
  onClose: () => void;
  onMasteryChange: (conceptId: string, mastery: number) => void;
  onQuiz: () => void;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTurns([]);
    setError(null);
    setDraft("");
  }, [node.id]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  async function send() {
    const message = draft.trim();
    if (!message || busy) return;
    setDraft("");
    setError(null);
    setBusy(true);
    setTurns((t) => [...t, { role: "user", content: message }, { role: "tutor", content: "" }]);

    try {
      await askTutor(node.id, message, (chunk) => {
        setTurns((t) => {
          const next = [...t];
          next[next.length - 1] = {
            role: "tutor",
            content: next[next.length - 1].content + chunk,
          };
          return next;
        });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "The tutor did not respond.");
      setTurns((t) => t.slice(0, -1));
    } finally {
      setBusy(false);
    }
  }

  async function grade(correct: boolean) {
    try {
      const result = await submitAnswer(node.id, correct);
      onMasteryChange(node.id, result.mastery);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record that.");
    }
  }

  const blockers = node.blockedBy
    .map((id) => nodesById.get(id)?.title)
    .filter(Boolean) as string[];

  return (
    <aside className="panel">
      <header className="panel-head">
        <div>
          <p className="panel-eyebrow">Depth {node.depth}</p>
          <h2>{node.title}</h2>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      {node.summary && <p className="panel-summary">{node.summary}</p>}

      <div className="meter">
        <div className="meter-row">
          <span>Mastery</span>
          <strong>{Math.round(node.mastery * 100)}%</strong>
        </div>
        <div className="meter-track">
          <div
            className={`meter-fill ${node.mastered ? "is-mastered" : ""}`}
            style={{ width: `${Math.max(2, node.mastery * 100)}%` }}
          />
          <div className="meter-threshold" style={{ left: "70%" }} />
        </div>
        <p className="meter-note">
          {node.mastered
            ? "Mastered — above the 70% threshold."
            : `${Math.round((0.7 - node.mastery) * 100)} points below the threshold.`}
        </p>
      </div>

      {node.locked && (
        <div className="locked-note">
          <strong>Locked.</strong> Master {blockers.join(", ")} first.
        </div>
      )}

      <div className="grade-row">
        <span>Record practice</span>
        <div>
          <button onClick={() => grade(true)} className="btn btn-ok">
            Got it right
          </button>
          <button onClick={() => grade(false)} className="btn btn-no">
            Got it wrong
          </button>
        </div>
      </div>

      <div className="grade-row">
        <span>Check yourself</span>
        <div>
          <button onClick={onQuiz} className="btn btn-review">
            Quiz me
          </button>
        </div>
      </div>

      <div className="chat" ref={scroller}>
        {turns.length === 0 && (
          <p className="chat-empty">
            Ask about {node.title.toLowerCase()} — the tutor adapts to where your
            mastery currently sits.
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`bubble bubble-${t.role}`}>
            {t.content || <span className="dots">…</span>}
          </div>
        ))}
        {error && <p className="chat-error">{error}</p>}
      </div>

      <div className="composer">
        <input
          id="tutor-input"
          value={draft}
          placeholder="Ask a question"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          disabled={busy}
        />
        <button className="btn btn-send" onClick={send} disabled={busy || !draft.trim()}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </aside>
  );
}
