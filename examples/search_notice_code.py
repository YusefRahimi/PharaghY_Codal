"""جستجوی همه اطلاعیه‌های یک کد رسمی (مثلاً ن-42) برای یک نماد."""
import pharaghy_codal as fpyc

SYMBOL = "خودرو"
CODE = "ن-42"

# برای تست سریع max_pages بگذارید؛ برای لیست کامل None
items = fpyc.search_by_notice_code(
    SYMBOL,
    CODE,
    title_contains="عادی سالیانه",  # اختیاری
    max_pages=20,
)
print(f"{len(items)} مورد")
for L in items:
    print(L.tracing_no, L.code, L.title[:70], L.files)
