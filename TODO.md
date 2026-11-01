# Kraken landing page

صفحه فعلی از ایدهٔ قبلی مارکتیم به یک لندینگ‌پیج کامل برای پلتفرم ترید رمزارز Kraken به‌روزرسانی شده است. ساختار شامل Hero با داشبورد پورتفولیو، شبکهٔ تیکرها و swap widget، قیمت‌گذاری، بخش Why Us، CTA و Footer است.

تمام انیمیشن‌ها با Framer Motion و رندرهای تعاملی DotMatrix و FlowGradient اجرا می‌شوند. دارایی‌های تصویری مستقیماً از URLهای رسمی `qclay.design/lovable/kraken/` بارگذاری می‌شوند و نسخهٔ دسکتاپ و موبایل هر سکشن در کد پیاده‌سازی شده است.

## ادامهٔ موتور تحلیل و بررسی داشبورد

- [x] cache پایدار فشرده برای کندل‌ها با دریافت incremental فقط از آخرین timestamp و fallback به bootstrap.
- [x] ثبت cache hit/miss، درخواست‌های incremental و زمان آخرین به‌روزرسانی در خروجی اسکن.
- [x] به‌روزرسانی Workflow اسکن برای ذخیرهٔ cache بین اجراها بدون انتشار آن در سایت.
- [x] اجرای تست‌های deterministic برای merge، حذف duplicate و بازیابی cache خراب.
- [x] بررسی ویدئوی مرجع از نظر تناسب با داشبورد فارسی Signal Hub.
- [x] گرفتن screenshot از داشبورد پس از اجرای تغییرات.

## ادغام ATLAS QUANT و DayTraderSkill نسخهٔ اصلی

- [x] ادغام ماژول `DayTraderSkill` با فیلتر روند EMA55/EMA200، شرط ADX14 بزرگ‌تر از ۲۰، RSI14، منطقهٔ بدون معاملهٔ CHOP14 بالاتر از ۶۱٫۸ و ATR14.
- [x] اتصال `BacktestEngine` به cache افزایشی کندل‌های Signal Hub و تولید `atlas.json` با وضعیت `PAPER ONLY` و `real_orders_enabled=false`.
- [x] پیاده‌سازی حد ضرر پویا با ATR، هدف ثابت بر اساس R و انتقال حد ضرر به نقطهٔ ورود پس از رسیدن قیمت به ۵۰٪ مسیر هدف؛ پشتیبانی short در موتور با `allow_short=false` پیش‌فرض.
- [x] اجرای خودکار ATLAS پس از مرحلهٔ دریافت/ادغام کندل‌ها در `scan.py` و افزودن خروجی به اعتبارسنجی و workflow انتشار.
- [x] افزودن تب فارسی `ATLAS` به داشبورد و نمایش شاخص‌های EMA/ADX/RSI/CHOP/ATR، سرمایه، ریسک، کارمزد، بازده، نرخ برد، افت سرمایه، Profit Factor و تعداد Breakeven هر نماد.
- [x] افزودن تست‌های deterministic برای DayTraderSkill، بک‌تست، cache adapter و ردکردن دادهٔ ناکافی.
- [ ] اجرای workflow اسکن زنده و بررسی گزارش ATLAS روی دادهٔ بازار تازه؛ این مرحله به دسترسی موفق workflow به APIهای عمومی نیاز دارد.
