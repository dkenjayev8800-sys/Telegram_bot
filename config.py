import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID", "")

# Agar channel username bo'lsa @ bilan, ID bo'lsa raqam
CHANNEL_IDENTIFIER = TELEGRAM_CHANNEL_ID

