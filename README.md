# 📱 Telegram Soliq Bot - Multi-Agent Post Generation Sistema

Professional soliq va bухgalteriya bo'yicha Telegram kanalga avtomatik post yaratuvchi bot. AI orqali yangilik generatsiya qiladi va belgilangan vaqtda avtomatik chop etadi.

## 🎯 Asosiy Xususiyatlar

### 1. **🔄 Avtomatik Post Generatsiya**
- ✅ AI (Google Gemini) orqali mavzu bo'yicha post yaratish
- ✅ Soha bo'yicha kategorilashtirilgan mavzular (soliq, bухgalteriya, moliya, xorijiy savdo, korporativ huquq)
- ✅ Post tahrirlash va qayta generatsiya imkoniyati
- ✅ 1 soat inaktivlikdan so'ng avtomatik navbatga qo'shish

### 2. **⏰ Avtomatik Chop Etish**
- ✅ Belgilangan vaqtlarda postlarni avtomatik chop etish
- ✅ Vaqtlar dinamik o'zgartirilishi
- ✅ Scheduler status monitoring
- ✅ Navbatdagi postlarni boshqarish

### 3. **📋 Soliq Hisobotlari Reminder**
- ✅ Oylik soliq hisobotlari uchun reminder
- ✅ Weekend va bayram kunlarini hisobga olish
- ✅ To'lov va hisobot sanalarini alohida o'rnatish
- ✅ Har kun ertalab reminder yuborish

### 4. **📊 Kanal Monitoring**
- ✅ Manba kanaldan yangi xabarlarni avtomatik tekshirish (har 5 minutda)
- ✅ Yangi xabarni o'zgartirib navbatga qo'shish
- ✅ Admin tasdiqini kutish

### 5. **📢 Avtomatik Xabarlar**
- ✅ Har kun ertalab salomlashish (07:00)
- ✅ Har juma kuni juma muborak xabari (juma 07:00)

## 🛠️ O'rnatish

### Talablar
- Python 3.8+
- pip

### Qadam-qadam

1. **Repositoriyani klonlash:**
```bash
git clone <repo-url>
cd telegram-bot-soliq-v2
```

2. **Virtual Environment qo'shish:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. **Dependensiyalarni o'rnatish:**
```bash
pip install -r requirements.txt
```

4. **`.env` faylni tayyorlash:**
```bash
cp .env.example .env
```

5. **`.env` faylini tahrirlash (o'z valueleringiz bilan):**
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=your_channel_id_here
GEMINI_API_KEY=your_gemini_api_key_here
ADMIN_USER_ID=your_user_id_here
```

6. **Botni ishga tushirish:**
```bash
python bot.py
```

## 📖 Foydalanish

### Admin Panel
Bot boshlanishida asosiy menyuda quyidagi tugmalar mavjud:

- **⏰ Chop etish vaqtlari** - Post chop etish vaqtlarini o'rnatish
- **📚 Mavzular** - Mavzular bo'yicha post generatsiya qilish
- **📰 Manba ma'lumotlari** - Kanaldan yangi xabarlarni tekshirish
- **📋 Soliq hisobotlari** - Soliq hisobotlarini boshqarish
- **📢 Kanal sozlash** - Manba kanal ID'sini o'rnatish
- **📋 Navbat** - Chop etish navbatini ko'rish
- **📊 Avtomatik Chop Status** - Scheduler va vaqtlarni monitoring qilish

### Mavzular bo'limi
1. **🔄 Generatsiya** - Soha bo'yicha yangilik generatsiya qilish
2. **➕ Mavzu qo'sh** - O'z mavzuingizni yozish

### Post Yaratish Jarayoni
1. Mavzu tanlagach, bot AI orqali post yaratadi
2. Post ko'rinadi va quyidagi tugmalar:
   - **✅ Chop et** - Postni navbatga qo'shish
   - **✏️ Tahrirlash** - Postni o'zingiz tahrirlash
   - **🔄 Qayta generatsiya** - Boshqa variant yaratish
   - **❌ O'chirish** - Postni o'chirish

3. **1 soat timeout** - Hech qanday amal bajarmasangiz, post avtomatik navbatga qo'shiladi

## 🔧 Konfiguratsiya

### Chop etish vaqtlari
Qo'shish: `⏰ Chop etish vaqtlari` → `➕ Vaqt qo'sh` → vaqt kiriting (masalan: 09:00)

### Soliq hisobotlari
Qo'shish: `📋 Soliq hisobotlari` → `➕ Hisobot qo'sh`
- Hisobot turi
- Hisobot sanasi (oyda)
- To'lov sanasi (oyda)

### Manba kanal
Qo'shish: `📢 Kanal sozlash` → kanal ID yoki @username

## 📁 Fayl Strukturasi

```
telegram-bot-soliq-v2/
├── bot.py                 # Asosiy bot logic
├── config.py              # Konfiguratsiya va environment variables
├── database.py            # Ma'lumotlarni saqlash (JSON)
├── ai_handler.py          # AI post generatsiya (Google Gemini)
├── scheduler.py           # Vaqt bo'yicha avtomatik amallar
├── channel_monitor.py     # Kanal monitoring
├── tax_reports.py         # Soliq hisobotlari boshqaruvi
├── requirements.txt       # Python dependensiyalari
├── .env.example           # Environment variables shabloni
└── bot_data.json          # Ma'lumotlarni saqlash faylı
```

## 🔐 Xavfsizlik

- Bot token va API key'ni `.env` faylida saqlang
- `.env` faylni `.gitignore`ga qo'shing
- Faqat admin ID'si bot bilan ishlashi mumkin
- Bot ma'lumotlari JSON'da saqlandi, encryption tavsiya etiladi

## 🐛 Muammolarni Hal Qilish

### Bot boshlanmayapti
```bash
# Xatolarni ko'rish uchun
python bot.py
```

### Post chop etilmayapti
- ✅ Scheduler ishlamoqda ekanligini tekshirish (`📊 Avtomatik Chop Status`)
- ✅ Navbatda post borligini tekshirish
- ✅ Vaqt to'g'ri o'rnatilganligini tekshirish

### Post generatsiya ishlamayapti
- ✅ GEMINI_API_KEY to'g'ri ekanligini tekshirish
- ✅ Internet aloqasini tekshirish
- ✅ Google Gemini API'ni tekshirish

## 📝 Dependencies

```
python-telegram-bot==22.8
google-generativeai==0.8.3
APScheduler==3.10.4
requests==2.31.0
beautifulsoup4==4.12.2
python-dotenv==1.0.0
```

## 🚀 O'rnatilgan Xususiyatlar (v2.0)

- ✅ AI orqali post generatsiya
- ✅ Avtomatik chop etish
- ✅ Soliq hisobotlari reminder
- ✅ Kanal monitoring
- ✅ Post tahrirlash va qayta generatsiya
- ✅ 1 soat timeout bilan avtomatik navbatga qo'shish
- ✅ Soha bo'yicha mavzular kategoriyasi

## 📞 Support

Muammolar yoki takliflar uchun repository issue'sini oching.

---

**Developed for soliq-related business automation** 💼
