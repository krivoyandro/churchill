from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    main_menu_keyboard,
    settings_keyboard,
    goal_keyboard,
    minutes_keyboard,
    assessment_start_keyboard,
)
from bot.states.states import OnboardingStates
from db.models import User
from db.repo import get_user_stats, get_user_mistakes, get_active_plan, save_learning_plan, toggle_reminder
from services.ai.engine import generate_learning_plan

router = Router()


@router.message(Command("menu"))
@router.message(F.text == "🔙 В меню")
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        await event.answer()
    else:
        await event.answer("Главное меню:", reply_markup=main_menu_keyboard())


@router.message(F.text == "📊 Прогресс")
async def show_progress(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start")
        return

    stats = await get_user_stats(session, user.id)

    weaknesses = stats.get("weaknesses", [])
    weak_str = ", ".join(weaknesses[:3]) if weaknesses else "пока нет данных"

    await message.answer(
        f"📊 <b>Твой прогресс</b>\n\n"
        f"🎯 Уровень: {stats['level']}\n"
        f"🎓 Цель: {stats['goal']}\n"
        f"🔥 Серия дней: {stats['streak']}\n"
        f"📚 Уроков пройдено: {stats['completed_lessons']}\n"
        f"📖 Слов выучено: {stats['learned_words']}\n"
        f"❌ Всего ошибок: {stats['total_mistakes']}\n"
        f"⚠️ Слабые темы: {weak_str}\n"
        f"⏱ Минут в день: {stats['daily_minutes']}\n"
        f"💎 Подписка: {stats['subscription']}",
    )


@router.message(F.text == "❌ Мои ошибки")
async def show_mistakes(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start")
        return

    mistakes = await get_user_mistakes(session, user.id, limit=10)
    if not mistakes:
        await message.answer("🎉 У тебя пока нет записанных ошибок! Продолжай учиться.")
        return

    text = "❌ **Последние ошибки**\n\n"
    for i, m in enumerate(mistakes, 1):
        text += (
            f"{i}. [{m.category}]\n"
            f"   ❌ {m.original}\n"
            f"   ✅ {m.corrected}\n"
        )
        if m.explanation:
            text += f"   💡 {m.explanation[:100]}\n"
        text += "\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "📖 Мой план")
async def show_plan(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start")
        return

    current = user.current_level.value if user.current_level else "A0"
    goal = user.goal.value if user.goal else "conversational"
    minutes = user.daily_minutes

    # Determine target level
    level_order = ["A0", "A1", "A2", "B1", "B2", "C1"]
    current_idx = level_order.index(current) if current in level_order else 0
    target = level_order[min(current_idx + 2, len(level_order) - 1)]

    # Check for existing plan
    existing_plan = await get_active_plan(session, user.id)
    if existing_plan:
        plan_text = existing_plan.plan_text
        header = (
            f"📖 <b>Твой план обучения</b>\n"
            f"📅 Создан: {existing_plan.created_at.strftime('%d.%m.%Y')}\n"
            f"🎯 {existing_plan.current_level} → {existing_plan.target_level}\n\n"
        )
    else:
        await message.answer("⏳ Генерирую персональный план...")
        plan_text = await generate_learning_plan(current, target, goal, minutes)
        await save_learning_plan(session, user.id, current, target, goal, minutes, plan_text)
        header = f"📖 <b>Твой план обучения</b>\n🎯 {current} → {target}\n\n"

    full_text = header + plan_text
    # Split long messages
    if len(full_text) > 4000:
        parts = [full_text[i:i + 4000] for i in range(0, len(full_text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(full_text)


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    await message.answer("⚙️ Настройки:", reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings:goal")
async def change_goal(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        await state.update_data(user_id=user.id)
        await state.set_state(OnboardingStates.choosing_goal)
        await callback.message.edit_text("Выбери новую цель:", reply_markup=goal_keyboard())
    await callback.answer()


@router.callback_query(F.data == "settings:minutes")
async def change_minutes(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        await state.update_data(user_id=user.id)
        await state.set_state(OnboardingStates.choosing_minutes)
        await callback.message.edit_text(
            "Сколько минут в день?", reply_markup=minutes_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "settings:reminder")
async def toggle_reminder_setting(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        new_state = await toggle_reminder(session, user.id)
        status = "включены ✅" if new_state else "выключены ❌"
        await callback.message.edit_text(f"🔔 Напоминания {status}")
    await callback.answer()


@router.callback_query(F.data == "settings:retest")
async def retest(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        await state.update_data(user_id=user.id)
        await callback.message.edit_text(
            "Пройти тест уровня заново?",
            reply_markup=assessment_start_keyboard(),
        )
    await callback.answer()
