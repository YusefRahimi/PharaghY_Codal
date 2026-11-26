"""دانلود همه فایل‌های یک اطلاعیه (اکسل / PDF / پیوست)."""
import pharaghy_codal as fpyc

# شماره پیگیری را از search_by_notice_code بگیر
TN = 1592996

print("files:", fpyc.list_files(TN))
paths = fpyc.download_all_files(TN, f"out_{TN}")
for p in paths:
    print("saved:", p, p.stat().st_size)
