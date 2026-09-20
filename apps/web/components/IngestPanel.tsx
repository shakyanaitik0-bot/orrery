"use client";

import { useRef, useState } from "react";

import { ingestNotes, ingestPdf } from "@/lib/api";

type Mode = "notes" | "pdf";

export default function IngestPanel({
  onCreated,
  onClose,
}: {
  onCreated: (slug: string) => void;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<Mode>("notes");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ concepts: number; edges: number } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const canSubmit = mode === "notes" ? text.trim().length >= 40 : file !== null;

  async function submit() {
    if (!canSubmit || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === "notes"
          ? await ingestNotes(text.trim(), title.trim() || undefined)
          : await ingestPdf(file as File);
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
            <h2>Build a map from your material</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <div className="mode-tabs">
          <button
            className={`mode-tab ${mode === "notes" ? "is-active" : ""}`}
            onClick={() => setMode("notes")}
            disabled={busy}
          >
            Paste notes
          </button>
          <button
            className={`mode-tab ${mode === "pdf" ? "is-active" : ""}`}
            onClick={() => setMode("pdf")}
            disabled={busy}
          >
            Upload PDF
          </button>
        </div>

        {mode === "notes" ? (
          <>
            <p className="panel-summary">
              Paste lecture notes, a chapter, or a transcript. It becomes a
              concept graph you can navigate like the demo map.
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
          </>
        ) : (
          <>
            <p className="panel-summary">
              Upload a PDF with a real text layer — lecture slides, a chapter, a
              handout. Scanned images without text can't be read yet.
            </p>
            <div
              className={`dropzone ${file ? "has-file" : ""}`}
              onClick={() => fileInput.current?.click()}
            >
              <input
                ref={fileInput}
                type="file"
                accept="application/pdf"
                hidden
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={busy}
              />
              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>{(file.size / 1024).toFixed(0)} KB · click to change</span>
                </>
              ) : (
                <>
                  <strong>Click to choose a PDF</strong>
                  <span>Up to 15 MB</span>
                </>
              )}
            </div>
          </>
        )}

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
          <button className="btn btn-send" onClick={submit} disabled={busy || !canSubmit}>
            {busy ? "Building the graph…" : "Build the map"}
          </button>
        </div>
      </div>
    </div>
  );
}
