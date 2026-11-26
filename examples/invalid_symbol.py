"""
رفتار کتابخانه برای نماد ناموجود.

اجرا:
    python examples/invalid_symbol.py
"""

from __future__ import annotations

import pharaghy_codal as fpyc
from pharaghy_codal import CodalError


def main() -> None:
    symbol = "کتاب"
    print("=== get_company ===")
    try:
        print(fpyc.get_company(symbol))
    except CodalError as e:
        print("CodalError:", e)

    print("\n=== list_monthly_letters ===")
    rows = fpyc.list_monthly_letters(symbol)
    print("len =", len(rows))

    print("\n=== search_letters ===")
    r = fpyc.search_letters(symbol=symbol, letter_type=58)
    print("total =", r.total, "letters =", len(r.letters))

    print("\n=== get_monthly_activity ===")
    try:
        print(fpyc.get_monthly_activity(symbol))
    except CodalError as e:
        print("CodalError:", e)


if __name__ == "__main__":
    main()
