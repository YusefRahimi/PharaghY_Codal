"""جریان کامل: کد ن-... → لیست → انتخاب اول → دانلود."""
import pharaghy_codal as fpyc

SYMBOL = "خودرو"
CODE = "ن-42"

items = fpyc.search_by_notice_code(
    SYMBOL,
    CODE,
    title_contains="عادی سالیانه",
    max_pages=15,
)
print(f"{len(items)} items")
if not items:
    raise SystemExit(0)

chosen = items[0]
print("chosen:", chosen.tracing_no, chosen.title)
letter = fpyc.get_letter(chosen.tracing_no)
print("kind:", fpyc.letter_content_kind(letter))
print("list_files:", fpyc.list_files(chosen.tracing_no))
paths = fpyc.download_all_files(chosen.tracing_no, f"dl_{chosen.tracing_no}")
print("downloaded:", paths)
