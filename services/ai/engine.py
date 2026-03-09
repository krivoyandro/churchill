import json
import logging
import re

from openai import AsyncOpenAI

from config import settings
from services.ai.prompts import (
    CHECK_ANSWER_PROMPT,
    CHECK_FREE_ANSWER_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
    GENERATE_PLAN_PROMPT,
    GENERATE_WORDS_PROMPT,
    LESSON_SYSTEM_PROMPT,
    TEACHER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


client = AsyncOpenAI(api_key=settings.openai_api_key)


async def _chat(system: str, messages: list[dict], temperature: float = 0.7) -> str:
    full_messages = [{"role": "system", "content": system}] + messages
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=full_messages,
        temperature=temperature,
        max_tokens=2000,
    )
    return response.choices[0].message.content


async def teacher_respond(user_message: str, context: str = "") -> str:
    system = TEACHER_SYSTEM_PROMPT
    if context:
        system += f"\n\nКонтекст об ученике:\n{context}"
    return await _chat(system, [{"role": "user", "content": user_message}])


async def check_free_answer(question: str, answer: str) -> bool:
    """Use AI to evaluate a free-form assessment answer. Returns True/False."""
    prompt = CHECK_FREE_ANSWER_PROMPT.format(question=question, answer=answer)
    try:
        result = await _chat(
            "Ты — экзаменатор.", [{"role": "user", "content": prompt}], temperature=0.1
        )
        return "CORRECT:true" in result.lower()
    except Exception as e:
        logger.warning("AI check_free_answer failed: %s", e)
        return False


async def generate_lesson(level: str, goal: str, topic: str, weaknesses: str = "") -> str:
    system = LESSON_SYSTEM_PROMPT.format(
        level=level, goal=goal, topic=topic, weaknesses=weaknesses
    )
    return await _chat(system, [{"role": "user", "content": f"Проведи урок на тему: {topic}"}])


async def conversation_respond(level: str, history: list[dict]) -> str:
    system = CONVERSATION_SYSTEM_PROMPT.format(level=level)
    return await _chat(system, history)


async def check_answer(exercise: str, answer: str, correct_answer: str = "") -> dict:
    """Check an exercise answer. Returns structured result with mistakes."""
    prompt = CHECK_ANSWER_PROMPT.format(
        exercise=exercise, answer=answer, correct_answer=correct_answer
    )
    result = await _chat(
        "Ты — проверяющий преподаватель.", [{"role": "user", "content": prompt}], temperature=0.3
    )
    correct_match = re.search(r"CORRECT:(true|false)", result, re.IGNORECASE)
    score_match = re.search(r"SCORE:([\d.]+)", result)

    # Remove control lines from explanation
    explanation = re.sub(r"CORRECT:(true|false)\n?", "", result, flags=re.IGNORECASE)
    explanation = re.sub(r"SCORE:[\d.]+\n?", "", explanation)
    explanation = re.sub(r"MISTAKES:.*", "", explanation, flags=re.DOTALL).strip()

    # Extract structured mistakes
    mistakes = []
    mistakes_section = re.search(r"MISTAKES:(.*)", result, re.DOTALL)
    if mistakes_section:
        for line in mistakes_section.group(1).strip().split("\n"):
            line = line.strip()
            if not line or line == "none":
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                mistakes.append({
                    "category": parts[0].strip(),
                    "original": parts[1].strip(),
                    "corrected": parts[2].strip(),
                    "explanation": parts[3].strip() if len(parts) > 3 else "",
                })

    return {
        "correct": correct_match and correct_match.group(1).lower() == "true",
        "score": float(score_match.group(1)) if score_match else 0.5,
        "explanation": explanation,
        "mistakes": mistakes,
    }


async def generate_words(level: str, topic: str, count: int = 5) -> list[dict]:
    prompt = GENERATE_WORDS_PROMPT.format(level=level, topic=topic, count=count)
    result = await _chat(
        "Ты — генератор учебного контента.", [{"role": "user", "content": prompt}], temperature=0.5
    )
    words = []
    for line in result.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove leading numbering like "1. " or "- "
        line = re.sub(r"^[\d]+\.\s*", "", line)
        line = re.sub(r"^-\s*", "", line)
        parts = line.split("|")
        if len(parts) >= 4:
            words.append({
                "word": parts[0].strip(),
                "translation": parts[1].strip(),
                "transcription": parts[2].strip(),
                "example": parts[3].strip(),
            })
    return words


async def generate_learning_plan(
    current_level: str, target_level: str, goal: str, daily_minutes: int
) -> str:
    prompt = GENERATE_PLAN_PROMPT.format(
        current_level=current_level,
        target_level=target_level,
        goal=goal,
        daily_minutes=daily_minutes,
    )
    return await _chat("Ты — методист по английскому языку.", [{"role": "user", "content": prompt}])
