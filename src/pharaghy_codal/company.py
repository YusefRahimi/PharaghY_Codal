"""جستجوی شرکت و سال‌های مالی."""

from __future__ import annotations

from typing import Any

from .client import SEARCH, CodalClient, CodalError, get_default_client
from .models import Company
from .utils import normalize_key, normalize_symbol, to_ascii

LOOKUP_TTL = 12 * 3600

MARKETS = {
    0: "بورس تهران",
    1: "فرابورس",
    2: "ثبت‌شده پذیرفته‌نشده",
    3: "ثبت‌نشده نزد سازمان",
    4: "بورس کالا",
    5: "بورس انرژی",
}

KINDS = {
    1: "ناشر",
    2: "کارگزار",
    3: "نهاد مالی / صندوق",
    4: "نهاد عمومی",
    5: "شرکت دولتی",
}

REPORTING = {
    1000000: "تولیدی",
    1000001: "ساختمانی",
    1000002: "سرمایه‌گذاری",
    1000003: "بانک",
    1000004: "لیزینگ",
    1000005: "خدماتی",
    1000006: "بیمه",
    1000007: "حمل‌ونقل دریایی",
    1000008: "کشاورزی",
    1000009: "تأمین سرمایه",
}


def _companies(client: CodalClient) -> list[dict[str, Any]]:
    body = client.fetch_json(f"{SEARCH}/v1/companies", ttl=LOOKUP_TTL)
    if not isinstance(body, list) or not body:
        raise CodalError("کدال لیست شرکت‌ها را برنگرداند.")
    return [c for c in body if isinstance(c, dict)]


def get_company(
    query: str,
    limit: int = 10,
    *,
    client: CodalClient | None = None,
) -> Company | list[Company]:
    """
    پیدا کردن شرکت با نماد یا بخشی از نام.

    اگر دقیقاً یک نتیجه با نماد برابر باشد، همان Company برگردانده می‌شود؛
    در غیر این صورت لیست Companyها (حداکثر limit).
    """
    c = client or get_default_client()
    q = normalize_key(query)
    if not q:
        raise CodalError("query نباید خالی باشد.")

    companies = _companies(c)
    groups = c.fetch_json(f"{SEARCH}/v1/IndustryGroup", ttl=LOOKUP_TTL)
    industry = (
        {g.get("Id"): g.get("Name") for g in groups if isinstance(g, dict)}
        if isinstance(groups, list)
        else {}
    )

    ranked: list[tuple] = []
    for row in companies:
        sy = normalize_key(str(row.get("sy") or ""))
        name = normalize_key(str(row.get("n") or ""))
        if q == sy or q == name:
            rank = 0
        elif sy.startswith(q):
            rank = 1
        elif q in name:
            rank = 2
        elif q in sy:
            rank = 3
        else:
            continue
        # شرکت‌های بورسی/فرابورسی اول
        listed = row.get("st") not in (0, 1, 4, 5)
        ranked.append((rank, listed, len(sy), row))

    ranked.sort(key=lambda r: r[:3])
    results: list[Company] = []
    for *_, row in ranked[:limit]:
        results.append(
            Company(
                symbol=to_ascii(row.get("sy")),
                name=to_ascii(row.get("n")),
                isic=to_ascii(row.get("i")) or None,
                market=MARKETS.get(row.get("st")),
                kind=KINDS.get(row.get("t")),
                industry=to_ascii(industry.get(row.get("IG"))) or None,
                reporting_type=REPORTING.get(row.get("RT")),
            )
        )

    if not results:
        raise CodalError(f"شرکتی با عبارت {query!r} پیدا نشد.")

    # اگر دقیقاً یک match با نماد برابر باشد، همان را برگردان
    exact = [r for r in results if normalize_key(r.symbol) == q]
    if len(exact) == 1:
        return exact[0]
    if len(results) == 1:
        return results[0]
    return results


def get_financial_years(
    symbol: str,
    *,
    client: CodalClient | None = None,
) -> list[str]:
    """لیست پایان سال‌های مالی شرکت (شمسی، جدیدترین اول)."""
    c = client or get_default_client()
    sy = normalize_symbol(symbol)
    if not sy:
        raise CodalError("symbol نباید خالی باشد.")
    body = c.fetch_json(f"{SEARCH}/v1/financialYears", {"Symbol": sy}, ttl=LOOKUP_TTL)
    if not isinstance(body, list):
        raise CodalError("کدال سال‌های مالی را برنگرداند.")
    return [to_ascii(y) for y in body]
