import type { AnswerResult, Scene } from "./types";

// The session token is the actual proof of identity now — a bearer token
// issued by /api/auth/start, not the user id (which is not a secret and
// would let anyone reach another learner's data if the API trusted it).
let sessionToken: string | null = null;

export function setSessionToken(token: string | null) {
  sessionToken = token;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (sessionToken) headers["Authorization"] = `Bearer ${sessionToken}`;
  return headers;
}

export async function fetchScene(subject: string): Promise<Scene> {
  const res = await fetch(`/api/graph/scene/${subject}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Could not load the map (${res.status})`);
  return res.json();
}

export async function submitAnswer(
  conceptId: string,
  correct: boolean
): Promise<AnswerResult> {
  const res = await fetch("/api/graph/answer", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ concept_id: conceptId, correct }),
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
  conceptId: string,
  message: string,
  onChunk: (text: string) => void
): Promise<void> {
  const res = await fetch("/api/tutor/ask", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ concept_id: conceptId, message }),
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

export async function fetchTutorHistory(
  conceptId: string
): Promise<{ role: string; content: string }[]> {
  const res = await fetch(`/api/tutor/history/${conceptId}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) return [];
  return res.json();
}

export interface Account {
  userId: string;
  tenantId: string;
  displayName: string;
  sessionToken: string;
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
  const data = await res.json();
  setSessionToken(data.sessionToken);
  return data;
}

/** Clears the stored session so another learner can sign in on this device. */
export function clearStoredAccount() {
  setSessionToken(null);
  try {
    localStorage.removeItem("orrery.sessionToken");
    localStorage.removeItem("orrery.displayName");
  } catch {
    /* private window or blocked storage */
  }
}

/** Restores a session from a stored bearer token — called on page load. */
export async function restoreAccount(token: string): Promise<Account | null> {
  setSessionToken(token);
  const res = await fetch("/api/auth/me", { cache: "no-store", headers: authHeaders() });
  if (!res.ok) {
    setSessionToken(null);
    return null;
  }
  const data = await res.json();
  return {
    userId: data.userId,
    tenantId: data.tenantId,
    displayName: data.displayName,
    sessionToken: token,
  };
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
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ text, title }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not build a subject from that (${res.status})`);
  }
  return res.json();
}

export interface DashboardSubject {
  slug: string;
  title: string;
  description: string | null;
  accent: string;
  conceptCount: number;
  mastered: number;
  open: number;
  locked: number;
  averageMastery: number;
}

export async function fetchDashboard(): Promise<{
  subjects: DashboardSubject[];
  masteryThreshold: number;
}> {
  const res = await fetch("/api/graph/dashboard", {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Could not load your progress (${res.status})`);
  return res.json();
}

export async function listSubjects(): Promise<
  { id: string; slug: string; title: string; description: string | null; accent: string }[]
> {
  const res = await fetch("/api/graph/subjects", { cache: "no-store", headers: authHeaders() });
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

export async function fetchDueCards(subjectSlug: string): Promise<ReviewCard[]> {
  const res = await fetch(`/api/review/due/${subjectSlug}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
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

/** Downloads the learner's deck for a subject as an Anki-importable CSV. */
export async function exportDeckCsv(subjectSlug: string): Promise<void> {
  const res = await fetch(`/api/review/export/${subjectSlug}.csv`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Could not export the deck (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${subjectSlug}-deck.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function gradeCard(cardId: string, quality: number): Promise<GradeResult> {
  const res = await fetch("/api/review/grade", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ card_id: cardId, quality }),
  });
  if (!res.ok) throw new Error(`Could not record that review (${res.status})`);
  return res.json();
}

export interface QuizQuestion {
  id: string;
  type: "mcq" | "short";
  prompt: string;
  options: string[] | null;
}

export interface GeneratedQuiz {
  quizId: string;
  conceptTitle: string;
  questions: QuizQuestion[];
}

export interface QuizResult {
  score: number;
  correct: number;
  total: number;
  mastery: number | null;
  results: {
    id: string;
    prompt: string;
    given: string;
    correct: boolean;
    answer: string;
    explanation: string;
  }[];
}

export async function generateQuiz(conceptId: string): Promise<GeneratedQuiz> {
  const res = await fetch("/api/quiz/generate", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ concept_id: conceptId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not build a quiz (${res.status})`);
  }
  return res.json();
}

export async function submitQuiz(
  quizId: string,
  answers: Record<string, string>
): Promise<QuizResult> {
  const res = await fetch("/api/quiz/submit", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ quiz_id: quizId, answers }),
  });
  if (!res.ok) throw new Error(`Could not mark that quiz (${res.status})`);
  return res.json();
}

export async function ingestPdf(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/ingest/pdf", { method: "POST", headers: authHeaders(), body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not read that PDF (${res.status})`);
  }
  return res.json();
}

export async function ingestYoutube(url: string, title?: string): Promise<IngestResult> {
  const res = await fetch("/api/ingest/youtube", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ url, title }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Could not read that video (${res.status})`);
  }
  return res.json();
}
