import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_keyboard
from bot.states.states import OnboardingStates
from db.models import CEFRLevel
from db.repo import update_user_level, save_assessment, set_onboarding_complete
from services.learning.assessment_data import (
    ASSESSMENT_QUESTIONS,
    LEVEL_ORDER,
    get_question,
    total_questions,
    check_answer_deterministic,
    calculate_level,
)
from services.ai.engine import check_free_answer

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "assessment:start")
async def start_assessment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.assessment_in_progress)
    await state.update_data(
        q_index=0,
        scores_by_level={},
    )

    q = get_question(0)
    await callback.message.edit_text(
        f"📝 <b>Тест уровня</b> (1/{total_questions()})\n\n{q['text']}"
    )
    await callback.answer()


@router.callback_query(F.data == "assessment:skip")
async def skip_assessment(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_id = data["user_id"]

    await update_user_level(session, user_id, CEFRLevel.A0)
    await save_assessment(session, user_id, CEFRLevel.A0, score=0.0, details="Тест пропущен")
    await set_onboarding_complete(session, user_id)
    await state.clear()

    await callback.message.edit_text(
        "✅ Уровень установлен: A0 (начинающий)\n\n"
        "Ты можешь пройти тест позже в настройках.\n"
        "А пока — давай начнём учиться! 🚀"
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(OnboardingStates.assessment_in_progress)
async def process_assessment_answer(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_id = data["user_id"]
    q_index = data["q_index"]
    scores = data.get("scores_by_level", {})

    q = get_question(q_index)
    if not q:
        await _finish_assessment(message, state, session, user_id, scores)
        return

    level = q["level"]
    if level not in scores:
        scores[level] = {"correct": 0, "total": 0}
    scores[level]["total"] += 1

    # Check answer
    if q["answers"]:
        is_correct = check_answer_deterministic(q, message.text)
    else:
        is_correct = await check_free_answer(q["text"], message.text)

    if is_correct:
        scores[level]["correct"] += 1
        feedback = "✅ Верно!"
    else:
        if q["answers"]:
            feedback = f"❌ Неверно. Правильный ответ: <b>{q['answers'][0]}</b>"
        else:
            feedback = "❌ Не совсем."

    next_index = q_index + 1

    # Early stop: if user fails too many at current level, skip higher
    level_stats = scores.get(level, {"correct": 0, "total": 0})
    failed_at_level = level_stats["total"] - level_stats["correct"]
    questions_at_level = sum(1 for qn in ASSESSMENT_QUESTIONS if qn["level"] == level)

    should_stop_early = False
    if level_stats["total"] >= questions_at_level and failed_at_level >= 2 and level != "A0":
        should_stop_early = True

    if next_index >= total_questions() or should_stop_early:
        await message.answer(feedback)
        await _finish_assessment(message, state, session, user_id, scores)
        return

    next_q = get_question(next_index)
    if next_q and failed_at_level >= 2 and level != "A0":
        current_level_idx = LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 0
        next_q_level_idx = LEVEL_ORDER.index(next_q["level"]) if next_q["level"] in LEVEL_ORDER else 0
        if next_q_level_idx > current_level_idx:
            await message.answer(feedback)
            await _finish_assessment(message, state, session, user_id, scores)
            return

    await state.update_data(q_index=next_index, scores_by_level=scores)
    await message.answer(
        f"{feedback}\n\n"
        f"📝 Вопрос {next_index + 1}/{total_questions()}\n\n{next_q['text']}"
    )


async def _finish_assessment(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_id: int,
    scores: dict,
):
    """Calculate level and save results."""
    level_str, sub_scores = calculate_level(scores)
    level = CEFRLevel(level_str)

    await update_user_level(session, user_id, level)

    details = "; ".join(
        f"{lvl}: {s['correct']}/{s['total']}"
        for lvl in LEVEL_ORDER
        if (s := scores.get(lvl)) and s["total"] > 0
    )
    await save_assessment(
        session,
        user_id,
        level,
        score=sub_scores["overall_score"],
        grammar_score=sub_scores["grammar_score"],
        vocabulary_score=sub_scores["vocabulary_score"],
        reading_score=0.0,
        details=details,
    )
    await set_onboarding_complete(session, user_id)
    await state.clear()

    breakdown = ""
    for lvl in LEVEL_ORDER:
        s = scores.get(lvl)
        if s and s["total"] > 0:
            emoji = "✅" if s["correct"] >= 2 else "❌"
            breakdown += f"  {emoji} {lvl}: {s['correct']}/{s['total']}\n"

    weak = [
        lvl for lvl in LEVEL_ORDER
        if (s := scores.get(lvl)) and s["total"] > 0 and s["correct"] < s["total"]
    ]
    weaknesses_text = ", ".join(weak) if weak else "нет явных"

    await message.answer(
        f"📊 <b>Тест завершён!</b>\n\n"
        f"🎯 Твой уровень: <b>{level.value}</b>\n\n"
        f"Результаты по уровням:\n{breakdown}\n"
        f"📗 Грамматика: {sub_scores['grammar_score']:.0%}\n"
        f"📘 Словарный запас: {sub_scores['vocabulary_score']:.0%}\n\n"
        f"🔧 Над чем работать: {weaknesses_text}\n\n"
        f"Готов начать обучение! 🚀",
    )
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    logger.info("User %s assessed as %s", user_id, level.value)
