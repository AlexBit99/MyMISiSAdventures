import asyncio
from bott.bot import bot, dp, bot_commands
from bott.handlers import router
from database.db_session import global_init


async def main():
    global_init(True, "db/esse.db")
    dp.include_router(router)

    await bot_commands()

    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())