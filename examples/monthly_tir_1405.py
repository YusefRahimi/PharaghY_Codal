"""
گزارش فعالیت ماهانه تیر ۱۴۰۵ نماد شپنا.

اجرا:
    python examples/monthly_tir_1405.py
"""

from __future__ import annotations

import pharaghy_codal as fpyc
from pharaghy_codal import CodalError


def main() -> None:
    symbol = "شپنا"
    year_month = "1405/04"  # تیر

    try:
        company = fpyc.get_company(symbol)
        print("شرکت:", company.symbol, company.name)
    except CodalError as e:
        print("نماد نامعتبر:", e)
        return

    try:
        chosen = fpyc.find_monthly_letter(symbol, year_month, max_pages=5)
    except CodalError as e:
        print("پیدا نشد:", e)
        print("نمونهٔ چند گزارش اخیر:")
        for row in fpyc.list_monthly_letters(symbol)[:8]:
            print(" ", row["tracing_no"], row["title"])
        return

    print("انتخاب شد:", chosen["tracing_no"], chosen["title"])
    data = fpyc.get_monthly_activity(symbol, tracing_no=chosen["tracing_no"])
    print("meta:", data["meta"])
    print("موضوعات:", {k: len(v) for k, v in data["tables"].items()})
    for topic, frames in data["tables"].items():
        if not frames:
            continue
        print(f"\n=== {topic} ===")
        print(frames[0].head(6).to_string())


if __name__ == "__main__":
    main()
