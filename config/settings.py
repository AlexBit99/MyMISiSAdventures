import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///esse.db")
    GIGACHAT_KEY: str = os.getenv("GIGACHAT_KEY")

settings = Settings()