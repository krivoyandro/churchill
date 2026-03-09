import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_keyboard
from bot.states.states import DrillStates
from db.models import User
from db.repo import (
    get_mistakes_for_drill,
    get_user_weaknesses,
    increment_mistake_repeated,
    save_mistake,
)
from services.ai.engine import check_answer, generate_drill_exercise

logger = logging.getLogger(__name__)

router = Router()

MAX_DRILL_ROUNDS = 3


@router.message(F.text == "🔁 Работа над ошибками")
async def start_drill(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.current_level:
        await message.answer("Сначала пройди тест уровня! Нажми /start")
        return

    mistakes = await get_mistakes_for_drill(session, user.id, limit=5)
    if not mistakes:
        await message.answer(
            "🎉 У тебя пока нет ошибок для проработки! Пройди урок и возвращайся.",
            reply_markup=main_menu_keyboard(),
        )
        return

    level = user.current_level.value

    # Build summary of mistakes for AI
    mistakes_summary = ""
    mistake_ids = []
    for m in mistakes:
        mistakes_summary += (
            f"- [{m.category}] Написал: «{m.original}» → Правильно: «{m.corrected}»\n"
        )
        mistake_ids.append(m.id)

    await message.answer("🔁 Работа над ошибками\n\n⏳ Генерирую упражнение по твоим слабым местам...")

    exercise = await generate_drill_exercise(level, mistakes_summary)

    await state.set_state(DrillStates.drilling)
    await state.update_data(
        user_id=user.id,
        level=level,
        drill_round=0,
        mistake_ids=mistake_ids,
        drill_exercise=exercise,
    )

    await message.answer(
        f"🔁 <b>Проработка ошибок</b>\n\n{exercise}\n\n"
        f"Раунд 1/{MAX_DRILL_ROUNDS}. Отправь ответ или /menu для выхода."
    )


@router.message(DrillStates.drilling)
async def process_drill_answer(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.startswith("/menu"):
        await state.clear()
        await message.answer("Возвращаюсь в меню.", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    drill_exercise = data.get("drill_exercise", "")
    level = data.get("level", "A1")
    drill_round = data.get("drill_round", 0) + 1

    # Increment repeated counter for all drilled mistakes
    for mid in data.get("mistake_ids", []):
        await increment_mistake_repeated(session, mid)

    result = await check_answer(
        exercise=f"Упражнение на проработку ошибок:\n{drill_exercise}",
        answer=message.text,
    )

    # Save any new mistakes found during drill
    for m in result.get("mistakes", []):
        await save_mistake(
            session,
            user_id=data["user_id"],
            category=m.get("category", "other"),
            original=m.get("original", ""),
            corrected=m.get("corrected", ""),
            explanation=m.get("explanation", ""),
        )

    emoji = "✅" if result["correct"] else "❌"
    response = f"{emoji} Оценка: {result['score']:.0%}\n\n{result['explanation']}"

    if drill_round >= MAX_DRILL_ROUNDS:
        await message.answer(response)
        await state.clear()
        await message.answer(
            f"🔁 Проработка завершена! Раундов: {drill_round}\n"
            "Продолжай уроки, чтобы закрепить материал.",
            reply_markup=main_menu_keyboard(),
        )
        return

    # Generate next drill exercise
    weaknesses = await get_user_weaknesses(session, data["user_id"])
    mistakes = await get_mistakes_for_drill(session, data["user_id"], limit=5)
    if not mistakes:
        await message.answer(response)
        await state.clear()
        await message.answer("🎉 Все ошибки проработаны!", reply_markup=main_menu_keyboard())
        return

    mistakes_summary = ""
    mistake_ids = []
    for m in mistakes:
        mistakes_summary += (
            f"- [{m.category}] Написал: «{m.original}» → Правильно: «{m.corrected}»\n"
        )
        mistake_ids.append(m.id)

    next_exercise = await generate_drill_exercise(level, mistakes_summary)

    await state.update_data(
        drill_round=drill_round,
        mistake_ids=mistake_ids,
        drill_exercise=next_exercise,
    )

    await message.answer(
        f"{response}\n\n"
        f"🔁 Следующее упражнение:\n\n{next_exercise}\n\n"
        f"Раунд {drill_round + 1}/{MAX_DRILL_ROUNDS}. Отправь ответ или /menu для выхода."
    )
