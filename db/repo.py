from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    CEFRLevel,
    DailyTask,
    GoalType,
    LevelAssessment,
    Mistake,
    User,
    UserLesson,
    UserVocabulary,
)


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.last_active_at = datetime.utcnow()
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        await session.commit()
        return user
    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_level(session: AsyncSession, user_id: int, level: CEFRLevel) -> None:
    await session.execute(update(User).where(User.id == user_id).values(current_level=level))
    await session.commit()


async def update_user_goal(session: AsyncSession, user_id: int, goal: GoalType) -> None:
    await session.execute(update(User).where(User.id == user_id).values(goal=goal))
    await session.commit()


async def update_user_daily_minutes(session: AsyncSession, user_id: int, minutes: int) -> None:
    await session.execute(update(User).where(User.id == user_id).values(daily_minutes=minutes))
    await session.commit()


async def set_onboarding_complete(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(onboarding_complete=True)
    )
    await session.commit()


async def save_assessment(
    session: AsyncSession,
    user_id: int,
    level: CEFRLevel,
    score: float,
    grammar_score: float = 0.0,
    vocabulary_score: float = 0.0,
    reading_score: float = 0.0,
    details: str | None = None,
) -> LevelAssessment:
    assessment = LevelAssessment(
        user_id=user_id,
        level=level,
        score=score,
        grammar_score=grammar_score,
        vocabulary_score=vocabulary_score,
        reading_score=reading_score,
        details=details,
    )
    session.add(assessment)
    await session.commit()
    return assessment


async def save_user_lesson(
    session: AsyncSession,
    user_id: int,
    topic: str,
    content: str | None = None,
    lesson_id: int | None = None,
) -> UserLesson:
    ul = UserLesson(user_id=user_id, topic=topic, content=content, lesson_id=lesson_id)
    session.add(ul)
    await session.commit()
    await session.refresh(ul)
    return ul


async def complete_user_lesson(session: AsyncSession, lesson_id: int, score: float | None = None) -> None:
    await session.execute(
        update(UserLesson)
        .where(UserLesson.id == lesson_id)
        .values(completed=True, completed_at=datetime.utcnow(), score=score)
    )
    await session.commit()


async def save_mistake(
    session: AsyncSession,
    user_id: int,
    category: str,
    original: str,
    corrected: str,
    explanation: str | None = None,
) -> Mistake:
    m = Mistake(
        user_id=user_id,
        category=category,
        original=original,
        corrected=corrected,
        explanation=explanation,
    )
    session.add(m)
    await session.commit()
    return m


async def get_user_mistakes(session: AsyncSession, user_id: int, limit: int = 20) -> list[Mistake]:
    result = await session.execute(
        select(Mistake)
        .where(Mistake.user_id == user_id)
        .order_by(Mistake.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {}

    lessons_result = await session.execute(
        select(UserLesson).where(UserLesson.user_id == user_id, UserLesson.completed == True)
    )
    completed_lessons = len(list(lessons_result.scalars().all()))

    vocab_result = await session.execute(
        select(UserVocabulary).where(UserVocabulary.user_id == user_id, UserVocabulary.learned == True)
    )
    learned_words = len(list(vocab_result.scalars().all()))

    mistakes_result = await session.execute(
        select(Mistake).where(Mistake.user_id == user_id)
    )
    total_mistakes = len(list(mistakes_result.scalars().all()))

    return {
        "level": user.current_level.value if user.current_level else "не определён",
        "goal": user.goal.value if user.goal else "не выбрана",
        "streak": user.streak_days,
        "completed_lessons": completed_lessons,
        "learned_words": learned_words,
        "total_mistakes": total_mistakes,
        "daily_minutes": user.daily_minutes,
        "subscription": user.subscription.value,
    }


async def increment_streak(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(streak_days=User.streak_days + 1)
    )
    await session.commit()


async def add_user_vocabulary(
    session: AsyncSession,
    user_id: int,
    word: str,
    translation: str,
    word_id: int | None = None,
) -> UserVocabulary:
    uv = UserVocabulary(user_id=user_id, word=word, translation=translation, word_id=word_id)
    session.add(uv)
    await session.commit()
    await session.refresh(uv)
    return uv


async def get_words_for_review(session: AsyncSession, user_id: int, limit: int = 10) -> list[UserVocabulary]:
    now = datetime.utcnow()
    result = await session.execute(
        select(UserVocabulary)
        .where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.learned == False,
            (UserVocabulary.next_review_at <= now) | (UserVocabulary.next_review_at == None),
        )
        .order_by(UserVocabulary.next_review_at.asc().nullsfirst())
        .limit(limit)
    )
    return list(result.scalars().all())
