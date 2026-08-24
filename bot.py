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
from tax_reports import add_tax_report, get_tax_reports, remove_tax_report, get_today_reminders, update_tax_report
from poll_handler import create_poll, publish_poll, cancel_poll

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_state = {}
pending_posts = {}  # Post ID -> post data
auto_publish_callbacks = {}  # User ID -> auto publish callback

TOPIC_CATEGORIES = {
    "1": "Soliq qonunchilik va to'lovlar",
    "2": "Bухgalteriya amaliyoti va hisobotlar",
    "3": "Moliya va kapital boshqaruvi",
    "4": "Xorijiy savdo va import-eksport",
    "5": "Korporativ huquq va shartnomalar",
    "6": "Boshqa mavzular"
}

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
        [InlineKeyboardButton("📋 Soliq hisobotlari", callback_data="tax_reports")],
        [InlineKeyboardButton("📊 Poll", callback_data="poll")],
        [InlineKeyboardButton("📋 Navbat", callback_data="queue")],
        [InlineKeyboardButton("📊 Avtomatik Chop Status", callback_data="auto_publish_status")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Salom! Bot sozlamalarini boshqarish\n\nNimani qilishni xoxlaysiz?",
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
    elif query.data == "tax_reports":
        await show_tax_reports(query, context)
    elif query.data == "poll":
        await query.edit_message_text(
            "📊 Poll Yaratish\n\n"
            "Format:\n"
            "Savol?\n"
            "Javob 1\n"
            "Javob 2\n"
            "Javob 3\n"
            "Javob 4\n\n"
            "Misol:\n"
            "KPI nima?\n"
            "Korxona profit solig'i\n"
            "Kapital boshqaruvi\n"
            "Moliya rivojlantirish\n"
            "Hech biri emas\n\n"
            "Shundayin formatda xabar yuboring:"
        )
    elif query.data == "queue":
        await show_queue(query, context)
    elif query.data == "auto_publish_status":
        await show_auto_publish_status(query, context)
    elif query.data == "add_another_question":
        query.from_user.id
        user_state[query.from_user.id] = "waiting_test_questions"
        await query.edit_message_text("📝 Keyingi savol matnini kiriting:")
    elif query.data == "test_ready":
        user_id = query.from_user.id
        questions = context.user_data.get("test_questions", [])
        title = context.user_data.get("test_title", "Test")

        if questions:
            test_id = create_test(title, questions)
            await query.edit_message_text(
                f"✅ Test yaratildi!\n\n"
                f"ID: {test_id}\n"
                f"Sarlavha: {title}\n"
                f"Savollar: {len(questions)}"
            )
            user_state[user_id] = None
            if "test_title" in context.user_data:
                del context.user_data["test_title"]
            if "test_questions" in context.user_data:
                del context.user_data["test_questions"]
            if "current_question_text" in context.user_data:
                del context.user_data["current_question_text"]
    elif query.data == "add_time":
        user_state[query.from_user.id] = "waiting_time"
        await query.edit_message_text("⏰ Vaqtni kiriting (masalan: 09:00)")
    elif query.data == "add_topic":
        user_state[query.from_user.id] = "waiting_topic"
        await query.edit_message_text("📚 Mavzuni kiriting:")
    elif query.data == "generate_topic":
        user_state[query.from_user.id] = "waiting_generate_topic"
        await query.edit_message_text("""🔍 *Mavzu Generatsiyasi*

Sohangizga tegishli mavzularni tanlang:

1️⃣ Soliq qonunchilik
2️⃣ Bухгалтерия
3️⃣ Moliya
4️⃣ Xorijiy savdo
5️⃣ Korporativ huquq
6️⃣ Boshqa mavzu

Raqamni yoki o'z mavzuingizni yozing:""", parse_mode="Markdown")
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("⏰ Chop etish vaqtlari", callback_data="times")],
            [InlineKeyboardButton("📚 Mavzular", callback_data="topics")],
            [InlineKeyboardButton("📋 Soliq hisobotlari", callback_data="tax_reports")],
            [InlineKeyboardButton("📊 Poll", callback_data="poll")],
            [InlineKeyboardButton("📋 Navbat", callback_data="queue")],
            [InlineKeyboardButton("📊 Avtomatik Chop Status", callback_data="auto_publish_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👋 Salom! Bot sozlamalarini boshqarish\n\nNimani qilishni xoxlaysiz?",
            reply_markup=reply_markup
        )
    elif query.data.startswith("del_time_"):
        time_str = query.data.replace("del_time_", "")
        remove_publish_time(time_str)

        # Vaqt o'chirilganda schedulerni yangilash
        from scheduler import schedule_post_publication
        from database import get_publish_times
        all_times = get_publish_times()
        schedule_post_publication(all_times)

        await show_times(query, context)
    elif query.data == "publish_poll":
        await publish_poll(query, context)
    elif query.data == "cancel_poll":
        await cancel_poll(query, context)
    elif query.data.startswith("publish_"):
        try:
            post_id = int(query.data.replace("publish_", ""))
            await publish_post(post_id, context)
            await query.answer("✅ Post kanalga yuborildi!")
            await show_queue(query, context)
        except ValueError:
            await query.answer("❌ Xato", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Xato: {str(e)}", show_alert=True)
            logger.error(f"Publish xatosi: {e}")
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
    elif query.data.startswith("regen_topic_"):
        post_id = int(query.data.replace("regen_topic_", ""))
        post_data = pending_posts.get(post_id)
        if post_data:
            try:
                await query.edit_message_text("⏳ Yangi post generatsiya qilinmoqda...")
                new_post = generate_post(post_data['title'])
                post_data['content'] = new_post

                keyboard = [
                    [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                    [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"refine_topic_{post_id}")],
                    [InlineKeyboardButton("🔄 Qayta generatsiya", callback_data=f"regen_topic_{post_id}")],
                    [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
                ]

                await query.edit_message_text(
                    f"📝 Mavzu: {post_data['title']}\n\n{new_post}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                reset_inactivity_timeout(query.from_user.id)
                add_inactivity_timeout(query.from_user.id, lambda: auto_publish_pending(post_id, context))
            except Exception as e:
                await query.edit_message_text(f"❌ Xato: {str(e)}")
    elif query.data.startswith("delete_topic_"):
        post_id = int(query.data.replace("delete_topic_", ""))
        if post_id in pending_posts:
            del pending_posts[post_id]
            reset_inactivity_timeout(query.from_user.id)
            await query.edit_message_text("❌ Post o'chirildi")
            await query.answer("Post o'chirildi", show_alert=True)
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
    elif query.data == "publish_poll":
        await publish_poll(query, context)
    elif query.data == "cancel_poll":
        await cancel_poll(query, context)
    elif query.data == "create_test":
        user_state[query.from_user.id] = "waiting_test_title"
        await query.edit_message_text("📝 Test sarlavhasini kiriting:")
    elif query.data.startswith("view_test_"):
        test_id = int(query.data.replace("view_test_", ""))
        await show_test_for_user(query, context, test_id)
    elif query.data.startswith("test_answer_"):
        parts = query.data.replace("test_answer_", "").split("_")
        test_id = int(parts[0])
        q_idx = int(parts[1])
        a_idx = int(parts[2])
        await handle_test_answer(query, context, test_id, q_idx, a_idx)
    elif query.data.startswith("test_stats_"):
        test_id = int(query.data.replace("test_stats_", ""))
        await show_test_stats(query, context, test_id)
    elif query.data.startswith("del_test_"):
        test_id = int(query.data.replace("del_test_", ""))
        from database import delete_test
        delete_test(test_id)
        await show_tests_menu(query, context)

async def show_times(query, context: ContextTypes.DEFAULT_TYPE):
    """Chop etish vaqtlarini ko'rsatish"""
    times = get_publish_times()
    text = "⏰ Chop etish vaqtlari:\n\n"

    keyboard = []
    for t in times:
        keyboard.append([
            InlineKeyboardButton(f"🗑️ {t}", callback_data=f"del_time_{t}")
        ])

    keyboard.append([InlineKeyboardButton("➕ Vaqt qo'sh", callback_data="add_time")])
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    text += "\n".join(times) if times else "Vaqtlar o'rnatilmagan"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_topics(query, context: ContextTypes.DEFAULT_TYPE):
    """Mavzularni ko'rsatish"""
    topics = get_topics()
    text = "📚 Mavzular:\n\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Generatsiya", callback_data="generate_topic")],
        [InlineKeyboardButton("➕ Mavzu qo'sh", callback_data="add_topic")]
    ]
    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    if topics:
        for i, topic in enumerate(topics, 1):
            text += f"{i}. {topic['text']}\n"
    else:
        text += "Mavzular yo'q"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_tax_reports(query, context: ContextTypes.DEFAULT_TYPE):
    """Soliq hisobotlarini ko'rsatish"""
    reports = get_tax_reports()
    text = "📋 Soliq Hisobotlari\n\n"

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

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_queue(query, context: ContextTypes.DEFAULT_TYPE):
    """Chop etish navbatini ko'rsatish"""
    queue = get_queue()
    text = "📋 Chop etish navbati:\n\n"

    keyboard = []

    if not queue:
        text += "Navbat bo'sh"
    else:
        for i, post in enumerate(queue, 1):
            post_id = post.get('id')
            post_title = post.get('title', 'Post')[:20]
            keyboard.append([
                InlineKeyboardButton(
                    f"#{i} - {post_title}",
                    callback_data=f"publish_{post_id}"
                )
            ])
            text += f"{i}. {post.get('title', 'Post')}\n"

    keyboard.append([InlineKeyboardButton("🏠 Orqaga", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_auto_publish_status(query, context: ContextTypes.DEFAULT_TYPE):
    """Avtomatik chop etish status"""
    from scheduler import scheduler
    times = get_publish_times()
    queue = get_queue()

    text = "📊 Avtomatik Chop Etish Status\n\n"
    text += "⏰ Belgilangan Vaqtlar:\n"

    if times:
        for t in times:
            text += f"• {t}\n"
    else:
        text += "• Vaqtlar o'rnatilmagan\n"

    text += f"\n📝 Navbatda: {len(queue)} ta post\n"
    scheduler_status = "✅ Ishlamoqda" if scheduler.running else "❌ To'xtab turgan"
    text += f"🔄 Scheduler: {scheduler_status}\n"

    keyboard = [[InlineKeyboardButton("🏠 Orqaga", callback_data="back")]]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def publish_post(post_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Postni kanalga chop etish"""
    try:
        queue = get_queue()
        post = next((p for p in queue if p.get('id') == post_id or str(p.get('id')) == str(post_id)), None)

        if post:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=post.get('content', post.get('title', 'Post'))
            )
            remove_from_queue(post_id)
            logger.info(f"Post #{post_id} kanalga chop etildi")
        else:
            logger.warning(f"Post #{post_id} navbatda topilmadi")
    except Exception as e:
        logger.error(f"Chop etishda xato: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni qabul qilish"""
    if update.effective_user.id != ADMIN_USER_ID:
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Poll yaratish
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) >= 5 and lines[0].endswith("?"):
        await create_poll(update, context)
        return

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

    elif user_state.get(user_id) == "waiting_time":
        if add_publish_time(text):
            # Yangi vaqt qo'shilganda schedulerni yangilash
            from scheduler import schedule_post_publication
            from database import get_publish_times
            all_times = get_publish_times()
            schedule_post_publication(all_times)

            await update.message.reply_text(f"✅ Vaqt qo'shildi: {text}")
        else:
            await update.message.reply_text(f"❌ Bu vaqt allaqachon mavjud")
        user_state[user_id] = None
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
            # Yangi vaqt qo'shilganda schedulerni yangilash
            from scheduler import schedule_post_publication
            from database import get_publish_times
            all_times = get_publish_times()
            schedule_post_publication(all_times)

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
                "id": post_id,
                "title": text,
                "content": post,
                "status": "waiting_approval"
            }

            keyboard = [
                [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"refine_topic_{post_id}")],
                [InlineKeyboardButton("🔄 Qayta generatsiya", callback_data=f"regen_topic_{post_id}")],
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

    elif user_state.get(user_id) == "waiting_generate_topic":
        category = text
        if category in TOPIC_CATEGORIES:
            topic_text = TOPIC_CATEGORIES[category]
        else:
            topic_text = category

        await update.message.reply_text(f"⏳ '{topic_text}' mavzusiga oid yangilik yig'ilyapti...")

        try:
            post = generate_post(topic_text)
            post_id = len(pending_posts) + 1
            pending_posts[post_id] = {
                "id": post_id,
                "title": topic_text,
                "content": post,
                "status": "waiting_approval"
            }

            keyboard = [
                [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"refine_topic_{post_id}")],
                [InlineKeyboardButton("🔄 Qayta generatsiya", callback_data=f"regen_topic_{post_id}")],
                [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
            ]

            await update.message.reply_text(
                f"📝 Mavzu: {topic_text}\n\n{post}",
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
            post_id = int(state.replace("editing_", ""))
            post_data = pending_posts.get(post_id)
            if post_data:
                post_data['content'] = text

                keyboard = [
                    [InlineKeyboardButton("✅ Chop et", callback_data=f"approve_topic_{post_id}")],
                    [InlineKeyboardButton("✏️ Yana tahrirlash", callback_data=f"refine_topic_{post_id}")],
                    [InlineKeyboardButton("🔄 Qayta generatsiya", callback_data=f"regen_topic_{post_id}")],
                    [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
                ]

                await update.message.reply_text(
                    f"📝 Tahrirlangan post:\n\n{text}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                reset_inactivity_timeout(user_id)
                add_inactivity_timeout(user_id, lambda: auto_publish_pending(post_id, context))
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
                        [InlineKeyboardButton("🔄 Qayta generatsiya", callback_data=f"regen_topic_{post_id}")],
                        [InlineKeyboardButton("❌ O'chirish", callback_data=f"delete_topic_{post_id}")],
                    ]

                    await update.message.reply_text(
                        f"📝 Yangilangan post:\n\n{refined_post}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    reset_inactivity_timeout(user_id)
                    add_inactivity_timeout(user_id, lambda: auto_publish_pending(post_id, context))
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

    # Scheduler ni ishga tushirish va publish vaqtlarini o'rnatish
    data = load_database()
    publish_times = data.get('publish_times', ['09:00', '15:00'])
    start_scheduler(app)

    from scheduler import schedule_post_publication
    schedule_post_publication(publish_times)

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
