import json
import re

from openai import AsyncOpenAI

from config import settings
from services.ai.prompts import (
    CHECK_ANSWER_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
    EXAMINER_SYSTEM_PROMPT,
    GENERATE_PLAN_PROMPT,
    GENERATE_WORDS_PROMPT,
    LESSON_SYSTEM_PROMPT,
    TEACHER_SYSTEM_PROMPT,
)


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


async def run_assessment_step(conversation_history: list[dict]) -> str:
    return await _chat(EXAMINER_SYSTEM_PROMPT, conversation_history, temperature=0.3)


def parse_assessment_result(text: str) -> dict | None:
    level_match = re.search(r"RESULT:LEVEL:(\w+)", text)
    if not level_match:
        return None

    grammar = re.search(r"GRAMMAR_SCORE:([\d.]+)", text)
    vocab = re.search(r"VOCABULARY_SCORE:([\d.]+)", text)
    reading = re.search(r"READING_SCORE:([\d.]+)", text)
    strengths = re.search(r"STRENGTHS:(.+)", text)
    weaknesses = re.search(r"WEAKNESSES:(.+)", text)

    return {
        "level": level_match.group(1),
        "grammar_score": float(grammar.group(1)) if grammar else 0.0,
        "vocabulary_score": float(vocab.group(1)) if vocab else 0.0,
        "reading_score": float(reading.group(1)) if reading else 0.0,
        "strengths": strengths.group(1).strip() if strengths else "",
        "weaknesses": weaknesses.group(1).strip() if weaknesses else "",
    }


async def generate_lesson(level: str, goal: str, topic: str, weaknesses: str = "") -> str:
    system = LESSON_SYSTEM_PROMPT.format(
        level=level, goal=goal, topic=topic, weaknesses=weaknesses
    )
    return await _chat(system, [{"role": "user", "content": f"Проведи урок на тему: {topic}"}])


async def conversation_respond(level: str, history: list[dict]) -> str:
    system = CONVERSATION_SYSTEM_PROMPT.format(level=level)
    return await _chat(system, history)


async def check_answer(exercise: str, answer: str, correct_answer: str = "") -> dict:
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
    explanation = re.sub(r"SCORE:[\d.]+\n?", "", explanation).strip()

    return {
        "correct": correct_match and correct_match.group(1).lower() == "true",
        "score": float(score_match.group(1)) if score_match else 0.5,
        "explanation": explanation,
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
