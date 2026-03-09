from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_keyboard
from bot.states.states import OnboardingStates
from db.models import CEFRLevel
from db.repo import update_user_level, save_assessment, set_onboarding_complete
from services.ai.engine import run_assessment_step, parse_assessment_result

router = Router()


@router.callback_query(F.data == "assessment:start")
async def start_assessment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.assessment_in_progress)
    await state.update_data(assessment_history=[])

    first_response = await run_assessment_step(
        [{"role": "user", "content": "Начни тест для определения моего уровня английского."}]
    )
    history = [
        {"role": "user", "content": "Начни тест для определения моего уровня английского."},
        {"role": "assistant", "content": first_response},
    ]
    await state.update_data(assessment_history=history)

    await callback.message.edit_text(f"📝 Тест уровня\n\n{first_response}")
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
    history = data.get("assessment_history", [])

    history.append({"role": "user", "content": message.text})

    response = await run_assessment_step(history)
    history.append({"role": "assistant", "content": response})
    await state.update_data(assessment_history=history)

    # Check if assessment is complete
    result = parse_assessment_result(response)
    if result:
        level = CEFRLevel(result["level"])
        await update_user_level(session, user_id, level)
        await save_assessment(
            session,
            user_id,
            level,
            score=(result["grammar_score"] + result["vocabulary_score"] + result["reading_score"]) / 3,
            grammar_score=result["grammar_score"],
            vocabulary_score=result["vocabulary_score"],
            reading_score=result["reading_score"],
            details=f"Strengths: {result['strengths']}\nWeaknesses: {result['weaknesses']}",
        )
        await set_onboarding_complete(session, user_id)
        await state.clear()

        # Clean response — remove the RESULT: lines for user display
        display_text = response.split("RESULT:")[0].strip()

        await message.answer(
            f"📊 Тест завершён!\n\n"
            f"{display_text}\n\n"
            f"🎯 **Твой уровень: {level.value}**\n"
            f"📗 Грамматика: {result['grammar_score']:.0%}\n"
            f"📘 Словарный запас: {result['vocabulary_score']:.0%}\n"
            f"📙 Чтение: {result['reading_score']:.0%}\n\n"
            f"💪 Сильные стороны: {result['strengths']}\n"
            f"🔧 Над чем работать: {result['weaknesses']}\n\n"
            f"Готов начать обучение! 🚀",
            parse_mode="Markdown",
        )
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    else:
        await message.answer(response)
