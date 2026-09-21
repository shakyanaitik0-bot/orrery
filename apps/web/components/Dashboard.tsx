"use client";

import { useEffect, useState } from "react";

import { fetchDashboard } from "@/lib/api";
import type { DashboardSubject } from "@/lib/api";

export default function Dashboard({
  displayName,
  onOpenSubject,
  onNewSubject,
  onSwitchUser,
}: {
  displayName: string;
  onOpenSubject: (slug: string) => void;
  onNewSubject: () => void;
  onSwitchUser: () => void;
}) {
  const [subjects, setSubjects] = useState<DashboardSubject[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard()
      .then((d) => setSubjects(d.subjects))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load your progress."));
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard-head">
        <div>
          <p className="hud-eyebrow">Orrery · {displayName}</p>
          <h1>Your subjects</h1>
        </div>
        <div className="dashboard-head-actions">
          <button className="btn btn-add" onClick={onNewSubject}>
            + New subject
          </button>
          <button className="btn" onClick={onSwitchUser}>
            Switch user
          </button>
        </div>
      </header>

      {error && <p className="chat-error">{error}</p>}
      {!subjects && !error && <p className="chat-empty">Loading your progress…</p>}

      {subjects && subjects.length === 0 && (
        <p className="chat-empty">No subjects yet — add one to get started.</p>
      )}

      <div className="subject-grid">
        {subjects?.map((s) => {
          const pct = s.conceptCount > 0 ? Math.round((s.mastered / s.conceptCount) * 100) : 0;
          return (
            <button
              key={s.slug}
              className="subject-card"
              style={{ borderColor: s.accent }}
              onClick={() => onOpenSubject(s.slug)}
            >
              <div className="subject-card-head">
                <h2>{s.title}</h2>
                <span className="subject-card-pct" style={{ color: s.accent }}>
                  {pct}%
                </span>
              </div>
              {s.description && <p className="subject-card-desc">{s.description}</p>}
              <div className="subject-card-track">
                <div
                  className="subject-card-fill"
                  style={{ width: `${pct}%`, background: s.accent }}
                />
              </div>
              <dl className="subject-card-counts">
                <div>
                  <dt>Mastered</dt>
                  <dd className="c-mastered">{s.mastered}</dd>
                </div>
                <div>
                  <dt>Open</dt>
                  <dd className="c-open">{s.open}</dd>
                </div>
                <div>
                  <dt>Locked</dt>
                  <dd className="c-locked">{s.locked}</dd>
                </div>
              </dl>
            </button>
          );
        })}
      </div>
    </main>
  );
}
