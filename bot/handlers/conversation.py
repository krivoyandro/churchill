import logging
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import main_menu_keyboard
from bot.states.states import ConversationStates
from db.models import User
from db.repo import save_mistake
from services.ai.engine import conversation_respond

logger = logging.getLogger(__name__)

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
    await state.update_data(conv_history=[], user_level=level, user_id=user.id)

    await message.answer(
        "💬 Режим практики диалога\n\n"
        "Пиши на английском — я буду отвечать и исправлять ошибки.\n"
        "Для выхода напиши /menu\n\n"
        "Let's start! How are you today?"
    )


def _extract_corrections(ai_response: str) -> list[dict]:
    """Extract corrections from AI conversation response.

    AI is prompted to correct mistakes inline, typically with patterns like:
    *correction*, "should be ...", "you mean ...", etc.
    """
    corrections = []
    # Pattern: "Correct: X" / "Should be: X" / "you mean X"
    patterns = [
        r'["\*]([^"*]+)["\*]\s*(?:→|->|should be|Correct(?:ion)?:?)\s*["\*]([^"*]+)["\*]',
        r'(?:It should be|You mean|Correction:?)\s*["\*]([^"*]+)["\*]',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, ai_response, re.IGNORECASE):
            groups = match.groups()
            if len(groups) == 2:
                corrections.append({
                    "category": "grammar",
                    "original": groups[0].strip(),
                    "corrected": groups[1].strip(),
                    "explanation": "Исправлено во время диалога",
                })
            elif len(groups) == 1:
                corrections.append({
                    "category": "grammar",
                    "original": "",
                    "corrected": groups[0].strip(),
                    "explanation": "Исправлено во время диалога",
                })
    return corrections


@router.message(ConversationStates.chatting)
async def process_conversation(message: Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text.startswith("/menu"):
        await state.clear()
        await message.answer("Практика завершена! 👋", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    history = data.get("conv_history", [])
    level = data.get("user_level", "A1")
    user_id = data.get("user_id")

    history.append({"role": "user", "content": message.text})

    response = await conversation_respond(level, history)
    history.append({"role": "assistant", "content": response})

    # Extract and save corrections from AI response
    if user_id:
        corrections = _extract_corrections(response)
        for c in corrections:
            await save_mistake(
                session,
                user_id=user_id,
                category=c["category"],
                original=c["original"],
                corrected=c["corrected"],
                explanation=c["explanation"],
            )

    # Keep only last 20 messages to save memory
    if len(history) > 20:
        history = history[-20:]

    await state.update_data(conv_history=history)
    await message.answer(response)
