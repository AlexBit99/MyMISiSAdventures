from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config.settings import settings
from config.answers import REPLY_BUTTONS

bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Старт"), KeyboardButton(text="Меню")],
            [KeyboardButton(text="Помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard