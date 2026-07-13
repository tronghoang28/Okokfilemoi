"""
Tien24h OTP — gửi SMS OTP không cần GUI.

Yêu cầu: chạy tien24h_appcheck.py trước để có tien24h_jwt.json, hoặc đặt lịch
cron refresh token mỗi 50 phút.

Cách dùng:
    python tien24h.py 0945987331

Sign formula (reverse-engineer từ store-Dy6IrkuN.js — xác nhận 100%):
    app_md5 = MD5("tien24hh5")
    raw     = f"{app_md5}*|*{secret}*|*{JSON(sorted_body)}*|*{timestamp_ms}"
    sign    = MD5(raw).lower()
"""

import sys
import asyncio
import hashlib
import json
import time
from pathlib import Path

import httpx

# ─── Config ───────────────────────────────────────────────────────────────────
BASE       = "https://api.tien-24h.com"
APPCODE    = "tien24hh5"
VERSION    = "1.0.0"
MOBILE_T   = "1"
APP_MD5    = hashlib.md5(APPCODE.encode()).hexdigest()   # ae55ea0fc3a84eb85ce6b30c6945cad1

JWT_FILE   = Path(__file__).parent / "tien24h_jwt.json"

# Runtime cache secret (5 phút)
_secret_cache: tuple[str, float] | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def _make_sign(body: dict, secret: str, ts: str) -> str:
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


# ─── AppCheck token — đọc từ file ─────────────────────────────────────────────
def _load_appcheck_token(jwt_file: Path = JWT_FILE) -> str:
    """
    Đọc Firebase AppCheck JWT từ tien24h_jwt.json (do tien24h_appcheck.py tạo ra).
    Báo lỗi rõ ràng nếu file chưa tồn tại hoặc token đã hết hạn.
    """
    if not jwt_file.exists():
        raise FileNotFoundError(
            f"Chưa có file token: {jwt_file}\n"
            "Chạy trước: python tien24h_appcheck.py"
        )
    data = json.loads(jwt_file.read_text(encoding="utf-8"))
    token      = data.get("token", "")
    expires_at = data.get("expires_at", 0.0)

    if not token:
        raise ValueError(f"File {jwt_file} không chứa token hợp lệ.")

    remaining = expires_at - time.time()
    if remaining <= 0:
        raise RuntimeError(
            f"Firebase AppCheck token đã hết hạn ({jwt_file}).\n"
            "Chạy lại: python tien24h_appcheck.py"
        )

    print(f" [AppCheck] token còn hiệu lực {int(remaining // 60)} phút {int(remaining % 60)} giây")
    return token


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


# ─── SMS OTP ──────────────────────────────────────────────────────────────────
async def send_sms(phone: str, jwt_file: Path = JWT_FILE) -> bool:
    secret = await _get_secret()
    token  = _load_appcheck_token(jwt_file)

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
        print(f" ✅ Tien24h SMS {phone}  {d.get('message', '')}")
    else:
        print(f" ✘ Tien24h SMS code={d.get('code')} msg={d.get('message', '')!r}")
    return ok


# ─── Standalone CLI ───────────────────────────────────────────────────────────
async def _main():
    phone = sys.argv[1] if len(sys.argv) > 1 else input("Nhập số điện thoại: ").strip()
    await send_sms(phone)


if __name__ == "__main__":
    asyncio.run(_main())
