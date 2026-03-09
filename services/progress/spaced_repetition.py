"""Spaced repetition using SM-2 algorithm."""

from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserVocabulary


async def update_word_review(session: AsyncSession, word_id: int, correct: bool) -> None:
    """Update word review schedule using SM-2 algorithm."""
    from sqlalchemy import select

    result = await session.execute(select(UserVocabulary).where(UserVocabulary.id == word_id))
    word = result.scalar_one_or_none()
    if not word:
        return

    if correct:
        word.correct_count += 1
        if word.interval_days == 1:
            word.interval_days = 3
        elif word.interval_days == 3:
            word.interval_days = 7
        else:
            word.interval_days = int(word.interval_days * word.ease_factor)
        word.ease_factor = max(1.3, word.ease_factor + 0.1)
        if word.correct_count >= 5:
            word.learned = True
    else:
        word.wrong_count += 1
        word.interval_days = 1
        word.ease_factor = max(1.3, word.ease_factor - 0.2)

    word.next_review_at = datetime.utcnow() + timedelta(days=word.interval_days)
    await session.commit()
