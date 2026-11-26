"""نمایش کدهای رسمی اطلاعیه کدال به‌صورت گروه‌بندی‌شده."""

from pharaghy_codal.constants import (
    NOTICE_GROUP_LABELS_FA,
    NOTICE_GROUPS,
    list_notice_codes,
)


def main() -> None:
    for group, label in NOTICE_GROUP_LABELS_FA.items():
        print(f"\n=== {label} ({group}) ===")
        for item in list_notice_codes(group):
            print(f"  {item['code']}: {item['title']}")


if __name__ == "__main__":
    main()
