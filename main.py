import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from bot.handlers import start, assessment, lessons, vocabulary, conversation, menu, drill
from bot.middlewares.db import DbSessionMiddleware
from db.session import engine
from scheduler.reminders import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    # Database schema is managed by Alembic migrations.
    # Run `alembic upgrade head` before starting the bot.
    setup_scheduler(bot)
    logger.info("Bot started")


async def main():
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(assessment.router)
    dp.include_router(lessons.router)
    dp.include_router(drill.router)
    dp.include_router(vocabulary.router)
    dp.include_router(conversation.router)
    dp.include_router(menu.router)

    await on_startup(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
