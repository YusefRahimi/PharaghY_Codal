## 0.3.0 — 2026-11-25

### مرحله ۵: API عمومی تمیز
- `__init__` و `__all__` پایدار و گروه‌بندی‌شده
- `docs/API.md` مرجع سریع توابع
- نسخه 0.3.0 به‌عنوان نقطهٔ تثبیت API پیش از 1.0

## 0.2.0 — 2026-11-25

### مرحله ۱: کشف و جستجوی کامل
- `iter_letters` / `search_all` صفحه‌بندی خودکار
- `search_by_notice_code(symbol, "ن-42")` با فیلتر API + کلاینت
- `search_by_letter_type(symbol, 6)`
- `normalize_letter_code` (ن-۴۲ ≡ ن-42)
- پارامتر `title_contains` برای جدا کردن عادی سالیانه از فوق‌العاده
- `max_pages` برای محدود کردن اسکن در تست


# Changelog

## 0.1.6 — 2026-11-25

- `download_pdf(tracing_no, path)` برای ذخیره PDF روی دیسک
- `download_file(url, path)` برای هر لینک کدال (پیوست و ...)
- `download_attachments(tracing_no, directory)` برای همه پیوست‌ها
- بهبود پر کردن `pdf_url` حتی وقتی فلگ HasPdf ناسازگار است
- پارامتر `letter_code` در `search_letters`

## 0.1.5 — 2026-11-25

- کدهای رسمی اطلاعیه کدال (ن-۱۰ … ن-۸۱) در `constants.NOTICE_CODES`
- گروه‌بندی موضوعی: مالی، افشا، ماهانه، مجمع، افزایش سرمایه، …
- توابع `list_notice_codes`، `notice_title`، `notice_group_of`
- نام پکیج PyPI: `PharaghY-codal`
- لوگوی پروژه در `docs/logo.png`

## 0.1.4 — 2026-11-24

- ماژول `constants` اولیه
- مثال‌های `examples/`
- README حرفه‌ای‌تر

## 0.1.3 — 2026-11-24

- گزارش فعالیت ماهانه (`get_monthly_activity` و مرتبط‌ها)

