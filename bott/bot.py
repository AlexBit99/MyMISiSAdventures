from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from config.settings import settings
from config.answers import REPLY_BUTTONS

bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def main_board():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Меню"), KeyboardButton(text="Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

async def bot_commands():
    commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/help", description="Помощь"),
        BotCommand(command="/menu", description="Показать меню"),
        BotCommand(command="/write", description="Написать сочинение"),
        BotCommand(command="/check", description="Проверить сочинение"),
        BotCommand(command="/templates", description="Шаблоны сочинений"),
        BotCommand(command="/history", description="История сочинений"),
    ]
    await bot.set_my_commands(commands)