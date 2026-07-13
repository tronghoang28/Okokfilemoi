"""
Lấy Firebase AppCheck JWT cho Tien24h bằng Playwright headless và lưu vào file.

Cài đặt (một lần):
    pip install playwright
    playwright install chromium
    playwright install-deps chromium

Cách dùng:
    python tien24h_appcheck.py                  # lưu vào tien24h_jwt.json (mặc định)
    python tien24h_appcheck.py /tmp/jwt.json    # lưu vào đường dẫn tuỳ chọn

File JSON đầu ra:
    {
        "token":      "<JWT>",
        "expires_at": 1783912345.678   # Unix timestamp — hết hạn sau 3600 giây
    }

Lên lịch cron ví dụ (refresh mỗi 50 phút):
    */50 * * * * /usr/bin/python3 /path/to/tien24h_appcheck.py
"""

import sys
import json
import asyncio
import time
import os
from pathlib import Path

from playwright.async_api import async_playwright

SITE                    = "https://www.tien24hpro.com"
LOGIN_PAGE              = f"{SITE}/login"
APPCHECK_EXCHANGE_PAT   = "exchangeRecaptchaEnterpriseToken"
TOKEN_TTL               = 3600          # Firebase AppCheck token valid 3600 giây
DEFAULT_OUT             = Path(__file__).parent / "tien24h_jwt.json"


async def fetch_appcheck_token() -> str:
    """
    Mở tien24hpro.com/login bằng Playwright headless.
    Intercepte phản hồi Firebase AppCheck (exchangeRecaptchaEnterpriseToken) → lấy JWT.
    """
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
            if APPCHECK_EXCHANGE_PAT in resp.url and not token_holder:
                try:
                    data = await resp.json()
                    t = data.get("token", "")
                    if t:
                        token_holder.append(t)
                except Exception:
                    pass

        page.on("response", _on_response)

        try:
            await page.goto(LOGIN_PAGE, wait_until="domcontentloaded", timeout=35_000)
        except Exception:
            pass

        # Chờ tối đa 25 giây để Firebase AppCheck khởi tạo và trao đổi token
        for _ in range(50):
            if token_holder:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    if not token_holder:
        raise RuntimeError(
            "Không lấy được Firebase AppCheck token.\n"
            "Kiểm tra: playwright install chromium && playwright install-deps chromium"
        )

    return token_holder[0]


def save_token(token: str, out_path: Path) -> None:
    payload = {
        "token":      token,
        "expires_at": time.time() + TOKEN_TTL,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[AppCheck] token lưu → {out_path}")
    print(f"[AppCheck] hết hạn lúc: {time.strftime('%H:%M:%S', time.localtime(payload['expires_at']))}")
    print(f"[AppCheck] token (40 ký tự đầu): {token[:40]}...")


async def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT

    print("[AppCheck] đang mở trình duyệt headless...")
    token = await fetch_appcheck_token()
    save_token(token, out_path)
    print("[AppCheck] hoàn tất ✅")


if __name__ == "__main__":
    asyncio.run(main())
