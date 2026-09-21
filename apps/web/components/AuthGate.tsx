"use client";

import { useState } from "react";

import { startAccount } from "@/lib/api";
import type { Account } from "@/lib/api";

const LEVELS = [
  { value: "primary", label: "Primary school" },
  { value: "secondary", label: "Secondary school" },
  { value: "high_school", label: "High school" },
  { value: "undergraduate", label: "Undergraduate" },
  { value: "postgraduate", label: "Postgraduate" },
];

/** Minimal account creation — see apps/api/routers/auth.py for what this is
 *  a stand-in for (Clerk) and why. */
export default function AuthGate({ onReady }: { onReady: (account: Account) => void }) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState("high_school");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const displayName = name.trim();
    if (!displayName || busy) return;
    setBusy(true);
    setError(null);
    try {
      const account = await startAccount(displayName, level);
      try {
        localStorage.setItem("orrery.sessionToken", account.sessionToken);
        localStorage.setItem("orrery.displayName", account.displayName);
      } catch {
        /* private window or blocked storage — the session still works, it
           just won't be remembered on reload */
      }
      onReady(account);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start your account.");
      setBusy(false);
    }
  }

  return (
    <main className="gate">
      <div className="gate-shell">
        <div className="gate-pitch">
          <div className="gate-mark" aria-hidden="true">
            <svg width="40" height="40" viewBox="0 0 44 44">
              <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#5aa9c7" strokeWidth="2" fill="none" />
              <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#4bd6b0" strokeWidth="2" fill="none" transform="rotate(60 22 22)" />
              <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#e0b341" strokeWidth="2" fill="none" transform="rotate(120 22 22)" />
              <circle cx="22" cy="22" r="5.5" fill="#e6eef5" />
            </svg>
            <span>Orrery</span>
          </div>
          <h1>Learn what you're ready for, not what's next on a list.</h1>
          <p className="gate-tagline">
            Orrery turns your notes, a PDF, or a lecture into a living 3D map
            of concepts. Real mastery tracking decides what unlocks next —
            no fixed syllabus, no guessing what to review.
          </p>
          <ul className="gate-features">
            <li>
              <span className="gate-feature-dot d-mastered" />
              A Socratic tutor for every concept, tuned to your level
            </li>
            <li>
              <span className="gate-feature-dot d-learning" />
              Flashcards and quizzes that feed one real mastery score
            </li>
            <li>
              <span className="gate-feature-dot d-open" />
              Build a subject from pasted notes, a PDF, or a YouTube link
            </li>
          </ul>
        </div>

        <div className="gate-card">
          <p className="gate-eyebrow">Get started</p>
          <h2>What should the map call you?</h2>
          <p className="gate-sub">
            No password — this creates a learner profile so your mastery and
            conversations are saved on this device.
          </p>

          <label className="field">
            <span>Name</span>
            <input
              id="gate-name"
              autoFocus
              value={name}
              placeholder="Your name"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              disabled={busy}
            />
          </label>

          <label className="field">
            <span>Level</span>
            <select
              id="gate-level"
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              disabled={busy}
            >
              {LEVELS.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>

          {error && <p className="gate-error">{error}</p>}

          <button className="btn btn-send gate-submit" onClick={submit} disabled={busy || !name.trim()}>
            {busy ? "Starting…" : "Enter Orrery"}
          </button>
        </div>
      </div>
    </main>
  );
}
