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

  const overallPct =
    subjects && subjects.length > 0
      ? Math.round(
          (subjects.reduce((sum, s) => sum + s.mastered, 0) /
            Math.max(1, subjects.reduce((sum, s) => sum + s.conceptCount, 0))) *
            100
        )
      : 0;

  return (
    <main className="dashboard">
      <nav className="topbar">
        <div className="topbar-brand">
          <svg width="22" height="22" viewBox="0 0 44 44" aria-hidden="true">
            <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#5aa9c7" strokeWidth="2.4" fill="none" />
            <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#4bd6b0" strokeWidth="2.4" fill="none" transform="rotate(60 22 22)" />
            <ellipse cx="22" cy="22" rx="20" ry="9" stroke="#e0b341" strokeWidth="2.4" fill="none" transform="rotate(120 22 22)" />
            <circle cx="22" cy="22" r="5.5" fill="#e6eef5" />
          </svg>
          <span>Orrery</span>
        </div>
        <button className="btn" onClick={onSwitchUser}>
          {displayName} · Switch user
        </button>
      </nav>

      <header className="dashboard-head">
        <div>
          <p className="hud-eyebrow">Welcome back</p>
          <h1>Your subjects</h1>
          {subjects && subjects.length > 0 && (
            <p className="dashboard-summary">
              <strong>{overallPct}%</strong> average mastery across {subjects.length}{" "}
              subject{subjects.length === 1 ? "" : "s"}
            </p>
          )}
        </div>
        <button className="btn btn-add" onClick={onNewSubject}>
          + New subject
        </button>
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
