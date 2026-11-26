"""تست‌های واحد بدون شبکه برای نام فایل و نوع محتوا."""

from pathlib import Path

from pharaghy_codal.letter import (
    _guess_extension,
    _safe_filename,
    _with_extension,
    letter_content_kind,
)
from pharaghy_codal.models import Letter


def test_guess_pdf():
    assert _guess_extension(b"%PDF-1.4 rest") == ".pdf"


def test_guess_xlsx():
    data = b"PK\x03\x04" + b" " * 100 + b"xl/worksheets/sheet1.xml"
    assert _guess_extension(data) == ".xlsx"


def test_guess_html_excel():
    data = b"<html xmlns:x=\"urn:schemas-microsoft-com:office:excel\">"
    assert _guess_extension(data) in {".xls.html", ".html"}


def test_safe_filename():
    assert "<" not in _safe_filename('a<b>c')
    assert _safe_filename("  ") == "file"


def test_with_extension():
    assert _with_extension(Path("x"), ".pdf").name == "x.pdf"
    assert _with_extension(Path("x.pdf"), ".pdf").name == "x.pdf"


def test_content_kind_empty():
    L = Letter(1, "s", "c", "t", "d")
    assert letter_content_kind(L) == "empty"


def test_content_kind_files():
    L = Letter(1, "s", "c", "t", "d", attachments=[{"url": "http://x"}])
    assert letter_content_kind(L) == "files_only"


def test_content_kind_text():
    L = Letter(1, "s", "c", "t", "d", text="hello")
    assert letter_content_kind(L) == "text"
