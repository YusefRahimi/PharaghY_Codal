"""انواع و گروه‌های گزارش کدال."""

from __future__ import annotations

from typing import Any

from .client import SEARCH, CodalClient, CodalError, get_default_client
from .models import LetterGroup, LetterType
from .utils import to_ascii

LOOKUP_TTL = 12 * 3600


def get_letter_groups(*, client: CodalClient | None = None) -> list[LetterGroup]:
    """لیست ۱۱ گروه اصلی گزارش‌های کدال."""
    c = client or get_default_client()
    body = c.fetch_json(f"{SEARCH}/v1/categories", ttl=LOOKUP_TTL)
    if not isinstance(body, list):
        raise CodalError("کدال لیست گروه‌ها را برنگرداند.")

    groups: list[LetterGroup] = []
    for cat in body:
        if not isinstance(cat, dict):
            continue
        code = cat.get("Code")
        if not isinstance(code, int) or code <= 0:
            continue
        count = 0
        for pub in cat.get("PublisherTypes") or []:
            count += len(pub.get("LetterTypes") or [])
        groups.append(
            LetterGroup(
                category=code,
                name=to_ascii(cat.get("Name")),
                letter_types_count=count,
            )
        )
    return groups


def get_letter_types(
    category: int | None = None,
    *,
    client: CodalClient | None = None,
) -> list[LetterType] | list[LetterGroup]:
    """
    اگر category داده نشود → لیست گروه‌ها.
    اگر category داده شود → انواع گزارش آن گروه با شناسه (letter_type).

    شناسه‌های مهم:
      6  = صورت‌های مالی
      58 = گزارش فعالیت ماهانه
      20 = تصمیمات مجمع عمومی عادی سالیانه
    """
    if category is None:
        return get_letter_groups(client=client)

    c = client or get_default_client()
    body = c.fetch_json(f"{SEARCH}/v1/categories", ttl=LOOKUP_TTL)
    if not isinstance(body, list):
        raise CodalError("کدال لیست انواع گزارش را برنگرداند.")

    match = [
        cat
        for cat in body
        if isinstance(cat, dict) and cat.get("Code") == category
    ]
    if not match:
        raise CodalError(
            f"گروه {category} شناخته نشد. ابتدا get_letter_groups() را فراخوانی کنید."
        )

    seen: dict[int, str] = {}
    for pub in match[0].get("PublisherTypes") or []:
        for lt in pub.get("LetterTypes") or []:
            if isinstance(lt, dict) and lt.get("Id") not in seen:
                seen[int(lt["Id"])] = to_ascii(lt.get("Name"))

    return [LetterType(id=k, name=v) for k, v in sorted(seen.items())]
