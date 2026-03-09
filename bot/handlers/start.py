from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    goal_keyboard,
    minutes_keyboard,
    main_menu_keyboard,
    assessment_start_keyboard,
)
from bot.states.states import OnboardingStates
from db.repo import get_or_create_user, update_user_goal, update_user_daily_minutes
from db.models import GoalType

router = Router()

GOAL_LABELS = {
    "from_zero": "🆕 С нуля",
    "conversational": "💬 Разговорный",
    "for_work": "💼 Для работы",
    "for_exam": "📝 Для экзамена",
    "for_travel": "✈️ Для путешествий",
    "for_it": "💻 Для IT",
    "for_medicine": "🏥 Для медицины",
    "for_business": "📊 Для бизнеса",
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if user.onboarding_complete:
        await message.answer(
            f"С возвращением, {user.first_name or 'друг'}! 👋\n"
            "Готов продолжить обучение?",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "👋 Привет! Я — Churchill, твой AI-преподаватель английского.\n\n"
        "Помогу выучить язык с нуля или довести до уверенного уровня.\n\n"
        "Для начала давай определим твою цель.\n"
        "Зачем тебе английский?",
        reply_markup=goal_keyboard(),
    )
    await state.update_data(user_id=user.id)
    await state.set_state(OnboardingStates.choosing_goal)


@router.callback_query(OnboardingStates.choosing_goal, F.data.startswith("goal:"))
async def on_goal_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    goal_key = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = data["user_id"]

    await update_user_goal(session, user_id, GoalType(goal_key))
    await state.update_data(goal=goal_key)

    goal_label = GOAL_LABELS.get(goal_key, goal_key)
    await callback.message.edit_text(
        f"Отлично! Цель: {goal_label}\n\n"
        "⏱ Сколько минут в день ты готов уделять английскому?",
        reply_markup=minutes_keyboard(),
    )
    await state.set_state(OnboardingStates.choosing_minutes)
    await callback.answer()


@router.callback_query(OnboardingStates.choosing_minutes, F.data.startswith("minutes:"))
async def on_minutes_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    minutes = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_id = data["user_id"]

    await update_user_daily_minutes(session, user_id, minutes)
    await state.update_data(daily_minutes=minutes)

    await callback.message.edit_text(
        f"✅ Отлично! {minutes} минут в день — хороший режим.\n\n"
        "Теперь давай определим твой текущий уровень.\n"
        "Я задам несколько вопросов — от простых к сложным.\n"
        "Это займёт 2-3 минуты.",
        reply_markup=assessment_start_keyboard(),
    )
    await callback.answer()
