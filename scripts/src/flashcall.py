import requests
import json

url = "https://1xlite-859253.top/web-api/api/web/registration/v2/flashcall"

# ---- Cập nhật các giá trị này mỗi lần dùng ----
X_HD = "Sw6mCZmXpmhl1nOXG4KLR9NIbtqqcAbMJIo7yUmO4dTQeU5SxRY4lLyqU3qM147mTonSI8DVG3X1mrVYCLqQNyfPLxUHGlljut21iFVEj+u//M5vpaERNTNS/Cr/Dh8X9admbWrX82+iq4+kZNuLkxEVrRBTROUdV87moLVe5zQEGQO3zbhoNFijyGjYEmMsFAL4mzfwCPatZUoiaPbgJv7+QC1umXF1U1ux1ylYlkSBWM1WoW/6NhqBGoNChvjvdC3cMKEFv8fG0Zvz6n8mAkN4jGJ9sYIEnNh9Q9+97O9C2KG36e0ANkJbZY+OKVjOkpBloXIWwsk548eSUuJAvM0qnUoHipmPQ8SCRQcQBogaw5UeBr5aGwNmMv5Bz6cewwGwFHMC9HzfH3YAzUwiY+BXXDGUshg2igYFaXocGH7GthaCkNOo9mpaOwrXvISHMvq5FPue0/bc6l8ag7vc4et9CTFNhwldlMhKejKziLZLyxz/sAh5NDdPLg6k0Lm0jx7dWBnpT/6UM7kEBYRuGc+5Nc4iceOAi7SgTfS6F/3PKhsTf83aypVPRdVb5B3qebK+CsDJvpm/KFuTlZnZSHvt4jkkrj1W5RZpYIcfZQL2UKx17pfbuMabukE75RL53IH/fkBDOiZmFFiNtFYi/ZG391EFNsg="

X_CAPTCHA_TOKEN = "s1LQ/7DQkUIoFqMINdlZwXe1cigWTVSdlIkmsV0NFmSXOd7B8hq9Crg6ILHKrrTqLpThElGMym+BPfXDXR497D4dvznx1PkJsKZGuag+sMndWFCjv7hHvL0/eS/Z6dOTJFW+oBprNSDlrz5laZUkYlaAZRSxqCn/TiMPEurqUgIG+cRXMoDNxCvyllGNPpfEiThBTZmsYimzzAemCUwYp/Gl45mde0PNIa0mPq4hOHnjl2QUoLA/6UbXH05ovG/gWo5e9pI/+YJ3gzlgKvuNDBqlWfZsAT618263txs84ONf3tz2MBC61mCiAKDPVSQmIULv1KrsDDmhPaOscyqtwr2178fmbw9t9QC2QH60+y4EtuQPzbEnyx/UNWdRtUGAVPfUQyE5V326fJ3MGVP98mpLHsvO5eYmr5ArQgNqvYuBusd5JfOA/cL/AMCfNFUlLrLlSfh0+jQ4nLG5xZ/gACdsQt83pwPBmW8JF0Qy1vTLVfIwvsc2gRD9KP3exgeP0+Tz1jqGqsV9wmp1"

# Session captcha từ cookie/sessionStorage (cập nhật mỗi phiên)
CAPTCHA_SESSION = "019e3792-d579-700b-9e23-56d721b16432"

# UUID thiết bị từ cookie fatman_uuid
FATMAN_UUID = "ade7b55e-6d7e-94bc-a215-1e2697a32a97"

# Session ID từ cookie __fatman_session
FATMAN_SESSION_ID = "a703bf6a-6e3b-4714-bb46-f1f61aed19ff"
# ------------------------------------------------

COOKIES = {
    "window_width": "390",
    "cookies_agree_type": "3",
    "is12h": "0",
    "tzo": "7",
    "lng": "vi",
    "platform_type": "mobile",
    "che_i": "2",
    "coefview": "0",
    "fast_coupon": "true",
    "typeBetNames": "short",
    "fatman_uuid": FATMAN_UUID,
    "ggru": "202",
    "_glhf": "1779066605",
}

HEADERS = {
    "content-type": "application/vnd.api+json",
    "accept": "application/vnd.api+json",
    "x-requested-with": "XMLHttpRequest",
    "is-srv": "false",
    "x-svc-source": "__WELCOME_APP__",
    "x-app-n": "__WELCOME_APP__",
    "x-hd": X_HD,
    "x-captcha-token": X_CAPTCHA_TOKEN,
    "x-hunt-captcha-session": CAPTCHA_SESSION,
    "cache-control": "no-cache",
}


def send_flashcall(phone: str, country_code: str = "84") -> dict:
    payload = {
        "data": {
            "attributes": {
                "phone": phone,
                "country_code": country_code,
            }
        }
    }

    session = requests.Session()
    session.cookies.update(COOKIES)

    response = session.post(url, headers=HEADERS, json=payload)

    print(f"Status: {response.status_code}")
    print(f"Rate limit còn lại: {response.headers.get('x-ratelimit-remaining', 'N/A')}")
    print(f"Reset sau (giây): {response.headers.get('x-ratelimit-reset', 'N/A')}")

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    result = send_flashcall(phone="945987331", country_code="84")
    print(json.dumps(result, ensure_ascii=False, indent=2))
