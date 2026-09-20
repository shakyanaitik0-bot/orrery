"use client";

import { useEffect, useState } from "react";

import { fetchDueCards, gradeCard } from "@/lib/api";
import type { ReviewCard } from "@/lib/api";

// SM-2's own four-way recall scale, mapped to plain language. "Again" is the
// only one below the pass line (quality 3) — everything else also counts as
// a correct answer for mastery.
const GRADES: { label: string; quality: number; tone: string }[] = [
  { label: "Again", quality: 1, tone: "btn-no" },
  { label: "Hard", quality: 3, tone: "" },
  { label: "Good", quality: 4, tone: "btn-ok" },
  { label: "Easy", quality: 5, tone: "btn-ok" },
];

export default function ReviewPanel({
  userId,
  subjectSlug,
  onClose,
  onMasteryChange,
}: {
  userId: string;
  subjectSlug: string;
  onClose: () => void;
  onMasteryChange: (conceptId: string, mastery: number) => void;
}) {
  const [cards, setCards] = useState<ReviewCard[] | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(0);

  useEffect(() => {
    fetchDueCards(userId, subjectSlug)
      .then(setCards)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load the queue."));
  }, [userId, subjectSlug]);

  const current = cards?.[index];

  async function grade(quality: number) {
    if (!current || busy) return;
    setBusy(true);
    try {
      const result = await gradeCard(userId, current.id, quality);
      onMasteryChange(current.conceptId, result.mastery);
      setDone((d) => d + 1);
      setRevealed(false);
      setIndex((i) => i + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record that review.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal review-modal" onClick={(e) => e.stopPropagation()}>
        <header className="panel-head">
          <div>
            <p className="panel-eyebrow">Review · {subjectSlug}</p>
            <h2>Flashcards</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {error && <p className="chat-error">{error}</p>}

        {!cards && !error && <p className="chat-empty">Loading the queue…</p>}

        {cards && cards.length === 0 && (
          <p className="ingest-success">Nothing due right now. Come back later.</p>
        )}

        {cards && current && (
          <>
            <p className="review-progress">
              Card {index + 1} of {cards.length}
              {done > 0 && ` · ${done} reviewed this session`}
            </p>

            <div className="flashcard" onClick={() => setRevealed((r) => !r)}>
              <p className="flashcard-eyebrow">{current.conceptTitle}</p>
              <p className="flashcard-face">{revealed ? current.back : current.front}</p>
              {!revealed && <p className="flashcard-hint">Tap to reveal the answer</p>}
            </div>

            {revealed ? (
              <div className="grade-buttons">
                {GRADES.map((g) => (
                  <button
                    key={g.label}
                    className={`btn ${g.tone}`}
                    onClick={() => grade(g.quality)}
                    disabled={busy}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            ) : (
              <button className="btn btn-send review-reveal" onClick={() => setRevealed(true)}>
                Show answer
              </button>
            )}
          </>
        )}

        {cards && !current && cards.length > 0 && (
          <p className="ingest-success">
            Reviewed all {cards.length} due cards. Mastery updated as you went.
          </p>
        )}
      </div>
    </div>
  );
}
