import os
import logging
import asyncio
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from supabase import create_client, Client as SupabaseClient
import imageio_ffmpeg

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

# Get internal FFmpeg executable path automatically
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

# 1️⃣ BOT CLIENT INITIALIZE
app = Client(
    "Kage_x_Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# 2️⃣ USERBOT CLIENT INITIALIZE
userbot = Client(
    "Kage_Userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Supabase Database Client Initialize
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

# Temporary storage for video compression sessions
USER_VIDEOS = {}

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if ADMINS and user_id not in ADMINS:
        await message.reply_text("⚠️ **Access Denied!**")
        return

    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Compressor", callback_data="compress_menu")
        ],
        [
            InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
            InlineKeyboardButton("⚙️ Help & Support", callback_data="help")
        ]
    ])

    await message.reply_text(
        f"👋 **Hello {username}!**\n\nWelcome to **Kage x Bot** 🚀\n\nNeeche diye gaye buttons se features explore karein, ya koi bhi restricted link yahan bhej do save karne ke liye!",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    await callback_query.message.edit_text(
        "🗜️ **Video Compressor Studio**\n\n"
        "Bhai, apni video yahan direct bhej do. Uske baad main tujhe quality options dunga ki kitni quality tak compress karna hai!",
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
            InlineKeyboardButton("🗜️ Video Compressor", callback_data="compress_menu")
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

# 📥 SAVE RESTRICTED CONTENT HANDLER (WITH DOWNLOAD & UPLOAD BYPASS)
@app.on_message(filters.regex(r"https?://t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)") & filters.private)
async def restricted_link_handler(client, message):
    user_id = message.from_user.id
    link = message.text.strip()
    
    match = re.search(r"t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", link)
    if not match:
        return
        
    chat_identifier = match.group(1)
    msg_id = int(match.group(2))
    
    if chat_identifier.isdigit():
        chat_id = int("-100" + chat_identifier)
    else:
        chat_id = "@" + chat_identifier
        
    progress_msg = await message.reply_text("📥 **Fetching restricted content via userbot...**")
    
    try:
        target_msg = await userbot.get_messages(chat_id, msg_id)
        
        if not target_msg or target_msg.empty:
            await progress_msg.edit("❌ Ye message nahi mila ya delete ho gaya hai!")
            return
            
        if target_msg.media:
            await progress_msg.edit("📥 **Downloading restricted media...**")
            file_path = await target_msg.download()
            
            await progress_msg.edit("📤 **Uploading file to you...**")
            if target_msg.video:
                await client.send_video(chat_id=message.chat.id, video=file_path, caption=target_msg.caption or "")
            elif target_msg.document:
                await client.send_document(chat_id=message.chat.id, document=file_path, caption=target_msg.caption or "")
            elif target_msg.photo:
                await client.send_photo(chat_id=message.chat.id, photo=file_path, caption=target_msg.caption or "")
            elif target_msg.audio:
                await client.send_audio(chat_id=message.chat.id, audio=file_path, caption=target_msg.caption or "")
            
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await client.send_message(chat_id=message.chat.id, text=target_msg.text or "")
            
        await progress_msg.delete()
        
    except Exception as e:
        await progress_msg.edit(f"❌ Error aagaya bhai: `{str(e)}`\n\nMake sure userbot is joined or added to that channel/group!")

# Handle incoming videos for compression
@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video(client, message):
    user_id = message.from_user.id
    
    if message.document and not message.document.mime_type.startswith("video"):
        return

    if message.text and "t.me/" in message.text:
        return

    USER_VIDEOS[user_id] = message
    
    quality_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 480p (Fast & Light)", callback_data="comp_480p"),
            InlineKeyboardButton("💻 540p (Standard)", callback_data="comp_540p")
        ],
        [
            InlineKeyboardButton("🎬 720p (HD Quality)", callback_data="comp_720p"),
            InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")
        ]
    ])
    
    await message.reply_text(
        "🎬 **Video mil gayi bhai!**\n\nNeeche se select karo ki isko kis quality mein compress karna hai:",
        reply_markup=quality_keyboard
    )

# Process Compression with Live Percentage Progress Bar
@app.on_callback_query(filters.regex(r"^comp_"))
async def process_compression(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠️️ Koi video nahi mili! Dubara video bhejo.", show_alert=True)
        return

    data = callback_query.data
    resolution = "480" if "480p" in data else ("540" if "540p" in data else "720")
    
    msg = USER_VIDEOS[user_id]
    duration = getattr(msg.video, "duration", 0) if msg.video else 0
    
    status_msg = await callback_query.message.edit_text(f"🔄 **Downloading video for compression ({resolution}p)...**")
    
    input_file = f"input_{user_id}.mp4"
    output_file = f"output_{user_id}.mp4"
    
    try:
        downloaded_path = await msg.download(file_name=input_file)
        await status_msg.edit(f"🗜️ **Starting compression to {resolution}p...**")
        
        if resolution == "480":
            scale_filter = "scale=-2:480"
        elif resolution == "540":
            scale_filter = "scale=960:540"
        else:
            scale_filter = "scale=-2:720"
            
        command = [
            FFMPEG_PATH, "-i", downloaded_path,
            "-vf", scale_filter,
            "-c:v", "libx264", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            output_file, "-y"
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        last_percent = -1
        
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='ignore')
            
            time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line_str)
            if time_match and duration > 0:
                hrs, mins, secs = map(float, time_match.groups())
                current_seconds = hrs * 3600 + mins * 60 + secs
                percent = int((current_seconds / duration) * 100)
                percent = max(0, min(100, percent))
                
                if percent >= last_percent + 10:
                    last_percent = percent
                    filled_blocks = int(percent / 10)
                    bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
                    try:
                        await status_msg.edit(
                            f"🗜️ **Compressing to {resolution}p...**\n\n"
                            f"[{bar}] **{percent}%**\n"
                            f"⏳ Please wait while video is being processed."
                        )
                    except Exception:
                        pass

        await process.wait()
        
        if os.path.exists(output_file):
            await status_msg.edit("📤 **Uploading compressed video...**")
            await client.send_video(
                chat_id=callback_query.message.chat.id,
                video=output_file,
                caption=f"✅ **Compressed successfully to {resolution}p!**\n👑 By Kage x Bot"
            )
            await status_msg.delete()
        else:
            await status_msg.edit("❌ Compression fail ho gaya bhai!")
            
    except Exception as e:
        await status_msg.edit(f"❌ Error: `{str(e)}`")
        
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)
        if os.path.exists(output_file):
            os.remove(output_file)
        if user_id in USER_VIDEOS:
            del USER_VIDEOS[user_id]

# Simple HTTP Server for Railway
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
    
    try:
        userbot.start()
    except FloodWait as e:
        logging.warning(f"Userbot FloodWait: Need to wait {e.value} seconds.")
    except Exception as e:
        logging.warning(f"Userbot start error: {e}")

    try:
        app.run()
    except FloodWait as e:
        logging.error(f"Bot FloodWait: Telegram is asking to wait for {e.value} seconds.")
    except Exception as e:
        logging.error(f"Bot run error: {e}")
