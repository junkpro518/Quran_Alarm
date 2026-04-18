# Quran Alarm Bot — Design Spec
**Date:** 2026-04-18  
**Status:** Approved

---

## المشروع

بوت تيليجرام يُذكّر المستخدم بورد القرآن اليومي من قاعدة بيانات Notion، ويرسل تذكيرات كل 30 دقيقة من الظهر حتى منتصف الليل حتى يضغط "تم".

---

## المتطلبات

| المتطلب | التفاصيل |
|---------|----------|
| وقت البداية | 12:00 ظهراً يومياً |
| التكرار | كل 30 دقيقة |
| وقت التوقف | 12:00 منتصف الليل (حتى لو لم يضغط تم) |
| زر التأكيد | "✅ تم" في كل رسالة |
| مصدر البيانات | Notion DB: 🕌 الختمة السنوية |
| نظام التشغيل | VPS عبر systemd |

---

## هيكل قاعدة بيانات Notion

- **Database ID:** `32b39125-abb1-80b7-be54-e59e45a2fed4`
- **الورد** (title): أرقام الصفحات مثل `"37-38"`
- **التاريخ** (text): تاريخ هجري بصيغة `"DD/شهر/YYYY"` مثل `"20/شوال/1447"`
- **تم** (checkbox): حالة الإنجاز

---

## المعمارية

```
Quran_Alarm/
├── bot.py                  # تشغيل البوت + callback handlers
├── scheduler.py            # APScheduler — جدولة المهام اليومية
├── notion_service.py       # قراءة/تحديث Notion API
├── hijri_utils.py          # تحويل التاريخ الميلادي → هجري
├── config.py               # متغيرات البيئة من .env
├── requirements.txt
├── .env.example
└── quran-alarm.service     # Systemd service للـ VPS
```

---

## تدفق العمل

```
[12:00 ظهراً] 
    ↓ APScheduler يطلق مهمة اليوم
    ↓ notion_service: يجلب ورد اليوم عبر التاريخ الهجري
    ↓ إذا كان "تم" = True في Notion → لا إرسال (تم القراءة مسبقاً)
    ↓ scheduler: يجدول إرسال كل 30 دقيقة
    
[كل 30 دقيقة]
    ↓ bot.py: يرسل رسالة "ورد اليوم: X-Y" + زر "✅ تم"
    
[عند ضغط "✅ تم"]
    ↓ callback_handler: يُوقف مهام اليوم
    ↓ notion_service: يحدّث حقل "تم" = True
    ↓ bot.py: يرسل تأكيد
    
[12:00 منتصف الليل]
    ↓ APScheduler: يلغي جميع مهام اليوم تلقائياً
```

---

## التفاصيل التقنية

### تحويل التاريخ الهجري
- مكتبة: `hijri-converter`
- تحويل `datetime.date.today()` → `Hijri` ← تنسيق `"DD/شهر/YYYY"`
- أسماء الأشهر العربية: محرم، صفر، ربيع الأول، ربيع الآخر، جمادى الأولى، جمادى الآخرة، رجب، شعبان، رمضان، شوال، ذو القعدة، ذو الحجة

### Notion API
- مكتبة: `notion-client`
- استعلام بـ filter على حقل `"التاريخ"` (rich_text equals اليوم الهجري)
- تحديث checkbox `"تم"` عند الضغط

### Telegram Bot
- مكتبة: `python-telegram-bot` v20+ (async)
- Inline keyboard مع `callback_data = "done_YYYY-MM-DD"` (تاريخ ميلادي للتعرف على اليوم)

### إدارة الحالة
- `dict` في الذاكرة: `{"YYYY-MM-DD": {"done": bool, "job_ids": [...]}}`
- لا حاجة لقاعدة بيانات (استخدام شخصي — مستخدم واحد)

### APScheduler
- `BackgroundScheduler` مع `timezone="Asia/Riyadh"`
- مهمة يومية ثابتة: `cron` على 12:00 ظهراً
- مهام التذكير: `interval` كل 30 دقيقة، تُلغى عند الضغط أو منتصف الليل

---

## معالجة الأخطاء

| الحالة | السلوك |
|--------|--------|
| لا يوجد ورد لليوم في Notion | تسجيل خطأ، لا إرسال |
| فشل Notion API | إعادة المحاولة مرة واحدة، ثم تسجيل خطأ |
| تاريخ هجري غير موجود في DB | لا إرسال، تسجيل تحذير |

---

## النشر على VPS

```ini
# quran-alarm.service
[Unit]
Description=Quran Alarm Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/quran-alarm
ExecStart=/opt/quran-alarm/venv/bin/python bot.py
Restart=always
EnvironmentFile=/opt/quran-alarm/.env

[Install]
WantedBy=multi-user.target
```

---

## المتغيرات المطلوبة (.env)

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
NOTION_TOKEN=...
NOTION_DATABASE_ID=32b39125abb180b7be54e59e45a2fed4
TIMEZONE=Asia/Riyadh
```

---

## التحقق من الصحة

1. تشغيل `python bot.py` محلياً والتأكد من بدء الـ scheduler
2. اختبار يدوي: تشغيل مهمة إرسال مباشرة بتاريخ اليوم
3. التأكد من ظهور الزر "✅ تم" وعمله
4. التحقق من تحديث نوشن بعد الضغط
5. اختبار التوقف التلقائي عند منتصف الليل
