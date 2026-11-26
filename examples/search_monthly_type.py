"""جستجو با letter_type عددی (۵۸ = فعالیت ماهانه)."""
import pharaghy_codal as fpyc

items = fpyc.search_by_letter_type("شپنا", 58, max_pages=2)
print(len(items))
for L in items[:5]:
    print(L.tracing_no, L.code, L.title[:60])
