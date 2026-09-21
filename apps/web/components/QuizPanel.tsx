"use client";

import { useEffect, useState } from "react";

import { generateQuiz, submitQuiz } from "@/lib/api";
import type { GeneratedQuiz, QuizResult } from "@/lib/api";

export default function QuizPanel({
  conceptId,
  conceptTitle,
  onClose,
  onMasteryChange,
}: {
  conceptId: string;
  conceptTitle: string;
  onClose: () => void;
  onMasteryChange: (conceptId: string, mastery: number) => void;
}) {
  const [quiz, setQuiz] = useState<GeneratedQuiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setQuiz(null);
    setResult(null);
    setAnswers({});
    setError(null);
    generateQuiz(conceptId)
      .then((q) => !cancelled && setQuiz(q))
      .catch(
        (e) => !cancelled && setError(e instanceof Error ? e.message : "Could not build a quiz.")
      );
    return () => {
      cancelled = true;
    };
  }, [conceptId, attempt]);

  const answered = quiz ? quiz.questions.filter((q) => answers[q.id]?.trim()).length : 0;

  async function submit() {
    if (!quiz || busy) return;
    setBusy(true);
    try {
      const outcome = await submitQuiz(quiz.quizId, answers);
      setResult(outcome);
      if (outcome.mastery !== null) onMasteryChange(conceptId, outcome.mastery);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not mark that quiz.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal review-modal" onClick={(e) => e.stopPropagation()}>
        <header className="panel-head">
          <div>
            <p className="panel-eyebrow">Quiz · {conceptTitle}</p>
            <h2>{result ? `${result.correct} of ${result.total} correct` : "Test yourself"}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {error && <p className="chat-error">{error}</p>}
        {!quiz && !error && <p className="chat-empty">Writing your questions…</p>}

        {quiz && !result && (
          <>
            <p className="review-progress">
              {answered} of {quiz.questions.length} answered
            </p>

            {quiz.questions.map((q, i) => (
              <div key={q.id} className="quiz-question">
                <p className="quiz-prompt">
                  {i + 1}. {q.prompt}
                </p>

                {q.type === "mcq" && q.options ? (
                  <div className="quiz-options">
                    {q.options.map((opt) => (
                      <label
                        key={opt}
                        className={`quiz-option ${answers[q.id] === opt ? "is-picked" : ""}`}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          value={opt}
                          checked={answers[q.id] === opt}
                          onChange={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                        />
                        <span>{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <input
                    className="quiz-input"
                    placeholder="Your answer"
                    value={answers[q.id] ?? ""}
                    onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                  />
                )}
              </div>
            ))}

            <button
              className="btn btn-send review-reveal"
              onClick={submit}
              disabled={busy || answered === 0}
            >
              {busy ? "Marking…" : "Submit answers"}
            </button>
          </>
        )}

        {result && (
          <>
            <p className="review-progress">
              Scored {Math.round(result.score * 100)}%
              {result.mastery !== null &&
                ` · mastery now ${Math.round(result.mastery * 100)}%`}
            </p>

            {result.results.map((r, i) => (
              <div key={r.id} className={`quiz-result ${r.correct ? "is-right" : "is-wrong"}`}>
                <p className="quiz-prompt">
                  {i + 1}. {r.prompt}
                </p>
                <p className="quiz-given">
                  You said: {r.given.trim() ? r.given : <em>nothing</em>}
                </p>
                {!r.correct && <p className="quiz-answer">Answer: {r.answer}</p>}
                {r.explanation && <p className="quiz-explanation">{r.explanation}</p>}
              </div>
            ))}

            <button className="btn btn-send review-reveal" onClick={() => setAttempt((a) => a + 1)}>
              Try a new quiz
            </button>
          </>
        )}
      </div>
    </div>
  );
}
