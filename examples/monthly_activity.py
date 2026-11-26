"""مثال: گزارش فعالیت ماهانه و موضوعات جداول."""
from pharaghy_codal import get_monthly_activity, list_monthly_letters

SYMBOL = "شپنا"

print("آخرین گزارش‌های ماهانه:")
for row in list_monthly_letters(SYMBOL)[:5]:
    print(f"  {row['tracing_no']}  {row['title']}")

data = get_monthly_activity(SYMBOL)
print("\nmeta:", data["meta"])
print("topics:", {k: len(v) for k, v in data["tables"].items()})
