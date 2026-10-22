"""
RestAron: Foydalanuvchilar parolini yangilash (reset) skripti
"""
import sys
import os
import asyncio
import getpass
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Backend papkasini qidiruv yo'liga qo'shish
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


async def reset_passwords():
    print("=" * 65)
    print(" RestAron: Foydalanuvchilar parolini yangilash (Reset Passwords)")
    print("=" * 65)

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).order_by(User.id))
        users = res.scalars().all()

        if not users:
            print("\n⚠️ Bazada birorta ham foydalanuvchi topilmadi.")
            return

        print(f"\nJami topilgan foydalanuvchilar soni: {len(users)}\n")
        header = f"{'ID':<4} | {'Username':<20} | {'Rol':<15} | {'Holat':<10}"
        print(header)
        print("-" * len(header))
        for u in users:
            role_str = u.role.value if hasattr(u.role, "value") else str(u.role)
            status_str = "Faol" if u.is_active else "Nofaol"
            print(f"{u.id:<4} | {u.username:<20} | {role_str:<15} | {status_str:<10}")
        print("-" * len(header))

        # 'dev' va 'developer' ikkalasi mavjudligini tekshirish
        dev_user = next((u for u in users if u.username == "dev"), None)
        developer_user = next((u for u in users if u.username == "developer"), None)

        if dev_user and developer_user:
            print("\n⚠️ 'dev' va 'developer' foydalanuvchilarining ikkalasi ham mavjud.")
            print("Qaysi birini nofaol (is_active=False) qilishni xohlaysiz? (o'chirilmaydi)")
            print("  1) 'dev' ni nofaol qilish")
            print("  2) 'developer' ni nofaol qilish")
            print("  0) Ikkalasini ham o'zgarishsiz qoldirish")
            choice = input("Tanlovingiz [0/1/2] (standart: 0): ").strip()
            if choice == "1":
                dev_user.is_active = False
                print("ℹ️ 'dev' foydalanuvchisi nofaol holatga o'tkazildi.")
            elif choice == "2":
                developer_user.is_active = False
                print("ℹ️ 'developer' foydalanuvchisi nofaol holatga o'tkazildi.")
            else:
                print("ℹ️ Ikkala foydalanuvchi ham o'zgarishsiz qoldirildi.")

        print("\nHar bir foydalanuvchi uchun yangi parol kiritishingiz mumkin.")
        print("(O'tkazib yuborish uchun shunchaki Enter bosing)")

        updated_count = 0
        for u in users:
            role_str = u.role.value if hasattr(u.role, "value") else str(u.role)
            status_str = "Faol" if u.is_active else "Nofaol"
            print(f"\n--- [ID: {u.id}] {u.username} (Rol: {role_str}, Holat: {status_str}) ---")

            while True:
                new_pwd = getpass.getpass("Yangi parol (kamida 10 ta belgi, o'tkazish uchun Enter): ")
                if not new_pwd:
                    print("⏭️ O'tkazib yuborildi.")
                    break
                if len(new_pwd) < 10:
                    print("❌ Parol kamida 10 ta belgidan iborat bo'lishi kerak!")
                    continue
                pwd_repeat = getpass.getpass("Parolni takrorlang: ")
                if new_pwd != pwd_repeat:
                    print("❌ Parollar mos kelmadi! Qaytadan urinib ko'ring.")
                    continue

                u.hashed_password = get_password_hash(new_pwd)
                updated_count += 1
                print(f"✅ '{u.username}' uchun parol belgilandi.")
                break

        await db.commit()
        print("\n" + "=" * 65)
        print(f"🎉 Jarayon yakunlandi! Jami yangilangan parollar: {updated_count}")
        print("=" * 65)


def main():
    try:
        asyncio.run(reset_passwords())
    except KeyboardInterrupt:
        print("\n\nJarayon bekor qilindi.")
        sys.exit(0)


if __name__ == "__main__":
    main()
