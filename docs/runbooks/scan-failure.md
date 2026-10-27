# Runbook: خطای اسکن Signal Hub

**یعنی چه؟** اجرای `scan` نتوانسته داده‌های بازار را بخواند، خروجی JSON معتبر بسازد یا خروجی‌ها را به ریشهٔ سایت commit کند.

**اول بررسی کن:** اجرای آخر را با `gh run view <RUN_ID> --repo farshchi94-pixel/mohammad --log-failed` بخوان و Step `Run scanner` و `Validate output files` را بررسی کن.

**چک‌های سریع:**

1. Secretهای اختیاری `TELEGRAM_TOKEN`، `TELEGRAM_CHAT_ID` و `HELIUS_API_KEY` را بررسی کن؛ هیچ‌کدام را در log چاپ نکن.
2. خطای rate limit یا provider را با retryهای داخل `scan.py` و وضعیت APIهای عمومی بررسی کن.
3. اگر خطای `missing` یا `stale` دیدی، وجود فایل‌های JSON و مقدار `updated` را بررسی کن.
4. بعد از اصلاح، فقط Workflow `scan` را دستی دوباره اجرا کن؛ دادهٔ تولیدشده باید در commit بعدی دیده شود.

**معیار سلامت:** Step اعتبارسنجی باید event JSON با `status=ok` بنویسد، فایل‌ها باید timestamp تازه داشته باشند و Pages باید پس از commit داده‌ها دوباره smoke test شود.
