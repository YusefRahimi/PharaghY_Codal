"""
لایهٔ HTTP برای ارتباط با کدال.

- فاصله بین درخواست‌ها + retry روی timeout / قطع اتصال / HTTP 429
- پروکسی: PHARAGHY_CODAL_PROXY
- تنظیمات اختیاری از محیط:
  PHARAGHY_CODAL_TIMEOUT, PHARAGHY_CODAL_MIN_INTERVAL,
  PHARAGHY_CODAL_MAX_RETRIES, PHARAGHY_CODAL_CACHE_DIR
- کش حافظه + کش دیسک اختیاری
"""

from __future__ import annotations

import copy
import os
import random
import time
from typing import Any

import httpx

SEARCH = "https://search.codal.ir/api/search"
WWW = "https://www.codal.ir"
EXCEL = "https://excel.codal.ir"

MIN_INTERVAL = 2.0
JITTER = (0.2, 0.8)
BLOCK_COOLDOWN = 60
MAX_RATE_LIMIT_RETRIES = 3  # چند بار بعد از 429 صبر و تکرار
CACHE_MAX = 64
MAX_BODY = 8_000_000
MAX_RETRIES = 3
RETRY_BACKOFF = (2.0, 4.0, 8.0)  # seconds between network retries

HEADERS = {
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

PAGE_HEADERS = {
    **HEADERS,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Upgrade-Insecure-Requests": "1",
}


class CodalError(Exception):
    """خطای ارتباط با کدال یا پاسخ نامعتبر."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class CodalClient:
    """کلاینت همگام برای API و صفحات کدال."""

    def __init__(
        self,
        proxy: str | None = None,
        min_interval: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cache_dir: str | None = None,
    ):
        """
        Parameters
        ----------
        proxy :
            آدرس پروکسی؛ پیش‌فرض از PHARAGHY_CODAL_PROXY
        min_interval :
            حداقل ثانیه بین دو درخواست (پیش‌فرض ۲ یا env)
        timeout :
            مهلت کل درخواست به ثانیه (پیش‌فرض ۴۵ یا env)
        max_retries :
            تعداد تلاش مجدد شبکه (پیش‌فرض ۳ یا env)
        cache_dir :
            اگر مسیر بدهی، پاسخ‌های JSON/متن روی دیسک هم کش می‌شوند
        """
        env_proxy = os.environ.get("PHARAGHY_CODAL_PROXY", "").strip()
        self._proxy = proxy or env_proxy or None

        def _env_float(name: str, default: float) -> float:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        def _env_int(name: str, default: int) -> int:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        self._min_interval = (
            MIN_INTERVAL if min_interval is None else float(min_interval)
        )
        if min_interval is None:
            self._min_interval = _env_float("PHARAGHY_CODAL_MIN_INTERVAL", MIN_INTERVAL)

        self._timeout = 45.0 if timeout is None else float(timeout)
        if timeout is None:
            self._timeout = _env_float("PHARAGHY_CODAL_TIMEOUT", 45.0)

        self._max_retries = MAX_RETRIES if max_retries is None else int(max_retries)
        if max_retries is None:
            self._max_retries = _env_int("PHARAGHY_CODAL_MAX_RETRIES", MAX_RETRIES)

        env_cache = os.environ.get("PHARAGHY_CODAL_CACHE_DIR", "").strip()
        self._cache_dir = cache_dir or env_cache or None
        if self._cache_dir:
            os.makedirs(self._cache_dir, exist_ok=True)

        self._last = 0.0
        self._blocked_until = 0.0
        self._cache: dict[tuple, tuple[float, float, Any]] = {}
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers=HEADERS,
                timeout=httpx.Timeout(self._timeout, connect=20.0),
                proxy=self._proxy,
                follow_redirects=True,
                trust_env=False,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> CodalClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _wait(self) -> None:
        """صبر برای فاصله بین درخواست‌ها و پایان cooldown مربوط به 429."""
        now = time.monotonic()
        if self._blocked_until > now:
            time.sleep(self._blocked_until - now + random.uniform(0.2, 1.0))
        now = time.monotonic()
        wait = self._last + self._min_interval + random.uniform(*JITTER) - now
        if wait > 0:
            time.sleep(wait)

    def _cache_key_str(self, key: tuple) -> str:
        import hashlib
        import json

        raw = json.dumps(key, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]

    def _cache_get(self, key: tuple) -> Any | None:
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < hit[1]:
            return copy.deepcopy(hit[2])
        if self._cache_dir:
            import json
            from pathlib import Path

            path = Path(self._cache_dir) / f"{self._cache_key_str(key)}.json"
            if path.is_file():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    saved_at = float(payload.get("saved_at") or 0)
                    ttl = float(payload.get("ttl") or 0)
                    if time.time() - saved_at < ttl:
                        body = payload.get("body")
                        self._cache[key] = (time.monotonic(), ttl, copy.deepcopy(body))
                        return copy.deepcopy(body)
                except Exception:
                    return None
        return None

    def _cache_set(self, key: tuple, ttl: float, body: Any) -> None:
        if len(self._cache) >= CACHE_MAX:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = (time.monotonic(), ttl, copy.deepcopy(body))
        if self._cache_dir:
            import json
            from pathlib import Path

            path = Path(self._cache_dir) / f"{self._cache_key_str(key)}.json"
            try:
                path.write_text(
                    json.dumps(
                        {"saved_at": time.time(), "ttl": ttl, "body": body},
                        ensure_ascii=False,
                        default=str,
                    ),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """
        درخواست با:
        - فاصله بین درخواست‌ها
        - retry روی timeout / قطع اتصال
        - صبر + تکرار روی HTTP 429 (rate-limit کدال)
        """
        last_err: Exception | None = None
        rate_limit_hits = 0

        for attempt in range(self._max_retries + 1 + MAX_RATE_LIMIT_RETRIES):
            self._wait()
            client = self._get_client()
            try:
                if stream:
                    r = client.stream(method, url, params=params, headers=headers)
                    self._last = time.monotonic()
                    return r  # type: ignore[return-value]
                r = client.request(method, url, params=params, headers=headers)
                self._last = time.monotonic()

                # rate-limit: صبر و تکرار
                if r.status_code == 429:
                    rate_limit_hits += 1
                    self._blocked_until = time.monotonic() + BLOCK_COOLDOWN
                    if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                        raise CodalError(
                            f"کدال پس از {MAX_RATE_LIMIT_RETRIES} بار صبر و تکرار "
                            f"(هر بار حدود {BLOCK_COOLDOWN} ثانیه) هنوز rate-limit می‌کند. "
                            "چند دقیقه بعد دوباره تلاش کنید.",
                            status=429,
                        )
                    # صبر اجباری؛ _wait بعدی هم _blocked_until را رعایت می‌کند
                    time.sleep(BLOCK_COOLDOWN + random.uniform(1.0, 3.0))
                    continue

                return r

            except CodalError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                self._last = time.monotonic()
                last_err = e
                self.close()
                if attempt >= self._max_retries:
                    break
                delay = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                time.sleep(delay + random.uniform(0.1, 0.5))
            except httpx.RequestError as e:
                self._last = time.monotonic()
                last_err = e
                self.close()
                if attempt >= self._max_retries:
                    break
                delay = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                time.sleep(delay)

        raise CodalError(
            f"اتصال به کدال برقرار نشد پس از چند تلاش "
            f"({type(last_err).__name__ if last_err else 'unknown'}). "
            "کمی صبر کنید یا PHARAGHY_CODAL_PROXY را تنظیم کنید."
        ) from last_err

    def fetch_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        ttl: float = 120.0,
    ) -> Any:
        """GET و پارس JSON."""
        query = {k: v for k, v in (params or {}).items() if v is not None}
        key = (url, tuple(sorted(query.items())), False)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        headers = {
            "Referer": f"{WWW}/",
            "Accept": "application/json, text/plain, */*",
            "Origin": WWW,
        }
        r = self._request("GET", url, params=query, headers=headers)

        if r.status_code >= 400:
            raise CodalError(f"کدال خطای HTTP {r.status_code} برگرداند.", status=r.status_code)

        try:
            body = r.json()
        except ValueError as e:
            raise CodalError("پاسخ کدال JSON معتبر نبود.") from e

        self._cache_set(key, ttl, body)
        return body

    def fetch_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        ttl: float = 3600.0,
    ) -> str:
        """GET صفحهٔ HTML."""
        query = {k: v for k, v in (params or {}).items() if v is not None}
        key = (url, tuple(sorted(query.items())), True)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        # captcha ممکن است با 200 برگردد؛ چند بار تکرار می‌کنیم
        for captcha_try in range(MAX_RATE_LIMIT_RETRIES + 1):
            r = self._request("GET", url, params=query, headers=PAGE_HEADERS)
            content = r.content
            if len(content) > MAX_BODY:
                raise CodalError("پاسخ کدال بیش از حد بزرگ بود.")
            if b"Captcha.aspx/GetCaptchaImage" in content:
                self._blocked_until = time.monotonic() + BLOCK_COOLDOWN
                if captcha_try >= MAX_RATE_LIMIT_RETRIES:
                    raise CodalError(
                        f"کدال captcha نشان داد و پس از {MAX_RATE_LIMIT_RETRIES} بار "
                        f"صبر و تکرار برطرف نشد.",
                        status=429,
                    )
                time.sleep(BLOCK_COOLDOWN + random.uniform(1.0, 3.0))
                continue
            if r.status_code >= 400:
                raise CodalError(
                    f"کدال خطای HTTP {r.status_code} برگرداند.", status=r.status_code
                )
            text = content.decode("utf-8", "replace")
            self._cache_set(key, ttl, text)
            return text

        raise CodalError("کدال پاسخ HTML معتبر نداد.", status=429)

    def fetch_bytes(self, url: str) -> bytes:
        """دانلود محتوای باینری/HTML (مثلاً اکسل یا PDF کدال) با retry."""
        headers = {
            **PAGE_HEADERS,
            "Referer": f"{WWW}/",
        }
        r = self._request("GET", url, headers=headers)
        if r.status_code >= 400:
            raise CodalError(f"دانلود ناموفق بود (HTTP {r.status_code}).", r.status_code)
        if len(r.content) > MAX_BODY:
            raise CodalError("فایل دانلود‌شده بیش از حد بزرگ بود.")
        return r.content

    def download(self, url: str, path: str) -> str:
        """دانلود فایل و ذخیره در path."""
        data = self.fetch_bytes(url)
        with open(path, "wb") as f:
            f.write(data)
        return path


# کلاینت پیش‌فرض سراسری (lazy)
_default: CodalClient | None = None


def get_default_client() -> CodalClient:
    global _default
    if _default is None:
        _default = CodalClient()
    return _default


def set_default_client(client: CodalClient | None) -> None:
    global _default
    if _default is not None:
        _default.close()
    _default = client


def configure_client(
    *,
    proxy: str | None = None,
    min_interval: float | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
    cache_dir: str | None = None,
) -> CodalClient:
    """
    کلاینت پیش‌فرض را با تنظیمات جدید جایگزین می‌کند و همان را برمی‌گرداند.

    مثال::

        configure_client(timeout=60, min_interval=2.5, cache_dir=".codal_cache")
    """
    client = CodalClient(
        proxy=proxy,
        min_interval=min_interval,
        timeout=timeout,
        max_retries=max_retries,
        cache_dir=cache_dir,
    )
    set_default_client(client)
    return client
