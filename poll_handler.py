from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_USER_ID, TELEGRAM_CHANNEL_ID
import logging

logger = logging.getLogger(__name__)

poll_cache = {}

async def create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Poll yaratish - oson usul"""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    if len(lines) < 5:
        await update.message.reply_text(
            "❌ Format noto'g'ri!\n\n"
            "Shaklash:\n"
            "Savol?\n"
            "Javob 1\n"
            "Javob 2\n"
            "Javob 3\n"
            "Javob 4\n\n"
            "Misol:\n"
            "KPI nima?\n"
            "Korxona profit solig'i\n"
            "Kapital\n"
            "Boshqa solik\n"
            "Hech biri emas"
        )
        return

    question = lines[0]
    options = lines[1:5]

    if len(options) < 2:
        await update.message.reply_text("❌ Kamida 2 ta javob kerak!")
        return

    poll_data = {
        "question": question,
        "options": options
    }

    poll_cache[user_id] = poll_data

    keyboard = [
        [InlineKeyboardButton("📊 Kanalga jo'ylash", callback_data="publish_poll")],
        [InlineKeyboardButton("❌ O'chirish", callback_data="cancel_poll")]
    ]

    await update.message.reply_text(
        "✅ Poll tayyorlandi!\n\n"
        f"❓ Savol: {question}\n"
        f"📋 Javoblar:\n" +
        "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def publish_poll(query, context: ContextTypes.DEFAULT_TYPE):
    """Poll'ni kanalga jo'ylash"""
    user_id = query.from_user.id

    if user_id not in poll_cache:
        await query.answer("❌ Poll topilmadi", show_alert=True)
        return

    poll_data = poll_cache[user_id]

    try:
        await context.bot.send_poll(
            chat_id=TELEGRAM_CHANNEL_ID,
            question=poll_data["question"],
            options=poll_data["options"],
            is_anonymous=True,
            allows_multiple_answers=False
        )

        await query.edit_message_text(
            "✅ Poll kanalga jo'ylandi!\n\n"
            f"❓ Savol: {poll_data['question']}\n"
            f"📋 Javoblar: {len(poll_data['options'])} ta"
        )

        del poll_cache[user_id]
    except Exception as e:
        await query.answer(f"❌ Xato: {str(e)}", show_alert=True)
        logger.error(f"Poll joylash xatosi: {e}")

async def cancel_poll(query, context: ContextTypes.DEFAULT_TYPE):
    """Poll'ni bekor qilish"""
    user_id = query.from_user.id

    if user_id in poll_cache:
        del poll_cache[user_id]

    await query.edit_message_text("❌ Poll o'chirildi")


