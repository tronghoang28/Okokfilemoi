import sys
import os
import asyncio
import html
import math
import os
import random
import shlex
import signal
import sqlite3
import subprocess
import threading
import time
import re
import psutil
import aiohttp
from datetime import datetime, timedelta
from functools import wraps
import pytz
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
BASE_DIR = "/root/denvkl"
REMOTE_VPS_URL = "http://103.218.123.203:5000"
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "bot_secret_key_12345")
SCRIPT_LOCAL = {
    "call": ["tun13.py"],
    "spam": ["lenhsieuvip1.py", "lenhspam1.py"],
    "callsuper": ["callfull.py"],
    "smscall": ["sm.py"],
}
SCRIPT_REMOTE = {
    "vip": ["lonchau.py", "lonchau1.py"],
    "call": ["tun14.py"],
    "spam": ["07.py", "lenhlon.py", "lenhspam1.py", "lenhcall.py"],
    "callsuper": ["callfull2.py"],
    "full": ["pro24h.py"],
}
TIMEOUT_MAP = {
    "vip": 300,
    "spam": 300,
    "call": 300,
    "auto": 600,
    "tiktok": 2700,
    "ngl": 3600,
    "callsuper": 600,
    "smscall": 600,
    "full": 1200,
    "gmail": 600,
    "spamtele": 300,
}
DEFAULT_ROUNDS = {"spam": 2, "call": 1}
ALL_SCRIPTS = set()
for _d in (SCRIPT_LOCAL, SCRIPT_REMOTE):
    for _v in _d.values():
        ALL_SCRIPTS.update(_v)
ALL_SCRIPTS.update(
    ["tcp.py", "tt.py", "spamngl.py", "spamtele.py", "autovip.py", "gmailvip.py"]
)
SCRIPT_TIMEOUT_MINUTES = {
    "tt.py": 65,
    "spamngl.py": 65,
    "tcp.py": 25,
    "callfull.py": 25,
    "callfull2.py": 25,
    "pro24h.py": 60,
}
MA_TOKEN_BOT = os.getenv("BOT_TOKEN", "7945237130:AAFsKTv90VT2BU6jZ8WL-_Nx4vy9b0o92lo")
ID_ADMIN_MAC_DINH = "5365031415"
TEN_ADMIN_MAC_DINH = "Super Admin"
NHOM_CHO_PHEP = [-1003743197744]
AUTO_BOT_USERNAME = os.getenv("AUTO_BOT_USERNAME", "Thoatlamsaoduoc_bot")
THU_MUC_DU_LIEU = "./data"
os.makedirs(THU_MUC_DU_LIEU, exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
DUONG_DAN_DB = os.path.join(THU_MUC_DU_LIEU, "bot_data.db")
USER_PROCESSES = {}
PROCESS_LOCK = threading.Lock()
BOT_USERNAME = None
bot = Bot(token=MA_TOKEN_BOT, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
def tao_ket_noi_db():
    conn = sqlite3.connect(DUONG_DAN_DB, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn
class OptimizedCache:
    def __init__(self, max_size=100, ttl=300):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.ttl = ttl
    def get(self, key):
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
        return None
    def set(self, key, value):
        current_time = time.time()
        expired_keys = [
            k for k, t in self.timestamps.items() if current_time - t >= self.ttl
        ]
        for k in expired_keys:
            self.cache.pop(k, None)
            self.timestamps.pop(k, None)
        if len(self.cache) >= self.max_size:
            oldest_keys = sorted(self.timestamps.items(), key=lambda x: x[1])[
                : self.max_size // 3
            ]
            for k, _ in oldest_keys:
                self.cache.pop(k, None)
                self.timestamps.pop(k, None)
        self.cache[key] = value
        self.timestamps[key] = current_time
quyen_cache = OptimizedCache(max_size=50, ttl=600)
cooldown_cache = OptimizedCache(max_size=100, ttl=2000)
COMMAND_COOLDOWNS = {
    "admin": {"default": 0},
    "super_vip": {
        "callsuper": 1800,
        "smscall": 1800,
        "full": 3000,
        "gmail": 1800,
        "call": 300,
        "vip": 240,
        "spam": 300,
        "img": 90,
        "vid": 90,
        "ngl": 90,
        "tiktok": 1000,
        "gmail": 200,
        "spamtele": 190,
        "invite": 60,
        "default": 1200,
    },
    "vip": {
        "call": 300,
        "vip": 300,
        "spam": 300,
        "img": 90,
        "vid": 90,
        "ngl": 90,
        "tiktok": 1000,
        "spamtele": 190,
        "invite": 3000,
        "default": 1200,
    },
    "member": {
        "spam": 1000,
        "img": 90,
        "vid": 90,
        "ngl": 900,
        "spamtele": 90,
        "invite": 3000,
        "default": 1200,
    },
}
def script_should_run_remote(script_name: str, command_type: str) -> bool:
    if not REMOTE_VPS_URL:
        return False
    return script_name in SCRIPT_REMOTE.get(command_type, [])
async def goi_script_vps_khac(
    command_type: str, phone_numbers: list, user_id: int, script_name: str, **kwargs
):
    if not REMOTE_VPS_URL:
        return False, {"error": "VPS khác chưa được cấu hình"}
    try:
        payload = {
            "command_type": command_type,
            "phone_numbers": phone_numbers,
            "user_id": str(user_id),
            "script_name": script_name,
            "rounds": kwargs.get("rounds"),
        }
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.post(
                f"{REMOTE_VPS_URL}/execute",
                json=payload,
                headers={"Authorization": f"Bearer {API_SECRET_KEY}"},
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("success", False), result.get("data", {})
                else:
                    return False, {"error": f"VPS trả về lỗi: {resp.status}"}
    except asyncio.TimeoutError:
        return False, {"error": "Timeout kết nối VPS"}
    except Exception as e:
        logger.error(f"goi_script_vps_khac lỗi: {e}")
        return False, {"error": str(e)}
def get_carrier(phone):
    if not phone:
        return "Không xác định"
    phone = str(phone).strip()
    if phone.startswith("+84"):
        phone = "0" + phone[3:]
    elif phone.startswith("84"):
        phone = "0" + phone[2:]
    if len(phone) < 3:
        return "Không xác định"
    prefix = phone[:3]
    viettel = {
        "086",
        "096",
        "097",
        "098",
        "032",
        "033",
        "034",
        "035",
        "036",
        "037",
        "038",
        "039",
    }
    mobifone = {"089", "090", "093", "070", "079", "077", "076", "078"}
    vinaphone = {"088", "091", "094", "083", "084", "085", "081", "082"}
    vietnamobile = {"092", "056", "058"}
    gmobile = {"099", "059"}
    if prefix in viettel:
        return "𝑉𝑖𝑒𝑡𝑡𝑒𝑙"
    elif prefix in mobifone:
        return "𝑀𝑜𝑏𝑖𝑓𝑜𝑛𝑒"
    elif prefix in vinaphone:
        return "𝑉𝑖𝑛𝑎𝑝ℎ𝑜𝑛𝑒"
    elif prefix in vietnamobile:
        return "𝑉𝑖𝑒𝑡𝑛𝑎𝑚𝑜𝑏𝑖𝑙𝑒"
    elif prefix in gmobile:
        return "𝐺𝑚𝑜𝑏𝑖𝑙𝑒"
    return "𝐾ℎ𝑜̂𝑛𝑔 𝑥𝑎́𝑐 𝑑𝑖̣𝑛ℎ"
async def execute_with_swap(
    command_type: str, phone_numbers: list, user_id: int, **kwargs
):
    phone_str = " ".join(phone_numbers)
    local_list = SCRIPT_LOCAL.get(command_type, [])
    remote_list = SCRIPT_REMOTE.get(command_type, [])
    candidates = (
        [("local", s) for s in local_list]
        + [("remote", s) for s in remote_list]
    )
    if not candidates:
        return False, {"error": f"Không có script cho {command_type}"}

    mode, script_name = random.choice(candidates)

    rounds = kwargs.get("rounds")
    if rounds is None:
        if command_type in DEFAULT_ROUNDS:
            rounds = DEFAULT_ROUNDS[command_type]

    if mode == "remote":
        return await goi_script_vps_khac(
            command_type, phone_numbers, user_id, script_name, rounds=rounds
        )

    script_path = os.path.join(BASE_DIR, script_name)
    if command_type in DEFAULT_ROUNDS and rounds is not None:
        cmd = f"python3 {script_path} {phone_str} {rounds}"
    else:
        cmd = f"python3 {script_path} {phone_str}"
    success, pid = chay_script_don_gian(cmd, user_id, command_type=command_type)
    return success, {"script": script_name, "pid": pid}
async def kiem_tra_vip_het_han():
    while True:
        await asyncio.sleep(7200)  
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name, role, expiry_date FROM admin WHERE role IN ('vip', 'super_vip') AND expiry_date IS NOT NULL AND datetime(expiry_date) <= datetime('now', '+1 day')"
        )
        vip_users = cursor.fetchall()
        for user in vip_users:
            user_id = user["user_id"]
            role = user["role"]
            expiry_date = user["expiry_date"]
            try:
                expiry = datetime.fromisoformat(expiry_date)
                if datetime.now() > expiry:
                    cursor.execute("DELETE FROM admin WHERE user_id = ?", (user_id,))
                    conn.commit()
                    quyen_cache.set(user_id, "member")
            except Exception:
                continue
        conn.close()
def chay_script_don_gian(command, user_id=None, timeout=1200, command_type=None):
    try:
        if not command or not user_id:
            return False, None
        if command_type:
            timeout = TIMEOUT_MAP.get(command_type, timeout)
        with PROCESS_LOCK:
            user_procs = USER_PROCESSES.get(user_id, [])
            alive_procs = []
            for p in user_procs:
                if p.poll() is not None:
                    try:
                        p.wait(timeout=1)
                    except:
                        pass
                    continue
                proc_hung = False
                try:
                    ps_proc = psutil.Process(p.pid)
                    age_sec = time.time() - ps_proc.create_time()
                    max_allowed = max(TIMEOUT_MAP.values()) + 60
                    if age_sec > max_allowed:
                        proc_hung = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_hung = True
                if proc_hung:
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    try:
                        p.kill()
                        p.wait(timeout=1)
                    except:
                        pass
                else:
                    alive_procs.append(p)
            USER_PROCESSES[user_id] = alive_procs
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
            start_new_session=True,
            cwd=BASE_DIR,
        )
        with PROCESS_LOCK:
            if user_id not in USER_PROCESSES:
                USER_PROCESSES[user_id] = []
            USER_PROCESSES[user_id].append(process)
        def kill_after_timeout():
            time.sleep(timeout)
            try:
                if process.poll() is None:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except (ProcessLookupError, OSError):
                        pass
                    time.sleep(3)
                    if process.poll() is None:
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except (ProcessLookupError, OSError):
                            pass
                        try:
                            process.kill()
                        except:
                            pass
            except:
                pass
        timer_thread = threading.Thread(target=kill_after_timeout, daemon=True)
        timer_thread.start()
        return True, process.pid
    except Exception:
        return False, None
def cleanup_dead_processes():
    try:
        with PROCESS_LOCK:
            for user_id in list(USER_PROCESSES.keys()):
                alive_procs = []
                for p in USER_PROCESSES[user_id]:
                    if p.poll() is None:
                        alive_procs.append(p)
                    else:
                        try:
                            try:
                                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                            except (ProcessLookupError, OSError):
                                pass
                            p.wait(timeout=1)
                        except:
                            pass
                if alive_procs:
                    USER_PROCESSES[user_id] = alive_procs
                else:
                    USER_PROCESSES.pop(user_id, None)
        current_time = time.time()
        python_procs = [
            p for p in psutil.process_iter(
                ["pid", "name", "cmdline", "create_time", "status", "cpu_percent"]
            )
            if p.info and "python" in p.info.get("name", "").lower()
        ]
        for proc in python_procs:
            try:
                cmdline = proc.info.get("cmdline", [])
                if len(cmdline) < 2:
                    continue
                script_name = os.path.basename(cmdline[1]) if cmdline[1] else ""
                if script_name not in ALL_SCRIPTS:
                    continue
                age_minutes = (current_time - proc.info.get("create_time", 0)) / 60
                process_status = proc.info.get("status", "")
                should_kill = False
                script_timeout_min = SCRIPT_TIMEOUT_MINUTES.get(script_name, 10)
                if age_minutes > script_timeout_min:
                    should_kill = True
                if process_status in [psutil.STATUS_ZOMBIE, psutil.STATUS_STOPPED]:
                    should_kill = True
                elif age_minutes > 30:
                    try:
                        cpu_percent = proc.cpu_percent(interval=None)
                        if cpu_percent == 0.0:
                            should_kill = True
                    except:
                        should_kill = True
                if should_kill:
                    try:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        except (ProcessLookupError, OSError):
                            pass
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            try:
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            except (ProcessLookupError, OSError):
                                pass
                            proc.kill()
                            proc.wait(timeout=2)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue
    except Exception:
        pass
def force_kill_zombies():
    try:
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "create_time", "status"]
        ):
            try:
                if "python" not in proc.info["name"].lower():
                    continue
                cmdline = proc.info.get("cmdline", [])
                if len(cmdline) < 2:
                    continue
                script_name = os.path.basename(cmdline[1]) if cmdline[1] else ""
                if script_name not in ALL_SCRIPTS:
                    continue
                age_minutes = (time.time() - proc.info.get("create_time", 0)) / 60
                process_status = proc.info.get("status", "")
                script_timeout_min = SCRIPT_TIMEOUT_MINUTES.get(script_name, 10)
                if (
                    process_status in [psutil.STATUS_ZOMBIE, psutil.STATUS_STOPPED]
                    or age_minutes > script_timeout_min
                ):
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, OSError):
                        pass
                    try:
                        os.kill(proc.pid, 9)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                        pass
            except:
                continue
    except Exception:
        pass
async def schedule_cleanup():
    _cycle = 0
    while True:
        await asyncio.sleep(300)
        try:
            await asyncio.to_thread(cleanup_dead_processes)
        except Exception:
            pass
        _cycle += 1
        if _cycle % 4 == 0:
            try:
                await asyncio.to_thread(force_kill_zombies)
            except Exception:
                pass
def khoi_tao_database():
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TIMESTAMP,
                admin_added_by TEXT
            )
        """
        )
        try:
            cursor.execute("ALTER TABLE admin ADD COLUMN expiry_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE admin ADD COLUMN admin_added_by TEXT")
        except sqlite3.OperationalError:
            pass
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS thu_supervip_da_dung (
                user_id TEXT PRIMARY KEY,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Invite system tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_links (
                user_id TEXT,
                group_id INTEGER,
                invite_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, group_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_log (
                invited_user_id TEXT PRIMARY KEY,
                inviter_user_id TEXT,
                group_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invite_count (
                user_id TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass
def da_dung_thu_supervip(user_id) -> bool:
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM thu_supervip_da_dung WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False

def danh_dau_da_dung_thu_supervip(user_id):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO thu_supervip_da_dung (user_id) VALUES (?)",
            (str(user_id),)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def khoi_tao_admin_mac_dinh():
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM admin WHERE user_id = ?", (ID_ADMIN_MAC_DINH,)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO admin (user_id, name, role) VALUES (?, ?, ?)",
                (ID_ADMIN_MAC_DINH, TEN_ADMIN_MAC_DINH, "admin"),
            )
            conn.commit()
        conn.close()
    except Exception:
        pass
_JS_FILE_CACHE = {}
_FILE_ID_CACHE = {}

def doc_file_js(ten_file):
    try:
        if not os.path.exists(ten_file):
            return []
        mtime = os.path.getmtime(ten_file)
        cached = _JS_FILE_CACHE.get(ten_file)
        if cached and cached[0] == mtime:
            return cached[1]
        with open(ten_file, "r", encoding="utf-8") as file:
            noi_dung = file.read()
        pattern = r"\[([^\]]+)\]"
        match = re.search(pattern, noi_dung, re.DOTALL)
        urls = []
        if match:
            array_content = match.group(1)
            for line in array_content.split("\n"):
                line = line.strip()
                if line.startswith('"') and line.endswith('",'):
                    urls.append(line[1:-2])
                elif line.startswith('"') and line.endswith('"'):
                    urls.append(line[1:-1])
        _JS_FILE_CACHE[ten_file] = (mtime, urls)
        return urls
    except Exception:
        return []
def lay_cap_do_quyen_ngu_dung(user_id):
    user_id = str(user_id)
    if user_id == ID_ADMIN_MAC_DINH:
        return "admin"
    cached = quyen_cache.get(user_id)
    if cached:
        return cached
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, expiry_date FROM admin WHERE user_id = ? LIMIT 1", (user_id,)
        )
        result = cursor.fetchone()
        if result:
            role = result["role"]
            expiry_date = result["expiry_date"]
            if role in ("vip", "super_vip") and expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    if datetime.now() > expiry:
                        cursor.execute(
                            "DELETE FROM admin WHERE user_id = ?", (user_id,)
                        )
                        conn.commit()
                        conn.close()
                        quyen_cache.set(user_id, "member")
                        return "member"
                except:
                    pass
            conn.close()
            quyen_cache.set(user_id, role)
            return role
        conn.close()
        quyen_cache.set(user_id, "member")
        return "member"
    except Exception:
        return "member"
def la_admin(user_id):
    return lay_cap_do_quyen_ngu_dung(user_id) == "admin"
def la_vip_vinh_vien(user_id):
    cap_do = lay_cap_do_quyen_ngu_dung(user_id)
    return cap_do in ("admin", "vip", "super_vip")
def la_super_vip(user_id):
    return lay_cap_do_quyen_ngu_dung(user_id) == "super_vip"
def la_so_dien_thoai_hop_le(so_dien_thoai):
    if not so_dien_thoai or not so_dien_thoai.isdigit():
        return False
    if len(so_dien_thoai) not in [10, 11]:
        return False
    if len(so_dien_thoai) == 10 and so_dien_thoai[0] == "0":
        return True
    if len(so_dien_thoai) == 11 and so_dien_thoai[:2] == "84":
        return True
    return False
def check_cooldown(user_id, command):
    if la_admin(user_id):
        return False, 0
    key = f"{command}:{user_id}"
    last_use = cooldown_cache.get(key)
    if not last_use:
        return False, 0
    quyen = lay_cap_do_quyen_ngu_dung(user_id)
    user_cooldowns = COMMAND_COOLDOWNS.get(quyen, COMMAND_COOLDOWNS["member"])
    cooldown_time = user_cooldowns.get(command, user_cooldowns.get("default", 1200))
    elapsed = time.time() - last_use
    if elapsed < cooldown_time:
        return True, cooldown_time - elapsed
    return False, 0
def set_cooldown(user_id, command):
    if not la_admin(user_id):
        key = f"{command}:{user_id}"
        cooldown_cache.set(key, time.time())
def lay_thoi_gian_vn():
    try:
        mui_gio_vn = pytz.timezone("Asia/Ho_Chi_Minh")
        hien_tai = datetime.now(mui_gio_vn)
        return hien_tai.strftime("%H:%M:%S"), hien_tai.strftime("%d/%m/%Y")
    except:
        hien_tai = datetime.now()
        return hien_tai.strftime("%H:%M:%S"), hien_tai.strftime("%d/%m/%Y")
def escape_html(text):
    if text is None:
        return ""
    return html.escape(str(text))
def dinh_dang_thoi_gian_cooldown(giay):
    if giay <= 0:
        return "0 𝑔𝑖𝑎̂𝑦"
    giay_lam_tron = math.ceil(giay)
    if giay_lam_tron < 60:
        return f"{giay_lam_tron} 𝑔𝑖𝑎̂𝑦"
    phut = giay_lam_tron // 60
    giay_con_lai = giay_lam_tron % 60
    if giay_con_lai == 0:
        return f"{phut} 𝑃ℎ𝑢́𝑡"
    else:
        return f"{phut} 𝑃ℎ𝑢́𝑡 {giay_con_lai} 𝑔𝑖𝑎̂𝑦"
def dinh_dang_lien_ket_nguoi_dung(user, an_danh=False):
    try:
        if not user:
            return "Người dùng không rõ"
        user_id = user.id
        if an_danh:
            return f'<a href="tg://user?id={user_id}">𝑨̂̉𝒏 𝑫𝒂𝒏𝒉</a>'
        ten_day_du = user.full_name
        if ten_day_du:
            return f'<a href="tg://user?id={user_id}">{escape_html(ten_day_du)}</a>'
        else:
            return f'<a href="tg://user?id={user_id}">ID: {user_id}</a>'
    except:
        return "Người dùng không rõ"
def che_so_dien_thoai(sdt):
    sdt = str(sdt).strip()
    n = len(sdt)
    if n < 7:
        return sdt
    start = 5 if (sdt.startswith("84") and n == 11) else 4
    return sdt[:start] + "***" + sdt[start + 3:]

def lay_tieu_de_quyen(user_id):
    cap_do = lay_cap_do_quyen_ngu_dung(user_id)
    user_id_str = str(user_id)
    if cap_do == "admin":
        if user_id_str == "5365031415":
            return "👶🏻 𝑻𝒓𝒂̂̉𝒖 𝑻𝒓𝒆 "
            return "🧝🏻‍♂️ • 𝓐𝓭𝓶𝓲𝓷 "
    tieu_de = {
        "super_vip": "🏆 𝑺𝒖𝒑𝒆𝒓𝑽𝑰𝑷",
        "vip": "🧞‍♂️ 🅥🅘🅟 🧜🏻‍",
        "member": " ༉ 𝑀𝑒𝑚𝑏𝑒𝑟𝑠 ༉ ",
    }
    return tieu_de.get(cap_do, tieu_de["member"])
def tao_keyboard_lien_ket_nhom():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👶🏻 𝑻𝒓𝒂̂̉𝒖 𝑻𝒓𝒆 ",
                    url="https://t.me/@concucachp"                ),
                InlineKeyboardButton(
                    text=" 𝓐𝓭𝓶𝓲𝓷  🧝🏻‍♂️ ",
                    url="https://t.me/@chocopie7531"
                ),
            ]
        ]
    )

    return keyboard


def tao_keyboard_chat_rieng(start_command):
    username = "@Ngayemdibxu_bot".lstrip("@")
    url = f"https://t.me/{username}?start={start_command}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 𝑀𝑜̛̉ 𝑐ℎ𝑎𝑡 !",
                    url=url,
                )
            ]
        ]
    )


async def gui_phan_hoi_chuyen_chat_rieng(message, command, mo_ta):
    if not message.from_user:
        return False
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(message.from_user)
    noi_dung = (
        f"🪬 𝑪𝒉𝒂̀𝒐 𝑻𝒉𝒂̆̀𝒏𝒈 𝑴𝒂̣̆𝒕 𝑳𝒐̂̀𝒏 •.•\n"
        f"{lien_ket_nguoi_dung} 🪬\n\n"
        """
        f"𝐷𝑒̂̉ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 {command}, 𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑎̂́𝑛 𝑣𝑎̀𝑜 𝑝ℎ𝑖́𝑚 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 𝑑𝑒̂̉ 𝑛ℎ𝑎̆́𝑛 𝑡𝑖𝑛 𝑟𝑖𝑒̂𝑛𝑔 𝑣𝑜̛́𝑖 𝐵𝑂𝑇 !
        """
        f"{mo_ta}"
    )
    return await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        tu_dong_xoa_sau_giay=15,
        reply_markup=tao_keyboard_chat_rieng(command.lstrip("/")),
    )


def cooldown_decorator(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user:
            return False
        user_id = message.from_user.id
        func_name = func.__name__
        if func_name.startswith("xu_ly_"):
            command = func_name.replace("xu_ly_", "").replace("_", "")
            command_mapping = {
                "randomanh": "img",
                "randomvideo": "vid",
                "checkid": "checkid",
                "themvip": "themvip",
                "xoavip": "xoavip",
                "themadmin": "themadmin",
                "xoaadmin": "xoaadmin",
            }
            command = command_mapping.get(command, command)
        else:
            command = func_name
        is_cooldown, remaining = check_cooldown(user_id, command)
        if is_cooldown:
            time_str = dinh_dang_thoi_gian_cooldown(remaining)
            lien_ket = dinh_dang_lien_ket_nguoi_dung(message.from_user)
            await gui_phan_hoi(
                message,
                f"🐸 {lien_ket}, 𝑏𝑎̣𝑛 𝑐𝑎̂̀𝑛 𝑐ℎ𝑜̛̀ {time_str} 𝑛𝑢̛̃𝑎 𝑑𝑒̂̉ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑙𝑒̣̂𝑛ℎ 𝑛𝑎̀𝑦 ! 🎯",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=10,
            )
            return False
        result = await func(message, *args, **kwargs)
        if result is True:
            set_cooldown(user_id, command)
        return result
    return wrapper
def chi_nhom(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user:
            return False
        if la_admin(message.from_user.id):
            return await func(message, *args, **kwargs)
        if not message.chat or message.chat.id not in NHOM_CHO_PHEP:
            return False
        return await func(message, *args, **kwargs)
    return wrapper
def chi_admin(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user or not la_admin(message.from_user.id):
            await gui_phan_hoi(
                message,
                "𝐾ℎ𝑜̂𝑛𝑔 𝑑𝑢̉ 𝑞𝑢𝑦𝑒̂̀𝑛 𝑑𝑎̂𝑢 𝑏𝑎̣𝑛 𝑒̂ !",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=10,
            )
            return False
        return await func(message, *args, **kwargs)
    return wrapper
def chi_vip_vinh_vien(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        la_super_vip_nguoi_dung = bool(
            message.from_user and la_super_vip(message.from_user.id)
        )
        if not message.from_user or not (
            la_admin(message.from_user.id)
            or (
                la_vip_vinh_vien(message.from_user.id)
                and not la_super_vip_nguoi_dung
            )
        ):
            if la_super_vip_nguoi_dung:
                await gui_phan_hoi(
                    message,
                    "🏆 𝐵𝑎̣𝑛 𝑑𝑎𝑛𝑔 𝑙𝑎̀ 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 𝑛𝑒̂𝑛 𝑘ℎ𝑜̂𝑛𝑔 𝑡ℎ𝑒̂̉ 𝑑𝑢̀𝑛𝑔 𝑐𝑎́𝑐 𝑙𝑒̣̂𝑛ℎ 𝑉𝐼𝑃 𝑡ℎ𝑢̛𝑜̛̀𝑛𝑔.\n\n"
                    "🚀 𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑑𝑢̀𝑛𝑔 𝑐𝑎́𝑐 𝑔𝑜́𝑖 𝑐𝑎𝑜 𝑐𝑎̂́𝑝 ℎ𝑜̛𝑛 !"
                    xoa_tin_nguoi_dung=True,
                    tu_dong_xoa_sau_giay=20,
                    co_keyboard=True,
                )
                return False
            await gui_phan_hoi(
                message,
                f"🐸 𝐿𝑒̣̂𝑛ℎ 𝑛𝑎̀𝑦 𝑐ℎ𝑖̉ 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑉𝐼𝑃 !\n\n"
                f"🎯 𝐴̂́𝑛 𝑣𝑎̀𝑜 𝑛𝑢́𝑡 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 𝑑𝑒̂̉ 𝑙𝑖𝑒̂𝑛 ℎ𝑒̣̂ 𝐴𝑑𝑚𝑖𝑛 ℎ𝑜𝑎̣̆𝑐 𝑄𝑢𝑎̉𝑛 𝑙𝑖́ 𝑛ℎ𝑜́𝑚 !",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=20,
                co_keyboard=True,
            )
            return False
        return await func(message, *args, **kwargs)
    return wrapper


def chi_super_vip(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not message.from_user or not (
            la_admin(message.from_user.id) or la_super_vip(message.from_user.id)
        ):
            await gui_phan_hoi(
                message,
                "🐸 𝐿𝑒̣̂𝑛ℎ 𝑛𝑎̀𝑦 𝑐ℎ𝑖̉ 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 !\n\n"
                "🎯 𝐴̂́𝑛 𝑣𝑎̀𝑜 𝑛𝑢́𝑡 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 đ𝑒̂̉ 𝑙𝑖𝑒̂𝑛 ℎ𝑒̣̂ 𝐴𝑑𝑚𝑖𝑛 !",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=20,
                co_keyboard=True,
            )
            return False
        return await func(message, *args, **kwargs)

    return wrapper
async def gui_phan_hoi(
    message: Message,
    noi_dung: str,
    xoa_tin_nguoi_dung=True,
    tu_dong_xoa_sau_giay=10,
    luu_vinh_vien=False,
    co_keyboard=False,
    photo_path=None,
    reply_markup=None,
    tre_xoa_tin_nguoi_dung=0,
):
    try:
        chat_id = message.chat.id
        text = f"<blockquote>{noi_dung.strip()}</blockquote>"
        keyboard = (
            reply_markup
            if reply_markup
            else (tao_keyboard_lien_ket_nhom() if co_keyboard else None)
        )
        async def _gui_nhan_tin():
            try:
                if photo_path and os.path.exists(photo_path):
                    from aiogram.types import FSInputFile
                    cache_key = f"local::{photo_path}"
                    cached_id = _FILE_ID_CACHE.get(cache_key)
                    video_obj = cached_id if cached_id else FSInputFile(photo_path)
                    try:
                        sent_message = await bot.send_video(
                            chat_id=chat_id,
                            video=video_obj,
                            caption=text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=keyboard,
                        )
                    except Exception:
                        if cached_id:
                            _FILE_ID_CACHE.pop(cache_key, None)
                            sent_message = await bot.send_video(
                                chat_id=chat_id,
                                video=FSInputFile(photo_path),
                                caption=text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=keyboard,
                            )
                        else:
                            raise
                    try:
                        if not cached_id and sent_message and sent_message.video:
                            _FILE_ID_CACHE[cache_key] = sent_message.video.file_id
                    except Exception:
                        pass
                else:
                    sent_message = await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard,
                    )
                if tu_dong_xoa_sau_giay > 0 and not luu_vinh_vien and sent_message:
                    asyncio.create_task(
                        tu_dong_xoa_tin_nhan(
                            chat_id, sent_message.message_id, tu_dong_xoa_sau_giay
                        )
                    )
            except Exception:
                pass
        if photo_path and os.path.exists(photo_path):
            asyncio.create_task(_gui_nhan_tin())
        else:
            await _gui_nhan_tin()
        if xoa_tin_nguoi_dung:
            try:
                if tre_xoa_tin_nguoi_dung > 0:
                    asyncio.create_task(
                        tu_dong_xoa_tin_nhan(
                            chat_id, message.message_id, tre_xoa_tin_nguoi_dung
                        )
                    )
                else:
                    asyncio.create_task(
                        tu_dong_xoa_tin_nhan(chat_id, message.message_id, 0)
                    )
            except:
                pass
        return True
    except Exception:
        return None
async def tu_dong_xoa_tin_nhan(chat_id, message_id, tre=10):
    try:
        await asyncio.sleep(tre)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

def them_vip(user_id, ten, admin_added_by=None):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(days=30)
        cursor.execute(
            "INSERT OR REPLACE INTO admin (user_id, name, role, expiry_date, admin_added_by) VALUES (?, ?, ?, ?, ?)",
            (
                str(user_id),
                ten,
                "vip",
                expiry,
                str(admin_added_by) if admin_added_by else None,
            ),
        )
        conn.commit()
        conn.close()
        quyen_cache.set(str(user_id), "vip")
    except Exception:
        pass

def them_super_vip_thu(user_id, ten, admin_added_by=None, days=1):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute(
            "INSERT OR REPLACE INTO admin (user_id, name, role, expiry_date, admin_added_by) VALUES (?, ?, ?, ?, ?)",
            (
                str(user_id),
                ten,
                "super_vip",
                expiry,
                str(admin_added_by) if admin_added_by else None,
            ),
        )
        conn.commit()
        conn.close()
        quyen_cache.set(str(user_id), "super_vip")
        return expiry
    except Exception:
        return None

def them_admin(user_id, ten):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO admin (user_id, name, role) VALUES (?, ?, ?)",
            (str(user_id), ten, "admin"),
        )
        conn.commit()
        conn.close()
        quyen_cache.set(str(user_id), "admin")
    except Exception:
        pass
def trich_xuat_tham_so(message: Message):
    if not message.text:
        return []
    return message.text.split()[1:]

@chi_nhom
async def xu_ly_auto(message: Message):
    if not message.from_user:
        return False
    user_id = message.from_user.id
    user = message.from_user
    role = lay_cap_do_quyen_ngu_dung(user_id)
    if role in ("admin", "super_vip"):
        tieu_de = lay_tieu_de_quyen(user_id)
        lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 𝑀𝑜̛̉ 𝐵𝑜𝑡 𝐴𝑢𝑡𝑜 𝑉𝐼𝑃",
                        url=f"https://t.me/{AUTO_BOT_USERNAME}",  
                    )
                ]
            ]
        )
        noi_dung = (
            f"🤖 𝐶ℎ𝑎̀𝑜 {tieu_de}! {lien_ket_nguoi_dung}\n\n"
            f"✨ 𝐵𝑎̉𝑛𝑔 đ𝑖𝑒̂̀𝑢 𝑘ℎ𝑖𝑒̂̉𝑛 𝑆𝑢𝑝𝑒𝑟 𝑉𝐼𝑃\n\n"
            f"🎯 𝐻𝑎̃𝑦 𝑎̂́𝑛 𝑣𝑎̀𝑜 𝑛𝑢́𝑡 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 đ𝑒̂̉ 𝑏𝑎̆́𝑡 đ𝑎̂̀𝑢 𝑐𝑎̂́𝑢 ℎ𝑖̀𝑛ℎ !"
        )
        await gui_phan_hoi(
            message,
            noi_dung,
            xoa_tin_nguoi_dung=True,
            luu_vinh_vien=True,
            reply_markup=keyboard,
        )
    else:
        await gui_phan_hoi(
            message,
            "🐸 𝑅𝑎̂́𝑡 𝑡𝑖𝑒̂́𝑐, 𝑐ℎ𝑖̉ 𝑆𝑢𝑝𝑒𝑟 𝑉𝐼𝑃 ℎ𝑜𝑎̣̆𝑐 𝐴𝐷𝑀𝐼𝑁 𝑚𝑜̛́𝑖 𝑐𝑜́ 𝑞𝑢𝑦𝑒̂̀𝑛 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑡𝑖́𝑛ℎ 𝑛𝑎̆𝑛𝑔 ℎ𝑜̂̃ 𝑡𝑟𝑜̛̣ 𝑟𝑖𝑒̂𝑛𝑔 𝑛𝑎̀𝑦!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
@chi_admin
async def xu_ly_addsuper(message: Message):
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) < 1:
        await gui_phan_hoi(message, "𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /addsuper [ID]", tu_dong_xoa_sau_giay=5)
        return False
    target_id = cac_tham_so[0]
    ten = " ".join(cac_tham_so[1:]) if len(cac_tham_so) > 1 else f"SuperVIP_{target_id}"
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        expiry = datetime.now() + timedelta(days=30)
        cursor.execute(
            "INSERT OR REPLACE INTO admin (user_id, name, role, expiry_date, admin_added_by) VALUES (?, ?, ?, ?, ?)",
            (str(target_id), ten, "super_vip", expiry, str(message.from_user.id)),
        )
        conn.commit()
        conn.close()
        quyen_cache.set(str(target_id), "super_vip")
        await gui_phan_hoi(
            message,
            f" 𝐷𝑎̃ 𝑐𝑎̂́𝑝 𝑞𝑢𝑦𝑒̂̀𝑛 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 𝑐ℎ𝑜 {ten} (ID: {target_id})",
            luu_vinh_vien=True,
        )
    except Exception as e:
        await gui_phan_hoi(message, f"🐸 Lỗi: {str(e)}", tu_dong_xoa_sau_giay=5)
        return False
async def xu_ly_sta(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = str(user.id)
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    noi_dung = f"""{tieu_de}      :      {lien_ket_nguoi_dung}

 • /invite    -   𝑳𝒊𝒏𝒌 𝒎𝒐̛̀𝒊 𝒕𝒉𝒂̀𝒏𝒉 𝒗𝒊𝒆̂𝒏 !
 • /ping      -   𝑲𝒊𝒆̂̉𝒎 𝒕𝒓𝒂 𝒕𝒓𝒂̣𝒏𝒈 𝒕𝒉𝒂́𝒊 𝒃𝒐𝒕
 • /checkid   -   𝑿𝒆𝒎 𝒎𝒂̃ 𝑰𝑫 𝒏𝒈𝒖̛𝒐̛̀𝒊 𝒅𝒖̀𝒏𝒈

🚀 𝐿𝐸̣̂𝑁𝐻 𝐶𝑂̛ 𝐵𝐴̉𝑁 :
 • /free       -       𝑀𝑖𝑒̂̃𝑛 𝑝ℎ𝑖́ 𝑆𝑝𝑎𝑚 𝑆𝑀𝑆 𝑍𝑎𝑙𝑜
 • /callfree    -       𝑀𝑖𝑒̂̃𝑛 𝑝ℎ𝑖́ 𝑔𝑜̣𝑖 𝟹 𝑐𝑢𝑜̣̂𝑐
 • /img        -        𝑅𝑎𝑛𝑑𝑜𝑚 𝐴̉𝑛ℎ
 • /vid        -        𝑅𝑎𝑛𝑑𝑜𝑚 𝑉𝑖𝑑𝑒𝑜
 • /ngl        -        𝑆𝑝𝑎𝑚 𝑁𝐺𝐿

🔥 𝐿𝐸̣̂𝑁𝐻 𝑉𝐼𝑃 :
 • /spam        -       𝑆𝑝𝑎𝑚 𝑆𝑀𝑆 𝑍𝑎𝑙𝑜
 • /call        -        𝐺𝑜̣𝑖 1 𝑆𝑜̂́
 • /vip         -       𝑆𝑀𝑆 𝐶𝑎𝑙𝑙 30 𝑠𝑜̂́
 • /spamtele    -        𝑆𝑝𝑎𝑚 𝑇𝑒𝑙𝑒𝑔𝑟𝑎𝑚 
 • /tiktok      -      𝑇𝑎̆𝑛𝑔 𝑉𝑖𝑒𝑤 𝑇𝑖𝑘𝑇𝑜𝑘

🏆 𝐿𝐸̣̂𝑁𝐻 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 :
 • /auto       -       𝐴𝑢𝑡𝑜 𝑐ℎ𝑎̣𝑦 𝑑𝑒̂𝑚 𝟸𝟺/𝟽
 • /callsuper  -     𝑆𝑖𝑒̂𝑢 𝑐𝑎𝑙𝑙 𝟷𝟶 𝑠𝑜̂́ 𝑐𝑢̀𝑛𝑔 𝑙𝑢́𝑐
 • /smscall     -      𝑆𝑀𝑆 + 𝐶𝑎𝑙𝑙 10 𝑠𝑜̂́
 • /full        -      𝑀𝑎𝑥 𝟷𝟶𝟶 𝑆𝑜̂́
 • /gmail       -      𝑋𝑢̛̉ 𝑙𝑦́ 𝑒𝑚𝑎𝑖𝑙 𝑉𝐼𝑃

"""
    photo_path = ""  
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True
@cooldown_decorator
@chi_nhom
async def xu_ly_ping(message: Message):
    logger.info(
        f"📥 /ping từ user {message.from_user.id if message.from_user else 'unknown'}"
    )
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    noi_dung = f"""{tieu_de}      :      {lien_ket_nguoi_dung}
🆔 𝑀ã 𝐼𝐷         :        {user_id}
🤖 𝑇𝑟𝑎̣𝑛𝑔 𝑡ℎ𝑎́𝑖 𝐵𝑜𝑡     :    𝑂𝑛𝑙𝑖𝑛𝑒 🛰️
🚀 𝑆𝐴̆̃𝑁 𝑆𝐴̀𝑁𝐺 𝑁𝐻𝐴̣̂𝑁 𝐿𝐸̣̂𝑁𝐻 !  🎯"""
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True

@chi_nhom
async def xu_ly_callfree(message: Message):
    if not message.from_user:
        return False
    return await gui_phan_hoi_chuyen_chat_rieng(
        message,
        "/callfree",
        "Lệnh này được tiếp tục xử lý trong chat riêng với BOT.",
    )
@cooldown_decorator
@chi_nhom
@chi_vip_vinh_vien
async def xu_ly_spam(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /𝒔𝒑𝒂𝒎 𝟎𝟗𝟗𝟗𝟖𝟖𝟖𝟗𝟗𝟗 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    so_dien_thoai = cac_tham_so[0].strip()
    if not la_so_dien_thoai_hop_le(so_dien_thoai):
        await gui_phan_hoi(
            message,
            "🐸 Số điện thoại không hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    thanh_cong, result = await execute_with_swap(
        "spam", [so_dien_thoai], user_id, rounds=1
    )
    if not thanh_cong:
        await gui_phan_hoi(
            message,
            "🐸 𝑇𝑜̂́𝑖 𝑑𝑎 𝟷𝟶 𝑡𝑖𝑒̂́𝑛 𝑡𝑟𝑖̀𝑛ℎ 𝑚𝑜̂̃𝑖, 𝑐𝑜́ 𝑡ℎ𝑒̂̉ ℎ𝑒̂́𝑡 𝑡ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛 𝑐𝑜𝑜𝑙𝑑𝑜𝑤𝑛 𝑛ℎ𝑢̛𝑛𝑔 𝑐𝑎́𝑐 𝑠𝑜̂́ 𝑐𝑢̉𝑎 𝑏𝑎̣𝑛 𝑣𝑎̂̃𝑛 𝑑𝑎𝑛𝑔 𝑐ℎ𝑎̣𝑦 𝑡𝑟𝑒̂𝑛 𝑠𝑒𝑟𝑣𝑒𝑟 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    _an_danh = lay_cap_do_quyen_ngu_dung(user_id) == "super_vip"
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=_an_danh)
    so_hien_thi = che_so_dien_thoai(so_dien_thoai) if _an_danh else so_dien_thoai
    noi_dung = (
        f"{tieu_de}        :         {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷              :        {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁         :         {so_hien_thi}\n"
        f"🛰️ 𝑁ℎ𝑎̀ 𝑚𝑎̣𝑛𝑔        :         {get_carrier(so_dien_thoai)}\n"
        f"🪩 𝑉𝑖̣ 𝑡𝑟𝑖́                :         𝑉/𝑁 𝑂𝑛𝑙𝑖𝑛𝑒\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐒𝐏𝐀𝐌✧ 𝑑𝑎̃ 𝑐ℎ𝑎̣𝑦 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔\n"
        f" 𝑇𝑎̆𝑛𝑔 𝑡𝑜̂́𝑐 𝑔𝑢̛̉𝑖 𝑡𝑖𝑛 𝑟𝑎́𝑐 𝑙𝑖𝑒̂𝑛 𝑡𝑢̣𝑐 ! 🐸\n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True
@chi_nhom
async def xu_ly_free(message: Message):
    if not message.from_user:
        return False
    return await gui_phan_hoi_chuyen_chat_rieng(
        message,
        "/free",
        "Lệnh này được tiếp tục xử lý trong chat riêng với BOT.",
    )
@chi_nhom
@cooldown_decorator
async def xu_ly_callsuper(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cap_do = lay_cap_do_quyen_ngu_dung(user_id)
    if cap_do not in ("admin", "super_vip"):
        lien_ket = dinh_dang_lien_ket_nguoi_dung(user)
        # VIP được thử 3 ngày, member thường được 1 ngày
        so_ngay_thu = 3 if cap_do == "vip" else 1
        nhan_quyen = "𝐕𝐈𝐏 ✦" if cap_do == "vip" else "𝑀𝑒𝑚𝑏𝑒𝑟"
        da_dung = da_dung_thu_supervip(user_id)
        if da_dung:
            so_ngay_hien_thi = "𝟑 𝑛𝑔𝑎̀𝑦" if cap_do == "vip" else "𝟏 𝑛𝑔𝑎̀𝑦"
            noi_dung_tu_choi = (
                f"🏆 {lien_ket}\n\n"
                f"𝐵𝑎̣𝑛 𝑐ℎ𝑢̛𝑎 𝑐𝑜́ 𝑞𝑢𝑦𝑒̂̀𝑛 𝑐𝑎𝑜 ℎ𝑜̛𝑛 đ𝑒̂̉ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑡𝑖́𝑛ℎ 𝑛𝑎̆𝑛𝑔 𝑛𝑎̀𝑦 !\n\n"
                f"🐸 𝐵𝑎̣𝑛 đ𝑎̃ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑙𝑖𝑒̂𝑛 𝑘𝑒̂́𝑡 𝑡𝑟𝑎̉𝑖 𝑛𝑔ℎ𝑖𝑒̣̂𝑚 {so_ngay_hien_thi} 𝑟𝑜̂̀𝑖 !\n"
                f"𝐿𝑖𝑒̂𝑛 ℎ𝑒̣̂ 𝐴𝑑𝑚𝑖𝑛 đ𝑒̂̉ 𝑛𝑎̂𝑛𝑔 𝑐𝑎̂́𝑝 𝑡𝑎̀𝑖 𝑘ℎ𝑜𝑎̉𝑛."
            )
            await gui_phan_hoi(
                message,
                noi_dung_tu_choi,
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=15,
                co_keyboard=True,
            )
        else:
            so_ngay_hien_thi = "𝟑 𝑛𝑔𝑎̀𝑦" if so_ngay_thu == 3 else "𝟏 𝑛𝑔𝑎̀𝑦"
            noi_dung_tu_choi = (
                f"🏆 {lien_ket}  ─  {nhan_quyen}\n\n"
                f"𝐵𝑎̣𝑛 𝑐ℎ𝑢̛𝑎 𝑐𝑜́ 𝑞𝑢𝑦𝑒̂̀𝑛 𝑐𝑎𝑜 ℎ𝑜̛𝑛 đ𝑒̂̉ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑡𝑖́𝑛ℎ 𝑛𝑎̆𝑛𝑔 𝑛𝑎̀𝑦 !\n\n"
                f"✨ 𝑁ℎ𝑎̂́𝑝 𝑣𝑎̀𝑜 𝑛𝑢́𝑡 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 đ𝑒̂̉ 𝑡𝑢̛̣ đ𝑜̣̂𝑛𝑔 𝑙𝑒̂𝑛 𝐒𝐔𝐏𝐄𝐑 𝐕𝐈𝐏\n"
                f"𝑡𝑟𝑎̉𝑖 𝑛𝑔ℎ𝑖𝑒̣̂𝑚 𝑚𝑖𝑒̂̃𝑛 𝑝ℎ𝑖́ 𝑡𝑟𝑜𝑛𝑔 {so_ngay_hien_thi} !"
            )
            ten_nut = (
                f"🚀 𝑻𝒓𝒂̉𝒊 𝒏𝒈𝒉𝒊𝒆̣̂𝒎 𝑺𝑼𝑷𝑬𝑹 𝑽𝑰𝑷 𝟑 𝒏𝒈𝒂̀𝒚 𝒎𝒊𝒆̂̃𝒏 𝒑𝒉𝒊́ !"
                if so_ngay_thu == 3
                else "🚀 𝑻𝒓𝒂̉𝒊 𝒏𝒈𝒉𝒊𝒆̣̂𝒎 𝑺𝑼𝑷𝑬𝑹 𝑽𝑰𝑷 𝟏 𝒏𝒈𝒂̀𝒚 𝒎𝒊𝒆̂̃𝒏 𝒑𝒉𝒊́ !"
            )
            keyboard_thu = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=ten_nut,
                            callback_data=f"thu_supervip:{user_id}:{so_ngay_thu}",
                        )
                    ]
                ]
            )
            await gui_phan_hoi(
                message,
                noi_dung_tu_choi,
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=30,
                reply_markup=keyboard_thu,
            )
        return False
    _an_danh = cap_do == "super_vip"
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=_an_danh)
    cac_tham_so = trich_xuat_tham_so(message)
    if not cac_tham_so:
        await gui_phan_hoi(
            message,
            f"🤖 𝐶ℎ𝑎̀𝑜 {tieu_de}! {lien_ket_nguoi_dung}\n\n"
            f"📝 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /callsuper 𝑆𝐷𝑇1 𝑆𝐷𝑇2 ... (𝑡𝑜̂́𝑖 đ𝑎 10 𝑠𝑜̂́)",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=15,
        )
        # Chỉ hướng dẫn, chưa chạy lệnh nên không được kích hoạt cooldown.
        return False
    cac_so_hop_le = []
    for so in cac_tham_so:
        so = so.strip()
        if la_so_dien_thoai_hop_le(so):
            cac_so_hop_le.append(so)
    if not cac_so_hop_le:
        await gui_phan_hoi(
            message,
            "🐸 Số điện thoại không hợp lệ! Vui lòng nhập số Việt Nam (10-11 chữ số).",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    if len(cac_so_hop_le) > 10:
        await gui_phan_hoi(
            message,
            "🐸 𝑇𝑜̂́𝑖 đ𝑎 𝑐ℎ𝑖̉ đ𝑢̛𝑜̛̣𝑐 10 𝑠𝑜̂́ đ𝑖𝑒̣̂𝑛 𝑡ℎ𝑜𝑎̣𝑖 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    thanh_cong, result = await execute_with_swap("callsuper", cac_so_hop_le, user_id)
    if not thanh_cong:
        error_msg = result.get("error", "") if isinstance(result, dict) else ""
        await gui_phan_hoi(
            message,
            f"🐸 Không thể khởi động CallSuper trên VPS!\n{escape_html(error_msg)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()
    so_hien_thi = " | ".join(    
        f"{(che_so_dien_thoai(s) if _an_danh else s):<12}"
        for s in cac_so_hop_le    
    )
    noi_dung = (
        f"{tieu_de}        :        {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷               :       {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁         :        {len(cac_so_hop_le)} 𝑠𝑜̂́\n\n"
        f"📋 𝐷𝑎𝑛ℎ 𝑠𝑎́𝑐ℎ                \n{so_hien_thi}\n\n"
        f"🕜 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛          :         {chuoi_gio}\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐂𝐀𝐋𝐋 𝐒𝐔𝐏𝐄𝐑✧ đ𝑎̃ 𝑐ℎ𝑎̣𝑦 {len(cac_so_hop_le)} 𝑠𝑜̂́ 𝑐𝑢̀𝑛𝑔 𝑙𝑢́𝑐 !\n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True

@cooldown_decorator
@chi_nhom
@chi_vip_vinh_vien
async def xu_ly_vip(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if not cac_tham_so or len(cac_tham_so) < 2:
        await gui_phan_hoi(
            message,
            "🐸 /vip 0989299990 0988... (𝐼́𝑡 𝑛ℎ𝑎̂́𝑡 2 𝑠𝑜̂́, 𝑇𝑜̂́𝑖 𝑑𝑎 30 𝑠𝑜̂́) !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    if len(cac_tham_so) > 30:
        await gui_phan_hoi(
            message,
            "🐸 Lệnh /vip chỉ cho phép tối đa 30 số!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    cac_so_hop_le = []
    for so in cac_tham_so[:30]:
        so = so.strip()
        if la_so_dien_thoai_hop_le(so):
            cac_so_hop_le.append(so)
    if len(cac_so_hop_le) < 2:
        await gui_phan_hoi(
            message,
            "🐸 Bạn cần nhập ít nhất 2 số điện thoại hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    thanh_cong, result = await execute_with_swap(
        "vip", cac_so_hop_le, user_id
    )
    if not thanh_cong:
        await gui_phan_hoi(
            message,
            f"🐸 Không thể khởi tạo tiến trình VIP nào!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    noi_dung = (
        f"{tieu_de}       :       {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷             :       {user_id}\n"
        f"📲 𝑁ℎ𝑎̣̂𝑝 𝑇𝑎𝑦        :       {len(cac_so_hop_le)} 𝑠𝑜̂́ 𝐻𝑜̛̣𝑝 𝑙𝑒̣̂\n"
        f"⚡ 𝑇𝑖𝑒̂́𝑛 𝑡𝑟𝑖̀𝑛ℎ        :       Đ𝑜̛𝑛 𝑙𝑒̉ (1 𝑡𝑖𝑒̂́𝑛 𝑡𝑟𝑖̀𝑛ℎ)\n"
        f"🪩 𝑉𝑖̣ 𝑡𝑟𝑖́                :        𝑉/𝑁 𝑂𝑛𝑙𝑖𝑛𝑒\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐕𝐈𝐏✧ 𝑑𝑎̃ 𝑐ℎ𝑎̣𝑦 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔\n"
        f" 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛 𝑐ℎ𝑎̣𝑦 30 𝑝ℎ𝑢́𝑡... ! 🐸 \n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True
@cooldown_decorator
@chi_nhom
@chi_vip_vinh_vien
async def xu_ly_call(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /𝑐𝑎𝑙𝑙 0989226998 1 𝑠𝑜̂́ 𝑚𝑜̂̃𝑖 𝑙𝑎̂̀𝑛 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    so_dien_thoai = cac_tham_so[0].strip()
    if not la_so_dien_thoai_hop_le(so_dien_thoai):
        await gui_phan_hoi(
            message,
            "🐸 Số điện thoại không hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    thanh_cong, result = await execute_with_swap(
        "call", [so_dien_thoai], user_id, rounds=2
    )
    if not thanh_cong:
        await gui_phan_hoi(
            message,
            "🐸 𝑇𝑜̂́𝑖 𝑑𝑎 𝟷𝟶 𝑡𝑖𝑒̂́𝑛 𝑡𝑟𝑖̀𝑛ℎ 𝑚𝑜̂̃𝑖, 𝑐𝑜́ 𝑡ℎ𝑒̂̉ ℎ𝑒̂́𝑡 𝑡ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛 𝑐𝑜𝑜𝑙𝑑𝑜𝑤𝑛 𝑛ℎ𝑢̛𝑛𝑔 𝑐𝑎́𝑐 𝑠𝑜̂́ 𝑐𝑢̉𝑎 𝑏𝑎̣𝑛 𝑣𝑎̂̃𝑛 𝑑𝑎𝑛𝑔 𝑐ℎ𝑎̣𝑦 𝑡𝑟𝑒̂𝑛 𝑠𝑒𝑟𝑣𝑒𝑟 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    _an_danh = lay_cap_do_quyen_ngu_dung(user_id) == "super_vip"
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=_an_danh)
    so_hien_thi = che_so_dien_thoai(so_dien_thoai) if _an_danh else so_dien_thoai
    noi_dung = (
        f"{tieu_de}       :        {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷              :       {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁        :        {so_hien_thi}\n"
        f"🛰️ 𝑁ℎ𝑎̀ 𝑚𝑎̣𝑛𝑔       :        {get_carrier(so_dien_thoai)}\n"
        f"🪩 𝑉𝑖̣ 𝑡𝑟𝑖́                :        𝑉/𝑁 𝑂𝑛𝑙𝑖𝑛𝑒\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐂𝐀𝐋𝐋✧ 𝑑𝑎̃ 𝑐ℎ𝑎̣𝑦 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔\n"
        f" 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛 𝑐𝑜́ ℎ𝑖𝑒̣̂𝑢 𝑙𝑢̛̣𝑐 10 𝑝ℎ𝑢́𝑡 ! 🐸\n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True

@cooldown_decorator
@chi_nhom
async def xu_ly_smscall(message: Message):
    """Lệnh /smscall — chỉ Super VIP, tối đa 10 số, cooldown = callsuper."""
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cap_do = lay_cap_do_quyen_ngu_dung(user_id)
    if cap_do not in ("admin", "super_vip"):
        lien_ket = dinh_dang_lien_ket_nguoi_dung(user)
        da_dung = da_dung_thu_supervip(user_id)
        if da_dung:
            await gui_phan_hoi(
                message,
                f"🏆 {lien_ket}\n\n𝐿𝑒̣̂𝑛ℎ /smscall 𝑐ℎ𝑖̉ 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃.\n𝐿𝑖𝑒̂𝑛 ℎ𝑒̣̂ 𝐴𝑑𝑚𝑖𝑛 đ𝑒̂̉ 𝑛𝑎̂𝑛𝑔 𝑐𝑎̂́𝑝 𝑡𝑎̀𝑖 𝑘ℎ𝑜𝑎̉𝑛.",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=15,
                co_keyboard=True,
            )
        else:
            so_ngay_thu = 3 if cap_do == "vip" else 1
            ten_nut = (
                "🚀 𝑻𝒓𝒂̉𝒊 𝒏𝒈𝒉𝒊𝒆̣̂𝒎 𝑺𝑼𝑷𝑬𝑹 𝑽𝑰𝑷 𝟑 𝒏𝒈𝒂̀𝒚 𝒎𝒊𝒆̂̃𝒏 𝒑𝒉𝒊́ !"
                if so_ngay_thu == 3
                else "🚀 𝑻𝒓𝒂̉𝒊 𝒏𝒈𝒉𝒊𝒆̣̂𝒎 𝑺𝑼𝑷𝑬𝑹 𝑽𝑰𝑷 𝟏 𝒏𝒈𝒂̀𝒚 𝒎𝒊𝒆̂̃𝒏 𝒑𝒉𝒊́ !"
            )
            keyboard_thu = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(
                    text=ten_nut,
                    callback_data=f"thu_supervip:{user_id}:{so_ngay_thu}",
                )]]
            )
            nhan_quyen = "𝐕𝐈𝐏 ✦" if cap_do == "vip" else "𝑀𝑒𝑚𝑏𝑒𝑟"
            so_ngay_hien_thi = "𝟑 𝑛𝑔𝑎̀𝑦" if so_ngay_thu == 3 else "𝟏 𝑛𝑔𝑎̀𝑦"
            await gui_phan_hoi(
                message,
                f"🏆 {lien_ket}  ─  {nhan_quyen}\n\n"
                f"𝐿𝑒̣̂𝑛ℎ /smscall 𝑐ℎ𝑖̉ 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 !\n\n"
                f"✨ 𝑁ℎ𝑎̂́𝑝 𝑣𝑎̀𝑜 𝑛𝑢́𝑡 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖 đ𝑒̂̉ 𝑡𝑟𝑎̉𝑖 𝑛𝑔ℎ𝑖𝑒̣̂𝑚 𝑚𝑖𝑒̂̃𝑛 𝑝ℎ𝑖́ {so_ngay_hien_thi} !",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=30,
                reply_markup=keyboard_thu,
            )
        return False
    _an_danh = cap_do == "super_vip"
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=_an_danh)
    cac_tham_so = trich_xuat_tham_so(message)
    if not cac_tham_so:
        await gui_phan_hoi(
            message,
            f"🤖 𝐶ℎ𝑎̀𝑜 {tieu_de}! {lien_ket_nguoi_dung}\n\n"
            f"📝 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /smscall 𝑆𝐷𝑇1 𝑆𝐷𝑇2 ... (𝑡𝑜̂́𝑖 đ𝑎 10 𝑠𝑜̂́)",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=15,
        )
        return True
    cac_so_hop_le = [s.strip() for s in cac_tham_so if la_so_dien_thoai_hop_le(s.strip())]
    if not cac_so_hop_le:
        await gui_phan_hoi(
            message,
            "🐸 𝑆𝑜̂́ đ𝑖𝑒̣̂𝑛 𝑡ℎ𝑜𝑎̣𝑖 𝑘ℎ𝑜̂𝑛𝑔 ℎ𝑜̛̣𝑝 𝑙𝑒̣̂! 𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑛ℎ𝑎̣̂𝑝 𝑠𝑜̂́𝑉𝑖𝑒̣̂𝑡 𝑁𝑎𝑚 (10-11 𝑐ℎ𝑢̛̃ 𝑠𝑜̂́).",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    if len(cac_so_hop_le) > 10:
        await gui_phan_hoi(
            message,
            "🐸 𝑇𝑜̂́𝑖 đ𝑎 𝑐ℎ𝑖̉ đ𝑢̛𝑜̛̣𝑐 10 𝑠𝑜̂́ đ𝑖𝑒̣̂𝑛 𝑡ℎ𝑜𝑎̣𝑖 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    thanh_cong, result = await execute_with_swap("smscall", cac_so_hop_le, user_id)
    if not thanh_cong:
        error_msg = result.get("error", "") if isinstance(result, dict) else ""
        await gui_phan_hoi(
            message,
            f"🐸 𝐾ℎ𝑜̂𝑛𝑔 𝑡ℎ𝑒̂̉ 𝑘ℎ𝑜̛̉𝑖 đ𝑜̣̂𝑛𝑔 SMS𝐶𝑎𝑙𝑙 𝑡𝑟𝑒̂𝑛 𝑉𝑃𝑆!\n{escape_html(error_msg)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()
    so_hien_thi = " | ".join(
        f"{(che_so_dien_thoai(s) if _an_danh else s):<12}"
        for s in cac_so_hop_le
    )
    noi_dung = (
        f"{tieu_de}        :        {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷               :       {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁         :        {len(cac_so_hop_le)} 𝑠𝑜̂́\n\n"
        f"📋 𝐷𝑎𝑛ℎ 𝑠𝑎́𝑐ℎ                \n{so_hien_thi}\n\n"
        f"🕜 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛          :         {chuoi_gio}\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐒𝐌𝐒𝐂𝐀𝐋𝐋✧ đ𝑎̃ 𝑐ℎ𝑎̣𝑦 {len(cac_so_hop_le)} 𝑠𝑜̂́ 𝑐𝑢̀𝑛𝑔 𝑙𝑢́𝑐 !\n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True


@cooldown_decorator
@chi_nhom
@chi_super_vip
async def xu_ly_full(message: Message):
    if not message.from_user:
        return False

    user = message.from_user
    user_id = user.id
    user_role = lay_cap_do_quyen_ngu_dung(user_id)
    lien_ket = dinh_dang_lien_ket_nguoi_dung(
        user, an_danh=user_role == "super_vip"
    )
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = lien_ket
    cac_tham_so = trich_xuat_tham_so(message)

    if not cac_tham_so:
        await gui_phan_hoi(
            message,
            f"🫡 {lien_ket}\n\n"
            "📝 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /full 𝟶𝟿𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽 𝟶𝟿𝟶𝟿𝟾𝟽𝟼𝟻𝟺𝟹.....𝑙𝑒̣̂𝑛ℎ 𝑛𝑎̀𝑦 𝑛ℎ𝑎̣̂𝑛 𝑡𝑜̂́𝑖 𝑑𝑎 𝟷𝟶𝟶 𝑠𝑜̂́ 𝑚𝑜̂̃𝑖 𝑙𝑎̂̀𝑛 𝑐ℎ𝑎̣𝑦 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=15,
        )
        return False

    cac_so_hop_le = []
    for so in cac_tham_so:
        so = so.strip()
        if la_so_dien_thoai_hop_le(so):
            cac_so_hop_le.append(so)

    if not cac_so_hop_le:
    await gui_phan_hoi(
            message,
            "🐸 𝑆𝑜̂́ 𝑑𝑖𝑒̣̂𝑛 𝑡ℎ𝑜𝑎̣𝑖 𝑘ℎ𝑜̂𝑛𝑔 ℎ𝑜̛̣𝑝 𝑙𝑒̣̂! 𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑛ℎ𝑎̣̂𝑝 𝑠𝑜̂́ 𝑉𝑖𝑒̣̂𝑡 𝑁𝑎𝑚 "
            "(𝟷𝟶-𝟷𝟷 𝑐ℎ𝑢̛̃ 𝑠𝑜̂́).",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    if len(cac_so_hop_le) > 100:
        await gui_phan_hoi(
            message,
            "🐸 𝐿𝑒̣̂𝑛ℎ /full 𝑐ℎ𝑖̉ 𝑐ℎ𝑜 𝑝ℎ𝑒́𝑝 𝑡𝑜̂́𝑖 𝑑𝑎 𝟷𝟶𝟶 𝑠𝑜̂́ 𝑚𝑜̂̃𝑖 𝑙𝑎̂̀𝑛!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    thanh_cong, result = await execute_with_swap(
        "full", cac_so_hop_le, user_id
    )
    if not thanh_cong:
        error_msg = result.get("error", "") if isinstance(result, dict) else ""
        await gui_phan_hoi(
            message,
            f"🐸 Không thể khởi động Full trên VPS!\n{escape_html(error_msg)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()
    so_hien_thi = " | ".join(
        che_so_dien_thoai(so) if user_role == "super_vip" else so
        for so in cac_so_hop_le
    )
    noi_dung = (

        f"{tieu_de}        :        {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷               :       {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁         :        {len(cac_so_hop_le)} 𝑠𝑜̂́\n\n"
        f"🕜 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛          :         {chuoi_gio}\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝑭𝑼𝑳𝑳 𝑨𝑻𝑻𝑨𝑪𝑲✧ {len(cac_so_hop_le)} 𝑠𝑜̂́ 𝑐𝑢̀𝑛𝑔 𝑙𝑢́𝑐 !\n"
    )
        await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path="ANH1.MP4",
    )
    return True


@cooldown_decorator
@chi_nhom
@chi_vip_vinh_vien
async def xu_ly_tiktok(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /tiktok [link video tiktok]",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    link_tiktok = cac_tham_so[0].strip()
    if not ("tiktok.com" in link_tiktok or "vm.tiktok.com" in link_tiktok):
        await gui_phan_hoi(
            message,
            "🐸 Link TikTok không hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    script_tiktok = os.path.join(BASE_DIR, "tt.py")
    thanh_cong, pid = chay_script_don_gian(
        f"python3 {shlex.quote(script_tiktok)} {shlex.quote(link_tiktok)} 1000",
        user_id,
        command_type="tiktok",
    )
    if not thanh_cong:
        await gui_phan_hoi(
            message,
            "🐸 Lỗi khi khởi động lệnh tiktok!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    noi_dung = f"""{tieu_de}     :     {lien_ket_nguoi_dung}
🆔 𝑀ã 𝐼𝐷          :        {user_id}
🎬 Link            :       {escape_html(link_tiktok[:30])}
🪩 𝑆𝑒𝑟𝑣𝑒𝑟           :          𝑂𝑛𝑙𝑖𝑛𝑒
🚀 𝐿𝑒̣̂𝑛ℎ 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔〔❨✧𝐓𝐢𝐤𝐓𝐨𝐤✧❩〕"""
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True

@cooldown_decorator
@chi_nhom
async def xu_ly_ngl(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /ngl [link ngl]",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    link_ngl = cac_tham_so[0].strip()
    if not ("ngl.link" in link_ngl):
        await gui_phan_hoi(
            message,
            "🐸 Link NGL không hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    script_ngl = os.path.join(BASE_DIR, "spamngl.py")
    thanh_cong, pid = chay_script_don_gian(
        f"python3 {shlex.quote(script_ngl)} {shlex.quote(link_ngl)} 1000",
        user_id,
        command_type="ngl",
    )
    if not thanh_cong:
        await gui_phan_hoi(
            message,
            "🐸 Lỗi khi khởi động lệnh NGL!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()  
    noi_dung = f"""{tieu_de}      :       {lien_ket_nguoi_dung}
🆔 𝑀ã 𝐼𝐷          :           {user_id}
🛰️ Link           :         {escape_html(link_ngl[:30])}...
🎬 Target         :          1000+ messages
🕜 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛        :          {chuoi_gio}
🚀 𝐿𝑒̣̂𝑛ℎ 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔〔❨✧𝐍𝐆𝐋✧❩〕"""
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True
@cooldown_decorator
@chi_nhom

async def xu_ly_random_anh(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    danh_sach_anh = doc_file_js("/root/denvkl/images.js")
    if not danh_sach_anh:
        await gui_phan_hoi(
            message,
            "🐸 Không tìm thấy danh sách ảnh!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    anh_random = random.choice(danh_sach_anh)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()
    caption = (
        f"<blockquote>🏓 Random Ảnh cho {lien_ket_nguoi_dung}\n"
        f"⏱️ Thời gian: {chuoi_gio} - {chuoi_ngay}</blockquote>"
    )
    photo_payload = _FILE_ID_CACHE.get(anh_random, anh_random)
    try:
        sent = await asyncio.wait_for(
            bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_payload,
                caption=caption,
                parse_mode=ParseMode.HTML,
            ),
            timeout=30.0,
        )
        try:
            if sent and sent.photo:
                _FILE_ID_CACHE[anh_random] = sent.photo[-1].file_id
        except Exception:
            pass
        asyncio.create_task(
            tu_dong_xoa_tin_nhan(message.chat.id, message.message_id, 0)
        )
        return True
    except asyncio.TimeoutError:
        await gui_phan_hoi(
            message,
            "🐸 Timeout khi tải ảnh! Thử lại sau.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    except Exception as e:
        # Nếu file_id cache hỏng (bot đổi token...), xóa cache và thử URL gốc
        if anh_random in _FILE_ID_CACHE and photo_payload != anh_random:
            _FILE_ID_CACHE.pop(anh_random, None)
        if "failed to get HTTP URL content" in str(e) and len(danh_sach_anh) > 1:
            anh_backup = random.choice([a for a in danh_sach_anh if a != anh_random])
            backup_payload = _FILE_ID_CACHE.get(anh_backup, anh_backup)
            try:
                sent = await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=backup_payload,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
                try:
                    if sent and sent.photo:
                        _FILE_ID_CACHE[anh_backup] = sent.photo[-1].file_id
                except Exception:
                    pass
                return True
            except Exception:
                pass
        await gui_phan_hoi(
            message,
            "🐸 Không thể tải ảnh! URL có thể bị lỗi.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@cooldown_decorator
@chi_nhom
async def xu_ly_random_video(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    danh_sach_video = doc_file_js("/root/denvkl/videos.js")
    danh_sach_gif = doc_file_js("/root/denvkl/video2.js")
    tat_ca_video = danh_sach_video + danh_sach_gif
    if not tat_ca_video:
        await gui_phan_hoi(
            message,
            "🐸 Không tìm thấy danh sách video!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    video_random = random.choice(tat_ca_video)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()

    async def _gui_video(url):
        payload = _FILE_ID_CACHE.get(url, url)
        is_gif = url.endswith(".gif") or "giphy" in url
        caption_gif = (
            f"<blockquote>🎬 Random GIF cho {lien_ket_nguoi_dung}\n"
            f"⏱️ Thời gian: {chuoi_gio} - {chuoi_ngay}</blockquote>"
        )
        caption_video = (
            f"<blockquote>🎬 Random Video cho {lien_ket_nguoi_dung}\n"
            f"⏱️ Thời gian: {chuoi_gio} - {chuoi_ngay}</blockquote>"
        )
        if is_gif:
            sent = await bot.send_animation(
                chat_id=message.chat.id,
                animation=payload,
                caption=caption_gif,
                parse_mode=ParseMode.HTML,
            )
            try:
                if sent and sent.animation:
                    _FILE_ID_CACHE[url] = sent.animation.file_id
            except Exception:
                pass
        else:
            sent = await bot.send_video(
                chat_id=message.chat.id,
                video=payload,
                caption=caption_video,
                parse_mode=ParseMode.HTML,
            )
            try:
                if sent and sent.video:
                    _FILE_ID_CACHE[url] = sent.video.file_id
            except Exception:
                pass

    try:
        await asyncio.wait_for(_gui_video(video_random), timeout=45.0)
        asyncio.create_task(
            tu_dong_xoa_tin_nhan(message.chat.id, message.message_id, 0)
        )
        return True
    except asyncio.TimeoutError:
        await gui_phan_hoi(
            message,
            "🐸 Timeout khi tải video! File quá lớn.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    except Exception as e:
        if video_random in _FILE_ID_CACHE:
            _FILE_ID_CACHE.pop(video_random, None)
        if "failed to get HTTP URL content" in str(e) and len(tat_ca_video) > 1:
            video_backup = random.choice([v for v in tat_ca_video if v != video_random])
            try:
                await _gui_video(video_backup)
                return True
            except Exception:
                pass
        await gui_phan_hoi(
            message,
            "🐸 Không thể tải video! URL có thể bị lỗi.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@chi_nhom
async def xu_ly_checkid(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    is_admin = la_admin(user_id)
    target_user = None
    target_user_id = None
    target_user_name = None
    cac_tham_so = trich_xuat_tham_so(message)
    if message.reply_to_message and message.reply_to_message.from_user:
        if is_admin:
            target_user = message.reply_to_message.from_user
            target_user_id = target_user.id
            target_user_name = target_user.full_name or target_user.first_name
    elif len(cac_tham_so) >= 1 and is_admin:
        try:
            target_user_id = int(cac_tham_so[0].strip())
            try:
                chat_info = await bot.get_chat(target_user_id)
                target_user_name = (
                    chat_info.full_name
                    or chat_info.first_name
                    or f"User {target_user_id}"
                )
            except:
                target_user_name = f"User {target_user_id}"
        except ValueError:
            pass
    if target_user_id and is_admin:
        check_user_id = target_user_id
        check_user_name = target_user_name
        lien_ket_nguoi_dung = (
            f'<a href="tg://user?id={check_user_id}">{escape_html(check_user_name)}</a>'
        )
    else:
        check_user_id = user_id
        check_user_name = user.full_name or user.first_name
        lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=lay_cap_do_quyen_ngu_dung(user_id) == "super_vip")
    cap_do = lay_cap_do_quyen_ngu_dung(check_user_id)
    tieu_de = lay_tieu_de_quyen(check_user_id)
    expiry_info = ""
    if cap_do in ("vip", "super_vip"):
        try:
            conn = tao_ket_noi_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT expiry_date FROM admin WHERE user_id = ? AND role IN ('vip', 'super_vip')",
                (str(check_user_id),),
            )
            result = cursor.fetchone()
            conn.close()
            if result and result["expiry_date"]:
                expiry_date = datetime.fromisoformat(result["expiry_date"])
                now = datetime.now()
                remaining = expiry_date - now
                if remaining.total_seconds() > 0:
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    expiry_info = (
                        f"⏰ 𝐶𝑜̀𝑛 𝑙𝑎̣𝑖           :       {days} 𝑛𝑔𝑎̀𝑦 {hours} 𝑔𝑖𝑜̛̀\n"
                    )
                    expiry_info += f"📅 𝐻𝑒̂́𝑡 ℎ𝑎̣𝑛          :       {expiry_date.strftime('%d/%m/%Y %H:%M')}\n"
                else:
                    expiry_info = "\n🐸 𝑉𝐼𝑃 đ𝑎̃ ℎ𝑒̂́𝑡 ℎ𝑎̣𝑛!\n"
        except:
            pass
    elif cap_do == "admin":
        expiry_info = " 𝑇𝑢̛̣ 𝐻𝑜𝑎̀𝑛 𝑇ℎ𝑖𝑒̣̂𝑛 ! "
    quyen_text = {
        "admin": "🪬 𝐴𝑑𝑚𝑖𝑛",
        "super_vip": "🏆 𝑆𝑢𝑝𝑒𝑟𝑉𝐼𝑃",
        "vip": "🌀 𝑉𝐼𝑃",
        "member": "👤 𝑀𝑒𝑚𝑏𝑒𝑟",
    }.get(cap_do, cap_do)
    noi_dung = f"""{tieu_de}      :       {lien_ket_nguoi_dung}
🆔 𝑀ã 𝐼𝐷            :       {check_user_id}
✨ 𝑄𝑢𝑦𝑒̂̀𝑛            :       {quyen_text}
{expiry_info}
"""
    if cap_do == "member":
        noi_dung += "\n𝐵𝑎̣𝑛 𝑐𝑜́ 𝑡ℎ𝑒̂̉ 𝑑𝑢̀𝑛𝑔 𝑙𝑒̣̂𝑛ℎ 𝑓𝑟𝑒𝑒 𝑣𝑎̀ 𝑠𝑚𝑠 𝑚𝑖𝑒̂̃𝑛 𝑝ℎ𝑖́ !"
    elif cap_do == "vip":
        noi_dung += "\n🎯 𝑆𝑢̛̉ 𝑑𝑢̣𝑛𝑔 đ𝑎̂̀𝑦 đ𝑢̉ 𝑐𝑎́𝑐 𝑙𝑒̣̂𝑛ℎ 𝑉𝐼𝑃!"
    elif cap_do == "super_vip":
        noi_dung += "\n🏆 𝑇𝑜𝑎̀𝑛 𝑞𝑢𝑦𝑒̂̀𝑛 𝑆𝑈𝑃𝐸𝑅 𝑉𝐼𝑃 "
    elif cap_do == "admin":
        noi_dung += "\n🎯 𝑇𝑜𝑎̀𝑛 𝑞𝑢𝑦𝑒̂̀𝑛 𝑞𝑢𝑎̉𝑛 𝑡𝑟𝑖̣!"
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True
@cooldown_decorator
@chi_nhom
@chi_admin
async def xu_ly_them_vip(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) < 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /themvip USER_ID [TÊN]",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    id_muc_tieu = cac_tham_so[0].strip()
    ten_muc_tieu = " ".join(cac_tham_so[1:]) if len(cac_tham_so) > 1 else "VIP User"
    try:
        them_vip(id_muc_tieu, ten_muc_tieu, user.id)
        lien_ket_muc_tieu = (
            f'<a href="tg://user?id={id_muc_tieu}">{escape_html(ten_muc_tieu)}</a>'
        )
        lien_ket_admin = dinh_dang_lien_ket_nguoi_dung(user)
        noi_dung = (
            f"✨ 𝐷𝑎̃ 𝑡ℎ𝑒̂𝑚 𝑉𝐼𝑃 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔 !\n\n"
            f"🧞‍♂️ 𝑉𝐼𝑃 𝑀𝑜̛́𝑖         :        {lien_ket_muc_tieu}\n"
            f"🆔 𝑈𝑠𝑒𝑟 𝐼𝐷         :        {id_muc_tieu}\n"
            f"💬 𝑇ℎ𝑒̂𝑚 𝑏𝑜̛̉𝑖        :        {lien_ket_admin}\n"
            f"📅 𝑇ℎ𝑜̛̀𝑖 ℎ𝑎̣𝑛         :        30 𝑛𝑔𝑎̀𝑦"
        )
        await gui_phan_hoi(
            message, noi_dung, xoa_tin_nguoi_dung=True, luu_vinh_vien=True
        )
        return True
    except Exception as e:
        await gui_phan_hoi(
            message,
            f"Lỗi khi thêm VIP: {str(e)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@cooldown_decorator
@chi_nhom
@chi_admin
async def xu_ly_xoa_vip(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /xoavip USER_ID",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    id_muc_tieu = cac_tham_so[0].strip()
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM admin WHERE user_id = ? AND role IN ('vip', 'super_vip')",
            (id_muc_tieu,),
        )
        vip_info = cursor.fetchone()
        cursor.execute(
            "DELETE FROM admin WHERE user_id = ? AND role IN ('vip', 'super_vip')",
            (id_muc_tieu,),
        )
        so_hang_xoa = cursor.rowcount
        conn.commit()
        conn.close()
        quyen_cache.set(id_muc_tieu, "member")
        if so_hang_xoa > 0:
            ten_vip = vip_info[0] if vip_info and vip_info[0] else "VIP User"
            lien_ket_vip_xoa = (
                f'<a href="tg://user?id={id_muc_tieu}">{escape_html(ten_vip)}</a>'
            )
            lien_ket_admin = dinh_dang_lien_ket_nguoi_dung(user)
            noi_dung = (
                f"🗑️ 𝐷𝑎̃ 𝑥𝑜́𝑎 𝑉𝐼𝑃 !\n\n"
                f"👤 𝑁𝑔𝑢̛𝑜̛̀𝑖 𝑏𝑖̣ 𝑥𝑜́𝑎     :       {lien_ket_vip_xoa}\n"
                f"🆔 𝑈𝑠𝑒𝑟 𝐼𝐷          :       {id_muc_tieu}\n\n"
                f"🥷🏿 𝑋𝑜́𝑎 𝑏𝑜̛̉𝑖          :       {lien_ket_admin}"
            )
        else:
            lien_ket_khong_tim_thay = (
                f'<a href="tg://user?id={id_muc_tieu}">User {id_muc_tieu}</a>'
            )
            noi_dung = f" 𝐾ℎ𝑜̂𝑛𝑔 𝑡𝑖̀𝑚 𝑡ℎ𝑎̂́𝑦 𝑉𝐼𝑃: {lien_ket_khong_tim_thay}"
        await gui_phan_hoi(
            message, noi_dung, xoa_tin_nguoi_dung=True, luu_vinh_vien=True
        )
        return True
    except Exception as e:
        await gui_phan_hoi(
            message,
            f"Lỗi khi xóa VIP: {str(e)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@cooldown_decorator
@chi_nhom
@chi_admin
async def xu_ly_them_admin(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) < 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /themadmin USER_ID [TÊN]",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    id_muc_tieu = cac_tham_so[0].strip()
    ten_muc_tieu = " ".join(cac_tham_so[1:]) if len(cac_tham_so) > 1 else "Admin Thêm"
    try:
        them_admin(id_muc_tieu, ten_muc_tieu)
        noi_dung = f"Đã thêm Admin: {id_muc_tieu} - {ten_muc_tieu}"
        await gui_phan_hoi(
            message, noi_dung, xoa_tin_nguoi_dung=True, luu_vinh_vien=True
        )
        return True
    except Exception as e:
        await gui_phan_hoi(
            message,
            f"Lỗi khi thêm Admin: {str(e)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@cooldown_decorator
@chi_nhom
@chi_admin
async def xu_ly_xoa_admin(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "🐸 Cú pháp: /xoaadmin USER_ID",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    id_muc_tieu = cac_tham_so[0].strip()
    if id_muc_tieu == ID_ADMIN_MAC_DINH:
        await gui_phan_hoi(
            message,
            "Không thể xóa Super Admin!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM admin WHERE user_id = ? AND role = 'admin'", (id_muc_tieu,)
        )
        so_hang_xoa = cursor.rowcount
        conn.commit()
        conn.close()
        quyen_cache.set(id_muc_tieu, "member")
        if so_hang_xoa > 0:
            noi_dung = f"Đã xóa Admin: {id_muc_tieu}"
        else:
            noi_dung = f"Không tìm thấy Admin: {id_muc_tieu}"
        await gui_phan_hoi(
            message, noi_dung, xoa_tin_nguoi_dung=True, luu_vinh_vien=True
        )
        return True
    except Exception as e:
        await gui_phan_hoi(
            message,
            f"Lỗi khi xóa Admin: {str(e)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
@cooldown_decorator
@chi_nhom
@chi_vip_vinh_vien
async def xu_ly_spamtele(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if not cac_tham_so:
        await gui_phan_hoi(
            message,
            "📱 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /spamtele 0909123456",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    so_dien_thoai = cac_tham_so[0].strip()
    if not la_so_dien_thoai_hop_le(so_dien_thoai):
        await gui_phan_hoi(
            message,
            "🐸 Số điện thoại không hợp lệ!",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    script_path = os.path.join(BASE_DIR, "spamtele.py")
    cmd = f"python3 {shlex.quote(script_path)} {shlex.quote(so_dien_thoai)}"
    success, pid = chay_script_don_gian(cmd, user_id, command_type="spamtele")
    if not success:
        await gui_phan_hoi(
            message,
            "🐸 𝑇𝑜̂́𝑖 𝑑𝑎 𝟷𝟶 𝑡𝑖𝑒̂́𝑛 𝑡𝑟𝑖̀𝑛ℎ 𝑚𝑜̂̃𝑖, 𝑐𝑜́ 𝑡ℎ𝑒̂̉ ℎ𝑒̂́𝑡 𝑡ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛 𝑐𝑜𝑜𝑙𝑑𝑜𝑤𝑛 𝑛ℎ𝑢̛𝑛𝑔 𝑐𝑎́𝑐 𝑠𝑜̂́ 𝑐𝑢̉𝑎 𝑏𝑎̣𝑛 𝑣𝑎̂̃𝑛 𝑑𝑎𝑛𝑔 𝑐ℎ𝑎̣𝑦 𝑡𝑟𝑒̂𝑛 𝑠𝑒𝑟𝑣𝑒𝑟 !",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
    _an_danh = lay_cap_do_quyen_ngu_dung(user_id) == "super_vip"
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(user, an_danh=_an_danh)
    so_hien_thi = che_so_dien_thoai(so_dien_thoai) if _an_danh else so_dien_thoai
    noi_dung = (
        f"{tieu_de}        :         {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷              :        {user_id}\n"
        f"📲 𝑃ℎ𝑜𝑛𝑒 𝑉𝑁         :         {so_hien_thi}\n"
        f"🛰️ 𝑁ℎ𝑎̀ 𝑚𝑎̣𝑛𝑔        :         {get_carrier(so_dien_thoai)}\n"
        f"🪩 𝑉𝑖̣ 𝑡𝑟𝑖́                :         𝑉/𝑁 𝑂𝑛𝑙𝑖𝑛𝑒\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝑺𝑷𝑨𝑴 𝑻𝑬𝑳𝑬✧ 𝑑𝑎̃ 𝑐ℎ𝑎̣𝑦 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔\n"
        f" 𝐵𝑜𝑚𝑏 𝑡𝑖𝑛 𝑇𝑒𝑙𝑒𝑔𝑟𝑎𝑚 𝑙𝑖𝑒̂𝑛 𝑡𝑢̣𝑐 ! 🎯\n"
    )
    photo_path = "ANH1.MP4"
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path=photo_path,
    )
    return True


@cooldown_decorator
@chi_nhom
@chi_super_vip
async def xu_ly_gmail(message: Message):
    if not message.from_user:
        return False

    user = message.from_user
    user_id = user.id
    cac_tham_so = trich_xuat_tham_so(message)
    if len(cac_tham_so) != 1:
        await gui_phan_hoi(
            message,
            "📧 𝐶𝑢́ 𝑝ℎ𝑎́𝑝: /gmail ten@gmail.com",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    email = cac_tham_so[0].strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        await gui_phan_hoi(
            message,
            "🐸 Email không hợp lệ! Vui lòng nhập theo dạng ten@gmail.com.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    script_path = os.path.join(BASE_DIR, "gmailvip.py")
    cmd = f"python3 {shlex.quote(script_path)} {shlex.quote(email)}"
    success, pid = chay_script_don_gian(cmd, user_id, command_type="gmail")
    if not success:
        await gui_phan_hoi(
            message,
            "🐸 𝐾ℎ𝑜̂𝑛𝑔 𝑡ℎ𝑒̂̉ 𝑘ℎ𝑜̛̉𝑖 đ𝑜̣̂𝑛𝑔 𝑙𝑒̣̂𝑛ℎ Gmail! "
            "𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑡ℎ𝑢̛̉ 𝑙𝑎̣𝑖 𝑠𝑎𝑢.",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False

    cap_do = lay_cap_do_quyen_ngu_dung(user_id)
    tieu_de = lay_tieu_de_quyen(user_id)
    lien_ket_nguoi_dung = dinh_dang_lien_ket_nguoi_dung(
        user, an_danh=cap_do == "super_vip"
    )
    chuoi_gio, chuoi_ngay = lay_thoi_gian_vn()
    noi_dung = (
        f"{tieu_de}        :         {lien_ket_nguoi_dung}\n"
        f"🆔 𝑀ã 𝐼𝐷              :        {user_id}\n"
        f"📧 𝐸𝑚𝑎𝑖𝑙              :        {escape_html(email)}\n"
        f"🕜 𝑇ℎ𝑜̛̀𝑖 𝑔𝑖𝑎𝑛        :        {chuoi_gio} - {chuoi_ngay}\n"
        f"🪩 𝑉𝑖̣ 𝑡𝑟𝑖́                :        𝑉/𝑁 𝑂𝑛𝑙𝑖𝑛𝑒\n\n"
        f"🚀 𝐿𝑒̣̂𝑛ℎ ✧𝐺𝑀𝐴𝐼𝐿 𝑉𝐼𝑃✧ đ𝑎̃ 𝑐ℎ𝑎̣𝑦 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔\n"
        f" 𝑆𝑐𝑟𝑖𝑝𝑡 𝑑𝑎̃ đ𝑢̛𝑜̛̣𝑐 𝑘ℎ𝑜̛̉𝑖 𝑐ℎ𝑎̣𝑦 𝑡𝑟𝑒̂𝑛 𝑠𝑒𝑟𝑣𝑒𝑟 ! 🎯"
    )
    await gui_phan_hoi(
        message,
        noi_dung,
        xoa_tin_nguoi_dung=True,
        luu_vinh_vien=True,
        co_keyboard=True,
        photo_path="ANH1.MP4",
    )
    return True


@chi_nhom
@chi_admin
async def xu_ly_cleanup(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    lien_ket_admin = dinh_dang_lien_ket_nguoi_dung(user)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass
    script_path = os.path.join(BASE_DIR, "vps.py")
    subprocess.Popen(
        f"python3 {shlex.quote(script_path)}",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
        start_new_session=True,
        cwd=BASE_DIR,
    )
    noi_dung = (
        f"🧹 𝐷𝑜̣𝑛 𝑑𝑒̣𝑝 𝑉𝑃𝑆 𝑑𝑎̃ 𝑘ℎ𝑜̛̉𝑖 𝑐ℎ𝑎̣𝑦 !\n"
        f"• 🥷🏿 𝑇ℎ𝑢̛̣𝑐 ℎ𝑖𝑒̣̂𝑛 𝑏𝑜̛̉𝑖 : {lien_ket_admin}\n"
        f"• 🚀 𝑉𝑃𝑆 𝑑𝑎𝑛𝑔 𝑑𝑢̛𝑜̛̣𝑐 𝑡𝑜̂́𝑖 𝑢̛u ℎ𝑜́𝑎 𝑛𝑒̂̀𝑛 !"
    )
    await gui_phan_hoi(
        message,
        noi_dung,
        luu_vinh_vien=False,
        tu_dong_xoa_sau_giay=10,
    )
    return True


@chi_nhom
@chi_admin
async def xu_ly_prx(message: Message):
    if not message.from_user:
        return False
    user = message.from_user
    lien_ket_admin = dinh_dang_lien_ket_nguoi_dung(user)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass
    script_path = os.path.join(BASE_DIR, "prx.py")
    subprocess.Popen(
        f"python3 {shlex.quote(script_path)}",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
        start_new_session=True,
        cwd=BASE_DIR,
    )
    noi_dung = (
        f"• 🥷🏿 𝑇ℎ𝑢̛̣𝑐 ℎ𝑖𝑒̣̂𝑛 𝑏𝑜̛̉𝑖 : {lien_ket_admin}\n"
    )
    await gui_phan_hoi(
        message,
        noi_dung,
        luu_vinh_vien=False,
        tu_dong_xoa_sau_giay=10,
    )
    return True


@chi_nhom
@chi_admin
async def xu_ly_xem_danh_sach_vip(message: Message):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name, admin_added_by, expiry_date, role FROM admin WHERE role IN ('vip', 'super_vip') ORDER BY role DESC, name ASC"
        )
        vip_list = cursor.fetchall()
        conn.close()
        if not vip_list:
            await gui_phan_hoi(
                message,
                "Chưa có VIP nào trong hệ thống!",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=15,
            )
            return False
        noi_dung = "📋 𝐷𝐀𝐍𝐇 𝐒𝐀́𝐂𝐇 𝐕𝐈𝐏:\n\n"
        vip_only = [v for v in vip_list if v["role"] == "vip"]
        super_vip_only = [v for v in vip_list if v["role"] == "super_vip"]
        if super_vip_only:
            noi_dung += "🏆 𝐒𝐔𝐏𝐄𝐑 𝐕𝐈𝐏:\n\n"
            for vip in super_vip_only:
                user_id = vip[0]
                user_name = vip[1] if vip[1] else f"User_{str(user_id)[-4:]}"
                lien_ket_nguoi_dung = (
                    f'<a href="tg://user?id={user_id}">{escape_html(user_name)}</a>'
                )
                expiry_str = ""
                if vip[3]:
                    try:
                        expiry = datetime.fromisoformat(vip[3])
                        now = datetime.now()
                        if expiry > now:
                            days_left = (expiry - now).days
                            hours_left = (expiry - now).seconds // 3600
                            if days_left > 0:
                                expiry_str = f" ({days_left} ngày)"
                            else:
                                expiry_str = f" ({hours_left} giờ)"
                        else:
                            expiry_str = " (Hết hạn)"
                    except:
                        expiry_str = " (Lỗi date)"
                noi_dung += (
                    f"  🏆 {lien_ket_nguoi_dung}{expiry_str}\n     🆔 {user_id}\n\n"
                )
        if vip_only:
            noi_dung += "🌀 𝑽𝑰𝑷:\n\n"
            for vip in vip_only:
                user_id = vip[0]
                user_name = vip[1] if vip[1] else f"User_{str(user_id)[-4:]}"
                lien_ket_nguoi_dung = (
                    f'<a href="tg://user?id={user_id}">{escape_html(user_name)}</a>'
                )
                expiry_str = ""
                if vip[3]:
                    try:
                        expiry = datetime.fromisoformat(vip[3])
                        now = datetime.now()
                        if expiry > now:
                            days_left = (expiry - now).days
                            hours_left = (expiry - now).seconds // 3600
                            if days_left > 0:
                                expiry_str = f" ({days_left} ngày)"
                            else:
                                expiry_str = f" ({hours_left} giờ)"
                        else:
                            expiry_str = " (Hết hạn)"
                    except:
                        expiry_str = " (Lỗi date)"
                noi_dung += (
                    f"  🌀 {lien_ket_nguoi_dung}{expiry_str}\n     🆔 {user_id}\n\n"
                )
        noi_dung += f"Tổng: {len(super_vip_only)} Super VIP + {len(vip_only)} VIP = {len(vip_list)} Thành Viên"
        await gui_phan_hoi(
            message, noi_dung, xoa_tin_nguoi_dung=True, luu_vinh_vien=True
        )
        return True
    except Exception as e:
        await gui_phan_hoi(
            message,
            f"Lỗi khi lấy danh sách: {str(e)}",
            xoa_tin_nguoi_dung=True,
            tu_dong_xoa_sau_giay=10,
        )
        return False
async def xu_ly_tin_nhan_khong_phai_lenh(message: Message):
    try:
        if not message.from_user or message.from_user.is_bot:
            return
        if not message.text:
            return
        user_id = message.from_user.id
        if message.chat.id not in NHOM_CHO_PHEP:
            return
        asyncio.create_task(
            tu_dong_xoa_tin_nhan(message.chat.id, message.message_id, 0)
        )
        if message.text.startswith("/"):
            cac_lenh_hop_le = [
                "/sta",
                "/start",
                "/vip",
                "/gmail",
                "/checkid",
                "/call",
                "/callsuper",
                "/smscall",
                "/full",
                "/callfree",
                "/spam",
                "/ping",
                "/img",
                "/vid",
                "/themvip",
                "/xoavip",
                "/themadmin",
                "/xoaadmin",
                "/listvip",
                "/tiktok",
                "/ngl",
                "/cleanup",
                "/prx",
                "/free",
                "/invite",
                "/diem",
            ]
            lenh = message.text.split()[0].split("@")[0].lower()
            if lenh not in cac_lenh_hop_le and lenh not in ["/auto", "/addsuper"]:
                try:
                    phan_hoi = await bot.send_message(
                        chat_id=message.chat.id,
                        text="<blockquote>🐸𝐿𝑒̣̂𝑛ℎ 𝑘ℎ𝑜̂𝑛𝑔 ℎ𝑜̛̣𝑝 𝑙𝑒̣̂ !\n𝐺𝑜̃ /sta 𝑑𝑒̂̉ 𝑥𝑒𝑚 𝑑𝑎𝑛ℎ 𝑠𝑎́𝑐ℎ 𝑙𝑒̣̂𝑛ℎ ❗ </blockquote>",
                        parse_mode=ParseMode.HTML,
                    )
                    asyncio.create_task(
                        tu_dong_xoa_tin_nhan(phan_hoi.chat.id, phan_hoi.message_id, 5)
                    )
                except:
                    pass
    except Exception as e:
        logger.error(f"Lỗi xu_ly_tin_nhan_khong_phai_lenh: {e}")

async def xu_ly_callback_thu_supervip(callback: CallbackQuery):
    try:
        await callback.answer()
        if not callback.from_user or not callback.data:
            return
        user = callback.from_user
        user_id_nguoi_nhan = user.id
        # Chỉ cho phép đúng người nhận nút bấm
        phan = callback.data.split(":")
        if len(phan) < 2:
            return
        user_id_chu_so_huu = int(phan[1])
        so_ngay_thu = int(phan[2]) if len(phan) >= 3 else 1
        if user_id_nguoi_nhan != user_id_chu_so_huu:
            await callback.answer("⛔ Nút này không dành cho bạn !", show_alert=True)
            return
        if da_dung_thu_supervip(user_id_nguoi_nhan):
            so_ngay_hien_thi = f"{so_ngay_thu} ngày"
            await callback.answer(
                f"🐸 Bạn đã sử dụng trải nghiệm {so_ngay_hien_thi} rồi ! Liên hệ Admin để nâng cấp.",
                show_alert=True,
            )
            return
        ten = user.full_name or f"User {user_id_nguoi_nhan}"
        expiry = them_super_vip_thu(user_id_nguoi_nhan, ten, admin_added_by="auto_trial", days=so_ngay_thu)
        if not expiry:
            await callback.answer("☠ Có lỗi xảy ra, thử lại sau !", show_alert=True)
            return
        danh_dau_da_dung_thu_supervip(user_id_nguoi_nhan)
        lien_ket = dinh_dang_lien_ket_nguoi_dung(user)
        so_ngay_hien_thi = "𝟑 𝑛𝑔𝑎̀𝑦" if so_ngay_thu == 3 else "𝟏 𝑛𝑔𝑎̀𝑦"
        noi_dung_ok = (
            f"✨ {lien_ket}\n\n"
            f"🎉 𝐷𝑎̃ 𝑛𝑎̂𝑛𝑔 𝑐𝑎̂́𝑝 𝑙𝑒̂𝑛 𝐒𝐔𝐏𝐄𝐑 𝐕𝐈𝐏 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔 !\n\n"
            f"⏳ 𝐻𝑖𝑒̣̂𝑢 𝑙𝑢̛̣𝑐 :  {so_ngay_hien_thi}  ( ℎ𝑒̂́𝑡 ℎ𝑎̣𝑛 {expiry.strftime('%d/%m/%Y %H:%M')} )\n\n"
            f"🚀 𝑆𝑢̛̉ 𝑑𝑢̣𝑛𝑔 𝑙𝑒̣̂𝑛ℎ /callsuper đ𝑒̂̉ 𝑡𝑟𝑎̉𝑖 𝑛𝑔ℎ𝑖𝑒̣̂𝑚 𝑛𝑔𝑎𝑦 !"
        )
        try:
            if callback.message:
                await callback.message.edit_text(
                    f"<blockquote>{noi_dung_ok.strip()}</blockquote>",
                    parse_mode=ParseMode.HTML,
                )
                asyncio.create_task(
                    tu_dong_xoa_tin_nhan(
                        callback.message.chat.id, callback.message.message_id, 20
                    )
                )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Lỗi xu_ly_callback_thu_supervip: {e}")

async def xu_ly_start_rieng(message: Message):
    if not message.from_user:
        return False
    if message.chat.type != "private":
        return False
    payloads = trich_xuat_tham_so(message)
    payload = payloads[0].lower() if payloads else ""
    if payload in {"callfree", "free"}:
        await bot.send_message(
            chat_id=message.chat.id,
            text=(
                f"<blockquote>🤖 𝐶ℎ𝑎̀𝑜 {escape_html(message.from_user.full_name or 'bạn')} !\n\n"
                f"✅ 𝐵𝑎̣𝑛 đ𝑎̃ 𝑚𝑜̛̉ 𝑐ℎ𝑎𝑡 𝑟𝑖𝑒̂𝑛𝑔 𝑣𝑜̛́𝑖 𝐵𝑂𝑇.\n"
                f"📌 𝐿𝑒̣̂𝑛ℎ đ𝑢̛𝑜̛̣𝑐 𝑐ℎ𝑜̣𝑛 : /{payload}\n\n"
                f"💡 𝑉𝑢𝑖 𝑙𝑜̀𝑛𝑔 𝑔𝑢̛̉𝑖 𝑙𝑎̣𝑖 𝑙𝑒̣̂𝑛ℎ trong chat riêng để tiếp tục.</blockquote>"
            ),
            parse_mode=ParseMode.HTML,
        )
        return True
    await bot.send_message(
        chat_id=message.chat.id,
        text=f"<blockquote>🤖 𝐶ℎ𝑎̀𝑜 𝑏𝑎̣𝑛 !\n\n"
        f"𝐵𝑜𝑡 𝑛𝑎̀𝑦 ℎ𝑜𝑎̣𝑡 𝑑𝑜̣𝑛𝑔 𝑐ℎ𝑖̉ 𝑡𝑟𝑜𝑛𝑔 𝑛ℎ𝑜́𝑚 𝑏𝑒̂𝑛 𝑑𝑢̛𝑜̛́𝑖\n"
        f"𝐻𝑎̃𝑦 𝑣𝑎̀𝑜 𝑛ℎ𝑜́𝑚 𝑑𝑒̂̉ 𝑠𝑢̛̉ 𝑑𝑢̣𝑛𝑔 :\n\n"
        f"🏠 𝑁ℎ𝑜́𝑚  :  t.me/ditcuthangnaohacknhomtao\n\n"
        f"💡 𝐺𝑜̃ /sta 𝑡𝑟𝑜𝑛𝑔 𝑛ℎ𝑜́𝑚 𝑑𝑒̂̉ 𝑥𝑒𝑚 ℎ𝑢̛𝑜̛́𝑛𝑔 𝑑𝑎̂̃𝑛 !</blockquote>",
        parse_mode=ParseMode.HTML,
    )
    return True


# ====================== INVITE LINK SYSTEM ======================

INVITE_MILESTONES = {
    10: ("vip",       30, "🎁 𝑉𝐼𝑃 1 𝑡ℎ𝑎́𝑛𝑔"),
    25: ("super_vip", 30, "💎 𝑆𝑢𝑝𝑒𝑟 𝑉𝐼𝑃 1 𝑡ℎ𝑎́𝑛𝑔"),
    50: ("super_vip", 90, "🏆 𝑆𝑢𝑝𝑒𝑟 𝑉𝐼𝑃 3 𝑡ℎ𝑎́𝑛𝑔"),
}


def lay_so_lan_moi(user_id: str) -> int:
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute("SELECT count FROM invite_count WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row["count"] if row else 0
    except Exception:
        return 0


def dat_lai_so_lan_moi(user_id: str):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invite_count (user_id, count) VALUES (?, 0) "
            "ON CONFLICT(user_id) DO UPDATE SET count = 0, updated_at = CURRENT_TIMESTAMP",
            (user_id,),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def tang_so_lan_moi(user_id: str) -> int:
    """Tăng số lần mời 1 đơn vị, trả về số lần hiện tại sau khi tăng."""
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invite_count (user_id, count) VALUES (?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET count = count + 1, updated_at = CURRENT_TIMESTAMP",
            (user_id,),
        )
        cursor.execute("SELECT count FROM invite_count WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return row["count"] if row else 1
    except Exception:
        return 0


def ghi_nhan_moi(invited_user_id: str, inviter_user_id: str, group_id: int) -> bool:
    """Ghi nhận người được mời. Trả về True nếu chưa đếm trước đó."""
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO invite_log (invited_user_id, inviter_user_id, group_id) VALUES (?, ?, ?)",
            (invited_user_id, inviter_user_id, group_id),
        )
        added = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return added
    except Exception:
        return False


def luu_invite_link(user_id: str, group_id: int, invite_link: str):
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invite_links (user_id, group_id, invite_link) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, group_id) DO UPDATE SET invite_link = excluded.invite_link",
            (user_id, group_id, invite_link),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def lay_inviter_tu_link(invite_link_url: str):
    """Trả về (user_id, group_id) của người tạo link, hoặc (None, None)."""
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, group_id FROM invite_links WHERE invite_link = ?",
            (invite_link_url,),
        )
        row = cursor.fetchone()
        conn.close()
        return (row["user_id"], row["group_id"]) if row else (None, None)
    except Exception:
        return (None, None)


def cap_quyen_tu_invite(user_id: str, ten: str, role: str, days: int):
    """Cấp quyền và cập nhật cache."""
    try:
        expiry = datetime.now() + timedelta(days=days)
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO admin (user_id, name, role, expiry_date, admin_added_by) "
            "VALUES (?, ?, ?, ?, 'INVITE_SYSTEM')",
            (user_id, ten, role, expiry.isoformat()),
        )
        conn.commit()
        conn.close()
        quyen_cache.set(user_id, role)
        return expiry
    except Exception:
        return None


def tao_keyboard_invite_milestone(user_id: str, so_lan: int) -> InlineKeyboardMarkup:
    ms_hien_tai = max(m for m in INVITE_MILESTONES if m <= so_lan)
    _, _, label = INVITE_MILESTONES[ms_hien_tai]
    ms_tiep_theo = [m for m in sorted(INVITE_MILESTONES.keys()) if m > ms_hien_tai]
    buttons = [[
        InlineKeyboardButton(
            text=f"🎁 Nhận thưởng — {label}",
            callback_data=f"invite_nhan:{user_id}:{ms_hien_tai}",
        )
    ]]
    if ms_tiep_theo:
        next_ms = ms_tiep_theo[0]
        next_label = INVITE_MILESTONES[next_ms][2]
        buttons.append([
            InlineKeyboardButton(
                text=f"📈 Tiếp tục → {next_ms} người ({next_label})",
                callback_data=f"invite_tiep:{user_id}:{ms_hien_tai}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dinh_dang_tien_do_invite(so_lan: int) -> str:
    milestones = sorted(INVITE_MILESTONES.keys())
    next_ms = next((m for m in milestones if m > so_lan), None)
    if next_ms is None:
        return f"{'█' * 10} {so_lan}/{milestones[-1]} ✅ Tối đa!"
    prev_ms = max((m for m in milestones if m <= so_lan), default=0)
    pct = (so_lan - prev_ms) / (next_ms - prev_ms)
    filled = int(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {so_lan}/{next_ms} người"


@chi_nhom
@cooldown_decorator
async def xu_ly_invite(message: Message):
    """Lệnh /invite — tạo hoặc hiển thị link mời cá nhân."""
    if not message.from_user:
        return
    user = message.from_user
    user_id = str(user.id)
    group_id = message.chat.id

    # Lấy link đã có hoặc tạo mới
    try:
        conn = tao_ket_noi_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT invite_link FROM invite_links WHERE user_id = ? AND group_id = ?",
            (user_id, group_id),
        )
        row = cursor.fetchone()
        conn.close()
    except Exception:
        row = None

    if row:
        link = row["invite_link"]
    else:
        try:
            invite = await bot.create_chat_invite_link(
                chat_id=group_id,
                name=f"inv_{user_id}",
                creates_join_request=False,
            )
            link = invite.invite_link
            luu_invite_link(user_id, group_id, link)
        except Exception:
            await gui_phan_hoi(
                message,
                "☠ 𝐾ℎ𝑜̂𝑛𝑔 𝑡ℎ𝑒̂̉ 𝑡𝑎̣𝑜 𝑙𝑖𝑛𝑘. 𝐵𝑜𝑡 𝑐𝑎̂̀𝑛 𝑞𝑢𝑦𝑒̂̀𝑛 𝑞𝑢𝑎̉𝑛 𝑡𝑟𝑖̣ 𝑡𝑟𝑜𝑛𝑔 𝑛ℎ𝑜́𝑚 !",
                xoa_tin_nguoi_dung=True,
                tu_dong_xoa_sau_giay=10,
            )
            return

    so_lan = lay_so_lan_moi(user_id)
    tien_do = dinh_dang_tien_do_invite(so_lan)
    milestones_text = ""
    for ms, (_, __, label) in sorted(INVITE_MILESTONES.items()):
        icon = "✅" if so_lan >= ms else "⬜"
        milestones_text += f"  {icon} {ms} người → {label}\n"

    noi_dung = (
        f"🔗 𝐋𝐈𝐍𝐊 𝐌𝐎̛̀𝐈 𝐂𝐔̉𝐀 𝐁𝐀̣𝐍\n\n"
        f"🎰𝑇𝑖𝑒̂́𝑛 độ     :     {tien_do}\n"
        f"👥 Đ𝑎̃ 𝑚𝑜̛̀𝑖      :       {so_lan} 𝑛𝑔𝑢̛𝑜̛̀𝑖\n\n"
        f"🎯 𝑀𝑜̂́𝑐 𝑡ℎ𝑢̛𝑜̛̉𝑛𝑔   :\n{milestones_text}\n"
        f"🔗 𝐿𝑖𝑛𝑘 𝑐𝑢̉𝑎 𝑏𝑎̣𝑛 :\n"
        f'<a href="{escape_html(link)}">𝑁ℎ𝑎̂́𝑝 𝑣𝑎̀𝑜 đ𝑎̂𝑦 đ𝑒̂̉ 𝑚𝑜̛̉ 𝑙𝑖𝑛𝑘</a>\n\n'
        f"💡 𝑀𝑜̂̃𝑖 𝑛𝑔𝑢̛𝑜̛̀𝑖 𝑣𝑎̀𝑜 𝑛ℎ𝑜́𝑚 𝑞𝑢𝑎 𝑙𝑖𝑛𝑘 𝑛𝑎̀𝑦 = +1 đ𝑖𝑒̂̉𝑚 !"
    )

    # Hiển thị nút nhận thưởng nếu đã đạt milestone
    dat_milestone = [m for m in INVITE_MILESTONES if so_lan >= m]
    keyboard = tao_keyboard_invite_milestone(user_id, so_lan) if dat_milestone else None
    await gui_phan_hoi(
        message, noi_dung,
        xoa_tin_nguoi_dung=True, luu_vinh_vien=True,
        reply_markup=keyboard,
    )
    return True


@chi_nhom
async def xu_ly_diem_moi(message: Message):
    if not message.from_user:
        return
    user = message.from_user
    user_id = str(user.id)

    so_lan = lay_so_lan_moi(user_id)
    tien_do = dinh_dang_tien_do_invite(so_lan)
    milestones_text = ""
    for ms, (_, __, label) in sorted(INVITE_MILESTONES.items()):
        icon = "✅" if so_lan >= ms else "⬜"
        milestones_text += f"  {icon} {ms} người → {label}\n"

    noi_dung = (
        f"🏅 𝐃𝐈𝐄̂̉𝐌 𝐌𝐎̛̀𝐈 — {dinh_dang_lien_ket_nguoi_dung(user)}\n\n"
        f"🎰𝑇𝑖𝑒̂́𝑛 độ   :  {tien_do}\n"
        f"👥 Đ𝑎̃ 𝑚𝑜̛̀𝑖   :  {so_lan} 𝑛𝑔𝑢̛𝑜̛̀𝑖\n\n"
        f"🎯 𝑀𝑜̂́𝑐 𝑡ℎ𝑢̛𝑜̛̉𝑛𝑔 :\n{milestones_text}"
    )

    dat_milestone = [m for m in INVITE_MILESTONES if so_lan >= m]
    keyboard = tao_keyboard_invite_milestone(user_id, so_lan) if dat_milestone else None
    await gui_phan_hoi(
        message, noi_dung,
        xoa_tin_nguoi_dung=True, luu_vinh_vien=True,
        reply_markup=keyboard,
    )


async def xu_ly_thanh_vien_moi_qua_link(event: ChatMemberUpdated):
    try:
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        # Chỉ xử lý khi chuyển từ ngoài → trong nhóm
        if new_status not in ("member", "administrator", "creator"):
            return
        if old_status in ("member", "administrator", "creator"):
            return

        if event.chat.id not in NHOM_CHO_PHEP:
            return

        if not event.invite_link:
            return

        invite_link_url = event.invite_link.invite_link
        invited_user = event.new_chat_member.user

        if invited_user.is_bot:
            return

        invited_user_id = str(invited_user.id)
        group_id = event.chat.id

        inviter_id, _ = await asyncio.to_thread(lay_inviter_tu_link, invite_link_url)
        if not inviter_id:
            return
        if inviter_id == invited_user_id:
            return  # Không tự mời bản thân

        # Ghi nhận (mỗi người chỉ tính 1 lần dù vào/ra nhiều lần)
        added = await asyncio.to_thread(ghi_nhan_moi, invited_user_id, inviter_id, group_id)
        if not added:
            return

        so_lan = await asyncio.to_thread(tang_so_lan_moi, inviter_id)

        # Kiểm tra milestone
        if so_lan in INVITE_MILESTONES:
            _, _, label = INVITE_MILESTONES[so_lan]
            keyboard = tao_keyboard_invite_milestone(inviter_id, so_lan)
            ms_list = sorted(INVITE_MILESTONES.keys())
            next_ms_list = [m for m in ms_list if m > so_lan]
            if next_ms_list:
                next_label = INVITE_MILESTONES[next_ms_list[0]][2]
                extra = f"\n📈 𝑀𝑢𝑜̂́𝑛 𝑛ℎ𝑎̣̂𝑛 {next_label} ? 𝑇𝑖𝑒̂́𝑝 𝑡𝑢̣𝑐 𝑚𝑜̛̀𝑖 {next_ms_list[0]} 𝑛𝑔𝑢̛𝑜̛̀𝑖 !"
            else:
                extra = "\n🏆 Đ𝑎̂𝑦 𝑙𝑎̀ 𝑝ℎ𝑎̂̀𝑛 𝑡ℎ𝑢̛𝑜̛̉𝑛𝑔 𝑐𝑎𝑜 𝑛ℎ𝑎̂́𝑡 — 𝑁ℎ𝑎̣̂𝑛 𝑛𝑔𝑎𝑦 𝑡ℎ𝑜̂𝑖 !"
            thong_bao = (
                f"🎉 <a href='tg://user?id={inviter_id}'>𝐶ℎ𝑢́𝑐 𝑚𝑢̛̀𝑛𝑔 !</a>\n\n"
                f"🔥 𝐵𝑎̣𝑛 đ𝑎̃ 𝑚𝑜̛̀𝑖 <b>{so_lan}</b> 𝑡ℎ𝑎̀𝑛ℎ 𝑣𝑖𝑒̂𝑛 𝑡ℎ𝑎𝑚 𝑔𝑖𝑎 𝑛ℎ𝑜́𝑚 !\n"
                f"🎁 𝑃ℎ𝑎̂̀𝑛 𝑡ℎ𝑢̛𝑜̛̉𝑛𝑔 đ𝑎𝑛𝑔 𝑐ℎ𝑜̛̀ 𝑏𝑎̣𝑛 : <b>{label}</b>{extra}\n\n"
                f"👇 𝐶ℎ𝑜̣𝑛 ℎ𝑎̀𝑛ℎ đ𝑜̣̂𝑛𝑔 :"
            )
            await bot.send_message(
                chat_id=group_id,
                text=f"<blockquote>{thong_bao}</blockquote>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.error(f"Lỗi xu_ly_thanh_vien_moi_qua_link: {e}")


async def xu_ly_nhan_thuong_invite(callback: CallbackQuery):
    try:
        await callback.answer()
        if not callback.from_user or not callback.data:
            return
        phan = callback.data.split(":")
        if len(phan) < 3:
            return
        user_id_chu = phan[1]
        milestone = int(phan[2])
        user_id_bam = str(callback.from_user.id)

        if user_id_bam != user_id_chu:
            await callback.answer("☠ 𝑁𝑢́𝑡 𝑛𝑎̀𝑦 𝑘ℎ𝑜̂𝑛𝑔 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑏𝑎̣𝑛 !", show_alert=True)
            return

        so_lan = lay_so_lan_moi(user_id_chu)
        if so_lan < milestone:
            await callback.answer("☠ 𝑆𝑜̂́ đ𝑖𝑒̂̉𝑚 𝑘ℎ𝑜̂𝑛𝑔 đ𝑢̉ !", show_alert=True)
            return

        if milestone not in INVITE_MILESTONES:
            return

        role, days, label = INVITE_MILESTONES[milestone]
        ten = callback.from_user.full_name or f"User_{user_id_chu[-4:]}"

        expiry = cap_quyen_tu_invite(user_id_chu, ten, role, days)
        if not expiry:
            await callback.answer("☠ 𝐿𝑜̂̃𝑖 𝑐𝑎̂́𝑝 𝑞𝑢𝑦𝑒̂̀𝑛, 𝑡ℎ𝑢̛̉ 𝑙𝑎̣𝑖 𝑠𝑎𝑢 !", show_alert=True)
            return

        dat_lai_so_lan_moi(user_id_chu)
        lien_ket = f'<a href="tg://user?id={user_id_chu}">{escape_html(ten)}</a>'

        try:
            if callback.message:
                await callback.message.edit_text(
                    f"<blockquote>✅ {lien_ket} đ𝑎̃ 𝑛ℎ𝑎̣̂𝑛 𝑡ℎ𝑢̛𝑜̛̉𝑛𝑔 𝑡ℎ𝑎̀𝑛ℎ 𝑐𝑜̂𝑛𝑔 !\n\n"
                    f"🏆 𝑄𝑢𝑦𝑒̂̀𝑛        :  {label}\n"
                    f"⏳ 𝐻𝑖𝑒̣̂𝑢 𝑙𝑢̛̣𝑐   :  {days} 𝑛𝑔𝑎̀𝑦\n"
                    f"📅 𝐻𝑒̂́𝑡 ℎ𝑎̣𝑛      :  {expiry.strftime('%d/%m/%Y')}\n\n"
                    f"🔄 Đ𝑖𝑒̂̉𝑚 𝑚𝑜̛̀𝑖 đ𝑎̃ 𝑟𝑒𝑠𝑒𝑡 𝑣𝑒̂̀ 0 — 𝑏𝑎̆́𝑡 đ𝑎̂̀𝑢 𝑐ℎ𝑢 𝑘𝑦̀ 𝑚𝑜̛́𝑖 !</blockquote>",
                    parse_mode=ParseMode.HTML,
                )
                asyncio.create_task(
                    tu_dong_xoa_tin_nhan(
                        callback.message.chat.id, callback.message.message_id, 20
                    )
                )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Lỗi xu_ly_nhan_thuong_invite: {e}")


async def xu_ly_tiep_tuc_invite(callback: CallbackQuery):
    try:
        await callback.answer()
        if not callback.from_user or not callback.data:
            return
        phan = callback.data.split(":")
        if len(phan) < 3:
            return
        user_id_chu = phan[1]
        milestone_da_dat = int(phan[2])
        user_id_bam = str(callback.from_user.id)

        if user_id_bam != user_id_chu:
            await callback.answer("☠ 𝑁𝑢́𝑡 𝑛𝑎̀𝑦 𝑘ℎ𝑜̂𝑛𝑔 𝑑𝑎̀𝑛ℎ 𝑐ℎ𝑜 𝑏𝑎̣𝑛 !", show_alert=True)
            return

        ms_list = sorted(INVITE_MILESTONES.keys())
        next_ms_list = [m for m in ms_list if m > milestone_da_dat]
        if not next_ms_list:
            await callback.answer("🏆 Đây là phần thưởng cao nhất, hãy nhận ngay!", show_alert=True)
            return

        next_ms = next_ms_list[0]
        _, _, next_label = INVITE_MILESTONES[next_ms]
        so_lan_hien_tai = lay_so_lan_moi(user_id_chu)
        can_them = next_ms - so_lan_hien_tai

        try:
            if callback.message:
                await callback.message.edit_text(
                    f"<blockquote>📈 𝑇𝑖𝑒̂́𝑝 𝑡𝑢̣𝑐 𝑡𝑖́𝑐ℎ đ𝑖𝑒̂̉𝑚 !\n\n"
                    f"🎰𝐻𝑖𝑒̣̂𝑛 𝑡𝑎̣𝑖   :  {so_lan_hien_tai} 𝑛𝑔𝑢̛𝑜̛̀𝑖\n"
                    f"🎯 𝑀𝑢̣𝑐 𝑡𝑖𝑒̂𝑢   :  {next_ms} 𝑛𝑔𝑢̛𝑜̛̀𝑖 → {next_label}\n"
                    f"📌 𝐶𝑎̂̀𝑛 𝑡ℎ𝑒̂𝑚   :  {can_them} 𝑛𝑔𝑢̛𝑜̛̀𝑖 𝑛𝑢̛̃𝑎 !\n\n"
                    f"🔗 𝐺𝑜̃ /invite đ𝑒̂̉ 𝑙𝑎̂́𝑦 𝑙𝑖𝑛𝑘 𝑚𝑜̛̀𝑖 !</blockquote>",
                    parse_mode=ParseMode.HTML,
                )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Lỗi xu_ly_tiep_tuc_invite: {e}")


def create_router():
    router = Router()
    router.message.register(
        xu_ly_start_rieng, Command("start")
    )  
    router.message.register(xu_ly_sta, Command("sta"))
    router.message.register(xu_ly_ping, Command("ping"))
    router.message.register(xu_ly_auto, Command("auto"))
    router.message.register(xu_ly_addsuper, Command("addsuper"))
    router.message.register(xu_ly_callfree, Command("callfree"))
    router.message.register(xu_ly_spam, Command("spam"))
    router.message.register(xu_ly_free, Command("free"))
    router.message.register(xu_ly_vip, Command("vip"))
    router.message.register(xu_ly_call, Command("call"))
    router.message.register(xu_ly_callsuper, Command("callsuper"))
    router.message.register(xu_ly_smscall, Command("smscall"))
    router.message.register(xu_ly_full, Command("full"))
    router.message.register(xu_ly_gmail, Command("gmail"))
    router.message.register(xu_ly_tiktok, Command("tiktok"))
    router.message.register(xu_ly_ngl, Command("ngl"))
    router.message.register(xu_ly_checkid, Command("checkid"))
    router.message.register(xu_ly_them_vip, Command("themvip"))
    router.message.register(xu_ly_random_anh, Command("img"))
    router.message.register(xu_ly_xoa_vip, Command("xoavip"))
    router.message.register(xu_ly_random_video, Command("vid"))
    router.message.register(xu_ly_them_admin, Command("themadmin"))
    router.message.register(xu_ly_xoa_admin, Command("xoaadmin"))
    router.message.register(xu_ly_xem_danh_sach_vip, Command("listvip"))
    router.message.register(xu_ly_cleanup, Command("cleanup"))
    router.message.register(xu_ly_prx, Command("prx"))
    router.message.register(xu_ly_spamtele, Command("spamtele"))
    router.message.register(xu_ly_invite, Command("invite"))
    router.message.register(xu_ly_diem_moi, Command("diem"))
    router.callback_query.register(
        xu_ly_callback_thu_supervip, F.data.startswith("thu_supervip:")
    )
    router.callback_query.register(
        xu_ly_nhan_thuong_invite, F.data.startswith("invite_nhan:")
    )
    router.callback_query.register(
        xu_ly_tiep_tuc_invite, F.data.startswith("invite_tiep:")
    )
    router.chat_member.register(xu_ly_thanh_vien_moi_qua_link)
    router.message.register(xu_ly_tin_nhan_khong_phai_lenh)
    return router
async def main():
    try:
        khoi_tao_database()
        khoi_tao_admin_mac_dinh()
        dp = Dispatcher()
        router = create_router()
        dp.include_router(router)
        try:
            bot_info = await bot.get_me()
            global BOT_USERNAME
            BOT_USERNAME = bot_info.username
        except Exception as e:
            raise
        cleanup_task = asyncio.create_task(schedule_cleanup())
        vip_check_task = asyncio.create_task(kiem_tra_vip_het_han())
        try:
            await dp.start_polling(
                bot,
                drop_pending_updates=True,
                polling_timeout=30,
                allowed_updates=["message", "callback_query", "chat_member"],
            )
        finally:
            cleanup_task.cancel()
            vip_check_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            try:
                await vip_check_task
            except asyncio.CancelledError:
                pass
    except Exception as e:
        cleanup_dead_processes()
        raise
    finally:
        cleanup_dead_processes()
        try:
            await bot.session.close()
        except Exception as e:
            logger.warning(f"Không thể đóng phiên HTTP của bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup_dead_processes()
    except Exception as e:
        cleanup_dead_processes()
