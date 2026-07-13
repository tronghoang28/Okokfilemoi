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
        "expires_at": 1783912345.678
    }

Lên lịch cron (refresh mỗi 50 phút):
    */50 * * * * /usr/bin/python3 /path/to/tien24h_appcheck.py
"""

import sys
import json
import asyncio
import time
from pathlib import Path

from playwright.async_api import async_playwright, Route, Request

SITE                  = "https://www.tien24hpro.com"
LOGIN_PAGE            = f"{SITE}/login"
APPCHECK_EXCHANGE_PAT = "exchangeRecaptchaEnterpriseToken"
TOKEN_TTL             = 3600
DEFAULT_OUT           = Path(__file__).parent / "tien24h_jwt.json"

# Ẩn dấu vết headless — patch navigator.webdriver + plugins + languages
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => false});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['vi-VN', 'vi', 'en-US', 'en']});
window.chrome = {runtime: {}};
Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
"""


async def fetch_appcheck_token() -> str:
    """
    Mở tien24hpro.com/login với stealth headless.
    Intercept phản hồi exchangeRecaptchaEnterpriseToken → lấy JWT.
    Fallback: gọi trực tiếp firebase.appCheck().getToken() qua JS.
    """
    token_holder: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-extensions",
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
            color_scheme="light",
            java_script_enabled=True,
        )

        # Patch navigator trước khi bất kỳ script nào chạy
        await ctx.add_init_script(STEALTH_SCRIPT)

        page = await ctx.new_page()

        # ── Intercept response để bắt token ─────────────────────────────────
        async def _on_response(resp):
            if APPCHECK_EXCHANGE_PAT in resp.url and not token_holder:
                try:
                    data = await resp.json()
                    t = data.get("token", "")
                    if t:
                        token_holder.append(t)
                        print(f"[AppCheck] token intercepted từ network ✅")
                except Exception:
                    pass

        page.on("response", _on_response)

        # ── Mở trang ────────────────────────────────────────────────────────
        print("[AppCheck] đang mở trang login...")
        try:
            await page.goto(LOGIN_PAGE, wait_until="domcontentloaded", timeout=40_000)
        except Exception as e:
            print(f"[AppCheck] goto warning (tiếp tục): {e}")

        # Chờ page JS load xong
        await asyncio.sleep(3)

        # ── Simulate tương tác người dùng để trigger reCAPTCHA ───────────────
        try:
            # Di chuyển chuột ngẫu nhiên
            await page.mouse.move(150, 300)
            await asyncio.sleep(0.3)
            await page.mouse.move(200, 400)
            await asyncio.sleep(0.3)
            # Click vào input số điện thoại nếu có
            phone_input = await page.query_selector("input[type='number'], input[type='tel'], input[name='phone']")
            if phone_input:
                await phone_input.click()
                await asyncio.sleep(0.5)
                await phone_input.type("09", delay=100)
                await asyncio.sleep(0.5)
        except Exception:
            pass

        # ── Chờ network intercept, tối đa 35 giây ───────────────────────────
        for i in range(70):
            if token_holder:
                break
            if i == 20:
                # Sau 10 giây vẫn chưa có → thử scroll để trigger lazy-init
                try:
                    await page.evaluate("window.scrollTo(0, 100)")
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        # ── Fallback: gọi Firebase AppCheck SDK trực tiếp qua JS ─────────────
        if not token_holder:
            print("[AppCheck] network intercept thất bại, thử JS fallback...")
            try:
                js_token = await page.evaluate("""
                    async () => {
                        // Thử lấy token từ Firebase AppCheck SDK
                        try {
                            const apps = window._delegate?._apps || window.firebase?.apps || [];
                            if (apps && apps.size > 0) {
                                const app = [...apps.values()][0];
                                const { getToken } = await import('firebase/app-check');
                                const { getApp } = await import('firebase/app');
                                // fallback: không import được → skip
                            }
                        } catch(e) {}

                        // Thử tìm token trong localStorage / sessionStorage / indexedDB
                        for (const key of Object.keys(localStorage)) {
                            try {
                                const v = JSON.parse(localStorage.getItem(key) || '');
                                if (v && v.token && typeof v.token === 'string' && v.token.length > 100) {
                                    return v.token;
                                }
                            } catch(e) {}
                        }
                        return null;
                    }
                """)
                if js_token:
                    token_holder.append(js_token)
                    print("[AppCheck] token lấy từ localStorage fallback ✅")
            except Exception as e:
                print(f"[AppCheck] JS fallback lỗi: {e}")

        # ── Fallback 2: tìm token trong IndexedDB (firebase-app-check-database) ─
        if not token_holder:
            print("[AppCheck] thử đọc IndexedDB...")
            try:
                idb_token = await page.evaluate("""
                    async () => {
                        return new Promise((resolve) => {
                            try {
                                const req = indexedDB.open('firebase-app-check-database', 1);
                                req.onsuccess = (e) => {
                                    const db = e.target.result;
                                    const stores = Array.from(db.objectStoreNames);
                                    if (!stores.length) { resolve(null); return; }
                                    const tx = db.transaction(stores[0], 'readonly');
                                    const store = tx.objectStore(stores[0]);
                                    const all = store.getAll();
                                    all.onsuccess = (ev) => {
                                        const results = ev.target.result;
                                        for (const item of results || []) {
                                            const v = item?.value;
                                            if (v?.token && typeof v.token === 'string' && v.token.length > 100) {
                                                resolve(v.token);
                                                return;
                                            }
                                        }
                                        resolve(null);
                                    };
                                };
                                req.onerror = () => resolve(null);
                            } catch(e) { resolve(null); }
                        });
                    }
                """)
                if idb_token:
                    token_holder.append(idb_token)
                    print("[AppCheck] token lấy từ IndexedDB ✅")
            except Exception as e:
                print(f"[AppCheck] IndexedDB lỗi: {e}")

        await browser.close()

    if not token_holder:
        raise RuntimeError(
            "\n[AppCheck] Không lấy được Firebase AppCheck token.\n"
            "Nguyên nhân thường gặp:\n"
            "  1. reCAPTCHA Enterprise chặn headless browser (bot detection)\n"
            "  2. Playwright chưa cài chromium: playwright install chromium\n"
            "  3. Thiếu deps trên Linux: playwright install-deps chromium\n"
            "Thử chạy với PWDEBUG=1 để xem browser:\n"
            "  PWDEBUG=1 python tien24h_appcheck.py"
        )

    return token_holder[0]


def save_token(token: str, out_path: Path) -> None:
    payload = {
        "token":      token,
        "expires_at": time.time() + TOKEN_TTL,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[AppCheck] lưu → {out_path}")
    print(f"[AppCheck] hết hạn: {time.strftime('%H:%M:%S', time.localtime(payload['expires_at']))}")
    print(f"[AppCheck] token đầu: {token[:50]}...")


async def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    print("[AppCheck] bắt đầu lấy token...")
    token = await fetch_appcheck_token()
    save_token(token, out_path)
    print("[AppCheck] hoàn tất ✅")


if __name__ == "__main__":
    asyncio.run(main())
