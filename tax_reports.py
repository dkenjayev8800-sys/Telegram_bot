from datetime import datetime, timedelta
from database import load_database, save_database

# O'zbekistondagi bayram kunlari (YYYY-MM-DD format)
HOLIDAYS = [
    "2026-01-01",  # Yangi yil
    "2026-03-08",  # Ayollar kuni
    "2026-03-21",  # Navro'z
    "2026-09-01",  # Mustaqillik kuni
    "2026-12-08",  # Xotira va qadr etish kuni
]

def is_weekend_or_holiday(date: datetime.date) -> bool:
    """Shanba, yakshanba yoki bayram kun ekanligini tekshirish"""
    # Shanba (5) va yakshanba (6)
    if date.weekday() in [5, 6]:
        return True

    # Bayram kunlari
    if date.strftime('%Y-%m-%d') in HOLIDAYS:
        return True

    return False

def get_next_business_day(date: datetime.date) -> datetime.date:
    """Keyingi ish kunni olish"""
    current = date
    while is_weekend_or_holiday(current):
        current += timedelta(days=1)
    return current

def add_tax_report(name: str, report_day: int, payment_day: int) -> bool:
    """Soliq hisobot qo'shish (oylik kun: 1-31)"""
    data = load_database()
    if 'tax_reports' not in data:
        data['tax_reports'] = []

    data['tax_reports'].append({
        'name': name,
        'report_day': report_day,  # Oyda necha kuni (1-31)
        'payment_day': payment_day,  # Oyda necha kuni (1-31)
    })
    save_database(data)
    return True

def get_tax_reports() -> list:
    """Barcha soliq hisobotlarini olish"""
    data = load_database()
    return data.get('tax_reports', [])

def remove_tax_report(name: str) -> bool:
    """Soliq hisobotni o'chirish"""
    data = load_database()
    data['tax_reports'] = [t for t in data.get('tax_reports', []) if t['name'] != name]
    save_database(data)
    return True

def update_tax_report(name: str, edit_type: int, new_day: int) -> bool:
    """Soliq hisobotni yangilash (edit_type: 1=hisobot, 2=to'lov)"""
    data = load_database()
    for report in data.get('tax_reports', []):
        if report['name'] == name:
            if edit_type == 1:
                report['report_day'] = new_day
            elif edit_type == 2:
                report['payment_day'] = new_day
            save_database(data)
            return True
    return False

def get_today_reminders() -> list:
    """Bugungi reminderslar - oylik sanalar"""
    reports = get_tax_reports()
    today = datetime.now().date()
    tomorrow = (datetime.now() + timedelta(days=1)).date()

    reminders = []

    for report in reports:
        report_day = report['report_day']
        payment_day = report['payment_day']

        # Bugungi oyda report_day sana
        try:
            report_date = datetime(today.year, today.month, min(report_day, 31)).date()
        except ValueError:
            continue

        # Ertaga oyda report_day sana
        tomorrow_date = tomorrow
        try:
            tomorrow_report = datetime(tomorrow_date.year, tomorrow_date.month, min(report_day, 31)).date()
        except ValueError:
            tomorrow_report = None

        # Bugungi oyda payment_day sana
        try:
            payment_date = datetime(today.year, today.month, min(payment_day, 31)).date()
        except ValueError:
            continue

        # Ertaga oyda payment_day sana
        try:
            tomorrow_payment = datetime(tomorrow_date.year, tomorrow_date.month, min(payment_day, 31)).date()
        except ValueError:
            tomorrow_payment = None

        # Weekend/holiday tekshirish va keyingi ish kuniga ko'chirish
        if is_weekend_or_holiday(report_date):
            actual_report_date = get_next_business_day(report_date)
        else:
            actual_report_date = report_date

        if is_weekend_or_holiday(payment_date):
            actual_payment_date = get_next_business_day(payment_date)
        else:
            actual_payment_date = payment_date

        # Hisobot uchun 1 kun oldin
        if actual_report_date - timedelta(days=1) == today:
            original_info = f" (Asl: {actual_report_date.day})" if actual_report_date.day != report_day else ""
            reminders.append({
                'type': 'report_pre',
                'name': report['name'],
                'date': actual_report_date,
                'message': f"⚠️ *{report['name']}* hisobotining oxirgi kuni *ertaga* ({actual_report_date.day}-kuni){original_info}"
            })

        # Hisobot sanasining o'sha kuni
        if actual_report_date == today:
            original_info = f" (Asl: {report_day})" if actual_report_date.day != report_day else ""
            reminders.append({
                'type': 'report',
                'name': report['name'],
                'date': actual_report_date,
                'message': f"🔴 *{report['name']}* hisobot jo'natishning *oxirgi kuni bugun*! ({actual_report_date.day}-kuni){original_info}"
            })

        # To'lov uchun 1 kun oldin
        if actual_payment_date - timedelta(days=1) == today:
            original_info = f" (Asl: {actual_payment_date.day})" if actual_payment_date.day != payment_day else ""
            reminders.append({
                'type': 'payment_pre',
                'name': report['name'],
                'date': actual_payment_date,
                'message': f"⚠️ *{report['name']}* to'lovining oxirgi kuni *ertaga* ({actual_payment_date.day}-kuni){original_info}"
            })

        # To'lov sanasining o'sha kuni
        if actual_payment_date == today:
            original_info = f" (Asl: {payment_day})" if actual_payment_date.day != payment_day else ""
            reminders.append({
                'type': 'payment',
                'name': report['name'],
                'date': actual_payment_date,
                'message': f"🔴 *{report['name']}* to'lovining *oxirgi kuni bugun*! ({actual_payment_date.day}-kuni){original_info}"
            })

    return reminders


