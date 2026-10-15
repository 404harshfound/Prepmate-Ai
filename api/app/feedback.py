"""LLM-powered STAR feedback for interview answers.

Primary: Groq (fast inference on open models).
Fallback: Google Gemini Flash (if Groq fails or is not configured).

Both return structured JSON matching FeedbackResult. The caller never
needs to know which provider answered.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("prepmate.feedback")

FEEDBACK_TIMEOUT = 30.0  # seconds; Groq is usually <5s

# ------------------------------------------------------------------ prompt

SYSTEM_PROMPT = """\
You are an expert interview coach for Indian placement interviews (campus and
off-campus). The candidate has answered an interview question. Your job:

1. Score the answer on four dimensions, each 1-10:
   - **structure**: Does it follow a clear format (STAR for behavioural/HR,
     step-by-step for technical, systematic for aptitude)?
   - **relevance**: Does it actually answer the question asked?
   - **clarity**: Is the language precise, concise, and jargon-free where
     appropriate?
   - **depth**: Does it show genuine understanding, concrete examples, or
     correct reasoning?

2. Give a one-paragraph overall assessment (2-4 sentences).

3. List 1-3 specific, actionable improvements. Each improvement must quote
   the exact weak phrase or gap and suggest a concrete replacement or addition.

Respond ONLY with valid JSON matching this schema — no markdown, no preamble:
{
  "scores": {
    "structure": <int 1-10>,
    "relevance": <int 1-10>,
    "clarity": <int 1-10>,
    "depth": <int 1-10>
  },
  "overall": "<string>",
  "improvements": [
    {
      "issue": "<what is weak>",
      "suggestion": "<how to fix it>"
    }
  ]
}
"""


def _user_prompt(question: str, answer: str, round_type: str) -> str:
    return (
        f"Round type: {round_type}\n\n"
        f"**Question:** {question}\n\n"
        f"**Candidate's answer:**\n{answer}"
    )


# ------------------------------------------------------------------ result

@dataclass(frozen=True, slots=True)
class ScoreSet:
    structure: int
    relevance: int
    clarity: int
    depth: int

    @property
    def overall_score(self) -> float:
        return (self.structure + self.relevance + self.clarity + self.depth) / 4


@dataclass(frozen=True, slots=True)
class Improvement:
    issue: str
    suggestion: str


@dataclass(frozen=True, slots=True)
class FeedbackResult:
    scores: ScoreSet
    overall: str
    improvements: list[Improvement]
    model: str

    def scores_dict(self) -> dict[str, Any]:
        return {
            "structure": self.scores.structure,
            "relevance": self.scores.relevance,
            "clarity": self.scores.clarity,
            "depth": self.scores.depth,
            "overall": round(self.scores.overall_score, 1),
        }

    def feedback_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "improvements": [
                {"issue": imp.issue, "suggestion": imp.suggestion}
                for imp in self.improvements
            ],
        }


def _parse_response(text: str, model: str) -> FeedbackResult:
    """Parse the JSON from the LLM, raising ValueError on bad structure."""
    # Strip markdown fences if the model wrapped it
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ``` and closing ```
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    data = json.loads(cleaned)
    scores_raw = data["scores"]
    scores = ScoreSet(
        structure=_clamp_score(scores_raw["structure"]),
        relevance=_clamp_score(scores_raw["relevance"]),
        clarity=_clamp_score(scores_raw["clarity"]),
        depth=_clamp_score(scores_raw["depth"]),
    )
    improvements = [
        Improvement(issue=str(imp["issue"]), suggestion=str(imp["suggestion"]))
        for imp in data.get("improvements", [])[:3]
    ]
    return FeedbackResult(
        scores=scores,
        overall=str(data["overall"]),
        improvements=improvements,
        model=model,
    )


def _clamp_score(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 5  # default if the model returns garbage
    return max(1, min(10, n))


# ------------------------------------------------------------------ providers


class FeedbackError(Exception):
    """Raised when both providers fail to produce feedback."""


async def _call_groq(
    api_key: str,
    model: str,
    question: str,
    answer: str,
    round_type: str,
) -> FeedbackResult:
    """Call Groq's OpenAI-compatible chat endpoint."""
    async with httpx.AsyncClient(timeout=FEEDBACK_TIMEOUT) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _user_prompt(question, answer, round_type)},
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return _parse_response(text, model=f"groq/{model}")


async def _call_gemini(
    api_key: str,
    model: str,
    question: str,
    answer: str,
    round_type: str,
) -> FeedbackResult:
    """Call Google Gemini's generateContent endpoint."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=FEEDBACK_TIMEOUT) as client:
        response = await client.post(
            url,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    SYSTEM_PROMPT
                                    + "\n\n"
                                    + _user_prompt(question, answer, round_type)
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_response(text, model=f"gemini/{model}")


async def get_feedback(
    *,
    question: str,
    answer: str,
    round_type: str,
    groq_api_key: str | None,
    groq_model: str,
    gemini_api_key: str | None,
    gemini_model: str,
) -> FeedbackResult:
    """Get STAR feedback, trying Groq first, falling back to Gemini."""
    errors: list[str] = []

    if groq_api_key:
        try:
            return await _call_groq(groq_api_key, groq_model, question, answer, round_type)
        except Exception as exc:
            logger.warning("Groq feedback failed: %s", exc)
            errors.append(f"Groq: {exc}")

    if gemini_api_key:
        try:
            return await _call_gemini(gemini_api_key, gemini_model, question, answer, round_type)
        except Exception as exc:
            logger.warning("Gemini feedback failed: %s", exc)
            errors.append(f"Gemini: {exc}")

    if not groq_api_key and not gemini_api_key:
        raise FeedbackError("No LLM API key is configured. Set GROQ_API_KEY or GEMINI_API_KEY.")
    raise FeedbackError(f"All LLM providers failed: {'; '.join(errors)}")
