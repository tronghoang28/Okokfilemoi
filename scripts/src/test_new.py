"""
Test 2 hàm mới trước khi thêm vào main.py:
  - call_vvay_h5  : V-Vay h5api (h5=True)
  - tien24h_sms   : Tien24h SMS OTP

Cách dùng:
    python test_new.py 0945987331
"""

import sys
import asyncio
import uuid
import base64
import json

from curl_cffi.requests import AsyncSession as BrowserSession
from tien24h import send_sms as tien24h_sms

# ─── V-Vay helpers (copy từ main.py) ──────────────────────────────────────────
from Crypto.Cipher import AES as _AES
from Crypto.Util.Padding import pad as _pad, unpad as _unpad

_VVAY_KEY = b"aajiaozicashmeh5"
_VVAY_IV  = b"hajiaozicashmeh5"
_VVAY_URL = "https://h5api.v-vay.com/h5/adrs7vc167lsu00n79ms98o0r4t1bqm5"
_BROWSER  = "chrome120"


def _vvay_encrypt(data) -> str:
    if isinstance(data, dict):
        data = json.dumps(data, separators=(',', ':'))
    ct = _AES.new(_VVAY_KEY, _AES.MODE_CBC, _VVAY_IV).encrypt(_pad(data.encode(), 16))
    return base64.b64encode(ct).decode()


def _vvay_decrypt(b64_str: str) -> dict:
    ct = base64.b64decode(b64_str)
    plain = _unpad(_AES.new(_VVAY_KEY, _AES.MODE_CBC, _VVAY_IV).decrypt(ct), 16)
    return json.loads(plain.decode('utf-8').strip())


_VVAY_XPATH = _vvay_encrypt("/login/requestVerifyCode")


def _vvay_headers(device_id: str) -> dict:
    return {
        "Host":             "h5api.v-vay.com",
        "fpPlatform":       "5",
        "appId":            "4",
        "language":         "vi-VN",
        "User-Agent":       "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer":          "https://h5api.v-vay.com/login",
        "country":          "VN",
        "Origin":           "https://h5api.v-vay.com",
        "Sec-Fetch-Dest":   "empty",
        "fpDeviceId":       str(uuid.uuid4()),
        "version":          "1.0.0_4.0.6",
        "Sec-Fetch-Site":   "same-origin",
        "fingerPrint":      "",
        "Content-Type":     "text/plain",
        "platform":         "2",
        "token":            "",
        "x_x_path":         _VVAY_XPATH,
        "loginPlatform":    "H5",
        "marketToken":      "",
        "Accept":           "application/json",
        "Sec-Fetch-Mode":   "cors",
        "Accept-Language":  "vi-VN,vi;q=0.9",
        "deviceId":         device_id,
    }


# ─── Hàm mới 1: V-Vay h5=True ─────────────────────────────────────────────────
async def call_vvay_h5(phone: str):
    """V-Vay — SMS OTP với h5=True."""
    device_id = uuid.uuid4().hex
    body = _vvay_encrypt({"phone": phone, "isVoice": False, "h5": True, "deviceId": device_id})
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post(_VVAY_URL, data=body, headers=_vvay_headers(device_id))
        resp = _vvay_decrypt(r.text)
        print(f"call_vvay_h5 raw: {resp}")
        if resp.get("successful"):
            print(f"✅ call_vvay_h5 | {phone} | OK")
        else:
            print(f"✘ call_vvay_h5 | {phone} | {resp}")
    except Exception as e:
        print(f"✘ call_vvay_h5 exception: {e}")


# ─── Main test ────────────────────────────────────────────────────────────────
async def main():
    phone = sys.argv[1] if len(sys.argv) > 1 else input("Số điện thoại: ").strip()

    print(f"\n=== test call_vvay_h5({phone}) ===")
    await call_vvay_h5(phone)

    print(f"\n=== test tien24h_sms({phone}) ===")
    await tien24h_sms(phone)


if __name__ == "__main__":
    asyncio.run(main())
