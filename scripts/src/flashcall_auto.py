"""
Script tự động gửi flashcall - chạy headless trên VPS không có GUI.

Cài đặt trên VPS (Ubuntu/Debian):
    pip install playwright
    playwright install chromium
    playwright install-deps chromium

Cách dùng:
    python flashcall_auto.py 945987331
    python flashcall_auto.py 945987331 84
"""

import sys
import json
import asyncio
from playwright.async_api import async_playwright

REGISTER_URL = "https://1xlite-859253.top/vi/registration?type=phone&bonus=SPORT_SINGLE&currency=VND"
FLASHCALL_API = "/web-api/api/web/registration/v2/flashcall"

PHONE = sys.argv[1] if len(sys.argv) > 1 else "945987331"
COUNTRY_CODE = sys.argv[2] if len(sys.argv) > 2 else "84"


async def call_api(page, extra_headers=None):
    """Gọi flashcall API từ bên trong browser context."""
    headers_js = json.dumps({
        "content-type": "application/vnd.api+json",
        "accept": "application/vnd.api+json",
        "x-requested-with": "XMLHttpRequest",
        "is-srv": "false",
        "x-svc-source": "__WELCOME_APP__",
        "x-app-n": "__WELCOME_APP__",
        **(extra_headers or {}),
    })

    result = await page.evaluate(f"""
        async () => {{
            try {{
                // Lấy fingerprint từ localStorage (fp_d.token = x-hd)
                let xhd = '';
                const fpData = localStorage.getItem('fp_d');
                if (fpData) {{
                    try {{ xhd = JSON.parse(fpData).token || ''; }} catch(e) {{}}
                }}

                // Lấy captcha session từ sessionStorage
                let captchaSession = sessionStorage.getItem('x-hunt-captcha-session') || '';

                const headers = {{...{headers_js}}};
                if (xhd) headers['x-hd'] = xhd;
                if (captchaSession) headers['x-hunt-captcha-session'] = captchaSession;

                const resp = await fetch('/web-api/api/web/registration/v2/flashcall', {{
                    method: 'POST',
                    headers,
                    body: JSON.stringify({{
                        data: {{
                            attributes: {{
                                phone: '{PHONE}',
                                country_code: '{COUNTRY_CODE}'
                            }}
                        }}
                    }})
                }});

                const text = await resp.text();
                let body;
                try {{ body = JSON.parse(text); }} catch(e) {{ body = text; }}

                return {{
                    status: resp.status,
                    body,
                    has_xhd: !!xhd,
                    has_captcha_session: !!captchaSession,
                }};
            }} catch(e) {{
                return {{ error: e.toString() }};
            }}
        }}
    """)
    return result


async def run():
    print(f"[*] Bắt đầu cho số: +{COUNTRY_CODE}{PHONE}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/112.0.0.0 Mobile Safari/537.36"
            ),
            viewport={"width": 390, "height": 844},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )

        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        print("[*] Mở trang đăng ký, chờ tải xong...")
        await page.goto(REGISTER_URL, wait_until="networkidle", timeout=30000)
        # Đợi thêm để FingerprintJS và captcha khởi tạo xong
        await page.wait_for_timeout(4000)

        # ---- Lần 1: Gửi không có captcha token để lấy challenge ----
        print("[*] Lần 1: Gửi request để lấy captcha challenge...")
        r1 = await call_api(page)
        status1 = r1.get("status")
        body1 = r1.get("body", {})

        print(f"    Status: {status1} | x-hd: {r1.get('has_xhd')} | captcha-session: {r1.get('has_captcha_session')}")

        if status1 == 200:
            print("[+] Thành công ngay lần đầu!")
            print(json.dumps(body1, ensure_ascii=False, indent=2))
            await browser.close()
            return

        # Lấy meta.token từ response lỗi (captcha challenge)
        meta_token = None
        if isinstance(body1, dict):
            meta_token = body1.get("meta", {}).get("token")

        if meta_token:
            print(f"[*] Lấy được captcha challenge token từ server.")
        else:
            print("[!] Không có meta.token trong response.")
            print(json.dumps(body1, ensure_ascii=False, indent=2))

        # ---- Lần 2: Gửi lại với meta.token làm x-captcha-token ----
        if meta_token:
            print("[*] Lần 2: Gửi lại với captcha challenge token...")
            await page.wait_for_timeout(1000)
            r2 = await call_api(page, extra_headers={"x-captcha-token": meta_token})
            status2 = r2.get("status")
            body2 = r2.get("body", {})

            print(f"    Status: {status2} | x-hd: {r2.get('has_xhd')} | captcha-session: {r2.get('has_captcha_session')}")
            print(json.dumps(body2, ensure_ascii=False, indent=2))

            if status2 == 200:
                print("\n[+] Thành công!")
            elif status2 == 400:
                errors = body2.get("errors", []) if isinstance(body2, dict) else []
                code = errors[0].get("code") if errors else "?"
                detail = errors[0].get("detail") if errors else ""

                # Nếu lại có meta.token mới thì thử lần 3
                meta_token2 = body2.get("meta", {}).get("token") if isinstance(body2, dict) else None
                if meta_token2 and meta_token2 != meta_token:
                    print(f"[*] Lần 3: Server gửi token mới (code={code}), thử lại...")
                    await page.wait_for_timeout(1000)
                    r3 = await call_api(page, extra_headers={"x-captcha-token": meta_token2})
                    print(f"    Status: {r3.get('status')}")
                    print(json.dumps(r3.get("body"), ensure_ascii=False, indent=2))
                else:
                    print(f"\n[!] Vẫn lỗi 400 (code={code}): {detail}")
                    print("    Server yêu cầu giải captcha thật (image/text captcha).")
                    print("    Không thể bypass tự động.")
            elif status2 == 429:
                print("[!] Rate limit! Chờ 120 giây rồi chạy lại.")

        await page.screenshot(path="/tmp/debug.png")
        print("\n[*] Screenshot debug: /tmp/debug.png")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
