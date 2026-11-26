"""جستجوی اطلاعیه‌های کدال.

دو شناسهٔ مهم (با هم اشتباه نشوند):

* **LetterType** (عدد): شناسهٔ نوع در API جستجو — مثلاً ``6`` صورت مالی، ``58`` ماهانه.
  لیست به‌روز: ``get_letter_types(category)``.

* **LetterCode / کد اطلاعیه** (رشته): برچسب رسمی مثل ``ن-۱۰`` یا ``ن-42`` که در
  فیلد ``LetterCode`` هر اطلاعیه می‌آید و در UI کدال دیده می‌شود.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .client import SEARCH, CodalClient, CodalError, get_default_client
from .models import LetterSummary, SearchResult
from .utils import normalize_symbol, parse_jalali, to_ascii

PAGE_SIZE = 20  # اندازهٔ صفحهٔ ثابت API کدال


def normalize_letter_code(code: str | None) -> str:
    """
    یکسان‌سازی کد اطلاعیه برای مقایسه.

    ``ن-۴۲`` و ``ن-42`` و ``ن 42`` همه به ``ن-42`` تبدیل می‌شوند.
    """
    if not code:
        return ""
    s = str(code).strip().replace(" ", "").replace("\u200c", "")
    # ارقام فارسی/عربی → انگلیسی
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    s = s.translate(trans)
    # اگر بدون خط تیره نوشته شده باشد
    if s.startswith("ن") and len(s) > 1 and s[1] != "-":
        s = "ن-" + s[1:]
    return s


def letter_code_variants(code: str) -> list[str]:
    """اشکال محتمل ارسال LetterCode به API (ارقام فارسی و انگلیسی)."""
    base = normalize_letter_code(code)
    if not base:
        return []
    # ن-42
    variants = [base]
    # ن-۴۲
    fa_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    variants.append(base.translate(fa_digits))
    # بدون تکراری
    out: list[str] = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out


def _search_raw(client: CodalClient, params: dict[str, Any], ttl: float = 120.0) -> dict[str, Any]:
    query = {
        "Audited": "true",
        "AuditorRef": -1,
        "Category": -1,
        "Childs": "true",
        "CompanyState": -1,
        "CompanyType": -1,
        "Consolidatable": "true",
        "IsNotAudited": "false",
        "Length": -1,
        "LetterType": -1,
        "Mains": "true",
        "NotAudited": "true",
        "NotConsolidatable": "true",
        "PageNumber": 1,
        "Publisher": "false",
        "ReportingType": -1,
        "TracingNo": -1,
        "search": "true",
        **{k: v for k, v in params.items() if v is not None},
    }
    body = client.fetch_json(f"{SEARCH}/v2/q", query, ttl=ttl)
    if not isinstance(body, dict) or not isinstance(body.get("Letters"), list):
        raise CodalError("کدال نتیجهٔ جستجو برنگرداند.")
    return body


def _to_summary(x: dict[str, Any]) -> LetterSummary:
    return LetterSummary(
        tracing_no=int(x.get("TracingNo") or 0),
        symbol=to_ascii(x.get("Symbol")),
        company=to_ascii(x.get("CompanyName")),
        title=to_ascii(x.get("Title")),
        sent=to_ascii(x.get("SentDateTime")),
        code=to_ascii(x.get("LetterCode")) or None,
        published=to_ascii(x.get("PublishDateTime"))
        if x.get("PublishDateTime") and x.get("PublishDateTime") != x.get("SentDateTime")
        else None,
        has_html=bool(x.get("HasHtml")),
        has_pdf=bool(x.get("HasPdf")),
        has_excel=bool(x.get("HasExcel")),
        has_attachment=bool(x.get("HasAttachment")),
        under_supervision=bool(x.get("UnderSupervision")),
    )


def _pages_from_total(total: int) -> int:
    if total <= 0:
        return 0
    return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)


def search_letters(
    symbol: str | None = None,
    letter_type: int | None = None,
    category: int | None = None,
    period_months: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    title: str | None = None,
    letter_code: str | None = None,
    tracing_no: int | None = None,
    page: int = 1,
    *,
    client: CodalClient | None = None,
) -> SearchResult:
    """
    جستجوی یک صفحه از اطلاعیه‌های کدال (جدیدترین اول، حدود ۲۰ مورد در هر صفحه).

    Parameters
    ----------
    symbol :
        نماد دقیق فارسی (مثلاً شپنا، فولاد، خودرو)
    letter_type :
        شناسهٔ نوع گزارش در API (۶ = صورت‌های مالی، ۵۸ = فعالیت ماهانه، ...)
    category :
        گروه گزارش (۱ تا ۱۱)
    period_months :
        طول دوره: ۱۲ سالانه، ۶ شش‌ماهه، ۳ فصلی، ۱ ماهانه
    from_date / to_date :
        تاریخ شمسی ارسال (YYYY/MM/DD)
    title :
        کلمات داخل عنوان (Subject). عبارت خیلی طولانی ممکن است نتیجه ندهد.
    letter_code :
        کد رسمی اطلاعیه مثل ``ن-۴۲`` یا ``ن-30`` (پارامتر LetterCode).
        اگر API چیزی برنگرداند، از ``search_by_notice_code`` استفاده کنید
        که فیلتر سمت کلاینت هم دارد.
    tracing_no :
        شماره پیگیری یک اطلاعیهٔ خاص
    page :
        شماره صفحه (از ۱)
    """
    c = client or get_default_client()
    code = None
    if letter_code:
        # برای API اغلب شکل با ارقام انگلیسی کار می‌کند
        code = normalize_letter_code(letter_code) or str(letter_code).strip()

    body = _search_raw(
        c,
        {
            "Symbol": normalize_symbol(symbol),
            "Category": category,
            "LetterType": letter_type,
            "Subject": to_ascii(title) or None,
            "LetterCode": code,
            "FromDate": parse_jalali(from_date, "from_date"),
            "ToDate": parse_jalali(to_date, "to_date"),
            "Length": period_months,
            "TracingNo": tracing_no,
            "PageNumber": page,
        },
    )
    letters = [_to_summary(x) for x in body["Letters"] if isinstance(x, dict)]
    total = int(body.get("Total") or 0)
    # API فیلد Page را گاهی «تعداد صفحات» می‌دهد؛ ما از total مطمئن‌تر حساب می‌کنیم
    pages = _pages_from_total(total) or int(body.get("Page") or 1)
    return SearchResult(total=total, page=page, pages=pages, letters=letters)


def iter_letters(
    symbol: str | None = None,
    letter_type: int | None = None,
    category: int | None = None,
    period_months: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    title: str | None = None,
    letter_code: str | None = None,
    *,
    max_pages: int | None = None,
    client: CodalClient | None = None,
) -> Iterator[LetterSummary]:
    """
    پیمایش صفحه‌به‌صفحهٔ همهٔ نتایج جستجو (ژنراتور).

    Parameters
    ----------
    max_pages :
        سقف تعداد صفحات (مثلاً برای تست). ``None`` = همهٔ صفحات.
    """
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        result = search_letters(
            symbol=symbol,
            letter_type=letter_type,
            category=category,
            period_months=period_months,
            from_date=from_date,
            to_date=to_date,
            title=title,
            letter_code=letter_code,
            page=page,
            client=client,
        )
        if not result.letters:
            break
        yield from result.letters
        if page >= result.pages:
            break
        page += 1


def search_all(
    symbol: str | None = None,
    letter_type: int | None = None,
    category: int | None = None,
    period_months: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    title: str | None = None,
    letter_code: str | None = None,
    *,
    max_pages: int | None = None,
    client: CodalClient | None = None,
) -> list[LetterSummary]:
    """
    همهٔ صفحات جستجو را جمع می‌کند و یک لیست برمی‌گرداند.

    برای نمادهای پرت اطلاعیه ممکن است طول بکشد (rate-limit کدال).
    در صورت امکان ``letter_code`` یا ``letter_type`` یا بازهٔ تاریخ بگذارید.
    """
    return list(
        iter_letters(
            symbol=symbol,
            letter_type=letter_type,
            category=category,
            period_months=period_months,
            from_date=from_date,
            to_date=to_date,
            title=title,
            letter_code=letter_code,
            max_pages=max_pages,
            client=client,
        )
    )


def search_by_letter_type(
    symbol: str | None,
    letter_type: int,
    *,
    period_months: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    max_pages: int | None = None,
    client: CodalClient | None = None,
) -> list[LetterSummary]:
    """همهٔ اطلاعیه‌های یک ``letter_type`` عددی (مثلاً ۶ یا ۵۸)."""
    return search_all(
        symbol=symbol,
        letter_type=letter_type,
        period_months=period_months,
        from_date=from_date,
        to_date=to_date,
        max_pages=max_pages,
        client=client,
    )


def search_by_notice_code(
    symbol: str | None,
    notice_code: str,
    *,
    title_contains: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    max_pages: int | None = None,
    client: CodalClient | None = None,
) -> list[LetterSummary]:
    """
    همهٔ اطلاعیه‌های دارای یک کد رسمی (مثل ``ن-42`` یا ``ن-۴۲``).

    ابتدا فیلتر ``LetterCode`` را به API می‌دهد؛ اگر نتیجه خالی یا ناقص بود،
    روی نتایج نماد (بدون کد) فیلتر سمت کلاینت می‌زند.

    Parameters
    ----------
    title_contains :
        اگر مقدار داشته باشد، فقط عناوینی که این زیررشته را دارند نگه داشته می‌شوند
        (مثلاً ``عادی سالیانه`` برای جدا کردن از فوق‌العاده).
    max_pages :
        سقف صفحات در حالت اسکن کامل؛ ``None`` = همه.
    """
    target = normalize_letter_code(notice_code)
    if not target:
        raise CodalError("کد اطلاعیه خالی است.")

    c = client or get_default_client()

    def _match(L: LetterSummary) -> bool:
        if normalize_letter_code(L.code) != target:
            return False
        if title_contains and title_contains not in (L.title or ""):
            return False
        return True

    # ۱) تلاش با LetterCode در API
    via_api: list[LetterSummary] = []
    for variant in letter_code_variants(notice_code):
        via_api = search_all(
            symbol=symbol,
            letter_code=variant,
            from_date=from_date,
            to_date=to_date,
            max_pages=max_pages,
            client=c,
        )
        matched = [L for L in via_api if _match(L)]
        if matched:
            return matched
        # اگر API چیزی داد ولی کد فیلد خالی/متفاوت بود، همان‌ها را با title فیلتر کن
        if via_api and title_contains:
            titled = [L for L in via_api if title_contains in (L.title or "")]
            if titled:
                return titled
        if via_api:
            # نتایج آمده ولی کد جور نبود — باز هم برمی‌گردانیم اگر بدون title_contains
            if not title_contains:
                return via_api

    # ۲) اسکن روی نماد و فیلتر کد سمت کلاینت
    found: list[LetterSummary] = []
    for L in iter_letters(
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        max_pages=max_pages,
        client=c,
    ):
        if _match(L):
            found.append(L)
    return found
