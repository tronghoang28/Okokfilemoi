import asyncio
import os
import sys
import sqlite3
import time
import random
import logging
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup,
)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("SHOPEE_BOT_TOKEN", "7605235504:AAGzGnTP55IDsovFlCojatS9u0gLwvAKOQ8")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "5365031415")   # comma-separated Telegram user IDs
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
MIN_NAME_LEN = 3           # min chars user must type to pass name check
USES_PER_VERIFY = 1        # how many commands per verification (change to 2, 3... for more uses per click)
DB_PATH = "./data/shopee_bot.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── DB SETUP ────────────────────────────────────────────────────────────────
os.makedirs("./data", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            url      TEXT NOT NULL,
            name     TEXT NOT NULL,
            active   INTEGER DEFAULT 1,
            added_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS verifications (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            verified_at TEXT,
            expires_at  TEXT,
            uses_left   INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id  INTEGER PRIMARY KEY,
            username TEXT
        );
        CREATE TABLE IF NOT EXISTS pending (
            user_id    INTEGER PRIMARY KEY,
            product_id INTEGER,
            sent_at    TEXT
        );
        """)
        conn.commit()

init_db()

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def now_vn():
    return datetime.now(VN_TZ)

def is_admin(user_id: int) -> bool:
    # Check env-configured admins
    if ADMIN_IDS_STR:
        for uid in ADMIN_IDS_STR.split(","):
            if uid.strip() == str(user_id):
                return True
    # Check DB admins
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
        return row is not None

def is_verified(user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT uses_left FROM verifications WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            return False
        return (row["uses_left"] or 0) > 0

def remaining_uses(user_id: int) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT uses_left FROM verifications WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            return 0
        return row["uses_left"] or 0

def use_one_command(user_id: int):
    """Decrement uses_left by 1 after a command is used."""
    with get_db() as conn:
        conn.execute(
            "UPDATE verifications SET uses_left = MAX(0, uses_left - 1) WHERE user_id=?",
            (user_id,)
        )
        conn.commit()

def mark_verified(user_id: int, username: str):
    now = datetime.utcnow()
    expires = now + timedelta(days=30)  # kept for record-keeping only; access is controlled by uses_left
    with get_db() as conn:
        conn.execute("""
            INSERT INTO verifications (user_id, username, verified_at, expires_at, uses_left)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                verified_at=excluded.verified_at,
                expires_at=excluded.expires_at,
                uses_left=excluded.uses_left
        """, (user_id, username or "", now.isoformat(), expires.isoformat(), USES_PER_VERIFY))
        conn.commit()

def get_random_product():
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE active=1 ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

def set_pending(user_id: int, product_id: int):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO pending (user_id, product_id, sent_at)
            VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET product_id=excluded.product_id, sent_at=excluded.sent_at
        """, (user_id, product_id, datetime.utcnow().isoformat()))
        conn.commit()

def get_pending(user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT p.*, pr.name as product_name FROM pending p "
            "JOIN products pr ON pr.id=p.product_id WHERE p.user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

def clear_pending(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM pending WHERE user_id=?", (user_id,))
        conn.commit()

def fuzzy_match(user_input: str, product_name: str) -> bool:
    """Accept if user typed at least MIN_NAME_LEN chars that appear in product name."""
    user_input = user_input.strip().lower()
    product_name = product_name.lower()
    if len(user_input) < MIN_NAME_LEN:
        return False
    # Check if user_input words appear in product_name
    words = user_input.split()
    matches = sum(1 for w in words if w in product_name)
    return matches >= max(1, len(words) // 2) or user_input[:MIN_NAME_LEN] in product_name

# ─── ROUTER ──────────────────────────────────────────────────────────────────
router = Router()

# ─── /start ──────────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message):
    user = msg.from_user
    if is_verified(user.id):
        uses = remaining_uses(user.id)
        await msg.answer(
            f"✅ Bạn đã xác nhận rồi!\n"
            f"🎯 Lượt dùng còn lại: <b>{uses} lượt</b>\n\n"
            f"Dùng /lenh để xem các lệnh có sẵn.",
            parse_mode=ParseMode.HTML
        )
        return

    product = get_random_product()
    if not product:
        await msg.answer(
            "⚠️ Chưa có link sản phẩm nào. Admin vui lòng dùng /addlink để thêm.",
        )
        return

    set_pending(user.id, product["id"])
    btn = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Click vào link Shopee này", url=product["url"])
    ]])
    await msg.answer(
        "👋 Chào mừng bạn!\n\n"
        "Để dùng bot, bạn cần xác nhận bằng cách:\n\n"
        "1️⃣ <b>Click vào link bên dưới</b> để xem sản phẩm Shopee\n"
        "2️⃣ <b>Gửi tên sản phẩm</b> bạn thấy khi vào link (gõ /xacnhan [tên sp])\n\n"
        "Ví dụ: <code>/xacnhan Áo thun nam</code>\n\n"
        "🎯 Xác nhận 1 lần = dùng được <b>1 lệnh</b>. Muốn dùng thêm thì click link lần nữa!",
        parse_mode=ParseMode.HTML,
        reply_markup=btn
    )

# ─── /xacnhan ────────────────────────────────────────────────────────────────
@router.message(Command("xacnhan"))
async def cmd_xacnhan(msg: Message):
    user = msg.from_user

    if is_verified(user.id):
        uses = remaining_uses(user.id)
        await msg.answer(f"✅ Bạn đã xác nhận rồi! Còn <b>{uses} lượt</b> dùng lệnh.", parse_mode=ParseMode.HTML)
        return

    pending = get_pending(user.id)
    if not pending:
        await msg.answer("⚠️ Hãy dùng /start trước để nhận link sản phẩm.")
        return

    # Get what user typed after /xacnhan
    args = msg.text.split(maxsplit=1)
    if len(args) < 2 or len(args[1].strip()) < MIN_NAME_LEN:
        await msg.answer(
            f"❌ Vui lòng gõ tên sản phẩm sau lệnh.\n"
            f"Ví dụ: <code>/xacnhan Áo thun nam</code>",
            parse_mode=ParseMode.HTML
        )
        return

    user_input = args[1].strip()
    product_name = pending["product_name"]

    if fuzzy_match(user_input, product_name):
        mark_verified(user.id, user.username)
        clear_pending(user.id)
        await msg.answer(
            f"🎉 Xác nhận thành công! Bạn có <b>{USES_PER_VERIFY} lượt</b> dùng lệnh.\n\n"
            f"Dùng /lenh để xem các lệnh.",
            parse_mode=ParseMode.HTML
        )
    else:
        # Be lenient - if they typed something reasonable, accept it
        # (we can't truly verify what they see on Shopee)
        if len(user_input) >= MIN_NAME_LEN:
            mark_verified(user.id, user.username)
            clear_pending(user.id)
            await msg.answer(
                f"🎉 Xác nhận thành công! Bạn có <b>{USES_PER_VERIFY} lượt</b> dùng lệnh.\n\n"
                f"Dùng /lenh để xem các lệnh.",
                parse_mode=ParseMode.HTML
            )
        else:
            await msg.answer(
                f"❌ Tên sản phẩm quá ngắn. Hãy click vào link Shopee và gõ tên sản phẩm bạn thấy.\n"
                f"Dùng /start để nhận lại link.",
                parse_mode=ParseMode.HTML
            )

# ─── /thoigian ───────────────────────────────────────────────────────────────
@router.message(Command("thoigian"))
async def cmd_thoigian(msg: Message):
    uses = remaining_uses(msg.from_user.id)
    if uses > 0:
        await msg.answer(f"🎯 Lượt dùng lệnh còn lại: <b>{uses} lượt</b>", parse_mode=ParseMode.HTML)
    else:
        await msg.answer("❌ Bạn chưa xác nhận hoặc đã hết lượt. Dùng /start để nhận link mới.", parse_mode=ParseMode.HTML)

# ─── /lenh (help) — chỉ hiện lệnh người dùng, ẩn admin ──────────────────────
@router.message(Command("lenh"))
async def cmd_help(msg: Message):
    uses = remaining_uses(msg.from_user.id)
    status_line = (
        f"🎯 Lượt còn lại: <b>{uses} lượt</b>"
        if uses > 0
        else "❌ Chưa xác nhận — dùng /start để nhận link"
    )
    text = (
        "📋 <b>Danh sách lệnh:</b>\n\n"
        f"{status_line}\n\n"
        "/start — Nhận link xác nhận\n"
        "/xacnhan — Xác nhận đã click link\n"
        "/thoigian — Kiểm tra lượt còn lại\n"
        "/call — 📞 Cuộc gọi miễn phí\n"
        "/sms — 💬 Tin nhắn miễn phí\n"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)

# ─── /call ───────────────────────────────────────────────────────────────────
@router.message(Command("call"))
async def cmd_call(msg: Message):
    if not await require_verify(msg):
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.answer(
            "📞 <b>Cuộc gọi miễn phí</b>\n\n"
            "Cú pháp: <code>/call [số điện thoại]</code>\n"
            "Ví dụ: <code>/call 0987654321</code>",
            parse_mode=ParseMode.HTML
        )
        return

    phone = parts[1].strip().replace(" ", "").replace("-", "")
    if not (phone.isdigit() and len(phone) == 10 and phone.startswith("0")):
        await msg.answer(
            "❌ Số điện thoại không hợp lệ!\n"
            "Phải là số 10 chữ số bắt đầu bằng 0.\n"
            "Ví dụ: <code>0987654321</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # Trừ 1 lượt trước khi gọi
    use_one_command(msg.from_user.id)
    uses_left = remaining_uses(msg.from_user.id)

    wait_msg = await msg.answer(
        f"📞 Đang thực hiện cuộc gọi tới <b>{phone}</b>...\n⏳ Vui lòng chờ.",
        parse_mode=ParseMode.HTML
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "goiconcac.py", phone,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        output = stdout.decode("utf-8", errors="replace").strip()
        err    = stderr.decode("utf-8", errors="replace").strip()
        combined = output or err or "✅ Đã gửi lệnh gọi thành công!"

        await wait_msg.edit_text(
            f"📞 <b>Kết quả gọi tới {phone}:</b>\n\n"
            f"{combined}\n\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )
    except asyncio.TimeoutError:
        await wait_msg.edit_text(
            f"⏱ Quá thời gian chờ khi gọi tới <b>{phone}</b>.\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.exception("cmd_call error")
        await wait_msg.edit_text(
            f"❌ Lỗi hệ thống: {e}\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )

# ─── /sms ────────────────────────────────────────────────────────────────────
@router.message(Command("sms"))
async def cmd_sms(msg: Message):
    if not await require_verify(msg):
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.answer(
            "💬 <b>Tin nhắn miễn phí</b>\n\n"
            "Cú pháp: <code>/sms [số điện thoại]</code>\n"
            "Ví dụ: <code>/sms 0987654321</code>",
            parse_mode=ParseMode.HTML
        )
        return

    phone = parts[1].strip().replace(" ", "").replace("-", "")
    if not (phone.isdigit() and len(phone) == 10 and phone.startswith("0")):
        await msg.answer(
            "❌ Số điện thoại không hợp lệ!\n"
            "Phải là số 10 chữ số bắt đầu bằng 0.\n"
            "Ví dụ: <code>0987654321</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # Trừ 1 lượt trước khi gửi
    use_one_command(msg.from_user.id)
    uses_left = remaining_uses(msg.from_user.id)

    wait_msg = await msg.answer(
        f"💬 Đang gửi tin nhắn tới <b>{phone}</b>...\n⏳ Vui lòng chờ.",
        parse_mode=ParseMode.HTML
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "goiconcac2.py", phone,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
        output = stdout.decode("utf-8", errors="replace").strip()
        err    = stderr.decode("utf-8", errors="replace").strip()
        combined = output or err or "✅ Đã gửi tin nhắn thành công!"

        await wait_msg.edit_text(
            f"💬 <b>Kết quả gửi SMS tới {phone}:</b>\n\n"
            f"{combined}\n\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )
    except asyncio.TimeoutError:
        await wait_msg.edit_text(
            f"⏱ Quá thời gian chờ khi gửi SMS tới <b>{phone}</b>.\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.exception("cmd_sms error")
        await wait_msg.edit_text(
            f"❌ Lỗi hệ thống: {e}\n"
            f"🎯 Lượt còn lại: <b>{uses_left}</b>",
            parse_mode=ParseMode.HTML
        )

# ─── Shared gate helper ──────────────────────────────────────────────────────
async def require_verify(msg: Message) -> bool:
    """Returns True if user is verified and has uses left. Sends prompt if not."""
    user_id = msg.from_user.id
    if not is_verified(user_id):
        product = get_random_product()
        if product:
            set_pending(user_id, product["id"])
            btn = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🛒 Click vào link Shopee", url=product["url"])
            ]])
            await msg.answer(
                "🔒 Bạn cần xác nhận trước!\n\n"
                "1️⃣ Click vào link Shopee bên dưới\n"
                "2️⃣ Gõ: <code>/xacnhan [tên sản phẩm]</code>\n"
                "🎯 Mỗi lần click = 1 lượt dùng lệnh",
                parse_mode=ParseMode.HTML,
                reply_markup=btn
            )
        else:
            await msg.answer("🔒 Bạn cần xác nhận trước! Dùng /start để bắt đầu.")
        return False
    return True

# ─── ADMIN: /addlink ─────────────────────────────────────────────────────────
@router.message(Command("addlink"))
async def cmd_addlink(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer(
            "❌ Cú pháp: <code>/addlink [url] [tên sản phẩm]</code>\n"
            "Ví dụ: <code>/addlink https://shopee.vn/... Áo thun nam form rộng</code>",
            parse_mode=ParseMode.HTML
        )
        return
    url, name = parts[1], parts[2]
    with get_db() as conn:
        cur = conn.execute("INSERT INTO products (url, name) VALUES (?,?)", (url, name))
        conn.commit()
        pid = cur.lastrowid
    await msg.answer(f"✅ Đã thêm sản phẩm ID <b>{pid}</b>: {name}", parse_mode=ParseMode.HTML)

# ─── ADMIN: /removelink ──────────────────────────────────────────────────────
@router.message(Command("removelink"))
async def cmd_removelink(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("❌ Cú pháp: <code>/removelink [id]</code>", parse_mode=ParseMode.HTML)
        return
    pid = int(parts[1])
    with get_db() as conn:
        conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
        conn.commit()
    await msg.answer(f"✅ Đã xóa link ID <b>{pid}</b>.", parse_mode=ParseMode.HTML)

# ─── ADMIN: /listlinks ───────────────────────────────────────────────────────
@router.message(Command("listlinks"))
async def cmd_listlinks(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, url, active FROM products ORDER BY id DESC LIMIT 20"
        ).fetchall()
    if not rows:
        await msg.answer("📭 Chưa có link nào.")
        return
    lines = []
    for r in rows:
        status = "✅" if r["active"] else "❌"
        lines.append(f"{status} <b>ID {r['id']}</b>: {r['name']}\n<code>{r['url'][:60]}...</code>")
    await msg.answer("\n\n".join(lines), parse_mode=ParseMode.HTML)

# ─── ADMIN: /addadmin ────────────────────────────────────────────────────────
@router.message(Command("addadmin"))
async def cmd_addadmin(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("❌ Cú pháp: <code>/addadmin [user_id]</code>", parse_mode=ParseMode.HTML)
        return
    new_admin_id = int(parts[1])
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO admins (user_id) VALUES (?)", (new_admin_id,)
        )
        conn.commit()
    await msg.answer(f"✅ Đã thêm admin ID <b>{new_admin_id}</b>.", parse_mode=ParseMode.HTML)

# ─── ADMIN: /thongke ─────────────────────────────────────────────────────────
@router.message(Command("thongke"))
async def cmd_thongke(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    with get_db() as conn:
        total_products = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        total_verified = conn.execute(
            "SELECT COUNT(*) FROM verifications WHERE uses_left > 0"
        ).fetchone()[0]
        total_all_time = conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]
    await msg.answer(
        f"📊 <b>Thống kê bot:</b>\n\n"
        f"🔗 Link sản phẩm đang dùng: <b>{total_products}</b>\n"
        f"✅ User còn lượt dùng: <b>{total_verified}</b>\n"
        f"👥 Tổng user đã xác nhận: <b>{total_all_time}</b>",
        parse_mode=ParseMode.HTML
    )

# ─── ADMIN: /layflashsale ────────────────────────────────────────────────────
SHOPEE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/537.36",
    "referer": "https://shopee.vn/",
}

async def fetch_flash_sale_items(limit: int = 15) -> list:
    """Fetch current flash sale items from Shopee public API."""
    import re
    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: get current session
            async with session.get(
                "https://shopee.vn/api/v4/flash_sale/get_all_sessions",
                headers=SHOPEE_HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json(content_type=None)
            sessions = data.get("data", {}).get("sessions", [])
            if not sessions:
                return []
            promotionid = sessions[0]["promotionid"]

            # Step 2: get items in that session
            async with session.get(
                f"https://shopee.vn/api/v4/flash_sale/flash_sale_get_items"
                f"?promotionid={promotionid}&categoryid=0&sort_soldout=true&limit={limit}&offset=0",
                headers=SHOPEE_HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json(content_type=None)

        items = data.get("data", {}).get("items", [])
        results = []
        for item in items:
            name = item.get("name", "Sản phẩm Shopee")
            shopid = item.get("shopid")
            itemid = item.get("itemid")
            discount = item.get("discount", "")
            price_raw = item.get("price", 0)
            price = int(price_raw) // 100000  # convert to VND (prices are * 100000)
            # Build slug from name (basic)
            slug = re.sub(r'[^\w\s-]', '', name.lower())
            slug = re.sub(r'\s+', '-', slug.strip())[:50]
            url = f"https://shopee.vn/{slug}-i.{shopid}.{itemid}"
            results.append({
                "name": name,
                "url": url,
                "discount": discount,
                "price": price,
            })
        return results
    except Exception as e:
        logger.error(f"fetch_flash_sale_items error: {e}")
        return []

@router.message(Command("layflashsale"))
async def cmd_layflashsale(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return

    await msg.answer("⏳ Đang lấy flash sale từ Shopee...")
    items = await fetch_flash_sale_items(limit=15)
    if not items:
        await msg.answer("⚠️ Không lấy được flash sale lúc này. Thử lại sau.")
        return

    # Group into batches of 5 (matches Shopee's convert tool limit)
    batch_size = 5
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]

    await msg.answer(
        f"✅ Lấy được <b>{len(items)} sản phẩm</b> flash sale — chia thành {len(batches)} nhóm.\n\n"
        f"👇 Copy từng nhóm link → dán vào <b>Chuyển đổi liên kết</b> → convert → dùng /addlink",
        parse_mode=ParseMode.HTML
    )

    for i, batch in enumerate(batches, 1):
        # List product names
        names_text = "\n".join(
            f"  {j+1}. {p['name'][:45]}... ({p['discount']})" if len(p['name']) > 45
            else f"  {j+1}. {p['name']} ({p['discount']})"
            for j, p in enumerate(batch)
        )
        # Raw links ready to copy-paste into Shopee app
        links_text = "\n".join(p["url"] for p in batch)

        await msg.answer(
            f"📦 <b>Nhóm {i}/{len(batches)}:</b>\n{names_text}\n\n"
            f"📋 <b>Dán 5 link này vào Chuyển đổi liên kết:</b>\n"
            f"<code>{links_text}</code>",
            parse_mode=ParseMode.HTML
        )

# ─── ADMIN: /broadcast ───────────────────────────────────────────────────────
@router.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("❌ Bạn không có quyền admin.")
        return
    product = get_random_product()
    if not product:
        await msg.answer("⚠️ Chưa có link nào để broadcast.")
        return
    btn = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Xem sản phẩm Shopee", url=product["url"])
    ]])
    await msg.answer(
        f"🔥 <b>Deal hôm nay!</b>\n\n"
        f"🛍️ {product['name']}\n\n"
        f"👆 Click vào link để xem giá & mua ngay!\n"
        f"💡 Dùng /start để mở khóa lệnh bot sau khi xem.",
        parse_mode=ParseMode.HTML,
        reply_markup=btn
    )

# ─── MAIN ────────────────────────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        logger.error("SHOPEE_BOT_TOKEN chưa được set! Đặt biến môi trường SHOPEE_BOT_TOKEN.")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot Shopee Affiliate đang chạy...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
