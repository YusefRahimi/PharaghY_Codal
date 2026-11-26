"""تست‌های واحد بدون اتصال به کدال برای منطق financials."""

from pharaghy_codal.financials import _flatten_col_name, _score_financial_letter
from pharaghy_codal.models import LetterSummary


def test_flatten_tuple_column():
    assert "1404/12/29" in _flatten_col_name(("دوره منتهي به 1404/12/29", "حسابرسی شده"))


def test_flatten_string_tuple_column():
    s = "('دوره منتهي به 1404/12/29', 'حسابرسی شده')"
    assert "1404/12/29" in _flatten_col_name(s)


def test_score_prefers_consolidated_over_subsidiary():
    main = LetterSummary(
        tracing_no=1,
        symbol="شپنا",
        company="پالایش",
        title="صورت‌های مالی تلفیقی سال مالی منتهی به 1404/12/29 (حسابرسی شده)",
        sent="",
    )
    sub = LetterSummary(
        tracing_no=2,
        symbol="شپنا",
        company="فرعی",
        title="صورت‌های مالی سال مالی منتهی به 1404/09/30 (حسابرسی شده) (شرکت راهبر ترابر انرژی)",
        sent="",
    )
    assert _score_financial_letter(main, "شپنا") > _score_financial_letter(sub, "شپنا")
