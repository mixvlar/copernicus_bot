import asyncio
from aiogram.methods import DeleteWebhook
from bot.utils import logger
from bot.configuration import bot, dp
from bot.routers import admin_router, user_router, eligibility_router, programs_router, faq_router, profile_router
from bot.scheduler import loop


async def main():
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(eligibility_router)
    dp.include_router(programs_router)
    dp.include_router(faq_router)
    dp.include_router(profile_router)
    await bot(DeleteWebhook(drop_pending_updates=True))
    asyncio.create_task(loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Bot started")
    asyncio.run(main())
