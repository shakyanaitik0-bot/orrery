"use client";

import { useState } from "react";

import { ingestNotes } from "@/lib/api";

export default function IngestPanel({
  onCreated,
  onClose,
}: {
  onCreated: (slug: string) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ concepts: number; edges: number } | null>(null);

  async function submit() {
    if (text.trim().length < 40 || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await ingestNotes(text.trim(), title.trim() || undefined);
      setResult({ concepts: res.conceptCount, edges: res.edgeCount });
      setTimeout(() => onCreated(res.subject.slug), 900);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not build a subject from that.");
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="panel-head">
          <div>
            <p className="panel-eyebrow">New subject</p>
            <h2>Build a map from notes</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <p className="panel-summary">
          Paste lecture notes, a chapter, or a transcript. It becomes a concept
          graph you can navigate like the demo map.
        </p>

        <label className="field">
          <span>Title (optional)</span>
          <input
            id="ingest-title"
            value={title}
            placeholder="Leave blank to let it name itself"
            onChange={(e) => setTitle(e.target.value)}
            disabled={busy}
          />
        </label>

        <label className="field field-grow">
          <span>Material</span>
          <textarea
            id="ingest-text"
            value={text}
            placeholder="Paste your notes here…"
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
            rows={10}
          />
        </label>

        {error && <p className="chat-error">{error}</p>}
        {result && (
          <p className="ingest-success">
            Built {result.concepts} concepts and {result.edges} connections. Opening the
            map…
          </p>
        )}

        <div className="modal-actions">
          <button className="btn" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="btn btn-send"
            onClick={submit}
            disabled={busy || text.trim().length < 40}
          >
            {busy ? "Building the graph…" : "Build the map"}
          </button>
        </div>
      </div>
    </div>
  );
}
