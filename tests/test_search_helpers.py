from pharaghy_codal.search import normalize_letter_code, letter_code_variants


def test_normalize_letter_code():
    assert normalize_letter_code("ن-۴۲") == "ن-42"
    assert normalize_letter_code("ن-42") == "ن-42"
    assert normalize_letter_code(" ن-۳۰ ") == "ن-30"
    assert normalize_letter_code("ن30") == "ن-30"


def test_variants():
    vs = letter_code_variants("ن-42")
    assert "ن-42" in vs
    assert any("۴" in v or "۲" in v for v in vs) or "ن-42" in vs
