"""
خواندن کامل یک اطلاعیه با tracing_no.

اجرا:
    python examples/read_one_letter.py 1562697
"""

from __future__ import annotations

import sys

import pharaghy_codal as fpyc
from pharaghy_codal import CodalError


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python examples/read_one_letter.py <tracing_no>")
        return
    tracing_no = int(sys.argv[1])
    try:
        letter = fpyc.get_letter(tracing_no)
    except CodalError as e:
        print("خطا:", e)
        return

    print("title:", letter.title)
    print("period_end:", letter.period_end)
    print("unit_note:", letter.unit_note)
    print("excel_url:", letter.excel_url)
    print("tables:", len(letter.tables))
    for i, t in enumerate(letter.tables[:5]):
        print(f"\n--- table[{i}] {t.title!r} rows={len(t.rows)} ---")
        for row in t.rows[:5]:
            print(row)


if __name__ == "__main__":
    main()
