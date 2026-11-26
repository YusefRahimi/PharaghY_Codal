"""
گزارش فعالیت ماهانه کدال (letter_type ≈ 58).

خروجی‌ها DataFrame هستند تا در شیت‌های تولید و فروش / مواد مدل استفاده شوند.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .client import CodalClient, CodalError, get_default_client
from .financials import table_to_dataframe
from .letter import get_letter
from .models import Letter, LetterSummary, TableBlock
from .search import search_letters
from .utils import to_ascii

LETTER_TYPE_MONTHLY = 58

_SUBSIDIARY_HINTS = (
    "(شرکت ",
    "（شرکت ",
    "شرکت فرعی",
    "شرکت وابسته",
)


def _score_monthly_letter(letter: LetterSummary, symbol: str) -> int:
    title = letter.title or ""
    score = 0
    if any(h in title for h in _SUBSIDIARY_HINTS):
        score -= 50
    if "فعالیت ماهانه" in title or "فعاليت ماهانه" in title:
        score += 15
    if "گزارش فعالیت" in title or "گزارش فعاليت" in title:
        score += 10
    if symbol and symbol in title:
        score += 5
    return score


def list_monthly_letters(
    symbol: str,
    *,
    page: int = 1,
    max_pages: int = 1,
    year_month: str | None = None,
    client: CodalClient | None = None,
) -> list[dict[str, Any]]:
    """
    لیست گزارش‌های فعالیت ماهانه یک نماد (با امتیاز).

    Parameters
    ----------
    year_month :
        فیلتر متنی روی عنوان، مثلاً ``\"1405/04\"`` برای تیر ۱۴۰۵
    max_pages :
        چند صفحه از نتایج جستجو خوانده شود (هر صفحه حدود ۲۰ مورد)
    """
    rows: list[dict[str, Any]] = []
    for p in range(page, page + max(1, max_pages)):
        result = search_letters(
            symbol=symbol,
            letter_type=LETTER_TYPE_MONTHLY,
            page=p,
            client=client,
        )
        if not result.letters:
            break
        for L in result.letters:
            rows.append(
                {
                    "tracing_no": L.tracing_no,
                    "title": L.title,
                    "sent": L.sent,
                    "has_excel": L.has_excel,
                    "has_pdf": L.has_pdf,
                    "score": _score_monthly_letter(L, symbol),
                }
            )
        if p * 20 >= (result.total or 0):
            break

    if year_month:
        ym = to_ascii(year_month).strip()
        rows = [r for r in rows if ym in to_ascii(r.get("title") or "")]

    rows.sort(key=lambda r: (r["score"], r["tracing_no"]), reverse=True)
    return rows


def find_monthly_letter(
    symbol: str,
    year_month: str,
    *,
    max_pages: int = 5,
    client: CodalClient | None = None,
) -> dict[str, Any]:
    """
    یک گزارش ماهانه برای ``year_month`` مثل ``\"1405/04\"`` پیدا می‌کند.

    اگر چند مورد (مثلاً اصلاحیه) باشد، بالاترین ``tracing_no`` انتخاب می‌شود.
    """
    rows = list_monthly_letters(
        symbol,
        max_pages=max_pages,
        year_month=year_month,
        client=client,
    )
    if not rows:
        raise CodalError(
            f"گزارش ماهانه برای {symbol!r} در دورهٔ {year_month!r} پیدا نشد."
        )
    return max(rows, key=lambda r: r["tracing_no"])


def select_best_monthly_letter(
    letters: list[LetterSummary],
    symbol: str,
) -> LetterSummary:
    if not letters:
        raise CodalError("گزارش فعالیت ماهانه‌ای پیدا نشد.")
    ranked = sorted(
        letters,
        key=lambda L: (_score_monthly_letter(L, symbol), L.tracing_no),
        reverse=True,
    )
    return ranked[0]


def _classify_table(title: str, sample_blob: str) -> str:
    """برچسب موضوعی برای یک جدول داخل گزارش ماهانه."""
    t = to_ascii(title) + " " + to_ascii(sample_blob)
    t = t.replace("\u200c", " ")
    rules = [
        ("production", ("مقدار تولید", "تولید", "production")),
        ("sales_qty", ("مقدار فروش", "فروش مقداری")),
        ("sales_amount", ("مبلغ فروش", "درآمد حاصل از فروش", "فروش ریالی")),
        ("sales", ("فروش", "sales")),
        ("materials", ("مواد اولیه", "مواد مصرفی", "خرید مواد", "مصرف مواد")),
        ("energy", ("انرژی", "برق", "گاز", "آب و سوخت", "سوخت")),
        ("currency", ("ارز", "منابع ارزی", "مصارف ارزی")),
        ("inventory", ("موجودی", "کالا")),
    ]
    for label, keys in rules:
        if any(k in t for k in keys):
            return label
    return "other"


def _tables_by_topic(letter: Letter) -> dict[str, list[pd.DataFrame]]:
    """جداول نامه را بر اساس موضوع گروه‌بندی می‌کند."""
    grouped: dict[str, list[pd.DataFrame]] = {}
    for t in letter.tables:
        blob = " ".join(" ".join(r[:4]) for r in t.rows[:8])
        topic = _classify_table(t.title or "", blob)
        df = table_to_dataframe(t)
        if df.empty:
            continue
        df.attrs["table_title"] = t.title
        grouped.setdefault(topic, []).append(df)
    return grouped


def get_monthly_activity(
    symbol: str,
    *,
    tracing_no: int | None = None,
    client: CodalClient | None = None,
) -> dict[str, Any]:
    """
    آخرین (یا مشخص‌شده) گزارش فعالیت ماهانه را می‌خواند.

    Returns
    -------
    dict با کلیدهای:
      - meta: symbol, tracing_no, title, period_end, unit_note, sent
      - tables: dict[topic -> list[DataFrame]]
        topic ∈ production, sales, sales_qty, sales_amount, materials,
                 energy, currency, inventory, other
      - all_frames: dict[sheet_name -> DataFrame] همهٔ شیت‌ها
    """
    c = client or get_default_client()

    if tracing_no is None:
        result = search_letters(
            symbol=symbol,
            letter_type=LETTER_TYPE_MONTHLY,
            client=c,
        )
        if not result.letters:
            raise CodalError(f"گزارش فعالیت ماهانه برای {symbol!r} پیدا نشد.")
        chosen = select_best_monthly_letter(result.letters, symbol)
        tracing_no = chosen.tracing_no

    letter = get_letter(tracing_no, client=c)
    if not letter.tables:
        raise CodalError(f"اطلاعیه {tracing_no} جدولی نداشت.")

    grouped = _tables_by_topic(letter)
    all_frames: dict[str, pd.DataFrame] = {}
    used: dict[str, int] = {}
    for t in letter.tables:
        name = t.title or "جدول"
        if name in used:
            used[name] += 1
            key = f"{name} ({used[name]})"
        else:
            used[name] = 1
            key = name
        all_frames[key] = table_to_dataframe(t)

    return {
        "meta": {
            "symbol": letter.symbol or symbol,
            "tracing_no": tracing_no,
            "title": letter.title,
            "period_end": letter.period_end,
            "unit_note": letter.unit_note,
            "sent": letter.sent,
        },
        "tables": grouped,
        "all_frames": all_frames,
    }


def get_monthly_production_sales(
    symbol: str,
    *,
    tracing_no: int | None = None,
    client: CodalClient | None = None,
) -> pd.DataFrame:
    """
    تلاش می‌کند جدول‌های مرتبط با تولید/فروش را پیدا و به هم بچسباند.

    اگر چند جدول باشد، اولین جدول production یا sales برمی‌گردد؛
    در غیر این صورت اولین جدول موجود.
    """
    data = get_monthly_activity(symbol, tracing_no=tracing_no, client=client)
    for key in ("production", "sales_qty", "sales_amount", "sales"):
        frames = data["tables"].get(key) or []
        if frames:
            df = frames[0].copy()
            df.attrs.update(data["meta"])
            df.attrs["topic"] = key
            return df
    # fallback
    if data["all_frames"]:
        first_key = next(iter(data["all_frames"]))
        df = data["all_frames"][first_key].copy()
        df.attrs.update(data["meta"])
        df.attrs["topic"] = "other"
        return df
    raise CodalError("جدول تولید/فروش در گزارش ماهانه پیدا نشد.")


def get_monthly_materials(
    symbol: str,
    *,
    tracing_no: int | None = None,
    client: CodalClient | None = None,
) -> pd.DataFrame:
    """جدول مواد اولیه / مصرفی از گزارش ماهانه."""
    data = get_monthly_activity(symbol, tracing_no=tracing_no, client=client)
    frames = data["tables"].get("materials") or []
    if not frames:
        raise CodalError("جدول مواد در گزارش ماهانه پیدا نشد.")
    df = frames[0].copy()
    df.attrs.update(data["meta"])
    df.attrs["topic"] = "materials"
    return df
