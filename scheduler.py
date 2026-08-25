import logging
import asyncio
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# O'zbekiston vaqt mintaqasini belgilaymiz
TIMEZONE = pytz.timezone("Asia/Tashkent")
scheduler = BackgroundScheduler(timezone=TIMEZONE)

monitor_callback = None
app_context = None

def set_monitor_callback(callback):
    """Monitoring callback ni set qilish"""
    global monitor_callback
    monitor_callback = callback

def set_app_context(context):
    """Bot contextini set qilish"""
    global app_context
    app_context = context

def _send_telegram_msg(chat_id, text, parse_mode=None):
    """Xabarlarni xavfsiz yuborish uchun yordamchi funksiya"""
    global app_context
    if not app_context:
        logger.error("Xabar yuborilmadi: app_context mavjud emas!")
        return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        kwargs = {"chat_id": chat_id, "text": text}
        if parse_mode:
            kwargs["parse_mode"] = parse_mode
        loop.run_until_complete(app_context.bot.send_message(**kwargs))
        loop.close()
    except Exception as e:
        logger.error(f"Telegram xabar yuborishda xatolik: {e}")

def schedule_post_publication(publish_times: list):
    """Belgilangan vaqtlarda postlarni chop etish"""
    for time_str in publish_times:
        try:
            hour, minute = map(int, time_str.split(':'))
            job_id = f'publish_{time_str}'
            if not any(job.id == job_id for job in scheduler.get_jobs()):
                scheduler.add_job(
                    func=check_and_publish,
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    timezone=TIMEZONE,
                    id=job_id,
                    replace_existing=True
                )
                logger.info(f"Scheduler qo'shildi: {time_str}")
        except Exception as e:
            logger.error(f"Scheduler qo'shishda xato: {e}")

def check_and_publish():
    """Navbatdagi postlarni chop etish"""
    from database import get_queue, remove_from_queue
    from config import TELEGRAM_CHANNEL_ID

    queue = get_queue()
    logger.info(f"Chop etish vaqti! Navbatda {len(queue)} post bor")

    if queue:
        post = queue[0]
        text = post.get('content', post.get('title', 'Post'))
        _send_telegram_msg(TELEGRAM_CHANNEL_ID, text)
        remove_from_queue(post['id'])
        logger.info(f"Post #{post['id']} kanalga chop etildi")

def schedule_channel_monitor():
    """Har 5 minutda kanaldan ma'lumot tekshirish"""
    if not any(job.id == 'monitor_channel' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=monitor_channel,
            trigger='interval',
            minutes=5,
            id='monitor_channel',
            replace_existing=True
        )
        logger.info("Kanal monitoring scheduled - har 5 minutda tekshirish")

def monitor_channel():
    """Kanaldan ma'lumot olish"""
    global monitor_callback
    if monitor_callback:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitor_callback())
            loop.close()
        except Exception as e:
            logger.error(f"Monitoring xatosi: {e}")

def schedule_tax_reminders(context):
    """Soliq hisobotlari reminderslarini schedule qilish"""
    if not any(job.id == 'tax_reminder' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=send_tax_reminders,
            trigger='cron',
            hour=9,
            minute=0,
            timezone=TIMEZONE,
            id='tax_reminder',
            replace_existing=True
        )
        logger.info("Soliq hisobotlari reminder scheduled - har kun 09:00 da")

def send_tax_reminders():
    """Soliq hisobotlari reminderslarini yuborish"""
    from tax_reports import get_today_reminders
    from config import ADMIN_USER_ID

    reminders = get_today_reminders()
    if reminders:
        message = "📋 *Soliq Hisobotlari Ogohlantirish*\n\n"
        for reminder in reminders:
            message += reminder['message'] + "\n\n"
        _send_telegram_msg(ADMIN_USER_ID, message, parse_mode="Markdown")
        logger.info(f"Soliq reminderlari yuborildi: {len(reminders)} ta")

# --- O'CHIRIB YUBORILGAN FUNKSIYALAR QAYTA QO'SHILDI ---
def add_inactivity_timeout(user_id: int, callback):
    """1 soat inaktivlikdan so'ng avtomatik chop etish"""
    job_id = f'timeout_{user_id}'

    if any(job.id == job_id for job in scheduler.get_jobs()):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        func=callback,
        trigger='date',
        run_date=datetime.now() + timedelta(hours=1),
        id=job_id,
        replace_existing=True
    )
    logger.info(f"Inaktivlik timeout qo'shildi: {user_id}")

def reset_inactivity_timeout(user_id: int):
    """Timeout ni reset qilish (yangi amal bajarilganda)"""
    job_id = f'timeout_{user_id}'
    if any(job.id == job_id for job in scheduler.get_jobs()):
        scheduler.remove_job(job_id)
    logger.info(f"Timeout reset qilindi: {user_id}")
# --------------------------------------------------------

def schedule_daily_greeting(context):
    """Har kun ertalab salomlashish"""
    if not any(job.id == 'daily_greeting' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=send_daily_greeting,
            trigger='cron',
            hour=7,
            minute=0,
            timezone=TIMEZONE,
            id='daily_greeting',
            replace_existing=True
        )
        logger.info("Salomlashish scheduled - har kun 07:00 da (Asia/Tashkent)")

def schedule_friday_message(context):
    """Har juma kuni juma muborak xabari"""
    if not any(job.id == 'friday_message' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=send_friday_message,
            trigger='cron',
            day_of_week='fri',
            hour=7,
            minute=0,
            timezone=TIMEZONE,
            id='friday_message',
            replace_existing=True
        )
        logger.info("Juma xabari scheduled - har juma 07:00 da (Asia/Tashkent)")

def send_daily_greeting():
    """Ertalab salomlashish"""
    from config import TELEGRAM_CHANNEL_ID
    message = """☀️ Assalomu alaykum!

Yangi kun yangi imkoniyatlar keltiradi! 💪
Sizga ishda muvaffaqiyat va barcha ishlaringizda omad tilaymiz! 🎯
Keling, shu kunni qimmatli qilaylik! 🚀"""
    _send_telegram_msg(TELEGRAM_CHANNEL_ID, message)
    logger.info("Salomlashish xabari kanalga yuborildi")

def send_friday_message():
    """Juma xabari"""
    from config import TELEGRAM_CHANNEL_ID
    message = """🌙 Juma Muborak! 🌙

Juma - barokat va yaxshi niyatlar kuni! 🤲
Ushbu muborak kunni oilangiz, do'stlaringiz va hamkasblaringiz bilan birdamlikda o'tkazing.
Hammangizga juma muborak! 💚

#JumaMuborak #Baraka"""
    _send_telegram_msg(TELEGRAM_CHANNEL_ID, message)
    logger.info("Juma xabari kanalga yuborildi")

def start_scheduler(context=None):
    """Schedulerni ishga tushirish"""
    global app_context
    if context:
        app_context = context

    if not scheduler.running:
        scheduler.start()
        schedule_channel_monitor()
        if context:
            schedule_tax_reminders(context)
            schedule_daily_greeting(context)
            schedule_friday_message(context)
        logger.info("Scheduler ishga tushdi")

def stop_scheduler():
    """Schedulerni to'xtatish"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler to'xtadi")
