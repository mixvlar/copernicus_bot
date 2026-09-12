import os
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from bot.functions import Database, load_json

load_dotenv()

ROOT = Path(__file__).parent.parent

database = Database(name=str(ROOT / "copernicus.db"))
database.create_tables()

configuration = load_json("config.json")
eligibility = load_json("eligibility.json")
programs = load_json("programs.json")
faq = load_json("faq.json")

texts = {}
for code in ("en", "ru", "de"):
    texts[code] = load_json("texts", f"{code}.json")

LANGS = {"en": "🇬🇧 English", "ru": "🇷🇺 Русский", "de": "🇩🇪 Deutsch"}

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


class ClientStatesGroup(StatesGroup):
    asking_question = State()
    admin_password = State()
    admin_broadcast = State()
    admin_answer = State()
