from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import vocabulary_topic_keyboard, main_menu_keyboard
from bot.states.states import VocabularyStates
from db.models import User, UserVocabulary
from db.repo import add_user_vocabulary, get_words_for_review
from services.ai.engine import generate_words
from services.progress.spaced_repetition import update_word_review

router = Router()


@router.message(F.text == "🔤 Слова")
async def vocabulary_menu(message: Message, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start")
        return

    words_to_review = await get_words_for_review(session, user.id, limit=5)

    if words_to_review:
        await message.answer(
            f"🔁 У тебя {len(words_to_review)} слов на повторение.\n\n"
            "Выбери действие:",
            reply_markup=_vocab_action_keyboard(has_review=True),
        )
    else:
        await message.answer(
            "📚 Словарь\n\nВыбери тему для изучения новых слов:",
            reply_markup=vocabulary_topic_keyboard(),
        )


def _vocab_action_keyboard(has_review: bool = False):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = []
    if has_review:
        buttons.append([InlineKeyboardButton(text="🔁 Повторить слова", callback_data="vocab:review")])
    buttons.append([InlineKeyboardButton(text="📖 Учить новые слова", callback_data="vocab:new")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "vocab:new")
async def choose_vocab_topic(callback: CallbackQuery):
    await callback.message.edit_text(
        "📚 Выбери тему для новых слов:",
        reply_markup=vocabulary_topic_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vocab_topic:"))
async def learn_new_words(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    topic = callback.data.split(":")[1]
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Ошибка")
        return

    level = user.current_level.value if user.current_level else "A1"

    await callback.message.edit_text("⏳ Генерирую слова...")

    words = await generate_words(level, topic, count=5)

    if not words:
        await callback.message.edit_text("Не удалось сгенерировать слова. Попробуй ещё раз.")
        return

    text = f"📖 Новые слова — тема: {topic}\n\n"
    for i, w in enumerate(words, 1):
        text += (
            f"{i}. **{w['word']}** [{w['transcription']}]\n"
            f"   🇷🇺 {w['translation']}\n"
            f"   💡 _{w['example']}_\n\n"
        )
        await add_user_vocabulary(session, user.id, w["word"], w["translation"])

    text += "✅ Слова добавлены в твой словарь для повторения!"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "vocab:review")
async def start_review(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("Ошибка")
        return

    words = await get_words_for_review(session, user.id, limit=5)
    if not words:
        await callback.message.edit_text("🎉 Нет слов на повторение! Выучи новые.")
        return

    await state.set_state(VocabularyStates.reviewing)
    await state.update_data(
        review_words=[{"id": w.id, "word": w.word, "translation": w.translation} for w in words],
        review_index=0,
        review_correct=0,
        user_id=user.id,
    )

    first_word = words[0]
    await callback.message.edit_text(
        f"🔁 Повторение (1/{len(words)})\n\n"
        f"Переведи на русский:\n\n**{first_word.word}**",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(VocabularyStates.reviewing)
async def process_review_answer(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    words = data["review_words"]
    index = data["review_index"]
    correct_count = data["review_correct"]

    current_word = words[index]
    user_answer = message.text.strip().lower()
    expected = current_word["translation"].lower()

    is_correct = user_answer == expected or expected in user_answer or user_answer in expected

    if is_correct:
        correct_count += 1
        response = f"✅ Верно! **{current_word['word']}** — {current_word['translation']}"
    else:
        response = (
            f"❌ Неверно.\n"
            f"**{current_word['word']}** — {current_word['translation']}\n"
            f"Ты написал: {message.text}"
        )

    await update_word_review(session, current_word["id"], is_correct)

    index += 1
    if index >= len(words):
        await state.clear()
        await message.answer(
            f"{response}\n\n"
            f"📊 Повторение завершено!\n"
            f"Результат: {correct_count}/{len(words)} правильных",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await state.update_data(review_index=index, review_correct=correct_count)
        next_word = words[index]
        await message.answer(
            f"{response}\n\n"
            f"🔁 Повторение ({index + 1}/{len(words)})\n\n"
            f"Переведи на русский:\n\n**{next_word['word']}**",
            parse_mode="Markdown",
        )
