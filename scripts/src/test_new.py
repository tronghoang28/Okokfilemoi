"""
Test tien24h_sms trước khi thêm vào main.py.

Bước 1 — lấy AppCheck JWT (chỉ cần 1 lần, valid 1 giờ):
    python tien24h_appcheck.py <phone>

Bước 2 — test gửi SMS:
    python test_new.py <phone>
"""

import sys
import asyncio
from pathlib import Path

from tien24h import send_sms as tien24h_sms, JWT_FILE


async def main():
    phone = sys.argv[1] if len(sys.argv) > 1 else input("Số điện thoại: ").strip()

    # Kiểm tra JWT file tồn tại trước
    if not JWT_FILE.exists():
        print(f"[!] Chưa có JWT file: {JWT_FILE}")
        print(f"[!] Chạy trước: python tien24h_appcheck.py {phone}")
        return

    print(f"\n=== test tien24h_sms({phone}) ===")
    await tien24h_sms(phone)


if __name__ == "__main__":
    asyncio.run(main())
