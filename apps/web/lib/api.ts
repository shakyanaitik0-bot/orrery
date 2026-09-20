import type { AnswerResult, Scene } from "./types";

export async function fetchScene(subject: string, userId: string): Promise<Scene> {
  const res = await fetch(`/api/graph/scene/${subject}?user_id=${userId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Could not load the map (${res.status})`);
  return res.json();
}

export async function submitAnswer(
  userId: string,
  conceptId: string,
  correct: boolean
): Promise<AnswerResult> {
  const res = await fetch("/api/graph/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, concept_id: conceptId, correct }),
  });
  if (!res.ok) throw new Error(`Could not record that answer (${res.status})`);
  return res.json();
}

export async function fetchProvider(): Promise<{ provider: string; model: string | null }> {
  const res = await fetch("/api/tutor/provider", { cache: "no-store" });
  if (!res.ok) return { provider: "unknown", model: null };
  return res.json();
}

/** Streams the tutor's reply, calling `onChunk` as text arrives. */
export async function askTutor(
  userId: string,
  conceptId: string,
  message: string,
  onChunk: (text: string) => void
): Promise<void> {
  const res = await fetch("/api/tutor/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, concept_id: conceptId, message }),
  });
  if (!res.ok || !res.body) throw new Error(`The tutor did not respond (${res.status})`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value, { stream: true }));
  }
}


export interface Account {
  userId: string;
  tenantId: string;
  displayName: string;
}

export async function startAccount(
  displayName: string,
  educationLevel: string = "high_school"
): Promise<Account> {
  const res = await fetch("/api/auth/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName, education_level: educationLevel }),
  });
  if (!res.ok) throw new Error(`Could not create an account (${res.status})`);
  return res.json();
}

export async function restoreAccount(userId: string): Promise<Account | null> {
  const res = await fetch(`/api/auth/me/${userId}`, { cache: "no-store" });
  if (!res.ok) return null;
  const data = await res.json();
  return { userId: data.userId, tenantId: data.tenantId, displayName: data.displayName };
}

export interface IngestResult {
  subject: { slug: string; title: string };
  conceptCount: number;
  edgeCount: number;
  provider: string;
}

/** Turns pasted notes into a new subject and its concept graph. */
export async function ingestNotes(text: string, title?: string): Promise<IngestResult> {
  const res = await fetch("/api/ingest/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, title }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not build a subject from that (${res.status})`);
  }
  return res.json();
}

export async function listSubjects(): Promise<
  { id: string; slug: string; title: string; description: string | null; accent: string }[]
> {
  const res = await fetch("/api/graph/subjects", { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}


export interface ReviewCard {
  id: string;
  conceptId: string;
  conceptTitle: string;
  front: string;
  back: string;
}

export async function fetchDueCards(userId: string, subjectSlug: string): Promise<ReviewCard[]> {
  const res = await fetch(`/api/review/due/${userId}/${subjectSlug}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Could not load the review queue (${res.status})`);
  const data = await res.json();
  return data.cards;
}

export interface GradeResult {
  cardId: string;
  nextDueAt: string | null;
  intervalDays: number;
  mastery: number;
}

export async function gradeCard(
  userId: string,
  cardId: string,
  quality: number
): Promise<GradeResult> {
  const res = await fetch("/api/review/grade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, card_id: cardId, quality }),
  });
  if (!res.ok) throw new Error(`Could not record that review (${res.status})`);
  return res.json();
}

export async function ingestPdf(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/ingest/pdf", { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not read that PDF (${res.status})`);
  }
  return res.json();
}
