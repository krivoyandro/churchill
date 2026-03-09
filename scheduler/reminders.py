import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from db.models import User
from db.session import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_daily_reminders(bot):
    """Send daily reminders to users who haven't studied today."""
    current_hour = datetime.utcnow().hour

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.onboarding_complete == True,
                User.reminder_enabled == True,
                User.reminder_hour == current_hour,
            )
        )
        users = result.scalars().all()

    for user in users:
        try:
            today = datetime.utcnow().date()
            last_active = user.last_active_at.date() if user.last_active_at else None

            if last_active == today:
                continue

            streak_text = ""
            if user.streak_days > 0:
                streak_text = f"🔥 Серия: {user.streak_days} дней! Не теряй прогресс!\n\n"

            await bot.send_message(
                user.telegram_id,
                f"👋 Привет! Время для английского!\n\n"
                f"{streak_text}"
                f"📚 Твой ежедневный урок ждёт.\n"
                f"Нажми «📚 Начать урок» чтобы продолжить.",
            )
        except Exception as e:
            logger.warning(f"Failed to send reminder to {user.telegram_id}: {e}")


def setup_scheduler(bot):
    """Schedule hourly reminder check."""
    scheduler.add_job(send_daily_reminders, "interval", hours=1, args=[bot])
    scheduler.start()
    logger.info("Scheduler started")
