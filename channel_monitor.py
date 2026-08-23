import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

last_post_ids = {}

async def fetch_channel_posts(channel_id: str, context: ContextTypes.DEFAULT_TYPE) -> list:
    """Telegram kanaldan eng so'nggi postlarni olish"""
    try:
        if not channel_id:
            return []

        # Kanal ID ni normalize qilish
        if isinstance(channel_id, str) and channel_id.startswith('@'):
            channel_identifier = channel_id
        else:
            channel_identifier = channel_id

        logger.info(f"Kanal tekshirilmoqda: {channel_identifier}")

        # Telegram Bot API orqali kanal informatsiyasi
        # Eslatma: Bot admin bo'lishi kerak
        updates = await context.bot.get_updates(limit=100)

        posts = []
        for update in updates:
            if update.channel_post:
                posts.append({
                    'id': update.channel_post.message_id,
                    'text': update.channel_post.text or update.channel_post.caption or "Matn yo'q",
                    'date': update.channel_post.date,
                    'media': update.channel_post.photo or update.channel_post.video or update.channel_post.document
                })

        return sorted(posts, key=lambda x: x['date'], reverse=True)
    except Exception as e:
        logger.error(f"Kanal ma'lumotini olishda xato: {e}")
        return []

async def check_new_posts(admin_id: int, channel_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Yangi postlarni tekshirish va yuborish"""
    global last_post_ids

    if not channel_id:
        logger.info("Kanal ID o'rnatilmagan")
        return

    posts = await fetch_channel_posts(channel_id, context)

    if not posts:
        return

    channel_key = str(channel_id)
    last_id = last_post_ids.get(channel_key, 0)

    new_posts = [p for p in posts if p['id'] > last_id]

    if new_posts:
        last_post_ids[channel_key] = new_posts[0]['id']

        for post in new_posts[:1]:  # So'nggi 1 ta post
            await notify_admin(admin_id, post, context)
            logger.info(f"Yangi post topildi: {post['id']}")

async def notify_admin(admin_id: int, post: dict, context: ContextTypes.DEFAULT_TYPE):
    """Adminga yangi post haqida xabar berish"""
    try:
        text = post['text'][:500] if post['text'] else "Matn yo'q"

        keyboard = [
            [InlineKeyboardButton("✅ Qabul qil", callback_data=f"approve_source_{post['id']}")],
            [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"edit_source_{post['id']}")],
            [InlineKeyboardButton("❌ Bekor qil", callback_data="skip_source")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"""📰 *Manba Kanaldan Yangi Xabar*

{text}

---
⏰ Vaqt: {post['date'].strftime('%Y-%m-%d %H:%M')}"""

        await context.bot.send_message(
            chat_id=admin_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Adminga xabar yuborishda xato: {e}")
