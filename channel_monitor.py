import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime

logger = logging.getLogger(__name__)

last_post_ids = {}

async def fetch_channel_posts(channel_id: str, context: ContextTypes.DEFAULT_TYPE) -> list:
    """Telegram kanaldan eng so'nggi postlarni olish"""
    try:
        if not channel_id:
            return []

        # Kanal ID ni normalize qilish - raqamli ID yoki @username
        if isinstance(channel_id, str):
            if channel_id.startswith('@'):
                channel_identifier = channel_id
            else:
                try:
                    channel_identifier = int(channel_id)
                except ValueError:
                    channel_identifier = channel_id
        else:
            channel_identifier = channel_id

        logger.info(f"Kanal tekshirilmoqda: {channel_identifier}")

        try:
            # Kanal haqqida ma'lumot olish
            chat = await context.bot.get_chat(channel_identifier)
            logger.info(f"Kanal topildi: {chat.title}")
            return []
        except Exception as e:
            logger.error(f"Kanal ma'lumotini olishda xato: {e}")
            return []

    except Exception as e:
        logger.error(f"Fetch xatosi: {e}")
        return []

async def check_new_posts(admin_id: int, channel_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Yangi postlarni tekshirish va yuborish"""
    global last_post_ids

    if not channel_id:
        logger.info("Kanal ID o'rnatilmagan")
        return

    try:
        # Kanal ma'lumotini tekshirish
        await context.bot.get_chat(channel_id)
        logger.info(f"Kanal mavjud: {channel_id}")
    except Exception as e:
        logger.error(f"Kanal mavjud emas yoki bot admin emas: {e}")
        return

async def notify_admin(admin_id: int, post: dict, context: ContextTypes.DEFAULT_TYPE):
    """Adminga yangi post haqida xabar berish"""
    try:
        text = post.get('text', "Matn yo'q")[:500] if post.get('text') else "Matn yo'q"

        keyboard = [
            [InlineKeyboardButton("✅ Qabul qil", callback_data=f"approve_source_{post['id']}")],
            [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"edit_source_{post['id']}")],
            [InlineKeyboardButton("❌ Bekor qil", callback_data="skip_source")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"""📰 Manba Kanaldan Yangi Xabar

{text}

---
Vaqt: {post.get('date', datetime.now()).strftime('%Y-%m-%d %H:%M')}"""

        await context.bot.send_message(
            chat_id=admin_id,
            text=message_text,
            reply_markup=reply_markup
        )
        logger.info(f"Admin'ga xabar yuborildi")
    except Exception as e:
        logger.error(f"Adminga xabar yuborishda xato: {e}")
