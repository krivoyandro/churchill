from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_keyboard
from bot.states.states import ConversationStates
from db.models import User
from services.ai.engine import conversation_respond

router = Router()


@router.message(F.text == "💬 Практика диалога")
async def start_conversation(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start")
        return

    level = user.current_level.value if user.current_level else "A1"

    await state.set_state(ConversationStates.chatting)
    await state.update_data(conv_history=[], user_level=level)

    await message.answer(
        "💬 Режим практики диалога\n\n"
        "Пиши на английском — я буду отвечать и исправлять ошибки.\n"
        "Для выхода напиши /menu\n\n"
        "Let's start! How are you today?"
    )


@router.message(ConversationStates.chatting)
async def process_conversation(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/menu"):
        await state.clear()
        await message.answer("Практика завершена! 👋", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    history = data.get("conv_history", [])
    level = data.get("user_level", "A1")

    history.append({"role": "user", "content": message.text})

    response = await conversation_respond(level, history)
    history.append({"role": "assistant", "content": response})

    # Keep only last 20 messages to save memory
    if len(history) > 20:
        history = history[-20:]

    await state.update_data(conv_history=history)
    await message.answer(response)
