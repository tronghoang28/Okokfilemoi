"""
Script tự động lấy token và gửi flashcall - chạy headless trên VPS không có GUI.

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

        captured = {}

        async def on_request(request):
            if FLASHCALL_API in request.url:
                print("[*] Bắt được request flashcall!")
                captured["headers"] = dict(request.headers)

        async def on_response(response):
            if FLASHCALL_API in response.url:
                try:
                    body = await response.json()
                    captured["response"] = body
                    captured["status"] = response.status
                except Exception:
                    captured["response_text"] = await response.text()
                    captured["status"] = response.status

        context.on("request", on_request)
        context.on("response", on_response)

        page = await context.new_page()

        # Ẩn dấu hiệu automation
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        print("[*] Mở trang đăng ký...")
        await page.goto(REGISTER_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Thử cách 1: gọi API qua browser context (dùng cookies + captcha từ trang)
        print("[*] Gọi API qua browser context (dùng token của trang)...")
        result = await page.evaluate(f"""
            async () => {{
                try {{
                    const resp = await fetch('/web-api/api/web/registration/v2/flashcall', {{
                        method: 'POST',
                        headers: {{
                            'content-type': 'application/vnd.api+json',
                            'accept': 'application/vnd.api+json',
                            'x-requested-with': 'XMLHttpRequest',
                            'is-srv': 'false',
                            'x-svc-source': '__WELCOME_APP__',
                            'x-app-n': '__WELCOME_APP__',
                        }},
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
                    return {{ status: resp.status, body }};
                }} catch(e) {{
                    return {{ error: e.toString() }};
                }}
            }}
        """)

        status = result.get("status")
        body = result.get("body")

        print(f"\n[*] HTTP Status: {status}")

        if status == 200:
            print("[+] Thành công!")
            print(json.dumps(body, ensure_ascii=False, indent=2))
        elif status == 400:
            print("[-] Lỗi 400 - Token captcha chưa được tải hoặc đã hết hạn.")
            print("[*] Thử chờ trang tải xong captcha rồi thử lại...")
            print(json.dumps(body, ensure_ascii=False, indent=2))

            # Thử cách 2: Đợi captcha load rồi thử lại
            await page.wait_for_timeout(5000)
            result2 = await page.evaluate(f"""
                async () => {{
                    try {{
                        // Lấy captcha session từ sessionStorage
                        const captchaSession = sessionStorage.getItem('x-hunt-captcha-session');
                        // Lấy fingerprint từ localStorage
                        const fpData = localStorage.getItem('fp_d');
                        let xhd = '';
                        if (fpData) {{
                            try {{ xhd = JSON.parse(fpData).token || ''; }} catch(e) {{}}
                        }}

                        const headers = {{
                            'content-type': 'application/vnd.api+json',
                            'accept': 'application/vnd.api+json',
                            'x-requested-with': 'XMLHttpRequest',
                            'is-srv': 'false',
                            'x-svc-source': '__WELCOME_APP__',
                            'x-app-n': '__WELCOME_APP__',
                        }};
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

                        // Trả về cả headers đã dùng để debug
                        return {{ status: resp.status, body, used_xhd: !!xhd, used_captcha: !!captchaSession }};
                    }} catch(e) {{
                        return {{ error: e.toString() }};
                    }}
                }}
            """)
            print(f"\n[*] Lần 2 - HTTP Status: {result2.get('status')}")
            print(f"    Có x-hd: {result2.get('used_xhd')} | Có captcha session: {result2.get('used_captcha')}")
            print(json.dumps(result2.get("body"), ensure_ascii=False, indent=2))

        elif status == 429:
            reset = body.get("data", {}).get("attributes", {}).get("retry_after", 120) if isinstance(body, dict) else 120
            print(f"[-] Rate limit! Chờ {reset} giây rồi chạy lại script.")
        else:
            print(json.dumps(body, ensure_ascii=False, indent=2))

        # Lưu screenshot để debug nếu cần
        await page.screenshot(path="/tmp/debug.png")
        print("\n[*] Screenshot debug lưu tại: /tmp/debug.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
