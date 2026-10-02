import os
import logging
import asyncio
import re
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from supabase import create_client, Client as SupabaseClient
import imageio_ffmpeg
import subprocess

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

# Temporary storage & states
USER_VIDEOS = {}
USER_SETTING_BANNER = set()

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
            InlineKeyboardButton("🗜️ Video Compressor", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Banner", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
            InlineKeyboardButton("⚙️ Help & Support", callback_data="help")
        ]
    ])

    await message.reply_text(
        f"👋 **Hello {username}!**\n\n"
        f"Welcome to **Kage x Bot** 🚀\n"
        f"👑 **Developer:** @kage_x_edit\n\n"
        f"Neeche diye gaye buttons se features explore karein, ya koi bhi restricted link yahan bhej do save karne ke liye!",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    await callback_query.message.edit_text(
        "🗜️ **Video Watermark / Compressor Studio**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Bhai, apni video yahan direct bhej do. Banner lagane ke liye options mil jayenge!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ Set Custom Banner", callback_data="set_banner_menu")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("set_banner_menu"))
async def set_banner_menu(client, callback_query):
    user_id = callback_query.from_user.id
    USER_SETTING_BANNER.add(user_id)
    
    banner_path = f"banner_{user_id}.png"
    has_banner = os.path.exists(banner_path)
    
    status_text = "🟢 **Aapka current banner pehle se saved hai!** (Naya bhejne par update ho jayega)" if has_banner else "🔴 **Abhi koi banner saved nahi hai.**"
    
    await callback_query.message.edit_text(
        f"🖼 **Custom Banner Setup**\n\n"
        f"{status_text}\n\n"
        f"Ab apni **Logo ya Banner image (Photo)** yahan chat mein direct bhej do!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        
    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Compressor", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Banner", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("💎 Premium & Coins", callback_data="premium"),
            InlineKeyboardButton("⚙️ Help & Support", callback_data="help")
        ]
    ])
    await callback_query.message.edit_text(
        "👋 **Main Menu**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Neeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

# 📥 SAVE RESTRICTED CONTENT HANDLER
@app.on_message(filters.regex(r"https?://t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)") & filters.private)
async def restricted_link_handler(client, message):
    link = message.text.strip()
    match = re.search(r"t\.me/(?:c/)?([a-zA-Z0-9_]+)/(\d+)", link)
    if not match:
        return
        
    chat_identifier = match.group(1)
    msg_id = int(match.group(2))
    chat_id = int("-100" + chat_identifier) if chat_identifier.isdigit() else "@" + chat_identifier
        
    progress_msg = await message.reply_text("📥 **Fetching restricted content...**")
    
    last_update_time = [0]
    async def progress_callback(current, total):
        now = time.time()
        if total > 0 and (now - last_update_time[0] > 3 or current == total):
            last_update_time[0] = now
            percent = int(current * 100 / total)
            percent = max(0, min(100, percent))
            filled_blocks = int(percent / 10)
            bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
            try:
                await progress_msg.edit(
                    f"📥 **Downloading restricted media...**\n\n"
                    f"[{bar}] **{percent}%**\n"
                    f"📊 `{current / (1024*1024):.2f} MB` / `{total / (1024*1024):.2f} MB`"
                )
            except Exception:
                pass

    try:
        target_msg = await userbot.get_messages(chat_id, msg_id)
        if not target_msg or target_msg.empty:
            await progress_msg.edit("❌ Ye message nahi mila ya delete ho gaya hai!")
            return
            
        if target_msg.media:
            file_path = await target_msg.download(progress=progress_callback)
            await progress_msg.edit("📤 **Uploading file to you...**")
            
            if target_msg.video:
                thumb_path = None
                if target_msg.video.thumbs:
                    thumb_path = await userbot.download_media(target_msg.video.thumbs[0].file_id)
                
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    thumb=thumb_path,
                    duration=target_msg.video.duration,
                    width=target_msg.video.width,
                    height=target_msg.video.height,
                    supports_streaming=True,
                    caption=target_msg.caption or ""
                )
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
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
        await progress_msg.edit(f"❌ Error aagaya bhai: `{str(e)}`")

# 🖼️ HANDLE BANNER PHOTO OR VIDEO
@app.on_message((filters.photo | filters.video | filters.document) & filters.private)
async def receive_media(client, message):
    user_id = message.from_user.id
    
    # 1. If user is in banner setting mode and sent a photo
    if message.photo and user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.png"
        await message.download(file_name=banner_path)
        
        menu_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗜️ Compressor Menu", callback_data="compress_menu"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")
            ]
        ])
        await message.reply_text(
            "✅ **Banner/Logo successfully save ho gaya hai!**\n\n"
            "Ab aap jab bhi video bhejenge, ye banner automatically video par lag jayega.",
            reply_markup=menu_keyboard
        )
        return

    if message.text and "t.me/" in message.text:
        return

    if message.document and not message.document.mime_type.startswith("video"):
        return

    # 2. Handle incoming video
    if message.video or message.document:
        USER_VIDEOS[user_id] = message
        
        banner_path = f"banner_{user_id}.png"
        has_banner = os.path.exists(banner_path)
        banner_status = "🟢 Custom Banner Detected" if has_banner else "🔴 No Banner Set (Click 'Set Custom Banner')"
        
        options_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚡ Original Quality (Bina Compress kiye Banner lagaye)", callback_data="comp_original")
            ],
            [
                InlineKeyboardButton("📱 480P", callback_data="comp_480p"),
                InlineKeyboardButton("💻 540P", callback_data="comp_540p")
            ],
            [
                InlineKeyboardButton("🎬 720P", callback_data="comp_720p"),
                InlineKeyboardButton("🖼️ Change Banner", callback_data="set_banner_menu")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="back_to_menu")
            ]
        ])
        
        await message.reply_text(
            f"🎬 **Video mil gayi bhai!**\n"
            f"Status: `{banner_status}`\n\n"
            f"Select option (Original Quality choose karne par video compress nahi hogi, sirf banner lag jayega):",
            reply_markup=options_keyboard
        )

# 🔄 PROCESS BANNER & COMPRESSION/ORIGINAL
@app.on_callback_query(filters.regex(r"^comp_"))
async def process_compression(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEOS:
        await callback_query.answer("⚠ Koi video nahi mili! Dubara video bhejo.", show_alert=True)
        return

    data = callback_query.data
    is_original = "original" in data
    resolution = "Original" if is_original else ("480" if "480p" in data else ("540" if "540p" in data else "720"))
    
    msg = USER_VIDEOS[user_id]
    
    original_size = 0
    if msg.video and hasattr(msg.video, "file_size"):
        original_size = msg.video.file_size
    elif msg.document and hasattr(msg.document, "file_size"):
        original_size = msg.document.file_size

    status_msg = await callback_query.message.edit_text(f"🔄 **Downloading video (Mode: {resolution})...**")
    
    input_file = f"input_{user_id}.mp4"
    output_file = f"output_{user_id}.mp4"
    banner_file = f"banner_{user_id}.png"
    
    try:
        last_dl_time = [0]
        async def dl_progress(current, total):
            if total > 0:
                now = time.time()
                if now - last_dl_time[0] > 2 or current == total:
                    last_dl_time[0] = now
                    pct = int(current * 100 / total)
                    pct = max(0, min(100, pct))
                    try:
                        await status_msg.edit(
                            f"📥 **Downloading video ({pct}%)...**\n"
                            f"📊 `{current / (1024*1024):.2f} MB` / `{total / (1024*1024):.2f} MB`"
                        )
                    except Exception:
                        pass

        downloaded_path = await msg.download(file_name=input_file, progress=dl_progress)
        
        if original_size == 0 and os.path.exists(downloaded_path):
            original_size = os.path.getsize(downloaded_path)
        
        await status_msg.edit(f"🖼️ **Applying Banner (Mode: {resolution})...**")
        
        def get_video_duration(file_path):
            try:
                cmd = [FFMPEG_PATH, "-i", file_path]
                result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
                if match:
                    hrs, mins, secs = map(float, match.groups())
                    return hrs * 3600 + mins * 60 + secs
            except Exception:
                pass
            return 0

        duration = get_video_duration(downloaded_path)
        has_banner = os.path.exists(banner_file)
        
        if is_original:
            # Bina resolution change kiye sirf original size par banner overlay karega high quality (crf 18) ke sath
            if has_banner:
                filter_complex = f"[1:v]scale=-1:60[banner];[0:v][banner]overlay=W-w-15:15[v]"
                command = [
                    FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "18",
                    "-c:a", "copy",
                    output_file, "-y"
                ]
            else:
                # Agar banner nahi hai toh simply copy kar dega bina loss ke
                command = [
                    FFMPEG_PATH, "-i", downloaded_path,
                    "-c", "copy",
                    output_file, "-y"
                ]
        else:
            if resolution == "480":
                base_scale = "scale=trunc(oh*a/2)*2:480,pad=iw:ih:(ow-iw)/2:(oh-ih)/2"
            elif resolution == "540":
                base_scale = "scale=trunc(oh*a/2)*2:540,pad=iw:ih:(ow-iw)/2:(oh-ih)/2"
            else:
                base_scale = "scale=trunc(oh*a/2)*2:720,pad=iw:ih:(ow-iw)/2:(oh-ih)/2"

            if has_banner:
                filter_complex = f"[0:v]{base_scale}[scaled];[1:v]scale=-1:60[banner];[scaled][banner]overlay=W-w-15:15[v]"
                command = [
                    FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                    "-filter_complex", filter_complex,
                    "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "28",
                    "-c:a", "aac", "-b:a", "128k",
                    output_file, "-y"
                ]
            else:
                command = [
                    FFMPEG_PATH, "-i", downloaded_path,
                    "-vf", base_scale,
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
        buffer = b""
        while True:
            chunk = await process.stderr.read(1024)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer or b"\r" in buffer:
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                else:
                    line, buffer = buffer.split(b"\r", 1)
                
                line_str = line.decode('utf-8', errors='ignore')
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line_str)
                if time_match and duration > 0:
                    hrs, mins, secs = map(float, time_match.groups())
                    current_seconds = hrs * 3600 + mins * 60 + secs
                    percent = int((current_seconds / duration) * 100)
                    percent = max(0, min(100, percent))
                    
                    if percent != last_percent and percent % 5 == 0:
                        last_percent = percent
                        filled_blocks = int(percent / 10)
                        bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
                        try:
                            await status_msg.edit(
                                f"🖼️ **Adding Banner (Mode: {resolution})...\n\n"
                                f"[{bar}] **{percent}%**"
                            )
                        except Exception:
                            pass

        await process.wait()
        
        if os.path.exists(output_file):
            await status_msg.edit("📤 **Uploading processed video...**")
            
            processed_size = os.path.getsize(output_file)
            orig_mb = original_size / (1024 * 1024) if original_size > 0 else 0
            proc_mb = processed_size / (1024 * 1024)
            
            thumb_path = None
            try:
                if msg.video and msg.video.thumbs:
                    thumb_path = await client.download_media(msg.video.thumbs[0].file_id)
            except Exception:
                pass
            
            original_caption = msg.caption or ""
            if len(original_caption) > 300:
                original_caption = original_caption[:300] + "..."

            final_caption = (
                f"✅ **Banner Added Successfully ({resolution} Quality)!**\n"
                f"📊 **Size:** `{proc_mb:.2f} MB` (Original: `{orig_mb:.2f} MB`)\n\n"
                f"{original_caption}\n\n"
                f"👑 **Developer:** @kage_x_edit"
            )
            
            try:
                await asyncio.wait_for(
                    client.send_video(
                        chat_id=callback_query.message.chat.id,
                        video=output_file,
                        thumb=thumb_path,
                        supports_streaming=True,
                        caption=final_caption
                    ),
                    timeout=300
                )
            except asyncio.TimeoutError:
                await status_msg.edit("❌ **Upload timed out!**")
                return
            
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
                
            await status_msg.delete()
        else:
            await status_msg.edit("❌ Process fail ho gaya bhai!")
            
    except Exception as _err:
        await status_msg.edit(f"❌ Error: `{str(_err)}`")
        
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
