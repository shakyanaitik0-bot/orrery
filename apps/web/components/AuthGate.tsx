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
        localStorage.setItem("orrery.userId", account.userId);
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
      <div className="gate-card">
        <p className="gate-eyebrow">Orrery</p>
        <h1>What should the map call you?</h1>
        <p className="gate-sub">
          No password — this creates a learner profile so your mastery and
          conversations are saved.
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
          {busy ? "Starting…" : "Enter the map"}
        </button>
      </div>
    </main>
  );
}
