import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import datetime, timedelta

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, ADMIN_USER_ID
from database import (
    load_database, save_database, add_publish_time, remove_publish_time,
    get_publish_times, add_topic, get_topics, add_to_queue, get_queue, remove_from_queue
)
from ai_handler import generate_post, refine_post
from scheduler import start_scheduler, stop_scheduler, add_inactivity_timeout, reset_inactivity_timeout, set_monitor_callback, set_app_context
from channel_monitor import check_new_posts
from tax_reports import add_tax_report, get_tax_reports, remove_tax_report, get_today_reminders, update_tax_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_state = {}
pending_posts = {}  # Post ID -> post data
auto_publish_callbacks = {}  # User ID -> auto publish callback

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanish"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return

    from config import SOURCE_CHANNEL_ID
    data = load_database()

    keyboard = [
        [InlineKeyboardButton("⏰ Chop etish vaqtlari", callback_data="times")],
        [InlineKeyboardButton("📚 Mavzular", callback_data="topics")],
        [InlineKeyboardButton("📰 Manba ma'lumotlari", callback_data="source_news")],
        [InlineKeyboardButton("📋 Soliq hisobotlari", callback_data="tax_reports")],
        [InlineKeyboardButton("📢 Kanal sozlash", callback_data="setup_source_channel")],
        [InlineKeyboardButton("📋 Navbat", callback_data="queue")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    source_info = data.get('source_channel_id', 'O\'rnatilmagan')

    await update.message.reply_text(
        f"👋 Salom! Bot sozlamalarini boshqarish\n\n📢 Manba: {source_info}\n\nNimani qilishni xoxlaysiz?",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tugmalar handleri"""
    query = update.callback_query
    await query.answer()

    if query.data == "times":
        await show_times(query, context)
    elif query.data == "topics":
        await show_topics(query, context)
    elif query.data == "source_news":
        await show_source_news(query, context)
    elif query.data == "tax_reports":
        await show_tax_reports(query, context)
    elif query.data == "setup_source_channel":
        user_state[query.from_user.id] = "waiting_source_channel"
        await query.edit_message_text("📢 Manba kanal ID yoki @username ni kiriting:\n(Masalan: -1001234567890 yoki @kanalnom)")
    elif query.data == "queue":
        await show_queue(query, context)
    elif query.data == "add_time":
        user_state[query.from_user.id] = "waiting_time"
        await query.edit_message_text("⏰ Vaqtni kiriting (masalan: 09:00)")
    elif query.data == "add_topic":
        user_state[query.from_user.id] = "waiting_topic"
        await query.edit_message_text("📚 Mavzuni kiriting:")
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("⏰ Chop etish vaqtlari", callback_data="times")],
            [InlineKeyboardButton("📚 Mavzular", callback_data="topics")],
            [InlineKeyboardButton("📰 Manba ma'lumotlari", callback_data="source_news")],
            [InlineKeyboardButton("📋 Soliq hisobotlari", callback_data="tax_reports")],
            [InlineKeyboardButton("📢 Kanal sozlash", callback_data="setup_source_channel")],
            [InlineKeyboardButton("📋 Navbat", callback_data="queue")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 Salom! Bot sozlamalarini boshqarish\n\nNimani qilishni xoxlaysiz?",
            reply_markup=reply_markup
        )
    elif query.data.startswith("del_time_"):
        time_str = query.data.replace("del_time_", "")
        remove_publish_time(time_str)
        await show_times(query, context)
    elif query.data.startswith("publish_"):
        post_id = int(query.data.replace("publish_", ""))
        await publish_post(post_id, context)
        await query.answer("✅ Post kanalga yuborildi!")
    elif query.data.startswith("approve_source_"):
        post_id = query.data.replace("approve_source_", "")
        post_data = pending_posts.get(post_id)
        if post_data:
            add_to_queue(post_data)
            del pending_posts[post_id]
            reset_inactivity_timeout(query.from_user.id)
            await query.edit_message_text("✅ Post navbatga qo'shildi!")
    elif query.data.startswith("edit_source_"):
        post_id = query.data.replace("edit_source_", "")
        user_state[query.from_user.id] = f"editing_{post_id}"
        await query.edit_message_text("✏️ Post matnini o'zgartirib yozing:")
    elif query.data == "skip_source":
        await query.edit_message_text("⏭️ Otsib yuborildi")
    elif query.data.startswith("approve_topic_"):
        post_id = int(query.data.replace("approve_topic_", ""))
        post_data = pending_posts.get(post_id)
        if post_data:
            add_to_queue(post_data)
            del pending_posts[post_id]
            reset_inactivity_timeout(query.from_user.id)
            await query.edit_message_text("✅ Post navbatga qo'shildi!")
    elif query.data.startswith("refine_topic_"):
        post_id = int(query.data.replace("refine_topic_", ""))
        user_state[query.from_user.id] = f"refining_{post_id}"
        await query.edit_message_text("✏️ Post haqida fikring:")
    elif query.data.startswith("dtax_"):
        tax_id = int(query.data.replace("dtax_", ""))
        reports = get_tax_reports()
        if 0 < tax_id <= len(reports):
            remove_tax_report(reports[tax_id - 1]['name'])
            await show_tax_reports(query, context)
    elif query.data.startswith("etax_"):
        tax_id = int(query.data.replace("etax_", ""))
        reports = get_tax_reports()
        if 0 < tax_id <= len(reports):
            tax_name = reports[tax_id - 1]['name']
            user_state[query.from_user.id] = f"editing_tax_{tax_name}"
            await query.edit_message_text(f"📝 *{tax_name}* uchun oylik kunni o'zgartiring:\n\n*1. Hisobot kuni* yoki *2. To'lov kuni*\n\nMasalan: *1 15* (hisobot 15-kuniga o'zgartirish)", parse_mode="Markdown")
    elif query.data == "add_tax":
        user_state[query.from_user.id] = "waiting_tax_type"
        await query.edit_message_text("""📋 *Soliq turi*

Quyidagisini tanlang yoki kiriting:

• KPI - Korxona profit solig'i
• Asosiy soliq - Asosiy soliq turi
• Boshqa soliq turi...

Yoki o'zing yozing:""", parse_mode="Markdown")

async def show_times(query, context: ContextTypes.DEFAULT_TYPE):
    """Chop etish vaqtlarini ko'rsatish"""
    times = get_publish_times()
    text = "⏰ *Chop etish vaqtlari:*\n\n"

    keyboard = []
    for t in times:
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {t}", callback_data=f"del_time_{t}")
        ])

    keyboard.append([InlineKeyboardButton("➕ Vaqt qo'sh", callback_data="add_time")])
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    text += "\n".join(times) if times else "Vaqtlar o'rnatilmagan"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_topics(query, context: ContextTypes.DEFAULT_TYPE):
    """Mavzularni ko'rsatish"""
    topics = get_topics()
    text = "📚 *Mavzular:*\n\n"

    keyboard = [[InlineKeyboardButton("➕ Mavzu qo'sh", callback_data="add_topic")]]
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    if topics:
        for topic in topics:
            text += f"• {topic['text']}\n"
    else:
        text += "Mavzular yo'q"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_source_news(query, context: ContextTypes.DEFAULT_TYPE):
    """Manba kanaldan yangi ma'lumotlarni ko'rsatish"""
    text = "📰 *Manba Ma'lumotlari*\n\n"
    text += "Bot har 5 minutda manba kanalda yangi xabarlarni tekshiradi.\n\n"
    text += "Yangi xabar topilsa, bu yerda chiqadi.\n\n"
    text += "⏳ Hozircha yangi xabar yo'q"

    keyboard = [[InlineKeyboardButton("🏠 Orqaga", callback_data="back")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_tax_reports(query, context: ContextTypes.DEFAULT_TYPE):
    """Soliq hisobotlarini ko'rsatish"""
    reports = get_tax_reports()
    text = "📋 *Soliq Hisobotlari*\n\n"

    keyboard = []
    if reports:
        for i, report in enumerate(reports, 1):
            text += f"{i}. {report['name']}\n"
            text += f"   📤 Hisobot: Har oyning {report['report_day']}-kuni\n"
            text += f"   💳 To'lov: Har oyning {report['payment_day']}-kuni\n\n"

            # Callback data qisqartirish (max 64 char)
            tax_id = str(i)
            keyboard.append([
                InlineKeyboardButton(f"✏️", callback_data=f"etax_{tax_id}"),
                InlineKeyboardButton(f"🗑️", callback_data=f"dtax_{tax_id}")
            ])
    else:
        text += "Hisobotlar o'rnatilmagan"

    keyboard.append([InlineKeyboardButton("➕ Hisobot qo'sh", callback_data="add_tax")])
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_channel(query, context: ContextTypes.DEFAULT_TYPE):
    """Kanal ma'lumotini ko'rsatish"""
    text = f"""📢 *Kanal*

Kanal ID: `{TELEGRAM_CHANNEL_ID}`

Bot shu kanalga postlarni chop etadi."""

    keyboard = [[InlineKeyboardButton("🏠 Orqaga", callback_data="back")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_queue(query, context: ContextTypes.DEFAULT_TYPE):
    """Chop etish navbatini ko'rsatish"""
    queue = get_queue()
    text = "📋 *Chop etish navbati:*\n\n"

    keyboard = []

    if not queue:
        text += "Navbat bo'sh"
    else:
        for i, post in enumerate(queue, 1):
            keyboard.append([
                InlineKeyboardButton(
                    f"#{i} - {post.get('title', 'Post')[:20]}",
                    callback_data=f"publish_{post['id']}"
                )
            ])
            text += f"{i}. {post.get('title', 'Post')}\n"

    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def publish_post(post_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Postni kanalga chop etish"""
    try:
        queue = get_queue()
        post = next((p for p in queue if p['id'] == post_id), None)

        if post:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=post['content']
            )
            remove_from_queue(post_id)
            logger.info(f"Post #{post_id} kanalga chop etildi")
    except Exception as e:
        logger.error(f"Chop etishda xato: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni qabul qilish"""
    if update.effective_user.id != ADMIN_USER_ID:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_state.get(user_id) == "waiting_tax_type":
        user_state[user_id] = "waiting_tax_report_day"
        user_state[f"{user_id}_tax_type"] = text
        await update.message.reply_text(f"📤 Hisobot topshirishning kuni (oyda, masalan: 10, 15, 20):")

    elif user_state.get(user_id) == "waiting_tax_report_day":
        try:
            day = int(text)
            if 1 <= day <= 31:
                user_state[user_id] = "waiting_tax_payment_day"
                user_state[f"{user_id}_tax_report_day"] = day
                await update.message.reply_text(f"💳 To'lovning kuni (oyda, masalan: 10, 15, 20):")
            else:
                await update.message.reply_text("❌ Kun 1-31 orasida bo'lishi kerak")
        except ValueError:
            await update.message.reply_text("❌ Raqam kiriting (masalan: 10)")

    elif user_state.get(user_id) == "waiting_tax_payment_day":
        try:
            payment_day = int(text)
            if 1 <= payment_day <= 31:
                tax_type = user_state.get(f"{user_id}_tax_type", "Soliq")
                report_day = user_state.get(f"{user_id}_tax_report_day", 1)

                add_tax_report(tax_type, report_day, payment_day)
                await update.message.reply_text(f"✅ Hisobot qo'shildi:\n*{tax_type}*\n📤 Har oyning {report_day}-kuni\n💳 Har oyning {payment_day}-kuni", parse_mode="Markdown")

                user_state[user_id] = None
                if f"{user_id}_tax_type" in user_state:
                    del user_state[f"{user_id}_tax_type"]
                if f"{user_id}_tax_report_day" in user_state:
                    del user_state[f"{user_id}_tax_report_day"]
            else:
                await update.message.reply_text("❌ Kun 1-31 orasida bo'lishi kerak")
        except ValueError:
            await update.message.reply_text("❌ Raqam kiriting (masalan: 20)")

    elif user_state.get(user_id) == "waiting_source_channel":
        data = load_database()
        data['source_channel_id'] = text
        save_database(data)
        await update.message.reply_text(f"✅ Kanal o'rnatildi: {text}\n\n/start buyrugini kiriting")
        user_state[user_id] = None

    elif any(user_state.get(user_id, "").startswith("editing_tax_") for _ in [None]):
        state = user_state.get(user_id, "")
        if state.startswith("editing_tax_"):
            tax_name = state.replace("editing_tax_", "")
            try:
                parts = text.split()
                if len(parts) == 2:
                    edit_type = int(parts[0])  # 1=hisobot, 2=to'lov
                    new_day = int(parts[1])

                    if 1 <= new_day <= 31:
                        update_tax_report(tax_name, edit_type, new_day)
                        await update.message.reply_text(f"✅ {tax_name} yangilandi!")
                    else:
                        await update.message.reply_text("❌ Kun 1-31 orasida bo'lishi kerak")
                else:
                    await update.message.reply_text("❌ Format: *1 15* (1=hisobot, 2=to'lov, kun)", parse_mode="Markdown")
            except ValueError:
                await update.message.reply_text("❌ Raqamlar kiriting: *1 15*", parse_mode="Markdown")

            user_state[user_id] = None

    elif user_state.get(user_id) == "waiting_time":
        if add_publish_time(text):
            await update.message.reply_text(f"✅ Vaqt qo'shildi: {text}")
        else:
            await update.message.reply_text(f"❌ Bu vaqt allaqachon mavjud")
        user_state[user_id] = None

    elif user_state.get(user_id) == "waiting_topic":
        await update.message.reply_text(f"⏳ Ma'lumot yig'ilyapti: {text}")

        try:
            post = generate_post(text)
            post_id = len(pending_posts) + 1
            pending_posts[post_id] = {
                "title": text,
                "content": post,
                "status": "waiting_approval"
            }

            keyboard = [
                [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"refine_topic_{post_id}")],
                [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
            ]

            await update.message.reply_text(
                f"📝 Mavzu: {text}\n\n{post}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            # 1 soat timeout
            add_inactivity_timeout(user_id, lambda: auto_publish_pending(post_id, context))
        except Exception as e:
            await update.message.reply_text(f"❌ Xato: {str(e)}")

        user_state[user_id] = None

    elif any(user_state.get(user_id, "").startswith("editing_") or user_state.get(user_id, "").startswith("refining_") for _ in [None]):
        state = user_state.get(user_id, "")
        if state.startswith("editing_"):
            post_id = state.replace("editing_", "")
            post_data = pending_posts.get(post_id)
            if post_data:
                post_data['content'] = text
                await update.message.reply_text(f"✅ Post o'zgartirildi!")
            user_state[user_id] = None
        elif state.startswith("refining_"):
            post_id = int(state.replace("refining_", ""))
            post_data = pending_posts.get(post_id)
            if post_data:
                try:
                    refined_post = refine_post(post_data['content'], text)
                    post_data['content'] = refined_post

                    keyboard = [
                        [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                        [InlineKeyboardButton("✏️ Yana tahrirlash", callback_data=f"refine_topic_{post_id}")],
                        [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
                    ]

                    await update.message.reply_text(
                        f"📝 Yangilangan post:\n\n{refined_post}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    await update.message.reply_text(f"❌ Xato: {str(e)}")
            user_state[user_id] = None

async def auto_publish_pending(post_id: int, context: ContextTypes.DEFAULT_TYPE):
    """1 soat inaktivlikdan so'ng avtomatik chop etish"""
    post_data = pending_posts.get(post_id)
    if post_data:
        add_to_queue(post_data)
        del pending_posts[post_id]
        logger.info(f"1 soat timeout - Post #{post_id} avtomatik navbatga qo'shildi")

        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"⏰ 1 soat timeout - Post avtomatik navbatga qo'shildi:\n\n{post_data['title']}"
            )
        except Exception as e:
            logger.error(f"Timeout xabari yuborishda xato: {e}")

def main():
    """Bot ishga tusishi"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Bot contextini scheduler ga uzatish
    set_app_context(app)

    # Monitoring callback ni set qilish
    async def monitor_callback():
        data = load_database()
        source_channel_id = data.get('source_channel_id')
        if source_channel_id:
            await check_new_posts(ADMIN_USER_ID, source_channel_id, app.context_types.application.context)

    set_monitor_callback(monitor_callback)

    start_scheduler(app)
    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
