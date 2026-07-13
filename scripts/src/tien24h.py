"""
Tien24h OTP script — dùng Playwright để lấy Firebase AppCheck token.

Cài đặt trên VPS:
    pip install playwright httpx
    playwright install chromium
    playwright install-deps chromium

Cách dùng:
    python tien24h.py 0945987331
    python tien24h.py 0945987331 voice   # gọi thoại (cần đăng nhập trước)

Cơ chế:
  1. GET  /api/user/app/common/secret  → verifySignSecret
  2. Playwright mở tien24hpro.com/login → intercepte Firebase AppCheck JWT (TTL 1h, cache 55 phút)
  3. POST /api/user/app/login/sms với sign + timestamp + X-Firebase-AppCheck

Sign formula (đã reverse-engineer từ store-Dy6IrkuN.js):
    app_md5 = MD5("tien24hh5")
    raw     = f"{app_md5}*|*{secret}*|*{JSON.stringify(sorted_body)}*|*{timestamp_ms}"
    sign    = MD5(raw).lower()
"""

import sys
import asyncio
import hashlib
import json
import time
from typing import Optional

import httpx
from playwright.async_api import async_playwright

# ─── Config ───────────────────────────────────────────────────────────────────
BASE       = "https://api.tien-24h.com"
SITE       = "https://www.tien24hpro.com"
APPCODE    = "tien24hh5"
VERSION    = "1.0.0"
MOBILE_T   = "1"
APP_MD5    = hashlib.md5(APPCODE.encode()).hexdigest()   # ae55ea0fc3a84eb85ce6b30c6945cad1

# Firebase AppCheck
APPCHECK_EXCHANGE_PATTERN = "exchangeRecaptchaEnterpriseToken"
LOGIN_PAGE = f"{SITE}/login"

# Token cache: (token_str, expires_at_unix)
_appcheck_cache: Optional[tuple[str, float]] = None
_secret_cache:   Optional[tuple[str, float]] = None   # cache 5 phút


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def _make_sign(body: dict, secret: str, ts: str) -> str:
    """
    sign = MD5( MD5(appCode) *|* secret *|* JSON(sorted_body) *|* timestamp )
    Đã xác nhận 100% qua sniffed requests:
      index: 25bff74f1a0a043ce9dddc88ef1dae30 ✅
      sms:   9eced772c2ebbea93c0737a864327794 ✅
    """
    sorted_body = json.dumps(
        dict(sorted(body.items())), separators=(",", ":"), ensure_ascii=False
    )
    raw = f"{APP_MD5}*|*{secret}*|*{sorted_body}*|*{ts}"
    return _md5(raw).lower()


def _base_headers() -> dict:
    return {
        "Accept":       "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "platform":     "h5",
        "app-version":  VERSION,
        "lang":         "vi_VN",
    }


# ─── Secret ───────────────────────────────────────────────────────────────────
async def _get_secret() -> str:
    global _secret_cache
    now = time.time()
    if _secret_cache and now < _secret_cache[1]:
        return _secret_cache[0]
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(
            f"{BASE}/api/user/app/common/secret",
            params={"appCode": APPCODE, "version": VERSION, "mobileType": MOBILE_T},
            headers=_base_headers(),
        )
        secret = r.json()["data"]["verifySignSecret"]
    _secret_cache = (secret, now + 300)
    return secret


# ─── Firebase AppCheck token (Playwright) ─────────────────────────────────────
async def _get_appcheck_token() -> str:
    """
    Mở tien24hpro.com/login bằng Playwright headless, intercepte phản hồi từ
    Firebase AppCheck (exchangeRecaptchaEnterpriseToken) để lấy JWT token.
    Token valid 3600 giây; cache lại 55 phút.
    """
    global _appcheck_cache
    now = time.time()
    if _appcheck_cache and now < _appcheck_cache[1]:
        print(" [AppCheck] dùng token cache")
        return _appcheck_cache[0]

    print(" [AppCheck] đang lấy token qua Playwright...")
    token_holder: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.1 Mobile/15E148 Safari/604.1"
            ),
            viewport={"width": 390, "height": 844},
            locale="vi-VN",
        )
        page = await ctx.new_page()

        async def _on_response(resp):
            if APPCHECK_EXCHANGE_PATTERN in resp.url and not token_holder:
                try:
                    body = await resp.json()
                    t = body.get("token", "")
                    if t:
                        token_holder.append(t)
                except Exception:
                    pass

        page.on("response", _on_response)

        try:
            await page.goto(LOGIN_PAGE, wait_until="domcontentloaded", timeout=35_000)
        except Exception:
            pass

        # Chờ tối đa 25 giây để AppCheck khởi tạo + trao đổi token
        for _ in range(50):
            if token_holder:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    if not token_holder:
        raise RuntimeError(
            "Không lấy được Firebase AppCheck token — "
            "kiểm tra playwright install chromium + playwright install-deps chromium"
        )

    token = token_holder[0]
    _appcheck_cache = (token, now + 3300)   # cache 55 phút
    print(f" [AppCheck] token lấy thành công (cache 55 phút): {token[:40]}...")
    return token


# ─── SMS OTP ──────────────────────────────────────────────────────────────────
async def send_sms(phone: str) -> bool:
    secret = await _get_secret()
    token  = await _get_appcheck_token()

    body = {
        "appCode":    APPCODE,
        "version":    VERSION,
        "mobileType": MOBILE_T,
        "phone":      phone,
    }
    ts   = str(int(time.time() * 1000))
    sign = _make_sign(body, secret, ts)

    hdrs = {
        **_base_headers(),
        "X-Firebase-AppCheck": token,
        "sign":      sign,
        "timestamp": ts,
    }

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{BASE}/api/user/app/login/sms", headers=hdrs, json=body)
        d = r.json()

    ok = d.get("code") == 200
    if ok:
        print(f" ✅ Tien24h SMS {phone}  {d.get('message','')}")
    else:
        print(f" ✘ Tien24h SMS code={d.get('code')} msg={d.get('message','')!r}")
    return ok


# ─── Standalone CLI ───────────────────────────────────────────────────────────
async def _main():
    phone = sys.argv[1] if len(sys.argv) > 1 else input("Nhập số điện thoại: ").strip()
    await send_sms(phone)


if __name__ == "__main__":
    asyncio.run(_main())
