"""مدل‌های دادهٔ کتابخانه."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Company:
    symbol: str
    name: str
    isic: str | None = None
    market: str | None = None
    kind: str | None = None
    industry: str | None = None
    reporting_type: str | None = None


@dataclass
class LetterType:
    id: int
    name: str


@dataclass
class LetterGroup:
    category: int
    name: str
    letter_types_count: int = 0


@dataclass
class LetterSummary:
    tracing_no: int
    symbol: str
    company: str
    title: str
    sent: str
    code: str | None = None
    published: str | None = None
    has_html: bool = False
    has_pdf: bool = False
    has_excel: bool = False
    has_attachment: bool = False
    under_supervision: bool = False

    @property
    def files(self) -> list[str]:
        out = []
        if self.has_html:
            out.append("html")
        if self.has_pdf:
            out.append("pdf")
        if self.has_excel:
            out.append("excel")
        if self.has_attachment:
            out.append("attachments")
        return out


@dataclass
class SearchResult:
    total: int
    page: int
    pages: int
    letters: list[LetterSummary] = field(default_factory=list)


@dataclass
class TableBlock:
    """یک جدول از یک شیت گزارش کدال."""

    title: str
    rows: list[list[str]]  # هر ردیف لیست سلول‌ها


@dataclass
class Letter:
    tracing_no: int
    symbol: str
    company: str
    title: str
    sent: str
    url: str = ""
    code: str | None = None  # کد رسمی مثل ن-42
    pdf_url: str | None = None
    excel_url: str | None = None
    report: str | None = None
    period_months: int | None = None
    period_end: str | None = None
    year_end: str | None = None
    audited: bool | None = None
    consolidated: bool | None = None
    unit_note: str | None = None
    listed_capital: str | None = None
    sheet: int | None = None
    sheets: list[dict[str, Any]] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)
    text: str | None = None
    attachments: list[dict[str, str]] = field(default_factory=list)
    truncated: bool = False
