import os
import re
import random
import sys
import requests
import time
import uuid
import base64
import hashlib
import json
import base64
import io
from typing import Optional, Any
from urllib.parse import urlparse
from Crypto.Cipher import AES, PKCS1_v1_5 as RSA_PKCS1
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad
from PIL import ImageFile, Image, ImageEnhance
import ddddocr

ImageFile.LOAD_TRUNCATED_IMAGES = True
_ocr = ddddocr.DdddOcr(show_ad=False)

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
    return next((item for item in candidates if len(item) >= 4), max(candidates, key=len, default=""))


def register_test(data, code, url="https://api.78wwing.com/vi5prod-ecp/api/v1/register"):

    if phone.startswith("0"):
        phone = "84 " + phone[1:]    

    headers = {
        "Host": "api.78wwing.com",
        "Accept": "application/json",
        "Origin": "https://www.78wwing.com/",
        "Referer": "https://www.78wwing.com/",
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    with requests.Session() as session:
        response = session.post(
            url,
            headers=headers,
            files={
                key: (None, str(value))
                for key, value in data.items()
            },
            timeout=20,
        )
        response.raise_for_status()
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {
                "status_code": response.status_code,
                "body": response.text[:500],
            }
if __name__ == "__main__":
    payload = {
        "playerid": "ksjdjjdjdjd",
        "password": "7d96561b01245303c0db7b22b29df4486f260711",
        "currency": "VND2",
        "firstname": "HOANG TRONG",
        "captcha": code,
        "mobile": phone,
        "portalid": "EC_MOBILE",
        "captchauuid": "39989b0a-404e-4767-8112-764ed65323a7",
        "c-njo6ru": "XPAqHZpAxVRr14qcw-UzSTeSyKl4oYna4GLXQU-WegnbefN5N9lF2ixS-0dvK58iekXhBeX-fTiD8Cqzc_4I5zQLGUdQiGQT0x_o0dYpwqqLl6k2szEVDsLW3vdXhtAqfSt_q3htgxQivmU6d5iC00Nhg-d9KxKx",
        "ulagentaccount": "chuyendoi40w8",
        "regfingerprint": "38696e2eba7a407bea916d9399025107",
        "pixelInfo": "pix=D6OKLG3C77UET383S48G&pixelFromCookie=false&ttclid=E_C_P_CsMBov89lyPr9lckw6gxoiWbQPBpExDpD_2fDGLDppDRfIPYWHODFcMJpyVCf6GIKVGrJW301eZ4kz88ZHp7q4WpgzHQ-gg4skRTOvKU4Sp25QEJfxUq_vvzi99dkL1vY17hkriwQN2wlXxZ4vMxt6w70k1hE84otdxRpD_Jmp5NgDKnxbFb9WWUH9EYKEi31yO9EjkflqwOwQAaARwDiquBl-H0nhW_2tN-Zm_C7uYe82m-sd_gDyC8pckcIBvpdIt6MLb-EgR2Mi4w&ttp=01M558MP9QQGZWNE2CTKENR242_.tt.1.1792251943224&uagt=chuyendoi40w8&utm_campaign=46306-ON%20KUME-7W-TIKTOK-%E1%BA%A2nh%20%2F%20Motion-chuyendoi40w8-New&utm_id=1878770538562593&utm_medium=paid&utm_source=tiktok",
        "language": "4",
    }
    print(register_test(payload))

code = _solve_captcha(image)