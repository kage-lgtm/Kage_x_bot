import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client as SupabaseClient

# Credentials & Supabase Config
API_ID = 38215355
API_HASH = "3f095c170be8c744b8f3d7f9c75ae544"
BOT_TOKEN = "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw"

SUPABASE_URL = "https://zjfuvwvzjpwmytmvywib.supabase.co"
SUPABASE_KEY = "sb_publishable_r8cPTMZLPK18QagNbIUz-w_uuOruHEQ"

# 👑 ADMINS CONFIGURATION
ADMINS = [5074717463, 6144546817]

# Logging setup
logging.basicConfig(level=logging.INFO)

# Pyrogram Bot Client Initialize karo
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Supabase Database Client Initialize karo
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # 🔒 ACCESS CONTROL CHECK
    if ADMINS and user_id not in ADMINS:
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "Yeh ek private bot hai. Aapke paas isko use karne ki permission nahi hai.\n"
            "Access ke liye developer se contact karein: **@Kage_x_edit**"
        )
        return

    # Database mein user save karne ka logic
    try:
        existing_user = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
        if not existing_user.data:
            supabase.table("users").insert({
                "user_id": user_id,
                "username": username,
                "coins": 0,
                "is_premium": False
            }).execute()
    except Exception as e:
        logging.error(f"Database Error: {e}")

    # Welcome Message with Developer / Brand Details
    welcome_text = (
        f"👋 **Hello {username}!\n\n**"
        "Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
        "👑 **Developer / Creator:** Kage (Kage x Edit)\n"
        "🎬 **Studio:** ZK Dubbing Studio\n\n"
        "✨ **What I can do:**\n"
        "📁 File Store & Restricted Content Saving\n"
        "📥 Universal Media Downloader (YouTube, Insta, etc.)\n"
        "🌐 Subtitle & Translation Tools\n"
        "⚡ Fast & Free Processing!\n\n"
        "Neeche diye gaye buttons se features explore karein:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
         InlineKeyboardButton("📥 Downloader", callback_data="media_downloader")],
        [InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
         InlineKeyboardButton("⚙️ Help & Support", callback_data="help")]
    ])

    await message.reply_text(welcome_text, reply_markup=keyboard)

# 🌐 Simple HTTP Server for Render Port Binding
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Kage x Bot is active and running 24/7!")
    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    logging.info(f"🌐 HTTP server started on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Background thread mein HTTP server start karo
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()

    # Pyrogram Bot ko main thread mein start karo
    logging.info("🤖 Starting Kage x Bot...")
    app.run()
