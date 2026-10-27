# Runbook: خطای انتشار GitHub Pages

**یعنی چه؟** Workflow `deploy-pages` نتوانسته artifact استاتیک را روی Pages منتشر کند یا smoke test عمومی پاسخ موفق نگرفته است.

**اول بررسی کن:** اجرای آخر را با `gh run view <RUN_ID> --repo farshchi94-pixel/mohammad --log-failed` بخوان؛ سپس در `Settings → Pages` مطمئن شو Source روی `GitHub Actions` است.

**اقدام‌های معمول:**

1. اگر `Get Pages site failed` دیدی، Pages را برای مخزن فعال کن و Workflow را با `gh workflow run pages.yml --repo farshchi94-pixel/mohammad --ref main` دوباره اجرا کن.
2. اگر `Prepare static site` شکست خورد، وجود `index.html` و `config.json` در ریشهٔ مخزن را بررسی کن.
3. اگر smoke test شکست خورد، URL ثبت‌شده در خروجی `deploy-pages` و فایل `manus-routes.json` را بررسی کن.

**Rollback:** در صورت خرابی نسخهٔ منتشرشده، commit سالم قبلی را پیدا کن، یک revert معمولی روی `main` انجام بده و اجازه بده Workflow Pages همان commit را منتشر کند؛ force-push ممنوع است.

**مراقبت:** بعد از اصلاح، اجرای `deploy-pages` باید سبز شود و هر دو URL صفحهٔ اصلی و `manus-routes.json` باید HTTP 200 بدهند.
