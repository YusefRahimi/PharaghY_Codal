"""
توابع سطح بالاتر برای استخراج صورت‌های مالی و گزارش‌های ساختاریافته.

خروجی‌ها عمدتاً pandas.DataFrame هستند تا مستقیماً در مدل‌های اکسل استفاده شوند.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .client import CodalClient, CodalError, get_default_client
from .letter import get_letter
from .models import Letter, LetterSummary, TableBlock
from .search import search_letters
from .utils import parse_number, to_ascii

LETTER_TYPE_FINANCIAL = 6

# الگوهایی که معمولاً یعنی گزارش شرکت فرعی / وابسته است
_SUBSIDIARY_HINTS = (
    "(شرکت ",
    "（شرکت ",
    "شرکت فرعی",
    "شرکت وابسته",
)


def _is_income_statement_title(title: str) -> bool:
    t = to_ascii(title).replace("\u200c", " ").replace("\u200f", "")
    keys = (
        "سود و زیان",
        "سودوزیان",
        "صورت سود",
        "درآمدهاي عملياتي",
        "درآمدهای عملیاتی",
        "income",
    )
    bad = ("ترازنامه", "وضعیت مالی", "جریان وجوه", "جریان نقد", "تغییرات در حقوق")
    if any(b in t for b in bad):
        return False
    return any(k in t for k in keys)


def _find_income_table(letter: Letter) -> TableBlock | None:
    """بهترین جدول صورت سود و زیان را از میان جداول نامه پیدا می‌کند."""
    candidates: list[tuple[int, TableBlock]] = []
    for t in letter.tables:
        score = 0
        title = t.title or ""
        if _is_income_statement_title(title):
            score += 10
        blob = to_ascii(" ".join(" ".join(r) for r in t.rows[:20]))
        if "درآمدهاي عملياتي" in blob or "درآمدهای عملیاتی" in blob:
            score += 8
        if "فروش" in blob:
            score += 2
        if "سود" in blob and ("زيان" in blob or "زیان" in blob):
            score += 3
        if "بهاي تمام شده" in blob or "بهای تمام شده" in blob:
            score += 2
        # ترجیح جدول اصلی تلفیقی روی جداگانه اگر در عنوان باشد
        if "تلفیقی" in title or "تلفيقي" in title:
            score += 2
        if score:
            candidates.append((score, t))
    if not candidates:
        return letter.tables[0] if letter.tables else None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _flatten_col_name(col: Any) -> str:
    """نام ستون را از MultiIndex / tuple / رشته به یک رشتهٔ خوانا تبدیل می‌کند."""
    # گاهی به صورت رشتهٔ "('دوره ...', 'حسابرسی شده')" ذخیره شده
    if isinstance(col, str) and col.startswith("(") and "," in col:
        inner = re.findall(r"'([^']*)'|\"([^\"]*)\"", col)
        parts = [to_ascii(a or b).strip() for a, b in inner if (a or b)]
        parts = [p for p in parts if p and not p.lower().startswith("unnamed")]
        for p in parts:
            if "منتهي" in p or "منتهی" in p or re.search(r"\d{4}/\d{2}", p):
                return p
        parts = [p for p in parts if "حسابرس" not in p] or parts
        return parts[0] if parts else to_ascii(col)

    if isinstance(col, tuple):
        parts = []
        for p in col:
            s = to_ascii(p).strip()
            if not s or s.lower().startswith("unnamed") or s == "nan":
                continue
            if s not in parts:
                parts.append(s)
        if parts and all(p in ("حسابرسی شده", "حسابرسي شده", "حسابرسی نشده") for p in parts):
            return parts[0]
        for p in parts:
            if "منتهي" in p or "منتهی" in p or re.search(r"\d{4}/\d{2}", p):
                return p
        parts = [p for p in parts if "حسابرس" not in p] or parts
        return " | ".join(parts) if parts else "col"
    return to_ascii(col)


def table_to_dataframe(table: TableBlock) -> pd.DataFrame:
    """TableBlock → DataFrame؛ هدرهای چندردیفهٔ کدال را تا حد امکان صاف می‌کند."""
    if not table.rows:
        return pd.DataFrame()

    rows = [[to_ascii(c) for c in r] for r in table.rows]
    ncols = max(len(r) for r in rows)

    def pad(r: list[str]) -> list[str]:
        return r + [""] * (ncols - len(r))

    rows = [pad(r) for r in rows]

    # اگر ردیف دوم فقط «حسابرسی شده / نشده» است، با ردیف اول ادغام کن
    header_rows = 1
    if len(rows) >= 2:
        second = rows[1]
        audit_like = sum(
            1
            for c in second
            if c in ("حسابرسی شده", "حسابرسي شده", "حسابرسی نشده", "حسابرسي نشده", "")
            or "حسابرس" in c
        )
        if audit_like >= max(1, ncols - 1):
            header_rows = 2

    if header_rows == 2:
        header = []
        for i in range(ncols):
            a, b = rows[0][i], rows[1][i]
            if i == 0:
                header.append(a or "شرح")
            elif a and b and b not in a:
                # فقط اگر b اطلاعات دوره ندارد، a را نگه دار
                if "حسابرس" in b and ("منتهي" in a or "منتهی" in a or re.search(r"\d{4}", a)):
                    header.append(a)
                else:
                    header.append(_flatten_col_name((a, b)))
            else:
                header.append(a or b or f"col_{i}")
        data = rows[2:]
    else:
        header = rows[0]
        data = rows[1:]

    # یکتا کردن نام ستون‌ها
    seen: dict[str, int] = {}
    uniq = []
    for h in header:
        h = h or "col"
        if h in seen:
            seen[h] += 1
            uniq.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 1
            uniq.append(h)

    df = pd.DataFrame(data, columns=uniq)
    return df


def _normalize_income_df(df: pd.DataFrame) -> pd.DataFrame:
    """ستون اول = شرح؛ بقیه تا حد امکان عدد."""
    if df.empty:
        return df
    out = df.copy()
    cols = [ _flatten_col_name(c) for c in out.columns ]
    # یکتا
    seen: dict[str, int] = {}
    final_cols = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            final_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 1
            final_cols.append(c)
    final_cols[0] = "شرح"
    out.columns = final_cols

    for c in out.columns[1:]:
        out[c] = out[c].map(
            lambda v: parse_number(v) if isinstance(v, str) else (v if v == v else None)
        )

    # ردیف‌های کم‌ارزش
    out = out[out["شرح"].astype(str).str.strip() != ""]
    # ردیف‌هایی که فقط برچسب بخش‌اند و عدد ندارند را نگه می‌داریم (برای خوانایی)
    out = out.reset_index(drop=True)
    return out


def _score_financial_letter(letter: LetterSummary, symbol: str) -> int:
    """امتیاز بالاتر = انتخاب بهتر برای صورت مالی اصلی نماد."""
    title = letter.title or ""
    score = 0
    # ترجیح گزارش خود شرکت (بدون نام شرکت دیگر داخل پرانتز)
    if any(h in title for h in _SUBSIDIARY_HINTS):
        score -= 50
    if "تلفیقی" in title or "تلفيقي" in title:
        score += 20
    if "جداگانه" in title:
        score += 5  # بهتر از فرعی؛ ولی از تلفیقی کمتر
    if "حسابرسی شده" in title:
        score += 10
    if "حسابرسی نشده" in title:
        score += 2
    # اگر نماد عیناً در عنوان باشد
    if symbol and symbol in title:
        score += 5
    return score


def select_best_financial_letter(
    letters: list[LetterSummary],
    symbol: str,
    *,
    audited_only: bool = False,
    prefer_consolidated: bool = True,
) -> LetterSummary:
    """از لیست نتایج جستجو، مناسب‌ترین صورت مالی را برمی‌گرداند."""
    pool = list(letters)
    if audited_only:
        pool = [L for L in pool if "حسابرسی شده" in (L.title or "")]
        if not pool:
            raise CodalError("گزارش حسابرسی‌شده‌ای پیدا نشد.")

    if not pool:
        raise CodalError("لیست اطلاعیه‌ها خالی است.")

    ranked = sorted(
        pool,
        key=lambda L: (
            _score_financial_letter(L, symbol),
            # در صورت تساوی، جدیدتر (شماره پیگیری معمولاً بزرگ‌تر)
            L.tracing_no,
        ),
        reverse=True,
    )
    best = ranked[0]
    if prefer_consolidated and "تلفیقی" not in (best.title or "") and "تلفيقي" not in (best.title or ""):
        # اگر گزینهٔ تلفیقی با امتیاز نزدیک وجود دارد همان را بگیر
        for L in ranked:
            if "تلفیقی" in (L.title or "") or "تلفيقي" in (L.title or ""):
                if _score_financial_letter(L, symbol) >= _score_financial_letter(best, symbol) - 15:
                    return L
                break
    return best


def get_income_statement(
    symbol: str,
    *,
    period_months: int = 12,
    tracing_no: int | None = None,
    audited_only: bool = False,
    prefer_consolidated: bool = True,
    client: CodalClient | None = None,
) -> pd.DataFrame:
    """
    صورت سود و زیان یک نماد را به‌صورت DataFrame برمی‌گرداند.

    Parameters
    ----------
    symbol :
        نماد فارسی (مثلاً شپنا)
    period_months :
        ۱۲=سالانه، ۶=شش‌ماهه، ۳=فصلی
    tracing_no :
        اگر مشخص باشد همان اطلاعیه خوانده می‌شود
    audited_only :
        فقط عنوان‌های دارای «حسابرسی شده»
    prefer_consolidated :
        ترجیح گزارش تلفیقی روی جداگانه / شرکت فرعی
    """
    c = client or get_default_client()

    if tracing_no is None:
        result = search_letters(
            symbol=symbol,
            letter_type=LETTER_TYPE_FINANCIAL,
            period_months=period_months,
            client=c,
        )
        if not result.letters:
            raise CodalError(
                f"صورت مالی با period_months={period_months} برای {symbol!r} پیدا نشد."
            )
        chosen = select_best_financial_letter(
            result.letters,
            symbol,
            audited_only=audited_only,
            prefer_consolidated=prefer_consolidated,
        )
        tracing_no = chosen.tracing_no

    letter = get_letter(tracing_no, client=c)
    if not letter.tables:
        raise CodalError(f"اطلاعیه {tracing_no} جدولی برای صورت سود و زیان نداشت.")

    table = _find_income_table(letter)
    if table is None:
        raise CodalError("جدول صورت سود و زیان در اطلاعیه پیدا نشد.")

    df = _normalize_income_df(table_to_dataframe(table))
    df.attrs["symbol"] = letter.symbol or symbol
    df.attrs["tracing_no"] = tracing_no
    df.attrs["title"] = letter.title
    df.attrs["period_end"] = letter.period_end
    df.attrs["unit_note"] = letter.unit_note
    df.attrs["table_title"] = table.title
    return df


def list_financial_letters(
    symbol: str,
    *,
    period_months: int | None = 12,
    page: int = 1,
    client: CodalClient | None = None,
) -> list[dict[str, Any]]:
    """لیست خلاصهٔ صورت‌های مالی یک نماد، با امتیاز انتخاب."""
    result = search_letters(
        symbol=symbol,
        letter_type=LETTER_TYPE_FINANCIAL,
        period_months=period_months,
        page=page,
        client=client,
    )
    rows = []
    for L in result.letters:
        rows.append(
            {
                "tracing_no": L.tracing_no,
                "title": L.title,
                "sent": L.sent,
                "has_excel": L.has_excel,
                "has_pdf": L.has_pdf,
                "score": _score_financial_letter(L, symbol),
            }
        )
    rows.sort(key=lambda r: (r["score"], r["tracing_no"]), reverse=True)
    return rows


def get_letter_tables_as_frames(
    tracing_no: int,
    *,
    client: CodalClient | None = None,
) -> dict[str, pd.DataFrame]:
    """همهٔ جداول یک اطلاعیه → دیکشنری نام → DataFrame."""
    letter = get_letter(tracing_no, client=client)
    out: dict[str, pd.DataFrame] = {}
    used: dict[str, int] = {}
    for t in letter.tables:
        name = t.title or "جدول"
        if name in used:
            used[name] += 1
            key = f"{name} ({used[name]})"
        else:
            used[name] = 1
            key = name
        out[key] = table_to_dataframe(t)
    return out
