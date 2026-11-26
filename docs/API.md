# مرجع سریع API — PharaghY-codal

```python
import pharaghy_codal as fpyc
```

## شرکت

| تابع | کار |
|------|-----|
| `get_company(symbol)` | مشخصات ناشر |
| `get_financial_years(symbol)` | پایان سال‌های مالی |

## جستجو

| تابع | کار |
|------|-----|
| `search_letters(...)` | یک صفحه نتیجه |
| `iter_letters(...)` | پیمایش همه صفحات |
| `search_all(...)` | لیست همه نتایج |
| `search_by_notice_code(symbol, "ن-42")` | فیلتر کد رسمی ن-… |
| `search_by_letter_type(symbol, 6)` | فیلتر letter_type عددی |

**LetterType** = عدد API (۶، ۵۸، …)  
**LetterCode** = برچسب `ن-10` / `ن-42` روی هر اطلاعیه

## خواندن یک اطلاعیه

| تابع | کار |
|------|-----|
| `get_letter(tracing_no)` | متادیتا + جداول/متن + پیوست‌ها |
| `list_files(tracing_no)` | منابع قابل دانلود |
| `letter_content_kind(letter)` | `tables` / `text` / `files_only` / `empty` |

## دانلود

| تابع | کار |
|------|-----|
| `download_excel(tn, path)` | اکسل کدال |
| `download_pdf(tn, path)` | PDF یا پیوست جایگزین |
| `download_attachments(tn, dir)` | همه پیوست‌ها |
| `download_all_files(tn, dir)` | اکسل + PDF + پیوست‌ها |
| `download_file(url, path)` | هر لینک کدال |

## سطح بالاتر (تحلیل)

| تابع | کار |
|------|-----|
| `get_income_statement(symbol)` | صورت سود → DataFrame |
| `get_monthly_activity(symbol)` | گزارش ماهانه گروه‌بندی‌شده |
| `list_notice_codes()` | فهرست ن-۱۰ … ن-۸۱ |

## شبکه

```python
fpyc.configure_client(timeout=60, min_interval=2.5, cache_dir=".codal_cache")
```

متغیرهای محیطی: `PHARAGHY_CODAL_PROXY`, `PHARAGHY_CODAL_TIMEOUT`,
`PHARAGHY_CODAL_MIN_INTERVAL`, `PHARAGHY_CODAL_MAX_RETRIES`, `PHARAGHY_CODAL_CACHE_DIR`
