"""
PharaghY_Codal
==============

کتابخانهٔ غیررسمی پایتون برای خواندن اطلاعیه‌ها و گزارش‌های سامانهٔ کدال
(https://www.codal.ir).

نقطهٔ ورود پیشنهادی::

    import pharaghy_codal as fpyc

    company = fpyc.get_company("شپنا")
    items = fpyc.search_by_notice_code("خودرو", "ن-42")
    letter = fpyc.get_letter(items[0].tracing_no)
    fpyc.download_all_files(items[0].tracing_no, "out")

گروه‌های اصلی API
-----------------
* شرکت: ``get_company``, ``get_financial_years``
* جستجو: ``search_letters``, ``search_all``, ``search_by_notice_code``, ...
* خواندن: ``get_letter``, ``list_files``, ``letter_content_kind``
* دانلود: ``download_excel``, ``download_pdf``, ``download_attachments``, ``download_all_files``
* مالی/ماهانه: ``get_income_statement``, ``get_monthly_activity``, ...
* تنظیمات شبکه: ``configure_client``, ``CodalClient``, ``CodalError``

کدال معمولاً فقط از داخل ایران یا با پروکسی ایرانی پاسخ می‌دهد.
"""

from __future__ import annotations

from . import constants
from .client import CodalClient, CodalError, configure_client
from .company import get_company, get_financial_years
from .constants import (
    NOTICE_CODES,
    NOTICE_GROUPS,
    list_notice_codes,
    notice_group_of,
    notice_title,
)
from .financials import (
    get_income_statement,
    get_letter_tables_as_frames,
    list_financial_letters,
    table_to_dataframe,
)
from .letter import (
    download_all_files,
    download_attachments,
    download_excel,
    download_file,
    download_pdf,
    get_letter,
    letter_content_kind,
    list_files,
)
from .models import Company, Letter, LetterSummary, LetterType, SearchResult
from .monthly import (
    find_monthly_letter,
    get_monthly_activity,
    get_monthly_materials,
    get_monthly_production_sales,
    list_monthly_letters,
)
from .search import (
    iter_letters,
    normalize_letter_code,
    search_all,
    search_by_letter_type,
    search_by_notice_code,
    search_letters,
)
from .types import get_letter_groups, get_letter_types

__version__ = "0.3.1"

# API پایدار برای import عمومی — تا 1.0 تا حد ممکن حفظ می‌شود
__all__ = [
    # meta
    "__version__",
    "constants",
    # errors / client
    "CodalClient",
    "CodalError",
    "configure_client",
    # models
    "Company",
    "Letter",
    "LetterSummary",
    "LetterType",
    "SearchResult",
    # company
    "get_company",
    "get_financial_years",
    # taxonomy
    "NOTICE_CODES",
    "NOTICE_GROUPS",
    "list_notice_codes",
    "notice_group_of",
    "notice_title",
    "get_letter_groups",
    "get_letter_types",
    "normalize_letter_code",
    # search
    "search_letters",
    "iter_letters",
    "search_all",
    "search_by_letter_type",
    "search_by_notice_code",
    # read
    "get_letter",
    "list_files",
    "letter_content_kind",
    # download
    "download_excel",
    "download_pdf",
    "download_file",
    "download_attachments",
    "download_all_files",
    # financial / monthly helpers
    "list_financial_letters",
    "get_income_statement",
    "get_letter_tables_as_frames",
    "table_to_dataframe",
    "list_monthly_letters",
    "find_monthly_letter",
    "get_monthly_activity",
    "get_monthly_materials",
    "get_monthly_production_sales",
]
