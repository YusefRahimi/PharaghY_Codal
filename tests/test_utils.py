"""تست‌های واحد بدون اتصال به کدال."""

from pharaghy_codal.utils import normalize_key, normalize_symbol, parse_jalali, parse_number, to_ascii


def test_to_ascii_digits():
    assert to_ascii("۱۴۰۳") == "1403"
    assert to_ascii("سال ۱۳۹۹") == "سال 1399"


def test_normalize_symbol():
    assert normalize_symbol(" شپنا ") == "شپنا"
    assert normalize_symbol("") is None


def test_normalize_key():
    assert normalize_key("فولاد") == normalize_key("فولاد")
    assert "ي" not in normalize_key("ولي")  # ي عربی → ی


def test_parse_jalali():
    assert parse_jalali("1403/7/1") == "1403/07/01"
    assert parse_jalali("۱۴۰۳-۰۷-۰۱") == "1403/07/01"
    assert parse_jalali(None) is None


def test_parse_number():
    assert parse_number("1,234") == 1234.0
    assert parse_number("(500)") == -500.0
    assert parse_number("-100") == -100.0
    assert parse_number("-") is None
    assert parse_number(None) is None
