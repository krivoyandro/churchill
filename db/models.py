import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class CEFRLevel(str, enum.Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


class GoalType(str, enum.Enum):
    FROM_ZERO = "from_zero"
    CONVERSATIONAL = "conversational"
    FOR_WORK = "for_work"
    FOR_EXAM = "for_exam"
    FOR_TRAVEL = "for_travel"
    FOR_IT = "for_it"
    FOR_MEDICINE = "for_medicine"
    FOR_BUSINESS = "for_business"
    FOR_EMIGRATION = "for_emigration"


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_level: Mapped[CEFRLevel | None] = mapped_column(Enum(CEFRLevel), nullable=True)
    target_level: Mapped[CEFRLevel | None] = mapped_column(Enum(CEFRLevel), nullable=True)
    goal: Mapped[GoalType | None] = mapped_column(Enum(GoalType), nullable=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=20)
    subscription: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.FREE
    )
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    reminder_hour: Mapped[int] = mapped_column(Integer, default=10)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    total_lessons: Mapped[int] = mapped_column(Integer, default=0)
    total_words_learned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    lessons: Mapped[list["UserLesson"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    vocabulary: Mapped[list["UserVocabulary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    mistakes: Mapped[list["Mistake"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    assessments: Mapped[list["LevelAssessment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    daily_tasks: Mapped[list["DailyTask"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LearningGoal(Base):
    __tablename__ = "learning_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    goal_type: Mapped[GoalType] = mapped_column(Enum(GoalType))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel))
    target_months: Mapped[int] = mapped_column(Integer, default=6)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LevelAssessment(Base):
    __tablename__ = "level_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    grammar_score: Mapped[float] = mapped_column(Float, default=0.0)
    vocabulary_score: Mapped[float] = mapped_column(Float, default=0.0)
    reading_score: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="assessments")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel))
    module: Mapped[int] = mapped_column(Integer, default=1)
    order: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500))
    topic: Mapped[str] = mapped_column(String(255))
    grammar_focus: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vocabulary_focus: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserLesson(Base):
    __tablename__ = "user_lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    topic: Mapped[str] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="lessons")


class VocabularyWord(Base):
    __tablename__ = "vocabulary_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(255), index=True)
    translation: Mapped[str] = mapped_column(String(255))
    transcription: Mapped[str | None] = mapped_column(String(255), nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel))
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)


class UserVocabulary(Base):
    __tablename__ = "user_vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_id: Mapped[int | None] = mapped_column(ForeignKey("vocabulary_words.id", ondelete="SET NULL"), nullable=True)
    word: Mapped[str] = mapped_column(String(255))
    translation: Mapped[str] = mapped_column(String(255))
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    learned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="vocabulary")


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[CEFRLevel] = mapped_column(Enum(CEFRLevel))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=1)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[str | None] = mapped_column(Text, nullable=True)


class Mistake(Base):
    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(100))
    original: Mapped[str] = mapped_column(Text)
    corrected: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    repeated: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="mistakes")


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    task_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="daily_tasks")
