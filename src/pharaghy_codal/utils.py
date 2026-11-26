"""ابزارهای کمکی: تبدیل ارقام فارسی، نرمال‌سازی نماد و تاریخ شمسی."""

from __future__ import annotations

import re
from typing import Any

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "0123456789" * 2)
_LETTERS = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "\u200c": " ",  # ZWNJ
        "\u200f": None,
        "\u200e": None,
    }
)


def to_ascii(value: Any) -> str:
    """ارقام فارسی/عربی را به ASCII تبدیل و فاصله‌های اضافه را حذف می‌کند."""
    return re.sub(r"\s+", " ", str(value or "").translate(_DIGITS)).strip()


def normalize_key(value: str) -> str:
    """فرم یکسان برای مقایسهٔ نماد یا نام: ارقام ASCII، ی/ک فارسی، بدون ZWNJ."""
    return re.sub(r"\s+", " ", value.translate(_DIGITS).translate(_LETTERS)).strip().lower()


def normalize_symbol(value: str | None) -> str | None:
    """نماد را تمیز می‌کند؛ اگر خالی باشد None برمی‌گرداند."""
    s = to_ascii(value) if value else ""
    return s or None


def parse_jalali(value: str | None, name: str = "date") -> str | None:
    """
    تاریخ شمسی را به صورت YYYY/MM/DD نرمال می‌کند.
    ورودی‌هایی مثل ۱۴۰۵/۷/۱ یا 1405-07-01 پذیرفته می‌شوند.
    """
    if not value:
        return None
    s = to_ascii(value).replace("-", "/")
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if not m:
        raise ValueError(f"{name} must be a Jalali date like 1403/07/01, got {value!r}")
    year, month, day = int(m[1]), int(m[2]), int(m[3])
    if not (1300 <= year <= 1500 and 1 <= month <= 12 and 1 <= day <= 31):
        raise ValueError(f"{name} is out of valid Jalali range: {value!r}")
    return f"{year}/{month:02d}/{day:02d}"


def parse_number(value: str | None) -> float | None:
    """رشتهٔ عددی (با پرانتز برای منفی) را به float تبدیل می‌کند."""
    if value is None:
        return None
    s = to_ascii(value).replace(",", "").replace("٬", "").strip()
    if not s or s in ("-", "—", "–"):
        return None
    # کدال گاهی اعداد منفی را داخل پرانتز می‌نویسد
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    try:
        n = float(s)
        return -n if neg else n
    except ValueError:
        return None
