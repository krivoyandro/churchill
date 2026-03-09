import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import lesson_topic_keyboard, main_menu_keyboard
from bot.states.states import LessonStates
from db.models import User
from db.repo import (
    save_user_lesson,
    complete_user_lesson,
    save_mistake,
    get_user_weaknesses,
    increment_streak,
)
from services.ai.engine import generate_lesson, check_answer

logger = logging.getLogger(__name__)

router = Router()

TOPIC_TITLES = {
    "alphabet_and_sounds": "Алфавит и звуки",
    "greetings": "Приветствия",
    "numbers": "Числа",
    "colors": "Цвета",
    "basic_phrases": "Простые фразы",
    "present_simple": "Present Simple",
    "to_be": "Глагол to be",
    "articles": "Артикли a/an/the",
    "prepositions_place": "Предлоги места",
    "food_and_drinks": "Еда и напитки",
    "past_simple": "Past Simple",
    "present_continuous": "Present Continuous",
    "modal_verbs": "Модальные глаголы",
    "comparatives": "Сравнительные степени",
    "travel": "Путешествия",
    "present_perfect": "Present Perfect",
    "future_forms": "Future forms",
    "conditionals": "Условные предложения",
    "reported_speech": "Reported Speech",
    "work_career": "Работа и карьера",
    "passive_voice": "Passive Voice",
    "advanced_conditionals": "Advanced Conditionals",
    "gerund_infinitive": "Gerund vs Infinitive",
    "phrasal_verbs": "Фразовые глаголы",
    "business_english": "Бизнес-английский",
    "inversion": "Inversion",
    "cleft_sentences": "Cleft sentences",
    "advanced_idioms": "Advanced idioms",
    "academic_writing": "Academic Writing",
    "debate": "Debate & Argumentation",
}

MAX_ANSWERS_PER_LESSON = 5


@router.message(F.text == "📚 Начать урок")
async def start_lesson_menu(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.current_level:
        await message.answer("Сначала пройди тест уровня! Нажми /start")
        return

    level = user.current_level.value
    await message.answer(
        f"📚 Выбери тему урока (уровень {level}):",
        reply_markup=lesson_topic_keyboard(level),
    )


@router.callback_query(F.data.startswith("lesson:"))
async def on_lesson_topic_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    topic_key = callback.data.split(":")[1]
    topic_title = TOPIC_TITLES.get(topic_key, topic_key)

    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Ошибка. Нажми /start")
        return

    level = user.current_level.value if user.current_level else "A1"
    goal = user.goal.value if user.goal else "conversational"

    await callback.message.edit_text(f"⏳ Готовлю урок: {topic_title}...")

    # Fetch weaknesses to personalize lesson
    weaknesses = await get_user_weaknesses(session, user.id)
    weaknesses_str = ", ".join(weaknesses) if weaknesses else "пока не определены"

    lesson_content = await generate_lesson(level, goal, topic_title, weaknesses=weaknesses_str)

    user_lesson = await save_user_lesson(session, user.id, topic_title, lesson_content)
    await state.set_state(LessonStates.in_lesson)
    await state.update_data(
        lesson_id=user_lesson.id,
        lesson_topic=topic_title,
        lesson_content=lesson_content,
        user_id=user.id,
        answer_count=0,
        total_score=0.0,
    )

    # Split long messages (Telegram limit 4096 chars)
    if len(lesson_content) > 4000:
        parts = [lesson_content[i:i + 4000] for i in range(0, len(lesson_content), 4000)]
        for part in parts[:-1]:
            await callback.message.answer(part)
        await callback.message.answer(
            parts[-1] + "\n\n✍️ Напиши свой ответ на упражнения или отправь /menu для возврата."
        )
    else:
        await callback.message.answer(
            lesson_content + "\n\n✍️ Напиши свой ответ на упражнения или отправь /menu для возврата."
        )
    await callback.answer()


async def _finish_lesson(message: Message, state: FSMContext, session: AsyncSession):
    """Complete the lesson, save score, update streak."""
    data = await state.get_data()
    answer_count = data.get("answer_count", 0)
    total_score = data.get("total_score", 0.0)
    avg_score = total_score / answer_count if answer_count > 0 else None

    await complete_user_lesson(session, data["lesson_id"], score=avg_score)
    await increment_streak(session, data["user_id"])

    summary = "📝 Урок завершён!\n"
    if answer_count > 0:
        summary += f"Ответов: {answer_count} | Средний балл: {avg_score:.0%}\n"
    summary += "\nВозвращаюсь в меню."
    await state.clear()
    await message.answer(summary, reply_markup=main_menu_keyboard())


@router.message(LessonStates.in_lesson)
async def process_lesson_answer(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.startswith("/menu"):
        await _finish_lesson(message, state, session)
        return

    data = await state.get_data()
    topic = data.get("lesson_topic", "")
    lesson_content = data.get("lesson_content", "")

    # Provide lesson context so AI knows what exercises were given
    exercise_context = f"Тема урока: {topic}\n\nМатериал урока:\n{lesson_content[:2000]}"

    result = await check_answer(
        exercise=exercise_context,
        answer=message.text,
    )

    # Save mistakes to DB
    for m in result.get("mistakes", []):
        await save_mistake(
            session,
            user_id=data["user_id"],
            category=m.get("category", "other"),
            original=m.get("original", ""),
            corrected=m.get("corrected", ""),
            explanation=m.get("explanation", ""),
        )

    # Track score
    answer_count = data.get("answer_count", 0) + 1
    total_score = data.get("total_score", 0.0) + result["score"]
    await state.update_data(answer_count=answer_count, total_score=total_score)

    emoji = "✅" if result["correct"] else "❌"
    response = f"{emoji} Оценка: {result['score']:.0%}\n\n{result['explanation']}"

    if answer_count >= MAX_ANSWERS_PER_LESSON:
        await message.answer(response)
        await _finish_lesson(message, state, session)
    else:
        remaining = MAX_ANSWERS_PER_LESSON - answer_count
        await message.answer(
            f"{response}\n\n"
            f"Ответ {answer_count}/{MAX_ANSWERS_PER_LESSON}. "
            f"Отправь следующий ответ или /menu для выхода."
        )
