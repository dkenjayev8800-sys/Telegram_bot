from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
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

def schedule_post_publication(publish_times: list):
    """Belgilangan vaqtlarda postlarni chop etish"""
    for time_str in publish_times:
        try:
            hour, minute = map(int, time_str.split(':'))

            if not any(job.id == f'publish_{time_str}' for job in scheduler.get_jobs()):
                scheduler.add_job(
                    func=check_and_publish,
                    trigger='cron',
                    hour=hour,
                    minute=minute,
                    id=f'publish_{time_str}',
                    replace_existing=True
                )
                logger.info(f"Scheduler qo'shildi: {time_str}")
        except Exception as e:
            logger.error(f"Scheduler qo'shishda xato: {e}")

def check_and_publish():
    """Navbatdagi postlarni chop etish"""
    global app_context
    from database import get_queue, remove_from_queue
    from config import TELEGRAM_CHANNEL_ID

    queue = get_queue()
    logger.info(f"Chop etish vaqti! Navbatda {len(queue)} post bor")

    if queue and app_context:
        post = queue[0]
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=post.get('content', post.get('title', 'Post'))
            ))
            loop.close()
            remove_from_queue(post['id'])
            logger.info(f"Post #{post['id']} kanalga chop etildi")
        except Exception as e:
            logger.error(f"Chop etishda xato: {e}")

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
            id='tax_reminder',
            replace_existing=True,
            kwargs={'context': context}
        )
        logger.info("Soliq hisobotlari reminder scheduled - har kun 09:00 da")

def send_tax_reminders(context):
    """Soliq hisobotlari reminderslarini yuborish"""
    global app_context
    from tax_reports import get_today_reminders
    from config import ADMIN_USER_ID

    reminders = get_today_reminders()

    if reminders and app_context:
        try:
            message = "📋 *Soliq Hisobotlari Ogohlantirish*\n\n"
            for reminder in reminders:
                message += reminder['message'] + "\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=message,
                parse_mode="Markdown"
            ))
            loop.close()
            logger.info(f"Soliq reminderlari yuborildi: {len(reminders)} ta")
        except Exception as e:
            logger.error(f"Reminder yuborish xatosi: {e}")

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

def start_scheduler(context=None):
    """Schedulerni ishga tushirish"""
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

def schedule_daily_greeting(context):
    """Har kun ertalab salomlashish"""
    if not any(job.id == 'daily_greeting' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=send_daily_greeting,
            trigger='cron',
            hour=7,
            minute=0,
            id='daily_greeting',
            replace_existing=True,
            kwargs={'context': context}
        )
        logger.info("Salomlashish scheduled - har kun 07:00 da")

def schedule_friday_message(context):
    """Har juma kuni juma muborak xabari"""
    if not any(job.id == 'friday_message' for job in scheduler.get_jobs()):
        scheduler.add_job(
            func=send_friday_message,
            trigger='cron',
            day_of_week=4,  # Juma (0=Dushanba, 4=Juma)
            hour=7,
            minute=0,
            id='friday_message',
            replace_existing=True,
            kwargs={'context': context}
        )
        logger.info("Juma xabari scheduled - har juma 07:00 da")

def send_daily_greeting(context):
    """Ertalab salomlashish"""
    global app_context
    from config import TELEGRAM_CHANNEL_ID

    message = """☀️ Assalomu alaykum!

Yangi kun yangi imkoniyatlar keltiradi! 💪

Sizga ishda muvaffaqiyat va barcha ishlaringizda omad tilaymiz! 🎯

Keling, shu kunni qimmatli qilaylik! 🚀"""

    try:
        if app_context:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message
            ))
            loop.close()
        logger.info("Salomlashish xabari yuborildi")
    except Exception as e:
        logger.error(f"Salomlashish xabari yuborish xatosi: {e}")

def send_friday_message(context):
    """Juma xabari"""
    global app_context
    from config import TELEGRAM_CHANNEL_ID

    message = """🌙 Juma Muborak! 🌙

Juma - barokat va yaxshi niyatlar kuni! 🤲

Ushbu muborak kunni oilangiz, do'stlaringiz va hamkasblaringiz bilan birdamlikda o'tkazing.

Hammangizga juma muborak! 💚

#JumaMuborak #Baraka"""

    try:
        if app_context:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message
            ))
            loop.close()
        logger.info("Juma xabari yuborildi")
    except Exception as e:
        logger.error(f"Juma xabari yuborish xatosi: {e}")
