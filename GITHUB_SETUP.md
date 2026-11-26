# راهنمای انتشار روی GitHub

این فایل را بعد از ساخت ریپو می‌توانی حذف کنی یا در `docs/` بگذاری.

## ۱. ساخت ریپو

1. در GitHub یک Repository جدید بساز، مثلاً `PharaghY_Codal`
2. Public + بدون README خودکار (چون خودمان داریم)
3. در **About** ریپو (آیکون چرخ‌دنده کنار About):
   - Description: `Python library for Codal.ir disclosures (Iran TSE)`
   - Website: `https://t.me/bourse_faraghy`
   - Topics: `codal`, `iran`, `bourse`, `python`, `finance`
3. در **About** ریپو (دکمهٔ چرخ‌دنده کنار About):
   - Description: `Python library for Codal.ir disclosures (Iran TSE)`
   - Website: `https://t.me/bourse_faraghy`
   - Topics: `codal`, `iran`, `bourse`, `python`, `finance`

## ۲. از پوشهٔ پروژه

```bash
cd D:\PharaghY_Codal   # یا مسیر لینوکس/مک

# اگر هنوز git init نشده:
git init
git add .
git status   # مطمئن شو .venv و *.xlsx و __pycache__ داخل staging نیستند

git commit -m "Initial release: PharaghY_Codal 0.1.3"

git branch -M main
git remote add origin https://github.com/YOUR_USER/PharaghY_Codal.git
git push -u origin main
```

در `README.md` عبارت `YOUR_USER` را با نام کاربری GitHub خودت عوض کن.

## ۳. نصب برای دیگران

```bash
pip install git+https://github.com/YOUR_USER/PharaghY_Codal.git
```

## ۴. (اختیاری) انتشار روی PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

نام پکیج روی PyPI الان `PharaghY_Codal` است؛ در صورت نیاز می‌توانی به `pharaghy-codal` تغییرش بدهی.

## ۵. نکات قبل از push

- [ ] `LICENSE` و `README.md` کامل‌اند
- [ ] `.gitignore` جلوی commit شدن `.venv` و فایل‌های دانلود کدال را می‌گیرد
- [ ] تست‌ها: `pytest` (بدون live) پاس می‌شود
- [ ] روی یک نماد واقعی (`شپنا`) یک‌بار `get_income_statement` و `get_monthly_activity` را امتحان کرده‌ای
