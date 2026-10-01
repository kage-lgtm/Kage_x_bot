import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client as SupabaseClient

# Credentials & Supabase Config
API_ID = int(os.environ.get("API_ID", 38215355))
API_HASH = os.environ.get("API_HASH", "3f095c170be8c744b8f3d7f9c75ae544")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# 👑 ADMINS CONFIGURATION
ADMINS = [5074717463, 6144546817]

# Logging setup
logging.basicConfig(level=logging.INFO)

# 1️⃣ BOT CLIENT INITIALIZE (For commands and menus)
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 2️⃣ USERBOT CLIENT INITIALIZE (For fetching restricted media)
userbot = Client(
    "Kage_Userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Supabase Database Client Initialize
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if ADMINS and user_id not in ADMINS:
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "Yeh ek private bot hai. Aapke paas isko use karne ki permission nahi hai."
        )
        return

    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("⚡ Save Restricted", callback_data="save_restricted")
        ],
        [
            InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
            InlineKeyboardButton("⚙️ Help & Support", callback_data="help")
        ]
    ])

    await message.reply_text(
        f"👋 **Hello {username}!**\n\n"
        f"Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
        f"👑 **Developer / Creator:** Kage (Kage x Edit)\n\n"
        f"✨ **What I can do:**\n"
        f"📁 File Store & Restricted Content Saving\n"
        f"📥 Universal Media Downloader (YouTube, Insta, etc.)\n"
        f"🌐 Subtitle & Translation Tools\n"
        f"⚡ Fast & Free Processing!\n\n"
        f"Neeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex("save_restricted"))
async def save_restricted_menu(client, callback_query):
    await callback_query.message.edit_text(
        "⚡ **Save Restricted Content**\n\n"
        "Bhai, ab aapko jis bhi private channel ya restricted media ka link (`t.me/c/...`) chahiye, wo yahan direct bhej do. Mera userbot usko turant fetch karke aapko bhej dega!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("⚡ Save Restricted", callback_data="save_restricted")
        ],
        [
            InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
            InlineKeyboardButton("⚙️ Help & Support", callback_data="help")
        ]
    ])
    await callback_query.message.edit_text(
        "👋 **Main Menu**\n\nNeeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

# Restricted Media Link Handler using USERBOT with Dialog Cache & Peer Fix
@app.on_message(filters.text & filters.private & filters.regex(r"t\.me/c/"))
async def fetch_restricted_media(client, message):
    link = message.text.strip()
    sent_msg = await message.reply("🔄 **Fetching restricted file... Please wait!**")
    
    try:
        parts = link.split("/")
        chat_id_raw = parts[-2]
        chat_id = int("-100" + chat_id_raw)
        msg_id = int(parts[-1])
        
        # 🔑 FIX: Userbot dialogs fetch karke cache refresh karenge taaki peer invalid error na aaye
        async for dialog in userbot.get_dialogs():
            pass
            
        # Chat resolve karo
        await userbot.get_chat(chat_id)
        
        # Message fetch karo
        fetched_msg = await userbot.get_messages(chat_id, msg_id)
        
        if fetched_msg:
            await fetched_msg.copy(message.chat.id)
            await sent_msg.delete()
        else:
            await sent_msg.edit("❌ File nahi mili ya link galat hai.")
            
    except Exception as e:
        await sent_msg.edit(f"❌ Error aa gaya bhai: `{str(e)}`")

# Simple HTTP Server
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Kage x Bot is active and running!")
    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()

    logging.info("🤖 Starting Kage x Userbot & Bot...")
    userbot.start()  # Userbot session start karega
    app.run()
