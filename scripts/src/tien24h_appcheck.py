"""
Tien24h — lấy Firebase AppCheck JWT bằng cách chạy toàn bộ flow trong trình duyệt.

Cách hoạt động:
  1. Playwright mở tien24hpro.com/login (headless)
  2. Điền số điện thoại → click nút "Gửi OTP"
  3. Trang tự xử lý reCAPTCHA + AppCheck + sign — không cần reverse-engineer thêm
  4. Chặn request POST /login/sms để lấy header X-Firebase-AppCheck → lưu file
  5. Trả về kết quả gửi SMS

Cài đặt (một lần):
    pip install playwright
    playwright install chromium
    playwright install-deps chromium

Cách dùng:
    python tien24h_appcheck.py 0945987331          # lấy token + gửi SMS
    python tien24h_appcheck.py 0945987331 --save-only  # chỉ lấy token, không gửi

File JSON đầu ra (tien24h_jwt.json):
    { "token": "<JWT>", "expires_at": 1234567890.0 }

Lên lịch cron refresh token mỗi 50 phút (không cần số điện thoại):
    */50 * * * * python /path/to/tien24h_appcheck.py 0000000000 --save-only
"""

import sys
import json
import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright, Request

SITE        = "https://www.tien24hpro.com"
LOGIN_PAGE  = f"{SITE}/login"
API_BASE    = "https://api.tien-24h.com"
TOKEN_TTL   = 3600
DEFAULT_OUT = Path(__file__).parent / "tien24h_jwt.json"

# Ẩn dấu vết automation
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver',  {get: () => false});
Object.defineProperty(navigator, 'plugins',    {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages',  {get: () => ['vi-VN','vi','en-US','en']});
Object.defineProperty(navigator, 'platform',   {get: () => 'iPhone'});
window.chrome = {runtime: {}};
"""


async def run(phone: str, save_only: bool = False, out_path: Path = DEFAULT_OUT) -> bool:
    """
    Mở trang login, điền phone, click Gửi OTP.
    Chặn request /login/sms để lấy AppCheck token → lưu file.
    Trả về True nếu SMS gửi thành công.
    """
    appcheck_token: list[str] = []
    sms_response:   list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=390,844",
            ],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.1 Mobile/15E148 Safari/604.1"
            ),
            viewport={"width": 390, "height": 844},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )
        await ctx.add_init_script(STEALTH_SCRIPT)
        page = await ctx.new_page()

        # ── Intercept: chặn request ra để lấy AppCheck token ─────────────────
        async def _on_request(req: Request):
            if "/login/sms" in req.url and not appcheck_token:
                hdrs = req.headers
                t = hdrs.get("x-firebase-appcheck", "")
                if t:
                    appcheck_token.append(t)
                    print(f"[AppCheck] token bắt được từ request ✅ ({len(t)} ký tự)")

        # Intercept response để lấy kết quả SMS
        async def _on_response(resp):
            if "/login/sms" in resp.url:
                try:
                    d = await resp.json()
                    sms_response.append(d)
                    print(f"[SMS] response: code={d.get('code')} msg={d.get('message','')!r}")
                except Exception:
                    pass

        page.on("request",  _on_request)
        page.on("response", _on_response)

        # ── Mở trang ─────────────────────────────────────────────────────────
        print(f"[Browser] mở {LOGIN_PAGE} ...")
        try:
            await page.goto(LOGIN_PAGE, wait_until="domcontentloaded", timeout=40_000)
        except Exception as e:
            print(f"[Browser] goto warning: {e}")

        # Chờ JS / Firebase khởi tạo
        await asyncio.sleep(4)

        # ── Điền số điện thoại ───────────────────────────────────────────────
        print(f"[Browser] điền số điện thoại {phone} ...")
        filled = False
        for selector in [
            "input[type='number']",
            "input[type='tel']",
            "input[name='phone']",
            "input[placeholder*='điện thoại']",
            "input[placeholder*='phone']",
            "input",
        ]:
            try:
                el = await page.wait_for_selector(selector, timeout=5_000)
                if el:
                    await el.click()
                    await el.fill(phone.lstrip("0"))  # bỏ số 0 đầu nếu cần
                    await asyncio.sleep(0.5)
                    filled = True
                    print(f"[Browser] đã điền vào selector: {selector}")
                    break
            except Exception:
                continue

        if not filled:
            # Fallback: gõ trực tiếp vào focus
            print("[Browser] không tìm thấy input, thử focus + type...")
            await page.keyboard.press("Tab")
            await page.keyboard.type(phone, delay=80)

        await asyncio.sleep(1)

        # ── Click nút Gửi OTP ────────────────────────────────────────────────
        print("[Browser] tìm nút Gửi OTP ...")
        otp_btn_found = False
        for selector in [
            "button[data-track-af='OTP']",
            "button:has-text('OTP')",
            "button:has-text('Gửi')",
            "button:has-text('Send')",
            "button[type='button']",
        ]:
            try:
                btn = await page.wait_for_selector(selector, timeout=5_000)
                if btn:
                    await btn.click()
                    otp_btn_found = True
                    print(f"[Browser] đã click nút: {selector}")
                    break
            except Exception:
                continue

        if not otp_btn_found:
            # Fallback: gọi API trực tiếp từ trong trình duyệt (Firebase SDK đã init)
            print("[Browser] không tìm được nút, thử gọi fetch trong page...")
            await page.evaluate(f"""
                async () => {{
                    // Lấy sign + token từ interceptor đã init sẵn trong page
                    const axios = window.axios || null;
                    if (!axios) {{
                        // Gọi thẳng fetch — app interceptor sẽ tự thêm AppCheck + sign
                        await fetch('{API_BASE}/api/user/app/login/sms', {{
                            method: 'POST',
                            headers: {{'Content-Type':'application/json','platform':'h5','app-version':'1.0.0','lang':'vi_VN'}},
                            body: JSON.stringify({{appCode:'tien24hh5',version:'1.0.0',mobileType:'1',phone:'{phone}'}})
                        }});
                    }}
                }}
            """)

        # ── Chờ request / response (tối đa 20 giây) ─────────────────────────
        for _ in range(40):
            if appcheck_token and sms_response:
                break
            await asyncio.sleep(0.5)

        await browser.close()

    # ── Lưu token ─────────────────────────────────────────────────────────────
    if appcheck_token:
        payload = {"token": appcheck_token[0], "expires_at": time.time() + TOKEN_TTL}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[AppCheck] token lưu → {out_path}")
        print(f"[AppCheck] hết hạn: {time.strftime('%H:%M:%S', time.localtime(payload['expires_at']))}")
    else:
        print("[AppCheck] ⚠ không bắt được token — trang có thể chưa gửi request")

    # ── Kết quả SMS ───────────────────────────────────────────────────────────
    if sms_response:
        d = sms_response[0]
        ok = d.get("code") == 200
        if ok:
            print(f"✅ Tien24h SMS {phone} thành công")
        else:
            print(f"✘ Tien24h SMS code={d.get('code')} msg={d.get('message','')!r}")
        return ok

    print("✘ Tien24h SMS — không nhận được response")
    return False


async def main():
    args = sys.argv[1:]
    if not args:
        print("Dùng: python tien24h_appcheck.py <số_điện_thoại> [--save-only]")
        sys.exit(1)

    phone     = args[0]
    save_only = "--save-only" in args
    out_path  = DEFAULT_OUT

    # Đọc --out /path/to/file.json nếu có
    if "--out" in args:
        idx = args.index("--out")
        if idx + 1 < len(args):
            out_path = Path(args[idx + 1])

    await run(phone, save_only=save_only, out_path=out_path)


if __name__ == "__main__":
    asyncio.run(main())
