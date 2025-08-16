# Environ News+ (FA)

وب‌سایت استاتیک برای گردآوری خودکار اخبار محیط‌زیست، آب، فاضلاب، نفت/گاز/پتروشیمی و **مناقصه‌ها** از فیدهای RSS و انتشار در GitHub Pages.

— ساخته شده: 2025-08-16T13:17:21.830787Z

## ایده
- تمام فیدها در `feeds.yaml` تعریف می‌شوند.
- اسکریپت پایتون (`scripts/build.py`) فیدها را می‌خواند، موارد تکراری را حذف می‌کند و صفحات HTML را با Jinja2 می‌سازد.
- GitHub Actions روزانه اجرا می‌شود و خروجی را روی شاخه‌ی `gh-pages` می‌فرستد.

## شروع سریع
1) روی دکمه **New repository** در گیت‌هاب یک ریپو بسازید (مثلاً `environ-news-plus`).
2) این فایل‌ها را پوش کنید (یا زیپ را از چت دانلود و آپلود کنید).
3) در تب **Settings → Pages**، حالت **Deploy from a branch** را انتخاب کنید و `gh-pages` را به عنوان شاخه‌ی انتشار بگذارید.
4) تب **Actions** را باز کنید تا اجازه اجرای Workflow داده شود (در اولین اجرا ممکن است لازم باشد Enable کنید).

## پیکربندی فیدها
- فایل `feeds.yaml` را باز کنید و URL فیدهای موردنظر خود را اضافه/حذف کنید.
- دسته‌ها: `environment`, `water`, `wastewater`, `oil_gas_petrochem`, `tenders`.

## اجرای محلی
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py
# خروجی در پوشه site/ ساخته می‌شود
python -m http.server -d site 8080
```

## برنامه زمان‌بندی
- فایل `.github/workflows/build.yml` هر ۶ ساعت یک‌بار اجرا می‌شود (قابل تغییر).

## سفارشی‌سازی
- استایل‌ها در `templates/styles.css` هستند.
- لوگو/عنوان را در `templates/partials/header.html` و `config_site.json` تغییر دهید.

## مجوز
- MIT
