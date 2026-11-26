"""مثال: جستجوی اطلاعیه‌های مرتبط با افزایش سرمایه."""
from pharaghy_codal import get_letter_types, search_letters
from pharaghy_codal.constants import CATEGORY_CAPITAL_INCREASE

SYMBOL = "شپنا"

print("انواع گزارش گروه افزایش سرمایه:")
for t in get_letter_types(CATEGORY_CAPITAL_INCREASE):
    print(f"  id={t.id}  {t.name}")

res = search_letters(symbol=SYMBOL, category=CATEGORY_CAPITAL_INCREASE)
print(f"\n{res.total} نتیجه — صفحه {res.page}/{res.pages}")
for L in res.letters[:10]:
    print(f"  {L.tracing_no}  {L.sent}  {L.title}")
