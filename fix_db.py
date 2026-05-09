import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

async def fix():
    print("Sedang memperbaiki database...")
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL tidak ditemukan di .env")
        return

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        # Menambah kolom next_allowed jika belum ada
        print("Checking columns in 'processed_dramas'...")
        await conn.execute('''
            ALTER TABLE processed_dramas 
            ADD COLUMN IF NOT EXISTS next_allowed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        ''')
        # Menambah kolom last_attempt jika belum ada
        await conn.execute('''
            ALTER TABLE processed_dramas 
            ADD COLUMN IF NOT EXISTS last_attempt TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        ''')
        await conn.close()
        print("✅ Database berhasil diperbaiki! Sekarang jalankan bot kembali.")
    except Exception as e:
        print(f"❌ Gagal memperbaiki database: {e}")

if __name__ == "__main__":
    asyncio.run(fix())
