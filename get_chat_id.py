"""
Jalankan script ini untuk mendapatkan CHAT_ID kamu.
Pastikan kamu sudah kirim pesan ke bot kamu di Telegram sebelum menjalankan ini.

Cara pakai:
  python get_chat_id.py
"""
from bot.telegram import get_updates

TOKEN = input("Masukkan TOKEN bot kamu: ").strip()

updates = get_updates(TOKEN)

if not updates:
    print("\nTidak ada pesan ditemukan.")
    print("Pastikan kamu sudah kirim pesan (apapun) ke bot kamu di Telegram, lalu coba lagi.")
else:
    print("\nChat ID yang ditemukan:")
    seen = set()
    for u in updates:
        msg = u.get('message', {})
        chat = msg.get('chat', {})
        cid  = chat.get('id')
        name = chat.get('first_name', '') + ' ' + chat.get('last_name', '')
        if cid and cid not in seen:
            print(f"  Chat ID : {cid}  |  Nama: {name.strip()}")
            seen.add(cid)
    print("\nSalin Chat ID di atas ke config.py pada bagian TELEGRAM_CHAT_ID")
