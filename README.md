<p align="center">
  <img src="docs/logo.png" alt="PharaghY Codal" width="160"/>
</p>

# PharaghY-codal

##### این ماژول با هدف دسترسی به اطلاعیه‌ها و گزارش‌های سامانهٔ **کدال** در محیط برنامه‌نویسی پایتون توسعه یافته است. با آن می‌توانید صورت‌های مالی، گزارش فعالیت ماهانه، مجامع، افزایش سرمایه و سایر افشاها را به‌صورت برنامه‌نویسی دریافت کنید و در مدل‌های تحلیل بنیادی یا پردازش داده به‌کار ببرید. خروجی بسیاری از توابع، **دیتافریم پانداز** یا اشیاء سادهٔ پایتونی است.

#### از جمله ویژگی‌های مهم این ماژول می‌توان به موارد زیر اشاره کرد

قابلیت جستجوی شرکت با نماد و دریافت مشخصات ناشر ←

قابلیت جستجوی اطلاعیه‌ها بر اساس نماد، نوع گزارش، دوره، تاریخ و کد اطلاعیه (ن-۱۰ … ن-۸۱) ←

قابلیت خواندن جداول یک اطلاعیه و تبدیل به DataFrame ←

قابلیت دریافت صورت سود و زیان با اولویت گزارش تلفیقی ←

قابلیت دریافت گزارش فعالیت ماهانه (تولید، مواد، انرژی و …) ←

قابلیت دانلود فایل اکسل، PDF و پیوست‌های اطلاعیه ←

مدیریت فاصله بین درخواست‌ها، retry روی قطع اتصال و صبر خودکار روی rate-limit کدال ←

پشتیبانی از پروکسی ایرانی از طریق متغیر محیطی ←

##### این مخزن در حال توسعه است. برای نمونه کدها به پوشهٔ [examples](examples/) مراجعه کنید.

---

# نصب ماژول

```bash
pip install PharaghY-codal
```

یا از سورس:

```bash
git clone https://github.com/YOUR_USER/PharaghY_Codal.git
cd PharaghY_Codal
pip install -e .
```

# فراخوانی ماژول

```python
import pharaghy_codal as fpyc
```

در صورت نیاز به پروکسی:

```bash
# Windows PowerShell
$env:PHARAGHY_CODAL_PROXY = "http://127.0.0.1:PORT"

# Linux / macOS
export PHARAGHY_CODAL_PROXY=http://127.0.0.1:PORT
```

> کدال معمولاً فقط از داخل ایران یا با IP/پروکسی ایرانی پاسخ می‌دهد.

---

# اطلاعات شرکت

### دریافت مشخصات شرکت

```python
fpyc.get_company(symbol="شپنا")
```

### دریافت پایان سال‌های مالی

```python
fpyc.get_financial_years(symbol="شپنا")
```

---

# جستجوی اطلاعیه‌ها

### لیست انواع و گروه‌های گزارش

```python
fpyc.get_letter_groups()
fpyc.get_letter_types(category=1)
```

### جستجو

```python
fpyc.search_letters(
    symbol="خودرو",
    letter_type=None,      # مثلاً 6 = صورت مالی، 58 = ماهانه
    letter_code="ن-42",    # کد رسمی اطلاعیه (در صورت پشتیبانی API)
    title=None,            # کلمات کوتاه داخل عنوان
    period_months=None,
    from_date=None,        # YYYY/MM/DD شمسی
    to_date=None,
    page=1,
)
```

### کدهای رسمی اطلاعیه (ن-۱۰ … ن-۸۱)

```python
fpyc.list_notice_codes()
fpyc.list_notice_codes("capital_increase")
fpyc.notice_title("ن-30")
```

---

# خواندن یک اطلاعیه و دانلود فایل

### خواندن جداول و متادیتا

```python
letter = fpyc.get_letter(tracing_no=1562697)
print(letter.title, letter.period_end, letter.unit_note)
print(len(letter.tables))
```

### دانلود اکسل / PDF / پیوست

```python
fpyc.download_excel(1562697, "report.xlsx")
fpyc.download_pdf(1592996, "notice.pdf")
fpyc.download_attachments(1592996, "attachments_folder")
fpyc.download_file(url, "file.bin")  # هر لینک کدال
```

---

# صورت‌های مالی (سطح بالاتر)

### لیست گزارش‌ها با امتیاز (ترجیح تلفیقی)

```python
fpyc.list_financial_letters(symbol="شپنا", period_months=12)
```

### صورت سود و زیان

```python
df = fpyc.get_income_statement(symbol="شپنا", period_months=12)
print(df.head())
print(df.attrs.get("period_end"), df.attrs.get("unit_note"))
```

---

# گزارش فعالیت ماهانه

### لیست و دریافت

```python
fpyc.list_monthly_letters(symbol="شپنا")

data = fpyc.get_monthly_activity(symbol="شپنا")
print(data["meta"])
print({k: len(v) for k, v in data["tables"].items()})

fpyc.get_monthly_production_sales(symbol="شپنا")
fpyc.get_monthly_materials(symbol="شپنا")
```

### یک ماه مشخص

```python
chosen = fpyc.find_monthly_letter("شپنا", "1405/04")  # تیر
data = fpyc.get_monthly_activity("شپنا", tracing_no=chosen["tracing_no"])
```

---

# نمونهٔ جریان کار: ن-۴۲ نماد خودرو

```python
import pharaghy_codal as fpyc

def norm_code(c):
    s = (c or "").replace(" ", "")
    for a, b in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789"):
        s = s.replace(a, b)
    return s

items = []
first = fpyc.search_letters(symbol="خودرو", page=1)
pages = max(1, (first.total + 19) // 20)
for page in range(1, min(pages, 30) + 1):  # برای تست محدود کنید
    r = first if page == 1 else fpyc.search_letters(symbol="خودرو", page=page)
    for L in r.letters:
        if norm_code(L.code) == "ن-42" and "عادی سالیانه" in (L.title or ""):
            items.append(L)

for i, L in enumerate(items, 1):
    print(i, L.tracing_no, L.title)

# پس از انتخاب کاربر:
# fpyc.download_pdf(items[0].tracing_no, "khodro_n42.pdf")
```

---

# وابستگی‌ها

- Python ≥ 3.10
- httpx, pandas, openpyxl, lxml

# مجوز

MIT License — استفاده، تغییر و انتشار آزاد است.  
داده‌ها از API عمومی غیررسمی کدال خوانده می‌شوند؛ این پروژه وابسته به سازمان بورس نیست.

---

# ارتباط

- **کانال تلگرام:** [bourse_faraghy](https://t.me/bourse_faraghy)
- Issues و پیشنهادها: از بخش Issues همین ریپو استفاده کنید.

# وضعیت

نسخهٔ فعلی: **0.3.1** (Alpha)  
