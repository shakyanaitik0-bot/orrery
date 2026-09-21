"""Per-concept quizzes, graded server-side and folded into BKT mastery.

The generation prompt and the mixed multiple-choice/short-answer shape come
from TutorBot (MIT). What is new here is where the result goes: a quiz is
not a standalone score, it is another observation for the same Rust BKT
engine the tutor and the flashcard deck already write to. Answer four of
five correctly and the map lights up the same way it would after a review.

Grading a short answer without a second model call is deliberate. A quiz
should be gradeable offline and instantly, so the check is a normalised
containment test against the expected answer and any listed alternatives —
generous about case, punctuation and articles, strict about the actual
content word. Anything subtler than that belongs in the tutor chat, which
is where an argument about a borderline answer can actually be had.
"""

import json
import re
import uuid

from services.learning.mastery import record_answer
from services.llm.base import LLMClient

SYSTEM_PROMPT = """You write short diagnostic quizzes for a single concept.

Produce exactly 5 questions that test whether someone understands the
concept — not whether they memorised its wording. Mix multiple-choice and
short-answer: roughly 3 multiple-choice, 2 short-answer.

Respond with ONLY a JSON object, no prose, no code fence, in this shape:

{
  "questions": [
    {
      "type": "mcq",
      "prompt": "the question",
      "options": ["option A", "option B", "option C", "option D"],
      "answer": "the exact text of the correct option",
      "explanation": "one sentence on why"
    },
    {
      "type": "short",
      "prompt": "the question",
      "answer": "the expected answer, a word or short phrase",
      "accept": ["other acceptable phrasings"],
      "explanation": "one sentence on why"
    }
  ]
}

Rules:
- An "mcq" answer must be character-for-character one of its own options.
- A "short" answer must be answerable in under five words, so it can be
  marked without a human. Never ask for an explanation or a sentence.
- Exactly one option is correct; the wrong ones must be plausible.
- Do not number the questions."""


class QuizError(ValueError):
    """The model's output could not be parsed as a usable quiz."""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise QuizError("No JSON object found in the model's response.")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise QuizError(f"Model output was not valid JSON: {exc}") from exc


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation and leading articles, collapse spaces."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return re.sub(r"^(a|an|the)\s+", "", cleaned)


def is_correct(question: dict, given: str) -> bool:
    if not given or not given.strip():
        return False
    expected = _normalise(str(question.get("answer", "")))
    actual = _normalise(given)
    if not expected:
        return False

    if question.get("type") == "mcq":
        return actual == expected

    accepted = [expected] + [
        _normalise(str(a)) for a in question.get("accept", []) if str(a).strip()
    ]
    # A short answer counts if the learner's wording contains the expected
    # one or vice versa — "photosynthesis" matches "it is photosynthesis",
    # and a one-word expected answer isn't failed by a fuller sentence.
    return any(a and (a in actual or actual in a) for a in accepted)


async def generate(client: LLMClient, concept_title: str, concept_summary: str | None) -> list[dict]:
    """Ask the model for a quiz and return validated, id-tagged questions."""
    material = f"Concept: {concept_title}"
    if concept_summary:
        material += f"\nSummary: {concept_summary}"

    content, _usage = await client.extract(SYSTEM_PROMPT, material)
    data = _extract_json(content)

    raw = data.get("questions")
    if not isinstance(raw, list) or not raw:
        raise QuizError("Model did not return any questions.")

    questions = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("prompt") or not item.get("answer"):
            continue
        kind = "mcq" if item.get("type") == "mcq" else "short"
        options = item.get("options") if kind == "mcq" else None
        # An MCQ whose answer isn't among its own options can't be graded,
        # and the model does occasionally produce one. Drop it rather than
        # marking every learner wrong on it.
        if kind == "mcq":
            if not isinstance(options, list) or len(options) < 2:
                continue
            if not any(_normalise(str(o)) == _normalise(str(item["answer"])) for o in options):
                continue

        questions.append(
            {
                "id": str(uuid.uuid4()),
                "type": kind,
                "prompt": str(item["prompt"]),
                "options": [str(o) for o in options] if options else None,
                "answer": str(item["answer"]),
                "accept": [str(a) for a in item.get("accept", [])] if kind == "short" else [],
                "explanation": str(item.get("explanation", "")),
            }
        )

    if not questions:
        raise QuizError("None of the model's questions were usable.")
    return questions


def for_client(questions: list[dict]) -> list[dict]:
    """The same questions with every answer stripped out."""
    return [
        {
            "id": q["id"],
            "type": q["type"],
            "prompt": q["prompt"],
            "options": q["options"],
        }
        for q in questions
    ]


async def grade(session, quiz, answers: dict[str, str]) -> dict:
    """Mark an attempt, record one BKT observation per question, and return
    the per-question breakdown with explanations now revealed."""
    questions = quiz.questions["items"]
    results = []
    correct_count = 0

    for q in questions:
        given = answers.get(q["id"], "")
        correct = is_correct(q, given)
        correct_count += correct
        results.append(
            {
                "id": q["id"],
                "prompt": q["prompt"],
                "given": given,
                "correct": correct,
                "answer": q["answer"],
                "explanation": q["explanation"],
            }
        )

    # Every question is its own observation, so a five-question quiz moves
    # mastery about as much as five flashcards would — not five times more.
    mastery_row = None
    for r in results:
        mastery_row = await record_answer(session, quiz.user_id, quiz.concept_id, r["correct"])

    score = correct_count / len(questions) if questions else 0.0
    return {
        "score": round(score, 4),
        "correct": correct_count,
        "total": len(questions),
        "results": results,
        "mastery": round(mastery_row.probability, 4) if mastery_row else None,
    }
