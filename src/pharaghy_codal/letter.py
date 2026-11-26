"""خواندن یک اطلاعیه کدال و دانلود فایل‌های اکسل، PDF و پیوست."""

from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from .client import SEARCH, WWW, CodalClient, CodalError, get_default_client
from .models import Letter, TableBlock
from .search import _search_raw, _to_summary
from .utils import to_ascii

LETTER_TTL = 3600
MAX_TEXT = 50_000  # برای کتابخانه محدودیت نرم‌تری نسبت به MCP


def _meta_from_text(text: str) -> dict[str, str | None]:
    """استخراج چند فیلد متداول از متن قابل‌مشاهدهٔ صفحه وقتی datasource نیست."""
    out: dict[str, str | None] = {
        "unit_note": None,
        "period_end": None,
        "listed_capital": None,
    }
    m = re.search(r"کلیه مبالغ[^\n]*", text)
    if m:
        out["unit_note"] = to_ascii(m.group(0))
    m = re.search(r"سال مالی منتهی به[:\s]*([0-9/]+)", text)
    if m:
        out["period_end"] = to_ascii(m.group(1))
    m = re.search(r"سرمایه ثبت شده[:\s]*([0-9,٬]+)", text)
    if m:
        out["listed_capital"] = to_ascii(m.group(1))
    return out


def _tables_from_excel_bytes(data: bytes) -> tuple[list[TableBlock], list[dict[str, Any]]]:
    """
    پارس خروجی «اکسل» کدال به TableBlock.

    کدال اغلب به‌جای xlsx واقعی، HTML سازگار با Excel برمی‌گرداند
    (xmlns office:excel). گاهی هم xlsx واقعی است.
    """
    import io

    tables: list[TableBlock] = []
    sheets_meta: list[dict[str, Any]] = []

    head = data[:300].lstrip().lower()
    is_html = head.startswith(b"<") or b"html" in head or b"xmlns" in head

    if is_html:
        html = data.decode("utf-8", errors="replace")
        sheet_names = [
            to_ascii(a or b)
            for a, b in re.findall(r"<x:Name>([^<]+)</x:Name>|<title>([^<]*)</title>", html, flags=re.I)
            if (a or b)
        ]
        dfs = []
        try:
            import pandas as pd

            dfs = pd.read_html(io.StringIO(html), flavor="lxml")
        except Exception:
            try:
                import pandas as pd

                dfs = pd.read_html(io.StringIO(html))
            except Exception:
                dfs = []

        if not dfs:
            # جداول خام HTML بدون pandas
            class _TableParser(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self.tables: list[list[list[str]]] = []
                    self._table: list[list[str]] | None = None
                    self._row: list[str] | None = None
                    self._cell: list[str] | None = None

                def handle_starttag(self, tag, attrs):
                    if tag == "table":
                        self._table = []
                    elif tag == "tr" and self._table is not None:
                        self._row = []
                    elif tag in ("td", "th") and self._row is not None:
                        self._cell = []

                def handle_endtag(self, tag):
                    if tag in ("td", "th") and self._cell is not None and self._row is not None:
                        self._row.append(to_ascii("".join(self._cell)))
                        self._cell = None
                    elif tag == "tr" and self._row is not None and self._table is not None:
                        if any(c.strip() for c in self._row):
                            self._table.append(self._row)
                        self._row = None
                    elif tag == "table" and self._table is not None:
                        if self._table:
                            self.tables.append(self._table)
                        self._table = None

                def handle_data(self, data):
                    if self._cell is not None:
                        self._cell.append(data)

            p = _TableParser()
            p.feed(html)
            for i, rows in enumerate(p.tables):
                title = sheet_names[i] if i < len(sheet_names) else f"جدول {i + 1}"
                tables.append(TableBlock(title=title, rows=rows))
                sheets_meta.append({"sheet": i, "name": title})
            return tables, sheets_meta

        for i, df in enumerate(dfs):
            title = (
                sheet_names[i]
                if i < len(sheet_names)
                else (str(df.columns[0]) if len(df.columns) else f"جدول {i + 1}")
            )
            title = to_ascii(title)

            def _col_label(c: object) -> str:
                # MultiIndex / tuple از read_html
                if isinstance(c, tuple):
                    parts = []
                    for p in c:
                        s = to_ascii(p).strip()
                        if not s or s.lower().startswith("unnamed") or s == "nan":
                            continue
                        if s not in parts:
                            parts.append(s)
                    # ترجیح بخش دارای تاریخ/دوره
                    for p in parts:
                        if "منتهي" in p or "منتهی" in p or re.search(r"\d{4}/\d{2}", p):
                            return p
                    # حذف برچسب تکراری حسابرسی اگر بخش دیگری هست
                    parts = [p for p in parts if "حسابرس" not in p] or parts
                    return parts[0] if len(parts) == 1 else " | ".join(parts) if parts else ""
                return to_ascii(c)

            header = [_col_label(c) for c in df.columns.tolist()]
            rows = [header]
            for _, series in df.iterrows():
                rows.append(
                    [
                        "" if (isinstance(v, float) and v != v) else to_ascii(v)
                        for v in series.tolist()
                    ]
                )
            tables.append(TableBlock(title=title, rows=rows))
            sheets_meta.append({"sheet": i, "name": title})
        return tables, sheets_meta

    # xlsx واقعی
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise CodalError("برای خواندن اکسل کدال به openpyxl نیاز است.") from e

    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    for idx, name in enumerate(wb.sheetnames):
        ws = wb[name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else to_ascii(v) for v in row]
            while vals and vals[-1] == "":
                vals.pop()
            if any(v != "" for v in vals):
                rows.append(vals)
        if rows:
            tables.append(TableBlock(title=to_ascii(name), rows=rows))
            sheets_meta.append({"sheet": idx, "name": to_ascii(name)})
    wb.close()
    return tables, sheets_meta


class _VisibleText(HTMLParser):
    """استخراج متن قابل‌مشاهده از صفحهٔ اطلاعیه."""

    VOID = {"br", "img", "input", "meta", "link", "hr", "col", "area", "base", "wbr", "source"}
    BLOCK = {"div", "p", "tr", "table", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "ul", "ol", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[tuple[str, bool]] = []

    def _hidden(self) -> bool:
        return bool(self.stack) and self.stack[-1][1]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        a = dict(attrs)
        style = re.sub(r"\s", "", (a.get("style") or "").lower())
        hidden = (
            self._hidden()
            or tag in ("script", "style", "head", "select", "option", "noscript")
            or "display:none" in style
            or a.get("type") == "hidden"
        )
        if tag in self.VOID:
            if tag == "br" and not hidden:
                self.out.append("\n")
            return
        self.stack.append((tag, hidden))
        if not hidden and tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                hidden = self.stack[i][1]
                del self.stack[i:]
                if not hidden:
                    self.out.append(" | " if tag in ("td", "th") else "\n" if tag in self.BLOCK else "")
                return

    def handle_data(self, data: str) -> None:
        if not self._hidden():
            self.out.append(re.sub(r"\s+", " ", data))

    def text(self) -> str:
        lines = []
        for line in "".join(self.out).split("\n"):
            line = to_ascii(line).strip(" |")
            line = re.sub(r"(\s*\|\s*){2,}", " | ", line)
            if line and line != "|":
                lines.append(line)
        return "\n".join(lines)


def _visible_text(html: str) -> str:
    p = _VisibleText()
    body = html.find("<body")
    p.feed(html[body:] if body >= 0 else html)
    p.close()
    return p.text()


def _datasource(html: str) -> dict[str, Any] | None:
    i = html.find("var datasource = ")
    if i < 0:
        return None
    try:
        d, _ = json.JSONDecoder().raw_decode(html, i + len("var datasource = "))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def _parse_tables(ds: dict[str, Any]) -> list[TableBlock]:
    out: list[TableBlock] = []
    for sheet in ds.get("sheets") or []:
        for t in sheet.get("tables") or []:
            rows_map: dict[int, list[dict[str, Any]]] = {}
            for cell in t.get("cells") or []:
                if isinstance(cell, dict):
                    rows_map.setdefault(cell.get("rowSequence") or 0, []).append(cell)
            lines: list[list[str]] = []
            for k in sorted(rows_map):
                cells = rows_map[k]
                if not any(c.get("isVisible", True) for c in cells):
                    continue
                vals = [
                    to_ascii(c.get("value"))
                    for c in sorted(cells, key=lambda c: c.get("columnSequence") or 0)
                ]
                while vals and not vals[-1]:
                    vals.pop()
                if vals:
                    lines.append(vals)
            if lines:
                title = to_ascii(t.get("title_Fa") or sheet.get("title_Fa"))
                out.append(TableBlock(title=title, rows=lines))
    return out


def _sheets(html: str) -> list[dict[str, Any]]:
    m = re.search(r'<select[^>]*name="ctl00\$ddlTable".*?</select>', html, re.S)
    if not m:
        return []
    return [
        {"sheet": int(v), "name": to_ascii(unescape(n))}
        for v, n in re.findall(r'<option[^>]*value="(-?\d+)"[^>]*>([^<]*)', m[0])
    ]


def _label(html: str, id_: str) -> str:
    m = re.search(rf'id="{id_}"[^>]*>([^<]*)<', html)
    return to_ascii(unescape(m[1])) if m else ""


def _attachments(html: str) -> list[dict[str, str]]:
    out = []
    rows = re.findall(
        r"window\.open\('(DownloadFile\.aspx\?id=[^']+)'\);\"[^>]*>(.*?)</tr>",
        unescape(html),
        re.S,
    )
    for link, cells in rows:
        tds = [to_ascii(re.sub(r"<[^>]+>", " ", td)) for td in re.findall(r"<td[^>]*>(.*?)</td>", cells, re.S)]
        tds = [t for t in tds if t]
        out.append(
            {
                "name": tds[0] if tds else "",
                "added": tds[1] if len(tds) > 1 else "",
                "url": f"{WWW}/Reports/{link}",
            }
        )
    return out


def _split(path: str) -> tuple[str, dict[str, str]]:
    u = urlsplit(path)
    p = u.path if u.path.startswith("/") else f"/{u.path}"
    return f"{WWW}{p}", dict(parse_qsl(u.query))


def _link(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"{WWW}{path if path.startswith('/') else '/' + path}"


def get_letter(
    tracing_no: int,
    sheet: int | None = None,
    *,
    client: CodalClient | None = None,
) -> Letter:
    """
    خواندن یک اطلاعیه با شماره پیگیری.

    برای صورت‌های مالی و گزارش‌های ساختاریافته، جداول در `tables` برمی‌گردد.
    برای خواندن شیت دیگر، دوباره با `sheet` صدا بزنید.
    """
    c = client or get_default_client()
    body = _search_raw(c, {"TracingNo": tracing_no}, ttl=LETTER_TTL)
    found = [
        x
        for x in body["Letters"]
        if isinstance(x, dict) and int(x.get("TracingNo") or 0) == int(tracing_no)
    ]
    if not found:
        raise CodalError(f"اطلاعیه‌ای با شماره پیگیری {tracing_no} پیدا نشد.")

    x = found[0]
    summary = _to_summary(x)
    url = x.get("Url") or ""
    # بعضی رکوردها HasPdf=true ولی PdfUrl خالی است یا برعکس؛ اگر URL باشد نگه می‌داریم
    pdf_raw = (x.get("PdfUrl") or "").strip()
    excel_raw = (x.get("ExcelUrl") or "").strip()
    letter = Letter(
        tracing_no=summary.tracing_no,
        symbol=summary.symbol,
        company=summary.company,
        title=summary.title,
        sent=summary.sent,
        url=_link(url),
        code=summary.code,
        pdf_url=_link(pdf_raw) if pdf_raw else None,
        excel_url=_link(excel_raw) if excel_raw else None,
    )

    # --- صفحه HTML (در صورت وجود) ---
    html = ""
    if url and (x.get("HasHtml") or "Decision.aspx" in url or "Report" in url):
        page_url, params = _split(url)
        if sheet is not None:
            params["sheetId"] = str(sheet)
        try:
            html = c.fetch_text(page_url, params, ttl=LETTER_TTL)
        except CodalError:
            html = ""

    if html:
        ds = _datasource(html)
        if ds:
            letter.report = to_ascii(ds.get("title_Fa")) or None
            letter.period_months = ds.get("period")
            letter.period_end = to_ascii(ds.get("periodEndToDate")) or None
            letter.year_end = to_ascii(ds.get("yearEndToDate")) or None
            letter.audited = ds.get("isAudited")
            letter.consolidated = ds.get("isConsolidated")
            letter.unit_note = _label(html, "ctl00_pPriceNote") or None
            letter.listed_capital = _label(html, "ctl00_lblListedCapital") or None
            sheets = _sheets(html)
            if sheets:
                letter.sheets = sheets
                shown = re.search(r'<option selected="selected" value="(-?\d+)"', html)
                letter.sheet = int(shown[1]) if shown else sheet
            tables = _parse_tables(ds)
            size = 0
            kept: list[TableBlock] = []
            for t in tables:
                size += sum(len("|".join(r)) + 1 for r in t.rows)
                if size > MAX_TEXT and kept:
                    letter.truncated = True
                    break
                kept.append(t)
            letter.tables = kept
        else:
            # ساختار جدید کدال: اغلب datasource دیگر در HTML نیست
            text = _visible_text(html)
            meta = _meta_from_text(text)
            letter.unit_note = meta.get("unit_note") or letter.unit_note
            letter.period_end = meta.get("period_end") or letter.period_end
            letter.listed_capital = meta.get("listed_capital") or letter.listed_capital
            if len(text) > MAX_TEXT:
                letter.text = text[:MAX_TEXT]
                letter.truncated = True
            else:
                letter.text = text

    # --- اگر جدول از HTML نیامد، از اکسل رسمی کدال بخوان ---
    if not letter.tables and letter.excel_url:
        try:
            content = c.fetch_bytes(letter.excel_url)
            if content:
                tables, sheets_meta = _tables_from_excel_bytes(content)
                letter.tables = tables
                if sheets_meta and not letter.sheets:
                    letter.sheets = sheets_meta
        except Exception:
            # اکسل اختیاری است؛ اگر نشد همان متن HTML می‌ماند
            pass

    if x.get("HasAttachment") and x.get("AttachmentUrl"):
        try:
            page_url, params = _split(x["AttachmentUrl"])
            letter.attachments = _attachments(c.fetch_text(page_url, params, ttl=LETTER_TTL))
        except CodalError:
            pass

    return letter



def _letter_raw(tracing_no: int, client: CodalClient) -> dict[str, Any]:
    """رکورد خام JSON یک اطلاعیه از API جستجو."""
    body = _search_raw(client, {"TracingNo": tracing_no}, ttl=LETTER_TTL)
    found = [
        x
        for x in body["Letters"]
        if isinstance(x, dict) and int(x.get("TracingNo") or 0) == int(tracing_no)
    ]
    if not found:
        raise CodalError(f"اطلاعیه‌ای با شماره پیگیری {tracing_no} پیدا نشد.")
    return found[0]


def _guess_extension(data: bytes, hint: str = "") -> str:
    """پسوند فایل از روی امضای باینری (و در صورت نیاز نام پیشنهادی)."""
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data[:2] == b"PK":
        if b"xl/" in data[:2000] or b"worksheets" in data[:4000]:
            return ".xlsx"
        return ".zip"
    head = data[:200].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"office:excel" in data[:500]:
        if b"office:excel" in data[:2000] or b"Excel" in data[:500]:
            return ".xls.html"
        return ".html"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG"):
        return ".png"
    hint_l = (hint or "").lower()
    for e in (".pdf", ".xlsx", ".xls", ".doc", ".docx", ".jpg", ".png", ".zip"):
        if hint_l.endswith(e):
            return e
    return ""


def _safe_filename(name: str, default: str = "file") -> str:
    name = to_ascii(name).strip() or default
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:120] or default


def _with_extension(path: Path, ext: str) -> Path:
    if not ext:
        return path
    if path.suffix.lower() == ext.lower():
        return path
    if path.suffix and path.suffix.lower() not in {".bin", ".tmp", ".dat"}:
        return path
    if path.suffix:
        return Path(str(path) + ext)
    return path.with_suffix(ext)


def _save_url(
    client: CodalClient,
    url: str,
    path: Path,
    *,
    name_hint: str = "",
    force_ext: str | None = None,
) -> Path:
    """دانلود URL و ذخیره با پسوند مناسب (بر اساس محتوای فایل)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = client.fetch_bytes(url)
    if not data:
        raise CodalError(f"دانلود ناموفق بود یا فایل خالی است: {url}")
    ext = force_ext if force_ext is not None else _guess_extension(data, name_hint or path.name)
    path = _with_extension(path, ext)
    path.write_bytes(data)
    if path.stat().st_size == 0:
        raise CodalError(f"دانلود ناموفق بود یا فایل خالی است: {path}")
    return path


def download_excel(
    tracing_no: int,
    path: str | Path,
    *,
    client: CodalClient | None = None,
) -> Path:
    """
    دانلود فایل اکسل اصلی کدال برای یک اطلاعیه و ذخیره در ``path``.

    توجه: پاسخ کدال گاهی HTML سازگار با اکسل است نه xlsx واقعی.
    """
    c = client or get_default_client()
    x = _letter_raw(tracing_no, c)
    excel = (x.get("ExcelUrl") or "").strip()
    if not excel:
        raise CodalError(f"اطلاعیه {tracing_no} لینک اکسل ندارد.")
    return _save_url(c, _link(excel), Path(path), name_hint="report.xlsx")


def download_pdf(
    tracing_no: int,
    path: str | Path,
    *,
    client: CodalClient | None = None,
    prefer_attachment: bool = True,
) -> Path:
    """
    دانلود فایل PDF اطلاعیه و ذخیره در ``path``.

    ترتیب تلاش:
    1) ``PdfUrl`` در متادیتای جستجو
    2) ``letter.pdf_url`` پس از ``get_letter``
    3) اگر ``prefer_attachment`` باشد: پیوست مناسب / اولین پیوست
    """
    c = client or get_default_client()
    x = _letter_raw(tracing_no, c)
    pdf = (x.get("PdfUrl") or "").strip()
    if pdf:
        return _save_url(c, _link(pdf), Path(path), name_hint="file.pdf", force_ext=".pdf")

    letter = get_letter(tracing_no, client=c)
    if letter.pdf_url:
        return _save_url(c, letter.pdf_url, Path(path), name_hint="file.pdf", force_ext=".pdf")

    if prefer_attachment and letter.attachments:
        ordered = sorted(
            letter.attachments,
            key=lambda a: (
                0
                if "pdf" in ((a.get("name") or "") + (a.get("url") or "")).lower()
                else 1
            ),
        )
        att = ordered[0]
        url = (att.get("url") or "").strip()
        if url:
            u = url if url.startswith("http") else _link(url)
            return _save_url(c, u, Path(path), name_hint=att.get("name") or "file.pdf")

    raise CodalError(f"اطلاعیه {tracing_no} لینک PDF و پیوست قابل‌دانلود ندارد.")


def download_file(
    url: str,
    path: str | Path,
    *,
    client: CodalClient | None = None,
) -> Path:
    """دانلود یک URL کدال (PDF، پیوست، اکسل و ...) و ذخیره در ``path``."""
    c = client or get_default_client()
    u = (url or "").strip()
    if not u:
        raise CodalError("آدرس فایل خالی است.")
    if not u.startswith("http"):
        u = _link(u)
    return _save_url(c, u, Path(path), name_hint=Path(path).name)


def download_attachments(
    tracing_no: int,
    directory: str | Path,
    *,
    client: CodalClient | None = None,
) -> list[Path]:
    """
    همهٔ پیوست‌های یک اطلاعیه را در پوشهٔ ``directory`` ذخیره می‌کند.
    پسوند فایل از روی محتوا تشخیص داده می‌شود.
    """
    c = client or get_default_client()
    letter = get_letter(tracing_no, client=c)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for i, att in enumerate(letter.attachments or [], start=1):
        url = (att.get("url") or "").strip()
        if not url:
            continue
        name = _safe_filename(att.get("name") or f"attachment_{i}", f"attachment_{i}")
        path = directory / f"{tracing_no}_{i}_{name}"
        try:
            u = url if url.startswith("http") else _link(url)
            saved.append(_save_url(c, u, path, name_hint=name))
        except CodalError:
            continue
    return saved


def download_all_files(
    tracing_no: int,
    directory: str | Path,
    *,
    client: CodalClient | None = None,
    include_page: bool = False,
) -> list[Path]:
    """
    اکسل، PDF و پیوست‌های اطلاعیه را در ``directory`` ذخیره می‌کند.
    """
    c = client or get_default_client()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    letter = get_letter(tracing_no, client=c)

    if letter.excel_url:
        try:
            saved.append(
                _save_url(c, letter.excel_url, directory / f"{tracing_no}_excel", name_hint="excel.xlsx")
            )
        except CodalError:
            pass
    if letter.pdf_url:
        try:
            saved.append(
                _save_url(
                    c,
                    letter.pdf_url,
                    directory / f"{tracing_no}_pdf",
                    name_hint="file.pdf",
                    force_ext=".pdf",
                )
            )
        except CodalError:
            pass

    for path in download_attachments(tracing_no, directory, client=c):
        if path not in saved:
            saved.append(path)

    if not letter.pdf_url and not any(x.suffix.lower() == ".pdf" for x in saved):
        try:
            path = download_pdf(tracing_no, directory / f"{tracing_no}.pdf", client=c)
            if path not in saved:
                saved.append(path)
        except CodalError:
            pass

    if include_page and letter.url:
        try:
            saved.append(
                _save_url(c, letter.url, directory / f"{tracing_no}_page", name_hint="page.html")
            )
        except CodalError:
            pass
    return saved


def list_files(
    tracing_no: int,
    *,
    client: CodalClient | None = None,
) -> list[dict[str, Any]]:
    """
    فهرست همه منابع قابل دانلود یک اطلاعیه.

    هر آیتم: ``kind`` (pdf | excel | attachment | page)، ``url``، ``name``، ``source``.
    """
    c = client or get_default_client()
    letter = get_letter(tracing_no, client=c)
    files: list[dict[str, Any]] = []

    if letter.excel_url:
        files.append(
            {"kind": "excel", "url": letter.excel_url, "name": f"{tracing_no}.xlsx", "source": "ExcelUrl"}
        )
    if letter.pdf_url:
        files.append(
            {"kind": "pdf", "url": letter.pdf_url, "name": f"{tracing_no}.pdf", "source": "PdfUrl"}
        )
    for i, att in enumerate(letter.attachments or [], start=1):
        url = (att.get("url") or "").strip()
        if not url:
            continue
        files.append(
            {
                "kind": "attachment",
                "url": url,
                "name": att.get("name") or f"attachment_{i}",
                "added": att.get("added") or "",
                "source": "Attachment",
            }
        )
    if letter.url:
        files.append(
            {"kind": "page", "url": letter.url, "name": f"{tracing_no}_page", "source": "Url"}
        )
    return files


def letter_content_kind(letter: Letter) -> str:
    """
    برچسب نوع محتوای اصلی اطلاعیه برای UI.

    یکی از: ``tables`` | ``text`` | ``files_only`` | ``empty``
    """
    if letter.tables:
        return "tables"
    if letter.text and letter.text.strip():
        return "text"
    if letter.attachments or letter.pdf_url or letter.excel_url:
        return "files_only"
    return "empty"
