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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529227386:AAFsqpj5mq4N_fRq1MJ9_hwF-hir7bVGrxw")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zjfuvwvzjpwmytmvywib.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_r8cPTMZLPK18QagNbIUz-w_uuOruHEQ")

# 👑 ADMINS CONFIGURATION
ADMINS = [5074717463, 6144546817]

# Logging setup
logging.basicConfig(level=logging.INFO)

# 1️⃣ CLIENT INITIALIZE
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Supabase Database Client Initialize
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

    # Check for Deep-linking (e.g. /start file_id)
    if len(message.command) > 1:
        file_code = message.command[1]
        try:
            # Database se file fetch karo
            res = supabase.table("files").select("*").eq("file_code", file_code).execute()
            if res.data:
                file_data = res.data[0]
                file_id = file_data["file_id"]
                file_type = file_data["file_type"]
                caption = file_data.get("caption", "")

                # File type ke mutabiq send karo
                if file_type == "video":
                    await client.send_video(user_id, file_id, caption=caption)
                elif file_type == "document":
                    await client.send_document(user_id, file_id, caption=caption)
                elif file_type == "audio":
                    await client.send_audio(user_id, file_id, caption=caption)
                elif file_type == "photo":
                    await client.send_photo(user_id, file_id, caption=caption)
                else:
                    await client.send_cached_media(user_id, file_id, caption=caption)
                return
            else:
                await message.reply_text("❌ File nahi mili ya link invalid ho chuka hai!")
                return
        except Exception as e:
            logging.error(f"Deep link error: {e}")
            await message.reply_text("⚠️ File fetch karne mein error aaya hai.")
            return

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

    welcome_text = (
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        "Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
        "👑 **Developer / Creator:** Kage (Kage x Edit)\n\n"
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


# 📥 Restricted Content / Media Saver Handler
@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def save_restricted_media(client, message):
    user_id = message.from_user.id
    if ADMINS and user_id not in ADMINS:
        return

    # Determine file type and file_id
    file_id = None
    file_type = "unknown"
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"

    if not file_id:
        return

    caption = message.caption or ""
    import random
    import string
    # Unique short code generate karo
    file_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    try:
        # Supabase mein store karo (Make sure 'files' table exist karti ho supabase mein)
        supabase.table("files").insert({
            "file_code": file_code,
            "file_id": file_id,
            "file_type": file_type,
            "caption": caption,
            "user_id": user_id
        }).execute()

        bot_info = await client.get_me()
        bot_username = bot_info.username
        share_link = f"https://t.me/{bot_username}?start={file_code}"

        await message.reply_text(
            f"✅ **File Successfully Saved!**\n\n"
            f"🔗 **Sharable Link:**\n`{share_link}`\n\n"
            f"Is link ko copy karke apne channel par bhej sakte hain. Jab koi is par click karega, bot seedha video bhej dega!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Open Link", url=share_link)]
            ])
        )
    except Exception as e:
        logging.error(f"Error saving file to DB: {e}")
        await message.reply_text("❌ File save karne mein database error aaya hai. Table schema check karein.")


# 🔘 Inline Buttons Callback Handler
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if ADMINS and user_id not in ADMINS:
        await callback_query.answer("⚠️ Access Denied!", show_alert=True)
        return

    if data == "my_files":
        await callback_query.message.edit_text(
            "📁 **My Files / Hub**\n\n"
            "Yahan aapki saved files aur restricted content ki list dikhegi.\n"
            "Apni file save karne ke liye mujhe direct koi bhi media forward karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "media_downloader":
        await callback_query.message.edit_text(
            "📥 **Universal Media Downloader**\n\n"
            "Kisi bhi platform (YouTube, Instagram, etc.) ki link yahan bhejein aur media download karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "premium":
        await callback_query.message.edit_text(
            "💎 **Premium & Coins Hub**\n\n"
            "Aapka current plan: **Free**\n"
            "Coins balance: 0\n\n"
            "Premium features unlock karne ke liye admin se contact karein.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "help":
        await callback_query.message.edit_text(
            "⚙️ **Help & Support**\n\n"
            "Kisi bhi problem ke liye developer se sampark karein:\n"
            "👑 **Developer:** @Kage_x_edit",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
    elif data == "main_menu":
        welcome_text = (
            f"👋 **Hello {callback_query.from_user.first_name}!**\n\n"
            "Welcome to **Kage x Bot** — Your ultimate all-in-one media and file management studio. 🚀\n\n"
            "👑 **Developer / Creator:** Kage (Kage x Edit)\n\n"
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
        await callback_query.message.edit_text(welcome_text, reply_markup=keyboard)
    
    await callback_query.answer()

# 🌐 Simple HTTP Server for Port Binding
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
    server.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_http_server)
    server_thread.daemon = True
    server_thread.start()

    logging.info("🤖 Starting Kage x Bot...")
    app.run()
