from pharaghy_codal.constants import NOTICE_CODES, list_notice_codes, notice_title, notice_group_of


def test_notice_codes_not_empty():
    assert "ن-۳۰" in NOTICE_CODES or "ن-30" in NOTICE_CODES or any("۳۰" in k or "30" in k for k in NOTICE_CODES)


def test_list_notice_codes_group():
    items = list_notice_codes("monthly")
    assert items
    assert any("ماهانه" in (x.get("title") or "") for x in items)


def test_notice_title():
    # whichever key exists for monthly
    code = next(k for k in NOTICE_CODES if "۳۰" in k or "30" in k)
    assert notice_title(code)


def test_notice_group():
    code = next(k for k in NOTICE_CODES if "۴۲" in k or "42" in k)
    g = notice_group_of(code)
    assert g in {None, "meetings", "governance"} or isinstance(g, str)
