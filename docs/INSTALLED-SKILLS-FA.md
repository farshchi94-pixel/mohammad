# Skillهای نصب‌شده برای Signal Hub

این پروژه از چهار مجموعهٔ تخصصی برای تحقیق وب، طراحی رابط، ساده‌سازی کد و بررسی امنیتی استفاده می‌کند. فایل‌های اجرایی Skillها در مسیر مشترک Manus نصب شده‌اند و وابستگی مستقیم به کد runtime پروژه ندارند.

## Firecrawl CLI

منبع: [firecrawl/cli](https://github.com/firecrawl/cli)

Skillهای `firecrawl`، `firecrawl-search`، `firecrawl-scrape`، `firecrawl-crawl`، `firecrawl-map`، `firecrawl-interact`، `firecrawl-monitor`، `firecrawl-parse`، `firecrawl-download`، `firecrawl-agent`، `firecrawl-research-index`، `firecrawl-developer-index` و `firecrawl-alexandria` نصب شده‌اند. CLI نسخهٔ `1.26.24` نیز نصب است.

برای استفاده، ابتدا `firecrawl login` را اجرا کن یا `FIRECRAWL_API_KEY` را در محیط قرار بده. خروجی‌های محلی را در `.firecrawl/` نگه دار و آن پوشه را commit نکن.

## UI/UX Pro Max

منبع: [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)

Skillهای `ui-ux-pro-max`، `ui-styling`، `design-system`، `design`، `brand` و `banner-design` نصب شده‌اند. Skill رسمی `slides` پروژه حفظ شده و با نسخهٔ خارجی جایگزین نشده است. CLI `uipro` نسخهٔ `2.15.0` نیز نصب است.

Design System پروژه در [design-system/signal-hub/MASTER.md](../design-system/signal-hub/MASTER.md) ذخیره شده و باید قبل از تغییرات بصری خوانده شود. جست‌وجوی مستقیم نمونه:

```bash
python3 /home/ubuntu/skills/ui-ux-pro-max/scripts/search.py "crypto trading analytics" --design-system
```

## Ponytail

منبع: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)

Skillهای `ponytail`، `ponytail-audit`، `ponytail-debt`، `ponytail-gain`، `ponytail-help` و `ponytail-review` نصب شده‌اند. Ponytail برای کوچک نگه‌داشتن تغییرات و `ponytail-audit` برای گزارش read-only کل مخزن است. فعال‌سازی آن فقط با درخواست صریح کاربر انجام شود؛ audit کامل نباید بدون درخواست اجرا شود.

## Security Audit

منبع: [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)

Skill `security-audit` با منابع روش‌شناسی، schema گزارش و validatorهای داخلی نصب شده است. تست‌های داخلی منبع با موفقیت اجرا شدند. این Skill در حالت عادی فقط راهنمایی می‌کند؛ اجرای full audit یا نوشتن گزارش امنیتی نیازمند درخواست صریح audit/pen-test است.

## وضعیت اعتبارسنجی

همهٔ Skillهای نصب‌شده با `quick_validate.py` بررسی شدند. تست‌های validator امنیتی Cloudflare نیز موفق بودند. Firecrawl احراز هویت نشده است؛ نصب CLI موفق است اما اجرای scrape/search تا زمان `firecrawl login` یا تنظیم API key انجام نمی‌شود.
