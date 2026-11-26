"""مثال: صورت سود و زیان سالانه یک نماد."""
from pharaghy_codal import get_company, get_income_statement

SYMBOL = "شپنا"

company = get_company(SYMBOL)
print(f"{company.symbol} | {company.name} | {company.market}")

df = get_income_statement(SYMBOL, period_months=12)
print("عنوان:", df.attrs.get("title"))
print("پایان دوره:", df.attrs.get("period_end"))
print("واحد:", df.attrs.get("unit_note"))
print(df.head(15).to_string(index=False))
