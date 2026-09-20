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
