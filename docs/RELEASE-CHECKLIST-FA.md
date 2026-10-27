# چک‌لیست انتشار Signal Hub

## قبل از انتشار

- [ ] `pnpm check` موفق است.
- [ ] تست‌های Vitest موفق هستند.
- [ ] `pnpm build:static` موفق است.
- [ ] فایل‌های JSON خروجی معتبر و بدون Secret هستند.
- [ ] Source در Settings → Pages روی `GitHub Actions` است.
- [ ] Secretهای لازم فقط در GitHub Actions ذخیره شده‌اند.

## هنگام انتشار

- [ ] Workflow `quality` سبز شده است.
- [ ] Workflow `deploy-pages` سبز شده است.
- [ ] Step `Public smoke test` پاسخ HTTP 200 گرفته است.
- [ ] اجرای `monitor-production` خطا ندارد.

## بعد از انتشار

- [ ] صفحهٔ اصلی سایت باز می‌شود.
- [ ] `manus-routes.json` با HTTP 200 قابل خواندن است.
- [ ] داده‌ها timestamp تازه دارند.
- [ ] در صورت خطا، از `docs/runbooks/pages-deploy-failure.md` یا `scan-failure.md` استفاده شود.

## Rollback

Rollback فقط با revert معمولی commit خراب انجام شود. Force-push ممنوع است. بعد از revert، موفقیت Pages و smoke test را دوباره بررسی کن.
