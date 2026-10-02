import os
import logging
import asyncio
import re
import time
import base64
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
USER_NEW_FILENAMES = {}
WAITING_FOR_FILENAME = set()
USER_SETTING_BANNER = set()
USER_BANNERS = {}

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Handle start with secure protected link parameter
    if len(message.command) > 1 and message.command[1].startswith("secure_"):
        token = message.command[1].replace("secure_", "")
        try:
            decoded_bytes = base64.urlsafe_b64decode(token.encode("utf-8"))
            original_link = decoded_bytes.decode("utf-8")
            
            await message.reply_text(
                f"✅ **Protected Link Unlocked Successfully!**\n\n"
                f"Aapka original link yeh raha:\n"
                f"🔗 {original_link}\n\n"
                f"Ab aap isse access kar sakte hain."
            )
            return
        except Exception:
            await message.reply_text("❌ **Invalid or Expired Protected Link!**")
            return

    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Studio & Rename", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("🔐 Link Protector", callback_data="protector_menu"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ]
    ])

    await message.reply_text(
        f"👋 **Hello {username}!**\n\n"
        f"Welcome to **Kage x Bot** 🚀\n"
        f"👑 **Developer:** @kage_x_edit\n\n"
        f"Aap yahan files rename karne ke sath-sath **Link Protector (`/protect`)** ka use bhi kar sakte hain!",
        reply_markup=menu_keyboard
    )

@app.on_callback_query(filters.regex("compress_menu"))
async def compress_menu(client, callback_query):
    await callback_query.message.edit_text(
        "🗜 **Video Renamer & Watermark Studio**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Bhai, apni video yahan direct bhej do. Phir bot aapse naya filename aur output type puchega!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")],
            [InlineKeyboardButton("⬅ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("set_banner_menu"))
async def set_banner_menu(client, callback_query):
    user_id = callback_query.from_user.id
    USER_SETTING_BANNER.add(user_id)
    
    banner_path = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
    has_banner = os.path.exists(banner_path)
    
    status_text = "🟢 **Aapka custom thumbnail pehle se saved hai!**" if has_banner else "🔴 **Abhi koi thumbnail saved nahi hai.**"
    
    await callback_query.message.edit_text(
        f"🖼 **Custom Thumbnail Setup**\n\n"
        f"{status_text}\n\n"
        f"Ab apni **Thumbnail ya Logo image (Photo)** yahan chat mein direct bhej do!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("protector_menu"))
async def protector_menu(client, callback_query):
    await callback_query.message.edit_text(
        "🔐 **Protected Link Generator (LkProtector)**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Kisi bhi link ko secure protect karne ke liye is format mein command bhejein:\n"
        "`/protect <tumhara_link>`\n\n"
        "Example:\n"
        "`/protect https://t.me/+G1ca0WgdltQyZjU1`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]
        ])
    )

@app.on_callback_query(filters.regex("back_to_menu"))
async def back_to_menu(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
    if user_id in WAITING_FOR_FILENAME:
        WAITING_FOR_FILENAME.remove(user_id)
        
    menu_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📁 My Files / Hub", callback_data="my_files"),
            InlineKeyboardButton("📥 Downloader", callback_data="downloader")
        ],
        [
            InlineKeyboardButton("🗜️ Video Studio & Rename", callback_data="compress_menu"),
            InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="set_banner_menu")
        ],
        [
            InlineKeyboardButton("🔐 Link Protector", callback_data="protector_menu"),
            InlineKeyboardButton("💎 Premium", callback_data="premium")
        ]
    ])
    await callback_query.message.edit_text(
        "👋 **Main Menu**\n"
        "👑 **Developer:** @kage_x_edit\n\n"
        "Neeche diye gaye buttons se features explore karein:",
        reply_markup=menu_keyboard
    )

# 🔐 PROTECTED LINK GENERATOR COMMAND (/protect)
@app.on_message(filters.command("protect") & filters.private)
async def protect_link_command(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text(
            "⚠️ **Invalid Format!**\n\n"
            "Sahi tarika:\n`/protect <tumhara_link>`"
        )
        return

    raw_link = args[1].strip()
    
    # Encode link securely using Base64
    encoded_bytes = base64.urlsafe_b64encode(raw_link.encode("utf-8"))
    encoded_str = encoded_bytes.decode("utf-8")
    
    bot_username = (await client.get_me()).username
    protected_url = f"https://t.me/{bot_username}?start=secure_{encoded_str}"
    
    response_text = (
        f"🔐 **Protected Link:**\n"
        f"`{protected_url}`\n\n"
        f"✨ *Yeh link fully protected hai, user start karega tabhi original link access kar payega!*"
    )
    
    await message.reply_text(response_text)

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

# 🖼 HANDLE PHOTO, VIDEO INPUT
@app.on_message(filters.photo & filters.private)
async def receive_photo(client, message):
    user_id = message.from_user.id
    if user_id in USER_SETTING_BANNER:
        USER_SETTING_BANNER.remove(user_id)
        banner_path = f"banner_{user_id}.png"
        downloaded_banner = await message.download(file_name=banner_path)
        USER_BANNERS[user_id] = downloaded_banner or banner_path
        
        await message.reply_text(
            "✅ **Thumbnail Saved**\n\n"
            "Ab aap jab bhi video bhejenge, ye thumbnail video par lag jayegi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu")]])
        )

@app.on_message((filters.video | filters.document) & filters.private)
async def receive_video(client, message):
    user_id = message.from_user.id
    if message.document and not message.document.mime_type.startswith("video"):
        return

    USER_VIDEOS[user_id] = message
    WAITING_FOR_FILENAME.add(user_id)
    
    old_file_name = "video.mp4"
    if message.video and message.video.file_name:
        old_file_name = message.video.file_name
    elif message.document and message.document.file_name:
        old_file_name = message.document.file_name

    await message.reply_text(
        f"Please Enter New Filename...\n\n"
        f"Old File Name :- `{old_file_name}`"
    )

@app.on_message(filters.text & filters.private)
async def receive_filename(client, message):
    user_id = message.from_user.id
    if message.text.startswith("/"):
        return

    if user_id in WAITING_FOR_FILENAME:
        WAITING_FOR_FILENAME.remove(user_id)
        new_name = message.text.strip()
        if not new_name.endswith((".mp4", ".mkv", ".avi", ".mov")):
            new_name += ".mp4"
            
        USER_NEW_FILENAMES[user_id] = new_name
        
        type_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📁 Document", callback_data="type_document"),
                InlineKeyboardButton("🎬 Video", callback_data="type_video")
            ]
        ])
        
        await message.reply_text(
            f"Select The Output File Type\n\n"
            f"File Name :- `{new_name}`",
            reply_markup=type_keyboard
        )

# 🔄 PROCESS RENAME & UPLOAD
@app.on_callback_query(filters.regex(r"^type_"))
async def process_renaming(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in USER_VIDEOS or user_id not in USER_NEW_FILENAMES:
        await callback_query.answer("⚠ Session expired! Dubara video bhejo.", show_alert=True)
        return

    is_document = "document" in callback_query.data
    msg = USER_VIDEOS[user_id]
    new_filename = USER_NEW_FILENAMES[user_id]
    
    status_msg = await callback_query.message.edit_text("Fast download...")
    
    input_file = f"input_{user_id}.mp4"
    output_file = f"output_{user_id}.mp4"
    banner_file = USER_BANNERS.get(user_id, f"banner_{user_id}.png")
    
    try:
        last_dl_time = [0]
        async def dl_progress(current, total):
            if total > 0:
                now = time.time()
                if now - last_dl_time[0] > 2 or current == total:
                    last_dl_time[0] = now
                    pct = int(current * 100 / total)
                    pct = max(0, min(100, pct))
                    filled_blocks = int(pct / 10)
                    bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
                    speed = current / (max(1, now - last_dl_time[0]) * 1024 * 1024)
                    try:
                        await status_msg.edit(
                            f"Progress: [{bar}] {pct}%\n"
                            f"📥 Downloading: {current / (1024*1024):.1f} Mb | {total / (1024*1024):.2f} Mb\n"
                            f"⚡ Speed: {speed:.2f} Mb/s"
                        )
                    except Exception:
                        pass

        downloaded_path = await msg.download(file_name=input_file, progress=dl_progress)
        
        await status_msg.edit("Trying To Uploading....")
        
        has_banner = os.path.exists(banner_file)
        
        if has_banner:
            filter_complex = f"[1:v]scale=-1:60[banner];[0:v][banner]overlay=W-w-15:15[v]"
            command = [
                FFMPEG_PATH, "-i", downloaded_path, "-i", banner_file,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "0:a?",
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k",
                output_file, "-y"
            ]
        else:
            command = [
                FFMPEG_PATH, "-i", downloaded_path,
                "-c", "copy",
                output_file, "-y"
            ]
            
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        
        final_file = output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 1024 else downloaded_path
        
        renamed_path = os.path.join(os.path.dirname(final_file), new_filename)
        if os.path.exists(renamed_path):
            os.remove(renamed_path)
        os.rename(final_file, renamed_path)
        
        thumb_path = banner_file if has_banner else None
        if not thumb_path and msg.video and msg.video.thumbs:
            try:
                thumb_path = await client.download_media(msg.video.thumbs[0].file_id)
            except Exception:
                pass

        if is_document:
            await client.send_document(
                chat_id=callback_query.message.chat.id,
                document=renamed_path,
                thumb=thumb_path,
                caption=new_filename
            )
        else:
            await client.send_video(
                chat_id=callback_query.message.chat.id,
                video=renamed_path,
                thumb=thumb_path,
                supports_streaming=True,
                caption=new_filename
            )
            
        if thumb_path and thumb_path != banner_file and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        await status_msg.delete()
        
    except Exception as _err:
        await status_msg.edit(f"❌ Error: `{str(_err)}`")
        
    finally:
        for f in [input_file, output_file]:
            if os.path.exists(f):
                os.remove(f)
        if user_id in USER_VIDEOS:
            del USER_VIDEOS[user_id]
        if user_id in USER_NEW_FILENAMES:
            del USER_NEW_FILENAMES[user_id]

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
