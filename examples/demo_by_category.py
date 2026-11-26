"""
نمایش عملی دسته‌های اصلی گزارش کدال برای یک نماد.

توجه:
  - کدهای «ن-۱۰ … ن-۸۱» برای مستندسازی و UI هستند.
  - جستجوی API با letter_type عددی (مثلاً 6 و 58) یا category انجام می‌شود.
  - این اسکریپت برای هر دسته چند عنوان اخیر را چاپ می‌کند؛ همهٔ کدهای ن-
    لزوماً letter_type جداگانه در API ندارند.

اجرا:
    python examples/demo_by_category.py
    python examples/demo_by_category.py فولاد
"""

from __future__ import annotations

import sys

import pharaghy_codal as fpyc
from pharaghy_codal import CodalError


def show_search(title: str, **kwargs) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)
    try:
        result = fpyc.search_letters(**kwargs)
    except CodalError as e:
        print("خطا:", e)
        return
    print(f"total={result.total}  page_items={len(result.letters)}")
    for L in result.letters[:8]:
        print(f"  {L.tracing_no:>8} | {L.title[:80]}")


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "شپنا"
    print("نماد:", symbol)

    try:
        c = fpyc.get_company(symbol)
        print("شرکت:", c.symbol, "|", c.name, "|", c.market)
    except CodalError as e:
        print("شرکت پیدا نشد:", e)
        return

    # صورت‌های مالی (letter_type=6)
    show_search(
        "صورت‌های مالی (letter_type=6، سالانه)",
        symbol=symbol,
        letter_type=6,
        period_months=12,
    )

    # فعالیت ماهانه (letter_type=58) — معادل کاربردی ن-۳۰
    show_search(
        "فعالیت ماهانه (letter_type=58 / نزدیک به ن-۳۰)",
        symbol=symbol,
        letter_type=58,
    )

    # جستجو با عنوان برای دسته‌هایی که letter_type ثابت قطعی نداریم
    for label, title_kw in [
        ("افزایش سرمایه (جستجوی عنوان)", "افزایش سرمایه"),
        ("مجمع عمومی (جستجوی عنوان)", "مجمع"),
        ("زمان‌بندی سود (جستجوی عنوان)", "زمان بندی پرداخت سود"),
        ("شفاف‌سازی (جستجوی عنوان)", "شفاف"),
        ("اطلاعات با اهمیت (جستجوی عنوان)", "با اهمیت"),
    ]:
        show_search(label, symbol=symbol, title=title_kw)

    print("\n" + "=" * 60)
    print("کدهای رسمی اطلاعیه (بدون شبکه)")
    print("=" * 60)
    for group in ("monthly", "capital_increase", "meetings", "financial"):
        print(f"\n-- {group} --")
        for item in fpyc.list_notice_codes(group)[:6]:
            print(f"  {item['code']}: {item['title']}")


if __name__ == "__main__":
    main()
